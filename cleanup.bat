@echo off
REM Cleanup script to remove unnecessary files and create a clean project structure

REM Create directories for input and output
mkdir input_csv 2>nul
mkdir output_jsons 2>nul

REM Remove test and example files
echo Removing test and example files...
del /q diagnose_csv.py fix_csv_links.py list_worksheets.py example_process.py test_setup.py 2>nul
del /q M0029.csv problematic_csv_row_17.csv problematic_csv_row_21.csv MSA091.json 2>nul
rmdir /s /q test_output 2>nul
rmdir /s /q test_output2 2>nul
rmdir /s /q test_output_new 2>nul
rmdir /s /q final_test_output 2>nul

REM Keep essential files
echo.
echo Keeping essential files:
echo - main.py - Main orchestrator script
echo - csv2json_converter.py - Core converter logic
echo - google_sheets_handler.py - Google Sheets integration
echo - drive_uploader.py - Google Drive uploader
echo - config.yaml - Configuration file
echo - requirements.txt - Dependencies
echo - README_new.md - Updated documentation (rename to README.md)
echo.

REM Rename README file
echo Renaming README_new.md to README.md
move /y README_new.md README.md 2>nul

echo Cleanup completed!
echo.
echo To convert CSV files, use the main script:
echo python main.py --process
echo.

pause