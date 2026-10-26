-- Purchase reservations are separate from accounts. An account is created only
-- after Stripe confirms payment; mailbox ownership is required to set a password.
CREATE TABLE cedar_press_guest_checkouts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT NOT NULL CHECK (email = lower(btrim(email)) AND length(email) <= 254),
    secret_hash TEXT NOT NULL CHECK (secret_hash ~ '^[0-9a-f]{64}$'),
    price_id TEXT NOT NULL,
    tier TEXT NOT NULL CHECK (tier IN ('press','press_pro')),
    cohort TEXT NOT NULL CHECK (cohort IN ('early_access','standard')),
    promotion_id TEXT,
    customer_id TEXT UNIQUE,
    session_id TEXT UNIQUE,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','open','complete','expired')),
    user_id UUID REFERENCES cedar_press_subscribers(id),
    expires_at TIMESTAMPTZ NOT NULL,
    claim_sent_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX cedar_press_guest_email_pending ON cedar_press_guest_checkouts(email)
    WHERE status IN ('pending','open');
CREATE INDEX cedar_press_guest_secret ON cedar_press_guest_checkouts(secret_hash);
