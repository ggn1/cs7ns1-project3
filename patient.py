# Nanobot nodes are injected at random 
# positions (indices) within this circular
# array to mimic how not all such bots
# would enter the body in the same blood
# vessel in a real-world injection scenario.
# Nanobots by default, move forwars at the
# same speed as the blood flows (here, 1) in 
# the same direction as the flow of blood.
# If the bot accellerates in the forward direction, 
# it moves at a speed 1 + x. If it accellerates in 
# the reverse direction, it moves at speed 1 - x.

class BloodStream:
    def __init__(self, length=1000):
        self.stream_length = length
        self.bots = {}
        self.tumors = {}
    
    def inject_nanobot(self, bot, bot_id):
        self.bots[bot_id] = [bot, random.randint(0, self.stream_length)]
    
    def circulate(self):
        for bot_id, [bot, bot_pos] in self.bots.items():
            print(bot_id)

if __name__ == '__main__':
    pass

