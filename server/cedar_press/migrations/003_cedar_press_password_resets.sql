-- Password reset links. Only a SHA-256 of each token is kept, so a read of
-- this table cannot reset anybody's password.
--
-- No foreign key to `cedar_press_subscribers`: a reference would make every
-- TRUNCATE of that table fail, and a token for a removed subscriber already
-- redeems to nothing because the password update finds no row.
--
-- Rows are written only for an address that is already a subscriber's, so
-- an unknown address asking for a link never lands here.

CREATE TABLE IF NOT EXISTS cedar_press_password_resets (
  token_hash TEXT PRIMARY KEY CHECK (token_hash ~ '^[0-9a-f]{64}$'),
  email      TEXT NOT NULL CHECK (email = lower(email) AND length(email) <= 254),
  expires_at TIMESTAMPTZ NOT NULL,
  used_at    TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- One live link per address: issuing a new one replaces the old in place
-- (`subscribers.issue_reset`), so an older email in the inbox stops working.
CREATE UNIQUE INDEX IF NOT EXISTS idx_cedar_press_password_resets_live
  ON cedar_press_password_resets (email) WHERE used_at IS NULL;
