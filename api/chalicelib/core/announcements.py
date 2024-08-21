# announcements 翻译：公告
# 获取公告页面: 当用户访问公告页面时，可以调用 get_all 函数来获取所有公告及其查看状态。
# 用户查看公告: 用户查看公告时，调用 view 函数更新用户的 lastAnnouncementView 时间，以便系统能正确标记哪些公告已被查看。
from chalicelib.utils import pg_client
from chalicelib.utils import helper
from decouple import config
from chalicelib.utils.TimeUTC import TimeUTC


# 功能：
# 获取所有公告: 这个函数用于获取指定用户的所有公告数据，并标记用户是否已查看每个公告。
# 数据库查询:
# 查询所有公告信息，并获取用户上次查看公告的时间（lastAnnouncementView）。
# 使用 mogrify 方法将参数化查询与实际的 SQL 语句结合起来，确保查询的安全性。
# 查询结果中，计算每条公告的 viewed 字段，标识用户是否在公告创建后查看过它。
# 数据处理:
# 使用 helper.list_to_camel_case 将查询结果转换为驼峰命名法格式。
# 将公告的 createdAt 时间戳格式化为 UTC 时间戳。
# 如果公告包含图片链接，则为图片链接加上前缀 URL。
# 返回值：
# 返回一个包含所有公告的列表，其中每个公告对象包含详细信息和用户是否已查看该公告的状态。
def get_all(user_id):
    with pg_client.PostgresClient() as cur:
        query = cur.mogrify(
            """
        SELECT a.*, u.last >= (EXTRACT(EPOCH FROM a.created_at)*1000) AS viewed
        FROM public.announcements AS a,
             (SELECT COALESCE(CAST(data ->> 'lastAnnouncementView' AS bigint), 0)
              FROM public.users
              WHERE user_id = %(userId)s
              LIMIT 1) AS u(last)
        ORDER BY a.created_at DESC;""",
            {"userId": user_id},
        )
        cur.execute(query)
        announcements = helper.list_to_camel_case(cur.fetchall())
        for a in announcements:
            a["createdAt"] = TimeUTC.datetime_to_timestamp(a["createdAt"])
            if a["imageUrl"] is not None and len(a["imageUrl"]) > 0:
                a["imageUrl"] = config("announcement_url") + a["imageUrl"]
        return announcements


# 功能：
# 更新用户公告查看时间: 该函数用于更新指定用户上次查看公告的时间。
# 数据库更新:
# 将当前 UTC 时间戳更新到用户的 data 字段中的 lastAnnouncementView 属性。
# 使用 PostgreSQL 的 JSONB 操作符 || 合并新的时间戳值。
# 返回值：
# 返回布尔值 True，表示操作成功。
def view(user_id):
    with pg_client.PostgresClient() as cur:
        query = cur.mogrify(
            """
        UPDATE public.users
        SET data=data ||
                 ('{"lastAnnouncementView":' ||
                  (EXTRACT(EPOCH FROM timezone('utc'::text, now())) * 1000)::bigint - 20 * 000 ||
                  '}')::jsonb
        WHERE user_id = %(userId)s;""",
            {"userId": user_id},
        )
        cur.execute(query)
    return True
