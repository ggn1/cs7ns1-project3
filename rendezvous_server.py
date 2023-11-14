import json
import socket
import argparse
import threading
from protocol import send_tcp
from protocol import make_data_packet

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

    def add_to_pit(self, content_name, incoming_face_name):
        if not content_name in self.pending_interest_table:
            self.pending_interest_table[content_name] = []
        if incoming_face_name not in self.pending_interest_table[content_name]:
            self.pending_interest_table[content_name].append(incoming_face_name) 

    def get_from_pit(self, content_name):
        if content_name in self.pending_interest_table:
            return self.pending_interest_table[content_name]
        else: return []

    def serve_beacon_interested_parties(self, interest):
        # Search Content Store.
        if (interest in self.content_store): # data in CS
            interested = self.get_from_pit(interest)
            for name in interested:
                host, port = self.ndn_ip[name] 
                send_tcp(
                    message=make_data_packet(
                        content_name=f'{self.host}-{self.port}-rendezvous-server/{interest}', 
                        data=self.content_store[interest]['data']
                    ),
                    host=host,
                    port=int(port)
                )
            if interest in self.pending_interest_table:
                self.pending_interest_table.pop(interest)

    def handle_interest_packet(self, packet):
        content_name = packet['content_name'].split('/')
        sender_host, sender_port, sender_name, sender_marker = content_name[0].split('-')
        interest = content_name[1:len(content_name)-1]
        timestamp = content_name[-1]
        self.ndn_ip[sender_name] = (sender_host, sender_port)

        if '/'.join(interest) == 'beacon/on':
            interest = '/'.join(interest)

            # Add this interest to the PIT.
            self.add_to_pit(interest, sender_name)
            self.serve_beacon_interested_parties(interest)

        if '/'.join(interest) == 'beacon/off':
            old_content_src = self.content_store['beacon/on']['content_name'].split('/')[0]
            cur_content_src = content_name[0]
            if (old_content_src == cur_content_src): 
                self.content_store.pop('beacon/on')

    def handle_data_packet(self, packet):
        content_name = packet['content_name'].split('/')
        sender_host, sender_port, sender_name, sender_marker = content_name[0].split('-')
        interest = content_name[1:len(content_name)-1]
        timestamp = content_name[-1]

        if '/'.join(interest) == 'beacon/on':
            interest = '/'.join(interest)
            self.ndn_ip[sender_name] = (sender_host, sender_port)
            self.content_store[interest] = packet
            # It may be that this packet was received after interest was
            # sent. So check CS and return packets corresponding to 
            # interests in PIT upon receiving a new beacon data packet.
            self.serve_beacon_interested_parties(interest)
            print(f'[RENDEZVOUS SERVER] Added {interest} to content store.')

    def handle_incoming(self, conn, addr):
        ''' Handle received data and send appropriate response. '''
        message = conn.recv(2048).decode('utf-8')
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
            self.handle_incoming(socket_connection, address)

if __name__ == '__main__':
    args = setup_argparser()
    server = Server(host=args.host, port=args.port)