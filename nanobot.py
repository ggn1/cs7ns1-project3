# AUTHOR: Tarun Singh (23330140) [Contribution = Security = Logging, auth token, input validation, error handling.]
# AUTHOR: Tejas Bhatnagar (23334930) [Contribution = Testing, Debugging]
# AUTHOR: Gayathri Girish Nair (23340334) [Contribution = Everything else (ICN, NDN, Scenario set up.)]

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
import logging

# Create a 'logs' directory if it doesn't exist
logs_dir = 'logs'
os.makedirs(logs_dir, exist_ok=True)

# Set up logging to write logs to both console and a file
logging.basicConfig(level=logging.INFO)

# Create a file handler that writes log messages to a file
log_file_path = os.path.join(logs_dir, 'nanobot.log')
file_handler = logging.FileHandler(log_file_path)
file_handler.setLevel(logging.INFO)

# Create a logger and add the file handler
logger = logging.getLogger(__name__)
logger.addHandler(file_handler)

def setup_argparser():
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
        logging.error("Please specify host address.")
        exit(1)

    if args.marker is None:
        logging.error("Please specify marker.")
        exit(1)

    if args.name is None:
        logging.error("Please specify a name.")
        exit(1)
    
    if args.port is None:
        logging.error("Please specify port number.")
        exit(1)

    return args

CONFIG = {}
with open('config.json', 'r') as f: CONFIG = json.load(f)

class Bot:
    def __init__(self, host, port, marker, name, sensor_value=None):
        self.name = name
        self.host = host
        self.port = port
        self.sensor_value = sensor_value
        self.position = random.randint( # position in blood stream.
            0, CONFIG['blood_stream_length']-1
        )
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM) # IP, TCP
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind((host, port)) # Setting up ears.
        self.marker = marker # The kind of tumour marker this bot detects.
        self.knowledge = {m:-1 for m in CONFIG['markers']}
        self.neighbor_discovery_complete = False
        if self.marker != CONFIG['primary_marker']: self.primary_node = None
        self.diagnosis = None
        self.__sensors = { # sensors
            'cancer_marker': 0, # 1 => detected
            'beacon': -1 # position of beacon detected
        }
        self.__actuators = { # actuators
            'tethers': 0, # 1 => extended
            'head_rotator': 0.25, # acceleration (+ve = forward, -ve = backward)
            'propeller_rotator': 0.25, # acceleration (+ve = forward, -ve = backward)
            'self_destruct': 0, # 1 => detonated
            'cargo_hatch': 0, # 1 => open
            'diffuser': 0, # 1 => diffused
        }
        self.last_conn = None
        if self.marker == CONFIG['primary_marker']: # special variables that only primary node has
            self.__actuators['beacon'] = 0 # 1 => active.
            self.ready_to_decide = 0
        self.neighbors = {}

        # NDN
        self.content_store = {f'marker/{self.marker}': self.sense_cancer_marker()}
        self.pending_interests_table = {}
        self.forwarding_information_base = {}

        self.set_sensors('beacon', -1)
        self.set_sensors('cancer_marker', 0)

        # THREADS
        # Listens for connection to self server.
        thread_listen_conn = threading.Thread(target=self.listen_conn, args=())
        thread_listen_conn.start()
        # Listens for events.
        thread_listen_event = threading.Thread(target=self.listen_event, args=())
        thread_listen_event.start()
    
    def __print_tables(self):
        logging.debug(f'[{self.name}]')
        logging.debug(f'\tNeighbors = {self.neighbors}.')
        logging.debug(f'\tCS = {self.content_store}.')
        logging.debug(f'\tPIT = {self.pending_interests_table}.')
        logging.debug(f'\tFIB = {self.forwarding_information_base}.')
    
    def __print(self, to_print):
        logging.info(f'[{self.name}] {to_print}')

    def sense_cancer_marker(self):
        ''' Returns latest value in sensor. '''
        return self.__sensors['cancer_marker']
    
    def add_to_pit(self, content_name, incoming_face_name):
        try:
            if not content_name in self.pending_interests_table:
                self.pending_interests_table[content_name] = []
            if incoming_face_name not in self.pending_interests_table[content_name]:
                self.pending_interests_table[content_name].append(incoming_face_name)
        except Exception as e:
            logger.error(f"Error adding to PIT: {str(e)}")

    def get_from_pit(self, content_name):
        try:
            if content_name in self.pending_interests_table:
                return self.pending_interests_table[content_name]
            else:
                return []
        except Exception as e:
            logger.error(f"Error getting from PIT: {str(e)}")
            return []
    
    def add_to_fib(self, content_name, outgoing_face_name, replace):
        try:
            if not content_name in self.forwarding_information_base:
                self.forwarding_information_base[content_name] = {}
            if outgoing_face_name in self.forwarding_information_base[content_name] and not replace:
                self.forwarding_information_base[content_name][outgoing_face_name] += 1
            else:
                self.forwarding_information_base[content_name][outgoing_face_name] = 0
            # Log information about adding to FIB
            logger.debug(f"Added {outgoing_face_name}:{self.forwarding_information_base[content_name][outgoing_face_name]} to FIB.")
        except Exception as e:
            logger.error(f"Error adding to FIB: {str(e)}")    

    def get_from_fib(self, content_name, get_cost=False):
        try:
            if content_name in self.forwarding_information_base:
                routes = self.forwarding_information_base[content_name] # {neighbor1:cost, neighbor2:cost, ...}
                least_costly = None
                for neighbor, cost in routes.items():
                    if not least_costly: least_costly = (neighbor, cost)
                    elif cost < least_costly[1]: least_costly = (neighbor, cost)
                return least_costly[0] if not get_cost else least_costly
            else:
                return None
        except Exception as e:
            logger.error(f"Error in get_from_fib method: {str(e)}")    
    
    def get_random_viable_neighbor(self, sender_name):
        try:
            neighbors = list(self.neighbors.keys())
            # Pick neighbors randomly until coming across one 
            # that is not the same as the sender, return this one.
            while True: 
                n = neighbors[random.randint(0, len(neighbors)-1)]
                if n != sender_name: 
                    return n
        except Exception as e:
            logger.error(f"Error in get_random_viable_neighbor method: {str(e)}")

    def get_fwd_neighbor(self, content_name, sender_name):
        try:
            # Attempt to get cheapest route for given content from FIB.
            fwd_neighbour = self.get_from_fib(content_name, get_cost=True) # [name, cost] / None 

            # If known route does not exist,
            # pick a random neighbor that is not the sender
            # and add it to FIB.
            if fwd_neighbour is None: 
                fwd_neighbour = self.get_random_viable_neighbor(sender_name)
                self.add_to_fib(content_name, fwd_neighbour, replace=False)

            # If a known route exists, check if it points towards sender itself. 
            else: 
                # If best route not same as sender 
                # check the cost of the route.
                if fwd_neighbour[0] != sender_name:
                    # If cost > 0, then there may be a better path. Explore
                    # other viable neighbor options.
                    if fwd_neighbour[1] > 0: 
                        # If there are as many existing routes for this content 
                        # as neighbors then this means no unexplored neighbors
                        # exist. Hence, current route, despite costing
                        # more than 0, remains to be the best option.
                        # If there are fewer routes than the number of neighbors,
                        # explore other neighbors.
                        all_routes = self.forwarding_information_base[content_name]
                        # all_routes = {neighbour: cost, ...}
                        if len(all_routes) < len(self.neighbors): # explore other neighbors
                            viable_n = None
                            # loop through all neighbors and find one that's 
                            # not been explored yet (not in the FIB yet).
                            for n in self.neighbors.keys(): 
                                if n not in all_routes and n != sender_name:
                                    viable_n = n
                                    break
                            if viable_n is None: # no viable neighbor found
                                fwd_neighbour = fwd_neighbour[0]
                            else: # viable neighbor found
                                fwd_neighbour = viable_n
                        else: 
                            fwd_neighbour = fwd_neighbour[0]
                    else: # If cost is 0, then this is the best option.
                        fwd_neighbour = fwd_neighbour[0]
                # If the best route is the same as the sender,
                # find another route.
                else: 
                    # Check to see if there is another known viable route.
                    all_routes = self.forwarding_information_base[content_name]
                    # all_routes = {neighbour: cost, ...}
                    viable_options = [n for n in all_routes.keys() if n != sender_name]
                    if len(viable_options) > 0:
                        fwd_neighbour = viable_options[
                            random.randint(0, len(viable_options)-1)
                        ]
                    # Else pick a random neighbor from the list of all neighbors to send to.
                    # Add this neighbor to FIB if not already present.
                    fwd_neighbour = self.get_random_viable_neighbor(sender_name)
                    if fwd_neighbour not in all_routes:
                        self.add_to_fib(content_name, fwd_neighbour, replace=False)

            # Note: "Viable" neighbor here means a node that is not the sender.
            return fwd_neighbour
        except Exception as e:
            logger.error(f"Error in get_fwd_neighbor method: {str(e)}")        

    def add_to_cs(self, content_name, data):
        try:
            self.content_store[content_name] = data
        except Exception as e:
            logger.error(f"Error adding data to content store: {str(e)}") 

    def get_from_cs(self, content_name):
        try:
            if content_name in self.content_store:
                return self.content_store[content_name]
            else:
                return None
        except Exception as e:
            logger.error(f"Error getting data from content store: {str(e)}")
            return None           

    def initiate_attack_sequence(self):
        try:
            ''' Attack protocol that each bot executes
                to destroy cancer cells. '''
            self.set_actuator('cargo_hatch', 1)
            logging.warning(f'[{self.name}]: Preparing to self-destruct.')
            self.set_actuator('self_destruct', 1)
        except Exception as e:
            logger.error(f"Error in initiate_attack_sequence method: {str(e)}")
    
    def initiate_state_reset(self):
        try:
            ''' Protocol that bots execute to untether and 
                continue operation. '''
            # Reset all state variables.
            self.last_conn = None
            self.knowledge = {m: -1 for m in CONFIG['markers']}
            self.neighbors = {}
            self.content_store = {f'marker/{self.marker}': self.sense_cancer_marker()}
            self.pending_interests_table = {}
            self.forwarding_information_base = {}
            self.set_actuator('tethers', 0)
            self.neighbor_discovery_complete = False
            if self.marker == CONFIG['primary_marker']:
                if self.__actuators['beacon'] != 0:
                    self.set_actuator('beacon', 0)
                self.ready_to_decide = 0
            else:
                self.primary_node = None
            self.set_sensors('beacon', -1)
            self.set_sensors('cancer_marker', 0)
            self.diagnosis = None
            self.__print('State reset.')

        except Exception as e:
            logger.error(f"Error in initiate_state_reset method: {str(e)}")
    
    def satisfy_interest(self, interest, data_packet):
        try:
            ''' Handles desired data packet. '''
            data = data_packet['data']

            # Decision making.
            # If a peer cancer marker data is available, then
            # update own knowledge and see if a decision can be made.
            if 'marker' in interest:
                # data = {'marker_type': <marker type>, 'marker_value': <marker value>}
                self.knowledge[data['marker_type']] = data['marker_value']
                marker_values = list(self.knowledge.values())
                # If all marker values are known, make a diagnosis.
                if marker_values.count(-1) == 0:
                    decision = 'healthy'
                    if sum(marker_values) == len(CONFIG['markers']):
                        decision = 'cancer'
                    self.diagnosis = decision

        except Exception as e:
            logger.error(f"Error in satisfy_interest method: {str(e)}")

    def handle_interest_packet(self, packet):
        try:
            content_name = packet['content_name'].split('/')
            sender_host, sender_port, sender_name, sender_marker = content_name[0].split('-')
            sender_port = int(sender_port)
            interest = content_name[1:len(content_name)-1]
            timestamp = content_name[-1]
            logging.debug(f"Node {self.name} received interest packet for interest {interest}")

            # Neighbor discovery.
            if 'neighbor' in interest:  # Only a primary node ever receives this.
                # interest = neighbor/<desired-marker>
                desired_marker = interest[1]  # marker for which sender requires a neighbor
                # add sender to list of neighbors
                self.neighbors[sender_name] = {
                    'host': sender_host,
                    'port': sender_port,
                    'marker': sender_marker
                }
                # add a route in FIB that links sender's marker to sender
                self.add_to_fib(content_name=f'marker/{sender_marker}', outgoing_face_name=sender_name, replace=True)
                # add sender's interest for neighbor of desired marker type to PIT
                self.add_to_pit(content_name=f'neighbor/{desired_marker}', incoming_face_name=sender_name)

                # If this node's (primary node) neighbor discovery is complete,
                # then service all interested parties in PID with desired routes from FIB.
                if len(self.neighbors) == (len(CONFIG['markers']) - 1):
                    self.__print('Servicing all neighbor interest packets.')
                    interests_serviced = []
                    for interest, interested_parties in self.pending_interests_table.items():
                        requested_marker = interest.split('/')[1]
                        requested_marker_src_name = self.get_from_fib(content_name=f'marker/{requested_marker}')
                        if 'neighbor' in interest:  # interest = neighbor/<requested-marker>
                            for name in interested_parties:  # interested_parties = [<name> ...]
                                send_tcp(
                                    message=make_data_packet(
                                        content_name=f'{self.host}-{self.port}-{self.name}-{self.marker}/neighbor/{requested_marker}',
                                        data={
                                            'name': requested_marker_src_name,
                                            'host': self.neighbors[requested_marker_src_name]['host'],
                                            'port': self.neighbors[requested_marker_src_name]['port'],
                                        }
                                    ),
                                    host=self.neighbors[name]['host'],
                                    port=self.neighbors[name]['port']
                                )
                            interests_serviced.append(interest)
                    # Since all above interests were serviced, they may be popped from PIT.
                    for interest in interests_serviced:
                        self.pending_interests_table.pop(interest)

                    if not(self.neighbor_discovery_complete):
                        self.neighbor_discovery_complete = True
                        self.__print('Neighbor discovery complete.')
                        self.set_actuator('beacon', 0)
                        self.__print('Beacon turned off.')
                        # self.__print_tables()

            # When a primary node receives diagnose interest from all non-primary
            # nodes and this primary node's neighbor discovery is complete, this
            # means neighbor discovery of the entire network is complete. It also then
            # sends a diagnose interest to all non-primary nodes.
            elif 'diagnose' in interest:
                # Primary bot can start decision making upon receiving 4 diagnose requests.
                if self.marker == CONFIG['primary_marker']:  # Primary node.
                    self.ready_to_decide += 1
                    if (
                        self.neighbor_discovery_complete
                        and self.ready_to_decide == (len(CONFIG['markers']) - 1)
                    ):
                        for host_port in self.neighbors.values():
                            send_tcp(
                                message=make_interest_packet(f'{self.host}-{self.port}-{self.name}-{self.marker}/diagnose'),
                                host=host_port['host'],
                                port=host_port['port']
                            )
                        self.__print('Ready to diagnose.')
                        self.__print('Starting diagnosis ...')
                        self.start_diagnosis()
                # Non-primary bots can start decision making upon receiving 1 diagnose request
                # from the primary bot that they know of.
                else:  # Non-primary node.
                    if sender_name == self.primary_node:
                        self.__print('Starting diagnosis ...')
                        self.start_diagnosis()

            # NDN Forwarding
            else:
                interest = '/'.join(interest)

                # 1. Add interest to PIT.
                self.add_to_pit(content_name=interest, incoming_face_name=sender_name)

                # 2. Attempt to get requested content from CS.
                cs_value = self.get_from_cs(content_name=interest)

                # 3. If this peer does not have the content,
                # pick a suitable neighbor to forward this packet to.
                if cs_value is None:
                    # To avoid taking longer paths, first update (+1)
                    # cost of last used route for this content if any.
                    # If there is a last used route X then it means that
                    # this packet has come back to this node as a result
                    # of having taken X. So, this cost update will encourage
                    # picking another possibly better route this time.
                    last_used_route = self.get_from_fib(interest)
                    if last_used_route: self.add_to_fib(interest, last_used_route, replace=False)

                    # pick good neighbor
                    fwd_neighbor = self.get_fwd_neighbor(
                        content_name=interest,
                        sender_name=sender_name
                    )

                    # forward packet
                    send_tcp(
                        message=make_interest_packet(content_name=f'{self.host}-{self.port}-{self.name}-{self.marker}/{interest}'),
                        host=self.neighbors[fwd_neighbor]['host'],
                        port=self.neighbors[fwd_neighbor]['port']
                    )

                # 4. If this peer has requested content in its CS,
                # then for every interested party in PIT
                # send this to them in a data packet.
                else:
                    # a data packet to all interested parties.
                    interested = self.get_from_pit(content_name=interest)  # ['neighbor', ...] / []
                    while len(interested) > 0:
                        fwd_name = interested.pop(-1)
                        send_tcp(
                            message=make_data_packet(
                                content_name=f'{self.host}-{self.port}-{self.name}-{self.marker}/{interest}',
                                data={'marker_type': self.marker, 'marker_value': cs_value}
                            ),
                            host=self.neighbors[fwd_name]['host'],
                            port=self.neighbors[fwd_name]['port']
                        )
                    # Pop this interest from the table since by now,
                    # all corresponding interested parties have been served.
                    self.pending_interests_table.pop(interest)

        except Exception as e:
            logger.error(f"Error in handle_interest_packet method: {str(e)}")

    def handle_data_packet(self, packet):
        try:
            content_name = packet['content_name'].split('/')
            sender_host, sender_port, sender_name, sender_marker = content_name[0].split('-')
            sender_port = int(sender_port)
            interest = content_name[1:len(content_name)-1]
            timestamp = content_name[-1]
            logging.debug(f"Node {self.name} received data packet for interest {interest}")

            # Data packet is of type beacon.
            if 'beacon' in interest:
                data = packet['data']
                self.set_sensors('beacon', data['position'])
                self.primary_node = data['name']
                self.neighbors[data['name']] = {
                    'host': data['host'],
                    'port': data['port']
                }
                self.add_to_fib(
                    content_name=f'marker/{CONFIG["primary_marker"]}',
                    outgoing_face_name=data['name'],
                    replace=True
                )
                self.add_to_cs(  # Add primary bot's marker value as 1 to CS.
                    content_name=f'marker/{CONFIG["primary_marker"]}',
                    data=1
                )
                self.move(position=data['position'])

            # Neighbor discovery (received by non-primary nodes only).
            elif 'neighbor' in interest:
                # interest = neighbor/<requested-marker>
                data = packet['data']  # {'name':str, 'host':str, 'port':int}
                desired_marker = interest[1]

                # Add discovered node to neighbor list.
                self.neighbors[data['name']] = {
                    'host': data['host'],
                    'port': data['port'],
                    'marker': desired_marker
                }

                # Add route to FIB.
                self.add_to_fib(content_name=f'marker/{desired_marker}', outgoing_face_name=data['name'], replace=True)

                # Check if neighbor discovery is complete.
                if (
                    len(self.neighbors) == len(CONFIG['markers']) - 1
                    and not self.neighbor_discovery_complete
                ):
                    self.neighbor_discovery_complete = True
                    self.__print('Neighbor discovery complete.')
                    # self.__print_tables()
                    # Send interest to start decision making to primary bot.
                    # Start only when the primary bot confirms the decision.
                    send_tcp(
                        message=make_interest_packet(f'{self.host}-{self.port}-{self.name}-{self.marker}/diagnose'),
                        host=self.neighbors[self.primary_node]['host'],
                        port=self.neighbors[self.primary_node]['port']
                    )
                    self.__print('Ready to diagnose.')

            # NDN Forwarding
            else:
                interest = '/'.join(interest)

                # 1. Cache it in content store.
                self.add_to_cs(interest, packet['data'])

                # 2. Check PIT table.
                interested = self.get_from_pit(interest)  # [name, ...]

                # Serve every party in PIT interested in received content
                # (if no interested parties, the packet is dropped).
                while len(interested) > 0:
                    interested_party = interested.pop(-1)  # interested party name

                    # If the interested party is this node itself,
                    # use the data for personal purposes.
                    if interested_party == self.name:
                        self.satisfy_interest(interest=interest, data_packet=packet)

                    # Else if this interested party is another peer
                    # that had previously requested this content.
                    # Forward it to them.
                    else:
                        send_tcp(
                            message=make_data_packet(
                                content_name=f'{self.host}-{self.port}-{self.name}-{self.marker}/{interest}',
                                data=packet['data']
                            ),
                            host=self.neighbors[interested_party]['host'],
                            port=self.neighbors[interested_party]['port']
                        )

                # Pop this interest from the table since by now,
                # all corresponding interested parties have been served.
                self.pending_interests_table.pop(interest)

        except Exception as e:
            logger.error(f"Error in handle_data_packet method: {str(e)}")

    def handle_incoming(self, conn):
        try:
            message = conn.recv(2048).decode('utf-8')
            packet = json.loads(message)
            if packet['type'] == 'data':
                self.handle_data_packet(packet)
            else:  # packet['type'] == 'interest'
                self.handle_interest_packet(packet)
        except Exception as e:
            logger.error(f"Error handling incoming connection: {str(e)}")
        finally:
            conn.close()
    
    def listen_conn(self):
        try:
            self.socket.listen()
            logger.info(f'[{self.name}] Listening on {self.host} port {self.port} ...')
            while True:
                socket_connection, address = self.socket.accept()
                self.last_conn = time.time()
                self.handle_incoming(socket_connection)
        except Exception as e:
            logger.error(f"Error in connection listener: {str(e)}")

    def listen_event(self):
        try:
            # If beacon sensor of a non-primary bot 
            # does not contain a position value indicating
            # that this bot has picked up a beacon,
            # search for a beacon.
            
            searching = False
            search_trials = 0
            search_start_time = None
            while True:
                # BEACON
                if (
                    self.marker != CONFIG['primary_marker'] 
                    and self.__sensors['beacon'] < 0
                ): 
                    cur_time = time.time()
                    if (
                        not search_start_time is None
                        and ((cur_time - search_start_time) >= CONFIG['timeout']['beacon_search'])
                    ):
                        searching = False
                        if search_trials > CONFIG['trials']['beacon_search']:
                            self.set_actuator('diffuser', 1)
                    # If we were not searching, start since we don't know where the primary bot is.
                    if searching == False:
                        searching = True
                        search_start_time = time.time()
                        search_trials += 1
                        print(f'[{self.name}] Searching for beacon ...')
                        send_tcp(
                            message=make_interest_packet(content_name=f'{self.host}-{self.port}-{self.name}-{self.marker}/beacon/on'), 
                            host=CONFIG['rendezvous_server'][0],
                            port=CONFIG['rendezvous_server'][1]
                        )
                else:
                    if searching == True:  # If we were searching, stop since found beacon.
                        searching = False
                        search_start_time = None
                        search_trials = 0

                # DIAGNOSIS
                # Be ready to take action as soon as a decision is available.
                if self.diagnosis:
                    time.sleep(3)
                    self.__print(f'Diagnosis = {self.diagnosis}.')
                    if self.diagnosis == 'cancer':
                        self.initiate_attack_sequence()
                    else:  # decision == 'healthy'
                        self.initiate_state_reset()
                
                # STALE CONNECTION
                if self.marker == CONFIG['primary_marker']:
                    if self.__actuators['tethers']:
                        cur_time = time.time()
                        if self.last_conn is None:
                            self.last_conn = cur_time
                        elif cur_time - self.last_conn > CONFIG['timeout']['last_conn']:
                            self.__print('Stale connection')
                            self.initiate_state_reset()
                else:
                    if self.__sensors['beacon'] > 0:
                        cur_time = time.time()
                        if self.last_conn is None:
                            self.last_conn = cur_time
                        elif cur_time - self.last_conn > CONFIG['timeout']['last_conn']:
                            self.__print('Stale connection')
                            self.initiate_state_reset()

        except Exception as e:
            logger.error(f"Error in event listener: {str(e)}")
    
    def move(self, position):
        try:
            # Bot has moved to some new location by the time this function is called.
            self.position = random.randint(0, CONFIG['blood_stream_length'] - 1)
            while self.position != position:  # Moving to cancer location.
                new_position = self.position + int(
                    CONFIG['blood_speed']
                    + self.__actuators['head_rotator']
                    + self.__actuators['propeller_rotator']
                )
                if new_position >= CONFIG['blood_stream_length']:
                    new_position = 0
                self.position = new_position
            if (
                self.marker != CONFIG['primary_marker']
                and self.__sensors['beacon'] == self.position
                and self.__actuators['tethers'] != 1
            ):
                self.set_actuator('tethers', 1)
        except Exception as e:
            logger.error(f"Error in move method: {str(e)}")

    def start_diagnosis(self):
        try:
            # Get marker value for each possible marker.
            for possible_marker in CONFIG['markers']:
                # For own marker, already have value so update knowledge.
                marker_value = self.get_from_cs(f'marker/{possible_marker}')
                # For marker whose values are yet to be in content base,
                # 1. create an interest
                # 2. add self interest to PIT
                # 3. get a suitable neighbor to forward to
                # 4. forward interest
                # send interest packet to best possible neighbor.
                if marker_value is None:
                    interest = f'marker/{possible_marker}'  # 1. express interest
                    self.add_to_pit(  # add to PIT
                        content_name=interest,
                        incoming_face_name=self.name
                    )
                    fwd_neighbor = self.get_fwd_neighbor(  # 2. get best neighbor to send to
                        content_name=interest,
                        sender_name=self.name
                    )
                    send_tcp(  # 3. send interest packet to chosen neighbor
                        message=make_interest_packet(content_name=f'{self.host}-{self.port}-{self.name}-{self.marker}/{interest}'),
                        host=self.neighbors[fwd_neighbor]['host'],
                        port=self.neighbors[fwd_neighbor]['port']
                    )
                    # print(f'[{self.name}] Sent {interest} to {fwd_neighbor}.')
                # For markers whose values are available,
                # update own knowledge with these values.
                else:
                    self.knowledge[possible_marker] = marker_value
                    
        except Exception as e:
            logger.error(f"Error in start_diagnosis method: {str(e)}")
   
    def start_neighbour_discovery(self):
        try:
            ''' This function is called by a non-primary node
                once it tethers to trigger neighbor discovery.
            '''
            # For all possible markers, if it's not own marker
            # or a marker already having forwarding information
            # in the FIB, send an interest packet to the primary node
            # for information about the node with this marker.
            for possible_marker in CONFIG['markers']:
                if (
                    f'marker/{possible_marker}' not in self.forwarding_information_base
                    and possible_marker != self.marker
                ):
                    send_tcp(
                        message=make_interest_packet(
                            content_name=f'{self.host}-{self.port}-{self.name}-{self.marker}/neighbor/{possible_marker}'
                        ),
                        host=self.neighbors[self.primary_node]['host'],
                        port=self.neighbors[self.primary_node]['port']
                    )

        except Exception as e:
            logger.error(f"Error in start_neighbour_discovery method: {str(e)}")
    
    def set_actuator(self, actuator, value):
        try:    
            ''' Sets value of actuators. '''
            if actuator == 'tethers':
                self.__actuators[actuator] = value
                if value == 1:
                    # Turn off rotators to slow down and
                    # extend tethers to fix itself to potentially cancerous tissue.
                    self.__actuators['head_rotator'] = 0
                    self.__actuators['propeller_rotator'] = 0
                    self.__actuators['tethers'] = 1
                    print(f'[{self.name}] Tethered to {self.position}.')
                    
                    # Non primary nodes take sensor reading and 
                    # initiate neighbor discovery.
                    if self.marker != CONFIG['primary_marker']:
                        if self.knowledge[self.marker] == -1: # Take cancer marker sensor reading.
                            if self.sensor_value is None:
                                cancer_marker_value = int(input(f'[{self.name}] Sensing cancer marker value: '))
                            else:
                                cancer_marker_value = int(self.sensor_value)
                                print(f'[{self.name}] Sensing cancer marker value: {self.sensor_value}')
                            self.set_sensors('cancer_marker', cancer_marker_value if cancer_marker_value == 1 else 0)
                        self.start_neighbour_discovery()
                else: # value == 0
                    # Tethers retract and rotators apply positive
                    # acceleration. Bot moves with blood flow.
                    self.__actuators['tethers'] = 0
                    self.__actuators['head_rotator'] = 0.25
                    self.__actuators['propeller_rotator'] = 0.25
            
            elif actuator == 'beacon':
                if 'beacon' in self.__actuators: # Only for primary bot.
                    # Activate beacon (send a data packet to Rendezvous server
                    # marking position of primary bot that has detected the 
                    # primary cancer marker.)
                    if value == 1:
                        self.__actuators['beacon'] = value
                        send_tcp(
                            message=make_data_packet(
                                content_name=f'{self.host}-{self.port}-{self.name}-{self.marker}/beacon/on',
                                data={'position': self.position}
                            ),
                            host=CONFIG['rendezvous_server'][0],
                            port=CONFIG['rendezvous_server'][1]
                        )
                    
                    # Turn the beacon off if it was previously on.
                    # (Send an interest packet to Rendezvous server
                    # marking turn off of beacon by this particular node.)
                    else: # value == 0
                        if self.__actuators['beacon'] == 1:
                            self.__actuators['beacon'] = value
                            send_tcp(
                                message=make_interest_packet(
                                    content_name=f'{self.host}-{self.port}-{self.name}-{self.marker}/beacon/off'
                                ), 
                                host=CONFIG['rendezvous_server'][0],
                                port=CONFIG['rendezvous_server'][1]
                            )

            elif actuator == 'cargo_hatch':
                self.__actuators[actuator] = value
                if value == 1: 
                    self.__print('Hatch open. Thrombin deployed.')
                else:
                    self.__print('Hatch closed.')
            
            elif actuator == 'self_destruct':
                self.__actuators[actuator] = value
                if value == 1:
                    self.__print(f'Detonated at position {self.position}.')
                    os.kill(os.getpid(), signal.SIGTERM)
            
            elif actuator == 'diffuser':
                self.__actuators[actuator] = value
                if value == 1:
                    self.__print('Diffused. Goodbye.')
                    os.kill(os.getpid(), signal.SIGTERM)

            else: self.__actuators[actuator] = value
        
        except Exception as e:
            logger.error(f"Error in set_actuator method: {str(e)}")

    def set_sensors(self, sensor, value):
        try:
            ''' Sets values for each sensor and initiates
                appropriate behavior. '''
            
            if sensor == 'cancer_marker':
                self.__sensors['cancer_marker'] = value

                # If a primary marker's cancer sensor is not set
                # simulate environment search for cancer marker.
                if value == 0 and self.marker == CONFIG['primary_marker']:
                    cancer_marker_value = 0
                    trials = 0
                    while cancer_marker_value == 0:
                        if trials >= CONFIG['trials']['tumour_search']:
                            self.set_actuator('diffuser', 1)
                        if self.sensor_value is None:
                            cancer_marker_value = int(input(f'[{self.name}] Sensing primary cancer marker value: '))
                        else:
                            cancer_marker_value = int(self.sensor_value)
                            print(f'[{self.name}] Sensing primary cancer marker value: {self.sensor_value}')
                        trials += 1
                    self.move(position=random.randint(0, CONFIG['blood_stream_length']-1))
                    self.set_sensors('cancer_marker', cancer_marker_value if cancer_marker_value == 1 else 0)

                # Update the value in content store with latest
                # marker value detected.
                self.add_to_cs(f'marker/{self.marker}', self.__sensors['cancer_marker'])

                # If a primary bot has detected a positive value for
                # its cancer marker, then tether to the current spot.
                if self.marker == CONFIG['primary_marker']:
                    if self.__sensors['cancer_marker'] == 1:
                        if self.__actuators['tethers'] != 1:
                            self.set_actuator('tethers', 1)
                        if self.__actuators['beacon'] != 1:
                            self.set_actuator('beacon', 1)
                    else: 
                        if self.__actuators['tethers'] != 0:
                            self.set_actuator('tethers', 0)
                        if self.__actuators['beacon'] != 0:
                            self.set_actuator('beacon', 0)
            else: 
                self.__sensors[sensor] = value
                
        except Exception as e:
            logger.error(f"Error in set_sensors method: {str(e)}")   

if __name__ == '__main__':
    try:
        args = setup_argparser()
        bot = Bot(host=args.host, port=args.port, marker=args.marker, name=args.name)
    except Exception as e:
        logger.error(f"Error in main block: {str(e)}")