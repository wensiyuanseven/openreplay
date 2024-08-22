# 此代码定义了一系列与用户认证、项目配置、数据过滤、警报和集成等相关的 Pydantic 模型。这些模型被用来验证和处理 Web 应用程序中的数据请求和响应。
# 具体来说，代码片段涵盖了用户注册、登录、密码管理、项目设置、通知、错误处理、数据过滤和分析等功能。
from typing import Annotated, Any
from typing import Optional, List, Union, Literal

from pydantic import Field, EmailStr, HttpUrl, SecretStr, AnyHttpUrl, validator
from pydantic import field_validator, model_validator, computed_field

from chalicelib.utils.TimeUTC import TimeUTC
from .overrides import BaseModel, Enum, ORUnion
from .transformers_validators import transform_email, remove_whitespace, remove_duplicate_values, single_to_list, \
    force_is_event, NAME_PATTERN, int_to_string
from pydantic.functional_validators import BeforeValidator

# 功能描述：
# 将旧版本的过滤器类型转换为新的过滤器类型，以便支持新系统中的数据过滤。
# 参数：
# cls: 当前类对象。
# values (字典类型): 包含要转换的过滤器类型和值的字典。
# 返回值：
# values (字典类型): 转换后的过滤器类型和值。
def transform_old_filter_type(cls, values):
    if values.get("type") is None:
        return values
    values["type"] = {
        # filters
        "USEROS": FilterType.user_os.value,
        "USERBROWSER": FilterType.user_browser.value,
        "USERDEVICE": FilterType.user_device.value,
        "USERCOUNTRY": FilterType.user_country.value,
        "USERID": FilterType.user_id.value,
        "USERANONYMOUSID": FilterType.user_anonymous_id.value,
        "REFERRER": FilterType.referrer.value,
        "REVID": FilterType.rev_id.value,
        "USEROS_IOS": FilterType.user_os_mobile.value,
        "USERDEVICE_IOS": FilterType.user_device_mobile.value,
        "USERCOUNTRY_IOS": FilterType.user_country_mobile.value,
        "USERID_IOS": FilterType.user_id_mobile.value,
        "USERANONYMOUSID_IOS": FilterType.user_anonymous_id_mobile.value,
        "REVID_IOS": FilterType.rev_id_mobile.value,
        "DURATION": FilterType.duration.value,
        "PLATFORM": FilterType.platform.value,
        "METADATA": FilterType.metadata.value,
        "ISSUE": FilterType.issue.value,
        "EVENTS_COUNT": FilterType.events_count.value,
        "UTM_SOURCE": FilterType.utm_source.value,
        "UTM_MEDIUM": FilterType.utm_medium.value,
        "UTM_CAMPAIGN": FilterType.utm_campaign.value,
        # events:
        "CLICK": EventType.click.value,
        "INPUT": EventType.input.value,
        "LOCATION": EventType.location.value,
        "CUSTOM": EventType.custom.value,
        "REQUEST": EventType.request.value,
        "FETCH": EventType.request_details.value,
        "GRAPHQL": EventType.graphql.value,
        "STATEACTION": EventType.state_action.value,
        "ERROR": EventType.error.value,
        "CLICK_IOS": EventType.click_mobile.value,
        "INPUT_IOS": EventType.input_mobile.value,
        "VIEW_IOS": EventType.view_mobile.value,
        "CUSTOM_IOS": EventType.custom_mobile.value,
        "REQUEST_IOS": EventType.request_mobile.value,
        "ERROR_IOS": EventType.error_mobile.value,
        "DOM_COMPLETE": PerformanceEventType.location_dom_complete.value,
        "LARGEST_CONTENTFUL_PAINT_TIME": PerformanceEventType.location_largest_contentful_paint_time.value,
        "TTFB": PerformanceEventType.location_ttfb.value,
        "AVG_CPU_LOAD": PerformanceEventType.location_avg_cpu_load.value,
        "AVG_MEMORY_USAGE": PerformanceEventType.location_avg_memory_usage.value,
        "FETCH_FAILED": PerformanceEventType.fetch_failed.value,
    }.get(values["type"], values["type"])
    return values

# 功能描述：
# 定义了一个包含 Google reCAPTCHA 验证响应的基本模型。

# 属性：
# g_recaptcha_response (可选，字符串类型): Google reCAPTCHA 验证响应，别名为 g-recaptcha-response。
class _GRecaptcha(BaseModel):
    g_recaptcha_response: Optional[str] = Field(default=None, alias='g-recaptcha-response')

# 用于验证用户登录数据的模型，继承自 _GRecaptcha 基本模型。

# 属性：
# email (必需，EmailStr 类型): 用户的电子邮件地址。
# password (必需，SecretStr 类型): 用户的密码。
# _transform_email (方法): 在字段验证前，使用 transform_email 函数对电子邮件地址进行处理。
class UserLoginSchema(_GRecaptcha):
    email: EmailStr = Field(...)
    password: SecretStr = Field(...)

    _transform_email = field_validator('email', mode='before')(transform_email)

# 用于验证用户注册数据的模型，继承自 UserLoginSchema 模型，并增加了 fullname 和 organizationName 字段。
# 属性：
# fullname (必需，字符串类型): 用户的全名，最小长度为 1，必须符合 NAME_PATTERN 正则表达式。
# organizationName (必需，字符串类型): 用户的组织名称，最小长度为 1，必须符合 NAME_PATTERN 正则表达式。
# _transform_fullname (方法): 在字段验证前，使用 remove_whitespace 函数对全名进行处理。
# _transform_organizationName (方法): 在字段验证前，使用 remove_whitespace 函数对组织名称进行处理。
class UserSignupSchema(UserLoginSchema):
    fullname: str = Field(..., min_length=1, pattern=NAME_PATTERN)
    organizationName: str = Field(..., min_length=1, pattern=NAME_PATTERN)

    _transform_fullname = field_validator('fullname', mode='before')(remove_whitespace)
    _transform_organizationName = field_validator('organizationName', mode='before')(remove_whitespace)


# 功能描述：
# 用于验证编辑账户数据的模型，允许用户更新其姓名、租户名称和退出选项。
# 属性：
# name (可选，字符串类型): 用户的姓名，必须符合 NAME_PATTERN 正则表达式。
# tenantName (可选，字符串类型): 用户的租户名称，必须符合 NAME_PATTERN 正则表达式。
# opt_out (可选，布尔类型): 用户是否选择退出某些功能。
# _transform_name (方法): 在字段验证前，使用 remove_whitespace 函数对姓名进行处理。
# _transform_tenantName (方法): 在字段验证前，使用 remove_whitespace 函数对租户名称进行处理。
class EditAccountSchema(BaseModel):
    name: Optional[str] = Field(default=None, pattern=NAME_PATTERN)
    tenantName: Optional[str] = Field(default=None, pattern=NAME_PATTERN)
    opt_out: Optional[bool] = Field(default=None)

    _transform_name = field_validator('name', mode='before')(remove_whitespace)
    _transform_tenantName = field_validator('tenantName', mode='before')(remove_whitespace)

# 功能描述：
# 用于验证忘记密码请求的数据模型，继承自 _GRecaptcha 基本模型。

# 属性：
# email (必需，EmailStr 类型): 用户的电子邮件地址。
# _transform_email (方法): 在字段验证前，使用 transform_email 函数对电子邮件地址进行处理。
class ForgetPasswordPayloadSchema(_GRecaptcha):
    email: EmailStr = Field(...)

    _transform_email = field_validator('email', mode='before')(transform_email)

# 功能描述：
# 用于验证用户密码修改请求的数据模型。

# 属性：
# old_password (必需，SecretStr 类型): 用户的旧密码。
# new_password (必需，SecretStr 类型): 用户的新密码。
class EditUserPasswordSchema(BaseModel):
    old_password: SecretStr = Field(...)
    new_password: SecretStr = Field(...)

# 功能描述：
# 用于创建项目的数据模型，包含项目名称和平台类型。

# 属性：
# name (字符串类型，默认值 "my first project"): 项目名称，必须符合 NAME_PATTERN 正则表达式。
# platform (Literal["web", "ios"] 类型，默认值 "web"): 项目所属的平台类型，可选值为 "web" 或 "ios"。
# _transform_name (方法): 在字段验证前，使用 remove_whitespace 函数去除项目名称中的多余空白。
class CreateProjectSchema(BaseModel):
    name: str = Field(default="my first project", pattern=NAME_PATTERN)
    platform: Literal["web", "ios"] = Field(default="web")

    _transform_name = field_validator('name', mode='before')(remove_whitespace)

# 功能描述：
# 用于表示当前项目上下文的数据模型，包含项目的基本信息。

# 属性：
# project_id (必需，整数类型，值必须大于0): 项目的唯一标识符。
# project_key (必需，字符串类型): 项目的密钥或标识符。
# name (必需，字符串类型): 项目名称。
# platform (Literal["web", "ios"] 类型): 项目所属的平台类型，可选值为 "web" 或 "ios"。
class CurrentProjectContext(BaseModel):
    project_id: int = Field(..., gt=0)
    project_key: str = Field(...)
    name: str = Field(...)
    platform: Literal["web", "ios"] = Field(...)

# CurrentAPIContext(BaseModel)
# 功能描述：
# 用于表示当前 API 上下文的数据模型，包含租户信息和当前项目的上下文。

# 属性：
# tenant_id (必需，整数类型): 租户的唯一标识符。
# project (Optional[CurrentProjectContext] 类型，默认值为 None): 当前项目的上下文信息。
class CurrentAPIContext(BaseModel):
    tenant_id: int = Field(...)
    project: Optional[CurrentProjectContext] = Field(default=None)

# 用于表示当前用户上下文的数据模型，继承自 CurrentAPIContext，并添加了用户信息和角色信息。

# 属性：
# user_id (必需，整数类型): 用户的唯一标识符。
# email (必需，EmailStr 类型): 用户的电子邮件地址。
# role (必需，字符串类型): 用户在系统中的角色（如 "owner", "admin", "member" 等）。
# _transform_email (方法): 在字段验证前，使用 transform_email 函数处理电子邮件地址。
# is_owner (computed_field，布尔类型): 计算属性，返回用户是否为项目所有者。
# is_admin (computed_field，布尔类型): 计算属性，返回用户是否为管理员。
# is_member (computed_field，布尔类型): 计算属性，返回用户是否为普通成员。
class CurrentContext(CurrentAPIContext):
    user_id: int = Field(...)
    email: EmailStr = Field(...)
    role: str = Field(...)

    _transform_email = field_validator('email', mode='before')(transform_email)

    @computed_field
    @property
    def is_owner(self) -> bool:
        return self.role == "owner"

    @computed_field
    @property
    def is_admin(self) -> bool:
        return self.role == "admin"

    @computed_field
    @property
    def is_member(self) -> bool:
        return self.role == "member"

# 用于添加协作关系的数据模型，包含协作名称和 URL。

# 属性：
# name (必需，字符串类型): 协作名称，必须符合 NAME_PATTERN 正则表达式。
# url (必需，HttpUrl 类型): 协作对象的 URL 地址。
# _transform_name (方法): 在字段验证前，使用 remove_whitespace 函数去除协作名称中的多余空白。
# _transform_url (方法): 在字段验证前，使用 remove_whitespace 函数去除 URL 中的多余空白。
class AddCollaborationSchema(BaseModel):
    name: str = Field(..., pattern=NAME_PATTERN)
    url: HttpUrl = Field(...)

    _transform_name = field_validator('name', mode='before')(remove_whitespace)
    _transform_url = field_validator('url', mode='before')(remove_whitespace)

# 用于编辑协作关系的数据模型，继承自 AddCollaborationSchema，允许选择性更新协作名称。

# 属性：
# name (Optional[str] 类型，默认值为 None): 可选的协作名称，必须符合 NAME_PATTERN 正则表达式。
class EditCollaborationSchema(AddCollaborationSchema):
    name: Optional[str] = Field(default=None, pattern=NAME_PATTERN)

# 用于表示带有时间戳的数据模型，包含开始和结束时间的验证逻辑。

# 属性：
# startTimestamp (Optional[int] 类型，默认值为 None): 开始时间的时间戳。
# endTimestamp (Optional[int] 类型，默认值为 None): 结束时间的时间戳。
# transform_time (方法): 在模型验证前，将 startDate 和 endDate 转换为相应的时间戳。
# __time_validator (方法): 在模型验证后，确保时间戳符合逻辑顺序，即开始时间必须小于等于结束时间。
class _TimedSchema(BaseModel):
    startTimestamp: int = Field(default=None)
    endTimestamp: int = Field(default=None)

    @model_validator(mode='before')
    def transform_time(cls, values):
        if values.get("startTimestamp") is None and values.get("startDate") is not None:
            values["startTimestamp"] = values["startDate"]
        if values.get("endTimestamp") is None and values.get("endDate") is not None:
            values["endTimestamp"] = values["endDate"]
        return values

    @model_validator(mode='after')
    def __time_validator(cls, values):
        if values.startTimestamp is not None:
            assert 0 <= values.startTimestamp, "startTimestamp must be greater or equal to 0"
        if values.endTimestamp is not None:
            assert 0 <= values.endTimestamp, "endTimestamp must be greater or equal to 0"
        if values.startTimestamp is not None and values.endTimestamp is not None:
            assert values.startTimestamp <= values.endTimestamp, \
                "endTimestamp must be greater or equal to startTimestamp"
        return values

# 用于通知视图的数据模型，继承自 _TimedSchema，并添加了通知 ID 列表。

# 属性：
# ids (List[int] 类型，默认值为 []): 通知的 ID 列表。
# startTimestamp (Optional[int] 类型，默认值为 None): 开始时间的时间戳。
# endTimestamp (Optional[int] 类型，默认值为 None): 结束时间的时间戳。
class NotificationsViewSchema(_TimedSchema):
    ids: List[int] = Field(default=[])
    startTimestamp: Optional[int] = Field(default=None)
    endTimestamp: Optional[int] = Field(default=None)

# 功能描述：
# 用于集成 Issue 跟踪系统的数据模型，包含系统的访问令牌。

# 属性：
# token (必需，字符串类型): 用于访问 Issue 跟踪系统的令牌。
class IssueTrackingIntegration(BaseModel):
    token: str = Field(...)

# 功能描述：
# 用于 GitHub Issue 跟踪集成的数据模型，继承自 IssueTrackingIntegration。
class IssueTrackingGithubSchema(IssueTrackingIntegration):
    pass

# 用于 Jira Issue 跟踪集成的数据模型，继承自 IssueTrackingIntegration，并增加了用户名和 URL。

# 属性：
# username (必需，字符串类型): 用于访问 Jira 系统的用户名。
# url (必需，HttpUrl 类型): Jira 系统的 URL 地址。
# transform_url (方法): 在字段验证时，标准化 URL 的方案和主机部分。
class IssueTrackingJiraSchema(IssueTrackingIntegration):
    username: str = Field(...)
    url: HttpUrl = Field(...)

    @field_validator('url')
    @classmethod
    def transform_url(cls, v: HttpUrl):
        return HttpUrl.build(scheme=v.scheme.lower(), host=v.host.lower())

# 用于 Webhook 配置的数据模型，包含 Webhook 的 ID、端点、认证头和名称等字段。

# 属性：
# webhook_id (Optional[int] 类型，默认值为 None): Webhook 的唯一标识符。
# endpoint (必需，AnyHttpUrl 类型): Webhook 的接收端点。
# auth_header (Optional[str] 类型，默认值为 None): 用于 Webhook 请求的认证头。
# name (字符串类型，默认值为 "", 最大长度为 100，符合 NAME_PATTERN): Webhook 的名称。
# _transform_name (方法): 在字段验证前，使用 remove_whitespace 函数去除名称中的多余空白。
class WebhookSchema(BaseModel):
    webhook_id: Optional[int] = Field(default=None)
    endpoint: AnyHttpUrl = Field(...)
    auth_header: Optional[str] = Field(default=None)
    name: str = Field(default="", max_length=100, pattern=NAME_PATTERN)

    _transform_name = field_validator('name', mode='before')(remove_whitespace)

# 用于创建新成员的数据模型，包含用户 ID、姓名、电子邮件和管理员权限等字段。

# 属性：
# user_id (可选，整数类型，默认值为 None): 成员的唯一标识符。
# name (必需，字符串类型): 成员的姓名。
# email (必需，EmailStr 类型): 成员的电子邮件地址。
# admin (布尔类型，默认值为 False): 是否赋予成员管理员权限。
# _transform_email (方法): 在字段验证前，使用 transform_email 函数处理电子邮件地址。
# _transform_name (方法): 在字段验证前，使用 remove_whitespace 函数去除姓名中的多余空白。
class CreateMemberSchema(BaseModel):
    user_id: Optional[int] = Field(default=None)
    name: str = Field(...)
    email: EmailStr = Field(...)
    admin: bool = Field(default=False)

    _transform_email = field_validator('email', mode='before')(transform_email)
    _transform_name = field_validator('name', mode='before')(remove_whitespace)

# 用于编辑现有成员的数据模型，包含成员的姓名、电子邮件和管理员权限等字段。

# 属性：
# name (必需，字符串类型，必须符合 NAME_PATTERN 正则表达式): 成员的姓名。
# email (必需，EmailStr 类型): 成员的电子邮件地址。
# admin (布尔类型，默认值为 False): 是否赋予成员管理员权限。
# _transform_email (方法): 在字段验证前，使用 transform_email 函数处理电子邮件地址。
# _transform_name (方法): 在字段验证前，使用 remove_whitespace 函数去除姓名中的多余空白。
class EditMemberSchema(BaseModel):
    name: str = Field(..., pattern=NAME_PATTERN)
    email: EmailStr = Field(...)
    admin: bool = Field(default=False)

    _transform_email = field_validator('email', mode='before')(transform_email)
    _transform_name = field_validator('name', mode='before')(remove_whitespace)

# 用于处理通过邀请链接修改密码的数据模型，包含邀请标识符、密钥和新密码。

# 属性：
# invitation (必需，字符串类型): 用于标识邀请的字符串。
# passphrase (必需，字符串类型，别名为 pass): 修改密码时使用的密钥。
# password (必需，SecretStr 类型): 用户的新密码。
class EditPasswordByInvitationSchema(BaseModel):
    invitation: str = Field(...)
    passphrase: str = Field(..., alias="pass")
    password: SecretStr = Field(...)

# 用于任务分配的数据模型，包含任务的受让人、描述、标题和问题类型。

# 属性：
# assignee (必需，字符串类型): 任务的受让人。
# description (必需，字符串类型): 任务的描述。
# title (必需，字符串类型): 任务的标题。
# issue_type (必需，字符串类型): 任务的类型（如问题类型）。
# _transform_title (方法): 在字段验证前，使用 remove_whitespace 函数去除标题中的多余空白。
class AssignmentSchema(BaseModel):
    assignee: str = Field(...)
    description: str = Field(...)
    title: str = Field(...)
    issue_type: str = Field(...)

    _transform_title = field_validator('title', mode='before')(remove_whitespace)

# 用于任务评论的数据模型，包含评论信息。

# 属性：
# message (必需，字符串类型): 任务的评论信息。

class CommentAssignmentSchema(BaseModel):
    message: str = Field(...)

# 用于集成通知的数据模型，包含可选的评论字段。
# 属性：
# comment (可选，字符串类型，默认值为 None): 集成通知的评论信息。
class IntegrationNotificationSchema(BaseModel):
    comment: Optional[str] = Field(default=None)

# 功能描述：
# 用于 GDPR（通用数据保护条例）相关设置的数据模型，包含邮件遮盖、采样率、数字遮盖和默认输入模式等字段。

# 属性：
# maskEmails (必需，布尔类型): 是否遮盖电子邮件地址。
# sampleRate (必需，整数类型): 数据采样率。
# maskNumbers (必需，布尔类型): 是否遮盖数字信息。
# defaultInputMode (必需，字符串类型): 默认的输入模式。
class GdprSchema(BaseModel):
    maskEmails: bool = Field(...)
    sampleRate: int = Field(...)
    maskNumbers: bool = Field(...)
    defaultInputMode: str = Field(...)

# 用于设置数据采样率的模型，包含采样率和是否捕获所有数据的选项。

# 属性：
# rate (必需，整数类型，范围为0到100): 数据采样率。
# capture_all (布尔类型，默认值为 False): 是否捕获所有数据。
class SampleRateSchema(BaseModel):
    rate: int = Field(..., ge=0, le=100)
    capture_all: bool = Field(default=False)

# 用于配置每周报告设置的模型。

# 属性：
# weekly_report (布尔类型，默认值为 True): 是否启用每周报告。
class WeeklyReportConfigSchema(BaseModel):
    weekly_report: bool = Field(default=True)

# 用于集成设置的基础模型，不包含任何具体字段，作为其他集成模型的基类。
class IntegrationBase(BaseModel):
    pass

# 用于 Sentry 集成的数据模型，包含项目标识符、组织标识符和访问令牌。

# 属性：
# project_slug (必需，字符串类型): Sentry 项目的标识符。
# organization_slug (必需，字符串类型): Sentry 组织的标识符。
# token (必需，字符串类型): 用于访问 Sentry 的令牌。
class IntegrationSentrySchema(IntegrationBase):
    project_slug: str = Field(...)
    organization_slug: str = Field(...)
    token: str = Field(...)

# 用于 Datadog 集成的数据模型，包含 API 密钥和应用密钥。

# 属性：
# api_key (必需，字符串类型): 用于访问 Datadog 的 API 密钥。
# application_key (必需，字符串类型): 用于访问 Datadog 的应用密钥。
class IntegrationDatadogSchema(IntegrationBase):
    api_key: str = Field(...)
    application_key: str = Field(...)

# 用于 Stackdriver 集成的数据模型，包含服务账户凭证和日志名称。

# 属性：
# service_account_credentials (必需，字符串类型): 用于访问 Stackdriver 的服务账户凭证。
# log_name (必需，字符串类型): Stackdriver 日志的名称。
class IntegartionStackdriverSchema(IntegrationBase):
    service_account_credentials: str = Field(...)
    log_name: str = Field(...)

# 用于 Newrelic 集成的数据模型，包含应用标识符、查询密钥和区域设置。

# 属性：
# application_id (必需，字符串类型): Newrelic 应用的标识符。
# x_query_key (必需，字符串类型): 用于查询的密钥。
# region (布尔类型，默认值为 False): 是否启用区域设置。

class IntegrationNewrelicSchema(IntegrationBase):
    application_id: str = Field(...)
    x_query_key: str = Field(...)
    region: bool = Field(default=False)

# 用于 Rollbar 集成的数据模型，包含访问令牌。

# 属性：
# access_token (必需，字符串类型): 用于访问 Rollbar 的令牌。
class IntegrationRollbarSchema(IntegrationBase):
    access_token: str = Field(...)

# 用于 Bugsnag 基本集成的数据模型，包含授权令牌。

# 属性：
# authorization_token (必需，字符串类型): 用于访问 Bugsnag 的授权令牌。
class IntegrationBugsnagBasicSchema(IntegrationBase):
    authorization_token: str = Field(...)

# 用于 Bugsnag 集成的数据模型，继承自 IntegrationBugsnagBasicSchema，并添加了项目标识符。

# 属性：
# bugsnag_project_id (必需，字符串类型): Bugsnag 项目的标识符。

class IntegrationBugsnagSchema(IntegrationBugsnagBasicSchema):
    bugsnag_project_id: str = Field(...)

# 用于 Cloudwatch 基本集成的数据模型，包含 AWS 访问密钥 ID、秘密访问密钥和区域设置。

# 属性：
# aws_access_key_id (必需，字符串类型): AWS 访问密钥 ID。
# aws_secret_access_key (必需，字符串类型): AWS 秘密访问密钥。
# region (必需，字符串类型): AWS 区域设置。
class IntegrationCloudwatchBasicSchema(IntegrationBase):
    aws_access_key_id: str = Field(...)
    aws_secret_access_key: str = Field(...)
    region: str = Field(...)

# 用于 Cloudwatch 集成的数据模型，继承自 IntegrationCloudwatchBasicSchema，并添加了日志组名称。

# 属性：
# log_group_name (必需，字符串类型): Cloudwatch 日志组的名称。
class IntegrationCloudwatchSchema(IntegrationCloudwatchBasicSchema):
    log_group_name: str = Field(...)

# 用于 Elasticsearch 测试集成的数据模型，包含主机、端口、API 密钥 ID 和 API 密钥。
# 属性：
# host (必需，字符串类型): Elasticsearch 的主机地址。
# port (必需，整数类型): Elasticsearch 的端口号。
# api_key_id (可选，字符串类型，默认值为 None): 用于访问 Elasticsearch 的 API 密钥 ID。
# api_key (必需，字符串类型): 用于访问 Elasticsearch 的 API 密钥。

class IntegrationElasticsearchTestSchema(IntegrationBase):
    host: str = Field(...)
    port: int = Field(...)
    api_key_id: Optional[str] = Field(default=None)
    api_key: str = Field(...)

# 用于 Elasticsearch 集成的数据模型，继承自 IntegrationElasticsearchTestSchema，并添加了索引字段。

# 属性：
# indexes (必需，字符串类型): Elasticsearch 索引的名称。

class IntegrationElasticsearchSchema(IntegrationElasticsearchTestSchema):
    indexes: str = Field(...)

# 用于 Sumologic 集成的数据模型，包含访问 ID、访问密钥和区域设置。

# 属性：
# access_id (必需，字符串类型): 用于访问 Sumologic 的 ID。
# access_key (必需，字符串类型): 用于访问 Sumologic 的密钥。
# region (必需，字符串类型): Sumologic 的区域设置。
class IntegrationSumologicSchema(IntegrationBase):
    access_id: str = Field(...)
    access_key: str = Field(...)
    region: str = Field(...)

# 用于元数据字段的数据模型，包含索引和键值。

# 属性：
# index (可选，整数类型，默认值为 None): 元数据的索引值。
# key (必需，字符串类型): 元数据的键名。
# _transform_key (方法): 在字段验证前，使用 remove_whitespace 函数去除键名中的多余空白。
class MetadataSchema(BaseModel):
    index: Optional[int] = Field(default=None)
    key: str = Field(...)

    _transform_key = field_validator('key', mode='before')(remove_whitespace)

# 用于邮件发送的数据模型，包含授权信息、电子邮件地址、链接和消息内容。
# 属性：
# auth (必需，字符串类型): 授权信息。
# email (必需，EmailStr 类型): 收件人的电子邮件地址。
# link (必需，字符串类型): 邮件中的链接。
# message (必需，字符串类型): 邮件的消息内容。
# _transform_email (方法): 在字段验证前，使用 transform_email 函数处理电子邮件地址。
class EmailPayloadSchema(BaseModel):
    auth: str = Field(...)
    email: EmailStr = Field(...)
    link: str = Field(...)
    message: str = Field(...)

    _transform_email = field_validator('email', mode='before')(transform_email)

# 用于成员邀请的数据模型，包含授权信息、电子邮件地址、邀请链接、客户端 ID 和发送者姓名。

# 属性：
# auth (必需，字符串类型): 授权信息。
# email (必需，EmailStr 类型): 被邀请者的电子邮件地址。
# invitation_link (必需，字符串类型): 邀请链接。
# client_id (必需，字符串类型): 客户端 ID。
# sender_name (必需，字符串类型): 发送者的姓名。
# _transform_email (方法): 在字段验证前，使用 transform_email 函数处理电子邮件地址。
class MemberInvitationPayloadSchema(BaseModel):
    auth: str = Field(...)
    email: EmailStr = Field(...)
    invitation_link: str = Field(...)
    client_id: str = Field(...)
    sender_name: str = Field(...)

    _transform_email = field_validator('email', mode='before')(transform_email)

# 用于定义警报消息的数据模型，包含消息类型和值。

# 属性：
# type (必需，字符串类型): 警报消息的类型。
# value (必需，字符串类型): 警报消息的值。
# _transform_value (方法): 在字段验证前，使用 int_to_string 函数将值转换为字符串。
class _AlertMessageSchema(BaseModel):
    type: str = Field(...)
    value: str = Field(...)

    _transform_value = field_validator('value', mode='before')(int_to_string)

# 定义警报检测类型的枚举类。

# 枚举值：
# percent: 检测类型为百分比。
# change: 检测类型为变化。
class AlertDetectionType(str, Enum):
    percent = "percent"
    change = "change"

# 用于定义警报选项的数据模型，包含消息、当前周期、前一周期、最后通知时间和重新通知间隔。

# 属性：
# message (List[_AlertMessageSchema] 类型，默认值为 []): 警报消息列表。
# currentPeriod (Literal[15, 30, 60, 120, 240, 1440] 类型): 当前周期，以分钟为单位。
# previousPeriod (Literal[15, 30, 60, 120, 240, 1440] 类型，默认值为 15): 前一周期，以分钟为单位。
# lastNotification (可选，整数类型，默认值为 None): 最后一次通知的时间戳。
# renotifyInterval (可选，整数类型，默认值为 720): 重新通知的时间间隔，以分钟为单位。
class _AlertOptionSchema(BaseModel):
    message: List[_AlertMessageSchema] = Field([])
    currentPeriod: Literal[15, 30, 60, 120, 240, 1440] = Field(...)
    previousPeriod: Literal[15, 30, 60, 120, 240, 1440] = Field(default=15)
    lastNotification: Optional[int] = Field(default=None)
    renotifyInterval: Optional[int] = Field(default=720)

# 定义警报列的枚举类，用于指定警报监控的具体指标。

# 枚举值：
# performance__dom_content_loaded__average: 页面加载完成时间的平均值。
# performance__first_meaningful_paint__average: 首次有意义绘制的平均时间。
# performance__page_load_time__average: 页面加载时间的平均值。
# performance__dom_build_time__average: DOM 构建时间的平均值。
# performance__speed_index__average: 页面速度指数的平均值。
# performance__page_response_time__average: 页面响应时间的平均值。
# performance__ttfb__average: 首字节时间的平均值。
# performance__time_to_render__average: 渲染时间的平均值。
# performance__image_load_time__average: 图像加载时间的平均值。
# performance__request_load_time__average: 请求加载时间的平均值。
# resources__load_time__average: 资源加载时间的平均值。
# resources__missing__count: 缺失资源的数量。
# errors__4xx_5xx__count: 4xx 和 5xx 错误的数量。
# errors__4xx__count: 4xx 错误的数量。
# errors__5xx__count: 5xx 错误的数量。
# errors__javascript__impacted_sessions__count: 受 JavaScript 错误影响的会话数量。
# performance__crashes__count: 页面崩溃的数量。
# errors__javascript__count: JavaScript 错误的数量。
# errors__backend__count: 后端错误的数量。
# custom: 自定义警报列。
class AlertColumn(str, Enum):
    performance__dom_content_loaded__average = "performance.dom_content_loaded.average"
    performance__first_meaningful_paint__average = "performance.first_meaningful_paint.average"
    performance__page_load_time__average = "performance.page_load_time.average"
    performance__dom_build_time__average = "performance.dom_build_time.average"
    performance__speed_index__average = "performance.speed_index.average"
    performance__page_response_time__average = "performance.page_response_time.average"
    performance__ttfb__average = "performance.ttfb.average"
    performance__time_to_render__average = "performance.time_to_render.average"
    performance__image_load_time__average = "performance.image_load_time.average"
    performance__request_load_time__average = "performance.request_load_time.average"
    resources__load_time__average = "resources.load_time.average"
    resources__missing__count = "resources.missing.count"
    errors__4xx_5xx__count = "errors.4xx_5xx.count"
    errors__4xx__count = "errors.4xx.count"
    errors__5xx__count = "errors.5xx.count"
    errors__javascript__impacted_sessions__count = "errors.javascript.impacted_sessions.count"
    performance__crashes__count = "performance.crashes.count"
    errors__javascript__count = "errors.javascript.count"
    errors__backend__count = "errors.backend.count"
    custom = "CUSTOM"

# 定义数学运算符的枚举类，用于指定警报条件中的比较操作。

# 枚举值：
# _equal: 等于运算符 "="。
# _less: 小于运算符 "<"。
# _greater: 大于运算符 ">"。
# _less_eq: 小于等于运算符 "<="。
# _greater_eq: 大于等于运算符 ">="。
class MathOperator(str, Enum):
    _equal = "="
    _less = "<"
    _greater = ">"
    _less_eq = "<="
    _greater_eq = ">="

# 用于定义警报查询条件的数据模型，包含左侧条件、右侧值和运算符。

# 属性：
# left (必需，Union[AlertColumn, int] 类型): 左侧条件，可以是警报列或整数。
# right (必需，浮点数类型): 右侧值，通常是一个数值，用于与左侧条件进行比较。
# operator (必需，MathOperator 类型): 比较操作符，用于定义如何比较左侧条件与右侧值。
class _AlertQuerySchema(BaseModel):
    left: Union[AlertColumn, int] = Field(...)
    right: float = Field(...)
    operator: MathOperator = Field(...)

# 定义警报检测方法的枚举类。

# 枚举值：
# threshold: 检测方法为阈值比较。
# change: 检测方法为变化检测。
class AlertDetectionMethod(str, Enum):
    threshold = "threshold"
    change = "change"

# 用于定义警报配置的数据模型，包含警报名称、检测方法、变化类型、描述、选项、查询和系列 ID。

# 属性：
# name (必需，字符串类型，必须符合 NAME_PATTERN 正则表达式): 警报的名称。
# detection_method (必需，AlertDetectionMethod 类型): 警报的检测方法。
# change (可选，AlertDetectionType 类型，默认值为 AlertDetectionType.change): 警报的变化类型。
# description (可选，字符串类型，默认值为 None): 警报的描述信息。
# options (必需，_AlertOptionSchema 类型): 警报的选项配置。
# query (必需，_AlertQuerySchema 类型): 警报的查询条件。
# series_id (可选，整数类型，默认值为 None, 在文档中隐藏): 警报关联的系列 ID。
# transform_alert (方法): 在模型验证后，处理警报查询条件，确保 series_id 的正确性。
class AlertSchema(BaseModel):
    name: str = Field(..., pattern=NAME_PATTERN)
    detection_method: AlertDetectionMethod = Field(...)
    change: Optional[AlertDetectionType] = Field(default=AlertDetectionType.change)
    description: Optional[str] = Field(default=None)
    options: _AlertOptionSchema = Field(...)
    query: _AlertQuerySchema = Field(...)
    series_id: Optional[int] = Field(default=None, doc_hidden=True)

    @model_validator(mode="after")
    def transform_alert(cls, values):
        values.series_id = None
        if isinstance(values.query.left, int):
            values.series_id = values.query.left
            values.query.left = AlertColumn.custom

        return values

# 用于上传 Sourcemap 的数据模型，包含一个 URL 列表。

# 属性：
# urls (必需，List[str] 类型，别名为 URL): Sourcemap 的 URL 列表。
class SourcemapUploadPayloadSchema(BaseModel):
    urls: List[str] = Field(..., alias="URL")

# 定义错误来源的枚举类，用于标识错误事件的来源。

# 枚举值：
# js_exception: JavaScript 异常。
# bugsnag: Bugsnag 错误报告。
# cloudwatch: Cloudwatch 日志。
# datadog: Datadog 日志。
# newrelic: New Relic 错误监控。
# rollbar: Rollbar 错误报告。
# sentry: Sentry 错误报告。
# stackdriver: Stackdriver 错误监控。
# sumologic: Sumologic 日志。

class ErrorSource(str, Enum):
    js_exception = "js_exception"
    bugsnag = "bugsnag"
    cloudwatch = "cloudwatch"
    datadog = "datadog"
    newrelic = "newrelic"
    rollbar = "rollbar"
    sentry = "sentry"
    stackdriver = "stackdriver"
    sumologic = "sumologic"

# 定义事件类型的枚举类，用于标识不同类型的用户交互事件。

# 枚举值：
# click: 点击事件。
# input: 输入事件。
# location: 位置事件。
# custom: 自定义事件。
# request: 请求事件。
# request_details: 请求详细信息事件（fetch）。
# graphql: GraphQL 请求事件。
# state_action: 状态操作事件。
# error: 错误事件。
# tag: 标签事件。
# click_mobile: 移动端点击事件。
# input_mobile: 移动端输入事件。
# view_mobile: 移动端视图事件。
# custom_mobile: 移动端自定义事件。
# request_mobile: 移动端请求事件。
# error_mobile: 移动端错误事件。
# swipe_mobile: 移动端滑动事件。
class EventType(str, Enum):
    click = "click"
    input = "input"
    location = "location"
    custom = "custom"
    request = "request"
    request_details = "fetch"
    graphql = "graphql"
    state_action = "stateAction"
    error = "error"
    tag = "tag"
    click_mobile = "clickMobile"
    input_mobile = "inputMobile"
    view_mobile = "viewMobile"
    custom_mobile = "customMobile"
    request_mobile = "requestMobile"
    error_mobile = "errorMobile"
    swipe_mobile = "swipeMobile"

# 定义性能事件类型的枚举类，用于标识与页面性能相关的事件。

# 枚举值：
# location_dom_complete: DOM 完成事件。
# location_largest_contentful_paint_time: 最大内容绘制时间。
# location_ttfb: 首字节时间（TTFB）。
# location_avg_cpu_load: 平均 CPU 负载。
# location_avg_memory_usage: 平均内存使用量。
# fetch_failed: 请求失败事件。
class PerformanceEventType(str, Enum):
    location_dom_complete = "domComplete"
    location_largest_contentful_paint_time = "largestContentfulPaintTime"
    location_ttfb = "ttfb"
    location_avg_cpu_load = "avgCpuLoad"
    location_avg_memory_usage = "avgMemoryUsage"
    fetch_failed = "fetchFailed"
    # fetch_duration = "FETCH_DURATION"

# 定义过滤器类型的枚举类，用于在会话中筛选特定属性或行为。

# 枚举值：
# user_os: 用户操作系统。
# user_browser: 用户浏览器。
# user_device: 用户设备。
# user_country: 用户国家。
# user_city: 用户城市。
# user_state: 用户状态。
# user_id: 用户 ID。
# user_anonymous_id: 匿名用户 ID。
# referrer: 引荐来源。
# rev_id: 修订 ID。
# user_os_mobile: 移动端用户操作系统。
# user_device_mobile: 移动端用户设备。
# user_country_mobile: 移动端用户国家。
# user_id_mobile: 移动端用户 ID。
# user_anonymous_id_mobile: 移动端匿名用户 ID。
# rev_id_mobile: 移动端修订 ID。
# duration: 会话持续时间。
# platform: 平台类型。
# metadata: 元数据。
# issue: 问题类型。
# events_count: 事件数量。
# utm_source: UTM 来源。
# utm_medium: UTM 媒介。
# utm_campaign: UTM 活动。
# thermal_state: 热状态。
# main_thread_cpu: 主线程 CPU 使用情况。
# view_component: 视图组件。
# log_event: 日志事件。
# click_event: 点击事件。
# memory_usage: 内存使用情况。
class FilterType(str, Enum):
    user_os = "userOs"
    user_browser = "userBrowser"
    user_device = "userDevice"
    user_country = "userCountry"
    user_city = "userCity"
    user_state = "userState"
    user_id = "userId"
    user_anonymous_id = "userAnonymousId"
    referrer = "referrer"
    rev_id = "revId"
    # IOS
    user_os_mobile = "userOsIos"
    user_device_mobile = "userDeviceIos"
    user_country_mobile = "userCountryIos"
    user_id_mobile = "userIdIos"
    user_anonymous_id_mobile = "userAnonymousIdIos"
    rev_id_mobile = "revIdIos"
    #
    duration = "duration"
    platform = "platform"
    metadata = "metadata"
    issue = "issue"
    events_count = "eventsCount"
    utm_source = "utmSource"
    utm_medium = "utmMedium"
    utm_campaign = "utmCampaign"
    # Mobile conditions
    thermal_state = "thermalState"
    main_thread_cpu = "mainThreadCPU"
    view_component = "viewComponent"
    log_event = "logEvent"
    click_event = "clickEvent"
    memory_usage = "memoryUsage"

# 定义搜索事件操作符的枚举类，用于指定事件过滤的条件。

# 枚举值：
# _is: 等于操作符。
# _is_any: 匹配任意值的操作符。
# _on: 在指定值上的操作符。
# _on_any: 在任意值上的操作符。
# _is_not: 不等于操作符。
# _is_undefined: 未定义操作符。
# _not_on: 不在指定值上的操作符。
# _contains: 包含操作符。
# _not_contains: 不包含操作符。
# _starts_with: 以指定值开头的操作符。
# _ends_with: 以指定值结尾的操作符。
class SearchEventOperator(str, Enum):
    _is = "is"
    _is_any = "isAny"
    _on = "on"
    _on_any = "onAny"
    _is_not = "isNot"
    _is_undefined = "isUndefined"
    _not_on = "notOn"
    _contains = "contains"
    _not_contains = "notContains"
    _starts_with = "startsWith"
    _ends_with = "endsWith"

# 定义点击事件的额外操作符的枚举类，主要用于指定选择器。
# 枚举值：
# _on_selector: 在指定选择器上的操作符。
class ClickEventExtraOperator(str, Enum):
    _on_selector = "onSelector"

# 定义平台类型的枚举类，用于标识用户访问的平台。

# 枚举值：
# mobile: 移动平台。
# desktop: 桌面平台。
# tablet: 平板平台。
class PlatformType(str, Enum):
    mobile = "mobile"
    desktop = "desktop"
    tablet = "tablet"

# 定义事件排序的枚举类，用于指定事件的排序逻辑。

# 枚举值：
# _then: 使用 "then" 逻辑进行排序。
# _or: 使用 "or" 逻辑进行排序。
# _and: 使用 "and" 逻辑进行排序。
class SearchEventOrder(str, Enum):
    _then = "then"
    _or = "or"
    _and = "and"

# 定义问题类型的枚举类，用于标识会话中可能出现的问题类型。

# 枚举值：
# click_rage: 点击狂怒。
# dead_click: 无效点击。
# excessive_scrolling: 过度滚动。
# bad_request: 错误请求。
# missing_resource: 资源缺失。
# memory: 内存问题。
# cpu: CPU 使用问题。
# slow_resource: 慢资源加载。
# slow_page_load: 页面加载缓慢。
# crash: 页面崩溃。
# custom: 自定义问题。
# js_exception: JavaScript 异常。
# mouse_thrashing: 鼠标抖动。
# tap_rage: 移动端点击狂怒。
class IssueType(str, Enum):
    click_rage = 'click_rage'
    dead_click = 'dead_click'
    excessive_scrolling = 'excessive_scrolling'
    bad_request = 'bad_request'
    missing_resource = 'missing_resource'
    memory = 'memory'
    cpu = 'cpu'
    slow_resource = 'slow_resource'
    slow_page_load = 'slow_page_load'
    crash = 'crash'
    custom = 'custom'
    js_exception = 'js_exception'
    mouse_thrashing = 'mouse_thrashing'
    # IOS
    tap_rage = 'tap_rage'

# 定义指标格式类型的枚举类，用于指定会话或用户计数格式。

# 枚举值：
# session_count: 会话计数。
class MetricFormatType(str, Enum):
    session_count = 'sessionCount'

# 定义扩展的指标格式类型的枚举类，用于指定更详细的会话或用户计数格式。

# 枚举值：
# session_count: 会话计数。
# user_count: 用户计数。

class MetricExtendedFormatType(str, Enum):
    session_count = 'sessionCount'
    user_count = 'userCount'

# 定义 HTTP 方法的枚举类，用于指定 HTTP 请求的方法类型。

# 枚举值：
# _get: GET 方法。
# _head: HEAD 方法。
# _post: POST 方法。
# _put: PUT 方法。
# _delete: DELETE 方法。
# _connect: CONNECT 方法。
# _option: OPTIONS 方法。
# _trace: TRACE 方法。
# _patch: PATCH 方法。
class HttpMethod(str, Enum):
    _get = 'GET'
    _head = 'HEAD'
    _post = 'POST'
    _put = 'PUT'
    _delete = 'DELETE'
    _connect = 'CONNECT'
    _option = 'OPTIONS'
    _trace = 'TRACE'
    _patch = 'PATCH'

# 定义 Fetch 请求过滤类型的枚举类，用于指定 Fetch 请求的过滤条件。

# 枚举值：
# _url: 请求 URL。
# _status_code: HTTP 状态码。
# _method: HTTP 方法。
# _duration: 请求持续时间。
# _request_body: 请求体。
# _response_body: 响应体。
class FetchFilterType(str, Enum):
    _url = "fetchUrl"
    _status_code = "fetchStatusCode"
    _method = "fetchMethod"
    _duration = "fetchDuration"
    _request_body = "fetchRequestBody"
    _response_body = "fetchResponseBody"

# 定义 GraphQL 请求过滤类型的枚举类，用于指定 GraphQL 请求的过滤条件。

# 枚举值：
# _name: GraphQL 请求名称。
# _method: GraphQL 请求方法。
# _request_body: 请求体。
# _response_body: 响应体。

class GraphqlFilterType(str, Enum):
    _name = "graphqlName"
    _method = "graphqlMethod"
    _request_body = "graphqlRequestBody"
    _response_body = "graphqlResponseBody"

# 用于定义 GraphQL 请求过滤条件的数据模型，包含过滤类型、值和操作符。

# 属性：
# type (必需，Union[FetchFilterType, GraphqlFilterType]): 过滤类型，可能是 Fetch 请求或 GraphQL 请求的类型。
# value (必需，List[Union[int, str]]): 过滤的值列表。
# operator (必需，Union[SearchEventOperator, MathOperator]): 用于比较的操作符。

class RequestGraphqlFilterSchema(BaseModel):
    type: Union[FetchFilterType, GraphqlFilterType] = Field(...)
    value: List[Union[int, str]] = Field(...)
    operator: Union[SearchEventOperator, MathOperator] = Field(...)

# 用于定义会话搜索事件的数据模型，包含事件类型、值、来源和过滤器等。

# 属性：
# is_event (Literal[True]): 指示此模式为事件类型的标识符。
# value (必需，List[Union[str, int]]): 事件的值列表。
# type (必需，Union[EventType, PerformanceEventType]): 事件的类型，可以是用户交互事件或性能事件。
# operator (必需，Union[SearchEventOperator, ClickEventExtraOperator]): 用于比较的操作符。
# source (可选，Optional[List[Union[ErrorSource, int, str]]]): 事件的来源列表。
# sourceOperator (可选，Optional[MathOperator]): 用于事件来源比较的操作符。
# filters (可选，Optional[List[RequestGraphqlFilterSchema]]): 事件的附加过滤器列表。
# _remove_duplicate_values (方法): 在字段验证前，使用 remove_duplicate_values 函数去除重复的值。
# _single_to_list_values (方法): 在字段验证前，使用 single_to_list 函数将单个值转换为列表。
# _transform (方法): 在模型验证前，使用 transform_old_filter_type 函数处理旧的过滤器类型。
# event_validator (方法): 在模型验证后，验证事件的正确性，确保事件类型、来源和操作符的一致性。

class SessionSearchEventSchema2(BaseModel):
    is_event: Literal[True] = True
    value: List[Union[str, int]] = Field(...)
    type: Union[EventType, PerformanceEventType] = Field(...)
    operator: Union[SearchEventOperator, ClickEventExtraOperator] = Field(...)
    source: Optional[List[Union[ErrorSource, int, str]]] = Field(default=None)
    sourceOperator: Optional[MathOperator] = Field(default=None)
    filters: Optional[List[RequestGraphqlFilterSchema]] = Field(default=[])

    _remove_duplicate_values = field_validator('value', mode='before')(remove_duplicate_values)
    _single_to_list_values = field_validator('value', mode='before')(single_to_list)
    _transform = model_validator(mode='before')(transform_old_filter_type)

    @model_validator(mode='after')
    def event_validator(cls, values):
        if isinstance(values.type, PerformanceEventType):
            if values.type == PerformanceEventType.fetch_failed:
                return values
            # assert values.get("source") is not None, "source should not be null for PerformanceEventType"
            # assert isinstance(values["source"], list) and len(values["source"]) > 0, \
            #     "source should not be empty for PerformanceEventType"
            assert values.sourceOperator is not None, \
                "sourceOperator should not be null for PerformanceEventType"
            assert "source" in values, f"source is required for {values.type}"
            assert isinstance(values.source, list), f"source of type list is required for {values.type}"
            for c in values["source"]:
                assert isinstance(c, int), f"source value should be of type int for {values.type}"
        elif values.type == EventType.error and values.source is None:
            values.source = [ErrorSource.js_exception]
        elif values.type == EventType.request_details:
            assert isinstance(values.filters, List) and len(values.filters) > 0, \
                f"filters should be defined for {EventType.request_details}"
        elif values.type == EventType.graphql:
            assert isinstance(values.filters, List) and len(values.filters) > 0, \
                f"filters should be defined for {EventType.graphql}"

        if isinstance(values.operator, ClickEventExtraOperator):
            assert values.type == EventType.click, \
                f"operator:{values.operator} is only available for event-type: {EventType.click}"
        return values

# 用于定义会话搜索过滤条件的数据模型，包含过滤类型、值、来源和操作符等。

# 属性：
# is_event (Literal[False]): 指示此模式为过滤类型的标识符。
# value (必需，List[Union[IssueType, PlatformType, int, str]]): 过滤的值列表。
# type (必需，FilterType): 过滤的类型。
# operator (必需，Union[SearchEventOperator, MathOperator]): 用于比较的操作符。
# source (可选，Optional[Union[ErrorSource, str]]): 过滤的来源。
# _remove_duplicate_values (方法): 在字段验证前，使用 remove_duplicate_values 函数去除重复的值。
# _transform (方法): 在模型验证前，使用 transform_old_filter_type 函数处理旧的过滤器类型。
# _single_to_list_values (方法): 在字段验证前，使用 single_to_list 函数将单个值转换为列表。
# _transform_data (方法): 在模型验证前，转换过滤数据，处理多值来源的特殊情况。
# filter_validator (方法): 在模型验证后，验证过滤器的正确性，确保过滤类型、值和操作符的一致性。
class SessionSearchFilterSchema(BaseModel):
    is_event: Literal[False] = False
    value: List[Union[IssueType, PlatformType, int, str]] = Field(default=[])
    type: FilterType = Field(...)
    operator: Union[SearchEventOperator, MathOperator] = Field(...)
    source: Optional[Union[ErrorSource, str]] = Field(default=None)

    _remove_duplicate_values = field_validator('value', mode='before')(remove_duplicate_values)
    _transform = model_validator(mode='before')(transform_old_filter_type)
    _single_to_list_values = field_validator('value', mode='before')(single_to_list)

    @model_validator(mode='before')
    def _transform_data(cls, values):
        if values.get("source") is not None:
            if isinstance(values["source"], list):
                if len(values["source"]) == 0:
                    values["source"] = None
                elif len(values["source"]) == 1:
                    values["source"] = values["source"][0]
                else:
                    raise ValueError(f"Unsupported multi-values source")
        return values

    @model_validator(mode='after')
    def filter_validator(cls, values):
        if values.type == FilterType.metadata:
            assert values.source is not None and len(values.source) > 0, \
                "must specify a valid 'source' for metadata filter"
        elif values.type == FilterType.issue:
            for v in values.value:
                if IssueType.has_value(v):
                    v = IssueType(v)
                else:
                    raise ValueError(f"value should be of type IssueType for {values.type} filter")
        elif values.type == FilterType.platform:
            for v in values.value:
                if PlatformType.has_value(v):
                    v = PlatformType(v)
                else:
                    raise ValueError(f"value should be of type PlatformType for {values.type} filter")
        elif values.type == FilterType.events_count:
            if MathOperator.has_value(values.operator):
                values.operator = MathOperator(values.operator)
            else:
                raise ValueError(f"operator should be of type MathOperator for {values.type} filter")

            for v in values.value:
                assert isinstance(v, int), f"value should be of type int for {values.type} filter"
        else:
            if SearchEventOperator.has_value(values.operator):
                values.operator = SearchEventOperator(values.operator)
            else:
                raise ValueError(f"operator should be of type SearchEventOperator for {values.type} filter")

        return values

# 定义分页模式的基础模型，包含分页相关的限制和页码属性。

# 属性：
# limit (必需，整数类型，默认值为 200): 每页显示的记录数，范围在 1 到 200 之间。
# page (必需，整数类型，默认值为 1): 当前页码，必须大于 0。
class _PaginatedSchema(BaseModel):
    limit: int = Field(default=200, gt=0, le=200)
    page: int = Field(default=1, gt=0)

# 定义排序顺序的枚举类，用于指定结果集的排序方式。

# 枚举值：
# asc: 升序排序。
# desc: 降序排序。
class SortOrderType(str, Enum):
    asc = "ASC"
    desc = "DESC"

# 函数用于在字典中添加缺失的 isEvent 属性，根据事件类型确定 isEvent 的值。

# 参数：
# values (dict): 需要处理的字典数据。
# 返回值：
# 修改后的字典数据，确保 isEvent 属性存在且正确。
def add_missing_is_event(values: dict):
    if values.get("isEvent") is None:
        values["isEvent"] = (EventType.has_value(values["type"])
                             or PerformanceEventType.has_value(values["type"])
                             or ProductAnalyticsSelectedEventType.has_value(values["type"]))
    return values

# 使用 Annotated 定义的联合类型，允许在同一个过滤器组中混合事件和过滤器，指定了 is_event 属性的区分器，并在验证前通过 BeforeValidator 添加缺失的 is_event 属性。
# this type is created to allow mixing events&filters and specifying a discriminator
GroupedFilterType = Annotated[Union[SessionSearchFilterSchema, SessionSearchEventSchema2], \
    Field(discriminator='is_event'), BeforeValidator(add_missing_is_event)]

# 用于定义会话搜索负载的数据模型，包含事件、过滤器、排序和分页等属性。

# 属性：
# events (List[SessionSearchEventSchema2] 类型，默认值为 []): 要查询的事件列表。
# filters (List[GroupedFilterType] 类型，默认值为 []): 要应用的过滤器列表，可以是事件或其他过滤器的组合。
# sort (str 类型，默认值为 startTs): 排序字段，默认按开始时间排序。
# order (SortOrderType 类型，默认值为 SortOrderType.desc): 排序顺序，默认按降序排列。
# events_order (Optional[SearchEventOrder] 类型，默认值为 SearchEventOrder._then): 事件的排序顺序。
# group_by_user (bool 类型，默认值为 False): 是否按用户分组。
# bookmarked (bool 类型，默认值为 False): 是否仅查询已加书签的会话。
# transform_order (方法): 在模型验证前，确保排序字段和顺序的正确性。
# add_missing_attributes (方法): 在模型验证前，添加缺失的 isEvent 属性。
# remove_wrong_filter_values (方法): 在模型验证前，移除无效的过滤值。
# split_filters_events (方法): 在模型验证后，将过滤器和事件分开。
# merge_identical_filters (方法): 在字段验证后，合并相同类型的过滤器，避免重复。
class SessionsSearchPayloadSchema(_TimedSchema, _PaginatedSchema):
    events: List[SessionSearchEventSchema2] = Field(default=[], doc_hidden=True)
    filters: List[GroupedFilterType] = Field(default=[])
    sort: str = Field(default="startTs")
    order: SortOrderType = Field(default=SortOrderType.desc)
    events_order: Optional[SearchEventOrder] = Field(default=SearchEventOrder._then)
    group_by_user: bool = Field(default=False)
    bookmarked: bool = Field(default=False)

    @model_validator(mode="before")
    def transform_order(cls, values):
        if values.get("sort") is None:
            values["sort"] = "startTs"

        if values.get("order") is None:
            values["order"] = SortOrderType.desc
        else:
            values["order"] = values["order"].upper()
        return values

    @model_validator(mode="before")
    def add_missing_attributes(cls, values):
        # in case isEvent is wrong:
        for f in values.get("filters"):
            if EventType.has_value(f["type"]) and not f.get("isEvent"):
                f["isEvent"] = True
            elif FilterType.has_value(f["type"]) and f.get("isEvent"):
                f["isEvent"] = False

        # in case the old search payload was passed
        if len(values.get("events", [])) > 0:
            for v in values["events"]:
                v["isEvent"] = True

        return values

    @model_validator(mode="before")
    def remove_wrong_filter_values(cls, values):
        for f in values.get("filters", []):
            vals = []
            for v in f.get("value", []):
                if v is not None:
                    vals.append(v)
            f["value"] = vals
        return values

    @model_validator(mode="after")
    def split_filters_events(cls, values):
        n_filters = []
        n_events = []
        for v in values.filters:
            if v.is_event:
                n_events.append(v)
            else:
                n_filters.append(v)
        values.events = n_events
        values.filters = n_filters
        return values

    @field_validator("filters", mode="after")
    def merge_identical_filters(cls, values):
        # ignore 'issue' type as it could be used for step-filters and tab-filters at the same time
        i = 0
        while i < len(values):
            if values[i].is_event or values[i].type == FilterType.issue:
                if values[i].type == FilterType.issue:
                    values[i] = remove_duplicate_values(values[i])
                i += 1
                continue
            j = i + 1
            while j < len(values):
                if values[i].type == values[j].type \
                        and values[i].operator == values[j].operator \
                        and (values[i].type != FilterType.metadata or values[i].source == values[j].source):
                    values[i].value += values[j].value
                    del values[j]
                else:
                    j += 1
            values[i] = remove_duplicate_values(values[i])
            i += 1

        return values

# 定义错误状态的枚举类，用于标识错误的处理状态。

# 枚举值：
# all: 所有状态。
# unresolved: 未解决状态。
# resolved: 已解决状态。
# ignored: 已忽略状态。

class ErrorStatus(str, Enum):
    all = 'all'
    unresolved = 'unresolved'
    resolved = 'resolved'
    ignored = 'ignored'

# 定义错误排序方式的枚举类，用于指定错误列表的排序依据。

# 枚举值：
# occurrence: 按发生次数排序。
# users_count: 按影响的用户数量排序。
# sessions_count: 按影响的会话数量排序。

class ErrorSort(str, Enum):
    occurrence = 'occurrence'
    users_count = 'users'
    sessions_count = 'sessions'

# 功能描述：
# 继承自 SessionsSearchPayloadSchema，用于定义错误搜索的过滤条件和排序方式。

# 属性：
# sort (ErrorSort 类型，默认值为 ErrorSort.occurrence): 错误排序方式。
# density (Optional[int] 类型，默认值为 7): 错误密度（可能与可视化相关）。
# status (Optional[ErrorStatus] 类型，默认值为 ErrorStatus.all): 错误的状态筛选条件。
# query (Optional[str] 类型，默认值为 None): 错误搜索查询字符串。
class SearchErrorsSchema(SessionsSearchPayloadSchema):
    sort: ErrorSort = Field(default=ErrorSort.occurrence)
    density: Optional[int] = Field(default=7)
    status: Optional[ErrorStatus] = Field(default=ErrorStatus.all)
    query: Optional[str] = Field(default=None)

# 定义产品分析中选择的事件类型枚举类，基于 EventType 枚举类的值。

# 枚举值：
# click: 点击事件。
# input: 输入事件。
# location: 位置事件。
# custom_event: 自定义事件。
class ProductAnalyticsSelectedEventType(str, Enum):
    click = EventType.click.value
    input = EventType.input.value
    location = EventType.location.value
    custom_event = EventType.custom.value

# 定义路径分析的子过滤器模型，主要用于路径分析中的事件过滤。

# 属性：
# is_event (Literal[True]): 标识此模型为事件类型过滤器。
# value (List[str]): 过滤器的值列表。
# type (ProductAnalyticsSelectedEventType): 事件类型。
# operator (Union[SearchEventOperator, ClickEventExtraOperator]): 过滤器操作符。
# _remove_duplicate_values (方法): 在字段验证前，使用 remove_duplicate_values 函数去除重复的值。

class PathAnalysisSubFilterSchema(BaseModel):
    is_event: Literal[True] = True
    value: List[str] = Field(...)
    type: ProductAnalyticsSelectedEventType = Field(...)
    operator: Union[SearchEventOperator, ClickEventExtraOperator] = Field(...)

    _remove_duplicate_values = field_validator('value', mode='before')(remove_duplicate_values)

    @model_validator(mode="before")
    def __force_is_event(cls, values):
        values["isEvent"] = True
        return values

# 定义产品分析的过滤器基础模型，用于非事件类型的过滤。

# 属性：
# is_event (Literal[False]): 标识此模型为非事件类型过滤器。
# type (FilterType): 过滤器的类型。
# operator (Union[SearchEventOperator, ClickEventExtraOperator, MathOperator]): 过滤器操作符。
# value (List[Union[IssueType, PlatformType, int, str]]): 过滤器的值列表。
# source (Optional[str]): 过滤器的来源。
# _remove_duplicate_values (方法): 在字段验证前，使用 remove_duplicate_values 函数去除重复的值。
class _ProductAnalyticsFilter(BaseModel):
    is_event: Literal[False] = False
    type: FilterType
    operator: Union[SearchEventOperator, ClickEventExtraOperator, MathOperator] = Field(...)
    value: List[Union[IssueType, PlatformType, int, str]] = Field(...)
    source: Optional[str] = Field(default=None)

    _remove_duplicate_values = field_validator('value', mode='before')(remove_duplicate_values)

# 定义产品分析的事件过滤器模型，用于事件类型的过滤。

# 属性：
# is_event (Literal[True]): 标识此模型为事件类型过滤器。
# type (ProductAnalyticsSelectedEventType): 事件类型。
# operator (Union[SearchEventOperator, ClickEventExtraOperator, MathOperator]): 过滤器操作符。
# value (List[Union[IssueType, PlatformType, int, str]]): 过滤器的值列表。
# _remove_duplicate_values (方法): 在字段验证前，使用 remove_duplicate_values 函数去除重复的值。
class _ProductAnalyticsEventFilter(BaseModel):
    is_event: Literal[True] = True
    type: ProductAnalyticsSelectedEventType
    operator: Union[SearchEventOperator, ClickEventExtraOperator, MathOperator] = Field(...)
    # TODO: support session metadata filters
    value: List[Union[IssueType, PlatformType, int, str]] = Field(...)

    _remove_duplicate_values = field_validator('value', mode='before')(remove_duplicate_values)

# 使用 Annotated 定义的联合类型，允许在产品分析中混合事件和非事件过滤器，并指定 is_event 属性作为区分符。
# this type is created to allow mixing events&filters and specifying a discriminator for PathAnalysis series filter
ProductAnalyticsFilter = Annotated[Union[_ProductAnalyticsFilter, _ProductAnalyticsEventFilter], \
    Field(discriminator='is_event')]

# 继承自 _TimedSchema 和 _PaginatedSchema，用于定义路径分析的过滤条件、事件密度、分页等属性。

# 属性：
# density (int 类型，默认值为 7): 路径分析的事件密度。
# filters (List[ProductAnalyticsFilter] 类型，默认值为 []): 路径分析中的过滤器列表。
# type (Optional[str] 类型，默认值为 None): 路径分析的类型。
# _transform_filters (方法): 在字段验证前，强制将事件类型过滤器标记为事件。
class PathAnalysisSchema(_TimedSchema, _PaginatedSchema):
    density: int = Field(default=7)
    filters: List[ProductAnalyticsFilter] = Field(default=[])
    type: Optional[str] = Field(default=None)

    _transform_filters = field_validator('filters', mode='before') \
        (force_is_event(events_enum=[ProductAnalyticsSelectedEventType]))


class MobileSignPayloadSchema(BaseModel):
    keys: List[str] = Field(...)

# 继承自 SearchErrorsSchema，用于定义卡片系列的过滤条件。

# 属性：
# sort (Optional[str] 类型，默认值为 None): 排序字段。
# order (SortOrderType 类型，默认值为 SortOrderType.desc): 排序顺序。
# group_by_user (Literal[False] 类型): 标识是否按用户分组。

class CardSeriesFilterSchema(SearchErrorsSchema):
    sort: Optional[str] = Field(default=None)
    order: SortOrderType = Field(default=SortOrderType.desc)
    group_by_user: Literal[False] = False

# 用于定义卡片系列的数据模型，包含系列 ID、名称、索引和过滤条件等。

# 属性：
# series_id (Optional[int]): 系列 ID。
# name (Optional[str]): 系列名称。
# index (Optional[int]): 系列索引。
# filter (Optional[CardSeriesFilterSchema]): 系列的过滤条件。
class CardSeriesSchema(BaseModel):
    series_id: Optional[int] = Field(default=None)
    name: Optional[str] = Field(default=None)
    index: Optional[int] = Field(default=None)
    filter: Optional[CardSeriesFilterSchema] = Field(default=None)

# 定义时间序列视图类型的枚举类，用于指定时间序列图表的显示方式。

# 枚举值：
# line_chart: 折线图。
# area_chart: 面积图。

class MetricTimeseriesViewType(str, Enum):
    line_chart = "lineChart"
    area_chart = "areaChart"

# 定义表格视图类型的枚举类，用于指定表格的显示方式。

# 枚举值：
# table: 表格视图。
class MetricTableViewType(str, Enum):
    table = "table"

# 定义其他视图类型的枚举类，用于指定非时间序列或表格的显示方式。

# 枚举值：
# other_chart: 其他图表。
# list_chart: 列表图表。
class MetricOtherViewType(str, Enum):
    other_chart = "chart"
    list_chart = "list"

# 定义度量类型的枚举类，用于指定不同的分析类型。

# 枚举值：
# timeseries: 时间序列分析。
# table: 表格分析。
# funnel: 漏斗分析。
# errors: 错误分析。
# performance: 性能分析。
# resources: 资源分析。
# web_vital: Web Vitals 分析。
# pathAnalysis: 路径分析。
# retention: 保留率分析。
# stickiness: 黏性分析。
# heat_map: 热力图分析。
# insights: 洞察分析。
class MetricType(str, Enum):
    timeseries = "timeseries"
    table = "table"
    funnel = "funnel"
    errors = "errors"
    performance = "performance"
    resources = "resources"
    web_vital = "webVitals"
    pathAnalysis = "pathAnalysis"
    retention = "retention"
    stickiness = "stickiness"
    heat_map = "heatMap"
    insights = "insights"

# 定义错误分析度量指标的枚举类，用于指定错误分析中的不同指标。

# 枚举值：
# calls_errors: 调用错误。
# domains_errors_4xx: 域名 4xx 错误。
# domains_errors_5xx: 域名 5xx 错误。
# errors_per_domains: 每个域名的错误。
# errors_per_type: 每种类型的错误。
# impacted_sessions_by_js_errors: 受 JavaScript 错误影响的会话。
# resources_by_party: 按方分类的资源。
class MetricOfErrors(str, Enum):
    calls_errors = "callsErrors"
    domains_errors_4xx = "domainsErrors4xx"
    domains_errors_5xx = "domainsErrors5xx"
    errors_per_domains = "errorsPerDomains"
    errors_per_type = "errorsPerType"
    impacted_sessions_by_js_errors = "impactedSessionsByJsErrors"
    resources_by_party = "resourcesByParty"

# 定义性能分析度量指标的枚举类，用于指定性能分析中的不同指标。

# 枚举值：
# cpu: CPU 使用情况。
# crashes: 崩溃情况。
# fps: 帧率。
# impacted_sessions_by_slow_pages: 受慢页面影响的会话。
# memory_consumption: 内存使用情况。
# pages_dom_buildtime: 页面 DOM 构建时间。
# pages_response_time: 页面响应时间。
# pages_response_time_distribution: 页面响应时间分布。
# resources_vs_visually_complete: 资源与视觉完成时间的对比。
# sessions_per_browser: 每个浏览器的会话数量。
# slowest_domains: 最慢的域名。
# speed_location: 速度位置。
# time_to_render: 渲染时间。
class MetricOfPerformance(str, Enum):
    cpu = "cpu"
    crashes = "crashes"
    fps = "fps"
    impacted_sessions_by_slow_pages = "impactedSessionsBySlowPages"
    memory_consumption = "memoryConsumption"
    pages_dom_buildtime = "pagesDomBuildtime"
    pages_response_time = "pagesResponseTime"
    pages_response_time_distribution = "pagesResponseTimeDistribution"
    resources_vs_visually_complete = "resourcesVsVisuallyComplete"
    sessions_per_browser = "sessionsPerBrowser"
    slowest_domains = "slowestDomains"
    speed_location = "speedLocation"
    time_to_render = "timeToRender"

# 定义资源分析度量指标的枚举类，用于指定资源分析中的不同指标。

# 枚举值：
# missing_resources: 缺失的资源。
# resources_count_by_type: 按类型分类的资源数量。
# resources_loading_time: 资源加载时间。
# resource_type_vs_response_end: 资源类型与响应结束时间的对比。
# slowest_resources: 最慢的资源。

class MetricOfResources(str, Enum):
    missing_resources = "missingResources"
    resources_count_by_type = "resourcesCountByType"
    resources_loading_time = "resourcesLoadingTime"
    resource_type_vs_response_end = "resourceTypeVsResponseEnd"
    slowest_resources = "slowestResources"

# 定义 Web Vitals 分析度量指标的枚举类，用于指定 Web Vitals 分析中的不同指标。

# 枚举值：
# avg_cpu: 平均 CPU 使用情况。
# avg_dom_content_loaded: 平均 DOM 内容加载时间。
# avg_dom_content_load_start: 平均 DOM 内容加载开始时间。
# avg_first_contentful_pixel: 平均首个内容像素时间。
# avg_first_paint: 平均首次绘制时间。
# avg_fps: 平均帧率。
# avg_image_load_time: 平均图片加载时间。
# avg_page_load_time: 平均页面加载时间。
# avg_pages_dom_buildtime: 平均页面 DOM 构建时间。
# avg_pages_response_time: 平均页面响应时间。
# avg_request_load_time: 平均请求加载时间。
# avg_response_time: 平均响应时间。
# avg_session_duration: 平均会话持续时间。
# avg_till_first_byte: 平均首字节时间。
# avg_time_to_interactive: 平均互动时间。
# avg_time_to_render: 平均渲染时间。
# avg_used_js_heap_size: 平均使用的 JavaScript 堆大小。
# avg_visited_pages: 平均访问的页面数量。
# count_requests: 请求计数。
# count_sessions: 会话计数。
# count_users: 用户计数。

class MetricOfWebVitals(str, Enum):
    avg_cpu = "avgCpu"
    avg_dom_content_loaded = "avgDomContentLoaded"
    avg_dom_content_load_start = "avgDomContentLoadStart"
    avg_first_contentful_pixel = "avgFirstContentfulPixel"
    avg_first_paint = "avgFirstPaint"
    avg_fps = "avgFps"
    avg_image_load_time = "avgImageLoadTime"
    avg_page_load_time = "avgPageLoadTime"
    avg_pages_dom_buildtime = "avgPagesDomBuildtime"
    avg_pages_response_time = "avgPagesResponseTime"
    avg_request_load_time = "avgRequestLoadTime"
    avg_response_time = "avgResponseTime"
    avg_session_duration = "avgSessionDuration"
    avg_till_first_byte = "avgTillFirstByte"
    avg_time_to_interactive = "avgTimeToInteractive"
    avg_time_to_render = "avgTimeToRender"
    avg_used_js_heap_size = "avgUsedJsHeapSize"
    avg_visited_pages = "avgVisitedPages"
    count_requests = "countRequests"
    count_sessions = "countSessions"
    count_users = "countUsers"

# 定义表格分析度量指标的枚举类，用于指定表格分析中的不同指标。

# 枚举值：
# user_os: 用户操作系统。
# user_browser: 用户浏览器。
# user_device: 用户设备。
# user_country: 用户国家。
# user_id: 用户 ID。
# issues: 问题。
# visited_url: 访问的 URL。
# sessions: 会话。
# errors: JavaScript 错误。
class MetricOfTable(str, Enum):
    user_os = FilterType.user_os.value
    user_browser = FilterType.user_browser.value
    user_device = FilterType.user_device.value
    user_country = FilterType.user_country.value
    # user_city = FilterType.user_city.value
    # user_state = FilterType.user_state.value
    user_id = FilterType.user_id.value
    issues = FilterType.issue.value
    visited_url = "location"
    sessions = "sessions"
    errors = "jsException"

# 定义时间序列分析度量指标的枚举类，用于指定时间序列分析中的不同指标。

# 枚举值：
# session_count: 会话计数。
# user_count: 用户计数。
class MetricOfTimeseries(str, Enum):
    session_count = "sessionCount"
    user_count = "userCount"

# 定义漏斗分析度量指标的枚举类，用于指定漏斗分析中的不同指标。

# 枚举值：
# session_count: 会话计数。
# user_count: 用户计数。
class MetricOfFunnels(str, Enum):
    session_count = MetricOfTimeseries.session_count.value
    user_count = MetricOfTimeseries.user_count.value

# 定义热力图分析度量指标的枚举类，用于指定热力图分析中的不同指标。

# 枚举值：
# heat_map_url: 热力图 URL。
class MetricOfHeatMap(str, Enum):
    heat_map_url = "heatMapUrl"

# 定义路径分析度量指标的枚举类，用于指定路径分析中的不同指标。

# 枚举值：
# session_count: 会话计数。
class MetricOfPathAnalysis(str, Enum):
    session_count = MetricOfTimeseries.session_count.value

# 描述: 继承了时间戳和分页的基础结构，用于定义会话卡片的基础结构。

# 属性:

# startTimestamp: 会话开始时间的时间戳，默认为当前时间减去7个小时。
# endTimestamp: 会话结束时间的时间戳，默认为当前时间。
# density: 数据密度，范围为1到200，默认为7。
# series: 包含的系列数据列表，默认为空。
# filters: 过滤条件的列表，默认为空。
# hide_excess: 是否隐藏额外的值，用于路径分析等卡片类型。
# 方法:

# remove_wrong_filter_values: 在"before"阶段验证并移除过滤条件中不合法的值。
# __enforce_default: 在"before"阶段强制设置默认的startTimestamp和endTimestamp。
# __enforce_default_after: 在"after"阶段设置每个系列中的过滤器的时间范围和分页信息。
# __merge_out_filters_with_series: 在"after"阶段将外部的过滤器合并到每个系列中。
# class CardSessionsSchema(SessionsSearchPayloadSchema):
class CardSessionsSchema(_TimedSchema, _PaginatedSchema):
    startTimestamp: int = Field(default=TimeUTC.now(-7))
    endTimestamp: int = Field(defautl=TimeUTC.now())
    density: int = Field(default=7, ge=1, le=200)
    series: List[CardSeriesSchema] = Field(default=[])

    # events: List[SessionSearchEventSchema2] = Field(default=[], doc_hidden=True)
    filters: List[GroupedFilterType] = Field(default=[])

    # Used mainly for PathAnalysis, and could be used by other cards
    hide_excess: Optional[bool] = Field(default=False, description="Hide extra values")

    _transform_filters = field_validator('filters', mode='before') \
        (force_is_event(events_enum=[EventType, PerformanceEventType]))

    @model_validator(mode="before")
    def remove_wrong_filter_values(cls, values):
        for f in values.get("filters", []):
            vals = []
            for v in f.get("value", []):
                if v is not None:
                    vals.append(v)
            f["value"] = vals
        return values

    @model_validator(mode="before")
    def __enforce_default(cls, values):
        if values.get("startTimestamp") is None:
            values["startTimestamp"] = TimeUTC.now(-7)

        if values.get("endTimestamp") is None:
            values["endTimestamp"] = TimeUTC.now()

        return values

    @model_validator(mode="after")
    def __enforce_default_after(cls, values):
        for s in values.series:
            if s.filter is not None:
                s.filter.limit = values.limit
                s.filter.page = values.page
                s.filter.startTimestamp = values.startTimestamp
                s.filter.endTimestamp = values.endTimestamp

        return values

    @model_validator(mode="after")
    def __merge_out_filters_with_series(cls, values):
        if len(values.filters) > 0:
            for f in values.filters:
                for s in values.series:
                    found = False

                    if f.is_event:
                        sub = s.filter.events
                    else:
                        sub = s.filter.filters

                    for e in sub:
                        if f.type == e.type and f.operator == e.operator:
                            found = True
                            if f.is_event:
                                # If extra event: append value
                                for v in f.value:
                                    if v not in e.value:
                                        e.value.append(v)
                            else:
                                # If extra filter: override value
                                e.value = f.value
                    if not found:
                        sub.append(f)

            values.filters = []

        return values

# 描述: 定义卡片的配置选项。
# 属性:
# col: 卡片列数，可选。
# row: 卡片行数，默认为2。
# position: 卡片的位置，默认为0。
class CardConfigSchema(BaseModel):
    col: Optional[int] = Field(default=None)
    row: Optional[int] = Field(default=2)
    position: Optional[int] = Field(default=0)

# 描述: 继承自CardSessionsSchema，用于定义通用卡片的基础结构。
# 属性:
# name: 卡片名称，可选。
# is_public: 是否公开卡片，默认为True。
# default_config: 卡片的默认配置，使用CardConfigSchema结构。
# thumbnail: 缩略图，可选。
# metric_format: 度量格式类型，可选。
# view_type: 显示类型。
# metric_type: 度量类型，必填。
# metric_of: 度量对象。
# metric_value: 度量值的列表，默认为空。
# session_id: 被选中的会话ID，用于热图，可选。
# 方法:
# is_predefined: 属性方法，判断卡片是否为预定义类型。
class __CardSchema(CardSessionsSchema):
    name: Optional[str] = Field(default=None)
    is_public: bool = Field(default=True)
    default_config: CardConfigSchema = Field(default=CardConfigSchema(), alias="config")
    thumbnail: Optional[str] = Field(default=None)
    metric_format: Optional[MetricFormatType] = Field(default=None)
    view_type: Any
    metric_type: MetricType = Field(...)
    metric_of: Any
    metric_value: List[IssueType] = Field(default=[])
    # This is used to save the selected session for heatmaps
    session_id: Optional[int] = Field(default=None)

    @computed_field
    @property
    def is_predefined(self) -> bool:
        return self.metric_type in [MetricType.errors, MetricType.performance,
                                    MetricType.resources, MetricType.web_vital]

# 描述: 继承自__CardSchema，用于定义时间序列卡片。

# 属性:

# metric_type: 固定为timeseries。
# metric_of: 时间序列度量对象，默认是会话计数。
# view_type: 时间序列的显示类型。
# 方法:

# __enforce_default: 在"before"阶段强制设置默认的metricValue为空列表。
# __transform: 在"after"阶段将度量对象转为对应的时间序列类型。
class CardTimeSeries(__CardSchema):
    metric_type: Literal[MetricType.timeseries]
    metric_of: MetricOfTimeseries = Field(default=MetricOfTimeseries.session_count)
    view_type: MetricTimeseriesViewType

    @model_validator(mode="before")
    def __enforce_default(cls, values):
        values["metricValue"] = []
        return values

    @model_validator(mode="after")
    def __transform(cls, values):
        values.metric_of = MetricOfTimeseries(values.metric_of)
        return values

# 描述: 继承自__CardSchema，用于定义表格卡片。

# 属性:

# metric_type: 固定为table。
# metric_of: 表格度量对象，默认是用户ID。
# view_type: 表格的显示类型。
# metric_format: 表格的度量格式，默认是会话计数。
# 方法:

# __enforce_default: 在"before"阶段根据度量对象设置默认的metricValue。
# __transform: 在"after"阶段将度量对象转为对应的表格类型。
# __validator: 在"after"阶段验证度量格式是否支持特定的度量对象。
class CardTable(__CardSchema):
    metric_type: Literal[MetricType.table]
    metric_of: MetricOfTable = Field(default=MetricOfTable.user_id)
    view_type: MetricTableViewType = Field(...)
    metric_format: MetricExtendedFormatType = Field(default=MetricExtendedFormatType.session_count)

    @model_validator(mode="before")
    def __enforce_default(cls, values):
        if values.get("metricOf") is not None and values.get("metricOf") != MetricOfTable.issues:
            values["metricValue"] = []
        return values

    @model_validator(mode="after")
    def __transform(cls, values):
        values.metric_of = MetricOfTable(values.metric_of)
        return values

    @model_validator(mode="after")
    def __validator(cls, values):
        if values.metric_of not in (MetricOfTable.issues, MetricOfTable.user_browser,
                                    MetricOfTable.user_device, MetricOfTable.user_country,
                                    MetricOfTable.visited_url):
            assert values.metric_format == MetricExtendedFormatType.session_count, \
                f'metricFormat:{MetricExtendedFormatType.user_count.value} is not supported for this metricOf'
        return values

# 描述: 继承自__CardSchema，用于定义漏斗卡片。

# 属性:

# metric_type: 固定为funnel。
# metric_of: 漏斗度量对象，默认是会话计数。
# view_type: 漏斗的显示类型。
# 方法:

# __enforce_default: 在"before"阶段根据度量对象设置默认的metricOf和viewType。
# __transform: 在"after"阶段将度量对象转为对应的时间序列类型。
class CardFunnel(__CardSchema):
    metric_type: Literal[MetricType.funnel]
    metric_of: MetricOfFunnels = Field(default=MetricOfFunnels.session_count)
    view_type: MetricOtherViewType = Field(...)

    @model_validator(mode="before")
    def __enforce_default(cls, values):
        if values.get("metricOf") and not MetricOfFunnels.has_value(values["metricOf"]):
            values["metricOf"] = MetricOfFunnels.session_count
        values["viewType"] = MetricOtherViewType.other_chart
        if values.get("series") is not None and len(values["series"]) > 0:
            values["series"] = [values["series"][0]]
        return values

    @model_validator(mode="after")
    def __transform(cls, values):
        values.metric_of = MetricOfTimeseries(values.metric_of)
        return values

# 描述: 继承自__CardSchema，用于定义错误统计卡片。

# 属性:

# metric_type: 固定为errors。
# metric_of: 错误度量对象，默认是JS错误影响的会话。
# view_type: 错误统计的显示类型。
# 方法:

# __enforce_default: 在"before"阶段强制设置默认的series为空列表。
# __transform: 在"after"阶段将度量对象转为对应的错误类型。
class CardErrors(__CardSchema):
    metric_type: Literal[MetricType.errors]
    metric_of: MetricOfErrors = Field(default=MetricOfErrors.impacted_sessions_by_js_errors)
    view_type: MetricOtherViewType = Field(...)

    @model_validator(mode="before")
    def __enforce_default(cls, values):
        values["series"] = []
        return values

    @model_validator(mode="after")
    def __transform(cls, values):
        values.metric_of = MetricOfErrors(values.metric_of)
        return values

# 描述: 继承自__CardSchema，用于定义性能监控卡片。
# 属性:
# metric_type: 固定为performance。
# metric_of: 性能度量对象，默认是CPU。
# view_type: 性能监控的显示类型。
# 方法:
# __enforce_default: 在"before"阶段强制设置默认的series为空列表。
# __transform: 在"after"阶段将度量对象转为对应的性能类型。
class CardPerformance(__CardSchema):
    metric_type: Literal[MetricType.performance]
    metric_of: MetricOfPerformance = Field(default=MetricOfPerformance.cpu)
    view_type: MetricOtherViewType = Field(...)

    @model_validator(mode="before")
    def __enforce_default(cls, values):
        values["series"] = []
        return values

    @model_validator(mode="after")
    def __transform(cls, values):
        values.metric_of = MetricOfPerformance(values.metric_of)
        return values

# 描述: 继承自__CardSchema，用于定义资源监控卡片。

# 属性:

# metric_type: 固定为resources。
# metric_of: 资源度量对象，默认是缺失资源。
# view_type: 资源监控的显示类型。
# 方法:

# __enforce_default: 在"before"阶段强制设置默认的series为空列表。
# __transform: 在"after"阶段将度量对象转为对应的资源类型。
class CardResources(__CardSchema):
    metric_type: Literal[MetricType.resources]
    metric_of: MetricOfResources = Field(default=MetricOfResources.missing_resources)
    view_type: MetricOtherViewType = Field(...)

    @model_validator(mode="before")
    def __enforce_default(cls, values):
        values["series"] = []
        return values

    @model_validator(mode="after")
    def __transform(cls, values):
        values.metric_of = MetricOfResources(values.metric_of)
        return values

# 描述: 继承自__CardSchema，用于定义Web Vital卡片。

# 属性:

# metric_type: 固定为web_vital。
# metric_of: Web Vital度量对象，默认是平均CPU。
# view_type: Web Vital的显示类型。
# 方法:

# __enforce_default: 在"before"阶段强制设置默认的series为空列表。
# __transform: 在"after"阶段将度量对象转为对应的Web Vital类型。
class CardWebVital(__CardSchema):
    metric_type: Literal[MetricType.web_vital]
    metric_of: MetricOfWebVitals = Field(default=MetricOfWebVitals.avg_cpu)
    view_type: MetricOtherViewType = Field(...)

    @model_validator(mode="before")
    def __enforce_default(cls, values):
        values["series"] = []
        return values

    @model_validator(mode="after")
    def __transform(cls, values):
        values.metric_of = MetricOfWebVitals(values.metric_of)
        return values

# 描述: 继承自__CardSchema，用于定义热图卡片。

# 属性:

# metric_type: 固定为heat_map。
# metric_of: 热图度量对象，默认是热图URL。
# view_type: 热图的显示类型。
# 方法:

# __enforce_default: 在"before"阶段验证和设置必要的默认值。
# __transform: 在"after"阶段将度量对象转为对应的热图类型。
class CardHeatMap(__CardSchema):
    metric_type: Literal[MetricType.heat_map]
    metric_of: MetricOfHeatMap = Field(default=MetricOfHeatMap.heat_map_url)
    view_type: MetricOtherViewType = Field(...)

    @model_validator(mode="before")
    def __enforce_default(cls, values):
        return values

    @model_validator(mode="after")
    def __transform(cls, values):
        values.metric_of = MetricOfHeatMap(values.metric_of)
        return values

# 描述: 继承自__CardSchema，用于定义路径分析卡片。

# 属性:

# metric_type: 固定为pathAnalysis。
# metric_of: 路径分析度量对象，默认是会话计数。
# view_type: 路径分析的显示类型。
# start_type: 路径分析的起点类型，默认为"start"。
# start_point: 路径分析的起点过滤条件列表，默认为空。
# excludes: 排除的路径分析过滤条件列表，默认为空。
# 方法:

# __enforce_default: 在"before"阶段强制设置默认的viewType为other_chart。
# __clean_start_point_and_enforce_metric_value: 在"after"阶段清理起点过滤条件并强制设置metric_value。
# __validator: 在"after"阶段验证起点和排除过滤条件是否冲突。
class MetricOfInsights(str, Enum):
    issue_categories = "issueCategories"

# 描述: 继承自__CardSchema，用于定义洞察卡片。

# 属性:

# metric_type: 固定为insights。
# metric_of: 洞察度量对象，默认是问题类别。
# view_type: 洞察的显示类型。
# 方法:

# __enforce_default: 在"before"阶段强制设置默认的view_type为list_chart。
# __transform: 在"after"阶段将度量对象转为对应的洞察类型。
# restrictions: 在"after"阶段强制抛出错误，因为insights类型暂时不被支持。
class CardInsights(__CardSchema):
    metric_type: Literal[MetricType.insights]
    metric_of: MetricOfInsights = Field(default=MetricOfInsights.issue_categories)
    view_type: MetricOtherViewType = Field(...)

    @model_validator(mode="before")
    def __enforce_default(cls, values):
        values["view_type"] = MetricOtherViewType.list_chart
        return values

    @model_validator(mode="after")
    def __transform(cls, values):
        values.metric_of = MetricOfInsights(values.metric_of)
        return values

    @model_validator(mode='after')
    def restrictions(cls, values):
        raise ValueError(f"metricType:{MetricType.insights} not supported yet.")

# 描述: 用于定义路径分析系列的数据结构。
# 属性:
# name: 系列名称，可选。
# filter: 路径分析的过滤器，使用PathAnalysisSchema类型。
# density: 数据密度，范围为2到10，默认值为4。
# 方法:
# __enforce_default: 在"before"阶段验证并强制设置默认的过滤器。当filter为空时，使用startTimestamp和endTimestamp来创建默认的过滤器。
class CardPathAnalysisSeriesSchema(CardSeriesSchema):
    name: Optional[str] = Field(default=None)
    filter: PathAnalysisSchema = Field(...)
    density: int = Field(default=4, ge=2, le=10)

    @model_validator(mode="before")
    def __enforce_default(cls, values):
        if values.get("filter") is None and values.get("startTimestamp") and values.get("endTimestamp"):
            values["filter"] = PathAnalysisSchema(startTimestamp=values["startTimestamp"],
                                                  endTimestamp=values["endTimestamp"],
                                                  density=values.get("density", 4))
        return values

# 描述: 用于定义路径分析卡片的数据结构。
# 属性:
# metric_type: 固定为pathAnalysis，表示路径分析类型。
# metric_of: 路径分析的度量对象，默认是会话计数。
# view_type: 路径分析的显示类型。
# metric_value: 用于存储路径分析中的特定事件类型。
# density: 数据密度，范围为2到10，默认值为4。
# start_type: 起点类型，可以是"start"或"end"。
# start_point: 起点的过滤条件列表，默认是空列表。
# excludes: 排除的路径过滤条件列表，默认是空列表。
# series: 包含路径分析系列的列表，默认为空。
# 方法:
# __enforce_default: 在"before"阶段强制设置默认的viewType为other_chart。并且如果series列表不为空，则仅保留第一个系列。
# __clean_start_point_and_enforce_metric_value: 在"after"阶段清理start_point并确保metric_value包含所有有效的事件类型。
# __validator: 在"after"阶段验证start_point和excludes之间的冲突，确保没有相同的值出现在这两个列表中。

class CardPathAnalysis(__CardSchema):
    metric_type: Literal[MetricType.pathAnalysis]
    metric_of: MetricOfPathAnalysis = Field(default=MetricOfPathAnalysis.session_count)
    view_type: MetricOtherViewType = Field(...)
    metric_value: List[ProductAnalyticsSelectedEventType] = Field(default=[])
    density: int = Field(default=4, ge=2, le=10)

    start_type: Literal["start", "end"] = Field(default="start")
    start_point: List[PathAnalysisSubFilterSchema] = Field(default=[])
    excludes: List[PathAnalysisSubFilterSchema] = Field(default=[])

    series: List[CardPathAnalysisSeriesSchema] = Field(default=[])

    @model_validator(mode="before")
    def __enforce_default(cls, values):
        values["viewType"] = MetricOtherViewType.other_chart.value
        if values.get("series") is not None and len(values["series"]) > 0:
            values["series"] = [values["series"][0]]
        return values

    @model_validator(mode="after")
    def __clean_start_point_and_enforce_metric_value(cls, values):
        start_point = []
        for s in values.start_point:
            if len(s.value) == 0:
                continue
            start_point.append(s)
            values.metric_value.append(s.type)

        values.start_point = start_point
        values.metric_value = remove_duplicate_values(values.metric_value)

        return values

    @model_validator(mode='after')
    def __validator(cls, values):
        s_e_values = {}
        exclude_values = {}
        for f in values.start_point:
            s_e_values[f.type] = s_e_values.get(f.type, []) + f.value

        for f in values.excludes:
            exclude_values[f.type] = exclude_values.get(f.type, []) + f.value

        assert len(
            values.start_point) <= 1, f"Only 1 startPoint with multiple values OR 1 endPoint with multiple values is allowed"
        for t in exclude_values:
            for v in t:
                assert v not in s_e_values.get(t, []), f"startPoint and endPoint cannot be excluded, value: {v}"

        return values

# 描述: 定义了一个联合类型，涵盖所有不同类型的卡片数据结构，用于在自由和企业版本之间共享。
# Union of cards-schemas that doesn't change between FOSS and EE
__cards_union_base = Union[
    CardTimeSeries, CardTable, CardFunnel,
    CardErrors, CardPerformance, CardResources,
    CardWebVital, CardHeatMap,
    CardPathAnalysis]
CardSchema = ORUnion(Union[__cards_union_base, CardInsights], discriminator='metric_type')


# 描述: 用于更新卡片状态的数据结构。
# 属性:
# active: 表示卡片是否激活的布尔值。
class UpdateCardStatusSchema(BaseModel):
    active: bool = Field(...)

# 描述: 用于保存搜索条件的数据结构。
# 属性:
# name: 搜索条件名称。
# is_public: 搜索条件是否公开，默认为False。
# filter: 使用SessionsSearchPayloadSchema定义的过滤条件。
class SavedSearchSchema(BaseModel):
    name: str = Field(...)
    is_public: bool = Field(default=False)
    filter: SessionsSearchPayloadSchema = Field([])

# 描述: 用于定义项目条件的数据结构。
# 属性:
# condition_id: 条件ID，可选。
# name: 条件名称。
# capture_rate: 捕获率，范围为0到100。
# filters: 过滤条件的列表，默认为空。
class ProjectConditions(BaseModel):
    condition_id: Optional[int] = Field(default=None)
    name: str = Field(...)
    capture_rate: int = Field(..., ge=0, le=100)
    filters: List[GroupedFilterType] = Field(default=[])

# 描述: 用于定义项目设置的数据结构。
# 属性:
# rate: 项目的捕获率，范围为0到100。
# conditional_capture: 是否进行条件捕获的布尔值。
# conditions: 项目的条件列表，使用ProjectConditions定义。
class ProjectSettings(BaseModel):
    rate: int = Field(..., ge=0, le=100)
    conditional_capture: bool = Field(default=False)
    conditions: List[ProjectConditions] = Field(default=[])

# 描述: 用于创建仪表板的数据结构。
# 属性:
# name: 仪表板名称，长度最少为1。
# description: 仪表板描述，可选，默认为空字符串。
# is_public: 仪表板是否公开，默认为False。
# is_pinned: 仪表板是否置顶，默认为False。
# metrics: 包含的指标ID列表，可选。
class CreateDashboardSchema(BaseModel):
    name: str = Field(..., min_length=1)
    description: Optional[str] = Field(default='')
    is_public: bool = Field(default=False)
    is_pinned: bool = Field(default=False)
    metrics: Optional[List[int]] = Field(default=[])

# 描述: 继承自CreateDashboardSchema，用于编辑仪表板。
# 属性:
# is_public: 仪表板是否公开，可选。
# is_pinned: 仪表板是否置顶，可选。
class EditDashboardSchema(CreateDashboardSchema):
    is_public: Optional[bool] = Field(default=None)
    is_pinned: Optional[bool] = Field(default=None)

# 描述: 用于更新小组件配置的数据结构。
# 属性:
# config: 小组件的配置，默认为空字典。
class UpdateWidgetPayloadSchema(BaseModel):
    config: dict = Field(default={})

# 描述: 继承自UpdateWidgetPayloadSchema，用于将小组件添加到仪表板。
# 属性:
# metric_id: 要添加的小组件的指标ID。
class AddWidgetToDashboardPayloadSchema(UpdateWidgetPayloadSchema):
    metric_id: int = Field(...)

# 描述: 定义了一些预定义的单位类型，用于度量显示。
# 枚举值:
# millisecond: 毫秒
# second: 秒
# minute: 分钟
# memory: 内存，以MB为单位
# frame: 帧率，以帧每秒为单位
# percentage: 百分比
# count: 计数
class TemplatePredefinedUnits(str, Enum):
    millisecond = "ms"
    second = "s"
    minute = "min"
    memory = "mb"
    frame = "f/s"
    percentage = "%"
    count = "count"

# 描述: 定义了会话搜索的实时过滤器类型。
# 枚举值:
# user_os: 用户操作系统
# user_browser: 用户浏览器
# user_device: 用户设备
# user_country: 用户国家
# user_id: 用户ID
# user_anonymous_id: 用户匿名ID
# rev_id: 版本ID
# platform: 平台
# page_title: 页面标题
# session_id: 会话ID
# metadata: 元数据
# user_UUID: 用户UUID
# tracker_version: 跟踪器版本
# user_browser_version: 用户浏览器版本
# user_device_type: 用户设备类型
class LiveFilterType(str, Enum):
    user_os = FilterType.user_os.value
    user_browser = FilterType.user_browser.value
    user_device = FilterType.user_device.value
    user_country = FilterType.user_country.value
    user_id = FilterType.user_id.value
    user_anonymous_id = FilterType.user_anonymous_id.value
    rev_id = FilterType.rev_id.value
    platform = FilterType.platform.value
    page_title = "pageTitle"
    session_id = "sessionId"
    metadata = FilterType.metadata.value
    user_UUID = "userUuid"
    tracker_version = "trackerVersion"
    user_browser_version = "userBrowserVersion"
    user_device_type = "userDeviceType"

# 描述: 用于定义实时会话搜索的过滤器。

# 属性:

# value: 过滤值，可以是字符串或字符串列表。
# type: 过滤器类型，使用LiveFilterType定义。
# source: 数据源，可选。
# operator: 过滤器操作符，可以是_is或_contains。
# 方法:

# __validator: 在"after"阶段验证metadata类型的过滤器是否具有有效的source。
class LiveSessionSearchFilterSchema(BaseModel):
    value: Union[List[str], str] = Field(...)
    type: LiveFilterType = Field(...)
    source: Optional[str] = Field(default=None)
    operator: Literal[SearchEventOperator._is, \
        SearchEventOperator._contains] = Field(default=SearchEventOperator._contains)

    _transform = model_validator(mode='before')(transform_old_filter_type)

    @model_validator(mode='after')
    def __validator(cls, values):
        if values.type is not None and values.type == LiveFilterType.metadata:
            assert values.source is not None, "source should not be null for METADATA type"
            assert len(values.source) > 0, "source should not be empty for METADATA type"
        return values

# 描述: 用于定义实时会话搜索的请求负载。

# 属性:

# filters: 过滤器的列表，使用LiveSessionSearchFilterSchema定义。
# sort: 排序字段，默认是时间戳。
# order: 排序顺序，默认是降序。
# 方法:

# __transform: 在"before"阶段处理排序和过滤器中的特殊条件。
class LiveSessionsSearchPayloadSchema(_PaginatedSchema):
    filters: List[LiveSessionSearchFilterSchema] = Field([])
    sort: Union[LiveFilterType, str] = Field(default="TIMESTAMP")
    order: SortOrderType = Field(default=SortOrderType.desc)

    @model_validator(mode="before")
    def __transform(cls, values):
        if values.get("order") is not None:
            values["order"] = values["order"].upper()
        if values.get("filters") is not None:
            i = 0
            while i < len(values["filters"]):
                if values["filters"][i]["value"] is None or len(values["filters"][i]["value"]) == 0:
                    del values["filters"][i]
                else:
                    i += 1
            for i in values["filters"]:
                if i.get("type") == LiveFilterType.platform:
                    i["type"] = LiveFilterType.user_device_type
        if values.get("sort") is not None:
            if values["sort"].lower() == "startts":
                values["sort"] = "TIMESTAMP"
        return values

# 描述: 定义了集成类型的枚举。
# 枚举值:
# github: GitHub
# jira: Jira
# slack: Slack
# ms_teams: Microsoft Teams
# sentry: Sentry
# bugsnag: Bugsnag
# rollbar: Rollbar
# elasticsearch: Elasticsearch
# datadog: Datadog
# sumologic: Sumo Logic
# stackdriver: Stackdriver
# cloudwatch: AWS CloudWatch
# newrelic: New Relic
class IntegrationType(str, Enum):
    github = "GITHUB"
    jira = "JIRA"
    slack = "SLACK"
    ms_teams = "MSTEAMS"
    sentry = "SENTRY"
    bugsnag = "BUGSNAG"
    rollbar = "ROLLBAR"
    elasticsearch = "ELASTICSEARCH"
    datadog = "DATADOG"
    sumologic = "SUMOLOGIC"
    stackdriver = "STACKDRIVER"
    cloudwatch = "CLOUDWATCH"
    newrelic = "NEWRELIC"

# 描述: 用于定义搜索笔记的请求负载。
# 属性:
# sort: 排序字段，默认是创建时间。
# order: 排序顺序，默认是降序。
# tags: 标签列表，可选。
# shared_only: 仅搜索共享的笔记，默认为False。
# mine_only: 仅搜索自己的笔记，默认为False。
class SearchNoteSchema(_PaginatedSchema):
    sort: str = Field(default="createdAt")
    order: SortOrderType = Field(default=SortOrderType.desc)
    tags: Optional[List[str]] = Field(default=[])
    shared_only: bool = Field(default=False)
    mine_only: bool = Field(default=False)

# 描述: 用于定义会话笔记的数据结构。
# 属性:
# message: 笔记内容，最少2个字符。
# tag: 笔记标签，可选。
# timestamp: 笔记时间戳，默认为-1。
# is_public: 笔记是否公开，默认为False。
class SessionNoteSchema(BaseModel):
    message: str = Field(..., min_length=2)
    tag: Optional[str] = Field(default=None)
    timestamp: int = Field(default=-1)
    is_public: bool = Field(default=False)

# 描述: 继承自SessionNoteSchema，用于更新会话笔记。

# 属性:

# message: 笔记内容，可选。
# timestamp: 笔记时间戳，可选。
# is_public: 笔记是否公开，可选。
# 方法:

# __validator: 在"after"阶段确保至少提供一个属性进行更新。
class SessionUpdateNoteSchema(SessionNoteSchema):
    message: Optional[str] = Field(default=None, min_length=2)
    timestamp: Optional[int] = Field(default=None, ge=-1)
    is_public: Optional[bool] = Field(default=None)

    @model_validator(mode='after')
    def __validator(cls, values):
        assert values.message is not None or values.timestamp is not None or values.is_public is not None, "at least 1 attribute should be provided for update"
        return values

# 描述: 定义了Webhook类型的枚举。
# 枚举值:
# webhook: Webhook
# slack: Slack
# email: Email
# msteams: Microsoft Teams
class WebhookType(str, Enum):
    webhook = "webhook"
    slack = "slack"
    email = "email"
    msteams = "msteams"

# 描述: 用于定义搜索卡片的请求负载。
# 属性:
# order: 排序顺序，默认是降序。
# shared_only: 仅搜索共享的卡片，默认为False。
# mine_only: 仅搜索自己的卡片，默认为False。
# query: 查询字符串，可选。
class SearchCardsSchema(_PaginatedSchema):
    order: SortOrderType = Field(default=SortOrderType.desc)
    shared_only: bool = Field(default=False)
    mine_only: bool = Field(default=False)
    query: Optional[str] = Field(default=None)

# 描述: 用于定义热图搜索的原始事件数据结构。
# 属性:
# type: 固定为位置事件。
class _HeatMapSearchEventRaw(SessionSearchEventSchema2):
    type: Literal[EventType.location] = Field(...)

# 描述: 用于定义热图会话搜索的请求负载。

# 属性:

# events: 热图相关的事件列表，默认为空。
# filters: 过滤器列表，可以是会话搜索过滤器或热图事件。
# 方法:

# __transform: 在"before"阶段确保包含持续时间过滤器。
class HeatMapSessionsSearch(SessionsSearchPayloadSchema):
    events: Optional[List[_HeatMapSearchEventRaw]] = Field(default=[])
    filters: List[Union[SessionSearchFilterSchema, _HeatMapSearchEventRaw]] = Field(default=[])

    @model_validator(mode="before")
    def __transform(cls, values):
        for f in values.get("filters", []):
            if f.get("type") == FilterType.duration:
                return values
        values["filters"] = values.get("filters", [])
        values["filters"].append({"value": [5000], "type": FilterType.duration,
                                  "operator": SearchEventOperator._is, "filters": []})
        return values

# 描述: 用于定义热图过滤器的数据结构。
# 属性:
# value: 过滤值列表，仅支持点击暴怒和死点击事件。
# type: 过滤器类型，固定为issue。
# operator: 过滤器操作符，固定为_is或_equal。
class HeatMapFilterSchema(BaseModel):
    value: List[Literal[IssueType.click_rage, IssueType.dead_click]] = Field(default=[])
    type: Literal[FilterType.issue] = Field(...)
    operator: Literal[SearchEventOperator._is, MathOperator._equal] = Field(...)

# 描述: 用于定义获取热图请求的负载。
# 属性:
# url: 热图的URL。
# filters: 过滤器列表，默认为空。
# click_rage: 是否包含点击暴怒的布尔值，默认为False。
class GetHeatMapPayloadSchema(_TimedSchema):
    url: str = Field(...)
    filters: List[HeatMapFilterSchema] = Field(default=[])
    click_rage: bool = Field(default=False)

# 描述: 继承自GetHeatMapPayloadSchema，用于获取点击图的请求负载。
class GetClickMapPayloadSchema(GetHeatMapPayloadSchema):
    pass

# 描述: 用于定义特性标志变体的数据结构。
# 属性:
# variant_id: 变体ID，可选。
# value: 变体的值。
# description: 变体的描述，可选。
# payload: 变体的载荷，可选。
# rollout_percentage: 变体的发布比例，范围为0到100，可选。
class FeatureFlagVariant(BaseModel):
    variant_id: Optional[int] = Field(default=None)
    value: str = Field(...)
    description: Optional[str] = Field(default=None)
    payload: Optional[str] = Field(default=None)
    rollout_percentage: Optional[int] = Field(default=0, ge=0, le=100)

# 描述: 用于定义特性标志条件的过滤器。

# 属性:

# is_event: 是否为事件过滤器，固定为False。
# type: 过滤器类型。
# value: 过滤值列表，最少1个值。
# operator: 过滤器操作符，可以是事件操作符或数学操作符。
# source: 数据源，可选。
# sourceOperator: 数据源操作符，可选。
# 方法:

# __force_is_event: 在"before"阶段强制设置is_event为False。
class FeatureFlagConditionFilterSchema(BaseModel):
    is_event: Literal[False] = False
    type: FilterType = Field(...)
    value: List[str] = Field(default=[], min_length=1)
    operator: Union[SearchEventOperator, MathOperator] = Field(...)
    source: Optional[str] = Field(default=None)
    sourceOperator: Optional[Union[SearchEventOperator, MathOperator]] = Field(default=None)

    @model_validator(mode="before")
    def __force_is_event(cls, values):
        values["isEvent"] = False
        return values

# 描述: 用于定义特性标志条件的数据结构。
# 属性:
# condition_id: 条件ID，可选。
# name: 条件名称。
# rollout_percentage: 条件的发布比例，默认值为0。
# filters: 条件的过滤器列表。
class FeatureFlagCondition(BaseModel):
    condition_id: Optional[int] = Field(default=None)
    name: str = Field(...)
    rollout_percentage: Optional[int] = Field(default=0)
    filters: List[FeatureFlagConditionFilterSchema] = Field(default=[])

# 描述: 用于定义搜索特性标志的请求负载。
# 属性:
# limit: 返回结果的最大数量，范围为1到200。
# user_id: 用户ID，可选。
# order: 排序顺序，默认是降序。
# query: 查询字符串，可选。
# is_active: 仅搜索激活的标志，默认为None。
class SearchFlagsSchema(_PaginatedSchema):
    limit: int = Field(default=15, gt=0, le=200)
    user_id: Optional[int] = Field(default=None)
    order: SortOrderType = Field(default=SortOrderType.desc)
    query: Optional[str] = Field(default=None)
    is_active: Optional[bool] = Field(default=None)

# 描述: 定义了特性标志类型的枚举。
# 枚举值:
# single_variant: 单变体
# multi_variant: 多变体
class FeatureFlagType(str, Enum):
    single_variant = "single"
    multi_variant = "multi"

# 描述: 用于定义特性标志状态的数据结构。
# 属性:
# is_active: 标志是否激活的布尔值。
class FeatureFlagStatus(BaseModel):
    is_active: bool = Field(...)

# 描述: 用于定义特性标志的数据结构。
# 属性:
# payload: 标志的载荷，可选。
# flag_key: 标志的键值，必须匹配正则表达式^[a-zA-Z0-9\-]+$。
# description: 标志的描述，可选。
# flag_type: 标志类型，使用FeatureFlagType定义。
# is_persist: 标志是否持久化，默认为False。
# is_active: 标志是否激活，默认为True。
# conditions: 标志的条件列表，至少有一个条件。
# variants: 标志的变体列表。
class FeatureFlagSchema(BaseModel):
    payload: Optional[str] = Field(default=None)
    flag_key: str = Field(..., pattern=r'^[a-zA-Z0-9\-]+$')
    description: Optional[str] = Field(default=None)
    flag_type: FeatureFlagType = Field(default=FeatureFlagType.single_variant)
    is_persist: Optional[bool] = Field(default=False)
    is_active: Optional[bool] = Field(default=True)
    conditions: List[FeatureFlagCondition] = Field(default=[], min_length=1)
    variants: List[FeatureFlagVariant] = Field(default=[])

# 描述: 用于定义模块状态的数据结构。
# 属性:
# module: 模块名称，可能的值包括assist、notes、bug-reports等。
# status: 模块是否激活的布尔值。
class ModuleStatus(BaseModel):
    module: Literal["assist", "notes", "bug-reports",
    "offline-recordings", "alerts", "assist-statts", "recommendations", "feature-flags"] = Field(...,
                                                                                                 description="Possible values: assist, notes, bug-reports, offline-recordings, alerts, assist-statts, recommendations, feature-flags")
    status: bool = Field(...)

# 描述: 用于更新标签的数据结构。
# 属性:
# name: 标签名称，最少1个字符，最多100个字符，必须匹配正则表达式^[a-zA-Z0-9\" -]*$。
class TagUpdate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, pattern='^[a-zA-Z0-9\" -]*$')

# 描述: 继承自TagUpdate，用于创建标签。
# 属性:
# selector: 标签选择器，最少1个字符，最多255个字符。
# ignoreClickRage: 是否忽略点击暴怒的布尔值，默认为False。
# ignoreDeadClick: 是否忽略死点击的布尔值，默认为False。
class TagCreate(TagUpdate):
    selector: str = Field(..., min_length=1, max_length=255)
    ignoreClickRage: bool = Field(default=False)
    ignoreDeadClick: bool = Field(default=False)
