# Dataset 10 — Native Bills & Congressional Votes

*Maintenance doc. Generated 2026-08-28. Tier: **Cedar Press ($500) - Congressional Votes and Proposed Legislation***

## What this is

Bills affecting Native entities, their roll calls, member positions and cosponsors — AND, since 2026-08-06, what happened to the bills that never reached a floor at all. The outcomes leg of the influence chain.

## Files

| File | Rows | Size |
|---|---:|---:|
| `data/clean/native_bills.csv` | 3,069 | 1 MB |
| `data/clean/bill_votes.csv` | 423 | 335 KB |
| `data/clean/member_positions.csv` | 136,119 | 14 MB |
| `data/clean/native_bill_outcomes.csv` | 3,069 | 2 MB |
| `data/clean/native_bills_entity_bridge.csv` | 676 | 196 KB |
| `data/clean/bill_votes_entity_bridge.csv` | 75 | 17 KB |
| `data/clean/native_bills_entity_class.csv` | 2,694 | 1 MB |
| `data/clean/native_bills_subject_sweep.csv` | 2,414 | 1 MB |
| `data/clean/bill_votes_official_verification.csv` | 305 | 108 KB |

## Refresh

**Cadence:** Per Congress, or after a votingpatterns refresh. Re-run `73 --actions --outcomes` after any Congress closes; action histories are the only part that goes stale.

**Build:** `code/14_build_bills_votes.py, then code/73_bills_votes_completion.py (--rollcalls --sweep --titles --actions --outcomes --bridge --classes)`

Run `py -3 code/00_run_all.py --list` to see pipeline stages.

## NEVER do these

- **Never present roll-call analysis as the full legislative record.** Only 283 of 3,069 bills (9.2%) ever get a roll call. 2,189 (71.3%) die without a floor vote of any kind — that is what `native_bill_outcomes.csv` is for, and it is the more common political fact by a factor of eight.
- **Never read a blank `question` or `result` before 1990 as a scraping gap.** It is a source boundary. clerk.house.gov/evs begins with calendar year 1990 (1989 → HTTP 404) and senate.gov LIS with the 101st Congress (100th → redirect to roll-call-vote-not-available.htm). The 118 blanks were EXACTLY the 69 House roll calls before 1990 plus the 49 Senate roll calls before the 101st — zero blanks inside the coverage window. Voteview inherits the same boundary. Questions are now filled from the ICPSR description Voteview ships as `dtl_desc`; read `question_source` before treating a question as official.
- **Never derive a pre-1990 `result` from yea > nay.** Most of those roll calls are motions to suspend the rules, which need two thirds. The 46 recovered results were matched on a Congress.gov action naming THAT roll call's own tally; date-matching alone was tried, produced 'Passed' on amendment votes and motions to table, and was withdrawn.
- **Never use `voteview_yea_count` / `voteview_nay_count`.** Use `yea` / `nay`. The Clerk's own record settled the 8 disputed 103rd-Congress roll calls in favour of the member-level recount, on all 8.
- Never treat `disposition = no-action-record` as a death. It says we have no record of what happened, not that nothing happened. Same for the committee dispositions: `disposition_basis` states in words when a disposition was inferred from the ABSENCE of a later action.
- **Never force a `tribe_id` from `native_bills_entity_class.csv`.** That file records the CLASS a bill reaches (every ANCSA village corporation, every NHO) precisely because the bill names no entity. Turning a class into a member is the false attribution the bridge exists to prevent.
- Never use the 21 votes flagged direction_circularity_flag in a Republican-margin analysis. Their direction was assigned FROM the observed partisan split, which is circular.
- Never include Voteview's presidential position rows in tallies. Drop by the explicit President ICPSR set — an icpsr>=99000 rule wrongly deletes Thurmond (99369), Deal, Forbes and Goode.

## Known issues and caveats

- **Every roll call now carries a question: 423/423.** `result` is on 351/423; the 72 blanks are pre-electronic votes where no Congress.gov action names the tally, and they are blank on purpose.
- **303 of 305 counts verified against the chamber's own XML.** Two disagree and both are real: `H101-0788` (Aroostook Band of Micmacs Settlement Act) is 248-172 at the Clerk and 247-172 here — Voteview's member file carries 432 of the 433 members the Clerk records; `S109-0538` is 46-53 at the Senate and 45-54 here — **Sen. Wyden (D-OR) is Yea in the Senate's record and Nay in Voteview.** Our counts were not overwritten; see `counts_agree_with_official` and `review/bill_votes_count_disagreements_2026-08-06.csv`.
- **The old '8 mismatches' caveat is resolved.** All 8 were 103rd-Congress House votes where Delegates could vote in the Committee of the Whole, and the Clerk record agrees with the Cedar recount to the vote on every one. Voteview's published totals are the ones that under-count.
- The 'Senate gap' does NOT exist — 141 Senate roll calls, Congresses 93–118. What IS thin is direction coding: only 28 of 141 have pro_tribal_is_yea.
- 53 votes sit on H.Res. rule vehicles, some for non-Native bills that entered on keyword text inside the rule. Restrict primary specs to vehicle_type=='bill'.
- κ = 0.952 on the House pro-tribal set (two coders, 246 roll calls). The anti-tribal κ of −1.000 reflects disjoint search spaces, not disagreement.
- **Dispositions run off the FULL action history (31,936 actions, 3,061 of 3,069 bills), not `latest_action`.** latest_action cannot tell 'reported out and never called up' from 'referred and never heard of again' — both end at a committee-shaped string. Distribution: referred-and-died 1,558; passed-one-chamber 421; enacted 283; placed-on-calendar-never-voted 282; committee-acted-never-reported 273; pending-in-committee 125; reported-from-committee-never-voted 76; superseded 15; floor-vote-failed 11; floor-vote-held-outcome-unresolved 9; vetoed 8; no-action-record 8.
- Tribe-specific bills are enacted at 13.4% (65/484) against 7.0% (170/2,417) for general Native legislation. Descriptive, not causal — narrow bills are easier to pass.
- **The ANCSA / Native Hawaiian / NAHASDA families were NOT badly under-covered.** The sweep of all 183,233 bills in `all_bill_intros.csv` found 87 ANCSA titles (73 already held), 90 Native Hawaiian (82 held), and 29/29 NAHASDA, 7/7 intertribal, 11/11 Alaska Native already held. All 2,071 bills carrying CRS policy area `Native Americans` were already in. 32 title matches were genuinely new and carry `classification_source = subject_family_phrase_sweep:<family>`.
- **Sweep corpus limits.** `all_bill_intros.csv` holds only hr/s/hjres/sjres — no simple or concurrent resolutions — and starts at the 103rd Congress. ANCSA or Hawaii measures in Congresses 93–102, or introduced as hres/sres, are outside its reach. That is a known recall gap, not an absence.
- Named-entity reach: 676 bill-entity links over 154 entities, of which 68 links over 28 entities are NOT federally recognised tribes — 17 ANCSA village corporations, 4 regional (Aleut, Chugach), 16 Alaska Native village governments, 11 state-recognised tribes, 9 intertribal (incl. Alaska Native Tribal Health Consortium), 11 tribal-enterprise/CNSF. 8 bills still have no title (treatydoc/treatydocno/hre/hjr — types the Congress.gov API does not serve) and so can never be entity-keyed.
- The class layer reaches 2,456 bills: 2,306 links to the federally-recognised tribe class, 122 Native Hawaiian Organization, 120 ANCSA village corporation, 88 ANCSA regional, 47 Alaska Native village government, 11 intertribal. Caveat on the last: 'tribal organization' in ISDEAA usage can mean a single tribe's organisation as well as a consortium, so those 11 are a loose class.

---

**House rules that apply to every dataset:**

- Never falsely attribute. Missing coverage is expandable; a wrong attribution is not.
- Only tier A publishes. Elijah's rulings are the only promotion path.
- Flag, never delete. Retain and mark rather than drop.
- Cedar Press is self-contained — stage inputs into `data/raw/external/` and build from local copies.
- Temporal floor is 2000; pre-2000 rows carry `pre_2000_flag = 1`.

See `STATE_OF_BUILD.md`, `docs/CROSS_DATASET_LEARNING.md`, and `docs/COVERAGE_EXPANSION_OPTIONS.md`.

## Reference

- **Codebook** — `docs/codebooks/` defines every variable, its type and units. Regenerate with `py -3 code/41_build_codebooks.py`; it is measured from the data, so it cannot drift from the files.
- **Oddities** — `docs/DATA_ODDITIES.md` states what a zero, a negative and a blank MEAN in each dataset. They are not rare: 9.7% of contract rows are negative (deobligations, which belong in the total) and 9.9% are zero (actions that moved no money). Zero is an assertion; blank is a silence; neither is an error. Never filter an oddity out silently - flag it, count it, explain it.
- **Refresh cadence** — `docs/REFRESH_CADENCE.md` gives the pull schedule for every dataset, the incremental change key for each source, and the re-run chain that must follow ANY refresh. Refresh on the SOURCE's clock, not ours: pulling a quarterly source weekly earns rate limits, and every unnecessary rebuild is a chance to lose a hand correction (`code/31` once silently reset a dataset from 93 keyed to 0).
- **Coverage** — `docs/COVERAGE_AUDIT.md` reports the observed year range and any gaps against the 2000-2026 target. Regenerate with `py -3 code/35_coverage_audit.py`.

A codebook says WHAT each variable is. It deliberately does not say how a value was derived - the linkage method is the product, so columns whose values would disclose it are marked internal and withheld from published extracts.