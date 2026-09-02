# Ruling application log

*Written 2026-08-26. Producer scripts: `code/173_consolidate_rulings_ledger.py`
(sweep + reconcile) and `code/174_apply_rulings_to_source_tables.py` (apply).*

---

## THE STANDING RULE

**A ruling that is not applied back to its source table is not a ruling, it is
a note.**

A verdict recorded in `review/` and nowhere else has no effect on any number
this project publishes, no effect on any queue this project builds, and no
effect on the next agent's view of the world. It costs a human's attention to
produce and buys nothing. The only place a ruling exists is in the table it
changes.

Corollary, and the reason this file is separate from the build logs: **the
question "has this been ruled?" and the question "has that ruling been
applied?" are different questions, and until today only the first one was ever
asked.** `code/160_ship_gap_report.py`'s `review_backlog()` counts rows with a
*blank* ruling column — work awaiting a human. It cannot see a row that has
been ruled and ignored, because that row looks finished from every angle except
the one nobody was looking from.

---

## THE DEFECT

**492 clusters / $17.5B** — the figure recorded in `docs/WORK_QUEUE.md` on
2026-08-26, which is what sent this session looking.

Measured 2026-08-26 and recorded in `docs/WORK_QUEUE.md`: **492 entity clusters
carrying $17.5B in obligations already had a ruling recorded somewhere in
`review/` or `data/clean/`, and the ruling was never written back to the source
table.** `prime_contracts.attributed_flag` stayed `0`, so they re-surfaced in a
fresh reconciliation queue as though nobody had ever looked at them. The owner
spotted it himself — he recognised entries he had already adjudicated.

Confirmed cases, all now carrying a status in `prime_contracts.csv`:

| subject | ruled | ruled in | status now |
|---|---|---|---|
| `Asrc Constructors, Inc.` | Arctic Slope Regional Corporation | 3 files | `RULED_ATTRIBUTED`, tier **A**, `ANRC-ARCSLO-00` |
| `All Points Logistics Incorporated` | NOT_NATIVE | 2 files | `RULED_NOT_NATIVE` |
| `Cherokee Information Services` | BLOCKED: individually_native_owned | 2 files | `RULED_NOT_NATIVE` |
| `Kuk Brs Alaska Venture` | HOLD — joint venture, owning share not established | 2 files | `RULED_HOLD` |
| `Nakupuna Solutions, Llc` | `NHO-NAKUPUNA-00` | 2 files | `RULED_TIER_C_NOT_ATTRIBUTED` |
| `Copper River Information Technology` | Native Village of Eyak / NATIVE | 3 files | ruled, carried to the consolidated ledger |

Why it recurred rather than happening once: **every ruling pass in this project
wrote its verdicts to a NEW file in `review/` and left the application step to
whoever came next.** Twelve `rulings_inbox_*` files, eleven `agent_rulings_*`
files, `auto_applied_2026-08-07.csv`, `cross_dataset_ruling_map.csv` and
`MASTER_QUEUE_2026-08-07.csv` all exist because a pass finished collecting and
never finished applying. `09_import_rulings.py` was the applier and became
unsafe to run on 2026-08-08 (it rebuilds from a stale upstream and cost 1,327
ledger rows), which removed the only route from `review/` back to the tables
and left no replacement.

---

## WHAT WAS DONE

### 1. Sweep — `code/173_consolidate_rulings_ledger.py`

Every `.csv` under `review/` and `data/clean/` was read for a ruling column
(`YOUR_RULING`, `ruling`, `decision`, `entity_class`, `proposed_class`,
`entity_category`, `verdict`, `AUDIT_VERDICT`, `resolution`, `existing_ruling`,
`proposed_ruling`, `your_decision`).

| | count |
|---|---:|
| files carrying a ruling column | **157** |
| …verdict-bearing | 128 |
| …proposal-only (never applied) | 29 |
| ruling rows swept | 89,996 |
| …verdict rows | 14,874 |
| …proposal rows | 70,454 |
| …machine-filter rows | 4,668 |
| **distinct subjects carrying a verdict** | **5,500** |

Output: `data/clean/cedar_ruling_ledger_consolidated.csv`, **15,587 rows** —
one row per (subject, source ruling), carrying the subject key, the verbatim
ruling, the resolved owner, the inherited tier, the tier's source, the
originating file and the ruling date.

**Three distinctions the sweep makes, each of which would otherwise have
laundered a non-answer into a decision:**

- **A PROPOSAL is not a RULING.** `review/review_queue_2026-08-05.csv` has
  `entity_class` populated on all 4,813 rows and `YOUR_RULING` blank on all
  4,813. The class column is the *question* — cluster_v3's guess, asked for
  confirmation — not the answer. Treating it as a ruling would have promoted
  algorithmic output to a human decision on 4,813 subjects. 29 files are marked
  proposal-only for reasons stated per file in `PROPOSAL_ONLY`.
- **A MACHINE FILTER is not a VERDICT.** `cross_dataset_ruling_map.csv` records
  both in one column. `BLOCKED: automated_filter:…` is the filter speaking;
  4,668 such rows are recorded and excluded from the verdict count. Counting
  them made every human "reinstate" ruling look like a conflict with itself.
- **A CLASS is not an OWNER.** "Native Hawaiian Organization" is a true
  statement that names no owning entity. It classifies; it can never attribute
  a dollar.

### 2. Reconcile — conflicts apply NEITHER

**116 subjects (1,215 ledger rows) are in genuine conflict and NOTHING was
applied to them.** They are written to
`review/ruling_conflicts_2026-08-26.csv`, each row naming both its own source
and every source for that subject.

| conflict type | subjects |
|---|---:|
| `POSITIVE_VS_NOT_NATIVE` | a positive owner or class against a NOT_NATIVE / BLOCKED |
| `OWNER_VS_DIFFERENT_UNRESOLVED_OWNER` | one owner resolves to the spine, another does not, and they are different names |
| `CLASS_CONTRADICTS_OWNER_SPINE_CLASS` | the ruled class is not the ruled owner's class in the spine |
| `TWO_DIFFERENT_UNRESOLVED_OWNERS` | two owners named, neither in the spine |
| `TWO_DIFFERENT_CLASSES` | two specific classes that disagree |
| | **116 total** |

Two reconciliation rules worth keeping:

- **A class ruling and an entity ruling are COMPATIBLE when the class is the
  entity's own.** `Asrc Constructors` is ruled both *Alaska Native Regional
  Corporation* and *Arctic Slope Regional Corporation*; ASRC's spine class **is**
  Alaska Native Regional Corporation, so they agree and both apply. The check
  fires only when the class and the owner's spine class genuinely differ.
- **A class ruling written as `<CLASS> — <prose reason>` is compared on the head
  only.** "NATIVE ORGANIZATION — statewide tribal health consortium" is the
  class `native organization` plus a note. Comparing the whole string invents a
  class nothing can equal and manufactures a conflict out of a comment.
- **A HOLD alongside a positive owner is NOT a conflict about identity.** The
  HOLD says "do not attribute yet". The conservative reading wins and the
  subject is recorded as `HOLD_OVER_OWNER` — 193 subjects.

### 3. Tier inheritance — five recorded sources, and a refusal

**A tier is INHERITED from the source ruling, never assigned by the applier.**
This project already shipped the opposite bug: an exact EIN hit was treated as
tier A on the strength of the key's exactness and attributed a Wisconsin United
Way to a California tribe. *The exactness of the KEY says nothing about the
correctness of the LINK.*

Every applied tier came from one of five recorded places, and which one is
written onto the row in `tier_source`:

1. a `tier` / `confidence_tier` column on the ruling row itself
2. `review/agent_identifier_rulings_applied.csv` — the project's own record of
   the tier each agent ruling was applied at
3. `cedar_identifier_ledger_final.csv`, where that identifier's
   `attribution_method` is one of the RULED methods
4. **the evidence-leg marker**, using the mapping the project itself applied,
   measured over every ruling that reached the applied file:

   | marker | tier | agreement |
   |---|---|---|
   | `Leg 1 (structural)` + `Leg 2` inline | A | 402 / 402 (100%) |
   | `Leg 1 only` | B | 173 / 173 (100%) |
   | `ONE LEG` prefix | B | 51 / 51 (100%) |
   | `TWO LEG` prefix | A | 17 / 17 (100%) |
   | `ATTRIBUTED` prefix | A | 18 / 18 (100%) |
   | `CONFIRMED` prefix | — | **B 93 / A 45 — NOT determinate, refused** |

5. the 09/124 ruling grammar, **hand inboxes only** — that grammar is this
   project's own published reading of an Elijah hand ruling

**A tier stated only in prose is NOT parsed.** The agent notes are full of
sentences like *"LEDGER STATE: currently tier C (unmatched)"* — which describes
the state being corrected, not the ruling — sitting beside *"CONFIRM + PROMOTE
to tier A"*, which describes the ruling. 42 first-sentence action clauses do
state a tier, and **not one of them overlaps the applied file, so the
extraction cannot be validated against any recorded practice.** Parsing them
would be exactly the inference the governing rule forbids.

**420 subjects were therefore REFUSED for want of a recorded tier** and written
to `review/ruling_tier_unstated_2026-08-26.csv`. They hold **$375,422,869** of
still-unattributed prime obligations. They are mostly NHO and intertribal-
organisation rulings from `agent_rulings_nonak_entities_2026-08-06.csv` whose
application failed at the time with `UNRESOLVED:no_spine_match` — the spine had
no NHO layer then and has 210 NHOs now, so the rulings are newly applicable and
need only a tier.

### 4. Apply — `code/174_apply_rulings_to_source_tables.py`

`prime_contracts.csv` gained three columns: `ruling_status`,
`ruling_source_file`, `ruling_applied_date`. **The originating file is carried
onto every row**, so the provenance of each attribution is recoverable from the
table itself.

| `ruling_status` | rows | dollars | of which still unattributed |
|---|---:|---:|---:|
| `RULED_ATTRIBUTED` | 458,548 | $139,773,841,089 | $0 |
| `RULED_NOT_NATIVE` | 34,699 | $5,875,486,547 | $5,800,065,697 |
| `RULED_CLASS_ONLY` | 29,929 | $5,603,581,258 | $5,460,164,121 |
| `RULED_HOLD` | 13,791 | $5,570,778,796 | $802,548,276 |
| `RULED_NAME_KEY_ONLY_NOT_ATTRIBUTED` | 7,715 | $2,024,774,657 | $0 |
| `RULING_CONFLICT` | 2,716 | $596,204,044 | $1,318,755 |
| `RULED_OWNER_NOT_IN_SPINE` | 2,668 | $493,938,088 | $473,868,487 |
| `RULED_TIER_UNSTATED` | 40,590 | $491,663,257 | $375,422,869 |
| `RULED_TIER_C_NOT_ATTRIBUTED` | 96 | $269,771,379 | $269,771,379 |
| **total** | **590,752** | | **$13,183,159,585** |

**`attributed_flag = 1` only at tier A or B.** That is not a choice made here —
it is the convention already in the file (586,185 flagged rows at tier A,
302,618 at B, zero at C). A tier-C ruling records the decision and stays
unattributed, because that is what tier C means.

**Movement:**

| | |
|---|---:|
| rows moved unattributed → attributed | **59** |
| dollars moved | **$483,461.88** |
| unattributed total, before | $65,240,102,268.66 |
| unattributed total, after | $65,239,618,806.78 |
| **unattributed dollars now carrying an explicit ruling status** | **$13,183,159,585 — 20.2% of the pile** |
| ledger rows re-tiered in place | 385 (54 → A, 34 → B, 297 → X) |
| `tier_A_ruled` | 1,580 → **1,634** |
| `links_on_village_corporations` | 866 → **911** |

**The honest headline is the second-to-last row, not the first.** Only $483K
of new attribution was recoverable, because the rulings that could legitimately
attribute at tier A or B had — for the large ANC families — already been
applied: 458,548 prime rows carrying $139.8B were *already* flagged and the
rulings agree with them, which is the strongest available check that the
subject keying is right. **What was actually missing was the record that a
decision had been made at all.** $13.2B of the unattributed pile was sitting
there looking untouched while carrying a verdict, and that — not the $483K — is
what was re-surfacing in the queue.

Name matching is **exact-normalised only**. No containment, no token overlap;
the containment defect has cost this project five separate false attributions.
A name key never carries a positive attribution regardless — only a status
(`RULED_NAME_KEY_ONLY_NOT_ATTRIBUTED`, 7,715 rows).

### 5. Two findings that came out of applying

- **122 subjects carry a ruling that CONTRADICTS what the table already says** —
  `review/ruling_vs_table_contradictions_2026-08-26.csv`. A ruling of
  NOT_NATIVE or HOLD on a row the algorithm has already attributed, or a ruling
  naming a different owner. **Neither side was overwritten.** The algorithmic
  attribution may be wrong, or the ruling may predate a later confirmation, and
  nothing available here can say which. A source disagreeing with itself is a
  finding, not a bug to smooth over.
- **34 subjects carry a class ruling and no owner** —
  `review/ruling_class_only_owner_unnamed_2026-08-26.csv`, **$5,460,164,121**
  unattributed. **Most of that is already settled and must not be sent to a
  human as an open question**, which is why the file carries a `triage` column:

  | triage | subjects | unattributed | reading |
  |---|---:|---:|---|
  | `NEEDS_AN_OWNER` | 7 | **$2,750,399,689** | ruled `NATIVE` and nothing more. **Genuinely open.** `Redstone Defense Systems` $1.36B, `Manu Kai, Llc` $760M |
  | `SETTLED_INDIVIDUAL_NATIVE` | 12 | $2,649,396,854 | `INDIVIDUAL_NATIVE` / `OWNER_NAMED`. **Not open.** |
  | `SETTLED_NO_OWNING_ENTITY` | 13 | $59,834,125 | "Native organisation — members, not owners". **Not open.** |
  | `SPINE_GAP` | 2 | $533,453 | the ruling names the class and says the spine lacks the entity — add it, then re-apply |

  The 12 `SETTLED_INDIVIDUAL_NATIVE` subjects are the class AGENTS.md created on
  2026-08-07: **an individually Native-owned business is its own
  `entity_class`, `parent_native_entity` stays NULL, and it never rolls up to a
  tribe, an ANC or an NHO.** Filing them under "needs an owner named" would
  send a human hunting for a tribal owner the ruling has already said does not
  exist — and 14 of the 34 subjects ($4.12B) already sit in
  `data/clean/individual_native_ownership_verification.csv`. **Only the 7
  `NEEDS_AN_OWNER` rows, $2.75B, are an open question.**

### Tables deliberately NOT written

`federal_funding_transactions.csv` and `subawards.csv` were skipped. At the
time of the run `115_pull_assistance_archive.py fetch 2020 2021 2022` and
`121_pull_subawards_api.py pull --sequential` were live processes writing into
them. **That is a lock on the table, not a gap in the rulings** — the
consolidated ledger is keyed by identifier and the same pass will apply to both
when the pullers finish.

---

## THE CHECK THAT CATCHES THIS

A count of **ruled-but-unapplied subjects**, run on every build, failing when it
rises.

`code/62_no_regression_check.py` already implements it as of this session:

    rulings_unapplied                  1,215
    ruling_log_clusters_reported       (this file)

It reads `data/clean/cedar_ruling_ledger_consolidated.csv` and counts rows whose
`status` column is not `SETTLED`. It reports **UNMEASURED, never 0**, when the
consolidated ledger is absent — because "nobody has measured it" and "there are
none" are opposite findings and must never print the same way. That property is
the entire value of the check: the defect survived for weeks precisely because
the absence of a measurement read as a clean result.

**The metric belongs in `MUST_NOT_RISE`.** A rise means either a new conflict
was found (fine, if a human is looking at it) or a new ruling pass wrote to
`review/` and did not apply — which is the defect returning.

### How `code/160_ship_gap_report.py` should fold it in

160 exists and its `review_backlog()` counts, per file, `rows` and `awaiting`
(rows with a **blank** ruling column). That is the wrong half of the question.
**A file where `awaiting = 0` currently reads as finished, and that is exactly
what a fully-ruled, never-applied file looks like.**

The change is small and local:

1. **Add an `applied` column beside `awaiting` in Section 3.** For each review
   file, join its subjects against `cedar_ruling_ledger_consolidated.csv` and
   report `ruled`, `applied`, `unapplied`. A file reading `ruled=622,
   applied=0` is the defect, on one line, by filename — which is 160's own
   design rule 1 (*never count a drop without naming it*).
2. **Add the dollar exposure.** 160 already has `parse_money` and
   `dollar_exposure` in `scan_table()`. Ruled-but-unapplied dollars is the
   number that makes this a priority rather than a curiosity: $13.2B here.
3. **Give it a line in Section 1 alongside the ship ratio.** Shipping and
   application are the same failure in two places — work finished, artefact
   never reached the shelf. An `application ratio` (applied ÷ ruled) reads
   exactly like the ship ratio and fails for the same reason.
4. **Do not let it print 0 when the consolidated ledger is missing.** Same rule
   as 62.

Until (1)–(4) land, `160` will continue to report a fully-ruled, never-applied
file as clean, and `62` is the only thing measuring it.

---

## RE-RUNNING

    py -3 code/173_consolidate_rulings_ledger.py --check    # report, write nothing
    py -3 code/173_consolidate_rulings_ledger.py            # rebuild the ledger
    py -3 code/174_apply_rulings_to_source_tables.py --check
    py -3 code/174_apply_rulings_to_source_tables.py        # apply
    py -3 code/62_no_regression_check.py

Both are safe to re-run and idempotent. 173 excludes its own outputs from the
sweep by name — swept back in, they would double every verdict and let a
conflict re-enter as evidence for itself. 174 writes `.part` then renames,
backs up to `.bak_<date>_pre174_rulings`, and captures each target's mtime
before reading and re-checks it before the rename, so a concurrent agent's
write aborts this one instead of being clobbered.

**Neither script reads `cedar_identifier_ledger_tiered.csv`, and neither runs
`09_import_rulings.py` or `01_build_entity_spine.py`.**

Codebook: `py -3 code/176_write_ruling_codebook_fragments.py` appends the three
new prime columns to `data/clean/codebook/02_prime_contracting.csv` and writes
`data/clean/codebook/02g_ruling_ledger.csv`. Fragments only — registering them
in `codebook_master.csv` is `41_build_codebooks.py`'s job and 41 is unsafe to
run.

### Script-number collision, recorded rather than renamed

Concurrent agents took 173, 174 and 175 during this session.
`173_refresh_individual_native_results_section.py` and
`174_document_nigc_declination_codebook.py` are somebody else's and are
unrelated to this work. The numbers were left alone because
`62_no_regression_check.py` names `code/173_consolidate_rulings_ledger.py`
directly in its own source, and renaming would break that reference for a
cosmetic gain. AGENTS.md already records that the numeric prefix no longer
guarantees a unique step — check `ls code/<n>_*` before claiming one.

---

## WHAT STILL NEEDS A HUMAN

| file | subjects | dollars at stake |
|---|---:|---:|
| `review/ruling_class_only_owner_unnamed_2026-08-26.csv`, `triage = NEEDS_AN_OWNER` | **7** | **$2,750,399,689** |
| `review/ruling_tier_unstated_2026-08-26.csv` | 420 | $375,422,869 |
| `review/ruling_vs_table_contradictions_2026-08-26.csv` | 122 | — |
| `review/ruling_conflicts_2026-08-26.csv` | 116 | $1,318,755 |
| `review/ruling_class_only_owner_unnamed_2026-08-26.csv`, `triage = SPINE_GAP` | 2 | $533,453 |

**The first row is worth more than the other four combined and is by far the
cheapest: seven firms already ruled `NATIVE`, each needing one sentence naming
the owner.** `Redstone Defense Systems` alone is $1.36B and `Manu Kai, Llc` is
$760M.

The second is a different kind of cheap: 420 rulings that name an owner and
need only a tier written next to them. They fail today for want of a single
letter, not for want of research.
