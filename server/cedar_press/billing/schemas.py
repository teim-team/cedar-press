"""Public HTTP response models for billing routes."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel

Tier = Literal["press", "press_pro"]
Cohort = Literal["early_access", "standard"]


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
