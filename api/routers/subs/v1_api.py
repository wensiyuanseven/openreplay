from fastapi import Depends, Body

import schemas
from chalicelib.core import sessions, events, jobs, projects
from or_dependencies import OR_context
from routers.base import get_routers

public_app, app, app_apikey = get_routers()


@app_apikey.get('/v1/{projectKey}/users/{userId}/sessions', tags=["api"])
def get_user_sessions(projectKey: str, userId: str, start_date: int = None, end_date: int = None,
                      context: schemas.CurrentContext = Depends(OR_context)):
    return {
        "data": sessions.get_user_sessions(
            project_id=context.project.project_id,
            user_id=userId,
            start_date=start_date,
            end_date=end_date
        )
    }


@app_apikey.get('/v1/{projectKey}/sessions/{sessionId}/events', tags=["api"])
def get_session_events(projectKey: str, sessionId: int, context: schemas.CurrentContext = Depends(OR_context)):
    return {
        "data": events.get_by_session_id(
            project_id=context.project.project_id,
            session_id=sessionId
        )
    }


@app_apikey.get('/v1/{projectKey}/users/{userId}', tags=["api"])
def get_user_details(projectKey: str, userId: str, context: schemas.CurrentContext = Depends(OR_context)):
    return {
        "data": sessions.get_session_user(
            project_id=context.project.project_id,
            user_id=userId
        )
    }


@app_apikey.delete('/v1/{projectKey}/users/{userId}', tags=["api"])
def schedule_to_delete_user_data(projectKey: str, userId: str, _=Body(None),
                                 context: schemas.CurrentContext = Depends(OR_context)):
    record = jobs.create(project_id=context.project.project_id, user_id=userId)
    return {"data": record}


@app_apikey.get('/v1/{projectKey}/jobs', tags=["api"])
def get_jobs(projectKey: str, context: schemas.CurrentContext = Depends(OR_context)):
    return {"data": jobs.get_all(project_id=context.project.project_id)}


@app_apikey.get('/v1/{projectKey}/jobs/{jobId}', tags=["api"])
def get_job(projectKey: str, jobId: int, context: schemas.CurrentContext = Depends(OR_context)):
    return {"data": jobs.get(job_id=jobId, project_id=context.project.project_id)}


@app_apikey.delete('/v1/{projectKey}/jobs/{jobId}', tags=["api"])
def cancel_job(projectKey: str, jobId: int, _=Body(None), context: schemas.CurrentContext = Depends(OR_context)):
    job = jobs.get(job_id=jobId, project_id=context.project.project_id)
    job_not_found = len(job.keys()) == 0

    if job_not_found:
        return {"errors": ["Job not found."]}
    if job["status"] == jobs.JobStatus.COMPLETED or job["status"] == jobs.JobStatus.CANCELLED:
        return {"errors": ["The request job has already been canceled/completed."]}

    job["status"] = "cancelled"
    return {"data": jobs.update(job_id=jobId, job=job)}


@app_apikey.get('/v1/projects', tags=["api"])
def get_projects(context: schemas.CurrentContext = Depends(OR_context)):
    records = projects.get_projects(tenant_id=context.tenant_id)
    for record in records:
        del record['projectId']

    return {"data": records}


@app_apikey.get('/v1/projects/{projectKey}', tags=["api"])
def get_project(projectKey: str, context: schemas.CurrentContext = Depends(OR_context)):
    return {
        "data": projects.get_by_project_key(project_key=projectKey)
    }


@app_apikey.post('/v1/projects', tags=["api"])
def create_project(data: schemas.CreateProjectSchema = Body(...),
                   context: schemas.CurrentContext = Depends(OR_context)):
    record = projects.create(
        tenant_id=context.tenant_id,
        user_id=None,
        data=data,
        skip_authorization=True
    )
    del record["data"]['projectId']
    return record


# API Endpoints
# get_user_sessions
# 路径: /v1/{projectKey}/users/{userId}/sessions
# 方法: GET
# 功能: 获取指定用户在项目中的所有会话信息。
# 参数:
# projectKey (str): 项目的唯一标识符。
# userId (str): 用户的唯一标识符。
# start_date (int, 可选): 开始日期时间戳（可选）。
# end_date (int, 可选): 结束日期时间戳（可选）。
# context (schemas.CurrentContext): 当前请求的上下文信息，用于识别项目ID和用户ID。
# get_session_events
# 路径: /v1/{projectKey}/sessions/{sessionId}/events
# 方法: GET
# 功能: 获取指定会话的所有事件。
# 参数:
# projectKey (str): 项目的唯一标识符。
# sessionId (int): 会话的唯一标识符。
# context (schemas.CurrentContext): 当前请求的上下文信息。
# get_user_details
# 路径: /v1/{projectKey}/users/{userId}
# 方法: GET
# 功能: 获取指定用户的详细信息。
# 参数:
# projectKey (str): 项目的唯一标识符。
# userId (str): 用户的唯一标识符。
# context (schemas.CurrentContext): 当前请求的上下文信息。
# schedule_to_delete_user_data
# 路径: /v1/{projectKey}/users/{userId}
# 方法: DELETE
# 功能: 安排删除指定用户的数据。
# 参数:
# projectKey (str): 项目的唯一标识符。
# userId (str): 用户的唯一标识符。
# context (schemas.CurrentContext): 当前请求的上下文信息。
# get_jobs
# 路径: /v1/{projectKey}/jobs
# 方法: GET
# 功能: 获取与项目相关的所有任务。
# 参数:
# projectKey (str): 项目的唯一标识符。
# context (schemas.CurrentContext): 当前请求的上下文信息。
# get_job
# 路径: /v1/{projectKey}/jobs/{jobId}
# 方法: GET
# 功能: 获取特定任务的详细信息。
# 参数:
# projectKey (str): 项目的唯一标识符。
# jobId (int): 任务的唯一标识符。
# context (schemas.CurrentContext): 当前请求的上下文信息。
# cancel_job
# 路径: /v1/{projectKey}/jobs/{jobId}
# 方法: DELETE
# 功能: 取消指定任务。
# 参数:
# projectKey (str): 项目的唯一标识符。
# jobId (int): 任务的唯一标识符。
# context (schemas.CurrentContext): 当前请求的上下文信息。
# get_projects
# 路径: /v1/projects
# 方法: GET
# 功能: 获取租户下的所有项目。
# 参数:
# context (schemas.CurrentContext): 当前请求的上下文信息。
# get_project
# 路径: /v1/projects/{projectKey}
# 方法: GET
# 功能: 获取指定项目的详细信息。
# 参数:
# projectKey (str): 项目的唯一标识符。
# context (schemas.CurrentContext): 当前请求的上下文信息。
# create_project
# 路径: /v1/projects
# 方法: POST
# 功能: 创建一个新项目。
# 参数:
# data (schemas.CreateProjectSchema): 包含新项目数据的对象。
# context (schemas.CurrentContext): 当前请求的上下文信息。





