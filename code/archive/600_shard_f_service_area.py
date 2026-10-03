#!/usr/bin/env python3
"""
Cedar Press - SHARD F, step 9: SERVICE AREA and AUTHORISING BASIS. Zero network.

WHY THIS MATTERS TO CEDAR AND NOT JUST TO THIS SHARD
----------------------------------------------------
A `geographic` or `program_authority` inclusion basis is only defensible if
something says what the geography or the authority IS. Right now Cedar asserts
neither for these 153 entities. This step reads it off two things already on
disk:

    ihs_uio_register.jsonl   the IHS Title V register - for a UIO, the city it
                             serves, the IHS area, and the service level the
                             contract buys, from the federal programme office
    raw/*.html               every page this shard already fetched, scanned for
                             the organisation's OWN statement of its authority

The authority scan looks for the statutes these bodies actually operate under
and keeps the sentence, not a label:

    Public Law 93-638 / Indian Self-Determination and Education Assistance Act
    self-governance compact / Title V of the ISDEAA (tribal self-governance)
    Title V of the Indian Health Care Improvement Act (urban programme)
    Title I contract, annual funding agreement, 477 plan

NOTHING IS INFERRED. An organisation that never states its authority gets a row
saying the pages were read and no statement was found. A consortium that is
obviously a 638 contractor but does not say so on its site is NOT recorded as
one - "obviously" is not a source.

Output: data/staging/tribe_harvest/shard_f/service_area_authority.jsonl
"""
import collections, json, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import shard_f_fetch as F

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SH = os.path.join(ROOT, "data", "staging", "tribe_harvest", "shard_f")
RAW = os.path.join(SH, "raw")
OUT = os.path.join(SH, "service_area_authority.jsonl")

AUTH = [
    ("isdeaa_638_contract",
     re.compile(r"(public law\s*93[-– ]?638|p\.?\s?l\.?\s*93[-– ]?638"
                r"|\b638\s+(contract|contracting|program|authority)"
                r"|indian self[- ]determination(\s+and\s+education\s+assistance)?\s+act)",
                re.I)),
    ("isdeaa_title_v_self_governance_compact",
     re.compile(r"(self[- ]govern(ance|ing)\s+(compact|agreement|tribe|status)"
                r"|compact\s+(with|of)\s+the\s+(indian health service|ihs|"
                r"bureau of indian affairs|federal government)"
                r"|annual funding agreement|\bafa\b)", re.I)),
    ("ihcia_title_v_urban_program",
     re.compile(r"title\s+v\s+of\s+the\s+indian\s+health\s+care\s+improvement\s+act"
                r"|indian health care improvement act", re.I)),
    ("pl_102_477_plan",
     re.compile(r"\b(public law\s*102[-– ]?477|477\s+program|477\s+plan)\b", re.I)),
    ("tribal_consortium_designation",
     re.compile(r"\b(tribal (health )?consortium|intertribal consortium|"
                r"tribal organization (as )?defined|designated by (its|the) member "
                r"tribes)\b", re.I)),
    ("nonprofit_501c",
     re.compile(r"\b501\s*\(?\s*c\s*\)?\s*\(?\s*(3|4|6)\s*\)?", re.I)),
]

SERVICE = [
    ("service_area_statement",
     re.compile(r"(service area|catchment area|we serve|serving the|serves the|"
                r"our region (covers|includes)|region (covers|includes|encompasses))"
                r"[^.]{0,300}\.", re.I)),
]


def texts_for(url_list):
    """The on-disk body of each URL this shard already fetched. No requests."""
    out = []
    for u in url_list:
        p = os.path.join(RAW, F._rawname(u))
        if os.path.exists(p) and p.lower().endswith(".html"):
            try:
                h = open(p, "rb").read().decode("utf-8", "replace")
            except Exception:
                continue
            out.append((u, F.to_text(h)))
    return out


def main():
    slice_rows = json.load(open(os.path.join(SH, "_slice.json"), encoding="utf-8"))
    by_uid = {r["cedar_uid"]: r for r in slice_rows}

    # --- the IHS Title V SELF-GOVERNANCE compact register: for a consortium this
    #     is the defining federal record, and it carries the compact YEAR.
    compacts = []
    cp = os.path.join(SH, "ihs_selfgov_compacts.jsonl")
    if os.path.exists(cp):
        compacts = [json.loads(l) for l in open(cp, encoding="utf-8") if l.strip()]

    def cnorm(x):
        x = (x or "").lower().replace("&", " and ")
        x = re.sub(r"\b(inc|incorporated|the|of|a)\b", " ", x)
        return " ".join(re.sub(r"[^a-z0-9]+", " ", x).split())

    comp_idx = {}
    for c in compacts:
        for k in (c["name_as_listed"], c["program_as_listed"]):
            k = cnorm(k)
            if k:
                comp_idx.setdefault(k, c)

    ihs = {}
    p = os.path.join(SH, "ihs_uio_register.jsonl")
    if os.path.exists(p):
        for line in open(p, encoding="utf-8"):
            d = json.loads(line)
            ihs.setdefault(d["org_website"], []).append(d)

    # every URL this shard touched, grouped by entity
    urls = collections.defaultdict(list)
    for line in open(os.path.join(SH, "_probe_results.jsonl"), encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        d = json.loads(line)
        for u in (d.get("final_url"), d.get("url")):
            if u:
                urls[d["cedar_uid"]].append(u)
    mp = os.path.join(SH, "_membership_pages.jsonl")
    if os.path.exists(mp):
        for line in open(mp, encoding="utf-8"):
            d = json.loads(line)
            for pr in d.get("probes", []):
                urls[d["org_cedar_uid"]].append(pr["url"])

    # membership rosters double as the service area of a consortium
    memb = collections.Counter()
    msrc = {}
    mfile = os.path.join(ROOT, "data", "staging", "org_membership", "shard_f.jsonl")
    if os.path.exists(mfile):
        for line in open(mfile, encoding="utf-8"):
            d = json.loads(line)
            if d.get("membership_status") == "current":
                memb[d["org_cedar_uid"]] += 1
                msrc.setdefault(d["org_cedar_uid"], d["source_url"])

    n_auth = n_area = 0
    with open(OUT, "w", encoding="utf-8") as fh:
        for uid, e in by_uid.items():
            rec = {
                "cedar_uid": uid, "handle": e["handle"],
                "canonical_name": e["canonical_name"],
                "entity_class": e["entity_class"],
                "service_area_type": "", "service_area_detail": "",
                "service_area_source": "", "service_area_quote": "",
                "authorizing_basis": [], "authorizing_basis_quotes": [],
                "authorizing_basis_source": "",
                "pages_read_from_disk": 0,
                "note": "",
            }

            # --- UIO: the federal programme office is the authority, not the org
            hit = None
            for u in set(urls.get(uid, [])):
                if u in ihs:
                    hit = ihs[u][0]
                    break
            if hit:
                cities = sorted({x["location_city"] for x in ihs[hit["org_website"]]
                                 if x["location_city"]})
                states = sorted({x["state_heading"] for x in ihs[hit["org_website"]]
                                 if x["state_heading"]})
                rec["service_area_type"] = "urban_catchment_cities"
                rec["service_area_detail"] = (
                    f"city/cities: {', '.join(cities)}; state(s): {', '.join(states)}; "
                    f"IHS area: {hit['ihs_area']}; service level: {hit['service_level']}")
                rec["service_area_source"] = hit["source_url"]
                rec["service_area_quote"] = hit["authorizing_basis_quote"]
                rec["authorizing_basis"].append("ihcia_title_v_urban_program")
                rec["authorizing_basis_quotes"].append(hit["authorizing_basis_quote"])
                rec["authorizing_basis_source"] = hit["source_url"]
                n_area += 1

            # --- consortium: the IHS compact register is the authority of record
            cn = cnorm(e["canonical_name"])
            cm = comp_idx.get(cn)
            cm_method = "exact_name_as_listed" if cm else ""
            # A CONSTITUENT BAND DOES NOT INHERIT ITS PARENT'S COMPACT.
            # Containment matched all five Paiute Indian Tribe of Utah bands to the
            # PARENT tribe's 2022 compact, because "paiute indian tribe utah" is a
            # substring of "paiute indian tribe utah cedar band of paiutes". IHS lists
            # the parent, not the bands. Bois Forte, Fond du Lac and Mille Lacs are a
            # different case and are correct: IHS names each of them in its own right.
            # So containment is allowed only for entities that are not constituency
            # entities; a band must match the printed name exactly or not at all.
            # DIRECTION IS THE WHOLE TEST for a constituency entity:
            #   canonical INSIDE the printed name  -> IHS is naming this very band
            #        "Bois Forte" inside "Bois Forte Band of Chippewa Indians"  ACCEPT
            #   printed name INSIDE the canonical  -> IHS is naming the PARENT
            #        "Paiute Indian Tribe of Utah" inside
            #        "Paiute Indian Tribe of Utah - Cedar Band of Paiutes"      REJECT
            # For everything else both directions are allowed, since an organisation
            # and its printed name differ mostly by suffixes.
            band = "constituency entity" in e["entity_class"]
            if cm is None:
                for k, v in comp_idx.items():
                    if len(k) < 10:
                        continue
                    if band:
                        ok = len(cn) >= 8 and cn in k
                    else:
                        ok = k in cn or cn in k
                    if ok:
                        cm = v
                        cm_method = ("containment, canonical inside the printed name"
                                     if band else "containment_on_name_as_listed")
                        break
            # IHS PRINTS "Yukon-Kuskowim Health Corporation". The corporation spells
            # itself Yukon-Kuskokwim. A federal register's typo is not a different
            # entity, and it is also not something to silently correct - so the match
            # is made here, deliberately, and the defect is recorded on the row.
            if cm is None and cnorm(e["canonical_name"]).startswith("yukon kuskokwim health"):
                cm = comp_idx.get(cnorm("Yukon-Kuskowim Health Corporation"))
                if cm:
                    cm_method = ("matched across a MISSPELLING IN THE SOURCE: IHS prints "
                                 "'Yukon-Kuskowim Health Corporation'; the corporation "
                                 "spells itself Yukon-Kuskokwim")
            if cm:
                rec["authorizing_basis"].append(cm["authorizing_basis"])
                rec["authorizing_basis_quotes"].append(cm["authorizing_basis_quote"])
                rec["authorizing_basis_source"] = cm["source_url"]
                rec["ihs_compact_year"] = cm["compact_year"]
                rec["ihs_compact_area"] = cm["ihs_area"]
                rec["ihs_compact_name_as_listed"] = cm["name_as_listed"]
                rec["ihs_compact_match_method"] = cm_method

            # --- consortium / intertribal: the roster IS the service area
            if not rec["service_area_type"] and memb.get(uid):
                rec["service_area_type"] = "member_tribes"
                rec["service_area_detail"] = (
                    f"{memb[uid]} member entities published by the organisation; the "
                    f"full list is in data/staging/org_membership/shard_f.jsonl under "
                    f"org_cedar_uid = {uid}")
                rec["service_area_source"] = msrc.get(uid, "")
                n_area += 1

            # --- the organisation's own words about its authority
            pages = texts_for(sorted(set(urls.get(uid, [])))[:12])
            rec["pages_read_from_disk"] = len(pages)
            for u, t in pages:
                for label, pat in AUTH:
                    if label in rec["authorizing_basis"]:
                        continue
                    m = pat.search(t)
                    if m:
                        q = re.sub(r"\s+", " ",
                                   t[max(0, m.start() - 140):m.end() + 200]).strip()
                        rec["authorizing_basis"].append(label)
                        rec["authorizing_basis_quotes"].append(q[:400])
                        if not rec["authorizing_basis_source"]:
                            rec["authorizing_basis_source"] = u
                if not rec["service_area_quote"]:
                    for _, pat in SERVICE:
                        m = pat.search(t)
                        if m:
                            rec["service_area_quote"] = re.sub(
                                r"\s+", " ", m.group(0)).strip()[:400]
                            if not rec["service_area_source"]:
                                rec["service_area_source"] = u
                            if not rec["service_area_type"]:
                                rec["service_area_type"] = "stated_service_area"
                                rec["service_area_detail"] = rec["service_area_quote"][:200]
                                n_area += 1
                            break

            if rec["authorizing_basis"]:
                n_auth += 1
            else:
                rec["note"] = (
                    f"{len(pages)} page(s) already retrieved by this shard were read from "
                    f"disk and none states an authorising statute or programme. Recorded "
                    f"as not stated, NOT inferred from the entity class.")
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")

    print(f"{len(by_uid)} entities -> {os.path.relpath(OUT, ROOT)}")
    print(f"  with an authorising basis in their own words or IHS's: {n_auth}")
    print(f"  with a service area / catchment:                       {n_area}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
