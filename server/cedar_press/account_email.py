"""Mailbox ownership links through SMTP. Local Docker uses a Mailpit inbox."""

from __future__ import annotations

import os
import smtplib
import ssl
from email.message import EmailMessage


def configured():
    development = os.environ.get("CEDAR_PRESS_ENVIRONMENT", "development") == "development"
    return bool(
        os.environ.get("CEDAR_PRESS_SMTP_HOST") and os.environ.get("CEDAR_PRESS_EMAIL_FROM")
    ) and (development or os.environ.get("CEDAR_PRESS_SMTP_STARTTLS", "1") == "1")


def send_link(email, link, *, sign_in=False):
    if not configured():
        raise RuntimeError("Account email is not configured")
    message = EmailMessage()
    message["From"] = os.environ["CEDAR_PRESS_EMAIL_FROM"]
    message["To"] = email
    message["Subject"] = (
        "Your Cedar Press membership" if sign_in else "Set your Cedar Press password"
    )
    if sign_in:
        message.set_content(
            "Your Cedar Press membership is ready. Sign in with your existing account:\n\n" + link
        )
    else:
        message.set_content(
            "Use this link to set your Cedar Press password and confirm your email address:\n\n"
            + link
            + "\n\nThis link expires in one hour and can be used once. "
            "If you did not request it, you can ignore this email."
        )
    with smtplib.SMTP(
        os.environ["CEDAR_PRESS_SMTP_HOST"],
        int(os.environ.get("CEDAR_PRESS_SMTP_PORT", "587")),
        timeout=10,
    ) as smtp:
        if os.environ.get("CEDAR_PRESS_SMTP_STARTTLS", "1") == "1":
            smtp.starttls(context=ssl.create_default_context())
        if os.environ.get("CEDAR_PRESS_SMTP_USERNAME"):
            smtp.login(
                os.environ["CEDAR_PRESS_SMTP_USERNAME"],
                os.environ.get("CEDAR_PRESS_SMTP_PASSWORD", ""),
            )
        smtp.send_message(message)
