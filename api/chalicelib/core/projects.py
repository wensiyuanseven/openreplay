# 这段代码实现了一个与项目管理相关的API，用于管理项目的创建、编辑、删除以及各种项目相关的操作。它主要通过PostgreSQL数据库执行各种操作，并通过FastAPI框架进行接口处理。
# 这段代码为项目管理提供了全面的API支持，涵盖了项目的创建、编辑、删除、条件管理、捕获状态管理等操作。通过这种方式，系统可以灵活地管理和操控项目数据。如果有进一步的问题或需要更多帮助，请随时告知我！
# 这些操作包括但不限于项目的创建、更新、删除、条件验证、获取项目信息等。
import json
from typing import Optional, List
from collections import Counter

from fastapi import HTTPException, status

import schemas
from chalicelib.core import users
from chalicelib.utils import pg_client, helper
from chalicelib.utils.TimeUTC import TimeUTC

# 功能描述：
# 检查给定的项目名称在数据库中是否已存在，并排除特定项目ID（如果提供）。

# 参数：
# name: 要检查的项目名称。
# exclude_id: 可选参数，如果提供此ID，则在检查时排除这个ID对应的项目。
# 返回值：
# bool: 如果项目名称已存在则返回True，否则返回False。
def __exists_by_name(name: str, exclude_id: Optional[int]) -> bool:
    with pg_client.PostgresClient() as cur:
        query = cur.mogrify(f"""SELECT EXISTS(SELECT 1
                                FROM public.projects
                                WHERE deleted_at IS NULL
                                    AND name ILIKE %(name)s
                                    {"AND project_id!=%(exclude_id)s" if exclude_id else ""}) AS exists;""",
                            {"name": name, "exclude_id": exclude_id})

        cur.execute(query=query)
        row = cur.fetchone()
        return row["exists"]

# 功能描述：
# 更新指定项目的指定字段值。

# 参数：
# tenant_id: 租户ID，用于多租户的支持。
# project_id: 要更新的项目ID。
# changes: 要更新的字段和值的字典。
# 返回值：
# dict: 包含更新后的项目信息的字典。
def __update(tenant_id, project_id, changes):
    if len(changes.keys()) == 0:
        return None

    sub_query = []
    for key in changes.keys():
        sub_query.append(f"{helper.key_to_snake_case(key)} = %({key})s")
    with pg_client.PostgresClient() as cur:
        query = cur.mogrify(f"""UPDATE public.projects 
                                SET {" ,".join(sub_query)} 
                                WHERE project_id = %(project_id)s
                                    AND deleted_at ISNULL
                                RETURNING project_id,name,gdpr;""",
                            {"project_id": project_id, **changes})
        cur.execute(query=query)
        return helper.dict_to_camel_case(cur.fetchone())

# 功能描述：
# 创建一个新的项目，并返回该项目的详细信息。

# 参数：
# tenant_id: 租户ID。
# data: 包含项目创建所需数据的字典。
# 返回值：
# dict: 新创建项目的详细信息。
def __create(tenant_id, data):
    with pg_client.PostgresClient() as cur:
        query = cur.mogrify(f"""INSERT INTO public.projects (name, platform, active)
                                VALUES (%(name)s,%(platform)s,TRUE)
                                RETURNING project_id;""",
                            data)
        cur.execute(query=query)
        project_id = cur.fetchone()["project_id"]
    return get_project(tenant_id=tenant_id, project_id=project_id, include_gdpr=True)

# 功能描述：
# 获取所有项目的列表，并根据提供的参数返回包含GDPR信息或记录状态的信息。

# 参数：
# tenant_id: 租户ID。
# gdpr: 布尔值，是否包含GDPR信息。
# recorded: 布尔值，是否包含记录状态的信息。
# 返回值：
# List[dict]: 项目信息的列表，每个字典包含一个项目的详细信息。
def get_projects(tenant_id: int, gdpr: bool = False, recorded: bool = False):
    with pg_client.PostgresClient() as cur:
        extra_projection = ""
        if gdpr:
            extra_projection += ',s.gdpr'
        if recorded:
            extra_projection += """,\nCOALESCE(EXTRACT(EPOCH FROM s.first_recorded_session_at) * 1000::BIGINT,
                                      (SELECT MIN(sessions.start_ts)
                                       FROM public.sessions
                                       WHERE sessions.project_id = s.project_id
                                         AND sessions.start_ts >= (EXTRACT(EPOCH 
                                                        FROM COALESCE(s.sessions_last_check_at, s.created_at)) * 1000-%(check_delta)s)
                                         AND sessions.start_ts <= %(now)s
                                       )) AS first_recorded"""

        query = cur.mogrify(f"""{"SELECT *, first_recorded IS NOT NULL AS recorded FROM (" if recorded else ""}
                                SELECT s.project_id, s.name, s.project_key, s.save_request_payloads, s.first_recorded_session_at,
                                       s.created_at, s.sessions_last_check_at, s.sample_rate, s.platform,
                                       (SELECT count(*) FROM projects_conditions WHERE project_id = s.project_id) AS conditions_count 
                                       {extra_projection}
                                FROM public.projects AS s
                                WHERE s.deleted_at IS NULL
                                ORDER BY s.name {") AS raw" if recorded else ""};""",
                            {"now": TimeUTC.now(), "check_delta": TimeUTC.MS_HOUR * 4})
        cur.execute(query)
        rows = cur.fetchall()
        # if recorded is requested, check if it was saved or computed
        if recorded:
            u_values = []
            params = {}
            for i, r in enumerate(rows):
                r["sessions_last_check_at"] = TimeUTC.datetime_to_timestamp(r["sessions_last_check_at"])
                r["created_at"] = TimeUTC.datetime_to_timestamp(r["created_at"])
                if r["first_recorded_session_at"] is None \
                        and r["sessions_last_check_at"] is not None \
                        and (TimeUTC.now() - r["sessions_last_check_at"]) > TimeUTC.MS_HOUR:
                    u_values.append(f"(%(project_id_{i})s,to_timestamp(%(first_recorded_{i})s/1000))")
                    params[f"project_id_{i}"] = r["project_id"]
                    params[f"first_recorded_{i}"] = r["first_recorded"] if r["recorded"] else None
                r.pop("first_recorded_session_at")
                r.pop("first_recorded")
                r.pop("sessions_last_check_at")
            if len(u_values) > 0:
                query = cur.mogrify(f"""UPDATE public.projects 
                                        SET sessions_last_check_at=(now() at time zone 'utc'), first_recorded_session_at=u.first_recorded
                                        FROM (VALUES {",".join(u_values)}) AS u(project_id,first_recorded)
                                        WHERE projects.project_id=u.project_id;""", params)
                cur.execute(query)
        else:
            for r in rows:
                r["created_at"] = TimeUTC.datetime_to_timestamp(r["created_at"])
                r.pop("sessions_last_check_at")

        return helper.list_to_camel_case(rows)

# 功能描述：
# 获取指定项目的详细信息，并可选地包含最后一个会话的时间戳和GDPR信息。

# 参数：
# tenant_id: 租户ID。
# project_id: 要获取详细信息的项目ID。
# include_last_session: 布尔值，是否包含最后一个会话的时间戳。
# include_gdpr: 布尔值，是否包含GDPR信息。
# 返回值：
# dict: 包含项目详细信息的字典。
def get_project(tenant_id, project_id, include_last_session=False, include_gdpr=None):
    with pg_client.PostgresClient() as cur:
        extra_select = ""
        if include_last_session:
            extra_select += """,(SELECT max(ss.start_ts) 
                                 FROM public.sessions AS ss 
                                 WHERE ss.project_id = %(project_id)s) AS last_recorded_session_at"""
        if include_gdpr:
            extra_select += ",s.gdpr"
        query = cur.mogrify(f"""SELECT s.project_id,
                                       s.project_key,
                                       s.name,
                                       s.save_request_payloads,
                                       s.platform
                                       {extra_select}
                                FROM public.projects AS s
                                WHERE s.project_id =%(project_id)s
                                    AND s.deleted_at IS NULL
                                LIMIT 1;""",
                            {"project_id": project_id})
        cur.execute(query=query)
        row = cur.fetchone()
        return helper.dict_to_camel_case(row)

# 功能描述：
# 创建一个新项目，并在创建前检查项目名称是否已经存在。如果用户没有足够的权限，则会返回未经授权的错误。

# 参数：
# tenant_id: 租户ID。
# user_id: 用户ID，用于权限检查。
# data: schemas.CreateProjectSchema类型，包含项目创建所需数据。
# skip_authorization: 布尔值，是否跳过权限检查。
# 返回值：
# dict: 包含创建成功后的项目信息或错误信息的字典。
def create(tenant_id, user_id, data: schemas.CreateProjectSchema, skip_authorization=False):
    if __exists_by_name(name=data.name, exclude_id=None):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"name already exists.")
    if not skip_authorization:
        admin = users.get(user_id=user_id, tenant_id=tenant_id)
        if not admin["admin"] and not admin["superAdmin"]:
            return {"errors": ["unauthorized"]}
    return {"data": __create(tenant_id=tenant_id, data=data.model_dump())}

# 功能描述：
# 编辑指定项目的详细信息，并在编辑前检查项目名称是否已经存在。如果用户没有足够的权限，则会返回未经授权的错误。

# 参数：
# tenant_id: 租户ID。
# user_id: 用户ID，用于权限检查。
# project_id: 要编辑的项目ID。
# data: schemas.CreateProjectSchema类型，包含项目编辑所需数据。
# 返回值：
# dict: 包含编辑成功后的项目信息或错误信息的字典。
def edit(tenant_id, user_id, project_id, data: schemas.CreateProjectSchema):
    if __exists_by_name(name=data.name, exclude_id=project_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"name already exists.")
    admin = users.get(user_id=user_id, tenant_id=tenant_id)
    if not admin["admin"] and not admin["superAdmin"]:
        return {"errors": ["unauthorized"]}
    return {"data": __update(tenant_id=tenant_id, project_id=project_id,
                             changes=data.model_dump())}

# 功能描述：
# 删除指定的项目，并将其标记为非活跃状态。

# 参数：
# tenant_id: 租户ID。
# user_id: 用户ID，用于权限检查。
# project_id: 要删除的项目ID。
# 返回值：
# dict: 包含删除状态的信息。
def delete(tenant_id, user_id, project_id):
    admin = users.get(user_id=user_id, tenant_id=tenant_id)

    if not admin["admin"] and not admin["superAdmin"]:
        return {"errors": ["unauthorized"]}
    with pg_client.PostgresClient() as cur:
        query = cur.mogrify("""UPDATE public.projects 
                               SET deleted_at = timezone('utc'::text, now()),
                                   active = FALSE
                               WHERE project_id = %(project_id)s;""",
                            {"project_id": project_id})
        cur.execute(query=query)
    return {"data": {"state": "success"}}

# 功能描述：
# 获取指定项目的GDPR信息。

# 参数：
# project_id: 要获取GDPR信息的项目ID。
# 返回值：
# dict: 包含项目GDPR信息的字典。
def get_gdpr(project_id):
    with pg_client.PostgresClient() as cur:
        query = cur.mogrify("""SELECT gdpr
                               FROM public.projects AS s
                               WHERE s.project_id =%(project_id)s
                                    AND s.deleted_at IS NULL;""",
                            {"project_id": project_id})
        cur.execute(query=query)
        row = cur.fetchone()["gdpr"]
        row["projectId"] = project_id
        return row

# 功能描述：
# 编辑指定项目的GDPR信息，并将新信息合并到现有信息中。

# 参数：
# project_id: 要编辑GDPR信息的项目ID。
# gdpr: schemas.GdprSchema类型，包含新的GDPR信息。
# 返回值：
# dict: 包含更新后GDPR信息的字典或错误信息。
def edit_gdpr(project_id, gdpr: schemas.GdprSchema):
    with pg_client.PostgresClient() as cur:
        query = cur.mogrify("""UPDATE public.projects 
                               SET gdpr = gdpr|| %(gdpr)s::jsonb
                               WHERE project_id = %(project_id)s 
                                    AND deleted_at ISNULL
                               RETURNING gdpr;""",
                            {"project_id": project_id, "gdpr": json.dumps(gdpr.model_dump())})
        cur.execute(query=query)
        row = cur.fetchone()
        if not row:
            return {"errors": ["something went wrong"]}
        row = row["gdpr"]
        row["projectId"] = project_id
        return row

# 功能描述：
# 通过项目密钥获取项目的基本信息。

# 参数：
# project_key: 项目密钥。
# 返回值：
# dict: 包含项目基本信息的字典。
def get_by_project_key(project_key):
    with pg_client.PostgresClient() as cur:
        query = cur.mogrify("""SELECT project_id,
                                      project_key,
                                      platform,
                                      name
                               FROM public.projects
                               WHERE project_key =%(project_key)s 
                                    AND deleted_at ISNULL;""",
                            {"project_key": project_key})
        cur.execute(query=query)
        row = cur.fetchone()
        return helper.dict_to_camel_case(row)

# 功能描述：
# 获取指定项目的项目密钥。

# 参数：
# project_id: 要获取密钥的项目ID。
# 返回值：
# str: 项目的密钥字符串。
def get_project_key(project_id):
    with pg_client.PostgresClient() as cur:
        query = cur.mogrify("""SELECT project_key
                               FROM public.projects
                               WHERE project_id =%(project_id)s
                                    AND deleted_at ISNULL;""",
                            {"project_id": project_id})
        cur.execute(query=query)
        project = cur.fetchone()
        return project["project_key"] if project is not None else None

# 函数：get_capture_status
# 功能描述：
# 获取指定项目的捕获状态信息，包括采样率和是否捕获所有数据的标志。

# 参数：
# project_id: 要获取捕获状态的项目ID。
# 返回值：
# dict: 包含采样率和捕获状态的字典。
def get_capture_status(project_id):
    with pg_client.PostgresClient() as cur:
        query = cur.mogrify("""SELECT sample_rate AS rate, sample_rate=100 AS capture_all
                               FROM public.projects
                               WHERE project_id =%(project_id)s 
                                    AND deleted_at ISNULL;""",
                            {"project_id": project_id})
        cur.execute(query=query)
        return helper.dict_to_camel_case(cur.fetchone())

# 函数：update_capture_status
# 功能描述：
# 更新指定项目的捕获状态，包括采样率和是否捕获所有数据。

# 参数：
# project_id: 要更新捕获状态的项目ID。
# changes: schemas.SampleRateSchema类型，包含新的采样率和捕获状态信息。
# 返回值：
# schemas.SampleRateSchema: 更新后的捕获状态信息。
def update_capture_status(project_id, changes: schemas.SampleRateSchema):
    sample_rate = changes.rate
    if changes.capture_all:
        sample_rate = 100
    with pg_client.PostgresClient() as cur:
        query = cur.mogrify("""UPDATE public.projects
                               SET sample_rate= %(sample_rate)s
                               WHERE project_id =%(project_id)s
                                    AND deleted_at ISNULL;""",
                            {"project_id": project_id, "sample_rate": sample_rate})
        cur.execute(query=query)

    return changes

# 功能描述：
# 获取指定项目的条件捕获设置和所有条件列表。

# 参数：
# project_id: 要获取条件捕获设置的项目ID。
# 返回值：
# dict: 包含条件捕获设置和所有条件列表的字典。
def get_conditions(project_id):
    with pg_client.PostgresClient() as cur:
        query = cur.mogrify("""SELECT p.sample_rate AS rate, p.conditional_capture,
                                    COALESCE(
                                        array_agg(
                                            json_build_object(
                                                'condition_id', pc.condition_id,
                                                'capture_rate', pc.capture_rate,
                                                'name', pc.name,
                                                'filters', pc.filters
                                            )
                                        ) FILTER (WHERE pc.condition_id IS NOT NULL), 
                                        ARRAY[]::json[]
                                    ) AS conditions
                               FROM public.projects AS p
                               LEFT JOIN (
                                   SELECT * FROM public.projects_conditions
                                   WHERE project_id = %(project_id)s ORDER BY condition_id
                               ) AS pc ON p.project_id = pc.project_id
                               WHERE p.project_id = %(project_id)s 
                                     AND p.deleted_at IS NULL
                               GROUP BY p.sample_rate, p.conditional_capture;""",
                            {"project_id": project_id})
        cur.execute(query=query)
        row = cur.fetchone()
        row = helper.dict_to_camel_case(row)
        row["conditions"] = [schemas.ProjectConditions(**c) for c in row["conditions"]]

        return row

# 函数：validate_conditions
# 功能描述：
# 验证条件列表，检查条件名称是否为空或重复。

# 参数：
# conditions: List[schemas.ProjectConditions]类型，包含要验证的条件列表。
# 返回值：
# List[str]: 包含验证错误信息的字符串列表。
def validate_conditions(conditions: List[schemas.ProjectConditions]) -> List[str]:
    errors = []
    names = [condition.name for condition in conditions]

    # Check for empty strings
    if any(name.strip() == "" for name in names):
        errors.append("Condition names cannot be empty strings")

    # Check for duplicates
    name_counts = Counter(names)
    duplicates = [name for name, count in name_counts.items() if count > 1]
    if duplicates:
        errors.append(f"Duplicate condition names found: {duplicates}")

    return errors

# 函数：update_conditions
# 功能描述：
# 更新指定项目的条件捕获设置，并根据条件列表创建、更新或删除项目条件。

# 参数：
# project_id: 要更新条件捕获设置的项目ID。
# changes: schemas.ProjectSettings类型，包含新的条件捕获设置和条件列表。
# 返回值：
# dict: 更新后的项目条件捕获设置。
def update_conditions(project_id, changes: schemas.ProjectSettings):
    validation_errors = validate_conditions(changes.conditions)
    if validation_errors:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=validation_errors)

    conditions = []
    for condition in changes.conditions:
        conditions.append(condition.model_dump())

    with pg_client.PostgresClient() as cur:
        query = cur.mogrify("""UPDATE public.projects
                               SET
                                    sample_rate= %(sample_rate)s,
                                    conditional_capture = %(conditional_capture)s
                               WHERE project_id =%(project_id)s
                                    AND deleted_at IS NULL;""",
                            {
                                "project_id": project_id,
                                "sample_rate": changes.rate,
                                "conditional_capture": changes.conditional_capture
                            })
        cur.execute(query=query)

    return update_project_conditions(project_id, changes.conditions)

# 功能描述：
# 批量创建新的项目条件。

# 参数：
# project_id: 项目ID。
# conditions: 包含要创建的条件列表。
# 返回值：
# List[dict]: 新创建的项目条件的详细信息列表。
def create_project_conditions(project_id, conditions):
    rows = []

    # insert all conditions rows with single sql query
    if len(conditions) > 0:
        columns = (
            "project_id",
            "name",
            "capture_rate",
            "filters",
        )

        sql = f"""
            INSERT INTO projects_conditions
            (project_id, name, capture_rate, filters)
            VALUES {", ".join(["%s"] * len(conditions))}
            RETURNING condition_id, {", ".join(columns)}
        """

        with pg_client.PostgresClient() as cur:
            params = [
                (project_id, c.name, c.capture_rate, json.dumps([filter_.model_dump() for filter_ in c.filters]))
                for c in conditions]
            query = cur.mogrify(sql, params)
            cur.execute(query)
            rows = cur.fetchall()

    return rows

# 功能描述：
# 更新项目条件，批量更新指定条件列表中的信息。

# 参数：
# project_id: 项目ID。
# conditions: 要更新的条件列表。
# 返回值：
# None: 无返回值。
def update_project_condition(project_id, conditions):
    values = []
    params = {
        "project_id": project_id,
    }
    for i in range(len(conditions)):
        values.append(f"(%(condition_id_{i})s, %(name_{i})s, %(capture_rate_{i})s, %(filters_{i})s::jsonb)")
        params[f"condition_id_{i}"] = conditions[i].condition_id
        params[f"name_{i}"] = conditions[i].name
        params[f"capture_rate_{i}"] = conditions[i].capture_rate
        params[f"filters_{i}"] = json.dumps(conditions[i].filters)

    sql = f"""
        UPDATE projects_conditions
        SET name = c.name, capture_rate = c.capture_rate, filters = c.filters
        FROM (VALUES {','.join(values)}) AS c(condition_id, name, capture_rate, filters)
        WHERE c.condition_id = projects_conditions.condition_id AND project_id = %(project_id)s;
    """

    with pg_client.PostgresClient() as cur:
        query = cur.mogrify(sql, params)
        cur.execute(query)

# 功能描述：
# 删除指定的项目条件。

# 参数：
# project_id: 项目ID。
# ids: 要删除的条件ID列表。
# 返回值：
# None: 无返回值。
def delete_project_condition(project_id, ids):
    sql = """
        DELETE FROM projects_conditions
        WHERE condition_id IN %(ids)s
            AND project_id= %(project_id)s;
    """

    with pg_client.PostgresClient() as cur:
        query = cur.mogrify(sql, {"project_id": project_id, "ids": tuple(ids)})
        cur.execute(query)

# 功能描述：
# 根据传入的条件列表，批量创建、更新或删除项目条件。

# 参数：
# project_id: 项目ID。
# conditions: 条件列表。
# 返回值：
# dict: 更新后的项目条件捕获设置。
def update_project_conditions(project_id, conditions):
    if conditions is None:
        return

    existing = get_conditions(project_id)["conditions"]
    existing_ids = {c.condition_id for c in existing}

    to_be_updated = [c for c in conditions if c.condition_id in existing_ids]
    to_be_created = [c for c in conditions if c.condition_id not in existing_ids]
    to_be_deleted = existing_ids - {c.condition_id for c in conditions}

    if to_be_deleted:
        delete_project_condition(project_id, to_be_deleted)

    if to_be_created:
        create_project_conditions(project_id, to_be_created)

    if to_be_updated:
        print(to_be_updated)
        update_project_condition(project_id, to_be_updated)

    return get_conditions(project_id)

# 功能描述：
# 获取所有项目的ID列表。

# 参数：
# tenant_id: 租户ID。
# 返回值：
# List[int]: 项目ID的列表。
def get_projects_ids(tenant_id):
    with pg_client.PostgresClient() as cur:
        query = f"""SELECT s.project_id
                    FROM public.projects AS s
                    WHERE s.deleted_at IS NULL
                    ORDER BY s.project_id;"""
        cur.execute(query=query)
        rows = cur.fetchall()
    return [r["project_id"] for r in rows]
