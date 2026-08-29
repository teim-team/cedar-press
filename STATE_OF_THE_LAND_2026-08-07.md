# State of the land — 2026-08-07

*All agents finished. Regression gate: **no regressions**, seven metrics improved.
This is what exists, what is broken, what is stale, and what to do next.*

> ## ⚠ SUPERSEDED, and TWO OF ITS "DO NOT RE-ATTEMPT" ENTRIES HAVE BEEN OVERTURNED
> *Flagged 2026-08-26. Read `START_HERE.md` first.*
>
> This file has not been touched since 2026-08-07 and predates every 2026-08-12 build. Its
> counts are dead. That much is ordinary staleness.
>
> **The section headed "WHAT IS EMPTY ON PURPOSE — do not re-attempt", described as
> "documented ceilings, not unfinished work", is the part that can cost real coverage,
> because two of its entries were wrong and one of them was our own bug:**
>
> **1. `resource_assets.csv` (0 rows), lines 51–53.** Attributed here to source limits — ND
> DMR and MT BOGC recording well *location* but never mineral *ownership*, with complete
> well indexes subscription-gated. **`docs/RESOURCE_ASSETS_BUILD_LOG.md` (2026-08-12) found
> the actual cause: a code defect.** Script 83 wrote the file outside its `do_all` branch
> and **truncated it on every partial run**. The file now holds **35 assets and 41 party
> links across 16 Native entities.** A ceiling was declared on an empty file without
> checking why it was empty.
>
> **2. Tribal Single Audits, lines 63–65.** Asserted as barred by 2 CFR 200.512(b)(2) on the
> strength of Seminole Tribe of Florida returning `is_public: false` on ten of ten filings.
> **200.512(b)(2) is an auditee opt-out, not a bar.** Measured on `api.fac.gov`: **6,780
> tribal records, 2,052 public (30.3%)**, including gaming tribes whose reporting-package
> PDFs download. The reversal is written up in `START_HERE.md`; it yielded 25 machine
> participation disclosures across 8 entities.
>
> **These are the same error twice, and it is worth naming: a property of ONE record read as
> a property of the WHOLE SYSTEM.** In the `resource_assets` case it was worse — a property
> of *our own code* read as a property of the source. A dead end recorded from a single
> observation is a hypothesis, not a ceiling. **Before trusting any other entry in that
> section, check whether it was measured on more than one object.**
>
> Full register: `docs/DOC_CONTRADICTIONS_2026-08-26.md`.

---

## 1. WHAT TO DO FIRST — five rulings, each unblocks a dataset

These are on the review page under the **Blockers** filter. Each is one decision.

| # | Ruling | Unblocks |
|---|---|---|
| 1 | **Which compact governs Oneida Indian Nation (NY)?** Our "Oneida Nation Gaming Compact" files are addressed to the **Wisconsin** tribe. | **$282.7M** of exact-derivable revenue |
| 2 | **Florida's 10% is a graduated bottom tier, not a flat rate** — confirm demotion. | Prevents a wrong revenue figure publishing |
| 3 | **35 properties Cedar calls closed are on NIGC's current map** (30 tribes). Who is right? | Single-property revenue attribution for 30 tribes |
| 4 | **Point Place Casino** — Oneida compacted property missing from our universe. Add? | Property universe completeness |
| 5 | **Louisiana: LGCB names 3 gaming tribes, we hold 4 properties.** | Roster reconciliation |

Then **120 spine name collisions** — each is one ruling that fixes a *class* of
misattribution, not a row. `Crow` [MT] vs `Crow Creek` [SD]; `Council` [AK];
`Turtle Mountain` [ND] vs Turtle Mountain College.

---

## 2. WHAT MUST BE RE-PULLED — all four blocked on one host

`api.usaspending.gov` has been **edge-blocking since 2026-08-07 18:01**. Every
one of these is queued behind it, and none should be attempted until a probe
comes back clean.

| Gap | Detail |
|---|---|
| **Prime contracts FY2023–2026** | Filter already validated (`filter_validated: true`), negative control returned 0. Died at `EdgeBlock: retries exhausted`. |
| **Subawards FY2021–2024** | **Never pulled** — four `bulk_download` jobs still owed. I wrongly said this data was on disk and killed the puller; that was my error. |
| **Subawards FY2020 contracts** | That job returned 456,412 assistance rows and **0 contract rows**. |
| **Federal funding FY2024–2026 + credit types 07/08/09** | `code/46_pull_funding_credit_types.py` written, never run. |

**Probe first, don't hammer.** An edge block lengthens with request volume.

---

## 3. WHAT IS EMPTY ON PURPOSE — do not re-attempt

These are **documented ceilings**, not unfinished work. Re-running them wastes a
session.

- **`wa_machine_transfers.csv` (0 rows).** Appendix D is a blank form; Appendix
  X2 §12.2.2 says *"The State shall have no responsibility whatsoever with
  respect to the plan."* Since 2007 WSGC receives a **count**, not documents.
  → **A Washington public-records request is the only route.**
- **`resource_assets.csv` (0 rows).** ND DMR and MT BOGC record well *location*,
  never mineral *ownership*; complete well indexes are subscription-gated.
- **Minnesota gaming payments.** Perpetual compacts, **no revenue sharing** —
  zero structured revenue terms parsed. There is no series because there are no
  payments.
- **Louisiana per-tribe figures.** LGCB prints the form annually and every cell
  reads *"Not Provided"* — tribes cannot be required to supply them.
- **Nevada / North Dakota / Kansas per-property win.** **Collected but sealed.**
  NGCB receives monthly per-property tribal win on the NGC-31 form; the compact
  requires strict confidentiality. NDCC § 54-58-02 and KLRD likewise.
- **Arizona aggregation** is statutory — § 5-601.02(H)(1).
- **Tribal Single Audits.** Seminole (EIN 59-1415030) files every year, audited
  by Deloitte; all ten FY2016–25 are `is_public: false` under 2 CFR
  200.512(b)(2) while non-tribal Florida auditees are public.
- **MSRB EMMA** blocks automated PDF access by robots.txt. **User-mediated pull
  only.**

---

## 4. NEW SOURCES WORTH GETTING, ranked

1. **990 e-file pull extended to the 601 philanthropy grantee EINs.** 491 are
   outside the nonprofit corpus entirely. The machinery exists (script 99 reads
   81 multi-GB ZIPs by HTTP range, 1.3 GB instead of 30 GB) — this is queue
   length, not new engineering. Completes the advocacy pass-through chain.
2. **North Dakota Fort Berthold severance sharing.** The largest per-tribe
   severance flow in the country, reported **monthly**. `SEVERANCE` is currently
   an empty tax type. 70 ND documents already retrieved as scaffolding.
3. **Wisconsin Legislative Fiscal Bureau, remaining editions.** Publishes
   **per-casino** device and table counts; 7 editions gave 168 rows and 22
   properties their first non-vendor figure.
4. **Arizona deep-mine.** 746 obligations, **707 state-side** — the highest
   ratio in the country — against only 463 observations held. Also runs a
   **transferable slot-rights market** like Washington's, six tribes with
   leasable rights and no casino.
5. **`budget.ny.gov`** — unreachable (ECONNRESET), *not* confirmed empty. The
   one place a Seneca-inclusive per-nation series could live. Retry from a
   different network before New York is recorded as 2019-only.
6. **NIGC roster additions** — 140 properties NIGC lists that we lack, staged in
   `review/gaming_additions_2026-08-06.csv`, waiting on rulings.

---

## 5. STALE OR BROKEN — fix before shipping

- **`codebook_master.csv` is clobbered by concurrent writes.** Three agents lost
  blocks today; one dropped another's 22-row `15_tribal_tax` set. Writers now
  restore rather than overwrite, but **the real fix is per-dataset codebook
  fragments** instead of one shared file.
- **`entity_hierarchy.csv` is stale and misleading** — 952 rows against a 1,310
  spine, and its `ultimate_parent_entity_id` is self-referential on 930 of 952.
  **Superseded by `entity_relationships.csv`.** Nothing should read it again.
- **`01_build_entity_spine.py` remains unsafe** — a rebuild drops every appended
  entity. Still unfixed.
- **`resolve_entity` containment** has now failed **ten** distinct ways. Guards
  are local; the central fix in the spec has not been built.
- **The 35 undocumented columns** flagged by the variable registry are internal
  method fields (`attribution_rule`, `class_match_basis`) that probably should
  not publish at all.
- **Script numbering collides** — `95_parse_compact_terms.py` and
  `95_wayback_az_gaming_status.py` both exist.

---

## 6. WHAT LANDED TODAY

**Infrastructure:** shared domain vocabulary (`cedar_domain.py`), ID service
(`cedar_ids.py`, all 1,310 entities resolve to a registered type), 5,943
aliases, 2,292 typed relationships, 10 harmonized views, variable registry with
**875 of 910 columns carrying a human label and hover definition**.

**Data:** California 40,164 payment rows both directions · Florida 9,756 ·
revenue bounds 13,803 · consultation 11,402 · gaming capacity 6,461 ·
hearings 2,667 · advocacy pass-through 1,620 · earmarks 1,002 · employment 769 ·
state gaming 494 · declinations 327 · WA allocations 75 · tribal tax 72.

**The number that justifies the architecture: 458 entities are corroborated by
3+ independent datasets.** No federal source can compute that — no source knows
the others exist.

**Refusals worth as much as builds:** California produced **zero** derived
revenue rows because every rate is marginal (San Manuel's `$19M / 15%` would
have shipped at $126.7M, wrong by an order of magnitude, with a correct
citation). Florida built a bound, published it in a draft, and **killed all 44
rows** when EDR's own Net Win falsified it — receipts lag obligations by a
fiscal year.

---

## 7. RECOMMENDED NEXT SESSION, in order

```
1. Rule the 5 blockers + 120 collisions          (you, on the review page)
2. Probe api.usaspending.gov; if clean, run:
     code/44_pull_contracts_transactions.py pull    FY2023-26 prime
     code/46_pull_funding_credit_types.py           credit types
     re-queue subaward FY2021-24 bulk_download
3. Extend the 990 e-file pull to 601 grantee EINs
4. North Dakota Fort Berthold severance
5. Fix codebook fragments + the central containment guard
6. Re-run 62 (gate), 87 (notes contracts), 102 (coverage), 110 (views)
```
