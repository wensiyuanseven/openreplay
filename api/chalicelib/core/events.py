# 这个代码片段主要用于处理和检索与用户会话相关的各种事件和错误信息。它提供了根据会话ID获取特定事件（如点击、输入、位置、错误等）的方法，并且支持基于事件类型和文本搜索来查找相关数据。
# 此外，代码片段还支持对移动端的特殊事件类型（如点击、输入、视图、滑动等）进行处理和搜索。
from typing import Optional

import schemas
from chalicelib.core import autocomplete
from chalicelib.core import issues
from chalicelib.core import sessions_metas
from chalicelib.utils import pg_client, helper
from chalicelib.utils.TimeUTC import TimeUTC
from chalicelib.utils.event_filter_definition import SupportedFilter, Event

# 根据会话ID获取自定义事件信息。
# 参数：
# - session_id: 会话ID。
# - project_id: 项目ID。
# 返回值：
# - 包含自定义事件的字典列表，按时间戳排序。
def get_customs_by_session_id(session_id, project_id):
    with pg_client.PostgresClient() as cur:
        cur.execute(cur.mogrify("""\
            SELECT 
                c.*,
                'CUSTOM' AS type
            FROM events_common.customs AS c
            WHERE 
              c.session_id = %(session_id)s
            ORDER BY c.timestamp;""",
                                {"project_id": project_id, "session_id": session_id})
                    )
        rows = cur.fetchall()
    return helper.dict_to_camel_case(rows)


# 合并表格中的指定行。
# 参数：
# - rows: 事件列表。
# - start: 开始合并的索引。
# - count: 要合并的行数。
# - replacement: 替换合并后内容的字典。
# 返回值：
# - 返回合并后的事件列表。
def __merge_cells(rows, start, count, replacement):
    rows[start] = replacement
    rows = rows[:start + 1] + rows[start + count:]
    return rows


# 获取并处理会话中的ClickRage问题。
# 参数：
# - rows: 事件列表。
# - session_id: 会话ID。
# - project_id: 项目ID。
# 返回值：
# - 返回处理ClickRage后的事件列表。
def __get_grouped_clickrage(rows, session_id, project_id):
    click_rage_issues = issues.get_by_session_id(session_id=session_id, issue_type="click_rage", project_id=project_id)
    if len(click_rage_issues) == 0:
        return rows

    for c in click_rage_issues:
        merge_count = c.get("payload")
        if merge_count is not None:
            merge_count = merge_count.get("Count", 3)
        else:
            merge_count = 3
        for i in range(len(rows)):
            if rows[i]["timestamp"] == c["timestamp"]:
                rows = __merge_cells(rows=rows,
                                     start=i,
                                     count=merge_count,
                                     replacement={**rows[i], "type": "CLICKRAGE", "count": merge_count})
                break
    return rows

# 根据会话ID和事件类型获取会话中发生的事件。
# 参数：
# - session_id: 会话ID。
# - project_id: 项目ID。
# - group_clickrage: 是否对ClickRage事件进行分组。
# - event_type: 可选的事件类型（如CLICK、INPUT、LOCATION等）。
# 返回值：
# - 返回按时间戳排序的事件列表。
def get_by_session_id(session_id, project_id, group_clickrage=False, event_type: Optional[schemas.EventType] = None):
    with pg_client.PostgresClient() as cur:
        rows = []
        if event_type is None or event_type == schemas.EventType.click:
            cur.execute(cur.mogrify("""\
                SELECT 
                    c.*,
                    'CLICK' AS type
                FROM events.clicks AS c
                WHERE 
                  c.session_id = %(session_id)s
                ORDER BY c.timestamp;""",
                                    {"project_id": project_id, "session_id": session_id})
                        )
            rows += cur.fetchall()
            if group_clickrage:
                rows = __get_grouped_clickrage(rows=rows, session_id=session_id, project_id=project_id)
        if event_type is None or event_type == schemas.EventType.input:
            cur.execute(cur.mogrify("""
                SELECT 
                    i.*,
                    'INPUT' AS type
                FROM events.inputs AS i
                WHERE 
                  i.session_id = %(session_id)s
                ORDER BY i.timestamp;""",
                                    {"project_id": project_id, "session_id": session_id})
                        )
            rows += cur.fetchall()
        if event_type is None or event_type == schemas.EventType.location:
            cur.execute(cur.mogrify("""\
                SELECT 
                    l.*,
                    l.path AS value,
                    l.path AS url,
                    'LOCATION' AS type
                FROM events.pages AS l
                WHERE 
                  l.session_id = %(session_id)s
                ORDER BY l.timestamp;""", {"project_id": project_id, "session_id": session_id}))
            rows += cur.fetchall()
        rows = helper.list_to_camel_case(rows)
        rows = sorted(rows, key=lambda k: (k["timestamp"], k["messageId"]))
    return rows

# 搜索标签相关的事件。
# 参数：
# - project_id: 项目ID。
# - value: 搜索的标签值。
# - key: 可选的标签键。
# - source: 可选的来源。
# 返回值：
# - 返回与搜索值匹配的标签列表。
def _search_tags(project_id, value, key=None, source=None):
    with pg_client.PostgresClient() as cur:
        query = f"""
        SELECT public.tags.name
               '{events.EventType.TAG.ui_type}' AS type
        FROM public.tags
        WHERE public.tags.project_id = %(project_id)s
        ORDER BY SIMILARITY(public.tags.name, %(value)s) DESC
        LIMIT 10
        """
        query = cur.mogrify(query, {'project_id': project_id, 'value': value})
        cur.execute(query)
        results = helper.list_to_camel_case(cur.fetchall())
    return results

# 定义了各种事件类型，包含不同事件的表名和列名。
class EventType:
    CLICK = Event(ui_type=schemas.EventType.click, table="events.clicks", column="label")
    INPUT = Event(ui_type=schemas.EventType.input, table="events.inputs", column="label")
    LOCATION = Event(ui_type=schemas.EventType.location, table="events.pages", column="path")
    CUSTOM = Event(ui_type=schemas.EventType.custom, table="events_common.customs", column="name")
    REQUEST = Event(ui_type=schemas.EventType.request, table="events_common.requests", column="path")
    GRAPHQL = Event(ui_type=schemas.EventType.graphql, table="events.graphql", column="name")
    STATEACTION = Event(ui_type=schemas.EventType.state_action, table="events.state_actions", column="name")
    TAG = Event(ui_type=schemas.EventType.tag, table="events.tags", column="tag_id")
    ERROR = Event(ui_type=schemas.EventType.error, table="events.errors",
                  column=None)  # column=None because errors are searched by name or message
    METADATA = Event(ui_type=schemas.FilterType.metadata, table="public.sessions", column=None)
    #     MOBILE
    CLICK_MOBILE = Event(ui_type=schemas.EventType.click_mobile, table="events_ios.taps", column="label")
    INPUT_MOBILE = Event(ui_type=schemas.EventType.input_mobile, table="events_ios.inputs", column="label")
    VIEW_MOBILE = Event(ui_type=schemas.EventType.view_mobile, table="events_ios.views", column="name")
    SWIPE_MOBILE = Event(ui_type=schemas.EventType.swipe_mobile, table="events_ios.swipes", column="label")
    CUSTOM_MOBILE = Event(ui_type=schemas.EventType.custom_mobile, table="events_common.customs", column="name")
    REQUEST_MOBILE = Event(ui_type=schemas.EventType.request_mobile, table="events_common.requests", column="path")
    CRASH_MOBILE = Event(ui_type=schemas.EventType.error_mobile, table="events_common.crashes",
                         column=None)  # column=None because errors are searched by name or message

# 定义了支持的事件类型及其处理方式。
SUPPORTED_TYPES = {
    EventType.CLICK.ui_type: SupportedFilter(get=autocomplete.__generic_autocomplete(EventType.CLICK),
                                             query=autocomplete.__generic_query(typename=EventType.CLICK.ui_type)),
    EventType.INPUT.ui_type: SupportedFilter(get=autocomplete.__generic_autocomplete(EventType.INPUT),
                                             query=autocomplete.__generic_query(typename=EventType.INPUT.ui_type)),
    EventType.LOCATION.ui_type: SupportedFilter(get=autocomplete.__generic_autocomplete(EventType.LOCATION),
                                                query=autocomplete.__generic_query(
                                                    typename=EventType.LOCATION.ui_type)),
    EventType.CUSTOM.ui_type: SupportedFilter(get=autocomplete.__generic_autocomplete(EventType.CUSTOM),
                                              query=autocomplete.__generic_query(typename=EventType.CUSTOM.ui_type)),
    EventType.REQUEST.ui_type: SupportedFilter(get=autocomplete.__generic_autocomplete(EventType.REQUEST),
                                               query=autocomplete.__generic_query(
                                                   typename=EventType.REQUEST.ui_type)),
    EventType.GRAPHQL.ui_type: SupportedFilter(get=autocomplete.__generic_autocomplete(EventType.GRAPHQL),
                                               query=autocomplete.__generic_query(
                                                   typename=EventType.GRAPHQL.ui_type)),
    EventType.STATEACTION.ui_type: SupportedFilter(get=autocomplete.__generic_autocomplete(EventType.STATEACTION),
                                                   query=autocomplete.__generic_query(
                                                       typename=EventType.STATEACTION.ui_type)),
    EventType.TAG.ui_type: SupportedFilter(get=_search_tags, query=None),
    EventType.ERROR.ui_type: SupportedFilter(get=autocomplete.__search_errors,
                                             query=None),
    EventType.METADATA.ui_type: SupportedFilter(get=autocomplete.__search_metadata,
                                                query=None),
    #     MOBILE
    EventType.CLICK_MOBILE.ui_type: SupportedFilter(get=autocomplete.__generic_autocomplete(EventType.CLICK_MOBILE),
                                                    query=autocomplete.__generic_query(
                                                        typename=EventType.CLICK_MOBILE.ui_type)),
    EventType.SWIPE_MOBILE.ui_type: SupportedFilter(get=autocomplete.__generic_autocomplete(EventType.SWIPE_MOBILE),
                                                    query=autocomplete.__generic_query(
                                                        typename=EventType.SWIPE_MOBILE.ui_type)),
    EventType.INPUT_MOBILE.ui_type: SupportedFilter(get=autocomplete.__generic_autocomplete(EventType.INPUT_MOBILE),
                                                    query=autocomplete.__generic_query(
                                                        typename=EventType.INPUT_MOBILE.ui_type)),
    EventType.VIEW_MOBILE.ui_type: SupportedFilter(get=autocomplete.__generic_autocomplete(EventType.VIEW_MOBILE),
                                                   query=autocomplete.__generic_query(
                                                       typename=EventType.VIEW_MOBILE.ui_type)),
    EventType.CUSTOM_MOBILE.ui_type: SupportedFilter(get=autocomplete.__generic_autocomplete(EventType.CUSTOM_MOBILE),
                                                     query=autocomplete.__generic_query(
                                                         typename=EventType.CUSTOM_MOBILE.ui_type)),
    EventType.REQUEST_MOBILE.ui_type: SupportedFilter(get=autocomplete.__generic_autocomplete(EventType.REQUEST_MOBILE),
                                                      query=autocomplete.__generic_query(
                                                          typename=EventType.REQUEST_MOBILE.ui_type)),
    EventType.CRASH_MOBILE.ui_type: SupportedFilter(get=autocomplete.__search_errors_mobile,
                                                    query=None),
}

# 根据会话ID获取会话中的错误信息。
# 参数：
# - session_id: 会话ID。
# - project_id: 项目ID。
# 返回值：
# - 返回错误事件的详细信息列表。
def get_errors_by_session_id(session_id, project_id):
    with pg_client.PostgresClient() as cur:
        cur.execute(cur.mogrify(f"""\
                    SELECT er.*,ur.*, er.timestamp - s.start_ts AS time
                    FROM {EventType.ERROR.table} AS er INNER JOIN public.errors AS ur USING (error_id) INNER JOIN public.sessions AS s USING (session_id)
                    WHERE er.session_id = %(session_id)s AND s.project_id=%(project_id)s
                    ORDER BY timestamp;""", {"session_id": session_id, "project_id": project_id}))
        errors = cur.fetchall()
        for e in errors:
            e["stacktrace_parsed_at"] = TimeUTC.datetime_to_timestamp(e["stacktrace_parsed_at"])
        return helper.list_to_camel_case(errors)

# 根据输入文本、事件类型、项目ID等搜索相关事件。
# 参数：
# - text: 输入的搜索文本。
# - event_type: 事件类型。
# - project_id: 项目ID。
# - source: 数据来源。
# - key: 可选的键值。
# 返回值：
# - 返回匹配的事件数据列表。
def search(text, event_type, project_id, source, key):
    if not event_type:
        return {"data": autocomplete.__get_autocomplete_table(text, project_id)}

    if event_type in SUPPORTED_TYPES.keys():
        rows = SUPPORTED_TYPES[event_type].get(project_id=project_id, value=text, key=key, source=source)
        # for IOS events autocomplete
        # if event_type + "_IOS" in SUPPORTED_TYPES.keys():
        #     rows += SUPPORTED_TYPES[event_type + "_IOS"].get(project_id=project_id, value=text, key=key,source=source)
    elif event_type + "_MOBILE" in SUPPORTED_TYPES.keys():
        rows = SUPPORTED_TYPES[event_type + "_MOBILE"].get(project_id=project_id, value=text, key=key, source=source)
    elif event_type in sessions_metas.SUPPORTED_TYPES.keys():
        return sessions_metas.search(text, event_type, project_id)
    elif event_type.endswith("_IOS") \
            and event_type[:-len("_IOS")] in sessions_metas.SUPPORTED_TYPES.keys():
        return sessions_metas.search(text, event_type, project_id)
    elif event_type.endswith("_MOBILE") \
            and event_type[:-len("_MOBILE")] in sessions_metas.SUPPORTED_TYPES.keys():
        return sessions_metas.search(text, event_type, project_id)
    else:
        return {"errors": ["unsupported event"]}

    return {"data": rows}

# 注意事项：
# 事件处理顺序：在处理复杂的事件时，需要确保事件处理的顺序正确，以避免数据混淆或不准确的情况。
# 查询效率：对于大量数据的查询，可能会影响性能，建议进行适当的数据库优化或分页查询。
