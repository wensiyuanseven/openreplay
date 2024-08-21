# 这段代码主要用于与 BugSnag 的 API 进行交互，管理与 BugSnag 的集成，并使用 log_tools 模块在数据库中进行操作。它提供了添加、更新、删除和获取 BugSnag 集成信息的功能，并能够通过 BugSnag API 获取组织和项目的列表。
from chalicelib.core import log_tools
import requests

from schemas import schemas

# 定义集成类型为 "bugsnag"
IN_TY = "bugsnag"


# 函数：list_projects
# 功能：获取使用者在 BugSnag 中的所有组织及其项目列表。
# 参数：
# - auth_token: BugSnag API 认证令牌，用于授权 API 请求。
# 返回值：
# - 返回包含组织名称及其项目的列表。
def list_projects(auth_token):
    # 请求用户的组织信息
    r = requests.get(url="https://api.bugsnag.com/user/organizations", params={"per_page": "100"}, headers={"Authorization": "token " + auth_token, "X-Version": "2"})
    if r.status_code != 200:
        print("=======> bugsnag get organizations: something went wrong")
        print(r)
        print(r.status_code)
        print(r.text)
        return []

    orgs = []
    for i in r.json():
        # 获取每个组织中的项目列表
        pr = requests.get(url="https://api.bugsnag.com/organizations/%s/projects" % i["id"], params={"per_page": "100"}, headers={"Authorization": "token " + auth_token, "X-Version": "2"})
        if pr.status_code != 200:
            print("=======> bugsnag get projects: something went wrong")
            print(pr)
            print(r.status_code)
            print(r.text)
            continue
        orgs.append({"name": i["name"], "projects": [{"name": p["name"], "id": p["id"]} for p in pr.json()]})
    return orgs


# 函数：get_all
# 功能：获取指定租户下所有 BugSnag 集成的日志信息。
# 参数：
# - tenant_id: 租户ID，用于标识集成操作的租户。
# 返回值：
# - 返回包含所有 BugSnag 集成日志信息的列表。
def get_all(tenant_id):
    return log_tools.get_all_by_tenant(tenant_id=tenant_id, integration=IN_TY)


# 函数：get
# 功能：获取指定项目的 BugSnag 集成日志信息。
# 参数：
# - project_id: 项目ID，用于标识具体的项目。
# 返回值：
# - 返回包含指定项目 BugSnag 集成日志信息的字典。
def get(project_id):
    return log_tools.get(project_id=project_id, integration=IN_TY)


# 函数：update
# 功能：更新指定项目的 BugSnag 集成信息。
# 参数：
# - tenant_id: 租户ID，用于标识集成操作的租户。
# - project_id: 项目ID，用于标识具体的项目。
# - changes: 包含需要更新的信息的字典。
# 返回值：
# - 返回更新后的集成信息。
def update(tenant_id, project_id, changes):
    options = {}
    if "authorizationToken" in changes:
        options["authorizationToken"] = changes.pop("authorizationToken")
    if "bugsnagProjectId" in changes:
        options["bugsnagProjectId"] = changes.pop("bugsnagProjectId")
    return log_tools.edit(project_id=project_id, integration=IN_TY, changes=options)


# 函数：add
# 功能：为指定项目添加新的 BugSnag 集成信息。
# 参数：
# - tenant_id: 租户ID，用于标识集成操作的租户。
# - project_id: 项目ID，用于标识具体的项目。
# - authorization_token: 用于授权 BugSnag API 的令牌。
# - bugsnag_project_id: BugSnag 项目ID。
# 返回值：
# - 返回添加后的集成信息。
def add(tenant_id, project_id, authorization_token, bugsnag_project_id):
    options = {
        "bugsnagProjectId": bugsnag_project_id,
        "authorizationToken": authorization_token,
    }
    return log_tools.add(project_id=project_id, integration=IN_TY, options=options)


# 函数：delete
# 功能：删除指定项目的 BugSnag 集成信息。
# 参数：
# - tenant_id: 租户ID，用于标识集成操作的租户。
# - project_id: 项目ID，用于标识具体的项目。
# 返回值：
# - 返回删除状态信息。
def delete(tenant_id, project_id):
    return log_tools.delete(project_id=project_id, integration=IN_TY)


# 函数：add_edit
# 功能：根据传入的数据添加或更新指定项目的 BugSnag 集成信息。
# 参数：
# - tenant_id: 租户ID，用于标识集成操作的租户。
# - project_id: 项目ID，用于标识具体的项目。
# - data: 包含 BugSnag 集成信息的架构实例（schemas.IntegrationBugsnagSchema）。
# 返回值：
# - 返回添加或更新后的集成信息。
def add_edit(tenant_id, project_id, data: schemas.IntegrationBugsnagSchema):
    s = get(project_id)
    if s is not None:
        return update(tenant_id=tenant_id, project_id=project_id, changes={"authorizationToken": data.authorization_token, "bugsnagProjectId": data.bugsnag_project_id})
    else:
        return add(tenant_id=tenant_id, project_id=project_id, authorization_token=data.authorization_token, bugsnag_project_id=data.bugsnag_project_id)
