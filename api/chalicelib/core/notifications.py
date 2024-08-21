# 这段代码实现了一个通知系统的相关功能，包括获取通知、获取未读通知的计数、标记通知为已读以及创建新通知。
import json

from chalicelib.utils import pg_client, helper
from chalicelib.utils.TimeUTC import TimeUTC


# 获取特定用户的所有通知：
# 参数:
# tenant_id: 租户 ID。
# user_id: 用户 ID。
# 功能:
# 从数据库中查询给定用户的通知，结果包括通知的详细信息以及用户是否已查看该通知的状态。
# 使用 SQL 查询 LEFT JOIN 合并通知表 (notifications) 和用户查看的通知表 (user_viewed_notifications)。
# 查询结果按创建时间倒序排序，并限制返回100条记录。
# 使用 helper.list_to_camel_case 将数据库字段名转换为驼峰式命名（CamelCase）。
# 将每条记录的 createdAt 字段从日期格式转换为时间戳格式。
# 返回值: 返回通知列表，包含通知的详细信息及其是否已被查看的状态。
def get_all(tenant_id, user_id):
    with pg_client.PostgresClient() as cur:
        cur.execute(
            # 从数据库中查询给定用户的通知，结果包括通知的详细信息以及用户是否已查看该通知的状态。
            cur.mogrify(
                """\
                    SELECT notifications.*,
                           user_viewed_notifications.notification_id NOTNULL AS viewed
                    FROM public.notifications
                             LEFT JOIN (SELECT notification_id
                                        FROM public.user_viewed_notifications
                                        WHERE user_viewed_notifications.user_id = %(user_id)s) AS user_viewed_notifications USING (notification_id)
                    WHERE notifications.user_id IS NULL OR notifications.user_id =%(user_id)s
                    ORDER BY created_at DESC
                    LIMIT 100;""",
                {"user_id": user_id},
            )
        )
        rows = helper.list_to_camel_case(cur.fetchall())
    for r in rows:
        r["createdAt"] = TimeUTC.datetime_to_timestamp(r["createdAt"])
    # 返回通知列表，包含通知的详细信息及其是否已被查看的状态
    return rows


# 获取特定用户未读通知的计数：

# 参数:
# tenant_id: 租户 ID。
# user_id: 用户 ID。
# 功能:
# 从数据库中查询给定用户的未读通知数量。
# 使用 SQL 查询 LEFT JOIN 合并通知表和用户查看的通知表，并过滤出用户未查看的通知。
# 查询返回未读通知的计数。
# 返回值: 返回一个包含未读通知数量的字典。
def get_all_count(tenant_id, user_id):
    with pg_client.PostgresClient() as cur:
        cur.execute(
            cur.mogrify(
                """\
                    SELECT COALESCE(COUNT(notifications.*),0) AS count
                    FROM public.notifications
                             LEFT JOIN (SELECT notification_id
                                        FROM public.user_viewed_notifications
                                        WHERE user_viewed_notifications.user_id = %(user_id)s) AS user_viewed_notifications USING (notification_id)
                    WHERE (notifications.user_id IS NULL OR notifications.user_id =%(user_id)s) AND user_viewed_notifications.notification_id IS NULL;""",
                {"user_id": user_id},
            )
        )
        row = cur.fetchone()
    return row


# 将指定通知标记为已读：
# 参数:
# user_id: 用户 ID。
# notification_ids: 要标记为已读的通知 ID 列表。
# tenant_id: 租户 ID。
# startTimestamp: 开始时间戳。
# endTimestamp: 结束时间戳
# 功能:
# 如果提供了 notification_ids，则将这些通知标记为已读。
# 如果未提供 notification_ids，则根据时间戳范围标记所有在该范围内的通知为已读。
# 使用批量插入 (executemany) 将多个记录插入 user_viewed_notifications 表中，确保记录不会重复插入（ON CONFLICT DO NOTHING）。
# 返回值: 返回布尔值 True 表示操作成功。
def view_notification(user_id, notification_ids=[], tenant_id=None, startTimestamp=None, endTimestamp=None):
    if len(notification_ids) == 0 and endTimestamp is None:
        return False
    if startTimestamp is None:
        startTimestamp = 0
    notification_ids = [(user_id, id) for id in notification_ids]
    with pg_client.PostgresClient() as cur:
        if len(notification_ids) > 0:
            cur.executemany("INSERT INTO public.user_viewed_notifications(user_id, notification_id) VALUES (%s,%s) ON CONFLICT DO NOTHING;", notification_ids)
        else:
            query = """INSERT INTO public.user_viewed_notifications(user_id, notification_id) 
                                SELECT %(user_id)s AS user_id, notification_id
                                FROM public.notifications
                                WHERE (user_id IS NULL OR user_id =%(user_id)s) 
                                    AND EXTRACT(EPOCH FROM created_at)*1000>=(%(startTimestamp)s) 
                                    AND EXTRACT(EPOCH FROM created_at)*1000<=(%(endTimestamp)s+1000) 
                                ON CONFLICT DO NOTHING;"""
            params = {"user_id": user_id, "startTimestamp": startTimestamp, "endTimestamp": endTimestamp}
            # print('-------------------')
            # print(cur.mogrify(query, params))
            cur.execute(cur.mogrify(query, params))
    return True


# 创建新通知：
# 参数:
# notifications: 通知的列表，每个通知都是一个字典，包含通知的详细信息。
# 功能:
# 将每个通知的数据准备好后插入到 notifications 表中。
# 使用 json.dumps() 将通知的 options 字段转换为 JSON 字符串。
# 使用 mogrify 准备 SQL 插入语句，然后执行插入操作。
# 将插入后的通知记录转换为驼峰式命名，并将 createdAt 字段转换为时间戳格式。
# 所有创建的通知默认标记为未查看（viewed = False）。
# 返回值: 返回包含新创建通知的列表，每个通知包括详细信息和已转换的时间戳。
def create(notifications):
    if len(notifications) == 0:
        return []
    with pg_client.PostgresClient() as cur:
        values = []
        for n in notifications:
            clone = dict(n)
            if "userId" not in clone:
                clone["userId"] = None
            if "options" not in clone:
                clone["options"] = "{}"
            else:
                clone["options"] = json.dumps(clone["options"])
            values.append(cur.mogrify("(%(userId)s, %(title)s, %(description)s, %(buttonText)s, %(buttonUrl)s, %(imageUrl)s,%(options)s)", clone).decode("UTF-8"))
        cur.execute(
            f"""INSERT INTO public.notifications(user_id, title, description, button_text, button_url, image_url, options) 
                VALUES {",".join(values)} RETURNING *;"""
        )
        rows = helper.list_to_camel_case(cur.fetchall())
        for r in rows:
            r["createdAt"] = TimeUTC.datetime_to_timestamp(r["createdAt"])
            r["viewed"] = False
    return rows
