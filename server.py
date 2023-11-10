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

    def handle_client(self, conn, addr):
        ''' Handle received data and send appropriate response. '''
        connected = True
        while connected:
            message_length = conn.recv(PROTOCOL['header']).decode(PROTOCOL['format'])
            if message_length: 
                message_length = int(message_length)
                message = conn.recv(message_length).decode(PROTOCOL['format'])
                print(f'[CLIENT {addr}] {message}')
                if message == PROTOCOL['disconnect']: 
                    connected = False
                    print(f'[CLIENT {addr}] Disconnected.')
        conn.close()
        
    def start(self):
        ''' Listens on given port. '''
        self.socket.listen()
        print(f'[SERVER {self.address[0]}] Listening on port {self.address[1]} ...')
        while True:
            socket_connection, address = self.socket.accept()
            print(f'[SERVER {self.address[0]}] Connected to {address}.')
            thread = threading.Thread(target=self.handle_client, args=(socket_connection, address))
            thread.start()
            print(f'[SERVER {self.address[0]}] New connection! No. of active connections = {threading.active_count() - 1}.')

if __name__ == '__main__':
    args = setup_argparser()
    server = Server(host=args.host, port=args.port)