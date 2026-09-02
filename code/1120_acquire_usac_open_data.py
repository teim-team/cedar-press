#!/usr/bin/env python3
"""
1120 - acquire USAC open data: the E-Rate `tribal_type` slice and the Rural
Health Care commitments.

    py -3 code/1120_acquire_usac_open_data.py probe
    py -3 code/1120_acquire_usac_open_data.py pull [--refetch]
    py -3 code/1120_acquire_usac_open_data.py build
    py -3 code/1120_acquire_usac_open_data.py verify     # exits 1 on breach
    py -3 code/1120_acquire_usac_open_data.py selftest   # proves verify FIRES

WHY THIS SOURCE, IN ONE SENTENCE
--------------------------------
`docs/PULL_DISCIPLINE.md`'s selection doctrine measured that **an
identifier-seeded pull can never discover an entity Cedar does not already
know** - roughly three quarters of the entity universe is invisible to one -
and `tribal_type` on the E-Rate file is a **TYPE FILTER leg**: the publisher
did the Native identification, on 53,847 rows, for free.

===========================================================================
SELECTION DECLARATION  (PULL_DISCIPLINE, "THE RULE")
===========================================================================
  usac_erate_tribal_commitments.csv
      leg USED     : TYPE_FILTER  - `tribal_type IS NOT NULL`, the
                     publisher's own categorisation on the FCC Form 471
                     recipient-of-service record.
      leg MISSING  : KNOWN_IDENTIFIER. USAC publishes no UEI, EIN or CAGE, so
                     there is nothing for Cedar's ledger to seed on. A tribal
                     school that never self-identified on Form 471 is
                     invisible to this pull and no identifier leg can rescue
                     it here.
      population_basis on every row: `TYPE_FILTER`
      value        : `TYPE_FILTER_PUBLISHER_ASSIGNED`

  usac_rhc_hcp_directory.csv / usac_rhc_native_candidate_lines.csv
      leg USED     : NAME_TOKEN_SWEEP.
      leg MISSING  : both the others. **RHC HAS NO TRIBAL TYPE FIELD** - this
                     is a CORRECTION to `docs/SOURCE_EXPLORATION_2026-09-02.md`
                     §1.3, which lists RHC beside the E-Rate file as though
                     the two shared a flag. Measured 2026-09-02: the only
                     categorical is `filing_hcp_entity_type`, whose twelve
                     values are 'Rural Health Clinic', 'Not-For-Profit
                     Hospital', 'Consortium Of The Above' and so on. **None
                     of them is tribal.**
      population_basis on every row: `NAME_TOKEN_SWEEP`
      **EVERY RHC ROW IS A CANDIDATE, NOT AN ATTRIBUTION.** A name token is
      not a determination. "Boys & Girls Clubs of Wichita Falls" is not the
      Wichita Tribe, and this file carries the same hazard - so the sweep
      writes tier C, inherits nothing, and attributes nothing. A tier is
      inherited from the source row, never assigned by the consumer.
===========================================================================

WHAT IT WRITES
--------------
  data/clean/usac_erate_tribal_commitments.csv    53,847
      one row per (Form 471 line item x recipient of service) that USAC
      flagged with a `tribal_type`. **NOT one row per school**: one school
      appears once per funded line item per funding year. Deduplicate on
      `ros_entity_number` before counting schools; the entity roster below
      is that count, done once.
  data/clean/usac_erate_tribal_entities.csv       ~1,900
      one row per distinct `ros_entity_number` in the file above, with the
      years it appears in and its most recent address. THIS is the entity
      grain; the file above is the money grain.
  data/clean/usac_rhc_hcp_directory.csv           ~10,000
      one row per distinct filing health care provider, from `$group`. The
      discovery surface, taken whole so the Native subset has a denominator.
  data/clean/usac_rhc_native_candidate_lines.csv  ~6,500
      commitment lines whose HCP name carries a Native token. CANDIDATES.

TERMS
-----
`https://opendata.usac.org/api/views/<id>.json` -> `license.name` is
**"Public Domain"** (`licenseId: PUBLIC_DOMAIN`), `attribution` is
"Universal Service Administrative Company". robots.txt disallows only
faceted `/browse?*` query strings and sets `Crawl-delay: 1`; the `/resource/`
SODA path carries no directive. This script sleeps 1.5s, which honours it.
The verbatim robots body and the licence object are both stored in the run
manifest, so the permission is auditable without re-fetching.
"""
from __future__ import annotations

import csv
import importlib.util
import json
import sys
import urllib.parse
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

_spec = importlib.util.spec_from_file_location("cedar_arcgis", HERE / "cedar_arcgis.py")
ag = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ag)                                       # type: ignore

SCRIPT = "1120_acquire_usac_open_data"
HOST = "opendata.usac.org"
RAW = ROOT / "data" / "raw" / "external" / "usac"
CLEAN = ROOT / "data" / "clean"
LOG = ROOT / "logs" / f"{SCRIPT}.jsonl"
MANIFEST = RAW / "_manifest.json"

ERATE = "avi8-svp9"          # E-Rate Recipient Details And Commitments
RHC = "2kme-evqq"            # Rural Health Care Commitments and Disbursements

PAGE = 25_000                # SODA serves up to 50k; 25k keeps a page < ~30 MB
PAUSE_S = 1.5                # robots says Crawl-delay: 1

# Tokens for the RHC name sweep. Deliberately NARROW: every one of these is a
# term a health care provider would only carry if it were Native-serving, and
# even so every hit is a CANDIDATE. Tokens known to produce place-name false
# positives on their own ("nation", "band", "eagle", "chief") are excluded -
# `docs/AGENT_FIELD_GUIDE.md` and the NAME_TRAPS lesson: a place suffix makes
# a tribe name a place.
RHC_TOKENS = ["tribal", "tribe", "indian health", "indian hospital",
              "native american", "alaska native", "native hawaiian",
              "pueblo", "navajo", "cherokee nation", "choctaw nation",
              "chickasaw nation", "muscogee", "ihs ", "i.h.s."]


def soda_url(res: str, params: dict) -> str:
    return f"https://{HOST}/resource/{res}.json?" + urllib.parse.urlencode(params)


def meta_url(res: str) -> str:
    return f"https://{HOST}/api/views/{res}.json"


def _load_manifest() -> dict:
    if MANIFEST.exists():
        return json.loads(MANIFEST.read_text(encoding="utf-8"))
    return {"host": HOST, "script": SCRIPT, "assets": {}}


def _save_manifest(m: dict) -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    m["written_at"] = datetime.now(timezone.utc).isoformat()
    MANIFEST.write_text(json.dumps(m, indent=2), encoding="utf-8")


def soda_count(sess, res: str, where: str | None = None) -> int:
    p = {"$select": "count(*)"}
    if where:
        p["$where"] = where
    d = sess.get(soda_url(res, p))["json"]
    return int(d[0]["count"])


def soda_page_all(sess, res: str, where: str | None, order: str,
                  advertised: int, label: str) -> tuple[list[dict], list[str]]:
    """$offset paging with a stable $order, hashed per page, then reconciled."""
    rows: list[dict] = []
    shas: list[str] = []
    seen: set[str] = set()
    off = 0
    while True:
        p = {"$limit": PAGE, "$offset": off, "$order": order}
        if where:
            p["$where"] = where
        r = sess.get(soda_url(res, p))
        got = r["json"]
        if not got:
            break
        if r["sha256"] in seen:
            raise RuntimeError(
                f"{label}: page at $offset={off} is byte-identical to an "
                "earlier page - the server is ignoring $offset. Stopping.")
        seen.add(r["sha256"])
        shas.append(r["sha256"])
        rows.extend(got)
        print(f"      {label}: {len(rows):,}/{advertised:,}", flush=True)
        if len(got) < PAGE:
            break
        off += len(got)
        if len(shas) > 2000:
            raise RuntimeError("page ceiling hit; refusing to loop")
    return rows, shas


def _rhc_where() -> str:
    parts = [f"upper(filing_hcp_name) like upper('%{t}%')" for t in RHC_TOKENS]
    parts += [f"upper(participating_hcp_name) like upper('%{t}%')" for t in RHC_TOKENS]
    return " OR ".join(parts)


# ---------------------------------------------------------------------------

def cmd_probe() -> int:
    sess = ag.Session(SCRIPT, LOG, pause_s=PAUSE_S)
    p = ag.robots_posture(soda_url(ERATE, {"$limit": 1}))
    print(f"robots  status={p['robots_status']} served={p['robots_served']} "
          f"verdict={p['verdict']}  (naive-our-UA: {p['naive_our_ua_verdict']})")
    if p["verdict"] != "ALLOWED":
        return 1
    for res, name in ((ERATE, "E-Rate"), (RHC, "RHC")):
        m = sess.get(meta_url(res))["json"]
        n = soda_count(sess, res)
        print(f"{name:<8} {n:>10,} rows   licence={m.get('license', {}).get('name')!r}"
              f"   attribution={m.get('attribution')!r}")
    d = sess.get(soda_url(ERATE, {"$select": "tribal_type, count(*)",
                                  "$group": "tribal_type"}))["json"]
    tot = 0
    for r in d:
        if r.get("tribal_type"):
            tot += int(r["count"])
            print(f"   tribal_type {r['tribal_type']!r:<58} {int(r['count']):>7,}")
    print(f"   {'TOTAL carrying a tribal_type':<70} {tot:>7,}")
    n = soda_count(sess, RHC, _rhc_where())
    print(f"RHC name-token sweep matches: {n:,}  "
          "(CANDIDATES - RHC publishes no tribal type)")
    return 0


def cmd_pull(refetch: bool = False) -> int:
    RAW.mkdir(parents=True, exist_ok=True)
    posture = ag.require_allowed(soda_url(ERATE, {"$limit": 1}))
    lock = ag.claim_host(HOST, SCRIPT, queue=[ERATE, RHC])
    sess = ag.Session(SCRIPT, LOG, pause_s=PAUSE_S, deadline_s=3 * 3600)
    man = _load_manifest()
    man["robots"] = posture
    downloaded, skipped, refused = 0, 0, []

    jobs = [
        {"key": "erate_tribal", "res": ERATE,
         "where": "tribal_type IS NOT NULL",
         "order": "ros_entity_number, funding_year, funding_request_number, "
                  "form_471_line_item_number",
         "population_basis": "TYPE_FILTER"},
        {"key": "rhc_hcp_directory", "res": RHC, "group": True,
         "population_basis": "FULL_UNIVERSE_ROSTER"},
        {"key": "rhc_native_candidates", "res": RHC,
         "where": _rhc_where(),
         "order": "funding_year, funding_request_number, frn_line_number",
         "population_basis": "NAME_TOKEN_SWEEP"},
    ]
    try:
        for j in jobs:
            out = RAW / f"{j['key']}.json"
            m = sess.get(meta_url(j["res"]))["json"]
            licence = m.get("license", {})
            if j.get("group"):
                # The distinct-provider roster, taken with $group so the
                # denominator is measured rather than derived from a slice.
                advertised = None
                sel = ("filing_hcp, filing_hcp_name, filing_hcp_entity_type, "
                       "filing_hcp_city, filing_hcp_state, filing_hcp_county, "
                       "filing_hcp_zip_code, count(*) as line_rows, "
                       "min(funding_year) as first_year, "
                       "max(funding_year) as last_year")
                grp = ("filing_hcp, filing_hcp_name, filing_hcp_entity_type, "
                       "filing_hcp_city, filing_hcp_state, filing_hcp_county, "
                       "filing_hcp_zip_code")
                rows, shas, off = [], [], 0
                seen = set()
                while True:
                    r = sess.get(soda_url(j["res"], {
                        "$select": sel, "$group": grp, "$order": "filing_hcp",
                        "$limit": PAGE, "$offset": off}))
                    got = r["json"]
                    if not got:
                        break
                    if r["sha256"] in seen:
                        raise RuntimeError("repeated page body on the $group roster")
                    seen.add(r["sha256"])
                    shas.append(r["sha256"])
                    rows.extend(got)
                    print(f"      {j['key']}: {len(rows):,}", flush=True)
                    if len(got) < PAGE:
                        break
                    off += len(got)
                advertised = len(rows)
            else:
                advertised = soda_count(sess, j["res"], j.get("where"))
                prior = man["assets"].get(j["key"], {})
                if out.exists() and not refetch and prior.get("rows") == advertised:
                    print(f"SKIP  {j['key']:<26} {advertised:>9,} already on disk")
                    skipped += 1
                    continue
                rows, shas = soda_page_all(sess, j["res"], j.get("where"),
                                           j["order"], advertised, j["key"])
                after = soda_count(sess, j["res"], j.get("where"))
                ag.reconcile(len(rows), after, j["key"])
                advertised = after

            payload = {
                "asset_id": j["res"], "key": j["key"],
                "where": j.get("where", ""), "grouped": bool(j.get("group")),
                "population_basis": j["population_basis"],
                "licence_verbatim": licence,
                "attribution_verbatim": m.get("attribution"),
                "rows_updated_at_epoch": m.get("rowsUpdatedAt"),
                "rows_updated_at_iso": (
                    datetime.fromtimestamp(m["rowsUpdatedAt"], tz=timezone.utc).isoformat()
                    if m.get("rowsUpdatedAt") else ""),
                "rows": len(rows), "advertised": advertised,
                "page_sha256": shas, "distinct_page_sha256": len(set(shas)),
                "retrieved_at": datetime.now(timezone.utc).isoformat(),
                "records": rows,
            }
            tmp = out.with_suffix(".json.part")
            tmp.write_text(json.dumps(payload), encoding="utf-8")
            tmp.replace(out)
            man["assets"][j["key"]] = {k: v for k, v in payload.items()
                                       if k != "records"}
            man["assets"][j["key"]]["file"] = str(
                out.relative_to(ROOT)).replace("\\", "/")
            _save_manifest(man)
            downloaded += 1
            print(f"PULL  {j['key']:<26} {len(rows):>9,} rows, {len(shas)} pages, "
                  f"{len(set(shas))} distinct hashes  RECONCILED")
    except ag.EdgeBlocked as e:
        refused.append(str(e))
        print(f"EDGE BLOCK - stopping the run.\n  {e}")
        return 2
    finally:
        _save_manifest(man)
        ag.release_host(lock, downloaded_this_run=downloaded,
                        already_on_disk_skipped=skipped, refused_by_host=refused,
                        requests_made=sess.n_requests, bytes_read=sess.bytes_read)
    print(f"\n{downloaded} assets pulled, {skipped} skipped, "
          f"{sess.n_requests} requests, {sess.bytes_read:,} bytes.")
    return 0


# ---------------------------------------------------------------------------

def _write_csv(path: Path, header: list[str], rows) -> int:
    tmp = path.with_suffix(".csv.part")
    n = 0
    with tmp.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(header)
        for r in rows:
            w.writerow(r)
            n += 1
    tmp.replace(path)
    return n


def cmd_build() -> int:
    CLEAN.mkdir(parents=True, exist_ok=True)
    man = _load_manifest()
    if not man.get("assets"):
        print("nothing pulled - run `pull` first")
        return 1
    built = []

    # --- 1. E-Rate tribal line items --------------------------------------
    src = RAW / "erate_tribal.json"
    d = json.loads(src.read_text(encoding="utf-8"))
    recs = d["records"]
    cols = sorted({k for r in recs for k in r})
    header = cols + ["source_asset_id", "source_url", "retrieved_at",
                     "source_id", "population_basis", "tribal_type_verbatim",
                     "inclusion_basis", "inclusion_basis_detail"]
    p = CLEAN / "usac_erate_tribal_commitments.csv"
    n = _write_csv(p, header, (
        [r.get(c, "") for c in cols]
        + [d["asset_id"], f"https://{HOST}/resource/{d['asset_id']}",
           d["retrieved_at"], "usac_open_data", "TYPE_FILTER",
           r.get("tribal_type", ""),
           # ADR-013 C12: `subject_classification`, and the classifier is
           # named - USAC's own `tribal_type` field on the Form 471 record.
           "subject_classification",
           "USAC tribal_type = " + (r.get("tribal_type") or "")]
        for r in recs))
    ag.reconcile(n, d["advertised"], "usac_erate_tribal_commitments")
    built.append((p.name, n, len(header)))
    print(f"BUILD {p.name:<44} {n:>9,} rows x {len(header)} cols")

    # --- 2. the ENTITY grain, derived once so nobody counts rows as schools -
    ent: dict[str, dict] = {}
    for r in recs:
        k = r.get("ros_entity_number") or ""
        if not k:
            continue
        e = ent.setdefault(k, {"years": set(), "types": Counter(),
                               "names": Counter(), "lines": 0})
        e["lines"] += 1
        if r.get("funding_year"):
            e["years"].add(str(r["funding_year"]))
        if r.get("tribal_type"):
            e["types"][r["tribal_type"]] += 1
        if r.get("ros_entity_name"):
            e["names"][r["ros_entity_name"]] += 1
        for f in ("ros_physical_city", "ros_physical_state",
                  "ros_physical_zipcode", "ros_physical_address",
                  "ros_entity_type", "ros_urban_rural_status",
                  "ros_latitude", "ros_longitude", "ros_physical_county",
                  "ros_number_of_full_time_students", "organization_name",
                  "billed_entity_number"):
            if r.get(f):
                e[f] = r[f]
    eh = ["ros_entity_number", "ros_entity_name", "tribal_type",
          "tribal_type_distinct_values", "ros_entity_type", "organization_name",
          "billed_entity_number", "ros_physical_address", "ros_physical_city",
          "ros_physical_state", "ros_physical_zipcode", "ros_physical_county",
          "ros_urban_rural_status", "ros_latitude", "ros_longitude",
          "ros_number_of_full_time_students", "line_item_rows",
          "funding_years_present", "first_funding_year", "last_funding_year",
          "source_asset_id", "retrieved_at", "source_id", "population_basis",
          "inclusion_basis", "inclusion_basis_detail"]
    pe = CLEAN / "usac_erate_tribal_entities.csv"
    ne = _write_csv(pe, eh, (
        [k, e["names"].most_common(1)[0][0] if e["names"] else "",
         e["types"].most_common(1)[0][0] if e["types"] else "",
         len(e["types"]), e.get("ros_entity_type", ""),
         e.get("organization_name", ""), e.get("billed_entity_number", ""),
         e.get("ros_physical_address", ""), e.get("ros_physical_city", ""),
         e.get("ros_physical_state", ""), e.get("ros_physical_zipcode", ""),
         e.get("ros_physical_county", ""), e.get("ros_urban_rural_status", ""),
         e.get("ros_latitude", ""), e.get("ros_longitude", ""),
         e.get("ros_number_of_full_time_students", ""), e["lines"],
         len(e["years"]), min(e["years"]) if e["years"] else "",
         max(e["years"]) if e["years"] else "",
         d["asset_id"], d["retrieved_at"], "usac_open_data", "TYPE_FILTER",
         "subject_classification",
         "USAC tribal_type = " + (e["types"].most_common(1)[0][0]
                                  if e["types"] else "")]
        for k, e in sorted(ent.items())))
    built.append((pe.name, ne, len(eh)))
    print(f"BUILD {pe.name:<44} {ne:>9,} rows x {len(eh)} cols   "
          f"(the ENTITY grain; {n:,} line items collapse to {ne:,} entities)")

    # --- 3 & 4. RHC -------------------------------------------------------
    for key, table, basis in (
            ("rhc_hcp_directory", "usac_rhc_hcp_directory", "FULL_UNIVERSE_ROSTER"),
            ("rhc_native_candidates", "usac_rhc_native_candidate_lines",
             "NAME_TOKEN_SWEEP")):
        s = RAW / f"{key}.json"
        if not s.exists():
            print(f"MISSING raw {s.name} - skipped")
            continue
        dd = json.loads(s.read_text(encoding="utf-8"))
        rr = dd["records"]
        cc = sorted({k for r in rr for k in r})
        extra = ["source_asset_id", "source_url", "retrieved_at", "source_id",
                 "population_basis", "confidence_tier", "attribution_method",
                 "inclusion_basis", "inclusion_basis_detail",
                 "inclusion_basis_terms_matched"]
        hh = cc + extra
        pp = CLEAN / f"{table}.csv"
        # tier C, attribution_method `unmatched`: a NAME TOKEN IS NOT A
        # DETERMINATION. Nothing downstream may read these as attributed.
        tier = "C" if basis == "NAME_TOKEN_SWEEP" else ""
        method = "usac_rhc_name_token_candidate" if tier else ""
        # ADR-013 C12: `term_match` REQUIRES the matched terms to be
        # recorded, not just the fact of matching. Re-derived here from the
        # same RHC_TOKENS list the WHERE clause was built from, so the column
        # cannot drift away from the filter that produced the row.
        def _terms(r):
            hay = ((r.get("filing_hcp_name") or "") + " | "
                   + (r.get("participating_hcp_name") or "")).lower()
            return "; ".join(t.strip() for t in RHC_TOKENS if t in hay)

        if basis == "NAME_TOKEN_SWEEP":
            ib, ibd = "term_match", ("provider name carries a Native token; "
                                     "RHC publishes NO tribal type, so this is "
                                     "a CANDIDATE and not a classification")
        else:
            ib, ibd = ("NOT_INDIAN_COUNTRY_SCOPED_DENOMINATOR",
                       "the FULL RHC provider universe, held so the Native "
                       "subset has a denominator. MOST ROWS ARE NOT INDIAN "
                       "COUNTRY. ADR-013's six bases do not cover a "
                       "denominator table; this value is PROPOSED, not "
                       "adopted - see docs/BIAMAPS_ACQUISITION_LOG_2026-09-02.md")
        nn = _write_csv(pp, hh, (
            [r.get(c, "") for c in cc]
            + [dd["asset_id"], f"https://{HOST}/resource/{dd['asset_id']}",
               dd["retrieved_at"], "usac_open_data", basis, tier, method,
               ib, ibd, _terms(r) if basis == "NAME_TOKEN_SWEEP" else ""]
            for r in rr))
        ag.reconcile(nn, dd["advertised"], table)
        built.append((pp.name, nn, len(hh)))
        print(f"BUILD {pp.name:<44} {nn:>9,} rows x {len(hh)} cols"
              + ("   [tier C CANDIDATES - never attributed]" if tier else ""))

    (ROOT / "docs" / "usac_acquisition_1120.json").write_text(json.dumps({
        "script": SCRIPT, "host": HOST,
        "built_at": datetime.now(timezone.utc).isoformat(),
        "licence": man["assets"]["erate_tribal"]["licence_verbatim"],
        "attribution": man["assets"]["erate_tribal"]["attribution_verbatim"],
        "tables": [{"table": t, "rows": r, "columns": c} for t, r, c in built],
    }, indent=2), encoding="utf-8")
    print(f"\n{len(built)} tables built, {sum(b[1] for b in built):,} rows total.")
    return 0


def cmd_verify() -> int:
    man = _load_manifest()
    fails, checks = [], 0

    def ck(name, cond, detail=""):
        nonlocal checks
        checks += 1
        print(("OK  " if cond else "FAIL") + "  " + name + (f"  {detail}" if detail else ""))
        if not cond:
            fails.append(name)

    if not man.get("assets"):
        print("UNMEASURED - nothing pulled.")
        return 1

    for key, table in (("erate_tribal", "usac_erate_tribal_commitments"),
                       ("rhc_hcp_directory", "usac_rhc_hcp_directory"),
                       ("rhc_native_candidates", "usac_rhc_native_candidate_lines")):
        a = man["assets"].get(key)
        if not a:
            ck(f"{key}: manifest entry", False)
            continue
        ck(f"{key}: rows == source count(*)", a["rows"] == a["advertised"],
           f"{a['rows']:,} vs {a['advertised']:,}")
        ck(f"{key}: page hashes all distinct",
           a["distinct_page_sha256"] == len(a["page_sha256"]),
           f"{a['distinct_page_sha256']}/{len(a['page_sha256'])}")
        ck(f"{key}: licence recorded as Public Domain",
           (a.get("licence_verbatim") or {}).get("name") == "Public Domain",
           str(a.get("licence_verbatim")))
        p = CLEAN / f"{table}.csv"
        if not p.exists():
            ck(f"{table}: built", False)
            continue
        with p.open("r", encoding="utf-8", newline="") as fh:
            rdr = csv.reader(fh)
            hdr = next(rdr)
            n = sum(1 for _ in rdr)
        ck(f"{table}: CSV rows == source count", n == a["advertised"],
           f"{n:,} vs {a['advertised']:,}")
        ck(f"{table}: population_basis column present",
           "population_basis" in hdr)

    # The E-Rate slice must be exactly the tribal_type population and nothing
    # else. A filter that quietly widened is the failure this catches.
    p = CLEAN / "usac_erate_tribal_commitments.csv"
    if p.exists():
        blank = 0
        seen_types = Counter()
        with p.open("r", encoding="utf-8", newline="") as fh:
            for r in csv.DictReader(fh):
                v = (r.get("tribal_type") or "").strip()
                seen_types[v] += 1
                if not v:
                    blank += 1
        ck("erate slice: zero rows with a blank tribal_type", blank == 0, f"{blank:,}")
        ck("erate slice: 42,967 Tribal School",
           seen_types.get("Tribal School") == 42967, str(seen_types.get("Tribal School")))
        ck("erate slice: 10,862 Tribal Library",
           seen_types.get("Tribal Library") == 10862, str(seen_types.get("Tribal Library")))

    # The RHC candidate file must never carry a tier above C.
    p = CLEAN / "usac_rhc_native_candidate_lines.csv"
    if p.exists():
        bad = 0
        with p.open("r", encoding="utf-8", newline="") as fh:
            for r in csv.DictReader(fh):
                if (r.get("confidence_tier") or "") != "C":
                    bad += 1
        ck("rhc candidates: every row is tier C, none promoted", bad == 0, f"{bad:,}")

    print(f"\n{checks} checks, {len(fails)} failed.")
    if fails:
        print("BREACH: " + "; ".join(fails))
        return 1
    return 0


def cmd_selftest() -> int:
    import copy
    man = _load_manifest()
    if not man.get("assets"):
        print("UNMEASURED - selftest needs a pulled manifest.")
        return 1
    backup = copy.deepcopy(man)
    try:
        man["assets"]["erate_tribal"]["rows"] = \
            man["assets"]["erate_tribal"]["advertised"] - 1
        _save_manifest(man)
        print("--- verify against an INJECTED short-retrieval ---")
        if cmd_verify() != 1:
            print("SELFTEST FAIL: verify did not exit 1 on an injected violation")
            return 1
    finally:
        _save_manifest(backup)
    print("--- restored; re-verifying ---")
    rc = cmd_verify()
    print("\nSELFTEST " + ("PASS" if rc == 0 else "FAIL"))
    return 0 if rc == 0 else 1


def main() -> int:
    c = sys.argv[1] if len(sys.argv) > 1 else ""
    return {"probe": cmd_probe, "build": cmd_build, "verify": cmd_verify,
            "selftest": cmd_selftest}.get(
        c, (lambda: cmd_pull("--refetch" in sys.argv)) if c == "pull"
        else (lambda: (print(__doc__), 1)[1]))()


if __name__ == "__main__":
    raise SystemExit(main())
