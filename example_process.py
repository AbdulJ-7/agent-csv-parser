import argparse
import yaml
import os
import json
import pandas as pd
from types import SimpleNamespace

def create_system_message():
    """Create the standard system message for the conversation"""
    return {
        "role": "system",
        "content": "You are a helpful AI assistant specialized in synthesizing information.\n\nIMPORTANT: Your role is to provide ONLY text-based responses. Do NOT make any tool calls during summary generation.\n\nYour task is to:\n1. Take information from multiple tools that were already executed\n2. Combine and synthesize the information into a coherent response\n3. Answer the user's question directly and comprehensively\n4. Present the information in a natural, conversational way\n\nYou have access to tools but should NOT use them during this final summary phase. TOOLS:\n- current_time(q:str)->{current_time_result}\n- google_trends(q:str)->{google_trends_result}\n- mealdb_food(q:str)->{mealdb_food_result}\n- tmdb_movies(q:str)->{tmdb_movies_result}\n- pubmed(q:str)->{pubmed_result}\n- arxiv_papers(q:str)->{arxiv_papers_result}\n- weather(q:str)->{weather_result}\n- google_places(q:str)->{google_places_result}\n- youtube_summarizer(q:str)->{youtube_summarizer_result}\n- youtube_search(q:str)->{youtube_search_result}\n- calculator(q:str)->{calculator_result}\n- amadeus_travel(q:str)->{amadeus_travel_result}\n- github(q:str)->{github_result}\n- email_sender(q:str)->{email_sender_result}\n- web_search(q:str)->{web_search_result}\n- steam_search(q:str)->{steam_search_result}\n- yahoo_finance(q:str)->{yahoo_finance_result}\n- wikipedia(q:str)->{wikipedia_result}\n- tavily_search(q:str)->{tavily_search_result}\n- multiply(q:str)->{multiply_result}"
    }

def extract_tool_arguments(original_args_str):
    """Extract and format tool arguments from the original_args string"""
    if pd.isna(original_args_str) or not original_args_str:
        return {}

    try:
        args = json.loads(original_args_str)
        if isinstance(args, dict):
            if len(args) == 1 and "query" in args:
                return {"__arg1": args["query"]}
            return args
        return {"__arg1": str(args)}
    except:
        return {"__arg1": str(original_args_str)}

def transform_csv_to_json(input_file, args, json_path):
    """Convert conversation log CSV to clean conversation JSON format"""
    df = pd.read_csv(input_file)

    messages = []

    messages.append(create_system_message())

    df = pd.read_csv(input_file)
    for turn_id, group in df.groupby("turn_id", sort=False):
        temp = {"user": [], "reasoning": [], "tooling": [], "response": []}
        for idx, row in group.iterrows():
            event_type = row.get(args.fields.event_type, "")
            role = row.get(args.fields.role, "")
            content = row.get(args.fields.content, "")
            tool_name = row.get(args.fields.tool_name, "")
            original_args = row.get(args.fields.original_args, "")
            execution_result = row.get(args.fields.execution_result, "")   


            if event_type == "user_message" and role == "user":
                temp["user"].append({
                    "role": "user",
                    "content": str(content).strip()
                })

            # Capture reasoning from reasoning_completed events for this specific turn
            elif event_type == "reasoning_completed" and role == "system":
                
                if execution_result and not pd.isna(execution_result):
                    reasoning_text = str(execution_result).strip()
                    if reasoning_text:
                        temp["reasoning"].append({
                            "role": "assistant",
                            "reasoning": [reasoning_text]
                        })

            # Capture tool call interrupts (assistant proposing tool use)
            elif event_type == "tool_call_interrupt" and role == "assistant":
                if tool_name and original_args:
                    tool_call = {
                        "role": "assistant"
                    }
                    # Then add tool_call
                    tool_call["tool_call"] = {
                        "name": tool_name,
                        "arguments": extract_tool_arguments(original_args)
                    }

                    temp["tooling"].append(tool_call)

            # Capture tool execution results - add immediately after the tool call
            elif event_type == "tool_execution_approved" and role == "tool":
                if tool_name and execution_result:
                    try:
                        # Try to parse execution_result as JSON
                        result_data = json.loads(execution_result) if execution_result else {}
                        tool_response = {
                            "role": "tool",
                            "name": tool_name,
                            "content": json.dumps(result_data, indent=2) if isinstance(result_data, dict) else str(execution_result)
                        }
                        temp["tooling"].append(tool_response)
                    except:
                        tool_response = {
                            "role": "tool",
                            "name": tool_name,
                            "content": str(execution_result)
                        }
                        temp["tooling"].append(tool_response)

            # Capture the final AI response for this turn
            elif event_type == "ai_response" and role == "assistant":
                if content and not pd.isna(content):
                    temp["response"].append({
                        "role": "assistant",
                        "content": str(content).strip()
                    })
        for k in temp:
            for val in temp[k]:
                messages.append(val)

    json_obj = {"messages": messages}
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(json_obj, f, ensure_ascii=False, indent=2)



def load_yaml(path: str) -> tuple:
    """Load YAML and return as SimpleNamespace."""
    with open(path, "r") as f:
        data = yaml.safe_load(f)
    
    sheet_url = data.get('google_sheets', '')
    sheet_name = data.get('sheet_name', 'Sheet1')  # Default to Sheet1 if not specified
    
    # Extract just the spreadsheet ID from the URL
    if "spreadsheets/d/" in sheet_url:
        sheet_id = sheet_url.split("spreadsheets/d/")[1].split("/")[0]
    else:
        sheet_id = sheet_url  # Assume it's already just the ID
        
    return [dict_to_namespace(data), sheet_id, sheet_name]


def dict_to_namespace(d: dict) -> SimpleNamespace:
    """Recursively convert dicts to SimpleNamespace for dot notation access."""
    ns = SimpleNamespace()
    for key, value in d.items():
        if isinstance(value, dict):
            setattr(ns, key, dict_to_namespace(value))
        else:
            setattr(ns, key, value)
    return ns

import os
import io
import yaml
import csv
import json
import requests
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload

# ---- Config ----
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'  # Full drive scope for folder access
]
YAML_PATH = 'config.yaml'  
CREDENTIALS_FILE = 'credentials.json'
DRIVE_FOLDER_ID = '1yukSN032ikLFNn07ti4dRoshWZMGOHL-' #Create a drive folder to upload files and share inside the organization.   

# ---- Auth ----
def get_creds():
    # Use service account credentials directly
    creds = service_account.Credentials.from_service_account_file(
        CREDENTIALS_FILE, scopes=SCOPES)
    return creds

def upload_to_drive(drive_service, json_file_path, filename):

    if not os.path.exists(json_file_path):
        raise FileNotFoundError(f"File not found: {json_file_path}")

    file_metadata = {
        'name': filename,
        'parents': [DRIVE_FOLDER_ID],
        'mimeType': 'application/json'
    }

    media = MediaFileUpload(json_file_path, mimetype='application/json')

    file = drive_service.files().create(
        body=file_metadata,
        media_body=media,
        fields='id'
    ).execute()

    file_id = file.get('id')

    # Set the file to be accessible by anyone with the link
    drive_service.permissions().create(
        fileId=file_id,
        body={
            'type': 'anyone',
            'role': 'reader'
        }
    ).execute()

    # Also add domain-specific permission if needed
    try:
        drive_service.permissions().create(
            fileId=file_id,
            body={
                'type': 'domain',
                'role': 'reader',
                'domain': 'deccan.ai'
            }
        ).execute()
    except Exception as e:
        print(f"Note: Domain-specific permission setting failed: {e}")

    share_link = f"https://drive.google.com/file/d/{file_id}/view?usp=sharing"
    print("✅ Uploaded:", share_link)
    return share_link


def main():
    print("starting parsing")
    parser = argparse.ArgumentParser(description="Run function with YAML config")
    parser.add_argument("--config", "-c", required=True, help="Path to YAML config file")
    args = parser.parse_args()

    config, sheet_id, sheet_name = load_yaml(args.config)

    creds = get_creds()
    sheets = build("sheets", "v4", credentials=creds)
    drive = build("drive", "v3", credentials=creds)

    # Get data from the specified sheet
    result = sheets.spreadsheets().values().get(
        spreadsheetId=sheet_id, range=f"{sheet_name}"
    ).execute()
    values = result.get("values", [])
    if not values:
        print(f"Sheet '{sheet_name}' is empty.")
        return

    header = values[0]
    rows = values[1:]

    if "Link to CSV" not in header:
        raise Exception("No 'Link to CSV' column found in sheet header.")

    if "Link to JSON" not in header:
        header.append("Link to JSON")
        sheets.spreadsheets().values().update(
            spreadsheetId=sheet_id,
            range=f"{sheet_name}!1:1",
            valueInputOption="RAW",
            body={"values": [header]}
        ).execute()

    csv_col = header.index("Link to CSV")
    json_col = header.index("Link to JSON")

    for i, row in enumerate(rows, start=2):
        if len(row) <= csv_col:
            continue
        csv_url = row[csv_col].strip()
        if not csv_url or not csv_url.startswith("http"):
            continue

        print(f"Processing row {i}: {csv_url}")

        try:
            # Extract file ID from Google Drive URL
            if "/d/" in csv_url:
                file_id = csv_url.split("/d/")[1].split("/")[0]
            elif "id=" in csv_url:
                file_id = csv_url.split("id=")[1].split("&")[0]
            else:
                print(f"⚠️ Cannot parse URL format: {csv_url}")
                continue
                
            # Download CSV using service account
            print(f"Downloading CSV with ID: {file_id}")
            csv_path = f"temp_{i}.csv"
            json_path = f"temp_{i}.json"
            
            # Use service account to download the file
            request = drive.files().get_media(fileId=file_id)
            fh = io.BytesIO()
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while done is False:
                status, done = downloader.next_chunk()
                print(f"Download {int(status.progress() * 100)}%.")
                
            with open(csv_path, "wb") as f:
                f.write(fh.getvalue())
            transform_csv_to_json(csv_path, config, json_path)
            filename = os.path.basename(json_path)
            json_link = upload_to_drive(drive, json_path, filename)

            # Update Sheet with the sheet_name from config
            cell_range = f"{sheet_name}!{chr(65 + json_col)}{i}"
            sheets.spreadsheets().values().update(
                spreadsheetId=sheet_id,
                range=cell_range,
                valueInputOption="RAW",
                body={"values": [[json_link]]}
            ).execute()

            print(f"✅ Row {i} updated with {json_link}")
            os.remove(csv_path)
            os.remove(json_path)


        except Exception as e:
            print(f"⚠️ Error processing row {i}: {e}")


if __name__ == "__main__":
    main()



