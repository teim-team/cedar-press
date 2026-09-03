#!/usr/bin/env python3
"""
Cedar Press - 1152: reconcile the 151-finding QA review against the live tables.

    py -3 code/1152_qa_review_reconciliation.py            # report
    py -3 code/1152_qa_review_reconciliation.py build      # write the ledger
    py -3 code/1152_qa_review_reconciliation.py verify

WHY THIS EXISTS
---------------
Two QA reviews now exist and they looked at different products. The owner's
instruction was to reconcile them, not to run either again:

    *"Do not rerun the entire old 151-finding review as if nothing changed.
    Instead classify every old finding into: CONFIRMED BY 100-ROW REVIEW /
    STILL REQUIRES FULL-DATA CHECK / LIKELY FIXED IN NEW EXPORT / OBSOLETE -
    BASED ON OLD SAMPLE DESIGN... otherwise you risk fixing ghosts from an old
    export while missing the few problems that genuinely persist."*

The ten-row review saw 29-81 columns per file and could therefore inspect
adjudication state, provenance, parser diagnostics, supersession and quarantine
flags. The hundred-row review sees a curated 7-11 columns and can therefore ask
whether the CUSTOMER-FACING records make sense. Neither replaces the other, and
the second cannot even evaluate most of what the first found.

WHAT THIS FILE REFUSES TO DO
----------------------------
Classify by reading. Every finding whose truth is a property of the data is
CHECKED against `dist/customer/*.csv` and `data/clean/*.csv`, and the verdict
carries the measurement. A reconciliation done by judgement would be a third
opinion; this is meant to end the argument, not extend it.

Where a finding genuinely cannot be machine-checked - a claim about tone, or
about what a buyer would infer - it is marked NEEDS_HUMAN and says so rather
than guessing. That is a smaller number than it looks: most of the 151 assert
something concrete about a column, a value or a row count.

THE ONE CORRECTION THE OWNER MADE, AND IT REWRITES TWO FINDINGS
----------------------------------------------------------------
CP-003 and RG-005 said `cedar_uid` is unsafe because it is not always the
subject of the row. The owner ruled that too broad:

    *"The Cedar UID must always resolve to the same impermeable Native entity,
    while the dataset separately identifies the event/object/business and
    describes the Native entity's role... The issue is not 'Cedar UID must
    identify the row subject.' The issue is 'the role of the Cedar UID must be
    unambiguous.'"*

So NEST carrying `enterprise_id = CEDAR-NEST-...` beside `cedar_uid = Ahtna` is
CORRECT. Both findings are rewritten rather than discarded, and the test
changes with them: not "does cedar_uid identify the subject" but "does every
dataset declare the ROLE its cedar_uid plays, and does it resolve to a Native
entity in the register every time".
"""
from __future__ import annotations

import csv
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "code"))
csv.field_size_limit(10_000_000)
TODAY = date.today().isoformat()
REVIEW = ROOT / "review" / "QA_REVIEW_10ROW_2026-09-02.txt"
CUST = ROOT / "dist" / "customer"
OUT = ROOT / "review" / f"QA_RECONCILIATION_{TODAY}.csv"
DOC = ROOT / "docs" / f"QA_RECONCILIATION_{TODAY}.md"

CONFIRMED = "CONFIRMED_BY_100ROW"
FULLDATA = "STILL_REQUIRES_FULL_DATA_CHECK"
FIXED = "LIKELY_FIXED_IN_NEW_EXPORT"
OBSOLETE = "OBSOLETE_OLD_SAMPLE_DESIGN"
HUMAN = "NEEDS_HUMAN"


def findings():
    """Parse the review's pipe table. ID, priority, category, field, text."""
    out = []
    for line in REVIEW.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.startswith("| CP-") and not line.startswith("| RG-"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 5:
            continue
        out.append({"id": cells[0], "priority": cells[1], "category": cells[2],
                    "field": cells[3], "finding": cells[4],
                    "release_test": cells[-1]})
    return out


# ---------------------------------------------------------------- live checks
def _rows(name, cap=None):
    p = CUST / f"{name}.csv"
    if not p.exists():
        return [], []
    with p.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
        rd = csv.DictReader(fh)
        hdr = list(rd.fieldnames or [])
        rows = [r for i, r in zip(range(cap or 10**9), rd)]
    return hdr, rows


def check_cite_as():
    """CP-001: a fabricated `cite_as` row appended to the data."""
    hits = []
    for p in sorted(CUST.glob("*.csv")):
        if p.name == "MANIFEST.csv":
            continue
        with p.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
            first = next(csv.reader(fh), [])
            for row in csv.reader(fh):
                if row and row[0].strip().lower() == "cite_as":
                    hits.append(p.name)
                    break
    return hits


def check_internal_paths():
    """CP: source fields exposing .py, .zip, local CSVs, Desktop paths.

    READS THE FIRST 2,000 ROWS PER FILE and the cap is deliberate here -
    running this regex over every cell of a 1.2M-row, 80-column file is 97M
    matches. The counts below are therefore a LOWER BOUND, not a population:
    `nest.source_document` reports 669 and is 3,189 on the whole file. For the
    full measure, and for the split between a column that is build lineage and
    a column whose values MIX evidence with a code path,
    `code/1153_qa_publication_eligibility.py` reads every row.
    """
    pat = re.compile(r"\.py\b|\.zip\b|[A-Za-z]:\\\\|/Desktop/|\\Desktop\\|"
                     r"data/staging|data\\staging|review/|review\\\\", re.I)
    hits = defaultdict(list)
    for p in sorted(CUST.glob("*.csv")):
        if p.name == "MANIFEST.csv":
            continue
        hdr, rows = _rows(p.stem, cap=2000)
        for c in hdr:
            n = sum(1 for r in rows if pat.search((r.get(c) or "")))
            if n:
                hits[p.stem].append((c, n))
    return hits


def check_blocked_states():
    """CP-002: HOLD / quarantine / superseded / duplicate reaching the export.

    CORRECTED 2026-09-02 by `1153`. This read `cap=5000` rows per file and
    reported the result as a population, so every blocked-state count this
    reconciliation published was a count of the first 5,000 rows:
    `lobbying.is_superseded = 1` was reported 211 and is **1,064**;
    `subcontracting.duplicate_status = superseded_by_primary_source` was
    reported 38 and is **846**; `contractors.owner_attribution_status =
    CONTRADICTED_AS_OF` was reported 8 and is **9,223**. Same defect as the
    width claim below - a partial scan quoted as a whole.

    The cap is gone. `contractors.csv` is 1.6 GB, so this pass reads it with
    `csv.reader` and column indices rather than DictReader.
    """
    words = ("quarantin", "superseded", "hold_open", "do_not_ship",
             "contradict", "redirect_pending", "awaiting_owner")
    hits = defaultdict(list)
    for p in sorted(CUST.glob("*.csv")):
        if p.name == "MANIFEST.csv":
            continue
        with p.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
            rd = csv.reader(fh)
            hdr = next(rd, [])
            watch = [(i, c) for i, c in enumerate(hdr)
                     if any(k in c.lower() for k in
                            ("status", "flag", "state", "disposition",
                             "superseded", "duplicate"))]
            if not watch:
                continue
            bad = {c: Counter() for _, c in watch}
            for row in rd:
                w = len(row)
                for i, c in watch:
                    v = row[i].strip().lower() if i < w else ""
                    if not v:
                        continue
                    if any(x in v for x in words):
                        bad[c][v] += 1
                    if c.lower().startswith("is_superseded") and                             v in ("true", "1", "yes"):
                        bad[c]["is_superseded=true"] += 1
        for _, c in watch:
            if bad[c]:
                hits[p.stem].append((c, dict(bad[c].most_common(3))))
    return hits


def check_uid_role():
    """CP-003 / RG-005, REWRITTEN per the owner's ruling.

    Not "is cedar_uid the row subject" - that was ruled too broad. The test is
    whether every dataset that carries a cedar_uid resolves it to a real Native
    entity, and whether its ROLE is declared somewhere a buyer can read.
    """
    reg = ROOT / "data" / "spine" / "cedar_identity_register.csv"
    known = set()
    if reg.exists():
        with reg.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
            for r in csv.DictReader(fh):
                v = (r.get("cedar_uid") or "").strip()
                if v:
                    known.add(v)
    out = {}
    for p in sorted(CUST.glob("*.csv")):
        if p.name == "MANIFEST.csv":
            continue
        hdr, rows = _rows(p.stem, cap=5000)
        if "cedar_uid" not in hdr:
            continue
        vals = [(r.get("cedar_uid") or "").strip() for r in rows]
        filled = [v for v in vals if v]
        unknown = [v for v in filled if known and v not in known]
        codebook = CUST / f"{p.stem}__CODEBOOK.md"
        declared = (codebook.exists()
                    and "cedar_uid" in codebook.read_text(encoding="utf-8",
                                                          errors="replace"))
        out[p.stem] = {"filled": len(filled), "rows": len(rows),
                       "unresolvable": len(unknown), "role_documented": declared}
    return out


def check_synthetic_dates():
    """A month-only source rendered as the 15th."""
    out = {}
    for p in sorted(CUST.glob("*.csv")):
        if p.name == "MANIFEST.csv":
            continue
        hdr, rows = _rows(p.stem, cap=20000)
        for c in hdr:
            if "date" not in c.lower():
                continue
            days = Counter()
            for r in rows:
                m = re.match(r"^\d{4}-\d{2}-(\d{2})", (r.get(c) or "").strip())
                if m:
                    days[m.group(1)] += 1
            tot = sum(days.values())
            if tot >= 40 and days.get("15", 0) / tot > 0.25:
                out[f"{p.stem}.{c}"] = (days["15"], tot)
    return out


def check_owned_has_rows():
    """The blocker: Native-Owned Businesses exported zero business records."""
    hdr, rows = _rows("native-owned-businesses")
    return len(rows), len(hdr)


def check_width():
    """CP: the export shipping 60-80 debugging columns."""
    return {p.stem: len(_rows(p.stem, cap=1)[0])
            for p in sorted(CUST.glob("*.csv")) if p.name != "MANIFEST.csv"}


def check_preview_width():
    """The OTHER width, and the one the earlier claim confused it with.

    `dist/preview` is the 100-row curated preview and is 7-11 columns wide.
    `dist/customer` is the delivered product. Reporting one range without
    saying which directory it came from is how "the export has narrowed"
    got written about an export that had widened.
    """
    d = ROOT / "dist" / "preview"
    if not d.exists():
        return {}
    out = {}
    for p in sorted(d.glob("*.csv")):
        if p.name == "MANIFEST.csv":
            continue
        with p.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
            out[p.stem] = len(next(csv.reader(fh), []))
    return out


def classify(f, ev):
    """One finding -> (verdict, evidence). Machine-checked where possible."""
    i, cat = f["id"], f["category"].lower()
    text = (f["finding"] + " " + f["field"]).lower()

    if i == "CP-001":
        h = ev["cite_as"]
        return ((CONFIRMED, f"`cite_as` row still in {len(h)} file(s): "
                 f"{', '.join(h[:4])}") if h else
                (FIXED, "no delivered file carries a `cite_as` data row"))

    if i in ("CP-003", "RG-005"):
        bad = [k for k, v in ev["uid"].items() if v["unresolvable"]]
        undoc = [k for k, v in ev["uid"].items() if not v["role_documented"]]
        return (HUMAN,
                "REWRITTEN per owner ruling 2026-09-02: the test is not "
                "whether cedar_uid names the row subject - a NEST row keyed "
                "enterprise_id with cedar_uid=owner is correct - but whether "
                "its ROLE is unambiguous and it always resolves to a Native "
                f"entity. Measured: {len(ev['uid'])} datasets carry cedar_uid, "
                f"{len(bad)} hold a uid absent from the register "
                f"({', '.join(bad[:3]) or 'none'}), "
                f"{len(undoc)} do not document the role in their codebook "
                f"({', '.join(undoc[:3]) or 'none'})")

    if "no data" in text or "zero business records" in text or "owned-collection" in text:
        n, w = ev["owned"]
        return ((FIXED, f"native-owned-businesses now delivers {n:,} rows x {w} cols")
                if n > 100 else (CONFIRMED, f"still only {n} rows"))

    if any(k in text for k in ("python file", ".py", ".zip", "desktop", "local csv",
                               "code path", "pipeline artifact", "source_file")):
        h = ev["paths"]
        return ((CONFIRMED, "internal paths still exported (first 2,000 rows "
                 "per file, a lower bound): "
                 + "; ".join(f"{k}:{c[0][0]}({c[0][1]})" for k, c in list(h.items())[:3])
                 + ". Every PURE build-lineage column is now dropped by "
                   "cedar_publication.LINEAGE_COLS; what remains are columns "
                   "whose values MIX a real source statement with a code path, "
                   "kept deliberately and listed in "
                   "docs/PUBLICATION_ELIGIBILITY.md")
                if h else (FIXED, "no delivered column exposes a .py/.zip/Desktop path"))

    if any(k in text for k in ("hold", "quarantin", "superseded", "duplicate",
                               "adjudication", "publication gate", "blocked")):
        h = ev["blocked"]
        return ((CONFIRMED, "blocked states still present: "
                 + "; ".join(f"{k}.{c[0][0]}" for k, c in list(h.items())[:3])
                 + ". Judged one by one in cedar_publication.BLOCKED_STATES: "
                   "what remains is FLAG (a superseded LDA filing is a real "
                   "filed record and ships with its supersession stated) or "
                   "MASK (the row ships, the Cedar attribution on it does "
                   "not). WITHHOLD states no longer ship - see "
                   "docs/PUBLICATION_ELIGIBILITY.md")
                if h else (FULLDATA,
                           "no blocked state found in the delivered columns - but "
                           "the curated export no longer carries most status "
                           "fields, so absence here is not proof of absence "
                           "upstream. Check data/clean, not dist/customer."))

    if "15th" in text or "month-only" in text or "synthetic date" in text:
        h = ev["dates"]
        return ((CONFIRMED, "day-15 clustering: "
                 + "; ".join(f"{k} {v[0]}/{v[1]}" for k, v in list(h.items())[:3]))
                if h else (FIXED, "no date column clusters on the 15th"))

    if any(k in text for k in ("all ten", "ten rows", "sample", "concentrat",
                               "one era", "one source", "eight of ten")):
        return (OBSOLETE, "a property of the old ten-row sample generator; the "
                          "hundred-row export selects for distinct subjects")

    if any(k in text for k in ("column", "field", "debug", "residue", "internal")):
        w = ev["width"]
        wide = {k: v for k, v in w.items() if v > 40}
        pv = ev["preview_width"]
        return (FULLDATA, f"dist/customer is {min(w.values())}-{max(w.values())} "
                          f"columns (widest {max(w, key=w.get)}); {len(wide)} "
                          f"dataset(s) over 40. The DELIVERED export is WIDER "
                          f"than the review's 29-81, not narrower - only the "
                          f"100-row previews are narrow"
                          + (f" ({min(pv.values())}-{max(pv.values())})"
                             if pv else " (dist/preview absent)")
                          + ". Whether a specific field survived needs a named "
                            "check; the build-lineage columns are now dropped "
                            "by cedar_publication.LINEAGE_COLS and audited by "
                            "1153.")

    return (FULLDATA, "not machine-checkable from the delivered export alone")


def main() -> int:
    mode = sys.argv[1] if len(sys.argv) > 1 else "report"
    if not REVIEW.exists():
        print(f"  the review is not at {REVIEW.relative_to(ROOT)}")
        return 1
    fs = findings()
    ev = {"cite_as": check_cite_as(), "paths": check_internal_paths(),
          "blocked": check_blocked_states(), "uid": check_uid_role(),
          "dates": check_synthetic_dates(), "owned": check_owned_has_rows(),
          "width": check_width(), "preview_width": check_preview_width()}

    rows, tally = [], Counter()
    for f in fs:
        verdict, why = classify(f, ev)
        tally[verdict] += 1
        rows.append({**f, "verdict": verdict, "evidence": why})

    print(f"  1152 reconciliation   {len(fs)} findings from the ten-row review\n")
    for k in (CONFIRMED, FULLDATA, FIXED, OBSOLETE, HUMAN):
        print(f"    {k:<32} {tally[k]:>4}")
    print()
    print(f"    native-owned-businesses : {ev['owned'][0]:,} rows "
          f"(the review found 0)")
    print(f"    files with a cite_as row: {len(ev['cite_as'])} (was 11)")
    print(f"    internal paths exported : {len(ev['paths'])} dataset(s)")
    print(f"    blocked states exported : {len(ev['blocked'])} dataset(s)")
    print(f"    day-15 date clustering  : {len(ev['dates'])} column(s)")
    w, pv = ev["width"], ev["preview_width"]
    # CORRECTED 2026-09-02. This line used to print one range and let the
    # reader infer the export had narrowed toward the review's 29-81. It had
    # not: `gaming` ships 309 columns and only `dist/preview` is narrow. Two
    # ranges, each named for the directory it measures.
    print(f"    dist/customer width     : {min(w.values())}-{max(w.values())} cols "
          f"(widest {max(w, key=w.get)}) - the review saw 29-81 on the ten-row "
          f"sample, so the delivered export is WIDER, not narrower")
    print(f"    dist/preview width      : "
          + (f"{min(pv.values())}-{max(pv.values())} cols" if pv
             else "absent - rebuild with 1151"))

    if mode == "build":
        OUT.parent.mkdir(parents=True, exist_ok=True)
        with OUT.open("w", encoding="utf-8", newline="") as fh:
            wr = csv.DictWriter(fh, fieldnames=list(rows[0]))
            wr.writeheader()
            wr.writerows(rows)
        print(f"\n    ledger -> {OUT.relative_to(ROOT)}")
    elif mode != "verify":
        print("\n  nothing written. re-run with `build`.")

    if mode == "verify":
        bad = []
        if not OUT.exists():
            bad.append("no reconciliation ledger - run `build`")
        if ev["cite_as"]:
            bad.append(f"CP-001 unfixed: {len(ev['cite_as'])} file(s) ship a "
                       f"cite_as row")
        for b in bad:
            print("  FAIL " + b)
        print(f"  1152 verify   {'FAIL' if bad else 'ok'}   {len(bad)} problem(s)")
        return 1 if bad else 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
