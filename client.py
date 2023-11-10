import socket
import argparse
from protocol import PROTOCOL

def setup_argparser():
    ''' Adds arguments.
        --server
    '''
    parser = argparse.ArgumentParser()

    parser.add_argument(
        '--server', 
        help="Server's IP address of server.", 
        type=str
    )

    parser.add_argument(
        '--port', 
        help='Port number.', 
        type=int
    )

    args = parser.parse_args()

    if args.server is None:
        print("Please specify server's address.")
        exit(1)

    if args.port is None:
        print("Please specify a port number.")
        exit(1)

    return args

class Client:
    def __init__(self, server, port):
        self.addr = (server, port)
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM) # IP, TCP
        self.connect()
    
    def connect(self):
        ''' Connects to server. '''
        self.socket.connect(self.addr)

    def send(self, message):
        ''' Sends data to server and returns response. '''
        message = message.encode(PROTOCOL['format'])
        message_length = len(message)
        send_length = str(message_length).encode(PROTOCOL['format'])
        send_length += b' ' * (PROTOCOL['header']-len(send_length))
        self.socket.send(send_length)
        self.socket.send(message)

if __name__ == '__main__':
    args = setup_argparser()
    client = Client(server=args.server, port=args.port)
    while True:
        message = input('Enter next message: ')
        client.send(message)
        if message == PROTOCOL['disconnect']: break
        


