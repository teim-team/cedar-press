#!/usr/bin/env python3
"""
Cedar Press - 129: build the review queue WITH a guess and a confidence.

WHAT ELIJAH ASKED FOR
---------------------
"you need to update the website for what you think the entity is and your %
unless you have no clue ... i think it makes more sense to say like ANC (click)
then enter the name of it ... have a running total of how much entities/dollars
this resolves"

So every card needs: a proposed entity, a proposed CLASS (ANC / NHO / TRIBE /
INDIVIDUAL), a confidence number, and the dollars it settles.

HOW THE CONFIDENCE IS DERIVED - it is a score, not a probability
---------------------------------------------------------------
A percentage implies precision we do not have, so it is computed from named
signals and the REASON is shown on the card. Nothing is invented.

    95  ultimate-parent UEI resolves to an entity already in the ledger
    85  spine resolver returns an exact canonical-name match
    70  a distinctive spine token appears in the legal name
        (e.g. "TEPA" -> Tepa companies; tokens <5 chars are excluded unless
         they are known short tribal names, because "UTE" would match "COMPUTER")
    55  a single unambiguous ownership flag and a corporate-form name
    35  only individual-Native flags - likely an individual, not an entity
     0  no signal - the card says "no read" rather than guessing

The class guess comes from the SPINE's own `entity_class` when a match is
found, never from the flags, because the flags are a firm's self-certification
and are demonstrably inconsistent (Goldbelt Raven, an ANC subsidiary, certifies
alaskanNativeCorporationOwnedFirm = NO).

    py -3 code/129_build_review_queue.py
"""

import csv
import importlib.util
import json
import re
import sys
from collections import Counter
from pathlib import Path

CEDAR = Path(r"C:\Users\esm247\Desktop\Cedar Press")
CLEAN = CEDAR / "data" / "clean"
REVIEW = CEDAR / "review"
SPINE = CEDAR / "data" / "spine" / "cedar_entity_spine.csv"
OUT = CEDAR / "data" / "interim" / "review_queue.json"
REMOVED = CEDAR / "review" / "_already_ruled_removals" / \
    "129_review_queue_already_ruled.csv"

csv.field_size_limit(min(sys.maxsize, 2**31 - 1))

# THE QUEUE MUST NOT ASK ABOUT A SUBJECT HE HAS ALREADY RULED.
# Added 2026-08-26. The 2026-08-12 Schedule I queue asked about 30 EINs
# already ruled tier X, including UNITED WAY OF THE GREATER CHIPPEWA VALLEY -
# the case the whole tier-inheritance rule was built on. Being re-shown an
# entity you have adjudicated is the complaint the owner raised that day.
# The subtraction lives in ONE place, `code/cedar_review_queue.py`, so every
# queue writer gets it and none of them re-invents the policy; it filters on
# the ruling's OUTCOME, never its STATUS.
sys.path.insert(0, str(CEDAR / "code"))
import cedar_review_queue as RQ                                # noqa: E402

# Short but distinctive Native names. Genericness, not length, is the test -
# Zuni, Hopi, Crow and Ute are 3-4 chars and perfectly distinctive.
SHORT_OK = {"zuni", "hopi", "crow", "ute", "sac", "fox", "yurok", "hoopa",
            "makah", "lummi", "quinault", "tlingit", "haida", "aleut", "inupiat",
            "koniag", "chugach", "doyon", "calista", "bristol", "ahtna", "sealaska"}
PLACE_SUFFIXES = {"falls", "city", "county", "springs", "heights", "valley",
                  "park", "beach", "ridge", "lake", "lakes", "river", "hills",
                  "junction", "township", "borough", "village", "plains",
                  "bay", "harbor", "island"}
STOP = {"the", "of", "and", "inc", "llc", "corporation", "company", "tribe",
        "tribal", "nation", "native", "indian", "indians", "alaska", "alaskan",
        "village", "community", "band", "pueblo", "council", "group",
        "enterprises", "enterprise", "holdings", "corp", "incorporated", "ltd",
        "limited", "joint", "venture", "jv", "development", "management",
        # Added 2026-08-12, THIRD occurrence of the same bad match. The guard
        # tests whether the SPINE name is fully covered by the candidate. That
        # only works if the spine name has a DISTINCTIVE token left after this
        # list. "Native Health" reduced to just {"health"} - because "native"
        # was here and "health" was not - so it was "fully covered" by DENVER
        # INDIAN HEALTH & FAMILY SERVICES and matched at 85%. Same for Alaska
        # Native Tribal Health Consortium.
        #
        # A spine name made ENTIRELY of these words has nothing to match on,
        # and weak_containment() correctly refuses it.
        "services", "service", "health", "healthcare", "housing", "authority",
        "center", "centre", "foundation", "institute", "association",
        "society", "school", "college", "university", "fund", "trust",
        "program", "programs", "project", "projects", "agency", "office",
        "department", "board", "commission", "systems", "solutions",
        "resources", "consortium", "partnership", "alliance", "network"}


def load(p):
    p = Path(p)
    if not p.exists():
        return []
    with open(p, encoding="utf-8-sig", errors="replace", newline="") as fh:
        return list(csv.DictReader(fh))


def norm(s):
    return re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).strip()


_dom_spec = importlib.util.spec_from_file_location(
    "cedar_domain", CEDAR / "code" / "cedar_domain.py")
_dom = importlib.util.module_from_spec(_dom_spec)
_dom_spec.loader.exec_module(_dom)
NAME_TRAPS = _dom.NAME_TRAPS      # one list, project-wide


def load_module(name, filename):
    spec = importlib.util.spec_from_file_location(name, CEDAR / "code" / filename)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


CLASS_MAP = {
    "ANRC": "ANC", "ANVC": "ANC", "ANC": "ANC",
    "NHO": "NHO", "NHVO": "NHO",
    "TRBF": "TRIBE", "TRBS": "TRIBE", "AKNF": "TRIBE", "ITO": "TRIBE",
    "BIE": "TRIBE", "UIO": "TRIBE", "CDFI": "TRIBE",
}


def klass(tribe_id, entity_class):
    ec = (entity_class or "").upper()
    if "ALASKA NATIVE" in ec or "ANC" in ec:
        return "ANC"
    if "HAWAII" in ec or "NHO" in ec:
        return "NHO"
    return CLASS_MAP.get((tribe_id or "").split("-")[0], "TRIBE")



def weak_containment(spine_name, candidate, how, tok=None):
    """Reject a containment match only when it does NOT cover the spine name.

    TWO WRONG VERSIONS PRECEDED THIS ONE, both measured 2026-08-12.

    v1 excluded only stopwords and short words. That let DENVER INDIAN HEALTH &
    FAMILY SERVICES match the spine entity "Native Health" on the single shared
    word "health" - 6 characters, so the length test passed it.

    v2 required a shared token UNIQUE to one spine entity. That was too strict
    in the other direction and killed correct matches: "NAVAJO NATION TRIBAL
    GOVERNMENT, THE" -> Navajo was rejected because "navajo" also appears in
    Ramah Navajo and Alamo Navajo. It threw away the eight LARGEST tribes in the
    assistance crosswalk - Navajo, Oglala Sioux, Turtle Mountain, Fort Peck,
    Lummi, White Mountain Apache, Rosebud, Salish and Kootenai.

    The real discriminator is COVERAGE OF THE SPINE NAME:

        "Navajo"        vs "NAVAJO NATION TRIBAL GOVERNMENT"  -> 1/1 covered  KEEP
        "Native Health" vs "DENVER INDIAN HEALTH & FAMILY..."  -> 1/2 covered  DROP

    A containment match is sound when every distinctive token of the SPINE
    entity's name appears in the candidate. Matching half a spine name proves
    nothing; matching all of it is what containment is supposed to mean.
    """
    if "contain" not in (how or "").lower():
        return False
    cand = set(norm(candidate).split())
    spine_tokens = [w for w in norm(spine_name).split()
                    if w not in STOP and (len(w) >= 4 or w in SHORT_OK)]
    if not spine_tokens:
        return True                      # nothing distinctive to match on
    return not all(w in cand for w in spine_tokens)

def token_hit(name, tok):
    """Find a distinctive spine token in a name - respecting NAME_TRAPS.

    The containment guard alone is not enough. Blocking the resolver's
    containment path just pushes the same bad match down to the token path,
    which is exactly what happened to "Boys & Girls Clubs of Wichita Falls":
    containment refused, token path matched "wichita" at 70% anyway.

    NAME_TRAPS is the project's list of names that must never link on their
    own - every term in it cost a real misattribution. The token path has to
    honour it, and the place-suffix rule, or the guard is theatre.
    """
    words = norm(name).split()
    for i, w in enumerate(words):
        if w not in tok:
            continue
        if w in NAME_TRAPS:
            continue
        if i + 1 < len(words) and words[i + 1] in PLACE_SUFFIXES:
            continue
        return tok[w]
    return None



def main():
    m33 = load_module("m33", "33_apply_party_rulings.py")
    spine = load(SPINE)
    ledger = load(CLEAN / "cedar_identifier_ledger_final.csv")

    by_id = {}
    for r in ledger:
        v = (r.get("identifier") or "").strip().upper()
        if v and r.get("canonical_name"):
            by_id.setdefault(v, (r["canonical_name"], r.get("tribe_id", ""),
                                 r.get("entity_class", "")))
    # distinctive token -> spine entity
    tok = {}
    for r in spine:
        cn = r.get("canonical_name") or ""
        for w in norm(cn).split():
            if w in STOP:
                continue
            if len(w) < 5 and w not in SHORT_OK:
                continue
            tok.setdefault(w, []).append(r)
    tok = {k: v[0] for k, v in tok.items() if len(v) == 1}   # unique tokens only

    items = []

    # ---- 1. ESM contract discovery ---------------------------------------
    esm = [r for r in load(REVIEW / "esm_native_entity_candidates_2026-08-12.csv")
           if r.get("already_in_ledger") == "NO"
           and int(r.get("ownership_flag_rows") or 0) > 0]
    for r in esm:
        name = (r.get("legal_name") or "").strip()
        pu = (r.get("ultimate_parent_uei") or "").strip().upper()
        pn = (r.get("ultimate_parent_name") or "").strip()
        guess = gclass = why = ""
        conf = 0

        known = by_id.get(pu)
        if known and norm(known[0]) != norm(name):
            guess, gclass = known[0], klass(known[1], known[2])
            conf, why = 95, "ultimate-parent UEI is already in our ledger"
        else:
            tid, cname, how = m33.resolve_entity(name, spine)
            if tid and not weak_containment(cname, name, how, tok):
                guess = cname
                sp = next((s for s in spine if s["tribe_id"] == tid), {})
                gclass = klass(tid, sp.get("entity_class"))
                conf, why = 85, f"spine resolver matched ({how})"
            else:
                hit = token_hit(name, tok)
                if hit:
                    guess = hit["canonical_name"]
                    gclass = klass(hit["tribe_id"], hit.get("entity_class"))
                    conf, why = 70, "a distinctive name token matches this entity"
                elif pn and norm(pn) != norm(name):
                    guess, gclass = pn, ""
                    conf, why = 55, "reports this ultimate parent, unknown to us"
                elif int(r.get("individual_native_flag_rows") or 0) > 0 and \
                        int(r.get("ownership_flag_rows") or 0) <= 1:
                    conf, why = 35, "only individual-Native flags - may be a person"
                    gclass = "INDIVIDUAL_NATIVE"

        flags = [f.split("=")[0] for f in (r.get("flags_asserted") or "").split("; ") if f]
        items.append({
            "id": "ESM:" + (r.get("uei") or r.get("recipient_key")),
            "src": "Contract discovery",
            "name": name,
            "uei": r.get("uei", ""), "cage": "", "duns": r.get("duns", ""),
            "dollars": float(r.get("obligations_usd") or 0),
            "metric": "$%.1fM · %s txns · FY%s–%s" % (
                float(r.get("obligations_usd") or 0) / 1e6,
                r.get("n_transactions"), r.get("fy_min"), r.get("fy_max")),
            "ctx": "Self-certifies: " + ", ".join(flags[:4]),
            "ctx2": ("Ultimate parent UEI " + pu) if pu else "No ultimate parent reported",
            "guess": guess, "gclass": gclass, "conf": conf, "why": why,
            "grade": "Self-certified — never auto tier A",
        })

    # ---- 2. Elijah's own redirects that did not resolve -------------------
    for r in load(REVIEW / "ruling_redirect_unresolved_2026-08-12.csv"):
        owner = (r.get("ruled_owner") or "").strip()
        rid = r.get("review_id", "")
        tid, cname, how = m33.resolve_entity(owner, spine)
        if tid:
            sp = next((s for s in spine if s["tribe_id"] == tid), {})
            guess, gclass, conf = cname, klass(tid, sp.get("entity_class")), 85
            why = "your ruling now resolves (" + how + ")"
        else:
            hit = token_hit(owner, tok)
            if hit:
                guess = hit["canonical_name"]
                gclass = klass(hit["tribe_id"], hit.get("entity_class"))
                conf, why = 70, "closest spine entity to the name you gave"
            else:
                guess, gclass, conf = owner, "", 40
                why = "the name you gave, which the spine does not hold"
        items.append({
            "id": "RDR:" + rid, "src": "Your unresolved ruling",
            "name": r.get("entity_name") or r.get("current_canonical_name") or owner,
            "uei": rid.split(":")[-1] if rid.startswith("UEI") else "",
            "cage": rid.split(":")[-1] if rid.startswith("CAGE") else "",
            "duns": "", "dollars": 0.0,
            "metric": "currently tier " + (r.get("current_tier") or "?"),
            "ctx": 'You ruled the owner is: "' + owner + '"',
            "ctx2": "Spine could not resolve it (" + (r.get("resolver_reason") or "") +
                    "), so the row was left untouched.",
            "guess": guess, "gclass": gclass, "conf": conf, "why": why,
            "grade": "Your ruling — blocked on a spine gap",
        })

    # ---- 3. deal parties --------------------------------------------------
    for r in load(REVIEW / "deals_party_unmatched_2026-08-12.csv"):
        party = (r.get("native_party") or "").strip()
        tid, cname, how = m33.resolve_entity(party, spine)
        if tid:
            sp = next((s for s in spine if s["tribe_id"] == tid), {})
            guess, gclass, conf = cname, klass(tid, sp.get("entity_class")), 85
            why = "spine resolver matched (" + how + ")"
        else:
            hit = token_hit(party, tok)
            if hit:
                guess = hit["canonical_name"]
                gclass = klass(hit["tribe_id"], hit.get("entity_class"))
                conf, why = 70, "a distinctive name token matches this entity"
            else:
                guess = gclass = why = ""
                conf = 0
        items.append({
            "id": "DEAL:" + party, "src": "Unlinked deal party", "name": party,
            "uei": "", "cage": "", "duns": "", "dollars": 0.0,
            "metric": (r.get("n_deals") or "?") + " deal(s) unlinked",
            "ctx": "Named as a deal party but resolves to no spine entity.",
            "ctx2": "May be a spine gap rather than an unknown entity.",
            "guess": guess, "gclass": gclass, "conf": conf, "why": why,
            "grade": "Needs spine resolution",
        })


    # ---- 4. Schedule I grant recipients (IRS 990) -------------------------
    # Only those worth a human decision: named on a filed Schedule I, sizeable,
    # and not already resolved. Capped so the queue stays answerable.
    sched = load(REVIEW / "np_schedule_i_recipients_2026-08-12.csv")
    sched = [r for r in sched if not (r.get("proposed_entity_id") or "").strip()]
    def _amt(r):
        try:
            return float((r.get("total_cash_grant_usd") or 0) or 0)
        except ValueError:
            return 0.0
    sched.sort(key=_amt, reverse=True)
    for r in sched[:90]:
        nm = (r.get("recipient_name_as_filed") or "").strip()
        tid, cname, how = m33.resolve_entity(nm, spine)
        if tid and not weak_containment(cname, nm, how, tok):
            guess, gclass, conf = cname, klass(tid, ""), 85
            why = f"spine resolver matched ({how})"
        else:
            hit = token_hit(nm, tok)
            if hit:
                guess = hit["canonical_name"]
                gclass = klass(hit["tribe_id"], hit.get("entity_class"))
                conf, why = 70, "a distinctive name token matches this entity"
            else:
                guess = gclass = why = ""
                conf = 0
        items.append({
            "id": "SCHI:" + (r.get("review_id") or r.get("recipient_ein") or nm),
            "src": "990 Schedule I recipient", "name": nm,
            "uei": "", "cage": "", "duns": r.get("recipient_ein", ""),
            "dollars": _amt(r),
            "metric": "$%.2fM received · %s grant row(s) · %s funder(s) · %s" % (
                _amt(r)/1e6, r.get("n_grant_rows"), r.get("n_funders"),
                r.get("tax_years") or ""),
            "ctx": "Named as a grant recipient on a filed Form 990 Schedule I.",
            "ctx2": "Funders: " + (r.get("funders") or "")[:110],
            "guess": guess, "gclass": gclass, "conf": conf, "why": why,
            "grade": "Recipient of Native-connected grant money — is IT Native?",
        })

    # ---- 5. resource revenue: statutory funds needing a ruling ------------
    # Only the tier-B funds. The 127 already resolved need no decision, and the
    # 172 refusals (individual headright holders, multi-party classes) are
    # deliberate refusals - queueing them would ask Elijah to overturn a rule.
    for r in load(REVIEW / "resource_revenue_entity_proposals_2026-08-12.csv"):
        if (r.get("recipient_class") or "") != "STATUTORY_FUND":
            continue
        nm = (r.get("recipient_entity_name") or "").strip()
        try:
            amt = float(r.get("amount_usd") or 0)
        except ValueError:
            amt = 0.0
        hit = token_hit(nm, tok)
        items.append({
            "id": "RESF:" + (r.get("resource_revenue_event_id") or nm),
            "src": "Resource fund recipient", "name": nm,
            "uei": "", "cage": "", "duns": "", "dollars": amt,
            "metric": "$%.2fM · %s · %s" % (
                amt/1e6, r.get("revenue_type") or "", r.get("payment_date") or ""),
            "ctx": "A state-created fund receiving resource revenue.",
            "ctx2": "Source: " + (r.get("source_system") or ""),
            "guess": hit["canonical_name"] if hit else "",
            "gclass": klass(hit["tribe_id"], hit.get("entity_class")) if hit else "",
            "conf": 55 if hit else 0,
            "why": "the fund's name points at this entity, but the statute was "
                   "not read" if hit else "",
            "grade": "Which entity is the beneficiary? Never asserted at A.",
        })


    # ---- 6. administrative appeal parties (IBIA/IBLA) ---------------------
    for r in load(REVIEW / "admin_appeal_entity_link_candidates.csv")[:70]:
        nm = (r.get("party_name") or "").strip()
        cand = (r.get("candidate_entity") or "").strip()
        try:
            nrows = int(r.get("n_party_rows") or 0)
        except ValueError:
            nrows = 0
        items.append({
            "id": "APPEAL:" + nm, "src": "Appeal party (IBIA/IBLA)", "name": nm,
            "uei": "", "cage": "", "duns": "", "dollars": 0.0,
            "metric": f"{nrows} appeal row(s)",
            "ctx": "A party to an Interior administrative appeal.",
            "ctx2": (r.get("question") or "Is this a Native entity, and which?")[:150],
            "guess": cand, "gclass": "",
            "conf": 70 if cand else 0,
            "why": ("proposed by " + (r.get("resolve_method") or "resolver")) if cand else "",
            "grade": "Appellant or respondent — opposition/outcome layer",
        })

    # ---- 7. gaming property geocode conflicts -- REMOVED 2026-08-12 ----
    # Visual inspection caught two defects, both fatal for this queue:
    #
    # 1. THE BUTTONS DO NOT FIT THE QUESTION. A location conflict asks "which
    #    source is right?" The ruling vocabulary is Tribe/ANC/NHO/Individual/
    #    Not Native/Hold, which answers "what class of entity is this?" Elijah
    #    made exactly this complaint about collision cards: a card that cannot
    #    be answered with the controls it offers is worse than no card.
    #
    # 2. MOST ARE NOT CONFLICTS. Wind Creek Atmore appeared twice with the SAME
    #    address - "303 Poarch Road" / "303 Poarch Rd" / "303 POARCH RD" -
    #    differing by ~0.05 degrees of geocoder precision.
    #
    # The genuine cases (Northern Edge Navajo: Fruitland NM address, Roswell
    # coordinate, 492 km apart; 173 of 422 are NIGC disagreeing with itself)
    # need a map-and-two-buttons interface, not this one. They stay in
    # review/gaming_locations_geocode_conflicts_2026-08-12.csv.

    # ---- 8. FAC Single Audit auditees --------------------------------------
    for r in load(REVIEW / "fac_unresolved_auditees_2026-08-12.csv")[:55]:
        nm = (r.get("auditee_name") or "").strip()
        hit = token_hit(nm, tok)
        items.append({
            "id": "FAC:" + (r.get("auditee_ein") or nm),
            "src": "Single Audit auditee", "name": nm,
            "uei": "", "cage": "", "duns": r.get("auditee_ein", ""),
            "dollars": 0.0,
            "metric": f"{r.get('entity_type','')} · {r.get('auditee_state','')} · FY{r.get('audit_year','')}",
            "ctx": "Filed a federal Single Audit; not resolved to the spine.",
            "ctx2": (r.get("reason") or "")[:140],
            "guess": hit["canonical_name"] if hit else "",
            "gclass": klass(hit["tribe_id"], hit.get("entity_class")) if hit else "",
            "conf": 70 if hit else 0,
            "why": "a distinctive spine token matches this name" if hit else "",
            "grade": "Audited entity — gaming transfers and participation expense live here",
        })

    # ---- 9. NRC external participants --------------------------------------
    for r in load(REVIEW / "nrc_entity_link_candidates.csv"):
        nm = (r.get("external_participant") or "").strip()
        cand = (r.get("candidate_entity") or "").strip()
        items.append({
            "id": "NRC:" + nm, "src": "NRC meeting participant", "name": nm,
            "uei": "", "cage": "", "duns": "", "dollars": 0.0,
            "metric": f"{r.get('n_participant_rows','?')} meeting row(s)",
            "ctx": "Named as an external participant in an NRC public meeting.",
            "ctx2": (r.get("question") or "")[:150],
            "guess": cand, "gclass": "",
            "conf": 70 if cand else 0,
            "why": ("proposed by " + (r.get("resolve_method") or "resolver")) if cand else "",
            "grade": "Nuclear/uranium/waste docket — regulatory contact",
        })

    # ---- 10. BGOV-only attributed prime rows the merge kept ---------------
    # 584 rows the archive has no counterpart for, concentrated FY2017-18 and
    # dominated by joint ventures. A UEI-identity question, not a dollar one.
    seen_jv = set()
    for r in load(REVIEW / "prime_merge_bgov_only_attributed_2026-08-12.csv"):
        nm = (r.get("awardee_name") or "").strip()
        if nm in seen_jv:
            continue
        seen_jv.add(nm)
        if len(seen_jv) > 40:
            break
        items.append({
            "id": "BGOV:" + (r.get("awardee_uei") or nm),
            "src": "BGOV-only prime awardee", "name": nm,
            "uei": r.get("awardee_uei", ""), "cage": r.get("cage_code", ""),
            "duns": "", "dollars": 0.0,
            "metric": f"FY{r.get('fiscal_year','')} · {r.get('contract_number','')}",
            "ctx": "In the BGOV extract with no counterpart in the federal archive.",
            "ctx2": "Parent on file: " + (r.get("parent_name") or "(none)")[:90],
            "guess": (r.get("parent_name") or "").strip(),
            "gclass": "", "conf": 55 if (r.get("parent_name") or "").strip() else 0,
            "why": "the extract names this parent" if (r.get("parent_name") or "").strip() else "",
            "grade": "Often a joint venture — a UEI identity question",
        })


    # ---- 11. assistance legacy tribe ids that did not map -----------------
    # These are the do-file's OWN attributions - the row is already known to be
    # this tribe. What is missing is only the Cedar id. So the card must show
    # what the spine holds NEARBY, because the answer is usually sitting there
    # under a slightly different string.
    #
    # Diagnosed causes, measured: the resolver prefers a tribal COLLEGE over the
    # tribe (Confederated Salish and Kootenai -> Salish Kootenai College);
    # a parent plus its constituent bands reads as "ambiguous" (Shoshone-Bannock
    # plus its two Fort Hall bands); an abbreviation misses (FT MC DOWELL vs
    # Fort McDowell); or the tribe is genuinely absent from the spine.
    import importlib.util as _ilu
    _sp = _ilu.spec_from_file_location("m33b", CEDAR / "code" / "33_apply_party_rulings.py")
    _m33 = _ilu.module_from_spec(_sp); _sp.loader.exec_module(_m33)

    def _nearby(name, spine, limit=4):
        """Spine entities sharing a distinctive token with the name."""
        want = {w for w in norm(name).split()
                if w not in STOP and (len(w) >= 4 or w in SHORT_OK)}
        out = []
        for r in spine:
            cn = r.get("canonical_name") or ""
            if want & set(norm(cn).split()):
                out.append(f"{cn} [{r.get('entity_class','')[:22]}]")
            if len(out) >= limit:
                break
        return out

    for r in load(REVIEW / "assistance_legacy_id_unresolved_2026-08-12.csv"):
        nm = (r.get("legacy_name_as_filed") or "").strip()
        try:
            nrows = int(r.get("n_rows") or 0)
            usd = float(r.get("obligated_usd") or 0)
        except ValueError:
            nrows, usd = 0, 0.0
        _, _, how = _m33.resolve_entity(nm, spine)
        near = _nearby(nm, spine)
        items.append({
            "id": "ASSTID:" + (r.get("legacy_tribe_id") or nm),
            "src": "Assistance legacy id", "name": nm,
            "uei": "", "cage": "", "duns": r.get("legacy_tribe_id", ""),
            "dollars": usd,
            "metric": "%s rows · $%.1fM · %s" % (
                f"{nrows:,}", usd / 1e6, r.get("top_states") or ""),
            "ctx": "The do-file already attributed these rows to this tribe. "
                   "Only the Cedar id is missing.",
            "ctx2": ("Resolver said: " + (how or "no match") + " · Spine holds nearby: "
                     + ("; ".join(near) if near else "nothing similar")),
            "guess": near[0].split(" [")[0] if near else "",
            "gclass": "", "conf": 55 if near else 0,
            "why": "closest spine entity by a distinctive shared token" if near else "",
            "grade": "Maps a whole tribe's assistance history in one ruling",
        })

    items.sort(key=lambda x: (-x["conf"], -x["dollars"]))

    # SUBTRACT WHAT HE HAS ALREADY RULED, before the file exists.
    n_before = len(items)
    items, dropped, stats = RQ.subtract(items)
    if dropped:
        REMOVED.parent.mkdir(parents=True, exist_ok=True)
        RQ.write_removals(REMOVED, dropped)
    print(f"  already-ruled subtraction: {n_before:,} -> {len(items):,} "
          f"({len(dropped):,} removed)")
    for k, v in sorted(stats.items()):
        if k.startswith("removed_outcome_"):
            print(f"     {k[len('removed_outcome_'):]:<22} {v:>5,}")
    if dropped:
        # NAME them, do not merely count them. A count scrolls past.
        print(f"     the dropped subjects are in "
              f"{REMOVED.relative_to(CEDAR)}, in full, with the outcome and "
              f"the ruling that decided each one. First few:")
        for d in dropped[:5]:
            print(f"       {d.get('id', '?')}  {str(d.get('name'))[:40]:<42}"
                  f"{d.get('removed_outcome')}")
    kept_conflicted = stats.get("kept_conflicted", 0)
    if kept_conflicted:
        print(f"     {kept_conflicted:,} subject(s) KEPT and annotated: he has "
              f"ruled them more than once and the rulings disagree, which is a "
              f"tie only he can break - but the card now says so.")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    json.dump(items, open(OUT, "w", encoding="utf-8"), ensure_ascii=False)

    c = Counter(i["src"] for i in items)
    g = Counter("guess" if i["conf"] else "no read" for i in items)
    print(f"  queue: {len(items)} items  {dict(c)}")
    print(f"  with a proposed entity: {g['guess']}   no read: {g['no read']}")
    print(f"  total dollars in queue: ${sum(i['dollars'] for i in items)/1e6:,.1f}M")
    print(f"  confidence spread: {dict(Counter(i['conf'] for i in items))}")
    print(f"  wrote {OUT.relative_to(CEDAR)}")


if __name__ == "__main__":
    main()
