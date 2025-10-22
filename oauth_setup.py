#!/usr/bin/env python3
"""
OAuth Setup Instructions for CSV to JSON Converter

This script provides step-by-step instructions for setting up OAuth authentication
to replace the service account authentication that doesn't work for Google Drive uploads.
"""

import os

def print_setup_instructions():
    print("=" * 70)
    print("🔧 OAUTH SETUP INSTRUCTIONS")
    print("=" * 70)
    print()
    
    print("You need to switch from Service Account to OAuth authentication.")
    print("This will allow uploading files to your personal Google Drive.")
    print()
    
    print("📋 STEP-BY-STEP SETUP:")
    print()
    
    print("1. 🌐 Go to Google Cloud Console:")
    print("   https://console.cloud.google.com/")
    print()
    
    print("2. 📁 Select your existing project (or create new one)")
    print()
    
    print("3. 🔑 Create OAuth Credentials:")
    print("   - Go to 'APIs & Services' > 'Credentials'")
    print("   - Click 'Create Credentials' > 'OAuth client ID'")
    print("   - Select 'Desktop Application'")
    print("   - Name: 'CSV2JSON Converter'")
    print("   - Click 'Create'")
    print()
    
    print("4. 💾 Download Credentials:")
    print("   - Click 'Download JSON' for your new OAuth client")
    print("   - Save as 'client_secret.json' in this directory")
    print(f"   - Location: {os.path.abspath('.')}")
    print()
    
    print("5. 🔄 Run the converter:")
    print("   - First run will open browser for authentication")
    print("   - Login and grant permissions")
    print("   - Future runs will use saved token")
    print()
    
    print("6. 🗑️  Clean up (optional):")
    print("   - You can delete 'credentials.json' (service account)")
    print("   - Keep 'client_secret.json' and 'token.json'")
    print()
    
    print("=" * 70)
    print("📁 FILE STATUS CHECK:")
    print("=" * 70)
    
    files_to_check = [
        ('credentials.json', 'Service Account (old)', '❌ Will be replaced'),
        ('client_secret.json', 'OAuth Client (new)', '✅ Required'),
        ('token.json', 'OAuth Token (auto-generated)', '📝 Created after first auth')
    ]
    
    for filename, description, status in files_to_check:
        exists = "✅ Found" if os.path.exists(filename) else "❌ Missing"
        print(f"  {filename:<20} - {description:<25} - {exists}")
    
    print()
    
    if os.path.exists('client_secret.json'):
        print("🎉 Great! You have OAuth credentials ready.")
        print("   Run: python main.py --process")
    else:
        print("⚠️  You need to create 'client_secret.json' first.")
        print("   Follow steps 1-4 above.")
    
    print()
    print("=" * 70)


if __name__ == "__main__":
    print_setup_instructions()