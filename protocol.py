import json
import time

PROTOCOL = {
    'header': 64,
    'format': 'utf-8',
    'disconnect': 'okover'
}

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