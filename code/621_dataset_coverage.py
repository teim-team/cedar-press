#!/usr/bin/env python3
"""
Cedar Press - 621: THE MEASURED HALF OF EVERY DATASET DOC'S COVERAGE TABLE.

    py -3 code/621_dataset_coverage.py                # measure (incremental)
    py -3 code/621_dataset_coverage.py --force        # re-measure every table
    py -3 code/621_dataset_coverage.py inject         # rewrite the AUTO blocks
                                                      # in the hand-written docs
    py -3 code/621_dataset_coverage.py verify         # exit 1 if a doc's AUTO
                                                      # block is out of date

WHY THIS EXISTS
---------------
The owner's standing complaint about the per-dataset docs is *"it seems like
you're missing stuff for every dataset"* and *"I'm not sure why you're
forgetting parts of it"*. The answer the project settled on is a COVERAGE table
per dataset: per source, **years upstream, years Cedar holds, the gap.**

Two of those three columns are research and belong to a human. **One of them is
a measurement**, and a measurement typed into markdown by hand is stale the
moment the next build lands - which is the entire subject of
`code/527_doc_staleness.py`. `02_contracting.md` already carries an exemplary
COVERAGE table, and every "years Cedar holds" cell in it was hand-typed.

So this script owns the measured column, and only that column:

    years upstream    authored - SPEC in 24, or prose in a hand-written doc
    years CEDAR HOLDS measured HERE, from the live table, on every run
    the gap           follows from the two

THE MARKER CONTRACT
-------------------
Every dataset doc carries exactly one block delimited by

    <!-- CEDAR:COVERAGE-MEASURED collection=<id> START -->
    ...generated, do not hand-edit...
    <!-- CEDAR:COVERAGE-MEASURED collection=<id> END -->

`inject` rewrites what is between the markers and touches nothing else, so the
authored research around it survives. `24_generate_dataset_docs.py` imports
`render_block()` and emits the same content for the 11 docs it generates - the
docs it owns must never be hand-edited (its own docstring says so), so it calls
the renderer rather than being injected into.

WHY IT CACHES
-------------
The 13 collections' tables total ~4.9 GB and this repo lives on a spinning
disk. A full pass is minutes; the docs are regenerated far more often than the
tables change. So the measurement is keyed on (size, mtime) per file and only
changed tables are re-read. `--force` ignores the cache.

WHAT A BLANK CELL MEANS, STATED
-------------------------------
`period` reads **no dated column** when the table declares no period column and
none of the candidate names is present. That is NOT the same as "no dates" and
must never be rendered as a zero or an empty range - `cedar_period_columns`
exists because exactly that confusion printed 0.0% coverage on two fully-dated
tables for 19 days. A table with no dated column is a real answer about the
table, and it is printed as words.
"""
from __future__ import annotations

import csv
import json
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CODE = ROOT / "code"
CLEAN = ROOT / "data" / "clean"
DOCS = ROOT / "docs"
CACHE = DOCS / "schema" / "dataset_coverage_measured.json"
TODAY = date.today().isoformat()

csv.field_size_limit(10_000_000)
sys.path.insert(0, str(CODE))

try:
    from cedar_period_columns import PERIOD_COLUMNS  # noqa: E402
except ImportError:            # pragma: no cover - the module is committed
    PERIOD_COLUMNS = {}

# The fallback candidate list, kept identical in spirit to 35's DATE_COLS.
# Exact match on the lowercased header name, best first. `cedar_period_columns`
# always wins where it has an entry - this list is only for tables that have no
# declaration yet, and a name that is missing here reports "no dated column"
# rather than silently reporting nothing.
DATE_COLS = [
    "action_date", "event_date", "filing_date", "filed_date", "decision_date",
    "publication_date", "effective_date", "award_date", "notice_date",
    "period_end", "payment_date", "date", "signed_date", "vote_date",
    "introduced_date", "open_date", "as_of_date", "observation_date",
    "observation_period", "document_date", "source_document_date",
    "event_year", "fiscal_year", "filing_year", "year", "tax_year",
    "report_year", "award_fiscal_year",
    # ADDED 2026-09-01 after the first run printed "no dated column" on tables
    # that are fully dated. `fac_tribal_single_audits.csv` was the tell: 6,780
    # rows, and `301_source_freshness_probe.py` had already measured its newest
    # period as 2026-08 - so the absence was in THIS LIST, which is the exact
    # defect `cedar_period_columns.py` was written about. Each name below was
    # confirmed present on a real table before being added.
    "opinion_date", "meeting_date", "hearing_date", "bia_decision_date",
    "publication_year", "audit_year", "grant_year",
    # A ruling ledger's only date is the date of the ruling. It is a Cedar
    # event rather than a source event, which is why it sits last - any table
    # with a real source date will match above it.
    "ruled_date", "ruling_date",
]

# NOT period columns, and listed so nobody adds them by pattern-matching on the
# name. `built_date` appears on 70 tables and is the date CEDAR wrote the row;
# using it would report every table as "2026" and hide every real gap.
# `first_year`/`last_year` are the ENDS of a span the row already summarises,
# not the period the row sits in.
NEVER_PERIOD = ("built_date", "fetched_date", "promoted_date", "checked_date",
                "verified_date", "ocr_date", "first_year", "last_year",
                "entity_keyed_date", "entity_link_date", "inflation_base_year")

YEAR_RX = re.compile(r"(1[6-9]\d\d|20\d\d|21\d\d)")

MARK_START = "<!-- CEDAR:COVERAGE-MEASURED collection={cid} START -->"
MARK_END = "<!-- CEDAR:COVERAGE-MEASURED collection={cid} END -->"

# Hand-written docs this script injects into. The generated docs are NOT here:
# 24 owns those and imports render_block() instead.
HAND_DOCS = {
    "natural-resources": "docs/datasets/natural_resources_sources.md",
    "native-owned-businesses": "docs/datasets/native-owned-businesses.md",
    "_entity_layer": "docs/datasets/_entity_layer.md",
    "federal-register": "docs/datasets/federal-register.md",
    "nagpra": "docs/datasets/nagpra.md",
    "subcontracting": "docs/datasets/subcontracting.md",
    "gaming": "docs/datasets/gaming_sources.md",
    "lobbying": "docs/datasets/lobbying_sources.md",
    # Added 2026-09-02 by GRAIN-LEGISLATION. docs/datasets/10_bills_votes.md
    # ALREADY CARRIED the CEDAR:COVERAGE-MEASURED block and was not in this
    # map, so the generator never touched it and the block froze at its
    # 2026-09-01 vintage - still reading "Status: BLOCKED, 12 customer tables"
    # after the dataset reached READY at 11. A generated block that no
    # generator owns is worse than a hand-written one, because it carries a
    # banner telling the reader not to edit it by hand.
    "legislation": "docs/datasets/10_bills_votes.md",
}


# ---------------------------------------------------------------------------
# measurement
# ---------------------------------------------------------------------------
def _period_column(table: str, header: list[str]) -> str | None:
    low = {h.lower(): h for h in header}
    spec = PERIOD_COLUMNS.get(table)
    if spec:
        for c in spec["cols"]:
            if c.lower() in low:
                return low[c.lower()]
    for c in DATE_COLS:
        if c in low and c not in NEVER_PERIOD:
            return low[c]
    return None


def measure_table(table: str) -> dict:
    """Rows, period column, and observed year span for one clean table."""
    p = CLEAN / table
    if not p.exists():
        return {"exists": False, "rows": None, "period_col": None,
                "first_year": None, "last_year": None, "years": [],
                "size": None, "mtime": None}
    st = p.stat()
    out = {"exists": True, "size": st.st_size, "mtime": int(st.st_mtime)}
    years: dict[int, int] = {}
    n = 0
    with p.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
        rd = csv.reader(fh)
        try:
            header = next(rd)
        except StopIteration:
            out.update(rows=0, period_col=None, first_year=None,
                       last_year=None, years=[])
            return out
        col = _period_column(table, header)
        idx = header.index(col) if col else None
        for row in rd:
            n += 1
            if idx is None or idx >= len(row):
                continue
            m = YEAR_RX.search(row[idx] or "")
            if m:
                y = int(m.group(1))
                years[y] = years.get(y, 0) + 1
    ys = sorted(years)
    out.update(rows=n, period_col=col,
               first_year=ys[0] if ys else None,
               last_year=ys[-1] if ys else None,
               dated_rows=sum(years.values()),
               years=ys,
               year_counts={str(y): years[y] for y in ys})
    return out


def thin_years(m: dict) -> list[int]:
    """Years inside the observed range that are present but NEARLY empty.

    AN INTERIOR-GAP CHECK ONLY CATCHES A ZERO, AND A FAILED PULL RARELY
    LEAVES A ZERO. `subawards.csv` is the case that produced this function:
    FY2021 holds 9,462 rows and FY2025 holds 7,360, while FY2022/23/24 hold
    89, 120 and 166 - because `usaspending_fsrs_pull` contributed NOTHING to
    those three years and only a 2023 vendor export and a forward-fill did.
    `35_coverage_audit.py` reports "no interior gaps" for that table and is
    right on its own terms; the three-year hole is invisible to it.

    So: a year is thin when it holds under 20% of the MEDIAN populated year
    in the same table. The median, not the mean, because one enormous year
    must not excuse the rest. This is a flag, not a verdict - a genuinely
    quiet year (a compact is not signed every year) will trip it, which is
    why the render prints it as a question and never as a defect.
    """
    yc = {int(k): v for k, v in (m.get("year_counts") or {}).items()}
    if len(yc) < 5:
        return []
    vals = sorted(yc.values())
    med = vals[len(vals) // 2]
    if med <= 0:
        return []
    return [y for y in sorted(yc) if yc[y] < 0.2 * med]


def contracts() -> list[dict]:
    d = json.loads((DOCS / "schema" / "dataset_contracts.json")
                   .read_text(encoding="utf-8"))
    return d["contracts"]


def readiness() -> dict:
    p = CLEAN / "cedar_dataset_readiness.csv"
    with p.open(encoding="utf-8-sig") as fh:
        return {r["dataset"]: r for r in csv.DictReader(fh)}


def measure(force: bool = False) -> dict:
    old = {}
    if CACHE.exists() and not force:
        try:
            old = json.loads(CACHE.read_text(encoding="utf-8")).get("tables", {})
        except ValueError:
            old = {}
    tables, reused, fresh = {}, 0, 0
    for c in contracts():
        for t in c["tables"]:
            name = t["table"]
            if name in tables:
                continue
            p = CLEAN / name
            prev = old.get(name)
            if (prev and not force and p.exists()
                    and prev.get("size") == p.stat().st_size
                    and prev.get("mtime") == int(p.stat().st_mtime)):
                tables[name] = prev
                reused += 1
                continue
            tables[name] = measure_table(name)
            fresh += 1
    blob = {"measured_date": TODAY, "script": "code/621_dataset_coverage.py",
            "n_tables": len(tables), "tables": tables}
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps(blob, indent=1), encoding="utf-8")
    print(f"  621 coverage   {len(tables)} tables   "
          f"{fresh} re-measured   {reused} cached")
    return blob


def load() -> dict:
    if not CACHE.exists():
        return measure()
    return json.loads(CACHE.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# rendering
# ---------------------------------------------------------------------------
def _span(m: dict) -> str:
    if not m.get("exists"):
        return "**not built**"
    if not m.get("period_col"):
        return "no dated column"
    if m.get("first_year") is None:
        return f"`{m['period_col']}` present, **0 rows parse to a year**"
    a, b = m["first_year"], m["last_year"]
    ys = set(m.get("years") or [])
    interior = [y for y in range(a, b + 1) if y not in ys]
    s = f"{a}–{b}" if a != b else f"{a}"
    if interior:
        gap = ", ".join(str(y) for y in interior[:6])
        if len(interior) > 6:
            gap += f", +{len(interior) - 6} more"
        s += f" (interior gap: {gap})"
    thin = [y for y in thin_years(m) if y not in (a, b)]
    if thin:
        t = ", ".join(str(y) for y in thin[:6])
        if len(thin) > 6:
            t += f", +{len(thin) - 6} more"
        s += f" · **thin: {t}**"
    return s


def render_block(cid: str, blob: dict | None = None) -> str:
    """The measured block for one collection, markers included."""
    blob = blob or load()
    meas = blob["tables"]
    con = {c["collection"]: c for c in contracts()}.get(cid)
    rd = readiness().get(cid)
    L = [MARK_START.format(cid=cid), "",
         "## Readiness and coverage — measured, never hand-typed", "",
         f"*The status line and the `Years Cedar holds` column below are "
         f"regenerated by `py -3 code/621_dataset_coverage.py` "
         f"(tables measured {blob.get('measured_date', '?')}) and "
         f"`py -3 code/518_dataset_readiness.py`. Do not edit them by hand; "
         f"edit the table and re-run. The `Years upstream` research around "
         f"this block is authored and is NOT touched by the generator.*", ""]

    if rd:
        status = rd["status"]
        badge = "READY" if status == "READY" else "BLOCKED"
        L += [f"**Status: {badge}** — {rd['n_customer_tables']} customer "
              f"tables, shelf `{rd['shelf']}`, measured "
              f"{rd['measured_date']} by `518`.", ""]
        if status == "READY":
            L += ["No open contract point. Next action: "
                  f"**{rd['next_action']}**.", ""]
        else:
            L += ["**Open contract points, with the tables that carry "
                  "them:**", ""]
            for b in [x.strip() for x in rd["blockers"].split("|") if x.strip()]:
                L.append(f"- {b}")
            L += ["", f"Next action: **{rd['next_action']}**.", ""]
        L += ["| contract point | state |", "|---|---|",
              f"| C1 grain stated | {rd['c1_grain']} |",
              f"| C2 validated primary key | {rd['c2_keys']} |",
              f"| C3 literal duplicates | {rd['c3_duplicates']} |",
              f"| C4 identity path | {rd['c4_identity_path']} |",
              f"| C5 row conservation | {rd['c5_row_conservation']} |",
              f"| C6 unresolved conflicts | {rd['c6_unresolved_conflicts']} |",
              f"| C7 double counting | {rd['c7_double_counting']} |",
              f"| C8 rebuild path | {rd['c8_rebuild_path']} |",
              f"| C9 update documented | {rd['c9_update_documented']} |",
              f"| C10 gates | {rd['c10_gates']} |", ""]
    else:
        L += [f"**Status: not in `cedar_dataset_readiness.csv`** — `518` does "
              f"not know a collection called `{cid}`. That is a defect in the "
              f"scoreboard or in this marker, not a property of the data.", ""]

    L += ["### Years Cedar holds — per table, measured from the live file", "",
          "| Table | Rows | Period column | Years Cedar holds |",
          "|---|---:|---|---|"]
    if not con:
        L.append("| *(no contract entry)* | | | |")
    else:
        for t in sorted(con["tables"], key=lambda x: x["table"]):
            m = meas.get(t["table"]) or {"exists": False}
            rows = "—" if m.get("rows") is None else f"{m['rows']:,}"
            pc = f"`{m['period_col']}`" if m.get("period_col") else "—"
            flag = "" if t["status"] == "shippable" else f" *({t['status']})*"
            L.append(f"| `{t['table']}`{flag} | {rows} | {pc} | {_span(m)} |")
    L += ["", MARK_END.format(cid=cid)]
    return "\n".join(L)


# ---------------------------------------------------------------------------
# injection
# ---------------------------------------------------------------------------
def inject(check_only: bool = False) -> int:
    blob = load()
    bad = 0
    for cid, rel in sorted(HAND_DOCS.items()):
        p = ROOT / rel
        if not p.exists():
            print(f"    MISSING  {rel}")
            bad += 1
            continue
        txt = p.read_text(encoding="utf-8")
        s, e = MARK_START.format(cid=cid), MARK_END.format(cid=cid)
        block = render_block(cid, blob)
        if s in txt and e in txt:
            i, j = txt.index(s), txt.index(e) + len(e)
            cur = txt[i:j]
            if cur == block:
                print(f"    ok       {rel}")
                continue
            if check_only:
                print(f"    STALE    {rel}")
                bad += 1
                continue
            p.write_text(txt[:i] + block + txt[j:], encoding="utf-8")
            print(f"    updated  {rel}")
        else:
            if check_only:
                print(f"    NO BLOCK {rel}")
                bad += 1
                continue
            sep = "" if txt.endswith("\n") else "\n"
            p.write_text(txt + sep + "\n---\n\n" + block + "\n",
                         encoding="utf-8")
            print(f"    added    {rel}")
    return bad


def main() -> int:
    arg = sys.argv[1] if len(sys.argv) > 1 else ""
    if arg == "inject":
        measure("--force" in sys.argv)
        return 1 if inject(False) else 0
    if arg == "verify":
        return 1 if inject(True) else 0
    measure("--force" in sys.argv)
    return 0


if __name__ == "__main__":
    sys.exit(main())
