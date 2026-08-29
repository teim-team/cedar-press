#!/usr/bin/env python3
"""
94_extract_mi_mgcb_revshare.py -- Cedar Press.

WHY THIS EXISTS
---------------
The Michigan Gaming Control Board publishes two per-tribe payment tables that
nothing else in the market carries at tribe granularity:

  * Tribal 2% Payments to Local Units of State Government   (1993 -> current)
  * Tribal Payments to Michigan Strategic Fund / MEDC       (1993 -> current)

The first pass over Michigan landed 15 observations. The reason is recorded
here because it is the same defect script 93 caught in Arizona and it will
recur:

    `pdftotext -layout` SHIFTS THE TRIBE-NAME COLUMN BY ONE ROW.

The MGCB tables set the tribe name and its numbers on baselines that differ by
1-2 points. The linear text layer therefore emits the numbers of tribe N on the
line that carries the NAME of tribe N+1. Read linearly, Bay Mills' money lands
on Grand Traverse, Grand Traverse's on Gun Lake, and so on down the whole
column -- every row well-sourced, every row attached to the wrong nation. That
is the containment defect in AGENTS.md wearing a different costume.

So this reads WORD POSITIONS, groups baselines within a tolerance, assigns each
number to a column by its RIGHT EDGE against bands learned from the printed
TOTALS row, and then CHECKS every column against that TOTALS row. A column that
does not foot is reported and not published.

WRITES
  data/raw/external/gaming_official/mi_mgcb_revshare_extracted_<date>.csv
    (agent-evidence schema; `code/92_build_gaming_capacity_official.py` picks it
     up with no code change)
"""
import csv, collections, re
from pathlib import Path

import pdfplumber

CEDAR = Path(__file__).resolve().parent.parent
RAW = CEDAR / "data" / "raw" / "external" / "gaming_official"
TODAY = "2026-08-07"

MONEY = re.compile(r"^\$?-?[\d,]+\.\d{2}$")

SOURCES = [
    dict(
        pdf="mi_mgcb_revshare_payments_to_local_2023-04-03.pdf",
        url=("https://www.michigan.gov/mgcb/-/media/Project/Websites/mgcb/Detroit"
             "-Casinos/Tribal-Casinos/Tribal-2-Payments-to-Local-Units-of-State"
             "-Government.pdf"),
        metric="payment_to_local_government",
        payee="local units of state government (compact 2% payments)",
        doctype="state_regulator_payment_table",
    ),
    dict(
        pdf="mi_mgcb_revshare_payments_to_medc_msf_2023-04-03.pdf",
        url=("https://www.michigan.gov/mgcb/-/media/Project/Websites/mgcb/Detroit"
             "-Casinos/Tribal-Casinos/Tribal-Payments-to-Michigan-Strategic-Fund"
             "-or-Michigan-Economic-Development-Corporation.pdf"),
        metric="payment_to_state",
        payee="Michigan Strategic Fund / Michigan Economic Development Corporation",
        doctype="state_regulator_payment_table",
    ),
]

AUTHORITY = "Michigan Gaming Control Board"


def money(t):
    return float(t.replace("$", "").replace(",", ""))


def extract(pdf_path):
    """-> (rows, header_years, totals_row) with rows = [(tribe, {col: value})]."""
    with pdfplumber.open(pdf_path) as pdf:
        words = pdf.pages[0].extract_words()

    # group baselines: MGCB sets a name and its numbers up to ~3pt apart
    bands = []
    for w in sorted(words, key=lambda z: z["top"]):
        if bands and w["top"] - bands[-1][0] <= 3.0:
            bands[-1][1].append(w)
        else:
            bands.append([w["top"], [w]])
    lines = [(t, sorted(ws, key=lambda z: z["x0"])) for t, ws in bands]

    # ---- header: the year row carries the column labels ---------------------
    years, hdr_top = [], None
    for t, ws in lines:
        ys = [w for w in ws if re.fullmatch(r"(19|20)\d{2}", w["text"])]
        if len(ys) >= 5:
            years = ys
            hdr_top = t
            break
    if not years:
        raise SystemExit(f"no year header found in {pdf_path.name}")

    # ---- the printed TOTALS row defines the column bands --------------------
    totals_line = None
    for t, ws in lines:
        txt = " ".join(w["text"] for w in ws)
        if txt.lower().startswith("total") and sum(
                1 for w in ws if MONEY.match(w["text"])) >= 5:
            totals_line = (t, ws)
    if totals_line is None:
        raise SystemExit(f"no printed TOTALS row in {pdf_path.name}")
    tot_nums = [w for w in totals_line[1] if MONEY.match(w["text"])]

    # column identity = right edge of the TOTALS row cells. Right edges are
    # stable across digit counts; left edges are not.
    cols = [w["x1"] for w in tot_nums]

    # name the columns. The first money column is the cumulative "1993 - <yr>"
    # column, then one per header year, then the LTD total.
    names = ["cumulative_prior"] + [w["text"] for w in years] + ["ltd_total"]
    if len(names) != len(cols):
        # fall back: label by nearest header year where one exists
        names = []
        for x1 in cols:
            near = min(years, key=lambda w: abs(w["x1"] - x1))
            names.append(near["text"] if abs(near["x1"] - x1) < 45 else f"col_{x1:.0f}")
        names[0] = "cumulative_prior"
        names[-1] = "ltd_total"

    def col_of(x1):
        i = min(range(len(cols)), key=lambda k: abs(cols[k] - x1))
        return names[i] if abs(cols[i] - x1) <= 45 else None

    out, totals = [], {}
    for w in tot_nums:
        c = col_of(w["x1"])
        if c:
            totals[c] = money(w["text"])

    for t, ws in lines:
        if t <= hdr_top or ws is totals_line[1]:
            continue
        if t >= totals_line[0]:
            break
        name = " ".join(w["text"] for w in ws if not MONEY.match(w["text"]))
        name = re.sub(r"\*+", "", name).strip()
        if not name or len(name) < 4:
            continue
        vals = {}
        for w in ws:
            if MONEY.match(w["text"]):
                c = col_of(w["x1"])
                if c:
                    vals[c] = money(w["text"])
        if vals:
            out.append((name, vals, " ".join(w["text"] for w in ws)))
    return out, names, totals


def main():
    rows, report = [], []
    for src in SOURCES:
        p = RAW / src["pdf"]
        if not p.exists():
            print(f"  MISSING {src['pdf']}")
            continue
        data, names, totals = extract(p)
        print(f"\n=== {src['pdf']}   {len(data)} tribe rows, columns {names}")

        # ---- foot every column against the document's own TOTALS row --------
        ok_cols = set()
        for c in names:
            s = sum(v.get(c, 0.0) for _, v, _ in data)
            printed = totals.get(c)
            if printed is None:
                print(f"    {c:18s} no printed total -- column NOT published")
                continue
            good = abs(s - printed) < 1.0
            print(f"    {c:18s} sum {s:>18,.2f} vs printed {printed:>18,.2f}"
                  f"   {'OK' if good else '*** DOES NOT FOOT ***'}")
            if good:
                ok_cols.add(c)
            report.append((src["pdf"], c, s, printed, good))

        for name, vals, raw in data:
            for c, v in sorted(vals.items()):
                if c not in ok_cols:
                    continue
                if c == "ltd_total":
                    continue          # a life-to-date cumulative, not a period
                if c == "cumulative_prior":
                    continue          # spans an unstated multi-year window
                yr = int(c)
                rows.append(dict(
                    facility_name_as_published="",      # MGCB reports per TRIBE
                    tribe_name_as_published=name,
                    state="MI",
                    metric=src["metric"],
                    value=f"{v:.2f}",
                    unit="usd",
                    as_of_date=f"{yr}-12-31",
                    as_of_date_precision="year",
                    period_start=f"{yr}-01-01",
                    period_end=f"{yr}-12-31",
                    source_authority=AUTHORITY,
                    source_document_type=src["doctype"],
                    source_url=src["url"],
                    source_quote=(f'{name} | column "{c}" = ${v:,.2f} | payee: '
                                  f'{src["payee"]} | table line as printed: {raw}')[:900],
                    fetched_date="2026-08-06",
                ))

    # =====================================================================
    # EXACT DERIVED REVENUE -- spec 9.4's one honest route to real revenue
    # =====================================================================
    # "Where a public payment meets an invertible formula, `payment / rate` is
    #  exact arithmetic -- the one honest route to real property revenue --
    #  provided the revenue concept is preserved."  (SPEC_v2 sec 9.4)
    #
    # Michigan's 1999 Consent Decree compacts state the formula verbatim, and
    # the clause was verified WORD FOR WORD in all four of the 1999 compact
    # texts this project already holds:
    #
    #   "Payment in the aggregate amount equal to two percent (2%) of the net
    #    win at each casino derived from all Class III electronic games of
    #    chance, as those games are defined in this Compact."
    #
    # So net win from Class III electronic games = payment / 0.02, EXACTLY.
    #
    # THREE limits are carried on every derived row rather than discovered by a
    # subscriber later:
    #
    #  1. THE REVENUE CONCEPT IS NARROW. It is net win from CLASS III
    #     ELECTRONIC GAMES OF CHANCE ONLY. It is not total casino revenue: no
    #     table games, no Class II, no poker, no non-gaming. Reporting it as
    #     "casino revenue" would overstate nothing and understate a great deal,
    #     which is the subtler and more dangerous error.
    #  2. IT IS TRIBE-LEVEL. The clause says "the aggregate amount ... at each
    #     casino", so a tribe with three casinos remits one number covering all
    #     three. `facility_id` stays blank and that blank is meaningful.
    #  3. IT IS RESTRICTED TO THE FOUR 1999-COMPACT TRIBES. The 1993 compact
    #     texts on disk do NOT contain a 2% clause -- the obligation for those
    #     tribes arrives through Consent Judgments this project does not hold.
    #     MGCB's annual report prints "2%" against every tribe, but a
    #     regulator's summary table is not the operative instrument, and the
    #     derivation is only as good as the instrument. The other eight tribes
    #     are left as payments only.
    #
    # Footnoted tribe-years are excluded by flag, not silently: MGCB's own
    # footnotes say some totals include escrow, excess distributions or
    # prorated advances, and for those years payment / 0.02 is NOT the net win.
    DERIVABLE = {
        # tribe name as MGCB prints it -> compact text file that states the rate
        "Little River Band of Ottawa Indians":
            "508_compliant_1999.02.18_little_river_band_of_ottawa_indians_"
            "tribal_state_gaming_compact.txt",
        "Little Traverse Bay Bands of Odawa Indians":
            "508_compliant_1999.02.18_little_traverse_bay_bands_of_odawa_indians_"
            "tribal_state_gaming_compact.txt",
        "Nottawaseppi Huron Band of the Potawatomi":
            "508_compliant_1999.02.18_nottawaseppi_huron_band_of_potawatomi_"
            "tribal_state_gaming_compact.txt",
        "Pokagon Band of Potawatomi Indians":
            "508_compliant_1999.02.18_pokagon_band_of_potawatomi_"
            "tribal_state_gaming_compact.txt",
    }
    CLAUSE = ("Payment in the aggregate amount equal to two percent (2%) of the "
              "net win at each casino derived from all Class III electronic games "
              "of chance, as those games are defined in this Compact.")
    derived = 0
    for r in list(rows):
        if r["metric"] != "payment_to_local_government":
            continue
        name = r["tribe_name_as_published"]
        if name not in DERIVABLE:
            continue
        footnoted = "*" in r["source_quote"].split("table line as printed:")[-1]
        rows.append(dict(
            r,
            metric="net_win",
            value=f"{float(r['value']) / 0.02:.2f}",
            unit="usd",
            measurement_status="exact_derived_revenue",
            measurement_type="COMPACT_REPORTED_COUNT",
            applies_to="tribe_aggregate_all_casinos",
            qualifier=(
                "EXACT ARITHMETIC, not an estimate: the tribe's published 2% "
                "payment divided by the compact's stated 2% rate. REVENUE "
                "CONCEPT: net win from CLASS III ELECTRONIC GAMES OF CHANCE "
                "only -- not table games, not Class II, not non-gaming, and "
                "not total casino revenue. Aggregate across all of the tribe's "
                "casinos, so it is a TRIBE-level figure with no property split."),
            exclusion_flag="1" if footnoted else "",
            exclusion_reason=(
                "MGCB footnotes this tribe's 2% payment total (escrow, excess "
                "distributions or a prorated advance), so payment / 0.02 is not "
                "the net win for these years" if footnoted else ""),
            source_quote=(
                f'DERIVED payment/rate. RATE (compact, verbatim): "{CLAUSE}" '
                f'[{DERIVABLE[name]}]. PAYMENT (regulator): ' + r["source_quote"]
            )[:1500],
            source_authority=(AUTHORITY + " (payment) + Tribal-State Gaming Compact, "
                              "Michigan, 1999 (rate)"),
            source_document_type="exact_derived_from_statutory_formula",
        ))
        derived += 1
    print(f"\nexact-derived Class III electronic net win: {derived} tribe-years "
          f"({len(DERIVABLE)} tribes whose compact states the 2% rate verbatim)")

    outp = RAW / f"mi_mgcb_revshare_extracted_{TODAY}.csv"
    if rows:
        cols = list(rows[0].keys()) + [c for c in (
            "measurement_status", "measurement_type", "applies_to", "qualifier",
            "exclusion_flag", "exclusion_reason") if c not in rows[0]]
        with open(outp, "w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
            w.writeheader()
            w.writerows(rows)
    print(f"\nwrote {outp.name}  ({len(rows):,} rows)")
    print("tribes:", len({r["tribe_name_as_published"] for r in rows}))
    print("years :", sorted({r["period_end"][:4] for r in rows}))


if __name__ == "__main__":
    main()
