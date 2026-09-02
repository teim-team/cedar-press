# Subaward raw-corpus match — build log

*Script `code/94_match_raw_subawards.py`. Run 2026-08-07. Every figure below was
recomputed from the files by the script itself and is reproducible from
`review/_94_summary_2026-08-07.json`.*

---

## 1. The brief, and the finding that changed it

The task was to close the FY2021–2024 hole in `data/clean/subawards.csv` —
173 / 89 / 120 / 166 rows against 7,000–8,600 in the neighbouring years — from
raw data understood to be already on disk. The stated premise was that the raw
corpus held FY2021 43,857 · FY2022 41,020 · FY2023 71,279 · FY2024 183,078 rows,
and that a puller had spent two days re-downloading what we already had.

**The first thing script 94 does is count the corpus, and the premise did not
survive it.** Reading all 22 zips end to end, 6,613,471 rows:

| FY | rows in the raw corpus |
|---|---:|
| 2001–2010 | 18,446 |
| 2011 | 326,644 |
| 2012 | 517,635 |
| 2013 | 569,137 |
| 2014 | 682,396 |
| 2015 | 644,594 |
| 2016 | 658,992 |
| 2017 | 519,998 |
| 2018 | 738,115 |
| 2019 | 678,817 |
| 2020 | 456,412 |
| **2021** | **0** |
| **2022** | **0** |
| **2023** | **0** |
| **2024** | **0** |
| 2025 | 516,151 |
| 2026 | 286,134 |
| **total** | **6,613,471** |

Three independent checks agree, and none of them is an inference:

1. **`_state.json` holds 22 finished jobs and none of them is fy2021, fy2022,
   fy2023 or fy2024.** The pull went `fy2001…fy2020`, then `fy2025`, `fy2026`.
   The four years in the middle were never submitted.
2. **No row is misfiled across jobs.** Every one of the 6,613,471 rows carries a
   `subaward_action_date_fiscal_year` equal to its own job's fiscal year — zero
   bleed — so the missing years cannot be hiding inside a neighbouring chunk.
3. **The 548 FY2021–2024 rows already in the clean file come from somewhere
   else entirely**, and their own `source_dataset` says so:

   | FY | rows | source |
   |---|---:|---|
   | 2021 | 173 | `highergov_2023_export` |
   | 2022 | 89 | `highergov_2023_export` |
   | 2023 | 24 + 96 | `highergov_2023_export` + `funding_forward_fill` |
   | 2024 | 166 | `funding_forward_fill` |

   Not one of them came from the USAspending corpus, because the corpus holds
   none.

**So the FY2021–2024 gap is a PULL gap, not a matching gap.** No matching method
creates a row for a fiscal year whose raw data is not on disk. Closing it
requires four `bulk_download` jobs (`fy2021`…`fy2024`) and nothing else. That
work is out of scope here — this session was explicitly a no-network session —
but it is the whole of what remains.

The four figures in the brief (43,857 / 41,020 / 71,279 / 183,078) do not appear
anywhere in this corpus at any aggregation. They are recorded here as
unreproduced so the next agent does not go looking for them again.

### A second hole, found the same way

**The `fy2020` job returned its assistance member and no contracts member at
all**: 456,412 assistance rows, **0 contract rows**, against 220,820 contract
rows in FY2019 and 128,449 in FY2025. FY2020 contract subawards are missing from
the corpus. That is most of why FY2020 sat at 3,224 clean rows while FY2019 had
8,637, and it needs a re-pull of the `fy2020` procurement member alongside
FY2021–2024.

---

## 2. What was done instead, and why it was worth doing

The corpus we *do* hold had been matched on exactly one route: `subawardee_uei`
and `prime_awardee_uei`, exact, against the identifier ledger (script 41,
promoted by script 45). 6.6M rows in, 53,429 out. Two routes had never been
tried, and both are available with no network at all.

| route | `source_dataset` value | basis | tier |
|---|---|---|---|
| identifier | `usaspending_fsrs_pull` | UEI exact against the ledger | ledger's own A/B |
| declared parent | `usaspending_fsrs_parent_cluster` | `subawardee_parent_uei` / `prime_awardee_parent_uei` in the ledger | **B**, family level |
| name | `usaspending_fsrs_name_match` | `33_apply_party_rulings.resolve_entity` + seven refusal guards | **B**, always |

Nothing reaches tier A. Tier A requires a ruling.

`source_dataset` is the column carrying the route because it is the only one in
the schema marked `published=0 / internal`, so the two new values cause no public
codebook drift. **`code/41_build_codebooks.py` should be re-run** to refresh its
enumerated value list for that variable; it was deliberately not run here because
`codebook_variables` is a `MUST_NOT_FALL` metric in the regression guard and
another agent was writing to the codebook concurrently.

---

## 3. Results

**8,513 rows appended.** `data/clean/subawards.csv` 55,035 → **63,548**.

The file was opened for reading to index it, its header re-read immediately
before writing, then opened in append mode. Verified after the fact: the first
44,572,721 bytes of the new file are **byte-identical** to the pre-run copy. No
existing row was rewritten.

### By route

| route | rows | distinct entities | USD after both filters |
|---|---:|---:|---:|
| identifier (UEI exact) | 6,057 | 87 | $1,492,158,911 |
| name | 2,198 | 122 | $207,051,982 |
| declared parent | 258 | 36 | $44,101,804 |
| **total** | **8,513** | **226** | **$1,743,312,697** |

**71% of the added rows rest on an identifier, 26% on a name, 3% on a declared
parent identifier.** Dollars are more concentrated still: 86% of the added value
comes in on the identifier route.

The identifier route producing 6,057 rows is itself a finding. The brief warned
that a ledger join against unattributed prime rows had returned **zero** matches
and that every UEI we know was already applied. That is true of the prime
dataset; it is **not** true here. Script 45 promoted the subaward file on
2026-08-06, and a day of rulings and identifier work has been added to the ledger
since. Re-running a deterministic join after the ledger moves is not redundant
work — it is the cheapest 6,057 rows in the file.

### By fiscal year

| FY | raw on disk | clean before | clean after | added |
|---|---:|---:|---:|---:|
| 2001 | 53 | 0 | 1 | 1 |
| 2002 | 220 | 7 | 7 | 0 |
| 2003 | 20 | 1 | 1 | 0 |
| 2004 | 31 | 1 | 1 | 0 |
| 2005 | 41 | 0 | 0 | 0 |
| 2006 | 118 | 0 | 0 | 0 |
| 2007 | 660 | 1 | 1 | 0 |
| 2008 | 1,291 | 7 | 7 | 0 |
| 2009 | 2,511 | 30 | 33 | 3 |
| 2010 | 13,501 | 113 | 141 | 28 |
| 2011 | 326,644 | 1,652 | 1,953 | 301 |
| 2012 | 517,635 | 2,679 | 3,106 | 427 |
| 2013 | 569,137 | 3,064 | 3,669 | 605 |
| 2014 | 682,396 | 4,239 | 4,963 | 724 |
| 2015 | 644,594 | 4,455 | 5,248 | 793 |
| 2016 | 658,992 | 4,797 | 5,637 | 840 |
| 2017 | 519,998 | 4,510 | 5,569 | 1,059 |
| 2018 | 738,115 | 7,399 | 8,589 | 1,190 |
| 2019 | 678,817 | 8,637 | 9,373 | 736 |
| 2020 | 456,412 | 3,224 | 3,884 | 660 |
| **2021** | **0** | 173 | 173 | **0** |
| **2022** | **0** | 89 | 89 | **0** |
| **2023** | **0** | 120 | 120 | **0** |
| **2024** | **0** | 166 | 166 | **0** |
| 2025 | 516,151 | 6,666 | 7,360 | 694 |
| 2026 | 286,134 | 3,005 | 3,457 | 452 |
| **total** | **6,613,471** | **55,035** | **63,548** | **8,513** |

FY2021–2024 are unchanged at 173 / 89 / 120 / 166. **That is the correct
outcome, not a failure of the match** — see section 1.

**4 rows carry `action_date_precedes_ffata_flag = yes`** (FY2001 ×1, FY2009 ×3).
FSRS did not exist before FFATA; these are misdated filings, and the file already
documented 47 of them. They are flagged, retained, and are not counted as
coverage. The pre-FFATA population in the file is now 51 rows.

### Entities newly reached

**134 Native entities now appear in the subaward dataset that were not in it
before** (452 → **586** distinct entities across the file; 226 entities touched
by the new rows, 134 of them for the first time).

| entity class | newly reached |
|---|---:|
| BIE School | 27 |
| Urban Indian Organization | 23 |
| Intertribal Organization | 21 |
| Alaska Native Village Corporation | 20 |
| Tribal College or University | 15 |
| Native CDFI | 14 |
| Federally recognized tribe | 9 |
| Native Hawaiian Organization | 1 |
| State-recognized tribe | 1 |
| Federally recognized Alaska Native Village | 1 |
| Native Financial Institution | 1 |
| Federal-level self-governance consortium | 1 |

This distribution is the point. **109 of the 134 came in on the name route**,
and they are concentrated in exactly the classes added to the spine most
recently — BIE schools, UIOs, intertribal organisations, TCUs, CDFIs, village
corporations. Those entities are in the spine and largely absent from the
identifier ledger, so an identifier join could not see them however many times
it was re-run. Sitting Bull College, Wa He Lut Indian School, Nevada Urban
Indians, Northwest Indian Fisheries Commission, the Inter Tribal Council of
Arizona and Council for Native Hawaiian Advancement all entered the dataset this
way.

### The two filter columns

Computed on every appended row, applied to none.

- `duplicate_status`: 6,322 `primary`, 2,191 `exact_repeat_within_source`.
- `subaward_exceeds_prime_flag`: **69** of the 8,513 report a subaward larger
  than their own prime award. Retained and flagged.

The `$1,743,312,697` above is computed with **both** filters applied
(`duplicate_status == 'primary' AND subaward_exceeds_prime_flag != 'yes'`),
which is the only defensible way to total this dataset. Spec 9.2 stands: the
subaward data is reliable about relationships and unreliable about amounts.

### Downstream

`code/81_build_passthrough_dataset.py` re-run. `direction ==
'both_sides_native'` 1,225 → **1,262**; `native_passthrough.csv` 1,262 rows (891
countable), `native_passthrough_pairs.csv` **212** entity pairs, 166 entities,
**$712.3M** countable pass-through.

---

## 4. The guards, and what they refused

The one resolver — `33_apply_party_rulings.resolve_entity` — is **imported, not
reimplemented** (regression rule 8). Every guard below is a *refusal layer* on
what it returns: the guards can only reject an answer, never invent one.

`norm` and `core` are wrapped in `lru_cache` before any call. They are pure
functions of a string, so this changes nothing about what the resolver answers;
it only stops it re-folding all 1,310 spine names on every one of 13.2M
questions. The run went from ~3.5 minutes per 250,000 rows to ~5 seconds.

| guard | refusals | what it stops |
|---|---:|---|
| 8 — municipal/county government | **872,042** | `SPOKANE, CITY OF`, `WASHOE, COUNTY OF`, `MASHPEE TOWN OF`. A county is not a tribe, and the name they share is usually the tribe's homeland. |
| 7 — single-token entity core | **435,382** | An entity whose whole distinguishing core is one non-trap word — Hamilton, Elem, Enterprise, Craig, Spokane, "Native Health" — cannot be told from a company that shares it. |
| 3 — separate legal person | **432,062** | school, college, children, housing, authority, clinic, fund in the record's extra tokens. The Chickasaw Children's Village bug, the Yakama and Blackfeet repeats, and all 148 TDHEs, in one rule. |
| 5 — non-US country | 106,904 | "Indian" may mean India. |
| 4 — state disagreement | 4,860 | Indian Pueblo Cultural Center (NM) → Makaha (HI); Sequoyah High School (OK) → Sequoyah Fund (NC). |
| 2 — record less specific than entity | 173 | The `NATIVE VILLAGE OF ELIM` → *Elim Native **Corporation*** direction. |
| 1 — trap token only | 36 | `cedar_domain.NAME_TRAPS`, 26 terms, each of which cost a real misattribution. |
| 6 — ANCSA namesake pair | 1 | 77 pairs exist; $27.59B was booked wrong on them. |
| parent-route guards 8 and 3 | 197 | `WASHOE, COUNTY OF` and `CHIEF DULL KNIFE COLLEGE, INC` both declared parent UEIs the ledger maps to tribes. A self-declared federal parent field is evidence, not authority. |

### Containment: the seventh face of the same bug

**Containment attributes nothing in this build, and it took a measurement to
justify that rather than an argument.**

An intermediate version of this script let containment link once it had passed
guards 1–6. Measured on the first 600,000 raw rows, that version produced:

| record | resolved to | subawards |
|---|---|---:|
| `FL DEPT OF HEALTH` | Native Health (UIO, AZ) | 3,135 |
| `RI DEPT OF ELEM & SEC ED` | Elem Indian Colony | 1,617 |
| `MO DEPT OF HEALTH` | Native Health | 1,537 |
| `BOOZ ALLEN HAMILTON INC` | Hamilton (tribe) | 535 |
| `PERSPECTA ENTERPRISE SOLUTIONS LLC` | Enterprise (tribe) | 376 |
| `HABITAT FOR HUMANITY OF OMAHA, INC.` | Omaha Tribe | 64 |
| `COMMUNITY BASED CARE OF SEMINOLE, INC.` | Seminole Tribe | 59 |
| `SPOKANE, CITY OF` | Spokane Tribe | 19 |
| `ONONDAGA, COUNTY OF` | Onondaga Nation | 14 |

Same state. Record strictly more specific than the entity. No institution marker
in the extra tokens. **Every guard satisfied, every answer wrong** — because the
spine stores SHORT canonical names and a short tribal name is usually also the
name of a place.

AGENTS.md records six independent faces of the containment defect. This is the
seventh, and it is the first one caught before it booked a dollar.

So containment now returns a **candidate**. The row carries on as if the name had
resolved to nothing, and the candidate is banked in `review/` under
`CANDIDATE_NOT_APPENDED` for a human. **127** distinct candidates were banked,
including several that probably *are* correct — `RED LAKE BAND OF CHIPPEWA
INDIANS` → Red Lake, `BOYS & GIRLS CLUB OF THE CHEYENNE RIVER` → Cheyenne River
Sioux — and which a ruling can convert. Spec 3: *containment is not a match.*

---

## 5. Review queue

`review/subaward_matches_2026-08-07.csv`, 4,353 rows, three statuses:

| status | rows | meaning |
|---|---:|---|
| `STAGED_TIER_B` | 226 | appended at tier B, awaiting a ruling to reach A |
| `CANDIDATE_NOT_APPENDED` | 127 | containment. Attributed to nobody. |
| `REFUSED_BY_GUARD` | 4,000 | the resolver produced a candidate and a guard refused it, listed so the refusal is auditable rather than silent (top 4,000 by dollars) |

The 226 staged decisions break down as 160 name-route and 66 parent-route; by
resolver method, 102 `exact`, 47 `core`, 11 `alias`, 66 `declared_parent_uei`.
Filling `YOUR_RULING` promotes them; a ruling is the only route to tier A.

---

## 6. Regression guard

`code/62_no_regression_check.py` run **before** and **after**. Both passed with
**no regressions**. `code/01_build_entity_spine.py` was not run. Nothing under
`gaming_*`, `nigc_*`, `admin_region*`, `resource_*` or the identifier ledger was
touched.

Note for the next agent: **script 62 does not measure the subaward dataset at
all.** It passing is real but it is not evidence about this build. The checks
that are evidence here are the byte-identical prefix, the 49-column/0-ragged-row
re-parse, and the per-route counts above.

---

## 7. What remains

1. **Pull `fy2021`, `fy2022`, `fy2023`, `fy2024`** from
   `POST /api/v2/bulk_download/awards/`, one job per fiscal year, payload exactly
   as documented in the raw folder's `_SOURCE.md` §1. This is the entire
   FY2021–2024 gap. Observe `docs/PULL_DISCIPLINE.md`: one poller per host.
2. **Re-pull the `fy2020` contracts member**, which the completed job did not
   return.
3. **`_SOURCE.md` in the raw folder is stale** — it documents 11 jobs and 345,090
   rows against 22 jobs and 6,613,471 on disk, and it still points at
   `code/43_resume_subaward_pull.sh`, which was stopped. Regenerate it with
   `code/42_write_subaward_source_doc.py`; do not hand-edit it.
4. **Re-run `code/41_build_codebooks.py`** so `source_dataset` enumerates its two
   new internal values.
5. **Rule the 226 staged tier-B decisions and the 127 containment candidates.**
   Nothing from this build publishes until they are ruled.
