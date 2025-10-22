"""
List available worksheets in the Google Spreadsheet
"""

import gspread
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
import os

def list_worksheets():
    """List all worksheets in the configured spreadsheet"""
    
    # Set up OAuth2 authentication
    SCOPES = [
        'https://www.googleapis.com/auth/spreadsheets.readonly',
        'https://www.googleapis.com/auth/drive.readonly'
    ]
    
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('client_secret.json', SCOPES)
            creds = flow.run_local_server(port=0)
        
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    
    # Connect to Google Sheets
    gc = gspread.authorize(creds)
    
    # Open the spreadsheet
    spreadsheet_url = "https://docs.google.com/spreadsheets/d/1uJ9TS3F8pqlUcbzBcCxCYB4t9uaoJdd8kWr8nH8xNt4/edit?gid=613684105#gid=613684105"
    spreadsheet = gc.open_by_url(spreadsheet_url)
    
    print(f"Spreadsheet: {spreadsheet.title}")
    print("\nAvailable worksheets:")
    for i, worksheet in enumerate(spreadsheet.worksheets()):
        print(f"  {i+1}. {worksheet.title} (ID: {worksheet.id})")
    
    return spreadsheet.worksheets()

if __name__ == "__main__":
    list_worksheets()