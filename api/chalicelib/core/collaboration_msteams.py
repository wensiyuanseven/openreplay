# 这个类主要用于与 Microsoft Teams 进行集成，通过 webhook 向 Teams 发送消息、批量消息以及分享特定的会话或错误信息。
# 它提供了一些工具方法来处理集成的基本操作，如检测集成是否存在，向 Teams 发送测试消息等。
import logging

import requests
from decouple import config
from fastapi import HTTPException, status

import schemas
from chalicelib.core import webhook
from chalicelib.core.collaboration_base import BaseCollaboration

logger = logging.getLogger(__name__)


class MSTeams(BaseCollaboration):
    # 这个方法用于添加一个新的 Microsoft Teams 集成。
    # 首先，它会检查是否已经存在相同名称的 webhook，如果存在，则抛出一个 HTTP 400 错误。
    # 如果 say_hello 方法返回 True，则添加这个 webhook，并将其保存到数据库中
    @classmethod
    def add(cls, tenant_id, data: schemas.AddCollaborationSchema):
        if webhook.exists_by_name(tenant_id=tenant_id, name=data.name, exclude_id=None, webhook_type=schemas.WebhookType.msteams):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"name already exists.")
        if cls.say_hello(data.url):
            return webhook.add(tenant_id=tenant_id, endpoint=data.url.unicode_string(), webhook_type=schemas.WebhookType.msteams, name=data.name)
        return None

    # 个方法向指定的 Microsoft Teams webhook URL 发送一个简单的欢迎消息，用于测试集成是否成功。
    # 如果请求失败，它会记录一个警告日志并返回 False。
    @classmethod
    def say_hello(cls, url):
        r = requests.post(url=url, json={"@type": "MessageCard", "@context": "https://schema.org/extensions", "summary": "Welcome to OpenReplay", "title": "Welcome to OpenReplay"})
        if r.status_code != 200:
            logging.warning("MSTeams 集成失败")
            logging.warning(r.text)
            return False
        return True

    # 该方法直接向指定的 webhook 发送原始消息。
    # 首先，它会根据 tenant_id 和 webhook_id 获取相应的集成信息。
    # 如果集成信息不存在，它返回一个错误。
    # 否则，它发送请求并处理可能的超时或其他异常。
    @classmethod
    def send_raw(cls, tenant_id, webhook_id, body):
        integration = cls.get_integration(tenant_id=tenant_id, integration_id=webhook_id)
        if integration is None:
            return {"errors": ["msteams integration not found"]}
        try:
            r = requests.post(url=integration["endpoint"], json=body, timeout=5)
            if r.status_code != 200:
                logging.warning(f"!! issue sending msteams raw; webhookId:{webhook_id} code:{r.status_code}")
                logging.warning(r.text)
                return None
        except requests.exceptions.Timeout:
            logging.warning(f"!! Timeout sending msteams raw webhookId:{webhook_id}")
            return None
        except Exception as e:
            logging.warning(f"!! Issue sending msteams raw webhookId:{webhook_id}")
            logging.warning(e)
            return None
        return {"data": r.text}

    # 该方法用于批量发送消息。
    # 它将消息拆分成 50 条一组，并插入一些标记文本。
    # 然后，它依次发送这些消息，并处理可能的错误。
    @classmethod
    def send_batch(cls, tenant_id, webhook_id, attachments):
        integration = cls.get_integration(tenant_id=tenant_id, integration_id=webhook_id)
        if integration is None:
            return {"errors": ["msteams integration not found"]}
        logging.debug(f"====> sending msteams batch notification: {len(attachments)}")
        for i in range(0, len(attachments), 50):
            part = attachments[i : i + 50]
            for j in range(1, len(part), 2):
                part.insert(j, {"text": "***"})

            r = requests.post(url=integration["endpoint"], json={"@type": "MessageCard", "@context": "http://schema.org/extensions", "summary": part[0]["activityTitle"], "sections": part})
            if r.status_code != 200:
                logging.warning("!!!! something went wrong")
                logging.warning(r.text)

    # 这是一个私有方法，用于共享特定的内容到 Microsoft Teams。
    # 它接受附件信息和可选的额外参数 extra，并发送给指定的集成 URL。
    @classmethod
    def __share(cls, tenant_id, integration_id, attachement, extra=None):
        if extra is None:
            extra = {}
        integration = cls.get_integration(tenant_id=tenant_id, integration_id=integration_id)
        if integration is None:
            return {"errors": ["Microsoft Teams integration not found"]}
        r = requests.post(url=integration["endpoint"], json={"@type": "MessageCard", "@context": "http://schema.org/extensions", "sections": [attachement], **extra})

        return r.text

    # 这个方法用于分享特定会话的链接到 Microsoft Teams。
    # 它构建一个包含会话信息的消息，并调用 __share 方法发送。
    @classmethod
    def share_session(cls, tenant_id, project_id, session_id, user, comment, project_name=None, integration_id=None):
        title = f"*{user}* has shared the below session!"
        link = f"{config('SITE_URL')}/{project_id}/session/{session_id}"
        args = {"activityTitle": title, "facts": [{"name": "Session:", "value": link}], "markdown": True}
        if project_name and len(project_name) > 0:
            args["activitySubtitle"] = f"On Project *{project_name}*"
        if comment and len(comment) > 0:
            args["facts"].append({"name": "Comment:", "value": comment})
        data = cls.__share(tenant_id, integration_id, attachement=args, extra={"summary": title})
        if "errors" in data:
            return data
        return {"data": data}

    # 这个方法类似于 share_session，但用于分享错误信息。
    @classmethod
    def share_error(cls, tenant_id, project_id, error_id, user, comment, project_name=None, integration_id=None):
        title = f"*{user}* has shared the below error!"
        link = f"{config('SITE_URL')}/{project_id}/errors/{error_id}"
        args = {"activityTitle": title, "facts": [{"name": "Session:", "value": link}], "markdown": True}
        if project_name and len(project_name) > 0:
            args["activitySubtitle"] = f"On Project *{project_name}*"
        if comment and len(comment) > 0:
            args["facts"].append({"name": "Comment:", "value": comment})
        data = cls.__share(tenant_id, integration_id, attachement=args, extra={"summary": title})
        if "errors" in data:
            return data
        return {"data": data}

    # 这个方法用于获取特定租户的 Microsoft Teams 集成信息。
    # 如果提供了 integration_id，它会返回对应的集成信息；否则，返回租户的第一个 Microsoft Teams 集成。
    @classmethod
    def get_integration(cls, tenant_id, integration_id=None):
        if integration_id is not None:
            return webhook.get_webhook(tenant_id=tenant_id, webhook_id=integration_id, webhook_type=schemas.WebhookType.msteams)

        integrations = webhook.get_by_type(tenant_id=tenant_id, webhook_type=schemas.WebhookType.msteams)
        if integrations is None or len(integrations) == 0:
            return None
        return integrations[0]
