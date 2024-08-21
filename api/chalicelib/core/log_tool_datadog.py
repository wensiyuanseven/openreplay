from chalicelib.core import log_tools
from schemas import schemas

# 定义集成类型为 "datadog"
IN_TY = "datadog"


# 函数：get_all
# 功能：获取指定租户下所有 Datadog 集成的日志信息。
# 参数：
# - tenant_id: 租户ID，用于标识集成操作的租户。
# 返回值：
# - 返回包含所有 Datadog 集成日志信息的列表。
def get_all(tenant_id):
    return log_tools.get_all_by_tenant(tenant_id=tenant_id, integration=IN_TY)

# 函数：get
# 功能：获取指定项目的 Datadog 集成日志信息。
# 参数：
# - project_id: 项目ID，用于标识具体的项目。
# 返回值：
# - 返回包含指定项目 Datadog 集成日志信息的字典。
def get(project_id):
    return log_tools.get(project_id=project_id, integration=IN_TY)

# 函数：update
# 功能：更新指定项目的 Datadog 集成信息。
# 参数：
# - tenant_id: 租户ID，用于标识集成操作的租户。
# - project_id: 项目ID，用于标识具体的项目。
# - changes: 包含需要更新的信息的字典（例如API密钥和应用程序密钥）。
# 返回值：
# - 返回更新后的集成信息。
def update(tenant_id, project_id, changes):
    options = {}
    if "apiKey" in changes:
        options["apiKey"] = changes["apiKey"]
    if "applicationKey" in changes:
        options["applicationKey"] = changes["applicationKey"]

    return log_tools.edit(project_id=project_id, integration=IN_TY, changes=options)

# 函数：add
# 功能：为指定项目添加新的 Datadog 集成信息。
# 参数：
# - tenant_id: 租户ID，用于标识集成操作的租户。
# - project_id: 项目ID，用于标识具体的项目。
# - api_key: Datadog API 密钥。
# - application_key: Datadog 应用程序密钥。
# 返回值：
# - 返回添加后的集成信息。
def add(tenant_id, project_id, api_key, application_key):
    options = {"apiKey": api_key, "applicationKey": application_key}
    return log_tools.add(project_id=project_id, integration=IN_TY, options=options)

# 函数：delete
# 功能：删除指定项目的 Datadog 集成信息。
# 参数：
# - tenant_id: 租户ID，用于标识集成操作的租户。
# - project_id: 项目ID，用于标识具体的项目。
# 返回值：
# - 返回删除状态信息。
def delete(tenant_id, project_id):
    return log_tools.delete(project_id=project_id, integration=IN_TY)

# 函数：add_edit
# 功能：根据传入的数据添加或更新指定项目的 Datadog 集成信息。
# 参数：
# - tenant_id: 租户ID，用于标识集成操作的租户。
# - project_id: 项目ID，用于标识具体的项目。
# - data: 包含 Datadog 集成信息的架构实例（schemas.IntegrationDatadogSchema）。
# 返回值：
# - 返回添加或更新后的集成信息。
def add_edit(tenant_id, project_id, data: schemas.IntegrationDatadogSchema):
    s = get(project_id)
    if s is not None:
        return update(tenant_id=tenant_id, project_id=project_id, changes={"apiKey": data.api_key, "applicationKey": data.application_key})
    else:
        return add(tenant_id=tenant_id, project_id=project_id, api_key=data.api_key, application_key=data.application_key)
# 这段代码提供了与 Datadog 的集成管理功能，使得系统能够轻松地与 Datadog 进行连接。通过这些功能，用户可以管理 Datadog API 和应用程序密钥，以便应用程序能够与 Datadog API 进行交互，监控和管理其日志和指标数据。这使得集成管理变得更加方便和自动化，有助于确保集成的持续有效性。