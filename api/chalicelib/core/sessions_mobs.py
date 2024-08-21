# 这段代码的主要功能是处理与会话相关的移动设备数据文件（如会话视频、日志等）的获取和删除操作。它使用了 StorageClient 进行云存储的交互，通过生成预签名URL的方式共享存储在云端的资源。
from decouple import config

from chalicelib.utils.storage import StorageClient

# 功能描述:
# 生成并返回一个会话的相关资源键。键的格式由配置文件中的模式字符串决定。

# 参数:

# project_id: int - 项目ID。
# session_id: int - 会话ID。
# 返回值:


# List[str] - 包含资源键的列表。
def __get_mob_keys(project_id, session_id):
    params = {"sessionId": session_id, "projectId": project_id}
    return [config("SESSION_MOB_PATTERN_S", default="%(sessionId)s") % params, config("SESSION_MOB_PATTERN_E", default="%(sessionId)se") % params]


# 功能描述:
# 生成并返回与会话相关的移动设备视频资源键。

# 参数:

# project_id: int - 项目ID。
# session_id: int - 会话ID。
# 返回值:


# List[str] - 包含视频资源键的列表。
def __get_mobile_video_keys(project_id, session_id):
    params = {"sessionId": session_id, "projectId": project_id}
    return [
        config("SESSION_IOS_VIDEO_PATTERN") % params,
    ]


def __get_mob_keys_deprecated(session_id):
    return [str(session_id), str(session_id) + "e"]


# 功能描述:
# 获取某个会话的第一个移动设备资源的预签名URL。

# 参数:

# project_id: int - 项目ID。
# session_id: int - 会话ID。
# check_existence: bool - 是否检查资源是否存在。
# 返回值:


# str 或 None - 资源的预签名URL，如果资源不存在则返回 None。
def get_first_url(project_id, session_id, check_existence: bool = True):
    k = __get_mob_keys(project_id=project_id, session_id=session_id)[0]
    if check_existence and not StorageClient.exists(bucket=config("sessions_bucket"), key=k):
        return None
    return StorageClient.get_presigned_url_for_sharing(bucket=config("sessions_bucket"), expires_in=config("PRESIGNED_URL_EXPIRATION", cast=int, default=900), key=k)


# 功能描述:
# 获取某个会话的所有相关资源的预签名URL。

# 参数:

# project_id: int - 项目ID（仅 get_urls 使用）。
# session_id: int - 会话ID。
# check_existence: bool - 是否检查资源是否存在。
# 返回值:

# List[str] - 包含预签名URL的列表。


def get_urls(project_id, session_id, check_existence: bool = True):
    results = []
    for k in __get_mob_keys(project_id=project_id, session_id=session_id):
        if check_existence and not StorageClient.exists(bucket=config("sessions_bucket"), key=k):
            continue
        results.append(StorageClient.get_presigned_url_for_sharing(bucket=config("sessions_bucket"), expires_in=config("PRESIGNED_URL_EXPIRATION", cast=int, default=900), key=k))
    return results


def get_urls_depercated(session_id, check_existence: bool = True):
    results = []
    for k in __get_mob_keys_deprecated(session_id=session_id):
        if check_existence and not StorageClient.exists(bucket=config("sessions_bucket"), key=k):
            continue
        results.append(StorageClient.get_presigned_url_for_sharing(bucket=config("sessions_bucket"), expires_in=100000, key=k))
    return results


# 作用: 获取移动设备会话的视频资源的预签名URL。
def get_mobile_videos(session_id, project_id, check_existence=False):
    results = []
    for k in __get_mobile_video_keys(project_id=project_id, session_id=session_id):
        if check_existence and not StorageClient.exists(bucket=config("IOS_VIDEO_BUCKET"), key=k):
            continue
        results.append(StorageClient.get_presigned_url_for_sharing(bucket=config("IOS_VIDEO_BUCKET"), expires_in=config("PRESIGNED_URL_EXPIRATION", cast=int, default=900), key=k))
    return results


# 作用: 标记某些会话的移动设备资源以便在云存储中删除。
# 功能描述:
# 标记某些会话的移动设备资源以便在云存储中删除。

# 参数:

# project_id: int - 项目ID。
# session_ids: List[int] - 会话ID列表。
# 返回值:


# 无返回值。
def delete_mobs(project_id, session_ids):
    for session_id in session_ids:
        for k in __get_mob_keys(project_id=project_id, session_id=session_id) + __get_mob_keys_deprecated(session_id=session_id):
            StorageClient.tag_for_deletion(bucket=config("sessions_bucket"), key=k)
