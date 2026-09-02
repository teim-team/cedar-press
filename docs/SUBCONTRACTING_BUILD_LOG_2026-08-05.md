# Dataset 2b — Subcontracting — Build Log

*Built 2026-08-05. Script: `code/20_build_subcontracts.py`. Run log: `logs/20_subcontracts_2026-08-05.log`.*

> ## ⚠ SUPERSEDED ON ITS CENTRAL CLAIM. Flagged 2026-08-26.
>
> **This is the file named after the dataset, so it is the one people open — and its
> headline finding was overturned within 24 hours of being written.**
>
> Line 118 still reads *"`data/clean/subawards.csv` | **998** | One row per subaward.
> `direction` = `unknown` on all 998, by design."* Both halves are dead:
>
> | | this log | now |
> |---|---:|---:|
> | `data/clean/subawards.csv` | 998 | **63,548** |
> | `direction` | `unknown` on all rows | **separates two populations** — (a) Native as prime 18,696 · (b) Native as subawardee 22,096 · both sides 909 |
>
> **The "NET-NEW identifiers = 0" headline is true of its source and false about the
> ceiling.** `subcontract-05-09-23-22-23-37.csv` really was mined out — every one of its 304
> UEIs was already known. But it was a **HigherGov query result with an unpreserved sampling
> frame**, not a sample of the subaward universe. Going to the primary source with no
> recipient filter returned a different population entirely: **only 19 of the 998 rows recur
> in the primary-source pull** (`docs/datasets/02b_subcontracting.md:20`). Net-new UEIs
> against the 2023 file are **251,814**, not zero.
>
> **The generalisable lesson, and it is the reason this banner is long:** *"this source is
> exhausted"* and *"this subject is exhausted"* are different claims, and a query result
> whose sampling frame you did not capture can support neither. The 998 rows survive inside
> the current file as one of three source datasets — `usaspending_fsrs_pull` 53,429 ·
> `highergov_2023_export` 998 · `funding_forward_fill` 608.
>
> Current sources of truth: `docs/SUBAWARD_API_PULL_LOG.md`,
> `docs/SUBAWARD_RAW_MATCH_LOG.md`, and the PROMOTION section of
> `docs/SUBCONTRACTING_USASPENDING_PULL_2026-08-05.md` (which supersedes that document's own
> §1–§4).

---

## Headline: NET-NEW identifiers = 0 UEIs, 0 CAGEs

Against the union of `data/clean/cedar_identifier_ledger_final.csv` and
`data/clean/fpds_uei_cage_map.csv` (both read **read-only**; neither modified):

| Comparison | Net-new UEIs | Net-new CAGEs |
|---|---|---|
| vs **union** of both reference ledgers | **0** of 304 | **0** of 280 |
| vs `cedar_identifier_ledger_final.csv` alone (tiered attribution ledger) | **181** of 304 | **186** of 280 |

**The zero is real, and it has a specific cause.** `fpds_uei_cage_map.csv` already cites
`subcontract-05-09-23-22-23-37.csv` as a source for **304 of the 304** UEIs observed here.
An earlier Cedar Press stage (`13_build_fpds_hierarchy.py`) already mined this exact file
to exhaustion. Dataset 2b re-derives the identifier set independently, positionally, and
from a local copy — and **agrees with the prior extraction exactly**. That is a clean
reproducibility result, not a coverage gain.

**The actionable number is the second row: 181 UEIs and 186 CAGEs are present in the
subaward data but absent from the tiered attribution ledger.** They sit in the raw FPDS
identifier map and have never been carried into the tier system, so nothing about them is
publishable today. Most are non-Native primes (General Dynamics, BAE, Raytheon, Boeing,
Lockheed, Northrop, Tetra Tech, M.C. Dean) — which is expected and correct: direction (a)
of the subcontracting expansion is *Native entities as subs under non-Native primes*, so the
prime side of this file is largely a roster of the majors. They are written to
`data/clean/subaward_identifier_netnew.csv` with per-ledger flags for triage.

**Implication for the roadmap.** The identifier-coverage well on this file is dry. Growing
Dataset 2b's identifier yield requires a **new FSRS/USAspending subaward pull**, not further
mining of the 2023 HigherGov export. See *Coverage caveats* below.

---

## 1. Source schema — `subcontract-05-09-23-22-23-37.csv`

**49 columns, 998 data rows, all rows exactly 49 fields wide** (no ragged rows). HigherGov
export of FSRS subaward data, exported 2023-05-09 22:23:37 per the filename.

### The duplicate-column gotcha (confirmed)

The file ships **two columns both literally named `CAGE Code`**, at positions 22 and 23. A
name-based pandas read collapses or mangles them. This build reads the file **positionally**
with `csv.reader`. The two columns resolve as:

| Pos | Header as shipped | Actual content |
|---|---|---|
| 22 | `CAGE Code` | **Prime Awardee CAGE** |
| 23 | `CAGE Code` | **Prime Awardee Parent CAGE** |

Confirmed two independent ways: (a) column adjacency to `Prime Awardee UEI` (20) and
`Prime Awardee Parent UEI` (21); (b) the Stata treatment `clean/sub file.dta`, which
preserved both as `cagecode` and `x` with their original variable labels intact — Stata
renamed the collision rather than dropping it.

### Full positional schema

| Pos | Header | Non-blank / 998 | Distinct |
|---|---|---|---|
| 0 | Subaward Number | 998 | 867 |
| 1 | Sub Awardee Name | 998 | 88 |
| 2 | Sub Awardee Parent Name | 998 | 58 |
| 3 | Sub Awardee UEI | 998 | 92 |
| 4 | Sub Awardee Parent UEI | 998 | 59 |
| 5 | Sub Awardee Cage Code | 994 | 89 |
| 6 | Sub Awardee Parent Cage Code | 978 | 54 |
| 7 | Sub Parent Flag | 998 | 2 |
| 8 | Subaward Amount Total | 998 | 910 |
| 9 | Subaward Action Date | 998 | 641 |
| 10 | Subaward Action Date Fiscal Year | 998 | 13 |
| 11 | Subaward Description | 998 | 470 |
| 12 | Subaward Primary Place Of Performance City Name | 998 | 216 |
| 13 | Subaward Primary Place Of Performance State Name | 987 | 67 |
| 14 | Subaward POP Address Zip Code | 990 | 249 |
| 15 | Subaward POP Congressional District | 897 | 31 |
| 16 | Subaward POP Country Code | 998 | 7 |
| 17 | Prime Award ID | 998 | 449 |
| 18 | Prime Awardee Name | 998 | 124 |
| 19 | Prime Awardee Parent Name | 998 | 90 |
| 20 | Prime Awardee UEI | 998 | 153 |
| 21 | Prime Awardee Parent UEI | 998 | 90 |
| **22** | **`CAGE Code`** → Prime Awardee CAGE | 998 | 153 |
| **23** | **`CAGE Code`** → Prime Awardee Parent CAGE | 740 | 73 |
| 24–26 | Prime POP start / current end / potential end | 998 | 381 / 342 / 343 |
| 27–29 | Prime obligated / current value / potential value | 953 | 428 each |
| 30 | Prime Original Description | 993 | 424 |
| 31 | Prime Award Project Title | 714 | 281 |
| 32 | Prime Defense Program | 188 | 26 |
| 33 | Prime Research Code | 2 | 1 |
| 34 | Prime Type of Contract Pricing | 998 | 11 |
| 35 | Prime Solicitation Identifier | 765 | 236 |
| 36–39 | Prime awarding / top awarding / funding / top funding agency | 998 | 119 / 16 / 147 / 17 |
| 40 | Prime Vehicle | 163 | 46 |
| 41–42 | Prime PSC / PSC Title | 998 | 127 |
| 43–44 | Prime NAICS / NAICS Title | 998 | 68 |
| 45 | Prime Set Aside | 144 | 8 |
| 46 | Prime Award Type | 998 | 4 |
| 47 | FSRS Report Last Modified Date | 998 | 504 |
| 48 | HigherGov Page | 998 | **998 (unique — the row key)** |

**No DUNS column exists anywhere in this source.** The `duns` field in the harvest is empty
on every row and flagged `missing_duns`.

**`Subaward Number` is NOT a unique key** (867 distinct over 998 rows). The unique key is
`Prime Award ID` + `Subaward Number`, which is exactly what the HigherGov page URL encodes —
998 distinct, used as `source_url`.

---

## 2. Outputs

| File | Rows | Notes |
|---|---|---|
| `data/clean/subawards.csv` | **998** | One row per subaward. `direction` = `unknown` on all 998, by design. |
| `data/clean/subaward_identifier_harvest.csv` | **304** | One row per distinct `(uei, cage, duns)` observed. 304 UEIs, 280 CAGEs, 0 DUNS. |
| `data/clean/subaward_identifier_netnew.csv` | **210** | Harvest rows carrying an identifier missing from at least one reference ledger. |
| `data/clean/prime_sub_network.csv` | **220** | Prime→sub edges. 153 distinct primes, 92 distinct subs. |
| `data/raw/external/subcontracts/` | 5 files + manifest | Staged local copies with md5, byte size, source mtime. |

**Dollars:** $669,825,812 nominal across FY2011–FY2023 (13 fiscal years), as reported.
Not deflated. Three values arrived as accounting-parenthesis de-obligations — `(47)`,
`(1,914,018)`, `(5,825)` — and were parsed as negative, not dropped. Parentheses-as-negative
is unambiguous; discarding them would have silently overstated the total by $1.92M.

**Roles observed** (harvest `role` field):

| role | rows |
|---|---|
| prime | 108 |
| prime_parent | 52 |
| sub | 44 |
| sub+sub_parent | 34 |
| prime+prime_parent | 32 |
| sub_parent | 19 |
| both | 9 |
| both+sub_parent+prime_parent | 4 |
| sub+sub_parent+prime_parent | 1 |
| sub_parent+prime_parent | 1 |

*Vocabulary note:* the spec called for `role ∈ {sub, prime, both}`. The source also carries
**parent** UEIs and CAGEs on both sides — 111 identifiers are observed *only* in a parent
slot. Dropping them would have discarded a third of the identifier yield, which is the
opposite of this task's purpose. `role` therefore uses the spec vocabulary for direct roles
(`sub`, `prime`, `both`) and appends `sub_parent` / `prime_parent` where observed. Any
consumer wanting the strict three-value field can filter on the leading token.

---

## 3. Identifiers emitted exactly as observed — never repaired

Per the rules, no identifier was normalized, padded, or corrected. Malformed values are
emitted verbatim and flagged.

| `malformed_flag` | rows |
|---|---|
| `missing_duns` | 304 (all — no DUNS column in source) |
| `missing_cage` | 24 |
| `cage_len_4_ne_5` | 7 |
| `cage_len_8_ne_5` | 2 |
| `cage_nonalnum` | 2 |

**Zero UEI-format violations.** All 304 UEIs are 12 characters, alphanumeric, no `I`/`O`,
no leading zero.

**The CAGE damage is source-side, and it is Excel corruption.** Verified against the raw
file:

- **Leading zeros stripped** (7 values): Boeing `3953` (true CAGE `03953`), Boeing parent
  `8903`, Lockheed `4939` and `3640`, Raytheon `5716`, BAE Land & Armaments `6085`,
  General Dynamics Land Systems `1417`. Numeric coercion ate the leading zero.
- **Scientific notation** (2 values): Tetra Tech `7.80E+09`, S&K Security Group `6.90E+25`.
  The underlying CAGE is unrecoverable from this file.

`fpds_uei_cage_map.csv` **carries these same corrupted values unflagged** (e.g. Tetra Tech
`LMRMKLLL3LG5` → `7.80E+09`). This build is the first to flag them. Recommend the flags be
propagated; a CAGE join on `7.80E+09` will match nothing and will silently under-join.

---

## 4. Reconciliation against the 217 existing `prime_to_sub` edges

Against `data/clean/fpds_uei_edges.csv`, `edge_type = prime_to_sub`:

| Check | Result |
|---|---|
| Existing edges | 217 rows, 217 distinct pairs |
| This build | 220 distinct pairs |
| In existing, **not** in mine | **0** |
| In mine, not in existing | **3** |
| `n_observations` disagreements on the 217 shared pairs | **0** |
| `first_year` / `last_year` disagreements on shared pairs | **0** |

**No disagreement.** This build is a strict superset. The three extra edges are **self-edges
where `prime_uei == sub_uei`**: `JKCYFWJ3XY14`, `THNYM7ZLX333`, `VJDCALPAA628`. The prior
extraction dropped them, presumably as degenerate. This build **keeps them and flags them**
(`self_edge_flag = yes`) because they are real rows in the source — an entity reported as
subcontracting to itself, which is either an FSRS filing artifact or an intra-family
divisional transfer. Either way it is a source fact, not an error to be deleted. Consumers
building an input-output matrix should filter `self_edge_flag = yes` before computing
leakage, since a self-loop is not a real inter-firm linkage.

---

## 5. Stata treatments — audited, contributed nothing new

All four prior `.dta` files were read with `pyreadstat` and checked against the CSV harvest:

| File | Shape | Identifier contribution |
|---|---|---|
| `clean/sub file.dta` | 30 × 53 | 16 UEIs, 14 CAGEs — **all already in the CSV**. A Winnebago/HCI-family filtered subset of the same export. Retains both CAGE columns as `cagecode` / `x`. |
| `clean/master sub file.dta` | 185 × 4 | 59 parent UEIs (year × parent_uei sums) — **all already in the CSV**. |
| `intermediate/sub hci.dta` | 8 × 2 | Year-level sums only. **No identifiers.** |
| `intermediate/sub.dta` | 8 × 2 | Year-level sums only. **No identifiers.** |

**Net additional identifiers from all Stata files: 0 UEIs, 0 CAGEs.** They are derivatives of
the same CSV, not independent sources. `sub file.dta` does carry an analytic column,
`tribe_recipient` ("Tribe was direct recipient of awards not HCI"), and a 2022-base deflator
pair (`inflyear`, `inflfac`) — attribution content, deliberately **not** imported here, since
entity linking is out of scope for this build.

---

## 6. Coverage caveats — state plainly

**This is a filtered sample, not the subaward universe.** Say so in anything published.

1. **FSRS subaward reporting is threshold-gated and known to be incomplete.** Prime
   contractors report subawards only above a reporting threshold, only on prime awards above
   their own threshold, and compliance is self-reported and unaudited. Subawards below
   threshold, to unregistered entities, or simply unfiled **do not appear at all**. The
   absence of a subaward in this file is **not** evidence that no subcontracting occurred.
   Treat every dollar total here as a **lower bound of unknown tightness**.

2. **The export is a HigherGov query result, not a full pull.** 998 rows, 92 sub UEIs, 153
   prime UEIs, filtered toward a Native-relevant set (Cherokee Nation entities, S&K, Sioux
   Manufacturing, All Native Systems, Native Hawaiian Veterans, HCI). The query that produced
   it was not preserved. **The sampling frame is unknown**, so no denominator statement, no
   share-of-market claim, and no "Native entities received X% of subawards" is supportable
   from this file.

3. **Time coverage is uneven and the tail is incomplete.** FY2011–FY2023, but the row count
   ramps (14 in 2011 → 180 in 2020) and collapses to 24 in FY2023 because the export was
   taken 2023-05-09, mid-fiscal-year. **FY2023 is a partial year. Never chart it as a decline.**

4. **`naics` and `psc` are the PRIME award's codes, not the subaward's.** FSRS does not carry
   a subaward-level NAICS or PSC. `naics_modal` in the network file therefore describes what
   the *prime contract* was for, not what the *sub* actually supplied. This matters directly
   for TEIM: an input-output linkage built on `naics_modal` describes the demand side, not
   the supplying industry.

5. **`sub_state` is place of performance, not legal address.** 11 rows have it blank. It is
   the only geography in the file; there is no prime-side state at all.

6. **`total_subaward_usd` in the harvest mixes roles.** For an entity observed as both sub and
   prime it sums both. `total_usd_as_sub` and `total_usd_as_prime` are provided alongside
   precisely so nobody reads the combined figure as revenue.

7. **Prime dollar columns are award-level, repeated on every subaward row.** Columns 27–29
   describe the *prime contract*. Summing them across subaward rows multiple-counts. This
   build does not carry them into `subawards.csv` for that reason.

---

## 7. Known entity-resolution issue (flagged, not resolved)

`Sioux Manufacturing Corporation` appears under **two distinct sub UEIs** in the network file
(22 and 19 subawards under the same prime, BAE Land & Armaments). Same-name/different-UEI is
exactly the situation the house matching rules say to leave flagged rather than merge.
**Not resolved here** — resolution requires the spine and is out of scope. Any aggregation
over sub entities by UEI will treat these as two firms.

---

## 8. What could not be extracted

- **DUNS.** Not present in the source. Cannot be recovered from this file.
- **True CAGE for 9 entities.** Excel-corrupted at source (7 leading-zero-stripped,
  2 scientific-notation). The 7 stripped values are mechanically inferable but **were not
  repaired**, per the no-repair rule. The 2 scientific-notation values are unrecoverable.
- **`direction`.** Left `unknown` on all 998 rows by design. Deciding whether a row is
  `native_as_sub` or `native_prime_hiring` requires joining to the entity spine, which is
  attribution work and explicitly not this build's job.
- **Sub-level NAICS/PSC.** Does not exist in FSRS.
- **Prime-side state/geography.** Not in the file.
- **The HigherGov query definition.** Not preserved, so the sampling frame cannot be
  reconstructed. This is the single biggest limitation on the file's interpretability.

---

## 9. Reproducing

```
py -3 code/20_build_subcontracts.py
```

Reads only from `data/raw/external/subcontracts/` (staged local copies, manifested with
md5 in `_SOURCE_MANIFEST_subcontracts.csv`). Writes only to `data/clean/`, `docs/`, `logs/`.
`data/spine/`, `data/clean/cedar_*`, and `review/` are untouched;
`cedar_identifier_ledger_final.csv` and `fpds_uei_cage_map.csv` are opened read-only.
No entity is attributed to any tribe, ANC, or NHO anywhere in this build.
