#!/usr/bin/env python3
"""
106_build_revenue_bounds.py -- Cedar Press. The gaming revenue BOUNDS layer.

WHY THIS EXISTS
---------------
Elijah, 2026-08-07: "maybe sometimes we can process of eliminate revenue too
and attribute it."

Right in principle, and the measurement is the whole point. Cedar holds
property-level gaming revenue for EXACTLY TWO properties -- Connecticut's
Foxwoods and Mohegan Sun, from the CT Department of Consumer Protection slot
series. New Mexico's 1,072 `net_win` rows are TRIBE level, Michigan's 28 are
tribe level. So full residual elimination cannot run: you cannot solve for the
88th Sacramento operation knowing none of the other 87.

What IS derivable today is arithmetic on published figures, and there is a lot
of it. Four constraint types, none of them a model:

  1. REGIONAL CEILING. No property's gaming GGR exceeds its NIGC region-year
     total. A ceiling is NOT an estimate and is NEVER divided by the operation
     count into a per-property figure -- NIGC's own distribution proves why
     (see 2, below).
  2. BAND CONSTRAINTS. NIGC publishes, for FY2022-FY2025 only, the share of
     operations and the share of revenue in each of five revenue bands. That
     bounds the SET even where no property can be named. It is published,
     it was unused, and it constrains everything downstream.
  3. SINGLE-PROPERTY ATTRIBUTION. Where a tribe operated exactly one gaming
     property in the period, a tribe-level GAMING revenue figure is that
     property's revenue -- subject to all three tests in
     `cedar_domain.may_attribute_to_single_property`.
  4. RESIDUAL, where it closes. `regional_total - known_sum` bounds the sum of
     the unknown operations from above, always. It gives a POINT only when a
     single operation remains unknown, which today happens nowhere.

WHAT THIS FILE MAY NEVER CONTAIN
--------------------------------
- A modelled property revenue. No allocation of a regional total, no
  volume x price, no per-operation mean.
- The words "estimate", "predicted" or "confidence interval". A factual bound
  is not a confidence interval; a confidence interval requires a statistical
  model and this project is not building one. Enforced by BANNED_WORDS below.
- A silent promotion of an inference to an observation.
  `cedar_domain.may_promote(DERIVED_BOUND, ACTIVE_FLOOR_COUNT)` is False and is
  asserted at runtime.

REVENUE CONCEPTS DO NOT AGREE, AND THE DIFFERENCE IS LOAD-BEARING
-----------------------------------------------------------------
  NIGC GGR              gaming win, all games, before every expense
  CT DCP "Win (9)"      SLOT win only. Excludes table games. Foxwoods and
                        Mohegan Sun both run large table operations, so the CT
                        figure is a FLOOR on the property's GGR, not a match.
  NM net win            Class III tribe-level net win from the Gaming Control
                        Board's quarterly revenue-sharing releases.
  MI derived net win    payment / compact rate, Class III ELECTRONIC games only.

A bound built from one concept against another must say which way it can be
wrong. Every row here does, in `assumption_note`.

INPUTS  (all read-only; this script edits none of them)
  data/clean/nigc_regional_ggr.csv          198 region-years FY2001-FY2025
  data/clean/nigc_region_assignments.csv    2,438 property-region assignments
  data/clean/gaming_facilities.csv          774 properties
  data/clean/gaming_capacity_official.csv   net_win rows (CT/NM/MI)
  review/nigc_roster_diff_2026-08-06.csv    140 NIGC properties Cedar lacks
  data/raw/external/nigc/ggr_reports/*.pdf  24 NIGC GGR reports
  data/spine/cedar_entity_spine.csv         via resolve_entity

OUTPUTS
  data/clean/nigc_revenue_bands.csv
  data/clean/gaming_revenue_bounds.csv
  docs/REVENUE_BOUNDS_LOG.md
  docs/codebooks/07d_revenue_bounds.md
  review/revenue_bounds_single_property_refusals_2026-08-07.csv

RUN
  py -3 code/106_build_revenue_bounds.py
"""

import csv
import importlib.util
import json
import math
import re
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

CEDAR = Path(__file__).resolve().parent.parent
CLEAN = CEDAR / "data" / "clean"
RAW = CEDAR / "data" / "raw" / "external" / "nigc"
SPINE = CEDAR / "data" / "spine"
REVIEW = CEDAR / "review"
DOCS = CEDAR / "docs"
TODAY = date.today().isoformat()

NIGC_GGR_LANDING = "https://www.nigc.gov/downloads/gross-gaming-revenue-reports/"

sys.path.insert(0, str(CEDAR / "code"))
from cedar_keys import surrogate_id                            # noqa: E402

# --------------------------------------------------------------------------
# THE PRIMARY KEY OF nigc_revenue_bands.csv, AND WHAT IT IS MADE OF
#
# `band_id` used to be `f"NIGCBAND-{fy}-{i+1}"`. `fy` is stated by NIGC; `i`
# was the loop counter over `BAND_EDGES`. That was ALREADY very nearly
# deterministic - `i+1` is written into the row as `band_ordinal` - and it is
# migrated for one reason: an id whose stability depends on a constant list
# never being reordered is an id whose stability is a promise, not a property.
#
# It is now a deterministic blake2b digest of the three things NIGC prints
# about a band: the FISCAL YEAR, its ORDINAL in the schedule, and the LABEL
# NIGC gives it ("$25M to $50M"). Measured 2026-08-26: unique over all 20
# rows, 0 blank.
# --------------------------------------------------------------------------
NIGC_BAND_KEY_COLUMNS = ["fiscal_year", "band_ordinal", "band_label"]

# Never write these. A bound is a fact about arithmetic; these words claim a
# model we do not have.
BANNED_WORDS = ("estimate", "estimated", "estimation", "predict", "predicted",
                "prediction", "confidence interval", "forecast", "imputed",
                "modelled", "modeled")


# =========================================================================
# SHARED CODE - one resolver, one domain vocabulary (standing rule 8)
# =========================================================================
def _load(modname, filename):
    spec = importlib.util.spec_from_file_location(modname, CEDAR / "code" / filename)
    m = importlib.util.module_from_spec(spec)
    sys.modules[modname] = m
    spec.loader.exec_module(m)
    return m


M33 = _load("cedar33", "33_apply_party_rulings.py")
DOMAIN = _load("cedar_domain", "cedar_domain.py")

resolve_entity = M33.resolve_entity
REVENUE_EVIDENCE = DOMAIN.REVENUE_EVIDENCE
MeasurementType = DOMAIN.MeasurementType
may_promote = DOMAIN.may_promote
SINGLE_PROPERTY_ATTRIBUTED = DOMAIN.SINGLE_PROPERTY_ATTRIBUTED
SINGLE_PROPERTY_NOTE = DOMAIN.SINGLE_PROPERTY_NOTE
may_attribute_to_single_property = DOMAIN.may_attribute_to_single_property

# `SINGLE_PROPERTY_ATTRIBUTED` is deliberately NOT inside REVENUE_EVIDENCE:
# cedar_domain says so in as many words -- "it produces its own measurement
# status, never a silent upgrade to REPORTED_PROPERTY_REVENUE". The published
# vocabulary for this file is therefore the hierarchy plus that one status.
ALLOWED_STATUS = set(REVENUE_EVIDENCE) | {SINGLE_PROPERTY_ATTRIBUTED}


def read_csv(path):
    with open(path, newline="", encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


# --- REGENERATE GUARD (ADR-017, 2026-09-02) --------------------------------
def _carry_live_columns(path, canonical):
    """Derive this writer's header instead of declaring it.

    A wholesale writer holding a FIXED `fieldnames` list deletes every column
    an in-place enricher added since - no error, no exception, a diff nobody
    reads. Canonical order first so column order stays stable, then whatever
    the live file already carries. A retired column stays retired because it
    is not on disk; a promoted column survives because it is.

    THIS BUILD CANNOT REPOPULATE AN ENRICHER'S COLUMN. Carried columns are
    written BLANK and NAMED on stdout, which is strictly better than deleted:
    the schema survives and the enricher can refill them. Re-run the enricher
    after this build - `cedar_pipeline.enrichers_to_rerun(<table>)` names it.
    """
    import csv as _csv
    import os as _os
    canonical = list(canonical)
    _p = str(path)
    if not _os.path.exists(_p):
        return canonical
    with open(_p, encoding="utf-8-sig", newline="", errors="replace") as _fh:
        _live = next(_csv.reader(_fh), [])
    _extra = [c for c in _live if c and c not in canonical]
    if _extra:
        print("  [regenerate guard] %s: carrying %d enricher column(s) through "
              "this rebuild, BLANK - re-run the enricher: %s"
              % (_os.path.basename(_p), len(_extra), ", ".join(_extra)))
    return canonical + _extra


def write_csv(path, rows, cols):
    # REGENERATE GUARD (ADR-017, 2026-09-02): derive the header, do not declare it.
    cols = _carry_live_columns(path, cols)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)
    print(f"  wrote {path.name}: {len(rows):,} rows")


def num(x):
    try:
        if x is None or str(x).strip() == "":
            return None
        return float(str(x).replace(",", "").replace("$", ""))
    except ValueError:
        return None


def yr(x):
    v = num(x)
    return int(v) if v is not None else None


def banned_scan(rows, label):
    """A guard, not a formality. The rule is only real if it is enforced."""
    hits = []
    for i, r in enumerate(rows):
        blob = " ".join(str(v) for v in r.values()).lower()
        for w in BANNED_WORDS:
            if w in blob:
                hits.append((i, w))
    if hits:
        raise SystemExit(f"BANNED WORD in {label}: {hits[:5]}")
    print(f"  [PASS] {label}: no modelling vocabulary in {len(rows):,} rows")


# =========================================================================
# 1. BAND TABLES - the highest-value new extraction here
# =========================================================================
#
# NIGC's "REVENUE BY RANGE" chart appears in the FY2022, FY2023, FY2024 and
# FY2025 full GGR reports and in NO other document on disk (the other 20 are
# region tables and distribution maps; grep for "range"/"$25" returns nothing
# in any of them). Five bands, two series.
#
# The DATA LABELS are real text and are read out of the PDF here.
# The AXIS CATEGORY LABELS are outlined vector art and carry no text layer, so
# they were read off a 220-dpi render of the chart by hand on 2026-08-07 and
# are recorded below as BAND_EDGES. All four years use the same five bands.
# `chart_label_basis` on every row says so, so no reader mistakes a
# hand-verified label for an extracted one.
#
# The pairing rule: within a band, the % of Operations label sits left of the
# % of Revenue label. Verified three ways -- x-ordering, the printed callouts
# ("<$25M = 5%", ">$250M = 56%"), and the prose sentence naming the >$250M
# share. Both series are then checked to sum to 100 within rounding.

BAND_EDGES = [
    ("<$25M", None, 25_000_000),
    ("$25-50M", 25_000_000, 50_000_000),
    ("$50-100M", 50_000_000, 100_000_000),
    ("$100-250M", 100_000_000, 250_000_000),
    ("$250M+", 250_000_000, None),
]

BAND_REPORTS = [
    # (fiscal_year, pdf filename, report title, national operation count,
    #  verbatim sentence carrying the operation count)
    (2022, "GGRFY22_071923_Final.pdf",
     "FY 2022 Gross Gaming Revenue Report",
     519,
     "ed from the audited financial statements of 519 gaming operations, made up of 244"),
    (2023, "GGR23_Final.pdf",
     "FY 2023 Gross Gaming Revenue Report",
     527,
     "ed from the audited financial statements of 527 gaming operations, made up of"),
    (2024, "GGR24_080425.pdf",
     "FY 2024 Gross Gaming Revenue Report",
     532,
     "ed from the audited financial statements of 532 gaming operations, made up of 243"),
    (2025, "GGR25_071526.pdf",
     "FY 2025 Gross Gaming Revenue Report",
     545,
     "the audited financial statements of 545 gaming operations, facilities operated by nearly"),
]

# Hand-read from the rendered charts on 2026-08-07. The extractor below must
# reproduce these exactly or the build stops. This is the "hand-checked beats
# automated" rule applied to a chart whose axis has no text layer.
BAND_EXPECTED = {
    2022: ([55.0, 13.0, 11.0, 13.0, 8.0], [5.0, 6.0, 10.0, 29.0, 51.0]),
    2023: ([55.0, 14.0, 11.0, 11.0, 9.0], [5.0, 6.0, 10.0, 24.0, 55.0]),
    2024: ([54.3, 14.1, 11.7, 11.5, 8.5], [4.9, 5.9, 10.1, 24.5, 54.5]),
    2025: ([54.3, 13.8, 11.2, 12.1, 8.6], [4.8, 5.6, 9.3, 24.4, 55.8]),
}


def extract_band_chart(pdf_path):
    """Read the REVENUE BY RANGE chart's data labels and their x positions."""
    import pdfplumber
    with pdfplumber.open(pdf_path) as pdf:
        for pageno, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""
            if "REVENUE BY RANGE" not in text.upper():
                continue
            words = page.extract_words()
            # Data labels live inside the plot area. The callout block below it
            # ("<$25M = 5%") sits at top > 500 and must not be swept in.
            labels = [(w["x0"], float(w["text"].rstrip("%")))
                      for w in words
                      if re.fullmatch(r"\d{1,2}(\.\d)?%", w["text"])
                      and w["top"] < 470]
            if len(labels) != 10:
                continue
            labels.sort(key=lambda t: t[0])
            ops = [labels[i][1] for i in range(0, 10, 2)]
            rev = [labels[i][1] for i in range(1, 10, 2)]
            prose = " ".join(text.split())
            return pageno, ops, rev, prose
    raise SystemExit(f"no REVENUE BY RANGE chart found in {pdf_path.name}")


def build_bands():
    print("\n=== 1. NIGC REVENUE BAND TABLES ===")
    ggr = read_csv(CLEAN / "nigc_regional_ggr.csv")
    national_ggr = defaultdict(float)
    for r in ggr:
        national_ggr[yr(r["fiscal_year"])] += num(r["ggr_usd"]) or 0.0

    rows = []
    for fy, fname, title, nat_ops, ops_quote in BAND_REPORTS:
        pdf = RAW / "ggr_reports" / fname
        pageno, ops, rev, prose = extract_band_chart(pdf)

        exp_ops, exp_rev = BAND_EXPECTED[fy]
        if ops != exp_ops or rev != exp_rev:
            raise SystemExit(
                f"FY{fy} band chart disagrees with the hand-read values.\n"
                f"  extracted ops={ops} rev={rev}\n  hand-read  ops={exp_ops} rev={exp_rev}")
        for series, name in ((ops, "operations"), (rev, "revenue")):
            if not 99.0 <= sum(series) <= 101.0:
                raise SystemExit(f"FY{fy} {name} shares sum to {sum(series)}")

        # The report's own text must agree with the chart's end bands.
        # FY2022 hyphenates "Ap- proximately" across a line break, so anchor on
        # the clause rather than the first word.
        m = re.search(r"(\d+)% of gaming operations reported more than "
                      r"\$250 million of GGR in FY\s*" + str(fy), prose)
        if not m or abs(int(m.group(1)) - ops[4]) > 0.5:
            raise SystemExit(f"FY{fy}: prose >$250M operations share disagrees with chart")
        prose_quote = m.group(0)

        # Percentages are printed to 1 decimal from FY2024, to whole percent
        # before that. The rounding half-width is what turns a share into a
        # count RANGE; a single count would be a figure NIGC did not print.
        dec = any(abs(v - round(v)) > 1e-9 for v in ops + rev)
        prec = "0.1_percent" if dec else "1_percent"
        half = 0.05 if dec else 0.5

        nat_rev = national_ggr[fy]
        for i, (label, lo, hi) in enumerate(BAND_EDGES):
            po, pr = ops[i], rev[i]
            n_lo = max(0, math.ceil((po - half) / 100.0 * nat_ops))
            n_hi = math.floor((po + half) / 100.0 * nat_ops)
            g_lo = (pr - half) / 100.0 * nat_rev
            g_hi = (pr + half) / 100.0 * nat_rev
            band = {
                "band_id": "",         # set below, from THIS row's own facts
                "fiscal_year": fy,
                "band_ordinal": i + 1,
                "band_label": label,
                "band_lower_usd": "" if lo is None else int(lo),
                "band_upper_usd": "" if hi is None else int(hi),
                "pct_of_operations": po,
                "pct_of_revenue": pr,
                "pct_precision": prec,
                "national_operation_count": nat_ops,
                "national_ggr_usd": int(round(nat_rev)),
                "n_operations_implied_low": n_lo,
                "n_operations_implied_high": n_hi,
                "band_aggregate_ggr_implied_low_usd": int(round(g_lo)),
                "band_aggregate_ggr_implied_high_usd": int(round(g_hi)),
                "per_operation_upper_bound_usd": "" if hi is None else int(hi),
                "derivation_note": (
                    "Counts and aggregate dollars are the published share "
                    f"carried through its own rounding interval (+/-{half} "
                    "percentage points) against the operation count and the "
                    "national GGR total NIGC printed for the same year. NIGC "
                    "printed the shares, not the counts. The band tells you how "
                    "many operations sit in a range; it never tells you WHICH, "
                    "and it may not be turned into a figure for any named "
                    "property."),
                "chart_label_basis": (
                    "Data labels extracted from the PDF text layer. Band edge "
                    "labels are outlined vector art with no text layer and were "
                    "read off a 220-dpi render of the chart by hand on "
                    "2026-08-07; identical in all four years."),
                "source_url": NIGC_GGR_LANDING,
                "source_document": fname,
                "source_document_title": title,
                "source_page": pageno,
                "source_quote": prose_quote,
                "operation_count_source_quote": ops_quote,
                "confidence": "high",
                "tier": "B",
                "review_status": "pending_review",
                "fetched_date": "2026-08-06",
                "built_date": TODAY,
            }
            band["band_id"] = surrogate_id("NIGCBAND", band,
                                           NIGC_BAND_KEY_COLUMNS)
            rows.append(band)
        # Where the shares are printed to one decimal the implied counts are
        # determinate, and they must add back to NIGC's own operation count.
        # That is an independent confirmation of the pairing and the rounding
        # arithmetic, and it stops the build if it fails.
        mine = [r for r in rows if r["fiscal_year"] == fy]
        if all(r["n_operations_implied_low"] == r["n_operations_implied_high"]
               for r in mine):
            tot = sum(r["n_operations_implied_low"] for r in mine)
            if tot != nat_ops:
                raise SystemExit(
                    f"FY{fy}: band counts sum to {tot}, NIGC reports {nat_ops}")
            print(f"  FY{fy}: ops {ops} | rev {rev} | N={nat_ops} ops, "
                  f"${nat_rev/1e9:.1f}B  (page {pageno})  "
                  f"[band counts sum to {tot} = published total]")
        else:
            print(f"  FY{fy}: ops {ops} | rev {rev} | N={nat_ops} ops, "
                  f"${nat_rev/1e9:.1f}B  (page {pageno})  "
                  "[whole-percent shares: counts are ranges]")

    cols = list(rows[0].keys())
    banned_scan(rows, "nigc_revenue_bands.csv")
    write_csv(CLEAN / "nigc_revenue_bands.csv", rows, cols)
    return rows


# =========================================================================
# 2. PROPERTY COUNTS AND THE THREE SINGLE-PROPERTY CONDITIONS
# =========================================================================
STOP = {"casino", "resort", "hotel", "the", "and", "of", "at", "inc", "llc",
        "center", "centre", "gaming", "bingo", "lodge", "spa", "&"}


def name_core(s):
    s = (s or "").lower().replace("&", " and ")
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    return {t for t in s.split() if t and t not in STOP}


STREET_STOP = {"road", "rd", "street", "st", "avenue", "ave", "drive", "dr",
               "highway", "hwy", "boulevard", "blvd", "lane", "ln", "way",
               "north", "south", "east", "west", "n", "s", "e", "w", "box",
               "po", "p", "o", "suite", "exit", "us", "state", "county"}


def same_street_address(cedar_addr, nigc_addr):
    """Same house number and two or more shared street words.

    NIGC prints "54 Jemez Canyon Dam Rd., Bernalillo NM 87004" where Cedar
    holds "54 Jemez Canyon Dam Road" in Santa Ana Pueblo. The city strings
    disagree because a pueblo and its postal town are different names for the
    same place; the street address does not disagree at all.
    """
    a = re.sub(r"[^a-z0-9 ]+", " ", (cedar_addr or "").lower())
    b = re.sub(r"[^a-z0-9 ]+", " ", (nigc_addr or "").lower())
    na = re.match(r"\s*(\d+)\b", a)
    nb = re.match(r"\s*(\d+)\b", b)
    if not na or not nb or na.group(1) != nb.group(1):
        return False
    ta = {t for t in a.split() if t.isalpha() and t not in STREET_STOP}
    tb = {t for t in b.split() if t.isalpha() and t not in STREET_STOP}
    return len(ta & tb) >= 2


def load_facilities():
    fac = read_csv(CLEAN / "gaming_facilities.csv")
    out = []
    for f in fac:
        if (f.get("duplicate_of_facility_id") or "").strip():
            continue
        o = f.get("open_date") or ""
        c = f.get("close_date") or ""
        f["_open_year"] = yr(o[:4]) if o else None
        f["_close_year"] = yr(c[:4]) if c else None
        out.append(f)
    return out


def is_gaming_property(f, igra_by_fac):
    """Only gaming properties count toward a gaming property count."""
    if (f.get("property_type") or "").strip() == "Casino":
        return True
    st = igra_by_fac.get(f["facility_id"], set())
    return bool(st & {"VERIFIED_NIGC_OPERATION", "LIKELY_IGRA_OPERATION",
                      "CLOSED_IGRA_OPERATION", "MANAGED_BUT_NOT_OWNED"})


def open_in_year(f, year):
    """None = undeterminable. A missing open date is not an absent property."""
    oy, cy = f["_open_year"], f["_close_year"]
    if oy is None:
        return None
    if year < oy:
        return False
    if cy is not None and year > cy:
        return False
    return True


def build_property_counts(facs, igra_by_fac):
    """(tribe_id, year) -> (n_open, n_undeterminable, [facility_ids open])."""
    by_tribe = defaultdict(list)
    for f in facs:
        t = (f.get("tribe_id") or "").strip()
        if t and is_gaming_property(f, igra_by_fac):
            by_tribe[t].append(f)
    counts = {}
    for t, fs in by_tribe.items():
        for year in range(1988, 2027):
            openers, unknown = [], 0
            for f in fs:
                v = open_in_year(f, year)
                if v is None:
                    unknown += 1
                elif v:
                    openers.append(f["facility_id"])
            counts[(t, year)] = (len(openers), unknown, openers)
    return counts, by_tribe


def attribute_roster_gaps(spine, by_tribe, facs):
    """Read the NIGC roster diff for everything it says about our counts.

    Three findings come out of it, and they are not the same finding.

    1. ALIAS. The gaming spec is explicit: "A manufacturer or regulator using a
       different property name is an alias, not a second property." NIGC
       writing "Sandia Resort and Casino" where Cedar holds "Sandia Resort &
       Casino" in the same city is one property, not two. An alias does not
       defeat a property count.
    2. BLOCKING GAP. A NIGC operation that pins on a tribe and matches none of
       its held properties means our count for that tribe is short. Blocks.
    3. CLOSE-DATE CONFLICT. 37 properties Cedar records with a close_date are
       on NIGC's CURRENT gaming location map. NIGC's map is current, so the
       listing contradicts the close date, and every year after that date has
       an open-property count we cannot stand behind. Blocks from that year on.
       This is the check that caught Jicarilla: Cedar closes Wildhorse Casino
       in 2006 while NIGC still maps "Wild Horse Casino".
    """
    diff = read_csv(REVIEW / "nigc_roster_diff_2026-08-06.csv")
    fac_by_id = {f["facility_id"]: f for f in facs}
    gaps = [d for d in diff if d["outcome"] == "IN_NIGC_NOT_IN_CEDAR"]
    blocking = defaultdict(list)      # tribe_id -> [nigc names]
    aliases = defaultdict(list)
    unattributed_by_state = defaultdict(int)

    def alias_hit(core, addr, candidates):
        for f in candidates:
            fcore = name_core(f.get("facility_name"))
            if not (fcore and core):
                continue
            if not (fcore <= core or core <= fcore):
                continue
            city = (f.get("city") or "").lower().strip()
            if (city and city in addr) or same_street_address(f.get("address"), addr):
                return f
        return None

    for g in gaps:
        core = name_core(g.get("nigc_location_name"))
        addr = (g.get("nigc_address") or "").lower()
        state = g.get("state") or ""

        tid = (g.get("tribe_id") or "").strip()
        if not tid:
            nm = (g.get("tribe_canonical_name") or "").strip()
            if nm:
                tid, _, _ = resolve_entity(nm, spine)
                tid = tid or ""

        if tid:
            hit = alias_hit(core, addr, by_tribe.get(tid, []))
        else:
            # No tribe named on the diff row. Try to reach one through a held
            # property in the same state whose name and city agree - that both
            # identifies the tribe and proves the row is an alias.
            hit = alias_hit(core, addr,
                            [f for f in facs if (f.get("state") or "") == state])
            if hit:
                tid = (hit.get("tribe_id") or "").strip()

        if not tid:
            unattributed_by_state[state] += 1
            continue
        if hit:
            aliases[tid].append((g["nigc_location_name"], hit["facility_id"]))
        else:
            blocking[tid].append(g["nigc_location_name"])

    # ---- close-date conflicts on MATCHED rows -------------------------------
    closed_but_listed = defaultdict(list)   # tribe_id -> [(fid, name, year)]
    for d in diff:
        if d["outcome"] != "MATCHED":
            continue
        cd = (d.get("close_date") or "").strip()
        if not cd:
            continue
        m = re.search(r"(19|20)\d{2}", cd)
        if not m:
            continue
        f = fac_by_id.get(d.get("facility_id") or "")
        tid = (f.get("tribe_id") or "").strip() if f else ""
        if tid:
            closed_but_listed[tid].append(
                (d["facility_id"], d.get("facility_name") or "", int(m.group(0))))

    return (blocking, aliases, unattributed_by_state, len(gaps),
            closed_but_listed)


# =========================================================================
# 3. KNOWN REVENUE SERIES
# =========================================================================
def load_revenue_series():
    """Everything Cedar holds that is a revenue figure for a gaming operation.

    Returns two lists. `property_level` is revenue a source states for a named
    property. `tribe_level` is revenue a source states for a tribe.
    """
    rows = [r for r in read_csv(CLEAN / "gaming_capacity_official.csv")
            if r.get("metric") == "net_win"]

    # ---- property level: CT DCP monthly slot win, aggregated to NIGC FY.
    ct = defaultdict(list)
    for r in rows:
        if r.get("state") != "CT" or not (r.get("facility_id") or "").strip():
            continue
        ps = r.get("period_start") or ""
        if len(ps) < 7:
            continue
        y, m = int(ps[:4]), int(ps[5:7])
        fy = y + 1 if m >= 10 else y          # NIGC fiscal year, Oct-Sep
        ct[(r["facility_id"], r.get("tribe_id") or "", fy)].append(r)

    property_level = []
    for (fid, tid, fy), months in sorted(ct.items()):
        if len(months) != 12:                 # a partial year is not a year
            continue
        total = sum(num(m["value"]) or 0.0 for m in months)
        months.sort(key=lambda m: m["period_start"])
        property_level.append({
            "facility_id": fid, "tribe_id": tid, "fiscal_year": fy,
            "value": total, "n_periods": len(months),
            "facility_name": months[0].get("facility_name"),
            "concept": "connecticut_dcp_slot_machine_win",
            "source_url": months[0].get("source_url"),
            "source_authority": months[0].get("source_authority"),
            # All twelve quotes, not the first. A single month's quote against
            # a twelve-month total would read as a citation for a figure the
            # source never printed.
            "source_quote": " | ".join(m.get("source_quote") or "" for m in months),
            "period_basis": "twelve monthly figures summed to the NIGC fiscal "
                            "year (October-September)",
        })

    # ---- tribe level: NM quarterly (calendar year), MI annual.
    nm = defaultdict(list)
    for r in rows:
        if r.get("state") != "NM":
            continue
        ps = r.get("period_start") or ""
        if len(ps) < 4:
            continue
        nm[(r.get("tribe_id") or "", int(ps[:4]))].append(r)

    tribe_level = []
    for (tid, y), qs in sorted(nm.items()):
        if not tid or len(qs) != 4:
            continue
        qs.sort(key=lambda q: q["period_start"])
        tribe_level.append({
            "tribe_id": tid, "fiscal_year": y,
            "value": sum(num(q["value"]) or 0.0 for q in qs),
            "concept": "new_mexico_class_iii_tribal_net_win",
            "base_is_gaming_revenue": True,
            "source_url": qs[0].get("source_url"),
            "source_authority": qs[0].get("source_authority"),
            "source_quote": "; ".join(q.get("source_quote") or "" for q in qs),
            "period_basis": "four calendar quarters summed to the calendar "
                            "year; NOT the NIGC fiscal year",
            "state": "NM",
        })

    for r in rows:
        if r.get("state") != "MI":
            continue
        ps = r.get("period_start") or ""
        tribe_level.append({
            "tribe_id": r.get("tribe_id") or "", "fiscal_year": int(ps[:4]),
            "value": num(r["value"]),
            "concept": "michigan_class_iii_electronic_net_win_derived_from_payment_and_compact_rate",
            "base_is_gaming_revenue": True,
            "source_url": r.get("source_url"),
            "source_authority": r.get("source_authority"),
            "source_quote": r.get("source_quote"),
            "period_basis": "calendar year as published; NOT the NIGC fiscal year",
            "state": "MI",
            "applies_to": r.get("applies_to"),
        })
    return property_level, tribe_level


# =========================================================================
# 4. THE BOUNDS FILE
# =========================================================================
BOUND_COLS = [
    "bound_id", "facility_id", "tribe_id", "fiscal_year",
    "revenue_lower_bound", "revenue_upper_bound", "point_value",
    "measurement_status", "bound_basis", "n_properties_tribe_operated",
    "n_operations_in_region", "regional_total_usd", "known_property_sum_usd",
    "assumption_note", "source_url", "source_quote", "confidence", "tier",
    "built_date",
]

CEILING_NOTE = (
    "NIGC gross gaming revenue for the whole region is an upper bound on any "
    "one operation inside it, because a part cannot exceed its total. It is "
    "NOT a figure for this property and must never be divided by "
    "n_operations_in_region: NIGC's own FY2025 distribution has about 9% of "
    "operations making 56% of GGR while over 54% make about 5%, so an equal "
    "allocation would be wrong by an order of magnitude for most properties. "
    "NIGC GGR is gaming win only and excludes hotel, food, entertainment and "
    "retail."
)


def build_bounds(bands):
    print("\n=== 2. REGIONAL CEILINGS, RESIDUALS, SINGLE-PROPERTY ATTRIBUTION ===")
    spine = read_csv(SPINE / "cedar_entity_spine.csv")
    ggr = read_csv(CLEAN / "nigc_regional_ggr.csv")
    assigns = read_csv(CLEAN / "nigc_region_assignments.csv")
    facs = load_facilities()
    fac_by_id = {f["facility_id"]: f for f in facs}

    igra_by_fac = defaultdict(set)
    for a in assigns:
        igra_by_fac[a["facility_id"]].add(a.get("igra_coverage_status") or "")

    counts, by_tribe = build_property_counts(facs, igra_by_fac)
    (blocking, aliases, unattributed_state, n_gaps,
     closed_but_listed) = attribute_roster_gaps(spine, by_tribe, facs)
    print(f"  roster diff: {n_gaps} NIGC properties Cedar lacks -> "
          f"{sum(len(v) for v in aliases.values())} resolve as an alias of a held "
          f"property, {sum(len(v) for v in blocking.values())} block a tribe's count, "
          f"{sum(unattributed_state.values())} could not be pinned on any tribe")
    print(f"  close-date conflicts: {sum(len(v) for v in closed_but_listed.values())} "
          f"properties Cedar records as closed are on NIGC's current map, across "
          f"{len(closed_but_listed)} tribes")
    state_of_tribe = {}
    for f in facs:
        t = (f.get("tribe_id") or "").strip()
        if t and f.get("state"):
            state_of_tribe.setdefault(t, f["state"])

    # ---- regional GGR keyed by (region id, fiscal year). Prefer the report
    # headlined for the year over a later report's comparison column.
    reg = {}
    for r in ggr:
        k = (r["administrative_region_id"], yr(r["fiscal_year"]))
        if k not in reg or r.get("figure_vintage") == "own_year_report":
            reg[k] = r

    quotes = load_region_quotes()

    # ---- expand assignments to property-years -------------------------------
    IGRA_OK = {"VERIFIED_NIGC_OPERATION", "LIKELY_IGRA_OPERATION",
               "CLOSED_IGRA_OPERATION"}
    prop_years = []          # (facility_id, tribe_id, fy, region_row, assign)
    skipped_non_igra = skipped_no_region = 0
    for a in assigns:
        rid = (a.get("administrative_region_id") or "").strip()
        if not rid or (a.get("confidence") or "") == "none":
            skipped_no_region += 1
            continue
        if (a.get("igra_coverage_status") or "") not in IGRA_OK:
            # A NON_IGRA property is not inside NIGC's total at all, so the
            # regional total says nothing about it. Absence of a bound here is
            # a property of NIGC's universe, not a gap in ours.
            skipped_non_igra += 1
            continue
        s = yr(a.get("effective_start_year"))
        e = yr(a.get("effective_end_year"))
        if s is None:
            continue
        if e is None:
            e = 2025
        for fy in range(s, e + 1):
            rrow = reg.get((rid, fy))
            if rrow:
                prop_years.append((a["facility_id"], (a.get("tribe_id") or ""),
                                   fy, rrow, a))
    print(f"  {len(prop_years):,} property-years carry a regional ceiling "
          f"({len({p[0] for p in prop_years})} distinct properties); "
          f"skipped {skipped_non_igra} non-IGRA and {skipped_no_region} unassigned "
          f"assignment rows")

    # ---- known property-level revenue, indexed by region-year ---------------
    prop_rev, tribe_rev = load_revenue_series()
    known_by_fac_fy = {(p["facility_id"], p["fiscal_year"]): p for p in prop_rev}

    region_of = {}
    for fid, tid, fy, rrow, a in prop_years:
        region_of[(fid, fy)] = rrow["administrative_region_id"]

    known_in_region = defaultdict(list)
    for p in prop_rev:
        rid = region_of.get((p["facility_id"], p["fiscal_year"]))
        if rid:
            known_in_region[(rid, p["fiscal_year"])].append(p)

    rows = []
    n = 0

    def bid(tag):
        nonlocal n
        n += 1
        return f"RVB-{tag}-{n:06d}"

    # ---- (a) ceilings -------------------------------------------------------
    for fid, tid, fy, rrow, a in prop_years:
        n_open, n_unk, _ = counts.get((tid, fy), (None, None, None))
        known = known_in_region.get((rrow["administrative_region_id"], fy), [])
        known_sum = sum(k["value"] for k in known if k["facility_id"] != fid)
        total = num(rrow["ggr_usd"])
        prec_note = ""
        if rrow.get("figure_precision") == "rounded_0.1B":
            prec_note = (" NIGC printed this regional figure rounded to $0.1B, "
                         "so the ceiling carries up to $50M of that rounding.")
        rows.append({
            "bound_id": bid("CEIL"),
            "facility_id": fid,
            "tribe_id": tid,
            "fiscal_year": fy,
            "revenue_lower_bound": "",
            "revenue_upper_bound": int(total),
            "point_value": "",
            "measurement_status": "REGIONAL_GGR_CEILING",
            "bound_basis": "REGIONAL_GGR_CEILING",
            "n_properties_tribe_operated": "" if n_open is None else n_open,
            "n_operations_in_region": yr(rrow["operation_count"]),
            "regional_total_usd": int(total),
            "known_property_sum_usd": "",
            "assumption_note": (
                f"NIGC region {rrow['region_name']} "
                f"({rrow['region_system_version']}), FY{fy}. " + CEILING_NOTE + prec_note),
            "source_url": rrow.get("source_url") or NIGC_GGR_LANDING,
            "source_quote": quotes.get((rrow.get("source_document"),
                                        rrow.get("region_name"), fy), ""),
            "confidence": a.get("confidence") or "",
            "tier": "B",
            "built_date": TODAY,
        })

        # ---- (b) ceiling tightened by other properties we already know ------
        if known_sum > 0:
            rows.append({
                "bound_id": bid("CEILNET"),
                "facility_id": fid,
                "tribe_id": tid,
                "fiscal_year": fy,
                "revenue_lower_bound": "",
                "revenue_upper_bound": int(total - known_sum),
                "point_value": "",
                "measurement_status": "REGIONAL_GGR_CEILING",
                "bound_basis": "REGIONAL_GGR_CEILING_NET_OF_KNOWN",
                "n_properties_tribe_operated": "" if n_open is None else n_open,
                "n_operations_in_region": yr(rrow["operation_count"]),
                "regional_total_usd": int(total),
                "known_property_sum_usd": int(known_sum),
                "assumption_note": (
                    f"Regional total less the revenue Cedar already holds for "
                    f"{len([k for k in known if k['facility_id'] != fid])} other "
                    f"properties in NIGC region {rrow['region_name']} FY{fy}. "
                    "The subtracted figures are Connecticut DCP SLOT win, which "
                    "excludes table games, so the amount removed is smaller than "
                    "those properties' true GGR and this ceiling is therefore "
                    "loose in the safe direction -- it can only be too high, "
                    "never too low. " + CEILING_NOTE),
                "source_url": rrow.get("source_url") or NIGC_GGR_LANDING,
                "source_quote": quotes.get((rrow.get("source_document"),
                                            rrow.get("region_name"), fy), ""),
                "confidence": "medium",
                "tier": "B",
                "built_date": TODAY,
            })

    # ---- (c) region-year residual: the sum of everything still unknown ------
    residual_closed = 0
    residual_rows = 0
    for (rid, fy), known in sorted(known_in_region.items()):
        rrow = reg.get((rid, fy))
        if not rrow:
            continue
        total = num(rrow["ggr_usd"])
        ksum = sum(k["value"] for k in known)
        nops = yr(rrow["operation_count"])
        n_unknown = (nops - len(known)) if nops is not None else None
        closes = n_unknown == 1
        if closes:
            residual_closed += 1
        residual_rows += 1
        rows.append({
            "bound_id": bid("RESID"),
            "facility_id": "",
            "tribe_id": "",
            "fiscal_year": fy,
            "revenue_lower_bound": "",
            "revenue_upper_bound": int(total - ksum),
            "point_value": int(total - ksum) if closes else "",
            "measurement_status": "REGIONAL_GGR_CEILING",
            "bound_basis": ("RESIDUAL_CLOSED_SINGLE_UNKNOWN_OPERATION" if closes
                            else "UNKNOWN_PROPERTIES_RESIDUAL_SUM"),
            "n_properties_tribe_operated": "",
            "n_operations_in_region": nops,
            "regional_total_usd": int(total),
            "known_property_sum_usd": int(ksum),
            "assumption_note": (
                f"NIGC region {rrow['region_name']} FY{fy}: regional total minus "
                f"the {len(known)} property revenues Cedar holds inside it. This "
                f"bounds the combined revenue of the remaining "
                f"{'unknown operation' if closes else str(n_unknown) + ' unknown operations'}"
                " from above, and therefore bounds any single one of them. It is "
                "a point value only where exactly one operation remains unknown. "
                "Two facts keep this loose: the subtracted figures are "
                "Connecticut DCP SLOT win rather than GGR, and NIGC's "
                "operation_count counts SUBMITTERS OF AUDITED FINANCIAL "
                "STATEMENTS, not buildings, so one operation can cover several "
                "properties and the count will not reconcile 1:1 with a facility "
                "file."),
            "source_url": rrow.get("source_url") or NIGC_GGR_LANDING,
            "source_quote": quotes.get((rrow.get("source_document"),
                                        rrow.get("region_name"), fy), ""),
            "confidence": "medium",
            "tier": "B",
            "built_date": TODAY,
        })

    # ---- (d) reported property revenue (CT), stated as a floor on GGR -------
    for p in prop_rev:
        fy = p["fiscal_year"]
        rid = region_of.get((p["facility_id"], fy))
        rrow = reg.get((rid, fy)) if rid else None
        n_open, _, _ = counts.get((p["tribe_id"], fy), (None, None, None))
        rows.append({
            "bound_id": bid("REPT"),
            "facility_id": p["facility_id"],
            "tribe_id": p["tribe_id"],
            "fiscal_year": fy,
            "revenue_lower_bound": int(p["value"]),
            "revenue_upper_bound": int(num(rrow["ggr_usd"])) if rrow else "",
            "point_value": int(p["value"]),
            "measurement_status": "REPORTED_PROPERTY_REVENUE",
            "bound_basis": "REPORTED_SLOT_WIN_IS_FLOOR_FOR_GGR",
            "n_properties_tribe_operated": "" if n_open is None else n_open,
            "n_operations_in_region": yr(rrow["operation_count"]) if rrow else "",
            "regional_total_usd": int(num(rrow["ggr_usd"])) if rrow else "",
            "known_property_sum_usd": "",
            "assumption_note": (
                f"{p['facility_name']}: {p['period_basis']}. The revenue concept "
                "is Connecticut DCP slot machine win, which EXCLUDES table games. "
                "Both Connecticut properties run large table operations, so this "
                "figure is a floor on the property's NIGC-comparable gross gaming "
                "revenue and is not the same measure. point_value is the figure "
                "as published for its own concept, not a GGR figure."),
            "source_url": p.get("source_url") or "",
            "source_quote": p.get("source_quote") or "",
            "confidence": "high",
            "tier": "B",
            "built_date": TODAY,
        })

    # ---- (e) single-property attribution, and every refusal ----------------
    attributed, refusals = [], []
    for t in tribe_rev:
        tid, fy = t["tribe_id"], t["fiscal_year"]
        n_open, n_unk, openers = counts.get((tid, fy), (0, 0, []))
        base_ok = bool(t.get("base_is_gaming_revenue"))
        blocked = blocking.get(tid, [])
        conflicts = [c for c in closed_but_listed.get(tid, []) if c[2] < fy]
        count_verified = (not blocked) and n_unk == 0 and not conflicts
        ok = may_attribute_to_single_property(n_open, base_ok, count_verified)

        state = t.get("state") or state_of_tribe.get(tid, "")
        state_risk = unattributed_state.get(state, 0)

        fails = []
        if not base_ok:
            fails.append("base_not_gaming_revenue")
        if blocked:
            fails.append("property_count_not_verified:nigc_roster_gap")
        if n_unk:
            fails.append("property_count_not_verified:undated_property")
        if conflicts:
            fails.append("property_count_not_verified:nigc_lists_a_property_"
                         "cedar_records_as_closed(" +
                         ",".join(f"{c[0]}@{c[2]}" for c in conflicts) + ")")
        if n_open != 1:
            fails.append(f"n_open_properties={n_open}")
        if not by_tribe.get(tid):
            # A tribe-level GAMING revenue row keyed to an entity that holds no
            # gaming property at all is a keying defect upstream, not a
            # measurement. The known instance is the spine's San Juan collision
            # recorded in AGENTS.md: New Mexico's regulator writes "San Juan"
            # meaning Ohkay Owingeh (formerly San Juan Pueblo, New Mexico),
            # while the spine's `San Juan` is the San Juan Southern Paiute
            # Tribe of ARIZONA. Refused here and reported; the source file is
            # owned elsewhere and is not edited by this script.
            fails.append("tribe_holds_no_gaming_property_in_cedar")

        tribe_name = ""
        for f in by_tribe.get(tid, []):
            tribe_name = f.get("tribe_canonical_name") or tribe_name

        if ok:
            fid = openers[0]
            f = fac_by_id.get(fid, {})
            attributed.append((tid, fy))
            rows.append({
                "bound_id": bid("SINGLE"),
                "facility_id": fid,
                "tribe_id": tid,
                "fiscal_year": fy,
                "revenue_lower_bound": "",
                "revenue_upper_bound": "",
                "point_value": int(round(t["value"])),
                "measurement_status": SINGLE_PROPERTY_ATTRIBUTED,
                "bound_basis": "SINGLE_PROPERTY_TRIBE_LEVEL_GAMING_REVENUE",
                "n_properties_tribe_operated": n_open,
                "n_operations_in_region": "",
                "regional_total_usd": "",
                "known_property_sum_usd": "",
                "assumption_note": (
                    SINGLE_PROPERTY_NOTE + " Revenue concept: " + t["concept"] +
                    ". Period: " + t["period_basis"] + ". Property count verified "
                    "against review/nigc_roster_diff_2026-08-06.csv: no NIGC "
                    "operation absent from Cedar attributes to this tribe, no "
                    "property Cedar records as closed is on NIGC's current map, "
                    "and every held property carries a dated opening. Property: " +
                    (f.get("facility_name") or fid) + ". Residual risk: " +
                    f"{state_risk} NIGC operations in {state or 'this state'} "
                    "could not be pinned on any tribe; if one of them is this "
                    "tribe's, the count of one is short."),
                "source_url": t.get("source_url") or "",
                "source_quote": (t.get("source_quote") or "")[:1200],
                "confidence": "medium",
                "tier": "B",
                "built_date": TODAY,
            })
        else:
            rows.append({
                "bound_id": bid("TRIBE"),
                "facility_id": "",
                "tribe_id": tid,
                "fiscal_year": fy,
                "revenue_lower_bound": "",
                "revenue_upper_bound": "",
                "point_value": int(round(t["value"])),
                "measurement_status": "TRIBE_LEVEL_REVENUE",
                "bound_basis": "TRIBE_LEVEL_NOT_ATTRIBUTABLE_TO_A_PROPERTY",
                "n_properties_tribe_operated": n_open,
                "n_operations_in_region": "",
                "regional_total_usd": "",
                "known_property_sum_usd": "",
                "assumption_note": (
                    "Held at tribe level. Single-property attribution refused: "
                    + "; ".join(fails) + ". Revenue concept: " + t["concept"]
                    + ". Period: " + t["period_basis"] + "."),
                "source_url": t.get("source_url") or "",
                "source_quote": (t.get("source_quote") or "")[:1200],
                "confidence": "high",
                "tier": "B",
                "built_date": TODAY,
            })
            refusals.append({
                "tribe_id": tid, "tribe_canonical_name": tribe_name,
                "state": t.get("state", ""), "fiscal_year": fy,
                "value_usd": int(round(t["value"])),
                "revenue_concept": t["concept"],
                "base_is_gaming_revenue": int(base_ok),
                "n_open_properties": n_open,
                "n_properties_without_a_dated_opening": n_unk,
                "property_count_verified": int(count_verified),
                "nigc_roster_gap_names": " | ".join(blocked),
                "nigc_lists_closed_property": " | ".join(
                    f"{c[0]} {c[1]} (Cedar close {c[2]})" for c in conflicts),
                "unattributed_nigc_operations_in_state": state_risk,
                "conditions_failed": "; ".join(fails),
                "built_date": TODAY,
            })

    attributed_prop_years = {(r["facility_id"], r["fiscal_year"]) for r in rows
                             if r["measurement_status"] == SINGLE_PROPERTY_ATTRIBUTED}
    print(f"  single-property attribution: {len(attributed)} tribe-years attributed, "
          f"{len(refusals)} refused")
    print(f"  residual: {residual_rows} region-years carry a residual bound, "
          f"{residual_closed} close to a single unknown operation")

    # ---- guards -------------------------------------------------------------
    assert not may_promote(MeasurementType.DERIVED_BOUND,
                           MeasurementType.ACTIVE_FLOOR_COUNT), \
        "cedar_domain must refuse DERIVED_BOUND -> ACTIVE_FLOOR_COUNT"
    bad = {r["measurement_status"] for r in rows} - ALLOWED_STATUS
    if bad:
        raise SystemExit(f"measurement_status outside the vocabulary: {bad}")
    for r in rows:
        if r["revenue_lower_bound"] == "" and r["revenue_upper_bound"] == "" \
                and r["point_value"] == "":
            raise SystemExit(f"row {r['bound_id']} bounds nothing")
        if not r["bound_basis"]:
            raise SystemExit(f"row {r['bound_id']} has no bound_basis")
        lo, hi = num(r["revenue_lower_bound"]), num(r["revenue_upper_bound"])
        if lo is not None and hi is not None and lo > hi:
            raise SystemExit(f"row {r['bound_id']} lower bound above upper bound")
    banned_scan(rows, "gaming_revenue_bounds.csv")

    write_csv(CLEAN / "gaming_revenue_bounds.csv", rows, BOUND_COLS)
    if refusals:
        write_csv(REVIEW / f"revenue_bounds_single_property_refusals_{TODAY}.csv",
                  refusals, list(refusals[0].keys()))

    return rows, refusals, dict(
        prop_years=len(prop_years), residual_rows=residual_rows,
        residual_closed=residual_closed, attributed=len(attributed),
        blocking=blocking, aliases=aliases,
        unattributed_state=dict(unattributed_state), n_gaps=n_gaps,
        prop_rev=prop_rev, reg=reg, counts=counts, quotes=quotes,
        skipped_non_igra=skipped_non_igra, skipped_no_region=skipped_no_region,
        attributed_prop_years=attributed_prop_years,
        closed_but_listed=closed_but_listed,
    )


def load_region_quotes():
    """(document, region name, fiscal year) -> the printed table line.

    Reading the figure back out of the source text is both a verbatim quote and
    a check on `nigc_regional_ggr.csv`. Where the line cannot be found the quote
    is left EMPTY rather than reconstructed -- a restated table cell is not a
    quotation.
    """
    ggr = read_csv(CLEAN / "nigc_regional_ggr.csv")
    txt_dir = RAW / "ggr_reports" / "_txt"
    cache, out = {}, {}
    for r in ggr:
        doc = r.get("source_document") or ""
        stem = Path(doc).stem
        if stem not in cache:
            p = txt_dir / f"{stem}.txt"
            cache[stem] = p.read_text(encoding="utf-8", errors="replace").splitlines() \
                if p.exists() else []
        v = num(r["ggr_usd"])
        if v is None:
            continue
        needles = [f"{int(round(v)):,}", f"{int(round(v/1000)):,}"]
        rname = (r.get("region_name") or "").split()[0]
        hits = [line for line in cache[stem] if any(nd in line for nd in needles)]
        # Prefer a line that also names the region. Where NIGC abbreviates the
        # region in its own table ("D.C." for Washington DC) the amount alone
        # identifies the line, and it is only used when it is UNIQUE in the
        # document - an ambiguous line is no quotation at all.
        named = [h for h in hits if rname and rname in h]
        pick = named[0] if named else (hits[0] if len(hits) == 1 else None)
        if pick:
            out[(doc, r.get("region_name"), yr(r["fiscal_year"]))] = \
                " ".join(pick.split())[:400]
    print(f"  region source quotes located for {len(out)} of {len(ggr)} region-years")
    return out


# =========================================================================
# 5. CONNECTICUT AS THE VALIDATION CASE
# =========================================================================
def validate_connecticut(ctx):
    """Connecticut is the only state where Cedar holds every property's
    revenue. So it is the one place a residual can be sanity-checked -- and the
    check FAILS by design, for a reason worth writing down.
    """
    print("\n=== 3. CONNECTICUT VALIDATION ===")
    prop_rev, reg, counts = ctx["prop_rev"], ctx["reg"], ctx["counts"]
    by_fy = defaultdict(float)
    for p in prop_rev:
        by_fy[p["fiscal_year"]] += p["value"]

    lines = []
    for fy in sorted(by_fy):
        rid = None
        for (r_id, r_fy), rr in reg.items():
            if r_fy == fy and rr.get("region_name") in ("Washington DC",
                                                        "Region VI",
                                                        "Eastern Region"):
                rid = r_id
                break
        rr = reg.get((rid, fy)) if rid else None
        if not rr:
            continue
        total = num(rr["ggr_usd"])
        lines.append((fy, rr["region_name"], by_fy[fy], total,
                      100.0 * by_fy[fy] / total, yr(rr["operation_count"])))
    for L in lines[-6:]:
        print(f"  FY{L[0]}  CT slot win ${L[2]/1e9:.2f}B  vs {L[1]} region GGR "
              f"${L[3]/1e9:.2f}B  = {L[4]:.1f}%  ({L[5]} operations)")
    return lines


# =========================================================================
# 6. HOW FAR RESIDUAL ELIMINATION IS FROM BEING USABLE
# =========================================================================
def residual_gap_by_region(ctx):
    """The question that matters: how many MORE known property revenues before
    residual elimination works, region by region?

    Two counts, because they are not the same claim. `reported` is revenue a
    source states for a named property -- Connecticut's two. `plus_attributed`
    adds the single-property attributions, which are inferences; a residual
    built on them inherits the inference and would have to say so.

    The count reported here is a FLOOR on the work required, not a target.
    NIGC's operation_count counts submitters of audited financial statements,
    so one operation can cover several properties and the two universes will
    never line up 1:1. Residual elimination in the strict sense is therefore
    unreachable in most regions even with complete property coverage.
    """
    print("\n=== 4. DISTANCE TO RESIDUAL ELIMINATION, BY REGION ===")
    reg, prop_rev = ctx["reg"], ctx["prop_rev"]
    region_of, attributed = ctx["region_of"], ctx["attributed_prop_years"]

    reported_years = {(p["facility_id"], p["fiscal_year"]) for p in prop_rev}
    out = []
    latest = {}
    for (rid, fy), rr in reg.items():
        if rr.get("region_system_version") != "NIGC_R4_FY2017_present":
            continue
        if rr["region_name"] not in latest or fy > latest[rr["region_name"]][0]:
            latest[rr["region_name"]] = (fy, rr)

    def n_in(pairs, rid, fy):
        return sum(1 for (f, y) in pairs
                   if y == fy and region_of.get((f, y)) == rid)

    for name, (fy, rr) in sorted(latest.items()):
        rid = rr["administrative_region_id"]
        nops = yr(rr["operation_count"])
        n_rep = n_in(reported_years, rid, fy)
        n_att = n_in(attributed | reported_years, rid, fy)
        # best year in this region system, whichever gets closest
        best = max(((y, n_in(attributed | reported_years, rid, y))
                    for (r2, y) in reg if r2 == rid),
                   key=lambda t: t[1])
        out.append({
            "region_name": name, "fiscal_year": fy, "operations": nops,
            "known_reported_property_revenues": n_rep,
            "known_including_single_property_attributed": n_att,
            "more_needed_for_single_unknown_reported_only": max(0, nops - 1 - n_rep),
            "more_needed_for_single_unknown_including_attributed": max(0, nops - 1 - n_att),
            "best_covered_year": best[0], "best_covered_year_known": best[1],
            "regional_ggr_usd": int(num(rr["ggr_usd"])),
        })
        print(f"  {name:<16} FY{fy}  {nops:>3} operations | known: {n_rep} reported, "
              f"{n_att} incl. attributed -> {max(0, nops-1-n_att)} more needed "
              f"(best year FY{best[0]}: {best[1]} known)")
    return out


# =========================================================================
# 7. CODEBOOK - VARIABLES ONLY
# =========================================================================
def write_codebook():
    cb = DOCS / "codebooks" / "07e_revenue_bounds.md"
    cb.parent.mkdir(parents=True, exist_ok=True)
    L = [
        "# Codebook - gaming revenue bounds",
        "",
        "*Variables only. Method, sourcing and every figure verified against a "
        "document are in `docs/REVENUE_BOUNDS_LOG.md`.*",
        "",
        "**A factual bound is not a confidence interval.** Every number in "
        "these two files is arithmetic on figures a source printed. Nothing "
        "here is modelled and no column may be read as one.",
        "",
        "## `data/clean/gaming_revenue_bounds.csv`",
        "",
        "| variable | type | definition |",
        "|---|---|---|",
        "| `bound_id` | string | Cedar row id. `RVB-CEIL-` regional ceiling, "
        "`RVB-CEILNET-` ceiling net of known property revenue, `RVB-RESID-` "
        "region-year residual, `RVB-REPT-` reported property revenue, "
        "`RVB-SINGLE-` single-property attribution, `RVB-TRIBE-` tribe-level "
        "figure held at tribe level. |",
        "| `facility_id` | string | Cedar property id (`CCP-`/`VP-`/`TPL-`), "
        "key into `gaming_facilities.csv`. **Blank on region-level and "
        "tribe-level rows**, where no single property is named. |",
        "| `tribe_id` | string | Cedar entity spine id of the owning entity. "
        "Blank on region-level rows. |",
        "| `fiscal_year` | integer | The year the bound covers. For rows "
        "carrying a NIGC figure this is the NIGC fiscal year (October to "
        "September). For rows carrying a state figure it is the period the "
        "state published, which is NOT always the NIGC fiscal year; "
        "`assumption_note` states which on every row. |",
        "| `revenue_lower_bound` | number, USD | A floor: the property's "
        "revenue for the stated concept is at least this. Blank where no floor "
        "is established. |",
        "| `revenue_upper_bound` | number, USD | A ceiling: the revenue cannot "
        "exceed this, because a part cannot exceed its total. Blank where no "
        "ceiling applies. |",
        "| `point_value` | number, USD | A single figure, used only where a "
        "source states one or where arithmetic on published figures yields "
        "exactly one. Never a midpoint of the bounds. |",
        "| `measurement_status` | enum | What KIND of revenue evidence the row "
        "is. From `cedar_domain.REVENUE_EVIDENCE`: "
        "`REPORTED_PROPERTY_REVENUE`, `TRIBE_LEVEL_REVENUE`, "
        "`REGIONAL_GGR_CEILING`; plus `SINGLE_PROPERTY_ATTRIBUTED` from "
        "`cedar_domain.SINGLE_PROPERTY_ATTRIBUTED`, which is deliberately its "
        "own status so an inference can never be read as an observation. |",
        "| `bound_basis` | enum | What makes the bound true. "
        "`REGIONAL_GGR_CEILING`; "
        "`REGIONAL_GGR_CEILING_NET_OF_KNOWN`; "
        "`UNKNOWN_PROPERTIES_RESIDUAL_SUM`; "
        "`RESIDUAL_CLOSED_SINGLE_UNKNOWN_OPERATION`; "
        "`REPORTED_SLOT_WIN_IS_FLOOR_FOR_GGR`; "
        "`SINGLE_PROPERTY_TRIBE_LEVEL_GAMING_REVENUE`; "
        "`TRIBE_LEVEL_NOT_ATTRIBUTABLE_TO_A_PROPERTY`. Populated on every "
        "row: without it a bound is indistinguishable from a modelled figure. |",
        "| `n_properties_tribe_operated` | integer | Gaming properties Cedar "
        "records the tribe as operating in that year. Blank where the tribe is "
        "not named or the count is not determinable. |",
        "| `n_operations_in_region` | integer | Operations NIGC counted in the "
        "region that year. **An operation is a submitter of audited financial "
        "statements, not a building**, so it will not reconcile 1:1 with a "
        "property file. Present so a reader can see the denominator - it is "
        "NOT a divisor. |",
        "| `regional_total_usd` | number, USD | NIGC gross gaming revenue for "
        "the whole region-year. Gaming win only; excludes hotel, food, "
        "entertainment and retail. |",
        "| `known_property_sum_usd` | number, USD | Property revenue Cedar "
        "already holds inside that region-year and has subtracted. Blank where "
        "nothing was subtracted. |",
        "| `assumption_note` | string | What the row assumes, which direction "
        "it can be wrong in, and what its revenue concept and period are. "
        "Travels with the row so a join cannot lose it. |",
        "| `source_url` | string | The publisher's URL for the figure. |",
        "| `source_quote` | string | Verbatim support, whitespace collapsed and "
        "nothing else changed. For a total built from monthly figures, ALL the "
        "monthly quotes are carried, because one month's quote would not "
        "support a twelve-month figure. Blank where the source is a chart or "
        "map with no quotable line rather than where support is missing. |",
        "| `confidence` | enum | `high` / `medium`. Not a probability and not "
        "an interval. |",
        "| `tier` | enum | Always `B` - pending review. |",
        "| `built_date` | date | When this row was written. |",
        "",
        "## `data/clean/nigc_revenue_bands.csv`",
        "",
        "| variable | type | definition |",
        "|---|---|---|",
        "| `band_id` | string | Cedar row id, `NIGCBAND-<fiscal year>-<band "
        "ordinal>`. |",
        "| `fiscal_year` | integer | NIGC fiscal year. Bands exist for FY2022 "
        "to FY2025 only; NIGC published no band table before FY2022. |",
        "| `band_ordinal` | integer | 1 (lowest band) to 5 (highest). |",
        "| `band_label` | string | The band as NIGC labels it: `<$25M`, "
        "`$25-50M`, `$50-100M`, `$100-250M`, `$250M+`. |",
        "| `band_lower_usd` | number, USD | Lower edge. Blank on the lowest "
        "band, which is open below. |",
        "| `band_upper_usd` | number, USD | Upper edge. Blank on the highest "
        "band, which is open above. |",
        "| `pct_of_operations` | number, percent | Share of gaming operations "
        "in this band, as NIGC printed it. |",
        "| `pct_of_revenue` | number, percent | Share of total GGR contributed "
        "by this band, as NIGC printed it. |",
        "| `pct_precision` | enum | `1_percent` (FY2022, FY2023) or "
        "`0.1_percent` (FY2024, FY2025). Sets the rounding interval that the "
        "implied counts and dollars carry. |",
        "| `national_operation_count` | integer | Operations in NIGC's national "
        "total that year, as its own report states. |",
        "| `national_ggr_usd` | number, USD | National GGR that year, the sum "
        "of NIGC's published region figures. |",
        "| `n_operations_implied_low` | integer | Fewest operations consistent "
        "with the printed share and its rounding. |",
        "| `n_operations_implied_high` | integer | Most operations consistent "
        "with the printed share and its rounding. NIGC printed the share, not "
        "the count; a single count would be a figure it did not publish. |",
        "| `band_aggregate_ggr_implied_low_usd` | number, USD | Least combined "
        "GGR consistent with the printed revenue share and its rounding. |",
        "| `band_aggregate_ggr_implied_high_usd` | number, USD | Most combined "
        "GGR consistent with the same. |",
        "| `per_operation_upper_bound_usd` | number, USD | The band's upper "
        "edge, which is a ceiling on any single operation inside it. Blank on "
        "the top band, which has no upper edge. |",
        "| `derivation_note` | string | What the arithmetic is and what it does "
        "not license. The band bounds the SET; it never names a property. |",
        "| `chart_label_basis` | string | Which labels came from the PDF text "
        "layer and which were read off a render of the chart by hand. |",
        "| `source_url` | string | NIGC's report landing page. |",
        "| `source_document` | string | Filename of the NIGC PDF, held under "
        "`data/raw/external/nigc/ggr_reports/`. |",
        "| `source_document_title` | string | Title NIGC gives that document. |",
        "| `source_page` | integer | Page of that PDF carrying the chart. |",
        "| `source_quote` | string | NIGC's own sentence stating the top "
        "band's share, verbatim. |",
        "| `operation_count_source_quote` | string | NIGC's own sentence "
        "stating the national operation count, verbatim. |",
        "| `confidence` | enum | `high`. |",
        "| `tier` | enum | Always `B` - pending review. |",
        "| `review_status` | enum | `pending_review`. |",
        "| `fetched_date` | date | When the PDF was retrieved. |",
        "| `built_date` | date | When this row was written. |",
        "",
    ]
    cb.write_text("\n".join(L), encoding="utf-8")
    print(f"  wrote {cb.relative_to(CEDAR)}")


# =========================================================================
# 8. BUILD LOG
# =========================================================================
def write_log(summary, ctx, bands, refusals):
    p = DOCS / "REVENUE_BOUNDS_LOG.md"
    by_basis = summary["by_basis"]
    ct = summary["ct_validation"]
    L = []
    A = L.append
    A("# Revenue bounds build log")
    A("")
    A(f"*Script `code/106_build_revenue_bounds.py`. Built {TODAY}. "
      f"{summary['bound_rows']:,} bound rows, {summary['band_rows']} band rows. "
      "Everything tier B, pending review.*")
    A("")
    A("> Elijah, 2026-08-07: *\"maybe sometimes we can process of eliminate "
      "revenue too and attribute it.\"*")
    A("")
    A("Right in principle. The measured state is the point of this file.")
    A("")
    A("## What Cedar actually holds")
    A("")
    A("| | properties | grain |")
    A("|---|---:|---|")
    A("| Connecticut DCP slot win | 2 | property-month |")
    A("| New Mexico net win | 0 | tribe-quarter, 16 tribes |")
    A("| Michigan derived net win | 0 | tribe-year, 4 tribes |")
    A("")
    A("So full residual elimination cannot run. You cannot solve for the 88th "
      "Sacramento operation knowing none of the other 87. What follows is what "
      "IS derivable, and it is a lot.")
    A("")
    A("## 1. Regional ceilings")
    A("")
    A(f"{by_basis.get('REGIONAL_GGR_CEILING', 0):,} property-year ceilings "
      f"across {summary['properties_with_a_ceiling']} properties, FY2001-FY2025, "
      "joining `nigc_region_assignments.csv` to `nigc_regional_ggr.csv` through "
      "the administrative region id and the assignment's effective years.")
    A("")
    A(f"{ctx['skipped_non_igra']} assignment rows were deliberately given NO "
      "ceiling because their `igra_coverage_status` is `NON_IGRA_TRIBALLY_OWNED` "
      "or `PROPOSED`. A property outside IGRA is not inside NIGC's total, so the "
      "regional total says nothing about it. Absence of a bound there is a "
      "property of NIGC's universe, not a gap in ours. A further "
      f"{ctx['skipped_no_region']} rows carry no region assignment at all.")
    A("")
    A("**The ceiling is never divided by the operation count.** NIGC's own "
      "FY2025 distribution is why, and it was verified against the FY2025 "
      "report before being relied on:")
    A("")
    A("> " + next(b["source_quote"] for b in bands if b["fiscal_year"] == 2025))
    A("")
    A("Read off the FY2025 chart: **8.6% of operations hold 55.8% of GGR, while "
      "54.3% hold 4.8%.** An equal allocation of a regional total would be wrong "
      "by an order of magnitude for most properties, in both directions.")
    A("")
    A(f"{by_basis.get('REGIONAL_GGR_CEILING_NET_OF_KNOWN', 0):,} rows carry the "
      "tighter ceiling `regional total - the revenue we already know for OTHER "
      "properties in the same region-year`. Today that only bites in the "
      "Washington DC region, where Connecticut's two properties sit.")
    A("")
    A("## 2. Band constraints - the new extraction")
    A("")
    A("NIGC publishes a `REVENUE BY RANGE` chart giving, for five revenue "
      "bands, the share of operations and the share of revenue. **It appears "
      "in four of the 24 GGR reports on disk and in no others** - FY2022, "
      "FY2023, FY2024 and FY2025. The other twenty are region tables and "
      "distribution maps and contain no band data at any resolution; this was "
      "checked document by document, not assumed.")
    A("")
    A("| FY | ops <$25M | $25-50M | $50-100M | $100-250M | $250M+ | rev <$25M | "
      "$25-50M | $50-100M | $100-250M | $250M+ | operations |")
    A("|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for fy in (2022, 2023, 2024, 2025):
        rs = [b for b in bands if b["fiscal_year"] == fy]
        A("| " + str(fy) + " | "
          + " | ".join(f"{r['pct_of_operations']}%" for r in rs) + " | "
          + " | ".join(f"{r['pct_of_revenue']}%" for r in rs) + " | "
          + str(rs[0]["national_operation_count"]) + " |")
    A("")
    top25 = [b for b in bands if b["fiscal_year"] == 2025][4]
    lo, hi = top25["n_operations_implied_low"], top25["n_operations_implied_high"]
    span = f"exactly {lo}" if lo == hi else f"{lo}-{hi}"
    A("**Why this constrains the whole layer.** The share plus the published "
      f"operation count gives a count per band - in FY2025, {span} of 545 "
      "operations sit above $250M, because 8.6% printed to one decimal admits "
      "no other whole number against 545 - and the band's upper edge is a "
      "ceiling on every operation inside it. It bounds the SET without naming a "
      "member, which is exactly the shape of constraint the rest of this layer "
      "needs. FY2022 and FY2023, printed to whole percent, give ranges rather "
      "than a single count; `pct_precision` says which you are looking at.")
    A("")
    A("Four checks run on every extraction and stop the build on failure: both "
      "series must sum to 100 within rounding; the chart's top band must agree "
      "with NIGC's own sentence about the >$250M share; the extracted values "
      "must equal the values read off a 220-dpi render of the chart by hand; "
      "and where the shares are printed to one decimal, the implied counts must "
      "add back to NIGC's own operation count. **They do, exactly** - "
      + " and ".join(
          "FY{} {} sums to {}".format(
              fy,
              "/".join(str(b["n_operations_implied_low"])
                       for b in bands if b["fiscal_year"] == fy),
              sum(b["n_operations_implied_low"]
                  for b in bands if b["fiscal_year"] == fy))
          for fy in (2024, 2025))
      + ", both the published totals. That is an independent confirmation that the "
      "operations series was paired to the right bars. The band EDGE labels are "
      "outlined vector art with no text layer, so they were read by hand for "
      "all four years and are identical in all four; `chart_label_basis` says "
      "so on every row.")
    A("")
    A("## 3. Single-property attribution")
    A("")
    A(f"**{summary['single_property_attributed']} tribe-years attributed to a "
      f"named property. {summary['single_property_refused']} refused.** Refusals "
      "are staged at "
      f"`review/revenue_bounds_single_property_refusals_{TODAY}.csv` with the "
      "condition that failed.")
    A("")
    A("`cedar_domain.may_attribute_to_single_property` needs all three of "
      "gaming base, verified count, exactly one property open. Failures:")
    A("")
    A("| condition | tribe-years failing |")
    A("|---|---:|")
    A(f"| base is not gaming revenue | "
      f"{sum(1 for r in refusals if 'base_not_gaming' in r['conditions_failed'])} |")
    A(f"| property count not verified | "
      f"{sum(1 for r in refusals if 'property_count_not_verified' in r['conditions_failed'])} |")
    A(f"| not exactly one property open | "
      f"{sum(1 for r in refusals if 'n_open_properties=' in r['conditions_failed'])} |")
    A(f"| tribe holds no gaming property at all | "
      f"{sum(1 for r in refusals if 'tribe_holds_no_gaming_property' in r['conditions_failed'])} |")
    A("")
    A("(A tribe-year can fail more than one condition, so these do not sum to "
      "the refusal count.)")
    A("")
    A("**The base condition never fired**, and that is not luck: both tribe-level "
      "series are gaming measures by construction. New Mexico's is Class III "
      "tribal net win from the Gaming Control Board's quarterly revenue-sharing "
      "releases; Michigan's is `payment / compact rate` where the compact rate "
      "is written against *\"the net win at each casino derived from all Class "
      "III electronic games of chance\"*. A whole-tribe revenue figure would "
      "have failed it, and none was used.")
    A("")
    A("### What the count condition caught")
    A("")
    A(f"The roster diff holds {ctx['n_gaps']} NIGC properties Cedar lacks. "
      f"{summary['roster_gap_alias_of_held']} of them resolve as an ALIAS of a "
      "property Cedar already holds - same name core, same city or same street "
      "address - and an alias is not a second property. "
      f"{summary['roster_gap_blocking']} pin on a tribe and match nothing we "
      f"hold, and block that tribe's count. {sum(summary['roster_gap_unattributed_by_state'].values())} "
      "could not be pinned on any tribe; those are disclosed per state in every "
      "attributed row's `assumption_note` as residual risk rather than silently "
      "ignored.")
    A("")
    A("A second check came out of the same file and was not anticipated: "
      f"**{sum(len(v) for v in ctx['closed_but_listed'].values())} properties "
      f"Cedar records with a close date are on NIGC's CURRENT gaming location "
      f"map**, across {len(ctx['closed_but_listed'])} tribes. NIGC's map is "
      "current, so the listing contradicts our close date and every later year "
      "has an open-property count we cannot stand behind. This is what stopped "
      "the Jicarilla Apache Nation from being attributed: Cedar closes "
      "`CCP-799200` Wildhorse Casino in 2006 while NIGC still maps *Wild Horse "
      "Casino*, so the tribe's count of one from 2012 is not safe.")
    A("")
    A("### A keying defect the layer surfaced")
    A("")
    A("Three New Mexico tribe-years key to `TRBF-SNJUAN-00`, which holds no "
      "gaming property. That is the **San Juan collision** already recorded in "
      "`AGENTS.md`: New Mexico's regulator writes *San Juan* meaning Ohkay "
      "Owingeh, formerly San Juan Pueblo, in New Mexico - while the spine's "
      "`San Juan` is the San Juan Southern Paiute Tribe of **Arizona**. The rows "
      "are refused and flagged. `gaming_capacity_official.csv` is owned "
      "elsewhere and was not edited.")
    A("")
    A("## 4. Residual, where it closes")
    A("")
    A(f"**It closes nowhere.** {summary['residual_region_years']} region-years "
      "carry a residual bound - `regional total - known property sum`, which "
      "bounds the combined revenue of the unknown operations from above and "
      "therefore bounds any single one of them. "
      f"{summary['residual_closed']} of them reduce to a single unknown "
      "operation, which is the only case where the residual is a point value.")
    A("")
    A("Residual rows subtract **only reported property revenue**, never a "
      "single-property attribution. Subtracting an inference would propagate it "
      "into a published bound with nothing on the row to say so.")
    A("")
    A("## 5. Connecticut as the validation case")
    A("")
    A("Connecticut is the one state where Cedar holds every property's revenue, "
      "so it is the one place the residual can be checked. **The check does not "
      "reconcile, and the reason is the finding.**")
    A("")
    A("| NIGC FY | CT slot win | Washington DC region GGR | CT share | "
      "operations in region |")
    A("|---:|---:|---:|---:|---:|")
    for c in ct[-8:]:
        A(f"| {c['fiscal_year']} | ${c['ct_slot_win_usd']/1e9:.2f}B | "
          f"${c['region_ggr_usd']/1e9:.2f}B | {c['ct_share_pct']:.1f}% | "
          f"{c['operations_in_region']} |")
    A("")
    A("Two independent reasons, both structural:")
    A("")
    A("1. **Region is not state.** NIGC's Washington DC region covers Alabama, "
      "Connecticut, Florida, Louisiana, Mississippi, North Carolina and New "
      "York - Seminole Hard Rock is in the same bucket as Foxwoods. Connecticut "
      "is 2 of 46 operations in FY2025.")
    A("2. **Slot win is not GGR.** Connecticut publishes *\"Win (9)\"*, slot "
      "machine win. It excludes table games, which both properties run at "
      "scale. The Connecticut figure is a FLOOR on the property's "
      "NIGC-comparable GGR and is stored as one.")
    A("")
    A("So the Connecticut sum SHOULD sit well under the regional total, and it "
      "does. A reconciliation would have been evidence of an error, not of "
      "success.")
    A("")
    A("## 6. How far residual elimination is from being usable")
    A("")
    A("The question worth answering. `more needed` counts additional property "
      "revenues before a single operation remains unknown in that region-year.")
    A("")
    A("| NIGC region | FY | operations | known (reported) | known (incl. "
      "attributed) | more needed | best-covered year |")
    A("|---|---:|---:|---:|---:|---:|---|")
    for g in summary["residual_gap_by_region"]:
        A(f"| {g['region_name']} | {g['fiscal_year']} | {g['operations']} | "
          f"{g['known_reported_property_revenues']} | "
          f"{g['known_including_single_property_attributed']} | "
          f"{g['more_needed_for_single_unknown_including_attributed']} | "
          f"FY{g['best_covered_year']} ({g['best_covered_year_known']} known) |")
    A("")
    A("**These counts are a floor on the work, not a target, and strict "
      "residual elimination is probably unreachable in most regions at any "
      "coverage.** NIGC's `operation_count` counts submitters of audited "
      "financial statements, not buildings. One submitter can cover several "
      "properties, so a complete property file still would not put the two "
      "universes in 1:1 correspondence, and `n_known == operations - 1` would "
      "remain unverifiable.")
    A("")
    A("What DOES scale with coverage is the tighter ceiling: every additional "
      "known property revenue lowers `REGIONAL_GGR_CEILING_NET_OF_KNOWN` for "
      "every other property in the same region-year. That is a real, "
      "monotonic gain and it needs no closure.")
    A("")
    A("The highest-yield next pulls, from the table above: **Washington DC** "
      "(46 operations, smallest region with the largest GGR, and 2 already "
      "known), then **Rapid City** (44) and **Phoenix** (54). St. Paul at 101 "
      "operations and Sacramento at 88 are the furthest away.")
    A("")
    A("## Guards that ran")
    A("")
    A("- `cedar_domain.may_promote(DERIVED_BOUND, ACTIVE_FLOOR_COUNT)` is "
      "asserted False at runtime. A bound can never be relabelled an "
      "observation.")
    A("- Every `measurement_status` is checked against "
      "`cedar_domain.REVENUE_EVIDENCE` plus `SINGLE_PROPERTY_ATTRIBUTED`.")
    A("- Every row must carry a `bound_basis` and must bound something; a row "
      "with three empty value columns stops the build.")
    A("- No row may have a lower bound above its upper bound.")
    A("- **No row may contain the words** *estimate*, *predicted*, *confidence "
      "interval*, *forecast*, *imputed* or *modelled*, in any column. Scanned "
      "on every build.")
    A("- `resolve_entity` from `code/33_apply_party_rulings.py` is the only "
      "name matcher used. No second matcher was written.")
    A("")
    A("## Files this build did not touch")
    A("")
    A("`gaming_facilities.csv`, `gaming_capacity_official.csv`, "
      "`nigc_regional_ggr.csv`, `nigc_region_assignments.csv`, `compact_*`, "
      "`ca_gaming_*`, the spine, and every other file owned elsewhere. This "
      "layer is additive: two new clean files, one review file, one codebook, "
      "this log.")
    A("")
    A("**One step is deliberately left open.** The codebook is written as "
      "`docs/codebooks/07e_revenue_bounds.md`, following the precedent of "
      "scripts 84 and 100, which write their own. It is NOT yet registered in "
      "`code/41_build_codebooks.py`'s `DATASETS`, so the two files do not "
      "appear in `codebook_master.csv`. That file was being rewritten by "
      "another agent's run of script 41 while this build was running, and "
      "editing 41 concurrently would have collided. Adding "
      "`\"07e_revenue_bounds\": [\"gaming_revenue_bounds.csv\", "
      "\"nigc_revenue_bands.csv\"]` and re-running 41 is the whole remaining "
      "job. Note that `bound_basis` is already in 41's `PUBLIC_OVERRIDE`, so "
      "the generic `_basis$` internal rule will not swallow it.")
    A("")
    A("A standing failure in `code/62_no_regression_check.py` "
      "(`codebook_undocumented_public = 10`) predates this build and belongs to "
      "datasets 06 and 12. It was verified as pre-existing, not caused here, "
      "and not touched.")
    A("")
    A(f"Source quotes were located in the NIGC report text for "
      f"{len(ctx['quotes'])} of 198 region-years. The gap is the FY2013-FY2020 "
      "map-only reports, which print `$4.8B` rather than a full figure and "
      "carry `figure_precision = rounded_0.1B` upstream; those rows leave "
      "`source_quote` blank rather than restating a figure the document never "
      "printed.")
    A("")
    p.write_text("\n".join(L), encoding="utf-8")
    print(f"  wrote {p.relative_to(CEDAR)}")


# =========================================================================
# MAIN
# =========================================================================
def main():
    print("=" * 74)
    print("106_build_revenue_bounds.py -- gaming revenue bounds layer")
    print("=" * 74)
    bands = build_bands()
    rows, refusals, ctx = build_bounds(bands)

    # region_of is needed by the gap report; rebuild it cheaply.
    assigns = read_csv(CLEAN / "nigc_region_assignments.csv")
    region_of = {}
    for a in assigns:
        rid = (a.get("administrative_region_id") or "").strip()
        s, e = yr(a.get("effective_start_year")), yr(a.get("effective_end_year"))
        if not rid or s is None:
            continue
        for fy in range(s, (e if e is not None else 2025) + 1):
            region_of[(a["facility_id"], fy)] = rid
    ctx["region_of"] = region_of

    ct = validate_connecticut(ctx)
    gap = residual_gap_by_region(ctx)

    summary = {
        "built_date": TODAY,
        "bound_rows": len(rows),
        "band_rows": len(bands),
        "by_basis": {b: sum(1 for r in rows if r["bound_basis"] == b)
                     for b in sorted({r["bound_basis"] for r in rows})},
        "by_status": {s: sum(1 for r in rows if r["measurement_status"] == s)
                      for s in sorted({r["measurement_status"] for r in rows})},
        "properties_with_a_ceiling": len({r["facility_id"] for r in rows
                                          if r["bound_basis"] == "REGIONAL_GGR_CEILING"}),
        "single_property_attributed": ctx["attributed"],
        "single_property_refused": len(refusals),
        "residual_region_years": ctx["residual_rows"],
        "residual_closed": ctx["residual_closed"],
        "ct_validation": [{"fiscal_year": c[0], "region": c[1],
                           "ct_slot_win_usd": int(c[2]),
                           "region_ggr_usd": int(c[3]),
                           "ct_share_pct": round(c[4], 2),
                           "operations_in_region": c[5]} for c in ct],
        "residual_gap_by_region": gap,
        "roster_gap_total": ctx["n_gaps"],
        "roster_gap_alias_of_held": sum(len(v) for v in ctx["aliases"].values()),
        "roster_gap_blocking": sum(len(v) for v in ctx["blocking"].values()),
        "roster_gap_unattributed_by_state": ctx["unattributed_state"],
        "skipped_non_igra_assignment_rows": ctx["skipped_non_igra"],
        "skipped_unassigned_rows": ctx["skipped_no_region"],
    }
    (CLEAN / "_revenue_bounds_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8")
    print("\n  wrote data/clean/_revenue_bounds_summary.json")

    print("\n=== 5. DOCS ===")
    write_codebook()
    write_log(summary, ctx, bands, refusals)
    print(json.dumps(summary["by_basis"], indent=2))
    return summary


if __name__ == "__main__":
    main()
