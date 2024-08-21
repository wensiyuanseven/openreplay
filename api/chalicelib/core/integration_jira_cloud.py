# 这段代码定义了一个名为 JIRAIntegration 的类，该类继承自 BaseIntegration，用于处理 JIRA Cloud 的集成管理。
# 这个类主要负责管理 JIRA Cloud 的 OAuth 认证信息，并通过与 JIRA Cloud API 交互来实现任务（Issue）的管理功能。此外，还提供了对敏感信息（如 token）的模糊处理和对集成信息的增删改查功能。
import schemas
from chalicelib.core import integration_base
from chalicelib.core.integration_jira_cloud_issue import JIRACloudIntegrationIssue
from chalicelib.utils import pg_client, helper

PROVIDER = schemas.IntegrationType.jira


# 工具函数：obfuscate_string
# 功能：对字符串进行模糊处理，以隐藏敏感信息。
# 参数：
# - string: 要模糊处理的字符串。
# 返回值：
# - 返回模糊处理后的字符串，保留最后四个字符
def obfuscate_string(string):
    return "*" * (len(string) - 4) + string[-4:]


# 定义 JIRA 集成类，继承自 BaseIntegration。
class JIRAIntegration(integration_base.BaseIntegration):
    # 初始化函数，设置租户ID和用户ID，并调用父类构造函数。
    # 参数：
    # - tenant_id: 租户ID，用于标识集成操作的租户。
    # - user_id: 用户ID，用于标识进行集成操作的用户。
    def __init__(self, tenant_id, user_id):
        self.__tenant_id = tenant_id
        # TODO: enable super-constructor when OAuth is done
        # super(JIRAIntegration, self).__init__(jwt, user_id, JIRACloudIntegrationProxy)
        self._issue_handler = None
        self._user_id = user_id
        self.integration = self.get()

    # 静态方法：__validate
    # 功能：验证给定的数据对象是否包含有效的 JIRA URL。
    # 参数：
    # - data: 包含待验证数据的字典。
    @staticmethod
    def __validate(data):
        data["valid"] = JIRAIntegration.__is_valid_url(data["url"])

    # 静态方法：__is_valid_url
    # 功能：判断给定的 URL 是否为有效的 JIRA Cloud URL。
    # 参数：
    # - url: 要验证的 URL 字符串。
    # 返回值：
    # - 如果 URL 以 'atlassian.net' 结尾，则返回 True；否则返回 False。
    @staticmethod
    def __is_valid_url(url):
        return url.endswith("atlassian.net") or url.endswith("atlassian.net/")

    # 属性：provider
    # 功能：返回集成提供商的名称。
    @property
    def provider(self):
        return PROVIDER

    # 属性：issue_handler
    # 功能：返回 JIRACloudIntegrationIssue 对象，用于处理与 JIRA 相关的问题管理。
    # 如果 URL 有效且 issue_handler 尚未初始化，则尝试创建 JIRACloudIntegrationIssue 实例。
    @property
    def issue_handler(self):
        if JIRAIntegration.__is_valid_url(self.integration["url"]) and self._issue_handler is None:
            try:
                self._issue_handler = JIRACloudIntegrationIssue(token=self.integration["token"], username=self.integration["username"], url=self.integration["url"])
            except Exception as e:
                self._issue_handler = None
                self.integration["valid"] = False
        return self._issue_handler

    # 函数：get
    # 功能：从数据库中获取当前用户的 JIRA Cloud 认证信息。
    # 返回值：
    # - 返回包含用户名、token 和 URL 的字典，如果未找到则返回 None。
    # TODO: remove this once jira-oauth is done
    def get(self):
        with pg_client.PostgresClient() as cur:
            cur.execute(
                cur.mogrify(
                    """SELECT username, token, url
                        FROM public.jira_cloud 
                        WHERE user_id=%(user_id)s;""",
                    {"user_id": self._user_id},
                )
            )
            data = helper.dict_to_camel_case(cur.fetchone())

        if data is None:
            return
        JIRAIntegration.__validate(data)
        return data

    # 函数：get_obfuscated
    # 功能：获取模糊处理后的集成信息。
    # 返回值：
    # - 返回包含模糊处理的 token 和其他信息的字典。
    def get_obfuscated(self):
        if self.integration is None:
            return None
        integration = dict(self.integration)
        integration["token"] = obfuscate_string(self.integration["token"])
        integration["provider"] = self.provider.lower()
        return integration

    # 函数：update
    # 功能：更新数据库中的 JIRA 认证信息。
    # 参数：
    # - changes: 包含要更新的数据的字典。
    # - obfuscate: 是否对返回的 token 进行模糊处理，默认为 False。
    # 返回值：
    # - 返回更新后的认证信息，可能包含模糊处理后的 token。F
    def update(self, changes, obfuscate=False):
        with pg_client.PostgresClient() as cur:
            sub_query = [f"{helper.key_to_snake_case(k)} = %({k})s" for k in changes.keys()]
            cur.execute(
                cur.mogrify(
                    f"""\
                        UPDATE public.jira_cloud
                        SET {','.join(sub_query)}
                        WHERE user_id=%(user_id)s
                        RETURNING username, token, url;""",
                    {"user_id": self._user_id, **changes},
                )
            )
            w = helper.dict_to_camel_case(cur.fetchone())
            JIRAIntegration.__validate(w)
            if obfuscate:
                w["token"] = obfuscate_string(w["token"])
        return w

    # TODO: make this generic for all issue tracking integrations
    def _add(self, data):
        print("a pretty defined abstract method")
        return

    # 函数：add
    # 功能：添加新的 JIRA 认证信息到数据库。
    # 参数：
    # - username: JIRA 用户名。
    # - token: OAuth 令牌。
    # - url: JIRA 实例的 URL。
    # - obfuscate: 是否对返回的 token 进行模糊处理，默认为 False。
    # 返回值：
    # - 返回包含添加的认证信息，可能包含模糊处理后的 token。
    def add(self, username, token, url, obfuscate=False):
        with pg_client.PostgresClient() as cur:
            cur.execute(
                cur.mogrify(
                    """\
                        INSERT INTO public.jira_cloud(username, token, user_id,url)
                        VALUES (%(username)s, %(token)s, %(user_id)s,%(url)s)
                        RETURNING  username, token, url;""",
                    {"user_id": self._user_id, "username": username, "token": token, "url": url},
                )
            )
            w = helper.dict_to_camel_case(cur.fetchone())
            JIRAIntegration.__validate(w)
            if obfuscate:
                w["token"] = obfuscate_string(w["token"])

        return w

    # 函数：delete
    # 功能：删除当前用户的 JIRA 认证信息。
    # 返回值：
    # - 返回包含删除状态的字典。
    def delete(self):
        with pg_client.PostgresClient() as cur:
            cur.execute(
                cur.mogrify(
                    """\
                        DELETE FROM public.jira_cloud
                        WHERE user_id=%(user_id)s;""",
                    {"user_id": self._user_id},
                )
            )
            return {"state": "success"}

    # 函数：add_edit
    # 功能：根据提供的数据添加或编辑 JIRA 认证信息。
    # 参数：
    # - data: schemas.IssueTrackingJiraSchema 类型，包含认证信息。
    # 返回值：
    # - 返回添加或更新后的认证信息，可能包含模糊处理后的 token。
    def add_edit(self, data: schemas.IssueTrackingJiraSchema):
        if self.integration is not None:
            return self.update(changes={"username": data.username, "token": data.token if len(data.token) > 0 and data.token.find("***") == -1 else self.integration.token, "url": str(data.url)}, obfuscate=True)
        else:
            return self.add(username=data.username, token=data.token, url=str(data.url), obfuscate=True)
