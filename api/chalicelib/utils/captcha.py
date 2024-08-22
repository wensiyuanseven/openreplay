# 这段代码用于验证 CAPTCHA 响应的有效性，主要用于判断用户提交的 CAPTCHA 是否通过验证。
import logging

import requests
from decouple import config

from chalicelib.utils import helper

logger = logging.getLogger(__name__)

# 功能描述:
# 该函数从环境变量中获取 CAPTCHA 服务器的 URL 和密钥，并返回它们。
# 返回值:
# 返回一个包含 CAPTCHA 服务器 URL 和密钥的元组 (captcha_server, captcha_key)。
# 应用场景:
# 在需要与 CAPTCHA 服务交互时，获取必要的配置信息。
def __get_captcha_config():
    return config("captcha_server"), config("captcha_key")

# 功能描述:
# 该函数用于验证用户提交的 CAPTCHA 响应是否有效。
# 首先，它会检查是否启用了 CAPTCHA 功能（通过 helper.allow_captcha()），如果未启用，直接返回 True，表示验证通过。
# 如果启用了 CAPTCHA 功能，则会向 CAPTCHA 服务器发送一个 POST 请求，包含密钥和用户的响应数据。
# 如果请求成功且 CAPTCHA 服务返回的结果中 success 字段为 True，则返回 True，否则返回 False。
# 参数说明:
# response: 用户提交的 CAPTCHA 响应字符串。
# 返回值:
# True 如果 CAPTCHA 验证成功。
# False 如果验证失败或请求过程中发生了错误。
def is_valid(response):
    if not helper.allow_captcha():
        logger.info("!! Captcha is disabled")
        return True
    url, secret = __get_captcha_config()
    r = requests.post(url=url, data={"secret": secret, "response": response})
    if r.status_code != 200:
        logger.warning("something went wrong")
        logger.error(r)
        logger.warning(r.status_code)
        logger.warning(r.text)
        return
    r = r.json()
    logger.debug(r)
    return r["success"]
