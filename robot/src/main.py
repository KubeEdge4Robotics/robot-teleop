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
from typing import (
    Dict,
    List
)
from datetime import datetime

import numpy as np

from robosdk.core import Robot
from robosdk.utils.util import EnvBaseContext
from robosdk.common.robot_status import RobotStatus
from robosdk.common.constant import (
    RoboControlMode,
    ActionStatus
)
from robosdk.common.schema.pose import BasePose
from robosdk.common.schema.map import PgmMap
from robosdk.algorithms.navigation.planning import RosMoveBase
from robosdk.algorithms.perception.mapping.visual import RosMapVisual
from robosdk.cloud_robotics.remote_control.edge.webrtc import ControlRTCRobot


class RoboClient:
    skill_parameters = {
        "capture_photo": {"output": "/home/capture.png"}
    }

    def __init__(self, name="scout", config="scout_arm"):
        self.robot = Robot(name=name, config=config)

        uri = EnvBaseContext.get(
            "SERVER_URL", "http://127.0.0.1:5540/teleoperation")
        self.client = ControlRTCRobot(
            robot=self.robot,
            name="teleoperation",
            uri=uri
        )
        self._robot_status = RobotStatus(timer=.5)
        self.robot.connect()
        self.client.connect()
        self.waypoints: List[BasePose] = []
        self.waypoints_status: List[ActionStatus] = []
        self.labels = {}

        self.navigation = RosMoveBase(logger=self.robot.logger)
        self.map_view = RosMapVisual(logger=self.robot.logger)
        self.maps = None
        self.scaling_factor = [1, 1]
        self.show_laser = True
        self.client.add_worker(
            name_space="VideoConf",
            kind="remote",
            data_func=self.async_get_remote,
            audio_enable=True,
        )
        self.client.add_worker(
            name_space="CameraX",
            kind="stream",
            data_func=self.async_send_hand,
        )
        self.client.add_worker(
            name_space="CameraY",
            kind="stream",
            data_func=self.async_send_front,
        )
        self.client.add_worker(
            name_space="Map",
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

        for inx, point in enumerate(self.waypoints):
            self.map_view.add_label(
                int(point.x + 0.5), int(point.y + 0.5),
                kind="waypoint",
                name=str(inx)
            )

        for name, point in self.labels.items():
            self.map_view.add_label(
                int(point["x"] + 0.5),
                int(point["y"] + 0.5),
                kind="marker",
                name=name
            )

        if hasattr(self.robot, "voice"):
            voice, _ = self.robot.voice.get_data()
        else:
            voice = None
        return [self.map_view.curr_frame, voice]

    def async_get_remote(self, videos: List, audio: List):
        self.robot.logger.info(f"get video => {videos}")
        self.robot.logger.info(f"get audio => {audio}")
        for audio_msg in audio:
            self.robot.voice.say(audio_msg)

    def async_send_front(self) -> List[np.ndarray]:
        frame, _ = self.robot.all_sensors["camera"]["camera_front"].get_rgb()
        return [frame, None]

    def async_send_hand(self) -> List[np.ndarray]:
        frame, _ = self.robot.all_sensors["camera"]["camera_arm"].get_rgb()
        return [frame, None]

    def async_send_status(self) -> List[Dict]:
        robot_status = self._get_robot_status()
        dock_status = self._get_docking_status()
        status = [robot_status, dock_status]
        if self.waypoints:
            waypoint_status = self._get_waypoint_status()
            status.append(waypoint_status)
        if self.labels:
            label_status = self._get_labels_status()
            status.append(label_status)
        return status

    def _get_waypoint_status(self) -> Dict:
        # {"waypointNumber": 0}
        if ActionStatus.SUCCEEDED in self.waypoints_status:
            last_reached = self.waypoints_status[::-1].index(
                ActionStatus.SUCCEEDED
            )
            last_reached = len(self.waypoints_status) - last_reached
        else:
            last_reached = 0
        return {
            "type": "waypointReached",
            "waypointNumber": last_reached
        }

    def _get_docking_status(self) -> Dict:
        # {"status": ""}
        return {
            "type": "docking_status",
            "status": self.robot.control_mode.name
        }

    def _get_labels_status(self) -> Dict:
        # {"labels": []}
        labels = [
            {"name": k, "value": k, "description": v["description"]}
            for k, v in self.labels.items()
        ]
        return {
            "type": "labels",
            "labels": labels
        }

    def _get_robot_status(self) -> Dict:
        # {
        #     'battery': 10.4, 'isCharging': False, 'batteryVoltage': 14.5,
        #     'batteryCurrent': 1.0, 'batteryLevel': 56, 'cpuUsage': 80,
        #     'memUsage': 34, 'diskUsage': 21, 'wifiNetwork': 'testnetwork',
        #     'wifiStrength': 100, 'localIp': ""
        # }
        status = dict(self._robot_status.data)

        if hasattr(self.robot, "battery") and hasattr(self.robot.battery,
                                                      "battery"):
            battery = self.robot.battery.battery
            status["isCharging"] = battery.get("isCharging", "") or False
            for k in ("batteryCurrent", "battery",
                      "batteryVoltage", "batteryLevel"):
                status["battery"] = battery.get(k, .0)
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
            kv = self.skill_parameters.get(action, None) or {}
            return skill(**kv)
        if action == "setMovementMode":
            self.robot.control_mode = RoboControlMode.Auto
            self.robot.logger.info(f"changing RoboControlMode to {cmd}")
            if cmd == "teleop":
                self.robot.control_mode = RoboControlMode.Remote
            elif cmd == "follow":
                # todo
                pass
            else:
                # todo
                pass
        return

    def _scaler_coor(self, x, y, z) -> BasePose:
        coor = np.array([float(x), float(y)]) / self.scaling_factor
        z = float(z)
        goal = BasePose(
            x=coor[0], y=coor[1], z=z
        )
        return goal

    def _command_execute_label(self, msg: Dict, _type: str = ""):
        data = msg.get("label", {})
        if not data:
            return
        if _type == "addLabel":
            name = data.get("name", "")
            desc = data.get("description", "")
            coordinate = data.get("coordinate", {})
            if "x" not in coordinate:
                return

            goal = self._scaler_coor(
                coordinate["x"],
                coordinate["y"],
                coordinate["yaw"]
            )
            self.labels[name] = {
                "description": desc,
                "x": goal.x,
                "y": goal.y,
                "z": goal.z
            }

        if _type == "removeLabel":
            pass

        if _type == "editLabel":
            name = data.get("name", "")
            desc = data.get("description", "")
            self.labels[name] = {
                "description": desc,
            }

    def command_callback(self, msg: Dict):
        _type = msg.get("type", "")
        self.robot.logger.debug(f"get command {msg}")

        if _type == "action":
            return self._command_execute_action(msg)
        if _type == "stop":
            self.robot.motion.set_vel(  # noqa
                linear=0,
                rotational=0
            )
            self.robot.control_mode = RoboControlMode.Auto
            self.waypoints = []
            self.waypoints_status = []
            return
        if self.robot.control_mode != RoboControlMode.Remote:
            self.robot.logger.warning(f"Failed to execute command {msg} "
                                      f"while robot is not under remote mode")
            return

        if _type == "velCmd":
            self.robot.logger.info(f"[Command] {_type} : go to {msg}")
            x = float(msg.get("x", 0))
            yaw = float(msg.get("yaw", 0))
            if x == 0 and yaw == 0:
                return
            self.robot.motion.set_vel(  # noqa
                linear=x,
                rotational=yaw
            )
            return
        if _type == "waypoint":
            data = msg.get("array", [])

            for point in data:
                coordinate: Dict = point.get("coordinate", {})
                if "x" not in coordinate:
                    continue
                goal = self._scaler_coor(
                    coordinate["x"],
                    coordinate["y"],
                    coordinate["yaw"]
                )
                self.waypoints.append(goal)
                self.waypoints_status.append(ActionStatus.PENDING)
            return
        if _type == "start":
            self.robot.logger.info(f"start execute waypoints, "
                                   f"totally {len(self.waypoints)}")
            for gid, goal in enumerate(self.waypoints):
                curr_p = self.robot.odom.get_curr_state()  # noqa
                target = self.maps.pixel2world(
                    goal.x, goal.y, goal.z
                )
                state: ActionStatus = self.navigation.goto(
                    goal=target, start=curr_p, async_run=True
                )
                self.waypoints_status[gid] = state
                if state == ActionStatus.SUCCEEDED:
                    self.robot.logger.info(f"reach waypoints, {gid}: {goal}")

        if _type in ("goToLabel", "removeLabel", "addLabel", "editLabel"):
            self._command_execute_label(msg, _type)


if __name__ == '__main__':
    client = RoboClient()
    client.run()
