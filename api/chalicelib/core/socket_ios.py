import requests
from decouple import config
from chalicelib.core import projects

# 这段代码定义了一个函数 start_replay，用于启动一个移动端会话的回放。该函数向一个指定的中间件服务发送HTTP POST请求，传递项目ID、会话ID、设备信息等数据，并根据响应返回回放的相关信息或错误消息。
# 功能描述:
# 该函数用于通过HTTP POST请求向配置的iOS中间件服务发起回放请求。它将会话信息和设备信息发送给中间件，并返回中间件的响应结果。

# 参数:

# project_id: 项目的ID，用于标识请求中的项目。
# session_id: 会话的ID，指定要回放的具体会话。
# device: 设备信息，表示回放时使用的设备类型。
# os_version: 操作系统版本，表示设备运行的操作系统版本。
# mob_url: 移动端URL，表示回放时加载的页面URL。
# 返回值:


# 成功时返回中间件的响应结果，包含回放的相关信息和URL。
# 失败时返回错误信息。
def start_replay(project_id, session_id, device, os_version, mob_url):
    r = requests.post(config("IOS_MIDDLEWARE") + "/replay", json={"projectId": project_id, "projectKey": projects.get_project_key(project_id), "session_id": session_id, "device": device, "osVersion": os_version, "mobUrl": mob_url})
    if r.status_code != 200:
        print("failed replay middleware")
        print("status code: %s" % r.status_code)
        print(r.text)
        return r.text
    result = r.json()
    result["url"] = config("IOS_MIDDLEWARE")
    return result
