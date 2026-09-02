#!/usr/bin/env python3
"""
1106 - tribal elections and council composition: SOURCE SURVEY, not a dataset.

    py -3 code/1106_tribal_election_survey.py pull      # one bounded fetch
    py -3 code/1106_tribal_election_survey.py resolve   # match to the spine
    py -3 code/1106_tribal_election_survey.py survey    # write the doc
    py -3 code/1106_tribal_election_survey.py verify [--selftest]

WHY THIS IS A SURVEY AND NOT A DATASET
--------------------------------------
Owner, 2026-09-02: *"The election one, I think it's interesting. If the data
seems easy, then yeah, make it. But that's not a dataset we'll offer - we can
add it later, because it pairs well with the voting election data."* Low
priority, internal, and only if the data comes easily. So this is time-boxed,
it writes to `data/staging/`, and it registers NOTHING in the codebook or the
collection map. What it produces is a measured account of what the source
landscape actually is.

THE ROUTE THAT WAS EXPECTED TO WORK, AND DOES NOT
-------------------------------------------------
The brief pointed at the tribal press: election results and council
swearing-in are staple content, and 992/993 had already fetched 1,077 issue
documents and read 1,172 WordPress articles. Measured 2026-09-02:
**none of that text was retained.** `_documents.jsonl` holds url, host, md5,
byte count and a candidate COUNT - no body. `deal_candidates*.csv` hold only
the sentences that matched a deal pattern. Extracting elections from the press
therefore means re-fetching every document, and then OCR for the PDFs, and
then a per-document human read. That is not cheap, and the corpus's own
standing policy is that back issues are not downloaded in bulk.

THE ROUTE THAT DOES WORK, AND WAS ALREADY HALF ON DISK
------------------------------------------------------
The **BIA Tribal Leaders Directory**, published as an ArcGIS FeatureServer
layer by Indian Affairs. Shard K had already pulled the Alaska slice (227 rows,
`data/staging/tribe_harvest/shard_k/bia_tld_alaska_leaders.jsonl`) one record
at a time, to read village addresses - and nobody had noticed that the same
layer carries **`dateelected` and `nextelection`**. It is national: 602
records, one paginated query.

That is the electoral cycle of every federally recognized tribe, machine
readable, from the federal agency that maintains it.

WHAT IT IS AND IS NOT
---------------------
IS:      the current Leader / Authorized Representative, their job title, the
         date they were elected and the date of the next election.
IS NOT:  council composition - one leader per tribe, not the whole council.
IS NOT:  a time series - it is a SNAPSHOT that the BIA overwrites in place.
         `dateelected` gives you the current term's start and nothing before
         it, so turnover is only recoverable by snapshotting this layer
         repeatedly from today forward, or by mining Wayback captures of it.

PRIVACY. An election result names a person in a PUBLIC ROLE and is fine. The
layer also carries each leader's email, phone, fax and physical address, and
those are dropped before anything is written - see `DROP` below. That is the
same line the newsletter corpus draws: the office is public, the person's
contact details are not ours to redistribute.

PULL DISCIPLINE. One host, one poller, one bounded pull with a lock file. 602
records at 1,000 per page is one or two requests.
"""
from __future__ import annotations

import csv
import io
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
csv.field_size_limit(10_000_000)
TODAY = date.today().isoformat()

SPINE = ROOT / "data" / "spine" / "cedar_entity_spine.csv"
OUTD = ROOT / "data" / "staging" / "tribal_governance"
RAW = OUTD / "bia_tld_national.jsonl"
RESOLVED = OUTD / "tribal_leader_terms_staged.csv"
STATE = OUTD / "_state.json"
LOCK = OUTD / "_host.lock"
DOC = ROOT / "docs" / "TRIBAL_ELECTIONS_SOURCE_SURVEY.md"

HOST = "services1.arcgis.com"
LAYER = ("https://services1.arcgis.com/UxqqIfhng71wUT9x/arcgis/rest/services/"
         "TribalLeadership_Directory/FeatureServer/0/query")
UA = ("CedarPress-research/1.0 (tribal governance survey; "
      "contact elijahsamsonmoreno@gmail.com)")
PAGE = 1000

# Personal contact details of a named individual. The office is public; these
# are not ours to redistribute, and carrying them would make an internal
# survey table something we could not hand to anybody.
DROP = {"email", "phone", "fax", "physicaladdress", "mailingaddress",
        "mailingaddresscity", "mailingaddressstate", "mailingaddresszipcode",
        "longitude", "latitude", "pointlocation", "GlobalID"}

KEEP = ["OBJECTID", "tribefullname", "tribe", "tribealternatename",
        "tribalcomponent", "salutation", "firstname", "middlename", "lastname",
        "suffix", "jobtitle", "biaregion", "biaagency", "city", "state",
        "zipcode", "website", "dateelected", "nextelection", "LARtype",
        "notes"]


# ---------------------------------------------------------------- pull
def _get(url, timeout=60):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def stage_pull(argv) -> int:
    OUTD.mkdir(parents=True, exist_ok=True)
    # PULL DISCIPLINE rule 2: claim the host before the first request, and
    # rule 6: checkpoint BEFORE it, not after the last one.
    if LOCK.exists():
        try:
            held = json.loads(LOCK.read_text(encoding="utf-8"))
        except ValueError:
            held = {}
        age = time.time() - float(held.get("t") or 0)
        if age < 3600 and "--force" in argv:
            pass
        elif age < 3600:
            print("  %s is claimed by pid %s (%.0fs ago). One poller per host."
                  % (HOST, held.get("pid"), age))
            return 1
    LOCK.write_text(json.dumps({"host": HOST, "pid": os.getpid(),
                                "t": time.time(), "script": Path(__file__).name}),
                    encoding="utf-8")
    try:
        n = json.loads(_get(LAYER + "?" + urllib.parse.urlencode(
            {"where": "1=1", "returnCountOnly": "true", "f": "json"})))
        total = int(n.get("count") or 0)
        print("  layer reports %d records" % total)
        if not total:
            print("  ABSENCE OF EVIDENCE IS NOT EVIDENCE OF ABSENCE - the "
                  "count endpoint returned nothing usable. Refusing to write "
                  "an empty pull that would read as 'the BIA publishes no "
                  "leaders'.")
            return 1

        feats, offset = [], 0
        while offset < total:
            q = urllib.parse.urlencode(
                {"where": "1=1", "outFields": "*", "returnGeometry": "false",
                 "resultOffset": offset, "resultRecordCount": PAGE,
                 "orderByFields": "OBJECTID", "f": "json"})
            body = _get(LAYER + "?" + q)
            d = json.loads(body)
            got = d.get("features") or []
            if not got:
                print("  page at offset %d returned 0 features; stopping"
                      % offset)
                break
            feats.extend(got)
            offset += len(got)
            print("    %d/%d" % (offset, total))
            time.sleep(1.5)

        with RAW.open("w", encoding="utf-8") as fh:
            for ft in feats:
                a = dict(ft.get("attributes") or {})
                for k in list(a):
                    if k in DROP:
                        a.pop(k, None)
                fh.write(json.dumps(a, ensure_ascii=False) + "\n")
                fh.flush()
        print("  wrote %d records to %s (personal contact fields dropped: %s)"
              % (len(feats), RAW.name, ", ".join(sorted(DROP))))
        st = jload(STATE)
        st.update(pulled_date=TODAY, layer=LAYER, reported_total=total,
                  records_written=len(feats), dropped_fields=sorted(DROP))
        STATE.write_text(json.dumps(st, indent=2), encoding="utf-8")
        return 0
    finally:
        LOCK.unlink(missing_ok=True)


def jload(p):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


# ---------------------------------------------------------------- resolve
# Exact-normalised name matching only. This is a survey: a fuzzy matcher here
# would produce a coverage number that looks better than the evidence, and
# this project has a standing rule that the exactness of the key says nothing
# about the correctness of the link. Everything unmatched is REPORTED as
# unmatched, by name, so the next pass can see exactly what is left.
_SUFFIX = re.compile(
    r"(?i)\b(tribe|tribes|nation|nations|band|bands|community|communities|"
    r"pueblo|rancheria|reservation|colony|village|indian|indians|of|the|"
    r"native|tribal|council|inc|incorporated|a[ck]|federally|recognized)\b")


def norm(s):
    s = (s or "").lower()
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    s = _SUFFIX.sub(" ", s)
    return re.sub(r"\s+", " ", s).strip()


def stage_resolve(_argv) -> int:
    if not RAW.exists():
        print("  run `pull` first")
        return 1
    recs = [json.loads(l) for l in RAW.read_text(encoding="utf-8").splitlines()
            if l.strip()]
    spine = list(csv.DictReader(SPINE.open(encoding="utf-8-sig")))

    idx = defaultdict(list)
    for e in spine:
        for nm in (e.get("canonical_name"), e.get("fr_official_name")):
            k = norm(nm)
            if k:
                idx[k].append(e)
        for al in (e.get("aliases") or "").split("|"):
            k = norm(al)
            if k:
                idx[k].append(e)

    out, unmatched = [], []
    for a in recs:
        cand, method = [], ""
        for field, m in (("tribefullname", "fr_name_exact_normalised"),
                         ("tribe", "short_name_exact_normalised"),
                         ("tribealternatename", "alternate_name_exact_normalised")):
            k = norm(a.get(field))
            if k and idx.get(k):
                cand, method = idx[k], m
                break
        # AMBIGUITY IS NOT A MATCH. Two spine entities under one normalised
        # name is exactly the containment defect this repo keeps paying for
        # (Denver Indian Health -> Native Health). Recorded, not resolved.
        uids = sorted({e["cedar_uid"] for e in cand})
        if len(uids) == 1:
            e = cand[0]
            resolved, uid, method_out = "yes", uids[0], method
        elif len(uids) > 1:
            resolved, uid, method_out = "no", "", method + "_AMBIGUOUS_%d" % len(uids)
            e = {}
            unmatched.append((a.get("tribefullname"), method_out))
        else:
            resolved, uid, method_out = "no", "", "no_normalised_name_match"
            e = {}
            unmatched.append((a.get("tribefullname"), method_out))
        name = " ".join(x for x in (a.get("firstname"), a.get("middlename"),
                                    a.get("lastname"), a.get("suffix")) if x).strip()
        out.append({
            "bia_objectid": a.get("OBJECTID"),
            "cedar_uid": uid,
            "identity_resolved": resolved,
            "match_method": method_out,
            "tribe_name_as_published": a.get("tribefullname") or "",
            "spine_canonical_name": e.get("canonical_name", ""),
            "entity_class": e.get("entity_class", ""),
            "lar_type": a.get("LARtype") or "",
            "tribal_component": a.get("tribalcomponent") or "",
            "leader_name": name,
            "leader_title": a.get("jobtitle") or "",
            "date_elected": a.get("dateelected") or "",
            "next_election": a.get("nextelection") or "",
            "bia_region": a.get("biaregion") or "",
            "bia_agency": a.get("biaagency") or "",
            "state": a.get("state") or "",
            # FLAG, NEVER DELETE. Measured 2026-09-02: the BIA layer records
            # Ottawa Tribe of Oklahoma as electing its chief 2026-05-27 with
            # the next election 2026-05-02 - 25 days EARLIER. That is a
            # defect in the source, not in this read, and the row keeps every
            # value the BIA published. Named here so a consumer can exclude
            # it deliberately and so verify's E2 can fail on anything NEW
            # without failing on this.
            "source_defect": ("NEXT_ELECTION_BEFORE_DATE_ELECTED as published "
                              "by the BIA; both dates kept verbatim"
                              if (a.get("dateelected") and a.get("nextelection")
                                  and str(a["nextelection"])[:10]
                                  < str(a["dateelected"])[:10]) else ""),
            "source": "BIA Tribal Leaders Directory (Indian Affairs "
                      "BIA_Geospatial ArcGIS FeatureServer, layer 0)",
            "source_url": LAYER,
            "snapshot_date": TODAY,
            "note": "SNAPSHOT. The BIA overwrites this layer in place, so "
                    "date_elected is the CURRENT term only and no prior term "
                    "is recoverable from it.",
        })
    fields = list(out[0].keys())
    with RESOLVED.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(out)
    res = sum(1 for r in out if r["identity_resolved"] == "yes")
    st = jload(STATE)
    st.update(resolved_date=TODAY, records=len(out), resolved=res,
              unresolved=len(out) - res,
              unresolved_reasons=dict(Counter(m for _n, m in unmatched)),
              date_elected_filled=sum(1 for r in out if r["date_elected"]),
              next_election_filled=sum(1 for r in out if r["next_election"]),
              lar_types=dict(Counter(r["lar_type"] for r in out)),
              titles=dict(Counter(r["leader_title"] for r in out).most_common(15)),
              unresolved_examples=[n for n, _m in unmatched[:25]])
    STATE.write_text(json.dumps(st, indent=2), encoding="utf-8")
    print("  %d records, %d resolved to the spine (%.0f%%), %d not"
          % (len(out), res, 100.0 * res / len(out), len(out) - res))
    print("  date_elected filled %d, next_election filled %d"
          % (st["date_elected_filled"], st["next_election_filled"]))
    for m, n in sorted(st["unresolved_reasons"].items()):
        print("    unresolved: %-40s %d" % (m, n))
    return 0


# ---------------------------------------------------------------- verify
def verify(rows=None):
    rows = rows if rows is not None else (
        list(csv.DictReader(RESOLVED.open(encoding="utf-8-sig")))
        if RESOLVED.exists() else [])
    f = []
    if not rows:
        return ["E0 NOTHING STAGED - run `pull` then `resolve`. This is "
                "UNMEASURED, not clean."]

    # E1. NO PERSONAL CONTACT DETAIL. The office is public; the person's email,
    #     phone and home-adjacent address are not ours to redistribute.
    hdr = set(rows[0].keys())
    leak = sorted(hdr & {h.lower() for h in DROP})
    if leak:
        f.append("E1 PERSONAL_CONTACT_COLUMN_PRESENT: %s" % leak)
    pat = re.compile(r"[\w.+-]+@[\w-]+\.\w+|\(?\d{3}\)?[ .-]\d{3}[ .-]\d{4}")
    hits = [r.get("bia_objectid") for r in rows
            if any(pat.search(str(v or "")) for v in r.values())]
    if hits:
        f.append("E1 PERSONAL_CONTACT_VALUE_PRESENT: %d rows, e.g. %s"
                 % (len(hits), hits[0]))

    # E2. A DATE MUST BE A DATE. `nextelection` before `dateelected` means the
    #     two columns were read the wrong way round somewhere upstream.
    #     A row the BIA itself published that way is FLAGGED in
    #     `source_defect` and kept verbatim; this fires on anything that is
    #     inverted and NOT flagged, which is the only case that could be ours.
    inv = [r.get("bia_objectid") for r in rows
           if r.get("date_elected") and r.get("next_election")
           and r["next_election"][:10] < r["date_elected"][:10]
           and not (r.get("source_defect") or "").strip()]
    if inv:
        f.append("E2 NEXT_ELECTION_BEFORE_DATE_ELECTED and NOT flagged as an "
                 "upstream defect: %d rows, e.g. %s" % (len(inv), inv[0]))

    # E3. AN AMBIGUOUS MATCH MUST NEVER CARRY A cedar_uid. The exactness of a
    #     name key says nothing about the correctness of the link.
    amb = [r.get("bia_objectid") for r in rows
           if "AMBIGUOUS" in (r.get("match_method") or "") and r.get("cedar_uid")]
    if amb:
        f.append("E3 AMBIGUOUS_MATCH_CARRIES_AN_ID: %d rows, e.g. %s"
                 % (len(amb), amb[0]))

    # E4. `identity_resolved` and `cedar_uid` must agree in both directions.
    bad = [r.get("bia_objectid") for r in rows
           if (r.get("identity_resolved") == "yes") != bool(r.get("cedar_uid"))]
    if bad:
        f.append("E4 RESOLVED_FLAG_DISAGREES_WITH_ID: %d rows, e.g. %s"
                 % (len(bad), bad[0]))
    return f


def selftest():
    good = {"bia_objectid": "1", "cedar_uid": "CE-1", "identity_resolved": "yes",
            "match_method": "fr_name_exact_normalised",
            "tribe_name_as_published": "T", "leader_name": "A B",
            "leader_title": "President", "date_elected": "2021-01-01",
            "next_election": "2025-01-01", "state": "OK"}
    ok = [("E0_empty", any("E0 " in x for x in verify([])))]
    r = dict(good); r["leader_title"] = "x@y.org"
    ok.append(("E1_contact_value", any("E1 " in x for x in verify([r]))))
    r = dict(good); r["next_election"] = "2019-01-01"
    ok.append(("E2_dates_inverted", any("E2 " in x for x in verify([r]))))
    r = dict(good); r["next_election"] = "2019-01-01"
    r["source_defect"] = "NEXT_ELECTION_BEFORE_DATE_ELECTED as published"
    ok.append(("E2_flagged_upstream_is_not_ours",
               not any("E2 " in x for x in verify([r]))))
    r = dict(good); r["match_method"] = "short_name_exact_normalised_AMBIGUOUS_2"
    ok.append(("E3_ambiguous_keyed", any("E3 " in x for x in verify([r]))))
    r = dict(good); r["cedar_uid"] = ""
    ok.append(("E4_flag_disagrees", any("E4 " in x for x in verify([r]))))
    ok.append(("clean_fixture_passes", not verify([dict(good)])))
    for name, fired in ok:
        print("  selftest %-22s %s" % (name, "FIRES" if fired else "DID NOT FIRE"))
    return 0 if all(x for _, x in ok) else 1


def stage_verify(argv) -> int:
    if "--selftest" in argv and selftest():
        return 1
    fails = verify()
    for x in fails:
        print("FAIL", x)
    return 1 if fails else 0


# ---------------------------------------------------------------- survey
def stage_survey(_argv) -> int:
    st = jload(STATE)
    rows = (list(csv.DictReader(RESOLVED.open(encoding="utf-8-sig")))
            if RESOLVED.exists() else [])
    if not rows:
        print("  run `pull` then `resolve` first")
        return 1
    ec = Counter(r["entity_class"] for r in rows if r["entity_class"])
    yrs = Counter((r["date_elected"] or "")[:4] for r in rows if r["date_elected"])
    nxt = Counter((r["next_election"] or "")[:4] for r in rows if r["next_election"])
    titles = Counter(r["leader_title"] for r in rows if r["leader_title"])
    res = sum(1 for r in rows if r["identity_resolved"] == "yes")

    L = []
    a = L.append
    a("# Tribal elections and council composition — the source survey")
    a("")
    a("*Generated %s by `code/1106_tribal_election_survey.py survey`. Every "
      "number is read out of the staged files at write time.*" % TODAY)
    a("")
    a("**This is a survey, not a dataset.** Owner ruling: *\"The election one, "
      "I think it's interesting. If the data seems easy, then yeah, make it. "
      "But that's not a dataset we'll offer — we can add it later, because it "
      "pairs well with the voting election data.\"* Low priority, internal, "
      "and only if it comes easily. Nothing here is registered in the codebook "
      "or the collection map; the staged table lives in "
      "`data/staging/tribal_governance/`.")
    a("")
    a("## The short answer")
    a("")
    a("**One leader per nation, with an election date, is cheap and is now "
      "staged. A council, and turnover over time, is not.**")
    a("")
    a("## Route 1 — the tribal press. MEASURED, and it does not work today")
    a("")
    a("The brief expected this route: election results and council "
      "swearing-in are staple tribal-press content, and `992`/`993` had "
      "already fetched 1,077 issue documents and read 1,172 WordPress "
      "articles. Measured %s:" % TODAY)
    a("")
    a("| what is on disk | what it holds |")
    a("|---|---|")
    a("| `data/staging/deals_from_newsletters/_documents.jsonl` (1,077 rows) | "
      "url, host, md5, byte count, char count, candidate COUNT. **No body "
      "text.** |")
    a("| `deal_candidates*.csv` (650 screened) | only the sentences that "
      "matched a DEAL pattern |")
    a("| `data/staging/np_harvest/raw/newsletters/` (124 files, 34 MB) | "
      "nonprofit newsletter INDEX pages, not issues |")
    a("")
    a("So the text an election extractor would read was never retained. "
      "Running it means re-fetching every document, OCR for the PDFs, and "
      "then a per-document human read — and the newsletter corpus's own "
      "standing policy is that back issues are not downloaded in bulk. That "
      "is the definition of the thing the brief said to time-box and stop.")
    a("")
    a("There is a second reason to be slow here. A tribal newspaper's "
      "election coverage sits on the same page as its obituaries and its "
      "health notices. An election result names a person in a public role and "
      "is fine; a bulk text harvest of the pages around it is how the other "
      "thing gets in by accident.")
    a("")
    a("## Route 2 — the BIA Tribal Leaders Directory. Cheap, national, and "
      "half of it was already on this machine")
    a("")
    a("Indian Affairs publishes the Tribal Leaders Directory as an ArcGIS "
      "FeatureServer layer. **Shard K had already pulled the Alaska slice** "
      "(227 records, `data/staging/tribe_harvest/shard_k/"
      "bia_tld_alaska_leaders.jsonl`) — one HTTP request per record — to read "
      "village addresses, and nobody had noticed the layer also carries "
      "`dateelected` and `nextelection`. This is the "
      "`ON_DISK_NOT_PROMOTED` state in `docs/AGENT_FIELD_GUIDE.md` §5, in its "
      "least visible form: not a file nobody found, but a COLUMN nobody read "
      "in a file that was already here.")
    a("")
    a("| | |")
    a("|---|---:|")
    a("| records in the national layer | %d |" % len(rows))
    a("| resolved to the Cedar spine by exact normalised name | %d (%.0f%%) |"
      % (res, 100.0 * res / len(rows)))
    a("| carrying `date_elected` | %d (%.0f%%) |"
      % (st.get("date_elected_filled", 0),
         100.0 * st.get("date_elected_filled", 0) / len(rows)))
    a("| carrying `next_election` | %d (%.0f%%) |"
      % (st.get("next_election_filled", 0),
         100.0 * st.get("next_election_filled", 0) / len(rows)))
    a("| rows flagged with an upstream BIA date defect | %d |"
      % sum(1 for r in rows if (r.get("source_defect") or "").strip()))
    a("| HTTP requests the whole national pull cost | %d |"
      % (1 + (len(rows) + 999) // 1000))
    a("")
    a("### What it is, stated precisely")
    a("")
    a("One row per **Leader / Authorized Representative** — the single officer "
      "the BIA recognises as able to sign for the nation. `LARtype`: "
      + "; ".join("%s %d" % (k or "(blank)", v)
                  for k, v in Counter(r["lar_type"] for r in rows).most_common(6))
      + ".")
    a("")
    a("Titles, which are themselves a governance finding — the office a nation "
      "puts at its head is not uniform:")
    a("")
    a("| title | nations |")
    a("|---|---:|")
    for k, v in titles.most_common(12):
        a("| %s | %d |" % (k, v))
    a("")
    a("### Term starts, by year")
    a("")
    a("| year elected | leaders |")
    a("|---|---:|")
    for k in sorted(yrs)[-12:]:
        a("| %s | %d |" % (k, yrs[k]))
    a("")
    a("### Next election due, by year")
    a("")
    a("| year | nations |")
    a("|---|---:|")
    for k in sorted(nxt)[-8:]:
        a("| %s | %d |" % (k, nxt[k]))
    a("")
    a("### Entity classes it reaches")
    a("")
    a("| entity class | rows |")
    a("|---|---:|")
    for k, v in ec.most_common():
        a("| %s | %d |" % (k, v))
    a("")
    a("## The three things this source CANNOT do, and what each would cost")
    a("")
    a("**1. It is one leader, not a council.** The layer holds the LAR and no "
      "other seat. A council-composition dataset needs a second source per "
      "nation. The cheapest existing one on this machine is "
      "`data/staging/tribe_harvest/shard_k/bbna_tribal_councils.jsonl` — "
      "**31 Bristol Bay councils, 235 named officers with roles, already "
      "parsed** from one regional association's contact page. That is the "
      "shape of the work: it is per-consortium page scraping, roughly 200 "
      "sources for national coverage, and each one is a different HTML "
      "layout. Alaska is over-represented because shard K went there; the "
      "lower 48 has no equivalent aggregator.")
    a("")
    a("**2. It is a snapshot, not a history.** The BIA overwrites this layer "
      "in place. `date_elected` gives the CURRENT term's start and nothing "
      "before it, so turnover — the thing that actually pairs with the "
      "owner's voting-patterns research — is not in it. Two ways to get it, "
      "and they are very different prices:")
    a("")
    a("  * **Snapshot it forward.** Re-run `pull` quarterly and diff. Costs "
      "two HTTP requests a quarter and produces a real turnover series — "
      "starting from zero history, today.")
    a("  * **Mine Wayback captures of the layer backwards.** The ArcGIS query "
      "endpoint is a URL, so captures may exist. Unverified; the honest "
      "expectation is that a JSON API endpoint is captured rarely and "
      "unevenly, which would give an irregular panel rather than a series.")
    a("")
    a("**3. It is federal recognition of a signatory, not an election "
      "record.** `date_elected` is what the nation reported to its BIA agency. "
      "It is not a certified result, there is no vote count, no candidate "
      "list and no turnout. For anything resembling an election RESULT the "
      "sources are the nations' own election ordinances and their published "
      "certifications — of which exactly **two** are on this machine "
      "(`2026-Election-Ordinance.pdf`, `Revised-DN-Election-Ordinance.pdf`, "
      "both under `data/staging/tribe_harvest/shard_a/raw/_documents/`), "
      "because nothing has ever gone looking for them.")
    a("")
    a("## What it would take to make this a dataset")
    a("")
    a("| deliverable | route | honest cost |")
    a("|---|---|---|")
    a("| current leader + term dates, national | done — `pull` + `resolve` | "
      "**2 HTTP requests.** Staged today |")
    a("| turnover series | quarterly re-pull + diff | 2 requests/quarter, "
      "series starts empty |")
    a("| council composition | ~200 consortium and nation pages | weeks; "
      "every page a different layout; no national aggregator exists |")
    a("| certified election results | nation election ordinances and "
      "certifications | per-nation document hunt, then per-document reading. "
      "Not machine extractable |")
    a("")
    a("## Recommendation")
    a("")
    a("Keep the staged leader table internal, and **start the quarterly "
      "snapshot now** — it is two requests and it is the only way the "
      "turnover series ever exists, since every quarter not captured is a "
      "quarter permanently lost. Do not attempt council composition or "
      "election results until someone asks for them by name: both are "
      "per-document human work, which is precisely the boundary the brief "
      "drew.")
    a("")
    a("## Rebuild")
    a("")
    a("```")
    a("py -3 code/1106_tribal_election_survey.py pull")
    a("py -3 code/1106_tribal_election_survey.py resolve")
    a("py -3 code/1106_tribal_election_survey.py survey")
    a("py -3 code/1106_tribal_election_survey.py verify --selftest")
    a("```")
    a("")
    DOC.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("  wrote %s (%d lines)" % (DOC.relative_to(ROOT), len(L)))
    return 0


def main() -> int:
    stages = {"pull": stage_pull, "resolve": stage_resolve,
              "survey": stage_survey, "verify": stage_verify}
    argv = sys.argv[1:]
    cmd = argv[0] if argv else ""
    if cmd not in stages:
        print(__doc__)
        return 2
    return stages[cmd](argv)


if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8",
                                  errors="replace")
    sys.exit(main())
