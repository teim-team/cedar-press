"""Billing failures exposed consistently by services and HTTP routes."""


class BillingError(Exception):
    def __init__(self, code: str, message: str, status: int = 400):
        super().__init__(message)
        self.code, self.message, self.status = code, message, status


def unavailable() -> BillingError:
    return BillingError("BILLING_UNAVAILABLE", "Billing is temporarily unavailable.", 503)
