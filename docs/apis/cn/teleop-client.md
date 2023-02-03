## 客户端接口设计

### 1. 服务概述

客户端是指用于对远程机器人进行遥操作的js客户端，本章节主要介绍客户端接口设计，包括客户端接入、客户端接口、客户端数据流等。

### 2. 客户端接入

客户端通过http restful接口与服务端进行服务管理，通过websocket与服务端进行业务通信，通过WebRTC与机器人进行媒体通信。

### 3. 客户端接口

WebRTC客户端接口主要包括：
- 标准的协议栈，主要包括推荐用于信令交互的TCP协议栈和用于媒体数据传输的UDP协议栈。
- WebRTC C++实现和C++ Native API，可以用于开发者直接用在客户端App上面。
- 标准的JavaScript API，主要用于给浏览器直接使用。

![img.png](../images/webrtc-protoal.png)

### 4. 客户端数据流

> 数据流的建链通常会包括信令和媒体两个部分，在客户端传输数据之前，需要建立ICE（Interactive Connectivity Establishment）连接，这部分网络协议有标准的RFC定义：STUN、TURN，需要借助STUN和TURN服务器来完成。
> 
> 通信双方通过信令服务器来交换彼此的SDP信息， 建立 PeerConnection链接，完成之后，就可以传输编码之后的音视频和数据流了。
> 
> SDP是一份具有特殊约定格式的纯文本描述文档，其中包含了WebRTC建立连接所需要的ICE服务器信息、音视频编解码信息等（如下例所示）。

```yaml
v=0
o=jdoe 2890844526 2890842807 IN IP4 10.47.16.5
s=SDP Seminar
i=A Seminar on the session description protocol
u=http://www.example.com/seminars/sdp.pdf
e=j.doe@example.com (Jane Doe)
c=IN IP4 224.2.17.12/127
t=2873397496 2873404696
a=recvonly
m=audio 49170 RTP/AVP 0
m=video 51372 RTP/AVP 99
a=rtpmap:99 h263-1998/90000
```

![img.png](../images/rtc-connection.png)

#### 4.1 音视频数据流 (Streaming)

TBA

#### 4.2 控制数据流 (dataChannel)

##### 4.2.1 数据上报格式

- 机器人状态信息

```json

{
    "type": "robotStatus",
    "status": {
        "battery": 0, // 电量
        "isCharging": false, // 是否充电中
        "batteryVoltage": 0, // 电池电压
        "batteryCurrent": 0, // 电池电流
        "batteryLevel": 0, // 电池电量
        "cpuUsage": 0, // cpu使用率
        "memUsage": 0, // 内存使用率
        "wifiNetwork": "", // wifi网络名称
        "wifiStrength": "", // wifi信号强度
        "localIp": "", // 本地IP
        "diskUsage": 0 // 磁盘使用率
    }
}
```

##### 4.2.2 数据下发格式

- 执行预置技能

```json

{
  "type": "action",
  "cmd": "skill", // 技能
  "action": "pickup" // 技能名称
}

```

- 强制停止机器人

```json

{
  "type": "stop"
}

```

- 机器人移动

```json

{
  "type": "velCmd",
  "x": 0, // 线速度
  "yaw": 0 // 角速度
}
```
