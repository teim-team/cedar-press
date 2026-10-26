# The database

See the [schema ERD](#schema-erd) for the tables defined by migrations 001–009.

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
This lets you inspect accounts, Cedar Points, Stripe subscriptions, invoices,
payments, refunds, checkout attempts and webhook processing history. Sandbox
transactions persist in this database. Card details stay with Stripe.

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

Cedar Press supports individual accounts. Migration `004_account_foundation.sql`
extends the existing `cedar_press_subscribers` account table instead of creating
a parallel users table:

| Table | Purpose |
| --- | --- |
| `cedar_press_subscribers` | Existing UUID, email and password hash, plus verification, Stripe customer and session revision fields |
| `cedar_press_login_identities` | Google sign-in subject linked directly to the account UUID |
| `cedar_press_access_grants` | Individual legacy or complimentary access, including revocation history |

Existing account IDs, password hashes, timestamps and Cedar Points grouping are
preserved. There are no group accounts, memberships, `identity_id` column or
identity synchronization triggers. Stripe subscription and payment records reference the existing account UUID.
New subscribers purchase at `/subscribe`, then follow the emailed link to
`/create-account` to confirm their email and choose a password. Google sign-in
remains separate work.

A null legacy tier represents an account without legacy access. Code redemption
creates the account and legacy grant in the same transaction; duplicate-account
redemption leaves the code unspent and does not replace credentials. Tier changes
close the previous legacy grant and create a new one. Setting the tier to null
revokes legacy grants while preserving the account, Google identity and independent
complimentary grants. Runtime access uses `cedar_press_current_access`, combining active grants and
confirmed paid invoice coverage. After the first paid Stripe invoice, legacy
grants no longer restore access when that subscription ends. Complimentary
grants remain independent.
Accounts with grant history cannot be accidentally hard-deleted through the foreign
key; deliberate account deletion is a separate future lifecycle flow.

Password, binding and access-disable changes advance `sessions_revoked_at`.
Ordinary timestamps and changes between active tiers do not sign users out.
Sign-in and activation retain the existing optional teim-app account linking. Raw email or
UUID reassignment is refused until a verified account-management flow exists.

`accounts.create_user` creates an internal unpaid account. Unpaid and expired
accounts can sign in and manage billing; paid content remains protected.

### Stripe sandbox

Keep credentials in the ignored root `.env`. Compose accepts `STRIPE_TEST_KEY`
as a local alias for `CEDAR_PRESS_STRIPE_SECRET_KEY`.

```sh
docker compose build tools
docker compose run --rm tools python server/tools/setup_stripe.py
```

Save the printed price, portal and coupon IDs in `.env`. Obtain the listener's
signing secret with `docker compose run --rm stripe-listener listen --print-secret`
and save it as `CEDAR_PRESS_STRIPE_WEBHOOK_SECRET`. Treat it as a credential.
Then start `docker compose --profile app --profile billing up -d` and run
`npm run dev:connected -- --port 5173 --strictPort`. Open `/subscribe` with a
plan. The button goes directly to Stripe, which collects email and discount codes.
Checkout reservations create no users. A confirmed payment creates a new account
and emails its single-use setup link. Existing emails retain their account and
credentials and receive a sign-in link. This flow does not block repeat purchases.
Open the local Mailpit inbox at http://localhost:8025 to follow that link.
Stripe forwards signed sandbox events to the API. Restart the API after
changing `.env`.

SMTP settings are `CEDAR_PRESS_SMTP_HOST`, `CEDAR_PRESS_SMTP_PORT`,
`CEDAR_PRESS_SMTP_STARTTLS`, `CEDAR_PRESS_SMTP_USERNAME`,
`CEDAR_PRESS_SMTP_PASSWORD` and `CEDAR_PRESS_EMAIL_FROM`. Docker defaults to
Mailpit with plaintext SMTP confined to the Docker network. Production requires
STARTTLS and the chosen email provider's settings. Guest purchases refuse when
email delivery is unconfigured. Password recovery uses the same sender.
The confirmation page can resend its own paid account email, limited to three
requests per 15 minutes. Migration 009 adds leased email delivery and hashed setup links.
SMTP runs outside transactions; failed resends preserve earlier unexpired links.
Webhook retries or the reconciliation command retry pending deliveries.
Only hashed browser and email tokens are stored; neither the browser's Checkout
return nor its reservation cookie can establish account ownership.

The setup command is repeatable and requires `--live` for live-account setup.
Prices are annual USD: $500/$1,000 early access, $1,000/$2,000 from January 1,
2027 in America/Chicago. `GREATLAKES2026` deducts $100 from the first invoice.
Cedar Press and Cedar Press+ use separate Stripe products so Checkout names the
selected tier correctly. Each cohort uses tier-specific portal configurations
offering only the other tier’s cohort price. Previous price IDs remain in
`CEDAR_PRESS_STRIPE_LEGACY_PRICES` for existing purchases; new purchases use the
primary configured prices. Settings links directly to Stripe’s plan-change
confirmation; the general portal manages payment methods, invoices and cancellation.
Upgrades invoice prorations immediately; downgrades
and cancellation take effect at renewal. Existing subscriptions retain their
cohort. Stripe calculates prorations.

Webhook events are deduplicated and reconcile affected Stripe objects off the API
event loop. Provider reads use a customer session lock without an open SQL transaction;
the repair command performs full-history reconciliation. Each subscription has its
own account-management action, with ownership checked on the server.
The inbox stores IDs, attempts and processing status, without raw payloads.
Invoices, payments and refunds are current snapshots with provider IDs;
Stripe remains the financial system of record. Full refunds remove that
invoice's access coverage; partial refunds retain it. Access never comes from
the browser's Checkout return URL. Confirmation and resend target the reservation
ID from that return URL and require its browser cookie. Recovery searches only
the reservation window. Changing a signed-in checkout's plan or discount expires
the previous Stripe session before creating its replacement.

Retry reconciliation after provider failures with:

```sh
docker compose run --rm tools python -m cedar_press.billing.cli reconcile
```

For production, register `/billing/webhook` with API version
`2026-09-30.endive`, configure its signing secret and canonical `CEDAR_PRESS_*`
variables, and run reconciliation periodically as an operational recovery job.
Local Compose is for development only. `make db-test` covers migrations and
billing lifecycle failures in disposable databases.

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

The migration ledger and advisory lock make simultaneous API starts take turns
instead of racing. Keep deployment migrations compatible with the application
version still serving requests. Automatic startup migration stops
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
| `cedar_press_account_setup_links` | hashed, expiring setup links bound to account and email |
| `cedar_press_account_email_deliveries` | delivery attempts and leases per paid checkout |
| `cedar_press_password_resets` | hashed, single-use password reset tokens and their expiry |
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

Current PostgreSQL schema after migrations 001–009. `cedar_press_subscribers`
is the sole account table. Connections show database foreign keys only; dotted
lines are non-identifying relationships. `users` is an optional external teim-app
table, not a second Cedar Press user table. Its foreign key is installed only
when that table exists during migration 001. Password-authenticated sign-in and
activation link a matching platform account before issuing the session cookie.

```mermaid
erDiagram
    cedar_press_subscribers ||..o{ cedar_press_login_identities : "id to user_id; cascade delete"
    cedar_press_subscribers ||..o{ cedar_press_access_grants : "id to user_id; NO ACTION delete"
    cedar_press_subscribers ||..o{ cedar_press_subscriptions : user_id
    cedar_press_subscribers ||..o{ cedar_press_invoices : user_id
    cedar_press_subscribers ||..o{ cedar_press_payments : user_id
    cedar_press_subscribers ||..o{ cedar_press_checkout_attempts : user_id
    cedar_press_subscribers |o..o{ cedar_press_guest_checkouts : "user_id after payment"
    cedar_press_subscribers ||..o{ cedar_press_account_setup_links : user_id
    cedar_press_guest_checkouts ||..o| cedar_press_account_email_deliveries : checkout_id
    cedar_press_subscriptions ||..o{ cedar_press_invoices : subscription_id
    cedar_press_payments ||..o{ cedar_press_refunds : payment_id
    users |o..o| cedar_press_subscribers : "optional platform user_id"

    cedar_press_subscribers {
        uuid id PK
        text email UK
        text display_name "Nullable"
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
    cedar_press_account_setup_links {
        text token_hash PK
        uuid user_id FK
        text email
        timestamptz expires_at
        timestamptz used_at
        timestamptz created_at
    }
    cedar_press_account_email_deliveries {
        uuid checkout_id PK,FK
        text status
        uuid lease_id
        timestamptz lease_until
        integer attempts
        timestamptz updated_at
    }
    cedar_press_subscriptions {
        text id PK "Stripe subscription"
        uuid user_id FK
        text price_id
        text tier
        text cohort
        text customer_id "Stripe customer for this subscription"
        text status
        boolean cancel_at_period_end
        timestamptz period_end
        timestamptz activated_at
    }
    cedar_press_invoices {
        text id PK
        uuid user_id FK
        text subscription_id FK
        text status
        text currency
        bigint amount_due "Integer cents"
        bigint amount_paid "Integer cents"
        text tier
        timestamptz access_starts_at
        timestamptz access_ends_at
    }
    cedar_press_payments {
        text id PK "Stripe PaymentIntent"
        uuid user_id FK
        text invoice_id "Nullable, no FK; events can arrive first"
        text charge_id
        text status
        text currency
        bigint amount
        bigint amount_received
    }
    cedar_press_refunds {
        text id PK
        text payment_id FK
        text status
        text currency
        bigint amount
    }
    cedar_press_checkout_attempts {
        uuid id PK
        uuid user_id FK
        text price_id
        text session_id UK "Nullable"
        text status
        timestamptz expires_at
    }
    cedar_press_guest_checkouts {
        uuid id PK
        text email "Nullable until Stripe confirms payment"
        text secret_hash "Hashed browser cookie; no sign-in authority"
        text price_id
        text customer_id UK
        text session_id UK
        text status
        uuid user_id FK "Nullable until payment confirmed"
        timestamptz expires_at
        timestamptz claim_sent_at
    }
    cedar_press_webhook_events {
        text id PK
        text event_type
        text object_id
        text customer_id
        text status
        int attempts
        text error_code
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
not money. See migration 004 for account-security and legacy-grant triggers
and migration 005 for Stripe records and effective access.
