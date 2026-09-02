#!/usr/bin/env python3
"""
Cedar Press - SHARD F, step 7: nonprofit financial identity - EIN and the 990 route.

TWO LEGS, RECORDED SEPARATELY (docs/PULL_DISCIPLINE.md, selection doctrine)
---------------------------------------------------------------------------
    KNOWN_IDENTIFIER  an EIN already in Cedar (np_ein_entity_hub.csv), CONFIRMED
                      against the IRS-derived record at ProPublica
    NAME_SEARCH       ProPublica's name search, for the entities Cedar has no
                      EIN for at all

Neither leg is a superset of the other and every row says which one produced it,
in `ein_leg`. A name-search hit is a CANDIDATE: the name matched, and that is
all. It carries `ein_confidence` and is never promoted to a fact here.

WHY PROPUBLICA
--------------
It republishes the IRS Business Master File and the 990 XML corpus, it is the
route Cedar already touches, and it is rate-limited but tolerant if you go slow
(PULL_DISCIPLINE "Hosts with known limits"). One request every 2 seconds, and a
429 ends the run rather than being retried into a block.

A guessed EIN is worthless. Where neither leg produces one, the row says
`ein: ""` with the reason. That is the correct output, not a gap.

Output: data/staging/tribe_harvest/shard_f/ein_990.jsonl
"""
import json, os, re, sys, time, unicodedata

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import shard_f_fetch as F

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SH = os.path.join(ROOT, "data", "staging", "tribe_harvest", "shard_f")
OUT = os.path.join(SH, "ein_990.jsonl")
TODAY = time.strftime("%Y-%m-%d")

API = "https://projects.propublica.org/nonprofits/api/v2"


def norm(s):
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.lower().replace("&", " and ")
    s = re.sub(r"\b(inc|incorporated|corporation|corp|the|of|a)\b", " ", s)
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return " ".join(s.split())


def jget(url):
    rec = F.fetch(url, force=True)
    if rec["http_status"] != 200:
        return None, rec
    try:
        return json.loads(F.read_raw(rec)), rec
    except Exception:
        return None, rec


def main():
    ents = json.load(open(os.path.join(SH, "_slice.json"), encoding="utf-8"))
    fh = open(OUT, "a", encoding="utf-8")
    n_conf = n_found = n_none = 0

    for i, e in enumerate(ents, 1):
        known = e["known"]
        eins = known.get("eins_on_disk") or []
        # intertribal_orgs.csv carries its own EIN, hyphenated
        ito_ein = re.sub(r"\D", "", known.get("ito_ein", "") or "")
        if ito_ein and ito_ein not in {x["ein"] for x in eins}:
            eins.append({"ein": ito_ein, "ein_tier": "",
                         "ein_tier_source": "data/clean/intertribal_orgs.csv",
                         "hub_org_name": "", "latest_990": None, "n_990_years": 0})

        rows = []
        if eins:
            for x in eins:
                ein = re.sub(r"\D", "", x["ein"])
                d, rec = jget(f"{API}/organizations/{ein}.json")
                org = (d or {}).get("organization") or {}
                filings = (d or {}).get("filings_with_data") or []
                latest = filings[0] if filings else {}
                nm_ok = None
                if org.get("name"):
                    a, b = norm(org["name"]), norm(e["canonical_name"])
                    nm_ok = (a == b) or (a in b) or (b in a)
                rows.append({
                    "cedar_uid": e["cedar_uid"], "handle": e["handle"],
                    "canonical_name": e["canonical_name"],
                    "entity_class": e["entity_class"],
                    "ein_leg": "KNOWN_IDENTIFIER",
                    "ein": ein,
                    "ein_source_in_cedar": x.get("ein_tier_source", ""),
                    "ein_tier_inherited": x.get("ein_tier", ""),
                    "propublica_status": rec["http_status"],
                    "irs_name": org.get("name", ""),
                    "irs_name_agrees_with_cedar": nm_ok,
                    "city": org.get("city", ""), "state": org.get("state", ""),
                    "ntee_code": org.get("ntee_code", ""),
                    "subsection_code": org.get("subsection_code", ""),
                    "latest_990_year": latest.get("tax_prd_yr", ""),
                    "latest_990_formtype": latest.get("formtype", ""),
                    "total_revenue": latest.get("totrevenue", ""),
                    "total_expenses": latest.get("totfuncexpns", ""),
                    "total_assets": latest.get("totassetsend", ""),
                    "n_990_years_propublica": len(filings),
                    "n_990_years_cedar": x.get("n_990_years", 0),
                    "form_990_route": f"https://projects.propublica.org/nonprofits/organizations/{ein}",
                    "form_990_api": f"{API}/organizations/{ein}.json",
                    "latest_990_pdf": latest.get("pdf_url", ""),
                    "ein_confidence": (0.95 if nm_ok else 0.5 if nm_ok is None else 0.4),
                    "retrieved_date": TODAY,
                    "note": ("EIN was already in Cedar; this row CONFIRMS it against the "
                             "IRS-derived record. Tier is inherited, never promoted."),
                })
            n_conf += 1
        else:
            q = re.sub(r"[^A-Za-z0-9 ]", " ", e["canonical_name"])
            q = " ".join(q.split())
            d, rec = jget(f"{API}/search.json?q={q.replace(' ', '%20')}")
            hits = (d or {}).get("organizations") or []
            best, bs = None, 0.0
            tgt = norm(e["canonical_name"])
            for hgh in hits[:15]:
                a = norm(hgh.get("name", ""))
                if not a:
                    continue
                s = 1.0 if a == tgt else 0.75 if (a in tgt or tgt in a) else 0.0
                if s > bs:
                    best, bs = hgh, s
            if best:
                ein = re.sub(r"\D", "", str(best.get("ein", "")))
                rows.append({
                    "cedar_uid": e["cedar_uid"], "handle": e["handle"],
                    "canonical_name": e["canonical_name"],
                    "entity_class": e["entity_class"],
                    "ein_leg": "NAME_SEARCH",
                    "ein": ein,
                    "ein_source_in_cedar": "",
                    "ein_tier_inherited": "",
                    "propublica_status": rec["http_status"],
                    "irs_name": best.get("name", ""),
                    "irs_name_agrees_with_cedar": bs >= 0.99,
                    "city": best.get("city", ""), "state": best.get("state", ""),
                    "ntee_code": best.get("ntee_code", ""),
                    "subsection_code": best.get("subseccd", ""),
                    "form_990_route": f"https://projects.propublica.org/nonprofits/organizations/{ein}",
                    "form_990_api": f"{API}/organizations/{ein}.json",
                    "search_url": f"{API}/search.json?q={q.replace(' ', '%20')}",
                    "n_search_hits": len(hits),
                    "ein_confidence": round(bs, 2),
                    "retrieved_date": TODAY,
                    "note": ("CANDIDATE only - Cedar held no EIN for this entity and this "
                             "came from a ProPublica NAME search. Not a determination."),
                })
                n_found += 1
            else:
                rows.append({
                    "cedar_uid": e["cedar_uid"], "handle": e["handle"],
                    "canonical_name": e["canonical_name"],
                    "entity_class": e["entity_class"],
                    "ein_leg": "NAME_SEARCH",
                    "ein": "",
                    "propublica_status": rec["http_status"],
                    "n_search_hits": len(hits),
                    "search_url": f"{API}/search.json?q={q.replace(' ', '%20')}",
                    "ein_confidence": 0.0,
                    "retrieved_date": TODAY,
                    "note": ("no EIN: Cedar held none and a ProPublica name search returned "
                             "no acceptable match. Left blank deliberately - an unsourced "
                             "EIN is worthless."),
                })
                n_none += 1

        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
        fh.flush()
        tag = rows[0].get("ein") or "-"
        print(f"[{i:3d}/{len(ents)}] {rows[0]['ein_leg'][:4]} {tag:>10s}  {e['canonical_name'][:52]}")
        if rows and rows[0].get("propublica_status") == 429:
            print("!! ProPublica returned 429 - stopping rather than retrying into a block")
            break

    fh.close()
    print(f"\nEIN confirmed from Cedar: {n_conf}   found by name search: {n_found}   none: {n_none}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
