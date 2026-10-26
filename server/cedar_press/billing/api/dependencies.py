"""Compose request-scoped billing services and their shared dependencies."""

from dataclasses import dataclass

from cedar_press import db
from cedar_press.accounts.services.email import AccountEmailSender, EmailSender
from cedar_press.accounts.services.setup import AccountSetupService
from cedar_press.billing.adapters.stripe import BillingAdapter, StripeAdapter
from cedar_press.billing.services.billing import BillingService
from cedar_press.billing.services.checkout import CheckoutService
from cedar_press.billing.services.purchase_email import PurchaseEmailService
from cedar_press.billing.services.reconciler import BillingReconciler


@dataclass(frozen=True)
class BillingServices:
    billing: BillingService
    checkout: CheckoutService
    reconciler: BillingReconciler
    email: EmailSender
    setup: AccountSetupService
    purchase_email: PurchaseEmailService


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
    purchase_email = PurchaseEmailService(sender, setup, database=database)
    checkout = CheckoutService(
        adapter=adapter,
        database=database,
        clock=clock,
        email_sender=sender,
        purchase_email_service=purchase_email,
    )
    return BillingServices(
        billing=BillingService(adapter=adapter, database=database, clock=clock),
        checkout=checkout,
        reconciler=BillingReconciler(checkout, purchase_email, adapter=adapter, database=database),
        email=sender,
        setup=setup,
        purchase_email=purchase_email,
    )


def get_billing_services() -> BillingServices:
    return create_billing_services()
