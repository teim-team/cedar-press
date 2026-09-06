# Cedar Press and the platform: how Cedar is wired into teim-app, what the databases hold, and what a real integration needs

*Measured 2026-09-06 against the checkouts of teim-team/teim-app, teim-team/cedar and this repository. File and line references are to those trees on that day. Report only: nothing here has been built.*

## What is true today

- **teim-app is Postgres only** (node-postgres, `DATABASE_URL`), with the schema in 27 hand-written SQL migrations under `server/migrations/` and no ORM. There is **no workspaces table and no subscriptions or entitlements table**. The tier is a text column on `users` with a check constraint allowing `free`, `sprout`, `sapling` and `tree`.
- **Cedar is wired into teim-app as an outbound HTTP client only** (`server/cedar/client.js`), bearer-token authenticated, feature-flagged by `CEDAR_ENABLED` and `CEDAR_BASE_URL`. When the engine is unavailable the platform answers with a synthesized `unavailable: true` reply rather than an error.
- **The Cedar engine (`cedar`) has no notion of Cedar Press**, collections, datasets, entities or the identity register: zero hits for `cedar_uid`, `CE-0…`, `entity_class` or Cedar Press. Its database is five tables of agent sessions, messages, chat memory and document jobs. Auth is one shared bearer key. Cedar the engine and Cedar Press share a name and nothing else.
- **teim-app has no concept of Tribal Business News, access codes or a `press` or `press_pro` tier.** Those live entirely here, where accounts are an environment variable holding plaintext passwords and the ledger is an optional SQLite file.
- **The two session cookies cannot share a session today**: `teim_session` (`SameSite=Lax`, opaque random token with a server-side row) against `cedar_press_session` (`SameSite=None`, self-contained HMAC-signed JSON, no server-side record).

Nothing in teim-app or the engine serves a `/press/*` route. The FastAPI service in `server/` is the only implementation of this client's contract, which is why pointing `VITE_API_URL` at it is the whole switch from standalone to connected.

## 1. teim-app's database

**Engine.** Postgres 17 in development (`docker-compose.yml`, service `db`, host port 5433), an external instance in production (`docker-compose.prod.yml` requires `DATABASE_URL`; there is a `terraform/` directory). The engine has its own, separate Postgres; the two databases are never joined.

**Schema.** `server/migrations/*.sql`, applied in name order by a runner in `server/db.js` that records each file in `schema_migrations` and wraps initialisation in an advisory lock. Numbers 021 and 022 do not exist.

**Tables that matter to Cedar Press.**

| Table | Columns, in brief | Where |
| --- | --- | --- |
| `users` | `id`, `email`, `password_hash` (nullable since OAuth), `name`, `organization_name`, `role`, `oauth_provider`, `email_verified` and token, `workspace_tier TEXT NOT NULL DEFAULT 'sprout' CHECK IN ('free','sprout','sapling','tree')`, password-reset token, `deleted_at` | 002, 010–013, 015, 019, 023 |
| `sessions` | `id`, `user_id`, `token_hash UNIQUE`, `expires_at`, `created_at` | 002 |
| `organizations` | `id`, `name`, `slug`, `owner_id`, `is_personal`; **no tier column** | 014 |
| `organization_memberships` | `organization_id`, `user_id`, `role IN ('admin','member','viewer')` | 014 |
| `organization_invites` | by e-mail match, no token column | 016 |
| `projects`, `runs`, `project_participants`, `project_notes`, `project_drafts` | the analysis product | 001–005, 009, 014, 020, 024–027 |
| `cedar_chat_messages` | `owner_id`, `project_id NOT NULL`, `run_id` (bare uuid), `thread_id TEXT`, `role`, `content`, `context_used JSONB`; no threads table | 018 |
| `document_import_jobs`, `document_import_job_documents`, `uploaded_documents` | the import pipeline, with the engine's job ids | 005–008, 020 |

Two things to know about the tier column. Migration 013's own header says it lives on `users` because there is no workspace container yet, and lists the forward path (a `workspaces` table, a `workspace_id` on projects, then drop the column); that migration has not been written. The read projection in `server/repositories/users.js` maps a null tier to `'sprout'`, a paid tier, and there is no API route that changes a tier: no upgrade, no billing webhook, no admin endpoint. Provisioning scripts and the signup path set it.

## 2. How Cedar is wired into teim-app

- **Client.** `server/cedar/client.js` (`createCedarClient`), configured by `CEDAR_ENABLED`, `CEDAR_BASE_URL`, `CEDAR_INTERNAL_API_KEY` (or `CEDAR_API_KEY`), `CEDAR_API_PATH` (default `/api/v1/messages`), `CEDAR_DOCUMENT_API_PATH`, `CEDAR_TIMEOUT_MS` (120 s). Contract version `1.0.0`.
- **Contract.** `server/cedar/contract.schema.json` documents `chatRequest`, `chatResponse` and the document-job shapes. Nothing loads or validates against it; it is documentation. The request carries `requestId`, `threadId`, `user {id,email}`, `project {id,name,analysisYear,projectData}`, `projectContext`, `context` and `message {id,text}`. The response carries `messageId`, `threadId`, `answer`, `contextUsed`, `unavailable` and `fieldSuggestions[]`; the engine's response model has no `fieldSuggestions`, so that path is dead on the engine side.
- **Routes.** `POST /cedar/messages` (draft chat, persists nothing), `POST /projects/:id/cedar/messages` (project chat, transcript appended best-effort as one multi-row insert), `GET /projects/:id/cedar/messages`, and the document-import orchestration.
- **Unavailability.** Not configured, transport failure and document-import failure all degrade to a 200 with `unavailable: true` and the canned sentence "Cedar is unavailable right now."
- **Rate limits.** A per-process in-memory bucket, 40 chat calls a minute; with more than one replica the effective limit multiplies.
- **The tier gate is dead code.** `canUseCedarIntake` in `server/lib/tierCapabilities.js` returns `true` for every tier, so the 403 branches in the routes ("Sapling or Tree required") can never fire and their message contradicts the module. `resolveEntitlement` in `server/lib/entitlement.js` is the intended replacement; no Cedar route calls it.
- **The React client.** `src/api.js` (`sendCedarMessage`, `sendCedarDraftMessage`, `getProjectCedarMessages`), the chat in `src/components/CedarWidget.jsx`, availability read from four flags the auth payload carries (`cedarEntitled`, `cedarChatConfigured`, `cedarDocumentImportEntitled`, `cedarDocumentImportAvailable`).

## 3. The Cedar engine

FastAPI, SQLAlchemy async, Alembic, its own Postgres. Five tables: `agent_sessions`, `agent_messages` (one opaque serialized SDK item per row), `chat_memory` (rolling summary, pinned facts, workflow state), `document_jobs`, `document_job_files` (a presigned `document_url`; the engine no longer knows where a file lives). `threadId` is the engine's `session_id`. Auth is `require_internal_key`: one shared bearer key compared with `!=` rather than a constant-time comparison, and no per-user authorization at all; the engine trusts whatever `user.id` the platform sends.

## 4. Session and identity across the two

| | teim-app | cedar-press `server/` |
| --- | --- | --- |
| Cookie | `teim_session`, `HttpOnly`, `SameSite=Lax`, `Secure` in production, no `Domain`, 7 days | `cedar_press_session`, `HttpOnly`, `SameSite=None`, `Secure`, 14 days |
| Contents | 32 random bytes; only the SHA-256 is stored, in `sessions` | base64url `{email, tier}` plus an HMAC tag; no server-side record |
| Revocation | delete the row (done on soft-delete and lockout) | none short of rotating `CEDAR_PRESS_SECRET`, which logs everyone out |
| Passwords | scrypt, salted, constant-time compare, signup requires 12 characters | plaintext in `CEDAR_PRESS_ACCOUNTS`, constant-time compare, activation requires 10 |
| Tier | `users.workspace_tier`, emitted as `workspaceTier` | from the account record, emitted as `workspace_tier` |
| Tribal Business News, access codes, press tiers | none | `codes.py`, `CEDAR_PRESS_CODES`, spent set in process memory |

The casing works only by coincidence: `resolveTier` in this repository reads both spellings, but `tierCapabilities.normalizeTier` in teim-app takes a bare string and returns `'sprout'` for anything it does not recognise, which includes `press` and `press_pro`. A Cedar Press subscriber reaching a platform surface today would resolve as Sprout, a paid platform tier.

Two copies of `workspaceTier.js` exist, one per repository, sharing a filename and an exported function and disagreeing on the vocabulary (this repository knows `press` and `press_pro`; teim-app's knows `sapling` and `tree` and maps `free` to `sprout`). And `pressAccess.js` here reads `user.press` first, describing it as the server's resolution from `tierCapabilities.pressShelfReach`; no such function or field exists in teim-app, so the client falls through to its tier heuristic every time.

## 5. What a real integration needs

### The account and the tier

The account belongs in `users`; the tier in `users.workspace_tier`, which is the only place the platform resolves entitlement from. Concretely:

1. A migration widening the check constraint to admit `press`, `press_pro` and `grove`; without it an insert fails outright.
2. A `press_access_codes` table (`code`, `email`, `tier`, `expires_on`, `issued_at`, `spent_at`, `spent_by_user_id`) replacing `codes.py`'s environment variable and in-memory spent set, with activation creating the user and spending the code in one transaction. The ordering in `app.py` is already right; the transaction is missing.
3. Seats sharing one subscription: `organizations` and `organization_memberships` already model this. The organization id becomes the ledger's `account_id`, and the tier then belongs on the organization, because points accrue per subscription and not per seat. That also gives `resolveEntitlement`'s `sponsorTier` the source it lacks.
4. `hashPassword` from `server/auth.js` at activation; nothing of the plaintext comparison survives. Pick the higher minimum length (12).
5. `tierCapabilities` gains `pressShelfReach`, and the auth payload spreads `press: {canRead, shelfReach}` beside the Cedar flags, so `user.press` becomes what `pressAccess.js` already claims it is.

### The cookie across origins

`teim_session` is `Lax` with no `Domain`, and `cedarpress.ai` is a different site from the platform, so a credentialed fetch from cedarpress.ai to the platform sends no cookie at all. Three options, one recommended:

- **Same site, different subdomain** (`press.lumecon.ai` with `Domain=.lumecon.ai`): cheap, `Lax` keeps working; `cedarpress.ai` becomes a redirect and every subdomain receives the cookie.
- **`SameSite=None` on the platform cookie**: requires CSRF protection the platform does not have today (its CSRF defence is the `Lax` attribute; requests with no Origin header are allowed unconditionally). Risky, and it relaxes every route at once.
- **A bridge, no shared cookie** (recommended): the platform issues a short-lived, single-use, audience-scoped token at `GET /press/handoff` from its own page (same-site, so `Lax` works); cedarpress.ai exchanges it at `POST /auth/press-session` for its own host-only cookie backed by a `sessions` row. Two cookies, two revocation paths, no relaxation of the platform's posture.

Two further blockers either way: the platform sets `cross-origin-resource-policy: same-origin` on every response, which breaks a direct download link to `/press/collections/{id}/download` from another origin; and the platform SPA's `connect-src 'self'` would need the press API added if the call ever went the other way.

### The ledger and the profile in Postgres

Direct translations of `priorities.py`'s five SQLite tables, keeping the append-only property: `cedar_priorities` (re-seeded from `data/cedar/priorities.json` at start; points and counts never written back), `research_points_ledger` (append-only, with the partial unique index that makes the monthly credit idempotent), `priority_allocations`, `research_requests`, and `reader_profiles` keyed by `user_id` rather than e-mail. Four behaviours must survive the port or the product silently changes: `accrue`'s idempotency depends on the unique index, so the port catches the conflict or uses `ON CONFLICT DO NOTHING`; `_expire` and `allocate` are check-then-act sequences that SQLite's single lock serialised, so Postgres needs a row lock on the account or a serializable transaction (two seats spending at once can overdraw); and the unscoped `DELETE FROM priority_allocations WHERE points <= 0` becomes a table scan per write.

### The error envelope

This client reads `{code, message}`; the platform returns `{error}` everywhere. Press routes added to the Fastify server as they are would turn every worded refusal into "Request failed (400)" and lose the `PRESS_CODE_EXPIRED` wording. Either the press routes emit `{code, message}`, diverging from the rest of the platform, or the client's error reader is rewritten.

## Defects noticed on the way, by repository

- **teim-app**: the dead Cedar tier gate and its contradictory message; `normalizeTier` promoting unknown tiers to `sprout`; the null-tier fallback to `sprout` in the users repository; the stale `workspaceTier.js` (docstring, missing `free`, seat counts that disagree with the server); the per-process rate limiter.
- **cedar**: the bearer comparison is not constant-time; no per-user authorization; `fieldSuggestions` in the platform contract has no engine counterpart.
- **cedar-press**: `pressAccess.js` describes a `user.press` field the platform never sends; `CEDAR_PRESS_INSECURE_COOKIE` flips `Secure` and `SameSite` together, so the cross-site path is never exercised locally; the session cookie cannot be revoked; the access-code register and spent set live in process memory, which the module itself names as what must not reach production.
