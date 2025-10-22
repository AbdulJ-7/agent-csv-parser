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
   - Create a new project or select an existing one
   - Enable Google Sheets API and Google Drive API
   - Create OAuth 2.0 credentials (Desktop application)
   - Download the credentials and save as `client_secret.json` in project directory

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

- **Authentication issues**: Ensure `client_secret.json` is properly set up
- **CSV format errors**: Verify CSV files follow the expected format
- **Google Sheets access**: Check that you have access to the configured spreadsheet

For detailed logs, check `conversion.log` in the project directory.