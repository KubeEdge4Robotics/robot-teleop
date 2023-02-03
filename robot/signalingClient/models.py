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
    Optional,
    Any,
    Callable
)
from enum import Enum
import fractions
import time

import numpy as np
from pydantic import BaseModel
from aiortc.mediastreams import (
    MediaStreamTrack,
    VideoStreamTrack
)
from robosdk.utils.lazy_imports import LazyImport
from robosdk.common.constant import InternalConst


class ICEServerModel(BaseModel):
    """
    ICE server model
    """
    urls: str
    username: Optional[str]
    password: Optional[str]
    credential: Optional[str]


class RTCClient(BaseModel):
    """
    RTC client model
    """
    sid: str = ""
    name: str = ""
    pc: Any = None  # RoboRTCPeerConnection
    room: Optional[str]
    roomId: Optional[str]
    role: Optional[str]
    utype: Optional[str]


class SocketEvents(Enum):
    """
    Socket events
    """
    # client events
    CONNECT = "connect"
    DISCONNECT = "disconnect"
    CLOSE = "close"
    ROOM_CLIENTS = "room-clients"
    MAKE_PEER_CALL = "make-peer-call"
    PEER_CALL_ICE_CANDIDATE_RECEIVED = "ice-candidate-received"
    PEER_CALL_RECEIVED = "peer-call-received"
    PEER_CALL_ANSWER_RECEIVED = "peer-call-answer-received"
    PEER_CALL_CLOSE = "close-all-peer-connections-request-received"

    # server events
    JOIN_ROOM = "join-room"
    LEVE_ROOM = "leave-room"
    MAKE_PEER_CALL_ANSWER = "make-peer-call-answer"
    CALL_ALL = "call-all"
    CALL = "call-ids"
    PEER_CALL = "call-peer"
    PEER_CALL_ICE_CANDIDATE = "send-ice-candidate"
    CLOSE_ALL = "close-all-room-peer-connections"


class CameraStreamTrack(VideoStreamTrack):
    """
    A video stream track that reads frames from a queue.
    """

    def __init__(
            self,
            name: str,
            listen_track: Optional[MediaStreamTrack] = None,
            data_func: Optional[Callable] = None,
            message_callback: Optional[Callable] = None,
    ):
        """
        :param name: The name of the track.
        :param listen_track: The track to listen to.
        :param data_func: The function to get data.
        :param message_callback: The callback function to handle message.
        """
        super().__init__()
        self.kind = "video"
        self.name = name
        self.listen_track = listen_track
        self.data_func = data_func
        self.message_callback = message_callback
        self._av_lib = LazyImport("av")

    async def trans_frame(self, frame: np.ndarray, _format: str = "bgr24"):
        pts, time_base = await self.next_timestamp()
        # conver frame from ndarry to av frame
        data = self._av_lib.VideoFrame.from_ndarray(frame, format=_format)
        data.time_base = time_base
        data.pts = pts
        return data

    async def recv(self):

        if self.readyState != "live":
            return
        if self.listen_track is not None:
            frame = await self.listen_track.recv()
        elif self.data_func is not None:
            frame = await self.trans_frame(self.data_func())
        else:
            frame = None
        if self.message_callback is not None:
            # transform av frame to ndarry
            array = frame.to_ndarray()
            self.message_callback(array)
        return frame


class AudioStreamTrack(CameraStreamTrack):
    """
    An audio stream track that reads frames from a queue.
    """

    def __init__(
            self,
            name: str,
            listen_track: Optional[MediaStreamTrack] = None,
            data_func: Optional[Callable] = None,
            message_callback: Optional[Callable] = None,
    ):
        super().__init__(
            name,
            listen_track=listen_track,
            data_func=data_func,
            message_callback=message_callback
        )
        self.kind = "audio"

    async def trans_frame(
            self,
            frame: np.ndarray,
            _format: str = "s16",
            layout: str = "mono"):
        if self.readyState != "live":
            return
        fr = InternalConst.AUDIO_CLOCK_RATE.value
        timebase = fractions.Fraction(1, fr)
        pts = int(time.time() * fr)
        # conver frame from ndarry to av frame
        data = self._av_lib.AudioFrame.from_ndarray(
            array=frame, format=_format, layout=layout)  # noqa
        data.time_base = timebase
        data.pts = pts
        return data

