#!/usr/bin/env python3
"""
Cedar Press - 76: classify Schedule I grantees into Native-org candidates.

Input : data/raw/external/philanthropy/schedule_i_grantees_2026-08-06.csv
        data/raw/external/philanthropy/grantee_ein_resolved_2026-08-06.csv
        data/raw/external/philanthropy/grantee_missions_2026-08-06.csv  (opt)
Output: review/agent_native_org_candidates_philanthropy_2026-08-06.csv

WHAT A GRANTEE IS AND IS NOT
----------------------------
A grantee of a tribal or Native funder is NOT automatically a Native
organisation. Tribes and Native foundations give to hospitals, universities,
food banks and disaster relief that are not Native at all. So the grant is a
LEAD, never a ruling. Every NATIVE_ORG here rests on a retrieved document about
the ORGANISATION, not on the fact that Native money reached it.

Ownership and service are kept in separate fields of the note
(`ownership=` / `service=`) because they are different facts and the project
has a standing rule against collapsing them.

THE TRAPS THIS ENCODES (all already paid for)
---------------------------------------------
* 282 place-name coincidences were withdrawn from the nonprofit layer on
  2026-08-05 - Umatilla Electric Cooperative, Yavapai Community Hospital,
  Legacy Traditional School-Peoria. A place name is not evidence.
* `funnel_stage = verified_strict` in np_orgs.csv is a strict NAME match. It
  is NOT verified Native status and is never treated as such here.
* Heritage groups self-identifying as tribes are evidence AGAINST, not for.
* Northeast/Northwest "Comanche Tribe" are International Comanche Society
  chapters - Piper Comanche aircraft owners. `Sioux Tribe 128` is an Improved
  Order of Red Men lodge. Golden Comanche is a Mardi Gras krewe.
* REFUSE_ALONE tokens (creek, cherokee, colorado, ojibwe, shawnee, oneida,
  apache, central, eagle, river, mountain, santa) cannot carry a ruling by
  themselves.

Rule 8: the spine resolver is imported, never re-implemented.
"""

import csv
import importlib.util
import re
import sys
from collections import defaultdict
from pathlib import Path

CEDAR = Path(r"C:\Users\esm247\Desktop\Cedar Press")
RAW = CEDAR / "data" / "raw" / "external" / "philanthropy"
CLEAN = CEDAR / "data" / "clean"
SPINE = CEDAR / "data" / "spine"
OUT = CEDAR / "review" / "agent_native_org_candidates_philanthropy_2026-08-06.csv"

_spec = importlib.util.spec_from_file_location(
    "resolver", CEDAR / "code" / "33_apply_party_rulings.py")
_res = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_res)
resolve_entity, norm = _res.resolve_entity, _res.norm


def read(p):
    if not Path(p).exists():
        return []
    with open(p, encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


# --- Native identifiers -----------------------------------------------------
# Multi-word or orthographically distinctive. A single ambiguous word is never
# on this list.
STRONG = [
    "american indian", "native american", "native peoples", "indigenous",
    "indian tribe", "indian community", "indian center", "indian centre",
    "indian education", "indian health", "indian housing", "indian college",
    "indian school", "indian nation", "indian reservation", "indian country",
    "tribal", "intertribal", "inter-tribal", "inter tribal",
    "tribe of", "tribes of", "band of", "pueblo of", "nation of indians",
    "rancheria", "reservation",
    "alaska native", "alaskan native", "inupiat", "inupiaq", "yupik",
    "yup'ik", "athabascan", "athabaskan", "tlingit", "haida", "tsimshian",
    "aleut", "unangan", "alutiiq", "sugpiaq", "gwich'in", "koyukon",
    "traditional council", "village council", "native village",
    "tribal council", "tribal government",
    "native hawaiian", "kanaka maoli", "kanaka oiwi", "hawaiian homestead",
    "aloha aina", "papa ola", "haumana",
    "navajo nation", "dine", "lakota", "dakota", "nakota", "anishinaabe",
    "ojibwe nation", "haudenosaunee", "wabanaki", "muscogee nation",
    "first nations", "aboriginal", "powwow", "pow wow", "wampum",
    "sovereign nation", "tribally",
]
# Named here because the brief names them: these must never carry a ruling on
# their own.
REFUSE_ALONE = {"creek", "cherokee", "colorado", "ojibwe", "shawnee",
                "oneida", "apache", "central", "eagle", "river", "mountain",
                "santa",
                # added here, from a measured miss on this population:
                # "Dakota Rural Action" (SD) and "North Dakota Community
                # Foundation" (ND) both carry "dakota" from the STATE.
                "dakota"}
# Civic / place descriptors that fired the 282 withdrawals.
CIVIC = ["county", "chamber of commerce", "kiwanis", "rotary",
         "electric cooperative", "electric membership", "school district",
         "historical society", "booster", " pta", " pto",
         "community college", "credit union", "fire department",
         "improved order of red men", "shrine", "masonic", "elks",
         "lions club", "little league", "country club", "golf",
         "comanche society", "krewe"]
TRIBAL_IRC = {"TRIBE", "TRIBAL", "7871", "IRC 7871", "TRIBE 7871",
              "GOVERNMENT", "TRIBAL GOVT", "TRIBAL GOVERNMENT"}


# State names that contain a tribal word. "North Dakota Community Foundation"
# and "Dakota Rural Action" are the 283rd and 284th place-name coincidences
# waiting to happen; the state name must be removed before tokenising, exactly
# as "Umatilla County" had to be.
STATE_MASK = re.compile(r"\b(north|south) dakota\b|\bnew mexico\b|"
                        r"\bindiana\b|\bindianapolis\b", re.I)


def hits(name):
    """Match on WORD BOUNDARIES, not substrings.

    An earlier version used `token in name` and matched "reservation" inside
    "PRESERVATION", promoting `PAWNEE SEED PRESERVATION SOCIETY` and
    `TATANKA OYATE PRESERVATION SOCIETY` on a syllable. Substring matching on
    a name is how a place-name filter turns into a place-name generator.
    """
    n = " " + norm(STATE_MASK.sub(" ", name)) + " "
    out = []
    for t in STRONG:
        tn = norm(t)
        if re.search(r"(?<![a-z0-9])" + re.escape(tn) + r"(?![a-z0-9])", n):
            out.append(t)
    return out


def civic_hits(name):
    n = " " + norm(name) + " "
    return [t for t in CIVIC if norm(t) in n]


def main():
    grants = read(RAW / "schedule_i_grantees_2026-08-06.csv")
    resolved = {r["ein"]: r for r in read(
        RAW / "grantee_ein_resolved_2026-08-06.csv")}
    missions = {r["ein"]: r for r in read(
        RAW / "grantee_missions_2026-08-06.csv")}
    spine = read(SPINE / "cedar_entity_spine.csv")
    np_orgs = {r["EIN"]: r for r in read(CLEAN / "np_orgs.csv")}

    agg = defaultdict(lambda: {"rows": [], "funders": set(), "usd": 0.0,
                               "purposes": set(), "years": set()})
    for r in grants:
        a = agg[r["grantee_ein"]]
        a["rows"].append(r)
        a["funders"].add(r["funder_name"])
        a["purposes"].add(r["purpose_as_filed"])
        a["years"].add(r["tax_year"])
        try:
            a["usd"] += float(r["cash_grant_usd"] or 0)
        except ValueError:
            pass

    out = []
    for ein, a in sorted(agg.items(), key=lambda kv: -kv[1]["usd"]):
        rec = resolved.get(ein, {})
        name = (rec.get("name") or "").strip()
        filed = max((r["grantee_name_as_filed"] for r in a["rows"]), key=len)
        best = name or filed
        st = (rec.get("state") or a["rows"][0]["grantee_state"] or "").strip()
        city = (rec.get("city") or a["rows"][0]["grantee_city"] or "").strip()
        irc = {r["irc_section_as_filed"].upper().strip() for r in a["rows"]}
        is_tribal_irc = bool(irc & TRIBAL_IRC)

        tid, cname, how = resolve_entity(best, spine)
        if not tid and name and filed and norm(name) != norm(filed):
            tid, cname, how = resolve_entity(filed, spine)
        spine_state = ""
        if tid:
            for _r in spine:
                if _r["tribe_id"] == tid:
                    spine_state = (_r.get("state") or "").strip()
                    break

        h, c = hits(best), civic_hits(best)
        # A hit that is ONLY a refuse-alone word cannot carry the ruling. This
        # previously read `(not h) and toks & REFUSE_ALONE`, which is the
        # opposite test: it fired when there was no hit at all and never fired
        # when the single hit WAS the ambiguous word.
        only_refusable = bool(h) and all(norm(t) in REFUSE_ALONE for t in h)

        out.append({
            "ein": ein, "name": best, "name_as_filed": filed,
            "state": st, "city": city,
            "ntee": rec.get("ntee_code") or "",
            "revenue": rec.get("revenue_amount") or "",
            "pp_url": rec.get("source_url") or "",
            "in_spine": tid or "", "spine_name": cname or "",
            "spine_state": spine_state,
            "spine_how": how,
            "funders": sorted(a["funders"]), "usd": a["usd"],
            "purposes": sorted(p for p in a["purposes"] if p),
            "years": sorted(a["years"]),
            "sched_i_url": a["rows"][0]["source_url"],
            # The funder whose filing that URL actually is. Naming a
            # DIFFERENT funder next to a URL would be a citation that
            # does not check out.
            "revealed_by": a["rows"][0]["funder_name"],
            "irc_as_filed": sorted(irc), "tribal_irc": is_tribal_irc,
            "native_tokens": h, "civic_tokens": c,
            "only_refusable": only_refusable,
            "mission": (missions.get(ein) or {}).get("mission", ""),
            "mission_url": (missions.get(ein) or {}).get("source_url", ""),
            "np_orgs_tier": (np_orgs.get(ein) or {}).get("confidence_tier", ""),
            "np_orgs_stage": (np_orgs.get(ein) or {}).get("funnel_stage", ""),
        })

    # Triage report - what still needs individual evidence.
    need = [r for r in out if not r["in_spine"] and not r["native_tokens"]
            and not r["tribal_irc"]]
    print(f"grantee EINs        {len(out)}")
    print(f"  spine match       {sum(1 for r in out if r['in_spine'])}")
    print(f"  filed as TRIBE    {sum(1 for r in out if r['tribal_irc'])}")
    print(f"  Native token      {sum(1 for r in out if r['native_tokens'])}")
    print(f"  civic token       {sum(1 for r in out if r['civic_tokens'])}")
    print(f"  needs evidence    {len(need)}")
    Path(RAW / "_need_mission_eins.txt").write_text(
        "\n".join(r["ein"] for r in need), encoding="utf-8")
    import json
    Path(RAW / "_triage_2026-08-06.json").write_text(
        json.dumps(out, indent=1, default=list), encoding="utf-8")
    print(f"-> {RAW / '_triage_2026-08-06.json'}")


if __name__ == "__main__":
    main()
