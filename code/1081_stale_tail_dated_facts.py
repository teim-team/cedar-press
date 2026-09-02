#!/usr/bin/env python3
"""
1081_stale_tail_dated_facts.py -- CLOSE THE STALE-ENTITY TAIL WITH REAL DATES.

    py -3 code/1081_stale_tail_dated_facts.py measure   # the three numbers, now
    py -3 code/1081_stale_tail_dated_facts.py run       # acquire + write
    py -3 code/1081_stale_tail_dated_facts.py run --routes=ondisk_uei,ccd
    py -3 code/1081_stale_tail_dated_facts.py verify    # exit 1 on breach
    py -3 code/1081_stale_tail_dated_facts.py selftest  # prove verify FIRES

WHY
---
`code/830_entity_freshness.py`, once its third build-stamp defect was fixed,
measured a tail nothing else can see:

    untouched over a year   287
    no usable date at all   373
    in no substantive row    83   (all BIE schools)

The failure mode for this job is writing a row that says "we looked". A date
must come from a source that STATES it. 830 already refuses any column that
supplies many entities' newest date from few distinct values, so a bulk stamp
is detected -- and this script must not need that defence to be honest, so it
carries the same invariant in its own `verify`.

WHAT IT WRITES
--------------
`data/clean/entity_dated_public_facts.csv` -- one row per
(entity, route, source, fact_key, identifier). Every row carries `as_of_date`
(the date the SOURCE states) and `as_of_date_basis` (why that date is the
entity's and not ours). Cedar's own clock is `checked_date`, which 830's
`NEVER` regex excludes by name.

THE ROUTES, cheapest first
--------------------------
R1 `ondisk_uei`   ZERO NETWORK. Cedar already holds exact UEIs for tail
                  entities (tier-A identifier ledger, the BIE/UIO links, the
                  FAC audit rows, the NEST enterprise table) AND ~1.9M federal
                  transactions carrying `awardee_uei` / `recipient_uei` beside
                  an `action_date`. Nothing had joined the two, because those
                  transaction rows are `unattributed` -- the entity is absent
                  from the attribution column while its own UEI sits in the
                  identifier column of the same row. That is the
                  `ON_DISK_NOT_PROMOTED` state in the field guide, and it is
                  the largest free win in the tail.

                  A UEI IS EXACT, BUT AN EXACT KEY IS NOT A CORRECT LINK
                  (START_HERE trap 1). Tier is READ, never inferred: only
                  ledger rows whose `confidence_tier` is literally A and whose
                  `exclusion_id` is empty are used, because a tier-X row is a
                  REFUTATION and 317 of them were once published as confident
                  attributions. A UEI resolving to more than one entity is
                  dropped and named.

R2 `ccd`          NCES Common Core of Data, BIE reporting universe (fips 59),
                  via the Urban Institute Education Data API. EVERY year
                  2000-2024, not a sample: the last year a school appears IS
                  the fact, and a sampled year list manufactures a false one.
                  With the 12 years a sibling had cached, 181 schools "last
                  appeared" in 2005 only because 2006-2021 were never asked
                  for, and 174 shared one last-year -- the exact shape 830
                  refuses as a build stamp.

R3 `irs990`       ProPublica Nonprofit Explorer, EIN-first. The dated fact is
                  the most recent 990 tax period, which the IRS states. The
                  EIN is a LOOKUP KEY, never an inherited link: every one is
                  re-verified by name against what the IRS publishes for it
                  before a date is written.

WHAT IT NEVER DOES
------------------
No spine writes, no minting, no repointing, no commits. A candidate failing
the name test is written with `match_method = NOT_MATCHED` and what was seen
-- flag, never delete. No date is ever synthesised from a build or a run.

THE STOPWORD-NAME HAZARD, handled
---------------------------------
A name made only of stopwords cannot be identity-checked; the village of
*Council* matched `kawerak.org` and produced six junk rows. `has_identity()`
refuses any name with no distinctive tokens even after the all-generic
fallback, and such entities are reported as `NO_IDENTIFIABLE_NAME` rather
than matched on a guess.

REUSE
-----
The name machinery (`deacc`, `toks`, `name_matches`) is imported from
`code/1021_register_only_first_rows.py` rather than re-implemented. It carries
five defects' worth of corrections -- the school-level conflict refusal, the
all-generic fallback, the Navaho/Navajo substitution tolerance -- and a second
copy would drift away from all of them.
"""
from __future__ import annotations

import csv
import importlib.util
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import date, datetime, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLEAN = os.path.join(ROOT, "data", "clean")
SPINE = os.path.join(ROOT, "data", "spine")
STAGE = os.path.join(ROOT, "data", "staging", "stale_tail_1081")
FRESH = os.path.join(CLEAN, "cedar_entity_freshness.csv")
REGISTER = os.path.join(SPINE, "cedar_identity_register.csv")
OUT = os.path.join(CLEAN, "entity_dated_public_facts.csv")
TODAY = date.today().isoformat()
csv.field_size_limit(10_000_000)

UA = ("CedarPress-research/1.0 (entity freshness tail; contact "
      "elijahsamsonmoreno@gmail.com)")

# THE HEADER IS CANONICAL-THEN-LIVE, NEVER A FIXED LIST (845 / 62 rule 17).
# A fixed literal deletes any column something else has since added.
CANONICAL = [
    "cedar_uid", "handle", "canonical_name", "entity_class",
    "route", "source", "source_url",
    "fact_key", "fact_label", "fact_value",
    "as_of_date", "as_of_date_basis",
    "identifier_type", "identifier_value",
    "match_method", "match_note", "uniform_source_date",
    "evidence", "checked_date",
]

# STALE_BAR: a date older than this cannot be a claim of freshness, whatever
# else is wrong with it. It is the same 365-day line 830 draws.
STALE_BAR_DAYS = 365


def live_header(path, canonical):
    live = []
    if os.path.exists(path):
        with open(path, encoding="utf-8-sig", newline="") as fh:
            live = next(csv.reader(fh), []) or []
    return canonical + [c for c in live if c not in canonical]


# ------------------------------------------------------------ imported names
def _load_1021():
    p = os.path.join(ROOT, "code", "1021_register_only_first_rows.py")
    spec = importlib.util.spec_from_file_location("cedar_1021", p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


_N = _load_1021()
deacc, toks, name_matches = _N.deacc, _N.toks, _N.name_matches


def has_identity(name):
    """False when a name has no distinctive tokens even with the fallback.

    `toks` strips the generic vocabulary and, if nothing survives, falls back
    to the generic words themselves so an all-generic name can still be
    matched by demanding ALL of them. A name with NEITHER -- nothing but
    MINIMAL_STOP and sub-3-character words -- cannot be identity-checked at
    all. That is the shape of *Council*, and matching it against page text is
    how six rows about kawerak.org were written.
    """
    return bool(toks(name))


# ------------------------------------------------------------------ the tail
def read_freshness():
    with open(FRESH, encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def tail_slice(rows=None):
    """-> (uid -> freshness row, label -> set(uid)). DERIVED, never enumerated."""
    rows = rows if rows is not None else read_freshness()
    stale, undated, nosub = set(), set(), set()
    for r in rows:
        u = r["cedar_uid"]
        if not r["last_change"]:
            undated.add(u)
        elif r["days_since_change"] and int(r["days_since_change"]) > 365:
            stale.add(u)
        if r["n_substantive_datasets_present_in"] == "0":
            nosub.add(u)
    return ({r["cedar_uid"]: r for r in rows},
            {"stale": stale, "undated": undated, "nosub": nosub})


def measure(rows=None):
    _, g = tail_slice(rows)
    return {"untouched_over_a_year": len(g["stale"]),
            "no_usable_date": len(g["undated"]),
            "no_substantive_row": len(g["nosub"]),
            "tail_union": len(g["stale"] | g["undated"] | g["nosub"])}


ISO = re.compile(r"^(19|20)\d\d-\d\d-\d\d")


def sane_date(d):
    """Usable only if it PARSES and is not in the future.

    830 DISCARDS future dates rather than clamping them, after clamping made
    every entity holding a current-fiscal-year row read as touched today. Same
    rule here, for the same reason.
    """
    d = (d or "").strip()[:10]
    if not ISO.match(d):
        return ""
    try:
        datetime.strptime(d, "%Y-%m-%d")
    except ValueError:
        return ""
    return d if d <= TODAY else ""


# ------------------------------------------------------ identifiers on disk
LEDGER = "cedar_identifier_ledger_final.csv"
UEI_SOURCES = (("bie_uio_identifier_links.csv", "uei"),
               ("fac_tribal_single_audits.csv", "auditee_uei"),
               ("nest_enterprises.csv", "uei"))
EIN_SOURCES = (("np_ein_entity_hub.csv", "ein"),
               ("np_orgs.csv", "EIN"),
               ("bie_uio_identifier_links.csv", "ein"),
               ("fac_tribal_single_audits.csv", "auditee_ein"))


def _rows_of(fn):
    p = os.path.join(CLEAN, fn)
    if not os.path.exists(p):
        return [], []
    with open(p, encoding="utf-8-sig", newline="", errors="replace") as fh:
        rd = csv.DictReader(fh)
        return list(rd), (rd.fieldnames or [])


# A UEI IS TWELVE ALPHANUMERIC CHARACTERS. A COLUMN CALLED `uei` IS NOT.
# `fac_tribal_single_audits.auditee_uei` holds the literal string
# `GSA_MIGRATION` on the rows the FAC carried over from its pre-UEI system,
# and 41 tail entities share it. Without a shape test it reads as one exact
# identifier held by 41 different organisations -- the ambiguity guard below
# caught it, but only by accident of it being shared. A sentinel held by ONE
# entity would have passed and keyed that entity to every GSA_MIGRATION row in
# the federal tables. Shape first, then ambiguity.
UEI_SHAPE = re.compile(r"^[A-Z0-9]{12}$")
UEI_SENTINELS = {"GSA_MIGRATION", "NOT_AVAILABLE", "UNKNOWN", "NONE", "N/A"}


def tail_ueis(tail):
    """-> (UEI -> (uid, source), [rejected notes]).

    TIER IS READ, NEVER INFERRED -- see the module docstring, R1.
    """
    cand, src = defaultdict(set), {}
    led, _ = _rows_of(LEDGER)
    for r in led:
        if (r.get("cedar_uid") in tail
                and r.get("confidence_tier") == "A"
                and r.get("identifier_type") == "UEI"
                and not (r.get("exclusion_id") or "").strip()):
            v = (r.get("identifier") or "").strip().upper()
            if v:
                cand[v].add(r["cedar_uid"])
                src.setdefault(v, LEDGER + " (confidence_tier=A, no exclusion_id)")
    for fn, ucol in UEI_SOURCES:
        rows, hdr = _rows_of(fn)
        if ucol not in hdr:
            continue
        for r in rows:
            if r.get("cedar_uid") in tail:
                v = (r.get(ucol) or "").strip().upper()
                if v and v.lower() not in ("nan", "none", "n/a"):
                    cand[v].add(r["cedar_uid"])
                    src.setdefault(v, fn + " (" + ucol + ")")
    keep, dropped = {}, []
    for v, uids in cand.items():
        if v in UEI_SENTINELS or not UEI_SHAPE.match(v):
            dropped.append("NOT A UEI (%s): %s held by %d entit(ies)"
                           % ("sentinel" if v in UEI_SENTINELS else "shape",
                              v, len(uids)))
        elif len(uids) == 1:
            keep[v] = (next(iter(uids)), src[v])
        else:
            dropped.append("AMBIGUOUS " + v + " -> " + ",".join(sorted(uids)))
    return keep, dropped


def tail_eins(tail):
    """-> uid -> {(EIN, source)}. A LOOKUP KEY, never an inherited link.

    `np_ein_entity_hub` links are tier B via a containment matcher that
    AGENTS.md forbids from keying a dollar. Using it as a place to LOOK is
    legitimate; inheriting it as a fact is not, so every hit is re-verified
    by name against the IRS's own name for that EIN.
    """
    out = defaultdict(set)
    for fn, col in EIN_SOURCES:
        rows, hdr = _rows_of(fn)
        if col not in hdr:
            continue
        for r in rows:
            u = r.get("cedar_uid")
            if u in tail:
                v = re.sub(r"\D", "", r.get(col) or "")
                if len(v) == 9:
                    out[u].add((v, fn))
    return out


# ------------------------------------------------------- R1  on-disk UEI join
FED_TABLES = (
    ("prime_contracts.csv", "awardee_uei", "action_date",
     "USAspending prime contract award action"),
    ("federal_funding_transactions.csv", "recipient_uei", "action_date",
     "USAspending federal assistance award action"),
)


def _base(uid, ents, route, source, url):
    e = ents[uid]
    return {"cedar_uid": uid, "handle": e.get("handle", ""),
            "canonical_name": e["canonical_name"],
            "entity_class": e["entity_class"], "route": route,
            "source": source, "source_url": url, "checked_date": TODAY}


def route_ondisk_uei(tail, ents):
    ueis, dropped = tail_ueis(tail)
    for d in dropped:
        print("    REJECTED  " + d[:160])
    print("    %d exact UEI(s) covering %d tail entities"
          % (len(ueis), len({v[0] for v in ueis.values()})))
    best = {}
    for fn, ucol, dcol, label in FED_TABLES:
        p = os.path.join(CLEAN, fn)
        if not os.path.exists(p):
            print("    SKIP %s: not on disk" % fn)
            continue
        hit = 0
        with open(p, encoding="utf-8-sig", newline="", errors="replace") as fh:
            rd = csv.DictReader(fh)
            hdr = rd.fieldnames or []
            if ucol not in hdr or dcol not in hdr:
                print("    SKIP %s: no %s / %s column" % (fn, ucol, dcol))
                continue
            for r in rd:
                v = (r.get(ucol) or "").strip().upper()
                if v not in ueis:
                    continue
                d = sane_date(r.get(dcol))
                if not d:
                    continue
                hit += 1
                uid, isrc = ueis[v]
                k = (uid, fn)
                if k not in best or d > best[k][0]:
                    best[k] = (d, v, isrc, label, ucol,
                               (r.get("recipient_name")
                                or r.get("awardee_name") or "").strip())
        print("    %-38s %7d dated row(s) on a tail UEI" % (fn, hit))
    rows = []
    for (uid, fn), (d, uei, isrc, label, ucol, rname) in sorted(best.items()):
        r = _base(uid, ents, "ondisk_uei", label, "https://www.usaspending.gov/")
        r.update({
            "fact_key": "latest_award_action:" + fn,
            "fact_label": "most recent federal award action recorded against "
                          "this entity's UEI",
            "fact_value": rname,
            "as_of_date": d,
            "as_of_date_basis": (
                "`action_date`, the date the awarding agency recorded the "
                "transaction, on a row of " + fn + " whose `" + ucol + "` "
                "equals this entity's UEI. The date is the agency's, not "
                "Cedar's."),
            "identifier_type": "UEI", "identifier_value": uei,
            "match_method": "exact_uei",
            "match_note": "UEI sourced from " + isrc,
            "evidence": ("exact UEI join against data already on this "
                         "machine; the transaction row is UNATTRIBUTED in its "
                         "own attribution column, which is why no instrument "
                         "had seen this entity's date before"),
        })
        rows.append(r)
    return rows


# ------------------------------------------------------------------ R2  CCD
CCD = "https://educationdata.urban.org/api/v1/schools/ccd/directory/"
CCD_YEARS = tuple(range(2000, 2025))
CCD_FIPS_BIE = 59
CCD_STATUS = {1: "open", 2: "closed", 3: "new", 4: "added",
              5: "changed agency", 6: "inactive", 7: "future", 8: "reopened"}
_last = [0.0]
LOCKS = os.path.join(ROOT, "logs")


def host_lock(host, note):
    """PULL_DISCIPLINE rule 2. One poller per host, and say which fields mean
    what -- `downloaded_this_run: false` with an empty `refused_by_host` is
    NOT a block, it means there was nothing to do."""
    os.makedirs(LOCKS, exist_ok=True)
    p = os.path.join(LOCKS, "_HOSTLOCK_%s.json" % host)
    if os.path.exists(p):
        try:
            with open(p, encoding="utf-8") as fh:
                held = json.load(fh)
        except Exception:                                        # noqa: BLE001
            held = {}
        if held.get("script") not in (None, os.path.basename(__file__)):
            print("    HOST LOCK held by %s since %s -- deferring, not "
                  "starting a second poller"
                  % (held.get("script"), held.get("started")))
            return None
    with open(p, "w", encoding="utf-8") as fh:
        json.dump({"host": host, "pid": os.getpid(),
                   "script": os.path.basename(__file__),
                   "started": datetime.utcnow().isoformat() + "Z",
                   "queue": [], "note": note,
                   "downloaded_this_run": False,
                   "already_on_disk_skipped": 0,
                   "refused_by_host": []}, fh)
    return p


def host_unlock(p, downloaded, refused):
    if not p or not os.path.exists(p):
        return
    try:
        with open(p, encoding="utf-8") as fh:
            d = json.load(fh)
        d.update({"downloaded_this_run": bool(downloaded),
                  "finished": datetime.utcnow().isoformat() + "Z",
                  "refused_by_host": refused})
        with open(p, "w", encoding="utf-8") as fh:
            json.dump(d, fh)
    except Exception:                                            # noqa: BLE001
        pass


def pace(sec=0.8):
    d = sec - (time.time() - _last[0])
    if d > 0:
        time.sleep(d)
    _last[0] = time.time()


def get_json(url, timeout=90, tries=3):
    """-> (obj|None, note). Never raises."""
    for n in range(tries):
        pace()
        try:
            req = urllib.request.Request(
                url, headers={"User-Agent": UA, "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode("utf-8", "replace")), "200"
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503) and n + 1 < tries:
                time.sleep(3 * (n + 1))
                continue
            return None, "HTTP " + str(e.code)
        except Exception as e:                                    # noqa: BLE001
            if n + 1 < tries:
                time.sleep(2 * (n + 1))
                continue
            return None, type(e).__name__
    return None, "exhausted"


def ccd_year(y):
    """One CCD year, cached. `.part` then rename -- never a half file."""
    os.makedirs(STAGE, exist_ok=True)
    p = os.path.join(STAGE, "ccd_%d.json" % y)
    if os.path.exists(p):
        with open(p, encoding="utf-8") as fh:
            return json.load(fh), "cache"
    recs, url = [], CCD + "%d/?fips=%d" % (y, CCD_FIPS_BIE)
    while url:
        obj, note = get_json(url)
        if obj is None:
            return None, note
        recs.extend(obj.get("results") or [])
        url = obj.get("next")
    with open(p + ".part", "w", encoding="utf-8") as fh:
        json.dump(recs, fh)
    os.replace(p + ".part", p)
    return recs, "fetched"


# `ncessch` IS NOT A SCHOOL ID -- IT IS AN LEA ID GLUED TO ONE.
#
# The first pass keyed identity on `ncessch` and reported 132 of 142 BIE
# schools as AMBIGUOUS, most of them "2 NCES ids". They were not ambiguous.
# `ncessch` is leaid(7) + the school's own 5-digit number, and NCES re-issues
# the LEA half whenever a school's reporting agency changes -- Ahfachkee is
# 590000700041 up to 2005 and 590009200041 after it, one school, two strings.
# The stable half is the LAST FIVE DIGITS. `school_id`, which looks like the
# obvious candidate, is not usable: the same school is '00041' in some years
# and '5900041' in others.
#
# This is the field guide's signature defect in miniature -- a check that
# produced a plausible number about something other than its own name. Left
# alone it would have reported "NCES cannot identify 93% of BIE schools",
# which is a statement about a join key, not about NCES.
def bie_school_no(rec):
    return (rec.get("ncessch") or "")[-5:]


# CCD carries cp1252 bytes decoded as latin-1 in some vintages: DLO\x92AY for
# DLO'AY. The name matcher turns any non-letter into a SPACE, which would
# split `dloay` into two tokens and refuse a true match. Strip these, do not
# space them.
_MOJI = re.compile(r"[\x91\x92\x93\x94�‘’]")


def ccd_name(rec):
    return _MOJI.sub("", rec.get("school_name") or "")


def ccd_asof(y):
    """1 October of collection year Y.

    CCD's directory year Y is school year Y/Y+1 and its snapshot is the autumn
    membership count date, 1 October of Y. That is the date NCES states the
    record is ABOUT. It is not the release date and it is not today -- which
    is exactly why the newest CCD year cannot lift a BIE school out of the
    >1yr bucket, and saying so is the finding.
    """
    return "%d-10-01" % y


def route_ccd(tail, ents):
    schools = [u for u in tail if ents[u]["entity_class"] == "BIE School"]
    print("    %d BIE School(s) in the tail" % len(schools))
    lock = host_lock("educationdata.urban.org", "CCD BIE directory 2000-2024")
    per_year, misses = {}, []
    for y in CCD_YEARS:
        recs, note = ccd_year(y)
        if recs is None:
            misses.append("%d:%s" % (y, note))
            continue
        per_year[y] = recs
    host_unlock(lock, any(True for _ in per_year), misses)
    if misses:
        print("    years NOT retrieved: " + ", ".join(misses))
    print("    %d CCD year(s) held, %d record(s)"
          % (len(per_year), sum(len(v) for v in per_year.values())))
    if not per_year:
        return []
    years_of = defaultdict(set)
    for y, recs in per_year.items():
        for rec in recs:
            years_of[bie_school_no(rec)].add(y)

    rows = []
    for u in sorted(schools):
        nm = ents[u]["canonical_name"]
        r = _base(u, ents, "ccd",
                  "NCES Common Core of Data, BIE reporting universe "
                  "(fips 59), via the Urban Institute Education Data API",
                  CCD + "?fips=%d" % CCD_FIPS_BIE)
        r.update({"fact_key": "ccd_last_reported", "fact_label": "",
                  "fact_value": "", "as_of_date": "",
                  "identifier_type": "", "identifier_value": "",
                  "evidence": "searched every CCD year %d-%d for fips 59"
                              % (CCD_YEARS[0], CCD_YEARS[-1])})
        if not has_identity(nm):
            r.update({"match_method": "NOT_MATCHED",
                      "match_note": "NO_IDENTIFIABLE_NAME",
                      "as_of_date_basis": "no date: the name carries no "
                                          "distinctive token, so no name "
                                          "match can identify it"})
            rows.append(r)
            continue
        hits = {}
        for y in sorted(per_year):
            for rec in per_year[y]:
                ok, note = name_matches(nm, ccd_name(rec))
                if ok:
                    key = bie_school_no(rec)
                    if key not in hits or y > hits[key][0]:
                        hits[key] = (y, rec, note)
        if not hits:
            r.update({"match_method": "NOT_MATCHED",
                      "match_note": "NOT_IN_CCD_BIE_UNIVERSE",
                      "as_of_date_basis": "no date: the source does not "
                                          "carry this entity"})
            rows.append(r)
            continue
        if len(hits) > 1:
            # Two NCES ids for one Cedar entity is a question, not a match.
            r.update({"match_method": "NOT_MATCHED",
                      "match_note": "AMBIGUOUS_%d_BIE_SCHOOL_NUMBERS:%s"
                                    % (len(hits), ",".join(sorted(hits))),
                      "as_of_date_basis": "no date: more than one NCES BIE "
                                          "school number matches this name "
                                          "and picking one would be a guess"})
            rows.append(r)
            continue
        key, (y, rec, note) = next(iter(hits.items()))
        st = CCD_STATUS.get(rec.get("school_status"),
                            str(rec.get("school_status")))
        r.update({
            "source_url": CCD + "%d/?fips=%d" % (y, CCD_FIPS_BIE),
            "fact_label": "most recent NCES CCD school year in which this "
                          "school reported",
            "fact_value": ("SY%d-%02d | %s | status %s | enrollment %s | "
                           "teachers_fte %s | %s, %s"
                           % (y, (y + 1) % 100, ccd_name(rec),
                              st, rec.get("enrollment"),
                              rec.get("teachers_fte"),
                              rec.get("city_location") or "",
                              rec.get("state_location") or "")),
            "as_of_date": ccd_asof(y),
            "as_of_date_basis": (
                "1 October %d, the autumn membership count date of CCD "
                "collection year %d (school year %d-%02d). NCES states the "
                "record is about that school year; this is not a release "
                "date and not Cedar's clock. UNIFORM BY THE SOURCE'S "
                "CONSTRUCTION: the BIE reporting universe is static -- the "
                "same 174 schools reported in every collection year 2008-2024 "
                "-- so this date is shared by every school still reporting, "
                "and it is %d days old, well outside the 365-day staleness "
                "bar. It identifies the school and dates its enrolment; it is "
                "not evidence that anybody looked at it recently."
                % (y, y, y, (y + 1) % 100,
                   (date.fromisoformat(TODAY)
                    - date(y, 10, 1)).days)),
            "identifier_type": "NCES_BIE_SCHOOL_NUMBER",
            "identifier_value": key,
            "match_method": "distinctive_token_overlap", "match_note": note,
            "uniform_source_date": "Y",
            "evidence": ("present in %d of the %d CCD years %d-%d searched, "
                         "most recently %d; ncessch that year %s"
                         % (len(years_of[key]), len(per_year),
                            CCD_YEARS[0], CCD_YEARS[-1], y,
                            rec.get("ncessch"))),
        })
        rows.append(r)
    ok = sum(1 for r in rows if r["match_method"] != "NOT_MATCHED")
    print("    matched %d, not matched %d" % (ok, len(rows) - ok))
    return rows


# --------------------------------------------------------------- R3  IRS 990
PP_ORG = "https://projects.propublica.org/nonprofits/api/v2/organizations/%s.json"

# The tail classes that are ORGANISATIONS likely to file a 990. A for-profit
# ANCSA village corporation is not one, and asking for it is a request that
# cannot succeed -- an absence there would be an artefact of the question.
NP_CLASSES = {
    "Native Hawaiian Organization",
    "Native Community Development Financial Institution",
    "Native Financial Institution",
    "Urban Indian Organization",
    "Intertribal Organization",
    "Federal-level self-governance consortium",
    "Tribal College or University",
    "BIE School",
}


def _month_end(y, m):
    for dd in (31, 30, 29, 28):
        try:
            return date(y, m, dd)
        except ValueError:
            continue
    return None


def pp_filings(ein):
    """-> ({org, tax_period_end}|None, note). The date is the IRS's."""
    obj, note = get_json(PP_ORG % ein)
    if obj is None:
        return None, note
    best = ""
    for f in ((obj.get("filings_with_data") or [])
              + (obj.get("filings_without_data") or [])):
        raw = str(f.get("tax_prd") or "")
        if len(raw) == 6 and raw.isdigit():
            y, m = int(raw[:4]), int(raw[4:])
            if 1 <= m <= 12 and 1990 <= y <= 2100:
                end = _month_end(y, m)
                s = sane_date(end.isoformat()) if end else ""
                if s > best:
                    best = s
    return {"org": obj.get("organization") or {}, "tax_period_end": best}, "200"


def route_irs990(tail, ents, budget=300):
    eins = tail_eins(tail)
    todo = [u for u in sorted(tail)
            if ents[u]["entity_class"] in NP_CLASSES and u in eins]
    print("    %d tail entit(ies) in a 990-filing class with an EIN on disk"
          % len(todo))
    lock = host_lock("projects.propublica.org", "990 tax periods, stale tail")
    if lock is None:
        return []
    rows, spent, refused = [], 0, []
    for u in todo:
        if spent >= budget:
            print("    budget %d requests reached; %d entit(ies) unattempted"
                  % (budget, len(todo) - todo.index(u)))
            break
        nm = ents[u]["canonical_name"]
        for ein, isrc in sorted(eins[u]):
            if spent >= budget:
                break
            spent += 1
            res, note = pp_filings(ein)
            if res is None:
                if note != "HTTP 404":
                    refused.append(ein + ":" + note)
                    # STOP ON FIRST REFUSAL WHEN NOTHING HAS LANDED. If the
                    # first object exhausts its backoff and no object has
                    # succeeded, the HOST is refusing, not that EIN, and the
                    # remaining hundreds are hundreds of ways to learn the
                    # same fact.
                    if not rows and len(refused) >= 3:
                        print("    HOST REFUSING after %d attempts with "
                              "nothing landed: %s -- stopping"
                              % (len(refused), ",".join(refused)))
                        host_unlock(lock, False, refused)
                        return rows
                continue
            org = res["org"]
            cand = org.get("name") or ""
            ok, mnote = (name_matches(nm, cand) if has_identity(nm)
                         else (False, "NO_IDENTIFIABLE_NAME"))
            d = res["tax_period_end"]
            if ok and not d:
                ok, mnote = False, (mnote + "; the IRS lists no filing with a "
                                            "tax period for this EIN")
            r = _base(u, ents, "irs990",
                      "IRS Form 990 via ProPublica Nonprofit Explorer",
                      "https://projects.propublica.org/nonprofits/"
                      "organizations/" + str(int(ein)))
            r.update({
                "fact_key": "irs990_latest_tax_period",
                "fact_label": "most recent Form 990 tax period the IRS "
                              "records for this EIN",
                "fact_value": (cand + " | " + (org.get("city") or "") + ", "
                               + (org.get("state") or "")).strip(" |"),
                "as_of_date": d if ok else "",
                "as_of_date_basis": (
                    "last day of `tax_prd` (YYYYMM), the tax period the IRS "
                    "states on the most recent return filed under this EIN. "
                    "The date is the IRS's."
                    if ok else
                    "no date: the EIN on disk resolves to a different "
                    "organisation, or the IRS lists no dated filing for it"),
                "identifier_type": "EIN", "identifier_value": ein,
                "match_method": ("ein_lookup_name_verified" if ok
                                 else "NOT_MATCHED"),
                "match_note": mnote,
                "evidence": ("EIN taken from " + isrc + " as a LOOKUP KEY "
                             "only -- that link is tier B via containment and "
                             "is never inherited; the IRS's own name for the "
                             "EIN is re-checked before any date is written"),
            })
            rows.append(r)
    host_unlock(lock, spent > 0, refused)
    ok = sum(1 for r in rows if r["match_method"] != "NOT_MATCHED")
    print("    %d request(s) spent, %d row(s), %d name-verified"
          % (spent, len(rows), ok))
    return rows


# -------------------------------------------------- R4  IRS 990, by name
PP_SEARCH_BASE = "https://projects.propublica.org/nonprofits/api/v2/search.json"


def pp_search_url(name, state):
    """`urllib.parse.quote` LEAVES `/` ALONE, and that is a 404 here.

    `quote()` defaults to safe="/", so "Baca /Dlo'Ay Azhi Community School"
    became a query string containing a literal slash, ProPublica answered 404,
    and the first three entities in the queue all had that shape -- which
    tripped the host-refusing stop and ended the route after two rows. The
    host was fine. `urlencode` escapes everything.
    """
    q = {"q": deacc(name)}
    if state:
        q["state[id]"] = state
    return PP_SEARCH_BASE + "?" + urllib.parse.urlencode(q)

same_organisation = _N.same_organisation


def register_states():
    out = {}
    with open(REGISTER, encoding="utf-8-sig", newline="") as fh:
        for r in csv.DictReader(fh):
            if r.get("cedar_uid"):
                out[r["cedar_uid"]] = (r.get("state") or "").strip().upper()
    return out


def route_irs990_search(tail, ents, budget=900):
    """The entities with NO EIN anywhere on disk. Name search, STRICT accept.

    `same_organisation` is used, not `name_matches`: a search result is a
    stranger, and overlap against the smaller side is not identity. It
    produced four wrong EINs when 1021 tried the loose test -- Southern
    Indian Health Council -> Southern Exposure among them. Equality of the
    distinctive token sets, one substitution tolerated, or it is recorded as
    a CANDIDATE and carries no date.

    This route is what closes the Native Hawaiian Organization block: a
    sibling established the NHOs do not publish on their own websites, and
    135 of them had no date of any kind. What they DO have, almost all of
    them, is a Hawaii 501(c)(3) registration with dated returns.
    """
    have = tail_eins(tail)
    states = register_states()
    todo = [u for u in sorted(tail)
            if ents[u]["entity_class"] in NP_CLASSES and u not in have]
    print("    %d tail entit(ies) in a 990-filing class with NO EIN on disk"
          % len(todo))
    lock = host_lock("projects.propublica.org", "990 search, stale tail")
    if lock is None:
        return []
    rows, spent, refused = [], 0, []
    for u in todo:
        if spent >= budget:
            print("    budget %d reached; %d entit(ies) unattempted"
                  % (budget, len(todo) - todo.index(u)))
            break
        nm = ents[u]["canonical_name"]
        r = _base(u, ents, "irs990_search",
                  "IRS Form 990 via ProPublica Nonprofit Explorer (name search)",
                  "https://projects.propublica.org/nonprofits/search")
        r.update({"fact_key": "irs990_latest_tax_period", "fact_label": "",
                  "fact_value": "", "as_of_date": "",
                  "identifier_type": "", "identifier_value": "",
                  "uniform_source_date": "",
                  "evidence": "ProPublica Nonprofit Explorer name search"})
        if not has_identity(nm):
            r.update({"match_method": "NOT_MATCHED",
                      "match_note": "NO_IDENTIFIABLE_NAME",
                      "as_of_date_basis": "no date: the name carries no "
                                          "distinctive token, so no search "
                                          "result can be checked against it"})
            rows.append(r)
            continue
        st = states.get(u, "")
        url = pp_search_url(nm, st)
        spent += 1
        obj, note = get_json(url)
        if obj is None and note == "HTTP 404":
            # PROPUBLICA ANSWERS A ZERO-RESULT SEARCH WITH 404, NOT AN EMPTY
            # LIST. Measured 2026-09-02: `q=alu+like` -> 200 with one
            # organisation, `q=ahfachkee+school` -> 404, `q=school` -> 200.
            # 404 here is a fact about the QUERY, not about the host -- which
            # is exactly the distinction START_HERE draws -- and counting it
            # as a refusal stopped this route after two rows on its first run.
            r.update({"match_method": "NOT_MATCHED",
                      "match_note": "NO_IRS_ORGANISATION_FOR_THIS_NAME",
                      "as_of_date_basis": (
                          "no date: the IRS Exempt Organizations file "
                          "contains no organisation matching this name"
                          + (" in " + st if st else "")
                          + ". SOURCE_DOES_NOT_PUBLISH, not a Cedar gap.")})
            rows.append(r)
            continue
        if obj is None:
            refused.append(nm[:30] + ":" + note)
            if not any(x["as_of_date"] for x in rows) and len(refused) >= 3:
                print("    HOST REFUSING after %d attempts with nothing "
                      "landed: %s -- stopping"
                      % (len(refused), ",".join(refused)))
                host_unlock(lock, False, refused)
                return rows
            r.update({"match_method": "NOT_MATCHED",
                      "match_note": "SEARCH_FAILED:" + note,
                      "as_of_date_basis": "no date: the search did not answer"})
            rows.append(r)
            continue
        hits = obj.get("organizations") or []
        accepted = None
        for h in hits[:25]:
            ok, why = same_organisation(nm, h.get("name") or "")
            if ok:
                accepted = (h, why)
                break
        if not accepted:
            r.update({"match_method": "NOT_MATCHED",
                      "match_note": ("NO_EXACT_NAME_IN_%d_RESULT(S)%s"
                                     % (len(hits),
                                        "; nearest: "
                                        + (hits[0].get("name") or "")[:60]
                                        if hits else "")),
                      "as_of_date_basis": ("no date: the IRS lists no "
                                           "organisation whose name is this "
                                           "entity's" if hits else
                                           "no date: the IRS returns no "
                                           "organisation for this name"
                                           + (" in " + st if st else ""))})
            rows.append(r)
            continue
        h, why = accepted
        ein = str(h.get("ein") or "").zfill(9)
        spent += 1
        res, note2 = pp_filings(ein)
        d = res["tax_period_end"] if res else ""
        r.update({
            "source_url": ("https://projects.propublica.org/nonprofits/"
                           "organizations/" + str(int(ein))),
            "fact_label": "most recent Form 990 tax period the IRS records "
                          "for this organisation",
            "fact_value": ((h.get("name") or "") + " | "
                           + (h.get("city") or "") + ", "
                           + (h.get("state") or "")).strip(" |"),
            "as_of_date": d,
            "as_of_date_basis": (
                "last day of `tax_prd` (YYYYMM), the tax period the IRS "
                "states on the most recent return filed under EIN " + ein
                + ". The date is the IRS's."
                if d else
                "no date: the organisation is on the IRS list but no return "
                "with a tax period is published for it"),
            "identifier_type": "EIN", "identifier_value": ein,
            "match_method": "name_search_exact_token_sets",
            "match_note": why,
            "evidence": ("ProPublica name search%s returned %d "
                         "organisation(s); accepted only on EQUALITY of the "
                         "distinctive token sets, never on overlap"
                         % (" restricted to " + st if st else "", len(hits))),
        })
        rows.append(r)
    host_unlock(lock, spent > 0, refused)
    ok = sum(1 for x in rows if x["as_of_date"])
    print("    %d request(s) spent, %d row(s), %d dated" % (spent, len(rows), ok))
    return rows


# ------------------------------------------------------------------- writing
def grain(r):
    return (r.get("cedar_uid", ""), r.get("route", ""), r.get("source", ""),
            r.get("fact_key", ""), r.get("identifier_value", ""))


def write_rows(rows, routes):
    """Replace the rows of the routes just run; leave every other route alone.

    A ROUTE OWNS ITS ROWS, and re-running it must REPLACE them, not merge
    beside them. The first version merged on the grain, and when the CCD
    identity key was corrected from `ncessch` to the BIE school number the
    grain changed with it -- so 116 rows carrying the OLD, wrong key survived
    the fix and sat next to the right ones, and the bulk-stamp check fired on
    the stale copies. Same shape as the FERC partial restore: a re-run that
    only adds is a revert wearing a different hat.

    Header is still derived from the live file, never declared (845).
    """
    cols = live_header(OUT, CANONICAL)
    have = {}
    if os.path.exists(OUT):
        with open(OUT, encoding="utf-8-sig", newline="") as fh:
            for r in csv.DictReader(fh):
                if r.get("route") in routes:
                    continue
                have[grain(r)] = r
    for r in rows:
        have[grain(r)] = r
    ordered = sorted(have.values(),
                     key=lambda r: (r.get("entity_class", ""),
                                    r.get("canonical_name", ""),
                                    r.get("route", ""), r.get("fact_key", "")))
    tmp = OUT + ".part"
    with open(tmp, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in ordered:
            w.writerow({c: r.get(c, "") for c in cols})
    os.replace(tmp, OUT)
    return len(ordered)


# -------------------------------------------------------------------- verify
def check():
    """The NAMED invariants. Each is a way this job could have cheated."""
    if not os.path.exists(OUT):
        return ["output missing: " + OUT]
    with open(OUT, encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh))
    if not rows:
        return ["output is empty"]
    bad = []
    reg = set()
    with open(REGISTER, encoding="utf-8-sig", newline="") as fh:
        for r in csv.DictReader(fh):
            if r.get("cedar_uid"):
                reg.add(r["cedar_uid"])
    seen = set()
    dated, n_ent = defaultdict(set), defaultdict(set)
    uniform_ok = defaultdict(lambda: True)
    for i, r in enumerate(rows, 2):
        g = grain(r)
        if g in seen:
            bad.append("line %d: duplicate grain %s" % (i, g))
        seen.add(g)
        if r.get("cedar_uid") not in reg:
            bad.append("line %d: cedar_uid not in the register: %s"
                       % (i, r.get("cedar_uid")))
        d = (r.get("as_of_date") or "").strip()
        if not d:
            continue
        if not ISO.match(d):
            bad.append("line %d: as_of_date is not ISO: %r" % (i, d))
        elif d > TODAY:
            bad.append("line %d: as_of_date is in the FUTURE: %s" % (i, d))
        if not (r.get("as_of_date_basis") or "").strip():
            bad.append("line %d: a date with no basis" % i)
        if r.get("match_method") == "NOT_MATCHED":
            bad.append("line %d: NOT_MATCHED carries a date" % i)
        if d == (r.get("checked_date") or ""):
            bad.append("line %d: as_of_date equals checked_date -- that is "
                       "Cedar's clock, not the source's" % i)
        k = (r.get("route"), r.get("fact_key"))
        dated[k].add(d)
        n_ent[k].add(r.get("cedar_uid"))
        if r.get("uniform_source_date") != "Y":
            uniform_ok[k] = False
    # THE BULK-STAMP INVARIANT -- the same shape 830 enforces, applied per
    # (route, fact_key), which is STRICTER than 830's per-column test. This is
    # the exact failure mode this job was warned about.
    #
    # ONE NARROW, AUDITABLE EXEMPTION, and it cannot be used to fake freshness.
    # NCES's BIE reporting universe is static: 174 schools reported in every
    # collection year 2008-2024, so "the most recent year this school
    # reported" is genuinely 2024 for all 174. That uniformity is a property
    # of the SOURCE's collection, not of a Cedar build. A route may declare it
    # by setting `uniform_source_date = Y` -- but only where EVERY date in the
    # group is older than the 365-day staleness bar, so a declared-uniform
    # date can never be the thing that makes an entity look fresh, which is
    # the only harm the invariant exists to prevent.
    floor = max(1, int(len(reg) * 0.05))
    cutoff = (date.fromisoformat(TODAY)
              - timedelta(days=STALE_BAR_DAYS)).isoformat()
    for k, ds in dated.items():
        if len(n_ent[k]) < floor or len(ds) > 3:
            continue
        if uniform_ok[k] and max(ds) < cutoff:
            continue
        bad.append("BULK STAMP: %s dates %d entities from only %d distinct "
                   "value(s): %s%s"
                   % (str(k), len(n_ent[k]), len(ds), sorted(ds),
                      "" if uniform_ok[k] else
                      " -- and it is not declared `uniform_source_date`"
                      if max(ds) < cutoff else
                      " -- declared uniform, but %s is inside the %d-day "
                      "staleness bar, so it WOULD make these entities look "
                      "fresh" % (max(ds), STALE_BAR_DAYS)))
    return bad


_SELFTEST_SIG = {
    "future date": "FUTURE",
    "date with no basis": "no basis",
    "as_of == checked": "Cedar's clock",
    "uid not in register": "not in the register",
    "NOT_MATCHED with a date": "NOT_MATCHED carries a date",
    "duplicate grain": "duplicate grain",
}


def selftest():
    """Prove verify FIRES on each NAMED invariant, then restore and re-verify."""
    if not os.path.exists(OUT):
        print("  selftest: run the script first (nothing to perturb)")
        return 1
    with open(OUT, encoding="utf-8", newline="") as fh:
        original = fh.read()
    cols = live_header(OUT, CANONICAL)
    real_uid = ""
    with open(OUT, encoding="utf-8-sig", newline="") as fh:
        for r in csv.DictReader(fh):
            real_uid = r["cedar_uid"]
            break
    fails = []

    def stub(**patch):
        row = {c: "" for c in cols}
        row.update({"cedar_uid": real_uid, "canonical_name": "SELFTEST",
                    "entity_class": "SELFTEST", "route": "selftest",
                    "source": "selftest", "fact_key": "selftest",
                    "identifier_value": "SELFTEST", "checked_date": TODAY})
        row.update(patch)
        return row

    cases = [
        ("future date", [stub(as_of_date="2099-01-01", as_of_date_basis="x")]),
        ("date with no basis", [stub(as_of_date="2020-01-01")]),
        ("as_of == checked", [stub(as_of_date=TODAY, as_of_date_basis="x")]),
        ("uid not in register", [stub(cedar_uid="CE-NOTREAL-XX",
                                      as_of_date="2020-01-01",
                                      as_of_date_basis="x")]),
        ("NOT_MATCHED with a date", [stub(match_method="NOT_MATCHED",
                                          as_of_date="2020-01-01",
                                          as_of_date_basis="x")]),
        ("duplicate grain", [stub(as_of_date="2020-01-01",
                                  as_of_date_basis="x"),
                             stub(as_of_date="2020-01-01",
                                  as_of_date_basis="x")]),
        ("bulk stamp",
         [stub(fact_key="stamp", identifier_value="S%03d" % n,
               as_of_date="2026-01-01", as_of_date_basis="x")
          for n in range(120)]),
    ]
    try:
        for label, injected in cases:
            with open(OUT, "a", encoding="utf-8", newline="") as fh:
                w = csv.DictWriter(fh, fieldnames=cols)
                for row in injected:
                    w.writerow(row)
            bad = check()
            sig = _SELFTEST_SIG.get(label, "BULK STAMP")
            fired = any(sig in b for b in bad)
            print("    %-26s %s" % (label, "FIRES" if fired else "DID NOT FIRE"))
            if not fired:
                fails.append(label)
            with open(OUT, "w", encoding="utf-8", newline="") as fh:
                fh.write(original)
    finally:
        with open(OUT, "w", encoding="utf-8", newline="") as fh:
            fh.write(original)
    residual = check()
    print("    %-26s %s" % ("restored, verify clean",
                            "yes" if not residual else "NO: %s" % residual[:2]))
    if residual:
        fails.append("restore")
    print("  1081 selftest: %d failure(s)" % len(fails))
    return 1 if fails else 0


# ---------------------------------------------------------------------- main
ROUTES = {"ondisk_uei": route_ondisk_uei, "ccd": route_ccd,
          "irs990": route_irs990, "irs990_search": route_irs990_search}


def run(argv):
    want = [a.split("=", 1)[1] for a in argv if a.startswith("--routes=")]
    names = want[0].split(",") if want else list(ROUTES)
    ents, g = tail_slice()
    tail = g["stale"] | g["undated"] | g["nosub"]
    print("  tail: %d entities (stale %d, undated %d, no substantive row %d)"
          % (len(tail), len(g["stale"]), len(g["undated"]), len(g["nosub"])))
    allrows = []
    for n in names:
        if n not in ROUTES:
            print("  unknown route: " + n)
            return 2
        print("  route %s" % n)
        allrows.extend(ROUTES[n](tail, ents))
    total = write_rows(allrows, set(names))
    print("  wrote %d row(s) this run; %s now holds %d"
          % (len(allrows), os.path.relpath(OUT, ROOT), total))
    bad = check()
    print("  verify: %d violation(s)" % len(bad))
    for b in bad[:10]:
        print("    " + b)
    return 1 if bad else 0


def main():
    a = sys.argv[1] if len(sys.argv) > 1 else "measure"
    if a == "measure":
        for k, v in measure().items():
            print("  %-24s %d" % (k, v))
        return 0
    if a == "verify":
        bad = check()
        for b in bad[:40]:
            print("    VIOLATION  " + b)
        print("  1081 verify: %d violation(s)" % len(bad))
        return 1 if bad else 0
    if a == "selftest":
        return selftest()
    if a == "run":
        return run(sys.argv[2:])
    print(__doc__)
    return 0


if __name__ == "__main__":
    sys.exit(main())
