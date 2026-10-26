"""Interfaces for account email delivery."""

from typing import Protocol


class EmailSender(Protocol):
    def configured(self) -> bool: ...
    def send_link(self, email: str, link: str, *, sign_in: bool = False) -> None: ...
