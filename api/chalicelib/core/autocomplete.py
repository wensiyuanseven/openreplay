# 整个代码的主要目的是实现一个灵活的、可扩展的自动完成功能，支持不同类型的事件、过滤器、错误日志和元数据。
# 它通过生成和执行动态SQL查询，从数据库中检索相关信息并返回给调用者。
# 这些函数设计成可以适应不同的自动完成需求，并且通过模块化的方式分解任务，使得代码更易于维护和扩展。

# 这些导入语句包括了自定义的模块和库，用于处理数据库连接、事件定义、国家信息获取、帮助函数等。
import schemas
from chalicelib.core import countries, events, metadata
from chalicelib.utils import helper
from chalicelib.utils import pg_client
from chalicelib.utils.event_filter_definition import Event



TABLE = "public.autocomplete"

# 这个函数根据输入的值（value）和项目ID（project_id）从一个公共的自动完成表（public.autocomplete）中检索与输入内容相匹配的数据。
# 它处理了多种事件类型和过滤器类型，并根据匹配的类型和输入内容生成不同的子查询。最终，它将这些子查询合并成一个查询语句，执行后返回结果。
def __get_autocomplete_table(value, project_id):
    autocomplete_events = [schemas.FilterType.rev_id,
                           schemas.EventType.click,
                           schemas.FilterType.user_device,
                           schemas.FilterType.user_id,
                           schemas.FilterType.user_browser,
                           schemas.FilterType.user_os,
                           schemas.EventType.custom,
                           schemas.FilterType.user_country,
                           schemas.FilterType.user_city,
                           schemas.FilterType.user_state,
                           schemas.EventType.location,
                           schemas.EventType.input]
    autocomplete_events.sort()
    sub_queries = []
    c_list = []
    for e in autocomplete_events:
        if e == schemas.FilterType.user_country:
            c_list = countries.get_country_code_autocomplete(value)
            if len(c_list) > 0:
                sub_queries.append(f"""(SELECT DISTINCT ON(value) '{e.value}' AS _type, value
                                        FROM {TABLE}
                                        WHERE project_id = %(project_id)s
                                            AND type= '{e.value.upper()}' 
                                            AND value IN %(c_list)s)""")
            continue
        sub_queries.append(f"""(SELECT '{e.value}' AS _type, value
                                FROM {TABLE}
                                WHERE project_id = %(project_id)s
                                    AND type= '{e.value.upper()}' 
                                    AND value ILIKE %(svalue)s
                                ORDER BY value
                                LIMIT 5)""")
        if len(value) > 2:
            sub_queries.append(f"""(SELECT '{e.value}' AS _type, value
                                    FROM {TABLE}
                                    WHERE project_id = %(project_id)s
                                        AND type= '{e.value.upper()}' 
                                        AND value ILIKE %(value)s
                                    ORDER BY value
                                    LIMIT 5)""")
    with pg_client.PostgresClient() as cur:
        query = cur.mogrify(" UNION DISTINCT ".join(sub_queries) + ";",
                            {"project_id": project_id,
                             "value": helper.string_to_sql_like(value),
                             "svalue": helper.string_to_sql_like("^" + value),
                             "c_list": tuple(c_list)
                             })
        try:
            cur.execute(query)
        except Exception as err:
            print("--------- AUTOCOMPLETE SEARCH QUERY EXCEPTION -----------")
            print(query.decode('UTF-8'))
            print("--------- VALUE -----------")
            print(value)
            print("--------------------")
            raise err
        results = cur.fetchall()
    for r in results:
        r["type"] = r.pop("_type")
    results = helper.list_to_camel_case(results)
    return results

# 这个函数根据提供的类型名称（typename）和输入值的长度生成一个通用的SQL查询语句。它主要用于生成适用于不同类型的自动完成查询。
def __generic_query(typename, value_length=None):
    if typename == schemas.FilterType.user_country:
        return f"""SELECT DISTINCT value, type
                    FROM {TABLE}
                    WHERE
                      project_id = %(project_id)s
                      AND type='{typename.upper()}'
                      AND value IN %(value)s
                      ORDER BY value"""

    if value_length is None or value_length > 2:
        return f"""(SELECT DISTINCT value, type
                    FROM {TABLE}
                    WHERE
                      project_id = %(project_id)s
                      AND type='{typename.upper()}'
                      AND value ILIKE %(svalue)s
                      ORDER BY value
                    LIMIT 5)
                    UNION DISTINCT
                    (SELECT DISTINCT value, type
                    FROM {TABLE}
                    WHERE
                      project_id = %(project_id)s
                      AND type='{typename.upper()}'
                      AND value ILIKE %(value)s
                      ORDER BY value
                    LIMIT 5);"""
    return f"""SELECT DISTINCT value, type
                FROM {TABLE}
                WHERE
                  project_id = %(project_id)s
                  AND type='{typename.upper()}'
                  AND value ILIKE %(svalue)s
                  ORDER BY value
                LIMIT 10;"""

# 这个函数返回一个用于执行通用自动完成查询的函数。它使用__generic_query生成查询语句，并使用数据库客户端执行查询，返回结果。
def __generic_autocomplete(event: Event):
    def f(project_id, value, key=None, source=None):
        with pg_client.PostgresClient() as cur:
            query = __generic_query(event.ui_type, value_length=len(value))
            params = {"project_id": project_id, "value": helper.string_to_sql_like(value),
                      "svalue": helper.string_to_sql_like("^" + value)}
            cur.execute(cur.mogrify(query, params))
            return helper.list_to_camel_case(cur.fetchall())

    return f

# 这个函数类似于__generic_autocomplete，但专门用于处理元数据（metadata）的自动完成查询。它可以根据输入的文本返回匹配的元数据结果。
def __generic_autocomplete_metas(typename):
    def f(project_id, text):
        with pg_client.PostgresClient() as cur:
            params = {"project_id": project_id, "value": helper.string_to_sql_like(text),
                      "svalue": helper.string_to_sql_like("^" + text)}

            if typename == schemas.FilterType.user_country:
                params["value"] = tuple(countries.get_country_code_autocomplete(text))
                if len(params["value"]) == 0:
                    return []

            query = cur.mogrify(__generic_query(typename, value_length=len(text)), params)
            cur.execute(query)
            rows = cur.fetchall()
        return rows

    return f

# 这个函数生成一个查询语句，用于从错误日志中搜索与输入值匹配的错误信息。它可以根据输入值的长度和错误的来源（source）来生成不同的查询语句。
def __errors_query(source=None, value_length=None):
    if value_length is None or value_length > 2:
        return f"""((SELECT DISTINCT ON(lg.message)
                        lg.message AS value,
                        source,
                        '{events.EventType.ERROR.ui_type}' AS type
                    FROM {events.EventType.ERROR.table} INNER JOIN public.errors AS lg USING (error_id) LEFT JOIN public.sessions AS s USING(session_id)
                    WHERE
                      s.project_id = %(project_id)s
                      AND lg.message ILIKE %(svalue)s
                      AND lg.project_id = %(project_id)s
                      {"AND source = %(source)s" if source is not None else ""}
                    LIMIT 5)
                    UNION DISTINCT
                    (SELECT DISTINCT ON(lg.name)
                        lg.name AS value,
                        source,
                        '{events.EventType.ERROR.ui_type}' AS type
                    FROM {events.EventType.ERROR.table} INNER JOIN public.errors AS lg USING (error_id) LEFT JOIN public.sessions AS s USING(session_id)
                    WHERE
                      s.project_id = %(project_id)s
                      AND lg.name ILIKE %(svalue)s
                      AND lg.project_id = %(project_id)s
                      {"AND source = %(source)s" if source is not None else ""}
                    LIMIT 5)
                    UNION DISTINCT
                    (SELECT DISTINCT ON(lg.message)
                        lg.message AS value,
                        source,
                        '{events.EventType.ERROR.ui_type}' AS type
                    FROM {events.EventType.ERROR.table} INNER JOIN public.errors AS lg USING (error_id) LEFT JOIN public.sessions AS s USING(session_id)
                    WHERE
                      s.project_id = %(project_id)s
                      AND lg.message ILIKE %(value)s
                      AND lg.project_id = %(project_id)s
                      {"AND source = %(source)s" if source is not None else ""}
                    LIMIT 5)
                    UNION DISTINCT
                    (SELECT DISTINCT ON(lg.name)
                        lg.name AS value,
                        source,
                        '{events.EventType.ERROR.ui_type}' AS type
                    FROM {events.EventType.ERROR.table} INNER JOIN public.errors AS lg USING (error_id) LEFT JOIN public.sessions AS s USING(session_id)
                    WHERE
                      s.project_id = %(project_id)s
                      AND lg.name ILIKE %(value)s
                      AND lg.project_id = %(project_id)s
                      {"AND source = %(source)s" if source is not None else ""}
                    LIMIT 5));"""
    return f"""((SELECT DISTINCT ON(lg.message)
                    lg.message AS value,
                    source,
                    '{events.EventType.ERROR.ui_type}' AS type
                FROM {events.EventType.ERROR.table} INNER JOIN public.errors AS lg USING (error_id) LEFT JOIN public.sessions AS s USING(session_id)
                WHERE
                  s.project_id = %(project_id)s
                  AND lg.message ILIKE %(svalue)s
                  AND lg.project_id = %(project_id)s
                  {"AND source = %(source)s" if source is not None else ""}
                LIMIT 5)
                UNION DISTINCT
                (SELECT DISTINCT ON(lg.name)
                    lg.name AS value,
                    source,
                    '{events.EventType.ERROR.ui_type}' AS type
                FROM {events.EventType.ERROR.table} INNER JOIN public.errors AS lg USING (error_id) LEFT JOIN public.sessions AS s USING(session_id)
                WHERE
                  s.project_id = %(project_id)s
                  AND lg.name ILIKE %(svalue)s
                  AND lg.project_id = %(project_id)s
                  {"AND source = %(source)s" if source is not None else ""}
                LIMIT 5));"""

# 这个函数执行__errors_query生成的查询语句，用于搜索错误信息，并将结果返回。
def __search_errors(project_id, value, key=None, source=None):
    with pg_client.PostgresClient() as cur:
        cur.execute(
            cur.mogrify(__errors_query(source,
                                       value_length=len(value)),
                        {"project_id": project_id, "value": helper.string_to_sql_like(value),
                         "svalue": helper.string_to_sql_like("^" + value),
                         "source": source}))
        results = helper.list_to_camel_case(cur.fetchall())
    return results

# 这个函数类似于__search_errors，但专门用于处理移动设备崩溃日志的搜索。
def __search_errors_mobile(project_id, value, key=None, source=None):
    if len(value) > 2:
        query = f"""(SELECT DISTINCT ON(lg.reason)
                        lg.reason AS value,
                        '{events.EventType.CRASH_MOBILE.ui_type}' AS type
                    FROM {events.EventType.CRASH_MOBILE.table} INNER JOIN public.crashes_ios AS lg USING (crash_ios_id) LEFT JOIN public.sessions AS s USING(session_id)
                    WHERE
                      s.project_id = %(project_id)s
                      AND lg.project_id = %(project_id)s
                      AND lg.reason ILIKE %(svalue)s
                    LIMIT 5)
                    UNION ALL
                    (SELECT DISTINCT ON(lg.name)
                        lg.name AS value,
                        '{events.EventType.CRASH_MOBILE.ui_type}' AS type
                    FROM {events.EventType.CRASH_MOBILE.table} INNER JOIN public.crashes_ios AS lg USING (crash_ios_id) LEFT JOIN public.sessions AS s USING(session_id)
                    WHERE
                      s.project_id = %(project_id)s
                      AND lg.project_id = %(project_id)s
                      AND lg.name ILIKE %(svalue)s
                    LIMIT 5)
                    UNION ALL
                    (SELECT DISTINCT ON(lg.reason)
                        lg.reason AS value,
                        '{events.EventType.CRASH_MOBILE.ui_type}' AS type
                    FROM {events.EventType.CRASH_MOBILE.table} INNER JOIN public.crashes_ios AS lg USING (crash_ios_id) LEFT JOIN public.sessions AS s USING(session_id)
                    WHERE
                      s.project_id = %(project_id)s
                      AND lg.project_id = %(project_id)s
                      AND lg.reason ILIKE %(value)s
                    LIMIT 5)
                    UNION ALL
                    (SELECT DISTINCT ON(lg.name)
                        lg.name AS value,
                        '{events.EventType.CRASH_MOBILE.ui_type}' AS type
                    FROM {events.EventType.CRASH_MOBILE.table} INNER JOIN public.crashes_ios AS lg USING (crash_ios_id) LEFT JOIN public.sessions AS s USING(session_id)
                    WHERE
                      s.project_id = %(project_id)s
                      AND lg.project_id = %(project_id)s
                      AND lg.name ILIKE %(value)s
                    LIMIT 5);"""
    else:
        query = f"""(SELECT DISTINCT ON(lg.reason)
                            lg.reason AS value,
                            '{events.EventType.CRASH_MOBILE.ui_type}' AS type
                        FROM {events.EventType.CRASH_MOBILE.table} INNER JOIN public.crashes_ios AS lg USING (crash_ios_id) LEFT JOIN public.sessions AS s USING(session_id)
                        WHERE
                          s.project_id = %(project_id)s
                          AND lg.project_id = %(project_id)s
                          AND lg.reason ILIKE %(svalue)s
                        LIMIT 5)
                        UNION ALL
                        (SELECT DISTINCT ON(lg.name)
                            lg.name AS value,
                            '{events.EventType.CRASH_MOBILE.ui_type}' AS type
                        FROM {events.EventType.CRASH_MOBILE.table} INNER JOIN public.crashes_ios AS lg USING (crash_ios_id) LEFT JOIN public.sessions AS s USING(session_id)
                        WHERE
                          s.project_id = %(project_id)s
                          AND lg.project_id = %(project_id)s
                          AND lg.name ILIKE %(svalue)s
                        LIMIT 5);"""
    with pg_client.PostgresClient() as cur:
        cur.execute(cur.mogrify(query, {"project_id": project_id, "value": helper.string_to_sql_like(value),
                                        "svalue": helper.string_to_sql_like("^" + value)}))
        results = helper.list_to_camel_case(cur.fetchall())
    return results

# 这个函数根据输入的值和项目ID，从会话表（public.sessions）中检索匹配的元数据信息。它会先获取元数据键的映射，然后根据输入的键和值生成查询语句并执行，返回匹配的结果。
def __search_metadata(project_id, value, key=None, source=None):
    meta_keys = metadata.get(project_id=project_id)
    meta_keys = {m["key"]: m["index"] for m in meta_keys}
    if len(meta_keys) == 0 or key is not None and key not in meta_keys.keys():
        return []
    sub_from = []
    if key is not None:
        meta_keys = {key: meta_keys[key]}

    for k in meta_keys.keys():
        colname = metadata.index_to_colname(meta_keys[k])
        if len(value) > 2:
            sub_from.append(f"""((SELECT DISTINCT ON ({colname}) {colname} AS value, '{k}' AS key 
                                FROM public.sessions 
                                WHERE project_id = %(project_id)s 
                                AND {colname} ILIKE %(svalue)s LIMIT 5)
                                UNION
                                (SELECT DISTINCT ON ({colname}) {colname} AS value, '{k}' AS key 
                                FROM public.sessions 
                                WHERE project_id = %(project_id)s 
                                AND {colname} ILIKE %(value)s LIMIT 5))
                                """)
        else:
            sub_from.append(f"""(SELECT DISTINCT ON ({colname}) {colname} AS value, '{k}' AS key 
                                FROM public.sessions 
                                WHERE project_id = %(project_id)s 
                                AND {colname} ILIKE %(svalue)s LIMIT 5)""")
    with pg_client.PostgresClient() as cur:
        cur.execute(cur.mogrify(f"""\
                    SELECT key, value, 'METADATA' AS TYPE
                    FROM({" UNION ALL ".join(sub_from)}) AS all_metas
                    LIMIT 5;""", {"project_id": project_id, "value": helper.string_to_sql_like(value),
                                  "svalue": helper.string_to_sql_like("^" + value)}))
        results = helper.list_to_camel_case(cur.fetchall())
    return results
