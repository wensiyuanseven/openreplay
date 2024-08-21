import schemas
from chalicelib.utils import helper
from chalicelib.utils import pg_client

# 这段代码提供了对标签（Tag）的创建、查询、更新和删除功能，适用于某个特定项目中的标签管理。它使用了 PostgreSQL 数据库，并通过 pg_client 与数据库进行交互。每个函数都封装了一个特定的数据库操作，并返回操作的结果。

# 功能描述:
# 在指定项目中创建一个新的标签，并返回新创建的标签的 ID。
# 参数:
# project_id: 项目ID，标识标签所属的项目。
# data: 一个包含标签信息的 schemas.TagCreate 对象，包括标签名称、选择器、是否忽略点击愤怒和是否忽略死点击等。
# 返回值:
# 返回新创建的标签的 ID。
def create_tag(project_id: int, data: schemas.TagCreate) -> int:
    query = """
    INSERT INTO public.tags (project_id, name, selector, ignore_click_rage, ignore_dead_click)
    VALUES (%(project_id)s, %(name)s, %(selector)s, %(ignore_click_rage)s, %(ignore_dead_click)s)
    RETURNING tag_id;
    """

    data = {
        'project_id': project_id,
        'name': data.name.strip(),
        'selector': data.selector,
        'ignore_click_rage': data.ignoreClickRage,
        'ignore_dead_click': data.ignoreDeadClick
    }
    
    with pg_client.PostgresClient() as cur:
        query = cur.mogrify(query, data)
        cur.execute(query)
        row = cur.fetchone()

    return row['tag_id']

# 功能描述:
# 列出指定项目中的所有标签（未被删除的标签），并返回一个包含标签信息的列表。

# 参数:

# project_id: 项目ID，用于筛选属于该项目的标签。
# 返回值:

# 返回一个标签信息的列表，列表中的每个元素都是一个字典，包含标签的详细信息。
def list_tags(project_id: int):
    query = """
    SELECT tag_id, name, selector, ignore_click_rage, ignore_dead_click
    FROM public.tags
    WHERE project_id = %(project_id)s
      AND deleted_at IS NULL
    """

    with pg_client.PostgresClient() as cur:
        query = cur.mogrify(query, {'project_id': project_id})
        cur.execute(query)
        rows = cur.fetchall()

    return helper.list_to_camel_case(rows)

# 功能描述:
# 更新指定标签的名称。

# 参数:

# project_id: 项目ID，标识标签所属的项目。
# tag_id: 标签ID，标识需要更新的标签。
# data: 一个包含更新信息的 schemas.TagUpdate 对象，主要包含标签的新名称。
# 返回值:

# 返回 True，表示更新成功。
def update_tag(project_id: int, tag_id: int, data: schemas.TagUpdate):
    query = """
    UPDATE public.tags
    SET name = %(name)s
    WHERE tag_id = %(tag_id)s AND project_id = %(project_id)s
    """

    with pg_client.PostgresClient() as cur:
        query = cur.mogrify(query, {'tag_id': tag_id, 'name': data.name, 'project_id': project_id})
        cur.execute(query)

    return True


# 功能描述:
# 删除指定的标签，实际上是将标签的 deleted_at 字段设置为当前 UTC 时间，以表示该标签已被删除。
# 参数:
# project_id: 项目ID，标识标签所属的项目。
# tag_id: 标签ID，标识需要删除的标签。
# 返回值:

# 返回 True，表示删除操作成功。
def delete_tag(project_id: int, tag_id: int):
    query = """
    UPDATE public.tags
    SET deleted_at = now() at time zone 'utc'
    WHERE tag_id = %(tag_id)s AND project_id = %(project_id)s
    """

    with pg_client.PostgresClient() as cur:
        query = cur.mogrify(query, {'tag_id': tag_id, 'project_id': project_id})
        cur.execute(query)

    return True
