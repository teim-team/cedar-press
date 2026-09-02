#!/usr/bin/env python3
"""
1021_register_only_first_rows.py -- THE OTHER TAIL: entities with no row.

    py -3 code/1021_register_only_first_rows.py            # find them, then
                                                           # find them something
    py -3 code/1021_register_only_first_rows.py verify     # exit 1 on violation
    py -3 code/1021_register_only_first_rows.py selftest   # prove verify fires

WHY -- AND WHY 830 SAYS ZERO
    `code/830_entity_freshness.py` exists to answer the owner's standing worry:
    an entity can sit in the identity layer while no dataset has a single row
    for it, silently, forever, because nothing counts them. Its headline line
    is **"appear in NO Cedar row at all"**, and on 2026-09-02 it printed **0**.

    Zero is not a finding here. It is a defect, and it is this project's own
    recurring one -- a check that measures something other than what its name
    says and reports green.

    830 scans every `*.csv` in `data/clean` that carries an id column. Four of
    those files are the IDENTITY LAYER rather than a dataset:

        cedar_entity_freshness.csv   <- 830's OWN OUTPUT, one row per entity
        cedar_assertions.csv         <- what Cedar has claimed
        cedar_resolved_facts.csv     <- what Cedar has adjudicated
        entity_aliases.csv           <- names, one or more per entity

    `cedar_entity_freshness.csv` alone makes the number unreachable: 830 writes
    a row for all 1,555 entities, into the directory it scans, so from its
    second run onward every entity is "in a Cedar row" and `absent` is
    structurally pinned at 0 forever. The measure cannot fail, which means it
    cannot report.

    Excluding the identity layer, the honest count on 2026-09-02 is **104**:
    83 BIE Schools, 18 federal-level self-governance consortia, 3 Urban Indian
    Organizations. Those are the entities the owner has been asking about, and
    they were invisible.

    Then the name list failed too, an hour later and in the same session. The
    newsletter workstream landed `tribal_newsletter_coverage.csv` -- 1,555
    rows, one per register entity -- and the count went straight back to 0. A
    filename blacklist cannot see a file written after it, which is why
    `CENSUS_COVERAGE_MIN` below is a SHAPE test and not another name. With
    both defences the count is 83 absent plus 35 in exactly one table.

    This file computes that number properly, then does something about it.

WHAT "SOMETHING" MEANS
    A first row. Not a website -- 1020 owns the web tail -- but a fact from a
    public register that ties the entity to the world:

      BIE School     NCES Common Core of Data, the BIE reporting universe
                     (fips 59), via the Urban Institute Education Data API.
                     Yields the NCES school id, the LEA, the physical address,
                     phone, coordinates and the years the school reported.
      everything     IRS/990 via ProPublica Nonprofit Explorer -> EIN.
      else           Federal assistance via the USAspending award search ->
                     award ids, agency and obligated amounts.

    Health consortia are 638 self-governance contractors; a tribal school is a
    reporting unit in a federal collection. Both leave heavy public traces.
    That they had no Cedar row was never evidence that nothing exists.

THE TRAP IN THE USASPENDING KEYWORD SEARCH
    `keywords` is fuzzy. A search for "Norton Sound Health Corporation"
    returns KAWERAK, INC. in the first position. Accepting position one would
    attribute another organisation's money to this entity, which is worse than
    the blank it replaces because a blank is visible in the ledger and a wrong
    attribution is not. Every hit here must pass a recipient-name token test
    before it is written, and the test is recorded in `match_method`.

WHAT IT NEVER DOES
    No commits. No spine writes -- this is staging evidence, and promoting any
    of it to a dataset or to `entity_website` is an assertion that goes through
    510 with a human. No minting, no repointing, no identity resolution: a
    candidate that does not pass the name test is written as NOT_MATCHED with
    what was seen, never resolved on a guess. Zero fabrication; flag, never
    delete.
"""
from __future__ import annotations

import csv
import json
import os
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REGISTER = os.path.join(ROOT, "data", "spine", "cedar_identity_register.csv")
CLEAN = os.path.join(ROOT, "data", "clean")
STAGE = os.path.join(ROOT, "data", "staging")
OUT = os.path.join(STAGE, "register_only_first_rows.csv")
CACHE = os.path.join(STAGE, "tribe_harvest", "shard_n")
OUT_DOC = os.path.join(ROOT, "docs", "REGISTER_ONLY_TAIL.md")
TODAY = date.today().isoformat()

UA = ("CedarPress-research/1.0 (register coverage tail; contact "
      "elijahsamsonmoreno@gmail.com)")

# Same id columns 830 reads, so the two measures are comparable.
ID_COLS = ("cedar_uid", "tribe_id", "entity_id", "nation_id",
           "certifying_authority_entity_id", "recipient_entity_id")

# THE IDENTITY LAYER IS NOT A DATASET. See the docstring: counting these is
# what pins 830's `absent` at zero. `cedar_entity_freshness.csv` is 830's own
# output and is the fatal one; the other three are Cedar's claims about
# entities rather than observations of them.
IDENTITY_LAYER = {
    "cedar_entity_freshness.csv",
    "cedar_assertions.csv",
    "cedar_resolved_facts.csv",
    "entity_aliases.csv",
    "cedar_identity_register.csv",
    "cedar_entity_relationships.csv",
    "cedar_constellation_edges.csv",
    "cedar_source_records.csv",
}

# AND THE NAME LIST IS NOT THE DEFENCE, BECAUSE IT ALREADY FAILED ONCE TODAY.
#
# Within an hour of the list above being written, the newsletter workstream
# landed `tribal_newsletter_coverage.csv` -- 1,555 rows, one for every register
# entity, `probe_status` per entity. It is a ledger of OUR effort, exactly like
# `cedar_entity_freshness.csv`, and its arrival silently returned the count of
# register-only entities to 0. A blacklist of filenames cannot see a file
# written after it. That is the same reason 830's `NEVER` list of column names
# failed three times and had to grow a shape-based test beside it.
#
# THE SHAPE. A table with a row for essentially EVERY register entity and
# essentially ONE row each is a census of the register, not a set of
# observations about entities. A real dataset covers the entities it has
# something to say about: `entity_hierarchy.csv` is also one row per entity but
# reaches only 61% of the register, and it is kept.
#
# Measured against the live tree 2026-09-02: this refuses
# `tribal_newsletter_coverage.csv` and `cedar_entity_freshness.csv` and nothing
# else. Refused tables are NAMED in the output, never silently dropped.
CENSUS_COVERAGE_MIN = 0.98      # of the register
CENSUS_ROWS_PER_UID_MAX = 1.05

CCD = "https://educationdata.urban.org/api/v1/schools/ccd/directory/"
CCD_YEARS = (2022, 2021, 2020, 2019, 2018, 2016, 2014, 2012, 2010, 2008,
             2005, 2000)
CCD_FIPS_BIE = 59            # the Bureau of Indian Education reporting unit
PP = "https://projects.propublica.org/nonprofits/api/v2/search.json"
USASPEND = "https://api.usaspending.gov/api/v2/search/spending_by_award/"

COLS = ["cedar_uid", "canonical_name", "entity_class",
        "n_substantive_tables", "substantive_tables", "route",
        "evidence_class", "identifier_type", "identifier_value",
        "fact_label", "fact_value", "source", "source_url", "as_of",
        "match_method", "checked_date", "evidence"]

_last = [0.0]


def _pace(sec=0.6):
    d = sec - (time.time() - _last[0])
    if d > 0:
        time.sleep(d)
    _last[0] = time.time()


def get_json(url, payload=None, timeout=90, tries=3):
    """-> (obj|None, note). Never raises."""
    for n in range(tries):
        _pace()
        try:
            data = None
            hdrs = {"User-Agent": UA, "Accept": "application/json"}
            if payload is not None:
                data = json.dumps(payload).encode()
                hdrs["Content-Type"] = "application/json"
            req = urllib.request.Request(url, data=data, headers=hdrs)
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


# ------------------------------------------------------------------ names
def deacc(s):
    s = (s or "").replace("ʻ", "").replace("‘", "")
    s = s.replace("’", "").replace("'", "")
    return "".join(c for c in unicodedata.normalize("NFKD", s)
                   if not unicodedata.combining(c))


GENERIC = {"school", "schools", "community", "day", "elementary", "middle",
           "high", "boarding", "academy", "dormitory", "tribal", "indian",
           "the", "of", "and", "inc", "incorporated", "corp", "corporation",
           "nation", "tribe", "center", "centre", "jr", "sr", "public",
           "consortium", "health", "council", "association", "services",
           "system", "systems", "program", "clinic", "care", "county",
           "area", "regional", "native", "american", "llc", "phase"}


MINIMAL_STOP = {"the", "of", "and", "inc", "incorporated", "llc", "corp"}


def toks(name, allow_fallback=True):
    """Distinctive words. Returns [] only if `allow_fallback` is off.

    A NAME MADE ENTIRELY OF GENERIC WORDS HAS NO DISTINCTIVE TOKENS, AND THE
    FIRST VERSION THEREFORE COULD NOT MATCH IT AT ALL. 'Indian Health
    Council, Inc.' is `indian`+`health`+`council`, all three on the GENERIC
    list, so `toks` returned nothing and every route recorded a negative for
    an organisation that files a 990 every year. A test that cannot succeed
    is not a strict test, it is a broken one. The fallback keeps the words;
    `name_matches` compensates by demanding ALL of them instead of 60%.
    """
    s = re.sub(r"[^a-z0-9 ]", " ", deacc(name).lower())
    words = [t for t in s.split() if len(t) > 2 and t not in MINIMAL_STOP]
    strong = [t for t in words if t not in GENERIC]
    if strong or not allow_fallback:
        return strong
    return words


def _close(x, y):
    """Equal, or one substitution apart on a word of 5+ characters.

    'Utah Navaho Health System' on the register is 'Utah Navajo Health
    System' at the IRS. One letter. Requiring exact tokens recorded a
    negative for a 638 contractor with an EIN and federal awards, which is a
    false absence produced by a transliteration -- and false absences here
    are load-bearing.
    """
    if x == y:
        return True
    if len(x) != len(y) or len(x) < 5:
        return False
    return sum(1 for p, q in zip(x, y) if p != q) == 1


def name_matches(a, b, need=None):
    """Distinctive-token overlap, one substitution tolerated. -> (ok, note).

    Generic words are stripped first, because 'Health Corporation' matches
    every health corporation in Alaska and 'Day School' matches ninety BIE
    schools. What is left is the part that identifies the organisation.
    """
    sa, sb = toks(a, False), toks(b, False)
    fallback = not sa
    ta = set(sa or toks(a))
    tb = set(sb or toks(b))
    if not ta or not tb:
        return False, "no tokens on one side"
    inter = {x for x in ta if any(_close(x, y) for y in tb)}
    if need is None:
        if fallback:
            # Every word of an all-generic name must be present, or 'Indian
            # Health Council' would match 'Indian Health Care Resource
            # Center' on two shared generic words.
            need = len(ta)
        elif len(ta) <= 2:
            need = min(len(ta), len(tb))
        else:
            need = max(1, int(round(min(len(ta), len(tb)) * 0.6)))
    ok = len(inter) >= need
    return ok, ("tokens %d/%d shared (%s) need %d%s"
                % (len(inter), min(len(ta), len(tb)),
                   ",".join(sorted(inter))[:60], need,
                   "; all-generic name, ALL required" if fallback else ""))


# ------------------------------------------------------------------ slice
def read_register():
    with open(REGISTER, encoding="utf-8-sig", errors="replace",
              newline="") as fh:
        return list(csv.DictReader(fh))


def substantive_presence():
    """uid -> set of SUBSTANTIVE tables holding a row for it.

    Identity-layer files are excluded and NAMED, not silently dropped, so the
    exclusion is auditable and arguable rather than buried."""
    csv.field_size_limit(10_000_000)
    reg = read_register()
    known = {r["cedar_uid"] for r in reg if r.get("cedar_uid")}
    handle = {r["handle"]: r["cedar_uid"] for r in reg if r.get("handle")}
    per_table: dict = {}
    scanned, skipped = [], []
    for fn in sorted(os.listdir(CLEAN)):
        if not fn.endswith(".csv") or ".bak" in fn or fn.startswith("_"):
            continue
        p = os.path.join(CLEAN, fn)
        try:
            with open(p, encoding="utf-8-sig", errors="replace",
                      newline="") as fh:
                rd = csv.DictReader(fh)
                hdr = rd.fieldnames or []
                idc = next((c for c in ID_COLS if c in hdr), None)
                if not idc:
                    continue
                if fn in IDENTITY_LAYER:
                    skipped.append(fn + " (named identity layer)")
                    continue
                uids, n = set(), 0
                for r in rd:
                    raw = (r.get(idc) or "").strip()
                    if not raw:
                        continue
                    uid = raw if raw in known else handle.get(raw)
                    if uid:
                        uids.add(uid)
                        n += 1
                per_table[fn] = (uids, n)
        except OSError:
            continue

    seen: dict = {}
    for fn, (uids, n) in sorted(per_table.items()):
        cov = len(uids) / max(1, len(known))
        rpu = n / max(1, len(uids))
        if cov >= CENSUS_COVERAGE_MIN and rpu <= CENSUS_ROWS_PER_UID_MAX:
            skipped.append("%s (census of the register: %.0f%% coverage, "
                           "%.2f rows/entity)" % (fn, cov * 100, rpu))
            continue
        scanned.append(fn)
        for uid in uids:
            seen.setdefault(uid, set()).add(fn)
    return seen, scanned, skipped


# THE SLICE IS THE THIN TAIL, NOT ONLY THE EMPTY ONE.
#
# Measured 2026-09-02: 83 entities in ZERO substantive tables and 35 more in
# exactly one. The line between them moved WHILE THIS FILE WAS BEING WRITTEN --
# the newsletter workstream landed `tribal_newsletter_corpus.csv` and 21
# entities that had been register-only an hour earlier acquired exactly one
# row apiece. Slicing on == 0 would have dropped them on the floor at the
# moment they became reachable, which is the wrong response to a sibling
# landing.
#
# So the slice is <= 1, and `n_substantive_tables` is written on every row so
# the two states stay TOLD APART: 0 is "no dataset has ever carried this
# entity", 1 is "exactly one has". Collapsing them would repeat, one level up,
# the untouched-vs-none-found conflation this whole workstream exists to fix.
THIN_TAIL_MAX_TABLES = 1


def slice_rows():
    seen, scanned, skipped = substantive_presence()
    reg = read_register()
    out = []
    for r in reg:
        u = r.get("cedar_uid")
        if not u:
            continue
        n = len(seen.get(u, ()))
        if n <= THIN_TAIL_MAX_TABLES:
            r = dict(r)
            r["_n_tables"] = n
            r["_tables"] = ";".join(sorted(seen.get(u, ())))
            out.append(r)
    return out, scanned, skipped


# ------------------------------------------------------------- route: CCD
def load_ccd():
    """Every BIE-universe school NCES has published, across years, cached.

    Multiple years on purpose: names are re-keyed over time ('AHFACHKEE DAY
    SCHOOL' in 2012 is 'Ahfachkee School' now) and a school that closed is
    still a real first row for an entity that has none. One year would have
    matched 63 of 83; the name variants are the difference.
    """
    os.makedirs(CACHE, exist_ok=True)
    p = os.path.join(CACHE, "ccd_bie_directory.json")
    if os.path.exists(p):
        with open(p, encoding="utf-8") as fh:
            return json.load(fh)
    recs = []
    for y in CCD_YEARS:
        u = (CCD + str(y) + "/?fips=" + str(CCD_FIPS_BIE) + "&limit=1000")
        d, note = get_json(u)
        if not d:
            print("    CCD %d -> %s" % (y, note))
            continue
        recs += d.get("results", [])
        print("    CCD %d -> %d schools" % (y, len(d.get("results", []))))
    with open(p, "w", encoding="utf-8") as fh:
        json.dump(recs, fh)
    return recs


def ccd_lookup(name, recs):
    """Best CCD record for a school name. Returns (rec, note) or (None, note).

    Preference is for the most recent year that carries the name, because a
    current address is more useful than a 2000 one -- but ANY year is a hit.
    """
    best, best_note, best_year = None, "", -1
    for r in recs:
        ok, note = name_matches(name, r.get("school_name", ""))
        if not ok:
            continue
        y = int(r.get("year") or 0)
        if y > best_year:
            best, best_note, best_year = r, note, y
    if best:
        return best, best_note
    # NEAR MISSES ARE REPORTED, NOT RESOLVED.
    # 'Shiprock Reservation Dormitory' sits beside CCD's 'SHIPROCK ALTERNATIVE
    # DORMITORY'. They may be the same facility renamed, or two facilities.
    # Guessing would mint a wrong NCES id onto an entity; saying nothing would
    # hide a lead a human can settle in a minute. So the candidate is written
    # with the mismatch stated and NO identifier claimed. Flag, never delete.
    want = set(toks(name))
    near = []
    for r in recs:
        got = set(toks(r.get("school_name", "")))
        if want & got:
            near.append((len(want & got), r.get("school_name", ""),
                         r.get("ncessch", ""), r.get("year")))
    near.sort(reverse=True)
    seen_n, out = set(), []
    for _s, nm, nid, _y in near:
        if nm.lower() in seen_n:
            continue
        seen_n.add(nm.lower())
        out.append(nm + " [NCES " + str(nid) + "]")
        if len(out) == 3:
            break
    return None, ("no CCD BIE-universe school name passed the token test"
                  + ("; NEAR MISSES (not resolved): " + "; ".join(out)
                     if out else "; no near miss either"))


# -------------------------------------------------------- route: 990/IRS
def _pp_once(query):
    """-> (orgs|None, note). HTTP 404 IS PROPUBLICA'S EMPTY RESULT.

    The first pass recorded `propublica:HTTP 404` on nine entities and those
    read like transport failures in the evidence column. They are not: this
    API answers a search with no hits by 404-ing. Saying so in the note is the
    difference between a recorded negative and a recorded error, and a reader
    who cannot tell them apart cannot trust either.
    """
    d, note = get_json(PP + "?" + urllib.parse.urlencode({"q": query}),
                       timeout=45, tries=2)
    if d is None:
        if note == "HTTP 404":
            return [], "zero_results(404 is this API's empty search)"
        return None, note
    return (d.get("organizations") or []), "ok"


def propublica(name, state=""):
    """Full name, then the distinctive tokens alone.

    `state` is accepted and DELIBERATELY IGNORED. Filtering on the register's
    state killed Utah Navaho Health System -- 200 and a hit without the
    filter, 404 with it -- because the state an organisation FILES in is not
    always the state Cedar records it in. A filter that removes true positives
    to save a name test is a bad trade when the name test is the real
    discriminator.

    The token retry is the same lesson as SEARCHING FOR THE INSTITUTION
    INSTEAD OF THE THING: 'Juel Fairbanks Recovery Services' returns nothing
    because the filer is 'Juel Fairbanks Chemical Dependency Services'. The
    distinctive part of the name is the query; the rest is decoration.
    """
    queries = [name]
    t = toks(name)
    if t and " ".join(t[:3]) != name.lower():
        queries.append(" ".join(t[:3]))
    if len(t) > 1:
        queries.append(" ".join(t[:2]))
    notes = []
    for q in queries:
        orgs, note = _pp_once(q)
        if orgs is None:
            notes.append("q=%r %s" % (q, note))
            continue
        if not orgs:
            notes.append("q=%r %s" % (q, note))
            continue
        for o in orgs:
            ok, mnote = name_matches(name, o.get("name", ""))
            if not ok and o.get("sub_name"):
                ok, mnote = name_matches(name, o["sub_name"])
            if ok:
                return o, "propublica: q=%r %s" % (q, mnote)
        notes.append("q=%r %d results, none passed the name test"
                     % (q, len(orgs)))
    return None, "propublica: " + "; ".join(notes)


# ------------------------------------------------- route: federal awards
ASSISTANCE = ["02", "03", "04", "05"]
CONTRACTS = ["A", "B", "C", "D"]


def usaspending(name, codes, start="2007-10-01"):
    """Keyword search, then a RECIPIENT-NAME test on every row.

    The keyword index is fuzzy and will happily hand back a neighbouring
    organisation -- 'Norton Sound Health Corporation' returns KAWERAK, INC.
    first. Filtering here is the difference between a first row and a
    misattribution.
    """
    kw = [name]
    t = toks(name)
    if len(t) >= 2:
        kw.append(" ".join(t[:3]))
    payload = {"filters": {"keywords": kw, "award_type_codes": codes,
                           "time_period": [{"start_date": start,
                                            "end_date": TODAY}]},
               "fields": ["Award ID", "Recipient Name", "Award Amount",
                          "Awarding Agency", "Start Date"],
               "limit": 100, "page": 1}
    d, note = get_json(USASPEND, payload, timeout=120)
    if not d:
        return [], "usaspending:" + note
    kept, seen_names = [], set()
    for r in d.get("results", []):
        rn = r.get("Recipient Name") or ""
        ok, mnote = name_matches(name, rn)
        seen_names.add(rn)
        if ok:
            r["_match"] = mnote
            kept.append(r)
    if not kept:
        return [], ("usaspending:" + str(len(d.get("results", [])))
                    + "_hits_none_passed_the_recipient_name_test"
                    + (" (saw: " + "; ".join(sorted(seen_names)[:3]) + ")"
                       if seen_names else ""))
    return kept, "usaspending:" + str(len(kept)) + "_rows_passed"


# ---------------------------------------------------------------- writer
def ensure_out():
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    if not os.path.exists(OUT) or os.path.getsize(OUT) == 0:
        with open(OUT, "w", encoding="utf-8", newline="") as fh:
            csv.writer(fh).writerow(COLS)


def add(**kw):
    """Append ONE row and fsync. Flush per entity, never at the end."""
    ensure_out()
    row = [kw.get(c, "") for c in COLS]
    with open(OUT, "a", encoding="utf-8", newline="") as fh:
        csv.writer(fh).writerow(row)
        fh.flush()
        os.fsync(fh.fileno())


def already():
    if not os.path.exists(OUT):
        return set()
    with open(OUT, encoding="utf-8-sig", errors="replace", newline="") as fh:
        return {(r.get("cedar_uid") or "").strip() for r in csv.DictReader(fh)}


# ------------------------------------------------------------------- run
def run():
    rows, scanned, skipped = slice_rows()
    print("  1021 register-only tail")
    print("    %d substantive tables scanned; %d identity-layer files "
          "EXCLUDED and named: %s"
          % (len(scanned), len(skipped), ", ".join(sorted(skipped))))
    n0 = sum(1 for r in rows if r["_n_tables"] == 0)
    print("    thin tail: %d entities in <= %d substantive table(s) "
          "-- %d of them in ZERO"
          % (len(rows), THIN_TAIL_MAX_TABLES, n0))
    from collections import Counter
    for k, v in Counter(r["entity_class"] for r in rows).most_common():
        print("      %-45s %d" % (k, v))
    done = already()
    todo = [r for r in rows if r["cedar_uid"] not in done]
    print("    %d already have evidence written, %d to do"
          % (len(rows) - len(todo), len(todo)))
    if not todo:
        return 0

    ccd = load_ccd() if any(r["entity_class"] == "BIE School"
                            for r in todo) else []
    print("    CCD BIE universe: %d school-year records" % len(ccd))

    n_first = 0
    for i, r in enumerate(todo, 1):
        uid, name = r["cedar_uid"], r.get("canonical_name", "")
        cls = r.get("entity_class", "")
        st = (r.get("state") or "").strip()
        ctx = {"n_substantive_tables": r["_n_tables"],
               "substantive_tables": r["_tables"]}
        tried, got = [], False

        if cls == "BIE School":
            rec, note = ccd_lookup(name, ccd)
            tried.append("NCES Common Core of Data, BIE reporting universe "
                         "(fips 59), years " + str(CCD_YEARS[-1]) + "-"
                         + str(CCD_YEARS[0]) + " -> " + note)
            if rec:
                got = True
                n_first += 1
                addr = ", ".join(x for x in
                                 [rec.get("street_location"),
                                  rec.get("city_location"),
                                  rec.get("state_location"),
                                  str(rec.get("zip_location") or "")] if x)
                add(**ctx, cedar_uid=uid, canonical_name=name, entity_class=cls,
                    route="NCES_CCD", evidence_class="FACILITY_DIRECTORY",
                    identifier_type="NCES_SCHOOL_ID",
                    identifier_value=rec.get("ncessch", ""),
                    fact_label="school_directory_record",
                    fact_value=(rec.get("school_name", "") + " | LEA "
                                + str(rec.get("leaid", "")) + " "
                                + str(rec.get("lea_name", "")) + " | "
                                + addr + " | tel "
                                + str(rec.get("phone", "")) + " | lat/lon "
                                + str(rec.get("latitude", "")) + ","
                                + str(rec.get("longitude", ""))),
                    source="NCES Common Core of Data via Urban Institute "
                           "Education Data API",
                    source_url=(CCD + str(rec.get("year")) + "/?fips=59"),
                    as_of=str(rec.get("year", "")),
                    match_method="distinctive_token_overlap: " + note,
                    checked_date=TODAY,
                    evidence="TRIED: " + " | ".join(tried)
                             + " || FIRST ROW for an entity that had none in "
                               "any substantive Cedar table.")

        if not got or cls != "BIE School":
            o, note = propublica(name, st if st in ("HI", "AK", "CA", "OK",
                                                    "AZ", "UT", "MT", "MN")
                                 else "")
            tried.append("IRS/990 via ProPublica Nonprofit Explorer -> " + note)
            if o:
                got = True
                n_first += 1
                add(**ctx, cedar_uid=uid, canonical_name=name, entity_class=cls,
                    route="IRS_990", evidence_class="TAX_FILER",
                    identifier_type="EIN",
                    identifier_value=o.get("strein") or str(o.get("ein")),
                    fact_label="irs_exempt_organisation",
                    fact_value=((o.get("name") or "") + " | "
                                + (o.get("city") or "") + " "
                                + (o.get("state") or "") + " | NTEE "
                                + str(o.get("ntee_code") or "") + " | 501(c)"
                                + str(o.get("subseccd") or "")),
                    source="ProPublica Nonprofit Explorer (IRS BMF / Form 990)",
                    source_url=("https://projects.propublica.org/nonprofits/"
                                "organizations/" + str(o.get("ein"))),
                    as_of=TODAY,
                    match_method="distinctive_token_overlap: " + note,
                    checked_date=TODAY,
                    evidence="TRIED: " + " | ".join(tried)
                             + " || FIRST ROW: an EIN ties this entity to the "
                               "990 corpus Cedar already holds.")

        if cls != "BIE School":
            for codes, label in ((ASSISTANCE, "federal assistance"),
                                 (CONTRACTS, "prime contracts")):
                hits, note = usaspending(name, codes)
                tried.append("USAspending " + label + " -> " + note)
                if hits:
                    got = True
                    n_first += 1
                    tot = sum(float(h.get("Award Amount") or 0) for h in hits)
                    top = sorted(hits, key=lambda h: -float(
                        h.get("Award Amount") or 0))[:3]
                    add(**ctx, cedar_uid=uid, canonical_name=name, entity_class=cls,
                        route="USASPENDING",
                        evidence_class="FEDERAL_AWARD",
                        identifier_type="AWARD_ID",
                        identifier_value=";".join(
                            str(h.get("Award ID")) for h in top),
                        fact_label=label.replace(" ", "_") + "_present",
                        fact_value=("%d awards passing the recipient-name "
                                    "test, %.0f USD total; largest: %s"
                                    % (len(hits), tot,
                                       "; ".join(
                                           str(h.get("Recipient Name")) + " "
                                           + str(h.get("Award ID")) + " "
                                           + str(h.get("Awarding Agency"))
                                           for h in top))),
                        source="USAspending API v2 spending_by_award",
                        source_url=USASPEND,
                        as_of=TODAY,
                        match_method=("recipient_name_token_test; "
                                      + str(top[0].get("_match", ""))),
                        checked_date=TODAY,
                        evidence="TRIED: " + " | ".join(tried)
                                 + " || FIRST ROW from federal award data.")

        if not got:
            add(**ctx, cedar_uid=uid, canonical_name=name, entity_class=cls,
                route="NONE", evidence_class="NONE_FOUND",
                identifier_type="", identifier_value="",
                fact_label="no_public_record_located",
                fact_value="", source="", source_url="", as_of="",
                match_method="", checked_date=TODAY,
                evidence="TRIED: " + " | ".join(tried)
                         + " || CHECKED " + TODAY + ", nothing located. This "
                           "is attempted-and-none-found, NOT unexamined.")
        if i % 10 == 0:
            print("      %d/%d  %d evidence rows written"
                  % (i, len(todo), n_first))
    print("    done: %d evidence rows for %d entities" % (n_first, len(todo)))
    write_doc(rows, scanned, skipped)
    return 0


# ------------------------------------------------------------------- doc
def write_doc(rows, scanned, skipped):
    from collections import Counter, defaultdict
    got = defaultdict(list)
    if os.path.exists(OUT):
        with open(OUT, encoding="utf-8-sig", errors="replace",
                  newline="") as fh:
            for r in csv.DictReader(fh):
                got[r["cedar_uid"]].append(r)
    closed = [u for u, v in got.items()
              if any(x["evidence_class"] != "NONE_FOUND" for x in v)]
    L = ["# The register-only tail — entities with no substantive Cedar row",
         "",
         "*Generated " + TODAY + " by `code/1021_register_only_first_rows.py`."
         " Evidence: `data/staging/register_only_first_rows.csv`. This is "
         "STAGING. Promoting any of it to a dataset is an assertion and goes "
         "through 510.*",
         "",
         "## Why `830` reported zero",
         "",
         "`code/830_entity_freshness.py` prints **\"appear in NO Cedar row at "
         "all\"** and on 2026-09-02 it printed **0**. That is not a finding, "
         "it is a defect of the familiar shape: the check measures something "
         "other than what its name says and therefore always reads green.",
         "",
         "830 scans every id-bearing `*.csv` in `data/clean`. Four of those "
         "are the identity layer, not datasets — and one of them is **830's "
         "own output**. `cedar_entity_freshness.csv` holds one row per "
         "register entity and lives in the directory 830 scans, so from its "
         "second run onward every entity is \"in a Cedar row\" and the "
         "number is pinned at zero permanently.",
         "",
         "| excluded here | why |", "|---|---|",
         "| `cedar_entity_freshness.csv` | 830's own output, one row per "
         "entity — the self-reference that pins the measure |",
         "| `cedar_assertions.csv` | what Cedar has claimed about an entity |",
         "| `cedar_resolved_facts.csv` | what Cedar has adjudicated |",
         "| `entity_aliases.csv` | names, one or more for every entity |",
         "",
         "Excluding the identity layer, **" + str(len(rows)) + "** register "
         "entities have no row in any of the " + str(len(scanned))
         + " substantive tables.",
         "",
         "## The " + str(len(rows)) + " entities, by class", "",
         "| entity class | with no substantive row | given a first row here |",
         "|---|---:|---:|"]
    byc = Counter(r["entity_class"] for r in rows)
    okc = Counter(r["entity_class"] for r in rows
                  if r["cedar_uid"] in closed)
    for k, v in byc.most_common():
        L.append("| %s | %d | %d |" % (k, v, okc.get(k, 0)))
    L += ["| **total** | **%d** | **%d** |" % (len(rows), len(closed)), "",
          "## What was found", "",
          "| route | rows |", "|---|---:|"]
    rc = Counter(x["route"] for v in got.values() for x in v)
    for k, v in rc.most_common():
        L.append("| %s | %d |" % (k, v))
    still = [r for r in rows if r["cedar_uid"] not in closed]
    if still:
        L += ["", "## Checked, nothing located — " + str(len(still)), "",
              "*Every one of these has a row in "
              "`register_only_first_rows.csv` naming the routes run and the "
              "date. That is a finding. It is not the same as unexamined, and "
              "the two must never be collapsed.*", "",
              "| entity | class |", "|---|---|"]
        for r in still[:60]:
            L.append("| %s | %s |" % (r.get("canonical_name", ""),
                                      r.get("entity_class", "")))
    with open(OUT_DOC, "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")


# ---------------------------------------------------------------- verify
def check(path=OUT):
    """Invariants. Empty list means clean.

    (1) every cedar_uid is in the register
    (2) an evidence row names a source AND a source_url -- provenance or it
        did not happen
    (3) an identifier is well formed for its type: EIN 9 digits, NCES school
        id 12 digits. A malformed identifier is a fabricated one.
    (4) a matched row records HOW it matched
    (5) NONE_FOUND names >= 2 routes tried -- a negative from one route is not
        a negative
    (6) checked_date on every row
    """
    bad = []
    if not os.path.exists(path):
        return ["register_only_first_rows.csv has never been written"]
    known = {r["cedar_uid"] for r in read_register() if r.get("cedar_uid")}
    with open(path, encoding="utf-8-sig", errors="replace", newline="") as fh:
        for i, r in enumerate(csv.DictReader(fh), 2):
            uid = (r.get("cedar_uid") or "").strip()
            ec = (r.get("evidence_class") or "").strip()
            ev = r.get("evidence") or ""
            if uid not in known:
                bad.append("line %d: cedar_uid %r is not in the register"
                           % (i, uid))
            if not (r.get("checked_date") or "").strip():
                bad.append("line %d: no checked_date" % i)
            if ec and ec != "NONE_FOUND":
                if not (r.get("source") or "").strip() or \
                        not (r.get("source_url") or "").strip():
                    bad.append("line %d: %s claims evidence with no source "
                               "and/or source_url" % (i, uid))
                if not (r.get("match_method") or "").strip():
                    bad.append("line %d: %s claims a match but records no "
                               "match_method" % (i, uid))
                it = (r.get("identifier_type") or "").strip()
                iv = (r.get("identifier_value") or "").strip()
                if it == "EIN" and not re.fullmatch(r"\d{2}-?\d{7}", iv):
                    bad.append("line %d: EIN %r is not 9 digits" % (i, iv))
                if it == "NCES_SCHOOL_ID" and not re.fullmatch(r"\d{12}", iv):
                    bad.append("line %d: NCES school id %r is not 12 digits"
                               % (i, iv))
            if ec == "NONE_FOUND":
                n = len([x for x in ev.split(" | ") if x.strip()])
                if "TRIED:" not in ev or n < 2:
                    bad.append("line %d: %s recorded NONE_FOUND with only %d "
                               "route(s) named" % (i, uid, n))
    return bad


def selftest():
    import tempfile
    p = os.path.join(tempfile.gettempdir(), "reg_only_selftest.csv")
    real = next(r["cedar_uid"] for r in read_register() if r.get("cedar_uid"))

    def w(row):
        with open(p, "w", encoding="utf-8", newline="") as fh:
            ww = csv.writer(fh)
            ww.writerow(COLS)
            ww.writerow([row.get(c, "") for c in COLS])

    base = {"cedar_uid": real, "canonical_name": "x", "entity_class": "y",
            "route": "IRS_990", "evidence_class": "TAX_FILER",
            "identifier_type": "EIN", "identifier_value": "12-3456789",
            "source": "s", "source_url": "https://example.org",
            "match_method": "tok", "checked_date": TODAY,
            "evidence": "TRIED: a | b"}
    cases = [
        ("unknown uid", dict(base, cedar_uid="CE-NOTREAL-00")),
        ("evidence with no source", dict(base, source="", source_url="")),
        ("match with no method", dict(base, match_method="")),
        ("malformed EIN", dict(base, identifier_value="99")),
        ("malformed NCES id", dict(base, identifier_type="NCES_SCHOOL_ID",
                                   identifier_value="12345")),
        ("thin negative", dict(base, evidence_class="NONE_FOUND",
                               identifier_type="", identifier_value="",
                               source="", source_url="", match_method="",
                               evidence="TRIED: one route")),
        ("missing checked_date", dict(base, checked_date="")),
    ]
    fails = 0
    for label, row in cases:
        w(row)
        v = check(p)
        print("    selftest %-26s -> %s"
              % (label, v[0] if v else "NOT CAUGHT"))
        if not v:
            fails += 1
    w(base)
    v = check(p)
    print("    selftest %-26s -> %s"
          % ("clean row", v[0] if v else "accepted (correct)"))
    if v:
        fails += 1
    os.remove(p)
    return 1 if fails else 0


def main():
    arg = sys.argv[1] if len(sys.argv) > 1 else ""
    if arg == "selftest":
        return selftest()
    if arg == "verify":
        bad = check()
        for b in bad[:40]:
            print("    VIOLATION  " + b)
        print("  1021 register-only verify: %d violation(s)" % len(bad))
        return 1 if bad else 0
    return run()


if __name__ == "__main__":
    sys.exit(main())
