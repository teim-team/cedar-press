#!/usr/bin/env python3
r"""
Cedar Press - 1089: `consultation_events.csv` in place -
(A) state the NAGPRA overlap ON THE ROW, and
(B) parse the consultation EVENT date and place out of notice bodies already
    on disk.

    py -3 code/1089_fr_consultation_overlap_and_event_parse.py measure   # read-only
    py -3 code/1089_fr_consultation_overlap_and_event_parse.py apply
    py -3 code/1089_fr_consultation_overlap_and_event_parse.py verify
    py -3 code/1089_fr_consultation_overlap_and_event_parse.py --selftest

THIS IS AN IN-PLACE ENRICHER AND IT MUST RUN AFTER `96`
--------------------------------------------------------
`code/96_build_consultation_events.py` REBUILDS `consultation_events.csv` from
its own inputs and would revert every column below - the rebuild-reverts-
enricher collision that `docs/methodology/federal-register.md` says "has now
bitten this project four times in one day". The ordering
`96 -> 1089` is registered in `cedar_pipeline.KNOWN_ORDERINGS`, which is what
`build.py`, `62`'s enricher check and `293` class6 all read.

--------------------------------------------------------------------------
(A) THE NAGPRA OVERLAP - measured, then written on the row
--------------------------------------------------------------------------
`consultation_events.csv` is 11,402 rows and **10,888 (95.5%) are typed
`NAGPRA_consultation_reported`**, while `nagpra` ships as its own Cedar dataset
(`nagpra_notices.csv`, 6,792 notices). A buyer holding both must be able to see
the overlap without recomputing it, or the same notice is counted twice.

**But "95.5% NAGPRA" and "a duplicate of the nagpra dataset" are two different
claims, and the second one is false.** Measured 2026-09-02:

    consultation_events rows whose FR document is also a nagpra_notices row
                                                        10,920 / 11,402 (95.77%)
    DISTINCT FR documents in consultation_events                        2,313
      ... that are nagpra_notices rows                                  1,831
    nagpra_notices rows NOT represented here at all             4,961 / 6,792

**So this file sees 27.0% of the NAGPRA notice universe, and the 95.5% is a ROW
share, not a document share** - the rows are per (notice, participant), so
1,831 notices occupy 10,920 rows. And the coverage is a WINDOW, not a sample:

    1994-2010   0 of 1,882 NAGPRA notices        (0.0%)
    2011-2022   1,817 of 2,264                  (80.3%)
    2023-2026   14 of 2,646                      (0.5%)

`96`'s universe is `fr_consultation_referenced.csv`, which finds notices by the
Federal Register's *"in consultation with representatives of"* drafting
convention. **Revised 43 CFR 10 took effect 2024-01-12 and replaced that
sentence with a bulleted "Determinations" list, so the net stops catching them
- exactly when NAGPRA notice volume triples.** That is written on the row as
`nagpra_coverage_window`, not left in a build log.

Three columns are added, each a MEASUREMENT and not an opinion:

  `fr_document_number`      the Federal Register document number, parsed from
                            the row's own `source_url`. This file had no join
                            key to any other FR table; now it has the one the
                            whole corpus is keyed on.
  `nagpra_notice_overlap`   `same_notice_in_nagpra_notices`
                            `not_in_nagpra_notices`
  `nagpra_bridge_overlap`   `same_notice_and_party_in_nagpra_bridge`
                            `same_notice_different_party`
                            `notice_not_in_nagpra_dataset`
                            `no_tribe_resolved_on_this_row`

**This script never writes `nagpra_notices.csv` or
`nagpra_notice_entity_bridge.csv`.** It opens them read-only. Another agent
owns them.

--------------------------------------------------------------------------
(B) THE EVENT DATE AND PLACE - ON_DISK_NOT_PROMOTED, not a fetch
--------------------------------------------------------------------------
`event_start_date` was filled on **93 of 11,402 rows** and `location` on **60**.
`py -3 code/1050_preflight.py ondisk federal_register` and a direct count both
say the same thing: **all 2,313 notice texts are already on this machine**, in
`data/raw/external/consultation/fr_text/`. This is a parse. Zero requests.

`96`'s parser reads dates ONLY out of the `DATES:` field and places ONLY out of
`ADDRESSES:`, and it has three measured misses:

  1. `\bmeeting\b` does not match "meetings". A notice saying *"All meetings
     will begin at 9:00 A.M."* fails the meeting-word test that gates the date.
  2. Compressed date lists. *"DATES: October 13, 17, 19, 21, 24, 26, and 28,
     1994"* yields at most one date to a `Month DD, YYYY` regex.
  3. The Federal Register's consultation TABLE convention -
     `January 9, 1995: ... Minnesota, Minneapolis` - is `State, City`, which a
     `City, State` regex cannot see, and it sits past `ADDRESSES:`'s 2,000
     character cap.

WHAT THIS PARSER WILL AND WILL NOT DO
--------------------------------------
**It never infers a date or a place the notice does not state.** Every filled
cell carries the publisher's own sentence in `event_date_source_quote` /
`location_source_quote` and a named rule in `*_basis`. Specifically:

  * A date is taken ONLY from a sentence that also carries an event verb
    (`will be held`, `will convene`, `is scheduled`, `was held on`, ...) or
    from the `DATES:` field of a notice whose own `ACTION:` line says it is a
    notice OF MEETINGS. `96`'s `fallback_year` - which supplies a year the
    notice did not print - is NOT used.
  * Any sentence naming a comment deadline, a submission, a publication date,
    an effective date, or a CANCELLATION is refused outright, because the most
    likely way to be wrong here is to publish a comment deadline as a meeting.
  * A place is taken only from a segment that is meeting-anchored, and never
    from a "mail your comments to" sentence or a signature block.
  * **Existing values are never overwritten.** The 93 dates and 60 locations
    `96` already wrote stay exactly as they are; this only fills blanks. So the
    before/after is a clean addition and row conservation is trivially checkable.
  * A blank still means the source did not say it.

CONSERVATION
------------
Row conservation is proved on every run: rows in == rows out, and the multiset
of `consultation_event_id` is identical. **There is no money column in this
table** - `csv` header carries none, and the run prints that finding rather
than a zero, because a zero would look like a measurement.

READS   data/clean/consultation_events.csv            (writes IN PLACE)
        data/clean/nagpra_notices.csv                 (READ ONLY)
        data/clean/nagpra_notice_entity_bridge.csv    (READ ONLY)
        data/raw/external/consultation/fr_text/*.txt  (2,313 cached notices)
WRITES  data/clean/consultation_events.csv            (+8 columns, 0 rows)
        review/consultation_event_parse_audit_<date>.csv  (seeded 40-row sample)
        docs/CONSULTATION_OVERLAP_AND_EVENTS.json

INVARIANTS - exit 1
-------------------
  INV-CE-ROWS      rows out == rows in, and the consultation_event_id multiset
                   is unchanged.
  INV-CE-COLS      no column is lost; every original column keeps its value on
                   every row.
  INV-CE-NOGUESS   every non-blank `event_start_date` this script wrote is a
                   substring-derivable date of its own `event_date_source_quote`,
                   and every non-blank `location` it wrote appears in its own
                   `location_source_quote`. A cell with no quote is a defect.
  INV-CE-NOCLOBBER no pre-existing non-blank `event_start_date`,
                   `event_end_date` or `location` changed value.
  INV-CE-OVERLAP   `nagpra_notice_overlap` is non-blank on every row and says
                   `same_notice_in_nagpra_notices` only where the row's
                   `fr_document_number` is literally present in
                   `nagpra_notices.csv`.
"""
from __future__ import annotations

import csv
import datetime as dt
import html as htmlmod
import json
import random
import re
import shutil
import sys
from collections import Counter, defaultdict
from pathlib import Path

CEDAR = Path(__file__).resolve().parent.parent
CLEAN = CEDAR / "data" / "clean"
REVIEW = CEDAR / "review"
DOCS = CEDAR / "docs"
FRTEXT = CEDAR / "data" / "raw" / "external" / "consultation" / "fr_text"
SCRIPT = "code/1089_fr_consultation_overlap_and_event_parse.py"
STEM = "1089_fr_consultation_overlap_and_event_parse"
TODAY = dt.date.today().isoformat()

TABLE = CLEAN / "consultation_events.csv"
NAGPRA_NOTICES = CLEAN / "nagpra_notices.csv"
NAGPRA_BRIDGE = CLEAN / "nagpra_notice_entity_bridge.csv"
OUT_JSON = DOCS / "CONSULTATION_OVERLAP_AND_EVENTS.json"
AUDIT = REVIEW / f"consultation_event_parse_audit_{TODAY}.csv"

NEW_COLS = [
    "fr_document_number",
    "nagpra_notice_overlap",
    "nagpra_bridge_overlap",
    "nagpra_coverage_window",
    "event_date_basis",
    "event_date_source_quote",
    "location_basis",
    "location_source_quote",
]

csv.field_size_limit(10_000_000)

# ---------------------------------------------------------------- text tools

TAGS = re.compile(r"<[^>]+>")
DOCNUM = re.compile(
    r"^https://www\.federalregister\.gov/documents/\d{4}/\d{2}/\d{2}/([^/]+)/")

MONTHS = {m.lower(): i for i, m in enumerate(
    ["January", "February", "March", "April", "May", "June", "July", "August",
     "September", "October", "November", "December"], 1)}
MN = "|".join(list(MONTHS) + [m[:3] for m in MONTHS])

# "October 13, 17, 19, 21, 24, 26, and 28, 1994"  and  "April 18-20, 2007"
# The YEAR must be printed in the same construction. `96`'s `fallback_year`
# supplies a year the notice never printed; that is an inference and it is not
# used here.
DATE_LIST = re.compile(
    rf"\b({MN})\.?\s+"
    rf"((?:\d{{1,2}}\s*(?:[-–]\s*\d{{1,2}})?\s*,\s*)*"
    rf"(?:and\s+)?\d{{1,2}}(?:\s*[-–]\s*\d{{1,2}})?)"
    rf"\s*,?\s*(\d{{4}})\b", re.I)

EVENT_VERB = re.compile(
    r"(will be held|will be conducted|will be hosted|will convene|"
    r"will take place|will conduct|will host|will meet|is scheduled|"
    r"are scheduled|shall be held|was held on|were held on|meetings? will|"
    r"sessions? will|hearings? will|consultations? will be|will begin at)",
    re.I)

# The single most likely way to be wrong here is to publish a COMMENT DEADLINE
# as a meeting date. Every one of these kills the sentence outright.
NOT_AN_EVENT = re.compile(
    r"(comment|received (?:no later|in writing|by|on or before)|"
    r"must be received|no later than|postmark|deadline|\bdue\b|\bsubmit|"
    r"written (?:input|statement|suggestion|material)|"
    r"published in the federal register|publication of this notice|"
    r"effective date|expire|registration (?:is|must|deadline)|\brsvp\b|"
    r"nomination|cancel|postpone|has been removed|rescheduled from|"
    r"signed at|dated at)", re.I)

MEETING_ACTION = re.compile(
    r"notice of .{0,40}?"
    r"(meeting|session|hearing|consultation|summit|webinar|conference)", re.I)

STATES = ["Alabama", "Alaska", "Arizona", "Arkansas", "California", "Colorado",
          "Connecticut", "Delaware", "Florida", "Georgia", "Hawaii", "Idaho",
          "Illinois", "Indiana", "Iowa", "Kansas", "Kentucky", "Louisiana",
          "Maine", "Maryland", "Massachusetts", "Michigan", "Minnesota",
          "Mississippi", "Missouri", "Montana", "Nebraska", "Nevada",
          "New Hampshire", "New Jersey", "New Mexico", "New York",
          "North Carolina", "North Dakota", "Ohio", "Oklahoma", "Oregon",
          "Pennsylvania", "Rhode Island", "South Carolina", "South Dakota",
          "Tennessee", "Texas", "Utah", "Vermont", "Virginia", "Washington",
          "West Virginia", "Wisconsin", "Wyoming", "District of Columbia"]
SN = "|".join(sorted(STATES, key=len, reverse=True))
AB = ("AL|AK|AZ|AR|CA|CO|CT|DE|FL|GA|HI|ID|IL|IN|IA|KS|KY|LA|ME|MD|MA|MI|MN|"
      "MS|MO|MT|NE|NV|NH|NJ|NM|NY|NC|ND|OH|OK|OR|PA|RI|SC|SD|TN|TX|UT|VT|VA|"
      "WA|WV|WI|WY|DC")
STATE_SET = {s.lower() for s in STATES}
ABBR_SET = set(AB.split("|"))

CITY_STATE = re.compile(
    rf"\b([A-Z][A-Za-z.'\-]*(?:\s+[A-Z][A-Za-z.'\-]*){{0,3}}),\s*({SN}|{AB})\b")
# The Federal Register's consultation-table convention is `State, City`
# ("Minnesota, St. Paul"). A City,State regex cannot see it.
STATE_CITY = re.compile(
    rf"\b({SN}),\s*([A-Z][A-Za-z.'\-]*(?:\s+[A-Z][A-Za-z.'\-]*){{0,3}})\b")

MAIL_TO = re.compile(
    r"(mail|send|submit|address(?:ed)? to|attention|attn|box|"
    r"mail stop|fax|e-?mail|comments|telephone|suite|should contact|"
    r"may contact|signed at|dated at|cancel|postpone|has been removed|"
    r"were removed from|repatriat)", re.I)
# `\b(?!\d)` matters: without it "May 1997" reads as "May 19".
DATE_ROW = re.compile(rf"\b({MN})\s+\d{{1,2}}\b(?!\d)", re.I)

FIELD = {
    "dates": re.compile(
        r"\bDATES?:\s*(.{0,4000}?)(?=\s(?:ADDRESSES|FOR FURTHER|SUPPLEMENTARY|"
        r"SUMMARY|AGENCY|ACTION):|$)", re.S),
    "addresses": re.compile(
        r"\bADDRESSES?:\s*(.{0,6000}?)(?=\s(?:FOR FURTHER|SUPPLEMENTARY|DATES|"
        r"SUMMARY|AGENCY|ACTION):|$)", re.S),
    "action": re.compile(
        r"\bACTION:\s*(.{0,300}?)(?=\s(?:SUMMARY|DATES|ADDRESSES):|$)", re.S),
    "supp": re.compile(r"\bSUPPLEMENTARY INFORMATION:\s*(.{0,40000})", re.S),
}


def flatten(t):
    return re.sub(r"\s+", " ", htmlmod.unescape(TAGS.sub(" ", t))).strip()


def sentences(t):
    return [s for s in re.split(r"(?<=[.;])\s+", t) if s.strip()]


def table_segments(t):
    """Split a flattened ADDRESSES/DATES field into rows.

    The Federal Register lays consultation locations out as a table whose rows
    are separated by nothing a sentence splitter can see, so the row boundary
    is taken to be the START OF A DATE - which is exactly how the table is
    drawn. Splitting on raw newlines instead cuts `Oklahoma City, OK` in half
    at the wrap and yields the phantom place `City, OK`; this was measured on
    document 01-30327 before the field was flattened first.
    """
    parts = re.split(r"(?=\b(?:" + MN + r")\s+\d{1,2}\b(?!\d))", t)
    out = []
    for p in parts:
        out += [s for s in re.split(r"(?<=[.;])\s+", p) if s.strip()]
    return out


def iso_dates(text):
    """Every date the text PRINTS, with its year. Never a guessed year."""
    out = []
    for m in DATE_LIST.finditer(text):
        key = m.group(1).lower()
        mo = MONTHS.get(key) or MONTHS.get(
            next((k for k in MONTHS if k.startswith(key[:3])), ""), None)
        year = int(m.group(3))
        if not mo or not (1990 <= year <= 2035):
            continue
        for part in re.split(r",|\band\b", m.group(2)):
            part = part.strip()
            rng = re.match(r"^(\d{1,2})\s*[-–]\s*(\d{1,2})$", part)
            if rng:
                a, b = int(rng.group(1)), int(rng.group(2))
                days = list(range(a, b + 1)) if a <= b else [a, b]
            elif part.isdigit():
                days = [int(part)]
            else:
                days = []
            for d in days:
                try:
                    out.append(dt.date(year, mo, d).isoformat())
                except ValueError:
                    pass                      # February 30 is not a date
    return sorted(set(out))


# A street fragment is not a city. "2401 M Street, NW, Washington, DC" yields
# the phantom `NW, Washington`; "11111 North 7th Street, West Dunlap Avenue
# Phoenix, AZ" yields `West Dunlap Avenue Phoenix, AZ`. Both are printed by the
# notice and neither is a place name, so they are refused. Directionals are
# only refused STANDING ALONE or beside a street word, so `North Little Rock`
# and `West Valley City` survive.
STREET_TOKEN = re.compile(
    r"(Avenue|Ave|Street|Road|Boulevard|Blvd|Drive|Suite|Floor|Room|"
    r"Parkway|Highway|Zone|Building|Plaza|Hotel|Resort|Hall|Center|Centre|"
    r"NW|NE|SW|SE)", re.I)
STATE_TO_AB = {
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


def _canon(city, state):
    st = state.upper() if state.upper() in ABBR_SET else         STATE_TO_AB.get(state.lower(), state.lower())
    return (re.sub(r"[^a-z]", "", city.lower()), st)


def places_in(segment):
    """Place strings the segment PRINTS, in the publisher's own word order."""
    hits, seen = [], set()

    def add(text, city, state):
        if STREET_TOKEN.search(city) or len(city.strip()) < 3:
            return
        k = _canon(city, state)
        if k in seen:
            return
        seen.add(k)
        hits.append(text)

    for city, state in CITY_STATE.findall(segment):
        add(f"{city.strip()}, {state}", city, state)
    for state, city in STATE_CITY.findall(segment):
        # "Washington, DC" also matches State,City as ("Washington", "DC").
        # A second capture of the same span is not a second place.
        if city in ABBR_SET or city.lower() in STATE_SET:
            continue
        add(f"{state}, {city.strip()}", city, state)
    return [h for h in hits if len(h) > 4]


def parse_notice(text):
    """(event_dates, date_quote, date_basis, places, loc_quote, loc_basis)."""
    f = {}
    for k, rx in FIELD.items():
        m = rx.search(text)
        f[k] = flatten(m.group(1)) if m else ""

    # EVERY contributing sentence goes into the quote, not just the first.
    # A quote that does not print the date beside it is not evidence for it -
    # INV-CE-NOGUESS caught exactly that on 94-19169 before this was fixed.
    dates, dqs, db = [], [], ""
    for s in sentences(f["dates"]):
        if EVENT_VERB.search(s) and not NOT_AN_EVENT.search(s):
            got = iso_dates(s)
            if got:
                dates += got
                dqs.append(s)
                db = "dates_field_sentence_with_an_event_verb"
    if not dates and MEETING_ACTION.search(f["action"]):
        for s in table_segments(f["dates"]):
            if NOT_AN_EVENT.search(s):
                continue
            got = iso_dates(s)
            if got:
                dates += got
                dqs.append(s)
                db = ("dates_field_of_a_notice_whose_own_ACTION_line_says_"
                      "notice_of_meetings")
    if not dates:
        for s in sentences(f["supp"]):
            if EVENT_VERB.search(s) and not NOT_AN_EVENT.search(s):
                got = iso_dates(s)
                if got:
                    dates += got
                    dqs.append(s)
                    db = "supplementary_information_sentence_with_an_event_verb"
                    break
    dq = " | ".join(dict.fromkeys(dqs))[:2000]

    # A LOCATION IS THE LOCATION OF AN EVENT, and a notice that announces no
    # event has none. Measured before this guard existed: 657 of 703 new
    # locations landed on `NAGPRA_consultation_reported` rows and every one
    # sampled was a MUSEUM CONTACT ADDRESS or an EXCAVATION COUNTY -
    # "Cambridge, MA" from "should contact Patricia Capone, Peabody Museum",
    # "Coconino County, AZ" from where remains were removed in 1985. Both are
    # real places the notice prints; neither is where a consultation was held.
    # So: the notice must announce a meeting before any place is read as one.
    is_meeting_notice = bool(dates) or bool(MEETING_ACTION.search(f["action"]))
    places, lqs, lb = [], [], ""
    if not is_meeting_notice:
        return sorted(set(dates)), dq, db, [], "", ""
    for src, label in ((f["addresses"], "addresses_field"),
                       (f["dates"], "dates_field"),
                       (f["supp"], "supplementary_information")):
        for s in table_segments(src):
            # the ADDRESSES table convention pairs a date with a place, and it
            # only means a meeting inside a notice OF meetings
            anchored = bool(EVENT_VERB.search(s)) or (
                label == "addresses_field" and bool(DATE_ROW.search(s))
                and bool(MEETING_ACTION.search(f["action"])))
            if not anchored or MAIL_TO.search(s):
                continue
            got = places_in(s)
            if got:
                places += got
                lqs.append(s)
                lb = lb or f"{label}_segment_anchored_to_a_meeting"
        if places:
            break
    places = list(dict.fromkeys(places))[:12]
    # keep only the segments that actually print a place we kept, and keep
    # ALL of them, so every place in the cell is printed by its own quote
    lqs = [q for q in dict.fromkeys(lqs) if any(p in places_in(q)
                                                for p in places)]
    return (sorted(set(dates)), dq, db, places,
            " | ".join(lqs)[:2000], lb)


# ---------------------------------------------------------------- the pass


def load_nagpra():
    """READ ONLY. Another agent owns these two files."""
    if not NAGPRA_NOTICES.exists():
        return None, None
    notes = set()
    with open(NAGPRA_NOTICES, newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            notes.add(r["document_number"])
    pairs = set()
    if NAGPRA_BRIDGE.exists():
        with open(NAGPRA_BRIDGE, newline="", encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                if r.get("tribe_id"):
                    pairs.add((r["document_number"], r["tribe_id"]))
    return notes, pairs


def coverage_window(year):
    """The window `96`'s net actually covers, stated on the row.

    Not an opinion: it is the measured shape of the join, and its cause is the
    2024-01-12 revision of 43 CFR 10 replacing the drafting convention the net
    keys on.
    """
    if not year.isdigit():
        return ""
    y = int(year)
    if y <= 2010:
        return "before_this_files_nagpra_window_opens_2011"
    if y >= 2023:
        return "after_the_2024_43_CFR_10_rewrite_broke_the_consultation_sentence_net"
    return "inside_the_2011_2022_nagpra_window"


def build(rows, notes, pairs, texts_root=FRTEXT):
    """Returns (new_rows, stats). Pure over `rows` - takes no backup, writes
    nothing. `apply` is the only caller that touches disk."""
    stats = Counter()
    docs = {}
    for r in rows:
        m = DOCNUM.match(r.get("source_url", ""))
        r["_doc"] = m.group(1) if m else ""
        if r["_doc"]:
            docs.setdefault(r["_doc"], None)
    parsed = {}
    for d in docs:
        p = texts_root / f"{d}.txt"
        if not p.exists():
            stats["doc_text_not_on_disk"] += 1
            continue
        parsed[d] = parse_notice(p.read_text(encoding="utf-8", errors="replace"))
        stats["doc_text_read"] += 1

    out = []
    for r in rows:
        n = dict(r)
        d = n.pop("_doc")
        n["fr_document_number"] = d
        if notes is None:
            n["nagpra_notice_overlap"] = "UNMEASURED_nagpra_notices_absent"
            n["nagpra_bridge_overlap"] = "UNMEASURED_nagpra_notices_absent"
        elif d and d in notes:
            n["nagpra_notice_overlap"] = "same_notice_in_nagpra_notices"
            tid = (r.get("tribe_id") or "").strip()
            if not tid:
                n["nagpra_bridge_overlap"] = "no_tribe_resolved_on_this_row"
            elif (d, tid) in pairs:
                n["nagpra_bridge_overlap"] = \
                    "same_notice_and_party_in_nagpra_bridge"
            else:
                n["nagpra_bridge_overlap"] = "same_notice_different_party"
        else:
            n["nagpra_notice_overlap"] = "not_in_nagpra_notices"
            n["nagpra_bridge_overlap"] = "notice_not_in_nagpra_dataset"
        stats[f"overlap::{n['nagpra_notice_overlap']}"] += 1
        stats[f"bridge::{n['nagpra_bridge_overlap']}"] += 1

        n["nagpra_coverage_window"] = coverage_window(
            (r.get("notice_date") or "")[:4]) \
            if n["nagpra_notice_overlap"] == "same_notice_in_nagpra_notices" \
            else ""

        n.setdefault("event_date_basis", "")
        n.setdefault("event_date_source_quote", "")
        n.setdefault("location_basis", "")
        n.setdefault("location_source_quote", "")
        got = parsed.get(d)
        if got:
            dates, dq, db, places, lq, lb = got
            if dates and not (r.get("event_start_date") or "").strip():
                n["event_start_date"] = dates[0]
                n["event_end_date"] = dates[-1]
                n["event_date_basis"] = db
                n["event_date_source_quote"] = dq
                stats["rows_gained_event_date"] += 1
            if places and not (r.get("location") or "").strip():
                n["location"] = "; ".join(places)[:300]
                n["location_basis"] = lb
                n["location_source_quote"] = lq
                stats["rows_gained_location"] += 1
        out.append(n)
    return out, stats


# ---------------------------------------------------------------- invariants


def check(before, after, notes):
    """(invariant, message) list. Empty == clean."""
    bad = []
    if len(after) != len(before):
        bad.append(("INV-CE-ROWS",
                    f"{len(before)} rows in, {len(after)} rows out"))
        return bad
    if Counter(r["consultation_event_id"] for r in before) != \
            Counter(r["consultation_event_id"] for r in after):
        bad.append(("INV-CE-ROWS",
                    "the consultation_event_id multiset changed"))
        return bad
    frozen = [c for c in before[0]
              if c not in ("event_start_date", "event_end_date", "location")]
    for b, a in zip(before, after):
        for c in frozen:
            if a.get(c) != b.get(c):
                bad.append(("INV-CE-COLS",
                            f"{b['consultation_event_id']}: column {c!r} "
                            f"changed {b.get(c)!r} -> {a.get(c)!r}"))
                return bad
        for c in ("event_start_date", "event_end_date", "location"):
            if (b.get(c) or "").strip() and a.get(c) != b.get(c):
                bad.append(("INV-CE-NOCLOBBER",
                            f"{b['consultation_event_id']}: pre-existing {c} "
                            f"{b.get(c)!r} overwritten with {a.get(c)!r}"))
                return bad
    for b, a in zip(before, after):
        if a.get("event_date_basis"):
            q = a.get("event_date_source_quote", "")
            if not q:
                bad.append(("INV-CE-NOGUESS",
                            f"{a['consultation_event_id']}: an event date with "
                            f"no source quote"))
                return bad
            if a["event_start_date"] not in iso_dates(q):
                bad.append(("INV-CE-NOGUESS",
                            f"{a['consultation_event_id']}: event_start_date "
                            f"{a['event_start_date']} is not a date its own "
                            f"quote prints"))
                return bad
        if a.get("location_basis"):
            q = a.get("location_source_quote", "")
            if not q:
                bad.append(("INV-CE-NOGUESS",
                            f"{a['consultation_event_id']}: a location with no "
                            f"source quote"))
                return bad
            first = a["location"].split(";")[0].strip()
            if first and first not in places_in(q):
                bad.append(("INV-CE-NOGUESS",
                            f"{a['consultation_event_id']}: location {first!r} "
                            f"is not a place its own quote prints"))
                return bad
    for a in after:
        v = a.get("nagpra_notice_overlap", "")
        if not v:
            bad.append(("INV-CE-OVERLAP",
                        f"{a['consultation_event_id']}: blank "
                        f"nagpra_notice_overlap"))
            return bad
        if v == "same_notice_in_nagpra_notices" and notes is not None \
                and a["fr_document_number"] not in notes:
            bad.append(("INV-CE-OVERLAP",
                        f"{a['consultation_event_id']}: claims a NAGPRA "
                        f"overlap for {a['fr_document_number']}, which is not "
                        f"in nagpra_notices.csv"))
            return bad
    return bad


# ---------------------------------------------------------------- io


def read_table(path=TABLE):
    with open(path, newline="", encoding="utf-8") as fh:
        r = csv.DictReader(fh)
        return list(r), list(r.fieldnames)


def write_table(path, cols, rows):
    part = path.with_suffix(path.suffix + ".part")
    with open(part, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)
    part.replace(path)


def money_columns(cols):
    return [c for c in cols
            if re.search(r"amount|dollar|obligat|revenue|_usd|cost|value$",
                         c, re.I)]


def report(before, after, cols, stats, notes, pairs, apply_mode):
    money = money_columns(cols)
    print(f"[1089] ROW CONSERVATION  in {len(before):,}  out {len(after):,}  "
          f"delta {len(after) - len(before)}")
    if money:
        for c in money:
            def tot(rs):
                s = 0.0
                for r in rs:
                    try:
                        s += float(str(r.get(c, "")).replace(",", "") or 0)
                    except ValueError:
                        pass
                return s
            print(f"[1089] MONEY CONSERVATION {c}: {tot(before):,.2f} -> "
                  f"{tot(after):,.2f}")
    else:
        print("[1089] MONEY CONSERVATION  NOT APPLICABLE - this table declares "
              "no money column. Printing 0.00 -> 0.00 would look like a "
              "measurement of something.")
    def n(col):
        return (sum(1 for r in before if (r.get(col) or "").strip()),
                sum(1 for r in after if (r.get(col) or "").strip()))
    for col in ("event_start_date", "event_end_date", "location"):
        b, a = n(col)
        print(f"[1089] {col:20s} {b:6,} -> {a:6,}   (+{a - b:,}, "
              f"{a / len(after) * 100:.1f}% of rows)")
    docs_b = len({r["fr_document_number"] for r in after
                  if (r.get("event_start_date") or "")})
    print(f"[1089] distinct FR documents now carrying an event date: {docs_b:,}"
          f" of {len({r['fr_document_number'] for r in after}):,}")
    print(f"[1089] parse basis: "
          f"{dict(Counter(r['event_date_basis'] for r in after if r['event_date_basis']))}")
    print(f"[1089] location basis: "
          f"{dict(Counter(r['location_basis'] for r in after if r['location_basis']))}")
    print("[1089] NAGPRA overlap, on the row:")
    for k, v in sorted(stats.items()):
        if k.startswith("overlap::") or k.startswith("bridge::"):
            print(f"           {k:62s} {v:7,}")
    print(f"[1089] coverage window: "
          f"{dict(Counter(r['nagpra_coverage_window'] for r in after if r['nagpra_coverage_window']))}")
    if not apply_mode:
        print("[1089] MEASURE ONLY - nothing was written.")


def write_audit(after):
    """A seeded sample a human can check against the notice itself."""
    pool = [r for r in after if r.get("event_date_basis")
            or r.get("location_basis")]
    random.seed(20260902)
    sample = random.sample(pool, min(40, len(pool)))
    REVIEW.mkdir(exist_ok=True)
    cols = ["consultation_event_id", "fr_document_number", "notice_date",
            "consultation_type", "topic", "event_start_date", "event_end_date",
            "event_date_basis", "event_date_source_quote", "location",
            "location_basis", "location_source_quote", "source_url"]
    write_table(AUDIT, cols, sample)
    return len(sample), len(pool)


# ---------------------------------------------------------------- selftest


def selftest():
    fired = []
    base = [
        {"consultation_event_id": "A", "source_url":
         "https://www.federalregister.gov/documents/2020/01/02/2020-1/x/",
         "event_start_date": "", "event_end_date": "", "location": "",
         "tribe_id": "T1", "notice_date": "2020-01-02"},
        {"consultation_event_id": "B", "source_url":
         "https://www.federalregister.gov/documents/2015/01/02/2015-9/x/",
         "event_start_date": "2015-05-05", "event_end_date": "2015-05-05",
         "location": "Reno, Nevada", "tribe_id": "", "notice_date":
         "2015-01-02"},
    ]
    notes, pairs = {"2020-1"}, {("2020-1", "T1")}
    out, _ = build([dict(r) for r in base], notes, pairs,
                   texts_root=Path("/nonexistent"))
    assert not check(base, out, notes), check(base, out, notes)
    assert out[0]["nagpra_notice_overlap"] == "same_notice_in_nagpra_notices"
    assert out[0]["nagpra_bridge_overlap"] == \
        "same_notice_and_party_in_nagpra_bridge"
    assert out[1]["nagpra_notice_overlap"] == "not_in_nagpra_notices"

    bad = [dict(x) for x in out]
    bad.pop()
    got = check(base, bad, notes)
    assert got and got[0][0] == "INV-CE-ROWS", got
    fired.append("INV-CE-ROWS")

    bad = [dict(x) for x in out]
    bad[0]["topic"] = "rewritten"
    bad[0].setdefault("topic", "")
    base2 = [dict(x) for x in base]
    base2[0]["topic"] = "original"
    out2, _ = build([dict(r) for r in base2], notes, pairs,
                    texts_root=Path("/nonexistent"))
    out2[0]["topic"] = "rewritten"
    got = check(base2, out2, notes)
    assert got and got[0][0] == "INV-CE-COLS", got
    fired.append("INV-CE-COLS")

    bad = [dict(x) for x in out]
    bad[1]["location"] = "Elko, Nevada"
    got = check(base, bad, notes)
    assert got and got[0][0] == "INV-CE-NOCLOBBER", got
    fired.append("INV-CE-NOCLOBBER")

    bad = [dict(x) for x in out]
    bad[0]["event_start_date"] = "2020-03-03"
    bad[0]["event_date_basis"] = "made_up"
    bad[0]["event_date_source_quote"] = \
        "The session will be held on March 4, 2020."
    got = check(base, bad, notes)
    assert got and got[0][0] == "INV-CE-NOGUESS", got
    bad[0]["event_date_source_quote"] = ""
    got = check(base, bad, notes)
    assert got and got[0][0] == "INV-CE-NOGUESS", got
    bad = [dict(x) for x in out]
    bad[0]["location"] = "Atlantis, Oklahoma"
    bad[0]["location_basis"] = "made_up"
    bad[0]["location_source_quote"] = "The meeting will be held in Tulsa, OK."
    got = check(base, bad, notes)
    assert got and got[0][0] == "INV-CE-NOGUESS", got
    fired.append("INV-CE-NOGUESS")

    bad = [dict(x) for x in out]
    bad[1]["nagpra_notice_overlap"] = "same_notice_in_nagpra_notices"
    got = check(base, bad, notes)
    assert got and got[0][0] == "INV-CE-OVERLAP", got
    bad = [dict(x) for x in out]
    bad[0]["nagpra_notice_overlap"] = ""
    got = check(base, bad, notes)
    assert got and got[0][0] == "INV-CE-OVERLAP", got
    fired.append("INV-CE-OVERLAP")

    # the parser must refuse rather than guess
    assert iso_dates("The meeting is in the spring of 2020.") == []
    assert iso_dates("February 30, 2020") == []
    assert iso_dates("May 1997") == []          # no day printed
    assert iso_dates("October 13, 17, and 28, 1994") == \
        ["1994-10-13", "1994-10-17", "1994-10-28"]
    assert iso_dates("April 18-20, 2007") == \
        ["2007-04-18", "2007-04-19", "2007-04-20"]
    assert not DATE_ROW.search("Signed at Washington, DC, this day of May 1997")
    assert DATE_ROW.search("January 9, 1995: Minnesota, Minneapolis")
    assert places_in("Minnesota, St. Paul") == ["Minnesota, St. Paul"]
    assert places_in("Washington, DC") == ["Washington, DC"]
    assert places_in("Oklahoma City, Oklahoma") == ["Oklahoma City, Oklahoma"]
    # the line-wrap phantom the flatten-first rule exists to kill
    assert "City, OK" not in places_in(flatten("Oklahoma\nCity, OK"))
    # a comment deadline must never become a meeting
    d, dq, db, _, _, _ = parse_notice(
        "ACTION: Notice of Tribal Consultation Meetings.\n"
        "DATES: Written comments must be received no later than "
        "November 18, 1994.\nADDRESSES: x")
    assert d == [], (d, db)

    assert not check(base, out, notes), "restore must return the fixture clean"
    print("SELFTEST OK - invariants that FIRED on an injected violation: "
          + ", ".join(fired))
    print("           and the restored fixture passes, exit 0")
    return 0


# ---------------------------------------------------------------- main


def run(apply_mode):
    before, cols = read_table()
    notes, pairs = load_nagpra()
    if notes is None:
        print("UNMEASURED: nagpra_notices.csv is not on disk; the overlap "
              "cannot be measured and will not be guessed")
    after, stats = build([dict(r) for r in before], notes, pairs)
    bad = check(before, after, notes)
    if bad:
        for inv, msg in bad:
            print(f"FAIL {inv}: {msg}")
        return 1
    newcols = cols + [c for c in NEW_COLS if c not in cols]
    report(before, after, cols, stats, notes, pairs, apply_mode)
    if not apply_mode:
        return 0

    bak = TABLE.with_suffix(TABLE.suffix + f".bak_{TODAY}_pre_{STEM}")
    shutil.copy2(TABLE, bak)
    print(f"[1089] backup -> {bak.name}")
    write_table(TABLE, newcols, after)
    n_sample, n_pool = write_audit(after)
    print(f"[1089] audit sample {n_sample} of {n_pool} parsed rows -> "
          f"{AUDIT.name}")

    ndocs = {r["fr_document_number"] for r in after}
    nag_docs = {r["fr_document_number"] for r in after
                if r["nagpra_notice_overlap"] == "same_notice_in_nagpra_notices"}
    OUT_JSON.write_text(json.dumps({
        "measured_date": TODAY, "script": SCRIPT,
        "rows": len(after),
        "distinct_fr_documents": len(ndocs),
        "nagpra_overlap": {
            "rows_whose_notice_is_a_nagpra_notice":
                stats["overlap::same_notice_in_nagpra_notices"],
            "rows_not_in_nagpra_notices":
                stats["overlap::not_in_nagpra_notices"],
            "distinct_documents_shared_with_nagpra": len(nag_docs),
            "nagpra_notices_total": len(notes) if notes else None,
            "nagpra_notices_not_represented_here":
                (len(notes) - len(nag_docs)) if notes else None,
            "bridge": {k.split("::", 1)[1]: v for k, v in stats.items()
                       if k.startswith("bridge::")},
            "coverage_window": dict(Counter(
                r["nagpra_coverage_window"] for r in after
                if r["nagpra_coverage_window"])),
        },
        "event_fields": {
            c: {"before": sum(1 for r in before if (r.get(c) or "").strip()),
                "after": sum(1 for r in after if (r.get(c) or "").strip())}
            for c in ("event_start_date", "event_end_date", "location")},
        "event_date_basis": dict(Counter(
            r["event_date_basis"] for r in after if r["event_date_basis"])),
        "location_basis": dict(Counter(
            r["location_basis"] for r in after if r["location_basis"])),
        "notice_texts_read": stats["doc_text_read"],
        "notice_texts_not_on_disk": stats["doc_text_not_on_disk"],
    }, indent=1), encoding="utf-8")
    print(f"[1089] wrote {OUT_JSON.name}")
    return 0


def verify():
    rows, cols = read_table()
    missing = [c for c in NEW_COLS if c not in cols]
    if missing:
        print(f"FAIL: columns not present, run `apply` first: {missing}")
        return 1
    notes, _ = load_nagpra()
    bad = check(rows, rows, notes)
    if bad:
        for inv, msg in bad:
            print(f"FAIL {inv}: {msg}")
        return 1
    print(f"VERIFY OK  {len(rows):,} rows, {len(cols)} columns")
    for c in ("event_start_date", "location"):
        print(f"           {c:20s} "
              f"{sum(1 for r in rows if (r.get(c) or '').strip()):,} non-blank")
    print(f"           overlap: "
          f"{dict(Counter(r['nagpra_notice_overlap'] for r in rows))}")
    return 0


if __name__ == "__main__":
    a = sys.argv[1:]
    if "--selftest" in a:
        raise SystemExit(selftest())
    cmd = a[0] if a else "measure"
    if cmd == "measure":
        raise SystemExit(run(False))
    if cmd == "apply":
        raise SystemExit(run(True))
    if cmd == "verify":
        raise SystemExit(verify())
    raise SystemExit(f"unknown command {cmd!r}; "
                     f"use measure | apply | verify | --selftest")
