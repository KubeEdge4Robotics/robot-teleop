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

import traceback
from typing import List
from typing import Optional

from redis import asyncio as aioredis
from injector import singleton
from injector import inject

from server.orm.models import ServiceModel
from server.orm.models import RobotModel
from server.orm.models import RoomModel


@singleton
class DataManage:
    """A Redis wrapper class for usage in FastAPI endpoints."""
    CACHE_TTL = 60
    CACHE_SIZE = 1000
    REDIS_PREFIX_SERVICE = 'service:'
    REDIS_PREFIX_ROBOT = 'robot:'
    REDIS_PREFIX_ROOM = 'room:'

    @inject
    def __init__(self):
        self._redis: Optional[aioredis.Redis] = None

    @property
    def redis(self) -> aioredis.Redis:
        """Return wrapped Redis instance."""
        return self._redis

    async def create_redis(self, url: str):
        """create the connection. Use at server startup."""
        if self.redis is not None:
            await self.redis.close()
        try:
            self._redis = await aioredis.from_url(
                url, encoding="utf-8", decode_responses=True
            )
        except: # noqa
            traceback.print_exc()

    async def close_redis(self):
        """Close the connection. Use at server shutdown."""
        await self.redis.close()

    async def get_string(self, key: str, default=None):
        """get a string value in Redis."""
        return (await self.redis.get(key)) or default

    async def set_string(self, key: str, value: str):
        """Set a string value in Redis."""
        await self.redis.set(key, value)

    async def get_service(self, service_id: str) -> Optional[ServiceModel]:
        """Get a service from Redis."""
        data: str = await self.get_string(
            self.REDIS_PREFIX_SERVICE + service_id
        )
        if data is None:
            return
        return ServiceModel.parse_raw(data)

    async def get_robot(self, robot_id: str) -> Optional[RobotModel]:
        """Get a robot from Redis."""
        data: str = await self.get_string(
            self.REDIS_PREFIX_ROBOT + robot_id
        )
        if data is None:
            return
        return RobotModel.parse_raw(data)

    async def get_room(self, room_id: str) -> Optional[RoomModel]:
        """Get a room from Redis."""
        data: str = await self.get_string(
            self.REDIS_PREFIX_ROOM + room_id
        )
        if data is None:
            return
        return RoomModel.parse_raw(data)

    async def update_service(self, service_id: str, data: ServiceModel):
        """Update a service in Redis."""
        await self.set_string(
            self.REDIS_PREFIX_SERVICE + service_id, data.json()
        )

    async def update_robot(self, robot_id: str, data: RobotModel):
        """Update a robot in Redis."""
        await self.set_string(
            self.REDIS_PREFIX_ROBOT + robot_id, data.json()
        )

    async def update_room(self, room_id: str, data: RoomModel):
        """Update a room in Redis."""
        await self.set_string(
            self.REDIS_PREFIX_ROOM + room_id, data.json()
        )

    async def delete_service(self, service_id: str):
        """Delete a service in Redis."""
        await self.redis.delete(self.REDIS_PREFIX_SERVICE + service_id)

    async def delete_robot(self, robot_id: str):
        """Delete a robot in Redis."""
        await self.redis.delete(self.REDIS_PREFIX_ROBOT + robot_id)

    async def delete_room(self, room_id: str):
        """Delete a room in Redis."""
        await self.redis.delete(self.REDIS_PREFIX_ROOM + room_id)

    async def get_all_services(self) -> List[ServiceModel]:
        """Get all services from Redis."""
        keys = await self.redis.keys(self.REDIS_PREFIX_SERVICE + '*')
        services = []
        for data in await self.redis.mget(keys):
            try:
                services.append(ServiceModel.parse_raw(data))
            except:  # noqa
                pass
        return services

    async def get_all_robots(self) -> List[RobotModel]:
        """Get all robots from Redis."""
        keys = await self.redis.keys(self.REDIS_PREFIX_ROBOT + '*')
        robots = []
        for data in await self.redis.mget(keys):
            try:
                robots.append(RobotModel.parse_raw(data))
            except:  # noqa
                pass
        return robots

    async def get_all_rooms(self) -> List[RoomModel]:
        """Get all rooms from Redis."""
        keys = await self.redis.keys(self.REDIS_PREFIX_ROOM + '*')
        rooms = []
        for data in await self.redis.mget(keys):
            try:
                rooms.append(RoomModel.parse_raw(data))
            except:  # noqa
                pass
        return rooms
