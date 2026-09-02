# Methodology — Federal Register, Indian Affairs

**`federal-register`. `data/clean/federal_actions.csv`, 156,897 Federal
Register documents, 1994-01-03 to 2026-09-01, across 22 customer tables — 23
from 2026-09-02, when `dear_tribal_leader_letters.csv` (807 documents, 597 of
them letters, from IHS, BIE and BIA rather than from the Federal Register)
joined the collection, with `dtll_source_coverage.csv` beside it as an internal
coverage record.** [measured 2026-09-02]

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

**Readiness: READY** — one of the two datasets that cleared the line first, and
§8 explains what that required. [measured — `docs/DATASET_READINESS.md`,
regenerated 2026-09-02: 22 tables, 22/22 grain, 22/22 keys, duplicates clean,
C4 88% keyed [mixed], **C5 row conservation 22/22**]

---

## 1. Sources, and the inclusion rule — which IS the methodology

**One endpoint, on all 156,897 rows:
`https://www.federalregister.gov/api/v1/documents.json`.** Free, no key, plain
GET. [measured — `api_endpoint` identical on every row]

The window is **1994-01-01 to today**. The API's own coverage floor is 1994;
pre-1994 exists only in scanned GovInfo volumes and is unavailable through any
API.

### The fourteen nets

`code/10_pull_federal_register.py` runs fourteen searches sharded by
publication year: **one agency net**
(`conditions[agencies][]=indian-affairs-bureau`) and **thirteen keyword nets**
(`conditions[term]=…`). Live term counts [measured, from
`keyword_terms_matched`]:

```
tribal                     113,433
Indian                      82,606
tribe                       64,590
reservation                 25,752
"Native American"           19,591
"Native Hawaiian"            6,749
"Alaska Native"              6,263
ANCSA                          556
"tribal-state compact"         469
"federal acknowledgment"       222
"fee-to-trust"                 194
"land into trust"              169
"liquor ordinance"             129
```

**A document qualifies as Native-relevant if any one net returned it. That is
the whole rule — and it is a RECALL rule, not a relevance rule.** Documents are
de-duplicated on `document_number`.

`net_caught` [measured]: `keyword` 153,583 · `both` 3,302 · **`agency` 12**.

**Those 12 agency-only documents justify running both nets.** Two of them are
substantive land actions the keyword net missed outright — the 2001-02-20 and
2001-06-13 *Acquisition of Title to Land in Trust; Delay of Effective Date*
notices, now classified `land_into_trust`. **A keyword-only build would have
dropped them.**

### The single most consequential API limit, probed rather than assumed

```
conditions[title]=tribal
  -> HTTP 400 {"errors":{"title":"is not a valid field"}}
```

**There is no title- or abstract-scoped search. `conditions[term]` is full text
only.** That one fact is why the corpus is 156,897 rows rather than about
20,000, and why `title_abstract_term_hit` had to be computed client-side after
retrieval.

**Measured: only 22,257 of 156,897 rows (14.2%) name a harvest term in their
own title or abstract. 134,640 (85.8%) matched on body text alone.** The same
measure lives in `fr_content_classification.csv` (156,897 rows, **0 documents
unclassified**): `relevance_tier` = `body_only_unverifiable` **133,316
(85.0%)** · `abstract_subject` 12,932 · `title_subject` 9,536 ·
`weak_term_only` 1,113. [measured]

### Other probed API behaviour, recorded because it changes what a pull returns

- **`conditions[agencies][]=bureau-of-indian-affairs` → HTTP 400, invalid
  value.** The slug does not exist; the correct one is
  `indian-affairs-bureau`, agency id 234.
- **`conditions[bogus]=x` → HTTP 400**, so **a 200 from this API proves the
  filter was really applied.** (The contrast is instructive: `lda.gov` silently
  ignores unknown parameters, so a 200 there proves nothing.)
- **Any query returning ≥10,000 results is silently truncated.** Every net was
  therefore sharded by year with a 9,500 split guard, and **no shard ever
  reached it** — the largest was `tribal` in 2024 at 5,541.
- **Multi-word terms must be quoted.** `"Native American"` unquoted returned
  878 hits for 2010 against 598 quoted.
- **The API 503s on bursts.** Three concurrent workers produced a stream of
  503s; two workers at 0.6 s produced seven across the whole run, all absorbed
  by retry, **0 shards lost.**

Harvest result: 462 shards, 0 failed, 451 wrote records, 11 genuinely empty,
**0 count mismatches**, 1,132 seconds.

### What was deliberately not used

- **Pre-1994 volumes** — the API does not serve them.
- **A title-scoped search** — the API does not have one.
- **Terms-restricted tribal sources** are irrelevant here: every row is a
  federal publication.

---

## 2. How the rows were made

`code/10_pull_federal_register.py` (the full harvest, cached to
`data/raw/federal_register/*.jsonl.gz`) →
`code/11_classify_federal_actions.py` (adds `action_type`, `action_type_rule`,
`action_type_signal`, `action_type_source_field`, `tribe_or_native_entity`,
`classified_date`) → `code/22_apply_temporal_floor.py` (writes `pre_2000_flag`
and `floor_basis_field` **in place**) → thereafter
**`code/342_pull_federal_register_incremental.py`** for carry-forward, and
**`code/751_fr_refresh_promote.py`** for the derived tables.

Downstream builders on the same corpus: `code/77` (NAGPRA), `code/130`
(Section 106), `code/154` (FR ex parte), `code/96` (consultation), `code/78`
(content classification, themes, tiers), `code/136` (correspondence and FOIA),
`code/69` plus `code/514` and `code/510` (identity).

### Two hard "do not run" rules, both learned expensively

1. **`11_classify_federal_actions.py` is a FULL REBUILD and must never be used
   to refresh.** It reverts `pre_2000_flag` and `floor_basis_field` — the
   rebuild-reverts-enricher collision that *"has now bitten this project four
   times in one day."* `342` instead **imports `11`'s own `classify()` and
   `22`'s own `year_of()`** and appends, so there is one classifier rather than
   two that can drift.
2. **`10_pull_federal_register.py` cannot be used incrementally.** Its shard
   cache is keyed `net__key__d0__d1`, so moving `END_DATE` **renames the current
   year's shard and refetches the whole year across all fourteen nets.**

### The completeness contract, stated as code

This is the best methodological paragraph in the corpus and it is worth
quoting the reasoning. The next incremental run derives its start date from
`max(publication_date)` in the file. **So if a partial window were merged, the
max date would jump to today and every document missed in between would become
permanently unreachable — silently.**

Therefore: every shard compares `records_retrieved` against the API's own
reported `count`, and **the merge happens only if EVERY net completed and every
retrieved count equals its reported total.** Otherwise the fetched shards stay
on disk as cache, the CSVs are untouched, the run is recorded `INCOMPLETE`, and
a later run resumes free.

Host discipline: one poller, `logs/_HOSTLOCK_www.federalregister.gov.json`
claimed and released, sequential at 0.60 s, a wall-clock deadline before each
net, and `.part`-then-rename so an interruption cannot look like a completion.

The generation history is legible in the file itself: `fetched_date` on
`federal_actions.csv` = **156,452 at 2026-08-05 + 320 at 2026-08-26 + 125 at
2026-09-01 = 156,897.** [measured]

### Why `751` exists

`fr_consultation` has no builder of its own — it is written by
`code/78_content_analysis.py`, which writes **eighteen** tables of which only
ten are FR-side. The other eight are **lobbying** tables, and a full `78` run
rewrites `lobbying_issue_families_filing.csv` from scratch, **dropping five
columns it does not produce** (`cedar_uid` from `503`, four
`entity_id_withdrawn*` from `353`).

So `751` reuses `78`'s existing `ONLY` write filter rather than adding a second
mechanism, and never calls `build_lobbying`, `build_agencies` or `run_audits`.
Its second job is re-stamping `cedar_uid` against a **named** table list using
`503`'s own `register_map()` — because `503 stamp --apply` walks all 125 tables
in `data/clean`, and *"re-stamping a table another agent is mid-rebuild on is
how this project loses work."* It refuses to write a table whose row count
would fall or that would lose a column relative to the `.bak` it takes first,
and **it never mints.**

---

## 3. How entities were attributed

**This is the only Cedar dataset whose identity runs through the source-record
layer**, and the design point is that *what a source says* and *who Cedar
thinks it means* live in two tables — **so a bad match can be refuted without
refuting the fact.** Source records are content-addressed
`SR-sha1(dataset|locator)`; `510.harvest_fr_roster` emits only from links whose
`link_role = identifies` and whose `link_status` is `verified` or `proposed`;
and invariant **I17** fails the build if a roster fact reaches an entity no
accepted link names.

**`federal_actions.csv` itself carries NO entity attribution.**
`tribe_or_native_entity` is blank on all 156,897 rows, **by instruction**:
*"Resolving notice names to the spine needs alias history and reconcile-queue
rulings; string-matching tribe names out of titles is the 'Cherokee Inc.' trap
AGENTS.md forbids."* [measured]

Attribution lives in a separate bridge. `federal_actions_entity_bridge.csv`:
**5,786 rows across 633 entities and 4,991 documents**,
`entity_match_method = spine_name_in_text` on 100%, `matched_in` title 4,054 /
abstract 1,732, `entity_tier` **B 4,325 / A 1,461.** [measured]

**So 3.2% of the corpus (4,991 of 156,897) reaches any entity at all — and that
is scope, not failure.** A rule changing federal Indian law has no single
entity to attach. The scoreboard scores this dataset's C4 at **88% keyed
[mixed]** against its natural scope mix, not against the row count.

`fr_recognized_entities.csv` (575 rows) is rebuilt by
`code/69_enrich_spine_from_federal_register.py` **only** when a new *"Indian
Entities Recognized by and Eligible To Receive Services"* notice lands.
Measured 2026-08-29 without writing, re-running `69` today changes **one cell**
(the Alaska list's title moves `entity` → `section_heading`), 575 in and 575
out, and is a **complete no-op on the spine** — 1,536 rows compared, 0 changed,
0 aliases added. But because `514` embeds `kind` in the locator, that one cell
re-mints one node id and one link id, **so `69` obliges `514 all --apply` then
`510 all --apply` in that order, or `514 verify` fails.**

---

## 4. Decisions that shaped the data

### `action_type` is assigned only from explicit text, and the evidence travels

A document's `action_type` is assigned **only from explicit text in its own
title, abstract, or Federal Register `type` field**, and every row carries
`action_type_rule`, `action_type_signal` (the **literal substring that fired**)
and `action_type_source_field`.

[measured] other 87,261 · rulemaking 63,440 · grant_solicitation 3,397 ·
ancsa_conveyance 768 · tribal_state_compact 687 · land_into_trust 305 ·
liquor_ordinance 261 · consultation 236 · federal_acknowledgment 188 ·
reservation_proclamation 121 · gaming_land_decision 101 · irrigation_rates 97 ·
recognition_list_update 35.

### Two tiers inside that distribution must be read differently

**The ten named tribal buckets (2,794 rows) are 82–100% on-face.**

**`rulemaking` (4% on-face) and `other` are the RECALL tier.** *"Do not present
63,248 as a count of tribal rulemakings"* — it is the count of Rules and
Proposed Rules **inside the tribal keyword net.** `grant_solicitation`, at 25%
on-face, carries the same caveat ("Cooperative Agreements To Prevent Lyme
Disease").

### `consultation` is assigned from the TITLE only, and it undercounts on purpose

Agencies routinely recite in an abstract that consultation *was conducted*
before issuing a rule. **That sentence is evidence consultation happened; it is
not evidence the document IS a consultation notice.** Two real 2024 rows were
pulled in by such a recital before the restriction was added.

**The consequence is stated rather than hidden: consultation is undercounted.**

### `other` is not homogeneous, and its composition was measured

Within it: **Paperwork Reduction Act information-collection notices 27,981** —
32% of `other` and 18% of the whole corpus, the single largest source of bulk —
NAGPRA notices 5,634, and HEARTH Act leasing approvals 123. The latter two were
**flagged as the strongest candidates for new buckets and deliberately not
added**, so the decision is visible rather than silently taken.

### The corpus is not BIA-centric, and that is a property of the net

Top agencies [measured]: Interior 26,934 · **EPA 25,775** · HHS 11,783 · DHS
11,500 · Energy 11,124 · Coast Guard 8,989 · Commerce 8,967 · DOT 8,343 · NPS
8,227 · FERC 8,139.

**Agency composition describes who *mentions* tribes, not who *acts on* tribal
matters.**

### 1994 has no usable document type

**2,838 of 2,926 rows from 1994 are `Uncategorized Document`.** 39 rulemakings
in 1994 against 1,287 in 1995 is a **metadata artefact**, not a change in
federal behaviour. **Start any rulemaking series at 1995.**

### Section 106 was published as a second file rather than merged

`consultation_events.csv` holds **20** `NHPA_section_106` rows against
**1,367** in `section_106_consultation_events.csv`, with only **14** source-URL
overlaps and 17 tribes appearing nowhere in the older file.

**The merge was explicitly declined.** `code/96` owns `consultation_events.csv`
and rebuilds it from its own inputs, so appended rows would be dropped — *"the
same shape as the `09_import_rulings.py` regression."* The recommendation is to
publish side by side (`channel = CONSULTATION` against
`SECTION_106_CONSULTATION`), and if one view is wanted, **build a THIRD file
that reads both and writes neither.**

---

## 5. What a buyer may total

- **`federal_actions.csv` is a document count, and only the named tribal
  buckets are safe as subject counts.** `rulemaking` and `other` are recall
  categories.
- **`federal_actions_entity_bridge.csv` is one row per (document, entity)** —
  a document naming 165 tribes occupies 165 rows. Counting rows counts
  mentions, not documents.
- **`consultation_events.csv` is one row per (event, participant as
  published)**, and `consultation_event_id` alone is **not** unique: an event
  with several named participants has one row each, and **1,006 rows name no
  participant at all.**
- **`correspondence_foia_source_coverage.csv` is one row per URL probed** — 17
  rows repeat (agency, source, status, evidence) under a different URL, because
  one agency publishes several correspondence pages. **The url is the probe and
  the probe is the row.**
- **Benign natural-key duplicates are explained rather than removed**: 652 in
  `fr_consultation_referenced` (the FR reissues identically titled NAGPRA
  notices for different collections), 17 in
  `correspondence_foia_source_coverage`, 5 in `fr_consultation_year`. **Zero
  literal duplicate rows across all 22 tables.**

---

## 6. Known limits

- **Field population** varies enormously and the shipped sample hides it:
  `html_url` and `json_url` 100% · `agency_names` 99.4% · `pdf_url` 98.1% ·
  `abstract` 83.2% · `action` 82.6% · `dates` 80.7% · `docket_ids` 67.1% ·
  `cfr_references` 41.2% · `effective_on` 28.0% · `regulation_id_numbers`
  25.7% · **`comment_url` 0.7% — effectively unpopulated. Do not build a
  comment-deadline product on it; parse `dates` instead.**
- **156,897 rows, 156,897 distinct `document_number`, 0 duplicates, 0 blank
  titles, 0 blank publication dates.** [measured]
- **`consultation_events.csv` is a NAGPRA table wearing a consultation label.**
  11,402 rows, of which **10,888 (95.5%) are `NAGPRA_consultation_reported`**,
  and **11,068 of 11,402 come from Interior alone** (HHS 99, EPA 43, Commerce
  30, Energy 23). Actual policy consultation is `consultation_session` 212,
  `consultation_notice` 180, `listening_session` 37, `NHPA_section_106` 20,
  `negotiated_rulemaking` 14 and **`dear_tribal_leader_letter` 6.**
  `tier = B` on all 11,402.

  **UPDATED 2026-09-02, workstream FR-DTLL** — three of the claims in this
  bullet were re-measured and two of them moved.

  1. **"A NAGPRA table" is right about ROWS and wrong about DOCUMENTS.** The
     10,888 are one row per (notice, participant) and reduce to **1,831
     distinct notices**; **10,920 of 11,402 rows (95.8%) name a document
     `nagpra_notices.csv` also ships**, and **4,961 of the 6,792 NAGPRA
     notices are not represented here at all.** So this file sees **27.0% of
     the NAGPRA notice universe**, not a copy of it. The overlap is now
     `nagpra_notice_overlap` and `nagpra_bridge_overlap`, **columns on the
     row**, plus `fr_document_number` — the join key this table never had —
     written by `code/1089_fr_consultation_overlap_and_event_parse.py` and
     stated in codebook block `09c_consultation_events`, so a buyer holding
     both datasets cannot double-count from prose alone.
  2. **The NAGPRA coverage is a WINDOW and it is BROKEN AT THE HEAD.**
     1994–2010: **0 of 1,882**. 2011–2022: **1,817 of 2,264 (80.3%)**.
     2023–2026: **14 of 2,646 (0.5%)**. `96`'s universe is
     `fr_consultation_referenced.csv`, which finds notices by the *"in
     consultation with representatives of"* drafting convention — and revised
     43 CFR 10, effective **2024-01-12**, replaced that sentence with the
     bulleted "Determinations" list. **The net stops catching notices exactly
     as NAGPRA volume triples.** Written on the row as
     `nagpra_coverage_window`.
  3. ***"DOI alone posts dozens a year outside the Federal Register"* was an
     inference from a count of 6 and it was the wrong shape.** `962` measured
     the Federal Register itself at **46** documents containing the phrase, so
     the six is a faithful reading of the FR — the FR is simply the wrong
     ceiling. `code/1090_dtll_agency_harvest.py` then went to the publishers:
     **597 letters, 2000-01-10 to 2026-08-25 — IHS 574, BIE 14, BIA 9 —** in
     the new table `dear_tribal_leader_letters.csv`. **The largest single
     cause of the old six was an HTTP 406 on `ihs.gov` recorded as
     `NOT_CHECKED`**; it was a request-header shape, and behind it sat IHS's
     own 27-year `Dear Tribal Leader Letters` series. The letters are a
     separate table, not appended rows, because `96` owns and rebuilds
     `consultation_events.csv`.
- **The consultation's own date and place are still mostly absent, and the
  remaining absence is now sized.** `notice_date` is when the *notice*
  published. `event_start_date` was filled on **93 of 11,402 rows** and
  `location` on **60**; `1089` parsed the 2,313 notice texts already on disk
  and took them to **190** and **103**. Both are still under 2% of rows, and
  the reason is structural rather than parsing: **10,888 rows are NAGPRA
  notices REPORTING that consultation happened, and such a notice states
  neither when nor where.** Against the 484 non-NAGPRA documents the figure is
  **190 of 484 documents dated**. Every filled cell carries the notice's own
  sentence in `event_date_source_quote` / `location_source_quote`; a blank
  still means the notice did not say. **A measured trap, recorded because it
  fires silently:** an unanchored place regex filled 657 NAGPRA rows with
  museum contact addresses and excavation counties — *"Cambridge, MA"* from
  *"should contact Patricia Capone, Peabody Museum"*, *"Coconino County, AZ"*
  from where remains were removed in 1985. Both are places the notice prints;
  neither is where a consultation was held. A location is now read only from a
  notice that announces an event.
- **`participant_role` is an inference presented as a fact in the shipped
  sample.** `consulted` 9,110 · `invited_did_not_participate` 1,211 ·
  `not_enumerated` 1,006 · `invited` 75 — a real and useful distinction derived
  from notice language. The table carries `match_method`, `confidence`, `tier`,
  `source_url` and `source_quote`; the sample shows the conclusion and none of
  the four columns supporting it. **`invited_did_not_participate` is a claim
  about a named tribe's conduct and should never ship without its quote.**
- **`section_106_consultation_events.csv` is 1,367 rows, and only 154 of them
  are `PROJECT_UNDERTAKING`** — actual project-level consultation. The rest:
  `STATUTORY_REFERENCE_ONLY` 597 (a grant notice reciting a Section 106
  compliance condition), `AGREEMENT_DOCUMENT_REFERENCE` 355,
  `CONSULTATION_PROCESS_RECORD` 154, `PROGRAM_ALTERNATIVE` 107. **1,130 rows
  have `match_method = no_tribe_named_in_published_text`**; tier C 1,130 / B
  134 / A 103; 85 distinct tribes, 32 lead agencies. `is_lobbying = 0` on every
  row of both consultation files — *a licensee invited to develop a Programmatic
  Agreement with four tribes is discharging an obligation under 36 CFR 800.*
- **`cedar_uid` coverage varies by table**: 0% on `fr_ex_parte_parties.csv` and
  `section_106_project_parties.csv`; 17.3% on
  `section_106_consultation_events.csv`; 91.2% on `consultation_events.csv`.
  **The shipped `dist/cedar_press.db` is one stamp behind** — 28 columns on
  `consultation_events` against 29 live.
- **`consultation_agency_coverage.csv` (66 rows) is UNDOCUMENTED and not
  shippable** — `96` writes it, nothing declares its grain, and it sits outside
  the 22 customer tables.
- **`_shard_manifest.csv` under-reports the FR cache by eleven shards.**
  Anything counting the corpus must read the directory, not the manifest.
- **The Federal Register is not the universe.** Land can enter trust without a
  proclamation. Proceedings assembly — a `related_action_id` chaining a docket
  through its actions — is phase 2 and unbuilt; the chain keys exist
  (`regulation_id_numbers` 25.7%, `docket_ids` 67.1%).

---

## 7. Refresh

| source | cadence | Cedar holds | source has | state |
|---|---|---|---|---|
| federalregister.gov API | **every federal business day**; public inspection the day before | 2026-09-01 | 2026-09-01 | ✅ **0-day gap** |
| BLM/DOI NEPA ePlanning | continuous, as projects are registered | 2026-08-12 | — | source edge not established |

[measured — `docs/REFRESH_CADENCE.json`, regenerated 2026-09-02]

**Command:** `py -3 code/342_pull_federal_register_incremental.py`, then
`code/751_fr_refresh_promote.py consultation|restamp|all`. Cost: minutes, about
one API page a day. **Never `10`, never `11`** — see §2.

**Tribal-consultation notices are 15 days behind** (`fr_consultation_notices.csv`
holds through 2026-08-18, 485 rows) and the lobbying source doc independently
calls that leg *"3 months stale; 29 agencies only."*

**What breaks if it is not re-pulled** is not primarily this dataset. *"You go
blind to the recognition-notice trigger that fires the spine rebuild"* — **a
new "Indian Entities Recognized" notice is how the entity layer learns that a
newly recognised tribe exists**, and the daily FR pull is what sees it. A
missed notice means every dataset that later meets that tribe records an
`unresolved` scope.

A refresh also rebuilds `fr_content_classification.csv` (via `78`, which also
touches five lobbying tables), and the `130`, `76`, `98`, `133` and `136`
builds — each a separate owner's build, which is why `751` exists to write a
named subset rather than letting `78` run whole.

---

## 8. What READY required, and why this dataset cleared it

The scoreboard emits three statuses and no fourth, against a ten-point
contract. Both of the datasets that cleared it first —
`federal-register` and `nagpra` — cleared it on the same point: **C5, row
conservation.**

Row conservation is where most collections die, and these two are the only ones
at **100%**. `code/519_closure_federal_register.py conserve` writes a durable
per-dataset ledger (`review/federal_register_row_conservation.csv`) that
reconciles `rows_in == sum(dispositions)` within one key, and **a reason of
`other`, `unknown` or `misc` is refused by name, because an unnamed rejection
is exactly the defect the ledger exists to catch.** It is gated by
`510_assertions.py` invariant I13 and by `62_no_regression_check.py`'s
`harvest_rows_unaccounted`, which must be zero.

Comparing the four datasets in this family makes the point:

| | federal-register | nagpra | lobbying | legislation |
|---|---|---|---|---|
| status | READY | READY | READY | **BLOCKED** |
| tables | 22 | 4 | 33 | 12 |
| grain / keys | 22/22 | 4/4 | 33/33 | **11/12** |
| C4 identity | 88% [mixed] | **93% [entity]** | 41% [mixed] | 100% [indian_country] |
| **C5 conservation** | **22/22** | **4/4** | **3/33** | 2/12 |
| identity model | **source_record_link_v1** | legacy_fused | legacy_fused | legacy_fused |
| replay | not replayed | **captured** | not replayed | not replayed |

**Lobbying reached READY at 3 of 33 on conservation only because C5 is not a
blocker at the scoreboard's current thresholds** — worth stating, because it is
the difference between one READY and another.

---

## Stale claims found while writing this

1. **Every document quoting `federal_actions.csv` at 156,772 rows is one
   refresh behind**, including `docs/DOC_CONTRADICTIONS_2026-08-26.md`'s
   evening addendum — which was itself written *to correct* the build log's
   156,452. Measured **156,897**, after a second increment on 2026-09-01. The
   same is true of `federal_actions_raw.csv`.
2. **`docs/datasets/federal-register.md` §8 says "320 documents have no
   `fr_content_classification` row."** Measured **0** —
   `fr_content_classification.csv` is now 156,897 rows with **0 unclassified**,
   caught up by the 2026-09-01 promote.
3. **`docs/NAGPRA_BUILD_LOG.md`'s provenance section gives the universe as
   156,452 FR documents.** It is **156,897** — and the NAGPRA universe is
   title-anchored on this file, so it moves whenever this one does.
4. **`docs/SECTION_106_BUILD_AND_MERGE_PROPOSAL.md` is correct at 1,367** and
   the widely repeated 1,363 is the stale figure. Noted in the opposite
   direction from the rest of this list, because a reader chasing the
   discrepancy should know which side is right.
5. **`docs/FEDERAL_ACTIONS_BUILD_LOG_2026-08-05.md` quotes pre-refresh counts
   throughout** and predates two increments.
6. **`docs/REFRESH_CADENCE.md` correctly warns against running `10` or `11`**,
   and that warning has held — worth recording as a doc claim that verified.
