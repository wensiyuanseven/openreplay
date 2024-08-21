from chalicelib.core import integration_github, integration_jira_cloud
from chalicelib.utils import pg_client

# 这段代码定义了一些用于管理和获取用户与第三方问题跟踪工具（如 GitHub 和 JIRA）集成信息的函数。代码通过查询数据库来检查用户是否已与这些工具进行了集成，并根据这些集成状态来返回相关信息或实例。
# 支持的工具列表，目前包含 GitHub 和 JIRA。
SUPPORTED_TOOLS = [integration_github.PROVIDER, integration_jira_cloud.PROVIDER]


# 函数：get_available_integrations
# 功能：获取用户可用的集成工具，检查用户是否已集成了 GitHub 或 JIRA。
# 参数：
# - user_id: 用户ID，用于标识进行集成操作的用户。
# 返回值：
# - 返回包含 GitHub 和 JIRA 集成状态的字典
def get_available_integrations(user_id):
    with pg_client.PostgresClient() as cur:
        cur.execute(
            cur.mogrify(
                f"""\
                    SELECT EXISTS((SELECT 1
                               FROM public.oauth_authentication
                               WHERE user_id = %(user_id)s
                                 AND provider = 'github')) AS github,
                           EXISTS((SELECT 1
                                   FROM public.jira_cloud
                                   WHERE user_id = %(user_id)s))       AS jira;""",
                {"user_id": user_id},
            )
        )
        current_integrations = cur.fetchone()
    return dict(current_integrations)


# 函数：__get_default_integration
# 功能：获取用户的默认集成工具，如果 GitHub 集成存在，则返回 GitHub，否则返回 JIRA。
# 参数：
# - user_id: 用户ID，用于标识进行集成操作的用户。
# 返回值：
# - 返回默认的集成工具（GitHub 或 JIRA），如果没有集成则返回 None。
def __get_default_integration(user_id):
    current_integrations = get_available_integrations(user_id)
    return integration_github.PROVIDER if current_integrations["github"] else integration_jira_cloud.PROVIDER if current_integrations["jira"] else None


# 函数：get_integration
# 功能：根据用户请求获取指定的集成工具实例，或返回错误信息。
# 参数：
# - tenant_id: 租户ID，用于标识集成操作的租户。
# - user_id: 用户ID，用于标识进行集成操作的用户。
# - tool: 指定的集成工具名称（可选）。如果未指定，将使用默认工具。
# - for_delete: 标志是否用于删除操作（可选），默认为 False。
# 返回值：
# - 如果成功，返回 (None, 集成实例)；如果失败，返回 (错误信息, None)。
def get_integration(tenant_id, user_id, tool=None, for_delete=False):
    if tool is None:
        tool = __get_default_integration(user_id=user_id)
    if tool is None:
        return {"errors": [f"no issue tracking tool found"]}, None
    tool = tool.upper()
    if tool not in SUPPORTED_TOOLS:
        return {"errors": [f"issue tracking tool not supported yet, available: {SUPPORTED_TOOLS}"]}, None
    if tool == integration_jira_cloud.PROVIDER:
        integration = integration_jira_cloud.JIRAIntegration(tenant_id=tenant_id, user_id=user_id)
        if not for_delete and integration.integration is not None and not integration.integration.get("valid", True):
            return {"errors": ["JIRA: connexion issue/unauthorized"]}, integration
        return None, integration
    elif tool == integration_github.PROVIDER:
        return None, integration_github.GitHubIntegration(tenant_id=tenant_id, user_id=user_id)
    return {"errors": ["lost integration"]}, None


# 代码解析
# SUPPORTED_TOOLS 列表：

# 该列表定义了当前支持的第三方工具，即 GitHub 和 JIRA。这个列表用于确保用户请求的工具在系统中受支持。
# get_available_integrations 函数：

# 该函数查询数据库，以确定指定用户是否已与 GitHub 和 JIRA 进行了集成。返回的字典中包含两个键：github 和 jira，它们的值为布尔值，指示相应集成是否存在。
# __get_default_integration 函数：

# 这个私有函数通过检查用户的可用集成，返回默认的集成工具。如果用户已集成 GitHub，则返回 GitHub；否则返回 JIRA。如果两者都没有集成，则返回 None。
# get_integration 函数：

# 这个函数是获取集成工具实例的核心逻辑。它首先确定要使用的工具，如果工具未指定，则使用默认工具。
# 然后检查工具是否在支持的列表中。如果工具支持，函数会创建相应的集成实例（GitHub 或 JIRA）。
# 如果工具为 JIRA，还会检查其集成是否有效（例如，是否有连接问题或未经授权）。
# 最后，函数返回集成实例或错误信息。
# 该代码提供了一种机制，用于管理用户与 GitHub 和 JIRA 这两个主要问题跟踪工具的集成。通过检查集成状态、获取默认集成和返回适当的实例，代码确保了系统能够灵活而有效地处理这些第三方集成。同时，代码中还包含了对集成有效性和支持性检查的逻辑，使得集成过程更加稳健。
