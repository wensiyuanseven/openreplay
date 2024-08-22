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



# 这个代码片段定义了一个自定义的FastAPI路由处理器`ORRoute`以及一些与角色验证相关的函数，用于增强API的安全性和处理机制。以下是对各个部分的详细解释：

# ### 1. **`OR_context`函数**
# ```python
# async def OR_context(request: Request) -> schemas.CurrentContext:
#     if hasattr(request.state, "currentContext"):
#         return request.state.currentContext
#     else:
#         raise Exception("currentContext not found")
# ```
# - 这是一个依赖项函数，它用于从`request.state`中获取并返回`currentContext`。如果`request`对象中没有`currentContext`，则会抛出异常。
# - 在处理API请求时，这个`OR_context`通常用于获取当前请求的上下文（如用户信息、权限等），从而为后续的业务逻辑提供必要的数据。

# ### 2. **`ORRoute`类**
# ```python
# class ORRoute(APIRoute):
#     def get_route_handler(self) -> Callable:
#         original_route_handler = super().get_route_handler()

#         async def custom_route_handler(request: Request) -> Response:
#             logger.debug(f"call processed by: {self.methods} {self.path_format}")
#             try:
#                 response: Response = await original_route_handler(request)
#             except HTTPException as e:
#                 if e.status_code // 100 == 4:
#                     return JSONResponse(content={"errors": e.detail if isinstance(e.detail, list) else [e.detail]},
#                                         status_code=e.status_code)
#                 else:
#                     raise e

#             if isinstance(response, JSONResponse):
#                 response: JSONResponse = response
#                 body = json.loads(response.body.decode('utf8'))
#                 body = helper.cast_session_id_to_string(body)
#                 response = JSONResponse(content=body, status_code=response.status_code,
#                                         headers={k: v for k, v in response.headers.items() if k != "content-length"},
#                                         media_type=response.media_type, background=response.background)
#                 if response.status_code == 200 and body is not None and isinstance(body, dict) and body.get("errors") is not None:
#                     if "not found" in body["errors"][0]:
#                         response.status_code = status.HTTP_404_NOT_FOUND
#                     else:
#                         response.status_code = status.HTTP_400_BAD_REQUEST
#             return response

#         return custom_route_handler
# ```
# - `ORRoute`继承自FastAPI的`APIRoute`，自定义了FastAPI默认的路由处理行为。
# - `get_route_handler()`方法重写了路由的处理逻辑：
#   - 通过调用`original_route_handler`执行原始的路由处理逻辑。
#   - 捕获可能抛出的`HTTPException`，尤其是状态码4xx的错误。如果是客户端错误，返回一个包含错误信息的JSON响应。
#   - 对`JSONResponse`响应进行特殊处理：将响应体解析为Python对象，对`session_id`等字段进行必要的转换，然后重新生成一个JSON响应。
#   - 如果响应包含`errors`字段，并且错误信息中包含"not found"，则将HTTP状态码设为`404`，否则设置为`400`。
  
# 这个类主要是为了统一处理API的错误响应、日志记录以及确保特定字段的数据类型一致性。

# ### 3. **`__check_role`函数**
# ```python
# def __check_role(required_roles: SecurityScopes, context: schemas.CurrentContext = Depends(OR_context)):
#     if len(required_roles.scopes) > 0:
#         if context.role not in required_roles.scopes:
#             raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
#                                 detail="You need a different role to access this resource")
# ```
# - `__check_role`函数用于检查当前用户是否具有访问某个资源所需的角色。
# - `required_roles`是通过`SecurityScopes`传入的一组角色，`context`是通过`OR_context`获取的当前用户上下文。
# - 如果`context.role`不在`required_roles`中，则抛出`401 Unauthorized`的HTTP异常。

# ### 4. **`OR_role`函数**
# ```python
# def OR_role(*required_roles):
#     return Security(__check_role, scopes=list(required_roles))
# ```
# - 这是一个帮助函数，用于构建基于角色的权限验证。
# - 它返回一个`Security`依赖项，内部调用`__check_role`函数。`required_roles`指定了访问某个资源所需要的角色。
  
# 例如，如果一个路由只能由管理员访问，你可以这样使用：
# ```python
# @app.get("/admin-only", dependencies=[OR_role("admin")])
# async def admin_only_route():
#     return {"message": "This is a protected route for admins"}
# ```

# ### 总结
# - **`OR_context`** 用于从请求中提取上下文信息。
# - **`ORRoute`** 自定义了路由处理逻辑，用于更好地处理错误响应和特定数据字段的处理。
# - **`__check_role`** 和 **`OR_role`** 实现了基于角色的权限检查，确保只有特定角色的用户才能访问特定资源。