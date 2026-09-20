# Notes beside `docs/HOSTNAMES.md`: the email path, and what the `app.` alias changes

*Written 2026-09-20. **`docs/HOSTNAMES.md` is the authority on hostnames, TLS,
CloudFront, the bucket and the OIDC role, and nothing here restates it** — an
earlier draft of this file did, against a checkout cut before `bea4961`, and got
the deploy target wrong as a result. That draft's corrections are recorded in §0
rather than deleted. What follows is only what HOSTNAMES.md does not cover:
transactional email, which lives in another repository, and one consequence of
the certificate that touches the session design.*

*Detailed notes on the OIDC failure, SES and the certificate were already posted
for Kaylyn as a comment on `lumecon-website#345` by a parallel session. This file
is the repository's copy of the parts that are cedar-press's own; it is not a
second message to her and should not be reposted as one.*

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

## 1. Transactional email: the repository it helps is teim-app

**teim-app is the only repository in the estate that sends email.**
`server/mailer.js`, `@aws-sdk/client-sesv2`, two flows — verification and
password reset — with a default sender of `Cedar Impact <contact@lumecon.ai>`.

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

Note the DNS side is already prepared: HOSTNAMES.md records a `_dmarc` record in
the Route 53 zone.

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
`app.cedarpress.ai` and the client and its API are **the same site**, so a
host-only cookie on the apex is simply sent, with no bridge, no `SameSite=None`,
and no relaxation of anything. The cross-site problem then applies only where it
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
reads `DATABASE_URL`, *the same variable teim-app reads*. Migrations self-apply
under a `pg_advisory_lock`, are tracked in `cedar_press_migrations`, and the
foreign key to `public.users` is declared conditionally through `to_regclass`,
so deployment order does not matter and neither side has to wait for the other.

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
