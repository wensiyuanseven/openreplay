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
#  这意味着 APIKeyAuth 类将具有 APIKeyHeader 类的所有属性和方法。 继承允许 APIKeyAuth 扩展或修改 APIKeyHeader 的功能。


class APIKeyAuth(APIKeyHeader):
    # 在 __init__ 方法中，调用了父类 APIKeyHeader 的构造函数，并设置了 name 为 "Authorization" auto_error 为传入的参数或默认为 True。
    def __init__(self, auto_error: bool = True):
        # python3支持 super().__init__无参数调用，更简洁
        super(APIKeyAuth, self).__init__(
            name="Authorization", auto_error=auto_error)
    # 允许类的实例像函数一样被调用
    # 在这个 __call__ 方法中：
    # 首先调用父类的 __call__ 方法从请求中提取 API Key。
    # 然后调用 authorizers.api_key_authorizer(api_key) 方法验证提取的 API Key。
    # 如果验证失败（即 r 为 None），则引发一个 HTTP 401 未授权的异常，通知客户端 API Key 无效。
    # 如果验证成功，继续处理，并将相关信息存储在请求的 state 中。

    async def __call__(self, request: Request) -> Optional[CurrentAPIContext]:
        # 将结果赋值给 api_key 变量，并使用 Optional[str] 类型注解表明其类型
        api_key: Optional[str] = await super(APIKeyAuth, self).__call__(request)

        r = authorizers.api_key_authorizer(api_key)
        # 如果这个结果为 None，意味着提供的 API Key 无效或者没有通过验证。
        if r is None:
            # raise 关键字用于引发一个异常。在 Python 中，引发异常是报告错误情况的一种方式。 raise 终止
            # 401状态码 通常用于表示请求需要身份验证，但身份验证失败或未提供
            # Invalid API Key 提供异常的详细信息。这个信息会包含在 HTTP 响应中，通常用于向客户端说明错误原因
            # 整个代码块的功能是：如果 API Key 验证失败（即 r 为 None），则引发一个 HTTPException 异常，返回 HTTP 401 未授权状态码，
            # 并附带 "Invalid API Key" 的错误信息。这会立即终止当前请求的处理，并将错误信息返回给客户端。
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API Key",
            )
        # 设置授权标识
        r["authorizer_identity"] = "api_key"

        logger.debug(r)
        # 将授权标识保存到请求的状态中。
        request.state.authorizer_identity = "api_key"
        # 创建 CurrentAPIContext 实例并将其保存到请求的状态中。
        request.state.currentContext = CurrentAPIContext(
            tenantId=r["tenantId"])
        return request.state.currentContext
