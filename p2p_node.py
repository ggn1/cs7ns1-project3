import socket
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

class Node:
    def __init__(self, host, port):
        self.host_port = (host, port) # This node's host-port address.
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM) # IP, TCP
        self.socket.bind(self.host_port) # Setting up ears.
        thread_listen = threading.Thread(target=self.listen, args=()) # Begining to listen.
        thread_listen.start()
        self.connections = []
        # Sensors and actuators.
        self.sensor_cancer_marker = {'detected':0}
        self.sensor_beacon_detector = {'detected':0}
        self.actuator_thethers = {'extended':0}
        self.actuator_head_rotator = {'dir':'right', 'speed':0}
        self.actuator_propeller_rotator = {'dir':'left', 'speed':0}
        self.actuator_beacon = {'active':0}
        self.actuator_self_destruct = {'initiated':0}
        self.actuator_cargo_hatch = {'open':0}

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
        print(f'[SELF {self.host_port[1]} {self.host_port[0]}] Listening on port {self.host_port[1]} ...')
        while True:
            socket_peer, port_peer = self.socket.accept()
            thread_peer = threading.Thread(target=self.handle_peer, args=(port_peer,))
            thread_peer.start()
            print(f'[SELF {self.host_port[1]} {self.host_port[0]}] New connection! Connected to {socket_peer}. No. of active connections = {threading.active_count()-1}.')

if __name__ == '__main__':
    args = setup_argparser()
    me = Node(host=args.host, port=args.port)