# 这段代码实现了与 Elasticsearch 的集成管理功能。它提供了添加、更新、删除和获取 Elasticsearch 集成信息的功能，并使用 log_tools 模块在系统数据库中进行这些操作。
# 此外，代码中还包含了与 Elasticsearch 服务器通信的功能，用于验证连接和测试服务器的可用性。
import logging

from elasticsearch import Elasticsearch

from chalicelib.core import log_tools
from schemas import schemas

logger = logging.getLogger(__name__)
# 定义集成类型为 "elasticsearch"
IN_TY = "elasticsearch"

# 函数：get_all
# 功能：获取指定租户下所有 Elasticsearch 集成的日志信息。
# 参数：
# - tenant_id: 租户ID，用于标识集成操作的租户。
# 返回值：
# - 返回包含所有 Elasticsearch 集成日志信息的列表。
def get_all(tenant_id):
    return log_tools.get_all_by_tenant(tenant_id=tenant_id, integration=IN_TY)

# 函数：get
# 功能：获取指定项目的 Elasticsearch 集成日志信息。
# 参数：
# - project_id: 项目ID，用于标识具体的项目。
# 返回值：
# - 返回包含指定项目 Elasticsearch 集成日志信息的字典。
def get(project_id):
    return log_tools.get(project_id=project_id, integration=IN_TY)

# 函数：update
# 功能：更新指定项目的 Elasticsearch 集成信息。
# 参数：
# - tenant_id: 租户ID，用于标识集成操作的租户。
# - project_id: 项目ID，用于标识具体的项目。
# - changes: 包含需要更新的信息的字典（例如主机地址、API密钥ID、API密钥、索引和端口）。
# 返回值：
# - 返回更新后的集成信息。
def update(tenant_id, project_id, changes):
    options = {}

    if "host" in changes:
        options["host"] = changes["host"]
    if "apiKeyId" in changes:
        options["apiKeyId"] = changes["apiKeyId"]
    if "apiKey" in changes:
        options["apiKey"] = changes["apiKey"]
    if "indexes" in changes:
        options["indexes"] = changes["indexes"]
    if "port" in changes:
        options["port"] = changes["port"]

    return log_tools.edit(project_id=project_id, integration=IN_TY, changes=options)

# 函数：add
# 功能：为指定项目添加新的 Elasticsearch 集成信息。
# 参数：
# - tenant_id: 租户ID，用于标识集成操作的租户。
# - project_id: 项目ID，用于标识具体的项目。
# - host: Elasticsearch 主机地址。
# - api_key_id: Elasticsearch API 密钥ID。
# - api_key: Elasticsearch API 密钥。
# - indexes: 索引名称列表。
# - port: Elasticsearch 服务端口。
# 返回值：
# - 返回添加后的集成信息。
def add(tenant_id, project_id, host, api_key_id, api_key, indexes, port):
    options = {
        "host": host, "apiKeyId": api_key_id, "apiKey": api_key, "indexes": indexes, "port": port
    }
    return log_tools.add(project_id=project_id, integration=IN_TY, options=options)

# 函数：delete
# 功能：删除指定项目的 Elasticsearch 集成信息。
# 参数：
# - tenant_id: 租户ID，用于标识集成操作的租户。
# - project_id: 项目ID，用于标识具体的项目。
# 返回值：
# - 返回删除状态信息
def delete(tenant_id, project_id):
    return log_tools.delete(project_id=project_id, integration=IN_TY)

# 函数：add_edit
# 功能：根据传入的数据添加或更新指定项目的 Elasticsearch 集成信息。
# 参数：
# - tenant_id: 租户ID，用于标识集成操作的租户。
# - project_id: 项目ID，用于标识具体的项目。
# - data: 包含 Elasticsearch 集成信息的架构实例（schemas.IntegrationElasticsearchSchema）。
# 返回值：
# - 返回添加或更新后的集成信息。
def add_edit(tenant_id, project_id, data: schemas.IntegrationElasticsearchSchema):
    s = get(project_id)
    if s is not None:
        return update(tenant_id=tenant_id, project_id=project_id,
                      changes={"host": data.host, "apiKeyId": data.api_key_id, "apiKey": data.api_key,
                               "indexes": data.indexes, "port": data.port})
    else:
        return add(tenant_id=tenant_id, project_id=project_id,
                   host=data.host, api_key=data.api_key, api_key_id=data.api_key_id,
                   indexes=data.indexes, port=data.port)

# 函数：__get_es_client
# 功能：创建并返回一个 Elasticsearch 客户端实例，用于连接到指定的 Elasticsearch 服务器。
# 参数：
# - host: Elasticsearch 主机地址。
# - port: Elasticsearch 服务端口。
# - api_key_id: Elasticsearch API 密钥ID。
# - api_key: Elasticsearch API 密钥。
# - use_ssl: 是否使用 SSL 连接，默认为 False。
# - timeout: 请求超时时间，默认为 15 秒。
# 返回值：
# - 返回一个 Elasticsearch 客户端实例，如果连接失败则返回 None。
def __get_es_client(host, port, api_key_id, api_key, use_ssl=False, timeout=15):
    scheme = "http" if host.startswith("http") else "https"
    host = host.replace("http://", "").replace("https://", "")
    try:
        args = {
            "hosts": [{"host": host, "port": port, "scheme": scheme}],
            "verify_certs": use_ssl,
            "request_timeout": timeout,
            "api_key": api_key
        }
        es = Elasticsearch(
            **args
        )
        r = es.ping()
        if not r and not use_ssl:
            return __get_es_client(host, port, api_key_id, api_key, use_ssl=True, timeout=timeout)
        if not r:
            return None
    except Exception as err:
        logger.error("================exception connecting to ES host:")
        logger.exception(err)
        return None
    return es

# 函数：ping
# 功能：测试与指定 Elasticsearch 服务器的连接，并返回连接状态。
# 参数：
# - tenant_id: 租户ID，用于标识集成操作的租户。
# - data: 包含测试连接所需信息的架构实例（schemas.IntegrationElasticsearchTestSchema）。
# 返回值：
# - 返回包含连接状态的字典，键为 "state"，值为 True 表示连接成功，False 表示失败。
def ping(tenant_id, data: schemas.IntegrationElasticsearchTestSchema):
    es = __get_es_client(data.host, data.port, data.api_key_id, data.api_key, timeout=3)
    if es is None:
        return {"state": False}
    return {"state": es.ping()}


# 这段代码实现了与 Elasticsearch 的集成管理功能，使得系统能够通过添加、更新、删除和获取集成信息，与 Elasticsearch 服务器进行连接和通信。
# 这些功能有助于确保集成的有效性和可靠性，同时通过 ping 函数提供了测试连接的能力，从而帮助用户及时发现并解决连接问题。
