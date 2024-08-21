# 这段代码实现了与 New Relic 的集成管理功能。它提供了添加、更新、删除和获取 New Relic 集成信息的功能，并使用 log_tools 
# 模块在系统数据库中进行这些操作。New Relic 是一个应用性能监控（APM）工具，这段代码使得应用程序能够与 New Relic 进行集成，以便进行性能监控和日志管理。
# 这段代码实现了与 New Relic 的集成管理功能，使得系统能够通过添加、更新、删除和获取集成信息，与 New Relic 进行连接和通信。这些功能有助于确保集成的有效性和可靠性，同时简化了集成管理的过程。通过 add_edit 函数，代码能够根据现有的集成信息进行智能判断，选择适当的添加或更新操作。
from chalicelib.core import log_tools
from schemas import schemas
# 定义集成类型为 "newrelic"
IN_TY = "newrelic"

# 函数：get_all
# 功能：获取指定租户下所有 New Relic 集成的日志信息。
# 参数：
# - tenant_id: 租户ID，用于标识集成操作的租户。
# 返回值：
# - 返回包含所有 New Relic 集成日志信息的列表
def get_all(tenant_id):
    return log_tools.get_all_by_tenant(tenant_id=tenant_id, integration=IN_TY)

# 函数：get
# 功能：获取指定项目的 New Relic 集成日志信息。
# 参数：
# - project_id: 项目ID，用于标识具体的项目。
# 返回值：
# - 返回包含指定项目 New Relic 集成日志信息的字典。
def get(project_id):
    return log_tools.get(project_id=project_id, integration=IN_TY)

# 函数：update
# 功能：更新指定项目的 New Relic 集成信息。
# 参数：
# - tenant_id: 租户ID，用于标识集成操作的租户。
# - project_id: 项目ID，用于标识具体的项目。
# - changes: 包含需要更新的信息的字典（例如区域、应用程序ID和查询密钥）。
# 返回值：
# - 返回更新后的集成信息。
def update(tenant_id, project_id, changes):
    options = {}
    if "region" in changes:
        options["region"] = changes["region"]
    if "applicationId" in changes:
        options["applicationId"] = changes["applicationId"]
    if "xQueryKey" in changes:
        options["xQueryKey"] = changes["xQueryKey"]

    return log_tools.edit(project_id=project_id, integration=IN_TY, changes=options)

# 函数：add
# 功能：为指定项目添加新的 New Relic 集成信息。
# 参数：
# - tenant_id: 租户ID，用于标识集成操作的租户。
# - project_id: 项目ID，用于标识具体的项目。
# - application_id: New Relic 应用程序ID。
# - x_query_key: New Relic 查询密钥。
# - region: New Relic 服务器所在区域（False 表示美国，True 表示欧盟）。
# 返回值：
# - 返回添加后的集成信息。
def add(tenant_id, project_id, application_id, x_query_key, region):
    # region=False => US; region=True => EU
    options = {"applicationId": application_id, "xQueryKey": x_query_key, "region": region}
    return log_tools.add(project_id=project_id, integration=IN_TY, options=options)

# 函数：delete
# 功能：删除指定项目的 New Relic 集成信息。
# 参数：
# - tenant_id: 租户ID，用于标识集成操作的租户。
# - project_id: 项目ID，用于标识具体的项目。
# 返回值：
# - 返回删除状态信息。
def delete(tenant_id, project_id):
    return log_tools.delete(project_id=project_id, integration=IN_TY)

# 函数：add_edit
# 功能：根据传入的数据添加或更新指定项目的 New Relic 集成信息。
# 参数：
# - tenant_id: 租户ID，用于标识集成操作的租户。
# - project_id: 项目ID，用于标识具体的项目。
# - data: 包含 New Relic 集成信息的架构实例（schemas.IntegrationNewrelicSchema）。
# 返回值：
# - 返回添加或更新后的集成信息。
def add_edit(tenant_id, project_id, data: schemas.IntegrationNewrelicSchema):
    s = get(project_id)
    if s is not None:
        return update(tenant_id=tenant_id, project_id=project_id,
                      changes={"applicationId": data.application_id,
                               "xQueryKey": data.x_query_key,
                               "region": data.region})
    else:
        return add(tenant_id=tenant_id,
                   project_id=project_id,
                   application_id=data.application_id,
                   x_query_key=data.x_query_key,
                   region=data.region)
