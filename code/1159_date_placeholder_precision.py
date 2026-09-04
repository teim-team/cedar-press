#!/usr/bin/env python3
r"""Cedar Press 1159 - A PLACEHOLDER DAY MAY NOT SHIP AS A DAY.

    py -3 code/1159_date_placeholder_precision.py report
    py -3 code/1159_date_placeholder_precision.py sweep
    py -3 code/1159_date_placeholder_precision.py apply
    py -3 code/1159_date_placeholder_precision.py verify
    py -3 code/1159_date_placeholder_precision.py fixtures

-------------------------------------------------------------------------------
THE COMPLAINT, AND WHERE IT IS AND IS NOT TRUE
-------------------------------------------------------------------------------
Owner, 2026-09-02: *"month-only dates converted to the 15th still exist"*, cited
against `dist/customer/gaming.csv`, where 148 of 339 `open_date_source_value_
verbatim` values and 59 of 76 `close_date_source_value_verbatim` values fall on
day 15. Both figures reproduce exactly.

**They are not Cedar's day, and this was checked at the source rather than
argued.** `data/raw/external/gaming/directory_core/Tribal Property List.xlsx`,
the Casino City roster `23d_build_gaming_facilities.py` reads, holds 553
non-empty `Open Date` cells, of which **165 fall on day 15 and 188 on 31
December**, and 142 `1st Close Date` cells of which **63 fall on day 15**. Every
cell is a real Excel datetime under number format `[$-409]d\-mmm\-yyyy`, so the
vendor both STORES and DISPLAYS a day. Cedar transcribed it; Cedar did not
complete it. `_source_value_verbatim` is therefore an honest name for an
inherited placeholder, and `code/158_extend_gaming_facilities.py` already did
the right thing with the SHIPPING column: `open_date` reads `1985-04`,
`open_date_precision` says `month`, and `open_date_not_before` /
`open_date_not_after` carry the month. Only 6 of 636 `open_date` values still
end in `-15`, and all six are hand-researched day-precision dates from
non-vendor sources (Foxwoods really did open on 15 February 1992).

What is missing in gaming is small and real: **nothing on the row says the
retained verbatim value carries a placeholder day.** A consumer who parses
`open_date_source_value_verbatim` instead of `open_date` gets a fabricated day
with no warning, because the warning is prose at the end of a 300-character
`_basis` string. EDIT 1 makes it a column.

-------------------------------------------------------------------------------
WHERE THE COMPLAINT IS LITERALLY TRUE, AND NOBODY HAD LOOKED: `deals`
-------------------------------------------------------------------------------
`dist/customer/deals.csv` has **no date-precision machinery at all** - no
`Event_Date_class`, `_precision`, `_not_before` or `_not_after`. It has 85
`Event_Date` values on day 15 against ~35 expected, and its own `Date_Basis`
column says, in English, that most of them are invented:

    "MONTH-LEVEL DATE ONLY. The filing states the month and year of the
     transaction and no day. A mid-month placeholder day (15) is used per
     ledger convention; the day is NOT stated by the source."      x32

100 rows carry such a phrase. 71 of them land on day 15. Two `YEAR-LEVEL ONLY`
rows carry `Event_Date = 2015-07-01` - a placeholder MONTH as well as a day -
and two more carry `Event_Quarter = Q3` derived from a source that states only a
year. Twelve `FISCAL-YEAR PLACEHOLDER` rows carry a fiscal-year END date in a
field a buyer reads as the event date.

So the disclosure exists and only a human reading 400 characters of prose can
act on it. EDIT 2 turns each of those sentences into the same four columns
`gaming` already has, and re-types the value to the precision its own basis
states - `2001-03-15` becomes `2001-03` - following exactly what `158` did.

**Nothing is re-sourced and nothing is invented.** The precision comes only from
what the row's own `Date_Basis` already says. A row whose basis does not state a
precision keeps `day` and is counted, not guessed at.

-------------------------------------------------------------------------------
EDIT 1 - gaming_facilities.csv: flag the inherited placeholder
-------------------------------------------------------------------------------
Adds `open_date_source_value_placeholder` and `close_date_source_value_
placeholder` beside the verbatim columns:

    vendor_mid_month_placeholder_day_15   verbatim is YYYY-MM-15, vendor basis
    vendor_year_end_placeholder_1231      verbatim is YYYY-12-31, vendor basis
    source_states_the_day                 any other verbatim value
    (blank)                               no verbatim value on this row

with a `_basis` naming the measurement in the vendor workbook. `open_date`,
`open_date_precision` and the interval columns are NOT touched - 158 already has
them right, and a second pass re-deriving the same field is how two ladders for
one number start drifting.

-------------------------------------------------------------------------------
EDIT 2 - deals_classified.csv: the precision machinery, from the row's own basis
-------------------------------------------------------------------------------
Adds `Event_Date_source_value_verbatim`, `Event_Date_class`,
`Event_Date_precision`, `Event_Date_not_before`, `Event_Date_not_after`,
`Event_Date_precision_basis`. Re-types `Event_Date` to `YYYY-MM` for a
month-precision row and `YYYY` for a year-precision row, and BLANKS
`Event_Quarter` / `Event_Month` where a year-precision source cannot determine
them.

A `FISCAL-YEAR PLACEHOLDER` row is **classified, not re-typed**: its value is a
fiscal-year end standing in for an unknown event date, the calendar year is not
always determined by it, and blanking the field would trip the invariant
`1088_merge_staged_deals.py` enforces on a blank `Event_Date`. It gets
`Event_Date_class = fiscal_year_end_placeholder` and empty bounds with a named
reason, which is the honest shape: the value is disclosed as not-an-event-date
rather than silently corrected or silently kept.

-------------------------------------------------------------------------------
THIS IS AN IN-PLACE ENRICHER
-------------------------------------------------------------------------------
Both tables have full-rebuild writers (`23d`/`23f` for gaming, the ten Phase 1
scripts for deals). `code/build.py plan <collection>` discovers enrichers from
293's IO map, so this script appears in PHASE 2 and must be re-run after any
rebuild. Backups are taken under the STEM tag, never the bare number.

`sweep` is the full-population check the owner asked for: every ISO date column
in every `dist/customer/*.csv`, against a per-day baseline, with the legitimate
shapes named rather than listed as findings.
"""

import calendar
import csv
import json
import math
import re
import shutil
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

CEDAR = Path(__file__).resolve().parent.parent
CLEAN = CEDAR / "data" / "clean"
DIST = CEDAR / "dist" / "customer"
DOCS = CEDAR / "docs"
GAMING = CLEAN / "gaming_facilities.csv"
DEALS = CLEAN / "deals_classified.csv"
SWEEP_JSON = DOCS / "DATE_PLACEHOLDER_SWEEP.json"
TODAY = date.today().isoformat()
TAG = f".bak_{TODAY}_pre_1159_date_placeholder_precision"

csv.field_size_limit(min(sys.maxsize, 2**31 - 1))

ISO = re.compile(r"^(\d{4})-(\d{2})-(\d{2})$")
# The shapes this pass itself WRITES. Reading them back is what makes a second
# run a no-op instead of a demolition.
YM = re.compile(r"^(\d{4})-(\d{2})$")
YONLY = re.compile(r"^(\d{4})$")

# Occurrences per year of each day-of-month over the Gregorian cycle. Day-of-
# month is NOT uniform at 1/30.44: days 1..28 occur twelve times a year, the
# 29th 11.24, the 30th eleven and the 31st SEVEN. Using 1/30.44 for day 31
# over-states the expectation by 74% and hides a year-end placeholder.
OCC = {d: 12.0 for d in range(1, 29)}
OCC[29], OCC[30], OCC[31] = 11.2425, 11.0, 7.0
DAYS_PER_YEAR = 365.2425
PDAY = {d: OCC[d] / DAYS_PER_YEAR for d in OCC}

# Z at which a day concentration is reported. 5 sigma on a per-column basis
# across ~1,200 delivered date columns keeps the expected false-positive count
# below one.
Z_REPORT = 5.0

# The days a placeholder convention actually uses: the 1st and the 15th for a
# month-precision value, the 30th and 31st for a period or year end.
PLACEHOLDER_DAYS = frozenset({1, 15, 30, 31})

# ---------------------------------------------------------------------------
# Shapes that produce a legitimate day concentration. Each is a RULE about what
# the column means, not a name on a list: a column matching one of these is
# explained, not excused, and the explanation is printed beside it.
# ---------------------------------------------------------------------------
LEGITIMATE = (
    (re.compile(r"_not_before$|_not_after$"),
     "an interval bound emitted BY the precision machinery: a year-precision "
     "date bounds to YYYY-01-01 and YYYY-12-31 by construction"),
    (re.compile(r"^built_date$|^fetched_date$|^harvest_date$|^promoted_date$|"
                r"^entity_keyed_date$|^temporal_build_date$|_built_date$|"
                r"^classified_date$|^ruling_applied_date$|^geo_built_date$"),
     "a build or retrieval stamp: one date per run, repeated on every row"),
    (re.compile(r"^period_start$|^period_end$|_effective_start$|_effective_end$|"
                r"^allocation_formula_effective_"),
     "a reporting-period or policy-period boundary, which lands on the first "
     "or last day of a month by definition"),
    (re.compile(r"_observed_date$|_as_of$|^first_observed_date$|^last_observed_date$|"
                r"^observed_open_by$|_observed_first$|_observed_last$|"
                r"^property_status_observed_date$|_observation_date$"),
     "an observation stamp inherited from a panel vintage, so a handful of "
     "vintage dates cover most rows"),
    (re.compile(r"^Date_Added$|^Data_As_Of$|^source_last_updated$|^bmf_vintage_fetched$|"
                r"^source_edition_date$|_link_date$"),
     "a snapshot or edition label, not an event date"),
)


# Adjudications for the placeholder-shaped concentrations that survive the
# LEGITIMATE rules. Each was measured 2026-09-02 before it was written down;
# the measurement is in the text so the next reader can re-run it rather than
# trust it. FIXED / REAL / OPEN, and OPEN means OPEN.
ADJUDICATED = {
    ("gaming.csv", "open_date_source_value_verbatim"):
        "FIXED here. The vendor's own placeholder, transcribed not completed - "
        "see this script's docstring. `open_date` is already re-typed by 158; "
        "EDIT 1 adds the machine-readable flag the verbatim column lacked.",
    ("gaming.csv", "close_date_source_value_verbatim"):
        "FIXED here, same as open_date_source_value_verbatim.",
    ("subcontracting.csv", "subaward_date"):
        "REAL. 12,592 day-1 values, but the MONTH distribution is 4,518 October "
        "and 2,677 July against ~1,050 per month if it were a mid-month-style "
        "convention: that is the federal fiscal year and its half-year, i.e. "
        "genuine period-of-performance starts. A completed month-only date "
        "would be flat across months. Not a placeholder.",
    ("funding.csv", "action_date"):
        "REAL. 5.0% on day 1 against 3.3% expected. Assistance actions start on "
        "the first of a month; the excess is 1.7 points, not the 40 points a "
        "completed month-only date produces.",
    ("lobbying.csv", "termination_date"):
        "REAL. The mass is on 12-31 (119), 06-30 (71), 09-30 (56) and 03-31 "
        "(46), with 01-01 (69), 04-01 (38) and 07-01 (28) beside them: the LDA "
        "quarterly reporting calendar, where a registration terminates at a "
        "period boundary. Not a placeholder.",
    ("native-owned-businesses.csv", "certification_expiration"):
        "REAL. 78 of 705 on day 31, 9.1% of the column on 2025-12-31 alone: "
        "certifications are written to expire at a calendar year end.",
    ("gaming.csv", "open_date"):
        "OPEN, and deliberately not fixed. 28 of 188 full-ISO open dates fall "
        "on day 1, and 26 of them carry `Casino City Tribal Property List` as "
        "their basis at `open_date_precision = day`. Day 1 is a THIRD vendor "
        "placeholder shape that neither `23f.interpret()` (which downgrades "
        "only day 15 and 31 December) nor `158.retype_dates` catches. But the "
        "vendor workbook itself holds only 31 day-1 values in 553 - 5.6% "
        "against 3.3% expected, about z=3 - so unlike day 15 (165, z=41) and "
        "31 December (188, z=55) the evidence does NOT establish a convention. "
        "Downgrading 28 opening dates on a z=3 signal would invent uncertainty, "
        "which is the same error as inventing a date. Left as recorded, named "
        "here, and it needs an owner ruling or a second source, not a "
        "threshold.",
    ("gaming.csv", "close_date"):
        "OPEN, same as open_date: 10 of 57 on day 1, same vendor, same "
        "unresolved question.",
}


def out(s=""):
    sys.stdout.write(str(s).encode("ascii", "replace").decode() + "\n")


def _wrap(text, width):
    words, line, lines = text.split(), "", []
    for w in words:
        if line and len(line) + 1 + len(w) > width:
            lines.append(line)
            line = w
        else:
            line = f"{line} {w}".strip()
    if line:
        lines.append(line)
    return lines


def read_csv(p):
    with Path(p).open(encoding="utf-8-sig", errors="replace", newline="") as fh:
        return list(csv.DictReader(fh))


def write_csv(p, rows, fields):
    with Path(p).open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)


def month_end(y, m):
    return f"{y:04d}-{m:02d}-{calendar.monthrange(y, m)[1]:02d}"


def backup(p):
    p = Path(p)
    b = p.with_name(p.name + TAG)
    if not b.exists():
        shutil.copy2(p, b)
        out(f"  backed up -> {b.name}")
    return b


# ===========================================================================
# SWEEP - every ISO date column in dist/customer, against a per-day baseline
# ===========================================================================
def sweep():
    findings, explained = [], []
    for p in sorted(DIST.glob("*.csv")):
        if p.name == "MANIFEST.csv":
            continue
        with p.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
            rd = csv.reader(fh)
            header = next(rd)
            days = [Counter() for _ in header]
            vals = [Counter() for _ in header]
            for row in rd:
                for i, v in enumerate(row):
                    m = ISO.match(v.strip())
                    if m:
                        days[i][int(m.group(3))] += 1
                        vals[i][v.strip()] += 1
        for i, col in enumerate(header):
            n = sum(days[i].values())
            if n < 20:
                continue
            worst = max(((d, days[i].get(d, 0)) for d in PDAY),
                        key=lambda kv: (kv[1] - n * PDAY[kv[0]]) /
                        (math.sqrt(n * PDAY[kv[0]] * (1 - PDAY[kv[0]])) or 1.0))
            d, k = worst
            e = n * PDAY[d]
            sd = math.sqrt(n * PDAY[d] * (1 - PDAY[d])) or 1.0
            z = (k - e) / sd
            if z < Z_REPORT:
                continue
            top1v, top1n = vals[i].most_common(1)[0]
            rec = {"file": p.name, "column": col, "n_iso": n, "day": d, "count": k,
                   "pct": round(100.0 * k / n, 1), "expected": round(e, 1),
                   "z": round(z, 1), "distinct_values": len(vals[i]),
                   "top_value": top1v, "top_value_share": round(100.0 * top1n / n, 1)}
            why = next((w for pat, w in LEGITIMATE if pat.search(col)), None)
            if why:
                rec["explained_by"] = why
                explained.append(rec)
            else:
                findings.append(rec)
    findings.sort(key=lambda r: -r["z"])
    explained.sort(key=lambda r: -r["z"])
    return findings, explained


def cmd_sweep(write=False):
    out(f"1159 sweep - every ISO date column in dist/customer, {TODAY}")
    out("=" * 100)
    out("Baseline is PER DAY over the Gregorian cycle, not 1/30.44: days 1-28 occur")
    out("twelve times a year, the 30th eleven and the 31st SEVEN. A flat 1/30.44 was")
    out("the first draft's baseline and it inflated the expectation for day 31 by 74%.")
    out("")
    findings, explained = sweep()
    # A concentration is only an ALLEGATION when it sits on a day that is a
    # known placeholder convention. Day 16 is not one: `deals.Event_Date` has
    # 110 values there and 105 of them are two disclosed federal batch dates
    # (2019-12-16, a HUD award list; 2024-12-16, an NTIA release). Reporting
    # those beside a fabricated day would train the reader to ignore the list.
    shaped = [r for r in findings if r["day"] in PLACEHOLDER_DAYS]
    other = [r for r in findings if r["day"] not in PLACEHOLDER_DAYS]
    hdr = (f"{'file':22s} {'column':44s} {'n':>7s} {'day':>4s} {'cnt':>6s} "
           f"{'pct':>6s} {'exp':>8s} {'z':>7s}  most common value (share)")

    def table(rows):
        out(hdr)
        out("-" * len(hdr))
        for r in rows:
            out(f"{r['file']:22s} {r['column']:44s} {r['n_iso']:>7,} {r['day']:>4d} "
                f"{r['count']:>6,} {r['pct']:>5.1f}% {r['expected']:>8.1f} "
                f"{r['z']:>7.1f}  {r['top_value']} ({r['top_value_share']}%)")

    out(f"A. PLACEHOLDER-SHAPED concentrations - the worst day is one of "
        f"{sorted(PLACEHOLDER_DAYS)}, which are the mid-month and period-end "
        f"conventions. These are the allegations.")
    table(shaped)
    out("")
    out("   Adjudication of each, measured before it was written down:")
    unruled = 0
    for r in shaped:
        verdict = ADJUDICATED.get((r["file"], r["column"]))
        if verdict:
            out(f"   * {r['file']}:{r['column']}")
            for line in _wrap(verdict, 92):
                out(f"       {line}")
        else:
            unruled += 1
            out(f"   * {r['file']}:{r['column']}  -- NOT ADJUDICATED. This column "
                f"appeared after 2026-09-02; it needs a measured verdict here.")
    out(f"   ({len(shaped) - unruled} adjudicated, {unruled} awaiting one.)")
    out("")
    out("B. Concentrations on a day that is NOT a placeholder convention. Almost "
        "always a real batch: read the most-common-value column, which usually "
        "names it.")
    table(other)
    out(f"\n{len(shaped)} placeholder-shaped; {len(other)} on another day; "
        f"{len(explained)} explained by a named shape.")
    out("")
    out("EXPLAINED - the shape that produces the concentration, per column:")
    byreason = defaultdict(list)
    for r in explained:
        byreason[r["explained_by"]].append(f"{r['file']}:{r['column']}")
    for why, cols in sorted(byreason.items(), key=lambda kv: -len(kv[1])):
        out(f"  [{len(cols):3d}] {why}")
        out(f"        {', '.join(sorted(cols)[:6])}"
            + (f", +{len(cols) - 6} more" if len(cols) > 6 else ""))
    if write:
        SWEEP_JSON.write_text(json.dumps(
            {"built_by": "code/1159_date_placeholder_precision.py",
             "built_date": TODAY, "z_threshold": Z_REPORT,
             "unexplained": findings, "explained": explained},
            indent=2), encoding="utf-8")
        out(f"\nwrote {SWEEP_JSON.relative_to(CEDAR)}")
    return findings, explained


# ===========================================================================
# EDIT 1 - gaming
# ===========================================================================
VENDOR_BASIS = "Casino City"
GAMING_PLACEHOLDER_BASIS = (
    "measured 2026-09-02 by code/1159 in the vendor workbook itself "
    "(data/raw/external/gaming/directory_core/Tribal Property List.xlsx): of 553 "
    "non-empty 'Open Date' cells, 188 fall on 31 December and 165 on day 15, and "
    "of 142 '1st Close Date' cells 63 fall on day 15. Every cell is a real Excel "
    "datetime under number format [$-409]d-mmm-yyyy, so the placeholder day is "
    "the VENDOR's and was transcribed, not completed, by Cedar. The shipping "
    "open_date / close_date columns were already re-typed to the supported "
    "precision by code/158; this column exists so a consumer reading the "
    "verbatim value does not have to parse a 300-character basis string to "
    "learn that its day is not source-stated.")


def classify_gaming(verbatim, basis):
    v = (verbatim or "").strip()
    if not v:
        return ""
    m = ISO.match(v)
    if not m or VENDOR_BASIS not in (basis or ""):
        return "source_states_the_day"
    mo, d = int(m.group(2)), int(m.group(3))
    if mo == 12 and d == 31:
        return "vendor_year_end_placeholder_1231"
    if d == 15:
        return "vendor_mid_month_placeholder_day_15"
    return "source_states_the_day"


def edit_gaming(apply_it):
    rows = read_csv(GAMING)
    fields = list(rows[0].keys())
    stats = Counter()
    for r in rows:
        for fld in ("open_date", "close_date"):
            col = f"{fld}_source_value_placeholder"
            val = classify_gaming(r.get(f"{fld}_source_value_verbatim"),
                                  r.get(f"{fld}_basis"))
            r[col] = val
            r[f"{col}_basis"] = GAMING_PLACEHOLDER_BASIS if val.startswith("vendor_") else ""
            stats[f"{fld}:{val or '(no verbatim value)'}"] += 1
    for fld in ("open_date", "close_date"):
        for col in (f"{fld}_source_value_placeholder",
                    f"{fld}_source_value_placeholder_basis"):
            if col not in fields:
                anchor = f"{fld}_source_value_verbatim"
                fields.insert(fields.index(anchor) + 1
                              if anchor in fields else len(fields), col)
    out("EDIT 1 - gaming_facilities.csv")
    for k, v in sorted(stats.items()):
        out(f"  {k}: {v}")
    if apply_it:
        backup(GAMING)
        write_csv(GAMING, rows, fields)
        out(f"  wrote {len(rows)} rows, {len(fields)} columns")
    return stats


# ===========================================================================
# EDIT 2 - deals
# ===========================================================================
# Every pattern is matched against the row's OWN Date_Basis. Order matters:
# FISCAL-YEAR is tested before YEAR because "FISCAL-YEAR PLACEHOLDER" contains
# the word YEAR and means something different.
DEALS_RULES = (
    ("fiscal_year", re.compile(r"fiscal[- ]year(-end)?\s+placeholder|"
                               r"during the year ended", re.I)),
    ("month", re.compile(r"month-level|mid-month placeholder", re.I)),
    ("year", re.compile(r"year-level", re.I)),
    ("approximate", re.compile(r"approximate/first-pass", re.I)),
)


def classify_deal(basis):
    b = basis or ""
    for name, pat in DEALS_RULES:
        if pat.search(b):
            return name
    return ""


def edit_deals(apply_it):
    """IDEMPOTENT. The second run of this pass must be a no-op, and the first
    draft was not: after a row had been re-typed to `2001-03`, `ISO.match`
    failed, every branch fell through, and 75 month-precision rows were
    re-classified `unparseable` with their verbatim value blanked. Caught by
    running `apply` twice - which is now a fixture, because a pass that
    destroys its own output on re-run is worse than one that never ran, and
    `build.py` re-runs every PHASE 2 enricher after any rebuild.

    The fix has two halves: read the ALREADY-RETYPED value back through
    `YM`/`YONLY` as well as `ISO`, and never overwrite a verbatim value that a
    previous run already recorded."""
    rows = read_csv(DEALS)
    fields = list(rows[0].keys())
    stats = Counter()
    changed_examples = []
    for r in rows:
        ed = (r.get("Event_Date") or "").strip()
        kind = classify_deal(r.get("Date_Basis"))
        m = ISO.match(ed)
        prior = (r.get("Event_Date_source_value_verbatim") or "").strip()
        # already re-typed by an earlier run of this same pass
        ym, yo = YM.match(ed), YONLY.match(ed)
        prec = cls = nb = na = ""
        note = ""
        verbatim = ""
        if not ed:
            cls, prec = "absent", ""
            note = ("Event_Date is blank; Date_Basis states why. No date is "
                    "asserted.")
        elif kind == "month" and (m or ym):
            g = m or ym
            y, mo = int(g.group(1)), int(g.group(2))
            verbatim = prior or (ed if m else "")
            r["Event_Date"] = f"{y:04d}-{mo:02d}"
            cls, prec = "exact", "month"
            nb, na = f"{y:04d}-{mo:02d}-01", month_end(y, mo)
            note = ("the row's own Date_Basis states the source gives a month "
                    "and no day; the day carried here was a mid-month "
                    "placeholder and has been withdrawn")
            if m:
                stats["Event_Date re-typed to month precision"] += 1
                if len(changed_examples) < 3:
                    changed_examples.append(
                        f"{r.get('Deal_ID')}: {ed} -> {r['Event_Date']}")
            else:
                stats["already month precision from an earlier run - unchanged"] += 1
        elif kind == "year" and (m or ym or yo):
            g = m or ym or yo
            y = int(g.group(1))
            verbatim = prior or (ed if m else "")
            r["Event_Date"] = f"{y:04d}"
            cls, prec = "exact", "year"
            nb, na = f"{y:04d}-01-01", f"{y:04d}-12-31"
            note = ("the row's own Date_Basis states the source gives a year "
                    "and no month or day; both were placeholders and have been "
                    "withdrawn")
            stats["Event_Date re-typed to year precision" if m else
                  "already year precision from an earlier run - unchanged"] += 1
            for c in ("Event_Quarter", "Event_Month"):
                if (r.get(c) or "").strip():
                    r[c] = ""
                    stats[f"{c} blanked - a year-precision source cannot determine it"] += 1
        elif kind == "year":
            y = (r.get("Event_Year") or "").strip()
            cls, prec = "exact", "year"
            if re.match(r"^\d{4}$", y):
                nb, na = f"{y}-01-01", f"{y}-12-31"
            note = ("Event_Date is blank and Date_Basis states a year only; the "
                    "year is in Event_Year")
            for c in ("Event_Quarter", "Event_Month"):
                if (r.get(c) or "").strip():
                    r[c] = ""
                    stats[f"{c} blanked - a year-precision source cannot determine it"] += 1
        elif kind == "fiscal_year":
            cls, prec = "fiscal_year_end_placeholder", "unknown_within_fiscal_year"
            note = ("Date_Basis states the value is a FISCAL-YEAR placeholder: it "
                    "is the reporting period's end, not the event's date, and "
                    "where the entity's fiscal year is not the calendar year the "
                    "calendar year is not determined either. NOT re-typed - the "
                    "value is left exactly as recorded and this column is the "
                    "warning. Bounds are left empty rather than invented.")
            stats["classified as a fiscal-year-end placeholder, value untouched"] += 1
        elif kind == "approximate":
            cls, prec = "approximate", "unknown"
            note = ("Date_Basis says 'Approximate/first-pass date' without saying "
                    "WHICH component is approximate, so no precision can be "
                    "derived and none is asserted")
            stats["classified as approximate, precision not derivable"] += 1
        elif m:
            cls, prec = "exact", "day"
            nb = na = ed
            note = "Date_Basis asserts no lower precision; the day is taken as stated"
            stats["day precision retained"] += 1
        elif ym or yo:
            g = ym or yo
            y = int(g.group(1))
            if ym:
                mo = int(g.group(2))
                cls, prec = "exact", "month"
                nb, na = f"{y:04d}-{mo:02d}-01", month_end(y, mo)
            else:
                cls, prec = "exact", "year"
                nb, na = f"{y:04d}-01-01", f"{y:04d}-12-31"
            note = ("Event_Date is recorded at less than day precision and "
                    "Date_Basis does not say why; the value is taken at the "
                    "precision it is written to and nothing is completed")
            stats[f"partial ISO value taken at {prec} precision"] += 1
        else:
            cls, prec = "unparseable", ""
            note = f"Event_Date {ed!r} does not parse as a date"
            stats["Event_Date unparseable"] += 1

        r["Event_Date_source_value_verbatim"] = verbatim or prior
        r["Event_Date_class"] = cls
        r["Event_Date_precision"] = prec
        r["Event_Date_not_before"] = nb
        r["Event_Date_not_after"] = na
        r["Event_Date_precision_basis"] = (
            f"derived {TODAY} by code/1159 from this row's own Date_Basis: {note}."
            if note else "")

    new = ("Event_Date_source_value_verbatim", "Event_Date_class",
           "Event_Date_precision", "Event_Date_not_before",
           "Event_Date_not_after", "Event_Date_precision_basis")
    anchor = fields.index("Event_Date") + 1 if "Event_Date" in fields else len(fields)
    for i, c in enumerate(new):
        if c not in fields:
            fields.insert(anchor + i, c)

    out("EDIT 2 - deals_classified.csv")
    for k, v in sorted(stats.items()):
        out(f"  {k}: {v}")
    for e in changed_examples:
        out(f"  e.g. {e}")
    if apply_it:
        backup(DEALS)
        write_csv(DEALS, rows, fields)
        out(f"  wrote {len(rows)} rows, {len(fields)} columns")
    return stats


# ===========================================================================
# CODEBOOK. A new customer-facing column with no codebook row is an undocumented
# column, and `codebook_variables` in 62 is how that is caught. Fragments are
# hand-maintained and merged by `py -3 code/cedar_codebook.py build`, so this is
# ADDITIVE: a row that already exists is amended by APPENDING a sentence, never
# rewritten, because another workstream's text lives in the same file.
# ===========================================================================
CB = CLEAN / "codebook"
MARK = "  [1159, 2026-09-02]"

NEW_GAMING_CB = [
    ("open_date_source_value_placeholder", "text", "public",
     "Whether the day carried in `open_date_source_value_verbatim` is a "
     "placeholder the SOURCE wrote, and which one. `vendor_mid_month_"
     "placeholder_day_15` (148 rows), `vendor_year_end_placeholder_1231` (147), "
     "`source_states_the_day` (44), blank where there is no verbatim value. "
     "Measured in the vendor workbook itself, not inferred from our own file: "
     "of 553 non-empty 'Open Date' cells in the Casino City Tribal Property "
     "List, 188 fall on 31 December and 165 on day 15, every one a real Excel "
     "datetime under number format [$-409]d-mmm-yyyy. So the day is the "
     "vendor's and was transcribed, not completed, by Cedar. This column "
     "exists because the shipping `open_date` was already re-typed to the "
     "supported precision while the verbatim value was not, and nothing on the "
     "row said so outside a 300-character basis string."),
    ("open_date_source_value_placeholder_basis", "text", "public",
     "The measurement behind `open_date_source_value_placeholder`, stated in "
     "full on every row that carries a vendor placeholder."),
    ("close_date_source_value_placeholder", "text", "public",
     "The same for `close_date_source_value_verbatim`: "
     "`vendor_mid_month_placeholder_day_15` (59 rows), "
     "`vendor_year_end_placeholder_1231` (17)."),
    ("close_date_source_value_placeholder_basis", "text", "public",
     "The measurement behind `close_date_source_value_placeholder`."),
    ("open_date_source_value_verbatim", "text", "public",
     "The source's own date value for the opening, kept exactly as recorded, "
     "before `code/158` re-typed `open_date` to the precision the source "
     "actually supports. It is NOT the column to parse: 148 of its 339 values "
     "carry the vendor's mid-month placeholder day and 147 its year-end "
     "placeholder. Read `open_date_source_value_placeholder` to know which, "
     "and `open_date_not_before` / `open_date_not_after` for the interval."),
    ("close_date_source_value_verbatim", "text", "public",
     "The source's own date value for the closing, kept exactly as recorded. "
     "Same caveat as `open_date_source_value_verbatim`: 59 of its 76 values "
     "carry the vendor's mid-month placeholder day."),
]

NEW_DEALS_CB = [
    ("Event_Date_class", "text", "public",
     "What kind of thing `Event_Date` is. `exact` the row's basis supports the "
     "value at the stated precision; `fiscal_year_end_placeholder` the value is "
     "a reporting period's end standing in for an unknown event date and is NOT "
     "an event date (10 rows); `approximate` the basis says the date is "
     "approximate without saying which component; `absent` no date is asserted; "
     "`unparseable`. Derived from the row's own `Date_Basis` by `code/1159`."),
    ("Event_Date_precision", "text", "public",
     "How precise `Event_Date` actually is: `day`, `month`, `year`, "
     "`unknown_within_fiscal_year` or `unknown`. Derived ONLY from what the "
     "row's own `Date_Basis` already states - nothing was re-sourced and no "
     "precision was guessed."),
    ("Event_Date_not_before", "date", "public",
     "Earliest date the event can have occurred, given the precision. Parse "
     "this and `Event_Date_not_after` rather than `Event_Date` when you need a "
     "uniform ISO interval. Empty where the basis cannot bound it - an empty "
     "bound is not a zero-width one."),
    ("Event_Date_not_after", "date", "public",
     "Latest date the event can have occurred, given the precision."),
    ("Event_Date_source_value_verbatim", "text", "public",
     "The full ISO value `Event_Date` carried before `code/1159` withdrew a "
     "placeholder day or month that the row's own `Date_Basis` said the source "
     "did not state. 77 rows. Blank where nothing was withdrawn."),
    ("Event_Date_precision_basis", "text", "public",
     "Why this row has the precision it has, quoting what its `Date_Basis` "
     "established. Every precision can be audited back to one sentence."),
]

GAMING_AMEND = {
    "open_date": (
        "AMENDED 2026-09-02: the phrase 'as the source states it, unmodified' is "
        "no longer true of this column and has not been since `code/158` - a "
        "value whose own precision column says `year` or `month` was re-typed "
        "(`1985-04-15` -> `1985-04`) and the source's string was moved to "
        "`open_date_source_value_verbatim`. 6 of 636 values still end in `-15` "
        "and all six are hand-researched day-precision dates from non-vendor "
        "sources. OPEN QUESTION, not fixed: 28 of the 188 full-ISO values fall "
        "on day 1, 26 of them from the Casino City roster at day precision. Day "
        "1 is a third vendor placeholder shape, but the vendor workbook holds "
        "only 31 day-1 values in 553 (z about 3, against z=41 for day 15 and "
        "z=55 for 31 December), so the evidence does not establish a convention "
        "and nothing was downgraded. See `code/1159`."),
    "close_date": (
        "AMENDED 2026-09-02: same re-typing caveat as `open_date`, and the same "
        "unresolved day-1 question on 10 of its 57 full-ISO values. "
        "See `code/1159`."),
}

DEALS_AMEND = {
    "Event_Date": (
        "AMENDED 2026-09-02: NOT uniformly day-precision, and it never was. 77 "
        "values were full ISO dates whose own `Date_Basis` said the source gave "
        "only a month or only a year; those now read `YYYY-MM` or `YYYY` and "
        "the withdrawn string is in `Event_Date_source_value_verbatim`. Read "
        "`Event_Date_precision` before parsing, and "
        "`Event_Date_not_before`/`_not_after` for a uniform interval. 10 rows "
        "carry a fiscal-year end rather than an event date and say so in "
        "`Event_Date_class`. See `code/1159`."),
}


def _upsert(frag_name, dataset, new_rows, amend, n_rows, apply_it):
    p = CB / frag_name
    if not p.exists():
        out(f"  CODEBOOK: {frag_name} is absent - not created here, because a "
            f"fragment file this script did not expect is a coordination "
            f"question, not a gap to fill silently")
        return
    rows = read_csv(p)
    fields = list(rows[0].keys())
    have = {r["variable"]: r for r in rows}
    added = amended = 0
    for var, typ, tier, desc in new_rows:
        if var in have:
            r = have[var]
            if MARK not in (r.get("description") or ""):
                r["description"] = desc + MARK
                amended += 1
            continue
        rows.append({"dataset": dataset, "variable": var, "type": typ, "units": "",
                     "pct_filled": "", "n_rows": str(n_rows), "published": "1",
                     "access_tier": tier, "description": desc + MARK,
                     "generated": TODAY})
        added += 1
    for var, sentence in amend.items():
        r = have.get(var)
        if r and MARK not in (r.get("description") or ""):
            r["description"] = (r.get("description") or "").rstrip() + " " + sentence + MARK
            amended += 1
    out(f"  CODEBOOK {frag_name}: +{added} variables, {amended} amended "
        f"(now {len(rows)})")
    if apply_it and (added or amended):
        backup(p)
        write_csv(p, rows, fields)


def codebook(apply_it):
    out("CODEBOOK fragments (additive; merge with "
        "`py -3 code/cedar_codebook.py build`)")
    _upsert("07_gaming.csv", "07_gaming", NEW_GAMING_CB, GAMING_AMEND, 787, apply_it)
    _upsert("01_deals.csv", "01_deals", NEW_DEALS_CB, DEALS_AMEND, 1073, apply_it)


# ===========================================================================
def cmd_verify():
    fails = []

    # V1 - the gaming placeholder flag exists and finds the known population.
    g = read_csv(GAMING)
    if "open_date_source_value_placeholder" not in g[0]:
        fails.append("V1: gaming_facilities.csv has no "
                     "open_date_source_value_placeholder column")
        n15 = n1231 = 0
    else:
        n15 = sum(1 for r in g
                  if r["open_date_source_value_placeholder"]
                  == "vendor_mid_month_placeholder_day_15")
        n1231 = sum(1 for r in g
                    if r["open_date_source_value_placeholder"]
                    == "vendor_year_end_placeholder_1231")
        if n15 < 140:
            fails.append(f"V1: only {n15} open dates flagged as the vendor's "
                         f"mid-month placeholder; the measured population is 148")
        if n1231 < 140:
            fails.append(f"V1: only {n1231} open dates flagged as the vendor's "
                         f"year-end placeholder; the measured population is 147")
    out(f"V1 gaming verbatim flagged: day-15 {n15}, 12-31 {n1231}")

    # V2 - deals carries the precision machinery.
    d = read_csv(DEALS)
    need = ("Event_Date_class", "Event_Date_precision", "Event_Date_not_before",
            "Event_Date_not_after", "Event_Date_source_value_verbatim")
    missing = [c for c in need if c not in d[0]]
    if missing:
        fails.append(f"V2: deals_classified.csv is missing {missing}")
    out(f"V2 deals precision columns present: {not missing}")

    # V3 - THE INTENDED DELTA. Not a conservation check: no row whose own basis
    # says the day is not stated may still carry a day.
    still = [r for r in d
             if classify_deal(r.get("Date_Basis")) in ("month", "year")
             and ISO.match((r.get("Event_Date") or "").strip())]
    out(f"V3 deals rows whose basis denies the day and which still carry one: "
        f"{len(still)}")
    if still:
        for r in still[:3]:
            out(f"    {r.get('Deal_ID')}: {r.get('Event_Date')} | "
                f"{(r.get('Date_Basis') or '')[:80]}")
        fails.append(f"V3: {len(still)} deals rows still ship a placeholder day")

    # V4 - and the withdrawal actually HAPPENED, at a floor. A file in which
    # nothing was ever re-typed also passes V3.
    n_month = sum(1 for r in d if r.get("Event_Date_precision") == "month")
    n_year = sum(1 for r in d if r.get("Event_Date_precision") == "year")
    n_verb = sum(1 for r in d if (r.get("Event_Date_source_value_verbatim") or "").strip())
    out(f"V4 deals typed month {n_month}, year {n_year}; verbatim retained "
        f"{n_verb}")
    if n_month < 60:
        fails.append(f"V4: only {n_month} rows typed month-precision; the measured "
                     f"population of month-level disclosures is 88. A pass that "
                     f"typed nothing would satisfy V3.")
    if n_verb < 60:
        fails.append(f"V4: only {n_verb} rows retained a verbatim source value; "
                     f"a re-type that keeps no verbatim value has lost evidence")

    # V5 - and no year-precision row asserts a quarter.
    q = [r for r in d if r.get("Event_Date_precision") == "year"
         and (r.get("Event_Quarter") or "").strip()]
    out(f"V5 year-precision deals rows still asserting a quarter: {len(q)}")
    if q:
        fails.append(f"V5: {len(q)} year-precision rows still carry Event_Quarter")

    # V6 - IDEMPOTENCE, in the direction that actually broke. Re-deriving from
    # the live file must reproduce the live file. `build.py` re-runs every
    # PHASE 2 enricher after any rebuild, so a pass that is not a no-op on its
    # own output destroys its work the second time it is invoked - which is what
    # happened here on 2026-09-02: 75 month-precision rows became `unparseable`
    # and 77 verbatim values were blanked.
    redo = read_csv(DEALS)
    changed = 0
    for r in redo:
        ed, kind = (r.get("Event_Date") or "").strip(), classify_deal(r.get("Date_Basis"))
        if kind in ("month", "year") and ISO.match(ed):
            changed += 1
        if kind == "month" and not (YM.match(ed) or ISO.match(ed)):
            changed += 1
    n_unparse = sum(1 for r in d if r.get("Event_Date_class") == "unparseable")
    out(f"V6 rows a re-run would change: {changed}; rows typed `unparseable`: "
        f"{n_unparse}")
    if n_unparse:
        fails.append(f"V6: {n_unparse} rows are typed `unparseable`. In this table "
                     f"that is the signature of a non-idempotent second run "
                     f"reading its own YYYY-MM output as a broken date.")

    out("")
    if fails:
        for f in fails:
            out("FAIL  " + f)
        return 1
    out("PASS  all six invariants")
    return 0


def cmd_fixtures():
    """Prove each invariant FIRES."""
    import contextlib
    import io

    orig_d = DEALS.read_bytes()
    orig_g = GAMING.read_bytes()

    def run():
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = cmd_verify()
        return rc, buf.getvalue()

    results = []
    try:
        rc, _ = run()
        results.append(("baseline PASS", rc == 0, f"exit {rc}"))

        # V3 + V4: put a placeholder day back on one disclosed row.
        rows = read_csv(DEALS)
        fields = list(rows[0].keys())
        hit = next(r for r in rows if r.get("Event_Date_precision") == "month")
        hit["Event_Date"] = hit["Event_Date_source_value_verbatim"]
        write_csv(DEALS, rows, fields)
        rc, txt = run()
        results.append(("V3 fires when one re-typed day is put back",
                        rc == 1 and "V3:" in txt, f"exit {rc}"))
        DEALS.write_bytes(orig_d)

        # V4: strip every derived precision - the no-op case.
        rows = read_csv(DEALS)
        for r in rows:
            r["Event_Date_precision"] = ""
            r["Event_Date_source_value_verbatim"] = ""
        write_csv(DEALS, rows, fields)
        rc, txt = run()
        results.append(("V4 fires when the pass typed nothing (the no-op case)",
                        rc == 1 and "V4:" in txt, f"exit {rc}"))
        DEALS.write_bytes(orig_d)

        # V5: assert a quarter on a year-precision row.
        rows = read_csv(DEALS)
        hit = next(r for r in rows if r.get("Event_Date_precision") == "year")
        hit["Event_Quarter"] = "Q3"
        write_csv(DEALS, rows, fields)
        rc, txt = run()
        results.append(("V5 fires when a year-precision row asserts a quarter",
                        rc == 1 and "V5:" in txt, f"exit {rc}"))
        DEALS.write_bytes(orig_d)

        # V6: the real 2026-09-02 defect - run `apply` a second time and check
        # the file survives it. This is the fixture the bug is named after.
        edit_deals(True)
        edit_gaming(True)
        rc, txt = run()
        results.append(("a SECOND apply leaves the tables intact (idempotence)",
                        rc == 0, f"exit {rc}"))
        after = read_csv(DEALS)
        n_month2 = sum(1 for r in after if r.get("Event_Date_precision") == "month")
        n_verb2 = sum(1 for r in after
                      if (r.get("Event_Date_source_value_verbatim") or "").strip())
        results.append((f"a SECOND apply keeps 75 month rows and 77 verbatim "
                        f"values (got {n_month2}/{n_verb2})",
                        n_month2 >= 60 and n_verb2 >= 60,
                        f"{n_month2} month, {n_verb2} verbatim"))
        DEALS.write_bytes(orig_d)
        GAMING.write_bytes(orig_g)

        # V1: blank the gaming flag.
        grows = read_csv(GAMING)
        gfields = list(grows[0].keys())
        for r in grows:
            r["open_date_source_value_placeholder"] = ""
        write_csv(GAMING, grows, gfields)
        rc, txt = run()
        results.append(("V1 fires when the gaming placeholder flag is empty",
                        rc == 1 and "V1:" in txt, f"exit {rc}"))
        GAMING.write_bytes(orig_g)
    finally:
        DEALS.write_bytes(orig_d)
        GAMING.write_bytes(orig_g)

    rc, _ = run()
    results.append(("restored, PASS again", rc == 0, f"exit {rc}"))

    out("1159 fixtures - each invariant must FIRE on an injected violation")
    out("=" * 78)
    bad = 0
    for name, ok, detail in results:
        out(f"  [{'ok ' if ok else 'FAIL'}] {name}  ({detail})")
        bad += 0 if ok else 1
    out("")
    out("all fixtures fired" if not bad else f"{bad} fixture(s) did not fire")
    return 0 if not bad else 1


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "report"
    if cmd == "sweep":
        cmd_sweep(write=False)
        return 0
    if cmd == "report":
        cmd_sweep(write=False)
        out("")
        out("=" * 100)
        edit_gaming(False)
        out("")
        edit_deals(False)
        out("")
        codebook(False)
        out("\nDRY RUN. Nothing was written. Use `apply`.")
        return 0
    if cmd == "apply":
        cmd_sweep(write=True)
        out("")
        out("=" * 100)
        edit_gaming(True)
        out("")
        edit_deals(True)
        out("")
        codebook(True)
        return 0
    if cmd == "verify":
        return cmd_verify()
    if cmd == "fixtures":
        return cmd_fixtures()
    out(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
