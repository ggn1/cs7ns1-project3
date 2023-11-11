import os
import time
import json
import socket
import random
import argparse
import threading
from protocol import PROTOCOL
from protocol import make_interest_packet
from protocol import message_decode
from protocol import message_encode

def setup_argparser():
    ''' Adds arguments.
        --host
    '''
    ''' Adds arguments.
        --host
        --port
    '''
    parser = argparse.ArgumentParser()

    parser.add_argument(
        '--host', 
        help='IP address of this node.', 
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
with open('config.json', 'r') as f: CONFIG = json.load(f)

class Node:
    def __init__(self, host, port):
        # For networking.
        self.host = host
        self.port = port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM) # IP, TCP
        self.socket.bind((host, port)) # Setting up ears.
        self.connections = []
        
        # Sensors and actuators.
        self.__sensors = {
            'sensor_cancer_marker': 0, # 1 => detected
            'sensor_beacon_detector': 0 # 1 => detected
        }

        self.__actuators = {
            'actuator_tethers': 0, # 1 => extended
            'actuator_head_rotator': 0, # 1 => acceleration (+ve = forward, -ve = backward)
            'actuator_propeller_rotator': 0, # 1 => acceleration (+ve = forward, -ve = backward)
            'actuator_beacon': 0, # 1 => active
            'actuator_self_destruct': 0, # 1 => detonated
            'actuator_cargo_hatch': 0, # 1 => open
        }
        
        # Position in blood stream.
        self.position = random.randint(0, CONFIG['blood_stream_length']-1)

        # Listen thread.
        thread_listen = threading.Thread(target=self.listen, args=())
        thread_listen.start()

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

    def handle_peer(self, port_peer):
        ''' Handles new connection to a peer. '''
        is_connected = True
        while is_connected:
            message, is_connected = message_decode(self.connections[port_peer])
            if message: print(f'[PEER {port_peer}] {message}')
        self.connections[port_peer].close()
        del self.connections[port_peer]

    def listen(self):
        self.socket.listen()
        print(f'[SELF {self.port} {self.port}] Listening on port {self.port} ...')
        while True:
            socket_peer, port_peer = self.socket.accept()
            self.position += 1
            thread_peer = threading.Thread(target=self.handle_peer, args=(port_peer,))
            thread_peer.start()
            print(f'[SELF {self.port} {self.port}] New connection! Connected to {socket_peer}. No. of active connections = {threading.active_count()-1}.')

    def set_sensors(self, new):
        old = {}
        for key, value in new.items():
            if key in self.__sensors:
                old[key] = self.__sensors[key]
                self.__sensors[key] = value
        print(f'[NanoBot {self.port}]: Updated sensor values from {old} to {new}.')

    def human_computer_interface(self):
        while True:
            update = input('Update Sensor Values:')
            print('UPDATE =', update)
            update = json.loads(update)
            self.set_sensors(update)
        
if __name__ == '__main__':
    args = setup_argparser()
    me = Node(host=args.host, port=args.port)