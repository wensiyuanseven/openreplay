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



# 这个代码片段定义了一个 `get_routers()` 函数，用于创建和配置三个不同的 `APIRouter` 对象，它们代表了三种不同的 API 路由集，每个路由集都有各自的身份验证和授权方式。

# ### 具体说明：

# 1. **导入的模块和依赖项**：
#     - `APIRouter`: FastAPI 中用于组织和管理一组 API 路由的类。
#     - `Depends`: FastAPI 中用于依赖注入的工具，声明某个路由的依赖关系。
#     - `APIKeyAuth`, `JWTAuth`, `ProjectAuthorizer`: 这些是自定义的身份验证类或函数，负责不同的身份验证和项目授权逻辑。
#     - `ORRoute`: 自定义的路由类，扩展了 FastAPI 的 `APIRoute`，可能添加了日志或异常处理等功能。

# 2. **函数 `get_routers()`**：
#     - 返回一个包含三个不同 `APIRouter` 对象的元组，它们分别是 `public_app`, `app`, 和 `app_apikey`。
#     - 这三个路由器对象各自使用不同的身份验证方式，目的是为不同的访问权限场景提供路由。

# 3. **三个 `APIRouter` 对象的配置**：
#    - **`public_app`**:
#      - 这是一个公开的 API 路由集，使用了 `ORRoute` 作为路由类，但没有附加任何身份验证依赖，通常用于不需要身份验证的 API 路由。

#    - **`app`**:
#      - 这个路由集配置了 `JWTAuth()` 和 `ProjectAuthorizer("projectId")` 作为依赖。也就是说，使用这些 API 路由时，需要进行 JWT 验证和项目授权检查（通过 `projectId`），适用于登录用户和项目级别的权限控制。

#    - **`app_apikey`**:
#      - 这个路由集配置了 `APIKeyAuth()` 和 `ProjectAuthorizer("projectKey")` 作为依赖。这意味着调用这些 API 路由需要使用 API Key 进行身份验证，并且基于项目的 `projectKey` 来进行授权检查，适合于 API key 访问控制场景。

# 4. **`extra_dependencies`**:
#    - `extra_dependencies` 是一个可选参数，用于在创建 `APIRouter` 时附加额外的依赖项。这让函数更灵活，因为你可以为不同的场景添加更多的依赖。

# 5. **返回值**：
#    - 该函数返回一个元组，包含三个 `APIRouter` 对象：`public_app`, `app`, 和 `app_apikey`。这些对象可以通过 `FastAPI` 的 `include_router()` 方法包含到主应用中，分别用于公开路由、JWT 身份验证路由、API Key 身份验证路由。

# ### 总结：
# 这个代码片段通过 `APIRouter` 对象和 `Depends` 依赖注入，组织了不同访问权限的路由集。
