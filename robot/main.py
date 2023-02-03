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
from typing import (
    Dict,
    List
)
from datetime import datetime

import numpy as np
from robosdk.core import Robot
from robosdk.cloud_robotics.skills import SkillBase
from robosdk.utils.util import EnvBaseContext
from robosdk.common.robot_status import RobotStatus
from robosdk.common.constant import RoboControlMode
from robosdk.common.schema.pose import BasePose
from robosdk.common.schema.map import PgmMap
from robosdk.common.constant import GaitType
from robosdk.utils.util import parse_kwargs
from robosdk.algorithms.perception.mapping.visual import RosMapVisual

from signalingClient.webrtc import ControlRTCRobot
from signalingClient.models import ICEServerModel


class DanceSkill(SkillBase):  # noqa
    def __init__(self, robot):
        super(DanceSkill, self).__init__(name="Dance", robot=robot)

    def call(self):
        if not hasattr(self.robot, "motion"):
            self.logger.error("Robot has no motion module")
            return
        # -> -> <- <- ↑ ↓ ↑ ↓
        self.robot.motion.turn_left()
        self.robot.motion.turn_left()
        self.robot.motion.turn_right()
        self.robot.motion.turn_right()
        self.robot.motion.go_forward()
        self.robot.motion.go_backward()
        self.robot.motion.go_forward()
        self.robot.motion.go_backward()


class RoboClient:
    api_secret_name = "apisecret"
    skill_parameters = {
        "capture_photo": {"output": "/share/data/capture.png"}
    }

    def __init__(self, name="teleop", config="teleop"):
        self.robot = Robot(name=name, config=config)

        uri = EnvBaseContext.get(
            "TELEOP_SERVER_URL",
            "http://127.0.0.1:5540/teleoperation"
        ).strip("/")
        server_id = EnvBaseContext.get("TELEOP_SERVER_ID", "teleop")
        token = EnvBaseContext.get("TELEOP_SERVER_TOKEN", "")
        ice_server = None
        ice_servers_file = EnvBaseContext.get(
            "RTC_ICE_SERVER", ""
        ).strip()
        if os.path.isfile(ice_servers_file):
            try:
                with open(ice_servers_file, "r") as fin:
                    ice_server = ICEServerModel.parse_raw(fin.read())
            except Exception as e:
                pass
        if not ice_server:
            ice_server = ICEServerModel(
                urls="stun:stun.l.google.com:19302"
            )
        auth_token: str = EnvBaseContext.get(self.api_secret_name, "").strip()
        uri = f"{uri}/{server_id}"
        query = []
        if token:
            query.append(f"token={token}")
        if auth_token:
            query.append(f"x-auth-token={auth_token}")
        if query:
            uri = f"{uri}?{'&'.join(query)}"
        self.client = ControlRTCRobot(
            robot=self.robot,
            ice_servers=ice_server,
            name="teleoperation",
            uri=uri
        )
        self._robot_status = RobotStatus(timer=.5)
        self.robot.connect()
        self.client.connect()

        self.map_view = None
        self.maps = None
        self.scaling_factor = [1, 1]
        self.show_laser = True
        if getattr(self.robot, "voice", None) is not None:
            self.client.add_worker(
                name_space="VideoConf",
                kind="remote",
                data_func=self.async_get_remote_voice,
                video_enable=False,
            )
        cam_num = len(self.robot.all_sensors.get("camera", []))
        if cam_num:
            self.client.add_worker(
                name_space="top_camera",
                kind="stream",
                data_func=self.async_send_front,
            )
        if cam_num > 1:
            self.client.add_worker(
                name_space="bottom_camera",
                kind="stream",
                data_func=self.async_send_hand,
            )

        if "odom" in self.robot.all_sensors:
            self.map_view = RosMapVisual(logger=self.robot.logger)
            self.client.add_worker(
                name_space="map",
                kind="stream",
                data_func=self.async_send_maps,
                audio_enable=True,
            )

        self.client.add_worker(
            name_space="Teleop",
            data_func=self.async_send_status,
            message_callback=self.command_callback
        )

    def run(self):
        self.robot.skill_register("dance", DanceSkill)
        self._robot_status.start()
        self.client.run()

    def async_send_maps(self) -> List:
        maps, _ = self.robot.maps.get_data()  # noqa
        if not isinstance(maps, PgmMap):
            return [None, None]
        self.maps = maps
        self.map_view.initial_map(maps)

        self.scaling_factor = [
            1000.0 / maps.map_data.shape[1],
            1000.0 / maps.map_data.shape[0]
        ]

        curr_p: BasePose = self.robot.odom.get_curr_state()  # noqa
        self.map_view.add_robot(curr_p)

        if self.show_laser:
            laser, _ = self.robot.lidar.get_points()  # noqa
            scan = self.robot.odom.quat2mat(laser)  # noqa
            self.map_view.add_laser(scan)

        if hasattr(self.robot, "voice"):
            voice, _ = self.robot.voice.get_data()
        else:
            voice = None
        return [self.map_view.curr_frame, voice]

    def async_get_remote_voice(self, audio: np.ndarray):
        self.robot.logger.debug(f"get audio => {audio}")
        try:
            self.robot.voice.say(audio)
        except Exception as e:
            self.robot.logger.error(f"say error => {e}")

    def async_send_front(self) -> np.ndarray:
        frame, _ = self.robot.all_sensors["camera"]["camera_front"].get_rgb()
        return frame

    def async_send_hand(self) -> np.ndarray:
        frame, _ = self.robot.all_sensors["camera"]["camera_arm"].get_rgb()
        return frame

    def async_send_status(self) -> Dict:
        status = dict(self._robot_status.data)

        if hasattr(self.robot, "battery") and hasattr(self.robot.battery,
                                                      "battery"):
            battery = self.robot.battery.battery
            status["isCharging"] = battery.get("isCharging", "") or False
            for k in ("batteryCurrent", "battery",
                      "batteryVoltage", "batteryLevel"):
                status["battery"] = battery.get(k, .0)
        curr_gait = GaitType.UNKONWN
        if hasattr(self.robot, "legged"):
            try:
                curr_gait = self.robot.legged.get_curr_gait()
            except Exception as e:  # noqa
                self.robot.logger.error(f"get curr gait error: {e}")
        status["gaitType"] = curr_gait.value
        return {
            'type': 'robotStatus',
            'status': status,
            'timestamp': datetime.now().timestamp()
        }

    def _command_execute_action(self, msg: Dict):
        cmd = msg.get("cmd", "skill")
        action = msg.get("action", "")
        if not len(action):
            self.robot.logger.warning(f"get {msg}, unknown command")
        if cmd == "skill":
            if not hasattr(self.robot.skill, action):
                self.robot.logger.warning(f"get {msg}, not support skill")
                return
            skill = getattr(self.robot.skill, action)
            if not hasattr(skill, 'call'):
                self.robot.logger.warning(f"get {msg}, not support skill")
                return
            kv = self.skill_parameters.get(action, None) or {}
            in_kv = msg.get("parameters", None) or {}
            kv.update(in_kv)
            kv = parse_kwargs(skill.call, **kv)
            return skill(**kv)

        self.robot.logger.warning(f"get {msg}, not support command")
        return

    def _command_execute_control(self, msg: Dict):
        cmd = msg.get("cmd", "")  # legged, arm, head, ...
        control = msg.get("control", "")  # move, turn, ...
        if not (len(cmd) and hasattr(self.robot, cmd) and len(control)):
            self.robot.logger.warning(f"get {msg}, unknown command")
            return

        act_class = getattr(self.robot, cmd)
        if not hasattr(act_class, control):
            self.robot.logger.warning(f"get {msg}, not support control")
            return
        act_function = getattr(act_class, control)
        param = msg.get("parameters", {})
        act_param = parse_kwargs(act_function, **param)
        try:
            act_function(**act_param)
        except Exception as e:  # noqa
            self.robot.logger.error(f"execute {msg} error: {e}")

    def _scaler_coor(self, x, y, z) -> BasePose:
        coor = np.array([float(x), float(y)]) / self.scaling_factor
        z = float(z)
        goal = BasePose(
            x=coor[0], y=coor[1], z=z
        )
        return goal

    def command_callback(self, msg: str):
        try:
            msg = json.loads(msg)
        except Exception as e:  # noqa
            self.robot.logger.error(f"parse command error: {e}")
            return
        _type = msg.get("type", "")
        self.robot.logger.debug(f"get command {msg}")

        if _type == "action":
            return self._command_execute_action(msg)
        if _type == "control":
            return self._command_execute_control(msg)
        if _type == "stop":
            self.robot.motion.set_vel(  # noqa
                linear=0,
                rotational=0
            )
            self.robot.control_mode = RoboControlMode.Auto
            return
        if self.robot.control_mode != RoboControlMode.Remote:
            self.robot.logger.warning(f"Failed to execute command {msg} "
                                      f"while robot is not under remote mode")
            return

        if _type == "velCmd":
            self.robot.logger.debug(f"[Command] {_type} : go to {msg}")
            x = float(msg.get("x", 0))
            yaw = float(msg.get("yaw", 0))
            if x == 0 and yaw == 0:
                return
            self.robot.motion.set_vel(  # noqa
                linear=x,
                rotational=yaw
            )
            return


if __name__ == '__main__':
    client = RoboClient()
    client.run()
