import logging
import time
from contextlib import asynccontextmanager  # 用于创建异步上下文管理器。
import psycopg_pool  # 用于数据库连接池管理。
from apscheduler.schedulers.asyncio import AsyncIOScheduler  # 用于任务调度。
from decouple import config  # 用于读取环境变量。
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
# TODO 为什么要使用异步 有什么好处 同步不行吗
from psycopg import AsyncConnection
from starlette.responses import StreamingResponse  # 用于流式响应。
from chalicelib.utils import helper
from chalicelib.utils import pg_client
from crons import core_crons, core_dynamic_crons
from routers import core, core_dynamic, additional_routes
from routers.subs import insights, metrics, v1_api, health, usability_tests

# 设置日志记录的级别 默认值只有
loglevel = config("LOGLEVEL", default=logging.WARNING)
# 低于此日志级别件不会打印日志
print(f">日志级别设置为: {loglevel}")
logging.basicConfig(level=loglevel)

from psycopg.rows import dict_row


# 定义一个继承自AsyncConnection的异步数据库连接类，使用dict_row作为行工厂，这样每行数据将以字典形式返回。
class ORPYAsyncConnection(AsyncConnection):
    # *args: 用于捕获额外的未命名位置参数，结果为一个元组。
    # **kwargs: 用于捕获额外的关键字参数，结果为一个字典。
    # 关键字参数: 可以在定义函数时为某个参数提供默认值，调用时可以选择性地覆盖它
    # *args 将所有位置参数传递给父类的 __init__ 方法。
    # row_factory=dict_row 是一个关键字参数，直接传递给父类的 __init__ 方法，用于设置 row_factory。
    # **kwargs 将所有关键字参数传递给父类的 __init__ 方法。
    def __init__(self, *args, **kwargs):
        super().__init__(*args, row_factory=dict_row, **kwargs)


# 定义了一个异步上下文管理器lifespan，用于管理应用程序的生命周期：
# 启动时，初始化日志记录、调度器和数据库连接池。
# 为应用程序添加定时任务。
# 关闭时，关闭数据库连接池和调度器。
# TODO asynccontextmanager的原理是什么
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logging.info(">>>>> 启动 <<<<<")
    # apscheduler 调度程序
    # 用于获取一个名为 apscheduler 的日志记录器（logger）对象,如果该日志记录器不存在，logging 会自动创建一个。
    # apscheduler 是一个用于 Python 的高级调度库，它会生成日志来记录调度任务的执行情况和状态。通过获取名为 "apscheduler" 的日志记录器，
    # 可以对 apscheduler 生成的日志进行配置和管理
    ap_logger = logging.getLogger("apscheduler")
    ap_logger.setLevel(loglevel)

    app.schedule = AsyncIOScheduler()  # 异步调度任务

    await pg_client.init()
    app.schedule.start()

    for job in core_crons.cron_jobs + core_dynamic_crons.cron_jobs:
        # TODO add_job的使用
        # **job解包
        app.schedule.add_job(id=job["func"].__name__, **job)

    ap_logger.info(">调度工作:")
    for job in app.schedule.get_jobs():
        ap_logger.info(
            {
                "Name": str(job.id),
                "Run Frequency": str(job.trigger),
                "Next Run": str(job.next_run_time),
            }
        )

    database = {
        "host": config("pg_host", default="localhost"),
        "dbname": config("pg_dbname", default="orpy"),
        "user": config("pg_user", default="orpy"),
        "password": config("pg_password", default="orpy"),
        "port": config("pg_port", cast=int, default=5432),
        "application_name": "AIO" + config("APP_NAME", default="PY"),
    }

    database = psycopg_pool.AsyncConnectionPool(
        kwargs=database,
        connection_class=ORPYAsyncConnection,
        min_size=config("PG_AIO_MINCONN", cast=int, default=1),
        max_size=config("PG_AIO_MAXCONN", cast=int, default=5),
    )
    app.state.postgresql = database

    # App listening
    yield

    # Shutdown
    await database.close()
    logging.info(">>>>> 关闭 <<<<<")
    app.schedule.shutdown(wait=False)
    await pg_client.terminate()


# 创建FastAPI应用实例，并添加GZip中间件以压缩大于1000字节的响应。
app = FastAPI(
    root_path=config("root_path", default="/api"),  # 为所有请求路径添加一个=前缀
    docs_url=config("docs_url", default=""),
    redoc_url=config("redoc_url", default=""),
    lifespan=lifespan,
)
app.add_middleware(GZipMiddleware, minimum_size=1000)


# 定义一个http中间件，用于记录请求处理时间、捕获和记录异常、警告非2xx响应，并添加x-robots-tag头以防止搜索引擎索引。
@app.middleware("http")
async def or_middleware(request: Request, call_next):
    if helper.TRACK_TIME:
        now = time.time()
    try:
        response: StreamingResponse = await call_next(request)
    except:
        logging.error(f"{request.method}: {request.url.path} FAILED!")
        raise
    if response.status_code // 100 != 2:
        logging.warning(f"{request.method}:{request.url.path} {response.status_code}!")
    if helper.TRACK_TIME:
        now = time.time() - now
        if now > 2:
            now = round(now, 2)
            logging.warning(f"Execution time: {now} s for {request.method}: {request.url.path}")
    response.headers["x-robots-tag"] = "noindex, nofollow"
    return response


# 添加CORS中间件，允许所有来源的跨域请求。
origins = [
    "*",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# 将不同模块的路由器注册到应用程序中。
app.include_router(core.public_app)
app.include_router(core.app)
app.include_router(core.app_apikey)
app.include_router(core_dynamic.public_app)
app.include_router(core_dynamic.app)
app.include_router(core_dynamic.app_apikey)
app.include_router(metrics.app)
app.include_router(insights.app)
app.include_router(v1_api.app_apikey)
app.include_router(health.public_app)
app.include_router(health.app)
app.include_router(health.app_apikey)

app.include_router(usability_tests.public_app)
app.include_router(usability_tests.app)
app.include_router(usability_tests.app_apikey)

app.include_router(additional_routes.app)

# 注释掉的部分代码是一个用于关闭服务器的API端点，但当前未启用：
# @app.get('/private/shutdown', tags=["private"])
# async def stop_server():
#     logging.info("Requested shutdown")
#     await shutdown()
#     import os, signal
#     os.kill(1, signal.SIGTERM)
