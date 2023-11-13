import os
import time
import json
import socket
import random
import signal
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
        self.knowledge = {m:-1 for m in CONFIG['markers']}
        
        # Sensors and actuators.
        self.__sensors = {
            'cancer_marker': -1, # 1 => detected
            'beacon': -1 # position of beacon detected
        }

        self.__actuators = {
            'tethers': 0, # 1 => extended
            'head_rotator': 0, # 1 => accelself.content_storeeration (+ve = forward, -ve = backward)
            'propeller_rotator': 0, # 1 => acceleration (+ve = forward, -ve = backward)
            'self_destruct': 0, # 1 => detonated
            'cargo_hatch': 0, # 1 => open
            'diffuser': 0, # 1 => diffused
        }

        self.neighbors = {}

        # NDN
        self.content_store = {
            f'marker/{self.marker}': self.sense_cancer_marker()
        }
        self.pending_interest_table = {}
        self.forwarding_information_base = {}

        self.set_beacon(-1)
        self.set_cancer_marker(0)

        if self.marker == CONFIG['primary_marker']: 
            self.__actuators['actuator_beacon'] = 0 # 1 => active.
            self.num_neighbors_seen = 0

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

    def sense_cancer_marker(self):
        ''' Returns latest value in sensor. '''
        return self.__sensors['cancer_marker']

    def add_to_pit(self, content_name, incoming_face_name):
        if not content_name in self.pending_interest_table:
            self.pending_interest_table[content_name] = []
        self.pending_interest_table[content_name].append(incoming_face_name)    

    def get_from_pit(self, content_name):
        if content_name in self.pending_interest_table:
            return self.pending_interest_table[content_name]
        else: return None

    def add_to_fib(self, content_name, outgoing_face_name):
        if not content_name in self.forwarding_information_base:
            self.forwarding_information_base[content_name] = {}
        if outgoing_face_name in self.forwarding_information_base[content_name]:
            self.forwarding_information_base[content_name][outgoing_face_name] += 1
        else: 
            self.forwarding_information_base[content_name][outgoing_face_name] = 0

    def get_from_fib(self, content_name, get_cost=False):
        ''' Gets lest costly neighbor. '''
        if content_name in self.forwarding_information_base:
            routes = self.forwarding_information_base[content_name] # {neighbor1:cost, neighbor2:cost, ...}
            least_costly = None
            for neighbor, cost in routes.items():
                if not least_costly: least_costly = (neighbor, cost)
                elif cost < least_costly[1]: least_costly = (neighbor, cost)
            return least_costly[0] if not get_cost else least_costly
        else: return None

    def get_random_viable_neighbor(self, sender_name):
        ''' Returns the name of a neighbor that is not the sender. '''
        neighbors = list(self.neighbors.keys())
        while True:
            n = neighbors[random.randint(0, len(neighbors)-1)]
            if n != sender_name: 
                return n

    def get_fwd_neighbor(self, content_name, sender_name):
        ''' Get the name of a node to which a packet with 
            given content name can be forwarded to.
        '''
        # Check if known route exists for given content.
        fwd_neighbour = self.get_from_fib(content_name, get_cost=True) # (name, cost)
       
        if fwd_neighbour is None: # If not, then pick a
            # random viable neighbor (neighbor that is not the sender),
            # and return this name. Enter this chosen route 
            # into the FIB initially with cost 0.
            fwd_neighbour = self.get_random_viable_neighbor(sender_name)

        else: # If a known route exists,
            if fwd_neighbour[0] != sender_name: # check it's cost.
                if fwd_neighbour[1] > 0: # If cost > 0 then there may be a better path.
                    all_routes = self.forwarding_information_base[content_name]
                    # Check if there is an unexplored viable neighbor
                    # and consider this neighbor if found.
                    if len(all_routes) < len(self.neighbors):
                        for n in self.neighbors.keys():
                            if n not in all_routes and n != sender_name:
                                fwd_neighbour = n
                                break
                    # If there are already no. of routes for this content
                    # equal to no. of neighbors, then this means that current 
                    # route is the best possible one.
                    else: 
                        fwd_neighbour = fwd_neighbour[0]
                else: # If cost is 0, then this is the best option.
                    fwd_neighbour = fwd_neighbour[0]
            else: # If returned path is not viable.
                # Check to see if there is another known viable route.
                # If found, this is the node to send the packet to.
                all_routes = self.forwarding_information_base[content_name]
                for n in all_routes.keys():
                    if n != sender_name: 
                        fwd_neighbour = n
                        break
                # Else pick a random viable neighbor
                fwd_neighbour = self.get_random_viable_neighbor(sender_name)
            # Note: "Viable" neighbour here means a node that is not the sender.
        
        # Once a suitable neighbor has been identified to send the packet to, 
        # return name of this neighbour and add/update chosen path in FIB.
        self.add_to_fib(content_name, fwd_neighbour)
        return fwd_neighbour

    def add_to_cs(self, content_name, data):
        ''' Adds data with given name to the content store. '''
        self.content_store[content_name] = data

    def get_from_cs(self, content_name):
        ''' Gets data from content store if available
            else, returns None. '''
        if content_name in self.content_store:
            return self.content_store[content_name]
        else: return None

    def handle_interest_packet(self, packet):
        content_name = packet['content_name'].split('/')
        sender_host, sender_port, sender_name = content_name[0].split('-')
        sender_port = int(sender_port)
        data_name = content_name[1:len(content_name)-1]
        timestamp = content_name[-1]

        # Neighbor discovery.
        if 'neighbor' in data_name: # Only a primary node ever receives this.
            sender_marker_interest = data_name # [<marker>, neighbor]
            fib_content_name = f'marker/{sender_marker_interest[0]}'
            if not fib_content_name in self.forwarding_information_base:

                # Add to neighbor table and FIB.
                self.neighbors[sender_name] = {
                    'host': sender_host, 
                    'port': int(sender_port)
                }
                self.add_to_fib(
                    content_name=fib_content_name,
                    outgoing_face_name=sender_name
                )

                # Add to PIT.
                self.add_to_pit(
                    content_name=sender_marker_interest[1], 
                    incoming_face_name=(sender_name, sender_marker_interest[0])
                )
                print(f'[{self.name}] Discovered neighbor {sender_name}.')
                self.num_neighbors_seen += 1

                # Check FIB to see if there exists a suitable neighbor for
                # any interested party in the PIT. If so, send a data packet to them
                # with this suitable neighbor's information and remove corresponding
                # interest from PIT.
                interested_parties = self.pending_interest_table[sender_marker_interest[1]]
                to_pop = []
                for i in range(1, len(interested_parties)+1):
                    pit_name_marker = interested_parties[-1*i]
                    for j in range(1, len(self.forwarding_information_base.keys())+1): 
                        fib_marker_faces = list(self.forwarding_information_base.items())[-1*j]
                        fib_marker_name = [
                            fib_marker_faces[0].split('/')[1],
                            self.get_from_fib(fib_marker_faces[0])
                        ]
                        if f'marker/{pit_name_marker[1]}' != fib_marker_faces[0]:
                            message = make_data_packet(
                                content_name=f'{self.host}-{self.port}-{self.name}/{sender_marker_interest[1]}',
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
                    self.pending_interest_table.pop(sender_marker_interest[1])
                else:
                    self.pending_interest_table[sender_marker_interest[1]] = interested_parties

            if len(self.neighbors) == (len(CONFIG['markers'])-1):
                # Primary bot neighbor discovery complete.
                # So, turn off beacon and start 
                # decision making protocol.
                send_tcp(
                    message=make_interest_packet(
                        content_name=f'{self.host}-{self.port}-{self.name}/beacon/off'
                    ), 
                    host=CONFIG['rendezvous_server'][0],
                    port=CONFIG['rendezvous_server'][1]
                )
                self.set_beacon(new_value=-1)
                print(f'[{self.name}] Neighbor discovery complete. Turned off beacon.')
                print(f'[{self.name}] FIB = {self.forwarding_information_base}.')
                self.start_decision_making()

        # NDN Routing.
        else: 
            print(f'[{self.name}] Received interest packet = {packet}.')
            interest = '/'.join(data_name)

            # Add interest to PIT.
            self.add_to_pit(content_name=interest, incoming_face_name=sender_name)
            
            # Check CS to determine if you have the content.
            cs = self.get_from_cs(content_name=interest)
            if cs is None: # If this peer does not have the content,
                # get a suitable neighbour to forward this packet to
                # and send it to them.
                fwd_neighbor = self.get_fwd_neighbor(
                    content_name=interest, 
                    sender_name=sender_name
                )
                send_tcp(
                    message=make_interest_packet(
                        content_name=f'{self.host}-{self.port}-{self.name}/{interest}'
                    ), 
                    host=self.neighbors[fwd_neighbor]['host'],
                    port=self.neighbors[fwd_neighbor]['port']
                )
            else: # If this peer has the content
                # then check the PIT table and send
                # a data packet to all interested parties.
                interested = self.get_from_pit(content_name=interest)
                if not interested is None:
                    # interested = ['neighbor1', 'neighbor2', ...]
                    while len(interested) > 0:
                        name = interested.pop(-1)
                        send_tcp(
                            message=make_data_packet(
                                content_name=f'{self.host}-{self.port}-{self.name}/{interest}',
                                data={'cancer_marker':{'marker':self.marker, 'value':cs}}
                            ),
                            host=self.neighbors[name]['host'],
                            port=self.neighbors[name]['port']
                        )
                    self.pending_interest_table.pop(interest)

    def set_actuator(self, actuator, value):
        ''' Sets value of actuators. '''
        self.__actuators[actuator] = value
        if actuator == 'cargo_hatch':
            if value == 1: 
                print(f'[{self.name}]: Hatch open. Thrombin deployed.')
            else:
                print(f'[{self.name}]: Hatch closed.')
        if actuator == 'self_destruct':
            if value == 1:
                print(f'Detonated at position {self.position}.')
                os.kill(os.getpid(), signal.SIGTERM)

    def initiate_attack_sequence(self):
        ''' Attack protocol that each bot executes
            to destroy cancer cells. '''
        self.set_actuator('cargo_hatch', 1)
        print(f'[{self.name}]: Preparing to self-destruct.')
        time.sleep(2)
        self.set_actuator('self_destruct', 1)
    
    def initiate_state_reset(self):
        ''' Protocol that bots execute to untether and 
            continue operation. '''
        pass

    def handle_decision(self, decision):
        ''' Take action based on decision made. '''
        time.sleep(3) # Sleep to allow time for any pending communications.
        if decision == 'cancer':
            self.initiate_attack_sequence()
        else: 
            self.initiate_state_reset()

    def satisfy_interest(self, interest, data_packet):
        ''' Handles desired data packet. '''
        data = data_packet['data']
        
        # Decision making.
        # If a peer cancer marker data is available, then 
        # update own knowledge and see if a decision can be made.
        if 'marker' in interest:
            # data = {'cancer_marker': 'marker': <marker type>, 'value': <marker value>}
            self.knowledge[data['cancer_marker']['marker']] = data['cancer_marker']['value']
            marker_values = list(self.knowledge.values())
            # If all marker values are known, share decision with all peers.
            if marker_values.count(-1) == 0:
                decision = 'healthy'
                if sum(marker_values) == len(CONFIG['markers']):
                    decision = 'cancer'
                print(f'[{self.name}] Decision = {decision}!')
                self.handle_decision(decision)
                
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
            self.neighbors[sender_name] = {
                'host': sender_host,
                'port': sender_port
            }
            self.add_to_fib(
                content_name=f'marker/{CONFIG["primary_marker"]}',
                outgoing_face_name=sender_name
            )

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
                self.add_to_fib(
                    content_name=f'marker/{data["marker"]}', 
                    outgoing_face_name=data['name']
                )
                print(f'[{self.name}] Discovered neighbor {data["name"]}.')
                print(f'[{self.name}] Neighbor discovery complete.')
                
                # Bot neighbor discovery complete.
                # So, start decision making protocol.
                self.start_decision_making()

        # NDN Routing
        else: 
            interest = '/'.join(data_name)
            # Check PIT table.
            interested = self.get_from_pit(interest)
            # If there are interested parties for this 
            # packet, proceed, else drop it.
            if not interested is None:
                while len(interested) > 0:
                    # If other peers had previously 
                    # expressed interest in this packet,
                    # then forward it to them.
                    name = interested.pop(-1)
                    if name != self.name: 
                        send_tcp(
                            message=make_data_packet(
                                content_name=f'{self.host}-{self.port}-{self.name}/{interest}',
                                data=packet['data']
                            ),
                            host = self.neighbors[name]['host'],
                            port = self.neighbors[name]['port']
                        )
                    # If this node itself was previously yourself
                    # interested in this kind of content, then,
                    # this node uses this packet for itself.
                    else: 
                        self.satisfy_interest(interest=interest, data_packet=packet)

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
            content_name = f'{self.host}-{self.port}-{self.name}/beacon/on'
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

    def start_decision_making(self):
        # Get marker value for each marker.
        for marker in CONFIG['markers']:
            # For own marker, already have value so update knowledge.
            marker_value = self.get_from_cs(f'marker/{marker}')
            if marker_value is None: # For other markers, send interest packet.
                interest = f'marker/{marker}'
                prefix = f'{self.host}-{self.port}-{self.name}'
                self.add_to_pit( # Add own interest to PIT.
                    content_name=interest,
                    incoming_face_name=self.name
                )
                # Forward interest packet.
                fwd_neighbor = self.get_fwd_neighbor(
                    content_name=interest, 
                    sender_name=self.name
                )
                send_tcp(
                    message=make_interest_packet(content_name=f'{prefix}/{interest}'),
                    host=self.neighbors[fwd_neighbor]['host'],
                    port=self.neighbors[fwd_neighbor]['port']
                )
                print(f'[{self.name}] Sent {interest} to {fwd_neighbor}.')
            else: self.knowledge[self.marker] = marker_value
                
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
                if self.knowledge[self.marker] == -1:
                    cancer_marker_value = int(input('Sensing cancer marker value:'))
                    self.set_cancer_marker(cancer_marker_value)
                self.neighbor_discovery()

    def handle_actuator_beacon(self):
        if 'actuator_beacon' in self.__actuators:
            if self.__actuators['tethers'] == 0:
                self.__actuators['beacon'] = 0
            else:
                self.__actuators['beacon'] = 1
                content_name = f'{self.host}-{self.port}-{self.name}/beacon/on'
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
        self.add_to_cs(f'marker/{self.marker}', self.__sensors['cancer_marker'])
        if self.marker == CONFIG['primary_marker']:
            if self.__sensors['cancer_marker'] == 1:
                self.handle_actuator_tether(1)
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
    print('No. of threads active =', threading.active_count())