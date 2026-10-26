"""Provider interfaces and the public billing response contract."""

from datetime import datetime
from typing import Literal, Protocol

from pydantic import BaseModel

Tier = Literal["press", "press_pro"]
Cohort = Literal["early_access", "standard"]


class EmailSender(Protocol):
    def configured(self) -> bool: ...
    def send_link(self, email: str, link: str, *, sign_in: bool = False) -> None: ...


class BillingGateway(Protocol):
    livemode: bool

    def price(self, price_id: str) -> dict: ...
    def customer(self, user: dict) -> str: ...
    def subscriptions(self, customer: str) -> list[dict]: ...
    def subscription(self, subscription_id: str) -> dict: ...
    def invoices(self, subscription_id: str) -> list[dict]: ...
    def invoice(self, invoice_id: str) -> dict: ...
    def lines(self, invoice_id: str) -> list[dict]: ...
    def invoice_payments(self, invoice_id: str) -> list[dict]: ...
    def payment(self, payment_id: str) -> dict: ...
    def charge(self, charge_id: str) -> dict: ...
    def refunds(self, charge_id: str) -> list[dict]: ...
    def refund(self, refund_id: str) -> dict: ...
    def promotion(self, code: str) -> str: ...
    def checkout(
        self, customer: str | None, attempt: dict, app_url: str, guest: bool = False
    ) -> dict: ...
    def checkout_status(self, session_id: str) -> dict: ...
    def expire_checkout(self, session_id: str) -> dict: ...
    def find_checkout(
        self,
        customer: str | None,
        attempt_id: str,
        *,
        created_after: int | None = None,
        created_before: int | None = None,
    ) -> dict | None: ...
    def guest_session(self, customer: str) -> dict | None: ...
    def portal(
        self,
        customer: str,
        cohort: str,
        app_url: str,
        change_plan: bool = False,
        subscription_id: str | None = None,
    ) -> str: ...


class RedirectResponse(BaseModel):
    url: str


class PlanResponse(BaseModel):
    cohort: Cohort
    annualPrices: dict[Tier, int]


class GuestStatusResponse(BaseModel):
    status: Literal["pending", "open", "complete", "expired"]
    email: str | None
    emailSent: bool
    accountSetup: bool


class SubscriptionResponse(BaseModel):
    id: str
    tier: Tier
    cohort: Cohort
    status: str
    cancel_at_period_end: bool
    period_end: datetime | None
    activated_at: datetime | None


class InvoiceResponse(BaseModel):
    id: str
    status: str
    currency: str
    amount_due: int
    amount_paid: int
    hosted_url: str | None
    created_at: datetime


class PaymentResponse(BaseModel):
    id: str
    status: str
    currency: str
    amount: int
    amount_received: int
    created_at: datetime


class RefundResponse(BaseModel):
    id: str
    status: str
    currency: str
    amount: int
    created_at: datetime


class BillingResponse(PlanResponse):
    available: bool
    subscriptions: list[SubscriptionResponse]
    invoices: list[InvoiceResponse]
    payments: list[PaymentResponse]
    refunds: list[RefundResponse]
    hasCustomer: bool
