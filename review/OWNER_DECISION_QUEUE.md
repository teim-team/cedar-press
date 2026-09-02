# Owner decision queue — everything waiting on Elijah, one page

*Consolidated 2026-08-30 by the integrator. Each item states the decision, the
evidence already gathered, and what happens on each answer — so a ruling takes
a minute, not an investigation. Newest evidence first. Items are removed when
ruled; new agent proposals should be APPENDED here as well as to their inbox
file.*

---

## 1. BBAHC repoint — evidence complete, sign-off only

**Decision:** repoint the 742 rows unlinked from `ANRC-BRBYCO-00` (Bristol Bay
Native Corporation) to `SGVF-BRSTLB-00` (Bristol Bay Area Health Corporation),
including UEI `NL5HNWNUFMK4`.

**Evidence, all verified:** BBAHC is a tax-exempt Alaska nonprofit, Dillingham
AK, incorporated 1973, website bbahc.org (SAM system of record); across 191
public USAspending transactions it declares **itself** as its own parent — not
BBNC. Your original FA-01 ruling already said they are different entities; the
unlink half is done and propagated to all 10 tables.

**If YES:** rows re-key to the health consortium; dollars move off BBNC.
**If NO:** rows stay unattributed (current state, honest but empty).
File: `review/rulings_inbox_2026-08-29_agent.csv`.

## 2. Blocklisted parents in as-of ownership queries

**Decision:** may a blocklisted parent (e.g. "GOVERNMENT OF THE UNITED
STATES" roll-ups — 78 of 2,684 edges) ever WIN an as-of ownership query, or
must those edges be excluded from resolution entirely?

**Context:** workstream B's temporal layer resolves owners as of the
transaction date. The 78 edges are real declarations but are registrant
roll-ups, not ownership. Current behaviour: they participate.
**Recommendation:** exclude from winning, keep as evidence rows.

## 3. The $2.1B disagreement bucket — how loud should it be?

9,402 transactions ($2.1B) have an as-of owner that **contradicts** the
shipped `cedar_uid`. These are the highest-value review targets in the
temporal work.
**Decision:** (a) queue them all for review, (b) queue only those above a
dollar threshold (say $10M per UEI-year), or (c) hold until more ownership
dates are harvested?
**Recommendation:** (b) — the top slice will concentrate most of the dollars.

## 4. Grain rulings — workstream E's batch is in (9 items, evidence attached)

Full evidence: `docs/GRAIN_AUDIT.md` + `docs/schema/grain_evidence.json`.
Ranked by dollar consequence:

1. ~~**`prime_contracts_entity_year.csv` — ANSWER FIRST.**~~ **ANSWERED AND
   BUILT — no decision needed. Struck 2026-09-01 (workstream H).** The grain
   is entity-year, `428_rebuild_prime_entity_year.py` collapsed the variants,
   and the table is **6,715 rows with 0 literal duplicates** as of
   2026-09-01 (8,464 − 1,751 surplus name/tier variants + 2 new entity-years,
   exact, and the script refuses to write if that arithmetic does not close).

   **The scary half of the original item was also wrong and must not be
   re-inherited:** "anyone summing `obligations_usd` by tribe-year
   double-counts today" was false. Keyed either way the file summed to the
   identical cent; the real harm was **join fan-out** — a buyer merging *their
   own* table on the promised key got up to 3 copies of *their* rows. Fan-out
   is now 1.000×. Acting on the wrong model would have produced a destructive
   de-dupe. See `NEXT_SESSION.md` §3.
2. `fpds_uei_cage_map.csv` — `uei` repeats 11,455×; even
   (uei, cage, source_file) collides 4,680×. One row per UEI, or per
   observation-in-a-source?
3. `foia_request_index.csv` — `foia_request_id` repeats 381×; no key at
   arity ≤ 6. Defective id, or (request × matched entity) grain?
4. `gaming_projections.csv` — the build log's stated grain is contradicted
   by the data (8 collisions of 116). Which column separates them?
5. `ferc_ex_parte_communications.csv` — its own id collides 56×.
6. `contractor_ranking.csv` — only unique with a MEASURE in the key.
7. `tribal_bond_issuances.csv` — `cusip` blank on all 29 rows.
8. `visitor_record_foia_requests.csv` — only free text is unique.
9. Five 0/1-row tables — uniqueness vacuous; declare grain from intent.

## 4b. ~~Fifteen~~ **Thirteen** tables with literal duplicate rows — pipeline defects, not rulings

**CORRECTED 2026-09-01 (workstream H), by re-measuring all thirteen candidate
files rather than re-reading the earlier count.** `prime_contracts.csv` was the
headline entry here and it is **fixed**: 1,217,768 rows, **0 literal duplicate
rows**, because `430_restore_prime_transaction_key.py` restored the
`contract_transaction_unique_key` the mapper had been dropping — the 80,778
were distinct FPDS transactions all along and *not one row was deleted*.
`prime_contracts_entity_year.csv` is likewise clean at 6,715 rows / 0
duplicates. Where this section and `docs/GRAIN_AUDIT.md` disagreed,
**GRAIN_AUDIT was right**; this section was written before the repair landed.

For awareness, not decision (fixes route to the pipelines). Every figure below
was re-measured on 2026-09-01 and matches `docs/schema/grain_evidence.json`
exactly:

| table | rows | literal duplicates |
|---|---:|---:|
| `faads_transactions_all_agencies.csv` | 2,769,748 | 179,259 (6.5%) |
| `subawards.csv` | 72,837 | 10,770 (14.8%) |
| **`cedar_ruling_ledger_consolidated.csv`** | 15,587 | **6,302 (40.4%)** |
| `cedar_identifier_graph_edges.csv` | 46,051 | 2,451 (5.3%) |
| `cross_dataset_ruling_map.csv` | 7,507 | 2,228 (29.7%) |
| `faads_transactions.csv` | 60,661 | 1,001 (1.7%) |
| `ferc_docket_filings.csv` | 102,615 | 822 (0.8%) |
| `native_passthrough.csv` | 1,262 | 114 (9.0%) |
| `np_schedule_i_grants.csv` | 58,685 | 101 (0.2%) |
| `native_bills_subject_sweep.csv` | 2,414 | 5 (0.2%) |
| `lobbying_registrant_native_ownership_evidence.csv` | 27 | 4 (14.8%) |
| `tcu_cdfi_ownership_evidence.csv` | 130 | 4 (3.1%) |
| `hearing_bill_links.csv` | 465 | 1 (0.2%) |

That is **13 tables** by `docs/GRAIN_AUDIT.md`'s count, which includes
`hearing_bill_links.csv`'s single row. Full evidence per table in
`docs/GRAIN_AUDIT.md`; the running defect ledger is `docs/KNOWN_ISSUES.md`.

## 5. Suspect EIN links — 334 rows, from the first second-source harvest

`review/irs_ein_link_queue_2026-08-29.csv`. Six are self-filing entities
whose EIN files as a DIFFERENT organisation (IAIA → IAIA Foundation;
Chugachmiut (AK) → Lakota Language Consortium (IN)); 328 file cross-state;
7 ledger rows store the entity's name where the filer's belongs. These are
link-quality findings — batch-rule or sample-and-rule as you prefer.

## 6. ~~Grain rulings — incoming from workstream E~~ — SWEEP LANDED, nothing incoming

**Closed 2026-09-01 (workstream H).** The sweep this item was waiting on has
run. It tested candidate keys for all 207 undeclared shippable tables against
the FULL file and landed **185 DECLARED_VALIDATED, 12 OPEN_WITH_EVIDENCE, 13
DEFECTIVE, 0 unexplained**. `contract_grain_unstated_shippable` is therefore
**25, not 207**, and the gate's ratchet floor in
`data/clean/_regression_baseline.json` reads 25.

The 12 that need a human are §4 above; the 13 that need a pipeline fix are
§4b. Nothing further is pending from that workstream.
(`federal_funding_transactions.csv` resolved on its own evidence:
`assistance_transaction_unique_key` is unique on all 701,955 rows across the
seam, so the union of the two pulls was not the problem it was expected to be.)

## 7. Standing items from earlier sessions (unchanged)

**Cross-reference added 2026-09-01 (workstream H): the first three items are
the same three tables `62` reports as `tables_undocumented_in_codebook = 3`.**
That metric and this list have been tracking one set of decisions in two places
with nothing connecting them, so the gate line read as an anonymous backlog and
this list read as optional. They are neither: **these three rulings are the only
thing standing between that metric and zero**, and no agent can close them —
each is a publication decision, not a measurement.

- `gaming_property_locations` publishable filter — 2,212 rows, **1,471
  `publishable = Y` / 741 `N`** (re-measured 2026-09-01)
- `consultation_agency_coverage` split decision — 66 rows
- `wa_machine_transfers` empty-or-real decision — **0 rows on disk**, 18 columns
- B&B git-history decision on the PUBLIC repo (accept vs filter-repo)

---

## 8. Correctness pass 2026-08-29 — three items an agent could not close

*Appended by the correctness agent. §4b's "fifteen tables with literal
duplicate rows" is partly ANSWERED below and the answer changes what it is
asking for.*

### 8a. ~~`ship_dist_rows` cannot return to its floor~~ — RESOLVED 2026-09-01, no ruling needed

**Struck by workstream H after re-running the gate: `py -3 code/62_no_regression_check.py`
exits 0 and prints `no regressions`.** Recommendation (b) was taken and then (a):
the allowance was made per-table and consumable, two further defects in it were
found and fixed while doing so (it compared dist-to-dist when the metric sums
`min(dist, clean)`, and `ship_ratio_pct` then failed on the very fall the line
above had just allowed), the correction-register row was written through
`354_correction_register.record()`, and the baseline was recorded **while
green** at `ship_dist_rows = 8,461,252`. No decision is outstanding here. The
reasoning is kept below because it is the clearest statement in the repo of why
a single-use allowance is the wrong shape.

Collapsing `prime_contracts_entity_year.csv` to its true grain removed 1,749
surplus rows (8,464 -> 6,715). The arithmetic closes EXACTLY —
`8,464 − 1,751 surplus name/tier variants + 2 new entity-years − 0 lost =
6,715`, printed on every run of
`py -3 code/428_rebuild_prime_entity_year.py`, which refuses to write if it
does not close or if any entity-year is lost. No entity-year, and no dollar,
left the file.

`62.ship_dist_rows` is MUST_NOT_FALL and it fell 8,463,001 -> 8,461,252, which
is exactly the 1,749. The gate's sanctioned escape is the correction register's
`rows_removed` declaration — but it compares `b - n` against the **sum of every
declared removal ever**, and the register already carries 55 rows from an
earlier episode that the baseline has since absorbed. So the sum is 1,804 while
the fall is 1,749 and can never match. **The mechanism works once.** That is a
gate defect, not a data defect, and it is not an agent's to fix (`62` is
owned).

**Decision:** (a) re-record the gate baseline now that the collapse is verified
and reconciled — the shelf catches up on the next `build.py ship`; or (b) change
the allowance to be per-table and consumable, matching the per-file allowance
that already exists twenty lines further down in the same file.
**Recommendation:** (b), then (a). The per-file form is already written and
already correct.

### 8b. The FAADS duplication is diagnosed but its repair needs a full rebuild

`faads_transactions_all_agencies.csv` — 179,259 literal duplicate rows — is
**not** a page fetched twice. 174,348 of them (97%) come from one staged
object, `ed_fy2007_archive.zip`; 174,957 are FY2007; all carry an
`award_id_fain`; and the staged zip carries
`assistance_transaction_unique_key` and `modification_number` among its 112
columns, neither of which `30_funding_pre2008.to_out_row` was taking. It is the
same projection loss proved exactly for prime contracting, where restoring the
key took 80,778 "duplicates" to **zero without deleting a row or a dollar**
(`code/430_restore_prime_transaction_key.py`).

`to_out_row` and `OUT_COLS` now carry both columns. Repairing the file on disk
needs `py -3 code/30_funding_pre2008.py build`, a full re-extract of a 2.77M-row
shipped table from staged zips, followed by re-running `503_identity.py stamp`.

**Decision:** run that rebuild, or leave the table diagnosed-not-repaired.
**Recommendation:** run it — the staged zips are all on disk, the fix is proved
on the sibling table, and until it runs the readiness scoreboard is blocking
`funding` on a defect that no longer exists in the code.

### 8c. As-of ownership: 81.4% of prime dollars, and what the shelf should do

`code/429_apply_asof_ownership_status.py` now carries the temporal verdict onto
`prime_contracts.csv` and up into the entity-year panel. Measured over
$244.766B of attributed prime obligations:

| status | rows | obligations | may ship a definite owner |
|---|---:|---:|---|
| CONFIRMED_AS_OF | 151,851 | $45.629B | **yes** |
| RESOLVED_OWNER_NOT_IN_CEDAR | 310,421 | $86.086B | no |
| NOT_EVALUATED | 306,626 | $78.830B | no |
| UNKNOWN_OUTSIDE_EVIDENCE | 58,847 | $18.603B | no |
| AMBIGUOUS_OVERLAP | 41,716 | $10.215B | no |
| NO_FACT_ON_SUBJECT | 9,459 | $2.931B | no |
| **CONTRADICTED_AS_OF** | **9,259** | **$2.074B** | **no — §3 above** |
| NO_COVERING_FACT | 608 | $0.333B | no |
| AMBIGUOUS_GRANULARITY | 75 | $0.066B | no |

`tribe_id` / `cedar_uid` are unchanged: they are Cedar's CURRENT attribution and
remain correctly labelled as that. The new
`owner_as_of_transaction_cedar_uid` names an owner ONLY on CONFIRMED_AS_OF and
reads `UNKNOWN` everywhere else — never filled from current ownership.

**Two decisions this raises.**

1. `517_export_safety.py` treats `asof_status == RESOLVED` as definite. It is
   not: of 10,983 RESOLVED cells only 3,669 carry `agrees_with_shipped = 1`;
   410 carry `0` (the layer CONTRADICTS the shipped owner) and 6,899 are blank
   (a parent resolved that Cedar holds no entity for). **517 currently counts
   all 10,983 as safe**, which is how $86.1B came to be reported as confirmed.
   517 is owned and was not edited. **Decision: adopt the three-way split in
   517's own counts.**
2. `contractor_ranking.csv` — the most owner-centric customer-facing table,
   1,429 rows, `owner_entity_id` + `owner_obligations_usd` — still carries no
   status. It is rebuilt wholesale by `269_build_contractor_ranking.py`, a
   PHASE 1 rebuild with unattributed enricher backups already sitting beside
   it, so it was not rebuilt at the end of a session. `269` reads
   `prime_contracts.csv`, which now carries the status per row, so the roll-up
   is a small change to that script. **Decision: schedule the 269 rebuild.**

---

## 9. The spiderweb harvest — three batches, ranked, evidence attached

*Appended 2026-09-01 by workstream J (`code/523_spiderweb_harvest.py`). Every
row below is **tier B**: a FAR 4.18 / 52.204-17 declaration is evidence of a
declared connection, never proof of Native ownership. Nothing here mints a
spine entity.*

**What changed underneath first.** `13_build_fpds_hierarchy.py` was reading 6
of the 40 files on disk that carry a parent-UEI column. Reading the other 34 —
the FY2007-FY2026 USAspending contract archive, the 2023-2026 assistance
pulls, the assistance subawards, the gapfill universe — took 1.2 minutes and
no network calls, and moved the declared-edge list from **2,901 to 5,167**.
The three batches below are drawn from the larger file.

### 9a. 78 firms declared into a known entity's family — RULE THESE FIRST

**Decision:** for each firm, does it belong in the named entity's corporate
family (a tier-B ownership relationship in the ledger), yes or no?

**Evidence per row:** the literal declared edge, its observation count and
year span, the source extract, the firm's dollars and dataset presence.
File: `review/523_spiderweb_ownership_candidates.csv`, `unambiguous = Y`,
sorted by `priority_rank` — 163 rows over 78 firms and 56 entities,
$0.62B of observed obligations. The top of the queue:

| rank | entity | firm declared into it | obligations |
|---:|---|---|---:|
| 1 | Rocky Boy's Chippewa Cree | STONE CHILD COLLEGE CORPORATION | $88.1M |
| 2 | Hawaiian Native Corporation | GSI PACIFIC INC. | $158.2M |
| 3 | Southern Plains ITO | CENTRAL OKLAHOMA AMERICAN INDIAN HEALTH | $83.2M |
| 4 | Tlingit & Haida | KIRA TRAINING SERVICES LLC | $128.8M |
| 5 | Tlingit & Haida | KIRA AVIATION SERVICES LLC | $40.4M |
| 6 | Kalispel | KAUFFMAN & ASSOCIATES, INC. | $97.3M |
| 7 | Koi Nation | NTVI ENTERPRISES, LLC | $44.8M |
| 8 | Northern Cheyenne | CHIEF DULL KNIFE COLLEGE, INC | $17.4M |

**If YES:** the firm's UEI enters `cedar_identifier_ledger_final.csv` at tier B
with the declaration as evidence; its obligations become attributable.
**If NO:** the row is a tier-X refutation and the declaration stops being
re-proposed every pass.

*`unambiguous` deliberately EXCLUDES single-observation declarations. One
filing is not a pattern: OKLAHOMA STATE UNIVERSITY MEDICAL AUTHORITY declares
CHOCTAW NATION OF OKLAHOMA as its parent on exactly one 2026 row, and it is
not a Choctaw subsidiary.*

### 9b. 246 UEIs that are entities we ALREADY hold — a ledger backfill, not new firms

**Decision:** approve the batch, or require row-by-row sign-off?

This is the biggest single finding of the pass. 258 declared edges are not
ownership at all — they are **one registrant filing under two UEIs**, or a
Cedar entity's own top-level UEI missing from the ledger. `13` drops a
self-edge only when the two UEI strings match, so a renewed or reassigned UEI
survives as a "parent" and reads as a holding company.

    COOK INLET REGION INC        S2SVA1GNRVK5  ->  ANRC-CKINLT-00   $133.2M
    NANA REGIONAL CORPORATION    RA4LQVFLCQC6  ->  ANRC-NANARC-00    $32.8M
    KONIAG, INC.                 DRDKNY4L1T33  ->  ANRC-KONIAG-00    $12.4M
    GOLDBELT, INCORPORATED       P9QQX7RT8E98  ->  ANVC-GLDBLT-00    $11.5M

File: `review/523_identifier_backfill_candidates.csv`. **251 undisputed, 7
disputed** (the declared name resolves to a DIFFERENT spine entity than the
edge's keyed end — those need a ruling, not a batch approval). Two evidence
kinds are kept apart on purpose: `identical_declared_name_on_the_same_edge` is
within-row string equality and carries no spine lookup, while
`matches_the_keyed_entitys_own_spine_name` is a name match against the spine
and is exactly how BRISTOL BAY AREA HEALTH CORPORATION was keyed to the ANCSA
regional. **Review the second kind; the first is safe to batch.**

**If YES:** ~246 UEIs key to entities Cedar already holds — the cheapest
coverage rise available.
**If NO:** they keep arriving as "new holding companies" every pass.

### 9c. 73 existing ledger links this harvest REFUSED to build on

**Decision:** these are not new claims — they are links already IN the ledger
that the harvest declined to inherit from. Rule them, or leave them standing?

`AKNF-INPTBW-00-ARCSLO` (Barrow) holds **103 UEIs, 58 of them `cluster_v3`
"Algorithmic name clustering, unreviewed"**, and the cluster matched on the
word **GOVERNMENT**:

    Ho'olaulima GOVERNMENT Solutions     A+ GOVERNMENT Solutions
    ATI GOVERNMENT Solutions             GOVERNMENT & Industrial Supply
    Qayaq GOVERNMENT Solutions           GOVERNMENT Technical Services
    Koman Propper GOVERNMENT Apparel     Computer Sciences Corporation

Barrow's real subsidiary is UIC **Government** Services LLC. Two more of the
same shape: `KLAMATH 9-1-1 EMERGENCY COMMUNICATIONS DISTRICT` keyed to the
Klamath Tribes and `COUNTY OF MOULTRIE` (Illinois) keyed to Forest County
Potawatomi — the Tuscarawas precedent, a place named for a tribe is not the
tribe.

File: `review/523_suspect_keyed_anchors.csv` — 73 links over 43 entities, each
with its ledger method, its rationale, and the token sets that do and do not
overlap. **The harvest hangs nothing from any of them.**

**If these are wrong:** they are already carrying dollars in shipped tables.

---

## 12. Nonprofits — the 990 mission text says WHY each row is here (shard J, 2026-09-01)

Your question: *"does it say it's native focused in the description... do we have
nonprofits that we know have a reason to be on the master list?"* Yes, and the
corpus was already on disk. `code/541_shard_j_mine_990_mission_text.py` reads
**10,651 local IRS 990 XML returns** (471 MB, no download) and pulls each
filer's `MissionDesc`, `ActivityOrMissionDesc`, `PrimaryExemptPurposeTxt` and
every program-service `Desc`. **4,296 of the 12,764 np_orgs EINs** have a local
return; of the 4,122 whose BMF tier is `full_990`/`990_EZ`, **4,105 (99.6%)** are
already here, and only 12 are absent from the IRS index entirely.

**The answer, as a histogram of `inclusion_basis` (ADR-013), over 4,296 EINs:**

| basis | EINs | what it means |
|---|---:|---|
| `placename_only` | **2,653** | the mission has NO Native word at all, and the row is here because a name token matched |
| `no_native_signal` | 948 | no Native word and no place-name explanation either |
| `subject_classification` | 419 | Native-focused, names no entity |
| `native_serving_not_native_controlled` | 15 | Native people named alongside an explicit broad, non-Native constituency |
| `named_entity` | **132** | the mission names a specific nation or Cedar entity |
| `program_authority` | 49 | ISDEAA / IHS / NAHASDA / ICWA / BIE named in the filing |
| `geographic` | 44 | reservation, trust land, ANCSA region — no nation named |
| `no_mission_text` | 36 | filed (mostly 990-PF) with no mission narrative |

**62% of the nonprofit rows that have a 990 carry no Native word anywhere in
their own mission statement.** That is the size of the place-name defect,
measured for the first time from the organisations' own filings rather than
from their names.

### 12a. The 412 tier-A rows — DECISION: bulk-rule the 21 that state a non-Native purpose

The doc says 412; the file says **697** `confidence_tier = A` rows are
`classification_ruling = UNRULED` (`docs/datasets/06_nonprofit.md` line 26 is
stale). **293 of the 697 have a local 990.** They split:

| basis | n | settleable now |
|---|---:|---|
| `placename_only` | 214 | **21 at `high`** — the filing names a plainly non-Native purpose |
| `subject_classification` | 24 | 9 at `high` |
| `named_entity` | 22 | 9 at `high` |
| `no_mission_text` | 22 | — |
| `geographic` | 7 | — |
| `program_authority` | 4 | 1 at `high` |

The 21 `placename_only / high` rows are the cheapest rulings available. Each
one's own 990 states what it is:

    MOHEGAN FIRE COMPANY INC              "TO PROVIDE VOLUNTEER FIRE AND AMBULANCE SERVICE TO THE COMMUNITY"
    MOHEGAN VOLUNTEER FIRE ASSOCIATION    "...SERVICES TO THE LAKE MOHEGAN, NEW YORK DISTRICT"
    LAKOTA AMBULANCE SERVICE INC          "AFFORDABLE RURAL AMBULANCE SERVICE TO NELSON [COUNTY]"
    APACHE AMBULANCE SERVICE INC          "ambulance service to Town of Apache and surrounding area"
    PEQUOT LIBRARY ASSOCIATION            "...A COLLECTION OF RARE BOOKS, MANUSCRIPTS, AND ARCHIVES"
    JEMEZ VALLEY CREDIT UNION             "...MEMBERS AT LEGITIMATE RATES OF INTEREST"
    PAWNEE CITY PUBLIC LIBRARY FOUNDATION "A STRONG PUBLIC LIBRARY IS THE FOUNDATION..."
    LENAPE VALLEY YOUTH BASEBALL AND SOFTBALL, MOJAVE RIVER ACADEMY SCHOOLS,
    COMMUNITIES IN SCHOOLS PUYALLUP, THE CHEHALIS FOUNDATION, SHOSHONE PROJECT INC,
    SHOSHONE MEDICAL CENTER FOUNDATION, BANNOCK YOUTH FOUNDATION, COQUILLE STUDENT
    LOAN FUND, FRIENDS OF PAWNEE BILL RANCH, CHRISTMAS IN ACTION WICHITA TX,
    CENTRAL DAKOTA ENTERPRISES, DON SHERWOOD ENDOWMENT (ROTARY),
    MOHEGAN VOLUNTEER EXEMPT FIREMENS BENEVOLENT ASSOCIATION

**If YES:** 21 tier-A rows are ruled `place_name_coincidence` on the strength of
the filer's own words, and the tier-A revenue aggregate stops being unquotable
for those rows.

**One to pull out before you sign:** `ROSEBUD ECONOMIC DEVELOPMENT CORP` lands in
this band on the phrase "Rosebud Chamber of Commerce". Rosebud, Texas has one
too, and the text does not settle which Rosebud this is.

The remaining 184 tier-A `placename_only` rows are `medium` (no Native word, but
no affirmative civic purpose either) and 9 are `low` (the filing says "our
culture / our people", so the org may BE the nation talking about itself —
**deliberately not settled**).

Full evidence with quotes: `data/staging/np_mission/inclusion_basis.jsonl`.

### 12b. The mint proposal — 644 candidates, and only 90 are actually mints

`data/staging/np_mission/mint_proposal.csv`, ranked strongest basis first. Every
row carries the verbatim quote and the source XML path.

| proposed action | n |
|---|---:|
| **KEY BY BASIS, do not mint** (no entity is named; the basis IS the claim) | 512 |
| **MINT** as a new nonprofit entity, keyed to the nation it names | 90 |
| **ATTACH EIN to an entity already in the register** — do not mint a duplicate | **42** |

The 42 are the immediate win: organisations already in the 1,555-entity register
whose EIN is simply not attached — Oglala Lakota College, National Indian Health
Board, Native American Rights Fund, Lac Courte Oreilles Ojibwe University and
School, Council for Native Hawaiian Advancement, Fresno American Indian Health
Project, Indian Health Board of Minneapolis, United Tribes Technical College,
California Rural Indian Health Board, Northwest Portland Area Indian Health
Board, Great Plains Tribal Leaders Health Board, and 31 more.

**Recommendation on the architectural question:** do **not** mint ~11,300
nonprofits into a 1,555-entity register. Mint the 90, attach the 42, key the
other 512 by `inclusion_basis` alone, and leave the ~11,300 out. Reasoning is in
the shard report; the short version is that the register has no entity class
that fits a nonprofit, and 11,300 rows of `subject_classification` would swamp
the 1,555 governmental and institutional entities 8:1 while adding no identity
that ADR-013's basis key does not already carry.

### 12c. DECISION: `entity_aliases.csv` holds 104 alias rows that are single English words

Measured while building the matcher. **Every one of the 104 `alias_type='brand'`
rows is a single token**, and among them:

    advantage  applied  ancillary  corporate  cultural  door  feet  field
    fire  indigenous  link  managed  media  nexus  peak  program  research

`cultural` resolves to Southern Ute (`TRBF-STHUTE-00`). `indigenous` resolves to
Delaware Nation (`TRBF-DELAWN-00`). This is the Enterprise Rancheria defect
(`docs/NATIVE_ENTITY_NUANCES.md`) living in the brand registry, and any matcher
reading the alias layer without knowing it will key half a corpus. 541 refuses
all 104 and names each one; nothing else in the repo does.

Two more measured while matching, both worth a rule rather than a patch:

* **"Solo" must be counted on DISTINCTIVE tokens, never on total tokens.**
  *Fond du Lac* is three tokens but only one distinctive one — it keyed the Fond
  du Lac Yacht Club, Rotary Club Charities, County Farm Bureau Cooperative, High
  School Hockey, Volleyball Club, Historical Society, Concert Association and
  nine more Wisconsin civic bodies to the Minnesota Ojibwe band. Tuscarawas,
  wearing a longer name so it clears a token-count guard.
* **The apostrophe must be deleted in normalisation, not spaced.** Spacing it
  turns "St. Mary's" into three tokens, which lets a two-token name pass a
  three-token confidence test: PEORIA SYMPHONY ORCHESTRA keyed to St. Mary's
  (Algaaciq) off the words "ST. MARY'S CATHEDRAL" in a concert-venue list.

**Decision:** withdraw the 104 brand aliases from `entity_aliases.csv`, or retype
them so no matcher can read them as entity names? Shard J did not touch the file.

### 12d. What else the local corpus connects to — measured, not built

| source | volume, local | connects dataset 6 to |
|---|---:|---|
| **Schedule C** lobbying and political activity | **860 returns, 415 EINs (361 of them in np_orgs)**; 222 501(h)-electing and 245 non-electing; $6.14M lobbying by np_orgs filers; **314 narrative blocks / 166 KB of free-text lobbying description**; 124 returns declaring direct contact with legislators, 37 declaring rallies | **dataset 4 (lobbying)** — and it captures advocacy the LDA never sees |
| **Schedule I** grants made | 1,490 returns, 63,628 grant blocks, 60,353 recipient EINs, 89,168 purpose statements | **dataset 3 (funding)** — largely already built: `np_schedule_i_grants.csv` holds 58,685 rows |
| Officers | 141,654 person blocks | governance structure only — **not publishable as a roster** |
| Mission narrative, whole corpus | 10,391 of 10,651 returns carry it | the basis layer above |

Schedule C was the one worth extracting, and it is extracted:
`data/staging/np_mission/schedule_c_lobbying.csv`, 860 rows, grain = one filed
return (a few EIN-years appear twice where the IRS index holds two object_ids
for one period — de-duplicate on `(ein, tax_period_end)` before summing).

**A defect for whoever owns `code/99_build_earmarks_and_schedc.py`:** it already
appends 30 `schedc_*` columns to `np_financials.csv`, but records
`schedc_present = 1` on only **93** rows with a lobbying total of **$82,303**.
Two causes, both measurable here: it reaches a narrower slice of the corpus than
what is on disk, and it reads only the 501(h) `...Grp` shape, so the **245
non-electing filers** who report a flat `TotalLobbyingExpendituresAmt` are read
as zero. That is an undercount, not a coverage limit.

**One limit worth stating plainly:** `native_serving_not_native_controlled` is
assigned to only 15 organisations, and that is a property of the source, not of
the classifier. **A Form 990 does not disclose who controls the filer.** The
tier is assigned only where the filing itself states a broad non-Native
constituency; absence of the tier is never evidence that an organisation IS
Native-controlled. Separating Native-controlled from Native-serving needs a
governance source — bylaws, a tribal charter, a board roster — not the 990.

---

## Do the 30 pre-1907 Osage rows belong in the natural-resources ledger?

*Appended 2026-09-01 by workstream O, after your "1880? What data goes that far
back lol". The question was right. The fields are already fixed; this is the
scope call, and it is genuinely arguable, so it is yours.*

**Decision:** keep the 30 rows for 1880–1906 in `data/clean/resource_revenue.csv`,
or move them out of the natural-resources dataset.

### What is already done, so this is not urgent

The rows were stamped `commodity = "Osage Mineral Estate (oil, gas, sand and
gravel, water use)"` and `land_status = trust`, with confidence **A** on four of
them. The Mineral Estate was created by the **1906 Osage Allotment Act**, and
the first Osage oil lease of any kind was the **Foster lease of 1896-03-16** —
so for 1880–1895 Cedar was asserting oil revenue from an estate that did not
exist. **Corrected**: commodity blank, `resource_type = not_stated`,
`land_status = not_stated`, `revenue_type = trust_disbursement`, all 30 demoted
to **B**, and the sourced explanation carried in `beneficiary_note`. Nothing
deleted — row count unchanged at 11,305.

### What the payments actually were

Louis F. Burns, "Osage", *Encyclopedia of Oklahoma History and Culture*,
Oklahoma Historical Society, entry OS001 — the Osage Trust Estate *"came from
treaty settlements, land sales from the Kansas Reservation, and accumulated
interest on money held in trust by the United States"*; *"Income mainly from
grazing leases caused the commissioner of Indian affairs to call the Osages 'the
richest people on earth'"*; and decisively, *"**Petroleum income did not become
a monetary factor until after Osage allotment in 1906–1907.**"*

Your own prior — trust interest on the Kansas land-sale proceeds — is **the
larger half of the right answer**. The source adds grazing income, which
complicates it: grass-lease income *is* resource revenue. The published figure
is one number covering both and nothing apportions it, so Cedar does not.

### The two answers

**KEEP THEM IN** (current state). They are one continuous series that the Osage
Minerals Council publishes as one table, 1880–2032. Splitting it across two
Cedar tables hides the seam from anyone reading only one of them. The corrected
fields already make the block excludable with a single predicate —
`resource_type = 'not_stated'` or `commodity = ''` — so a subscriber charting
resource revenue drops them automatically.

**MOVE THEM OUT.** The **BTFA precedent points this way and it is squarely on
point.** BTFA was deliberately kept out of this ledger because Interior's own
description makes royalties one of six ingredients: *"Trust funds include
payments from judgment awards, settlements of claims, land-use agreements,
royalties on natural resource use, other proceeds derived directly from trust
resources, and financial investment income."* A pre-1907 Osage payment is that
same mixture. If BTFA is scale context rather than a series, consistency says
these are too.

**If MOVE:** they leave `resource_revenue.csv` and land in a
`data/clean/` sibling for pre-estate distributions, or in `review/` as context.
Cost: the published series gains a 1907 floor and the seam has to be documented
in two places instead of one. About an hour, and it is reversible.

Evidence and both arguments in full:
`docs/datasets/natural_resources_sources.md`, "The pre-1907 classification
correction". Code: `code/83_build_resource_ledger.py`, `_osage_period_fields`.

### 12e. The Fond du Lac token bug, measured against the live resolver — 66 contradictions, and Umatilla Electric is still one of them

Follow-up after the lobbying workstream adopted the brand-alias guard (12c).
The second defect in that list is **not** fixed and it is the more dangerous
one. `data/staging/np_mission/resolver_exposure.csv`, produced by
`py -3 code/541_shard_j_mine_990_mission_text.py --resolver-exposure`, which
calls `503.resolve()` **read-only** and writes only into staging.

**Why a second test was needed.** `503`'s loose path wins on *"the spine
entity's distinctive tokens are a subset of the filed name"*, and its two
guards — `ADMIN_GEOGRAPHY` and `CIVIC_FORM` — are **denylists of words**:
COUNTY, YACHT, ROTARY, GOLF, LIBRARY. A denylist can only refuse a civic form
somebody already thought of. It catches `FOND DU LAC YACHT CLUB`. It does not
catch `ENVISION GREATER FOND DU LAC`, `FOND DU LAC FESTIVALS INC` or
`FOND DU LAC ADULT LITERACY SERVICES INC`, because no word in those names is on
either list. The guards are also blind to the shape itself: *Fond du Lac* is a
two-token distinctive set that is **entirely a Wisconsin city name**, so every
organisation in that city satisfies the subset test.

**The mission text is the orthogonal test, and it runs the other way round.**
Instead of asking whether the filed NAME looks civic, it asks what the
organisation says it does. Crossed over the 830 np_orgs organisations that
`503` keys *and* that have a local 990:

| what the filing says | 503 keys it | 503 does not |
|---|---:|---:|
| `placename_only` | **562** | 2,091 |
| `no_native_signal` | 69 | 879 |
| `named_entity` | 74 | 58 |
| `subject_classification` | 74 | 345 |
| `geographic` | 18 | 26 |
| `program_authority` | 17 | 32 |

The 562 are a screen, not a verdict — a tribal government's own 990 often
says "services to our members" and names no Native word at all, so silence
proves nothing. **The defensible subset is the 66 where the filing states an
affirmative non-Native civic purpose**, over **25 spine entities**:

    UMATILLA ELECTRIC COOPERATIVE ASSOCIATION -> TRBF-UMATLL-00
        "UMATILLA ELECTRIC COOPERATIVE IS A MEMBER-OWNED ELECTRIC UTILITY
         THAT SELLS ENERGY AND OTHER SERVICES..."
    ONEIDA-MADISON ELECTRIC COOPERATIVE INC   -> TRBF-ONDANY-00   electric cooperative
    ONEIDA HEALTHCARE SYSTEMS INC             -> TRBF-ONDANY-00   101-bed acute care hospital
    SENECA HOSE CO NO 1 INC                   -> TRBF-SNCNAT-00   volunteer fire company
    SENECA VOLUNTEER AMBULANCE SQUAD          -> TRBF-SNCNAT-00   ambulance, Seneca IL
    SOUTH ONONDAGA FIRE DEPARTMENT INC        -> TRBF-ONNDGA-00   fire department
    TAOS VOLUNTEER FIRE DEPARTMENT INC        -> TRBF-TAOSPB-00   volunteer fire
    PUYALLUP EDUCATION ASSOCIATION            -> TRBF-PUYLLP-00   teachers' association
    WASHOE EDUCATION ASSOCIATION              -> TRBF-WASHOE-00   Washoe County School District
    WYANDOTTE EDUCATION ASSOCIATION           -> TRBF-WYNDTT-00   Wyandotte public schools
    TUSCARORA TOWNSHIP VOLUNTEER FIRE ASSOC   -> TRBF-TSCARA-00   volunteer fire
    SPORTING WICHITA INC                      -> TRBF-WKWTOK-00   youth soccer club
    ST LUKES HEALTH FOUNDATION OF SIOUX CITY  -> SGVF-NDNHLT-00   regional medical center
    SHEPPTON ONEIDA VOLUNTEER FIRE CO, SENECA ROCKS VFD, SENECA VALLEY
    FOUNDATION, SOUTH SENECA AMBULANCE CORPS, CHEROKEE PASS FIRE DISTRICT,
    SEMINOLE TRAIL VOLUNTEER FIRE DEPARTMENT, ROSEBUD COMMUNITY HOSPITAL, ...

Concentration: Seneca Nation 9, Wichita 6, Cherokee Nation 5, Tuscarora 5,
Mohegan 4, ND Native Health 4, Oneida NY 4, Puyallup 4, Klamath 3, Onondaga 3,
Wyandotte 3, Osage 2.

**`UMATILLA ELECTRIC COOPERATIVE ASSOCIATION` is the $592M leak named at the
top of `docs/datasets/06_nonprofit.md`, and `503.resolve()` still returns
`TRBF-UMATLL-00` for it today** — reason string *"gov-class distinctive-token
match on 'Umatilla Tribe', unique"*. The doc records the symptom; this is the
first measurement of the mechanism still being live in the resolver.

**Decision, three options:**

1. **Feed the 66 to `503` as declared exclusions** (`RESOLUTIONS` entries, the
   TUSCARAWAS pattern). Smallest change, fixes exactly these, fixes nothing
   else — a hand list, which is what the 2026-09-01 guards were written to
   replace.
2. **Add a shape rule to the loose path** — refuse when the spine entity's
   distinctive-token set is entirely a US settlement name and the filed name
   contributes no Native term. This is the general fix and it reaches
   `ENVISION GREATER FOND DU LAC`, which no denylist will.
3. **Let evidence beat the name.** Where Cedar holds the organisation's own
   990 and it states a non-Native purpose, that outranks any name match. This
   is the strongest and it is the only one that scales, because the corpus is
   already on disk for 4,296 of the 12,764.

**Recommendation: 3, with 2 as the fallback where no 990 exists.**
Shard J did not touch `503` — it is another workstream's file and the guard
belongs with its owner, exactly as the brand-alias fix did.

---

## 13. Wire CICD's published figures in as STANDING GATE ASSERTIONS (shard-N, 2026-09-01)

**Decision:** approve (or amend) three checkable assertions so the CICD
benchmark stops being re-derived every session and starts failing a build when
Cedar silently loses data. `docs/CICD_BENCHMARK.md` already computes the
comparison; what does not exist is a **gate** that goes red. A gate that knows
Cedar's FY2000–2021 deflated prime total should sit near $190B catches a
1.2M-row table losing a fiscal year, which no lint class can see.

**Why now.** You measured Cedar against your own CICD benchmark and got
"$164.9B against ~$200B". That comparison is invalid as stated and this session
established why: three of the four axes differ. Deflated to 2021 dollars using
the table's own `deflator_factor_2025`, Cedar's FY2000–2021 attributed prime is
**$189.99B against CICD's $198B prime — −4.05%, inside the CORROBORATED band.**
The nineteen missing fiscal years are worth roughly **$2B nominal**, not $35B.
Full working and per-source coverage table: `docs/datasets/02_contracting.md`
§COVERAGE.

### Proposed assertions

| id | assertion | source, with year | current value | proposed tolerance |
|---|---|---|---|---|
| `CICD-A1` | Cedar's attributed prime obligations for FY2000–FY2021, expressed in **2021 dollars**, are within 10% of **$198B** | CICD, *Federal contracting's expanding revenue role in Indian Country*, 2022-12-21 — *"$202 billion in revenue (in 2021 dollars) … $198 billion from prime contracts and $4 billion from subcontracts"*, 1981–2021 | **$189.99B** (−4.05%) | ±10%. A one-sided floor is wrong here: Cedar going far ABOVE $198B would mean the attribution has started over-claiming, which is the failure this project most needs to catch. |
| `CICD-A2` | `prime_contracts.csv` holds **every fiscal year FY2000–FY2026 inclusive**, none with zero rows, and `min(fiscal_year) == 2000` | Cedar's own documented boundary — the FY2000 floor is now sourced, not accidental | FY2000–FY2026, 1,217,768 rows, no gaps | exact. This is the cheap one and it is the one that would have caught a lost year. |
| `CICD-A3` | DoD share of Cedar's attributed FY2000–2021 obligations is within 10% of **67.6%** | CICD, *Native entities and the federal contracting landscape*, 2023-06-21 | 63.76% (−5.7%) | ±10%. Currently typed UNEXPLAINED at 5%; at 10% it is a gate rather than an open question, and the open question stays in `CICD_BENCHMARK.md` where it belongs. |

**Deliberately NOT proposed as assertions:**

- *"~$200 billion in the last decade"* (2026-08-24). It is prime **plus** sub,
  and Cedar's subaward layer is a known floor — FY2021–24 hold 173/89/120/166
  rows against ~5,000/yr either side. An assertion whose input is broken tests
  the input, not the claim.
- *"$26.6 billion in 2025."* CICD's 2025 is calendar-year and Cedar's is fiscal;
  the quarter of difference falls in a rising series, and USAspending back-fills
  obligations for months after year-end. Two moving parts, no signal.
- Anything counting **contracts**. `SANITY-04` is still UNEXPLAINED: no Cedar
  award key reproduces CICD's 50,167 (parent PIID 15,985 · PIID 173,716 ·
  PIID+UEI 221,058) and CICD does not state its key. Do not gate on a number
  whose grain is unknown on both sides.

**If YES:** the three land in `docs/ASSERTION_LAYER.md` with source and year,
and `62_no_regression_check.py` (or whichever gate you prefer) gains a class
that goes red on a silent data loss. **If NO:** they stay as prose in
`CICD_BENCHMARK.md` and every future session re-derives the comparison, which
is how "$164.9B vs $200B" got stated as a shortfall in the first place.

**Second question, and it is one only you can answer.** `CICD-A1` depends on a
deflator. Cedar uses `deflator_factor_2025` (FY2000 = 1.77359, FY2021 =
1.170557). **CICD's 2022 article does not state which index it used.** You
built that dataset — was it CPI-U, the GDP implicit price deflator, or
something else? If the two indices differ, the −4.05% is partly an artefact of
the comparison itself and `CICD-A1`'s tolerance should widen.

---

## 14. The $65.2B unattributed pool — ranked, characterised, NOT attributed (shard-N, 2026-09-01)

**Not a decision — a worklist**, filed here because the ranking materially
changes what `503`/`510` should do next and because the headline number has
been quoted without its decomposition.

328,906 rows / **$65.24B** sit at tier C with `attributed_flag = 0`. Every row
carries a UEI; 105,688 carry a CAGE. Split by `ruling_status`:

| ruling_status | rows | obligations | distinct UEI | what it means |
|---|---:|---:|---:|---|
| **(never ruled)** | 262,079 | **$52.06B** | 9,160 | nobody has looked |
| `RULED_NOT_NATIVE` | 34,140 | $5.80B | 139 | correctly excluded, will never attribute |
| `RULED_CLASS_ONLY` | 28,940 | $5.46B | 34 | **Native, owner not in the spine** |
| `RULED_HOLD` | 914 | $0.80B | 17 | held |
| `RULED_OWNER_NOT_IN_SPINE` | 1,789 | $0.47B | 6 | owner identified, entity absent |
| `RULED_TIER_UNSTATED` | 936 | $0.38B | 29 | tier missing on the ruling |
| `RULED_TIER_C_NOT_ATTRIBUTED` | 96 | $0.27B | 1 | |
| `RULING_CONFLICT` | 12 | $0.001B | 3 | |

**79.8% of the money has never been ruled on. Only 8.9% has been ruled NOT
Native.** "Unattributed" has been reading as "rejected"; it means "unexamined".

**Where to start, and it is not the top of the dollar list.** The best signal is
a never-ruled row that carries a **Native-preference set-aside**: $16.99B across
65,492 rows. Inside that, **10,877 rows / $720M sit on Buy Indian or Indian
Business set-asides, which are statutorily Native-only** — an unattributed row
on one of those is a near-certain Native entity awaiting a name, and it is the
cheapest yield per ruling in the whole pool.

**It is a long tail.** 11,857 distinct never-ruled awardee names; the top 50 are
only 22.1% of the money. There is no top-20 sweep that closes this.

**Two cautions, both load-bearing.**

1. The pool contains obvious non-Native rows. The single largest never-ruled
   awardee is **`THE BAHRAIN PETROLEUM COMPANY BSC (CLOSED)`, 40 rows /
   $990.8M**, with no Native set-aside on any of them. Do not read $65.2B as
   latent Native dollars.
2. `RULED_CLASS_ONLY` at $5.46B on **34 UEIs** is the concentrated, tractable
   slice — Cedar already knows this money is Native and cannot name the owner.
   34 owner determinations move $5.46B. That is the highest dollars-per-ruling
   in the table and it needs entity work, not a filter.

Ranking, ready to work: `data/staging/pre2000_probe/unattributed_ruling_dollars.json`
(`never_ruled_top_50_awardees`) and `benchmark_reconciliation.json`
(`top_60_awardees_by_obligation`). Produced by `code/564` and `code/565`, both
read-only. **Shard-N attributed nothing and touched no ruling.**

### AMENDMENT to item 13, same session — CICD publishes its series year by year, and it changes the assertions

The 2022 article prints charts, not tables. **The complete year-by-year series
is in the page's `__NEXT_DATA__` payload** — `docs/HIDDEN_DATA_TECHNIQUES.md`
item 2, applied to a research article. `code/567` extracts it, validates it
against the article's own headline (three entity series sum to **$197.987B**
against the stated **$198B**, 0.007% off), and stages it at
`data/staging/cicd_published/cicd_prime_series_1981_2021.csv`.

That makes `CICD-A1` far sharper than a 41-year total, and it produces a
finding worth more than the assertion:

| window | CICD (2021$) | Cedar attributed (2021$) | delta |
|---|---:|---:|---:|
| 1981–1999 | **$0.354B** | $0 (Cedar holds no rows) | −$0.354B |
| FY2000–2007 | $32.508B | $24.858B | **−$7.644B, −23.53%** |
| FY2008–2021 | $165.124B | $165.131B | **+$0.007B, +0.004%** |
| FY2000–2021 | $197.633B | $189.989B | −3.87% |

**Two things follow and both matter more than the gate.**

1. **CICD's own 1981–1999 total is $354M — 0.179% of its own $198B.** 1982–1987
   and 1989 are literally zero in CICD's published data. The "nineteen missing
   years" are not a hole worth chasing; they are a rounding error, and this is
   the incumbent's own number saying so.
2. **The entire −$7.6B is FY2000–FY2007.** From FY2008 the two builds agree to
   four decimal places, which is the strongest external corroboration Cedar
   Press has ever produced about itself.

**Amended `CICD-A1`, proposed:** assert against **CICD's published FY2000–2021
subtotal, $197.633B**, not the 41-year headline, and split it —
`CICD-A1a` FY2008–2021 within **±3%** of $165.124B (currently +0.004%, so a 3%
band is a real gate rather than a decorative one), and `CICD-A1b`
FY2000–2007 within **±30%** of $32.508B (currently −23.53%, and tightened to
±10% once item 15 lands). Splitting matters: on the combined window a fixed
FY2000–2007 and a newly broken FY2008–2021 would cancel and the gate would stay
green.

---

## 15. FY2000–FY2007 is short by 23.5% and the fix is a file already on disk (shard-N, 2026-09-01)

**Decision:** authorise the **date-gated merge of HigherGov `Data Request
4-5-2023 File 2.csv`**, or rule that it stays out and Cedar publishes
FY2000–2007 as a known 23.5% floor.

**The measurement.** Cedar is within ±7% of CICD in every fiscal year from
FY2008 and short by **16–35% in every one of FY2001–FY2007**. FY2000–2007:
Cedar $24.858B against CICD $32.508B, **−$7.644B in 2021 dollars**.

**The cause is a selection-doctrine failure, and `docs/PULL_DISCIPLINE.md`
predicts this exact shape.** FY2000–FY2007 has exactly one source:
`master prime file.dta`, which is HigherGov **File 1 — the flag-at-award leg
alone**. File 1's 78,267 pre-2007 keys match the clean table's 78,267 exactly,
so nothing was lost in ingestion; the leg was simply never joined to its
partner. **File 2, the SAM-registration leg, has never been merged into
anything** and carries **26,240 net-new pre-2007 keys worth $7.93B nominal**
against a measured shortfall of $7.65B in 2021 dollars. Those are not proven to
be the same dollars and nothing here should be written as if they were — but
one leg run alone for eight years, costing about a quarter of the money, is
precisely what the selection doctrine says happens.

**Why it has not been done, and why that is right.** File 2 matches on
*current* registration. Its author flagged the defect unprompted in 2023:
*"it will pick up awards for companies before they were acquired (e.g., it
would pick up all of Vistronix's awards before ASRC Federal bought them)."*
ASRC is also the largest tier-A net-new entity in the file at $1.32B. Merged
naively, File 2 books a firm's pre-acquisition revenue to the tribe that later
bought it — a false attribution that would look impeccably sourced. **File 2 is
not a merge; it is a merge plus an adjudication**, date-gated against
`ownership_events.csv`, with rows preceding an acquisition held at tier B or
excluded and flagged.

**If YES:** FY2000–2007 closes toward CICD and `CICD-A1b` tightens to ±10%.
**If NO:** FY2000–2007 is published as a stated floor, and the −23.5% goes in
the codebook rather than being discovered by a reader with CICD's article open.

Evidence: `data/staging/cicd_published/cedar_vs_cicd_by_year.csv`;
`docs/datasets/02_contracting.md` §COVERAGE; `docs/PRE2007_SPENDING_SOURCES.md`
Part 2. **Shard-N merged nothing and attributed nothing.**

---

# 16. THE `review/` BACKLOG, RANKED — first whole-directory sweep (int-3, 2026-09-01)

*Full triage: `docs/REVIEW_BACKLOG.md`. Machine-readable: `data/staging/review_backlog_triage.csv`.*

**364 CSV files, 138 MB, and no gate has ever counted them.** Swept whole for
the first time today. The counts:

| bucket | files | rows |
|---|---:|---:|
| PROMOTABLE NOW | 3 | 374 |
| **NEEDS AN OWNER RULING** | **104** | **185,340** |
| SUPERSEDED (flag, never delete) | 27 | 13,452 |
| DIAGNOSTIC ONLY | 230 | 182,633 |

**The finding is that `review/` is mostly NOT a backlog.** 63% of it is the
project's evidence layer — refusal logs, coverage audits, series-break
registers, probe outputs. Those are marked so nobody triages them again.

What is left is **eleven questions**, below, in the order that disposes of the
most rows per answer.

> ## STATUS, updated 2026-09-01 after the owner changed the standing rule
>
> The owner, same day: *"I don't care about you listing issues, you decide how
> to fix them. The only thing I should need to adjudicate is uncertain native
> entities — but even then you can review websites and SAM or annual reports as
> long as you document the decisions and learn from them."*
>
> **Nine of the eleven are now DECIDED.** Write-up with the evidence behind each:
> **`docs/REVIEW_BACKLOG_RULINGS.md`**. Per-row dispositions:
> `data/staging/review_backlog_class_dispositions.csv` (15,911 rows) and
> `data/staging/master_queue_identifier_adjudication.csv` (579 rows). Four new
> numbered rules went into `docs/ENTITY_MATCH_RULES.md` as rules 7–12 so the
> next thousand rows are cheap.
>
> | still yours | why it was not decided |
> |---|---|
> | **16.11 vendor-list consent** (62 rows) | Not a method question. It is a decision about Cedar's relationship with the nations whose lists these are, and the one failure mode that would damage this project's standing rather than its accuracy. Recommendation below unchanged. |
> | **16.5 OSHA** (711 establishments / 1,879 filings) | Owned by INT-1, handed over with the evidence. |
>
> **Nothing was applied to a shipping table.** Every decision is a disposition
> with its evidence attached; applying them to the ledger or the spine is a
> separate, reversible pass that must run against a green gate.

Every item is an attribution, a tier promotion or a scoping call, and Cedar's
standing rule remains that only tier A publishes.

---

### 16.1 — THE IDENTIFIER-GRAPH SCOPING DOCTRINE · unblocks **102,051 rows** across eight `523_*` files

**The question, asked once:** *how far down the unkeyed-identifier ranking does
Cedar key, and on what evidence?*

**The evidence.** `523_idgraph_q3_unkeyed_by_dataset_count.csv` ranks **90,539
unkeyed identifier nodes carrying $506.5B observed**, by how many datasets see
them. The distribution is extremely thin at the top: only **346 nodes appear in
2+ datasets and 22 in 3+**, and the **top 100 alone carry $17.4B**. Alongside it
sit 9,814 name clusters (q2), 708 split-entity suspects (q4), 200 co-occurrence
rows (q1), 300 ownership candidates, 258 backfill candidates, 159 candidate
firms and 73 suspect anchors.

**Recommendation — a THREE-LINE doctrine, not 90,539 decisions:**

1. **Key the top 100 by observed dollars, by hand.** $17.4B, one sitting.
2. **Auto-key nothing below `n_datasets >= 2`** (346 nodes). One dataset seeing
   an identifier is one source's spelling, not corroboration.
3. **The rest are a stated coverage floor**, published in the codebook as
   "N identifiers observed and not keyed", never as an implied zero.

**A caution on the two candidate files inside this group.**
`523_spiderweb_ownership_candidates.csv` (300 rows, $2.28B observed) rests on
**SAM-declared parent/child edges** — an identifier relationship the registrant
filed, which is the strong form, and 22 rows are both `rule_first` and
`unambiguous`. `523_identifier_backfill_candidates.csv` (258 rows, $851.7M) does
**not**: 216 of its rows rest on `identical_declared_name_on_the_same_edge` and
42 on `matches_the_keyed_entitys_own_spine_name`. Both are name equality,
narrowed by an edge but still name. **Rule the 300 before the 258, and rule them
by different standards.**

---

### 16.2 — THE ADJUDICATION-HUB PARTY METHOD · unblocks **15,999 rows** across seven files

**The question:** *may a party named in an IBIA/IBLA decision, a FERC docket or
an ex parte filing be linked to a Cedar entity by the resolver's proposal alone,
and if so at what tier?*

**The evidence.** `168_link_adjudication_hubs.py` produced a proposed entity for
every one of these and then correctly refused to write any of them:
`168_admin_appeal_unresolved_parties` 4,642 · `168_ferc_unresolved_parties`
4,058 · `168_ferc_ex_parte_unresolved` 2,419 · `admin_appeal_unresolved_organisations`
4,289 · `admin_appeal_entity_link_candidates` 420 · `168_foia_link_audit` 166 ·
`168_resource_revenue_ceiling` 5. Every one carries an empty `YOUR_RULING`.

**Recommendation:** rule the METHOD, at **tier B**, and only where the party
name matches a spine canonical name *and* the docket state matches the entity
state. A docket party is a legal filing, so the name is the party's own — but it
is still a name, and `UMATILLA ELECTRIC COOPERATIVE` resolved to a tribe by
exactly this route until a guard went into `503_identity.py` today.
**Start with `168_resource_revenue_ceiling` — 5 rows, and it tests the doctrine
for the price of a coffee.**

---

### 16.3 — THE SELF-CERTIFICATION CEILING · unblocks **15,557 rows**

**The question:** *does a SAM `awardeeBusinessTypeName` Native flag ever get a
firm into the Cedar universe on its own, and at what tier?*

**The evidence.** `esm_native_entity_candidates_2026-08-12.csv` holds **12,645**
federal recipients carrying such a flag, with dollars, transaction counts and an
`evidence_grade`; `sam_individual_native_candidates_2026-08-26.csv` holds a
further **2,912**. `docs/INDIVIDUAL_NATIVE_CLASS_PROPOSAL.md` §4 already puts
the ceiling at **tier C**, and tier C never publishes alone.

**Recommendation:** **confirm tier C as a hard ceiling and close both files as
a stated universe floor.** A self-certification is the registrant's claim about
itself, and Cedar's premise is that it does not republish claims as facts. The
promotable thing here is the *aggregate*, and that is now done — see
`data/clean/sam_native_class_distributions.csv`, promoted today, which is
aggregate-only and small-cell suppressed.

---

### 16.4 — DOES A TEXT MENTION MAKE IT THAT ENTITY'S COMMENT? · unblocks **4,806 rows**

**The evidence.** `regulations_gov_comment_candidates.csv`: 4,806 regulations.gov
comments where a Cedar entity is named in the comment TEXT but not in the title.
`data/clean/regulations_gov_comments.csv` currently ships **172 rows, all
`TITLE_NAMES_THE_ENTITY`** — the text-mention class is excluded on purpose.

**Recommendation: NO — keep them out of the comment table**, and instead ship
the count as a `mentions` measure on `regulations_gov_entity_coverage.csv`. A
comment that criticises a tribe mentions it as loudly as one filed by it, and
the table's unit of analysis is *the tribe speaking*.

---

### 16.5 — OSHA GAMBLING ESTABLISHMENTS · unblocks **711 establishments / 1,879 Form 300A filings**, plus 1,852 more

**HANDED TO INT-1, who owns the labor promotion.**

**The evidence.** `employment_osha_unmatched_2026-08-07.csv` — 711 establishments
whose `n_filings` sum to exactly **1,879** — held because each *"shares a
distinctive token with a Cedar property but no exact name+state match"*
(e.g. `Pearl River Resort, Choctaw MS`, 3,233 employees, token `pearl`).
`YOUR_RULING` filled on **zero** of 711. The later, wider
`osha_gambling_unresolved_2026-08-26.csv` holds 4,560 rows of which **2,708
already carry a blocking verdict** and **1,852 are genuinely open**.
`data/clean/gaming_employment_observations.csv` already holds 874 OSHA rows, so
this is an extension of a live table, not a new one.

**Recommendation:** rule the two files TOGETHER — they overlap — and rule the
*rule*, not the rows: **a shared distinctive token is not a match.** Accept only
`name + state + NAICS 7132xx/7211xx` exact, and publish the remainder as a named
coverage gap.

---

### 16.6 — THE MASTER QUEUE, NEVER OPENED · unblocks **6,559 rows, $82.1B at stake**

**The evidence.** `MASTER_QUEUE_2026-08-07.csv` — 6,559 ranked entity questions,
each with `dollars_at_stake`, an evidence URL and a written question.
**`YOUR_RULING` is filled on ZERO of them.**

> **CORRECTION, same day, against my own earlier figure.** An earlier draft of
> this item said the `_already_ruled_removals/` corpus overlaps this file "by
> exactly 1". **That was wrong and it was wrong for the reason this project
> keeps writing down: the join key was blank.** 2,443 of the 6,559 rows carry an
> EMPTY `identifier` column, so joining on it matched almost nothing and
> reported a queue as wholly unseen. The UEI is present — inside the free-text
> `question` — and read from there the real overlap is **223 rows carrying
> $10.8B of the $82.1B, 3.4% already ruled**. Six of the top fifty by dollars
> are already-ruled rows still sitting here with an empty `YOUR_RULING`,
> including `SAN CARLOS APACHE TRIBAL COUNCIL` ($847M), `LUMMI INDIAN BUSINESS
> COUNCIL` ($696M) and `HOOPA VALLEY TRIBE` ($495M), all removed from the live
> queue on 2026-08-26. **The MASTER QUEUE is partly stale and does not say so.**

**Recommendation:** do not attempt it as a queue. **Sort by `dollars_at_stake`
and rule the top 50** — the ranking exists precisely so the tail never has to be
read — then close the rest into 16.1's stated floor.

**DONE, 2026-09-01.** All 50 adjudicated by `code/604_adjudicate_master_queue_by_identifier.py`
— 23 ACCEPT, 18 REFUSE, 6 ALREADY_RULED, 2 HOLD, 1 FLOOR, none left open. See
`docs/REVIEW_BACKLOG_RULINGS.md`.

---

### 16.7 — 1,223 PROPOSED TIER B → TIER A PROMOTIONS

**The evidence.** `entity_key_tierB_promotion_queue_2026-08-06.csv`: dataset,
source name, proposed tribe, row count and basis, per row.

**Recommendation: rule by BASIS, not by row.** Group the 1,223 by the `basis`
column, rule each basis once, and let the ruling fan out. **THE FIVE THINGS
THAT WILL BITE YOU #1 applies here in full:** the exactness of a key says
nothing about the correctness of a link, and 821 tier-B `need_v6` rows are
6.5% accurate.

---

### 16.8 — 1,049 NAGPRA ALIAS PROPOSALS

**The evidence.** `nagpra_alias_proposals.csv`, written today by script 77 —
proposed aliases harvested from NAGPRA notices, with notice counts and an
example document. `YOUR_RULING` empty on all 1,049. Precedent: of the earlier
recognition-alias pass, **76 of 228 proposals were dropped on review** — a 33%
reject rate, so these cannot be auto-applied.

**Recommendation:** rule only aliases seen in **3+ notices** and reject the
long tail. An alias is an identity assertion about a tribe; a one-notice
spelling is a typesetter, not a name.

---

### 16.9 — 6,796 UNRESOLVED CONGRESSIONAL EARMARK RECIPIENTS

`earmark_unresolved_2026-08-07.csv`, with amount requested, amount enacted and a
source URL per row. Recipient names are as printed in the committee table.
**Recommendation:** same doctrine as 16.2 — name + state exact, nothing else,
remainder published as a floor.

---

### 16.10 — 6,094 SUBAWARD PARTIES (2026-08-28 API route)

`subaward_api_unresolved_2026-08-28.csv`, each with a proposed `tribe_id`,
canonical name, `resolver_how` and confidence tier. **Supersedes** the 4,254-row
`subaward_matches_2026-08-07.csv`, which is recommended for `graveyard/`.
**Recommendation:** rule by `resolver_how`, one ruling per resolver.

---

### 16.11 — THE 62-TRIBE VENDOR-LIST REGISTRY: A CONSENT RULING, NOT AN EFFORT ONE

**This one was nearly promoted and should not have been.** It reads like a
finished registry of tribal vendor and ownership-certification lists — verdicts,
URLs, entry counts, formats. Re-measured 2026-09-01:

- **`publishable = N` on all 62 rows**
- **`consent_status = UNRESOLVED` on all 62 rows**
- 8 rows `TERMS_STATED_RESTRICTIVE`, 2 `ROBOTS_DISALLOW`
- every row carries a `suppression_key`
- and it is **live** — `570_shard_l` and `571_shard_m` wrote it today

**The question:** may Cedar publish the *existence and location* of a tribe's
own published vendor list — a fact about a public website — when the site terms
are restrictive or silent and no tribe has consented?

**Recommendation: split it.** Publish the *verdict* (`LIST_FOUND_PDF`,
`NO_LIST_FOUND`, …) and the *URL*, which are facts about a public page; publish
**no harvested list contents** from any of the 8 restrictive or 2
robots-disallowed hosts without written consent. That converts 62 rows from
`publishable = N` to a shippable coverage table without touching a single
harvested record.

---

**Rows these eleven rulings would unblock, in total: ~155,000 of the 185,340
sitting in the NEEDS AN OWNER RULING bucket.** The remaining ~30,000 sit in 93
smaller files, each listed with its own one-line reason in
`docs/REVIEW_BACKLOG.md`.


---

## 10. Nonprofits — shard-I harvest — 2026-09-01

*Appended by workstream SHARD-I. **Nothing below has been applied.** No `tier`, no `classification_ruling`, no spine row and no `np_orgs.csv` cell was written. Every quote is a literal substring of bytes retrieved and kept on disk under `data/staging/np_harvest/raw/`.*

### 10a. FIRST — the `412` in the dataset doc is not a measurement

`docs/datasets/06_nonprofit.md` says *"412 tier-A rows are awaiting a ruling."* That number is a **hardcoded string literal** in `code/24_generate_dataset_docs.py` (~line 506). It is not computed from `np_orgs.csv` and it does not move when the data moves. `docs/FACT_CHECK_2026-08-06.md` B-25 already flagged it as wrong once.

**Measured against the live file today:**

| | rows |
|---|---:|
| `confidence_tier = A` | 712 |
| …of which `classification_ruling = UNRULED` — **the real backlog** | **697** |
| …in shard-I's strata (`990_N` / `not_required_to_file` / `UNKNOWN`) | 480 |
| …in shard-J's strata (`full_990` / `990_EZ`) | 217 |

**Decision:** may the doc generator compute this figure from the data instead of carrying a literal? **Recommendation: yes.** A hardcoded count in a maintenance doc is a fact with no error term — it cannot be wrong loudly, only quietly. The same applies to the `$592M` / `$497M` figures in the same bullet, which the fact-check also found stale.

### 10b. Tier-A ruling evidence — 480 organisations, split four ways

Shard I fetched each organisation's **own website** and recorded what it says it is. `resolves_to` is an evidence-backed candidate label. **It is not a ruling and must not be applied as one.**

| `resolves_to` | orgs | what the evidence is |
|---|---:|---|
| `native_entity` | **4** | the org's own page asserts a Native control or charter relationship |
| `placename_only` | **35** | the org's own page describes a member-owned, county or denominational body with no Native content |
| `native_serving_not_native_controlled` | **19** | Native language, but no control, charter or ownership asserted |
| `undetermined` | **422** | no readable page — see 10c |

File: `data/staging/np_harvest/tier_a_ruling_evidence_shard_i.csv` — one row per organisation, with the quote, the source page and the raw bytes path.

**Strongest `native_entity` evidence** (own words):

| EIN | organisation | the organisation's own sentence |
|---|---|---|
| 311328543 | ZUNI CHRISTIAN MISSION SCHOOL | "By God’s grace, what began in 1897 as pioneer mission work of the Christian Reformed denomination, has matured into a ministry that is governed by local boards of Zuni Christians—an unparalleled accomplishment in mission efforts among the Pueblo tribes of the…" |
| 933214988 | NISENAN MIWOK COLLECTIVE | "Jane Rey at Frank’s Exchange Who We Are The Nisenan Miwok Collective 501(c)(3) is the nonprofit arm of the Southern Hill Nisenan Tribal community." |
| 331174840 | LIPAN APACHE TRIBE OF TEXAS INC | "[] The Lipan Apache Tribe of Texas is a historical Native American tribe, and the 501c(3) Lipan Apache Tribe of Texas, Inc, is an instrumentality of the tribe, not the tribe itself." |
| 910891385 | TLINGIT AND HAIDA INDIANS OF ALASKA-WASHINGTON CHAPTER | "In 1912 the Alaska Native Brotherhood (ANB) was founded by Tlingit, Haida and Tsimshian leaders who united to work to correct the injustices experienced by Alaska Natives throughout the Territory of Alaska." |

**Strongest `placename_only` evidence** — the Umatilla Electric shape, recommended for demotion out of tier A:

| EIN | organisation | revenue on file | what its own site says it is |
|---|---|---:|---|
| 852069418 | APACHE LEAP MEDIA | — | Z89.3 & 101.5 HD3 KZAO |
| 860828870 | PARTNERS FOR PAIUTE NEIGHBORHOOD CENTER | — | Partners for Paiute \| Community assistance |
| 873791650 | CAHUILLA ELEMENTARY PARENT TEACHER ORGANIZATION | — | Charity \| Cahuilla Elementary PTO \| Palm Springs |
| 800302641 | MOJAVE ARCHERS | — | Mojave Archers |
| 330964160 | MOJAVE RIVER VALLEY HORSEMENS ASSOCIATION | — | MRVHA \| Horse Shows & Events in Apple Valley |
| 920435652 | MOJAVE TRAILS OUTREACH & FOOD PANTRY | — | Mojave Trails Outreach & Food Pantry |
| 922962028 | MON PETIT MOJAVE FOUNDATION INC | — | Mon Petit Mojave |
| 272857715 | STRAIGHTWAY M B C OF MOJAVE | — | Straightway MBC of Mojave |
| 222523902 | MOHEGAN & PEQUOT MODEL RAILROAD CLUB INCORPORATED | — | Mohegan Pequot Model Railroad Club Inc. |
| 222720928 | PEQUOT CYCLISTS INC | — | Pequot Cyclists |

**`native_serving_not_native_controlled`** — the distinction the 990s are worst at, and the reason a website pass was worth running. Serving is not control; the doc's own Jemez Mountains Electric note is the precedent.

| EIN | organisation | the sentence that carries Native language |
|---|---|---|
| 453844277 | OGLALA PET PROJECT | "Oglala Pet Project (OPP) is a 100% volunteer driven, community based 501(c)3 non-profit organization located on the Pine Ridge Indian Reservation in South Dakota." |
| 462925916 | ZUNI PUEBLO MAINSTREET | "How are you doing these days?) Zuni Pueblo became the first Native American community to be designated as a MainStreet Community in the United States in July of 2012." |
| 920124517 | ALEUT FOUNDATION | "Looking ahead, Mei hopes to become a physician serving underserved communities, especially Indigenous populations." |
| 884129140 | APACHE KNIFE FOUNDATION | "[] Tci-He-Nde, Western Apache people, Fort Apache Indian Reservation, San Carlos Apaches, the Chiricahua Apache Nation, Ndee, Nde, GoFundMe, fundraising, Charity, New Charity, Apache Coffee, Apache, Robert Redfeather, Redfeather, Chiricahua…" |
| 881907630 | CHEEE FOKAA BAND OF NORTHEASTERN POMO | "Chhé’ee Ti’dóo (Salt Spring Valley) Our Mission History Get Involved ﻿ Contact Us Our Mission — Chhé'ee Fókaa Band of Northeastern Pomo 0 Skip to Content Our Mission Our Language History Get Involved Contact Us Open Menu Close Menu Our Miss…" |
| 364896186 | SANTA YNEZ CHUMASH OCEANOGRAPHIC INSTITUTE | "Facing Uncomfortable History: Native American Boarding Schools An introduction to forced assimilation in Native American boarding schools." |
| 841432104 | FRAY ANGELICO CHAVEZ CHAPTER GSHA- PUEBLO | "About Home Events About Publications FACC Library Videos Contact Links Photo Gallery Menu FACC-GSHA Home Events About Publications FACC Library Videos Contact Links Photo Gallery The Fray Angelico Chavez Chapter (FACC) is a non-profit organ…" |
| 237171302 | MOHEGAN STRIDERS ASSOC | "Chief Harold Tantaquideon, direct descendent of Uncas, Chief of the powerful Mohegan Nation, joined retired sports writer John DeGange in this unique honor." |

**Decision:** apply these as rulings in bulk by `resolves_to`, or read the quotes row by row? **Recommendation: bulk-apply `placename_only` where the page is substantive and carries zero Native language** (that is a strong negative and it is where the tier-A revenue leak lives), and **read `native_entity` row by row** — a promotion is the expensive direction to get wrong.

### 10c. The finding that decides whether the rest is worth attempting

**392 of the 480 tier-A organisations in shard-I's strata are UNREACHABLE BY WEBSITE** — they supplied no website on their e-Postcard and Cedar holds no e-file return for them. There is no page to read, so `undetermined` here means *no instrument existed*, not *the evidence was ambiguous*.

This generalises. Measured on the **whole** `990_N` population rather than a sample, from the IRS e-Postcard bulk corpus (one request, 93 MB, `Last-Modified 2026-08-31`):

| stratum | rows | found in e-Postcard | carry a website | **website hit rate** |
|---|---:|---:|---:|---:|
| `990_N` | 6453 | 5573 (86.4%) | 1329 | **20.6%** |
| `not_required_to_file` | 2060 | 96 (4.7%) | 17 | **0.8%** |
| `UNKNOWN` | 129 | 18 (13.9%) | 8 | **6.2%** |

**And a website FIELD is not a website.** The funnel, every rung measured:

| rung | orgs |
|---|---:|
| organisations in shard-I's strata | 8,642 |
| carry a non-blank website field | 1,476 |
| the field actually parses as a URL | 1,019 |
| the host answered 2xx | 864 |
| the page carried an evidence-bearing sentence | 251 |
| **the page asserted Native CONTROL** | **15** |

Every no-content outcome is NAMED rather than left blank — 51 dead DNS, 40 TLS failures, 79 fields that were not URLs (`N/A` is the commonest value), 36 pages that served bytes but yielded no extractable text. *(shard H's rule: a truncated or script-rendered read must report why, never a bare negative. Zero reads hit the size cap this run.)*

**Robots audit** (prompted by shard H losing 22 hosts to a phantom block): this shard never used `urllib.robotparser`. `robots.txt` is fetched by curl with the **same UA** used for content and any non-200 yields an EMPTY rule set, i.e. ALLOWED. All **11** hosts recorded `ROBOTS_DISALLOW` were re-audited against their saved `robots.txt`: **11 genuine, 0 phantom** (six are `facebook.com`). No organisation was written off as closed because our own check lied.

**No domain was guessed.** Every URL probed came from the filer's own IRS return. Shard H's finding that a guessed domain returning 200 is fabrication with a status code next to it does not bite here because no candidate was ever generated from an organisation name.

**Decision:** are the remaining `990_N` organisations worth pursuing? **Recommendation: no further web sweep, and here is the arithmetic.** About four in five postcard filers publish no website at all; of the ones that do, roughly 14% of the pages fetched were dead, parked or refused. A second sweep buys a small number of thin pages at a large number of requests. **The cheap remaining routes are not web routes**: state charity registries (bulk, free, and they carry a purpose statement), and the group-exemption parent, which names the affiliation directly. Both are Tier-1 in `docs/PULL_DISCIPLINE.md` terms — bounded objects, not per-org fetches.

### 10c-bis. The structured-endpoint pass paid for itself, and here is the number

`docs/HIDDEN_DATA_TECHNIQUES.md` was adopted mid-run. It matters most for exactly this population: **635 of 831 sites had a RENDERED page too thin to decide anything from.**

| technique | sites where it produced data |
|---|---:|
| `meta_opengraph` | 669 |
| `feed_link_rel` | 293 |
| `wp_json_advertised_by_link_rel` | 219 |
| `jsonld_schema_org` | 195 |
| `data_attributes` | 108 |
| `wp_json_inferred_from_wp_content_paths` | 28 |
| `embedded_app_state_present` | 24 |
| `select_option_vocabulary` | 17 |
| `html_comment_carrying_native_language` | 4 |
| `published_google_sheet` | 4 |

Reading the structured routes out of bytes ALREADY retrieved cost **zero extra requests**. A bounded second pass then called 683 documented public endpoints (`/wp-json/wp/v2/pages`, `/wp-json/wp/v2/media`, `/feed/`) across 270 organisations and returned **2,419 PDF-library items, 1,261 feed items, 31 annual reports and 84 newsletter PDFs** — and added evidence on **55 organisations whose rendered page carried none at all.**

Worked example: **Samish Neighborhood Association** rendered a near-empty shell. `/wp-json/wp/v2/pages` returned 17 pages of text and the media library listed 64 documents — enough to resolve it, and it resolves to `placename_only`. The technique that produced the data is recorded per site in the `evidence` field, as the doc requires.

**Boundary, asserted not merely intended:** only documented public endpoints were requested. `structured_probe.py` carries a `FORBIDDEN` regex covering `/wp-admin`, `/admin`, `/.env`, `/.git`, `/staging`, backups and dumps, and it *raises* rather than skips. Nothing behind a login, no robots `Disallow` path, no `TERMS_STATED_RESTRICTIVE` source.

### 10c-ter. Newsletters — where small Native nonprofits actually publish

140 organisations probed, 127 readable. Channel counts:

| channel | orgs |
|---|---:|
| `facebook_only` | 77 |
| `wordpress_blog` | 54 |
| `own_site` | 22 |
| `mailchimp` | 20 |
| `wix` | 19 |
| `squarespace` | 10 |
| `constant_contact` | 1 |

**`facebook_only` is the largest single channel.** That is a finding for the funding and deals datasets: a bulletin that never leaves Facebook is invisible to every route Cedar currently runs, and `facebook.com/robots.txt` disallows `/` for `*`, so it is not harvestable. Depth and cadence are recorded; archives were NOT downloaded. File: `data/staging/np_harvest/newsletters_shard_i.jsonl`.

### 10d. `filing_req_cd = 14` is a 51-row seam the doc says is invisible

The dataset doc warns that *"tribal instrumentalities largely DO NOT file 990s (IRC §7871) — the LARGEST tribal institutions can be invisible here."* True in general. But **BMF `filing_req_cd = 14` is the governmental-instrumentality code, and 51 `np_orgs` rows carry it** — the instrumentalities that hold an EIN anyway. They include San Carlos Apache College, Seneca Nation Library, Seneca Nation of Indians Economic Development Company, Cherokee Nation Education Corporation, Kickapoo Nation School and Quileute Tribal School. They also include County of Apache and Indian River State College, so it is a seam, not a whitelist.

**Decision:** should `filing_req_cd = 14` become a named review stratum? **Recommendation: yes** — 51 rows is a one-sitting adjudication and it is the densest concentration of genuine tribal institutions anywhere in this dataset. Relatedly, **1,491 of the 2,060 `not_required_to_file` rows are churches** (`filing_req_cd = 06`), which the doc already excludes in principle but which still sit in the row count.

### 10e. 4,362 candidate nonprofit→spine links — record or mint?

**This is the architectural question and it is yours, not an agent's.** `data/spine/cedar_identity_register.csv` has 17 entity classes and **no nonprofit class**, while `np_orgs.csv` holds 12,764 organisations of which 1,423 (11.1%) carry a `cedar_uid`.

Shard I found that **every one of the 6,646 unkeyed `tribe_id_token_match` values resolves exactly to an existing `spine.handle`** — 4,362 of them in shard-I's strata. So the links are mechanically available today.

**They should not be minted, and the harvest is the reason why.** Of the candidates where a website could be read, **434 were CONTRADICTED by the organisation's own site** and only **6 were corroborated**. A token match is the Umatilla Electric shape: `PENOBSCOT COUNTY CONSERVATION ASSOCIATION` token-matches `TRBF-PNBSCT-00` and is a Maine sportsmen's club.

**Decision, three options:**

1. **Mint a `Native nonprofit` entity class and key all ~11,300.** Fast coverage; imports every place-name false positive into the master list, where `START_HERE.md` standing rule 1 says a laundered tier can never be un-laundered. **Not recommended.**
2. **Mint nothing; keep nonprofits keyed only by EIN, and let the spine reach them through `np_ein_uei_bridge.csv`.** Honest, but the bridge is **28 rows**, so in practice the nonprofit economy stays outside the entity layer.
3. **Mint a nonprofit class, but populate it only from RULED rows** — the 89 promotions already in `docs/NONPROFIT_CLASSIFICATION_RESEARCH_LOG.md`, the `native_entity` evidence rows above, the 51 `filing_req_cd = 14` instrumentalities, and whatever shard J's mission-text pass promotes. Every other row stays a candidate in `data/staging/np_harvest/candidate_spine_matches_shard_i.csv`. **Recommended.** It makes the class exist, so the dataset has somewhere to key to, without the entity layer inheriting an unadjudicated backlog.

Files: `data/staging/np_harvest/candidate_spine_matches_shard_i.csv` (4,362 rows, each with `corroboration` and a per-row recommendation), `shard_i.jsonl` (9,918 harvested rows), `README.md` (what is and is not a claim).

