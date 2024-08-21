# 这段代码定义了若干个用于操作和查询与项目中的问题（issues）相关的函数。
# 通过这些函数，可以获取特定问题的详细信息，查询与会话（session）相关的问题，获取项目中所有问题类型的可视化信息，以及返回所有可能的问题类型及其默认排序和名称。
# 这段代码提供了一组工具函数，用于管理和查询与项目相关的问题数据。通过这些函数，系统可以方便地获取和展示问题的详细信息、会话中的问题，以及项目中的所有问题类型。
# 函数通过与数据库的交互，实现了对问题数据的高效管理和查询。
from chalicelib.utils import pg_client, helper

# 定义支持的所有问题类型列表
ISSUE_TYPES = ["click_rage", "dead_click", "excessive_scrolling", "bad_request", "missing_resource", "memory", "cpu", "slow_resource", "slow_page_load", "crash", "ml_cpu", "ml_memory", "ml_dead_click", "ml_click_rage", "ml_mouse_thrashing", "ml_excessive_scrolling", "ml_slow_resources", "custom", "js_exception", "custom_event_error", "js_error"]
# 定义查询中用于排序的问题类型顺序
ORDER_QUERY = """\
(CASE   WHEN type = 'js_exception' THEN 0
        WHEN type = 'bad_request' THEN 1
        WHEN type = 'missing_resource' THEN 2
        WHEN type = 'click_rage' THEN 3
        WHEN type = 'dead_click' THEN 4
        WHEN type = 'memory' THEN 5
        WHEN type = 'cpu' THEN 6
        WHEN type = 'crash' THEN 7
        ELSE -1 END)::INTEGER 
"""
# 定义查询中用于显示的问题类型名称
NAME_QUERY = """\
(CASE   WHEN type = 'js_exception' THEN 'Errors'
        WHEN type = 'bad_request' THEN 'Bad Requests'
        WHEN type = 'missing_resource' THEN 'Missing Images'
        WHEN type = 'click_rage' THEN 'Click Rage'
        WHEN type = 'dead_click' THEN 'Dead Clicks'
        WHEN type = 'memory' THEN 'High Memory'
        WHEN type = 'cpu' THEN 'High CPU'
        WHEN type = 'crash' THEN 'Crashes'
        ELSE type::text END)::text 
"""


# 函数：get
# 功能：获取特定问题的详细信息
# 参数：
# - project_id: 项目ID，用于标识项目。
# - issue_id: 问题ID，用于标识具体的问题。
# 返回值：
# - 返回包含问题详细信息的字典。
def get(project_id, issue_id):
    with pg_client.PostgresClient() as cur:
        query = cur.mogrify(
            """\
            SELECT
                *
            FROM public.issues
            WHERE project_id = %(project_id)s
                AND issue_id = %(issue_id)s;""",
            {"project_id": project_id, "issue_id": issue_id},
        )
        cur.execute(query=query)
        data = cur.fetchone()
        if data is not None:
            data["title"] = helper.get_issue_title(data["type"])
    return helper.dict_to_camel_case(data)


# 函数：get_by_session_id
# 功能：根据会话ID获取相关问题的详细信息
# 参数：
# - session_id: 会话ID，用于标识会话。
# - project_id: 项目ID，用于标识项目。
# - issue_type: 问题类型（可选），用于过滤特定类型的问题。
# 返回值：
# - 返回包含相关问题详细信息的列表。
def get_by_session_id(session_id, project_id, issue_type=None):
    with pg_client.PostgresClient() as cur:
        cur.execute(
            cur.mogrify(
                f"""\
                    SELECT *
                    FROM events_common.issues
                             INNER JOIN public.issues USING (issue_id)
                    WHERE session_id = %(session_id)s 
                        AND project_id= %(project_id)s
                        {"AND type = %(type)s" if issue_type is not None else ""}
                    ORDER BY timestamp;""",
                {"session_id": session_id, "project_id": project_id, "type": issue_type},
            )
        )
        return helper.list_to_camel_case(cur.fetchall())


# 函数：get_types_by_project
# 功能：获取项目中所有问题类型的信息，包括可见性、排序和名称。
# 参数：
# - project_id: 项目ID，用于标识项目。
# 返回值：
# - 返回包含问题类型信息的列表。
def get_types_by_project(project_id):
    with pg_client.PostgresClient() as cur:
        cur.execute(
            cur.mogrify(
                f"""SELECT type,
                               {ORDER_QUERY}>=0 AS visible,
                               {ORDER_QUERY} AS order,
                               {NAME_QUERY} AS name
                            FROM (SELECT DISTINCT type
                                  FROM public.issues
                                  WHERE project_id = %(project_id)s) AS types
                            ORDER BY "order";""",
                {"project_id": project_id},
            )
        )
        return helper.list_to_camel_case(cur.fetchall())


# 函数：get_all_types
# 功能：获取所有问题类型及其默认的排序和名称。
# 返回值：
# - 返回包含所有问题类型及其信息的列表。
def get_all_types():
    return [
        {"type": "js_exception", "visible": True, "order": 0, "name": "Errors"},
        {"type": "bad_request", "visible": True, "order": 1, "name": "Bad Requests"},
        {"type": "missing_resource", "visible": True, "order": 2, "name": "Missing Images"},
        {"type": "click_rage", "visible": True, "order": 3, "name": "Click Rage"},
        {"type": "dead_click", "visible": True, "order": 4, "name": "Dead Clicks"},
        {"type": "memory", "visible": True, "order": 5, "name": "High Memory"},
        {"type": "cpu", "visible": True, "order": 6, "name": "High CPU"},
        {"type": "crash", "visible": True, "order": 7, "name": "Crashes"},
    ]
