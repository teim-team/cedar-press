# Methodology — Federal Funding to Indian Country

**`funding`. `data/clean/federal_funding_transactions.csv`, 701,955 rows,
$219,689,020,478.59 in obligations, FY2007–FY2026; plus the pre-2008 archive
tables, 2,769,748 rows covering FY2001–2007.** [measured 2026-09-02]

*Written 2026-09-02. This is the methodology record: what was pulled and from
where, how the rows were made, how entities were attributed, what was decided
and why, what the known limits are, and how often it has to be re-pulled. It is
not the product copy (`docs/datasets/_descriptors.json`) and not the codebook
(`docs/codebooks/`).*

**A note on the figures.** `[measured]` means the figure was re-counted from
the live file with `csv.reader` on 2026-09-02, streaming the whole file.
`[from the record]` means it came from a build log or docstring without
independent measurement. Where a doc and the data disagreed, the measurement
won; the disagreements are listed at the end.

**Readiness: BLOCKED**, with five named blockers — C1 grain unstated on
`faads_transactions_all_agencies.csv` and `native_passthrough.csv`, C2 no
validated key on those two, C3 literal duplicates (3,441 and 116), C7
double-counting risk on those two, and C4 at 40% of entity-bearing rows.
[measured — `docs/DATASET_READINESS.md`, regenerated 2026-09-02] **Two of those
are deliberate refusals**, explained in §4.

---

## 1. Sources

### The modern table has three strata, and they are year-aligned

| `source_vintage` | rows | obligations | fiscal years |
|---|---:|---:|---|
| `usaspending_bulk_download_2023-04-09` | **476,924** | $140,437,899,148.89 | 2008–2023 |
| `usaspending_award_archive_20260806` | **93,536** | $32,030,351,466.39 | 2008–2023 |
| `usaspending_award_archive_20260706` | **131,495** | $47,220,769,863.31 | **2007 + 2024–2026** |

[measured] They are disjoint on `assistance_transaction_unique_key`, and the
result verifies: **701,955 rows, 701,955 distinct keys, 0 duplicates, 0
blanks.** [measured]

**A hazard worth stating up front: FY2007 and FY2024–26 sit on stamp
`20260706`**, which the project's own standing notes record as the dead
stamp — the years a launch piece would lead on are the un-refreshed ones.

### The pre-2008 record

77 staged zip objects [measured], in three groups:

- 7 × `seam/doi_fy20{01..07}.zip` — Interior, **112 columns**, transaction key
  present;
- 10 × `agencies/*_fy2007_archive.zip` — **112 columns**, key present;
- 60 × `agencies/<agency>_fy200{1..6}.zip` — **20 columns, key physically
  absent**.

The route was `POST api.usaspending.gov/api/v2/bulk_download/awards/`, prime
award types 02–11, `date_type=action_date`, per toptier agency.
`30_funding_pre2008.py` requested a **20-of-112 column subset** to keep
USDA- and HHS-scale files on disk. That single decision is the origin of the
transaction-key refusal in §4b.

### What was deliberately not used

- **FAADS itself.** FAADS is NARA series naId 604955, FY1982–FY2010,
  unrestricted, 116 quarterly files, 34.2M records — and it was **ruled out**
  because USAspending's own `bulk_download` reaches 2000-10-01 in the modern
  schema. **The Cedar tables are named `faads_*` for the era, not for the
  source.**
- **USAspending's advanced-search API for pre-2008.** A hard refusal, not a
  rate limit: *"start_date falls before the earliest available search date of
  2007-10-01."*
- **Lineage B** (`dissertation/.../tribal_federal_spending`) — read-only, and
  contributes **candidates only**. It is award-grain on `first_seen_year`,
  overlaps FY2023 with no reliable key, and passed through a max-dollar dedup
  the money rules prohibit.
- **`playground.do` as the integer→name key.** It is a genuine 379-entry key —
  belonging to the HCI **contracting** lineage. The ranges overlap and
  *disagree*: `307 → Stillaguamish` there, `307 → southern ute indian tribe`
  here. The authoritative key for this lineage is
  `data/raw/external/federal_funding/lineageA_dta_corrtd_tribe_key.csv`.
- **A re-pull of FY2001–2006 to recover the transaction key** — decided
  against; see §4b.
- **Any de-duplication step at all** — see §4a.
- **Terms-restricted tribal sources** (Colville, CTUIR/Umatilla, Yakama,
  Chickasaw, NANA/Akima, Southern Ute, Forest County Potawatomi, and Navajo's
  business directory) are excluded across Cedar by every route. **The exclusion
  is SOURCE-scoped, not entity-scoped**, and it does not bite here: federal
  assistance rows naming those tribes are public record and are present.
  Measured in `federal_funding_transactions.csv`: Yakama 5,206 rows / $1.63B ·
  Chickasaw 3,860 / $5.02B · Colville 3,556 / $1.28B · Umatilla 3,481 / $0.71B
  · Southern Ute 1,443 / $0.32B · Forest County Potawatomi 1,323 / $0.23B ·
  Stillaguamish 789 / $0.13B · NANA 197 / $0.03B.

---

## 2. How the rows were made

> ⚠ **Script numbers collide.** `ls code/<n>_*` before citing any of these.

| script | role |
|---|---|
| `code/16_federal_funding_recon.py` | profile-only reconciliation of the two lineages; emits `funding_identifier_harvest.csv` and `funding_identifier_netnew_ueis.csv` |
| `code/16b_extract_funding_rulings.py`, `code/16c_copy_funding_inputs.py` | pull the do-file rulings into `data/spine/federal_funding_rulings_from_dofile.csv` |
| **`code/24_funding_merge.py`** | **the merge.** Replays `fed_funding_do_file_corrtd.do` **in source-line order** as an attribution *layer* over the 476,924-row spine |
| `code/30_funding_pre2008.py` | the FY2001–2007 pull and both `faads_*` tables |
| `code/43_funding_forward_fill.py` | FY2023-04-06 → FY2026 |
| `code/46_pull_funding_credit_types.py` | credit instruments (types 07/08/09) |
| `code/73_faads_name_attribution.py` | name-only attribution over faads → `faads_entity_attribution.csv` |
| `code/115_pull_assistance_archive.py` | the `files.usaspending.gov` static-S3 archive pull |
| `code/152_build_assistance_id_crosswalk.py` | the 361-row legacy-integer → Cedar crosswalk |
| `code/199_faads_identifier_by_agency_year.py` | the 77-row DUNS/UEI coverage grid |
| `code/335_harmonize_assistance_seams_in_place.py` | **in-place enricher**, +9 columns, 0 modified |
| `code/336_correct_scheme_resolution_by_spine_membership.py` | fixed 335's regex mislabel of 21,693 compound-handle rows |
| `code/503_identity.py` | reconcile / mint / stamp `cedar_uid` |
| `code/710_faads_attribution_content_key.py` | mints `faads_attribution_key` |
| `code/791_faads_transaction_key_and_repoint.py` | the transaction-key re-extract, snapshot, repoint and seam verification |
| `code/843_retire_cicd_scheme.py` | drops the legacy integer scheme |
| `code/81_build_passthrough_dataset.py` | `native_passthrough*` from `subawards.csv` |
| `code/75_add_bie_schools_and_uios.py`, `code/40_build_bie_uio.py` | the BIE/UIO entities and their dollars |

### The `24` replay, in one line

The spine is the raw 476,924-row USAspending CSV. **Every Stata `replace
tribe_id = …` or `drop if …` in the analyst's do-file becomes a FLAG on a
retained row.** Lineage A's three deletions survive as `ak_flag` (55,443),
`excluded_flag` and `attributed_flag`. **Nothing is dropped, ever.**

### The repoint, which is the methodologically interesting part

`faads_entity_attribution.csv` keyed 29,594 attributions to `faads_row_id` —
which is the **row position** in a 2.77-million-row file
(`73:544`, `for i, r in enumerate(rd)`). A re-extract silently re-points every
one of them, and nothing errors.

So `791` did three things before rebuilding: fingerprinted the **24 published
source columns** at each target position pre-rebuild; gave every occurrence of
each fingerprint an **ordinal** (176 of 29,594 sit inside identical-content
groups); then rebuilt the index post-rebuild and mapped through. Result:
**29,594 of 29,594 re-found, 0 moved** [measured — `faads_row_id ==
faads_row_id_2026_09_01` on all 29,594 rows, all carrying the `791` repoint
basis].

### The tables

| table | rows | note |
|---|---:|---|
| `federal_funding_transactions.csv` | **701,955** | one assistance award **transaction** (a modification), FY2007–2026 |
| `faads_transactions_all_agencies.csv` | **2,769,748** | FY2001–2007, **the whole federal assistance universe** |
| `faads_transactions.csv` | **60,661** | the **Interior** slice of the above, carried verbatim into it |
| `faads_entity_attribution.csv` | **29,594** | FY2001–2006, the only Native attribution for those years |
| `federal_funding_tribe_year_panel.csv` | **5,496** | one (entity, fiscal year), FY2008–2023 |
| `native_passthrough.csv` | **1,663** | a projection of `subawards.csv`. *Was written 1,522; re-measured 2026-09-02 — the file grew with the FY2023 Q1/Q2 subaward promotion and is consistent with its parent* |
| `native_passthrough_pairs.csv` | **324** | one (paying entity, receiving entity) pair. *Was written 307; re-measured 2026-09-02* |
| `bie_uio_dollars_by_entity.csv` | **114** | a **cross-dataset roll-up** — see §5 |
| `funding_identifier_harvest.csv` | 37,704 | identifiers harvested along the way |
| `inflation_deflator.csv` | 27 | BEA NIPA 1.1.9, base 2025 |

[measured]

---

## 3. How entities were attributed

### The modern table

`attribution_method` [measured]:

| method | rows | obligations |
|---|---:|---:|
| `dofile_corrtd:prefix` 362,746 + `:exact` 1,448 + `:prefix+city` 1,007 + an Oneida rule 334 | **365,535** | **$107,499,964,215.89** |
| `uei_exact_archive` | **183,995** | $61,139,474,728.75 |
| `unattributed` 80,205 + `not_evaluated:ak_scope_line9` 55,443 + `ledger_uei_state_disagreement_withheld` 15,878 + `ledger_exclusion` 899 | **152,425** | $51,049,581,533.95 |

The first family is Lineage A's own hand-checked attribution, replayed. The
second is **exact UEI against `cedar_identifier_ledger_final.csv` and nowhere
else** — no name matching runs on the archive stratum.

`attribution_status` (the column `843` renamed from `tribe_id_scheme_resolved`)
[measured]: `cedar_neid` 553,106 · `unattributed` 146,717 ·
`excluded_not_native` 2,119 · `unresolved_native` 13.

`confidence_tier` [measured]: **A 437,138 ($124,449,341,268.73) · B 110,952
($43,737,874,580.09) · C 59,638 ($21,084,404,779.42) · X 54,090
($12,693,667,231.83) · blank 40,137 ($17,723,732,618.52).** Tier C's dollar
figure is **identical to the cent** to the 2026-08-05 merge log — a clean
corroboration that the C pool was never touched by any later pass.

**Cedar identity coverage: `cedar_uid` on 552,602 of 701,955 rows (78.7%),
across 669 distinct handles.** [measured]

### The pre-2008 record, and the rule that governs it

**Neither `faads_*` table is a Native table.** `tribe_id` is blank on all
2,769,748 rows of `faads_transactions_all_agencies.csv` and on all 60,661 rows
of `faads_transactions.csv`. [measured] The all-agencies file's
$1,830,639,317,707.66 is the **whole federal assistance universe for
FY2001–2007** — every recipient in the country, Native and not, unfiltered. The
Interior file is an **agency** filter, not a Native one.

**It must never be quoted as money reaching Indian Country, and no ratio to a
Native total is meaningful, because the file contains no attribution to divide
by.**

The Native attribution for those years lives **outside both files**, in
`faads_entity_attribution.csv`: **29,594 rows, tier B on every single one,
`state_check_passed = 1` on every single one, 686 distinct entities, 2,287
distinct recipient names.** [measured] Population: `recipient_type = I` only
(40,657 rows in window, 28,823 attributed = 70.9%), plus a guarded secondary
Native-token pool of 771 rows admitted **only on exact or alias, never
containment**. Fourteen ordered guards; **guard 2 (state agreement) is hard** —
a state disagreement is refused, never downgraded, and a spine row with no
state cannot confirm anything.

**Two attribution floors that must never be pooled:** the identifier floor
(tier A) is **FY2007**; the name floor (tier B) is **FY2001**.

### BIE and UIO

All 302 identifier links are tier B. `rolls_up_to_a_tribe` [measured]:
`UNRESOLVED` 55 · `NO – Title V UIO` 33 · `NO – federally operated school` 14 ·
`AFFILIATION ONLY – tier B, not ownership` 12. **56 of 185 BIE schools are
federally operated and by rule have no tribal parent**; only 31 of the 129
tribally controlled schools carry one, and it is recorded as *affiliation*, not
ownership.

---

## 4. Decisions that shaped the data

### 4a. The phantom duplicates, and the $8.29 billion

| table | whole-row duplicates before `791` | after |
|---|---:|---:|
| `faads_transactions.csv` | 1,001 | **0** [measured] |
| `faads_transactions_all_agencies.csv` | 179,259 | **3,441** [measured] |

**175,818 apparent duplicates disappeared because an identity column came back,
not because a row went away. Nothing was deleted.**

The evidence was taken from the **source objects**, not inferred from the
output. Every staged object measured has exactly as many distinct
`assistance_transaction_unique_key` values as it has rows:
`ed_fy2007_archive.zip` 344,401 / 344,401; `doi_fy2001.zip` 6,951 / 6,951;
`doi_fy2002.zip` 6,842 / 6,842; and so on through FY2007. **The worst apparent
duplicate group — 445 identical UC Irvine rows — is 740 real transactions
carrying modification numbers 0001–0740, 592 of them $0.**

The rows looked identical because the **published** fields were identical: the
mapper `30_funding_pre2008.to_out_row` never carried
`assistance_transaction_unique_key` or `modification_number`, so distinct
transactions rendered the same.

**A de-duplication would have destroyed $8,291,124,113 of real obligations.**

This is one of five duplicate allegations across Cedar and one of four that
dissolved on measurement — the others being `prime_contracts` (80,778 → 0),
`prime_contracts_archive_backfill` (60,919 → 0) and `np_schedule_i_grants` (101
→ 0). Only the identity hub's 11,981 were real, and even those were distinct
events rendered identical by a lossy projection. **The rule: a duplicate is
proved against the source, never inferred from the output.**

### 4b. The transaction key is REFUSED on the all-agencies table, and the refusal is a finding

`assistance_transaction_unique_key` is present on **825,754 of 2,769,748 rows
(29.81%)** and blank on **1,943,994**. [measured] The 29.8% is every FY2007 row
and every Interior row, and it is **unique wherever present — 0 collisions.**
[measured]

Three stacked reasons make the refusal correct:

1. **The bytes do not contain the column.** The 60
   `<agency>_fy200{1..6}.zip` objects are **20-column** objects, because
   `30.COLUMNS` requested a 20-of-112 subset. This is not a mapper bug that a
   re-extract fixes — the data was never downloaded.
2. **There is no full-column route for those years.** The only 112-column
   source is the USAspending Award Data Archive, and its own listing
   **begins at FY2007**.
3. **Re-pulling was decided against, and the reason is the audit trail.** All
   29,594 attributions land on FY2001–2006 rows. A re-pull would replace
   *exactly the rows the attributions point at*, with live data restated since
   2026-08-05, destroying the ability to prove they still point at the same
   transaction. And the payoff is all-or-nothing: **a primary key blank on even
   one row collides with the other blanks, so a 99%-successful merge buys
   nothing.**

So the grain is **DECLARED on `faads_transactions.csv`** — 60,661 of 60,661
unique, 0 collisions, 0 blanks — and **REFUSED on
`faads_transactions_all_agencies.csv`**, because *a primary key blank on 70% of
a file is not a primary key.*

**Minting an occurrence ordinal to manufacture uniqueness was explicitly
declined**: *"a surrogate ordinal on a source-mirror table is how `faads_row_id`
rotted in the first place."* `30.COLUMNS` now requests the key and
`modification_number` so it cannot recur.

**The residual exposure is stated rather than hidden: 3,441 rows remain
byte-identical to another row across all 27 columns, all of them inside the
unkeyed FY2001–2006 region.** `cedar_export_safety.csv` books the table
`ROW_LEVEL_ONLY / grain UNSTATED / 3441 literal duplicate rows`.

**The documented recovery path, if an owner ever wants it:** re-pull the
**60** non-Interior FY2001–2006 agency-years, **merge the key onto existing rows
by content — never replace them** — then re-run `791 repoint`.

> **CORRECTED 2026-09-02T15:40Z, twice, by re-running
> `code/1083_faads_zip_column_census.py` and re-measuring the live table.**
>
> **It is 60, not 54.** The narrow objects are
> `{doc, doe, doj, dol, dot, ed, epa, hhs, hud, usda}` × `fy2001..fy2006`, and
> `count(distinct source_file)` over the unkeyed rows is exactly **60**.
>
> **And reason 2 above — "there is no full-column route for those years" — is
> wrong.** `seam/doi_fy2001.zip` is a **112-column FY2001 object carrying the
> key**, pulled by this same script from this same
> `bulk_download/awards` endpoint on 2026-08-05 at 19:06Z, **79 minutes before**
> the 20-column `agencies/ed_fy2001.zip` at 20:25Z. The only difference is the
> `columns` key in the payload. The archive listing beginning at FY2007 is true
> and irrelevant — these objects never came from the archive.
>
> So the state of the 1,943,994 unkeyed rows is **`NOT_ACQUIRED`**, not
> `SOURCE_DOES_NOT_PUBLISH`. **Reasons 1 and 3 are untouched and are what still
> carries the refusal**: the bytes on disk do not hold the key and cannot be
> made to (two of its five components are absent), and a re-pull must merge by
> content or it re-points all 29,594 position-keyed attributions. Full evidence:
> `docs/FAADS_TRANSACTION_KEY_SETTLEMENT_2026-09-02.md`, closing section.

### 4c. Two identifier schemes in one column, worth $107.50B — and the crosswalk deliberately not applied

Measured on `federal_funding_transactions.csv.bak_2026-08-26_pre335`, the last
backup that still carries the `tribe_id` column:

| scheme | rows | obligations |
|---|---:|---:|
| Lineage A integer ids (`192`, `201`, `343`) | **365,535** | **$107,499,964,215.89** |
| Cedar handles | **183,995** | $61,139,474,728.75 |
| unattributed | **152,425** | $51,049,581,533.95 |

**Nothing was blank and nothing was malformed — the same entity simply had two
ids.** So a per-entity total *split* an entity at the stratum boundary and a
distinct-entity count *doubled* it, invisibly. 26 canonical names appeared
under both schemes on exact match alone.

The declaring column `tribe_id_scheme` was itself the trap: populated on the
365,535 integer rows and **blank on all 336,420 others**, so it read as
authoritative while describing half the file.

**The crosswalk exists and was not applied.** `152` writes a crosswalk, not an
edit. `24_funding_merge.py:751` leaves the Cedar handle blank with the comment
*"the NEID crosswalk is a ruling, not a computation."* `335` honours both
refusals and routes the proposal into **its own columns** —
`tribe_id_neid_proposed`, `_tier`, `_basis` — with
`crosswalk_applied_into_tribe_id: false` written into
`docs/ASSISTANCE_SEAM_HARMONIZATION.json`. Three reasons were given: every
proposal inherits tier B and is never upgraded; 122 rested on the containment
matcher, **which AGENTS.md forbids from keying a dollar**; and 17 integers had
no spine candidate at all and are spine gaps rather than junk.

`336` then corrected `335`'s own error. `335` used an id-shape regex requiring a
numeric tail and mislabelled **21,693 rows across 231 compound handles** as
`UNKNOWN_SCHEME`. All 231 are in the spine as **full** handles:
`AKNF-MTLKTL-00-TLNGHD` and `CNSF-MINNCH-LL` are canonical, and the apparent
"base" `AKNF-MTLKTL-00` **is not in the spine at all**. **Never strip a suffix
to make a join work** — it would turn 21,693 joinable rows into unjoinable ones
while looking like a normalisation.

### 4d. Two renderings of the tribal-government flag

`business_types_description` renders the federally-recognized tribal government
token both as `…AMERICAN TRIBAL GOVERNMENT (FEDERALLY-RECOGNIZED)` and
`…AMERICANTRIBAL GOVERNMENT (FEDERALLY RECOGNIZED)` — **one missing space, one
absent hyphen.** An exact-string filter on the majority form silently drops the
minority rows from a column that looks like a Native flag.

Measured across all 26 distinct semicolon-delimited tokens, **it is the only
such collision** — so the repair is a literal one-entry map, not fuzzy
normalisation. (The same reason a normalising `core()` must never fold a word
carrying identity: *National Education Association → National **Indian**
Education Association*.) The original column is preserved byte-identical beside
`business_types_description_normalized`, exactly as `extent_competed` is in
contracting. Live counts [measured]: majority form **116,437**, minority
**7,160**, normalized total 123,597.

### 4e. The CICD legacy id scheme, retired 2026-09-01

`code/843_retire_cicd_scheme.py`. Owner: *"I think the CICD ID system sucks
ass. Just remove it. No one uses CICD data."* The evidence was worse than the
aesthetics. The reconciliation used a **gov-class distinctive-token match**, and
that matcher:

- **merged two federally recognised tribes** — legacy `347`, *United Keetoowah
  Band of Cherokee*, onto **Cherokee Nation**, on the token `Cherokee`:
  **820 rows, $181,881,441.37**;
- **filed county housing authorities as tribes** — legacy `344`, *Tuscarawas
  Metropolitan Housing* (Ohio), as `tuscarora tribe`; legacy `186`, *Montgomery
  County Housing Authority*, as Forest County, on the token `COUNTY`.

**Removed:** `same_as_legacy_cicd` from the register (357 entities carried
one); `tribe_id` and `tribe_id_scheme` from `federal_funding_transactions.csv`
and `federal_funding_tribe_year_panel.csv`.
**Renamed:** `tribe_id_scheme_resolved` → **`attribution_status`**,
`tribe_id_scheme_resolved_basis` → **`attribution_basis`**.
**Kept:** `cedar_uid`, `tribe_id_neid`, and the `*_proposed*` working columns.
**Moved, not deleted:** the crosswalk to `data/spine/legacy/` — *deleting the
scaffolding after the building stands would make the build unreproducible.*

**Safety was measured before anything was written.** Of the 365,535 CICD-keyed
rows, **365,491 (99.99%) already carried a `cedar_uid`**, so dropping the
integer cost **exactly 44 rows of identity — all 44 the county housing
authorities**, which are not Native entities and should never have been keyed
to one. [measured — 44 rows carry the `"CICD scheme retired 2026-09-01"` basis
string.] This was not a migration: the identity was already Cedar's, and the
CICD column was a second, worse answer sitting beside the right one.

A separate defect was repaired in the same pass and **honestly not blamed on
CICD**: 72 rows of *Sonoma County Indian Health Project* credited to Forest
County Potawatomi arrived as a stray handle with a blank scheme, and were
repointed. [measured — exactly 72 repointed; 144 further Sonoma rows remain
unkeyed.]

> **An open defect this paper found, which no document records.** The
> Keetoowah merge is **still live in the transaction table.** Measured
> 2026-09-02: **820 rows carrying `cedar_uid = CE-00134-BX` (Cherokee Nation)
> with `canonical_name = "united keetoowah band of cherokee"`, summing to
> $181,881,441.37 exactly**, FY2008 onward. The register already holds UKB
> separately as `CE-001BS-HA` / `TRBF-UKEETW-00`, and the crosswalk was
> corrected on 2026-09-01 — but `843` did not repoint the transaction rows. A
> further 407 Keetoowah-named rows *are* correctly keyed. **Any per-entity cut
> of federal funding today over-credits Cherokee Nation and zeroes UKB by that
> amount.** The register half of the defect is fixed; the data half is not.

### 4f. Money rules that shaped the columns

- **Loans never join obligations.** `federal_action_obligation`,
  `face_value_of_loan` and `original_loan_subsidy_cost` are three different
  things, and only the last is commensurable with an obligation.
- **`total_face_value_of_loan` and `total_loan_subsidy_cost` are
  AWARD-CUMULATIVE** and repeat on every transaction of the award. Summing the
  six retrieved credit rows gives $271.4M against a true $171.4M — **a $100M
  overstatement from six rows.**
- **Signs are real.** **43,866 negative rows summing −$6,755,491,333.85**, and
  **99,786 exactly-zero rows.** [measured] A deobligation is a correct record,
  not an error.
- **`business_types_code ∈ {I,J,K}` is not proof of Native status.**
  `GLENCORE LTD.` is coded `K`. The code defines the *population*; attribution
  runs through the ledger on exact UEI and nowhere else.
- **A standing prohibition: never dedup on (award_id, uei, family) keeping the
  maximum dollar.** That operator discards **$60.6B**, 83.7% of it distinct
  fiscal-year slices of live awards.

---

## 5. What a buyer may total, and the FY2007 seam

### The seam, as an exact set rather than a ratio

`faads_transactions_all_agencies.csv` covers FY2001–2007.
`federal_funding_transactions.csv` covers FY2007–2026. **They both hold FY2007,
and it is not a token overlap:**

| | rows | obligations |
|---|---:|---:|
| archive table, FY2007 | **774,755** | $475,359,703,131.83 |
| …carrying a transaction key | **774,755 (100%)** | |
| modern table, FY2007 | 11,443 | $2,189,838,445.60 |
| **…that are the SAME TRANSACTION as an archive row** | **11,063** | **$2,165,856,968.60** |
| present only in the modern table | 380 | $23,981,477.00 |

[measured — reproduced exactly]

**The rule: stack FY2001–2006 from the archive table and FY2007 onward from
`federal_funding_transactions.csv`.** The modern table is the attributed one,
so the seam belongs on its side. Loading both files whole double-counts 11,063
transactions and $2,165,856,969.

An earlier pass could only measure this as *"98.9% of the modern table's FY2007
dollars"*, because neither side carried a transaction key. Restoring the key
turned a percentage a consumer had to trust into **11,063 identified rows they
can subtract**. It is enforced by
`py -3 code/791_faads_transaction_key_and_repoint.py seam --verify` (exit 1 on
breach) against `docs/schema/faads_fy2007_seam.json`, so a future rebuild that
drops the column fails loudly instead of the seam quietly reverting to an
estimate.

### The roll-ups and projections that are not new money

| table | measure | it is a projection of | never add to |
|---|---|---|---|
| `federal_funding_tribe_year_panel.csv` | $107,047,741,120.07 over 5,496 (entity, year) cells | `federal_funding_transactions.csv`, after its filters | the transaction table, or its own `obl_type_*` columns, which decompose it |
| `faads_entity_attribution.csv` | $4,721,685,550 over 29,594 rows | the archive table — the dollar is carried verbatim onto an attribution row | either faads table |
| `native_passthrough_pairs.csv` | $869,328,591 over 307 pairs | the countable rows of `native_passthrough.csv`, reconciling to the cent | `native_passthrough.csv` |
| `bie_uio_dollars_by_entity.csv` | $3,905,609,834 over 114 entities | **FIVE DATASETS AT ONCE** | anything |

**`bie_uio_dollars_by_entity.total_usd` is a programme-exposure measure, not a
dollar total.** It adds `usd_federal_funding` $3,537,539,150 +
`usd_prime_contracts` $235,304,731 + `usd_faads_all_agencies` $120,183,074 +
`usd_subawards` $12,582,879 + `usd_nonprofit_990` $0 — an assistance
obligation, a contract obligation, and **a subaward slice of that same
contract**, which is partly the same dollar twice. Read the components; never
quote the total as money received.

**`native_passthrough.csv` is reliable about relationships and unreliable about
amounts.** FSRS is self-reported by the prime with no validation, and only
**1,135 of 1,522 rows are `amount_countable = 1`** ($869,328,591 against
$2,972,389,901 unfiltered). **Hop 2 — Native CDFI to borrower — is not visible
and is not a gap that can be closed by pulling harder**: CDFI Transaction Level
Reports are confidential.

**The figure Cedar publishes for the modern era** is $167,692,910,442 over
547,586 attributed, non-excluded FY2007–2026 rows — a different **period** as
well as a different population from anything above, so it is not the
denominator of any of it.

---

## 6. Known limits

- **Coverage starts at FY2007 in the modern table, and FY2007 exists only
  because of the `20260706` archive** — the 2023 bulk stratum begins at FY2008.
  `faads_*` starts at FY2001. **FY2000 is not served by any route at any
  price**: `bulk_download` bottoms out at 2000-10-01 and advanced search hard-
  refuses before 2007-10-01.
- **Pre-2007 identifiers barely exist.** Across FY2001–2006, **65 of 1,994,993
  rows carry a DUNS and 54 carry a UEI (0.003%).** `pct_with_duns` jumps to
  96–100% at FY2007 for nine agencies — and stays at **0.7% for DOT and 0.0%
  for Interior** even in FY2007. This is why the pre-2008 attribution is a
  name pass at tier B and can never be anything else.
- **`ak_flag` is blank on 225,031 rows** [measured] — it exists only on the
  2023 bulk stratum (0: 421,481, 1: 55,443, blank: 225,031). **Any
  `ak_flag == 0` filter silently loses a third of the table.**
- **`canonical_name` is two vocabularies and must not be grouped on.**
  **341,558 rows (61.8% of those carrying a `cedar_uid`), $94,473,554,840.79,
  have a `canonical_name` that disagrees with the identity register's name for
  that row's own `cedar_uid`**; a further 3,622 have a blank name with a uid
  present. [measured] The cause is `24_funding_merge.load_tribe_names()`
  copying the legacy do-file's display string. **The keyed identity is right in
  every checked case**: `PUEBLO OF ACOMA (INC)` × 1,097 is labelled *haaku
  community academy* and keyed `CE-0011W-HN`, which is Pueblo of Acoma.
  **Grouping on `cedar_uid` credits the tribe; grouping on the display name
  credits the school.**
- **`federal_funding_tribe_year_panel.csv` is not a panel of the dataset.** It
  covers only the Lineage-A attributed lower-48 subset — 5,496 rows, 359 names,
  FY2008–2023, **49% of the table's dollars.**
- **21.7% of rows (152,448) have no `canonical_name` at all.** A fifth of
  "Federal Funding to Indian Country" is attributed to no named entity, and
  that is honestly represented rather than filled in.
- **`assistance_type_description` is blank on 299,367 of 701,955 rows
  (42.6%)** while the coded sibling `assistance_type` is populated — so a blank
  looks like absent data when the code is present. This is the distinction
  between a grant, a cooperative agreement and a direct payment.
- **Assistance FY2020/21/22 credit backfill and FY2008–FY2023 credit types are
  still owed**; the `115` run **stopped at FY2007 when
  `files.usaspending.gov` edge-blocked.**
- **Two tables a buyer cannot safely total**:
  `faads_transactions_all_agencies.csv` (3,441 residual duplicate rows) and
  `native_passthrough.csv` (116), both booked `ROW_LEVEL_ONLY` in
  `cedar_export_safety.csv`. [measured]
- **A downstream fragility worth naming:** `faads_entity_attribution.csv` keys
  29,594 attributions to `faads_row_id`, which is a **row position**. Any
  rebuild that re-orders the parent file must re-point them in the same pass,
  or they silently move to different transactions. `791` did exactly that and
  proved 0 moved; a future rebuild must repeat it.

---

## 7. Refresh

| source | state | cadence | Cedar holds | owed |
|---|---|---|---|---|
| USAspending assistance archive | ✅ CURRENT | **monthly**, whole 93.9 GB archive replaced atomically; stamp dated the 6th, published about the 10th; **a month keeps filling for ~2 further months** (2026-05 at 66%, 2026-06 at 60% of plateau) | 2026-06-30 | **no** |
| 2023-04-09 bulk download | ⛔ closed | one-time | — | **never re-pull** — it would re-open the vintage-mixing defect `335` closed |
| FAADS-era pre-2008 | ⛔ closed | retired | 2007-09-30 | no — *stamp it once and never touch it* |
| BIE / IHS UIO rosters | ❓ edge not established | irregular snapshots; neither agency states a schedule | last pulled 2026-08-06 | **cannot be called current or stale on the evidence held** — a change-detection source, not a calendar source |

[measured — `docs/REFRESH_CADENCE.json`, regenerated 2026-09-02]

**Probe the stamp PER YEAR on the 11th, then re-filter. Do NOT run `41` or
`88`** — they rebuild from a stale upstream.

**What breaks if the archive is re-pulled:** `source_vintage` on **all 701,955
rows** (`335` is an in-place enricher, and the `.bak_<date>_pre335` file beside
the table is the signal it has run), the notes vintage written by `87`, and
`federal_funding_tribe_year_panel.csv`. **Re-run `335` then `336` after any
rebuild.** The same rebuild-reverts-enricher collision has bitten FERC four
times in this project; here the enricher must run last.

**And the source's own filling behaviour matters more than the pull cadence.** A
month is still at 60–66% of its eventual plateau two months after it first
appears, so a series built from a fresh pull understates its own newest points.

---

## Stale claims found while writing this

1. **`docs/datasets/03_funding.md` (generated 2026-09-01) says the table is
   "still SPINE ONLY — 476,924 rows ending action_date 2023-04-05 … forward
   fill … NOT merged."** It is **701,955 rows through FY2026**, merged. The
   same document's C3 duplicate counts —
   `faads_transactions.csv(1,001)`, `faads_transactions_all_agencies.csv(179,259)`,
   `native_passthrough.csv(114)` — measure to **0**, **3,441** and **116**; its
   coverage table gives `native_passthrough.csv` as 1,262 rows and
   `native_passthrough_pairs.csv` as 212, measuring **1,522** and **307**; and
   it lists `assistance_tribe_id_crosswalk.csv` as a funding table when `843`
   moved it to `data/spine/legacy/`. The generators ran before `791` and
   before `843`, and **`cedar_export_safety.csv` already carries the post-791
   figures — so two generated artefacts in the same tree disagree with each
   other.**
2. **`code/335`'s docstring gives the majority `business_types_description`
   form as 118,465 rows.** Measured **116,437** — and **116,437 in `335`'s own
   `.bak_2026-08-26_pre335` backup**, so the figure was already wrong at the
   moment it was written. The 7,160 minority figure is exact.
3. **`code/335` says "Strata B and C carry Cedar NEIDs (158,949 rows matching
   the NEID shape, $55.49B)."** Measured on the same backup: **183,995
   non-integer, non-blank rows, $61,139,474,728.75.** The 158,949 is the
   regex-matched subset that `336` later corrected, and the JSON's own
   `counts_after_336` (183,995) is right. **`code/152`'s docstring gives a
   third value for the same thing** — "Cedar-shaped (has a dash) 170,488 rows."
4. **`335`'s stated reason for refusing the crosswalk is a generation out of
   date.** It says all 344 proposals are tier B, 122 rest on containment, and
   17 integers have no candidate. The live crosswalk measures **360 with a
   proposal, tier A 359 / B 1, ZERO rows with "containment" in `match_basis`,
   and exactly 1 with no spine candidate** — `503 reconcile` upgraded it on
   2026-08-28. **But the funding table's own
   `tribe_id_neid_proposed_basis` is still frozen at the old state: 126,964
   rows on `spine resolver (containment)` and 13,713 on `no spine candidate`.**
   The refusal may still be the right call; its stated evidence is stale.
5. **`docs/IDENTIFIER_STANDARD.md` §1 and §5 instruct readers to read
   `tribe_id_scheme_resolved`.** That column no longer exists — `843` renamed
   it `attribution_status`. `docs/ASSISTANCE_SEAM_HARMONIZATION.json` also
   still lists it among "columns_added."
6. **`docs/datasets/03_funding.md` says there are "zero rows of `07` direct
   loan, `08` guaranteed loan, `09` insurance."** True of the 476,924-row
   stratum. The live table holds **1,641 type-`07` rows and 102 type-`08`
   rows, with `credit_instrument_flag = 1` on 1,817 rows** — plus undocumented
   `assistance_type` values `F001` (642), `F002` (139) and `-1` (75).
7. **The same doc says the spine carries "25,099 negative-obligation rows
   summing −$2,894,421,223.31."** Live: **43,866 negative rows,
   −$6,755,491,333.85**, plus 99,786 exactly-zero rows.
8. **`cedar_export_safety.csv` declares
   `federal_funding_tribe_year_panel.csv`'s primary key as
   `tribe_id + fiscal_year`.** `843` dropped `tribe_id` from that file. The
   real key is `canonical_name + fiscal_year`, verified unique on all 5,496
   rows — **but the declared key names a column that is gone.**
9. **`docs/FAADS_TRANSACTION_KEY_LOG.md`'s appendix gives the `canonical_name`
   drift as 345,108 rows and 3,620 blanks; `docs/WHAT_IS_MISSING.md` gives
   341,486 / 62.2% / $94.4B.** Measured: **341,558 differing
   ($94,473,554,840.79) and 3,622 blank.** All three describe the same real
   drift; none is exactly right today.
10. **`docs/FAADS_NAME_ATTRIBUTION_LOG.md` and `docs/BIE_UIO_BUILD_LOG.md` are
    written against a 1,310-entity spine; `docs/TCU_CDFI_BUILD_LOG.md` and
    `docs/ENTITY_KEY_PROPAGATION_LOG.md` against 952.** The live spine is
    **1,555 across 17 classes.** Those logs say themselves that a re-run
    against a later spine should reach *more* entities — but their numbers
    still read as current.
11. **`docs/ASSISTANCE_ARCHIVE_PULL_LOG.md` says "4,631 objects" in three
    places and self-corrects to 4,597 four hundred lines later.** The correct
    enumeration is **4,597**, and `docs/FAADS_TRANSACTION_KEY_LOG.md` still
    cites 4,631 at exactly the point where it explains why FY2001–2006 cannot
    be re-fetched.
12. **`code/503_identity.py` writes the basis tag
    `503_reconcile_assistance_to_cedar_ids` onto about 13,000 funding rows, and
    no script by that name exists** — it is in
    `graveyard/2026-08-29_identity_consolidation/`. Likewise
    `federal_funding_transactions.csv.bak_2026-09-01_pre820` exists and there
    is **no `code/820_*`**. Both are reproducibility gaps for anyone tracing
    provenance from a basis string.
