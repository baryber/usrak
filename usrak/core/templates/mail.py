from usrak.core.dependencies.config_provider import get_app_config
from usrak.core.schemas.mail import Mail


def signup_link_mail(
        receiver: str,
        link_token: str
) -> Mail:
    config = get_app_config()
    return Mail(
        subject="Ваш код подтверждения для SmartCardMaker.online",
        body=f"Здравствуйте!\n\n"
             f"Благодарим за регистрацию на платформе SmartCardMaker.online.  \n"
             f"Ваш код подтверждения:\n\n"
             f"{config.MAIN_DOMAIN}/verify-signup?data={link_token}\n\n"
             f"Пожалуйста, введите этот код на сайте, чтобы завершить процесс подтверждения и "
             f"начать пользоваться всеми возможностями нашей платформы.\n\n"
             f"> Если вы не запрашивали этот код, просто проигнорируйте это письмо.\n\n"
             f"С уважением,\n"
             f"Команда SmartCardMaker",
        receiver=receiver
    )


def reset_password_link_mail(
        receiver: str,
        link_token: str,
) -> Mail:

    print("/reset_password?data={encoded_str}")

    config = get_app_config()
    return Mail(
        subject="Ссылка для смены/восстановления пароля на SmartCardMaker.online",
        body=f"Здравствуйте!\n\n"
             f"Вы запросили смену/восстановление пароля на платформе SmartCardMaker.online.\n"
             f"{config.MAIN_DOMAIN}/reset-password?data={link_token}\n\n"
             f"Пожалуйста, перейдите по данной ссылке, чтобы продолжить процесс смены пароля.\n\n"
             f"> Если вы не запрашивали смену пароля, просто проигнорируйте это письмо.\n\n"
             f"С уважением,\n"
             f"Команда SmartCardMaker",

        receiver=receiver
    )


if __name__ == '__main__':
    print(reset_password_link_mail(
        "solbearer07@gmail.com",
        "token",
        1845842619
    ).body)
