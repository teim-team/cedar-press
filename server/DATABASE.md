# The database

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
