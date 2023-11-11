import json
import socket
import argparse
import threading
from protocol import send_tcp

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
        self.host = host
        self.port = port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM) # IP, TCP
        self.socket.bind((host, port))
        self.content_store = {}
        self.pending_interest_table = {}
        self.forwarding_information_base = {}
        self.ndn_ip = {}
        self.listen()

    def handle_interest_packet(self, packet):
        content_name = packet['content_name'].split('/')
        sender_host, sender_port, sender_name = content_name[0].split('-')
        data_name = '/'.join(content_name[1:len(content_name)-1])
        timestamp = content_name[-1]
        self.ndn_ip[sender_name] = (sender_host, sender_port)

        # Add this interest to the PIT.
        if (data_name in self.pending_interest_table): # data_name exists
            incoming_faces = self.pending_interest_table[data_name]
            if not sender_name in incoming_faces: # if this sender is not already in the list 
                self.pending_interest_table[data_name].append(sender_name)
        else: # data_name does not exist
            self.pending_interest_table[data_name] = [sender_name]

        # Search Content Store
        if (data_name in self.content_store): # data in CS
            interested = self.pending_interest_table[data_name]
            for name in interested:
                host, port = self.ndn_ip[name] 
                send_tcp(
                    message=json.dumps(self.content_store[data_name]),
                    host=host, port=int(port)
                )
            del self.pending_interest_table[data_name]

    def handle_data_packet(self, packet):
        content_name = packet['content_name'].split('/')
        sender_host, sender_port, sender_name = content_name[0].split('-')
        data_name = '/'.join(content_name[1:len(content_name)-1])
        timestamp = content_name[-1]
        data = packet['data']
        self.ndn_ip[sender_name] = (sender_host, sender_port)
        self.content_store[data_name] = data
        print(f'[RENDEZVOUS SERVER] Added {data_name} to content store.')

    def handle_incoming(self, conn, addr):
        ''' Handle received data and send appropriate response. '''
        message = conn.recv(1024).decode('utf-8')
        packet = json.loads(message)
        if packet['type'] == 'data':
            self.handle_data_packet(packet)
        else:
            self.handle_interest_packet(packet)
        conn.close()
        
    def listen(self):
        ''' Listens on given port. '''
        self.socket.listen()
        print(f'[RENDEZVOUS SERVER] Listening on {self.host} port {self.port} ...')
        while True:
            socket_connection, address = self.socket.accept()
            # print(f'[RENDEZVOUS SERVER] Connected to {address}.')
            self.handle_incoming(socket_connection, address)

if __name__ == '__main__':
    args = setup_argparser()
    server = Server(host=args.host, port=args.port)