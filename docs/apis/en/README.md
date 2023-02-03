## System Interface design

>Notes: This document primarily focuses on system interface design and provides descriptions and instructions for using these interfaces.
>It is intended for remote operation service developers who utilize Docker + K8S + KubeEdge to develop components.

### 1. System architecture

The objective of the mobile robot teleoperation service is to enable users to communicate and operate real-time audio and video with a remote robot via a web interface. For more information on solution selection and design, please refer to the [Mobile Robot Teleoperation Service Design](../proposal.md).

#### 1.1 System architecture diagram

This system architecture diagram primarily includes the following parts:

- **Teleop Client**: The client can be any terminal that supports the WebRTC protocol, such as a browser or mobile device. The client is developed using Vue3+Vite in this solution. It communicates with the signaling server through the WebSocket protocol for signaling exchange and uses the UDP protocol to transmit audio and video streams with the WebRTC service gateway.

- **Signaling Server**: The signaling server processes signaling information, including session establishment, media negotiation, and control commands, between clients. It uses the SDP (Session Description Protocol) and ICE (Interactive Connectivity Establishment) protocols to establish audio and video connections.

- **Teleop Server**: The teleop server handles business authentication, robot list, session management, and component creation.

- **Teleop Robot**: The teleop robot is a specialized client that captures video and audio and executes mobile control commands. It uses UDP to transmit audio and video streams with the service gateway and receives and executes control commands.

- **STUN/TURN Server**: The STUN/TURN server aids in NAT traversal for clients and WebRTC service gateways, enabling them to obtain a public IP address and establish a connection in different network environments. The STUN (Session Traversal Utilities for NAT) server obtains a public IP address, while the TURN (Traversal Using Relays around NAT) server relays data when a direct connection is not feasible.

![系统架构图](../images/teleop.png)

#### 1.2 API interface design

The API interface design of this system primarily includes the following parts:

1.2.0 [Turn Server](./turn-server.md)

1.2.1 [Teleop server](./teleop-server.md)

1.2.2 [Teleop Client](./teleop-client.md)