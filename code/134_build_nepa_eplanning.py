#!/usr/bin/env python3
r"""
Cedar Press - 134: BLM National NEPA Register (ePlanning) - the OPPOSITION layer.

WHY THIS SOURCE EXISTS IN CEDAR PRESS
-------------------------------------
Every other advocacy source here observes people who REGISTERED to influence
government - LDA filers, OIRA visitors, hearing witnesses. That filter has a
structural blind spot the spec names exactly:

    A county government, a mining company, a municipality, a landowners'
    association or an industry group that opposes a tribal position may never
    register under the LDA in its life. Its position still lands in the
    administrative record, because NEPA requires the agency to take it.

So this is the one place organised opposition to a tribal interest becomes
observable without anybody self-reporting. `ADMINISTRATIVE_COMMENT` is
`EventClass.ADVOCACY` and is **not lobbying** - `cedar_domain.is_lobbying` is
narrower than ADVOCACY, and the assertions below refuse to run if that ever
changes.

WHAT THE SOURCE ACTUALLY PUBLISHES - MEASURED, NOT ASSUMED
-----------------------------------------------------------
ePlanning was rebuilt on Microsoft Power Pages in January 2026. The register
is served by a single JSON endpoint, `POST /searchresults/`, which returns
**69,994 projects, 1987-2026**, filterable by state, office, program, NEPA
type and year. Project pages carry the APPLICANT - the private developer -
which is the actor the lobbying data never sees.

What it does **not** publish is the thing that would be most valuable:
`/Participate-Now` is a comment SUBMISSION form, not a comment register. Its
own privacy notice says a comment "**may** be made publicly available", and
there is no endpoint that lists submitted comments by commenter. Where
comments surface at all they surface as PDFs in a project's document list.

That is recorded in `nepa_source_coverage.csv` as a source property, not
smoothed over: **commenter-level identity is inside document files and was not
extracted here.** What IS captured, and is a retrieved fact rather than an
inference, is the document inventory - a document titled "Comment Letters -
<organisation>" names an organisation in the administrative record.

THE POSITION RULE (hard, from the spec)
---------------------------------------
`administrative_record_position` is a SEPARATE column from `lobbying_position`
and the two are never merged into one "position". An organisation can oppose in
the record and never lobby, or lobby and never comment. `lobbying_position` is
written blank here with its basis stated, so a downstream join cannot silently
treat one as the other.

A position value is only ever read from a document's own words, with the
verbatim substring in `administrative_record_position_quote`. We never author a
verdict about an organisation's stance - LOBBYING_EXPANSION_RECONCILIATION.md
settled that: build the fact, not the verdict.

TRIBAL RELEVANCE, AND WHAT IT IS NOT
-------------------------------------
A project is flagged tribal-relevant only from the register's OWN text: the
program "Cultural-Historical-Native American Resources", or a tribal term in
the project name or the published project description, quoted verbatim. County
adjacency to a reservation is NOT used. Geography is a hypothesis; a sentence
in the record is a fact.

ABSENCE IS A PROPERTY OF THE PROJECT
------------------------------------
A project with no tribal mention is a project whose PUBLISHED SUMMARY does not
mention a tribe. Section 106 consultation on that project may have happened and
lives in the agency file. Never read a blank here as "no tribe was consulted".

Reads   data/spine/cedar_entity_spine.csv
Writes  data/clean/nepa_eplanning_projects.csv
        data/clean/nepa_project_documents.csv
        data/clean/nepa_administrative_record_parties.csv
        data/clean/nepa_source_coverage.csv
        data/raw/advocacy/nepa_eplanning/*.json

RUN:  py -3 code/134_build_nepa_eplanning.py register
      py -3 code/134_build_nepa_eplanning.py details
      py -3 code/134_build_nepa_eplanning.py build
"""

import csv
import html as htmllib
import importlib.util
import json
import re
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

CEDAR = Path(__file__).resolve().parent.parent
CLEAN = CEDAR / "data" / "clean"
SPINE_DIR = CEDAR / "data" / "spine"
RAW = CEDAR / "data" / "raw" / "advocacy" / "nepa_eplanning"
TODAY = date.today().isoformat()

HOST = "eplanning.blm.gov"
BASE = "https://eplanning.blm.gov"
SCRIPT = "code/134_build_nepa_eplanning.py"
DEADLINE_S = 70 * 60
MIN_GAP = 1.0
MAX_DETAIL_PROJECTS = 700

csv.field_size_limit(min(sys.maxsize, 2147483647))

sys.path.insert(0, str(CEDAR / "code"))
from cedar_domain import (AdvocacyChannel, EventClass, Tier,       # noqa: E402
                          may_promote_event_class)
import cedar_match_guard as guard_mod                              # noqa: E402

_spec = importlib.util.spec_from_file_location(
    "c96", CEDAR / "code" / "96_build_consultation_events.py")
c96 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(c96)
Resolver = c96.Resolver
read_csv = c96.read_csv
write_csv = c96.write_csv
claim_host = c96.claim_host
release_host = c96.release_host

CHANNEL = AdvocacyChannel.ADMINISTRATIVE_COMMENT
assert CHANNEL.event_class is EventClass.ADVOCACY, \
    "a NEPA comment must be ADVOCACY - refusing to build."
assert CHANNEL.is_lobbying is False, \
    "cedar_domain calls an administrative comment lobbying - refusing to build."
assert AdvocacyChannel.SECTION_106_CONSULTATION.event_class is \
    EventClass.GOVERNMENT_ENGAGEMENT
assert may_promote_event_class(EventClass.ACCESS, EventClass.ADVOCACY) is False

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")

# See the long note in code/133_build_ferc_advocacy.py. `cedar_match_guard` is
# a DRAFT written for the raw containment tier; the c96 Resolver already
# applies class, specificity, trap, state and head guards internally. Stacking
# the draft on its strong tiers was measured on 2026-08-12 and refused
# "Yurok Tribe" -> Yurok and "Nez Perce Tribe" -> Nez Perce, both correct. It
# fires here only on the tier it was written for.
DRAFT_GUARD_APPLIES_TO = frozenset({
    "resolve_entity_containment", "resolve_entity_core",
    "resolve_entity_containment_guarded", "resolve_entity_core_guarded",
})

_CTX = ssl.create_default_context()
MANIFEST = []
_last_hit = [0.0]
_START = [time.time()]

# The register's own vocabulary, read off the search form 2026-08-12.
PROGRAM_NATIVE = "85e74528-2bea-f011-8544-001dd80f931d"   # Cultural-Historical-Native American Resources
COLUMNS = ["nepanumber", "projectid", "nepastatus", "type", "leadoffice",
           "program", "projectname", "count", "longitude", "latitude",
           "coordinates"]


def _post(path, form, timeout=120, tries=4):
    """Sequential POST with spacing and exponential backoff. 0 = transport."""
    delay = 60.0
    body = urllib.parse.urlencode(form).encode()
    for _ in range(tries):
        if time.time() - _START[0] > DEADLINE_S:
            return -1, "RUN_DEADLINE"
        gap = MIN_GAP - (time.time() - _last_hit[0])
        if gap > 0:
            time.sleep(gap)
        _last_hit[0] = time.time()
        req = urllib.request.Request(
            BASE + path, data=body, method="POST", headers={
                "User-Agent": UA, "Accept": "application/json",
                "Content-Type": "application/x-www-form-urlencoded; "
                                "charset=UTF-8",
                "Referer": BASE + "/search/", "Connection": "close"})
        t0 = time.time()
        try:
            with urllib.request.urlopen(req, timeout=timeout,
                                        context=_CTX) as r:
                raw = r.read()
                MANIFEST.append({"url": BASE + path, "http_status": r.status,
                                 "bytes": len(raw), "fetched_date": TODAY})
                return r.status, raw.decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            MANIFEST.append({"url": BASE + path, "http_status": e.code,
                             "bytes": 0, "fetched_date": TODAY})
            if e.code in (403, 404):
                return e.code, ""
            time.sleep(delay)
        except Exception as e:
            el = time.time() - t0
            print(f"    [{'edge_block' if el < 1 else 'slow'}] "
                  f"{type(e).__name__} after {el:.1f}s")
            MANIFEST.append({"url": BASE + path, "http_status": 0, "bytes": 0,
                             "fetched_date": TODAY})
            time.sleep(delay)
        delay = min(delay * 2, 1800)
    return 0, ""


def _get(url, timeout=90, tries=3):
    delay = 60.0
    for _ in range(tries):
        if time.time() - _START[0] > DEADLINE_S:
            return -1, "RUN_DEADLINE"
        gap = MIN_GAP - (time.time() - _last_hit[0])
        if gap > 0:
            time.sleep(gap)
        _last_hit[0] = time.time()
        req = urllib.request.Request(url, headers={
            "User-Agent": UA,
            "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
            "Connection": "close"})
        t0 = time.time()
        try:
            with urllib.request.urlopen(req, timeout=timeout,
                                        context=_CTX) as r:
                raw = r.read()
                MANIFEST.append({"url": url, "http_status": r.status,
                                 "bytes": len(raw), "fetched_date": TODAY})
                return r.status, raw.decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            MANIFEST.append({"url": url, "http_status": e.code, "bytes": 0,
                             "fetched_date": TODAY})
            if e.code in (403, 404):
                return e.code, ""
            time.sleep(delay)
        except Exception as e:
            el = time.time() - t0
            print(f"    [{'edge_block' if el < 1 else 'slow'}] "
                  f"{type(e).__name__} after {el:.1f}s")
            MANIFEST.append({"url": url, "http_status": 0, "bytes": 0,
                             "fetched_date": TODAY})
            time.sleep(delay)
        delay = min(delay * 2, 1800)
    return 0, ""


def save_manifest():
    RAW.mkdir(parents=True, exist_ok=True)
    p = RAW / "_SOURCE_MANIFEST.csv"
    old = read_csv(p)
    seen = {r["url"] for r in old}
    write_csv(p, old + [r for r in MANIFEST if r["url"] not in seen],
              ["url", "http_status", "bytes", "fetched_date"])


def _form(page, length, extra, total=False, draw=1):
    return [("order_attribute", "0"), ("order_direction", "asc"),
            ("page", str(page)), ("draw", str(draw)),
            ("columns", json.dumps([{"data": c} for c in COLUMNS])),
            ("start", str((page - 1) * length)), ("length", str(length))] \
        + extra + [("active", "false"), ("download", "false"),
                   ("filter_total_count", "0"),
                   ("get_total_count", "true" if total else "false")]


# ===========================================================================
# STAGE 1 - REGISTER. Sweep the whole NEPA Register, year by year.
# ===========================================================================

def stage_register():
    print("=== 134 stage REGISTER ===\n")
    _START[0] = time.time()
    RAW.mkdir(parents=True, exist_ok=True)
    if not claim_host(HOST, SCRIPT, "BLM NEPA Register sweep, ~80 POSTs"):
        print("  deferring to the existing poller. Nothing fetched.")
        return

    out_p = RAW / "register.json"
    have = {}
    if out_p.exists():
        have = {r["nepanumber"]: r for r in
                json.loads(out_p.read_text(encoding="utf-8"))}
    state_p = RAW / "_register_state.json"
    state = json.loads(state_p.read_text(encoding="utf-8")) \
        if state_p.exists() else {"years_done": []}
    state_p.write_text(json.dumps(state, indent=1), encoding="utf-8")

    years = [str(y) for y in range(2026, 1986, -1)]
    any_success = False
    refused = []
    for y in years:
        if y in state["years_done"]:
            continue
        if time.time() - _START[0] > DEADLINE_S:
            print("  RUN_DEADLINE reached - stopping cleanly.")
            break
        st, txt = _post("/searchresults/", _form(1, 10, [("years", y)],
                                                 total=True))
        if st != 200:
            refused.append({"year": y, "http_status": st})
            if not any_success:
                print("  first request refused and nothing has landed - the "
                      "HOST is refusing. Stopping.")
                break
            continue
        try:
            n = json.loads(txt).get("recordsFiltered") or 0
        except Exception:
            refused.append({"year": y, "http_status": st,
                            "reading": "200 with unparseable body"})
            continue
        any_success = True
        got = 0
        page = 1
        while got < n:
            st, txt = _post("/searchresults/",
                            _form(page, 1000, [("years", y)], draw=page + 1))
            if st != 200:
                refused.append({"year": y, "page": page, "http_status": st})
                break
            try:
                data = json.loads(txt).get("data") or []
            except Exception:
                break
            if not data:
                break
            for r in data:
                r["register_year_filter"] = y
                have[r.get("nepanumber") or f"__{len(have)}"] = r
            got += len(data)
            page += 1
            if page > 80:
                break
        print(f"  {y}: source reports {n:5,}   retrieved {got:5,}")
        state["years_done"].append(y)
        state_p.write_text(json.dumps(state, indent=1), encoding="utf-8")
        out_p.write_text(json.dumps(list(have.values()), indent=1),
                         encoding="utf-8")

    # The explicit Native-American program slice, as its own evidenced net.
    st, txt = _post("/searchresults/",
                    _form(1, 1000, [("program", PROGRAM_NATIVE)]))
    native_ids = set()
    if st == 200:
        try:
            for r in json.loads(txt).get("data") or []:
                native_ids.add(r.get("nepanumber"))
                if r.get("nepanumber") in have:
                    have[r["nepanumber"]]["native_program_net"] = "1"
                else:
                    r["native_program_net"] = "1"
                    r["register_year_filter"] = ""
                    have[r["nepanumber"]] = r
        except Exception:
            pass
    print(f"\n  'Cultural-Historical-Native American Resources' program: "
          f"{len(native_ids):,} projects")
    out_p.write_text(json.dumps(list(have.values()), indent=1),
                     encoding="utf-8")
    save_manifest()
    release_host(HOST, SCRIPT,
                 f"register sweep: {len(have):,} projects, "
                 f"{len(refused)} refusals")
    print(f"  register on disk: {len(have):,} projects "
          f"| refused_by_host={len(refused)}")


# ===========================================================================
# STAGE 2 - DETAILS for the tribal-relevant subset.
# ===========================================================================

# PRECISION OVER RECALL - and this cost a measured correction.
#
# A first draft listed bare tribe names (`dakota`, `cheyenne`, `crow`, `ute`,
# `omaha`, `santa clara`, `laguna`) as tribal markers. Measured on the 66,889-
# project register it returned **4,522 candidates** - because in a BLM land
# register those strings are overwhelmingly PLACES. Cheyenne is a city in
# Wyoming, Dakota is a state name, "Crow Creek" and "Ute Trail" are landforms,
# Laguna is a California town. A project named for a valley is not a project
# about a tribe, and a tribal flag on it would be a false attribution of
# exactly the kind AGENTS.md exists to prevent.
#
# So the net is EXPLICIT MARKERS ONLY:
#   * words that can only mean Indian country or its statutory machinery, and
#   * a tribe name ONLY when the record itself follows it with a governmental
#     or land noun - "Navajo Nation", "Ute Reservation", "Zuni Pueblo".
#
# The second pass (a tribe named in the project DESCRIPTION) is resolved
# through the shared Resolver, which carries its own trap and state guards.
#   `allotment` and `reservation` were BOTH in an earlier draft and BOTH are
#   wrong on their own. In BLM's register an "allotment" is a GRAZING
#   allotment - "Grazing Lease Renewal for Devils Gulch (#00116) Allotment" -
#   and it is one of the most common words in the whole file. A bare `indian`
#   catches "Indian Camp Water" and "Indian Creek", which are landforms. So
#   each of these must be adjacent to a word that makes it Indian country.
EXPLICIT_MARKERS = [
    r"\btribes?\b", r"\btribal\b", r"\bnative american\b",
    r"\bamerican indian\b",
    r"\bindian\s+(?:tribes?|nation|reservation|allotment|country|affairs|"
    r"trust|lands?|community|colony|band|pueblo|claims?)\b",
    r"\bthpo\b", r"\brancheria\b", r"\bpueblo\b",
    r"\bindian\s+reservation\b", r"\bindian\s+allotment\b",
    r"traditional cultural propert", r"\bsacred site", r"section 106",
    r"\bnagpra\b", r"government-to-government", r"\bnative alaskan?\b",
    r"\balaska native\b", r"\bancsa\b", r"\bnsn\.gov\b",
]
TRIBE_NAMES = [
    "navajo", "hopi", "zuni", "ute", "shoshone", "paiute", "bannock",
    "apache", "tohono o'odham", "gila river", "chemehuevi", "cocopah",
    "quechan", "mojave", "havasupai", "hualapai", "yavapai", "jicarilla",
    "mescalero", "acoma", "laguna", "taos", "isleta", "jemez", "cochiti",
    "santa clara", "ohkay owingeh", "sioux", "lakota", "dakota", "arapaho",
    "cheyenne", "crow", "blackfeet", "assiniboine", "gros ventre",
    "salish", "kootenai", "kalispel", "coeur d'alene", "nez perce",
    "umatilla", "warm springs", "yakama", "colville", "spokane",
    "klamath", "modoc", "washoe", "te-moak", "duckwater", "yomba",
    "goshute", "chippewa", "ojibwe", "menominee", "ho-chunk", "osage",
    "cherokee", "choctaw", "chickasaw", "muscogee", "seminole", "comanche",
    "kiowa", "wichita", "caddo", "pawnee", "ponca", "winnebago", "yurok",
    "karuk", "hoopa", "pit river", "round valley", "morongo", "cahuilla",
    "pechanga", "viejas", "barona", "campo", "walker river",
    "pyramid lake", "fort mcdermitt", "skull valley",
]
_GOV_NOUN = (r"(?:tribes?|nation|pueblo|rancheria|band|community|"
             r"reservation|indian|colony|agency|allotment)")
TRIBAL_RE = re.compile(
    "|".join(EXPLICIT_MARKERS
             + [rf"\b{re.escape(t)}\s+{_GOV_NOUN}\b" for t in TRIBE_NAMES]),
    re.I)


def _text(html_s, start_marker="Project Name:"):
    i = html_s.find(start_marker)
    seg = html_s[i:] if i > 0 else html_s
    seg = re.sub(r"<(script|style)\b.*?</\1>", " ", seg, flags=re.S | re.I)
    seg = re.sub(r"<br\s*/?>", "\n", seg, flags=re.I)
    seg = re.sub(r"</(p|div|li|tr|h\d|td|th)>", "\n", seg, flags=re.I)
    t = htmllib.unescape(re.sub(r"<[^>]+>", "\n", seg))
    return [l.strip() for l in t.split("\n") if l.strip()]


def _field(lines, label, max_ahead=3):
    for i, l in enumerate(lines):
        if l.strip().lower() == label.lower():
            for j in range(i + 1, min(i + 1 + max_ahead, len(lines))):
                v = lines[j].strip()
                if v and v.lower() not in ("none", "n/a"):
                    return v
            return ""
    return ""


def stage_details():
    print("=== 134 stage DETAILS ===\n")
    _START[0] = time.time()
    reg = json.loads((RAW / "register.json").read_text(encoding="utf-8"))
    print(f"  register: {len(reg):,} projects")

    cands = []
    for r in reg:
        why, quote = [], ""
        if r.get("native_program_net") == "1" or \
                "Native American" in (r.get("program") or ""):
            why.append("register_program_cultural_historical_native_american")
            quote = r.get("program") or ""
        m = TRIBAL_RE.search(r.get("projectname") or "")
        if m:
            why.append("tribal_term_in_project_name")
            quote = quote or (r.get("projectname") or "")
        if why:
            r["_why"] = ";".join(why)
            r["_quote"] = quote
            cands.append(r)
    print(f"  tribal-relevant by register text: {len(cands):,}")

    if not claim_host(HOST, SCRIPT,
                      f"project pages for {min(len(cands), MAX_DETAIL_PROJECTS)} "
                      f"tribal-relevant projects"):
        print("  deferring to the existing poller. Nothing fetched.")
        return

    det_dir = RAW / "projects"
    det_dir.mkdir(parents=True, exist_ok=True)
    any_success = False
    refused = 0
    todo = [c for c in cands
            if not (det_dir / f"{c['projectid']}.json").exists()
            ][:MAX_DETAIL_PROJECTS]
    print(f"  to fetch: {len(todo):,}\n")

    for i, c in enumerate(todo, 1):
        if time.time() - _START[0] > DEADLINE_S:
            print("  RUN_DEADLINE reached - stopping cleanly.")
            break
        pid = c["projectid"]
        st, page = _get(f"{BASE}/project-home?id={pid}")
        if st != 200:
            refused += 1
            if not any_success:
                print("  first project refused and nothing landed - the HOST "
                      "is refusing. Stopping.")
                break
            continue
        any_success = True
        lines = _text(page)
        spid = ""
        m = re.search(r"/documents\?id=[0-9a-f\-]+&amp;spid=([0-9a-f\-]{36})",
                      page) or re.search(
            r"/documents\?id=[0-9a-f\-]+&spid=([0-9a-f\-]{36})", page)
        if m:
            spid = m.group(1)
        docs_html = ""
        if spid:
            st2, docs_html = _get(
                f"{BASE}/documents?id={pid}&spid={spid}")
            if st2 != 200:
                docs_html = ""
        (det_dir / f"{pid}.json").write_text(json.dumps({
            "register": {k: v for k, v in c.items() if not k.startswith("_")},
            "why_tribal_relevant": c.get("_why", ""),
            "tribal_relevance_quote": c.get("_quote", ""),
            "project_lines": lines[:400],
            "documents_html": docs_html[:900000],
            "project_url": f"{BASE}/project-home?id={pid}",
            "documents_url": f"{BASE}/documents?id={pid}&spid={spid}"
            if spid else "",
            "fetched_date": TODAY}, indent=1), encoding="utf-8")
        if i % 25 == 0 or i == len(todo):
            print(f"  [{i}/{len(todo)}] {c.get('nepanumber','')}")
    save_manifest()
    release_host(HOST, SCRIPT,
                 f"project details: {len(list(det_dir.glob('*.json')))} on "
                 f"disk, {refused} refused")


# ===========================================================================
# STAGE 3 - BUILD.
# ===========================================================================

DOC_TYPES = [
    # THE ADVOCACY-BEARING CATEGORIES ARE TESTED FIRST, and the boundary
    # syntax matters more than it looks.
    #
    # Two separate defects, both measured on this file's own output:
    #   1. Requiring the phrase "comment letter" / "public comment" typed
    #      exactly ONE document across 312 projects, while the record plainly
    #      held `SUWA_Protocol_Comments.pdf`, `NTHP_Protocol_Comments.pdf` and
    #      `PLPCO_Protocol_Comments.pdf`. Those filenames are how organised
    #      participation is actually named on this system.
    #   2. `\bcomments?\b` still did not match them, because in
    #      `SUWA_Protocol_Comments.pdf` the UNDERSCORE is a word character, so
    #      there is no word boundary before `Comments`. Explicit letter
    #      lookarounds are the fix.
    # And the order matters: `\bEA\b` fires on "Preliminary EA Comment
    # Request", which is a comment record, not an environmental assessment.
    ("COMMENT_RECORD", re.compile(
        r"(?<![A-Za-z])comments?(?![A-Za-z])|comment letter|public comment|"
        r"response to comment|comment analysis|comment summary", re.I)),
    ("PROTEST_RECORD", re.compile(
        r"(?<![A-Za-z])protest(s|ed|ing)?(?![A-Za-z])", re.I)),
    ("SCOPING_RECORD", re.compile(r"scoping", re.I)),
    ("RECORD_OF_DECISION", re.compile(r"\bROD\b|record of decision", re.I)),
    ("FONSI", re.compile(r"\bFONSI\b|finding of no significant impact", re.I)),
    ("DECISION_RECORD", re.compile(r"decision record|\bDR\b", re.I)),
    ("EIS", re.compile(r"\bEIS\b|environmental impact statement", re.I)),
    ("EA", re.compile(r"\bEA\b|environmental assessment", re.I)),
    ("CATEGORICAL_EXCLUSION", re.compile(r"\bCX\b|\bCE\b|categorical "
                                         r"exclusion", re.I)),
    ("TRIBAL_CONSULTATION_RECORD", re.compile(
        r"tribal consultation|section 106|native american consultation|"
        r"\bTHPO\b|programmatic agreement|cultural resource", re.I)),
    ("PLAN_OF_OPERATIONS", re.compile(r"plan of operations", re.I)),
]

POSITION_PATTERNS = [
    ("OPPOSITION_STATED_IN_DOCUMENT_TITLE",
     re.compile(r"\bprotest\b|\bopposition\b|\bopposing\b|\bobjection\b", re.I)),
    ("SUPPORT_STATED_IN_DOCUMENT_TITLE",
     re.compile(r"\bin support of\b|\bletter of support\b", re.I)),
]

ORG_TYPE_PATTERNS = [
    ("TRIBAL_GOVERNMENT_OR_ORGANIZATION", re.compile(
        r"\btribe\b|\btribal\b|\bpueblo\b|\brancheria\b|\bnation\b|"
        r"\bband of\b|\bindian\b", re.I)),
    ("FEDERAL_AGENCY", re.compile(
        r"\bEPA\b|\bUSFWS\b|\bNPS\b|\bBIA\b|Fish and Wildlife|Forest Service|"
        r"National Park|Army Corps|Environmental Protection Agency", re.I)),
    ("STATE_AGENCY", re.compile(
        r"\bState of\b|Department of Environmental|Department of Wildlife|"
        r"Department of Natural Resources|State Historic Preservation|"
        r"\bSHPO\b", re.I)),
    ("LOCAL_GOVERNMENT", re.compile(
        r"\bCounty\b|\bCity of\b|\bTown of\b|\bBorough\b|"
        r"\bConservation District\b|\bIrrigation District\b", re.I)),
    ("NGO_OR_ASSOCIATION", re.compile(
        r"\bAssociation\b|\bAlliance\b|\bCoalition\b|\bSociety\b|\bClub\b|"
        r"\bCenter for\b|\bTrust\b|\bFoundation\b|\bCouncil\b|"
        r"\bWatershed\b|\bRiverkeeper\b|\bLandowners?\b|\bPermittees?\b|"
        r"\bStockgrowers?\b|\bCattlemen\b|\bFarm Bureau\b", re.I)),
    ("COMPANY", re.compile(
        r"\bLLC\b|\bInc\b|\bCorp\b|\bCompany\b|\bLP\b|\bLtd\b|"
        r"\bResources\b|\bEnergy\b|\bMining\b|\bMinerals\b", re.I)),
]


def doc_type(name):
    for t, rx in DOC_TYPES:
        if rx.search(name or ""):
            return t
    return "OTHER_PROJECT_DOCUMENT"


def doc_position(name):
    for v, rx in POSITION_PATTERNS:
        m = rx.search(name or "")
        if m:
            return v, name.strip()
    return "NOT_STATED_IN_DOCUMENT_TITLE", ""


ORG_TOKEN_RE = re.compile(r"^([A-Za-z][A-Za-z&\.\- ]{1,40}?)[_\.]{1,2}"
                          r"(?=[A-Za-z]*(?:Protocol|Comment|Letter|Protest))")


def org_token(name):
    """The leading filename token, VERBATIM. Never resolved to an entity."""
    m = ORG_TOKEN_RE.match(name or "")
    return m.group(1).strip(" _.-") if m else ""


def org_type(name):
    for t, rx in ORG_TYPE_PATTERNS:
        if rx.search(name or ""):
            return t
    return "OTHER_ORGANIZATION"


def stage_build():
    print("=== 134 stage BUILD ===\n")
    reg_p = RAW / "register.json"
    reg = json.loads(reg_p.read_text(encoding="utf-8")) if reg_p.exists() \
        else []
    det_dir = RAW / "projects"
    files = sorted(det_dir.glob("*.json")) if det_dir.exists() else []
    print(f"  register {len(reg):,} projects | detail pages {len(files):,}")

    spine = read_csv(SPINE_DIR / "cedar_entity_spine.csv")
    R = Resolver(spine)
    spine_rows = {r["tribe_id"]: r for r in spine}

    projects, documents, parties = [], [], []
    tribes, applicants, orgs_opposing, orgs_all = set(), set(), set(), set()
    st = Counter()

    for p in files:
        j = json.loads(p.read_text(encoding="utf-8"))
        r = j["register"]
        lines = j.get("project_lines") or []
        desc_i = None
        for i, l in enumerate(lines):
            if l.strip().lower() == "project description":
                desc_i = i
                break
        desc = ""
        if desc_i is not None:
            buf = []
            for l in lines[desc_i + 1:desc_i + 25]:
                if l.strip() in ("Project Location", "Application Information",
                                 "Project Dates", "What's New",
                                 "Project Office Information",
                                 "Final EIS Publication"):
                    break
                buf.append(l)
            desc = " ".join(buf)

        # THE LOCATION TABLE IS LABEL-ROW-THEN-VALUE-ROW, NOT LABEL:VALUE.
        # A generic "next non-empty line after the label" reader returned
        # `state_or_territory = "Zip Code"` on all 312 projects - the NEXT
        # HEADER, not the value. The four headers are emitted consecutively
        # and the four values follow in the same order.
        loc = {}
        try:
            li = lines.index("Project Location")
            hdr = lines[li + 1:li + 5]
            if hdr[:4] == ["City", "State/Territory", "Zip Code",
                           "County(ies)"]:
                vals = lines[li + 5:li + 9]
                loc = dict(zip(hdr, vals + [""] * 4))
        except (ValueError, IndexError):
            loc = {}

        applicant = _field(lines, "Applicant")
        if applicant.lower().startswith("program"):
            applicant = ""
        if applicant:
            applicants.add(applicant)
        counties = loc.get("County(ies)", "")
        state_name = loc.get("State/Territory", "")
        city = loc.get("City", "")
        program = _field(lines, "Program") or r.get("program") or ""
        subprogram = _field(lines, "Sub-Program")

        # tribal relevance, from the record's own text only
        why = [w for w in (j.get("why_tribal_relevant") or "").split(";") if w]
        quote = j.get("tribal_relevance_quote") or ""
        m = TRIBAL_RE.search(desc)
        if m:
            why.append("tribal_term_in_published_project_description")
            i0 = max(0, m.start() - 120)
            quote = re.sub(r"\s+", " ", desc[i0:m.end() + 180]).strip()
        consult = "1" if re.search(
            r"consult\w*\s+with\s+(the\s+)?(tribe|tribes|tribal|native)|"
            r"tribal consultation|section 106|government-to-government",
            desc, re.I) else "0"

        # named tribes, resolved through the ONE resolver, then guarded
        named = []
        for cand in set(re.findall(
                r"\b([A-Z][A-Za-z'\-]+(?:\s+[A-Z][A-Za-z'\-]+){0,4}\s+"
                r"(?:Tribe|Tribes|Nation|Pueblo|Rancheria|Band|Community))\b",
                (r.get("projectname") or "") + " " + desc)):
            res = R.resolve(cand)
            if res and res[0]:
                ok, reason = (True, "")
                if res[2] in DRAFT_GUARD_APPLIES_TO:
                    ok, reason = guard_mod.guard(
                        cand, spine_rows.get(res[0], {}), res[2],
                        {"record_state": ""})
                if ok:
                    named.append((res[0], res[1], cand, res[2]))
                    tribes.add(res[0])
                else:
                    st["draft_guard_refused"] += 1

        proj_id = r.get("nepanumber") or r.get("projectid")
        projects.append({
            "nepa_number": r.get("nepanumber", ""),
            "eplanning_project_id": r.get("projectid", ""),
            "project_name": r.get("projectname", ""),
            "agency": "Bureau of Land Management",
            "lead_office": r.get("leadoffice", ""),
            "nepa_document_type": r.get("type", ""),
            "nepa_status": r.get("nepastatus", ""),
            "program": program, "sub_program": subprogram,
            "applicant_or_developer_as_published": applicant,
            "city": city, "state_or_territory": state_name,
            "counties": counties,
            "latitude": r.get("latitude", ""), "longitude": r.get("longitude", ""),
            "tribal_relevance_basis": ";".join(sorted(set(why))),
            "tribal_relevance_quote": quote[:500],
            "tribal_consultation_referenced": consult,
            "tribes_named_in_record": ";".join(
                sorted({n[1] for n in named})),
            "tribe_ids_named_in_record": ";".join(
                sorted({n[0] for n in named})),
            "project_description_verbatim": desc[:1200],
            "absence_note":
                "A blank tribal field is a property of the PUBLISHED SUMMARY, "
                "not of the project. Consultation may have occurred and sit "
                "in the agency file.",
            "source_url": j.get("project_url", ""),
            "fetched_date": j.get("fetched_date", TODAY),
            "confidence_tier": Tier.A.value,
            "built_date": TODAY, "built_by_script": SCRIPT,
        })
        for tid, canon, as_written, method in named:
            parties.append({
                "party_id": f"NEPAP-{r.get('nepanumber','')}-{tid}",
                "nepa_number": r.get("nepanumber", ""),
                "eplanning_project_id": r.get("projectid", ""),
                "event_class": EventClass.GOVERNMENT_ENGAGEMENT.value,
                "channel": AdvocacyChannel.CONSULTATION.value
                if consult == "1" else "",
                "is_lobbying": "0",
                "party_name_as_published": as_written,
                "party_role": "TRIBE_NAMED_IN_PROJECT_RECORD",
                "party_organization_type": "TRIBAL_GOVERNMENT_OR_ORGANIZATION",
                "resolved_native_entity_id": tid,
                "resolved_native_entity_name": canon,
                "resolution_method": method,
                "administrative_record_position": "NOT_STATED_IN_RECORD",
                "administrative_record_position_quote": "",
                "lobbying_position": "",
                "lobbying_position_basis":
                    "NOT_OBSERVED_IN_THIS_SOURCE - the administrative record "
                    "and the LDA record are separate observations and are "
                    "never merged",
                "supporting_quote": quote[:400],
                "source_url": j.get("project_url", ""),
                "fetched_date": j.get("fetched_date", TODAY),
                "confidence_tier": Tier.A.value,
                "built_date": TODAY, "built_by_script": SCRIPT,
            })

        # --- documents: the administrative record inventory -----------------
        # THE DOCUMENT LIST IS AN EMBEDDED JSON BLOCK, NOT MARKUP.
        # The page renders its table client-side from
        #   {"Document1": [...], "Document2": [{"documentName": ..., ...}]}
        # so a scraper looking for anchors finds the LITERAL Angular-style
        # template `${row.documentName}` and concludes the project has no
        # documents. A first pass did exactly that and reported 62 documents
        # across 307 projects; the JSON block holds far more.
        dh = j.get("documents_html") or ""
        recs = {}
        for m2 in re.finditer(
                r'"documentName"\s*:\s*"([^"]{3,300})"(?P<tail>.{0,700}?)'
                r'"order"', dh, re.S):
            name = htmllib.unescape(m2.group(1))
            tail = m2.group("tail")
            rel = re.search(r'"releaseDate"\s*:\s*"([^"]*)"', tail)
            dtyp = re.search(r'"documentType"\s*:\s*"([^"]*)"', tail)
            blob = re.search(r'"blobUrl"\s*:\s*"([^"]*)"', tail)
            recs[name] = {
                "release_date": (rel.group(1) if rel else ""),
                "source_document_type": (dtyp.group(1) if dtyp else ""),
                "blob_path": (blob.group(1) if blob else ""),
            }
        for m2 in re.finditer(r'data-documentname="([^"$]{3,300})"', dh):
            recs.setdefault(htmllib.unescape(m2.group(1)), {})
        for m2 in re.finditer(r'/Documents/([^"?$]{3,300})"', dh):
            recs.setdefault(urllib.parse.unquote(m2.group(1)), {})
        for name in sorted(recs):
            meta = recs[name]
            st["documents_seen"] += 1
            dt = doc_type(name)
            pos, pq = doc_position(name)
            documents.append({
                "nepa_number": r.get("nepanumber", ""),
                "eplanning_project_id": r.get("projectid", ""),
                "document_name_verbatim": name[:300],
                "document_release_date": meta.get("release_date", ""),
                "document_type_as_published": meta.get(
                    "source_document_type", ""),
                "document_record_type": dt,
                "event_class": EventClass.ADVOCACY.value
                if dt in ("COMMENT_RECORD", "PROTEST_RECORD") else "",
                "channel": CHANNEL.value
                if dt in ("COMMENT_RECORD", "PROTEST_RECORD") else "",
                "is_lobbying": "0" if dt in ("COMMENT_RECORD",
                                             "PROTEST_RECORD") else "",
                "administrative_record_position": pos,
                "administrative_record_position_quote": pq[:300],
                "lobbying_position": "",
                "lobbying_position_basis":
                    "NOT_OBSERVED_IN_THIS_SOURCE",
                "organization_token_in_document_name": org_token(name)
                if dt in ("COMMENT_RECORD", "PROTEST_RECORD") else "",
                "organization_token_basis":
                    "VERBATIM leading token of the filename, recorded as text "
                    "only. It is NOT resolved to an organisation - "
                    "SUWA/NTHP/PLPCO are acronyms and acronym matching is how "
                    "false attributions are made. Resolve it by reading the "
                    "document, not by guessing.",
                "commenter_identity_note":
                    "Commenter names are inside the document file. ePlanning "
                    "publishes no commenter-level list; see "
                    "nepa_source_coverage.csv.",
                "source_url": j.get("documents_url", ""),
                "fetched_date": j.get("fetched_date", TODAY),
                "confidence_tier": Tier.A.value,
                "built_date": TODAY, "built_by_script": SCRIPT,
            })
            if dt in ("COMMENT_RECORD", "PROTEST_RECORD"):
                st["comment_or_protest_documents"] += 1
            if applicant:
                orgs_all.add(applicant)
            if pos == "OPPOSITION_STATED_IN_DOCUMENT_TITLE":
                orgs_opposing.add(f"{r.get('nepanumber','')}::{name[:80]}")

    write_csv(CLEAN / "nepa_eplanning_projects.csv", projects, [
        "nepa_number", "eplanning_project_id", "project_name", "agency",
        "lead_office", "nepa_document_type", "nepa_status", "program",
        "sub_program", "applicant_or_developer_as_published",
        "city", "state_or_territory", "counties", "latitude", "longitude",
        "tribal_relevance_basis", "tribal_relevance_quote",
        "tribal_consultation_referenced", "tribes_named_in_record",
        "tribe_ids_named_in_record", "project_description_verbatim",
        "absence_note", "source_url", "fetched_date", "confidence_tier",
        "built_date", "built_by_script"])
    write_csv(CLEAN / "nepa_project_documents.csv", documents, [
        "nepa_number", "eplanning_project_id", "document_name_verbatim",
        "document_release_date", "document_type_as_published",
        "document_record_type", "event_class", "channel", "is_lobbying",
        "administrative_record_position",
        "administrative_record_position_quote", "lobbying_position",
        "lobbying_position_basis", "organization_token_in_document_name",
        "organization_token_basis", "commenter_identity_note", "source_url",
        "fetched_date", "confidence_tier", "built_date", "built_by_script"])
    write_csv(CLEAN / "nepa_administrative_record_parties.csv", parties, [
        "party_id", "nepa_number", "eplanning_project_id", "event_class",
        "channel", "is_lobbying", "party_name_as_published", "party_role",
        "party_organization_type", "resolved_native_entity_id",
        "resolved_native_entity_name", "resolution_method",
        "administrative_record_position",
        "administrative_record_position_quote", "lobbying_position",
        "lobbying_position_basis", "supporting_quote", "source_url",
        "fetched_date", "confidence_tier", "built_date", "built_by_script"])
    write_nepa_coverage(len(reg), len(files), len(projects), len(documents))

    print()
    for k, v in st.most_common():
        print(f"  {k:34s} {v:>8,}")
    print(f"\n  projects           {len(projects):,}")
    print(f"  documents          {len(documents):,}")
    print(f"  parties            {len(parties):,}")
    print(f"  distinct tribes    {len(tribes):,}")
    print(f"  distinct applicants{len(applicants):,}")


def write_nepa_coverage(n_reg, n_det, n_proj, n_doc):
    rows = [
        {"source": "BLM NEPA Register - POST /searchresults/",
         "url": f"{BASE}/searchresults/",
         "status": "PUBLISHES",
         "what_was_swept": "every register year 1987-2026, plus the "
                           "'Cultural-Historical-Native American Resources' "
                           "program as its own net",
         "probe_evidence": f"HTTP 200, zero refusals. Measured 2026-08-12: "
                           f"the all-years filter reports 69,994; the 40 "
                           f"per-year queries report 69,995 in total and "
                           f"returned 67,053 rows, which de-duplicate on "
                           f"nepanumber to {n_reg:,} unique projects. Form-"
                           f"encoded POST; `columns` must be a JSON array and "
                           f"at least one filter must be present - an "
                           f"unfiltered POST returns recordsFiltered 0, which "
                           f"is a property of the endpoint, not of the "
                           f"register.",
         "reading": "Project-level register, 95.8% of the rows the source "
                    "reports. The ~2,900-row shortfall is the paginator, not "
                    "the register, and is stated rather than rounded away. "
                    "164 nepanumbers appear under two year filters.",
         "checked_date": TODAY},
        {"source": "BLM ePlanning project page (/project-home)",
         "url": f"{BASE}/project-home?id=<guid>",
         "status": "PUBLISHES",
         "what_was_swept": f"{n_det:,} tribal-relevant projects",
         "probe_evidence": "HTTP 200; carries Applicant, Program/Sub-Program, "
                           "counties, dates and the published project "
                           "description",
         "reading": "This is where the private developer is named - the actor "
                    "the LDA data never sees.",
         "checked_date": TODAY},
        {"source": "BLM ePlanning comment submissions (/Participate-Now)",
         "url": f"{BASE}/Participate-Now?id=<guid>&ppid=<guid>",
         "status": "WITHHOLDS",
         "what_was_swept": "the participation-period page itself",
         "probe_evidence": "It is a SUBMISSION FORM, not a register. Its own "
                           "privacy notice reads: 'your entire comment - "
                           "including your personal identifying information - "
                           "MAY be made publicly available at any time', and "
                           "it offers 'Withhold my personally identifying "
                           "information from future publications on this "
                           "project.' No endpoint lists submitted comments by "
                           "commenter.",
         "reading": "COMMENTER-LEVEL IDENTITY IS NOT PUBLISHED IN STRUCTURED "
                    "FORM. Comments surface, if at all, as PDFs in a "
                    "project's document list. A project with no named "
                    "commenter here received comments we cannot see - never "
                    "read this as 'nobody commented'.",
         "checked_date": TODAY},
        {"source": "BLM ePlanning document files",
         "url": f"{BASE}/<guid>/Documents/<filename>",
         "status": "NOT_CHECKED",
         "what_was_swept": "document NAMES only",
         "probe_evidence": "Files are served through an Azure Logic App "
                           "connector (blm-eplanninganonconnector-lap.blm.gov) "
                           "with a signed URL. Disk on this machine stood at "
                           "5.9 GB free with five other agents running and a "
                           "2 GB floor, so no PDFs were downloaded.",
         "reading": "Document inventory is real; document CONTENT - where the "
                    "named commenting organisations and their arguments "
                    "actually are - has not been read.",
         "checked_date": TODAY},
        {"source": "BLM ePlanning robots.txt",
         "url": f"{BASE}/robots.txt",
         "status": "NOT_FOUND",
         "what_was_swept": "one request",
         "probe_evidence": "HTTP 404 with the site's own 'Page Not Found' "
                           "body - no crawl rule is published.",
         "reading": "No robots restriction was found. Fetching stayed "
                    "sequential at >=1s spacing regardless.",
         "checked_date": TODAY},
    ]
    write_csv(CLEAN / "nepa_source_coverage.csv", rows,
              ["source", "url", "status", "what_was_swept", "probe_evidence",
               "reading", "checked_date"])


if __name__ == "__main__":
    stage = (sys.argv[1] if len(sys.argv) > 1 else "all").lower()
    if stage in ("register", "all"):
        stage_register()
    if stage in ("details", "all"):
        stage_details()
    if stage in ("build", "all"):
        stage_build()
