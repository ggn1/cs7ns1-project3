# Nanobot nodes are injected at random 
# positions (indices) within this circular
# array to mimic how not all such bots
# would enter the body in the same blood
# vessel in a real-world injection scenario.
# Nanobots by default, move forwards at the
# same speed as the blood flows (here, 1) in 
# the same direction as the flow of blood.
# If the bot accelerates in the forward direction, 
# it moves at a speed 1 + x. If it accelerates in 
# the reverse direction, it moves at speed 1 - x.

# Imports.
import json
import random
from nanobot import Node

CONFIG = {}
with open('config.json', 'r') as f: CONFIG = json.load(f)

PORTS = {}
with open('ports.json', 'r') as f: PORTS = json.load(f)

bots = {} # Bot name to bot object mapping.
tumour = 50 # Tumour to position mapping.

def get_port():
    port = PORTS['available'].pop(0)
    PORTS['taken'].append(port)
    with open('ports.json', 'w') as f:
        json.dump(PORTS, f)
    return port

def make_bot_team():
    ''' Creates a team of 5 bots and adds them to the blood stream. '''
    for marker in CONFIG['markers']:
        bot_name = f'bot{len(bots)}'
        bots[bot_name] = Node(
            host='127.0.0.1', 
            port=get_port(),
            marker=marker,
            name=bot_name
        )

if __name__ == '__main__':
    for i in range(1):
        make_bot_team()
    while True:
        