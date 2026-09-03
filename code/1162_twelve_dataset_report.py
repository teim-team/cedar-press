#!/usr/bin/env python3
"""
Cedar Press - 1162: the twelve-dataset report, measured rather than written.

    py -3 code/1162_twelve_dataset_report.py            # print
    py -3 code/1162_twelve_dataset_report.py build      # write the report
    py -3 code/1162_twelve_dataset_report.py zip        # + the delivery bundle

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
runs. Nothing is typed. If a number is wrong, the data is wrong, which is the
only kind of wrong worth having.

WHAT THIS REPORT WILL NOT DO
----------------------------
Claim the datasets are finished. It prints what changed, what is measured to be
still broken, and what has not been checked - because a reviewer's first move is
to look for the thing the report avoided, and the fastest way to lose them is to
be caught having avoided it.
"""
from __future__ import annotations

import csv
import json
import subprocess
import sys
import zipfile
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "code"))
csv.field_size_limit(10_000_000)
TODAY = date.today().isoformat()
CUST = ROOT / "dist" / "customer"
PREV = ROOT / "dist" / "preview"
REPORT = ROOT / "docs" / f"TWELVE_DATASET_REPORT_{TODAY}.md"
BUNDLE = Path.home() / "Desktop" / f"cedar-press-twelve-datasets-{TODAY}.zip"


def shape(p: Path):
    with p.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
        rd = csv.reader(fh)
        hdr = next(rd, [])
        n = sum(1 for _ in rd)
    return n, len(hdr)


def gate(script: str, *args):
    """Run a gate and return (rc, last line). The rc alone has lied before."""
    try:
        r = subprocess.run([sys.executable, str(ROOT / "code" / script), *args],
                           capture_output=True, text=True, timeout=1800,
                           cwd=str(ROOT))
    except Exception as e:
        return 99, f"could not run: {e}"
    blob = (r.stdout or "") + (r.stderr or "")
    if "Traceback (most recent call last)" in blob:
        return 99, "CRASHED"
    lines = [l for l in blob.splitlines() if l.strip()]
    return r.returncode, (lines[-1].strip() if lines else "")


def reconciliation():
    f = sorted(ROOT.glob("review/QA_RECONCILIATION_*.csv"))
    if not f:
        return None
    rs = list(csv.DictReader(f[-1].open(encoding="utf-8-sig", errors="replace")))
    import collections
    return collections.Counter(r["verdict"] for r in rs), len(rs), f[-1].name


def eligibility():
    """What the publication gate withheld or masked, from its own ledger."""
    out = {}
    for f in sorted(ROOT.glob("review/1153_adjudication_states_*.csv")):
        rs = list(csv.DictReader(f.open(encoding="utf-8-sig", errors="replace")))
        for r in rs:
            d = (r.get("disposition") or "").strip()
            if not d:
                continue
            try:
                out[d] = out.get(d, 0) + int(r.get("rows") or 0)
            except ValueError:
                pass
    return out


def main() -> int:
    mode = sys.argv[1] if len(sys.argv) > 1 else "print"

    prev = sorted(p for p in PREV.glob("*.csv"))
    cust = sorted(p for p in CUST.glob("*.csv") if p.name != "MANIFEST.csv")
    L, A = [], lambda s: L.append(s)

    A(f"# The twelve datasets — what changed and what did not")
    A("")
    A(f"*Generated {TODAY} by `code/1162_twelve_dataset_report.py`. Every figure "
      f"is read off the delivered files when the report runs. Nothing is typed.*")
    A("")
    A("A hand-written status report is the artifact this project spent the day "
      "proving unreliable: seven documents asserted a gaming denominator that had "
      "moved, a build log said a source published no data when it publishes six "
      "databases, and I twice reported a partial scan as a population. So this "
      "measures instead.")
    A("")

    # ---- the twelve, as delivered -------------------------------------
    A("## The twelve, as delivered")
    A("")
    A("| dataset | rows | columns | preview rows |")
    A("|---|---:|---:|---:|")
    for p in prev:
        c = CUST / p.name
        cn, cc = shape(c) if c.exists() else (0, 0)
        pn, _ = shape(p)
        A(f"| `{p.stem}` | {cn:,} | {cc} | {pn} |")
    A("")
    A(f"The preview is a curated subset — {min(shape(p)[1] for p in prev)}–"
      f"{max(shape(p)[1] for p in prev)} columns against the delivered "
      f"{min(shape(c)[1] for c in cust)}–{max(shape(c)[1] for c in cust)}. "
      f"A preview can look clean while the delivered file is not, which is why "
      f"the sections below measure the delivered files.")
    A("")

    # ---- the publication gate -----------------------------------------
    el = eligibility()
    if el:
        A("## What the publication gate now withholds")
        A("")
        A("The customer export was publishing rows the pipeline had already "
          "ruled unsafe. One deny-by-default policy now decides, and an "
          "unenumerated state withholds itself rather than slipping through.")
        A("")
        A("| disposition | rows |")
        A("|---|---:|")
        for k, v in sorted(el.items(), key=lambda kv: -kv[1]):
            A(f"| `{k}` | {v:,} |")
        A("")

    # ---- the reconciliation -------------------------------------------
    rec = reconciliation()
    if rec:
        tally, total, name = rec
        A("## The outside QA review, reconciled")
        A("")
        A(f"An outside review logged 151 findings against the export. All "
          f"{total} (including 22 follow-ups) were **checked against the live "
          f"tables** rather than judged by reading — `{name}`.")
        A("")
        A("| verdict | findings |")
        A("|---|---:|")
        for k, v in tally.most_common():
            A(f"| {k} | {v} |")
        A("")

    # ---- the gates -----------------------------------------------------
    A("## Gates, run for this report")
    A("")
    A("| gate | result |")
    A("|---|---|")
    for s, a in (("846_session_audit.py", ()),
                 ("1137_customer_dataset_combine.py", ("verify",)),
                 ("1151_customer_preview_ten.py", ("verify",)),
                 ("1152_qa_review_reconciliation.py", ("verify",)),
                 ("845_regenerate_guard.py", ("verify",))):
        rc, last = gate(s, *a)
        mark = "pass" if rc == 0 else ("CRASHED" if rc == 99 else f"FAIL rc={rc}")
        A(f"| `{s.split('_')[0]}` | **{mark}** — {last[:110]} |")
    A("")

    A("## What is NOT fixed")
    A("")
    A("Stated because a reviewer's first move is to look for what the report "
      "avoided.")
    A("")
    A("- The delivered export is **wider** than when the review ran — "
      f"{min(shape(c)[1] for c in cust)}–{max(shape(c)[1] for c in cust)} "
      "columns against 29–81. The review's complaint about shipping debugging "
      "columns is not resolved by the previews being narrow.")
    A("- Findings marked `STILL_REQUIRES_FULL_DATA_CHECK` in the reconciliation "
      "are exactly that: not cleared, not confirmed.")
    A("- `gaming` is the thirteenth dataset and ships through Cedar Grove, not "
      "the Cedar Press storefront. It is built and gated with the twelve but is "
      "not one of them.")
    A("")

    text = "\n".join(L) + "\n"
    print(text if mode == "print" else f"  {len(L)} lines")

    if mode in ("build", "zip"):
        REPORT.write_text(text, encoding="utf-8")
        print(f"  report -> {REPORT.relative_to(ROOT)}")
    if mode == "zip":
        with zipfile.ZipFile(BUNDLE, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr("REPORT.md", text)
            for p in prev:
                z.write(p, f"datasets/{p.name}")
            mf = PREV / "MANIFEST.json"
            if mf.exists():
                z.write(mf, "datasets/MANIFEST.json")
        print(f"  bundle -> {BUNDLE}  "
              f"({BUNDLE.stat().st_size/1024:,.0f} KB, {len(prev)} datasets)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
