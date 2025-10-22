#!/usr/bin/env python3
"""
Main orchestrator for CSV to JSON Converter
Coordinates the entire workflow from reading Google Sheets to uploading JSON files
"""

import os
import sys
import logging
import requests
from typing import List, Dict, Any
from urllib.parse import urlparse
import time

from csv2json_converter import CSV2JSONConverter
from google_sheets_handler import GoogleSheetsHandler
from drive_uploader import GoogleDriveUploader


class CSV2JSONOrchestrator:
    """Main orchestrator class that coordinates the entire workflow"""
    
    def __init__(self, config_path: str = "config.yaml"):
        """Initialize the orchestrator"""
        self.config_path = config_path
        self.logger = self._setup_logging()
        
        # Initialize components
        self.converter = CSV2JSONConverter(config_path)
        self.sheets_handler = GoogleSheetsHandler(config_path) 
        self.drive_uploader = GoogleDriveUploader(config_path)
        
        # Create local directories for input and output
        self.project_dir = os.path.dirname(os.path.abspath(config_path))
        self.input_csv_dir = os.path.join(self.project_dir, "input_csv")
        self.output_json_dir = os.path.join(self.project_dir, "output_jsons")
        
        # Ensure directories exist
        os.makedirs(self.input_csv_dir, exist_ok=True)
        os.makedirs(self.output_json_dir, exist_ok=True)
        
        self.logger.info(f"Using input CSV directory: {self.input_csv_dir}")
        self.logger.info(f"Using output JSON directory: {self.output_json_dir}")
    
    def _setup_logging(self) -> logging.Logger:
        """Setup logging for the orchestrator"""
        logger = logging.getLogger(__name__)
        logger.setLevel(logging.INFO)
        
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
        return logger
    
    def download_csv_from_url(self, url: str, filename: str) -> str:
        """Download CSV file from URL to input_csv directory"""
        try:
            self.logger.info(f"Downloading CSV from: {url}")
            
            # Handle Google Drive URLs
            if 'drive.google.com' in url:
                url = self._convert_google_drive_url(url)
            
            # Download the file
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            # Save to input_csv directory
            csv_path = os.path.join(self.input_csv_dir, filename)
            with open(csv_path, 'wb') as f:
                f.write(response.content)
            
            self.logger.info(f"Downloaded CSV to: {csv_path}")
            return csv_path
            
        except Exception as e:
            self.logger.error(f"Failed to download CSV from {url}: {e}")
            raise
    
    def _convert_google_drive_url(self, url: str) -> str:
        """Convert Google Drive sharing URL to direct download URL"""
        # Extract file ID from various Google Drive URL formats
        file_id = None
        
        if '/file/d/' in url:
            # Format: https://drive.google.com/file/d/FILE_ID/view
            file_id = url.split('/file/d/')[1].split('/')[0]
        elif 'id=' in url:
            # Format: https://drive.google.com/open?id=FILE_ID
            file_id = url.split('id=')[1].split('&')[0]
        
        if file_id:
            # Convert to direct download URL
            return f"https://drive.google.com/uc?export=download&id={file_id}"
        
        return url  # Return original if conversion fails
    
    def process_single_csv(self, csv_info: Dict[str, Any]) -> Dict[str, Any]:
        """Process a single CSV file through the entire workflow"""
        result = {
            'row_number': csv_info['row_number'],
            'csv_url': csv_info['csv_url'],
            'json_urls': [],
            'success': False,
            'error': None
        }
        
        try:
            # Generate filename for CSV
            parsed_url = urlparse(csv_info['csv_url'])
            csv_filename = os.path.basename(parsed_url.path) or f"conversation_{csv_info['row_number']}.csv"
            
            # Ensure .csv extension
            if not csv_filename.endswith('.csv'):
                csv_filename += '.csv'
            
            # Download CSV
            local_csv_path = self.download_csv_from_url(csv_info['csv_url'], csv_filename)
            
            # Convert CSV to JSON (output to local directory)
            json_files = self.converter.convert_csv_to_json(local_csv_path, self.output_json_dir)
            
            if not json_files:
                raise ValueError("No JSON files were generated")
            
            # Files are now saved to local cache, now upload to Google Drive
            json_urls = []
            upload_enabled = self.converter.config.get('google_drive', {}).get('enable_upload', True)
            
            if upload_enabled:
                try:
                    # Clean up old files first (extract just filenames)
                    filenames_to_replace = [os.path.basename(json_file) for json_file in json_files]
                    cleanup_count = self.drive_uploader.cleanup_old_files(filenames_to_replace)
                    if cleanup_count > 0:
                        self.logger.info(f"Cleaned up {cleanup_count} old files from Drive before uploading new ones")
                    
                    self.logger.info(f"Uploading {len(json_files)} JSON files to Google Drive...")
                    # Force upload since we may have cleaned up old versions
                    upload_results = self.drive_uploader.upload_multiple_files(json_files, force_upload=True)
                    
                    # Extract shareable URLs
                    for upload_result in upload_results:
                        if upload_result.get('shareable_url'):
                            json_urls.append(upload_result['shareable_url'])
                            self.logger.info(f"Successfully uploaded: {upload_result.get('filename')} -> {upload_result.get('shareable_url')}")
                        elif upload_result.get('error'):
                            self.logger.error(f"Upload failed for {upload_result.get('filename', 'unknown')}: {upload_result['error']}")
                    
                    if json_urls:
                        self.logger.info(f"Successfully uploaded {len(json_urls)} out of {len(json_files)} files to Google Drive")
                    else:
                        raise ValueError("No files were successfully uploaded to Google Drive")
                    
                except Exception as e:
                    self.logger.error(f"Google Drive upload failed: {e}")
                    raise ValueError(f"Failed to upload to Google Drive: {e}")
            else:
                self.logger.info("Google Drive upload disabled - skipping upload")
                raise ValueError("Google Drive upload is disabled")
            
            # Use Google Drive URLs for updating the sheet
            result['json_urls'] = json_urls
            result['success'] = True
            primary_json_url = json_urls[0] if len(json_urls) == 1 else ', '.join(json_urls)
            
            # Update Google Sheets with the Google Drive URL
            self.sheets_handler.update_json_link(csv_info['row_number'], primary_json_url)
            
            self.logger.info(f"Successfully processed row {csv_info['row_number']}")
            self.logger.info(f"JSON files created locally: {[os.path.basename(f) for f in json_files]}")
            self.logger.info(f"Updated Google Sheets with Drive URL: {primary_json_url}")
            
        except Exception as e:
            result['error'] = str(e)
            self.logger.error(f"Failed to process row {csv_info['row_number']}: {e}")
        
        return result
    
    def process_all_pending(self) -> Dict[str, Any]:
        """Process all pending CSV conversions"""
        self.logger.info("Starting batch processing of pending conversions")
        
        # Get pending conversions
        pending_conversions = self.sheets_handler.get_pending_conversions()
        
        if not pending_conversions:
            self.logger.info("No pending conversions found")
            return {
                'total': 0,
                'processed': 0,
                'successful': 0,
                'failed': 0,
                'results': []
            }
        
        self.logger.info(f"Found {len(pending_conversions)} pending conversions")
        
        # Process each conversion
        results = []
        successful = 0
        failed = 0
        
        max_files = self.converter.config['processing']['max_files_per_batch']
        if max_files > 0 and len(pending_conversions) > max_files:
            pending_conversions = pending_conversions[:max_files]
            self.logger.info(f"Limited processing to {max_files} files per batch")
        
        for i, csv_info in enumerate(pending_conversions, 1):
            self.logger.info(f"Processing {i}/{len(pending_conversions)}: Row {csv_info['row_number']}")
            
            result = self.process_single_csv(csv_info)
            results.append(result)
            
            if result['success']:
                successful += 1
            else:
                failed += 1
                
                # Stop processing if continue_on_error is False
                if not self.converter.config['error_handling']['continue_on_error']:
                    self.logger.error("Stopping processing due to error and continue_on_error=False")
                    break
            
            # Add delay between processing
            if i < len(pending_conversions):  # Don't sleep after the last item
                time.sleep(1)
        
        summary = {
            'total': len(pending_conversions),
            'processed': len(results),
            'successful': successful,
            'failed': failed,
            'results': results
        }
        
        self.logger.info(f"Batch processing completed: {successful} successful, {failed} failed")
        return summary
    
    def validate_setup(self) -> bool:
        """Validate that all components are properly configured"""
        self.logger.info("Validating setup...")
        
        try:
            # Test Google Sheets access
            if not self.sheets_handler.validate_access():
                self.logger.error("Google Sheets validation failed")
                return False
            
            # Test Google Drive access
            folder_info = self.drive_uploader.get_folder_info()
            if not folder_info.get('id'):
                self.logger.error("Google Drive validation failed")
                return False
            
            self.logger.info("Setup validation successful")
            return True
            
        except Exception as e:
            self.logger.error(f"Setup validation failed: {e}")
            return False
    
    def get_status_report(self) -> Dict[str, Any]:
        """Generate a status report of the current state"""
        try:
            # Get worksheet info
            worksheet_info = self.sheets_handler.get_worksheet_info()
            
            # Get pending conversions
            pending = self.sheets_handler.get_pending_conversions()
            
            # Get Drive folder info
            folder_info = self.drive_uploader.get_folder_info()
            drive_files = self.drive_uploader.list_files_in_folder()
            
            report = {
                'worksheet': {
                    'title': worksheet_info.get('title'),
                    'total_rows': worksheet_info.get('row_count', 0) - 1,  # Subtract header row
                    'headers': worksheet_info.get('headers', [])
                },
                'pending_conversions': len(pending),
                'drive_folder': {
                    'name': folder_info.get('name'),
                    'url': folder_info.get('url'),
                    'total_files': len(drive_files)
                },
                'configuration': {
                    'csv_column': self.converter.config['google_sheets']['csv_link_column'],
                    'json_column': self.converter.config['google_sheets']['json_link_column'],
                    'batch_size': self.converter.config['processing']['max_files_per_batch'],
                    'skip_existing': self.converter.config['processing']['skip_existing']
                }
            }
            
            return report
            
        except Exception as e:
            self.logger.error(f"Failed to generate status report: {e}")
            return {'error': str(e)}
    
    def _update_drive_setting(self, enabled: bool):
        """Update Google Drive upload setting in config file"""
        try:
            import yaml
            
            # Load current config
            with open(self.config_path, 'r', encoding='utf-8') as file:
                config = yaml.safe_load(file)
            
            # Update setting
            if 'google_drive' not in config:
                config['google_drive'] = {}
            config['google_drive']['enable_upload'] = enabled
            
            # Save config
            with open(self.config_path, 'w', encoding='utf-8') as file:
                yaml.dump(config, file, default_flow_style=False, indent=2)
            
            self.logger.info(f"Updated Google Drive upload setting to: {enabled}")
            
        except Exception as e:
            self.logger.error(f"Failed to update config: {e}")
    
    def cleanup(self):
        """Clean up any temporary files (local directories are preserved)"""
        self.logger.info("Cleanup completed - local files preserved in input_csv and output_jsons directories")


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='CSV to JSON Converter with Google Sheets integration')
    parser.add_argument('--config', default='config.yaml', help='Path to configuration file')
    parser.add_argument('--validate', action='store_true', help='Validate setup and exit')
    parser.add_argument('--status', action='store_true', help='Show status report and exit')
    parser.add_argument('--process', action='store_true', help='Process all pending conversions')
    parser.add_argument('--enable-drive', action='store_true', help='Enable Google Drive uploads')
    parser.add_argument('--disable-drive', action='store_true', help='Disable Google Drive uploads')
    
    args = parser.parse_args()
    
    try:
        # Initialize orchestrator
        orchestrator = CSV2JSONOrchestrator(args.config)
        
        if args.validate:
            # Validate setup
            success = orchestrator.validate_setup()
            sys.exit(0 if success else 1)
        
        elif args.status:
            # Show status report
            report = orchestrator.get_status_report()
            print("\n=== Status Report ===")
            print(f"Worksheet: {report.get('worksheet', {}).get('title', 'Unknown')}")
            print(f"Total rows: {report.get('worksheet', {}).get('total_rows', 0)}")
            print(f"Pending conversions: {report.get('pending_conversions', 0)}")
            print(f"Drive folder: {report.get('drive_folder', {}).get('name', 'Unknown')}")
            print(f"Files in folder: {report.get('drive_folder', {}).get('total_files', 0)}")
            print("=" * 20)
        
        elif args.enable_drive:
            # Enable Google Drive uploads
            orchestrator._update_drive_setting(True)
            print("Google Drive uploads enabled")
            
        elif args.disable_drive:
            # Disable Google Drive uploads
            orchestrator._update_drive_setting(False)
            print("Google Drive uploads disabled")
            
        elif args.process:
            # Validate setup first
            if not orchestrator.validate_setup():
                print("Setup validation failed. Please check configuration and credentials.")
                sys.exit(1)
            
            # Process all pending conversions
            summary = orchestrator.process_all_pending()
            
            print("\n=== Processing Summary ===")
            print(f"Total: {summary['total']}")
            print(f"Processed: {summary['processed']}")
            print(f"Successful: {summary['successful']}")
            print(f"Failed: {summary['failed']}")
            print("=" * 25)
            
            # Show failed conversions
            failed_results = [r for r in summary['results'] if not r['success']]
            if failed_results:
                print("\nFailed conversions:")
                for result in failed_results:
                    print(f"Row {result['row_number']}: {result['error']}")
        
        else:
            # Default: show help
            parser.print_help()
        
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
    finally:
        if 'orchestrator' in locals():
            orchestrator.cleanup()


if __name__ == "__main__":
    main()