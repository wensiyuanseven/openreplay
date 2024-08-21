# 这段代码是一个用于处理和分析点击热力图（Click Heatmap）的模块。
# 通过与PostgreSQL数据库的交互，该模块能够根据项目ID、URL、会话ID等参数查询并返回热力图数据。主要功能包括：按URL查询点击事件的坐标、根据URL和会话ID获取点击事件的坐标和选择器、搜索符合条件的短会话、以及获取特定会话的详细信息和页面事件。
import logging

import schemas
from chalicelib.core import sessions_mobs, sessions, events
from chalicelib.utils import pg_client, helper

# from chalicelib.utils import sql_helper as sh

logger = logging.getLogger(__name__)

# 函数：get_by_url
# 功能：根据项目ID和给定的URL获取该URL上发生的点击事件的坐标数据，用于生成点击热力图。
# 参数：
# - project_id: 项目ID。
# - data: schemas.GetHeatMapPayloadSchema类型，包含URL、时间范围等过滤条件。
# 返回值：
# - 返回包含点击事件坐标的列表。
def get_by_url(project_id, data: schemas.GetHeatMapPayloadSchema):
    args = {"startDate": data.startTimestamp, "endDate": data.endTimestamp,
            "project_id": project_id, "url": data.url}
    constraints = ["sessions.project_id = %(project_id)s",
                   "(url = %(url)s OR path= %(url)s)",
                   "clicks.timestamp >= %(startDate)s",
                   "clicks.timestamp <= %(endDate)s",
                   "start_ts >= %(startDate)s",
                   "start_ts <= %(endDate)s",
                   "duration IS NOT NULL",
                   "normalized_x IS NOT NULL"]
    query_from = "events.clicks INNER JOIN sessions USING (session_id)"
    has_click_rage_filter = False
    # TODO: is this used ?
    # if len(data.filters) > 0:
    #     for i, f in enumerate(data.filters):
    #         if f.type == schemas.FilterType.issue and len(f.value) > 0:
    #             has_click_rage_filter = True
    #             query_from += """INNER JOIN events_common.issues USING (timestamp, session_id)
    #                            INNER JOIN issues AS mis USING (issue_id)
    #                            INNER JOIN LATERAL (
    #                                 SELECT COUNT(1) AS real_count
    #                                  FROM events.clicks AS sc
    #                                           INNER JOIN sessions as ss USING (session_id)
    #                                  WHERE ss.project_id = 2
    #                                    AND (sc.url = %(url)s OR sc.path = %(url)s)
    #                                    AND sc.timestamp >= %(startDate)s
    #                                    AND sc.timestamp <= %(endDate)s
    #                                    AND ss.start_ts >= %(startDate)s
    #                                    AND ss.start_ts <= %(endDate)s
    #                                    AND sc.selector = clicks.selector) AS r_clicks ON (TRUE)"""
    #             constraints += ["mis.project_id = %(project_id)s",
    #                             "issues.timestamp >= %(startDate)s",
    #                             "issues.timestamp <= %(endDate)s"]
    #             f_k = f"issue_value{i}"
    #             args = {**args, **sh.multi_values(f.value, value_key=f_k)}
    #             constraints.append(sh.multi_conditions(f"%({f_k})s = ANY (issue_types)",
    #                                                    f.value, value_key=f_k))
    #             constraints.append(sh.multi_conditions(f"mis.type = %({f_k})s",
    #                                                    f.value, value_key=f_k))

    if data.click_rage and not has_click_rage_filter:
        constraints.append("""(issues.session_id IS NULL 
                                OR (issues.timestamp >= %(startDate)s
                                    AND issues.timestamp <= %(endDate)s
                                    AND mis.project_id = %(project_id)s
                                    AND mis.type='click_rage'))""")
        query_from += """LEFT JOIN events_common.issues USING (timestamp, session_id)
                       LEFT JOIN issues AS mis USING (issue_id)"""
    with pg_client.PostgresClient() as cur:
        query = cur.mogrify(f"""SELECT normalized_x, normalized_y
                                FROM {query_from}
                                WHERE {" AND ".join(constraints)}
                                LIMIT 500;""", args)
        logger.debug("---------")
        logger.debug(query.decode('UTF-8'))
        logger.debug("---------")
        try:
            cur.execute(query)
        except Exception as err:
            logger.warning("--------- HEATMAP 2 SEARCH QUERY EXCEPTION -----------")
            logger.warning(query.decode('UTF-8'))
            logger.warning("--------- PAYLOAD -----------")
            logger.warning(data)
            logger.warning("--------------------")
            raise err
        rows = cur.fetchall()

    return helper.list_to_camel_case(rows)

# 函数：get_x_y_by_url_and_session_id
# 功能：根据项目ID、会话ID和URL获取该会话中发生的点击事件的坐标数据。
# 参数：
# - project_id: 项目ID。
# - session_id: 会话ID。
# - data: schemas.GetHeatMapPayloadSchema类型，包含URL等过滤条件。
# 返回值：
# - 返回点击事件的坐标列表。
def get_x_y_by_url_and_session_id(project_id, session_id, data: schemas.GetHeatMapPayloadSchema):
    args = {"session_id": session_id, "url": data.url}
    constraints = ["session_id = %(session_id)s",
                   "(url = %(url)s OR path= %(url)s)",
                   "normalized_x IS NOT NULL"]
    query_from = "events.clicks"

    with pg_client.PostgresClient() as cur:
        query = cur.mogrify(f"""SELECT normalized_x, normalized_y
                                FROM {query_from}
                                WHERE {" AND ".join(constraints)};""", args)
        logger.debug("---------")
        logger.debug(query.decode('UTF-8'))
        logger.debug("---------")
        try:
            cur.execute(query)
        except Exception as err:
            logger.warning("--------- HEATMAP-session_id SEARCH QUERY EXCEPTION -----------")
            logger.warning(query.decode('UTF-8'))
            logger.warning("--------- PAYLOAD -----------")
            logger.warning(data)
            logger.warning("--------------------")
            raise err
        rows = cur.fetchall()

    return helper.list_to_camel_case(rows)

# 函数：get_selectors_by_url_and_session_id
# 功能：根据项目ID、会话ID和URL获取该会话中发生的点击事件的选择器信息，并统计每个选择器的点击次数。
# 参数：
# - project_id: 项目ID。
# - session_id: 会话ID。
# - data: schemas.GetHeatMapPayloadSchema类型，包含URL等过滤条件。
# 返回值：
# - 返回选择器及其点击次数的列表。
def get_selectors_by_url_and_session_id(project_id, session_id, data: schemas.GetHeatMapPayloadSchema):
    args = {"session_id": session_id, "url": data.url}
    constraints = ["session_id = %(session_id)s",
                   "(url = %(url)s OR path= %(url)s)"]
    query_from = "events.clicks"

    with pg_client.PostgresClient() as cur:
        query = cur.mogrify(f"""SELECT selector, COUNT(1) AS count
                                FROM {query_from}
                                WHERE {" AND ".join(constraints)}
                                GROUP BY 1
                                ORDER BY count DESC;""", args)
        logger.debug("---------")
        logger.debug(query.decode('UTF-8'))
        logger.debug("---------")
        try:
            cur.execute(query)
        except Exception as err:
            logger.warning("--------- HEATMAP-selector-session_id SEARCH QUERY EXCEPTION -----------")
            logger.warning(query.decode('UTF-8'))
            logger.warning("--------- PAYLOAD -----------")
            logger.warning(data)
            logger.warning("--------------------")
            raise err
        rows = cur.fetchall()

    return helper.list_to_camel_case(rows)

# 定义会话投影列，用于简化会话数据的选择
SESSION_PROJECTION_COLS = """s.project_id,
s.session_id::text AS session_id,
s.start_ts,
s.duration"""

# 函数：search_short_session
# 功能：搜索符合条件的简短会话，用于生成点击热力图时使用。
# 参数：
# - data: schemas.HeatMapSessionsSearch类型，包含过滤条件和排序方式。
# - project_id: 项目ID。
# - user_id: 用户ID。
# - include_mobs: 是否包括移动端数据，默认为True。
# - exclude_sessions: 要排除的会话ID列表。
# - _depth: 搜索深度，默认为3。
# 返回值：
# - 返回一个符合条件的简短会话数据。
def search_short_session(data: schemas.HeatMapSessionsSearch, project_id, user_id,
                         include_mobs: bool = True, exclude_sessions: list[str] = [],
                         _depth: int = 3):
    no_platform = True
    no_location = True
    for f in data.filters:
        if f.type == schemas.FilterType.platform:
            no_platform = False
            break
    for f in data.events:
        if f.type == schemas.EventType.location:
            no_location = False
            if len(f.value) == 0:
                f.operator = schemas.SearchEventOperator._is_any
            break
    if no_platform:
        data.filters.append(schemas.SessionSearchFilterSchema(type=schemas.FilterType.platform,
                                                              value=[schemas.PlatformType.desktop],
                                                              operator=schemas.SearchEventOperator._is))
    if no_location:
        data.events.append(schemas.SessionSearchEventSchema2(type=schemas.EventType.location,
                                                             value=[],
                                                             operator=schemas.SearchEventOperator._is_any))

    data.filters.append(schemas.SessionSearchFilterSchema(type=schemas.FilterType.events_count,
                                                          value=[0],
                                                          operator=schemas.MathOperator._greater))

    full_args, query_part = sessions.search_query_parts(data=data, error_status=None, errors_only=False,
                                                        favorite_only=data.bookmarked, issue=None,
                                                        project_id=project_id, user_id=user_id)
    full_args["exclude_sessions"] = tuple(exclude_sessions)
    if len(exclude_sessions) > 0:
        query_part += "\n AND session_id NOT IN %(exclude_sessions)s"
    with pg_client.PostgresClient() as cur:
        data.order = schemas.SortOrderType.desc
        data.sort = 'duration'
        main_query = cur.mogrify(f"""SELECT *
                                     FROM (SELECT {SESSION_PROJECTION_COLS}
                                           {query_part}
                                           ORDER BY {data.sort} {data.order.value}
                                           LIMIT 20) AS raw
                                     ORDER BY random()
                                     LIMIT 1;""", full_args)
        logger.debug("--------------------")
        logger.debug(main_query)
        logger.debug("--------------------")
        try:
            cur.execute(main_query)
        except Exception as err:
            logger.warning("--------- CLICK MAP SHORT SESSION SEARCH QUERY EXCEPTION -----------")
            logger.warning(main_query.decode('UTF-8'))
            logger.warning("--------- PAYLOAD -----------")
            logger.warning(data.model_dump_json())
            logger.warning("--------------------")
            raise err

        session = cur.fetchone()
    if session:
        if include_mobs:
            session['domURL'] = sessions_mobs.get_urls(session_id=session["session_id"], project_id=project_id)
            session['mobsUrl'] = sessions_mobs.get_urls_depercated(session_id=session["session_id"])
            if _depth > 0 and len(session['domURL']) == 0 and len(session['mobsUrl']) == 0:
                return search_short_session(data=data, project_id=project_id, user_id=user_id,
                                            include_mobs=include_mobs,
                                            exclude_sessions=exclude_sessions + [session["session_id"]],
                                            _depth=_depth - 1)
            elif _depth == 0 and len(session['domURL']) == 0 and len(session['mobsUrl']) == 0:
                logger.info("couldn't find an existing replay after 3 iterations for heatmap")

        session['events'] = get_page_events(session_id=session["session_id"], project_id=project_id)
    else:
        logger.debug("No session found for heatmap")

    return helper.dict_to_camel_case(session)

# 函数：get_selected_session
# 功能：获取指定会话的详细信息，用于生成点击热力图时使用。
# 参数：
# - project_id: 项目ID。
# - session_id: 会话ID。
# 返回值：
# - 返回会话的详细信息，包括页面事件和移动端相关数据。
def get_selected_session(project_id, session_id):
    with pg_client.PostgresClient() as cur:
        main_query = cur.mogrify(f"""SELECT {SESSION_PROJECTION_COLS}
                                     FROM public.sessions AS s
                                     WHERE session_id=%(session_id)s;""", {"session_id": session_id})
        logger.debug("--------------------")
        logger.debug(main_query)
        logger.debug("--------------------")
        try:
            cur.execute(main_query)
        except Exception as err:
            logger.warning("--------- CLICK MAP GET SELECTED SESSION QUERY EXCEPTION -----------")
            logger.warning(main_query.decode('UTF-8'))
            raise err

        session = cur.fetchone()

    if session:
        session['domURL'] = sessions_mobs.get_urls(session_id=session["session_id"], project_id=project_id)
        session['mobsUrl'] = sessions_mobs.get_urls_depercated(session_id=session["session_id"])
        if len(session['domURL']) == 0 and len(session['mobsUrl']) == 0:
            session["_issue"] = "mob file not found"
            logger.info("can't find selected mob file for heatmap")
        session['events'] = get_page_events(session_id=session["session_id"], project_id=project_id)

    return helper.dict_to_camel_case(session)


# 函数：get_page_events
# 功能：获取指定会话的页面事件数据。
# 参数：
# - session_id: 会话ID。
# - project_id: 项目ID。
# 返回值：
# - 返回页面事件的详细信息列表。
def get_page_events(session_id, project_id):
    with pg_client.PostgresClient() as cur:
        cur.execute(cur.mogrify("""\
                SELECT 
                    message_id,
                    timestamp,
                    host,
                    path,
                    path AS value,
                    path AS url,
                    'LOCATION' AS type
                FROM events.pages
                WHERE session_id = %(session_id)s
                ORDER BY timestamp,message_id;""", {"session_id": session_id}))
        rows = cur.fetchall()
        rows = helper.list_to_camel_case(rows)
    return rows

# 该代码模块主要用于处理和分析热力图数据，帮助用户可视化网页上的点击行为。通过查询数据库中的点击事件和会话数据，该模块提供了生成点击热力图和获取特定会话详细信息的功能。
