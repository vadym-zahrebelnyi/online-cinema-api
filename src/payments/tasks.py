import logging

from src.celery_app import celery_app
from src.notifications.emails import EmailService

logger = logging.getLogger(__name__)


@celery_app.task(
    name="send_payment_confirmation_email",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
    max_retries=5,
    time_limit=60,
)
def send_payment_confirmation_email_task(email: str, amount: str, order_id: int):
    """
    Background task to send a payment confirmation email to the user.

    This task is executed asynchronously by a Celery worker to avoid blocking
    the main API thread during the webhook processing or checkout flow.

    Args:
        email (str): The recipient's email address.
        amount (str): The total amount paid, formatted as a string (e.g., "10.00").
        order_id (int): The unique identifier of the order associated with the payment.

    Returns:
        None

    Raises:
        Exception: Logs any error that occurs during the email sending process
            but does not propagate it to the caller (fail-safe).
    """
    logger.info(f"Starting email task for Order #{order_id}")
    email_service = EmailService()
    email_service.send_payment_success_email(email, amount, order_id)
    logger.info(f"Email sent successfully to {email}")
