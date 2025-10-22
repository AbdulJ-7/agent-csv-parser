#!/usr/bin/env python3
"""
CSV Diagnostic Tool
Analyzes problematic CSV files to identify parsing issues
"""

import pandas as pd
import csv
import sys
import os
from google_sheets_handler import GoogleSheetsHandler

def diagnose_csv_file(file_path):
    """Diagnose a specific CSV file for parsing issues"""
    print(f"\n{'='*60}")
    print(f"DIAGNOSING: {file_path}")
    print(f"{'='*60}")
    
    if not os.path.exists(file_path):
        print(f"❌ File not found: {file_path}")
        return
    
    try:
        # Check file size
        file_size = os.path.getsize(file_path)
        print(f"📁 File size: {file_size:,} bytes ({file_size/1024/1024:.2f} MB)")
        
        # Try to read first few lines manually
        print("\n📋 FIRST 5 LINES ANALYSIS:")
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            lines = []
            for i, line in enumerate(f):
                if i >= 5:
                    break
                lines.append(line.rstrip('\n\r'))
                field_count = len(line.split(','))
                print(f"Line {i+1}: {field_count:,} fields | Length: {len(line):,} chars")
                if i == 0:  # Header
                    print(f"   Header: {line[:100]}{'...' if len(line) > 100 else ''}")
                elif i <= 2:  # First couple data lines
                    print(f"   Sample: {line[:100]}{'...' if len(line) > 100 else ''}")
        
        # Check for inconsistent field counts
        print("\n🔍 FIELD COUNT ANALYSIS:")
        field_counts = {}
        line_count = 0
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            for i, line in enumerate(f):
                line_count += 1
                field_count = len(line.split(','))
                field_counts[field_count] = field_counts.get(field_count, 0) + 1
                if i >= 1000:  # Sample first 1000 lines
                    break
        
        print(f"Analyzed first {line_count:,} lines:")
        for count, frequency in sorted(field_counts.items()):
            print(f"  {count:,} fields: {frequency:,} lines ({frequency/line_count*100:.1f}%)")
        
        if len(field_counts) > 1:
            print("⚠️  INCONSISTENT FIELD COUNTS DETECTED!")
        
        # Try different parsing methods
        print("\n🧪 PARSING ATTEMPTS:")
        
        # Method 1: Default pandas
        try:
            df = pd.read_csv(file_path, nrows=10)
            print(f"✅ Default pandas: {len(df.columns)} columns, {len(df)} rows")
            print(f"   Columns: {list(df.columns)[:5]}{'...' if len(df.columns) > 5 else ''}")
        except Exception as e:
            print(f"❌ Default pandas failed: {str(e)[:100]}")
        
        # Method 2: With error handling
        try:
            df = pd.read_csv(file_path, nrows=10, on_bad_lines='skip')
            print(f"✅ Skip bad lines: {len(df.columns)} columns, {len(df)} rows")
        except Exception as e:
            print(f"❌ Skip bad lines failed: {str(e)[:100]}")
        
        # Method 3: Different separator
        try:
            df = pd.read_csv(file_path, nrows=10, sep=';')
            print(f"✅ Semicolon separator: {len(df.columns)} columns, {len(df)} rows")
        except Exception as e:
            print(f"❌ Semicolon separator failed: {str(e)[:100]}")
        
        # Method 4: Quote handling
        try:
            df = pd.read_csv(file_path, nrows=10, quoting=csv.QUOTE_NONE)
            print(f"✅ No quotes: {len(df.columns)} columns, {len(df)} rows")
        except Exception as e:
            print(f"❌ No quotes failed: {str(e)[:100]}")
        
        # Method 5: Custom engine
        try:
            df = pd.read_csv(file_path, nrows=10, engine='python')
            print(f"✅ Python engine: {len(df.columns)} columns, {len(df)} rows")
        except Exception as e:
            print(f"❌ Python engine failed: {str(e)[:100]}")
        
    except Exception as e:
        print(f"❌ Critical error during diagnosis: {e}")

def diagnose_from_sheets():
    """Download and diagnose problematic CSV files from Google Sheets"""
    print("🔍 DIAGNOSING CSV FILES FROM GOOGLE SHEETS")
    print("="*60)
    
    try:
        # Initialize sheets handler
        sheets_handler = GoogleSheetsHandler()
        csv_links = sheets_handler.get_csv_links()
        
        print(f"Found {len(csv_links)} CSV links in spreadsheet")
        
        # Find links that might be problematic (we'll check a few)
        for i, link_info in enumerate(csv_links[:20]):  # Check first 20
            row_num = link_info['row_number']
            csv_url = link_info['csv_url']
            print(f"\n📥 Downloading CSV {i+1}/20 from row {row_num}...")
            
            try:
                # Download CSV
                import requests
                response = requests.get(csv_url.replace('/view?usp=sharing', '/export?format=csv'))
                csv_path = f'temp_diagnosis_{row_num}.csv'
                
                with open(csv_path, 'wb') as f:
                    f.write(response.content)
                
                # Quick check if this might be problematic
                with open(csv_path, 'r', encoding='utf-8', errors='replace') as f:
                    first_line = f.readline()
                    second_line = f.readline()
                    third_line = f.readline()
                
                first_fields = len(first_line.split(','))
                second_fields = len(second_line.split(','))
                third_fields = len(third_line.split(','))
                
                if abs(first_fields - third_fields) > 100:  # Large field count difference
                    print(f"⚠️  POTENTIAL ISSUE DETECTED in row {row_num}!")
                    print(f"   Line 1: {first_fields} fields")
                    print(f"   Line 3: {third_fields} fields")
                    diagnose_csv_file(csv_path)
                    
                    # Keep this file for inspection
                    os.rename(csv_path, f'problematic_csv_row_{row_num}.csv')
                    print(f"💾 Saved problematic file as: problematic_csv_row_{row_num}.csv")
                else:
                    print(f"✅ Row {row_num} looks normal ({first_fields} fields)")
                    os.remove(csv_path)
                    
            except Exception as e:
                print(f"❌ Error checking row {row_num}: {e}")
                if os.path.exists(f'temp_diagnosis_{row_num}.csv'):
                    os.remove(f'temp_diagnosis_{row_num}.csv')
        
    except Exception as e:
        print(f"❌ Error accessing Google Sheets: {e}")

def main():
    """Main diagnostic function"""
    if len(sys.argv) > 1:
        # Diagnose specific file
        file_path = sys.argv[1]
        diagnose_csv_file(file_path)
    else:
        # Diagnose from sheets
        diagnose_from_sheets()

if __name__ == "__main__":
    main()