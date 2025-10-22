# CSV to JSON Converter

A Python utility for converting CSV conversation logs to structured JSON format.

## Overview

This tool processes conversation data from CSV files and converts them into a structured JSON format suitable for LLM training. It includes:

- CSV to JSON conversion with customizable field mapping
- Google Sheets integration to track conversions
- Google Drive uploads of generated JSON files
- Support for tool call and reasoning extraction

## Requirements

- Python 3.8+
- Google account with access to Google Sheets and Drive
- OAuth 2.0 credentials for Google API access

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/csv-to-json-converter.git
   cd csv-to-json-converter
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Set up Google OAuth credentials:
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project:
     - Click on the project dropdown at the top of the page
     - Click "New Project"
     - Enter a name for your project and click "Create"
   
   - Enable required APIs:
     - Go to "APIs & Services" > "Library"
     - Search for and enable "Google Sheets API"
     - Search for and enable "Google Drive API"
   
   - Create OAuth 2.0 credentials:
     - Go to "APIs & Services" > "Credentials"
     - Click "Create Credentials" > "OAuth client ID"
     - Return to the credentials page
     - Select "Desktop Application" as the application type
     - Give your credentials a name (e.g., "CSV2JSON Converter")
     - Click "Create"
   
   - Download and setup credentials:
     - Click "Download JSON" for the OAuth client you just created
     - Save the file as `client_secret.json` in the project directory
     - The file should look similar to `client_secret_template.json`
   
   - First-time authentication:
     - When you first run the script, it will open a browser window
     - Log in with the Google account that has access to your Sheets/Drive
     - Grant the requested permissions when prompted
     - The script will save a `token.json` file for future authentication
     - This token will be valid until you revoke access or it expires

## Configuration

Edit `config.yaml` to customize:

- **Google Sheets settings**: 
  - Update `spreadsheet_url` with your Google Sheets URL
  - Set `worksheet_name` to the correct sheet name
  - Configure column names for CSV links and JSON output

- **Google Drive settings**:
  - Set the `output_folder_name` for uploaded JSON files

- **CSV Processing settings**:
  - Configure included/excluded fields
  - Set filtering criteria for event types and roles

- **JSON output structure**:
  - Customize the output format for converted files

## Usage

### Full Process with Google Integration

1. **Validate your setup**:
   ```bash
   python main.py --validate
   ```

2. **Process all pending conversions**:
   ```bash
   python main.py --process
   ```

3. **Check status of processed items**:
   ```bash
   python main.py --status
   ```

4. **Batch Processing and Reprocessing**:
   - The script can be run multiple times to process new CSVs added to the Google Sheet
   - By default, previously processed CSVs will be skipped (based on the presence of a JSON link in the sheet)
   - To reprocess updated CSV files:
     - If you've edited a CSV file without changing its name, you must:
       1. Delete the corresponding JSON file(s) from the local `output_jsons` directory
       2. Delete the corresponding file from the Google Drive folder
       3. Clear the JSON link cell in the Google Sheet
     - Otherwise, the tool will skip processing due to the existing links and cached files
   - You can control this behavior with the `skip_existing` setting in `config.yaml`

### Direct CSV Conversion

You can also use the converter component directly in your code:

```python
from csv2json_converter import CSV2JSONConverter

converter = CSV2JSONConverter("config.yaml")
json_files = converter.convert_csv_to_json("path/to/file.csv", "output_dir")
```

## Workflow

1. The tool reads a Google Sheet containing links to CSV files
2. It downloads each CSV file and processes it according to configuration
3. The CSV is converted to JSON with the specified structure
4. The JSON file is uploaded to Google Drive
5. The Google Sheet is updated with a link to the uploaded JSON file

## JSON Structure

The output JSON follows this structure:
- System message containing tool definitions
- User messages
- Assistant reasoning followed by tool calls and tool outputs
- Assistant final responses

## Troubleshooting

### Authentication Issues

- **Invalid client_secret.json**: 
  - Verify you downloaded the correct OAuth 2.0 credentials (not API keys or service account keys)
  - Ensure the file is named exactly `client_secret.json` and is in the project root directory
  - If you see "The application was not found" errors, return to Google Cloud Console and check that your project and OAuth consent screen are properly configured

- **Token Refresh Errors**:
  - If you encounter token expiration issues, delete the `token.json` file to force reauthentication
  - Run `python oauth_setup.py` to generate a new token before running the main script
  - Ensure you're using the same Google account that has access to your spreadsheet

- **Scope Issues**:
  - If you receive "insufficient permission" errors, check that you've added the correct scopes in the OAuth consent screen
  - Required scopes include `/auth/drive.file` and `/auth/spreadsheets`

### CSV and Google Sheets Issues

- **CSV format errors**: 
  - Verify CSV files follow the expected format with required columns
  - Check for encoding issues (the tool expects UTF-8 encoding)
  - If parsing specific rows fails, examine the problematic rows in the CSV file

- **Google Sheets access**: 
  - Ensure the authenticated Google account has access to the configured spreadsheet
  - Verify the spreadsheet URL and worksheet name in `config.yaml` are correct
  - Check that the column names for CSV links and JSON links match your spreadsheet headers

- **CSVs not being processed**:
  - If a CSV appears to be skipped, check if it was processed in a previous run
  - The tool skips files that have existing JSON links in the spreadsheet
  - For updated CSVs, clear the JSON link cell and remove any existing output files

- **Reprocessing updated CSVs**:
  - To force reprocessing of an updated CSV:
    1. Delete the JSON file from local `output_jsons` folder
    2. Delete the file from Google Drive folder
    3. Remove the JSON link from the Google Sheet
    4. Run the script again with `python main.py --process`

For detailed logs, check `conversion.log` in the project directory. You can increase the logging level in `config.yaml` by changing `level: "INFO"` to `level: "DEBUG"` for more verbose output.