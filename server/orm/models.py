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
from enum import Enum
from typing import Optional
from typing import Dict
from typing import List
from typing import Any

from pydantic import BaseModel
from pydantic.fields import ModelField


class RoboAppEnvKey(Enum):
    """
    robot app env key
    """
    server_url = 'TELEOP_SERVER_URL'
    service_id = 'TELEOP_SERVER_ID'
    service_token = "TELEOP_SERVER_TOKEN"
    robot_id = "TELEOP_ROBOT_ID"
    robot_name = "TELEOP_ROBOT_NAME"
    robot_type = "TELEOP_ROBOT_TYPE"
    robot_arch = "TELEOP_ROBOT_ARCH"
    robot_pcl = "TELEOP_ROBOT_PCL"
    robot_audio = "TELEOP_ROBOT_AUDIO"
    robot_skills = "TELEOP_ROBOT_SKILLS"
    robot_cameras = "TELEOP_ROBOT_CAMERAS"


class ServerStatus(str, Enum):
    """
    server status
    """
    new = 'new'
    active = 'active'
    inactive = 'inactive'
    deleted = 'deleted'


class DeviceStatus(str, Enum):
    """
    device status
    """
    connect = 'connect'
    disconnect = 'disconnect'
    unknown = 'unknown'


class Architecture(str, Enum):
    """
    device architecture
    """
    arm64 = 'arm64'
    amd64 = 'x86_64'
    unknown = 'unknown'


class ICEServerModel(BaseModel):
    """
    ICE server model
    """
    urls: str
    username: Optional[str]
    password: Optional[str]
    credential: Optional[str]


class AppModel(BaseModel):
    """
    app model
    """
    app_id: str
    app_name: str
    app_deploy: Optional[str]
    app_type: Optional[str]
    app_version: Optional[str]
    package_url: Optional[str]
    release_type: Optional[str]
    status: Optional[str]
    description: Optional[str]
    message: Optional[str]
    command: Optional[str]
    run_args: Optional[List]
    run_env: Optional[Dict]
    volumes: Optional[List]
    resources: Optional[Dict]
    additional_properties: Optional[str]


class ServiceModel(BaseModel):
    """
    teleop service model
    """
    service_id: str
    token: Optional[str]
    user_id: Optional[str]  # robot ID
    # sparkrtc: Optional[RTCModel]
    ice_server: ICEServerModel
    rooms: Optional[Dict]
    status: ServerStatus
    create_time: str
    update_time: str

    @classmethod
    def add_fields(cls, **field_definitions: Any):
        new_fields: Dict[str, ModelField] = {}
        new_annotations: Dict[str, Optional[type]] = {}

        for f_name, f_def in field_definitions.items():
            if isinstance(f_def, tuple):
                try:
                    f_annotation, f_value = f_def
                except ValueError as e:
                    raise Exception(
                        'field definitions should either be a tuple '
                        'of (<type>, <default>) or just a default value, '
                        'unfortunately this means tuples as '
                        'default values are not allowed'
                    ) from e
            else:
                f_annotation, f_value = None, f_def

            if f_annotation:
                new_annotations[f_name] = f_annotation

            new_fields[f_name] = ModelField.infer(name=f_name, value=f_value,
                                                  annotation=f_annotation,
                                                  class_validators=None,
                                                  config=cls.__config__)

        cls.__fields__.update(new_fields)
        cls.__annotations__.update(new_annotations)


class RoboSkillModel(BaseModel):
    """
    robot skill model
    """
    skill_id: str
    skill_name: str
    skill_type: Optional[str]
    version: Optional[str]
    description: Optional[str]
    parameters: Optional[Dict]


class CameraModel(BaseModel):
    """
    camera model
    """
    camera_name: str
    camera_type: Optional[str]
    camera_url: Optional[str]
    camera_status: Optional[DeviceStatus]


class RobotModel(BaseModel):
    """
    robot model
    """
    robot_id: str
    service_id: Optional[str]
    robot_name: Optional[str]
    robot_type: Optional[str]
    camera: Optional[List[CameraModel]]
    skills: Optional[List[RoboSkillModel]]
    status: Optional[str]
    pcl_status: Optional[DeviceStatus] = DeviceStatus.connect
    audio_status: Optional[DeviceStatus] = DeviceStatus.connect
    control_id: Optional[str]
    architecture: Optional[Architecture] = Architecture.arm64
    application: Optional[Dict[str, AppModel]]


class RoomModel(BaseModel):
    """
    room model
    """
    room_id: Optional[int]
    room_alias: Optional[str]
    room_name: Optional[str]
    room_type: Optional[str]  # text or video
    service_id: Optional[str]
    max_users: Optional[int]
    participants: Optional[int]
    participants_list: Optional[list]


class RoomClient(BaseModel):
    """
    room client model
    """
    client_id: str
    client_name: str
    client_type: str  # publisher or subscriber
    client_role: Optional[str]  # robot or console


class RoomManage:
    max_users = 6

    def __init__(self, service_id: str, base_num: int = 1000):
        self.service_id = service_id
        self.rooms: Dict[str, RoomModel] = {}  # {room_name: RoomModel}
        self.base_num = base_num
        self.participants: Dict[str, Dict] = {}

    @property
    def participant_number(self):
        return len(self.participants)

    def json(self) -> Dict:
        return {
            "service_id": self.service_id,
            "rooms": {
                room_name: room.json()
                for room_name, room in self.rooms.items()
            },
            "base_num": self.base_num
        }

    def update_from_json(self, raw):
        if isinstance(raw, str):
            try:
                raw = json.loads(raw)
            except: # noqa
                return
        if raw.get("service_id"):
            self.service_id = raw.get("service_id")
        if isinstance(raw.get("rooms"), Dict):
            for room_name, room in raw.get("rooms").items():
                self.rooms[room_name] = RoomModel.parse_raw(room)
        base_num = raw.get("base_num") or self.base_num
        if str(base_num).isdigit():
            self.base_num = int(base_num)

    def update_base_num(self, base_num: int):
        self.base_num = base_num

    def initial(self):
        raw = [
            ["live_stream", "Camera", "cloud_rtc"],
            ["top_camera", "Front UP", "video"],
            ["bottom_camera", "Front Down", "video"],
            ["map", "Map", "video"],
            ["conference", "VideoConf", "local_rtc"],
            ["point_cloud", "PointCloud", "binary"],
            ["Teleop", "Teleop", "text"],
            ["other", "Other", "text"],
        ]
        for inx, item in enumerate(raw):
            self.rooms[item[0]] = RoomModel(
                room_id=self.base_num + inx,
                room_name=item[0],
                room_alias=item[1],
                room_type=item[2],
                service_id=self.service_id,
                max_users=self.max_users,
                participants=0,
                participants_list=[],
            )
        self.base_num += len(raw)

    def get_room(self, room_name: str = None, room_id: int = None):
        if room_id:
            rtc_room = self.get_room_by_id(room_id)
        else:
            rtc_room = self.get_room_by_name(room_name)
        return rtc_room

    def get_room_by_id(self, room_id: int):
        for room in self.rooms.values():
            if room.room_id == room_id:
                return room
        return

    def get_room_by_name(self, room_name):
        return self.rooms.get(room_name) or self.get_room_by_alias(room_name)

    def get_room_by_alias(self, room_alias):
        for room in self.rooms.values():
            if room.room_alias == room_alias:
                return room
        return

    def create_room(
            self,
            room_name: str, room_type: str,
            max_users: int = 6,
            room_id: int = None
    ):
        # check if room exists
        if self.get_room(room_name=room_name, room_id=room_id):
            return self.get_room(room_name=room_name, room_id=room_id)
        self.base_num += 1
        if not room_id:
            room_id = self.base_num
        self.rooms[room_name] = RoomModel(
            id=room_id,
            room_name=room_name,
            room_type=room_type,
            max_users=max_users,
            participants=0,
            participants_list=[],
        )
        return self.rooms[room_name]

    def delete_room(self, room_name: str = None, room_id: int = None):
        r = None
        for key, room in self.rooms.items():
            if room.room_name == room_name or str(room.room_id) == str(room_id):
                r = key
                break

        if r:
            del self.rooms[r]
        return r

    def join_room(self, room: RoomModel, client: RoomClient):
        if room.participants >= room.max_users:
            raise AttributeError(f"Room {room.room_name} is full")
        participants_list = [
            c for c in room.participants_list
            if c.client_name != client.client_name
        ]
        participants_list.append(client)
        if client.client_id not in self.participants:
            self.participants[client.client_id] = {}
        self.participants[client.client_id][room.room_name] = client
        room.participants_list = participants_list
        room.participants = len(participants_list)

    def leave_room(self, room: RoomModel, client_id: str):
        rooms = self.participants.get(client_id, {})
        if room.room_name not in rooms:
            return
        client = rooms[room.room_name]
        room.participants_list = [
            c for c in room.participants_list
            if c.client_name != client.client_name
        ]
        room.participants = len(room.participants_list)
        del self.participants[client_id][room.room_name]

    def kcick(self, client_id: str):
        if client_id not in self.participants:
            return
        all_rooms = list(self.participants[client_id].keys())
        for room_name in all_rooms:
            room = self.get_room_by_name(room_name)
            if room is not None:
                self.leave_room(room, client_id)
        del self.participants[client_id]

    def get_room_of_client(self, client_id: str) -> Dict:
        return self.participants.get(client_id, {})
