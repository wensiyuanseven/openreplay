# 这段代码实现了对 Webhooks 的全面管理，包括创建、查询、更新、删除以及批量触发。
# 通过这些功能，系统可以与外部服务进行实时的事件驱动交互，适用于多种应用场景，如通知系统、第三方集成和自动化工作流。
import logging
from typing import Optional

import requests
from fastapi import HTTPException, status

import schemas
from chalicelib.utils import pg_client, helper
from chalicelib.utils.TimeUTC import TimeUTC

# 根据 webhook_id 获取单个 Webhook 的详细信息：

# 参数: webhook_id 是 Webhook 的唯一标识符。
# 功能:
# 查询数据库，获取指定 webhook_id 的 Webhook 记录。
# 如果找到了记录，将创建时间 (createdAt) 转换为时间戳格式，并返回该 Webhook 的详细信息。
# 返回值: 返回 Webhook 的详细信息（如果存在）。
def get_by_id(webhook_id):
    with pg_client.PostgresClient() as cur:
        cur.execute(
            cur.mogrify("""\
                    SELECT w.*
                    FROM public.webhooks AS w 
                    WHERE w.webhook_id =%(webhook_id)s AND deleted_at ISNULL;""",
                        {"webhook_id": webhook_id})
        )
        w = helper.dict_to_camel_case(cur.fetchone())
        if w:
            w["createdAt"] = TimeUTC.datetime_to_timestamp(w["createdAt"])
        return w

# 根据 webhook_id 和 webhook_type 获取 Webhook 的详细信息：

# 参数:
# tenant_id: 租户 ID。
# webhook_id: Webhook 的唯一标识符。
# webhook_type: Webhook 的类型，默认为 'webhook'。
# 功能:
# 查询数据库，根据 webhook_id 和 webhook_type 获取 Webhook 的详细信息。
# 如果找到记录，将创建时间 (createdAt) 转换为时间戳格式，并返回 Webhook 的详细信息。
# 返回值: 返回 Webhook 的详细信息（如果存在）。
def get_webhook(tenant_id, webhook_id, webhook_type='webhook'):
    with pg_client.PostgresClient() as cur:
        cur.execute(
            cur.mogrify("""SELECT w.*
                            FROM public.webhooks AS w 
                            WHERE w.webhook_id =%(webhook_id)s 
                                AND deleted_at ISNULL AND type=%(webhook_type)s;""",
                        {"webhook_id": webhook_id, "webhook_type": webhook_type})
        )
        w = helper.dict_to_camel_case(cur.fetchone())
        if w:
            w["createdAt"] = TimeUTC.datetime_to_timestamp(w["createdAt"])
        return w

# 根据 webhook_type 获取所有该类型的 Webhooks：

# 参数:
# tenant_id: 租户 ID。
# webhook_type: Webhook 的类型。
# 功能:
# 查询数据库，获取所有指定类型且未被删除的 Webhooks。
# 将结果中的创建时间转换为时间戳格式。
# 返回值: 返回指定类型的 Webhooks 列表。
def get_by_type(tenant_id, webhook_type):
    with pg_client.PostgresClient() as cur:
        cur.execute(
            cur.mogrify("""SELECT w.webhook_id,w.endpoint,w.auth_header,w.type,w.index,w.name,w.created_at
                            FROM public.webhooks AS w 
                            WHERE w.type =%(type)s AND deleted_at ISNULL;""",
                        {"type": webhook_type})
        )
        webhooks = helper.list_to_camel_case(cur.fetchall())
        for w in webhooks:
            w["createdAt"] = TimeUTC.datetime_to_timestamp(w["createdAt"])
        return webhooks

# 获取特定租户的所有 Webhooks：

# 参数:
# tenant_id: 租户 ID。
# replace_none: 是否将 None 值替换为空字符串，默认为 False。
# 功能:
# 查询数据库，获取所有未被删除的 Webhooks。
# 将结果中的创建时间转换为时间戳格式。
# 如果 replace_none 为 True，将所有 None 值替换为空字符串。
# 返回值: 返回租户的所有 Webhooks 列表。
def get_by_tenant(tenant_id, replace_none=False):
    with pg_client.PostgresClient() as cur:
        cur.execute("""SELECT w.*
                        FROM public.webhooks AS w 
                        WHERE deleted_at ISNULL;""")
        all = helper.list_to_camel_case(cur.fetchall())
        for w in all:
            w["createdAt"] = TimeUTC.datetime_to_timestamp(w["createdAt"])
        return all

# 更新指定 Webhook 的信息：
# 参数:
# tenant_id: 租户 ID。
# webhook_id: Webhook 的唯一标识符。
# changes: 包含需要更新字段的字典。
# replace_none: 是否将 None 值替换为空字符串，默认为 False。
# 功能:
# 根据 webhook_id 更新指定字段（如 name、index、authHeader、endpoint 等）。
# 更新后，返回更新后的 Webhook 信息。如果 Webhook 不存在，则抛出 HTTPException 异常。
# 返回值: 返回更新后的 Webhook 信息。
def update(tenant_id, webhook_id, changes, replace_none=False):
    allow_update = ["name", "index", "authHeader", "endpoint"]
    with pg_client.PostgresClient() as cur:
        sub_query = [f"{helper.key_to_snake_case(k)} = %({k})s" for k in changes.keys() if k in allow_update]
        cur.execute(
            cur.mogrify(f"""\
                    UPDATE public.webhooks
                    SET {','.join(sub_query)}
                    WHERE webhook_id =%(id)s AND deleted_at ISNULL
                    RETURNING *;""",
                        {"id": webhook_id, **changes})
        )
        w = helper.dict_to_camel_case(cur.fetchone())
        if w is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"webhook not found.")
        w["createdAt"] = TimeUTC.datetime_to_timestamp(w["createdAt"])
        if replace_none:
            for k in w.keys():
                if w[k] is None:
                    w[k] = ''
        return w

# 创建新的 Webhook：

# 参数:
# tenant_id: 租户 ID。
# endpoint: Webhook 的 URL 端点。
# auth_header: Webhook 的授权头，默认为 None。
# webhook_type: Webhook 的类型，默认为 'webhook'。
# name: Webhook 的名称。
# replace_none: 是否将 None 值替换为空字符串，默认为 False。
# 功能:
# 将新 Webhook 插入数据库，并返回插入后的 Webhook 信息。
# 如果 replace_none 为 True，将所有 None 值替换为空字符串。
# 返回值: 返回创建的 Webhook 信息。
def add(tenant_id, endpoint, auth_header=None, webhook_type='webhook', name="", replace_none=False):
    with pg_client.PostgresClient() as cur:
        query = cur.mogrify("""\
                    INSERT INTO public.webhooks(endpoint,auth_header,type,name)
                    VALUES (%(endpoint)s, %(auth_header)s, %(type)s,%(name)s)
                    RETURNING *;""",
                            {"endpoint": endpoint, "auth_header": auth_header,
                             "type": webhook_type, "name": name})
        cur.execute(
            query
        )
        w = helper.dict_to_camel_case(cur.fetchone())
        w["createdAt"] = TimeUTC.datetime_to_timestamp(w["createdAt"])
        if replace_none:
            for k in w.keys():
                if w[k] is None:
                    w[k] = ''
        return w

# 检查 Webhook 名称是否已存在：

# 参数:
# name: Webhook 的名称。
# exclude_id: 可选参数，指定要排除检查的 Webhook ID。
# webhook_type: Webhook 的类型，默认为 'webhook'。
# tenant_id: 租户 ID。
# 功能:
# 查询数据库，检查是否存在具有相同名称且未被删除的 Webhook。
# 如果指定了 exclude_id，则排除该 ID 的 Webhook。
# 返回值: 返回布尔值，表示名称是否已存在。
def exists_by_name(name: str, exclude_id: Optional[int], webhook_type: str = schemas.WebhookType.webhook,
                   tenant_id: Optional[int] = None) -> bool:
    with pg_client.PostgresClient() as cur:
        query = cur.mogrify(f"""SELECT EXISTS(SELECT 1 
                                FROM public.webhooks
                                WHERE name ILIKE %(name)s
                                    AND deleted_at ISNULL
                                    AND type=%(webhook_type)s
                                    {"AND webhook_id!=%(exclude_id)s" if exclude_id else ""}) AS exists;""",
                            {"name": name, "exclude_id": exclude_id, "webhook_type": webhook_type})
        cur.execute(query)
        row = cur.fetchone()
    return row["exists"]

# 添加或编辑 Webhook：

# 参数:
# tenant_id: 租户 ID。
# data: 包含 Webhook 信息的模式对象。
# replace_none: 是否将 None 值替换为空字符串，默认为 None。
# 功能:
# 如果 data.name 已存在且不属于当前编辑的 Webhook，则抛出 HTTPException 异常。
# 如果 data.webhook_id 存在，则更新 Webhook；否则创建新的 Webhook。
# 返回值: 返回创建或更新后的 Webhook 信息。
def add_edit(tenant_id, data: schemas.WebhookSchema, replace_none=None):
    if len(data.name) > 0 \
            and exists_by_name(name=data.name, exclude_id=data.webhook_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"name already exists.")
    if data.webhook_id is not None:
        return update(tenant_id=tenant_id, webhook_id=data.webhook_id,
                      changes={"endpoint": data.endpoint.unicode_string(),
                               "authHeader": data.auth_header,
                               "name": data.name},
                      replace_none=replace_none)
    else:
        return add(tenant_id=tenant_id,
                   endpoint=data.endpoint.unicode_string(),
                   auth_header=data.auth_header,
                   name=data.name,
                   replace_none=replace_none)

# 删除 Webhook（软删除）：

# 参数:
# tenant_id: 租户 ID。
# webhook_id: Webhook 的唯一标识符。
# 功能:
# 将指定 Webhook 的 deleted_at 字段设置为当前 UTC 时间，以表示该 Webhook 已被删除。
# 返回值: 返回删除状态。
def delete(tenant_id, webhook_id):
    with pg_client.PostgresClient() as cur:
        cur.execute(
            cur.mogrify("""\
                    UPDATE public.webhooks
                    SET deleted_at = (now() at time zone 'utc')
                    WHERE webhook_id =%(id)s AND deleted_at ISNULL
                    RETURNING *;""",
                        {"id": webhook_id})
        )
    return {"data": {"state": "success"}}

# 批量触发 Webhooks：
# 参数:
# data_list: 包含 Webhook 触发数据的列表。
# 功能:
# 根据 data_list 中的 destination 获取 Webhook，并调用 __trigger 函数发送请求。
# 如果 Webhook 未找到，则记录错误日志。
def trigger_batch(data_list):
    webhooks_map = {}
    for w in data_list:
        if w["destination"] not in webhooks_map:
            webhooks_map[w["destination"]] = get_by_id(webhook_id=w["destination"])
        if webhooks_map[w["destination"]] is None:
            logging.error(f"!!Error webhook not found: webhook_id={w['destination']}")
        else:
            __trigger(hook=webhooks_map[w["destination"]], data=w["data"])

# 触发单个 Webhook：
# 参数:
# hook: 包含 Webhook 信息的字典。
# data: 需要发送的数据。
# 功能:
# 通过 requests.post 向指定 Webhook 端点发送 POST 请求，并附带必要的授权头（如果存在）。
# 如果请求失败，记录错误日志；否则返回响应。
def __trigger(hook, data):
    if hook is not None and hook["type"] == 'webhook':
        headers = {}
        if hook["authHeader"] is not None and len(hook["authHeader"]) > 0:
            headers = {"Authorization": hook["authHeader"]}

        r = requests.post(url=hook["endpoint"], json=data, headers=headers)
        if r.status_code != 200:
            logging.error("=======> webhook：发生了一些错误:")
            logging.error(hook)
            logging.error(r.status_code)
            logging.error(r.text)
            return
        response = None
        try:
            response = r.json()
        except:
            try:
                response = r.text
            except:
                logging.info("no response found")
        return response
