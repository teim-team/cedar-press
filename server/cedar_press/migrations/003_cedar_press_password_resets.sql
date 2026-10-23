-- Password reset links. Only a SHA-256 of each token is kept, so a read of
-- this table cannot reset anybody's password.
--
-- No foreign key to `cedar_press_subscribers`: a reference would make every
-- TRUNCATE of that table fail, and a token for a removed subscriber already
-- redeems to nothing because the password update finds no row.

CREATE TABLE IF NOT EXISTS cedar_press_password_resets (
  token_hash TEXT PRIMARY KEY,
  email      TEXT NOT NULL,
  expires_at TIMESTAMPTZ NOT NULL,
  used_at    TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_cedar_press_password_resets_email
  ON cedar_press_password_resets (email) WHERE used_at IS NULL;
