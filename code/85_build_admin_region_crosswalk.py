#!/usr/bin/env python3
"""
Cedar Press - 85: The Federal Indian Program Geography crosswalk.

THE GOVERNING PRINCIPLE
-----------------------
A tribe does not have one universal federal region. It sits, at the same
moment, in a BIA region, a BIA agency, an IHS area, an IHS service unit, an
NIGC region and a HUD ONAP area - and those boundaries do not align.

So there is no `region` column anywhere in this layer. Every assignment names
the PROGRAM it belongs to, because the same word means different ground in
different programs:

  "Phoenix"  BIA   - not a region at all; Phoenix is where the WESTERN
                     Regional Office sits.
            IHS    - the Phoenix Area: central Arizona, northern Nevada,
                     north-western Utah, eleven service units.
            NIGC   - the Phoenix Region, a gaming-enforcement jurisdiction
                     with its own tribal roster.
            HUD    - the Phoenix office of the SOUTHWEST ONAP, which also
                     operates from Albuquerque.

Four different boundaries, one word. A single `region` column would silently
average them.

NEVER ASSERT THAT ONE BIA REGION EQUALS ONE IHS AREA
----------------------------------------------------
They were drawn by different agencies for different statutes at different
times. Where this build reports a relationship between two systems it is
DERIVED from entities the two happen to share, written to a file whose name
says `derived`, and it is never an equivalency.

WHAT OUTRANKS WHAT
------------------
An OFFICIAL_AGENCY_ASSIGNMENT - the agency itself publishing that this entity
belongs to this office - always outranks a GEOGRAPHIC_INFERENCE, and the two
stay in separate `assignment_basis` values forever so a later reader can tell
them apart. Same precision-over-recall rule the whole project runs on.

THE FAILURE MODE THIS LAYER EXISTS TO PREVENT
---------------------------------------------
`admin_regional_observations.csv` holds statistics that agencies publish only
at region level - "the Bemidji Area serves 34 federally recognised Tribes",
"the Pacific Region has 105". Those numbers describe the REGION. Copying one
onto each tribe inside it manufactures an entity-level observation that nobody
measured. The observations file is deliberately a separate table with no
entity key, so that join cannot be made by accident.

SCOPE
-----
This script owns BIA, IHS and HUD ONAP. A second agent owns NIGC and writes
NIGC_REGION rows into the same three files. The ID block CEDAR-ADMREG-3000xx
is reserved for NIGC and this script never writes into it; on every run it
reads back whatever NIGC rows already exist and preserves them untouched.

Usage:  py -3 code/85_build_admin_region_crosswalk.py fetch
        py -3 code/85_build_admin_region_crosswalk.py build
        py -3 code/85_build_admin_region_crosswalk.py all

Reads  data/spine/cedar_entity_spine.csv
       data/raw/external/admin_regions/*            (saved by `fetch`)
       data/raw/external/federal_award_lists/hud_onap_awards_parsed.csv
Writes data/clean/admin_region_systems.csv
       data/clean/admin_regions.csv
       data/clean/admin_region_assignments.csv
       data/clean/admin_regional_observations.csv
       data/clean/admin_region_overlap_derived.csv
       review/admin_region_unresolved.csv
       docs/ADMIN_REGION_CROSSWALK_LOG.md   (counts appended by hand)
"""

import csv
import html
import json
import re
import subprocess
import sys
import time
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

CEDAR = Path(__file__).resolve().parent.parent
CLEAN = CEDAR / "data" / "clean"
SPINE = CEDAR / "data" / "spine"
RAW = CEDAR / "data" / "raw" / "external" / "admin_regions"
AWARDS = CEDAR / "data" / "raw" / "external" / "federal_award_lists"
REVIEW = CEDAR / "review"
TODAY = date.today().isoformat()

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")

# Never write your own name matcher. resolve_entity is the project's one
# entity resolver and it refuses rather than guesses.
sys.path.insert(0, str(CEDAR / "code"))
_m = __import__("33_apply_party_rulings")
resolve_entity = _m.resolve_entity
norm = _m.norm

import cedar_ids                                               # noqa: E402
from cedar_keys import surrogate_id                            # noqa: E402

# ---------------------------------------------------------------------------
# ID BLOCKS.  Six digits, one contiguous block per system, so an ID is
# self-describing and two agents building concurrently cannot collide.
#
# 2026-08-26: "cannot collide" was a claim this file made and nothing
# enforced. The blocks were minted by an f-string, `cedar_ids` was never
# imported, and `cedar_ids.RESERVED_BLOCKS` knew about exactly ONE of these
# six ranges - so `allocate("CEDAR-ADMREG")` could have handed out a number
# inside `BIA_REGION`. Every block is now DECLARED to the ID service below,
# which refuses an overlapping claim from a different owner and steps over all
# of them in `allocate`. `84_build_nigc_regions.py` declares its own 9000xx
# block the same way. The bypass is now a call into the service, which means
# `328_audit_id_service_bypass.py` can find the ones that are not.
# ---------------------------------------------------------------------------
ID_BLOCKS = {
    "BIA_REGION":       (100001, 109999),
    "BIA_AGENCY":       (110001, 119999),
    "IHS_AREA":         (200001, 209999),
    "IHS_SERVICE_UNIT": (210001, 219999),
    "NIGC_REGION":      (300001, 309999),   # RESERVED - the NIGC agent owns it
    "HUD_ONAP_AREA":    (400001, 409999),
}
OWNED_BY_THIS_SCRIPT = {"BIA_REGION", "BIA_AGENCY", "IHS_AREA",
                        "IHS_SERVICE_UNIT", "HUD_ONAP_AREA"}

#: DECLARE every block to the ID service at import time. `NIGC_REGION` is
#: declared under its real owner, so a claim from anyone else raises
#: `cedar_ids.IdCollision` instead of silently overlapping.
_ADMREG_MINT = {
    sysname: cedar_ids.declare_static_block(
        "CEDAR-ADMREG", lo, hi,
        owner=("85_build_admin_region_crosswalk.py"
               if sysname in OWNED_BY_THIS_SCRIPT
               else "NIGC build (separate script)"),
        why=f"contiguous pre-assigned block for the {sysname} region system, "
            f"so a given region's id is the same number on every machine")
    for sysname, (lo, hi) in ID_BLOCKS.items()
}

# --------------------------------------------------------------------------
# THE PRIMARY KEY OF admin_regional_observations.csv, AND WHAT IT IS MADE OF
#
# `observation_id` was `f"CEDAR-ADMOBS-{len(observations)+1:06d}"` - the CALL
# ORDER of `add_obs()`. Adding one region system renumbered every observation
# recorded after it.
#
# It is now a deterministic blake2b digest of what an observation IS: a named
# measure, about one administrative region of one region system, in one year.
# All four are columns of the row. Measured 2026-08-26: unique over all 27
# rows, 0 blank.
#
# NOTE the deliberate difference from the region ids above. A REGION gets a
# block ordinal because it is one of a fixed, pre-assigned, contiguous set the
# project wants to be able to read off a number. An OBSERVATION is an
# open-ended fact about a region, so it gets a digest of the fact.
# --------------------------------------------------------------------------
ADMIN_OBSERVATION_KEY_COLUMNS = ["region_system_code",
                                 "administrative_region_id",
                                 "observation_name", "observation_year"]

# The published version of each boundary set, with the dates it governs.
# Boundaries change; a 2013 grant was not administered under the 2026 map, so
# nothing here is applied backwards without checking the then-current lists.
SYSTEM_VERSION = {
    "BIA_REGION":       "bia.gov-directory-2026",
    "BIA_AGENCY":       "bia.gov-directory-2026",
    "IHS_AREA":         "ihs.gov-directory-2026",
    "IHS_SERVICE_UNIT": "ihs.gov-directory-2026",
    "HUD_ONAP_AREA":    "hud.gov-onap-offices-2026",
}

BIA_REGIONS = [
    ("ALASKA",          "alaska",          "Alaska"),
    ("EASTERN",         "eastern",         "Eastern"),
    ("EASTERN_OKLAHOMA", "eastern-oklahoma", "Eastern Oklahoma"),
    ("GREAT_PLAINS",    "great-plains",    "Great Plains"),
    ("MIDWEST",         "midwest",         "Midwest"),
    ("NAVAJO",          "navajo",          "Navajo"),
    ("NORTHWEST",       "northwest",       "Northwest"),
    ("PACIFIC",         "pacific",         "Pacific"),
    ("ROCKY_MOUNTAIN",  "rocky-mountain",  "Rocky Mountain"),
    ("SOUTHERN_PLAINS", "southern-plains", "Southern Plains"),
    ("SOUTHWEST",       "southwest",       "Southwest"),
    ("WESTERN",         "western",         "Western"),
]

IHS_AREAS = [
    ("ALASKA",       "alaska",       "Alaska"),
    ("ALBUQUERQUE",  "albuquerque",  "Albuquerque"),
    ("BEMIDJI",      "bemidji",      "Bemidji"),
    ("BILLINGS",     "billings",     "Billings"),
    ("CALIFORNIA",   "california",   "California"),
    ("GREAT_PLAINS", "greatplains",  "Great Plains"),
    ("NASHVILLE",    "nashville",    "Nashville"),
    ("NAVAJO",       "navajo",       "Navajo"),
    ("OKLAHOMA_CITY", "oklahomacity", "Oklahoma City"),
    ("PHOENIX",      "phoenix",      "Phoenix"),
    ("PORTLAND",     "portland",     "Portland"),
    ("TUCSON",       "tucson",       "Tucson"),
]

# bia.gov's own nav points the Southwest Region's agency list at a DIFFERENT
# slug from every other region (`southwest-region`, not `southwest`). The
# obvious URL 404s, and a 404 body still contains a <main> element, so a
# parser that trusted the file rather than the status would have silently
# produced a Southwest Region with zero agencies.
BIA_AGENCY_PATH = {"southwest": "/regional-offices/southwest-region/agencies"}

# Two IHS areas publish NO `healthcarefacilities` page, and that is a fact
# about how care is delivered rather than a broken link: the Alaska Area is
# delivered entirely through tribal health organisations under compact, and
# the California Area entirely through tribally operated Indian health
# programmes. Neither runs IHS service units. Their rosters live elsewhere.
IHS_NO_FACILITIES_PAGE = {
    "alaska": ("/alaska/tribalhealthorganizations/",
               "Alaska Area care is delivered by tribal health organisations "
               "under P.L. 93-638 compacts; IHS runs no service units there."),
    "california": ("/california/index.cfm/health-programs/health-programs/",
                   "California Area care is delivered by tribally operated "
                   "Indian health programmes; IHS runs no service units "
                   "there."),
}

# IHS area pages that publish a roster of the tribes the area serves. Only
# these produce OFFICIAL tribe->area assignments; the rest are left unassigned
# rather than inferred from a state.
# they serve, with the SUBJECT TYPE each page actually lists. The Alaska page
# lists tribal health ORGANISATIONS, not tribes - ANTHC and the regional
# consortia are the entities IHS deals with there, and recording them as
# tribes would misdescribe both the entity and the relationship.
IHS_TRIBE_PAGES = {
    "phoenix": ("/phoenix/tribal/", "TRIBE", "SERVICE_POPULATION"),
    "alaska":  ("/alaska/tribalhealthorganizations/", "NATIVE_ENTITY",
                "FACILITY_ASSIGNMENT"),
}
# Bemidji's `Tribal Information` page is about consultation policy and lists
# no tribes, so it is deliberately NOT here. Its 34 tribes are a published
# COUNT (an admin_regional_observation) and not a published roster; inventing
# the roster from the count is precisely the move this layer forbids.

# Grouping headers on those pages - "Arizona Tribes", "Nevada and Utah
# Tribes" - are page furniture, not entities. Held items should be entities
# the resolver genuinely could not place, not headings it was never meant to.
IHS_SECTION_HEADER = re.compile(
    r"^(arizona|nevada|utah|california|minnesota|michigan|wisconsin|"
    r"nevada and utah|alaska)?\s*(tribes|tribal (organizations|health "
    r"organizations)|federally recognized tribes)$|"
    r"^office of |^national |^ihs |^urban indian|^index$", re.I)

# HUD ONAP. The office list names seven areas across eight office locations -
# Southwest ONAP operates from both Phoenix and Albuquerque and is ONE area.
HUD_ONAP = [
    ("AK", "Alaska", "Alaska ONAP", "Anchorage", "AK",
     "AK-Tribe-TDHE-Assignments.pdf"),
    ("EW", "Eastern Woodlands", "Eastern Woodlands ONAP", "Chicago", "IL",
     "EW-Tribe-TDHE-Assignments.pdf"),
    ("HI", "Hawaii", "Office of Native American Programs - Hawaii", "Honolulu",
     "HI", ""),
    ("NP", "Northern Plains", "Northern Plains ONAP", "Denver", "CO",
     "NP-Tribe-TDHE-Assignments.pdf"),
    ("NW", "Northwest", "Northwest ONAP", "Seattle", "WA",
     "NW-Tribe-TDHE-Assignments.pdf"),
    ("SP", "Southern Plains", "Southern Plains ONAP", "Oklahoma City", "OK",
     "SP-Tribe-TDHE-Assignments.pdf"),
    ("SW", "Southwest", "Southwest ONAP", "Phoenix", "AZ",
     "SW-Tribe-TDHE-Assignments.pdf"),
]

BIA_BASE = "https://www.bia.gov"
IHS_BASE = "https://www.ihs.gov"
HUD_ONAP_OFFICES_URL = ("https://www.hud.gov/helping-americans/"
                        "public-indian-housing-offices")
HUD_PDF_BASE = "https://www.hud.gov/sites/dfiles/PIH/documents/"

BOILERPLATE = re.compile(
    r"tribal leaders directory|to search the|to view the|visit the bia|"
    r"geospatial|open data portal|exit disclaimer|^\s*$|^page \d|"
    r"^\W+$", re.I)


# ---------------------------------------------------------------------------
# io
# ---------------------------------------------------------------------------
def read_csv(p):
    p = Path(p)
    if not p.exists():
        return []
    with open(p, encoding="utf-8-sig", errors="replace", newline="") as fh:
        return list(csv.DictReader(fh))


def write_csv(p, rows, fields):
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fields})
    print(f"  wrote {p.relative_to(CEDAR)}  ({len(rows):,} rows)")


def curl(url, dest, sleep=1.2):
    """One request, saved to disk, status recorded. No retry loop lives here -
    per docs/PULL_DISCIPLINE.md a retry loop is a poller and needs a lock."""
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    p = subprocess.run(
        ["curl", "-s", "-L", "-A", UA, "--max-time", "45",
         "-w", "%{http_code}", "-o", str(dest), url],
        capture_output=True, text=True)
    status = (p.stdout or "0").strip()[-3:]
    size = dest.stat().st_size if dest.exists() else 0
    print(f"    {status}  {size:>8,}  {url}")
    time.sleep(sleep)
    return {"file": dest.name, "url": url, "http_status": status,
            "bytes": size, "fetched_date": TODAY}


# ---------------------------------------------------------------------------
# html helpers
# ---------------------------------------------------------------------------
def main_block(t, marker=None):
    """Content region. The MARKER WINS when one is given: ihs.gov wraps its
    entire page - masthead, A-to-Z index, mail-stop list - inside <main>, so
    preferring <main> there returns the furniture and buries the roster. On
    bia.gov <main> is the content and no marker is needed."""
    if marker:
        i = t.find(marker)
        if i > 0:
            j = t.find("<footer", i)
            return t[i: j if j > i else i + 60000]
    m = re.search(r"<main.*?</main>", t, re.S | re.I)
    if m:
        return m.group(0)
    return t


def to_lines(frag):
    """Tag soup -> text lines, preserving the <br>/<li>/<p> boundaries that
    carry the structure on these pages."""
    b = re.sub(r"<(script|style)\b.*?</\1>", "", frag, flags=re.S | re.I)
    b = re.sub(r"<br\s*/?>", "\n", b, flags=re.I)
    b = re.sub(r"</(p|li|div|h\d|td|tr|ul|strong)>", "\n", b, flags=re.I)
    b = re.sub(r"<[^>]+>", "", b)
    b = html.unescape(b).replace("\u00a0", " ").replace("\ufffd", "'")
    # ihs.gov puts its leaving-the-site notice INSIDE the same line as the
    # entity, so "Hopi Tribe" arrives as "Hopi Tribe Exit Disclaimer: You Are
    # Leaving www.ihs.gov". Dropping such lines as boilerplate discards every
    # tribe with an external website - which is most of them.
    b = re.sub(r"\s*Exit Disclaimer:[^\n]*", "", b)
    return [re.sub(r"\s+", " ", x).strip() for x in b.split("\n")
            if re.sub(r"\s+", " ", x).strip()]


def links(frag, prefix):
    """(href, label) pairs, de-duplicated on href, labels of a split anchor
    joined - bia.gov wraps 'Tohono O'odham Agency' across two <a> fragments."""
    out = {}
    for m in re.finditer(r'href="([^"]+)"[^>]*>(.*?)</a>', frag, re.S | re.I):
        href = m.group(1)
        if not href.startswith(prefix):
            continue
        lab = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "",
                                         html.unescape(m.group(2)))).strip()
        if not lab:
            continue
        out[href] = (out[href] + " " + lab).strip() if href in out else lab
    return list(out.items())


# ---------------------------------------------------------------------------
# FETCH
# ---------------------------------------------------------------------------
def fetch():
    print("=== 85 fetch: agency directories ===")
    man = []
    print("\n[BIA]")
    man.append(curl(f"{BIA_BASE}/regional-offices",
                    RAW / "bia_regional_offices.html"))
    for _, slug, _ in BIA_REGIONS:
        man.append(curl(f"{BIA_BASE}/regional-offices/{slug}",
                        RAW / f"bia_region_{slug}.html"))
        man.append(curl(BIA_BASE + BIA_AGENCY_PATH.get(
            slug, f"/regional-offices/{slug}/agencies"),
            RAW / f"bia_agencies_{slug}.html"))
        man.append(curl(f"{BIA_BASE}/regional-offices/{slug}/tribes-served",
                        RAW / f"bia_tribes_{slug}.html"))
        man.append(curl(f"{BIA_BASE}/regional-offices/{slug}/contact-us",
                        RAW / f"bia_contact_{slug}.html"))

    print("\n[IHS]")
    man.append(curl(f"{IHS_BASE}/locations/", RAW / "ihs_locations.html"))
    for _, slug, _ in IHS_AREAS:
        man.append(curl(f"{IHS_BASE}/{slug}/", RAW / f"ihs_area_{slug}.html"))
        man.append(curl(f"{IHS_BASE}/{slug}/contactus/",
                        RAW / f"ihs_contact_{slug}.html"))
        if slug in IHS_NO_FACILITIES_PAGE:
            man.append(curl(IHS_BASE + IHS_NO_FACILITIES_PAGE[slug][0],
                            RAW / f"ihs_programs_{slug}.html"))
            continue
        man.append(curl(f"{IHS_BASE}/{slug}/healthcarefacilities/",
                        RAW / f"ihs_facilities_{slug}.html"))
    for slug, (path, _, _) in IHS_TRIBE_PAGES.items():
        man.append(curl(f"{IHS_BASE}{path}", RAW / f"ihs_tribes_{slug}.html"))

    print("\n[HUD ONAP]")
    man.append(curl(HUD_ONAP_OFFICES_URL, RAW / "hud_onap_offices.html"))
    for code, _, _, _, _, pdf in HUD_ONAP:
        if pdf:
            man.append(curl(HUD_PDF_BASE + pdf, RAW / f"hud_onap_{code}.pdf"))

    write_csv(RAW / "_SOURCE_MANIFEST.csv", man,
              ["file", "url", "http_status", "bytes", "fetched_date"])
    bad = [m for m in man if m["http_status"] != "200"]
    print(f"\n  {len(man)} requests, {len(bad)} non-200")
    for b in bad:
        print(f"    {b['http_status']}  {b['url']}")


# ---------------------------------------------------------------------------
# PARSERS
# ---------------------------------------------------------------------------
OFFICE_HEADING = re.compile(r"(agency|field office|regional office)\s*:?\s*$",
                            re.I)


def parse_office_roster(path, known=frozenset()):
    """`tribes-served` pages, four different house styles across twelve
    regions:  <p><strong>X:</strong><br>a<br>b</p>  |  <p>X:</p><ul><li>a</li>
    |  <h2><strong>X:</strong></h2><ul>...  |  a table wrapping either.

    All four reduce to the same line stream once <br>/<li>/<p> become
    newlines: a heading ends in a colon, everything after it belongs to that
    heading until the next one. Parsing the stream rather than the markup is
    what makes one parser cover all twelve.

    THE COLON IS NOT ALWAYS THERE. Eastern Oklahoma prints "Talihina Agency"
    and "Wewoka Agency" bare, and Western prints "Southern Paiute Agency"
    bare. A colon-only rule reads those as TRIBES belonging to the office
    above them - which does not merely lose three headings, it files every
    tribe underneath them with the wrong agency. So a line is also a heading
    when it ends in Agency / Field Office / Regional Office, or when it
    matches an office `known` from that region's own agency page.
    """
    t = Path(path).read_text(encoding="utf-8", errors="replace")
    out = defaultdict(list)
    office = None
    for line in to_lines(main_block(t)):
        if BOILERPLATE.search(line):
            continue
        head = None
        if line.endswith(":") and len(line) < 90:
            head = line[:-1].strip()
        elif len(line) < 90 and (OFFICE_HEADING.search(line)
                                 or norm(line) in known):
            head = line.rstrip(":").strip()
        if head:
            office = head
            out.setdefault(office, [])
            continue
        if office and 3 < len(line) < 140 and not line.startswith("http"):
            out[office].append(line)
    return dict(out)


def parse_agency_links(path, slug):
    """Agency roster from a region's `agencies` page. Links three segments
    deep are agencies; four segments deep are agencies nested under a state
    grouping link, and the grouping link itself is dropped."""
    t = Path(path).read_text(encoding="utf-8", errors="replace")
    body = main_block(t)
    found = links(body, f"/regional-offices/{slug}/")
    deep = [(h, l) for h, l in found if h.strip("/").count("/") == 3]
    if deep:                       # state groupings present -> leaves only
        return deep
    return [(h, l) for h, l in found if h.strip("/").count("/") == 2]


AGENCY_IN_PROSE = re.compile(
    r"\b((?:[A-Z][\w'’.\-]*(?<!Agency)(?<!Office)(?<!Agencies)\s+){0,3}"
    r"[A-Z][\w'’.\-]*\s+(?:Agency|Field Office))\b")
NOT_AN_AGENCY = re.compile(
    r"regional|bureau|indian affairs|central office|agencies|email|"
    r"irrigation|\bthe\b|\band\b|\bor\b", re.I)


def parse_agency_prose(path):
    """Some regions name agencies only in prose. The Southwest Regional Office
    page says "Nine agencies are under the SWRO" and then hyperlinks eight of
    them - Laguna Agency is named in the sentence and linked nowhere. Reading
    the sentence as well as the links is the difference between 8 and the 9
    BIA says it runs.

    Scanned LINE BY LINE. Run against the whole page joined into one string,
    the left boundary walks backwards across a list separator and produces
    "Fort Defiance Agency Shiprock Agency" - one name for two offices, and a
    new office that does not exist."""
    t = Path(path).read_text(encoding="utf-8", errors="replace")
    out = []
    for line in to_lines(main_block(t)):
        for m in AGENCY_IN_PROSE.finditer(line):
            nm = re.sub(r"\s+", " ", m.group(1)).strip()
            if NOT_AN_AGENCY.search(nm) or len(nm) > 55:
                continue
            if len(re.findall(r"Agency|Field Office", nm)) != 1:
                continue
            out.append(nm)
    return out


def office_type(label):
    lab = label.lower()
    if "irrigation" in lab:
        return "irrigation_project"
    if "field office" in lab:
        return "field_office"
    if lab.endswith("office") or " office" in lab:
        return "field_office"
    if "agency" in lab:
        return "agency"
    return "non_agency_service_provider"


# Every Indian Affairs page carries the Department of the Interior's own
# address. Reading the first "City, ST ZIP" off a page therefore puts the
# Midwest Regional Office in Washington DC, which is where the Department is
# and not where the office is.
DEPARTMENT_HQ = re.compile(r"1849 C Street|Washington,?\s+DC\s+20240|"
                           r"5600 Fishers Lane|Rockville,?\s+MD\s+20857", re.I)

# Address lines are not uniform even inside one agency: bia.gov prints
# "Portland, Oregon 97232-4169" and ihs.gov prints "Oklahoma City, OK. 73114".
STATE_ABBR = {
    "alabama": "AL", "alaska": "AK", "arizona": "AZ", "arkansas": "AR",
    "california": "CA", "colorado": "CO", "connecticut": "CT",
    "delaware": "DE", "florida": "FL", "georgia": "GA", "hawaii": "HI",
    "idaho": "ID", "illinois": "IL", "indiana": "IN", "iowa": "IA",
    "kansas": "KS", "kentucky": "KY", "louisiana": "LA", "maine": "ME",
    "maryland": "MD", "massachusetts": "MA", "michigan": "MI",
    "minnesota": "MN", "mississippi": "MS", "missouri": "MO",
    "montana": "MT", "nebraska": "NE", "nevada": "NV",
    "new hampshire": "NH", "new jersey": "NJ", "new mexico": "NM",
    "new york": "NY", "north carolina": "NC", "north dakota": "ND",
    "ohio": "OH", "oklahoma": "OK", "oregon": "OR", "pennsylvania": "PA",
    "rhode island": "RI", "south carolina": "SC", "south dakota": "SD",
    "tennessee": "TN", "texas": "TX", "utah": "UT", "vermont": "VT",
    "virginia": "VA", "washington": "WA", "west virginia": "WV",
    "wisconsin": "WI", "wyoming": "WY",
}
ADDRESS_LINE = re.compile(
    r"^(.+?)\s*,\s*([A-Za-z][A-Za-z ]{1,19}?)\s*[.,]?\s+\d{5}")


def parse_mailing_address(paths, marker=None):
    """City / ST from an office's own mailing-address block."""
    for path in paths:
        if not path:
            continue
        t = Path(path).read_text(encoding="utf-8", errors="replace")
        lines = to_lines(main_block(t, marker))
        for i, line in enumerate(lines):
            if DEPARTMENT_HQ.search(line):
                continue
            if i and DEPARTMENT_HQ.search(lines[i - 1]):
                continue
            m = ADDRESS_LINE.match(line)
            if not m or len(m.group(1)) > 40:
                continue
            st = m.group(2).strip()
            st = st.upper() if len(st) == 2 else STATE_ABBR.get(st.lower(), "")
            if st:
                return m.group(1).strip(), st
    return "", ""


def parse_ihs_service_units(path, slug):
    """IHS areas list service units and individual facilities in one
    undifferentiated bullet list, and SIX OF THE TEN AREAS WITH SUCH A PAGE
    NEVER USE THE PHRASE. Albuquerque writes "Acoma-Canoncito-Laguna Service
    Unit"; Navajo writes "There are 12 health care centers in the region" and
    names the centres. Only entries IHS itself calls a Service Unit become
    IHS_SERVICE_UNIT boundaries. The rest are facilities and are recorded as
    facilities - real, sourced, attached to the AREA, and not promoted to a
    boundary that the agency never drew."""
    p = Path(path)
    if not p.exists():
        return [], []
    t = p.read_text(encoding="utf-8", errors="replace")
    body = main_block(t, 'id="site_content"')
    units, others = [], []
    for href, lab in links(body, "http") + links(body, "/"):
        lab = lab.strip()
        if not lab or len(lab) > 90 or BOILERPLATE.search(lab):
            continue
        if re.search(r"service unit", lab, re.I):
            units.append((lab, href))
        elif (f"/{slug}/healthcarefacilities/" in href
              or re.search(r"health|hospital|clinic|medical|wellness|"
                           r"treatment|dental", lab, re.I)):
            others.append((lab, href))
    return units, others


def parse_ihs_facilities(path):
    """The IHS locations map carries the whole facility list in parallel JS
    arrays. The facility's own URL names its area, which is the only area
    statement on the page; a facility with no URL gets no area rather than the
    area of whatever block it happens to sit in."""
    t = Path(path).read_text(encoding="utf-8", errors="replace")

    def arr(name):
        # Quoted items ONLY. A permissive split also captures the whitespace
        # between elements, which shifts every later index by one and silently
        # pairs a facility with another facility's city and area.
        m = re.search(r"var\s+" + name + r"\s*=\s*\[(.*?)\];", t, re.S)
        return re.findall(r"'([^']*)'", m.group(1)) if m else []

    names = arr("fac_names")
    urls = arr("fac_urls")
    cities = arr("fac_cities")
    states = arr("fac_states")
    n = min(len(names), len(urls), len(cities), len(states))
    out = []
    for i in range(n):
        u = urls[i]
        area = ""
        su = ""
        m = re.search(r"ihs\.gov/([a-z]+)/healthcarefacilities/([a-z0-9\-]+)?",
                      u, re.I)
        if m:
            area = m.group(1).lower()
            su = (m.group(2) or "").lower()
        out.append({"name": names[i], "city": cities[i], "state": states[i],
                    "url": "" if u == "NA" else u, "area_slug": area,
                    "su_slug": su})
    return out


def parse_hud_tdhe_pdf(path):
    """HUD publishes, per ONAP area, the tribes and the TDHEs that office
    administers. The two are labelled separately in the source and stay
    separate here: a tribe and its TDHE are different legal persons and
    collapsing them would lose which one actually receives the grant."""
    try:
        import pypdf
    except ImportError:
        print("    pypdf missing - HUD TDHE assignments skipped")
        return [], ""
    r = pypdf.PdfReader(str(path))
    text = "\n".join((pg.extract_text() or "") for pg in r.pages)
    doc_date = ""
    m = re.search(r"[A-Z][a-z]+day,\s+([A-Z][a-z]+ \d{1,2}, \d{4})", text)
    if m:
        doc_date = m.group(1)
    out, current_tribe = [], ""
    for line in text.split("\n"):
        line = line.strip()
        m = re.match(r"^(.*?)(Tribe|TDHE):$", line)
        if not m or not m.group(1).strip():
            continue
        name, role = m.group(1).strip(), m.group(2).upper()
        if role == "TRIBE":
            current_tribe = name
        # HUD prints each TDHE directly beneath the tribe it serves, and a
        # regional authority such as AVCP RHA appears once per village. That
        # pairing IS the document's structure, so it is carried on the row -
        # which also keeps one assignment per (TDHE, tribe) rather than
        # flattening a regional authority to a single row and losing which
        # communities it actually covers.
        out.append((name, role, "" if role == "TRIBE" else current_tribe))
    return out, doc_date


# ---------------------------------------------------------------------------
# BUILD
# ---------------------------------------------------------------------------
class Ids:
    """Minting goes through `cedar_ids`, which owns the declared blocks.

    This used to keep its own counters and its own f-string. Both are now the
    ID service's - a block that is exhausted raises `cedar_ids.IdCollision`
    rather than spilling into the next owner's range.
    """

    def __init__(self):
        self.mint = {k: cedar_ids.declare_static_block(
            "CEDAR-ADMREG", lo, hi,
            owner=("85_build_admin_region_crosswalk.py"
                   if k in OWNED_BY_THIS_SCRIPT
                   else "NIGC build (separate script)"),
            why=f"contiguous pre-assigned block for {k}")
            for k, (lo, hi) in ID_BLOCKS.items()}

    def next(self, system):
        return self.mint[system]()


def build():
    print("=== 85 build: Federal Indian Program Geography crosswalk ===\n")
    spine = read_csv(SPINE / "cedar_entity_spine.csv")
    print(f"spine entities: {len(spine):,}")
    fed_tribes = [r for r in spine if r["entity_class"] in (
        "Federally recognized tribe", "Federally recognized Alaska Native Village")]
    print(f"  federally recognised: {len(fed_tribes):,}")

    manifest = {m["file"]: m for m in read_csv(RAW / "_SOURCE_MANIFEST.csv")}

    def src(fname, fallback=""):
        return manifest.get(fname, {}).get("url", fallback)

    def ok(fname):
        """Path to a raw file ONLY if the fetch returned 200. A 404 body from
        these CMSs still contains a <main> element, so trusting the file
        rather than the status is how a region silently loses its agencies."""
        p = RAW / fname
        st = manifest.get(fname, {}).get("http_status", "")
        # A file with no manifest row is a leftover from an earlier URL that
        # no longer exists - exactly the 404 bodies this guard is for - so it
        # is refused too. Only a file the CURRENT fetch recorded as 200 is
        # read. When there is no manifest at all, nothing has been fetched.
        if manifest and p.exists() and st == "200":
            return p
        return None

    ids = Ids()
    regions, assigns, observations, unresolved = [], [], [], []
    reg_by_key = {}          # (system, region_code) -> id
    aid = [0]

    def add_region(system, code, canonical, official="", parent="",
                   city="", st="", url="", vstatus="OFFICIAL_PUBLISHED",
                   start="", end="", active="active", notes=""):
        rid = ids.next(system)
        reg_by_key[(system, code)] = rid
        regions.append({
            "administrative_region_id": rid,
            "region_system_code": system,
            "region_code": code,
            "canonical_name": canonical,
            "official_name": official or canonical,
            "parent_administrative_region_id": parent,
            "headquarters_city": city,
            "headquarters_state": st,
            "effective_start_date": start,
            "effective_end_date": end,
            "active_status": active,
            "source_url": url,
            "verification_status": vstatus,
            "built_date": TODAY,
            "region_system_version": SYSTEM_VERSION.get(system, ""),
            "notes": notes,
            "built_by_script": "85_build_admin_region_crosswalk.py",
        })
        return rid

    def add_assign(subject_type, subject_id, subject_name, system, rid,
                   basis, method, conf, url, notes="", primary="0",
                   vstatus="OFFICIAL_PUBLISHED", start="", end="",
                   sy="", ey="", related=""):
        aid[0] += 1
        assigns.append({
            "assignment_id": f"CEDAR-ADMASG-{aid[0]:06d}",
            "subject_type": subject_type,
            "subject_id": subject_id,
            "subject_name": subject_name,
            "related_subject_name": related,
            "region_system_code": system,
            "administrative_region_id": rid,
            "assignment_basis": basis,
            "effective_start_date": start,
            "effective_end_date": end,
            "is_primary": primary,
            "verification_status": vstatus,
            "confidence": conf,
            "source_url": url,
            "notes": notes,
            "built_date": TODAY,
            "region_system_version": SYSTEM_VERSION.get(system, ""),
            "effective_start_year": sy,
            "effective_end_year": ey,
            "assignment_method": method,
            "fetched_date": TODAY,
            "built_by_script": "85_build_admin_region_crosswalk.py",
        })

    def hold(what, name, system, reason, evidence=""):
        unresolved.append({"item_type": what, "name": name,
                           "region_system_code": system, "reason": reason,
                           "evidence": evidence, "queued_date": TODAY})

    def add_obs(system, rid, code, name, value, unit, year, published,
                basis, url, quote="", notes=""):
        obs = {
            "observation_id": "",      # set below, from THIS row's own facts
            "region_system_code": system,
            "administrative_region_id": rid,
            "region_code": code,
            "observation_name": name,
            "observation_value": value,
            "observation_unit": unit,
            "observation_year": year,
            "published_at_region_level": published,
            "observation_basis": basis,
            "source_url": url,
            "source_quote": quote[:400],
            "notes": notes,
            "fetched_date": TODAY,
            "built_date": TODAY,
            "built_by_script": "85_build_admin_region_crosswalk.py",
        }
        obs["observation_id"] = surrogate_id(
            "CEDAR-ADMOBS", obs, ADMIN_OBSERVATION_KEY_COLUMNS)
        observations.append(obs)

    # -----------------------------------------------------------------
    # 1. BIA regions and agencies
    # -----------------------------------------------------------------
    print("\n[1] BIA")
    bia_index = ok("bia_regional_offices.html")
    declared_regions = declared_agencies = ""
    if bia_index:
        txt = " ".join(to_lines(main_block(
            bia_index.read_text(encoding="utf-8", errors="replace"))))
        m = re.search(r"the (\w+) regional offices and (\d+) agencies", txt, re.I)
        if m:
            declared_regions, declared_agencies = m.group(1), m.group(2)
            print(f"  bia.gov states: {declared_regions} regional offices, "
                  f"{declared_agencies} agencies")

    bia_url = src("bia_regional_offices.html",
                  "https://www.bia.gov/regional-offices")
    for code, slug, name in BIA_REGIONS:
        city, st = parse_mailing_address([ok(f"bia_contact_{slug}.html"),
                                          ok(f"bia_region_{slug}.html")])
        add_region("BIA_REGION", code, f"{name} Region",
                   f"Bureau of Indian Affairs {name} Regional Office",
                   city=city, st=st,
                   url=src(f"bia_region_{slug}.html",
                           f"https://www.bia.gov/regional-offices/{slug}"))
    print(f"  BIA regions: {sum(1 for r in regions if r['region_system_code']=='BIA_REGION')}")

    # Agency roster = links on the /agencies page UNION headings on the
    # /tribes-served page. Two regions publish no agency list at all
    # (Eastern is prose, Southwest 404s) and their agencies appear only as
    # tribes-served headings, so neither source alone is complete.
    agency_rows = {}          # (region_code, key) -> dict
    served = {}               # slug -> {office: [tribe, ...]}

    def put(code, reg_id, label, url, how, keys, subset_guard=False):
        """One office, several names. The Western Region's Papago Agency is
        hyperlinked as `Tohono O'odham Agency` and headed `Papago Agency` on
        the tribes-served page - the same office under its old and new names.
        Keyed on every alias, it is one row with an alias list; keyed on the
        label alone it becomes two agencies that do not both exist."""
        label = re.sub(r"\s+", " ", label).strip()
        if not label or BOILERPLATE.search(label):
            return
        keys = {k for k in keys if k}
        hit = next((agency_rows[(code, k)] for k in keys
                    if (code, k) in agency_rows), None)
        if hit:
            if norm(label) != norm(hit["label"]):
                hit["aliases"].add(label)
            hit["url"] = hit["url"] or url
            for k in keys:
                agency_rows[(code, k)] = hit
            return
        if subset_guard:
            # A prose sweep also reads the tail of a longer name: "Uintah &
            # Ouray Agency" yields "Ouray Agency", which is not a second
            # office. Anything already contained in a linked name is that
            # name, not a new one.
            n = norm(label)
            for (c, _), other in agency_rows.items():
                if c == code and n in norm(other["label"]) and n != norm(other["label"]):
                    other["aliases"].add(label)
                    return
        rec = {"label": label, "region": code, "parent": reg_id, "url": url,
               "how": how, "aliases": set(), "keys": keys}
        for k in keys:
            agency_rows[(code, k)] = rec

    for code, slug, name in BIA_REGIONS:
        reg_id = reg_by_key[("BIA_REGION", code)]
        ap = ok(f"bia_agencies_{slug}.html")
        if ap:
            for href, lab in parse_agency_links(ap, slug):
                # The URL slug is an alias in its own right and it is what
                # bridges "Tohono O'odham Agency" to "Papago Agency".
                slug_name = norm(href.rstrip("/").rsplit("/", 1)[-1]
                                 .replace("-", " "))
                put(code, reg_id, lab, BIA_BASE + href, "agency_page_link",
                    {norm(lab), slug_name})
            for lab in parse_agency_prose(ap):
                put(code, reg_id, lab, "", "agency_page_prose_only",
                    {norm(lab)}, subset_guard=True)
        known = {k for (c, k) in agency_rows if c == code}
        tp = ok(f"bia_tribes_{slug}.html")
        if tp:
            served[slug] = parse_office_roster(tp, known)
            for office in served[slug]:
                if re.search(r"regional office", office, re.I):
                    continue
                put(code, reg_id, office, "", "tribes_served_heading",
                    {norm(office)})

    # lint-ok: class7 - `id()` here is PYTHON OBJECT IDENTITY for an in-memory object,
    # used as a key in a dict/set that lives and dies inside this one function. It is
    # never written to a file, nothing joins on it, and it is not a primary key.
    # 293_lint_bug_classes.py waives the same shape in its own source. Triaged LOW by
    # 326_triage_class7_key_risk.py on 2026-08-26: no clean or spine table carries it.
    uniq = {id(a): a for a in agency_rows.values()}
    agency_id = {}            # (region_code, key) -> administrative_region_id
    for a in sorted(uniq.values(), key=lambda x: (x["region"], x["label"])):
        ac = re.sub(r"[^A-Z0-9]+", "_", a["label"].upper()).strip("_")
        rid = add_region("BIA_AGENCY", f"{a['region']}::{ac}", a["label"],
                         parent=a["parent"], url=a["url"] or bia_url,
                         notes=(f"office_type={office_type(a['label'])}; "
                                f"named by BIA via {a['how']}"
                                + (f"; also published as "
                                   f"{' | '.join(sorted(a['aliases']))}"
                                   if a["aliases"] else "")),
                         vstatus=("OFFICIAL_PUBLISHED"
                                  if a["how"] != "agency_page_prose_only"
                                  else "OFFICIAL_PROSE_ONLY"))
        for k in a["keys"]:
            agency_id[(a["region"], k)] = rid
    n_ag = len(uniq)
    kinds = Counter(office_type(a["label"]) for a in uniq.values())
    print(f"  BIA agency-level offices parsed: {n_ag}   "
          f"(bia.gov declares {declared_agencies} agencies)")
    for k, v in kinds.most_common():
        print(f"      {v:4d}  {k}")

    # tribe -> agency, and tribe -> region. OFFICIAL: BIA published it.
    bia_region_of_tribe = defaultdict(set)
    n_ag_asg = n_unres = 0
    for code, slug, name in BIA_REGIONS:
        reg_id = reg_by_key[("BIA_REGION", code)]
        url = src(f"bia_tribes_{slug}.html",
                  f"https://www.bia.gov/regional-offices/{slug}/tribes-served")
        for office, tribes in served.get(slug, {}).items():
            is_ro = bool(re.search(r"regional office", office, re.I))
            ag_id = "" if is_ro else agency_id.get((code, norm(office)), "")
            for tname in tribes:
                tid, canon, how = resolve_entity(tname, spine)
                if not tid:
                    hold("bia_tribes_served", tname, "BIA_AGENCY", how,
                         f"{name} Region / {office}")
                    n_unres += 1
                    continue
                bia_region_of_tribe[tid].add(code)
                if ag_id:
                    add_assign("TRIBE", tid, canon, "BIA_AGENCY", ag_id,
                               "OFFICIAL_AGENCY_ASSIGNMENT",
                               f"bia_tribes_served+{how}", "high", url,
                               notes=f"BIA {name} Region, {office}",
                               primary="1")
                    n_ag_asg += 1
                else:
                    add_assign("TRIBE", tid, canon, "BIA_REGION", reg_id,
                               "OFFICIAL_AGENCY_ASSIGNMENT",
                               f"bia_tribes_served+{how}", "high", url,
                               notes=("served directly by the Regional Office; "
                                      "no agency-level office"), primary="1")
    print(f"  tribe->BIA agency assignments: {n_ag_asg}")
    print(f"  tribes-served names unresolved to the spine: {n_unres}")

    # tribe -> region. Rolls up from the agency assignment where BIA published
    # one; otherwise from the BIA Tribal Leaders Directory region already on
    # the spine, which is BIA's own attribute and so still official - but a
    # different publication, and it says so.
    n_roll = n_spine = 0
    for r in spine:
        tid = r["tribe_id"]
        if tid in bia_region_of_tribe:
            for code in sorted(bia_region_of_tribe[tid]):
                add_assign("TRIBE", tid, r["canonical_name"], "BIA_REGION",
                           reg_by_key[("BIA_REGION", code)],
                           "OFFICIAL_AGENCY_ASSIGNMENT",
                           "rollup_from_bia_agency", "high",
                           src(f"bia_tribes_{dict((c,s) for c,s,_ in BIA_REGIONS)[code]}.html"),
                           notes="rolled up from the BIA agency that serves it",
                           primary="1")
                n_roll += 1
            continue
        sp = (r.get("bia_region") or "").strip()
        if not sp:
            continue
        code = re.sub(r"[^A-Z0-9]+", "_", sp.upper()).strip("_")
        rid = reg_by_key.get(("BIA_REGION", code))
        if not rid:
            hold("spine_bia_region", sp, "BIA_REGION",
                 "region name on the spine matches no BIA region", tid)
            continue
        add_assign("TRIBE", tid, r["canonical_name"], "BIA_REGION", rid,
                   "OFFICIAL_AGENCY_ASSIGNMENT", "bia_tribal_leaders_directory",
                   "medium", "https://www.bia.gov/service/tribal-leaders-directory",
                   notes=("BIA Tribal Leaders Directory region carried on the "
                          "entity spine; the region's own tribes-served page "
                          "does not list this entity"),
                   primary="1", vstatus="OFFICIAL_SECONDARY_PUBLICATION")
        n_spine += 1
    print(f"  tribe->BIA region  from agency roll-up : {n_roll}")
    print(f"  tribe->BIA region  from TLD on spine   : {n_spine}")

    # Regional statistics BIA publishes in region-page prose.
    for code, slug, name in BIA_REGIONS:
        rid = reg_by_key[("BIA_REGION", code)]
        url = src(f"bia_region_{slug}.html")
        for p in (ok(f"bia_region_{slug}.html"), ok(f"bia_agencies_{slug}.html")):
            if not p:
                continue
            txt = " ".join(to_lines(main_block(
                p.read_text(encoding="utf-8", errors="replace"))))
            for pat, oname, unit in [
                (r"(?:to|the)\s+([\d,]+)\s+federally recognized (?:Indian )?[Tt]ribes",
                 "federally_recognized_tribes_served", "count"),
                (r"([\d,]+)\s+unique [Tt]ribes",
                 "federally_recognized_tribes_served", "count"),
                (r"over\s+([\d,]+)\s+[Tt]ribal [Mm]embers",
                 "tribal_members_minimum", "persons"),
                (r"([\d,]+)\s+acres held in trust",
                 "trust_acres", "acres"),
                (r"([\d,]+)\s+acres of restricted lands",
                 "restricted_acres", "acres"),
                (r"over\s+([\d,]+)\s+million acres",
                 "land_area_million_acres_minimum", "million_acres"),
            ]:
                m = re.search(pat, txt)
                if m:
                    q = txt[max(0, m.start() - 90): m.end() + 90]
                    add_obs("BIA_REGION", rid, code, oname,
                            m.group(1).replace(",", ""), unit, "2026",
                            "1", "AGENCY_PUBLISHED", url, q)

    # -----------------------------------------------------------------
    # 2. IHS areas and service units
    # -----------------------------------------------------------------
    print("\n[2] IHS")
    for code, slug, name in IHS_AREAS:
        city, st = parse_mailing_address([ok(f"ihs_contact_{slug}.html"),
                                          ok(f"ihs_area_{slug}.html")],
                                         'id="site_content"')
        add_region("IHS_AREA", code, f"{name} Area",
                   f"Indian Health Service {name} Area",
                   city=city, st=st,
                   url=src(f"ihs_area_{slug}.html", f"{IHS_BASE}/{slug}/"))
    print(f"  IHS areas: {len(IHS_AREAS)}  (ihs.gov/locations lists "
          f"{len(IHS_AREAS)})")

    su_by_slug = {}
    n_su = 0
    n_fac_page = [0]
    for code, slug, name in IHS_AREAS:
        area_id = reg_by_key[("IHS_AREA", code)]
        if slug in IHS_NO_FACILITIES_PAGE:
            path, why = IHS_NO_FACILITIES_PAGE[slug][:2]
            hold("ihs_service_units_absent", f"{name} Area",
                 "IHS_SERVICE_UNIT", why, IHS_BASE + path)
            continue
        fp = ok(f"ihs_facilities_{slug}.html")
        units, others = parse_ihs_service_units(fp, slug) if fp else ([], [])
        for lab, href in units:
            sc = re.sub(r"[^A-Z0-9]+", "_", lab.upper()).strip("_")
            rid = add_region("IHS_SERVICE_UNIT", f"{code}::{sc}", lab,
                             parent=area_id, url=href if href.startswith("http")
                             else IHS_BASE + href)
            m = re.search(r"healthcarefacilities/([a-z0-9\-]+)", href, re.I)
            if m:
                su_by_slug[(slug, m.group(1).lower())] = rid
            n_su += 1
        for lab, href in others:
            add_assign("HEALTH_FACILITY", "", lab, "IHS_AREA", area_id,
                       "FACILITY_ASSIGNMENT", "ihs_area_facility_page",
                       "high", src(f"ihs_facilities_{slug}.html",
                                   f"{IHS_BASE}/{slug}/healthcarefacilities/"),
                       notes=("listed on the IHS area's own facility page; "
                              "the area publishes no service unit for it"),
                       primary="1")
            n_fac_page[0] += 1
    print(f"  IHS service units named as such by IHS: {n_su}")
    print(f"  facility->IHS area from area facility pages: {n_fac_page[0]}")

    # Health facilities from the locations map.
    fac_n = fac_su = 0
    locp = ok("ihs_locations.html")
    if locp:
        slug2code = {s: c for c, s, _ in IHS_AREAS}
        for f in parse_ihs_facilities(locp):
            if not f["area_slug"]:
                hold("ihs_facility", f["name"], "IHS_AREA",
                     "IHS publishes no area-bearing URL for this facility",
                     f"{f['city']}, {f['state']}")
                continue
            code = slug2code.get(f["area_slug"])
            if not code:
                continue
            add_assign("HEALTH_FACILITY", "", f["name"], "IHS_AREA",
                       reg_by_key[("IHS_AREA", code)], "FACILITY_ASSIGNMENT",
                       "ihs_locations_facility_url", "high",
                       src("ihs_locations.html", f"{IHS_BASE}/locations/"),
                       notes=f"{f['city']}, {f['state']}", primary="1")
            fac_n += 1
            surid = su_by_slug.get((f["area_slug"], f["su_slug"]))
            if surid:
                add_assign("HEALTH_FACILITY", "", f["name"],
                           "IHS_SERVICE_UNIT", surid, "FACILITY_ASSIGNMENT",
                           "ihs_locations_facility_url", "high",
                           src("ihs_locations.html"),
                           notes=f"{f['city']}, {f['state']}", primary="1")
                fac_su += 1
    print(f"  facility->IHS area assignments: {fac_n} "
          f"(of which also to a service unit: {fac_su})")

    # tribe -> IHS area, only where the area publishes its own roster.
    n_ihs_t = n_ihs_h = 0
    slug2code = {s: c for c, s, _ in IHS_AREAS}
    for slug, (path, subj_type, basis) in IHS_TRIBE_PAGES.items():
        p = ok(f"ihs_tribes_{slug}.html")
        if not p:
            continue
        code = slug2code[slug]
        rid = reg_by_key[("IHS_AREA", code)]
        url = src(f"ihs_tribes_{slug}.html", IHS_BASE + path)
        t = p.read_text(encoding="utf-8", errors="replace")
        seen = set()
        for line in to_lines(main_block(t, 'id="site_content"')):
            if BOILERPLATE.search(line) or len(line) < 5 or len(line) > 90:
                continue
            if (line.endswith(":") or IHS_SECTION_HEADER.match(line)
                    or line.lower().startswith(("the ", "each ", "working ",
                                                "services ", "tribal health "))):
                continue
            if not re.search(r"tribe|nation|band|pueblo|community|village|"
                             r"rancheria|colony|council|corporation|"
                             r"association|consortium|health", line, re.I):
                continue
            if line in seen:
                continue
            seen.add(line)
            tid, canon, how = resolve_entity(line, spine)
            if not tid:
                hold(f"ihs_{subj_type.lower()}_roster", line, "IHS_AREA", how,
                     f"IHS {code} Area")
                n_ihs_h += 1
                continue
            # The page's own list mixes tribes with the organisations that
            # serve them - the Inter Tribal Council of Arizona sits among the
            # Arizona tribes. The resolved entity's CLASS decides what it is,
            # not the heading it appeared under.
            cls = next((r["entity_class"] for r in spine
                        if r["tribe_id"] == tid), "")
            subj = ("TRIBE" if cls in ("Federally recognized tribe",
                                       "Federally recognized Alaska Native Village",
                                       "State-recognized tribe")
                    else "NATIVE_ENTITY")
            add_assign(subj, tid, canon, "IHS_AREA", rid, basis,
                       f"ihs_area_roster+{how}", "high", url,
                       notes=f"listed by the IHS {code} Area on its own "
                             f"roster of the entities it serves", primary="1")
            n_ihs_t += 1
    print(f"  tribe->IHS area assignments: {n_ihs_t} "
          f"(unresolved names held: {n_ihs_h})")
    print("  NOTE: nine IHS areas publish no tribe roster. Those tribes carry "
          "NO IHS assignment rather than one inferred from a state.")

    # IHS regional statistics from area-page prose.
    for code, slug, name in IHS_AREAS:
        p = ok(f"ihs_area_{slug}.html")
        if not p:
            continue
        rid = reg_by_key[("IHS_AREA", code)]
        url = src(f"ihs_area_{slug}.html", f"{IHS_BASE}/{slug}/")
        txt = " ".join(to_lines(main_block(
            p.read_text(encoding="utf-8", errors="replace"),
            'id="site_content"')))
        for pat, oname, unit in [
            (r"([\d,]+)\s+Federally[- ]recognized Tribes",
             "federally_recognized_tribes_served", "count"),
            (r"([\d,]+)\s+Urban Indian Health programs",
             "urban_indian_health_programs", "count"),
            (r"([\d,]+)\s+P\.L\. 93-638 Title V compacts",
             "title_v_compacts", "count"),
            (r"([\d,]+)\s+Title I contracts", "title_i_contracts", "count"),
            (r"comprised of (\w+) regional areas referred to as service units",
             "service_units_stated", "count_word"),
        ]:
            m = re.search(pat, txt, re.I)
            if m:
                q = txt[max(0, m.start() - 90): m.end() + 90]
                add_obs("IHS_AREA", rid, code, oname, m.group(1).replace(",", ""),
                        unit, "2026", "1", "AGENCY_PUBLISHED", url, q)

    # -----------------------------------------------------------------
    # 3. HUD ONAP
    # -----------------------------------------------------------------
    print("\n[3] HUD ONAP")
    onap_url = src("hud_onap_offices.html", HUD_ONAP_OFFICES_URL)
    for code, name, official, city, st, pdf in HUD_ONAP:
        note = ("Southwest ONAP operates from two offices, Phoenix and "
                "Albuquerque; it is ONE area." if code == "SW" else
                "Administers the Native Hawaiian Housing Block Grant."
                if code == "HI" else "")
        add_region("HUD_ONAP_AREA", code, f"{name} ONAP", official,
                   city=city, st=st, url=onap_url, notes=note)
    print(f"  HUD ONAP areas: {len(HUD_ONAP)} "
          f"(hud.gov lists {len(HUD_ONAP)} areas across 8 office locations)")

    n_tribe = n_tdhe = n_hold = 0
    for code, name, official, city, st, pdf in HUD_ONAP:
        if not pdf:
            continue
        p = ok(f"hud_onap_{code}.pdf")
        if not p:
            continue
        rid = reg_by_key[("HUD_ONAP_AREA", code)]
        url = src(f"hud_onap_{code}.pdf", HUD_PDF_BASE + pdf)
        rows, doc_date = parse_hud_tdhe_pdf(p)
        sy = doc_date.split(", ")[-1] if doc_date else ""
        for ent_name, role, paired_tribe in rows:
            subj = "TRIBE" if role == "TRIBE" else "TDHE"
            # A TDHE IS NOT ITS TRIBE. The entity spine holds no tribally
            # designated housing entity - the only three rows mentioning
            # housing are an intertribal council and two CDFIs - so every
            # TDHE that "resolves" resolves by containment onto the tribal
            # government whose name it carries. "Blackfeet Housing Program"
            # landing on the Blackfeet Tribe would assert that the grantee
            # and the government are one legal person, which is the exact
            # collapse HUD's own list is careful to avoid. So TDHE rows keep
            # the published name, take no entity link, and queue as candidate
            # spine additions.
            tid, canon, how = ((None, None, "tdhe_not_on_entity_spine")
                               if subj == "TDHE"
                               else resolve_entity(ent_name, spine))
            if not tid:
                hold(f"hud_onap_{role.lower()}", ent_name, "HUD_ONAP_AREA",
                     how, f"{name} ONAP")
                n_hold += 1
                # A TDHE that is not on the entity spine is still a real
                # program recipient with a real ONAP assignment. Recording it
                # by NAME with an empty subject_id keeps the fact without
                # inventing an entity link.
                add_assign(subj, "", ent_name, "HUD_ONAP_AREA", rid,
                           "PROGRAM_RECIPIENT_ASSIGNMENT",
                           "hud_onap_tribe_tdhe_assignment_list", "medium",
                           url, notes=("named by HUD as a "
                                       f"{role.lower()} this ONAP administers; "
                                       "not resolved to a Cedar entity"),
                           primary="1", vstatus="OFFICIAL_UNLINKED",
                           sy=sy, related=paired_tribe)
                continue
            add_assign(subj, tid, canon, "HUD_ONAP_AREA", rid,
                       "PROGRAM_RECIPIENT_ASSIGNMENT",
                       f"hud_onap_tribe_tdhe_assignment_list+{how}", "high",
                       url, notes=(f"HUD lists this entity as a {role.lower()} "
                                   f"administered by {name} ONAP"),
                       primary="1", sy=sy, related=paired_tribe)
            if role == "TRIBE":
                n_tribe += 1
            else:
                n_tdhe += 1
    print(f"  tribe->ONAP assignments : {n_tribe}")
    print(f"  TDHE ->ONAP assignments : {n_tdhe}")
    print(f"  names held for review   : {n_hold}")

    # HUD ONAP program dollars, aggregated UP from award rows. This is the
    # safe direction: entity -> region. The forbidden direction, region ->
    # entity, is what `published_at_region_level=0` warns a reader about.
    aw = read_csv(AWARDS / "hud_onap_awards_parsed.csv")
    if aw:
        by_area = Counter()
        rows_area = Counter()
        name2area, id2area = {}, {}
        for a in assigns:
            if a["region_system_code"] == "HUD_ONAP_AREA":
                name2area.setdefault(norm(a["subject_name"]),
                                     a["administrative_region_id"])
                if a["subject_id"]:
                    id2area.setdefault(a["subject_id"],
                                       a["administrative_region_id"])
        unmatched = 0
        for r in aw:
            recip = r.get("recipient", "")
            rid = name2area.get(norm(recip))
            if not rid:
                # Second route: resolve the recipient to a Cedar entity, then
                # use that entity's own ONAP assignment. A grantee often
                # appears in an award list under a name the roster spells
                # differently, and the entity key bridges the two.
                tid, _, _ = resolve_entity(recip, spine)
                rid = id2area.get(tid) if tid else None
            if not rid:
                unmatched += 1
                continue
            try:
                by_area[rid] += float(r.get("amount") or 0)
            except ValueError:
                pass
            rows_area[rid] += 1
        code_of = {x["administrative_region_id"]: x["region_code"]
                   for x in regions}
        for rid, amt in by_area.items():
            add_obs("HUD_ONAP_AREA", rid, code_of[rid],
                    "cedar_hud_onap_award_dollars", f"{amt:.0f}", "usd", "",
                    "0", "CEDAR_AGGREGATION_FROM_ENTITY_ROWS",
                    "https://www.hud.gov/codetalk",
                    notes=("Aggregated UP from Cedar award rows whose recipient "
                           "matched a HUD-published ONAP roster name. NOT a "
                           "HUD-published regional total, and NOT divisible "
                           "back onto member entities."))
            add_obs("HUD_ONAP_AREA", rid, code_of[rid],
                    "cedar_hud_onap_award_rows", str(rows_area[rid]), "count",
                    "", "0", "CEDAR_AGGREGATION_FROM_ENTITY_ROWS",
                    "https://www.hud.gov/codetalk")
        print(f"  HUD award rows aggregated to an ONAP: "
              f"{sum(rows_area.values())}/{len(aw)} "
              f"({unmatched} recipients not on an ONAP roster)")

    # A top-level region with no headquarters is a gap in the registry, not a
    # detail. It is queued rather than filled from memory.
    for r in regions:
        if (r["region_system_code"] in ("BIA_REGION", "IHS_AREA",
                                        "HUD_ONAP_AREA")
                and not r["headquarters_city"]):
            hold("region_headquarters_missing", r["canonical_name"],
                 r["region_system_code"],
                 "the office's own pages publish no street address",
                 r["source_url"])

    # -----------------------------------------------------------------
    # 4. Systems registry
    # -----------------------------------------------------------------
    per_system = Counter(r["region_system_code"] for r in regions)
    systems = [
        dict(region_system_code="BIA_REGION", agency="Bureau of Indian Affairs",
             system_name="BIA Regional Office",
             level="1 - region", parent_system_code="",
             description=("Twelve regional offices that administer BIA "
                          "programme delivery to federally recognised tribes."),
             source_url="https://www.bia.gov/regional-offices",
             agency_declared_count=declared_regions or "twelve"),
        dict(region_system_code="BIA_AGENCY", agency="Bureau of Indian Affairs",
             system_name="BIA Agency / Field Office",
             level="2 - agency", parent_system_code="BIA_REGION",
             description=("Reservation-level BIA offices reporting to a "
                          "regional office. Often the more useful unit than "
                          "the region for reservation-level records."),
             source_url="https://www.bia.gov/regional-offices",
             agency_declared_count=declared_agencies or "83"),
        dict(region_system_code="IHS_AREA", agency="Indian Health Service",
             system_name="IHS Area", level="1 - area", parent_system_code="",
             description=("Twelve IHS areas. Drawn for health-service "
                          "delivery and NOT coterminous with BIA regions."),
             source_url="https://www.ihs.gov/locations/",
             agency_declared_count="12"),
        dict(region_system_code="IHS_SERVICE_UNIT",
             agency="Indian Health Service", system_name="IHS Service Unit",
             level="2 - service unit", parent_system_code="IHS_AREA",
             description=("Sub-area units of health-service delivery. IHS "
                          "publishes them per area alongside tribally "
                          "operated programmes; only entries IHS itself calls "
                          "a Service Unit are recorded here."),
             source_url="https://www.ihs.gov/locations/",
             agency_declared_count=""),
        dict(region_system_code="NIGC_REGION",
             agency="National Indian Gaming Commission",
             system_name="NIGC Region", level="1 - region",
             parent_system_code="",
             description=("NIGC gaming-enforcement regions. RESERVED - "
                          "populated by the NIGC build, not by script 85. "
                          "NIGC 'Phoenix' is not BIA 'Western' and not IHS "
                          "'Phoenix'."),
             source_url="https://www.nigc.gov/",
             agency_declared_count=""),
        dict(region_system_code="HUD_ONAP_AREA",
             agency="Department of Housing and Urban Development",
             system_name="ONAP Area Office", level="1 - area",
             parent_system_code="",
             description=("Office of Native American Programs area offices. "
                          "Assignments attach to the actual programme "
                          "recipient - a tribe, a TDHE or a housing "
                          "authority - which are different legal persons."),
             source_url=HUD_ONAP_OFFICES_URL,
             agency_declared_count="7 areas / 8 office locations"),
    ]
    for s in systems:
        lo, hi = ID_BLOCKS[s["region_system_code"]]
        s.update(
            region_system_version=SYSTEM_VERSION.get(s["region_system_code"],
                                                     "reserved"),
            # RENDERING a declared block boundary, not minting an id. The
            # zero-padding lives in the ID service so a caller cannot render
            # the same ordinal two different ways in two different places.
            id_block_start=cedar_ids.format_id("CEDAR-ADMREG", lo),
            id_block_end=cedar_ids.format_id("CEDAR-ADMREG", hi),
            n_regions_built=per_system.get(s["region_system_code"], 0),
            owned_by=("85_build_admin_region_crosswalk.py"
                      if s["region_system_code"] in OWNED_BY_THIS_SCRIPT
                      else "NIGC build (separate script)"),
            effective_start_year="2026", effective_end_year="",
            fetched_date=TODAY, built_date=TODAY)

    # -----------------------------------------------------------------
    # 5. DERIVED cross-system overlap. Never an equivalency.
    # -----------------------------------------------------------------
    by_sys = defaultdict(lambda: defaultdict(set))
    for a in assigns:
        if a["subject_type"] == "TRIBE" and a["subject_id"]:
            by_sys[a["region_system_code"]][a["subject_id"]].add(
                a["administrative_region_id"])
    name_of = {r["administrative_region_id"]: r["canonical_name"]
               for r in regions}
    overlap = []
    pairs = [("BIA_REGION", "IHS_AREA"), ("BIA_REGION", "HUD_ONAP_AREA"),
             ("IHS_AREA", "HUD_ONAP_AREA")]
    for s1, s2 in pairs:
        c = Counter()
        for tid, r1 in by_sys[s1].items():
            for r2 in by_sys[s2].get(tid, ()):
                for x in r1:
                    c[(x, r2)] += 1
        for (x, y), n in sorted(c.items(), key=lambda kv: -kv[1]):
            overlap.append({
                "system_a": s1, "administrative_region_id_a": x,
                "region_name_a": name_of.get(x, ""),
                "system_b": s2, "administrative_region_id_b": y,
                "region_name_b": name_of.get(y, ""),
                "n_shared_tribes": n,
                "relationship": "DERIVED_CO_OCCURRENCE",
                "warning": ("Derived from tribes both systems happen to "
                            "share. NOT an official equivalency; the two "
                            "agencies never mapped these boundaries onto "
                            "each other."),
                "built_date": TODAY})

    # -----------------------------------------------------------------
    # 6. Preserve anything the NIGC build already wrote, then write.
    # -----------------------------------------------------------------
    # Exact-duplicate rows arise where an agency publishes the same fact on
    # two pages - the Eastern Region's acreage on both its overview and its
    # agencies page, Metlakatla twice in the Alaska ONAP list. That is one
    # fact stated twice, not two facts, and it must not double a count.
    # Distinct assignments to DIFFERENT regions are kept: they are the
    # multiple memberships this layer exists to preserve.
    def dedupe(rows, keys, label):
        out, seen_k = [], set()
        for r in rows:
            k = tuple(r.get(x, "") for x in keys)
            if k in seen_k:
                continue
            seen_k.add(k)
            out.append(r)
        if len(out) != len(rows):
            print(f"  de-duplicated {label}: {len(rows)} -> {len(out)}")
        return out

    assigns = dedupe(assigns, ["subject_type", "subject_id", "subject_name",
                               "related_subject_name", "region_system_code",
                               "administrative_region_id",
                               "assignment_basis", "assignment_method"],
                     "assignments")
    observations = dedupe(observations, ["region_system_code",
                                         "administrative_region_id",
                                         "observation_name",
                                         "observation_value"], "observations")

    def foreign(rows, col="region_system_code"):
        return [r for r in rows if r.get(col) not in OWNED_BY_THIS_SCRIPT]

    prev_regions = foreign(read_csv(CLEAN / "admin_regions.csv"))
    prev_assign = foreign(read_csv(CLEAN / "admin_region_assignments.csv"))
    prev_obs = foreign(read_csv(CLEAN / "admin_regional_observations.csv"))
    prev_sys = [r for r in read_csv(CLEAN / "admin_region_systems.csv")
                if r.get("region_system_code") == "NIGC_REGION"
                and r.get("n_regions_built") not in ("", "0")]
    if prev_regions or prev_assign or prev_obs:
        print(f"\n  preserving rows from the NIGC build: "
              f"{len(prev_regions)} regions, {len(prev_assign)} assignments, "
              f"{len(prev_obs)} observations")
    if prev_sys:
        systems = [s for s in systems if s["region_system_code"] != "NIGC_REGION"]
        systems += prev_sys

    write_csv(CLEAN / "admin_region_systems.csv", systems, [
        "region_system_code", "agency", "system_name", "level",
        "parent_system_code", "region_system_version", "n_regions_built",
        "agency_declared_count", "id_block_start", "id_block_end",
        "effective_start_year", "effective_end_year", "owned_by",
        "description", "source_url", "fetched_date", "built_date"])

    write_csv(CLEAN / "admin_regions.csv", regions + prev_regions, [
        "administrative_region_id", "region_system_code", "region_code",
        "canonical_name", "official_name", "parent_administrative_region_id",
        "headquarters_city", "headquarters_state", "effective_start_date",
        "effective_end_date", "active_status", "source_url",
        "verification_status", "built_date", "region_system_version", "notes",
        "built_by_script"])

    write_csv(CLEAN / "admin_region_assignments.csv", assigns + prev_assign, [
        "assignment_id", "subject_type", "subject_id", "subject_name",
        "related_subject_name", "region_system_code",
        "administrative_region_id", "assignment_basis",
        "effective_start_date", "effective_end_date", "is_primary",
        "verification_status", "confidence", "source_url", "notes",
        "built_date", "region_system_version", "effective_start_year",
        "effective_end_year", "assignment_method", "fetched_date",
        "built_by_script"])

    write_csv(CLEAN / "admin_regional_observations.csv",
              observations + prev_obs, [
        "observation_id", "region_system_code", "administrative_region_id",
        "region_code", "observation_name", "observation_value",
        "observation_unit", "observation_year", "published_at_region_level",
        "observation_basis", "source_url", "source_quote", "notes",
        "fetched_date", "built_date", "built_by_script"])

    write_csv(CLEAN / "admin_region_overlap_derived.csv", overlap, [
        "system_a", "administrative_region_id_a", "region_name_a",
        "system_b", "administrative_region_id_b", "region_name_b",
        "n_shared_tribes", "relationship", "warning", "built_date"])

    # One row per distinct question. A TDHE that administers eleven villages
    # appears eleven times in HUD's list and is still ONE thing to rule on.
    dedup, seen_q = [], set()
    for u in unresolved:
        k = (u["item_type"], norm(u["name"]), u["region_system_code"],
             u["evidence"])
        if k in seen_q:
            continue
        seen_q.add(k)
        dedup.append(u)
    write_csv(REVIEW / "admin_region_unresolved.csv", dedup,
              ["item_type", "name", "region_system_code", "reason",
               "evidence", "queued_date"])

    qa(systems, regions + prev_regions, assigns + prev_assign,
       observations + prev_obs, spine, fed_tribes)


# ---------------------------------------------------------------------------
# QA
# ---------------------------------------------------------------------------
def qa(systems, regions, assigns, obs, spine, fed_tribes):
    print("\n=== quality checks ===")
    fails = []
    rid_index = {r["administrative_region_id"]: r for r in regions}

    # 1. every federally recognised tribe has a reviewed BIA region
    have = {a["subject_id"] for a in assigns
            if a["region_system_code"] == "BIA_REGION" and a["subject_id"]}
    missing = [r for r in fed_tribes if r["tribe_id"] not in have]
    print(f"  federally recognised entities with a BIA region : "
          f"{len(fed_tribes)-len(missing)}/{len(fed_tribes)}")
    if missing:
        fails.append(f"{len(missing)} federally recognised entities have no "
                     f"BIA region")
        with open(REVIEW / "admin_region_missing_bia.csv", "w",
                  encoding="utf-8", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["tribe_id", "canonical_name", "entity_class", "state",
                        "reason", "queued_date"])
            for r in missing:
                w.writerow([r["tribe_id"], r["canonical_name"],
                            r["entity_class"], r["state"],
                            "no BIA region published for this entity", TODAY])
        print(f"    -> review/admin_region_missing_bia.csv "
              f"({len(missing)} rows)")

    # 2. agencies roll up to a valid region; service units to a valid area
    for child, parent in (("BIA_AGENCY", "BIA_REGION"),
                          ("IHS_SERVICE_UNIT", "IHS_AREA")):
        kids = [r for r in regions if r["region_system_code"] == child]
        bad = [r for r in kids
               if rid_index.get(r["parent_administrative_region_id"], {})
               .get("region_system_code") != parent]
        print(f"  {child} rows rolling up to a valid {parent} : "
              f"{len(kids)-len(bad)}/{len(kids)}")
        if bad:
            fails.append(f"{len(bad)} {child} rows have no valid {parent}")

    # 3. every assignment has a source
    nosrc = [a for a in assigns if not a.get("source_url")]
    print(f"  assignments carrying a source_url : "
          f"{len(assigns)-len(nosrc)}/{len(assigns)}")
    if nosrc:
        fails.append(f"{len(nosrc)} assignments have no source_url")

    # 4. inferred stays distinguishable from official
    b = Counter(a["assignment_basis"] for a in assigns)
    print("  assignment_basis:")
    for k, v in b.most_common():
        print(f"    {v:6,}  {k}")
    inferred = b.get("GEOGRAPHIC_INFERENCE", 0)
    print(f"  GEOGRAPHIC_INFERENCE rows : {inferred} "
          f"(distinguishable by construction)")

    # 5. multiple assignments preserved
    multi = Counter()
    for a in assigns:
        if a["subject_id"]:
            multi[(a["subject_id"], a["region_system_code"])] += 1
    n_multi = sum(1 for v in multi.values() if v > 1)
    print(f"  subject x system pairs holding MORE THAN ONE region : {n_multi} "
          f"(preserved, not overwritten)")

    # 6. no regional statistic mislabelled as entity-level
    bad_obs = [o for o in obs if not o.get("administrative_region_id")]
    entity_cols = {"subject_id", "tribe_id", "entity_id"}
    leak = entity_cols & set(obs[0].keys()) if obs else set()
    print(f"  regional observations : {len(obs)}, all region-keyed: "
          f"{not bad_obs}, entity keys present: {sorted(leak) or 'none'}")
    if bad_obs or leak:
        fails.append("a regional observation carries or lacks the wrong key")
    pub = Counter(o["published_at_region_level"] for o in obs)
    print(f"    agency-published at region level : {pub.get('1',0)}")
    print(f"    Cedar aggregation up from rows   : {pub.get('0',0)} "
          f"(flagged, never divisible back down)")

    # 7. Nothing is dropped for being inactive, unrecognised or unlinked.
    #
    # The spine carries no `terminated` status to test against, so the
    # meaningful measure is whether subjects OUTSIDE the current federally
    # recognised roster survive the build. They do, in two forms: entities on
    # the spine that are not currently recognised tribes, and names an agency
    # published that resolve to no Cedar entity at all - kept with an empty
    # subject_id rather than deleted, because an unlinked fact is still a
    # fact. This build never removes a row on the ground that a subject has
    # stopped being current.
    fed_ids = {r["tribe_id"] for r in fed_tribes}
    non_current = sum(1 for a in assigns
                      if a["subject_id"] and a["subject_id"] not in fed_ids)
    unlinked = sum(1 for a in assigns if not a["subject_id"])
    print(f"  assignments on subjects outside the current federally "
          f"recognised roster : {non_current}")
    print(f"  assignments retained by NAME with no entity link           "
          f"  : {unlinked}")
    dated = sum(1 for a in assigns if a.get("effective_start_year")
                or a.get("effective_start_date"))
    print(f"  assignments carrying an effective start                    "
          f"  : {dated}  (the rest are dated by region_system_version + "
          f"fetched_date)")

    # 8. ID blocks respected
    stray = [r for r in regions
             if not (ID_BLOCKS[r["region_system_code"]][0]
                     <= int(r["administrative_region_id"].split("-")[-1])
                     <= ID_BLOCKS[r["region_system_code"]][1])]
    print(f"  region IDs inside their system's block : "
          f"{len(regions)-len(stray)}/{len(regions)}")
    if stray:
        fails.append(f"{len(stray)} region IDs fall outside their block")

    print("\n" + ("  ALL CHECKS PASS" if not fails else "  ATTENTION:"))
    for f in fails:
        print(f"    - {f}")


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"
    if mode in ("fetch", "all"):
        fetch()
    if mode in ("build", "all"):
        build()
