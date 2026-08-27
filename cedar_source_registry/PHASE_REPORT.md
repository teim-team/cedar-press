# Phase report — Phases 0–1 (Wave 5.1), 2026-08-27

## Environment constraint that shaped everything

This pass ran in a build environment whose network egress policy blocks ALL
outbound page fetches (HTTPS CONNECT rejected at the proxy; the fetch tool
returns EGRESS_BLOCKED for every external domain). The only working evidence
channel was web search (Anthropic-routed), which returns titles, URLs and
snippets — never page content. Everything below is graded against that limit,
and nothing was presented as page-inspected when it was not.

Consequence for evidence semantics: `last_checked: 2026-08-27` now covers two
different evidence grades — 51 rows page-inspected in wave 5 proper, 97 rows
search-only from wave 5.1. The distinguishers are (a) the dated
"search-only re-check" sentence in each wave-5.1 row's caveats and (b)
`channel: web_search_only` on every wave-5.1 verification_log line.

## What was done

### Setup
- Unpacked `cedar_source_registry_wave5.zip` into `cedar_source_registry/` as
  the working tree; the xlsx remains the wave-5 human-facing artifact, but
  edits from this branch forward live in these files.
- Added `tools/build_summary.py` (summary.json counts computed, never
  transcribed), `tools/check_integrity.py` (JSONL parse, join-key resolution,
  computed-summary equality, schema validation of templates, nation-crosswalk
  consistency, verification-log append-only vs git HEAD). Both pass on every
  commit in this range.

### Phase 0 — nation crosswalk stub
- `nations.jsonl`: 109 rows — every nation the registry references, keyed
  `bia:<slug>`; six MCT component bands keyed
  `bia:minnesota-chippewa-tribe--<band>` with `parent_nation_id`; two
  referenced non-BIA nations under `nonbia:` (Patawomeck: state-recognized;
  Chappaquiddick Wampanoag: unrecognized).
- Every `sources.jsonl` row gained `nation_ids[]` and `nation_scope`
  (110 single_nation / 2 multi_nation / 29 regional / 7 national). Wind River
  (TBD-097 → two nations) and SPIPA (TBD-142 → five) landed as the canonical
  multi-mapping cases. ANC sources map to `[]` + regional: ANCSA corporations
  are not nations. `nation_ids` on a source row is scope, never an ownership
  assertion.
- **Deliberately not done:** the full 575-entity BIA-list import
  (list unfetchable — see needs-human). `bia_name` values are transcribed from
  model knowledge of the list and flagged `name_verified_against_list: false`
  on every row; verify-and-diff against the fetched list is a standing TODO
  before Phase 4 promotes the crosswalk to governed form.
- No verification-log entries were written for Phase 0 (it alters no source
  evidence).

### Phase 1 — verification sweep (search-only)
- All 97 sources with `last_checked: 2026-08-26` were re-checked via web
  search by nine parallel research agents under strict rules: evidence URLs
  must literally appear in results, no invented dates, honest `not_found`
  preferred over optimistic classification. Landed as four commits
  (24 / 22 / 19 / 32 sources).
- **No status_group changed.** Upgrades require page-level evidence this
  environment cannot produce; no downgrade was warranted (a missing search
  trace is a flag, not a death certificate). Statuses therefore stand as
  wave-5 left them, now with 97 fresh evidence trails.
- **No directory_url changed.** Wave 5's own experience (two same-day URL
  edits reverted after inspection showed redirects) says search-suggested
  moves are applied only after page inspection. Candidate URLs are logged.
- Outcome distribution across the 97: 16 corroborated_current,
  73 corroborated_exists, 2 moved-candidates (TBD-040 Oneida vendor list →
  /resources/dpw/ path; TBD-071 WNACC — registered wnacc.org shows no trace
  of the chamber, which appears at wanacc.org: likely a registry typo),
  5 not_found (TBD-022, TBD-025, TBD-027, TBD-028, TBD-029), 1 unresolved
  (TBD-020); every one has a log line with evidence URLs.
- Notable currency evidence (dated 2025–2026 artifacts in results): Nez Perce
  buynezperce Dec-2025 PDF and CIB list 11/13/25; Puyallup 2025 IP directory;
  Blackfeet TERO Catalog 2026; MHA 07/21/2025 contractor lists; Southern Ute
  2026 IOB list; Ute Indian Tribe UTERO April-2026 editions; Kiowa 2026-06
  vendor application; Pyramid Lake April-2026 TERO activity; Klamath 2025
  program activity; Minneapolis Fed NEED 2025Q1.
- Notable upgrade paths (Leads whose roster may already be public —
  fetch-verify before acting): Fort Peck **fortpecktero.org** public
  certified-contractor and Indian-owned business pages (strongest find);
  Tlingit & Haida **thbusinessresourcecenter.com** directory; Penobscot
  directory page publicly indexed; Hoopa active-business-license listing;
  Crow business-registration-database page; Calista's standalone
  **calistashareholderbiz.com**.
- Possible-stale flags (no recent artifact surfaced): Shoshone-Bannock
  (newest directory Sept 2022 — already Stale), Oneida vendor list (newest
  PDF Apr 2024), USET Tribal Enterprise Directory (2022 PDF), Tohono O'odham
  (registered July-2026 listing URL did not surface; newest found July 2023,
  though site TERO uploads continue into 2026), Standing Rock (registered
  Nov-2024 hearing notice did not surface).

### Standing guardrails serviced
- `outreach/requests.md` created: the three Stale→current one-email
  conversions (Lummi TBD-031, Coeur d'Alene TBD-044, Sisseton TBD-077) with
  cited bases, plus the 55-row partnership-lead roster generated from
  `partnership_leads.jsonl` (`tools/build_outreach.py`). Outreach is
  human-performed; this file is the queue, not the sender.

## What was excluded, and why

- **Phase 2 (deep inspection)** — not started. Every deliverable
  (presentation vs acquisition channel, robots.txt / wp-json / export
  probing, cadence evidence, `source_quote`d rules) requires fetching pages.
  Doing it from snippets would fabricate exactly the acquisition detail wave
  5 proved is invisible in search.
- **Phase 3 (expansion)** — not started; its bounded protocol begins with
  official-site searches that need fetch, and negative findings recorded
  without the full sequence would poison `negative_findings.jsonl` with
  false negatives.
- **Phases 4–5** — sequenced behind 2–3 by design; also fetch-dependent
  (ingesters, snapshots, hashing of real artifacts).
- **FIELD_CLASSIFICATION.md** — required "before Phase 5"; deferred with
  Phase 5. Nothing in this pass ingested Layer-1 records, so no publication
  boundary was crossed.
- **Full BIA list import** — blocked (egress); stub covers all referenced
  nations instead, flagged unverified.

## Needs human

1. **Network egress policy** (blocks Phases 2–5 and honest re-verification):
   the environment needs an allowlist covering the ~120 registry domains plus
   bia.gov / federalregister.gov, or this work needs to run where fetches are
   allowed. This is the single highest-leverage unblock.
2. **Outreach** (never automated): send the three priority requests in
   `outreach/requests.md` (Lummi, Coeur d'Alene, Sisseton) and work the
   partnership-lead roster; each received roster needs a human decision on
   storage terms and publication permission.
3. **BIA list count discrepancy**: the Jan-30-2026 Federal Register notice
   reports 575 entities, while BIA Tribal Leaders Directory search results
   claim "all 587 federally recognized tribes". Resolve against the primary
   sources when fetchable before the crosswalk is promoted (Phase 4).
4. **WNACC domain (TBD-071)**: registered wnacc.org appears to be a typo for
   wanacc.org (and the member directory may be login-gated). One fetch
   settles it; correcting the URL is a registry edit with a log line.
5. **Tulalip export terms**: unchanged wave-5 ask — confirm export terms and
   rate limits before production ingestion (Phase 5 gate).
6. **Tribal data governance posture for ANC spouse/operated-by records**
   remains as wave 5 stated: relationship fields must survive every pipeline;
   any pipeline that can't preserve them doesn't ship.

## Definition-of-done check for this range

- summary.json regenerated computed on every commit; integrity checks pass
  (JSONL parses, join keys resolve, schemas validate, verification_log
  append-only).
- Source-facing commits updated sources.jsonl and appended one verification
  record per source touched (97 lines, channel-marked).
- Phase 0 and tooling commits manufactured no verification-log entries.
