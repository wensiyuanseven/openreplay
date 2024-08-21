# 这段代码定义了一个 GitHubIntegration 类，该类继承自 BaseIntegration 类，用于处理 GitHub 集成的认证和问题管理功能。该类实现了从数据库中获取、添加、更新和删除 GitHub 集成的 OAuth 认证信息，并提供了模糊化处理认证令牌的方法。
# 它还与 GithubIntegrationIssue 类结合，实现了与 GitHub 的问题管理集成。
# 代码解析
# GitHubIntegration 类：

# 这个类继承了 BaseIntegration，并具体实现了与 GitHub 的集成操作。它负责管理用户的 GitHub OAuth 认证信息，并提供了操作这些信息的接口。
# get_obfuscated 方法：

# 这个方法获取当前用户的 GitHub 认证信息，并对认证令牌进行模糊处理，以隐藏敏感数据。模糊化后的令牌和供应商信息一起返回。
# update 方法：

# 该方法允许更新数据库中存储的 OAuth 认证信息。通过传入一个包含更改数据的字典，方法会更新对应字段的值。如果指定了 obfuscate=True，更新后的令牌将被模糊化处理。
# add 方法：

# 这个方法用于将新的 OAuth 令牌添加到数据库中，并返回插入的数据。如果 obfuscate=True，返回的令牌将被模糊化处理。
# delete 方法：

# 从数据库中删除用户的 GitHub OAuth 认证信息。
# add_edit 方法：

# 该方法检查用户是否已经有 OAuth 认证信息，如果有则更新信息，否则添加新的认证信息。该方法提供了处理 OAuth 令牌的灵活性，并且在更新时也支持模糊化处理。
# 总结
# GitHubIntegration 类是一个专门用于处理 GitHub 集成的实现类。它管理 OAuth 认证信息，支持增删改查等操作，并且可以对敏感数据进行模糊处理。这使得它在确保安全的同时，能够有效地与 GitHub 进行集成操作。
import schemas
from chalicelib.core import integration_base
from chalicelib.core.integration_github_issue import GithubIntegrationIssue
from chalicelib.utils import pg_client, helper

PROVIDER = schemas.IntegrationType.github


# 定义 GitHub 集成的实现类，继承自 BaseIntegration。
class GitHubIntegration(integration_base.BaseIntegration):
    # 初始化函数，设置租户ID和用户ID，并调用父类构造函数初始化问题处理类。
    # 参数：
    # - tenant_id: 租户ID，用于标识集成操作的租户。
    # - user_id: 用户ID，用于标识进行集成操作的用户。
    def __init__(self, tenant_id, user_id):
        self.__tenant_id = tenant_id
        super(GitHubIntegration, self).__init__(user_id=user_id, ISSUE_CLASS=GithubIntegrationIssue)

    # 属性：provider
    # 功能：返回集成提供商的名称。
    @property
    def provider(self):
        return PROVIDER

    # 属性：issue_handler
    # 功能：返回问题处理对象。
    @property
    def issue_handler(self):
        return self._issue_handler

    # 函数：get_obfuscated
    # 功能：获取模糊化处理后的集成信息。
    # 返回值：
    # - 返回包含模糊化令牌的字典，如果未配置令牌则返回 None。
    def get_obfuscated(self):
        integration = self.get()
        if integration is None:
            return None
        return {"token": helper.obfuscate(text=integration["token"]), "provider": self.provider.lower()}

    # 函数：update
    # 功能：更新集成的 OAuth 认证信息。
    # 参数：
    # - changes: 包含要更新的数据的字典。
    # - obfuscate: 是否对返回的令牌进行模糊处理，默认为 False。
    # 返回值：
    # - 返回更新后的认证信息，可能包含模糊化处理后的令牌
    def update(self, changes, obfuscate=False):
        with pg_client.PostgresClient() as cur:
            sub_query = [f"{helper.key_to_snake_case(k)} = %({k})s" for k in changes.keys()]
            cur.execute(
                cur.mogrify(
                    f"""\
                        UPDATE public.oauth_authentication
                        SET {','.join(sub_query)}
                        WHERE user_id=%(user_id)s
                        RETURNING token;""",
                    {"user_id": self._user_id, **changes},
                )
            )
            w = helper.dict_to_camel_case(cur.fetchone())
            if w and w.get("token") and obfuscate:
                w["token"] = helper.obfuscate(w["token"])
            return w

    # 函数：_add
    # 功能：添加新的集成信息到数据库（未实现，在子类中应覆盖实现）。F
    def _add(self, data):
        pass

    # 函数：add
    # 功能：将新的 GitHub OAuth 令牌添加到数据库。
    # 参数：
    # - token: 要添加的 OAuth 令牌。
    # - obfuscate: 是否对返回的令牌进行模糊处理，默认为 False。
    # 返回值：
    # - 返回包含添加的认证信息，可能包含模糊化处理后的令牌
    def add(self, token, obfuscate=False):
        with pg_client.PostgresClient() as cur:
            cur.execute(
                cur.mogrify(
                    """\
                        INSERT INTO public.oauth_authentication(user_id, provider, provider_user_id, token)
                        VALUES(%(user_id)s, 'github', '', %(token)s)
                        RETURNING token;""",
                    {"user_id": self._user_id, "token": token},
                )
            )
            w = helper.dict_to_camel_case(cur.fetchone())
            if w and w.get("token") and obfuscate:
                w["token"] = helper.obfuscate(w["token"])
            return w

    # 函数：delete
    # 功能：从数据库中删除用户的 GitHub OAuth 认证信息。
    # 返回值：
    # - 返回删除状态的字典
    # TODO: make a revoke token call
    def delete(self):
        with pg_client.PostgresClient() as cur:
            cur.execute(
                cur.mogrify(
                    """\
                        DELETE FROM public.oauth_authentication
                        WHERE user_id=%(user_id)s AND provider=%(provider)s;""",
                    {"user_id": self._user_id, "provider": self.provider.lower()},
                )
            )
            return {"state": "success"}

    # 函数：add_edit
    # 功能：添加或更新 GitHub OAuth 认证信息。
    # 参数：
    # - data: schemas.IssueTrackingGithubSchema 类型，包含 OAuth 令牌信息。
    # 返回值：
    # - 返回添加或更新后的认证信息，可能包含模糊化处理后的令牌。
    def add_edit(self, data: schemas.IssueTrackingGithubSchema):
        s = self.get()
        if s is not None:
            return self.update(changes={"token": data.token if len(data.token) > 0 and data.token.find("***") == -1 else s.token}, obfuscate=True)
        else:
            return self.add(token=data.token, obfuscate=True)
