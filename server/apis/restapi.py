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
import os
import json
import asyncio
from typing import Dict
from typing import Optional
from typing import List
from signal import SIGINT
from signal import SIGTERM
from importlib import import_module

import uvicorn
import socketio
from fastapi import FastAPI
from fastapi.routing import APIRoute
from robosdk.common.config import BaseConfig
from robosdk.common.exceptions import CloudError
from robosdk.utils.util import parse_kwargs
from starlette.responses import FileResponse
from robosdk.cloud_robotics.cloud_base import ServiceBase

from server.orm.db import DataManage
from server.orm.models import ServerStatus
from server.orm.models import RoboAppEnvKey
from server.orm.models import ICEServerModel
from server.utils.cloud_apis import CloudAuthProxy
from server.utils.cloud_apis import CloudOMSProxy
from server.utils.utils import EventManager
from server.apis.service import ServerAPI
from server.apis.robot import RobotAPI
from server.apis.ws import WebRTCGatewayWSServer
from server.apis.middleware import RequestMiddleware
from server.apis.middleware import catch_exceptions_middleware
from server.apis.__version__ import __version__ as version


class SignalGatewayAPI(ServiceBase):  # noqa
    api_secret_name = "apisecret"
    __refresh_period__ = 10
    _config = BaseConfig.DYNAMICS_CONFING

    def __init__(self,
                 name: str = "control",
                 host: str = "0.0.0.0",
                 port: int = 5540,
                 loop: Optional[asyncio.AbstractEventLoop] = None
                 ):
        """
        :param name: name of the server
        :param host: host of the server
        :param port: port of the server
        :param loop: asyncio loop
        """

        static_folder = self._config.get("server_static_folder", "")
        super(SignalGatewayAPI, self).__init__(
            name=name, host=host, port=port, static_folder=static_folder
        )
        if loop is None:
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = asyncio.get_event_loop()
        self.loop = loop
        self.redis_client = DataManage()

        self._cloud_api = CloudAuthProxy(
            config=self._config
        )
        self._oms_api = CloudOMSProxy(
            config=self._config
        )
        ice_server = None
        ice_servers_file = self._config.get("ice_servers_url", "").strip()
        if os.path.isfile(ice_servers_file):
            try:
                with open(ice_servers_file) as fin:
                    ice_server = ICEServerModel.parse_raw(fin.read())
            except:  # noqa
                pass
        elif ice_servers_file.startswith(("stun:", "turn:")):
            ice_server = ICEServerModel(urls=ice_servers_file)
        if ice_server is None:
            ice_server = ICEServerModel(
                urls="stun:stun.l.google.com:19302"
            )

        self._cloud_api.register_event(self._oms_api)
        self.server_manage = ServerAPI(
            self.redis_client,
            self.logger,
            ice_servers=ice_server,
        )
        deploy_apps = self._config.get("deploy_apps", [])
        apisecret = self._config.get(self.api_secret_name, "").strip()
        teleop_server_url = self._config.get("teleop_server_url", "").strip()
        event_bus_def = self._config.get("teleop_server_event", "")
        self._event_bus = EventManager()
        if event_bus_def:
            self.register_event(event_bus_def)
        deploy_app_env = {}
        if apisecret:
            deploy_app_env[self.api_secret_name] = apisecret
        if teleop_server_url:
            deploy_app_env[RoboAppEnvKey.server_url.value] = teleop_server_url

        self.robot_manage = RobotAPI(
            self.redis_client,
            self.logger,
            deploy_apps=deploy_apps,
            deploy_app_env=deploy_app_env,
            oms=self._oms_api,
        )

        self._ws_server = WebRTCGatewayWSServer(
            logger=self.logger,
            redis_client=self.redis_client,
        )
        self.server = None

    def register_event(self, event_bus_def: str):
        if not os.path.isfile(event_bus_def):
            return
        with open(event_bus_def, "r") as f:
            try:
                event_bus = json.load(f, encoding="utf-8")
            except Exception as e:
                self.logger.error(f"Load event bus error: {e}")
                return
        if not isinstance(event_bus, List):
            return
        for event in event_bus:
            if not isinstance(event, Dict):
                continue
            event_name = event.get("name", "")
            event_package = event.get("package", "")
            if not event_name:
                continue
            if event_package:
                try:
                    _ = import_module(event_package)
                except Exception as e:
                    self.logger.error(f"Import event package error: {e}")
                    continue
            self._event_bus.register(event_name)

    async def get_download_urls(self, filename: str) -> FileResponse:
        # 去除目录遍历漏洞
        filename = filename.replace("../", "")
        if not filename:
            raise CloudError(
                status_code=404,
                message=json.dumps(
                    {
                        "code": 404,
                        "message": "filename is empty"
                    }
                )
            )
        if len(self._static_folder):
            for _p in self._static_folder:
                if os.path.isfile(os.path.join(_p, filename)):
                    return FileResponse(
                        os.path.join(_p, filename),
                        media_type="application/octet-stream",
                        filename=os.path.basename(filename)
                    )
        raise CloudError(
            status_code=404,
            message=json.dumps(
                {
                    "code": 404,
                    "message": "file not found"
                }
            )
        )

    def initial(self, **kwargs):
        if self.server is not None:
            return
        rounters: List[APIRoute] = [
            APIRoute(
                f"/{version}/{self.name}",
                self.get_all_urls
            ),
            APIRoute(
                f"/{version}/{self.name}/download",
                self.get_download_urls
            )
        ]
        rounters.extend(self.server_manage.initial())
        rounters.extend(self.robot_manage.initial())
        self._event_bus.emit("initial", server=self)
        self.app = FastAPI(
            title=self.name,
            debug=True,
            description="WebRTC Gateway Server",
            version=version,
            on_startup=[self._on_startup],
            on_shutdown=[self._on_shutdown],
            routes=rounters,
        )

        self.app.add_middleware(
            RequestMiddleware,
            auth_token=self._config.get(self.api_secret_name, "").strip(),
            redis_client=self.redis_client
        )
        self.app.middleware('http')(catch_exceptions_middleware)
        if not hasattr(self.app, "mount"):
            self.logger.error("The version of fastapi is too low")
            return

        _app = socketio.ASGIApp(socketio_server=self._ws_server.sio)

        self.app.mount(
            f"/{version}/service" + "/{service_id}", _app,  # noqa
            name="socketio"
        )

        all_k: Dict = parse_kwargs(uvicorn.Config, **kwargs)
        all_k.update(dict(
            app=self.app,
            host=self.host,
            port=self.port,
            ssl_keyfile=self.use_ssl["key"],
            ssl_certfile=self.use_ssl["cert"],
            log_level=BaseConfig.CLOUD_SERVERS_LOG_LEV
        ))
        self.server = uvicorn.Server(config=uvicorn.Config(**all_k))

    async def _on_startup(self):
        await self.redis_client.create_redis(
            self._config.get("redis_url", "redis://localhost").strip()
        )
        self.app.state.redis = self.redis_client

    async def _on_shutdown(self):
        self.logger.debug("Server shutdown")
        if self.app.state.redis is not None:
            try:
                await self.app.state.redis.close()
            except:  # noqa
                pass
        self._event_bus.emit("shutdown")

    async def _update_robot(self):
        while 1:
            if self.redis_client.redis is None:
                await asyncio.sleep(1)
                continue
            all_service = await self.redis_client.get_all_services()
            await self.robot_manage.refresh_robots()
            self._event_bus.emit("refresh")
            for service in all_service:
                if service.status == ServerStatus.deleted:
                    await self.redis_client.delete_service(
                        service.service_id
                    )

            await asyncio.sleep(self.__refresh_period__)

    def run(self, **kwargs):
        self.logger.debug("Server startup")
        self.initial(**kwargs)
        _async_tasks = [
            asyncio.ensure_future(self.server.serve(), loop=self.loop),
            asyncio.ensure_future(self._update_robot(), loop=self.loop),
            asyncio.ensure_future(self._ws_server.run(), loop=self.loop),
            asyncio.ensure_future(self._cloud_api.run(), loop=self.loop),
            asyncio.ensure_future(self._oms_api.run(), loop=self.loop),
        ]
        self._event_bus.emit("start_up", server=self)
        for task in _async_tasks:
            for signal in [SIGINT, SIGTERM]:
                self.loop.add_signal_handler(signal, task.cancel)
        self.logger.info("Startup complete.")
        self.loop.run_forever()
