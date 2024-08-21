# 文件的整体目的是定期检查和报告系统中各个服务和组件的运行状况，以确保整个应用程序生态系统的健康和稳定运行。
from urllib.parse import urlparse

import redis
import requests
from decouple import config

from chalicelib.utils import pg_client
from chalicelib.utils.TimeUTC import TimeUTC

# 根据服务名称、端口号和路径生成连接字符串，用于访问各个服务的健康检查端点。
def app_connection_string(name, port, path):
    namespace = config("POD_NAMESPACE", default="app")
    conn_string = config("CLUSTER_URL", default="svc.cluster.local")
    return f"http://{'.'.join(filter(None,[name,namespace,conn_string]))}:{port}/{path}"


# 是一个字典，包含了不同服务的健康检查端点，通过 app_connection_string 函数生成
HEALTH_ENDPOINTS = {
    "alerts": app_connection_string("alerts-openreplay", 8888, "health"),
    "assets": app_connection_string("assets-openreplay", 8888, "metrics"),
    "assist": app_connection_string("assist-openreplay", 8888, "health"),
    "chalice": app_connection_string("chalice-openreplay", 8888, "metrics"),
    "db": app_connection_string("db-openreplay", 8888, "metrics"),
    "ender": app_connection_string("ender-openreplay", 8888, "metrics"),
    "heuristics": app_connection_string("heuristics-openreplay", 8888, "metrics"),
    "http": app_connection_string("http-openreplay", 8888, "metrics"),
    "ingress-nginx": app_connection_string("ingress-nginx-openreplay", 80, "healthz"),
    "integrations": app_connection_string("integrations-openreplay", 8888, "metrics"),
    "peers": app_connection_string("peers-openreplay", 8888, "health"),
    "sink": app_connection_string("sink-openreplay", 8888, "metrics"),
    "sourcemapreader": app_connection_string("sourcemapreader-openreplay", 8888, "health"),
    "storage": app_connection_string("storage-openreplay", 8888, "metrics"),
}


# 检查PostgreSQL数据库的运行状态和版本信息
def __check_database_pg(*_):
    fail_response = {"health": False, "details": {"errors": ["Postgres health-check failed"]}}
    with pg_client.PostgresClient() as cur:
        try:
            # SHOW server_version;：这是一个 PostgreSQL 的 SQL 命令，用于显示当前连接的 PostgreSQL 数据库的版本信息。这个命令会返回数据库服务器的版本号
            # ur.execute("SHOW server_version;") 用于在 PostgreSQL 数据库上执行 SHOW server_version; SQL 命令，来获取并显示数据库的版本信息。
            cur.execute("SHOW server_version;")
            server_version = cur.fetchone()
        except Exception as e:
            print("!! 健康检查失败：postgres 没有响应")
            print(str(e))
            return fail_response
        try:
            cur.execute("SELECT openreplay_version() AS version;")
            schema_version = cur.fetchone()
        except Exception as e:
            print("!! 健康检查失败：未定义 openreplay_version")
            print(str(e))
            return fail_response
    return {
        "health": True,
        "details": {
            # "version": server_version["server_version"],
            # "schema": schema_version["version"]
        },
    }

# *_ 是一种不常见但有效的命名方式，表示函数接收任意数量的位置参数，但这些参数在函数体中并不使用。下划线 _ 通常用作一个占位符，表示这个变量或参数是被故意忽略的、不重要的
# 使用场景
# 兼容性：当你希望函数能够接受任意参数（以保持与其他函数签名一致），但实际上并不需要使用这些参数时，可以使用这种语法。
# 占位符：在某些场景下，使用 _ 作为变量或参数名称表示它们不重要或不使用，这是一种约定俗成的方式。
def __not_supported(*_):
    return {"errors": ["not supported"]}

# *_ 是一种不常见但有效的命名方式，表示函数接收任意数量的位置参数，但这些参数在函数体中并不使用。下划线 _ 通常用作一个占位符，表示这个变量或参数是被故意忽略的、不重要的
# 使用场景
# 兼容性：当你希望函数能够接受任意参数（以保持与其他函数签名一致），但实际上并不需要使用这些参数时，可以使用这种语法。
# 占位符：在某些场景下，使用 _ 作为变量或参数名称表示它们不重要或不使用，这是一种约定俗成的方式。
def __always_healthy(*_):
    return {"health": True, "details": {}}


# 动态生成一个检查后端服务（如 alerts, assets, assist 等）的函数，通过向相应服务的健康检查端点发送HTTP请求，来确认服务是否正常运行
def __check_be_service(service_name):
    def fn(*_):
        fail_response = {"health": False, "details": {"errors": ["server health-check failed"]}}
        try:
            results = requests.get(HEALTH_ENDPOINTS.get(service_name), timeout=2)
            if results.status_code != 200:
                print(f"!! issue with the {service_name}-health code:{results.status_code}")
                print(results.text)
                # fail_response["details"]["errors"].append(results.text)
                return fail_response
        except requests.exceptions.Timeout:
            print(f"!! Timeout getting {service_name}-health")
            # fail_response["details"]["errors"].append("timeout")
            return fail_response
        except Exception as e:
            print(f"!! Issue getting {service_name}-health response")
            print(str(e))
            try:
                print(results.text)
                # fail_response["details"]["errors"].append(results.text)
            except Exception:
                print("couldn't get response")
                # fail_response["details"]["errors"].append(str(e))
            return fail_response
        return {"health": True, "details": {}}

    return fn


# 检查Redis服务的运行状态。
def __check_redis(*_):
    fail_response = {"health": False, "details": {"errors": ["server health-check failed"]}}
    if config("REDIS_STRING", default=None) is None:
        # fail_response["details"]["errors"].append("REDIS_STRING not defined in env-vars")
        return fail_response

    try:
        r = redis.from_url(config("REDIS_STRING"))
        r.ping()
    except Exception as e:
        print("!! Issue getting redis-health response")
        print(str(e))
        # fail_response["details"]["errors"].append(str(e))
        return fail_response

    return {
        "health": True,
        "details": {
            # "version": r.execute_command('INFO')['redis_version']
        },
    }


# 检查SSL证书的有效性
def __check_SSL(*_):
    fail_response = {"health": False, "details": {"errors": ["SSL Certificate health-check failed"]}}
    try:
        requests.get(config("SITE_URL"), verify=True, allow_redirects=True)
    except Exception as e:
        print("!! health failed: SSL Certificate")
        print(str(e))
        return fail_response
    return {"health": True, "details": {}}


def __get_sessions_stats(*_):
    with pg_client.PostgresClient() as cur:
        constraints = ["projects.deleted_at IS NULL"]
        query = cur.mogrify(
            f"""SELECT COALESCE(SUM(sessions_count),0) AS s_c,
                                       COALESCE(SUM(events_count),0) AS e_c
                                FROM public.projects_stats
                                     INNER JOIN public.projects USING(project_id)
                                WHERE {" AND ".join(constraints)};"""
        )
        cur.execute(query)
        row = cur.fetchone()
    return {"numberOfSessionsCaptured": row["s_c"], "numberOfEventCaptured": row["e_c"]}


# 函数通过聚合不同的健康检查函数来生成一个整体的健康报告。这个报告包含了数据库、后端服务、Redis、SSL证书的健康状态，还包括了应用程序的整体运行情况
def get_health():
    health_map = {
        "databases": {"postgres": __check_database_pg},
        "ingestionPipeline": {"redis": __check_redis},
        "backendServices": {
            "alerts": __check_be_service("alerts"),
            "assets": __check_be_service("assets"),
            "assist": __check_be_service("assist"),
            "chalice": __always_healthy,
            "db": __check_be_service("db"),
            "ender": __check_be_service("ender"),
            "frontend": __always_healthy,
            "heuristics": __check_be_service("heuristics"),
            "http": __check_be_service("http"),
            "ingress-nginx": __always_healthy,
            "integrations": __check_be_service("integrations"),
            "peers": __check_be_service("peers"),
            "sink": __check_be_service("sink"),
            "sourcemapreader": __check_be_service("sourcemapreader"),
            "storage": __check_be_service("storage"),
        },
        "details": __get_sessions_stats,
        "ssl": __check_SSL,
    }
    return __process_health(health_map=health_map)


# 函数负责处理和过滤健康报告中的信息，根据环境变量配置，有选择地排除某些检查项。
def __process_health(health_map):
    response = dict(health_map)
    for parent_key in health_map.keys():
        if config(f"SKIP_H_{parent_key.upper()}", cast=bool, default=False):
            response.pop(parent_key)
        elif isinstance(health_map[parent_key], dict):
            for element_key in health_map[parent_key]:
                if config(f"SKIP_H_{parent_key.upper()}_{element_key.upper()}", cast=bool, default=False):
                    response[parent_key].pop(element_key)
                else:
                    response[parent_key][element_key] = health_map[parent_key][element_key]()
        else:
            response[parent_key] = health_map[parent_key]()
    return response


# 计划任务
# 目的是定期统计项目的会话和事件数量，并确保 projects_stats 表中的数据是最新的。通过遍历所有项目，该函数能够插入新的统计数据或更新现有数据，从而维持项目统计的准确性和完整性。
def cron():
    # 该函数 cron 使用一个数据库客户端 pg_client.PostgresClient() 连接到数据库。使用 with 语句是为了确保数据库连接在操作完成后自动关闭。
    with pg_client.PostgresClient() as cur:
        query = cur.mogrify(
            """SELECT projects.project_id,
                                      projects.created_at,
                                      projects.sessions_last_check_at,
                                      projects.first_recorded_session_at,
                                      projects_stats.last_update_at
                                FROM public.projects
                                     LEFT JOIN public.projects_stats USING (project_id)
                                WHERE projects.deleted_at IS NULL
                                ORDER BY project_id;"""
        )
        cur.execute(query)
        rows = cur.fetchall()
        for r in rows:
            insert = False
            if r["last_update_at"] is None:
                # never counted before, must insert
                insert = True
                if r["first_recorded_session_at"] is None:
                    if r["sessions_last_check_at"] is None:
                        count_start_from = r["created_at"]
                    else:
                        count_start_from = r["sessions_last_check_at"]
                else:
                    count_start_from = r["first_recorded_session_at"]

            else:
                # 如果项目从未统计过会话和事件数据（即 last_update_at 为空），则标记为需要插入新数据。
                # counted before, must update
                count_start_from = r["last_update_at"]
            # TimeUTC.datetime_to_timestamp() 将时间转换为时间戳格式
            count_start_from = TimeUTC.datetime_to_timestamp(count_start_from)
            # current_timestamp = TimeUTC.now()
            # print(current_timestamp)  # 输出类似于 1729124096000 的毫秒级时间戳
            params = {"project_id": r["project_id"], "start_ts": count_start_from, "end_ts": TimeUTC.now(), "sessions_count": 0, "events_count": 0}

            query = cur.mogrify(
                """SELECT COUNT(1) AS sessions_count,
                                          COALESCE(SUM(events_count),0) AS events_count
                                   FROM public.sessions
                                   WHERE project_id=%(project_id)s
                                      AND start_ts>=%(start_ts)s
                                      AND start_ts<=%(end_ts)s
                                      AND duration IS NOT NULL;""",
                params,
            )
            cur.execute(query)
            row = cur.fetchone()
            if row is not None:
                params["sessions_count"] = row["sessions_count"]
                params["events_count"] = row["events_count"]

            if insert:
                query = cur.mogrify(
                    """INSERT INTO public.projects_stats(project_id, sessions_count, events_count, last_update_at)
                                       VALUES (%(project_id)s, %(sessions_count)s, %(events_count)s, (now() AT TIME ZONE 'utc'::text));""",
                    params,
                )
            else:
                query = cur.mogrify(
                    """UPDATE public.projects_stats
                                       SET sessions_count=sessions_count+%(sessions_count)s,
                                           events_count=events_count+%(events_count)s,
                                           last_update_at=(now() AT TIME ZONE 'utc'::text)
                                       WHERE project_id=%(project_id)s;""",
                    params,
                )
            cur.execute(query)


# this cron is used to correct the sessions&events count every week
# cron 计划 任务
# 主要目的是确保 projects_stats 表中每个项目的 sessions_count 和 events_count 是准确的。它通过重新计算每个项目的所有会话和事件数量来纠正任何潜在的不准确之处。
# 每周执行一次，重新计算所有项目的会话和事件数量，纠正任何潜在的统计错误。
def weekly_cron():
    # 打开一个PostgreSQL数据库连接，并获取一个数据库游标 cur
    with pg_client.PostgresClient(long_query=True) as cur:
        #    mogrify 是 psycopg2 中游标对象的一个方法，用于将 SQL 查询字符串和参数结合，并返回一个完整的 SQL 查询字符串。
        query = cur.mogrify(
            """SELECT project_id,
                                      projects_stats.last_update_at
                               FROM public.projects
                                    LEFT JOIN public.projects_stats USING (project_id)
                               WHERE projects.deleted_at IS NULL
                               ORDER BY project_id;"""
        )
        # 这里执行了实际的 SQL 查询，query 是由 mogrify 生成的完整 SQL 语句。
        # TODO 什么是游标
        # cur.execute() 方法运行该查询并将结果存储在游标对象中。
        cur.execute(query)
        # fetchall() 方法用于获取所有查询结果，并将其存储在 data 变量中。
        rows = cur.fetchall()
        for r in rows:
            if r["last_update_at"] is None:
                continue

            params = {"project_id": r["project_id"], "end_ts": TimeUTC.now(), "sessions_count": 0, "events_count": 0}

            query = cur.mogrify(
                """SELECT COUNT(1) AS sessions_count,
                                          COALESCE(SUM(events_count),0) AS events_count
                                   FROM public.sessions
                                   WHERE project_id=%(project_id)s
                                      AND start_ts<=%(end_ts)s
                                      AND duration IS NOT NULL;""",
                params,
            )
            # cur.execute(query) 是实际执行SQL查询的操作。虽然在前面的代码中构建了SQL语句（使用 cur.mogrify()），但这些语句只是将SQL命令以字符串的形式准备好。真正对数据库进行操作，执行这些SQL命令，是通过 cur.execute(query) 完成的。
            # 如果没有 cur.execute(query)，即使SQL语句已经准备好，数据库也不会发生任何变化（如插入、更新、删除等操作也不会生效）。
            # cur.execute() 使得Python与数据库进行实际的交互。例如，读取数据（SELECT）、更新数据（UPDATE）、删除数据（DELETE）等。
            # 这一步不仅是发出SQL语句，还确保这些语句被数据库接收到并执行，从而在数据库中产生预期的效果。
            cur.execute(query)
            row = cur.fetchone()
            if row is not None:
                params["sessions_count"] = row["sessions_count"]
                params["events_count"] = row["events_count"]

            query = cur.mogrify(
                """UPDATE public.projects_stats
                                   SET sessions_count=%(sessions_count)s,
                                       events_count=%(events_count)s,
                                       last_update_at=(now() AT TIME ZONE 'utc'::text)
                                   WHERE project_id=%(project_id)s;""",
                params,
            )
            cur.execute(query)
