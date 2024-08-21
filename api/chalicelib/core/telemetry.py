# 该脚本主要用于租户管理系统中，帮助开发者自动化地收集、更新并上传租户的使用数据和统计信息。
from chalicelib.utils import pg_client
import requests
from chalicelib.core import license
# 该脚本主要用于管理和维护租户管理系统中的租户统计信息和使用数据。它自动化地收集租户的使用数据并将其发送到指定的远程服务器，以便进行统计和分析。此功能帮助开发者跟踪租户的使用情况并进行相关的系统管理。

# 功能描述:
# 将从数据库中提取的租户信息转换为所需的格式，以便发送到远程服务器进行处理。
# 参数:
# data: 包含租户信息的字典，从数据库中提取。
# 返回值:
# 返回一个格式化后的字典，包含了租户的关键信息，如版本号、用户ID、项目数、会话数等。
def process_data(data):
    return {
        "edition": license.EDITION,
        "tracking": data["opt_out"],
        "version": data["version_number"],
        "user_id": data["tenant_key"],
        "tenant_key": data["tenant_key"],
        "owner_email": None if data["opt_out"] else data["email"],
        "organization_name": None if data["opt_out"] else data["name"],
        "users_count": data["t_users"],
        "projects_count": data["t_projects"],
        "sessions_count": data["t_sessions"],
        "integrations_count": data["t_integrations"],
    }

# 功能描述:
# 计算并更新租户的统计数据，然后将这些数据发送到远程服务器以进行进一步的处理。
# compute() 函数 用于定期更新并发送租户的统计数据。
def compute():
    with pg_client.PostgresClient(long_query=True) as cur:
        cur.execute(
            f"""UPDATE public.tenants
                SET t_integrations = COALESCE((SELECT COUNT(DISTINCT provider) FROM public.integrations) +
                                              (SELECT COUNT(*) FROM public.webhooks WHERE type = 'slack') +
                                              (SELECT COUNT(*) FROM public.jira_cloud), 0),
                    t_projects=COALESCE((SELECT COUNT(*) FROM public.projects WHERE deleted_at ISNULL), 0),
                    t_sessions=t_sessions + COALESCE((SELECT COUNT(*)
                                                      FROM public.sessions
                                                      WHERE start_ts >= (SELECT last_telemetry FROM tenants)
                                                        AND start_ts <=CAST(EXTRACT(epoch FROM date_trunc('day', now())) * 1000 AS BIGINT)), 0),
                    t_users=COALESCE((SELECT COUNT(*) FROM public.users WHERE deleted_at ISNULL), 0),
                    last_telemetry=CAST(EXTRACT(epoch FROM date_trunc('day', now())) * 1000 AS BIGINT)
                RETURNING name,t_integrations,t_projects,t_sessions,t_users,tenant_key,opt_out,
                    (SELECT openreplay_version()) AS version_number,(SELECT email FROM public.users WHERE role = 'owner' LIMIT 1);"""
        )
        data = cur.fetchone()
        if len(data) > 0:
            # 向指定的 URL 发送 HTTP POST 请求，并携带 JSON 格式的请求体。具体来说，它向 https://api.openreplay.com/os/telemetry 发送了一个包含统计数据的请求
            # json 参数用于指定要作为请求体发送的 JSON 数据。requests 库会自动将 Python 字典或列表序列化为 JSON 格式，并设置正确的 Content-Type 头（application/json）。
            # {
            #     "stats": [
            #         {
            #             "edition": "Some Edition",
            #             "tracking": false,
            #             "version": "1.0.0",
            #             "user_id": "some_user_id",
            #             "tenant_key": "some_tenant_key",
            #             "owner_email": "owner@example.com",
            #             "organization_name": "Some Organization",
            #             "users_count": 5,
            #             "projects_count": 10,
            #             "sessions_count": 1000,
            #             "integrations_count": 3
            #         }
            #     ]
            # }

            requests.post("https://api.openreplay.com/os/telemetry", json={"stats": [process_data(data)]})

# 在新租户注册时，向远程服务器发送包含初始信息的数据包。
# new_client() 函数 用于在新客户端注册时发送初始信息。
def new_client():
    with pg_client.PostgresClient() as cur:
        cur.execute(
            f"""SELECT *, openreplay_version() AS version_number,
                (SELECT email FROM public.users WHERE role='owner' LIMIT 1) AS email
                FROM public.tenants
                LIMIT 1;"""
        )
        data = cur.fetchone()
        requests.post("https://api.openreplay.com/os/signup", json=process_data(data))
