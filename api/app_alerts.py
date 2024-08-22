# 这个代码片段定义了一个使用 FastAPI 构建的微服务应用，用于处理基于时间调度的告警任务。
# 应用在启动时初始化 PostgreSQL 数据库连接，并配置一个 AsyncIOScheduler 调度器来周期性地执行告警处理任务。
# 代码还包括基本的健康检查端点，以及在开发模式下手动触发主要告警任务的功能。日志记录功能也集成在应用中，用于跟踪系统运行状态和调度任务执行情况。
import logging
from contextlib import asynccontextmanager

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from decouple import config
from fastapi import FastAPI

from chalicelib.core import alerts_processor
from chalicelib.utils import pg_client

# 描述: 一个异步上下文管理器，定义了应用的生命周期管理，负责在应用启动和关闭时执行相应的初始化和清理操作。
# 启动时:
# 记录启动日志。
# 初始化 PostgreSQL 客户端。
# 启动调度器并添加告警处理任务，该任务按照配置的时间间隔定期运行。
# 打印所有已调度任务的信息。
# 关闭时:
# 记录关闭日志。
# 停止调度器，并关闭 PostgreSQL 客户端连接。
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logging.info(">>>>> starting up <<<<<")
    await pg_client.init()
    app.schedule.start()
    app.schedule.add_job(id="alerts_processor", **{"func": alerts_processor.process, "trigger": "interval",
                                                   "minutes": config("ALERTS_INTERVAL", cast=int, default=5),
                                                   "misfire_grace_time": 20})

    ap_logger.info(">Scheduled jobs:")
    for job in app.schedule.get_jobs():
        ap_logger.info({"Name": str(job.id), "Run Frequency": str(job.trigger), "Next Run": str(job.next_run_time)})

    # App listening
    yield

    # Shutdown
    logging.info(">>>>> shutting down <<<<<")
    app.schedule.shutdown(wait=False)
    await pg_client.terminate()

# 描述: 初始化 FastAPI 应用实例，并配置应用的根路径、API 文档路径和生命周期管理器 lifespan。
# 参数:
# root_path: 应用的根路径，默认为/alerts。
# docs_url: FastAPI 自动生成的文档路径。
# redoc_url: ReDoc 文档路径。
# lifespan: 应用的生命周期管理器。
app = FastAPI(root_path=config("root_path", default="/alerts"), docs_url=config("docs_url", default=""),
              redoc_url=config("redoc_url", default=""), lifespan=lifespan)
logging.info("============= ALERTS =============")


# 描述: 定义了一个根路径的 GET 请求处理函数，返回应用的运行状态。
# 返回值: 返回一个包含 status 键和值为 Running 的字典。
@app.get("/")
async def root():
    return {"status": "Running"}

# 描述: 定义了一个健康检查端点，用于确认应用的健康状态。
# 返回值: 返回包含健康状态和应用版本信息的字典。
@app.get("/health")
async def get_health_status():
    return {"data": {
        "health": True,
        "details": {"version": config("version_number", default="unknown")}
    }}

# 描述: 初始化一个 AsyncIOScheduler 实例，用于调度和管理周期性任务。
# 作用:
# 该调度器用于在后台执行告警处理任务，并且可以在应用生命周期中启动和停止。
app.schedule = AsyncIOScheduler()

loglevel = config("LOGLEVEL", default=logging.INFO)
print(f">Loglevel set to: {loglevel}")
logging.basicConfig(level=loglevel)
ap_logger = logging.getLogger('apscheduler')
ap_logger.setLevel(loglevel)
app.schedule = AsyncIOScheduler()

if config("LOCAL_DEV", default=False, cast=bool):
    @app.get('/trigger', tags=["private"])
    async def trigger_main_cron():
        logging.info("Triggering main cron")
        alerts_processor.process()



# 这个 FastAPI 应用程序设计为一个可扩展的、易于管理的告警处理服务，通过调度器定期执行任务，确保及时处理系统中需要关注的告警信息。
# 同时，应用提供基本的健康检查和日志记录功能，方便运维人员监控和管理。通过结合生命周期管理器和调度器，应用在启动和关闭时能够高效地进行资源的初始化和清理，确保系统的稳定运行。