# 该代码片段的主要功能是生成一组用于共享对象的预签名URL。它通过StorageClient从指定的存储桶中生成这些URL，这些URL具有一个小时的有效期。
# 这个功能通常用于在受限制的时间段内安全地共享存储在云端的文件或数据。
from chalicelib.core import projects
from chalicelib.utils.storage import StorageClient
from decouple import config

# 功能描述：
# 生成一组用于共享对象的预签名URL，这些URL可以在指定的时间内访问项目相关的数据文件。

# 参数：
# project_id: 项目ID，用于获取项目的密钥前缀。
# session_id: 会话ID，用于指定数据的存储路径。
# keys: 数据文件的键列表，每个键对应一个需要生成预签名URL的对象。
# 返回值：
# result: 一个列表，包含每个键对应的预签名URL，这些URL有效期为1小时。

def sign_keys(project_id, session_id, keys):
    result = []
    project_key = projects.get_project_key(project_id)
    for k in keys:
        result.append(StorageClient.get_presigned_url_for_sharing(bucket=config("iosBucket"), key=f"{project_key}/{session_id}/{k}", expires_in=60 * 60))
    return result
