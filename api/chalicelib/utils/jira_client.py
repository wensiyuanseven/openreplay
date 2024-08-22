# 该代码实现了一个用于与 JIRA API 进行交互的 JiraManager 类，提供了一系列方法来管理 JIRA 项目、问题（issue）、评论、用户等功能。通过该类，你可以获取项目列表、单个项目、问题列表、单个问题，创建问题、关闭问题、分配问题、添加评论、获取评论、获取可分配用户及获取问题类型等。
# 代码中使用了 JIRA API 库进行大部分操作，并且在出现错误时通过重试机制和 HTTP 异常处理来应对网络或 API 请求的失败。
import logging
import time
from datetime import datetime

import requests
from fastapi import HTTPException, status
from jira import JIRA
from jira.exceptions import JIRAError
from requests.auth import HTTPBasicAuth

logger = logging.getLogger(__name__)
# 定义需要获取的 JIRA 问题字段
fields = "id, summary, description, creator, reporter, created, assignee, status, updated, comment, issuetype, labels"


# 定义与 JIRA API 进行交互的管理类
class JiraManager:
    retries = 0  # 重试次数初始化为 0

    # 初始化 JiraManager 类的实例
    # 参数：
    # - url: 字符串类型，JIRA 服务器的 URL
    # - username: 字符串类型，用于登录 JIRA 的用户名
    # - password: 字符串类型，用于登录 JIRA 的密码
    # - project_id: 可选的字符串类型，JIRA 项目的 ID
    def __init__(self, url, username, password, project_id=None):
        self._config = {"JIRA_PROJECT_ID": project_id, "JIRA_URL": url, "JIRA_USERNAME": username, "JIRA_PASSWORD": password}
        try:
            self._jira = JIRA(url, basic_auth=(username, password), logging=True, max_retries=0, timeout=3)
        except Exception as e:
            logger.warning("!!! JIRA AUTH ERROR")
            logger.error(e)
            raise e

    # 设置 JIRA 项目的 ID
    # 参数：
    # - project_id: 字符串类型，JIRA 项目的 ID
    def set_jira_project_id(self, project_id):
        self._config["JIRA_PROJECT_ID"] = project_id

    # 获取 JIRA 项目列表
    # 返回值：
    # - projects_dict_list: 包含项目信息的字典列表
    def get_projects(self):
        try:
            projects = self._jira.projects()
        except JIRAError as e:
            self.retries -= 1
            if (e.status_code // 100) == 4 and self.retries > 0:
                time.sleep(1)
                return self.get_projects()
            logger.error(f"=>JIRA Exception {e.text}")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"JIRA: {e.text}")
        projects_dict_list = []
        for project in projects:
            projects_dict_list.append(self.__parser_project_info(project))

        return projects_dict_list

    # 获取单个 JIRA 项目的详细信息
    # 返回值：
    # - 项目信息的字典
    def get_project(self):
        try:
            project = self._jira.project(self._config["JIRA_PROJECT_ID"])
        except JIRAError as e:
            self.retries -= 1
            if (e.status_code // 100) == 4 and self.retries > 0:
                time.sleep(1)
                return self.get_project()
            logger.error(f"=>Exception {e.text}")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"JIRA: {e.text}")
        return self.__parser_project_info(project)

    # 获取 JIRA 问题列表
    # 参数：
    # - sql: 字符串类型的 JQL 查询条件
    # - offset: 整型，分页起始位置，默认为 0
    # 返回值：
    # - issues_dict_list: 包含问题信息的字典列表
    def get_issues(self, sql: str, offset: int = 0):
        jql = "project = " + self._config["JIRA_PROJECT_ID"] + ((" AND " + sql) if sql is not None and len(sql) > 0 else "") + " ORDER BY createdDate DESC"

        try:
            issues = self._jira.search_issues(jql, maxResults=1000, startAt=offset, fields=fields)
        except JIRAError as e:
            self.retries -= 1
            if (e.status_code // 100) == 4 and self.retries > 0:
                time.sleep(1)
                return self.get_issues(sql, offset)
            logger.error(f"=>Exception {e.text}")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"JIRA: {e.text}")

        issue_dict_list = []
        for issue in issues:
            issue_dict_list.append(self.__parser_issue_info(issue, include_comments=False))

        # return {"total": issues.total, "issues": issue_dict_list}
        return issue_dict_list

    # 获取单个 JIRA 问题的详细信息
    # 参数：
    # - issue_id: 字符串类型，问题的 ID
    # 返回值：
    # - 问题的详细信息字典
    def get_issue(self, issue_id: str):
        try:
            # issue = self._jira.issue(issue_id)
            issue = self._jira.issue(issue_id, fields=fields)
        except JIRAError as e:
            self.retries -= 1
            if (e.status_code // 100) == 4 and self.retries > 0:
                time.sleep(1)
                return self.get_issue(issue_id)
            logger.error(f"=>Exception {e.text}")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"JIRA: {e.text}")
        return self.__parser_issue_info(issue)

    # 使用 JIRA API v3 获取单个问题的详细信息
    # 参数：
    # - issue_id: 字符串类型，问题的 ID
    # 返回值：
    # - 问题的详细信息字典
    def get_issue_v3(self, issue_id: str):
        try:
            url = f"{self._config['JIRA_URL']}/rest/api/3/issue/{issue_id}?fields={fields}"
            auth = HTTPBasicAuth(self._config["JIRA_USERNAME"], self._config["JIRA_PASSWORD"])
            issue = requests.get(url, headers={"Accept": "application/json"}, auth=auth)
        except Exception as e:
            self.retries -= 1
            if self.retries > 0:
                time.sleep(1)
                return self.get_issue_v3(issue_id)
            logger.error(f"=>Exception {e}")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"JIRA: get issue error")
        return self.__parser_issue_info(issue.json())

    # 创建新的 JIRA 问题
    # 参数：
    # - issue_dict: 字典类型，包含问题的详细信息
    # 返回值：
    # - 创建成功后的问题信息字典
    def create_issue(self, issue_dict):
        issue_dict["project"] = {"id": self._config["JIRA_PROJECT_ID"]}
        try:
            issue = self._jira.create_issue(fields=issue_dict)
            return self.__parser_issue_info(issue)
        except JIRAError as e:
            self.retries -= 1
            if (e.status_code // 100) == 4 and self.retries > 0:
                time.sleep(1)
                return self.create_issue(issue_dict)
            logger.error(f"=>Exception {e.text}")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"JIRA: {e.text}")

    # 关闭指定的 JIRA 问题
    # 参数：
    # - issue: 问题的对象或 ID
    def close_issue(self, issue):
        try:
            # jira.transition_issue(issue, '5', assignee={'name': 'pm_user'}, resolution={'id': '3'})
            self._jira.transition_issue(issue, "Close")
        except JIRAError as e:
            self.retries -= 1
            if (e.status_code // 100) == 4 and self.retries > 0:
                time.sleep(1)
                return self.close_issue(issue)
            logger.error(f"=>Exception {e.text}")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"JIRA: {e.text}")

    # 为指定问题分配用户
    # 参数：
    # - issue_id: 字符串类型，问题的 ID
    # - account_id: 字符串类型，用户的账号 ID
    # 返回值：
    # - 布尔值，表示操作是否成功
    def assign_issue(self, issue_id, account_id) -> bool:
        try:
            return self._jira.assign_issue(issue_id, account_id)
        except JIRAError as e:
            self.retries -= 1
            if (e.status_code // 100) == 4 and self.retries > 0:
                time.sleep(1)
                return self.assign_issue(issue_id, account_id)
            logger.error(f"=>Exception {e.text}")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"JIRA: {e.text}")

    # 为指定问题添加评论
    # 参数：
    # - issue_id: 字符串类型，问题的 ID
    # - comment: 字符串类型，评论内容
    # 返回值：
    # - 添加成功后的评论信息字典
    def add_comment(self, issue_id: str, comment: str):
        try:
            comment = self._jira.add_comment(issue_id, comment)
        except JIRAError as e:
            self.retries -= 1
            if (e.status_code // 100) == 4 and self.retries > 0:
                time.sleep(1)
                return self.add_comment(issue_id, comment)
            logger.error(f"=>Exception {e.text}")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"JIRA: {e.text}")
        return self.__parser_comment_info(comment)

    # 使用 JIRA API v3 为指定问题添加评论
    # 参数：
    # - issue_id: 字符串类型，问题的 ID
    # - comment: 字符串类型，评论内容
    # 返回值：
    # - 添加成功后的评论信息字典
    def add_comment_v3(self, issue_id: str, comment: str):
        try:
            url = f"{self._config['JIRA_URL']}/rest/api/3/issue/{issue_id}/comment"
            auth = HTTPBasicAuth(self._config["JIRA_USERNAME"], self._config["JIRA_PASSWORD"])
            comment_response = requests.post(url, headers={"Accept": "application/json"}, auth=auth, json={"body": {"type": "doc", "version": 1, "content": [{"type": "paragraph", "content": [{"text": comment, "type": "text"}]}]}})
        except Exception as e:
            self.retries -= 1
            if self.retries > 0:
                time.sleep(1)
                return self.add_comment_v3(issue_id, comment)
            logger.error(f"=>Exception {e}")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"JIRA: comment error")
        return self.__parser_comment_info(comment_response.json())

    # 获取指定问题的评论列表
    # 参数：
    # - issueKey: 字符串类型，问题的 ID
    # 返回值：
    # - 包含评论信息的字典列表
    def get_comments(self, issueKey):
        try:
            comments = self._jira.comments(issueKey)
            results = []
            for c in comments:
                results.append(self.__parser_comment_info(c.raw))
            return results
        except JIRAError as e:
            self.retries -= 1
            if (e.status_code // 100) == 4 and self.retries > 0:
                time.sleep(1)
                return self.get_comments(issueKey)
            logger.error(f"=>Exception {e.text}")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"JIRA: {e.text}")

    # 获取 JIRA 的元数据信息，如问题类型和可分配的用户列表
    # 返回值：
    # - 包含问题类型和用户列表的字典
    def get_meta(self):
        meta = {}
        meta["issueTypes"] = self.get_issue_types()
        meta["users"] = self.get_assignable_users()
        return meta

    # 获取可分配的用户列表
    # 返回值：
    # - 包含用户信息的字典列表
    def get_assignable_users(self):
        try:
            users = self._jira.search_assignable_users_for_issues(project=self._config["JIRA_PROJECT_ID"], query="*")
        except JIRAError as e:
            self.retries -= 1
            if (e.status_code // 100) == 4 and self.retries > 0:
                time.sleep(1)
                return self.get_assignable_users()
            logger.error(f"=>Exception {e.text}")
            if e.status_code == 401:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="JIRA: 401 Unauthorized")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"JIRA: {e.text}")
        users_dict = []
        for user in users:
            users_dict.append({"name": user.displayName, "email": user.emailAddress, "id": user.accountId, "avatarUrls": user.raw["avatarUrls"]})

        return users_dict

    # 获取问题类型列表
    # 返回值：
    # - 包含问题类型信息的字典列表
    def get_issue_types(self):
        try:
            types = self._jira.project(self._config["JIRA_PROJECT_ID"]).issueTypes
        except JIRAError as e:
            self.retries -= 1
            if (e.status_code // 100) == 4 and self.retries > 0:
                time.sleep(1)
                return self.get_issue_types()
            logger.error(f"=>Exception {e.text}")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"JIRA: {e.text}")
        types_dict = []
        for type in types:
            if not type.subtask and not type.name.lower() == "epic":
                types_dict.append({"id": type.id, "name": type.name, "iconUrl": type.iconUrl, "description": type.description})
        return types_dict

    # 解析评论信息
    # 参数：
    # - comment: 字典类型或对象类型，包含评论的详细信息
    # 返回值：
    # - 格式化后的评论信息字典
    def __parser_comment_info(self, comment):
        if not isinstance(comment, dict):
            comment = comment.raw

        pattern = "%Y-%m-%dT%H:%M:%S.%f%z"
        creation = datetime.strptime(comment["created"], pattern)
        # update = datetime.strptime(comment['updated'], pattern)

        return {
            "id": comment["id"],
            "author": comment["author"]["accountId"],
            "message": comment["body"],
            # 'created': comment['created'],
            "createdAt": int((creation - creation.utcoffset()).timestamp() * 1000),
            # 'updated': comment['updated'],
            # 'updatedAt': int((update - update.utcoffset()).timestamp() * 1000)
        }

    # 判断问题状态是否为关闭状态
    # 参数：
    # - status: 字符串类型，表示问题的状态
    # 返回值：
    # - 布尔值，表示问题是否为关闭状态
    @staticmethod
    def __get_closed_status(status):
        return status.lower() == "done" or status.lower() == "close" or status.lower() == "closed" or status.lower() == "finish" or status.lower() == "finished"

    # 解析问题信息
    # 参数：
    # - issue: 字典类型或对象类型，包含问题的详细信息
    # - include_comments: 布尔类型，表示是否包括评论信息
    # 返回值：
    # - 格式化后的问题信息字典
    def __parser_issue_info(self, issue, include_comments=True):
        results_dict = {}
        if not isinstance(issue, dict):
            raw_info = issue.raw
        else:
            raw_info = issue

        fields = raw_info["fields"]
        results_dict["id"] = raw_info["id"]
        results_dict["key"] = raw_info["key"]
        # results_dict["ticketNumber"] = raw_info["key"]
        results_dict["title"] = fields["summary"]
        results_dict["description"] = fields["description"]
        results_dict["issueType"] = [fields["issuetype"]["id"]]

        # results_dict["assignee"] = None
        # results_dict["reporter"] = None

        if isinstance(fields["assignee"], dict):
            results_dict["assignees"] = [fields["assignee"]["accountId"]]
        # if isinstance(fields["reporter"], dict):
        #     results_dict["reporter"] = fields["reporter"]["accountId"]
        if isinstance(fields["creator"], dict):
            results_dict["creator"] = fields["creator"]["accountId"]

        if "comment" in fields:
            if include_comments:
                comments_dict = []
                for comment in fields["comment"]["comments"]:
                    comments_dict.append(self.__parser_comment_info(comment))

                results_dict["comments"] = comments_dict
            results_dict["commentsCount"] = fields["comment"]["total"]

        results_dict["status"] = fields["status"]["name"]
        results_dict["createdAt"] = fields["created"]
        # results_dict["updated"] = fields["updated"]
        results_dict["labels"] = fields["labels"]
        results_dict["closed"] = self.__get_closed_status(fields["status"]["name"])

        return results_dict

    # 解析项目信息
    # 参数：
    # - project: 对象类型，包含项目信息
    # 返回值：
    # - 格式化后的项目信息字典
    @staticmethod
    def __parser_project_info(project):
        results_dict = {}
        raw_info = project.raw
        results_dict["id"] = raw_info["id"]
        results_dict["name"] = raw_info["name"]
        results_dict["avatarUrls"] = raw_info["avatarUrls"]
        results_dict["description"] = raw_info["description"] if "description" in raw_info else ""

        return results_dict
