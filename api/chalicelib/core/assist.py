# Assist协助
# 这段代码主要提供了与“Assist”服务进行交互的多种功能，
# 包括获取实时会话、生成代理令牌、检查会话存在性、以及处理与 EFS（Elastic File System）相关的文件路径和权限等操作。
# “Assist”服务通常是指一个提供实时支持、监控、或协作功能的服务或平台。
# 具体到这段代码中，“Assist”服务似乎是一个用于实时监控或帮助用户会话的后台服务，可能与应用程序中的实时用户交互或会话跟踪有关
# 检查文件是否可读。
from os import access, R_OK  # access 是 os 模块中的一个函数，用于检查指定路径的文件或目录是否具有特定的访问权限 它的常见用法是验证文件是否可读、可写、或可执行。
from os.path import exists as path_exists, getsize

import jwt
import requests
from decouple import config
from fastapi import HTTPException, status

import schemas
from chalicelib.core import projects
from chalicelib.utils.TimeUTC import TimeUTC

# ASSIST_KEY 和 ASSIST_URL: 这些常量用于存储 Assist 服务的访问密钥和 URL。
ASSIST_KEY = config("ASSIST_KEY")
ASSIST_URL = config("ASSIST_URL") % ASSIST_KEY
# SESSION_PROJECTION_COLS: 定义了从数据库中查询会话信息时选择的列。
SESSION_PROJECTION_COLS = """s.project_id,
                           s.session_id::text AS session_id,
                           s.user_uuid,
                           s.user_id,
                           s.user_agent,
                           s.user_os,
                           s.user_browser,
                           s.user_device,
                           s.user_device_type,
                           s.user_country,
                           s.start_ts,
                           s.user_anonymous_id,
                           s.platform
                           """

# 功能: 获取指定用户在项目中的实时会话。
# 参数:
# project_id: 项目 ID。
# user_id: 用户 ID。
# 返回值: 返回与用户相关的实时会话数据。
def get_live_sessions_ws_user_id(project_id, user_id):
    data = {"filter": {"userId": user_id} if user_id else {}}
    return __get_live_sessions_ws(project_id=project_id, data=data)


# 功能: 根据测试 ID 获取实时会话。
# 参数:
# project_id: 项目 ID。
# test_id: 测试 ID。
# 返回值: 返回与测试 ID 相关的实时会话数据。
def get_live_sessions_ws_test_id(project_id, test_id):
    data = {"filter": {"uxtId": test_id, "operator": "is"}}
    return __get_live_sessions_ws(project_id=project_id, data=data)


# 功能: 根据指定的过滤条件和分页信息获取实时会话。
# 参数:
# project_id: 项目 ID。
# body: 包含过滤条件和分页信息的搜索请求体。
# 返回值: 返回符合条件的实时会话数据。
def get_live_sessions_ws(project_id, body: schemas.LiveSessionsSearchPayloadSchema):
    data = {"filter": {}, "pagination": {"limit": body.limit, "page": body.page}, "sort": {"key": body.sort, "order": body.order}}
    for f in body.filters:
        if f.type == schemas.LiveFilterType.metadata:
            data["filter"][f.source] = {"values": f.value, "operator": f.operator}

        else:
            data["filter"][f.type] = {"values": f.value, "operator": f.operator}
    return __get_live_sessions_ws(project_id=project_id, data=data)


# 功能: 实际执行获取实时会话的 HTTP 请求，并处理响应。
# 参数:
# project_id: 项目 ID。
# data: 请求体数据，包括过滤条件和分页信息。
# 返回值: 返回包含实时会话的 JSON 数据或空数据。
def __get_live_sessions_ws(project_id, data):
    project_key = projects.get_project_key(project_id)
    try:
        results = requests.post(ASSIST_URL + config("assist") + f"/{project_key}", json=data, timeout=config("assistTimeout", cast=int, default=5))
        if results.status_code != 200:
            print(f"!! issue with the peer-server code:{results.status_code} for __get_live_sessions_ws")
            print(results.text)
            return {"total": 0, "sessions": []}
        live_peers = results.json().get("data", [])
    except requests.exceptions.Timeout:
        print("!! Timeout getting Assist response")
        live_peers = {"total": 0, "sessions": []}
    except Exception as e:
        print("!! Issue getting Live-Assist response")
        print(str(e))
        print("expected JSON, received:")
        try:
            print(results.text)
        except:
            print("couldn't get response")
        live_peers = {"total": 0, "sessions": []}
    _live_peers = live_peers
    if "sessions" in live_peers:
        _live_peers = live_peers["sessions"]
    for s in _live_peers:
        s["live"] = True
        s["projectId"] = project_id
        if "projectID" in s:
            s.pop("projectID")
    return live_peers


# 功能: 生成一个 JWT（JSON Web Token），用于在实时会话中验证代理。
# 参数:
# project_id: 项目 ID。
# project_key: 项目密钥。
# session_id: 会话 ID。
# 返回值: 返回生成的 JWT。
def __get_agent_token(project_id, project_key, session_id):
    iat = TimeUTC.now()
    # 将有效载荷编码为 JWT
    return jwt.encode(payload={"projectKey": project_key, "projectId": project_id, "sessionId": session_id, "iat": iat // 1000, "exp": iat // 1000 + config("ASSIST_JWT_EXPIRATION", cast=int) + TimeUTC.get_utc_offset() // 1000, "iss": config("JWT_ISSUER"), "aud": f"openreplay:agent"}, key=config("ASSIST_JWT_SECRET"), algorithm=config("jwt_algorithm"))


# 功能: 根据项目 ID 和会话 ID 获取特定的实时会话信息。
# 参数:
# project_id: 项目 ID。
# session_id: 会话 ID。
# 返回值: 返回会话数据及其代理验证令牌。
def get_live_session_by_id(project_id, session_id):
    project_key = projects.get_project_key(project_id)
    try:
        results = requests.get(ASSIST_URL + config("assist") + f"/{project_key}/{session_id}", timeout=config("assistTimeout", cast=int, default=5))
        if results.status_code != 200:
            print(f"!! issue with the peer-server code:{results.status_code} for get_live_session_by_id")
            print(results.text)
            return None
        results = results.json().get("data")
        if results is None:
            return None
        results["live"] = True
        results["agentToken"] = __get_agent_token(project_id=project_id, project_key=project_key, session_id=session_id)
    except requests.exceptions.Timeout:
        print("!! Timeout getting Assist response")
        return None
    except Exception as e:
        print("!! Issue getting Assist response")
        print(str(e))
        print("expected JSON, received:")
        try:
            print(results.text)
        except:
            print("couldn't get response")
        return None
    return results


# 功能: 检查特定会话是否仍然处于活动状态。
# 参数:
# project_id: 项目 ID。
# session_id: 会话 ID。
# project_key: 项目密钥（可选）。
# 返回值: 如果会话仍然处于活动状态，返回 True，否则返回 False。
def is_live(project_id, session_id, project_key=None):
    if project_key is None:
        project_key = projects.get_project_key(project_id)
    try:
        results = requests.get(ASSIST_URL + config("assistList") + f"/{project_key}/{session_id}", timeout=config("assistTimeout", cast=int, default=5))
        if results.status_code != 200:
            print(f"!! issue with the peer-server code:{results.status_code} for is_live")
            print(results.text)
            return False
        results = results.json().get("data")
    except requests.exceptions.Timeout:
        print("!! Timeout getting Assist response")
        return False
    except Exception as e:
        print("!! Issue getting Assist response")
        print(str(e))
        print("expected JSON, received:")
        try:
            print(results.text)
        except:
            print("couldn't get response")
        return False
    return str(session_id) == results


# 功能: 为指定项目的查询提供自动补全功能。
# 参数:
# project_id: 项目 ID。
# q: 查询字符串。
# key: 可选键，用于进一步过滤查询。
# 返回值: 返回包含自动补全结果的数据。
def autocomplete(project_id, q: str, key: str = None):
    project_key = projects.get_project_key(project_id)
    params = {"q": q}
    if key:
        params["key"] = key
    try:
        results = requests.get(ASSIST_URL + config("assistList") + f"/{project_key}/autocomplete", params=params, timeout=config("assistTimeout", cast=int, default=5))
        if results.status_code != 200:
            print(f"!! issue with the peer-server code:{results.status_code} for autocomplete")
            print(results.text)
            return {"errors": [f"Something went wrong wile calling assist:{results.text}"]}
        results = results.json().get("data", [])
    except requests.exceptions.Timeout:
        print("!! Timeout getting Assist response")
        return {"errors": ["Assist request timeout"]}
    except Exception as e:
        print("!! Issue getting Assist response")
        print(str(e))
        print("expected JSON, received:")
        try:
            print(results.text)
        except:
            print("couldn't get response")
        return {"errors": ["Something went wrong wile calling assist"]}
    for r in results:
        r["type"] = __change_keys(r["type"])
    return {"data": results}


# 功能: 获取 ICE 服务器的配置，用于 WebRTC 连接。
# 返回值: 返回 ICE 服务器的配置，如果配置不存在则返回 None
def get_ice_servers():
    return config("iceServers") if config("iceServers", default=None) is not None and len(config("iceServers")) > 0 else None


# 功能: 获取 EFS（Elastic File System）的路径，并检查路径的存在性和可读性。
# 返回值: 返回 EFS 的路径，如果路径不存在或不可读则抛出 HTTP 异常。
def __get_efs_path():
    efs_path = config("FS_DIR")
    if not path_exists(efs_path):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"EFS not found in path: {efs_path}")

    if not access(efs_path, R_OK):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"EFS found under: {efs_path}; but it is not readable, please check permissions")
    return efs_path


# 功能: 根据项目 ID 和会话 ID 获取移动端会话数据文件的路径模式。
# 参数:
# project_id: 项目 ID。
# session_id: 会话 ID。
# 返回值: 返回移动端会话数据文件的路径。
def __get_mob_path(project_id, session_id):
    params = {"projectId": project_id, "sessionId": session_id}
    return config("EFS_SESSION_MOB_PATTERN", default="%(sessionId)s") % params


# 功能: 根据项目 ID 和会话 ID 获取原始移动端会话数据文件。
# 参数:
# project_id: 项目 ID。
# session_id: 会话 ID。
# 返回值: 如果文件存在且可读且不超过最大大小，则返回文件路径；否则返回 None。
def get_raw_mob_by_id(project_id, session_id):
    efs_path = __get_efs_path()
    path_to_file = efs_path + "/" + __get_mob_path(project_id=project_id, session_id=session_id)
    if path_exists(path_to_file):
        if not access(path_to_file, R_OK):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Replay file found under: {efs_path};" + " but it is not readable, please check permissions")
        # getsize return size in bytes, UNPROCESSED_MAX_SIZE is in Kb
        if (getsize(path_to_file) / 1000) >= config("UNPROCESSED_MAX_SIZE", cast=int, default=200 * 1000):
            raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Replay file too large")
        return path_to_file

    return None


# 功能: 根据项目 ID 和会话 ID 获取 DevTools 数据文件的路径模式。
# 参数:
# project_id: 项目 ID。
# session_id: 会话 ID。
# 返回值: 返回 DevTools 数据文件的路径。
def __get_devtools_path(project_id, session_id):
    params = {"projectId": project_id, "sessionId": session_id}
    return config("EFS_DEVTOOLS_MOB_PATTERN", default="%(sessionId)s") % params


# 功能: 根据项目 ID 和会话 ID 获取原始 DevTools 数据文件。
# 参数:
# project_id: 项目 ID。
# session_id: 会话 ID。
# 返回值: 如果文件存在且可读，则返回文件路径；否则返回 None。
def get_raw_devtools_by_id(project_id, session_id):
    efs_path = __get_efs_path()
    path_to_file = efs_path + "/" + __get_devtools_path(project_id=project_id, session_id=session_id)
    if path_exists(path_to_file):
        if not access(path_to_file, R_OK):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Devtools file found under: {efs_path};" " but it is not readable, please check permissions")

        return path_to_file

    return None


# 功能: 检查给定项目 ID 和会话 ID 的会话是否存在。
# 参数:
# project_id: 项目 ID。
# session_id: 会话 ID。
# 返回值: 如果会话存在返回 True，否则返回 False。
def session_exists(project_id, session_id):
    project_key = projects.get_project_key(project_id)
    try:
        results = requests.get(ASSIST_URL + config("assist") + f"/{project_key}/{session_id}", timeout=config("assistTimeout", cast=int, default=5))
        if results.status_code != 200:
            print(f"!! issue with the peer-server code:{results.status_code} for session_exists")
            print(results.text)
            return None
        results = results.json().get("data")
        if results is None:
            return False
        return True
    except requests.exceptions.Timeout:
        print("!! Timeout getting Assist response")
        return False
    except Exception as e:
        print("!! Issue getting Assist response")
        print(str(e))
        print("expected JSON, received:")
        try:
            print(results.text)
        except:
            print("couldn't get response")
        return False


# 功能: 将特定键值转换为适用于 API 的格式。
# 参数:
# key: 需要转换的键值。
# 返回值: 返回转换后的键值，如果键不匹配则返回原始键。
def __change_keys(key):
    return {
        "PAGETITLE": schemas.LiveFilterType.page_title.value,
        "ACTIVE": "active",
        "LIVE": "live",
        "SESSIONID": schemas.LiveFilterType.session_id.value,
        "METADATA": schemas.LiveFilterType.metadata.value,
        "USERID": schemas.LiveFilterType.user_id.value,
        "USERUUID": schemas.LiveFilterType.user_UUID.value,
        "PROJECTKEY": "projectKey",
        "REVID": schemas.LiveFilterType.rev_id.value,
        "TIMESTAMP": "timestamp",
        "TRACKERVERSION": schemas.LiveFilterType.tracker_version.value,
        "ISSNIPPET": "isSnippet",
        "USEROS": schemas.LiveFilterType.user_os.value,
        "USERBROWSER": schemas.LiveFilterType.user_browser.value,
        "USERBROWSERVERSION": schemas.LiveFilterType.user_browser_version.value,
        "USERDEVICE": schemas.LiveFilterType.user_device.value,
        "USERDEVICETYPE": schemas.LiveFilterType.user_device_type.value,
        "USERCOUNTRY": schemas.LiveFilterType.user_country.value,
        "PROJECTID": "projectId",
    }.get(key.upper(), key)
