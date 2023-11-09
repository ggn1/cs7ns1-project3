Information Centric Networking (ICN) seeks to move away from traditional TCP/IP network design architecture where location is king to a different style where data rules.

Here, there are no separate senders or receivers, only **requesters**.

## Objectives
1. Improve content location.
2. Deliver efficiency (in-network caching).
3. Improve content availability (redundancy).
4. Ensure data authenticity.

## Design Goals
1. Access content regardless of location.
2. Use names to address content.
	- Name based content identification.
	* Name based routing.
2. Security applied to content itself directly.
3. Data is independent of the following.
	- Location.
	- Application.
	- Transportation.
## Rethinking TCP/IP
|TCP/IP|ICN|
|---|---|
|Send/receive.|Publish/subscribe.|
|Sender driven.|Receiver driven.|
|Connect to host.|Request data object.|
|Establish secure tunnel.|Secure content.|
|Unicast.|Multicast.|
