# API Keys — Cedar Press

**Keys are not stored here.** The single master file is
`Desktop/dissertation/docs/API_KEYS.md`, and that file's own sync rule says every
other project references it rather than copying it. A key duplicated into two
files is a key that gets rotated in one of them.

This page records only which keys Cedar Press *needs*, and what breaks without
each one — so an agent picking up a failing pull can tell a dead key apart from
a dead source.

*Last verified: 2026-08-26.*

---

## What Cedar Press uses

| Service | Variable | Needed for | Status 2026-08-05 |
|---|---|---|---|
| Lobbying Disclosure Act | `LDA_API_KEY` | Dataset 4 — lobbying filings | Working, verified |
| USAspending | none | Datasets 2, 2b, 3 | No key required |
| Federal Register | none | Dataset 9 | No key required |
| ProPublica Nonprofit Explorer | none | Dataset 6 | No key required, rate-limited |
| SAM.gov Entity Information | `SAM_GOV_API_KEY` | `code/67_sam_entity_harvest.py` — UEI/CAGE harvest | **LIVE** (rotated 2026-08-26; the pre-rotation key measured 401 that morning) |
| SAM.gov Contract Awards | **`SAM_API_KEY`** | **`code/141_pull_sam_contract_awards.py` — the FY2000–2007 prime backfill, dataset 2** | **LIVE, verified 2026-08-26** — 6 extracts accepted. **10 requests/day**, resets 00:00 UTC |
| api.data.gov (FAC Single Audits) | hardcoded in `code/147_build_fac_single_audits.py` | `api.fac.gov` tribal Single Audits | Working, 1,000/hr |

## Notes that have cost time before

**LDA moved hosts.** `lda.senate.gov` published a `Sunset: Fri, 31 Jul 2026`
header and is now dead. The live host is `https://lda.gov/api/v1/`, and the key
is sent as `Authorization: Token <key>`. Without a key the API still returns
every field — the key only lifts throttling from 15 to 120 requests per minute.
So a 403 or 401 on LDA is a key problem; an empty result is not.

**CORRECTED 2026-08-26 — SAM.gov IS a Cedar Press dependency, and a blocking
one.** This page previously said *"SAM.gov is not a Cedar Press dependency…no
code here calls `api.sam.gov`…the rotation broke one dissertation script and
nothing in this project."* That stopped being true on 2026-08-12, when
`code/141_pull_sam_contract_awards.py` was written against
`api.sam.gov/contract-awards/v1/search`. `code/67_sam_entity_harvest.py` calls
the same host.

**The dependency is load-bearing, not incidental.** The USAspending static
archive begins at FY2008. SAM's Contract Awards API is the **only** route to
FY2000–2007 prime contracts (confirmed: `fiscalYear=2000` → 591,754 records),
and those years currently come from a BGOV export that was filtered at download
time — measured cost, **missing entities**. So "stage the data instead" has no
referent here: there is nothing to stage.

**Two env var names are in play and they are not interchangeable.**

| script | reads | host |
|---|---|---|
| `code/141_pull_sam_contract_awards.py` | **`SAM_API_KEY`** | `api.sam.gov/contract-awards/v1` |
| `code/67_sam_entity_harvest.py` | `SAM_GOV_API_KEY` (from `.env.local`) | `api.sam.gov/entity-information/v3` |

One SAM Public API Key serves both; set both variables to it.

**Status: LIVE and PERSISTED as of 2026-08-26.** A replacement key was collected
and verified working — six extract submissions accepted against
`contract-awards/v1/search`.

**It is stored in three places, none of which is a session environment:**

| location | variable |
|---|---|
| Windows **User**-scope environment variable (survives reboot) | `SAM_API_KEY` |
| `Cedar Press/.env.local` | `SAM_API_KEY` |
| `dissertation/data/tribal_federal_spending/.env.local` | `SAM_GOV_API_KEY` **and** `SAM_API_KEY` (same value) |

**The key value is not written in this file or any other doc**, per the rule
that a key duplicated into two documents is a key that gets rotated in one.

### Why the 2026-08-26 outage happened, so it does not repeat

The key that worked on 2026-08-12 **lived only in that session's environment.**
Nothing on disk held it. When the session ended it was gone, and the next agent
found only the pre-rotation key from 2026-04-27, measured it dead (HTTP 401
`API_KEY_INVALID`), and the FY2000–2007 backfill sat blocked for two weeks.
**A key that exists only in a running process is not persisted; it is borrowed.**
Any newly collected key goes to User-scope environment **and** a `.env.local`
before it is used for anything.

### Two defects in the first persistence attempt, both repaired 2026-08-26

Recorded because they are silent and would have surfaced as "the key is bad":

1. **`dissertation/.env.local` was one 92-character line.** The new
   `SAM_API_KEY=…` was appended to the existing line with **no newline**, so
   `SAM_GOV_API_KEY` parsed as *dead key + the literal text `SAM_API_KEY=` +
   live key*. `67_sam_entity_harvest.py` reading that file gets a 92-char string
   and a 401 that looks like another rotation.
2. **Both files were written UTF-8 **with a BOM**.** `67_sam_entity_harvest.py`
   matches with `line.startswith("SAM_GOV_API_KEY=")`, which a leading `﻿`
   defeats — the key reads as absent on line 1 specifically.

Both files are now BOM-free, one variable per line, backup at
`.env.local.bak_2026-08-26_pre_repair`. **`67_sam_entity_harvest.py` still reads
with a plain `startswith` and no `utf-8-sig`, so it will break again if anything
rewrites that file from PowerShell** (`Out-File`/`Set-Content` default to a BOM
here). Read env files with `encoding="utf-8-sig"`.

**If it rotates again:** log in at sam.gov directly — **do not follow the link
in the rotation email** — Workspace > Profile > Account Details > **Public API
Key**, eye icon, one-time password to email. Write it to all three locations
above; record the fact of rotation, never the value, in
`dissertation/docs/API_KEYS.md` per the sync rule.

**Format note:** this key is `SAM-` followed by a UUID, **40 characters**. The
older api.data.gov-style keys are 40 characters of plain alphanumerics. **Do not
reject a key on shape — test it.** Both shapes are 40 characters.

**The rate limit is the other half of the problem.** A non-federal user with no
SAM role gets **10 requests/day**, reset 00:00 UTC. The org role request that
lifts it to 1,000/day is **pending and not yet granted**. At 10/day the extract
mode is the only viable path (1,000,000 records per request); the paginated
subaward endpoints are not attemptable at all.

**USAspending needs no key but does need patience.** Bulk download endpoints are
POST, return a job to poll, and reach back to 2000-10-01 — further than the
search index, which starts at FY2008. A coverage floor stated by an API often
belongs to its index rather than to its data.

## When a pull starts failing

Check in this order, because the cheapest explanation is usually right:

1. **Is the host alive?** LDA's sunset is the precedent — a dead host returns
   plausible-looking errors for weeks.
2. **Is the key rotated?** SAM.gov rotates individual keys on a schedule and
   emails a warning. A rotated key returns HTTP 401 `API_KEY_INVALID`, not a
   network error.

   **Reconciled 2026-08-26 — 401 is not the only shape, and this page and
   `START_HERE.md` appeared to contradict each other on it.** `START_HERE.md`
   rule 3 and the `WHAT IT REFUSES` block of
   `code/141_pull_sam_contract_awards.py` both state that **`api.sam.gov` returns
   HTTP 404 for a bad or missing key on every path, including paths that exist.**
   That is measured and true. This page's 401 is also measured and true. Both
   are correct: **401, 403 and 404 are all key states on this host**, and 141's
   canary handler branches on all three by design. The operational rule is the
   one that matters and neither document should be read as denying it:

   > **A 404 from `api.sam.gov` is never evidence that the endpoint is wrong.**
   > Fix the key before you touch the path.
3. **Is it throttling?** HTTP 429, or a run that crawls without erroring.
4. **Only then suspect the data.** Most "the source is empty" reports here have
   turned out to be one of the three above.
