# 这段代码定义了一个函数 get_by_session_id，用于从数据库中检索特定会话的资源事件（如网页加载时间、URL、资源类型等）。该函数使用 PostgreSQL 数据库，通过 SQL 查询获取与特定会话 ID 和项目 ID 相关的资源事件信息，并返回这些事件的详细信息。
from chalicelib.utils import helper, pg_client
from decouple import config

# 功能描述：
# 从数据库中获取指定会话 ID 和项目 ID 的资源事件信息，并根据给定的时间戳和持续时间进行过滤。

# 参数：
# session_id: 会话的唯一标识符，用于从数据库中查找与该会话相关的事件。
# project_id: 项目的唯一标识符，用于确保查询的事件属于指定的项目。
# start_ts: 会话开始的时间戳，用于确定会话的时间范围。
# duration: 持续时间，表示会话的持续时间，用于进一步过滤资源事件。
# 返回值：
# List[dict]: 包含资源事件信息的字典列表，每个字典包含事件的详细信息。
def get_by_session_id(session_id, project_id, start_ts, duration):
    with pg_client.PostgresClient() as cur:
        if duration is None or (type(duration) != 'int' and type(duration) != 'float') or duration < 0:
            duration = 0
        delta = config("events_ts_delta", cast=int, default=60 * 60) * 1000
        ch_query = """\
                SELECT
                      timestamp AS datetime,
                      url,
                      type,
                      resources.duration AS duration,
                      ttfb,
                      header_size,
                      encoded_body_size,
                      decoded_body_size,
                      success,
                      COALESCE(CASE WHEN status=0 THEN NULL ELSE status END, CASE WHEN success THEN 200 END) AS status
                FROM events.resources INNER JOIN sessions USING (session_id)
                WHERE session_id = %(session_id)s 
                    AND project_id= %(project_id)s
                    AND sessions.start_ts=%(start_ts)s
                    AND resources.timestamp>=%(res_start_ts)s
                    AND resources.timestamp<=%(res_end_ts)s;"""
        params = {"session_id": session_id, "project_id": project_id, "start_ts": start_ts, "duration": duration,
                  "res_start_ts": start_ts - delta, "res_end_ts": start_ts + duration + delta, }
        cur.execute(cur.mogrify(ch_query, params))
        rows = cur.fetchall()
        return helper.list_to_camel_case(rows)


# 关键点
# 参数验证: 函数首先验证 duration 参数的有效性，如果不符合要求，会自动设置为 0。
# 时间窗口: 查询的时间范围不仅包括 start_ts 和 duration，还加上了配置的 delta 值，用于扩展查询的时间范围，确保不会遗漏边界事件。
# SQL 查询: 使用 SQL 查询从数据库中检索与会话相关的资源事件，并根据时间范围进行过滤。
# 数据处理: 查询结果在返回前被转换为驼峰命名法格式，以便于与前端接口的字段命名保持一致。
# 通过这种方式，函数能够有效地从数据库中获取特定会话的资源事件信息，并返回结构化的数据。如果有进一步的问题或需要更多帮助，请随时告知我！