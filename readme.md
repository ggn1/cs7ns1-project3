# Use Case: Teams of NanoBots in the body for Cancer detection.
Every action team comprises 5 nanobots, each to detect one of 5 markers in cells indicative of cancer:
- "tumour" marker = This is the most important (primary) marker and refers to chemical markers most closely associated with particular kinds of cancer (e.g. Prostate-specific antigen (PSA) associated with Prostrate Cancer).
- "acidity" marker = Cancerous cells are more acidic in nature than healthy cells, hence this marker.
- "growth" marker = This marker represents growth factors like Insulin-like Growth Factors (IGFs) and the Epidermal Growth Factor (EGF) that mark uncontrolled growing nature of cancerous tissue.
- "survivin" marker = This protein counteracts growth inhibitors in the body that allows cancer to keep growing.
- "ecmr" marker = Extracellular Matrix Remodeling Enzymes like metalloproteinases (MMPs) and lysyl oxidase (LOX) help reshape surroundings of the cancer cell and aid in immune suppression.

The nanobot that detects the tumour marker is the primary bot which triggers collective diagnosis, while all others are non-primary/secondary bots.

We had demonstrated functioning of 1 such team with 5 bots.

There is also a 6th node in the network called a rendezvous server whose presence may be viewed as perhaps a smart watch worn by the patient. This server was added to simulate NP bots detecting beacon signals emitted by a P bot. If this were in real life, NP bots would simply sense the beacon when it got within range of it. Thus, the rendezvous server here, merely serves to pick up beacon data packets from P bots (active beacon actuator) and relay them the interested NP bots (searching for beacon).

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