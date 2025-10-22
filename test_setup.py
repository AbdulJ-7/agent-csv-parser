#!/usr/bin/env python3
"""
Test script for CSV to JSON Converter
Run this to validate your setup and test basic functionality
"""

import os
import sys
import tempfile
import json
from datetime import datetime


def test_imports():
    """Test that all required modules can be imported"""
    print("Testing imports...")
    
    try:
        import pandas as pd
        print("✓ pandas")
    except ImportError as e:
        print(f"✗ pandas: {e}")
        return False
    
    try:
        import yaml
        print("✓ PyYAML")
    except ImportError as e:
        print(f"✗ PyYAML: {e}")
        return False
    
    try:
        import gspread
        print("✓ gspread")
    except ImportError as e:
        print(f"✗ gspread: {e}")
        return False
    
    try:
        from google.oauth2.service_account import Credentials
        print("✓ google-auth")
    except ImportError as e:
        print(f"✗ google-auth: {e}")
        return False
    
    try:
        from googleapiclient.discovery import build
        print("✓ google-api-python-client")
    except ImportError as e:
        print(f"✗ google-api-python-client: {e}")
        return False
    
    print("All imports successful!\n")
    return True


def test_config_file():
    """Test that configuration file exists and is valid"""
    print("Testing configuration file...")
    
    config_path = "config.yaml"
    if not os.path.exists(config_path):
        print(f"✗ Configuration file not found: {config_path}")
        return False
    
    try:
        import yaml
        with open(config_path, 'r', encoding='utf-8') as file:
            config = yaml.safe_load(file)
        
        # Check required sections
        required_sections = ['google_sheets', 'google_drive', 'csv_processing', 'json_output']
        for section in required_sections:
            if section not in config:
                print(f"✗ Missing configuration section: {section}")
                return False
        
        print("✓ Configuration file is valid")
        return True
        
    except Exception as e:
        print(f"✗ Configuration file error: {e}")
        return False


def test_credentials_file():
    """Test that credentials file exists"""
    print("Testing credentials file...")
    
    credentials_path = "credentials.json"
    if not os.path.exists(credentials_path):
        print(f"✗ Credentials file not found: {credentials_path}")
        print("  Please follow the setup instructions in README.md to create credentials.json")
        return False
    
    try:
        with open(credentials_path, 'r', encoding='utf-8') as file:
            creds = json.load(file)
        
        # Check for required fields
        required_fields = ['type', 'project_id', 'private_key', 'client_email']
        for field in required_fields:
            if field not in creds:
                print(f"✗ Missing field in credentials: {field}")
                return False
        
        if creds.get('type') != 'service_account':
            print("✗ Credentials type should be 'service_account'")
            return False
        
        print("✓ Credentials file is valid")
        return True
        
    except Exception as e:
        print(f"✗ Credentials file error: {e}")
        return False


def test_csv_conversion():
    """Test CSV to JSON conversion with sample data"""
    print("Testing CSV to JSON conversion...")
    
    try:
        # Create sample CSV data
        sample_csv = """id,session_id,role,content,timestamp,event_type,model_used
1,test_session_123,user,"Hello, how are you?",2025-10-13T13:08:56.778810Z,user_message,
2,test_session_123,assistant,"I'm doing well, thank you!",2025-10-13T13:08:58.123456Z,ai_response,gpt-4o-mini
3,test_session_123,user,"What's the weather like?",2025-10-13T13:09:00.000000Z,user_message,
4,test_session_123,assistant,"I don't have access to real-time weather data.",2025-10-13T13:09:02.500000Z,ai_response,gpt-4o-mini"""
        
        # Write to temporary CSV file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(sample_csv)
            temp_csv_path = f.name
        
        # Test conversion
        from csv2json_converter import CSV2JSONConverter
        converter = CSV2JSONConverter()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            json_files = converter.convert_csv_to_json(temp_csv_path, temp_dir)
            
            if json_files:
                print(f"✓ Successfully converted CSV to {len(json_files)} JSON file(s)")
                
                # Validate JSON structure
                with open(json_files[0], 'r', encoding='utf-8') as f:
                    json_data = json.load(f)
                
                if 'messages' in json_data and len(json_data['messages']) > 0:
                    print("✓ JSON structure is valid")
                    print(f"  Generated {len(json_data['messages'])} messages")
                    return True
                else:
                    print("✗ Invalid JSON structure")
                    return False
            else:
                print("✗ No JSON files generated")
                return False
        
        # Cleanup
        os.unlink(temp_csv_path)
        
    except Exception as e:
        print(f"✗ CSV conversion test failed: {e}")
        return False


def test_google_apis():
    """Test Google APIs connectivity (if credentials are available)"""
    print("Testing Google APIs connectivity...")
    
    if not os.path.exists("credentials.json"):
        print("⚠ Skipping Google APIs test (no credentials file)")
        return True
    
    try:
        # Test Google Sheets
        from google_sheets_handler import GoogleSheetsHandler
        sheets_handler = GoogleSheetsHandler()
        
        if sheets_handler.validate_access():
            print("✓ Google Sheets API connectivity successful")
        else:
            print("✗ Google Sheets API connectivity failed")
            return False
        
        # Test Google Drive  
        from drive_uploader import GoogleDriveUploader
        drive_uploader = GoogleDriveUploader()
        
        folder_info = drive_uploader.get_folder_info()
        if folder_info.get('id'):
            print("✓ Google Drive API connectivity successful")
            return True
        else:
            print("✗ Google Drive API connectivity failed")
            return False
        
    except Exception as e:
        print(f"✗ Google APIs test failed: {e}")
        return False


def main():
    """Run all tests"""
    print("CSV to JSON Converter - Setup Validation")
    print("=" * 40)
    
    tests = [
        ("Imports", test_imports),
        ("Configuration", test_config_file),
        ("Credentials", test_credentials_file),
        ("CSV Conversion", test_csv_conversion),
        ("Google APIs", test_google_apis),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n{test_name} Test:")
        try:
            result = test_func()
            results.append((test_name, result))
        except KeyboardInterrupt:
            print("\nTest interrupted by user")
            sys.exit(1)
        except Exception as e:
            print(f"✗ Unexpected error: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 40)
    print("TEST SUMMARY:")
    
    passed = 0
    for test_name, result in results:
        status = "PASS" if result else "FAIL"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\nPassed: {passed}/{len(results)} tests")
    
    if passed == len(results):
        print("✓ All tests passed! Your setup is ready to use.")
        print("\nNext steps:")
        print("1. Update config.yaml with your Google Sheet URL")
        print("2. Run: python main.py --status")
        print("3. Run: python main.py --process")
    else:
        print("✗ Some tests failed. Please check the errors above.")
        print("Refer to README.md for setup instructions.")
        sys.exit(1)


if __name__ == "__main__":
    main()