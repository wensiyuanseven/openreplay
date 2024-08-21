# SMTP，全称为 Simple Mail Transfer Protocol，即“简单邮件传输协议”。它是一种用于在网络中发送和接收电子邮件的协议。
# SMTP 是互联网邮件服务的基础，通过它，邮件客户端可以将邮件发送到邮件服务器，邮件服务器之间也可以通过 SMTP 传输邮件。

# 这个文件的主要目的是提供一个用于发送电子邮件的 SMTP 客户端封装，并确保在发邮件之前正确配置和测试 SMTP 服务器连接。

# 通过日志记录和异常处理，它能确保在邮件发送过程中的错误被及时捕获和报告，同时提供了一种优雅的方式管理 SMTP 连接的生命周期。
import logging

# Python 标准库中的一个模块，用于发送邮件。smtplib 提供了 SMTP 客户端类和方法来与 SMTP 服务器进行通信，包括发送邮件、登录、启动 TLS 连接等功能。
import smtplib

# SMTPAuthenticationError 是 smtplib 中的一个异常类，表示 SMTP 认证失败时会引发该异常。
from smtplib import SMTPAuthenticationError

from decouple import config
from fastapi import HTTPException


# 作用: EmptySMTP 是一个占位类，当没有有效的 SMTP 配置时，它被用作发送邮件的替代类。
# 它不会真正发送邮件，而是记录一条错误日志，指出没有有效的 SMTP 配置。
class EmptySMTP:
    # 这些方法模拟了标准的 SMTP 发送邮件操作，但只是简单地记录错误日志而不执行实际的邮件发送操作。
    def sendmail(self, from_addr, to_addrs, msg, mail_options=(), rcpt_options=()):
        logging.error("!! 无法发送电子邮件，找不到有效的SMTP配置")

    def send_message(self, msg):
        self.sendmail(msg["FROM"], msg["TO"], msg.as_string())


# 实际处理 SMTP 连接的类，负责初始化连接，处理安全选项（如 TLS/SSL），并提供上下文管理支持。
class SMTPClient:
    server = None

    # 不同方式的连接
    def __init__(self):
        # 查是否配置了 EMAIL_HOST，即 SMTP 服务器的主机地址。如果没有配置主机地址，函数将返回。self.server 保持为 None。
        if config("EMAIL_HOST") is None or len(config("EMAIL_HOST")) == 0:
            return
        # 检查是否配置了 SSL。如果未配置 SSL (EMAIL_USE_SSL 为 False)，则使用普通的 SMTP 连接。
        elif not config("EMAIL_USE_SSL", cast=bool):
            self.server = smtplib.SMTP(host=config("EMAIL_HOST"), port=config("EMAIL_PORT", cast=int))
        # 如果不使用 SSL，创建一个普通的 SMTP 连接，指定主机 (EMAIL_HOST) 和端口
        else:
            # 检查是否提供了 SSL 证书和密钥文件。如果未提供，则创建一个简单的 SSL SMTP 连接。
            if len(config("EMAIL_SSL_KEY")) == 0 or len(config("EMAIL_SSL_CERT")) == 0:
                self.server = smtplib.SMTP_SSL(host=config("EMAIL_HOST"), port=config("EMAIL_PORT", cast=int))
            # 如果提供了 SSL 证书和密钥文件，则使用这些文件创建一个 SSL SMTP 连接。
            else:
                self.server = smtplib.SMTP_SSL(host=config("EMAIL_HOST"), port=config("EMAIL_PORT", cast=int), keyfile=config("EMAIL_SSL_KEY"), certfile=config("EMAIL_SSL_CERT"))

    def __enter__(self):
        # 检查 server 是否已初始化。如果没有初始化，返回 EmptySMTP()，这是一个占位类，表示没有有效的 SMTP 配置。
        if self.server is None:
            return EmptySMTP()
        # 向 SMTP 服务器发送 EHLO 命令，表示客户端的身份，并请求服务器的扩展功能。
        self.server.ehlo()
        # 检查是否配置使用 TLS。如果配置了 TLS 并且未使用 SSL，则启动 TLS。
        if not config("EMAIL_USE_SSL", cast=bool) and config("EMAIL_USE_TLS", cast=bool):
            # 启动 TLS 加密，切换到安全连接模式。
            self.server.starttls()
            # stmplib docs recommend calling ehlo() before & after starttls()
            # 再次发送 EHLO 命令，因为切换到 TLS 后需要重新确认连接状态。
            self.server.ehlo()
        # 检查是否提供了 SMTP 用户名和密码。如果提供了，则尝试登录 SMTP 服务器。
        if len(config("EMAIL_USER", default="")) > 0 and len(config("EMAIL_PASSWORD", default="")) > 0:

            try:
                # 使用提供的用户名和密码登录 SMTP 服务器。
                self.server.login(user=config("EMAIL_USER"), password=config("EMAIL_PASSWORD"))
            except SMTPAuthenticationError:
                # 如果登录失败，抛出 SMTPAuthenticationError 异常，并在 HTTP 响应中返回 401 错误。
                raise HTTPException(401, "SMTP Authentication Error")
            # 返回 SMTP 连接对象，以便在 with 语句中使用。
        return self.server

    # 这个方法实现了上下文管理协议，使得 SMTPClient 可以与 with 语句一起使用。它负责连接服务器、启动 TLS（如果需要）、并执行身份验证。
    def __exit__(self, *args):
        if self.server is None:
            return
        # 作用: 这个方法在 with 语句结束时调用，负责关闭 SMTP 连接。
        self.server.quit()

    def test_configuration(self):
        # check server connexion
        try:
            status = self.server.noop()[0]
            if not (status == 250):
                raise Exception(f"SMTP 连接错误, status:{status}")
        except Exception as e:  # smtplib.SMTPServerDisconnected
            logging.error(f'!! SMTP 连接错误 {config("EMAIL_HOST")}:{config("EMAIL_PORT", cast=int)}')
            logging.error(e)
            return False, e

        # check authentication
        try:
            self.__enter__()
            self.__exit__()
        except Exception as e:
            logging.error(f'!! SMTP 身份验证错误 {config("EMAIL_HOST")}:{config("EMAIL_PORT", cast=int)}')
            logging.error(e)
            return False, e

        return True, None


VALID_SMTP = None
SMTP_ERROR = None
SMTP_NOTIFIED = False


# 这个函数检查 SMTP 配置是否可用。如果之前的配置测试失败，会记录错误日志。
# 如果配置有效，则返回 True，否则返回 False。
def has_smtp():
    global VALID_SMTP, SMTP_ERROR, SMTP_NOTIFIED
    if SMTP_ERROR is not None:
        logging.error("!!! 发现 SMTP 错误，禁用 SMTP 配置:")
        logging.error(SMTP_ERROR)

    if VALID_SMTP is not None:
        return VALID_SMTP

    if config("EMAIL_HOST") is not None and len(config("EMAIL_HOST")) > 0:
        VALID_SMTP, SMTP_ERROR = check_connexion()
        return VALID_SMTP
    elif not SMTP_NOTIFIED:
        SMTP_NOTIFIED = True
        logging.info("未找到 SMTP 配置")
    return False


def check_connexion():
    # check SMTP host&port
    import socket

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(config("EMAIL_CHECK_TIMEOUT", cast=int, default=5))
    result = sock.connect_ex((config("EMAIL_HOST"), config("EMAIL_PORT", cast=int)))
    sock.close()
    if not (result == 0):
        error = f"""!! SMTP {config("EMAIL_HOST")}:{config("EMAIL_PORT", cast=int)} 无法访问.请确保主机和端口正确，并且您的服务器上已授权 SMTP 协议."""
        logging.error(error)
        sock.close()
        return False, error

    return SMTPClient().test_configuration()
