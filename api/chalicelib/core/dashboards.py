# 这段代码实现了一个与仪表盘管理相关的API模块。通过定义一系列函数，代码能够处理仪表盘的创建、更新、删除、获取以及仪表盘小部件（widgets）的增删改查操作。
# 代码的设计支持在仪表盘中添加和管理不同的指标（metrics），并且能够将指标卡片转换为可视化的图表。
import json
import schemas
from chalicelib.core import custom_metrics
from chalicelib.utils import helper
from chalicelib.utils import pg_client
from chalicelib.utils.TimeUTC import TimeUTC

# 函数：create_dashboard
# 功能：创建一个新的仪表盘，并可选择添加与之关联的小部件（widgets）。
# 参数：
# - project_id: 项目ID，指定数据的项目。
# - user_id: 用户ID，指定请求数据的用户。
# - data: schemas.CreateDashboardSchema类型，包含新建仪表盘的配置信息和小部件列表。
# 返回值：
# - 如果成功，返回创建的仪表盘的详细信息；否则返回错误信息。
def create_dashboard(project_id, user_id, data: schemas.CreateDashboardSchema):
    with pg_client.PostgresClient() as cur:
        pg_query = f"""INSERT INTO dashboards(project_id, user_id, name, is_public, is_pinned, description) 
                        VALUES(%(projectId)s, %(userId)s, %(name)s, %(is_public)s, %(is_pinned)s, %(description)s)
                        RETURNING *"""
        params = {"userId": user_id, "projectId": project_id, **data.model_dump()}
        if data.metrics is not None and len(data.metrics) > 0:
            pg_query = f"""WITH dash AS ({pg_query})
                         INSERT INTO dashboard_widgets(dashboard_id, metric_id, user_id, config)
                         VALUES {",".join([f"((SELECT dashboard_id FROM dash),%(metric_id_{i})s, %(userId)s, (SELECT default_config FROM metrics WHERE metric_id=%(metric_id_{i})s)||%(config_{i})s)" for i in range(len(data.metrics))])}
                         RETURNING (SELECT dashboard_id FROM dash)"""
            for i, m in enumerate(data.metrics):
                params[f"metric_id_{i}"] = m
                # params[f"config_{i}"] = schemas.AddWidgetToDashboardPayloadSchema.schema() \
                #     .get("properties", {}).get("config", {}).get("default", {})
                # params[f"config_{i}"]["position"] = i
                # params[f"config_{i}"] = json.dumps(params[f"config_{i}"])
                params[f"config_{i}"] = json.dumps({"position": i})
        cur.execute(cur.mogrify(pg_query, params))
        row = cur.fetchone()
    if row is None:
        return {"errors": ["something went wrong while creating the dashboard"]}
    return {"data": get_dashboard(project_id=project_id, user_id=user_id, dashboard_id=row["dashboard_id"])}

# 函数：get_dashboards
# 功能：获取指定项目和用户的所有仪表盘信息。
# 参数：
# - project_id: 项目ID，指定数据的项目。
# - user_id: 用户ID，指定请求数据的用户。
# 返回值：
# - 返回所有符合条件的仪表盘列表。
def get_dashboards(project_id, user_id):
    with pg_client.PostgresClient() as cur:
        pg_query = f"""SELECT *, owner_email, owner_name
                        FROM dashboards
                         LEFT JOIN LATERAL (SELECT email AS owner_email, name AS owner_name
                                            FROM users
                                            WHERE deleted_at ISNULL
                                              AND users.user_id = dashboards.user_id
                                            ) AS owner ON (TRUE)
                        WHERE deleted_at ISNULL
                          AND project_id = %(projectId)s
                          AND (user_id = %(userId)s OR is_public);"""
        params = {"userId": user_id, "projectId": project_id}
        cur.execute(cur.mogrify(pg_query, params))
        rows = cur.fetchall()
    return helper.list_to_camel_case(rows)

# 函数：get_dashboard
# 功能：获取指定的仪表盘详细信息，包括与之关联的小部件。
# 参数：
# - project_id: 项目ID，指定数据的项目。
# - user_id: 用户ID，指定请求数据的用户。
# - dashboard_id: 仪表盘ID，指定要获取的仪表盘。
# 返回值：
# - 返回仪表盘的详细信息和关联的小部件列表。
def get_dashboard(project_id, user_id, dashboard_id):
    with pg_client.PostgresClient() as cur:
        pg_query = """SELECT dashboards.*, all_metric_widgets.widgets AS widgets
                        FROM dashboards
                                 LEFT JOIN LATERAL (SELECT COALESCE(JSONB_AGG(raw_metrics), '[]') AS widgets
                                                    FROM (SELECT dashboard_widgets.*, 
                                                                 metrics.name, metrics.edited_at,metrics.metric_of,
                                                                 metrics.view_type,metrics.thumbnail,metrics.metric_type,
                                                                 metrics.metric_format,metrics.metric_value,metrics.default_config,
                                                                 metric_series.series
                                                          FROM metrics
                                                               INNER JOIN dashboard_widgets USING (metric_id)
                                                               LEFT JOIN LATERAL (
                                                                      SELECT COALESCE(JSONB_AGG(metric_series.* ORDER BY index),'[]') AS series
                                                                      FROM (SELECT metric_series.name, 
                                                                                   metric_series.index, 
                                                                                   metric_series.metric_id,
                                                                                   metric_series.series_id, 
                                                                                   metric_series.created_at
                                                                            FROM metric_series
                                                                            WHERE metric_series.metric_id = metrics.metric_id
                                                                              AND metric_series.deleted_at ISNULL) AS metric_series
                                                              ) AS metric_series ON (TRUE)
                                                          WHERE dashboard_widgets.dashboard_id = dashboards.dashboard_id
                                                            AND metrics.deleted_at ISNULL
                                                            AND (metrics.project_id = %(projectId)s OR metrics.project_id ISNULL)) AS raw_metrics
                            ) AS all_metric_widgets ON (TRUE)
                        WHERE dashboards.deleted_at ISNULL
                          AND dashboards.project_id = %(projectId)s
                          AND dashboard_id = %(dashboard_id)s
                          AND (dashboards.user_id = %(userId)s OR is_public);"""
        params = {"userId": user_id, "projectId": project_id, "dashboard_id": dashboard_id}
        cur.execute(cur.mogrify(pg_query, params))
        row = cur.fetchone()
        if row is not None:
            row["created_at"] = TimeUTC.datetime_to_timestamp(row["created_at"])
            for w in row["widgets"]:
                w["created_at"] = TimeUTC.datetime_to_timestamp(w["created_at"])
                w["edited_at"] = TimeUTC.datetime_to_timestamp(w["edited_at"])
                w["config"]["col"] = w["default_config"]["col"]
                w["config"]["row"] = w["default_config"]["row"]
                w.pop("default_config")
                for s in w["series"]:
                    s["created_at"] = TimeUTC.datetime_to_timestamp(s["created_at"])
    return helper.dict_to_camel_case(row)

# 函数：delete_dashboard
# 功能：删除指定的仪表盘，将其标记为删除并更新删除时间。
# 参数：
# - project_id: 项目ID，指定数据的项目。
# - user_id: 用户ID，指定请求数据的用户。
# - dashboard_id: 仪表盘ID，指定要删除的仪表盘。
# 返回值：
# - 返回成功删除的状态信息
def delete_dashboard(project_id, user_id, dashboard_id):
    with pg_client.PostgresClient() as cur:
        pg_query = """UPDATE dashboards
                      SET deleted_at = timezone('utc'::text, now())
                        WHERE dashboards.project_id = %(projectId)s
                          AND dashboard_id = %(dashboard_id)s
                          AND (dashboards.user_id = %(userId)s OR is_public);"""
        params = {"userId": user_id, "projectId": project_id, "dashboard_id": dashboard_id}
        cur.execute(cur.mogrify(pg_query, params))
    return {"data": {"success": True}}

# 函数：update_dashboard
# 功能：更新指定的仪表盘信息，可以选择修改名称、描述、是否公开、是否固定等属性，并可添加新的小部件。
# 参数：
# - project_id: 项目ID，指定数据的项目。
# - user_id: 用户ID，指定请求数据的用户。
# - dashboard_id: 仪表盘ID，指定要更新的仪表盘。
# - data: schemas.EditDashboardSchema类型，包含更新的仪表盘信息。
# 返回值：
# - 返回更新后的仪表盘的详细信息。
def update_dashboard(project_id, user_id, dashboard_id, data: schemas.EditDashboardSchema):
    with pg_client.PostgresClient() as cur:
        pg_query = """SELECT COALESCE(COUNT(*),0) AS count
                    FROM dashboard_widgets
                    WHERE dashboard_id = %(dashboard_id)s;"""
        params = {"userId": user_id, "projectId": project_id, "dashboard_id": dashboard_id, **data.model_dump()}
        cur.execute(cur.mogrify(pg_query, params))
        row = cur.fetchone()
        offset = row["count"]
        pg_query = f"""UPDATE dashboards
                       SET name = %(name)s,
                          description= %(description)s
                            {", is_public = %(is_public)s" if data.is_public is not None else ""}
                            {", is_pinned = %(is_pinned)s" if data.is_pinned is not None else ""}
                       WHERE dashboards.project_id = %(projectId)s
                          AND dashboard_id = %(dashboard_id)s
                          AND (dashboards.user_id = %(userId)s OR is_public)
                       RETURNING dashboard_id,name,description,is_public,created_at"""
        if data.metrics is not None and len(data.metrics) > 0:
            pg_query = f"""WITH dash AS ({pg_query})
                           INSERT INTO dashboard_widgets(dashboard_id, metric_id, user_id, config)
                           VALUES {",".join([f"(%(dashboard_id)s, %(metric_id_{i})s, %(userId)s, (SELECT default_config FROM metrics WHERE metric_id=%(metric_id_{i})s)||%(config_{i})s)" for i in range(len(data.metrics))])}
                           RETURNING (SELECT dashboard_id FROM dash),(SELECT name FROM dash),
                                     (SELECT description FROM dash),(SELECT is_public FROM dash),
                                     (SELECT created_at FROM dash);"""
            for i, m in enumerate(data.metrics):
                params[f"metric_id_{i}"] = m
                # params[f"config_{i}"] = schemas.AddWidgetToDashboardPayloadSchema.schema() \
                #     .get("properties", {}).get("config", {}).get("default", {})
                # params[f"config_{i}"]["position"] = i
                # params[f"config_{i}"] = json.dumps(params[f"config_{i}"])
                params[f"config_{i}"] = json.dumps({"position": i + offset})

        cur.execute(cur.mogrify(pg_query, params))
        row = cur.fetchone()
        if row:
            row["created_at"] = TimeUTC.datetime_to_timestamp(row["created_at"])
    return helper.dict_to_camel_case(row)

# 函数：get_widget
# 功能：
# get_widget 函数用于获取指定仪表盘小部件的详细信息，包括与之关联的指标（metrics）及其系列数据（series）。
# 参数：
# project_id: int
# 项目ID，指定要查询的数据所属的项目。
# user_id: int
# 用户ID，指定请求数据的用户。
# dashboard_id: int
# 仪表盘ID，指定该小部件所属的仪表盘。
# widget_id: int
# 小部件ID，指定要查询的小部件。
# 返回值：
# dict
# 返回包含小部件及其关联的指标和系列数据的详细信息，数据经过驼峰命名转换以适应前端使用。
def get_widget(project_id, user_id, dashboard_id, widget_id):
    with pg_client.PostgresClient() as cur:
        pg_query = """SELECT metrics.*, metric_series.series
                        FROM dashboard_widgets
                                 INNER JOIN dashboards USING (dashboard_id)
                                 INNER JOIN metrics USING (metric_id)
                                 LEFT JOIN LATERAL (SELECT COALESCE(jsonb_agg(metric_series.* ORDER BY index), '[]'::jsonb) AS series
                                                    FROM metric_series
                                                    WHERE metric_series.metric_id = metrics.metric_id
                                                      AND metric_series.deleted_at ISNULL
                            ) AS metric_series ON (TRUE)
                        WHERE dashboard_id = %(dashboard_id)s
                          AND widget_id = %(widget_id)s
                          AND (dashboards.is_public OR dashboards.user_id = %(userId)s)
                          AND dashboards.deleted_at IS NULL
                          AND metrics.deleted_at ISNULL
                          AND (metrics.project_id = %(projectId)s OR metrics.project_id ISNULL)
                          AND (metrics.is_public OR metrics.user_id = %(userId)s);"""
        params = {"userId": user_id, "projectId": project_id, "dashboard_id": dashboard_id, "widget_id": widget_id}
        cur.execute(cur.mogrify(pg_query, params))
        row = cur.fetchone()
    return helper.dict_to_camel_case(row)

# 函数：add_widget
# 功能：向指定的仪表盘中添加一个新的小部件（widget），并将其与指定的指标（metric）关联。
# 参数：
# - project_id: 项目ID，指定数据的项目。
# - user_id: 用户ID，指定请求数据的用户。
# - dashboard_id: 仪表盘ID，指定要添加小部件的仪表盘。
# - data: schemas.AddWidgetToDashboardPayloadSchema类型，包含新小部件的配置信息和关联指标。
# 返回值：
# - 返回添加的小部件的详细信息。
def add_widget(project_id, user_id, dashboard_id, data: schemas.AddWidgetToDashboardPayloadSchema):
    with pg_client.PostgresClient() as cur:
        pg_query = """INSERT INTO dashboard_widgets(dashboard_id, metric_id, user_id, config)
                          SELECT %(dashboard_id)s AS dashboard_id, %(metric_id)s AS metric_id, 
                                 %(userId)s AS user_id, (SELECT default_config FROM metrics WHERE metric_id=%(metric_id)s)||%(config)s::jsonb AS config
                          WHERE EXISTS(SELECT 1 FROM dashboards 
                                       WHERE dashboards.deleted_at ISNULL AND dashboards.project_id = %(projectId)s
                                          AND dashboard_id = %(dashboard_id)s
                                          AND (dashboards.user_id = %(userId)s OR is_public))
                      RETURNING *;"""
        params = {"userId": user_id, "projectId": project_id, "dashboard_id": dashboard_id, **data.model_dump()}
        params["config"] = json.dumps(data.config)
        cur.execute(cur.mogrify(pg_query, params))
        row = cur.fetchone()
    return helper.dict_to_camel_case(row)

# 函数：update_widget
# 功能：更新指定的仪表盘小部件的配置信息。
# 参数：
# - project_id: 项目ID，指定数据的项目。
# - user_id: 用户ID，指定请求数据的用户。
# - dashboard_id: 仪表盘ID，指定小部件所属的仪表盘。
# - widget_id: 小部件ID，指定要更新的小部件。
# - data: schemas.UpdateWidgetPayloadSchema类型，包含更新的小部件配置信息。
# 返回值：
# - 返回更新后的小部件详细信息。
def update_widget(project_id, user_id, dashboard_id, widget_id, data: schemas.UpdateWidgetPayloadSchema):
    with pg_client.PostgresClient() as cur:
        pg_query = """UPDATE dashboard_widgets
                      SET config= %(config)s
                      WHERE dashboard_id=%(dashboard_id)s AND widget_id=%(widget_id)s
                      RETURNING *;"""
        params = {"userId": user_id, "projectId": project_id, "dashboard_id": dashboard_id, "widget_id": widget_id, **data.model_dump()}
        params["config"] = json.dumps(data.config)
        cur.execute(cur.mogrify(pg_query, params))
        row = cur.fetchone()
    return helper.dict_to_camel_case(row)

# 函数：remove_widget
# 功能：从指定的仪表盘中移除一个小部件。
# 参数：
# - project_id: 项目ID，指定数据的项目。
# - user_id: 用户ID，指定请求数据的用户。
# - dashboard_id: 仪表盘ID，指定要移除小部件的仪表盘。
# - widget_id: 小部件ID，指定要移除的小部件。
# 返回值：
# - 返回成功移除的状态信息。
def remove_widget(project_id, user_id, dashboard_id, widget_id):
    with pg_client.PostgresClient() as cur:
        pg_query = """DELETE FROM dashboard_widgets
                      WHERE dashboard_id=%(dashboard_id)s AND widget_id=%(widget_id)s;"""
        params = {"userId": user_id, "projectId": project_id, "dashboard_id": dashboard_id, "widget_id": widget_id}
        cur.execute(cur.mogrify(pg_query, params))
    return {"data": {"success": True}}

# 函数：pin_dashboard
# 功能：将指定的仪表盘设为固定（pin），同时取消其他仪表盘的固定状态。
# 参数：
# - project_id: 项目ID，指定数据的项目。
# - user_id: 用户ID，指定请求数据的用户。
# - dashboard_id: 仪表盘ID，指定要固定的仪表盘。
# 返回值：
# - 返回固定后的仪表盘详细信息
def pin_dashboard(project_id, user_id, dashboard_id):
    with pg_client.PostgresClient() as cur:
        pg_query = """UPDATE dashboards
                      SET is_pinned = FALSE
                      WHERE project_id=%(project_id)s;
                      UPDATE dashboards
                      SET is_pinned = True
                      WHERE dashboard_id=%(dashboard_id)s AND project_id=%(project_id)s AND deleted_at ISNULL
                      RETURNING *;"""
        params = {"userId": user_id, "project_id": project_id, "dashboard_id": dashboard_id}
        cur.execute(cur.mogrify(pg_query, params))
        row = cur.fetchone()
    return helper.dict_to_camel_case(row)

# 函数：create_metric_add_widget
# 功能：创建新的指标卡片并将其添加为仪表盘的小部件。
# 参数：
# - project_id: 项目ID，指定数据的项目。
# - user_id: 用户ID，指定请求数据的用户。
# - dashboard_id: 仪表盘ID，指定要添加小部件的仪表盘。
# - data: schemas.CardSchema类型，包含新建指标的配置信息。
# 返回值：
# - 返回创建的小部件的详细信息。
def create_metric_add_widget(project_id, user_id, dashboard_id, data: schemas.CardSchema):
    metric_id = custom_metrics.create_card(project_id=project_id, user_id=user_id, data=data, dashboard=True)
    return add_widget(project_id=project_id, user_id=user_id, dashboard_id=dashboard_id, data=schemas.AddWidgetToDashboardPayloadSchema(metricId=metric_id))


# def make_chart_widget(dashboard_id, project_id, user_id, widget_id, data: schemas.CardChartSchema):
#     raw_metric = get_widget(widget_id=widget_id, project_id=project_id, user_id=user_id, dashboard_id=dashboard_id)
#     if raw_metric is None:
#         return None
#     metric = schemas.CustomMetricAndTemplate = schemas.CustomMetricAndTemplate(**raw_metric)
#     if metric.is_template:
#         return get_predefined_metric(key=metric.predefined_key, project_id=project_id, data=data.model_dump())
#     else:
#         return custom_metrics.make_chart(project_id=project_id, user_id=user_id, metric_id=raw_metric["metricId"],
#                                          data=data, metric=raw_metric)
