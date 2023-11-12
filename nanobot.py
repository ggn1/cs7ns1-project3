import os
import time
import json
import socket
import random
import argparse
import threading
from protocol import send_tcp
from protocol import make_interest_packet
from protocol import make_data_packet

def setup_argparser():
    ''' Adds arguments.
        --host
    '''
    ''' Adds arguments.
        --host
        --port
        --marker
        --name
    '''
    parser = argparse.ArgumentParser()

    parser.add_argument(
        '--host', 
        help='IP address of this node.', 
        type=str
    )

    parser.add_argument(
        '--marker', 
        help='Kind of cancer marker this bot senses.', 
        type=str
    )

    parser.add_argument(
        '--name', 
        help='Name of this bot.', 
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

    if args.marker is None:
        print("Please specify marker.")
        exit(1)

    if args.name is None:
        print("Please specify a name.")
        exit(1)
    
    if args.port is None:
        print("Please specify port number.")
        exit(1)

    return args

CONFIG = {}
with open('config.json', 'r') as f: CONFIG = json.load(f)

class Node:
    def __init__(self, host, port, marker, name):
        self.name = name
        self.host = host
        self.port = port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM) # IP, TCP
        self.socket.bind((host, port)) # Setting up ears.
        self.marker = marker # The kind of tumour marker this bot detects.
        
        # Sensors and actuators.
        self.__sensors = {
            'cancer_marker': None, # 1 => detected
            'beacon': None # position of beacon detected
        }

        self.__actuators = {
            'tethers': 0, # 1 => extended
            'head_rotator': 0, # 1 => acceleration (+ve = forward, -ve = backward)
            'propeller_rotator': 0, # 1 => acceleration (+ve = forward, -ve = backward)
            'self_destruct': 0, # 1 => detonated
            'cargo_hatch': 0, # 1 => open
            'diffuser': 0, # 1 => diffused
        }

        # NDN
        self.content_store = {
            f'marker/{self.marker}': self.__sensors['cancer_marker']
        }
        self.pending_interest_table = {}
        self.forwarding_information_base = {}

        self.set_beacon(-1)
        self.set_cancer_marker(0)

        if self.marker == CONFIG['primary_marker']: 
            self.__actuators['actuator_beacon'] = 0 # 1 => active.

        # Position in blood stream.
        self.position = random.randint(0, CONFIG['blood_stream_length']-1)

        # Listen thread.
        thread_listen = threading.Thread(target=self.listen, args=())
        thread_listen.start()

        # Move thread.
        thread_move = threading.Thread(target=self.move, args=())
        thread_move.start()

        # Human computer interaction thread.
        if self.marker == CONFIG['primary_marker']:
            thread_hci = threading.Thread(target=self.human_computer_interface, args=())
            thread_hci.start()

    def handle_interest_packet(self, packet):
        content_name = packet['content_name'].split('/')
        sender_host, sender_port, sender_name = content_name[0].split('-')
        sender_port = int(sender_port)
        data_name = content_name[1:len(content_name)-1]
        timestamp = content_name[-1]
        # print(f'[{self.name}] Received interest packet = {packet}.')

        # Neighbor discovery (not routing).
        if 'neighbor' in data_name: # Only a primary node ever receives this.
            neighbor_marker = f'marker/{data_name[1]}'
            if not neighbor_marker in self.forwarding_information_base:
                self.forwarding_information_base[neighbor_marker] = {
                    'host': sender_host, 
                    'port': sender_port,
                    'name': sender_name
                }
                print(f'[{self.name}] Discovered neighbor {sender_name}.')
            
            eligible_neighbors = []
            for name, face in self.forwarding_information_base.items():
                if 'marker' in name:
                    marker = name[name.find('/')+1:]
                    if marker != self.marker and marker != neighbor_marker:
                        eligible_neighbors.append({
                            'content_name': f'{self.host}-{self.port}-{self.name}/neighbor',
                            'data': {
                                'marker': marker, 
                                'name': face['name'],
                                'host': face['host'],
                                'port': face['port']
                            }
                        })
            if len(eligible_neighbors) > 0:
                neighbor = eligible_neighbors[
                    random.randint(0, len(eligible_neighbors)-1)
                ]
                message = make_data_packet(
                    content_name=neighbor['content_name'],
                    data=neighbor['data']
                )
                send_tcp(
                    message=message,
                    host=sender_host,
                    port=sender_port
                )

    def handle_data_packet(self, packet):
        content_name = packet['content_name'].split('/')
        sender_host, sender_port, sender_name = content_name[0].split('-')
        sender_port = int(sender_port)
        data_name = content_name[1:len(content_name)-1]
        timestamp = content_name[-1]
        # print(f'[{self.name}] Received data packet = {packet}.')
        
        # Data packet is of type beacon.
        if 'beacon' in data_name:
            data = packet['data']
            self.set_beacon(data['position'])
            self.forwarding_information_base[f'marker/{CONFIG["primary_marker"]}'] = {
                'host': sender_host,
                'port': sender_port,
                'name': sender_name
            }
            
        # Neighbor discovery.
        if 'neighbor' in data_name:
            # Data format = {'marker':str, 'name':str, 'host':str, 'port':int}
            data = packet['data']
            if (
                not (f'marker/{data["marker"]}' in self.forwarding_information_base)
                and data["marker"] != self.marker
            ):
                self.forwarding_information_base[f'marker/{data["marker"]}'] = {
                    'host': data['host'],
                    'port': data['port'],
                    'name': data['name']
                }
                print(f'[{self.name}] Discovered neighbor {data["name"]}.')

    def neighbor_discovery(self):
        ''' Discovers all neighbors. '''
        print(f'[{self.name}] Discovering 3 neighbors ...')
        
        while len(self.forwarding_information_base) < CONFIG['num_neighbors']:
            primary_host = self.forwarding_information_base[
                f'marker/{CONFIG["primary_marker"]}'
            ]['host']
            primary_port = int(self.forwarding_information_base[
                f'marker/{CONFIG["primary_marker"]}'
            ]['port'])
            message = f'{self.host}-{self.port}-{self.name}/neighbor/{self.marker}'
            send_tcp(
                message=make_interest_packet(message),
                host=primary_host,
                port=primary_port
            )
            time.sleep(1)

        print(f'[{self.name}] Neighbor discovery complete.')
        
        

    def handle_incoming(self, conn, addr):
        ''' Handle received data and send appropriate response. '''
        message = conn.recv(1024).decode('utf-8')
        packet = json.loads(message)
        # print(f'[{self.name}] Message received from {addr}: {packet}.')
        if packet['type'] == 'data':
            self.handle_data_packet(packet)
        else:
            self.handle_interest_packet(packet)
        conn.close()

    def listen(self):
        ''' Listens on given port. '''
        self.socket.listen()
        print(f'[{self.name}] Listening on {self.host} port {self.port} ...')
        while True:
            socket_connection, address = self.socket.accept()
            self.handle_incoming(socket_connection, address)

    def move(self):
        while True:
            time.sleep(1)
            new_position = self.position + CONFIG['blood_speed'] + (
                self.__actuators['head_rotator'] 
                + self.__actuators['propeller_rotator'] 
            )
            if new_position >= CONFIG['blood_stream_length']: new_position = 0
            self.position = int(new_position)
            if (
                self.__sensors['beacon'] == self.position
                and self.__actuators['tethers'] != 1
            ): self.handle_actuator_tether(tether=1)

    def search_beacon(self):
        print(f'[{self.name}] Searching for beacon ...')
        while (
            self.__sensors['beacon'] < 0 
            and self.marker != CONFIG['primary_marker']
        ):
            time.sleep(1)
            content_name = f'{self.host}-{self.port}-{self.name}/beacon'
            send_tcp(
                message=make_interest_packet(content_name=content_name), 
                host=CONFIG['rendezvous_server'][0],
                port=CONFIG['rendezvous_server'][1]
            )
        print(f'[{self.name}] Beacon found at {self.__sensors["beacon"]}.')

    def set_beacon(self, new_value):
        self.__sensors['beacon'] = new_value
        if (
            self.__sensors['beacon'] < 0 
            and self.marker != CONFIG['primary_marker']
        ):
            thread_search_beacon = threading.Thread(target=self.search_beacon, args=())
            thread_search_beacon.start()

    def handle_actuator_tether(self, tether):
        if tether == 0:
            self.__actuators['tethers'] = 0
            self.__actuators['head_rotator'] = 0
            self.__actuators['propeller_rotator'] = 0
        else:
            self.__actuators['tethers'] = 1
            self.__actuators['head_rotator'] = -0.5
            self.__actuators['propeller_rotator'] = -0.5
            print(f'[{self.name}] Tethered to {self.position}.')
            
            # Non primary nodes initiate neighbor discovery.
            if self.marker != CONFIG['primary_marker']:
                self.neighbor_discovery()

    def handle_actuator_beacon(self):
        if 'actuator_beacon' in self.__actuators:
            if self.__actuators['tethers'] == 0:
                self.__actuators['beacon'] = 0
            else:
                self.__actuators['beacon'] = 1
                content_name = f'{self.host}-{self.port}-{self.name}/beacon'
                send_tcp(
                    message=make_data_packet(
                        content_name=content_name,
                        data={
                            'position': self.position, 
                            'host': self.host, 
                            'port':self.port
                        }
                    ),
                    host=CONFIG['rendezvous_server'][0],
                    port=CONFIG['rendezvous_server'][1]
                )
    
    def set_cancer_marker(self, new_value):
        self.__sensors['cancer_marker'] = new_value
        if (
            self.__sensors['cancer_marker'] == 1 
            and self.marker == CONFIG['primary_marker']
        ): self.handle_actuator_tether(1)
        else: self.handle_actuator_tether(0)
        self.handle_actuator_beacon()
            
    def set_sensors(self, new):
        for key, value in new.items():
            if key == 'beacon':
                self.set_beacon(value)
                print(f'[{self.port}]: Updated beacon to {value}.')
            if key == 'cancer_marker':
                self.set_cancer_marker(value)
                print(f'[{self.port}]: Updated cancer_marker to {value}.')

    def human_computer_interface(self):
        while True:
            update = input('Update Sensor Values:')
            print('UPDATE =', update)
            update = json.loads(update)
            self.set_sensors(update)
        
if __name__ == '__main__':
    args = setup_argparser()
    me = Node(host=args.host, port=args.port, marker=args.marker, name=args.name)