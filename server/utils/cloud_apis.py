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
import traceback
from typing import List
from typing import Dict
from datetime import datetime
from datetime import timedelta

import aiohttp
from robosdk.common.config import Config
from robosdk.common.exceptions import CloudError
from robosdk.common.logger import logging
from robosdk.common.fileops import FileOps
from server.orm.models import Architecture

from server.utils.utils import genearteMD5

_CloudAPI = {
    "HuaweiCloud": {
        "iam": "https://iam.{region}.myhuaweicloud.com/v3",
        "oms": "https://oms.{region}.myhuaweicloud.com/v1/{project_id}/robooms",
        "rtc": "https://rtc.{region}.myhuaweicloud.com/v2/{project_id}",
        "obs": "https://obs.{region}.myhuaweicloud.com",
    }
}


class CloudAPIProxy:
    _ENDPOINT_NAME = "IAM_ENDPOINT"
    _DOMAIN_NAME = "IAM_DOMAIN"
    __timeout__ = 10
    __update_token_period__ = 60

    def __init__(self, config: Config, resource: str = ""):
        self.__session__ = aiohttp.ClientSession(
            headers={"Content-Type": "application/json"},
            timeout=aiohttp.ClientTimeout(total=self.__timeout__),
            connector=aiohttp.TCPConnector(verify_ssl=False),
        )
        self.config = config

        if not resource:
            resource = config.get("cloud", "HuaweiCloud")
        if resource not in _CloudAPI:
            raise ValueError(f"Unsupported cloud service: {resource}")
        self._resource = resource
        self.cloud = _CloudAPI[resource]
        self.logger = logging.bind(instance="CloudAPIProxy", system=True)
        self._should_exit = False

    async def run(self):
        raise NotImplementedError

    def update_token(self, token: str = "", project_id: str = "", rtc_token: str = "", rtc_project_id: str = ""):
        raise NotImplementedError

    async def close(self):
        await self.__session__.close()
        self._should_exit = True

    def __str__(self):
        return "CloudAPIProxy"


class CloudAuthProxy(CloudAPIProxy):

    def __init__(self, config: Config, resource: str = ""):
        self.__token__ = None
        self.__project_id__ = None
        self.__token_expires__ = None
        self.__token_lock__ = asyncio.Lock()
        self._all_registry_event: List[CloudAPIProxy] = []
        self._rtc_registry_event: CloudAPIProxy = None
        super(CloudAuthProxy, self).__init__(config, resource)

    def __str__(self):
        return f"{self._resource}.IAM"

    def register_event(self, event: CloudAPIProxy):
        self._all_registry_event.append(event)

    def register_rtc_event(self, event: CloudAPIProxy):
        self._rtc_registry_event = event

    def update_event_token(self):
        for event in self._all_registry_event:
            self.logger.debug(f"Update event token: {event}")
            event.update_token(
                token=self.__token__,
                project_id=self.__project_id__
            )
        self.logger.debug(f"Update rtc event token: {event}")
        self._rtc_registry_event.update_token(
            rtc_token=self.__rtc_token__,
            rtc_project_id=self.__rtc_project_id__
        )

    def update_token(self, token: str = "", project_id: str = "", rtc_token: str = "", rtc_project_id: str = ""):
        """ not recommend to use this method, use _update_token instead """
        if token:
            self.__token__ = token
            self.__token_expires__ = datetime.utcnow() + timedelta(
                seconds=self.__update_token_period__)

        if project_id:
            self.__project_id__ = project_id

        if rtc_token:
            self.__rtc_token__ = rtc_token
            self.__rtc_token_expires__ = datetime.utcnow() + timedelta(
                seconds=self.__update_token_period__)

        if rtc_project_id:
            self.__rtc_project_id__ = rtc_project_id

    @property
    def token(self):
        return self.__token__

    @property
    def rtc_token(self):
        return self.__rtc_token__

    @property
    def project_id(self):
        return self.__project_id__

    async def run(self):
        while 1:
            if self._should_exit:
                break
            async with self.__token_lock__:
                check = await self._update_token()
                if check or (not self.project_id):
                    self.__project_id__ = await self.get_project_id(
                        token=self.token
                    )
                    self.__rtc_project_id__ = await self.get_project_id(
                        token=self.rtc_token
                    )
                    check = True
            if check:
                self.update_event_token()
            await asyncio.sleep(self.__update_token_period__)

    @property
    def server_uri(self) -> str:
        server_uri = self.config.get(self._ENDPOINT_NAME, "").strip()
        region = self.config.get(self._DOMAIN_NAME, "cn-south-1").strip()
        if not server_uri:
            server_uri = self.cloud["iam"]
        return server_uri.format(region=region)

    async def _update_token(self):
        if (
                self.__token__ and self.__token_expires__ and
                datetime.utcnow() < self.__token_expires__
        ):
            return False
        iam_server = self.server_uri
        region = self.config.get(self._DOMAIN_NAME, "cn-south-1").strip()

        name = self.config.get("username", "").strip()
        password = self.config.get("password", "").strip()
        domain = self.config.get("domain", "").strip()
        self.logger.debug(f"Update token by {iam_server} - {name} @ {domain}")
        if not (name and password):
            raise CloudError("username or password not set", 401)

        try:
            self.__token__, self.__token_expires__ = await self.get_token(
                name=name,
                password=password,
                domain=domain,
                project_id=region
            )
        except Exception as e:
            self.logger.debug(traceback.format_exc())
            self.logger.error(f"Update token failed: {e}")

        rtc_name = self.config.get("rtc_username", "").strip()
        rtc_password = self.config.get("rtc_password", "").strip()
        rtc_domain = self.config.get("rtc_domain", "").strip()
        if not (rtc_name and rtc_password):
            raise CloudError("rtc_username or rtc_password not set", 401)
        try:
            self.__rtc_token__, self.__rtc_token_expires__ = await self.get_token(
                name=rtc_name,
                password=rtc_password,
                domain=rtc_domain,
                project_id=region
            )
        except Exception as e:
            self.logger.debug(traceback.format_exc())
            self.logger.error(f"Update rtc_token failed: {e}")

        return True

    async def get_token(
            self, name, password, domain, project_id
    ):
        """ auth with username/password """
        data = {
            "auth": {
                "identity": {
                    "methods": ["password"],
                    "password": {
                        "user": {
                            "name": name,
                            "password": password,
                            "domain": {
                                "name": domain
                            }
                        }
                    }
                },
                "scope": {
                    "project": {
                        "name": project_id,
                    }
                }
            }
        }
        _url = f"{self.server_uri}/auth/tokens"
        resp = await self.__session__.post(
            _url, json=data
        )
        if resp.status != 201:
            _text = await resp.text()
            self.logger.debug(f"Call {_url} fail: {data} => {_text}")
            raise CloudError(f"auth failed, status code", resp.status)
        token = resp.headers.get("X-Subject-Token")
        token_detail = await resp.json()
        token_expires_at = datetime.strptime(
            token_detail['token']['expires_at'],
            "%Y-%m-%dT%H:%M:%S.%fZ"
        )
        return token, token_expires_at

    async def get_project_id(self, token: str = ""):
        """ get project id from huawei cloud api """
        if not token:
            return
        iam_server = self.server_uri
        region = self.config.get(self._DOMAIN_NAME, "cn-south-1").strip()
        _url = f"{iam_server}/projects"
        self.logger.debug(f"Get project id by {_url} - {region}")
        _headers = {
            "Content-Type": "application/json;charset=utf8",
            "X-Auth-Token": token
        }
        data = {
            "enabled": "true",
            "name": region
        }
        resp = await self.__session__.get(
            _url,
            params=data,
            headers=_headers
        )
        if resp.status != 200:
            _text = await resp.text()
            self.logger.debug(f"Call {_url} fail: {data} => {_text}")
            raise CloudError(
                f"auth failed, status code: {resp.status}", resp.status)
        res = await resp.json()
        projects = res.get("projects", [])
        self.logger.debug(f"Get project id by {_url} - {region} - {projects}")
        if len(projects):
            return projects[0].get("id")
        return


class CloudOMSProxy(CloudAPIProxy):
    _page_size = 100
    __update_period__ = 60

    def __init__(
            self,
            config: Config,
            resource: str = "",
            token: str = "",
            project_id: str = "",
            action: str = "roboartisan:roboinstance:create"
    ):
        self._token = token.strip()
        self._project_id = project_id.strip()
        self._ext_header = {
            "Content-Type": "application/json;charset=utf8",
            "X-Auth-Token": self._token
        }
        if action:
            self._ext_header["Action"] = action
        _default_app_arch = config.get(
            "default_app_arch", "arm64"
        ).strip()
        try:
            self.default_app_arch = Architecture(_default_app_arch)
        except ValueError:
            self.default_app_arch = Architecture.amd64
        self._robot_data: List = []
        self._deployment_data: List = []

        self._robot_data_lock = asyncio.Lock()
        self._app_data_lock = asyncio.Lock()
        self._deployment_data_lock = asyncio.Lock()
        self._all_skills_map = {}
        self._all_properties_map = {}
        super(CloudOMSProxy, self).__init__(config, resource)

    def update_token(self, token: str = "", project_id: str = "", rtc_token: str = "", rtc_project_id: str = ""):
        if token:
            self._token = token.strip()
            self._ext_header["X-Auth-Token"] = self._token
        if project_id:
            self._project_id = project_id.strip()

    def __str__(self):
        return f"{self._resource}.OMS"

    @property
    def server_uri(self) -> str:
        server_uri = self.config.get("oms_server_uri", "").strip()
        if not server_uri:
            server_uri = self.cloud["oms"]

        return server_uri.format(
            region=self.config.get(self._DOMAIN_NAME, "cn-south-1").strip(),
            project_id=self._project_id
        ).strip("/")

    async def run(self):
        while 1:
            if self._should_exit:
                break
            if self._token and self._project_id:
                try:
                    async with self._deployment_data_lock:
                        self._deployment_data = await self.get_app_deployment()
                    async with self._robot_data_lock:
                        self._robot_data = await self.get_robots()
                except Exception as e:
                    self.logger.debug(traceback.format_exc())
                    self.logger.error(f"Update oms data failed: {e}")
                await asyncio.sleep(self.__update_period__)
            await asyncio.sleep(1)

    @property
    def robots(self):
        return self._robot_data

    @property
    def num_robots(self):
        return len(self._robot_data)

    @property
    def deployments(self):
        return {d["id"]: d for d in self._deployment_data if "id" in d}

    async def get_robot_skills(
            self,
            robot_id: str = "",
            robot_type: str = ""
    ) -> List:
        """ get robot skills """
        # todo: get robot skills from oms
        if not robot_type:
            robot = await self.get_robot(robot_id)
            robot_type = robot.get("type", "")
        if robot_type in self._all_skills_map:
            return self._all_skills_map[robot_type]
        return []

    async def get_robot_properties(
            self,
            robot_id: str = "",
            robot_type: str = ""
    ) -> Dict:
        """ get robot properties """
        # todo: get robot skills from oms
        if not robot_type:
            robot = await self.get_robot(robot_id)
            robot_type = robot.get("type", "")
        if robot_type in self._all_properties_map:
            return self._all_properties_map[robot_type]
        return {}

    async def get_robots(self, offset: int = 0) -> List:
        """ get all robot """
        url = f"{self.server_uri}/roboinstances"
        data = {
            "limit": int(self._page_size),
            "offset": int(offset),
            "sort_key": "created_at",
            "sort_dir": "desc"
        }
        resp = await self.__session__.get(
            url,
            params=data,
            headers=self._ext_header
        )
        if resp.status != 200:
            _text = await resp.text()
            self.logger.debug(f"Call {url} fail: {data} => {_text}")
            raise CloudError("get oms instance failed", resp.status)
        """
        "roboinstances": [
              {
               "id": "9f4544ef-b990-11ed-a1aa-fa163e93eac6",
               "name": "x20_test",
               "architecture": "amd64",
               "created_at": "2023-03-03T06:57:11Z",
               "status": "Running",
               "hostname": "",
               "image_url": "robot1.png",
               "model": "x20",
               "type": "四足机器人",
               "robomodel_id": "2cfd5251-79f4-11ec-8a73-6805cab16801"
              },
        ],
        "count": 15
        """
        res = await resp.json()
        all_robot = res.get("roboinstances", [])
        count = res.get("count", 0)

        skill_json_file = self.config.get("skill_json_file", "").strip()
        if skill_json_file:
            self._all_skills_map = self._parse_json(skill_json_file)
        property_json_file = self.config.get("property_json_file", "").strip()
        if property_json_file:
            self._all_properties_map = self._parse_json(property_json_file)

        for robot in all_robot:
            robot["skills"] = await self.get_robot_skills(
                robot_id=robot.get("id", ""),
                robot_type=robot.get("type", "")
            )
            properties = await self.get_robot_properties(
                robot_id=robot.get("id", ""),
                robot_type=robot.get("type", "")
            )
            if "properties" not in robot:
                robot["properties"] = {}
            robot["properties"].update(properties)
        if count > offset + self._page_size:
            all_robot.extend(
                await self.get_robots(offset + self._page_size)
            )
        return all_robot

    @staticmethod
    def _parse_json(json_str: str) -> Dict:
        _map = {}
        try:
            _json_file = FileOps.download(json_str)
        except:  # noqa
            _json_file = ""
        if os.path.isfile(_json_file):
            try:
                with open(_json_file) as fin:
                    _map = json.load(fin)
            except:  # noqa
                pass
        return _map

    async def get_robot(self, robot_id: str) -> Dict:
        """ get robot by id """
        url = f"{self.server_uri}/roboinstances/{robot_id}"
        resp = await self.__session__.get(
            url,
            headers=self._ext_header
        )
        if resp.status != 200:
            _text = await resp.text()
            self.logger.debug(f"Call {url} fail: => {_text}")
            raise CloudError("list robot failed", resp.status)
        """
        {
            "id": "9f4544ef-b990-11ed-a1aa-fa163e93eac6",
            "name": "x20_test",
            "architecture": "amd64",
            "created_at": "2023-03-03T06:57:11Z",
            "status": "Running",
            "hostname": "",
            "image_url": "robot1.png",
            "model": "x20",
            "type": "四足机器人",
            "robomodel_id": "2cfd5251-79f4-11ec-8a73-6805cab16801"
        }
        """

        return await resp.json()

    async def get_apps(self, name: str = "", offset: int = 0) -> List:
        """ get all app """
        url = f"{self.server_uri}/roboapps"
        data = {
            "name": name,
            "limit": int(self._page_size),
            "offset": int(offset),
            "sort_key": "created_at",
            "sort_dir": "desc"
        }
        resp = await self.__session__.get(
            url,
            params=data,
            headers=self._ext_header
        )
        if resp.status != 200:
            _text = await resp.text()
            self.logger.debug(f"Call {url} fail: {data} => {_text}")
            raise CloudError("get oms instance failed", resp.status)
        """{
            "roboapps": [
                {
                    "id": "9f4544ef-b990-11ed-a1aa-fa163e93eac6",
                    "name": "x20_test",
                    "release_type": "dev",
                    "package_arch": "amd64",
                    "package_type": "image",
                    "package_url": "",
                    "created_time": "2023-03-03T06:57:11Z",
                    "updated_time": "Running",
                }
            ],
            "page": {
                "count": 1
            }
        }"""
        res = await resp.json()
        all_app = res.get("roboapps", [])
        count = res.get("page", {}).get("count", 0)
        if count > offset + self._page_size:
            all_app.extend(
                await self.get_apps(
                    name=name,
                    offset=offset + self._page_size
                )
            )
        return all_app

    async def get_app(self, app_id: str) -> Dict:
        """ get app by id """
        url = f"{self.server_uri}/roboapps/{app_id}"
        resp = await self.__session__.get(
            url,
            headers=self._ext_header
        )
        if resp.status != 200:
            _text = await resp.text()
            self.logger.debug(f"Call {url} fail: => {_text}")
            raise CloudError("get app failed", resp.status)
        """{
            "id": "9f4544ef-b990-11ed-a1aa-fa163e93eac6",
            "name": "x20_test",
            "release_type": "dev",
            "package_arch": "amd64",
            "package_type": "image",
            "package_url": "",
            "created_time": "2023-03-03T06:57:11Z",
            "updated_time": "Running",
        }"""
        return await resp.json()

    async def create_app(
            self, name: str,
            package_url: str,
            package_type: str = "image",
            package_arch: str = "arm64",
            ros_version: str = "ros1_melodic"
    ) -> str:
        """ create app """
        url = f"{self.server_uri}/roboapps"

        for app in await self.get_apps(name):
            if app.get("name") == name:
                if app.get("package_url") == package_url:
                    return app.get("id")
                await self.delete_app(app.get("id"))

        data = {
            "name": name,
            "package_arch": (package_arch or self.default_app_arch.value),
            "package_url": package_url,
            "package_type": package_type,
            "robo_suite": {
                "ros_version": ros_version
            },
            "tags": {}
        }

        resp = await self.__session__.post(
            url,
            json=data,
            headers=self._ext_header
        )
        if resp.status != 201:
            _text = await resp.text()
            self.logger.debug(f"Call {url} fail: {data} => {_text}")
            raise CloudError("create app failed", resp.status)

        res = await resp.json()
        return res.get("id")

    async def delete_app(self, app_id: str):
        """ delete app """
        url = f"{self.server_uri}/roboapps/{app_id}"
        try:
            await self.__session__.delete(
                url,
                headers=self._ext_header
            )
        except:  # noqa
            self.logger.error("delete app failed", traceback.format_exc())

    async def get_app_versions(self, app_id: str) -> List:
        """ get app versions """
        url = f"{self.server_uri}/roboapps/{app_id}/versions"
        resp = await self.__session__.get(
            url,
            headers=self._ext_header
        )
        if resp.status != 200:
            _text = await resp.text()
            self.logger.debug(f"Call {url} fail: => {_text}")
            raise CloudError("get app versions failed", resp.status)

        res = await resp.json()
        all_versions = res.get("roboapps", [])
        return all_versions

    async def create_app_version(
            self, app_id: str,
            release_type: str = "release",
            release_version: str = "latest",
    ) -> str:
        """ create app version """
        exits_version = await self.get_app_versions(app_id)
        for app_data in exits_version:
            version = app_data.get("release_version", "")
            _type = app_data.get("release_type", "")
            if version != release_version:
                continue
            if _type == release_type:
                return version
            await self.delete_app_version(app_id, version)

        url = f"{self.server_uri}/roboapps/{app_id}/versions"
        data = {
            "release_type": release_type,
            "release_version": release_version
        }

        resp = await self.__session__.post(
            url,
            json=data,
            headers=self._ext_header
        )
        if resp.status != 201:
            _text = await resp.text()
            self.logger.debug(f"Call {url} fail: {data} => {_text}")
            raise CloudError("create app version failed", resp.status)

        return release_version

    async def delete_app_version(self, app_id: str, version: str):
        """ delete app version """
        url = f"{self.server_uri}/roboapps/{app_id}/versions/{version}"
        try:
            await self.__session__.delete(
                url,
                headers=self._ext_header
            )
        except:  # noqa
            self.logger.error(
                "delete app version failed", traceback.format_exc())

    async def get_app_deployment(self, offset: int = 0) -> List:
        """ get app deployment """
        url = f"{self.server_uri}/deployments"

        resp = await self.__session__.get(
            url,
            headers=self._ext_header
        )
        if resp.status != 200:
            _text = await resp.text()
            self.logger.debug(f"Call {url} fail: => {_text}")
            raise CloudError("get app deployment failed", resp.status)
        """{
            "deployment_infos": [
                {
                    "id": "9f4544ef-b990-11ed-a1aa-fa163e93eac6",
                    "name": "x20_test",
                    "robot_id": "",
                    "status": "Running",
                }
            ],
            "count": 2
        }"""
        res = await resp.json()
        # self.logger.debug(f"get app deployment: {res}")
        all_deployment = res.get("deployment_infos", [])
        count = res.get("count", 0)
        if count > offset + self._page_size:
            all_deployment.extend(
                await self.get_app_deployment(
                    offset=offset + self._page_size
                )
            )
        return all_deployment

    async def create_app_deployment(
            self,
            app_id: str,
            robot_id: str,
            version: str = "latest",
            resources=None,
            command: str = "",
            run_args: List = None,
            run_env: Dict = None,
            volumes: List = None,
            additional_properties: str = ""
    ):
        deploy_name = genearteMD5(f"{app_id}_{version}_{robot_id}")

        for deployment in self._deployment_data:
            if deployment.get("name", "") == deploy_name:
                status = deployment.get("status", "")
                self.logger.debug(
                    f"deployment {deploy_name} already exists, {status}"
                )
                await self.delete_app_deployment(deployment.get("id", ""))
        launch_config = {
            "host_network": True,
            "privileged": False,
            "additionalProperties": additional_properties,
        }
        if command:
            launch_config["command"] = command
        if volumes and isinstance(volumes, list):
            launch_config["volumes"] = volumes
        if run_env and isinstance(run_env, dict):
            launch_config["envs"] = run_env
        if run_args and isinstance(run_args, list):
            launch_config["args"] = run_args
        if resources and isinstance(resources, dict):
            r_limits = resources.get("limits", {})
            r_requests = resources.get("requests", {})
            resources = {}
            if r_limits:
                resources["limits"] = r_limits
            if r_requests:
                resources["requests"] = r_requests
            if resources:
                launch_config["resources"] = resources

        url = f"{self.server_uri}/deployments"

        data = {
            "name": deploy_name,
            "robot_id": robot_id,
            "description": "Deploy by teleop server, do not delete it",
            "robot_app_config": {
                "robot_app_id": app_id,
                "version": version,
                "launch_config": launch_config
            }
        }
        resp = await self.__session__.post(
            url,
            json={"deployment": data},
            headers=self._ext_header
        )
        if resp.status != 201:
            _text = await resp.text()
            self.logger.debug(f"Call {url} fail: {data} => {_text}")
            raise CloudError("create app deployment failed", resp.status)
        res = await resp.json()
        return res.get("id", "")

    async def delete_app_deployment(self, deployment_id: str):
        """ delete app deployment """
        url = f"{self.server_uri}/deployments/{deployment_id}"
        try:
            await self.__session__.delete(
                url,
                headers=self._ext_header
            )
            self._deployment_data = await self.get_app_deployment()
        except:  # noqa
            self.logger.error(
                "delete app deployment failed", traceback.format_exc()
            )

    async def get_app_deployment_status(self, deployment_id: str):
        """ get app deployment status """

        url = f"{self.server_uri}/deployments/{deployment_id}"
        resp = await self.__session__.get(
            url,
            headers=self._ext_header
        )
        if resp.status != 200:
            _text = await resp.text()
            self.logger.debug(f"Call {url} fail: => {_text}")
            raise CloudError("get app deployment status failed", resp.status)
        res = await resp.json()
        self.logger.debug(f"get app deployment {deployment_id} status: {res}")
        return res.get("status", "failure")
