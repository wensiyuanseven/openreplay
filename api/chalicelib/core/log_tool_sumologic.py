from chalicelib.core import log_tools
from schemas import schemas
# 这段代码提供了与 Sumo Logic 集成的管理功能。它允许在系统中添加、更新、删除和获取与 Sumo Logic 的集成信息。Sumo Logic 是一种用于实时日志管理和分析的云原生服务，这段代码旨在使应用程序能够与 Sumo Logic 进行集成，以便进行日志管理和分析。
# 定义集成类型为 "sumologic"
IN_TY = "sumologic"

# 函数：get_all
# 功能：获取指定租户下所有 Sumo Logic 集成的日志信息。
# 参数：
# - tenant_id: 租户ID，用于标识集成操作的租户。
# 返回值：
# - 返回包含所有 Sumo Logic 集成日志信息的列表。
def get_all(tenant_id):
    return log_tools.get_all_by_tenant(tenant_id=tenant_id, integration=IN_TY)

# 函数：get
# 功能：获取指定项目的 Sumo Logic 集成日志信息。
# 参数：
# - project_id: 项目ID，用于标识具体的项目。
# 返回值：
# - 返回包含指定项目 Sumo Logic 集成日志信息的字典。
def get(project_id):
    return log_tools.get(project_id=project_id, integration=IN_TY)

# 函数：update
# 功能：更新指定项目的 Sumo Logic 集成信息。
# 参数：
# - tenant_id: 租户ID，用于标识集成操作的租户。
# - project_id: 项目ID，用于标识具体的项目。
# - changes: 包含需要更新的信息的字典（例如区域、访问ID和访问密钥）。
# 返回值：
# - 返回更新后的集成信息。
def update(tenant_id, project_id, changes):
    options = {}

    if "region" in changes:
        options["region"] = changes["region"]

    if "accessId" in changes:
        options["accessId"] = changes["accessId"]

    if "accessKey" in changes:
        options["accessKey"] = changes["accessKey"]
    return log_tools.edit(project_id=project_id, integration=IN_TY, changes=options)

# 函数：add
# 功能：为指定项目添加新的 Sumo Logic 集成信息。
# 参数：
# - tenant_id: 租户ID，用于标识集成操作的租户。
# - project_id: 项目ID，用于标识具体的项目。
# - access_id: 访问ID，用于 Sumo Logic 集成。
# - access_key: 访问密钥，用于 Sumo Logic 集成。
# - region: 区域，用于指定 Sumo Logic 服务的区域。
# 返回值：
# - 返回添加后的集成信息。
def add(tenant_id, project_id, access_id, access_key, region):
    options = {
        "accessId": access_id,
        "accessKey": access_key,
        "region": region
    }
    return log_tools.add(project_id=project_id, integration=IN_TY, options=options)

# 函数：delete
# 功能：删除指定项目的 Sumo Logic 集成信息。
# 参数：
# - tenant_id: 租户ID，用于标识集成操作的租户。
# - project_id: 项目ID，用于标识具体的项目。
# 返回值：
# - 返回删除状态信息。
def delete(tenant_id, project_id):
    return log_tools.delete(project_id=project_id, integration=IN_TY)

# 函数：add_edit
# 功能：根据传入的数据添加或更新指定项目的 Sumo Logic 集成信息。
# 参数：
# - tenant_id: 租户ID，用于标识集成操作的租户。
# - project_id: 项目ID，用于标识具体的项目。
# - data: 包含 Sumo Logic 集成信息的架构实例（schemas.IntegrationSumologicSchema）。
# 返回值：
# - 返回添加或更新后的集成信息。
def add_edit(tenant_id, project_id, data: schemas.IntegrationSumologicSchema):
    s = get(project_id)
    if s is not None:
        return update(tenant_id=tenant_id, project_id=project_id,
                      changes={"accessId": data.access_id,
                               "accessKey": data.access_key,
                               "region": data.region})
    else:
        return add(tenant_id=tenant_id,
                   project_id=project_id,
                   access_id=data.access_id,
                   access_key=data.access_key,
                   region=data.region)
