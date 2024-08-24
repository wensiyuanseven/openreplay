# 这个文件实现了基于JWT（JSON Web Token）的认证机制，主要用于对API请求进行身份验证。通过JWT令牌，系统可以确保用户的身份，并授权用户访问相应的资源。
# 文件中的功能包括解析JWT令牌、校验令牌是否有效、并在某些情况下处理刷新令牌的逻辑。
import datetime
import logging
from typing import Optional

from decouple import config
from fastapi import Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette import status
from starlette.exceptions import HTTPException

import schemas
from chalicelib.core import authorizers, users

logger = logging.getLogger(__name__)


def _get_current_auth_context(request: Request, jwt_payload: dict) -> schemas.CurrentContext:
    user = users.get(user_id=jwt_payload.get("userId", -1), tenant_id=jwt_payload.get("tenantId", -1))
    if user is None:
        logger.warning("User not found.")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User not found.")
    request.state.authorizer_identity = "jwt"
    request.state.currentContext = schemas.CurrentContext(tenantId=jwt_payload.get("tenantId", -1), userId=jwt_payload.get("userId", -1), email=user["email"], role=user["role"])
    return request.state.currentContext


class JWTAuth(HTTPBearer):
    def __init__(self, auto_error: bool = True):
        super(JWTAuth, self).__init__(auto_error=auto_error)

    async def __call__(self, request: Request) -> Optional[schemas.CurrentContext]:
        if request.url.path in ["/refresh", "/api/refresh"]:
            if "refreshToken" not in request.cookies:
                logger.warning("Missing refreshToken cookie.")
                jwt_payload = None
            else:
                jwt_payload = authorizers.jwt_refresh_authorizer(scheme="Bearer", token=request.cookies["refreshToken"])

            if jwt_payload is None or jwt_payload.get("jti") is None:
                logger.warning("Null refreshToken's payload, or null JTI.")
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid refresh-token or expired refresh-token.")
            auth_exists = users.refresh_auth_exists(user_id=jwt_payload.get("userId", -1), jwt_jti=jwt_payload["jti"])
            if not auth_exists:
                logger.warning("refreshToken's user not found.")
                logger.warning(jwt_payload)
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid refresh-token or expired refresh-token.")

            credentials: HTTPAuthorizationCredentials = await super(JWTAuth, self).__call__(request)
            if credentials:
                if not credentials.scheme == "Bearer":
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid authentication scheme.")
                old_jwt_payload = authorizers.jwt_authorizer(scheme=credentials.scheme, token=credentials.credentials, leeway=datetime.timedelta(days=config("JWT_LEEWAY_DAYS", cast=int, default=3)))
                if old_jwt_payload is None or old_jwt_payload.get("userId") is None or old_jwt_payload.get("userId") != jwt_payload.get("userId"):
                    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid token or expired token.")

                return _get_current_auth_context(request=request, jwt_payload=jwt_payload)

        else:
            credentials: HTTPAuthorizationCredentials = await super(JWTAuth, self).__call__(request)
            if credentials:
                if not credentials.scheme == "Bearer":
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid authentication scheme.")
                jwt_payload = authorizers.jwt_authorizer(scheme=credentials.scheme, token=credentials.credentials)
                auth_exists = jwt_payload is not None and users.auth_exists(user_id=jwt_payload.get("userId", -1), jwt_iat=jwt_payload.get("iat", 100))
                if jwt_payload is None or jwt_payload.get("iat") is None or jwt_payload.get("aud") is None or not auth_exists:
                    if jwt_payload is not None:
                        logger.debug(jwt_payload)
                        if jwt_payload.get("iat") is None:
                            logger.debug("iat is None")
                        if jwt_payload.get("aud") is None:
                            logger.debug("aud is None")
                    if not auth_exists:
                        logger.warning("not users.auth_exists")

                    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid token or expired token.")

                return _get_current_auth_context(request=request, jwt_payload=jwt_payload)

        logger.warning("Invalid authorization code.")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid authorization code.")
# 函数及类描述
# _get_current_auth_context
# 描述:
# 这个函数用于从JWT的有效负载中提取用户信息，并设置当前请求的身份认证上下文。

# 参数:

# request (Request): 当前的HTTP请求对象。
# jwt_payload (dict): 从JWT解析出的有效负载，其中包含用户ID、租户ID等信息。
# 返回值:

# schemas.CurrentContext: 代表当前用户的身份认证上下文，包括用户ID、租户ID、电子邮件及角色等信息。
# JWTAuth
# 描述:
# 这是一个自定义的JWT认证类，继承自FastAPI的HTTPBearer。该类重写了认证的逻辑，处理Bearer Token和刷新令牌的情况。

# __call__
# 描述:
# 这个方法在处理请求时被调用，负责解析和校验JWT令牌，并在必要时验证刷新令牌。根据请求路径，它会判断是否使用刷新令牌或普通Bearer Token进行身份验证。

# 参数:

# request (Request): 当前的HTTP请求对象。
# 返回值:

# schemas.CurrentContext: 验证成功后返回当前用户的身份认证上下文。
# 函数执行逻辑
# 1. 刷新令牌处理
# 如果请求路径为/refresh或/api/refresh，那么JWTAuth会使用cookie中的refreshToken来进行身份验证。
# 首先检查请求中的cookie是否包含refreshToken，如果没有，抛出异常。
# 然后，它会验证refreshToken的有效性，检查refreshToken中的JTI（JWT ID）是否与数据库中的记录匹配。
# 最后，如果提供了普通的Bearer Token，则对其进行验证，并确认是否与refreshToken的用户信息一致。
# 2. 普通Bearer Token处理
# 对于非刷新令牌路径，JWTAuth类会使用Bearer Token进行身份验证。
# 首先验证Bearer Token的有效性，解析JWT令牌中的userId和iat（签发时间）字段。
# 然后，检查JWT的签发时间和用户是否仍然有效。
# 如果令牌有效，则设置当前的用户身份认证上下文。
# 错误处理
# 如果JWT或刷新令牌无效，或是用户信息不存在，该系统会返回HTTP 403错误，提示"Invalid token or expired token"或者其他相应的错误消息。
# 核心逻辑总结
# 身份验证: 系统通过JWT进行身份验证，提取用户信息并确保用户身份的真实性。
# 刷新令牌: 对于需要刷新身份验证的情况，系统会使用refreshToken来重新获取身份认证上下文。
# 错误处理: 如果身份验证失败，系统会记录错误日志，并返回适当的HTTP错误响应。
