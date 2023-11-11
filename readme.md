# Idea

## Use Case: NanoBots in the body for Cancer detection.
Every action team comprises 5 nanobots

TO DO ...

## Flow
1. The bot with the beacon actuator (this is the bot with the most important marker sensor) detects a positive sensor value of 1. It extends its tethers and anchors itself to the suspected cancer site. It starts the beacon.

2. Of the other 4 bots, two others eventually arrive at the beacon site. Their beacon sensor picks up 1. They also tether at the site. Being able to detect the beacon is considered suitable range for peer to peer communication. These 3 bots (A, B, C) are now ready to communicate.

3. All 3 bots require information about the 4 other sensor values that they don't themselves collect to collectively decide whether or not this really is cancer. It is considered cancer only if 4/5 markers are 1.

4. To get each other's port addresses, all bots send an interest packet to a rendezvous server that exists only to facilitate this peer to pere connection and will not serve any other purpose later. Such a rendezvous server is often used to set up peer to peer initially (for IP addresses and ports) when using IP protocol. The rendezvous server sends back all ports known to be in use.

5. Each bot sends an interest packet on all other 4 ports (not own) for 1 marker type each. This shall use UDP. For all markers for which no response is received, another request is sent to a different port after some time.

6. B received an interest packet from A. B checks CS. No entry found. So, it populates PIT and FIB and forwards this interest packet to one of the other ports that it knows about which is not itself or the sender. Say, here, it sent it to C.

7. C receives interest packet from B that's originally from A. C checks CS and data is found. C sends data packet to B. B removes from PIT and adds to FIB and CS. B sends to A.

8. 1st one to get 4 1s sends an interest to detonate to all known peers from FIB (TCP). If it also gets at leasts 3 other detonate interests, is not receiving any sensor interest, then wait 5 seconds, release blood clot inducer, and detonate.

9. Bots that go too long without either detecting or initiating a beacon event, will diffuse itself that makes it possible for it to get eliminated from the body.

CHANGES
=======
1. Only one bot out of each team of 5 will have a beacon actuator. But more than one team can be deployed in the body (here, 2 teams, one on each Pi.).
2. All bots have a new diffuser actuator.