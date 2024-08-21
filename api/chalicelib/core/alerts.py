# 这段代码实现了一个处理警报的系统，主要功能包括创建、获取、更新和删除警报，以及处理与通知相关的操作
import json  # 处理JSON数据格式。
import logging
import time  #处理与时间相关的功能。
from datetime import datetime #用于处理日期和时间。

from decouple import config

import schemas
# 导入核心功能模块，分别用于处理通知、Webhooks、Microsoft Teams 和 Slack 通讯。 
# 导入数据库操作、辅助功能、邮件发送和SMTP配置。
from chalicelib.core import notifications, webhook
from chalicelib.core.collaboration_msteams import MSTeams
from chalicelib.core.collaboration_slack import Slack
from chalicelib.utils import pg_client, helper, email_helper, smtp
from chalicelib.utils.TimeUTC import TimeUTC

#从数据库中根据id查找并返回警报的详细信息
def get(id):
    with pg_client.PostgresClient() as cur:
        cur.execute(
            cur.mogrify(
                """SELECT *
                    FROM public.alerts
                    WHERE alert_id =%(id)s;
                """,
                {"id": id},
            )
        )
        a = helper.dict_to_camel_case(cur.fetchone())
    return helper.custom_alert_to_front(__process_circular(a))

# 获取某个项目的所有警报： 
# 参数: project_id 是项目的唯一标识符。
# 功能: 查询数据库，获取与指定项目相关的所有未被删除的警报，并按创建时间排序。
def get_all(project_id):
    with pg_client.PostgresClient() as cur:
        query = cur.mogrify(
            """
                    SELECT alerts.*,
                           COALESCE(metrics.name || '.' || (COALESCE(metric_series.name, 'series ' || index)) || '.count',
                                    query ->> 'left') AS series_name
                    FROM public.alerts
                         LEFT JOIN metric_series USING (series_id)
                         LEFT JOIN metrics USING (metric_id)
                    WHERE alerts.project_id =%(project_id)s 
                        AND alerts.deleted_at ISNULL
                    ORDER BY alerts.created_at;""",
            {"project_id": project_id},
        )
        cur.execute(query=query)
        all = helper.list_to_camel_case(cur.fetchall())
    for i in range(len(all)):
        all[i] = helper.custom_alert_to_front(__process_circular(all[i]))
    return all

# 处理警报对象的时间戳和数据格式：
# 参数: alert 是警报的详细信息。
# 功能: 移除deletedAt字段，并将createdAt字段从日期格式转换为时间戳格式。
def __process_circular(alert):
    if alert is None:
        return None
    alert.pop("deletedAt")
    alert["createdAt"] = TimeUTC.datetime_to_timestamp(alert["createdAt"])
    return alert

# 创建新的警报：
# 参数: project_id 是项目的唯一标识符，data 是包含警报详细信息的模式对象。
# 功能: 将新警报插入到数据库中，并返回创建的警报信息。
def create(project_id, data: schemas.AlertSchema):
    # 数据模型（例如通过 Pydantic 定义的模型）转换为一个字典  这在处理和传递数据时非常有用，因为字典格式的数据可以很容易地序列化为 JSON 或与数据库等外部系统交互。
    data = data.model_dump()
    # 用于将 Python 对象（如字典）序列化为 JSON 字符串，以便存储或传输。
    data["query"] = json.dumps(data["query"])
    data["options"] = json.dumps(data["options"])

    with pg_client.PostgresClient() as cur:
        cur.execute(
            cur.mogrify(
                """
                    INSERT INTO public.alerts(project_id, name, description, detection_method, query, options, series_id, change)
                    VALUES (%(project_id)s, %(name)s, %(description)s, %(detection_method)s, %(query)s, %(options)s::jsonb, %(series_id)s, %(change)s)
                    RETURNING *;""",
                {"project_id": project_id, **data},
            )
        )
        a = helper.dict_to_camel_case(cur.fetchone())
    return {"data": helper.custom_alert_to_front(helper.dict_to_camel_case(__process_circular(a)))}

# 更新已有的警报：
# 参数: id 是警报的唯一标识符，data 是包含更新信息的模式对象。
# 功能: 更新数据库中指定警报的详细信息，并返回更新后的信息。

def update(id, data: schemas.AlertSchema):
    data = data.model_dump()
    data["query"] = json.dumps(data["query"])
    data["options"] = json.dumps(data["options"])

    with pg_client.PostgresClient() as cur:
        query = cur.mogrify(
            """\
                    UPDATE public.alerts
                    SET name = %(name)s,
                        description = %(description)s,
                        active = TRUE,
                        detection_method = %(detection_method)s,
                        query = %(query)s,
                        options = %(options)s,
                        series_id = %(series_id)s,
                        change = %(change)s
                    WHERE alert_id =%(id)s AND deleted_at ISNULL
                    RETURNING *;""",
            {"id": id, **data},
        )
        cur.execute(query=query)
        a = helper.dict_to_camel_case(cur.fetchone())
    return {"data": helper.custom_alert_to_front(__process_circular(a))}

# 处理通知：
# 参数: data 是一个通知列表。
# 功能: 解析通知的类型，并根据类型调用相应的发送函数（例如发送到Slack、MSTeams或通过电子邮件发送）。
def process_notifications(data):
    full = {}
    for n in data:
        if "message" in n["options"]:
            webhook_data = {}
            if "data" in n["options"]:
                webhook_data = n["options"].pop("data")
            for c in n["options"].pop("message"):
                if c["type"] not in full:
                    full[c["type"]] = []
                if c["type"] in ["slack", "msteams", "email"]:
                    full[c["type"]].append({"notification": n, "destination": c["value"]})
                elif c["type"] in ["webhook"]:
                    full[c["type"]].append({"data": webhook_data, "destination": c["value"]})
    notifications.create(data)
    BATCH_SIZE = 200
    for t in full.keys():
        for i in range(0, len(full[t]), BATCH_SIZE):
            notifications_list = full[t][i : min(i + BATCH_SIZE, len(full[t]))]
            if notifications_list is None or len(notifications_list) == 0:
                break

            if t == "slack":
                try:
                    send_to_slack_batch(notifications_list=notifications_list)
                except Exception as e:
                    logging.error("!!!Error while sending slack notifications batch")
                    logging.error(str(e))
            elif t == "msteams":
                try:
                    send_to_msteams_batch(notifications_list=notifications_list)
                except Exception as e:
                    logging.error("!!!Error while sending msteams notifications batch")
                    logging.error(str(e))
            elif t == "email":
                try:
                    send_by_email_batch(notifications_list=notifications_list)
                except Exception as e:
                    logging.error("!!!Error while sending email notifications batch")
                    logging.error(str(e))
            elif t == "webhook":
                try:
                    webhook.trigger_batch(data_list=notifications_list)
                except Exception as e:
                    logging.error("!!!发送 webhook 通知批次时出错")
                    logging.error(str(e))

# 通过电子邮件发送通知：
# 参数: notification 是通知内容，destination 是收件人。
# 功能: 使用email_helper.alert_email发送电子邮件通知。
def send_by_email(notification, destination):
    if notification is None:
        return
    email_helper.alert_email(recipients=destination, subject=f'"{notification["title"]}" has been triggered', data={"message": f'"{notification["title"]}" {notification["description"]}', "project_id": notification["options"]["projectId"]})

# 批量通过电子邮件发送通知：
# 参数: notifications_list 是通知列表。
# 功能: 检查SMTP配置，逐条发送邮件通知，发送间隔为1秒。
def send_by_email_batch(notifications_list):
    if not smtp.has_smtp():
        logging.info("没有用于电子邮件通知的 SMTP 配置")
    if notifications_list is None or len(notifications_list) == 0:
        logging.info("没有电子邮件通知")
        return
    for n in notifications_list:
        send_by_email(notification=n.get("notification"), destination=n.get("destination"))
        time.sleep(1)

# 批量发送通知到Slack：
# 参数: notifications_list 是通知列表。
# 功能: 将通知整理为Slack消息格式，并使用Slack.send_batch发送。
def send_to_slack_batch(notifications_list):
    webhookId_map = {}
    for n in notifications_list:
        if n.get("destination") not in webhookId_map:
            webhookId_map[n.get("destination")] = {"tenantId": n["notification"]["tenantId"], "batch": []}
        webhookId_map[n.get("destination")]["batch"].append({"text": n["notification"]["description"] + f"\n<{config('SITE_URL')}{n['notification']['buttonUrl']}|{n['notification']['buttonText']}>", "title": n["notification"]["title"], "title_link": n["notification"]["buttonUrl"], "ts": datetime.now().timestamp()})
    for batch in webhookId_map.keys():
        Slack.send_batch(tenant_id=webhookId_map[batch]["tenantId"], webhook_id=batch, attachments=webhookId_map[batch]["batch"])

# 批量发送通知到Microsoft Teams：
# 参数: notifications_list 是通知列表。
# 功能: 将通知整理为Microsoft Teams消息格式，并使用MSTeams.send_batch发送。

def send_to_msteams_batch(notifications_list):
    webhookId_map = {}
    for n in notifications_list:
        if n.get("destination") not in webhookId_map:
            webhookId_map[n.get("destination")] = {"tenantId": n["notification"]["tenantId"], "batch": []}

        link = f"{config('SITE_URL')}{n['notification']['buttonUrl']}"
        # for MSTeams, the batch is the list of `sections`
        webhookId_map[n.get("destination")]["batch"].append({"activityTitle": n["notification"]["title"], "activitySubtitle": f"On Project *{n['notification']['projectName']}*", "facts": [{"name": "Target:", "value": link}, {"name": "Description:", "value": n["notification"]["description"]}], "markdown": True})
    for batch in webhookId_map.keys():
        MSTeams.send_batch(tenant_id=webhookId_map[batch]["tenantId"], webhook_id=batch, attachments=webhookId_map[batch]["batch"])

# 删除警报：
# 参数: project_id 是项目的唯一标识符，alert_id 是警报的唯一标识符。
# 功能: 在数据库中将指定警报的deleted_at字段设置为当前时间，并将active字段设为FALSE，表示该警报已被删除。
def delete(project_id, alert_id):
    with pg_client.PostgresClient() as cur:
        cur.execute(
            cur.mogrify(
                """ UPDATE public.alerts 
                            SET deleted_at = timezone('utc'::text, now()),
                                active = FALSE
                            WHERE alert_id = %(alert_id)s AND project_id=%(project_id)s;""",
                {"alert_id": alert_id, "project_id": project_id},
            )
        )
    return {"data": {"state": "success"}}

# 获取预定义的警报值：
# 功能: 返回所有预定义的警报列及其相关信息，如名称、值、单位等。
def get_predefined_values():
    values = [e.value for e in schemas.AlertColumn]
    values = [{"name": v, "value": v, "unit": "count" if v.endswith(".count") else "ms", "predefined": True, "metricId": None, "seriesId": None} for v in values if v != schemas.AlertColumn.custom]
    return values
