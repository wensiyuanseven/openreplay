# 这段代码定义了 GithubIntegrationIssue 类，该类继承自 BaseIntegrationIssue，用于处理与 GitHub 集成相关的问题管理。
# 通过与 GitHub API 交互，GithubIntegrationIssue 类实现了创建新任务、获取任务详情、评论任务、获取元数据和获取用户项目等功能。
from chalicelib.core.integration_base_issue import BaseIntegrationIssue
from chalicelib.utils import github_client_v3
from chalicelib.utils.github_client_v3 import github_formatters as formatter


class GithubIntegrationIssue(BaseIntegrationIssue):
    # 初始化函数，设置 GitHub API 客户端和调用父类的构造函数。
    # 参数：
    # - integration_token: 用于验证 GitHub API 的令牌。
    def __init__(self, integration_token):
        self.__client = github_client_v3.githubV3Request(integration_token)
        super(GithubIntegrationIssue, self).__init__("GITHUB", integration_token)

    # 函数：get_current_user
    # 功能：获取当前认证的 GitHub 用户信息。
    # 返回值：
    # - 返回经过格式化的当前用户信息。
    def get_current_user(self):
        return formatter.user(self.__client.get("/user"))

    # 函数：get_meta
    # 功能：获取指定 GitHub 仓库的元数据信息，包括协作者和标签（问题类型）。
    # 参数：
    # - repoId: 仓库ID。
    # 返回值：
    # - 返回包含协作者和问题类型的字典。
    def get_meta(self, repoId):
        current_user = self.get_current_user()
        try:
            users = self.__client.get(f"/repositories/{repoId}/collaborators")
        except Exception as e:
            users = []
        users = [formatter.user(u) for u in users]
        if current_user not in users:
            users.insert(0, current_user)
        meta = {"users": users, "issueTypes": [formatter.label(l) for l in self.__client.get(f"/repositories/{repoId}/labels")]}

        return meta

    # 函数：create_new_assignment
    # 功能：在指定的 GitHub 仓库中创建一个新的任务（Issue）。
    # 参数：
    # - integration_project_id: 仓库ID。
    # - title: 任务标题。
    # - description: 任务描述。
    # - assignee: 分配的用户ID。
    # - issue_type: 问题类型（标签）。
    # 返回值：
    # - 返回经过格式化的任务信息。
    def create_new_assignment(self, integration_project_id, title, description, assignee, issue_type):
        repoId = integration_project_id
        assignees = [assignee]
        labels = [str(issue_type)]

        metas = self.get_meta(repoId)
        real_assignees = []
        for a in assignees:
            for u in metas["users"]:
                if a == str(u["id"]):
                    real_assignees.append(u["name"])
                    break
        real_labels = ["OpenReplay"]
        for l in labels:
            found = False
            for ll in metas["issueTypes"]:
                if l == str(ll["id"]):
                    real_labels.append(ll["name"])
                    found = True
                    break
            if not found:
                real_labels.append(l)
        issue = self.__client.post(f"/repositories/{repoId}/issues", body={"title": title, "body": description, "assignees": real_assignees, "labels": real_labels})
        return formatter.issue(issue)

    # 函数：get_by_ids
    # 功能：根据保存的任务ID列表获取任务的详细信息。
    # 参数：
    # - saved_issues: 包含任务ID和集成项目ID的字典列表。
    # 返回值：
    # - 返回包含任务详细信息的字典。
    def get_by_ids(self, saved_issues):
        results = []
        for i in saved_issues:
            results.append(self.get(integration_project_id=i["integrationProjectId"], assignment_id=i["id"]))
        return {"issues": results}

    # 函数：get
    # 功能：获取指定任务的详细信息，包括评论。
    # 参数：
    # - integration_project_id: 仓库ID。
    # - assignment_id: 任务ID（Issue编号）。
    # 返回值：
    # - 返回包含任务详细信息的字典。
    def get(self, integration_project_id, assignment_id):
        repoId = integration_project_id
        issueNumber = assignment_id
        issue = self.__client.get(f"/repositories/{repoId}/issues/{issueNumber}")
        issue = formatter.issue(issue)
        if issue["commentsCount"] > 0:
            issue["comments"] = [formatter.comment(c) for c in self.__client.get(f"/repositories/{repoId}/issues/{issueNumber}/comments")]
        return issue

    # 该方法用于在指定的 GitHub 任务（Issue）上添加评论。它通过 GitHub API 向特定任务提交评论，并返回格式化后的评论信息。
    # 参数：
    # integration_project_id: 仓库ID，表示评论要添加到哪个 GitHub 仓库的任务中。
    # assignment_id: 任务ID，表示评论要添加到哪个特定任务（Issue）中。
    # comment: 评论内容，是用户希望添加到任务中的文本信息。
    # 返回值：
    # 返回经过格式化的评论信息。这个信息是调用 formatter.comment 方法后的结果，该方法会对从 GitHub API 返回的原始评论数据进行处理，使其更易于使用。
    def comment(self, integration_project_id, assignment_id, comment):
        repoId = integration_project_id
        issueNumber = assignment_id
        commentCreated = self.__client.post(f"/repositories/{repoId}/issues/{issueNumber}/comments", body={"body": comment})
        return formatter.comment(commentCreated)

    # 函数：get_metas
    # 功能：获取指定仓库的元数据，包括协作者和问题类型。
    # 参数：
    # - integration_project_id: 仓库ID。
    # 返回值：
    # - 返回包含协作者和问题类型的字典。
    def get_metas(self, integration_project_id):
        current_user = self.get_current_user()
        try:
            users = self.__client.get(f"/repositories/{integration_project_id}/collaborators")
        except Exception as e:
            users = []
        users = [formatter.user(u) for u in users]
        if current_user not in users:
            users.insert(0, current_user)

        return {"provider": self.provider.lower(), "users": users, "issueTypes": [formatter.label(l) for l in self.__client.get(f"/repositories/{integration_project_id}/labels")]}

    # 函数：get_projects
    # 功能：获取当前用户的所有 GitHub 仓库。
    # 返回值：
    # - 返回包含仓库信息的列表。
    def get_projects(self):
        repos = self.__client.get("/user/repos")
        return [formatter.repo(r) for r in repos]


# get_metas 方法：
# 该方法获取指定仓库的元数据信息，包括协作者列表和标签（问题类型）列表。
# 方法首先调用 get_current_user 获取当前用户信息。
# 通过调用 GitHub API 的 /repositories/{integration_project_id}/collaborators 端点获取指定仓库的协作者列表。如果获取失败（例如用户没有足够权限访问仓库的协作者列表），捕获异常并将 users 设置为空列表。
# 接着，方法会检查当前用户是否在协作者列表中，如果不在，则将当前用户添加到列表的首位。
# 然后，通过调用 /repositories/{integration_project_id}/labels 端点获取该仓库中的标签，并将这些标签格式化后返回。
# 最终，方法返回一个包含协作者列表和标签列表的字典对象。
# get_projects 方法：

# 该方法用于获取当前用户在 GitHub 上的所有仓库列表。
# 通过调用 GitHub API 的 /user/repos 端点获取用户的所有仓库。
# 返回经过格式化后的仓库信息列表。
# 总结
# get_metas 方法获取了有关特定仓库的元数据信息，并为用户提供了相关的协作者和问题标签的信息，这在创建新任务时尤其有用。
# get_projects 方法则提供了一个用户所有仓库的列表，可以用于进一步操作，例如在这些仓库中创建任务或获取仓库的详细信息。
# 这些方法使得 GithubIntegrationIssue 类能够有效地与 GitHub API 交互，为用户提供操作和管理 GitHub 项目的便利途径。
