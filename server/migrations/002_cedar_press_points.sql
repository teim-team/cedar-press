-- Shape the Research: the Cedar Points ledger, moved off SQLite.
--
-- WHY IT MOVED. `priorities.py` kept this in SQLite, defaulting to
-- `:memory:` -- so unless a deployment happened to set CEDAR_PRESS_DB, every
-- point a subscriber had ever earned was discarded on restart. For a ledger
-- whose whole design is "append-only, so any balance can be explained", a
-- default that forgets is the one thing it cannot be.
--
-- WHY THE COLUMN NAMES ARE THE SQLITE ONES. `priorities.py` holds the rule
-- -- twelve-month expiry, oldest spent first, one credit per subscription
-- per month -- and that rule is the part that must not exist twice. Naming
-- these columns exactly as the SQLite schema names them lets every statement
-- in that module be written once and run against either store, so there is
-- no second implementation of the expiry arithmetic to drift out of step
-- with the first. The tables are prefixed because they live in the
-- platform's own database beside teim-app's `users`, not in a database of
-- their own; the columns are not, because nothing else reads them.
--
-- `account_id` is now joinable to `cedar_press_subscribers.account_id`,
-- which is what that module's docstring has been waiting for: "When the
-- subscriber table arrives the account id here is its key."

-- The editorial catalogue. `data/cedar/priorities.json` is the owner's and
-- stays the source: the store re-seeds these fields from the file on every
-- start and never writes them back. The table exists so the totals can be
-- joined to a title in SQL rather than reassembled in Python.
CREATE TABLE IF NOT EXISTS cedar_press_priorities (
  id               TEXT PRIMARY KEY,
  type             TEXT NOT NULL CHECK (type IN ('research_question', 'dataset')),
  title            TEXT NOT NULL,
  description      TEXT NOT NULL DEFAULT '',
  status           TEXT NOT NULL DEFAULT 'interest',
  created_by       TEXT,
  published_output TEXT,
  evolved_from     TEXT,
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- THE LEDGER IS APPEND-ONLY. A balance is a sum over rows that each say why
-- a point came or went. Nothing here is updated and nothing is deleted, so a
-- balance a subscriber disputes can be walked back to the month it was
-- earned. `cedar_press_allocations` is the derived table kept for the totals.
CREATE TABLE IF NOT EXISTS cedar_press_ledger (
  id          BIGSERIAL PRIMARY KEY,
  account_id  TEXT NOT NULL,
  -- The seat that acted, for the activity list. The subscription earns and
  -- spends; the seat is only who was holding the pen.
  user_id     TEXT,
  amount      INTEGER NOT NULL,
  reason      TEXT NOT NULL
              CHECK (reason IN ('monthly_activity', 'allocation', 'refund', 'expiration')),
  priority_id TEXT,
  -- The month the points were EARNED, not the month they were spent: expiry
  -- runs twelve months from earning and oldest is spent first, so a row that
  -- loses this cannot be expired correctly.
  month       TEXT,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_cedar_press_ledger_account
  ON cedar_press_ledger (account_id, id);

-- One earning row per subscription per month, enforced by the database
-- rather than by a read-then-write in the application: two seats of one
-- organization signing in at the same moment is exactly the race that hands
-- out double points, and it is not reproducible in a test suite.
CREATE UNIQUE INDEX IF NOT EXISTS idx_cedar_press_ledger_monthly
  ON cedar_press_ledger (account_id, month)
  WHERE reason = 'monthly_activity';

CREATE TABLE IF NOT EXISTS cedar_press_allocations (
  account_id  TEXT NOT NULL,
  priority_id TEXT NOT NULL,
  points      INTEGER NOT NULL,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (account_id, priority_id)
);

-- What a reader says they work on: one optional answer per SEAT, never per
-- subscription, because two seats of one organization can do different work.
CREATE TABLE IF NOT EXISTS cedar_press_reader_profiles (
  email      TEXT PRIMARY KEY,
  work       TEXT,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- A subscriber's request in their own words. `text` is a type name in
-- Postgres but a legal column name, and it is the name the SQLite schema
-- already uses; see the note at the top about why that matters more here.
CREATE TABLE IF NOT EXISTS cedar_press_requests (
  id          BIGSERIAL PRIMARY KEY,
  account_id  TEXT NOT NULL,
  user_id     TEXT,
  text        TEXT NOT NULL,
  priority_id TEXT,
  use_case    TEXT,
  status      TEXT NOT NULL DEFAULT 'received',
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_cedar_press_requests_account
  ON cedar_press_requests (account_id, id DESC);
