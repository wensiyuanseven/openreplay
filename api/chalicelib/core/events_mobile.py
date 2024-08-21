# 这个代码片段主要用于从数据库中获取与iOS会话相关的自定义事件、交互事件（如点击、输入、视图切换、滑动）以及崩溃信息。
# 通过这些功能，系统可以详细记录和分析用户在iOS设备上的会话行为，帮助开发者或运营人员进行故障排查和用户行为分析。
# 注意事项：
# 查询效率：在会话包含大量事件时，查询和排序可能会导致性能问题。建议在使用时注意数据库的索引优化，并考虑分页处理。
# 数据的一致性：由于涉及多个表的联合查询，需要确保相关表的数据一致性，避免因数据更新不及时导致的错误。
from chalicelib.utils import pg_client, helper
from chalicelib.core import events


# 根据会话ID和项目ID获取自定义事件。
# 参数：
# - session_id: 会话ID。
# - project_id: 项目ID。
# 返回值：
# - 返回指定会话的自定义事件列表。
def get_customs_by_session_id(session_id, project_id):
    return events.get_customs_by_session_id(session_id=session_id, project_id=project_id)


# 根据会话ID获取与该会话相关的所有事件，包括点击、输入、视图和滑动事件。
# 参数：
# - session_id: 会话ID。
# - project_id: 项目ID。
# 返回值：
# - 返回按时间排序的事件列表，每个事件包含类型信息。
def get_by_sessionId(session_id, project_id):
    with pg_client.PostgresClient() as cur:
        cur.execute(
            cur.mogrify(
                f"""
            SELECT 
                c.*,
                'TAP' AS type
            FROM events_ios.taps AS c
            WHERE 
              c.session_id = %(session_id)s
            ORDER BY c.timestamp;""",
                {"project_id": project_id, "session_id": session_id},
            )
        )
        rows = cur.fetchall()

        cur.execute(
            cur.mogrify(
                f"""
            SELECT 
                i.*,
                'INPUT' AS type
            FROM events_ios.inputs AS i
            WHERE 
              i.session_id = %(session_id)s
            ORDER BY i.timestamp;""",
                {"project_id": project_id, "session_id": session_id},
            )
        )
        rows += cur.fetchall()
        cur.execute(
            cur.mogrify(
                f"""
            SELECT 
                v.*,
                'VIEW' AS type
            FROM events_ios.views AS v
            WHERE 
              v.session_id = %(session_id)s
            ORDER BY v.timestamp;""",
                {"project_id": project_id, "session_id": session_id},
            )
        )
        rows += cur.fetchall()
        cur.execute(
            cur.mogrify(
                f"""
            SELECT 
                s.*,
                'SWIPE' AS type
            FROM events_ios.swipes AS s
            WHERE 
              s.session_id = %(session_id)s
            ORDER BY s.timestamp;""",
                {"project_id": project_id, "session_id": session_id},
            )
        )
        rows += cur.fetchall()
        rows = helper.list_to_camel_case(rows)
        rows = sorted(rows, key=lambda k: k["timestamp"])
    return rows


# 根据会话ID获取该会话中的崩溃信息。
# 参数：
# - session_id: 会话ID。
# 返回值：
# - 返回崩溃事件的详细信息列表。
def get_crashes_by_session_id(session_id):
    with pg_client.PostgresClient() as cur:
        cur.execute(
            cur.mogrify(
                f"""
                    SELECT cr.*,uc.*, cr.timestamp - s.start_ts AS time
                    FROM {events.EventType.CRASH_MOBILE.table} AS cr 
                        INNER JOIN public.crashes_ios AS uc USING (crash_ios_id) 
                        INNER JOIN public.sessions AS s USING (session_id)
                    WHERE
                      cr.session_id = %(session_id)s
                    ORDER BY timestamp;""",
                {"session_id": session_id},
            )
        )
        errors = cur.fetchall()
        return helper.list_to_camel_case(errors)
