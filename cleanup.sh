#!/bin/bash
# Cleanup script to remove unnecessary files and create a clean project structure

# Create directories for input and output
mkdir -p input_csv output_jsons

# Remove test and example files
echo "Removing test and example files..."
rm -f diagnose_csv.py fix_csv_links.py list_worksheets.py example_process.py test_setup.py
rm -f M0029.csv problematic_csv_row_17.csv problematic_csv_row_21.csv MSA091.json
rm -rf test_output/ test_output2/ test_output_new/ final_test_output/

# Keep essential files
echo "Keeping essential files:"
echo "- main.py - Main orchestrator script"
echo "- csv2json_converter.py - Core converter logic"
echo "- google_sheets_handler.py - Google Sheets integration"
echo "- drive_uploader.py - Google Drive uploader"
echo "- config.yaml - Configuration file"
echo "- requirements.txt - Dependencies"
echo "- README_new.md - Updated documentation (rename to README.md)"

# Rename README file
echo "Renaming README_new.md to README.md"
mv README_new.md README.md

echo "Cleanup completed!"
echo "To convert CSV files, use the main script:"
echo "python main.py --process"