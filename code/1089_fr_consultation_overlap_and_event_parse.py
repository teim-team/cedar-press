#!/usr/bin/env python3
r"""
Cedar Press - 1089: `consultation_events.csv` in place -
(A) state the NAGPRA overlap ON THE ROW, and
(B) parse the consultation EVENT date and place out of notice bodies already
    on disk.

    py -3 code/1089_fr_consultation_overlap_and_event_parse.py measure   # read-only
    py -3 code/1089_fr_consultation_overlap_and_event_parse.py apply
    py -3 code/1089_fr_consultation_overlap_and_event_parse.py codebook
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


# ===========================================================================
# STAGE `codebook` - document all 37 columns, and STATE THE OVERLAP THERE
# ===========================================================================
# `consultation_events.csv` carried ZERO rows in `codebook_master.csv`. A clean
# table no codebook block documents is invisible to `87_build_dataset_notes.py`
# and to `512`'s shippable list. It is also why the NAGPRA overlap could only
# ever be stated in prose: there was no codebook entry to state it in.
#
# Two writes, the same shape `1072` uses and for the same reason:
#   * the FRAGMENT `data/clean/codebook/09c_consultation_events.csv`, owned by
#     this dataset, which a future `cedar_codebook.py build` folds in;
#   * an APPEND to `codebook_master.csv`, because `41_build_codebooks.py`
#     rewrites the master wholesale and is the one script on NEVER_RUN.
#     An append cannot shrink the master; a rewrite can.
CB_FIELDS = ["dataset", "variable", "type", "units", "pct_filled", "n_rows",
             "published", "access_tier", "description", "generated"]
CB_BLOCK = "09c_consultation_events"

OVERLAP_SENTENCE = (
    "OVERLAP WITH THE `nagpra` DATASET, measured 2026-09-02 and stated here so "
    "a buyer holding both cannot double-count: 10,920 of these 11,402 rows "
    "(95.8%) describe a Federal Register notice that `nagpra_notices.csv` also "
    "ships. Those 10,920 rows are only 1,831 DISTINCT notices, because this "
    "file is one row per (notice, participant); and 4,961 of the 6,792 NAGPRA "
    "notices appear here NOT AT ALL. Never add a count from this file to a "
    "count from `nagpra_notices.csv`."
)

CB_DESC = {
    "consultation_event_id":
        "Identifier of the consultation EVENT, `CONS-FR-<FR document "
        "number>`. NOT unique in this file: an event with several named "
        "participants has one row each.",
    "channel": "Always CONSULTATION. Consultation is a statutory "
               "government-to-government obligation and is never lobbying.",
    "agency": "The publishing agency as the Federal Register names it. 11,068 "
              "of 11,402 rows are Interior, which is a property of the NAGPRA "
              "notice series, not of federal consultation.",
    "sub_agency": "The sub-agency as the Federal Register names it.",
    "program": "The programme or institution named in the notice's own "
               "abstract, verbatim up to the governing verb.",
    "consultation_type":
        "What kind of consultation record this is. 10,888 rows (95.5%) are "
        "`NAGPRA_consultation_reported` - a NAGPRA notice REPORTING that "
        "consultation was undertaken, not a notice of a meeting. "
        + OVERLAP_SENTENCE,
    "topic": "The Federal Register document title, verbatim.",
    "notice_date": "The date the NOTICE published. This is NOT the date of the "
                   "consultation; see event_start_date.",
    "event_start_date":
        "First date of the consultation event ITSELF, where the notice states "
        "one. 190 of 11,402 rows. BLANK MEANS THE NOTICE DID NOT SAY - never "
        "that no event happened. Where 1089 filled it, "
        "`event_date_source_quote` prints the sentence it came from, and no "
        "year is ever supplied that the notice did not print.",
    "event_end_date": "Last such date, on the same basis as event_start_date.",
    "location":
        "Place of the consultation event, in the publisher's own word order "
        "(the Federal Register's consultation tables print `State, City`). 103 "
        "of 11,402 rows. A place is read as an event location only where the "
        "notice announces an event: a NAGPRA notice's museum contact address, "
        "and the county remains were removed from, are places the notice "
        "prints and are NOT consultation locations.",
    "format": "virtual / teleconference / in_person / written_comment, "
              "semicolon-joined, from the notice's own words.",
    "tribe_id": "Cedar entity id of the participant, where the resolver was "
                "certain. Blank is unresolved, never 'no participant'.",
    "tribe_name": "Cedar's canonical name for tribe_id.",
    "participant_name_as_published":
        "The participant's name EXACTLY as the notice printed it. This field "
        "is authoritative; tribe_id is Cedar's reading of it.",
    "participant_role":
        "consulted / invited / invited_did_not_participate / not_enumerated, "
        "assigned from the governing verb phrase in the SAME sentence as the "
        "name list. `invited_did_not_participate` is a claim about a named "
        "tribe's conduct and must never be shown without source_quote.",
    "comment_deadline": "The comment deadline the notice states. NOT an event "
                        "date.",
    "has_written_comments": "1 where the notice's own text names written "
                            "comments.",
    "has_summary": "1 where the notice names a consultation summary or report.",
    "has_transcript": "1 where the notice names a transcript.",
    "federal_register_citation": "Volume and page, e.g. `81 FR 36952`.",
    "source_url": "The Federal Register document URL. Every row has one.",
    "source_quote": "The sentence the participant and role were read out of.",
    "fetched_date": "When Cedar retrieved the notice text.",
    "tier": "B on every row: an algorithmic match against published text, "
            "never hand-ruled.",
    "confidence": "The parser's own confidence in the participant match.",
    "built_date": "When this row was built.",
    "match_method": "How the participant name resolved to tribe_id.",
    "cedar_uid": "Cedar universal id of the participant entity.",
    "fr_document_number":
        "THE JOIN KEY. The Federal Register document number, parsed from this "
        "row's own source_url. Joins to `federal_actions.csv` (156,897 "
        "documents), to `nagpra_notices.csv`, and to every other FR-keyed "
        "table. Added 2026-09-02; this file previously had no join key at all.",
    "nagpra_notice_overlap":
        "`same_notice_in_nagpra_notices` (10,920 rows) or "
        "`not_in_nagpra_notices` (482). " + OVERLAP_SENTENCE,
    "nagpra_bridge_overlap":
        "Whether this row's (notice, tribe) pair is ALSO a row in "
        "`nagpra_notice_entity_bridge.csv`: "
        "`same_notice_and_party_in_nagpra_bridge` 8,788, "
        "`same_notice_different_party` 1,606, "
        "`no_tribe_resolved_on_this_row` 526, "
        "`notice_not_in_nagpra_dataset` 482. The 1,606 measure how far two "
        "independent extractions disagree about who was consulted on the same "
        "notice; they are a review queue, not an error count.",
    "nagpra_coverage_window":
        "Which part of this file's NAGPRA coverage the row falls in. The "
        "coverage is a WINDOW, not a sample: 0 of 1,882 NAGPRA notices from "
        "1994-2010, 1,817 of 2,264 from 2011-2022, 14 of 2,646 from 2023-2026. "
        "Revised 43 CFR 10 took effect 2024-01-12 and replaced the 'in "
        "consultation with representatives of' sentence this file's net keys "
        "on with a bulleted Determinations list, so the net stops catching "
        "notices exactly as NAGPRA volume triples.",
    "event_date_basis":
        "Which rule filled event_start_date. Blank where the date came from "
        "the original build, or where there is no date.",
    "event_date_source_quote":
        "The notice's OWN sentence that prints the event date. Every date 1089 "
        "wrote is a date this quote prints; the build fails otherwise "
        "(INV-CE-NOGUESS).",
    "location_basis": "Which rule filled location.",
    "location_source_quote":
        "The notice's OWN segment that prints the place. Every location 1089 "
        "wrote is a place this quote prints.",
}
CB_GENERIC = ("Column of consultation_events.csv. See "
              "docs/methodology/federal-register.md for how this table is "
              "built and what it may be totalled on.")


def _cb_type(vals):
    v = [x for x in vals if (x or "").strip()]
    if not v:
        return "text"
    if all(re.match(r"^-?\d+$", x) for x in v):
        return "integer"
    if all(re.match(r"^\d{4}-\d{2}-\d{2}$", x) for x in v):
        return "date"
    if all(re.match(r"^-?\d*\.?\d+$", x) for x in v):
        return "numeric"
    return "text"


def stage_codebook():
    rows, cols = read_table()
    if not rows:
        print("  ! consultation_events.csv has no rows")
        return 1
    if "nagpra_notice_overlap" not in cols:
        print("  ! run `apply` first - the overlap columns are not on the file")
        return 1
    frag_dir = CLEAN / "codebook"
    frag_dir.mkdir(parents=True, exist_ok=True)
    frag = []
    for col in cols:
        vals = [r.get(col, "") for r in rows]
        filled = sum(1 for x in vals if (x or "").strip())
        frag.append({
            "dataset": CB_BLOCK, "variable": col, "type": _cb_type(vals),
            "units": "code" if col.endswith(("_id", "_uid", "_number"))
                     else "date" if col.endswith(("_date", "_deadline"))
                     else "text",
            "pct_filled": round(100.0 * filled / len(rows), 1),
            "n_rows": len(rows), "published": 1,
            # Federal Register text and Cedar's own derivations from it. No
            # licensed field and no terms-restricted source: every row here is
            # a federal publication.
            "access_tier": "public",
            "description": CB_DESC.get(col, CB_GENERIC),
            "generated": TODAY,
        })
    write_table(frag_dir / (CB_BLOCK + ".csv"), CB_FIELDS, frag)
    master = CLEAN / "codebook_master.csv"
    existing = list(csv.DictReader(
        open(master, newline="", encoding="utf-8"))) if master.exists() else []
    have = {(r["dataset"], r["variable"]) for r in existing}
    new = [r for r in frag if (r["dataset"], r["variable"]) not in have]
    if new:
        bak = master.with_suffix(f".csv.bak_{TODAY}_pre_{STEM}")
        if not bak.exists():
            bak.write_bytes(master.read_bytes())
        with master.open("a", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=CB_FIELDS, extrasaction="ignore")
            for r in new:
                w.writerow(r)
        print(f"  appended {len(new)} rows to codebook_master.csv "
              f"({len(existing)} -> {len(existing) + len(new)}); "
              f"backup {bak.name}")
    else:
        print("  codebook_master.csv already carries this block")
    n_overlap = sum(1 for r in frag if "nagpra" in r["description"].lower())
    print(f"  {CB_BLOCK}: {len(frag)} variables documented, {len(rows):,} rows")
    print(f"  the NAGPRA overlap is stated on {n_overlap} of them, including "
          f"consultation_type and nagpra_notice_overlap")
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
    if cmd == "codebook":
        raise SystemExit(stage_codebook())
    raise SystemExit(f"unknown command {cmd!r}; "
                     f"use measure | apply | codebook | verify | --selftest")
