# Notes beside `docs/HOSTNAMES.md`: the email path, and what the `app.` alias changes

*Written 2026-09-20. **`docs/HOSTNAMES.md` is the authority on hostnames, TLS,
CloudFront, the bucket and the OIDC role, and nothing here restates it** — an
earlier draft of this file did, against a checkout cut before `bea4961`, and got
the deploy target wrong as a result. That draft's corrections are recorded in §0
rather than deleted. What follows is only what HOSTNAMES.md does not cover:
transactional email, which lives in another repository, and one consequence of
the certificate that touches the session design.*

*Detailed notes on the OIDC failure, SES and the certificate were already posted
for Kaylyn on `lumecon-website#345` by a parallel session. **Read the correction,
not the original**: the first comment
([#issuecomment-5753295546](https://github.com/teim-team/lumecon-website/issues/345#issuecomment-5753295546),
23:00Z) carried two errors, both retracted nine minutes later in
[#issuecomment-5753349768](https://github.com/teim-team/lumecon-website/issues/345#issuecomment-5753349768).
It had claimed the site posts `POST /auth/register` — it does not; `/signup`
collects no password and posts to `/v1/contact`, and `submitSignup` is an unused
export, so deploying teim-app cannot by itself turn on account creation. And it
described a CORS failure as a login that appears to succeed leaving no session —
`fetch` rejects, `api.ts` returns `{ok:false, reason:'network'}` and `/login`
shows a failure; the silent-session symptom belongs to the SameSite case
instead. This file is the repository's copy of the parts that are cedar-press's
own; it is not a second message to her and should not be reposted as one.*

## 0. Two things the first draft of this file got wrong

Recorded rather than silently edited, because both would have sent someone the
wrong way.

1. **"Cedar Press deploys to GitHub Pages, so the certificate does not attach to
   anything."** Wrong, and wrong in the most misleading available way: the
   workflow is *still named* `Deploy to GitHub Pages` and its first job still
   uploads a Pages artifact, but since #87 it also assumes
   `cedarpress-site-deploy`, syncs `dist-site/` to
   `s3://cedarpress-ai-site-502309351676` and invalidates CloudFront
   `E3AEMUAUDGWNTQ`. The apex resolves to CloudFront. The stale workflow *name*
   is worth renaming on its own account — it is what misled this document.
2. **"The certificate takes the cheap cookie option off the table."** The
   opposite, and see §2.
3. **The default sender string.** Read off a teim-app checkout sitting on an
   unmerged branch rather than off `main`. Corrected in §1 — along with the
   reason it was flagged, which was itself wrong: the two strings differ only in
   the display name, and SES verifies an address or a domain, not a display
   name.

## 1. Transactional email: the repository it helps is teim-app

**teim-app is the only repository in the estate that sends email.**
`server/mailer.js`, `@aws-sdk/client-sesv2`, two flows — verification and
password reset.

**The default sender, and why the string is less important than it looks.** On
`main`, `mailer.js:14` reads `Tribal Economic Impact <contact@lumecon.ai>`. An
earlier draft of this file said `Cedar Impact <contact@lumecon.ai>`, which is
what `51d2a752` ("The product is Cedar Impact, from Lumecon") changes it to —
that commit is **not on main**; it rides on the `cedar-grove/*` branches and
teim-app#171, all unmerged. So today's deployed default is the first string and
the second is pending.

**What matters for SES is the address, not the display name.** Both strings
carry the same address, `contact@lumecon.ai`, and an SES identity is a domain or
an email address — the RFC 5322 display name in front of it is not part of the
identity and is not verified. So verify `lumecon.ai` (or `contact@lumecon.ai`)
and the rename cannot break delivery whichever way it lands. That is also the
more robust instruction: verifying one exact *string* would appear to work and
then need redoing.

**cedar-press sends none.** No SES client, no SMTP, no mailer module; a grep
across `server/`, `src/` and `scripts/` returns nothing. Activation and access
codes cannot send mail today, and leaving the SES sandbox does not change that.
When Cedar Press needs to send, it either gains its own path or routes through
the platform — a decision, not a configuration.

**The part worth knowing before switching it on.** Delivery is off unless
`EMAIL_DELIVERY=ses` exactly (trimmed, lowercased). When unset the mailer
**builds the link and silently does nothing**, which is deliberate — it keeps
dev and tests from sending — and it means a half-configured production
deployment is indistinguishable from a working one from outside: signup
succeeds, the reader waits for mail that was never attempted, and the only trace
is an info log line.

| variable | if missing |
| --- | --- |
| `EMAIL_DELIVERY=ses` | nothing is ever sent, no error |
| `EMAIL_VERIFICATION_BASE_URL` | verification mail skipped, logged `not_configured` |
| `PASSWORD_RESET_BASE_URL` | reset mail skipped, the same way |
| `EMAIL_FROM` | falls back to `Cedar Impact <contact@lumecon.ai>` |
| `SES_REGION` / `AWS_REGION` | defaults to `us-east-1` |

And two things outside the repo: the sender must be a verified SES identity, and
the task role needs `ses:SendEmail`. A missing permission makes the send throw;
it is caught, logged as `send_failed`, and **the request still returns 200**. So
permission errors are quiet too. One smoke send to a real inbox after
provisioning is worth more than a green deploy.

**Correction — the DNS side is not prepared, and an earlier draft of this note
said it was.** HOSTNAMES.md records a `_dmarc` record in the `cedarpress.ai`
zone, and DMARC is a *policy* record. It neither verifies a domain as an SES
identity nor installs the SES-issued DKIM CNAMEs that make mail authenticate in
alignment. Treating it as completion is worse than treating it as absent: a
published DMARC policy with unaligned mail means messages that do send get
**rejected or quarantined by the recipient**, on the domain's own instruction.

Three records are needed, and none of them is the one that exists:

- the SES **domain-identity verification** record,
- the three **DKIM** CNAMEs SES issues for that identity,
- SPF, if the policy requires an SPF pass rather than DKIM alignment alone.

And check *which* domain. The mailer's default sender is
`Tribal Economic Impact <contact@lumecon.ai>` (teim-app `server/mailer.js`), so
the identity to verify is **`lumecon.ai`** — a different Route 53 zone from the
`cedarpress.ai` one this note has been describing. The `_dmarc` record that
prompted the original sentence is in the wrong zone for the mail this section is
about.

## 2. `app.cedarpress.ai` is in the certificate, and that is the interesting part

HOSTNAMES.md: the ACM certificate covers `cedarpress.ai`, **`app.cedarpress.ai`**
and `www.cedarpress.ai`, and `app.` is today a 301 to the apex *"until the
subscriber API has a host."*

That sentence is a session-design decision already made, and it is the good one.
`docs/PLATFORM_INTEGRATION_2026-09-06.md` measured that `cedarpress.ai` and
`lumecon.ai` are different **sites**, so the platform's `teim_session` cookie
(`SameSite=Lax`, no `Domain`) sends nothing on a credentialed fetch between them
— and it offered three fixes, recommending a handoff bridge because the cheap
same-site option appeared to require moving Press under `lumecon.ai`.

The certificate points the other way: put the subscriber API on
`app.cedarpress.ai` and the client and its API are **the same site**, so
`SameSite=Lax` stops being the obstacle — no bridge, no `SameSite=None`, no
relaxation of anything.

**But same-site is not the same as same-host, and an earlier draft of this
paragraph conflated them.** A host-only cookie set for `cedarpress.ai` is *not*
sent to `app.cedarpress.ai`; host matching is a separate rule from the SameSite
check, and being same-site relaxes only the latter. Written as "a host-only
cookie on the apex is simply sent", this sentence would have sent someone to
build a session that never arrives, with the certificate and the CORS
configuration both looking correct.

What actually works, and the choice has to be made deliberately:

- **The API sets the cookie itself, responding from `app.cedarpress.ai`.** It is
  then host-only *for that host*, sent on every subsequent call to the API, and
  same-site means `Lax` does not block it. This is the one to pick — no
  `Domain` attribute, narrowest possible scope.
- **Or an explicit `Domain=cedarpress.ai`**, which widens the cookie to the apex
  and every subdomain. It works, and it hands the cookie to any host that is
  ever added to the zone. Only worth it if the apex itself must read it. The cross-site problem then applies only where it
genuinely must — a reader crossing to the *platform* at `lumecon.ai` — rather
than to every call the Press client makes.

Two blockers from that document survive and are unaffected: the platform sets
`cross-origin-resource-policy: same-origin` on every response, which breaks a
direct download link from another origin; and the platform SPA's
`connect-src 'self'` would need the press API added if a call ever goes that way.

## 3. What is already provisioned that the dataset work can reuse

teim-app carries a document-upload path on S3 — `@aws-sdk/client-s3` and
`s3-request-presigner`, with `DOCUMENTS_BUCKET_NAME`, `DOCUMENTS_S3_KMS_KEY_ID`
and `DOCUMENTS_S3_SSE_ALGORITHM` in its deployment environment, and presigned
URLs so the engine never holds bucket credentials. If the collection
upload/download infrastructure wants a pattern, that one is deployed,
KMS-encrypted and reviewed. Worth reading before designing a second.

## 4. The database seam is already open

Not an AWS item, and the thing most likely to be misjudged from the outside.
Cedar Press does **not** need a database of its own: `server/cedar_press/db.py`
reads `DATABASE_URL`, *the same variable name teim-app reads*. Migrations
self-apply under a `pg_advisory_lock` and are tracked in
`cedar_press_migrations`.

Two corrections to an earlier draft of this paragraph, both of them the kind
that make a deployment look done when it is not.

**The same variable name is not the same database.** Two separately deployed
services each reading `DATABASE_URL` share a store only if deployment points
both of them at the same Postgres *instance and schema*. Give the Cedar Press
API its own `DATABASE_URL` and these migrations run happily against an
independent subscriber store containing no platform users — the tables exist,
the service starts, nothing errors, and the seam this section describes is not
there. So "set `DATABASE_URL`" is not the instruction. **Point both services at
the same database and schema, and confirm it** — the cheapest check is that
`cedar_press_migrations` and teim-app's `users` are visible from one connection.

**Deployment order does matter, in one direction.** The foreign key to
`public.users` is declared conditionally, which is right — Cedar Press does not
own that table:

```sql
-- 001_cedar_press_subscribers.sql
IF to_regclass('public.users') IS NOT NULL AND NOT EXISTS (
  SELECT 1 FROM pg_constraint WHERE conname = 'cedar_press_subscribers_user_fk'
) THEN ... ADD CONSTRAINT ... REFERENCES users(id) ON DELETE SET NULL;
```

But `db.migrate()` records `001_cedar_press_subscribers.sql` in
`cedar_press_migrations` whether or not the constraint was created, and then
skips **every filename already recorded**, forever. So in the order where Cedar
Press initialises the shared database first:

1. `users` is absent, the `IF` is false, the constraint is skipped;
2. `001` is recorded as applied;
3. teim-app starts later and creates `users`;
4. `001` never runs again, and `cedar_press_subscribers_user_fk` **never
   exists**.

The account links then carry no referential integrity and no `ON DELETE SET
NULL` — deleting a platform user silently leaves a subscriber row pointing at a
`user_id` that is gone. Nothing reports this; the only symptom is an absent
constraint nobody thought to look for.

Two remedies, and the choice is real. Either **bring teim-app up first** so
`users` exists when `001` runs — operationally simple, and a standing
dependency somebody will eventually forget — or add a **later migration** that
re-attempts the constraint, which runs because its own filename has not been
recorded yet, and is idempotent because the `NOT EXISTS` guard is already there.
The second is the durable one. **This is a code change in this repository, not
a deployment step, and it is not in this pull request** — it is recorded here
so that whoever does the deployment knows the constraint may be missing and how
to check:

```sql
SELECT conname FROM pg_constraint WHERE conname = 'cedar_press_subscribers_user_fk';
```

So "get the site on the database" is two independent switches, not one:

- **the server** — set `DATABASE_URL`; the subscriber tables create themselves.
- **the client** — set `vars.VITE_API_URL` in `deploy.yml`. Unset is standalone
  (bundled catalog, demo gate as sign-in); set makes the deployment connected
  and the demo gate turns *itself* off, because every module discriminates on
  `isConnected()`. A settings change, deliberately, not a code change.

What is still missing before the client switch is useful: a host for the
subscriber API (§2), and the error envelope — this client reads
`{code, message}` while the platform returns `{error}` everywhere, so platform
press routes added as-is would turn every worded refusal into
"Request failed (400)".

## 5. Four quiet failures, collected

Grouped because they share a shape: each looks like success from outside.

1. `EMAIL_DELIVERY` unset — mail never attempted, request returns 200.
2. `ses:SendEmail` missing from the task role — send throws, is caught, 200.
3. `VITE_API_URL` unset in a deployment meant to be connected — a working site
   serving its bundled catalog and the demo gate, rather than an error.
4. The S3 publish step failing — merges change `main` without changing the site,
   and the Pages job publishes the same artifact where nobody reaches it.
   HOSTNAMES.md documents this one and its live cause.

Each deserves one explicit post-deploy check rather than an assumption.
