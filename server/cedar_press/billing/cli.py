"""Repair local Stripe state: python -m cedar_press.billing.cli reconcile."""

from __future__ import annotations

import argparse

from cedar_press import db
from cedar_press.billing.dependencies import create_billing_services
from cedar_press.billing.stripe_gateway import StripeGateway


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("reconcile",))
    parser.parse_args(argv)
    if not db.configured():
        parser.error("Reconciliation requires DATABASE_URL")
    gateway = StripeGateway()
    reconciler = create_billing_services(gateway=gateway).reconciler
    for reservation in db.query(
        "SELECT session_id FROM cedar_press_guest_checkouts "
        "WHERE status IN ('pending','open') AND session_id IS NOT NULL"
    ):
        session = gateway.checkout_status(reservation["session_id"])
        customer = session.get("customer")
        if isinstance(customer, str) and session.get("payment_status") == "paid":
            reconciler.reconcile_customer(customer)
    for row in db.query(
        """
        SELECT stripe_customer_id FROM cedar_press_subscribers WHERE
        stripe_customer_id IS NOT NULL UNION SELECT customer_id AS stripe_customer_id
        FROM cedar_press_guest_checkouts WHERE customer_id IS NOT NULL
        """
    ):
        reconciler.reconcile_customer(row["stripe_customer_id"])
    print("Billing reconciliation completed.")


if __name__ == "__main__":
    main()
