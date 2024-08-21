# 这段代码的主要功能是为租户（tenant_id）生成一个任务列表，这些任务帮助租户完成 OpenReplay 的设置和配置过程。
# 代码中的各个函数分别检查某些条件是否满足，并根据这些条件返回任务的状态（是否完成）和相关的文档或管理页面的链接。
from chalicelib.utils import pg_client
from chalicelib.core import projects, log_tool_datadog, log_tool_stackdriver, log_tool_sentry

from chalicelib.core import users

# 作用:
# 此函数返回一个包含多个任务的列表，每个任务检查 OpenReplay 设置的不同方面是否已经完成，并提供相应的文档链接。
# 传参:
# tenant_id: 一个字符串或整数，表示租户的唯一标识。
# 返回值:
# 一个包含四个字典的列表，每个字典代表一个任务。每个字典包含以下键：
# "task": 任务名称。
# "done": 布尔值，表示该任务是否完成。
# "URL": 相关的文档或管理页面的链接。
def get_state(tenant_id):
    pids = projects.get_projects_ids(tenant_id=tenant_id)
    with pg_client.PostgresClient() as cur:
        recorded = False
        meta = False

        if len(pids) > 0:
            cur.execute(
                cur.mogrify("""SELECT EXISTS((  SELECT 1
                                                FROM public.sessions AS s
                                                WHERE s.project_id IN %(ids)s)) AS exists;""",
                            {"ids": tuple(pids)})
            )
            recorded = cur.fetchone()["exists"]
            meta = False
            if recorded:
                cur.execute("""SELECT EXISTS((SELECT 1
                               FROM public.projects AS p
                                        LEFT JOIN LATERAL ( SELECT 1
                                                            FROM public.sessions
                                                            WHERE sessions.project_id = p.project_id
                                                              AND sessions.user_id IS NOT NULL
                                                            LIMIT 1) AS sessions(user_id) ON (TRUE)
                               WHERE p.deleted_at ISNULL
                                 AND ( sessions.user_id IS NOT NULL OR p.metadata_1 IS NOT NULL
                                       OR p.metadata_2 IS NOT NULL OR p.metadata_3 IS NOT NULL
                                       OR p.metadata_4 IS NOT NULL OR p.metadata_5 IS NOT NULL
                                       OR p.metadata_6 IS NOT NULL OR p.metadata_7 IS NOT NULL
                                       OR p.metadata_8 IS NOT NULL OR p.metadata_9 IS NOT NULL
                                       OR p.metadata_10 IS NOT NULL )
                                   )) AS exists;""")

                meta = cur.fetchone()["exists"]

    return [
        {"task": "Install OpenReplay",
         "done": recorded,
         "URL": "https://docs.openreplay.com/getting-started/quick-start"},
        {"task": "Identify Users",
         "done": meta,
         "URL": "https://docs.openreplay.com/data-privacy-security/metadata"},
        {"task": "Invite Team Members",
         "done": len(users.get_members(tenant_id=tenant_id)) > 1,
         "URL": "https://app.openreplay.com/client/manage-users"},
        {"task": "Integrations",
         "done": len(log_tool_datadog.get_all(tenant_id=tenant_id)) > 0 \
                 or len(log_tool_sentry.get_all(tenant_id=tenant_id)) > 0 \
                 or len(log_tool_stackdriver.get_all(tenant_id=tenant_id)) > 0,
         "URL": "https://docs.openreplay.com/integrations"}
    ]

# 作用:
# 此函数仅检查是否已安装 OpenReplay，判断方法是查看是否有任何会话数据已记录。\
# 传参:
# tenant_id: 一个字符串或整数，表示租户的唯一标识。
# 返回值:
# 一个字典，包含以下键：
# "task": 任务名称（“Install OpenReplay”）。
# "done": 布尔值，表示 OpenReplay 是否已安装（即是否有会话记录）。
# "URL": 安装 OpenReplay 的文档链接。
def get_state_installing(tenant_id):
    pids = projects.get_projects_ids(tenant_id=tenant_id)
    with pg_client.PostgresClient() as cur:
        recorded = False

        if len(pids) > 0:
            cur.execute(
                cur.mogrify("""SELECT EXISTS((  SELECT 1
                                                FROM public.sessions AS s
                                                WHERE s.project_id IN %(ids)s)) AS exists;""",
                            {"ids": tuple(pids)})
            )
            recorded = cur.fetchone()["exists"]

    return {"task": "Install OpenReplay",
            "done": recorded,
            "URL": "https://docs.openreplay.com/getting-started/quick-start"}

# 作用:
# 此函数检查是否已标识用户，判断方法是查看是否存在任何用户 ID 或元数据。

# 传参:
# tenant_id: 一个字符串或整数，表示租户的唯一标识。
# 返回值:
# 一个字典，包含以下键：
# "task": 任务名称（“Identify Users”）。
# "done": 布尔值，表示是否已经标识了用户或存在用户元数据。
# "URL": 用户标识和元数据的文档链接。
def get_state_identify_users(tenant_id):
    with pg_client.PostgresClient() as cur:
        cur.execute("""SELECT EXISTS((SELECT 1
                                       FROM public.projects AS p
                                                LEFT JOIN LATERAL ( SELECT 1
                                                                    FROM public.sessions
                                                                    WHERE sessions.project_id = p.project_id
                                                                      AND sessions.user_id IS NOT NULL
                                                                    LIMIT 1) AS sessions(user_id) ON (TRUE)
                                       WHERE p.deleted_at ISNULL
                                         AND ( sessions.user_id IS NOT NULL OR p.metadata_1 IS NOT NULL
                                               OR p.metadata_2 IS NOT NULL OR p.metadata_3 IS NOT NULL
                                               OR p.metadata_4 IS NOT NULL OR p.metadata_5 IS NOT NULL
                                               OR p.metadata_6 IS NOT NULL OR p.metadata_7 IS NOT NULL
                                               OR p.metadata_8 IS NOT NULL OR p.metadata_9 IS NOT NULL
                                               OR p.metadata_10 IS NOT NULL )
                                           )) AS exists;""")

        meta = cur.fetchone()["exists"]

    return {"task": "Identify Users",
            "done": meta,
            "URL": "https://docs.openreplay.com/data-privacy-security/metadata"}

# 作用:
# 此函数检查是否邀请了团队成员，判断方法是查看当前租户是否有多个用户。

# 传参:

# tenant_id: 一个字符串或整数，表示租户的唯一标识。
# 返回值:

# 一个字典，包含以下键：
# "task": 任务名称（“Invite Team Members”）。
# "done": 布尔值，表示是否已邀请团队成员（即租户中是否有多于一个的用户）。
# "URL": 管理用户的页面链接。
def get_state_manage_users(tenant_id):
    return {"task": "Invite Team Members",
            "done": len(users.get_members(tenant_id=tenant_id)) > 1,
            "URL": "https://app.openreplay.com/client/manage-users"}

# 作用:
# 此函数检查是否配置了日志集成，判断方法是查看是否已配置了 DataDog、Sentry 或 Stackdriver 的集成。

# 传参:

# tenant_id: 一个字符串或整数，表示租户的唯一标识。
# 返回值:

# 一个字典，包含以下键：
# "task": 任务名称（“Integrations”）。
# "done": 布尔值，表示是否配置了任何日志集成。
# "URL": 日志集成的文档链接。
def get_state_integrations(tenant_id):
    return {"task": "Integrations",
            "done": len(log_tool_datadog.get_all(tenant_id=tenant_id)) > 0 \
                    or len(log_tool_sentry.get_all(tenant_id=tenant_id)) > 0 \
                    or len(log_tool_stackdriver.get_all(tenant_id=tenant_id)) > 0,
            "URL": "https://docs.openreplay.com/integrations"}
