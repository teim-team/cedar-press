"""Compose request-scoped billing services and their shared dependencies."""

from dataclasses import dataclass

from cedar_press import db
from cedar_press.account_email import AccountEmailSender
from cedar_press.billing import BillingService
from cedar_press.billing_reconciler import BillingReconciler
from cedar_press.guest_checkout import GuestCheckoutService


@dataclass(frozen=True)
class BillingServices:
    billing: BillingService
    guest: GuestCheckoutService
    reconciler: BillingReconciler
    email: AccountEmailSender


def create_billing_services(*, gateway=None, email_sender=None, clock=None, database=db):
    sender = email_sender or AccountEmailSender()
    guest = GuestCheckoutService(
        gateway=gateway, database=database, clock=clock, email_sender=sender
    )
    return BillingServices(
        billing=BillingService(gateway=gateway, database=database, clock=clock),
        guest=guest,
        reconciler=BillingReconciler(guest, gateway=gateway, database=database),
        email=sender,
    )


def get_billing_services() -> BillingServices:
    return create_billing_services()
