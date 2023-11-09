Peer to peer (P2P) networks have the following characteristics.
- All nodes/peers act as both clients and servers.
- Data is fragmented and distributed among all peers. That is, each peer has a small part of total data.
- Peers request missing data fragments from other peers in the network to complete a file and get the full picture.
- Communications happen simultaneously allowing for *parallelisation of data transfer*.
- Because there are multiple peers, after each transfer timestep, the rate of transfer will grow exponentially until all peers have at least one data fragment.
- For a P2P network to be successful, each peer needs to know which other peer it should be talking to next. This is called [[Peer Discovery]] or **peer selection**.