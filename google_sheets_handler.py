"""
Google Sheets Handler for CSV to JSON Converter
Handles reading CSV links from Google Sheets and updating with JSON URLs
"""

import gspread
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
import logging
from typing import List, Dict, Tuple, Optional
import re
import time
import yaml
import os


class GoogleSheetsHandler:
    """Handles Google Sheets operations for the CSV to JSON converter"""
    
    def __init__(self, config_path: str = "config.yaml"):
        """Initialize with configuration"""
        self.config = self._load_config(config_path)
        self.logger = self._setup_logging()
        self.client = None
        self.spreadsheet = None
        self.worksheet = None
        self._authenticate()
    
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
        """Authenticate with Google Sheets API using OAuth"""
        try:
            # Define the scope for Google Sheets and Google Drive
            scopes = [
                'https://www.googleapis.com/auth/spreadsheets',
                'https://www.googleapis.com/auth/drive'
            ]
            
            creds = None
            token_path = 'token.json'
            credentials_path = self.config['google_sheets']['credentials_path']
            
            # The file token.json stores the user's access and refresh tokens.
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
            
            # Create client
            self.client = gspread.authorize(creds)
            self.logger.info("Successfully authenticated with Google Sheets API using OAuth")
            
            # Open spreadsheet
            self._open_spreadsheet()
            
        except FileNotFoundError:
            raise FileNotFoundError(f"Credentials file not found: {credentials_path}")
        except Exception as e:
            self.logger.error(f"Authentication failed: {e}")
            raise
    
    def _open_spreadsheet(self):
        """Open the configured spreadsheet and worksheet"""
        try:
            spreadsheet_url = self.config['google_sheets']['spreadsheet_url']
            worksheet_name = self.config['google_sheets']['worksheet_name']
            
            # Extract spreadsheet ID from URL
            spreadsheet_id = self._extract_spreadsheet_id(spreadsheet_url)
            
            # Open spreadsheet
            self.spreadsheet = self.client.open_by_key(spreadsheet_id)
            self.logger.info(f"Opened spreadsheet: {self.spreadsheet.title}")
            
            # Open worksheet
            self.worksheet = self.spreadsheet.worksheet(worksheet_name)
            self.logger.info(f"Opened worksheet: {worksheet_name}")
            
        except gspread.WorksheetNotFound:
            raise ValueError(f"Worksheet '{worksheet_name}' not found in spreadsheet")
        except gspread.SpreadsheetNotFound:
            raise ValueError(f"Spreadsheet not found or not accessible")
        except Exception as e:
            self.logger.error(f"Failed to open spreadsheet: {e}")
            raise
    
    def _extract_spreadsheet_id(self, url: str) -> str:
        """Extract spreadsheet ID from Google Sheets URL"""
        # Pattern to match Google Sheets URL
        pattern = r'/spreadsheets/d/([a-zA-Z0-9-_]+)'
        match = re.search(pattern, url)
        
        if match:
            return match.group(1)
        else:
            raise ValueError(f"Invalid Google Sheets URL: {url}")
    
    def get_csv_links(self) -> List[Dict[str, str]]:
        """Get all CSV links from the configured column"""
        try:
            csv_column = self.config['google_sheets']['csv_link_column']
            json_column = self.config['google_sheets']['json_link_column']
            
            # Define expected headers to handle duplicate empty headers
            expected_headers = [csv_column, json_column]
            
            # Get all values from the worksheet with expected headers
            try:
                all_values = self.worksheet.get_all_records(expected_headers=expected_headers)
            except Exception as header_error:
                self.logger.warning(f"Failed to use expected_headers, trying alternative approach: {header_error}")
                # Fallback: get all values as raw data and process manually
                all_data = self.worksheet.get_all_values()
                if not all_data:
                    self.logger.error("No data found in worksheet")
                    return []
                
                # Use first row as headers, handling duplicates
                headers = all_data[0]
                processed_headers = []
                for i, header in enumerate(headers):
                    if header.strip():
                        processed_headers.append(header.strip())
                    else:
                        processed_headers.append(f"empty_col_{i}")
                
                # Convert to list of dictionaries
                all_values = []
                for row_data in all_data[1:]:
                    row_dict = {}
                    for i, value in enumerate(row_data):
                        if i < len(processed_headers):
                            row_dict[processed_headers[i]] = value
                    all_values.append(row_dict)
            
            csv_links = []
            for i, row in enumerate(all_values, start=2):  # Start from row 2 (after header)
                csv_link = row.get(csv_column, '').strip()
                
                if csv_link and self._is_valid_csv_link(csv_link):
                    csv_links.append({
                        'row_number': i,
                        'csv_url': csv_link,
                        'json_url': row.get(json_column, '').strip()
                    })
            
            self.logger.info(f"Found {len(csv_links)} CSV links in spreadsheet")
            return csv_links
            
        except Exception as e:
            self.logger.error(f"Failed to get CSV links: {e}")
            raise
    
    def _is_valid_csv_link(self, url: str) -> bool:
        """Check if URL is a valid CSV link"""
        if not url:
            return False
        
        # Check for Google Drive CSV links or direct CSV URLs
        csv_patterns = [
            r'drive\.google\.com.*\.csv',
            r'.*\.csv$',
            r'drive\.google\.com/file/d/.*',  # Google Drive file links
        ]
        
        return any(re.search(pattern, url, re.IGNORECASE) for pattern in csv_patterns)
    
    def update_json_link(self, row_number: int, json_url: str) -> bool:
        """Update the JSON link column for a specific row"""
        try:
            json_column = self.config['google_sheets']['json_link_column']
            
            # Find the column index for the JSON link column
            headers = self.worksheet.row_values(1)
            
            if json_column not in headers:
                self.logger.error(f"JSON column '{json_column}' not found in headers")
                return False
            
            json_column_index = headers.index(json_column) + 1  # gspread uses 1-based indexing
            
            # Update the cell
            self.worksheet.update_cell(row_number, json_column_index, json_url)
            self.logger.info(f"Updated row {row_number} with JSON URL: {json_url}")
            
            # Add a small delay to avoid hitting API limits
            time.sleep(0.5)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to update JSON link for row {row_number}: {e}")
            return False
    
    def update_multiple_json_links(self, updates: List[Tuple[int, str]]) -> int:
        """Update multiple JSON links in batch"""
        success_count = 0
        
        for row_number, json_url in updates:
            if self.update_json_link(row_number, json_url):
                success_count += 1
            
            # Respect API rate limits
            time.sleep(0.1)
        
        self.logger.info(f"Successfully updated {success_count} out of {len(updates)} rows")
        return success_count
    
    def get_pending_conversions(self) -> List[Dict[str, str]]:
        """Get CSV links that don't have corresponding JSON links"""
        csv_links = self.get_csv_links()
        
        pending = [
            link for link in csv_links 
            if not link['json_url'] or link['json_url'] == ''
        ]
        
        self.logger.info(f"Found {len(pending)} pending conversions")
        return pending
    
    def validate_access(self) -> bool:
        """Validate that we have access to the spreadsheet"""
        try:
            # Try to read the title
            title = self.spreadsheet.title
            self.logger.info(f"Validated access to spreadsheet: {title}")
            return True
        except Exception as e:
            self.logger.error(f"Access validation failed: {e}")
            return False
    
    def get_worksheet_info(self) -> Dict[str, any]:
        """Get information about the current worksheet"""
        try:
            info = {
                'title': self.worksheet.title,
                'row_count': self.worksheet.row_count,
                'col_count': self.worksheet.col_count,
                'headers': self.worksheet.row_values(1) if self.worksheet.row_count > 0 else []
            }
            
            self.logger.info(f"Worksheet info: {info}")
            return info
            
        except Exception as e:
            self.logger.error(f"Failed to get worksheet info: {e}")
            return {}
    
    def create_backup_sheet(self, backup_name: str = None) -> str:
        """Create a backup of the current worksheet"""
        try:
            if backup_name is None:
                from datetime import datetime
                backup_name = f"Backup_{self.worksheet.title}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # Duplicate the worksheet
            backup_sheet = self.spreadsheet.duplicate_sheet(
                self.worksheet.id,
                new_sheet_name=backup_name
            )
            
            self.logger.info(f"Created backup sheet: {backup_name}")
            return backup_name
            
        except Exception as e:
            self.logger.error(f"Failed to create backup: {e}")
            raise
    
    def retry_operation(self, operation, max_retries: int = None, delay: float = None):
        """Retry an operation with exponential backoff"""
        if max_retries is None:
            max_retries = self.config['error_handling']['max_retries']
        if delay is None:
            delay = self.config['error_handling']['retry_delay']
        
        for attempt in range(max_retries):
            try:
                return operation()
            except Exception as e:
                if attempt == max_retries - 1:
                    raise e
                
                wait_time = delay * (2 ** attempt)  # Exponential backoff
                self.logger.warning(f"Operation failed (attempt {attempt + 1}), retrying in {wait_time}s: {e}")
                time.sleep(wait_time)


def main():
    """Main function for testing"""
    try:
        # Initialize handler
        sheets_handler = GoogleSheetsHandler()
        
        # Validate access
        if not sheets_handler.validate_access():
            print("Failed to access Google Sheets")
            return
        
        # Get worksheet info
        info = sheets_handler.get_worksheet_info()
        print(f"Worksheet info: {info}")
        
        # Get pending conversions
        pending = sheets_handler.get_pending_conversions()
        print(f"Pending conversions: {len(pending)}")
        
        for item in pending[:3]:  # Show first 3 pending items
            print(f"Row {item['row_number']}: {item['csv_url']}")
        
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()