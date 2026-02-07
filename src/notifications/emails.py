import logging
import smtplib
from email.message import EmailMessage
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from src.core.settings import settings
from src.notifications.interfaces import EmailSenderInterface


class EmailService(EmailSenderInterface):
    def __init__(self):
        self.hostname = settings.SMTP_HOST
        self.port = settings.SMTP_PORT
        self.sender_email = settings.EMAILS_FROM_EMAIL

        template_dir = Path(__file__).parent / "templates"
        self.env = Environment(loader=FileSystemLoader(template_dir))

    def _send(self, to_email: str, subject: str, html_content: str):
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
        template = self.env.get_template("activation_request.html")
        html_content = template.render(email=email, activation_link=activation_link)
        self._send(email, "Account Activation", html_content)

    def send_password_reset_email(self, email: str, reset_link: str) -> None:
        template = self.env.get_template("password_reset_request.html")
        html_content = template.render(email=email, reset_link=reset_link)
        self._send(email, "Password Reset Request", html_content)

    def send_activation_complete_email(self, email: str, login_link: str) -> None:
        template = self.env.get_template("activation_complete.html")
        html_content = template.render(email=email, login_link=login_link)
        self._send(email, "Account Activated Successfully", html_content)

    def send_password_reset_complete_email(self, email: str, login_link: str) -> None:
        template = self.env.get_template("password_reset_complete.html")
        html_content = template.render(email=email, login_link=login_link)
        self._send(email, "Security Alert: Password Changed", html_content)
