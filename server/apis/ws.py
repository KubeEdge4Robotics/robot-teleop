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
import datetime
import itertools
from typing import Optional
from typing import Union
from typing import Dict
from typing import List
from enum import Enum

import socketio

from server.orm.models import ServiceModel
from server.orm.models import ServerStatus
from server.orm.models import RoomManage
from server.orm.models import RoomModel
from server.orm.models import RoomClient
from server.orm.db import DataManage


class SocketEvents(Enum):
    """
    Socket events
    """
    # client events
    CONNECT = "connect"
    DISCONNECT = "disconnect"
    CLOSE = "close"
    ROOM_CLIENTS = "room-clients"
    MAKE_PEER_CALL = "make-peer-call"
    PEER_CALL_ICE_CANDIDATE_RECEIVED = "ice-candidate-received"
    PEER_CALL_RECEIVED = "peer-call-received"
    PEER_CALL_ANSWER_RECEIVED = "peer-call-answer-received"
    PEER_CALL_CLOSE = "close-all-peer-connections-request-received"

    # server events
    JOIN_ROOM = "join-room"
    LEVE_ROOM = "leave-room"
    MAKE_PEER_CALL_ANSWER = "make-peer-call-answer"
    CALL_ALL = "call-all"
    CALL = "call-ids"
    PEER_CALL = "call-peer"
    PEER_CALL_ICE_CANDIDATE = "send-ice-candidate"
    CLOSE_ALL = "close-all-room-peer-connections"


class WebRTCGatewayWSServer:
    DISCONNECT_DELAY_S = 1
    INACTIVE_DELAY_S = 30
    PING_TIME_OUT = 60

    def __init__(
            self,
            logger: None,
            redis_client: DataManage,
            async_mode: str = "asgi",
            cors_allowed_origins: Union[str, list] = '*',
    ):

        self.logger = logger
        self._sio = socketio.AsyncServer(
            async_mode=async_mode,
            ping_timeout=self.PING_TIME_OUT,
            cors_allowed_origins=cors_allowed_origins
        )
        self._services: Dict[str, ServiceModel] = {}
        self._rooms: Dict[str, RoomManage] = {}  # service_id: RoomManage
        self._redis_client = redis_client
        self._should_exit = False

    @property
    def sio(self) -> socketio.AsyncServer:
        """Return the Socket.IO instance."""
        return self._sio

    def initial(self):
        self.sio.on(SocketEvents.CONNECT.value, self.on_connect)
        self.sio.on(SocketEvents.DISCONNECT.value, self.disconnect)

        self.sio.on(SocketEvents.JOIN_ROOM.value, self.join_rtc_room)
        self.sio.on(SocketEvents.LEVE_ROOM.value, self.leave_rtc_room)
        self.sio.on(
            SocketEvents.PEER_CALL_ICE_CANDIDATE.value, self.ice_candidate
        )
        self.sio.on(
            SocketEvents.MAKE_PEER_CALL_ANSWER.value, self.make_call_answer
        )
        self.sio.on(SocketEvents.CALL_ALL.value, self.call_all)
        self.sio.on(SocketEvents.PEER_CALL.value, self.call_peer)
        self.sio.on(SocketEvents.CALL.value, self.call_ids)
        self.sio.on(SocketEvents.CLOSE_ALL.value, self.close)

    async def run(self):
        self.initial()
        await self.sio.start_background_task(self.self_check)

    async def self_check(self):
        while 1:
            if self._should_exit:
                break
            await asyncio.sleep(self.INACTIVE_DELAY_S)
            try:
                await self._check_inactive()
            except Exception as e:
                self.logger.error(f"check inactive error {e}")
            try:
                await self._check_disconnect()
            except Exception as e:
                self.logger.error(f"check disconnect error {e}")

    async def _check_inactive(self):
        remove_service_ids = []

        for service_id, room_manage in self._rooms.items():
            # get service last active time
            service = await self._redis_client.get_service(service_id)
            if not service:
                remove_service_ids.append(service_id)
                continue
            _client = self.sio.manager.rooms["/"].get(
                service.service_id, {}
            ).keys()
            if len(_client) > 0:
                continue
            update_time = datetime.datetime.strptime(
                service.update_time, "%Y-%m-%d %H:%M:%S"
            ) if getattr(service, "update_time", None) else None
            # if service is inactive or update_time is 2 hours ago
            if update_time and (datetime.datetime.now() - update_time
                                > datetime.timedelta(hours=2)):
                self.logger.debug(f"service {service_id} is inactive")
                remove_service_ids.append(service_id)
        for service_id in remove_service_ids:
            await self._redis_client.delete_service(service_id)
            self._rooms.pop(service_id)

    async def _check_disconnect(self):
        remove_sids = []
        for sid, server in self._services.items():
            if server.service_id not in self._rooms:
                # service is inactive, disconnect all clients
                self.logger.debug(
                    f"service {server.service_id} is inactive")
                await self.sio.disconnect(sid)
                remove_sids.append(sid)
        for sid in remove_sids:
            self._services.pop(sid)

    async def on_connect(self, sid: str, env):
        self.logger.debug(f"Client {sid} connected")
        # get service id from path_params
        service_id = env['asgi.scope']['path_params'].get("service_id", "")
        server: ServiceModel = await self._redis_client.get_service(service_id)
        if (
                getattr(server, "status", "") not in
                (ServerStatus.active, ServerStatus.inactive)
        ):
            self.logger.error(f"inactive Service {service_id}")
            return
        server.update_time = datetime.datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )
        await self._redis_client.update_service(service_id, server)
        # join service room
        self.sio.enter_room(sid, service_id)
        self._services[sid] = server
        if service_id not in self._rooms:
            self._rooms[service_id] = RoomManage(
                service_id=service_id,
            )
            self._rooms[service_id].update_from_json(server.rooms)
        self.logger.debug(f"Client {sid} connected {service_id}")

    async def disconnect(self, sid: str):
        self.logger.debug(f"Client {sid} disconnected")
        rtc = self._get_rtc_room(sid)
        if not rtc:
            return

        try:
            self.logger.debug(f"Client {sid} disconnect {rtc.service_id}")
            self.sio.leave_room(sid, rtc.service_id)
            await self.sio.disconnect(sid)
        except Exception as e:
            self.logger.debug(f"disconnect error {e}")
        finally:
            rtc.kcick(sid)

    def _get_rtc_room(self, sid: str) -> Optional[RoomManage]:
        server: ServiceModel = self._services.get(sid)
        if not server:
            return
        return self._rooms.get(server.service_id)

    def _get_rtc_room_online_clients(
            self, room: RoomModel, service_id: str,
            exclude_sid: List[str] = None
    ):
        _client = list(self.sio.manager.rooms["/"].get(service_id, {}).keys())
        participants = []
        for s in room.participants_list:
            if s.client_id not in _client:
                self.logger.info(
                    f'remove_inactive_user: {s.client_id} from {room.room_name}'
                )
                continue
            if exclude_sid and s.client_id in exclude_sid:
                continue
            participants.append(s)
        return participants

    async def join_rtc_room(self, sid: str, data: Dict) -> str:
        self.logger.debug(f"Client {sid} join room {data}")
        rtc_ = self._get_rtc_room(sid)
        if not rtc_:
            self.logger.error(f"client {sid} never connected")
            return ""
        room_name = data.get("room", "")
        room_id = data.get("roomId", "")
        client_name = data.get("name", "")
        client_type = data.get("type", "")
        client_role = data.get("role", "")
        if not ((room_name or room_id) and client_name):
            self.logger.error(f"join room {data} error")
            return ""

        if not len(rtc_.rooms):
            rtc_.initial()
        rtc_room = rtc_.get_room(room_name=room_name, room_id=room_id)
        if not rtc_room:
            self.logger.error(f"room {room_name} invalid")
            return ""

        client = RoomClient(
            client_id=sid,
            client_name=client_name,
            client_type=client_type,
            client_role=client_role
        )
        rtc_.join_room(rtc_room, client)
        data = []
        all_ids = []
        for r in self._get_rtc_room_online_clients(
                rtc_room, rtc_.service_id
        ):
            data.append(
                {
                    "id": r.client_id,
                    "name": r.client_name,
                    "type": r.client_type,
                }
            )
            all_ids.append(r.client_id)
        await self.send_json(
            SocketEvents.ROOM_CLIENTS.value, rtc_room, data, all_ids)
        self.logger.info(
            f"Client {client_name} join room {rtc_room.room_name}")
        return sid

    async def leave_rtc_room(self, sid: str, data: Dict) -> bool:
        self.logger.debug(f"Client {sid} leave room {data}")
        rtc_ = self._get_rtc_room(sid)
        if not rtc_:
            self.logger.error(f"client {sid} never connected")
            return False
        room = data.get("room", "")
        room_id = data.get("roomId", "")
        rtc_room = rtc_.get_room(room_name=room, room_id=room_id)
        if not rtc_room:
            self.logger.error(f"room {room} invalid")
            return False

        rtc_.leave_room(rtc_room, sid)
        _data = [
            {
                "id": r.client_id,
                "name": r.client_name,
                "type": r.client_type,
            }
            for r in self._get_rtc_room_online_clients(
                rtc_room, rtc_.service_id
            )
        ]
        await self.send_json(
            SocketEvents.ROOM_CLIENTS.value, rtc_room, _data)
        self.logger.info(f"Client {sid} leave room {rtc_room.room_name}")
        return True

    async def send_json(self,
                        event: str,
                        room: RoomModel,
                        data: Union[Dict, List],
                        to_id: Optional[List[str]] = None):
        if not event:
            return
        if not to_id:
            to_id = [r.client_id for r in room.participants_list]
        if not len(to_id):
            return
        tasks = []
        for sid in to_id:
            tasks.append(
                self._sio.emit(event, data, to=sid, room=room.service_id)
            )
        await asyncio.wait(tasks)

    async def _call_client(self, from_id: str, data: Dict, event: str):
        to_id = data.get("toId", "")
        if not to_id:
            return
        if to_id == from_id:
            return
        from_service: ServiceModel = self._services.get(from_id, "")
        to_service: ServiceModel = self._services.get(to_id, "")
        service_id = getattr(from_service, "service_id", "")
        if not (
                service_id and
                service_id == getattr(to_service, "service_id", "")
        ):
            return
        _rtc: RoomManage = self._rooms.get(service_id)
        if _rtc is None:
            self.logger.error(f"client {from_id} never connected")
            return
        data['fromId'] = from_id
        self.logger.debug(f'{event}: {data} - from {from_id}')
        await self.sio.emit(
            event, data, to=to_id, room=from_service.service_id)

    async def ice_candidate(self, from_id: str, data: Dict):
        self.logger.debug(f'ice-candidate by {from_id}')
        await self._call_client(
            from_id, data, SocketEvents.PEER_CALL_ICE_CANDIDATE_RECEIVED.value
        )

    async def call_peer(self, from_id, data):
        self.logger.debug(f'call-peer by {from_id}')
        await self._call_client(
            from_id, data, SocketEvents.PEER_CALL_RECEIVED.value
        )

    async def make_call_answer(self, from_id, data):
        self.logger.debug(f'make-call-answer by {from_id}')
        await self._call_client(
            from_id, data, SocketEvents.PEER_CALL_ANSWER_RECEIVED.value
        )

    async def call_all(self, from_id):
        self.logger.debug(f'call-all by {from_id}')
        server: ServiceModel = self._services.get(from_id)
        if not server:
            self.logger.error(f"client {from_id} never connected")
            return
        service_id = server.service_id
        _rtc: RoomManage = self._get_rtc_room(from_id)
        all_rooms = _rtc.get_room_of_client(from_id)
        _client = self.sio.manager.rooms["/"].get(service_id, {}).keys()
        tasks = []
        for room_name in all_rooms:
            room = _rtc.get_room_by_name(room_name)
            if room is not None:
                all_client = [
                    r.client_id for r in room.participants_list
                ]
                tmp_ids = list(set(_client) & set(all_client))
                if not len(tmp_ids):
                    continue
                tasks.append(
                    self.call_ids(from_id, list(tmp_ids))
                )
            else:
                self.logger.debug(f"room {room_name} not found")
                continue
        if len(tasks) == 0:
            return
        await asyncio.wait(tasks)

    async def call_ids(self, from_id: str, ids: List):
        _rtc: RoomManage = self._get_rtc_room(from_id)
        if _rtc is None:
            self.logger.error(f"client {from_id} never connected")
            return

        ids = list(set(ids) & set(_rtc.participants.keys()) - {from_id})
        self.logger.debug(f'call-id {from_id} - {ids}')
        # make sure fromId be called
        ids.append(from_id)
        if len(ids) < 2:
            return
        combinations = itertools.combinations(ids, 2)
        tasks = []
        for _id in ids:
            ids_to_call = [c[1] for c in combinations if c[0] == _id]
            if len(ids_to_call) == 0:
                continue
            tasks.append(
                self.sio.emit(
                    SocketEvents.MAKE_PEER_CALL.value,
                    ids_to_call,
                    to=_id
                )
            )
        await asyncio.gather(*tasks)

    async def close(self, from_id):
        self.logger.debug(f'close by {from_id}')
        self._should_exit = True

        _rtc = self._get_rtc_room(from_id)
        if _rtc is None:
            self.logger.error(f"client {from_id} never connected")
            return
        data = {}
        for room_name, client in _rtc.get_room_of_client(from_id).items():
            room = _rtc.get_room(room_name=room_name)
            all_client = self._get_rtc_room_online_clients(
                room, _rtc.service_id, exclude_sid=[from_id]
            )
            all_client_id = [r.client_id for r in all_client]
            await self.send_json(
                SocketEvents.PEER_CALL_CLOSE.value,
                room, data, all_client_id
            )

        await self.disconnect(from_id)
