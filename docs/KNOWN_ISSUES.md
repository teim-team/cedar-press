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

## A5 [RESOLVED 2026-09-02 — see note at end] · S1 · The arbiter document of last resort had gone stale in 6 of 14 rows

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


<!-- BEGIN STANDARD-PUNCHLIST-GUARD -->
## STANDARD — do not act on these punch-list lines (2026-09-02)

**OPEN, and it is an instruction defect, not a stale number.**
`docs/datasets/_PUNCHLIST.md` is generated by `code/526_dataset_standard.py`,
whose `scan()` stops at 20,000 rows and then asserts, on that prefix, that a
column is *"always empty in 20,001 rows"*. Re-counted over the full files by
`code/1107_punchlist_claim_verify.py`: **43 of 65 such claims on the 13 capped
tables are FALSE.**

The one to see before anything else — `prime_contracts.csv` carries the line
*"drop 10 always-empty column(s)"*, and all ten hold data:

| column | non-blank rows of 1,217,768 |
|---|---:|
| `contract_transaction_unique_key` | 841,002 |
| `contract_award_unique_key` | 841,002 |
| `naics_code` | 838,229 |
| `action_date` | 841,002 |
| `award_type` | 769,868 |
| `geo_award_unique_key` | 841,002 |
| `naics_description`, `product_or_service_code`, `product_or_service_code_description`, `award_base_description` | 247,987 each |

**Before acting on any `C11 … always empty` or `C5 … no conservation coverage`
line, check it against `docs/datasets/_PUNCHLIST_CLAIM_AUDIT.md`**, which is
regenerated beside the punch list and names every false claim with its true
count. `py -3 code/1107_punchlist_claim_verify.py verify` exits 1 while any
remain.

**FIXED, same pass:** no `C11 … write codebook entries` item could close at all,
because `cedar_codebook.py build` was refusing to run — 14 rows sat in
`codebook_master.csv` that no fragment carried, and `build` refuses any rebuild
that shrinks the codebook. An agent could write the fragment exactly as `392`
instructs and the punch item would never move. Repaired by
`py -3 code/1108_codebook_fragment_repair.py repair`; `cedar_codebook.py check`
reports 0 lost / 0 added. **Write fragments, never the master, and run
`py -3 code/cedar_codebook.py build` afterwards or your work will not be
measured.**

**FIXED:** `07_gaming / casino_city_id` was `published=1, access_tier=public` in
the codebook, and `03_federal_funding / recipient_duns` was `published=1` with
`access_tier=internal`. `62`'s `duns_marked_publishable` caught neither: it
reads `access_tier` and not `published`, and it greps the variable name for
"duns", so a Casino City key is invisible to it. Both are now `0/internal`.
`dist/` was never affected — it already withheld the column — but the codebook
is what a buyer reads. Standing check: `py -3
code/1108_codebook_fragment_repair.py verify` (K4 uses
`cedar_codebook.is_licensed_col`, not a name grep).
<!-- END STANDARD-PUNCHLIST-GUARD -->

<!-- BEGIN STALE-TAIL-1081 -->
## The stale-entity tail — what is left, and the one acquisition that would close it

*Added 2026-09-02 by workstream STALE-TAIL (ADR-025). Full write-up and the
regenerable before/after: `docs/STALE_TAIL_CLOSURE_1081.md`. Measure:
`py -3 code/1081_stale_tail_dated_facts.py measure`.*

| 830 measure | before | after |
|---|---:|---:|
| untouched over a year | 287 | 398 |
| no usable date at all | 373 | **148** |
| in no substantive Cedar row | 83 | **0** |
| union of the first two | 660 | **546** |
| p90 days since change | 3,627 | **1,365** |

`untouched over a year` rose because 287 was an undercount — an entity with no
date could not be counted as stale. 255 entities gained a first dated public
fact and most of those dates are old, so they became visible rather than fresh.

**A1. `www.commerce.alaska.gov` (Alaska DCCED corporations register) is
`NOT_ACQUIRED` because the host refuses automation.** HTTP 403 with a DataDome
CAPTCHA on `robots.txt`, on the entity search and on the bulk
`CorporationsDownload.CSV`, measured 2026-09-02. This is the single source that
would date **95** Alaska Native village and ANCSA-group corporations at once —
every Alaska corporation has a stated registration date, status and
biennial-report date there. It needs a human-driven or records-request route.
It is **not** `SOURCE_DOES_NOT_PUBLISH`.

**A2. The ANCSA annual-report corpus cannot substitute for A1.** The 358
audited AS 45.55.139 reports in `data/interim/ancsa_txt_v3/` come from **41**
corporations; exactly **one** of the 95 tail entities is among them. AS
45.55.139 exempts the small village corporations, which is the whole tail.
Do not re-open this as a mining task.

**A3. 170 Native Hawaiian Organizations have no dated public record on any
route tried.** A sibling established they do not publish on their own sites;
this pass established that **258** of them return no organisation at all from
the IRS Exempt Organizations file under their register name and state. Most are
homestead associations and *hui* that are not 501(c)(3) filers. The SBA 8(a)
register and the NHOA directory remain untried and are the next candidates.

**A4. NCES cannot make a BIE school look fresh, by construction.** CCD's newest
collection year for fips 59 is 2024 (count date 2024-10-01), and the BIE
reporting universe is static — the same 174 schools in every year 2008-2024 —
so "most recent year reported" is one shared date outside the 365-day bar. CCD
is still what took *no substantive row* from 83 to 0: it supplies the NCES BIE
school number, LEA, enrolment, teacher FTE, status and location.

**A5. `code/62_no_regression_check.py` DOES NOT RUN as of 2026-09-02 03:5x.**
`NameError: name 'ROOT' is not defined`, from `_load_declared_removals()` at
line 131 being *called* at line 159, above where `ROOT` is bound. The 37 lines
that introduce it are **uncommitted** (`git diff HEAD` = 1 file, +37) and
postdate commit `ada1845`. Not this workstream's file and not this
workstream's edit — 62 is integrator-owned — but every gate downstream of it
is currently unrunnable, so it is recorded here rather than left to the next
agent to rediscover. `293_lint_bug_classes.py` and `845_regenerate_guard.py`
both run.

> **RESOLVED** — see the `A5-RESOLUTION` block below. The loader now
> derives its path from `__file__` and `62` imports clean. A failure observed
> inside a live edit window is real but perishable.

**A6. `docs/schema/dataset_contracts.json` may lag `512` by one run, and it is
a write race right now.** `GRAIN_STALE_TAIL` is declared in
`code/512_build_dataset_contracts.py` (verified: `entity_dated_public_facts.csv`
is in `GRAIN` at import), but the artefact on disk still lists that table as
`UNDOCUMENTED` — it was written by one of the **four concurrent `512`
processes** running on 2026-09-02, at least one of which started before the
dict was added. A third write was deliberately NOT started: `512` rewrites that
JSON wholesale and racing it is how a contract silently loses a block. The next
single run of `512` picks the declaration up. Verify with
`python -c "import json;print('entity_dated_public_facts' in open('docs/schema/dataset_contracts.json').read())"`
and then check the entry says `UNDOCUMENTED` no longer.
<!-- END STALE-TAIL-1081 -->

<!-- BEGIN QUARANTINE -->
## The quarantine is now visible — and $10.9B of it is still open (workstream QUARANTINE, 2026-09-02)

`code/1079_quarantine_method_exposure.py`, ADR-019, full write-up in
`docs/QUARANTINE_EXPOSURE_LOG_2026-09-02.md`. CDR-11 and CDR-12 in
`review/1011_cross_dataset_findings.csv` are closed. **These four are not.**

**1. The CAGE leg of the quarantine was measured for the first time and is
adjudicated only where a SECOND source confirmed it — 502 identifiers,
$3,536,050,157 remain.** CDR-11 scoped on UEI ledger
rows; `40_build_prime_contracts.py` keys on three legs. `cage_exact` on a
quarantined CAGE row carries 14,149 prime rows and $7.25B, and `need_v6` —
**6.5% accurate** — is 838 tier-B CAGE rows of it. It is flagged in
`identifier_ruling_quarantined` and written to
`review/1079_owner_holds_2026-09-02.csv`; it is not repaired. Adjudicating a
population in the same pass that discovered it is the mistake this repo keeps
paying for — so the only CAGE rows repaired are the two named families where an
INDEPENDENT workstream reached the same verdict (North Wind / LBYD, and Copper
River). **This is the largest single piece of unfinished attribution work in
contracting.**

**1a. A NEIGHBOURING PASS IS WITHDRAWING ROWS IN A WAY NO CONSUMER CAN SEE.**
Found 2026-09-02 on the Copper River family: rows were "withdrawn" by writing a
240-character English sentence into `prime_contracts.attribution_method` while
leaving `tribe_id` populated. The rows stayed attributed — `tribe_id` is what
every consumer keys on — and the prose also put that column outside
`40_build_prime_contracts.py`'s vocabulary. This is CDR-11 in a mirror: there
the method column hid a ruling, here it *was* the ruling and nothing else
recorded it. 1079 no longer trusts the column (it falls back to 40's own
resolution order and counts `unknown_attribution_method_rows`), but **the
convention itself needs a ruling**: a withdrawal must clear `tribe_id`.

**1b. $1.5B THAT A COMMIT MESSAGE CALLS ATTRIBUTED IS NOT ATTRIBUTED IN THE
TABLE.** The same pass then *attributed* the Copper River family to the Native
Village of Eyak on excellent evidence — `copperrivermc.com`, verbatim: *"Owned
by the Native Village of Eyak, the Copper River Family of Companies …"* — and
recorded it the same way. Measured on the live table 2026-09-02 after all
passes: **4,294 Copper River rows, $1,512,965,388, and `tribe_id` is blank on
4,288 of them.** `canonical_name` and `cedar_uid` say Native Village of Eyak;
`confidence_tier` is `C` and `attributed_flag` is `0`; six rows name Eyak in
`canonical_name` while `tribe_id` still says `ANVC-SLDVSS-00` (Seldovia), so
the row disagrees with itself. **No ledger row keys any Copper River identifier
to an Eyak hub**, so a rebuild reverts the whole thing.
**The destination is right and the write is unfinished.** 1079 deliberately did
not finish it: attributing $1.5B from another workstream's prose, with no
ledger row behind it, is the failure mode this pass exists to remove. 1079's
tier X does **not** block the fix — `40_build_prime_contracts.py` skips tier X
and takes the first tier A/B row, so a ruled Eyak ledger row wins a rebuild.

**2. $6,254,678,105 across 758 identifiers is HELD, not decided.** Unresolved
is a legitimate outcome (ADR-010), but it is a queue, not an answer. The
biggest four are named in the log's §6.

**3. A hub whose ENTIRE distinctive name is one ordinary English word is still
unguarded.** The fragment rule needs a second token to be a fragment *of*, so
it cannot fire for `Marshall`. `MARSHALL COMMUNICATIONS CORP` ($336.3M) is
therefore KEPT on the Native Village of Marshall by rule 7's residue test,
while its FPDS-declared parent is `MISSION SOLUTIONS GROUP INC` observed 1,050
times and resolving to no hub. Defensible under the written rules, and probably
wrong. Needs an owner ruling, not a wider automatic rule.

**4. `1079` joins the enrichers that a rebuild reverts.**
`40_build_prime_contracts.py` drops all five new columns, as it drops 207's
two, 950's nine and 871's thirteen. 1079 must run **last** of those, because it
reads `attribution_method`. The
`.bak_2026-09-02_pre_1079_quarantine_method_exposure` files beside the five
touched tables are the signal.
<!-- END QUARANTINE -->

<!-- BEGIN A5-RESOLUTION -->
### A5 resolved — `62` NameError was a two-minute window

`_load_declared_removals()` was added at import time and used `ROOT`, which is bound further down the module. Reported by the stale-tail workstream, and true when it looked. The loader now derives its path from `__file__` instead, and `62` imports clean: `runpy` with `run_name='not_main'` raises no `NameError`, and a full run has completed since. **A failure observed inside a live edit window is real but perishable — re-measure before recording it as an issue.**
<!-- END A5-RESOLUTION -->

<!-- BEGIN HARVEST-COVERAGE-1112 -->
## `docs/SHARD_COVERAGE.md` measures site discovery, not harvest — and two of its shards are mislabelled

*Measured 2026-09-02 by `code/1112_harvest_coverage_matrix.py`. Full account:
`docs/HARVEST_COVERAGE_AUDIT_2026-09-02.md`.*

- Its **`untouched = 0`** column is true and is about `cedar_web_map.csv` membership.
  Per *thing* — enterprises, CAGE/UEI, individual-business directories, gaming,
  newsletters — the never-checked count runs **373 to 1,439 of 1,555**.
  **CAGE / UEI / DUNS has never been looked for on 1,439 of the 1,555 (92.5%).**
- **`shard_l` and `shard_m` are listed `NOT_STARTED`. Both ran.** shard_l holds 152
  entity verdicts and 13 probe logs; shard_m holds a 148-entity deep probe and a
  149-entity host log. The shard table is keyed on web-map rows and they wrote none.
- **`1,254 with a URL` does not reproduce**: 1,275 entities have a 2xx URL of a
  non-dead type, 1,484 have any URL string.
- **185 of 185 BIE Schools have never been looked at for any of the five things**,
  though 182 of them have a live site.

Per-entity, per-thing state with the artefact that proves each cell:
`data/clean/cedar_harvest_coverage_matrix.csv` (7,775 rows).
<!-- END HARVEST-COVERAGE-1112 -->

<!-- BEGIN RULING-PROPAGATION-1116 -->
## The 44th script-number collision is `1123`, and it is not this pass's

*Added 2026-09-02 by the ruling-propagation pass (ADR-026). Named here because
`docs/AGENT_FIELD_GUIDE.md` §7 says a red gate is not automatically yours and must
be handed over with a measurement rather than left for the next agent to
rediscover.*

`py -3 code/1050_preflight.py` prints **44 colliding numbers against a ratchet
floor of 43 in `62_no_regression_check.py`**, so `code_duplicate_numbers` is red
and `62` will exit 1. The measurement:

```
code/1123_copper_river_attribution.py       7,211 bytes   2026-09-02 11:14
code/1111_probe_new_source_candidates.py   32,070 bytes   2026-09-02 11:15
```

Written a minute apart by two concurrent workstreams. **This is the exact
failure `1050_preflight.py claim` exists to make impossible** — `ls code/1111_*`
cannot stop it, because check-then-write is not atomic (§1). Both files predate
this pass; this pass claimed `1116` through `claim`, which allocates strictly
above the frontier, and `1116` collides with nothing.

**It is worse than an ordinary collision, because `1123` is a number tonight's
record cites by itself.** `docs/QUARANTINE_EXPOSURE_LOG_2026-09-02.md` §5 and
`docs/AGENT_FIELD_GUIDE.md` §3 both discuss *"`1123`"* meaning the Copper River
attribution; a reader who resolves that to the source probe reads the wrong
script. **A citation of "script 1123" is now ambiguous in the prose that was
written the same day it became ambiguous.**

Not this pass's to fix: renaming touches the citing prose and any `.bak_*_pre1111`
tag, and `62` is integrator-owned. Two routes, either of which clears the gate:
rename one file (preferring the one with no prose citations — the probe) and
update its citations, or have the integrator re-baseline **only** after the
rename, never instead of it. **Never re-baseline to clear this**: a gate stepped
around is a gate the next six sessions also step around.

## The propagation gate

`py -3 code/1116_ruling_propagation_2026_09_02.py verify` is green as of
2026-09-02 and exits 1 while any document in `docs/` or `review/` states one of
the 2026-09-02 superseded figures with nothing beside it. `derive` re-measures
them from the live files; `selftest` proves the scanner fires, that a marked
literal does not, and that an empty corpus reports **UNMEASURED** rather than
clean. Add to `SUPERSEDED` in that script when the next figure moves.
<!-- END RULING-PROPAGATION-1116 -->

<!-- BEGIN CORROBORATION-1118 -->
## Corroboration: what the family count exposed (workstream CORROBORATION, 2026-09-02)

Measured by `code/1118_corroboration_layer.py`; full account in
`docs/CORROBORATION_LAYER_2026-09-02.md`. Each item below is a defect in
another workstream's table, and **none of them was changed here.**

**1. `np_orgs.disposition = NATIVE_VERIFIED_STRICT` has ZERO voting evidence
families, and 214 of the 293 that can be checked are contradicted by the
organisation's own words.** The label is a name match over an IRS BMF row; the
IRS never asserts that an organisation is Native, so the determination is
`cedar_inference` and does not vote. `n_coders_agree` reads like five sources
and is four coders reading one BMF row. 4,296 np_orgs EINs have a local Form
990 narrative (`data/staging/np_mission/inclusion_basis.jsonl`), which is a
genuine second family: **68 corroborate, 226 are silent.**

**29 of the silent ones ALSO cross a state line** and should not publish before
an owner sees them — `KANSAS HUMANE SOCIETY OF WICHITA`, `WAMPANOAG COUNTRY
CLUB`, `UNITED HABESHA COMMUNITY OF WICHITA` (the Ethiopian and Eritrean
diaspora), `RANCHO LA LAGUNA` (charrería), `PASADENA ROSEBUD ACADEMY CHARTER
SCHOOL`, `CHICKASAW CIVIC THEATRE` (Chickasaw, **Alabama**, is a city). Listed
in full in `data/clean/cedar_corroboration_disagreements.csv`, verdict
`OWN_990_SILENT_AND_THE_LINK_CROSSES_A_STATE_LINE`. **Silence is not
refutation** — the miner scores *Tongass Tlingit Cultural Heritage Institute*
as `placename_only` — so these are a queue, not a correction.

**2. `nest_enterprises.n_distinct_sources = 438` is not 438 corroborations.**
At observation grain the same population reaches two evidence FAMILIES on 40
groups, rising to 141 of 1,615 once the FPDS declared-parent family from
`code/1102` is added. The gap is one filer's AS 45.55.139 report across several
fiscal years: three documents, one observer. A buyer can reasonably read 438 as
corroboration. It should ship beside an `n_independent_families` column.

**3. `deals_classified.Verification_Status` claims more than it cites.** Of 651
deals carrying two citations, **220 cite the SAME URL twice** (one live, one
Internet Archive snapshot of it) and 362 more are two paths on one host; 53
reach two different observers. **13 rows carry a label that unambiguously
claims independent corroboration and reach one evidence family**, including
five `Independent secondary corroborated`. The labels are not wrong to keep —
they should carry the measurement beside them.

**4. `gaming_facilities.operating_entity_cedar_uids` is not an operator
statement.** It equals `cedar_uid` on 786 of 787 rows: the tribe restated. And
`gaming_nigc_roster_link.csv` looks like 453 rows of federal corroboration of a
facility's tribe — the NIGC location map carries a name, an address and a
contact person and **no tribe**, so the tribe on those rows is Cedar's own. It
is refused for that predicate here and the refusal should be visible upstream.

**5. Nine of fourteen shipping datasets are wholly single-sourced**, and the
census separates the two reasons. The highest-value unbuilt pair is
**`lobbying`: LDA registrant filings × Form 990 Schedule C** — two regimes,
different definitions, different penalties, same spend, and both already on
disk (`data/staging/np_mission/schedule_c_lobbying.csv`, 553 filers already in
`np_orgs`).
**6. GATE `62` IS CRASHING, IT IS NOT THIS WORKSTREAM'S, AND ITS FAILURE LOOKED
LIKE A PASS.** `py -3 code/62_no_regression_check.py` raises
`NameError: name 'ROOT' is not defined` at line 1996 and never reaches its
summary. The module's root constant is `CEDAR`
(`code/62_no_regression_check.py:161`); `ROOT` is not defined anywhere in the
file. **One line: `ROOT` -> `CEDAR`.** This is NOT the `A5` instance above, which was at line 131/159 and is resolved; it is a SECOND, later occurrence of the same undefined name in a different function. The file's mtime is 2026-09-02 09:05:38
and this workstream never opened it — `62` is integrator-owned
(`docs/AGENT_FIELD_GUIDE.md` §2), so it is filed rather than fixed.

The branch only executes when a table drops out of the dist manifest, which is
why it can sit unnoticed: **the gate passes for as long as nothing is wrong,
and crashes exactly when it has something to report.** Worse, the crash was
first read here as a PASS, because the shell reported exit 0 while the
traceback sat in the output — the field guide's habit 4 arriving from a
direction it does not yet name. **Assert on the summary line, not on the exit
code alone, when running `62` through a wrapper.**
<!-- END CORROBORATION-1118 -->

<!-- BEGIN DEFECT-SWEEP-1115 -->
## The retroactive defect-class sweep, 2026-09-02 — 898 instances of 12 classes

`code/1115_defect_class_retro_sweep.py`. Report:
`docs/defect_class_retro_sweep.json`. Re-run:

    py -3 code/1115_defect_class_retro_sweep.py selftest   # 11 detectors, fixtures
    py -3 code/1115_defect_class_retro_sweep.py all        # code + data, ~5 min

Every defect class this project has named was found ONCE and fixed THERE.
Nobody asked whether it existed elsewhere. This is that question, asked once
for all of them, across **612 python files** and **363 tables / 10,548,870
rows** in `data/clean` + `data/spine`. **No data pass is sampled.** Every
detector has a synthetic positive and a synthetic negative in `selftest`;
`all` runs the selftest first and says so if it failed.

| class | instances | at risk | worst instance |
|---|---:|---|---|
| C1 capped read then a whole-file claim | 70 | 140,112 row caps | **`526_dataset_standard.py` — FIXED.** `scan(name, cap=20000)` on 1.2M-row tables, then `drop N always-empty column(s)` |
| C2 input glob matches own output | 9 | 10 outputs | `1108`, `516`, `860` |
| C3 unanchored substring as identity/policy | 83 | 83 sites | `1082` `if key in cname or cname in key` on bond obligors |
| C4 token/containment keying a dollar | 53 | **$1.34T gross** | `fac_tribal_single_audits` 2,864/6,780 rows (42.2%), $42.4B |
| C5 invariance proved, occurrence not | 39 | 39 writers | **`1111` — FIXED.** 38 conservation-only writers remain |
| C6 display column vs keying column | 57 | 55,525 rows split | **`prime_contracts`: one `cedar_uid` on two sovereigns, 17,280 rows** |
| C7 prose in a controlled vocabulary | 231 | 170,748 rows | `native_entity_lobbying_disclosures.filing_type_display`, 50 values |
| C8 a refusal cached as a completion | 6 | 7 sites | five `_robots_cache` dicts that store the failure |
| C9 absence printed as evidence of absence | 44 | 44 subprocesses | `subprocess.run` whose `.returncode` is never read |
| C12 duplicate marker name in one file | **0** | — | MEASURED zero. 3 cross-file reuses, none sharing a generator |
| C12b bare-number backup tag | **156** | 569 files on disk | **34 sites on a COLLIDING number — the 163 incident, still loaded** |
| C13 positional writers | 0 | — | delegated to `845`; enforced by `62` rule 17 |
| C14 sentinel string in a live column | 147 | 2,935,692 rows | **`prime_contracts.owner_as_of_transaction_cedar_uid = "UNKNOWN"` on 1,066,926 rows / $264.5B** |

**C10** (a decision written where the asker cannot see) and **C11** (a
present-tense map inverting a past event) have **no detector here and no
count**. They are not derivable from code shape or column shape, and a
counter that pretended otherwise would be this project's signature defect.
Recorded in the report under `not_mechanically_detectable`.

### The five that should move first

1. **`owner_as_of_transaction_cedar_uid = "UNKNOWN"` on 1,066,926 of
   1,217,768 prime rows, $264.5B.** `518` C4 already learned this on 47,877
   rows — *"a populated cell is not a resolved identity"*. The real figure is
   **22x** that. Any consumer counting non-blank as attached overstates
   ownership coverage from 12.4% to 100%.
2. **`cage_code = "NAN"` (the literal string) on 398,840 prime rows,
   $87.6B**, and `auditee_uei = "GSA_MIGRATION"` on 4,103 FAC rows carrying
   $62.0B expended. Both are identity columns; both join.
3. **One `cedar_uid` spans two sovereigns.** `CE-001C8-GH` carries
   `canonical_name = "Winnebago"` and appears against **both**
   `TRBF-WNNBGO-00` (17,259 rows) and `TRBF-HOCHNK-00` (21 rows, $101,977).
   Ho-Chunk Nation of Wisconsin and the Winnebago Tribe of Nebraska are
   different nations; *Ho-Chunk, Inc.* is Winnebago's enterprise. **The
   display column already says the likely-correct answer and the keying
   column disagrees with it.** Owner ruling: `review/OWNER_DECISION_QUEUE.md`
   item **DS-1**. Not touched.
4. **156 bare-number backup tags, 34 of them on a colliding number.** The
   field guide's §1 rule (`.bak_<date>_pre_<stem>`) has never been measured.
   `_pre163` alone has **13 files on disk** and 163 is two different scripts.
   A restore by that tag still cannot tell whose backup it is.
5. **38 writers still prove conservation without proving occurrence.** The
   `1111` shape. Each writes, compares a before-total to an after-total, and
   never gates on how many rows it changed.

### What this workstream changed, and what it did not

**Changed — two files, both the named canonical instance of their class:**

- `code/526_dataset_standard.py` — `scan(name, cap=20000)` → `cap=None`, full
  pass. The cap was a **default argument**, so no caller could see it, and the
  C11 rule recommended dropping "always-empty" columns on the strength of the
  first 20,000 rows. Sibling `518` had fixed the identical defect the same
  week (`SCAN_CAP = None  # Do not reinstate a head-N cap.`). Cost measured:
  a full pass over all 363 tables is 115 s. **Not run** — it writes punch
  lists, and its output is another agent's input.
- `code/1111_copper_river_attribution.py` — `verify` passed vacuously. Its
  whole success condition was `not bad and not anc`; if the `COPPER RIVER`
  filter ever stopped matching it printed `ok  0 Copper River rows` and
  exited 0. Now refuses below a floor of 1,000 targets. **Re-run against live
  data: `ok  4,272 Copper River rows, 0 not on the hub`, exit 0.**

**Not changed, and handed on with an owner:**

- the 5 `_robots_cache` refusal caches (`142`, `553`, `980`, `991`,
  `1020`) — changing crawl behaviour is the crawl owners' call.
- the 44 unchecked subprocesses and 83 containment sites — each needs its own
  script's author to say whether the test is load-bearing.
- `62` was **not** touched. It is integrator-owned. Making this sweep
  permanent means a rule 18 beside rule 17; the proposal is in the ADR.

### Three defects this detector had, in itself

Recorded because the mandate predicted them and because the next person to
extend the file will reproduce them.

1. **C2 matched on the BASENAME and ignored the directory**, so
   `data/raw/*_freshness.csv` and `data/clean/*_freshness.csv` were the same
   pattern — the containment defect inside the containment detector. Caught
   by its own synthetic negative, which is the only reason it was caught.
2. **C12 returned 0 for a whole run** because a patch tool wrote a literal
   **backspace byte** into its regex. Zero looked exactly like clean. It now
   has a fixture, and it emits UNMEASURED when it finds no markers at all.
3. **C5 read `ast.unparse` output with a regex.** `unparse` renders
   `not bad and not anc` as `not bad and (not anc)`; the parentheses made the
   pattern miss and the detector reported zero findings while looking like it
   had run. Rewritten on the AST. It then found the `1111` instance by name.

Also: `detect_C13` was **defined and never called**, and mis-unpacked 845's
2-tuple return. Both fixed. A detector that is never invoked reports nothing
and nothing says so.
<!-- END DEFECT-SWEEP-1115 -->

<!-- BEGIN LADDER-1117-1122 -->
## `62_no_regression_check.py` DOES NOT RUN — `NameError: ROOT` — and it is not the caller's

Measured 2026-09-02 while checking the gates after `code/1117` and `code/1122`:

```
py -3 code/62_no_regression_check.py
  File "code/62_no_regression_check.py", line 1996, in main
    _live = (ROOT / "data" / "clean" / f).exists()
NameError: name 'ROOT' is not defined
```

`ROOT` is **never bound in that file** — `grep -n '^ROOT' code/62_no_regression_check.py`
returns nothing; the module uses `CLEAN` and `BASELINE` (lines 168–170). The line
was added by commit **`f274b01`** ("The punch list was telling agents to delete
columns that hold 838,229 values") inside the SHIPPING-LOST message that was
rewritten that day to say which surface lost the table. `git status --porcelain
code/62_no_regression_check.py` is empty, so the breakage is committed, not a
working-tree edit. **The project's main gate has been dark since that commit.**

The integrator owns `62` (`docs/AGENT_FIELD_GUIDE.md` §2), so it is left
unpatched here. The fix is one line: `CLEAN / f` in place of
`ROOT / "data" / "clean" / f`, or bind `ROOT = CLEAN.parent.parent`.

**A dark gate is worse than a red one**, and it is the field guide's own habit 4
in a new place: the gate produced *no* number and every caller since has read
that as nothing-to-report.

## `tier_A_ruled` FALLS 1,676 → 1,669, deliberately, and here are the seven

`tier_A_ruled` is in `MUST_NOT_FALL` and the baseline records **1,676**.
`code/1122_ladder_repoints.py` takes it to **1,669**. The fall is seven rows,
every one of them a tier-A row keyed to the WRONG SOVEREIGN, and each is
itemised in `review/ladder_repoints_2026-09-02.csv`:

| identifier | filed name | was (tier A) | now (tier B) |
|---|---|---|---|
| UEI `HLTFBD3FTDG8` | Confederated Tribes Of Warm Springs Reservation Of Oregon | Fort Sill-Chiricahua-Warm Springs-Apache (OK), `hand` | Warm Springs Tribe (OR) |
| UEI `LWRAHAFNKQ13` | Flandreau Santee Sioux Tribe | Santee Sioux (NE), `hand` | Flandreau (SD) |
| CAGE `50WN1` | Flandreau Santee Sioux Tribe | Santee Sioux (NE), `bgov_manual` | Flandreau (SD) |
| CAGE `4AD60` | Flandreau Santee Sioux Tribe | `canonical_name` already said Flandreau while `tribe_id` said `TRBF-SANTSX-00` — the row disagreed with itself | Flandreau (SD) |
| CAGE `3XGD7` | Sac & Fox Nation Of Missouri In Kansas And Nebraska | Sac and Fox Nation (OK), `bgov_manual` | Sac & Fox of Missouri (KS) |
| CAGE `3VFL3` | Ho-Chunk Nation | Winnebago Tribe of Nebraska, `bgov_manual` | Ho-Chunk (WI) |
| CAGE `4XH62` | Chignik Lagoon, Native Village Of | Yavapai-Apache Nation (AZ), `bgov_manual` | Chignik Lagoon (AK) |

**It was not re-baselined and it must not be.** `ENTITY_MATCH_RULES` rule 8
forbids an agent minting tier A, so a repoint an agent makes lands at tier B
even when it corrects an owner-graded row. The metric is doing its job: it is
reporting that seven owner-graded assertions were withdrawn. The way back to
1,676 is the owner confirming the seven — which is exactly what
`OWNER_DECISION_QUEUE` **EL-1** asks — not a new floor.

`prime_entities` moves the other way, 498 → **526** distinct `cedar_uid` in
`prime_contracts.csv`. Neither number is gate-verified, because the gate does
not run.
<!-- END LADDER-1117-1122 -->

<!-- BEGIN CAPABILITY-1114 -->
## `elyshoshonetribe.com` is recorded as refusing this agent and, measured 2026-09-02, does not

*Found by `code/1114_capability_statement_harvest.py`. Full account:
`docs/CAPABILITY_STATEMENT_HARVEST_2026-09-02.md` §2.*

`review/tribal_vendor_list_registry_2026-08-26.csv` records `ROBOTS_DISALLOW`
for Ely Shoshone, quoting *"robots.txt explicitly names and disallows
'ClaudeBot', 'anthropic-ai', 'GPTBot', 'Amazonbot' and others"*.
`review/1020_named_agent_robots_exposure.csv` rows 40-41 carry it forward, and
shard N purged the host's bodies on it.

The live file is the Squarespace template and is **one group**: thirty
`User-agent:` lines — `AI2Bot` … `ClaudeBot` … `AdsBot-Google-Mobile-Apps`,
then `User-agent: *` — followed by a single shared block of **27 path-scoped
`Disallow` directives**. **There is no `Disallow: /` in the file for any agent.**
`ClaudeBot` is subject to exactly the wildcard's rules.

**Being named in a `User-agent:` list is not being disallowed.** This is the
mirror of the defect the coverage audit caught in itself, where
`"Disallow" in robots_note` fired on the string `no Disallow directives`: there
a *string* match manufactured 106 refusals, here a *name* match manufactured
one. A false refusal is the more expensive direction, because it leaves no
artefact to trip over — it reads as a completed decision.

**Bounded claim:** as of 2026-09-02 the file does not disallow us. It may have
changed since 2026-08-26 and nothing on this machine can prove it did not.
`www.penobscotnation.org`, checked the same minute by the same parser, **does**
carry `Disallow: /` for `ClaudeBot` and is correctly still refused — which is
the evidence the parser reads groups rather than strings.

**Not acted on.** Nothing was harvested from Ely Shoshone beyond robots.txt and
the home page. Raised in `review/OWNER_DECISION_QUEUE.md` for a ruling.

## Two hazards this project has written down, in a form the written version misses

- **"Ask robots as every name that means you" needs its second half: and no
  name that does not.** `CCBot` (Common Crawl) sat in this script's agent-token
  tuple for its first 47 hosts and recorded four false refusals. Three of the
  four turned out to name `ClaudeBot` genuinely; `wildhorseresort.com` did not
  and was recovered. An over-broad refusal is invisible because it fails safe.
- **A URL fragment is not a document.** `verify` V7 fired on the live run:
  `www.tyonek.com` returned the same md5 **eleven** times because
  `/capabilities`, `/capabilities/`, `/capabilities#manufacturing` and eight
  more were treated as separate objects — the `?wpdmdl=` shape reached by a
  different road. Purged (187 rows, 76 findings), not waived. Defrag at
  candidate time.
<!-- END CAPABILITY-1114 -->

<!-- BEGIN FWD-CONSTRUCTION-2026-09-02 -->
## Open after the 2026-09-02 forward-construction pass

**1. FY2022 subawards are still 89 countable rows / $47,021,525, and it is the
only empty year left.** `fy2022_q1..q4` had never been submitted; all four were
submitted at 16:47Z and are generating server-side, one at a time, tokens
checkpointed in
`data/raw/subcontracts/usaspending_2026-08-12/_state.json`. **If the poller
died, nothing is lost — resume with `py -3 code/121_pull_subawards_api.py
collect`, then `match` → `append` → `910 rescan` → `910 apply` → `911 apply`
→ `871` → `1085 apply` → `81` → `1109 index` → `1109 apply`.** Never
re-submit an accepted token (rule 5).

**2. `1109 verify`'s INV-SGEO-1 is UNMEASURED, not passing.** The only
`.bak_*_pre_1109_*` on disk was the 76,859-row vintage from before two fold-ins,
so it was moved aside rather than used as a comparand that would report the
day's work as a breach. The conservation figures for the 16:58Z run are the ones
the apply measured during the write (89,809 → 89,809, $57,020,557,710.47
unchanged). The next `1109 apply` will take a correct snapshot automatically.

**3. `docs/datasets/_PUNCHLIST_CLAIM_AUDIT.md` reports `product_or_service_code`,
`product_or_service_code_description`, `award_base_description` and
`naics_description` at 247,987 non-blank.** All four are now 827,858–840,754.
It is GENERATED — re-derive with `py -3 code/1107_punchlist_claim_verify.py`,
do not hand-edit.

**4. `62_no_regression_check.py` will exit 1 on `code_duplicate_numbers`.**
`1050_preflight.py` measured **44** colliding script numbers against a ratchet
floor of 43 at 15:34Z. Not this pass's — no new number was claimed here; the
work ran through existing scripts. Named so the next agent does not inherit it
as an unowned red gate.

**5. The FAADS 112-column re-pull is feasible, not run, and needs an owner
ruling.** 1,943,994 rows can be keyed; the state is `NOT_ACQUIRED`, not
`SOURCE_DOES_NOT_PUBLISH`. See
`docs/FAADS_TRANSACTION_KEY_SETTLEMENT_2026-09-02.md`, closing section.
<!-- END FWD-CONSTRUCTION-2026-09-02 -->

<!-- BEGIN ESCAPE-COLLAPSE-1125 -->
## ~~OPEN~~ **RESOLVED 2026-09-02** — the collapsed-escape defect is not confined to `846`. SEVEN more live scripts carry it, and one of them is the identity normaliser

> **RESOLVED 2026-09-02 by `code/1136_control_byte_gate.py`.** All 41 bytes in
> all 7 files are repaired, every site was compared broken-vs-repaired on the
> live data before the repair landed, and a standing gate now exits 1 if any
> control byte reappears in source. **The resolution, with the measurements, is
> the `ESCAPE-COLLAPSE-1136-RESOLUTION` block immediately below this one.**
> Everything in this entry is kept because it is the reasoning; only the
> "STILL OPEN" status is dead.

*Found 2026-09-02 by `code/1126_annual_total_federal_and_gaming.py`, which
tried to IMPORT the gated gaming denominator instead of retyping it and got
771 instead of 714. **The `846` half of this was found and repaired
independently the same evening by workstream PLACE-IDS — see
the `PLACE-IDS-1129` block below, which owns that repair.** What is new
here is that `846` is not special: a tree-wide scan finds the same corruption
in seven other scripts, and it is a defect CLASS, not a typo.*

### The shape, once, because both entries describe it

A word-boundary escape reached the file as a literal **backspace byte, 0x08**,
sitting where `\b` belongs. A raw string cannot produce that byte, so something
between the author and the file interpreted the escape. The pattern then
matches no string that can exist — and it does not raise. It silently matches
**less**, and every count downstream of it looks like a clean measurement.

In `846::_denom` that meant the facility-name normaliser never stripped
`CASINO` / `GAMING`, all 771 grouping keys came out unique, and the ladder
reported **771 distinct properties** instead of 714. It failed loudly only
because `_denom` compares `(rows, placeholders, extra)` against
`(787, 16, 57)` and appends *"shape changed, re-derive before quoting"* — so it
refused to stand behind its own figure rather than publishing a sixth
denominator into a session where five were already circulating.
**Repaired; `_denom()` now returns `787 - 16 = 771 - 57 = 714` with its shape
test green, and a full `846` run is 25/27 with the two remaining failures
unrelated (`attribution_method` off-vocabulary from `ladder_1122`; `845 verify`).**

### ~~STILL OPEN~~ REPAIRED 2026-09-02 — seven files, 41 bytes, ~~16~~ **15** lines

*Re-measured by `1136`: the 41-byte count reproduces exactly; the line count is
**15**, not 16, and the file count is **7**, not 8 — the eighth was `846`,
already repaired by PLACE-IDS before this sweep ran, and its nine bytes are not
among the 41. Stated as measured, per the rule that a prior summary is not
evidence.*

Deliberately not repaired here: each one changes another workstream's matching
behaviour, and that is an owner or integrator call rather than a passing
agent's.

| file | bytes | lines | what the dead pattern is for |
|---|---:|---|---|
| `code/561_shard_k_alaska_villages.py` | 18 | 557–560 | the site-hijack marker list (`situs`, `judi`, `togel`, `bandar`, …) — **a spam-detection screen that currently detects nothing** |
| `code/1104_nagpra_affiliation_rule_audit.py` | 8 | 363–364 | the `FURNITURE` filter (`email`, `telephone`, `fax`, `nagpra coordinator`) |
| `code/1089_fr_consultation_overlap_and_event_parse.py` | 6 | 254–255, 334–336 | the contact-line detector and the street-suffix detector |
| `code/142_build_property_site_observations.py` | 3 | 1024–1025 | the bound-phrase prefix (`more than`, `over`, `nearly`) and a year matcher |
| `code/1080_sec_gaming_facility_revenue.py` | 2 | 275 | a fiscal-range phrase matcher |
| `code/76_build_recognition_history.py` | 2 | 836 | the `legislation` term in the recognition-instrument classifier |
| `code/503_identity.py` | 1, **plus one 0x01** | 95 | `FT MC DOWELL -> MCDOWELL`. **Both the word boundary and the `\1` backreference collapsed** — 0x08 in the pattern, 0x01 in the replacement — so the normaliser is inert, and if it ever did match it would write a control byte into a name |

**`503_identity.py` is the one to look at first.** It is an identity
normaliser, and an identity normaliser that silently stops normalising is how
two spellings of one entity become two entities. It is also the only instance
where the *replacement* is corrupted as well as the pattern, so the failure
mode is not merely "matches nothing" — it is "would emit a control byte".

### Reproduce — cheap, and it needs no backslash of its own

```
py -3 -c "import os;print([(os.path.join(r,f), open(os.path.join(r,f),'rb').read().count(bytes([8]))) for r,d,fs in os.walk('code') if '__pycache__' not in r for f in fs if f.endswith('.py') and '.bak' not in f and open(os.path.join(r,f),'rb').read().count(bytes([8]))])"
```

### The data side, adjacent and NOT the same defect

The same scan over `data/clean/*.csv` finds **483 control bytes in 7 tables** —
`ca_gaming_payments.csv` (118 × 0x02 and 118 × 0x03),
`section_106_consultation_events.csv` (192 NUL bytes across 87 lines),
`subawards.csv`, `compact_structured_terms.csv`, `compact_required_reports.csv`,
`compact_terms.csv`, `gaming_property_self_published_claims.csv`. These are
almost certainly OCR and PDF-extraction artefacts rather than collapsed source
escapes, and they are recorded here only so the next scanner does not conflate
the two. A NUL byte in a shipped CSV is its own small problem.

### HOW THE DEFECT IS MANUFACTURED, which is the part worth keeping

**This environment collapses a doubled backslash on its way into a shell
heredoc.** A repair script authored as `replace(bytes([8]), b'\\b')` arrived on
disk as `b'\b'` — which Python reads back as 0x08 — so the "fix" replaced the
byte with itself, printed *"replaced 9 occurrences"*, and changed nothing.
**The same collapse ate the first draft of this very section, and a
line-continuation backslash in a Python source file being patched the same
way.** Three times in one session, in three different file types.

So: write the replacement as `bytes([0x5C, 0x62])`, or write the file with an
editor rather than a heredoc, and **assert the remaining count is zero** rather
than trusting the success message. And treat any authoring path that passes
source text through a shell as a place where `\b`, `\1`, `\n` and `\t` can
silently become the bytes they name.
<!-- END ESCAPE-COLLAPSE-1125 -->
<!-- BEGIN ESCAPE-COLLAPSE-1136-RESOLUTION -->
## RESOLVED — all 41 collapsed escapes repaired, every one measured before and after, and gated (2026-09-02, `code/1136_control_byte_gate.py`)

*This block closes `ESCAPE-COLLAPSE-1125` above. That entry found the class and
declined to repair it, correctly, because each site changes another
workstream's matching behaviour. This block does the adjudication it was
waiting for.*

### The sweep was widened and the count is now measured, not inherited

`1125` swept for `0x08` only. `1136` sweeps `code/**/*.py`, `docs/**/*.md`, the
root `*.md` and `docs/schema/**/*.{json,txt}` — **975 files** — for every
control byte a regex escape can collapse into: `0x00`–`0x08`, `0x0b`, `0x0c`,
`0x0e`–`0x1f`, `0x7f`, excluding only tab, newline and CR.

**41 bytes · 7 files · 15 lines.** Every one `0x08` but a single `0x01`.
**Widening the byte set found nothing new** — no `\v`, no `\f`, no `\a`, no
NUL, nothing outside the seven known files. **And no legitimate literal control
byte exists in scope**: no form-feed record splitter, no vertical-tab
delimiter, nothing in a data-parsing path. All 41 are defects, and each sits in
a regex literal where a word boundary is the only sensible reading.

`1125` said "41 bytes across 16 lines in 8 files". Bytes reproduce exactly;
lines and files do not. The eighth file was `846_session_audit.py`, whose nine
bytes PLACE-IDS had already repaired and which are not among the 41.

### DID THE BEHAVIOUR CHANGE WHEN IT BROKE? Per site, on the live data.

Every site was run in both forms against the corpus the script actually reads —
not a fixture, and using each script's own machinery where it has any.

| site | corpus | result |
|---|---|---|
| `503_identity.py:95` | 18,506 names: spine, register, `entity_aliases.csv`, 9,098 distinct `recipient_name` | **7 distinct names normalise differently** |
| `1080…:275` `PAT_B1` | 609 SEC filings via 1080's own `totext`/`flat`/alias alternation | **6 → 28 matches** |
| `1089…:254-5,334-6` | 2,313 FR texts through the real `parse_notice()` | **7 documents move**, all place lists; 0 date lists |
| `1104…:363-4` | 51,579 `nagpra_notice_entity_bridge.csv` rows | **1 → 5 furniture rows** |
| `142…:1024-5` | 1,749 cached pages / 2,519 candidates through real `has_counting_cue()` | **0 verdicts change** |
| `76…:836` | 366 shipped `federal_recognition_events.csv` rows through real `classify_mechanism()` | **0 labels change**, 6 bases improve |
| `561…:557-60` | 689 cached shard-K pages | **0 → 0** on cache; 14 of 18 markers were dead |

**`503_identity.py` — the one to worry about, and it is worse than "inert".**
The line was `re.sub(r"<0x08>MC ([A-Z])", r"MC<0x01>", s)`: the boundary AND the
`\1` backreference collapsed. It is the only site where the **replacement** is
corrupt, so the failure mode was not merely "matches nothing" but "would emit a
control byte into an entity name". Measured: across 18,506 names the broken
form emitted a control byte **0 times**, because it never matched — the 0x01
was latent, not live. No name in Cedar carries a control byte from this.

What it cost is the fold. Repaired, `FT MC DOWELL YAVAPAI NATION` and
`FORT MCDOWELL YAVAPAI NATION` produce one key for the first time, and the
distinctive-token subset test — `resolve()`'s last resort — flips:

```
"MC GRATH NATIVE VILLAGE COUNCIL"
   broken {GRATH, MC}   vs  AKNF-MCGRTH-00-DOYONL-TNNACH {MCGRATH}  ->  no match
   fixed  {MCGRATH}     vs  AKNF-MCGRTH-00-DOYONL-TNNACH {MCGRATH}  ->  MATCH
"FT MC DOWELL YAVAPAI NATION"
   broken {DOWELL, FORT, MC, YAVAPAI}  vs TRBF-FMCDWL-00 {FORT, MCDOWELL} -> no
   fixed  {FORT, MCDOWELL, YAVAPAI}    vs TRBF-FMCDWL-00 {FORT, MCDOWELL} -> MATCH
```

**Fort McDowell is already attributed** (470 rows, $94,394,514.94,
`attribution_status = cedar_neid`) — the repair only tightens the normaliser
there. **McGrath is not: 151 rows / $11,358,100.32 of federal assistance sit
`unattributed`**, and neither loose-path guard (G1 admin-geography, G2 civic
form) refuses the name. **This is a PROPOSAL, not an applied attribution.** A
link that keys a dollar is a ruling and `503` is a library, not a writer; it is
in `review/collapsed_escape_flagged_rows_2026-09-02.csv` for the owner.

**`1089` — a guard that has never once fired, and 7 shipped rows to show for
it.** `STREET_TOKEN` is `<0x08>(Avenue|Ave|Street|…)<0x08>`, which matches
nothing, so the refusal its own docstring describes — *"2401 M Street, NW,
Washington, DC yields the phantom `NW, Washington`"* — was a no-op from the day
it was written. Seven `consultation_events.csv` rows carry the result, and
`location_basis` shows **four were written by 1089 itself**:

```
CONS-FR-2014-03720  'M Street NW., Washington'                 -> no place
CONS-FR-2016-10525  'E Street SW., Washington'                 -> no place
CONS-FR-2012-5438   drops 'West Dunlap Avenue Phoenix, AZ'
CONS-FR-2017-12494  drops 'Port Puget Sound Zone, WA'
CONS-FR-00-27437 / 2011-18096 / 2019-17786  (basis blank -> written by 96)
```

**The repair does not self-heal them**: `1089` fills `location` only when blank,
so a re-run leaves all seven unchanged. Flagged, not deleted, no `cedar_uid`
touched. MAIL_TO's two bytes change no `parse_notice` output at all.

**`1104` — the audit could not see the thing it was auditing.** The `FURNITURE`
filter goes 1 → 5 rows and the D1 check now FIRES: document `01-8989` keys
*"NAGPRA coordinator for the Walker River Paiute Tribe of the Walker River
Reservation, Nevada"* to `TRBF-WLKRRV-00`, tier C, `resolve_method =
containment`. The source comment two lines above the broken regex says *"every
one of them is unresolved, so none carries a tribe_id"* — **that sentence is
false, and it is false because the detector was blind.** Flagged for a ruling.

**`1080` — 22 per-facility revenue figures the pattern could not see.** The
optional tail `(?:.{0,170}?\bto\b)?` is what reads *"declined by $11.0 million,
or 1.0%, TO $1,069 million for the fiscal year ended September 30, 2018"*. With
a collapsed boundary the group never matched, so `PAT_B1` saw only the
`totaled $X` form. Repaired: **6 → 28 matches**, the 22 new ones being **Mohegan
Sun (11) and Mohegan Sun Pocono (10)** plus one MGE Niagara, FY2018–FY2021,
$5,756,300,000 read as printed — *a sum ACROSS fiscal periods, not a total; see
`MONEY_TOTALLING_RULES.md`*. **Nothing shipped moves on its own**: `mine` writes
candidates and `build` refuses without an adjudication row, and
`sec_gaming_financial_disclosures.csv` holds **0** `B_MDNA_*` rows today. So
this is 22 new candidates awaiting adjudication, not a silent correction — but
it is worth noting that the two largest tribal gaming properties in the country
were the ones the dead byte hid.

**`142`, `76`, `561` move nothing measurable today** and were repaired anyway.
`142`'s `QUALIFIER_HEAD` is redundant with `CUE_WORDS`, which already holds
`over`/`than`/`nearly`/`about`/`up`, and `DATE_NEAR`'s surviving `m/d/y` branch
catches every date in its 14-character window. `76`'s six changed rows are the
Virginia tribes of `2018-15679`, whose `mechanism` stays `act_of_congress` while
`mechanism_basis` improves from `matched_in_surrounding_text:Recognition Act` to
`matched_in_quote:legislation` — strictly better, and exactly what
`classify_mechanism`'s docstring argues for. `561`'s screen finds no hijacked
page in the 689-page cache either way, but 14 of its 18 markers were dead, and
its value is in the next live fetch, not in the cache.

### The gate

```
py -3 code/1136_control_byte_gate.py report     # inventory, rendered like cat -A
py -3 code/1136_control_byte_gate.py apply      # repair the adjudicated manifest
py -3 code/1136_control_byte_gate.py verify     # EXIT 1 if any byte reappears
py -3 code/1136_control_byte_gate.py selftest   # 7 fixtures prove it FIRES
py -3 code/1136_control_byte_gate.py flag       # rewrite the flagged register
```

`apply` refuses any file whose byte census is not exactly what the manifest
expects — a changed census means the file moved and the adjudication above no
longer describes it. It backs up to
`.bak_2026-09-02_pre_1136_control_byte_gate`, writes `.part`-then-rename, and
**asserts zero remaining bytes** rather than trusting its own report. That
assert is the step the earlier repair skipped, which is why it printed
*"replaced 9 occurrences"* and changed nothing. A byte that genuinely belongs
goes in `ALLOWLIST` with a stated purpose and an exact count; nothing qualifies
today.

Every replacement is built as `bytes([0x5C, 0x62])` / `bytes([0x5C, 0x31])`, and
`1136` contains no backslash-escape literal of its own, so no authoring path
through a shell can eat it.

**Wired in two places, both of which run every session:**

- **`293_lint_bug_classes.py` gained `class9`** — *"a collapsed regex escape — a
  literal control byte where `\b` or a backreference belongs"* — **consumed**
  from `1136.scan()` and never re-derived there, the same contract `class7` has
  with `284`. `293 --selftest` runs 1136's seven fixtures. Class 9 is the one
  class `ast` cannot detect: once the module parses, the byte is just a
  character inside a string constant.
- **`846_session_audit.py`** carries it as a **CRITICAL** claim. 846 is where
  this began — nine of these bytes in its own source blinded `_denom` into
  printing "771 distinct properties" against a true 714.

**Current state: `1136 verify` PASS over 975 files, `293` class9 = 0,
`293 --selftest` all green including class9, all seven repaired files compile.**

### Flagged, not deleted

`review/collapsed_escape_flagged_rows_2026-09-02.csv` — 8 rows. The 7
`consultation_events.csv` locations the repaired `STREET_TOKEN` refuses (with
`written_by` naming 1089 or 96 from `location_basis`), and the 1
`nagpra_notice_entity_bridge.csv` row the repaired `FURNITURE` filter reaches.
No row edited. No `cedar_uid` touched. Regenerate with `1136 flag`.

### The rule, recorded in `AGENTS.md`

*A regex literal is the one place in this codebase where a defect is invisible
in a terminal.* `cat -A` or a byte inspection is required before believing a
suspiciously clean zero.
<!-- END ESCAPE-COLLAPSE-1136-RESOLUTION -->


<!-- BEGIN PLACE-IDS-1129 -->
## PLACE IDS (ADR-030, `code/1129_place_ids.py`) — 2026-09-02

**FIXED THIS PASS, and both were load-bearing.**

**1. `846_session_audit.py` carried NINE 0x08 BACKSPACE BYTES where `\b` was
intended, and one of them blinded the gate for the gaming denominator.**
`_denom`'s `loose()` read `\x08(CASINO|RESORT|HOTEL|...)\x08` — a pattern that
matches no string that can exist — so the generic facility vocabulary was never
stripped, every facility name stayed distinct, the check found **0 duplicate
groups** and printed *"771 distinct properties — shape changed, re-derive before
quoting"*. Two other checks were blinded identically: `\bearns\b` /
`\bawarded?\b.*\blodge\b` in the business-name detector, and
`(Tourism|Recreation|Archaeology|Archeology)\b` in the NAGPRA tail detector.
The nine bytes are in the **committed** blob, so this is not a working-tree
accident. **Repaired 2026-09-02: 9 bytes, `0x08` -> `\b`. `_denom` now PASSES at
787 - 16 - 57 = 714.** Word-boundary and unbounded forms were compared on the
live file and give identical results, so the repair changes no adjudication.

*The general lesson, and it is new: a regex literal is the one place in this
repo where a defect is INVISIBLE IN A TERMINAL.* `cat`, `Read` and most editors
render `0x08` as nothing or as a cursor move, so the source reads exactly as
intended while matching nothing. **When a detector reports a suspiciously clean
zero, run `cat -A` on its pattern before you believe it.**

**2. Three wholesale writers would have deleted `cedar_place_id` on their next
rebuild** — `1080_sec_gaming_facility_revenue.py` (`FIG_COLS`, `TERM_COLS`) and
`92_build_gaming_capacity_official.py` (`COLS`), all three flagged NEW by
`845_regenerate_guard.py` the moment the migration landed. Fixed with the repair
`845` prescribes and recognises structurally: `carry_live_columns(path,
canonical)`. `845 verify` is green — 3 unsafe writers, 0 new since baseline.

**OPEN, and deliberately so.**

- **5 duplicate groups are HELD OPEN, not merged**, in
  `review/place_gaming_adjudication_2026-09-02.csv`. Two are **operator
  contradictions** that a duplicate sweep may not settle: `7 Clans First
  Council` is filed to the Ponca Tribe (`VP-0170`) and the Otoe-Missouria
  (`CCP-843900`) at one address; `The Stables` is filed to the Modoc Nation
  (`VP-0153`) and the Miami Tribe of Oklahoma (`CCP-305300`) and is in fact
  jointly owned. Three are groups where **the vendor itself minted two property
  ids** (Cities of Gold casino/hotel, Glacier Peaks casino/hotel, and Three
  Rivers Coos Bay vs Florence — 67 km apart). Each needs an owner ruling, not
  another pass of the same name test.
- **The adjudicated gaming count is 717; `846::_denom` measures 714.** Both are
  right about what they measure and **neither is re-baselined**: 714 is the
  mechanical name-collision count, 717 is the adjudication, and the difference
  is exactly the three vendor-distinguished groups above.
  `1129 verify` V9 recomputes the reconciliation from the live file on every run.
- **`IHS_FACILITY` is a declared place class with ZERO rows.** There is no IHS
  facility directory on this machine; it is NOT_ACQUIRED. `verify` prints it as
  UNPOPULATED and does not count it as a pass.
- **`cedar_places.csv` is not yet claimed by a collection**, so `512` does not
  see it as shippable. Its grain IS declared (`GRAIN_PLACE`). Registering it is
  an integrator decision.
- **EVENTS pass the ID test and `Deal_ID` is source-scoped in exactly the way
  `facility_id` was** — 15 channel prefixes across 1,073 rows. The recommendation
  is to GENERALISE `Deal_ID` into a `CEDAR-EVENT` id rather than mint beside it.
  Owner decision; see ADR-030 and `review/OWNER_DECISION_QUEUE.md`.
<!-- END PLACE-IDS-1129 -->

---

<!-- BEGIN LEDGER-STATE-1134 -->
# LS · The `state` column of the identifier ledger held the row's own UEI — and did so UPSTREAM of its own fix

*2026-09-02, `code/1134_repair_ledger_state_uei_contamination.py`. FIXED.
Recorded here for the two general lessons, not for the repair.*

**The defect.** `data/spine/cedar_identifier_ledger.csv`, 12,127 of 19,232
rows (63%), `state` = that row's own 12-character UEI. All 12,127 are
`identifier_type = UEI` from `master_tribal_entity_registry.csv`.
`data/clean/cedar_publishable_identifiers.csv` — **1,577 rows, every one tier A
and publishable** — had 699 more, and its remaining 878 held unnormalised full
state names, so **not one row of the most customer-facing copy of the ledger
carried a usable state**.

## Lesson 1 — A FIX APPLIED DOWNSTREAM OF THE DEFECT LOOKS LIKE A FIX FOREVER

`71_fix_known_defects.py` defect 5 found this and cleaned
`cedar_identifier_ledger_tiered.csv` and `cedar_identifier_ledger_final.csv`.
It never touched `data/spine/cedar_identifier_ledger.csv`, the file both are
BUILT FROM. So the defect sat upstream of its own repair: every shipped copy
measured clean, the source measured 63% corrupt, and a rerun of
`03_apply_exclusions_and_tier.py` would have pushed all 12,127 straight back
in. It also missed `cedar_publishable_identifiers.csv` entirely, which 03
writes from the same rows in the same pass.

**Rule: when you repair a derived table, name the table it derives from in the
same commit, and check it.** A green check on the output of a pipeline says
nothing about the input.

## Lesson 2 — SWEEP THE CLASS, NOT THE INSTANCE

The brief named one table. `62`'s new rule-18 check looks at **every** CSV in
`data/spine/` and `data/clean/` carrying both an `identifier` and a `state`
column — 5 tables — and that is the only reason
`cedar_publishable_identifiers.csv` was found. A check written against the
three tables somebody already knew about would have passed.

## Lesson 3 — "COLUMN SHIFT" WAS THE WRONG DIAGNOSIS, AND THE RIGHT ONE IS WORSE

Recorded in `review/OWNER_DECISION_QUEUE.md` (`OWNER-V6-NEST-2026-09-02`) as a
column shift travelling in from the owner's enterprise dataset. **The shift
width is zero** — measured against v6 across all 26 columns on 11,392 matched
rows, and against the raw 12-column registry, where exactly one column ever
equals the row's own UEI. The cause is
`sam_extracts/build_master_entity_registry.py:126`, a pandas `agg` whose
missing-column fallback substitutes `awardee_uei` for
`recipient_location_state_code`. A shift is a parser bug you fix once; a silent
column substitution produces a full column of plausible values and recurs on
the next renamed column. Corrected in the queue under `LS-1`; the original
block is left standing as written (flag, never delete).

## Lesson 4 — BLANKING IS NOT REPAIRING, AND `verify` MUST KNOW THE DIFFERENCE

71 replaced each rejected value with `""`. Safe, and lossy: the owner's v6 held
the true state for **12,019 of 14,923** blank rows in the tiered ledger and
**12,026 of 16,250** in the final one. A shipped column reading "unknown" where
the authority says "VA" is the first defect wearing different clothes.

1134's `verify` therefore asserts a POSITIVE — every row v6 can speak to must
carry v6's answer — and its `selftest` runs that check against a synthetic
table in three states: contaminated (FAILS), **blanked but unrepaired (FAILS)**,
repaired (passes). A conservation proof that nothing broke is not a proof that
something happened.

## What stands, and what was deliberately not done

- **48 multi-state strings and 3 junk values were LEFT ALONE**, not blanked.
  Blanking deletes evidence with no recovery behind it.
- **184 spine rows and 2 publishable rows are BLANK** because v6 has no state
  for those UEIs. Blank is the honest answer; nothing was inferred.
- **The $8.21B withheld-attribution hypothesis is FALSE.** 0 of the 15,878
  `ledger_uei_state_disagreement_withheld` rows in
  `federal_funding_transactions.csv` were withheld against a corrupted state —
  `115_pull_assistance_archive.py:892` reads `cedar_entity_spine.csv`, whose
  `state` is clean on all 1,555 rows. Full working in the queue under `LS-1`.

## The guard

- `01_build_entity_spine.py` already ran `clean_state` on the registry leg;
  `LEDGER_REFRESH = ()` means `merge_table` cannot overwrite a repaired cell.
  Dry run after the repair: 19,232 -> 19,358 rows, **0 refreshed, 0 blanks
  filled**, 0 lost. The repair survives a rebuild.
- `03_apply_exclusions_and_tier.py` had NO guard and is the only route from the
  spine ledger into both clean tables. One added, and **proved**: 500
  contaminated rows injected into a copy of the spine ledger, 03 run against
  it, **0 reached either output**.
- `62_no_regression_check.py` rule 18,
  `ledger_state_holds_own_identifier`, is in `MUST_BE_ZERO`.
<!-- END LEDGER-STATE-1134 -->
