-- A requested change of sign-in address, confirmed from the new inbox.
-- Only the token's hash is stored; one live request per account.
CREATE TABLE cedar_press_email_changes (
    token_hash TEXT PRIMARY KEY CHECK (token_hash ~ '^[0-9a-f]{64}$'),
    user_id UUID NOT NULL REFERENCES cedar_press_subscribers(id) ON DELETE CASCADE,
    new_email TEXT NOT NULL CHECK (new_email = lower(btrim(new_email)) AND new_email <> ''),
    expires_at TIMESTAMPTZ NOT NULL,
    used_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX cedar_press_email_change_live
    ON cedar_press_email_changes(user_id) WHERE used_at IS NULL;

-- The guard from 004, now letting the verified flow through: the transaction
-- that redeems a confirmed link marks itself with SET LOCAL, so an ad hoc
-- UPDATE of the address is still refused. A new address ends every session.
CREATE OR REPLACE FUNCTION cedar_press_guard_account() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.id IS DISTINCT FROM OLD.id THEN
        RAISE EXCEPTION 'account_identity_immutable';
    END IF;
    IF lower(btrim(NEW.email)) IS DISTINCT FROM lower(btrim(OLD.email))
       AND current_setting('cedar_press.verified_email_change', true) IS DISTINCT FROM 'on' THEN
        RAISE EXCEPTION 'account_email_change_requires_verified_flow';
    END IF;
    IF NEW.password_hash IS DISTINCT FROM OLD.password_hash
       OR lower(btrim(NEW.email)) IS DISTINCT FROM lower(btrim(OLD.email))
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
