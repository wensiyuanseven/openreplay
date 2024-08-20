import json
import logging
from typing import Callable

from fastapi import Depends, Security
from fastapi.routing import APIRoute
from fastapi.security import SecurityScopes
from starlette import status
from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.responses import Response, JSONResponse

import schemas
from chalicelib.utils import helper

logger = logging.getLogger(__name__)


async def OR_context(request: Request) -> schemas.CurrentContext:
    # 如果 request.state 对象有 currentContext 属性，则执行以下代码
    if hasattr(request.state, "currentContext"):
        return request.state.currentContext
    else:
        raise Exception("currentContext not found")


class ORRoute(APIRoute):
    def get_route_handler(self) -> Callable:
        original_route_handler = super().get_route_handler()

        async def custom_route_handler(request: Request) -> Response:
            logger.debug(f"call processed by: {self.methods} {self.path_format}")
            try:
                response: Response = await original_route_handler(request)
            except HTTPException as e:
                # 捕获整个 4xx 范围的状态码
                if e.status_code // 100 == 4:
                    return JSONResponse(content={"errors": e.detail if isinstance(e.detail, list) else [e.detail]},
                                        status_code=e.status_code)
                else:
                    raise e

            if isinstance(response, JSONResponse):
                # response = response 这样的代码在语法上是完全正确的，但在逻辑上它是冗余的 它只是把 response 变量的当前值重新赋值给它自己。这不会导致语法错误或异常
                # 相比之下，带有类型注解的 response: JSONResponse = response 是有用的，因为它明确了 response 的类型，尽管它也不会改变 response 的值或类型。类型注解的作用是在代码中提供类型信息，增强代码的可读性，并帮助静态类型检查器。
                response: JSONResponse = response
                # 用于将 JSON 格式的字符串解析为对应的 Python 数据结构（通常是字典或列表）。
                body = json.loads(response.body.decode('utf8'))  #假设输入的字符串是 '{"key": "value"}'，那么 json.loads 会将其转换为 Python 字典 {"key": "value"}。
                body = helper.cast_session_id_to_string(body)
                response = JSONResponse(content=body, status_code=response.status_code,
                                        headers={k: v for k, v in response.headers.items() if k != "content-length"},
                                        media_type=response.media_type, background=response.background)
                if response.status_code == 200 and body is not None and isinstance(body, dict) and body.get("errors") is not None:
                    if "not found" in body["errors"][0]:
                        response.status_code = status.HTTP_404_NOT_FOUND
                    else:
                        response.status_code = status.HTTP_400_BAD_REQUEST
            return response

        return custom_route_handler


def __check_role(required_roles: SecurityScopes, context: schemas.CurrentContext = Depends(OR_context)):
    if len(required_roles.scopes) > 0:
        if context.role not in required_roles.scopes:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                detail="You need a different role to access this resource")


def OR_role(*required_roles):
    return Security(__check_role, scopes=list(required_roles))
