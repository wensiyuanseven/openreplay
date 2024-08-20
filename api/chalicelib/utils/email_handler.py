import logging
import re
from email.header import Header
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from decouple import config

from chalicelib.utils import smtp

logger = logging.getLogger(__name__)


def __get_html_from_file(source, formatting_variables):
    if formatting_variables is None:
        formatting_variables = {}
    formatting_variables["frontend_url"] = config("SITE_URL")
    with open(source, "r") as body:
        BODY_HTML = body.read()
        if formatting_variables is not None and len(formatting_variables.keys()) > 0:
            BODY_HTML = re.sub(r"%(?![(])", "%%", BODY_HTML)
            BODY_HTML = BODY_HTML % {**formatting_variables}
    return BODY_HTML


def __replace_images(HTML):
    pattern_holder = re.compile(r'<img[\w\W\n]+?(src="[a-zA-Z0-9.+\/\\-]+")')
    pattern_src = re.compile(r'src="(.*?)"')
    mime_img = []
    swap = []
    for m in re.finditer(pattern_holder, HTML):
        sub = m.groups()[0]
        sub = str(re.findall(pattern_src, sub)[0])
        if sub not in swap:
            swap.append(sub)
            cid = f"img-{len(mime_img)}"
            HTML = HTML.replace(sub, f"cid:{cid}")
            sub = "chalicelib/utils/html/" + sub
            with open(sub, "rb") as image_file:
                img_data = image_file.read()
            mime_img.append(MIMEImage(img_data))
            mime_img[-1].add_header("Content-ID", f"<{cid}>")
    return HTML, mime_img

# send_html 函数的作用是：
# 处理包含图片的 HTML 正文，确保图片在邮件中正确显示。
# 生成一个包含 HTML 正文和相关图片的电子邮件对象。
# 使用 SMTP 客户端将邮件发送给一个或多个收件人。
# 在发送过程中记录操作日志，并处理可能的错误。
# 这个函数在需要发送包含复杂 HTML 内容的邮件时非常有用，尤其是当邮件包含内嵌图片时。
def send_html(BODY_HTML, SUBJECT, recipient):
    # 处理 HTML 正文中的图片:
    BODY_HTML, mime_img = __replace_images(BODY_HTML)
    # 检查 recipient 是否是列表。如果不是，则将其转换为列表。这是为了确保后续的代码能够正确地处理多个收件人。
    if not isinstance(recipient, list):
        recipient = [recipient]
    # MIMEMultipart('related'): 创建一个多部分的 MIME 消息对象。'related' 表示邮件正文和嵌入的图片资源是相关的。
    msg = MIMEMultipart("related")
    # 设置邮件的主题 Subject 和发件人地址 From。
    msg["Subject"] = Header(SUBJECT, "utf-8")
    msg["From"] = config("EMAIL_FROM")
    # 附加 HTML 正文: 创建一个 MIMEText 对象，用于包含 HTML 格式的邮件正文，并附加到邮件对象 msg 上。
    body = MIMEText(BODY_HTML, "html", "utf-8")
    msg.attach(body)
    # 附加图片: 将所有嵌入的 MIME 图像对象（即 mime_img 中的元素）附加到邮件对象 msg 上。 这样，图片就会作为邮件的一部分发送，而不依赖于外部资源。
    for m in mime_img:
        msg.attach(m)
    # 发送邮件: 使用 smtp.SMTPClient 创建一个 SMTP 客户端连接。
    with smtp.SMTPClient() as s:
        for r in recipient:
            msg["To"] = r
            try:
                logging.info(f"Email sending to: {r}")
                s.send_message(msg)
            except Exception as e:
                logging.error("!!! Email error!")
                logging.error(e)


def send_text(recipients, text, subject):
    with smtp.SMTPClient() as s:
        msg = MIMEMultipart()
        msg["Subject"] = Header(subject, "utf-8")
        msg["From"] = config("EMAIL_FROM")
        msg["To"] = ", ".join(recipients)
        body = MIMEText(text)
        msg.attach(body)
        try:
            s.send_message(msg)
        except Exception as e:
            logging.error("!! Text-email failed: " + subject),
            logging.error(e)


def __escape_text_html(text):
    return text.replace("@", "<span>@</span>").replace(".", "<span>.</span>").replace("=", "<span>=</span>")
