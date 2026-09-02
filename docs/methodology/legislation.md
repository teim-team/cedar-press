# Methodology — Native Legislation and Votes

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

**Readiness: BLOCKED**, on exactly one table. [measured —
`docs/DATASET_READINESS.md`, regenerated 2026-09-02: 12 tables, grain 11/12,
keys 11/12, duplicates clean, C4 **100% keyed [indian_country]**] The blocker
is `congressional_correspondence_log.csv`, which has **zero rows** — see §6.

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

`bill_scope` [measured]: `general` **2,417** · `tribe-specific` **484** · blank
168. A bill is tribe-specific if its title contains a spine name — canonical or
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
- **Nine votes read `Failed` with more yea than nay**, and there is no column
  explaining why. `H105-0482` is 229 yea to 176 nay and **correctly Failed**,
  because suspension of the rules requires two-thirds. There are nine such rows
  (`H097-0770`, `H099-0529`, `H100-0889`, `H101-0788`, `H105-0482`,
  `H105-0568`, `H108-0229`, `H109-1107`, `H112-1442`) and **no
  `threshold_required` column exists.** A buyer will file it as a bug. The
  threshold is derivable from `question` — 87 votes contain "suspend" — and
  belongs on the row.
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
- **`native_bills.title` covers only 390 of the 423 votes**, and the shipped
  sample of `bill_votes.csv` shows `114-hr-360` and *"On Motion to Suspend the
  Rules and Pass, as Amended"* — a buyer cannot tell what was voted on. This is
  the cheapest high-value join in the thirteen datasets and it has not been
  made.
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
4. **`docs/WHAT_IS_MISSING.md` describes the nine anomalous `Failed` votes and
   the absent `threshold_required` column accurately**, and the derivation
   (87 votes whose `question` contains "suspend") has not been done.
