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

import time
import asyncio
import traceback
import yaml
from enum import Enum
from typing import List
from typing import Dict
from typing import Optional

from pydantic import BaseModel
from pyee.asyncio import AsyncIOEventEmitter
from robosdk.common.config import Config
from robosdk.common.exceptions import CloudError
from robosdk.common.class_factory import ClassFactory
from robosdk.common.class_factory import ClassType
from robosdk.common.config import BaseConfig
from robosdk.common.logger import logging
from robosdk.cloud_robotics.cloud_base import ServiceBase

from server.utils.utils import HMAC256
from server.utils.utils import genearteMD5
from server.utils.utils import gen_token
from server.utils.cloud_apis import CloudAPIProxy
from server.orm.models import ServiceModel
from server.orm.models import RoomManage
from server.orm.models import RoomModel
from server.orm.models import RobotModel
from server.orm.models import AppModel
from server.orm.models import RoomClient


class RTCRole(Enum):
    """ rtc role """
    Control = "control"
    Robot = "robot"


class RTCClientModel(BaseModel):
    """
    sparkrtc client model
    """
    client_id: str
    client_name: Optional[str]
    client_type: RTCRole
    signature: str
    expire_time: str


class RTCModel(BaseModel):
    """
    sparkrtc model
    """
    room_id: str
    robot_id: str
    app_id: str
    app_key: str
    clients: Dict[str, RTCClientModel]
    domain: Optional[str]


class CloudRTCProxy(CloudAPIProxy):
    _page_size = 100
    __update_period__ = 60

    def __init__(
            self,
            config: Config,
            resource: str = "",
            token: str = "",
            project_id: str = "",
    ):
        self._token = token.strip()
        self._project_id = project_id.strip()
        self._ext_header = {
            "Content-Type": "application/json;charset=utf8",
            "X-Auth-Token": self._token
        }
        self._app_data = []
        self._app_lock = asyncio.Lock()
        super(CloudRTCProxy, self).__init__(config, resource)

    def update_token(self, token: str = "", project_id: str = "", rtc_token: str = "", rtc_project_id: str = ""):
        """ update token """
        if rtc_token:
            self._token = rtc_token.strip()
            self._ext_header["X-Auth-Token"] = self._token
        if rtc_project_id:
            self._project_id = rtc_project_id.strip()

    def __str__(self):
        return f"{self._resource}.RTC"

    async def run(self):
        while 1:
            if self._should_exit:
                break
            if self._token and self._project_id:
                await self.get_all()
                await asyncio.sleep(self.__update_period__)
            await asyncio.sleep(1)

    async def _run(self):
        try:
            async with self._app_lock:
                self._app_data = await self.get_all()
        except Exception as e:
            self.logger.debug(traceback.format_exc())
            self.logger.error(f"Update rtc data failed: {e}")

    @property
    def server_uri(self) -> str:
        server_uri = self.config.get("rtc_server_uri", "").strip()
        if not server_uri:
            server_uri = self.cloud["rtc"]

        return server_uri.format(
            region=self.config.get(self._DOMAIN_NAME, "cn-south-1").strip(),
            project_id=self._project_id
        ).strip("/")

    @property
    def app_data(self) -> List[Dict]:
        return self._app_data

    @property
    def app_num(self) -> int:
        return len(self._app_data)

    async def create(self, name: str) -> Dict:
        """ create rtc app """
        if self.app_num == 0:
            await self._run()
        for app in self._app_data:
            if app.get("app_name") == name:
                state = app.get("state", {}).get("state", "")
                if state.upper() == "ACTIVATION":
                    return app
                await self.delete(app.get("id", ""))

        url = f"{self.server_uri}/apps"
        data = {"app_name": name}

        resp = await self.__session__.post(
            url,
            json=data,
            headers=self._ext_header
        )
        if resp.status != 201:
            _text = await resp.text()
            self.logger.debug(f"Call {url} fail: {data} => {_text}")
            raise CloudError("create rtc app failed", resp.status)
        res = await resp.json()
        app_id = res.get("app_id", "")
        if not app_id:
            raise CloudError("create rtc app failed", resp.status)
        app_info = await self.get(app_id)
        app_key = app_info.get("authentication", {}).get("app_key", "")
        if not app_key:
            raise CloudError("create rtc app failed", resp.status)
        await self._run()
        return app_info

    async def delete(self, app_id: str):
        """ delete rtc app """
        url = f"{self.server_uri}/apps/{app_id}"
        try:
            await self.__session__.delete(
                url,
                headers=self._ext_header
            )
            await self._run()
        except:  # noqa
            self.logger.error(
                "delete rtc app failed", traceback.format_exc()
            )

    async def get(self, app_id: str) -> Dict:
        """ get rtc app """
        url = f"{self.server_uri}/apps/{app_id}"
        resp = await self.__session__.get(
            url,
            headers=self._ext_header
        )
        if resp.status != 200:
            _text = await resp.text()
            self.logger.debug(f"Call {url} fail: => {_text}")
            raise CloudError("get rtc app failed", resp.status)
        res = await resp.json()
        return res

    async def get_all(self, offset: int = 0) -> List[Dict]:
        """ get all rtc app """
        url = f"{self.server_uri}/apps"
        params = {
            "offset": offset,
            "limit": self._page_size
        }
        resp = await self.__session__.get(
            url,
            params=params,
            headers=self._ext_header
        )
        if resp.status != 200:
            _text = await resp.text()
            self.logger.debug(f"Call {url} fail: {params} => {_text}")
            raise CloudError("get rtc app failed", resp.status)
        res = await resp.json()
        count = res.get("count", 0)
        apps = res.get("apps", [])

        if count > offset + self._page_size:
            apps.extend(
                await self.get_all(
                    offset=offset + self._page_size
                )
            )
        return apps

    def get_signature(
            self, app_key: str, app_id: str,
            room_id: str, user_id: str
    ) -> List[str]:

        # get expire ctime
        expire_time = int(
            self.config.get("rtc_signature_expire_time", 7200)
        )
        ctime = str(int(time.time()) + expire_time)

        signature = HMAC256(
            app_key, f"{app_id}+{room_id}+{user_id}+{ctime}"
        )
        return [signature, ctime]


@ClassFactory.register(ClassType.EVENT, "sparkrtc")
class CloudRTC(AsyncIOEventEmitter):

    def __init__(self):
        super(CloudRTC, self).__init__()
        ServiceModel.add_fields(
            sparkrtc=(Optional[RTCModel], None)
        )
        self._config = BaseConfig.DYNAMICS_CONFING
        self.logger = logging.bind(instance="CloudRTCEvent", system=True)
        self._rtc = None
        self._app_env = {}
        self.on("ping", self.on_ping)
        self.on("initial", self.on_start_up)
        self.on("refresh", self.on_refresh)
        self.on("shutdown", self.on_shutdown)
        self.on("delete_service", self.on_service_close)
        self.on("app_create", self.on_app_create)
        self.on("app_deploy", self.on_app_deploy)

    async def on_ping(self):  # noqa
        self.logger.info("pong")

    async def on_start_up(self, server: ServiceBase, **kwargs):  # noqa
        self._rtc = CloudRTCProxy(config=self._config)
        self.logger.debug("CloudRTC init success")

        if hasattr(getattr(server, '_cloud_api', None), "register_rtc_event"):
            try:
                server._cloud_api.register_rtc_event(self._rtc)  # noqa
                self.logger.debug("CloudRTC register event success")
            except:  # noqa
                pass

    async def on_refresh(self):
        if self._rtc is None:
            return
        await self._rtc._run()  # noqa

    async def on_shutdown(self):
        self.logger.debug("CloudRTC shutdown")
        if self._rtc is None:
            return
        await self._rtc.close()

    async def on_service_close(self, service: ServiceModel, **kwargs):  # noqa
        self.logger.debug("CloudRTC service close")
        if self._rtc is None:
            return
        if not hasattr(service, "sparkrtc"):
            return
        app_id = getattr(getattr(service, "sparkrtc", None), "app_id", None)
        if app_id:
            await self._rtc.delete(app_id)
        if app_id in self._app_env:
            del self._app_env[app_id]
        setattr(service, "sparkrtc", None)

    async def on_app_create(self,
                            service: ServiceModel,
                            robot: RobotModel,
                            **kwargs  # noqa
                            ):
        self.logger.debug("CloudRTC app create")
        service_id = service.service_id
        rooms = RoomManage(service_id)
        if service.rooms is None:
            rooms.initial()
        else:
            rooms.update_from_json(service.rooms)
        rtc_ = list(
            filter(lambda x: x.room_type == "cloud_rtc",
                   rooms.rooms.values())
        )
        room: RoomModel = rtc_[0] if len(rtc_) else rooms.create_room(
            room_name="rtc",
            room_type="cloud_rtc",
        )
        self._app_env[robot.robot_id] = {

            "rooms": rooms,
            "robot": robot,
            "room": room,
            "service": service
        }
        rtc: Optional[RTCModel] = await self._new_rtc_model(
            robot_id=robot.robot_id,
            teleop_client=robot.control_id,
        )
        setattr(service, "sparkrtc", rtc)
        self._app_env[robot.robot_id]["rtc"] = rtc
        self.logger.debug(f"CloudRTC app {rtc} create")
    
    async def on_app_deploy(self, app: AppModel, robot: RobotModel, **kwargs):
        self.logger.debug(f"CloudRTC app {app} deploy")
        if not (robot.robot_id in self._app_env and app.app_type == "sparkrtc"):
            return
        if not (app.run_env and isinstance(app.run_env, dict)):
            app.run_env = {}

        mode = app.run_env.get("mode", "p2p")  # p2p / mutil
        token: str = gen_token()
        rtc: RTCModel = self._app_env[robot.robot_id]["rtc"]
        expire_time = ""
        if mode == "mutil":
            agent_num = int(app.run_env.get("agent_num", 1))
            stream = []
            for i in range(agent_num):
                client_id = app.run_env.get(f"stream_{i}_id", "")
                client_name = (app.run_env.get(f"stream_{i}_name", "")
                               or f"{robot.robot_name}_{i}")
                ros_topic = app.run_env.get(
                    f"stream_{i}_ros_topic", "/camera/color/image_raw"
                )
                if not client_id:
                    client_id = genearteMD5(ros_topic)
                if client_id in rtc.clients:
                    client_id = f"{client_id}_{token}"
                    client_name = f"{client_name}_{token}"
                client = self._add_single_client(
                    robot=robot,
                    client_id=client_id,
                    client_name=client_name,
                )
                stream.append(
                    {
                        "stream_id": client_id,
                        "stream_name": client_name,
                        "ros_image_topic": ros_topic,
                        "signature": client.signature,
                        "rtc_ctime": client.expire_time,
                        "client_type": "robot"
                    }
                )
                expire_time = client.expire_time
            run_env = {
                "device_id": rtc.room_id,
                "app_id": rtc.app_id,
                "app_key": rtc.app_key,
                "domain": rtc.domain,
                "ctime": expire_time,
                "streams": stream,
            }
            if not app.volumes:
                app.volumes = []
            app.volumes = list(
                filter(lambda x: x["name"] != "sparkrtconf", app.volumes)
            )
            app.volumes.append(
                {
                    "name": "sparkrtconf",
                    "type": "configMap",
                    "source": "sparkrtc-config",
                    "destination": "/home/cameraagent/share/robocamera_agent/config",  # noqa
                    "data": {
                        "config.yaml": yaml.dump(run_env)
                    }
                }
            )

        else:
            if "stream_id" in app.run_env:
                client_id = app.run_env["stream_id"]
            else:
                client_id = kwargs.get("client_id", "")
            if not client_id:
                client_id = genearteMD5(
                    app.run_env.get(
                        "ros_image_topic", "/camera/color/image_raw"
                    )
                )

            if "stream_name" in app.run_env:
                client_name = app.run_env["stream_name"]
            else:
                client_name = (
                        kwargs.get("client_name", "") or robot.robot_name
                )
            if client_id in rtc.clients:
                client_id = f"{client_id}_{token}"
                client_name = f"{client_name}_{token}"

            client = self._add_single_client(
                robot=robot,
                client_id=client_id,
                client_name=client_name,
            )
            run_env = {
                "device_id": rtc.room_id,
                "rtc_app_id": rtc.app_id,
                "stream_id": client_id,
                "stream_name": client_name,
                "signature": client.signature,
                "rtc_app_key": rtc.app_key,
                "rtc_domain": rtc.domain,
                "rtc_ctime": client.expire_time
            }
            app.run_env.update(run_env)

    def _add_single_client(self, robot: RobotModel, client_id: str, client_name: str):
        rtc: RTCModel = self._app_env[robot.robot_id]["rtc"]
        rooms: RoomManage = self._app_env[robot.robot_id]["rooms"]
        room: RoomModel = self._app_env[robot.robot_id]["room"]
        service: ServiceModel = self._app_env[robot.robot_id]["service"]

        rooms.join_room(
            room,
            RoomClient(
                client_id=client_id,
                client_name=client_name,
                client_type="publisher",
                client_role=RTCRole.Robot.value,
            )
        )
        signature, expire_time = self._rtc.get_signature(
            app_key=rtc.app_key,
            app_id=rtc.app_id,
            room_id=rtc.room_id,
            user_id=client_id,
        )
        client = RTCClientModel(
            client_id=client_id,
            client_name=client_name,
            client_type=RTCRole.Robot,
            signature=signature,
            expire_time=expire_time
        )
        rtc.clients[client_id] = client

        service.rooms = rooms.json()
        return client

    async def _new_rtc_model(
            self,
            robot_id: str = "",
            teleop_client: str = "",
            teleop_name: str = "console",
    ) -> Optional[RTCModel]:
        if self._rtc is None:
            return
        rooms: RoomManage = self._app_env[robot_id]["rooms"]
        room: RoomModel = self._app_env[robot_id]["room"]
        service: ServiceModel = self._app_env[robot_id]["service"]

        rtc_app_name = genearteMD5(f"{room.room_name}-{robot_id}")
        rtc_info = await self._rtc.create(
            name=rtc_app_name,
        )
        app_key = rtc_info.get("authentication", {}).get("app_key", "")
        app_id = rtc_info.get("app_id", "")
        app_name = rtc_info.get("app_name", "")
        app_domain = rtc_info.get("domain", "")

        if not teleop_client:
            teleop_client = robot_id
        if not teleop_name:
            teleop_name = teleop_client
        signature, expire_time = self._rtc.get_signature(
            app_key=app_key, app_id=app_id,
            room_id=room.room_name,
            user_id=teleop_client
        )
        client = RTCClientModel(
            client_id=teleop_client,
            client_name=teleop_name,
            client_type=RTCRole.Control,
            signature=signature,
            expire_time=expire_time
        )
        rooms.join_room(
            room,
            RoomClient(
                client_id=teleop_client,
                client_name=teleop_name,
                client_type="subscriber",
                client_role=RTCRole.Control.value,
            )
        )
        rtc = RTCModel(
            app_id=app_id,
            robot_id=robot_id,
            app_name=app_name,
            app_key=app_key,
            clients={client.client_id: client},
            room_id=room.room_name,
            domain=app_domain
        )
        service.rooms = rooms.json()
        return rtc
