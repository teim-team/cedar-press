#!/usr/bin/env python3
"""
96_extract_sec_property_capacity.py -- Cedar Press.

LAYER 5 of the official capacity build, which was specified in
`code/92_build_gaming_capacity_official.py` and never populated: audited filing
evidence. `agent_bond_sec_2026-08-06.csv` was never written -- the agent that
was to write it died -- but the DOCUMENTS survived on disk:

    data/raw/external/gaming_official/sec_filings/txt/
      27 Mohegan Tribal Gaming Authority 10-Ks   FY1996 - FY2022
      11 Seneca Gaming Corporation 10-K / S-4    FY2004 - FY2009

These are the strongest evidence class in this build. A 10-K is signed under
Section 302 by named officers; a state regulator's roster is not. They are also
the ONLY per-property, per-year device series available for Mohegan Sun and the
Seneca properties, because the vendor panel holds zero Connecticut rows and the
Connecticut regulator publishes a weighted MONTHLY AVERAGE rather than a count.

THE FAILURE THIS SCRIPT IS BUILT AROUND
---------------------------------------
A gaming 10-K describes THREE kinds of casino floor and they read identically:

  1. the issuer's own property                       -> publishable
  2. a COMPETITOR's property, in Item 1 Competition  -> NOT the issuer's, and
     not audited either; the issuer is repeating trade press about a rival
  3. a PLANNED expansion                             -> a projection

Mohegan's FY2005 10-K contains, within a few hundred characters of each other,
"approximately 3,800 slot machines" (its own Mohegan Sun), "Turning Stone
Casino Resort currently has approximately 2,100 VLTs ... and 350 hotel rooms"
(the Oneida Nation's, a competitor), and "projected to have 220 hotel rooms"
(Seneca's unbuilt Salamanca facility). Pattern-matching numbers near the word
"slot machines" pulls all three and attributes all three to Mohegan. That is
AGENTS.md's containment defect with an SEC cover page on it.

So the guards are:
  * an issuer-owned property name must appear IN THE WINDOW, and exactly one;
  * ANY competitor name in the window rejects the window outright and stages it;
  * forward-looking language ("will", "projected", "expected", "plans to",
    "upon completion", "would") rejects the window as a projection, staged, per
    `cedar_domain.may_promote`: PROJECTED never becomes an ACTIVE floor count;
  * bullet-list fragments with no property name in the window are staged, never
    assigned to the nearest heading.

Everything rejected lands in the same evidence CSV with `exclusion_flag` set and
a reason, so the refusals are auditable rather than invisible.

WRITES
  data/raw/external/gaming_official/agent_bond_sec_2026-08-07.csv
  data/raw/external/gaming_official/agent_bond_sec_rejected_2026-08-07.csv
"""
import csv, re, sys, importlib.util
from pathlib import Path

CEDAR = Path(r"C:\Users\esm247\Desktop\Cedar Press")
RAW = CEDAR / "data" / "raw" / "external" / "gaming_official"
TXT = RAW / "sec_filings" / "txt"
TODAY = "2026-08-07"

# --- the domain vocabulary, imported not re-invented ------------------------
_spec = importlib.util.spec_from_file_location(
    "cedar_domain", str(CEDAR / "code" / "cedar_domain.py"))
_cd = importlib.util.module_from_spec(_spec)
sys.modules["cedar_domain"] = _cd
_spec.loader.exec_module(_cd)
MeasurementType, may_promote = _cd.MeasurementType, _cd.may_promote

assert not may_promote(MeasurementType.PROJECTED, MeasurementType.ACTIVE_FLOOR_COUNT)

ISSUERS = {
    "mohegan": dict(
        tribe="Mohegan Tribe of Indians of Connecticut",
        authority="Mohegan Tribal Gaming Authority (SEC Form 10-K)",
        cik="1005276",
        # (regex, published property name, state)
        props=[
            (r"Mohegan Sun Pocono|Pocono Downs", "Mohegan Sun Pocono", "PA"),
            (r"Mohegan Sun(?! Pocono)", "Mohegan Sun", "CT"),
        ],
        competitors=[
            "Foxwoods", "Turning Stone", "Oneida", "Empire City", "Yonkers",
            "Aqueduct", "Saratoga", "Batavia", "Monticello", "Twin River",
            "Newport Grand", "Lincoln Park", "Seneca", "Niagara Fallsview",
            "Casino Niagara", "Bethlehem", "Sands", "Parx", "Philadelphia Park",
            "Presque Isle", "Meadows", "Harrah's Chester", "Mount Airy",
            "Penn National", "Atlantic City", "Borgata", "Encore Boston",
            "MGM Springfield", "Plainridge", "Wynn", "Rivers", "del Lago",
            "Tioga Downs", "Vernon Downs", "Resorts World", "Hollywood Casino",
            "Valley Forge", "Lady Luck", "Nemacolin", "Live! Casino",
        ],
    ),
    "seneca": dict(
        tribe="Seneca Nation of Indians",
        authority="Seneca Gaming Corporation (SEC Form 10-K)",
        cik="1300734",
        props=[
            (r"Seneca Niagara", "Seneca Niagara Casino & Hotel", "NY"),
            (r"Seneca Allegany", "Seneca Allegany Casino & Hotel", "NY"),
            (r"Seneca Buffalo Creek|Buffalo Creek Casino", "Seneca Buffalo Creek Casino", "NY"),
            (r"Seneca Gaming and Entertainment|Irving|Salamanca (?:bingo|gaming)",
             "Seneca Gaming and Entertainment", "NY"),
        ],
        competitors=[
            "Mohegan", "Foxwoods", "Turning Stone", "Oneida", "Empire City",
            "Yonkers", "Aqueduct", "Saratoga", "Batavia", "Monticello",
            "Finger Lakes", "Vernon Downs", "Tioga Downs", "Casino Niagara",
            "Niagara Fallsview", "Fallsview", "Presque Isle", "Erie",
            "Mountaineer", "Wheeling", "Chautauqua", "Fort Erie",
            "Woodbine", "Georgian Downs", "Casino Rama", "Point Place",
        ],
    ),
}

# `Salamanca` is BOTH a Seneca Allegany location word and, in the Mohegan
# filings, a competitor reference. Handled by the per-issuer competitor list.

NUM = r"(?:approximately\s+|about\s+|over\s+|nearly\s+|more than\s+|at least\s+)?" \
      r"([\d][\d,]{1,6})"
METRICS = [
    (re.compile(NUM + r"\s+slot machines", re.I), "gaming_machines", "machines"),
    (re.compile(NUM + r"\s+(?:gaming machines|gaming devices)", re.I),
     "gaming_machines", "machines"),
    (re.compile(NUM + r"\s+(?:VLTs|video lottery terminals)", re.I),
     "gaming_machines", "machines"),
    (re.compile(NUM + r"\s+table games", re.I), "table_games", "tables"),
    (re.compile(NUM + r"\s+(?:hotel rooms|guest rooms)", re.I), "hotel_rooms", "rooms"),
    (re.compile(NUM + r"\s+(?:poker tables|tables for live poker)", re.I),
     "poker_tables", "tables"),
    (re.compile(NUM + r"\s+square feet of (?:gaming|casino)", re.I),
     "gaming_square_feet", "square_feet"),
    (re.compile(NUM + r"\s+parking spaces", re.I), "parking_spaces", "spaces"),
]

# Forward-looking. `cedar_domain.may_promote` refuses PROJECTED -> ACTIVE, so
# these windows are never emitted as counts.
FUTURE = re.compile(
    r"\b(will|would|projected|expected to|expects to|anticipat|plans? to|planned|"
    r"upon completion|when completed|scheduled to|intend|plan for|proposed|"
    r"under construction|estimate[sd]? that)\b", re.I)
# Past-tense/other-period phrasing that makes the date ambiguous.
PAST = re.compile(r"\b(prior to|formerly|previously|until|in fiscal (?:19|20)\d\d)\b", re.I)

WINDOW = 320

# A STATUTORY CEILING reads exactly like a floor count. MEASURED: Mohegan's
# FY2004 10-K says "An aggregate of 61,000 slot machines may be permitted for up
# to 14 locations throughout Pennsylvania" -- a statewide licence pool created by
# the 2004 Pennsylvania gaming act, which the first run published as Mohegan Sun
# Pocono's device count and which the plausibility gate then had to catch.
# `cedar_domain.may_promote` refuses AUTHORIZED_MAXIMUM -> ACTIVE_FLOOR_COUNT, so
# the window is refused here rather than relabelled downstream.
# Deliberately NARROW. A first version also rejected on "legislation",
# "licensees", "statewide" and "limited to" -- words that appear in the
# ordinary legal prose surrounding a real count -- and it cost two genuine
# Seneca Allegany device counts. Only phrases that qualify THE NUMBER ITSELF
# as a ceiling are kept. Measured both ways rather than asserted, which is
# the discipline script 91 had to learn when its tribe-token guard rejected
# 1,359 correct sentences.
AUTHORIZED = re.compile(
    r"(may be permitted|may be authorized|may operate up to"
    r"|permitted to operate|authorized to operate|entitled to operate"
    r"|aggregate of [\d,]+ slot|no more than [\d,]+|up to a maximum of"
    r"|maximum of [\d,]+)", re.I)

# Areas WITHIN Mohegan Sun. A number in a window that names one of these
# belongs to the area, not to the property.
AREA_NAME = re.compile(r"Casino of the (?:Earth|Sky|Wind)", re.I)


def fy_end(fname):
    m = re.search(r"_((?:19|20)\d\d)-(\d\d)-(\d\d)_", fname)
    return f"{m.group(1)}-{m.group(2)}-{m.group(3)}" if m else ""


def main():
    good, bad = [], []
    for f in sorted(TXT.glob("*.txt")):
        key = "mohegan" if f.name.startswith("mohegan") else "seneca"
        iss = ISSUERS[key]
        aod = fy_end(f.name)
        if not aod:
            continue          # S-4s carry no fiscal-year date in the filename
        form = "10-K"
        text = f.read_text(encoding="utf-8", errors="ignore")
        text = re.sub(r"\s+", " ", text)
        url = f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={iss['cik']}&type=10-K"
        seen = set()
        for rx, metric, unit in METRICS:
            for m in rx.finditer(text):
                a, b = max(0, m.start() - WINDOW), min(len(text), m.end() + WINDOW)
                win = text[a:b]
                try:
                    val = float(m.group(1).replace(",", ""))
                except ValueError:
                    continue
                base = dict(
                    tribe_name_as_published=iss["tribe"], state="",
                    metric=metric, value=f"{val:g}", unit=unit,
                    as_of_date=aod, as_of_date_precision="day",
                    period_start="", period_end=aod,
                    source_authority=iss["authority"],
                    source_document_type="sec_form_10k",
                    source_url=url, source_page=f.name,
                    source_quote=win.strip()[:900],
                    fetched_date="2026-08-06")

                comp = [c for c in iss["competitors"] if c.lower() in win.lower()]
                hits = [(pub, stt) for rx2, pub, stt in iss["props"]
                        if re.search(rx2, win, re.I)]
                # de-duplicate the two Mohegan Sun patterns overlapping
                hits = list(dict.fromkeys(hits))

                if comp:
                    bad.append(dict(base, facility_name_as_published="",
                                    exclusion_reason=(
                                        "window names a COMPETITOR property ("
                                        + ", ".join(sorted(set(comp))[:4]) +
                                        "); a rival's floor described in an issuer's "
                                        "10-K is neither the issuer's property nor an "
                                        "audited count of the rival's")))
                    continue
                if FUTURE.search(win):
                    bad.append(dict(base, facility_name_as_published=(hits[0][0] if hits else ""),
                                    exclusion_reason=(
                                        "forward-looking language in the window; this is "
                                        "PROJECTED and cedar_domain.may_promote refuses "
                                        "PROJECTED -> ACTIVE_FLOOR_COUNT")))
                    continue
                if PAST.search(win):
                    bad.append(dict(base, facility_name_as_published=(hits[0][0] if hits else ""),
                                    exclusion_reason="window dates the figure to another period"))
                    continue
                if AUTHORIZED.search(win):
                    bad.append(dict(base,
                                    facility_name_as_published=(hits[0][0] if hits else ""),
                                    exclusion_reason=(
                                        "window describes an AUTHORISED CEILING or a "
                                        "statewide licence pool, not a floor count; "
                                        "cedar_domain.may_promote refuses "
                                        "AUTHORIZED_MAXIMUM -> ACTIVE_FLOOR_COUNT")))
                    continue
                if AREA_NAME.search(win):
                    # An AREA of Mohegan Sun (Casino of the Earth / Sky / Wind)
                    # is named in the window, so this number belongs to that
                    # area and not to the whole property. MEASURED: without this
                    # guard pass 1 published Casino of the Earth's FY2011 3,400
                    # devices AS Mohegan Sun's whole floor, while pass 2 was
                    # correctly deriving 6,325 for the same date -- the file
                    # would have contradicted itself. Pass 2 handles these.
                    bad.append(dict(base, facility_name_as_published="Mohegan Sun",
                                    exclusion_reason=(
                                        "window names an AREA of the property, not the "
                                        "property; handled by the named-area pass")))
                    continue
                if len(hits) != 1:
                    bad.append(dict(base, facility_name_as_published="",
                                    exclusion_reason=(
                                        f"{len(hits)} issuer properties named in the window; "
                                        f"a bullet-list fragment is never assigned to the "
                                        f"nearest heading")))
                    continue
                pub, stt = hits[0]
                k = (pub, metric, aod, val)
                if k in seen:
                    continue
                seen.add(k)
                good.append(dict(base, facility_name_as_published=pub, state=stt))

    # =====================================================================
    # PASS 2 -- Mohegan Sun's NAMED, DATED sub-floors
    # =====================================================================
    # Pass 1 is deliberately blind to Mohegan Sun's own floor in most years,
    # because the 10-K never states a single Mohegan Sun device count. It states
    # THREE, one per named casino inside the one property:
    #
    #   "Mohegan Sun currently operates in an approximately 3.1 million
    #    square-foot facility, which includes the following: Casino of the Earth
    #    As of September 30, 2015, Casino of the Earth offered: ... approximately
    #    2,605 slot machines and 135 table games ..."
    #
    # Casino of the Earth / of the Sky / of the Wind are AREAS OF ONE PROPERTY,
    # not three properties, and the filing dates each one explicitly. So each is
    # emitted as its own observation carrying `applies_to = <area>`, and the
    # property total is emitted only where ALL THREE areas are present in the
    # same filing -- the same rule script 92 applies to Arizona's Class III +
    # Class II derivation. A total built from two of three areas would publish a
    # partial floor as a whole one.
    #
    # Sunrise Square is EXCLUDED from the sum on purpose: the filings describe it
    # as an area inside Casino of the Earth, so adding it double-counts.
    AREAS = ["Casino of the Earth", "Casino of the Sky", "Casino of the Wind"]
    AREA_RX = re.compile(
        r"(" + "|".join(AREAS) + r")\s+(?:offered|offers|featured|features)\b", re.I)
    area_rows = []
    for f in sorted(TXT.glob("mohegan*.txt")):
        aod = fy_end(f.name)
        if not aod:
            continue
        text = re.sub(r"\s+", " ", f.read_text(encoding="utf-8", errors="ignore"))
        marks = [(m.start(), m.group(1)) for m in AREA_RX.finditer(text)]
        if not marks:
            continue
        # first occurrence of each area only; the Item 2 Properties section
        # repeats the same prose later in the filing
        first, byarea = {}, {}
        for pos, nm in marks:
            first.setdefault(nm.title(), pos)
        allpos = sorted(first.values())
        for nm, pos in first.items():
            nxt = next((p for p in allpos if p > pos), pos + 2500)
            seg = text[pos:min(nxt, pos + 2500)]
            if FUTURE.search(seg[:400]):
                continue
            for rx, metric, unit in METRICS:
                m = rx.search(seg)
                if not m:
                    continue
                try:
                    val = float(m.group(1).replace(",", ""))
                except ValueError:
                    continue
                byarea.setdefault(metric, {})[nm] = val
                area_rows.append(dict(
                    facility_name_as_published="Mohegan Sun",
                    tribe_name_as_published=ISSUERS["mohegan"]["tribe"], state="CT",
                    metric=metric, value=f"{val:g}", unit=unit,
                    as_of_date=aod, as_of_date_precision="day",
                    period_start="", period_end=aod,
                    source_authority=ISSUERS["mohegan"]["authority"],
                    source_document_type="sec_form_10k",
                    source_url=("https://www.sec.gov/cgi-bin/browse-edgar?action="
                                "getcompany&CIK=1005276&type=10-K"),
                    source_page=f.name,
                    source_quote=(f"[{nm}] " + seg[:820]).strip(),
                    applies_to=f"area_of_property:{nm}",
                    fetched_date="2026-08-06"))
        # property total, only when all three areas reported the metric
        for metric, d in byarea.items():
            if len(d) != len(AREAS):
                continue
            unit = next(u for _, mm, u in METRICS if mm == metric)
            area_rows.append(dict(
                facility_name_as_published="Mohegan Sun",
                tribe_name_as_published=ISSUERS["mohegan"]["tribe"], state="CT",
                metric=metric, value=f"{sum(d.values()):g}", unit=unit,
                as_of_date=aod, as_of_date_precision="day",
                period_start="", period_end=aod,
                source_authority=ISSUERS["mohegan"]["authority"],
                source_document_type="sec_form_10k",
                source_url=("https://www.sec.gov/cgi-bin/browse-edgar?action="
                            "getcompany&CIK=1005276&type=10-K"),
                source_page=f.name,
                source_quote="; ".join(f"{k} = {v:g}" for k, v in sorted(d.items())),
                applies_to="whole_property_derived_by_adding_the_three_named_areas",
                fetched_date="2026-08-06"))
    good.extend(area_rows)
    print(f"pass 2 (Mohegan Sun named areas): {len(area_rows):,} rows")

    # Where one filing states two different values for the same
    # (property, metric, date), neither is trustworthy on its own -- the two
    # windows are describing different things (e.g. a floor before and after a
    # mid-year expansion). Both are moved to the rejected file, flagged.
    from collections import defaultdict
    by = defaultdict(list)
    for r in good:
        by[(r["facility_name_as_published"], r["metric"], r["as_of_date"],
            r.get("applies_to", ""))].append(r)
    keep, conflict = [], 0
    for k, rs in by.items():
        vals = {r["value"] for r in rs}
        if len(vals) > 1:
            conflict += len(rs)
            for r in rs:
                bad.append(dict(r, exclusion_reason=(
                    "the same filing states " + str(len(vals)) +
                    " different values for this property-metric-date ("
                    + ", ".join(sorted(vals)) + "); not resolved here")))
        else:
            keep.append(rs[0])

    cols = ["facility_name_as_published", "tribe_name_as_published", "state",
            "metric", "value", "unit", "as_of_date", "as_of_date_precision",
            "period_start", "period_end", "source_authority",
            "source_document_type", "source_url", "source_page", "source_quote",
            "applies_to", "fetched_date"]
    with open(RAW / f"agent_bond_sec_{TODAY}.csv", "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(sorted(keep, key=lambda r: (r["facility_name_as_published"],
                                                r["metric"], r["as_of_date"],
                                                r.get("applies_to", ""))))
    with open(RAW / f"agent_bond_sec_rejected_{TODAY}.csv", "w", encoding="utf-8",
              newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols + ["exclusion_reason"],
                           extrasaction="ignore")
        w.writeheader()
        w.writerows(bad)

    from collections import Counter
    print(f"accepted {len(keep):,}   rejected {len(bad):,} "
          f"(of which {conflict} intra-filing conflicts)")
    print("\naccepted by property x metric")
    for k, v in Counter((r["facility_name_as_published"], r["metric"])
                        for r in keep).most_common():
        print(f"  {v:4}  {k[0]:32s} {k[1]}")
    print("\naccepted by applies_to")
    for k, v in Counter(r.get("applies_to", "") or "(whole property, as stated)"
                        for r in keep).most_common():
        print(f"  {v:4}  {k}")
    print("\nrejection reasons")
    for k, v in Counter(r["exclusion_reason"][:70] for r in bad).most_common(12):
        print(f"  {v:4}  {k}")


if __name__ == "__main__":
    main()
