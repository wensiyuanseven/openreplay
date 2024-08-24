# 这个代码片段定义了一系列基于 FastAPI 的 API 端点，这些端点涉及到多个模块的集成和操作，如事件搜索、告警管理、元数据管理、集成管理、用户通知、项目管理等。
# 这些 API 端点通过依赖注入的方式获取当前上下文，并使用 Pydantic 的模式（schemas）来进行请求数据的验证和处理。
# 这个文件是一个完整的后端 API 实现，支持多个模块和功能的集成与操作。它通过 FastAPI 框架来处理 HTTP 请求，并使用 Pydantic 的数据验证功能来确保请求数据的正确性和安全性。
# 文件中涵盖了多个API端点，包括事件搜索、告警管理、元数据管理、用户通知管理、项目管理、集成管理等。
from typing import Union
from typing import Optional

from decouple import config
from fastapi import Depends, Body, BackgroundTasks

import schemas
from chalicelib.core import (
    log_tool_rollbar,
    sourcemaps,
    events,
    sessions_assignments,
    projects,
    alerts,
    issues,
    integrations_manager,
    metadata,
    log_tool_elasticsearch,
    log_tool_datadog,
    log_tool_stackdriver,
    reset_password,
    log_tool_cloudwatch,
    log_tool_sentry,
    log_tool_sumologic,
    log_tools,
    sessions,
    log_tool_newrelic,
    announcements,
    log_tool_bugsnag,
    weekly_report,
    integration_jira_cloud,
    integration_github,
    assist,
    mobile,
    tenants,
    boarding,
    notifications,
    webhook,
    users,
    custom_metrics,
    saved_search,
    integrations_global,
    tags,
)
from chalicelib.core.collaboration_msteams import MSTeams
from chalicelib.core.collaboration_slack import Slack
from or_dependencies import OR_context, OR_role
from routers.base import get_routers

public_app, app, app_apikey = get_routers()


# 描述: 允许用户基于项目 ID 和查询参数进行事件的自动完成和搜索。
# 参数:
# projectId: 项目 ID，用于指定查询所属的项目。
# q: 查询字符串，用于事件搜索。
# type: 事件类型，用于限定搜索范围。
# key: 事件的关键字，用于细化搜索条件。
# source: 事件的来源。
# live: 布尔值，指示是否在实时环境中搜索。
# 功能:
# 如果查询字符串为空，返回空结果。
# 根据不同的事件类型执行搜索，返回相应的搜索结果。
# {projectId} 是路径参数，表示在请求时会传入projectId

# 作用: 允许用户基于项目 ID 和查询参数进行事件的自动完成和搜索。
# 功能: 根据提供的查询参数搜索对应的事件，支持实时搜索和基于不同事件类型的搜索。

@app.get("/{projectId}/autocomplete", tags=["events"])
@app.get("/{projectId}/events/search", tags=["events"])
def events_search(
    projectId: int,
    q: str,
    type: Optional[
        Union[
            schemas.FilterType,
            schemas.EventType,
            schemas.PerformanceEventType,
            schemas.FetchFilterType,
            schemas.GraphqlFilterType,
            str,
        ]
    ] = None,
    key: Optional[str] = None,
    source: Optional[str] = None,
    live: bool = False,
    context: schemas.CurrentContext = Depends(OR_context),
):
    # 接口传枚举
    # 如果定义的只有枚举  那么打印出来的就是 <enum 'EventType'> EventType
    # 而如果既有字符串又有枚举，就像当前接口，那么打印出来的就是字符串，即使你传入的是字符串枚举，那么打印出来的也是字符串
    if len(q) == 0:
        return {"data": []}
    if live:
        # TODO 逻辑
        # 三元表达式 如果 key 不是 None，则返回 key 的值；否则返回 type。
        return assist.autocomplete(project_id=projectId, q=q, key=key if key is not None else type) # type: ignore
   # 接口调用 那前端传递的就是枚举字符串
    if type in [schemas.FetchFilterType._url]:
        type = schemas.EventType.request
    elif type in [schemas.GraphqlFilterType._name]:
        type = schemas.EventType.graphql
    elif isinstance(type, schemas.PerformanceEventType):
        if type in [
            schemas.PerformanceEventType.location_dom_complete,
            schemas.PerformanceEventType.location_largest_contentful_paint_time,
            schemas.PerformanceEventType.location_ttfb,
            schemas.PerformanceEventType.location_avg_cpu_load,
            schemas.PerformanceEventType.location_avg_memory_usage,
        ]:
            type = schemas.EventType.location
        elif type in [schemas.PerformanceEventType.fetch_failed]:
            type = schemas.EventType.request
        else:
            return {"data": []}

    result = events.search(text=q, event_type=type, project_id=projectId, source=source, key=key)
    return result


# 作用: 获取项目的集成状态。
# 功能: 根据项目 ID 获取当前项目的所有集成状态信息。
@app.get("/{projectId}/integrations", tags=["integrations"])
def get_integrations_status(projectId: int, context: schemas.CurrentContext = Depends(OR_context)):
    data = integrations_global.get_global_integrations_status(tenant_id=context.tenant_id, user_id=context.user_id, project_id=projectId)
    return {"data": data}


# 根据传入的 integration 和 source 类型，触发特定的通知到对应的集成（例如 Slack、Microsoft Teams）。该函数接受通知内容，并根据 sourceId 进行相应的处理和分享。
# 参数:
# projectId (int): 项目的唯一标识符。
# integration (str): 集成类型（如 Slack 或 Microsoft Teams）。
# webhookId (int): Webhook 的唯一标识符。
# source (str): 通知的源头，可能是 sessions 或 errors。
# sourceId (str): 具体的会话或错误的唯一标识符。
# data (schemas.IntegrationNotificationSchema): 通知的数据。
# context (schemas.CurrentContext): 当前请求的上下文，依赖于 OR_context。


@app.post(
    "/{projectId}/integrations/{integration}/notify/{webhookId}/{source}/{sourceId}",
    tags=["integrations"],
)
def integration_notify(
    projectId: int,
    integration: str,
    webhookId: int,
    source: str,
    sourceId: str,
    data: schemas.IntegrationNotificationSchema = Body(...),
    context: schemas.CurrentContext = Depends(OR_context),
):
    comment = None
    if data.comment:
        comment = data.comment

    args = {
        "tenant_id": context.tenant_id,
        "user": context.email,
        "comment": comment,
        "project_id": projectId,
        "integration_id": webhookId,
        "project_name": context.project.name,
    }
    if integration == schemas.WebhookType.slack:
        if source == "sessions":
            return Slack.share_session(session_id=sourceId, **args)
        elif source == "errors":
            return Slack.share_error(error_id=sourceId, **args)
    elif integration == schemas.WebhookType.msteams:
        if source == "sessions":
            return MSTeams.share_session(session_id=sourceId, **args)
        elif source == "errors":
            return MSTeams.share_error(error_id=sourceId, **args)
    return {"data": None}


# 获取当前租户下的所有 Sentry 集成信息。
# 参数:
# context (schemas.CurrentContext): 当前请求的上下文。
@app.get("/integrations/sentry", tags=["integrations"])
def get_all_sentry(context: schemas.CurrentContext = Depends(OR_context)):
    return {"data": log_tool_sentry.get_all(tenant_id=context.tenant_id)}


# 获取特定项目的 Sentry 集成信息。
# 参数:
# projectId (int): 项目的唯一标识符。
# context (schemas.CurrentContext): 当前请求的上下文。
@app.get("/{projectId}/integrations/sentry", tags=["integrations"])
def get_sentry(projectId: int, context: schemas.CurrentContext = Depends(OR_context)):
    return {"data": log_tool_sentry.get(project_id=projectId)}


# 为指定项目添加或编辑 Sentry 集成。
# 参数:
# projectId (int): 项目的唯一标识符。
# data (schemas.IntegrationSentrySchema): 包含 Sentry 集成的配置信息。
# context (schemas.CurrentContext): 当前请求的上下文，依赖于 OR_context，用于获取当前租户的上下文。
@app.post("/{projectId}/integrations/sentry", tags=["integrations"])
def add_edit_sentry(
    projectId: int,
    data: schemas.IntegrationSentrySchema = Body(...),
    context: schemas.CurrentContext = Depends(OR_context),
):
    return {"data": log_tool_sentry.add_edit(tenant_id=context.tenant_id, project_id=projectId, data=data)}


# 删除指定项目的 Sentry 集成。
# 参数:
# projectId (int): 项目的唯一标识符。
# context (schemas.CurrentContext): 当前请求的上下文，依赖于 OR_context，用于获取当前租户的上下文。
@app.delete("/{projectId}/integrations/sentry", tags=["integrations"])
def delete_sentry(projectId: int, _=Body(None), context: schemas.CurrentContext = Depends(OR_context)):
    return {"data": log_tool_sentry.delete(tenant_id=context.tenant_id, project_id=projectId)}


# 代理获取 Sentry 事件的详细信息。
# 参数:
# projectId (int): 项目的唯一标识符。
# eventId (str): Sentry 事件的唯一标识符。
# context (schemas.CurrentContext): 当前请求的上下文，依赖于 OR_context。


@app.get("/{projectId}/integrations/sentry/events/{eventId}", tags=["integrations"])
def proxy_sentry(projectId: int, eventId: str, context: schemas.CurrentContext = Depends(OR_context)):
    return {"data": log_tool_sentry.proxy_get(tenant_id=context.tenant_id, project_id=projectId, event_id=eventId)}


# 获取当前租户下的所有 Datadog 集成信息。

# 参数:


# context (schemas.CurrentContext): 当前请求的上下文，依赖于 OR_context。
@app.get("/integrations/datadog", tags=["integrations"])
def get_all_datadog(context: schemas.CurrentContext = Depends(OR_context)):
    return {"data": log_tool_datadog.get_all(tenant_id=context.tenant_id)}


# 获取指定项目的 Datadog 集成信息。

# 参数:

# projectId (int): 项目的唯一标识符。
# context (schemas.CurrentContext): 当前请求的上下文，依赖于 OR_context。


@app.get("/{projectId}/integrations/datadog", tags=["integrations"])
def get_datadog(projectId: int, context: schemas.CurrentContext = Depends(OR_context)):
    return {"data": log_tool_datadog.get(project_id=projectId)}


# 为指定项目添加或编辑 Datadog 集成。

# 参数:


# projectId (int): 项目的唯一标识符。
# data (schemas.IntegrationDatadogSchema): 包含 Datadog 集成的配置信息。
# context (schemas.CurrentContext): 当前请求的上下文，依赖于 OR_context。
@app.post("/{projectId}/integrations/datadog", tags=["integrations"])
def add_edit_datadog(
    projectId: int,
    data: schemas.IntegrationDatadogSchema = Body(...),
    context: schemas.CurrentContext = Depends(OR_context),
):
    return {"data": log_tool_datadog.add_edit(tenant_id=context.tenant_id, project_id=projectId, data=data)}


# 删除指定项目的 Datadog 集成。

# 参数:


# projectId (int): 项目的唯一标识符。
# context (schemas.CurrentContext): 当前请求的上下文，依赖于 OR_context。
@app.delete("/{projectId}/integrations/datadog", tags=["integrations"])
def delete_datadog(projectId: int, _=Body(None), context: schemas.CurrentContext = Depends(OR_context)):
    return {"data": log_tool_datadog.delete(tenant_id=context.tenant_id, project_id=projectId)}


# 获取当前租户下的所有 Stackdriver 集成信息。

# 参数:


# context (schemas.CurrentContext): 当前请求的上下文，依赖于 OR_context。
@app.get("/integrations/stackdriver", tags=["integrations"])
def get_all_stackdriver(context: schemas.CurrentContext = Depends(OR_context)):
    return {"data": log_tool_stackdriver.get_all(tenant_id=context.tenant_id)}


# 获取指定项目的 Stackdriver 集成信息。

# 参数:

# projectId (int): 项目的唯一标识符。
# context (schemas.CurrentContext): 当前请求的上下文，依赖于 OR_context。


@app.get("/{projectId}/integrations/stackdriver", tags=["integrations"])
def get_stackdriver(projectId: int, context: schemas.CurrentContext = Depends(OR_context)):
    return {"data": log_tool_stackdriver.get(project_id=projectId)}


# 为指定项目添加或编辑 Stackdriver 集成。

# 参数:


# projectId (int): 项目的唯一标识符。
# data (schemas.IntegartionStackdriverSchema): 包含 Stackdriver 集成的配置信息。
# context (schemas.CurrentContext): 当前请求的上下文，依赖于 OR_context。
@app.post("/{projectId}/integrations/stackdriver", tags=["integrations"])
def add_edit_stackdriver(
    projectId: int,
    data: schemas.IntegartionStackdriverSchema = Body(...),
    context: schemas.CurrentContext = Depends(OR_context),
):
    return {"data": log_tool_stackdriver.add_edit(tenant_id=context.tenant_id, project_id=projectId, data=data)}


# 删除指定项目的 Stackdriver 集成。

# 参数:


# projectId (int): 项目的唯一标识符。
# context (schemas.CurrentContext): 当前请求的上下文，依赖于 OR_context。
@app.delete("/{projectId}/integrations/stackdriver", tags=["integrations"])
def delete_stackdriver(projectId: int, _=Body(None), context: schemas.CurrentContext = Depends(OR_context)):
    return {"data": log_tool_stackdriver.delete(tenant_id=context.tenant_id, project_id=projectId)}


# 获取当前租户下的所有 New Relic 集成信息。

# 参数:

# context (schemas.CurrentContext): 当前请求的上下文，依赖于 OR_context。


@app.get("/integrations/newrelic", tags=["integrations"])
def get_all_newrelic(context: schemas.CurrentContext = Depends(OR_context)):
    return {"data": log_tool_newrelic.get_all(tenant_id=context.tenant_id)}


# 获取指定项目的 New Relic 集成信息。

# 参数:

# projectId (int): 项目的唯一标识符。
# context (schemas.CurrentContext): 当前请求的上下文，依赖于 OR_context。


@app.get("/{projectId}/integrations/newrelic", tags=["integrations"])
def get_newrelic(projectId: int, context: schemas.CurrentContext = Depends(OR_context)):
    return {"data": log_tool_newrelic.get(project_id=projectId)}


# 为指定项目添加或编辑 New Relic 集成。

# 参数:


# projectId (int): 项目的唯一标识符。
# data (schemas.IntegrationNewrelicSchema): 包含 New Relic 集成的配置信息。
# context (schemas.CurrentContext): 当前请求的上下文，依赖于 OR_context。
@app.post("/{projectId}/integrations/newrelic", tags=["integrations"])
def add_edit_newrelic(
    projectId: int,
    data: schemas.IntegrationNewrelicSchema = Body(...),
    context: schemas.CurrentContext = Depends(OR_context),
):
    return {"data": log_tool_newrelic.add_edit(tenant_id=context.tenant_id, project_id=projectId, data=data)}


# 删除指定项目的 New Relic 集成。

# 参数:


# projectId (int): 项目的唯一标识符。
# context (schemas.CurrentContext): 当前请求的上下文，依赖于 OR_context。
@app.delete("/{projectId}/integrations/newrelic", tags=["integrations"])
def delete_newrelic(projectId: int, _=Body(None), context: schemas.CurrentContext = Depends(OR_context)):
    return {"data": log_tool_newrelic.delete(tenant_id=context.tenant_id, project_id=projectId)}


# 获取当前租户下的所有 Rollbar 集成信息。
# 参数:
# context (schemas.CurrentContext): 当前请求的上下文，依赖于 OR_context。
@app.get("/integrations/rollbar", tags=["integrations"])
def get_all_rollbar(context: schemas.CurrentContext = Depends(OR_context)):
    return {"data": log_tool_rollbar.get_all(tenant_id=context.tenant_id)}


# 获取指定项目的 Rollbar 集成信息。

# 参数:


# projectId (int): 项目的唯一标识符。
# context (schemas.CurrentContext): 当前请求的上下文，依赖于 OR_context。
@app.get("/{projectId}/integrations/rollbar", tags=["integrations"])
def get_rollbar(projectId: int, context: schemas.CurrentContext = Depends(OR_context)):
    return {"data": log_tool_rollbar.get(project_id=projectId)}


# 为指定项目添加或编辑 Rollbar 集成。

# 参数:

# projectId (int): 项目的唯一标识符。
# data (schemas.IntegrationRollbarSchema): 包含 Rollbar 集成的配置信息。
# context (schemas.CurrentContext): 当前请求的上下文，依赖于 OR_context。


@app.post("/{projectId}/integrations/rollbar", tags=["integrations"])
def add_edit_rollbar(
    projectId: int,
    data: schemas.IntegrationRollbarSchema = Body(...),
    context: schemas.CurrentContext = Depends(OR_context),
):
    return {"data": log_tool_rollbar.add_edit(tenant_id=context.tenant_id, project_id=projectId, data=data)}


# 删除指定项目的 Rollbar 集成。

# 参数:

# projectId (int): 项目的唯一标识符。
# context (schemas.CurrentContext): 当前请求的上下文，依赖于 OR_context。


@app.delete("/{projectId}/integrations/rollbar", tags=["integrations"])
def delete_datadog(projectId: int, _=Body(None), context: schemas.CurrentContext = Depends(OR_context)):
    return {"data": log_tool_rollbar.delete(tenant_id=context.tenant_id, project_id=projectId)}


# 列出 Bugsnag 中的所有项目。

# 参数:

# data (schemas.IntegrationBugsnagBasicSchema): 包含授权信息的对象，用于访问 Bugsnag。
# context (schemas.CurrentContext): 当前请求的上下文，依赖于 OR_context。


@app.post("/integrations/bugsnag/list_projects", tags=["integrations"])
def list_projects_bugsnag(
    data: schemas.IntegrationBugsnagBasicSchema = Body(...),
    context: schemas.CurrentContext = Depends(OR_context),
):
    return {"data": log_tool_bugsnag.list_projects(auth_token=data.authorization_token)}


# 获取当前租户下的所有 Bugsnag 集成信息。

# 参数:

# context (schemas.CurrentContext): 当前请求的上下文，依赖于 OR_context。


@app.get("/integrations/bugsnag", tags=["integrations"])
def get_all_bugsnag(context: schemas.CurrentContext = Depends(OR_context)):
    return {"data": log_tool_bugsnag.get_all(tenant_id=context.tenant_id)}


# 获取指定项目的 Bugsnag 集成信息。

# 参数:


# projectId (int): 项目的唯一标识符。
# context (schemas.CurrentContext): 当前请求的上下文，依赖于 OR_context。
@app.get("/{projectId}/integrations/bugsnag", tags=["integrations"])
def get_bugsnag(projectId: int, context: schemas.CurrentContext = Depends(OR_context)):
    return {"data": log_tool_bugsnag.get(project_id=projectId)}


# 为指定项目添加或编辑 Bugsnag 集成。

# 参数:

# projectId (int): 项目的唯一标识符。
# data (schemas.IntegrationBugsnagSchema): 包含 Bugsnag 集成的配置信息。
# context (schemas.CurrentContext): 当前请求的上下文，依赖于 OR_context。


@app.post("/{projectId}/integrations/bugsnag", tags=["integrations"])
def add_edit_bugsnag(
    projectId: int,
    data: schemas.IntegrationBugsnagSchema = Body(...),
    context: schemas.CurrentContext = Depends(OR_context),
):
    return {"data": log_tool_bugsnag.add_edit(tenant_id=context.tenant_id, project_id=projectId, data=data)}


# 删除指定项目的 Bugsnag 集成。

# 参数:

# projectId (int): 项目的唯一标识符。
# context (schemas.CurrentContext): 当前请求的上下文，依赖于 OR_context。


@app.delete("/{projectId}/integrations/bugsnag", tags=["integrations"])
def delete_bugsnag(projectId: int, _=Body(None), context: schemas.CurrentContext = Depends(OR_context)):
    return {"data": log_tool_bugsnag.delete(tenant_id=context.tenant_id, project_id=projectId)}


# 列出 CloudWatch 中的所有日志组。

# 参数:


# data (schemas.IntegrationCloudwatchBasicSchema): 包含 CloudWatch 的认证信息（访问密钥 ID、密钥、区域）。
# context (schemas.CurrentContext): 当前请求的上下文，依赖于 OR_context。
@app.post("/integrations/cloudwatch/list_groups", tags=["integrations"])
def list_groups_cloudwatch(
    data: schemas.IntegrationCloudwatchBasicSchema = Body(...),
    context: schemas.CurrentContext = Depends(OR_context),
):
    return {
        "data": log_tool_cloudwatch.list_log_groups(
            aws_access_key_id=data.awsAccessKeyId,
            aws_secret_access_key=data.awsSecretAccessKey,
            region=data.region,
        )
    }


# 获取当前租户下所有的 CloudWatch 集成信息。

# 参数:

# context (schemas.CurrentContext): 当前请求的上下文，依赖于 OR_context。


@app.get("/integrations/cloudwatch", tags=["integrations"])
def get_all_cloudwatch(context: schemas.CurrentContext = Depends(OR_context)):
    return {"data": log_tool_cloudwatch.get_all(tenant_id=context.tenant_id)}


# 获取指定项目的 CloudWatch 集成信息。

# 参数:

# projectId (int): 项目的唯一标识符。
# context (schemas.CurrentContext): 当前请求的上下文，依赖于 OR_context。


@app.get("/{projectId}/integrations/cloudwatch", tags=["integrations"])
def get_cloudwatch(projectId: int, context: schemas.CurrentContext = Depends(OR_context)):
    return {"data": log_tool_cloudwatch.get(project_id=projectId)}


# 为指定项目添加或编辑 CloudWatch 集成。

# 参数:

# projectId (int): 项目的唯一标识符。
# data (schemas.IntegrationCloudwatchSchema): 包含 CloudWatch 集成的配置信息。
# context (schemas.CurrentContext): 当前请求的上下文，依赖于 OR_context。


@app.post("/{projectId}/integrations/cloudwatch", tags=["integrations"])
def add_edit_cloudwatch(
    projectId: int,
    data: schemas.IntegrationCloudwatchSchema = Body(...),
    context: schemas.CurrentContext = Depends(OR_context),
):
    return {"data": log_tool_cloudwatch.add_edit(tenant_id=context.tenant_id, project_id=projectId, data=data)}


# 删除指定项目的 CloudWatch 集成。

# 参数:

# projectId (int): 项目的唯一标识符。
# context (schemas.CurrentContext): 当前请求的上下文，依赖于 OR_context。


@app.delete("/{projectId}/integrations/cloudwatch", tags=["integrations"])
def delete_cloudwatch(projectId: int, _=Body(None), context: schemas.CurrentContext = Depends(OR_context)):
    return {"data": log_tool_cloudwatch.delete(tenant_id=context.tenant_id, project_id=projectId)}


# 获取当前租户下所有的 Elasticsearch 集成信息。

# 参数:

# context (schemas.CurrentContext): 当前请求的上下文，依赖于 OR_context。


@app.get("/integrations/elasticsearch", tags=["integrations"])
def get_all_elasticsearch(context: schemas.CurrentContext = Depends(OR_context)):
    return {"data": log_tool_elasticsearch.get_all(tenant_id=context.tenant_id)}


# 获取指定项目的 Elasticsearch 集成信息。

# 参数:

# projectId (int): 项目的唯一标识符。
# context (schemas.CurrentContext): 当前请求的上下文，依赖于 OR_context。


@app.get("/{projectId}/integrations/elasticsearch", tags=["integrations"])
def get_elasticsearch(projectId: int, context: schemas.CurrentContext = Depends(OR_context)):
    return {"data": log_tool_elasticsearch.get(project_id=projectId)}


# 测试 Elasticsearch 集成的连接性。

# 参数:


# data (schemas.IntegrationElasticsearchTestSchema): 包含测试连接的配置信息。
# context (schemas.CurrentContext): 当前请求的上下文，依赖于 OR_context。
@app.post("/integrations/elasticsearch/test", tags=["integrations"])
def test_elasticsearch_connection(
    data: schemas.IntegrationElasticsearchTestSchema = Body(...),
    context: schemas.CurrentContext = Depends(OR_context),
):
    return {"data": log_tool_elasticsearch.ping(tenant_id=context.tenant_id, data=data)}


# 为指定项目添加或编辑 Elasticsearch 集成。

# 参数:


# projectId (int): 项目的唯一标识符。
# data (schemas.IntegrationElasticsearchSchema): 包含 Elasticsearch 集成的配置信息。
# context (schemas.CurrentContext): 当前请求的上下文，依赖于 OR_context。
@app.post("/{projectId}/integrations/elasticsearch", tags=["integrations"])
def add_edit_elasticsearch(
    projectId: int,
    data: schemas.IntegrationElasticsearchSchema = Body(...),
    context: schemas.CurrentContext = Depends(OR_context),
):
    return {"data": log_tool_elasticsearch.add_edit(tenant_id=context.tenant_id, project_id=projectId, data=data)}


# 删除指定项目的 Elasticsearch 集成。

# 参数:

# projectId (int): 项目的唯一标识符。
# context (schemas.CurrentContext): 当前请求的上下文，依赖于 OR_context。


@app.delete("/{projectId}/integrations/elasticsearch", tags=["integrations"])
def delete_elasticsearch(projectId: int, _=Body(None), context: schemas.CurrentContext = Depends(OR_context)):
    return {"data": log_tool_elasticsearch.delete(tenant_id=context.tenant_id, project_id=projectId)}


# 获取当前租户下所有的 Sumo Logic 集成信息。

# 参数:

# context (schemas.CurrentContext): 当前请求的上下文，依赖于 OR_context。


@app.get("/integrations/sumologic", tags=["integrations"])
def get_all_sumologic(context: schemas.CurrentContext = Depends(OR_context)):
    return {"data": log_tool_sumologic.get_all(tenant_id=context.tenant_id)}


# 获取指定项目的 Sumo Logic 集成信息。

# 参数:


# projectId (int): 项目的唯一标识符。
# context (schemas.CurrentContext): 当前请求的上下文，依赖于 OR_context。
@app.get("/{projectId}/integrations/sumologic", tags=["integrations"])
def get_sumologic(projectId: int, context: schemas.CurrentContext = Depends(OR_context)):
    return {"data": log_tool_sumologic.get(project_id=projectId)}


# 为指定项目添加或编辑 Sumo Logic 集成。

# 参数:

# projectId (int): 项目的唯一标识符。
# data (schemas.IntegrationSumologicSchema): 包含 Sumo Logic 集成的配置信息。
# context (schemas.CurrentContext): 当前请求的上下文，依赖于 OR_context。


@app.post("/{projectId}/integrations/sumologic", tags=["integrations"])
def add_edit_sumologic(
    projectId: int,
    data: schemas.IntegrationSumologicSchema = Body(...),
    context: schemas.CurrentContext = Depends(OR_context),
):
    return {"data": log_tool_sumologic.add_edit(tenant_id=context.tenant_id, project_id=projectId, data=data)}


# 删除指定项目的 Sumo Logic 集成。

# 参数:

# projectId (int): 项目的唯一标识符。
# context (schemas.CurrentContext): 当前请求的上下文，依赖于 OR_context。


@app.delete("/{projectId}/integrations/sumologic", tags=["integrations"])
def delete_sumologic(projectId: int, _=Body(None), context: schemas.CurrentContext = Depends(OR_context)):
    return {"data": log_tool_sumologic.delete(tenant_id=context.tenant_id, project_id=projectId)}


# 获取当前租户下所有集成状态信息。

# 参数:

# context (schemas.CurrentContext): 当前请求的上下文，依赖于 OR_context。


@app.get("/integrations/issues", tags=["integrations"])
def get_integration_status(context: schemas.CurrentContext = Depends(OR_context)):
    error, integration = integrations_manager.get_integration(tenant_id=context.tenant_id, user_id=context.user_id)
    if error is not None and integration is None:
        return {"data": {}}
    return {"data": integration.get_obfuscated()}


# 获取 Jira 集成的状态信息。

# 参数:

# context (schemas.CurrentContext): 当前请求的上下文，依赖于 OR_context。


@app.get("/integrations/jira", tags=["integrations"])
def get_integration_status_jira(context: schemas.CurrentContext = Depends(OR_context)):
    error, integration = integrations_manager.get_integration(
        tenant_id=context.tenant_id,
        user_id=context.user_id,
        tool=integration_jira_cloud.PROVIDER,
    )
    if error is not None and integration is None:
        return error
    return {"data": integration.get_obfuscated()}


# 获取 GitHub 集成的状态信息。

# 参数:


# context (schemas.CurrentContext): 当前请求的上下文，依赖于 OR_context。
@app.get("/integrations/github", tags=["integrations"])
def get_integration_status_github(
    context: schemas.CurrentContext = Depends(OR_context),
):
    error, integration = integrations_manager.get_integration(
        tenant_id=context.tenant_id,
        user_id=context.user_id,
        tool=integration_github.PROVIDER,
    )
    if error is not None and integration is None:
        return error
    return {"data": integration.get_obfuscated()}


# 为当前租户添加或编辑 Jira 集成。

# 参数:


# data (schemas.IssueTrackingJiraSchema): 包含 Jira 集成的配置信息。
# context (schemas.CurrentContext): 当前请求的上下文，依赖于 OR_context。
@app.post("/integrations/jira", tags=["integrations"])
def add_edit_jira_cloud(
    data: schemas.IssueTrackingJiraSchema = Body(...),
    context: schemas.CurrentContext = Depends(OR_context),
):
    if not str(data.url).rstrip("/").endswith("atlassian.net"):
        return {"errors": ["url must be a valid JIRA URL (example.atlassian.net)"]}
    error, integration = integrations_manager.get_integration(
        tool=integration_jira_cloud.PROVIDER,
        tenant_id=context.tenant_id,
        user_id=context.user_id,
    )
    if error is not None and integration is None:
        return error
    return {"data": integration.add_edit(data=data)}


# 为当前租户添加或编辑 GitHub 集成。

# 参数:

# data (schemas.IssueTrackingGithubSchema): 包含 GitHub 集成的配置信息。
# context (schemas.CurrentContext): 当前请求的上下文，依赖于 OR_context。


@app.post("/integrations/github", tags=["integrations"])
def add_edit_github(
    data: schemas.IssueTrackingGithubSchema = Body(...),
    context: schemas.CurrentContext = Depends(OR_context),
):
    error, integration = integrations_manager.get_integration(
        tool=integration_github.PROVIDER,
        tenant_id=context.tenant_id,
        user_id=context.user_id,
    )
    if error is not None:
        return error
    return {"data": integration.add_edit(data=data)}


# 删除当前租户的默认问题跟踪工具。

# 参数:

# context (schemas.CurrentContext): 当前请求的上下文，依赖于 OR_context。


@app.delete("/integrations/issues", tags=["integrations"])
def delete_default_issue_tracking_tool(_=Body(None), context: schemas.CurrentContext = Depends(OR_context)):
    error, integration = integrations_manager.get_integration(tenant_id=context.tenant_id, user_id=context.user_id)
    if error is not None and integration is None:
        return error
    return {"data": integration.delete()}


# 删除当前租户的 Jira 集成。

# 参数:


# context (schemas.CurrentContext): 当前请求的上下文，依赖于 OR_context。
@app.delete("/integrations/jira", tags=["integrations"])
def delete_jira_cloud(_=Body(None), context: schemas.CurrentContext = Depends(OR_context)):
    error, integration = integrations_manager.get_integration(
        tool=integration_jira_cloud.PROVIDER,
        tenant_id=context.tenant_id,
        user_id=context.user_id,
        for_delete=True,
    )
    if error is not None:
        return error
    return {"data": integration.delete()}


# 删除当前租户的 GitHub 集成。

# 参数:


# context (schemas.CurrentContext): 当前请求的上下文，依赖于 OR_context。
@app.delete("/integrations/github", tags=["integrations"])
def delete_github(_=Body(None), context: schemas.CurrentContext = Depends(OR_context)):
    error, integration = integrations_manager.get_integration(
        tool=integration_github.PROVIDER,
        tenant_id=context.tenant_id,
        user_id=context.user_id,
        for_delete=True,
    )
    if error is not None:
        return error
    return {"data": integration.delete()}


# 获取当前租户下所有问题跟踪项目。

# 参数:


# context (schemas.CurrentContext): 当前请求的上下文，依赖于 OR_context。
@app.get("/integrations/issues/list_projects", tags=["integrations"])
def get_all_issue_tracking_projects(
    context: schemas.CurrentContext = Depends(OR_context),
):
    error, integration = integrations_manager.get_integration(tenant_id=context.tenant_id, user_id=context.user_id)
    if error is not None:
        return error
    data = integration.issue_handler.get_projects()
    if "errors" in data:
        return data
    return {"data": data}


# 获取指定问题跟踪项目的元数据。

# 参数:


# integrationProjectId (int): 问题跟踪项目的唯一标识符。
# context (schemas.CurrentContext): 当前请求的上下文，依赖于 OR_context。
@app.get("/integrations/issues/{integrationProjectId}", tags=["integrations"])
def get_integration_metadata(integrationProjectId: int, context: schemas.CurrentContext = Depends(OR_context)):
    error, integration = integrations_manager.get_integration(tenant_id=context.tenant_id, user_id=context.user_id)
    if error is not None:
        return error
    data = integration.issue_handler.get_metas(integrationProjectId)
    if "errors" in data.keys():
        return data
    return {"data": data}


# 获取指定项目的所有分配任务信息。

# 参数:

# projectId (int): 项目的唯一标识符。
# context (schemas.CurrentContext): 当前请求的上下文，依赖于 OR_context。


@app.get("/{projectId}/assignments", tags=["assignment"])
def get_all_assignments(projectId: int, context: schemas.CurrentContext = Depends(OR_context)):
    data = sessions_assignments.get_all(project_id=projectId, user_id=context.user_id)
    return {"data": data}


# 为指定会话创建新的问题分配任务。

# 参数:


# projectId (int): 项目的唯一标识符。
# sessionId (int): 会话的唯一标识符。
# integrationProjectId (int): 集成项目的唯一标识符。
# data (schemas.AssignmentSchema): 包含任务分配信息的数据。
# context (schemas.CurrentContext): 当前请求的上下文，依赖于 OR_context。
@app.post(
    "/{projectId}/sessions/{sessionId}/assign/projects/{integrationProjectId}",
    tags=["assignment"],
)
def create_issue_assignment(
    projectId: int,
    sessionId: int,
    integrationProjectId,
    data: schemas.AssignmentSchema = Body(...),
    context: schemas.CurrentContext = Depends(OR_context),
):
    data = sessions_assignments.create_new_assignment(
        tenant_id=context.tenant_id,
        project_id=projectId,
        session_id=sessionId,
        creator_id=context.user_id,
        assignee=data.assignee,
        description=data.description,
        title=data.title,
        issue_type=data.issue_type,
        integration_project_id=integrationProjectId,
    )
    if "errors" in data.keys():
        return data
    return {"data": data}


# 获取指定项目的 GDPR（通用数据保护条例）相关信息。

# 参数:


# projectId (int): 项目的唯一标识符。
# context (schemas.CurrentContext): 当前请求的上下文，依赖于 OR_context。
@app.get("/{projectId}/gdpr", tags=["projects", "gdpr"])
def get_gdpr(projectId: int, context: schemas.CurrentContext = Depends(OR_context)):
    return {"data": projects.get_gdpr(project_id=projectId)}


# 编辑指定项目的 GDPR 信息。

# 参数:

# projectId (int): 项目的唯一标识符。
# data (schemas.GdprSchema): 包含 GDPR 编辑信息的数据。
# context (schemas.CurrentContext): 当前请求的上下文，依赖于 OR_context。


@app.post("/{projectId}/gdpr", tags=["projects", "gdpr"])
def edit_gdpr(
    projectId: int,
    data: schemas.GdprSchema = Body(...),
    context: schemas.CurrentContext = Depends(OR_context),
):
    result = projects.edit_gdpr(project_id=projectId, gdpr=data)
    if "errors" in result:
        return result
    return {"data": result}


# 处理用户请求重置密码的流程，发送密码重置链接。

# 参数:

# background_tasks (BackgroundTasks): 用于处理后台任务。
# data (schemas.ForgetPasswordPayloadSchema): 包含用户邮箱的重置密码请求数据。


@public_app.post("/password/reset-link", tags=["reset password"])
def reset_password_handler(
    background_tasks: BackgroundTasks,
    data: schemas.ForgetPasswordPayloadSchema = Body(...),
):
    if len(data.email) < 5:
        return {"errors": ["please provide a valid email address"]}
    return reset_password.reset(data=data, background_tasks=background_tasks)


# 获取指定项目的元数据信息。

# 参数:


# projectId (int): 项目的唯一标识符。
# context (schemas.CurrentContext): 当前请求的上下文，依赖于 OR_context。
@app.get("/{projectId}/metadata", tags=["metadata"])
def get_metadata(projectId: int, context: schemas.CurrentContext = Depends(OR_context)):
    return {"data": metadata.get(project_id=projectId)}


# @app.post('/{projectId}/metadata/list', tags=["metadata"])
# def add_edit_delete_metadata(projectId: int, data: schemas.MetadataListSchema = Body(...),
#                              context: schemas.CurrentContext = Depends(OR_context)):
#     return metadata.add_edit_delete(tenant_id=context.tenant_id, project_id=projectId, new_metas=data.list)

# 为指定项目添加新的元数据。

# 参数:


# projectId (int): 项目的唯一标识符。
# data (schemas.MetadataSchema): 包含要添加的元数据键值对。
# context (schemas.CurrentContext): 当前请求的上下文，依赖于 OR_context。
@app.post("/{projectId}/metadata", tags=["metadata"])
def add_metadata(
    projectId: int,
    data: schemas.MetadataSchema = Body(...),
    context: schemas.CurrentContext = Depends(OR_context),
):
    return metadata.add(tenant_id=context.tenant_id, project_id=projectId, new_name=data.key)


# 编辑指定项目中的现有元数据。

# 参数:


# projectId (int): 项目的唯一标识符。
# index (int): 元数据的索引。
# data (schemas.MetadataSchema): 包含要编辑的元数据键值对。
# context (schemas.CurrentContext): 当前请求的上下文，依赖于 OR_context。
@app.post("/{projectId}/metadata/{index}", tags=["metadata"])
def edit_metadata(
    projectId: int,
    index: int,
    data: schemas.MetadataSchema = Body(...),
    context: schemas.CurrentContext = Depends(OR_context),
):
    return metadata.edit(
        tenant_id=context.tenant_id,
        project_id=projectId,
        index=index,
        new_name=data.key,
    )


# 删除指定项目的元数据。

# 参数:


# projectId (int): 项目的唯一标识符。
# index (int): 元数据的索引。
# context (schemas.CurrentContext): 当前请求的上下文，依赖于 OR_context。
@app.delete("/{projectId}/metadata/{index}", tags=["metadata"])
def delete_metadata(
    projectId: int,
    index: int,
    _=Body(None),
    context: schemas.CurrentContext = Depends(OR_context),
):
    return metadata.delete(tenant_id=context.tenant_id, project_id=projectId, index=index)


# 根据键和值在指定项目中搜索元数据。

# 参数:


# projectId (int): 项目的唯一标识符。
# q (str): 搜索的值。
# key (str): 元数据的键。
# context (schemas.CurrentContext): 当前请求的上下文，依赖于 OR_context。
@app.get("/{projectId}/metadata/search", tags=["metadata"])
def search_metadata(
    projectId: int,
    q: str,
    key: str,
    context: schemas.CurrentContext = Depends(OR_context),
):
    if len(q) == 0 and len(key) == 0:
        return {"data": []}
    if len(q) == 0:
        return {"errors": ["please provide a value for search"]}
    if len(key) == 0:
        return {"errors": ["please provide a key for search"]}
    return metadata.search(tenant_id=context.tenant_id, project_id=projectId, value=q, key=key)


# 搜索指定项目的所有日志工具集成源。

# 参数:

# projectId (int): 项目的唯一标识符。
# context (schemas.CurrentContext): 当前请求的上下文，依赖于 OR_context。


@app.get("/{projectId}/integration/sources", tags=["integrations"])
def search_integrations(projectId: int, context: schemas.CurrentContext = Depends(OR_context)):
    return log_tools.search(project_id=projectId)


# 获取指定项目的捕获状态。

# 参数:

# projectId (int): 项目的唯一标识符。
# context (schemas.CurrentContext): 当前请求的上下文，依赖于 OR_context。


@app.get("/{projectId}/sample_rate", tags=["projects"])
def get_capture_status(projectId: int, context: schemas.CurrentContext = Depends(OR_context)):
    return {"data": projects.get_capture_status(project_id=projectId)}


# 更新指定项目的捕获状态。

# 参数:

# projectId (int): 项目的唯一标识符。
# data (schemas.SampleRateSchema): 包含捕获状态的数据。
# context (schemas.CurrentContext): 当前请求的上下文，依赖于 OR_context。


@app.post("/{projectId}/sample_rate", tags=["projects"])
def update_capture_status(
    projectId: int,
    data: schemas.SampleRateSchema = Body(...),
    context: schemas.CurrentContext = Depends(OR_context),
):
    return {"data": projects.update_capture_status(project_id=projectId, changes=data)}


# 更新项目条件或规则。

# 参数:


# projectId (int): 项目的唯一标识符。
# data (schemas.ProjectSettings): 包含项目的条件设置。
# context (schemas.CurrentContext): 当前请求的上下文，依赖于 OR_context。
@app.post("/{projectId}/conditions", tags=["projects"])
def update_conditions(
    projectId: int,
    data: schemas.ProjectSettings = Body(...),
    context: schemas.CurrentContext = Depends(OR_context),
):
    return {"data": projects.update_conditions(project_id=projectId, changes=data)}


# 获取指定项目的条件设置。

# 参数:


# projectId (int): 项目的唯一标识符。
# context (schemas.CurrentContext): 当前请求的上下文，依赖于 OR_context。
@app.get("/{projectId}/conditions", tags=["projects"])
def get_conditions(projectId: int, context: schemas.CurrentContext = Depends(OR_context)):
    return {"data": projects.get_conditions(project_id=projectId)}


# 获取当前用户的所有公告。

# 参数:


# context (schemas.CurrentContext): 当前请求的上下文，依赖于 OR_context。
@app.get("/announcements", tags=["announcements"])
def get_all_announcements(context: schemas.CurrentContext = Depends(OR_context)):
    return {"data": announcements.get_all(user_id=context.user_id)}


# 查看所有公告的状态。

# 参数:


# context (schemas.CurrentContext): 当前请求的上下文，依赖于 OR_context。
@app.get("/announcements/view", tags=["announcements"])
def get_all_announcements(context: schemas.CurrentContext = Depends(OR_context)):
    return {"data": announcements.view(user_id=context.user_id)}


# 检查错误合并状态，通常用于显示错误横幅。

# 参数:


# context (schemas.CurrentContext): 当前请求的上下文，依赖于 OR_context。
@app.get("/show_banner", tags=["banner"])
def errors_merge(context: schemas.CurrentContext = Depends(OR_context)):
    return {"data": False}


# 为指定项目创建新的警报。

# 参数:

# projectId (int): 项目的唯一标识符。
# data (schemas.AlertSchema): 包含警报设置的数据。
# context (schemas.CurrentContext): 当前请求的上下文，依赖于 OR_context。


@app.post("/{projectId}/alerts", tags=["alerts"])
def create_alert(
    projectId: int,
    data: schemas.AlertSchema = Body(...),
    context: schemas.CurrentContext = Depends(OR_context),
):
    return alerts.create(project_id=projectId, data=data)


# 获取指定项目的所有警报。

# 参数:

# projectId (int): 项目的唯一标识符。
# context (schemas.CurrentContext): 当前请求的上下文，依赖于 OR_context。


@app.get("/{projectId}/alerts", tags=["alerts"])
def get_all_alerts(projectId: int, context: schemas.CurrentContext = Depends(OR_context)):
    return {"data": alerts.get_all(project_id=projectId)}


# 获取项目中的所有警报触发器以及自定义指标的序列。

# 参数:


# projectId (int): 项目的唯一标识符。
# context (schemas.CurrentContext): 当前请求的上下文，依赖于 OR_context。
@app.get("/{projectId}/alerts/triggers", tags=["alerts", "customMetrics"])
def get_alerts_triggers(projectId: int, context: schemas.CurrentContext = Depends(OR_context)):
    return {"data": alerts.get_predefined_values() + custom_metrics.get_series_for_alert(project_id=projectId, user_id=context.user_id)}


# 获取指定警报的详细信息。

# 参数:


# projectId (int): 项目的唯一标识符。
# alertId (int): 警报的唯一标识符。
# context (schemas.CurrentContext): 当前请求的上下文，依赖于 OR_context。
@app.get("/{projectId}/alerts/{alertId}", tags=["alerts"])
def get_alert(projectId: int, alertId: int, context: schemas.CurrentContext = Depends(OR_context)):
    return {"data": alerts.get(id=alertId)}


# 更新指定警报的设置。

# 参数:


# projectId (int): 项目的唯一标识符。
# alertId (int): 警报的唯一标识符。
# data (schemas.AlertSchema): 包含警报的更新数据。
# context (schemas.CurrentContext): 当前请求的上下文，依赖于 OR_context。
@app.post("/{projectId}/alerts/{alertId}", tags=["alerts"])
def update_alert(
    projectId: int,
    alertId: int,
    data: schemas.AlertSchema = Body(...),
    context: schemas.CurrentContext = Depends(OR_context),
):
    return alerts.update(id=alertId, data=data)


# 删除指定的警报。

# 参数:


# projectId (int): 项目的唯一标识符。
# alertId (int): 警报的唯一标识符。
# context (schemas.CurrentContext): 当前请求的上下文，依赖于 OR_context。
@app.delete("/{projectId}/alerts/{alertId}", tags=["alerts"])
def delete_alert(
    projectId: int,
    alertId: int,
    _=Body(None),
    context: schemas.CurrentContext = Depends(OR_context),
):
    return alerts.delete(project_id=projectId, alert_id=alertId)


# 为指定项目签署 SourceMap 上传 URL，用于上传错误源映射文件。

# 参数:

# projectKey (str): 项目的唯一标识符。
# data (schemas.SourcemapUploadPayloadSchema): 包含 URL 数据的请求体。
# context (schemas.CurrentContext): 当前请求的上下文，依赖于 OR_context。


@app_apikey.put("/{projectKey}/sourcemaps/", tags=["sourcemaps"])
@app_apikey.put("/{projectKey}/sourcemaps", tags=["sourcemaps"])
def sign_sourcemap_for_upload(
    projectKey: str,
    data: schemas.SourcemapUploadPayloadSchema = Body(...),
    context: schemas.CurrentContext = Depends(OR_context),
):
    return {"data": sourcemaps.presign_upload_urls(project_id=context.project.project_id, urls=data.urls)}


# 获取当前用户的每周报告配置。

# 参数:

# context (schemas.CurrentContext): 当前请求的上下文，依赖于 OR_context。


@app.get("/config/weekly_report", tags=["weekly report config"])
def get_weekly_report_config(context: schemas.CurrentContext = Depends(OR_context)):
    return {"data": weekly_report.get_config(user_id=context.user_id)}


# 编辑当前用户的每周报告配置。

# 参数:


# data (schemas.WeeklyReportConfigSchema): 包含每周报告配置信息的数据。
# context (schemas.CurrentContext): 当前请求的上下文，依赖于 OR_context。
@app.post("/config/weekly_report", tags=["weekly report config"])
def edit_weekly_report_config(
    data: schemas.WeeklyReportConfigSchema = Body(...),
    context: schemas.CurrentContext = Depends(OR_context),
):
    return {"data": weekly_report.edit_config(user_id=context.user_id, weekly_report=data.weekly_report)}


# 获取指定项目中的所有问题类型。

# 参数:


# projectId (int): 项目的唯一标识符。
# context (schemas.CurrentContext): 当前请求的上下文，依赖于 OR_context。
@app.get("/{projectId}/issue_types", tags=["issues"])
def issue_types(projectId: int, context: schemas.CurrentContext = Depends(OR_context)):
    return {"data": issues.get_all_types()}


# 获取系统中所有问题类型。

# 参数:

# context (schemas.CurrentContext): 当前请求的上下文，依赖于 OR_context。


@app.get("/issue_types", tags=["issues"])
def all_issue_types(context: schemas.CurrentContext = Depends(OR_context)):
    return {"data": issues.get_all_types()}


# 获取指定项目中的实时协助会话。

# 参数:


# projectId (int): 项目的唯一标识符。
# userId (str, 可选): 用户的唯一标识符，用于过滤结果。
# context (schemas.CurrentContext): 当前请求的上下文，依赖于 OR_context。
@app.get("/{projectId}/assist/sessions", tags=["assist"])
def get_sessions_live(
    projectId: int,
    userId: str = None,
    context: schemas.CurrentContext = Depends(OR_context),
):
    data = assist.get_live_sessions_ws_user_id(projectId, user_id=userId)
    return {"data": data}


# 根据搜索条件获取指定项目中的实时协助会话。

# 参数:


# projectId (int): 项目的唯一标识符。
# data (schemas.LiveSessionsSearchPayloadSchema): 包含会话搜索条件的数据。
# context (schemas.CurrentContext): 当前请求的上下文，依赖于 OR_context。
@app.post("/{projectId}/assist/sessions", tags=["assist"])
def sessions_live(
    projectId: int,
    data: schemas.LiveSessionsSearchPayloadSchema = Body(...),
    context: schemas.CurrentContext = Depends(OR_context),
):
    data = assist.get_live_sessions_ws(projectId, body=data)
    return {"data": data}


# 签署移动端会话的 URL 用于处理相关数据。

# 参数:

# projectId (int): 项目的唯一标识符。
# sessionId (int): 会话的唯一标识符。
# data (schemas.MobileSignPayloadSchema): 包含需要签署的密钥数据。
# context (schemas.CurrentContext): 当前请求的上下文，依赖于 OR_context。


@app.post("/{projectId}/mobile/{sessionId}/urls", tags=["mobile"])
def mobile_signe(
    projectId: int,
    sessionId: int,
    data: schemas.MobileSignPayloadSchema = Body(...),
    context: schemas.CurrentContext = Depends(OR_context),
):
    return {"data": mobile.sign_keys(project_id=projectId, session_id=sessionId, keys=data.keys)}


# 为租户创建一个新的项目。

# 参数:

# data (schemas.CreateProjectSchema): 包含新项目创建信息的数据。
# context (schemas.CurrentContext): 当前请求的上下文，依赖于 OR_context。


@app.post("/projects", tags=["projects"], dependencies=[OR_role("owner", "admin")])
def create_project(
    data: schemas.CreateProjectSchema = Body(...),
    context: schemas.CurrentContext = Depends(OR_context),
):
    return projects.create(tenant_id=context.tenant_id, user_id=context.user_id, data=data)


# 获取指定项目的详细信息，包括最近一次的会话和 GDPR 设置。

# 参数:


# projectId (int): 项目的唯一标识符。
# context (schemas.CurrentContext): 当前请求的上下文，依赖于 OR_context。
@app.get("/projects/{projectId}", tags=["projects"])
def get_project(projectId: int, context: schemas.CurrentContext = Depends(OR_context)):
    data = projects.get_project(
        tenant_id=context.tenant_id,
        project_id=projectId,
        include_last_session=True,
        include_gdpr=True,
    )
    if data is None:
        return {"errors": ["project not found"]}
    return {"data": data}


# 编辑指定项目的详细信息。

# 参数:

# projectId (int): 项目的唯一标识符。
# data (schemas.CreateProjectSchema): 包含项目更新信息的数据。
# context (schemas.CurrentContext): 当前请求的上下文，依赖于 OR_context。


@app.put("/projects/{projectId}", tags=["projects"], dependencies=[OR_role("owner", "admin")])
def edit_project(
    projectId: int,
    data: schemas.CreateProjectSchema = Body(...),
    context: schemas.CurrentContext = Depends(OR_context),
):
    return projects.edit(
        tenant_id=context.tenant_id,
        user_id=context.user_id,
        data=data,
        project_id=projectId,
    )


# 删除指定的项目。

# 参数:

# projectId (int): 项目的唯一标识符。
# context (schemas.CurrentContext): 当前请求的上下文，依赖于 OR_context。


@app.delete("/projects/{projectId}", tags=["projects"], dependencies=[OR_role("owner", "admin")])
def delete_project(projectId: int, _=Body(None), context: schemas.CurrentContext = Depends(OR_context)):
    return projects.delete(tenant_id=context.tenant_id, user_id=context.user_id, project_id=projectId)


# 为当前租户生成一个新的 API 密钥。

# 参数:


# context (schemas.CurrentContext): 当前请求的上下文，依赖于 OR_context。
@app.get("/client/new_api_key", tags=["client"])
def generate_new_tenant_token(context: schemas.CurrentContext = Depends(OR_context)):
    return {"data": tenants.generate_new_api_key(context.tenant_id)}


# 更新当前用户的模块状态信息。

# 参数:

# data (schemas.ModuleStatus): 包含模块状态的数据。
# context (schemas.CurrentContext): 当前请求的上下文，依赖于 OR_context。


@app.post("/users/modules", tags=["users"])
def update_user_module(
    context: schemas.CurrentContext = Depends(OR_context),
    data: schemas.ModuleStatus = Body(...),
):
    return {"data": users.update_user_module(context.user_id, data)}


# 获取当前用户的所有通知。

# 参数:


# context (schemas.CurrentContext): 当前请求的上下文，依赖于 OR_context。
@app.get("/notifications", tags=["notifications"])
def get_notifications(context: schemas.CurrentContext = Depends(OR_context)):
    return {"data": notifications.get_all(tenant_id=context.tenant_id, user_id=context.user_id)}


# 获取当前用户的未读通知计数。

# 参数:

# context (schemas.CurrentContext): 当前请求的上下文，依赖于 OR_context。


@app.get("/notifications/count", tags=["notifications"])
def get_notifications_count(context: schemas.CurrentContext = Depends(OR_context)):
    return {"data": notifications.get_all_count(tenant_id=context.tenant_id, user_id=context.user_id)}


# 标记指定通知为已读。

# 参数:


# notificationId (int): 通知的唯一标识符。
# context (schemas.CurrentContext): 当前请求的上下文，依赖于 OR_context。
@app.get("/notifications/{notificationId}/view", tags=["notifications"])
def view_notifications(notificationId: int, context: schemas.CurrentContext = Depends(OR_context)):
    return {"data": notifications.view_notification(notification_ids=[notificationId], user_id=context.user_id)}


# 批量标记通知为已读。

# 参数:


# data (schemas.NotificationsViewSchema): 包含要标记的通知 ID 列表及相关时间戳的数据。
# context (schemas.CurrentContext): 当前请求的上下文，依赖于 OR_context。
@app.post("/notifications/view", tags=["notifications"])
def batch_view_notifications(
    data: schemas.NotificationsViewSchema,
    context: schemas.CurrentContext = Depends(OR_context),
):
    return {
        "data": notifications.view_notification(
            notification_ids=data.ids,
            startTimestamp=data.startTimestamp,
            endTimestamp=data.endTimestamp,
            user_id=context.user_id,
            tenant_id=context.tenant_id,
        )
    }


# 获取租户的用户登机（boarding）状态。

# 参数:


# context (schemas.CurrentContext): 当前请求的上下文，依赖于 OR_context。
@app.get("/boarding", tags=["boarding"])
def get_boarding_state(context: schemas.CurrentContext = Depends(OR_context)):
    if config("LOCAL_DEV", cast=bool, default=False):
        return {"data": ""}
    return {"data": boarding.get_state(tenant_id=context.tenant_id)}


# 获取租户用户登机过程中安装状态。

# 参数:


# context (schemas.CurrentContext): 当前请求的上下文，依赖于 OR_context。
@app.get("/boarding/installing", tags=["boarding"])
def get_boarding_state_installing(
    context: schemas.CurrentContext = Depends(OR_context),
):
    return {"data": boarding.get_state_installing(tenant_id=context.tenant_id)}


# 获取租户用户登机过程中识别用户的状态。

# 参数:


# context (schemas.CurrentContext): 当前请求的上下文，依赖于 OR_context。
@app.get("/boarding/identify-users", tags=["boarding"])
def get_boarding_state_identify_users(
    context: schemas.CurrentContext = Depends(OR_context),
):
    return {"data": boarding.get_state_identify_users(tenant_id=context.tenant_id)}


# 获取租户用户登机过程中管理用户的状态。

# 参数:


# context (schemas.CurrentContext): 当前请求的上下文，依赖于 OR_context。
@app.get("/boarding/manage-users", tags=["boarding"])
def get_boarding_state_manage_users(
    context: schemas.CurrentContext = Depends(OR_context),
):
    return {"data": boarding.get_state_manage_users(tenant_id=context.tenant_id)}


# 获取租户用户登机过程中集成系统的状态。

# 参数:

# context (schemas.CurrentContext): 当前请求的上下文，依赖于 OR_context。


@app.get("/boarding/integrations", tags=["boarding"])
def get_boarding_state_integrations(
    context: schemas.CurrentContext = Depends(OR_context),
):
    return {"data": boarding.get_state_integrations(tenant_id=context.tenant_id)}


# 获取当前租户的 Slack 渠道信息。

# 参数:


# context (schemas.CurrentContext): 当前请求的上下文，依赖于 OR_context。
@app.get("/integrations/slack/channels", tags=["integrations"])
def get_slack_channels(context: schemas.CurrentContext = Depends(OR_context)):
    return {"data": webhook.get_by_type(tenant_id=context.tenant_id, webhook_type=schemas.WebhookType.slack)}


# 获取指定 Slack 集成的 Webhook 详细信息。

# 参数:

# integrationId (int): Slack 集成的唯一标识符。
# context (schemas.CurrentContext): 当前请求的上下文，依赖于 OR_context。


@app.get("/integrations/slack/{integrationId}", tags=["integrations"])
def get_slack_webhook(integrationId: int, context: schemas.CurrentContext = Depends(OR_context)):
    return {"data": Slack.get_integration(tenant_id=context.tenant_id, integration_id=integrationId)}


# 删除指定的 Slack 集成。

# 参数:

# integrationId (int): Slack 集成的唯一标识符。
# context (schemas.CurrentContext): 当前请求的上下文，依赖于 OR_context。


@app.delete("/integrations/slack/{integrationId}", tags=["integrations"])
def delete_slack_integration(
    integrationId: int,
    _=Body(None),
    context: schemas.CurrentContext = Depends(OR_context),
):
    return webhook.delete(tenant_id=context.tenant_id, webhook_id=integrationId)


# 添加或编辑 Webhook。

# 参数:

# data (schemas.WebhookSchema): 包含 Webhook 设置信息的数据。
# context (schemas.CurrentContext): 当前请求的上下文，依赖于 OR_context。


@app.put("/webhooks", tags=["webhooks"])
def add_edit_webhook(
    data: schemas.WebhookSchema = Body(...),
    context: schemas.CurrentContext = Depends(OR_context),
):
    return {"data": webhook.add_edit(tenant_id=context.tenant_id, data=data, replace_none=True)}


# 获取当前租户的所有 Webhook 信息。

# 参数:

# context (schemas.CurrentContext): 当前请求的上下文，依赖于 OR_context。


@app.get("/webhooks", tags=["webhooks"])
def get_webhooks(context: schemas.CurrentContext = Depends(OR_context)):
    return {"data": webhook.get_by_tenant(tenant_id=context.tenant_id, replace_none=True)}


# 删除指定的 Webhook。

# 参数:

# webhookId (int): Webhook 的唯一标识符。
# context (schemas.CurrentContext): 当前请求的上下文，依赖于 OR_context。


@app.delete("/webhooks/{webhookId}", tags=["webhooks"])
def delete_webhook(webhookId: int, _=Body(None), context: schemas.CurrentContext = Depends(OR_context)):
    return webhook.delete(tenant_id=context.tenant_id, webhook_id=webhookId)


# 获取租户的所有成员信息。

# 参数:


# context (schemas.CurrentContext): 当前请求的上下文，依赖于 OR_context。
@app.get("/client/members", tags=["client"], dependencies=[OR_role("owner", "admin")])
def get_members(context: schemas.CurrentContext = Depends(OR_context)):
    return {"data": users.get_members(tenant_id=context.tenant_id)}


# 重新邀请或重置指定的成员。

# 参数:


# memberId (int): 成员的唯一标识符。
# context (schemas.CurrentContext): 当前请求的上下文，依赖于 OR_context。
@app.get(
    "/client/members/{memberId}/reset",
    tags=["client"],
    dependencies=[OR_role("owner", "admin")],
)
def reset_reinvite_member(memberId: int, context: schemas.CurrentContext = Depends(OR_context)):
    return users.reset_member(
        tenant_id=context.tenant_id,
        editor_id=context.user_id,
        user_id_to_update=memberId,
    )


# 作用:
# 删除指定的成员。

# 参数:

# memberId (int): 成员的唯一标识符。
# context (schemas.CurrentContext): 当前请求的上下文，依赖于 OR_context。


@app.delete(
    "/client/members/{memberId}",
    tags=["client"],
    dependencies=[OR_role("owner", "admin")],
)
def delete_member(memberId: int, _=Body(None), context: schemas.CurrentContext = Depends(OR_context)):
    return users.delete_member(tenant_id=context.tenant_id, user_id=context.user_id, id_to_delete=memberId)


# 为当前用户生成一个新的 API 密钥。

# 参数:


# context (schemas.CurrentContext): 当前请求的上下文，依赖于 OR_context。
@app.get("/account/new_api_key", tags=["account"], dependencies=[OR_role("owner", "admin")])
def generate_new_user_token(context: schemas.CurrentContext = Depends(OR_context)):
    return {"data": users.generate_new_api_key(user_id=context.user_id)}


# 更改当前用户的密码。

# 参数:

# data (schemas.EditUserPasswordSchema): 包含旧密码和新密码的数据。
# context (schemas.CurrentContext): 当前请求的上下文，依赖于 OR_context。


@app.post("/account/password", tags=["account"])
def change_client_password(
    data: schemas.EditUserPasswordSchema = Body(...),
    context: schemas.CurrentContext = Depends(OR_context),
):
    return users.change_password(
        email=context.email,
        old_password=data.old_password.get_secret_value(),
        new_password=data.new_password.get_secret_value(),
        tenant_id=context.tenant_id,
        user_id=context.user_id,
    )


# 为指定项目创建保存的搜索条件。

# 参数:

# projectId (int): 项目的唯一标识符。
# data (schemas.SavedSearchSchema): 包含保存的搜索条件的数据。
# context (schemas.CurrentContext): 当前请求的上下文，依赖于 OR_context。


@app.post("/{projectId}/saved_search", tags=["savedSearch"])
def add_saved_search(
    projectId: int,
    data: schemas.SavedSearchSchema = Body(...),
    context: schemas.CurrentContext = Depends(OR_context),
):
    return saved_search.create(project_id=projectId, user_id=context.user_id, data=data)


# 获取指定项目的所有已保存搜索条件。

# 参数:


# projectId (int): 项目的唯一标识符。
# context (schemas.CurrentContext): 当前请求的上下文，依赖于 OR_context。
@app.get("/{projectId}/saved_search", tags=["savedSearch"])
def get_saved_searches(projectId: int, context: schemas.CurrentContext = Depends(OR_context)):
    return {"data": saved_search.get_all(project_id=projectId, user_id=context.user_id, details=True)}


# 获取指定保存搜索条件的详细信息。

# 参数:


# projectId (int): 项目的唯一标识符。
# search_id (int): 已保存搜索的唯一标识符。
# context (schemas.CurrentContext): 当前请求的上下文，依赖于 OR_context。
@app.get("/{projectId}/saved_search/{search_id}", tags=["savedSearch"])
def get_saved_search(
    projectId: int,
    search_id: int,
    context: schemas.CurrentContext = Depends(OR_context),
):
    return {"data": saved_search.get(project_id=projectId, search_id=search_id, user_id=context.user_id)}


# 更新指定的保存搜索条件。

# 参数:


# projectId (int): 项目的唯一标识符。
# search_id (int): 已保存搜索的唯一标识符。
# data (schemas.SavedSearchSchema): 包含保存搜索条件的更新信息的数据。
# context (schemas.CurrentContext): 当前请求的上下文，依赖于 OR_context。
@app.post("/{projectId}/saved_search/{search_id}", tags=["savedSearch"])
def update_saved_search(
    projectId: int,
    search_id: int,
    data: schemas.SavedSearchSchema = Body(...),
    context: schemas.CurrentContext = Depends(OR_context),
):
    return {
        "data": saved_search.update(
            user_id=context.user_id,
            search_id=search_id,
            data=data,
            project_id=projectId,
        )
    }


# 删除指定的保存搜索条件。

# 参数:


# projectId (int): 项目的唯一标识符。
# search_id (int): 已保存搜索的唯一标识符。
# context (schemas.CurrentContext): 当前请求的上下文，依赖于 OR_context。
@app.delete("/{projectId}/saved_search/{search_id}", tags=["savedSearch"])
def delete_saved_search(
    projectId: int,
    search_id: int,
    _=Body(None),
    context: schemas.CurrentContext = Depends(OR_context),
):
    return {"data": saved_search.delete(project_id=projectId, user_id=context.user_id, search_id=search_id)}


# 获取当前用户的使用限制（如团队成员和项目数量）。

# 参数:


# context (schemas.CurrentContext): 当前请求的上下文，依赖于 OR_context。
@app.get("/limits", tags=["accounts"])
def get_limits(context: schemas.CurrentContext = Depends(OR_context)):
    return {
        "data": {
            "teamMember": -1,
            "projects": -1,
        }
    }


# 获取 Microsoft Teams 渠道信息。

# 参数:

# context (schemas.CurrentContext): 当前请求的上下文，依赖于 OR_context。


@app.get("/integrations/msteams/channels", tags=["integrations"])
def get_msteams_channels(context: schemas.CurrentContext = Depends(OR_context)):
    return {"data": webhook.get_by_type(tenant_id=context.tenant_id, webhook_type=schemas.WebhookType.msteams)}


# 为当前租户添加 Microsoft Teams 集成。

# 参数:


# data (schemas.AddCollaborationSchema): 包含 Microsoft Teams 集成信息的数据。
# context (schemas.CurrentContext): 当前请求的上下文，依赖于 OR_context。
@app.post("/integrations/msteams", tags=["integrations"])
def add_msteams_integration(
    data: schemas.AddCollaborationSchema,
    context: schemas.CurrentContext = Depends(OR_context),
):
    n = MSTeams.add(tenant_id=context.tenant_id, data=data)
    if n is None:
        return {"errors": ["We couldn't send you a test message on your Microsoft Teams channel. Please verify your webhook url."]}
    return {"data": n}


# 编辑 Microsoft Teams 集成。

# 参数:

# webhookId (int): Microsoft Teams 集成的唯一标识符。
# data (schemas.EditCollaborationSchema): 包含更新后的 Microsoft Teams 集成数据。
# context (schemas.CurrentContext): 当前请求的上下文，依赖于 OR_context。


@app.post("/integrations/msteams/{webhookId}", tags=["integrations"])
def edit_msteams_integration(
    webhookId: int,
    data: schemas.EditCollaborationSchema = Body(...),
    context: schemas.CurrentContext = Depends(OR_context),
):
    if len(data.url.unicode_string()) > 0:
        old = MSTeams.get_integration(tenant_id=context.tenant_id, integration_id=webhookId)
        if not old:
            return {"errors": ["MsTeams integration not found."]}
        if old["endpoint"] != data.url.unicode_string():
            if not MSTeams.say_hello(data.url.unicode_string()):
                return {"errors": ["We couldn't send you a test message on your Microsoft Teams channel. Please verify your webhook url."]}
    return {
        "data": webhook.update(
            tenant_id=context.tenant_id,
            webhook_id=webhookId,
            changes={"name": data.name, "endpoint": data.url.unicode_string()},
        )
    }


# 删除 Microsoft Teams 集成。

# 参数:

# webhookId (int): Microsoft Teams 集成的唯一标识符。
# context (schemas.CurrentContext): 当前请求的上下文，依赖于 OR_context。


@app.delete("/integrations/msteams/{webhookId}", tags=["integrations"])
def delete_msteams_integration(webhookId: int, _=Body(None), context: schemas.CurrentContext = Depends(OR_context)):
    return webhook.delete(tenant_id=context.tenant_id, webhook_id=webhookId)


# 检查指定项目的录制状态和会话计数。

# 参数:

# project_id (int): 项目的唯一标识符。


@app.get("/{project_id}/check-recording-status", tags=["sessions"])
async def check_recording_status(project_id: int):
    """
    Check the recording status and sessions count for a given project ID.

    Args:
        project_id (int): The ID of the project to check.

    Returns:
        dict: A dictionary containing the recording status and sessions count.
              The dictionary has the following structure:
              {
                  "recording_status": int,   # The recording status:
                                            # 0 - No sessions
                                            # 1 - Processing
                                            # 2 - Ready
                  "sessions_count": int      # The total count of sessions
              }
    """
    return {"data": sessions.check_recording_status(project_id=project_id)}


# 执行健康检查以确保系统正常运行。


# 参数: 无。
@public_app.get("/", tags=["health"])
def health_check():
    return {}


# tags

# 为指定项目创建新标签。

# 参数:


# projectId (int): 项目的唯一标识符。
# data (schemas.TagCreate): 包含标签信息的数据。
# context (schemas.CurrentContext): 当前请求的上下文，依赖于 OR_context。
@app.post("/{projectId}/tags", tags=["tags"])
def tags_create(
    projectId: int,
    data: schemas.TagCreate = Body(),
    context: schemas.CurrentContext = Depends(OR_context),
):
    data = tags.create_tag(project_id=projectId, data=data)
    return {"data": data}


# 更新指定项目的标签。

# 参数:


# projectId (int): 项目的唯一标识符。
# tagId (int): 标签的唯一标识符。
# data (schemas.TagUpdate): 包含更新后的标签信息。
# context (schemas.CurrentContext): 当前请求的上下文，依赖于 OR_context。
@app.put("/{projectId}/tags/{tagId}", tags=["tags"])
def tags_update(
    projectId: int,
    tagId: int,
    data: schemas.TagUpdate = Body(),
    context: schemas.CurrentContext = Depends(OR_context),
):
    data = tags.update_tag(project_id=projectId, tag_id=tagId, data=data)
    return {"data": data}


# 获取指定项目中的所有标签。

# 参数:


# projectId (int): 项目的唯一标识符。
# context (schemas.CurrentContext): 当前请求的上下文，依赖于 OR_context。
@app.get("/{projectId}/tags", tags=["tags"])
def tags_list(projectId: int, context: schemas.CurrentContext = Depends(OR_context)):
    data = tags.list_tags(project_id=projectId)
    return {"data": data}


# 删除指定项目中的标签。

# 参数:


# projectId (int): 项目的唯一标识符。
# tagId (int): 标签的唯一标识符。
# context (schemas.CurrentContext): 当前请求的上下文，依赖于 OR_context。
@app.delete("/{projectId}/tags/{tagId}", tags=["tags"])
def tags_delete(projectId: int, tagId: int, context: schemas.CurrentContext = Depends(OR_context)):
    data = tags.delete_tag(projectId, tag_id=tagId)
    return {"data": data}
