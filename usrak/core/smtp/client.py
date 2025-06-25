from aiosmtplib import SMTP
from email.message import EmailMessage
from email.utils import formataddr
from usrak.core.logger import logger

from usrak.core.schemas.mail import Mail
from usrak.core.smtp.base import SMTPClientABS


class SMTPClient(SMTPClientABS):
    def __init__(self, service_name: str = "Default SMTP Service"):
        super().__init__(service_name)
        self.server = SMTP(
            hostname=self.app_config.SMTP_HOST,
            port=self.app_config.SMTP_PORT,
            use_tls=True,
            validate_certs=self.app_config.ENV == "prod",
            username=self.app_config.SMTP_USERNAME,
            password=self.app_config.SMTP_PASSWORD,
        )
        logger.info(f"SMTP client initialized with {self.app_config.SMTP_HOST}:{self.app_config.SMTP_PORT}, "
                    f"user: {self.app_config.SMTP_USERNAME}")

    async def start(self) -> None:
        await self.server.connect()
        self.connected = True
        logger.info(f"Connected to the SMTP server as {self.service_name}")

    async def stop(self) -> None:
        await self.server.quit()
        self.connected = False
        logger.info("Disconnected from the server")

    async def send_mail(self, mail: Mail) -> tuple[bool, str]:
        if not self.connected:
            raise RuntimeError("Not connected to the server, call start() first")

        message = EmailMessage()
        message["From"] = formataddr(("Smart Card Maker", self.service_name))
        message["To"] = mail.receiver
        message["Subject"] = mail.subject
        message.set_content(mail.body)

        try:
            status = await self.server.send_message(message)
            if isinstance(status, tuple) and len(status) == 2:
                error_dict, response_str = status
                if error_dict == {}:
                    return True, f"Email sent successfully: {response_str}"
                return False, f"Failed to send email: {error_dict}"
            elif isinstance(status, dict):
                return (True, "Email sent successfully") if not status else (False, f"Failed: {status}")
            else:
                return False, f"Unexpected response format: {status}"
        except Exception as e:
            return False, f"Error during email sending: {str(e)}"
