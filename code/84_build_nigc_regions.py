#!/usr/bin/env python3
"""
Cedar Press - 84: The NIGC administrative region layer.

ELIJAH, 2026-08-06
------------------
"id rather someone else estimate reveneu than us lol"

"to the extent we can use different federal sources to sanity check we should"

WHAT IS MEASURED
----------------
NIGC publishes gross gaming revenue at the REGION level and nowhere else. This
script states three measured things and refuses a fourth.

  1. `nigc_regional_ggr.csv` - the regional GGR series as NIGC printed it,
     FY2001-FY2025, transcribed from the agency's own PDFs, carrying the region
     system that was in force in each year rather than today's map.

  2. `nigc_region_assignments.csv` - which NIGC region each of our gaming
     properties sits in, assigned by PROPERTY LOCATION, dated to the region
     system version that was in force.

  3. `review/nigc_roster_diff_*.csv` - a row-level diff of our property file
     against NIGC's published gaming location list. The rows NIGC has that we
     do not are the highest-value output here.

WHAT IS REFUSED
---------------
**No property-level revenue. Not modelled, not allocated, not constrained.**

A source report proposed a MODELED_PROPERTY_GGR column - regional GGR divided
across properties, calibrated to sum back to the regional total. It is refused,
and NIGC's own FY2025 distribution is why:

    ~9% of operations reported over $250M and made ~56% of GGR.
    54%+ of operations reported under $25M and together made ~5%.
                                       - GGR25_071526.pdf, "Revenue by Range"

FY2025 GGR was $46.16B across 545 operations, so an even split is $84.7M each.
For the 54% of operations under $25M that is wrong by at least 3.4x, and for
the largest properties it is wrong by an order of magnitude the other way. A
constrained allocation that sums to the regional total is not more defensible -
it is the same error with a reconciliation check bolted on.

**A property being INCLUDED IN a regional revenue universe is not the same as
that property GENERATING the region's revenue.** A regional average appears
below only as `region_mean_ggr_per_operation_usd`, labelled a descriptive
statistic, never joined to a property.

**GGR IS GAMING WIN.** It excludes hotel, restaurant, entertainment and retail,
and it is measured BEFORE wages, operating expenses, debt service, compact
payments to states and reinvestment. It is not resort revenue and it is not
tribal government income. `includes_nongaming_revenue` is false on every row and
`measure_note` says so on every row.

THE SERIES IS NOT TIMELESS AND THAT IS THE POINT
------------------------------------------------
NIGC has used FOUR region systems since FY2001. Applying today's eight-region
map to a 2002 revenue report would produce a chart that looks continuous and
is not:

  R1  FY2001-FY2002 reports  6 regions  Region I-V + "Eastern Region"
  R2  FY2003-FY2007 reports  6 regions  Eastern renamed VI; MONTANA MOVED I->IV
  R3  FY2008-FY2016 reports  7 regions  city names; Region V split Tulsa/OK City
  R4  FY2017 report onward   8 regions  Rapid City split out of St. Paul

R1->R2 is the dangerous kind: Region I and Region IV kept their names while
their boundaries moved. Measured in NIGC's own documents - the FY2002 report put
72 operations in Region I; the FY2003 report, restating FY2002 without Montana,
put 47 there.

The 7->8 change is dated FY2017, NOT FY2020. Measured: the FY16 map shows St.
Paul with 132 audited financial statements and no Rapid City region; the FY17
map restates FY2016 as St. Paul 93 + Rapid City 39 = 132.

Writes data/clean/nigc_regional_ggr.csv
       data/clean/nigc_region_assignments.csv
       review/nigc_coverage_gap_<date>.csv
       review/nigc_roster_diff_<date>.csv
       review/nigc_series_breaks_<date>.csv
       review/nigc_region_conflicts_<date>.csv
"""

import csv
import importlib.util
import json
import math
import re
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

CEDAR = Path(__file__).resolve().parent.parent
CLEAN = CEDAR / "data" / "clean"
SPINE = CEDAR / "data" / "spine"
REVIEW = CEDAR / "review"
RAW = CEDAR / "data" / "raw" / "external" / "nigc"
TODAY = date.today().isoformat()
FETCHED = "2026-08-06"

# The entity resolver is script 33's. Never a second name matcher.
_spec = importlib.util.spec_from_file_location(
    "cedar33", CEDAR / "code" / "33_apply_party_rulings.py")
_m33 = importlib.util.module_from_spec(_spec)
sys.modules["cedar33"] = _m33
_spec.loader.exec_module(_m33)
resolve_entity, norm = _m33.resolve_entity, _m33.norm

# The ID service. SPEC v2 13.2: "All internal IDs from one shared service -
# never inline in ingestion scripts." This build needs a CONTIGUOUS block
# rather than one id at a time, so it declares one - see ADMREG below.
sys.path.insert(0, str(CEDAR / "code"))
import cedar_ids                                              # noqa: E402

ARCHIVE = "https://www.nigc.gov/downloads/gross-gaming-revenue-reports/"
REGIONS_PAGE = "https://www.nigc.gov/office-of-chief-of-staff/compliance/regions/"
MAP_PAGE = "https://www.nigc.gov/map/"

MEASURE_NOTE = (
    "NIGC gross gaming revenue = gaming win only. EXCLUDES hotel, restaurant, "
    "entertainment and retail revenue, and is measured BEFORE wages, operating "
    "expenses, debt service, tribal-state compact payments and reinvestment. "
    "It is not resort revenue and it is not tribal government income. Published "
    "by NIGC at the region level only; NIGC publishes no property-level revenue "
    "and Cedar Press does not estimate one."
)

# ---------------------------------------------------------------------------
# REGION SYSTEMS - transcribed from the state legend printed on each report,
# and for R4 from NIGC's current Regions page. `legend_as_of` records WHEN the
# legend we hold was published, because a legend read today is not evidence of
# the legend in force in 2017.
# ---------------------------------------------------------------------------
SYSTEMS = [
    {
        "version": "NIGC_R1_FY2001_FY2002", "n_regions": 6,
        "start": 2001, "end": 2002,
        "legend_as_of": "FY2002 report (gamingrevenuesbyregion2002to2001.pdf)",
        "regions": {
            "Region I":       ["AK", "ID", "MT", "OR", "WA"],
            "Region II":      ["CA", "NV-N"],
            "Region III":     ["AZ", "CO", "NM", "NV-S"],
            "Region IV":      ["IA", "MI", "MN", "NE", "ND", "SD", "WI", "WY"],
            "Region V":       ["KS", "OK", "TX"],
            "Eastern Region": ["AL", "CT", "FL", "LA", "MS", "NC", "NY"],
        },
    },
    {
        "version": "NIGC_R2_FY2003_FY2007", "n_regions": 6,
        "start": 2003, "end": 2007,
        "legend_as_of": "FY2005 report (2005vs2004gmgrevbyregn.pdf)",
        "regions": {
            "Region I":   ["AK", "ID", "OR", "WA"],
            "Region II":  ["CA", "NV-N"],
            "Region III": ["AZ", "CO", "NM", "NV-S"],
            "Region IV":  ["IA", "MI", "MN", "MT", "ND", "NE", "SD", "WI", "WY"],
            "Region V":   ["KS", "OK", "TX"],
            "Region VI":  ["AL", "CT", "FL", "LA", "MS", "NC", "NY"],
        },
    },
    {
        "version": "NIGC_R3_FY2008_FY2016", "n_regions": 7,
        "start": 2008, "end": 2016,
        "legend_as_of": "FY2012 report (2012GGRbyRegionforWeb.pdf)",
        "regions": {
            "Portland":      ["AK", "ID", "OR", "WA"],
            "Sacramento":    ["CA", "NV-N"],
            "Phoenix":       ["AZ", "CO", "NM", "NV-S"],
            "St. Paul":      ["IA", "MI", "MN", "MT", "ND", "NE", "SD", "WI", "WY"],
            "Tulsa":         ["KS", "OK-E"],
            "Oklahoma City": ["OK-W", "TX"],
            "Washington DC": ["AL", "CT", "FL", "LA", "MS", "NC", "NY"],
        },
    },
    {
        "version": "NIGC_R4_FY2017_present", "n_regions": 8,
        "start": 2017, "end": "",
        "legend_as_of": "NIGC Regions page retrieved 2026-08-06",
        "regions": {
            "Portland":      ["AK", "ID", "OR", "WA"],
            "Sacramento":    ["CA", "NV-N"],
            "Phoenix":       ["AZ", "CO", "NM", "NV-S"],
            "St. Paul":      ["IN", "IA", "MI", "MN", "NE", "WI"],
            "Tulsa":         ["KS", "OK-E"],
            "Oklahoma City": ["OK-W", "TX"],
            "Washington DC": ["AL", "CT", "FL", "LA", "MS", "NY", "NC", "MA"],
            "Rapid City":    ["MT", "ND", "SD", "WY"],
        },
    },
]

# Stable ids. Cedar Press reserves the 9000xx block for NIGC_REGION so this
# build cannot collide with the shared crosswalk another agent is writing.
#
# 2026-08-26: that reservation used to live ONLY in this comment. The block was
# minted by an f-string, `cedar_ids` knew nothing about it, and
# `cedar_ids.RESERVED_BLOCKS` listed exactly one CEDAR-ADMREG range - not this
# one - so `allocate("CEDAR-ADMREG")` could have walked straight into these
# numbers. It is now DECLARED to the ID service, which refuses an overlapping
# claim from another owner, steps over it in `allocate`, and raises rather than
# spilling past 900099 into somebody else's range.
#
# The id is still POSITIONAL within the block, and that is correct here: it is
# a stable, pre-assigned ordinal over a FIXED constant table (`SYSTEMS`), not a
# position in a file that changes. The key that identifies a region is
# `(region_system_version, region_name)`, which is what this dict is keyed on.
ADMREG = {}
_mint_admreg = cedar_ids.declare_static_block(
    "CEDAR-ADMREG", 900001, 900099,
    owner="84_build_nigc_regions.py",
    why="NIGC region system versions. A contiguous pre-assigned block so the "
        "id of a given NIGC region is the same number on every machine, "
        "independent of what anyone else minted first. Keyed on "
        "(region_system_version, region_name).")
for _s in SYSTEMS:
    for _r in _s["regions"]:
        ADMREG[(_s["version"], _r)] = _mint_admreg()

DOC = {  # short key -> (filename, human title)
    "fy02": ("gamingrevenuesbyregion2002to2001.pdf", "Tribal Gaming Revenues by Region, FY 2002 and 2001"),
    "fy03": ("gamingrevenuesbyregion2003to2002.pdf", "Tribal Gaming Revenues by Region, FY 2003 and 2002"),
    "fy04": ("gamingrevenuesbyregion2004to2003.pdf", "Tribal Gaming Revenues by Region, FY 2004 and 2003"),
    "fy05": ("2005vs2004gmgrevbyregn.pdf", "Tribal Gaming Revenues by Region, FY 2005 and 2004"),
    "fy06": ("gamingrevenuebyregion2006.pdf", "Tribal Gaming Growth, 2006 and 2005"),
    "fy07": ("gamingrevenuebyregion2007.pdf", "Tribal Gaming Revenues by Region, FY 2007 and 2006"),
    "fy08": ("gamingrevenuesbyregion2008to2007.pdf", "Tribal Gaming Revenues by Region, FY 2008 and 2007"),
    "fy09": ("gamingrevenuesbyregion2009to2008.pdf", "Tribal Gaming Revenues by Region, FY 2009 and 2008"),
    "fy10": ("Gaming-Revenues-2010-2009-region.pdf", "Tribal Gaming Revenues by Region, FY 2010 and 2009"),
    "fy12": ("2012GGRbyRegionforWeb.pdf", "Tribal Gaming Revenues by Region, FY 2012 and 2011"),
    "fy14": ("NIGC_GGR_Chart_2014_Gaming_Revenue_Distributed_by_Region.pdf", "2014 Gaming Revenue Distributed by Region"),
    "fy15": ("2015_NIGC_FY15_Gross_Gaming_Revenue_Distribution_Map.pdf", "NIGC FY15 GGR Distribution Map"),
    "fy16": ("2016GamingRevenueDistributedbyRegion.pdf", "NIGC FY16 GGR Distribution Map"),
    "fy17": ("Graphic2017GamingRevenueDistributedbyRegion.pdf", "NIGC FY17 GGR Distribution Map"),
    "fy18": ("2018GGRDistributionMapFINALCharts_3a.pdf", "NIGC FY18 GGR Distribution Map"),
    "fy19": ("2019_GGR_Map.pdf", "NIGC FY19 GGR Distribution Map"),
    "fy20": ("FY20GGRDistriMap.pdf", "NIGC FY20 GGR Distribution Map"),
    "fy21": ("FY21_GGR_Charts_for_press_release_FINAL.pdf", "NIGC FY21 GGR Distribution Map"),
    "fy22": ("GGRFY22_071923_Final.pdf", "NIGC FY 2022 Gross Gaming Revenue Report"),
    "fy23": ("GGR23_Final.pdf", "NIGC FY 2023 Gross Gaming Revenue Report"),
    "fy24": ("GGR24_080425.pdf", "NIGC FY 2024 Gross Gaming Revenue Report"),
    "fy25": ("GGR25_071526.pdf", "NIGC FY 2025 Gross Gaming Revenue Report"),
}

K, B = 1_000, 1_000_000_000

# (system, fiscal_year, doc, precision, vintage, {region: (ggr_usd, ops)})
# vintage: own_year_report        = the report headlined for this fiscal year
#          prior_year_column      = the comparison column of the NEXT report
# precision: exact_dollars | exact_thousands | rounded_0.1B
SERIES = [
    # ---- R1 ------------------------------------------------------------
    ("NIGC_R1_FY2001_FY2002", 2001, "fy02", "exact_thousands", "prior_year_column", {
        "Region I": (1_013_470 * K, 75), "Region II": (2_891_522 * K, 48),
        "Region III": (1_633_957 * K, 34), "Region IV": (3_254_151 * K, 79),
        "Region V": (437_397 * K, 72), "Eastern Region": (3_591_206 * K, 21)}),
    ("NIGC_R1_FY2001_FY2002", 2002, "fy02", "exact_thousands", "own_year_report", {
        "Region I": (1_196_178 * K, 72), "Region II": (3_594_401 * K, 52),
        "Region III": (1_782_310 * K, 38), "Region IV": (3_523_690 * K, 75),
        "Region V": (580_524 * K, 71), "Eastern Region": (3_819_897 * K, 22)}),
    # ---- R2 ------------------------------------------------------------
    ("NIGC_R2_FY2003_FY2007", 2002, "fy03", "exact_thousands", "prior_year_column", {
        "Region I": (1_230_194 * K, 47), "Region II": (3_678_095 * K, 51),
        "Region III": (1_782_874 * K, 40), "Region IV": (3_537_227 * K, 109),
        "Region V": (651_841 * K, 79), "Region VI": (3_835_825 * K, 22)}),
    ("NIGC_R2_FY2003_FY2007", 2003, "fy03", "exact_thousands", "own_year_report", {
        "Region I": (1_439_516 * K, 43), "Region II": (4_699_889 * K, 54),
        "Region III": (1_898_522 * K, 43), "Region IV": (3_547_360 * K, 91),
        "Region V": (822_727 * K, 75), "Region VI": (4_322_134 * K, 24)}),
    ("NIGC_R2_FY2003_FY2007", 2004, "fy04", "exact_thousands", "own_year_report", {
        "Region I": (1_601_346 * K, 44), "Region II": (5_788_332 * K, 52),
        "Region III": (2_133_116 * K, 43), "Region IV": (3_815_763 * K, 117),
        "Region V": (1_248_089 * K, 84), "Region VI": (4_820_864 * K, 27)}),
    ("NIGC_R2_FY2003_FY2007", 2005, "fy05", "exact_thousands", "own_year_report", {
        "Region I": (1_829_195 * K, 47), "Region II": (7_042_686 * K, 57),
        "Region III": (2_529_128 * K, 48), "Region IV": (3_984_449 * K, 118),
        "Region V": (1_729_981 * K, 93), "Region VI": (5_514_136 * K, 28)}),
    ("NIGC_R2_FY2003_FY2007", 2006, "fy06", "exact_thousands", "own_year_report", {
        "Region I": (2_080_337 * K, 45), "Region II": (7_675_432 * K, 56),
        "Region III": (2_927_711 * K, 45), "Region IV": (4_050_080 * K, 117),
        "Region V": (2_123_169 * K, 97), "Region VI": (6_219_100 * K, 27)}),
    ("NIGC_R2_FY2003_FY2007", 2007, "fy07", "exact_thousands", "own_year_report", {
        "Region I": (2_208_190 * K, 43), "Region II": (7_796_488 * K, 58),
        "Region III": (2_840_585 * K, 44), "Region IV": (4_217_960 * K, 109),
        "Region V": (2_553_034 * K, 100), "Region VI": (6_399_841 * K, 28)}),
    # ---- R3 ------------------------------------------------------------
    ("NIGC_R3_FY2008_FY2016", 2007, "fy08", "exact_thousands", "prior_year_column", {
        "Portland": (2_263_950 * K, 46), "Sacramento": (7_796_488 * K, 58),
        "Phoenix": (2_874_052 * K, 46), "St. Paul": (4_224_866 * K, 111),
        "Tulsa": (1_438_228 * K, 57), "Oklahoma City": (1_146_047 * K, 45),
        "Washington DC": (6_399_841 * K, 28)}),
    ("NIGC_R3_FY2008_FY2016", 2008, "fy08", "exact_thousands", "own_year_report", {
        "Portland": (2_376_025 * K, 47), "Sacramento": (7_363_493 * K, 59),
        "Phoenix": (2_773_715 * K, 46), "St. Paul": (4_402_311 * K, 115),
        "Tulsa": (1_699_940 * K, 62), "Oklahoma City": (1_347_242 * K, 48),
        "Washington DC": (6_776_100 * K, 28)}),
    ("NIGC_R3_FY2008_FY2016", 2009, "fy09", "exact_thousands", "own_year_report", {
        "Portland": (2_520_908 * K, 49), "Sacramento": (6_969_881 * K, 62),
        "Phoenix": (2_599_885 * K, 47), "St. Paul": (4_384_444 * K, 120),
        "Tulsa": (1_715_393 * K, 64), "Oklahoma City": (1_509_200 * K, 49),
        "Washington DC": (6_782_735 * K, 28)}),
    ("NIGC_R3_FY2008_FY2016", 2010, "fy10", "exact_thousands", "own_year_report", {
        "Portland": (2_655_096 * K, 50), "Sacramento": (6_794_012 * K, 62),
        "Phoenix": (2_538_617 * K, 48), "St. Paul": (4_451_539 * K, 119),
        "Tulsa": (1_769_493 * K, 65), "Oklahoma City": (1_582_635 * K, 51),
        "Washington DC": (6_711_142 * K, 27)}),
    ("NIGC_R3_FY2008_FY2016", 2011, "fy12", "exact_thousands", "prior_year_column", {
        "Portland": (2_763_647 * K, 49), "Sacramento": (6_902_843 * K, 63),
        "Phoenix": (2_614_362 * K, 48), "St. Paul": (4_565_004 * K, 119),
        "Tulsa": (1_889_706 * K, 64), "Oklahoma City": (1_702_409 * K, 51),
        "Washington DC": (6_715_837 * K, 27)}),
    ("NIGC_R3_FY2008_FY2016", 2012, "fy12", "exact_thousands", "own_year_report", {
        "Portland": (2_873_925 * K, 49), "Sacramento": (6_956_562 * K, 64),
        "Phoenix": (2_716_525 * K, 48), "St. Paul": (4_797_631 * K, 120),
        "Tulsa": (2_014_997 * K, 64), "Oklahoma City": (1_800_972 * K, 53),
        "Washington DC": (6_739_392 * K, 27)}),
    ("NIGC_R3_FY2008_FY2016", 2013, "fy14", "rounded_0.1B", "prior_year_column", {
        "Portland": (2.9 * B, 51), "Sacramento": (7.0 * B, 66),
        "Phoenix": (2.7 * B, 48), "St. Paul": (4.7 * B, 128),
        "Tulsa": (2.0 * B, 68), "Oklahoma City": (1.9 * B, 60),
        "Washington DC": (6.8 * B, 28)}),
    ("NIGC_R3_FY2008_FY2016", 2014, "fy14", "rounded_0.1B", "own_year_report", {
        "Portland": (2.9 * B, 51), "Sacramento": (7.3 * B, 68),
        "Phoenix": (2.7 * B, 48), "St. Paul": (4.7 * B, 130),
        "Tulsa": (2.1 * B, 67), "Oklahoma City": (2.0 * B, 65),
        "Washington DC": (6.8 * B, 30)}),
    ("NIGC_R3_FY2008_FY2016", 2015, "fy15", "rounded_0.1B", "own_year_report", {
        "Portland": (3.0 * B, 52), "Sacramento": (7.9 * B, 71),
        "Phoenix": (2.8 * B, 53), "St. Paul": (4.8 * B, 134),
        "Tulsa": (2.2 * B, 68), "Oklahoma City": (2.1 * B, 65),
        "Washington DC": (7.0 * B, 31)}),
    ("NIGC_R3_FY2008_FY2016", 2016, "fy16", "rounded_0.1B", "own_year_report", {
        "Portland": (3.2 * B, 53), "Sacramento": (8.4 * B, 70),
        "Phoenix": (2.9 * B, 57), "St. Paul": (4.9 * B, 132),
        "Tulsa": (2.3 * B, 69), "Oklahoma City": (2.3 * B, 66),
        "Washington DC": (7.3 * B, 37)}),
    # ---- R4 ------------------------------------------------------------
    ("NIGC_R4_FY2017_present", 2016, "fy17", "rounded_0.1B", "prior_year_column", {
        "Portland": (3.2 * B, 53), "Sacramento": (8.4 * B, 70),
        "Phoenix": (2.9 * B, 57), "St. Paul": (4.5 * B, 93),
        "Rapid City": (0.4 * B, 39), "Tulsa": (2.3 * B, 69),
        "Oklahoma City": (2.3 * B, 66), "Washington DC": (7.3 * B, 37)}),
    ("NIGC_R4_FY2017_present", 2017, "fy17", "rounded_0.1B", "own_year_report", {
        "Portland": (3.4 * B, 52), "Sacramento": (9.0 * B, 74),
        "Phoenix": (3.0 * B, 59), "St. Paul": (4.6 * B, 92),
        "Rapid City": (0.4 * B, 39), "Tulsa": (2.4 * B, 72),
        "Oklahoma City": (2.3 * B, 69), "Washington DC": (7.3 * B, 37)}),
    ("NIGC_R4_FY2017_present", 2018, "fy18", "rounded_0.1B", "own_year_report", {
        "Portland": (3.7 * B, 55), "Sacramento": (9.3 * B, 73),
        "Phoenix": (3.1 * B, 59), "St. Paul": (4.8 * B, 95),
        "Rapid City": (0.4 * B, 36), "Tulsa": (2.5 * B, 73),
        "Oklahoma City": (2.5 * B, 72), "Washington DC": (7.5 * B, 38)}),
    ("NIGC_R4_FY2017_present", 2019, "fy19", "rounded_0.1B", "own_year_report", {
        "Portland": (3.8 * B, 57), "Sacramento": (9.7 * B, 76),
        "Phoenix": (3.3 * B, 57), "St. Paul": (4.9 * B, 100),
        "Rapid City": (0.4 * B, 42), "Tulsa": (2.5 * B, 75),
        "Oklahoma City": (2.7 * B, 73), "Washington DC": (7.4 * B, 42)}),
    ("NIGC_R4_FY2017_present", 2020, "fy20", "rounded_0.1B", "own_year_report", {
        "Portland": (3.1 * B, 57), "Sacramento": (8.4 * B, 77),
        "Phoenix": (2.4 * B, 52), "St. Paul": (3.7 * B, 103),
        "Rapid City": (0.2 * B, 42), "Tulsa": (2.1 * B, 76),
        "Oklahoma City": (2.1 * B, 74), "Washington DC": (5.8 * B, 43)}),
    ("NIGC_R4_FY2017_present", 2021, "fy22", "exact_dollars", "prior_year_column", {
        "Portland": (4_440_688_687, 56), "Sacramento": (11_926_737_084, 78),
        "Phoenix": (3_217_759_740, 50), "St. Paul": (4_787_386_386, 99),
        "Rapid City": (372_306_820, 41), "Tulsa": (3_155_036_484, 74),
        "Oklahoma City": (3_027_386_184, 70), "Washington DC": (8_098_283_597, 42)}),
    ("NIGC_R4_FY2017_present", 2022, "fy22", "exact_dollars", "own_year_report", {
        "Portland": (4_483_512_096, 55), "Sacramento": (11_759_106_562, 87),
        "Phoenix": (3_722_950_358, 51), "St. Paul": (4_950_589_631, 96),
        "Rapid City": (406_169_922, 43), "Tulsa": (3_489_234_645, 74),
        "Oklahoma City": (3_149_318_979, 72), "Washington DC": (8_976_860_441, 41)}),
    ("NIGC_R4_FY2017_present", 2023, "fy23", "exact_dollars", "own_year_report", {
        "Portland": (4_531_931_711, 53), "Sacramento": (11_965_357_091, 87),
        "Phoenix": (3_926_245_150, 54), "St. Paul": (5_087_839_643, 95),
        "Rapid City": (425_875_203, 45), "Tulsa": (3_560_275_433, 74),
        "Oklahoma City": (3_216_288_977, 75), "Washington DC": (9_191_534_330, 44)}),
    ("NIGC_R4_FY2017_present", 2024, "fy24", "exact_dollars", "own_year_report", {
        "Portland": (4_694_100_529, 55), "Sacramento": (12_135_475_969, 87),
        "Phoenix": (3_999_888_645, 53), "St. Paul": (5_171_624_189, 97),
        "Rapid City": (443_861_592, 44), "Tulsa": (3_564_148_943, 73),
        "Oklahoma City": (3_624_523_166, 78), "Washington DC": (10_218_407_815, 45)}),
    ("NIGC_R4_FY2017_present", 2025, "fy25", "exact_dollars", "own_year_report", {
        "Portland": (4_943_983_904, 58), "Sacramento": (12_631_303_247, 88),
        "Phoenix": (4_211_135_056, 54), "St. Paul": (5_320_261_193, 101),
        "Rapid City": (439_790_197, 44), "Tulsa": (3_653_169_798, 74),
        "Oklahoma City": (3_744_841_561, 80), "Washington DC": (11_218_298_614, 46)}),
]

# NIGC's own printed national totals, used as an arithmetic check on every year.
PRINTED_TOTALS = {
    ("NIGC_R1_FY2001_FY2002", 2001): (12_821_703 * K, 329),
    ("NIGC_R1_FY2001_FY2002", 2002): (14_497_000 * K, 330),
    ("NIGC_R2_FY2003_FY2007", 2002): (14_716_056 * K, 348),
    ("NIGC_R2_FY2003_FY2007", 2003): (16_730_148 * K, 330),
    ("NIGC_R2_FY2003_FY2007", 2004): (19_407_510 * K, 367),
    ("NIGC_R2_FY2003_FY2007", 2005): (22_629_575 * K, 391),
    ("NIGC_R2_FY2003_FY2007", 2006): (25_075_829 * K, 387),
    ("NIGC_R2_FY2003_FY2007", 2007): (26_016_098 * K, 382),
    ("NIGC_R3_FY2008_FY2016", 2007): (26_143_472 * K, 391),
    ("NIGC_R3_FY2008_FY2016", 2008): (26_738_826 * K, 405),
    ("NIGC_R3_FY2008_FY2016", 2009): (26_482_447 * K, 419),
    ("NIGC_R3_FY2008_FY2016", 2010): (26_502_533 * K, 422),
    ("NIGC_R3_FY2008_FY2016", 2011): (27_153_807 * K, 421),
    ("NIGC_R3_FY2008_FY2016", 2012): (27_900_004 * K, 425),
    ("NIGC_R3_FY2008_FY2016", 2014): (28.5 * B, 459),
    ("NIGC_R3_FY2008_FY2016", 2015): (29.9 * B, 474),
    ("NIGC_R3_FY2008_FY2016", 2016): (31.2 * B, 484),
    ("NIGC_R4_FY2017_present", 2017): (32.4 * B, 494),
    ("NIGC_R4_FY2017_present", 2018): (33.7 * B, 501),
    ("NIGC_R4_FY2017_present", 2019): (34.6 * B, 522),
    ("NIGC_R4_FY2017_present", 2020): (27.8 * B, 524),
    ("NIGC_R4_FY2017_present", 2021): (39_025_584_982, 510),
    ("NIGC_R4_FY2017_present", 2022): (40_937_742_634, 519),
    ("NIGC_R4_FY2017_present", 2023): (41_905_347_538, 527),
    ("NIGC_R4_FY2017_present", 2024): (43_852_030_848, 532),
    ("NIGC_R4_FY2017_present", 2025): (46_162_783_570, 545),
}

# NIGC map category id -> region name, from the map page's own category legend.
MAP_CAT = {1: "St. Paul", 2: "Sacramento", 3: "Portland", 4: "Phoenix",
           5: "Oklahoma City", 6: "Tulsa", 8: "Washington DC", 9: "Rapid City"}

# Names that assert NO gaming. A property whose name carries a gaming word
# ("casino", "gaming", "bingo", "gaming parlor") is NOT ruled out by this list -
# a Choctaw Travel Plaza with machines in it is an IGRA operation and the blunt
# keyword sweep that would have dropped it is the error this guard exists to
# prevent.
NONGAMING_NAME = re.compile(
    r"smoke shop|tobacco|golf|liquor|convenience store|c-store|fuel mart|"
    r"grill room|travel (plaza|center|mart)|truck stop|grocer|marina|rv park",
    re.I)
GAMING_WORD = re.compile(r"casino|gaming|bingo|slot|parlor", re.I)
# "Las Vegas Paiute Smoke Shop - no casino" contains the word casino in order to
# DENY one. A gaming-word test that reads it as a casino is worse than no test.
NEGATED = re.compile(r"\bno casino\b|\bnon[- ]?gaming\b|\bno gaming\b", re.I)
GAMING_CAP = ("gaming_machines", "table_games", "poker_tables", "bingo_seats")


def rd(p):
    p = Path(p)
    if not p.exists():
        return []
    with open(p, encoding="utf-8-sig", errors="replace", newline="") as fh:
        return list(csv.DictReader(fh))


def wr(p, rows, fields):
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    print(f"  wrote {p.relative_to(CEDAR)}  ({len(rows):,} rows)")


def deflator():
    return {int(r["year"]): float(r["factor_to_base"])
            for r in rd(CLEAN / "inflation_deflator.csv")}


def haversine(a, b, c, d):
    R = 6371.0088
    p1, p2 = math.radians(a), math.radians(c)
    dp, dl = p2 - p1, math.radians(d - b)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(min(1.0, math.sqrt(h)))


ZIP_ST = re.compile(r"\b([A-Z]{2})\b[ ,]*\d{4,5}(?:-\d{3,4})?\s*$")
CITY_ST = re.compile(r",\s*[A-Za-z .'-]+\s+([A-Z]{2})\b")


def marker_state(addr):
    a = (addr or "").strip()
    m = ZIP_ST.search(a) or CITY_ST.search(a)
    return m.group(1) if m else ""


# ===========================================================================
def build_ggr():
    """The regional GGR series. One row per (region_system_version, region, FY)."""
    defl = deflator()
    rows, arith = [], []
    by_key = {}
    for ver, fy, dk, prec, vint, regs in SERIES:
        for rname, (ggr, ops) in regs.items():
            by_key[(ver, rname, fy)] = (ggr, ops, prec, vint, dk)

    for ver, fy, dk, prec, vint, regs in SERIES:
        fn, title = DOC[dk]
        # arithmetic check against NIGC's own printed total
        pt = PRINTED_TOTALS.get((ver, fy))
        if pt:
            s_ggr = sum(v[0] for v in regs.values())
            s_ops = sum(v[1] for v in regs.values())
            # Rounded inputs cannot sum exactly. NIGC prints each region to
            # $0.1B, so n regions carry up to n x $0.05B of rounding, and the
            # printed total is itself rounded. Demanding equality there would
            # manufacture four false alarms; demanding it of the exact-dollar
            # years is the check that actually bites.
            tol = (0.05 * B * len(regs) + 0.05 * B) if prec == "rounded_0.1B" \
                else max(2000.0, pt[0] * 1e-9)
            arith.append({
                "region_system_version": ver, "fiscal_year": fy,
                "source_document": fn, "figure_precision": prec,
                "summed_ggr_usd": round(s_ggr, 2), "printed_ggr_usd": round(pt[0], 2),
                "tolerance_usd": round(tol, 2),
                "ggr_agrees": int(abs(s_ggr - pt[0]) <= tol),
                "summed_operations": s_ops, "printed_operations": pt[1],
                "operations_agree": int(s_ops == pt[1]),
            })
        for rname, (ggr, ops) in sorted(regs.items()):
            prev = by_key.get((ver, rname, fy - 1))
            pct = ""
            basis = "no_prior_year_in_this_region_system"
            if prev and prev[0]:
                pct = round((ggr - prev[0]) / prev[0] * 100, 2)
                basis = ("computed_from_cedar_series_exact" if prec.startswith("exact")
                         and prev[2].startswith("exact")
                         else "computed_from_cedar_series_rounded_inputs")
            # the ONLY regional average we publish, and it is not a property figure
            mean = round(ggr / ops, 2) if ops else ""
            f = defl.get(fy, "")
            rows.append({
                "administrative_region_id": ADMREG[(ver, rname)],
                "region_system_code": "NIGC_REGION",
                "region_name": rname,
                "region_system_version": ver,
                "fiscal_year": fy,
                "ggr_usd": round(ggr, 2),
                "ggr_usd_real2025": round(ggr * f, 2) if f else "",
                "operation_count": ops,
                "ggr_change_pct": pct,
                "ggr_change_pct_basis": basis,
                "region_mean_ggr_per_operation_usd": mean,
                "region_mean_is_descriptive_only": 1,
                "revenue_measure": "nigc_gross_gaming_revenue",
                "geographic_level": "nigc_region",
                "allocation_level": "aggregate_only",
                "includes_nongaming_revenue": "false",
                "measure_note": MEASURE_NOTE,
                "figure_precision": prec,
                "figure_vintage": vint,
                "deflator_factor_2025": f,
                "inflation_base_year": 2025,
                "region_states_in_force": "|".join(
                    next(s["regions"][rname] for s in SYSTEMS if s["version"] == ver)),
                "source_url": ARCHIVE,
                "source_document": fn,
                "source_document_title": title,
                "fetched_date": FETCHED,
                "built_date": TODAY,
            })
    rows.sort(key=lambda r: (r["region_system_version"], r["fiscal_year"], r["region_name"]))
    return rows, arith


# ===========================================================================
def load_markers():
    p = RAW / "locations" / "nigc_gaming_locations_map6_2026-08-06.json"
    out = []
    for m in json.load(open(p, encoding="utf-8")):
        cat = int(m["category"]) if str(m.get("category", "")).isdigit() else 0
        try:
            lat, lng = float(m["lat"]), float(m["lng"])
        except (TypeError, ValueError):
            lat = lng = None
        out.append({
            "nigc_marker_id": m.get("id", ""),
            "nigc_location_name": (m.get("title") or "").strip(),
            "nigc_address": (m.get("address") or "").strip(),
            "state": marker_state(m.get("address")),
            "region_name": MAP_CAT.get(cat, ""),
            "lat": lat, "lng": lng,
        })
    return out


def match_roster(fac, markers):
    """Deterministic geographic + exact-name matching. Never fuzzy.

    Three bases, tried in order, each of which a reader can re-derive:
      coords_1200m   - same state, centres within 1.2 km
      name_state     - identical normalised name in the same state
      name_near_25km - identical normalised name, same state, within 25 km
                       (kept separate so a coincidental name tie in a big state
                        is visible rather than buried)
    """
    used_m, pairs = set(), []
    fn = {}
    for r in fac:
        fn.setdefault((norm(r["facility_name"]), r["state"]), []).append(r)

    # pass 1: coordinates, ONE-TO-ONE. Nearest-first greedy rather than
    # nearest-per-marker, because two NIGC locations 400 m apart would
    # otherwise both claim the same Cedar property and the match count would
    # exceed the number of properties matched - which is how a roster diff
    # quietly overstates its own coverage.
    cand = []
    for i, m in enumerate(markers):
        if m["lat"] is None:
            continue
        for j, r in enumerate(fac):
            if r["state"] != m["state"] or not r["latitude"] or not r["longitude"]:
                continue
            try:
                d = haversine(m["lat"], m["lng"], float(r["latitude"]), float(r["longitude"]))
            except ValueError:
                continue
            if d < 1.2:
                cand.append((d, i, j))
    cand.sort()
    matched_f = set()
    for d, i, j in cand:
        if i in used_m or j in matched_f:
            continue
        pairs.append((fac[j], markers[i], "coords_1200m", round(d * 1000)))
        used_m.add(i)
        matched_f.add(j)
    # lint-ok: class7 - `id()` here is PYTHON OBJECT IDENTITY for an in-memory object,
    # used as a key in a dict/set that lives and dies inside this one function. It is
    # never written to a file, nothing joins on it, and it is not a primary key.
    # 293_lint_bug_classes.py waives the same shape in its own source. Triaged LOW by
    # 326_triage_class7_key_risk.py on 2026-08-26: no clean or spine table carries it.
    matched_f = {id(p[0]) for p in pairs}

    # pass 2 / 3: exact normalised name in the same state
    for i, m in enumerate(markers):
        if i in used_m:
            continue
        cands = [r for r in fn.get((norm(m["nigc_location_name"]), m["state"]), [])
                 # lint-ok: class7 - `id()` here is PYTHON OBJECT IDENTITY for an in-memory object,
                 # used as a key in a dict/set that lives and dies inside this one function. It is
                 # never written to a file, nothing joins on it, and it is not a primary key.
                 # 293_lint_bug_classes.py waives the same shape in its own source. Triaged LOW by
                 # 326_triage_class7_key_risk.py on 2026-08-26: no clean or spine table carries it.
                 if id(r) not in matched_f]
        if len(cands) != 1:
            continue
        r = cands[0]
        d = ""
        basis = "name_state"
        if m["lat"] is not None and r["latitude"] and r["longitude"]:
            try:
                km = haversine(m["lat"], m["lng"], float(r["latitude"]), float(r["longitude"]))
                d = round(km * 1000)
                basis = "name_state" if km <= 25 else "name_state_far"
            except ValueError:
                pass
        pairs.append((r, m, basis, d))
        used_m.add(i)
        # lint-ok: class7 - `id()` here is PYTHON OBJECT IDENTITY for an in-memory object,
        # used as a key in a dict/set that lives and dies inside this one function. It is
        # never written to a file, nothing joins on it, and it is not a primary key.
        # 293_lint_bug_classes.py waives the same shape in its own source. Triaged LOW by
        # 326_triage_class7_key_risk.py on 2026-08-26: no clean or spine table carries it.
        matched_f.add(id(r))
    return pairs, used_m


def gaming_signal(r):
    """Does this row show any evidence of gaming? Name AND capacity."""
    name = r.get("facility_name") or ""
    gw = bool(GAMING_WORD.search(name)) and not NEGATED.search(name)
    cap = any((r.get(c) or "").strip() not in ("", "0") for c in GAMING_CAP)
    return gw, cap


def coverage_status(r, is_marker_matched, gaming_words, cap_any):
    """Order matters. The non-gaming test runs BEFORE the closed test, because a
    smoke shop that carries a close date is not a closed IGRA operation - it was
    never an IGRA operation, and calling it one puts a non-casino into the
    gaming universe by the back door."""
    if is_marker_matched:
        return "VERIFIED_NIGC_OPERATION"
    nong = NONGAMING_NAME.search(r.get("facility_name") or "") or \
        NEGATED.search(r.get("facility_name") or "")
    if nong and not gaming_words and not cap_any:
        return "NON_IGRA_TRIBALLY_OWNED"
    if (r.get("property_status") or "").lower() == "approved":
        return "PROPOSED_IGRA_OPERATION"
    if r.get("close_date"):
        return "CLOSED_IGRA_OPERATION"
    if cap_any or gaming_words:
        return "LIKELY_IGRA_OPERATION"
    return "UNKNOWN"


# ===========================================================================
def main():
    print("=== Cedar Press 84: NIGC administrative region layer ===\n")

    # ---- 1. regional GGR --------------------------------------------------
    ggr, arith = build_ggr()
    wr(CLEAN / "nigc_regional_ggr.csv", ggr, list(ggr[0].keys()))
    yrs = sorted({r["fiscal_year"] for r in ggr})
    print(f"   fiscal years {yrs[0]}-{yrs[-1]}  ({len(yrs)} years)")
    for s in SYSTEMS:
        n = sum(1 for r in ggr if r["region_system_version"] == s["version"])
        fys = sorted({r["fiscal_year"] for r in ggr if r["region_system_version"] == s["version"]})
        print(f"   {s['version']:24} {s['n_regions']} regions  "
              f"FY{fys[0]}-{fys[-1]}  {n} region-years")
    bad = [a for a in arith if not (a["ggr_agrees"] and a["operations_agree"])]
    print(f"   arithmetic vs NIGC printed totals: {len(arith)-len(bad)}/{len(arith)} agree")
    for a in bad:
        print(f"     MISMATCH {a['region_system_version']} FY{a['fiscal_year']} "
              f"ggr={a['ggr_agrees']} ops={a['operations_agree']} ({a['source_document']})")

    # ---- 2. roster diff ---------------------------------------------------
    fac = rd(CLEAN / "gaming_facilities.csv")
    spine = rd(SPINE / "cedar_entity_spine.csv")
    markers = load_markers()
    print(f"\nfacilities {len(fac):,}   NIGC map locations {len(markers):,}")

    pairs, used_m = match_roster(fac, markers)
    m_by_fid = {p[0]["facility_id"]: p[1] for p in pairs}
    basis_by_fid = {p[0]["facility_id"]: (p[2], p[3]) for p in pairs}
    print(f"  matched {len(pairs)}  "
          f"({Counter(p[2] for p in pairs).most_common()})")

    # corroborating federal sources per tribe
    compacts, land, fr = defaultdict(int), defaultdict(int), defaultdict(int)
    for r in rd(CLEAN / "compacts.csv"):
        t = (r.get("tribe_id") or r.get("entity_id") or "").strip()
        if t:
            compacts[t] += 1
    for r in rd(CLEAN / "gaming_land_decisions.csv"):
        t = (r.get("tribe_id") or r.get("entity_id") or "").strip()
        if t:
            land[t] += 1
    for r in rd(CLEAN / "gaming_project_facilities.csv"):
        t = (r.get("tribe_id") or r.get("entity_id") or "").strip()
        if t:
            fr[t] += 1

    diff, corro = [], Counter()
    for r in fac:
        fid = r["facility_id"]
        m = m_by_fid.get(fid)
        tid = (r.get("tribe_id") or r.get("entity_id") or "").strip()
        srcs = []
        if m:
            srcs.append("NIGC_GAMING_LOCATION_MAP")
        if compacts.get(tid):
            srcs.append("TRIBAL_STATE_COMPACT")
        if land.get(tid):
            srcs.append("BIA_GAMING_LAND_DECISION")
        if fr.get(tid):
            srcs.append("FEDERAL_REGISTER_GAMING_PROJECT")
        corro[len(srcs)] += 1
        gw, cap = gaming_signal(r)
        st = coverage_status(r, bool(m), gw, cap)
        b = basis_by_fid.get(fid, ("", ""))
        diff.append({
            "outcome": "MATCHED" if m else "IN_CEDAR_NOT_IN_NIGC",
            "facility_id": fid, "facility_name": r["facility_name"],
            "city": r["city"], "state": r["state"],
            "tribe_id": tid, "tribe_canonical_name": r.get("tribe_canonical_name", ""),
            "nigc_marker_id": m["nigc_marker_id"] if m else "",
            "nigc_location_name": m["nigc_location_name"] if m else "",
            "nigc_address": m["nigc_address"] if m else "",
            "nigc_region_name": m["region_name"] if m else "",
            "match_basis": b[0], "match_distance_m": b[1],
            "igra_coverage_status": st,
            "corroborating_sources": "|".join(srcs),
            "n_corroborating_sources": len(srcs),
            "property_status": r.get("property_status", ""),
            "close_date": r.get("close_date", ""),
            "investigate_reason": "" if m else (
                "closed_row" if r.get("close_date") else
                "non_igra_candidate" if st == "NON_IGRA_TRIBALLY_OWNED" else
                "proposed_not_yet_operating" if st == "PROPOSED_IGRA_OPERATION" else
                "absent_from_NIGC_map__may_be_consolidated_audit_name_variant_"
                "or_non_IGRA_commercial_property"),
            "source_url": MAP_PAGE, "fetched_date": FETCHED, "built_date": TODAY,
        })

    for i, m in enumerate(markers):
        if i in used_m:
            continue
        tid, canon, how = resolve_entity(m["nigc_location_name"], spine)
        diff.append({
            "outcome": "IN_NIGC_NOT_IN_CEDAR",
            "facility_id": "", "facility_name": "",
            "city": "", "state": m["state"],
            "tribe_id": tid or "", "tribe_canonical_name": canon or "",
            "nigc_marker_id": m["nigc_marker_id"],
            "nigc_location_name": m["nigc_location_name"],
            "nigc_address": m["nigc_address"],
            "nigc_region_name": m["region_name"],
            "match_basis": "", "match_distance_m": "",
            "igra_coverage_status": "VERIFIED_NIGC_OPERATION",
            "corroborating_sources": "NIGC_GAMING_LOCATION_MAP",
            "n_corroborating_sources": 1,
            "property_status": "", "close_date": "",
            "investigate_reason": (
                f"STAGE FOR ADDITION. entity_resolution={how}"
                if not tid else "STAGE FOR ADDITION. entity resolved via "
                                f"resolve_entity({how})"),
            "source_url": MAP_PAGE, "fetched_date": FETCHED, "built_date": TODAY,
        })

    wr(REVIEW / f"nigc_roster_diff_{TODAY}.csv", diff, list(diff[0].keys()))
    oc = Counter(d["outcome"] for d in diff)
    for k, v in oc.most_common():
        print(f"   {v:5,}  {k}")
    print("   igra_coverage_status:",
          dict(Counter(d["igra_coverage_status"] for d in diff).most_common()))
    print("   corroborating federal sources per Cedar property:",
          dict(sorted(corro.items())))

    # ---- 3. region assignments -------------------------------------------
    assigns, conflicts = [], []
    st_map = {}   # (version, plain_state) -> region  (unambiguous states only)
    split_states = {}
    for s in SYSTEMS:
        amb = defaultdict(list)
        for rname, sts in s["regions"].items():
            for x in sts:
                amb[x.split("-")[0]].append((x, rname))
        for base, lst in amb.items():
            if len(lst) == 1 and "-" not in lst[0][0]:
                st_map[(s["version"], base)] = lst[0][1]
            else:
                split_states[(s["version"], base)] = dict(
                    (x, rn) for x, rn in lst)

    for r in fac:
        fid, stt = r["facility_id"], r["state"]
        m = m_by_fid.get(fid)
        gw, cap = gaming_signal(r)
        cov = coverage_status(r, bool(m), gw, cap)
        oy = (r.get("open_date") or "")[:4]
        cy = (r.get("close_date") or "")[:4]
        oy = int(oy) if oy.isdigit() else None
        cy = int(cy) if cy.isdigit() else None
        for s in SYSTEMS:
            v, v0 = s["version"], s["start"]
            v1 = s["end"] if s["end"] != "" else 2026
            if oy and oy > v1:
                continue          # not yet open when this system ended
            if cy and cy < v0:
                continue          # demonstrably closed before this system began
            region, method, conf = "", "", ""
            if (v, stt) in st_map:
                region = st_map[(v, stt)]
                method = "nigc_published_state_to_region_legend"
                conf = "high"
            elif (v, stt) in split_states:
                # OK and NV are split WITHIN the state. State alone cannot
                # decide, so the only sourced answer is NIGC's own published
                # location for THIS property. No line is drawn by us.
                if m and m["region_name"] in split_states[(v, stt)].values():
                    region = m["region_name"]
                    method = "nigc_published_gaming_location_map"
                    conf = "high" if v == "NIGC_R4_FY2017_present" else "medium"
                else:
                    method = "unassigned_substate_split_not_sourced"
                    conf = "none"
            else:
                method = "state_absent_from_published_legend_for_this_system"
                conf = "none"
            if m and region and m["region_name"] and m["region_name"] != region \
                    and v == "NIGC_R4_FY2017_present":
                conflicts.append({
                    "facility_id": fid, "facility_name": r["facility_name"],
                    "state": stt, "region_system_version": v,
                    "region_from_state_legend": region,
                    "region_from_nigc_map": m["region_name"],
                    "nigc_marker_id": m["nigc_marker_id"],
                    "nigc_address": m["nigc_address"],
                    "resolution": "BOTH RECORDED, NEITHER DISCARDED. NIGC map "
                                  "is property-specific and outranks the "
                                  "state-level legend; the legend row is kept "
                                  "so the disagreement stays visible.",
                    "source_url_legend": REGIONS_PAGE, "source_url_map": MAP_PAGE,
                    "built_date": TODAY,
                })
                region, method, conf = (m["region_name"],
                                        "nigc_published_gaming_location_map",
                                        "high")
            assigns.append({
                "facility_id": fid,
                "administrative_region_id": ADMREG.get((v, region), "") if region else "",
                "region_system_code": "NIGC_REGION",
                "region_name": region,
                "region_system_version": v,
                "effective_start_year": max(v0, oy) if oy else v0,
                "effective_end_year": min(v1, cy) if cy else (s["end"] if s["end"] != "" else ""),
                "assignment_method": method,
                "assignment_geography_basis": "property_location_not_tribal_headquarters",
                "igra_coverage_status": cov,
                "nigc_operation_match_status": (
                    "MATCHED_NIGC_GAMING_LOCATION" if m else "NOT_ON_NIGC_GAMING_LOCATION_MAP"),
                "is_primary": int(v == "NIGC_R4_FY2017_present"),
                "confidence": conf,
                "facility_state": stt,
                "facility_city": r.get("city", ""),
                "tribe_id": (r.get("tribe_id") or "").strip(),
                "nigc_marker_id": m["nigc_marker_id"] if m else "",
                "source_url": MAP_PAGE if method.startswith("nigc_published_gaming")
                              else (REGIONS_PAGE if v == "NIGC_R4_FY2017_present" else ARCHIVE),
                "fetched_date": FETCHED,
                "built_date": TODAY,
            })

    wr(CLEAN / "nigc_region_assignments.csv", assigns, list(assigns[0].keys()))
    print("   assignment_method:",
          dict(Counter(a["assignment_method"] for a in assigns).most_common()))
    print(f"   distinct properties with >=1 sourced region: "
          f"{len({a['facility_id'] for a in assigns if a['region_name']}):,}")
    if conflicts:
        wr(REVIEW / f"nigc_region_conflicts_{TODAY}.csv", conflicts,
           list(conflicts[0].keys()))

    # ---- 4. coverage benchmark -------------------------------------------
    gap = []
    ggr_by = {(r["region_system_version"], r["region_name"], r["fiscal_year"]): r
              for r in ggr}
    for (v, rn, fy), g in sorted(ggr_by.items()):
        ours = 0
        for a in assigns:
            if a["region_system_version"] != v or a["region_name"] != rn:
                continue
            s0 = a["effective_start_year"]
            s1 = a["effective_end_year"] or 2026
            if int(s0) <= fy <= int(s1):
                ours += 1
        gap.append({
            "region_system_version": v, "region_name": rn, "fiscal_year": fy,
            "administrative_region_id": g["administrative_region_id"],
            "nigc_operation_count": g["operation_count"],
            "cedar_properties_assigned": ours,
            "difference": ours - int(g["operation_count"]),
            "gap_is_not_automatically_an_error":
                "An NIGC 'operation' is an entity submitting audited or reviewed "
                "financial statements for a fiscal year; NIGC's map is a list of "
                "LOCATIONS. The two universes differ by construction. Investigate: "
                "closed rows marked active, duplicates, name variants, multiple "
                "locations under one submission, and non-IGRA tribally owned "
                "properties that NIGC never counts.",
            "source_document": g["source_document"],
            "source_url": ARCHIVE, "built_date": TODAY,
        })
    wr(REVIEW / f"nigc_coverage_gap_{TODAY}.csv", gap, list(gap[0].keys()))

    # ---- 5. series breaks -------------------------------------------------
    D = f"{ARCHIVE} (documents named in `source`)"
    breaks = [
        # -- the two rows series_breaks.csv is waiting on -------------------
        dict(dataset="nigc_regional_ggr", column="region_name",
             break_period="FY2002 -> FY2003", break_type="REGION_BOUNDARY_CHANGE",
             what_changed="MONTANA MOVED FROM REGION I TO REGION IV while both "
             "regions kept their names. This is the boundary-moved-without-a-"
             "rename case. Measured: the FY2002 report prints Region I = 72 "
             "operations / $1,196,178K and Region IV = 75 / $3,523,690K. The "
             "FY2003 report restates the SAME FY2002 as Region I = 47 / "
             "$1,230,194K and Region IV = 109 / $3,537,227K.",
             effect_on_series="A Region I series spanning FY2002-FY2003 loses a "
             "quarter of its operations to a definition, not to closures. "
             "Region I and Region IV are not comparable across the boundary.",
             verification_status="MEASURED",
             source="gamingrevenuesbyregion2002to2001.pdf; gamingrevenuesbyregion2003to2002.pdf"),
        dict(dataset="nigc_regional_ggr", column="region_name",
             break_period="FY2003", break_type="REGION_RENAMED",
             what_changed="'Eastern Region' renamed 'Region VI'. Same seven "
             "states, same 22 operations; revenue restated $3,819,897K -> "
             "$3,835,825K.",
             effect_on_series="A join on region NAME breaks at FY2003 even "
             "though the geography did not.",
             verification_status="MEASURED",
             source="gamingrevenuesbyregion2002to2001.pdf; gamingrevenuesbyregion2003to2002.pdf"),
        dict(dataset="nigc_regional_ggr", column="region_name",
             break_period="FY2008", break_type="REGION_SPLIT",
             what_changed="Six regions became SEVEN. Roman numerals replaced by "
             "city names ('Portland (fka Region I)'), and Region V (Kansas, "
             "Oklahoma, Texas) split into Tulsa (Kansas + EASTERN Oklahoma) and "
             "OK City (WESTERN Oklahoma + Texas). The Oklahoma split is stated "
             "in NIGC's own legend and is visible on the FY2014 map, where "
             "Oklahoma is drawn in two colours.",
             effect_on_series="The split is NOT a clean decomposition. The "
             "FY2008 report restates FY2007 on the 7-region basis at 391 ops / "
             "$26,143,472K against the FY2007 report's own 382 / $26,016,098K, "
             "and Tulsa 57 + OK City 45 = 102 against Region V's 100.",
             verification_status="MEASURED",
             source="gamingrevenuesbyregion2008to2007.pdf; gamingrevenuebyregion2007.pdf"),
        dict(dataset="nigc_regional_ggr", column="region_name",
             break_period="FY2017", break_type="REGION_SPLIT",
             what_changed="Seven regions became EIGHT: Rapid City (Montana, "
             "North Dakota, South Dakota, Wyoming) split out of St. Paul. "
             "CORRECTION TO series_breaks.csv, which dates this FY2020. "
             "Measured: the FY16 map prints St. Paul 132 AFS / $4.9B and has no "
             "Rapid City region; the FY17 map restates FY2016 as St. Paul 93 + "
             "Rapid City 39 = 132 and $4.5B + $0.4B = $4.9B.",
             effect_on_series="St. Paul drops ~39 operations and ~$0.4B at "
             "FY2017 with no change in the industry. The 2009->FY2020 framing "
             "in series_breaks.csv is wrong at both ends: 2009 was already the "
             "7-region system (introduced FY2008), and 8 regions began FY2017.",
             verification_status="MEASURED",
             source="2016GamingRevenueDistributedbyRegion.pdf; Graphic2017GamingRevenueDistributedbyRegion.pdf"),
        dict(dataset="nigc_regional_ggr", column="operation_count",
             break_period="ongoing", break_type="SOURCE_DEFINITION_CHANGE",
             what_changed="NIGC's own wording, FY2022-FY2025 reports: the GGR "
             "figure 'is an aggregate of gaming revenues collected from the "
             "audited financial statements of [N] gaming operations', and "
             "'Tribes are required to submit financial statements within 120 "
             "days after the end of the operation's fiscal year.' The FY2025 "
             "report adds that because tribes have differing fiscal year-ends, "
             "'fiscal year GGR data found in this report includes revenue which "
             "may have been earned up to 16 months prior to publication.' "
             "THE CONSOLIDATED-AUDIT CLAUSE IS NOT SUPPORTED: the word "
             "'consolidated' does not appear in any of the 24 NIGC GGR "
             "documents retrieved for this build.",
             effect_on_series="An NIGC operation count is a count of audited "
             "financial statements, not of buildings. NIGC's own gaming "
             "location map lists 490 locations against 545 FY2025 operations, "
             "so the two NIGC universes do not agree with each other either. A "
             "difference against our facility file is a lead, not an error.",
             verification_status="DOCUMENTED",
             source="GGR25_071526.pdf; GGR24_080425.pdf; GGR23_Final.pdf; GGRFY22_071923_Final.pdf"),
        dict(dataset="nigc_regional_ggr", column="operation_count",
             break_period="FY2005", break_type="SOURCE_DEFINITION_CHANGE",
             what_changed="FY2005 report footnote: 'Compiled from gaming "
             "operation audited financial statements received by the NIGC "
             "through June 29, 2006; 12 operations' revenue figures compiled "
             "from fee worksheets, as audited financial statements of those "
             "operations were not received.' Late submissions were SUBSTITUTED "
             "from fee worksheets in FY2005, not excluded.",
             effect_on_series="12 of 391 FY2005 operations carry a different "
             "measurement basis from the other 379. No later report repeats "
             "this footnote, so whether the practice continued is unknown.",
             verification_status="DOCUMENTED",
             source="2005vs2004gmgrevbyregn.pdf"),
        # -- breaks not previously in the file ------------------------------
        dict(dataset="nigc_regional_ggr", column="ggr_usd",
             break_period="FY2001-FY2008", break_type="PRIOR_YEAR_RESTATEMENT",
             what_changed="Every early NIGC report restates the prior year as "
             "late audits arrive, and the restatement is not always upward. "
             "FY2003: own report 330 ops / $16,730,148K, restated by the FY2004 "
             "report to 358 / $16,826,126K. FY2004: own 367 / $19,407,510K, "
             "restated to 375 / $19,479,134K. FY2005 Region II restated DOWN "
             "$7,042,686K -> $6,992,784K. FY2006 Region III restated DOWN "
             "$2,927,711K -> $2,718,914K, a 7.1% cut.",
             effect_on_series="The same fiscal year has two published values. "
             "This file publishes the FIRST publication and records the vintage "
             "in `figure_vintage`; a user who wants the restated value must "
             "take it from the following year's report. No restatement is "
             "detectable FY2021-FY2024: the FY24 report's FY2023 column equals "
             "the FY23 report's own total to the dollar ($41,905,347,538).",
             verification_status="MEASURED",
             source="gamingrevenuesbyregion2003to2002.pdf; gamingrevenuesbyregion2004to2003.pdf; 2005vs2004gmgrevbyregn.pdf; gamingrevenuebyregion2006.pdf; gamingrevenuebyregion2007.pdf; GGR23_Final.pdf; GGR24_080425.pdf"),
        dict(dataset="nigc_regional_ggr", column="ggr_usd",
             break_period="FY2013-FY2020", break_type="PRECISION_CHANGE",
             what_changed="For FY2013-FY2020 NIGC published only a distribution "
             "MAP, with each region rounded to $0.1B. Exact-dollar regional "
             "tables stop after the FY2012 table and resume with the FY2022 "
             "report (which also carries exact FY2021). FY2013 and FY2014 exist "
             "only inside an image-only PDF with no text layer.",
             effect_on_series="FY2013-FY2020 regional figures carry up to "
             "$50M of rounding each and cannot be summed to a precise national "
             "total. `figure_precision` marks every affected row.",
             verification_status="MEASURED",
             source="2012GGRbyRegionforWeb.pdf; NIGC_GGR_Chart_2014_Gaming_Revenue_Distributed_by_Region.pdf; GGRFY22_071923_Final.pdf"),
        dict(dataset="nigc_regional_ggr", column="fiscal_year",
             break_period="FY2010", break_type="FISCAL_YEAR_BASIS_CHANGE",
             what_changed="FY2010 report note: 'Three operations changed their "
             "Fiscal Year End Date for 2010 reporting and included only 9 "
             "months of gaming revenue in 2010.'",
             effect_on_series="Three FY2010 operations contribute nine months "
             "of revenue against twelve for the rest. NIGC does not say which "
             "regions they sit in, so the affected regional totals cannot be "
             "identified.",
             verification_status="DOCUMENTED",
             source="Gaming-Revenues-2010-2009-region.pdf"),
        dict(dataset="nigc_regional_ggr", column="ggr_usd",
             break_period="FY2020", break_type="EXOGENOUS_LEVEL_SHIFT",
             what_changed="COVID-19 closures. National GGR fell from $34.6B "
             "(FY2019) to $27.8B (FY2020), a 19.5% decrease, then rebounded to "
             "$39.0B in FY2021. NIGC: 'Fiscal Year 2020 was a major exception to "
             "the trend, where the GGR decreased due to the closure of gaming "
             "operations for different lengths of time.'",
             effect_on_series="FY2020 is not a data problem and must not be "
             "smoothed away, but any growth rate computed off an FY2020 base is "
             "a rebound, not a trend.",
             verification_status="DOCUMENTED",
             source="FY20GGRDistriMap.pdf; GGRFY22_071923_Final.pdf"),
        dict(dataset="nigc_regional_ggr", column="operation_count",
             break_period="FY2015 -> FY2016 -> FY2021", break_type="TERMINOLOGY_CHANGE",
             what_changed="The same count is labelled 'ops' on the FY15 map, "
             "'AFS' on the FY16 map, and 'submissions' on the FY21 map.",
             effect_on_series="Cosmetic, but it defeats a parser keyed to the "
             "label and it is why the FY16 map reads as a different measure "
             "when it is not.",
             verification_status="MEASURED",
             source="2015_NIGC_FY15_Gross_Gaming_Revenue_Distribution_Map.pdf; 2016GamingRevenueDistributedbyRegion.pdf; FY21_GGR_Charts_for_press_release_FINAL.pdf"),
        dict(dataset="nigc_region_assignments", column="region_name",
             break_period="FY2008-present", break_type="REGION_RENAMED",
             what_changed="One region carries four printed names across the "
             "series: 'Eastern Region' (FY2002), 'Region VI' (FY2003-FY2007), "
             "'Washington (fka Region VI)' (FY2008-FY2009), 'Washington DC' "
             "(FY2010-FY2021), 'D.C.' (FY2022-FY2025). Likewise 'OK City' "
             "(FY2008-FY2012) vs 'Oklahoma City' (FY2013 onward), and NIGC's "
             "gaming location map calls that region 'Oklahoma Region'.",
             effect_on_series="A name join fails at four points. This build "
             "normalises to one `region_name` per system version and keeps the "
             "printed variants in the build log.",
             verification_status="MEASURED",
             source="gamingrevenuesbyregion2008to2007.pdf; Gaming-Revenues-2010-2009-region.pdf; GGRFY22_071923_Final.pdf; https://www.nigc.gov/map/"),
        dict(dataset="nigc_region_assignments", column="region_states_in_force",
             break_period="FY2002-2026", break_type="GEOGRAPHY_COVERAGE_CHANGE",
             what_changed="States enter and leave the printed legend. Wyoming "
             "is in the FY2002 Region IV legend, ABSENT from the FY2003 and "
             "FY2004 legends, and back in FY2005. Indiana and Massachusetts "
             "appear in the current (2026) legend and in no earlier one. "
             "Arkansas appears in NO published NIGC legend, yet NIGC's own "
             "gaming location map places an Arkansas location in the Tulsa "
             "region.",
             effect_on_series="A state-to-region rule applied outside the years "
             "its legend covers is an invention. Assignments for out-of-legend "
             "state-years are left BLANK and written to "
             "review/nigc_out_of_legend_states_*.csv.",
             verification_status="MEASURED",
             source="gamingrevenuesbyregion2002to2001.pdf; gamingrevenuesbyregion2003to2002.pdf; 2005vs2004gmgrevbyregn.pdf; https://www.nigc.gov/office-of-chief-of-staff/compliance/regions/"),
        dict(dataset="nigc_regional_ggr", column="fiscal_year",
             break_period="FY2000; FY2026", break_type="SERIES_BOUNDARY",
             what_changed="NIGC's Gross Gaming Revenue Reports archive begins "
             "with an FY2001-and-FY2002 comparison. There is no FY2000 regional "
             "report on nigc.gov and none was found. FY2026 is not published: "
             "the FY2025 report was released 2026-07-15 and an FY2026 report "
             "would follow in mid-2027.",
             effect_on_series="Cedar Press targets 2000-2026; the NIGC regional "
             "series can only be sourced 2001-2025. FY2000 and FY2026 are "
             "absent because the source does not exist, not because we did not "
             "look.",
             verification_status="MEASURED",
             source=ARCHIVE),
    ]
    for b in breaks:
        b["built_date"] = TODAY
    wr(REVIEW / f"nigc_series_breaks_{TODAY}.csv", breaks,
       ["dataset", "column", "break_period", "break_type", "what_changed",
        "effect_on_series", "verification_status", "source", "built_date"])
    print("   verification_status:",
          dict(Counter(b["verification_status"] for b in breaks).most_common()))

    # ---- 6. states outside every published legend -------------------------
    oo = []
    seen = set()
    for a in assigns:
        if not a["assignment_method"].startswith("state_absent"):
            continue
        k = (a["facility_id"], a["region_system_version"])
        if k in seen:
            continue
        seen.add(k)
        oo.append({
            "facility_id": a["facility_id"], "state": a["facility_state"],
            "city": a["facility_city"], "region_system_version": a["region_system_version"],
            "reason": "State does not appear in the NIGC region legend published "
                      "for this region system. No region assigned. Back-filling "
                      "today's map would invent a boundary NIGC never printed.",
            "source_url": REGIONS_PAGE, "built_date": TODAY,
        })
    if oo:
        wr(REVIEW / f"nigc_out_of_legend_states_{TODAY}.csv", oo, list(oo[0].keys()))

    # ---- 7. arithmetic audit trail ---------------------------------------
    wr(REVIEW / f"nigc_total_reconciliation_{TODAY}.csv", arith, list(arith[0].keys()))

    print("\nFY2025 sanity, straight from GGR25_071526.pdf")
    tot = sum(r["ggr_usd"] for r in ggr if r["fiscal_year"] == 2025)
    ops = sum(r["operation_count"] for r in ggr if r["fiscal_year"] == 2025)
    print(f"   8 regions sum to ${tot/B:,.3f}B against a printed $46.16B; "
          f"{ops} operations against a printed 545")
    print(f"   an even split would be ${tot/ops/1e6:,.1f}M per operation - and "
          f"54% of operations reported under $25M. That is why there is no "
          f"property-level revenue column.")


if __name__ == "__main__":
    main()
