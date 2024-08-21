# 这段代码定义了一个用于处理集成管理的抽象基类 BaseIntegration。
# 该类提供了一些基础设施来管理集成供应商的认证信息，并处理用户与外部集成服务之间的交互。该类还定义了一些抽象方法，要求子类实现具体的集成逻辑。
# BaseIntegration 类提供了一个管理用户与集成服务之间交互的基础结构。通过定义抽象方法，该类确保了不同集成服务的具体实现能够满足统一的接口要求。
# 这使得代码具有高度的扩展性和灵活性，可以适应多种集成服务的需求。
from abc import ABC, abstractmethod

from chalicelib.utils import pg_client, helper


# 定义一个抽象基类，用于处理集成服务的管理。
class BaseIntegration(ABC):
    # 初始化函数，设置用户ID和问题处理类。
    # 参数：
    # - user_id: 用户ID，用于标识进行集成操作的用户。
    # - ISSUE_CLASS: 问题处理类，用于创建和管理与集成供应商相关的问题。
    def __init__(self, user_id, ISSUE_CLASS):
        self._user_id = user_id
        self._issue_handler = ISSUE_CLASS(self.integration_token)

    # 抽象属性：provider
    # 功能：获取集成供应商的名称。
    # 该属性必须在子类中实现。
    @property
    @abstractmethod
    def provider(self):
        pass

    # 抽象属性：issue_handler
    # 功能：获取问题处理对象。
    # 该属性必须在子类中实现。
    @property
    @abstractmethod
    def issue_handler(self):
        pass

    # 属性：integration_token
    # 功能：获取用户的集成认证令牌，如果令牌未配置则返回None。
    # 返回值：
    # - 返回用户的集成令牌。
    @property
    def integration_token(self):
        integration = self.get()
        if integration is None:
            print("no token configured yet")
            return None
        return integration["token"]

    # 函数：get
    # 功能：从数据库中获取用户的集成认证信息。
    # 返回值：
    # - 返回包含用户集成认证信息的字典，如果没有找到则返回None。
    def get(self):
        with pg_client.PostgresClient() as cur:
            cur.execute(
                cur.mogrify(
                    """SELECT *
                        FROM public.oauth_authentication 
                        WHERE user_id=%(user_id)s AND provider=%(provider)s;""",
                    {"user_id": self._user_id, "provider": self.provider.lower()},
                )
            )
            return helper.dict_to_camel_case(cur.fetchone())

    # 抽象方法：get_obfuscated
    # 功能：获取经过模糊处理的集成信息，用于隐藏敏感数据。
    # 该方法必须在子类中实现。
    @abstractmethod
    def get_obfuscated(self):
        pass

    # 抽象方法：update
    # 功能：更新用户的集成信息。
    # 参数：
    # - changes: 包含要更新的数据的字典。
    # - obfuscate: 布尔值，指示是否对敏感数据进行模糊处理。
    # 该方法必须在子类中实现。
    @abstractmethod
    def update(self, changes, obfuscate=False):
        pass

    # 抽象方法：_add
    # 功能：添加新的集成信息到数据库。
    # 参数：
    # - data: 包含要添加的集成数据的字典。
    # 该方法必须在子类中实现
    @abstractmethod
    def _add(self, data):
        pass

    # 抽象方法：delete
    # 功能：删除用户的集成信息。
    # 该方法必须在子类中实现。
    @abstractmethod
    def delete(self):
        pass

    # 抽象方法：add_edit
    # 功能：添加或编辑用户的集成信息。
    # 参数：
    # - data: 包含要添加或编辑的数据的字典。
    # 该方法必须在子类中实现。
    @abstractmethod
    def add_edit(self, data):
        pass
