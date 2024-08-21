from chalicelib.utils import pg_client, helper
from chalicelib.utils.storage import StorageClient
from decouple import config

# 该脚本主要用于与存储和数据库交互，以获取测试信号、检查测试信号的存在性以及生成 UX 测试的摄像头视频文件的预签名 URL。通过这些功能，开发者可以更方便地访问和管理用户测试数据。
# 功能描述:
# 从数据库中获取指定会话的所有测试信号，并将结果按时间顺序排序。

# 参数:

# session_id: 会话的唯一标识符。
# project_id: 项目的唯一标识符。
# 返回值:

# 返回一个包含测试信号的列表，列表中的每个元素都是一个字典，表示一个测试信号的详细信息。
def get_test_signals(session_id, project_id):
    with pg_client.PostgresClient() as cur:
        cur.execute(cur.mogrify("""\
            SELECT *
            FROM public.ut_tests_signals
                     LEFT JOIN public.ut_tests_tasks USING (task_id)
            WHERE session_id = %(session_id)s
            ORDER BY timestamp;""",
                                {"project_id": project_id, "session_id": session_id})
                    )
        rows = cur.fetchall()
    return helper.dict_to_camel_case(rows)

# 功能描述:
# 检查数据库中是否存在指定会话的测试信号。

# 参数:

# session_id: 会话的唯一标识符。
# project_id: 项目的唯一标识符。
# 返回值:

# 如果存在测试信号，返回 True，否则返回 False。
def has_test_signals(session_id, project_id):
    with pg_client.PostgresClient() as cur:
        cur.execute(cur.mogrify("""\
            SELECT EXISTS(SELECT 1 FROM public.ut_tests_signals
                            WHERE session_id = %(session_id)s) AS has;""",
                                {"project_id": project_id, "session_id": session_id})
                    )
        row = cur.fetchone()
    return row.get("has")

# 功能描述:
# 生成指定会话的 UX 测试摄像头视频文件的预签名 URL，用于共享和访问文件。

# 参数:

# session_id: 会话的唯一标识符。
# project_id: 项目的唯一标识符。
# check_existence: 是否在生成 URL 前检查文件是否存在，默认为 True。
# 返回值:

# 返回一个包含预签名 URL 的列表。如果文件不存在且 check_existence 为 True，则返回一个空列表。
def get_ux_webcam_signed_url(session_id, project_id, check_existence: bool = True):
    results = []
    bucket_name = "uxtesting-records" # config("sessions_bucket")
    k = f'{session_id}/ux_webcam_record.webm'
    if check_existence and not StorageClient.exists(bucket=bucket_name, key=k):
        return []
    results.append(StorageClient.get_presigned_url_for_sharing(
        bucket=bucket_name,
        expires_in=100000,
        key=k
    ))
    return results
