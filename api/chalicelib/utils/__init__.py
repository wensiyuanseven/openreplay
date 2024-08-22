# 这段代码用于检测是否有有效的 SMTP（简单邮件传输协议）配置，并根据检查结果记录日志。SMTP 配置通常用于应用程序发送电子邮件通知等功能。
from . import smtp
import logging
from decouple import config

logging.basicConfig(level=config("LOGLEVEL", default=logging.INFO))


# 功能描述:
# 调用 smtp.has_smtp() 方法来检查是否存在有效的 SMTP 配置。
# 如果存在有效的 SMTP 配置，记录一条 INFO 级别的日志消息：“valid SMTP configuration found”（找到有效的 SMTP 配置）。
# 如果未找到有效的 SMTP 配置，或者配置验证失败，则记录一条 INFO 级别的日志消息：“no SMTP configuration found or SMTP validation failed”（未找到 SMTP 配置或 SMTP 验证失败）。
if smtp.has_smtp():
    logging.info("valid SMTP configuration found")
else:
    logging.info("no SMTP configuration found or SMTP validation failed")
