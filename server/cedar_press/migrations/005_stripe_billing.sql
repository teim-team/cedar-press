-- Stripe objects are mirrored for account history and local access checks.
CREATE TABLE cedar_press_subscriptions (
    id TEXT PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES cedar_press_subscribers(id),
    price_id TEXT NOT NULL,
    tier TEXT NOT NULL CHECK (tier IN ('press', 'press_pro')),
    cohort TEXT NOT NULL CHECK (cohort IN ('early_access', 'standard')),
    status TEXT NOT NULL,
    cancel_at_period_end BOOLEAN NOT NULL DEFAULT false,
    period_end TIMESTAMPTZ,
    activated_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX cedar_press_subscription_user ON cedar_press_subscriptions(user_id);

CREATE TABLE cedar_press_invoices (
    id TEXT PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES cedar_press_subscribers(id),
    subscription_id TEXT NOT NULL REFERENCES cedar_press_subscriptions(id),
    status TEXT NOT NULL,
    currency TEXT NOT NULL,
    amount_due BIGINT NOT NULL CHECK (amount_due >= 0),
    amount_paid BIGINT NOT NULL CHECK (amount_paid >= 0),
    tier TEXT CHECK (tier IN ('press', 'press_pro')),
    access_starts_at TIMESTAMPTZ,
    access_ends_at TIMESTAMPTZ,
    hosted_url TEXT,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX cedar_press_invoice_user ON cedar_press_invoices(user_id, created_at);

CREATE TABLE cedar_press_payments (
    id TEXT PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES cedar_press_subscribers(id),
    -- Invoice association may arrive after a payment event.
    invoice_id TEXT,
    charge_id TEXT,
    status TEXT NOT NULL,
    currency TEXT NOT NULL,
    amount BIGINT NOT NULL CHECK (amount >= 0),
    amount_received BIGINT NOT NULL CHECK (amount_received >= 0),
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX cedar_press_payment_invoice ON cedar_press_payments(invoice_id);
CREATE TABLE cedar_press_refunds (
    id TEXT PRIMARY KEY,
    payment_id TEXT NOT NULL REFERENCES cedar_press_payments(id),
    status TEXT NOT NULL,
    currency TEXT NOT NULL,
    amount BIGINT NOT NULL CHECK (amount > 0),
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE cedar_press_checkout_attempts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES cedar_press_subscribers(id),
    price_id TEXT NOT NULL,
    tier TEXT NOT NULL CHECK (tier IN ('press', 'press_pro')),
    cohort TEXT NOT NULL CHECK (cohort IN ('early_access', 'standard')),
    promotion_id TEXT,
    session_id TEXT UNIQUE,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','open','complete','expired')),
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX cedar_press_one_checkout ON cedar_press_checkout_attempts(user_id)
    WHERE status IN ('pending','open');

CREATE TABLE cedar_press_webhook_events (
    id TEXT PRIMARY KEY,
    event_type TEXT NOT NULL,
    object_id TEXT NOT NULL,
    customer_id TEXT,
    status TEXT NOT NULL DEFAULT 'received' CHECK (status IN ('received','processed','ignored','failed')),
    attempts INTEGER NOT NULL DEFAULT 0,
    error_code TEXT,
    received_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    processed_at TIMESTAMPTZ
);

-- Once an account has purchased through Stripe, legacy grants cannot revive
-- access after cancellation. Explicit complimentary grants remain independent.
CREATE VIEW cedar_press_current_access AS
SELECT account.id AS user_id, (
    SELECT candidate.tier FROM (
        SELECT grant_row.tier FROM cedar_press_access_grants grant_row
        WHERE grant_row.user_id = account.id AND grant_row.revoked_at IS NULL
          AND grant_row.starts_at <= now()
          AND (grant_row.ends_at IS NULL OR grant_row.ends_at > now())
          AND (grant_row.source = 'complimentary' OR NOT EXISTS (
              SELECT 1 FROM cedar_press_subscriptions previous
              WHERE previous.user_id = account.id AND previous.activated_at IS NOT NULL
          ))
        UNION ALL
        SELECT invoice.tier FROM cedar_press_invoices invoice
        JOIN cedar_press_subscriptions subscription ON subscription.id = invoice.subscription_id
        WHERE invoice.user_id = account.id AND invoice.status = 'paid'
          AND subscription.status IN ('active','past_due')
          AND invoice.access_starts_at <= now() AND invoice.access_ends_at > now()
          AND invoice.tier IS NOT NULL
          AND (invoice.amount_paid = 0 OR COALESCE((
              SELECT sum(refund.amount) FROM cedar_press_refunds refund
              JOIN cedar_press_payments payment ON payment.id = refund.payment_id
              WHERE payment.invoice_id = invoice.id AND refund.status = 'succeeded'
          ),0) < invoice.amount_paid)
    ) candidate ORDER BY CASE candidate.tier WHEN 'press_pro' THEN 2 ELSE 1 END DESC LIMIT 1
) AS tier FROM cedar_press_subscribers account;
