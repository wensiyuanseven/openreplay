# 该代码片段实现了一个与 GitHub API v3 进行交互的客户端库。它包含多个静态方法用于格式化 GitHub 的各种数据类型（如时间戳、标签、评论、问题、用户等），
# 并提供了一个 githubV3Request 类，用于通过 GET 和 POST 请求与 GitHub API 交互。
# 整个模块还包含用于解析响应头中的链接信息的函数，以及日志记录功能，用于记录与 GitHub API 交互的过程和错误信息。
import logging
from datetime import datetime

import requests
from fastapi import HTTPException, status

logger = logging.getLogger(__name__)


#  定义用于格式化 GitHub 数据的工具类
class github_formatters:
    # 将 ISO 格式的时间戳转换为毫秒级的 Unix 时间戳
    # 参数：
    # - ts: 字符串类型，GitHub 提供的 ISO 时间戳
    # 返回值：
    # - 返回整数类型的 Unix 时间戳（毫秒）
    @staticmethod
    def get_timestamp(ts):
        ts = ts[:-1]
        pattern = "%Y-%m-%dT%H:%M:%S"
        creation = datetime.strptime(ts, pattern)
        return int(creation.timestamp() * 1000)

    # 格式化标签信息
    # 参数：
    # - label: 字典类型，包含 GitHub 标签信息
    # 返回值：
    # - 返回格式化后的标签信息字典
    @staticmethod
    def label(label):
        return {"id": label["id"], "name": label["name"], "description": label["description"], "color": label["color"]}

    # 格式化评论信息
    # 参数：
    # - comment: 字典类型，包含 GitHub 评论信息
    # 返回值：
    # - 返回格式化后的评论信息字典
    @staticmethod
    def comment(comment):
        return {"id": str(comment["id"]), "message": comment["body"], "author": str(github_formatters.user(comment["user"])["id"]), "createdAt": github_formatters.get_timestamp(comment["created_at"])}

    # 格式化问题信息（Issue）
    # 参数：
    # - issue: 字典类型，包含 GitHub Issue 信息
    # 返回值：
    # - 返回格式化后的 Issue 信息字典
    @staticmethod
    def issue(issue):
        labels = [github_formatters.label(l) for l in issue["labels"]]
        result = {
            "id": str(issue["number"]),
            "creator": str(github_formatters.user(issue["user"])["id"]),
            "assignees": [str(github_formatters.user(a)["id"]) for a in issue["assignees"]],
            "title": issue["title"],
            "description": issue["body"],
            "status": issue["state"],
            "createdAt": github_formatters.get_timestamp(issue["created_at"]),
            "closed": issue["closed_at"] is not None,
            "commentsCount": issue["comments"],
            "issueType": [str(l["id"]) for l in labels if l["name"].lower() != "openreplay"],
            "labels": [l["name"] for l in labels],
        }
        return result

    # 格式化用户信息
    # 参数：
    # - user: 字典类型，包含 GitHub 用户信息
    # 返回值：
    # - 返回格式化后的用户信息字典
    @staticmethod
    def user(user):
        if not user:
            return None
        result = {"id": user["id"], "name": user["login"], "avatarUrls": {"24x24": user["avatar_url"]}, "email": ""}
        return result

    # 格式化团队信息
    # 参数：
    # - team: 对象类型，包含团队信息
    # 返回值：
    # - 返回格式化后的团队信息字典
    @staticmethod
    def team_to_dict(team):
        if not team:
            return None

        result = {"id": team.id, "name": team.name, "members_count": team.members_count}
        return result

    # 格式化仓库信息
    # 参数：
    # - repo: 字典类型，包含 GitHub 仓库信息
    # 返回值：
    # - 返回格式化后的仓库信息字典
    @staticmethod
    def repo(repo):
        if not repo:
            return None
        return {"id": str(repo["id"]), "name": repo["name"], "description": repo["description"], "creator": str(repo["owner"]["id"])}

    # 格式化组织信息
    # 参数：
    # - org: 字典类型，包含 GitHub 组织信息
    # 返回值：
    # - 返回格式化后的组织信息字典
    @staticmethod
    def organization(org):
        if not org:
            return None
        return {"id": org["id"], "name": org["login"], "description": org["description"], "avatarUrls": {"24x42": org["avatar_url"]}}


# 解析响应头中的链接信息，用于处理分页请求
# 参数：
# - response: requests.Response 对象，包含 GitHub API 的响应
# 返回值：
# - links: 字典类型，包含各个分页链接的映射关系
def get_response_links(response):
    links = {}
    if "Link" in response.headers:
        link_headers = response.headers["Link"].split(", ")
        for link_header in link_headers:
            (url, rel) = link_header.split("; ")
            url = url[1:-1]
            rel = rel[5:-1]
            links[rel] = url
    return links


#  定义与 GitHub API v3 进行交互的请求类
class githubV3Request:
    __base = "https://api.github.com"

    # 初始化 githubV3Request 类的实例
    # 参数：
    # - token: 字符串类型，用于身份验证的 GitHub API 令牌
    def __init__(self, token):
        self.__token = token

    # 获取请求头部信息，用于认证和指定 API 版本
    # 返回值：
    # - 字典类型的请求头部信息
    def __get_request_header(self):
        return {"Accept": "application/vnd.github.v3+json", "Authorization": f"token {self.__token}"}

    # 发送 GET 请求以获取数据，并处理分页
    # 参数：
    # - url: 字符串类型，GitHub API 的相对路径
    # - params: 字典类型，可选的查询参数
    # 返回值：
    # - 返回请求的数据，类型为列表或字典
    def get(self, url, params={}):
        results = []
        params = {"per_page": 100, **params}
        pages = {"next": f"{self.__base}{url}", "last": ""}
        while len(pages.keys()) > 0 and pages["next"] != pages["last"]:
            response = requests.get(pages["next"], headers=self.__get_request_header(), params=params)
            pages = get_response_links(response)
            result = response.json()
            if response.status_code != 200:
                logger.warning(f"=>GITHUB Exception")
                logger.error(result)
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"GITHUB: {result['message']}")
            if isinstance(result, dict):
                return result
            results += result
        return results

    # 发送 POST 请求以提交数据
    # 参数：
    # - url: 字符串类型，GitHub API 的相对路径
    # - body: 字典类型，请求的 JSON 数据
    # 返回值：
    # - 返回请求的数据，类型为字典
    def post(self, url, body):
        response = requests.post(f"{self.__base}{url}", headers=self.__get_request_header(), json=body)
        return response.json()
