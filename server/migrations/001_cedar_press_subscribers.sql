-- Cedar Press's own tables, in the platform's database.
--
-- WHY THESE LIVE BESIDE teim-app's TABLES AND NOT IN A DATABASE OF THEIR OWN.
-- A Cedar Press subscriber is a person, and that person may also hold a TMAP
-- plan. Two databases would mean two answers to "who is this" and a
-- reconciliation job to keep them agreeing, which is the problem Cedar itself
-- exists to solve for everybody else's records. One database, one identity,
-- and this file adds only what Cedar Press knows that the platform does not.
--
-- THE SEAM WITH `users`. teim-app owns `users(id UUID, email UNIQUE,
-- password_hash, workspace_tier)`; `workspace_tier` is the TMAP ladder
-- (seed/sprout/sapling/tree) and is none of Cedar Press's business. Cedar
-- Press's ladder is press/press_pro, sold through Tribal Business News, and
-- a person can hold one, the other, both or neither. So the press tier is a
-- row here rather than a column there, and the two ladders never have to be
-- collapsed into one.
--
-- `user_id` is nullable ON PURPOSE. A Tribal Business News subscriber may
-- arrive with an access code before they have ever signed into the platform,
-- and refusing them until a `users` row exists would make the platform a
-- prerequisite for a product sold separately. `email` is the key that always
-- exists; `user_id` is bound when the platform account does, and the unique
-- index on it keeps one platform account from holding two subscriptions.

CREATE TABLE IF NOT EXISTS cedar_press_subscribers (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email         TEXT NOT NULL UNIQUE,
  -- The SUBSCRIPTION an address belongs to. Two seats of one organization
  -- share it, which is what `account_id_for` computes today and what the
  -- points ledger counts by: 30 points from 25 organizations is not 30 from
  -- 5, and the difference is only visible if seats are grouped.
  account_id    TEXT NOT NULL,
  tier          TEXT NOT NULL CHECK (tier IN ('press', 'press_pro')),
  password_hash TEXT,
  user_id       UUID REFERENCES users(id) ON DELETE SET NULL,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_cedar_press_subscribers_user
  ON cedar_press_subscribers (user_id) WHERE user_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_cedar_press_subscribers_account
  ON cedar_press_subscribers (account_id);

-- Access codes, issued by Tribal Business News and spent once.
--
-- `spent_at` rather than a delete, because "this code was used, on this day,
-- by this address" is the question asked when a subscriber says they never
-- received their access and somebody has to find out what happened. A row
-- that is gone cannot answer it.
CREATE TABLE IF NOT EXISTS cedar_press_codes (
  code        TEXT PRIMARY KEY,
  email       TEXT NOT NULL,
  tier        TEXT NOT NULL CHECK (tier IN ('press', 'press_pro')),
  expires_on  DATE,
  spent_at    TIMESTAMPTZ,
  spent_by    TEXT,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_cedar_press_codes_email
  ON cedar_press_codes (lower(email));
