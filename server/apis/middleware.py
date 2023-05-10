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
import traceback
from typing import Optional

from starlette.types import ASGIApp
from fastapi import Request
from fastapi import Response
from fastapi.exceptions import HTTPException
from robosdk.common.exceptions import CloudError

from server.orm.models import ServiceModel


class RequestMiddleware:
    def __init__(
            self,
            app: ASGIApp,
            auth_token: str = None,
            redis_client=None
    ):
        self.app = app
        self._auth_token = auth_token
        self.redis_client = redis_client

    async def __call__(self, scope, receive, send):
        if scope["type"] not in ("lifespan", "http", "websocket"):
            raise CloudError(
                status_code=500,
                message=json.dumps(
                    {
                        "code": 500,
                        "message": f"unknown scope type {scope['type']}"
                     }
                )
            )

        if scope["type"] == "http" and self._auth_token:
            # get iam token from request header
            headers = dict(scope["headers"])
            token = headers.get(b"x-auth-token", b"").decode()
            if not token:
                query_string = scope["query_string"].decode()
                token = self._get_token("x-auth-token", query_string, "")
            if not self.verify_restful_token(token):
                raise CloudError(
                    status_code=401,
                    message=json.dumps(
                        {"code": 401, "message": "X-Auth-Token is invalid"})
                )
        elif scope["type"] == "websocket":
            # get service id from path
            path = scope["path"].strip("/").split("/")
            service_id = path[2] if len(path) > 2 else ""
            # get token from query string
            query_string = scope["query_string"].decode()
            token = self._get_token("token", query_string, "")
            if not await self.verify_websocket_token(service_id, token):
                raise CloudError(
                    status_code=401,
                    message=json.dumps(
                        {"code": 401, "message": "token is invalid"}
                    )
                )

        await self.app(scope, receive, send)

    @staticmethod
    def _get_token(key: str, query_string: str, default="") -> str:
        key = key.strip().lower()
        if not (query_string and key):
            return default
        query_param = query_string.split("&")
        token = default
        for param in query_param:
            items = param.split("=")
            if not len(items) == 2:
                continue
            if items[0].strip().lower() == key:
                token = items[1].strip()
                break
        return token

    async def verify_websocket_token(
            self, service_id: str,
            token: Optional[str] = ""
    ):
        if not token:
            return True
        # get info from redis
        if self.redis_client is None:
            return False
        info: ServiceModel = await self.redis_client.get_service(service_id)
        if info is None:
            return False

        return info.token.strip() == token.strip()

    def verify_restful_token(
            self, token: Optional[str] = ""
    ):
        if not token:
            return True
        return token.upper().strip() == self._auth_token.upper().strip()


async def catch_exceptions_middleware(request: Request, call_next):

    try:
        response = await call_next(request)
    except HTTPException as exc:
        print(f"HTTPException: {exc}", traceback.format_exc())
        response = Response(
            content=json.dumps({"detail": exc.detail, "code": exc.status_code}),
            status_code=exc.status_code)
    except CloudError as e:
        traceback.print_exc()
        return Response(
            status_code=e.status_code,
            content=json.dumps({"code": e.status_code, "message": e.message})
        )
    except Exception as err:  # noqa
        print(f"Exception: {err}", traceback.format_exc())
        response = Response(
            content=json.dumps(
                {"detail": "Internal server error", "code": 500}
            ),
            status_code=500)
    return response
