import asyncio
from datetime import datetime, timezone

from sqlalchemy import NullPool, delete
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.accounts.models import ActivationTokenDB
from src.celery_app import celery_app
from src.core import settings
from src.notifications.emails import EmailService
from src.notifications.interfaces import EmailSenderInterface

email_sender: EmailSenderInterface = EmailService()


@celery_app.task
def send_activation_email_task(email_to: str, token: str):
    from src.core.settings import settings

    link = f"{settings.DOMAIN_NAME}/api/v1/accounts/activate/?token={token}"

    email_sender.send_activation_email(email_to, link)


@celery_app.task
def send_password_reset_email_task(email_to: str, token: str):
    from src.core.settings import settings

    link = (
        f"{settings.DOMAIN_NAME}/api/v1/accounts/reset-password/complete?token={token}"
    )

    email_sender.send_password_reset_email(email_to, link)


@celery_app.task
def send_activation_complete_email_task(email_to: str):
    from src.core.settings import settings

    login_link = f"{settings.DOMAIN_NAME}/login"

    email_sender.send_activation_complete_email(email_to, login_link)
    return "Activation complete email sent"


@celery_app.task
def send_password_reset_complete_email_task(email_to: str):
    from src.core.settings import settings

    login_link = f"{settings.DOMAIN_NAME}/login"

    email_sender.send_password_reset_complete_email(email_to, login_link)
    return "Password reset complete email sent"


@celery_app.task
def cleanup_expired_tokens_task():
    async def _cleanup():
        task_engine = create_async_engine(
            settings.DATABASE_URL, poolclass=NullPool, echo=True
        )

        TaskSessionLocal = async_sessionmaker(
            bind=task_engine, class_=AsyncSession, expire_on_commit=False
        )

        try:
            async with TaskSessionLocal() as session:
                stmt = delete(ActivationTokenDB).where(
                    ActivationTokenDB.expires_at < datetime.now(timezone.utc)
                )
                result = await session.execute(stmt)
                await session.commit()
                return result.rowcount
        finally:
            await task_engine.dispose()

    try:
        deleted_count = asyncio.run(_cleanup())
    except RuntimeError:
        loop = asyncio.get_event_loop()
        deleted_count = loop.run_until_complete(_cleanup())

    return f"Deleted {deleted_count} expired activation tokens"
