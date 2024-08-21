# 这段代码定义了一个异步函数 create_tenant，用于处理新租户（tenant）的创建请求。该函数主要用于用户注册流程，
# 验证输入的数据，并在数据库中创建租户、用户、以及初始项目。在成功创建后，函数返回相关的身份验证信息和用户数据。
import json
import logging

import schemas
from chalicelib.core import users, telemetry, tenants
from chalicelib.utils import captcha, smtp
from chalicelib.utils import helper
from chalicelib.utils import pg_client
from chalicelib.utils.TimeUTC import TimeUTC

logger = logging.getLogger(__name__)

# 功能描述:
# 该函数用于处理用户注册请求，验证用户输入的数据是否合法，包括邮箱、密码、全名、以及组织名称。如果数据有效，函数将在数据库中创建新租户和用户，并初始化一个项目。最终返回包含 JWT 和用户信息的字典。

# 参数:

# data: 类型为 schemas.UserSignupSchema 的对象，包含用户提交的注册信息，例如邮箱、密码、全名、组织名称等。
# 返回值:


# dict: 如果注册成功，返回一个包含 JWT 令牌、刷新令牌和用户信息的字典；如果失败，返回包含错误信息的字典。
async def create_tenant(data: schemas.UserSignupSchema):
    logger.info(f"==== Signup started at {TimeUTC.to_human_readable(TimeUTC.now())} UTC")
    errors = []
    if await tenants.tenants_exists():
        return {"errors": ["tenants already registered"]}

    email = data.email
    logger.debug(f"email: {email}")
    password = data.password.get_secret_value()

    if email is None or len(email) < 5:
        errors.append("Invalid email address.")
    else:
        if users.email_exists(email):
            errors.append("Email address already in use.")
        if users.get_deleted_user_by_email(email) is not None:
            errors.append("Email address previously deleted.")

    if helper.allow_captcha() and not captcha.is_valid(data.g_recaptcha_response):
        errors.append("Invalid captcha.")

    if len(password) < 6:
        errors.append("Password is too short, it must be at least 6 characters long.")

    fullname = data.fullname
    if fullname is None or len(fullname) < 1 or not helper.is_alphabet_space_dash(fullname):
        errors.append("Invalid full name.")

    organization_name = data.organizationName
    if organization_name is None or len(organization_name) < 1:
        errors.append("Invalid organization name.")

    if len(errors) > 0:
        logger.warning(f"==> signup error for:\n email:{data.email}, fullname:{data.fullname}, organizationName:{data.organizationName}")
        logger.warning(errors)
        return {"errors": errors}

    project_name = "my first project"
    params = {"email": email, "password": password, "fullname": fullname, "projectName": project_name, "data": json.dumps({"lastAnnouncementView": TimeUTC.now()}), "organizationName": organization_name}
    query = f"""WITH t AS (
                    INSERT INTO public.tenants (name)
                        VALUES (%(organizationName)s)
                    RETURNING api_key
                ),
                 u AS (
                     INSERT INTO public.users (email, role, name, data)
                             VALUES (%(email)s, 'owner', %(fullname)s,%(data)s)
                             RETURNING user_id,email,role,name
                 ),
                 au AS (
                     INSERT INTO public.basic_authentication (user_id, password)
                         VALUES ((SELECT user_id FROM u), crypt(%(password)s, gen_salt('bf', 12)))
                 )
                 INSERT INTO public.projects (name, active)
                 VALUES (%(projectName)s, TRUE)
                 RETURNING project_id, (SELECT api_key FROM t) AS api_key;"""

    with pg_client.PostgresClient() as cur:
        cur.execute(cur.mogrify(query, params))

    telemetry.new_client()
    r = users.authenticate(email, password)
    r["smtp"] = smtp.has_smtp()

    return {"jwt": r.pop("jwt"), "refreshToken": r.pop("refreshToken"), "refreshTokenMaxAge": r.pop("refreshTokenMaxAge"), "data": {"user": r}}


# 该函数依赖多个外部模块和函数，如 tenants.tenants_exists、captcha.is_valid、pg_client.PostgresClient 等，因此在生产环境中使用前需要确保这些依赖已正确配置和测试。
# 由于这是一个异步函数，确保在调用它的上下文中正确处理异步操作。
# 密码的加密使用了 crypt 函数和 Blowfish 算法（bf），确保数据库支持此加密算法。
# 数据库操作应当放在事务中处理，确保操作的原子性，避免在多租户环境下产生数据一致性问题。
