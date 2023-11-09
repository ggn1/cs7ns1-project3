Peer discovery is the process of identifying and locating other peers or nodes in a network. It is a fundamental step in establishing communication and collaboration among networked devices. This allows devices to find and connect with other devices that are part of the same network or distributed system, enabling data sharing, communication, and cooperation.

## TCP/IP Implementation
Following are some ways in which each peer can keep track of who their going to talk to next.
1. Have a central database known as a **tracker** that orchestrates the entire network.
2. Use a **Gossip Protocol** where each peer maintains a local ***hash table*** which maps other peer addresses with identifiers of data chunks that they have. Such a hash table present in every node is also called **distributed hash table**.
## NDN Implementation