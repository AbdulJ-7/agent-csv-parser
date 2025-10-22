"""
CSV to JSON Converter for Conversation Logs
Converts CSV conversation logs to structured JSON format based on configuration
"""

import pandas as pd
import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
import os
import yaml


class CSV2JSONConverter:
    """Handles conversion from CSV conversation logs to JSON format"""
    
    def __init__(self, config_path: str = "config.yaml"):
        """Initialize converter with configuration"""
        self.config = self._load_config(config_path)
        self.logger = self._setup_logging()
        
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        try:
            with open(config_path, 'r', encoding='utf-8') as file:
                return yaml.safe_load(file)
        except FileNotFoundError:
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML configuration: {e}")
    
    def _setup_logging(self) -> logging.Logger:
        """Setup logging based on configuration"""
        logger = logging.getLogger(__name__)
        logger.setLevel(getattr(logging, self.config['logging']['level']))
        
        formatter = logging.Formatter(self.config['logging']['format'])
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
        # File handler if configured
        if self.config['logging']['log_to_file']:
            file_handler = logging.FileHandler(self.config['logging']['log_file_path'])
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        
        return logger
    
    def read_csv(self, csv_path: str) -> pd.DataFrame:
        """Read CSV file and return DataFrame"""
        try:
            self.logger.info(f"Reading CSV file: {csv_path}")
            df = pd.read_csv(csv_path)
            self.logger.info(f"Successfully read {len(df)} rows from CSV")
            return df
        except Exception as e:
            self.logger.error(f"Error reading CSV file {csv_path}: {e}")
            raise
    
    def filter_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Filter DataFrame based on configuration criteria"""
        original_count = len(df)
        
        # Apply event_type filter if specified
        event_type_filter = self.config['csv_processing']['filter_criteria'].get('event_type', [])
        if event_type_filter:
            df = df[df['event_type'].isin(event_type_filter)]
            self.logger.info(f"Applied event_type filter: {len(df)} rows remaining")
        
        # Apply role filter if specified
        role_filter = self.config['csv_processing']['filter_criteria'].get('role', [])
        if role_filter:
            df = df[df['role'].isin(role_filter)]
            self.logger.info(f"Applied role filter: {len(df)} rows remaining")
        
        # Remove rows with empty content if skip_invalid_rows is enabled
        if self.config['error_handling']['skip_invalid_rows']:
            before_count = len(df)
            df = df.dropna(subset=['content'])
            df = df[df['content'].str.strip() != '']
            after_count = len(df)
            if before_count != after_count:
                self.logger.info(f"Removed {before_count - after_count} rows with empty content")
        
        self.logger.info(f"Filtered DataFrame: {original_count} -> {len(df)} rows")
        return df
    
    def select_fields(self, df: pd.DataFrame) -> pd.DataFrame:
        """Select only specified fields from DataFrame"""
        included_fields = self.config['csv_processing']['included_fields']
        excluded_fields = self.config['csv_processing']['excluded_fields']
        
        # If included_fields is specified, use only those fields
        if included_fields:
            available_fields = [field for field in included_fields if field in df.columns]
            df = df[available_fields]
            self.logger.info(f"Selected fields: {available_fields}")
        
        # Remove excluded fields
        if excluded_fields:
            fields_to_exclude = [field for field in excluded_fields if field in df.columns]
            df = df.drop(columns=fields_to_exclude)
            self.logger.info(f"Excluded fields: {fields_to_exclude}")
        
        return df
    
    def group_by_conversation(self, df: pd.DataFrame) -> Dict[str, pd.DataFrame]:
        """Group DataFrame by conversation ID"""
        conversation_id_field = self.config['json_output']['structure']['conversation_id_field']
        
        if conversation_id_field not in df.columns:
            self.logger.warning(f"Conversation ID field '{conversation_id_field}' not found. Using default grouping.")
            return {"single_conversation": df}
        
        conversations = {}
        for conv_id, group in df.groupby(conversation_id_field):
            conversations[str(conv_id)] = group.sort_values('timestamp') if 'timestamp' in group.columns else group
        
        self.logger.info(f"Grouped into {len(conversations)} conversations")
        return conversations
    
    def create_system_message(self):
        """Create the standard system message for the conversation"""
        return {
            "role": "system",
            "content": "You are a helpful AI assistant specialized in synthesizing information.\n\nIMPORTANT: Your role is to provide ONLY text-based responses. Do NOT make any tool calls during summary generation.\n\nYour task is to:\n1. Take information from multiple tools that were already executed\n2. Combine and synthesize the information into a coherent response\n3. Answer the user's question directly and comprehensively\n4. Present the information in a natural, conversational way\n\nYou have access to tools but should NOT use them during this final summary phase. TOOLS:\n- current_time(q:str)->{current_time_result}\n- google_trends(q:str)->{google_trends_result}\n- mealdb_food(q:str)->{mealdb_food_result}\n- tmdb_movies(q:str)->{tmdb_movies_result}\n- pubmed(q:str)->{pubmed_result}\n- arxiv_papers(q:str)->{arxiv_papers_result}\n- weather(q:str)->{weather_result}\n- google_places(q:str)->{google_places_result}\n- youtube_summarizer(q:str)->{youtube_summarizer_result}\n- youtube_search(q:str)->{youtube_search_result}\n- calculator(q:str)->{calculator_result}\n- amadeus_travel(q:str)->{amadeus_travel_result}\n- github(q:str)->{github_result}\n- email_sender(q:str)->{email_sender_result}\n- web_search(q:str)->{web_search_result}\n- steam_search(q:str)->{steam_search_result}\n- yahoo_finance(q:str)->{yahoo_finance_result}\n- wikipedia(q:str)->{wikipedia_result}\n- tavily_search(q:str)->{tavily_search_result}\n- multiply(q:str)->{multiply_result}"
        }

    def extract_tool_arguments(self, original_args_str):
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

    def convert_to_json_structure(self, df: pd.DataFrame, conversation_id: str) -> Dict[str, Any]:
        """Convert DataFrame to structured JSON with interleaved reasoning, tool calls, and tool outputs"""
        messages_field = self.config['json_output']['structure']['messages_field']
        messages = []
        
        # Add system message first
        messages.append(self.create_system_message())
        
        # Sort by timestamp or turn_id to maintain chronological order
        if 'timestamp' in df.columns:
            df = df.sort_values('timestamp')
        elif 'turn_id' in df.columns:
            df = df.sort_values('turn_id')
        
        # Track pending tool calls to match with their execution results
        pending_tool_calls = {}
        
        # Process each row in chronological order
        for idx, row in df.iterrows():
            event_type = row.get('event_type', '')
            role = row.get('role', '')
            content = row.get('content', '')
            tool_name = row.get('tool_name', '')
            original_args = row.get('original_args', '')
            execution_result = row.get('execution_result', '')
            timestamp = row.get('timestamp', '')

            # User messages
            if event_type == "user_message" and role == "user":
                if content and not pd.isna(content):
                    messages.append({
                        "role": "user",
                        "content": str(content).strip()
                    })

            # Reasoning from thought events
            elif event_type == "thought" and role == "assistant":
                if content and not pd.isna(content):
                    reasoning_text = str(content).strip()
                    if reasoning_text:
                        messages.append({
                            "role": "assistant", 
                            "reasoning": [reasoning_text]
                        })

            # Tool calls from tool_call events
            elif event_type == "tool_call" and role == "assistant":
                if tool_name and original_args:
                    tool_call_msg = {
                        "role": "assistant",
                        "tool_call": {
                            "name": str(tool_name),
                            "arguments": self.extract_tool_arguments(original_args)
                        }
                    }
                    messages.append(tool_call_msg)
                    
                    # Store the tool call to match with execution result later
                    call_key = f"{tool_name}_{timestamp}_{idx}"
                    pending_tool_calls[call_key] = {
                        "tool_name": str(tool_name),
                        "message_index": len(messages) - 1
                    }

            # Tool execution results from tool_execution events
            elif event_type == "tool_execution" and role == "tool":
                if tool_name and execution_result:
                    try:
                        # Try to parse execution_result as JSON
                        result_data = json.loads(execution_result) if execution_result else {}
                        tool_response = {
                            "role": "tool",
                            "name": str(tool_name),
                            "content": json.dumps(result_data, indent=2) if isinstance(result_data, dict) else str(execution_result)
                        }
                    except:
                        tool_response = {
                            "role": "tool",
                            "name": str(tool_name),
                            "content": str(execution_result)
                        }
                    
                    messages.append(tool_response)

            # Final AI responses from ai_response or final_answer events
            elif (event_type == "ai_response" or event_type == "final_answer") and role == "assistant":
                if content and not pd.isna(content):
                    messages.append({
                        "role": "assistant",
                        "content": str(content).strip()
                    })
            
            # Fallback for simple role-content pairs (backward compatibility)
            elif not event_type and role and content:
                if role == "user":
                    messages.append({
                        "role": "user",
                        "content": str(content).strip()
                    })
                elif role == "assistant":
                    messages.append({
                        "role": "assistant", 
                        "content": str(content).strip()
                    })
        
        return {messages_field: messages}
    
    def _generate_metadata(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Generate metadata for the conversation"""
        metadata = {}
        metadata_fields = self.config['json_output']['metadata_fields']
        
        if 'total_messages' in metadata_fields:
            metadata['total_messages'] = len(df)
        
        if 'timestamp' in df.columns:
            timestamps = pd.to_datetime(df['timestamp'], errors='coerce').dropna()
            if not timestamps.empty:
                if 'conversation_start' in metadata_fields:
                    metadata['conversation_start'] = timestamps.min().isoformat()
                if 'conversation_end' in metadata_fields:
                    metadata['conversation_end'] = timestamps.max().isoformat()
        
        if 'unique_models' in metadata_fields and 'model_used' in df.columns:
            unique_models = df['model_used'].dropna().unique().tolist()
            metadata['unique_models'] = unique_models
        
        metadata['processing_timestamp'] = datetime.now().isoformat()
        
        return metadata
    
    def save_json(self, json_data: Dict[str, Any], output_path: str) -> str:
        """Save JSON data to file"""
        try:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            with open(output_path, 'w', encoding='utf-8') as file:
                if self.config['json_output']['pretty_print']:
                    json.dump(json_data, file, indent=2, ensure_ascii=False)
                else:
                    json.dump(json_data, file, ensure_ascii=False)
            
            self.logger.info(f"JSON saved to: {output_path}")
            return output_path
        except Exception as e:
            self.logger.error(f"Error saving JSON to {output_path}: {e}")
            raise
    
    def generate_filename(self, conversation_id: str, index: int = 0) -> str:
        """Generate filename based on configuration template"""
        template = self.config['file_naming']['json_filename_template']
        
        # Prepare variables for template
        variables = {
            'conversation_id': conversation_id,
            'index': index,
            'timestamp': datetime.now().strftime(self.config['file_naming']['date_format'])
        }
        
        filename = template.format(**variables)
        
        # Ensure .json extension
        if not filename.endswith('.json'):
            filename += '.json'
        
        return filename
    
    def convert_csv_to_json(self, csv_path: str, output_dir: str = "output") -> List[str]:
        """Main conversion function - converts CSV to JSON files"""
        try:
            # Read and process CSV
            df = self.read_csv(csv_path)
            df = self.filter_dataframe(df)
            df = self.select_fields(df)
            
            # Group by conversations
            conversations = self.group_by_conversation(df)
            
            # Convert each conversation to JSON
            output_files = []
            for i, (conv_id, conv_df) in enumerate(conversations.items()):
                json_data = self.convert_to_json_structure(conv_df, conv_id)
                filename = self.generate_filename(conv_id, i)
                output_path = os.path.join(output_dir, filename)
                
                saved_path = self.save_json(json_data, output_path)
                output_files.append(saved_path)
            
            self.logger.info(f"Conversion completed. Generated {len(output_files)} JSON files.")
            return output_files
            
        except Exception as e:
            self.logger.error(f"Conversion failed: {e}")
            if not self.config['error_handling']['continue_on_error']:
                raise
            return []
    
    def convert_multiple_csvs(self, csv_paths: List[str], output_dir: str = "output") -> Dict[str, List[str]]:
        """Convert multiple CSV files to JSON"""
        results = {}
        
        for csv_path in csv_paths:
            self.logger.info(f"Processing: {csv_path}")
            try:
                output_files = self.convert_csv_to_json(csv_path, output_dir)
                results[csv_path] = output_files
            except Exception as e:
                self.logger.error(f"Failed to process {csv_path}: {e}")
                if self.config['error_handling']['continue_on_error']:
                    results[csv_path] = []
                else:
                    raise
        
        return results


def main():
    """Main function for testing"""
    converter = CSV2JSONConverter()
    
    # Test with sample CSV
    sample_csv = "C:\\Users\\Admin\\Downloads\\csv2json\\M0029.csv"
    if os.path.exists(sample_csv):
        output_files = converter.convert_csv_to_json(sample_csv, "output")
        print(f"Generated files: {output_files}")
    else:
        print(f"Sample CSV not found: {sample_csv}")


if __name__ == "__main__":
    main()