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

-- Provenance is stored once; effective membership is a view over remaining grants.
CREATE TABLE cedar_press_membership_grants (
    account_id UUID NOT NULL REFERENCES cedar_press_billing_accounts(id),
    user_id UUID NOT NULL REFERENCES cedar_press_users(id),
    role TEXT NOT NULL CHECK (role IN ('member', 'owner')) DEFAULT 'member',
    source TEXT NOT NULL CONSTRAINT cedar_press_membership_source
        CHECK (source IN ('preexisting', 'legacy', 'manual', 'stripe')),
    PRIMARY KEY (account_id, user_id, source),
    CONSTRAINT cedar_press_legacy_membership_cannot_own
        CHECK (source <> 'legacy' OR role = 'member')
);
CREATE VIEW cedar_press_account_members AS
SELECT account_id, user_id,
       CASE WHEN bool_or(role = 'owner') THEN 'owner' ELSE 'member' END AS role
FROM cedar_press_membership_grants GROUP BY account_id, user_id;

-- Paid access will be derived from subscriptions, never mirrored into grants.
CREATE TABLE cedar_press_access_grants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id UUID NOT NULL REFERENCES cedar_press_billing_accounts(id),
    user_id UUID NOT NULL REFERENCES cedar_press_users(id),
    tier TEXT NOT NULL CHECK (tier IN ('press', 'press_pro')),
    source TEXT NOT NULL CONSTRAINT cedar_press_access_grant_source
        CHECK (source IN ('legacy', 'complimentary')),
    starts_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    ends_at TIMESTAMPTZ,
    revoked_at TIMESTAMPTZ,
    CHECK (ends_at IS NULL OR ends_at > starts_at)
);
CREATE INDEX cedar_press_access_grant_user ON cedar_press_access_grants(user_id);
CREATE UNIQUE INDEX cedar_press_active_legacy_grant ON cedar_press_access_grants(user_id)
    WHERE source = 'legacy' AND revoked_at IS NULL;

ALTER TABLE cedar_press_subscribers
    ADD COLUMN identity_id UUID REFERENCES cedar_press_users(id),
    ADD COLUMN sessions_revoked_at TIMESTAMPTZ,
    ADD CONSTRAINT cedar_press_subscriber_account_required CHECK (btrim(account_id) <> '');

-- Bootstrap existing subscribers explicitly, before installing runtime writers.
-- No email match is used to link an independently established identity: the users
-- table is new, and the normalized-email index above refuses ambiguous seats.
INSERT INTO cedar_press_users(email, created_at)
SELECT lower(btrim(email)), created_at FROM cedar_press_subscribers;
INSERT INTO cedar_press_billing_accounts(legacy_account_id)
SELECT DISTINCT account_id FROM cedar_press_subscribers;
UPDATE cedar_press_subscribers s
SET identity_id = u.id, sessions_revoked_at = s.updated_at
FROM cedar_press_users u WHERE u.email = lower(btrim(s.email));
INSERT INTO cedar_press_membership_grants(account_id, user_id, role, source)
SELECT b.id, s.identity_id, 'member', 'legacy'
FROM cedar_press_subscribers s
JOIN cedar_press_billing_accounts b ON b.legacy_account_id = s.account_id;
INSERT INTO cedar_press_access_grants(account_id, user_id, tier, source, starts_at)
SELECT b.id, s.identity_id, s.tier, 'legacy', s.created_at
FROM cedar_press_subscribers s
JOIN cedar_press_billing_accounts b ON b.legacy_account_id = s.account_id;
ALTER TABLE cedar_press_subscribers
    ALTER COLUMN identity_id SET NOT NULL,
    ALTER COLUMN sessions_revoked_at SET NOT NULL,
    ALTER COLUMN sessions_revoked_at SET DEFAULT now(),
    ADD CONSTRAINT cedar_press_subscriber_identity_unique UNIQUE (identity_id);

CREATE FUNCTION cedar_press_sync_legacy_subscriber() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE
    identity UUID;
    billing UUID;
BEGIN
    IF TG_OP = 'INSERT' THEN
        IF NEW.identity_id IS NOT NULL THEN
            RAISE EXCEPTION 'legacy_identity_insert_forbidden';
        END IF;
        -- Preserve trusted legacy upserts on an already linked subscriber.
        -- Do not attach a different existing identity by matching an email.
        SELECT identity_id INTO identity FROM cedar_press_subscribers
        WHERE email = NEW.email;
        IF FOUND THEN
            NEW.identity_id := identity;
            RETURN NEW;
        END IF;
        INSERT INTO cedar_press_users (email, created_at)
        VALUES (lower(btrim(NEW.email)), NEW.created_at) RETURNING id INTO identity;
        NEW.identity_id := identity;
    ELSE
        IF NEW.identity_id IS DISTINCT FROM OLD.identity_id THEN
            RAISE EXCEPTION 'legacy_identity_rebinding_forbidden';
        END IF;
        -- A raw legacy email edit cannot establish whether this is the same
        -- person or a seat reassignment. Neither operation is implemented here.
        IF lower(btrim(NEW.email)) IS DISTINCT FROM lower(btrim(OLD.email)) THEN
            RAISE EXCEPTION 'legacy_email_change_requires_verified_flow';
        END IF;
        IF NEW.password_hash IS DISTINCT FROM OLD.password_hash
           OR NEW.account_id IS DISTINCT FROM OLD.account_id
           OR NEW.user_id IS DISTINCT FROM OLD.user_id THEN
            NEW.sessions_revoked_at := GREATEST(
                clock_timestamp(), OLD.sessions_revoked_at + interval '1 microsecond'
            );
        END IF;
    END IF;
    IF NEW.account_id IS NULL OR btrim(NEW.account_id) = '' THEN
        RAISE EXCEPTION 'legacy_account_id_required';
    END IF;
    INSERT INTO cedar_press_billing_accounts (legacy_account_id)
    VALUES (NEW.account_id)
    ON CONFLICT (legacy_account_id) DO UPDATE
    SET legacy_account_id = EXCLUDED.legacy_account_id RETURNING id INTO billing;
    INSERT INTO cedar_press_membership_grants(account_id, user_id, role, source)
    VALUES (billing, NEW.identity_id, 'member', 'legacy') ON CONFLICT DO NOTHING;
    IF TG_OP = 'UPDATE' AND NEW.account_id IS DISTINCT FROM OLD.account_id THEN
        DELETE FROM cedar_press_membership_grants
        WHERE user_id = NEW.identity_id AND source = 'legacy' AND account_id IN (
            SELECT id FROM cedar_press_billing_accounts WHERE legacy_account_id = OLD.account_id
        );
    END IF;
    -- Keep closed grants as history. A tier or account change closes the old
    -- grant and starts a fresh one; unchanged writes leave history untouched.
    IF NOT EXISTS (
        SELECT 1 FROM cedar_press_access_grants
        WHERE user_id = NEW.identity_id AND source = 'legacy' AND revoked_at IS NULL
          AND account_id = billing AND tier = NEW.tier
    ) THEN
        UPDATE cedar_press_access_grants SET revoked_at = clock_timestamp()
        WHERE user_id = NEW.identity_id AND source = 'legacy' AND revoked_at IS NULL;
        INSERT INTO cedar_press_access_grants(account_id, user_id, tier, source, starts_at)
        VALUES (billing, NEW.identity_id, NEW.tier, 'legacy', clock_timestamp());
    END IF;
    RETURN NEW;
END;
$$;
CREATE TRIGGER cedar_press_legacy_subscriber_bridge
BEFORE INSERT OR UPDATE OF email, account_id, tier, identity_id, password_hash, user_id
ON cedar_press_subscribers FOR EACH ROW
EXECUTE FUNCTION cedar_press_sync_legacy_subscriber();

CREATE FUNCTION cedar_press_remove_legacy_access() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    UPDATE cedar_press_access_grants SET revoked_at = clock_timestamp()
    WHERE user_id = OLD.identity_id AND source = 'legacy' AND revoked_at IS NULL;
    DELETE FROM cedar_press_membership_grants
    WHERE user_id = OLD.identity_id AND source = 'legacy' AND account_id IN (
        SELECT id FROM cedar_press_billing_accounts WHERE legacy_account_id = OLD.account_id
    );
    RETURN OLD;
END;
$$;
CREATE TRIGGER cedar_press_legacy_subscriber_removal
AFTER DELETE ON cedar_press_subscribers FOR EACH ROW
EXECUTE FUNCTION cedar_press_remove_legacy_access();
