# 这段代码实现了一个与项目分析、统计图表相关的API模块。通过定义不同的函数，代码能够获取并处理不同类型的图表数据，包括时间序列图、漏斗图、热力图、路径分析图、会话列表、错误列表等。
# 此外，代码还实现了对指标卡片（Card）的创建、更新、删除以及搜索功能，能够支持用户自定义和预定义的指标类型。代码的设计采用了FastAPI框架，并利用了PostgreSQL数据库和JSON格式的数据存储。
import json
import logging

from decouple import config
from fastapi import HTTPException, status

import schemas
from chalicelib.core import sessions, funnels, errors, issues, heatmaps, sessions_mobs, product_analytics, \
    custom_metrics_predefined
from chalicelib.utils import helper, pg_client
from chalicelib.utils.TimeUTC import TimeUTC
from chalicelib.utils.storage import StorageClient

logger = logging.getLogger(__name__)
# 定义一个常量，用于表示饼图的分组数量
PIE_CHART_GROUP = 5


# TODO: refactor this to split
#  timeseries /
#  table of errors / table of issues / table of browsers / table of devices / table of countries / table of URLs
# remove "table of" calls from this function

# 函数：__try_live
# 功能：获取实时系列数据，用于时间序列图表的绘制。
# 参数：
# - project_id: 项目ID，用于指定数据的项目。
# - data: schemas.CardSchema类型，包含系列数据的过滤条件和其他相关信息。
# 返回值：
# - results: 包含每个系列查询结果的列表。
def __try_live(project_id, data: schemas.CardSchema):
    results = []
    for i, s in enumerate(data.series):
        results.append(sessions.search2_series(data=s.filter, project_id=project_id, density=data.density,
                                               view_type=data.view_type, metric_type=data.metric_type,
                                               metric_of=data.metric_of, metric_value=data.metric_value))

    return results


# 函数：__get_table_of_series
# 功能：获取系列的表格数据，适用于各类表格图表的数据处理。
# 参数：
# - project_id: 项目ID，指定数据的项目。
# - data: schemas.CardSchema类型，包含系列数据的过滤条件和其他相关信息。
# 返回值：
# - results: 包含每个系列表格查询结果的列表。
def __get_table_of_series(project_id, data: schemas.CardSchema):
    results = []
    for i, s in enumerate(data.series):
        results.append(sessions.search2_table(data=s.filter, project_id=project_id, density=data.density,
                                              metric_of=data.metric_of, metric_value=data.metric_value,
                                              metric_format=data.metric_format))

    return results

# 函数：__get_funnel_chart
# 功能：获取漏斗图数据，分析用户在漏斗中的行为并识别重要的见解。
# 参数：
# - project_id: 项目ID，指定数据的项目。
# - data: schemas.CardFunnel类型，包含漏斗分析所需的过滤条件。
# - user_id: 用户ID，指定请求数据的用户（可选）。
# 返回值：
# - 漏斗图的数据，包含阶段和由于问题导致的总丢失数量。
def __get_funnel_chart(project_id: int, data: schemas.CardFunnel, user_id: int = None):
    if len(data.series) == 0:
        return {
            "stages": [],
            "totalDropDueToIssues": 0
        }

    return funnels.get_top_insights_on_the_fly_widget(project_id=project_id,
                                                      data=data.series[0].filter,
                                                      metric_of=data.metric_of)

# 函数：__get_errors_list
# 功能：获取指定项目和用户的错误列表。
# 参数：
# - project_id: 项目ID，指定数据的项目。
# - user_id: 用户ID，指定请求数据的用户。
# - data: schemas.CardSchema类型，包含系列数据的过滤条件和其他相关信息。
# 返回值：
# - 错误列表的数据，包含总错误数量和错误详细信息。
def __get_errors_list(project_id, user_id, data: schemas.CardSchema):
    if len(data.series) == 0:
        return {
            "total": 0,
            "errors": []
        }
    return errors.search(data.series[0].filter, project_id=project_id, user_id=user_id)

# 函数：__get_sessions_list
# 功能：获取指定项目和用户的会话列表。
# 参数：
# - project_id: 项目ID，指定数据的项目。
# - user_id: 用户ID，指定请求数据的用户。
# - data: schemas.CardSchema类型，包含系列数据的过滤条件和其他相关信息。
# 返回值：
# - 会话列表的数据，包含总会话数量和会话详细信息。
def __get_sessions_list(project_id, user_id, data: schemas.CardSchema):
    if len(data.series) == 0:
        logger.debug("empty series")
        return {
            "total": 0,
            "sessions": []
        }
    return sessions.search_sessions(data=data.series[0].filter, project_id=project_id, user_id=user_id)

# 函数：__get_heat_map_chart
# 功能：获取热力图数据，根据过滤条件返回与热力图相关的会话数据。
# 参数：
# - project_id: 项目ID，指定数据的项目。
# - user_id: 用户ID，指定请求数据的用户。
# - data: schemas.CardHeatMap类型，包含热力图分析所需的过滤条件。
# - include_mobs: bool类型，指示是否包含移动设备数据（默认值为True）。
# 返回值：
# - 热力图的数据，包含过滤后的会话数据，如果系列为空则返回None。
def __get_heat_map_chart(project_id, user_id, data: schemas.CardHeatMap, include_mobs: bool = True):
    if len(data.series) == 0:
        return None
    data.series[0].filter.filters += data.series[0].filter.events
    data.series[0].filter.events = []
    return heatmaps.search_short_session(project_id=project_id, user_id=user_id,
                                         data=schemas.HeatMapSessionsSearch(
                                             **data.series[0].filter.model_dump()),
                                         include_mobs=include_mobs)

# 函数：__get_path_analysis_chart
# 功能：获取路径分析图数据，根据用户路径分析需求返回相关的路径数据。
# 参数：
# - project_id: 项目ID，指定数据的项目。
# - user_id: 用户ID，指定请求数据的用户。
# - data: schemas.CardPathAnalysis类型，包含路径分析所需的过滤条件。
# 返回值：
# - 路径分析图的数据，包含分析结果。
def __get_path_analysis_chart(project_id: int, user_id: int, data: schemas.CardPathAnalysis):
    if len(data.series) == 0:
        data.series.append(
            schemas.CardPathAnalysisSeriesSchema(startTimestamp=data.startTimestamp, endTimestamp=data.endTimestamp))
    elif not isinstance(data.series[0].filter, schemas.PathAnalysisSchema):
        data.series[0].filter = schemas.PathAnalysisSchema()

    return product_analytics.path_analysis(project_id=project_id, data=data)

# 函数：__get_timeseries_chart
# 功能：获取时间序列图数据，处理多个系列的数据并返回时间序列图的结构化结果。
# 参数：
# - project_id: 项目ID，指定数据的项目。
# - data: schemas.CardTimeSeries类型，包含时间序列图所需的过滤条件。
# - user_id: 用户ID，指定请求数据的用户（可选）。
# 返回值：
# - results: 包含每个时间点的时间戳和对应的计数数据的列表。
def __get_timeseries_chart(project_id: int, data: schemas.CardTimeSeries, user_id: int = None):
    series_charts = __try_live(project_id=project_id, data=data)
    results = [{}] * len(series_charts[0])
    for i in range(len(results)):
        for j, series_chart in enumerate(series_charts):
            results[i] = {**results[i], "timestamp": series_chart[i]["timestamp"],
                          data.series[j].name if data.series[j].name else j + 1: series_chart[i]["count"]}
    return results

# 函数：not_supported
# 功能：处理不支持的图表类型，当请求的图表类型不被支持时抛出异常。
# 参数：
# - **args: 可变参数，用于接收不定数量的参数。
# 返回值：
# - 无返回值，直接抛出异常。
def not_supported(**args):
    raise Exception("not supported")

# 函数：__get_table_of_user_ids
# 功能：获取用户ID的表格数据，实际上是调用了获取系列表格数据的函数。
# 参数：
# - project_id: 项目ID，指定数据的项目。
# - data: schemas.CardTable类型，包含表格数据的过滤条件。
# - user_id: 用户ID，指定请求数据的用户（可选）。
# 返回值：
# - 包含用户ID表格查询结果的列表。
def __get_table_of_user_ids(project_id: int, data: schemas.CardTable, user_id: int = None):
    return __get_table_of_series(project_id=project_id, data=data)

# 函数：__get_table_of_sessions
# 功能：获取会话的表格数据，通过会话过滤条件返回表格查询结果。
# 参数：
# - project_id: 项目ID，指定数据的项目。
# - data: schemas.CardTable类型，包含表格数据的过滤条件。
# - user_id: 用户ID，指定请求数据的用户。
# 返回值：
# - 包含会话表格查询结果的列表
def __get_table_of_sessions(project_id: int, data: schemas.CardTable, user_id):
    return __get_sessions_list(project_id=project_id, user_id=user_id, data=data)

# 函数：__get_table_of_errors
# 功能：获取错误的表格数据，通过错误过滤条件返回表格查询结果。
# 参数：
# - project_id: 项目ID，指定数据的项目。
# - data: schemas.CardTable类型，包含表格数据的过滤条件。
# - user_id: 用户ID，指定请求数据的用户。
# 返回值：
# - 包含错误表格查询结果的列表。
def __get_table_of_errors(project_id: int, data: schemas.CardTable, user_id: int):
    return __get_errors_list(project_id=project_id, user_id=user_id, data=data)

# 函数：__get_table_of_issues
# 功能：获取问题的表格数据，通过问题过滤条件返回表格查询结果。
# 参数：
# - project_id: 项目ID，指定数据的项目。
# - data: schemas.CardTable类型，包含表格数据的过滤条件。
# - user_id: 用户ID，指定请求数据的用户（可选）。
# 返回值：
# - 包含问题表格查询结果的列表。
def __get_table_of_issues(project_id: int, data: schemas.CardTable, user_id: int = None):
    return __get_table_of_series(project_id=project_id, data=data)

# 函数：__get_table_of_browsers
# 功能：获取浏览器的表格数据，通过浏览器过滤条件返回表格查询结果。
# 参数：
# - project_id: 项目ID，指定数据的项目。
# - data: schemas.CardTable类型，包含表格数据的过滤条件。
# - user_id: 用户ID，指定请求数据的用户（可选）。
# 返回值：
# - 包含浏览器表格查询结果的列表。
def __get_table_of_browsers(project_id: int, data: schemas.CardTable, user_id: int = None):
    return __get_table_of_series(project_id=project_id, data=data)

# 函数：__get_table_of_devises
# 功能：获取设备的表格数据，通过设备过滤条件返回表格查询结果。
# 参数：
# - project_id: 项目ID，指定数据的项目。
# - data: schemas.CardTable类型，包含表格数据的过滤条件。
# - user_id: 用户ID，指定请求数据的用户（可选）。
# 返回值：
# - 包含设备表格查询结果的列表。
def __get_table_of_devises(project_id: int, data: schemas.CardTable, user_id: int = None):
    return __get_table_of_series(project_id=project_id, data=data)

# 函数：__get_table_of_countries
# 功能：获取国家的表格数据，通过国家过滤条件返回表格查询结果。
# 参数：
# - project_id: 项目ID，指定数据的项目。
# - data: schemas.CardTable类型，包含表格数据的过滤条件。
# - user_id: 用户ID，指定请求数据的用户（可选）。
# 返回值：
# - 包含国家表格查询结果的列表
def __get_table_of_countries(project_id: int, data: schemas.CardTable, user_id: int = None):
    return __get_table_of_series(project_id=project_id, data=data)

# 函数：__get_table_of_urls
# 功能：获取URL的表格数据，通过URL过滤条件返回表格查询结果。
# 参数：
# - project_id: 项目ID，指定数据的项目。
# - data: schemas.CardTable类型，包含表格数据的过滤条件。
# - user_id: 用户ID，指定请求数据的用户（可选）。
# 返回值：
# - 包含URL表格查询结果的列表。
def __get_table_of_urls(project_id: int, data: schemas.CardTable, user_id: int = None):
    return __get_table_of_series(project_id=project_id, data=data)

# 函数：__get_table_chart
# 功能：根据指定的表格类型获取表格数据，支持不同的表格类型如会话、错误、用户ID等。
# 参数：
# - project_id: 项目ID，指定数据的项目。
# - data: schemas.CardTable类型，包含表格数据的过滤条件和表格类型信息。
# - user_id: 用户ID，指定请求数据的用户。
# 返回值：
# - 根据表格类型返回相应的表格查询结果，若不支持则抛出异常
def __get_table_chart(project_id: int, data: schemas.CardTable, user_id: int):
    supported = {
        schemas.MetricOfTable.sessions: __get_table_of_sessions,
        schemas.MetricOfTable.errors: __get_table_of_errors,
        schemas.MetricOfTable.user_id: __get_table_of_user_ids,
        schemas.MetricOfTable.issues: __get_table_of_issues,
        schemas.MetricOfTable.user_browser: __get_table_of_browsers,
        schemas.MetricOfTable.user_device: __get_table_of_devises,
        schemas.MetricOfTable.user_country: __get_table_of_countries,
        schemas.MetricOfTable.visited_url: __get_table_of_urls,
    }
    return supported.get(data.metric_of, not_supported)(project_id=project_id, data=data, user_id=user_id)

# 函数：get_chart
# 功能：根据指定的图表类型获取图表数据，支持时间序列图、表格图、热力图、漏斗图、路径分析图等。
# 参数：
# - project_id: 项目ID，指定数据的项目。
# - data: schemas.CardSchema类型，包含图表所需的过滤条件和图表类型信息。
# - user_id: 用户ID，指定请求数据的用户。
# 返回值：
# - 返回对应图表类型的数据，如果是预定义的指标，则返回预定义的指标数据；如果图表类型不支持，则抛出异常。

def get_chart(project_id: int, data: schemas.CardSchema, user_id: int):
    if data.is_predefined:
        return custom_metrics_predefined.get_metric(key=data.metric_of,
                                                    project_id=project_id,
                                                    data=data.model_dump())

    supported = {
        schemas.MetricType.timeseries: __get_timeseries_chart,
        schemas.MetricType.table: __get_table_chart,
        schemas.MetricType.heat_map: __get_heat_map_chart,
        schemas.MetricType.funnel: __get_funnel_chart,
        schemas.MetricType.insights: not_supported,
        schemas.MetricType.pathAnalysis: __get_path_analysis_chart
    }
    return supported.get(data.metric_type, not_supported)(project_id=project_id, data=data, user_id=user_id)


# def __merge_metric_with_data(metric: schemas.CardSchema,
#                              data: schemas.CardSessionsSchema) -> schemas.CardSchema:
#     metric.startTimestamp = data.startTimestamp
#     metric.endTimestamp = data.endTimestamp
#     metric.page = data.page
#     metric.limit = data.limit
#     metric.density = data.density
#     if data.series is not None and len(data.series) > 0:
#         metric.series = data.series
#
#     # if len(data.filters) > 0:
#     #     for s in metric.series:
#     #         s.filter.filters += data.filters
#     # metric = schemas.CardSchema(**metric.model_dump(by_alias=True))
#     return metric

# 函数：get_sessions_by_card_id
# 功能：根据卡片ID获取与之相关的会话数据，并生成会话列表。
# 参数：
# - project_id: 项目ID，指定数据的项目。
# - user_id: 用户ID，指定请求数据的用户。
# - metric_id: 指标ID，指定数据所属的指标卡片。
# - data: schemas.CardSessionsSchema类型，包含会话数据的过滤条件和其他信息。
# 返回值：
# - 返回与指定指标卡片相关的会话数据列表。
def get_sessions_by_card_id(project_id, user_id, metric_id, data: schemas.CardSessionsSchema):
    # No need for this because UI is sending the full payload
    # card: dict = get_card(metric_id=metric_id, project_id=project_id, user_id=user_id, flatten=False)
    # if card is None:
    #    return None
    # metric: schemas.CardSchema = schemas.CardSchema(**card)
    # metric: schemas.CardSchema = __merge_metric_with_data(metric=metric, data=data)
    if not card_exists(metric_id=metric_id, project_id=project_id, user_id=user_id):
        return None
    results = []
    for s in data.series:
        results.append({"seriesId": s.series_id, "seriesName": s.name,
                        **sessions.search_sessions(data=s.filter, project_id=project_id, user_id=user_id)})

    return results

# 函数：get_funnel_issues
# 功能：根据指标ID获取漏斗分析中的问题列表，返回与这些问题相关的会话数据。
# 参数：
# - project_id: 项目ID，指定数据的项目。
# - user_id: 用户ID，指定请求数据的用户。
# - metric_id: 指标ID，指定数据所属的指标卡片。
# - data: schemas.CardSessionsSchema类型，包含会话数据的过滤条件和其他信息。
# 返回值：
# - 返回与指定指标卡片相关的漏斗问题列表和会话数据。
def get_funnel_issues(project_id, user_id, metric_id, data: schemas.CardSessionsSchema):
    # No need for this because UI is sending the full payload
    # raw_metric: dict = get_card(metric_id=metric_id, project_id=project_id, user_id=user_id, flatten=False)
    # if raw_metric is None:
    #     return None
    # metric: schemas.CardSchema = schemas.CardSchema(**raw_metric)
    # metric: schemas.CardSchema = __merge_metric_with_data(metric=metric, data=data)
    # if metric is None:
    #     return None
    if not card_exists(metric_id=metric_id, project_id=project_id, user_id=user_id):
        return None
    for s in data.series:
        return {"seriesId": s.series_id, "seriesName": s.name,
                **funnels.get_issues_on_the_fly_widget(project_id=project_id, data=s.filter)}

# 函数：get_errors_list
# 功能：根据指标ID获取错误列表，返回与这些错误相关的会话数据。
# 参数：
# - project_id: 项目ID，指定数据的项目。
# - user_id: 用户ID，指定请求数据的用户。
# - metric_id: 指标ID，指定数据所属的指标卡片。
# - data: schemas.CardSessionsSchema类型，包含会话数据的过滤条件和其他信息。
# 返回值：
# - 返回与指定指标卡片相关的错误列表和会话数据。
def get_errors_list(project_id, user_id, metric_id, data: schemas.CardSessionsSchema):
    # No need for this because UI is sending the full payload
    # raw_metric: dict = get_card(metric_id=metric_id, project_id=project_id, user_id=user_id, flatten=False)
    # if raw_metric is None:
    #     return None
    # metric: schemas.CardSchema = schemas.CardSchema(**raw_metric)
    # metric: schemas.CardSchema = __merge_metric_with_data(metric=metric, data=data)
    # if metric is None:
    #     return None
    if not card_exists(metric_id=metric_id, project_id=project_id, user_id=user_id):
        return None
    for s in data.series:
        return {"seriesId": s.series_id, "seriesName": s.name,
                **errors.search(data=s.filter, project_id=project_id, user_id=user_id)}

# 函数：get_sessions
# 功能：根据给定的过滤条件获取会话数据，处理额外的过滤器并返回会话列表。
# 参数：
# - project_id: 项目ID，指定数据的项目。
# - user_id: 用户ID，指定请求数据的用户。
# - data: schemas.CardSessionsSchema类型，包含会话数据的过滤条件和其他信息。
# 返回值：
# - 返回处理后的会话数据列表。
def get_sessions(project_id, user_id, data: schemas.CardSessionsSchema):
    results = []
    if len(data.series) == 0:
        return results
    for s in data.series:
        if len(data.filters) > 0:
            s.filter.filters += data.filters
            s.filter = schemas.SessionsSearchPayloadSchema(**s.filter.model_dump(by_alias=True))

        results.append({"seriesId": None, "seriesName": s.name,
                        **sessions.search_sessions(data=s.filter, project_id=project_id, user_id=user_id)})

    return results

# 函数：__get_funnel_issues
# 功能：获取漏斗分析中的问题列表，通过过滤条件返回漏斗问题数据。
# 参数：
# - project_id: 项目ID，指定数据的项目。
# - user_id: 用户ID，指定请求数据的用户。
# - data: schemas.CardFunnel类型，包含漏斗分析的过滤条件和其他信息。
# 返回值：
# - 返回处理后的漏斗问题数据列表。
def __get_funnel_issues(project_id: int, user_id: int, data: schemas.CardFunnel):
    if len(data.series) == 0:
        return []
    data.series[0].filter.startTimestamp = data.startTimestamp
    data.series[0].filter.endTimestamp = data.endTimestamp
    data = funnels.get_issues_on_the_fly_widget(project_id=project_id, data=data.series[0].filter)
    return data

# 函数：__get_path_analysis_issues
# 功能：获取路径分析中的问题列表，通过过滤条件返回路径分析问题数据。
# 参数：
# - project_id: 项目ID，指定数据的项目。
# - user_id: 用户ID，指定请求数据的用户。
# - data: schemas.CardPathAnalysis类型，包含路径分析的过滤条件和其他信息。
# 返回值：
# - 返回处理后的路径分析问题数据列表。
def __get_path_analysis_issues(project_id: int, user_id: int, data: schemas.CardPathAnalysis):
    if len(data.filters) > 0 or len(data.series) > 0:
        filters = [f.model_dump(by_alias=True) for f in data.filters] \
                  + [f.model_dump(by_alias=True) for f in data.series[0].filter.filters]
    else:
        return []

    search_data = schemas.SessionsSearchPayloadSchema(
        startTimestamp=data.startTimestamp,
        endTimestamp=data.endTimestamp,
        limit=data.limit,
        page=data.page,
        filters=filters
    )
    # ---- To make issues response close to the chart response
    search_data.filters.append(schemas.SessionSearchFilterSchema(type=schemas.FilterType.events_count,
                                                                 operator=schemas.MathOperator._greater,
                                                                 value=[1]))
    if len(data.start_point) == 0:
        search_data.events.append(schemas.SessionSearchEventSchema2(type=schemas.EventType.location,
                                                                    operator=schemas.SearchEventOperator._is_any,
                                                                    value=[]))
    # ---- End

    for s in data.excludes:
        search_data.events.append(schemas.SessionSearchEventSchema2(type=s.type,
                                                                    operator=schemas.SearchEventOperator._not_on,
                                                                    value=s.value))
    result = sessions.search_table_of_individual_issues(project_id=project_id, data=search_data)
    return result

# 函数：get_issues
# 功能：根据卡片中的设定获取与路径分析、漏斗分析相关的问题数据。
# 参数：
# - project_id: 项目ID，指定数据的项目。
# - user_id: 用户ID，指定请求数据的用户。
# - data: schemas.CardSchema类型，包含问题数据的过滤条件和其他信息。
# 返回值：
# - 返回与路径分析、漏斗分析相关的问题数据。
def get_issues(project_id: int, user_id: int, data: schemas.CardSchema):
    if data.is_predefined:
        return not_supported()
    if data.metric_of == schemas.MetricOfTable.issues:
        return __get_table_of_issues(project_id=project_id, user_id=user_id, data=data)
    supported = {
        schemas.MetricType.timeseries: not_supported,
        schemas.MetricType.table: not_supported,
        schemas.MetricType.heat_map: not_supported,
        schemas.MetricType.funnel: __get_funnel_issues,
        schemas.MetricType.insights: not_supported,
        schemas.MetricType.pathAnalysis: __get_path_analysis_issues,
    }
    return supported.get(data.metric_type, not_supported)(project_id=project_id, data=data, user_id=user_id)

# 函数：__get_path_analysis_card_info
# 功能：获取路径分析卡片的详细信息，包括起点、排除条件、是否隐藏多余路径等。
# 参数：
# - data: schemas.CardPathAnalysis类型，包含路径分析卡片的详细信息。
# 返回值：
# - 返回字典形式的路径分析卡片信息。
def __get_path_analysis_card_info(data: schemas.CardPathAnalysis):
    r = {"start_point": [s.model_dump() for s in data.start_point],
         "start_type": data.start_type,
         "excludes": [e.model_dump() for e in data.excludes],
         "hideExcess": data.hide_excess}
    return r

# 函数：create_card
# 功能：在数据库中创建新的指标卡片，并保存其相关的配置信息和数据。
# 参数：
# - project_id: 项目ID，指定数据的项目。
# - user_id: 用户ID，指定请求数据的用户。
# - data: schemas.CardSchema类型，包含新建指标卡片的配置信息和数据。
# - dashboard: bool类型，指示是否将卡片添加到仪表板（默认值为False）。
# 返回值：
# - 如果dashboard为True，返回创建的卡片ID；否则返回包含卡片详细信息的字典。
def create_card(project_id, user_id, data: schemas.CardSchema, dashboard=False):
    with pg_client.PostgresClient() as cur:
        session_data = None
        if data.metric_type == schemas.MetricType.heat_map:
            if data.session_id is not None:
                session_data = {"sessionId": data.session_id}
            else:
                session_data = __get_heat_map_chart(project_id=project_id, user_id=user_id,
                                                    data=data, include_mobs=False)
                if session_data is not None:
                    session_data = {"sessionId": session_data["sessionId"]}

        _data = {"session_data": json.dumps(session_data) if session_data is not None else None}
        for i, s in enumerate(data.series):
            for k in s.model_dump().keys():
                _data[f"{k}_{i}"] = s.__getattribute__(k)
            _data[f"index_{i}"] = i
            _data[f"filter_{i}"] = s.filter.json()
        series_len = len(data.series)
        params = {"user_id": user_id, "project_id": project_id, **data.model_dump(), **_data}
        params["default_config"] = json.dumps(data.default_config.model_dump())
        params["card_info"] = None
        if data.metric_type == schemas.MetricType.pathAnalysis:
            params["card_info"] = json.dumps(__get_path_analysis_card_info(data=data))

        query = """INSERT INTO metrics (project_id, user_id, name, is_public,
                            view_type, metric_type, metric_of, metric_value,
                            metric_format, default_config, thumbnail, data,
                            card_info)
                   VALUES (%(project_id)s, %(user_id)s, %(name)s, %(is_public)s, 
                              %(view_type)s, %(metric_type)s, %(metric_of)s, %(metric_value)s, 
                              %(metric_format)s, %(default_config)s, %(thumbnail)s, %(session_data)s,
                              %(card_info)s)
                   RETURNING metric_id"""
        if len(data.series) > 0:
            query = f"""WITH m AS ({query})
                        INSERT INTO metric_series(metric_id, index, name, filter)
                        VALUES {",".join([f"((SELECT metric_id FROM m), %(index_{i})s, %(name_{i})s, %(filter_{i})s::jsonb)"
                                          for i in range(series_len)])}
                        RETURNING metric_id;"""

        query = cur.mogrify(query, params)
        cur.execute(query)
        r = cur.fetchone()
        if dashboard:
            return r["metric_id"]
    return {"data": get_card(metric_id=r["metric_id"], project_id=project_id, user_id=user_id)}

# 函数：update_card
# 功能：更新已有的指标卡片，修改其配置信息和数据。
# 参数：
# - metric_id: 指标ID，指定要更新的指标卡片。
# - user_id: 用户ID，指定请求数据的用户。
# - project_id: 项目ID，指定数据的项目。
# - data: schemas.CardSchema类型，包含更新后的指标卡片配置信息和数据。
# 返回值：
# - 返回更新后的指标卡片的详细信息
def update_card(metric_id, user_id, project_id, data: schemas.CardSchema):
    metric: dict = get_card(metric_id=metric_id, project_id=project_id,
                            user_id=user_id, flatten=False, include_data=True)
    if metric is None:
        return None
    series_ids = [r["seriesId"] for r in metric["series"]]
    n_series = []
    d_series_ids = []
    u_series = []
    u_series_ids = []
    params = {"metric_id": metric_id, "is_public": data.is_public, "name": data.name,
              "user_id": user_id, "project_id": project_id, "view_type": data.view_type,
              "metric_type": data.metric_type, "metric_of": data.metric_of,
              "metric_value": data.metric_value, "metric_format": data.metric_format,
              "config": json.dumps(data.default_config.model_dump()), "thumbnail": data.thumbnail}
    for i, s in enumerate(data.series):
        prefix = "u_"
        if s.index is None:
            s.index = i
        if s.series_id is None or s.series_id not in series_ids:
            n_series.append({"i": i, "s": s})
            prefix = "n_"
        else:
            u_series.append({"i": i, "s": s})
            u_series_ids.append(s.series_id)
        ns = s.model_dump()
        for k in ns.keys():
            if k == "filter":
                ns[k] = json.dumps(ns[k])
            params[f"{prefix}{k}_{i}"] = ns[k]
    for i in series_ids:
        if i not in u_series_ids:
            d_series_ids.append(i)
    params["d_series_ids"] = tuple(d_series_ids)
    params["card_info"] = None
    params["session_data"] = json.dumps(metric["data"])
    if data.metric_type == schemas.MetricType.pathAnalysis:
        params["card_info"] = json.dumps(__get_path_analysis_card_info(data=data))
    elif data.metric_type == schemas.MetricType.heat_map:
        if data.session_id is not None:
            params["session_data"] = json.dumps({"sessionId": data.session_id})
        elif metric.get("data") and metric["data"].get("sessionId"):
            params["session_data"] = json.dumps({"sessionId": metric["data"]["sessionId"]})

    with pg_client.PostgresClient() as cur:
        sub_queries = []
        if len(n_series) > 0:
            sub_queries.append(f"""\
            n AS (INSERT INTO metric_series (metric_id, index, name, filter)
                 VALUES {",".join([f"(%(metric_id)s, %(n_index_{s['i']})s, %(n_name_{s['i']})s, %(n_filter_{s['i']})s::jsonb)"
                                   for s in n_series])}
                 RETURNING 1)""")
        if len(u_series) > 0:
            sub_queries.append(f"""\
            u AS (UPDATE metric_series
                    SET name=series.name,
                        filter=series.filter,
                        index=series.index
                    FROM (VALUES {",".join([f"(%(u_series_id_{s['i']})s,%(u_index_{s['i']})s,%(u_name_{s['i']})s,%(u_filter_{s['i']})s::jsonb)"
                                            for s in u_series])}) AS series(series_id, index, name, filter)
                    WHERE metric_series.metric_id =%(metric_id)s AND metric_series.series_id=series.series_id
                 RETURNING 1)""")
        if len(d_series_ids) > 0:
            sub_queries.append("""\
            d AS (DELETE FROM metric_series WHERE metric_id =%(metric_id)s AND series_id IN %(d_series_ids)s
                 RETURNING 1)""")
        query = cur.mogrify(f"""\
            {"WITH " if len(sub_queries) > 0 else ""}{",".join(sub_queries)}
            UPDATE metrics
            SET name = %(name)s, is_public= %(is_public)s, 
                view_type= %(view_type)s, metric_type= %(metric_type)s, 
                metric_of= %(metric_of)s, metric_value= %(metric_value)s,
                metric_format= %(metric_format)s,
                edited_at = timezone('utc'::text, now()),
                default_config = %(config)s,
                thumbnail = %(thumbnail)s,
                card_info = %(card_info)s,
                data = %(session_data)s
            WHERE metric_id = %(metric_id)s
            AND project_id = %(project_id)s 
            AND (user_id = %(user_id)s OR is_public) 
            RETURNING metric_id;""", params)
        cur.execute(query)
    return get_card(metric_id=metric_id, project_id=project_id, user_id=user_id)

# 函数：search_all
# 功能：根据给定的过滤条件搜索所有符合条件的指标卡片，并返回搜索结果。
# 参数：
# - project_id: 项目ID，指定数据的项目。
# - user_id: 用户ID，指定请求数据的用户。
# - data: schemas.SearchCardsSchema类型，包含搜索过滤条件和分页信息。
# - include_series: bool类型，指示是否包含系列数据（默认值为False）。
# 返回值：
# - 返回符合条件的指标卡片列表。
def search_all(project_id, user_id, data: schemas.SearchCardsSchema, include_series=False):
    constraints = ["metrics.project_id = %(project_id)s",
                   "metrics.deleted_at ISNULL"]
    params = {"project_id": project_id, "user_id": user_id,
              "offset": (data.page - 1) * data.limit,
              "limit": data.limit, }
    if data.mine_only:
        constraints.append("user_id = %(user_id)s")
    else:
        constraints.append("(user_id = %(user_id)s OR metrics.is_public)")
    if data.shared_only:
        constraints.append("is_public")

    if data.query is not None and len(data.query) > 0:
        constraints.append("(name ILIKE %(query)s OR owner.owner_email ILIKE %(query)s)")
        params["query"] = helper.values_for_operator(value=data.query,
                                                     op=schemas.SearchEventOperator._contains)
    with pg_client.PostgresClient() as cur:
        sub_join = ""
        if include_series:
            sub_join = """LEFT JOIN LATERAL (SELECT COALESCE(jsonb_agg(metric_series.* ORDER BY index),'[]'::jsonb) AS series
                                                FROM metric_series
                                                WHERE metric_series.metric_id = metrics.metric_id
                                                  AND metric_series.deleted_at ISNULL 
                                                ) AS metric_series ON (TRUE)"""
        query = cur.mogrify(
            f"""SELECT metric_id, project_id, user_id, name, is_public, created_at, edited_at,
                        metric_type, metric_of, metric_format, metric_value, view_type, is_pinned, 
                        dashboards, owner_email, owner_name, default_config AS config, thumbnail
                FROM metrics
                         {sub_join}
                         LEFT JOIN LATERAL (SELECT COALESCE(jsonb_agg(connected_dashboards.* ORDER BY is_public,name),'[]'::jsonb) AS dashboards
                                            FROM (SELECT DISTINCT dashboard_id, name, is_public
                                                  FROM dashboards INNER JOIN dashboard_widgets USING (dashboard_id)
                                                  WHERE deleted_at ISNULL
                                                    AND dashboard_widgets.metric_id = metrics.metric_id
                                                    AND project_id = %(project_id)s
                                                    AND ((dashboards.user_id = %(user_id)s OR is_public))) AS connected_dashboards
                                            ) AS connected_dashboards ON (TRUE)
                         LEFT JOIN LATERAL (SELECT email AS owner_email, name AS owner_name
                                            FROM users
                                            WHERE deleted_at ISNULL
                                              AND users.user_id = metrics.user_id
                                            ) AS owner ON (TRUE)
                WHERE {" AND ".join(constraints)}
                ORDER BY created_at {data.order.value}
                LIMIT %(limit)s OFFSET %(offset)s;""", params)
        logger.debug("---------")
        logger.debug(query)
        logger.debug("---------")
        cur.execute(query)
        rows = cur.fetchall()
        if include_series:
            for r in rows:
                for s in r["series"]:
                    s["filter"] = helper.old_search_payload_to_flat(s["filter"])
        else:
            for r in rows:
                r["created_at"] = TimeUTC.datetime_to_timestamp(r["created_at"])
                r["edited_at"] = TimeUTC.datetime_to_timestamp(r["edited_at"])
        rows = helper.list_to_camel_case(rows)
    return rows

# 函数：get_all
# 功能：获取指定项目和用户的所有指标卡片，迭代执行分页搜索直到获取所有卡片数据。
# 参数：
# - project_id: 项目ID，指定数据的项目。
# - user_id: 用户ID，指定请求数据的用户。
# 返回值：
# - 返回指定项目和用户的所有指标卡片列表。
def get_all(project_id, user_id):
    default_search = schemas.SearchCardsSchema()
    rows = search_all(project_id=project_id, user_id=user_id, data=default_search)
    result = rows
    while len(rows) == default_search.limit:
        default_search.page += 1
        rows = search_all(project_id=project_id, user_id=user_id, data=default_search)
        result += rows

    return result

# 函数：delete_card
# 功能：删除指定的指标卡片，将其标记为删除并更新编辑时间。
# 参数：
# - project_id: 项目ID，指定数据的项目。
# - metric_id: 指标ID，指定要删除的指标卡片。
# - user_id: 用户ID，指定请求数据的用户。
# 返回值：
# - 返回成功删除的状态。
def delete_card(project_id, metric_id, user_id):
    with pg_client.PostgresClient() as cur:
        cur.execute(
            cur.mogrify("""\
            UPDATE public.metrics 
            SET deleted_at = timezone('utc'::text, now()), edited_at = timezone('utc'::text, now()) 
            WHERE project_id = %(project_id)s
              AND metric_id = %(metric_id)s
              AND (user_id = %(user_id)s OR is_public);""",
                        {"metric_id": metric_id, "project_id": project_id, "user_id": user_id})
        )

    return {"state": "success"}

# 函数：__get_path_analysis_attributes
# 功能：从数据库行中提取路径分析的属性信息并返回。
# 参数：
# - row: 包含路径分析信息的数据库行。
# 返回值：
# - 包含路径分析属性信息的字典。
def __get_path_analysis_attributes(row):
    card_info = row.pop("cardInfo")
    row["excludes"] = card_info.get("excludes", [])
    row["startPoint"] = card_info.get("startPoint", [])
    row["startType"] = card_info.get("startType", "start")
    row["hideExcess"] = card_info.get("hideExcess", False)
    return row

# 函数：get_card
# 功能：根据指标ID获取详细的指标卡片信息，包括配置信息和系列数据。
# 参数：
# - metric_id: 指标ID，指定要获取的指标卡片。
# - project_id: 项目ID，指定数据的项目。
# - user_id: 用户ID，指定请求数据的用户。
# - flatten: bool类型，指示是否将嵌套数据展平（默认值为True）。
# - include_data: bool类型，指示是否包含卡片数据（默认值为False）。
# 返回值：
# - 返回包含详细配置信息和系列数据的指标卡片。
def get_card(metric_id, project_id, user_id, flatten: bool = True, include_data: bool = False):
    with pg_client.PostgresClient() as cur:
        query = cur.mogrify(
            f"""SELECT metric_id, project_id, user_id, name, is_public, created_at, deleted_at, edited_at, metric_type, 
                        view_type, metric_of, metric_value, metric_format, is_pinned, default_config, 
                        default_config AS config,series, dashboards, owner_email, card_info
                        {',data' if include_data else ''}
                FROM metrics
                         LEFT JOIN LATERAL (SELECT COALESCE(jsonb_agg(metric_series.* ORDER BY index),'[]'::jsonb) AS series
                                            FROM metric_series
                                            WHERE metric_series.metric_id = metrics.metric_id
                                              AND metric_series.deleted_at ISNULL 
                                            ) AS metric_series ON (TRUE)
                         LEFT JOIN LATERAL (SELECT COALESCE(jsonb_agg(connected_dashboards.* ORDER BY is_public,name),'[]'::jsonb) AS dashboards
                                            FROM (SELECT dashboard_id, name, is_public
                                                  FROM dashboards INNER JOIN dashboard_widgets USING (dashboard_id)
                                                  WHERE deleted_at ISNULL
                                                    AND project_id = %(project_id)s
                                                    AND ((dashboards.user_id = %(user_id)s OR is_public))
                                                    AND metric_id = %(metric_id)s) AS connected_dashboards
                                            ) AS connected_dashboards ON (TRUE)
                         LEFT JOIN LATERAL (SELECT email AS owner_email
                                            FROM users
                                            WHERE deleted_at ISNULL
                                            AND users.user_id = metrics.user_id
                                            ) AS owner ON (TRUE)
                WHERE metrics.project_id = %(project_id)s
                  AND metrics.deleted_at ISNULL
                  AND (metrics.user_id = %(user_id)s OR metrics.is_public)
                  AND metrics.metric_id = %(metric_id)s
                ORDER BY created_at;""",
            {"metric_id": metric_id, "project_id": project_id, "user_id": user_id}
        )
        cur.execute(query)
        row = cur.fetchone()
        if row is None:
            return None
        row["created_at"] = TimeUTC.datetime_to_timestamp(row["created_at"])
        row["edited_at"] = TimeUTC.datetime_to_timestamp(row["edited_at"])
        if flatten:
            for s in row["series"]:
                s["filter"] = helper.old_search_payload_to_flat(s["filter"])
        row = helper.dict_to_camel_case(row)
        if row["metricType"] == schemas.MetricType.pathAnalysis:
            row = __get_path_analysis_attributes(row=row)
    return row

# 函数：get_series_for_alert
# 功能：获取所有可用于告警的系列数据，返回可选的系列ID、名称和单位等信息。
# 参数：
# - project_id: 项目ID，指定数据的项目。
# - user_id: 用户ID，指定请求数据的用户。
# 返回值：
# - 返回包含系列ID、名称、单位和指标ID的列表。
def get_series_for_alert(project_id, user_id):
    with pg_client.PostgresClient() as cur:
        cur.execute(
            cur.mogrify(
                """SELECT series_id AS value,
                       metrics.name || '.' || (COALESCE(metric_series.name, 'series ' || index)) || '.count' AS name,
                       'count' AS unit,
                       FALSE AS predefined,
                       metric_id,
                       series_id
                    FROM metric_series
                             INNER JOIN metrics USING (metric_id)
                    WHERE metrics.deleted_at ISNULL
                      AND metrics.project_id = %(project_id)s
                      AND metrics.metric_type = 'timeseries'
                      AND (user_id = %(user_id)s OR is_public)
                    ORDER BY name;""",
                {"project_id": project_id, "user_id": user_id}
            )
        )
        rows = cur.fetchall()
    return helper.list_to_camel_case(rows)

# 函数：change_state
# 功能：更改指标卡片的激活状态。
# 参数：
# - project_id: 项目ID，指定数据的项目。
# - metric_id: 指标ID，指定要更改状态的指标卡片。
# - user_id: 用户ID，指定请求数据的用户。
# - status: bool类型，指示要设置的状态值（激活或未激活）。
# 返回值：
# - 返回更新状态后的指标卡片详细信息
def change_state(project_id, metric_id, user_id, status):
    with pg_client.PostgresClient() as cur:
        cur.execute(
            cur.mogrify("""\
            UPDATE public.metrics 
            SET active = %(status)s 
            WHERE metric_id = %(metric_id)s
              AND (user_id = %(user_id)s OR is_public);""",
                        {"metric_id": metric_id, "status": status, "user_id": user_id})
        )
    return get_card(metric_id=metric_id, project_id=project_id, user_id=user_id)


# 函数：get_funnel_sessions_by_issue
# 功能：根据指定的问题ID获取漏斗分析中的会话数据。
# 参数：
# - project_id: 项目ID，指定数据的项目。
# - user_id: 用户ID，指定请求数据的用户。
# - metric_id: 指标ID，指定数据所属的指标卡片。
# - issue_id: 问题ID，指定漏斗分析中的问题。
# - data: schemas.CardSessionsSchema类型，包含会话数据的过滤条件和其他信息。
# 返回值：
# - 返回与指定问题相关的会话数据列表。
def get_funnel_sessions_by_issue(user_id, project_id, metric_id, issue_id,
                                 data: schemas.CardSessionsSchema
                                 # , range_value=None, start_date=None, end_date=None
                                 ):
    # No need for this because UI is sending the full payload
    # card: dict = get_card(metric_id=metric_id, project_id=project_id, user_id=user_id, flatten=False)
    # if card is None:
    #     return None
    # metric: schemas.CardSchema = schemas.CardSchema(**card)
    # metric: schemas.CardSchema = __merge_metric_with_data(metric=metric, data=data)
    # if metric is None:
    #     return None
    if not card_exists(metric_id=metric_id, project_id=project_id, user_id=user_id):
        return None
    for s in data.series:
        s.filter.startTimestamp = data.startTimestamp
        s.filter.endTimestamp = data.endTimestamp
        s.filter.limit = data.limit
        s.filter.page = data.page
        issues_list = funnels.get_issues_on_the_fly_widget(project_id=project_id, data=s.filter).get("issues", {})
        issues_list = issues_list.get("significant", []) + issues_list.get("insignificant", [])
        issue = None
        for i in issues_list:
            if i.get("issueId", "") == issue_id:
                issue = i
                break
        if issue is None:
            issue = issues.get(project_id=project_id, issue_id=issue_id)
            if issue is not None:
                issue = {**issue,
                         "affectedSessions": 0,
                         "affectedUsers": 0,
                         "conversionImpact": 0,
                         "lostConversions": 0,
                         "unaffectedSessions": 0}
        return {"seriesId": s.series_id, "seriesName": s.name,
                "sessions": sessions.search_sessions(user_id=user_id, project_id=project_id,
                                                     issue=issue, data=s.filter)
                if issue is not None else {"total": 0, "sessions": []},
                "issue": issue}

# 函数：make_chart_from_card
# 功能：从已有的指标卡片生成图表数据，支持热力图和其他图表类型。
# 参数：
# - project_id: 项目ID，指定数据的项目。
# - user_id: 用户ID，指定请求数据的用户。
# - metric_id: 指标ID，指定数据所属的指标卡片。
# - data: schemas.CardSessionsSchema类型，包含图表数据的过滤条件和其他信息。
# 返回值：
# - 返回生成的图表数据，如果指标卡片不存在则抛出404错误。
def make_chart_from_card(project_id, user_id, metric_id, data: schemas.CardSessionsSchema):
    raw_metric: dict = get_card(metric_id=metric_id, project_id=project_id, user_id=user_id, include_data=True)

    if raw_metric is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="card not found")
    raw_metric["startTimestamp"] = data.startTimestamp
    raw_metric["endTimestamp"] = data.endTimestamp
    raw_metric["limit"] = data.limit
    raw_metric["density"] = data.density
    metric: schemas.CardSchema = schemas.CardSchema(**raw_metric)

    if metric.is_predefined:
        return custom_metrics_predefined.get_metric(key=metric.metric_of,
                                                    project_id=project_id,
                                                    data=data.model_dump())
    elif metric.metric_type == schemas.MetricType.heat_map:
        if raw_metric["data"] and raw_metric["data"].get("sessionId"):
            return heatmaps.get_selected_session(project_id=project_id,
                                                 session_id=raw_metric["data"]["sessionId"])
        else:
            return heatmaps.search_short_session(project_id=project_id,
                                                 data=schemas.HeatMapSessionsSearch(**metric.model_dump()),
                                                 user_id=user_id)

    return get_chart(project_id=project_id, data=metric, user_id=user_id)

# 函数：card_exists
# 功能：检查指标卡片是否存在。
# 参数：
# - metric_id: 指标ID，指定要检查的指标卡片。
# - project_id: 项目ID，指定数据的项目。
# - user_id: 用户ID，指定请求数据的用户。
# 返回值：
# - 如果指标卡片存在则返回True，否则返回False。
def card_exists(metric_id, project_id, user_id) -> bool:
    with pg_client.PostgresClient() as cur:
        query = cur.mogrify(
            f"""SELECT 1
                FROM metrics
                         LEFT JOIN LATERAL (SELECT COALESCE(jsonb_agg(connected_dashboards.* ORDER BY is_public,name),'[]'::jsonb) AS dashboards
                                            FROM (SELECT dashboard_id, name, is_public
                                                  FROM dashboards INNER JOIN dashboard_widgets USING (dashboard_id)
                                                  WHERE deleted_at ISNULL
                                                    AND project_id = %(project_id)s
                                                    AND ((dashboards.user_id = %(user_id)s OR is_public))
                                                    AND metric_id = %(metric_id)s) AS connected_dashboards
                                            ) AS connected_dashboards ON (TRUE)
                         LEFT JOIN LATERAL (SELECT email AS owner_email
                                            FROM users
                                            WHERE deleted_at ISNULL
                                            AND users.user_id = metrics.user_id
                                            ) AS owner ON (TRUE)
                WHERE metrics.project_id = %(project_id)s
                  AND metrics.deleted_at ISNULL
                  AND (metrics.user_id = %(user_id)s OR metrics.is_public)
                  AND metrics.metric_id = %(metric_id)s
                ORDER BY created_at;""",
            {"metric_id": metric_id, "project_id": project_id, "user_id": user_id}
        )
        cur.execute(query)
        row = cur.fetchone()
        return row is not None
