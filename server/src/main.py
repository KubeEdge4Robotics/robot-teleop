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

from robosdk.core.world import World
from robosdk.common.class_factory import ClassFactory
from robosdk.common.class_factory import ClassType
from robosdk.cloud_robotics.cloud_base import ServiceBase


@ClassFactory.register(ClassType.CLOUD_ROBOTICS, "rtc_teleop_server")
class RTCTeleopServer(ServiceBase):
    def __init__(self,
                 name: str = "control",
                 host: str = "0.0.0.0",
                 port: int = 5540,
                 static_folder: str = "",):
        super(RTCTeleopServer, self).__init__(
            name=name, host=host, port=port, static_folder=static_folder
        )

    def run(self, **kwargs):
        self.server.initial()
        super(RTCTeleopServer, self).run(**kwargs)

    def close(self):
        self.app.shutdown = True


def main():

    server: World = World(name="teleoperation", config="teleop")
    server.start()


if __name__ == '__main__':
    main()
