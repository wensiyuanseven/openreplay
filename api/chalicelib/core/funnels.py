# 这段代码的主要功能是对漏斗分析中的事件进行处理，包括过滤、修正和解析，然后通过调用significance模块中的方法来获取实时洞察和问题列表。
# 这些功能可以应用于数据分析平台，用于实时监控用户行为并识别关键问题点。
from typing import List

import schemas
from chalicelib.core import significance
from chalicelib.utils import helper
from chalicelib.utils import sql_helper as sh


# 筛选阶段中的事件类型，保留允许的事件类型
# 参数：
# - stages: 包含SessionSearchEventSchema2类型的阶段列表。
# 返回值：
# - 返回包含有效事件类型且值不为空的阶段列表。
def filter_stages(stages: List[schemas.SessionSearchEventSchema2]):
    ALLOW_TYPES = [
        schemas.EventType.click,
        schemas.EventType.input,
        schemas.EventType.location,
        schemas.EventType.custom,
        schemas.EventType.click_mobile,
        schemas.EventType.input_mobile,
        schemas.EventType.view_mobile,
        schemas.EventType.custom_mobile,
    ]
    return [s for s in stages if s.type in ALLOW_TYPES and s.value is not None]


# 解析事件列表为SessionSearchEventSchema2对象
# 参数：
# - f_events: 字典类型的事件列表。
# 返回值：
# - 返回解析后的SessionSearchEventSchema2对象列表。
def __parse_events(f_events: List[dict]):
    return [schemas.SessionSearchEventSchema2.parse_obj(e) for e in f_events]


# 修正阶段中的事件对象，设置默认操作符，并规范化值的格式
# 参数：
# - f_events: 包含SessionSearchEventSchema2类型的事件列表。
# 返回值：
# - 返回修正后的事件列表。
def __fix_stages(f_events: List[schemas.SessionSearchEventSchema2]):
    if f_events is None:
        return
    events = []
    for e in f_events:
        if e.operator is None:
            e.operator = schemas.SearchEventOperator._is

        if not isinstance(e.value, list):
            e.value = [e.value]
        is_any = sh.isAny_opreator(e.operator)
        if not is_any and isinstance(e.value, list) and len(e.value) == 0:
            continue
        events.append(e)
    return events


# 获取实时洞察小组件的顶级洞察
# 参数：
# - project_id: 项目ID。
# - data: 包含过滤条件的CardSeriesFilterSchema对象。
# - metric_of: 漏斗度量类型。
# 返回值：
# - 返回包含阶段列表和因问题导致的总下降数。
# def get_top_insights_on_the_fly_widget(project_id, data: schemas.FunnelInsightsPayloadSchema):
def get_top_insights_on_the_fly_widget(project_id, data: schemas.CardSeriesFilterSchema, metric_of: schemas.MetricOfFunnels):
    data.events = filter_stages(__parse_events(data.events))
    data.events = __fix_stages(data.events)
    if len(data.events) == 0:
        return {"stages": [], "totalDropDueToIssues": 0}
    insights, total_drop_due_to_issues = significance.get_top_insights(filter_d=data, project_id=project_id, metric_of=metric_of)
    insights = helper.list_to_camel_case(insights)
    if len(insights) > 0:
        if metric_of == schemas.MetricOfFunnels.session_count and total_drop_due_to_issues > (insights[0]["sessionsCount"] - insights[-1]["sessionsCount"]):
            total_drop_due_to_issues = insights[0]["sessionsCount"] - insights[-1]["sessionsCount"]
        elif metric_of == schemas.MetricOfFunnels.user_count and total_drop_due_to_issues > (insights[0]["usersCount"] - insights[-1]["usersCount"]):
            total_drop_due_to_issues = insights[0]["usersCount"] - insights[-1]["usersCount"]
        insights[-1]["dropDueToIssues"] = total_drop_due_to_issues
    return {"stages": insights, "totalDropDueToIssues": total_drop_due_to_issues}


# 获取实时问题小组件中的问题列表
# 参数：
# - project_id: 项目ID。
# - data: 包含过滤条件的CardSeriesFilterSchema对象。
# 返回值：
# - 返回包含问题列表的字典
# def get_issues_on_the_fly_widget(project_id, data: schemas.FunnelSearchPayloadSchema):
def get_issues_on_the_fly_widget(project_id, data: schemas.CardSeriesFilterSchema):
    data.events = filter_stages(data.events)
    data.events = __fix_stages(data.events)
    if len(data.events) < 0:
        return {"issues": []}

    return {"issues": helper.dict_to_camel_case(significance.get_issues_list(filter_d=data, project_id=project_id, first_stage=1, last_stage=len(data.events)))}
