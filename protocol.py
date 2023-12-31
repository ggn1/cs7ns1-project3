# AUTHOR: Tarun Singh (23330140) [Contribution = Security = Logging, auth token, input validation, error handling.]
# AUTHOR: Tejas Bhatnagar (23334930) [Contribution = Testing, Debugging]
# AUTHOR: Gayathri Girish Nair (23340334) [Contribution = Everything else (ICN, NDN, Scenario set up.)]

import json
import time
import socket
import logging
import os

# Create a 'logs' directory if it doesn't exist
logs_dir = 'logs'
os.makedirs(logs_dir, exist_ok=True)

# Set up logging to write logs to both console and a file
logging.basicConfig(level=logging.INFO)

# Create a file handler that writes log messages to a file
log_file_path = os.path.join(logs_dir, 'protocol.log')
file_handler = logging.FileHandler(log_file_path)
file_handler.setLevel(logging.INFO)

# Create a logger and add the file handler
logger = logging.getLogger(__name__)
logger.addHandler(file_handler)

def send_tcp(message, host, port):
    socket_temp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        port = int(port)  # Validate that port is an integer
        socket_temp.connect((host, port))
        message = message.encode('utf-8')
        socket_temp.send(message)
    except Exception as e:
        message_info = json.loads(message)
        content_name = message_info['content_name'].split('/')[0].split('-')
        logger.error(f"[{content_name[2]}] Connection Error: {e}. Message = {message_info}.")
    finally:
        socket_temp.close()

def make_interest_packet(content_name):
    try:
        # Validate content_name format
        if not isinstance(content_name, str) or not content_name:
            raise ValueError("Invalid content_name format.")

        packet = {
            "content_name": f'{content_name}/{time.time()}',
            "type": "interest"
        }
        return json.dumps(packet)
    except Exception as e:
        logger.error(f"Error creating interest packet: {str(e)}")
        return None

def make_data_packet(content_name, data):
    try:
        # Validate content_name format
        if not isinstance(content_name, str) or not content_name:
            raise ValueError("Invalid content_name format.")
            
        packet = {
            "content_name": f'{content_name}/{time.time()}',
            'data': data,
            'type': 'data'
        }
        return json.dumps(packet)
    except Exception as e:
        logger.error(f"Error creating data packet: {str(e)}")
        return None