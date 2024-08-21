# 这段代码实现了与“已保存搜索”功能相关的CRUD操作（创建、读取、更新和删除）。该功能允许用户在项目中创建、更新、删除和获取已保存的搜索记录。搜索记录包括搜索名称、搜索条件、是否公开等信息。这些操作通过与 PostgreSQL 数据库交互来实现。
import json

import schemas
from chalicelib.utils import helper, pg_client
from chalicelib.utils.TimeUTC import TimeUTC

# 功能描述：
# 创建一个新的已保存搜索记录，并将其插入到数据库中。

# 参数：
# project_id: 项目的唯一标识符，用于标识搜索记录所属的项目。
# user_id: 用户的唯一标识符，用于标识哪个用户创建了搜索记录。
# data: schemas.SavedSearchSchema 类型，包含保存搜索的名称、筛选条件等信息。
# 返回值：
# dict: 返回包含新创建的搜索记录数据的字典。
def create(project_id, user_id, data: schemas.SavedSearchSchema):
    with pg_client.PostgresClient() as cur:
        data = data.model_dump()
        data["filter"] = json.dumps(data["filter"])
        query = cur.mogrify("""\
            INSERT INTO public.searches (project_id, user_id, name, filter,is_public) 
            VALUES (%(project_id)s, %(user_id)s, %(name)s, %(filter)s::jsonb,%(is_public)s)
            RETURNING *;""", {"user_id": user_id, "project_id": project_id, **data})
        cur.execute(
            query
        )
        r = cur.fetchone()
        r["created_at"] = TimeUTC.datetime_to_timestamp(r["created_at"])
        r["filter"] = helper.old_search_payload_to_flat(r["filter"])
        r = helper.dict_to_camel_case(r)
        return {"data": r}

# 功能描述：
# 更新指定的已保存搜索记录。

# 参数：
# search_id: 要更新的搜索记录的唯一标识符。
# project_id: 项目的唯一标识符。
# user_id: 用户的唯一标识符。
# data: schemas.SavedSearchSchema 类型，包含更新后的搜索记录信息。
# 返回值：
# dict: 返回更新后的搜索记录数据的字典。
def update(search_id, project_id, user_id, data: schemas.SavedSearchSchema):
    with pg_client.PostgresClient() as cur:
        data = data.model_dump()
        data["filter"] = json.dumps(data["filter"])
        query = cur.mogrify(f"""\
            UPDATE public.searches 
            SET name = %(name)s,
                filter = %(filter)s,
                is_public = %(is_public)s
            WHERE search_id=%(search_id)s 
                AND project_id= %(project_id)s
                AND (user_id = %(user_id)s OR is_public)
            RETURNING *;""", {"search_id": search_id, "project_id": project_id, "user_id": user_id, **data})
        cur.execute(
            query
        )
        r = cur.fetchone()
        r["created_at"] = TimeUTC.datetime_to_timestamp(r["created_at"])
        r["filter"] = helper.old_search_payload_to_flat(r["filter"])
        r = helper.dict_to_camel_case(r)
        return r

# 功能描述：
# 获取指定项目中所有的已保存搜索记录，可以选择是否包含详细信息。

# 参数：
# project_id: 项目的唯一标识符。
# user_id: 用户的唯一标识符。
# details: 布尔值，决定是否获取搜索记录的详细信息（如筛选条件）。
# 返回值：
# List[dict]: 返回包含搜索记录的字典列表。
def get_all(project_id, user_id, details=False):
    with pg_client.PostgresClient() as cur:
        cur.execute(
            cur.mogrify(
                f"""\
                SELECT search_id, project_id, user_id, name, created_at, deleted_at, is_public
                    {",filter" if details else ""}
                FROM public.searches
                WHERE project_id = %(project_id)s
                  AND deleted_at IS NULL
                  AND (user_id = %(user_id)s OR is_public);""",
                {"project_id": project_id, "user_id": user_id}
            )
        )

        rows = cur.fetchall()
        rows = helper.list_to_camel_case(rows)
        for row in rows:
            row["createdAt"] = TimeUTC.datetime_to_timestamp(row["createdAt"])
            if details:
                if isinstance(row["filter"], list) and len(row["filter"]) == 0:
                    row["filter"] = {}
                row["filter"] = helper.old_search_payload_to_flat(row["filter"])
    return rows

# 功能描述：
# 删除指定的已保存搜索记录，将其标记为已删除。

# 参数：
# project_id: 项目的唯一标识符。
# search_id: 要删除的搜索记录的唯一标识符。
# user_id: 用户的唯一标识符。
# 返回值：
# dict: 返回一个状态字典，指示删除操作的结果。
def delete(project_id, search_id, user_id):
    with pg_client.PostgresClient() as cur:
        cur.execute(
            cur.mogrify("""\
            UPDATE public.searches 
            SET deleted_at = timezone('utc'::text, now()) 
            WHERE project_id = %(project_id)s
              AND search_id = %(search_id)s
              AND (user_id = %(user_id)s OR is_public);""",
                        {"search_id": search_id, "project_id": project_id, "user_id": user_id})
        )

    return {"state": "success"}

# 功能描述：
# 获取指定的已保存搜索记录的详细信息。

# 参数：
# search_id: 搜索记录的唯一标识符。
# project_id: 项目的唯一标识符。
# user_id: 用户的唯一标识符。
# 返回值：
# dict: 返回搜索记录的详细信息。如果记录不存在，返回 None。
def get(search_id, project_id, user_id):
    with pg_client.PostgresClient() as cur:
        cur.execute(
            cur.mogrify(
                """SELECT
                      *
                    FROM public.searches
                    WHERE project_id = %(project_id)s
                      AND deleted_at IS NULL
                      AND search_id = %(search_id)s
                      AND (user_id = %(user_id)s OR is_public);""",
                {"search_id": search_id, "project_id": project_id, "user_id": user_id}
            )
        )

        f = helper.dict_to_camel_case(cur.fetchone())
    if f is None:
        return None

    f["createdAt"] = TimeUTC.datetime_to_timestamp(f["createdAt"])
    f["filter"] = helper.old_search_payload_to_flat(f["filter"])
    return f



# 关键点
# 数据转换: 在插入和更新操作中，filter 字段被转换为 JSON 格式字符串存储，而在获取时被转换回结构化数据。
# 软删除: 搜索记录的删除操作是软删除，即通过设置 deleted_at 字段来标记记录已被删除，而不是物理删除。
# 数据权限: 通过 user_id 和 is_public 来控制用户对搜索记录的访问权限。
# 这段代码通过提供灵活的查询和更新机制，使用户能够方便地管理和操作已保存的搜索记录。如果有进一步的问题或需要更多帮助，请随时告知我！
