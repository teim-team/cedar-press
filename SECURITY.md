# Security Policy

Cedar Press is a Lumecon service. This document covers how to report a
vulnerability and what falls inside the scope of this repository, the
subscriber-facing web client served at `cedarpress.ai`.

## Reporting a vulnerability

Please report security vulnerabilities by email to **contact@lumecon.ai**
with the subject line `Security: <brief title>`. We aim to respond within 5
business days.

When reporting, please include:

- A description of the issue and where it appears (URL, page, or component).
- A clear path to reproduce.
- The potential impact you observe.
- Your name or handle if you would like attribution in the disclosure.

We follow coordinated disclosure. Please do not publicly disclose an issue
until we confirm a fix has shipped. We do not currently offer a paid bounty
and will credit researchers at our discretion.

## Scope

In scope:

- `cedarpress.ai` and the static client in this repository.
- The subscriber gate and session handling.
- Collection downloads and the citation metadata they carry.

Out of scope:

- Third-party destinations we link to (Tribal Business News, lumecon.ai).
- The Lumecon platform itself, which has its own policy and repository.
- Denial-of-service testing, social engineering, and physical attacks.
- Missing security headers without a demonstrated exploitable consequence.
- Reports generated solely by automated scanners without a working
  reproduction.
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
