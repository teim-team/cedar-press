# Security Policy

Cedar Press is a Lumecon research publication, partnered with Tribal Business
News. This document covers how to report a vulnerability and what falls
inside the scope of this repository, the subscriber-facing web client served
at `cedarpress.ai` and the API alongside it.

## Reporting a vulnerability

Please report security vulnerabilities to **contact@lumecon.ai** with the
subject line `Security: <brief title>`, and name the repository in the
subject. For Lumecon's current product controls and security-program status,
see <https://lumecon.ai/security>.

Include a description of the issue, a clear path to reproduce it, the
potential impact and your name or handle if you would like attribution.

We will acknowledge receipt within five business days, provide our assessment
and expected fix timeline within ten business days and credit you, if you
wish, in a public disclosure note.

Please do not disclose the issue publicly until we confirm that a fix has
shipped or 90 days have passed from your report, whichever comes first. If a
fix requires longer, we will explain why and ask to agree on an extension.

### Safe harbor

If you make a good-faith effort to follow this policy, we will treat your
research as authorized. We will not initiate or support legal action against
you. If a third party brings action concerning research conducted under this
policy, we will make it known that the work was authorized.

Good faith means:

- Stop as soon as you have demonstrated the issue.
- Do not access, modify, delete or retain data belonging to anyone else. If
  you encounter personal data, stop immediately, do not save a copy and tell
  us what you saw.
- Do not degrade the service for others through denial-of-service testing,
  high-volume automated scanning, spam or social engineering.
- Give us a reasonable opportunity to fix the issue before disclosure.

This authorization covers only systems we operate. It cannot authorize
testing against third parties, including hosting and payment providers.

### Confidential reporting

Lumecon does not currently publish a PGP key. Send a short message without
sensitive details if plaintext email is unsuitable, and we will arrange a
secure channel before you provide the report.

### Bounty and language

Lumecon does not currently offer a paid bounty program. We will credit
researchers who wish to be credited. We read and respond in English.

### Out of scope in every Lumecon repository

- Denial-of-service testing and brute-force attacks.
- Social engineering.
- Reports about a missing security header without an exploitable consequence.
- Reports generated solely by automated scanners without a working
  reproduction.

## Scope

In scope:

- `cedarpress.ai` and the static client in this repository.
- The API in `server/`.
- The subscriber gate and session handling.
- Collection downloads and the citation metadata they carry.

Out of scope:

- Third-party destinations we link to, including Tribal Business News, the
  partner that handles Cedar Press subscriber plans.
- The sibling Lumecon repositories, each separate scope with its own policy
  (*as of 2026-09-23*):
  - `teim-app`, the Lumecon platform (Cedar Impact, Cedar Commons and Cedar
    Grove): <https://github.com/teim-team/teim-app/blob/main/SECURITY.md>.
  - `cedar`, Cedar, Lumecon's AI economic analyst:
    <https://github.com/teim-team/cedar/blob/develop/SECURITY.md> (`develop`
    is that repository's default branch).
  - `teim-engine`, the internal model engine:
    <https://github.com/teim-team/teim-engine/blob/main/SECURITY.md>. That
    file is not on `main` yet; it lands with
    [teim-engine #20](https://github.com/teim-team/teim-engine/pull/20).
  - `lumecon-website`, the public site `lumecon.ai`, which holds Lumecon's
    canonical policy:
    <https://github.com/teim-team/lumecon-website/blob/main/SECURITY.md>.
  - [`Lumecon-data`](https://github.com/teim-team/Lumecon-data), the shared
    data foundation. It has no root `SECURITY.md` on `main` yet.

  Reports for any of them still reach contact@lumecon.ai; naming the
  repository in the subject line routes it faster.
- Everything under *Out of scope in every Lumecon repository* above, and
  physical attacks.
- **The standalone sign-in.** A build with no API configured checks its
  password in the browser, against a salted digest that ships in the bundle.
  That it can be bypassed from devtools is its documented character, not a
  finding: it is a demonstration gate, it guards nothing confidential (see
  below), and it is off entirely on a connected deployment. A collection or
  record reachable through it that should not be public **is** in scope, and
  we want to hear about it.

## Posture

- **No third-party runtime.** Brand fonts are self-hosted and the build ships
  no analytics, tag managers or external scripts, so a page load makes no
  request off-origin.
- **No secrets in the bundle.** The client holds no keys. Every build-time
  value it carries is one that is safe to read: `VITE_APP_URL` and
  `VITE_API_URL` are public origins, the Datadog client token is a
  write-only ingest token, and `VITE_PRESS_DEMO_ACCOUNTS` is an email and a
  salted SHA-256 digest, never a password. Until September 2026 this was not
  true — two preview accounts were committed with their passwords in
  plaintext and every build shipped them. They are gone; a standalone
  deployment now takes its account from build-time configuration and, given
  none, signs nobody in.
- **A standalone build guards nothing confidential.** It carries the catalog,
  the methods, the release history and ten sampled rows per table. The
  collections themselves reach a reader only from the API, behind a session.
- **Outbound links.** Every external link carries `rel="noreferrer"`.
- **Storage.** Browser storage holds session and preference state only, and
  every access is guarded so a storage-denying policy degrades rather than
  breaks the page.
- **Entitlements.** The client decides what renders; a subscriber's
  entitlement is authoritative on the server, and the two are expected to
  answer identically. Access-control findings should be reported against the
  server-side answer.

## Data

Collections published through Cedar Press are built from public records and
Lumecon's own research. Cedar Press does not collect analytics or behavioral
data from readers. Correspondence sent to `contact@lumecon.ai` is handled by
the Lumecon team.
