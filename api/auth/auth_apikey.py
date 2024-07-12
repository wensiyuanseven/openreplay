# 导入模块和库
import logging  # Python 内置的日志记录模块，用于记录调试信息。
from typing import Optional  # Python 标准库中的类型提示，表示某个值可以是指定类型，也可以是 None

from fastapi import Request  # FastAPI 中的请求对象，用于处理 HTTP 请求。
from fastapi.security import APIKeyHeader  # FastAPI 提供的用于处理 API Key 头部认证的类。
from starlette import status  # Starlette 中定义的 HTTP 状态码。
# Starlette 中的 HTTP 异常类，用于抛出 HTTP 异常。
from starlette.exceptions import HTTPException

# 从自定义模块 chalicelib.core 中导入 authorizers，用于 API Key 的授权逻辑。
from chalicelib.core import authorizers
from schemas import CurrentAPIContext  # 导入一个用于当前 API 上下文的数据模型。

logger = logging.getLogger(__name__)  # 创建一个日志记录器，名称为当前模块的名称，用于记录调试信息


# APIKeyAuth 类：
# 定义了一个继承自 APIKeyHeader 的新类 APIKeyAuth，用于处理 API Key 头部认证。


class APIKeyAuth(APIKeyHeader):
    # 在 __init__ 方法中，调用了父类 APIKeyHeader 的构造函数，并设置了 name 为 "Authorization" auto_error 为传入的参数或默认为 True。
    def __init__(self, auto_error: bool = True):
        super(APIKeyAuth, self).__init__(
            name="Authorization", auto_error=auto_error)

    async def __call__(self, request: Request) -> Optional[CurrentAPIContext]:
        api_key: Optional[str] = await super(APIKeyAuth, self).__call__(request)
        r = authorizers.api_key_authorizer(api_key)
        if r is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API Key",
            )
        r["authorizer_identity"] = "api_key"
        logger.debug(r)
        request.state.authorizer_identity = "api_key"
        request.state.currentContext = CurrentAPIContext(
            tenantId=r["tenantId"])
        return request.state.currentContext
