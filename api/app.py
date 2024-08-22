# 这个代码片段实现了一个使用 FastAPI 构建的异步 Web 应用程序，并集成了多个功能模块。应用使用了异步上下文管理器来管理应用的生命周期，并通过 APScheduler 实现了异步任务调度。数据库连接池使用了 psycopg_pool 进行管理，确保高效的数据库连接处理。
# 代码还配置了多种中间件，包括 HTTP 请求处理、CORS 支持、GZip 压缩等，确保应用的性能、安全性和跨域支持。
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

# 描述: 这是一个继承自 AsyncConnection 的异步数据库连接类，使用 dict_row 作为行工厂，使得数据库查询结果以字典形式返回。
# 作用: 在执行查询时，每一行数据将以字典的形式返回，这样可以更方便地访问数据。
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



# 描述: 一个异步上下文管理器，管理应用程序的生命周期，包括启动时的初始化操作和关闭时的清理操作。
# 启动时:
# 初始化日志记录器。
# 启动 APScheduler 调度器。
# 初始化数据库连接池 psycopg_pool.AsyncConnectionPool。
# 注册定时任务，并记录调度信息。
# 关闭时:
# 关闭数据库连接池和调度器。
# 记录关闭日志。
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

# 描述: 创建了一个 FastAPI 应用实例，并配置了多个中间件和路由器。
# 功能:
# GZip 压缩: 使用 GZipMiddleware 对大于 1000 字节的响应进行压缩，减少网络传输时间。
# CORS 支持: 使用 CORSMiddleware 允许跨域请求，支持所有来源。
# HTTP 请求中间件: 用于记录请求处理时间、捕获和记录异常、警告非 2xx 响应，并添加 x-robots-tag 头以防止搜索引擎索引。
# 创建FastAPI应用实例，并添加GZip中间件以压缩大于1000字节的响应。
app = FastAPI(
    root_path=config("root_path", default="/api"),  # 为所有请求路径添加一个=前缀
    docs_url=config("docs_url", default=""),
    redoc_url=config("redoc_url", default=""),
    lifespan=lifespan,
)

# 添加 x-robots-tag 头，防止搜索引擎对响应内容进行索引。
app.add_middleware(GZipMiddleware, minimum_size=1000)


# 描述: 定义了一个 HTTP 请求中间件，处理每个请求的日志记录、异常处理和性能监控。
# 功能:
# 记录请求的处理时间，如果处理时间超过 2 秒，则记录警告日志。
# 在请求处理期间发生异常时，记录错误日志。
# 为所有非 2xx 响应记录警告日志。

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


# 这个代码片段通过结合异步编程、任务调度、数据库连接池和中间件，为构建高性能、可扩展的 Web 应用程序提供了坚实的基础。异步任务调度确保了应用能够处理高并发的定时任务，而异步数据库连接则提高了数据库操作的效率。通过丰富的中间件支持，应用能够在保证性能的同时，提供良好的用户体验和跨域支持。
