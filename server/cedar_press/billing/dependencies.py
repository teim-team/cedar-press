"""Compose request-scoped billing services and their shared dependencies."""

from dataclasses import dataclass

from cedar_press import db
from cedar_press.account_email import AccountEmailSender
from cedar_press.billing.account_setup import AccountSetupService
from cedar_press.billing.checkout import CheckoutService
from cedar_press.billing.interfaces import BillingGateway, EmailSender
from cedar_press.billing.reconciler import BillingReconciler
from cedar_press.billing.service import BillingService
from cedar_press.billing.stripe_gateway import StripeGateway


@dataclass(frozen=True)
class BillingServices:
    billing: BillingService
    checkout: CheckoutService
    reconciler: BillingReconciler
    email: EmailSender
    setup: AccountSetupService


def create_billing_services(
    *,
    gateway: BillingGateway | None = None,
    email_sender: EmailSender | None = None,
    clock=None,
    database=db,
) -> BillingServices:
    gateway = gateway if gateway is not None else StripeGateway()
    sender = email_sender or AccountEmailSender()
    setup = AccountSetupService(sender, database=database)
    checkout = CheckoutService(
        gateway=gateway, database=database, clock=clock, email_sender=sender, setup_service=setup
    )
    return BillingServices(
        billing=BillingService(gateway=gateway, database=database, clock=clock),
        checkout=checkout,
        reconciler=BillingReconciler(checkout, setup, gateway=gateway, database=database),
        email=sender,
        setup=setup,
    )


def get_billing_services() -> BillingServices:
    return create_billing_services()
