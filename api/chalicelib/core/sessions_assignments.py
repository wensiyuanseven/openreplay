# 这段代码主要负责管理项目中的任务分配和集成工具的相关操作。包括创建新的任务分配、获取任务信息、向任务添加评论等操作。代码通过与不同的集成工具（如 JIRA、GitHub 等）交互，实现了对任务的创建、获取和更新。
from decouple import config
from chalicelib.utils import helper
from chalicelib.utils.TimeUTC import TimeUTC
from chalicelib.utils import pg_client
from chalicelib.core import integrations_manager, integration_base_issue
import json

# 功能描述：
# 从数据库中获取已保存的分配数据。


# 参数：
# project_id: 项目ID。
# session_id: 会话ID。
# issue_id: 任务ID。
# tool: 集成工具的名称。
# 返回值：
# dict: 返回分配数据，如果未找到则返回 None。
# 代码详解：
# 通过 SQL 查询从 assigned_sessions 表中获取指定 session_id、issue_id 和 provider 的数据。
# 将查询结果转换为驼峰命名格式返回。
def __get_saved_data(project_id, session_id, issue_id, tool):
    with pg_client.PostgresClient() as cur:
        query = cur.mogrify(
            f"""\
                    SELECT *
                    FROM public.assigned_sessions
                    WHERE  
                        session_id = %(session_id)s
                        AND issue_id = %(issue_id)s
                        AND provider = %(provider)s;\
    """,
            {"session_id": session_id, "issue_id": issue_id, "provider": tool.lower()},
        )
        cur.execute(query)
        return helper.dict_to_camel_case(cur.fetchone())


# 功能描述：
# 创建新的任务分配并将其保存到数据库中。


# 参数：
# tenant_id: 租户ID。
# project_id: 项目ID。
# session_id: 会话ID。
# creator_id: 创建者ID。
# assignee: 被分配者。
# description: 任务描述。
# title: 任务标题。
# issue_type: 任务类型。
# integration_project_id: 集成工具中的项目ID。
# 返回值：
# dict: 返回创建的任务信息，如果发生错误则返回错误信息。
def create_new_assignment(tenant_id, project_id, session_id, creator_id, assignee, description, title, issue_type, integration_project_id):
    error, integration = integrations_manager.get_integration(tenant_id=tenant_id, user_id=creator_id)
    if error is not None:
        return error

    i = integration.get()

    if i is None:
        return {"errors": [f"integration not found"]}
    link = config("SITE_URL") + f"/{project_id}/session/{session_id}"
    description += f"\n> {link}"
    try:
        issue = integration.issue_handler.create_new_assignment(title=title, assignee=assignee, description=description, issue_type=issue_type, integration_project_id=integration_project_id)
    except integration_base_issue.RequestException as e:
        return integration_base_issue.proxy_issues_handler(e)
    if issue is None or "id" not in issue:
        return {"errors": ["something went wrong while creating the issue"]}
    with pg_client.PostgresClient() as cur:
        query = cur.mogrify(
            """\
                INSERT INTO public.assigned_sessions(session_id, issue_id, created_by, provider,provider_data) 
                VALUES (%(session_id)s, %(issue_id)s, %(creator_id)s, %(provider)s,%(provider_data)s);\
            """,
            {"session_id": session_id, "creator_id": creator_id, "issue_id": issue["id"], "provider": integration.provider.lower(), "provider_data": json.dumps({"integrationProjectId": integration_project_id})},
        )
        cur.execute(query)
    issue["provider"] = integration.provider.lower()
    return issue


# 功能描述：
# 获取所有任务分配信息。


# 参数：
# project_id: 项目ID。
# user_id: 用户ID。
# 返回值：
# List[dict]: 返回包含所有任务分配信息的列表。
# 代码详解：
# 获取用户的可用集成工具列表。
# 构建 SQL 查询条件，获取所有符合条件的任务分配信息。
# 将查询结果转换为驼峰命名格式，并格式化时间戳。
# 返回任务分配信息列表。
def get_all(project_id, user_id):
    available_integrations = integrations_manager.get_available_integrations(user_id=user_id)
    no_integration = not any(available_integrations.values())
    if no_integration:
        return []
    all_integrations = all(available_integrations.values())
    extra_query = ["sessions.project_id = %(project_id)s"]
    if not all_integrations:
        extra_query.append("provider IN %(providers)s")
    with pg_client.PostgresClient() as cur:
        query = cur.mogrify(
            f"""\
                SELECT assigned_sessions.*
                FROM public.assigned_sessions
                    INNER JOIN public.sessions USING (session_id)
                WHERE {" AND ".join(extra_query)};\
""",
            {"project_id": project_id, "providers": tuple(d for d in available_integrations if available_integrations[d])},
        )
        cur.execute(query)
        assignments = helper.list_to_camel_case(cur.fetchall())
        for a in assignments:
            a["createdAt"] = TimeUTC.datetime_to_timestamp(a["createdAt"])
        return assignments


# 功能描述：
# 根据会话ID获取相关任务分配信息。


# 参数：
# tenant_id: 租户ID。
# user_id: 用户ID。
# project_id: 项目ID。
# session_id: 会话ID。
# 返回值：
# List[dict]: 返回与会话相关的任务分配信息。
# 代码详解：
# 获取用户的可用集成工具列表。
# 构建 SQL 查询条件，获取与指定会话相关的任务分配信息。
# 对每个集成工具，调用其API获取任务详细信息，并将结果合并返回。
def get_by_session(tenant_id, user_id, project_id, session_id):
    available_integrations = integrations_manager.get_available_integrations(user_id=user_id)
    if not any(available_integrations.values()):
        return []
    extra_query = ["session_id = %(session_id)s", "provider IN %(providers)s"]
    with pg_client.PostgresClient() as cur:
        query = cur.mogrify(
            f"""\
                SELECT *
                FROM public.assigned_sessions
                WHERE {" AND ".join(extra_query)};""",
            {"session_id": session_id, "providers": tuple([k for k in available_integrations if available_integrations[k]])},
        )
        cur.execute(query)
        results = cur.fetchall()
    issues = {}
    for i in results:
        if i["provider"] not in issues.keys():
            issues[i["provider"]] = []

        issues[i["provider"]].append({"integrationProjectId": i["provider_data"]["integrationProjectId"], "id": i["issue_id"]})
    results = []
    for tool in issues.keys():
        error, integration = integrations_manager.get_integration(tool=tool, tenant_id=tenant_id, user_id=user_id)
        if error is not None:
            return error

        i = integration.get()
        if i is None:
            print("integration not found")
            continue

        r = integration.issue_handler.get_by_ids(saved_issues=issues[tool])
        for i in r["issues"]:
            i["provider"] = tool
        results += r["issues"]
    return results


# 功能描述：
# 获取指定任务的详细信息。


# 参数：
# tenant_id: 租户ID。
# user_id: 用户ID。
# project_id: 项目ID。
# session_id: 会话ID。
# assignment_id: 任务ID。
# 返回值：
# dict: 返回任务的详细信息，如果未找到任务或集成工具，返回错误信息。
def get(tenant_id, user_id, project_id, session_id, assignment_id):
    error, integration = integrations_manager.get_integration(tenant_id=tenant_id, user_id=user_id)
    if error is not None:
        return error
    l = __get_saved_data(project_id, session_id, assignment_id, tool=integration.provider)
    if l is None:
        return {"errors": ["issue not found"]}
    i = integration.get()
    if i is None:
        return {"errors": ["integration not found"]}
    r = integration.issue_handler.get(integration_project_id=l["providerData"]["integrationProjectId"], assignment_id=assignment_id)

    r["provider"] = integration.provider.lower()
    return r


# 功能描述：
# 在指定任务中添加评论。


# 参数：
# tenant_id: 租户ID。
# user_id: 用户ID。
# project_id: 项目ID。
# session_id: 会话ID。
# assignment_id: 任务ID。
# message: 评论内容。
# 返回值：
# dict: 返回评论操作的结果。
def comment(tenant_id, user_id, project_id, session_id, assignment_id, message):
    error, integration = integrations_manager.get_integration(tenant_id=tenant_id, user_id=user_id)
    if error is not None:
        return error
    i = integration.get()

    if i is None:
        return {"errors": [f"integration not found"]}
    l = __get_saved_data(project_id, session_id, assignment_id, tool=integration.provider)

    return integration.issue_handler.comment(integration_project_id=l["providerData"]["integrationProjectId"], assignment_id=assignment_id, comment=message)


# 关键点
# 集成工具交互: 代码中涉及多个集成工具的交互操作，如创建任务、获取任务信息、添加评论等。这些操作通过 integration_manager 和 integration.issue_handler 来实现。
# 数据库操作: 任务的创建、查询等操作均需要与 PostgreSQL 数据库交互，通过 pg_client 实现。
# 错误处理: 对每个可能失败的操作均进行了错误处理，如集成工具未找到、API 请求失败等。
# 这段代码实现了复杂的任务分配管理功能，并通过集成工具的 API 实现了与外部系统的互操作。如果有进一步的问题或需要更多帮助，请随时告知我！
