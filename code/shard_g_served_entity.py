"""SHARD-G: the tribe each institution SERVES - candidates only, never resolved.

A BIE school serves a specific nation, a TCU is chartered by one, a Native CDFI
serves a defined target market. That entity->entity edge is one Cedar does not
carry for this slice. This script records it as EVIDENCE plus a CANDIDATE, and
stops there:

  * `served_entity_name_raw` is the name AS THE SOURCE WRITES IT, with the source
    URL and the sentence or field it came from.
  * `candidate_*` names an existing Cedar entity the raw name may denote, with a
    confidence and the basis for it.
  * `resolved` is "no" on every row. Shard G does not adjudicate identity, does
    not write the spine and does not mint. Resolution is 503/510's job.

EVIDENCE ROUTES, strongest first
  spine_parent          the spine already carries parent_entity_id for this
                        institution (script 73 adjudicated it) - recorded so the
                        edge is visible in one table, marked already_resolved
  charter_sentence      a retrieved sentence says X chartered / established /
                        owns the institution (AIHEC roster, institution's own
                        about page, spine entity_source_quote)
  bie_navajo_field      the BIE school directory's Navajo_Operation field, which
                        states the school is operated within the Navajo Nation
  name_token            the institution's own name carries a tribal name. This is
                        the WEAKEST route and is confidence-graded, never high:
                        "Blackfeet Dormitory" naming the Blackfeet Nation is an
                        inference from a name, not a statement by a source.

Writes only data/staging/institution_registry/served_entity_crosswalk.csv and
data/staging/tribe_harvest/shard_g/_served_state.json.
"""
from __future__ import annotations

import csv, json, re, sys, unicodedata
from collections import defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUTREG = ROOT / "data" / "staging" / "institution_registry"
OUTH = ROOT / "data" / "staging" / "tribe_harvest" / "shard_g"
SPINE = ROOT / "data" / "spine" / "cedar_entity_spine.csv"
EXT = ROOT / "data" / "raw" / "external"
RAW = OUTH / "raw"
TODAY = date.today().isoformat()
csv.field_size_limit(10_000_000)

TRIBAL_CLASSES = {"Federally recognized tribe",
                  "Federally recognized Alaska Native Village",
                  "State-recognized tribe"}
# words that appear in tribal government names but do not identify WHICH one
TRIBE_GENERIC = {"tribe", "tribes", "tribal", "nation", "nations", "band", "bands",
                 "indian", "indians", "community", "communities", "of", "the",
                 "reservation", "rancheria", "colony", "pueblo", "village",
                 "council", "government", "people", "peoples", "confederated",
                 "confederacy", "and", "native", "american", "americans", "group",
                 "california", "oklahoma", "arizona", "montana", "washington",
                 "town", "association", "corporation", "inc"}
INST_GENERIC = {"school", "schools", "day", "boarding", "community", "college",
                "university", "institute", "center", "centre", "dormitory",
                "dorm", "academy", "elementary", "middle", "high", "junior",
                "senior", "jr", "sr", "bank", "credit", "union", "federal",
                "fund", "loan", "funds", "capital", "financial", "development",
                "corporation", "company", "inc", "the", "of", "and", "tribal",
                "indian", "district", "board", "learning", "education"}


def norm(s):
    s = unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode()
    s = s.lower().replace("&", " and ")
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def rows(p, enc="utf-8-sig"):
    with open(p, encoding=enc, newline="") as f:
        return list(csv.DictReader(f))


SLICE = rows(OUTREG / "_slice.csv")
FACTS = rows(OUTREG / "institution_facts.csv")
spine = rows(SPINE)
spine_by_uid = {r["cedar_uid"]: r for r in spine if r.get("cedar_uid")}

# ------------------------------------------------------------ tribal name index
tribes = [r for r in spine if r["entity_class"] in TRIBAL_CLASSES]
print(f"tribal-government entities in spine: {len(tribes)}", file=sys.stderr)

# distinctive n-grams -> list of tribal entities
gram = defaultdict(list)
for t in tribes:
    names = [t["canonical_name"]] + [a for a in (t["aliases"] or "").split("|")
                                     if a.strip()]
    grams = set()
    for nm in names:
        toks = [x for x in norm(nm).split() if x not in TRIBE_GENERIC and len(x) > 2]
        for i in range(len(toks)):
            grams.add(toks[i])
            if i + 1 < len(toks):
                grams.add(toks[i] + " " + toks[i + 1])
            if i + 2 < len(toks):
                grams.add(" ".join(toks[i:i + 3]))
    for g in grams:
        gram[g].append(t)

OUT = []


def emit(inst, raw, rel, url, quote, route, cand=None, conf="", basis="",
         resolved="no"):
    OUT.append({
        "cedar_uid": inst["cedar_uid"], "tribe_id": inst["tribe_id"],
        "canonical_name": inst["canonical_name"],
        "entity_class": inst["entity_class"],
        "served_entity_name_raw": raw, "relationship": rel,
        "evidence_route": route, "source_url": url, "source_quote": quote[:700],
        "candidate_cedar_uid": (cand or {}).get("cedar_uid", ""),
        "candidate_tribe_id": (cand or {}).get("tribe_id", ""),
        "candidate_canonical_name": (cand or {}).get("canonical_name", ""),
        "candidate_entity_class": (cand or {}).get("entity_class", ""),
        "match_confidence": conf, "match_basis": basis,
        "resolved": resolved, "captured_date": TODAY,
    })


CHARTER = re.compile(
    r"([A-Z][\w''.\-]*(?:\s+(?:of|the|and|de|du)\s+|\s+)?(?:[A-Z][\w''.\-]*\s*){0,6})"
    r"\s+(?:chartered|established|founded|created|owns|operates|governs)\b", re.M)
CHARTERED_BY = re.compile(
    r"(?:chartered|established|founded|created|owned|operated|governed)\s+by\s+"
    r"(?:the\s+)?([A-Z][\w''.\-]*(?:\s+[A-Z][\w''.\-]*){0,6})")

n_spine_parent = n_charter = n_navajo = n_token = 0

for inst in SLICE:
    uid = inst["cedar_uid"]
    sp = spine_by_uid.get(uid, {})
    facts = [f for f in FACTS if f["cedar_uid"] == uid]

    # ---- route 1: the spine already carries an adjudicated parent
    if sp.get("parent_entity_id") and sp.get("parent_entity_name"):
        par = next((r for r in spine
                    if r.get("cedar_entity_id") == sp["parent_entity_id"]
                    or r.get("tribe_id") == sp["parent_entity_id"]), None)
        emit(inst, sp["parent_entity_name"], sp.get("ownership_basis") or "parent",
             sp.get("entity_source_url") or sp.get("source_url")
             or "data/spine/cedar_entity_spine.csv",
             sp.get("entity_source_quote") or
             f"cedar_entity_spine.csv parent_entity_name={sp['parent_entity_name']}; "
             f"hierarchy_basis={sp.get('hierarchy_basis','')}",
             "spine_parent", par, "already_resolved",
             f"spine parent_entity_id={sp['parent_entity_id']}", "yes_in_spine")
        n_spine_parent += 1

    # ---- route 2: a retrieved charter/ownership sentence
    for q, url in [(sp.get("entity_source_quote", ""),
                    sp.get("entity_source_url", "")),
                   *[(f["source_quote"], f["source_url"]) for f in facts
                     if f["attribute"] in ("aihec_membership",)]]:
        if not q:
            continue
        for m in CHARTERED_BY.finditer(q):
            raw = m.group(1).strip(" .,;")
            if len(raw) < 4 or norm(raw) in ("bie", "bureau"):
                continue
            key = norm(raw)
            toks = [x for x in key.split() if x not in TRIBE_GENERIC and len(x) > 2]
            cands = gram.get(" ".join(toks[:3])) or gram.get(" ".join(toks[:2])) \
                or (gram.get(toks[0]) if toks else None) or []
            cand = cands[0] if len(cands) == 1 else None
            conf = "high" if cand else ("ambiguous" if len(cands) > 1 else "no_match")
            emit(inst, raw, "chartered_or_owned_by", url, q, "charter_sentence",
                 cand, conf,
                 f"sentence names '{raw}'; {len(cands)} Cedar tribal entities "
                 f"share its distinctive tokens")
            n_charter += 1

    # ---- route 3: BIE Navajo_Operation field
    nav = next((f for f in facts if f["attribute"] == "bie_navajo_operation"), None)
    # the field's four values are Bureau-Operated/Tribally-Controlled crossed with
    # (Navajo)/(Non-Navajo). Only the "(Navajo)" half says anything about a tribe.
    if nav and "(navajo)" in nav["value"].lower():
        cands = gram.get("navajo") or []
        cand = next((c for c in cands
                     if norm(c["canonical_name"]).startswith("navajo")), None)
        emit(inst, "Navajo Nation", "school operated within the Navajo Nation "
             "(BIE directory Navajo_Operation field)", nav["source_url"],
             nav["source_quote"], "bie_navajo_field", cand,
             "high" if cand else "no_match",
             f"BIE school directory Navajo_Operation = '{nav['value']}'")
        n_navajo += 1

    # ---- route 4: tribal name carried in the institution's own name (WEAK)
    toks = [x for x in norm(inst["canonical_name"]).split()
            if x not in INST_GENERIC and len(x) > 2]
    found = []
    for size in (3, 2, 1):
        for i in range(len(toks) - size + 1):
            g = " ".join(toks[i:i + size])
            if g in gram:
                found.append((size, g, gram[g]))
        if found:
            break
    if found:
        size, g, cands = found[0]
        st = (inst["state"] or "").upper()
        in_state = [c for c in cands if (c.get("state") or "").upper() == st]
        pick, conf, why = None, "", ""
        if len(cands) == 1 and in_state:
            # STATE AGREEMENT IS REQUIRED on this route. Without it the name token
            # route produced Rock Point Community School (AZ) -> Standing Rock
            # (SD), Second Mesa Day School (AZ) -> Mesa Grande (CA) and Circle of
            # Nations (ND) -> Circle (AK). All three die on the state check.
            pick = cands[0]
            conf = "medium" if size >= 2 or len(g) >= 6 else "low"
            why = (f"institution name contains the {size}-token string '{g}', "
                   f"which is distinctive to exactly one Cedar tribal entity, and "
                   f"that entity is in the same state as the institution ({st})")
        elif len(cands) == 1 and not in_state:
            conf = "no_match_state_mismatch"
            why = (f"institution name contains '{g}', distinctive to exactly one "
                   f"Cedar tribal entity - {cands[0]['canonical_name']} "
                   f"({cands[0].get('state','')}) - but the institution is in {st}. "
                   f"Candidate WITHHELD: a shared word across two states is a "
                   f"coincidence, not an affiliation.")
        elif len(in_state) == 1:
            pick = in_state[0]
            conf = "medium" if size >= 2 else "low"
            why = (f"institution name contains '{g}', shared by {len(cands)} Cedar "
                   f"tribal entities, of which exactly one is in {st}")
        else:
            conf = "ambiguous"
            why = (f"institution name contains '{g}', shared by {len(cands)} Cedar "
                   f"tribal entities ({len(in_state)} in {st}): " +
                   "; ".join(c["canonical_name"] for c in cands[:5]))
        emit(inst, g, "tribal name appears in the institution's own name",
             "data/spine/cedar_entity_spine.csv (canonical_name of the institution)",
             f"Institution canonical_name = '{inst['canonical_name']}'. "
             f"INFERENCE FROM A NAME, not a statement by any source.",
             "name_token", pick, conf, why)
        n_token += 1

    if not any(o["cedar_uid"] == uid for o in OUT):
        emit(inst, "", "", "", "no source consulted here names a tribe this "
             "institution serves; recorded as absent rather than guessed",
             "none_found", None, "", "")

fields = ["cedar_uid", "tribe_id", "canonical_name", "entity_class",
          "served_entity_name_raw", "relationship", "evidence_route",
          "source_url", "source_quote", "candidate_cedar_uid",
          "candidate_tribe_id", "candidate_canonical_name",
          "candidate_entity_class", "match_confidence", "match_basis",
          "resolved", "captured_date"]
OUT.sort(key=lambda r: (r["entity_class"], r["canonical_name"],
                        r["evidence_route"]))
with open(OUTREG / "served_entity_crosswalk.csv", "w", encoding="utf-8",
          newline="") as f:
    w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
    w.writeheader()
    w.writerows(OUT)

with_cand = {r["cedar_uid"] for r in OUT if r["candidate_cedar_uid"]}
st = {
    "script": "code/shard_g_served_entity.py", "run_date": TODAY,
    "network_requests": 0,
    "rows": len(OUT), "entities": len({r["cedar_uid"] for r in OUT}),
    "entities_with_a_candidate_tribe": len(with_cand),
    "entities_with_no_evidence": sum(
        1 for u in {r["cedar_uid"] for r in OUT}
        if all(o["evidence_route"] == "none_found"
               for o in OUT if o["cedar_uid"] == u)),
    "by_route": {r: sum(1 for o in OUT if o["evidence_route"] == r)
                 for r in sorted({o["evidence_route"] for o in OUT})},
    "by_confidence": {c: sum(1 for o in OUT if o["match_confidence"] == c)
                      for c in sorted({o["match_confidence"] for o in OUT})},
    "by_class_with_candidate": {
        c: len({r["cedar_uid"] for r in OUT
                if r["entity_class"] == c and r["candidate_cedar_uid"]})
        for c in sorted({r["entity_class"] for r in OUT})},
    "resolved_by_this_script": 0,
}
(OUTH / "_served_state.json").write_text(json.dumps(st, indent=2), encoding="utf-8")
print(f"wrote data/staging/institution_registry/served_entity_crosswalk.csv "
      f"rows={len(OUT)}", file=sys.stderr)
print(json.dumps(st, indent=2))
