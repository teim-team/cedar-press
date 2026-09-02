#!/usr/bin/env python3
"""
Cedar Press - SHARD F, step 1: build the organisational-layer slice.

WHAT THIS IS
------------
The 153 entities in `data/spine/cedar_identity_register.csv` whose `entity_class`
is one of the five organisational classes:

    Intertribal Organization                     56
    Urban Indian Organization                    43
    Federal-level self-governance consortium     29
    Federal-level constituency entity            22
    State-level constituency entity               3

ZERO NETWORK. Every field written here comes off disk, from datasets Cedar
already owns. The point is to know exactly what is already known BEFORE
spending a single request, because a large part of the intertribal side has
already been worked:

    data/clean/intertribal_orgs.csv          57 rows, 52 carry a website, 55 an EIN
    data/clean/intertribal_memberships.csv   989 rows across 36 organisations
    data/clean/np_ein_entity_hub.csv         EIN -> cedar_uid, tier INHERITED from source
    data/clean/np_orgs.csv                   BMF fields, state/city, source_url
    data/clean/np_financials.csv             990 financials + pdf_url

Output: data/staging/tribe_harvest/shard_f/_slice.json

TIER DISCIPLINE
---------------
`ein_tier` and `ein_tier_source` are COPIED from the hub row. This script never
assigns a tier and never promotes one. Corroboration between two on-disk
sources is recorded as a count, not as a promotion (see the tier_note carried in
np_ein_entity_hub.csv).
"""
import csv, json, os, sys, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "staging", "tribe_harvest", "shard_f", "_slice.json")

CLASSES = {
    "Intertribal Organization",
    "Urban Indian Organization",
    "Federal-level self-governance consortium",
    "Federal-level constituency entity",
    "State-level constituency entity",
}


def rd(rel):
    p = os.path.join(ROOT, rel)
    if not os.path.exists(p):
        return []
    with open(p, encoding="utf-8-sig", errors="replace", newline="") as fh:
        return list(csv.DictReader(fh))


def main():
    reg = rd("data/spine/cedar_identity_register.csv")
    slice_rows = [r for r in reg if r["entity_class"] in CLASSES]
    assert len(slice_rows) == 153, f"expected 153, got {len(slice_rows)}"

    ito = {r["proposed_id"]: r for r in rd("data/clean/intertribal_orgs.csv") if r["proposed_id"]}

    memb = rd("data/clean/intertribal_memberships.csv")
    memb_by_org = collections.defaultdict(list)
    for m in memb:
        memb_by_org[m["org_id"]].append(m)

    hub = rd("data/clean/np_ein_entity_hub.csv")
    hub_by_uid = collections.defaultdict(list)
    for h in hub:
        if h.get("cedar_uid"):
            hub_by_uid[h["cedar_uid"]].append(h)

    nporgs = rd("data/clean/np_orgs.csv")
    npo_by_ein = {}
    for n in nporgs:
        e = (n.get("EIN") or "").strip()
        if e:
            npo_by_ein.setdefault(e, n)

    fin = rd("data/clean/np_financials.csv")
    fin_by_ein = collections.defaultdict(list)
    for f in fin:
        e = (f.get("ein") or "").strip()
        if e:
            fin_by_ein[e].append(f)

    out = []
    for r in slice_rows:
        eid = (r.get("cedar_entity_id") or "").strip()
        rec = {
            "cedar_uid": r["cedar_uid"],
            "handle": r["handle"],
            "cedar_entity_id": eid,
            "canonical_name": r["canonical_name"],
            "entity_class": r["entity_class"],
            "known": {},
        }

        k = rec["known"]

        # --- intertribal_orgs.csv (the only Cedar table that already carries a website)
        io = ito.get(eid)
        if io:
            k["ito_website"] = io.get("website", "").strip()
            k["ito_evidence_url"] = io.get("evidence_url", "").strip()
            k["ito_ein"] = io.get("ein", "").strip()
            k["ito_aliases"] = io.get("aliases", "").strip()
            k["ito_member_count"] = io.get("member_count", "").strip()
            k["ito_roster_count"] = io.get("roster_count", "").strip()
            k["ito_retrieved"] = io.get("retrieved_date", "").strip()
            k["ito_notes"] = io.get("notes", "").strip()

        # --- existing roster coverage
        ms = memb_by_org.get(eid, [])
        k["existing_membership_rows"] = len(ms)
        k["existing_membership_source_urls"] = sorted(
            {m["source_url"] for m in ms if m.get("source_url")}
        )

        # --- EIN(s) already sourced in Cedar, with the tier INHERITED from the hub row
        eins = []
        for h in hub_by_uid.get(r["cedar_uid"], []):
            e = (h.get("ein") or "").strip()
            if not e:
                continue
            npo = npo_by_ein.get(e, {})
            fins = sorted(
                fin_by_ein.get(e, []), key=lambda x: x.get("tax_year", ""), reverse=True
            )
            eins.append(
                {
                    "ein": e,
                    "hub_org_name": h.get("org_name", ""),
                    "ein_tier": h.get("link_tier", ""),
                    "ein_tier_source": h.get("link_tier_source", ""),
                    "ein_link_method": h.get("link_method", ""),
                    "ein_link_sources": h.get("link_sources", ""),
                    "state": h.get("entity_state", "") or npo.get("state", ""),
                    "city": npo.get("city", ""),
                    "ntee_code": npo.get("ntee_code", ""),
                    "bmf_subsection": npo.get("bmf_subsection", ""),
                    "bmf_revenue_amt": npo.get("bmf_revenue_amt", ""),
                    "bmf_asset_amt": npo.get("bmf_asset_amt", ""),
                    "np_orgs_source_url": npo.get("source_url", ""),
                    "latest_990": (
                        {
                            "tax_year": fins[0].get("tax_year", ""),
                            "form_type": fins[0].get("form_type", ""),
                            "total_revenue": fins[0].get("total_revenue", ""),
                            "total_assets": fins[0].get("total_assets", ""),
                            "n_employees": fins[0].get("n_employees", ""),
                            "pdf_url": fins[0].get("pdf_url", ""),
                            "source_url": fins[0].get("source_url", ""),
                        }
                        if fins
                        else None
                    ),
                    "n_990_years": len(fins),
                }
            )
        k["eins_on_disk"] = eins

        out.append(rec)

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1)

    # ---- report
    byc = collections.Counter(r["entity_class"] for r in out)
    print(f"slice: {len(out)} entities -> {os.path.relpath(OUT, ROOT)}")
    for c, n in byc.most_common():
        sub = [r for r in out if r["entity_class"] == c]
        w = sum(1 for r in sub if r["known"].get("ito_website"))
        e = sum(1 for r in sub if r["known"]["eins_on_disk"])
        m = sum(1 for r in sub if r["known"]["existing_membership_rows"])
        print(f"  {c:44s} n={n:3d}  website_known={w:3d}  ein_known={e:3d}  roster_known={m:3d}")
    print()
    print("GAPS (this is the shard's actual work):")
    print("  no website on disk :", sum(1 for r in out if not r["known"].get("ito_website")))
    print("  no EIN on disk     :", sum(1 for r in out if not r["known"]["eins_on_disk"]))
    print("  no roster on disk  :", sum(1 for r in out if not r["known"]["existing_membership_rows"]))


if __name__ == "__main__":
    sys.exit(main())
