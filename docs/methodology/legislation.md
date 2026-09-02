# Methodology — Congressional Votes and Proposed Legislation

<!-- BEGIN GENERATED:IDENTITY -->

**`legislation` — Congressional Votes and Proposed Legislation.** Delivered as `dist/customer/legislation.csv`: **3,069 rows × 39 columns, 3.3 MB**, built from the flagship table `data/clean/native_bills.csv`. Shelf `standard`; sold through **Cedar Press**; on the Cedar Press storefront. Readiness **READY**. [measured 2026-09-02 from the delivered file]

> **This block and Appendix M at the foot of this paper are GENERATED** by `code/1143_methodology_papers.py` from the delivered file itself, on every build — the same reason the codebooks are generated. Do not hand-edit either; the next build overwrites them.
>
> Everything between `<!-- BEGIN EDITORIAL:legislation -->` and `<!-- END EDITORIAL:legislation -->` is **hand-written and preserved byte-for-byte** across rebuilds. Put prose there and nowhere else.
>
> This paper is **not** the codebook. `dist/customer/legislation__CODEBOOK.md` carries the grain, the folded-in tables and the per-column fill rates, and `__NOTES.txt` carries the same for a person. This paper says how the dataset came to exist and why you should believe it.
>
> Generated 2026-09-02. `py -3 code/1143_methodology_papers.py verify` **fails** if the delivered file has moved since — see §M7.

<!-- END GENERATED:IDENTITY -->

<!-- BEGIN EDITORIAL:legislation -->
**`legislation`. `data/clean/native_bills.csv`, 3,069 bills across Congresses
93–119; `bill_votes.csv`, 423 roll calls; `member_positions.csv`, 136,119
member-vote rows.** [measured 2026-09-02]

*Written 2026-09-02. This is the methodology record: what was pulled and from
where, how the rows were made, how records were scoped, what was decided and
why, what the known limits are, and how often it has to be re-pulled. It is not
the product copy (`docs/datasets/_descriptors.json`) and not the codebook
(`docs/codebooks/`).*

**A note on the figures.** `[measured]` means the figure was re-counted from
the live file with `csv.reader` on 2026-09-02. `[from the record]` means it
came from a build log or docstring without independent measurement. Where a doc
and the data disagreed, the measurement won; the disagreements are listed at
the end.

**Readiness: READY**, 11 tables. [measured — `py -3 code/518_dataset_readiness.py`,
re-run 2026-09-02 after this section was first written: `READY  legislation
11 tables  maintain`.] The earlier BLOCKED reading in this file was against a
12-table scoreboard whose blocker was `congressional_correspondence_log.csv`,
a zero-row table — see §6, which is kept because the *reasoning* about an
empty table is still the reasoning.

---

## The scoping decision this dataset exists to demonstrate

**Most legislation affecting Indian Country names no single tribe, and an
unattached row here is the correct representation rather than a gap.**

A bill that changes federal Indian law affects all 574 federally recognised
tribes. Under an earlier framing that treated every unkeyed row as a defect,
`legislation` would have been pushed toward *inventing* an entity attribution
to clear a blocker — the exact failure the project's first rule forbids.
ADR-010 settles it: `record_scope = indian_country` is an **answer**, and
`unresolved` is the only scope that is a defect.

So `cedar_uid` is blank on all 3,069 rows of `native_bills.csv` [measured], and
the readiness scoreboard scores this dataset **100% keyed at scope
`indian_country`** — not 0%.

**Which makes `classification_source` the load-bearing column of the whole
dataset.** Where no entity can be named, the recorded basis for calling a bill
Native-relevant is the only evidence of scope a buyer has.

---

## 1. Sources

**Voteview** (Lewis, Poole, Rosenthal, Boche, Rudkin, Sonnet — voteview.com):
`HSall_rollcalls.csv` (113,066 roll calls), `HSall_votes.csv` (**26,262,296
member-vote rows**) and `HSall_members.csv` (51,053 member-Congress rows).
**All roll-call counts, dates, questions, results and member positions come
from these files** — not from Clerk XML and not from senate.gov LIS.

**Congress.gov API v3** — bill titles, CRS policy areas, sponsors, introduced
dates, latest actions and cosponsor rosters, Congresses 103–119.

**Upstream classification, imported rather than re-done.** The pro- and
anti-tribal codings were built in a separate project
(`C:\Users\esm247\Desktop\votingpatterns`). **Nothing there was modified.** All
21 source files were copied into `data/raw/external/votingpatterns/` with a
`SOURCE_MANIFEST.csv` carrying each original path, byte count, sha256-16 and
physical line count.

### What was deliberately not used, and the probe that settled it

**Clerk of the House EVS and Senate LIS were not used**, and the reason was
measured rather than assumed:

```
clerk.house.gov/evs/1990/roll001.xml  -> HTTP 200
clerk.house.gov/evs/1989/roll001.xml  -> HTTP 404
senate.gov/.../vote1011/...           -> HTTP 200
senate.gov/.../vote1002/...           -> HTTP 301 to roll-call-vote-not-available.htm
```

**The House EVS record begins with calendar 1990 and the Senate LIS with the
101st Congress — and that is exactly the 118 blank questions in the table:** 69
House roll calls before 1990 plus 49 Senate roll calls before the 101st = 118,
with **0 blanks inside the coverage window.** The gap is the publisher's, not
the pull's.

**Also deliberately not used:** the `analysis_panel*`, `district_*`, `tribe_*`,
compact, casino and gaming-revenue files from the upstream project, which were
present and belong to a different paper.

**Terms-restricted tribal sources** do not bite here at all: every source is a
federal record or an academic republication of one.

---

## 2. How the rows were made

`code/14_copy_votingpatterns_sources.py` → `code/14_build_bills_votes.py` →
`code/14_pull_cosponsors.py`; then `code/73_bills_votes_completion.py`, whose
stages are `--rollcalls --sweep --titles --actions --outcomes --bridge
--classes`.

> ⚠ **Both numbers collide.** `ls code/14_*` returns three files and
> `ls code/73_*` returns three (including `73_add_tcu_and_cdfi.py` and
> `73_faads_name_attribution.py`). Cite the filename.

### How `republican_yea_share` is computed, and the trap inside it

It is computed **from member-level cast codes, never from a published
summary**: stream 26.26M rows → keep the 423 tribal roll calls (136,471
member-votes) → drop `cast_code == 0` → **drop 352 presidential position rows**
→ join members on `(congress, chamber, icpsr)` → count cast codes 1 and 6 only,
carrying paired and announced positions (cast 2–5, 305 rows, 0.22%) in separate
columns.

**The presidential rows are identified by the explicit President ICPSR set from
`HSall_members.csv`, NOT by an `icpsr >= 99000` rule** — which would wrongly
delete Thurmond (99369), Deal (99342), Forbes (99542) and Goode (99767).

### The tables

| table | rows |
|---|---:|
| `native_bills.csv` | **3,069** |
| `native_bill_outcomes.csv` | 3,069 |
| `bill_votes.csv` | **423** (House 282 / Senate 141) |
| `member_positions.csv` | **136,119** |
| `native_bills_entity_bridge.csv` | 676, 154 entities |
| `bill_votes_entity_bridge.csv` | 75 |
| `bill_votes_official_verification.csv` | 305 |
| `native_bills_entity_class.csv` | 2,694 |
| `native_bills_subject_sweep.csv` | 2,409 |
| `native_issue_litigation_positions.csv` | 197 (coverage 8) |
| `congressional_correspondence_systems.csv` | 257 |
| `congressional_correspondence_log.csv` | **0** |

[measured]

---

## 3. How a bill is classified Native-relevant

Seven controlled `classification_source` values, with a measured κ where one
exists [measured distribution]:

| value | κ | votes | bills |
|---|---|---:|---:|
| `two_coder_adjudicated` | **0.952** | 212 | 110 |
| `two_coder_adjudicated_inherited_from_rollcall` | 0.952 | — | 53 |
| `two_coder_zero_overlap_adjudicated` | **−1.000 (undefined)** | 64 | 51 |
| `single_coded_8strategy_expansion` | — | 6 | 4 |
| `single_coded_keyword_rule` (Senate) | — | 141 | 63 |
| `congress_gov_policy_area_native_americans` (CRS) | — | — | **2,019** |
| `single_coded_keyword_rule_on_title` | — | — | 737 |
| `subject_family_phrase_sweep:*` | — | — | 32 |

**κ = 0.952** comes from `intercoder_report.txt` (2026-03-23): 246 House roll
calls, raw agreement 243 of 246 = 98.8%, with the three disagreements
adjudicated.

> **The caveat that must travel with the dataset, from the upstream report
> itself:** these are **AI-generated codings**, and a human federal-Indian-law
> expert should validate a subset before publication.

**κ = −1.000 is not a reliability failure.** The two anti-tribal coders
searched **disjoint spaces** — coder A substantive amendments, coder B
procedural motions to recommit — so overlap was zero by construction and the
statistic is undefined rather than bad.

`bill_scope` [re-measured 2026-09-02, after `code/1092_bill_titles_residue_and_scope.py`]:
`general` **2,569** · `tribe-specific` **500** · blank **0**. It read
`general` 2,417 · `tribe-specific` 484 · blank **168** until that run, and the
168 were not unrulable rows: **they were rows the ruler had never been run
on.** 128 got a title from the 2026-08-05 backfill and nobody replayed the
scope derivation, so they still said `bill_scope_basis = no_title_available`
while carrying a title — `93-hr-10337`, *"An Act to provide for final
settlement of the conflicting rights and interests of the Hopi and Navajo
Tribes…"*, among them. 32 more came in through `73 --sweep` with a blank
basis, and 8 had no title at all (see §6). A bill is tribe-specific if its title contains a spine name — canonical or
alias, at least 8 characters, matched on a word boundary, across 1,124 names —
or one of five designators (`Rancheria`, `Pueblo of X`, `Confederated
Tribes/Salish/Bands`, `Band of`, `Indian Colony`). **The matched string is
recorded per row** (`spine_name_match:Gila River`), which is what makes the
scope auditable.

### Member positions preserve Voteview's exact semantics

`member_positions.csv` — 136,119 rows = 423 votes × 2,583 unique members,
`bioguide_id` populated on 100%. `position` [measured]: Yea 82,199 · Nay 45,272
· Not Voting 8,312 · Announced Yea 150 · Paired Yea 61 · Paired Nay 59 ·
Announced Nay 35 · Present 31. Party D 72,331 / R 63,553 / I 235; House 122,019
/ Senate 14,100. `position_simple` folds the paired and announced categories.

**Yea counts sum exactly to `bill_votes.yea` on all 423 votes, 0 mismatches.**

`cosponsor_flag` is **blank on 21,830 rows, and blank is not zero** — it is 0
only on the 233 bills the API actually answered for.

---

## 4. Decisions that shaped the data

### 415 of 423 recounts match Voteview, and all 8 mismatches are explained

Every one of the eight is a **103rd-Congress House vote**. In the 103rd the
five territorial Delegates could vote in the Committee of the Whole; verified
on `H103-0228`, where Norton, de Lugo, Faleomavaega and Underwood vote Nay and
Romero-Barceló does not vote — exactly the +4 gap.

**Nothing was adjusted. Both numbers ship, with a `tally_matches_voteview`
flag**, and `docs/datasets/10_bills_votes.md` then says **never use
`voteview_yea_count`** — the Clerk's own record settled all eight for the
recount.

### Results were not derived from `yea > nay`, and the first fix was withdrawn in full

Most pre-1990 roll calls are motions to suspend the rules, which need
two-thirds. The obvious repair — fill a missing result from a Congress.gov
action on the same bill and the same date — was **withdrawn entirely, all 66
date-keyed fills**, after the filled rows were read: **three separate amendment
votes on H.R. 1426 on 1986-09-18 all got stamped `Passed` from the passage
action.**

**The rule is now IDENTITY, not adjacency**: the Congress.gov action must
contain a tally equal to that roll call's own yea–nay. **46 recovered; 72 left
blank.** `result` stands at 351 of 423. [measured — 72 blank]

### Questions are quoted, never paraphrased

Filled from Voteview's ICPSR `dtl_desc` as a **verbatim substring**, with
`question_source` recording it and a descriptive `question_family` sitting
**beside** the quote rather than replacing it.

### Direction circularity is flagged, not hidden

21 expansion votes had `anti_tribal_is_yea` assigned upstream **from the
observed partisan split** (Republican yea rate minus Democratic yea rate >
0.15), which is circular against any party-margin outcome. Those rows carry
`direction_circularity_flag = 1` and are **excluded** from
`republican_pro_tribal_share`.

### The "Senate gap" was investigated and does not exist

There are 141 Senate roll calls across Congresses 93–118. What *is* thinner is
Senate **direction**: 28 of 141 carry a coded `pro_tribal_is_yea`, and 113 are
`direction_source = unresolved_needs_hand_coding`. Senate classification is
single-coded.

### `native_bills_entity_class.csv` exists because the bill names no member

2,694 rows recording the **class** a bill reaches — every ANCSA village
corporation, every Native Hawaiian Organization — rather than a member of it.
**Turning a class into a member is the false attribution the bridge exists to
prevent.**

---

## 5. What a buyer may total

- **Bills and votes, not dollars.** There is no money column in this dataset.
- **`member_positions.csv` is the transaction grain**; `bill_votes.csv` is its
  roll-up and the two must not be unioned. The yea counts reconcile exactly, so
  either is usable — never both.
- **SIXTEEN votes read as failures on a majority tally, and the row now says
  why.** `H105-0482` is 229 yea to 176 nay and **correctly Failed**, because
  suspension of the rules requires two-thirds. This paragraph said *nine* and
  said no `threshold_required` column existed; both were true when written and
  neither is now.

  `code/890_bill_votes_threshold_and_titles.py` added `threshold_required`
  (official record on 305 votes, question-text derivation on 118) and
  `code/1093_bill_votes_majority_anomaly.py` added
  `result_contradicts_simple_majority`, `result_anomaly_class` and
  `result_anomaly_basis`. **Re-measured from the live file 2026-09-02:
  MAJORITY_YEA_BUT_REJECTED on 16 rows, MINORITY_YEA_BUT_AGREED on 0, N on
  335, NOT_TESTABLE_NO_RESULT on 72.** The composition is **9 + 5 + 2**:

  | class | n | votes |
  |---|---:|---|
  | `HOUSE_SUSPENSION_TWO_THIRDS` | 9 | H097-0770 H099-0529 H100-0889 H101-0788 H105-0482 H105-0568 H108-0229 H109-1107 H112-1442 |
  | `SENATE_CLOTURE_THREE_FIFTHS` | 5 | S102-0315 S104-0027 S109-0531 S115-0399 S115-0402 |
  | `SENATE_THREE_FIFTHS_NOT_IN_QUESTION_TEXT` | 2 | S108-0356 S114-0351 |

  **The nine were the House half. The two extra ones are the finding.**
  `S108-0356` (2003-09-23, 49–45, *Motion Rejected*) is a Congressional Budget
  Act point-of-order waiver on S.Amdt. 1734, *"To provide additional funds for
  clinical services of the Indian Health Service, with an offset"*;
  `S114-0351` (2016-02-02, 52–43, *Amendment Rejected*) is S.Amdt. 3030 to
  S. 2012 under a unanimous-consent 60-vote agreement. **Neither is a cloture
  motion and neither threshold appears anywhere in the question string** —
  both read `On the Motion` / `On the Amendment` — so a question-text-only
  derivation leaves exactly these two looking like data-entry errors. They are
  on the row only because senate.gov's own `majority_requirement` was joined
  from `bill_votes_official_verification.csv`, and both carry
  `threshold_agrees_with_official = N`.

  **The trap, restated because it has cost this dataset a count once already:
  `threshold_required` is a property of THE VOTE'S OWN RECORDED PROCEDURE, not
  of the chamber.** 311 of 423 votes are simple majority and 85 are
  two-thirds, in the same two chambers; `H095-0549` (376–19) contains "SUSPEND
  THE RULES" in its question and is a SIMPLE majority, because the question is
  *ordering a second* on the suspension motion. And the derivation is wrong on
  12 of the 92 Senate votes that can be checked against an official record —
  13%.

  Note that `result_reconciles_with_threshold` reads **Y on all 351 testable
  rows and N on none**, so it cannot tell a buyer which sixteen rows will look
  wrong to them. That is what `result_contradicts_simple_majority` is for.
- **`republican_pro_tribal_share` excludes the 21 circularity-flagged votes.**
  Recomputing it without that filter reproduces the circularity.

---

## 6. Known limits

- **Only 283 of 3,069 bills (9.2%) ever get a roll call; 2,189 (71.3%) die
  without any floor vote.** A vote-based series is a series about 9% of the
  legislation.
- **398 of 423 votes carry a `bill_id`** — Voteview records no bill number on
  25. 879 companion links exist, 35 of them pointing at a bill outside the
  table.
- **`bill_title` now covers 398 of the 423 votes** [measured 2026-09-02]. It
  read 390 until `code/1092_bill_titles_residue_and_scope.py` closed the
  eight, and the join itself was made by `code/890`. **All eight blanks had
  one cause and it was not the source:** every canonical congress.gov
  bill_type slug in `native_bills.csv` is 100% titled (`hr` 1651/1651, `s`
  1332/1332, `hres` 38/38, `hjres` 23/23, `sjres` 12/12, `sconres` 5/5) and
  every NON-canonical slug was 0% (`hre` 0/2, `hjr` 0/1, `treatydoc` 0/2,
  `treatydocno` 0/3). `code/14_pull_cosponsors.py` hard-codes an `ok_types`
  allow-list that `hre` and `hjr` — Voteview's abbreviations for `hres` and
  `hjres` — fail, and treaty documents are not on `/bill` at all. Asked with
  the right slug, and on `/treaty/{congress}/{number}`, all eight answered
  HTTP 200 first time.

  Two of the five treaty identifiers were **ambiguous** — Voteview writes
  `TREATYDOC1134` and `TREATYDOC1173` with no separator, so 1|134, 11|34 and
  113|4 all read the first. They were settled by evidence, not by
  plausibility: a candidate was accepted only where the treaty's own action
  list carried a Senate action on the roll call's date AND congress.gov's
  `congressConsidered` equalled the vote's Congress. `1134` is **Treaty Doc.
  113-4**, the Protocol Amending the Tax Convention with Spain; `1173` is
  **Treaty Doc. 117-3**, the Protocols on the Accession of Finland and Sweden
  to the North Atlantic Treaty.

- **The honest floor on the remaining 25 title-less votes: 22 of them are
  facts about the world.** Those 25 carry no `bill_id`, and Voteview records
  no bill number for any of them [verified against `HSall_rollcalls.csv`].
  **22 are votes on reservations to a resolution of ratification** — 17
  Panama Canal Treaty, 4 Neutrality Treaty, 1 US-UK tax treaty — where there
  is no bill and therefore no bill title: `SOURCE_DOES_NOT_PUBLISH`. **3 name
  a numbered measure inside their own question text** (`H100-0888`
  H.Con.Res. 331, `S100-0452` S.Res. 386, `S100-0417` six S.Res. adopted en
  bloc) and are `NOT_ACQUIRED` — their eight titles were fetched and are on
  disk at `data/raw/external/congress_gov/1092_title_residue_unlinked.csv`,
  deliberately **not promoted**, because promoting one means minting a
  `bill_id` and a `native_bills.csv` row and rebuilding `n_rollcalls`,
  `native_bill_outcomes.csv` and both entity bridges. That is a decision for
  `14_build_bills_votes.py`, not an enrichment. `S100-0417` adopted six
  resolutions on one roll call, so no single bill title is the right answer
  for that row at all.
- **The party split is on the table and not in the sample.** `D_yea`, `D_nay`,
  `R_yea`, `R_nay`, `present` and `not_voting` are populated on **all 423
  rows**, as are `republican_yea_share` and `pro_tribal_is_yea` (240). For a
  political-research buyer that is the reason to buy the dataset.
- **BLOCKED on one empty table, and the emptiness is the finding.**
  `congressional_correspondence_log.csv` is **0 rows, 24 columns** [measured].
  The scoreboard reports `C1 grain UNSTATED on 1` and `C2 no validated primary
  key on 1` — correctly, because *the file has zero rows, so every candidate
  key is vacuously unique and the data cannot evidence a grain.* **The
  emptiness is deliberate:** *"no agency in scope publishes the log itself, and
  a row is only written where a retrieved record names a congressional office
  as a party."* **Declaring a grain would clear the block; nothing needs to be
  acquired.**
- **The upstream BIA index defects, inherited and flagged rather than fixed.**
  `docs/VOTINGPATTERNS_BIA_INDEX_WARNING.md` records three, all upstream:
  1. **The BIA Office of Indian Gaming compact index has its `Tribes` column
     misaligned with its `Title` column on 61 of 1,189 rows (5.1%)** — verified
     against archived raw HTML, so **it is BIA's error**, not a parse artefact
     (Mohegan → Mississippi Choctaw, Mashpee → Mashantucket Pequot, Yurok →
     Yocha Dehe). Four upstream files the upstream README designates
     *cross-project authoritative* inherit it. **Cedar takes the tribe from the
     Title, keeps BIA's value in `bia_tribes_column` with a conflict flag, and
     modified nothing upstream** — the owner's call.
  2. **`tier2A_agent_verified_real` mislabels derived revenue**: 372 of 435
     rows are compact-rate inversions, and the *v2* vintage had labelled them
     honestly as `tier2b_reverse_engineered`. **The later audit made provenance
     less accurate, not more.**
  3. **The BIA gaming-decisions index has the same misalignment on 3 of 138
     rows (2.2%)** — *"two independent indexes with identical structural
     breakage points at a CMS-level problem, so any future BIA index scrape
     should be assumed to have it until checked."*

---

## 7. Refresh

**This is the one dataset whose source edge cannot be established, and the
reason is a missing key.**

| source | cadence | Cedar holds | state |
|---|---|---|---|
| Congress.gov API — bills, actions, cosponsors | continuous while Congress sits | 2026-04-16 | **source edge NOT ESTABLISHED** |
| Roll-call votes (Voteview) | republished after each Congress | 2025-05-06 | source edge not established |
| Congressional correspondence systems | irregular, per office | 2026-01-27 | published, not pulled |

[measured — `docs/REFRESH_CADENCE.json`, regenerated 2026-09-02]

**`api.congress.gov` requires a key and Cedar holds none.** Checked
2026-09-01: `CONGRESS_API_KEY`, `CONGRESS_GOV_API_KEY` and `DATA_GOV_API_KEY`
are all absent from the environment and from `.env.local`. `refresh_due` is
recorded as `no` **because "due" cannot be computed**, not because nothing is
owed. The 2026-08-05 cosponsor pull is the only live API call in the whole
dataset, and its key was read from the upstream project's `.env`, never printed
and never written.

**What breaks if it is not re-pulled:** Voteview republishes `HSall_*` after
each Congress, so **the roll-call universe freezes at the 119th and every new
Native bill becomes invisible.** The commands are
`code/14_build_bills_votes.py` then
`code/73_bills_votes_completion.py --rollcalls --sweep --titles --actions
--outcomes`. A refresh rebuilds `native_bill_outcomes.csv`,
`member_positions.csv` and the two entity bridges.

---

## Stale claims found while writing this

1. **`docs/BILLS_VOTES_BUILD_LOG_2026-08-05.md` gives `native_bills.csv` as
   3,037 rows.** Measured **3,069** — 32 added by the `73` completion pass.
2. **`docs/DATASET_READINESS.md`'s C4 line for this dataset reads "100% keyed
   [indian_country]"**, which is correct and easy to misread as a coverage
   claim. It means every row carries the correct *scope*, not that every row
   carries an entity — `cedar_uid` is blank on all 3,069 bills by design.
3. **The upstream `intercoder_report.txt`'s own caveat — that these are
   AI-generated codings needing expert validation — is not repeated in any
   Cedar-side document**, and it is the single most important caveat in the
   dataset. It is recorded here.
4. **`docs/WHAT_IS_MISSING.md` describes NINE anomalous `Failed` votes and an
   absent `threshold_required` column. Both statements are now stale**, and
   the count was never nine: it is **sixteen** (9 House suspensions + 5 Senate
   cloture rejections + 2 Senate three-fifths thresholds that appear nowhere
   in the question text). The derivation it proposes — "87 votes whose
   `question` contains 'suspend'" — is also the wrong rule: matching bare
   `suspend` catches `S095-0741`, a Panama Canal Treaty reservation reading
   "…SHALL BE SUSPENDED UNTIL SETTLEMENT", and matching `suspend the rules`
   alone mistypes `H095-0549`, an *order a second* motion decided by majority.
   Done 2026-09-02 by `code/890` and `code/1093`.

5. **A title backfill ran without replaying the derivation that depends on
   titles, and nothing caught it for four weeks.** 128 rows gained a `title`
   on 2026-08-05 and kept `bill_scope_basis = no_title_available`; 32 more
   arrived from `73 --sweep` with a blank basis.
   `code/287_build_dependency_manifest.py` exists for exactly this shape, and
   `bill_votes.csv` and `native_bills.csv` both had **no declared ordering at
   all** until 2026-09-02. Both are now in `cedar_pipeline.KNOWN_ORDERINGS`;
   the chain is **14 → 73 → 1092 → 890 → 1093**, enrichers last.

6. **`bill_scope` carries two ruler vintages, and it is flagged rather than
   repaired.** The scope ruler reads spine names out of
   `cedar_entity_spine.csv`, which has grown: it carried 3,717 usable names on
   2026-09-02. Re-running today's ruler over the 2,901 rulings made on
   2026-08-05 changes **76** of them. Those 76 were NOT re-ruled — that moves
   a published `tribe-specific` count and is an owner decision — and
   `py -3 code/1092_bill_titles_residue_and_scope.py verify` prints them every
   run. Two of the causes are spine-quality problems rather than new
   knowledge: an entity literally named **"Tribal Self-Governance"** matches
   14 generic bill titles and **"Native Health"** matches 7, and names that
   generic arguably belong in the ruler's `GENERIC` exclusion list. The 168
   rows 1092 ruled were ruled with the 2026-09-02 spine and stamped
   `scope_ruled_1092_2026-09-02` in `record_basis`; **152 of the 168 came back
   `no_specific_entity_matched`, which is vintage-safe in the only direction
   that matters** — a smaller spine cannot produce a match a larger one did
   not — so only the 16 `tribe-specific` rulings are vintage-sensitive.
<!-- END EDITORIAL:legislation -->

<!-- BEGIN GENERATED:MEASURED -->

---

# Appendix M — measured from the delivered file

*Generated 2026-09-02 by `code/1143_methodology_papers.py` from `dist/customer/legislation.csv`, read whole with duckdb and never sampled. Not from `data/clean/`, not from a build log, not from `MANIFEST.csv`. Where this appendix and a document disagree, **the delivered file is right** and `verify` prints the disagreement rather than smoothing it over.*

*Grain, folded-in tables and per-column fill rates are in `dist/customer/legislation__CODEBOOK.md` and are deliberately not repeated here.*

## M1 · Sources, as the delivered rows themselves record them

**`source_file`** — 3,069 of 3,069 rows populated, 3 distinct values:

| value | rows |
|---|---:|
| `tribal_bill_intros.csv` | 2,809 |
| `HSall_rollcalls.csv (via tribal roll-call classification)` | 228 |
| `all_bill_intros.csv via 73_bills_votes_completion.py --sweep` | 32 |

### The terms rulings that bind this dataset

Quoted from `docs/PUBLICATION_POLICY.md`, which holds the rulings; this paper does not restate them from memory.

- **Owner ruling, 2026-09-02** (`<!-- BEGIN TERMS-OWNER-RULING-2026-09-02 -->`): *"So tribal websites, I actually don't care if they say it does scrape. Because if it's publicly available and you can scrape it, scrape it."* A tribal entity's own public pages may be harvested regardless of a terms statement. `source_terms_status = TERMS_STATED_RESTRICTIVE` on a Native entity's own site is now **a recorded observation, not a gate**.
- **Four things that ruling does NOT touch, and none is a terms question:** (1) technical access controls — nothing login-gated, no admin or staging paths, no exploiting a misconfiguration; (2) a natural person's data held apart from their public role — home address, personal email or phone, DOB, SSN/TIN; (3) non-tribal licensors — EMMA/MSRB bars redistribution of its output "sold or free of charge" and names "any manual process", with CUSIP Global Services as a second licensor; (4) proprietary identifiers — Casino City, D-U-N-S — held internally, never shipped.
- **A terms restriction is scoped to the SOURCE that stated it, not to the nation** (`<!-- BEGIN TERMS-SCOPE -->`), and it does not bind a third party's filing of the same fact.

## M2 · How the rows were built — the pipeline, in order

**One documented rebuild:** `py -3 code/build.py run legislation --execute`. `py -3 code/build.py plan legislation` prints the ordering below live; it is reproduced here so the paper stands alone.

The collection holds **13 tables**. Those with a named build stage, flagship first:

| table | rebuilt by | then enriched by (must run LAST) | status |
|---|---|---|---|
| `native_bills.csv` **(flagship)** | `14_build_bills_votes.py` | `1092_bill_titles_residue_and_scope.py`, `35_entity_harvest.py` | shippable |
| `bill_votes.csv` | `14_build_bills_votes.py` | `1093_bill_votes_majority_anomaly.py`, `73_bills_votes_completion.py`, `890_bill_votes_threshold_and_titles.py` | shippable |
| `native_issue_litigation_positions.csv` | `139_build_litigation_positions.py` | `140_build_grantmaker_funding_flows.py` | shippable |

**A full rebuild and an in-place enricher on one file need an ordering, and the enricher must run LAST.** A `.bak_*_pre<script>` file sitting beside a table is the signal that an enricher has touched it since the last build. This has cost this project four reverts of one file in a single day.

The delivered spreadsheet is then assembled by `code/1137_customer_dataset_combine.py`, which folds supporting tables onto the flagship **only where the measured cardinality on the shared key is one**, reverts any join that moved the row count, and prefixes every joined column with its source table's stem. One-to-many tables contribute a count column instead of rows, so a money total cannot be multiplied by a join.

## M3 · How entities were attributed

Cedar keys every dataset to one identity layer. `cedar_uid` is permanent and never reused; the human-readable handle retires when an entity is reclassified, so **join on `cedar_uid`, never on the handle**. A compound handle is canonical, not broken — stripping a suffix to make a join work turns joinable rows into unjoinable ones while looking like a normalisation.

**The delivered file carries no `cedar_uid`, `tribe_id` or `owner_hub_cedar_uid` column.** Where a dataset names parties but keys none of them on the row, the link lives in a bridge table and the codebook says which. A pipe-delimited list of ids in a cell is **not** a join key; join through the bridge.

### What `attribution_method` means **in this dataset**

`docs/schema/attribution_method_vocabulary.json`, declared 2026-09-02: *"`attribution_method` is three different columns sharing a name — a join method, an evidence provenance, and a name-match algorithm. Each table is gated against its OWN vocabulary."* Reading one table's sense into another is how a containment match came to key a dollar.

**This dataset carries no `attribution_method` column and no tier or method column of any kind.** Its rows are not entity attributions — they are records of a published event, and the entity link, where there is one, is made through a bridge table rather than carried on the row. Do not import another dataset's term list to interpret it.

**And a RULED METHOD IS NOT A POSITIVE RULING.** `attribution_method` says WHO decided; `confidence_tier` says WHAT was decided. All 317 `elijah_ruling` EIN rows in the ledger are tier **X** — *negative* — and a script that read "the method is in the RULED set" as "the answer was yes" published 317 owner *exclusions* as confident attributions. Standing detector: `py -3 code/293_lint_bug_classes.py`. [from the record — `START_HERE.md`, defect class 1b]

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

- **L362** *(under “`legislation` — `bill_votes.csv`, 423 rows”)* — ## `legislation` — `bill_votes.csv`, 423 rows
- **L371** *(under “`legislation` — `bill_votes.csv`, 423 rows”)* — > from `native_bills.csv`. `890 verify` refuses any title that is not
- **L372** *(under “`legislation` — `bill_votes.csv`, 423 rows”)* — > byte-identical to the `native_bills.csv` value it cites.
- **L376** *(under “`legislation` — `bill_votes.csv`, 423 rows”)* — > > `TITLE_BLANK_IN_native_bills.csv`. **All eight are closed and that
- **L378** *(under “`legislation` — `bill_votes.csv`, 423 rows”)* — > > congress.gov bill_type slug in `native_bills.csv` is 100% titled and
- **L400** *(under “`legislation` — `bill_votes.csv`, 423 rows”)* — > > `bill_id` and a `native_bills.csv` row — a decision for
- **L462** *(under “`legislation` — `bill_votes.csv`, 423 rows”)* — as Amended"*. **`native_bills.csv` holds a title for 390 of the 423 votes
- **L749** *(under “THE SHORT LIST — what this week can fix without a single download”)* — | 7 | `legislation` | join `native_bills.title` and `.outcome` on `bill_id` | DONE — 398 of 423 titles (was 390; `code/890` made the join, `code/1092` closed the last 8) |

### Open issues — every line in `docs/KNOWN_ISSUES.md` that names this dataset or its flagship

- **L1431** *(under “~~STILL OPEN~~ REPAIRED 2026-09-02 — seven files, 41 bytes, ~~16~~ **15** lines”)* — | `code/76_build_recognition_history.py` | 2 | 836 | the `legislation` term in the recognition-instrument classifier |

## M5 · The money rules — which columns may be summed

**This dataset carries no numeric money column.** Nothing in it may be presented as a dollar total, and a reader who needs one has to go to the money dataset that holds it. A structure or directory table with no money column is not an incomplete money table.

### The fence, quoted verbatim from `docs/MONEY_TOTALLING_RULES.md`

That document is authoritative on which columns may be summed. It is **quoted here, never re-derived** — re-deriving a totalling rule from the data is precisely the error it exists to prevent.

**`docs/MONEY_TOTALLING_RULES.md` states no one-line rule for `native_bills.csv`.** Where this dataset carries a money column and the rules document does not fence it, treat that as an open item, not as permission.

## M6 · Known limits, stated plainly

**Readiness: READY.** [measured — `docs/DATASET_READINESS.md`, regenerated by `py -3 code/518_dataset_readiness.py`]

| tables | grain | keys | duplicates | agg-unsafe | rebuild |
|---|---|---|---|---|---|
| 11 | 11/11 | 11/11 | clean | 0 | declared  |

The twelve-point contract a dataset is held to — grain declared and validated; keys and cardinality measured, not guessed; duplicates removed or the distinguishing dimension declared; entity attachment where the subject is an entity; every harvested row in a named disposition bucket; unresolved identity conflicts never shipping as definite facts; no double-counting path; one documented rebuild that does not destroy later enrichment; an update runbook another session can execute from the document alone; regression and semantic-diff gates over the outputs; column hygiene; and an inclusion basis on every row.

**1 column is blank on every delivered row** and is kept deliberately. Dropping them would make the schema depend on which rows shipped, and a buyer diffing two deliveries would watch columns appear and vanish. Sparsity is a coverage fact. They are named in the codebook.

**Do not sell past the evidence.** Where this paper states a figure it was measured on the date stamped beside it, from the file named beside it. Where it states a decision it names who made it. Anything not stated here is not known.

## M7 · Fingerprint — what makes this paper stale

`verify` re-measures the four values below against `dist/customer/legislation.csv` and **exits 1 if any has moved**. A methodology paper is stale the moment its dataset is rebuilt, and a stale paper that cannot say so is worse than no paper.

```json
{
  "dataset": "legislation",
  "file": "dist/customer/legislation.csv",
  "bytes": 3278007,
  "rows": 3069,
  "columns": 39,
  "header_sha256": "b632f229223f329d2cedbb6737bc911917b5fb5087cd5ed36ff35e31a6affef3",
  "measured": "2026-09-02"
}
```

Cross-check against `dist/customer/MANIFEST.csv`, which `code/1137_customer_dataset_combine.py` wrote at build time: it records **3069 rows × 39 columns**. The two agree.

<!-- END GENERATED:MEASURED -->
