import json
import time
import socket

def send_tcp(message, host, port):
    socket_temp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    socket_temp.connect((host, port))
    message = message.encode('utf-8')
    socket_temp.send(message)
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