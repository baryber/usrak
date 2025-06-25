from usrak.core.managers.notification.base import NotificationServiceABS


class NoOpNotificationService(NotificationServiceABS):
    async def send_signup_verification(self, email: str, code: str) -> bool:
        return True

    async def send_password_reset_link(self, email: str, token: int) -> bool:
        return True
