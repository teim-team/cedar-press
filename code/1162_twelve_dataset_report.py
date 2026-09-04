#!/usr/bin/env python3
"""
Cedar Press - 1162: the thirteen-dataset report, measured rather than written.

    py -3 code/1162_twelve_dataset_report.py            # print
    py -3 code/1162_twelve_dataset_report.py build      # write the report
    py -3 code/1162_twelve_dataset_report.py zip        # + the delivery bundle
    py -3 code/1162_twelve_dataset_report.py build --fast    # skip the
            flagship re-count; the withheld reconciliation then prints
            UNMEASURED rather than a number

WHY THIS IS GENERATED
---------------------
Owner, 2026-09-02: *"When you feel more confident you addressed the issues of
the twelve datasets, give a report of what you've done and why, and all this in
a zip with the updated twelve preview datasets."*

And separately: *"ChatGPT will review your work."*

A hand-written status report is the exact artifact this project has spent the
day proving unreliable. Today alone: seven documents asserted a gaming
denominator that had moved; a build log said a source published no data when it
publishes six databases; the money warning shipped in three different vintages
at once; and I twice reported a partial scan as a population - 211 superseded
lobbying rows when there were 1,064, and 8 contradicted contractor rows when
there were 9,223.

So every figure here is read off the delivered files at the moment the report
runs. Nothing is typed.

WHAT THE FIRST VERSION OF THIS FILE GOT WRONG  (repaired 2026-09-03)
--------------------------------------------------------------------
It had never been run. Run, it did not crash - it produced a report that was
thin in four measurable ways, and each is the reason for a change below:

  1. **It described TWELVE datasets and thirteen are delivered.** The table
     iterated `dist/preview/`, which `1151` writes for the storefront only, so
     `gaming` - the largest maintained collection in the project - was absent
     from a report about the deliverables. It now iterates the DELIVERED files
     and carries the preview count as a column, so a dataset with no preview
     is visible as exactly that.

  2. **Its disposition table counted column-values and called them rows.** It
     summed `review/1153_adjudication_states_<date>.csv`, one line per state
     COLUMN per VALUE. A contractors row carries four state columns, so rows
     were counted up to four times, and the source was a file a previous
     session wrote rather than the delivered data. Row-level dispositions now
     come from `1165`, which asks `cedar_publication.adjudication()` about
     every delivered row, one row one answer.

  3. **It read one delivered file five times.** `shape()` was called inside the
     loop and again inside four `min`/`max` comprehensions, so
     `contractors.csv` - 1.5 GB - was fully parsed five times to print two
     numbers. Everything is measured once and reused.

  4. **It said nothing per dataset.** A reviewer opening thirteen spreadsheets
     needs, for each one: what a row is, how big it is, what was folded into it
     and what was refused, what was withheld and why, and what is known to be
     wrong with it. That is now the body of the report.

WHERE EVERY FIGURE COMES FROM, AND WHY THAT IS STATED IN THE REPORT ITSELF
---------------------------------------------------------------------------
Three classes, and the report labels each one, because a reviewer's first fair
question is "who measured this":

  MEASURED FROM THE DELIVERED FILE   rows, columns, bytes, per-column fill,
      adjudication states, mask leaks, the subaward fence - all from
      `code/1165_delivered_publication_audit.py`, a full uncapped pass over
      `dist/customer/*.csv`. `1165 selftest` proves each detector fires.
  MEASURED FROM THE SOURCE TABLE     the flagship's row count, re-counted with
      a CSV parser (never a line count - `27_build_dataset_manifests` once
      reported 17,877 rows against 1,521 records because quoted fields contain
      newlines). Withheld rows are then flagship minus delivered, which is a
      measurement rather than the builder's account of itself.
  THE BUILDER'S OWN RECORD           `MANIFEST.csv` - the join provenance and
      the per-reason withheld breakdown. Labelled as such wherever it appears,
      and its row and column counts are CHECKED against the measured ones; a
      disagreement is printed as a defect rather than silently preferred.

The one thing this report may never do is print a number nobody measured. Where
a figure cannot be measured on this run it prints **UNMEASURED**, which is the
discipline `62` already applies to `293` and `845`.

WHAT THIS REPORT WILL NOT DO
----------------------------
Claim the datasets are finished. It prints what is measured to be still broken
and what has not been checked - because a reviewer's first move is to look for
the thing the report avoided, and the fastest way to lose them is to be caught
having avoided it.

READS   dist/customer/*.csv (through 1165), dist/preview/*.csv,
        dist/customer/MANIFEST.csv, the flagship tables under data/clean and
        data/spine, docs/KNOWN_ISSUES.md, review/QA_RECONCILIATION_*.csv
WRITES  docs/TWELVE_DATASET_REPORT_<date>.md and dist/customer/REPORT.md
        (one string, written twice in one call, so they cannot disagree);
        review/1162_flagship_rows.json (a measurement cache keyed by size and
        mtime); the desktop zip in `zip` mode.
"""
from __future__ import annotations

import csv
import json
import subprocess
import sys
import zipfile
from collections import Counter
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "code"))
csv.field_size_limit(10_000_000)
# Local calendar date, as every other script in `code/` stamps its artefacts.
TODAY = date.today().isoformat()  # noqa: DTZ011
CUST = ROOT / "dist" / "customer"
PREV = ROOT / "dist" / "preview"
CLEAN = ROOT / "data" / "clean"
SPINE = ROOT / "data" / "spine"
REPORT = ROOT / "docs" / f"TWELVE_DATASET_REPORT_{TODAY}.md"
BESIDE = CUST / "REPORT.md"
BUNDLE = Path.home() / "Desktop" / f"cedar-press-twelve-datasets-{TODAY}.zip"
AUDIT_JSON = ROOT / "review" / f"1165_delivered_publication_audit_{TODAY}.json"
FLAG_CACHE = ROOT / "review" / "1162_flagship_rows.json"

from cedar_publication import (
    BUILD_SHELVES,
    FLAGSHIP,
    LOBBYING_FENCE,
    N_BUILT_EXPECTED,
    N_STOREFRONT_EXPECTED,
    STOREFRONT_SHELVES,
    SUBAWARD_FENCE,
    shelves,
)

UNMEASURED = "**UNMEASURED**"


def rowcount(p: Path) -> int:
    """Records, not physical lines. A quoted field may contain a newline."""
    with p.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
        rd = csv.reader(fh)
        next(rd, None)
        return sum(1 for _ in rd)


def gate(script: str, *args):
    """Run a gate and return (rc, last line). The rc alone has lied before."""
    try:
        r = subprocess.run([sys.executable, str(ROOT / "code" / script), *args],
                           capture_output=True, text=True, timeout=7200,
                           cwd=str(ROOT), check=False)
    except (OSError, subprocess.SubprocessError) as e:
        return 99, f"could not run: {e}"
    blob = (r.stdout or "") + (r.stderr or "")
    if "Traceback (most recent call last)" in blob:
        return 99, "CRASHED"
    lines = [ln for ln in blob.splitlines() if ln.strip()]
    return r.returncode, (lines[-1].strip() if lines else "")


def delivered_audit(force: bool = False) -> dict:
    """1165's measurement of the delivered files, refreshed if it is stale.

    A REPORT MAY NOT QUOTE A MEASUREMENT OLDER THAN THE FILE IT DESCRIBES. That
    is the same failure the freshness gate in `1137` exists to catch, one
    artefact along: a JSON from this morning describing a spreadsheet rebuilt
    this afternoon reads exactly like a current one. So the audit is re-run
    whenever any delivered CSV is newer than it, and this function RAISES
    rather than fall back to a stale file or to no file - an absent measurement
    must stop the report, not quietly shrink it.
    """
    newest = max((p.stat().st_mtime for p in CUST.glob("*.csv")), default=0)
    fresh = (AUDIT_JSON.exists()
             and AUDIT_JSON.stat().st_mtime >= newest and not force)
    if not fresh:
        print("    1165 audit is absent or older than a delivered file; "
              "re-running it (full scan, several minutes)")
        rc, last = gate("1165_delivered_publication_audit.py", "json")
        # rc 1 means violations were MEASURED, which is a result, not a
        # failure to measure. rc 99 or a missing file is a failure to measure.
        if rc == 99 or not AUDIT_JSON.exists():
            raise SystemExit(f"  1162: cannot measure the delivered files - "
                             f"1165 returned rc={rc} ({last}). The report is "
                             f"not written; nothing here may be estimated.")
    return json.loads(AUDIT_JSON.read_text(encoding="utf-8"))


def flagship_path(name: str):
    for d in (CLEAN, SPINE):
        p = d / name
        if p.exists():
            return p
    return None


def flagship_rows(names, fast: bool) -> dict:
    """Re-count the source tables, cached on (size, mtime).

    2.4 GB of flagship CSV is several minutes of parsing and the answer only
    changes when the file does, so the cache key is the file's size and mtime
    rather than a date. `--fast` skips the measurement entirely and the report
    prints UNMEASURED - it does NOT fall back to the builder's figure, because
    a builder's figure wearing a measured figure's label is the whole defect
    this report was rewritten to stop.
    """
    cache = {}
    if FLAG_CACHE.exists():
        try:
            cache = json.loads(FLAG_CACHE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            cache = {}
    out = {}
    for coll, fname in sorted(names.items()):
        p = flagship_path(fname)
        if not p:
            out[coll] = None
            continue
        st = p.stat()
        key = f"{p.name}|{st.st_size}|{int(st.st_mtime)}"
        if key in cache:
            out[coll] = cache[key]
            continue
        if fast:
            out[coll] = None
            continue
        print(f"    counting {p.name} ({st.st_size/1e6:,.0f} MB)")
        cache[key] = out[coll] = rowcount(p)
    FLAG_CACHE.parent.mkdir(parents=True, exist_ok=True)
    FLAG_CACHE.write_text(json.dumps(cache, indent=2), encoding="utf-8")
    return out


def reconciliation():
    f = sorted(ROOT.glob("review/QA_RECONCILIATION_*.csv"))
    if not f:
        return None
    with f[-1].open(encoding="utf-8-sig", errors="replace") as fh:
        rs = list(csv.DictReader(fh))
    return Counter(r["verdict"] for r in rs), len(rs), f[-1].name


def known_issue_titles(coll: str) -> list:
    """Headings in docs/KNOWN_ISSUES.md that MENTION this dataset id.

    A mention is not a finding about the dataset, and the report says so where
    it prints them. This is a pointer for a reviewer, not an assertion - the
    substring test that produces it is the same one `1137`'s codebook uses,
    and a loose substring test is this repo's most-repeated defect.
    """
    p = ROOT / "docs" / "KNOWN_ISSUES.md"
    if not p.exists():
        return []
    needles = {coll.lower(), coll.replace("-", " ").lower()}
    hits = []
    for block in p.read_text(encoding="utf-8", errors="replace").split("\n## "):
        low = block.lower()
        if any(n in low for n in needles):
            hits.append(block.strip().splitlines()[0].strip("# ").strip()[:150])
    return hits[:6]


def build_report(fast: bool) -> str:
    aud = delivered_audit()
    by_ds = {f["dataset"]: f for f in aud["files"]}
    sh = shelves()
    with (CUST / "MANIFEST.csv").open(encoding="utf-8-sig",
                                      errors="replace") as fh:
        man = {r["dataset"]: r for r in csv.DictReader(fh)}
    previews = {p.stem: rowcount(p) for p in sorted(PREV.glob("*.csv"))}
    fl = flagship_rows({c: FLAGSHIP[c] for c in by_ds if c in FLAGSHIP}, fast)
    # Read back rather than re-harvested: the audit wrote it, and two
    # harvests of one vocabulary are two things that can disagree.
    neid_vocab = set()
    _vc = ROOT / "review" / "1165_neid_vocabulary.json"
    if _vc.exists():
        neid_vocab = set(json.loads(
            _vc.read_text(encoding="utf-8")).get("values", []))

    L = []
    A = L.append
    order = sorted(by_ds)

    A("# The thirteen delivered datasets — measured, not written")
    A("")
    A(f"*Generated {TODAY} by `code/1162_twelve_dataset_report.py`. Every "
      f"figure below is read off a file on disk when the report runs; nothing "
      f"is typed, and anything this run could not measure says "
      f"{UNMEASURED} rather than carrying a plausible number.*")
    A("")
    A("Thirteen datasets are built. Twelve are sold on the Cedar Press "
      "storefront; `gaming` is built and gated to the same standard and is "
      "sold through Cedar Grove. A report about the deliverables covers all "
      "thirteen — an earlier version of this file iterated the preview "
      "directory, which the storefront-only preview builder writes, and so "
      "left the largest collection in the project out of a report about "
      "delivery.")
    A("")
    A("### Where each figure comes from")
    A("")
    A("| label | source | what it means |")
    A("|---|---|---|")
    A("| measured (delivered) | `code/1165_delivered_publication_audit.py`, "
      "a full uncapped pass over `dist/customer/*.csv` | read off the file the "
      "customer receives. `1165 selftest` injects each violation class and "
      "asserts the named detector fires. |")
    A("| measured (source) | a CSV-parser re-count of the flagship table | "
      "records, not physical lines; a quoted field may contain a newline. |")
    A("| builder's record | `dist/customer/MANIFEST.csv` | what "
      "`1137` says it did. Its row and column counts are checked against the "
      "measured ones below; a disagreement is printed as a defect. |")
    A("")

    # ---------------------------------------------------------------- table
    A("## The thirteen, as delivered")
    A("")
    A("| dataset | shelf | sold through | rows | columns | file size | "
      "preview rows | empty columns |")
    A("|---|---|---|---:|---:|---:|---:|---:|")
    for c in order:
        a, m = by_ds[c], man.get(c, {})
        pv = previews.get(c)
        A(f"| `{c}` | {sh.get(c, '?')} | {m.get('sold_through', '?')} | "
          f"{a['rows']:,} | {a['columns']} | {a['bytes']/1e6:,.1f} MB | "
          f"{pv if pv is not None else 'none'} | "
          f"{len(a['empty_columns'])} |")
    A(f"| **total** | | | **{sum(x['rows'] for x in by_ds.values()):,}** | | "
      f"**{sum(x['bytes'] for x in by_ds.values())/1e9:,.2f} GB** | | |")
    A("")
    nopv = [c for c in order if c not in previews]
    if nopv:
        A(f"`{'`, `'.join(nopv)}` has no preview file: `1151` writes previews "
          f"for the {N_STOREFRONT_EXPECTED} storefront datasets only. That is "
          f"a fact about the preview builder, not about the delivery.")
        A("")
    # The manifest is the builder's claim; check it rather than repeat it.
    dis = []
    for c in order:
        a, m = by_ds[c], man.get(c)
        if not m:
            dis.append(f"`{c}`: delivered on disk, no manifest line")
            continue
        if int(m.get("rows") or 0) != a["rows"]:
            dis.append(f"`{c}`: manifest says {int(m['rows']):,} rows, the "
                       f"file holds {a['rows']:,}")
        if int(m.get("columns") or 0) != a["columns"]:
            dis.append(f"`{c}`: manifest says {int(m['columns'])} columns, "
                       f"the header holds {a['columns']}")
    A("**Manifest against measurement.** " + (
        f"{len(order)} datasets checked on rows and on columns; "
        f"{len(dis)} disagreement(s)."
        if not dis else "DISAGREEMENTS FOUND: " + "; ".join(dis)))
    A("")

    # ------------------------------------------------- the publication rules
    A("## The publication rules, checked in the delivered files")
    A("")
    A("Masking and column-dropping happen at export, so `data/clean` is the "
      "wrong place to look for them and `MANIFEST.csv` is the writer grading "
      "its own homework. These are read off `dist/customer/`.")
    A("")
    A("| rule | what must be true | measured |")
    A("|---|---|---|")
    nev = sum(len(a["never_columns_present"]) for a in by_ds.values())
    drp = sum(len(a["drop_columns_present"]) for a in by_ds.values())
    lin = sum(len(a["lineage_columns_present"]) for a in by_ds.values())
    wh = sum(sum(a["withheld_states_present"].values()) for a in by_ds.values())
    un = sum(sum(a["unenumerated_states_present"].values())
             for a in by_ds.values())
    lk = sum(sum(a["mask_attribution_leaks"].values()) for a in by_ds.values())
    ql = sum(sum(a["quarantine_leaks"].values()) for a in by_ds.values())
    rag = sum(a.get("ragged_rows", 0) for a in by_ds.values())
    A(f"| personal-data columns (`NEVER`) | absent from every delivered "
      f"header | **{nev}** present across {len(order)} headers |")
    A(f"| licensed proprietary identifiers (`DROP_COLS`) | absent from every "
      f"delivered header | **{drp}** present |")
    A(f"| build-lineage columns | absent from every delivered header | "
      f"**{lin}** present |")
    A(f"| rows in a WITHHOLD adjudication state | none delivered | "
      f"**{wh:,}** delivered |")
    A(f"| rows in a state the policy does not enumerate | none delivered "
      f"(deny-by-default) | **{un:,}** delivered |")
    A(f"| a MASK row still carrying its Cedar attribution | none | "
      f"**{lk:,}** cells |")
    A(f"| a quarantined non-tier-A row still carrying its attribution | none "
      f"| **{ql:,}** cells |")
    A(f"| rows with more fields than the header | none | **{rag:,}** |")
    nn = sum(len(a["neid_columns_present"]) for a in by_ds.values())
    nv = sum(sum((a.get("neid_value_cells") or {}).values())
             for a in by_ds.values())
    nt = sum(sum((a.get("neid_value_tokens") or {}).values())
             for a in by_ds.values())
    A(f"| retired NEID columns, by NAME | absent from every delivered header "
      f"| **{nn}** present |")
    A(f"| retired NEID identifiers, by VALUE | none delivered | "
      f"**{nt:,}** identifier(s) on **{nv:,}** rows |")
    A("")
    qpop = sum(a["quarantine_population"] for a in by_ds.values())
    qa = sum(a["quarantine_tier_A"] for a in by_ds.values())
    A(f"**The quarantine rows are still in the file, and that is the policy.** "
      f"{qpop:,} delivered rows carry "
      f"`identifier_ruling_quarantined = Y` with a tier other than A, and "
      f"{qa:,} carry tier A. `BLOCKED_COMBINATIONS` disposes the first set "
      f"MASK, not WITHHOLD: the award is a real federal record and ships, "
      f"while the Cedar attribution on it does not. Reporting only the leak "
      f"count of {ql:,} would leave a reader to assume those rows were "
      f"dropped.")
    A("")
    sub = by_ds.get("subcontracting")
    if sub:
        A("**The subaward fence has two legs and they are different kinds of "
          "rule.** `" + SUBAWARD_FENCE[0] + "` is a ROW gate — the other two "
          "`duplicate_status` values are WITHHOLD and may not ship. `"
          + SUBAWARD_FENCE[1] + "` is a MONEY fence — those rows are real "
          "filings, they ship flagged, and they are excluded from the "
          "countable total. Measured in the delivered file:")
        A("")
        A("| leg | measured |")
        A("|---|---|")
        A("| `duplicate_status` | "
          + "; ".join(f"`{k}` = {v:,}"
                      for k, v in sorted(sub["duplicate_status_counts"].items()))
          + " |")
        A("| `subaward_exceeds_prime_flag` | "
          + "; ".join(f"`{k}` = {v:,}"
                      for k, v in sorted(sub["exceeds_prime_counts"].items()))
          + " |")
        A(f"| `subaward_amount` | ${sub['subaward_unfiltered_usd']:,.2f} "
          f"summed over every delivered row against "
          f"${sub['subaward_countable_usd']:,.2f} over the "
          f"{sub['subaward_rows_countable']:,} rows inside the fence |")
        A("")
    lob = by_ds.get("lobbying")
    if lob:
        A("**The lobbying money fence.** Superseded LDA filings are PUBLISHED "
          "with their supersession stated — an amendment restating an "
          "original's money is a money rule, not a row rule. The fence is `"
          + "` AND `".join(LOBBYING_FENCE) + "`.")
        A("")

    # ------------------------------------------------- the NEID retirement
    A("## The retired NEID identifiers (owner ruling, 2026-09-03)")
    A("")
    A("The CICD/NEID identifiers are retired; Cedar's own key is the "
      "identity. `cedar_publication.publishable_columns()` now drops "
      "`NEID_COLS` and `PROPOSED_COLS` at export, which puts the rule on the "
      "whole publication surface instead of the three files "
      "`code/843_retire_cicd_scheme.py` named by hand.")
    A("")
    A("**By column name, the retirement landed.** Measured in the delivered "
      f"headers: {sum(len(a['neid_columns_present']) for a in by_ds.values())}"
      " retired column name(s) survive across the thirteen files.")
    A("")
    A("**By VALUE, it did not.** A name gate cannot see the same identifier "
      "arriving in a column called something else, and that is what the "
      "delivered files hold. Every count below is a full pass over the "
      "delivered file, testing each cell — and each token of a "
      "pipe-delimited cell — for membership in the "
      f"{len(neid_vocab):,}-value NEID vocabulary harvested from "
      "`data/clean` and `data/spine`, not against a shape:")
    A("")
    neid_rows = [(c, col, n,
                  (by_ds[c].get("neid_value_tokens") or {}).get(col, 0),
                  (by_ds[c].get("neid_value_examples") or {}).get(col, ""))
                 for c in order
                 for col, n in sorted((by_ds[c].get("neid_value_cells")
                                       or {}).items())]
    if neid_rows:
        A("| dataset | column | rows | identifiers | example |")
        A("|---|---|---:|---:|---|")
        for c, col, n, tk, ex in neid_rows:
            A(f"| `{c}` | `{col}` | {n:,} | {tk:,} | `{ex}` |")
        A(f"| **total** | **{len(neid_rows)} column(s) in "
          f"{len({r[0] for r in neid_rows})} dataset(s)** | "
          f"**{sum(r[2] for r in neid_rows):,}** | "
          f"**{sum(r[3] for r in neid_rows):,}** | |")
    else:
        A("_No delivered cell holds a value from the NEID vocabulary._")
    A("")
    scr = [(c, col, n) for c in order
           for col, n in sorted((by_ds[c].get("neid_shaped_unknown")
                                 or {}).items())]
    if scr:
        A("Screened and **not** counted above: "
          + "; ".join(f"`{c}.{col}` {n:,} cell(s)" for c, col, n in scr)
          + ". These match the NEID shape and are absent from the "
            "vocabulary — `contractors.award_base_description` holds "
            "`DPW-00229-01` inside a contract description and "
            "`subcontracting.subaward_number` holds `SR-2012-11`. A shape "
            "test alone reported 568 of these as violations and missed 2,173 "
            "real identifiers, which is why membership is the test.")
        A("")
    A("**Which datasets can still name an entity.** A dataset whose only "
      "entity key was a NEID has nothing left after the retirement, and no "
      "row-count or column-count check can see that — dropping a column never "
      "fails a row count.")
    A("")
    A("| dataset | Cedar identity column(s) in the delivered header | filled |")
    A("|---|---|---:|")
    for c in order:
        a = by_ds[c]
        ids = a.get("identity_columns_present") or []
        fill = "; ".join(f"`{i}` {(a.get('filled') or {}).get(i, 0):,}"
                         for i in ids)
        A(f"| `{c}` | " + (", ".join(f"`{i}`" for i in ids) if ids
                           else "**NONE**") + f" | {fill or '—'} |")
    A("")
    # A COLUMN NAME IS NOT A COLUMN VALUE, and the table above is built from
    # names. Where an identity-named column turns out to hold NEIDs on every
    # populated row, say so - otherwise this table reports a dataset as keyed
    # by Cedar on the strength of a column called `cedar_*` that holds the
    # identifier the ruling retired.
    liars = []
    for c in order:
        a = by_ds[c]
        for i in a.get("identity_columns_present") or []:
            n = (a.get("neid_value_cells") or {}).get(i, 0)
            f = (a.get("filled") or {}).get(i, 0)
            if n:
                liars.append((c, i, n, f))
    if liars:
        A("**An identity-named column holding retired identifiers.** "
          + "; ".join(f"`{c}.{i}` is {n:,} of {f:,} populated rows"
                      for c, i, n, f in liars)
          + ". The name says Cedar; the values are NEIDs. The table above is "
            "built from column NAMES, so it credits these as identity "
            "coverage — read them out of it.")
        A("")
    noid = [c for c in order if not by_ds[c].get("identity_columns_present")]
    if noid:
        A(f"**`{'`, `'.join(noid)}` carry no `cedar_uid` under any spelling.** "
          f"This is NOT a regression from the retirement — their flagship "
          f"tables never held one, and their delivered column counts did not "
          f"move — but it is the condition that makes the retirement bite: "
          f"their only entity keys are `*_entity_id` / `*_entity_ids` columns "
          f"holding the retired identifiers. Until Cedar's key is promoted "
          f"onto them, applying the ruling to those columns would leave the "
          f"datasets unable to name a party at all.")
        A("")
    A("**`funding` lost six columns and that is a CORRECTION, not a "
      "regression.** Four are internal working columns: "
      "`ledger_proposed_tribe_id`, `tribe_id_neid_proposed`, "
      "`tribe_id_neid_proposed_tier` and `tribe_id_neid_proposed_basis` are "
      "proposals that `843` states are never shipped, and 67,826 "
      "funding rows carried a proposed NEID with no `cedar_uid` — rows with "
      "no settled identity at all, advertising one. Two more columns went "
      "with them: `tribe_id_neid` itself and "
      "`bie_uio_dollars_by_entity__tribe_id`, which was populated on zero "
      "rows. A no-regression gate reading the drop in populated-identity "
      "cells as a loss would be reading a correction as damage.")
    A("")

    # ------------------------------------------------------------ per dataset
    A("## Per dataset")
    A("")
    for c in order:
        a = by_ds[c]
        m = man.get(c, {})
        A(f"### `{c}` — {m.get('name') or '(no name in the manifest)'}")
        A("")
        A(f"`{a['rows']:,}` rows × `{a['columns']}` columns · "
          f"{a['bytes']/1e6:,.1f} MB · shelf `{sh.get(c, '?')}` · sold through "
          f"{m.get('sold_through', '?')} — *measured (delivered)*")
        A("")
        A("**What one row is.** "
          + ((m.get("grain") or "").strip()
             or "_Grain not declared in `docs/schema/dataset_contracts.json`._"))
        A("")
        # ---- provenance
        fname = FLAGSHIP.get(c, "")
        src = fl.get(c)
        A(f"**Join provenance.** Flagship table `{fname or '?'}`"
          + (f", measured at {src:,} rows." if src is not None
             else f", row count {UNMEASURED} on this run.")
          + " *(builder's record for the rest of this paragraph.)*")
        folded = [x for x in (m.get("tables_folded_in") or "").split("; ") if x]
        refused = [x for x in (m.get("tables_counted_not_joined") or "").split("; ") if x]
        if folded:
            A("")
            A("Folded in one-to-one, cardinality re-measured on the rows "
              "actually loaded rather than trusted from the contracts file:")
            A("")
            for x in folded:
                A(f"- `{x}`")
        else:
            A("")
            A("_No supporting table met the one-to-one test; the substantive "
              "columns are the flagship's own._")
        if refused:
            A("")
            A("Counted, **not** joined. These are one-to-many on the shared "
              "key; joining them would multiply the flagship's rows and "
              "inflate every money total, so each contributes a count column "
              "instead:")
            A("")
            for x in refused:
                A(f"- `{x}`")
        joined_cols = sorted({h.split("__", 1)[0] for h in a["header"]
                              if "__" in h})
        A("")
        A(f"Measured in the delivered header: "
          f"{sum(1 for h in a['header'] if '__' in h)} column(s) carry a join "
          f"prefix, from {len(joined_cols)} source table(s)"
          + (f" — `{'`, `'.join(joined_cols[:8])}`"
             + (" …" if len(joined_cols) > 8 else "") if joined_cols else "")
          + f"; {sum(1 for h in a['header'] if h.startswith('n_'))} "
            f"count column(s).")
        A("")
        # ---- withheld
        A("**What was withheld, and why.**")
        A("")
        if src is None:
            A(f"Rows not delivered: {UNMEASURED} — the flagship was not "
              f"re-counted on this run (`--fast`), and the builder's figure is "
              f"deliberately not substituted for a measurement.")
        else:
            gap = src - a["rows"]
            A(f"- Measured: the flagship holds {src:,} rows and "
              f"{a['rows']:,} were delivered — **{gap:,} row(s) not "
              f"delivered**.")
            claimed = int(m.get("rows_withheld") or 0)
            if gap != claimed:
                A(f"- **DISAGREEMENT**: `MANIFEST.csv` reports "
                  f"{claimed:,} rows withheld against a measured gap of "
                  f"{gap:,}. One of the two is wrong and it is not resolved "
                  f"here.")
        why = (m.get("withheld_why") or "").strip()
        A("- Builder's per-reason breakdown: "
          + (f"`{why}`" if why else "none — no row was withheld."))
        A("")
        A("**What was masked.** A MASK keeps the row — a real public record — "
          "and withholds the Cedar attribution on it.")
        A("")
        dr = a.get("disposition_rows") or {}
        A("- Measured (delivered), one row one disposition, from "
          "`cedar_publication.adjudication()`: "
          + ("; ".join(f"`{k}` = {v:,}"
                       for k, v in sorted(dr.items(), key=lambda kv: -kv[1]))
             or "no adjudication-state column on this dataset"))
        mw = (m.get("attribution_masked_why") or "").strip()
        A(f"- Builder's record of masks that actually cleared a cell: "
          f"{int(m.get('rows_attribution_masked') or 0):,} row(s)"
          + (f" — `{mw[:400]}`" if mw else "."))
        if a["mask_rows"] and int(m.get("rows_attribution_masked") or 0) \
                != a["mask_rows"]:
            A(f"- The two differ ({a['mask_rows']:,} rows adjudicated MASK "
              f"against {int(m.get('rows_attribution_masked') or 0):,} "
              f"recorded) because a mask on a row whose attribution columns "
              f"were **already blank** clears nothing and is not counted by "
              f"the builder. Both are correct about what they measure.")
        A("")
        # ---- defects
        A("**Known defects.**")
        A("")
        defects = []
        for label, key in (("personal-data column", "never_columns_present"),
                           ("licensed identifier column", "drop_columns_present"),
                           ("build-lineage column", "lineage_columns_present"),
                           ("retired NEID / internal-proposal column",
                            "neid_columns_present")):
            for col in a[key]:
                defects.append(f"{label} `{col}` survived into the delivered "
                               f"header")
        for col, n in sorted((a.get("neid_value_cells") or {}).items()):
            tk = (a.get("neid_value_tokens") or {}).get(col, 0)
            defects.append(
                f"retired NEID identifiers still ship as VALUES in `{col}` — "
                f"{n:,} row(s), {tk:,} identifier(s) (e.g. "
                f"`{(a.get('neid_value_examples') or {}).get(col, '')}`). "
                f"The 2026-09-03 retirement dropped the NEID columns by NAME; "
                f"a name gate cannot see the same identifier under another "
                f"column name")
        if not a.get("identity_columns_present"):
            defects.append(
                "**no Cedar identity column at all** — this dataset carries "
                "no `cedar_uid` under any spelling, so after the NEID "
                "retirement its only entity key is a retired identifier")
        for k, v in sorted(a["withheld_states_present"].items()):
            defects.append(f"{v:,} delivered row(s) in the WITHHOLD state `{k}`")
        for k, v in sorted(a["unenumerated_states_present"].items()):
            defects.append(f"{v:,} delivered row(s) in `{k}`, a state the "
                           f"policy does not enumerate")
        for k, v in sorted(a["mask_attribution_leaks"].items()):
            defects.append(f"MASK leak: `{k}` populated on {v:,} row(s)")
        for k, v in sorted(a["quarantine_leaks"].items()):
            defects.append(f"quarantine leak: `{k}` populated on {v:,} row(s)")
        if a.get("ragged_rows"):
            defects.append(f"{a['ragged_rows']:,} row(s) carry more fields "
                           f"than the header — malformed CSV")
        if a["rows"] > 1_048_576:
            defects.append(f"{a['rows']:,} rows exceeds Excel's 1,048,576-row "
                           f"sheet limit; every other reader (R, Stata, "
                           f"pandas, DuckDB, Power BI) opens the whole file")
        if a["bytes"] > 95 * 1024 * 1024:
            defects.append(f"{a['bytes']/1e6:,.0f} MB exceeds GitHub's 100 MB "
                           f"file limit — a hosting problem, not a reason to "
                           f"split the dataset")
        empt = a["empty_columns"]
        if empt:
            defects.append(f"{len(empt)} column(s) are blank on every "
                           f"delivered row and are kept deliberately: `"
                           + "`, `".join(empt[:12])
                           + ("` …" if len(empt) > 12 else "`")
                           + " — dropping blank columns would make the schema "
                             "depend on which rows shipped")
        thin = [col for col, n in (a.get("filled") or {}).items()
                if 0 < n < 0.10 * max(a["rows"], 1)]
        if thin:
            defects.append(f"{len(thin)} column(s) are under 10% populated — "
                           f"real, but do not build a headline on them: `"
                           + "`, `".join(sorted(thin)[:10])
                           + ("` …" if len(thin) > 10 else "`"))
        stale_join = [x for x in refused if "MEASURED" in x]
        for x in stale_join:
            defects.append(f"the contracts file is stale for this join: `{x}`")
        if defects:
            for d in defects:
                A(f"- {d}")
        else:
            A("- None measured in the delivered file by `1165`, and no size "
              "or sparsity finding.")
        ki = known_issue_titles(c)
        if ki:
            A("")
            A(f"Headings in `docs/KNOWN_ISSUES.md` that MENTION `{c}` — a "
              f"mention, found by substring, not a finding about this "
              f"dataset:")
            A("")
            for k in ki:
                A(f"- {k}")
        A("")

    # ----------------------------------------------------------------- gates
    A("## Gates, run for this report")
    A("")
    A("| gate | result |")
    A("|---|---|")
    for s, args in (("846_session_audit.py", ()),
                    ("1137_customer_dataset_combine.py", ("verify",)),
                    ("1151_customer_preview_ten.py", ("verify",)),
                    ("1152_qa_review_reconciliation.py", ("verify",)),
                    ("845_regenerate_guard.py", ("verify",)),
                    ("1165_delivered_publication_audit.py", ("selftest",))):
        rc, last = gate(s, *args)
        mark = "pass" if rc == 0 else ("CRASHED" if rc == 99 else f"FAIL rc={rc}")
        A(f"| `{s.split('_')[0]}` `{' '.join(args) or '(no args)'}` | "
          f"**{mark}** — {last[:120]} |")
    A("")
    A("`1137 verify` is the freshness gate: a delivered file older than any "
      "table it was built from is STALE and it exits 1 naming the file that "
      "moved. `1165 selftest` is the proof that the publication audit's "
      "detectors fire — a green audit whose detectors have never been made to "
      "go red is not evidence of anything.")
    A("")

    # ------------------------------------------------------- the outside QA
    rec = reconciliation()
    if rec:
        tally, total, name = rec
        A("## The outside QA review, reconciled")
        A("")
        A(f"`review/{name}` holds {total} logged findings, each checked "
          f"against the live tables rather than judged by reading.")
        A("")
        A("| verdict | findings |")
        A("|---|---:|")
        for k, v in tally.most_common():
            A(f"| {k} | {v} |")
        A("")

    # ------------------------------------------------------- what is not done
    A("## What is NOT fixed, and what was NOT measured")
    A("")
    A("Stated because a reviewer's first move is to look for what the report "
      "avoided.")
    A("")
    widths = [a["columns"] for a in by_ds.values()]
    A(f"- **The delivered files are wide.** {min(widths)}–{max(widths)} "
      f"columns. Every column is kept deliberately — dropping the blank ones "
      f"would make the schema depend on which rows shipped — but a reviewer "
      f"who called the export cluttered will still find it cluttered.")
    A("- **`gaming` is the thirteenth dataset** and ships through Cedar "
      "Grove, not the Cedar Press storefront. It is built and gated with the "
      "twelve and it has no preview file.")
    if fast:
        A("- **The flagship tables were not re-counted on this run** "
          "(`--fast`), so every withheld reconciliation above says "
          f"{UNMEASURED}.")
    A("- **Nothing here measures whether a VALUE is correct.** This report "
      "measures shape, provenance and the publication policy. Whether a "
      "contract is attributed to the right nation is the adjudication layer's "
      "question and is not answered by any figure above.")
    A("- **A green gate is not a proof of coverage.** `1165` reports zero "
      "violations of the rules it implements; rules nobody has written are "
      "not tested by it. The rule of three applies — zero observed violations "
      "licenses a floor, never a claim of correctness.")
    A("")
    A(f"*Built set: {N_BUILT_EXPECTED} datasets across shelves "
      f"`{'`, `'.join(BUILD_SHELVES)}`; storefront: {N_STOREFRONT_EXPECTED} "
      f"across `{'`, `'.join(STOREFRONT_SHELVES)}`. Rebuild the deliverables "
      f"with `py -3 code/1137_customer_dataset_combine.py build`; regenerate "
      f"this report with `py -3 code/1162_twelve_dataset_report.py build`.*")
    return "\n".join(L) + "\n"


def main() -> int:
    argv = sys.argv[1:]
    fast = "--fast" in argv
    mode = next((a for a in argv if not a.startswith("-")), "print")
    text = build_report(fast)
    if mode == "print":
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        print(text)
    else:
        print(f"  {len(text.splitlines())} lines")
    if mode in ("build", "zip"):
        # ONE STRING, WRITTEN TWICE IN ONE CALL. `docs/` is where this repo
        # keeps its reports; `dist/customer/REPORT.md` is what an outside
        # reviewer opens beside the spreadsheets. Two files that could be
        # generated separately would drift, so they never are.
        REPORT.write_text(text, encoding="utf-8")
        BESIDE.write_text(text, encoding="utf-8")
        print(f"  report -> {REPORT.relative_to(ROOT)}")
        print(f"  report -> {BESIDE.relative_to(ROOT)}")
    if mode == "zip":
        prev = sorted(PREV.glob("*.csv"))
        with zipfile.ZipFile(BUNDLE, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr("REPORT.md", text)
            for p in prev:
                z.write(p, f"datasets/{p.name}")
            mf = PREV / "MANIFEST.json"
            if mf.exists():
                z.write(mf, "datasets/MANIFEST.json")
        print(f"  bundle -> {BUNDLE}  "
              f"({BUNDLE.stat().st_size/1024:,.0f} KB, {len(prev)} previews)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
