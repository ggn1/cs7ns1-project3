PROTOCOL = {
    'header': 64,
    'format': 'utf-8',
    'disconnect': 'okover'
}

def message_transfer_protocol(conn):
    ''' Receives input from a peer and decodes it into a message while
        following the message transfer protocol. 
        Returns decoded message and whether the peer is still connected.
    '''
    message_length = conn.recv(PROTOCOL['header']).decode(PROTOCOL['format'])
    is_connected = True
    if message_length: 
        message_length = int(message_length) # First determine length of the message.
        message = conn.recv(message_length).decode(PROTOCOL['format']) # Then receive message of determined length.
        if message == PROTOCOL['disconnect']: is_connected = False
    else: 
        message = None
    return message, is_connected