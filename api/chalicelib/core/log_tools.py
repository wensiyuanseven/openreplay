# 这段代码是一个用于管理系统中集成配置的模块，主要负责项目集成信息的增删改查（CRUD）操作。代码通过 PostgreSQL 数据库与系统交互，支持不同类型的集成工具（如日志工具等）的管理。它包括了集成的添加、编辑、删除、搜索和获取等功能。
from chalicelib.utils import pg_client, helper
import json
# 定义一个排除列表，指定哪些集成不包括在结果中
EXCEPT = ["jira_server", "jira_cloud"]

# 函数：search
# 功能：根据项目ID搜索当前系统支持的集成，并返回已集成的项目列表。
# 参数：
# - project_id: 项目ID，用于标识具体的项目。
# 返回值：
# - 包含已集成的工具信息的字典列表。
def search(project_id):
    result = []
    with pg_client.PostgresClient() as cur:
        cur.execute(
            cur.mogrify(
                """\
                SELECT supported_integrations.name,
                       (SELECT COUNT(*)
                        FROM public.integrations
                                 INNER JOIN public.projects USING (project_id)
                        WHERE provider = supported_integrations.name
                          AND project_id = %(project_id)s
                          AND projects.deleted_at ISNULL
                        LIMIT 1) AS count
                FROM unnest(enum_range(NULL::integration_provider)) AS supported_integrations(name);""",
                {"project_id": project_id},
            )
        )
        r = cur.fetchall()
        for k in r:
            if k["count"] > 0 and k["name"] not in EXCEPT:
                result.append({"value": helper.key_to_camel_case(k["name"]), "type": "logTool"})
        return {"data": result}

# 函数：add
# 功能：为指定项目添加一个新的集成配置。
# 参数：
# - project_id: 项目ID，用于标识具体的项目。
# - integration: 集成类型（如日志工具）。
# - options: 一个字典，包含集成的配置信息。
# 返回值：
# - 返回新添加的集成配置信息。
def add(project_id, integration, options):
    options = json.dumps(options)
    with pg_client.PostgresClient() as cur:
        cur.execute(
            cur.mogrify(
                """\
                INSERT INTO public.integrations(project_id, provider, options) 
                VALUES (%(project_id)s, %(provider)s, %(options)s::jsonb)
                RETURNING *;""",
                {"project_id": project_id, "provider": integration, "options": options},
            )
        )
        r = cur.fetchone()
    return helper.dict_to_camel_case(helper.flatten_nested_dicts(r))

# 函数：get
# 功能：获取指定项目的特定集成配置。
# 参数：
# - project_id: 项目ID，用于标识具体的项目。
# - integration: 集成类型（如日志工具）。
# 返回值：
# - 返回集成配置信息。
def get(project_id, integration):
    with pg_client.PostgresClient() as cur:
        cur.execute(
            cur.mogrify(
                """\
                SELECT integrations.* 
                FROM public.integrations INNER JOIN public.projects USING(project_id)
                WHERE provider = %(provider)s 
                    AND project_id = %(project_id)s
                    AND projects.deleted_at ISNULL
                LIMIT 1;""",
                {"project_id": project_id, "provider": integration},
            )
        )
        r = cur.fetchone()
    return helper.dict_to_camel_case(helper.flatten_nested_dicts(r))

# 函数：get_all_by_type
# 功能：根据集成类型获取所有集成配置。
# 参数：
# - integration: 集成类型（如日志工具）。
# 返回值：
# - 返回符合条件的集成配置信息列表。
def get_all_by_type(integration):
    with pg_client.PostgresClient() as cur:
        cur.execute(
            cur.mogrify(
                """\
                SELECT integrations.* 
                FROM public.integrations INNER JOIN public.projects USING(project_id)
                WHERE provider = %(provider)s AND projects.deleted_at ISNULL;""",
                {"provider": integration},
            )
        )
        r = cur.fetchall()
    return helper.list_to_camel_case(r, flatten=True)

# 函数：edit
# 功能：编辑指定项目的集成配置。
# 参数：
# - project_id: 项目ID，用于标识具体的项目。
# - integration: 集成类型（如日志工具）。
# - changes: 包含需要更新的配置信息的字典。
# 返回值：
# - 返回更新后的集成配置信息。
def edit(project_id, integration, changes):
    if "projectId" in changes:
        changes.pop("project_id")
    if "integration" in changes:
        changes.pop("integration")
    if len(changes.keys()) == 0:
        return None
    with pg_client.PostgresClient() as cur:
        cur.execute(
            cur.mogrify(
                """\
                    UPDATE public.integrations
                    SET options=options||%(changes)s
                    WHERE project_id =%(project_id)s AND provider = %(provider)s 
                    RETURNING *;""",
                {"project_id": project_id, "provider": integration, "changes": json.dumps(changes)},
            )
        )
        return helper.dict_to_camel_case(helper.flatten_nested_dicts(cur.fetchone()))

# 函数：delete
# 功能：删除指定项目的集成配置。
# 参数：
# - project_id: 项目ID，用于标识具体的项目。
# - integration: 集成类型（如日志工具）。
# 返回值：
# - 返回删除操作的状态信息。
def delete(project_id, integration):
    with pg_client.PostgresClient() as cur:
        cur.execute(
            cur.mogrify(
                """\
                    DELETE FROM public.integrations
                    WHERE project_id=%(project_id)s AND provider=%(provider)s;""",
                {"project_id": project_id, "provider": integration},
            )
        )
        return {"state": "success"}

# 函数：get_all_by_tenant
# 功能：根据租户ID和集成类型获取该租户下所有项目的集成配置信息。
# 参数：
# - tenant_id: 租户ID，用于标识集成操作的租户。
# - integration: 集成类型（如日志工具）。
# 返回值：
# - 返回符合条件的集成配置信息列表。
def get_all_by_tenant(tenant_id, integration):
    with pg_client.PostgresClient() as cur:
        cur.execute(
            cur.mogrify(
                """SELECT integrations.*
                    FROM public.integrations INNER JOIN public.projects USING(project_id) 
                    WHERE provider = %(provider)s 
                        AND projects.deleted_at ISNULL;""",
                {"provider": integration},
            )
        )
        r = cur.fetchall()
    return helper.list_to_camel_case(r, flatten=True)
