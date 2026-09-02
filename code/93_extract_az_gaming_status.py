#!/usr/bin/env python3
"""
93_extract_az_gaming_status.py -- Arizona Dept of Gaming "Gaming Status Report".

WHY THIS EXISTS SEPARATELY
--------------------------
This one PDF is the richest independent per-property capacity source found
anywhere in the 50-state sweep: for 26 named tribal casinos it publishes, in one
table, Class III devices, Class II devices, blackjack tables, house-banked poker
tables, poker tables, baccarat, craps, roulette, DCETG, live keno and event
wagering positions -- plus the date the casino first opened and the effective
date of its current compact. It is the direct independent replacement for the
vendor panel's core metric.

A first pass by a survey agent read it linearly and dropped 20 of the 26 Class II
values, because the table has a RAGGED text layer: some rows omit the DCETG cell
entirely, so field N is a different column on different rows. Reading this table
by counting tokens cannot work.

So this extractor is POSITIONAL -- it bins every number by its x-coordinate
against the column header positions -- and then it is CHECKED: each column is
summed and compared against the report's own printed TOTALS row. A column that
does not foot is not published.

  Class III 21,084 | Class II 572 | Blackjack 310 | House-banked poker 86
  Poker 175 | Baccarat 19 | Craps 21 | Roulette 35 | DCETG 0

Two structural facts about this table that must not be lost:

  1. Two rows are marked "Class II Only *" (Pascua Yaqui / Del Sol Marketplace,
     Tohono O'odham / Desert Diamond - Why) and carry `--` in every Class III and
     table column. The footnote says these are "not regulated by the Arizona
     Department of Gaming or Tribal-State Compacts". `--` is NOT zero and is
     never recorded as zero -- the cell is absent, so no row is emitted.
  2. A second table lists tribes with a "Current Gaming Device Allocation" and
     NO casino. That is an AUTHORISATION, not an operating count, and is emitted
     as `gaming_machines_authorized_max`.

Writes data/raw/external/gaming_official/az_adg_status_report_extracted_<date>.csv
in the standard agent-evidence schema, which script 92 then ingests.
"""
import csv, os, re, collections
import fitz
from pathlib import Path

BASE = str(Path(__file__).resolve().parent.parent)
RAW = os.path.join(BASE, "data", "raw", "external", "gaming_official")
PDF = os.path.join(RAW, "az_adg_gaming_status_report_20260701.pdf")
OUT = os.path.join(RAW, "az_adg_status_report_extracted_2026-08-06.csv")

SRC_URL = ("https://gaming.az.gov/sites/default/files/"
           "Gaming%20Status%20Report%2007012026_0.pdf")
AUTHORITY = "Arizona Department of Gaming"
AS_OF = "2026-07-01"          # "STATUS OF TRIBAL GAMING IN ARIZONA AS OF 07/01/26"
TODAY = "2026-08-06"

# column header -> (metric, unit). Order is left-to-right in the PDF.
COLUMNS = [
    ("Class III\nGaming\nDevices", "class_iii_gaming_machines", "devices", 21084),
    ("Class II\nGaming\nDevices", "class_ii_gaming_machines", "devices", 572),
    ("Blackjack\nTables", "blackjack_tables", "tables", 310),
    ("House\nBanked\nPoker\nTables", "house_banked_poker_tables", "tables", 86),
    ("Poker\nTables", "poker_tables", "tables", 175),
    ("Baccarat\nTables", "baccarat_tables", "tables", 19),
    ("Craps\nTables", "craps_tables", "tables", 21),
    ("Roulette\nTables", "roulette_tables", "tables", 35),
    ("DCETG", "dcetg", "tables", 0),
]

# Tribe attribution for each casino, taken from the report's own Tribe column.
# The table uses a merged Tribe cell spanning several casino rows, so the tribe
# is carried down explicitly here rather than inferred from row adjacency.
CASINO_TRIBE = {
    "Harrah's Ak-Chin Casino": "Ak-Chin Indian Community",
    "Cocopah Casino": "Cocopah Indian Tribe",
    "Blue Water Casino": "Colorado River Indian Tribes",
    "We-Ko-Pa Casino": "Ft. McDowell Yavapai Nation",
    "Spirit Mountain Casino": "Fort Mojave Indian Tribe",
    "Gila River - Lone Butte": "Gila River Indian Community",
    "Gila River - San Tan Mountain": "Gila River Indian Community",
    "Gila River - Vee Quiva": "Gila River Indian Community",
    "Gila River - Wild Horse Pass": "Gila River Indian Community",
    "Twin Arrows Casino": "Navajo Nation",
    "Casino del Sol": "Pascua Yaqui Tribe",
    "Casino of the Sun": "Pascua Yaqui Tribe",
    "Del Sol Marketplace": "Pascua Yaqui Tribe",
    "Paradise Casino": "Quechan Indian Tribe",
    "Casino Arizona": "Salt River Pima-Maricopa Indian Community",
    "Talking Stick Resort and Casino": "Salt River Pima-Maricopa Indian Community",
    "Apache Gold Casino": "San Carlos Apache Tribe",
    "Apache Sky Casino": "San Carlos Apache Tribe",
    "Desert Diamond - Tucson": "Tohono O'odham Nation",
    "Desert Diamond - Sahuarita": "Tohono O'odham Nation",
    "Desert Diamond - West Valley": "Tohono O'odham Nation",
    "Desert Diamond - White Tanks": "Tohono O'odham Nation",
    "Desert Diamond - Why": "Tohono O'odham Nation",
    "Mazatzal Casino": "Tonto Apache Tribe",
    "Hon-Dah Casino": "White Mountain Apache Tribe",
    "Cliff Castle Casino": "Yavapai-Apache Nation",
    "Bucky's Casino - Prescott Resort": "Yavapai-Prescott Indian Tribe",
    "Yavapai Gaming Center": "Yavapai-Prescott Indian Tribe",
}

# Rows the report itself marks "Class II Only *" with `--` across the board.
CLASS_II_ONLY = {"Del Sol Marketplace", "Desert Diamond - Why"}


def main():
    doc = fitz.open(PDF)
    page = doc[0]
    words = page.get_text("words")   # (x0, y0, x1, y1, word, block, line, wordno)

    # ---- THE PAGE IS ROTATED 90 DEGREES -------------------------------------
    # `page.rotation == 90`, so the visual table is transposed in PDF space:
    # a visual COLUMN is a band of constant Y, and a visual ROW is a band of
    # constant X. Reading it with the usual x=column assumption produced every
    # column centre at x~65 and a zero for every total -- which the totals check
    # caught. Column key is therefore the Y centre and row key is the X centre.
    def ycen(w):
        return (w[1] + w[3]) / 2.0

    def xcen(w):
        return (w[0] + w[2]) / 2.0

    # Anchor each numeric column on a distinctive header token. `II` is a
    # substring of `III` as a STRING but they are separate word tokens here, so
    # exact token equality separates them cleanly.
    anchors = [
        ("class_iii_gaming_machines", "III"),
        ("class_ii_gaming_machines", "II"),
        ("blackjack_tables", "Blackjack"),
        ("house_banked_poker_tables", "Banked"),
        ("poker_tables", "Poker"),
        ("baccarat_tables", "Baccarat"),
        ("craps_tables", "Craps"),
        ("roulette_tables", "Roulette"),
        ("dcetg", "DCETG"),
    ]
    # Header words all sit in the leftmost X band (the top of the visual page).
    header_x = min(w[0] for w in words if w[4] == "Blackjack")
    band = [w for w in words if w[0] < header_x + 40]
    centres = {}
    for metric, tok in anchors:
        cands = [w for w in band if w[4] == tok]
        if not cands:
            print(f"  !! header token not found: {tok}")
            continue
        if metric == "poker_tables":
            # `Poker` occurs in both "House Banked Poker Tables" and "Poker
            # Tables". Visual left-to-right is DESCENDING Y on a 90-rotated
            # page, so the standalone Poker column is the LOWER Y of the two.
            w = min(cands, key=ycen)
        elif metric == "house_banked_poker_tables":
            w = max(cands, key=ycen)
        else:
            w = cands[0]
        centres[metric] = ycen(w)
    print("  column centres (y, visual left-to-right = descending y):")
    for k, v in sorted(centres.items(), key=lambda kv: -kv[1]):
        print(f"      {k:32s} y={v:7.1f}")

    ordered = sorted(centres.items(), key=lambda kv: -kv[1])

    # ---- assign each casino row -------------------------------------------
    rows_out = []
    sums = collections.Counter()
    found = {}
    for casino, tribe in CASINO_TRIBE.items():
        hits = page.search_for(casino)
        if not hits:
            print(f"  !! casino label not found in PDF: {casino}")
            continue
        r = hits[0]
        xmid = (r.x0 + r.x1) / 2.0
        # Same visual row = same X band; data cells sit BELOW the label in
        # visual terms, i.e. at LOWER Y than the casino-name cell.
        line = [w for w in words if abs(xcen(w) - xmid) < 6 and ycen(w) < r.y0]
        vals = {}
        for w in line:
            tok = w[4].replace(",", "")
            if not re.fullmatch(r"-?\d+", tok):
                continue
            cy = ycen(w)
            metric, dist = None, 1e9
            for m, c in ordered:
                if abs(cy - c) < dist:
                    metric, dist = m, abs(cy - c)
            if dist <= 14:
                vals[metric] = int(tok)
        found[casino] = vals
        for m, v in vals.items():
            sums[m] += v

    # ---- CHECK against the report's own printed totals ---------------------
    print("\n  column totals vs the report's printed TOTALS row:")
    ok_metrics = set()
    for _, metric, _, printed in COLUMNS:
        got = sums.get(metric, 0)
        flag = "OK " if got == printed else "MISMATCH"
        if got == printed:
            ok_metrics.add(metric)
        print(f"    {flag}  {metric:32s} extracted {got:6,}   printed {printed:6,}")

    unit_of = {m: u for _, m, u, _ in COLUMNS}
    for casino, vals in found.items():
        tribe = CASINO_TRIBE[casino]
        for metric, v in sorted(vals.items()):
            if metric not in ok_metrics:
                continue          # a column that does not foot is not published
            if casino in CLASS_II_ONLY and metric != "class_ii_gaming_machines":
                continue          # `--` is not zero
            rows_out.append(dict(
                facility_name_as_published=casino,
                tribe_name_as_published=tribe,
                state="AZ",
                metric=metric,
                value=v,
                unit=unit_of[metric],
                as_of_date=AS_OF,
                as_of_date_precision="day",
                period_start="", period_end="",
                source_authority=AUTHORITY,
                source_document_type="state_regulator_status_report",
                source_url=SRC_URL,
                source_quote=(
                    f'"STATUS OF TRIBAL GAMING IN ARIZONA AS OF 07/01/26"; row '
                    f'"{casino}" ({tribe}); column "'
                    f'{[c[0] for c in COLUMNS if c[1] == metric][0]}".replace = {v}; '
                    f'column verified against the report\'s own printed TOTALS row '
                    f'({[c[3] for c in COLUMNS if c[1] == metric][0]:,})'),
                fetched_date=TODAY))

    # ---- the comparable device TOTAL ---------------------------------------
    # Most casinos have a BLANK Class II cell, and blank is not zero as a
    # general rule. Here, though, the document proves its own convention: the
    # printed Class II total of 572 is exactly the sum of the SIX stated values
    # (109 + 400 + 9 + 6 + 8 + 40), so ADG's own arithmetic treats a blank cell
    # as contributing nothing. That is evidence from the document rather than an
    # assumption about it, and it is what licenses a total here.
    #
    # The total matters because `gaming_machines` is the metric a directory
    # sells and the one the vendor panel carries; without it the Arizona rows
    # cannot be compared to anything.
    stated_ii = {c: v["class_ii_gaming_machines"] for c, v in found.items()
                 if "class_ii_gaming_machines" in v}
    assert sum(stated_ii.values()) == 572, "Class II footing changed - re-derive the rule"
    made = 0
    for casino, vals in found.items():
        if "class_iii_gaming_machines" not in vals:
            continue                      # Class II only facility; no total to state
        iii = vals["class_iii_gaming_machines"]
        ii = vals.get("class_ii_gaming_machines", 0)
        rows_out.append(dict(
            facility_name_as_published=casino,
            tribe_name_as_published=CASINO_TRIBE[casino],
            state="AZ", metric="gaming_machines", value=iii + ii, unit="machines",
            as_of_date=AS_OF, as_of_date_precision="day",
            period_start="", period_end="",
            source_authority=AUTHORITY,
            source_document_type="state_regulator_status_report",
            source_url=SRC_URL,
            source_quote=(
                f'"STATUS OF TRIBAL GAMING IN ARIZONA AS OF 07/01/26"; row "{casino}"; '
                f'"Class III Gaming Devices" = {iii:,} plus "Class II Gaming Devices" = '
                f'{ii:,}'
                + ("" if "class_ii_gaming_machines" in vals else
                   " (Class II cell blank; the report\'s own printed Class II total of "
                   "572 equals the sum of the six stated values, so a blank cell "
                   "contributes zero in ADG\'s own arithmetic)")
                + f'. Both component columns verified against the report\'s printed '
                  f'TOTALS row (21,084 and 572).'),
            fetched_date=TODAY))
        made += 1
    print(f"  device totals emitted: {made}")

    cols = list(rows_out[0].keys())
    with open(OUT, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows_out)
    print(f"\n  wrote {OUT}  ({len(rows_out)} rows, "
          f"{len(found)} casinos, {len(ok_metrics)} verified columns)")


if __name__ == "__main__":
    main()
