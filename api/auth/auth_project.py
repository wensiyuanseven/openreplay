# 这个文件定义了一个 ProjectAuthorizer 类，用于在 FastAPI 路由中进行项目授权检查。
# 其主要功能是确保每个请求与合法的项目相关联。如果请求路径中包含项目标识符（如项目 ID 或项目 Key），ProjectAuthorizer 将验证该项目的存在性，并在验证成功时将项目信息存储在请求的上下文中。
# 这对于需要根据项目进行访问控制的 API 端点非常有用。
import logging

from fastapi import Request
from starlette import status
from starlette.exceptions import HTTPException

import schemas
from chalicelib.core import projects
from or_dependencies import OR_context

logger = logging.getLogger(__name__)


class ProjectAuthorizer:
    #  作用：该方法用于初始化 ProjectAuthorizer 实例，接受一个项目标识符作为参数（如 projectId 或 projectKey）。
    # 参数：project_identifier (str)：项目标识符，可能是路径参数中的 projectId 或 projectKey，用于标识请求中与项目相关的参数名。
    def __init__(self, project_identifier):
        self.project_identifier: str = project_identifier

    # 作用：该方法是类的核心功能，它通过检查请求中的项目标识符（如 projectId 或 projectKey），验证当前用户是否有权访问该项目。此方法会被 FastAPI 的依赖注入机制自动调用。
    # 参数：
    # request (Request)：FastAPI 中的请求对象。它包含请求的路径参数、用户上下文等信息。
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
