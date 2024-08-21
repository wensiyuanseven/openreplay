# 这个文件的主要作用是处理 JWT 的生成、验证，以及通过 JWT 获取用户信息。
# 它还处理了 API 密钥的验证。整个模块通过 JWT 来确保 API 调用的安全性，并且支持对 JWT 和刷新令牌的管理。
# 这对于保护 API 免受未经授权的访问以及管理用户会话非常重要。
import logging

import jwt
from decouple import config

from chalicelib.core import tenants
from chalicelib.core import users
from chalicelib.utils import helper
from chalicelib.utils.TimeUTC import TimeUTC

logger = logging.getLogger(__name__)

# 这个函数用于验证 JWT 的有效性，并返回解码后的有效载荷。
# 参数：
# scheme: 表示认证的方案，通常是 "Bearer"。
# token: JWT 令牌。
# leeway: 可选的时间宽限，用于处理时间相关的校验，如签发时间和过期时间。
# 作用：
# 检查认证方案是否为 "Bearer"，如果不是，返回 None。
# 使用 jwt.decode 方法解码 JWT，验证其有效性，包括过期时间、签名等。
# 如果 JWT 过期或解码失败，捕获异常并记录日志。
# 成功解码后，返回解码后的有效载荷（payload）。
def jwt_authorizer(scheme: str, token: str, leeway=0):
    if scheme.lower() != "bearer":
        return None
    try:
        payload = jwt.decode(
            token,
            config("jwt_secret"),
            algorithms=config("jwt_algorithm"),
            audience=[f"front:{helper.get_stage_name()}"],
            leeway=leeway
        )
    except jwt.ExpiredSignatureError:
        logger.debug("! JWT Expired signature")
        return None
    except BaseException as e:
        logger.warning("! JWT Base Exception")
        logger.debug(e)
        return None
    return payload

# 这个函数类似于 jwt_authorizer，但它用于验证 JWT 刷新令牌（refresh token）。
# 参数：
# scheme: 认证方案，通常是 "Bearer"。
# token: JWT 刷新令牌。
# 作用：
# 与 jwt_authorizer 类似，但使用不同的密钥 JWT_REFRESH_SECRET 和不同的令牌有效载荷（payload）。
# 如果刷新令牌过期或解码失败，同样会捕获异常并记录日志。

def jwt_refresh_authorizer(scheme: str, token: str):
    if scheme.lower() != "bearer":
        return None
    try:
        payload = jwt.decode(
            token,
            config("JWT_REFRESH_SECRET"),
            algorithms=config("jwt_algorithm"),
            audience=[f"front:{helper.get_stage_name()}"]
        )
    except jwt.ExpiredSignatureError:
        logger.debug("! JWT-refresh Expired signature")
        return None
    except BaseException as e:
        logger.warning("! JWT-refresh Base Exception")
        logger.debug(e)
        return None
    return payload

# 这个函数根据 JWT 提供的上下文信息，获取用户的详细信息。
# 参数：
# context: 包含 userId 和 tenantId 的上下文信息。
# 作用：
# 根据上下文中的 userId 和 tenantId 从数据库中获取用户信息。
# 如果用户存在，返回包含 tenantId、userId 和用户其他信息的字典。
# 如果用户不存在，返回 None。
def jwt_context(context):
    user = users.get(user_id=context["userId"], tenant_id=context["tenantId"])
    if user is None:
        return None
    return {
        "tenantId": context["tenantId"],
        "userId": context["userId"],
        **user
    }

# 这个函数用于生成 JWT 令牌。

# 参数：

# user_id: 用户 ID。
# tenant_id: 租户 ID。
# iat: 签发时间（以时间戳表示）。
# aud: 受众（audience），表示令牌的预期接收方。
# 作用：

# 生成一个包含 userId、tenantId、exp（过期时间）、iss（签发者）、iat（签发时间）和 aud（受众）的有效载荷。
# 使用配置文件中的密钥和算法对令牌进行签名，并返回生成的 JWT 令牌。
def generate_jwt(user_id, tenant_id, iat, aud):
    token = jwt.encode(
        payload={
            "userId": user_id,
            "tenantId": tenant_id,
            "exp": iat + config("JWT_EXPIRATION", cast=int),
            "iss": config("JWT_ISSUER"),
            "iat": iat,
            "aud": aud
        },
        key=config("jwt_secret"),
        algorithm=config("jwt_algorithm")
    )
    return token

# 这个函数用于生成 JWT 刷新令牌。
# 参数：
# user_id: 用户 ID。
# tenant_id: 租户 ID。
# iat: 签发时间。
# aud: 受众。
# jwt_jti: JWT ID，用于标识刷新令牌。
# 作用：
# 与 generate_jwt 类似，但用于生成刷新令牌，使用不同的密钥 JWT_REFRESH_SECRET 和包含 jti（JWT ID） 的有效载荷。
# 返回生成的 JWT 刷新令牌。
def generate_jwt_refresh(user_id, tenant_id, iat, aud, jwt_jti):
    token = jwt.encode(
        payload={
            "userId": user_id,
            "tenantId": tenant_id,
            "exp": iat + config("JWT_REFRESH_EXPIRATION", cast=int),
            "iss": config("JWT_ISSUER"),
            "iat": iat,
            "aud": aud,
            "jti": jwt_jti
        },
        key=config("JWT_REFRESH_SECRET"),
        algorithm=config("jwt_algorithm")
    )
    return token

# 这个函数用于基于 API 密钥进行授权。
# 参数：
# token: API 密钥。
# 作用：
# 根据提供的 API 密钥从数据库中获取租户信息。
# 如果租户存在，将租户的 createdAt 时间戳进行转换，并返回租户信息。
# 如果未找到对应的租户，返回 None。
def api_key_authorizer(token):
    t = tenants.get_by_api_key(token)
    if t is not None:
        t["createdAt"] = TimeUTC.datetime_to_timestamp(t["createdAt"])
    return t
