# 这段代码定义了一个函数 get_global_integrations_status，用于获取某个项目的各种第三方集成（如 GitHub、JIRA、Slack 等）的当前状态。
# 函数通过查询数据库，检查用户和项目是否已与这些服务进行集成，并返回集成状态的列表。
import schemas
from chalicelib.utils import pg_client


# 函数：get_global_integrations_status
# 功能：获取指定项目的各种第三方集成状态。
# 参数：
# - tenant_id: 租户ID，用于标识集成操作的租户。
# - user_id: 用户ID，用于标识进行集成操作的用户。
# - project_id: 项目ID，用于标识进行集成操作的项目。
# 返回值：
# - 返回一个列表，列表中包含每个集成的名称及其集成状态（True 或 False）。
def get_global_integrations_status(tenant_id, user_id, project_id):
    # 执行数据库查询，检查每个集成的存在状态
    with pg_client.PostgresClient() as cur:
        cur.execute(
            cur.mogrify(
                f"""\
                    SELECT EXISTS((SELECT 1
                               FROM public.oauth_authentication
                               WHERE user_id = %(user_id)s
                                 AND provider = 'github')) AS {schemas.IntegrationType.github.value},
                           EXISTS((SELECT 1
                                   FROM public.jira_cloud
                                   WHERE user_id = %(user_id)s)) AS {schemas.IntegrationType.jira.value},
                           EXISTS((SELECT 1
                                   FROM public.integrations
                                   WHERE project_id=%(project_id)s 
                                        AND provider='bugsnag')) AS {schemas.IntegrationType.bugsnag.value},
                           EXISTS((SELECT 1
                                   FROM public.integrations
                                   WHERE project_id=%(project_id)s 
                                        AND provider='cloudwatch')) AS {schemas.IntegrationType.cloudwatch.value},
                           EXISTS((SELECT 1
                                   FROM public.integrations
                                   WHERE project_id=%(project_id)s 
                                        AND provider='datadog')) AS {schemas.IntegrationType.datadog.value},
                           EXISTS((SELECT 1
                                   FROM public.integrations
                                   WHERE project_id=%(project_id)s 
                                        AND provider='newrelic')) AS {schemas.IntegrationType.newrelic.value},
                           EXISTS((SELECT 1
                                   FROM public.integrations
                                   WHERE project_id=%(project_id)s 
                                        AND provider='rollbar')) AS {schemas.IntegrationType.rollbar.value},
                           EXISTS((SELECT 1
                                   FROM public.integrations
                                   WHERE project_id=%(project_id)s 
                                        AND provider='sentry')) AS {schemas.IntegrationType.sentry.value},
                           EXISTS((SELECT 1
                                   FROM public.integrations
                                   WHERE project_id=%(project_id)s 
                                        AND provider='stackdriver')) AS {schemas.IntegrationType.stackdriver.value},
                           EXISTS((SELECT 1
                                   FROM public.integrations
                                   WHERE project_id=%(project_id)s 
                                        AND provider='sumologic')) AS {schemas.IntegrationType.sumologic.value},
                           EXISTS((SELECT 1
                                   FROM public.integrations
                                   WHERE project_id=%(project_id)s 
                                        AND provider='elasticsearch')) AS {schemas.IntegrationType.elasticsearch.value},
                           EXISTS((SELECT 1
                                   FROM public.webhooks
                                   WHERE type='slack' AND deleted_at ISNULL)) AS {schemas.IntegrationType.slack.value},
                           EXISTS((SELECT 1
                                   FROM public.webhooks
                                   WHERE type='msteams' AND deleted_at ISNULL)) AS {schemas.IntegrationType.ms_teams.value};""",
                {"user_id": user_id, "tenant_id": tenant_id, "project_id": project_id},
            )
        )
        current_integrations = cur.fetchone()
    result = []
    # 将查询结果转换为包含集成状态的列表
    for k in current_integrations.keys():
        result.append({"name": k, "integrated": current_integrations[k]})
    return result


# 代码解析
# get_global_integrations_status 函数：

# 这个函数用于查询数据库，以确定指定用户和项目是否已集成了多个第三方服务（如 GitHub、JIRA、Slack 等）。每个集成的状态以布尔值的形式返回。
# cur.execute 和 cur.mogrify：

# cur.execute 是执行 SQL 查询的函数，cur.mogrify 用于格式化查询语句并填充参数。这里使用了多个 EXISTS 子查询来检查特定集成是否存在。
# EXISTS 子查询：

# 每个 EXISTS 子查询都会返回一个布尔值，表示指定的集成是否存在于数据库中。例如，检查用户是否已与 GitHub 进行了集成，或者项目是否已与 Sentry 进行了集成。
# current_integrations：

# 这是一个字典，包含了所有集成的状态（True 或 False），键是集成的名称，值是其状态。
# result 列表：

# 最后，将查询结果转换为一个包含每个集成名称和其状态的字典列表，并返回该列表。
# 总结
# get_global_integrations_status 函数是一个用于检查项目和用户与各种第三方服务集成状态的实用工具。通过查询数据库，函数返回一个列表，其中包含每个集成的名称和集成状态。这使得系统可以方便地跟踪和管理这些集成的启用情况。