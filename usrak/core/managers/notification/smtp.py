import json
import time
import base64
import urllib.parse

from usrak.core.logger import logger

from usrak.core import dependencies as deps
from usrak.core.templates import mail
from usrak.core.managers.notification.base import NotificationServiceABS


class SmtpNotificationService(NotificationServiceABS):
    def __init__(self):
        self.cli = deps.get_smtp_client()

    async def send_signup_verification(self, email: str, token: str) -> bool:
        data = {
            "email": email,
            "token": token,
            "exp": int(time.time())
        }
        json_str = json.dumps(data)
        base64_bytes = base64.urlsafe_b64encode(json_str.encode("utf-8"))
        base64_str = base64_bytes.decode("utf-8")

        encoded_str = urllib.parse.quote(base64_str)

        mail_to_send = mail.signup_link_mail(receiver=email, link_token=encoded_str)
        success, msg = self.cli.send_mail(mail=mail_to_send)
        if not success:
            logger.info(f"Failed to send email: {msg}")
            return False

        logger.info(f"Email sent successfully: {msg}")
        return True

    async def send_password_reset_link(self, email: str, token: int) -> bool:
        data = {
            "email": email,
            "token": token,
            "exp": int(time.time())
        }
        json_str = json.dumps(data)
        base64_bytes = base64.urlsafe_b64encode(json_str.encode("utf-8"))
        base64_str = base64_bytes.decode("utf-8")

        encoded_str = urllib.parse.quote(base64_str)

        mail_to_send = mail.reset_password_link_mail(receiver=email, link_token=encoded_str)
        success, msg = self.cli.send_mail(mail=mail_to_send)
        if not success:
            logger.info(f"Failed to send email: {msg}")
            return False

        logger.info(f"Email sent successfully: {msg}")
        return True
