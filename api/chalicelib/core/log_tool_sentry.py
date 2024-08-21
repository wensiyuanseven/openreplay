# 这段代码实现了与 Sentry 的集成管理功能。它提供了添加、更新、删除和获取 Sentry 集成信息的功能，并使用 log_tools 模块在系统数据库中进行这些操作。此外，还提供了通过代理方式获取 Sentry 事件详细信息的功能。Sentry 是一个错误监控和报告工具，这段代码使得应用程序能够与 Sentry 进行集成，以便进行错误监控和日志管理。
import requests
from chalicelib.core import log_tools
from schemas import schemas
# 定义集成类型为 "sentry"
IN_TY = "sentry"

# 函数：get_all
# 功能：获取指定租户下所有 Sentry 集成的日志信息。
# 参数：
# - tenant_id: 租户ID，用于标识集成操作的租户。
# 返回值：
# - 返回包含所有 Sentry 集成日志信息的列表。
def get_all(tenant_id):
    return log_tools.get_all_by_tenant(tenant_id=tenant_id, integration=IN_TY)

# 函数：get
# 功能：获取指定项目的 Sentry 集成日志信息。
# 参数：
# - project_id: 项目ID，用于标识具体的项目。
# 返回值：
# - 返回包含指定项目 Sentry 集成日志信息的字典。
def get(project_id):
    return log_tools.get(project_id=project_id, integration=IN_TY)

# 函数：update
# 功能：更新指定项目的 Sentry 集成信息。
# 参数：
# - tenant_id: 租户ID，用于标识集成操作的租户。
# - project_id: 项目ID，用于标识具体的项目。
# - changes: 包含需要更新的信息的字典（例如组织 Slug、项目 Slug 和访问令牌）。
# 返回值：
# - 返回更新后的集成信息。
def update(tenant_id, project_id, changes):
    options = {}
    if "organizationSlug" in changes:
        options["organizationSlug"] = changes["organizationSlug"]
    if "projectSlug" in changes:
        options["projectSlug"] = changes["projectSlug"]
    if "token" in changes:
        options["token"] = changes["token"]

    return log_tools.edit(project_id=project_id, integration=IN_TY, changes=changes)

# 函数：add
# 功能：为指定项目添加新的 Sentry 集成信息。
# 参数：
# - tenant_id: 租户ID，用于标识集成操作的租户。
# - project_id: 项目ID，用于标识具体的项目。
# - project_slug: Sentry 项目 Slug。
# - organization_slug: Sentry 组织 Slug。
# - token: Sentry 访问令牌。
# 返回值：
# - 返回添加后的集成信息。
def add(tenant_id, project_id, project_slug, organization_slug, token):
    options = {
        "organizationSlug": organization_slug, "projectSlug": project_slug, "token": token
    }
    return log_tools.add(project_id=project_id, integration=IN_TY, options=options)

# 函数：delete
# 功能：删除指定项目的 Sentry 集成信息。
# 参数：
# - tenant_id: 租户ID，用于标识集成操作的租户。
# - project_id: 项目ID，用于标识具体的项目。
# 返回值：
# - 返回删除状态信息。
def delete(tenant_id, project_id):
    return log_tools.delete(project_id=project_id, integration=IN_TY)

# 函数：add_edit
# 功能：根据传入的数据添加或更新指定项目的 Sentry 集成信息。
# 参数：
# - tenant_id: 租户ID，用于标识集成操作的租户。
# - project_id: 项目ID，用于标识具体的项目。
# - data: 包含 Sentry 集成信息的架构实例（schemas.IntegrationSentrySchema）。
# 返回值：
# - 返回添加或更新后的集成信息。
def add_edit(tenant_id, project_id, data: schemas.IntegrationSentrySchema):
    s = get(project_id)
    if s is not None:
        return update(tenant_id=tenant_id, project_id=project_id,
                      changes={"projectSlug": data.project_slug,
                               "organizationSlug": data.organization_slug,
                               "token": data.token})
    else:
        return add(tenant_id=tenant_id,
                   project_id=project_id,
                   project_slug=data.project_slug,
                   organization_slug=data.organization_slug,
                   token=data.token)

# 函数：proxy_get
# 功能：通过代理方式获取指定 Sentry 事件的详细信息。
# 参数：
# - tenant_id: 租户ID，用于标识集成操作的租户。
# - project_id: 项目ID，用于标识具体的项目。
# - event_id: Sentry 事件 ID。
# 返回值：
# - 返回包含事件详细信息的字典。
def proxy_get(tenant_id, project_id, event_id):
    i = get(project_id)
    if i is None:
        return {}
    r = requests.get(
        url="https://sentry.io/api/0/projects/%(organization_slug)s/%(project_slug)s/events/%(event_id)s/" % {
            "organization_slug": i["organizationSlug"], "project_slug": i["projectSlug"], "event_id": event_id},
        headers={"Authorization": "Bearer " + i["token"]})
    if r.status_code != 200:
        print("=======> sentry get: something went wrong")
        print(r)
        print(r.status_code)
        print(r.text)
    return r.json()


# 代码解析
# IN_TY 变量：

# 这个变量定义了当前集成的类型为 sentry，并在后续函数中用作标识符。
# get_all 函数：

# 该函数使用 log_tools.get_all_by_tenant 获取指定租户下所有与 Sentry 集成相关的日志信息。
# get 函数：

# 该函数使用 log_tools.get 获取指定项目的 Sentry 集成日志信息。
# update 函数：

# 该函数更新指定项目的 Sentry 集成信息，包括组织 Slug、项目 Slug 和访问令牌。调用 log_tools.edit 进行更新操作。
# add 函数：

# 该函数为指定项目添加新的 Sentry 集成信息，主要包括组织 Slug、项目 Slug 和访问令牌，然后调用 log_tools.add 进行添加操作。
# delete 函数：

# 该函数删除指定项目的 Sentry 集成信息，调用 log_tools.delete 进行删除操作。
# add_edit 函数：

# 首先检查指定项目是否已有 Sentry 集成信息。如果存在，则调用 update 函数更新信息；如果不存在，则调用 add 函数添加新信息。
# proxy_get 函数：

# 该函数通过代理方式从 Sentry 获取指定事件的详细信息。如果获取失败，会在控制台输出错误信息。调用 requests.get 发送 HTTP 请求获取事件数据。
# 总结
# 这段代码实现了与 Sentry 的集成管理功能，使得系统能够通过添加、更新、删除和获取集成信息，与 Sentry 进行连接和通信。这些功能有助于确保集成的有效性和可靠性，同时简化了集成管理的过程。通过 proxy_get 函数，代码能够通过代理方式获取 Sentry 中的事件详细信息，方便用户进行调试和问题追踪。






