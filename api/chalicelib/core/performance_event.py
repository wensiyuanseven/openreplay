import schemas

# 该代码片段定义了一个函数get_col，用于根据传入的性能事件类型（perf）返回一个包含数据库查询信息的字典。此字典包括数据库列名和可能需要的额外连接表信息。该函数主要用于处理与性能事件相关的查询，帮助构建动态SQL查询语句。

# 功能描述：
# 根据传入的性能事件类型返回相应的列名和额外的表连接信息，用于动态构建SQL查询。

# 参数：
# perf: schemas.PerformanceEventType类型的枚举值，表示性能事件的具体类型。
# 返回值：
# 一个字典，包含以下键值对：
# column: 字符串，表示数据库中对应性能事件的列名。
# extraJoin: 字符串或None，表示是否需要在查询中进行额外的表连接。如果不需要额外连接，则为None。

def get_col(perf: schemas.PerformanceEventType):
    return {
        schemas.PerformanceEventType.location_dom_complete: {"column": "dom_building_time", "extraJoin": None},
        schemas.PerformanceEventType.location_ttfb: {"column": "ttfb", "extraJoin": None},
        schemas.PerformanceEventType.location_avg_cpu_load: {"column": "avg_cpu", "extraJoin": "events.performance"},
        schemas.PerformanceEventType.location_avg_memory_usage: {"column": "avg_used_js_heap_size",
                                                                 "extraJoin": "events.performance"},
        schemas.PerformanceEventType.fetch_failed: {"column": "success", "extraJoin": None},
        # schemas.PerformanceEventType.fetch_duration: {"column": "duration", "extraJoin": None},
        schemas.PerformanceEventType.location_largest_contentful_paint_time: {"column": "first_contentful_paint_time",
                                                                              "extraJoin": None}
    }.get(perf)
