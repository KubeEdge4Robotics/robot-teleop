## 系统接口设计

>Notes: 本文档是系统接口设计的说明文档，主要用于系统接口设计的说明，以及接口的使用说明。
>适用于遥操作服务开发人员基于 Docker + K8S + KubeEdge 进行组件开发。


### 1. 系统架构简介

移动机器人遥操作服务的目标是允许用户通过 Web 界面与远程机器人进行实时音视频通信和控制，详细的方案选型和设计请参考[《移动机器人遥操作服务设计》](../proposal_cn.md)

#### 1.1 系统架构图
这个系统架构图主要包含以下几个部分：

- **客户端（Teleop-Client）**：客户端可以是浏览器、移动设备或其他支持WebRTC协议的终端，本方案中基于 Vue3+Vite 开发，通过WebSocket协议与信令服务器进行信令交换，通过UDP协议与WebRTC服务网关进行音视频流传输。
- **信令服务器（Signaling-Server）**：信令服务器负责处理客户端之间的会话建立、媒体协商、控制指令等信令信息，它使用SDP（Session Description Protocol）和ICE（Interactive Connectivity Establishment）协议来描述和建立音视频连接。
- **服务网关（Teleop-Server）**：服务网关负责业务鉴权、机器人列表、会话管理、组件创建等服务。
- **远端机器人（Teleop-Robot）**：远端机器人是一种特殊的客户端，它具备摄像头、麦克风和执行移动控制指令的能力，通过UDP与服务网关进行音视频流传输，以及接收和执行控制指令。
- **STUN/TURN服务器（Turn-Server）**：STUN/TURN服务器负责帮助客户端和WebRTC服务网关实现NAT穿越，即在不同网络环境下获取公网IP地址并建立连接。STUN（Session Traversal Utilities for NAT）服务器用于获取公网IP地址，TURN（Traversal Using Relays around NAT）服务器用于在无法直连的情况下中转数据。

![系统架构图](../images/teleop.png)

#### 1.2 系统接口设计

本系统的接口设计主要包含以下几个部分：

1.2.0 [Turn 服务器接口设计](./turn-server.md)

1.2.1 [服务网关接口设计](./teleop-server.md)

1.2.2 [客户端接口设计](./teleop-client.md)