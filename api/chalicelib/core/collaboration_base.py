# BaseCollaboration 抽象基类定义了协作系统中的标准操作接口，
# 要求任何继承该基类的类必须实现这些操作方法。这种设计模式确保了不同的协作工具或平台实现了相同的接口，从而简化了系统的扩展和维护。
from abc import ABC, abstractmethod

import schemas


class BaseCollaboration(ABC):
    # 作用: 添加协作记录或配置，通常涉及在协作系统中创建或更新数据。
    # 参数:
    # tenant_id: 租户的唯一标识符。
    # data: 包含协作信息的数据对象，类型为 schemas.AddCollaborationSchema。
    @classmethod
    @abstractmethod
    def add(cls, tenant_id, data: schemas.AddCollaborationSchema):
        pass

    # 作用: 一个简单的测试或验证方法，通常用于确认连接或配置是否正确。
    # 参数:
    # url: 需要测试或验证的URL。
    @classmethod
    @abstractmethod
    def say_hello(cls, url):
        pass

    # 作用: 发送原始数据或消息到指定的 webhook。
    # 参数:
    # tenant_id: 租户的唯一标识符。
    # webhook_id: webhook 的唯一标识符。
    # body: 要发送的消息体或数据。
    @classmethod
    @abstractmethod
    def send_raw(cls, tenant_id, webhook_id, body):
        pass

    # 作用: 批量发送附件或数据到指定的 webhook。
    # 参数:
    # tenant_id: 租户的唯一标识符。
    # webhook_id: webhook 的唯一标识符。
    # attachments: 要发送的附件或数据列表。
    @classmethod
    @abstractmethod
    def send_batch(cls, tenant_id, webhook_id, attachments):
        pass

    # 作用: 共享附件或数据到特定的集成平台。
    # 参数:
    # tenant_id: 租户的唯一标识符。
    # integration_id: 集成平台的唯一标识符。
    # attachments: 要共享的附件或数据。
    # extra: 可选的额外参数。
    @classmethod
    @abstractmethod
    def __share(cls, tenant_id, integration_id, attachments, extra=None):
        pass

    # 作用: 共享特定的会话信息到集成平台或协作工具。
    # 参数:
    # tenant_id: 租户的唯一标识符。
    # project_id: 项目的唯一标识符。
    # session_id: 会话的唯一标识符。
    # user: 共享会话的用户信息。
    # comment: 共享时的附加评论或信息。
    # project_name: 可选的项目名称。
    # integration_id: 可选的集成平台标识符。
    @classmethod
    @abstractmethod
    def share_session(cls, tenant_id, project_id, session_id, user, comment, project_name=None, integration_id=None):
        pass

    # 作用: 共享特定的错误信息到集成平台或协作工具。
    # 参数:
    # tenant_id: 租户的唯一标识符。
    # project_id: 项目的唯一标识符。
    # error_id: 错误的唯一标识符。
    # user: 共享错误信息的用户。
    # comment: 共享时的附加评论或信息。
    # project_name: 可选的项目名称。
    # integration_id: 可选的集成平台标识符。
    @classmethod
    @abstractmethod
    def share_error(cls, tenant_id, project_id, error_id, user, comment, project_name=None, integration_id=None):
        pass

    # 作用: 获取特定租户的集成信息，可能包括配置的集成平台详情。
    # 参数:
    # tenant_id: 租户的唯一标识符。
    # integration_id: 可选的集成平台标识符。
    @classmethod
    @abstractmethod
    def get_integration(cls, tenant_id, integration_id=None):
        pass
