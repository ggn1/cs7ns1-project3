PROTOCOL = {
    'header': 64,
    'format': 'utf-8',
    'disconnect': 'okover'
}

def make_interest_packet(name, snib):
    ''' Creates an interest packet. '''
    packet = f'{name}|{snib}'
    return packet

def message_decode(conn):
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

def message_encode(conn, message):
    message = message.encode(PROTOCOL['format'])
    message_length = len(message)
    send_length = str(message_length).encode(PROTOCOL['format'])
    send_length += b' '*(PROTOCOL['header']-len(send_length)) # padding
    conn.send(send_length)
    conn.send(message)