"""
Fix CSV download links by converting Google Drive view URLs to direct download URLs
"""

import re
import requests
import pandas as pd
from google_sheets_handler import GoogleSheetsHandler
import yaml
from urllib.parse import urlparse, parse_qs

def convert_google_drive_url(url):
    """
    Convert Google Drive sharing URL to direct download URL
    
    Converts:
    - https://drive.google.com/file/d/FILE_ID/view?usp=sharing
    - https://drive.google.com/open?id=FILE_ID
    
    To:
    - https://drive.google.com/uc?export=download&id=FILE_ID
    """
    if not url or not isinstance(url, str):
        return url
        
    # Pattern 1: drive.google.com/file/d/FILE_ID/view
    pattern1 = r'https://drive\.google\.com/file/d/([a-zA-Z0-9_-]+)/view'
    match1 = re.search(pattern1, url)
    if match1:
        file_id = match1.group(1)
        return f"https://drive.google.com/uc?export=download&id={file_id}"
    
    # Pattern 2: drive.google.com/open?id=FILE_ID
    pattern2 = r'https://drive\.google\.com/open\?id=([a-zA-Z0-9_-]+)'
    match2 = re.search(pattern2, url)
    if match2:
        file_id = match2.group(1)
        return f"https://drive.google.com/uc?export=download&id={file_id}"
    
    # Pattern 3: Already a direct download URL
    if 'drive.google.com/uc?export=download' in url:
        return url
    
    # If no pattern matches, return original URL
    print(f"Warning: Could not convert URL: {url}")
    return url

def test_csv_download(url, max_preview_lines=3):
    """
    Test downloading CSV from URL and preview first few lines
    """
    try:
        # Convert to direct download URL if it's a Google Drive link
        download_url = convert_google_drive_url(url)
        print(f"Testing download from: {download_url}")
        
        response = requests.get(download_url, timeout=30)
        response.raise_for_status()
        
        content = response.text
        lines = content.split('\n')
        
        print(f"Downloaded {len(content)} characters, {len(lines)} lines")
        print(f"First {max_preview_lines} lines:")
        for i, line in enumerate(lines[:max_preview_lines]):
            print(f"  Line {i+1}: {line[:100]}{'...' if len(line) > 100 else ''}")
        
        # Test if it's actually CSV content
        if content.startswith('<!DOCTYPE html>'):
            print("❌ Still getting HTML content!")
            return False
        else:
            print("✅ Looks like proper CSV content")
            return True
            
    except Exception as e:
        print(f"❌ Error downloading: {e}")
        return False

def fix_problematic_csvs():
    """
    Test and fix the problematic CSV files we identified
    """
    print("=== Fixing Problematic CSV Downloads ===\n")
    
    # Load config
    with open('config.yaml', 'r') as f:
        config = yaml.safe_load(f)
    
    # Initialize handler
    handler = GoogleSheetsHandler()
    
    # Get the spreadsheet data
    csv_links = handler.get_csv_links()
    
    # Debug: Check what keys are available
    if csv_links:
        print(f"Available keys in row data: {list(csv_links[0].keys())}")
    
    # Test the problematic rows (17 and 21 - adjust for 0-based indexing)
    problematic_rows = [16, 20]  # 0-based indices for rows 17 and 21
    
    for row_idx in problematic_rows:
        if row_idx < len(csv_links):
            row = csv_links[row_idx]
            # Use the correct key names from the debug output
            csv_link = row.get('csv_url')
            row_num = row.get('row_number', row_idx + 1)
            
            if not csv_link:
                print(f"Row {row_num}: No CSV URL found, skipping")
                continue
            
            print(f"Row {row_num}: CSV URL found")
            print(f"Original URL: {csv_link}")
            
            # Convert URL
            fixed_url = convert_google_drive_url(csv_link)
            print(f"Fixed URL: {fixed_url}")
            
            # Test download
            success = test_csv_download(fixed_url)
            print(f"Download test: {'✅ Success' if success else '❌ Failed'}")
            print("-" * 80)
    
    return True

if __name__ == "__main__":
    fix_problematic_csvs()