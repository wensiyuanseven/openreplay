# 该代码实现了一个 ProjectAuthorizer 类，用于在 FastAPI 应用中进行项目授权。该类通过 __call__ 方法验证请求的路径参数中是否包含指定的项目标识符（如 projectId 或 projectKey），
# 并根据该标识符从数据库中获取相应的项目数据。如果项目存在，将其添加到请求的上下文中；如果项目不存在，则抛出 404 错误。
import logging

from fastapi import Request
from starlette import status
from starlette.exceptions import HTTPException

import schemas
from chalicelib.core import projects
from or_dependencies import OR_context

logger = logging.getLogger(__name__)


# 定义一个用于项目授权的类
class ProjectAuthorizer:
    # 初始化 ProjectAuthorizer 类的实例
    # 参数：
    # - project_identifier: 字符串类型，表示项目标识符的名称（如 "projectId" 或 "projectKey"）
    def __init__(self, project_identifier):
        self.project_identifier: str = project_identifier

    # 定义一个异步调用方法，用于在请求中进行项目授权
    # 参数：
    # - request: FastAPI 的 Request 对象，表示当前请求
    # 返回值：
    # - None，直接修改请求的上下文或抛出异常
    async def __call__(self, request: Request) -> None:
        if len(request.path_params.keys()) == 0 or request.path_params.get(self.project_identifier) is None:
            return
        current_user: schemas.CurrentContext = await OR_context(request)
        value = request.path_params[self.project_identifier]
        current_project = None
        if self.project_identifier == "projectId" and (isinstance(value, int) or isinstance(value, str) and value.isnumeric()):
            current_project = projects.get_project(project_id=value, tenant_id=current_user.tenant_id)
        elif self.project_identifier == "projectKey":
            current_project = projects.get_by_project_key(project_key=value)

        if current_project is None:
            logger.debug(f"unauthorized project {self.project_identifier}:{value}")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="project not found.")
        else:
            current_project = schemas.CurrentProjectContext(projectId=current_project["projectId"], projectKey=current_project["projectKey"], platform=current_project["platform"], name=current_project["name"])
            request.state.currentContext.project = current_project


# 文件作用
# 该文件实现了基于API密钥的身份验证机制。通过提供的API密钥（通常在请求头中），系统可以验证请求的合法性，并决定是否允许用户访问API资源。具体来说，该文件通过继承APIKeyHeader，并自定义其行为，来处理API密钥的认证流程。

# 类及方法描述
# APIKeyAuth
# 描述:
# 这是一个自定义的API密钥认证类，继承自FastAPI的APIKeyHeader类。它通过解析请求头中的Authorization字段获取API密钥，并调用内部验证逻辑检查密钥的有效性。

# __init__
# 描述:
# 初始化APIKeyAuth类，设置请求头中用于存放API密钥的字段（即Authorization），并决定是否自动抛出错误。

# 参数:

# auto_error (bool): 当为True时，如果认证失败将自动抛出HTTP 401错误；否则将返回None。
# __call__
# 描述:
# 该方法会在每次请求时调用，用于验证请求头中的API密钥。它首先从请求头中获取Authorization字段的值，然后调用authorizers.api_key_authorizer来检查密钥的有效性。如果密钥无效，则会抛出HTTP 401 Unauthorized错误。

# 参数:

# request (Request): FastAPI请求对象，表示当前的HTTP请求。
# 返回值:

# Optional[CurrentAPIContext]: 如果认证成功，返回包含当前请求上下文的对象CurrentAPIContext，否则抛出HTTP错误。
# 函数执行逻辑
# 获取API密钥:

# 系统通过Authorization请求头字段获取API密钥。
# 验证API密钥:

# 使用authorizers.api_key_authorizer(api_key)函数对密钥进行验证。该函数会检查密钥的有效性并返回与该密钥相关的租户信息。
# 认证成功:

# 如果验证成功，系统会将认证身份（即api_key）记录到请求的状态中，并设置当前的API上下文（即CurrentAPIContext），包含租户ID等信息。
# 认证失败:

# 如果密钥验证失败，则会抛出HTTP 401 Unauthorized错误，并返回"Invalid API Key"的详细信息。
# 核心逻辑总结
# API密钥验证: 系统通过请求头中的API密钥来验证请求的合法性。
# 上下文设置: 在验证通过后，系统会设置当前请求的API上下文信息，并将其传递给后续处理程序。
# 错误处理: 如果API密钥无效，系统会返回401 Unauthorized错误，提示API密钥无效。
# 使用场景
# 该类主要用于保护需要API密钥的API接口。通过APIKeyAuth类，开发者可以为API添加一层安全保护，确保只有合法的API密钥持有者才能访问指定的资源或接口。
