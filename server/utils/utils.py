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

from datetime import datetime

import hashlib
import hmac
from robosdk.utils.util import singleton
from robosdk.common.logger import logging
from robosdk.common.class_factory import ClassFactory
from robosdk.common.class_factory import ClassType
from pyee.asyncio import AsyncIOEventEmitter


def HMAC256(key: str, msg: str) -> str:
    """
    HMAC256
    """
    return hmac.new(
        bytes(key, 'utf-8'), bytes(msg, 'utf-8'),
        hashlib.sha256
    ).hexdigest()


def genearteMD5(item) -> str:
    hl = hashlib.md5()
    hl.update(item.encode(encoding='utf-8'))
    return hl.hexdigest()


def gen_token(length: int = 4):
    """
    generate token
    """
    return str(
        hashlib.sha256(str(datetime.now()).encode('utf-8')).hexdigest()
    )[:length]


@singleton
class EventManager:
    _event = {}
    logger = logging.bind(instance="EventManager", system=True)

    def register(self, event_tag: str, event: AsyncIOEventEmitter = None):
        if event is None:
            event = ClassFactory.get_cls(
                ClassType.EVENT, event_tag
            )()
        if not isinstance(event, AsyncIOEventEmitter):
            raise TypeError(
                f"event {event_tag} is not a AsyncIOEventEmitter"
            )
        self._event[event_tag] = event

    def emit(self, event_name: str, **kwargs):
        if kwargs.get("event_tag"):
            _event_tag = kwargs.pop("event_tag")
            if _event_tag in self._event:
                try:
                    self._event[_event_tag].emit(event_name, **kwargs)
                except Exception as e:
                    self.logger.error(
                        f"emit event {event_name} - {_event_tag} error: {e}"
                    )
        else:
            for _event_tag, event in self._event.items():
                try:
                    event.emit(event_name, **kwargs)
                except Exception as e:
                    self.logger.error(
                        f"emit event {event_name} - {_event_tag} error: {e}"
                    )
