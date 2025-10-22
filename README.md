# CSV to JSON Conversation Converter

A comprehensive Python tool that automates the conversion of CSV conversation logs to structured JSON format, with seamless Google Sheets and Google Drive integration.

## Features

- 🔄 **Automated CSV to JSON Conversion**: Convert conversation logs from CSV format to structured JSON
- 📊 **Google Sheets Integration**: Read CSV links from Google Sheets and update with JSON URLs
- ☁️ **Google Drive Upload**: Automatically upload converted JSON files to Google Drive
- ⚙️ **Highly Configurable**: All settings configurable via YAML file
- 🔍 **Field Filtering**: Include/exclude specific CSV fields based on configuration
- 📝 **Conversation Grouping**: Group messages by conversation/session ID
- 🎯 **Smart Filtering**: Filter rows based on event types and roles
- 🔄 **Error Handling**: Robust error handling with retry mechanisms
- 📈 **Batch Processing**: Process multiple files efficiently
- 📋 **Detailed Logging**: Comprehensive logging for monitoring and debugging

## Installation

1. **Clone or download the repository**:
   ```bash
   git clone <repository-url>
   cd csv2json
   ```

2. **Create a virtual environment** (recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

## Setup

### 1. Google API Credentials

1. **Go to the Google Cloud Console**: https://console.cloud.google.com/

2. **Create a new project** or select an existing one

3. **Enable required APIs**:
   - Google Sheets API
   - Google Drive API

4. **Create OAuth 2.0 Credentials**:
   - Go to "APIs & Services" > "Credentials"
   - Click "Create Credentials" > "OAuth client ID"
   - Select "Desktop Application" as the application type
   - Give it a name (e.g., "CSV2JSON Converter")
   - Click "Create"

5. **Download and setup credentials**:
   - Click "Download JSON" for the OAuth client you just created
   - Save the file as `client_secret.json` in the project directory
   - The file should look similar to `client_secret_template.json`

6. **First-time authentication**:
   - When you first run the script, it will open a browser window
   - Log in to your Google account and grant the requested permissions
   - The script will save a `token.json` file for future use
   - No need to manually share sheets - you'll have access to all your own files

### 2. Configuration

1. **Copy and customize the configuration**:
   ```bash
   cp config.yaml config_custom.yaml
   ```

2. **Update `config.yaml`** with your specific settings:

   ```yaml
   # Update these values with your Google Sheet details
   google_sheets:
     spreadsheet_url: "YOUR_GOOGLE_SHEET_URL_HERE"
     worksheet_name: "YOUR_WORKSHEET_NAME"
     csv_link_column: "Link to csv"
     json_link_column: "Link to json"
     credentials_path: "client_secret.json"

   # Update Drive folder name
   google_drive:
     output_folder_name: "your_output_folder_name"
   ```

### 3. Google Sheets Format

Your Google Sheet should have the following structure:

| Column A | Link to csv | Link to json | Other columns... |
|----------|-------------|--------------|------------------|
| Row 1    | https://... |              | ...              |
| Row 2    | https://... |              | ...              |

## Usage

### Command Line Interface

1. **Validate setup**:
   ```bash
   python main.py --validate
   ```

2. **Check status**:
   ```bash
   python main.py --status
   ```

3. **Process all pending conversions**:
   ```bash
   python main.py --process
   ```

4. **Use custom config file**:
   ```bash
   python main.py --config config_custom.yaml --process
   ```

### Programmatic Usage

```python
from main import CSV2JSONOrchestrator

# Initialize orchestrator
orchestrator = CSV2JSONOrchestrator("config.yaml")

# Validate setup
if orchestrator.validate_setup():
    # Process all pending conversions
    summary = orchestrator.process_all_pending()
    print(f"Processed: {summary['successful']} successful, {summary['failed']} failed")

# Cleanup
orchestrator.cleanup()
```

### Individual Components

```python
# Use converter standalone
from csv2json_converter import CSV2JSONConverter

converter = CSV2JSONConverter("config.yaml")
json_files = converter.convert_csv_to_json("path/to/file.csv", "output_dir")

# Use Google Sheets handler
from google_sheets_handler import GoogleSheetsHandler

sheets = GoogleSheetsHandler("config.yaml")
pending = sheets.get_pending_conversions()

# Use Drive uploader
from drive_uploader import GoogleDriveUploader

uploader = GoogleDriveUploader("config.yaml")
result = uploader.upload_file("path/to/file.json")
```

## Configuration Reference

### CSV Processing Options

```yaml
csv_processing:
  # Fields to include (leave empty to include all)
  included_fields:
    - "role"
    - "content"
    - "timestamp"
    - "model_used"
  
  # Fields to exclude
  excluded_fields:
    - "extra"
    - "original_args"
  
  # Filter criteria
  filter_criteria:
    event_type: 
      - "user_message"
      - "ai_response"
    role:
      - "user" 
      - "assistant"
```

### JSON Output Structure

```yaml
json_output:
  structure:
    conversation_id_field: "session_id"
    messages_field: "messages"
    
    message_mapping:
      role: "role"
      content: "content"
      timestamp: "timestamp"
      model: "model_used"
```

### File Naming

```yaml
file_naming:
  json_filename_template: "{conversation_id}_{timestamp}.json"
  include_date: true
  date_format: "%Y%m%d"
```

## Expected Input/Output Formats

### Input CSV Format

The CSV should contain conversation logs with columns like:
- `session_id`: Unique conversation identifier
- `role`: user/assistant/system
- `content`: Message content
- `timestamp`: Message timestamp
- `event_type`: Type of event (user_message, ai_response, etc.)
- `model_used`: AI model used for responses

### Output JSON Format

```json
{
  "conversation_id": "session_123",
  "messages": [
    {
      "role": "user",
      "content": "Hello, how are you?",
      "timestamp": "2025-10-13T13:08:56.778810Z",
      "turn_id": "turn_1"
    },
    {
      "role": "assistant", 
      "content": "I'm doing well, thank you!",
      "timestamp": "2025-10-13T13:08:58.123456Z",
      "model": "gpt-4o-mini",
      "turn_id": "turn_2"
    }
  ],
  "metadata": {
    "total_messages": 2,
    "conversation_start": "2025-10-13T13:08:56.778810Z",
    "conversation_end": "2025-10-13T13:08:58.123456Z",
    "unique_models": ["gpt-4o-mini"],
    "processing_timestamp": "2025-10-13T15:30:00.000000Z"
  }
}
```

## Troubleshooting

### Common Issues

1. **Authentication Failed**:
   - Check that `credentials.json` is in the correct location
   - Verify the service account has the necessary permissions
   - Make sure the Google Sheet is shared with the service account email

2. **Spreadsheet Not Found**:
   - Verify the spreadsheet URL in config.yaml
   - Check that the worksheet name is correct
   - Ensure the service account has access to the spreadsheet

3. **CSV Download Failed**:
   - Check if CSV URLs are accessible
   - For Google Drive links, ensure they're set to "Anyone with the link can view"
   - Verify network connectivity

4. **Upload Failed**:
   - Check Google Drive API quotas
   - Verify the service account has Drive permissions
   - Ensure sufficient storage space in Google Drive

### Enable Debug Logging

```yaml
logging:
  level: "DEBUG"
  log_to_file: true
  log_file_path: "debug.log"
```

### Test Individual Components

```bash
# Test CSV conversion only
python csv2json_converter.py

# Test Google Sheets access
python google_sheets_handler.py

# Test Drive upload
python drive_uploader.py
```

## API Quotas and Limits

### Google Sheets API
- 100 requests per 100 seconds per user
- 1000 requests per 100 seconds

### Google Drive API  
- 1000 requests per 100 seconds per user
- 10,000 requests per 100 seconds

The tool includes automatic rate limiting and retry mechanisms to handle these limits.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For issues and questions:
1. Check the troubleshooting section above
2. Review the logs for error details
3. Create an issue with detailed error information and configuration (remove sensitive data)

## Changelog

### Version 1.0.0
- Initial release
- CSV to JSON conversion
- Google Sheets integration
- Google Drive upload
- Configurable processing options
- Command line interface