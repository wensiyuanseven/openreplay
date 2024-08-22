from decouple import config
from fastapi import HTTPException, status

from chalicelib.core import health, tenants
from routers.base import get_routers

public_app, app, app_apikey = get_routers()


# 功能: 检查应用程序的全局健康状态。
# 逻辑:
# 首先检查是否在本地开发环境中运行 (LOCAL_DEV 环境变量)。
# 如果是在本地开发环境中，返回一个空的 data 字段。
# 如果不是本地开发环境，则调用 health.get_health() 获取健康状态，并将其作为 data 字段返回。
@app.get("/healthz", tags=["health-check"])
def get_global_health_status():
    if config("LOCAL_DEV", cast=bool, default=False):
        return {"data": ""}
    return {"data": health.get_health()}


# 功能: 这是一个公共的健康检查，仅在没有租户存在的情况下使用。
# 逻辑:
# 在应用启动时检查是否有租户 (tenants.tenants_exists_sync(use_pool=False))，如果没有租户存在，定义此端点。
# 当请求 /health 时，它会异步检查是否存在租户 (await tenants.tenants_exists())，如果租户存在，则抛出 404 错误 (Not Found)，否则返回健康状态。
if not tenants.tenants_exists_sync(use_pool=False):

    @public_app.get("/health", tags=["health-check"])
    async def get_public_health_status():
        if await tenants.tenants_exists():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Not Found")

        return {"data": health.get_health()}
