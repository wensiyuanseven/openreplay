# 这段代码为与 Google Stackdriver 的集成管理功能提供了支持。它允许在系统中添加、更新、删除和获取与 Stackdriver 的集成信息。
# Stackdriver 是 Google Cloud 提供的一种监控和日志管理工具，这段代码旨在使应用程序能够与 Stackdriver 进行集成，以便进行日志管理和监控。
from chalicelib.core import log_tools
from schemas import schemas
# 定义集成类型为 "stackdriver"
IN_TY = "stackdriver"

# 函数：get_all
# 功能：获取指定租户下所有 Stackdriver 集成的日志信息。
# 参数：
# - tenant_id: 租户ID，用于标识集成操作的租户。
# 返回值：
# - 返回包含所有 Stackdriver 集成日志信息的列表。
def get_all(tenant_id):
    return log_tools.get_all_by_tenant(tenant_id=tenant_id, integration=IN_TY)

# 函数：get
# 功能：获取指定项目的 Stackdriver 集成日志信息。
# 参数：
# - project_id: 项目ID，用于标识具体的项目。
# 返回值：
# - 返回包含指定项目 Stackdriver 集成日志信息的字典。
def get(project_id):
    return log_tools.get(project_id=project_id, integration=IN_TY)

# 函数：update
# 功能：更新指定项目的 Stackdriver 集成信息。
# 参数：
# - tenant_id: 租户ID，用于标识集成操作的租户。
# - project_id: 项目ID，用于标识具体的项目。
# - changes: 包含需要更新的信息的字典（例如服务账户凭证和日志名称）。
# 返回值：
# - 返回更新后的集成信息。
def update(tenant_id, project_id, changes):
    options = {}
    if "serviceAccountCredentials" in changes:
        options["serviceAccountCredentials"] = changes["serviceAccountCredentials"]
    if "logName" in changes:
        options["logName"] = changes["logName"]
    return log_tools.edit(project_id=project_id, integration=IN_TY, changes=options)

# 函数：add
# 功能：为指定项目添加新的 Stackdriver 集成信息。
# 参数：
# - tenant_id: 租户ID，用于标识集成操作的租户。
# - project_id: 项目ID，用于标识具体的项目。
# - service_account_credentials: 服务账户凭证，用于 Stackdriver 集成。
# - log_name: 日志名称，用于标识 Stackdriver 中的日志。
# 返回值：
# - 返回添加后的集成信息。
def add(tenant_id, project_id, service_account_credentials, log_name):
    options = {"serviceAccountCredentials": service_account_credentials, "logName": log_name}
    return log_tools.add(project_id=project_id, integration=IN_TY, options=options)

# 函数：delete
# 功能：删除指定项目的 Stackdriver 集成信息。
# 参数：
# - tenant_id: 租户ID，用于标识集成操作的租户。
# - project_id: 项目ID，用于标识具体的项目。
# 返回值：
# - 返回删除状态信息。
def delete(tenant_id, project_id):
    return log_tools.delete(project_id=project_id, integration=IN_TY)

# 函数：add_edit
# 功能：根据传入的数据添加或更新指定项目的 Stackdriver 集成信息。
# 参数：
# - tenant_id: 租户ID，用于标识集成操作的租户。
# - project_id: 项目ID，用于标识具体的项目。
# - data: 包含 Stackdriver 集成信息的架构实例（schemas.IntegrationStackdriverSchema）。
# 返回值：
# - 返回添加或更新后的集成信息。
def add_edit(tenant_id, project_id, data: schemas.IntegartionStackdriverSchema):
    s = get(project_id)
    if s is not None:
        return update(tenant_id=tenant_id, project_id=project_id,
                      changes={"serviceAccountCredentials": data.service_account_credentials,
                               "logName": data.log_name})
    else:
        return add(tenant_id=tenant_id, project_id=project_id,
                   service_account_credentials=data.service_account_credentials,
                   log_name=data.log_name)
