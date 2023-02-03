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

from typing import Optional
from typing import List
from datetime import datetime

import uuid
from fastapi.routing import APIRoute
from robosdk.common.exceptions import CloudError

from server.orm.db import DataManage
from server.orm.models import ServiceModel
from server.orm.models import ServerStatus
from server.orm.models import ICEServerModel
from server.orm.models import RoomManage
from server.orm.models import RoomModel
from server.utils.utils import EventManager
from server.utils.utils import gen_token
from server.apis.__version__ import __version__ as version


class ServerAPI:
    prefix = f"/{version}/service"

    def __init__(
            self,
            redis_client: DataManage,
            logger,
            ice_servers: Optional[ICEServerModel] = None
    ):
        self._event_bus = EventManager()
        self.redis_client: DataManage = redis_client
        self._ice_servers = ice_servers
        self.logger = logger

    def initial(self) -> List[APIRoute]:
        return [
            APIRoute(
                path=self.prefix,
                endpoint=self.list_services,
                methods=["GET"],
                name="list_services",
                tags=["service"],
                summary="List all services"
            ),
            APIRoute(
                path=f"{self.prefix}/" + "{service_id}",
                endpoint=self.get_service,
                methods=["GET"],
                name="get_service",
                tags=["service"],
                summary="Get service by id",
                response_model=Optional[ServiceModel]
            ),
            APIRoute(
                path=f"{self.prefix}",
                endpoint=self.create_service,
                methods=["POST"],
                name="create_service",
                tags=["service"],
                summary="Create a new service",
                response_model=ServiceModel
            ),
            APIRoute(
                path=f"{self.prefix}/" + "{service_id}",
                endpoint=self.delete_service,
                methods=["DELETE"],
                name="delete_service",
                tags=["service"],
                summary="Delete a service by id",
                response_model=ServiceModel
            ),
            APIRoute(
                path=f"{self.prefix}/" + "{service_id}/rooms",
                endpoint=self.get_rooms,
                methods=["GET"],
                name="get_rooms",
                tags=["room"],
                summary="Get rooms by service id",
            ),
            APIRoute(
                path=f"{self.prefix}/" + "{service_id}/rooms",
                endpoint=self.create_room,
                methods=["POST"],
                name="create_room",
                tags=["room"],
                summary="Create a new room",
                response_model=RoomModel
            ),
            APIRoute(
                path=f"{self.prefix}/" + "{service_id}/rooms/{room_id}",
                endpoint=self.delete_room,
                methods=["DELETE"],
                name="delete_room",
                tags=["room"],
                summary="Delete a room by id",
                response_model=RoomModel
            ),
            APIRoute(
                path=f"{self.prefix}/" + "{service_id}/rooms/{room_id}",
                endpoint=self.get_room,
                methods=["GET"],
                name="get_room",
                tags=["room"],
                summary="Get room by id",
                response_model=RoomModel
            ),
        ]

    async def list_services(self):
        """
        List all services
        """
        services = await self.redis_client.get_all_services()
        self._event_bus.emit("list_services")
        return {
            "total": len(services),
            "services": services
        }

    async def get_service(self, service_id: str):
        """
        Get service by id
        """
        self._event_bus.emit("get_service", service_id=service_id)
        return await self.redis_client.get_service(service_id)

    async def create_service(self) -> ServiceModel:
        """
        Create a new service
        """
        service_id = uuid.uuid4().hex
        rooms = RoomManage(service_id)
        rooms.initial()
        service = ServiceModel(
            service_id=service_id,
            token=gen_token(),
            rooms=rooms.json(),
            ice_server=self._ice_servers,
            status=ServerStatus.new,
            create_time=datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            ),
            update_time=datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            ),
        )

        # save service to redis
        await self.redis_client.update_service(service_id, service)
        self._event_bus.emit("create_service", service=service)
        return service

    async def delete_service(self, service_id: str):
        """
        Delete a service by id
        """
        service = await self.get_service(service_id)
        if service is None:
            raise CloudError("service not found", 404)
        self._event_bus.emit("delete_service", service=service)
        await self.redis_client.delete_service(service.service_id)
        return service

    async def get_rooms(self, service_id: str):
        """
        Get rooms by service id
        """
        service = await self.get_service(service_id)
        if service is None:
            raise CloudError("service not found", 404)
        return service.rooms

    async def create_room(self, service_id: str, room: RoomModel):
        """
        Update rooms by service id
        """
        service = await self.get_service(service_id)
        if service is None:
            raise CloudError("service not found", 404)
        rooms = RoomManage(service_id)
        if service.rooms is None:
            rooms.initial()
        else:
            rooms = rooms.update_from_json(service.rooms)
        data = rooms.create_room(
            room_id=room.room_id,
            room_name=room.room_name,
            room_type=room.room_type,
            max_users=room.max_users,
        )
        service.rooms = rooms.json()
        await self.redis_client.update_service(service_id, service)
        self._event_bus.emit("create_room", service=service, room=room)
        return data

    async def get_room(self, service_id: str, room_id: str):
        """
        Get room by service id and room id
        """
        service = await self.get_service(service_id)
        if service is None:
            raise CloudError("service not found", 404)
        rooms = RoomManage(service_id)
        if service.rooms is None:
            rooms.initial()
        else:
            rooms = rooms.update_from_json(service.rooms)

        if str(room_id).isdigit():
            data = rooms.get_room(room_id=int(room_id), room_name=room_id)
        else:
            data = rooms.get_room(room_name=room_id)
        return data

    async def delete_room(self, service_id: str, room_id: str):
        """
        Delete room by service id and room id
        """
        service = await self.get_service(service_id)
        if service is None:
            raise CloudError("service not found", 404)
        rooms = RoomManage(service_id)
        if service.rooms is None:
            rooms.initial()
        else:
            rooms = rooms.update_from_json(service.rooms)
        if str(room_id).isdigit():
            data = rooms.delete_room(room_id=int(room_id), room_name=room_id)
        else:
            data = rooms.delete_room(room_name=room_id)
        service.rooms = rooms.json()
        self._event_bus.emit("delete_room", service=service, room_id=room_id)
        await self.redis_client.update_service(service_id, service)
        return data
