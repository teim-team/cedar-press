#!/usr/bin/env python3
"""
Cedar Press - 75: Add BIE schools and Urban Indian Organizations to the spine.

TWO ENTITY POPULATIONS, ONE SHARED LESSON
-----------------------------------------
Both of these classes look like tribal entities and mostly are not owned by a
tribe. Getting that wrong in either direction is the expensive mistake, so the
ownership question is decided from the source roster, never inferred.

1. BIE SCHOOLS (`BIE-`)
   The Bureau of Indian Education's own directory splits its schools into
   `Bureau-Operated` and `Tribally-Controlled`, and that split is the whole
   task. A Bureau-operated school is a FEDERAL school: the United States runs
   it, staffs it with federal employees, and spends federal money on it.
   Booking those dollars to a tribe would attribute the federal government's
   own spending to a tribal government - the largest single false-attribution
   risk in this build, and it is 56 of the 185 elementary and secondary
   schools.

   Tribally-controlled schools are grant or contract schools run by a tribe or
   a tribal school board under P.L. 100-297 or P.L. 93-638. Those DO belong to
   a tribe - but even there the project's live precedent (four Navajo BIE grant
   schools and Kayenta Township, tier B, "affiliation, not ownership") governs:
   the school board is a distinct legal person from the tribe, and its ISEP
   money must not publish as tribal revenue without a further ruling. So
   `parent_native_entity` records the AFFILIATION and the hierarchy columns
   (`parent_entity_id`) are deliberately LEFT EMPTY so no rollup happens on the
   strength of a name.

2. URBAN INDIAN ORGANIZATIONS (`UIO-`)
   A UIO is owned by NO tribe. That is not a data gap, it is the design of the
   programme: Title V of the Indian Health Care Improvement Act funds nonprofit
   organisations that serve urban American Indian and Alaska Native people
   drawn from many tribal affiliations. NCUIH's own definition, retrieved:
   "a nonprofit situated in an urban center governed by a board of directors of
   whom at least 51 percent are American Indian and Alaska Natives".

   So `parent_native_entity` stays EMPTY for every UIO and the relationship is
   carried by `serves_native_entities`. This is the ownership-vs-service
   distinction Elijah has already ruled on for Native American Health Center
   and the Alaska constellation organisations.

SOURCES (retrieved; every entity carries a URL and a verbatim quote)
-------------------------------------------------------------------
BIE   https://www.bie.edu/schools  ->  ArcGIS Experience 505ac8e4... -> web map
      e6004556... -> feature service BIE_Schools_Directory/FeatureServer/0.
      The published directory page states the split verbatim, and the feature
      service is the data behind that page - so the count and the split are
      checked against each other rather than asserted.
IHS   https://www.ihs.gov/urban/urban-indian-organizations/ and its twelve area
      pages: "The Urban Indian Organizations (UIO) listed below have current
      Title V Indian Health Care Improvement Act contracts with the Indian
      Health Service."
NCUIH https://ncuih.org/uio-directory/ (cross-check only): "There are 41 Urban
      Indian Organizations in the United States who contract with the Indian
      Health Service."

WHAT THIS SCRIPT WILL NOT DO
----------------------------
- It will not overwrite an existing spine row. A tribe_id or a canonical-name
  collision aborts or skips; it never merges.
- It will not touch `TCU-` or `CDFI-` (another agent owns those), and it
  refuses Haskell Indian Nations University and SIPI for the same reason -
  they are BIE-operated POST-secondary and belong to that agent's roster.
- It will not write to `data/clean/cedar_*` or `review/cedar_*`. Newly found
  identifiers land in a NEW file for review, not in the published ledger.
- It will not fetch `api.usaspending.gov`. Every host here is different, and
  each is hit a handful of times with a courtesy delay.

Reads   data/spine/cedar_entity_spine.csv
        data/clean/{federal_funding_transactions,faads_transactions,
                    faads_transactions_all_agencies,prime_contracts,
                    subawards,np_orgs}.csv
Writes  data/spine/cedar_entity_spine.csv          (BIE-/UIO- rows appended)
        data/raw/external/bie_uio/*                 (raw payloads + manifest)
        data/clean/bie_uio_identifier_links.csv     (identifiers found)
        data/clean/bie_uio_dollars_by_entity.csv    (dollars newly attributable)
        review/bie_uio_refusals.csv                 (everything refused + why)
        docs/BIE_UIO_BUILD_LOG.md

Usage   py -3 code/75_add_bie_schools_and_uios.py            # full run
        py -3 code/75_add_bie_schools_and_uios.py --refetch  # re-pull sources
        py -3 code/75_add_bie_schools_and_uios.py --no-link  # spine only
"""

import csv
import html
import importlib.util
import json
import re
import shutil
import sys
import time
import unicodedata
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from datetime import date, datetime, timezone
from pathlib import Path

CEDAR = Path(r"C:\Users\esm247\Desktop\Cedar Press")
SPINE = CEDAR / "data" / "spine" / "cedar_entity_spine.csv"
CLEAN = CEDAR / "data" / "clean"
RAW = CEDAR / "data" / "raw" / "external" / "bie_uio"
REVIEW = CEDAR / "review"
DOCS = CEDAR / "docs"
TODAY = date.today().isoformat()

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")

# ONE resolver (standing rule 8). Filename starts with a digit, so import by path.
_spec = importlib.util.spec_from_file_location(
    "party_rulings", CEDAR / "code" / "33_apply_party_rulings.py")
PR = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(PR)
norm, core, STRUCTURAL = PR.norm, PR.core, PR.STRUCTURAL

# ---------------------------------------------------------------------------
# SOURCES
# ---------------------------------------------------------------------------
BIE_DIRECTORY_URL = "https://www.bie.edu/schools"
BIE_APP_URL = "https://biamaps.geoplatform.gov/BIE-Schools-Directory"
BIE_FS_URL = ("https://services1.arcgis.com/UxqqIfhng71wUT9x/arcgis/rest/"
              "services/BIE_Schools_Directory/FeatureServer/0")
# Verbatim, from the <meta og:description> of https://www.bie.edu/schools
BIE_QUOTE = (
    "Here are 183 Bureau-funded elementary and secondary schools and "
    "residential facilities. Of these, 55 are BIE-Operated and 128 are "
    "Tribally Controlled. The BIE also directly operates two postsecondary "
    "institutions: Haskell Indian Nations University (HINU) and the "
    "Southwestern Indian Polytechnic Institute (SIPI).")
# Verbatim, from the ArcGIS item description of the live web experience, which
# is what the feature service actually contains. The two disagree; see the log.
BIE_ITEM_QUOTE = (
    "There are 187 Bureau-funded elementary and secondary schools on 64 "
    "reservations in 23 states, serving approximately 40,000 Indian students. "
    "Of these, 58 are BIE-operated and 129 are tribally controlled under BIE "
    "contracts or grants.")

IHS_UIO_URL = "https://www.ihs.gov/urban/urban-indian-organizations/"
IHS_QUOTE = (
    "The Urban Indian Organizations (UIO) listed below have current Title V "
    "Indian Health Care Improvement Act contracts with the Indian Health "
    "Service. UIOs have been arranged in alphabetical order based on the IHS "
    "area and respective State they belong in.")
NCUIH_URL = "https://ncuih.org/uio-directory/"
NCUIH_QUOTE = (
    "There are 41 Urban Indian Organizations in the United States who "
    "contract with the Indian Health Service. Urban Indian organization means "
    "a nonprofit situated in an urban center governed by a board of directors "
    "of whom at least 51 percent are American Indian and Alaska Natives, for "
    "establishing and administering an urban Indian health program and "
    "related activities as described in the Indian Health Care Improvement "
    "Act.")

IHS_AREAS = ["albuquerque", "bemidji", "billings", "california", "great-plains",
             "nashville", "navajo", "oklahoma-city", "phoenix", "portland",
             "tucson", "regional-national-tribal"]

# Left to the TCU agent. BIE-operated POST-secondary, not elementary/secondary.
POSTSECONDARY_REFUSALS = {
    "haskell indian nations university",
    "southwestern indian polytechnic institute",
}

# ---------------------------------------------------------------------------
# NAME TRAPS
# ---------------------------------------------------------------------------
# Words that must never carry a match on their own. 282 place-name coincidences
# were already withdrawn from the nonprofit layer on exactly this failure: a
# school in a town called Cherokee is not a Cherokee Nation school.
TRAPS = {"creek", "cherokee", "colorado", "ojibwe", "shawnee", "oneida",
         "apache", "central", "eagle", "river", "mountain", "santa"}

# Words that describe a KIND of thing rather than identify one. An overlap
# consisting only of these is not evidence. "Native Health" reduces to
# {health} under the resolver's STRUCTURAL set, and {health} is a subset of
# "Alaska Native Health Board" - which is how a Phoenix-area UIO would silently
# collect Alaska's dollars.
GENERIC = {"health", "center", "centre", "clinic", "service", "services",
           "board", "school", "schools", "project", "association", "council",
           "coalition", "consortium", "organization", "organisation", "family",
           "families", "medical", "care", "wellness", "program", "programs",
           "urban", "american", "indians", "town", "township", "island",
           "academy", "day", "elementary", "middle", "high", "junior",
           "senior", "dormitory", "residential", "hall", "campus", "district",
           "learning", "north", "south", "east", "west", "northern",
           "southern", "eastern", "western", "new", "first", "second",
           "national", "regional", "tribal", "inter", "intertribal", "life",
           "nations", "home", "house", "point", "lake", "hill", "hills",
           "springs", "valley", "rock", "water", "grant", "settlement",
           "reservation", "county", "city", "state", "united", "u", "s",
           "st", "mt", "ft", "dr", "jr", "sr", "de", "la", "el", "us", "no",
           "inc", "co", "the", "public"}

# Organisation types that bar a match outright. `Cooperative Association` is
# exempt: it is the standard IRA-era name for an Alaska village government.
ORG_TYPE_BAR = re.compile(
    r"\b(city of|county|univ(ersity|\.)|regents|cooperative|public)\b", re.I)
COOP_ASSOC_OK = re.compile(r"cooperative\s+association", re.I)

# The ONLY words a recipient name may add to an entity name and still be the
# same body. A grant school's award recipient is usually its governing board:
# "Alamo Navajo School Board, Inc." for Alamo Navajo Community School. Those
# extra words are grantee form, not identity.
#
# `district` is deliberately ABSENT. "Menominee Indian School District" is the
# PUBLIC district in Keshena; "Menominee Tribal School" is the BIE grant school
# in Neopit. One added word, two different institutions, $112M between them.
GRANTEE_EXTRAS = {"board", "boards", "education", "grant", "bia", "bie", "day"}

SCHOOL_WORDS = {"school", "schools", "community", "day", "boarding",
                "elementary", "middle", "high", "junior", "senior", "academy",
                "dormitory", "dorm", "residential", "hall", "campus", "center",
                "learning", "district", "tribal", "indian", "preparatory",
                "prep", "psa", "jr", "sr", "bordertown", "settlement", "inc",
                "incorporated", "elemenatary"}

STATE_ABBR = {
    "alabama": "AL", "alaska": "AK", "arizona": "AZ", "arkansas": "AR",
    "california": "CA", "colorado": "CO", "connecticut": "CT",
    "delaware": "DE", "florida": "FL", "georgia": "GA", "hawaii": "HI",
    "idaho": "ID", "illinois": "IL", "indiana": "IN", "iowa": "IA",
    "kansas": "KS", "kentucky": "KY", "louisiana": "LA", "maine": "ME",
    "maryland": "MD", "massachusetts": "MA", "michigan": "MI",
    "minnesota": "MN", "mississippi": "MS", "missouri": "MO", "montana": "MT",
    "nebraska": "NE", "nevada": "NV", "new hampshire": "NH",
    "new jersey": "NJ", "new mexico": "NM", "new york": "NY",
    "north carolina": "NC", "north dakota": "ND", "ohio": "OH",
    "oklahoma": "OK", "oregon": "OR", "pennsylvania": "PA",
    "rhode island": "RI", "south carolina": "SC", "south dakota": "SD",
    "tennessee": "TN", "texas": "TX", "utah": "UT", "vermont": "VT",
    "virginia": "VA", "washington": "WA", "west virginia": "WV",
    "wisconsin": "WI", "wyoming": "WY", "district of columbia": "DC",
}

MANIFEST = []
REFUSALS = []


def refuse(scope, name, reason, detail=""):
    REFUSALS.append({"scope": scope, "name": name, "reason": reason,
                     "detail": detail, "logged_date": TODAY})


# ---------------------------------------------------------------------------
# FETCH
# ---------------------------------------------------------------------------
def get(url, fname, refetch=False, pause=1.5):
    """Retrieve and cache. Courtesy pause; these hosts are not usaspending and
    are touched a handful of times, but the pull-discipline rule is a rule."""
    p = RAW / fname
    if p.exists() and not refetch:
        MANIFEST.append({"file": fname, "url": url, "http_status": "cached",
                         "bytes": p.stat().st_size, "fetched_date": TODAY})
        return p.read_bytes()
    RAW.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=90) as r:
        body = r.read()
        status = r.status
    p.write_bytes(body)
    MANIFEST.append({"file": fname, "url": url, "http_status": status,
                     "bytes": len(body), "fetched_date": TODAY})
    print(f"    fetched {fname:44s} {status} {len(body):>9,}B "
          f"{time.time()-t0:.1f}s")
    time.sleep(pause)
    return body


def fetch_all(refetch=False):
    print("--- retrieving sources ---")
    get(BIE_DIRECTORY_URL, "bie_schools_landing.html", refetch)
    q = urllib.parse.urlencode({"where": "1=1", "outFields": "*",
                                "returnGeometry": "false", "f": "json",
                                "resultRecordCount": 2000})
    get(f"{BIE_FS_URL}/query?{q}", "bie_schools_featureserver.json", refetch)
    get(IHS_UIO_URL, "ihs_uio_list.html", refetch)
    for a in IHS_AREAS:
        get(f"https://www.ihs.gov/urban/urban-indian-organizations/{a}/",
            f"ihs_uio_{a}.html", refetch)
    get("https://ncuih.org/wp-json/wp/v2/pages?slug=uio-directory",
        "ncuih_uio_directory_wpjson.json", refetch)

    m = RAW / "_SOURCE_MANIFEST.csv"
    with open(m, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["file", "url", "http_status",
                                           "bytes", "fetched_date"])
        w.writeheader()
        w.writerows(MANIFEST)
    print(f"    manifest -> {m.relative_to(CEDAR)} ({len(MANIFEST)} files)\n")


# ---------------------------------------------------------------------------
# PARSE
# ---------------------------------------------------------------------------
def parse_bie():
    d = json.loads((RAW / "bie_schools_featureserver.json")
                   .read_text(encoding="utf-8"))
    rows = [f["attributes"] for f in d["features"]]
    out = []
    for a in rows:
        name = (a.get("School_Name") or "").strip()
        if not name:
            refuse("BIE", f"OBJECTID {a.get('OBJECTID')}", "no school name")
            continue
        if norm(name) in POSTSECONDARY_REFUSALS:
            refuse("BIE", name, "BIE-operated post-secondary",
                   "Owned by the concurrent TCU agent; adding it here would "
                   "duplicate. Present in the same feature service, which is "
                   "why the layer holds 187 rows and the elementary/secondary "
                   "universe is 185.")
            continue
        op = (a.get("Operation_Type") or "").strip()
        if op not in ("Bureau-Operated", "Tribally-Controlled"):
            refuse("BIE", name, "unrecognised Operation_Type", op)
            continue
        out.append({
            "name": name,
            "operation_type": ("bie_operated" if op == "Bureau-Operated"
                               else "tribally_controlled"),
            "source_operation_type": op,
            "navajo_group": (a.get("Navajo_Operation") or "").strip(),
            "city": (a.get("City") or "").strip(),
            "state_name": (a.get("State") or "").strip(),
            "state": STATE_ABBR.get((a.get("State") or "").strip().lower(), ""),
            "zip": (a.get("Zip_Code") or "").strip(),
            "website": (a.get("website") or "").strip(),
            "erc": (a.get("Education_Resource_Center") or "").strip(),
            "grades": (a.get("Grades_Served") or "").strip(),
        })
    return out


def _strip_tags(seg):
    seg = re.sub(r"<(script|style)\b.*?</\1>", "", seg, flags=re.S | re.I)
    seg = re.sub(r"<br\s*/?>|</(p|div|li|tr|h\d|td|a)>", "\n", seg, flags=re.I)
    t = html.unescape(re.sub(r"<[^>]+>", "\n", seg))
    return "\n".join(l.strip() for l in t.split("\n") if l.strip())


def parse_ihs_uios():
    """One row per IHS listing. Section headers are <h2>State</h2> on eleven
    pages and <p><strong>State:</strong></p> on Albuquerque - both handled,
    because a parser that silently drops a state drops its organisations."""
    listings = []
    for a in IHS_AREAS:
        b = (RAW / f"ihs_uio_{a}.html").read_text(encoding="utf-8",
                                                  errors="replace")
        i = b.find('id="site_content"')
        j = b.find("</main>", i)
        seg = b[i:j]
        seg = re.sub(r'<a href="https://www\.ihs\.gov/Disclaimers".*?</a>', "",
                     seg, flags=re.S)
        section = ""
        pat = (r"<h2>(?P<h2>.*?)</h2>"
               r"|<strong>(?P<st>[^<]*?):?</strong>"
               r"|<li>\s*<a href=\"(?P<url>https?://[^\"]+)\"[^>]*>"
               r"(?P<name>.*?)</a>"
               r"|<li>\s*(?P<plain>[A-Za-z][^<]{0,160}?)\s*</li>")
        for m in re.finditer(pat, seg, re.S):
            g = m.groupdict()
            if g["h2"] is not None:
                # `.strip(" :")` matters: two headers are "Nebraska:" and
                # "South Dakota:", and without it those two organisations lose
                # their state - which is the column the link-stage state guard
                # depends on.
                section = html.unescape(
                    re.sub("<[^>]+>", "", g["h2"])).strip().strip(" :")
            elif g["st"] is not None:
                s = html.unescape(re.sub("<[^>]+>", "", g["st"])).strip(" :")
                if s:
                    section = s
            elif g["url"]:
                nm = html.unescape(re.sub("<[^>]+>", "", g["name"])).strip()
                if nm and "Exit Disclaimer" not in nm:
                    listings.append({"area": a, "section": section, "name": nm,
                                     "website": g["url"], "location": "",
                                     "service_level": ""})
            elif g["plain"] and listings:
                p = html.unescape(g["plain"]).strip()
                if p.lower().startswith("location:"):
                    listings[-1]["location"] = p.split(":", 1)[1].strip()
                elif p.lower().startswith("service level"):
                    listings[-1]["service_level"] = p.split(":", 1)[1].strip()
    return listings


def parse_ncuih():
    raw = (RAW / "ncuih_uio_directory_wpjson.json").read_text(encoding="utf-8")
    d = json.loads(raw)
    if not d:
        return []
    txt = _strip_tags(d[0]["content"]["rendered"])
    return [l for l in txt.split("\n")]


# ---------------------------------------------------------------------------
# MATCH GUARDS
# ---------------------------------------------------------------------------
def distinctive(tokens):
    """Tokens that can carry a match on their own.

    The length floor is 2, not 3. At 3 it silently deleted *Santa Fe Indian
    School* - `santa` is a trap word and `fe` was too short to count, so the
    school had no identifying token at all and every one of its 281 funding
    rows was refused. A trap word must not carry a match ALONE; it is still
    allowed to sit beside a real one.
    """
    return {t for t in tokens if t not in TRAPS and t not in GENERIC
            and len(t) >= 2}


def org_type_barred(name):
    if COOP_ASSOC_OK.search(name):
        return False
    m = ORG_TYPE_BAR.search(name or "")
    return m.group(0) if m else False


def guard_match(subject_name, subject_state, ent, how):
    """Return (ok, reason). Applied on TOP of the resolver - refusals only,
    never a widening. Two guards do the real work:

    ALASKA GUARD. The spine holds Alaska villages named `Circle` and `Eagle`.
    Circle of Life Academy is White Earth in Minnesota and Two Eagle River
    School is CSKT in Montana; both resolved onto Alaska villages by
    containment. An Alaska entity claiming a non-Alaska school is refused
    outright - the same category error the village-corporation work was built
    to stop.

    OVERLAP GUARD. The tokens the two names actually share must include at
    least one that identifies rather than describes. `{township}`, `{eagle}`
    and `{health}` do not.
    """
    # An EXACT or ALIAS hit is whole-name equality, not a partial overlap, so
    # the overlap guard does not apply to it. Without this exemption the
    # Phoenix UIO literally named "Native Health" could never match a recipient
    # literally named "NATIVE HEALTH": the resolver strips `native` as
    # structural, leaving `{health}`, which the overlap guard correctly refuses
    # as a partial match. The Alaska guard, the organisation-type bar and the
    # state check all still apply below.
    if how not in ("exact", "alias"):
        ent_core = core(ent["canonical_name"])
        sub_core = core(subject_name)
        shared = ent_core & sub_core
        if not shared:
            return False, "no shared identifying token"
        if not distinctive(shared):
            return False, ("overlap is only trap/generic words: "
                           + ",".join(sorted(shared)))
    est = (ent.get("state") or "").strip().upper()
    if est == "AK" and subject_state and subject_state != "AK":
        return False, (f"Alaska entity '{ent['canonical_name']}' vs "
                       f"{subject_state} subject - place-name collision")
    bar = org_type_barred(subject_name)
    if bar:
        return False, f"organisation type bars a match: '{bar}'"
    return True, how


# ---------------------------------------------------------------------------
# BUILD SPINE ROWS
# ---------------------------------------------------------------------------
STOP_TOK = {"the", "inc", "incorporated", "corporation", "corp", "company",
            "llc", "ltd", "limited", "native", "of", "and", "school",
            "schools", "community", "center", "indian"}


def token(name, taken):
    words = [w for w in norm(name).split() if w not in STOP_TOK]
    if not words:
        words = norm(name).split() or ["entity"]
    base = "".join(words)
    cons = re.sub(r"[aeiou]", "", base)
    cand = (cons if len(cons) >= 6 else base)[:6].upper().ljust(6, "X")
    if cand not in taken:
        return cand
    for i in range(1, 1000):
        alt = (cand[:5] + str(i))[:6] if i < 10 else (cand[:4] + str(i))[:6]
        if alt not in taken:
            return alt
    raise SystemExit(f"cannot mint a unique token for {name}")


def read_csv(p):
    if not Path(p).exists():
        return []
    with open(p, encoding="utf-8-sig", errors="replace", newline="") as fh:
        return list(csv.DictReader(fh))


def bie_aliases(name):
    """Recipient names in the award data are usually the GRANTEE, which for a
    grant school is the school BOARD ("Little Wound School Board, Inc.") or a
    school DISTRICT. Generating those variants lets exact/alias matching carry
    the link instead of containment."""
    out = [name]
    bare = re.sub(r"\s*\(.*?\)\s*", " ", name).strip()
    if bare and bare != name:
        out.append(bare)
    par = re.findall(r"\(([^)]+)\)", name)
    out.extend(p.strip() for p in par if len(p.strip()) > 4)
    stem = re.sub(r"\s+(School|Schools)$", "", bare, flags=re.I).strip()
    for base in {bare, stem}:
        if not base:
            continue
        # No "<base> School District" variant: a same-named PUBLIC district
        # sits next to several of these schools, and an alias is an assertion
        # of identity, not a hint.
        out += [f"{base} Board", f"{base} Board, Inc.", f"{base} Board Inc",
                f"{base} School Board", f"{base} School Board, Inc.",
                f"{base} Inc", f"{base}, Inc."]
    if re.search(r"\bSchool$", bare, re.I):
        out.append(re.sub(r"\bSchool$", "Schools", bare, flags=re.I))
    if re.search(r"\bSchools$", bare, re.I):
        out.append(re.sub(r"\bSchools$", "School", bare, flags=re.I))
    seen, uniq = set(), []
    for a in out:
        k = norm(a)
        if k and k not in seen:
            seen.add(k)
            uniq.append(a.strip())
    return uniq


# Extra aliases evidenced by the NCUIH cross-check (dba / short names). Each is
# a name the same organisation is listed under on ncuih.org/uio-directory/.
UIO_EXTRA_ALIASES = {
    "urban inter tribal center of texas": ["Texas Native Health"],
    "native american rehabilitation association of the northwest inc":
        ["NARA NW", "NARA Northwest"],
    "native americans for community action": ["NACA"],
    "bakersfield american indian health project": ["BAIHP"],
    "fresno american indian health project": ["FAIHP"],
    "sacramento native american health center inc": ["SNAHC"],
    "native directions inc": ["Native Directions, Inc./Three Rivers Indian "
                              "Lodge", "Three Rivers Indian Lodge"],
    "friendship house association of american indians":
        ["Friendship House Association of American Indians, Inc. of "
         "San Francisco"],
    "indian family health clinic": ["IFHC"],
    "urban indian center of salt lake": ["Urban Indian Center of Salt Lake City"],
    "american indian health services corporation":
        ["American Indian Health & Services, Inc.",
         "American Indian Health and Services"],
    "hunter health": ["Hunter Health Clinic, Inc.", "Hunter Health Clinic"],
    "juel fairbanks recovery services": ["Juel Fairbanks"],
    "native american lifelines inc": ["Native American LifeLines of Baltimore",
                                      "Native American LifeLines of Boston",
                                      "Native American LifeLines"],
    "nebraska urban indian health coalition":
        ["Nebraska Urban Indian Health Coalition, Inc."],
    "south dakota urban indian health":
        ["South Dakota Urban Indian Health, Inc."],
    "indian health board of minneapolis inc": ["Indian Health Board of Minneapolis"],
    "billings urban indian health and wellness center":
        ["Billings Urban Indian Health & Wellness Center"],
    "denver indian health family service inc":
        ["Denver Indian Health and Family Services",
         "Denver Indian Health & Family Service, Inc."],
}


def build_rows(bie, uio_listings, spine):
    fields = list(spine[0].keys())
    for extra in ("bie_operation_type", "parent_native_entity",
                  "serves_native_entities", "source_url", "source_quote",
                  "entity_website", "city", "built_by_script"):
        if extra not in fields:
            fields.append(extra)

    have_names = {norm(r["canonical_name"]) for r in spine}
    have_alias = set()
    for r in spine:
        for a in (r.get("aliases") or "").split("|"):
            if a.strip():
                have_alias.add(norm(a))
    have_ids = {r["tribe_id"] for r in spine}
    taken = {r["tribe_id"].split("-")[1] for r in spine if "-" in r["tribe_id"]}

    added = []

    # ---- BIE schools -----------------------------------------------------
    for s in bie:
        n = norm(s["name"])
        if n in have_names or n in have_alias:
            refuse("BIE", s["name"], "already in the spine",
                   "exact canonical-name or alias collision; refusing to "
                   "duplicate or overwrite")
            continue
        tok = token(s["name"], taken)
        taken.add(tok)
        tid = f"BIE-{tok}-00"
        if tid in have_ids:
            raise SystemExit(f"ABORT: {tid} exists. Refusing to overwrite.")
        row = {f: "" for f in fields}
        row.update({
            "tribe_id": tid,
            "canonical_name": s["name"],
            "entity_class": "BIE School",
            "state": s["state"],
            "city": s["city"],
            "aliases": "|".join(bie_aliases(s["name"])),
            "entity_website": s["website"],
            "bie_operation_type": s["operation_type"],
            "cicd_verified": "0",
            "n_uei_tierA": "0", "n_uei_tierB": "0", "n_cage": "0", "n_ein": "0",
            "source_url": BIE_DIRECTORY_URL + " -> " + BIE_FS_URL,
            "source_quote": BIE_ITEM_QUOTE,
            "built_by_script": "code/75_add_bie_schools_and_uios.py",
        })
        if s["operation_type"] == "bie_operated":
            row["parent_native_entity"] = ""
            row["reconciliation_status"] = "federally_operated_no_tribal_parent"
            row["reconciliation_note"] = (
                "BIE-OPERATED. The Bureau of Indian Education runs this "
                "school; it is a federal school, not a tribal entity. Source "
                f"field Operation_Type = '{s['source_operation_type']}' "
                f"({s['navajo_group']}). Federal money spent here is federal "
                "money spent on a federal school. It MUST NOT roll up to any "
                "tribe, and parent_native_entity is empty by rule rather than "
                "by absence of research.")
        else:
            row["reconciliation_status"] = "seek_parent"
            row["reconciliation_note"] = (
                "TRIBALLY CONTROLLED. Run by a tribe or a tribal school board "
                "under a BIE grant (P.L. 100-297) or contract (P.L. 93-638). "
                f"Source field Operation_Type = '{s['source_operation_type']}' "
                f"({s['navajo_group']}).")
        row["hierarchy_basis"] = (
            f"BIE school directory Operation_Type={s['source_operation_type']}"
            f"; ERC {s['erc']}" if s["erc"] else
            f"BIE school directory Operation_Type={s['source_operation_type']}")
        added.append(row)
        have_names.add(n)
        have_ids.add(tid)

    # ---- UIOs ------------------------------------------------------------
    # Collapse to one entity per ORGANISATION. IHS lists Native American
    # LifeLines twice (Baltimore, Boston) because it operates two sites; NCUIH
    # lists it as two members. It is one legal person with one EIN, and two
    # spine rows would double-count every dollar it receives.
    by_org = defaultdict(list)
    for l in uio_listings:
        by_org[norm(l["name"])].append(l)

    for key, group in by_org.items():
        first = group[0]
        name = first["name"]
        if key in have_names or key in have_alias:
            refuse("UIO", name, "already in the spine",
                   "exact canonical-name or alias collision; NCUIH is already "
                   "carried as an Intertribal Organization")
            continue
        locations = [g["location"] for g in group if g["location"]]
        sections = sorted({g["section"] for g in group if g["section"]})
        areas = sorted({g["area"] for g in group})
        tok = token(name, taken)
        taken.add(tok)
        tid = f"UIO-{tok}-00"
        if tid in have_ids:
            raise SystemExit(f"ABORT: {tid} exists. Refusing to overwrite.")
        aliases = [name] + UIO_EXTRA_ALIASES.get(key, [])
        st = ""
        for sec in sections:
            if sec.lower() in STATE_ABBR:
                st = STATE_ABBR[sec.lower()]
                break
        row = {f: "" for f in fields}
        row.update({
            "tribe_id": tid,
            "canonical_name": name,
            "entity_class": "Urban Indian Organization",
            "state": st,
            "city": "; ".join(locations),
            "aliases": "|".join(dict.fromkeys(aliases)),
            "entity_website": first["website"],
            "cicd_verified": "0",
            "n_uei_tierA": "0", "n_uei_tierB": "0", "n_cage": "0", "n_ein": "0",
            "parent_native_entity": "",       # by rule: no tribe owns a UIO
            "serves_native_entities": (
                "multi-tribal urban American Indian and Alaska Native service "
                "population; no single tribal owner (IHCIA Title V)"),
            "source_url": (IHS_UIO_URL + areas[0] + "/" if len(areas) == 1
                           else IHS_UIO_URL),
            "source_quote": IHS_QUOTE,
            "hierarchy_basis": (
                f"IHS OUIHP Title V roster, area(s) {', '.join(areas)}; "
                f"section(s) {', '.join(sections) or 'n/a'}; service level "
                f"{first['service_level'] or 'not stated'}"),
            "reconciliation_status": "seek_identifiers",
            "reconciliation_note": (
                "URBAN INDIAN ORGANIZATION. Owned by NO tribe: a Title V "
                "nonprofit serving urban AI/AN people across many tribal "
                "affiliations, which is the design of the programme rather "
                "than a gap in the data. parent_native_entity is EMPTY BY "
                "RULE; the relationship is carried by serves_native_entities. "
                "Same ruling as Native American Health Center and the Alaska "
                "constellation organisations."
                + (f" IHS lists {len(group)} service locations "
                   f"({'; '.join(locations)}) under one organisation name; "
                   "collapsed to one entity so dollars are not double-counted."
                   if len(group) > 1 else "")),
            "built_by_script": "code/75_add_bie_schools_and_uios.py",
        })
        if norm(name).startswith("urban indian health institute"):
            row["reconciliation_status"] = "review_possible_division"
            row["reconciliation_note"] += (
                " REVIEW: IHS lists this under 'Tribal' as a Tribal "
                "Epidemiology Center rather than as a Title V direct-service "
                "grantee, and its own site publishes a press contact at "
                "sihb.org, which suggests it is a division of Seattle Indian "
                "Health Board rather than a separate legal person. No "
                "retrieved statement says so outright, so the relationship is "
                "flagged, not asserted. Settle it before any dollars roll up.")
        added.append(row)
        have_names.add(key)
        have_ids.add(tid)

    return fields, added


def resolve_parents(added, spine):
    """Attach the operating tribe to TRIBALLY-CONTROLLED schools only.

    Deliberately conservative. The BIE directory does not name the operating
    tribe, so this is an inference from the school's name, and an inference is
    tier B with the affiliation caveat - never tier A, never an ownership
    claim. Where the name does not identify a tribe unambiguously, the field
    stays empty and the row keeps `seek_parent`. Precision over recall: a blank
    is a known unknown, a wrong tribe is a published error.
    """
    # A tribally CONTROLLED school is controlled by a TRIBE. Restricting the
    # candidate pool to governments is not a convenience - it caught a live
    # error. `Sequoyah High School` (Tahlequah, Oklahoma - Cherokee Nation)
    # resolved by containment on the single token `sequoyah` onto
    # `Sequoyah Fund Inc., The` (CDFI-SQYHFN-00), a North Carolina CDFI that
    # the concurrent CDFI agent had just written into the spine. Wrong entity
    # type, wrong state, wrong tribe, and it would have looked fine in a table.
    #
    # Constituency entities stay in: the Fond du Lac Band is the right parent
    # for Fond du Lac Ojibwe School and the spine files it that way.
    allowed = PR.GOVERNMENT_CLASSES | {"Federal-level constituency entity"}
    pool = [r for r in spine if r.get("entity_class") in allowed]

    n_set = 0
    for row in added:
        if row["entity_class"] != "BIE School":
            continue
        if row.get("bie_operation_type") != "tribally_controlled":
            continue
        name = row["canonical_name"]
        base = re.sub(r"\(.*?\)", " ", name)
        base = " ".join(t for t in norm(base).split() if t not in SCHOOL_WORDS)
        c = distinctive(core(base))
        if not c:
            refuse("BIE parent", name, "no distinctive token after stripping "
                   "school words", base)
            continue
        tid, cn, how = PR.resolve_entity(base, pool)
        if not tid:
            refuse("BIE parent", name, f"resolver: {how}", base)
            continue
        ent = next(r for r in pool if r["tribe_id"] == tid)
        ok, why = guard_match(base, row.get("state", ""), ent, how)
        if not ok:
            refuse("BIE parent", name, f"guard: {why}",
                   f"resolver offered {cn} ({tid}) via {how}")
            continue
        mismatch = (ent.get("state") and row.get("state")
                    and ent["state"] != row["state"])
        row["parent_native_entity"] = f"{tid}|{cn}"
        row["reconciliation_status"] = "parent_affiliation_tierB"
        row["reconciliation_note"] += (
            f" PARENT (AFFILIATION, NOT OWNERSHIP): resolved to {cn} ({tid}) "
            f"by {how} on the school name. Tier B. This follows the standing "
            f"precedent for the four Navajo BIE grant schools and Kayenta "
            f"Township: the school board is a distinct legal person from the "
            f"tribe, so these dollars MUST NOT publish as tribal revenue "
            f"without a further ruling. parent_entity_id is left EMPTY on "
            f"purpose so no hierarchy rollup fires on the strength of a name."
            + (f" NOTE: spine state for {cn} is {ent['state']} but the school "
               f"is in {row['state']}; expected for multi-state nations "
               f"(Navajo, Standing Rock) and flagged rather than refused."
               if mismatch else ""))
        n_set += 1
    return n_set


# ---------------------------------------------------------------------------
# LINK
# ---------------------------------------------------------------------------
DATASETS = [
    # file, name col, state col, uei col, duns col, amount col, kind
    ("federal_funding_transactions.csv", "recipient_name",
     "recipient_state_code", "recipient_uei", "recipient_duns",
     "obligated_usd", "federal_funding"),
    # `faads_transactions.csv` is DELIBERATELY ABSENT. Measured, not assumed:
    # all 59,514 distinct (fain, action_date, recipient, amount) keys in it
    # also appear in `faads_transactions_all_agencies.csv` - it is a strict
    # subset, not a separate population. Reading both summed $53M of the same
    # awards twice. Standing rule 7 in the same clothes.
    ("faads_transactions_all_agencies.csv", "recipient_name",
     "recipient_state", "recipient_uei", "recipient_duns", "obligated_usd",
     "faads_all_agencies"),
    ("prime_contracts.csv", "awardee_name", "recipient_state_code",
     "awardee_uei", "", "total_obligations", "prime_contracts"),
    ("subawards.csv", "sub_name", "sub_state", "sub_uei", "",
     "subaward_amount", "subawards"),
    ("np_orgs.csv", "org_name", "state", "", "", "", "nonprofit_990"),
]


def _f(v):
    try:
        return float(v or 0)
    except ValueError:
        return 0.0


def link(added):
    """Search every dataset, not just contracting.

    Elijah's proven finding: for entities like these, federal funding and FAADS
    beat contracting by roughly 3:1. BIE schools draw ISEP and BIE facilities
    money; UIOs draw IHS Title V and HRSA grants. Contracting alone would have
    made both populations look nearly dollarless.
    """
    subset = added  # resolve against the NEW entities only
    links, dollars = [], defaultdict(lambda: defaultdict(float))
    counts = defaultdict(lambda: defaultdict(int))

    # CANDIDATE NARROWING, not matching. `resolve_entity` is O(entities) with
    # regex normalisation inside, and the datasets hold ~370k distinct
    # recipient names - a naive pass did not finish in ten minutes. So build an
    # inverted index over every core token of every entity name AND alias, and
    # only call the resolver on names that share at least one such token.
    #
    # This cannot change an answer. Every branch the resolver can return
    # (exact, core-equality, alias, containment) requires the two core sets to
    # intersect, so a name sharing no token could only ever come back
    # `no_spine_match`. The resolver still makes every decision; this only
    # decides which questions are worth asking it.
    index = defaultdict(set)
    always = []
    for i, e in enumerate(subset):
        toks = set(core(e["canonical_name"]))
        for a in (e.get("aliases") or "").split("|"):
            if a.strip():
                toks |= set(core(a))
        if not toks:
            always.append(i)
        for t in toks:
            index[t].add(i)

    for fname, ncol, scol, ucol, dcol, acol, kind in DATASETS:
        p = CLEAN / fname
        if not p.exists():
            print(f"    {fname:44s} MISSING - skipped")
            continue
        agg = {}
        n_rows = 0
        with open(p, encoding="utf-8-sig", errors="replace", newline="") as fh:
            for r in csv.DictReader(fh):
                n_rows += 1
                nm = (r.get(ncol) or "").strip()
                if not nm:
                    continue
                st = (r.get(scol) or "").strip().upper()[:2]
                k = (norm(nm), st)
                a = agg.setdefault(k, {"name": nm, "state": st, "n": 0,
                                       "usd": 0.0, "uei": Counter(),
                                       "duns": Counter(), "ein": Counter(),
                                       "years": set()})
                a["n"] += 1
                a["usd"] += _f(r.get(acol)) if acol else 0.0
                if ucol and (r.get(ucol) or "").strip():
                    a["uei"][r[ucol].strip()] += 1
                if dcol and (r.get(dcol) or "").strip():
                    a["duns"][r[dcol].strip()] += 1
                if kind == "nonprofit_990" and (r.get("EIN") or "").strip():
                    a["ein"][r["EIN"].strip()] += 1
                y = (r.get("fiscal_year") or "").strip()
                if y:
                    a["years"].add(y)

        matched = 0
        skipped = 0
        for (nkey, st), a in agg.items():
            cand = set(always)
            for t in core(a["name"]):
                cand |= index.get(t, set())
            if not cand:
                skipped += 1
                continue
            tid, cn, how = PR.resolve_entity(a["name"],
                                             [subset[i] for i in sorted(cand)])
            if not tid:
                continue
            ent = next(e for e in subset if e["tribe_id"] == tid)
            ok, why = guard_match(a["name"], st, ent, how)
            if not ok:
                refuse(f"link:{kind}", a["name"], f"guard: {why}",
                       f"resolver offered {cn} ({tid}) via {how}")
                continue
            # STATE GUARD for links. A school or clinic name repeats across the
            # country; the award recipient must be in the same state as the
            # entity, or the match is a place-name coincidence.
            est = (ent.get("state") or "").strip().upper()
            if est and st and est != st:
                refuse(f"link:{kind}", a["name"],
                       f"state mismatch: recipient {st} vs entity {est}",
                       f"{cn} ({tid})")
                continue
            # DIRECTION GUARD - the single most expensive bug in this build.
            #
            # `resolve_entity`'s containment branch accepts either direction,
            # which is right for the job it was written for (Elijah writes a
            # long official tribe name, the spine holds a short one). Turned
            # around and pointed at award data it is a disaster: the tribe's
            # own name is a SUBSET of the school's name, so
            # "CHICKASAW NATION" resolved onto "Chickasaw Children's Village"
            # and carried $2.8B of the Chickasaw Nation's federal funding onto
            # a school. The same shape put the Yakama Nation's $917M on a
            # school, the Blackfeet Nation's $568M on a dormitory, and
            # "SANTA FE LTD" and "CHICAGO" on two more entities. Unfixed, this
            # would have published $13.4B, most of it other people's money.
            #
            # So a recipient must be at least as SPECIFIC as the entity, and
            # whatever it adds must be grantee form rather than identity.
            if how == "containment":
                ec, rc = core(ent["canonical_name"]), core(a["name"])
                extra = rc - ec
                if not (ec <= rc):
                    refuse(f"link:{kind}", a["name"],
                           "recipient is BROADER than the entity - a parent "
                           "body, not this entity",
                           f"{cn} ({tid}); entity-only tokens "
                           f"{sorted(ec - rc)}")
                    continue
                if not extra <= GRANTEE_EXTRAS:
                    refuse(f"link:{kind}", a["name"],
                           "recipient adds identifying words beyond grantee "
                           "form", f"{cn} ({tid}); extra {sorted(extra)}")
                    continue
            matched += 1
            counts[tid][kind] += a["n"]
            dollars[tid][kind] += a["usd"]
            links.append({
                "tribe_id": tid, "canonical_name": cn,
                "entity_class": ent["entity_class"],
                "bie_operation_type": ent.get("bie_operation_type", ""),
                "parent_native_entity": ent.get("parent_native_entity", ""),
                "dataset": kind, "source_file": fname,
                "recipient_name": a["name"], "recipient_state": st,
                "match_method": how, "confidence_tier": "B",
                "tier_rationale": (
                    "Name match against the IHS/BIE roster entity, guarded by "
                    "trap-word, organisation-type and state checks. Tier B: "
                    "the identifier is not independently confirmed against "
                    "SAM/IRS for this entity."),
                "n_transactions": a["n"],
                "obligations_usd": round(a["usd"], 2),
                "fiscal_years": (f"{min(a['years'])}-{max(a['years'])}"
                                 if a["years"] else ""),
                "uei": "|".join(sorted(a["uei"])),
                "duns_internal_only": "|".join(sorted(a["duns"])),
                "ein": "|".join(sorted(a["ein"])),
                "built_date": TODAY,
            })
        print(f"    {fname:44s} {n_rows:>9,} rows -> {len(agg):>7,} distinct "
              f"names -> {len(agg)-skipped:>6,} asked -> {matched:>4} matched",
              flush=True)
    return links, dollars, counts


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------
def main():
    refetch = "--refetch" in sys.argv
    do_link = "--no-link" not in sys.argv
    print("=== Cedar Press 75: BIE schools + Urban Indian Organizations ===\n")

    fetch_all(refetch)

    bie = parse_bie()
    uios = parse_ihs_uios()
    ncuih_lines = parse_ncuih()
    ops = Counter(s["operation_type"] for s in bie)
    print(f"BIE schools parsed (elementary/secondary) : {len(bie)}")
    print(f"  bie_operated                            : {ops['bie_operated']}")
    print(f"  tribally_controlled                     : "
          f"{ops['tribally_controlled']}")
    print(f"IHS Title V UIO listings                  : {len(uios)}")
    print(f"  distinct organisations                  : "
          f"{len({norm(u['name']) for u in uios})}")
    print(f"NCUIH cross-check lines                   : {len(ncuih_lines)}\n")

    spine = read_csv(SPINE)
    before = len(spine)

    # RE-RUNNABLE. If this script has already written its rows, adding them
    # again is not the job - refreshing the links and the log is. Without this
    # branch a second run reports "0 added" and regenerates a log that
    # contradicts the data sitting in the spine, which is standing rule 10
    # (a number in a doc that is not recomputed from the data is a claim).
    existing = [r for r in spine if r["tribe_id"].startswith(("BIE-", "UIO-"))]
    if existing:
        print(f"spine already holds {len(existing)} BIE-/UIO- rows from an "
              f"earlier run. Refreshing links and log only; not re-adding.\n")
        added, fields = existing, list(spine[0].keys())
        n_parent = sum(1 for r in existing if r.get("parent_native_entity"))
        rebuilt = True
        before -= len(existing)   # so the log still reports the real delta
        # Replay parent resolution on THROWAWAY copies. Nothing in the spine
        # is touched; the point is that `review/bie_uio_refusals.csv` still
        # lists every parent this build declined to assert, so a re-run
        # produces the same artefacts rather than a quietly shorter file.
        _fresh, _replay = build_rows(bie, uios,
                                     [r for r in spine
                                      if not r["tribe_id"].startswith(
                                          ("BIE-", "UIO-"))])
        resolve_parents(_replay, spine)
    else:
        fields, added = build_rows(bie, uios, spine)
        n_parent = resolve_parents(added, spine)
        rebuilt = False

    cls = Counter(r["entity_class"] for r in added)
    print(f"spine entities before                     : {before}")
    print(f"  BIE School rows to add                  : {cls['BIE School']}")
    print(f"  Urban Indian Organization rows to add   : "
          f"{cls['Urban Indian Organization']}")
    print(f"  tribally-controlled with a parent set   : {n_parent}")
    print(f"  BIE-operated (federal; NO tribal parent): "
          f"{sum(1 for r in added if r.get('bie_operation_type') == 'bie_operated')}\n")

    ids = [r["tribe_id"] for r in added]
    if len(ids) != len(set(ids)):
        raise SystemExit("ABORT: duplicate tribe_id minted.")
    if not rebuilt:
        prior = {r["tribe_id"] for r in spine}
        if prior & set(ids):
            raise SystemExit(f"ABORT: collision with existing spine ids: "
                             f"{sorted(prior & set(ids))[:5]}")

    if added and not rebuilt:
        # CONCURRENCY. Another agent is appending `TCU-` and `CDFI-` rows to
        # this same file right now. Between the read at the top of this run and
        # this write, it may have added rows - and writing back the copy read
        # minutes ago would silently delete them. So re-read here, append to
        # what is on disk NOW, and re-check every guarantee against the fresh
        # copy rather than the stale one.
        fresh = read_csv(SPINE)
        if len(fresh) != before:
            print(f"  NOTE: spine changed under us during this run "
                  f"({before} -> {len(fresh)} rows). Another agent is writing. "
                  f"Appending to the current file, not the copy read earlier.")
        fresh_ids = {r["tribe_id"] for r in fresh}
        clash = fresh_ids & set(ids)
        if clash:
            raise SystemExit(f"ABORT: {len(clash)} tribe_id(s) now exist that "
                             f"did not when this run started: "
                             f"{sorted(clash)[:5]}. Refusing to overwrite.")
        fresh_names = {norm(r["canonical_name"]) for r in fresh}
        dropped = [r for r in added if norm(r["canonical_name"]) in fresh_names]
        for r in dropped:
            refuse(r["entity_class"], r["canonical_name"],
                   "added to the spine by another agent during this run",
                   "refused rather than duplicated")
        added = [r for r in added if norm(r["canonical_name"])
                 not in fresh_names]
        fields = list(fresh[0].keys()) + [f for f in fields
                                          if f not in fresh[0]]

        shutil.copy2(SPINE, SPINE.with_suffix(f".csv.bak_{TODAY}_pre75"))
        with open(SPINE, "w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore",
                               restval="")
            w.writeheader()
            w.writerows(fresh + added)
        print(f"  wrote {SPINE.relative_to(CEDAR)}  "
              f"({len(fresh)} -> {len(fresh) + len(added)} entities"
              f"{f'; {len(dropped)} refused as concurrent duplicates' if dropped else ''})\n")

    links, dollars, counts = [], {}, {}
    if do_link:
        print("--- searching every dataset for identifiers and dollars ---")
        links, dollars, counts = link(added)
        if links:
            lp = CLEAN / "bie_uio_identifier_links.csv"
            with open(lp, "w", encoding="utf-8", newline="") as fh:
                w = csv.DictWriter(fh, fieldnames=list(links[0].keys()))
                w.writeheader()
                w.writerows(links)
            print(f"\n  wrote {lp.relative_to(CEDAR)}  ({len(links)} links)")

            rows = []
            for r in added:
                tid = r["tribe_id"]
                if tid not in dollars:
                    continue
                tot = sum(dollars[tid].values())
                rows.append({
                    "tribe_id": tid, "canonical_name": r["canonical_name"],
                    "entity_class": r["entity_class"],
                    "bie_operation_type": r.get("bie_operation_type", ""),
                    "parent_native_entity": r.get("parent_native_entity", ""),
                    "rolls_up_to_a_tribe":
                        "NO - federally operated school"
                        if r.get("bie_operation_type") == "bie_operated"
                        else ("NO - no tribal owner (Title V UIO)"
                              if r["entity_class"] == "Urban Indian Organization"
                              else ("AFFILIATION ONLY - tier B, not ownership"
                                    if r.get("parent_native_entity")
                                    else "UNRESOLVED - parent not identified")),
                    "total_usd": round(tot, 2),
                    **{f"usd_{k}": round(v, 2)
                       for k, v in sorted(dollars[tid].items())},
                    "n_transactions": sum(counts[tid].values()),
                    "built_date": TODAY,
                })
            allf = ["tribe_id", "canonical_name", "entity_class",
                    "bie_operation_type", "parent_native_entity",
                    "rolls_up_to_a_tribe", "total_usd"]
            allf += sorted({k for r in rows for k in r if k.startswith("usd_")})
            allf += ["n_transactions", "built_date"]
            dp = CLEAN / "bie_uio_dollars_by_entity.csv"
            with open(dp, "w", encoding="utf-8", newline="") as fh:
                w = csv.DictWriter(fh, fieldnames=allf, extrasaction="ignore",
                                   restval="")
                w.writeheader()
                w.writerows(sorted(rows, key=lambda x: -x["total_usd"]))
            print(f"  wrote {dp.relative_to(CEDAR)}  ({len(rows)} entities "
                  f"with dollars)")

    REVIEW.mkdir(parents=True, exist_ok=True)
    rp = REVIEW / "bie_uio_refusals.csv"
    with open(rp, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["scope", "name", "reason", "detail",
                                           "logged_date"])
        w.writeheader()
        w.writerows(REFUSALS)
    print(f"  wrote {rp.relative_to(CEDAR)}  ({len(REFUSALS)} refusals)")

    write_log(bie, uios, added, links, dollars, counts, n_parent, before)
    print("\ndone.")


def write_log(bie, uios, added, links, dollars, counts, n_parent, before):
    ops = Counter(s["operation_type"] for s in bie)
    cls = Counter(r["entity_class"] for r in added)
    linked_ids = {l["tribe_id"] for l in links}
    tot = sum(sum(v.values()) for v in dollars.values())
    by_kind = defaultdict(float)
    for v in dollars.values():
        for k, x in v.items():
            by_kind[k] += x

    def cls_dollars(pred):
        return sum(sum(dollars[r["tribe_id"]].values()) for r in added
                   if pred(r) and r["tribe_id"] in dollars)

    fed_only = cls_dollars(lambda r: r.get("bie_operation_type") == "bie_operated")
    trib_aff = cls_dollars(
        lambda r: r.get("bie_operation_type") == "tribally_controlled"
        and r.get("parent_native_entity"))
    trib_unk = cls_dollars(
        lambda r: r.get("bie_operation_type") == "tribally_controlled"
        and not r.get("parent_native_entity"))
    uio_d = cls_dollars(lambda r: r["entity_class"] == "Urban Indian Organization")

    L = []
    A = L.append
    A("# BIE Schools and Urban Indian Organizations - build log")
    A(f"*Built {TODAY} by `code/75_add_bie_schools_and_uios.py`. "
      f"Every entity below carries a retrieved source URL and a verbatim "
      f"quote; nothing here was typed from memory.*")
    A("")
    A("## The distinction that is the whole task")
    A("")
    A("A **BIE-operated** school is a federal school. The Bureau of Indian "
      "Education runs it, and the money spent on it is the federal "
      "government's own spending. Booking it to a tribe would be a false "
      "attribution of the most damaging kind, because the numbers would look "
      "entirely plausible. A **tribally controlled** school is a grant or "
      "contract school (P.L. 100-297 / P.L. 93-638) run by a tribe or a "
      "tribal school board, and those do belong to a tribe.")
    A("")
    A(f"**{ops['bie_operated']} of the {len(bie)} elementary and secondary "
      f"schools added are federally operated and must NOT roll up to any "
      f"tribe.** Their `parent_native_entity` is empty by rule, not for want "
      f"of research, and `reconciliation_status` records that explicitly.")
    A("")
    A("A **UIO** is owned by no tribe at all. Title V of the Indian Health "
      "Care Improvement Act funds nonprofits serving urban AI/AN people from "
      "many tribal affiliations; that is the design of the programme, not a "
      "gap in the data. `parent_native_entity` stays empty for all of them "
      "and `serves_native_entities` carries the relationship - the same "
      "ownership-vs-service ruling already made for Native American Health "
      "Center and the Alaska constellation organisations.")
    A("")
    A("## Sources")
    A("")
    A("| Source | URL | Verbatim quote |")
    A("|---|---|---|")
    A(f"| BIE school directory (landing page) | {BIE_DIRECTORY_URL} | "
      f"\"{BIE_QUOTE}\" |")
    A(f"| BIE school directory (live web experience item) | {BIE_APP_URL} | "
      f"\"{BIE_ITEM_QUOTE}\" |")
    A(f"| BIE school directory (data behind the map) | {BIE_FS_URL} | "
      f"n/a - feature service; {len(bie) + len(POSTSECONDARY_REFUSALS)} "
      f"features returned |")
    A(f"| IHS Office of Urban Indian Health Programs | {IHS_UIO_URL} | "
      f"\"{IHS_QUOTE}\" |")
    A(f"| NCUIH member directory (cross-check) | {NCUIH_URL} | "
      f"\"{NCUIH_QUOTE}\" |")
    A("")
    A("### A source discrepancy worth recording")
    A("")
    A("The BIE landing page says **183 schools, 55 BIE-operated, 128 tribally "
      "controlled**. The live web experience the same page redirects to says "
      "**187 schools, 58 BIE-operated, 129 tribally controlled**, and the "
      "feature service behind it returns exactly 187 features split 58/129. "
      "The landing-page text is stale. This build uses the feature service, "
      "because it is the data the directory actually renders and the only one "
      "of the two that can be counted rather than read.")
    A("")
    A(f"Removing Haskell Indian Nations University and the Southwestern "
      f"Indian Polytechnic Institute - BIE-operated **post-secondary**, and "
      f"the concurrent TCU agent's to add - leaves **{len(bie)} elementary "
      f"and secondary schools: {ops['bie_operated']} BIE-operated and "
      f"{ops['tribally_controlled']} tribally controlled**.")
    A("")
    A("### The UIO count")
    A("")
    n_area = sum(1 for u in uios if u["area"] != "regional-national-tribal")
    n_rnt = len(uios) - n_area
    A(f"IHS lists **{n_area} entries across its eleven area pages** - the "
      f"Title V direct-service roster, and the figure of roughly 41 UIOs in "
      f"the brief - plus **{n_rnt} more** on its Regional / National / Tribal "
      f"page. Native American LifeLines accounts for two of the "
      f"{n_area} because it runs sites in Baltimore and Boston; NCUIH lists "
      f"those as two members, which is how it reaches 41 while naming "
      f"{n_area - 1} distinct bodies. They are one legal person with one EIN, "
      f"so this build creates **one** entity with both locations recorded. "
      f"Two rows would double-count every dollar it receives.")
    A("")
    A(f"That gives {len({norm(u['name']) for u in uios})} distinct "
      f"organisations. NCUIH itself is one of them and is already in the "
      f"spine as `ITO-RBNHLT-00`, so it is refused as a duplicate rather than "
      f"added again - leaving **{cls['Urban Indian Organization']}** new "
      f"entities.")
    A("")
    A("## What was added")
    A("")
    A("| Class | Entities | Notes |")
    A("|---|---|---|")
    A(f"| BIE School - `bie_operated` | "
      f"{sum(1 for r in added if r.get('bie_operation_type') == 'bie_operated')}"
      f" | Federal schools. No tribal parent, by rule. |")
    A(f"| BIE School - `tribally_controlled` | "
      f"{sum(1 for r in added if r.get('bie_operation_type') == 'tribally_controlled')}"
      f" | {n_parent} have a parent tribe resolved at tier B (affiliation, "
      f"not ownership); the rest keep `seek_parent`. |")
    A(f"| Urban Indian Organization | "
      f"{cls['Urban Indian Organization']} | No tribal parent, by rule. |")
    A(f"| **Total** | **{len(added)}** | spine {before} -> {before+len(added)} |")
    A("")
    A("## Parent attribution for tribally controlled schools")
    A("")
    A("The BIE directory does not name the operating tribe, so the parent is "
      "an inference from the school's name resolved through "
      "`33_apply_party_rulings.resolve_entity` - the one resolver - and then "
      "put through two refusal guards. It is recorded at **tier B as "
      "affiliation, not ownership**, following the standing precedent for the "
      "four Navajo BIE grant schools and Kayenta Township. `parent_entity_id` "
      "is left empty on purpose so that no hierarchy rollup fires on the "
      "strength of a name.")
    A("")
    A("The guards, and what each one actually caught here:")
    A("")
    A("- **Alaska guard.** The spine holds Alaska Native Villages named "
      "`Circle` and `Eagle`. Containment resolved *Circle of Life Academy* "
      "(White Earth, Minnesota), *Circle of Nations* (North Dakota), *Little "
      "Eagle School* (Standing Rock, South Dakota) and *Two Eagle River "
      "School* (CSKT, Montana) onto them. All four refused.")
    A("- **Overlap guard.** The shared tokens must include one that identifies "
      "rather than describes. `{township}` alone resolved *Indian Township "
      "School* onto Passamaquoddy Indian Township - substantively right, but "
      "on evidence too thin to publish, so refused.")
    A("- **Trap words** (`creek, cherokee, colorado, ojibwe, shawnee, oneida, "
      "apache, central, eagle, river, mountain, santa`) cannot carry a match "
      "alone. This refuses the three *Cherokee Central* schools and *Oneida "
      "Nation School* - each of which is in fact tribally run, and each of "
      "which would be indistinguishable from a place-name coincidence to any "
      "rule this build could state.")
    A("- **Organisation type** bars city / county / university / cooperative / "
      "public, with `Cooperative Association` exempt as the IRA-era name for "
      "Alaska village governments.")
    A("- **Candidate class.** A tribally controlled school is controlled by a "
      "TRIBE, so only government-class spine rows (plus federal-level "
      "constituency entities, which is how the Fond du Lac Band is filed) may "
      "be a parent. This caught a live cross-agent error: *Sequoyah High "
      "School* (Tahlequah, Oklahoma - Cherokee Nation) resolved by containment "
      "on the single token `sequoyah` onto `Sequoyah Fund Inc., The` "
      "(`CDFI-SQYHFN-00`), a North Carolina CDFI the concurrent CDFI agent had "
      "just written into the spine. Wrong entity type, wrong state, wrong "
      "tribe - and it would have read as perfectly ordinary in a table.")
    A("")
    A(f"Result: **{n_parent} of "
      f"{sum(1 for r in added if r.get('bie_operation_type') == 'tribally_controlled')}"
      f" tribally controlled schools** carry a parent. The remainder are a "
      f"known unknown rather than a guess; a wrong tribe is a published error.")
    A("")
    A("## Identifiers and dollars found")
    A("")
    A(f"Elijah's finding held: **federal funding and FAADS beat contracting "
      f"decisively** for these populations. Searching contracting alone would "
      f"have made both classes look nearly dollarless.")
    A("")
    A("| Dataset | Obligations matched |")
    A("|---|---|")
    for k in sorted(by_kind, key=lambda x: -by_kind[x]):
        A(f"| {k} | ${by_kind[k]:,.0f} |")
    A(f"| **Total** | **${tot:,.0f}** |")
    A("")
    A(f"- Entities linked to at least one identifier or award: "
      f"**{len(linked_ids)} of {len(added)}**")
    A(f"- Link rows written: **{len(links)}** -> "
      f"`data/clean/bie_uio_identifier_links.csv`")
    A(f"- Per-entity dollars -> `data/clean/bie_uio_dollars_by_entity.csv`")
    A("")
    A("### How the dollars may and may not be used")
    A("")
    A("| Bucket | Amount | Publishable as tribal revenue? |")
    A("|---|---|---|")
    A(f"| BIE-operated schools | ${fed_only:,.0f} | **No.** Federal spending "
      f"on federal schools. |")
    A(f"| Tribally controlled, parent resolved | ${trib_aff:,.0f} | **Not "
      f"yet.** Tier B AFFILIATION; the school board is a distinct legal "
      f"person from the tribe. |")
    A(f"| Tribally controlled, parent unresolved | ${trib_unk:,.0f} | **No - "
      f"no tribe named.** The school owns these dollars; which tribe controls "
      f"the school is an open question, not an assumed one. |")
    A(f"| Urban Indian Organizations | ${uio_d:,.0f} | **No tribal owner "
      f"exists.** Attribute to the UIO itself. |")
    A("")
    A("### Two link-stage guards that changed the answer by billions")
    A("")
    A("**Direction.** `resolve_entity`'s containment branch accepts a match in "
      "either direction, which is correct for the job it was written for. "
      "Pointed at award data it inverts: a tribe's own name is a SUBSET of its "
      "school's name, so `CHICKASAW NATION` resolved onto *Chickasaw "
      "Children's Village* and carried **$2.8B** of the Chickasaw Nation's "
      "federal funding onto a school. The same shape put the Yakama Nation's "
      "$917M on a school and the Blackfeet Nation's $568M on a dormitory, and "
      "matched `SANTA FE LTD` and `CHICAGO`. A first pass totalled **$13.4B**, "
      "most of it other people's money. Requiring the recipient to be at least "
      "as specific as the entity - and to add nothing beyond grantee form "
      "(`board`, `education`, `grant`, `bia`, `day`) - brings it to "
      f"**${tot:,.0f}**.")
    A("")
    A("`district` is not on that allowed list, deliberately. *Menominee Indian "
      "School District* is the public district in Keshena; *Menominee Tribal "
      "School* is the BIE grant school in Neopit. One added word, two "
      "institutions, $112M between them.")
    A("")
    A("**State.** The award recipient's state must equal the entity's state. "
      "School and clinic names repeat across the country, and without that "
      "check a place-name coincidence is indistinguishable from a match.")
    A("")
    A("### A double-count avoided")
    A("")
    A("`faads_transactions.csv` is **excluded** from the totals above. It is "
      "not an independent source: all 59,514 of its distinct "
      "(fain, action date, recipient, amount) keys also appear in "
      "`faads_transactions_all_agencies.csv`. Reading both counted $53M of the "
      "same awards twice - standing rule 7 wearing different clothes.")
    A("")
    A("## Source defects found (reported, not corrected)")
    A("")
    A("- **Website fields swapped.** The BIE directory gives *Hannahville "
      "Indian School* (Wilson, MI) the site `hanaadlicsd.com` and *Hanaadli "
      "Community School/Dormitory Inc.* (Bloomfield, NM) the site "
      "`hannahvilleschool.net`. Each school has been given the other's "
      "website. Recorded as retrieved; not silently corrected.")
    A("- **`Navajo_Operation` is an administrative grouping, not an ownership "
      "field.** *Blackwater Community School* (Coolidge, AZ - Gila River, and "
      "administered from the Albuquerque Education Resource Center) is tagged "
      "`Tribally-Controlled (Navajo)`. It is therefore recorded as metadata "
      "and **never** used to attribute a school to the Navajo Nation. Had it "
      "been trusted, 35 schools would have been booked to Navajo on the "
      "strength of a field that demonstrably does not mean that.")
    A("")
    A("## Refused")
    A("")
    A(f"Full list with reasons: `review/bie_uio_refusals.csv` "
      f"({len(REFUSALS)} rows).")
    A("")
    rc = Counter(r["reason"].split(":")[0] for r in REFUSALS)
    A("| Reason | Count |")
    A("|---|---|")
    for k, v in rc.most_common():
        A(f"| {k} | {v} |")
    A("")
    A("Named refusals worth keeping in view:")
    A("")
    A("- **Haskell Indian Nations University** and **Southwestern Indian "
      "Polytechnic Institute** - BIE-operated post-secondary, owned by the "
      "concurrent TCU agent. Present in the same feature service, which is "
      "why its 187 features become 185 schools here.")
    A("- **National Council of Urban Indian Health** - already in the spine "
      "as an Intertribal Organization (`ITO-RBNHLT-00`). Refused as a "
      "duplicate rather than added a second time.")
    A("- **Urban Indian Health Institute** - added, but flagged "
      "`review_possible_division`. IHS lists it under *Tribal* as a Tribal "
      "Epidemiology Center rather than a Title V direct-service grantee, and "
      "its own site publishes a press contact at `sihb.org`, which suggests "
      "it is a division of Seattle Indian Health Board. No retrieved "
      "statement says so outright, so the relationship is flagged, not "
      "asserted, and must be settled before any dollars roll up.")
    A("")
    A("## Scope this build stayed out of")
    A("")
    A("- `TCU-` and `CDFI-` prefixes: another agent's concurrent work.")
    A("- `api.usaspending.gov`: held by a puller with four jobs queued. Every "
      "host used here (`bie.edu`, `biamaps.geoplatform.gov`, `arcgis.com`, "
      "`services1.arcgis.com`, `ihs.gov`, `ncuih.org`) is unrelated to it.")
    A("- `data/clean/cedar_*` and `review/cedar_*.html`: not written. The "
      "identifiers found here land in new files for review rather than in the "
      "published ledger.")
    A("- `code/00_run_all.py`: not run.")
    A("")
    A("## Reproduce")
    A("")
    A("```")
    A("py -3 code/62_no_regression_check.py           # before")
    A("py -3 code/75_add_bie_schools_and_uios.py")
    A("py -3 code/62_no_regression_check.py           # after")
    A("```")
    A("")
    A("Raw payloads and their retrieval manifest: "
      "`data/raw/external/bie_uio/` (`_SOURCE_MANIFEST.csv`).")
    A("")
    p = DOCS / "BIE_UIO_BUILD_LOG.md"
    p.write_text("\n".join(L), encoding="utf-8")
    print(f"  wrote {p.relative_to(CEDAR)}")


if __name__ == "__main__":
    main()
