#!/usr/bin/env python3
"""
Cedar Press - 23f: Give the gaming dataset a time dimension.

THE PROBLEM
-----------
`code/35_coverage_audit.py` reported gaming as the only dataset it could not
place in time at all:

    gaming_facilities        no usable date column  (2 file(s))

That report was TRUE of the audit and FALSE of the data. Both files carry
dates; neither carries them under a name the audit's `DATE_COLS` list knows:

    gaming_facilities.csv          open_date / close_date / *_observed_date
    gaming_facility_metrics.csv    observation_date / observation_period

So the first half of this script's job is not a build at all - it is a naming
fix in the audit (done in 35). The second half is the real work: a casino is
not an event, it is an ENTITY WITH A LIFESPAN, and the columns that make that
usable are `opened`, `closed`, and an as-of date on every point-in-time
measurement.

WHAT THIS SCRIPT ADDS
---------------------
1. `as_of_date` on every metric observation. `observation_date` covers 64,181
   rows and `observation_period` (a bare fiscal year) covers the other 1,042;
   they are exactly complementary, so a single derived column reaches 100%.
   A machine count with no as-of date is uninterpretable - "1,200 gaming
   machines" means nothing without a when.

2. `open_date_not_before` / `open_date_not_after` on every facility: a clean
   ISO INTERVAL that is always true, alongside the verbatim source value which
   is never modified.

3. `open_date_precision`, derived rather than assumed. The source dates LOOK
   day-precise and mostly are not - see PLACEHOLDER DETECTION below.

4. `open_date_class` in {exact, bounded, absent} on all 774 rows, with
   `open_date_absent_reason` naming why whenever it is `absent`.

PLACEHOLDER DETECTION (the finding that forced this design)
-----------------------------------------------------------
Of the 447 ISO open dates inherited from the Casino City Tribal Property List:

    day == 31 (and specifically 12-31)   150   33.6%
    day == 15                            148   33.1%

Under genuine day-precision dates each would be near 3%. Two thirds of these
dates are placeholders wearing day precision. `YYYY-12-31` is a year-precision
placeholder and `YYYY-MM-15` is the mid-month convention. This script therefore
DOWNGRADES their precision and widens their interval to the year or the month
the source actually supports. It never deletes the original value.

The cost is that a genuinely-Dec-31 or genuinely-15th opening is recorded as
less precise than it is - roughly one row in each bucket, against ~290 rows of
false precision removed. Precision over recall.

RULES THAT BIND THIS SCRIPT
---------------------------
* A land decision date is NOT an opening date. It bounds an opening from below
  only when the decision is for THIS facility's site, which a (tribe, state)
  join cannot establish - see LAND_DECISION_BOUNDS.
* A bound is more valuable than a fabricated precise date.
* Rows with no date are retained, never dropped.

Reads and writes data/clean/gaming_*.csv in place, plus
data/raw/external/gaming/facility_opening_research_<date>.csv - one archived
evidence file per research sweep - for the hand-researched openings.
"""

import calendar
import csv
import glob
import re
import shutil
from datetime import date
from pathlib import Path

CEDAR = Path(r"C:\Users\esm247\Desktop\Cedar Press")
CLEAN = CEDAR / "data" / "clean"
RAW = CEDAR / "data" / "raw" / "external" / "gaming"
TODAY = date.today().isoformat()

# One evidence file PER SWEEP, named by the date the research was done, read
# newest-last so a later sweep supersedes an earlier one on the same facility.
# Was a single hardcoded 2026-08-05 path; globbed on 2026-08-06 when a second
# sweep was added. Appending to the old file instead would have put 2026-08-06
# research inside a file called ...2026-08-05.csv and destroyed the provenance
# that makes the evidence auditable.
RESEARCH_GLOB = "facility_opening_research_*.csv"


def research_files():
    return sorted(RAW.glob(RESEARCH_GLOB))


# ---------------------------------------------------------------- helpers ---
def load(name):
    with open(CLEAN / name, encoding="utf-8-sig", newline="") as fh:
        rd = csv.DictReader(fh)
        return list(rd), list(rd.fieldnames)


GRAVE = CEDAR / "graveyard"


def save(name, rows, fields):
    # never-delete rule: the pre-build vintage goes to the central graveyard,
    # not next to the live file where a glob would pick it up.
    GRAVE.mkdir(exist_ok=True)
    bak = GRAVE / f"{Path(name).stem}_pre_temporal_{TODAY}.csv"
    if not bak.exists():
        shutil.copy2(CLEAN / name, bak)
    with open(CLEAN / name, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)
    print(f"  wrote {name}  rows={len(rows)}  cols={len(fields)}")


def add_cols(fields, new):
    for c in new:
        if c not in fields:
            fields.append(c)
    return fields


def month_end(y, m):
    return f"{y:04d}-{m:02d}-{calendar.monthrange(y, m)[1]:02d}"


ISO = re.compile(r"^(\d{4})-(\d{2})-(\d{2})$")
YONLY = re.compile(r"^(\d{4})(?:\.0)?$")
DECADE = re.compile(r"^(\d{3})0s$")


def interpret(raw_value, source_basis):
    """Turn a source date string into (precision, not_before, not_after, note).

    Returns precision None when the value cannot be read at all.
    `source_basis` is the existing free-text provenance string; the placeholder
    downgrade is applied only to the Casino City vintage, because that is the
    vintage in which the 12-31 / day-15 concentration was measured.
    """
    v = (raw_value or "").strip()
    if not v:
        return None, "", "", ""
    basis = source_basis or ""
    casino_city = "Casino City" in basis

    m = ISO.match(v)
    if m:
        y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
        # A hand-researched row records its own precision in the basis string.
        # Honour it, so re-running this script does not silently promote a
        # year-precision finding to day precision just because it is stored as
        # an ISO date.
        if "year-precision" in basis:
            return "year", f"{y:04d}-01-01", f"{y:04d}-12-31", ""
        if "month-precision" in basis:
            return "month", f"{y:04d}-{mo:02d}-01", month_end(y, mo), ""
        if casino_city and mo == 12 and d == 31:
            return ("year", f"{y:04d}-01-01", f"{y:04d}-12-31",
                    "YYYY-12-31 is this source's year-precision placeholder "
                    "(150 of 447 open dates fall on day 31 vs ~3% expected); "
                    "month and day are not source-stated")
        if casino_city and d == 15:
            return ("month", f"{y:04d}-{mo:02d}-01", month_end(y, mo),
                    "day 15 is this source's mid-month placeholder "
                    "(148 of 447 open dates fall on day 15 vs ~3% expected); "
                    "day is not source-stated")
        return "day", v, v, ""

    m = YONLY.match(v)
    if m:
        y = int(m.group(1))
        return ("year", f"{y:04d}-01-01", f"{y:04d}-12-31",
                "source states a year only" if "." not in v else
                "source value carries a float artefact ('YYYY.0'); year only")

    m = DECADE.match(v)
    if m:
        dec = int(m.group(1)) * 10
        return ("decade", f"{dec:04d}-01-01", f"{dec + 9:04d}-12-31",
                "source states a decade, not a year")

    return None, "", "", f"unparseable source value {v!r}"


# ------------------------------------------------------ absent-row rules ---
# Rows that are in the file for a reason but are not datable facilities. These
# come from the votingpatterns roster, which carries one row per TRIBE and uses
# the facility_name field to say "this tribe has no casino". They are retained
# (never-delete rule) and marked so nobody reads them as an undated casino.
NO_FACILITY = re.compile(
    r"\bno casino\b|no gaming|tribal admin only|casino - none|- none\b", re.I)
CROSS_REF = re.compile(
    r"see (tuolumne|mooretown|ca entry)\b|- actual [A-Z]{2}\b", re.I)

# Rows RULED not to be gaming facilities against a source, one at a time.
# The name-based rule above deliberately cannot reach these: the build refuses
# to key "not a casino" off words like `travel plaza`, `smoke shop` or
# `trading post`, because several tribal properties with exactly those names
# demonstrably DO host gaming (Choctaw Travel Plaza Casino Too, Wewoka Trading
# Post Casino, Watonga Bingo and Smoke Shop). So the only safe way to retire
# one is to read its operator's own description. Added 2026-08-06.
RULED_NOT_FACILITY = {
    # --- 2026-08-06 session 3 -------------------------------------------------------
    # Three votingpatterns roster rows whose SUBJECT does not exist as
    # described. Each is ruled against the tribe's own enterprise list, not
    # against a name pattern. Note the contrast with RULED_GAMING_UNCERTAIN
    # below: these are roster rows built from a tribe's enterprise page, so
    # that page is the right evidence. A Casino City gaming-roster row is not
    # refuted the same way.
    "VP-0155": (
        "not a gaming facility - RULED 2026-08-06 (session 3). Peoria Ridge is the Peoria "
        "Tribe's 18-hole GOLF COURSE. peoriatribe.com lists Buffalo Run Casino "
        "& Resort and Peoria Ridge Golf Course as SEPARATE enterprises, and "
        "the row's address (10238 S 580 Rd, Miami OK) is the golf course, not "
        "the casino (8520 S Highway 69A, carried on CCP-646400 Peoria Gaming "
        "Center). Same class of row as Lake of Isles, Foxwoods' golf course "
        "(VP-0002). There is no gaming opening to date. "
        "https://www.peoriatribe.com/"),
    "VP-0169": (
        "not a distinct gaming property - RULED 2026-08-06 (session 3). The row fuses "
        "three different nations' facts: '7 Clans' is the OTOE-MISSOURIA "
        "brand (this file holds six 7 Clans rows, all Otoe-Missouria, none in "
        "Ponca City); the tribe field says Ponca Tribe of Oklahoma, whose own "
        "Ponca City casino IS in this file as CCP-411000 Blue Star Gaming and "
        "Casino, 20 White Eagle Drive, opened 2010-10-15; and the location, "
        "Ponca City, is where the OSAGE NATION's casino sits (CCP-859600 / "
        "VP-0199, 2007). The Indian Gaming Dataset independently records the "
        "Ponca Tribe's Ponca City property as 'Two Rivers Casino', 101 White "
        "Eagle Dr, grand opening 2010, closed 2013 - the same White Eagle "
        "site as CCP-411000. Every real property this row could denote is "
        "already in the file and dated. Dating this row would create a fourth "
        "Ponca City record for three casinos."),
    "VP-0160": (
        "not a distinct gaming property - RULED 2026-08-06 (session 3). The name does not "
        "resolve: potawatomi.org's gaming enterprise list has exactly TWO "
        "properties, Grand Casino Hotel & Resort and FireLake Casino, and "
        "'FireLake Express' is the Citizen Potawatomi Nation's GROCERY chain. "
        "The votingpatterns source file that contributed this row cites "
        "'GrandResortOK.com' and annotates it 'Adjacent to Grand' - i.e. the "
        "roster itself recorded it as an adjunct of the Grand Casino "
        "property, not as a casino of its own. Both candidate properties are "
        "already dated here (CCP-766700 Grand Casino Hotel Resort, 2006; "
        "CCP-409700 FireLake Casino, 1989), and the duplicate queue scores "
        "this row STRONG against BOTH - which is the tell that it is a merged "
        "label rather than a property. A date was available (October 2006 for "
        "the Grand) and was deliberately NOT recorded. "
        "https://www.potawatomi.org/"),
}


# Rows where it is NOT ESTABLISHED whether the location hosted gaming.
#
# CORRECTION 2026-08-06 (session 3), and the reasoning matters more than the two rows.
# TPL-0070 MidJim #2 and CCP-764800 MidJim St. Ignace were retired on
# 2026-08-06 as `not a gaming facility` on the strength of saulttribe.com's
# CURRENT enterprise page, which describes MidJim as a convenience-store and
# fuel brand. That page is about the brand as it stands in 2026. The two rows
# it was used to refute are CASINO CITY TRIBAL PROPERTY LIST records that
# carry CLOSE DATES - 2003-11-21 and 2005-03-15 - so the vendor was describing
# locations that stopped operating twenty years before the page was written.
#
# The vendor list is a GAMING property roster, and its Montana section makes
# that unmistakable: it carries `B & S Laundry`, `Dad's Bar`, `TJ's Quikstop`
# and `Allard's General Store`, which are licensed video-gambling locations,
# not casinos. A tribal convenience store appearing in that roster is
# therefore evidence FOR gaming at the location, not against it - and §3 of
# the build log already warns that travel plazas and smoke shops in this file
# demonstrably do host gaming.
#
# So the retirement asserted a negative its evidence could not carry, which is
# the same over-claim §2 corrected on `not_gaming_commencement`. The rows keep
# their reclassification out of "undated casino" - which was the right
# instinct - but the reason now states both sides instead of ruling.
RULED_GAMING_UNCERTAIN = {
    "TPL-0070": (
        "gaming status not established - RULED 2026-08-06 (session 3), REPLACING a "
        "2026-08-06 ruling of 'not a gaming facility' that over-claimed. FOR "
        "gaming: this row is a Casino City Tribal Property List record, and "
        "that roster is a gaming-property roster (its Montana entries include "
        "B & S Laundry, Dad's Bar and TJ's Quikstop, which are licensed "
        "video-gambling locations). It carries a close date of 2003-11-21, so "
        "the vendor tracked it as an operating gaming location until then. "
        "AGAINST gaming: saulttribe.com's CURRENT enterprise page describes "
        "MidJim as a convenience-store and fuel brand listed separately from "
        "Kewadin Casinos - 'Midjim has two locations in the Upper Peninsula, "
        "in Sault Ste. Marie and St. Ignace. Both locations offer items such "
        "as gasoline, cigarettes, beer, wine and other convenience items.' "
        "That page describes the brand in 2026 and cannot speak to a location "
        "that closed in 2003. Neither the opening date nor the gaming status "
        "is established. https://www.saulttribe.com/enterprises/midjim"),
    "CCP-764800": (
        "gaming status not established - RULED 2026-08-06 (session 3), REPLACING a "
        "2026-08-06 ruling of 'not a gaming facility' that over-claimed (see "
        "TPL-0070 for the full reasoning; same MidJim brand, Casino City "
        "close date 2005-03-15). SEPARATE AND STILL OPEN: this row is "
        "labelled 'St. Ignace' but Casino City gives its address as 2205 "
        "Shunk Road, which is in Sault Ste. Marie - the two MidJim locations "
        "appear to have been crossed. Queued, not corrected. "
        "https://www.saulttribe.com/enterprises/midjim"),
    "VP-0123": (
        "identity not established - RULED 2026-08-06 (session 3). No distinct Choctaw "
        "CASINO in Atoka is evidenced anywhere: 'Atoka' appears nowhere in a "
        "31,054-row CDX enumeration of choctawcasinos.com, and the live "
        "locations page (fetched 2026-08-06) lists Durant, Pocola, Hochatown, "
        "Broken Bow, Idabel, McAlester, Grant and Stringtown as casinos, with "
        "Atoka appearing only as CHOCTAW TRAVEL PLAZA ATOKA. Stringtown is in "
        "Atoka County, which is a plausible source of the mislabel. This file "
        "already holds the tribe's Atoka gaming property as CCP-970700 "
        "Choctaw Travel Plaza - Atoka (1302 South Mississippi, 2010-06-15) - "
        "and travel plazas in this file DO host gaming, so that row is not a "
        "non-casino. NOT ruled a duplicate: this row's address is 1790 S "
        "Mississippi Ave against the vendor's 1302 South Mississippi, and a "
        "different street number is not a merge this project will make on "
        "inference. Searching harder cannot date a row whose subject is "
        "undefined. https://www.choctawcasinos.com/locations/"),
    "VP-0165": (
        "identity not established - RULED 2026-08-06 (session 3). The Sac and Fox Nation "
        "of Oklahoma's Shawnee gaming property is The Black Hawk Casino, "
        "already in this file as CCP-692600 (42008 Westech Road, Shawnee, "
        "2004-07-28), and the Indian Gaming Dataset independently lists "
        "Shawnee's casinos as Thunderbird, FireLake, Grand, Kickapoo Shawnee "
        "and The Black Hawk - with no 'Sac and Fox Casino Shawnee' among "
        "them. NOT ruled a duplicate of CCP-692600, because this row's "
        "address (920866 S Hwy 99) is a STROUD address - the Sac and Fox "
        "Nation's headquarters sits at 920883 S Hwy 99, Stroud - while its "
        "city field says Shawnee. Name, city and address disagree, and the "
        "votingpatterns roster cites 'SacAndFoxCasinos.com' for it, a domain "
        "the 2026-08-06 sweep found belongs to a DIFFERENT TRIBE (the Sac and "
        "Fox Nation of MISSOURI, Powhattan, Kansas). Resolve which property "
        "this row is before dating it."),
}


# Rows RULED to be the SAME PROPERTY as another row that already carries the
# date. Added 2026-08-06 (session 3), and this is the ruling §7.5 of the build log asked
# for: 49 of the 56 undated rows carried `duplicate_risk = 1`, and researching
# them returned dates the file already held on a twin.
#
# WHAT SETTLED THESE, AND WHY IT IS NOT NAME SIMILARITY. The
# `23g` candidate scorer works on name tokens, city and tribe, and it
# explicitly refuses to merge. Three sources of harder evidence settled these
# rows, none of which the scorer can see:
#
#   1. THE ROSTER'S OWN `notes` COLUMN. The votingpatterns file that
#      contributed every VP-* row -
#      data/raw/external/gaming/directory_core/canonical_casino_addresses_supplement.csv
#      - carries a per-record `notes` field, and on several of these rows it
#      says in as many words that the row is the same property: "Same
#      property" (Pala hotel tower), "Same property as primary" (WinStar
#      additional plaza), "Main casino in IA" (WinneVegas-Lite). The
#      duplication was DISCLOSED AT SOURCE and had simply never been read.
#   2. THE ROSTER'S `source` COLUMN. It records which website each row was
#      built from. Where that domain is the twin property's own site -
#      NorthernLightsCasino.com, GoldenBuffaloCasino.com,
#      IronHorseBarAndCasino.com, SageHillCasino.com - the row is that
#      property, whatever its tribe and state fields say.
#   3. BYTE-LEVEL ADDRESS AGREEMENT with the dated row.
#
# THE ROW IS RETAINED AND ITS DATE IS NOT COPIED ACROSS. Copying it would put
# one opening on two rows, which is the double-count §7.5 exists to prevent.
# `duplicate_of_facility_id` points at the row that carries the date.
RULED_DUPLICATE = {
    "VP-0116": ("VP-0011", (
        "The votingpatterns source file annotates this record 'Same property' "
        "and gives its address as 11154 Hwy 76 - byte-identical to VP-0011 "
        "Pala Casino Spa Resort and to CCP-521600 (11154 Highway 76). It is "
        "the hotel tower added to the existing Pala Casino, not a separate "
        "casino. Gaming at the property commenced 2001-04-03, which VP-0011 "
        "already carries; the hotel/spa expansion opened 2003-08-19, which is "
        "an expansion, not an opening. This is the §7.5c row whose "
        "well-sourced date was deliberately NOT recorded, and this ruling is "
        "why: the date is real and it belongs to VP-0011."))
    ,
    "VP-0133": ("CCP-411600", (
        "The votingpatterns source file annotates this record 'Same property "
        "as primary' and gives its address as 777 Casino Ave, Thackerville - "
        "which the Indian Gaming Dataset also gives for WinStar World Casino "
        "and Resort (grand opening 2003, expansion 2024). WinStar is a single "
        "complex whose themed plazas (Beijing, Madrid, Paris, Rome, Vienna, "
        "London, New York, Cairo) were added across successive expansions; "
        "there is no 'additional plaza' with an opening of its own. "
        "CCP-411600 carries the 2003 date."))
    ,
    "VP-0261": ("CCP-67000", (
        "Address is byte-identical to the dated row - 6800 Y Frontage Rd NW "
        "against CCP-67000's 6800 Y Frontage Road Northwest, both Walker MN, "
        "both Leech Lake Band of Ojibwe - and the votingpatterns source file "
        "cites 'NorthernLightsCasino.com', the twin's own site. One property. "
        "READ THE TWIN'S EVENT RULING: researching this row is what "
        "established that CCP-67000's 2001-05-15 is a REPLACEMENT BUILDING, "
        "not the original opening (see RULED_EVENT). The original opening is "
        "still unsourced."))
    ,
    "VP-0371": ("CCP-11800", (
        "Address is byte-identical to the dated row - 321 Sitting Bull St "
        "against CCP-11800's 321 Sitting Bull Street, both Lower Brule SD, "
        "both Lower Brule Sioux Tribe - the votingpatterns source file cites "
        "'GoldenBuffaloCasino.com', and the Indian Gaming Dataset "
        "independently records 'The Golden Buffalo Casino Restaurant and "
        "Motel' at 321 Sitting Bull St with a 1992 grand opening, agreeing "
        "with CCP-11800's 1992-02-15. Three sources, one property."))
    ,
    "VP-0393": ("CCP-908000", (
        "SAME PROPERTY, AND THE TRIBE AND STATE ON THIS ROW ARE WRONG. Sage "
        "Hill Casino is on the FORT HALL Reservation in IDAHO and belongs to "
        "the SHOSHONE-BANNOCK Tribes - the operator's own page states "
        "'Located on the Fort Hall Indian Reservation, 3 mi South of "
        "Blackfoot on Highway 91. I-15 Exit 89' (sho-ban.com, fetched "
        "2026-08-06 (session 3)). This row says Shoshone-PAIUTE Tribes at Owyhee, NEVADA. "
        "The votingpatterns source file cites 'SageHillCasino.com' - the "
        "Idaho property's own site - and annotates the record 'NV side', so "
        "the roster knowingly filed an Idaho casino under a Nevada tribe. "
        "This file ALREADY HOLDS the property correctly as CCP-908000 Sage "
        "Hill Casino, Shoshone-Bannock Tribes, Idaho, open 2009-03-18. "
        "The 23g duplicate scorer could not find that twin because it "
        "searches within a state and this row's state field is the corrupted "
        "one. THIS IS WHY THE §7.5c DATE WAS HELD: applying the sourced "
        "'February 2009' opening here would have dated a Nevada row with an "
        "Idaho casino's opening while the correct row already carried it. "
        "NOTE A REMAINING CONFLICT, not resolved here: the held source says "
        "February 2009 and Casino City says 2009-03-18. Both are early 2009; "
        "neither is preferred without a further source."))
    ,
    "VP-0362": ("CCP-39900", (
        "Cross-reference stub. The facility_name says '- main IA' and the "
        "votingpatterns source file annotates the record 'Main casino in IA', "
        "both pointing at the Winnebago Tribe of Nebraska's Iowa property - "
        "CCP-39900 WinnaVegas Casino Resort, 1500 330th Street, Sloan IA, "
        "1992. Not a distinct Nebraska facility. The CROSS_REF name rule did "
        "not catch it because that rule keys on '- actual XX' and 'see X', "
        "and this row says '- main IA'."))
    ,
    "VP-0363": ("CCP-688700", (
        "Same property, and the TRIBE on this row is wrong. The "
        "votingpatterns source file cites 'IronHorseBarAndCasino.com' for "
        "this record - the twin's own site - and the twin is CCP-688700 Iron "
        "Horse Bar & Casino, Emerson NE, open 2004-07-09, operated by the "
        "WINNEBAGO Tribe of Nebraska. This row attributes it to the OMAHA "
        "Tribe of Nebraska. Emerson is a village of about 800 people and does "
        "not host two casinos of the same name run by two tribes. The "
        "'- small' suffix is the roster's size-class descriptor, not a "
        "separate property. Addresses differ (1402 Hwy 75 against the "
        "vendor's 1106 South Main Street) and that discrepancy is disclosed "
        "rather than smoothed over."))
    ,
    "VP-0164": ("CCP-800600", (
        "Same property. Name, city and tribe all agree with CCP-800600 Sac & "
        "Fox Nation Stroud Casino (Stroud OK, 2005-06-15), and the Indian "
        "Gaming Dataset records the Sac and Fox Nation Casino at 356120 926 "
        "Rd, Stroud - the same 356120 house number this row carries as "
        "'356120 EW 1240', which is the same rural address under Oklahoma's "
        "two road-naming conventions. Contrast VP-0165, the tribe's other "
        "roster row, which is NOT ruled a duplicate because its name, city "
        "and address disagree with each other."))
    ,
    "VP-0150": ("CCP-962300", (
        "Same property - Indigo Sky Casino, Eastern Shawnee Tribe, Wyandotte "
        "OK - and THIS ROW IS THE ONE WITH THE CORRECT ADDRESS. It carries "
        "70220 E Hwy 60, which the Indian Gaming Dataset also gives for "
        "Indigo Sky Casino (70220 US-60). The dated twin CCP-962300 carries "
        "130 North Oneida Street, which is the PREDECESSOR Bordertown "
        "Casino's address (the Indian Gaming Dataset puts Bordertown Casino & "
        "Arena at 129 Oneida St). So the twin is dated, and this row is "
        "correctly located, and they are one casino. READ THE TWIN'S EVENT "
        "RULING: CCP-962300's 1981-12-31 cannot be Indigo Sky's opening."))
    ,
}


# ------------------------------------------------ WHICH EVENT IS DATED? ----
# `open_date` was silently carrying two different meanings: "gaming commenced
# here" and "this property opened", which are not the same event on a property
# that existed before it hosted gaming. Pooled, they corrupt any "tribal gaming
# since 19xx" series at the left tail - and corrupt it invisibly, because the
# basis column says the date is exact and it IS exact, just about a different
# event. `open_date_event` names the event so a subscriber does not have to
# guess.
#
#   gaming_commenced         the date marks when gaming began here
#   property_opened          the date marks the property's establishment
#   not_gaming_commencement  verified NOT a gaming date; which event it marks
#                            is not established
#   unspecified              the source publishes an "Open Date" for a gaming
#                            property without saying which event it marks
#
# `unspecified` is the honest default for the Casino City vintage, and it is
# most of the file. It is not a defect to be cleaned - it is what the source
# supports. Splitting `open_date` into `property_opened_date` and
# `gaming_opened_date` was considered and rejected for exactly this reason: it
# would force 447 rows into one column or the other on evidence that does not
# exist, replacing a disclosed ambiguity with an undisclosed guess.

# The first widely-documented high-stakes tribal bingo hall is the Seminole
# Tribe's Hollywood operation, opened December 1979 - the operation that
# produced Seminole Tribe v. Butterworth and, through it, IGRA. This file
# carries it at 1979. A tribal gaming property dated BEFORE that is therefore
# prima facie dating something other than gaming, whatever else is true.
TRIBAL_GAMING_ERA_FLOOR = 1979

# Hand-verified event assignments. Each carries the source that settles it.
VERIFIED_EVENT = {
    "CCP-1189200": (
        "not_gaming_commencement",
        "Verified against the operator's own site (crosbylodge.com, Internet "
        "Archive snapshot 2001-04-28): Crosby Lodge is a lodge, grocery store, "
        "snack bar and bar at Sutcliffe on Pyramid Lake. The page describes "
        "lodging, tackle, fuel, an RV park and fishing derbies and contains no "
        "mention of gaming, slot machines, bingo or a casino. It states 'Our "
        "lodge has been in the family since 1896' and 'We have been your hosts "
        "since 1970' - NEITHER of which is 1905, so what the source's "
        "1905-06-07 marks is not established either. It is certainly not the "
        "date gaming commenced.",
        "https://web.archive.org/web/20010428005337/http://www.crosbylodge.com/",
        "Our lodge has been in the family since 1896. ... We have been your "
        "hosts since 1970"),
}


# Per-facility event rulings, added 2026-08-06.
#
# WHY THIS IS A TABLE AND NOT A RULE. The hand-researched branch below assigns
# `gaming_commenced` unless the researcher's note trips a keyword list. Auditing
# the 59 researched rows showed the keyword list misses cases and that widening
# it makes things WORSE: 13 rows mention "expansion" or "replaced" in a note
# that is nonetheless correctly dating the ORIGINAL opening ("Describes the
# ORIGINAL casino opening, not the hotel/RV park additions"; "not a later hotel
# or expansion"). A broader regex would have flipped all 13. The four rows
# below are the ones where the row's OWN cited evidence states that gaming, or
# the property, was already operating before the date recorded - so the date
# cannot be gaming commencement. Each is ruled individually against the quote
# already on the row, which is the same jurisprudence the project uses for
# per-UEI ownership drops.
RULED_EVENT = {
    "VP-0002": (
        "property_opened",
        "RULED 2026-08-06. Lake of Isles is Foxwoods' GOLF COURSE, not a "
        "gaming floor, and the cited quote dates the golf facility: 'Since "
        "opening in 2005, Lake of Isles has consistently been ranked as one of "
        "the top golf facilities in the country.' Gaming at Mashantucket "
        "Pequot began at Foxwoods in 1986 (bingo) / 1992 (casino), not 2005. "
        "This row is the clearest surviving example of `open_date` carrying a "
        "property-establishment date on a post-1979 row, where the "
        "pre-tribal-gaming-era detector cannot reach it. Whether an amenity "
        "golf course belongs in a gaming-facility file at all is a separate "
        "question - noted for the reconcile queue."),
    "VP-0392": (
        "property_opened",
        "RULED 2026-08-06 on the researcher's own disclosure, which the "
        "keyword rule did not catch: 'CURRENT BUILDING ONLY ... the same "
        "article says [it] replaces the older, detached casino.' The "
        "Shoshone-Bannock Tribes were operating a casino before 2019-02-05, "
        "so that date marks the current building, not gaming commencement."),
    "VP-0037": (
        "property_opened",
        "RULED 2026-08-06 on the row's own evidence: 'Dates the casino "
        "opening, not the 1986 bingo-hall predecessor.' Gaming at "
        "Mashantucket commenced at the bingo hall in 1986; 1992-02-15 is the "
        "casino building. Correct as a building date, wrong as a "
        "gaming-commencement date."),
    "VP-0142": (
        "gaming_commenced",
        "RULED 2026-08-06. The keyword rule flipped this to `property_opened` "
        "because the note mentions the later River Spirit rebuild, but the "
        "quote is unambiguous about the event: 'Opened in 1985, CNTB was the "
        "first high-stakes gaming operation in Oklahoma.' Gaming commenced at "
        "the 81st & Riverside site in 1985. SEPARATE AND UNRESOLVED: whether "
        "this ROW is that site. The Muscogee Nation's current property list "
        "has no standalone 'Muscogee Nation Casino Tulsa'; its Tulsa property "
        "is River Spirit Casino Resort, which dates to 2009 on the same "
        "81st & Riverside lineage. Queued in "
        "review/gaming_facility_identity_queue_2026-08-06.csv."),
    "VP-0153": (
        "unspecified",
        "RULED 2026-08-06 on the researcher's own caveat. The Modoc Nation's "
        "history page says 'In 1998, The Modoc Tribe ESTABLISHED The Stables "
        "Casino' - established, not opened. Chartering an enterprise and "
        "commencing gaming are different events and no source states the "
        "second, so 1998 is retained as the stated date but the event it "
        "marks is not claimed. A one-word difference in a source is exactly "
        "the kind of thing this column exists to preserve."),
    # --- 2026-08-06 session 3: three rulings on rows that were ALREADY DATED ---------
    # All three were found by researching UNDATED rows, which is the argument
    # for doing that work even when it dissolves into duplicates: it does not
    # only fill gaps, it audits the dates already present.
    "CCP-67000": (
        "property_opened",
        "RULED 2026-08-06 (session 3), resolving §7.6b of the build log. This row's "
        "2001-05-15 is a REPLACEMENT BUILDING, not the original opening. "
        "Establishing why the undated twin VP-0261 could not be dated is what "
        "surfaced it: the May 2001 date that circulates on tribal and local "
        "sites describes 'the new facility, which opened in May of 2001'. The "
        "Leech Lake Band operated Northern Lights at Walker well before that "
        "and the original opening remains unsourced - the casino's earliest "
        "archived captures (2000-08, 2001-04, 2001-05) are register.com host "
        "placeholders and the band's 2001 page is a 295-byte stub. "
        "`open_date_postdates_observation` cannot catch this row because the "
        "file holds no earlier capacity observation of the property, which is "
        "exactly the blind spot a rebuild date sits in. Usable as the current "
        "building's opening; NOT usable in a 'gaming since' series."),
    "CCP-962300": (
        "unspecified",
        "RULED 2026-08-06 (session 3), resolving §7.6 of the build log. The stated "
        "1981-12-31 CANNOT mark Indigo Sky Casino's opening and the event it "
        "does mark is not established. Two independent facts settle the "
        "first half. (1) The Indian Gaming Dataset - the per-event-sourced "
        "opening history in data/raw/external/gaming/directory_core - records "
        "Indigo Sky Casino at 70220 US-60, Wyandotte OK with a GRAND OPENING "
        "IN 2012, citing a KOAM News report on Bordertown Casino's closure. "
        "(2) This row's Casino City address is 130 North Oneida Street, which "
        "is not Indigo Sky's address at all: the same dataset places "
        "Bordertown Casino & Arena, the Eastern Shawnee property Indigo Sky "
        "REPLACED, at 129 Oneida St, with a 2005 grand opening and a 2013 "
        "closing. So this row carries a successor property's name over a "
        "predecessor's address and a date earlier than either - a vendor "
        "carrying a LINEAGE date on a rebuilt property, which is a third "
        "route to the same property-versus-gaming conflation §2 documents. "
        "The date is retained unmodified because it is the source value and "
        "no source read here states what 1981 marks. CONSEQUENCE FOR §2: this "
        "row must NOT be counted among the verified pre-IGRA halls."),
    "CCP-336100": (
        "permanent_facility_opened",
        "RULED 2026-08-06, RE-STATED IN CODE 2026-08-06 (session 3) so that re-running "
        "this script cannot silently drop it - the ruling had been applied "
        "directly to the CSV, and this loop clears `open_date_event` on every "
        "row before recomputing it, so the next rebuild would have reverted "
        "it to `unspecified`. TWO OPENINGS, BOTH REAL. The Kansas State "
        "Gaming Agency's history page states: 'The Iowa Tribe opened a "
        "temporary gaming facility on May 20, 1998. On December 15, 1998, "
        "their permanent casino, Casino White Cloud, was opened...'. "
        "`open_date` carries the PERMANENT building, 1998-12-15; the temporary "
        "facility is recorded separately in `interim_open_date` rather than "
        "resolved by a house rule, because 'when did gaming start here' and "
        "'when did this building open' are different questions and this file "
        "answers both. http://www.kansas.gov/ksga/History.htm"),
    "VP-0051": (
        "property_opened",
        "RULED 2026-08-06 on the row's own evidence: the date is 'the "
        "gaming-floor opening of the NEW Soboba Casino Resort', which "
        "'replaced the original 1995 Soboba Casino on a different site, which "
        "was already operating by 2000-10-17 per an archived soboba.com "
        "capture.' Gaming by this operator began in 1995. Usable as the new "
        "resort's opening; NOT usable in a 'gaming since' series."),
}


# Evidence that does not settle WHICH event a date marks, but that does
# independently establish the facility was operating by some date. It is
# appended to open_date_event_basis so the subscriber can see how far the
# verification actually got, rather than reading a bare "not established".
CORROBORATION = {
    # Seneca Gaming and Entertainment - Irving. Casino City states
    # 1970-12-31 (its year placeholder -> year precision, 1970). No source
    # located states an opening date. What IS established, from a primary
    # filing: the Irving Class II hall was operating through the fiscal year
    # ended 2003-09-30 and was material ($25.5M net revenue). The Nation's own
    # site (senecagames.com, fetched 2026-08-06) still lists Irving, Salamanca
    # and Oil Spring, and states no opening date anywhere on the page.
    "CCP-43500": (
        " CORROBORATION (does not date the opening): Seneca Gaming "
        "Corporation's SEC Form S-4 filed 2004-07-23 (CIK 0001296785) states "
        "the Nation 'through its wholly owned business enterprise, Seneca "
        "Gaming & Entertainment, operates a Class II gaming facility located "
        "on the Nation's Territory in Irving, New York' and that 'For the "
        "fiscal year ended September 30, 2003, the Irving Class II facility "
        "generated $25.5 million in net revenue'. That proves the hall was "
        "operating by 2003-09-30 and says nothing about when it opened. "
        "https://www.sec.gov/Archives/edgar/data/1296785/000104746904024134/"
        "a2140167zs-4.htm"),
}


# ------------------------------------------------- land-decision bounding ---
# A BIA gaming-land decision bounds an opening FROM BELOW only for the parcel
# it decides. Joining on (tribe, state) does not establish that, and the data
# proves how badly it fails:
#
#   Muckleshoot Casino Resort <- "Muckleshoot Indian Tribe Decision" 2008-12-12
#       The casino has operated since the 1990s. A (tribe, state) bound would
#       have asserted it could not have opened before 2008. Flatly wrong.
#   Pearl River Resort (both properties) <- a 2008 DISAPPROVAL
#       A disapproval bounds nothing; no land was taken into trust.
#   Cherokee Nation: 15 facility rows against 5 decisions, no site key.
#
# So bounds are applied only where the decision TITLE names the facility's own
# site AND the decision is a LAND ACQUISITION (which the land could not have
# hosted gaming before), hand-checked one at a time.
#
# Exactly one of the thirteen (tribe, state) candidates survives. The two
# Cherokee West Siloam Springs rows were REJECTED even though the decision
# title names their site: 'Cherokee Nation Siloam Spring Decision' is an
# Oklahoma within-former-reservation-boundaries GAMING ELIGIBILITY
# determination, not a land acquisition, and a Class II bingo operation could
# lawfully have preceded it on the same ground. A lower bound that a bingo hall
# would falsify is not a bound.
LAND_DECISION_BOUNDS = {
    "VP-0401": ("GLD-OR-coquille-indian-tribe-19940622",
                "The Mill Casino sits on the North Bend waterfront parcel; the "
                "BIA decision titled 'Coquille Indian Tribe North Bend "
                "Waterfront Decision' (Approved, 1994-06-22) acquires that "
                "specific site, which the tribe therefore did not hold before."),
}


def resolve_decision_dates(decisions):
    """decision_id -> (date, status, title). ids in LAND_DECISION_BOUNDS are
    written from the title, so fall back to a (state, tribe, date) lookup."""
    by_date = {}
    for r in decisions:
        by_date[(r.get("state_abbr", ""), r.get("decision_date", ""))] = r
    return by_date


def main():
    print("=== Cedar Press 23f: gaming temporal build ===\n")

    # ---------------------------------------------------------- metrics ---
    print("[1] gaming_facility_metrics.csv - as_of_date")
    met, mf = load("gaming_facility_metrics.csv")
    add_cols(mf, ["as_of_date", "as_of_date_precision", "as_of_date_basis"])
    n_d = n_p = n_none = 0
    for r in met:
        od = (r.get("observation_date") or "").strip()
        op = (r.get("observation_period") or "").strip()
        if od:
            r["as_of_date"] = od
            r["as_of_date_precision"] = "day"
            r["as_of_date_basis"] = "source observation_date"
            n_d += 1
        elif re.match(r"^\d{4}$", op):
            r["as_of_date"] = f"{op}-01-01"
            r["as_of_date_precision"] = "year"
            r["as_of_date_basis"] = (
                "derived from observation_period; the source states a fiscal "
                "year only, so month and day are not claimed")
            n_p += 1
        else:
            r["as_of_date"] = ""
            r["as_of_date_precision"] = ""
            r["as_of_date_basis"] = "absent - no observation_date or period"
            n_none += 1
    print(f"    from observation_date : {n_d:,}")
    print(f"    from observation_period: {n_p:,}")
    print(f"    still undated          : {n_none:,}")
    save("gaming_facility_metrics.csv", met, mf)

    # earliest date at which each facility was OBSERVED OPEN. Only
    # observation_status == 'current' qualifies: 'proposed' and 'approved' are
    # Casino City's Planned / Under Construction rows and a planned casino is
    # not an open one.
    observed_open = {}
    for r in met:
        fid = (r.get("facility_id") or "").strip()
        if not fid or r.get("observation_status") != "current":
            continue
        if r.get("source_status_literal") not in ("Open", "Temporarily Closed", ""):
            continue
        d = r["as_of_date"]
        if d and (fid not in observed_open or d < observed_open[fid]):
            observed_open[fid] = d

    # ------------------------------------------------------- facilities ---
    print("\n[2] gaming_facilities.csv - lifespan columns")
    fac, ff = load("gaming_facilities.csv")
    global OBS_DATE_COLS
    OBS_DATE_COLS = [c for c in ff if c.endswith("_observed_date")]
    decisions, _ = load("gaming_land_decisions.csv")
    dec_by_state_date = resolve_decision_dates(decisions)

    research = {}
    rfiles = research_files()
    if rfiles:
        for p in rfiles:
            n0 = len(research)
            with open(p, encoding="utf-8-sig", newline="") as fh:
                for r in csv.DictReader(fh):
                    fid = (r.get("facility_id") or "").strip()
                    if fid:
                        r["_evidence_file"] = p.name
                        research[fid] = r
            print(f"    hand-research {p.name}: "
                  f"{len(research) - n0} new facilities")
        print(f"    hand-research total: {len(research)} facilities")
    else:
        print(f"    hand-research files ABSENT ({RESEARCH_GLOB})")

    add_cols(ff, [
        "open_date_class", "open_date_precision",
        "open_date_not_before", "open_date_not_after",
        "open_date_evidence", "open_date_evidence_url",
        "open_date_evidence_quote", "open_date_absent_reason",
        "close_date_class", "close_date_precision",
        "close_date_not_before", "close_date_not_after",
        "observed_open_by", "open_date_postdates_observation",
        "close_date_precedes_open_date",
        "open_date_event", "open_date_event_basis",
        "open_date_predates_tribal_gaming_era",
        "duplicate_of_facility_id", "temporal_build_date",
    ])

    counts = {"exact": 0, "bounded": 0, "absent": 0}
    reasons = {}
    for r in fac:
        # CLEARED, not setdefault. These are all derived, and on a re-run over
        # an already-built file a stale value would be sticky: `if not
        # r["open_date_class"]` would read the PREVIOUS run's answer and skip
        # every later evidence source, so newly-arrived research could never
        # change a row already marked `absent`. That bug cost four bounds
        # before it was caught.
        for c in ("open_date_class", "open_date_precision", "open_date_not_before",
                  "open_date_not_after", "open_date_evidence",
                  "open_date_evidence_url", "open_date_evidence_quote",
                  "open_date_absent_reason", "close_date_class",
                  "close_date_precision", "close_date_not_before",
                  "close_date_not_after"):
            r[c] = ""
        r["temporal_build_date"] = TODAY

        # ---- close date first (independent of the open-date logic)
        cprec, cnb, cna, cnote = interpret(r.get("close_date"),
                                           r.get("close_date_basis"))
        if cprec:
            r["close_date_class"] = "exact"
            r["close_date_precision"] = cprec
            r["close_date_not_before"] = cnb
            r["close_date_not_after"] = cna
        else:
            r["close_date_class"] = "absent"

        # ---- open date
        fid = r["facility_id"]
        name = r.get("facility_name") or ""
        raw = (r.get("open_date") or "").strip()

        # The hand-research file is consulted FIRST, before the row's own
        # open_date, and that ordering is load-bearing. Run 1 writes the
        # researched date INTO open_date; if run 2 then took the "row already
        # has a date" path it would never re-read the research file, and the
        # evidence quote and note - which the top of this loop clears - would
        # be silently dropped on every rebuild. That bug turned four
        # `property_opened` rows into `not_gaming_commencement` on the second
        # run, because the pre-1979 rule could no longer see the quote.
        if fid in research and (research[fid].get("date_basis") or "").strip() \
                in ("exact", "bounded"):
            pass                        # handled in the research block below
        elif raw:
            prec, nb, na, note = interpret(raw, r.get("open_date_basis"))
            if prec == "decade":
                # a decade is a bound, not a stated date
                r["open_date_class"] = "bounded"
            elif prec:
                r["open_date_class"] = "exact"
            else:
                r["open_date_class"] = "absent"
                r["open_date_absent_reason"] = note or "unparseable source value"
            r["open_date_precision"] = prec or ""
            r["open_date_not_before"] = nb
            r["open_date_not_after"] = na
            r["open_date_evidence"] = note or (r.get("open_date_basis") or "")
            r["open_date_evidence_url"] = r.get("open_date_source_url", "")
            counts[r["open_date_class"]] += 1
            if r["open_date_class"] == "absent":
                reasons[r["open_date_absent_reason"]] = \
                    reasons.get(r["open_date_absent_reason"], 0) + 1
            continue

        # ---- rows that are not datable facilities at all
        #
        # Ordering note: the three ruled tables bind BEFORE the name rules and
        # before the hand-research and observed-operating branches, because a
        # row ruled to be a duplicate, a non-facility or an unresolved
        # identity must not pick up a bound that would move it out of `absent`
        # and back into the population a subscriber reads as datable casinos.
        if fid in RULED_NOT_FACILITY:
            r["open_date_class"] = "absent"
            r["open_date_absent_reason"] = RULED_NOT_FACILITY[fid]
        elif fid in RULED_DUPLICATE:
            twin, why = RULED_DUPLICATE[fid]
            r["open_date_class"] = "absent"
            r["open_date_absent_reason"] = (
                f"duplicate row - RULED 2026-08-06 (session 3) to be the same property as "
                f"{twin}, which carries the date. See "
                f"`duplicate_of_facility_id`. {why}")
        elif fid in RULED_GAMING_UNCERTAIN:
            r["open_date_class"] = "absent"
            r["open_date_absent_reason"] = RULED_GAMING_UNCERTAIN[fid]
        elif NO_FACILITY.search(name):
            r["open_date_class"] = "absent"
            r["open_date_absent_reason"] = (
                "not a gaming facility - this row comes from the "
                "votingpatterns tribe roster and its facility_name records "
                "that the tribe operates no casino; there is no opening to date")
        elif CROSS_REF.search(name):
            r["open_date_class"] = "absent"
            r["open_date_absent_reason"] = (
                "cross-reference stub - facility_name points at another row "
                "for the same property; not a distinct facility")

        # ---- hand-researched
        elif fid in research:
            rr = research[fid]
            basis = (rr.get("date_basis") or "").strip()
            if basis == "exact":
                od = (rr.get("open_date") or "").strip()
                prec = (rr.get("open_date_precision") or "day").strip()
                r["open_date"] = od
                r["open_date_basis"] = (
                    f"hand-researched {TODAY}; {prec}-precision date stated by "
                    f"the cited source")
                r["open_date_source_url"] = rr.get("source_url", "")
                r["open_date_class"] = "exact"
                r["open_date_precision"] = prec
                y = int(od[:4])
                if prec == "year":
                    r["open_date_not_before"], r["open_date_not_after"] = \
                        f"{y}-01-01", f"{y}-12-31"
                elif prec == "month":
                    mo = int(od[5:7])
                    r["open_date_not_before"], r["open_date_not_after"] = \
                        f"{y}-{mo:02d}-01", month_end(y, mo)
                else:
                    r["open_date_not_before"] = r["open_date_not_after"] = od
                r["open_date_evidence"] = rr.get("note", "")
                r["open_date_evidence_url"] = rr.get("source_url", "")
                r["open_date_evidence_quote"] = rr.get("source_quote", "")
            elif basis == "bounded":
                r["open_date_class"] = "bounded"
                r["open_date_not_before"] = rr.get("open_date_not_before", "")
                r["open_date_not_after"] = rr.get("open_date_not_after", "")
                r["open_date_evidence"] = (
                    "hand-researched bound; no source states an opening date. "
                    + (rr.get("note") or ""))
                r["open_date_evidence_url"] = rr.get("source_url", "")
                r["open_date_evidence_quote"] = rr.get("source_quote", "")

        # ---- observed operating in the capacity panel
        # Prefer the metrics file; fall back to the per-metric observed dates
        # carried on the facility row itself, which a handful of properties
        # have without a matching metrics row.
        seen = observed_open.get(fid, "")
        if not seen and r.get("property_status_literal") in ("Open", "Temporarily Closed"):
            row_dates = [r[c].strip() for c in OBS_DATE_COLS
                         if r.get(c, "").strip()]
            if row_dates:
                seen = min(row_dates)
        if not r["open_date_class"] and seen:
            r["open_date_class"] = "bounded"
            r["open_date_not_after"] = seen
            r["open_date_evidence"] = (
                "Casino City Press observed this property with status Open on "
                f"{seen}, so it was operating by then. No source located "
                "states when it opened. The observation date is NOT an "
                "opening date.")

        # ---- land decision lower bound, hand-checked site match only
        if fid in LAND_DECISION_BOUNDS:
            did, why = LAND_DECISION_BOUNDS[fid]
            ddate = did.rsplit("-", 1)[-1]
            iso = f"{ddate[:4]}-{ddate[4:6]}-{ddate[6:8]}"
            if not r["open_date_not_before"]:
                r["open_date_not_before"] = iso
                if not r["open_date_class"]:
                    r["open_date_class"] = "bounded"
                r["open_date_evidence"] = (
                    (r["open_date_evidence"] + " ") if r["open_date_evidence"]
                    else "") + (
                    f"Lower bound from BIA gaming-land decision {did} "
                    f"({iso}): {why} A decision date is not an opening date - "
                    "the lag between them is variable and is not claimed here.")

        if not r["open_date_class"]:
            r["open_date_class"] = "absent"
            r["open_date_absent_reason"] = (
                "no source located - see docs/GAMING_TEMPORAL_BUILD_LOG.md for "
                "what was searched")

        counts[r["open_date_class"]] += 1
        if r["open_date_class"] == "absent":
            reasons[r["open_date_absent_reason"][:60]] = \
                reasons.get(r["open_date_absent_reason"][:60], 0) + 1

    # ---- internal consistency, flagged and never silently corrected -------
    # `open_date` is not reliably the ORIGINAL opening. On a set of properties
    # it postdates an observation of the same property already operating,
    # which means it dates the CURRENT BUILDING or a re-opening. Anyone
    # charting "casino openings by year" off this column is partly charting
    # rebuilds, so the fact is carried on the row rather than left in a doc.
    n_post = n_rev = n_pre = 0
    events = {}
    for r in fac:
        fid = r["facility_id"]
        seen = observed_open.get(fid, "")
        r["observed_open_by"] = seen
        # Points at the row that carries this property's date. Published as a
        # column rather than resolved by deleting the row, because the
        # never-delete rule holds and because a subscriber counting casinos
        # needs to be able to see WHICH rows to collapse and why.
        r["duplicate_of_facility_id"] = RULED_DUPLICATE.get(fid, ("",))[0]
        r["open_date_postdates_observation"] = ""
        r["close_date_precedes_open_date"] = ""
        nb = r["open_date_not_before"]
        if r["open_date_class"] == "exact" and seen and nb and nb > seen:
            r["open_date_postdates_observation"] = "1"
            n_post += 1
        if nb and r["close_date_not_after"] and r["close_date_not_after"] < nb:
            r["close_date_precedes_open_date"] = "1"
            n_rev += 1

        # ---- which event does the date mark?
        r["open_date_event"] = ""
        r["open_date_event_basis"] = ""
        r["open_date_predates_tribal_gaming_era"] = ""
        # Only a STATED date can name the wrong event. A row whose only
        # temporal evidence is a bound has no date whose meaning could be
        # misread, so it is left blank rather than labelled `unspecified`.
        if not (r.get("open_date") or "").strip() or not nb:
            continue
        if int(nb[:4]) < TRIBAL_GAMING_ERA_FLOOR:
            r["open_date_predates_tribal_gaming_era"] = "1"
            n_pre += 1
        basis = r.get("open_date_basis") or ""
        if fid in RULED_EVENT:
            # Binds ahead of everything, including the hand-researched branch,
            # because it is a ruling ON that branch's output.
            r["open_date_event"], r["open_date_event_basis"] = RULED_EVENT[fid]
        elif fid in VERIFIED_EVENT:
            ev, why, url, quote = VERIFIED_EVENT[fid]
            r["open_date_event"] = ev
            r["open_date_event_basis"] = why
            if not r["open_date_evidence_url"]:
                r["open_date_evidence_url"] = url
            if not r["open_date_evidence_quote"]:
                r["open_date_evidence_quote"] = quote
        elif "Indian Gaming Dataset" in basis:
            r["open_date_event"] = "gaming_commenced"
            r["open_date_event_basis"] = (
                "The Indian Gaming Dataset codes dated GAMING opening events "
                "for gaming properties and carries a per-event source URL, so "
                "the event is the source's own subject. Not independently "
                "re-verified here.")
        # A stated date before the tribal gaming era CANNOT mark gaming
        # commencement, whatever the researcher's source called it. This rule
        # binds ahead of every source-based assignment and it caught two real
        # errors on its first run: Pala Mesa Resort ("Since opening in 1961,
        # Pala Mesa Resort has been dedicated to ... golfing") and Singing
        # Hills at Sycuan (a 1956 golf course opening). Both had been about to
        # publish as `gaming_commenced` because the underlying source honestly
        # described an opening - just not a casino's.
        elif r["open_date_predates_tribal_gaming_era"] == "1":
            # Knowing a date is NOT a gaming date is not the same as knowing
            # what it IS. Only a row with a cited source describing an opening
            # earns `property_opened`; the rest get the weaker, true claim.
            if r["open_date_evidence_quote"]:
                r["open_date_event"] = "property_opened"
                r["open_date_event_basis"] = (
                    f"The stated date precedes {TRIBAL_GAMING_ERA_FLOOR}, the "
                    "first documented year of high-stakes tribal gaming, so it "
                    "cannot mark gaming commencement. The cited source "
                    "describes the opening of the PROPERTY - a golf course, "
                    "resort or lodge that later hosted gaming. Read "
                    "`open_date_evidence_quote`.")
            else:
                # OVER-CLAIM CORRECTED 2026-08-06. This branch used to publish
                # `not_gaming_commencement` on the strength of the 1979 rule
                # alone. That asserts a negative the rule cannot carry: 1979 is
                # the first year of HIGH-STAKES tribal bingo (the Butterworth
                # hall), not the first year of tribal gaming of any kind, and
                # small charitable bingo halls predate it. `not_gaming_
                # commencement` is now reserved for rows with actual
                # verification (VERIFIED_EVENT above - Crosby Lodge) or a
                # source quote describing a property opening (the branch
                # above). A rule-only row gets the true, weaker claim:
                # unspecified, plus the flag that says why to look twice.
                # The flag column open_date_predates_tribal_gaming_era already
                # carries the whole signal, and it is the documented detector.
                r["open_date_event"] = "unspecified"
                r["open_date_event_basis"] = (
                    f"NOT INDEPENDENTLY VERIFIED. The stated date precedes "
                    f"{TRIBAL_GAMING_ERA_FLOOR}, the first documented year of "
                    "high-stakes tribal gaming, so it is unlikely - but NOT "
                    "proven - to mark gaming commencement; small tribal bingo "
                    "predates that year. No source states which event this "
                    "date marks. Treat the date as unusable for a "
                    "'gaming since' series and see "
                    "`open_date_predates_tribal_gaming_era`."
                    + CORROBORATION.get(fid, ""))
        elif "hand-researched" in basis:
            # The researcher's own disclosure decides. Where the source dates a
            # replacement building or a rebranding rather than the first
            # operation, gaming did NOT commence on that date - the building
            # opened on it, which is a different event and the exact confusion
            # `open_date_event` exists to prevent.
            ev_txt = (r["open_date_evidence"] or "").lower()
            # NEGATION GUARD, added 2026-08-06 after the rule misfired twice in
            # one batch. Researchers write about a rebuild in order to say the
            # date is NOT the rebuild - "The Feb 1987 date is the ORIGINAL
            # opening as a high-stakes bingo hall, not the 2012
            # renovation/rebranding" - and a substring scan reads the
            # disclaimer as the claim, flipping a correct
            # gaming-commencement row to `property_opened`.
            #
            # This is the mirror of the false POSITIVE problem documented in
            # RULED_EVENT: prose scanning is unreliable in BOTH directions.
            # The real fix is for the researcher to state the event in its own
            # column rather than have it inferred from a note; until the
            # evidence schema carries that field, the guard below stops the
            # commonest misfire and the rest are ruled one at a time.
            claims_original = any(k in ev_txt for k in (
                "original opening", "is the original", "the original opening",
                "not the 2012", "not a later", "not the later",
                "original gaming commencement", "not the rebuild",
                "not the hotel", "not a rebrand"))
            if not claims_original and any(
                    k in ev_txt for k in ("replacement building", "rebrand",
                                          "relocat", "new building",
                                          "successor")):
                r["open_date_event"] = "property_opened"
                r["open_date_event_basis"] = (
                    "Researched, and the source dates a REPLACEMENT BUILDING "
                    "or a rebranding, not the first operation on this site. "
                    "Gaming here began earlier by an amount the source does "
                    "not state. Read `open_date_evidence`.")
            else:
                r["open_date_event"] = "gaming_commenced"
                r["open_date_event_basis"] = (
                    "Researched against a source describing the casino opening "
                    "to the public.")
        else:
            r["open_date_event"] = "unspecified"
            r["open_date_event_basis"] = (
                "The Casino City Tribal Property List publishes an 'Open Date' "
                "for each gaming property but does not state whether it marks "
                "the date gaming commenced or the date the property opened. "
                "Not inferred here.")
        events[r["open_date_event"]] = events.get(r["open_date_event"], 0) + 1

    print(f"    exact  : {counts['exact']}")
    print(f"    bounded: {counts['bounded']}")
    print(f"    absent : {counts['absent']}")
    for k, v in sorted(reasons.items(), key=lambda x: -x[1]):
        print(f"       {v:4d}  {k}")
    print(f"    FLAG open_date postdates an observation of the property "
          f"already open: {n_post}")
    print(f"    FLAG close_date precedes open_date               : {n_rev}")
    print(f"    FLAG open_date predates {TRIBAL_GAMING_ERA_FLOOR} "
          f"(pre-tribal-gaming era): {n_pre}")
    print("    open_date_event:")
    for k, v in sorted(events.items(), key=lambda x: -x[1]):
        print(f"       {v:4d}  {k}")
    print(f"    RULED duplicate rows (date lives on a twin)      : "
          f"{sum(1 for r in fac if r['duplicate_of_facility_id'])}")

    # ---- guard regression check ------------------------------------------
    # §2 of the build log: the rebuild keyword rule misfires in BOTH
    # directions, and the negation guard exists because researchers write
    # about a rebuild in order to RULE IT OUT. Print what the guard is doing
    # so a future edit to either keyword list shows up as a diff rather than
    # as a silent re-labelling of correct gaming-commencement dates.
    n_flip = n_saved = 0
    for r in fac:
        if "hand-researched" not in (r.get("open_date_basis") or ""):
            continue
        if r["facility_id"] in RULED_EVENT or r["facility_id"] in VERIFIED_EVENT:
            continue
        t = (r["open_date_evidence"] or "").lower()
        orig = any(k in t for k in (
            "original opening", "is the original", "the original opening",
            "not the 2012", "not a later", "not the later",
            "original gaming commencement", "not the rebuild",
            "not the hotel", "not a rebrand"))
        kw = any(k in t for k in ("replacement building", "rebrand", "relocat",
                                  "new building", "successor"))
        if kw and orig:
            n_saved += 1
        elif kw:
            n_flip += 1
    print(f"    GUARD rebuild-keyword flips to property_opened   : {n_flip}")
    print(f"    GUARD negation guard suppressed a flip           : {n_saved}")
    save("gaming_facilities.csv", fac, ff)

    # ------------------------------------------- projections doc dates ---
    print("\n[3] gaming_projections.csv - source_document_date")
    proj, pf = load("gaming_projections.csv")
    pfac, _ = load("gaming_project_facilities.csv")
    ea_date = {}
    for r in pfac:
        d = (r.get("document_date") or "").strip()
        pid = r.get("project_id", "")
        if d and (pid not in ea_date or d > ea_date[pid]):
            ea_date[pid] = d
    MONTHS = {m: i for i, m in enumerate(
        ["January", "February", "March", "April", "May", "June", "July",
         "August", "September", "October", "November", "December"], 1)}
    MRE = re.compile(r"\b(" + "|".join(MONTHS) + r")\s+(\d{4})\b")
    add_cols(pf, ["source_document_date", "source_document_date_basis"])
    n_stated = n_bound = 0
    for r in proj:
        m = MRE.search(r.get("source_document") or "")
        if m:
            r["source_document_date"] = f"{int(m.group(2)):04d}-{MONTHS[m.group(1)]:02d}"
            r["source_document_date_basis"] = (
                "exact - the source_document title states this month and year")
            n_stated += 1
        elif ea_date.get(r.get("project_id", "")):
            r["source_document_date"] = ea_date[r["project_id"]]
            r["source_document_date_basis"] = (
                "bounded - the appendix states no date of its own; it cannot "
                "postdate the environmental assessment it is filed under, so "
                "this is an upper bound, not the document's own date")
            n_bound += 1
        else:
            r["source_document_date"] = ""
            r["source_document_date_basis"] = "absent"
    print(f"    stated in document title: {n_stated}")
    print(f"    bounded by parent EA    : {n_bound}")
    save("gaming_projections.csv", proj, pf)

    print("\ndone.")


if __name__ == "__main__":
    main()
