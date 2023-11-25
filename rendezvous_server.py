# AUTHOR [START]: Gayathri Girish Nair (23340334)
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

CONFIG = {}
with open('config.json', 'r') as f: 
    CONFIG = json.load(f)

class Server:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM) # IP, TCP
        self.socket.bind((host, port))
        self.non_primary_bots = {}
        self.primary_bots = {}
        self.listen()

    def serve_beacon_interested_parties(self):
        # For every interested non-primary bot,
        # check if there is a free primary bot
        # that either has a spot in its neighbors list for this 
        # bot's marker type or has this bot already registered 
        # as a neighbor. If so, assign corresponding primary
        # bot to this non-primary bot and send the primary
        # bot's information to this bot.
        for np_bot_name, np_bot_data in self.non_primary_bots.items():
            if np_bot_data['primary_bot'] is None:
                for p_bot_name, p_bot_data in self.primary_bots.items():
                    if p_bot_data['non_primary_bots'][np_bot_data['marker']] is None:
                        p_bot_data['non_primary_bots'][np_bot_data['marker']] = np_bot_name
                    if p_bot_data['non_primary_bots'][np_bot_data['marker']] == np_bot_name:
                        self.non_primary_bots[np_bot_name]['primary_bot'] = p_bot_name
                        send_tcp(
                            message=make_data_packet(
                                content_name=f'{self.host}-{self.port}-rendezvous-server/beacon/on', 
                                data={
                                    'name': p_bot_name, 
                                    'host': p_bot_data['host'], 
                                    'port': p_bot_data['port'],
                                    'position': p_bot_data['position'],
                                }
                            ),
                            host=np_bot_data['host'],
                            port=int(np_bot_data['port'])
                        )

    def handle_interest_packet(self, packet):
        content_name = packet['content_name'].split('/')
        sender_host, sender_port, sender_name, sender_marker = content_name[0].split('-')
        interest = content_name[1:len(content_name)-1]

        if '/'.join(interest) == 'beacon/on':
            interest = '/'.join(interest)
            # If it's a non-primary bot, add to dictionary of non-primary bots.
            if sender_marker != CONFIG['primary_marker']:
                self.non_primary_bots[sender_name] = {
                    'host': sender_host,
                    'port': sender_port,
                    'marker': sender_marker,
                    'primary_bot': None
                }
                self.serve_beacon_interested_parties()
            # Sender cannot be a primary bot.
            else:
                pass

        elif '/'.join(interest) == 'beacon/off':
            if sender_name in self.primary_bots:
                self.primary_bots.pop(sender_name)
                for np_bot_data in self.non_primary_bots.values():
                    if np_bot_data['primary_bot'] == sender_name:
                        np_bot_data['primary_bot'] = None

    def handle_data_packet(self, packet):
        content_name = packet['content_name'].split('/')
        data = packet['data']
        sender_host, sender_port, sender_name, sender_marker = content_name[0].split('-')
        interest = content_name[1:len(content_name)-1]

        if '/'.join(interest) == 'beacon/on':
            self.primary_bots[sender_name] = {
                'host': sender_host,
                'port': sender_port,
                'position': data['position'],
                'non_primary_bots': {marker:None for marker in CONFIG['markers']}
            }
            self.serve_beacon_interested_parties()

    def handle_incoming(self, conn):
        ''' Handle received data and send appropriate response. '''
        message = conn.recv(2048).decode('utf-8')
        packet = json.loads(message)
        if packet['type'] == 'data': self.handle_data_packet(packet)
        else: self.handle_interest_packet(packet)
        conn.close()
        
    def listen(self):
        ''' Listens on given port. '''
        self.socket.listen()
        print(f'[RENDEZVOUS SERVER] Listening on {self.host} port {self.port} ...')
        while True:
            socket_connection, address = self.socket.accept()
            self.handle_incoming(socket_connection)

if __name__ == '__main__':
    args = setup_argparser()
    server = Server(host=args.host, port=args.port)
# AUTHOR [END]: Gayathri Girish Nair (23340334)