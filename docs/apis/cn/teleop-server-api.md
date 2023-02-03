##  服务网关 API 详细说明

###  1. 服务管理

####  1.1 遥操作服务创建

```http request
# 请求
POST /v1/service HTTP/1.1

# 请求消息头
Content-Type: application/json
X-Auth-Token: <token>

# 请求Body参数
无

# 响应参数
{
    "service_id": "string", // 服务ID
    "token": "string", // ws 连接认证用，非必须
    "user_id": "xxx", // 机器人ID
    "status": "string",  // 服务状态
    "rooms": { },  // 服务相关的房间信息
    "ice_server": [
        {
            "url": "string", // ICE服务器地址
            "username": "string", // ICE服务器用户名
            "password": "string", // ICE服务器密码
            "credential": "string", // ICE服务器凭证
        }
    ] // ICE服务器地址
}


```

#### 1.2 服务删除

```http request
# 请求
DELETE /v1/service/{service_id} HTTP/1.1

# 请求消息头
Content-Type: application/json
X-Auth-Token: <token>

# 请求Body参数
无

# 响应参数

{
    "service_id": "string", // 服务ID
    "token": "string", // ws 连接认证用，非必须
    "user_id": "xxx", // 机器人ID
    "status": "string",  // 服务状态
    "rooms": { },  // 服务相关的房间信息
    "ice_server": [
        {
            "url": "string", // ICE服务器地址
            "username": "string", // ICE服务器用户名
            "password": "string", // ICE服务器密码
            "credential": "string", // ICE服务器凭证
        }
    ] // ICE服务器地址
}
```

#### 1.3 服务列表

```http request
# 请求
GET /v1/service HTTP/1.1

# 请求消息头
Content-Type: application/json
X-Auth-Token: <token>

# 请求Body参数
无

# 响应参数

{
   services: [
      {
         service_id: "string", // 服务ID
         token: "", // ws服务token
         user_id: "xxx", // 机器人ID
         "status": "string", 
         ...
         service_create_time: "string", // 服务创建时间
         service_update_time: "string", // 服务更新时间
      }
   ],
    total: 0 // 服务总数
}
```

#### 1.4 服务状态查询

```http request

# 请求
GET /v1/service/{service_id} HTTP/1.1

# 请求消息头
Content-Type: application/json
X-Auth-Token: <token>

# 请求Body参数
无

# 响应参数

{
    "service_id": "string", // 服务ID
    "token": "", // ws服务token
    "user_id": "xxx", // 机器人ID
    "sparkrtc": {  // sparkRTC 所需
        "signature": "xxxx",
        "roomID": ""
    },
    "status": "string", 
    "ice_server": [
        {
            "url": "string", // ICE服务器地址
            "username": "string", // ICE服务器用户名
            "password": "string", // ICE服务器密码
            "credential": "string", // ICE服务器凭证
        }
    ] // ICE服务器地址
    "service_create_time": "string", // 服务创建时间
    "service_update_time": "string", // 服务更新时间
}
```

### 2. 机器人管理

#### 2.1 机器人列表

```http request
# 请求
GET /v1/robot HTTP/1.1

# 请求消息头
Content-Type: application/json
X-Auth-Token: <token>

# 请求Body参数
无

# 响应参数
{
   robots: [
      {
         robot_id: "string", // 机器人ID
         service_id: "string", // 绑定的服务ID，仅在start后执行
         robot_name: "string", // 机器人名称
         robot_type: "string", // 机器人类型
         camera: [
             {
               camera_id: "string", // 摄像头ID
               camera_name: "string", // 摄像头名称
               camera_type: "string", // 摄像头类型
               camera_status: "string", // 摄像头状态
               camera_url: "string" // 摄像头地址
            }
         ],
         skills: [
            {
                skill_id: "string", // 技能ID
                skill_name: "string", // 技能名称
                skill_type: "string", // 技能类型
                version: "string", // 技能版本
                description: "string", // 技能描述
                parameters: {
                    "string": "string"
                } // 技能参数
            }
         ],
         pcl_status: "string", // 点云状态
         audio_status: "string", // 音频状态
         control_id: "string", // 遥控器ID
         architecture: "string", // 机器人架构
         application: {},  // 部署的机器人应用
         status: "string", // 机器人状态
         robot_create_time: "string", // 机器人创建时间
         robot_update_time: "string", // 机器人更新时间
      }
   ],
    total: 0 // 机器人总数
}
```

#### 2.2 启动机器人遥操作

```http request
# 请求
POST /v1/robot/{robot_id}/{service_id}/start HTTP/1.1

# 请求消息头
Content-Type: application/json
X-Auth-Token: <token>

# 请求Body参数
无

# 响应参数

{
    "service_id": "string", // 服务ID
    "token": "", // ws服务token
    "user_id": "xxx", // 机器人ID
    "sparkrtc": {  // sparkRTC 所需
        "signature": "xxxx",
        "roomID": ""
    },
    "status": "string", 
    "ice_server": [
        {
            "url": "string", // ICE服务器地址
            "username": "string", // ICE服务器用户名
            "password": "string", // ICE服务器密码
            "credential": "string", // ICE服务器凭证
        }
    ] // ICE服务器地址
    "service_create_time": "string", // 服务创建时间
    "service_update_time": "string", // 服务更新时间
}
```

#### 2.3 停止机器人遥操作

```http request
# 请求
POST /v1/robot/{robot_id}/{service_id}/stop HTTP/1.1

# 请求消息头
Content-Type: application/json
X-Auth-Token: <token>

# 请求Body参数
无

# 响应参数

{
    "service_id": "string", // 服务ID
    "token": "", // ws服务token
    "user_id": "xxx", // 机器人ID
    "sparkrtc": {  // sparkRTC 所需
        "signature": "xxxx",
        "roomID": ""
    },
    "status": "string", 
    "ice_server": [
        {
            "url": "string", // ICE服务器地址
            "username": "string", // ICE服务器用户名
            "password": "string", // ICE服务器密码
            "credential": "string", // ICE服务器凭证
        }
    ] // ICE服务器地址
    "service_create_time": "string", // 服务创建时间
    "service_update_time": "string", // 服务更新时间
}
```

### 3. 房间管理

#### 3.1 创建房间

```http request

# 请求
POST /v1/service/{service_id}/room HTTP/1.1

# 请求消息头
Content-Type: application/json
X-Auth-Token: <token>

# 请求Body参数

{
    "id": "string", // 房间ID, Optional
    "name": "string", // 房间名称
    "type": "string", // 房间类型
    "token": "string", // 房间自定义认证token, Optional
    "max_users": 0, // 房间最大用户数, Optional
    "max_duration": 0, // 房间最大持续时间, Optional
}

# 响应参数
{
    "id": "string", // 房间ID
    "name": "string", // 房间名称
    "type": "string", // 房间类型
    "token": "string", // 房间自定义认证token
    "max_users": 0, // 房间最大用户数
    "max_duration": 0, // 房间最大持续时间
    "room_create_time": "string", // 房间创建时间
    "room_update_time": "string", // 房间更新时间
}
```

#### 3.2 房间列表

```http request

# 请求
GET /v1/service/{service_id}/room HTTP/1.1

# 请求消息头
Content-Type: application/json
X-Auth-Token: <token>

# 请求Body参数
无

# 响应参数
{
   rooms: [
      {
         id: "string", // 房间ID
         name: "string", // 房间名称
         type: "string", // 房间类型
         max_users: 0, // 房间最大用户数
         max_duration: 0, // 房间最大持续时间
         room_create_time: "string", // 房间创建时间
         room_update_time: "string", // 房间更新时间
      }
   ],
    total: 0 // 房间总数
}
```

#### 3.4 房间删除

```http request

# 请求
DELETE /v1/service/{service_id}/room/{room_id} HTTP/1.1

# 请求消息头
Content-Type: application/json
X-Auth-Token: <token>

# 请求Body参数
无

# 响应参数
无
```

### 2. 业务接口

#### 2.1 链接websocket

```webscoket
# 请求
ws://<host>:<port>/v1/service/{service_id}/?token={token}

# 请求参数
service_id: 服务ID
token: 房间token

```

#### 2.2 server 端事件

- 加入房间
```webscoket

# 请求
{
    "event": "join-room", // 事件类型
    "data": {
        "name": "string", // 客户端名称
        "type": "string" // 用户类型
    }
}

# 后果
# 客户端加入房间，随后服务端向所有客户端发送房间内客户端列表
{
    "event": "room-clients",
    "data": [
        {
            "id": "string", // 客户端ID
            "name": "string", // 客户端名称
            "type": "string" // 用户类型
        }
    ]
}
```

- 离开房间
```webscoket

# 请求
{
    "event": "leave-room", // 事件类型
    "data": {
        "name": "string", // 客户端名称
        "type": "string" // 用户类型
    }
}

# 后果
# 客户端离开房间，随后服务端向所有客户端发送房间内客户端列表
{
    "event": "room-clients",
    "data": [
        {
            "id": "string", // 客户端ID
            "name": "string", // 客户端名称
            "type": "string" // 用户类型
        }
    ]
}
```

- 发送ice候选
```webscoket

# 请求
{
    "event": "send-ice-candidate", // 事件类型
    "data": {
        "toId": "string", // 接收ice候选的客户端ID
        "candidate": {
            "candidate": "string", // ice候选
            "sdpMid": "string", // ice候选的媒体标识
            "sdpMLineIndex": 0 // ice候选的媒体索引
        }
    }
}

# 后果
# 客户端发送ice候选，随后服务端向对应客户端发送ice候选
{
    "event": "ice-candidate-received",
    "data": {
        "candidate": {
            "candidate": "string", // ice候选
            "sdpMid": "string", // ice候选的媒体标识
            "sdpMLineIndex": 0 // ice候选的媒体索引
        },
        "fromId": "string" // 发送ice候选的客户端ID
    }
}
```

- 创建 Answer
```webscoket

# 请求
{
    "event": "make-peer-call-answer", // 事件类型
    "data": {
        "toId": "string", // 接收answer的客户端ID
        "answer": {
            "type": "string", // answer类型
            "sdp": "string" // answer内容
        }
    }
}

# 后果
# 客户端发送answer，随后服务端向对应客户端发送answer
{
    "event": "peer-call-answer-received",
    "data": {
        "answer": {
            "type": "string", // answer类型
            "sdp": "string" // answer内容
        },
        "fromId": "string" // 发送answer的客户端ID
    }
}
```

- 通知客户端创建PeerConnection
```webscoket

# 请求
{
    "event": "call-all"
}

# 后果
# 客户端发送全员信息，随后服务端发送全员信息
{
    "event": "make-peer-call",
    "fromId": "string" // 发送全员信息的客户端ID
}

```


- 发送offer
```webscoket

# 请求
{
    "event": "call-peer", // 事件类型
    "data": {
        "toId": "string", // 接收offer的客户端ID
        "offer": {
            "type": "string", // offer类型
            "sdp": "string" // offer内容
        }
    }
}

# 后果
# 客户端发送offer，随后服务端向对应客户端发送offer
{
    "event": "peer-call-received",
    "data": {
        "offer": {
            "type": "string", // offer类型
            "sdp": "string" // offer内容
        },
        "fromId": "string" // 发送offer的客户端ID
    }
}
```

- 通知指定客户端创建PeerConnection
```webscoket

# 请求
{
    "event": "call-ids",
    "ids": [
        "string" // 指定客户端ID
    ]
}

# 后果
# 客户端发送指定信息，随后服务端向指定客户端发送信息
{
    "event": "make-peer-call",
    "fromId": "string" // 发送指定信息的客户端ID
}

```

- 关闭房间所有链接
```webscoket

# 请求
{
    "event": "close-all-room-peer-connections", // 事件类型
}

# 后果
# 服务端向所有客户端发送关闭房间所有链接的时间
{
    "event": "close-room-peer-connections"
}
```