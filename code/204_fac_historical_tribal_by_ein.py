"""
204_fac_historical_tribal_by_ein.py
===================================
Cedar Press. Written 2026-08-26.

CORRECTS A NEAR-MISS IN `code/203_verify_fac_historical_bulk_tribal.py`.

203 filtered the Census-era FAC archive for tribal auditees on
`TYPEOFENTITY.startswith("I")` -- the MODERN vocabulary -- and printed
**"TRIBAL auditee rows = 0"** for both FY1998 and FY2005.

That number is an artefact, not a finding. In the Census-era files
`TYPEOFENTITY` is a NUMERIC code (908, 505, 903, ...) and in FY1998 it is
**blank on all 32,247 rows**. A filter written against the wrong vocabulary
returns zero and looks exactly like an empty source. `AGENTS.md` concurrency
rule 8 names this: *an absent column reads as an empty source; a coverage
computation must RAISE on a missing column, never print a zero.* Here it was an
absent VOCABULARY rather than an absent column, and it printed a zero.

THE CORRECT TEST USES NO NAME MATCHING AT ALL.

`data/clean/fac_tribal_single_audits.csv` holds 6,780 records that FAC itself
types `entity_type = tribal`, each with an `auditee_ein`. Those EINs are the
source's own tribal roster. Looking them up in the Census-era archive is an
EXACT join on a federal identifier -- the thing that is supposed to be
impossible before FY2007.

TIER DISCIPLINE: an EIN hit here inherits whatever the 2016+ row was worth. It
proves the SAME EIN filed a Single Audit in the earlier year; it does not by
itself prove the tribal entity link, which came from FAC's own `entity_type`.
Recorded as an observation, not an attribution.

READ-ONLY over files already on disk. Zero network requests.

Run:  py -3 code/204_fac_historical_tribal_by_ein.py
"""

import csv
import io
import json
import os
import sys
import zipfile
import collections
from datetime import datetime, timezone

csv.field_size_limit(10 ** 9)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TRIBAL = os.path.join(ROOT, "data", "clean", "fac_tribal_single_audits.csv")
RAW = os.path.join(ROOT, "data", "raw", "fac_historical_census")
OUT = os.path.join(ROOT, "docs", "FAC_HISTORICAL_TRIBAL_BY_EIN.json")


def norm_ein(s):
    return "".join(ch for ch in (s or "") if ch.isdigit()).lstrip("0")


def load_tribal_roster():
    """FAC's own tribal EINs, from the 2016+ pull. No name matching."""
    eins = {}
    with open(TRIBAL, encoding="utf-8", errors="replace", newline="") as f:
        for r in csv.DictReader(f):
            e = norm_ein(r.get("auditee_ein"))
            if not e:
                continue
            eins.setdefault(e, {
                "auditee_name": (r.get("auditee_name") or "").strip(),
                "entity_id": (r.get("entity_id") or "").strip(),
                "entity_name": (r.get("entity_name") or "").strip(),
                "entity_tier": (r.get("entity_tier") or "").strip(),
                "state": (r.get("auditee_state") or "").strip(),
            })
    return eins


def scan_year(path, roster):
    res = {"zip": os.path.basename(path)}
    with zipfile.ZipFile(path) as z:
        names = z.namelist()
        hdr = next((n for n in names if "ELECAUDITHEADER" in n.upper()), None)
        awd = next((n for n in names if n.upper().endswith("ELECAUDITS.CSV")), None)
        if not hdr:
            return {"error": "no header member"}

        hits = {}
        entity_type_vals = collections.Counter()
        typeofentity_vals = collections.Counter()
        n = 0
        with z.open(hdr) as fh:
            rd = csv.DictReader(io.TextIOWrapper(fh, encoding="utf-8",
                                                 errors="replace", newline=""))
            for r in rd:
                n += 1
                entity_type_vals[(r.get("ENTITY_TYPE") or "").strip()] += 1
                typeofentity_vals[(r.get("TYPEOFENTITY") or "").strip()] += 1
                e = norm_ein(r.get("EIN"))
                if e and e in roster:
                    try:
                        exp = float((r.get("TOTFEDEXPEND") or 0) or 0)
                    except ValueError:
                        exp = 0.0
                    hits[e] = {
                        "ein": r.get("EIN"),
                        "auditee_name_in_archive": (r.get("AUDITEENAME") or "").strip(),
                        "state": (r.get("STATE") or "").strip(),
                        "audit_year": (r.get("AUDITYEAR") or "").strip(),
                        "total_fed_expend": exp,
                        "typeofentity_code": (r.get("TYPEOFENTITY") or "").strip(),
                        "entity_type": (r.get("ENTITY_TYPE") or "").strip(),
                        "cedar_entity_name": roster[e]["entity_name"],
                        "cedar_entity_id": roster[e]["entity_id"],
                        "cedar_inherited_tier": roster[e]["entity_tier"],
                        "dbkey": (r.get("DBKEY") or "").strip(),
                    }
        res["header_rows"] = n
        res["ENTITY_TYPE_values"] = dict(entity_type_vals.most_common(12))
        res["TYPEOFENTITY_values"] = dict(typeofentity_vals.most_common(12))
        res["tribal_ein_matches"] = len(hits)
        res["tribal_total_fed_expend"] = round(
            sum(h["total_fed_expend"] for h in hits.values()), 2)
        res["matches"] = sorted(hits.values(),
                                key=lambda h: -h["total_fed_expend"])

        # SEFA rows (auditee x CFDA programme) for the matched EINs
        if awd:
            keys = {h["dbkey"] for h in hits.values() if h["dbkey"]}
            eins = set(hits)
            prog_rows = 0
            prog_amt = 0.0
            cfda = collections.Counter()
            with z.open(awd) as fh:
                rd = csv.DictReader(io.TextIOWrapper(fh, encoding="utf-8",
                                                     errors="replace",
                                                     newline=""))
                for r in rd:
                    e = norm_ein(r.get("EIN"))
                    k = (r.get("DBKEY") or "").strip()
                    if (e and e in eins) or (k and k in keys):
                        prog_rows += 1
                        try:
                            a = float((r.get("AMOUNT") or 0) or 0)
                        except ValueError:
                            a = 0.0
                        prog_amt += a
                        c = (r.get("CFDA") or "").strip()
                        if c:
                            cfda[c] += 1
            res["tribal_SEFA_program_rows"] = prog_rows
            res["tribal_SEFA_amount"] = round(prog_amt, 2)
            res["top_cfda"] = dict(cfda.most_common(15))
    return res


def main():
    roster = load_tribal_roster()
    print(f"FAC-typed tribal EINs from the 2016+ pull: {len(roster):,}",
          file=sys.stderr)

    zips = sorted(f for f in os.listdir(RAW) if f.endswith(".zip")) \
        if os.path.isdir(RAW) else []
    if not zips:
        print(f"no archives in {RAW}; run code/203 first", file=sys.stderr)
        sys.exit(2)

    out = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "script": "code/204_fac_historical_tribal_by_ein.py",
        "network_requests_issued": 0,
        "method": ("Exact EIN join between FAC's own 2016+ tribal roster "
                   "(entity_type=tribal, 6,780 records) and the Census-era "
                   "FAC archive. NO name matching anywhere in this script."),
        "tier_note": ("An EIN hit proves the same EIN filed a Single Audit in "
                      "the earlier year. The tribal typing is FAC's, from the "
                      "2016+ row; the Cedar entity link and its tier are "
                      "INHERITED, not assigned here."),
        "corrects": ("code/203 printed 'TRIBAL auditee rows = 0' by filtering "
                     "TYPEOFENTITY on the MODERN vocabulary. The Census-era "
                     "files use numeric codes, and FY1998 is blank on every "
                     "row. A wrong-vocabulary filter returns zero and reads as "
                     "an empty source."),
        "tribal_roster_eins": len(roster),
        "years": {},
    }
    for z in zips:
        y = z.replace("census-", "").replace(".zip", "")
        print(f"scanning {z} ...", file=sys.stderr)
        out["years"][y] = scan_year(os.path.join(RAW, z), roster)

    tmp = OUT + ".part"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1)
    os.replace(tmp, OUT)
    with open(OUT, encoding="utf-8") as fh:
        back = json.load(fh)
    assert back["script"] == out["script"], "re-read verification FAILED"
    print(f"\nwrote + verified {OUT}", file=sys.stderr)

    for y, r in sorted(out["years"].items()):
        if "error" in r:
            print(f"\n{y}: {r['error']}", file=sys.stderr)
            continue
        print(f"\n=== census-{y} ===", file=sys.stderr)
        print(f"  header rows {r['header_rows']:,}", file=sys.stderr)
        print(f"  ENTITY_TYPE values: {r['ENTITY_TYPE_values']}", file=sys.stderr)
        print(f"  TYPEOFENTITY values: "
              f"{list(r['TYPEOFENTITY_values'])[:8]}", file=sys.stderr)
        print(f"  *** TRIBAL EIN MATCHES: {r['tribal_ein_matches']:,} "
              f"— reported federal expenditures "
              f"${r['tribal_total_fed_expend']:,.0f}", file=sys.stderr)
        if "tribal_SEFA_program_rows" in r:
            print(f"  SEFA programme rows for those EINs: "
                  f"{r['tribal_SEFA_program_rows']:,} "
                  f"(${r['tribal_SEFA_amount']:,.0f})", file=sys.stderr)
            print(f"  top CFDA: {list(r['top_cfda'])[:10]}", file=sys.stderr)
        for h in r["matches"][:10]:
            print(f"    {h['auditee_name_in_archive'][:42]:<42} "
                  f"EIN={h['ein']:<12} ${h['total_fed_expend']:>13,.0f}  "
                  f"-> {h['cedar_entity_name'][:26]}", file=sys.stderr)


if __name__ == "__main__":
    main()
