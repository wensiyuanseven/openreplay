# 文件作用
# 该文件定义了一个用于基于API密钥的身份验证类APIKeyAuth，它继承自FastAPI的APIKeyHeader类，
# 目的是从HTTP请求头中提取API密钥并对其进行验证。通过这种方式，确保只有提供有效API密钥的用户才能访问特定API接口。
import logging
from typing import Optional

from fastapi import Request
from fastapi.security import APIKeyHeader
from starlette import status
from starlette.exceptions import HTTPException

from chalicelib.core import authorizers
from schemas import CurrentAPIContext

logger = logging.getLogger(__name__)

# APIKeyAuth是一个自定义的身份验证类，通过继承APIKeyHeader，实现从HTTP请求头中提取API密钥并调用自定义的验证逻辑。在验证通过后，设置请求的当前上下文信息，包括租户ID。
class APIKeyAuth(APIKeyHeader):
    # 该方法用于初始化APIKeyAuth类。它通过指定API密钥所在的请求头字段（默认是Authorization），并决定当API密钥验证失败时，是否自动抛出错误。
    # 参数:
    # auto_error (bool):默认值为True。
    # 如果设置为True，验证失败时会自动抛出HTTP 401 Unauthorized错误。
    # 如果设置为False，验证失败时返回None，而不抛出错误。
    def __init__(self, auto_error: bool = True):
        super(APIKeyAuth, self).__init__(name="Authorization", auto_error=auto_error)
    # 该方法会在每次请求时调用，用于从请求中提取API密钥并进行验证。它首先从Authorization头中获取API密钥，然后调用自定义的authorizers.api_key_authorizer函数来检查该密钥的有效性。
    # 如果API密钥有效，它将请求上下文中的authorizer_identity设置为api_key，并将当前上下文的租户ID添加到request.state.currentContext。
    # 参数:request (Request):FastAPI的请求对象，包含请求的所有信息。
    # 返回值:
    # Optional[CurrentAPIContext]:
    # 如果API密钥有效，则返回当前上下文对象CurrentAPIContext，其中包含与该API密钥关联的租户ID。
    # 如果API密钥无效，则抛出HTTP 401 Unauthorized错误。
    # 函数执行逻辑
    # 获取API密钥:
    # 通过从HTTP请求头中的Authorization字段提取API密钥。
    # 验证API密钥:
    # 使用authorizers.api_key_authorizer(api_key)函数对提取的API密钥进行验证。
    # 如果API密钥无效，抛出HTTP 401 Unauthorized错误，并返回"Invalid API Key"。
    # 设置上下文:
    # 如果验证通过，则将认证方式（api_key）保存到request.state.authorizer_identity。
    # 同时，将当前的租户ID保存到request.state.currentContext中，供后续请求使用。
    # 日志记录:
    # 如果验证成功，记录调试日志以便进行调试和跟踪。
    # 核心逻辑总结
    # API密钥验证: 验证请求是否包含有效的API密钥。
    # 上下文设置: 验证通过后，设置当前请求的API上下文，包括租户ID信息。
    # 错误处理: 如果API密钥无效，系统会返回HTTP 401 Unauthorized错误，防止未经授权的访问。
    # 使用场景
    # 该类主要用于需要API密钥保护的API接口，通过验证API密钥来确保只有持有有效密钥的用户能够访问受保护的资源。这种机制通常用于防止未经授权的第三方请求。
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
        request.state.currentContext = CurrentAPIContext(tenantId=r["tenantId"])
        return request.state.currentContext