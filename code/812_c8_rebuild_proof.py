#!/usr/bin/env python3
"""
Cedar Press - 812: PROVE the C8 rebuild path is non-destructive.

C8 is "ONE documented rebuild path reproduces the tables without destroying
later enrichment". It was the last blocker on `_entity_layer` and on `deals`,
and it is the one gate in this project that could be turned green by deleting
three dictionary entries - which is exactly why it needed a proof and not an
assertion.

WHAT THIS DOES
--------------
Runs each of the three formerly-destructive builders in `--dry-run`: the whole
computation, the whole merge, and NO WRITE. Then it checks the merge report
against the census `741_hub_grain_and_rebuild.py` measured off the backup
trail, and fails loudly on:

    rows_lost  != 0          a rebuild that deletes a row
    cols_lost  != []         a rebuild that deletes a column - the single most
                             repeated defect in this repo, having hit
                             admin_appeal_positions.csv, two gaming tables and
                             four Federal Register tables on 2026-08-31 alone
    spine rows  < 1,555      a partial restore wearing a green build log
    spine cols  < the 44 in docs/schema/hub_rebuild_census.json

THE RULE THAT GOVERNS THIS SCRIPT
---------------------------------
**It never runs a builder for real.** Every number below comes from a dry run
against the LIVE tables, which reads them and writes nothing. Seven
workstreams wrote to `data/clean` today; a spine rebuild mid-flight would be
unrecoverable, because `.gitignore` line 95 excludes `data/spine/*` apart from
`cedar_identity_register.csv` and `cedar_handle_history.csv`, so git cannot
put the spine back.

WHAT IT CANNOT PROVE, STATED HERE RATHER THAN OMITTED
-----------------------------------------------------
`docs/schema/hub_rebuild_census.json` lists two spine enrichers with NO
checkpoint - `08_build_review_page.py` and `115_pull_assistance_archive.py`.
Every other enricher takes a `cedar_entity_spine.csv.bak_<date>_pre<NN>`
before it writes, which is what let the genealogy be read off the trail at
all. These two leave no trace, so:

  * they contribute no stage to the census, and no column in the live spine is
    attributed to them;
  * a replay driven by `REPLAY_ORDERS` does not include them, and nothing can
    say from the evidence whether that is correct or a hole.

What this proof DOES establish about them is narrower and still worth having:
the merge is additive by construction, so if either of those two ever wrote a
column or a row into the spine, a rebuild through `01` PRESERVES it - the
check below compares against the live table, whatever put it there. The gap is
in the REPLAY story (can the hub be rebuilt from nothing?), not in the
NON-DESTRUCTION story (can it be rebuilt without loss?). C8 asks for the
second. The first remains partly unevidenced for two of seventeen stages and
should not be claimed.

Writes docs/schema/c8_rebuild_proof.json
"""

import contextlib
import importlib.util
import io
import json
import sys
from datetime import date
from pathlib import Path

CEDAR = Path(__file__).resolve().parent.parent
CODE = CEDAR / "code"
sys.path.insert(0, str(CODE))
import cedar_pipeline as CP  # noqa: E402

TODAY = date.today().isoformat()
CENSUS = CEDAR / "docs" / "schema" / "hub_rebuild_census.json"
OUT = CEDAR / "docs" / "schema" / "c8_rebuild_proof.json"


def load(script):
    spec = importlib.util.spec_from_file_location(
        "m" + script.split("_")[0], CODE / script)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def quiet(fn, *a, **k):
    """Run `fn`, swallowing its log. The builders are chatty and this script
    is about the verdict, not the narration - but the log is kept so a failure
    can print it."""
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        r = fn(*a, **k)
    return r, buf.getvalue()


def main():
    print("=== 812: C8 rebuild proof (DRY RUN - nothing is written by any "
          "builder) ===\n")
    census = json.loads(CENSUS.read_text(encoding="utf-8"))
    gate = census["rebuild_gate"]
    results = {}
    failures = []
    logs = {}

    # ---- 1. the guard state itself ---------------------------------------
    print("[1] Guard state")
    still_guarded = sorted(CP.NEVER_RUN)
    retired = sorted(getattr(CP, "RETIRED_FROM_NEVER_RUN", {}))
    print(f"  NEVER_RUN still holds  : {still_guarded}")
    print(f"  retired on 2026-09-01  : {retired}")
    if "41_build_codebooks.py" not in CP.NEVER_RUN:
        failures.append("41_build_codebooks.py left NEVER_RUN - it was never "
                        "fixed and it still deletes 21 of 43 codebook blocks")
    for s in ("01_build_entity_spine.py", "09_import_rulings.py",
              "88_build_deals_taxonomy.py"):
        if s in CP.NEVER_RUN:
            failures.append(f"{s} is still guarded; this proof is moot")
        if s not in getattr(CP, "RETIRED_FROM_NEVER_RUN", {}):
            failures.append(f"{s} came off NEVER_RUN with no recorded reason")

    # ---- 2. 01 - the spine ------------------------------------------------
    print("\n[2] 01_build_entity_spine.py --dry-run")
    m01 = load("01_build_entity_spine.py")
    reps, logs["01"] = quiet(m01.build, dry_run=True)
    for name, rep in reps.items():
        d = rep.as_dict()
        results[name] = d
        print(f"  {rep}")
        if rep.rows_lost:
            failures.append(f"{name}: {rep.rows_lost} rows lost")
        if rep.cols_lost:
            failures.append(f"{name}: columns lost {rep.cols_lost}")

    spine = results["cedar_entity_spine.csv"]
    need_cols = gate["required_columns"]
    missing = [c for c in need_cols if c not in spine["path"] and
               c not in reps["cedar_entity_spine.csv"].cols_after]
    print(f"\n  CENSUS GATE  >= {gate['min_rows']:,} rows and all "
          f"{len(need_cols)} columns")
    print(f"    rows after merge    : {spine['rows_after']:,}  "
          f"{'PASS' if spine['rows_after'] >= gate['min_rows'] else 'FAIL'}")
    print(f"    census columns held : {len(need_cols) - len(missing)}"
          f"/{len(need_cols)}  {'PASS' if not missing else 'FAIL'}")
    if spine["rows_after"] < gate["min_rows"]:
        failures.append(f"spine {spine['rows_after']:,} rows < census "
                        f"{gate['min_rows']:,}")
    if missing:
        failures.append(f"spine missing census columns: {missing}")

    # ---- 3. 09 - the ruling ledger ---------------------------------------
    print("\n[3] 09_import_rulings.py --dry-run")
    m09 = load("09_import_rulings.py")
    rep09, logs["09"] = quiet(m09.main, dry_run=True)
    for name, d in rep09.items():
        results[name] = d
        print(f"  {name}: {d['rows_before']:,} -> {d['rows_after']:,} rows "
              f"({d['rows_lost']} lost), {d['n_cols_before']} -> "
              f"{d['n_cols_after']} cols (lost {d['cols_lost'] or 'none'})")
        print(f"    tier-A owner adjudications: "
              f"{d['tierA_adjudications_before']} in, "
              f"{d['tierA_adjudications_after']} out")
        if d["rows_lost"]:
            failures.append(f"{name}: {d['rows_lost']} rows lost")
        if d["cols_lost"]:
            failures.append(f"{name}: columns lost {d['cols_lost']}")

    # ---- 4. 88 - deals ----------------------------------------------------
    print("\n[4] 88_build_deals_taxonomy.py --dry-run")
    m88 = load("88_build_deals_taxonomy.py")
    _, logs["88"] = quiet(m88.main, dry_run=True)
    # 88 reports through its own log; re-derive the report by re-merging in
    # memory would duplicate its rule tables, so parse the one line it prints.
    line = next((l for l in logs["88"].splitlines()
                 if l.strip().startswith("deals_classified.csv:")), "")
    print(f"  {line.strip() or 'NO MERGE LINE - 88 did not reach its write'}")
    if not line:
        failures.append("88 produced no merge report")
    elif "0 lost" not in line or "lost none" not in line:
        failures.append(f"88 merge report is not clean: {line.strip()}")
    results["deals_classified.csv"] = {"merge_report_line": line.strip()}

    # ---- 5. what the proof does NOT cover --------------------------------
    print("\n[5] Unevidenced enrichers - stated, not papered over")
    nocp = census.get("enrichers_with_no_checkpoint", [])
    for s in nocp:
        print(f"  {s}: no cedar_entity_spine.csv.bak checkpoint, so it "
              f"contributes no stage to the census and no column in the live "
              f"spine is attributed to it.")
    print("  Effect on THIS proof: none on non-destruction (the merge is "
          "additive and compares against the LIVE table, whatever wrote it), "
          "but the REPLAY-FROM-NOTHING story stays unevidenced for 2 of 17 "
          "stages and must not be claimed.")

    # ---- verdict ----------------------------------------------------------
    print("\n=== VERDICT ===")
    if failures:
        print(f"  C8 NOT PROVEN - {len(failures)} failure(s):")
        for f in failures:
            print(f"    - {f}")
    else:
        print("  C8 PROVEN. Every rebuilder reproduces its table with zero "
              "rows and zero columns lost, and the spine clears the census.")
    print("  No builder was run outside --dry-run. No file was written by "
          "any builder.")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({
        "generated": TODAY,
        "by": "812_c8_rebuild_proof.py (workstream C8)",
        "method": "each builder run with dry_run=True against the LIVE "
                  "tables: full computation, full merge, no write. Compared "
                  "to docs/schema/hub_rebuild_census.json.",
        "census_gate": gate,
        "never_run_remaining": still_guarded,
        "retired_from_never_run": retired,
        "tables": results,
        "enrichers_with_no_checkpoint": nocp,
        "unevidenced_caveat":
            "08_build_review_page.py and 115_pull_assistance_archive.py leave "
            "no spine checkpoint, so the replay-from-nothing sequence is "
            "unevidenced for 2 of 17 stages. Non-destruction is unaffected: "
            "the merge is additive and diffs against the live table.",
        "failures": failures,
        "passed": not failures,
    }, indent=2), encoding="utf-8")
    print(f"\n  wrote {OUT.relative_to(CEDAR)}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
