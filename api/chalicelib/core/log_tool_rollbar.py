# 这段代码实现了与 Rollbar 的集成管理功能。它提供了添加、更新、删除和获取 Rollbar 集成信息的功能，并使用 log_tools 模块在系统数据库中进行这些操作。Rollbar 是一个用于监控和跟踪应用程序错误的工具，这段代码使得应用程序能够与 Rollbar 进行集成，以便进行错误监控和日志管理。
# 这段代码实现了与 Rollbar 的集成管理功能，使得系统能够通过添加、更新、删除和获取集成信息，与 Rollbar 进行连接和通信。这些功能有助于确保集成的有效性和可靠性，同时简化了集成管理的过程。通过 add_edit 函数，代码能够根据现有的集成信息进行智能判断，选择适当的添加或更新操作。
from chalicelib.core import log_tools
from schemas import schemas
# 定义集成类型为 "rollbar"
IN_TY = "rollbar"

# 函数：get_all
# 功能：获取指定租户下所有 Rollbar 集成的日志信息。
# 参数：
# - tenant_id: 租户ID，用于标识集成操作的租户。
# 返回值：
# - 返回包含所有 Rollbar 集成日志信息的列表。
def get_all(tenant_id):
    return log_tools.get_all_by_tenant(tenant_id=tenant_id, integration=IN_TY)

# 函数：get
# 功能：获取指定项目的 Rollbar 集成日志信息。
# 参数：
# - project_id: 项目ID，用于标识具体的项目。
# 返回值：
# - 返回包含指定项目 Rollbar 集成日志信息的字典。
def get(project_id):
    return log_tools.get(project_id=project_id, integration=IN_TY)

# 函数：update
# 功能：更新指定项目的 Rollbar 集成信息。
# 参数：
# - tenant_id: 租户ID，用于标识集成操作的租户。
# - project_id: 项目ID，用于标识具体的项目。
# - changes: 包含需要更新的信息的字典（例如访问令牌）。
# 返回值：
# - 返回更新后的集成信息。
def update(tenant_id, project_id, changes):
    options = {}
    if "accessToken" in changes:
        options["accessToken"] = changes["accessToken"]
    return log_tools.edit(project_id=project_id, integration=IN_TY, changes=options)

# 函数：add
# 功能：为指定项目添加新的 Rollbar 集成信息。
# 参数：
# - tenant_id: 租户ID，用于标识集成操作的租户。
# - project_id: 项目ID，用于标识具体的项目。
# - access_token: Rollbar 访问令牌。
# 返回值：
# - 返回添加后的集成信息。
def add(tenant_id, project_id, access_token):
    options = {"accessToken": access_token}
    return log_tools.add(project_id=project_id, integration=IN_TY, options=options)

# 函数：delete
# 功能：删除指定项目的 Rollbar 集成信息。
# 参数：
# - tenant_id: 租户ID，用于标识集成操作的租户。
# - project_id: 项目ID，用于标识具体的项目。
# 返回值：
# - 返回删除状态信息。
def delete(tenant_id, project_id):
    return log_tools.delete(project_id=project_id, integration=IN_TY)

# 函数：add_edit
# 功能：根据传入的数据添加或更新指定项目的 Rollbar 集成信息。
# 参数：
# - tenant_id: 租户ID，用于标识集成操作的租户。
# - project_id: 项目ID，用于标识具体的项目。
# - data: 包含 Rollbar 集成信息的架构实例（schemas.IntegrationRollbarSchema）。
# 返回值：
# - 返回添加或更新后的集成信息。
def add_edit(tenant_id, project_id, data: schemas.IntegrationRollbarSchema):
    s = get(project_id)
    if s is not None:
        return update(tenant_id=tenant_id, project_id=project_id,
                      changes={"accessToken": data.access_token})
    else:
        return add(tenant_id=tenant_id,
                   project_id=project_id,
                   access_token=data.access_token)
