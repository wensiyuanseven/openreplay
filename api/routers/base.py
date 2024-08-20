# APIRouter用于将一组路由组织在一起，从而方便地管理和复用这些路由，然后过 include_router 将 router 集成到 FastAPI 主应用
# Depends 是 FastAPI 中用于依赖注入的函数或类，用来声明路径操作函数（API端点）的依赖项。依赖项可以是数据库连接、身份验证检查、请求参数验证等。
from fastapi import APIRouter, Depends

from auth.auth_apikey import APIKeyAuth
from auth.auth_jwt import JWTAuth
from auth.auth_project import ProjectAuthorizer
from or_dependencies import ORRoute



# 创建和配置三个不同的API路由集（APIRouter对象），每个路由集使用不同的身份验证和授权方式
def get_routers(extra_dependencies=[]) -> tuple[APIRouter, APIRouter, APIRouter]:

    public_app = APIRouter(route_class=ORRoute)

    app = APIRouter(
        dependencies=[Depends(JWTAuth()), Depends(ProjectAuthorizer("projectId"))]
        + extra_dependencies,
        route_class=ORRoute,
    )

    app_apikey = APIRouter(
        dependencies=[Depends(APIKeyAuth()), Depends(ProjectAuthorizer("projectKey"))]
        + extra_dependencies,
        route_class=ORRoute,
    )

    return public_app, app, app_apikey
