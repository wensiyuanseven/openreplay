# 这段代码定义了一个名为 JIRACloudIntegrationIssue 的类，该类继承自 BaseIntegrationIssue，用于处理与 JIRA Cloud 集成相关的问题管理。
# 通过与 JIRA Cloud API 交互，该类实现了创建新任务、获取任务详情、评论任务、获取元数据和获取用户项目等功能。
from chalicelib.utils import jira_client
from chalicelib.core.integration_base_issue import BaseIntegrationIssue


# JIRACloudIntegrationIssue 类继承自 BaseIntegrationIssue，处理 JIRA Cloud 的问题管理。
class JIRACloudIntegrationIssue(BaseIntegrationIssue):
    # 初始化函数，设置 JIRA API 客户端和调用父类的构造函数。
    # 参数：
    # - token: 用于验证 JIRA API 的令牌。
    # - username: 用于访问 JIRA 的用户名。
    # - url: JIRA 实例的基础 URL。
    def __init__(self, token, username, url):
        self.username = username
        self.url = url
        self._client = jira_client.JiraManager(self.url, self.username, token, None)
        super(JIRACloudIntegrationIssue, self).__init__("JIRA", token)

    # 函数：create_new_assignment
    # 功能：在指定的 JIRA 项目中创建一个新的任务（Issue）。
    # 参数：
    # - integration_project_id: JIRA 项目ID。
    # - title: 任务标题。
    # - description: 任务描述。
    # - assignee: 分配的用户ID。
    # - issue_type: 问题类型ID。
    # 返回值：
    # - 返回创建的任务（Issue）的详细信息。
    def create_new_assignment(self, integration_project_id, title, description, assignee, issue_type):
        self._client.set_jira_project_id(integration_project_id)
        data = {"summary": title, "description": description, "issuetype": {"id": issue_type}, "assignee": {"id": assignee}, "labels": ["OpenReplay"]}
        return self._client.create_issue(data)

    # 函数：get_by_ids
    # 功能：根据保存的任务ID列表获取任务的详细信息。
    # 参数：
    # - saved_issues: 包含任务ID和集成项目ID的字典列表。
    # 返回值：
    # - 返回包含任务详细信息的字典。
    def get_by_ids(self, saved_issues):
        projects_map = {}
        for i in saved_issues:
            if i["integrationProjectId"] not in projects_map.keys():
                projects_map[i["integrationProjectId"]] = []
            projects_map[i["integrationProjectId"]].append(i["id"])

        results = []
        for integration_project_id in projects_map:
            self._client.set_jira_project_id(integration_project_id)
            jql = "labels = OpenReplay"
            if len(projects_map[integration_project_id]) > 0:
                jql += f" AND ID IN ({','.join(projects_map[integration_project_id])})"
            issues = self._client.get_issues(jql, offset=0)
            results += issues
        return {"issues": results}

    # 函数：get
    # 功能：获取指定任务的详细信息。
    # 参数：
    # - integration_project_id: JIRA 项目ID。
    # - assignment_id: 任务ID（Issue编号）。
    # 返回值：
    # - 返回任务的详细信息。
    def get(self, integration_project_id, assignment_id):
        self._client.set_jira_project_id(integration_project_id)
        return self._client.get_issue_v3(assignment_id)

    # 函数：comment
    # 功能：在指定任务上添加评论。
    # 参数：
    # - integration_project_id: JIRA 项目ID。
    # - assignment_id: 任务ID（Issue编号）。
    # - comment: 评论内容。
    # 返回值：
    # - 返回添加的评论的详细信息。
    def comment(self, integration_project_id, assignment_id, comment):
        self._client.set_jira_project_id(integration_project_id)
        return self._client.add_comment_v3(assignment_id, comment)

    # 函数：get_metas
    # 功能：获取指定项目的元数据信息，包括问题类型和可分配用户列表。
    # 参数：
    # - integration_project_id: JIRA 项目ID。
    # 返回值：
    # - 返回包含问题类型和用户列表的字典。
    def get_metas(self, integration_project_id):
        meta = {}
        self._client.set_jira_project_id(integration_project_id)
        meta["issueTypes"] = self._client.get_issue_types()
        meta["users"] = self._client.get_assignable_users()
        return {"provider": self.provider.lower(), **meta}

    # 函数：get_projects
    # 功能：获取当前用户的所有 JIRA 项目。
    # 返回值：
    # - 返回包含项目信息的列表。
    def get_projects(self):
        return self._client.get_projects()