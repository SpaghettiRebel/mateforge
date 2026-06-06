from fastapi_mail import ConnectionConfig, FastMail, MessageSchema, MessageType

from auth_service.src.infrastructure.config import settings

conf = ConnectionConfig(
    MAIL_USERNAME=settings.MAIL_USERNAME,
    MAIL_PASSWORD=settings.MAIL_PASSWORD,
    MAIL_FROM=settings.MAIL_FROM,
    MAIL_PORT=settings.MAIL_PORT,
    MAIL_SERVER=settings.MAIL_SERVER,
    MAIL_STARTTLS=settings.MAIL_STARTTLS,
    MAIL_SSL_TLS=settings.MAIL_SSL_TLS,
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True
)

fastmail = FastMail(conf)


async def send_verification_email(email: str, token: str):
    verify_url = f"{settings.PUBLIC_APP_URL}/auth/verify?token={token}"

    message = MessageSchema(
        subject="Подтверждение регистрации",
        recipients=[email],
        body=f"Для подтверждения перейдите по ссылке: {verify_url}\nЕсли вы не регистрировались в сервисе MateForge – "
             f"проигнорируйте это письмо",
        subtype=MessageType.plain
    )

    await fastmail.send_message(message)
