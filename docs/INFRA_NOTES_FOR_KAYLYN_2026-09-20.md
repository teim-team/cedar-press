# Infrastructure notes: what the AWS work touches, and the two places it can go quiet

*Written 2026-09-20 for Kaylyn, after SES production access and the Cedar Press
certificate. Measured against the checkouts of teim-team/cedar-press and
teim-team/teim-app on that day; file and line references are to those trees.
Nothing here has been changed — these are findings, not a change request.*

## 1. SES production access: the repo it helps is teim-app, not this one

**teim-app is the only repository that sends email.** `server/mailer.js`, using
`@aws-sdk/client-sesv2`, for two flows: e-mail verification and password reset.
The default sender is `Cedar Impact <contact@lumecon.ai>`.

**cedar-press sends no email at all.** There is no SES client, no SMTP, no
mailer module — a grep across `server/`, `src/` and `scripts/` returns nothing.
So Cedar Press activation and access codes cannot send anything today, and
leaving the sandbox does not change that. When Cedar Press needs to send, it
either gains its own path or routes through the platform API, which is a
decision, not a configuration.

**The thing worth knowing before you flip it on.** Delivery is off unless
`EMAIL_DELIVERY=ses` exactly (trimmed, lowercased), and when it is unset the
mailer **builds the link and silently does nothing**. That is deliberate — it
keeps dev and tests from sending — but it means a half-configured production
deployment looks identical to a working one from the outside: the signup
succeeds, the user waits for an email that was never attempted, and the only
trace is an info-level log line. Four settings have to move together:

| variable | what happens if it is missing |
| --- | --- |
| `EMAIL_DELIVERY=ses` | nothing is ever sent; no error |
| `EMAIL_VERIFICATION_BASE_URL` | verification mail is skipped, logged as `not_configured` |
| `PASSWORD_RESET_BASE_URL` | reset mail is skipped, same way |
| `EMAIL_FROM` | falls back to `Cedar Impact <contact@lumecon.ai>` |
| `SES_REGION` or `AWS_REGION` | defaults to `us-east-1`, which may not be where the identity is verified |

Plus two things outside the repo: the sender address must be a verified SES
identity, and the task role needs `ses:SendEmail`. If the role is missing the
permission the send throws and is caught — logged as `send_failed`, returned as
a failure, and the request still succeeds. So permission errors are also quiet.

Worth one smoke send to a real inbox after provisioning rather than trusting a
green deploy, because every failure mode above is a 200.

## 2. The certificate, and the one thing it commits us to

**Where Cedar Press actually deploys today: GitHub Pages.**
`.github/workflows/deploy.yml` builds and publishes with
`actions/upload-pages-artifact` / `actions/deploy-pages`. Pages terminates TLS
itself and issues its own certificate for a custom domain, so an ACM
certificate does not attach to what is currently deployed. That is not a
problem — it just means the certificate is for something else, and it is worth
being explicit about which:

- **a move to CloudFront/S3**, in which case the certificate is step one and
  must be in `us-east-1` for CloudFront to accept it;
- **an API hostname** (`api.cedarpress.ai` or similar) in front of the FastAPI
  service in `server/`;
- **an SES domain identity**, which it is *not* — SES verifies a domain with
  DKIM CNAME records and a TXT, not with an ACM certificate.

**The part that is a real decision, not a detail.** The site's own identity is
`cedarpress.ai` — `src/features/grove/useDocumentTitle.js` sets
`SITE_ORIGIN = "https://cedarpress.ai"`, `vite.config.js` builds for the domain
root, and `CEDAR_PRESS_ORIGINS` defaults to
`http://localhost:5173,https://cedarpress.ai`. Meanwhile the client points at
`https://api.lumecon.ai` and the app at `https://lumecon.ai`.

`cedarpress.ai` and `lumecon.ai` are **different sites**, not different
subdomains. `docs/PLATFORM_INTEGRATION_2026-09-06.md` measured what that costs:
the platform's `teim_session` cookie is `SameSite=Lax` with no `Domain`, so a
credentialed fetch from `cedarpress.ai` to the platform sends **no cookie at
all**. That document laid out three options and recommended one:

1. `press.lumecon.ai` with `Domain=.lumecon.ai` — cheapest, `Lax` keeps working,
   `cedarpress.ai` becomes a redirect;
2. `SameSite=None` on the platform cookie — relaxes every route at once and
   needs CSRF protection the platform does not have;
3. **a handoff bridge** — the platform issues a short-lived, single-use,
   audience-scoped token from its own page, which `cedarpress.ai` exchanges for
   its own host-only cookie. Two cookies, two revocation paths, no relaxation.
   This was the recommendation.

A certificate for `cedarpress.ai` is consistent with keeping the brand domain,
which is a reasonable call — Cedar Press reaches readers through Tribal Business
News and the name is the product. It just means option 1 is off the table and
the bridge is on the critical path rather than a later nicety. Worth saying out
loud so it is a choice rather than a consequence.

**Two smaller blockers from the same document, both still true.** The platform
sets `cross-origin-resource-policy: same-origin` on every response, which breaks
a direct download link to a press collection from another origin; and the
platform SPA's `connect-src 'self'` would need the press API added if a call
ever goes the other way.

## 3. What is already provisioned that the dataset work can reuse

teim-app already carries an S3 path for document upload — `@aws-sdk/client-s3`
and `s3-request-presigner`, with `DOCUMENTS_BUCKET_NAME`,
`DOCUMENTS_S3_KMS_KEY_ID` and `DOCUMENTS_S3_SSE_ALGORITHM` in its deployment
environment, and presigned URLs so the engine never needs bucket credentials.
If the collection upload/download infrastructure wants a pattern, that one is
already deployed, already KMS-encrypted, and already reviewed. Worth looking at
before designing a second one.

## 4. Connecting the site to the database is genuinely one setting

Not an AWS item, but it is the thing most likely to be asked for next and it is
smaller than it sounds. `deploy.yml` reads one repository variable,
`vars.VITE_API_URL`. Unset is standalone: the client serves its bundled catalog
and the demo gate is the sign-in. Set it to the platform API and the deployment
is connected — real sessions, signed HTTP-only cookies, activation — and the
demo gate turns itself off, because every module discriminates on
`isConnected()`. A settings change, deliberately, not a code change.

What has to be true on the other side first: the press routes have to exist on
the platform (nothing in teim-app or the engine serves a `/press/*` route
today), the cookie question in §2 has to be answered, and the error envelope has
to be reconciled — this client reads `{code, message}` and the platform returns
`{error}` everywhere, so press routes added as-is would turn every worded
refusal into "Request failed (400)".

## 5. Four things that are quiet failures, collected

Named together because they share a shape, and because each one looks like
success from the outside:

1. `EMAIL_DELIVERY` unset — mail is never attempted, request returns 200.
2. `ses:SendEmail` missing from the task role — send throws, is caught, request
   returns 200.
3. A cross-site credentialed fetch from `cedarpress.ai` — the browser sends no
   cookie, so it presents as "signed out", not as a misconfiguration.
4. `VITE_API_URL` unset in a deployment meant to be connected — the site serves
   its bundled catalog and the demo gate, which is a working site showing stale
   data rather than an error.

Each is worth one explicit post-deploy check rather than an assumption.
