# Methodology — Native Federal Prime Contracting

**`contractors`. `data/clean/prime_contracts.csv`, 1,217,768 rows,
$310,005,258,660.76 in obligations, FY2000–FY2026.** [measured 2026-09-02]

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

**Readiness: READY.** [measured — `docs/DATASET_READINESS.md`, regenerated
2026-09-02: 10 tables, 10/10 grain, 10/10 keys, duplicates clean, 0
aggregation-unsafe, rebuild declared. The 2026-09-01 generation of
`docs/datasets/02_contracting.md` reports BLOCKED and is one day stale.]

---

## The claim this dataset makes, and the reason to believe it

Federal contracting **should be the cleanest dataset in Cedar**, and the reason
is structural rather than optimistic. Every advantage lands here at once:
identifiers on every row (UEI, CAGE, often a declared parent); owner rulings
already recorded against many of the large awardees; a strong
published-subsidiary route for the ANC and NHO families that dominate the
dollars; and a self-declaration incentive that makes those families announce
themselves — an NHO or ANC subsidiary gets sole-source and 8(a) advantages *by
being one*, and must say so to claim them.

So a hard case in contracting is treated as **a signal that the evidence ladder
was not run**, rather than as an intrinsically ambiguous record.

---

## 1. Sources

### The three populations, and their seams

| population | rows | obligations | years |
|---|---:|---:|---|
| **USAspending static archive** (`FY*_All_Contracts_Full_*.zip`) | 841,002 | $226,214,484,630.70 | FY2008–FY2026 |
| **BGOV / HigherGov FPDS extract** (`master prime file.dta`) | 376,766 | $83,790,774,030.07 | FY2000–FY2022 |
| **SAM.gov Contract Awards API** (separate table) | 269,312 | $40,361,791,652.38 | FY2000–FY2007 |

[measured]

**The USAspending award-data archive** —
`https://files.usaspending.gov/award_data_archive/FY####_All_Contracts_Full_########.zip`,
a plain GET with no key, and **a different host from `api.usaspending.gov`**.
The bucket was re-enumerated by `?marker=` pagination on 2026-08-12: 5 pages,
**4,597 keys** (the `?list-type=2` v2 form 404s). `_All_Contracts_Full_` exists
for **FY2007–FY2026 only**. FY2007 was never retrieved — HTTP status `0` /
`RemoteDisconnected` at 2026-08-12T16:47:45Z, **recorded as an edge block, not
as absence**.

**The BGOV extract** is `data/raw/esm_hci/ESM/clean/master prime file.dta`,
originally HigherGov's FPDS "File 1 = flag-at-award" (Justin Siken, March 2023
correspondence, retained at
`data/raw/esm_hci/ESM/documents/Gmail - Data request for Taylor policy group.pdf`).
The owner recorded its defect himself in 2026-08-07: *"i had to download with
limits through bgov, so i had to filter where i was most likely to find native
entities."* **It is under-inclusive by construction**, which is the reason the
archive backfill exists.

**SAM.gov Contract Awards API** — six `awardeeBusinessTypeName` variant
extracts for FY2000–2007, held in `sam_prime_contracts_fy2000_2007.csv` and
**not merged into `prime_contracts.csv`** [measured — no SAM `source_file`
appears there].

Attribution evidence comes from **SAM entity registrations**, **FPDS declared
parent UEIs**, and **parent-published subsidiary disclosures**, including ANCSA
audited filings under **Alaska Statute 45.55.139**, whose *Principles of
Consolidation* note enumerates subsidiaries by legal name.

### What was deliberately not used

- **`api.usaspending.gov`** — zero requests in the 114 pull.
  `POST /api/v2/download/transactions/` 503'd through a 60s→1800s backoff.
  **`code/44_pull_contracts_transactions.py` is SUPERSEDED — do not run it.**
- **The FPDS-NG ATOM feed.** 26,936,840 FY1979–2007 records, free, no key —
  never pulled. Page size is fixed at 10 with a silent 400,000-record paging
  ceiling, so a full retrieval is roughly **1.7 million requests**. It also
  **retires in FY2026** — an expiry date, not a cadence.
- **NARA RG 269 (naId 573450)**, 8,663,457 records, free and no login —
  civilian agencies only, **no DUNS and no ownership flag**, so it cannot
  carry an attribution.
- **HigherGov File 2** — a SAM-registration match, 1,078,021 rows, **26,240
  net-new pre-2007 keys worth $7.93B**, retrieved and never merged. It is
  blocked on date-gating against `ownership_events.csv`, because it matches on
  a firm's *current* registration and would therefore book a firm's
  pre-acquisition revenue to its later Native owner. Siken named ASRC/Vistronix
  as the example, and ASRC is the largest tier-A net-new entity in that file at
  $1.32B.
- **Pre-FY2000 coverage** — see §4, *"the FY2000 floor is real."*
- **Sources whose terms forbid reuse** — Colville, CTUIR/Umatilla, Yakama,
  Chickasaw, NANA/Akima, Southern Ute, Forest County Potawatomi. This bites the
  *subsidiary-list* route rather than the contracting record itself: those
  nations' federal contract rows are public record and are present. NANA/Akima
  is the costliest refusal in the project — about 55 operating companies
  publishing UEI, CAGE, DUNS, NAICS and 8(a) status, i.e. exactly the
  identifier evidence this dataset runs on. A sitemap enumeration was **stopped
  mid-run** when the terms were read.

---

## 2. How the rows were made

> ⚠ **Script numbers collide in this project.** `ls code/40_*` returns three
> files (`40_build_prime_contracts.py`, `40_contracts_ledger_pass.py`,
> `40_pull_usaspending_subawards.py`); `41_*`, `45_*`, `94_*`, `163_*` and
> `20_*` also collide. Cite the filename.

1. **`code/40_build_prime_contracts.py`** — reads the `.dta` and joins **UEI
   first, CAGE second**, against `cedar_identifier_ledger_final.csv`. **No name
   matching**: `resolve_entity` is deliberately not imported.
2. **`code/114_pull_prime_archive.py`** (`run` → `append` → `panel` →
   `codebook` → `doc`) — downloads the archive zips, filters locally to ledger
   identifiers, and writes
   `data/raw/contracts/usaspending_archive_2026-08-07/filtered/FY*_ledger_rows.csv`
   plus a `_SOURCE_MANIFEST.csv` carrying url, HTTP status, bytes, md5 and S3
   etag. FY2023–26 append to `prime_contracts.csv`; FY2008–22 stage to
   `prime_contracts_archive_backfill.csv`.
3. **`code/131_merge_archive_backfill.py`** — the merge, on the key
   `(contract_number, fiscal_year, awardee_uei)`. **The archive wins wholesale
   on a shared key**: the BGOV row is dropped, and no field is blended.
   `source_file` is never rewritten.
4. **`code/79_build_award_level_contracts.py`** — the award-level rollup →
   `prime_contracts_awards.csv` and `prime_contracts_published.csv`.
5. **`code/207_normalize_extent_competed.py apply`** — adds
   `extent_competed_normalized` and `_basis` **in place**.
6. **`code/429_apply_asof_ownership_status.py`** and
   **`code/430_restore_prime_transaction_key.py --apply`** — in-place
   enrichers.
7. **`code/428_rebuild_prime_entity_year.py --apply`** — rebuilds the
   entity-year panel from `prime_contracts.csv` as it stands.
8. **`code/141_pull_sam_contract_awards.py`** (pull) →
   **`code/163_load_sam_contract_awards.py load`** (merge the six variants).
9. **`code/13_build_fpds_hierarchy.py`** → the two `fpds_*` tables;
   **`code/269_build_contractor_ranking.py`** → the ranking.

### The tables, and what one row is

| table | rows | one row = |
|---|---:|---|
| `prime_contracts.csv` | **1,217,768** | **two populations under one schema.** An archive row is one FPDS **transaction**, identified by `contract_transaction_unique_key`. A BGOV row is one (contract, parent vehicle, fiscal year, vendor) **aggregate**, with an **empty** transaction key because none exists for it. Both are additive in `total_obligations`; **neither row count is comparable to the other** |
| `prime_contracts_archive_backfill.csv` | 631,507 | the staged FY2008–22 half of the above — **wholly contained in it** |
| `prime_contracts_awards.csv` | 455,080 | one contract (award), rolled up |
| `prime_contracts_published.csv` | 455,080 | the publishable projection of that |
| `prime_contracts_entity_year.csv` | **6,715** | one (Native entity, federal fiscal year). Tier A and tier B are **separate columns, never separate rows** |
| `contractor_ranking.csv` | 1,429 | one operating company of one Native owner, **tier A only** |
| `fpds_uei_cage_map.csv` | 34,601 | one (UEI, CAGE, legal name) triple observed in the extracts |
| `fpds_uei_edges.csv` | 5,167 | one declared (child UEI, parent UEI, edge type) |
| `sam_prime_contracts_fy2000_2007.csv` | 269,312 | one FPDS transaction in the SAM FY2000–07 pull |

[measured]

---

## 3. How entities were attributed

**Identifier only. The tier is inherited from
`cedar_identifier_ledger_final.csv` and is never assigned by the consumer.**

`attribution_method` [measured]: `uei_exact` 813,496 · `unattributed` 328,810 ·
`parent_uei` 43,593 · `cage_exact` 31,714 · `ruling_applied_tier_c` 96 ·
`ruling_applied` 59.

| tier | rows | obligations |
|---|---:|---:|
| **A** | 586,244 | **$176,743,066,195.73** |
| **B** | 302,618 | $68,022,573,658.25 |
| **C** (unattributed candidates) | 328,906 | $65,239,618,806.78 |

[measured] Attributed: **888,958 rows carry a `cedar_uid`,
$245,035,411,233.43, across 499 distinct entities and 12,491 distinct awardee
UEIs.** [measured]

`ruling_status` records what the owner decided, and it is not binary
[measured]: blank 627,016 · `RULED_ATTRIBUTED` 458,548 · `RULED_TIER_UNSTATED`
40,590 · `RULED_NOT_NATIVE` 34,699 · `RULED_CLASS_ONLY` 29,929 · `RULED_HOLD`
13,791 · `RULED_NAME_KEY_ONLY_NOT_ATTRIBUTED` 7,715 · `RULING_CONFLICT` 2,716 ·
`RULED_OWNER_NOT_IN_SPINE` 2,668 · `RULED_TIER_C_NOT_ATTRIBUTED` 96.

`owner_attribution_status` records ownership **as of the transaction**, which
is a different question from who owns the firm now [measured]:
`NO_OWNER_ATTRIBUTED` 328,906 · `RESOLVED_OWNER_NOT_IN_CEDAR` 310,421 ·
`NOT_EVALUATED` 306,626 · `CONFIRMED_AS_OF` 151,851 ·
`UNKNOWN_OUTSIDE_EVIDENCE` 58,847 · `AMBIGUOUS_OVERLAP` 41,716 ·
`NO_FACT_ON_SUBJECT` 9,459 · `CONTRADICTED_AS_OF` 9,259 · `NO_COVERING_FACT`
608 · `AMBIGUOUS_GRANULARITY` 75.

### The evidence rules that produced those tiers

**An identifier beats every name method.** A subsidiary's legal name routinely
shares no token with its owner — ASRC Federal's operating companies file as
**BROADLEAF**, **INUTEQ** and **VISTRONIX**. Shard E linked seven ASRC
subsidiaries worth **$5.43B, none sharing a single token with "Arctic Slope"**,
through published CAGE codes.

**A declared parent UEI outranks a name, and 20 observations is the floor.**
`fpds_uei_edges.csv` carries relationships the registrant filed about itself.
Below 20 observations an edge is a joint venture or a co-award, and a JV
genuinely has two parents: all 72 ledger rows whose declared parent disagrees
on a sub-20 edge are JVs (*WHH Nisqually Federal Services* declares TDX Quality
exactly **once**), while every real ownership case is observed 100+ times.
**The parent's tier does not transfer** — a link resolved through a tier-A
parent is proposed at tier B.

**When a declared parent contradicts an attribution, suspect the PARENT row
first.** A sweep of every tier A/B UEI produced 129 contradictions on $2.82B.
54 of them ($2.39B) were the *parent* row being wrong: every Bowhead subsidiary
is correctly keyed to Ukpeaġvik Iñupiat Corporation while the corporation's own
UEI was keyed to the Native *Village*, a link
`cedar_domain.village_government_owns_an_anc()` returns `False` for by
definition. 72 were the JV floor. **3 were genuine.** Acting on the raw 129
would have repointed 126 correct rows to chase 3 wrong ones.

**A join key can be poison.** `fpds_uei_cage_map.csv` carries the literal
string `NAN` in `cage_code` on **2,196 rows across 2,193 distinct UEIs** — a
pandas null stringified on export. Joining on `cage_code` without excluding it
fuses 2,193 unrelated entities into one. Excluding it, the route is near-exact:
of 6,843 real CAGE codes only 15 map to more than one UEI and none to more than
two. A **blank** `cage_code` is a value, not a gap — the extract recorded that
UEI under that legal name with no CAGE, on 23,510 of 34,601 rows.

**A token match on `Cherokee` is not weak evidence — it is no evidence.**
Forty-five entities in the register carry the token: three federally recognised
tribes, six state-recognized Cherokee groups, and about thirty businesses named
`Cherokee <something>`. The adjudication ladder is: the address → the
organisation's own website → **search the address itself and see what else is
there** → CAGE as a *pointer* to the next name, never as an answer → a news
article → **stop**. Unresolved is a legitimate outcome.

**Never inherit ownership through UEI `NW2RJN8TQQW1`** — GOVERNMENT OF THE
UNITED STATES, 29 declared children including BIA and IHS. It is blocklisted;
**99 `fpds_uei_edges` rows carry `blocklist_reason = federal_registrant_rollup`**
[measured]. **Never inherit ownership along a `prime_to_sub` edge** [measured:
550 such edges].

**FPDS populates `ultimate_parent_uei` but never `immediate_parent_uei` or
`domestic_parent_uei`** (0 of 2,279,891 rows) — the hierarchy it publishes is
flat root-to-child, with no multi-level trees. 190 of 1,805 children carry more
than one ownership parent, and that is real: firms are sold between ANCs.
Resolve by year window.

**And the last hop is Cedar's own.** The declared highest-level owner in a
federal database is the highest *incorporated* owner — **Ho-Chunk, Inc., not
the Winnebago Tribe of Nebraska**. No federal database supplies that final
edge.

### The ranking is tier A only, and the reason is measured

`contractor_ranking.csv` is `link_tier = A` on all 1,429 rows [measured];
`link_identifier_type` UEI 1,278 / CAGE 151; 283 owners over 1,424 operating
companies.

Publishing off `attributed_flag` alone would have produced this: the four
largest tier-B owner totals are Native Village of Barrow **$8.75B** — whose
largest "operating companies" are **General Dynamics IT at $3.53B** and Peraton
at $2.03B — Blue Lake Rancheria $3.66B (of which Blue Tech Inc $3.51B, the
token doing the work being *"blue"*), Eagle $2.88B and Pribilof Islands $1.06B.
**A $3.5B General Dynamics subsidiary would have appeared inside an Alaska
Native village's record at rank 8.**

---

## 4. Decisions that shaped the data

### The 80,778 duplicates that measured to zero

`docs/GRAIN_AUDIT.md` alleged **80,778 byte-identical rows** in
`prime_contracts.csv` and concluded that anyone summing it was over-counting.
`code/430_restore_prime_transaction_key.py` disproved it:

- all 80,778 came from the archive, none from the `.dta`;
- joined back to the staged rows on FY2020, **2,825 of 2,825 colliding groups
  resolved to fully distinct `contract_transaction_unique_key`, and every group
  spanned more than one `modification_number`**;
- 4,961 of FY2020's 5,194 surplus rows carry **$0** obligations.

The cause was a lossy projection: `114`'s `map_row()` projected a 40-column
transaction feed onto a 38-column BGOV schema **with no modification number, no
action date and no transaction key**. Distinct transactions rendered identical.

**Nothing was deleted. The key was restored instead.** [measured today:
`contract_transaction_unique_key` has **0 keys appearing more than once** across
841,003 distinct values, and 376,766 BGOV rows carry a deliberately **empty**
key; whole-row duplicates across the full file: **0**.] The same disproof ran on
`prime_contracts_archive_backfill.csv`: **60,919 → 0**.

**The rule this earned: a duplicate is proved against the source, never
inferred from the output.** An identical-looking row is evidence that the
projection is lossy, and the fix is a restored key — never a delete. The same
shape recurred three more times in Cedar: `faads_*` (180,260 → 3,441, where a
de-dupe would have destroyed **$8,291,124,113** of real obligations),
`np_schedule_i_grants` (101 → 0) and `contractor_ranking`'s
`operating_company_seq`.

### The merge key that was refused

`131`'s obvious key — `PIID + modification + transaction + agency` — was
rejected. Two of the four fields do not exist on the BGOV side, and
**`funding_agency` must not be in the key**: measured, `piid+fy+uei` leaves 584
BGOV rows ($0.203B) unmatched, while `piid+fy+uei+agency` leaves 40,949 rows
and **$20,739,000,000 double-counted**, purely on `Us Geological Survey`
against `Geological Survey`. `awardee_uei` **is** in the key, because dropping
it wrongly merged 157 rows belonging to a different vendor under one IDV.

### Set-aside is a property of the AWARD, not of the modification

The archive leaves `type_of_set_aside_code` blank on about 56% of rows,
overwhelmingly modifications; the `.dta` carries the award's value on every
row. Read at transaction level the two disagree on **59.4%** of shared FY2022
contracts, and 4,528 contracts the `.dta` calls 8(a) land in "None reported."

Blanks are therefore forward-filled from any non-blank observation of the same
`contract_award_unique_key` across all pulled years — **191,991 awards**. The
window matters and was measured rather than assumed: a 3-year (FY2022–24) map
was **bit-for-bit identical to no fill at all**, while rebuilding FY2023–24
against the 19-year map moved 848 rows out of "None reported", 603 of them into
8(a).

**The residual is recorded, not smoothed: 4,317 contracts the `.dta` calls 8(a)
and the archive reports nothing for, anywhere.** That is why every such column
is named `reported_*`. Net effect on the published statistic: 63.84% → 63.86%
of dollars, +0.02 pp.

### The extent_competed seam: filtering it selects an ERA, not a status

One column held FPDS single-letter codes on some rows and rendered labels on
others, so **any filter on `extent_competed` selected a source vintage rather
than a competition status.**

`CICD_BENCHMARK` named the seam as BGOV-versus-archive and **was backwards**.
Measured: the `.dta` carries **labels** (367,346 plus 9,420 blank, zero codes);
the break is at the **FY2016/FY2017 boundary inside the archive itself** —
`FY2008…FY2016_*_20260806.zip` is 100% codes (367,759 rows) and
`FY2017…FY2026_*_20260706.zip` is labels (473,243 rows, including 1,561 literal
`nan`). The cause is upstream: USAspending's older monthly files put the *code*
in the *description-tag* column.

`code/207_normalize_extent_competed.py` added two columns and **did not touch
`extent_competed`**, which is kept as the evidence of which vintage a row came
from. The crosswalk lives in `code/cedar_extent_competed.py`, quoted verbatim
from **DAIMS-DEC v2.2 (rev 2022-06-03)**,
`https://files.usaspending.gov/docs/Data_Dictionary_Crosswalk.xlsx`, retrieved
2026-08-26, HTTP 200, 110,540 bytes, md5 `0353550157c0c66278f67147ff916d9e` —
**never re-derived from the data**.

`extent_competed_normalized_basis` [measured]: `LABEL_AS_RECORDED` 839,028 ·
`FPDS_CODE_MAPPED` 359,909 · `NOT_REPORTED_BLANK` 9,420 ·
`NOT_REPORTED_NULL_TOKEN` 9,411 · **`UNDEFINED_BY_DICTIONARY` 0**.

Validation: 20 raw tokens, 0 undefined; the coded side uses exactly the
dictionary's nine codes and the labelled side exactly its nine labels. On the
adjacent-year control FY2016 (codes) against FY2017 (labels), the **largest
single-category gap is 1.86 pp** and nothing appears, disappears or halves.

**Refused:** collapsing the nine categories into "competed" / "not competed."
SAP is FAR Part 13 and CDO/NDO is FAR 16.505(b)(1) fair opportunity — that is a
research decision, not a lookup.

**Also refused:** normalising `funding_agency`. 176,973 rows across the two
eras carry an agency rendering the other never produces, and there is no
authoritative code column to normalise against. **Do not join or group on
`funding_agency` across the seam.**

**Not fixed, and worth stating:** `prime_contracts_awards.csv` and
`prime_contracts_published.csv` copy `extent_competed` verbatim from the
award's *first* row, so an award straddling FY2016/17 gets whichever vocabulary
that row used. **Do not compute a competition figure from the award-level
files.** And the `NAN` token also reaches `recipient_state_code` (202 rows) and
`place_of_perform_state`, surviving a `state in (...)` filter as a distinct
category.

### The FY2000 floor is real, not an omission

Coverage begins at FY2000 **because Native identification does not exist in the
pre-2000 federal record at all**, and that was established three independent
ways:

1. **The schema.** FPDS's Native vendor booleans (`isIndianTribe`,
   `isTriballyOwnedFirm`, `isAlaskanNativeOwnedCorporationOrFirm`,
   `isNativeHawaiianOwnedOrganizationOrFirm`) are present in the ATOM schema on
   FY1985 records and carry `false` on **all** of them — while `isSmallBusiness`
   is true on 44% of the same sample. A per-attribute absence, not a blank
   record (`code/563`, run live 2026-09-01).
2. **The publisher's own documentation.** The FPDC Socio-Economic Reports page
   (Wayback `20011107033509`) lists every category the legacy system could
   report — small business, SDB, women-owned, 8(a), very small, HUBZone. **No
   Native, Indian, tribal, ANC or NHO category exists.**
3. **An empirical census.** HigherGov ran the Native filter over the whole FPDS
   corpus and returned **2,607 pre-FY2000 rows starting at FY1989, with
   FY1990–FY1996 completely empty.**

All three of Cedar's extracts together hold 6,816 pre-FY2000 rows worth
$2,611,636,699 — of which **$691.35M is a single manifest error**: two FY1989
McDonnell Douglas rows (PIID F3365781C2108) flagged
`native_american_owned_business = t`. Net of it, FY1979–FY1998 is 451 rows and
roughly $105M over twenty years. CICD's own published series puts 1981–1999 at
**$353,983,469 in 2021 dollars — 0.179% of its own $198B**.

**Ruling: do not backfill FY1981–1999.** `pre_2000_flag` is 0 on all 1,217,768
rows. [measured]

### The entity-year panel had a grain collapse

Measured 2026-08-29: 8,464 rows over 6,713 distinct `(tribe_id, fiscal_year)` —
**1,635 colliding keys** — because three writers keyed on `(tribe_id,
canonical_name, fiscal_year, confidence_tier)`. A `groupby(tribe_id,
fiscal_year).sum()` was always right; a **merge** on those two columns fanned a
buyer's own table out by up to 3×.

Collapsed to a true entity-year grain with tier as *columns*; the two candidate
keys summed to the identical cent. A staleness was fixed in the same pass — 13
buckets existed in the rows and not in the panel, and ANVC village corporations
were $4,729,215.51 short. **Now 6,715 rows, 498 entities, $244,765,639,853.91.**
[measured]

### `40_build_prime_contracts.py` must not be re-run

It rebuilds from the `.dta` and would erase the `131` merge, the 174/427/64
rulings, and the 207/429/430 enrichers. `131` refuses to run twice by design.
**This is why `428` exists as a separate panel rebuilder.**

### The SAM FY2000–2007 pull, shaped end to end by a 10-requests-a-day cap

Confirmed by an HTTP 429 reading `"You can access API after 2026-Aug-13"`. The
socio-economic flags are **output-only** (both return HTTP 400 as search
parameters); the working filter is `awardeeBusinessTypeName`, a **partial**
match. Six variants were pulled.

The partial match is what makes the file interesting. `variant_match_basis`
[measured]: NATIVE_FLAG 166,637 · **SUBCONTINENT_ASIAN_INDIAN_AMERICAN_ONLY
102,587** · HOUSING_AUTHORITY_PUBLIC_TRIBAL_ONLY 87 ·
NO_NATIVE_FLAG_UNEXPLAINED 1. Obligations by class: INDIVIDUAL_NATIVE_OWNED
$22,789,700,022.87, all in the Native universe; ENTITY_OWNED
$17,572,091,629.51, **of which only $6,441,905,593.05 is in the Native
universe** — i.e. **$11.13B of the INDIAN extract is Asian-Indian-American-owned
firms**, caught because *"Subcontinent Asian (Asian-**Indian**) American Owned
Business"* contains the string. **All kept, all flagged, none deleted.**
`include_in_native_universe` is 1 on 166,637 and 0 on 102,675;
`double_count_risk = 1` on 179,050; `class_conflict = 1` on 57,266. [measured]

**A rejected dedup key:** `piid + mod` alone would have collapsed the NATIVE
AMERICAN extract 158,199 → 115,403, **destroying 42,796 distinct
transactions in one file**. The key used is
`subtier|piid|mod|txn|referencedIDVPiid`, **unique on 380,374 of 380,374** raw
rows.

**`AMERICAN INDIAN` is a strict subset of `INDIAN`** (all 52,714 rows) and
contributed **zero** unique transactions. Do not re-submit it.

**The nesting broke the class rule and the rule was left alone.** Of the 57,266
contested transactions, **49,792 (2,272 UEIs, $4,448,849,761) are assigned
ENTITY_OWNED by the substring alone, with no ownership flag.** They are staged
unruled in `review/sam_class_conflicts_<date>.csv`; the merge rule was
deliberately **not** changed to paper over it.

**Licensing travels with the file.** Every row is a base award dated before
2022-04-04, so **D&B Open Data attaches to 100% of it**. Contract facts publish;
legal business name and address do not, in bulk. The `_PUBLISHABLE` twin
withholds exactly the ten `dnb_*` columns.

### The CICD legacy id scheme, and where it does *not* bite

`code/843_retire_cicd_scheme.py` retired the lineage-A Stata integer scheme on
2026-09-01, after its token matcher merged **United Keetoowah Band of Cherokee
into Cherokee Nation — 820 rows, $181,881,441.37, on the token "Cherokee"** —
and filed two county housing authorities as tribes (Tuscarawas Metropolitan
Housing as *"tuscarora tribe"*; Montgomery County Housing Authority as Forest
County, on the token `COUNTY`).

**That defect lives in the funding dataset, not here.** `prime_contracts.tribe_id`
uses only Cedar handles (`TRBF-`, `ANRC-`, `ANVC-`, `AKNF-`) and **no CICD
integer ever entered contracting.** [measured] It is worth stating because the
two datasets share a `tribe_id` column name and a reader could reasonably
assume otherwise.

---

## 5. What a buyer may total

- **`total_obligations` is additive** at row grain across both populations:
  **$310,005,258,660.76** over 1,217,768 rows. [measured]
- **`total_award_value` is restated on every transaction of an award. Take the
  MAX, never the sum.** Summing gives $5,625,791,120,829.37 against a true
  $310.0B. [measured]
- **Deobligations and zeros belong in the total.** **120,943 rows (9.9%) are
  negative and 265,491 (21.8%) are exactly zero.** [measured] Those are real
  actions that moved no money.
- **`prime_contracts_archive_backfill.csv` is the staged half of
  `prime_contracts.csv`.** Every one of its 631,507 rows is also in that file.
  **Never sum the two.** [measured — its $162,480,480,619.39 is exactly the
  FY2008–22 archive slice inside prime.]
- **`contractor_ranking.csv` is a lossless partition of the tier-A slice.**
  `SUM(firm_obligations_usd)` = **$176,743,066,195.69**, equal to
  `prime_contracts.csv`'s tier-A obligations to within **$0.04**. Never sum the
  two together and never union them.
- **Within the ranking, only the `firm_*` family is additive.** Every `owner_*`
  column is an owner-grain attribute repeated on every operating-company row:
  row-summing `owner_obligations_usd` gives **$6,535,955,756,591.51 against a
  true $176,743,066,195.70 — a 36.98× inflation over 283 owners**. `owner_rank`
  is an owner attribute too, and `operating_company_seq` is a **position**
  recomputed on every build — **join on `operating_company_uei`** if you need
  something stable across vintages.
- **A subaward is not additive with a prime.** A subaward is a slice of a prime
  award already counted here.
- **FY2026 carries `deflator_factor_2025 = 1.0`** on all 61,813 rows
  [measured] — *undeflated, not adjusted*. `subawards.csv` and
  `federal_funding_transactions.csv` leave FY2026 **blank**. A buyer summing
  `*_real2025` across the three silently gets FY2026 in one and not the others.
  Open review item `FY2026-DEFLATOR-CONVENTION`.
- **The set-aside share, reproduced:** on the award key `(contract_number,
  awardee_uei)` — not `contract_number` alone, because a PIID recurs across
  vendors and across the DUNS→UEI migration — **$140,003,836,181.83 = 57.20%**
  of the $244.77B attributed, over 317,482 attributed awards. Grouping on PIID
  alone gives $129.82B.

---

## 6. Known limits

- **$65,239,618,806.78 across 328,906 rows is unattributed** and stays that way
  rather than being assigned to a plausible owner. Of it, **$52.06B (262,079
  rows, 9,160 UEIs) has never been ruled on**; only $5.80B is
  `RULED_NOT_NATIVE`; $5.46B is `RULED_CLASS_ONLY` — Native class established,
  owner not in the spine. The highest-value adjudication slice is **$16.99B
  across 65,492 never-ruled rows carrying a Native-preference set-aside**,
  10,877 rows / $720M of which are Buy Indian or Indian Business and therefore
  statutorily Native-only. The largest never-ruled awardee is **The Bahrain
  Petroleum Company** — 40 rows, $990.8M, obviously not Native.
- **The dataset is a lower bound by construction.** The population is the
  ledger's own identifiers, so a Native firm the ledger has never seen is
  invisible. The fix is ledger growth, not a different endpoint. Measured
  separately: **9,719 entities carry a Native business-type flag in FPDS prime
  data that the identifier route has never seen — 76.9% of all flagged
  entities, $70.96B.**
- **Set-aside flags are self-reports**, and only 28.8%–58.4% of attributed
  dollars carry any Native preference in a given year.
- ~~**No NAICS, no PSC, no award description, no action date.**~~ **SUPERSEDED
  2026-09-02, PARTLY — see `docs/PRIME_ATTRIBUTE_REPULL_LOG_2026-09-02.md`.**
  The struck bullet said PSC + description were reachable for **247,987 of
  1,217,768 rows (20.4%)** from the local gapfill zips and that "the other
  79.6% is a genuine re-pull, because `114::release()` deletes each archive zip
  after filtering by design." That was correct. The re-pull was then run:
  `code/1085_prime_psc_desc_repull.py` re-fetched the archive objects (FY2008's
  re-fetch is **byte-for-byte the size `_SOURCE_MANIFEST.csv` recorded**, so it
  is provably the same object) and took four attribute columns off them.

  | column | was | is [measured 2026-09-02T15:38Z, after the COMPLETE 1085 run] | of the 841,002 archive rows |
  |---|---:|---:|---:|
  | `product_or_service_code` | 247,987 (20.4%) | **840,754 (69.04%)** | **99.97%** |
  | `product_or_service_code_description` | 247,987 (20.4%) | **840,738 (69.04%)** | 99.97% |
  | `award_base_description` | 247,987 (20.4%) | **840,079 (68.99%)** | 99.89% |
  | `naics_description` | 247,987 (20.4%) | **827,858 (67.98%)** | 98.44% |
  | `naics_code` (6-digit) | 838,229 (68.8%) | 838,229 (68.8%) — unchanged | 99.67% |

  **All nineteen archive objects are re-fetched and applied, and PSC fill is
  99.7% or better of the archive stratum in every one of FY2008–FY2026.** The
  intermediate 47.1% figures, and the FY2016 4.7% / FY2017 6.8% per-year
  numbers, describe the eight-object partial run and are dead. The eleven
  outstanding objects were fetched 12:12Z–15:09Z on 2026-09-02 at the 480s
  pacing the earlier edge block earned; every year resolved on stamp
  `20260806`, HTTP 200, and **no year was recorded absent.**

  **The 10:45Z apply was reverted before those objects landed**, by
  `871_promote_geo_keys_contracts.py` rebuilding the table at 09:11Z — PSC
  measured back at exactly 247,987 at 15:34Z, and the evidence file
  `prime_contracts.csv.REVERTED_BY_871_2026-09-02_kept_as_evidence` is beside
  the table. Nothing was lost: the attribute files survive a revert and `apply`
  is a pure re-run. **A stale pre-1085 backup was moved aside first**, because
  `verify`'s row/money invariant compares against it and a comparand three
  rebuilds old would have made the check pass on a lie. Rows
  1,217,768 → 1,217,768 and $310,005,258,661.21 → $310,005,258,661.21,
  conserved to the cent, 0 non-blank values overwritten; `verify` exit 0 and
  `selftest` exit 0 with both invariants proven to fire on an injected
  violation.

  **The 68.8% NAICS figure is the structural ceiling for all four columns and
  it is not laziness.** Only **841,002** rows carry
  `contract_transaction_unique_key`. The other **376,766** are BGOV /
  master-prime lineage and **never had one**, because a BGOV row is a
  (contract, parent vehicle, fiscal year, vendor) *aggregate*, not an FPDS
  transaction — there is no transaction for a transaction key to name. No
  re-pull reaches them; that is a merge question, not a column question, and
  `award_attributes_basis` distinguishes the two states per row.
- **`sector` is not trustworthy at ROW grain on the archive stratum, and
  `Not given` is a value it takes.** Added 2026-09-02 by
  `code/1087_prime_naics_sector_conflict_resolve.py`;
  `docs/PRIME_SECTOR_PAIRING_DIAGNOSIS.json` and
  `review/prime_naics_sector_conflicts_2026-09-02_v2.csv` carry it row by row.

  `docs/COLUMN_PROMOTION_LOG_2026-09-02.md` registered **20** rows where
  `sector` disagrees with the archive's 6-digit `naics_code`, "all FY2008, all
  pairing within one PIID with the sectors crossed". Re-measured today:

  - **The pairing hypothesis is confirmed, and provably rather than by
    example.** On every one of the **10** affected
    `(contract_number, fiscal_year, awardee_uei)` groups, the MULTISET of
    `sector` values equals the MULTISET of NAICS-derived 2-digit sectors —
    **10 of 10, zero exceptions.** DABQ0303D0002 FY2008 carries
    `23 23 23 56 56 56 56 56` on both sides, on different rows. So no sector
    VALUE is wrong at contract level; the ROW each landed on is.
  - **The cause is a non-unique merge key, and the exposure is 645× the
    register.** `131_merge_archive_backfill.py` merges on
    `(contract_number, fiscal_year, awardee_uei)`, which resolves **841,002
    archive rows onto 486,889 distinct keys**. **498,533 rows (59.3%)** sit in
    a group with more than one row, and **2,813 groups carrying 12,911 rows**
    hold more than one distinct `sector` — inside those, the sector-to-row
    assignment is arbitrary. **The 20 are the visible subset**, the ones where
    the archive NAICS happens to contradict the assignment. The register is a
    sample, not the set.
  - **There are 22, not 20, and one is FY2010, not FY2008.** The two extra
    carry `sector = 'Not given'` and the registering check compares two-digit
    codes, so it could not see them.
  - **`sector` holds the literal string `Not given` on 19,259 rows (1.58%)** —
    the same sentinel class as `cage_code` holding `nan`. It groups as a
    category. `supersector` carries the matching `Other services or Not given`
    on 35,620 rows. **Filter it before any sector cut.**

  **Nothing was changed.** The repair — `sector = substr(naics_code,1,2)` on
  the 22, and a unique merge key for `131` — is written up and PROPOSED, not
  applied: `950_promote_contract_attributes.py` owns the INV-SECTOR gate and
  that gate fails by design if a registered conflict heals.
- **`contract_number` is not a key.** `0001` alone appears on 11,700 rows and
  **290,525 rows (23.9%) carry a `contract_number` of six characters or
  fewer** — those are FPDS modification PIIDs, meaningless without the
  referencing IDV. `parent_contract_number` is populated on all 1,217,768 rows.
- **Nine CAGE codes are Excel-corrupted at source** (seven with leading zeros
  stripped, two in unrecoverable scientific notation) — flagged, never
  repaired.
- **FY2007 archive is a host edge-block, not an absence**, and is retrievable.

---

## 7. Refresh

| source | cadence | Cedar holds | source has | owed |
|---|---|---|---|---|
| USAspending prime archive | **monthly** (same object set as assistance) | 2026-07-03 | 2026-07-03 | **nothing** |
| SAM.gov Contract Awards API | continuous, but Cedar's use is a one-time FY2000–07 backfill | 2007 | 2007 | nothing |
| FPDS-NG ATOM feed | continuous — **and it retires in FY2026** | — | — | probe only, no production pull |
| CICD published series 1981–2021 | one-time (a 2022-12-21 article) | — | 2021 | closed by design — a **published benchmark**, never merged as a Cedar measurement |

[measured — `docs/REFRESH_CADENCE.json`, regenerated 2026-09-02]

**Probe the archive stamp PER YEAR on the 11th, then re-filter.** A global
stamp constant would both mislabel rows and defeat the guard that stops
FY2023/24 being appended twice.

**What breaks if it is not re-pulled: the archive REPLACES its objects monthly
and does not accumulate.** `FY2016_All_Contracts_Full_20260706.zip` now answers
a real HTTP 404 in half a second. Two vintages are live inside this dataset at
once (`20260806` for FY2008–16, `20260706` for FY2017–26), which is why
`source_file` records the object actually fetched.

**Enrichers run LAST**, always: `207` (extent_competed), `269` (contractor
ranking), `168` (adjudication hubs). `py -3 code/build.py plan contractors`
prints the ordering, and a `.bak_*_pre<script>` file beside a table is the
signal that an in-place enricher has touched it since the last rebuild.

**SAM:** `code/141_pull_sam_contract_awards.py` — *never casually*, 10 requests
a day. The canary is a **separate invocation** that spends exactly one call,
and `extract` exits non-zero until an accepted canary is on record. Two
findings from that leg are worth carrying: **`emailId` is a boolean flag
(`YES`/`NO`), not an address** — an error message naming a parameter tells you
*which* one is wrong, never *what* it should contain — and **the export tokens
expire in roughly 48 hours**, so download the same day you submit.

---

## Stale claims found while writing this

Ordered by how much damage acting on them would do.

1. **`prime_contracts.csv`'s own `source_authority` column mislabels the
   vintage on 473,243 rows.** It reads *"USAspending award_data_archive
   (FPDS-NG static monthly file), stamp 20260806"* on **all 841,002 archive
   rows**, including the FY2017–FY2026 rows that `source_file` shows were read
   from `_20260706` objects. `docs/PRIME_ARCHIVE_PULL_LOG.md` explicitly claims
   *"The stamp is resolved per year from the URL actually fetched, never from a
   global constant."* That is true of `source_file` and **false of
   `source_authority`**. Anyone filtering vintage on `source_authority` gets
   one answer for two vintages.
2. **`docs/PRIME_ARCHIVE_PULL_LOG.md` and `code/114`'s docstring both still say
   the FY2007–FY2022 archive rows are "deliberately NOT merged."** They were
   merged on 2026-08-12 by `131` (826,637 → 1,217,768). Measured: FY2008–FY2022
   carry both populations, and the backfill file is wholly contained in
   `prime_contracts.csv`. `docs/DATASET_CONTRACTS.md` has the corrected rule;
   the two contracting-side docs do not.
3. **`docs/USASPENDING_PROBLEM_BRIEF.md`** still says the 631,507-row backfill
   is "not yet merged", gives prime as 826,637 rows, and says the static
   archive only goes back to FY2008. All three are wrong (merged; 1,217,768;
   the archive reaches FY2007). It carries a warning banner and the body text
   is intact.
4. **`docs/ARCHITECTURE.md` counts LINES, not CSV records.**
   `500_build_architecture_map.py::read_rows()` is `sum(1 for _ in f) - 1`.
   `sam_prime_contracts_fy2000_2007.csv` is **276,261 lines against 269,312
   records** (6,949 embedded newlines). `prime_contracts.csv` and both `fpds_*`
   tables have no embedded newlines and are unaffected. Its contractors table
   is also generally behind: `fpds_uei_cage_map` 24,977 → **34,601**;
   `fpds_uei_edges` 2,290 → **5,167**; `prime_contracts_entity_year` 8,464 →
   **6,715** (the `428` grain collapse). `docs/datasets/02_contracting.md`
   carries the correct figures for all three — prefer it.
5. **`code/79_build_award_level_contracts.py`'s docstring is pre-merge** —
   "617,142 transaction rows → 318,792 contracts." Measured:
   `prime_contracts_awards.csv` and `_published.csv` are **455,080 rows each**.
   `docs/EXTENT_COMPETED_CROSSWALK.md` says those two files are **136,288 rows
   each**, which is also wrong. `code/40_build_prime_contracts.py`'s "617,142
   rows, FY2000-2022" describes the `.dta`, not the shipped table.
6. **The boilerplate Oddities line in every dataset doc — "9.7% of contract
   rows are negative and 9.9% are zero" — is half wrong.** Measured: negatives
   **120,943 (9.9%)**, zeros **265,491 (21.8%)**. The zero share is more than
   double the stated figure.
7. **`docs/datasets/02_contracting.md:7` still says the spine is "687
   entities."** It is **1,555** across 17 classes, and it moved twice during
   the 2026-09-01 pass. The line survives because it sits outside the generated
   block.
8. **`docs/SUBAWARD_API_PULL_LOG.md` and `code/114`'s docstring still cite
   "4,631 keys."** The correct enumeration is **4,597**. The conclusions those
   passages support are unaffected, but citing a retired listing invites a
   settled question to be re-opened on a technicality.
9. **`docs/EXTENT_COMPETED_CROSSWALK.md` records `prime_contracts.csv` as "43
   columns."** It is **47** — `429` and `430` added
   `owner_attribution_status`, `owner_as_of_transaction_cedar_uid`,
   `contract_transaction_unique_key` and `cedar_uid`. Every one of that
   document's twenty raw-token counts and ten normalized counts **reproduces
   exactly**, so the analysis is solid and only the schema line has drifted.
10. **`docs/FPDS_HIERARCHY_BUILD_LOG_2026-08-05.md` is internally
    inconsistent**: its "identifier columns found" table gives File 1 = 476,924
    rows and File 2 = 1,101,796, while its "rows scanned" table gives File 1 =
    1,101,796 and File 2 = 1,078,021. Its **total of 5,167 edges matches the
    live file exactly.**
11. **`docs/INDIAN_INCENTIVE_PROGRAM_GAP.md`** measures against
    `prime_contracts.csv` at 617,142 rows / 34 columns. Today: 1,217,768 / 47.
    Its **$12.10B DoD/Native-flagged eligible-base ceiling will move on a
    re-run**; its conclusion — no Indian Incentive Program field exists
    anywhere in the record — is unaffected.
12. **`docs/datasets/02_contracting.md` (generated 2026-09-01) reports
    `contractors` BLOCKED** on C1/C2/C7 with C4 at 59%. The scoreboard
    regenerated 2026-09-02 rates it **READY**, 10/10 on grain and keys. One day
    stale.

**And what is not stale, worth saying so:** the 2026-09-01 regeneration of
`docs/datasets/02_contracting.md` reproduces every row count measured here
(1,217,768 / 631,507 / 455,080 / 6,715 / 34,601 / 5,167 / 269,312 / 1,429);
`docs/CICD_BENCHMARK.md`'s $140.00B / 57.2% reproduced to
**$140,003,836,181.83 / 57.20%**; and every SAM figure in
`docs/SAM_EXTRACTION_PLAN.md`'s 2026-08-26 section reproduced to the row and
the cent.
