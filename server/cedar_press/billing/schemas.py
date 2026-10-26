"""HTTP request and response models for billing routes."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

Tier = Literal["press", "press_pro"]
Cohort = Literal["early_access", "standard"]


class CheckoutRequest(BaseModel):
    tier: Tier
    discount_code: str = Field(default="", max_length=64)
    replace_open: bool = False


class CheckoutTarget(BaseModel):
    checkout_id: UUID | None = None


class SubscriptionRequest(BaseModel):
    subscription_id: str | None = Field(default=None, min_length=1, max_length=255)


class CheckoutStartRequest(BaseModel):
    tier: Tier


class RedirectResponse(BaseModel):
    url: str


class PlanResponse(BaseModel):
    cohort: Cohort
    annualPrices: dict[Tier, int]


class CheckoutStatusResponse(BaseModel):
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
