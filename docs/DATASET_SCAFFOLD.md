# How Cedar Press datasets are scaffolded

> ## ⚠ ONE STATUS ROW IS WRONG BY A FACTOR OF 56 — and it is wrong in the direction that kills a dataset
> *Banner added 2026-08-28 during doc consolidation. Source:
> `docs/DOC_CONTRADICTIONS_2026-08-26.md` item **B9**. The scaffolding pattern
> this document teaches is unchanged and still correct.*
>
> The status table reads *"Resources | 10,482 rows, **13 entities**"*.
> Measured on `data/clean/resource_revenue.csv`: **734 recipient-linked rows**,
> not 13.
>
> **Why this matters more than an ordinary stale number:** 13 entities makes the
> resources dataset look unusable, and this document is a *prioritisation*
> document. The figure would kill the dataset in any triage pass. **734 is the
> current value.**
>
> Related and in the same file: `docs/DOC_CONTRADICTIONS_2026-08-26.md` **B1**
> confirms the **1,310** spine figure this document carries at lines 14/41/98 was
> correct when written; the spine measured **1,536** on 2026-08-28.

*Written 2026-08-07. The pattern every dataset follows, and where each one
currently sits. If you are building a new dataset, this is the shape.*

---

## The observation model — the one idea that carries everything

Cedar Press does not store facts about things. It stores **dated observations
of things, each with a source and a measurement type.**

```
ENTITY (1,310)        who — resolved through the spine, stable ID
  ↓
FACILITY / ASSET      what — a physical thing: casino, well, school, clinic
  ↓
OBSERVATION           a dated measurement, with:
                        value
                        measurement_type   what KIND of number this is
                        as_of_date         when it was true
                        source_url         where it came from
                        source_quote       verbatim, or it does not exist
                        confidence + tier  how sure, and may it publish
```

**A property with 1,200 devices in 2008 and 2,480 in 2026 keeps both rows.**
Never overwrite. That is what makes expansion visible instead of inferred, and
it is why we can answer questions a directory cannot.

`measurement_type` is the field that stops the dataset lying. `AUTHORIZED_MAXIMUM`
is not `ACTIVE_FLOOR_COUNT`; `PROJECTED` is not observed. `cedar_domain.may_promote()`
refuses the dangerous transitions in code, not in a doc.

---

## The five layers, in dependency order

Each layer only depends on the ones above it. Build downward; never sideways.

**1. SPINE** — `cedar_entity_spine.csv`, 1,310 entities. The join target.
Everything resolves here or goes to review. **Never rebuilt** — appended only,
because `01_build_entity_spine.py` drops appended rows.

**2. IDENTITY** — the ledger (20,559 identifiers), aliases (5,943), typed
relationships (2,292). This is the moat. It answers "is this record about an
entity we know," and its typed edges answer "may a dollar roll up through this
relationship" — `bears_ownership()` is the single gate.

**3. SOURCE RECORDS** — raw pulls, kept verbatim under `data/raw/` with a
`_SOURCE_MANIFEST.csv` and md5s. Cedar Press is self-contained: copies of raw,
no external runtime reads. Ingestion is **idempotent** (upsert on source key +
content hash) because federal sources correct retroactively.

**4. OBSERVATIONS / EVENTS** — the dated rows above. Facts about entities and
assets over time. Multiple sources reporting one thing = one canonical record
with several claims, never several records.

**5. PRODUCTS** — the joined, published files. `gaming_properties.csv` is the
template: a physical facility joined to its legal instruments through the spine.

---

## The build sequence for any new dataset

```
1  ROSTER      pull the published universe first (FR list, AIHEC, CDFI Fund,
               BIE, IHS Title V). Everything on it exists by definition, so
               the only question is which identifier it uses. Cheapest, first.

2  STRUCTURE   expand through what we already know — FPDS ultimate_parent_uei,
               106 brand families, cross-dataset propagation. FREE. Reuse
               before researching.

3  SWEEP       broad pulls matched against the 1,310-name corpus + 5,943
               aliases. Expensive, LAST, and gated by the containment guard.

4  RULE        Elijah's decisions. Tier A. Outranks everything, including
               deterministic identifier matches. Only a new ruling reverses one.
```

Then, always:

```
staged output → diff vs prior run → HUMAN REVIEW GATE → promote
```

Nothing reaches Tier A, the published layer, or a release bundle without
review. Automated results land at B/C. Routine re-observations of already-ruled
facts may auto-promote at B.

---

## Where each dataset sits right now

| Layer | Built | Missing |
|---|---|---|
| Spine | 1,310 entities, 12 classes | 148 TDHEs have no entity |
| Identity | ledger + aliases + typed relationships | — |
| Prime contracts | FY2000–2022 | **FY2023–26** (pull edge-blocked) |
| Federal funding | FY2008–2023 | FY2024–26, credit types 07/08/09 |
| Subawards | 55,035 clean | FY2021–24 — **raw already on disk**, matching in flight |
| FAADS | 2.77M rows, 29,594 attributed | the other recipient types |
| Gaming | 774 properties, 6,027 official capacity obs | devices, digital, components |
| Compacts | 707 held | **terms never parsed** — in flight |
| Lobbying | 27,796 filings, 97% keyed | consultation, OIRA, hearings, earmarks — all in flight |
| Resources | 10,482 rows, ~~13 entities~~ **734 recipient-linked rows** *(corrected 2026-08-26 — the "13" was wrong by a factor of 56 and made the dataset look unusable; measured ceiling is 966)* | more states |
| NAGPRA | 6,729 notices, 51,338 bridge | 212 misattributions to re-key |

---

## LODES at block level — what it takes

**We already hold LODES**, but at the wrong grain:

```
4wheeler/project/raw/api/lodes_reservation_employment.csv   WAC 2005-2022
4wheeler/project/raw/api/lodes_rac_reservation.csv          RAC 2009-2022
built by tero/scripts/build_lodes_reservation_employment.py
```

Those are **reservation-aggregated**. A reservation total includes the tribal
government, the school, the clinic and every other employer — so it cannot
stand in for a casino's employment.

Block level is a re-pull, not new research:

1. **Pull raw WAC by state-year** from LEHD (`lodes8/<st>/wac/`). Block-level
   is the native grain — the reservation file was aggregated up from it.
2. **Geocode each property to its block.** `gaming_facilities.csv` carries
   `latitude`/`longitude` with a `coords_basis` column. Census Geocoder returns
   the 15-digit block GEOID.
3. **Join WAC on the block**, and keep `S000` (total jobs) plus the CNS sector
   splits — `CNS17` (accommodation & food) and `CNS18` (arts, entertainment,
   recreation) are where casino employment lands.

**The caveat that must travel with every row:** LODES block jobs are
**workplace jobs in that block**, not casino payroll. Where a block holds a
hotel, a truck stop and a tribal office, all of it is in the number. So the
measurement type is `LODES_BLOCK_WORKPLACE_JOBS` and it is never labelled
"employees." Record how many other employers share the block; a block with one
employer is a much stronger observation than one with nine.

That is also why OSHA, environmental reviews and tribal reports are kept
alongside rather than reconciled into one figure. **Multiple independent
employment observations are a feature.** Cedar may derive a preferred value; it
retains all the underlying ones.

---

## The rule that decides whether a new source is worth building

> **"Which existing records can this enrich?"** — never "can this become
> another dataset?"

No second property universe. No new IDs for things that have Cedar IDs. A
manufacturer or regulator using a different property name is an **alias**, not
a new property.

A source earns a new dataset only when it describes a **new kind of thing** —
a new node class. Facilities earned one because a casino is neither an entity
nor an event. Loyalty programs do not: they are an attribute of properties that
already exist.
