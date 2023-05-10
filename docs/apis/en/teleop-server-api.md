## Teleop Server API

###  1. Service Management

####  1.1 Create Service

```http request
# Request
POST /v1/service HTTP/1.1

# Request Header
Content-Type: application/json
X-Auth-Token: <token>

# Request Body
None

# Response
{
    "service_id": "string", // Service ID
    "token": "string", // ws connection token
    "user_id": "xxx", // Robot ID
    "status": "string",  // Service Status
    "rooms": { },  // Room Info
    "ice_server": [
        {
            "url": "string",
            "username": "string",
            "password": "string",
            "credential": "string",
        }
    ] // ICE Server Info
}


```

#### 1.2 Delete Service

```http request
# Request
DELETE /v1/service/{service_id} HTTP/1.1

# Request Header
Content-Type: application/json
X-Auth-Token: <token>

# Request Body
None

# Response

{
    "service_id": "string", // Service ID
    "token": "string", // ws connection token
    "user_id": "xxx", // Robot ID
    "status": "string",  // Service Status
    "rooms": { },  // Room Info
    "ice_server": [
        {
            "url": "string",
            "username": "string",
            "password": "string",
            "credential": "string",
        }
    ] // ICE Server Info
}
```

#### 1.3 List Services

```http request
# Request
GET /v1/service HTTP/1.1

# Request Header
Content-Type: application/json
X-Auth-Token: <token>

# Request Body
None

# Response

{
   services: [
      {
        "service_id": "string", // Service ID
        "token": "string", // ws connection token
        "user_id": "xxx", // Robot ID
        "status": "string",  // Service Status
        "rooms": { },  // Room Info
        "ice_server": [
            {
                "url": "string",
                "username": "string",
                "password": "string",
                "credential": "string",
            }
        ] // ICE Server Info
    }
   ],
    total: 0
}
```

#### 1.4 Get Service

```http request

# Request
GET /v1/service/{service_id} HTTP/1.1

# Request Header
Content-Type: application/json
X-Auth-Token: <token>

# Request Body
None

# Response

{
    "service_id": "string", // Service ID
    "token": "string", // ws connection token
    "user_id": "xxx", // Robot ID
    "status": "string",  // Service Status
    "rooms": { },  // Room Info
    "ice_server": [
        {
            "url": "string",
            "username": "string",
            "password": "string",
            "credential": "string",
        }
    ] // ICE Server Info
}
```

### 2. Robot Management

#### 2.1 List Robot

```http request
# Request
GET /v1/robot HTTP/1.1

# Request Header
Content-Type: application/json
X-Auth-Token: <token>

# Request Body
None

# Response
{
   robots: [
      {
         robot_id: "string", // Robot ID
         service_id: "string", // Service ID binded, only when robot-teleop is start
         robot_name: "string", // Robot Name
         robot_type: "string", // Robot Type
         camera: [
             {
               camera_id: "string",
               camera_name: "string",
               camera_type: "string",
               camera_status: "string",
               camera_url: "string"
            }
         ],
         skills: [
            {
                skill_id: "string",
                skill_name: "string",
                skill_type: "string",
                version: "string",
                description: "string",
                parameters: {
                    "string": "string"
                }
            }
         ],
         pcl_status: "string", // Point Cloud Status
         audio_status: "string", // Audio Status
         control_id: "string", // Control ID - only when robot-teleop is start
         architecture: "string", // Arm64 or Amd64
         application: {},  // Application Info
         status: "string", // Robot Status
         robot_create_time: "string",
         robot_update_time: "string"
      }
   ],
    total: 0
}
```

#### 2.2 Start Robot Teleop

```http request
# Request
POST /v1/robot/{robot_id}/{service_id}/start HTTP/1.1

# Request Header
Content-Type: application/json
X-Auth-Token: <token>

# Request Body
None

# Response

{
    "service_id": "string", // Service ID
    "token": "string", // ws connection token
    "user_id": "xxx", // Robot ID
    "status": "string",  // Service Status
    "rooms": { },  // Room Info
    "ice_server": [
        {
            "url": "string",
            "username": "string",
            "password": "string",
            "credential": "string",
        }
    ] // ICE Server Info
}
```

#### 2.3 Stop Robot Teleop

```http request
# Request
POST /v1/robot/{robot_id}/{service_id}/stop HTTP/1.1

# Request Header
Content-Type: application/json
X-Auth-Token: <token>

# Request Body
None

# Response

{
    "service_id": "string", // Service ID
    "token": "string", // ws connection token
    "user_id": "xxx", // Robot ID
    "status": "string",  // Service Status
    "rooms": { },  // Room Info
    "ice_server": [
        {
            "url": "string",
            "username": "string",
            "password": "string",
            "credential": "string",
        }
    ] // ICE Server Info
}
```

### 3. Room Management

#### 3.1 Create Room

```http request

# Request
POST /v1/service/{service_id}/room HTTP/1.1

# Request Header
Content-Type: application/json
X-Auth-Token: <token>

# Request Body

{
    "id": "string", // Room ID, Optional
    "name": "string", // Room Name
    "type": "string", // Room Type
    "token": "string", // Optional
    "max_users": 0, // Optional
    "max_duration": 0 // Optional
}

# Response
{
    "id": "string",
    "name": "string",
    "type": "string",
    "token": "string",
    "max_users": 0,
    "max_duration": 0,
    "room_create_time": "string",
    "room_update_time": "string"
}
```

#### 3.2 List Rooms

```http request

# Request
GET /v1/service/{service_id}/room HTTP/1.1

# Request Header
Content-Type: application/json
X-Auth-Token: <token>

# Request Body
None

# Response
{
   rooms: [
      {
        "id": "string",
        "name": "string",
        "type": "string",
        "token": "string",
        "max_users": 0,
        "max_duration": 0,
        "room_create_time": "string",
        "room_update_time": "string"
     }
   ],
    total: 0
}
```

#### 3.4 Delete Room

```http request

# Request
DELETE /v1/service/{service_id}/room/{room_id} HTTP/1.1

# Request Header
Content-Type: application/json
X-Auth-Token: <token>

# Request Body
None

# Response
None
```

### 2. Control

#### 2.1 websocket connection

```webscoket
# Request
ws://<host>:<port>/v1/service/{service_id}/?token={token}

# Request
service_id: Service ID
token: Service token

```

#### 2.2 Server Event

- Join Room
```webscoket

# Request
{
    "event": "join-room",
    "data": {
        "name": "string", // Client Name
        "type": "string" // Client Type
    }
}

# Action
# The client joins the room, and then the server sends a list of clients in the room to all clients
{
    "event": "room-clients",
    "data": [
        {
            "id": "string", // Clinet ID
            "name": "string", // Client Name
            "type": "string" // Client Type
        }
    ]
}
```

- Leave Room
```webscoket

# Request
{
    "event": "leave-room",
    "data": {
        "name": "string",
        "type": "string"
    }
}

# Action
# A client Leave the room, and then the server sends a list of clients in the room to all clients
{
    "event": "room-clients",
    "data": [
        {
            "id": "string", // Clinet ID
            "name": "string", // Client Name
            "type": "string" // Client Type
        }
    ]
}
```

- Send ice candidate
```webscoket

# Request
{
    "event": "send-ice-candidate",
    "data": {
        "toId": "string",
        "candidate": {
            "candidate": "string",
            "sdpMid": "string",
            "sdpMLineIndex": 0
        }
    }
}

# Action
# The client sends the ice candidate, and then the server sends the ice candidate to the corresponding client
{
    "event": "ice-candidate-received",
    "data": {
        "candidate": {
            "candidate": "string",
            "sdpMid": "string",
            "sdpMLineIndex": 0
        },
        "fromId": "string"
    }
}
```

- Create Answer
```webscoket

# Request
{
    "event": "make-peer-call-answer",
    "data": {
        "toId": "string",
        "answer": {
            "type": "string",
            "sdp": "string"
        }
    }
}

# Action
# The client sends an answer, and then the server sends an answer to the request client
{
    "event": "peer-call-answer-received",
    "data": {
        "answer": {
            "type": "string",
            "sdp": "string"
        },
        "fromId": "string"
    }
}
```

- create new peer connection
```webscoket

# Request
{
    "event": "call-all"
}

# Action
# Server requires all clients to create a new peer-connection and send the offer
{
    "event": "make-peer-call",
    "fromId": "string"
}

```


- create offer
```webscoket

# Request
{
    "event": "call-peer",
    "data": {
        "toId": "string",
        "offer": {
            "type": "string",
            "sdp": "string"
        }
    }
}

# Action
# The client sends an offer, and then the server sends an offer to the corresponding client
{
    "event": "peer-call-received",
    "data": {
        "offer": {
            "type": "string",
            "sdp": "string"
        },
        "fromId": "string"
    }
}
```

- Create PeerConnection
```webscoket

# Request
{
    "event": "call-ids",
    "ids": [
        "string" // Client ID
    ]
}

# Action
# Server requires the specified client to create a peer-connection and send the offer
{
    "event": "make-peer-call",
    "fromId": "string"
}

```

- Close all peer-connections
```webscoket

# Request
{
    "event": "close-all-room-peer-connections",
}

# Action
# Server sends to all clients requests to close all connections
{
    "event": "close-room-peer-connections"
}
```