import logging

from src.celery_app import celery_app
from src.notifications.emails import EmailService

logger = logging.getLogger(__name__)


@celery_app.task(name="send_payment_confirmation_email")
def send_payment_confirmation_email_task(email: str, amount: str, order_id: int):
    logger.info(f"Starting email task for Order #{order_id}")
    try:
        email_service = EmailService()
        email_service.send_payment_success_email(email, amount, order_id)
        logger.info(f"Email sent successfully to {email}")
    except Exception as e:
        logger.error(f"Failed to send payment email: {e}")
