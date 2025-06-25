from usrak.core.smtp.base import SMTPClientABS, Mail


class NoOpSMTPClient(SMTPClientABS):
    def __init__(self, service_name: str = "NoOp SMTP"):
        super().__init__(service_name)

    async def start(self) -> None:
        pass

    async def stop(self) -> None:
        pass

    async def send_mail(self, mail: Mail) -> tuple[bool, str]:
        print(f"[NoOpSMTPClient] Simulating email to {mail.receiver}")
        return True, "Simulated email send (noop)"
