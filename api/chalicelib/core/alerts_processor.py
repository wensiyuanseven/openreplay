# 这段代码是一个完整的告警监控处理系统的核心部分!!!。
# 它从数据库中获取数据，依据预设的条件和规则判断是否触发告警，并生成通知以告知相关人员。代码中还处理了告警的各种复杂情况，如不同类型的告警检测方法、时间条件的处理等。
import decimal  # 用于处理高精度的小数计算。
import logging

from decouple import config
from pydantic_core._pydantic_core import ValidationError  # 用于处理数据验证错误。

# 导入了自定义模块，用于告警的管理、监听、会话处理等。
import schemas
from chalicelib.core import alerts
from chalicelib.core import alerts_listener
from chalicelib.core import sessions
from chalicelib.utils import pg_client
from chalicelib.utils.TimeUTC import TimeUTC

logging.basicConfig(level=config("LOGLEVEL", default=logging.INFO))

# 一个映射字典，将告警的左侧条件（如页面加载时间、图像加载时间等）映射到相应的 SQL 表和公式，用于生成 SQL 查询。
LeftToDb = {
    schemas.AlertColumn.performance__dom_content_loaded__average: {
        "table": "events.pages INNER JOIN public.sessions USING(session_id)",
        "formula": "COALESCE(AVG(NULLIF(dom_content_loaded_time ,0)),0)",
    },
    schemas.AlertColumn.performance__first_meaningful_paint__average: {
        "table": "events.pages INNER JOIN public.sessions USING(session_id)",
        "formula": "COALESCE(AVG(NULLIF(first_contentful_paint_time,0)),0)",
    },
    schemas.AlertColumn.performance__page_load_time__average: {"table": "events.pages INNER JOIN public.sessions USING(session_id)", "formula": "AVG(NULLIF(load_time ,0))"},
    schemas.AlertColumn.performance__dom_build_time__average: {"table": "events.pages INNER JOIN public.sessions USING(session_id)", "formula": "AVG(NULLIF(dom_building_time,0))"},
    schemas.AlertColumn.performance__speed_index__average: {"table": "events.pages INNER JOIN public.sessions USING(session_id)", "formula": "AVG(NULLIF(speed_index,0))"},
    schemas.AlertColumn.performance__page_response_time__average: {"table": "events.pages INNER JOIN public.sessions USING(session_id)", "formula": "AVG(NULLIF(response_time,0))"},
    schemas.AlertColumn.performance__ttfb__average: {"table": "events.pages INNER JOIN public.sessions USING(session_id)", "formula": "AVG(NULLIF(first_paint_time,0))"},
    schemas.AlertColumn.performance__time_to_render__average: {"table": "events.pages INNER JOIN public.sessions USING(session_id)", "formula": "AVG(NULLIF(visually_complete,0))"},
    schemas.AlertColumn.performance__image_load_time__average: {
        "table": "events.resources INNER JOIN public.sessions USING(session_id)",
        "formula": "AVG(NULLIF(resources.duration,0))",
        "condition": "type='img'",
    },
    schemas.AlertColumn.performance__request_load_time__average: {
        "table": "events.resources INNER JOIN public.sessions USING(session_id)",
        "formula": "AVG(NULLIF(resources.duration,0))",
        "condition": "type='fetch'",
    },
    schemas.AlertColumn.resources__load_time__average: {"table": "events.resources INNER JOIN public.sessions USING(session_id)", "formula": "AVG(NULLIF(resources.duration,0))"},
    schemas.AlertColumn.resources__missing__count: {
        "table": "events.resources INNER JOIN public.sessions USING(session_id)",
        "formula": "COUNT(DISTINCT url_hostpath)",
        "condition": "success= FALSE AND type='img'",
    },
    schemas.AlertColumn.errors__4xx_5xx__count: {"table": "events.resources INNER JOIN public.sessions USING(session_id)", "formula": "COUNT(session_id)", "condition": "status/100!=2"},
    schemas.AlertColumn.errors__4xx__count: {"table": "events.resources INNER JOIN public.sessions USING(session_id)", "formula": "COUNT(session_id)", "condition": "status/100=4"},
    schemas.AlertColumn.errors__5xx__count: {"table": "events.resources INNER JOIN public.sessions USING(session_id)", "formula": "COUNT(session_id)", "condition": "status/100=5"},
    schemas.AlertColumn.errors__javascript__impacted_sessions__count: {
        "table": "events.resources INNER JOIN public.sessions USING(session_id)",
        "formula": "COUNT(DISTINCT session_id)",
        "condition": "success= FALSE AND type='script'",
    },
    schemas.AlertColumn.performance__crashes__count: {"table": "public.sessions", "formula": "COUNT(DISTINCT session_id)", "condition": "errors_count > 0 AND duration>0"},
    schemas.AlertColumn.errors__javascript__count: {
        "table": "events.errors INNER JOIN public.errors AS m_errors USING (error_id)",
        "formula": "COUNT(DISTINCT session_id)",
        "condition": "source='js_exception'",
        "joinSessions": False,
    },
    schemas.AlertColumn.errors__backend__count: {
        "table": "events.errors INNER JOIN public.errors AS m_errors USING (error_id)",
        "formula": "COUNT(DISTINCT session_id)",
        "condition": "source!='js_exception'",
        "joinSessions": False,
    },
}

# This is the frequency of execution for each threshold
# 时间间隔映射
# 定义了每个时间间隔的执行频率，单位是分钟。例如，15 分钟的时间间隔会每 3 分钟执行一次。
TimeInterval = {
    15: 3,
    30: 5,
    60: 10,
    120: 20,
    240: 30,
    1440: 60,
}


# 告警检测函数  can_check：用于判断当前时间点是否需要检查某个告警，主要依据告警的创建时间、上次通知时间和重新通知间隔等条件进行计算。
def can_check(a) -> bool:
    now = TimeUTC.now()

    repetitionBase = a["options"]["currentPeriod"] if a["detectionMethod"] == schemas.AlertDetectionMethod.change and a["options"]["currentPeriod"] > a["options"]["previousPeriod"] else a["options"]["previousPeriod"]

    if TimeInterval.get(repetitionBase) is None:
        logging.error(f"repetitionBase: {repetitionBase} NOT FOUND")
        return False

    return (a["options"]["renotifyInterval"] <= 0 or a["options"].get("lastNotification") is None or a["options"]["lastNotification"] <= 0 or ((now - a["options"]["lastNotification"]) > a["options"]["renotifyInterval"] * 60 * 1000)) and ((now - a["createdAt"]) % (TimeInterval[repetitionBase] * 60 * 1000)) < 60 * 1000


# SQL 查询构建函数  根据告警的条件和参数，动态生成 SQL 查询语句。这个函数处理了不同类型的告警（阈值型、变化型等），并将参数传递给 SQL 查询。
def Build(a):
    now = TimeUTC.now()
    params = {"project_id": a["projectId"], "now": now}
    full_args = {}
    j_s = True
    main_table = ""
    if a["seriesId"] is not None:
        a["filter"]["sort"] = "session_id"
        a["filter"]["order"] = schemas.SortOrderType.desc
        a["filter"]["startDate"] = 0
        a["filter"]["endDate"] = TimeUTC.now()
        try:
            data = schemas.SessionsSearchPayloadSchema.model_validate(a["filter"])
        except ValidationError:
            logging.warning("Validation error for:")
            logging.warning(a["filter"])
            raise

        full_args, query_part = sessions.search_query_parts(data=data, error_status=None, errors_only=False, issue=None, project_id=a["projectId"], user_id=None, favorite_only=False)
        subQ = f"""SELECT COUNT(session_id) AS value 
                {query_part}"""
    else:
        colDef = LeftToDb[a["query"]["left"]]
        subQ = f"""SELECT {colDef["formula"]} AS value
                    FROM {colDef["table"]}
                    WHERE project_id = %(project_id)s 
                        {"AND " + colDef["condition"] if colDef.get("condition") else ""}"""
        j_s = colDef.get("joinSessions", True)
        main_table = colDef["table"]
    is_ss = main_table == "public.sessions"
    q = f"""SELECT coalesce(value,0) AS value, coalesce(value,0) {a["query"]["operator"]} {a["query"]["right"]} AS valid"""

    if a["detectionMethod"] == schemas.AlertDetectionMethod.threshold:
        if a["seriesId"] is not None:
            q += f""" FROM ({subQ}) AS stat"""
        else:
            q += f""" FROM ({subQ} {"AND timestamp >= %(startDate)s AND timestamp <= %(now)s" if not is_ss else ""} 
                                {"AND start_ts >= %(startDate)s AND start_ts <= %(now)s" if j_s else ""}) AS stat"""
        params = {**params, **full_args, "startDate": TimeUTC.now() - a["options"]["currentPeriod"] * 60 * 1000}
    else:
        if a["change"] == schemas.AlertDetectionType.change:
            if a["seriesId"] is not None:
                sub2 = subQ.replace("%(startDate)s", "%(timestamp_sub2)s").replace("%(endDate)s", "%(startDate)s")
                sub1 = f"SELECT (({subQ})-({sub2})) AS value"
                q += f" FROM ( {sub1} ) AS stat"
                params = {
                    **params,
                    **full_args,
                    "startDate": TimeUTC.now() - a["options"]["currentPeriod"] * 60 * 1000,
                    "timestamp_sub2": TimeUTC.now() - 2 * a["options"]["currentPeriod"] * 60 * 1000,
                }
            else:
                sub1 = f"""{subQ} {"AND timestamp >= %(startDate)s AND timestamp <= %(now)s" if not is_ss else ""}
                                {"AND start_ts >= %(startDate)s AND start_ts <= %(now)s" if j_s else ""}"""
                params["startDate"] = TimeUTC.now() - a["options"]["currentPeriod"] * 60 * 1000
                sub2 = f"""{subQ} {"AND timestamp < %(startDate)s AND timestamp >= %(timestamp_sub2)s" if not is_ss else ""}
                            {"AND start_ts < %(startDate)s AND start_ts >= %(timestamp_sub2)s" if j_s else ""}"""
                params["timestamp_sub2"] = TimeUTC.now() - 2 * a["options"]["currentPeriod"] * 60 * 1000
                sub1 = f"SELECT (( {sub1} )-( {sub2} )) AS value"
                q += f" FROM ( {sub1} ) AS stat"

        else:
            if a["seriesId"] is not None:
                sub2 = subQ.replace("%(startDate)s", "%(timestamp_sub2)s").replace("%(endDate)s", "%(startDate)s")
                sub1 = f"SELECT (({subQ})/NULLIF(({sub2}),0)-1)*100 AS value"
                q += f" FROM ({sub1}) AS stat"
                params = {
                    **params,
                    **full_args,
                    "startDate": TimeUTC.now() - a["options"]["currentPeriod"] * 60 * 1000,
                    "timestamp_sub2": TimeUTC.now() - (a["options"]["currentPeriod"] + a["options"]["currentPeriod"]) * 60 * 1000,
                }
            else:
                sub1 = f"""{subQ} {"AND timestamp >= %(startDate)s AND timestamp <= %(now)s" if not is_ss else ""}
                                {"AND start_ts >= %(startDate)s AND start_ts <= %(now)s" if j_s else ""}"""
                params["startDate"] = TimeUTC.now() - a["options"]["currentPeriod"] * 60 * 1000
                sub2 = f"""{subQ} {"AND timestamp < %(startDate)s AND timestamp >= %(timestamp_sub2)s" if not is_ss else ""}
                        {"AND start_ts < %(startDate)s AND start_ts >= %(timestamp_sub2)s" if j_s else ""}"""
                params["timestamp_sub2"] = TimeUTC.now() - (a["options"]["currentPeriod"] + a["options"]["currentPeriod"]) * 60 * 1000
                sub1 = f"SELECT (({sub1})/NULLIF(({sub2}),0)-1)*100 AS value"
                q += f" FROM ({sub1}) AS stat"

    return q, params

# 告警处理函数  它从 alerts_listener 中获取所有活跃的告警，检查每个告警是否需要执行查询，构建 SQL 查询并执行，最后根据查询结果生成通知。
def process():
    notifications = []
    all_alerts = alerts_listener.get_all_alerts()
    with pg_client.PostgresClient() as cur:
        for alert in all_alerts:
            if can_check(alert):
                query, params = Build(alert)
                try:
                    query = cur.mogrify(query, params)
                except Exception as e:
                    logging.error(f"!!!构建 alertId 警报查询时出错:{alert['alertId']} name: {alert['name']}")
                    logging.error(e)
                    continue
                logging.debug(alert)
                logging.debug(query)
                try:
                    cur.execute(query)
                    result = cur.fetchone()
                    if result["valid"]:
                        logging.info(f"有效警报，通知用户, alertId:{alert['alertId']} name: {alert['name']}")
                        notifications.append(generate_notification(alert, result))
                except Exception as e:
                    logging.error(f"!!!运行 alertId 警报查询时出错:{alert['alertId']} name: {alert['name']}")
                    logging.error(query)
                    logging.error(e)
                    cur = cur.recreate(rollback=True)
        if len(notifications) > 0:
            cur.execute(
                cur.mogrify(
                    f"""UPDATE public.alerts 
                                SET options = options||'{{"lastNotification":{TimeUTC.now()}}}'::jsonb 
                                WHERE alert_id IN %(ids)s;""",
                    {"ids": tuple([n["alertId"] for n in notifications])},
                )
            )
    if len(notifications) > 0:
        alerts.process_notifications(notifications)

# 格式化告警结果中的数值，确保显示时保留适当的精度。
def __format_value(x):
    if x % 1 == 0:
        x = int(x)
    else:
        x = round(x, 2)
    return f"{x:,}"

# 生成通知字典，包含告警的详细信息和通知的相关内容，用于推送给用户。
def generate_notification(alert, result):
    left = __format_value(result["value"])
    right = __format_value(alert["query"]["right"])
    return {
        "alertId": alert["alertId"],
        "tenantId": alert["tenantId"],
        "title": alert["name"],
        "description": f"{alert['seriesName']} = {left} ({alert['query']['operator']} {right}).",
        "buttonText": "Check metrics for more details",
        "buttonUrl": f"/{alert['projectId']}/metrics",
        "imageUrl": None,
        "projectId": alert["projectId"],
        "projectName": alert["projectName"],
        "options": {
            "source": "ALERT",
            "sourceId": alert["alertId"],
            "sourceMeta": alert["detectionMethod"],
            "message": alert["options"]["message"],
            "projectId": alert["projectId"],
            "data": {
                "title": alert["name"],
                "limitValue": alert["query"]["right"],
                "actualValue": float(result["value"]) if isinstance(result["value"], decimal.Decimal) else result["value"],
                "operator": alert["query"]["operator"],
                "trigger": alert["query"]["left"],
                "alertId": alert["alertId"],
                "detectionMethod": alert["detectionMethod"],
                "currentPeriod": alert["options"]["currentPeriod"],
                "previousPeriod": alert["options"]["previousPeriod"],
                "createdAt": TimeUTC.now(),
            },
        },
    }
