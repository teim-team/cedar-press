# `extent_competed` — two vocabularies in one column, and the crosswalk that closes it

*Written 2026-08-26. Closes `docs/CICD_BENCHMARK.md` finding **INTERNAL-05** (severity HIGH).
Scripts: `code/206_profile_prime_vocabulary_seams.py`,
`code/207_normalize_extent_competed.py`, `code/cedar_extent_competed.py`,
`code/208_register_extent_competed_codebook_fragment.py`.*

---

## THE HEADLINE

**`data/clean/prime_contracts.csv` now carries `extent_competed_normalized`. Filter on
that. Do not filter on `extent_competed`.**

`extent_competed` holds two different vocabularies for the same fact, so until today any
filter on it silently selected a **source vintage** rather than a **competition status**.
It is the same failure shape as the set-aside definition change that `AGENTS.md` records
as nearly corrupting the flagship statistic — an artefact that reads as a discovery.

`extent_competed` is **not** overwritten. The raw value as recorded is evidence: it is the
only thing on the row that says which vintage the row came from.

---

## WHERE THE SEAM ACTUALLY IS — and INTERNAL-05 named it wrong

INTERNAL-05 said the letter codes came from *the BGOV era* and the labels from *the archive
era*. **Measured, that is backwards, and the seam is not the BGOV/archive seam at all.**

| `source_file` | rows | what `extent_competed` holds |
|---|---:|---|
| `master prime file.dta` (BGOV, FY2000–2022) | 376,766 | **rendered labels** (367,346) + 9,420 blank. **Zero codes.** |
| `FY2008…FY2016_All_Contracts_Full_**20260806**.zip` | 367,759 | **raw FPDS codes**, 100% of rows |
| `FY2017…FY2026_All_Contracts_Full_**20260706**.zip` | 473,243 | **rendered labels**, plus 1,561 literal `nan` |

The break is at the **FY2016 / FY2017 boundary inside the USAspending award archive**, and
it is **upstream of Cedar Press**. Measured directly in the raw extracts at
`data/raw/contracts/usaspending_archive_2026-08-07/filtered/`:

```
FY2015_ledger_rows.csv   extent_competed = 'D', 'B', 'A', 'F', 'C', 'G'
FY2016_ledger_rows.csv   extent_competed = 'D', 'B', 'A', 'F', 'G', 'C'
FY2017_ledger_rows.csv   extent_competed = 'FULL AND OPEN COMPETITION AFTER EXCLUSION OF SOURCES', ...
FY2018_ledger_rows.csv   extent_competed = 'FULL AND OPEN COMPETITION AFTER EXCLUSION OF SOURCES', ...
```

`114_pull_prime_archive.py` reads the archive column faithfully. **The archive changed what
that column contains.** Neither owner script is at fault, and neither can be "fixed" by
reading a different column — the FY2008–2016 files do not carry a separate code column.

**Why one column can hold both is settled by the dictionary itself.** They are two
different USAspending download fields:

| DAIMS-DEC element | USAspending download column | holds |
|---|---|---|
| `ExtentCompeted` | `extent_competed_code` | the code |
| `Extent Competed Description Tag` | `extent_competed` | the label |

> "Extent Competed Description Tag — Description tag (by way of the FPDS Atom Feed) that
> explains the meaning of the code provided in the Extent Competed Field."

So the archive's older monthly files put the **code** in the **description-tag** column.

---

## THE CROSSWALK, VERBATIM

**It was not reconstructed from our data and no letter was matched to a label by
frequency.** A guessed crosswalk that looks right is worse than none, because it never gets
questioned again.

**Source:** DATA Act Information Model Schema (DAIMS) — Data Element Crosswalk (DEC),
**DAIMS-DEC v2.2, Revision Date: 2022-06-03**, sheet `Public`, element `ExtentCompeted`
(`FPDS Data Dictionary Element` = `Extent Competed`), column **`Domain Values`**.

**URL:** <https://files.usaspending.gov/docs/Data_Dictionary_Crosswalk.xlsx>
— the file served behind <https://www.usaspending.gov/data-dictionary>, and the same file
`usaspending-api` loads as its Data Dictionary
(`usaspending_api/settings.py`: `DATA_DICTIONARY_DOWNLOAD_URL = {FILES_SERVER_BASE_URL}/docs/Data_Dictionary_Crosswalk.xlsx`).
Retrieved 2026-08-26, **HTTP 200, 110,540 bytes, md5 `0353550157c0c66278f67147ff916d9e`**
— one request, recorded in `logs/_HOSTLOCK_files.usaspending.gov.json`.

Definition, verbatim:

> A code that represents the competitive nature of the contract.

`Domain Values` cell, verbatim (newline-separated in the source cell):

```
A = FULL AND OPEN COMPETITION
B = NOT AVAILABLE FOR COMPETITION
C = NOT COMPETED
D = FULL AND OPEN COMPETITION AFTER EXCLUSION OF SOURCES
E = FOLLOW ON TO COMPETED ACTION
F = COMPETED UNDER SAP
G = NOT COMPETED UNDER SAP
CDO = COMPETITIVE DELIVERY ORDER
NDO = NON-COMPETITIVE DELIVERY ORDER
```

`Domain Values Code Description` cell, verbatim, which is where the FAR authority lives:

```
A = Report this code if the action resulted from an award pursuant to FAR 6.102(a) - sealed bid,
    FAR 6.102(b) - competitive proposal, FAR 6.102(c) - Combination, or any other competitive
    method that did not exclude sources of any type
B = Select this code when the contract is not available for competition
C = Select this code when the contract is not competed.
D = Select this code when some sources are excluded before competition
E = Select this code when the action is a follow on to an existing competed contract. FAR 6.302-1.
    (Note: This is not applicable to Version 1.4/1.5 documents.)
F = Select this code when the action is competed under the Simplified Acquisition Procedures.
G = Select this code when the action is NOT competed under the Simplified Acquisition Procedures.
CDO = Apply to Full and Open Competition pursuant to FAR 6.1 and only apply to Delivery Orders)
    Report this code if the IDV Type is a Federal Schedule. Report this code when the Order
    delivery/task order award was made pursuant to a process that permitted each contract awardee
    a fair opportunity to be considered. See FAR Part 16.505(b)(1). ...
NDO = Report this code when competitive procedures are not used in awarding the delivery order for
    a reason not included above (when the action was non-competitive). ...
```

**Nothing here was invented by Bloomberg Government.** The owner's read was right: these are
FPDS codes, they come from the FPDS Data Dictionary, and the DEC republishes them with the
FPDS element name attached.

### A note on where the FPDS-NG dictionary itself now lives

`www.fpds.gov` is retired — every path, including
`/downloads/top_requests/FPDSNG_Data_Dictionary.pdf` and the FPDS wiki, answers
**301 → `https://sam.gov/contracting`**. That is a fact about the host, not about the
document. `api.sam.gov` was not contacted. The DEC is the live federal republication of the
same element and is what is cited above.

---

## VERIFIED AGAINST OUR OWN DATA BEFORE IT WAS APPLIED

`py -3 code/207_normalize_extent_competed.py verify` — a separate invocation, on purpose,
for the same reason `141_pull_sam_contract_awards.py` keeps its canary outside the loop it
guards. Full output: `review/extent_competed_verify_2026-08-26.json`.

**1. Every distinct token in the file is accounted for. Twenty tokens, zero undefined.**

| raw token | rows | disposition |
|---|---:|---|
| `FULL AND OPEN COMPETITION AFTER EXCLUSION OF SOURCES` | 267,508 | label, unchanged |
| `NOT AVAILABLE FOR COMPETITION` | 233,124 | label, unchanged |
| `FULL AND OPEN COMPETITION` | 157,348 | label, unchanged |
| `B` | 134,203 | code → NOT AVAILABLE FOR COMPETITION |
| `D` | 110,603 | code → FULL AND OPEN COMPETITION AFTER EXCLUSION OF SOURCES |
| `COMPETED UNDER SAP` | 89,792 | label, unchanged |
| `A` | 65,859 | code → FULL AND OPEN COMPETITION |
| `NOT COMPETED UNDER SAP` | 46,720 | label, unchanged |
| `NOT COMPETED` | 40,266 | label, unchanged |
| `C` | 16,784 | code → NOT COMPETED |
| `F` | 14,956 | code → COMPETED UNDER SAP |
| `G` | 12,838 | code → NOT COMPETED UNDER SAP |
| *(blank)* | 9,420 | **not a value** → `NOT_REPORTED` |
| `NAN` | 9,411 | **not a value** → `NOT_REPORTED` |
| `CDO` | 3,594 | code → COMPETITIVE DELIVERY ORDER |
| `COMPETITIVE DELIVERY ORDER` | 2,721 | label, unchanged |
| `NON-COMPETITIVE DELIVERY ORDER` | 1,138 | label, unchanged |
| `NDO` | 671 | code → NON-COMPETITIVE DELIVERY ORDER |
| `FOLLOW ON TO COMPETED ACTION` | 411 | label, unchanged |
| `E` | 401 | code → FOLLOW ON TO COMPETED ACTION |

The coded side uses **exactly** the dictionary's nine codes and the labelled side **exactly**
the dictionary's nine labels. Neither side carries a tenth value. That two independently
produced vintages each close on the same nine-value domain is the strongest confirmation
available that the crosswalk is the right one.

**2. The one thing the dictionary does NOT define: `nan`.**
9,411 rows carry the literal string `nan` (the archive's rendering of a null; uppercased to
`NAN` by `114_pull_prime_archive.py`'s `.upper()`). **It is not a domain value.** It is
normalised to `NOT_REPORTED`, never to a competition status, and its basis says
`NOT_REPORTED_NULL_TOKEN` so it stays distinguishable from the 9,420 genuinely blank rows.
The same `nan` token also appears in `recipient_state_code` and `place_of_perform_state` —
see the seam audit below.

**3. Do the two vocabularies reconcile once mapped? YES.**

The controlled test is **FY2016 (codes) against FY2017 (labels)** — adjacent years, same
source system, same Cedar filter, one vintage boundary between them:

| normalized label | FY2016 | FY2017 | delta |
|---|---:|---:|---:|
| FULL AND OPEN COMPETITION AFTER EXCLUSION OF SOURCES | 37.97% | 38.30% | −0.33 pp |
| NOT AVAILABLE FOR COMPETITION | 21.82% | 21.62% | +0.20 pp |
| COMPETED UNDER SAP | 17.52% | 15.69% | **+1.83 pp** |
| FULL AND OPEN COMPETITION | 13.66% | 15.52% | **−1.86 pp** |
| NOT COMPETED UNDER SAP | 5.49% | 5.44% | +0.05 pp |
| NOT COMPETED | 3.40% | 3.04% | +0.35 pp |
| COMPETITIVE DELIVERY ORDER | 0.12% | 0.33% | −0.21 pp |
| NON-COMPETITIVE DELIVERY ORDER | 0.01% | 0.05% | −0.03 pp |
| FOLLOW ON TO COMPETED ACTION | 0.01% | 0.00% | +0.00 pp |

**Largest single-category gap across the seam: 1.86 pp.** No category appears, disappears
or halves. The break is in the **rendering only**.

*Do not read the whole-vintage columns in the JSON as a reconciliation.* `20260806` covers
FY2008–2016 and `20260706` covers FY2017–2026, so their differences are year composition,
not vocabulary. Only the adjacent-year test controls for that.

---

## WHAT WAS ADDED

Two columns, appended to `data/clean/prime_contracts.csv` by
`code/207_normalize_extent_competed.py apply`:

| column | contents |
|---|---|
| `extent_competed_normalized` | the FPDS description tag, one vocabulary — or `NOT_REPORTED`, or `UNDEFINED_BY_DICTIONARY` |
| `extent_competed_normalized_basis` | `DAIMS-DEC v2.2 ExtentCompeted \| https://files.usaspending.gov/docs/Data_Dictionary_Crosswalk.xlsx \| <disposition>` |

Dispositions: `FPDS_CODE_MAPPED` (359,909) · `LABEL_AS_RECORDED` (839,028) ·
`NOT_REPORTED_BLANK` (9,420) · `NOT_REPORTED_NULL_TOKEN` (9,411) ·
`UNDEFINED_BY_DICTIONARY` (**0 rows today**).

Result on 1,217,768 rows:

```
FULL AND OPEN COMPETITION AFTER EXCLUSION OF SOURCES      378,111
NOT AVAILABLE FOR COMPETITION                             367,327
FULL AND OPEN COMPETITION                                 223,207
COMPETED UNDER SAP                                        104,748
NOT COMPETED UNDER SAP                                     59,558
NOT COMPETED                                               57,050
NOT_REPORTED                                               18,831
COMPETITIVE DELIVERY ORDER                                  6,315
NON-COMPETITIVE DELIVERY ORDER                              1,809
FOLLOW ON TO COMPETED ACTION                                  812
```

Headline figures unchanged and re-read from the written file: **1,217,768 rows, $310.01B**,
43 columns. Backup: `prime_contracts.csv.bak_2026-08-26_pre_207_normalize_extent_competed`.

### BEFORE YOU GROUP THESE NINE INTO "COMPETED" AND "NOT COMPETED"

**There is no such line in this vocabulary and drawing one is a research decision, not a
lookup.** `COMPETED UNDER SAP` / `NOT COMPETED UNDER SAP` are Simplified Acquisition
Procedures under **FAR Part 13**, which is not a FAR Part 6 competition at all;
`CDO` / `NDO` describe fair-opportunity on delivery and task orders under FAR 16.505(b)(1),
a different question again. Any published competition share must state which of the nine it
counted.

### THIS IS AN IN-PLACE ENRICHER. A REBUILD REVERTS IT.

Concurrency rule 5: `40_build_prime_contracts.py` and `114_pull_prime_archive.py` are full
rebuilds of this file and neither knows about these columns — the same relationship
`124_apply_rulings_in_place.py` / `174_apply_rulings_to_source_tables.py` already have with
`ruling_status`. **After any rebuild of `prime_contracts.csv`, re-run
`py -3 code/207_normalize_extent_competed.py verify` then `apply`.**

The durable fix, for the owners of those two scripts: import
`cedar_extent_competed.normalize` and emit both columns at build time. The crosswalk
deliberately lives in a shared module (standing rule 8) so there is never a second copy.

---

## THE SAME QUESTION, ASKED OF EVERY OTHER COLUMN

`code/206_profile_prime_vocabulary_seams.py` measured, for **every** categorical column on
`prime_contracts.csv`, whether the BGOV era and the archive era use the same values. Full
output: `review/prime_vocabulary_seam_profile_2026-08-26.json`.

**Every column checked is listed, including the clean ones.**

| column | BGOV distinct | archive distinct | shared | verdict |
|---|---:|---:|---:|---|
| `setaside` | 7 | 7 | 7 | **CLEAN** |
| `reported_8a` | 2 | 2 | 2 | **CLEAN** |
| `reported_buy_indian` | 2 | 2 | 2 | **CLEAN** |
| `reported_indian_business` | 2 | 2 | 2 | **CLEAN** |
| `reported_native_preference` | 2 | 2 | 2 | **CLEAN** |
| `setaside_reported` | 2 | 2 | 2 | **CLEAN** |
| `sector` | 25 | 25 | 25 | **CLEAN** |
| `supersector` | 10 | 10 | 10 | **CLEAN** |
| `defense` | 2 | 2 | 2 | **CLEAN** |
| `inflation_base_year` | 1 | 1 | 1 | **CLEAN** |
| `pre_2000_flag` | 1 | 1 | 1 | **CLEAN** |
| `extent_competed` | 9 | 19 | 9 | **TWO VOCABULARIES** — 369,320 archive rows (43.9%) carry a value the BGOV era never uses. Fixed above. |
| `funding_agency` | 167 | 264 | 116 | **TWO RENDERINGS** — 50,254 BGOV rows and 126,719 archive rows carry an agency string the other era never uses. Already known; see below. |
| `place_of_perform_state` | 59 | 62 | 57 | **PARTIAL** — 87,193 archive rows (10.4%). Cause is `NAN`, plus `AE`/`AP` (military post offices) and `FM`/`PW` (Freely Associated States). BGOV alone carries `98` and `UM`. |
| `recipient_state_code` | 56 | 54 | 53 | **PARTIAL** — 324 BGOV rows (`DE`, `MP`, `VI`) and 202 archive rows (`NAN`). Trivial in size, real in kind. |
| `source_authority` | 1 | 1 | 0 | **DISJOINT BY DESIGN** — a provenance stamp, one constant per era. Not a defect. Never filter a population on it expecting a fact about the award. |
| `attribution_method` | 6 | 3 | 3 | **PIPELINE, NOT SOURCE** — `ruling_applied`, `ruling_applied_tier_c` and `unattributed` exist only on BGOV rows because the archive backfill is 100% attributed by construction (`INTERNAL-02`). |
| `confidence_tier` | 3 | 2 | 2 | **PIPELINE, NOT SOURCE** — tier `C` is BGOV-only, same cause. |
| `attributed_flag` | 2 | 1 | 1 | **PIPELINE, NOT SOURCE** — `0` is BGOV-only, same cause. |
| `ruling_status` | 9 | 8 | 8 | **PARTIAL, PIPELINE** — 96 BGOV rows carry `RULED_TIER_C_NOT_ATTRIBUTED`, which cannot arise on an all-tier-A/B population. |

Identifier and free-text columns (`contract_number`, `awardee_name`, `awardee_uei`,
`cage_code`, `parent_name`, `parent_uei`, `canonical_name`, `recipient_city_name`,
`place_of_perform_city`, `tribe_id`, `source_file`, `built_date`, `ruling_source_file`,
`ruling_applied_date`) and the money/deflator columns were **not** tested, because they are
not drawn from a controlled list and "the eras use different values" is expected there and
means nothing. Named here so the omission is a decision, not a gap.

### `funding_agency` — confirmed, and already a standing rule

The 2026-08-12 merge note in `AGENTS.md` already records this: *"the two sources use
different vocabularies for the same office — `Us Geological Survey` vs `Geological Survey`"*
— and measured that putting it in a join key would have double-counted **$20.5B**. This
profile confirms it at the value level and sizes it: **176,973 rows across both eras carry
an agency rendering the other era never produces.** It is a **rendering**, not an
identifier, and there is no authoritative code column on our side of it to normalise
against, so **no normalised column is offered here.** Do not group, join or filter on
`funding_agency` across the seam; the honest move is a separate agency-code build, and it
is not attempted in this pass.

### The `nan` token is a third, smaller finding

`114_pull_prime_archive.py` calls `.upper()` on every archive string, so a pandas-style
`nan` becomes the token `NAN` and stops looking like a null. It reaches at least three
columns (`extent_competed` 9,411, `recipient_state_code` 202, `place_of_perform_state`
~a subset of 87,193). `extent_competed_normalized` neutralises it for competition; **the
state columns are NOT fixed here** and a `NAN` state will silently survive a
`state in (...)` filter as a distinct category. Recorded, not repaired — it belongs to
114's owner.

---

## WHAT THIS UNBLOCKS

`docs/CICD_BENCHMARK.md` `DEFER-04` — CICD's published **8(a) sole-source share, >50%
(2001–2010) declining to ~35% (2011–2021)** — was `NOT_COMPUTABLE` *because of this
defect*, not because of the data: computed naively across the seam it read 0.9% then 5.3%,
which is a measurement of the vintage boundary and nothing else. It is now computable on
`extent_competed_normalized`. **It has not been computed here**, because the numerator
choice (which of the nine categories is "sole source", and whether `C`, `B` or both) is a
definitional decision that must be stated by whoever publishes it.

Re-run `py -3 code/186_cicd_benchmark.py` to move INTERNAL-05 off `UNEXPLAINED`.

---

## THE SEAM PROPAGATES DOWNSTREAM, AND THOSE FILES ARE NOT FIXED HERE

`code/79_build_award_level_contracts.py` copies `extent_competed` verbatim onto the
award-level derivatives — `data/clean/prime_contracts_awards.csv` and
`prime_contracts_published.csv` (136,288 rows each) — taking `first.get("extent_competed")`
for each award. **Those files carry the two-vocabulary defect unchanged and have no
normalised column.** Worse in kind than the transaction file: an award whose transactions
straddle FY2016/FY2017 gets whichever vocabulary its *first* row happened to use.

Not repaired in this pass, because 79 is a rebuild owned elsewhere and re-running it would
collide with in-place enrichers on its outputs (concurrency rule 5). **The fix for its
owner is one line:** import `cedar_extent_competed.normalize` and carry
`extent_competed_normalized` through, exactly as `prime_contracts.csv` now does. Until
then, **do not compute a competition figure from the award-level files.**

Other files naming this column, checked: `code/163_load_sam_contract_awards.py` maps
`coreData.competitionInformation.extentCompeted.name` from the SAM API — that is the
`.name` field, i.e. the label, so the SAM FY2000–2007 backfill will arrive on the LABEL
vocabulary; it will still need normalising when it merges, and `206` should be re-run then.
`code/227_anomaly_sweep.py` already flags this column (and `setaside`) as seam-affected.
`code/234_measure_reporting_regime_signatures.py` reads `extent_competed_normalized`
directly. `code/41_build_codebooks.py` holds the old one-line description and **must not be
run** — the fragment is the unit of work.

## ALSO RECORDED

- `data/clean/series_breaks.csv` gains the FY2016/FY2017 `SOURCE_DEFINITION_CHANGE` row
  (23 → 24 breaks), added to `code/86_build_series_breaks.py`'s `BREAKS` list so a rebuild
  keeps it.
- **Unrelated drift found while running 86, not repaired, named for its owner:** 86 prints
  *"pre-FSRS count moved from 47 to 51 — update the table text."* The subaward
  phase-in row also now measures FY2009 33 / FY2010 141 / FY2011 1,953 / FY2012 3,106
  against the text's 30 / 113 / 1,652 / 2,679. The row's *warning* is still right; its
  *numbers* are stale.
- **`data/clean/sam_prime_contracts_fy2000_2007.csv` is not in `prime_contracts.csv`** (no
  `source_file` from it appears) and was therefore not profiled. When it is merged, run 206
  again before trusting any categorical column across that third seam.
