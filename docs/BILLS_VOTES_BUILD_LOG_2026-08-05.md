# Cedar Press Dataset 10 — Native Bills & Congressional Votes
## Build log, 2026-08-05

Companion to `docs/plans/BILLS_VOTES_DATASET_PLAN.md` and `AGENTS.md`. This was a completion-and-
productization pass, not a construction pass: the classification work already existed in
`C:\Users\esm247\Desktop\votingpatterns`. Nothing in that project was modified. Every source
file was copied out and every table below was built from the local copies only.

- Build scripts: `code/14_copy_votingpatterns_sources.py`, `code/14_build_bills_votes.py`,
  `code/14_pull_cosponsors.py`
- Run log: `logs/14_bills_votes_2026-08-05.log`, `logs/14_cosponsors_2026-08-05.log`
- Source manifest: `data/raw/external/votingpatterns/SOURCE_MANIFEST.csv`
  (original path, bytes, sha256-16, physical line count, copied date, for all 21 files)

### Primary sources
- **Voteview** (Lewis, Poole, Rosenthal, Boche, Rudkin, Sonnet), voteview.com/data —
  `HSall_rollcalls.csv` (113,066 roll calls), `HSall_votes.csv` (26,262,296 member-vote rows),
  `HSall_members.csv` (51,053 member-Congress rows). All roll-call counts, dates, questions,
  results, and member positions in this dataset come from these files.
- **Congress.gov API v3** (Library of Congress) — bill titles, CRS policy areas, sponsors,
  introduced dates, latest actions, and cosponsor rosters. Congresses 103–119.

---

## 1. Inventory of the existing build — and the "Senate gap"

### The Senate gap is NOT real. Both chambers are present.

The plan (`docs/plans/BILLS_VOTES_DATASET_PLAN.md`, "confirm: House in hand; Senate to verify") flagged a
possible missing chamber. It does not exist. `rollcalls_senate_tribal.csv` (141 Senate roll
calls, Congresses 93–118) and `senate_member_tribal_scores.csv` (2,652 senator-Congress rows,
Congresses 93–119) were both built on 2026-04-20 by
`votingpatterns/code/python/44_classify_senate_tribal_votes.py` and `45_build_senate_tribal_scores.py`,
replicating the House pipeline against `HSall_rollcalls.csv` filtered to `chamber == "Senate"`.
Bill introductions were never House-only either: `tribal_bill_intros.csv` is 1,538 House and
1,278 Senate bills.

What IS thinner on the Senate side, and should be stated instead of the chamber claim:
- **Vote direction**, not vote coverage. 28 of 141 Senate roll calls carry a coded
  `pro_tribal_is_yea`; the other 113 are flagged `needs_hand_coding` upstream and are carried
  here as `direction_source = unresolved_needs_hand_coding`. Senate direction was inherited from
  the House adjudicated file by bill number, so it only exists where a Senate bill also drew a
  House tribal roll call.
- Two Congresses have zero Senate tribal roll calls in the classified set: the 96th and the
  119th (the 119th is in progress).
- The Senate classification is single-coded (keyword rule). Only the House pro-tribal set went
  through two independent coders.

### What exists, verified file by file (local copies)

| File | Rows | Congresses | Chambers |
|---|---|---|---|
| `rollcalls_tribal.csv` | 212 | 93–118 | House |
| `rollcalls_all_tribal_classified.csv` | 276 | 93–119 | House |
| `rollcalls_senate_tribal.csv` | 141 | 93–118 | Senate |
| `rollcalls_anti_tribal.csv` | 81 | 93–119 | House |
| `anti_tribal_votes_expanded.csv` | 21 | 94–109 | House |
| `anti_tribal_votes_adjudicated.csv` | 9 | 94–109 | House |
| `tribal_votes_coder_A.csv` / `_coder_B.csv` | 246 each | 93–119 | House |
| `tribal_votes_adjudicated.csv` | 212 | 93–118 | House |
| `tribal_bill_intros.csv` | 2,816 | 103–119 | 1,538 H / 1,278 S |
| `all_bill_intros.csv` | 183,233 | 103–119 | both (hr, s, hjres, sjres) |
| `member_tribal_scores_v2.csv` | 11,203 | 93–118 | House |
| `senate_member_tribal_scores.csv` | 2,652 | 93–119 | Senate |
| `member_bill_intros_panel.csv` | 1,292 | 103–119 | 816 H / 476 S |
| `HSall_rollcalls.csv` | 113,066 | 1–119 | 59,650 H / 53,416 S |
| `HSall_votes.csv` | 26,262,296 | 1–119 | both |
| `HSall_members.csv` | 51,053 | 1–119 | both + President |

**Nothing was empty or unusable.** Two files needed care rather than exclusion:
- `anti_tribal_votes_adjudicated.csv` holds only 9 rows — the conservative adjudicated set, not
  a defect. The 81-row `rollcalls_anti_tribal.csv` and the 21-row expansion are the working sets.
- `tribal_bill_intros.csv` reads as 2,826 physical lines but 2,816 records (embedded newlines in
  titles). The manifest records physical lines; this log records parsed records.

Files present in `votingpatterns/data/processed/` but **not** used: the `analysis_panel*`,
`district_*`, `tribe_*`, compact, casino and gaming-revenue families. They belong to the
"Capacity to Matter" paper, not to the bills-and-votes tables.

---

## 2. Outputs

All three tables are in `data/clean/`. Plan-schema columns come first in every file; everything
after them is provenance or support, added so no ruling in the table is unexplained.

### `native_bills.csv` — 3,037 bills, Congresses 93–119
`bill_id, congress, chamber, number, title, policy_area, bill_scope, affected_entities, sponsor,
introduced_date, latest_action, outcome, companion_bill_id` + `bill_type, sponsor_bioguide_id,
latest_action_date, cosponsor_count, n_rollcalls, has_rollcall, bill_scope_basis, outcome_basis,
companion_basis, classification_source, classification_kappa, record_basis, source_file, build_date`

- `bill_id` format `{congress}-{type}-{number}`, e.g. `118-hr-7826`.
- 2,809 bills from the Congress.gov tribal-classified introductions (103rd–119th).
- 228 bills added because they carried a tribal roll call but were absent from that pull —
  mostly pre-103rd Congress (Congress.gov coverage in the upstream pull starts at the 103rd) and
  House resolutions (`hres`), which the upstream pull never requested. This is what keeps
  `bill_votes.bill_id` referentially complete.
- **`affected_entities` is deliberately blank.** Entity/spine linking is a separate build step.
- Chamber = **origin** chamber, derived from bill type. 1,704 House, 1,333 Senate.
- `bill_scope`: 2,417 general, 484 tribe-specific, 136 blank. The blank rows are pre-103rd
  Voteview-only bills with no title to rule on. Rule, recorded per row in `bill_scope_basis`:
  tribe-specific if the title contains a name from `data/spine/cedar_entity_spine.csv`
  (canonical or alias, ≥8 characters, word-boundary, 1,124 names) or one of five entity
  designators (`Rancheria`, `Pueblo of X`, `Confederated Tribes/Salish/Bands`, `Band of`,
  `Indian Colony`); otherwise general. The matched string is recorded, e.g.
  `spine_name_match:Gila River`, `designator_pattern:Rancheria`.
- `outcome`, from `latest_action` text with the rule recorded in `outcome_basis`:
  died-in-committee 2,209 · enacted 229 · passed-one-chamber 170 · pending 132 · vetoed 4 ·
  blank 293. "Pending" is reserved for the 119th Congress, which is still in session on the
  build date; a non-final action in a completed Congress is died-in-committee.
- `companion_bill_id`: 879 linked, by identical normalized title in the same Congress and the
  opposite chamber (`companion_basis` records the rule). 35 of those point at a bill that is not
  itself in `native_bills.csv` — a real Congress.gov bill that the tribal classifier did not
  select. The ID is still valid; it just does not resolve inside this table.
- 283 bills carry at least one tribal roll call. **The other 2,754 do not** — see caveat 1.

### `bill_votes.csv` — 423 roll calls, Congresses 93–119, House + Senate
`vote_id, bill_id, chamber, congress, rollnumber, date, question, result, yea, nay, present,
not_voting, D_yea, D_nay, R_yea, R_nay, I_yea, I_nay, margin, republican_yea_share` + 29
provenance columns (`vehicle_type, majority_side, question_source, result_source,
vote_description, vote_description_source, democrat_yea_share, republican_pro_tribal_share,
pro_tribal_is_yea, direction_source, vote_type, n_republican_voting, n_democrat_voting, U_yea,
U_nay, yea_paired_announced, nay_paired_announced, voteview_yea_count, voteview_nay_count,
tally_matches_voteview, bill_number, bill_number_prefix_recognized, anti_tribal_is_yea,
anti_tribal_category, anti_tribal_direction_method, direction_circularity_flag,
classification_source, classification_kappa, build_date`).

- 282 House, 141 Senate. `vote_id` format `H118-0123` / `S118-0045`.
- The union of all five upstream classification files, deduplicated on
  (chamber, congress, rollnumber). All 423 resolve in `HSall_rollcalls.csv`; none were dropped.
- 398 of 423 carry a `bill_id`. The 25 without one are roll calls where Voteview records no
  bill number.
- Roll calls per Congress range from 1 (119th, partial) to 39 (104th).

### `member_positions.csv` — 136,119 member-vote rows
`vote_id, bill_id, bioguide_id, icpsr, party, party_code, state_abbrev, district, position,
cosponsor_flag` + `position_simple, chamber, congress, rollnumber, cast_code, bioname, build_date`

- 423 votes × 2,583 unique members. `bioguide_id` present on 100.0% of rows.
- `position` preserves Voteview's exact semantics: Yea 82,199 · Nay 45,272 · Not Voting 8,312 ·
  Announced Yea 150 · Paired Yea 61 · Paired Nay 59 · Announced Nay 35 · Present 31.
  `position_simple` folds paired/announced into Yea/Nay for anyone who wants the coarse version.
- Party: D 72,331 · R 63,553 · I 235.
- `cosponsor_flag`: 1 on 7,385 rows, 0 on 106,904, blank on 21,830 — see section 5.
- `member_positions` sums exactly to `bill_votes`: the count of `position == "Yea"` per `vote_id`
  equals `bill_votes.yea` on all 423 votes (verified, 0 mismatches).

---

## 3. How `republican_yea_share` was computed

It is computed from member-level cast codes, not from any published summary:

1. Stream `HSall_votes.csv` (26.26M rows), keep the rows whose (congress, chamber, rollnumber)
   is one of the 423 tribal roll calls → 136,471 member-vote rows. Cached at
   `data/raw/external/votingpatterns/_hsall_votes_tribal_subset.csv`.
2. Drop `cast_code == 0` (not a member of that chamber at the time).
3. **Drop presidential position rows.** Voteview records the President's announced position in
   the votes file under the voting chamber's label; it is not a member vote and is excluded from
   official tallies. 352 such rows dropped. They are identified by the exact President ICPSR set
   taken from `HSall_members.csv` where `chamber == "President"` — *not* by an `icpsr >= 99000`
   rule, which would wrongly delete Strom Thurmond (99369), Nathan Deal (99342), Michael Forbes
   (99542) and Virgil Goode (99767), all real members with high ICPSR numbers.
4. Join `HSall_members.csv` on (congress, chamber, icpsr) for `party_code`, `state_abbrev`,
   `district_code`, `bioguide_id`. Party groups: 100 = D, 200 = R, anything else = I.
5. `R_yea` = count of Republicans with `cast_code == 1`; `R_nay` = count with `cast_code == 6`.
   Cast codes 2–5 (paired and announced positions) are **excluded** from the party breakdown and
   from `yea`/`nay`, because they are not votes cast and are not in the official tally. They are
   carried separately as `yea_paired_announced` / `nay_paired_announced` (305 rows in total
   across the whole dataset, 0.22%).
6. `republican_yea_share = R_yea / (R_yea + R_nay)`, missing when no Republican voted either way.
   Populated on all 423 roll calls. `n_republican_voting` gives the denominator on every row.
   `democrat_yea_share` is computed the same way for the baseline comparison.

Mean `republican_yea_share` = 0.604 (House 0.583, Senate 0.645); mean `democrat_yea_share` =
0.680 (House 0.702, Senate 0.635).

**`republican_yea_share` is the literal yea share, not a direction-adjusted pro-tribal share.**
A separate column `republican_pro_tribal_share` flips it where `pro_tribal_is_yea == 0`. It is
populated on the 240 roll calls that have a coded direction and missing on the other 183 —
do not silently treat missing direction as "yea is pro-tribal."

### Verification against Voteview's own published counts
`voteview_yea_count` / `voteview_nay_count` are carried alongside the recount, with a
`tally_matches_voteview` flag. **415 of 423 match exactly.** All 8 mismatches are 103rd Congress
House votes and all are explained: in the 103rd Congress the five territorial Delegates (DC, PR,
GU, VI, AS) could vote in the Committee of the Whole. They appear in `HSall_votes.csv` and are
therefore in our recount and in `member_positions.csv`, but are outside Voteview's published
`nay_count`. Verified on `H103-0228`: Norton (DC), de Lugo (VI), Faleomavaega (AS), Underwood
(GU) voting Nay, Romero-Barceló (PR) not voting — exactly the +4 gap. Nothing was adjusted; both
numbers are published and the flag lets a user pick.

---

## 4. Intercoder provenance (`classification_source`)

Every row of `native_bills.csv` and `bill_votes.csv` carries `classification_source` and, where
one is documented, `classification_kappa`. Controlled vocabulary:

| Value | Meaning | κ | Votes | Bills |
|---|---|---|---|---|
| `two_coder_adjudicated` | Two independent coders + adjudication | **0.952** | 212 | 110 |
| `two_coder_adjudicated_inherited_from_rollcall` | Bill direction inherited from that set | 0.952 | — | 53 |
| `two_coder_zero_overlap_adjudicated` | Anti-tribal set; coders searched disjoint spaces | −1.000 (not meaningful) | 64 | 51 |
| `single_coded_8strategy_expansion` | Anti-tribal expansion, one pass | — | 6 | 4 |
| `single_coded_keyword_rule` | Senate keyword rule, one pass | — | 141 | 63 |
| `congress_gov_policy_area_native_americans` | CRS-assigned policy area (external authority) | — | — | 2,019 |
| `single_coded_keyword_rule_on_title` | Title keyword rule, one pass | — | — | 737 |

**The κ = 0.952 documented in the source.** From
`data/raw/external/votingpatterns/intercoder_report.txt` (dated 2026-03-23): two independent
coders classified pro-tribal vote direction on 246 House tribal roll calls; raw agreement
243/246 = 98.8%; **Cohen's κ = 0.952**; 3 disagreements adjudicated (higher-confidence coder
wins, ties default to yea = pro-tribal). Base rates: Coder A 85.0% yea, Coder B 85.4% yea. Final:
211 yea-is-pro-tribal, 35 nay-is-pro-tribal. The upstream report states plainly that these are
AI-generated codings and that a human federal-Indian-law expert should validate a subset before
publication. **That caveat travels with this dataset.**

The second κ is **−1.000** and is *not* a reliability failure —
`intercoder_report_anti_tribal.txt` records that the two anti-tribal coders searched disjoint
spaces (Coder A substantive amendments, Coder B procedural motions to recommit), so overlap was
zero by construction and κ is undefined in substance. 18 flagged, 9 included after adjudication
on substantive criteria. Labeled `two_coder_zero_overlap_adjudicated` rather than reported as
agreement.

### Circularity flag — read before using anti-tribal direction
`anti_tribal_is_yea` on the 21 expansion votes was assigned upstream from the **observed partisan
voting pattern** (Republican yea rate minus Democratic yea rate > 0.15 ⇒ yea is the anti-tribal
side), per `41_expand_anti_tribal.py`. That is circular with respect to any party-margin outcome
— including `republican_yea_share`, which is the point of this dataset. Those rows carry
`direction_circularity_flag = 1` and the direction is deliberately **not** folded into
`republican_pro_tribal_share`. Do not use partisan-derived direction as a covariate in a
partisan-outcome regression.

---

## 5. Cosponsors

The upstream Congress.gov pull stored only a cosponsor **count**, not the roster, so
`cosponsor_flag` could not be filled from the copied files alone. This was the one gap filled
with a live API call (`code/14_pull_cosponsors.py`, key read from `votingpatterns/.env`, never
printed or written anywhere).

Cosponsor rosters were requested for the 275 roll-call-carrying bills whose type the API serves.
Result — 5,318 cosponsor records across 275 bills:

| Fetch status | Bills | Meaning |
|---|---|---|
| `ok` | 162 | roster returned |
| `zero_cosponsors_reported` | 71 | API answered; the bill genuinely has no cosponsors |
| `no_api_record` | 41 | pre-103rd Congress; Congress.gov has no cosponsor record |
| `http_520` | 1 | upstream error; not retried into success |

Per-bill status is in `data/clean/_cosponsor_fetch_log.csv`; the roster is in
`data/clean/_cosponsors.csv`.

In `member_positions.csv`: `cosponsor_flag` = 1 on 7,385 rows, 0 on 106,904, **blank on 21,830**.
Blank is not zero. A row is 0 only where the API actually answered for that bill (status `ok` or
`zero_cosponsors_reported`, 233 bills); rows on the 42 bills the API could not serve, and all
rows on roll calls with no bill number, stay blank.

One timing limitation, not corrected: `cosponsor_flag` reflects cosponsorship at the time of the
API pull, and members may add cosponsorship after a vote. The sponsorship dates are preserved in
`_cosponsors.csv` if a date-aware version is ever needed.

---

## 6. REQUIRED CAVEATS

**1. Most bills never get a roll call. The vote tables cover the votable subset only.**
283 of 3,037 bills in `native_bills.csv` — **9.3%** — carry even one tribal roll call. The other
90.7% died in committee, passed by voice vote or unanimous consent, or moved by suspension
without a recorded vote. `native_bills.csv` covers the bill universe; `bill_votes.csv` and
`member_positions.csv` cover only the fraction that reached a recorded vote, and that fraction is
selected — contested and high-salience measures are over-represented in it by construction.
Never present roll-call analysis as the full legislative record of Indian Country, and never
compute a "share of Native bills passed" from the vote tables.

**2. Riders and provisions inside omnibus vehicles are a known undercount.**
Indian-affairs law is routinely enacted as a title or a rider inside Interior appropriations,
continuing resolutions, NDAAs and omnibus packages. Those provisions do not carry their own bill
number, do not appear as a Native bill, and their roll call is a vote on the whole vehicle, not
on the tribal provision. This dataset counts them only where the roll-call text itself names the
tribal provision. The direction of the bias is one-way: **the true count of enacted Native
legislative provisions is higher than 229, and the true count of member positions taken on
tribal policy is higher than what `member_positions.csv` records.** The upstream anti-tribal
adjudication makes the same judgment explicitly, excluding nine Interior-appropriations and
omnibus recommit motions on the ground that tribal intent could not be isolated from general
spending priorities (`intercoder_report_anti_tribal.txt`, section 4).

**3. "Native bill" is a ruled category, not a keyword hit.** 2,019 of the 3,037 bills enter on
Congress.gov's CRS-assigned policy area "Native Americans"; 737 enter on a single-pass title
keyword rule; the rest enter through roll-call classification. `classification_source` says which
on every row. Edge cases — general bills with tribal titles, appropriations riders — are exactly
where the keyword rule is weakest.

**4. Cosponsorship is cheap talk relative to votes.** Keep `cosponsor_flag` and `position` as
separate signals; do not build a combined support index from them.

**5. Position scorecards inherit the counter-lobby sensitivity posture.** Member-level Native-vote
scorecards derived from `member_positions.csv` are politically potent. Public record,
evidence-cited, framed as position tracking, never as endorsement.

**6. Coverage boundaries.** Roll calls: Congresses 93–119 (1973 onward, the post-self-determination
era) — the upstream classifier deliberately starts at the 93rd, so earlier Indian-affairs roll
calls (termination era, ICRA) are out of scope. Bill metadata: 103rd–119th only; the 93rd–102nd
appear in `native_bills.csv` only when they drew a roll call, and 136 of those have no title,
sponsor, or introduced date because the upstream Congress.gov pull did not reach back that far.
The upstream classification is also restricted to the lower 48 in places (`41_expand_anti_tribal.py`
excludes Alaska Native, ANCSA, Native Hawaiian and territorial matters), so ANC and NHO
legislation is under-covered relative to lower-48 tribal legislation.

**7. Eight roll-call bill numbers did not parse to a Congress.gov bill type** (`hre`, `hjr`,
`treatydoc`, `treatydocno` prefixes in Voteview). They are kept verbatim with
`bill_number_prefix_recognized = 0` rather than guessed into `hres`/`hjres`. Origin chamber for
these is inferred structurally only (h- prefix = House; treaty documents are Senate-only under
Art. II §2).

**8. 53 of the 423 roll calls are votes on a resolution vehicle, not on a tribal measure.**
`vehicle_type` classifies every vote structurally from its bill type: bill 337 ·
resolution_vehicle 53 · no_bill_number 25 · treaty_document 5 · unresolved_bill_type 3. The 53
resolution-vehicle votes are largely H.Res. rules "providing for consideration of" a bill, and
the 64 `procedural_opposition` votes are dominated by motions to recommit (31) and ordering the
previous question (16). Both classes are near-perfectly party-line **by institutional design**,
independent of anything tribal — several of them are rules for bills that are not Native
legislation at all (e.g. `H111-0218`/`H111-0219` on the rule for H.R. 1913, `H116-0204` on the
rule for H.R. 5), which entered the net on tribal keyword text inside the rule. They are flagged
rather than deleted, because deletion is a research judgment. **Any Republican-margin analysis
should restrict to `vehicle_type == "bill"` and `vote_type == "pro_tribal"` for the primary
specification** and use the rest as a robustness set. The upstream member scorecards
(`member_tribal_scores_v2.csv`) were built from the 212 pro-tribal votes only, for this reason.

**9. Voteview does not supply a question or result string for every roll call.** `question` and
`result` are populated on 305 of 423; `question_source` and `result_source` say which rows those
are. Nothing was invented to fill the gap. `vote_description` (populated on 418 of 423) coalesces
Voteview's `vote_desc` and `dtl_desc`, and `majority_side` is offered as a purely arithmetic
descriptor — it is **not** the official result, since suspension and cloture votes carry
supermajority thresholds.

---

## 7. What is not done

- **Spine linking.** `affected_entities` is blank by design; the tribe/entity join is a separate
  step. `bill_scope_basis` already records which spine name triggered a tribe-specific ruling,
  so that step has a seeded starting point.
- **Senate direction coding.** 113 of 141 Senate roll calls need direction. This is the single
  highest-value remaining task for the Republican-margin design, since it would raise
  direction-coded coverage from 240/423 to 353/423.
- **Human expert validation** of the AI-generated direction codings, per the upstream report's
  own recommendation.
- **The money join.** `bill_lobbying.csv` waits on dataset 4's bill-number parse of LDA
  specific-lobbying-issues text. `bill_id` here is in the format that join will target.
- **Current-Congress refresh.** The 119th Congress is partial (154 bills, 1 roll call) and needs
  the standing-cadence re-pull.
