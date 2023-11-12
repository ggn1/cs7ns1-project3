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
        self.lock = threading.Lock()
        
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

        self.neighbors = {}

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

    def add_to_pit(self, content_name, face):
        if not content_name in self.pending_interest_table:
            self.pending_interest_table[content_name] = []
        self.pending_interest_table[content_name].append(face)    

    def handle_interest_packet(self, packet):
        content_name = packet['content_name'].split('/')
        sender_host, sender_port, sender_name = content_name[0].split('-')
        sender_port = int(sender_port)
        interest_name = content_name[1:len(content_name)-1] # [<marker>, neighbor]
        timestamp = content_name[-1]
        print(f'[{self.name}] Received interest packet = {packet}.')

        # Neighbor discovery.
        if 'neighbor' in interest_name: # Only a primary node ever receives this.
            if not f'marker/{interest_name[0]}' in self.forwarding_information_base:

                # Add to neighbor table and FIB.
                self.neighbors[sender_name] = {
                    'host': sender_host, 
                    'port': int(sender_port)
                }
                self.forwarding_information_base[f'marker/{interest_name[0]}'] = sender_name
                if len(self.neighbors) > 2: # Max 2 neighbors only.
                    n = next(iter(self.neighbors))
                    self.neighbors.pop(n)
                    for marker, name in self.forwarding_information_base.items():
                        if name == n:
                            self.forwarding_information_base.pop(marker)
                            break
                
                # Add to PIT.
                self.add_to_pit(interest_name[1], (sender_name, interest_name[0]))
                print(f'[{self.name}] Discovered neighbor {sender_name}.')

                # Check FIB to see if there exists a suitable neighbor for
                # any interested party in the PIT. If so, send a data packet to them
                # with this suitable neighbor's information and remove corresponding
                # interest from PIT.
                interested_parties = self.pending_interest_table[interest_name[1]]
                to_pop = []
                for i in range(1, len(interested_parties)+1):
                    pit_name_marker = interested_parties[-1*i]
                    for j in range(1, len(self.forwarding_information_base.keys())+1): 
                        fib_marker_name = list(self.forwarding_information_base.items())[-1*j]
                        if f'marker/{pit_name_marker[1]}' != fib_marker_name[0]:
                            # print(f'marker/{pit_name_marker[1]} != {marker}', pit_name_marker[0], self.neighbors[pit_name_marker[0]])
                            message = make_data_packet(
                                content_name=f'{self.host}-{self.port}-{self.name}/{interest_name[1]}',
                                data={
                                    'name': fib_marker_name[1],
                                    'marker': fib_marker_name[0],
                                    'host': self.neighbors[fib_marker_name[1]]['host'],
                                    'port': self.neighbors[fib_marker_name[1]]['port']
                                }
                            )
                            send_tcp(
                                message=message,
                                host=self.neighbors[pit_name_marker[0]]['host'],
                                port=self.neighbors[pit_name_marker[0]]['port']
                            )
                            to_pop.append(pit_name_marker)
                            break
                for v in to_pop: 
                    interested_parties.pop(interested_parties.index(v))
                if len(interested_parties) == 0:
                    self.pending_interest_table.pop(interest_name[1])
                else:
                    self.pending_interest_table[interest_name[1]] = interested_parties

    def handle_data_packet(self, packet):
        content_name = packet['content_name'].split('/')
        sender_host, sender_port, sender_name = content_name[0].split('-')
        sender_port = int(sender_port)
        data_name = content_name[1:len(content_name)-1]
        timestamp = content_name[-1]
        print(f'[{self.name}] Received data packet = {packet}.')
        
        # Data packet is of type beacon.
        if 'beacon' in data_name:
            data = packet['data']
            self.set_beacon(data['position'])
            self.neighbors[sender_name] = {
                'host': sender_host,
                'port': sender_port
            }
            self.forwarding_information_base[
                f'marker/{CONFIG["primary_marker"]}'
            ] = sender_name

        # Neighbor discovery.
        if 'neighbor' in data_name:
            data = packet['data'] #  {'marker':str, 'name':str, 'host':str, 'port':int}
            if (
                not (f'marker/{data["marker"]}' in self.forwarding_information_base)
                and data["marker"] != self.marker
            ):
                # Add to neighbors and FIB.
                self.neighbors[data['name']] = {
                    'host': data['host'],
                    'port': data['port']
                }
                self.forwarding_information_base[f'marker/{data["marker"]}'] = data['name']
                print(f'[{self.name}] Discovered neighbor {data["name"]}.')

    def neighbor_discovery(self):
        ''' Discovers all neighbors. '''
        # print(f'[{self.name}] Discovering 3 neighbors ...')
        message = f'{self.host}-{self.port}-{self.name}/{self.marker}/neighbor'
        neighbor_first = self.neighbors[list(self.neighbors.keys())[0]]
        send_tcp(
            message=make_interest_packet(message),
            host=neighbor_first['host'],
            port=neighbor_first['port']
        )
        
    def handle_incoming(self, conn):
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
            self.handle_incoming(socket_connection)

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