# Methodology — Lobbying

<!-- BEGIN GENERATED:IDENTITY -->

**`lobbying` — Lobbying.** Delivered as `dist/customer/lobbying.csv`: **27,825 rows × 63 columns, 21.2 MB**, built from the flagship table `data/clean/native_entity_lobbying_disclosures.csv`. Shelf `standard`; sold through **Cedar Press**; on the Cedar Press storefront. Readiness **READY**. [measured 2026-09-02 from the delivered file]

> **This block and Appendix M at the foot of this paper are GENERATED** by `code/1143_methodology_papers.py` from the delivered file itself, on every build — the same reason the codebooks are generated. Do not hand-edit either; the next build overwrites them.
>
> Everything between `<!-- BEGIN EDITORIAL:lobbying -->` and `<!-- END EDITORIAL:lobbying -->` is **hand-written and preserved byte-for-byte** across rebuilds. Put prose there and nowhere else.
>
> This paper is **not** the codebook. `dist/customer/lobbying__CODEBOOK.md` carries the grain, the folded-in tables and the per-column fill rates, and `__NOTES.txt` carries the same for a person. This paper says how the dataset came to exist and why you should believe it.
>
> Generated 2026-09-02. `py -3 code/1143_methodology_papers.py verify` **fails** if the delivered file has moved since — see §M7.

<!-- END GENERATED:IDENTITY -->

<!-- BEGIN EDITORIAL:lobbying -->
**`lobbying`. 33 customer tables across twenty channels. The LDA leg is
`native_entity_lobbying_disclosures.csv`, 27,825 filings; the largest single
table is `ferc_docket_filings.csv`, 102,615 rows.** [measured 2026-09-02]

*Written 2026-09-02. This is the methodology record: what was pulled and from
where, how the rows were made, how entities were attributed, what was decided
and why, what the known limits are, and how often it has to be re-pulled. It is
not the product copy (`docs/datasets/_descriptors.json`) and not the codebook
(`docs/codebooks/`).*

**A note on the figures.** `[measured]` means the figure was re-counted from
the live file with `csv.reader` on 2026-09-02. `[from the record]` means it
came from a build log or docstring without independent measurement. Where a doc
and the data disagreed, the measurement won; the disagreements are listed at
the end.

**Readiness: READY.** [measured — `docs/DATASET_READINESS.md`, regenerated
2026-09-02: 33 tables, 33/33 grain, 33/33 keys, duplicates clean. Lobbying
crossed the line on 2026-09-01/02, when FERC's grain, key and duplicate
problems were closed; `docs/datasets/04_lobbying.md` and
`docs/datasets/lobbying_sources.md` were generated 2026-09-01 and both still
say BLOCKED.]

---

## The premise the whole dataset is built on

**The Lobbying Disclosure Act sees only a fraction of tribal advocacy.**
Measured against the 1,555-entity spine:

```
appear in LDA filings                        300
appear in a NON-LDA channel                  669
appear in a non-LDA channel and NEVER on LDA 373
visible to the LDA and NOWHERE else            4
```

[from the record — `docs/datasets/lobbying_sources.md`, 2026-09-01]

And among the 30 spine entities that attach an IRS 990 Schedule C, **22 appear
nowhere in the LDA**; of the 13 that report an actual lobbying dollar, **10 do
not** — NARF, NIEA, AIHEC, NAIHC, the Intertribal Timber Council, ANTHC.

**The LDA is not the spine of this dataset. It is one channel of twenty, and
the narrowest one that carries a dollar figure.** Each channel is kept as its
own record type rather than merged into a single misleading total.

---

## 1. Sources

### The LDA leg

**The Senate LDA REST API, `https://lda.gov/api/v1/`** — free anonymous GET, no
key. The predecessor `lda.senate.gov/api/v1/` published a
`Sunset: Fri, 31 Jul 2026` header five days before the 2026-08-05 build; a
re-probe on 2026-09-01 found **`lda.senate.gov` still returns HTTP 200 and
serves lda.gov's content** — its own `next` URL is
`https://lda.gov/api/v1/filings/?page=2`. **It redirects; it is not dead**, and
`docs/API_KEYS.md` saying otherwise is wrong.

**The LDA floor is 1999 and it is statutory** — the Act passed in 1995 and the
first filings are 1999. Publish it as a closed floor, not a gap.

### The other nineteen channels

FERC eLibrary dockets · Federal Register and FERC ex parte notices · IBIA and
IBLA administrative appeals · OIRA EO 12866 meetings (reginfo.gov) · NRC public
meetings · congressional hearings (Congress.gov committee-meeting plus govinfo
MODS) · earmarks and Community Project Funding · **IRS 990 Schedule C**, from
raw e-file XML · 990 Schedule I pass-through · regulations.gov comments · a
FOIA request index.

### What was deliberately not used

- **A `position_on_native_issue ∈ {Support, Oppose, …}` field**, which the
  2026-08-07 specification called for. Rejected as *"a characterisation we
  would be authoring"* and the **most legally exposed field in the spec.**
  Replaced by `alignment ∈ {SAME, OPPOSED, NO_TRIBAL_POSITION_FOUND}`, computed
  per-bill from two **separately sourced** positions.
- **ProPublica Nonprofit Explorer API v2 for Schedule C.** Measured: **0 of
  8,507 `lobbying_expenditure` values populated**; the API's
  `filings_with_data` carries 46 fields and none is a lobbying figure. The
  build went to **raw IRS e-file XML** instead (6,870 XMLs).
- **FERC document full text.** Disk stood at 5.9 GB with five agents running
  against a 2 GB floor. Metadata only — and the consequence is stated:
  *"the body of each filing, which is where a stated position actually argues
  its case, has not been read."*
- **FERC eLibrary's `Search/AdvancedSearch`.** Seven well-formed POSTs all
  returned `HTTP 200 success:true totalHits:0`, **including a query for an
  accession number the docket-sheet endpoint had served seconds earlier.**
  Recorded as `NOT_FOUND` — *a broken search is not evidence of absence* —
  which is precisely **why docket discovery is seed-driven and the docket set
  is not the universe.**
- **Terms-restricted tribal sources** (Colville, CTUIR/Umatilla, Yakama,
  Chickasaw, NANA/Akima, Southern Ute, Forest County Potawatomi,
  Stillaguamish). **They do not bite here**, because every channel is a federal
  record. Measured presence in the lobbying disclosures: Forest County
  Potawatomi 273 rows · Chickasaw 262 · Southern Ute 218 · NANA 210 · Colville
  158 · Yakama 86 · Umatilla 74 · Stillaguamish 71. The restriction attaches to
  *scraping the nations' own websites*, not to federal filings about them.

---

## 2. How the rows were made

`code/lobbying_pull/04_pull_lda_v2.py` → `05_match_filings_v2.py` →
`06_build_log_stats_v2.py`; then `code/65_lobbying_organization_type_guard.py`
(organisation-type withdrawals),
`code/353_propagate_lobbying_corrections_to_consumers.py`,
`code/860_state2_acquisition.py` (the 2026-09-01 incremental),
`code/180`–`183_*` (the registrant hub),
`code/78_content_analysis.py` (issue families, target entities, verbosity —
**eight of its eighteen outputs are lobbying tables**),
`code/133_build_ferc_advocacy.py` plus
`code/327_migrate_class7_keys_to_digests.py` (FERC),
`code/144_build_admin_appeals.py` (IBIA/IBLA),
`code/98_build_oira_and_hearings.py`,
`code/99_build_earmarks_and_schedc.py`,
`code/111_build_advocacy_passthrough.py`,
`code/154_build_fr_ex_parte_notices.py`.

### The three-stage LDA pull, and why it is three stages

**Stage 1** — 12 of 12 broad-keyword `/filings/` sweeps. **Stage 2** — 231 of
231 `/clients/` sweeps, building a client universe of 2,181 distinct LDA
clients. **Stage 3** — 739 of 739 per-`client_id` fetches. 39,448 raw lines,
39,448 unique `filing_uuid`.

API quirks recorded because they change what a pull returns: `page_size` is
capped server-side at 25; the anonymous throttle is about 15 a minute with
`Retry-After: 30`; and **`client_name` is a token-PREFIX match, not a
substring** — a search for `'ribe'` returns RIBERA DEVELOPMENT.

### The 2026-09-01 incremental, and the filter proof that matters

Keyed on `dt_posted >= 2026-08-04`: 62 pages, 62 distinct page MD5s,
`records_retrieved 1527 == source_reported_total 1527`, raw **39,448 →
40,968**, 1,520 new and 7 duplicates. Match: 1,520 candidates → **29 matched**,
`rows_before 27,796 → rows_after 27,825`.

**And the filter proof, recorded in the same log:** `no filter` → count
1,976,576; `bogus param` → count **1,976,576**. **The LDA API silently ignores
unknown query parameters** — the exact opposite of the Federal Register API,
which HTTP-400s them. **A 200 from lda.gov does not prove the filter applied.**
What proves it is the `posted>=` probe returning 1,527.

---

## 3. How entities were attributed

**Name → `entity_id` only.** *The LDA carries no UEI, no CAGE and no EIN*, so
cross-dataset rulings reach this dataset **through the spine**, never directly.

Nine attribution methods: `exact_normalized` 12,456 · `core_token_set` 9,424 ·
`core_containment` 2,118 · `contains_canonical` 1,915 ·
`exact_normalized_skeleton` 1,463 · `exact_subsidiary` 238 ·
`core_token_set_plus_state_qualifier` 146 · `contains_subsidiary` 22 ·
`core_token_set_subsidiary` 14. Nine **named** unmatched reasons, the largest
being `no_alias_hit` at 7,200 filings across 311 clients. 361 clients and
$229.6M are queued for a hand ruling. [from the record]

### Organisation type is a BAR, not a similarity score

`code/65_lobbying_organization_type_guard.py` withdrew **$39.43M**, headed by
**`SALT RIVER PROJECT` — an Arizona public power and irrigation district, 324
filings, $28.71M — matched on the alias `river salt`** to the Salt River
Pima-Maricopa Indian Community. Also Coeur d'Alene **Mines** $2.96M and the
**City of** Santa Rosa $2.31M.

**Withdrawals are flagged, never deleted**: `attribution_withdrawn = 1` on
**471 of 27,825 rows**, `org_type_barred = 1` on **841**. [measured]

### The keyed rate, and the three live denominators

`docs/LOBBYING_EXPANSION_RECONCILIATION.md` headlines *"27,796 filings, 97.0%
keyed — the highest keyed rate of any Cedar dataset."* That is arithmetically
true and the **wrong universe**: the denominator is the **post-match** file.
The build log's own numbers are 39,448 scored and 27,796 matched (70.5%), so
true coverage was **26,955 / 39,448 = 68.3%** — the sales claim is off by 29
points.

**Both sides have since moved** [measured]:

```
post-match file      27,825 rows, entity_id on 26,513  ->  95.3% keyed
raw pull             40,968                            ->  64.7% true coverage
                                                           (27,825/40,968 = 67.9% matched)
distinct entities    302
518's C4, across all 33 tables                          ->  41% keyed [mixed]
```

**Say which denominator, every single time. There are three live ones.**

---

## 4. Decisions that shaped the data

### Income against expense, and why "amount" is not one column

Under the LDA an **outside registrant reports income**; a **self-filing
organisation reports expenses**. Only one is populated per filing.
`income + expenses` is a correct **portfolio** rule and a wrong **row** rule.
Cedar carries `self_filed`, `income_usd`, `expenses_usd`, `spend_usd` and
`spend_basis`.

[measured] `spend_basis`: income **16,283** · **none_reported 11,314 — 40.7% of
filings carry no dollar figure at all** · expenses 228. Sums: income
**$694,622,319**, expenses **$31,121,656**, `spend_usd` **$725,743,975**.
`self_filed = 1` on 305.

### Four independent double-count paths, one of them unfixed

1. **Amendments ship as their own rows. ~~Nothing supersedes the original.~~
   CLOSED 2026-09-02 — as flags, not deletions.**
   `docs/METHODOLOGY_LOBBYING.md` describes the kept-unchanged cleaning
   sequence as *"amendments applied over the originals they replace…
   non-standard records (registrations, terminations) set aside before any
   total is struck."* **The shipped file did not do this until 2026-09-02.**
   Measured: **1,416 amendment rows carrying $41,640,996.01**; **1,135
   `(client_id, registrant_id, filing_year, filing_period)` groups contain an
   amendment alongside the original it amends** — that count reproduces to the
   row. Also present: 1,432 Registration rows, 1,233 Termination rows and
   4,907 "(No Activity)" rows.

   **The $28,961,112 previously printed here does not reproduce and has been
   withdrawn.** The string appeared in this document twice and in no script.
   Eight candidate definitions were measured against the live file on
   2026-09-02 — $33,218,483, $36,347,996, $39,183,189, $40,119,485,
   $45,805,356, $47,866,925 and two filtered variants — and none produces it.
   **The measured double-count is $37,349,254.01 — 5.15% of $725,743,974.52**,
   over 1,064 rows, computed by `code/1091_lobby_amendment_supersession.py`,
   whose `selftest` proves all eight of its invariants fire.

   The file now carries `is_superseded`, `superseded_by_filing_uuid`,
   `supersession_status` and `supersession_group_id`. **No row was dropped**
   and no existing cell changed; row and money conservation were proved on the
   write. The additive filing-grain total is `SUM(spend_usd) WHERE
   is_superseded = 0` = **$688,394,720.51**. 129 rows carry an `AMBIGUOUS_*`
   status where which filing restates which is not knowable from the LDA
   fields Cedar holds; they stay **in** the total and are flagged, not
   guessed. Registrations and terminations are still **not** set aside:
   registrations carry $0 by construction, and terminations carry
   $17,280,761.63 of real reported spend for the period they close. Full
   account: the `LOBBY-SUPERSESSION` block of
   `docs/MONEY_TOTALLING_RULES.md`.
2. **`spend_touching` against `spend_allocated`.** A filing naming four
   agencies contributes a quarter to each under even division
   (`spend_allocated_usd`, which sums to the true total) or its full value to
   each (`spend_touching_usd`, which **sums to more than the truth by
   construction**). The build log's agency table is the second kind: HOUSE
   $679.2M + SENATE $674.1M + DOI $417.9M against a $725.2M matched total.
3. **Direct against rolled subsidiaries.** `spend_direct_usd` and
   `spend_rolled_usd` must both publish — NANA Development's filings belong to
   NANA Regional, Alutiiq's to Afognak.
4. **The figure is not precise anyway.** The LDA requires good-faith estimates
   **rounded to the nearest $10,000.** A dollar-exact total implies precision
   the source does not have.

> **A trap worth naming, and it is still open.**
> `data/clean/cedar_export_safety.csv` classifies
> `native_entity_lobbying_disclosures.csv` as **`SAFE_TO_AGGREGATE`,
> `aggregation_safe = 1`**, and `518` reports C7 double-counting as **none**
> for the whole collection. **That verdict is a literal-duplicate-row and
> primary-key test** — `filing_uuid` is unique with 0 duplicate rows — **and it
> is not an amendment-supersession test.** The $37.3M above passes straight
> through it, and still does: the flag columns added 2026-09-02 make the
> correct total *computable*, they do not change what `517` measures. Either
> `517` gains a notion of *additive under a stated predicate* or the lobbying
> contract in `512` declares one; **both files are the integrator's**, so this
> is an owner decision, not an agent's edit.

`tribe_year_lobbying_panel.csv` — **5,001 rows**, 302 entities, 1999–2026,
`total_lobbying_spend_usd` **$680,561,641** [measured], which is $45.2M below
the filing-level sum because the panel drops withdrawn and barred attributions.
**Two live totals for "Native lobbying spend." Say which.**

### FERC: the unstable id was fixed, and the fix exposed real duplication

`ferc_docket_filings.csv` — **102,615 rows** · `ADVOCACY` **22,540** +
`GOVERNMENT_ENGAGEMENT` **278** = 22,818 (79,797 rows carry a blank
`event_class`) · **`is_lobbying = 0` on all 102,615** · entity-linked
**1,109 (1.08%)** across 101 distinct entities · `filed_date` 1990-01-03 →
2026-08-26 · channel: ADMINISTRATIVE_COMMENT 20,888, ADMINISTRATIVE_APPEAL 939,
REGULATORY_EX_PARTE 713, SECTION_106_CONSULTATION 278. [measured]

**Do not publish the `abs(hash())` warning in the present tense — it was fixed
on 2026-08-26** by `code/327_migrate_class7_keys_to_digests.py`.

- **Was:** the last segment of `ferc_filing_id` was
  `abs(hash(filer_organization)) % 10000`, and **Python randomises string
  hashing per process**, so the id changed on every rebuild. The current
  migration log also records that the old hash produced **855 collisions of its
  own**.
- **Is:** `cedar_keys.surrogate_id` — a blake2b digest over NFKC-normalised,
  case-folded, whitespace-collapsed parts joined by `0x1F`, over
  `(docket_number, subdocket, accession_number, filer_organization_as_recorded,
  document_description_verbatim)`. Format `FERCFIL-<16 hex>`. **The same value
  in every process, on every machine.**
- **It is stable but NOT unique, and the log says so rather than papering over
  it: 769 groups / 1,758 rows / 989 excess** [measured — 101,626 distinct ids
  over 102,615 rows]. Every collision is **the same eLibrary document recorded
  twice**, identical on every other column up to case and whitespace. **The old
  process hash was masking that duplication.**
- The table is now keyed **`ferc_filing_id + filing_occurrence_seq`** —
  verified unique with 0 collisions; sequence distribution 1:101,626 · 2:769 ·
  3:63 · 4:51 · 5:6 · 6:6. **Do not make `ferc_filing_id` alone a foreign-key
  target.**
- The migration ran in **RECOMPUTE** mode, which was legal only because a full
  cell-by-cell scan of every `data/clean/**/*.csv` and `data/spine/*.csv`
  proved `ferc_filing_id` appears in **exactly one place — its own column.**
  `327` aborts the whole specification if it finds one undeclared consumer:
  *"a half-migrated key is worse than a bad key."*

### The FERC finding worth carrying: an empty page is not an empty docket

**eLibrary's `pageNumber` is zero-based.** A first pass starting at
`pageNumber=1` returned `DataList:[]` for **124 dockets that were not empty** —
including live hydro and pipeline proceedings — while the server truthfully
reported a non-zero `totalHits`. *"AN EMPTY PAGE IS NOT AN EMPTY DOCKET…
Published unexamined, that would have been evidence that nobody filed
anything."*

Every docket row now publishes `documents_retrieved` beside
`total_hits_reported_by_source`. Also: **`subdockets` must be a string** —
passing an array returns `Page:null` and zero rows.

**And "307 of 307 dockets" needs care.** `ferc_tribal_dockets.csv` is **307
rows over 301 distinct `docket_number`** (307 = docket × subdocket), and only
**246 distinct docket numbers actually appear in `ferc_docket_filings.csv`**
[measured] — all 246 within the seed table. `ferc_source_coverage.csv` records
that sweep with `status = NOT_FOUND` and the sentence *"THE DOCKET SET HERE IS
NOT THE UNIVERSE OF TRIBAL FERC DOCKETS AND IS NOT EVEN ALL OF THE SEED SET"*:
the run stopped at its wall-clock budget, a populated docket sheet averaging
about 100 seconds, with two requests sitting motionless for 45 and 35 minutes
because urllib's timeout is the **inter-socket gap**, not a total.

### IBIA / IBLA: three principled refusals

`admin_appeal_decisions.csv` — **15,613 rows = IBIA 4,855 + IBLA 10,758**,
built by `code/144_build_admin_appeals.py` from **114 cached HTML pages in
`data/raw/admin_appeals/` — 57 IBIA plus 57 IBLA, 1970–2026** [measured]. Every
field is transcribed from a three-column HTML table (case name, date decided,
citation). **`www.oha.doi.gov` is a second host and is never touched** — the
PDF URL is recorded as published and never fetched. `decision_date`
1969-01-02 → 2026-07-28.

1. **No register of private individuals.** The bulk of the IBIA docket is
   Indian probate, so a party classified as a natural person, and the decedent
   of an estate, get a blank `party_name` with a
   `party_name_withheld_reason`, and the caption is published redacted.
   **Nothing is lost for verification, because the reporter citation IS the
   record identifier.**
2. **No stance label.** `admin_appeal_positions.csv` is **8 rows with
   `position = UNDETERMINED` on every one** [measured], because a caption
   establishes who appealed and **never** whether the challenged action
   favoured or harmed the tribe. `party_role` comes from **caption order** and
   is carried at **tier B**, because it rests on a reporter convention.
3. **No tribe link the caption does not carry** — `NOT_STATED_IN_CAPTION`.

### The FOIA index: a stated-unit trap

`foia_request_index.csv` — **20,102 rows** [measured], grown by the 2026-09-01
pass from the 9,481 the build log records.

- **`request_date` is blank on 14,865 of 20,102 rows (73.9%).** Falling back to
  `received_date` still leaves **1,777 rows with no parseable date.**
- **The date span is 1975–2026**, against source logs the build log describes
  as 1993–2026. One 1975 row, one 2000, then nothing until 2007. **"1993–2026"
  describes the 89 retrieved source log objects, not the request dates in the
  file.**
- **The "mixed M/D/YYYY and ISO" description is stale: there are now ZERO ISO
  dates.** Format census over the coalesced date: `M/D/Y` **18,320**,
  malformed **5** (a literal `202` year), blank 1,777. Two-digit years are
  present.
- `parse_quality`: CLEAN 16,644 / **SUSPECT_BOUNDARY 3,458**. `source_format`:
  XLSX 14,506 / PDF 5,596. Top agencies: Interior–Indian Affairs 2,498 · IHS
  1,412 · DOI 1,327.

**Do not build a year series off this column without normalising it first.**

`congressional_correspondence_systems.csv` — **257 rows**: **8 correspondence
systems confirmed to exist, each quoted verbatim from the agency's own Privacy
Act SORN with its Federal Register document number** (DOI OS-20, FAA 852,
EPA-22 "Quill", HUD/ADM-09, USDA/FNS-13, HHS), plus 249 FOIA-log evidence rows.
**A SORN says the system EXISTS. It does not say any log is public** —
`log_publicly_posted = NOT_FOUND` on all 8.

---

## 5. What a buyer may total

- **`spend_usd` at filing grain, `WHERE is_superseded = 0` —
  $688,394,720.51.** The unfiltered sum is $725,743,974.52 and
  **double-counts $37,349,254.01 (5.15%)** over 1,064 rows superseded by a
  later filing in their own supersession group. Filter on the column; do not
  try to reconstruct it from `filing_type_display`, which cannot see which
  original an amendment amends.
- **A fourth number now exists, and it is the additive one.** $645.1M
  (registrants) · $680.6M (panel) · $688.4M (filings, superseded excluded) ·
  $725.7M (filings, unfiltered). **Adding any two counts the same dollar
  twice**, and the two middle figures are within $7.8M of each other by
  coincidence.
- **Never add `income_usd` and `expenses_usd` on one row** — only one is ever
  populated, and adding them across a portfolio is a different operation from
  adding them on a row.
- **Never sum `spend_touching_usd`** across agencies; use
  `spend_allocated_usd`.
- **`tribe_year_lobbying_panel.csv` is a roll-up**, $45.2M below the
  filing-level sum because it drops withdrawn and barred attributions. Never
  add the two.
- **Never sum across channels.** A FERC docket filing, an IBIA appeal, an OIRA
  meeting and an LDA filing are four different kinds of event, and only one of
  them carries a dollar.
- **`is_lobbying = 0` on every FERC row** — do not filter on it expecting
  advocacy. Filter `event_class`.
- **Every figure is rounded to the nearest $10,000 at source.**

---

## 6. Known limits

- **Entity linkage on FERC is 1,109 of 102,615 rows (1.08%)**, across 101
  entities. Closing it further is phase-2 harmonisation work.
- **Entity linkage on administrative appeals is 566 of 15,613 (3.6%)** —
  `native_entity_link_tier` A 458 / B 108 / blank 15,047 — and **`disposition`
  is blank on all 15,613 rows: the column ships empty.** [measured]
- **The FERC docket set is not the universe** and is not even all of the seed
  set — see §4.
- **FERC full text was never read**, so a stated position's argument is not in
  the data.
- **`lobbying_issue_families_filing.csv` (27,796) is one refresh behind the
  27,825-row disclosure file** — `78` has not re-run since the 2026-09-01
  append. [measured]
- **`registrant_id` is the key, never the name.** Three registrant ids carry
  more than one name over time; keying on name splits PACE, LLP into two rows
  and undercounts it by 27 filings.
- **Three count columns a buyer cannot tell apart.**
  `n_filings_native_clients`, `n_native_clients` and
  `n_distinct_native_entities` sit side by side, and the last two are
  **identical on 631 of 653 registrant rows.** A client is an LDA filing
  entity; a Native entity is a Cedar spine entity. Nothing in the shipped
  sample says which to count.
- **The sample shows no money, no issues and no targets.**
  `spend_reported_usd` is on all 653 registrants (406 non-zero, **$645.1M**),
  with `spend_sensitivity_percell_max_usd`, `spend_sensitivity_naive_sum_usd`
  and `n_filings_reporting_no_dollar` beside it — the honest treatment of the
  LDA's period-band reporting, and exactly the care a buyer pays for. **None of
  the four is in the shipped sample**, and neither are `issue_codes` (405
  registrants) or `government_entities_lobbied` (388).
- Row counts across the family [measured]: `lobbying_registrants.csv` 653 ·
  `lobbying_registrant_client_relationships.csv` 1,309 ·
  `lobbying_registrant_identifiers.csv` 525 ·
  `lobbying_registrant_native_ownership_evidence.csv` 27 ·
  `lobbying_registrant_concentration.csv` 36 · `lobbying_unmatched_clients.csv`
  515 · `lobbying_client_attribution.csv` 458 · `lobbying_target_entities.csv`
  116 · `advocacy_passthrough.csv` 1,620 · `earmarks.csv` 1,002 ·
  `hearing_appearances.csv` 2,674 · `hearing_bill_links.csv` 464 ·
  `nrc_public_meetings.csv` 251 / `nrc_meeting_participants.csv` 407 ·
  `oira_meetings.csv` 72 / `oira_meeting_participants.csv` 1,128 /
  `oira_federal_action_links.csv` 145 · `ferc_ex_parte_communications.csv` 713
  / `ferc_ex_parte_parties.csv` 4,246 / `ferc_docket_parties.csv` 11,563 ·
  `fr_ex_parte_notices.csv` 7,828 / `fr_ex_parte_parties.csv` 116 /
  `fr_ex_parte_party_entity_links.csv` 9 ·
  `agency_attention_vs_advocacy_year.csv` 698.
- **`fr_ex_parte_party_entity_links.csv` has 9 rows, and all nine come from
  `ferc_ex_parte_parties.csv`** — `fr_ex_parte_parties.csv` resolves 0 of its
  116. **A customer joining the two gets nothing, and that is the data, not a
  broken key.** Join on `(source_dataset, source_row_id)`, never
  `source_row_id` alone.
- **Row conservation covers 3 of 33 tables.** Lobbying reached READY at that
  level only because C5 is not a blocker at the scoreboard's current
  thresholds — worth stating, because it is the difference between this READY
  and `nagpra`'s.

### The one Federal Register finding that belongs here

**"641 FR ex parte notices" was never 641 notices.** It is a full-text term
count for one agency's phrase, and it includes Order No. 607, Sunshine Act
notices and the 2003 tribal consultation policy statement.
`code/154_build_fr_ex_parte_notices.py` swept the FR-wide surface instead:
**7,818 documents carry an ex parte phrase, and outside FERC only 69 name a
party** (ITA 40, NHTSA 7, FCC 4, Copyright Office 3). **The FCC is 4,430 of the
7,818 and contributes almost nothing** — its ex parte filings live in ECFS and
the FR text is permit-but-disclose boilerplate. And **"Ex Parte No. 733" is a
DOCKET NUMBER at the Surface Transportation Board** (616 documents); matching
the substring would have typed them as communications.

---

## 7. Refresh

| source | cadence | Cedar holds | state |
|---|---|---|---|
| LDA (LD-2 / LD-203) | **quarterly** LD-2, due +20 days; semiannual LD-203; **amendments arrive continuously and indefinitely** | 2026-09-01 | ✅ current |
| Tribal consultation notices (FR) | every federal business day | 2026-08-18 | **published, not pulled — 14 days behind** |
| FR ex parte notices | every federal business day | 2026-08-31 | published, not pulled — 1 day |
| Section 106 (FR) | every federal business day | 2026-09-01 | ✅ current |
| regulations.gov | continuous — comment periods are the events | 2026-07-28 | not pulled; **the gap is ENTITY coverage, not time — 51 of 1,712 query names banked** |
| IBIA / IBLA | event-driven | 2026-07-28 | source edge **not established** |
| FERC eLibrary | continuous | 2026-08-26 | source edge not established |
| Agency FOIA logs | agency-dependent | 2026-08-12 | **the gap is AGENCY coverage — 3 of about 100 agencies publish and are pulled** |
| IRS 990 Schedule C | annual index per submission year | 2026 | not pulled |
| OIRA / NRC / hearings | event-driven, posted within days | 2026-08-13 | source edge not established |

[measured — `docs/REFRESH_CADENCE.json`, regenerated 2026-09-02]

**Key on `dt_posted >= last_pull`, NEVER on `filing_year + filing_period`, and
re-read the trailing four quarters.** The LD-2 deadline is 20 days after the
quarter closes, the median filing lands **exactly on day 20 — and only 57.4%
are filed by then.** The pull is resume-safe and dedupes on `filing_uuid`.

**What breaks on refresh:**

- **`code/78_content_analysis.py` rebuilds FIVE lobbying tables AND
  `fr_content_classification.csv`.** Run it only when no other lobbying build
  is live.
- **`code/168_link_adjudication_hubs.py` runs in place and `code/133` reverts
  it. This collision has bitten FERC four times.** The enricher runs LAST.

**If the LDA is not re-pulled** you lose the trailing quarters and every late
or amended filing for quarters you already hold — and amendments arrive
indefinitely, so a year is never closed.

---

## Stale claims found while writing this

1. **`docs/datasets/04_lobbying.md` and `docs/datasets/lobbying_sources.md`,
   both generated 2026-09-01, say "Status: BLOCKED — 34 customer tables"**
   with C1/C2 open on 3 tables and 827 duplicate rows. **The scoreboard
   regenerated 2026-09-02 rates lobbying READY at 33 tables, 33/33 grain, 33/33
   keys, duplicates clean.** One day stale.
2. **`docs/CLASS7_KEY_MIGRATION_LOG.md` and every doc describing
   `ferc_filing_id` as `abs(hash(filer_organization)) % 10000` are describing a
   state that ended on 2026-08-26.** The id is now a blake2b digest,
   `FERCFIL-<16hex>`, stable across processes — **and non-unique on 989 rows**,
   which the old hash was hiding. The composite key
   `ferc_filing_id + filing_occurrence_seq` is unique.
3. **`docs/DOC_CONTRADICTIONS_2026-08-26.md`'s ground-truth row says
   `ferc_docket_filings.csv` has 822 literal duplicates.** Measured **0** under
   the composite key.
4. **`docs/LOBBYING_BUILD_LOG_2026-08-05.md` gives 27,796 filings, 300 entities
   and a raw pull of 39,448.** Measured **27,825 filings, 302 entities, raw
   40,968**.
5. **`docs/LOBBYING_EXPANSION_RECONCILIATION.md`'s corrected coverage figure of
   68.3% (26,955/39,448) has itself moved**: measured **64.7%**
   (26,513/40,968), with the post-match keyed rate at **95.3%**. Both the
   headline "97%" and its correction are now historical.
6. **The panel has three values across three documents** — 5,051 in the build
   log, 4,997 in `docs/datasets/04_lobbying.md`, **5,001 measured**.
7. **`docs/datasets/04_lobbying.md` gives `hearing_bill_links.csv` 465,
   `fr_ex_parte_notices.csv` 7,820 and `fr_ex_parte_parties.csv` 112.**
   Measured **464 · 7,828 · 116**.
8. **`docs/CONGRESSIONAL_CORRESPONDENCE_FOIA_BUILD_LOG.md` says
   `foia_request_index.csv` holds 9,481 rows spanning 1993–2026.** Measured
   **20,102 rows**, parsed dates **1975–2026**. And the widely repeated
   description of the dates as *"mixed M/D/YYYY and ISO"* is now false —
   **there are no ISO dates left.**
9. **`docs/REFRESH_CADENCE.md` gives the IBIA/IBLA refresh command as
   `code/163 --year 2026`.** **Verified wrong:** `code/163_*` are
   `163_load_sam_contract_awards.py` and
   `163_promote_nho_universe_in_place.py`, and the only script that touches
   `oha.doi.gov` is **`code/144_build_admin_appeals.py`**.
10. **~~`docs/METHODOLOGY_LOBBYING.md`'s "what we keep, unchanged" section says
    amendments are applied over the originals they replace…~~ RESOLVED
    2026-09-02.** It did say that and the shipped file did not do it — 1,416
    amendment rows, 1,432 registrations and 1,233 terminations all shipping as
    rows. Supersession now ships **as flags, not deletions**
    (`code/1091_lobby_amendment_supersession.py`); the measured double-count is
    **$37,349,254.01 (5.15%)**, not the ~~$29.0M~~ this list carried, which
    reproduced under no definition tried. Registrations and terminations are
    still not set aside, and should not be: registrations are $0 by
    construction and terminations carry $17,280,761.63 of real spend.
    `cedar_export_safety.csv` still marks the table `aggregation_safe = 1` —
    that half is **open and is the integrator's** (`517`/`512`).
11. **`docs/API_KEYS.md` records `lda.senate.gov` as dead.** Re-probed
    2026-09-01: it returns HTTP 200 and serves lda.gov's content. It redirects.
<!-- END EDITORIAL:lobbying -->

<!-- BEGIN GENERATED:MEASURED -->

---

# Appendix M — measured from the delivered file

*Generated 2026-09-02 by `code/1143_methodology_papers.py` from `dist/customer/lobbying.csv`, read whole with duckdb and never sampled. Not from `data/clean/`, not from a build log, not from `MANIFEST.csv`. Where this appendix and a document disagree, **the delivered file is right** and `verify` prints the disagreement rather than smoothing it over.*

*Grain, folded-in tables and per-column fill rates are in `dist/customer/lobbying__CODEBOOK.md` and are deliberately not repeated here.*

## M1 · Sources, as the delivered rows themselves record them

**No `source_*` column survives into the delivered file.** That is a coverage fact and a real limit: a buyer holding this spreadsheet cannot tell which upstream object a given row came from without going back to the build log. The narrative inventory of sources is in §1 of this paper.

### The terms rulings that bind this dataset

Quoted from `docs/PUBLICATION_POLICY.md`, which holds the rulings; this paper does not restate them from memory.

- **Owner ruling, 2026-09-02** (`<!-- BEGIN TERMS-OWNER-RULING-2026-09-02 -->`): *"So tribal websites, I actually don't care if they say it does scrape. Because if it's publicly available and you can scrape it, scrape it."* A tribal entity's own public pages may be harvested regardless of a terms statement. `source_terms_status = TERMS_STATED_RESTRICTIVE` on a Native entity's own site is now **a recorded observation, not a gate**.
- **Four things that ruling does NOT touch, and none is a terms question:** (1) technical access controls — nothing login-gated, no admin or staging paths, no exploiting a misconfiguration; (2) a natural person's data held apart from their public role — home address, personal email or phone, DOB, SSN/TIN; (3) non-tribal licensors — EMMA/MSRB bars redistribution of its output "sold or free of charge" and names "any manual process", with CUSIP Global Services as a second licensor; (4) proprietary identifiers — Casino City, D-U-N-S — held internally, never shipped.
- **A terms restriction is scoped to the SOURCE that stated it, not to the nation** (`<!-- BEGIN TERMS-SCOPE -->`), and it does not bind a third party's filing of the same fact.

## M2 · How the rows were built — the pipeline, in order

**One documented rebuild:** `py -3 code/build.py run lobbying --execute`. `py -3 code/build.py plan lobbying` prints the ordering below live; it is reproduced here so the paper stands alone.

The collection holds **39 tables**. Those with a named build stage, flagship first:

| table | rebuilt by | then enriched by (must run LAST) | status |
|---|---|---|---|
| `native_entity_lobbying_disclosures.csv` **(flagship)** | `05_match_filings_v2.py` | `1091_lobby_amendment_supersession.py`, `350_withdraw_false_lobbying_attributions.py`, `65_lobbying_organization_type_guard.py` | shippable |
| `ferc_docket_filings.csv` | `133_build_ferc_advocacy.py` | `168_link_adjudication_hubs.py` | shippable |
| `ferc_ex_parte_parties.csv` | `133_build_ferc_advocacy.py` | `168_link_adjudication_hubs.py` | shippable |
| `ferc_tribal_dockets.csv` | `133_build_ferc_advocacy.py` | `168_link_adjudication_hubs.py`, `175_restore_ferc_docket_table_after_rebuild_revert.py` | shippable |
| `fr_ex_parte_parties.csv` | `154_build_fr_ex_parte_notices.py` | `503_identity.py` | shippable |
| `fr_ex_parte_party_entity_links.csv` | `154_build_fr_ex_parte_notices.py` | `503_identity.py` | shippable |
| `hearing_appearances.csv` | `98_build_oira_and_hearings.py` | `400_promote_stranded_hearing_appearances.py` | shippable |
| `lobbying_issue_families_filing.csv` | `78_content_analysis.py` | `353_propagate_lobbying_corrections_to_consumers.py`, `503_identity.py` | shippable |
| `nonprofit_schedule_c_coverage.csv` | `99_build_earmarks_and_schedc.py` | `1127_schedc_coverage_basis_fix.py` | shippable |
| `tribe_year_lobbying_panel.csv` | `05_match_filings_v2.py` | `351_rebuild_lobbying_panel_from_corrected_disclosures.py`, `65_lobbying_organization_type_guard.py` | shippable |

**A full rebuild and an in-place enricher on one file need an ordering, and the enricher must run LAST.** A `.bak_*_pre<script>` file sitting beside a table is the signal that an enricher has touched it since the last build. This has cost this project four reverts of one file in a single day.

The delivered spreadsheet is then assembled by `code/1137_customer_dataset_combine.py`, which folds supporting tables onto the flagship **only where the measured cardinality on the shared key is one**, reverts any join that moved the row count, and prefixes every joined column with its source table's stem. One-to-many tables contribute a count column instead of rows, so a money total cannot be multiplied by a join.

## M3 · How entities were attributed

Cedar keys every dataset to one identity layer. `cedar_uid` is permanent and never reused; the human-readable handle retires when an entity is reclassified, so **join on `cedar_uid`, never on the handle**. A compound handle is canonical, not broken — stripping a suffix to make a join work turns joinable rows into unjoinable ones while looking like a normalisation.

**Entity attachment in the delivered file:**

| key column | rows carrying one | distinct values | coverage |
|---|---:|---:|---:|
| `cedar_uid` | 26,513 | 302 | 95.3% |

**An unkeyed row is often the right answer, not a defect.** ADR-010 separates *"we could not identify the entity"* — a defect — from *"there is no single entity to identify"* — the correct representation. Coverage is measured against the *resolvable* denominator, not the row count.

### What `attribution_method` means **in this dataset**

`docs/schema/attribution_method_vocabulary.json`, declared 2026-09-02: *"`attribution_method` is three different columns sharing a name — a join method, an evidence provenance, and a name-match algorithm. Each table is gated against its OWN vocabulary."* Reading one table's sense into another is how a containment match came to key a dollar.

A NAME-MATCH ALGORITHM. Every term names the string comparison that fired - `exact_normalized`, `exact_normalized_skeleton`, `core_token_set`, `core_containment`, `contains_canonical` and their subsidiary variants. No identifier is involved anywhere in this column, so it may never be read as tier-A evidence: a containment match is tier C by `ENTITY_MATCH_RULES` and containment may never key a dollar.

**And a RULED METHOD IS NOT A POSITIVE RULING.** `attribution_method` says WHO decided; `confidence_tier` says WHAT was decided. All 317 `elijah_ruling` EIN rows in the ledger are tier **X** — *negative* — and a script that read "the method is in the RULED set" as "the answer was yes" published 317 owner *exclusions* as confident attributions. Standing detector: `py -3 code/293_lint_bug_classes.py`. [from the record — `START_HERE.md`, defect class 1b]

### Every identity, tier and method column, measured

- **`attribution_method`** — 9 distinct values: `exact_normalized` 12,475 · `core_token_set` 9,427 · `core_containment` 2,120 · `contains_canonical` 1,917 · `exact_normalized_skeleton` 1,465 · `exact_subsidiary` 238 · `core_token_set_plus_state_qualifier` 146 · `contains_subsidiary` 23 · `core_token_set_subsidiary` 14

### The frozen term list for this dataset's flagship

A term listed in the registry is **FROZEN, not blessed**: the declaration records what shipped on 2026-09-02 so a NEW term cannot appear silently.

`native_entity_lobbying_disclosures.csv` — 9 terms: `contains_canonical` 1,917 · `contains_subsidiary` 23 · `core_containment` 2,120 · `core_token_set` 9,427 · `core_token_set_plus_state_qualifier` 146 · `core_token_set_subsidiary` 14 · `exact_normalized` 12,475 · `exact_normalized_skeleton` 1,465 · `exact_subsidiary` 238

### The evidence tiers

| tier | what it means |
|---|---|
| **A** | an identifier (UEI, CAGE, EIN, declared parent UEI), or a human ruling. The only grade a dollar may be keyed on without corroboration |
| **B** | a strong name method with an independent corroborator, or inheritance from a tier-A parent |
| **C** | a weak method — containment, token subset — held as a candidate, not published as a fact |
| **X** | **refused.** A negative ruling. Never read as a confirmation |

**A tier is INHERITED from the source row, never assigned by the consumer.** The exactness of the KEY says nothing about the correctness of the LINK: 873 of 1,104 EIN rows in the ledger sit on 52 entities carrying five or more EINs each, and 821 are tier B via `need_v6`, which is 6.5% accurate and never publishes alone. [from the record — `START_HERE.md`, defect class 1]

## M4 · What is **not** in it, and why

**No row was withheld from this delivery.** Every row that passed the collection's own inclusion test is in the spreadsheet. [measured — `dist/customer/MANIFEST.csv`, `rows_withheld = 0`]

The gate itself is `code/cedar_publication.row_ok`, applied identically by every publisher: a row is withheld if `publishable` is set to anything outside `{Y, y, 1, true, TRUE, blank}`, or if `source_terms_status` is outside `{SILENT, TERMS_STATED_NO_REUSE_RESTRICTION, blank}`. **A blank gate column means the gate was never evaluated for that row, not that it failed.** Separately, ten column names are refused outright wherever they appear — `owner_name_raw`, `email`, `phone`, `home_address`, `personal_email`, `ssn`, `tin`, `date_of_birth`, `officer_name`, `contact_name` — and the proprietary identifier families (Casino City, D-U-N-S) drop as **columns**, not rows: the row is ours, the identifier is not.

### Known gaps — every line in `docs/WHAT_IS_MISSING.md` that names this dataset or its flagship

- **L70** *(under “READ THIS FIRST — the sample is a hand-curated column list, and that is where most of the loss happens”)* — - **`lobbying` shows no money.** `spend_reported_usd` is on the table for all
- **L487** *(under “`lobbying` — `lobbying_registrants.csv`, 653 rows”)* — ## `lobbying` — `lobbying_registrants.csv`, 653 rows
- **L511** *(under “`lobbying` — `lobbying_registrants.csv`, 653 rows”)* — `native_entity_lobbying_disclosures.csv` (43,963 filing-grain rows with
- **L746** *(under “THE SHORT LIST — what this week can fix without a single download”)* — | 4 | `lobbying` | add `spend_reported_usd`, `issue_codes`, `government_entities_lobbied` | $645.1M, 405, 388 |

### Open issues — every line in `docs/KNOWN_ISSUES.md` that names this dataset or its flagship

- **L85** *(under “A2 · S3 · Three collections were documented as planning a script "not in the repository" — all three scripts exist”)* — `build_v2.py`, `lobbying` → `05_match_filings_v2.py`, `natural-resources` →
- **L544** *(under “C4 · S2 · Nine grain rulings only a human can make”)* — `contractors`, `gaming`, `lobbying`, `natural-resources`, `deals`,
- **L720** *(under “D2 · S2 · `docs/WHAT_IS_MISSING.md` carries two figures that do not reproduce”)* — | `native_entity_lobbying_disclosures.csv` "(43,963 filing-grain rows…)" | lobbying, closing note | the file holds **27,825** rows × 40 columns |
- **L1096** *(under “Corroboration: what the family count exposed (workstream CORROBORATION, 2026-09-02)”)* — **`lobbying`: LDA registrant filings × Form 990 Schedule C** — two regimes,

## M5 · The money rules — which columns may be summed

Measured over the delivered file. **A sum printed here is the unfiltered arithmetic sum of the column and is NOT necessarily a figure a buyer may quote** — the fence below says which are and which are not.

| column | rows populated | distinct values | sum (unfiltered) | min | max |
|---|---:|---:|---:|---:|---:|
| `expenses_usd` | 237 | 67 | $31,121,655.81 | $0.00 | $450,000.00 |
| `income_usd` | 17,621 | 288 | $694,622,318.71 | $0.00 | $2,400,000.00 |
| `spend_usd` | 27,825 | 312 | $725,743,974.52 | $0.00 | $2,400,000.00 |

### The fence, quoted verbatim from `docs/MONEY_TOTALLING_RULES.md`

That document is authoritative on which columns may be summed. It is **quoted here, never re-derived** — re-deriving a totalling rule from the data is precisely the error it exists to prevent.

| table | additive measure | sum it at | what double-counts |
|---|---|---|---|
| `native_entity_lobbying_disclosures.csv` | `spend_usd` | **$725,743,974.52** | one LDA **filing** — and `spend_usd` is `income_usd` + `expenses_usd`, two different reporting regimes stacked in one column |

Marked blocks in that document that name `native_entity_lobbying_disclosures.csv`: `<!-- BEGIN INT-READY -->`, `<!-- BEGIN LOBBY-SUPERSESSION -->`.

### Time span, measured

| year column | min | max | rows with no parseable year |
|---|---:|---:|---:|
| `filing_year` | 1999 | 2026 | 0 |

**Read a trend against the reporting regime, not as behaviour.** `docs/ASSUMPTIONS_AND_LIMITATIONS.md` registers the breaks; a rise that begins at a rule change is the rule operating.

## M6 · Known limits, stated plainly

**Readiness: READY.** [measured — `docs/DATASET_READINESS.md`, regenerated by `py -3 code/518_dataset_readiness.py`]

| tables | grain | keys | duplicates | agg-unsafe | rebuild |
|---|---|---|---|---|---|
| 35 | 35/35 | 35/35 | clean | 0 | declared  |

The twelve-point contract a dataset is held to — grain declared and validated; keys and cardinality measured, not guessed; duplicates removed or the distinguishing dimension declared; entity attachment where the subject is an entity; every harvested row in a named disposition bucket; unresolved identity conflicts never shipping as definite facts; no double-counting path; one documented rebuild that does not destroy later enrichment; an update runbook another session can execute from the document alone; regression and semantic-diff gates over the outputs; column hygiene; and an inclusion basis on every row.

**Do not sell past the evidence.** Where this paper states a figure it was measured on the date stamped beside it, from the file named beside it. Where it states a decision it names who made it. Anything not stated here is not known.

## M7 · Fingerprint — what makes this paper stale

`verify` re-measures the four values below against `dist/customer/lobbying.csv` and **exits 1 if any has moved**. A methodology paper is stale the moment its dataset is rebuilt, and a stale paper that cannot say so is worse than no paper.

```json
{
  "dataset": "lobbying",
  "file": "dist/customer/lobbying.csv",
  "bytes": 21206882,
  "rows": 27825,
  "columns": 63,
  "header_sha256": "e33d4f07949e0c2a268ca068ea18c256a4ab89816e2aac1f6fc88db0d6f6e4d8",
  "measured": "2026-09-02"
}
```

Cross-check against `dist/customer/MANIFEST.csv`, which `code/1137_customer_dataset_combine.py` wrote at build time: it records **27825 rows × 63 columns**. The two agree.

<!-- END GENERATED:MEASURED -->
