-- Extend the existing account store; passwords and account UUIDs stay in place.
CREATE UNIQUE INDEX cedar_press_subscriber_normalized_email
    ON cedar_press_subscribers(lower(btrim(email)));
ALTER TABLE cedar_press_subscribers
    ADD COLUMN email_verified_at TIMESTAMPTZ,
    ADD COLUMN stripe_customer_id TEXT UNIQUE,
    ADD COLUMN sessions_revoked_at TIMESTAMPTZ,
    ALTER COLUMN tier DROP NOT NULL,
    ADD CONSTRAINT cedar_press_subscriber_account_required CHECK (btrim(account_id) <> '');
UPDATE cedar_press_subscribers SET sessions_revoked_at = updated_at;
ALTER TABLE cedar_press_subscribers
    ALTER COLUMN sessions_revoked_at SET NOT NULL,
    ALTER COLUMN sessions_revoked_at SET DEFAULT now();

-- Google subjects identify sign-in methods, not separate account records.
CREATE TABLE cedar_press_login_identities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES cedar_press_subscribers(id) ON DELETE CASCADE,
    provider TEXT NOT NULL CHECK (provider IN ('google')),
    subject TEXT NOT NULL CHECK (subject <> ''),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (provider, subject),
    UNIQUE (user_id, provider)
);

-- Explicit grants are for legacy or complimentary access, not Stripe payments.
-- Retain the account while grant history exists; disabling legacy access uses tier=NULL.
CREATE TABLE cedar_press_access_grants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES cedar_press_subscribers(id),
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
INSERT INTO cedar_press_access_grants(user_id, tier, source, starts_at)
SELECT id, tier, 'legacy', created_at FROM cedar_press_subscribers WHERE tier IS NOT NULL;

CREATE FUNCTION cedar_press_guard_account() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.id IS DISTINCT FROM OLD.id THEN
        RAISE EXCEPTION 'account_identity_immutable';
    END IF;
    IF lower(btrim(NEW.email)) IS DISTINCT FROM lower(btrim(OLD.email)) THEN
        RAISE EXCEPTION 'account_email_change_requires_verified_flow';
    END IF;
    IF NEW.password_hash IS DISTINCT FROM OLD.password_hash
       OR NEW.account_id IS DISTINCT FROM OLD.account_id
       OR NEW.user_id IS DISTINCT FROM OLD.user_id
       OR (NEW.tier IS NULL) IS DISTINCT FROM (OLD.tier IS NULL) THEN
        NEW.sessions_revoked_at := GREATEST(
            clock_timestamp(), OLD.sessions_revoked_at + interval '1 microsecond'
        );
    END IF;
    RETURN NEW;
END;
$$;
CREATE TRIGGER cedar_press_account_security
BEFORE UPDATE OF id, email, password_hash, account_id, user_id, tier ON cedar_press_subscribers
FOR EACH ROW EXECUTE FUNCTION cedar_press_guard_account();

CREATE FUNCTION cedar_press_sync_legacy_access() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.tier IS NULL OR NOT EXISTS (
        SELECT 1 FROM cedar_press_access_grants
        WHERE user_id = NEW.id AND source = 'legacy' AND revoked_at IS NULL AND tier = NEW.tier
    ) THEN
        UPDATE cedar_press_access_grants SET revoked_at = clock_timestamp()
        WHERE user_id = NEW.id AND source = 'legacy' AND revoked_at IS NULL;
        IF NEW.tier IS NOT NULL THEN
            INSERT INTO cedar_press_access_grants(user_id, tier, source, starts_at)
            VALUES (NEW.id, NEW.tier, 'legacy', clock_timestamp());
        END IF;
    END IF;
    RETURN NEW;
END;
$$;
CREATE TRIGGER cedar_press_legacy_access
AFTER INSERT OR UPDATE OF tier ON cedar_press_subscribers
FOR EACH ROW EXECUTE FUNCTION cedar_press_sync_legacy_access();
