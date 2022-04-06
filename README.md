# Networking RDT project

This is a backup for the RDT project I did. Read Programming-Project.pdf for detailed description.

## Project Description
two reliable data transfer layers are implemented , one is based on the Stop-and-Wait (rdt3.0) protocol and the other is based on the extended Stop-and-Wait (rdt 4.0) protocol. Both RDT protocols support connectionless reliable duplex data transfer on top of unreliable UDP. You can view the communication system has three layers. They are the Application layer, Reliable data transfer layer, and Unreliable layer.

The Application layer invokes the service primitives provided by the RDT layer in order to send/receive messages to/from remote application processes. Upon receiving a message from the Application layer, the RDT layer encapsulates the application message with control header to form a packet and passes the packet to Unreliable layer by invoking the service primitives exported by the Unreliable layer. The Unreliable layer is responsible for sending the packets to the Unreliable layer of a remote peer process by means of UDP packets. To simulate transmission errors, the Unreliable layer may randomly discard or corrupt packets.

### Part 1
- Assume UDP is reliable
- Implement the reliable layer directly on top of UDP without adding extra functionality to UDP

### Part 2
- UDP is unreliable with packet losses and corruptions
- Implement the reliable layer using Stop and Wait (rdt3.0) ARQ on top of UDP

### Part 3
- UDP is unreliable with packet losses and corruptions
- Implement the reliable layer using Extended Stop and Wait (rdt4.0) on top of UDP to improve performance
