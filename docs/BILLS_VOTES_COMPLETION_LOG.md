# Dataset 10 — completion pass, 2026-08-06

*Build script: `code/73_bills_votes_completion.py` (stages `--rollcalls --sweep
--titles --actions --outcomes --bridge --classes`). Prior build:
`code/14_build_bills_votes.py`, logged in `BILLS_VOTES_BUILD_LOG_2026-08-05.md`.*

Three things were asked for: fill the missing vote questions, make bills that
never reached a floor visible, and extend the entity reach beyond federally
recognised tribes. All three are done. The first one could not be done the way
it was specified, and why is the most useful thing in this log.

---

## 1. The 118 missing questions are a source boundary, not a scraping gap

`bill_votes.csv` carried `question` and `result` on 305 of 423 roll calls.

The instruction was to fill the other 118 from `clerk.house.gov/evs/` and
`senate.gov/legislative/LIS/roll_call_votes/`. **Neither source covers any of
them.** Probed 2026-08-06:

| Probe | Result |
|---|---|
| `clerk.house.gov/evs/1990/roll001.xml` | HTTP 200 |
| `clerk.house.gov/evs/1989/roll001.xml` | **HTTP 404** |
| `senate.gov/.../vote1011/vote_101_1_00001.xml` | HTTP 200 |
| `senate.gov/.../vote1002/vote_100_2_00001.xml` | **301 → `roll-call-vote-not-available.htm`** |

The House electronic voting system record begins with calendar year 1990. The
Senate LIS roll-call XML begins with the 101st Congress. Against those
boundaries the dataset splits exactly:

```
House roll calls dated before 1990          69
Senate roll calls before the 101st Congress 49
                                     total 118   <- exactly the 118 blanks
missing but INSIDE the coverage window        0
```

Zero. The blank set is not a random 28% of the file and not a failure of the
earlier build — it is the pre-electronic era, drawn with a hard edge. Voteview's
`vote_question` is blank on the same rows for the same reason: Voteview ingests
the Clerk and LIS feeds, so it inherits their start dates (`vote_question`
non-null on 6.4% of Congresses 93–101, 100% of 102+).

### What was done instead

**Questions — filled, from the ICPSR roll-call description.** Voteview ships
`dtl_desc` on **100%** of Congresses 93–101; it is the description ICPSR coded
from the Congressional Record, and for this era it *is* the question as the
chamber put it:

> `TO SUSPEND THE RULES AND PASS H. J. RES. 123, A BILL TO AMEND SECTION 123 OF THE FEDERAL-AID HIGHWAY ACT OF 1970`

The leading clause is taken **verbatim** — a substring of a sourced field, not a
paraphrase — and `question_source` records exactly that. A descriptive
`question_family` (On Passage, On the Motion to Table, On Ordering the Previous
Question …) sits beside the quoted text and never replaces it.

**Results — not invented, and the first attempt was wrong.** `yea > nay` does not
imply passage: the most common question in this set is a motion to suspend the
rules, which needs two thirds. So results were recovered from Congress.gov
actions instead.

The first version keyed on **same bill, same date**. That is wrong, and it was
caught only by reading the filled rows. Congresses routinely take several roll
calls on one bill in one day — three separate amendment votes on H.R. 1426 on
1986-09-18 — and the action Congress.gov records for that date describes the
*passage* vote. The date key therefore stamped `Passed` onto amendment votes,
motions to table and votes on the rule. **All 66 date-keyed fills were withdrawn.**

The rule is now identity, not adjacency: the action must contain a tally
**equal to this roll call's own yea-nay**. `roll call #253 (290-38)` against a
290-38 recount is that vote and can be nothing else. **46 results recovered**;
the remaining 72 stay blank, because a blank is a true statement about the
evidence and `Passed` on the wrong motion is not.

`result` now stands at **351/423**.

### The verification found two real disagreements

All 305 roll calls inside the coverage window were fetched from the chamber's
own XML (305/305 `ok`) and our member-level recount compared against it.
**303 of 305 agree exactly.** Our counts were not overwritten; the official
values sit alongside in `official_yea` / `official_nay` /
`counts_agree_with_official`, and the two disagreements are in
`review/bill_votes_count_disagreements_2026-08-06.csv`.

| Vote | Bill | Official | Cedar (and Voteview) | What it is |
|---|---|---|---|---|
| `H101-0788` 1990-10-10 | S. 1413, Aroostook Band of Micmacs Settlement Act | **248**–172 | 247–172 | The Clerk records 433 members; Voteview's member-level file carries 432. One Yea is missing from Voteview, so the recount and Voteview's own published total agree with each other and both are one short of the Clerk. |
| `S109-0538` 2006-06-15 | S.Amdt. 4234 to S. 2766 | **46**–53 | 45–54 | A single-member coding difference: **Sen. Wyden (D-OR) is `Yea` in the Senate's record and `Nay` in Voteview.** |

### And it overturned a caveat that was in the docs

The previous build flagged 8 roll calls where the member-level recount did not
match Voteview's published `yea_count`/`nay_count`, all 103rd-Congress House
votes, and published both numbers without adjudicating. **The Clerk record
adjudicates them: all 8 agree with the Cedar recount, to the vote.**

```
H103-0228  cedar 210-216  voteview 210-212  CLERK 210-216
H103-0521  cedar 178-238  voteview 178-234  CLERK 178-238
H103-0629  cedar 422-  1  voteview 417-  1  CLERK 422-  1
H103-0639  cedar 203-213  voteview 203-208  CLERK 203-213
H103-0688  cedar 173-245  voteview 173-240  CLERK 173-245
H103-0760  cedar 184-239  voteview 184-235  CLERK 184-239
H103-0889  cedar 188-233  voteview 188-229  CLERK 188-233
H103-0921  cedar 298-121  voteview 298-118  CLERK 298-121
```

The recount is right and Voteview's published totals under-count the territorial
Delegates who could vote in the Committee of the Whole in the 103rd. Use `yea`
and `nay`, not `voteview_yea_count` / `voteview_nay_count`.

---

## 2. Bills that never got a vote

> Elijah: *"we want to keep track of stuff that didnt get a vote which i think
> we should have."*

`native_bill_outcomes.csv` — one row per bill, with the action text and date
that establishes its disposition.

The classification reads the **full** Congress.gov action history, not
`latest_action`. That is the whole reason the file exists: latest_action cannot
distinguish

- *reported out of committee, calendared, and never called up* — a committee
  said yes and the floor said nothing; from
- *referred and never heard of again* — no committee ever said anything,

because both end at a committee-shaped string. They are different political
facts and they are now different values.

**31,936 actions pulled for 3,061 of 3,069 bills** (100% `ok`; the 8 missing are
bill types the API does not serve). Result:

| Disposition | Bills | |
|---|---:|---:|
| `referred-and-died-in-committee` | 1,558 | 50.8% |
| `passed-one-chamber` | 421 | 13.7% |
| `enacted` | 283 | 9.2% |
| `placed-on-calendar-never-voted` | 282 | 9.2% |
| `committee-acted-never-reported` | 273 | 8.9% |
| `pending-in-committee` | 125 | 4.1% |
| `reported-from-committee-never-voted` | 76 | 2.5% |
| `superseded-by-another-measure` | 15 | 0.5% |
| `floor-vote-failed` | 11 | 0.4% |
| `floor-vote-held-outcome-unresolved` | 9 | 0.3% |
| `vetoed` | 8 | 0.3% |
| `no-action-record` | 8 | 0.3% |

**283 of 3,069 bills (9.2%) ever reach a roll call. 2,189 (71.3%) die without a
floor vote of any kind.** The thing the dataset could not previously see is
eight times more common than the thing it could.

Descriptive by-product worth one line: tribe-specific bills are enacted at 13.4%
(65/484) against 7.0% (170/2,417) for general Native legislation. Narrow bills
are easier to pass; this is not a causal claim.

**Where a disposition rests on the absence of an action, `disposition_basis`
says so in those words** ("INFERRED FROM THE ABSENCE of any subsequent passage,
failure or withdrawal action in the full history"). A bill with no obtainable
action record is `no-action-record`, never "died" — that is a statement about
our evidence, not about the bill.

Two guards worth knowing:

- A bill in a Congress still sitting cannot have died, so committee-shaped
  dispositions in Congress 119 become `pending-in-committee`.
- A bill with a recorded roll call did reach a floor, whatever a stale committee
  string says; those are re-labelled and the override is recorded.

Also fixed here: **136 bills carried a roll call but no title**, because they
predate the `all_bill_intros` corpus (which starts at the 103rd Congress). A
bill with no title cannot be entity-keyed at all — the bridge scans titles — so
128 titles were backfilled from the Congress.gov bill endpoint. The remaining 8
are bill types the API does not serve (`treatydoc`, `treatydocno`, `hre`,
`hjr`).

---

## 3. Beyond tribes

> Elijah: *"i think we have this for tribes but can extend to other native
> entities."*

### The subject sweep

`native_bills_subject_sweep.csv` scans all 183,233 bills in `all_bill_intros.csv`
(Congresses 103–119) for six subject families. Honest result: **the families
were far better covered than expected.**

| Family | Found | Already in `native_bills` | New |
|---|---:|---:|---:|
| ANCSA / Alaska Native corporations | 87 | 73 | **14** |
| Native Hawaiian | 90 | 82 | **8** |
| Native American Housing (NAHASDA) | 29 | 29 | 0 |
| Intertribal organisations | 7 | 7 | 0 |
| Alaska Native (non-ANCSA) | 11 | 11 | 0 |
| Native American / American Indian (general) | 2,190 | 2,180 | **10** |

`native_bills.csv`: 3,037 → **3,069**.

All 2,071 bills carrying the CRS policy area `Native Americans` were already in
the dataset — the inherited classification had that layer completely. 32 title
matches were genuinely new (`ANCSA Dividend Exclusion Act`, `ANCSA Thirteenth
Regional Corporation Reincorporation Act`, `Hawaiian Home Lands Recovery Act`,
the Hawaiian Homes Commission Act consent resolutions) and were appended with
`classification_source = subject_family_phrase_sweep:<family>`, so no swept row
can ever be mistaken for one of the two-coder adjudicated rows.

Only **title** matches were added. Subject/policy-area matches stay in the sweep
file as a recall tier.

**Two coverage limits of the sweep corpus, stated rather than papered over.**
`all_bill_intros.csv` holds only `hr`, `s`, `hjres`, `sjres` — no simple or
concurrent resolutions — and starts at the 103rd Congress. Anything ANCSA- or
Hawaii-related in Congresses 93–102, or introduced as an `hres`/`sres`, is
outside the sweep's reach and is a known recall gap, not an absence.

### Named entities: the bridge, not a tribe_id

`native_bills_entity_bridge.csv` is still the only place a bill is linked to a
named entity, because **a bill affects many entities** and forcing one
`tribe_id` onto it would be a false attribution dressed as completeness. The
scanner from `70_key_unjoined_datasets.py` is imported whole — its designator
requirement, its compound-name demotion, its NAME_TRAPS refusal. `resolve_entity`
from `33_apply_party_rulings.py` is the only resolver (standing rule 8).

**Reach: 640 → 676 bill-entity links over 154 entities.** 68 links over **28
entities that are NOT federally recognised tribes**:

| | Links | Examples |
|---|---:|---|
| ANCSA village corporations | 17 | Cape Fox, Kake Tribal, Elim Native, Huna Totem, Olgoonik, Knikatnu, Seldovia |
| ANCSA regional corporations | 4 | The Aleut Corporation, Chugach Alaska |
| Alaska Native village governments | 16 | Kaktovik, Wainwright, Saxman, Tanana, King Salmon |
| State-recognised tribes | 11 | Haliwa-Saponi, Nottoway (VA), Patawomeck, Cheroenhaka, Edisto Natchez-Kusso, Wassamasaw |
| Intertribal organisations | 9 | Alaska Native Tribal Health Consortium |
| Tribal enterprises / consolidated | 11 | Viejas, White Earth, Leech Lake |

The vote bridge, which inherits through `bill_id`, went 26 → **75**.

Eight bills still have no title — `treatydoc`, `treatydocno`, `hre`, `hjr`, bill
types the Congress.gov API does not serve — and so can never be entity-keyed.

### The class layer — new, and the part that actually reaches non-tribes

Most non-tribe Native legislation names a **statute and a class**, never an
entity. A NAHASDA reauthorisation concerns every ANCSA village corporation and
no particular one. `native_bills_entity_class.csv` records that as what it is:

- `entity_class` + `entity_id_prefix` (`ANVC-`, `ANRC-`, `NHO-`, `ITO-`,
  `AKNF-`, `TRBF-`) joinable to the spine by prefix,
- `n_spine_entities_in_class` — the size of the class the bill reaches,
- and **no `tribe_id` at all**, in its own file so it can never be read as a
  named-entity link.

2,694 bill-class links over 2,456 bills: 2,306 to the federally recognised tribe
class, **122 Native Hawaiian Organization, 120 ANCSA village corporation, 88
ANCSA regional corporation, 47 Alaska Native village government, 11 intertribal**.

One caveat on the last: `tribal organization` in ISDEAA usage can mean a single
tribe's own organisation as well as a consortium, so those 11 are a loose class.

---

## Two failures in the regression check that are NOT from this work

`code/62_no_regression_check.py` passed before this pass and reports two
failures after it. Both are attributable to other agents running concurrently on
2026-08-06, and both are recorded here rather than "fixed" by an agent that does
not own them.

1. **`tier_A FELL 2,149 → 2,148`.** `cedar_identifier_ledger_final.csv` was
   rewritten at 17:27:22 by another agent's build.
   `73_bills_votes_completion.py` contains no reference to the ledger and writes
   only bill and vote files.
2. **`codebook_undocumented_public = 4`.** Regenerating `41_build_codebooks.py`
   (standing rule 10) surfaced four published columns with no description:
   `entity_website` on the spine, and `institution_primary`,
   `institution_names_all`, `spans_found` on the NAGPRA dataset. Those columns
   were added minutes earlier by `75_add_bie_schools_and_uios.py` and
   `77_build_nagpra_dataset.py`, **both of which were still running**. They
   belong to those builds; writing descriptions for them from the outside would
   be guessing at another dataset's semantics, and editing
   `41_build_codebooks.py` while another process holds it invites a clobber.
   The count was sitting at zero only because the generator had not been re-run
   — which is the exact failure mode the file's own header warns about.

Everything in the check that this pass touches moved the right way:
`bridge_native_bills_entity_bridge` 640 → 676,
`bridge_bill_votes_entity_bridge` 26 → 75, `codebook_variables` 641 → 765.

---

## Files

| File | What it is |
|---|---|
| `data/clean/bill_votes.csv` | now carries `question` on 423/423, plus `official_*` verification columns |
| `data/clean/bill_votes_official_verification.csv` | the raw official-record pull, one row per roll call, with source URL |
| `review/bill_votes_count_disagreements_2026-08-06.csv` | the 2 disagreements against the chamber's own record |
| `data/clean/native_bill_outcomes.csv` | **one row per bill, with its final disposition** |
| `data/clean/_bill_actions.csv` | every Congress.gov action, the evidence behind the dispositions |
| `data/clean/_bill_actions_fetch_log.csv` | per-bill fetch status — an empty history is distinguishable from a failed fetch |
| `data/clean/native_bills_subject_sweep.csv` | the ANCSA / Native Hawaiian / intertribal sweep, with the matched phrase |
| `data/clean/native_bills_entity_class.csv` | bill → class of Native entity, where no entity is named |
| `data/clean/_bill_metadata_backfill.csv` | the 128 backfilled titles |

## Hosts and discipline

`clerk.house.gov`, `www.senate.gov`, `api.congress.gov`. **`api.usaspending.gov`
was not touched** — it was held by a subaward puller throughout.
`logs/_HOSTLOCK_<host>.json` claimed per host before any loop, released after;
`Win32_Process.CommandLine` used to check for existing pollers, because Git
Bash `ps` cannot see command lines on Windows. Every stage writes incrementally
and resumes from its own fetch log.
