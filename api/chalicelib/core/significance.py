import logging

import schemas
from chalicelib.core import events, metadata
from chalicelib.utils import sql_helper as sh
# 这段代码提供了一系列函数，用于在数据库中检索和分析用户行为数据，特别是与用户会话相关的事件和问题。代码旨在帮助识别影响用户行为转换率的关键问题，
# 并评估这些问题对整体用户体验的影响。这些功能通常用于数据分析平台，以便在项目中识别和解决用户体验中的问题。
"""
todo: remove LIMIT from the query
"""

from typing import List
import math
import warnings
from collections import defaultdict

from psycopg2.extras import RealDictRow
from chalicelib.utils import pg_client, helper

logger = logging.getLogger(__name__)
SIGNIFICANCE_THRSH = 0.4
# Taha: the value 24 was estimated in v1.15
T_VALUES = {1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571, 6: 2.447, 7: 2.365, 8: 2.306, 9: 2.262, 10: 2.228,
            11: 2.201, 12: 2.179, 13: 2.160, 14: 2.145, 15: 2.13, 16: 2.120, 17: 2.110, 18: 2.101, 19: 2.093, 20: 2.086,
            21: 2.080, 22: 2.074, 23: 2.069, 24: 2.067, 25: 2.064, 26: 2.060, 27: 2.056, 28: 2.052, 29: 2.045,
            30: 2.042}

# 功能描述:
# 该函数用于根据给定的过滤条件和事件，从数据库中检索相关的用户会话数据，并生成各阶段的查询结果。

# 参数:

# filter_d: 包含过滤条件和事件信息的字典。
# project_id: 项目 ID，用于限定查询的范围。
# 返回值:

# List[RealDictRow]: 包含会话数据的列表，按照阶段进行分组。
def get_stages_and_events(filter_d: schemas.CardSeriesFilterSchema, project_id) -> List[RealDictRow]:
    """
    Add minimal timestamp
    :param filter_d: dict contains events&filters&...
    :return:
    """
    stages: [dict] = filter_d.events
    filters: [dict] = filter_d.filters
    filter_issues = []

    stage_constraints = ["main.timestamp <= %(endTimestamp)s"]
    first_stage_extra_constraints = ["s.project_id=%(project_id)s", "s.start_ts >= %(startTimestamp)s",
                                     "s.start_ts <= %(endTimestamp)s"]
    filter_extra_from = []
    n_stages_query = []
    values = {}
    if len(filters) > 0:
        meta_keys = None
        for i, f in enumerate(filters):
            if len(f.value) == 0:
                continue
            f.value = helper.values_for_operator(value=f.value, op=f.operator)

            op = sh.get_sql_operator(f.operator)

            filter_type = f.type
            f_k = f"f_value{i}"
            values = {**values,
                      **sh.multi_values(f.value, value_key=f_k)}
            is_not = False
            if sh.is_negation_operator(f.operator):
                is_not = True
            if filter_type == schemas.FilterType.user_browser:
                first_stage_extra_constraints.append(
                    sh.multi_conditions(f's.user_browser {op} %({f_k})s', f.value, is_not=is_not, value_key=f_k))

            elif filter_type in [schemas.FilterType.user_os, schemas.FilterType.user_os_mobile]:
                first_stage_extra_constraints.append(
                    sh.multi_conditions(f's.user_os {op} %({f_k})s', f.value, is_not=is_not, value_key=f_k))

            elif filter_type in [schemas.FilterType.user_device, schemas.FilterType.user_device_mobile]:
                first_stage_extra_constraints.append(
                    sh.multi_conditions(f's.user_device {op} %({f_k})s', f.value, is_not=is_not, value_key=f_k))

            elif filter_type in [schemas.FilterType.user_country, schemas.FilterType.user_country_mobile]:
                first_stage_extra_constraints.append(
                    sh.multi_conditions(f's.user_country {op} %({f_k})s', f.value, is_not=is_not, value_key=f_k))
            elif filter_type == schemas.FilterType.duration:
                if len(f.value) > 0 and f.value[0] is not None:
                    first_stage_extra_constraints.append(f's.duration >= %(minDuration)s')
                    values["minDuration"] = f.value[0]
                if len(f["value"]) > 1 and f.value[1] is not None and int(f.value[1]) > 0:
                    first_stage_extra_constraints.append('s.duration <= %(maxDuration)s')
                    values["maxDuration"] = f.value[1]
            elif filter_type == schemas.FilterType.referrer:
                # events_query_part = events_query_part + f"INNER JOIN events.pages AS p USING(session_id)"
                filter_extra_from = [f"INNER JOIN {events.EventType.LOCATION.table} AS p USING(session_id)"]
                first_stage_extra_constraints.append(
                    sh.multi_conditions(f"p.base_referrer {op} %({f_k})s", f.value, is_not=is_not, value_key=f_k))
            elif filter_type == events.EventType.METADATA.ui_type:
                if meta_keys is None:
                    meta_keys = metadata.get(project_id=project_id)
                    meta_keys = {m["key"]: m["index"] for m in meta_keys}
                if f.source in meta_keys.keys():
                    first_stage_extra_constraints.append(
                        sh.multi_conditions(
                            f's.{metadata.index_to_colname(meta_keys[f.source])} {op} %({f_k})s', f.value,
                            is_not=is_not, value_key=f_k))
                    # values[f_k] = helper.string_to_sql_like_with_op(f["value"][0], op)
            elif filter_type in [schemas.FilterType.user_id, schemas.FilterType.user_id_mobile]:
                first_stage_extra_constraints.append(
                    sh.multi_conditions(f's.user_id {op} %({f_k})s', f.value, is_not=is_not, value_key=f_k))
                # values[f_k] = helper.string_to_sql_like_with_op(f["value"][0], op)
            elif filter_type in [schemas.FilterType.user_anonymous_id,
                                 schemas.FilterType.user_anonymous_id_mobile]:
                first_stage_extra_constraints.append(
                    sh.multi_conditions(f's.user_anonymous_id {op} %({f_k})s', f.value, is_not=is_not, value_key=f_k))
                # values[f_k] = helper.string_to_sql_like_with_op(f["value"][0], op)
            elif filter_type in [schemas.FilterType.rev_id, schemas.FilterType.rev_id_mobile]:
                first_stage_extra_constraints.append(
                    sh.multi_conditions(f's.rev_id {op} %({f_k})s', f.value, is_not=is_not, value_key=f_k))
                # values[f_k] = helper.string_to_sql_like_with_op(f["value"][0], op)
    i = -1
    for s in stages:

        if s.operator is None:
            s.operator = schemas.SearchEventOperator._is

        if not isinstance(s.value, list):
            s.value = [s.value]
        is_any = sh.isAny_opreator(s.operator)
        if not is_any and isinstance(s.value, list) and len(s.value) == 0:
            continue
        i += 1
        if i == 0:
            extra_from = filter_extra_from + ["INNER JOIN public.sessions AS s USING (session_id)"]
        else:
            extra_from = []
        op = sh.get_sql_operator(s.operator)
        # event_type = s["type"].upper()
        event_type = s.type
        if event_type == events.EventType.CLICK.ui_type:
            next_table = events.EventType.CLICK.table
            next_col_name = events.EventType.CLICK.column
        elif event_type == events.EventType.INPUT.ui_type:
            next_table = events.EventType.INPUT.table
            next_col_name = events.EventType.INPUT.column
        elif event_type == events.EventType.LOCATION.ui_type:
            next_table = events.EventType.LOCATION.table
            next_col_name = events.EventType.LOCATION.column
        elif event_type == events.EventType.CUSTOM.ui_type:
            next_table = events.EventType.CUSTOM.table
            next_col_name = events.EventType.CUSTOM.column
        #     IOS --------------
        elif event_type == events.EventType.CLICK_MOBILE.ui_type:
            next_table = events.EventType.CLICK_MOBILE.table
            next_col_name = events.EventType.CLICK_MOBILE.column
        elif event_type == events.EventType.INPUT_MOBILE.ui_type:
            next_table = events.EventType.INPUT_MOBILE.table
            next_col_name = events.EventType.INPUT_MOBILE.column
        elif event_type == events.EventType.VIEW_MOBILE.ui_type:
            next_table = events.EventType.VIEW_MOBILE.table
            next_col_name = events.EventType.VIEW_MOBILE.column
        elif event_type == events.EventType.CUSTOM_MOBILE.ui_type:
            next_table = events.EventType.CUSTOM_MOBILE.table
            next_col_name = events.EventType.CUSTOM_MOBILE.column
        else:
            logging.warning(f"=================UNDEFINED:{event_type}")
            continue

        values = {**values, **sh.multi_values(helper.values_for_operator(value=s.value, op=s.operator),
                                              value_key=f"value{i + 1}")}
        if sh.is_negation_operator(s.operator) and i > 0:
            op = sh.reverse_sql_operator(op)
            main_condition = "left_not.session_id ISNULL"
            extra_from.append(f"""LEFT JOIN LATERAL (SELECT session_id 
                                                        FROM {next_table} AS s_main 
                                                        WHERE 
                                                        {sh.multi_conditions(f"s_main.{next_col_name} {op} %(value{i + 1})s",
                                                                             values=s.value, value_key=f"value{i + 1}")}
                                                        AND s_main.timestamp >= T{i}.stage{i}_timestamp
                                                        AND s_main.session_id = T1.session_id) AS left_not ON (TRUE)""")
        else:
            if is_any:
                main_condition = "TRUE"
            else:
                main_condition = sh.multi_conditions(f"main.{next_col_name} {op} %(value{i + 1})s",
                                                     values=s.value, value_key=f"value{i + 1}")
        n_stages_query.append(f""" 
        (SELECT main.session_id, 
                {"MIN(main.timestamp)" if i + 1 < len(stages) else "MAX(main.timestamp)"} AS stage{i + 1}_timestamp
        FROM {next_table} AS main {" ".join(extra_from)}        
        WHERE main.timestamp >= {f"T{i}.stage{i}_timestamp" if i > 0 else "%(startTimestamp)s"}
            {f"AND main.session_id=T1.session_id" if i > 0 else ""}
            AND {main_condition}
            {(" AND " + " AND ".join(stage_constraints)) if len(stage_constraints) > 0 else ""}
            {(" AND " + " AND ".join(first_stage_extra_constraints)) if len(first_stage_extra_constraints) > 0 and i == 0 else ""}
        GROUP BY main.session_id)
        AS T{i + 1} {"ON (TRUE)" if i > 0 else ""}
        """)
    n_stages = len(n_stages_query)
    if n_stages == 0:
        return []
    n_stages_query = " LEFT JOIN LATERAL ".join(n_stages_query)
    n_stages_query += ") AS stages_t"

    n_stages_query = f"""
    SELECT stages_and_issues_t.*, sessions.user_uuid, sessions.user_id
    FROM (
        SELECT * FROM (
             SELECT T1.session_id, {",".join([f"stage{i + 1}_timestamp" for i in range(n_stages)])}
              FROM {n_stages_query}
        LEFT JOIN LATERAL 
        (   SELECT  ISS.type as issue_type,  
                    ISE.timestamp AS issue_timestamp,
                    COALESCE(ISS.context_string,'') as issue_context,
                    ISS.issue_id as issue_id
            FROM events_common.issues AS ISE INNER JOIN issues AS ISS USING (issue_id)
            WHERE ISE.timestamp >= stages_t.stage1_timestamp 
                AND ISE.timestamp <= stages_t.stage{i + 1}_timestamp 
                AND ISS.project_id=%(project_id)s
                AND ISE.session_id = stages_t.session_id
                AND ISS.type!='custom' -- ignore custom issues because they are massive
                {"AND ISS.type IN %(issueTypes)s" if len(filter_issues) > 0 else ""}
            LIMIT 10 -- remove the limit to get exact stats
        ) AS issues_t ON (TRUE)
    ) AS stages_and_issues_t INNER JOIN sessions USING(session_id);
    """

    params = {"project_id": project_id, "startTimestamp": filter_d.startTimestamp,
              "endTimestamp": filter_d.endTimestamp,
              "issueTypes": tuple(filter_issues), **values}
    with pg_client.PostgresClient() as cur:
        query = cur.mogrify(n_stages_query, params)
        logging.debug("---------------------------------------------------")
        logging.debug(query)
        logging.debug("---------------------------------------------------")
        try:
            cur.execute(query)
            rows = cur.fetchall()
        except Exception as err:
            logging.warning("--------- FUNNEL SEARCH QUERY EXCEPTION -----------")
            logging.warning(query.decode('UTF-8'))
            logging.warning("--------- PAYLOAD -----------")
            logging.warning(filter_d.model_dump_json())
            logging.warning("--------------------")
            raise err
    for r in rows:
        if r["user_id"] == "":
            r["user_id"] = None
    return rows

# 函数 pearson_corr
# 功能描述:
# 该函数计算两个列表之间的皮尔逊相关系数，以评估它们之间的线性相关性。

# 参数:

# x: 列表，表示变量 X 的数据。
# y: 列表，表示变量 Y 的数据。
# 返回值:

# (float, float, bool): 返回相关系数、置信度以及相关性是否显著的元组。
def pearson_corr(x: list, y: list):
    n = len(x)
    if n != len(y):
        raise ValueError(f'x and y must have the same length. Got {len(x)} and {len(y)} instead')

    if n < 2:
        warnings.warn(f'x and y must have length at least 2. Got {n} instead')
        return None, None, False

    # If an input is constant, the correlation coefficient is not defined.
    if all(t == x[0] for t in x) or all(t == y[0] for t in y):
        warnings.warn("An input array is constant; the correlation coefficent is not defined.")
        return None, None, False

    if n == 2:
        return math.copysign(1, x[1] - x[0]) * math.copysign(1, y[1] - y[0]), 1.0, True

    xmean = sum(x) / len(x)
    ymean = sum(y) / len(y)

    xm = [el - xmean for el in x]
    ym = [el - ymean for el in y]

    normxm = math.sqrt((sum([xm[i] * xm[i] for i in range(len(xm))])))
    normym = math.sqrt((sum([ym[i] * ym[i] for i in range(len(ym))])))

    threshold = 1e-8
    if normxm < threshold * abs(xmean) or normym < threshold * abs(ymean):
        # If all the values in x (likewise y) are very close to the mean,
        # the loss of precision that occurs in the subtraction xm = x - xmean
        # might result in large errors in r.
        warnings.warn("An input array is constant; the correlation coefficent is not defined.")

    r = sum(
        i[0] * i[1] for i in zip([xm[i] / normxm for i in range(len(xm))], [ym[i] / normym for i in range(len(ym))]))

    # Presumably, if abs(r) > 1, then it is only some small artifact of  floating point arithmetic.
    # However, if r < 0, we don't care, as our problem is to find only positive correlations
    r = max(min(r, 1.0), 0.0)

    # approximated confidence
    if n < 31:
        t_c = T_VALUES[n]
    elif n < 50:
        t_c = 2.02
    else:
        t_c = 2
    if r >= 0.999:
        confidence = 1
    else:
        confidence = r * math.sqrt(n - 2) / math.sqrt(1 - r ** 2)

    if confidence > SIGNIFICANCE_THRSH:
        return r, confidence, True
    else:
        return r, confidence, False


# def tuple_or(t: tuple):
#     x = 0
#     for el in t:
#         x |= el # | is for bitwise OR
#     return x
#
# The following function is correct optimization of the previous function because t is a list of 0,1
# 函数 tuple_or
# 功能描述:
# 该函数计算一个元组的按位或运算，优化了元组中包含二进制值（0 或 1）的操作。

# 参数:

# t: 元组，包含二进制值。
# 返回值:

# int: 如果元组中包含至少一个 1，返回 1，否则返回 0。
def tuple_or(t: tuple):
    for el in t:
        if el > 0:
            return 1
    return 0

# 功能描述:
# 该函数根据用户会话数据，识别每个用户在不同阶段之间的转换，并统计每种类型的问题在这些阶段之间的发生情况。

# 参数:

# rows: 包含会话数据的列表。
# all_issues: 包含所有问题的字典。
# first_stage: 第一个阶段的索引。
# last_stage: 最后一个阶段的索引。
# 返回值:

# (list, dict, list, int): 返回转换列表、错误字典、所有错误的二进制列表以及受影响的会话数。
def get_transitions_and_issues_of_each_type(rows: List[RealDictRow], all_issues, first_stage, last_stage):
    """
    Returns two lists with binary values 0/1:

    transitions ::: if transited from the first stage to the last - 1
                    else - 0
    errors      ::: a dictionary WHERE the keys are all unique issues (currently context-wise)
                    the values are lists
                    if an issue happened between the first stage to the last - 1
                    else - 0

    For a small task of calculating a total drop due to issues,
    we need to disregard the issue type when creating the `errors`-like array.
    The `all_errors` array can be obtained by logical OR statement applied to all errors by issue
    The `transitions` array stays the same
    """
    transitions = []
    n_sess_affected = 0
    errors = {}

    for row in rows:
        t = 0
        first_ts = row[f'stage{first_stage}_timestamp']
        last_ts = row[f'stage{last_stage}_timestamp']
        if first_ts is None:
            continue
        elif last_ts is not None:
            t = 1
        transitions.append(t)

        ic_present = False
        for error_id in all_issues:
            if error_id not in errors:
                errors[error_id] = []
            ic = 0
            row_issue_id = row['issue_id']
            if row_issue_id is not None:
                if last_ts is None or (first_ts < row['issue_timestamp'] < last_ts):
                    if error_id == row_issue_id:
                        ic = 1
                        ic_present = True
            errors[error_id].append(ic)

        if ic_present and t:
            n_sess_affected += 1

    all_errors = [tuple_or(t) for t in zip(*errors.values())]

    return transitions, errors, all_errors, n_sess_affected

# 功能描述:
# 该函数识别并统计在指定阶段之间，所有会话中每个问题的影响范围，包括受影响的用户和会话数量。

# 参数:

# rows: 包含会话数据的列表。
# first_stage: 第一个阶段的索引。
# last_stage: 最后一个阶段的索引。
# 返回值:

# (dict, dict, dict, dict): 返回所有问题的字典、问题数量字典、受影响用户数量字典和受影响会话数量字典。
def get_affected_users_for_all_issues(rows, first_stage, last_stage):
    """

    :param rows:
    :param first_stage:
    :param last_stage:
    :return:
    """
    affected_users = defaultdict(lambda: set())
    affected_sessions = defaultdict(lambda: set())
    all_issues = {}
    n_affected_users_dict = defaultdict(lambda: None)
    n_affected_sessions_dict = defaultdict(lambda: None)
    n_issues_dict = defaultdict(lambda: 0)
    issues_by_session = defaultdict(lambda: 0)

    for row in rows:

        # check that the session has reached the first stage of subfunnel:
        if row[f'stage{first_stage}_timestamp'] is None:
            continue

        iss = row['issue_type']
        iss_ts = row['issue_timestamp']

        # check that the issue exists and belongs to subfunnel:
        if iss is not None and (row[f'stage{last_stage}_timestamp'] is None or
                                (row[f'stage{first_stage}_timestamp'] < iss_ts < row[f'stage{last_stage}_timestamp'])):
            if row["issue_id"] not in all_issues:
                all_issues[row["issue_id"]] = {"context": row['issue_context'], "issue_type": row["issue_type"]}
            n_issues_dict[row["issue_id"]] += 1
            if row['user_uuid'] is not None:
                affected_users[row["issue_id"]].add(row['user_uuid'])

            affected_sessions[row["issue_id"]].add(row['session_id'])
            issues_by_session[row[f'session_id']] += 1

    if len(affected_users) > 0:
        n_affected_users_dict.update({
            iss: len(affected_users[iss]) for iss in affected_users
        })
    if len(affected_sessions) > 0:
        n_affected_sessions_dict.update({
            iss: len(affected_sessions[iss]) for iss in affected_sessions
        })
    return all_issues, n_issues_dict, n_affected_users_dict, n_affected_sessions_dict

# 功能描述:
# 该函数统计在每个阶段中，参与会话的数量。

# 参数:

# rows: 包含会话数据的列表。
# n_stages: 阶段的数量。
# 返回值:

# dict: 返回每个阶段的会话数量字典。
def count_sessions(rows, n_stages):
    session_counts = {i: set() for i in range(1, n_stages + 1)}
    for row in rows:
        for i in range(1, n_stages + 1):
            if row[f"stage{i}_timestamp"] is not None:
                session_counts[i].add(row[f"session_id"])

    session_counts = {i: len(session_counts[i]) for i in session_counts}
    return session_counts

# 功能描述:
# 该函数统计在每个阶段中，参与用户的数量。

# 参数:

# rows: 包含会话数据的列表。
# n_stages: 阶段的数量。
# user_key: 用户唯一标识符的键名，默认为 user_uuid。
# 返回值:

# dict: 返回每个阶段的用户数量字典。
def count_users(rows, n_stages, user_key="user_uuid"):
    users_in_stages = {i: set() for i in range(1, n_stages + 1)}
    for row in rows:
        for i in range(1, n_stages + 1):
            if row[f"stage{i}_timestamp"] is not None and row[user_key] is not None:
                users_in_stages[i].add(row[user_key])

    users_count = {i: len(users_in_stages[i]) for i in range(1, n_stages + 1)}
    return users_count

# 功能描述:
# 该函数根据会话数据，生成各阶段的统计信息，包括会话数量、用户数量以及阶段间的转换率。

# 参数:

# stages: 包含阶段信息的列表。
# rows: 包含会话数据的列表。
# metric_of: 衡量标准，如会话计数（session_count）或用户计数。
# 返回值:

# list: 返回阶段的统计信息列表。
def get_stages(stages, rows, metric_of=schemas.MetricOfFunnels.session_count):
    n_stages = len(stages)
    if metric_of == "sessionCount":
        base_counts = count_sessions(rows, n_stages)
    else:
        base_counts = count_users(rows, n_stages, user_key="user_id")

    stages_list = []
    for i, stage in enumerate(stages):

        drop = None
        if i != 0:
            if base_counts[i] == 0:
                drop = 0
            elif base_counts[i] > 0:
                drop = int(100 * (base_counts[i] - base_counts[i + 1]) / base_counts[i])

        stages_list.append(
            {"value": stage.value,
             "type": stage.type,
             "operator": stage.operator,
             "drop_pct": drop,
             "dropDueToIssues": 0
             }
        )
        if metric_of == "sessionCount":
            stages_list[-1]["sessionsCount"] = base_counts[i + 1]
        else:
            stages_list[-1]["usersCount"] = base_counts[i + 1]

    return stages_list

# 功能描述:
# 该函数根据会话数据，分析在各阶段之间的用户行为中，哪些问题对转换率产生了显著影响。

# 参数:

# stages: 包含阶段信息的列表。
# rows: 包含会话数据的列表。
# first_stage: 第一阶段的索引，默认为 None。
# last_stage: 最后阶段的索引，默认为 None。
# drop_only: 布尔值，表示是否只返回由于问题导致的掉落数量。
# 返回值:

# (int, dict, int): 返回关键问题的数量、问题字典以及由于问题导致的掉落数量。
def get_issues(stages, rows, first_stage=None, last_stage=None, drop_only=False):
    """

    :param stages:
    :param rows:
    :param first_stage: If it's a part of the initial funnel, provide a number of the first stage (starting from 1)
    :param last_stage: If it's a part of the initial funnel, provide a number of the last stage (starting from 1)
    :return:
    """

    n_stages = len(stages)

    if first_stage is None:
        first_stage = 1
    if last_stage is None:
        last_stage = n_stages
    if last_stage > n_stages:
        logging.debug(
            "The number of the last stage provided is greater than the number of stages. Using n_stages instead")
        last_stage = n_stages

    n_critical_issues = 0
    issues_dict = {"significant": [],
                   "insignificant": []}
    session_counts = count_sessions(rows, n_stages)
    drop = session_counts[first_stage] - session_counts[last_stage]

    all_issues, n_issues_dict, affected_users_dict, affected_sessions = get_affected_users_for_all_issues(
        rows, first_stage, last_stage)
    transitions, errors, all_errors, n_sess_affected = get_transitions_and_issues_of_each_type(rows,
                                                                                               all_issues,
                                                                                               first_stage, last_stage)

    del rows

    if any(all_errors):
        total_drop_corr, conf, is_sign = pearson_corr(transitions, all_errors)
        if total_drop_corr is not None and drop is not None:
            total_drop_due_to_issues = int(total_drop_corr * n_sess_affected)
        else:
            total_drop_due_to_issues = 0
    else:
        total_drop_due_to_issues = 0

    if drop_only:
        return total_drop_due_to_issues
    for issue_id in all_issues:

        if not any(errors[issue_id]):
            continue
        r, confidence, is_sign = pearson_corr(transitions, errors[issue_id])

        if r is not None and drop is not None and is_sign:
            lost_conversions = int(r * affected_sessions[issue_id])
        else:
            lost_conversions = None
        if r is None:
            r = 0
        issues_dict['significant' if is_sign else 'insignificant'].append({
            "type": all_issues[issue_id]["issue_type"],
            "title": helper.get_issue_title(all_issues[issue_id]["issue_type"]),
            "affected_sessions": affected_sessions[issue_id],
            "unaffected_sessions": session_counts[1] - affected_sessions[issue_id],
            "lost_conversions": lost_conversions,
            "affected_users": affected_users_dict[issue_id],
            "conversion_impact": round(r * 100),
            "context_string": all_issues[issue_id]["context"],
            "issue_id": issue_id
        })

        if is_sign:
            n_critical_issues += n_issues_dict[issue_id]
    # To limit the number of returned issues to the frontend
    issues_dict["significant"] = issues_dict["significant"][:20]
    issues_dict["insignificant"] = issues_dict["insignificant"][:20]

    return n_critical_issues, issues_dict, total_drop_due_to_issues

# 功能描述:
# 该函数用于获取用户行为分析的顶级洞察，包括各阶段的统计信息和由于问题导致的掉落数量。

# 参数:

# filter_d: 包含过滤条件和事件信息的字典。
# project_id: 项目 ID，用于限定查询的范围。
# metric_of: 衡量标准，如会话计数或用户计数。
# 返回值:

# (list, int): 返回阶段的统计信息列表和由于问题导致的掉落数量。

def get_top_insights(filter_d: schemas.CardSeriesFilterSchema, project_id, metric_of: schemas.MetricOfFunnels):
    output = []
    stages = filter_d.events

    if len(stages) == 0:
        logging.debug("no stages found")
        return output, 0

    # The result of the multi-stage query
    rows = get_stages_and_events(filter_d=filter_d, project_id=project_id)
    # Obtain the first part of the output
    stages_list = get_stages(stages, rows, metric_of=metric_of)
    if len(rows) == 0:
        return stages_list, 0

    # Obtain the second part of the output
    total_drop_due_to_issues = get_issues(stages, rows,
                                          first_stage=1,
                                          last_stage=len(filter_d.events),
                                          drop_only=True)
    return stages_list, total_drop_due_to_issues

# 功能描述:
# 该函数生成一个问题列表，列出了在指定阶段之间，导致用户行为转换率下降的关键问题。

# 参数:

# filter_d: 包含过滤条件和事件信息的字典。
# project_id: 项目 ID，用于限定查询的范围。
# first_stage: 第一阶段的索引，默认为 None。
# last_stage: 最后阶段的索引，默认为 None。
# 返回值:

# dict: 包含关键问题和由于问题导致的掉落数量的字典。
def get_issues_list(filter_d: schemas.CardSeriesFilterSchema, project_id, first_stage=None, last_stage=None):
    output = dict({"total_drop_due_to_issues": 0, "critical_issues_count": 0, "significant": [], "insignificant": []})
    stages = filter_d.events
    # The result of the multi-stage query
    rows = get_stages_and_events(filter_d=filter_d, project_id=project_id)
    if len(rows) == 0:
        return output
        # Obtain the second part of the output
    n_critical_issues, issues_dict, total_drop_due_to_issues = get_issues(stages, rows, first_stage=first_stage,
                                                                          last_stage=last_stage)
    output['total_drop_due_to_issues'] = total_drop_due_to_issues
    # output['critical_issues_count'] = n_critical_issues
    output = {**output, **issues_dict}
    return output
