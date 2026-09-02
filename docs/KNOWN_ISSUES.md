# Known issues — the running ledger

*Opened 2026-09-01 by workstream H. **This is not an audit.** Every line was
first asked "can this be fixed right now?", and the answer is recorded as
**FIXED** (with what was done and how to check it) or **OPEN** (with why it
could not be, and who owns it). A ledger where most lines say FIXED is the
goal; a long OPEN list is the failure mode.*

**Companion documents.** `docs/INVENTORY.md` is what we HAVE (regenerate:
`py -3 code/521_inventory.py`). This is what is WRONG with it.
`docs/DATASET_READINESS.md` is the scoreboard. `review/OWNER_DECISION_QUEUE.md`
is the subset of OPEN items that need a human, restated for the owner.

**Deduplication.** Several defects here were previously described in up to four
documents under different numbers and, in six cases, with different figures.
Where two of our own documents disagreed, the live data was **measured** and
the wrong document was corrected in place with the date and both figures. Those
corrections are logged in §D.

---

## Scoreboard

| | |
|---|---:|
| **defects FIXED this pass** (§A) | **21** |
| OPEN — belongs to a file this workstream may not edit (§B) | 6 |
| OPEN — needs a pipeline rebuild nobody should run unattended (§C1–C3) | 3 |
| OPEN — needs an owner ruling (§C4–C8) | 5 |
| **defects catalogued** | **35** |
| standing conditions — true, known, not defects (§E) | 7 |
| documented contradictions resolved by measurement (§D) | 9 |
| gate state on close | `py -3 code/62_no_regression_check.py` → **exit 0** |

Severity is what a wrong answer costs a **buyer**, not how hard it is to fix:

| | |
|---|---|
| **S1** | a buyer computes a wrong number from a shipped table and cannot tell |
| **S2** | a dataset cannot reach READY until it is closed |
| **S3** | an agent or a session is misled — wasted work, wrong inference, re-litigated decision |
| **S4** | cosmetic or internal-only |

---

# A. FIXED

## A1 · S3 · `502_archive_candidates.py` was proposing a LIVE crawler for archival

**What it was.** The seven-signal dead-script detector's signal 6 — *does it
write anything at all* — was written before the solo B1 de-hardcode sweep and
did not survive it. The sweep rewrote every project-root literal into
`Path(__file__)...parent / "data" / "raw"`, so the path stopped being the
string `data/raw` and became four separate string constants; the regex matched
none of them. It also never recognised a plain `open(p, "wb").write(...)`.

**Evidence.** 48 scripts flipped from "writes nothing anywhere" to "writes"
when the pattern was corrected. Among them `code/ancsa_portal/download.py`,
which fetches from the Alaska STAR portal and saves every PDF into
`data/raw/external/ancsa_portal` — and which the report was listing as an
archive candidate. This is the same failure §17c of
`docs/RELEASE_REPLAY_LOG.md` caught in `516`'s input discovery; the sweep
blinded this detector too and nobody re-ran it.

**Fixed.** Pattern extended for both shapes, with the reason written into the
code beside it. Candidates **3 → 1**; `writes somewhere` **347 → 395**.
Also removed a hardcoded `"code/ holds 419 scripts"` from the docstring — the
live census is printed at the top of the report and should not be duplicated
where it can rot.

**Check.** `py -3 code/502_archive_candidates.py` → `411 scripts · 1 candidates
· 4 guarded`. The one remaining candidate, `code/ancsa_v2/ocr_stats.py`, was
read by hand: it is a **read-only** OCR-yield summariser whose inputs
(`data/interim/ancsa_ocr*/text_scan.json`) still exist, so it is a live
diagnostic and was deliberately **not** archived.

**Consequence for the question "which scripts are dead":** the honest answer is
**none proven dead**. Nothing was moved to `graveyard/` this pass, because
nothing survived the seven signals once signal 6 worked again.

## A2 · S3 · Three collections were documented as planning a script "not in the repository" — all three scripts exist

**What it was.** Debt **D7** in `docs/RELEASE_REPLAY_LOG.md`: *"A collection's
build plan names a script that is not in the repository"* — `deals` →
`build_v2.py`, `lobbying` → `05_match_filings_v2.py`, `natural-resources` →
`update_index.py`. Recorded as `plan_scripts_missing`, MUST_BE_ZERO, and
"confirmed by execution" when a clean-room replay produced
`can't open file … code\update_index.py`.

**Measured 2026-09-01. All five plan-named scripts exist:**

| plan says | actually at |
|---|---|
| `code/build_v2.py` | `code/ancsa_v2/build_v2.py` |
| `code/update_index.py` | `code/ancsa_v2/update_index.py` |
| `code/05_match_filings_v2.py` | `code/lobbying_pull/05_match_filings_v2.py` |
| `code/build_deals.py` | `code/ancsa_portal/build_deals.py` |
| `code/build_manifest_index.py` | `code/ancsa_portal/build_manifest_index.py` |

**The defect is path resolution, not absence.** `516_release_manifest.py`
builds each command as `["py","-3", f"code/{s}"]` from a **basename** the io
map records without its directory, then checks `HERE / s` — flat `code/` only.
`docs/releases/natural-resources-6c92a41/manifest.json` step 6 shows it
exactly: `["py","-3","code/update_index.py"]`, `"exists": false`.

**Partly fixed.** The half in a file this workstream owns is done: the three
dataset runbooks that named non-existent scripts are corrected (§A3). The
`516` half is **OPEN as B5** — one-line change, not this workstream's file.

## A3 · S2 · Three dataset runbooks named build scripts that have never existed

**What it was.** `docs/datasets/01_deals.md`, `compacts.md` and `gaming.md`
each carried a **Build:** line naming a script not on disk:
`code/22_deals_sweep.py`, `code/15_build_compacts.py`,
`code/23_gaming_phase1.py`. All three numbers are taken by unrelated scripts
(`22_apply_temporal_floor.py`, the `15a`–`15e` compact chain,
`23_cross_dataset_propagation.py`), so a reader following the number lands on
the wrong file rather than on nothing.

**Why it is S2, not cosmetic.** Contract point **C9** is *"an update procedure
another session can execute from the document alone"*. A runbook whose build
command cannot be typed fails C9 the moment anyone tries it — which is the
entire test C9 exists to be.

**Fixed** at the source, per the docs' own header (*"Edit the SPEC in that
script, not these files"*): the three `build` entries in
`code/24_generate_dataset_docs.py` now name real commands, with the reason for
each correction in a comment beside it. Regenerating also refreshed row counts
that had gone stale in five other runbooks — `fpds_uei_cage_map` 24,977 →
34,601, `fpds_uei_edges` 2,290 → 5,167.

**Check.** `py -3 code/24_generate_dataset_docs.py`, then
`grep -n '^\*\*Build:' docs/datasets/*.md` — every named script resolves.

## A4 · S3 · `AGENTS.md` carried an OPEN GATE FAILURE that had been closed

**What it was.** `AGENTS.md` CURRENT STATE (2026-08-30) opened with
`#### OPEN GATE FAILURE, named per standing rule 15 — ship_dist_rows`, stating
`62` exits 1. `NEXT_SESSION.md` §1 said the opposite. Standing rule 15 exists
because *"a red gate that is always red reports nothing"* — a **stale** red
gate notice is the same disease with an extra step, because the next session
reads it, assumes the gate is untrustworthy, and stops running it.

**Measured.** `py -3 code/62_no_regression_check.py` → **exit 0**, `no
regressions`. `prime_contracts_entity_year.csv` is 6,715 rows with **0**
literal duplicates — the collapsed grain the correction declared.

**Fixed.** Heading struck and dated; the reasoning kept below it as history,
because it is the clearest worked example in the repo of a correctly named,
correctly owned gate failure that got fixed instead of inherited.

## A5 · S1 · The arbiter document of last resort had gone stale in 6 of 14 rows

**What it was.** `docs/DOC_CONTRADICTIONS_2026-08-26.md` exists to be the
tie-breaker when two build logs disagree — *"before quoting any number from a
build log, check whether it appears below"*. Six of its fourteen ground-truth
rows were themselves wrong within five days, which makes it the most expensive
stale document in the repository: it is consulted **precisely** when someone
already knows the other numbers are unreliable.

| row | said | measured 2026-09-01 |
|---|---:|---:|
| `federal_funding_transactions.csv` | 684,923 | **701,955** |
| `subawards.csv` | 63,548 | **72,837** |
| `cedar_entity_spine.csv` | 1,310 entities / 16 classes | **1,555 / 17** (it moved 1,536 → 1,555 *during* this pass) |
| `ferc_docket_filings.csv` | 81,805 | **102,615** |
| `deals_classified.csv` | 921 / 874 linked | **935 / 886** |
| `cedar_identifier_ledger_final.csv` | 20,559 · A 2,148 · X 197 | **20,577 · A 2,286 · X 468** |

**Fixed.** All six corrected in place, both figures shown, with the date. Two
further rows were *not* wrong but were being read as if they were — see §D2.

**Durable fix.** The register is hand-written and has no generator, which is
why it rotted. `docs/INVENTORY.md` measures all 304 tables and **is**
regenerable; the register now points at it and is kept only for the prose
contradictions, which cannot be regenerated.

## A6 · S1 · The owner queue asked for a ruling on a defect that no longer exists

**What it was.** `review/OWNER_DECISION_QUEUE.md` §4 item 1 —
*"`prime_contracts_entity_year.csv` — **ANSWER FIRST**. (tribe_id,
fiscal_year) collides on 1,751 of 8,464 rows … **Anyone summing
`obligations_usd` by tribe-year double-counts today**"* — and §4b —
*"prime_contracts 80,778 dup rows"*.

**Measured 2026-09-01, both files read end to end:**

- `prime_contracts.csv` — 1,217,768 rows, **0 literal duplicate rows**
- `prime_contracts_entity_year.csv` — 6,715 rows, **0 literal duplicate rows**

**Both claims were wrong, in different ways.** The 80,778 were **distinct FPDS
transactions** whose `modification_number` the mapper never carried;
`430_restore_prime_transaction_key.py` took them to zero **without deleting a
row or a dollar**. And the double-counting claim was false on its own terms:
keyed either way the file summed to the identical cent — the real harm was join
fan-out (a buyer merging their own table got up to 3 copies of *their* rows),
now 1.000×. Acting on the queue as written would have produced a **destructive
de-dupe of real transactions**.

**Fixed.** Both items struck and dated in the queue, with the corrected
measurement and the reason the original mental model was wrong. §4b's list
rebuilt from live measurement: **13 tables, not 15**, every figure re-measured.

## A7 · S3 · Four documents still quoted a grain figure the ratchet had already beaten

**What it was.** `207 of 210 shippable tables have no grain declaration` was
carried, as current, by `docs/ARCHITECTURE_DECISIONS.md` (ADR-007),
`docs/EXTERNAL_REVIEW_RESPONSE.md` (F9), `docs/GRAIN_AUDIT.md` and
`review/OWNER_DECISION_QUEUE.md` §6. `README.md` had a fifth figure, 28.

**Measured:** `contract_grain_unstated_shippable = 25`,
`contract_grain_stated_shippable = 185`, `contract_violations = 0`, and the
ratchet floor in `data/clean/_regression_baseline.json` reads **25**. The
sweep landed 185 DECLARED_VALIDATED · 12 OPEN_WITH_EVIDENCE · 13 DEFECTIVE · 0
unexplained. `GRAIN_AUDIT.md` was the one that had it right, and says
"(was 207)" in its own summary table.

**Fixed** in ADR-007, EXTERNAL_REVIEW_RESPONSE F9, OWNER_DECISION_QUEUE §6 and
README's cleared-contradictions table — each with the old figure, the new one
and the date, so nobody re-derives the old number from a later document.

**RE-MEASURED 2026-09-01, and it has moved again: `contract_grain_unstated_shippable`
now reads 32**, against a ratchet floor of 25 in
`data/clean/_regression_baseline.json`, and `62_no_regression_check.py` is
failing on the rise. `n_shippable` grew 210 → 221 and
`contract_grain_stated_shippable` grew 185 → 189, so most of the rise is new
tables arriving without a grain declaration rather than an old declaration
being lost. `docs/schema/dataset_contracts.json` names all 32.
**The 25 above is what A7 measured when A7 was fixed and is correct as
history; do not quote it as the current figure.** `527_doc_staleness.py` now
reads this number from the contract JSON instead of carrying its own copy —
the previous version hardcoded 25, which is the same defect this entry is
about, in the script written to catch it.

## A8 · S1 · The keyed-identity headline contradicted the table printed beneath it

**What it was.** `docs/TWELVE_DATASET_PLAN.md` — *"2,195,145 entity-bearing
rows scanned; 1,053,435 carry a Cedar id (48.0%)"* — immediately above a table
listing `faads_transactions_all_agencies.csv` as entity-bearing, 0% keyed, and
**2,769,748 rows**. A total smaller than one of its own members has skipped
something, and the number it produced was the headline identity figure for the
whole project.

**Measured**, with the definition now stated in the document and implemented in
code rather than described: **134 entity-bearing tables · 7,250,710 rows ·
3,215,604 keyed = 44.3%**. Tables under 75% keyed: **46**, not 42.

**The correction makes the project's biggest lever bigger, not smaller.**
Keying the two FAADS tables (2,830,409 rows at 0%) moves the global figure
from 44.3% to **83.4%** — 39 points, against the ~20 the plan claimed.

**Fixed** in the plan, with both figures and the arithmetic. The definition is
now executable: `521_inventory.py` imports `503_identity.ID_COLS` rather than
copying it, so the id-column list cannot drift.

## A9 · S3 · The year-coverage section measured Cedar's clock, not the data's coverage

**What it was.** `docs/TWELVE_DATASET_PLAN.md` reported *"109 dated tables · 57
at 2026 · 78 of 109 current through 2025 or 2026"* with no stated scope.

**Two problems, and they pull in opposite directions.** The scan saw fewer than
half the dated tables it could have; and any scan of this kind that accepts a
column merely because it is called `*_date` reads `fetched_date` /
`classified_date` — debt **D4**, 283 wall-clock columns across 12 of 13
collections — and reports **Cedar's own activity as the data's coverage**. The
first draft of `521_inventory.py` made exactly that mistake and reported **255
of 303 tables current through 2026**, `faads_transactions.csv` (FY2001–2007)
among them.

**Fixed** in both places. `521_inventory.py` now refuses provenance columns
**by name** before opening the file, matches coverage columns on how the name
*ends* rather than on a substring (a substring rule read 2098 out of
`value_as_published` and 2057 out of `n_family_mentions_that_year`), and reads
a year only from a cell **shaped** like a year or a date — a loose search found
2099 inside a contract number in a file whose name says FY2000–2007. The plan's
section is rewritten with the scope stated: of the 210 shippable tables, **145
of 165 dated ones are current through 2025 or 2026 (88%)**, 45 carry no
coverage column at all, and 13 carry legitimate future dates (compact
expiries, bond maturities, FPDS `2099` sentinels) which are counted at 2026
rather than allowed to overstate currency.

## A10 · S4 · `README.md` was wrong about the size of its own codebase by 180 scripts

*"222 numbered Python scripts + 4 package dirs"*, in two places. Live: **401
scripts at the top level (375 numbered) + 3 package directories**, 427
recursively — which is what `62` reports as `code_scripts_total`. **Fixed**,
and the paragraph now tells the reader to regenerate rather than quote it, and
carries the live collision count (43) and the `ls code/<n>_*` rule.

## A11 · S3 · `START_HERE.md` said READY 0 / 13

Live: **READY 2 / 13** (`nagpra`, `federal-register`). The line sat inside the
box that tells every new session where to start. **Fixed**, with a pointer to
the regenerated scoreboard and a note not to quote the box.

## A12 · S3 · `NEXT_SESSION.md`'s number-one priority was already done

§4 item 1, *"Register row for the 1,749. Clears the gate"*, was completed and
recorded in §1 of the same document. A completed item at the top of a priority
list makes a reader discount the whole list. **Fixed** — struck, dated, and
re-verified by running the gate and re-measuring the table.

## A13 · S3 · `FOUNDATION_AUDIT.md` F-2 undercounted the pipeline ordering graph

*"80 orderings across 33 tables"*. Live: **103 orderings across 48 tables** (27
curated, each with a paid cost written down; 76 derived from 293's class-6
scan). **Fixed** with both figures.

## A14 · S3 · `FOUNDATION_AUDIT.md` F-2.1 lint counts were a snapshot presented as current

*"7 classes, 147 unwaived"*, class6 at 30. Live: **8 numbered classes (10
gated counters, class 2 splitting a/b/c), 146 unwaived**, class6 **29**, and a
**class 8** that did not exist when the section was written — it was added by
the B1 sweep that closed debt D1 and holds at 0. **Fixed**: the table now
carries an as-written column and a live column side by side.

## A15 · S3 · `FOUNDATION_AUDIT.md` F-4 listed two things as UNVERIFIED that are now verified, and one as true that never was

*"`dist/` holds one CSV; the shipping chain has never been run end to end"* —
`dist/` holds **144 product directories, a 202-table `cedar_press.db`,
`cedar_press_master.xlsx` and 199 `.notes.json` receipts**. Four collections
have since been captured and replayed with 25 tables compared and **4
byte-identical**. *"Only declared grain exists"* — actual grain is now measured
for all 210 shippable tables. **Fixed**, and what remains genuinely unverified
(a full BUILD replay from raw at a stamped commit — debt **D5**, 9 of 13
collections) is stated separately so it is not lost in the correction.

## A16 · S3 · The three "undocumented tables" in the gate and the three standing owner items were the same three tables

`62` reports `tables_undocumented_in_codebook = 3` and
`review/OWNER_DECISION_QUEUE.md` §7 lists three standing publication decisions.
Nothing connected them, so the metric read as an anonymous backlog and the list
read as optional. They are the same three files —
`consultation_agency_coverage.csv` (66 rows),
`gaming_property_locations.csv` (2,212), `wa_machine_transfers.csv` (0) — and
**those three rulings are the only thing between that metric and zero**.
**Fixed** by cross-referencing them in the queue, with live row counts.

## A17 · S1 · A validated grain proof can silently expire, and four have

**What it was.** `docs/schema/grain_evidence.json` records the row count each
table had when `512 probe` proved its key unique. Nothing checks that the file
still has that many rows — so a table can be rebuilt, grow, and keep
presenting a *validated* grain that was proved against a file that no longer
exists. This is the standing rule *"a check reading a key that does not exist
passes for the same reason it is useless"*, one level up: a check whose
**evidence** has expired.

**Measured — 4 tables, two of them claiming a validated grain:**

| table | rows when probed | rows now | delta | grain claim |
|---|---:|---:|---:|---|
| `fpds_uei_cage_map.csv` | 29,981 | 34,601 | +4,620 | unstated |
| `fr_nagpra_title_index.csv` | 6,606 | 6,644 | +38 | **validated** |
| `cedar_correction_register.csv` | 173 | 175 | +2 | **validated** |
| `entity_aliases.csv` | 6,297 | 6,296 | −1 | **validated** |

`fr_nagpra_title_index.csv` is in `nagpra`, one of the two **READY** datasets.

**Fixed** to the extent this workstream can: the check now exists and runs —
`docs/INVENTORY.md` § *Grain evidence that no longer matches the file*,
regenerated by `521_inventory.py`. Re-probing is **OPEN as B6** (`512` belongs
to the integrator).

## A18 · S4 · `502`'s docstring hardcoded a script count

*"code/ holds 419 scripts"*, stale on the day it was read, inside the very
report whose first line prints the live census. **Fixed** — the docstring now
points at the report's own header and says why the literal was removed.

## A19–A21 · S4 · Three defects in this workstream's own new code, caught before publication

Recorded because they are the same shapes this project keeps paying for, and
because a tool that ships with them is worse than no tool:

- **A19** — the year scan accepted provenance columns, reporting 255 of 303
  tables as current through 2026. (See A9.)
- **A20** — `NEVER_RUN` reasons were truncated at the first `.`, turning
  *"Rebuilds cedar_identifier_ledger_final.csv FROM the stale …"* into
  *"Rebuilds cedar_identifier_ledger_final."* — which reads as harmless, the
  exact opposite of true.
- **A21** — the measurement cache was keyed on `(size, mtime)` only, so a
  corrected scanner would have gone on serving answers produced by the broken
  one. Now keyed on `(SCAN_VERSION, size, mtime)`, with the version bumped
  whenever a field changes meaning.

---

# B. OPEN — belongs to a file this workstream may not edit

*Pass-3 ownership: H must not touch any pipeline, `503`, `510`, `512`, `62`, or
`build.py`. Each of these carries the exact change so its owner does not have to
re-derive it.*

## B1 · S1 · `517_export_safety.py` still counts `RESOLVED` as a definite owner

**Owner: the integrator (owns 517).** Of 10,983 `RESOLVED` ownership cells only
**3,669** carry `agrees_with_shipped = 1`; 410 carry `0` (the temporal layer
**contradicts** the shipped owner) and 6,899 are blank. 517 counts all 10,983
as safe, which is how **$86.1B** came to be reported as confirmed. The pipeline
already knows better — `prime_contracts.csv` carries the three-way split, of
which only `CONFIRMED_AS_OF` ($45.63B) may present a definite as-of owner.
**Fix:** adopt that split in 517's counts. Violates *"contradicted may never
ship as definite"* until it lands.

## B2 · S1 · `contractor_ranking.csv` carries no ownership status at all

**Owner: the contractors workstream.** 1,429 rows, the most owner-centric
customer-facing table in Cedar, with `owner_entity_id` and
`owner_obligations_usd` and nothing saying whether the owner is confirmed as of
the transaction. `269_build_contractor_ranking.py` reads `prime_contracts.csv`,
which now carries the status per row, so the roll-up is a small change to that
script. It is a **phase-1 wholesale rebuild** with unattributed enricher
backups already beside it, so it must be planned, not run casually.

## B3 · S2 · `62` does not gate debts D2–D11

**Owner: the integrator (owns 62).** `docs/RELEASE_REPLAY_LOG.md` §7 and §15
have asked for this twice across two passes. D1 was registered (as
`lint_class8`) and promptly went to 0 and stayed there — which is the argument
for registering the rest. Named metrics already specified: D2
`release_outputs_stale_vs_input` (MUST_BE_ZERO), D3 `undeclared_enrichers`
(MUST_BE_ZERO), D4 `nondeterministic_output_columns` (MUST_NOT_RISE, at 283),
D5 `collections_never_replayed` (at 9 of 13), D7 `plan_scripts_missing`
(MUST_BE_ZERO — see B5, the live value is arguably 0 already), D8
`undiscovered_inputs` (MUST_NOT_RISE, at 203), D9
`release_captures_non_quiescent`, D10 `build_plan_calls_a_live_api`, D11
`tables_no_planned_script_writes`.

## B4 · S1 · The identity spine is rebuilt by scripts that destroy it, and only prose stops that

**Owner: the `_entity_layer` workstream.** `01_build_entity_spine.py` and
`09_import_rulings.py` are listed as declared rebuilders of
`cedar_entity_spine.csv`, `cedar_identifier_ledger.csv`,
`cedar_identifier_ledger_final.csv` and `cedar_identifier_ledger_tiered.csv` —
and both are on `cedar_pipeline.NEVER_RUN`. `41_build_codebooks.py` is the
declared rebuilder of `codebook_master.csv` and would delete 21 of its 43
blocks. `guard()` catches a *runner* that calls them; it does not stop
`build.py run _entity_layer --execute` from planning them. Named in
`docs/INVENTORY.md` § *Tables whose build or enrich chain contains a NEVER_RUN
script*, which is the first place they have all appeared together.

## B5 · S3 · `516_release_manifest.py` loses a script's directory, which is the whole of debt D7

**Owner: whoever holds 516.** See §A2 for the measurement. The io map records a
**basename**; 516 rebuilds the command as `f"code/{s}"` and then tests
`HERE / s` against flat `code/`. Five scripts live in `code/ancsa_portal`,
`code/ancsa_v2` and `code/lobbying_pull` and are therefore reported missing
while sitting on disk. **Fix:** resolve `s` with `next(CODE.rglob(s), None)` and
emit the path relative to the repo root; keep the `exists: false` branch for the
genuine case. Expected effect: `plan_scripts_missing` 3 → 0, and three documented
rebuild commands become executable.

## B6 · S3 · `cedar_pipeline`'s write detector fires on a quoted path segment, not on the file mode

**Owner: whoever holds `cedar_pipeline.py` (shared, read-only to every
workstream).** Same root cause as §A1, opposite direction: the B1 de-hardcode
sweep turned single path literals into runs of quoted path segments, and
`_WRITE_HINTS`'s alternative

```
open\([^)]*['\"][wax]
```

is meant to catch `open(path, "w")` but matches **any quoted string beginning
w, a or x anywhere inside the `open(...)` call**.

**Proven instance.** `code/ancsa_v2/ocr_stats.py` is a read-only summariser
with **no `open()` in any write mode**. `cedar_pipeline.classify()` calls it
`enricher`, evidence `read-modify-writes: _SOURCE_MANIFEST.csv`. The match is
the `"a` of `"ancsa_portal"` in
`open(os.path.join(ROOT, "data", "raw", "external", "ancsa_portal", "_SOURCE_MANIFEST.csv"), ...)`.
It reads that manifest and never writes it.

**Blast radius, measured:** 38 scripts contain a match of the loose pattern
while having **no `open()` in a write mode at all**. Most of those write by
other means (`.write_text`, `to_csv`, a `DictWriter`) and are correctly
classified for a different reason — but the *file-level attribution* is wrong
wherever it fires, and a false `read_modify_write` is what `classify()` turns
into `enricher`, which `derived_orderings()` turns into an ordering a build
runner is told to honour. An invented ordering is cheap; a **missed** one costs
a rebuilt table, which is the failure this module exists to prevent, so the
false positives make the real signal harder to trust.

**Fix (the module already parses the AST, so this adds nothing):** find
`Call(func=Name('open'))` and read `args[1]` / `keywords['mode']`. A mode is
the second positional argument or the `mode=` keyword — never an arbitrary
string inside the call. Keep the regex as a fallback only for the write
helpers (`to_csv`, `DictWriter`, `write_text`) where there is no AST shape to
key on.

**Guarded meanwhile:** `py -3 code/521_inventory.py selftest` asserts that
`502` proposes neither the live ANCSA crawler nor a clean-table writer for
archival, which is the consequence that actually bit.

---

# C. OPEN — needs an owner ruling, or a rebuild nobody should run unattended

*Each of these is already in `review/OWNER_DECISION_QUEUE.md` with its evidence.
Listed here so the defect ledger is complete, not to duplicate the queue.*

## C1 · S1 · `faads_transactions_all_agencies.csv` — 179,259 duplicate rows, diagnosed, not repaired

2,769,748 rows, 6.5% byte-identical duplicates. **Not a page fetched twice:**
174,348 of them (97%) come from one staged object, `ed_fy2007_archive.zip`, and
174,957 are FY2007, while 40 other agency-years are almost clean. The staged
zip carries `assistance_transaction_unique_key` and `modification_number` among
its 112 columns and `30_funding_pre2008.to_out_row` took neither — the same
projection loss proved exactly on the prime archive, where 80,778 apparent
duplicates went to **zero without deleting a row**. The mapper is already
fixed; repairing the file needs a full re-extract of a 2.77M-row shipped table
plus a `503 stamp` re-run. **Blocks `funding`.** Queued deliberately rather
than run unattended.

## C2 · S1 · `subawards.csv` — 10,770 duplicate rows, same shape suspected, unproven

72,837 rows; `(subaward_number, subaward_date)` collides 27,470 times, so even
a subaward's natural key is not unique here. **Prove or disprove the projection
-loss shape before touching the data** — on prime contracting, de-duping on the
audit's reading would have deleted real transactions. `native_passthrough.csv`
inherits the duplication (114 of 1,262) and its passthrough dollars are
over-stated by an unmeasured amount. **Blocks `subcontracting` and `funding`.**

## C3 · S1 · `cedar_ruling_ledger_consolidated.csv` — 40% duplicate rows

6,302 of 15,587. A ruling ledger that records the same ruling twice cannot be
counted, and 157 source files feed it. `cross_dataset_ruling_map.csv` is 30%
(2,228 of 7,507) and `cedar_identifier_graph_edges.csv` 5.3% (2,451 of 46,051)
— duplicate graph edges inflate `n_asserting_sources` and every degree count
derived from it, which is the number `docs/SPIDERWEB_LEARNING_PLAN.md` is about
to mine. **Blocks `_entity_layer`.**

## C4 · S2 · Nine grain rulings only a human can make

`fpds_uei_cage_map` (a map that maps nothing uniquely — `uei` repeats 11,455×),
`foia_request_index` (no key at any arity ≤ 6; `foia_request_id` repeats 381×),
`gaming_projections` (the build log's stated grain is contradicted by the
data), `ferc_ex_parte_communications` (its own id collides 56×),
`contractor_ranking` (unique only with a MEASURE in the key),
`tribal_bond_issuances` (`cusip` blank on all 29 rows),
`visitor_record_foia_requests`, and five 0/1-row tables where uniqueness is
vacuous. Full evidence per table in `docs/GRAIN_AUDIT.md`. **Blocks
`contractors`, `gaming`, `lobbying`, `natural-resources`, `deals`,
`_entity_layer`.**

## C5 · S1 · BBAHC — 742 rows keyed to the wrong entity, evidence complete, sign-off only

`ANRC-BRBYCO-00` (Bristol Bay Native Corporation) is keyed to "Bristol Bay Area
Health Corporation" across 742 rows in 9 tables. Different entities; the
owner's own FA-01 ruling already says so; the unlink half is done. Waiting on
one yes/no. Informational in `62` (`FA-01`), not gating — which is why it has
survived three passes.

## C6 · S1 · $2.1B of transactions have an as-of owner contradicting the shipped id

9,259 transactions / $2.074B read `CONTRADICTED_AS_OF`. The decision is how
loudly to queue them, not whether they are real.

## C7 · S2 · Blocklisted parents may currently win an as-of ownership query

78 of 2,684 edges are registrant roll-ups ("GOVERNMENT OF THE UNITED STATES")
that participate in resolution today. Recommendation on file: exclude from
winning, keep as evidence rows.

## C8 · S2 · Three tables cannot ship until a publication decision is made

See §A16. `consultation_agency_coverage.csv`, `gaming_property_locations.csv`
(1,471 `publishable = Y` / 741 `N`), `wa_machine_transfers.csv` (0 rows). These
three ARE `tables_undocumented_in_codebook = 3`.

---

# D. Where two of our own documents disagreed, and which was right

| the disagreement | documents | measured 2026-09-01 | which was right |
|---|---|---|---|
| **D1** literal duplicates in `prime_contracts.csv` | `OWNER_DECISION_QUEUE` §4b said 80,778; `GRAIN_AUDIT` omitted the table entirely | 1,217,768 rows, **0 duplicates** | **GRAIN_AUDIT.** `430` had already repaired it. The queue was still asking for a de-dupe that would have deleted real transactions |
| **D2** tables with duplicate rows | `OWNER_DECISION_QUEUE` §4b said "fifteen"; `GRAIN_AUDIT` said 13 | **13**, each re-measured and matching `grain_evidence.json` to the row | **GRAIN_AUDIT** |
| **D3** shippable tables with no grain | `ADR-007`, `EXTERNAL_REVIEW_RESPONSE` F9 and `OWNER_DECISION_QUEUE` §6 said 207; `README` said 28; `GRAIN_AUDIT` said 25 | **25**; baseline floor 25 | **GRAIN_AUDIT** |
| **D4** is the gate red? | `AGENTS.md` said OPEN GATE FAILURE, `62` exits 1; `NEXT_SESSION` §1 said cleared, exit 0 | **exit 0**, `no regressions` | **NEXT_SESSION** |
| **D5** global keyed identity | `TWELVE_DATASET_PLAN` said 48.0% on a 2,195,145-row denominator — smaller than one member table it listed | **44.3%** on 7,250,710 entity-bearing rows | **Neither.** The plan's denominator was internally impossible; corrected in place with the definition now executable in code |
| **D6** `identity_facts_legacy_only` floor | `EXTERNAL_REVIEW_RESPONSE` said 4,100 | **4,089**; baseline reads 4089 | **the baseline.** Exposure had shrunk by 11 and the gate had already locked in the smaller number |
| **D7** do three collections plan a missing script? | `RELEASE_REPLAY_LOG` D7 said 3 collections name scripts "not in the repository", one "confirmed by execution" | all **5** plan-named scripts exist, in `code/` subdirectories | **Neither.** The traceback was real; the diagnosis was not. It is a path-resolution defect in `516` — see B5 |
| **D8** rows in `federal_funding_transactions.csv` | `DOC_CONTRADICTIONS` ground truth said 684,923; `START_HERE` said 701,955 and flagged the other as stale | **701,955** | **START_HERE**, which had already caught it — the arbiter document had not |
| **D9** script census | task framing said 414; `502` said 397 then 411; `62` says 427 | `code/**/*.py` = **427** (411 excluding the 11 shared `cedar_*` libraries, which is 502's scope) | **all of them, on different scopes** — none stated its scope. Now stated in `docs/INVENTORY.md` and in 502's own header |

---

# E. Standing conditions — true, known, not defects

Recorded so they are not re-discovered as findings every pass.

- **`rulings_unapplied = 1,215`** of 15,587 consolidated rulings carry
  `CONFLICT_NOT_APPLIED`. *"A ruling that is not applied back to its source
  table is not a ruling, it is a note."* Reported by `62`, not gated.
- **`corrections_not_propagated = 2`** — `F-DELAWARE-ALIAS` reached
  `entity_aliases.csv` but not `cedar_identifier_ledger_final.csv` or
  `cedar_identifier_ledger_tiered.csv`. `354_correction_register.py --check`
  lists them.
- **`files_with_an_inplace_enricher_backup = 174`, `columns_lost_vs_backup =
  0`.** 174 receipts, nothing currently reverted. The metric that matters is
  the second one and it is zero.
- **43 script numbers collide within one directory.** Ratcheted MUST_NOT_RISE.
  `ls code/<n>_*` before citing any script by number. **Two of these collisions
  involve a NEVER_RUN script** and are worth naming separately — surfaced
  2026-09-01 in `docs/INVENTORY.md` § NEVER_RUN:

  | guarded, destructive | shares its number with |
  |---|---|
  | `41_build_codebooks.py` — deletes 21 of 43 codebook blocks | `41_match_subawards_to_ledger.py` |
  | `88_build_deals_taxonomy.py` — discards the party rulings | `88_gaming_property_federal_traces.py` |

  `cedar_pipeline.guard()` keys on the **filename**, so the guard itself is
  safe. The hazard is human: "run script 88" and `code/88_*.py` each name two
  files, one of which destroys work. Renaming either side is not free — the
  guard's key is the filename and every doc reference would move — so this is
  recorded rather than fixed.
- **6 handoffs await independent verification** (`py -3 code/513_handoffs.py
  list --unverified`) — `nagpra` closure, `federal-register` closure, the
  correctness pass, workstream I's ruling mine, and this pass's own
  (`HAND-C3370B5C2A`, workstream H). Self-verification is refused by
  construction; a different session must re-execute their `verify_commands`.
  This document's are in §F.
- **C9 has never been tested for either READY dataset.** The contract says
  another session can execute the update procedure from the document alone.
  Nobody has tried. It may demote a dataset, and that is the point.
- **The codebase carries essentially no `TODO`/`FIXME`/`XXX`/`HACK` markers** —
  two hits across 427 files, and both are false positives (a regex that
  *detects* placeholders, and the string "TERO" inside a note). Debt here is
  recorded in documents and in the gate, not in comments. That is a deliberate
  and unusual discipline; do not start seeding TODOs.

---

# F. How to verify this pass, without trusting a word of it

Every claim above is re-executable. These are the commands, and each one's
exit 0 is the proof:

```bash
py -3 code/62_no_regression_check.py        # the gate. exit 0, "no regressions"
py -3 code/521_inventory.py selftest        # 23 fixtures; each asserts a NAMED defect stays fixed
py -3 code/521_inventory.py                 # regenerate docs/INVENTORY.md from live data
py -3 code/502_archive_candidates.py        # 1 candidate, and it is a read-only diagnostic
py -3 code/24_generate_dataset_docs.py      # every **Build:** line names a script that exists
py -3 code/512_build_dataset_contracts.py verify   # grain, PKs, cardinality — read-only
```

Two spot measurements, because the corrections in §D turn on them and a reader
should not have to take them on faith:

```bash
# prime_contracts has ZERO literal duplicate rows (the queue said 80,778)
py -3 -c "import csv,hashlib,sys; csv.field_size_limit(2**31-1); \
r=csv.reader(open('data/clean/prime_contracts.csv',encoding='utf-8-sig',newline='')); next(r); \
s={}; n=0
for x in r:
    n+=1; k=hashlib.md5('\x1f'.join(x).encode('utf-8','replace')).digest(); s[k]=s.get(k,0)+1
print(n, sum(c-1 for c in s.values() if c>1))"
#   -> 1217768 0

# every script the release plans actually exists, in a subdirectory (debt D7)
for f in build_v2.py update_index.py 05_match_filings_v2.py build_deals.py build_manifest_index.py; \
  do find code -name "$f"; done
```

**One caveat, stated rather than hidden.** Three other workstreams were writing
to `data/clean` and `data/spine` during this pass. The spine moved 1,536 →
1,555 *while these documents were being written*, and `fpds_uei_cage_map.csv`
grew by 4,620 rows between two runs minutes apart. Every count here is stamped
2026-09-01 and is regenerable; **`docs/INVENTORY.md` is the live answer and
this document is not**. Where they disagree, regenerate and believe the
inventory.

<!-- BEGIN INT-READY -->
## D1 · S1 · `503_identity.py` would REINTRODUCE the retired CICD scheme on its next rebuild

*Found 2026-09-02 by workstream INT-READY while enriching the identity
register. Not repaired here: 503 is identity-critical and owned elsewhere, and
an agent that cannot test every consumer should not edit its writer.*

`code/843_retire_cicd_scheme.py` retired the legacy CICD identifier scheme on
2026-09-01 and dropped `same_as_legacy_cicd` from
`data/spine/cedar_identity_register.csv`. The column is gone from the data and
the standing instruction is that it must not come back.

**`503_identity.py` line 1090 still names it.** The register is written from a
fixed list:

```python
regcols = ["cedar_uid", "handle", "cedar_entity_id", "canonical_name",
           "entity_class", "class_since_basis", "former_names",
           "same_as_legacy_cicd", "minted", "register_status"]
```

`503 --apply` therefore rewrites the register WITH a `same_as_legacy_cicd`
column — empty, because the data is gone, but present and named, and line 1063
still prints a count of it. A retired scheme returning as an empty column is
worse than one that never left: it looks like a scheme with no data rather than
a scheme that was withdrawn.

**The same fixed list is why `961`'s five columns are declared as reverted in
`cedar_pipeline.KNOWN_ORDERINGS`** — a 503 rebuild drops the Federal Register
legal name for 536 entities along with it.

**Fix:** delete `"same_as_legacy_cicd"` from `regcols` and the print at 1063,
and add the five 961 columns to the list or re-run 961 after every 503. Both
are one-line changes; neither should be made blind.

## D2 · S2 · `docs/WHAT_IS_MISSING.md` carries two figures that do not reproduce

*Measured 2026-09-02 with `csv.reader` against the live files, while acting on
that document. Recorded because the document is being used as a work list and
these two lines will be quoted.*

| claim | where | measured 2026-09-02 |
|---|---|---|
| `spend_reported_usd` … "406 non-zero, **$645.1M**" | lobbying #1 | the total reproduces to the cent — **$645,052,868.51** — but **351** rows are greater than zero, not 406 |
| `native_entity_lobbying_disclosures.csv` "(43,963 filing-grain rows…)" | lobbying, closing note | the file holds **27,825** rows × 40 columns |

Neither changes a conclusion in that document — the money is right and the
table exists — and both would be quoted as-is by the next reader.

Two more figures in it were re-derived and are correct or nearly so: 694 of 787
facilities carry a revenue bound (exact), and 509 register entities differ from
their FR legal name (**510** on the current files, using `entry_kind = entity`
as the pool).

**One is a real overstatement of coverage.** gaming #2 says Class II/III is
available for *"263 of the 284 facility-bearing tribes (93%)"*. 263 is the
count of facility-bearing tribes that have **any ordinance row**; the count
that have a **stated class** on one is **256**. The distinction is small and it
is the difference between a join that lands and a join that lands on a blank.

## D3 · S1 · Four Ho-Chunk identifiers are keyed across two unrelated nations, one at tier A

*Found 2026-09-02 by `code/963_flag_named_collision_families.py`, which the
owner's own list asked for. **Nothing was changed.** The ledger's md5 is
identical before and after the scan and no `cedar_uid` moved; the proposals sit
in `review/named_collision_families_2026-09-02.csv` for a human ruling.*

`Ho-Chunk` names two unrelated nations. **Ho-Chunk Nation of Wisconsin**
(`CE-00150-XS`, WI) is a government. **Ho-Chunk, Inc.** is the economic
development arm of the **Winnebago Tribe of Nebraska**, and its operating
companies are Ho-Chunk Farms, Ho-Chunk Builders, Ho-Chunk Shared Services and
Ho-Chunk Construction Management Services — all Nebraska.

`cedar_identifier_ledger_final.csv` currently holds rows going **both ways**:

| tier | id | legal business name | keyed to | suspected owner |
|---|---|---|---|---|
| **A** | CAGE `3VFL3` | `Ho-Chunk Nation` | **Winnebago Tribe of Nebraska (NE)** | Ho-Chunk Nation of Wisconsin |
| B | UEI `DMA6EKCMAPB7` | `Ho Chunk Inc` | Ho-Chunk (WI) | Winnebago Tribe of Nebraska |
| B | CAGE `7CE83` | `HO-CHUNK FARMS, INC.` | Ho-Chunk (WI) | Winnebago Tribe of Nebraska |
| B | CAGE `8APB4` | `HO-CHUNK CONSTRUCTION MANAGEMENT SERVICES COMP` | Ho-Chunk (WI) | Winnebago Tribe of Nebraska |

Winnebago separately and correctly holds `Ho-Chunk Inc` CAGE `52S22` at tier A,
`Ho-Chunk Builders Company` and `Ho-Chunk Shared Services Company` — so the
ledger holds the SAME firm family under both nations at once. Prime dollars on
the four flagged rows total **$0.01M**, so the money at stake is negligible and
the identity error is not: a tier-A CAGE is what a downstream join trusts.

**One more, lower confidence, in the Cherokee family:** EIN `133844128`
`NORTH EASTERN BAND OF CHEROKEE` is keyed to **Lumbee** (NC). Flagged as a
suspicion, not a finding — a longer name can contain a shorter one and still be
a third organisation.

**The two other pairs the owner named came back clean.** Every decisive
`Cherokee Nation` / `Eastern Band of Cherokee` / `Keetoowah` row (77) and every
decisive Seminole row (12) is keyed to the right nation. The Keetoowah repair
of 2026-09-01 is holding.

<!-- END INT-READY -->
