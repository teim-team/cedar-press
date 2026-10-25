-- Additive bridge: existing subscriber credentials and access remain authoritative
-- until the account lifecycle and billing adapters replace their writers.
-- Refuse ambiguous historical addresses rather than merging distinct seats.
CREATE UNIQUE INDEX cedar_press_subscriber_normalized_email
    ON cedar_press_subscribers(lower(btrim(email)));
CREATE TABLE cedar_press_users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT NOT NULL UNIQUE CHECK (email = lower(btrim(email)) AND email <> ''),
    email_verified_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- External identities use the provider's stable subject, never its email.
-- Password credentials remain in subscribers during this migration phase.
CREATE TABLE cedar_press_login_identities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES cedar_press_users(id),
    provider TEXT NOT NULL CHECK (provider IN ('google')),
    subject TEXT NOT NULL CHECK (subject <> ''),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (provider, subject),
    UNIQUE (user_id, provider)
);

CREATE TABLE cedar_press_billing_accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    -- Preserve the exact Cedar Points grouping, including multi-seat accounts.
    legacy_account_id TEXT UNIQUE,
    stripe_customer_id TEXT UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE cedar_press_account_members (
    account_id UUID NOT NULL REFERENCES cedar_press_billing_accounts(id),
    user_id UUID NOT NULL REFERENCES cedar_press_users(id),
    -- Historical seats do not establish who may manage an organization's bill.
    role TEXT NOT NULL CHECK (role IN ('member', 'owner')) DEFAULT 'member',
    PRIMARY KEY (account_id, user_id)
);

CREATE TABLE cedar_press_entitlements (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id UUID NOT NULL REFERENCES cedar_press_billing_accounts(id),
    user_id UUID NOT NULL REFERENCES cedar_press_users(id),
    tier TEXT NOT NULL CHECK (tier IN ('press', 'press_pro')),
    source TEXT NOT NULL CHECK (source IN ('legacy', 'stripe', 'manual')),
    starts_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    ends_at TIMESTAMPTZ,
    revoked_at TIMESTAMPTZ,
    CHECK (ends_at IS NULL OR ends_at > starts_at)
);
CREATE UNIQUE INDEX cedar_press_legacy_entitlement
    ON cedar_press_entitlements(user_id) WHERE source = 'legacy';
CREATE INDEX cedar_press_entitlement_user ON cedar_press_entitlements(user_id);

ALTER TABLE cedar_press_subscribers ADD COLUMN identity_id UUID
    REFERENCES cedar_press_users(id);
-- Preserve the old cookie revision exactly at migration time.
ALTER TABLE cedar_press_subscribers ADD COLUMN sessions_revoked_at TIMESTAMPTZ;
UPDATE cedar_press_subscribers SET sessions_revoked_at = updated_at;
ALTER TABLE cedar_press_subscribers ALTER COLUMN sessions_revoked_at SET DEFAULT now();
ALTER TABLE cedar_press_subscribers ALTER COLUMN sessions_revoked_at SET NOT NULL;

-- Synchronize trusted legacy provisioning in its original transaction. This
-- bridge does not verify email ownership or infer billing ownership.
CREATE FUNCTION cedar_press_sync_legacy_subscriber() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE
    identity UUID;
    billing UUID;
BEGIN
    IF TG_OP = 'UPDATE' AND NEW.identity_id IS DISTINCT FROM OLD.identity_id THEN
        RAISE EXCEPTION 'legacy_identity_rebinding_forbidden';
    END IF;
    IF NEW.identity_id IS NULL THEN
        INSERT INTO cedar_press_users (email, created_at)
        VALUES (lower(btrim(NEW.email)), NEW.created_at)
        ON CONFLICT (email) DO UPDATE SET email = EXCLUDED.email
        RETURNING id INTO identity;
        NEW.identity_id := identity;
    ELSE
        -- Preserve identity IDs across email changes; uniqueness refuses a merge.
        UPDATE cedar_press_users
        SET email_verified_at = CASE WHEN email = lower(btrim(NEW.email))
                                    THEN email_verified_at ELSE NULL END,
            email = lower(btrim(NEW.email))
        WHERE id = NEW.identity_id;
    END IF;
    INSERT INTO cedar_press_billing_accounts (legacy_account_id)
    VALUES (NEW.account_id)
    ON CONFLICT (legacy_account_id) DO UPDATE
    SET legacy_account_id = EXCLUDED.legacy_account_id
    RETURNING id INTO billing;
    INSERT INTO cedar_press_account_members (account_id, user_id)
    VALUES (billing, NEW.identity_id) ON CONFLICT DO NOTHING;
    IF TG_OP = 'UPDATE' AND NEW.account_id IS DISTINCT FROM OLD.account_id THEN
        DELETE FROM cedar_press_account_members
        WHERE user_id = NEW.identity_id AND account_id IN (
            SELECT id FROM cedar_press_billing_accounts WHERE legacy_account_id = OLD.account_id
        );
    END IF;
    INSERT INTO cedar_press_entitlements (account_id, user_id, tier, source, starts_at)
    VALUES (billing, NEW.identity_id, NEW.tier, 'legacy', NEW.created_at)
    ON CONFLICT (user_id) WHERE source = 'legacy'
    DO UPDATE SET account_id = EXCLUDED.account_id, tier = EXCLUDED.tier, revoked_at = NULL;
    RETURN NEW;
END;
$$;
CREATE TRIGGER cedar_press_legacy_subscriber_bridge
BEFORE INSERT OR UPDATE OF email, account_id, tier, identity_id
ON cedar_press_subscribers FOR EACH ROW
EXECUTE FUNCTION cedar_press_sync_legacy_subscriber();

-- Fires the same bridge used by later activations, without modifying hashes,
-- account grouping, timestamps, email verification or existing cookie revisions.
UPDATE cedar_press_subscribers SET email = email;
ALTER TABLE cedar_press_subscribers ALTER COLUMN identity_id SET NOT NULL;

CREATE FUNCTION cedar_press_remove_legacy_access() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    UPDATE cedar_press_entitlements SET revoked_at = clock_timestamp()
    WHERE user_id = OLD.identity_id AND source = 'legacy';
    DELETE FROM cedar_press_account_members
    WHERE user_id = OLD.identity_id AND account_id IN (
        SELECT id FROM cedar_press_billing_accounts WHERE legacy_account_id = OLD.account_id
    );
    RETURN OLD;
END;
$$;
CREATE TRIGGER cedar_press_legacy_subscriber_removal
AFTER DELETE ON cedar_press_subscribers FOR EACH ROW
EXECUTE FUNCTION cedar_press_remove_legacy_access();
