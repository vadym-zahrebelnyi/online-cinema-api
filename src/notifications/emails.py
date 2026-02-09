import logging
import smtplib
from email.message import EmailMessage
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from src.core.settings import settings
from src.notifications.interfaces import EmailSenderInterface


class EmailService(EmailSenderInterface):
    """
    Concrete implementation of the email notification service.

    This service handles the composition and transmission of transactional emails
    using the standard library's `smtplib`. It utilizes Jinja2 for rendering
    HTML templates, ensuring consistent branding and dynamic content insertion.

    Attributes:
        hostname (str): SMTP server hostname.
        port (int): SMTP server port.
        sender_email (str): The 'From' address used in outgoing emails.
        env (Environment): Jinja2 template environment for loading HTML files.
    """

    def __init__(self):
        """
        Initialize the email service configuration.

        Loads SMTP settings from the global configuration and sets up the
        Jinja2 file loader pointing to the local 'templates' directory.
        """
        self.hostname = settings.SMTP_HOST
        self.port = settings.SMTP_PORT
        self.sender_email = settings.EMAILS_FROM_EMAIL

        template_dir = Path(__file__).parent / "templates"
        self.env = Environment(loader=FileSystemLoader(template_dir))

    def _send(self, to_email: str, subject: str, html_content: str):
        """
        Internal helper to construct and transmit an email via SMTP.

        Args:
            to_email (str): The recipient's email address.
            subject (str): The subject line of the email.
            html_content (str): The rendered HTML body of the email.

        Raises:
            Exception: Propagates any SMTP or network errors after logging them.
        """
        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = f"{settings.EMAILS_FROM_NAME} <{self.sender_email}>"
        message["To"] = to_email
        message.set_content(html_content, subtype="html")

        try:
            with smtplib.SMTP(self.hostname, self.port) as server:
                # server.starttls() # prod
                # server.login(...) # prod
                server.send_message(message)
                logging.info(f"Email sent to {to_email}")
        except Exception as e:
            logging.error(f"Failed to send email: {e}")
            raise e

    def send_activation_email(self, email: str, activation_link: str) -> None:
        """
        Send an account activation email to a new user.

        Renders the 'activation_request.html' template.

        Args:
            email (str): The recipient's email address.
            activation_link (str): The unique URL for account verification.
        """
        template = self.env.get_template("activation_request.html")
        html_content = template.render(email=email, activation_link=activation_link)
        self._send(email, "Account Activation", html_content)

    def send_password_reset_email(self, email: str, reset_link: str) -> None:
        """
        Send a password reset link to a user who forgot their credentials.

        Renders the 'password_reset_request.html' template.

        Args:
            email (str): The recipient's email address.
            reset_link (str): The unique URL for resetting the password.
        """
        template = self.env.get_template("password_reset_request.html")
        html_content = template.render(email=email, reset_link=reset_link)
        self._send(email, "Password Reset Request", html_content)

    def send_activation_complete_email(self, email: str, login_link: str) -> None:
        """
        Notify the user that their account has been successfully verified.

        Renders the 'activation_complete.html' template.

        Args:
            email (str): The recipient's email address.
            login_link (str): The URL to the login page.
        """
        template = self.env.get_template("activation_complete.html")
        html_content = template.render(email=email, login_link=login_link)
        self._send(email, "Account Activated Successfully", html_content)

    def send_password_reset_complete_email(self, email: str, login_link: str) -> None:
        """
        Notify the user that their password was successfully changed.

        This serves as a security alert to inform the user of account modifications.
        Renders the 'password_reset_complete.html' template.

        Args:
            email (str): The recipient's email address.
            login_link (str): The URL to the login page.
        """
        template = self.env.get_template("password_reset_complete.html")
        html_content = template.render(email=email, login_link=login_link)
        self._send(email, "Security Alert: Password Changed", html_content)

    def send_payment_success_email(
        self, email: str, amount: str, order_id: int
    ) -> None:
        """
        Send a transaction receipt to the user after a successful payment.

        Renders the 'payment_success.html' template with order details.

        Args:
            email (str): The recipient's email address.
            amount (str): The formatted amount paid (e.g. "10.00").
            order_id (int): The unique identifier of the order.
        """
        template = self.env.get_template("payment_success.html")
        html_content = template.render(
            email=email,
            amount=amount,
            order_id=order_id,
            login_link=f"{settings.DOMAIN_NAME}/history",
        )
        self._send(email, f"Payment Successful - Order #{order_id}", html_content)
