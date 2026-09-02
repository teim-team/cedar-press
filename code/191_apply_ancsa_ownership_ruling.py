#!/usr/bin/env python3
"""
191 - Apply the owner's ANCSA ownership ruling to the 334
`ALASKA_VILLAGE_GOVERNMENT_VS_VILLAGE_CORPORATION` one-to-many defects.

    docs/ANCSA_OWNERSHIP_RULING.md, ruled by Elijah 2026-08-26,
    with the rule-4 correction (ANCESTRY, not membership) the same day.

ZERO NETWORK CALLS. This script READS shared tables and writes only its own
files under `review/` and `docs/`. It mutates nothing.
`192_apply_ancsa_resolutions_in_place.py` performs the mutation, from this
script's output, so the DECISION and the WRITE are separable and each is
auditable on its own.

THE RULING, AND HOW EACH CLAUSE BECOMES CODE
--------------------------------------------
1. **Presumption**: an ANCSA operating company is owned by the VILLAGE
   CORPORATION, not the village government.
2. **A village GOVERNMENT never owns an ANC.** Every government-side leg in
   this family is written to the refusal file with the ruling cited. There are
   no exceptions to this clause; rule 3 is not an exception to it, because a
   directly-owned tribal enterprise is not an ANC.
3. **A village government CAN directly own an enterprise** - then it is a
   tribal enterprise attributed to a federally recognized tribe that happens to
   be an Alaska Native village, and it is NOT classed as an ANC.
   **This must be EVIDENCED, never assumed.** Five rungs are accepted
   (`RULE3_RUNGS`). A name resemblance is NOT one of them.
4/5. Shareholding and shared ancestry are ASSOCIATION, never ownership.
   Encoded in `cedar_domain`, not here.

WHY RULE 3 IS NOT VACUOUS - THE CASE THAT PROVES IT
---------------------------------------------------
The owner said rule 3 has "a few real examples", and one is already in this
repository, ruled by him on 2026-08-06 and never applied:

    UEI:FM2KJG6M5363 / NAME:copper river family companies
    ruling = "Native Village of Eyak"      status = SETTLED
    ledger tier_rationale: "owner is Native Village of Eyak, not Kluti Kaah -
    but Native Village of Eyak is not in the spine (ambiguous_core:
    2_spine_entities), so this could not be re-attributed."

**The village is in the spine now** (`AKNF-NVEYAK-00-CHGCCO-CHGCMT`,
"Federally recognized Alaska Native Village"), so the ruling can finally land.
And the same village hosts BOTH shapes at once, which is exactly why the owner
called this tricky:

| family | owner | class |
|---|---|---|
| Copper River Family of Companies | **Native Village of Eyak** (the tribe) | rule 3 |
| EyakTek / Eyak Services / Northtide / Solutions71 / Cordova Central | **Eyak Corporation** (the ANC) | rule 1 |

Two enterprise families, two different owners, one village name. A matcher that
keys on "Eyak" gets it wrong half the time no matter which way it leans. That is
the whole reason rule 3 has to be evidenced per identifier rather than per name.

THE ONE-SIDED NAME TEST, AND WHY IT IS NOT THE FORBIDDEN INFERENCE
-------------------------------------------------------------------
The ruling forbids flipping to the government "because the names look alike -
the names look alike BY CONSTRUCTION, since both are named for the same
village." That warning is about the GOVERNMENT's name resembling the
CORPORATION's name. It is not a ban on reading a firm's own name.

`OLGOONIK FEDERAL, LLC` vs *Wainwright* (government) and *Olgoonik Corporation*
(corporation) has no by-construction resemblance at all: "Wainwright" and
"Olgoonik" share nothing. The resemblance is **one-sided** and points at the
corporation. So rung C5 fires only when a distinctive token of the CORPORATION's
name is in the firm name and no distinctive token of the GOVERNMENT's name is.
Where the token sits in both - "Eyak", "Chenega" - C5 refuses to fire and the
row must be carried by a stronger rung or go to a human. `NAME_TRAPS` is
imported from `cedar_domain` and excluded, per standing rule 8.

ELIMINATING ONE CANDIDATE IS NOT VERIFYING THE OTHER
-----------------------------------------------------
Where rule 2 removes the government leg and no rung establishes the surviving
corporation, the row goes to a HUMAN. The ruling settles
village-government-versus-its-own-village-corporation. It does not say which of
several unrelated corporations a firm belongs to, and stretching it to say so
would be exactly the over-reach this project keeps paying for.

THE RULE-4 CORRECTION IS A JUSTIFICATION CHANGE, NOT AN ARITHMETIC CHANGE
--------------------------------------------------------------------------
*A shareholder is not necessarily enrolled in the tribe; a shareholder
necessarily has ancestry.* ANCSA shares descend by inheritance and gift while
village tribal enrollment closed long ago, so the shareholder roll and the
enrollment roll are two overlapping populations, not one list. That wording is
written onto every refusal, because this project's failure mode is a correct
answer recorded with reasoning a later pass then generalises.

**NO PREDICATE HERE DEPENDS ON WHO MAY HOLD A SHARE.** The owner's open
share-transfer questions (adopted persons; gifts to non-Natives; gifts to
spouses) are recorded UNRESOLVED in the ruling doc and are not answered by
inference. Every decision below is about which LEGAL PERSON owns an operating
company, never about who may hold that person's stock, so no row changes
whatever the answer turns out to be. `SHARE_TRANSFER_PREDICATES_USED` is the
standing assertion of that.

A TIER IS INHERITED FROM THE SOURCE ROW. This ruling says WHICH entity is
correct; it never makes a weak link strong.
"""

import csv
import json
import os
import re
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cedar_domain import NAME_TRAPS, RULED_METHODS  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUN_DATE = "2026-08-26"

DEFECTS = os.path.join(ROOT, "review",
                       "identifier_one_to_many_defects_2026-08-26.csv")
SPINE = os.path.join(ROOT, "data", "spine", "cedar_entity_spine.csv")
LEDGER = os.path.join(ROOT, "data", "clean",
                      "cedar_identifier_ledger_final.csv")
RULINGS = os.path.join(ROOT, "data", "clean",
                       "cedar_ruling_ledger_consolidated.csv")
RELATIONSHIPS = os.path.join(ROOT, "data", "clean", "entity_relationships.csv")

OUT_RESOLUTIONS = os.path.join(ROOT, "review",
                               f"ancsa_ruling_resolutions_{RUN_DATE}.csv")
OUT_REFUSALS = os.path.join(ROOT, "review",
                            f"ancsa_ruling_refusals_{RUN_DATE}.csv")
OUT_SUMMARY = os.path.join(ROOT, "docs", "ANCSA_RULING_APPLICATION.json")

FAMILY = "ALASKA_VILLAGE_GOVERNMENT_VS_VILLAGE_CORPORATION"

GOVERNMENT_CLASSES = {
    "Federally recognized Alaska Native Village",
    "Federally recognized tribe",
}
CORPORATION_CLASSES = {
    "Alaska Native Village Corporation",
    "Alaska Native Regional Corporation",
    "ANCSA Group Corporation",
}

RULING_CITATION = "docs/ANCSA_OWNERSHIP_RULING.md, Elijah 2026-08-26"

#: The standing assertion required by the rule-4 open question. If a future edit
#: makes an attribution depend on ANCSA share-transfer rules, this list must
#: stop being empty and the ruling doc's open question must be closed first.
SHARE_TRANSFER_PREDICATES_USED = ()

RULE3_RUNGS = (
    "R3a_SETTLED_RULING_RESOLVES_THIS_IDENTIFIER_TO_A_GOVERNMENT",
    "R3b_SETTLED_RULING_TEXT_NAMES_A_GOVERNMENT_SPINE_ROW_ADDED_LATER",
    "R3c_SETTLED_RULING_ON_THE_BRAND_FAMILY_NAMES_A_GOVERNMENT",
    "R3d_LEDGER_ROW_WITH_A_RULED_METHOD_NAMES_A_GOVERNMENT",
    "R3e_OWNED_BY_EDGE_AT_RULED_STATUS_NAMES_THIS_IDENTIFIER",
)
RULE1_RUNGS = (
    "C1_TIER_A_village_corporation_for_EDGE_TIES_THIS_CORP_TO_THIS_VILLAGE",
    "C2_SETTLED_RULING_ON_THIS_IDENTIFIER_NAMES_THE_CORPORATION",
    "C3_LEDGER_ROW_WITH_A_RULED_METHOD_NAMES_THE_CORPORATION",
    "C4_TIER_A_RULED_brand_of_EDGE_TIES_THE_FIRM_BRAND_TO_THIS_CORP",
    "C5_ONE_SIDED_NAME_EVIDENCE_POINTING_AT_THE_CORPORATION_ONLY",
)

#: A ruling's `outcome`. ONLY `ENTITY` is a settled attribution. Measured cost
#: of getting this wrong, 2026-08-26: `UEI:VJ4MGKFTMVJ8` carries a SETTLED row
#: whose outcome is `HOLD_OVER_OWNER` and whose ruling text reads
#: "HOLD - RETRACTION REQUIRED, already written to the ledger from ...".
#: A first pass of this script read `status = SETTLED` plus a populated
#: `resolved_tribe_id` as confirmation and resolved the identifier to Seldovia
#: Native Association ON A RETRACTION. **`status` says the ruling was
#: processed; `outcome` says what the ruling DECIDED.** A HOLD is an
#: instruction not to attribute, and it is the strongest possible signal that a
#: human must look - never a confirmation.
SETTLED_ATTRIBUTION_OUTCOME = "ENTITY"
HOLD_OUTCOME_PREFIX = "HOLD"

#: Words that carry no identity in an Alaska Native corporate or village name.
#: Folding is for corporate forms and generics only - never for a word that
#: distinguishes (AGENTS.md, the `core()` finding).
GENERIC_TOKENS = frozenset({
    "corporation", "corp", "incorporated", "inc", "company", "co", "llc",
    "limited", "ltd", "lc", "group", "holdings", "enterprises", "enterprise",
    "native", "natives", "alaska", "alaskan", "village", "villages", "tribal",
    "tribe", "tribes", "council", "association", "islands", "island", "the",
    "and", "of", "for", "services", "service", "solutions", "systems",
    "technologies", "technology", "federal", "government", "indian",
})


def read_csv(path):
    with open(path, newline="", encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


def tokens(name):
    return [t for t in re.split(r"[^A-Za-z0-9']+", (name or "").lower()) if t]


def distinctive(name):
    """Identity-bearing tokens. Generic corporate words and NAME_TRAPS out."""
    return {t for t in tokens(name)
            if len(t) >= 4 and t not in GENERIC_TOKENS and t not in NAME_TRAPS}


def main():
    assert not SHARE_TRANSFER_PREDICATES_USED, (
        "An attribution predicate now depends on ANCSA share-transfer rules. "
        "Those are UNRESOLVED - see the OPEN QUESTION in "
        "docs/ANCSA_OWNERSHIP_RULING.md. Close the question with a retrieved "
        "source before this may run.")

    spine = {r["tribe_id"]: r for r in read_csv(SPINE)}
    defects = read_csv(DEFECTS)
    ak = [r for r in defects if r["defect_family"] == FAMILY]
    print(f"{FAMILY}: {len(ak)} defects")

    # ---- name index over GOVERNMENT-class Alaska rows ---------------------
    # Needed for rung R3b: a ruling written before the spine carried the
    # village names it in TEXT with a blank resolved_tribe_id.
    gov_by_name = {}
    for r in spine.values():
        if r["entity_class"] not in GOVERNMENT_CLASSES or r["state"] != "AK":
            continue
        for nm in [r["canonical_name"], r["fr_official_name"]] + \
                (r["aliases"] or "").split("|"):
            nm = (nm or "").strip().lower()
            if len(nm) >= 6:
                gov_by_name.setdefault(nm, r["tribe_id"])
    # The federal long form is the one a human writes in a ruling.
    for tid, r in spine.items():
        if r["entity_class"] in GOVERNMENT_CLASSES and r["state"] == "AK":
            gov_by_name.setdefault(
                f"native village of {r['canonical_name'].lower()}", tid)

    # ---- evidence indices -------------------------------------------------
    rulings = defaultdict(list)
    name_rulings = []
    for r in read_csv(RULINGS):
        k = r["subject_key"].strip().upper()
        rulings[k].append(r)
        if k.startswith("NAME:") and r.get("status") == "SETTLED":
            name_rulings.append((k[5:].strip().lower(), r))

    ledger_by_node = defaultdict(list)
    firm_name = {}
    for r in read_csv(LEDGER):
        k = (f"{r['identifier_type'].strip().upper()}:"
             f"{r['identifier'].strip().upper()}")
        ledger_by_node[k].append(r)
        if r["legal_business_name"] and k not in firm_name:
            firm_name[k] = r["legal_business_name"]

    vc_for = defaultdict(set)          # ANVC -> {AKNF village government}
    brand_of = defaultdict(set)        # brand token -> {entity_id}
    owned_by_gov = defaultdict(list)
    for r in read_csv(RELATIONSHIPS):
        rt = r["relationship_type"]
        if rt == "village_corporation_for":
            vc_for[r["source_entity_id"]].add(r["target_entity_id"])
        elif rt == "brand_of" and r.get("tier") == "A" \
                and r.get("verification_status") == "RULED":
            m = re.search(r"brand family '([^']+)'", r.get("notes") or "")
            if m:
                brand_of[m.group(1).strip().lower()].add(r["target_entity_id"])
        elif rt == "owned_by" and spine.get(
                r["target_entity_id"], {}).get("entity_class") \
                in GOVERNMENT_CLASSES:
            owned_by_gov[r["target_entity_id"]].append(r)
    print(f"village_corporation_for {sum(len(v) for v in vc_for.values())} | "
          f"tier-A RULED brand_of families {len(brand_of)}")

    resolutions, refusals = [], []
    tally, dollars = Counter(), Counter()

    for d in ak:
        ents, tiers = d["entities"].split("|"), d["tiers"].split("|")
        node = d["node"].strip().upper()
        usd = float(d["usd_observed"] or 0)
        name = d["observed_name"] or firm_name.get(node, "")
        ntok = tokens(name)

        gov = [(e, t) for e, t in zip(ents, tiers)
               if spine.get(e, {}).get("entity_class") in GOVERNMENT_CLASSES]
        corp = [(e, t) for e, t in zip(ents, tiers)
                if spine.get(e, {}).get("entity_class") in CORPORATION_CLASSES]
        if len(gov) != 1 or len(corp) != 1:
            tally["UNEXPECTED_SHAPE"] += 1
            continue
        (gov_id, gov_tier), (corp_id, corp_tier) = gov[0], corp[0]
        gov_name, corp_name = (spine[gov_id]["canonical_name"],
                               spine[corp_id]["canonical_name"])
        corp_class = spine[corp_id]["entity_class"]

        # ================= RULE 3: evidence, never assumption ==============
        r3 = []
        redirect_to = ""
        held = []
        for r in rulings.get(node, []):
            if r.get("status") != "SETTLED":
                continue
            outcome = (r.get("outcome") or "").strip().upper()
            if outcome.startswith(HOLD_OUTCOME_PREFIX):
                held.append(f"{r['source_file']}:{r['ruling_date']}:"
                            f"{outcome}:{r['ruling'][:120]!r}")
                continue
            tid = (r.get("resolved_tribe_id") or "").strip()
            if (outcome == SETTLED_ATTRIBUTION_OUTCOME and tid
                    and spine.get(tid, {}).get("entity_class")
                    in GOVERNMENT_CLASSES):
                r3.append((RULE3_RUNGS[0], tid,
                           f"{r['source_file']}:{r['ruling_date']}:"
                           f"{r['ruling']!r}", r.get("confidence_tier", "")))
            elif not tid:
                # A ruling written before the spine carried the village names
                # it in TEXT and could not resolve. The spine carries it now.
                hit = gov_by_name.get((r.get("ruling") or "").strip().lower())
                if hit:
                    r3.append((RULE3_RUNGS[1], hit,
                               f"{r['source_file']}:{r['ruling_date']}:"
                               f"outcome {outcome}; ruling text "
                               f"{r['ruling']!r} named a village the spine did "
                               f"not carry at ruling time ("
                               f"{r.get('resolve_how', '')}); it carries it "
                               f"now as {hit}", r.get("confidence_tier", "")))
        # Brand-family rule-3 CANDIDATE. Deliberately not a resolution: a
        # brand-family ruling names a family, and extending it to a specific
        # identifier is a name inference. It flags a human instead.
        r3_candidate = []
        if ntok:
            for brand, r in name_rulings:
                bt = tokens(brand)
                if len(bt) < 2 or len(ntok) < 2 or ntok[:2] != bt[:2]:
                    continue
                if not (set(bt[:2]) - GENERIC_TOKENS - NAME_TRAPS):
                    continue      # prefix carries no identity - never enough
                hit = gov_by_name.get((r.get("ruling") or "").strip().lower())
                if hit:
                    r3_candidate.append(
                        (hit, f"{r['source_file']}:{r['ruling_date']}:"
                              f"brand-family ruling {brand!r} -> "
                              f"{r['ruling']!r} ({hit})"))
                    break
        for r in ledger_by_node.get(node, []):
            if (spine.get(r["tribe_id"], {}).get("entity_class")
                    in GOVERNMENT_CLASSES
                    and r["attribution_method"].strip() in RULED_METHODS):
                r3.append((RULE3_RUNGS[3], r["tribe_id"],
                           f"{r['source_file']}:{r['attribution_method']}:"
                           f"{r['tier_rationale']}", r["confidence_tier"]))
        ident = node.split(":", 1)[-1]
        for tid, rows in owned_by_gov.items():
            for r in rows:
                if (r.get("verification_status") == "RULED"
                        and ident in (r.get("notes") or "").upper()):
                    r3.append((RULE3_RUNGS[4], tid,
                               f"entity_relationships.csv:"
                               f"{r['relationship_id']}:{r['evidence_text']}",
                               r.get("tier", "")))

        # ================= RULE 1 confirmation =============================
        c1 = gov_id in vc_for.get(corp_id, set())
        c2 = [r for r in rulings.get(node, [])
              if r.get("resolved_tribe_id") == corp_id
              and r.get("status") == "SETTLED"
              and (r.get("outcome") or "").strip().upper()
              == SETTLED_ATTRIBUTION_OUTCOME]
        c3 = [r for r in ledger_by_node.get(node, [])
              if r["tribe_id"] == corp_id
              and r["attribution_method"].strip() in RULED_METHODS]
        c4 = bool(ntok) and corp_id in brand_of.get(ntok[0], set())
        gov_dist, corp_dist = distinctive(gov_name), distinctive(corp_name)
        firm_dist = set(tokens(name))
        c5 = bool(corp_dist & firm_dist) and not (gov_dist & firm_dist)

        fired = [r for r, ok in zip(RULE1_RUNGS, (c1, c2, c3, c4, c5)) if ok]

        # ================= decide ==========================================
        if r3:
            rung, target, ev, evtier = r3[0]
            disposition = ("RESOLVED_TO_VILLAGE_GOVERNMENT_RULE_3"
                           if target in (gov_id,)
                           else "REDIRECTED_TO_A_THIRD_ENTITY_RULE_3")
            resolved_to = target
            resolved_class = spine[target]["entity_class"]
            inherited_tier = evtier or (gov_tier if target == gov_id else "")
            redirect_to = "" if target == gov_id else target
            note = (
                "RULE 3, EVIDENCED. A source shows the village GOVERNMENT "
                f"itself owns this enterprise, so it is attributed to "
                f"{spine[target]['canonical_name']} exactly as any tribal "
                "enterprise is attributed to its tribe. The owner is a "
                "federally recognized tribe that happens to be an Alaska "
                "Native village. IT IS NOT AN ANC AND MUST NOT BE CLASSED AS "
                f"ONE. Rung: {rung}. " + (
                    "This redirects to a THIRD entity - neither leg of the "
                    "defect was right. " if redirect_to else "") +
                RULING_CITATION)
            evidence = ev
        elif r3_candidate:
            # An existing SETTLED ruling names a village GOVERNMENT as owner of
            # this firm's BRAND FAMILY. That is rule 3's shape and it is the
            # answer to "are there real examples" - but a brand family is a
            # name family, not a legal person, so it does not resolve an
            # identifier on its own.
            disposition = "RULE_3_CANDIDATE_HUMAN_NEEDED"
            resolved_to = resolved_class = inherited_tier = ""
            note = (
                "RULE 3 CANDIDATE - do not auto-resolve. An existing SETTLED "
                f"ruling names {spine[r3_candidate[0][0]]['canonical_name']}, "
                "a village GOVERNMENT, as owner of this firm's brand family. "
                "That is exactly the rule-3 shape the owner said has a few "
                "real examples. It is NOT applied here because a brand family "
                "is a name family and not a legal person: carrying a "
                "family-level ruling onto one identifier is a name inference, "
                "and rule 3 must be EVIDENCED per identifier. The government "
                f"leg as recorded ({gov_name}) is refused under rule 2 and is "
                "in any case a DIFFERENT village from the one the ruling "
                "names. HUMAN NEEDED. " + RULING_CITATION)
            evidence = r3_candidate[0][1]
            redirect_to = r3_candidate[0][0]
        elif held:
            disposition = "HELD_BY_AN_EXISTING_RULING_HUMAN_NEEDED"
            resolved_to = resolved_class = inherited_tier = ""
            note = (
                "An existing SETTLED ruling on this identifier has outcome "
                "HOLD*, which is an instruction NOT to attribute. A hold is "
                "never confirmation - `status` says the ruling was processed, "
                "`outcome` says what it decided. The government leg is refused "
                "under rule 2; the corporation leg may not be written while "
                "the hold stands. HUMAN NEEDED. " + RULING_CITATION)
            evidence = " ;; ".join(held)
        elif fired:
            disposition = "RESOLVED_TO_VILLAGE_CORPORATION_RULE_1"
            resolved_to, resolved_class = corp_id, corp_class
            inherited_tier = corp_tier
            note = (
                "RULE 1 presumption applied: an ANCSA operating company is "
                "owned by the village corporation, not the village "
                f"government. The government leg ({gov_name}) is REFUSED "
                "under rule 2 - a village government never owns an ANC. The "
                "two entity names resemble each other BY CONSTRUCTION, both "
                "being named for the same village, and that resemblance is "
                f"not evidence. Confirming rungs: {', '.join(fired)}. "
                + RULING_CITATION)
            evidence = "; ".join(fired)
        else:
            disposition = "HUMAN_NEEDED_SURVIVING_CORPORATION_UNVERIFIED"
            resolved_to = resolved_class = inherited_tier = ""
            note = (
                f"The government leg ({gov_name}) is REFUSED under rule 2. But "
                f"the surviving corporation leg ({corp_name}) has no "
                "established tie to this village, no ruling on this "
                "identifier, no tier-A brand edge, and no one-sided name "
                "evidence. ELIMINATING ONE CANDIDATE IS NOT VERIFYING THE "
                "OTHER, and this ruling settles village-government-versus-"
                "its-own-village-corporation, not which of several unrelated "
                "corporations a firm belongs to. HUMAN NEEDED. "
                + RULING_CITATION)
            evidence = "no rung fired on either leg"

        # ---- rule 2 refusal, on every row that is not a rule-3 resolution --
        if not disposition.endswith("RULE_3"):
            refusals.append({
                "node": d["node"], "identifier_type": d["identifier_type"],
                "identifier": d["identifier"], "firm_name": name,
                "refused_entity_id": gov_id, "refused_entity_name": gov_name,
                "refused_entity_class": spine[gov_id]["entity_class"],
                "refused_leg_tier": gov_tier,
                "refused_leg_asserted_by": d["paths"],
                "usd_observed": d["usd_observed"],
                "refusal_rule": "RULE_2_A_VILLAGE_GOVERNMENT_NEVER_OWNS_AN_ANC",
                "refusal_text": (
                    "REFUSED. A village government never owns an ANC. This "
                    "attribution asserts that it does, so the attribution is "
                    "wrong. The village government and the village "
                    "corporation are ASSOCIATED, never in an ownership "
                    "relation, and THE ASSOCIATION IS ANCESTRAL RATHER THAN "
                    "MEMBERSHIP-BASED: a shareholder is not necessarily "
                    "enrolled in the tribe, but necessarily has ancestry. "
                    "ANCSA shares descend by inheritance and gift while "
                    "village tribal enrollment closed long ago, so the "
                    "shareholder roll and the enrollment roll are two "
                    "overlapping populations, not two views of one list. "
                    "Neither may be used as a proxy for the other, and "
                    "neither is a corporate ownership edge."),
                "ruling_cited": RULING_CITATION,
                "built_date": RUN_DATE,
            })

        resolutions.append({
            "node": d["node"], "identifier_type": d["identifier_type"],
            "identifier": d["identifier"], "firm_name": name,
            "disposition": disposition,
            "resolved_entity_id": resolved_to,
            "resolved_entity_name": spine.get(resolved_to, {}).get(
                "canonical_name", ""),
            "resolved_entity_class": resolved_class,
            "inherited_tier": inherited_tier,
            "tier_provenance": (
                "INHERITED from the leg or evidence row resolved to. This "
                "ruling assigns no tier and promotes nothing."),
            "redirected_to_third_entity": redirect_to,
            "government_leg_entity_id": gov_id,
            "government_leg_entity_name": gov_name,
            "government_leg_tier": gov_tier,
            "corporation_leg_entity_id": corp_id,
            "corporation_leg_entity_name": corp_name,
            "corporation_leg_class": corp_class,
            "corporation_leg_tier": corp_tier,
            "corporation_is_this_villages_own": "Y" if c1 else "N",
            "evidence": evidence,
            "note": note, "ruling_cited": RULING_CITATION,
            "usd_observed": d["usd_observed"], "built_date": RUN_DATE,
        })
        tally[disposition] += 1
        dollars[disposition] += usd

    for path, rows in ((OUT_RESOLUTIONS, resolutions),
                       (OUT_REFUSALS, refusals)):
        part = path + ".part"
        with open(part, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
        os.replace(part, path)
        print(f"wrote {path}  {len(rows)} rows")

    summary = {
        "built": RUN_DATE,
        "script": "code/191_apply_ancsa_ownership_ruling.py",
        "ruling": RULING_CITATION,
        "family": FAMILY, "defects": len(ak),
        "disposition_counts": dict(tally),
        "disposition_dollars_musd": {k: round(v / 1e6, 2)
                                     for k, v in dollars.items()},
        "rule2_refusals": len(refusals),
        "share_transfer_open_question_affects_any_row": False,
        "share_transfer_predicates_used": list(SHARE_TRANSFER_PREDICATES_USED),
    }
    with open(OUT_SUMMARY, "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2)
    print(f"wrote {OUT_SUMMARY}")

    print("\nDISPOSITION")
    for k, v in tally.most_common():
        print(f"  {v:>5}  ${dollars[k] / 1e6:>12,.1f}M  {k}")
    print(f"  {len(refusals):>5}  government-side legs REFUSED under rule 2")


if __name__ == "__main__":
    main()
