# The database

See the [schema ERD](#schema-erd) for the tables defined by migrations 001–003.

## Local Docker database

Run from the repository root:

```sh
make db-up
make db-migrate
make db-test
make db-shell
```

Docker Desktop must be running. PostgreSQL 16 listens on `127.0.0.1:55432`.
Local services are defined in the root `docker-compose.yml`.
The test image uses `server/Dockerfile.test`, beside the production Dockerfile,
with the repository root as its build context.
The test tools container uses Python 3.12, Node 22 and Git, and installs the server's development and
PostgreSQL dependencies. Rebuild it after dependency changes with
`docker compose build tools`.

For a host-run API, set
`DATABASE_URL=postgresql://cedar_local:local_development_only@127.0.0.1:55432/cedar_press`.
These credentials are for local development only.

Open http://localhost:8081 for Adminer. Choose PostgreSQL, server `db`, username
`cedar_local`, password `local_development_only`, database `cedar_press`.
This lets you inspect subscriber records and the Cedar Points transaction ledger.
Payment, invoice, refund and webhook history will be added with the billing
implementation; the current schema has no Stripe transaction tables. Local
Stripe testing will use sandbox payments, persisted in this development database.

The named Docker volume preserves records across container restarts and
`make db-stop`. Each `make db-test` invocation creates a uniquely named disposable
database, creates the optional platform-user compatibility fixture, applies the
real application migrations, and drops that database afterward. Tests truncate
their own tables and never target the development database. The runner uses
`CEDAR_PRESS_TEST_DATABASE_ADMIN_URL` only to create and remove its database;
it sets `CEDAR_PRESS_TEST_DATABASE_URL` to the new database before loading tests.
No volume initialization script is needed. `make db-test` exercises the existing
subscriber, account, session, points and release-download contracts, including
standalone database migration. Any skipped test fails this command. The subscriber
storage CI workflow builds the same `server/Dockerfile.test` and runs `make db-test`
against a fresh disposable Docker volume. `server/Dockerfile` remains the
production API image; the test image is not deployed.

`make db-migrate` applies migrations to the development database; repeat it to
check that no migration is applied twice. `make db-shell` opens SQL access to
that database. Do not remove the volume if you want to keep local transactions.

## Account foundation and direct billing

Cedar Press owns account creation, Stripe billing, renewals and upgrades
(Brian Kim, 2026-10-25). Older TBN-only payment descriptions below describe
the legacy access-code integration and do not define the billing roadmap.
The Terraform deployment uses a dedicated PostgreSQL database; sharing a
database with teim-app remains an optional compatibility arrangement.

Cedar Press supports individual accounts. Migration `003_account_foundation.sql`
extends the existing `cedar_press_subscribers` account table instead of creating
a parallel users table:

| Table | Purpose |
| --- | --- |
| `cedar_press_subscribers` | Existing UUID, email and password hash, plus verification, Stripe customer and session revision fields |
| `cedar_press_login_identities` | Google sign-in subject linked directly to the account UUID |
| `cedar_press_access_grants` | Individual legacy or complimentary access, including revocation history |

Existing account IDs, password hashes, timestamps and Cedar Points grouping are
preserved. There are no group accounts, memberships, `identity_id` column or
identity synchronization triggers. Future subscriptions and payment records will
reference the existing account UUID. Registration, Google sign-in and Stripe
billing flows are not implemented yet.

A null legacy tier represents an account without legacy access. Code redemption
creates the account and legacy grant in the same transaction; duplicate-account
redemption leaves the code unspent and does not replace credentials. Tier changes
close the previous legacy grant and create a new one. Setting the tier to null
revokes legacy grants while preserving the account, Google identity and independent
complimentary grants. Existing runtime access checks still use the legacy tier.
Accounts with grant history cannot be accidentally hard-deleted through the foreign
key; deliberate account deletion is a separate future lifecycle flow.

Password, binding and access-disable changes advance `sessions_revoked_at`.
Ordinary timestamps and changes between active tiers do not sign users out.
Sign-in and activation do not automatically link teim-app accounts. Raw email or
UUID reassignment is refused until a verified account-management flow exists.

`accounts.create_user` creates an internal unpaid account with no password or
access grant. New public registration and unpaid sign-in are subsequent changes.
This unmerged PR uses one account-foundation migration. Databases that ran earlier
branch drafts require local reconciliation; editing an applied migration file alone
does not change their schema. The local empty draft tables were replaced
transactionally, retaining the original application records and migration ledger.

The migrations are transactional. Roll back the application only after
ending outstanding sessions, since old and new logout writers differ. Do not drop
foundation tables or rerun historical migration SQL manually. Rehearse the changes
with `make db-test`, which creates isolated pre-migration databases and verifies
credential/cookie preservation, unpaid access refusal, provider uniqueness,
atomic legacy provisioning and explicit session revocation.

Cedar Press runs with or without one, and the switch is `DATABASE_URL` — the
same variable teim-app reads, so one deployment configures both services by
setting it once.

## Unset

Exactly what the service did before this existed: subscribers parsed out of
`CEDAR_PRESS_ACCOUNTS`, access codes out of `CEDAR_PRESS_CODES`, anything
activated at runtime held in a dict the process forgets on restart, and Cedar
Points in a SQLite file at `CEDAR_PRESS_DB` that defaults to `:memory:`.

That is right for the preview deployment and for the test suite. It is wrong
for anything a subscriber has paid for: a restart loses every account created
by activation, and an access code that was spent becomes spendable again.

## Set

    pip install -e server[postgres]
    DATABASE_URL=postgresql://user:pass@host/db

Subscribers, access codes, the Cedar Points ledger and the priorities
catalogue become rows in the platform's own database, beside teim-app's
`users`. Setting the variable is the whole of the installation: the service
applies any migration that has not run when it opens the store.

That is safe while every migration is additive — all of them so far are
`CREATE TABLE IF NOT EXISTS` — because the advisory lock makes two instances
booting at once take turns instead of racing, and an instance still running
the old code is reading tables the new migration only added to. It stops
being safe the first time a migration drops or retypes a column an older
instance is still reading. At that point run it as a deploy step instead:

    DATABASE_URL=postgresql://user:pass@host/db python -m cedar_press.migrate

which is the same code, idempotent, under the same lock, and prints what it
applied.

## What the tables are

| table                         | what it holds                                           |
| ----------------------------- | ------------------------------------------------------- |
| `cedar_press_subscribers`     | who holds a subscription, on which tier, and their hash  |
| `cedar_press_codes`           | codes Tribal Business News issued, and when each was spent |
| `cedar_press_priorities`      | the editorial catalogue, re-seeded from the owner's file |
| `cedar_press_ledger`          | append-only Cedar Points: why each point came or went    |
| `cedar_press_allocations`     | the derived totals per priority                          |
| `cedar_press_reader_profiles` | what a reader says they work on, per seat                |
| `cedar_press_requests`        | research requests, as written                            |

### The seam with `users`

teim-app owns `users(id, email, password_hash, workspace_tier)`, and
`workspace_tier` is the TMAP ladder — seed, sprout, sapling, tree. Cedar
Press's ladder is `press` and `press_pro`, sold through Tribal Business News,
and a person can hold one, the other, both or neither. So the press tier is a
row in `cedar_press_subscribers` rather than a column on `users`, and the two
ladders never have to be collapsed into one.

### A database of its own

`users` is teim-app's table, not this service's, and pointing Cedar Press at
a database that does not have it is supported: the migration adds the foreign
key only when the table is there, and `link_platform_account` asks
`to_regclass` and does nothing when it is not. A deployment that later puts
teim-app in the same database gets the key on the next migration pass.

`cedar_press_subscribers.user_id` is nullable on purpose. A Tribal Business
News subscriber can arrive with an access code before they have ever opened
the platform, and refusing them until a `users` row exists would make the
platform a prerequisite for a product sold separately. `email` is the key that
always exists; `subscribers.bind_user` ties the two together when a platform
account appears, and a unique index stops one platform account holding two
subscriptions.

## Running the tests against it

    CEDAR_PRESS_TEST_DATABASE_URL=postgresql://... \
      python3 -m unittest discover -s tests

`tests/test_subscribers.py` and `tests/test_priorities.py` each run their
whole set twice — once on the store a preview runs on, once on Postgres —
because a seam whose two sides disagree is worse than no seam: the
disagreement only shows up in production. Without the variable the Postgres
half skips.

For the points rule that doubling is the thing that matters most. The expiry
arithmetic and the allocation rule are written once and run against both
stores; what could still differ is the dialect underneath — a partial unique
index that does not fire, an `ON CONFLICT` clause Postgres reads differently,
a timestamp that comes back as a `datetime` where the API contract says
string. Twelve assertions about the rule, made twice, are what rule that out.

### The one thing the tests cannot show

That a balance survives the process that earned it. The rule tests pass on
`:memory:`, which forgets — that was the bug. Prove it against a real
database by earning in one process and reading in another:

    DATABASE_URL=postgresql://... python - <<'EOF'
    from cedar_press import priorities as pr
    s = pr.open_store()
    a = pr.Account("acct-demo", "you@example.org", "press_pro")
    print(s.accrue(a), s.balance(a.account_id))
    EOF

Run it twice. The first run credits 2 and reports 2; the second credits 0 —
the month is already earned — and still reports 2.

## Schema ERD

Current PostgreSQL schema after migrations 001–003. `cedar_press_subscribers`
is the sole account table. Connections show database foreign keys only; dotted
lines are non-identifying relationships. `users` is an optional external teim-app
table, not a second Cedar Press user table. Its foreign key is installed only
when that table exists during migration 001. Automatic linking is disabled.

```mermaid
erDiagram
    cedar_press_subscribers ||..o{ cedar_press_login_identities : "id to user_id; cascade delete"
    cedar_press_subscribers ||..o{ cedar_press_access_grants : "id to user_id; NO ACTION delete"
    users |o..o| cedar_press_subscribers : "optional platform user_id"

    cedar_press_subscribers {
        uuid id PK
        text email UK
        text account_id "Legacy Cedar Points key"
        text tier "Nullable; press or press_pro"
        text password_hash "Nullable; never plaintext"
        uuid user_id FK,UK "Nullable external teim-app ID"
        timestamptz created_at
        timestamptz updated_at
        timestamptz email_verified_at "Nullable"
        text stripe_customer_id UK "Nullable"
        timestamptz sessions_revoked_at
    }
    cedar_press_login_identities {
        uuid id PK
        uuid user_id FK
        text provider "google"
        text subject "Unique with provider"
        timestamptz created_at
    }
    cedar_press_access_grants {
        uuid id PK
        uuid user_id FK
        text tier "press or press_pro"
        text source "legacy or complimentary"
        timestamptz starts_at
        timestamptz ends_at "Nullable"
        timestamptz revoked_at "Nullable"
    }
    cedar_press_codes {
        text code PK
        text email
        text tier
        date expires_on "Nullable"
        timestamptz spent_at "Nullable"
        text spent_by "Nullable"
        timestamptz created_at
    }
    cedar_press_reader_profiles {
        text email PK
        text work "Nullable"
        timestamptz updated_at
    }
    cedar_press_priorities {
        text id PK
        text type
        text title
        text description
        text status
        text created_by "Nullable"
        text published_output "Nullable"
        text evolved_from "Nullable"
        timestamptz created_at
    }
    cedar_press_ledger {
        bigint id PK
        text account_id
        text user_id "Nullable; text, not account UUID"
        int amount
        text reason
        text priority_id "Nullable"
        text month "Nullable"
        timestamptz created_at
    }
    cedar_press_allocations {
        text account_id PK "Composite primary key"
        text priority_id PK "Composite primary key"
        int points
        timestamptz created_at
        timestamptz updated_at
    }
    cedar_press_requests {
        bigint id PK
        text account_id
        text user_id "Nullable; text, not account UUID"
        text text
        text priority_id "Nullable"
        text use_case "Nullable"
        text status
        timestamptz created_at
    }
    cedar_press_migrations {
        text filename PK
        timestamptz applied_at
    }
    users {
        uuid id PK "External table; other columns omitted"
    }
```

Application-level references without database foreign keys:

| Fields | Reference |
| --- | --- |
| Codes `email` and `spent_by`; reader profiles `email` | Subscriber email |
| Ledger, allocations and requests `account_id` | Legacy subscriber `account_id`; not unique per subscriber |
| Ledger, allocations and requests `priority_id`; priorities `evolved_from` | Priority ID |

Google identities are unique by `(provider, subject)` and `(user_id, provider)`.
At most one unrevoked legacy access grant exists per account. Subscriber emails
also have a normalized unique index. The Cedar Points ledger records points,
not money; Stripe subscription, invoice, payment and refund tables are not yet
implemented. See migration 003 for account-security and legacy-grant triggers.
