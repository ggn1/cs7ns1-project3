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
import random

config = {'bloodstream_length': 100}

nanobots = []

if __name__ == '__main__':
    pass