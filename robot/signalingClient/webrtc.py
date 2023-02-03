# Copyright 2021 The KubeEdge Authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import asyncio
import urllib.parse
import json
from signal import (
    SIGINT,
    SIGTERM
)
from typing import (
    Callable,
    Dict,
    List,
    Optional
)

import socketio
from aiortc import (
    RTCIceServer,
    RTCConfiguration,
    RTCDataChannel,
    RTCIceCandidate,
    RTCPeerConnection,
    RTCSessionDescription
)
from aiortc.mediastreams import MediaStreamTrack
from aiortc.contrib.media import MediaBlackhole
from aiortc.sdp import (
    candidate_from_sdp,
    candidate_to_sdp
)

from robosdk.cloud_robotics.edge_base import ClientBase
from robosdk.common.class_factory import (
    ClassFactory,
    ClassType
)
from robosdk.common.constant import ServiceConst
from robosdk.common.logger import logging
from robosdk.common.constant import RoboControlMode

from signalingClient.models import (
    RTCClient,
    ICEServerModel,
    SocketEvents,
    CameraStreamTrack,
    AudioStreamTrack
)


class RoboRTCPeerConnection:
    """
    A RoboRTCPeerConnection represents a WebRTC connection between the local
    """

    def __init__(
            self,
            client: RTCClient,
            ice_servers: ICEServerModel,
            logger=None,
            data_func: Optional[Callable] = None,
            message_callback: Optional[Callable] = None
    ):
        """
        :param client: peer connection client
        :param ice_servers: ice servers
        :param logger: logger
        :param data_func: The function to get data.
        :param message_callback: The callback function to handle message.
        """
        self.client = client
        if logger is None:
            self.logger = logging.bind(
                instance=f"{self.client.name}RTCPeerConnection",
                system=True
            )
        else:
            self.logger = logger
        self._ice_servers = RTCIceServer(
            urls=ice_servers.urls,
            username=ice_servers.username,
            credential=ice_servers.credential
        )
        self._pc = None
        self._message_callback = message_callback
        self._data_func = data_func
        self._initial = False
        self.initial_peer_connection()
        self.is_connected = False

    @property
    def state(self):
        return getattr(self._pc, "connectionState", "connecting")

    def on(self, event: str,
           callback: Optional[Callable] = None,
           params: Optional[Dict] = None):
        self.logger.debug(f"RTC add event registered: {event}")
        # f = lambda *args: callback(*args, **params) if params else callback
        if params:
            def f(*args):
                return callback(*args, **params)
        else:
            f = callback
        self._pc.on(event, f)

        return True

    async def add_ice_candidate(self, candidate: Dict):
        """
        Add a ice candidate.
        """
        self.logger.debug(f"Event: loadIceCandidate {candidate}")
        ice_candidate = candidate_from_sdp(candidate["candidate"])
        ice_candidate.sdpMid = candidate["sdpMid"]
        ice_candidate.sdpMLineIndex = candidate["sdpMLineIndex"]
        await self._pc.addIceCandidate(ice_candidate)

    def initial_peer_connection(self):
        """
        initial peer connection
        """
        if self._initial:
            return
        self._pc = RTCPeerConnection(
            RTCConfiguration(
                [self._ice_servers]
            )
        )
        self.on(
            "connectionstatechange",
            self.connectionstatechange
        )
        self.on(
            "iceconnectionstatechange",
            self._on_ice_connection_state_change
        )
        self.on(
            "icegatheringstatechange",
            self._on_ice_gathering_state_change
        )
        self.on("track", self.on_track)
        self.on("datachannel", self._on_datachannel)
        self._initial = True

    async def close(self):
        """
        Close the connection.
        """
        self.logger.warning('[Event: Closing peer connection]')
        await self._pc.close()
        self._initial = False

    def create_datachannel(
            self,
            label: str,
            maxPacketLifeTime=None,
            maxRetransmits=None,
            ordered=True,
            protocol="",
            negotiated=False,
            _id=None,
    ) -> RTCDataChannel:
        """
        Create a data channel.
        """
        self.logger.debug(f"Event: createDataChannel {label}")
        return self._pc.createDataChannel(
            label,
            maxPacketLifeTime=maxPacketLifeTime,
            maxRetransmits=maxRetransmits,
            ordered=ordered,
            protocol=protocol,
            negotiated=negotiated, id=_id
        )

    async def create_track(
            self,
            kind: str,
            name: str,
            listen_track: Optional[MediaStreamTrack] = None):
        """
        Create a track.
        """
        track = None
        self.logger.debug(f"Event: createTrack {name} - {kind}")
        if kind == "video":
            track = CameraStreamTrack(
                name=name,
                listen_track=listen_track,
                data_func=self._data_func,
                message_callback=self._message_callback
            )
        elif kind == "audio":
            track = AudioStreamTrack(
                name=name,
                listen_track=listen_track,
                data_func=self._data_func,
                message_callback=self._message_callback
            )
        if track:
            await self._on_track(track)
        return track

    async def on_track(self, track: MediaStreamTrack):
        """
        on track
        """
        self.logger.debug(f"Event: onTrack {track.kind} - {track.id}")
        name = getattr(track, "name", track.id)

        return await self.create_track(
            kind=track.kind,
            name=name,
            listen_track=track
        )

    async def connectionstatechange(self):
        """
        connection state change
        """
        self.logger.debug(
            f"{self.client.name} connection state change"
            f"  => {self._pc.connectionState}"
        )
        if self._pc.connectionState in ("failed", "closed", "disconnected"):
            await self.close()
        elif self._pc.connectionState == "connected":
            self.is_connected = True

    async def _on_ice_gathering_state_change(self):
        """
        ice gathering state change
        """
        self.logger.debug(
            f"{self.client.name} ice gathering state change"
            f"   => {self._pc.iceGatheringState}"
        )
        if self._pc.sctp and self._pc.iceGatheringState == 'complete':
            candidates = self._pc.sctp.transport.transport.iceGatherer.getLocalCandidates()  # noqa
            # for candidate in candidates:
            #     # self._ice_candidates.append(candidate)
            #     self._pc.emit("icecandidate", self.client.sid, candidate)

    async def _on_ice_connection_state_change(self):
        """
        ice connection state change
        """
        self.logger.debug(
            f"{self.client.name} ice connection state change "
            f"   => {self._pc.iceConnectionState}"
        )
        if self._pc.iceConnectionState in ("failed", "closed"):
            await self.close()

    async def _on_track(self, track: MediaStreamTrack):
        self.logger.debug(
            f"[Event: Received track : {track.kind}] "
            f"Connection state is {self._pc.connectionState}")
        listen_track = getattr(track, "listen_track", None)

        @track.on("ended")
        def on_ended():
            name = getattr(track, "name", track.id)
            self.logger.debug(f"Track {name} ended")

        if listen_track is not None:
            blackHole = MediaBlackhole()
            blackHole.addTrack(track)
            await blackHole.start()
        else:
            self._pc.addTrack(track)

        return track

    async def _on_datachannel(self, channel: RTCDataChannel):
        self.logger.debug(f"[Event: Received channel {channel.id}]")

        @channel.on("message")
        def on_message(message):
            if self._message_callback is not None:
                self._message_callback(message)

        return channel

    async def create_offer(self):
        await self._pc.setLocalDescription(await self._pc.createOffer())
        _offer = {
            "sdp": self._pc.localDescription.sdp,
            "type": self._pc.localDescription.type
        }
        return _offer

    async def create_answer(self):
        await self._pc.setLocalDescription(await self._pc.createAnswer())
        _answer = {
            "sdp": self._pc.localDescription.sdp,
            "type": self._pc.localDescription.type
        }
        return _answer

    async def set_sdp(self, sdp, kind="answer"):
        self.logger.debug(f'[Event: setRemoteDescription] {kind}')
        await self._pc.setRemoteDescription(
            RTCSessionDescription(sdp=sdp, type=kind))


class SignalingClient:
    """
    webrtc signaling client
    """

    def __init__(
            self,
            client: RTCClient,
            ice_servers: Optional[ICEServerModel] = None,
            logger=None
    ):
        """
        :param client: The client.
        :param logger: The logger.
        """
        if logger is None:
            self.logger = logging.bind(
                instance=f"{client.name}RTCPeerConnection",
                system=True
            )
        else:
            self.logger = logger
        self.ice_servers = ice_servers
        self.client = client
        self._peer_client: Dict[str, RTCClient] = {}
        self._sio = None
        self.kind = "signal"

    def register_socket_envent(self):
        self._sio = socketio.AsyncClient(
            logger=False,
            engineio_logger=False,
            ssl_verify=False,
        )
        self._sio.event(self.connect)
        self._sio.event(self.disconnect)
        self._sio.event(self.close)
        self._sio.on(
            SocketEvents.ROOM_CLIENTS.value,
            self._on_room_clients
        )
        self._sio.on(
            SocketEvents.MAKE_PEER_CALL.value,
            self._on_peer_call
        )
        self._sio.on(
            SocketEvents.PEER_CALL_RECEIVED.value,
            self._on_peer_call_received
        )
        self._sio.on(
            SocketEvents.PEER_CALL_ANSWER_RECEIVED.value,
            self._on_peer_call_answer_received
        )

        self._sio.on(
            SocketEvents.PEER_CALL_ICE_CANDIDATE_RECEIVED.value,
            self._on_ice_candidate_received
        )

    async def disconnect_events(self):
        """
        socketio disconnect events
        """
        self.logger.debug("[Event: disconnect]")
        if self.client.room:
            await self._sio.emit(
                SocketEvents.LEVE_ROOM.value,
                {
                    "name": self.client.name,
                    "room": self.client.room,
                    "type": self.client.utype,
                    "role": self.client.role,
                    "roomId": self.client.roomId,
                }
            )
        self._sio = None

    async def async_run(
            self,
            socket_url: str = "http://127.0.0.1:5540/ws",
            socketio_path: str = "socket.io"
    ):
        """
        Start the client.
        """
        while 1:
            if self._sio is not None:
                await self._sio.disconnect()
            self.register_socket_envent()

            try:
                await self._sio.connect(
                    socket_url,
                    socketio_path=socketio_path,
                    wait_timeout=ServiceConst.SocketTimeout.value
                )
            except Exception as err:
                self.logger.error(f"connect error: {err}")
                await asyncio.sleep(ServiceConst.APICallTryHold.value)
            else:
                break

        await self._sio.wait()

    def _update_sid(self, sid: str):
        if self.client.sid:
            self.logger.debug(
                f"[Event: update_sid] {self.client.sid} => {sid}"
            )
        self.client.sid = sid

    async def connect(self):
        """
        connect
        """
        self.logger.debug("[Event: connect]")
        await self._sio.emit(
            SocketEvents.JOIN_ROOM.value,
            {
                "name": self.client.name,
                "room": self.client.room,
                "type": self.client.utype,
                "role": self.client.role,
                "roomId": self.client.roomId,
            }, callback=self._update_sid
        )

    async def disconnect(self):
        self.logger.debug("Disconnected from signaling server")
        # close the connection
        self._update_sid("")
        await self.close()

    async def close(self):
        self.logger.debug("Connection closed by server")
        # close the connection
        for client in self._peer_client.values():
            if client.pc is not None:
                await client.pc.close()
        await self._sio.disconnect()

    async def _on_room_clients(self, clients: List):
        """
        room clients:
            id: socketId,
            name: Client_name,
            type: type,
            role?: role
        """
        for client in clients:
            room = client.get("room", "") or self.client.room
            roomId = client.get("roomId", "") or self.client.roomId
            if client["id"] in self._peer_client:
                continue
            elif client["name"] == self.client.name:
                self._update_sid(client["id"])
                self.client.room = room
                self.client.roomId = roomId
            if room != self.client.room or roomId != self.client.roomId:
                continue
            self.logger.debug(f"new client: {client}")

            self._peer_client[client["id"]] = RTCClient(
                sid=client["id"],
                pc=None,
                name=client.get("name", ""),
                room=room, roomId=roomId,
                role=client.get("role", ""),
                utype=client.get("type", "")
            )

        if len(self._peer_client) > 1:
            await self._sio.emit(SocketEvents.CALL_ALL.value)

    async def _on_ice_candidate(self, to_id: str, event: RTCIceCandidate):
        data = {
            "toId": to_id,
            "candidate": {
                "candidate": f"candidate:{candidate_to_sdp(event)}",
                "sdpMid": (event.sdpMid or "0"),
                "sdpMLineIndex": (event.sdpMLineIndex or 0),
            }
        }
        self.logger.info(f"try to send ice-candidate {data}")
        self._sio.emit(
            SocketEvents.PEER_CALL_ICE_CANDIDATE.value,
            data
        )

    async def _on_peer_call(self, ids: List[str]):
        """
        peer call id of clients
        """
        self.logger.debug(f"onPeerCallEvent {ids} - {self.kind}")
        tasks = []
        for _id in ids:
            if (
                    _id == self.client.sid or
                    _id not in self._peer_client
            ):
                continue

            self.logger.info(
                f"try to make peer call to {_id}, {self.client.sid}")
            tasks.append(self._make_peer_call(_id))
        if len(tasks):
            await asyncio.wait(tasks)

    async def _make_peer_call(self, _id: str):
        if _id not in self._peer_client:
            self.logger.error(f"{_id} never store")
            return
        client = self._peer_client[_id]
        if getattr(client.pc, "is_connected", False):
            return
        rtc_connection = await self.create_connection(client)
        rtc_connection.on("icecandidate", self._on_ice_candidate)
        client.pc = rtc_connection
        self.logger.debug(
            f"makePeerCall (form {self.client.sid} to_id={_id})")
        # create rtc offer
        offer: Dict = await rtc_connection.create_offer()
        udata = {
            "toId": _id,
            "offer": offer
        }
        self.logger.debug(f"call-peer (to_id={_id}) => {offer}")
        await self._sio.emit(SocketEvents.PEER_CALL.value, udata)

    async def _on_peer_call_received(self, data: Dict):
        """
        peer call received
        """
        self.logger.debug(f"[Event: peer_call_received] {data}")
        _id = data.get("fromId", "")
        if _id not in self._peer_client:
            self.logger.error(f"{_id} never store")
            return
        client = self._peer_client[_id]
        if getattr(client.pc, "is_connected", False):
            return
        rtc_connection = await self.create_connection(client)
        rtc_connection.on("icecandidate", self._on_ice_candidate)
        client.pc = rtc_connection
        offer = data.get("offer", {})
        if "sdp" not in offer:
            self.logger.error("offer sdp not found")
            return
        await client.pc.set_sdp(offer["sdp"], "offer")
        answer: Dict = await rtc_connection.create_answer()
        udata = {
            "toId": _id,
            "answer": answer
        }
        await self._sio.emit(
            SocketEvents.MAKE_PEER_CALL_ANSWER.value, udata
        )

    async def _on_peer_call_answer_received(self, data: Dict):
        """
        peer call answer received
        """
        self.logger.debug(f"[Event: peer_call_answer_received] {data}")
        _id = data.get("fromId", "")
        answer = data.get("answer", {})
        client = self._peer_client.get(_id, None)
        if not getattr(client, "pc", None):
            return
        if "sdp" not in answer:
            self.logger.error("answer sdp not found")
            return
        try:
            await client.pc.set_sdp(answer["sdp"], "answer")
        except Exception as e:
            self.logger.error(f"set answer sdp error: {e}")
            return

    async def _on_ice_candidate_received(self, data: Dict):
        """
        ice candidate received, update ice candidate
        """
        from_id = data.get("fromId", "")
        candidate = data.get("candidate") or {}
        self.logger.debug(f"ice-candidate-received, {data}")
        if not candidate.get("candidate", ""):
            return
        client = self._peer_client.get(from_id, None)
        if not getattr(client, "pc", None):
            return
        await client.pc.add_ice_candidate(candidate)

    async def create_connection(
            self,
            client: RTCClient
    ) -> RoboRTCPeerConnection:
        raise NotImplemented


class DataChannelClient(SignalingClient):
    """
    Data channel client
    """

    def __init__(
            self,
            client: RTCClient,
            logger: None,
            ice_servers: Optional[ICEServerModel] = None,
            data_func: Optional[Callable] = None,
            message_callback: Optional[Callable] = None,
    ):
        """
        :param client: The client instance.
        :param logger: The logger instance.
        :param ice_servers: The ice servers.
        :param data_func: The data generate function.
        :param message_callback: The message callback.
        """
        super(DataChannelClient, self).__init__(
            client, logger=logger, ice_servers=ice_servers
        )
        self._data_channel: Optional[RTCDataChannel] = None
        self._tasks = None
        self._data_func = data_func
        self._message_callback = message_callback
        self.kind = "datachannel"

    async def create_connection(
            self,
            client: RTCClient
    ) -> RoboRTCPeerConnection:
        rtc_connection = RoboRTCPeerConnection(
            client,
            ice_servers=self.ice_servers,
            logger=self.logger,
            data_func=self._data_func,
            message_callback=self._message_callback
        )
        channel_name = client.room or "chat"
        self._data_channel = rtc_connection.create_datachannel(channel_name)
        self._data_channel.on("open", self._on_dc_open)
        self._data_channel.on("message", self._on_dc_message)
        self._data_channel.on("close", self._on_dc_close)
        self._tasks = None
        return rtc_connection

    def _on_dc_open(self):
        dc = self._data_channel
        self.logger.debug(f"on_open: {dc.label}")
        self._tasks = asyncio.ensure_future(self.on_datachannel())

    async def on_datachannel(self):
        if self._data_func is None:
            return
        while 1:
            if self._data_channel.readyState != "open":
                continue
            status_dict: Dict = self._data_func()
            try:
                my_data = json.dumps(status_dict)
                self._data_channel.send(my_data)
            except Exception as e:
                self.logger.error(f"json dumps error: {e}")
                continue

            await asyncio.sleep(1)

    def _on_dc_close(self):
        dc = self._data_channel
        self.logger.debug(f"on_close: {dc.label}")
        if self._tasks:
            self._tasks.cancel()

    def _on_dc_message(self, message: str):
        self.logger.debug(f"on_message: {message}")
        if self._message_callback is None:
            return
        self._message_callback(message)


class StreamClient(SignalingClient):
    """
    Stream client
    """

    def __init__(
            self,
            client: RTCClient,
            logger: None,
            ice_servers: Optional[ICEServerModel] = None,
            data_func: Optional[Callable] = None,
            message_callback: Optional[Callable] = None,
            video_enable: bool = True,
            audio_enable: bool = False,
            kind: str = "stream"
    ):
        """
        :param client: The client instance.
        :param logger: The logger instance.
        :param ice_servers: The ice servers.
        :param data_func: The [video, audio] generate function.
        :param message_callback: The message callback.
        :param video_enable: Enable video.
        :param audio_enable: Enable audio.
        :param kind: The kind of client.
        """
        super(StreamClient, self).__init__(
            client, logger=logger, ice_servers=ice_servers)
        self._data_func = data_func
        self._message_callback = message_callback
        self.video_enable = video_enable
        self.audio_enable = audio_enable
        self.kind = kind

    async def create_connection(
            self,
            client: RTCClient
    ) -> RoboRTCPeerConnection:
        rtc_connection = RoboRTCPeerConnection(
            client,
            ice_servers=self.ice_servers,
            logger=self.logger,
            data_func=self._data_func,
            message_callback=self._message_callback
        )
        stream_name = client.room or "stream"
        if self.video_enable:
            await rtc_connection.create_track(
                "video", f"{stream_name}.video"
            )
        if self.audio_enable:
            await rtc_connection.create_track(
                "audio", f"{stream_name}.audio"
            )
        return rtc_connection


@ClassFactory.register(ClassType.CLOUD_ROBOTICS, "webrtc_control_robot")
class ControlRTCRobot(ClientBase):  # noqa
    def __init__(self,
                 robot,
                 name: str = "control",
                 loop=None,
                 ice_servers: Optional[ICEServerModel] = None,
                 **kwargs,
                 ):
        """
        :param robot: The robot instance.
        :param name: The name of the client.
        :param loop: The event loop.
        :param kwargs: The other parameters.
        """
        super(ControlRTCRobot, self).__init__(name=name, **kwargs)
        is_ssl = kwargs.get("ssl", "")
        if not self.uri.startswith("http"):
            self.uri = f"https://{self.uri}" if is_ssl else f"http://{self.uri}"
        self.uri, self.socketio_path = self._parse_socket_uri(self.uri)
        self.robot = robot
        self._workers: Dict[str, SignalingClient] = {}
        self.ice_server = ice_servers
        if loop is None:
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = asyncio.get_event_loop()
        self.loop = loop

    @staticmethod
    def _parse_socket_uri(uri: str):
        """
        Parse socket uri.
        :param uri: The socket uri.
        :return: The base_url and socketio_path.
        """
        engineio_path = 'socket.io'
        parsed_url = urllib.parse.urlparse(uri)
        _path = parsed_url.path.strip('/')
        if not _path.endswith(engineio_path):
            _path = _path + '/' + engineio_path
        query_str = parsed_url.query
        url = '{scheme}://{netloc}?{query}'.format(
            scheme=parsed_url.scheme, netloc=parsed_url.netloc,
            query=query_str)
        if not _path.startswith('/'):
            _path = '/' + _path
        return url, _path

    def add_worker(self,
                   name_space: str = "Teleop",
                   kind: str = "datachannel",
                   video_enable: bool = True,
                   audio_enable: bool = False,
                   data_func: Optional[Callable] = None,
                   message_callback: Optional[Callable] = None):
        """
        Add a worker to control robot.
        :param name_space: The namespace of the worker.
        :param kind: The kind of the rtc connection, datachannel or steam.
        :param video_enable: Whether to enable video.
        :param audio_enable: Whether to enable audio.
        :param data_func: function used to generate datas for remote offer.
        :param message_callback: function used to process receiving data.
        """
        if name_space in self._workers:
            return
        client = RTCClient(
            sid="",
            name=f"{self.robot.robot_name}.{name_space}",
            room=name_space,
            utype="robot"
        )
        if kind in ("stream", "remote"):
            stream = StreamClient(
                client=client,
                logger=self.logger,
                ice_servers=self.ice_server,
                video_enable=video_enable,
                audio_enable=audio_enable,
                data_func=data_func,
                kind=kind,
                message_callback=message_callback
            )
        else:
            stream = DataChannelClient(
                client=client,
                ice_servers=self.ice_server,
                logger=self.logger,
                data_func=data_func,
                message_callback=message_callback
            )
        self._workers[name_space] = stream

    def run(self):
        setattr(self.robot, "control_mode", RoboControlMode.Remote)
        workers = []
        for n, w in self._workers.items():
            main_task = asyncio.ensure_future(
                w.async_run(
                    self.uri, socketio_path=self.socketio_path
                ), loop=self.loop
            )
            for signal in [SIGINT, SIGTERM]:
                self.loop.add_signal_handler(signal, main_task.cancel)
            workers.append(main_task)

        self.loop.run_forever()

    def stop(self):
        for n, w in self._workers.items():
            w.close()
        self.loop.stop()
