"""Deliver account links through SMTP. Local Docker uses Mailpit."""

from __future__ import annotations

import os
import smtplib
import ssl
from email.message import EmailMessage
from typing import Protocol


class EmailSender(Protocol):
    def configured(self) -> bool: ...
    def send_link(self, email: str, link: str, *, sign_in: bool = False) -> None: ...
    def send_message(self, email: str, subject: str, body: str) -> None: ...


class AccountEmailSender:
    """SMTP delivery with injectable settings and transport."""

    def __init__(self, *, settings=None, smtp_factory=None):
        self.settings = os.environ if settings is None else settings
        self.smtp_factory = smtp_factory or smtplib.SMTP

    def configured(self):
        development = self.settings.get("CEDAR_PRESS_ENVIRONMENT", "development") == "development"
        return bool(
            self.settings.get("CEDAR_PRESS_SMTP_HOST")
            and self.settings.get("CEDAR_PRESS_EMAIL_FROM")
        ) and (development or self.settings.get("CEDAR_PRESS_SMTP_STARTTLS", "1") == "1")

    def send_link(self, email, link, *, sign_in=False):
        if sign_in:
            self.send_message(
                email,
                "Your Cedar Press membership",
                "Your Cedar Press membership is ready. Sign in with your existing account:\n\n"
                + link,
            )
        else:
            self.send_message(
                email,
                "Set your Cedar Press password",
                "Use this link to set your Cedar Press password and confirm your email address:\n\n"
                + link
                + "\n\nThis link expires in one hour and can be used once. "
                "If you did not request it, you can ignore this email.",
            )

    def send_message(self, email, subject, body):
        if not self.configured():
            raise RuntimeError("Account email is not configured")
        message = EmailMessage()
        message["From"] = self.settings["CEDAR_PRESS_EMAIL_FROM"]
        message["To"] = email
        message["Subject"] = subject
        message.set_content(body)
        with self.smtp_factory(
            self.settings["CEDAR_PRESS_SMTP_HOST"],
            int(self.settings.get("CEDAR_PRESS_SMTP_PORT", "587")),
            timeout=10,
        ) as smtp:
            if self.settings.get("CEDAR_PRESS_SMTP_STARTTLS", "1") == "1":
                smtp.starttls(context=ssl.create_default_context())
            if self.settings.get("CEDAR_PRESS_SMTP_USERNAME"):
                smtp.login(
                    self.settings["CEDAR_PRESS_SMTP_USERNAME"],
                    self.settings.get("CEDAR_PRESS_SMTP_PASSWORD", ""),
                )
            smtp.send_message(message)
