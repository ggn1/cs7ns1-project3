import json
import time
import socket

def send_tcp(message, host, port):
    socket_temp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        socket_temp.connect((host, int(port)))
        message = message.encode('utf-8')
        socket_temp.send(message)
    except Exception as e:
        message = json.loads(message)
        message = message['content_name'].split('/')[0].split('-')
        print(f'[{message[2]}] Connection Error: {e}. Message = {message}.')
    finally:
        socket_temp.close()

def make_interest_packet(content_name):
    ''' Creates an interest packet. '''
    packet = {
        "content_name": f'{content_name}/{time.time()}',
        "type": "interest"
    }
    return json.dumps(packet)

def make_data_packet(content_name, data):
    ''' Creates an interest packet. '''
    packet = {
        "content_name": f'{content_name}/{time.time()}',
        'data': data,
        'type': 'data'
    }
    return json.dumps(packet)