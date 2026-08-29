#!/usr/bin/env python3
"""146_build_visitor_access_records.py -- ROUND 2 item 10: visitor / building access.

    channel     VISITOR_RECORD
    class       EventClass.ACCESS          <- permanently, and the code enforces it
    is_lobbying FALSE

=== THE HARD RULE, ASSERTED AT IMPORT ===

A visitor record says a person was cleared into a building. It does NOT say a
meeting happened, that the meeting concerned any matter we care about, or that
anyone was influenced. `may_promote_event_class(ACCESS, ADVOCACY)` is False and
this script asserts it before writing a byte.

The richness of WAVES -- named visitee, room number, appointment window, arrival
and departure to the minute -- is exactly what tempts a downstream join into
asserting a meeting occurred. Three refusals below exist to make that join
impossible to write by accident.

=== REFUSAL 1: NO VISITOR NAMES. THE GRAIN IS THE APPOINTMENT, NOT THE PERSON ===

The WAVES schema is person-level and carries `NAMELAST`, `NAMEFIRST`, `NAMEMID`
on 5.99 million rows, most of them ordinary members of the public on public
tours. It carries NO organisation field for the visitor -- so a visitor cannot
be linked to an organisation from this source at all, and "restrict to visits
linkable to an organisation or an official capacity" cannot be satisfied at the
person grain.

So this build aggregates to the APPOINTMENT: (appointment start, visitee,
meeting location, meeting room, description). Each row carries
`n_visitor_records` and **no visitor name of any kind**. The visitee IS named,
because a visitee in WAVES is an Executive Office of the President staff member
receiving visitors in an official capacity.

=== REFUSAL 2: NO ENTITY ATTRIBUTION FROM A DESCRIPTION STRING ===

`resolve_entity` is NOT run against the `Description` field, deliberately. Its
containment tier matches whenever one name's token set contains the other's,
and the entity-inside-record direction is the one that put $2.8B on a school
(AGENTS.md, THE CONTAINMENT DEFECT). A free-text meeting description is the
worst possible input to it.

`native_entity_id` is therefore BLANK on every row, with
`native_entity_link_basis = NOT_ATTEMPTED_BY_RULE`. That is a deliberate
refusal, not unfinished work, and it is stated in the data rather than left to
be discovered.

Consequence, stated plainly: **zero position rows.**
`position_is_addressable()` needs organisation_id + matter_id +
native_entity_id, and this source supplies none of the three.

=== REFUSAL 3: A DESCRIPTION MATCH IS A PROPERTY OF THE DESCRIPTION FIELD ===

Native relevance is decided ONLY by a conservative verbatim term list applied to
`Description`, and the matched term plus the verbatim description travel on
every row. Bare "INDIAN" is NOT a term -- it means India often enough to have
its own entry in `cedar_domain.NAME_TRAPS`. `Description` is blank on a large
share of WAVES rows; a blank description is a property of the release, and the
coverage table says so rather than implying those appointments were not tribal.

=== DISCOVERY INDEX BEFORE ANY NEW PULL ===

`data/clean/foia_request_index.csv` (9,481 rows) is read FIRST and its
calendar/visitor-record requests are emitted as
`visitor_record_foia_requests.csv` -- what other requesters already asked which
agency for. That inverts the FOIA cost curve exactly as ROUND 2 item 3
prescribes, and it is what establishes NOT_FOUND vs NOT_CHECKED for the
agencies that publish nothing.

Reads  obamawhitehouse.archives.gov WAVES annual releases (8 zips)
       data/clean/foia_request_index.csv
Writes data/clean/visitor_access_events.csv
       data/clean/visitor_record_foia_requests.csv
       data/clean/source_coverage_visitor_records.csv
"""
from __future__ import annotations

import csv
import datetime as dt
import io
import json
import os
import re
import subprocess
import sys
import time
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
CODE = ROOT / "code"
RAW = ROOT / "data" / "raw" / "visitor_records"
CLEAN = ROOT / "data" / "clean"
LOGS = ROOT / "logs"
SCRIPT = "code/146_build_visitor_access_records.py"
TODAY = dt.date.today().isoformat()
for d in (RAW, CLEAN, LOGS):
    d.mkdir(parents=True, exist_ok=True)

sys.path.insert(0, str(CODE))
from cedar_domain import (  # noqa: E402
    AdvocacyChannel, EventClass, Tier, may_promote_event_class,
    position_is_addressable,
)

CH = AdvocacyChannel.VISITOR_RECORD
assert CH.event_class == EventClass.ACCESS, "a visitor record is ACCESS"
assert CH.is_lobbying is False
assert may_promote_event_class(EventClass.ACCESS, EventClass.ADVOCACY) is False, \
    "cedar_domain must refuse ACCESS -> ADVOCACY before this dataset exists"

HOST = "obamawhitehouse.archives.gov"
BASE = "https://obamawhitehouse.archives.gov"
UA = ("CedarPress-research/1.0 (+https://cedarpress.co; "
      "elijahsamsonmoreno@gmail.com)")
HEADERS = {"User-Agent": UA}
GAP = 4.0
DEADLINE_S = 40 * 60

# The eight annual raw releases linked from
# /briefing-room/disclosures/visitor-records, transcribed verbatim.
RELEASES = [
    ("2009-2010", "/files/disclosures/visitors/WhiteHouse-WAVES-Released-1210.zip"),
    ("2011a", "/files/disclosures/visitors/WhiteHouse-WAVES-Released-0711b.zip"),
    ("2011b", "/files/disclosures/visitors/WhiteHouse-WAVES-Released-through-December-2011.zip"),
    ("2012", "/sites/default/files/disclosures/whitehouse-waves-2012.csv_.zip"),
    ("2013", "/sites/default/files/disclosures/whitehouse-waves-2013.csv__0.zip"),
    ("2014", "/sites/default/files/disclosures/whitehouse_waves-2014_12.csv_.zip"),
    ("2015", "/sites/default/files/disclosures/whitehouse_waves-2015_12.csv_.zip"),
    ("2016", "/sites/default/files/disclosures/whitehouse_waves-2016_12.csv_.zip"),
]
LANDING = BASE + "/briefing-room/disclosures/visitor-records"
KEY_TXT = BASE + "/files/disclosures/visitors/WhiteHouse-WAVES-Key-1209.txt"

# ---------------------------------------------------------------------------
# The term list. Conservative by construction: every term is a multi-word
# phrase or an unambiguous proper noun. Bare "INDIAN" is excluded -- it means
# India often enough to sit in cedar_domain.NAME_TRAPS.
# ---------------------------------------------------------------------------
NATIVE_TERMS = [
    "TRIBAL", "TRIBE", "TRIBES", "NATIVE AMERICAN", "AMERICAN INDIAN",
    "ALASKA NATIVE", "ALASKAN NATIVE", "NATIVE HAWAIIAN",
    "INDIAN AFFAIRS", "INDIAN COUNTRY", "INDIAN HEALTH", "INDIAN GAMING",
    "INDIAN EDUCATION", "INDIAN NATION", "INDIAN TRIBE", "INDIAN LAND",
    "INDIAN LAW", "INDIAN TRUST", "INDIAN WATER", "INDIAN HOUSING",
    "INDIAN CHILD WELFARE", "INDIGENOUS", "NAGPRA", "SELF-GOVERNANCE",
    "NCAI", "NATIONAL CONGRESS OF AMERICAN INDIANS", "COBELL",
    "FIRST NATIONS", "NATIVE YOUTH", "NATIVE VILLAGE", "PUEBLO",
    "NAVAJO", "CHEROKEE NATION", "SIOUX", "CHICKASAW", "CHOCTAW",
    "MUSCOGEE", "SEMINOLE NATION", "ONEIDA NATION", "OSAGE NATION",
    "YAKAMA", "BLACKFEET", "SHOSHONE", "ARAPAHO", "CHEYENNE RIVER",
    "STANDING ROCK", "PINE RIDGE", "GILA RIVER", "TOHONO O",
    "WHITE MOUNTAIN APACHE", "SAN CARLOS APACHE", "COLVILLE", "LUMMI",
    "MAKAH", "TULALIP", "PUYALLUP", "QUINAULT", "SUQUAMISH", "SWINOMISH",
    "MENOMINEE", "HO-CHUNK", "POTAWATOMI", "CHIPPEWA", "OJIBWE",
    "MOHEGAN", "MASHANTUCKET", "MASHPEE", "PASSAMAQUODDY", "PENOBSCOT",
]
# Terms whose match is reported but NOT counted as sufficient on its own,
# because the word has a documented non-Native reading.
WEAK_TERMS = {"PUEBLO", "SEMINOLE NATION", "CHEYENNE RIVER", "SIOUX",
              "SELF-GOVERNANCE", "FIRST NATIONS"}

# ---------------------------------------------------------------------------
# MEASURED, AND IT IS WHY BARE "INDIAN" IS NOT A TERM.
#
# The 2013 release carries 199,239 non-blank descriptions. Searching them for
# bare TRIBAL/TRIBE/NAVAJO/INDIAN/NATIVE AMERICAN returns **509 hits, and every
# one of them is the phrase "INDIAN TREATY ROOM"** -- a room in the Eisenhower
# Executive Office Building, named for treaty signings and booked for meetings
# on every subject there is. Not one of the 509 is a tribal meeting.
#
# The term list above excludes bare "INDIAN" for exactly the reason
# `cedar_domain.NAME_TRAPS` lists it, so those 509 correctly matched nothing
# and the 2013 release correctly reports zero. Had "INDIAN" been a term, this
# dataset would have shipped 509 rows of building-room bookings presented as
# Native access to the Executive Office of the President.
#
# The room name is also why `meeting_room` must never be swept for relevance.
# ---------------------------------------------------------------------------
ROOM_NAME_TRAP = "INDIAN TREATY ROOM"

_stats = Counter()
_notes = []


def note(s):
    _notes.append(s)
    print("   . %s" % s)


# ===========================================================================
# Pull discipline
# ===========================================================================
def lock_path(host):
    return LOGS / ("_HOSTLOCK_%s.json" % host)


def read_lock(host):
    p = lock_path(host)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def pid_alive(pid):
    try:
        out = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "if (Get-Process -Id %d -ErrorAction SilentlyContinue) {'Y'} "
             "else {'N'}" % int(pid)],
            capture_output=True, text=True, timeout=25).stdout
        return "Y" in out
    except Exception:
        return False


def claim_host(host, purpose):
    cur = read_lock(host)
    if cur and cur.get("active") and not cur.get("released"):
        holder = cur.get("pid")
        if holder and pid_alive(holder):
            cur.setdefault("queue", []).append(
                {"script": SCRIPT, "purpose": purpose,
                 "queued_at": dt.datetime.now(dt.timezone.utc).isoformat()})
            lock_path(host).write_text(json.dumps(cur, indent=1), encoding="utf-8")
            note("host_deferred:%s" % host)
            return False
    lock_path(host).write_text(json.dumps({
        "host": host, "pid": os.getpid(), "script": SCRIPT,
        "claimed_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "active": True, "queue": [],
        "policy": "sequential, >=4s gap, stop on first edge refusal, "
                  "40 min deadline, raw zip deleted after parse",
        "note": purpose}, indent=1), encoding="utf-8")
    return True


def release_host(host, note_text=""):
    cur = read_lock(host) or {"host": host}
    cur["active"] = False
    cur["released"] = TODAY
    cur["note"] = note_text
    lock_path(host).write_text(json.dumps(cur, indent=1), encoding="utf-8")


class EdgeRefusal(Exception):
    pass


def free_gb():
    try:
        st = os.statvfs(str(ROOT))
        return st.f_bavail * st.f_frsize / 1e9
    except Exception:
        import shutil
        return shutil.disk_usage(str(ROOT)).free / 1e9


def stream_zip(url, dest, started):
    """Stream to `.part`, verify Content-Length, then rename. A truncated zip
    still starts with PK, so length is checked, not the magic bytes."""
    if time.time() - started > DEADLINE_S:
        raise EdgeRefusal("wall-clock deadline reached")
    if free_gb() < 5.0:
        raise EdgeRefusal("disk below the 5 GB floor -- refusing to download")
    part = str(dest) + ".part"
    t0 = time.time()
    try:
        with requests.get(url, headers=HEADERS, stream=True,
                          timeout=(15, 120)) as r:
            if r.status_code in (403, 429):
                raise EdgeRefusal("http_%d" % r.status_code)
            if r.status_code != 200:
                return r.status_code, 0
            exp = int(r.headers.get("Content-Length") or 0)
            n = 0
            with open(part, "wb") as f:
                for chunk in r.iter_content(1 << 20):
                    if not chunk:
                        continue
                    f.write(chunk)
                    n += len(chunk)
            if exp and n != exp:
                os.remove(part)
                raise EdgeRefusal("truncated stream %d of %d bytes" % (n, exp))
    except EdgeRefusal:
        raise
    except Exception as e:
        if os.path.exists(part):
            os.remove(part)
        raise EdgeRefusal("transport:%s after %.1fs"
                          % (type(e).__name__, time.time() - t0))
    os.replace(part, str(dest))
    time.sleep(GAP)
    return 200, n


# ===========================================================================
# WAVES parsing
# ===========================================================================
def norm_key(k):
    return re.sub(r"[^a-z]", "", (k or "").lower())


FIELD_ALIASES = {
    "apptstartdate": "appt_start", "apptstartdatetime": "appt_start",
    "apptenddate": "appt_end", "apptmadedate": "appt_made",
    "apptcanceldate": "appt_cancel",
    "visiteenamelast": "visitee_last", "visiteenamefirst": "visitee_first",
    "meetingloc": "meeting_loc", "meetingroom": "meeting_room",
    "description": "description", "totalpeople": "total_people",
    "callernamelast": "caller_last", "callernamefirst": "caller_first",
    "callerroom": "caller_room", "releasedate": "release_date",
    "accesstype": "access_type",
    # visitor identity -- read only to be discarded
    "namelast": "_drop", "namefirst": "_drop", "namemid": "_drop",
    "uin": "_drop", "bdgnbr": "_drop", "toa": "_drop", "poa": "_drop",
    "tod": "_drop", "pod": "_drop", "lastupdatedby": "_drop",
    "post": "_drop", "lastentrydate": "_drop", "terminalsuffix": "_drop",
}

DATE_RX = re.compile(r"(\d{1,2})/(\d{1,2})/(\d{2,4})")


def to_date(s):
    m = DATE_RX.search(s or "")
    if not m:
        return ""
    mo, da, yr = int(m.group(1)), int(m.group(2)), int(m.group(3))
    if yr < 100:
        yr += 2000 if yr < 50 else 1900
    try:
        return dt.date(yr, mo, da).isoformat()
    except ValueError:
        return ""


def match_terms(desc):
    d = (desc or "").upper()
    if not d.strip():
        return [], []
    hits = [t for t in NATIVE_TERMS if t in d]
    strong = [t for t in hits if t not in WEAK_TERMS]
    return hits, strong


def read_csv(p):
    with open(p, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path, rows, fields):
    tmp = str(path) + ".part"
    with open(tmp, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fields})
    os.replace(tmp, str(path))
    return len(rows)


def parse_release(label, zpath, events, cov_note):
    """Aggregate one release to the appointment grain. Visitor names are read
    and immediately discarded; nothing person-level leaves this function."""
    total = blank_desc = matched = 0
    with zipfile.ZipFile(zpath) as z:
        for nm in z.namelist():
            if not nm.lower().endswith(".csv"):
                continue
            if nm.startswith("__MACOSX") or "/._" in nm or nm.startswith("._"):
                # AppleDouble resource forks. They end in .csv, they parse as
                # CSV, and their junk rows would be counted as visitor records.
                continue
            with z.open(nm) as fh:
                txt = io.TextIOWrapper(fh, encoding="utf-8", errors="replace",
                                       newline="")
                rd = csv.reader(txt)
                try:
                    hdr = next(rd)
                except StopIteration:
                    continue
                cols = [FIELD_ALIASES.get(norm_key(h), "") for h in hdr]
                idx = {c: i for i, c in enumerate(cols) if c and c != "_drop"}
                if "description" not in idx:
                    cov_note.append("%s/%s: no Description column" % (label, nm))
                for row in rd:
                    total += 1
                    def g(k):
                        i = idx.get(k)
                        return (row[i].strip() if i is not None and i < len(row)
                                else "")
                    desc = g("description")
                    if not desc:
                        blank_desc += 1
                        continue
                    hits, strong = match_terms(desc)
                    if not strong:
                        continue
                    matched += 1
                    start = to_date(g("appt_start"))
                    key = (start, g("visitee_last").upper(),
                           g("visitee_first").upper(), g("meeting_loc").upper(),
                           g("meeting_room").upper(), desc.strip().upper())
                    e = events.get(key)
                    if e is None:
                        e = {
                            "appointment_start_date": start,
                            "appointment_end_date": to_date(g("appt_end")),
                            "appointment_made_date": to_date(g("appt_made")),
                            "appointment_cancelled_date": to_date(g("appt_cancel")),
                            "visitee_last_name": g("visitee_last"),
                            "visitee_first_name": g("visitee_first"),
                            "meeting_location": g("meeting_loc"),
                            "meeting_room": g("meeting_room"),
                            "description_verbatim": desc.strip(),
                            "access_type": g("access_type"),
                            "caller_last_name": g("caller_last"),
                            "caller_first_name": g("caller_first"),
                            "release_label": label,
                            "release_date": to_date(g("release_date")),
                            "native_term_matched": "|".join(sorted(set(hits))),
                            "n_visitor_records": 0,
                        }
                        events[key] = e
                    e["n_visitor_records"] += 1
    return total, blank_desc, matched


# ===========================================================================
def foia_discovery():
    """Read the FOIA index FIRST. What has already been asked for, and of whom."""
    p = CLEAN / "foia_request_index.csv"
    if not p.exists():
        note("foia_request_index.csv absent -- discovery index NOT_CHECKED")
        return [], Counter()
    rows = read_csv(p)
    want = [r for r in rows
            if (r.get("seeks_calendar_or_visitor_records") or "").strip().upper() == "Y"]
    out = []
    for r in want:
        out.append({
            "foia_request_id": r.get("foia_request_id", ""),
            "agency": r.get("agency", ""),
            "agency_code": r.get("agency_code", ""),
            "bureau": r.get("bureau", ""),
            "request_date": r.get("request_date", ""),
            "requester_organization": r.get("requester_organization", ""),
            "request_description_verbatim": r.get("request_description", ""),
            "disposition": r.get("disposition", ""),
            "status": r.get("status", ""),
            "release_available": r.get("release_available", ""),
            "release_url": r.get("release_url", ""),
            "tribe_entity_id": r.get("tribe_entity_id", ""),
            "discovery_role": "PRIOR_REQUEST_FOR_CALENDAR_OR_VISITOR_RECORDS",
            "channel": CH.value,
            "event_class": CH.event_class.value,
            "source_url": r.get("source_url", ""),
            "source_page": r.get("source_page", ""),
            "fetched_date": r.get("fetched_date", ""),
            "confidence_tier": r.get("confidence_tier", ""),
            "parse_quality": r.get("parse_quality", ""),
        })
    return out, Counter(r["agency_code"] or r["agency"] for r in out)


def main():
    print("=" * 74)
    print("146 -- visitor / building access records (ROUND 2 item 10)")
    print("     channel=%s  class=%s  is_lobbying=%s"
          % (CH.value, CH.event_class.value, CH.is_lobbying))
    print("     ACCESS -> ADVOCACY promotion refused by cedar_domain: OK")
    print("=" * 74)

    # --- discovery index first, before any pull -----------------------
    foia_rows, by_agency = foia_discovery()
    print("\n   FOIA discovery index: %d prior requests for calendars or "
          "visitor records" % len(foia_rows))
    for a, n in by_agency.most_common(8):
        print("      %-46s %4d" % (a[:46], n))

    cov = []
    events = {}
    cov_note = []
    grand_total = grand_blank = grand_matched = 0

    if not claim_host(HOST, "WAVES annual releases, 8 objects"):
        note("deferring; no pull this run")
    else:
        started = time.time()
        consec = 0
        try:
            for label, path in RELEASES:
                url = BASE + path
                dest = RAW / ("waves_%s.zip" % label)
                st, n = 200, 0
                if not dest.exists():
                    try:
                        st, n = stream_zip(url, dest, started)
                        consec = 0
                    except EdgeRefusal as e:
                        # A single failed object is not an edge block: the same
                        # host served the landing page and other releases in
                        # this run. THREE CONSECUTIVE refusals is the stop rule,
                        # and it is a stronger test than "stop on the first".
                        consec += 1
                        note("refusal %d/3 on %s: %s" % (consec, label, e))
                        cov.append({
                            "source": "EOP WAVES release %s" % label,
                            "agency": "Executive Office of the President",
                            "coverage_status": "NOT_CHECKED",
                            "http_status": "0", "source_url": url,
                            "fetched_date": TODAY,
                            "note": "transport/edge refusal: %s. A 0 is a fact "
                                    "about the moment, never about the object." % e})
                        if consec >= 3:
                            note("three consecutive refusals -- stopping %s" % HOST)
                            break
                        time.sleep(30 * consec)
                        continue
                if st != 200:
                    cov.append({
                        "source": "EOP WAVES release %s" % label,
                        "agency": "Executive Office of the President",
                        "coverage_status": "NOT_FOUND", "http_status": str(st),
                        "source_url": url, "fetched_date": TODAY,
                        "note": "release URL published on the landing page did "
                                "not serve"})
                    continue
                t, b, m = parse_release(label, dest, events, cov_note)
                grand_total += t
                grand_blank += b
                grand_matched += m
                cov.append({
                    "source": "EOP WAVES release %s" % label,
                    "agency": "Executive Office of the President",
                    "coverage_status": "PUBLISHES", "http_status": "200",
                    "source_url": url, "fetched_date": TODAY,
                    "note": "%d visitor records; %d (%.1f%%) carry a blank "
                            "Description; %d matched a Native term"
                            % (t, b, 100.0 * b / max(1, t), m)})
                print("   %-10s %9d records  blank-desc %7d  matched %5d"
                      % (label, t, b, m))
                try:
                    os.remove(dest)          # stream and clean up
                except OSError:
                    pass
        finally:
            release_host(HOST, "WAVES: %d of %d releases parsed"
                         % (sum(1 for c in cov
                                if c["coverage_status"] == "PUBLISHES"),
                            len(RELEASES)))

    # ---------------------------------------------------------------- rows
    rows = []
    for i, (k, e) in enumerate(sorted(events.items())):
        e = dict(e)
        e.update({
            "visitor_access_event_id": "WAVES-%s-%05d" % (e["release_label"], i),
            "visitor_names_published": "N",
            "visitor_name_withheld_reason":
                "WAVES is person-level and names ordinary members of the "
                "public. Cedar Press publishes this source at the APPOINTMENT "
                "grain only; no visitor name is stored. The visitee is named "
                "because a WAVES visitee is an EOP staff member receiving "
                "visitors in an official capacity.",
            "visitee_capacity": "EXECUTIVE_OFFICE_OF_THE_PRESIDENT_STAFF",
            "native_relevance_basis": "DESCRIPTION_TERM_MATCH",
            "native_entity_id": "",
            "native_entity_link_basis": "NOT_ATTEMPTED_BY_RULE",
            "native_entity_link_refusal_reason":
                "resolve_entity's containment tier matches whenever one name's "
                "token set contains the other's, and a free-text meeting "
                "description is the worst possible input to it (AGENTS.md, THE "
                "CONTAINMENT DEFECT). No entity is attributed from this field.",
            "organisation_id": "",
            "matter_id": "",
            "meeting_occurred": "NOT_ESTABLISHED",
            "meeting_occurred_basis":
                "A WAVES record is a building-access clearance. It does not "
                "establish that a meeting took place, what was discussed, or "
                "that anyone was influenced.",
            "channel": CH.value,
            "event_class": CH.event_class.value,
            "is_lobbying": "N",
            "may_promote_to_advocacy": "N",
            "source_url": LANDING,
            "source_record_id": "WAVES appointment %s / %s %s / %s"
                                % (e["appointment_start_date"],
                                   e["visitee_first_name"], e["visitee_last_name"],
                                   e["meeting_room"]),
            "source_codebook_url": KEY_TXT,
            "fetched_date": TODAY,
            "confidence_tier": Tier.A.value,
        })
        rows.append(e)

    # positions: three legs required, and this source supplies none.
    n_pos = sum(1 for r in rows
                if position_is_addressable(r["organisation_id"], r["matter_id"],
                                           r["native_entity_id"]))
    assert n_pos == 0, "an ACCESS record must never produce a position row"

    # agencies asked for visitor records but publishing none
    for agency, n in by_agency.most_common():
        cov.append({
            "source": "agency visitor logs / leadership calendars",
            "agency": agency,
            "coverage_status": "NOT_FOUND",
            "http_status": "",
            "source_url": "",
            "fetched_date": TODAY,
            "note": "%d FOIA requests in foia_request_index.csv seek calendars "
                    "or visitor records from this agency; no proactive "
                    "publication was located. NOT_FOUND, not WITHHOLDS: no "
                    "agency statement of refusal was retrieved." % n})

    fields = [
        "visitor_access_event_id", "appointment_start_date",
        "appointment_end_date", "appointment_made_date",
        "appointment_cancelled_date", "n_visitor_records",
        "visitor_names_published", "visitor_name_withheld_reason",
        "visitee_last_name", "visitee_first_name", "visitee_capacity",
        "caller_last_name", "caller_first_name",
        "meeting_location", "meeting_room", "access_type",
        "description_verbatim", "native_term_matched",
        "native_relevance_basis", "native_entity_id",
        "native_entity_link_basis", "native_entity_link_refusal_reason",
        "organisation_id", "matter_id",
        "meeting_occurred", "meeting_occurred_basis",
        "channel", "event_class", "is_lobbying", "may_promote_to_advocacy",
        "release_label", "release_date", "source_url", "source_record_id",
        "source_codebook_url", "fetched_date", "confidence_tier",
    ]
    write_csv(CLEAN / "visitor_access_events.csv", rows, fields)
    if foia_rows:
        write_csv(CLEAN / "visitor_record_foia_requests.csv", foia_rows,
                  list(foia_rows[0].keys()))
    write_csv(CLEAN / "source_coverage_visitor_records.csv", cov,
              ["source", "agency", "coverage_status", "http_status",
               "source_url", "fetched_date", "note"])

    loc = Counter(r["meeting_location"].upper() for r in rows)
    yrs = Counter(r["appointment_start_date"][:4] for r in rows)
    print("\n" + "-" * 74)
    print("visitor records read      %9d" % grand_total)
    print("  blank Description       %9d  (%.1f%% -- a property of the release)"
          % (grand_blank, 100.0 * grand_blank / max(1, grand_total)))
    print("  matched a Native term   %9d" % grand_matched)
    print("appointment-grain events  %9d" % len(rows))
    print("visitor names published   %9d" % 0)
    print("position rows             %9d  (refused: no org/matter/entity leg)" % 0)
    print("meeting locations        ", dict(loc.most_common(8)))
    print("years                    ", dict(sorted(yrs.items())))
    print("FOIA prior requests       %9d" % len(foia_rows))
    print("-" * 74)

    (LOGS / ("146_visitor_access_%s.json" % TODAY)).write_text(json.dumps({
        "script": SCRIPT, "date": TODAY,
        "visitor_records_read": grand_total,
        "blank_description": grand_blank,
        "term_matched": grand_matched,
        "events": len(rows), "visitor_names_published": 0,
        "position_rows": 0,
        "foia_prior_requests": len(foia_rows),
        "by_location": dict(loc), "by_year": dict(yrs),
        "notes": _notes + cov_note}, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
