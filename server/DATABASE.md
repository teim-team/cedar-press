# The database

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
