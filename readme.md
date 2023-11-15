# Idea

## Use Case: NanoBots in the body for Cancer detection.
Every action team comprises 5 nanobots

## Run Instructions

Open 6 terminals and run each command on a diff terminal

Terminal 1: (server) 

python3 rendezvous_server.py --host 127.0.0.1 --port 33000

Terminal 2: (Primary Node): 

python3 nanobot.py --host 127.0.0.1 --port 33001 --marker tumour --name primary

Terminal 3: (Nanobot node) : 

python3 nanobot.py --host 127.0.0.1 --port 33002 --marker acidity --name n1

Terminal 4,5 & 6:

python3 nanobot.py --host 127.0.0.1 --port 33003 --marker growth --name n2
python3 nanobot.py --host 127.0.0.1 --port 33004 --marker survivin --name n3
python3 nanobot.py --host 127.0.0.1 --port 33005 --marker ecmr --name n4


Once you ran these, now go to terminal 2 (primary node) give input as 1 

Again switch to T3, T4, T5, T6 and give 1 as an input or any failed test cases 

0,0,0,0 (fail)
1,0,0,0 (fail)
1,1,0,0 (fail)
1,1,1,0 (fail)
1,1,1,1 (pass)