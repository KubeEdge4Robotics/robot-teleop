## Stun/turn API Design

### 1. Overview

The establishment of data/stream typically involves two parts: signaling and media. 
Before data transmission can occur on the client side, an ICE (Interactive Connectivity Establishment) connection must be established. 
This network protocol is defined in RFCs with standard protocols such as STUN and TURN, which require the use of STUN and TURN servers to complete the process.

The STUN server is used to obtain the client's public IP address and port number for P2P (peer-to-peer) connections, while the TURN server relays and forwards data streams between clients.

In our solution, [coturn](https://github.com/coturn/coturn.git) is used as the STUN/TURN server.

### 2. STUN/TURN server

#### 2.1 coturn Configuration

```yaml
# coturn Configuration
lt-cred-mech  # use long-term credentials
no-tls  # no tls use
no-dtls  # no dtls use
verbose  # print log
listening-port=3487  # listening port
min-port=49150  # udp listening min port
max-port=49200  # udp listening max port
realm=coturn-svc.default:3487 # k8s service uri
external-ip=::1/::1  # external ip (public)
```

#### coturn use
The native WebRTC SDK integrates support for coturn, and you can directly specify the address and port number of coturn in its configuration items to complete coturn access.

```bash 
cat iceServers.json
```

```json 
[
  {
      "urls": "stun:coturn-svc.default:3487"
  }
]
```
