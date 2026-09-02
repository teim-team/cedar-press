# Column promotion — the four READY datasets, 2026-09-02

*Workstream PROMOTE. Ownership declared before editing in
`docs/ARCHITECTURE_DECISIONS.md` **ADR-016**. **Zero network requests.**
Everything below was already on this machine.*

`docs/WHAT_IS_MISSING.md` ranked 39 absences and found **27 of them are
`ON_DISK_NOT_PROMOTED`**. This pass promoted the ones belonging to
`contractors`, `deals`, `nonprofits` and `native-owned-businesses`.

| script | table | columns added | gate |
|---|---|---:|---|
| `950_promote_contract_attributes.py` | `prime_contracts.csv` | 9 | `verify` + `selftest`, both exit 0 |
| `952_nonprofit_disposition.py` | `np_orgs.csv` | 4 | `verify` + `selftest`, both exit 0 |
| `953_nob_federal_identifier_candidates.py` | `native_owned_businesses.csv` | 4 | `verify` + `selftest`, both exit 0 |
| `954_register_promoted_columns_codebook.py` | `codebook_master.csv` | 17 blocks | `verify` + `selftest`, both exit 0 |
| `770_sample_extracts.py` (`SHOW` only) | `dist/samples/*` | — | rebuilt, 13 of 13 |

All four datasets are still **READY** on `518_dataset_readiness.py` after the
change, and every promoted table conserved its rows and the md5 of its
pre-existing fields exactly.

---

## `contractors` — `prime_contracts.csv`, 1,217,768 rows

**Nine columns, none of which the table had:** `contract_award_unique_key`,
`naics_code`, `naics_description`, `action_date`, `award_type`,
`product_or_service_code`, `product_or_service_code_description`,
`award_base_description`, `award_attributes_basis`.

| column | rows | fill | source |
|---|---:|---:|---|
| `naics_code` (6-digit) | 838,229 | **68.8%** | archive extract, transaction grain |
| `action_date` | 841,002 | **69.1%** | archive extract |
| `award_type` | 769,868 | 63.2% | archive extract |
| `contract_award_unique_key` | 841,002 | 69.1% | archive extract |
| PSC + PSC description + `award_base_description` | 247,987 | **20.4%** | local gapfill corpus, AWARD grain |
| `naics_description` | 247,987 | 20.4% | local gapfill corpus |
| `award_attributes_basis` | 1,217,768 | **100%** | derived, never blank |

**The 69.1% ceiling is structural, not laziness.** Only 841,002 rows carry
`contract_transaction_unique_key`; the other 376,766 come from the BGOV /
master-prime lineage and never had one. `award_attributes_basis` says which of
the three states a row is in, so a blank PSC that means *"not acquired"* is
distinguishable from one that means *"this row has no federal transaction
key"* without leaving the table.

**The 20.4% PSC ceiling reproduces `docs/WHAT_IS_MISSING.md` exactly** —
247,987, arrived at independently here. The corpus holds 1,041,147 award keys
and only 87,171 of the 307,671 awards this table needs. **The other 79.6% is a
genuine FPDS re-pull. Nothing in the shipped product implies otherwise.**

### Two defects the gate found on its first run

**1. `nan` is not a value, and it is ours.** The archive extract renders a
missing field as the four-character string `nan` — a pandas artefact of
`114_pull_prime_archive.py`, not something FPDS published. 4,306 `naics_code`
values in the extract and 71,134 `award_type` values reaching this table.
Copied through, they would ship a NAICS that sorts between `n` and `o`.
Normalised to blank on the archive-sourced columns; counts in
`docs/CONTRACT_ATTRIBUTE_PROMOTION.json`. Gapfill *text* is untouched —
`award_base_description` reads `NA` on six rows and that is what the
contracting officer typed.

**2. Twenty rows where `sector` and the archive NAICS disagree, all at the
FY2008 merge seam.** `sector` is the pre-existing 2-digit NAICS prefix from the
BGOV lineage, so it is an independent witness, which is why INV-SECTOR tests
the JOIN and not merely the copy. 838,207 of 838,227 cross-checked rows agree.
The 20 that do not are **all FY2008** and pair up *within one PIID with the
sectors crossed* — `DABQ0303D0002` appears with `sector=23` carrying NAICS
`561210` and with `sector=56` carrying `236118`. Obligation and fiscal year
match the archive to the cent, so nothing is a copy error; what is in doubt is
which FY2008 modification each pre-archive row was paired with by
`131_merge_archive_backfill.py`.

**Flagged, not resolved, and enumerated BY KEY** in
`review/prime_naics_sector_conflicts_2026-09-02.csv`. The gate fails if a new
mismatch appears *or* if a registered one heals. That is a register, not a
re-baseline.

### What could not be done

- **PSC and award description for the other 969,781 rows.** The gapfill corpus
  does not hold those awards and `114_pull_prime_archive.py :: release()`
  deletes each `FY*_All_Contracts_Full_*.zip` after filtering. `NOT_ACQUIRED`,
  and it needs a re-pull.
- **Anything for the 376,766 rows with no transaction key.** They would need a
  key attached first, which is a merge question, not a column question.

---

## `deals` — `deals_classified.csv`, 935 rows

**No column was added: everything the report asked for was already on the
table and simply not shown.** The fix is entirely in `SHOW`.

Promoted into the sample: `Announced_Value_USD` (835 rows, $45.20B),
`Value_Type` (935), `Description` (935), `State` (805), `Source_1` (931),
`Source_1_Type` (931), `Verification_Status` (935), `cedar_uid` (886).
`Record_Scope` was removed — it reads `2000 commitment` / `2023 commitment`,
which is a year plus a word. `Event_Type` was kept: on the 282 `TRANSACTION`
rows it says something `Status` does not (`100% stock acquisition`, `Asset
acquisition`, `Notes issued`).

**Checked and clean, so nothing was changed:** `Announced_Value_USD` is numeric
on all 835 populated rows, no scaling anomaly. The smallest value, `$1`, is
correct — Sealaska's acquisition of the remaining 49% of Kingston Supply for a
stated cash consideration of $1 plus indemnification, and `Notes` says so.
Announced and closed are already labelled separately across `Status`,
`Event_Type` and `deal_status_std`.

**The aggregation trap is already governed** by
`docs/MONEY_TOTALLING_RULES.md`: 618 of 935 rows carry a `Value_Type` naming a
FEDERAL award, $6.87B of which Cedar already ships in `funding` and
`contractors`, and the nine `deals_*_additions.csv` files are all inside this
table. Nothing here changes that.

---

## `nonprofits` — `np_orgs.csv`, 12,764 rows

**`classification_ruling` was NOT overwritten.** It means one narrow thing — a
HAND ruling by a named authority, present on 398 rows — and repurposing it
would be the error AGENTS.md records as *"a ruled method is not a positive
ruling"*. Four new columns instead.

`disposition` is derived and **never blank**:

| disposition | rows |
|---|---:|
| `CANDIDATE_NAME_ONLY` | 5,082 |
| `EXCLUDED_PRIOR_RULING` | 4,681 |
| `CANDIDATE_NAME_MATCH_UNVERIFIED` | 1,573 |
| `NATIVE_VERIFIED_STRICT` | 697 |
| `EXCLUDED_PLACE_NAME_COINCIDENCE` | 279 |
| `CANDIDATE_NAME_MATCH_GENERIC_TOKEN_ONLY` | **258** |
| `CANDIDATE_STATE_VALIDATED` | 105 |
| `NATIVE_PROPOSED_AWAITING_OWNER_RULING` | 73 |
| `NATIVE_RULED_VERIFIED` | 14 |
| `CONFLICT_EXCLUDED_AND_RULED_NATIVE` | **2** |

### The Eastern Star family is 258 rows, not one

`docs/WHAT_IS_MISSING.md` named **one** live false positive and asked whether
there were others of that shape. **There are 258, across 169 distinct
organisation names, and every one inspected by eye is a false positive.**
Register: `review/np_generic_token_name_matches_2026-09-02.csv` (578 rows
across all funnel stages; 258 live at `canonical_name_match`).

| rows | organisation family | matched to | on the token |
|---:|---|---|---|
| 55 | `VETERANS OF FOREIGN WARS OF THE UNITED STATES ...` | United Auburn | **UNITED** |
| 38 | `ORDER OF THE EASTERN STAR OF (NORTH\|SOUTH) DAKOTA` | Chickahominy Indians-Eastern Division | **EASTERN** |
| ~40 | `... DEL PUEBLO`, `PUEBLO DE DIOS`, `TEATRO DEL PUEBLO` | Ysleta del Sur, Pueblo of Acoma, La Jolla | **PUEBLO**, **DEL** |
| 14 | `SOCIETY OF SAINT PIUS X ...`, `ST ANN CATHOLIC CHURCH ...` | Saint Regis, St. Croix | **SAINT**, **ST** |

Worse than the headline case: `PROTESTANT EPISCOPAL CHURCH IN N DAKOTA` →
*Kickapoo Tribe in Kansas* on the token **IN**, and `NEW LIFE CHRISTIAN
FELLOWSHIP OF ONEIDA` → *Pueblo of Acoma* on the token **OF**. A stopword keyed
a tribe.

**`name_match_support` is a statement about the EVIDENCE, never about Native
status.** Cedar's standing rule is that Native status comes from what an
organisation says about itself in its own filing — never from an NTEE code and
never from a name — so a generic-token flag excludes nothing and rules nothing.
Rows already verified from a filing keep their disposition and simply carry the
flag. `name_match_shared_tokens` puts the actual overlapping tokens on the row
so the label can be checked rather than trusted. Nothing was deleted.

A second, weaker shape is also now visible and was not before:
**2,268 rows (541 live) share NO token with the canonical name they cite**, so
the displayed evidence does not explain the match at all.

**And a conflict the derivation surfaced:** two rows are BOTH
`excluded_by_prior_ruling = 1` and at a funnel stage that ruled them Native.
They get `CONFLICT_EXCLUDED_AND_RULED_NATIVE` — a named state, not a guess at
which side is right.

---

## `native-owned-businesses` — `native_owned_businesses.csv`, 2,393 rows

### The six date formats were already fixed. This pass added the gate.

Re-measured 2026-09-02: **all 623 populated `certification_expiration` values
are ISO.** `code/771_normalize_nboa_certification_dates.py` closed it between
`docs/WHAT_IS_MISSING.md` and now; the six formats survive only in
`native_owned_businesses.csv.bak_2026-09-01_pre615` (`####-##-##` 346,
`##/##/####` 144, `#/##/####` 86, `#/#/####` 33, `##/#/####` 13, `#/##/##` 1).
What was missing was a guard — `330_build_native_owned_businesses.py` is a full
rebuild and would reintroduce all six. **INV-ISO** is that guard.

### The join to contracting: 4 rows → 220

`business_entity_id` is populated on 4 of 2,393 and is **not** written by this
script. Four new columns carry a *candidate* instead:

| status | rows |
|---|---:|
| `no_match` | 1,707 |
| `refused_source_terms_restrictive` | **346** |
| `unique_name_match` | **220** |
| `refused_person_name_too_weak` | 110 |
| `ambiguous_name_match_refused` | 10 |

`federal_cage_candidate` on 169. Derived with **zero downloads** from the
31,059 UEI-bearing normalised names in `prime_contracts.csv`,
`fpds_uei_cage_map.csv`, `subawards.csv` and the local gapfill recipient
universe, written only where a normalised name resolves to **exactly one** UEI.

**Independent corroboration that the matcher works:** it returns
`Broadleaf, Inc. → DGA4AQ4DJYY9`, the exact UEI
`docs/PUBLICATION_POLICY.md` cites for the ASRC operating company, without
having been told.

**Tier B, and it may not key a dollar.** A name match is the weak method
`docs/ENTITY_MATCH_RULES.md` refuses for attribution. This ships the way
`tribe_id_neid_proposed` ships on the assistance table: a proposal a consumer
adopts or refuses explicitly, with the basis on the row.

### A second, independent matcher exists — and they agree 196 of 196

`code/1001_link_businesses_to_contracting.py` (a different workstream, the same
day) solves the same problem the other way round: a TIERED sidecar,
`data/clean/native_business_identifier_crosswalk.csv`, and its header states
*"this script owns these files; it never rewrites the directory."* So the two
do not collide — but they could DRIFT, and two answers to one question is the
`248`-versus-`293` lesson: a drifted second detector is worse than none,
because it is trusted.

**Measured: 196 business ids carry a UEI from both, and all 196 agree. Zero
disagree.** Neither was derived from the other and the source sets differ, so
this is a real corroboration rather than a copy corroborating itself — the
distinction `docs/ASSERTION_LAYER.md` exists to keep, and the first genuine
instance of it this pass produced.

**The crosswalk is the richer authority** — 263 ids to this column's 220, with
A/B/C/X tiers (A 134, B 73, C 45, X 14), a self-published rung and a
contract-number rung, plus CAGE 220 and DUNS 10. A consumer who wants the tier
should join it. The on-row column is the coarse convenience that makes the
directory joinable without a second file.

**The agreement is now a standing check, not a one-off measurement.**
`953 verify` carries **INV-CROSSCHECK** and fails if the two ever disagree on a
shared id; it says SKIPPED, out loud, when the crosswalk is absent. 953 does
not read the crosswalk to produce its value — if it did, the agreement would
prove nothing.

**`no_match` is not evidence the firm holds no federal award.** The universe
searched is Cedar's Native-attributed slice of FPDS, not all of FPDS. The
column note says so.

### The restrictive-terms fence is now an invariant, not a convention

**INV-RESTRICTIVE**: no `TERMS_STATED_RESTRICTIVE` row may carry a candidate
identifier by any of the three columns, and the gate fails if one ever does.
**58 of those 346 rows would have matched** and were refused. Attaching a
federal identifier to a restricted directory's business name enriches the
restricted record even though the UEI itself came from FPDS; a harmonized
derivative is still a derivative.

`service_category_raw` (2,043 rows, 85%) and `source_last_updated` (1,127) were
already on the table and are now in the sample.

### What could not be done

- **`certification_start`** is on 72 of 2,393 rows. It is not anywhere on this
  machine; it is a re-harvest from each nation's directory. `NOT_ACQUIRED`.
- **CAGE / DUNS / UEI from the businesses' own websites**, the owner's "easy
  win". That is a fetch, out of scope for a zero-download pass, and it is the
  route that would lift the 1,707 `no_match` rows. The local route reached
  220; the web route is what reaches the rest.
- **`naics`** stays at 34 rows. `service_category_raw` is the column that
  answers the same question at 85% and it is free.

---

## Concurrency

Nine agents were live on this tree. `870_build_geo_crosswalks.py` (workstream
INT, ADR-015) draws county FIPS from the *same* gapfill corpus, so ADR-016
declared this workstream takes NAICS / PSC / description / action date and
**touches no geographic column**. It held: `871_promote_geo_keys_contracts.py`
appended 13 `geo_*` columns to `prime_contracts.csv` *after* 950 wrote its
nine, and `772_strip_nan_sentinels.py` rewrote `parent_contract_number` in the
same window. **All nine promoted columns survived both, and 950 `verify`
re-reads all 841,002 archive rows and confirms every promoted value still
equals its source.** All three enrichers are idempotent — they strip their own
columns and rewrite them — so re-running after any rebuild is safe, and the
`40 → 950` ordering is declared in `cedar_pipeline.KNOWN_ORDERINGS`.

`code/770_sample_extracts.py` turned out to be under concurrent edit by
workstream INT-READY, which had already fixed the drop-blank-column defect and
added `Announced_Value_USD`, `parent_contract_number` and `funnel_stage` to
`SHOW`. This pass made **additive** edits only, for the columns 950/952/953
created and that no other agent could have known about.
