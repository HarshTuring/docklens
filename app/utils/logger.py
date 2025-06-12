import os
import json
import time
import threading
from datetime import datetime
from flask import current_app

# Thread lock for file operations
file_lock = threading.Lock()

def initialize_log_file():
    """
    Initialize the log file if it doesn't exist.
    
    Returns:
        str: Path to the log file
    """
    log_dir = os.path.join(current_app.root_path, 'logs')
    os.makedirs(log_dir, exist_ok=True)
    
    log_file = os.path.join(log_dir, 'image_operations.json')
    
    # Create the log file with empty array if it doesn't exist
    if not os.path.exists(log_file):
        with open(log_file, 'w') as f:
            json.dump([], f)
    
    return log_file

def log_operation(image_name, operation, source_type, status='success', details=None):
    """
    Log an image operation to the JSON log file.
    
    Args:
        image_name (str): Name of the image file
        operation (str): Type of operation (upload, grayscale, etc.)
        source_type (str): Source of the image (upload, url)
        status (str): Status of the operation (success, error)
        details (dict, optional): Additional details about the operation
    """
    log_entry = {
        'timestamp': datetime.now().isoformat(),
        'unix_timestamp': int(time.time()),
        'image_name': image_name,
        'operation': operation,
        'source_type': source_type,
        'status': status,
        'details': details if details is not None else {}
    }
    
    log_file = initialize_log_file()
    
    # Use a lock to ensure thread safety when writing to the file
    with file_lock:
        try:
            # Read existing logs
            with open(log_file, 'r') as f:
                try:
                    logs = json.load(f)
                except json.JSONDecodeError:
                    logs = []
            
            # Append new log entry
            logs.append(log_entry)
            
            # Write back to file
            with open(log_file, 'w') as f:
                json.dump(logs, f, indent=2)
                
            current_app.logger.info(f"Logged {operation} operation for {image_name}")
        except Exception as e:
            current_app.logger.error(f"Error logging operation: {str(e)}")

def get_operation_logs(limit=None, operation_type=None, source_type=None):
    """
    Get operation logs with optional filtering.
    
    Args:
        limit (int, optional): Limit the number of logs returned
        operation_type (str, optional): Filter by operation type
        source_type (str, optional): Filter by source type
        
    Returns:
        list: List of log entries
    """
    log_file = initialize_log_file()
    
    try:
        with open(log_file, 'r') as f:
            try:
                logs = json.load(f)
            except json.JSONDecodeError:
                return []
        
        # Apply filters
        if operation_type:
            logs = [log for log in logs if log.get('operation') == operation_type]
            
        if source_type:
            logs = [log for log in logs if log.get('source_type') == source_type]
        
        # Sort by timestamp (newest first)
        logs.sort(key=lambda x: x.get('unix_timestamp', 0), reverse=True)
        
        # Apply limit
        if limit and isinstance(limit, int):
            logs = logs[:limit]
            
        return logs
    except Exception as e:
        current_app.logger.error(f"Error reading logs: {str(e)}")
        return []