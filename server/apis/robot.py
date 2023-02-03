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
import json
import asyncio
import traceback
from typing import Optional
from typing import Dict
from typing import List
from datetime import datetime
from copy import deepcopy

from fastapi.routing import APIRoute
from fastapi import Request
from robosdk.common.exceptions import CloudError

from server.orm.db import DataManage
from server.orm.models import RobotModel
from server.orm.models import ServerStatus
from server.orm.models import ServiceModel
from server.orm.models import RoboSkillModel
from server.orm.models import CameraModel
from server.orm.models import AppModel
from server.orm.models import Architecture
from server.orm.models import RoboAppEnvKey
from server.utils.utils import EventManager
from server.utils.cloud_apis import CloudOMSProxy

from server.apis.__version__ import __version__ as version


class RobotAPI:
    prefix = f"/{version}/robot"

    def __init__(self,
                 redis_client: DataManage,
                 logger,
                 deploy_apps: List[Dict],
                 deploy_app_env: Optional[Dict],
                 oms: CloudOMSProxy
                 ):
        self._event_bus = EventManager()
        self.redis_client: DataManage = redis_client
        self.logger = logger
        self._oms = oms
        self._deploy_apps = deepcopy(deploy_apps)
        self._deploy_app_extra_env = deepcopy(deploy_app_env)

    def initial(self) -> List[APIRoute]:
        # regist router to fastapi
        return [
            APIRoute(
                path=f"{self.prefix}",
                tags=["robot"],
                name="list_robots",
                methods=["GET"],
                summary="List all robots",
                endpoint=self.list_robots,
            ),
            APIRoute(
                path=f"{self.prefix}",
                tags=["robot"],
                name="refresh_robot_list",
                methods=["POST"],
                summary="refresh robot list",
                endpoint=self.refresh_robots,
                response_model=List[RobotModel]
            ),
            APIRoute(
                path=f"{self.prefix}/" + "{robot_id}",
                tags=["robot"],
                name="get_robot",
                methods=["GET"],
                summary="Get robot by id",
                endpoint=self.get_robot,
                response_model=Optional[RobotModel]
            ),
            APIRoute(
                path=f"{self.prefix}/" + "{robot_id}/{service_id}/start",
                tags=["teleop"],
                methods=["POST"],
                name="start_teleop",
                summary="Start teleop service",
                endpoint=self.start_teleop,
                response_model=Optional[ServiceModel]
            ),
            APIRoute(
                path=f"{self.prefix}/" + "{robot_id}/{service_id}/stop",
                tags=["teleop"],
                name="stop_teleop",
                methods=["POST"],
                summary="Stop teleop service",
                endpoint=self.stop_teleop,
                response_model=Optional[ServiceModel]
            ),
        ]

    def _parse_robot_data(
            self, robot: Dict,
            model: Optional[RobotModel] = None
    ) -> Optional[RobotModel]:
        robot_id = robot.get("id", "")
        if not robot_id:
            return
        arch = robot.get("arch", "").lower()
        # only support x86_64 and arm64
        if arch.startswith("arm"):
            arch = Architecture.arm64
        elif arch.startswith("x86"):
            arch = Architecture.arm64
        else:
            arch = self._oms.default_app_arch
        if not isinstance(model, RobotModel):
            model = RobotModel(
                robot_id=robot_id,
                application={},
                service_id="",
                control_id=""
            )
        model.robot_name = robot.get("name", "")
        model.robot_type = robot.get("type", "")
        model.status = robot.get("status", "")
        model.architecture = arch
        model.skills = [
            RoboSkillModel.parse_obj(skill)
            for skill in robot.get("skills", [])
            if skill.get("skill_id", "")
        ]

        properties = robot.get("properties", {})
        cameras = [
            CameraModel.parse_obj(v)
            for k, v in properties.items()
            if str(k).lower().startswith("camera") and v.get("camera_name")
        ]
        model.camera = cameras
        model.pcl_status = properties.get("pcl", {}).get(
            "status", "") or "disconnect"
        model.audio_status = properties.get(
            "audio", {}).get("status", "") or "disconnect"
        return model

    async def refresh_robots(self) -> List[RobotModel]:
        all_robots = []
        exists_robot = []
        _all_robots = await self.redis_client.get_all_robots()
        _all_deploy = self._oms.deployments
        for robot in self._oms.robots:
            # check if robot is in db
            robot_id = robot.get("id", "")
            if not robot_id:
                continue
            model = await self.redis_client.get_robot(robot_id)
            if model is not None:
                exists_robot.append(robot_id)
            model = self._parse_robot_data(robot, model)
            if model.application:
                for app, app_model in model.application.items():
                    if not app_model.app_deploy:
                        continue
                    deploy = _all_deploy.get(app_model.app_deploy, {})
                    status = deploy.get("status", "")
                    if status:
                        app_model.app_status = status
            await self.redis_client.update_robot(robot_id, model)
        # remove robot not in oms
        for robot in _all_robots:
            if robot.robot_id not in exists_robot:
                await self.redis_client.delete_robot(robot.robot_id)
        return all_robots

    async def list_robots(self):
        """
        List all robots
        """
        self._event_bus.emit("list_robots")
        robots = await self.redis_client.get_all_robots()
        if not len(robots):
            for robot in self._oms.robots:
                model = self._parse_robot_data(robot)
                if model is None:
                    continue
                robot_id = model.robot_id
                await self.redis_client.update_robot(robot_id, model)
                robots.append(model)
        count = len(robots)
        return {
            "total": count,
            "robots": robots
        }

    async def get_robot(self, robot_id: str):
        """
        Get robot by id
        """
        self._event_bus.emit("get_robot", robot_id=robot_id)
        robot = await self.redis_client.get_robot(robot_id)
        if robot is None:
            raise CloudError("robot not found", 404)
        return robot

    async def start_teleop(
            self,
            robot_id: str,
            service_id: str,
            request: Request,
    ):
        """
        Start teleop service
        """
        service = await self.redis_client.get_service(service_id)
        robot = await self.redis_client.get_robot(robot_id)
        if not (robot and service):
            raise CloudError("robot or service not found", 404)
        if str(robot.status).lower() != "running":
            raise CloudError("robot status invalid", 400)
        if service.status == ServerStatus.active:
            return service
        if robot.service_id and robot.service_id != service_id:
            old_service = await self.redis_client.get_service(
                robot.service_id
            )
            if old_service:
                old_service.status = ServerStatus.deleted
                old_service.user_id = ""
                await self.redis_client.update_service(
                    robot.service_id,
                    old_service
                )
        if service.user_id and service.user_id != robot.robot_id:
            raise CloudError(
                f"Robot {robot_id} is not owned by service {service_id}",
                status_code=400,
            )
        try:
            post_data = await request.json()
        except:  # noqa
            post_data = {}
        teleop_client = post_data.get("username", "") or "console"
        robot.control_id = teleop_client
        robot.service_id = service_id
        self._event_bus.emit("app_create", service=service, robot=robot)
        await asyncio.sleep(.1)
        robot.application = await self.deploy(robot, service)
        self.logger.debug(f"robot application: {robot.application}")
        await self.redis_client.update_robot(robot_id, robot)
        return service

    async def deploy(
            self,
            robot: RobotModel,
            service: ServiceModel
    ) -> Dict[str, AppModel]:

        service_id = robot.service_id
        if not service:
            return {}
        skills = json.dumps(
            [skill.dict() for skill in robot.skills]
        )
        cameras = json.dumps(
            [camera.dict() for camera in robot.camera]
        )
        app_env = {
            RoboAppEnvKey.service_id.value: service_id,
            RoboAppEnvKey.service_token.value: service.token,
            RoboAppEnvKey.robot_id.value: robot.robot_id,
            RoboAppEnvKey.robot_name.value: robot.robot_name,
            RoboAppEnvKey.robot_type.value: robot.robot_type,
            RoboAppEnvKey.robot_arch.value: robot.architecture.value,
            RoboAppEnvKey.robot_pcl.value: str(robot.pcl_status.value),
            RoboAppEnvKey.robot_audio.value: str(robot.audio_status.value),
            RoboAppEnvKey.robot_skills.value: skills,
            RoboAppEnvKey.robot_cameras.value: cameras,
        }
        if isinstance(self._deploy_app_extra_env, dict):
            app_env.update(self._deploy_app_extra_env)
        deploy = {}

        for app_conf in self._deploy_apps:
            if "name" not in app_conf:
                continue
            if "id" not in app_conf:
                app_conf["id"] = ""
            app = AppModel(
                app_id=(app_conf["id"] or ""),
                app_name=app_conf["name"],
                app_version=app_conf.get("versions", ""),
            )
            for key in ("package_url", "command", "run_args", "app_type",
                        "volumes", "resources", "additional_properties"
                        ):
                if key in app_conf and hasattr(app, key):
                    setattr(app, key, app_conf[key])
            app.run_env = deepcopy(app_env)
            for item in app_conf.get("run_env", []):
                if not isinstance(item, Dict):
                    continue
                key = item.get("name", "")
                value = item.get("value", "")
                if not len(key):
                    continue
                app.run_env[key] = value
            try:
                await self._deploy_app(app, robot)
            except Exception as e:  # noqa
                self.logger.debug(
                    f"Deploy app {app.app_name} error: {traceback.format_exc()}"
                )
            deploy[app.app_name] = app
        service.status = ServerStatus.active
        await self.redis_client.update_service(service_id, service)
        return deploy

    async def stop_teleop(
            self,
            robot_id: str,
            service_id: str,
    ):
        """
        Stop teleop service
        """
        service = await self.redis_client.get_service(service_id)
        robot = await self.redis_client.get_robot(robot_id)
        if not (robot and service):
            raise CloudError("robot or service not found", 404)
        if service.status != ServerStatus.active:
            raise CloudError("Service already stopped", 400)
        if str(robot.status).lower() != "running":
            raise CloudError("robot status invalid", 400)

        if service.user_id and service.user_id != robot.robot_id:
            raise CloudError(
                f"Robot {robot_id} is not owned by service {service_id}",
                status_code=400,
            )
        if robot.application:
            for app, deploy in robot.application.items():
                if not deploy.app_deploy:
                    continue
                await self._oms.delete_app_deployment(deploy.app_deploy)

        service.status = ServerStatus.inactive
        service.update_time = datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )
        await self.redis_client.update_service(service_id, service)
        self._event_bus.emit("app_stop", service=service, robot=robot)
        return service

    async def _deploy_app(self, app: AppModel, robot: RobotModel) -> Dict:
        # deploy app
        self._event_bus.emit("app_deploy", app=app, robot=robot)
        await asyncio.sleep(.1)
        if app.app_id == "":
            # create app
            app.app_id = await self._oms.create_app(
                name=app.app_name,
                package_arch=robot.architecture.value,
                package_url=app.package_url,
            )
        if app.release_type != "release":
            # release app
            app.app_version = await self._oms.create_app_version(
                app_id=app.app_id,
                release_version=(app.app_version or "latest"),
            )

        param = {}
        for key in (
                "command", "run_args", "run_env",
                "volumes", "resources", "additional_properties"
        ):
            value = getattr(app, key, None)
            if value is not None:
                param[key] = value

        deployment_id = await self._oms.create_app_deployment(
            app_id=app.app_id,
            robot_id=robot.robot_id,
            version=(app.app_version or "latest"),
            **param,
        )

        if deployment_id:
            deployment_status = await self._oms.get_app_deployment_status(
                deployment_id
            )
        else:
            deployment_status = "failure"
        app.app_deploy = deployment_id
        app.status = deployment_status
        return {
            "id": app.app_id,
            "version": (app.app_version or "latest"),
            "deploy": deployment_id,
            "status": deployment_status
        }


