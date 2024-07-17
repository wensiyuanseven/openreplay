import logging  # 导入日志记录模块

from fastapi import Request  # 导入 FastAPI 的 Request 类，用于处理 HTTP 请求
from starlette import status  # 导入 Starlette 的 status 模块，包含 HTTP 状态码的定义
from starlette.exceptions import HTTPException  # 导入 Starlette 的 HTTPException 异常类

import schemas  # 导入 schemas 模块，用于数据结构和验证
from chalicelib.core import projects  # 导入项目核心功能模块或包
from or_dependencies import OR_context  # 导入 OR_context 函数，用于获取请求的上下文信息

logger = logging.getLogger(__name__)  # 创建日志记录器对象，名称与当前模块或脚本的名称相同


class ProjectAuthorizer:
    def __init__(self, project_identifier):
        self.project_identifier: str = project_identifier   # 初始化项目标识符

    async def __call__(self, request: Request) -> None:
        if len(request.path_params.keys()) == 0 or request.path_params.get(self.project_identifier) is None:
            return

        # 获取当前用户的上下文信息
        current_user: schemas.CurrentContext = await OR_context(request)
        value = request.path_params[self.project_identifier]  # 获取指定的项目标识符的值
        current_project = None
        if self.project_identifier == "projectId" and (isinstance(value, int) or isinstance(value, str) and value.isnumeric()):
            # 传参可不按顺序指定
            current_project = projects.get_project(
                project_id=value, tenant_id=current_user.tenant_id)

        elif self.project_identifier == "projectKey":
            current_project = projects.get_by_project_key(project_key=value)

        if current_project is None:
            # 未授权
            logger.debug(
                f"unauthorized project {self.project_identifier}:{value}")
            # 抛出异常
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="project not found.")
        else:
            current_project = schemas.CurrentProjectContext(projectId=current_project["projectId"],
                                                            projectKey=current_project["projectKey"],
                                                            platform=current_project["platform"],
                                                            name=current_project["name"])
            request.state.currentContext.project = current_project
