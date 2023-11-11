import os
import time
import json
import socket
import random
import argparse
import threading
from protocol import PROTOCOL
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
        # For networking.
        self.name = name
        self.host = host
        self.port = port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM) # IP, TCP
        self.socket.bind((host, port)) # Setting up ears.
        self.marker = marker # The kind of tumour marker this bot detects.
        
        # Sensors and actuators.
        self.__sensors = {
            'sensor_cancer_marker': None, # 1 => detected
            'sensor_beacon': None # position of beacon detected
        }

        self.__actuators = {
            'actuator_tethers': 0, # 1 => extended
            'actuator_head_rotator': 0, # 1 => acceleration (+ve = forward, -ve = backward)
            'actuator_propeller_rotator': 0, # 1 => acceleration (+ve = forward, -ve = backward)
            'actuator_self_destruct': 0, # 1 => detonated
            'actuator_cargo_hatch': 0, # 1 => open
            'actuator_diffuser': 0, # 1 => diffused
        }

        self.set_sensor_beacon(-1)
        self.set_cancer_marker(0)

        if self.marker == CONFIG['primary_marker']: 
            self.__actuators['actuator_beacon'] = 0 # 1 => active.

        # Position in blood stream.
        self.position = random.randint(0, CONFIG['blood_stream_length']-1)

        # # Listen thread.
        # thread_listen = threading.Thread(target=self.listen, args=())
        # thread_listen.start()

        # Move thread.
        thread_move = threading.Thread(target=self.move, args=())
        thread_move.start()

        # Human computer interaction thread.
        thread_hci = threading.Thread(target=self.human_computer_interface, args=())
        thread_hci.start()

    def move(self):
        while True:
            time.sleep(1)
            new_position = self.position + CONFIG['blood_speed'] + (
                self.__actuators['actuator_head_rotator'] 
                + self.__actuators['actuator_propeller_rotator'] 
            )
            if new_position >= CONFIG['blood_stream_length']: new_position = 0
            self.position = int(new_position)

    def listen(self):
        self.socket.listen()
        print(f'[SELF {self.port} {self.port}] Listening on port {self.port} ...')
        while True:
            socket_peer, port_peer = self.socket.accept()
            self.position += 1
            thread_peer = threading.Thread(target=self.handle_peer, args=(port_peer,))
            thread_peer.start()
            print(f'[SELF {self.port} {self.port}] New connection! Connected to {socket_peer}. No. of active connections = {threading.active_count()-1}.')

    def send_tcp(self, message, host, port):
        socket_temp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        socket_temp.connect((host, port))
        message = message.encode('utf-8')
        socket_temp.send(message)
        socket_temp.close()

    def set_sensor_beacon(self, new_value):
        self.__sensors['sensor_beacon'] = new_value
        if (
            self.__sensors['sensor_beacon'] < 0 
            and self.marker != CONFIG['primary_marker']
        ):
            content_name = f'beacon/{self.host}/{self.port}/{self.name}'
            self.send_tcp(
                message=make_interest_packet(content_name=content_name), 
                host=CONFIG['rendezvous_server'][0],
                port=CONFIG['rendezvous_server'][1]
            )

    def handle_actuator_tether(self, tether):
        if tether == 0:
            self.__actuators['actuator_tethers'] = 0
            self.__actuators['actuator_head_rotator'] = 0
            self.__actuators['actuator_propeller_rotator'] = 0
        else:
            self.__actuators['actuator_tethers'] = 1
            self.__actuators['actuator_head_rotator'] = -0.5
            self.__actuators['actuator_propeller_rotator'] = -0.5
            print(f'[{self.host}_{self.port}_{self.name}]: Tethered to {self.position}.')

    def handle_actuator_beacon(self):
        if 'actuator_beacon' in self.__actuators:
            if self.__actuators['actuator_tethers'] == 0:
                self.__actuators['beacon'] = 0
            else:
                self.__actuators['beacon'] = 1
                content_name = f'beacon/{self.host}/{self.port}/{self.name}'
                self.send_tcp(
                    message=make_data_packet(
                        content_name=content_name,
                        data={'position': self.position}
                    ),
                    host=CONFIG['rendezvous_server'][0],
                    port=CONFIG['rendezvous_server'][1]
                )
    
    def set_cancer_marker(self, new_value):
        self.__sensors['sensor_cancer_marker'] = new_value
        if (
            self.__sensors['sensor_cancer_marker'] == 1 
            and self.marker == CONFIG['primary_marker']
        ): self.handle_actuator_tether(1)
        else: self.handle_actuator_tether(0)
        self.handle_actuator_beacon()
            
    def set_sensors(self, new):
        for key, value in new.items():
            if key == 'sensor_beacon':
                self.set_sensor_beacon(value)
                print(f'[NanoBot {self.port}]: Updated sensor_beacon to {value}.')
            if key == 'sensor_cancer_marker':
                self.set_cancer_marker(value)
                print(f'[NanoBot {self.port}]: Updated sensor_cancer_marker to {value}.')

    def human_computer_interface(self):
        while True:
            update = input('Update Sensor Values:')
            print('UPDATE =', update)
            update = json.loads(update)
            self.set_sensors(update)
        
if __name__ == '__main__':
    args = setup_argparser()
    me = Node(host=args.host, port=args.port, marker=args.marker, name=args.name)