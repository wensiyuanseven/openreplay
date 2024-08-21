# 这段代码实现了一个用于处理忘记密码请求的函数reset，该函数主要负责接收用户的忘记密码请求，并通过背景任务发送重置密码的电子邮件。
# 如果请求中的验证码验证通过且系统配置了SMTP服务器，系统会生成一个新的邀请链接并通过电子邮件发送给用户。
# 如果邮箱不存在，系统会记录一个警告日志，并返回一个通用的信息。

# 注意事项
# 异步操作: 密码重置邮件的发送通过BackgroundTasks在后台异步执行，这样可以加快API响应速度，不需要等待邮件发送完成。
# 通用信息返回: 为了安全性，不直接暴露系统中是否存在某个邮箱，返回的信息是通用的，即使邮箱不存在也不会明确告知用户。
# 这段代码通过使用日志、验证码验证和异步任务管理，实现了一个健壮的忘记密码功能。如果有进一步的问题或需要更多帮助，请随时告知我！
import logging

from fastapi import BackgroundTasks

import schemas
from chalicelib.core import users
from chalicelib.utils import email_helper, captcha, helper, smtp

logger = logging.getLogger(__name__)

# 功能描述：
# 处理忘记密码请求，验证验证码并生成密码重置链接，通过电子邮件发送给用户。

# 参数：
# data: schemas.ForgetPasswordPayloadSchema类型，包含用户提交的忘记密码请求数据，包括邮箱和验证码。
# background_tasks: BackgroundTasks类型，FastAPI 提供的后台任务，用于在请求完成后异步执行任务。
# 返回值：
# dict: 返回一个包含操作状态的字典。如果请求合法且邮箱存在，返回一个通用的信息；如果验证码无效或没有配置SMTP服务器，返回错误信息。
def reset(data: schemas.ForgetPasswordPayloadSchema, background_tasks: BackgroundTasks):
    logger.info(f"forget password request for: {data.email}")
    if helper.allow_captcha() and not captcha.is_valid(data.g_recaptcha_response):
        return {"errors": ["Invalid captcha."]}
    if not smtp.has_smtp():
        return {"errors": ["no SMTP configuration found, you can ask your admin to reset your password"]}
    a_user = users.get_by_email_only(data.email)
    if a_user:
        invitation_link = users.generate_new_invitation(user_id=a_user["userId"])
        background_tasks.add_task(email_helper.send_forgot_password,
                                  recipient=data.email,
                                  invitation_link=invitation_link)
    else:
        logger.warning(f"!!!invalid email address [{data.email}]")
    return {"data": {"state": "A reset link will be sent if this email exists in our system."}}
