# 该代码定义了一个用于处理集成问题的抽象基类 BaseIntegrationIssue，它为处理不同的集成供应商（如Jira、GitHub等）的问题管理提供了一个统一的接口。通过使用抽象基类，代码可以实现不同集成供应商的具体实现，同时保持接口的一致性。
# 此外，还定义了一个自定义异常类 RequestException 和一个用于处理代理问题的函数 proxy_issues_handler。
from abc import ABC, abstractmethod


# 定义一个自定义异常类，用于处理请求相关的异常情况。
class RequestException(Exception):
    pass


# 代理问题处理函数，用于处理在集成过程中出现的异常。
# 参数：
# - e: 传入的异常对象。
# 返回值：
# - 返回包含错误信息的字典。
def proxy_issues_handler(e):
    print("=======__proxy_issues_handler=======")
    print(str(e))
    return {"errors": [str(e)]}


# 定义一个抽象基类，用于处理集成问题。
# 不同的集成供应商（如Jira、GitHub等）可以继承此基类并实现其抽象方法。
class BaseIntegrationIssue(ABC):
    # 初始化函数，设置集成供应商的名称和集成令牌。
    # 参数：
    # - provider: 集成供应商的名称。
    # - integration_token: 用于验证和访问集成供应商API的令牌。
    def __init__(self, provider, integration_token):
        self.provider = provider
        self.integration_token = integration_token

    # 抽象方法：创建新的任务分配。
    # 参数：
    # - integration_project_id: 集成项目ID。
    # - title: 任务标题。
    # - description: 任务描述。
    # - assignee: 任务分配对象。
    # - issue_type: 问题类型。
    # 此方法必须在子类中实现。
    @abstractmethod
    def create_new_assignment(self, integration_project_id, title, description, assignee, issue_type):
        pass

    # 抽象方法：根据保存的任务ID列表获取任务信息。
    # 参数：
    # - saved_issues: 保存的任务ID列表。
    # 此方法必须在子类中实现。
    @abstractmethod
    @abstractmethod
    def get_by_ids(self, saved_issues):
        pass

    # 抽象方法：根据集成项目ID和任务ID获取任务信息。
    # 参数：
    # - integration_project_id: 集成项目ID。
    # - assignment_id: 任务ID。
    # 此方法必须在子类中实现。
    @abstractmethod
    def get(self, integration_project_id, assignment_id):
        pass

    # 抽象方法：对指定任务添加评论。
    # 参数：
    # - integration_project_id: 集成项目ID。
    # - assignment_id: 任务ID。
    # - comment: 评论内容。
    # 此方法必须在子类中实现。
    @abstractmethod
    def comment(self, integration_project_id, assignment_id, comment):
        pass

    # 抽象方法：获取指定项目的元数据。
    # 参数：
    # - integration_project_id: 集成项目ID。
    # 此方法必须在子类中实现。
    @abstractmethod
    def get_metas(self, integration_project_id):
        pass

    # 抽象方法：获取所有项目的列表。
    # 此方法必须在子类中实现。
    @abstractmethod
    def get_projects(self):
        pass


# 这个代码模块为处理不同的集成问题管理工具提供了一个统一的接口。通过定义抽象基类 BaseIntegrationIssue，
# 开发者可以轻松扩展支持不同的集成供应商，而无需修改现有的代码逻辑。每个供应商的具体实现可以继承此基类，并实现其抽象方法，从而保证了接口的一致性和可扩展性。