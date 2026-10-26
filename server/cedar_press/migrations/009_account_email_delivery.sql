-- Setup links are independent grants: a failed email must not invalidate a
-- previously delivered link. Only hashes are stored; all expire after one hour.
CREATE TABLE cedar_press_account_setup_links (
    token_hash TEXT PRIMARY KEY CHECK (token_hash ~ '^[0-9a-f]{64}$'),
    user_id UUID NOT NULL REFERENCES cedar_press_subscribers(id),
    email TEXT NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    used_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX cedar_press_setup_link_user ON cedar_press_account_setup_links(user_id);

-- A lease prevents concurrent deliveries without holding a transaction during SMTP.
CREATE TABLE cedar_press_account_email_deliveries (
    checkout_id UUID PRIMARY KEY REFERENCES cedar_press_checkouts(id),
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','sending','sent')),
    lease_id UUID,
    lease_until TIMESTAMPTZ,
    attempts INTEGER NOT NULL DEFAULT 0,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
