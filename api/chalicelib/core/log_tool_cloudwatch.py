# 这段代码提供了一整套操作函数，用于管理和操作 CloudWatch 与系统的集成信息。它能够通过 AWS SDK（boto3）与 CloudWatch 进行交互，
# 获取日志组、日志流和日志事件，并通过 log_tools 模块在数据库中管理这些集成信息，包括添加、更新和删除集成信息。这些操作使得系统能够与 CloudWatch 进行紧密的集成，
# 以便更好地管理和监控项目中的日志数据。
# 这段代码实现了与 AWS CloudWatch 的集成，允许用户列出日志组、搜索日志流和日志事件，并将这些操作与项目管理系统相结合。
# 代码提供了添加、更新、删除 CloudWatch 集成信息的功能，并能够通过 AWS SDK（boto3）与 CloudWatch 进行交互。
import boto3
from chalicelib.core import log_tools
from schemas import schemas

# 定义集成类型为 "cloudwatch"
IN_TY = "cloudwatch"


# 函数：__find_groups
# 功能：递归查找 CloudWatch 日志组并返回所有日志组名称。
# 参数：
# - client: AWS CloudWatch Logs 客户端实例。
# - token: 分页令牌，用于递归查询。
# 返回值：
# - 返回包含所有日志组名称的列表。
def __find_groups(client, token):
    d_args = {"limit": 50}
    if token is not None:
        d_args["nextToken"] = token
    response = client.describe_log_groups(**d_args)
    response["logGroups"] = [i["logGroupName"] for i in response["logGroups"]]
    if "nextToken" not in response:
        return response["logGroups"]

    return response["logGroups"] + __find_groups(client, response["nextToken"])

# 函数：__make_stream_filter
# 功能：生成一个日志流过滤函数，用于筛选符合时间范围的日志流。
# 参数：
# - start_time: 起始时间戳。
# - end_time: 结束时间戳。
# 返回值：
# - 返回一个用于过滤日志流的函数。
def __make_stream_filter(start_time, end_time):
    def __valid_stream(stream):
        return "firstEventTimestamp" in stream and not (stream["firstEventTimestamp"] <= start_time and stream["lastEventTimestamp"] <= start_time or stream["firstEventTimestamp"] >= end_time and stream["lastEventTimestamp"] >= end_time)

    return __valid_stream

# 函数：__find_streams
# 功能：递归查找符合条件的日志流。
# 参数：
# - project_id: 项目ID。
# - log_group: 日志组名称。
# - client: AWS CloudWatch Logs 客户端实例。
# - token: 分页令牌，用于递归查询。
# - stream_filter: 用于过滤日志流的函数。
# 返回值：
# - 返回符合条件的日志流列表。
def __find_streams(project_id, log_group, client, token, stream_filter):
    d_args = {"logGroupName": log_group, "orderBy": "LastEventTime", "limit": 50}
    if token is not None and len(token) > 0:
        d_args["nextToken"] = token
    data = client.describe_log_streams(**d_args)
    streams = list(filter(stream_filter, data["logStreams"]))
    if "nextToken" not in data:
        save_new_token(project_id=project_id, token=token)
        return streams
    return streams + __find_streams(project_id, log_group, client, data["nextToken"], stream_filter)

# 函数：__find_events
# 功能：递归查找日志流中的事件。
# 参数：
# - client: AWS CloudWatch Logs 客户端实例。
# - log_group: 日志组名称。
# - streams: 日志流名称列表。
# - last_token: 上次查询的分页令牌。
# - start_time: 起始时间戳。
# - end_time: 结束时间戳。
# 返回值：
# - 返回符合条件的日志事件列表。
def __find_events(client, log_group, streams, last_token, start_time, end_time):
    f_args = {"logGroupName": log_group, "logStreamNames": streams, "startTime": start_time, "endTime": end_time, "limit": 10000, "filterPattern": "openreplay_session_id"}
    if last_token is not None:
        f_args["nextToken"] = last_token
    response = client.filter_log_events(**f_args)
    if "nextToken" not in response:
        return response["events"]

    return response["events"] + __find_events(client, log_group, streams, response["nextToken"], start_time, end_time)

# 函数：list_log_groups
# 功能：列出 AWS 账户中的所有 CloudWatch 日志组。
# 参数：
# - aws_access_key_id: AWS Access Key ID。
# - aws_secret_access_key: AWS Secret Access Key。
# - region: AWS 区域名称。
# 返回值：
# - 返回包含日志组名称的列表。
def list_log_groups(aws_access_key_id, aws_secret_access_key, region):
    logs = boto3.client("logs", aws_access_key_id=aws_access_key_id, aws_secret_access_key=aws_secret_access_key, region_name=region)
    return __find_groups(logs, None)

# 函数：get_all
# 功能：获取指定租户下所有 CloudWatch 集成的日志信息。
# 参数：
# - tenant_id: 租户ID，用于标识集成操作的租户。
# 返回值：
# - 返回包含所有 CloudWatch 集成日志信息的列表。
def get_all(tenant_id):
    return log_tools.get_all_by_tenant(tenant_id=tenant_id, integration=IN_TY)

# 函数：get
# 功能：获取指定项目的 CloudWatch 集成日志信息。
# 参数：
# - project_id: 项目ID，用于标识具体的项目。
# 返回值：
# - 返回包含指定项目 CloudWatch 集成日志信息的字典。
def get(project_id):
    return log_tools.get(project_id=project_id, integration=IN_TY)

# 函数：update
# 功能：更新指定项目的 CloudWatch 集成信息。
# 参数：
# - tenant_id: 租户ID，用于标识集成操作的租户。
# - project_id: 项目ID，用于标识具体的项目。
# - changes: 包含需要更新的信息的字典。
# 返回值：
# - 返回更新后的集成信息。
def update(tenant_id, project_id, changes):
    options = {}
    if "authorization_token" in changes:
        options["authorization_token"] = changes.pop("authorization_token")
    if "project_id" in changes:
        options["project_id"] = changes.pop("project_id")
    if len(options.keys()) > 0:
        changes["options"] = options
    return log_tools.edit(project_id=project_id, integration=IN_TY, changes=changes)

# 函数：add
# 功能：为指定项目添加新的 CloudWatch 集成信息。
# 参数：
# - tenant_id: 租户ID，用于标识集成操作的租户。
# - project_id: 项目ID，用于标识具体的项目。
# - aws_access_key_id: AWS Access Key ID。
# - aws_secret_access_key: AWS Secret Access Key。
# - log_group_name: CloudWatch 日志组名称。
# - region: AWS 区域名称。
# 返回值：
# - 返回添加后的集成信息。
def add(tenant_id, project_id, aws_access_key_id, aws_secret_access_key, log_group_name, region):
    return log_tools.add(project_id=project_id, integration=IN_TY, options={"awsAccessKeyId": aws_access_key_id, "awsSecretAccessKey": aws_secret_access_key, "logGroupName": log_group_name, "region": region})

# 函数：save_new_token
# 功能：保存新的分页令牌，以便后续使用。
# 参数：
# - project_id: 项目ID，用于标识具体的项目。
# - token: 新的分页令牌。
def save_new_token(project_id, token):
    update(tenant_id=None, project_id=project_id, changes={"last_token": token})

# 函数：delete
# 功能：删除指定项目的 CloudWatch 集成信息。
# 参数：
# - tenant_id: 租户ID，用于标识集成操作的租户。
# - project_id: 项目ID，用于标识具体的项目。
# 返回值：
# - 返回删除状态信息。
def delete(tenant_id, project_id):
    return log_tools.delete(project_id=project_id, integration=IN_TY)

# 函数：add_edit
# 功能：根据传入的数据添加或更新指定项目的 CloudWatch 集成信息。
# 参数：
# - tenant_id: 租户ID，用于标识集成操作的租户。
# - project_id: 项目ID，用于标识具体的项目。
# - data: 包含 CloudWatch 集成信息的架构实例（schemas.IntegrationCloudwatchSchema）。
# 返回值：
# - 返回添加或更新后的集成信息。
def add_edit(tenant_id, project_id, data: schemas.IntegrationCloudwatchSchema):
    s = get(project_id)
    if s is not None:
        return update(tenant_id=tenant_id, project_id=project_id, changes={"awsAccessKeyId": data.aws_access_key_id, "awsSecretAccessKey": data.aws_secret_access_key, "logGroupName": data.log_group_name, "region": data.region})
    else:
        return add(tenant_id=tenant_id, project_id=project_id, aws_access_key_id=data.aws_access_key_id, aws_secret_access_key=data.aws_secret_access_key, log_group_name=data.log_group_name, region=data.region)
