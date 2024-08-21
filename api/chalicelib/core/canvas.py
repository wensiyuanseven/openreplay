# 这段代码的主要功能是为指定的会话（session_id）获取与画布记录相关的预签名URL列表，这些URL可以用于共享录制的画布内容。
# 代码使用了数据库查询来获取画布录制的信息，并通过调用存储客户端生成这些录制文件的预签名URL。
from chalicelib.utils import pg_client, helper
from chalicelib.utils.storage import StorageClient
from decouple import config

# 作用
# 该函数用于为给定的会话ID (session_id) 和项目ID (project_id)，生成包含录制画布文件的预签名URL列表。这些URL用于访问存储在指定存储桶中的录制文件。

# 参数
# session_id: 会话的唯一标识符，用于在数据库中查找相关的画布录制信息。
# project_id: 项目的唯一标识符，用于关联会话的项目。
# 返回值
# 返回一个列表 (urls)，其中包含生成的预签名URL。这些URL允许访问存储在云存储中的画布录制文件。

# 函数内部流程
# 数据库查询:
# 使用 pg_client.PostgresClient() 建立数据库连接。
# 执行 SQL 查询，获取与指定 session_id 相关的所有画布录制数据。
# 结果按时间戳排序，以确保按录制的顺序处理。
# 生成预签名URL:
# 遍历数据库查询结果中的每条记录。
# 生成包含 sessionId、projectId 和 recordingId 的参数字典。
# 使用不同的文件名模式（新模式和旧模式）生成对应的存储键（key）。
# 使用 StorageClient.get_presigned_url_for_sharing() 方法为每个键生成预签名URL，设置URL的过期时间为 PRESIGNED_URL_EXPIRATION 配置中的值（默认为900秒）。
# 将生成的URL添加到 urls 列表中。
# 返回结果:
# 最后，返回包含所有生成的预签名URL的列表。

def get_canvas_presigned_urls(session_id, project_id):
    with pg_client.PostgresClient() as cur:
        cur.execute(cur.mogrify("""\
            SELECT *
            FROM events.canvas_recordings
            WHERE session_id = %(session_id)s
            ORDER BY timestamp;""",
                                {"project_id": project_id, "session_id": session_id})
                    )
        rows = cur.fetchall()
        urls = []
        for i in range(len(rows)):
            params = {
                "sessionId": session_id,
                "projectId": project_id,
                "recordingId": rows[i]["recording_id"]
            }
            oldKey = "%(sessionId)s/%(recordingId)s.mp4" % params
            key = config("CANVAS_PATTERN", default="%(sessionId)s/%(recordingId)s.tar.zst") % params
            urls.append(StorageClient.get_presigned_url_for_sharing(
                bucket=config("CANVAS_BUCKET", default=config("sessions_bucket")),
                expires_in=config("PRESIGNED_URL_EXPIRATION", cast=int, default=900),
                key=key
            ))
            urls.append(StorageClient.get_presigned_url_for_sharing(
                bucket=config("CANVAS_BUCKET", default=config("sessions_bucket")),
                expires_in=config("PRESIGNED_URL_EXPIRATION", cast=int, default=900),
                key=oldKey
            ))
        return urls
