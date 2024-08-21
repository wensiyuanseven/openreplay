# 这个类主要用于与 Slack 进行集成，通过 webhook 向 Slack 发送消息、批量消息以及分享特定的会话或错误信息。
# 它提供了一些工具方法来处理集成的基本操作，如检测集成是否存在，向 Slack 发送测试消息等
# 主要流程
# 添加 Slack 集成：使用 add 方法，可以添加一个新的 Slack 集成。如果集成名称已经存在，抛出错误。成功添加后，会发送一条测试消息到指定的 Slack Webhook URL。

# 发送消息：

# 单条消息：使用 send_raw 方法，可以发送一条自定义的消息到 Slack。
# 批量消息：使用 send_batch 方法，可以分批发送大量消息到 Slack。
# 共享会话或错误信息：使用 share_session 或 share_error 方法，可以将特定会话或错误信息通过 Slack 共享。
# 获取集成信息：使用 get_integration 方法，可以根据租户 ID 和集成 ID 获取 Slack 集成信息。如果未提供集成 ID，则返回租户的第一个 Slack 集成。
from datetime import datetime

import requests
from decouple import config
from fastapi import HTTPException, status

import schemas
from chalicelib.core import webhook
from chalicelib.core.collaboration_base import BaseCollaboration  # 是 Slack 类的基


class Slack(BaseCollaboration):
    # 这个方法用于添加一个新的 Slack 集成。
    # 首先，它会检查是否已经存在相同名称的 webhook，如果存在，则抛出一个 HTTP 400 错误。
    # 如果 say_hello 方法返回 True，则添加这个 webhook，并将其保存到数据库中。
    @classmethod
    def add(cls, tenant_id, data: schemas.AddCollaborationSchema):
        if webhook.exists_by_name(tenant_id=tenant_id, name=data.name, exclude_id=None, webhook_type=schemas.WebhookType.slack):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"name already exists.")
        if cls.say_hello(data.url):
            return webhook.add(tenant_id=tenant_id, endpoint=data.url.unicode_string(), webhook_type=schemas.WebhookType.slack, name=data.name)
        return None

    # 这个方法向指定的 Slack webhook URL 发送一个简单的欢迎消息，用于测试集成是否成功。
    # 如果请求失败，它会打印一条错误消息并返回 False。
    @classmethod
    def say_hello(cls, url):
        r = requests.post(
            url=url,
            json={
                "attachments": [
                    {
                        "text": "Welcome to OpenReplay",
                        "ts": datetime.now().timestamp(),
                    }
                ]
            },
        )
        if r.status_code != 200:
            print("slack integration failed")
            print(r.text)
            return False
        return True

    # 该方法直接向指定的 Slack webhook 发送原始消息。
    # 首先，它会根据 tenant_id 和 webhook_id 获取相应的集成信息。
    # 如果集成信息不存在，它返回一个错误。
    # 否则，它发送请求并处理可能的超时或其他异常。
    @classmethod
    def send_raw(cls, tenant_id, webhook_id, body):
        integration = cls.get_integration(tenant_id=tenant_id, integration_id=webhook_id)
        if integration is None:
            return {"errors": ["slack integration not found"]}
        try:
            r = requests.post(url=integration["endpoint"], json=body, timeout=5)
            if r.status_code != 200:
                print(f"!! issue sending slack raw; webhookId:{webhook_id} code:{r.status_code}")
                print(r.text)
                return None
        except requests.exceptions.Timeout:
            print(f"!! Timeout sending slack raw webhookId:{webhook_id}")
            return None
        except Exception as e:
            print(f"!! Issue sending slack raw webhookId:{webhook_id}")
            print(str(e))
            return None
        return {"data": r.text}

    # 方法用于批量发送消息。
    # 它将消息拆分成每组最多 100 条，并逐组发送。
    # 如果发送失败，它会打印错误信息。
    @classmethod
    def send_batch(cls, tenant_id, webhook_id, attachments):
        integration = cls.get_integration(tenant_id=tenant_id, integration_id=webhook_id)
        if integration is None:
            return {"errors": ["slack integration not found"]}
        print(f"====> sending slack batch notification: {len(attachments)}")
        for i in range(0, len(attachments), 100):
            r = requests.post(url=integration["endpoint"], json={"attachments": attachments[i : i + 100]})
            if r.status_code != 200:
                print("!!!! something went wrong while sending to:")
                print(integration)
                print(r)
                print(r.text)

    # 这是一个私有方法，用于共享特定的内容到 Slack。
    # 它接受附件信息和可选的额外参数 extra，并发送给指定的集成 URL。
    # 在发送之前，附加当前时间戳。
    @classmethod
    def __share(cls, tenant_id, integration_id, attachement, extra=None):
        if extra is None:
            extra = {}
        integration = cls.get_integration(tenant_id=tenant_id, integration_id=integration_id)
        if integration is None:
            return {"errors": ["slack integration not found"]}
        attachement["ts"] = datetime.now().timestamp()
        r = requests.post(url=integration["endpoint"], json={"attachments": [attachement], **extra})
        return r.text

    #  这个方法用于分享特定会话的链接到 Slack。
    # 它构建一个包含会话信息的消息，并调用 __share 方法发送。
    @classmethod
    def share_session(cls, tenant_id, project_id, session_id, user, comment, project_name=None, integration_id=None):
        args = {"fallback": f"{user} has shared the below session!", "pretext": f"{user} has shared the below session!", "title": f"{config('SITE_URL')}/{project_id}/session/{session_id}", "title_link": f"{config('SITE_URL')}/{project_id}/session/{session_id}", "text": comment}
        data = cls.__share(tenant_id, integration_id, attachement=args)
        if "errors" in data:
            return data
        return {"data": data}

    # 这个方法类似于 share_session，但用于分享错误信息。
    @classmethod
    def share_error(cls, tenant_id, project_id, error_id, user, comment, project_name=None, integration_id=None):
        args = {"fallback": f"{user} has shared the below error!", "pretext": f"{user} has shared the below error!", "title": f"{config('SITE_URL')}/{project_id}/errors/{error_id}", "title_link": f"{config('SITE_URL')}/{project_id}/errors/{error_id}", "text": comment}
        data = cls.__share(tenant_id, integration_id, attachement=args)
        if "errors" in data:
            return data
        return {"data": data}

    # 这个方法用于获取特定租户的 Slack 集成信息。
    # 如果提供了 integration_id，它会返回对应的集成信息；否则，返回租户的第一个 Slack 集成。
    @classmethod
    def get_integration(cls, tenant_id, integration_id=None):
        if integration_id is not None:
            return webhook.get_webhook(tenant_id=tenant_id, webhook_id=integration_id, webhook_type=schemas.WebhookType.slack)

        integrations = webhook.get_by_type(tenant_id=tenant_id, webhook_type=schemas.WebhookType.slack)
        if integrations is None or len(integrations) == 0:
            return None
        return integrations[0]
