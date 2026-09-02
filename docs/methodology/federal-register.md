# Methodology — Federal Register

<!-- BEGIN GENERATED:IDENTITY -->

**`federal-register` — Federal Register.** Delivered as `dist/customer/federal-register.csv`: **11,402 rows × 43 columns, 16.6 MB**, built from the flagship table `data/clean/consultation_events.csv`. Shelf `standard`; sold through **Cedar Press**; on the Cedar Press storefront. Readiness **READY**. [measured 2026-09-02 from the delivered file]

> **This block and Appendix M at the foot of this paper are GENERATED** by `code/1143_methodology_papers.py` from the delivered file itself, on every build — the same reason the codebooks are generated. Do not hand-edit either; the next build overwrites them.
>
> Everything between `<!-- BEGIN EDITORIAL:federal-register -->` and `<!-- END EDITORIAL:federal-register -->` is **hand-written and preserved byte-for-byte** across rebuilds. Put prose there and nowhere else.
>
> This paper is **not** the codebook. `dist/customer/federal-register__CODEBOOK.md` carries the grain, the folded-in tables and the per-column fill rates, and `__NOTES.txt` carries the same for a person. This paper says how the dataset came to exist and why you should believe it.
>
> Generated 2026-09-02. `py -3 code/1143_methodology_papers.py verify` **fails** if the delivered file has moved since — see §M7.

<!-- END GENERATED:IDENTITY -->

<!-- BEGIN EDITORIAL:federal-register -->
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
> **CORRECTED 2026-09-02 — Dear Tribal Leader letters.** `dear_tribal_leader_letters.csv` holds **807 ROWS** and **597 LETTERS**. The other 210 are 209 enclosure, 1 publisher_index_page. `record_kind` is the discriminator and it is on every row, so there is no excuse for either number appearing without its noun. Agencies: Indian Health Service 783, Bureau of Indian Education 14, Bureau of Indian Affairs 10. **The '46-document Federal Register ceiling' is the wrong ceiling entirely** - it counted one publication venue, and the letters are published by the agencies on their own sites; an agency's own newsroom is not the Federal Register's to cap.

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
<!-- END EDITORIAL:federal-register -->

<!-- BEGIN GENERATED:MEASURED -->

---

# Appendix M — measured from the delivered file

*Generated 2026-09-02 by `code/1143_methodology_papers.py` from `dist/customer/federal-register.csv`, read whole with duckdb and never sampled. Not from `data/clean/`, not from a build log, not from `MANIFEST.csv`. Where this appendix and a document disagree, **the delivered file is right** and `verify` prints the disagreement rather than smoothing it over.*

*Grain, folded-in tables and per-column fill rates are in `dist/customer/federal-register__CODEBOOK.md` and are deliberately not repeated here.*

## M1 · Sources, as the delivered rows themselves record them

**`source_url`** — 11,402 of 11,402 rows carry one. Hosts, by row count:

| host | rows |
|---|---:|
| `www.federalregister.gov` | 11,402 |

**`fetched_date`** — 11,402 of 11,402 rows populated, 1 distinct value:

| value | rows |
|---|---:|
| `2026-08-07` | 11,402 |

### The terms rulings that bind this dataset

Quoted from `docs/PUBLICATION_POLICY.md`, which holds the rulings; this paper does not restate them from memory.

- **Owner ruling, 2026-09-02** (`<!-- BEGIN TERMS-OWNER-RULING-2026-09-02 -->`): *"So tribal websites, I actually don't care if they say it does scrape. Because if it's publicly available and you can scrape it, scrape it."* A tribal entity's own public pages may be harvested regardless of a terms statement. `source_terms_status = TERMS_STATED_RESTRICTIVE` on a Native entity's own site is now **a recorded observation, not a gate**.
- **Four things that ruling does NOT touch, and none is a terms question:** (1) technical access controls — nothing login-gated, no admin or staging paths, no exploiting a misconfiguration; (2) a natural person's data held apart from their public role — home address, personal email or phone, DOB, SSN/TIN; (3) non-tribal licensors — EMMA/MSRB bars redistribution of its output "sold or free of charge" and names "any manual process", with CUSIP Global Services as a second licensor; (4) proprietary identifiers — Casino City, D-U-N-S — held internally, never shipped.
- **A terms restriction is scoped to the SOURCE that stated it, not to the nation** (`<!-- BEGIN TERMS-SCOPE -->`), and it does not bind a third party's filing of the same fact.

## M2 · How the rows were built — the pipeline, in order

**One documented rebuild:** `py -3 code/build.py run federal-register --execute`. `py -3 code/build.py plan federal-register` prints the ordering below live; it is reproduced here so the paper stands alone.

The collection holds **29 tables**. Those with a named build stage, flagship first:

| table | rebuilt by | then enriched by (must run LAST) | status |
|---|---|---|---|
| `consultation_events.csv` **(flagship)** | `96_build_consultation_events.py` | `1089_fr_consultation_overlap_and_event_parse.py`, `503_identity.py` | shippable |
| `federal_actions.csv` | `11_classify_federal_actions.py` | `22_apply_temporal_floor.py` | shippable |
| `federal_actions_entity_bridge.csv` | `70_key_unjoined_datasets.py` | `503_identity.py` | shippable |
| `fr_ex_parte_parties.csv` | `154_build_fr_ex_parte_notices.py` | `503_identity.py` | shippable |
| `fr_ex_parte_party_entity_links.csv` | `154_build_fr_ex_parte_notices.py` | `503_identity.py` | shippable |
| `nepa_administrative_record_parties.csv` | `134_build_nepa_eplanning.py` | `503_identity.py` | shippable |
| `section_106_consultation_events.csv` | `130_build_section_106_consultation.py` | `503_identity.py` | shippable |
| `section_106_project_parties.csv` | `130_build_section_106_consultation.py` | `503_identity.py` | shippable |

**A full rebuild and an in-place enricher on one file need an ordering, and the enricher must run LAST.** A `.bak_*_pre<script>` file sitting beside a table is the signal that an enricher has touched it since the last build. This has cost this project four reverts of one file in a single day.

The delivered spreadsheet is then assembled by `code/1137_customer_dataset_combine.py`, which folds supporting tables onto the flagship **only where the measured cardinality on the shared key is one**, reverts any join that moved the row count, and prefixes every joined column with its source table's stem. One-to-many tables contribute a count column instead of rows, so a money total cannot be multiplied by a join.

## M3 · How entities were attributed

Cedar keys every dataset to one identity layer. `cedar_uid` is permanent and never reused; the human-readable handle retires when an entity is reclassified, so **join on `cedar_uid`, never on the handle**. A compound handle is canonical, not broken — stripping a suffix to make a join work turns joinable rows into unjoinable ones while looking like a normalisation.

**Entity attachment in the delivered file:**

| key column | rows carrying one | distinct values | coverage |
|---|---:|---:|---:|
| `cedar_uid` | 10,396 | 396 | 91.2% |
| `tribe_id` | 10,396 | 396 | 91.2% |

**An unkeyed row is often the right answer, not a defect.** ADR-010 separates *"we could not identify the entity"* — a defect — from *"there is no single entity to identify"* — the correct representation. Coverage is measured against the *resolvable* denominator, not the row count.

### What `attribution_method` means **in this dataset**

`docs/schema/attribution_method_vocabulary.json`, declared 2026-09-02: *"`attribution_method` is three different columns sharing a name — a join method, an evidence provenance, and a name-match algorithm. Each table is gated against its OWN vocabulary."* Reading one table's sense into another is how a containment match came to key a dollar.

**This dataset carries no `attribution_method` column.** The identity evidence it does carry is measured below. Do not import another dataset's term list to interpret it.

**And a RULED METHOD IS NOT A POSITIVE RULING.** `attribution_method` says WHO decided; `confidence_tier` says WHAT was decided. All 317 `elijah_ruling` EIN rows in the ledger are tier **X** — *negative* — and a script that read "the method is in the RULED set" as "the answer was yes" published 317 owner *exclusions* as confident attributions. Standing detector: `py -3 code/293_lint_bug_classes.py`. [from the record — `START_HERE.md`, defect class 1b]

### Every identity, tier and method column, measured

- **`match_method`** — 10 distinct values: `fr_official_name` 8,251 · `no_participants_named_in_record` 1,006 · `fr_official_prefix` 759 · `name_head` 650 · `government_class_core` 477 · `resolve_entity_alias` 136 · `government_class_core_via_former_name` 57 · `constituent_band_in_parenthetical` 55 · `exact_canonical` 10 · `name_head_via_former_name` 1

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

The row gate is `code/cedar_publication.row_ok`, applied identically by every publisher: a row is withheld if `publishable` is set to anything outside `{Y, y, 1, true, TRUE, blank}`, or if `source_terms_status` is outside `{SILENT, TERMS_STATED_NO_REUSE_RESTRICTION, blank}`. **A blank gate column means the gate was never evaluated for that row, not that it failed.**

Two families are refused as **COLUMNS** rather than as rows, by `cedar_publication.publishable_columns`, because the row is ours and the field is not: the proprietary identifiers (`casino_city_id` — Casino City Press; the D-U-N-S family — Dun & Bradstreet), and personal data held apart from a public role (`owner_name_raw`, `email`, `phone`, `home_address`, `personal_email`, `ssn`, `tin`, `date_of_birth`, `officer_name`, `contact_name`).

**The personal-data family became a column drop on 2026-09-02, and the change is worth understanding.** Until then it was a row gate only, and measured against the live tree that published **5 of the 587 rows** of `bia_tribal_leaders_directory.csv` — every row carrying a phone or an email was withheld whole — *and shipped the `phone` and `email` headers anyway on the five survivors*. Both halves of that were wrong. A tribal leader's name and office is a PUBLIC ROLE and belongs in the dataset; the phone number is the thing that must not travel. Dropping the field keeps 587 rows and publishes no contact data, where the row gate kept 5 rows and still advertised two contact columns. `row_ok` keeps its check as a **backstop**, for a personal field arriving under a name the list does not yet know. [from the record — the docstring of `cedar_publication.publishable_columns`, 2026-09-02]

### Known gaps — every line in `docs/WHAT_IS_MISSING.md` that names this dataset or its flagship

- **L518** *(under “`federal-register` — `consultation_events.csv`, 11,402 rows”)* — ## `federal-register` — `consultation_events.csv`, 11,402 rows

### Open issues — every line in `docs/KNOWN_ISSUES.md` that names this dataset or its flagship

- **L292** *(under “A11 · S3 · `START_HERE.md` said READY 0 / 13”)* — Live: **READY 2 / 13** (`nagpra`, `federal-register`). The line sat inside the
- **L620** *(under “E. Standing conditions — true, known, not defects”)* — list --unverified`) — `nagpra` closure, `federal-register` closure, the
- **L1450** *(under “The data side, adjacent and NOT the same defect”)* — `section_106_consultation_events.csv` (192 NUL bytes across 87 lines),
- **L1547** *(under “DID THE BEHAVIOUR CHANGE WHEN IT BROKE? Per site, on the live data.”)* — it was written. Seven `consultation_events.csv` rows carry the result, and
- **L1637** *(under “Flagged, not deleted”)* — `consultation_events.csv` locations the repaired `STREET_TOKEN` refuses (with

## M5 · The money rules — which columns may be summed

**This dataset carries no numeric money column.** Nothing in it may be presented as a dollar total, and a reader who needs one has to go to the money dataset that holds it. A structure or directory table with no money column is not an incomplete money table.

### The fence, quoted verbatim from `docs/MONEY_TOTALLING_RULES.md`

That document is authoritative on which columns may be summed. It is **quoted here, never re-derived** — re-deriving a totalling rule from the data is precisely the error it exists to prevent.

**`docs/MONEY_TOTALLING_RULES.md` states no one-line rule for `consultation_events.csv`.** Where this dataset carries a money column and the rules document does not fence it, treat that as an open item, not as permission.

## M6 · Known limits, stated plainly

**Readiness: READY.** [measured — `docs/DATASET_READINESS.md`, regenerated by `py -3 code/518_dataset_readiness.py`]

| tables | grain | keys | duplicates | agg-unsafe | rebuild |
|---|---|---|---|---|---|
| 23 | 23/23 | 23/23 | clean | 0 | declared  |

The twelve-point contract a dataset is held to — grain declared and validated; keys and cardinality measured, not guessed; duplicates removed or the distinguishing dimension declared; entity attachment where the subject is an entity; every harvested row in a named disposition bucket; unresolved identity conflicts never shipping as definite facts; no double-counting path; one documented rebuild that does not destroy later enrichment; an update runbook another session can execute from the document alone; regression and semantic-diff gates over the outputs; column hygiene; and an inclusion basis on every row.

**Do not sell past the evidence.** Where this paper states a figure it was measured on the date stamped beside it, from the file named beside it. Where it states a decision it names who made it. Anything not stated here is not known.

## M7 · Fingerprint — what makes this paper stale

`verify` re-measures the four values below against `dist/customer/federal-register.csv` and **exits 1 if any has moved**. A methodology paper is stale the moment its dataset is rebuilt, and a stale paper that cannot say so is worse than no paper.

```json
{
  "dataset": "federal-register",
  "file": "dist/customer/federal-register.csv",
  "bytes": 16575607,
  "rows": 11402,
  "columns": 43,
  "header_sha256": "5829a5d8907a227fbc95ec2c4ec09e66b96b7ee2d562cc49bc8d0ff5030a3940",
  "measured": "2026-09-02"
}
```

Cross-check against `dist/customer/MANIFEST.csv`, which `code/1137_customer_dataset_combine.py` wrote at build time: it records **11402 rows × 43 columns**. The two agree.

<!-- END GENERATED:MEASURED -->
