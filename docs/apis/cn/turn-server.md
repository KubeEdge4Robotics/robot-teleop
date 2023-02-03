## Stun/turn 服务接口设计

### 1. 服务概述
数据流的建链通常会包括信令和媒体两个部分，在客户端传输数据之前，需要建立ICE（Interactive Connectivity Establishment）连接，这部分网络协议有标准的RFC定义：STUN、TURN，需要借助STUN和TURN服务器来完成。

Stun 服务器用于获取客户端的公网 IP 地址和端口号进行P2P连接，Turn 服务器用于中继转发客户端之间的数据流。

本操作方案中使用的 Stun/Turn 服务器为 [coturn](https://github.com/coturn/coturn.git).

### 2. 业务接口

#### 2.1 coturn 配置

```yaml
# coturn 配置文件
lt-cred-mech  # 使用长期凭证
no-tls  # 不使用 tls
no-dtls  # 不使用 dtls
verbose  # 终端打印日志
listening-port=3487  # 监听端口
# listening-device=eth0  # 监听设备， 默认为所有设备，可选
min-port=49150  # udp监听连接的最小端口
max-port=49200  # udp监听连接的最大端口
realm=coturn-svc.default:3487 # k8s service uri
external-ip=::1/::1  # 外部ip
```

#### coturn 接入
原生的WebRTC SDK 集成了对coturn的支持，可以直接在其配置项中指定coturn的地址和端口号，即可完成coturn的接入。

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
