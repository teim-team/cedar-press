# NHO + Intertribal Organization spine merge

*Written 2026-08-06. Script: `code/61_add_nho_intertribal_to_spine.py`.
Written incrementally as the work proceeded, so a killed run still leaves the findings.*

---

## Part 0 — what the 67 stranded rulings actually are

**This is the most important finding in the run, and it contradicts the brief.**

`code/09_import_rulings.py` reports `named owner NOT in the spine : 67`. That line is
read as "67 owners Elijah named that do not exist in the spine". Decomposed by the
*text of the ruling* rather than by the count, it is not that at all:

| Ruling text | Ledger rows | What it is |
|---|---:|---|
| `Named for a place - demote` | **42** | a grammar Elijah uses; not an owner name |
| `Not a Native entity` | 5 | exclusion grammar (script 33 parses it; script 09 does not) |
| `Not a Native entity - individually Native-owned firm` | 2 | same |
| `No - not this entity` | 2 | bare rejection |
| `NATIVE ORGANIZATION - <kind>` (3 distinct) | 3 | script-33 shape 3: Native, not entity-owned |
| `MULTI-ENTITY CONSORTIUM - not attributable to one tribe` | 1 | script-33 shape 4 |
| `UNRESOLVED - needs research` | 1 | held |
| `Tribally controlled / Native-controlled - reinstate` | 1 | reinstatement grammar |
| `Native Village of Eyak` | 1 | **resolver ambiguity**, not a spine gap (`ambiguous_core:2`) |
| `Tyonek Native Corporation` | 1 | **resolver ambiguity**, not a spine gap (`ambiguous_core:2`) |
| **NHO / NHO-parent names genuinely absent from the spine** | **8** | the actual gap this task closes |
| | **67** | |

So **57 of the 67 are a ruling-grammar defect in script 09, not a spine gap**, and 2
more are resolver ambiguity against entities that *are* already in the spine. Only
**8 ledger rows** name an owner that is genuinely missing, and every one is a Native
Hawaiian Organisation:

```
NX91ENNCLVJ7  Ho'omaka Foundation
XPWJDYCDV6B8  Ho'omaka Foundation
N3GDEB78RNF8  NA 'OIWI KANE
NMNLQN6T66Z5  NATIVE HAWAIIAN ORGANIZATION CHARITY
TGGAL8H2TRQ4  ISLAND EMPIRE COMMUNITY DEVELOPMENT
EMNDBXF7JSK9  ALAKA`I SERVICES GROUP INC.        <- refused, see below
YVUEAX94D183  Hoilina Ranch LLC                  <- refused, see below
(1 more)      THE MAKUA GROUP
```

**Consequence for the measure of this task.** The honest ceiling for "stranded
rulings that a spine merge can rescue" is **6**, not 67 — because two of the eight
name things that are provably not NHOs and must stay out (below), and the other 59
need a fix in script 09's ruling grammar, not more entities.

Script 09 has no equivalent of script 33's `NOT_NATIVE_RE` / `ORG_RE` / `MULTI_RE`
detectors. It treats every ruling that is not `scope artifact - keep ...` or
`exclusion applies ...` as an owner name. That is why `Named for a place - demote` is
being fed to a spine resolver 42 times. **Fixing that grammar is worth more than
anything in this merge and is left as a named next action** — it was not done here
because the brief scoped this run to the spine and changing ruling semantics
mid-merge would confound the before/after count.

---

## Part 1 — what was added

`code/61_add_nho_intertribal_to_spine.py`. Spine **866 → 952 entities (+86)**.
Backup written alongside as `cedar_entity_spine.csv.bak_2026-08-06_pre61`,
following `code/52_add_village_corporations.py`.

| Layer | `entity_class` | Prefix | Added | Source register |
|---|---|---|---:|---|
| Native Hawaiian Organizations | `Native Hawaiian Organization` | `NHO-` | **31** | `data/clean/nho_register.csv` (33 contracting rows) |
| Intertribal organizations | `Intertribal Organization` | `ITO-` | **55** | `data/clean/intertribal_orgs.csv` (57 rows) |

Every added row carries `cedar_entity_id` = the register's `proposed_id`, its
`aliases` from the register, `n_ein = 1` where an EIN is on file, and nothing
else invented. Every one is backed by a retrieved `evidence_url`; every NHO
additionally by a verbatim `evidence_quote`, because for an NHO the class claim
*is* the contested fact.

New files:

| File | What |
|---|---|
| `data/clean/nho_ito_spine_crosswalk.csv` | 88 rows: `proposed_id` → `tribe_id`. **This is the join key for `intertribal_memberships.csv` (989 rows).** |
| `data/clean/nho_ownership_changes.csv` | 9 rows — Alaka'ina → BSNC, June 2026 |
| `review/nho_ito_refused_2026-08-06.csv` | every refusal with its reason |
| `review/nho_ledger_id_conflations_2026-08-06.csv` | the `NHO-MANUKAI-00` defect |
| `logs/61_add_nho_intertribal.log` | full run transcript |

### Members, not owners

The spine schema has **no `parent_native_entity` column at all**, so the rule
that intertribal organizations must never carry one is satisfied structurally
rather than by discipline. The membership relation stays where it belongs, in
`data/clean/intertribal_memberships.csv`, joined through the crosswalk.

### Orthography

`norm()` is **imported** from `code/33_apply_party_rulings.py`, not copied — for
the reason script 09 gives in its own docstring: there must be one normaliser or
the copies drift. It folds diacritics through NFKD *before* stripping
non-alphanumerics, so the ʻokina and the kahakō fold together. That is what
matched `NA 'OIWI KANE` (ruling), `Na 'Oiwi Kane` (register) and `Nā ʻŌiwi Kāne`
(the organisation's own rendering) to one entity. A fold that handled only the
ʻokina is what cost 8 organisations their EINs (`Hui o Kuapā` vs the IRS `Hui O
Kuapa`).

---

## Part 2 — what was refused, and why

### Refused on the evidence (4)

| Name | Why |
|---|---|
| **`Hoilina Ranch LLC`** | 13 C.F.R. 124.110 requires an NHO to be a **non-profit**. An LLC cannot be one. Described in the wild as "Native Hawaiian organization-**owned**", which names it a *subsidiary*; its actual NHO parent is unidentified. Review item **NHOIT-002**. Its ruling (`YVUEAX94D183`, $0.399M) therefore stays at tier X. |
| **`Alaka'i Services Group Inc.` (ASGI)** | A **subsidiary** of `Alaka'i Foundation, Inc.`, which is the NHOA member in all 9 captures 2022-05-28…2024-04-14; ASGI's own site claims no NHO status. The **parent is added** as `NHO-ALAKA1-00` (N-0018). Review item **NHOIT-001**. Ruling `EMNDBXF7JSK9` ($1.184M) stays at tier X until Elijah re-points it at the Foundation. |
| **`Kalaimoku Foundation`** (N-0033, tier C) | The only evidence located is a **consulting vendor's case study**. Neither the Foundation nor kalaimoku.com states the relationship; kalaimoku.com says only "Native Hawaiian-Owned" and "8(a) Certified since 2011". **8(a) is not evidence of NHO status** — it admits individually-disadvantaged owners too, which is what HALOA Construction proved. Review item **NHOIT-004**. |
| **`Ho'opale Foundation`** (N-0032, tier C) | Its own site says "a Native Hawaiian organization" in **lower case** — a descriptor, not the 13 C.F.R. 124.110 term of art. The Ho'opale → Nexus Consulting Group → Pacific Ridge chain is uncorroborated by any retrieved source. Review item **NHOIT-003**. |

`ALAKA'I FOUNDATION, INC.` must **never** be merged with `ALAKA'INA
FOUNDATION`. Two different organisations whose names differ by two letters, and
both are in the spine (`NHO-ALAKA1-00`, `NHO-ALAKAI-00`).

### Not added, by design (185)

The **185 DOI Office of Native Hawaiian Relations roster rows**. The ONHR list
is an **NHPA consultation notification list, not a contracting registry**.
Putting them in the spine would make 185 unverified organisations roll-up
targets for money. They remain a tier-C discovery pool in `nho_register.csv`.

### Already in the spine (2) — not a refusal, a correction

Two intertribal organizations were **already spine entities under the NEID
backbone** and were not re-minted:

| Register | Existing spine row |
|---|---|
| I-037 Association of Village Council Presidents | `SGVF-ASVCPR-00`, *Federal-level self-governance consortium* |
| I-038 Tanana Chiefs Conference | `SGVF-TNNACH-00`, *Tanana Chiefs Conference, **Incorporated*** |

TCC was caught only by the core-set guard, not by exact name — the spine stores
the `, Incorporated` long form. Both are mapped in the crosswalk with status
`ALREADY_IN_SPINE`, so the 989 membership rows still join. **The Alaska regional
self-governance consortia are intertribal organisations wearing a different
class label**; whether `SGVF` and `ITO-` should be one class is Elijah's call,
not a merge-time decision.

### Added with an open question (kept visible, not hidden)

- **`Native Hawaiian Organization Charity`** (`NHO-HWNRGN-00`, N-0031, tier B).
  Added because Elijah ruled four Lawelawe firms to it and the organisation
  provably exists (IRS EO BMF 501(c)(3), EIN 20-2482627). But it **never states
  its own NHO status**, its subsidiaries describe it as "partnered with…
  numerous Native Hawaiian Organizations" — a partner *of* NHOs — and it is
  absent from all 10 NHOA captures. Review item **NHOIT-005 stays open.**
- **`Hui O Hana Pono`** (N-0019) — NHOA member 2022-05 to 2023-06, then absent.
  Status after mid-2023 unknown. **NHOIT-006.**
- **`Kina'ole Foundation`** (N-0021) — NHOA lists the Foundation; kinaole.com
  applies NHO status to "Kina'ole Family of Companies". **NHOIT-007.**

---

## Part 3 — the ownership change is dated, not decided

> "Certified in 2004 as a Native Hawaiian Organization (NHO), the Alaka'ina
> Foundation entered federal contracting in 2005 and established nine (9) for
> profit firms that were **wholly acquired in June 2026 by BSNC**."
> — http://beringalakaina.com/ (retrieved 2026-08-05)

`data/clean/nho_ownership_changes.csv` carries one row per firm (9), naming
Bering Straits Native Corporation (`ANRC-BERSTR-00`, an ANC) as acquirer and
the Alaka'ina Foundation as seller, at `effective_month = 2026-06` with
`effective_date` **empty** and `date_usable_for_attribution = 0` — the source
gives a month and no day, and no day is invented.

The **Foundation itself remains an NHO** and stays classed as one
(`NHO-ALAKAI-00`). Only the nine firms changed hands. Since FPDS does not update
retroactively, awards before 2026-06 stay NHO-attributed and awards after are
ANC-attributed; that is the whole reason the date is recorded rather than an
owner picked.

Written to **its own file**, deliberately not merged into
`data/clean/ownership_events.csv`, which is a derived output of
`code/31_build_dataset5_linked.py` and must be rebuilt rather than hand-edited
(it still contains the withdrawn `ND-2026-077`).

---

## Part 4 — the measured result

### Stranded rulings (`code/09_import_rulings.py`, re-run after the merge)

| | Before | After |
|---|---:|---:|
| `named owner NOT in the spine` | 67 | **61** |
| `RE-ATTRIBUTED to the owner Elijah named` | 71 | **77** |
| tier A links | 1,699 | **1,705** |
| tier X links | 185 | **179** |
| publishable prime dollars | $90,788M | **$90,876M** |

**6 stranded rulings landed** — the full ceiling identified in Part 0, since the
other two NHO names are the two the evidence forbids adding:

| UEI | Firm | Now attributed to |
|---|---|---|
| `N3GDEB78RNF8` | Galapagos Federal Systems LLC | Na 'Oiwi Kane — $45.420M |
| `NMNLQN6T66Z5` | Lawelawe Technology Services, Inc | Native Hawaiian Organization Charity — $35.301M |
| `NX91ENNCLVJ7` | Kaula Ae LLC | Ho'omaka Foundation — $3.412M |
| `XPWJDYCDV6B8` | Kako'o Services LLC | Ho'omaka Foundation — $2.566M |
| `TGGAL8H2TRQ4` | Island Empire Technology Systems LLC | Island Empire Community Development — $1.466M |
| `WD3KPEA6BJK5` | TMGL, LLC | The Makua Group — $0.097M |

$88.262M moved from tier X to tier A, which is the whole $88M of the publishable
delta. **The first federal contracting dollars ever attributed to a Native
Hawaiian Organization in this project.**

### Brand propagation (`code/60_brand_family_propagation.py`)

**No new brands were learned. 89 before, 89 after — zero new, zero changed, zero
new proposals.** Measured as a clean A/B: the spine was rolled back to
`.bak_2026-08-06_pre61`, scripts 09 and 60 re-run, the registry captured, then
the merge restored and both re-run. (The first comparison attempted was against
a contaminated baseline — a registry already written *after* the merge — and was
discarded.)

This is the `MIN_FIRMS = 2` guard behaving correctly, not a failure. A brand
needs **two or more settled firms sharing a leading token and resolving to the
same entity**. The six new NHO attributions give five entities one firm each,
and Ho'omaka's two firms lead with different tokens (`Kaula` / `Kako'o`).
`lawelawe` is a genuine brand — Native Hawaiian Organization Charity's
subsidiaries are all `Lawelawe <something>` — and it will be learned as soon as
a second Lawelawe firm is settled. Ruling one more Lawelawe UEI is the cheapest
brand in the queue.

### No downstream regression

`code/33_apply_party_rulings.py` run against the pre-merge and post-merge spine
with identical code produced **identical output — 0 differences across 56
settled parties.** The 86 new entities introduced no new party match, false or
otherwise.

(`data/clean/deals_party_attribution.csv` did change against the copy on disk,
from 57 rows to 56: `Copper River Family of Companies` → `Native Village of
Eyak` stopped resolving. That file was **stale relative to today's code**, not
to the spine — `resolve_entity("Native Village of Eyak", …)` returns
`ambiguous_core:2_spine_entities` against the pre-merge spine too. See the next
section.)

---

## Part 5 — defects found and NOT fixed here

Each is reported rather than quietly patched, because each changes numbers
outside this merge's remit.

1. **Script 09 has no ruling grammar.** 57 of the 67 "spine gaps" are ruling
   *shapes* — `Named for a place - demote` (42), `Not a Native entity` (7),
   `No - not this entity` (2), `NATIVE ORGANIZATION - …` (3), `MULTI-ENTITY …`
   (1), `UNRESOLVED - needs research` (1), `Tribally controlled … - reinstate`
   (1). Script 33 parses these correctly; script 09 does not, and instead sends
   each to tier X naming the phrase as a missing owner. **Porting script 33's
   `NOT_NATIVE_RE` / `ORG_RE` / `MULTI_RE` into script 09 is the highest-value
   next action in this area** — worth roughly 9× what this merge was worth.

2. **`NHO-MANUKAI-00` conflates at least 17 unrelated organisations.**
   19 links; 16 come from `need_v6_geocoded.csv`, the method quarantined at 9
   rulings against and 0 for. Under one id: Ailani Hawaiian
   Defense/Federal/Solutions/Technology, Hungry Hawaiian LLC, Hawaiian Steam
   Inc, Native Hawaiian Legal Corporation, Native Hawaiian Education
   Association, and **Council for Native Hawaiian Advancement — which is I-012
   in the intertribal register, a wholly different organisation.** All 19 are
   tier C so nothing publishable is wrong today, and the defect is contained.
   Not adopted for any register organisation, because adopting it would inherit
   the conflation. `review/nho_ledger_id_conflations_2026-08-06.csv`.

3. **`NHO-NAKUPUNA-00` was adopted, not duplicated.** The ledger already used
   the `NHO-` prefix for two ids with no spine row behind them. Rather than mint
   a second Nakupuna identity, the spine row for **Nakupuna Foundation** adopts
   the existing `NHO-NAKUPUNA-00`, on nakupuna.com's own statement that "The
   Nakupuna Companies are majority owned by the Nakupuna Foundation, a Native
   Hawaiian Organization" and that Nakupuna Solutions is one of them. Note the
   token conventions differ (ledger 7–8 characters, this script 6), so no minted
   id could collide with a legacy one by accident.

4. **Village government vs village corporation is ambiguous to the resolver.**
   `resolve_entity` returns `ambiguous_core:2_spine_entities` for both
   `Native Village of Eyak` (→ `AKNF-NVEYAK-…` *Eyak* vs `ANVC-EYAKXX-00`
   *Eyak Corporation*) and `Tyonek Native Corporation` (→ `AKNF-TYONEK-…`
   *Tyonek* vs `ANVC-TYONE1-00` *The Tyonek Native Corporation*). `core()`
   strips `native`, `village`, `corporation` as structural, so both names
   reduce to `{eyak}` / `{tyonek}` and the two legal persons script 52 was
   written to keep apart become indistinguishable **at the resolver**. Two
   rulings are stranded on this today, and it is a pre-existing defect — it
   fires identically against the pre-merge spine. The fix belongs in
   `resolve_entity`: when a ruling names `Native Village of X` prefer the
   government, when it names `X … Corporation` prefer the corporation, using the
   raw string that `core()` discards.

5. **`SGVF` vs `ITO-` is an unresolved class question.** Nine Alaska regional
   self-governance consortia sit in the spine as
   `Federal-level self-governance consortium`; two of them (AVCP, TCC) are also
   rows in the intertribal register. They are the same kind of thing as an
   `ITO-`. Left alone deliberately — reclassifying NEID-backbone rows is not a
   merge-time decision.

---

## Files this run did not touch

`review/cedar_review*.html`, `code/00_run_all.py`, `entity_master.csv`,
`data/clean/nho_parents.csv`, `data/clean/ownership_events.csv`,
`data/spine/cedar_exclusion_rulings.csv`. No remote host was contacted; every
input was already local, per `docs/PULL_DISCIPLINE.md`.
