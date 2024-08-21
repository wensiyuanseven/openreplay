from decouple import config

from chalicelib.utils.storage import StorageClient

# 这段代码主要用于处理与开发工具相关的文件（通常是用于调试的会话数据）的存储、获取和删除操作。具体包括生成文件的键名、获取预签名URL以访问这些文件，以及标记文件以供删除。
# 功能描述：
# 生成与开发工具相关的存储键名列表。

# 参数：
# project_id: 项目ID。
# session_id: 会话ID。
# 返回值：
# List[str]: 返回与会话ID和项目ID相关的键名列表。
def __get_devtools_keys(project_id, session_id):
    params = {
        "sessionId": session_id,
        "projectId": project_id
    }
    return [
        config("DEVTOOLS_MOB_PATTERN", default="%(sessionId)sdevtools") % params
    ]

# 功能描述：
# 获取与指定会话相关的开发工具文件的预签名URL列表。
# 参数：
# session_id: 会话ID。
# project_id: 项目ID。
# check_existence: （可选）是否检查文件是否存在，默认为 True。
# 返回值：
# List[str]: 返回包含可访问文件的预签名URL的列表。
def get_urls(session_id, project_id, check_existence: bool = True):
    results = []
    for k in __get_devtools_keys(project_id=project_id, session_id=session_id):
        if check_existence and not StorageClient.exists(bucket=config("sessions_bucket"), key=k):
            continue
        results.append(StorageClient.get_presigned_url_for_sharing(
            bucket=config("sessions_bucket"),
            expires_in=config("PRESIGNED_URL_EXPIRATION", cast=int, default=900),
            key=k
        ))
    return results

# 功能描述：
# 标记与指定会话相关的开发工具文件以供删除。
# 参数：
# project_id: 项目ID。
# session_ids: 包含多个会话ID的列表。
# 返回值：
# None: 无返回值，该函数执行删除标记操作。
def delete_mobs(project_id, session_ids):
    for session_id in session_ids:
        for k in __get_devtools_keys(project_id=project_id, session_id=session_id):
            StorageClient.tag_for_deletion(bucket=config("sessions_bucket"), key=k)
