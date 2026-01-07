"""Simple SMTP email client."""

from dataclasses import dataclass
from email.message import EmailMessage
import smtplib
from typing import Iterable


@dataclass
class EmailConfig:
    """Configuration for connecting to an SMTP server."""

    smtp_server: str
    smtp_port: int
    username: str
    password: str
    use_tls: bool = True


class EmailClient:
    """Client for sending plain text emails via SMTP."""

    def __init__(self, config: EmailConfig) -> None:
        """Initialize the client.

        Args:
            config: SMTP connection settings.
        """
        self.config = config

    def send_email(
        self, subject: str, body: str, from_email: str, to_emails: Iterable[str]
    ) -> None:
        """Send an email message.

        Args:
            subject: Email subject line.
            body: Plain text email body.
            from_email: Sender email address.
            to_emails: Recipient email addresses.
        """
        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = from_email
        message["To"] = ", ".join(to_emails)
        message.set_content(body)

        with smtplib.SMTP(self.config.smtp_server, self.config.smtp_port) as smtp:
            if self.config.use_tls:
                smtp.starttls()
            smtp.login(self.config.username, self.config.password)
            smtp.send_message(message)
