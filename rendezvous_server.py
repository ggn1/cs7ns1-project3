import json
import socket
import argparse
import threading
from protocol import PROTOCOL

def setup_argparser():
    ''' Adds arguments.
        --host
        --port
    '''
    parser = argparse.ArgumentParser()

    parser.add_argument(
        '--host', 
        help='IP address of server.', 
        type=str
    )

    parser.add_argument(
        '--port', 
        help='Port number.', 
        type=int
    )

    args = parser.parse_args()

    if args.host is None:
        print("Please specify host address.")
        exit(1)
    
    if args.port is None:
        print("Please specify port number.")
        exit(1)

    return args

class Server:
    def __init__(self, host, port):
        self.address = (host, port)
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM) # IP, TCP
        self.socket.bind(self.address)
        self.start()

    def handle_interest_packet(self, packet):
        pass

    def handle_data_packet(self, packet):
        pass

    def handle_incoming(self, conn, addr):
        ''' Handle received data and send appropriate response. '''
        message = conn.recv(1024).decode('utf-8')
        packet = json.loads(message)
        print(f'Message received from {addr}: {packet}')
        conn.close()
        
    def start(self):
        ''' Listens on given port. '''
        self.socket.listen()
        print(f'[SERVER {self.address[0]}] Listening on port {self.address[1]} ...')
        while True:
            socket_connection, address = self.socket.accept()
            print(f'[SERVER {self.address[0]}] Connected to {address}.')
            self.handle_incoming(socket_connection, address)

if __name__ == '__main__':
    args = setup_argparser()
    server = Server(host=args.host, port=args.port)