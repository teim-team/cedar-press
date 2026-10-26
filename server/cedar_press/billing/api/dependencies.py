"""Compose request-scoped billing services and their shared dependencies."""

from dataclasses import dataclass

from cedar_press import db
from cedar_press.accounts.services.email import AccountEmailSender, EmailSender
from cedar_press.accounts.services.setup import AccountSetupService
from cedar_press.billing.adapters.stripe import BillingAdapter, StripeAdapter
from cedar_press.billing.services.billing import BillingService
from cedar_press.billing.services.checkout import CheckoutService
from cedar_press.billing.services.delivery import CheckoutEmailService
from cedar_press.billing.services.reconciler import BillingReconciler


@dataclass(frozen=True)
class BillingServices:
    billing: BillingService
    checkout: CheckoutService
    reconciler: BillingReconciler
    email: EmailSender
    setup: AccountSetupService
    delivery: CheckoutEmailService


def create_billing_services(
    *,
    adapter: BillingAdapter | None = None,
    email_sender: EmailSender | None = None,
    clock=None,
    database=db,
) -> BillingServices:
    adapter = adapter if adapter is not None else StripeAdapter()
    sender = email_sender or AccountEmailSender()
    setup = AccountSetupService(database=database)
    delivery = CheckoutEmailService(sender, setup, database=database)
    checkout = CheckoutService(
        adapter=adapter,
        database=database,
        clock=clock,
        email_sender=sender,
        delivery_service=delivery,
    )
    return BillingServices(
        billing=BillingService(adapter=adapter, database=database, clock=clock),
        checkout=checkout,
        reconciler=BillingReconciler(checkout, delivery, adapter=adapter, database=database),
        email=sender,
        setup=setup,
        delivery=delivery,
    )


def get_billing_services() -> BillingServices:
    return create_billing_services()
