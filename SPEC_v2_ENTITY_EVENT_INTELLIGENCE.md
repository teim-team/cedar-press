# Cedar Grove: Native Entity & Event Intelligence — Consolidated Specification (v2)

*Received from Elijah 2026-08-07. This file is the authoritative copy. Read this
before any architectural work. `AGENTS.md` remains the operating guide for
day-to-day rules; this is the migration and formalization plan.*

> **STATUS: NOT IMPLEMENTED.** Phase 0 (Section 4) has not been run. No PR from
> Section 14 exists. Nothing below has been built. This file records the target
> so it cannot be lost to a context window.

---

## MEASURED-STATE CORRECTIONS (applied 2026-08-07)

The spec's own rule is **"where drafts and reality conflict, reality wins."**
The counts in the spec's Section 2 were true on 2026-08-06 and moved during the
2026-08-06/07 sessions. Corrected figures, measured from the files:

| Spec says | Actually on disk (2026-08-07) | Note |
|---|---|---|
| spine 952 entities | **1,310** | +358: BIE schools 185, UIO 43, TCU 37, CDFI 64, NFI 29 |
| codebook 682 variables | **835** | grew with NAGPRA, bills/votes, admin regions |
| gaming 775 facilities | **774** | one row retired |
| NAGPRA notices 676 | **6,729 notices**, 51,338 bridge rows | the 08-07 build landed |
| recognition events 430 | **366 events**, 17,058 roster rows | rebuilt |
| deals 922 | **790** across 8 addition files | |
| lobbying 43,963 | **27,796** in `native_entity_lobbying_disclosures.csv` | 43,963 may be raw filings |
| subawards 67,229 (2010–2026) | **63,548** clean (was 55,035; +8,513 on 08-07); **6,613,471 raw on disk**, FY2001–2020 + FY2025–26 only | see below |
| federal funding FY2007–2026 | **FY2008–2023** | FY2024–26 not loaded |
| prime FY2000–2022 | unchanged, **FY2023–26 still not loaded** | pull edge-blocked 2026-08-07 |
| identifier ledger 20,559 | unchanged; **7,823 usable (A/B with an entity)** | 12,641 rows carry no `tribe_id` |

**Two findings the spec does not contain:**

1. ~~**The subaward raw data is already on disk.** `data/raw/subcontracts/` holds
   ~6.6M rows covering 2007–2026, including FY2021 43,857 · FY2022 41,020 ·
   FY2023 71,279 · FY2024 183,078 — years where the clean file has 173 / 89 /
   120 / 166. The puller was **re-downloading data we already held** and was
   stopped 2026-08-07 along with its `code/43_resume_subaward_pull.sh` respawn
   loop. **The FY2021–24 gap is a matching job, not a pull job.**~~

   **WITHDRAWN 2026-08-07 — measured false. The FY2021–24 gap IS a pull gap.**
   `code/94_match_raw_subawards.py` read all 22 zips end to end: 6,613,471 rows,
   and **FY2021 = 0 · FY2022 = 0 · FY2023 = 0 · FY2024 = 0**. `_state.json` holds
   no `fy2021`–`fy2024` job; the pull ran fy2001–fy2020, then fy2025, fy2026.
   Every row's `subaward_action_date_fiscal_year` equals its own job's fiscal
   year (zero bleed across 6.6M rows), so the years are not hiding in a
   neighbouring chunk, and the 548 FY2021–24 rows in the clean file all carry
   `source_dataset` of `highergov_2023_export` or `funding_forward_fill`. The
   43,857 / 41,020 / 71,279 / 183,078 figures do not reproduce at any
   aggregation. **Four `bulk_download` jobs are still owed, plus the `fy2020`
   contracts member, which came back with 0 contract rows against 456,412
   assistance rows.** Full evidence: `docs/SUBAWARD_RAW_MATCH_LOG.md`.

   What the corpus we hold *did* still owe was matching on routes never tried —
   declared parent UEI and name. Script 94 appended **8,513 rows** (55,035 →
   63,548) reaching **134 Native entities** the dataset had never seen, mostly
   BIE schools, UIOs, intertribal organisations, TCUs, CDFIs and village
   corporations: spine classes that carry no ledger UEI and so were invisible to
   an identifier join however often it was re-run.
2. **The identifier join on unattributed prime rows is exhausted.** 328,994
   unattributed rows scanned against 7,823 usable ledger identifiers →
   **0 matches**. Every UEI we know has already been applied. New attribution
   must come from names, parent clusters, and rulings — not from re-joining.

---

## 0. How to use this document

- **Section 1** is scope and hard constraints. These override everything else.
- **Section 2** is the current measured state — the files, datasets, and counts everything else must preserve.
- **Section 3** is the invariant operating principles.
- **Section 4** is the required process before substantial new code.
- **Sections 5–12** are the target architecture: data model, domain semantics, resolution, publishability, dataset semantics, and outputs.
- **Sections 13–15** are engineering standards, sequencing, and the master checklist.

When this document is silent, choose the option that (a) preserves existing verified work, (b) keeps results explainable and auditable, and (c) makes future ingestion cheaper. When genuinely uncertain whether a decision would materially change classification, ownership, publishability tier, or legal-entity assignment, queue it for review and continue — do not stall, and do not escalate ordinary naming variations.

---

## 1. Scope and hard constraints

**In scope:** Cedar Grove's internal entity, identifier, alias, relationship, crosswalk, event, and ingestion infrastructure — formalizing the existing spine files into durable, typed, cumulative infrastructure before more datasets are added.

**System boundary:** everything in this spec — pipelines, spine, review, promotion — is the shared data layer, and it lives on the Cedar Grove side: Grove is both where the plumbing happens and a standalone product (integrated with the io engine) where all datasets can be downloaded, visualized, analyzed, and surfaced as insights, sold to organizations with unlimited users. Cedar Press is a separate individual-account publishing product — articles, method notes, and a tiered subset of the collections. All datasets reach Grove; only a subset reaches Press shelves. Neither product holds authoritative data state; both read the promoted layer, filtered by entitlement. The full contract is `cedar-grove-press-boundary.md`.

**Out of scope:** The public website. Do not open or modify website code in this pass. Verify at the end that no website files changed.

**Hard constraints:**

1. **Preserve the spine.** The spine, identifier ledger, hierarchy, brand-family registry, codebook, instrument taxonomy, and all Tier A rulings are the product of substantial manual verification. Migrate them; never regenerate, re-derive, or restart them.
2. Existing entity IDs remain stable unless confirmed duplicates, handled via explicit merge/redirect (Section 5.9) — never silent deletion.
3. **Human rulings (Tier A) outrank every automated match**, including deterministic identifier matches. A ruling is only reversed by a new ruling.
4. Cedar-generated identifiers are always labeled internal and never presented as official identifiers. **DUNS is D&B-licensed: internal use only, never published in any output at any tier.**
5. Do not begin substantial implementation until the branch/file review (Section 4) and pre-implementation deliverables (Section 14) are complete.
6. Implement the **minimum** changes needed. Prefer formalizing what exists over building new.

---

## 2. Current measured state

See MEASURED-STATE CORRECTIONS above for 2026-08-07 figures. The spec's original
table is retained below for the structure it defines.

**The spine:** `cedar_entity_spine.csv` (every Native entity, the join target) ·
`cedar_identifier_ledger_final.csv` (UEI/CAGE/EIN → entity crosswalk, the moat) ·
`entity_hierarchy.csv` (parent / ultimate parent / ANCSA region) ·
`brand_family_registry.csv` (106 brands learned from rulings: alutiiq→Afognak,
akima→NANA) · `codebook_master.csv` (every variable, typed, tiered
public/subscriber/internal) · `instrument_taxonomy.csv` (17 types + per-instrument
quirks) · `inflation_deflator.csv` (BEA GDP deflator, base 2025).

**Entity classes:** federally recognized tribes · Alaska Native villages · ANCSA
village corporations · state-recognized · intertribal · NHOs · constituent bands ·
ANC regional corporations · TCU · CDFI · BIE schools · urban Indian organizations.
The first BIE pass over-attributed **$13.4B → $3.9B** before the specificity
correction.

**Ten parent datasets:** Deals · Prime contracts (transactions + awards) ·
Subawards · Federal funding · FAADS · Lobbying · Nonprofits · Gaming · Compacts ·
Federal actions · Bills & votes.

**Derived subsets:** NAGPRA notices · Native pass-through subawards (**1,262;
166 entities; $712.3M countable** — rebuilt 2026-08-07 after script 94) · Recognition events (internal infrastructure feeding the
entity/history layer; **ruled NOT to ship as a standalone collection**, since
legal-status change moves too rarely to sell as a maintained cadence) · FAADS
name attribution · Bill outcomes.

**Assembled cross-dataset products:** Indian Gaming Property dataset (script 82) —
774 properties, 52 columns, 64,181 dated capacity observations. Per property:
entity resolved with ultimate parent (757/774), compact link (672), opening date
(636), BIA land-into-trust decision with FR URL and legal theory (268), expansion
visible via 4+ dated observations (423). **Backbone facts (measured 2026-08-07):**
595 of 774 carry a `casino_city_id`, IDs prefixed CCP-/VP-; NIGC's map holds 490
locations vs. our 774 — 140 on theirs we lack, 424 on ours not on theirs; the
published capacity layer is 6,027 official state-regulator observations. Also
held: 707 compacts (terms never parsed), 484 consultation notices + 1,829
referenced records inside the Federal Register work, and `lobbying_expenditure`
already populated in `np_financials.csv` across 8,507 orgs.

**Roadmapped expansions (companion documents; not yet built — governed by 9.4–9.5):**
- *Gaming intelligence deepening* — device/equipment observations, compact economics reverse-engineered, digital gaming, loyalty programs, resort components, employment, energy, financing/vendor network, property lifecycle. Attaches to the existing 774-property backbone and existing gaming sources. Free/public sources only. See `docs/GAMING_SPEC_RECONCILIATION.md`.
- *Government Relations & Advocacy expansion* — LDA becomes one channel among many. Attaches to the existing LDA foundation and its crosswalks. See `docs/LOBBYING_EXPANSION_RECONCILIATION.md`.

**Existing linking order** (the macro strategy — keep it):

1. **Roster** — pull from published universes (FR list, AIHEC, CDFI Fund, BIE, IHS Title V). Cheap, near-certain.
2. **Structure** — FPDS `ultimate_parent_uei`, brand families, cross-dataset propagation. Free.
3. **Sweep** — broad pulls matched against the spine name corpus. Expensive, last.
4. **Rule** — human decisions. Tier A. Outranks everything.

**Existing tiers:** A = publishable (verified/ruled) · B = visible, never publishes · C = unattributed · X = ruled out.

> **Reconciliation note:** Roster→Structure→Sweep→Rule is the *macro* linking
> strategy (7.1); Tiers 1–5 are the *per-record* match method (7.2); confidence
> is *how sure* (8.2); A/B/C/X is *what may be done with it* (8.1). Four
> different axes, all kept.

---

## 3. Operating principles (invariants)

```text
Every meaningful entity has one stable spine ID; external identifiers
attach to it and never replace it.

Human rulings (Tier A) outrank automated matches. Rulings, brand-family
entries, and negative rules (Tier X) are permanent infrastructure.

Every ingested record stays traceable: raw record → source identity →
canonical entity → canonical event.

Every meaningful connection is a typed, directional relationship with
evidence, dates where possible, and a verification status.

Governmental constituent relationships are not corporate ownership.
Village associations are not ownership. ANCSA region is geography,
never a parent. Association is never upgraded to ownership without
evidence.

But do not over-apply the corporate guard: tribes own companies
directly (Chickasaw Nation Industries). Direct tribe→company ownership
is real and must not be forced through an invented holding layer.

Never conclude "not Native" from a filter. Absence under a filter is a
property of the filter. Set-aside columns are reported_*; tribe_id is
determined.

Blank ≠ zero. Zero is an assertion; blank is silence. Negative money
is a deobligation and belongs in totals.

State what is measured; never estimate what is not published. Where a
number does not exist (per-facility gaming revenue), the row says so
explicitly — refusal to guess is a stated data value, not an omission,
and it is the commercial differentiator.

A bound is not a value, and a factual bound is not a confidence
interval. A land decision bounds an opening date from below; regional
GGR is a mathematical ceiling on a property's revenue; a compact
formula inverted against a public payment is an exact derivation.
Store each with its basis; never promote a bound to a value, and
never dress factual bounds in statistical language.

Measurement type travels with every observation. PROJECTED never
silently becomes ACTIVE; an authorized maximum is never the number
operating; a proposed device count from an environmental review is
not a floor count. Promotion between measurement types requires a
new observation from a source that supports it.

When a new source arrives, the question is "which existing records
can this enrich?" — never "can this become another dataset?" No
second property universe, no new IDs for things that have Cedar IDs.

Free and public sources only in anything published. The system must
remain reconstructable from public sources; paid databases are
competitors to exceed, never dependencies. Two grandfathered licensed
sources exist — DUNS and Casino City — and both follow the same rule:
validate internally, never publish, hard-gated in the distribution
script.

Cedar records retrieved facts, never authored characterizations of
named parties. A filing said X is a fact; "organization Y opposes
tribal interests" is an editorial judgment Cedar would be publishing
under its own name — the most legally exposed kind of field there is.
Where a stance matters, record each party's own stated position and
DERIVE alignment per (org, issue); a general stance label exists only
as a hand ruling, tiered like everything else.

Multiple reports of one event attach to one canonical event; related
events stay separate but typed-connected.

A family-level match is a valid resolution. Never invent a specific
legal entity to avoid an unresolved field.

Absence of a UEI never causes a plausible record to be discarded — it
moves the record to the next pass. Pre-2007 records attribute by name
at Tier B.

Resolve once, preserve the evidence, reuse it. No entity, deal, or
source identity is researched from scratch after resolution.

Broader results come from traversing verified relationships, never
from flattening entities.

Name similarity alone never establishes ownership, constituent status,
recognition, village-corporation status, Native ownership, event
duplication, or contract-family membership.

Containment is not a match. A tribe's name inside a longer recipient
name (Chickasaw Nation ⊂ Chickasaw Children's Village) is evidence of
a DIFFERENT entity. A match requires the record's name to be at least
as specific as the entity it resolves to. This is one central guard,
not a per-dataset patch.

Silent truncation is worse than absence. Never emit an output that
looks complete but isn't; where a format can't hold the data, say so
and point at the file that can.
```

---

## 4. Phase 0 — Review before building

Review every branch and working file related to: the spine and its IDs, the identifier ledger, hierarchy, brand families, aliases, source crosswalks, each dataset's ingestion/matching, tier assignments, ruling records, deal handling, contract families, and review queues. Do not assume the current branch contains all relevant work.

Per branch, record: `branch_name, purpose, major_files_changed, schema_changes, identifier_changes, relationship_changes, matching_changes, dependencies, overlapping_branches, errors_found, missing_tests, lint_or_type_errors, recommended_action, recommended_merge_order`.

Then inventory: which entities/IDs exist (and whether any branch assigns conflicting IDs); which identifiers, aliases, relationships, and rulings are verified; which records were manually resolved; which unresolved cases already hold useful evidence; accidental duplicate entities. Confirmed bugs found here get regression tests where practical.

---

## 5. Data model — formalizing the spine

Each target table names the existing file it grows out of. Migration means loading and typing the existing data, not replacing it.

### 5.1 Canonical entity table ← `cedar_entity_spine.csv`

```text
entity_id                  -- existing spine IDs, preserved
canonical_name             -- spine stores SHORT names (see 7.3)
legal_name / common_name
entity_type / entity_subtype
legal_status / recognition_status
ownership_classification
active_status
state_or_region / primary_geography
website_domain
start_date / end_date
verification_status / confidence
created_at / updated_at
```

Parent-like concepts stay distinct and are never collapsed: `immediate_corporate_parent`, `ultimate_corporate_parent`, `ultimate_native_owner`, `umbrella_government`, `constituent_government`, `associated_village`, `associated_region`. The relationship table (5.4) is the source of truth; denormalized fields are derived, never independently maintained.

### 5.2 Identifier registry ← `cedar_identifier_ledger_final.csv`

The ledger is the moat. Migrate into:

```text
identifier_id, entity_id, identifier_type, identifier_value,
issuing_system, source_system, start_date, end_date, is_primary,
is_official, verification_status, confidence, source_id,
created_at, updated_at
```

Types: UEI, CAGE, EIN, DUNS, SAM registration, federal award recipient, IRS, state corporation number, tribal charter number, SEC, LDA registrant/client, commercial DB, source-native, Cedar-generated. Rules: one UEI never silently maps to two active entities; conflicting CAGEs need review; the same value may exist under different issuing systems; reassigned identifiers keep prior mappings with effective dates. **DUNS rows carry a licensing flag: internal only, suppressed from every published output.** Pre-2007 FAADS has identifiers on only 65 of 2.77M rows — the registry is not the only path to attribution (7.3, 8.1).

### 5.3 Alias table (new, seeded from spine variants + brand registry + rulings)

```text
alias_id, entity_id, alias_name, normalized_alias, alias_type,
source_system, start_date, end_date, first_observed_date,
last_observed_date, verification_status, confidence, source_id,
created_at, updated_at
```

Alias types: legal, former legal, common, abbreviation, acronym, brand, operating name, DBA, governmental-unit variation, historical, translated, source-specific, shortened, **full-form federal-filing variant** ("Village of Sleetmute" for spine "Sleetmute"), **diacritic-folded form**, known typo, informal. Every name variation is not a new entity; every similar name is not an alias without evidence.

### 5.4 Typed relationship table ← `entity_hierarchy.csv` + `brand_family_registry.csv`

```text
relationship_id, source_entity_id, relationship_type, target_entity_id,
start_date, end_date, is_current, legal_or_informal, direct_or_inferred,
verification_status, confidence, source_id, evidence_text, notes,
created_at, updated_at
```

Migration specifics:
- Hierarchy parent / ultimate-parent columns → `subsidiary_of` / ownership relationships.
- **The ANCSA-region column migrates to `associated_with_region` — never a parent or ownership relationship.**
- The 106 brand-family entries → `brand_of` at Tier A (learned from rulings), preserving the ruling as evidence.
- Direct tribe→company ownership (Chickasaw Nation Industries) stored as-is: `owned_by` the tribe, no invented intermediate.

Canonical type families (shared enums, 13.1): **corporate** (owned_by, wholly/majority_owned_by, controlled_by, subsidiary_of, indirect_subsidiary_of, enterprise_of, holding_company_for, section_17_entity_of, chartered_by, instrumentality_of, brand_of, operating_group_of, division_of, doing_business_as, joint_venture_of, acquired_by, formerly_owned_by); **governmental** (constituent_band_of, constituent_tribe_of, member_government_of, component_government_of, federated_with, governed_under_constitution_of, legislative_body_of, department_of, agency_of, authority_of, commission_of, program_of, governmental_unit_of); **Alaska Native / geographic** (associated_with_village, village_corporation_for, regional_corporation_for, serves_shareholders_from, associated_with_region, located_in_region, serves_region); **nonprofit/institutional** (member_of, membership_organization_for, affiliated_with, partner_of, serves_native_entities, fiscally_sponsored_by); **historical** (formerly_known_as, successor_to, predecessor_of, merged_into, spun_out_of, reorganized_as). Never generic `related_to` when the real type is determinable.

### 5.5 Source-entity crosswalk (new; formalizes cross-dataset propagation)

```text
source_entity_crosswalk_id, source_system, source_entity_id,
source_entity_id_type, source_entity_name, normalized_source_name,
canonical_entity_id, matched_family_id, relationship_context,
first_observed_date, last_observed_date, match_method, confidence,
tier, verification_status, source_evidence, reviewed_by,
created_at, updated_at
```

Keep four concepts separate: source entity, canonical legal entity, organizational family, ultimate Native entity. A source identifier is never reassigned without preserving the prior mapping and dates.

### 5.6 Source records and provenance

`source_record_id, source_system, source_native_record_id, source_url, source_file, source_row, retrieved_at, published_at, raw_name, raw_payload_reference, content_hash, created_at`. Because federal sources correct retroactively (Section 10), ingestion must be **idempotent** — upsert by source-native key + content hash. Distinguish: duplicate ingestion of one record, different reports of one event, different events with the same parties, and later corrections.

### 5.7 Canonical events, claims, parties, and event relationships

- **Canonical event:** `event_id, event_type/subtype, event_title, announcement/effective/closing/start/end dates, status, value_amount, value_currency, primary_geography, verification_status, confidence, timestamps`. One acquisition reported by four sources = one event, four claims.
- **Source claim:** `event_claim_id, event_id, source_system, source_record_id, source_url/title, publication_date, claimed_event_date, claimed_value, claim_text, source_party_names, verification_status, confidence`.
- **Event parties** (never one buyer/seller field): `event_party_id, event_id, entity_id, source_entity_id, party_role, party_role_detail, is_native_entity, native_relationship_context, ownership/participation_percentage, dates, verification_status, confidence, source_id`. One event may hold multiple Native parties.
- **Event relationships:** `same_event_as, reported_by, closes, amends, extends, renews, replaces, terminates, follows, follow_on_to, financing_for, part_of, phase_of, resulted_from, supersedes, option_exercise_for, task_order_under, modification_of`. Name similarity alone never decides duplication.

### 5.8 Contracts and contract families

Preserve official identifiers (PIID, parent award ID, referenced IDV, modification number, recipient IDs) and add internal contract and contract-family IDs. Never treat a modification as an unrelated contract; never flatten task orders into the base. Keep `legal_award_recipient, immediate_parent, ultimate_corporate_parent, ultimate_native_owner, joint_venture_members, known_subcontractors` separately queryable.

### 5.9 Negative rules (= Tier X) and merges

Rejected matches: `source_name, source_system, rejected_entity_id, reason_rejected, evidence, date_reviewed, reviewer`. Confirmed event non-duplicates: `event_id_1, event_id_2, is_same_event, reason_not_same, evidence, date_reviewed, reviewer`. Standing rules: **Oneida NY ≠ Oneida WI; Shoshone-Paiute (Duck Valley) ≠ Paiute-Shoshone (Fallon)**; village corporation ≠ namesake village government (77 pairs). Tier X never resurfaces.

Merges: `deprecated_entity_id, surviving_entity_id, merge_reason, merged_at, reviewed_by`; historical records on a deprecated ID still resolve to the survivor.

---

## 6. Domain semantics — measured stakes

### 6.1 The universe
The spine's classes plus TCU/CDFI/BIE/UIO. Roster sources define near-certain membership: FR list, AIHEC, CDFI Fund, BIE, IHS Title V.

### 6.2 Village corporations vs. village governments
**77 namesake pairs exist, and $27.59B was booked wrong before the distinction was enforced.** The single most expensive confusion in the system. Every matcher touching Alaska Native names must check the namesake-pair guard.

### 6.3 ANCSA regions, umbrella governments, constituent bands
ANCSA region is geography, never a parent. Umbrella/constituent (Mille Lacs Band → `constituent_band_of` → Minnesota Chippewa Tribe) is governmental, never corporate. Never attribute a constituent's activity wholesale to the umbrella or vice versa.

### 6.4 Corporate families, brands, governmental units
`Cherokee Nation → Cherokee Nation Businesses → Cherokee Federal family → subsidiaries`: connected, never interchangeable; resolve at the most specific defensible level. Counterweight: tribes also own companies **directly**. Council/department/authority wording usually names part of a government; create a distinct node only with independent legal, financial, contractual, or analytical identity.

### 6.5 Native classification spectrum
Distinct, never interchangeable: federally recognized · state-recognized · constituent government · tribally owned · Native-owned · Native-controlled · Native-serving · Native-focused · membership organization · Native-affiliated · located in a Native community.

**$86.19B (60.9%) of Native-linked contract dollars report no Native preference**; Tribalco alone has 77% of $1.32B invisible to a set-aside filter. Native status comes from the spine and ledger; preference flags are `reported_*`.

### 6.6 Institutions named after tribes are not the tribe
The containment failure appeared **six** independent times (spec says four; measured 2026-08-07): colleges onto tribes · Indian Pueblo onto Makaha · trap-token matches · tribes onto their schools (Chickasaw Nation → Chickasaw Children's Village, $2.8B; Yakama $917M; Blackfeet $568M; first pass $13.4B → $3.9B) · Elim village government onto Elim Native **Corporation** · **all 148 TDHEs onto their own tribes**. One bug, six faces, **one central fix** (7.3).

**The 56 federally operated BIE schools never roll up to a tribe.** `ultimate_native_owner` stays null.

---

## 7. Entity resolution

### 7.1 Macro strategy: Roster → Structure → Sweep → Rule
The outer loop of every dataset's pipeline. Rule is Tier A and outranks everything, including identifier matches.

### 7.2 Per-record match hierarchy
- **Tier 1 — Deterministic identifier**
- **Tier 2 — Verified alias** (incl. full-form federal variants and folded forms)
- **Tier 3 — Strong multi-attribute**
- **Tier 4 — Family-level** (family clear, legal entity not)
- **Tier 5 — Structured review candidate** (preserve candidates, evidence, rejected candidates, the open question, the next useful source)

Missing identifiers move a record **down** the ladder, never out of it.

### 7.3 Normalization and matching guards
One shared pipeline, no per-dataset helpers. Measured additions:
- **Fold diacritics correctly** — Ukpeaġvik must fold to `ukpeagvik`, not `ukpea vik`. Index raw and folded.
- **Short ↔ full name bridging** — spine stores short names; federal systems file full ones.
- **Name-trap terms require corroboration:** creek, cherokee, colorado, ojibwe, shawnee, oneida, apache, central, eagle, river, mountain, santa. **Add (measured 2026-08-07): indian, united, san, little, rancheria, minnesota, three, wind, bristol, advantage, alliance, pacific, summit, frontier.**
- **Central containment/specificity guard** — the record's name must be at least as specific as the entity's. The six local fixes become its regression tests.
- **Cross-worker collision check** — Sequoyah High School (OK) resolved onto Sequoyah Fund Inc. (NC CDFI) written minutes earlier by another agent.
- **Standing disambiguation rules** fire before any sweep match.

### 7.4 Dataset pipelines
**Identifier-rich:** official identifier → ledger/crosswalk → verified alias → name/attribute → relationship & family → review.
**Identifier-poor:** source-native ID → existing Cedar source identity → recurring exact source name → verified alias → family → multi-attribute → review.
**Deals:** extract every named party; link at the most specific defensible level; classify each new report as new deal / another report / later stage / amendment / related-but-separate / follow-on / replacement.

---

## 8. Publishability and confidence — two axes

### 8.1 Tier
```text
A   Publishable. Verified or human-ruled.
B   Visible internally; never publishes. (name-only attribution, e.g. pre-2007 FAADS)
C   Unattributed.
X   Ruled out. Never resurfaces.
```
Promotion to A requires verification or ruling — never confidence alone.

### 8.2 Confidence
```text
0.98–1.00   deterministic identifier or previously verified relationship
0.90–0.97   very strong alias / relationship / multi-attribute
0.75–0.89   likely, needs targeted review
0.50–0.74   plausible, retained for review
< 0.50      weak — never auto-link
```
High confidence does not imply Tier A.

### 8.3 Release packaging
Each published dataset ships as a **folder**: the **CSV** (uncapped, canonical, source bytes preserved) · **`_notes.xlsx`** (Read Me · Data · Codebook · Reading the Data · Comparability · Research Ready · Terms of Use · Citation; the Data tab written only if under Excel's 1,048,576-row ceiling, otherwise a notice pointing at the CSV — **never truncated**) · **`TERMS.txt`**.

**What is actually proprietary:** CAGE codes and UEIs are public federal identifiers; claiming ownership weakens the enforceable claims. The protected original work is the **crosswalk** — which entity an identifier belongs to, the Cedar IDs and hierarchy, the tiering, the rulings. Lawyer review before launch.

**"Research ready" is properties, not methods.**

**Bundle coherence:** `faads_transactions.csv` is a strict subset of `faads_transactions_all_agencies.csv` (59,514 keys verified); reading both double-counts $53M.

---

## 9. Dataset semantics

### 9.1 Money
- Negative = deobligation (9.7% of contract rows) and **belongs in totals**. Zero = an action that moved no money (9.9%). Blank ≠ zero.
- `total_obligations` = SUM. `total_award_value` = MAX per award. Enforce in shared helpers.
- Credit reports $0 obligation **by design**; money is face value + subsidy cost. Face value is award-cumulative and signed — naive summing turns $171M into $271M.
- Self-determination is **$46.30B**, neither grant nor contract. Classify by taxonomy, never by pipe.
- Real dollars use the BEA deflator, base 2025.

### 9.2 Subawards
Reliable about **relationships**, unreliable about **amounts**: 5,941 rows report a subaward larger than its own prime (worst $64,910 → $794.5M). Two mandatory filters: `duplicate_status == 'primary'` AND `subaward_exceeds_prime_flag != 'yes'`.

### 9.3 Other source realities
LDA spend is rounded to $10,000, income **or** expenses never both · 990-N filers (6,453 of 12,764) report no financials · CDFI relending is structurally untrackable · federal sources correct retroactively.

### 9.4 Gaming intelligence — see `docs/GAMING_SPEC_RECONCILIATION.md`
**Backbone ruling (2026-08-07): keep the IDs, replace the evidence under them.** CCP-/VP- IDs stay (the prefix is history, not provenance). Casino City → internal QA only, publish-gated like DUNS. NIGC = IGRA coverage, not identity. 140 NIGC locations we lack get new IDs after review; the 424 on ours not on theirs get IGRA-status review, **not deletion**.

**Class II/III mix is a dated observation, never a property attribute.**

**Highest-value gap needing no new access: parse the 707 compacts.** Where a public payment meets an invertible formula, `payment / rate` is exact arithmetic — the one honest route to real property revenue — provided the revenue concept is preserved.

**Revenue evidence hierarchy:**
```text
REPORTED_PROPERTY_REVENUE > EXACT_DERIVED_PROPERTY_REVENUE
> BOUNDED_DERIVED_REVENUE > TRIBE_LEVEL_REVENUE
> REGIONAL_GGR_CONTEXT / REGIONAL_GGR_CEILING > NO_REVENUE_OBSERVATION
```
Regional GGR is a **ceiling**, never allocated across properties.

**Declination letters** prove NIGC review, not execution: `NIGC_REVIEWED → EXECUTION_UNCONFIRMED → EXECUTED_CONFIRMED → CLOSED_CONFIRMED → SUPERSEDED / TERMINATED`.

Everything is a longitudinal observation with `measurement_type`; the promotion guard applies (PROJECTED never becomes ACTIVE).

### 9.5 Government relations & advocacy — see `docs/LOBBYING_EXPANSION_RECONCILIATION.md`
Every channel is an event with parties. Channel enum: `LDA_FILING, CONSULTATION, OIRA_MEETING, HEARING_TESTIMONY, FACA`. **Consultation is a statutory government-to-government obligation, not lobbying.**

Two channels are extensions, not builds: consultation (484 notices + 1,829 referenced already held) and 990 Schedule C (`lobbying_expenditure` already in `np_financials.csv`).

**`position_on_native_issue = Oppose` is rejected as designed** — an authored characterization of a named party, the most legally exposed field in the spec. Replacement: record each party's own stated position and derive `alignment` per (org, measure): `SAME / OPPOSED / NO_TRIBAL_POSITION_FOUND`. Stance labels only as Tier A rulings.

**Outcomes link, never claim causation.**

---

## 10. Cumulative learning, cadence, reprocessing

Every verification updates durable infrastructure. Reprocessing is **targeted**. Temporal change uses effective dates, never overwrites.

### 10.1 Sustainable build pipeline
```text
scheduled pull (per cadence)
→ versioned, idempotent build script
→ staged output with diff + changelog
→ resolution through the spine (guards active; results carry tier)
→ HUMAN REVIEW GATE: nothing enters Tier A, the published layer, or a
  release bundle without review
→ promote → database → reprocessing hooks fire
```
Automated results land at Tier B/C pending review. Routine re-observations of already-verified facts may auto-promote at Tier B.

**Cadence:** Daily FR · Weekly contracts/funding/deals · Monthly subawards + product release · Quarterly lobbying (2 weeks after LD-2), gaming, compacts, 990s · **Re-pull trailing windows** (contracts 90d, assistance 30d) because federal sources correct retroactively.

---

## 11. Search scopes
Distinct, never conflated: exact entity · entity + aliases · corporate family · governmental family · ultimate Native ownership network · associated network · event network. Every result explains its inclusion.

---

## 12. Required resolution outputs
Never bare matched/unmatched. Per source entity record and per potential event record, the full field lists in the original spec apply. The review queue holds only genuinely ambiguous cases.

---

## 13. Engineering standards

### 13.1 Shared domain enums
Every finite concept defined once and imported everywhere. No re-declared lists; no enums remapped onto identical values; display labels separate.

### 13.2 Internal ID service
All internal IDs from one shared service. Existing spine IDs grandfathered. **Never infer type from prefix.**

### 13.3 Utilities, comments, lint, tests
Keep custom utilities only for real domain logic. Comments explain non-obvious domain decisions.

Lint: no duplicate enums · no raw strings for relationship types or tiers · no `any` in resolution output · exhaustive enum handling · no ID construction outside the service · no silently ignored unresolved results · no event without provenance · **no DUNS field in any publish-path serializer**.

Tests (the measured regressions): namesake village-corp/government pairs · Oneida and Shoshone-Paiute · name-trap gating · **diacritic folding (Ukpeaġvik)** · constituent vs. umbrella · multiple Native parties per event · duplicate vs. related deal · modification vs. new contract · **obligation SUM vs. award-value MAX** · deobligation inclusion · blank-vs-zero · subaward filter pair · loan face-value dedupe · 638 classification · Tier B publication suppression · **bound-never-promoted** · NO_REVENUE_OBSERVATION carried through every export · idempotent re-run · **containment guard (Chickasaw Children's Village, Yakama, Blackfeet)** · **Sequoyah High School vs. Sequoyah Fund** · cross-worker collision · **56 BIE schools blocked from tribal roll-up** · **bundle overlap (FAADS subset)** · **Excel row-ceiling notice instead of truncation** · control-char stripping worksheet-only · targeted reprocessing · Tier X suppression · **measurement-type promotion guard** · regional GGR never allocated · derived-revenue concept labeling · declination execution ladder · no-new-ID guard · **Casino City and DUNS publish-gates** · alignment never emits an authored stance · Class II/III as dated observation · consultation never typed as lobbying · **staged changes cannot reach published without review** · end-to-end provenance.

---

## 14. Deliverables and sequencing

```text
PR 1  Shared domain enums, tiers, and types
PR 2  ID service + identifier-ledger migration (with DUNS suppression)
PR 3  Aliases (incl. folded/full-form seeding), relationships
      (hierarchy + brand-registry migration), source crosswalks
PR 4  Dataset pipelines (Roster→Structure→Sweep→Rule) + matching guards
PR 5  Aggregation/instrument semantics from Section 9
PR 6  Event layer: canonical events, claims, parties, deal dedup,
      contract families
PR 7  Targeted reprocessing, idempotent re-pull windows, tests, lint,
      cleanup
```

---

## 15. Master implementation checklist

```text
[ ] Review every relevant branch and working file
[ ] Confirm the website remains untouched
[ ] Inventory spine IDs, ledger identifiers, source-specific IDs
[ ] Identify duplicate entities and conflicting ID assignments
[ ] Define merge and redirect behavior
[ ] Consolidate domain enums incl. tiers and instrument types
[ ] Migrate spine → entity table (IDs preserved)
[ ] Migrate identifier ledger → registry (DUNS flagged internal-only)
[ ] Migrate hierarchy → typed relationships (ANCSA region → association)
[ ] Migrate brand-family registry → Tier A brand_of relationships
[ ] Seed alias table: variants, full-form filings, folded forms
[ ] Encode standing disambiguation + namesake-pair guards as Tier X
[ ] Implement name-trap gating and diacritic folding (with regressions)
[ ] Build source-entity crosswalks and source-record provenance
[ ] Make ingestion idempotent for trailing-window re-pulls
[ ] Encode Section 9 aggregation/instrument semantics in shared helpers
[ ] Add canonical event IDs, claims, multi-party events
[ ] Add deal deduplication and contract-family support
[ ] Add Tier X persistence and targeted reprocessing
[ ] Enforce Tier B publication suppression and DUNS suppression
[ ] Register facility/asset node class; wire gaming properties to
    entities, compacts, land decisions, and deals through the spine
[ ] Enforce revenue evidence hierarchy + bound-vs-date
[ ] Implement the central containment/specificity guard; retire the
    six local fixes into its regression suite
[ ] Add cross-worker collision checks to entity creation and matching
[ ] Encode 56 federally operated BIE schools as operated_by federal
[ ] Build the release-folder packager (CSV + _notes.xlsx + TERMS.txt)
    with row-ceiling notice and overlap check
[ ] Resolve FAADS subset double-count (drop from bundles or flag)
[ ] Get terms of use reviewed by a lawyer before launch
[ ] Add measurement_type enum + promotion guard to observation models
[ ] Implement revenue evidence hierarchy and bound_basis fields
[ ] Add source-claim provenance and source-coverage profiles (gaming)
[ ] Model digital gaming as a separate linked universe
[ ] Extend event types/roles for advocacy channels
[ ] Stand up state-lobbying source-scoped identities on the LDA pattern
[ ] Enforce free/public-source constraint on all published outputs
[ ] Ratify backbone ruling: CCP-/VP- IDs stay; Casino City → QA-only
    with publish gate; NIGC = IGRA coverage, not identity
[ ] Reconcile NIGC coverage gap (add 140 after review; IGRA-status
    review of the 424; no deletions)
[ ] Parse the 707 compacts into structured terms (first gaming priority)
[ ] Replace position_on_native_issue with derived (org, measure)
    alignment; stance labels only as Tier A rulings
[ ] Extend consultation from existing FR holdings (484 + 1,829)
[ ] Complete 990 Schedule C fields on existing np_financials
[ ] Stand up the staged-pull → diff → review-gate → promote pipeline
[ ] Stand up server-side entitlement (/auth/press/validate|activate)
    answering identically to client PLAN_REACH — no restricted data
    ships behind Press until it exists
[ ] Centralize internal ID generation
[ ] Remove unnecessary custom utilities; improve domain comments
[ ] Add regression tests and lint rules (Section 13.3 list)
[ ] Document PR dependencies; each PR passes its checks
[ ] Verify no website files changed
```

The immediate goal is unchanged: not more datasets, but making the spine, ledger, relationships, crosswalks, and event foundation reliable enough that each new dataset strengthens the system instead of spawning another isolated matcher.
