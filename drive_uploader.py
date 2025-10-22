"""
Google Drive Uploader for CSV to JSON Converter
Handles uploading JSON files to Google Drive and getting shareable URLs
"""

from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
import logging
from typing import List, Dict, Optional
import os
import yaml
import time


class GoogleDriveUploader:
    """Handles Google Drive operations for uploading JSON files"""
    
    def __init__(self, config_path: str = "config.yaml"):
        """Initialize with configuration"""
        self.config = self._load_config(config_path)
        self.logger = self._setup_logging()
        self.service = None
        self.output_folder_id = None
        self._authenticate()
        self._setup_output_folder()
    
    def _load_config(self, config_path: str) -> Dict:
        """Load configuration from YAML file"""
        try:
            with open(config_path, 'r', encoding='utf-8') as file:
                return yaml.safe_load(file)
        except FileNotFoundError:
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML configuration: {e}")
    
    def _setup_logging(self) -> logging.Logger:
        """Setup logging based on configuration"""
        logger = logging.getLogger(__name__)
        logger.setLevel(getattr(logging, self.config['logging']['level']))
        
        formatter = logging.Formatter(self.config['logging']['format'])
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
        return logger
    
    def _authenticate(self):
        """Authenticate with Google Drive API using OAuth"""
        try:
            # Define the scope for Google Drive
            scopes = ['https://www.googleapis.com/auth/drive']
            
            creds = None
            token_path = 'token.json'
            credentials_path = self.config['google_sheets']['credentials_path']
            
            # The file token.json stores the user's access and refresh tokens.
            # It is created automatically when the authorization flow completes for the first time.
            if os.path.exists(token_path):
                creds = Credentials.from_authorized_user_file(token_path, scopes)
            
            # If there are no (valid) credentials available, let the user log in.
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    # Use OAuth credentials file (client_secret.json format)
                    flow = InstalledAppFlow.from_client_secrets_file(credentials_path, scopes)
                    creds = flow.run_local_server(port=0)
                
                # Save the credentials for the next run
                with open(token_path, 'w') as token:
                    token.write(creds.to_json())
            
            # Build the service
            self.service = build('drive', 'v3', credentials=creds)
            self.logger.info("Successfully authenticated with Google Drive API using OAuth")
            
        except FileNotFoundError:
            raise FileNotFoundError(f"OAuth credentials file not found: {credentials_path}. Please use client_secret.json format.")
        except Exception as e:
            self.logger.error(f"Google Drive OAuth authentication failed: {e}")
            raise
    
    def _setup_output_folder(self):
        """Create or find the output folder in Google Drive"""
        try:
            folder_name = self.config['google_drive']['output_folder_name']
            
            # Search for existing folder
            query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder'"
            results = self.service.files().list(q=query, spaces='drive').execute()
            items = results.get('files', [])
            
            if items:
                # Folder exists, use the first one found
                self.output_folder_id = items[0]['id']
                self.logger.info(f"Using existing folder: {folder_name} (ID: {self.output_folder_id})")
            else:
                # Create new folder
                folder_metadata = {
                    'name': folder_name,
                    'mimeType': 'application/vnd.google-apps.folder'
                }
                
                folder = self.service.files().create(body=folder_metadata, fields='id').execute()
                self.output_folder_id = folder.get('id')
                self.logger.info(f"Created new folder: {folder_name} (ID: {self.output_folder_id})")
                
                # Make folder publicly readable if configured
                if self.config['google_drive']['make_public']:
                    self._make_public(self.output_folder_id)
            
        except Exception as e:
            self.logger.error(f"Failed to setup output folder: {e}")
            raise
    
    def _make_public(self, file_id: str):
        """Make a file publicly readable"""
        try:
            permission = {
                'type': 'anyone',
                'role': 'reader'
            }
            
            self.service.permissions().create(
                fileId=file_id,
                body=permission
            ).execute()
            
            self.logger.info(f"Made file public: {file_id}")
            
        except Exception as e:
            self.logger.warning(f"Failed to make file public {file_id}: {e}")
    
    def upload_file(self, file_path: str, filename: str = None, force_upload: bool = False) -> Dict[str, str]:
        """Upload a file to Google Drive and return the shareable URL"""
        try:
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"File not found: {file_path}")
            
            if filename is None:
                filename = os.path.basename(file_path)
            
            self.logger.info(f"Uploading file: {filename}")
            
            # Check if file already exists in the folder (unless force_upload is True)
            if not force_upload and self.config['processing']['skip_existing']:
                existing_file = self._find_file_in_folder(filename)
                if existing_file:
                    self.logger.info(f"File already exists, skipping: {filename}")
                    return {
                        'file_id': existing_file['id'],
                        'shareable_url': self._get_shareable_url(existing_file['id']),
                        'direct_url': self._get_direct_download_url(existing_file['id']),
                        'filename': filename
                    }
            
            # File metadata
            file_metadata = {
                'name': filename,
                'parents': [self.output_folder_id]
            }
            
            # Media upload
            media = MediaFileUpload(file_path, resumable=True)
            
            # Upload the file
            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id,name,webViewLink,webContentLink'
            ).execute()
            
            file_id = file.get('id')
            self.logger.info(f"Successfully uploaded: {filename} (ID: {file_id})")
            
            # Make file public if configured
            if self.config['google_drive']['make_public']:
                self._make_public(file_id)
            
            # Return file information
            return {
                'file_id': file_id,
                'shareable_url': self._get_shareable_url(file_id),
                'direct_url': self._get_direct_download_url(file_id),
                'filename': filename
            }
            
        except Exception as e:
            self.logger.error(f"Failed to upload file {file_path}: {e}")
            raise
    
    def _find_file_in_folder(self, filename: str) -> Optional[Dict]:
        """Find a file by name in the output folder"""
        try:
            query = f"name='{filename}' and parents='{self.output_folder_id}'"
            results = self.service.files().list(q=query).execute()
            items = results.get('files', [])
            
            return items[0] if items else None
            
        except Exception as e:
            self.logger.error(f"Failed to search for file {filename}: {e}")
            return None
    
    def _get_shareable_url(self, file_id: str) -> str:
        """Get the shareable URL for a file"""
        return f"https://drive.google.com/file/d/{file_id}/view"
    
    def _get_direct_download_url(self, file_id: str) -> str:
        """Get the direct download URL for a file"""
        return f"https://drive.google.com/uc?export=download&id={file_id}"
    
    def upload_multiple_files(self, file_paths: List[str], force_upload: bool = False) -> List[Dict[str, str]]:
        """Upload multiple files and return their information"""
        results = []
        
        for file_path in file_paths:
            try:
                result = self.upload_file(file_path, force_upload=force_upload)
                results.append(result)
                
                # Add delay to respect API rate limits
                time.sleep(0.5)
                
            except Exception as e:
                self.logger.error(f"Failed to upload {file_path}: {e}")
                if not self.config['error_handling']['continue_on_error']:
                    raise
                
                # Add error result
                results.append({
                    'file_id': None,
                    'shareable_url': None,
                    'direct_url': None,
                    'filename': os.path.basename(file_path),
                    'error': str(e)
                })
        
        self.logger.info(f"Uploaded {len([r for r in results if r.get('file_id')])} out of {len(file_paths)} files")
        return results
    
    def delete_file(self, file_id: str) -> bool:
        """Delete a file from Google Drive"""
        try:
            self.service.files().delete(fileId=file_id).execute()
            self.logger.info(f"Deleted file: {file_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to delete file {file_id}: {e}")
            return False
    
    def cleanup_old_files(self, filenames_to_replace: List[str]) -> int:
        """Delete old files that will be replaced with new versions"""
        deleted_count = 0
        
        try:
            self.logger.info(f"Cleaning up {len(filenames_to_replace)} old files from Drive folder...")
            
            for filename in filenames_to_replace:
                existing_file = self._find_file_in_folder(filename)
                if existing_file:
                    file_id = existing_file['id']
                    if self.delete_file(file_id):
                        deleted_count += 1
                        self.logger.info(f"Cleaned up old file: {filename}")
                    else:
                        self.logger.warning(f"Failed to clean up: {filename}")
                else:
                    self.logger.debug(f"File not found in Drive (nothing to clean): {filename}")
            
            self.logger.info(f"Successfully cleaned up {deleted_count} old files")
            return deleted_count
            
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")
            return deleted_count
    
    def list_files_in_folder(self) -> List[Dict[str, str]]:
        """List all files in the output folder"""
        try:
            query = f"parents='{self.output_folder_id}'"
            results = self.service.files().list(
                q=query,
                fields='files(id,name,createdTime,size,webViewLink)'
            ).execute()
            
            files = results.get('files', [])
            self.logger.info(f"Found {len(files)} files in output folder")
            
            return files
            
        except Exception as e:
            self.logger.error(f"Failed to list files: {e}")
            return []
    
    def get_folder_info(self) -> Dict[str, str]:
        """Get information about the output folder"""
        try:
            folder = self.service.files().get(
                fileId=self.output_folder_id,
                fields='id,name,webViewLink,createdTime'
            ).execute()
            
            return {
                'id': folder.get('id'),
                'name': folder.get('name'),
                'url': folder.get('webViewLink'),
                'created': folder.get('createdTime')
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get folder info: {e}")
            return {}
    
    def retry_upload(self, file_path: str, max_retries: int = None) -> Dict[str, str]:
        """Retry file upload with exponential backoff"""
        if max_retries is None:
            max_retries = self.config['error_handling']['max_retries']
        
        delay = self.config['error_handling']['retry_delay']
        
        for attempt in range(max_retries):
            try:
                return self.upload_file(file_path)
            except Exception as e:
                if attempt == max_retries - 1:
                    raise e
                
                wait_time = delay * (2 ** attempt)  # Exponential backoff
                self.logger.warning(f"Upload failed (attempt {attempt + 1}), retrying in {wait_time}s: {e}")
                time.sleep(wait_time)


def main():
    """Main function for testing"""
    try:
        # Initialize uploader
        uploader = GoogleDriveUploader()
        
        # Get folder info
        folder_info = uploader.get_folder_info()
        print(f"Output folder: {folder_info}")
        
        # List existing files
        files = uploader.list_files_in_folder()
        print(f"Existing files: {len(files)}")
        
        # Test upload (if JSON file exists)
        test_file = "C:\\Users\\Admin\\Downloads\\csv2json\\MSA091.json"
        if os.path.exists(test_file):
            result = uploader.upload_file(test_file)
            print(f"Upload result: {result}")
        else:
            print(f"Test file not found: {test_file}")
        
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()