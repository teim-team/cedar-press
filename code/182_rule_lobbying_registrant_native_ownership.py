#!/usr/bin/env python3
"""
Cedar Press - 182: which LDA registrants are themselves Native entities.

THE INSTRUCTION, AND WHY IT IS THE HARD PART
--------------------------------------------
    "Some registrants are themselves Native-owned. Establish this from
     evidence, never from a name. Where it is not, say so; NO_CLAIM_FOUND,
     never NOT_NATIVE."

A firm called IETAN CONSULTING with a contact named WILSON PIPESTEM in Tulsa,
Oklahoma looks Native. So does SPIRIT ROCK CONSULTING and so does MAPETSI
POLICY GROUP. **A name is not evidence and neither is a contact name.** This
project has a register of what happens when it is treated as one: National
Education Association -> National Indian Education Association, Boys & Girls
Clubs of Wichita Falls -> the Wichita Tribe, READ & STEVENS, INC. -> Stevens
Village.

So candidate SELECTION may use anything - that is search strategy. The RULING
uses only retrieved evidence, and where there is none the answer is
`NO_CLAIM_FOUND`, which means *nobody has looked hard enough yet*. It never
means NOT_NATIVE.

THE MEASURED TRAP THIS BUILD PAID FOR, BEFORE IT SHIPPED
--------------------------------------------------------
The obvious spine route - normalize the registrant's name and look it up -
matches `ALUTIIQ, LLC` to `AKNF-ALTIIQ-00-KONIAG`, **the Native Village of
Alutiiq, a village government**. Alutiiq LLC is a subsidiary of Afognak Native
Corporation. That is AGENTS.md's containment defect, direction 2 - "NATIVE
VILLAGE OF ELIM -> Elim Native Corporation" - arriving through a brand new
door, because normalization had stripped `LLC` and the shortest spine name won.

**Guard: the spine route preserves corporate-form tokens.** `ALUTIIQ, LLC` and
`Alutiiq` are not the same string once `LLC` survives normalization, so the
match is refused. `CALISTA CORPORATION` and `Calista Corporation` still agree.
The cost of the guard is zero correct matches and it forecloses the whole
class.

THE ROUTES, STRONGEST FIRST
---------------------------
R1 SELF_FILED_ON_OWN_BEHALF
   The registrant filed on its OWN behalf - registrant and client are the same
   organisation on the face of the filing - and that client is keyed to a
   Native entity. This is the strongest evidence available anywhere in LDA: it
   is the registrant's own sworn statement of who it is. Tier INHERITED from
   the keyed disclosure row.

R2 REGISTRANT_NAME_IS_A_KEYED_NATIVE_CLIENT
   The registrant's own name appears as a CLIENT elsewhere in the corpus,
   keyed to a Native entity by a different filer. Tier INHERITED.

R3 REGISTRANT_NAME_EQUALS_A_SPINE_ENTITY
   Strict, corporate-form-preserving equality against the spine's
   canonical_name, fr_official_name and curated aliases. Tier DECLARED B: a
   name equality is a match, not a ruling.

R4 EIN_ON_A_RULED_NATIVE_NONPROFIT
   An EIN this registrant holds (from 181) sits on an `np_orgs` row whose
   `classification_ruling` is a POSITIVE Native ruling. Tier INHERITED from
   that row's `confidence_tier`.

R5 IDENTIFIER_ATTRIBUTED_IN_THE_LEDGER
   A UEI or CAGE this registrant holds is attributed to a Native entity in
   `cedar_identifier_ledger_final.csv`. Tier INHERITED from the ledger row.

R6 FIRM_SELF_STATEMENT (web)
   The firm's own published statement of Native ownership, quoted verbatim
   with its URL - the standard AGENTS.md sets for the individually
   Native-owned class. **NOT_CHECKED in this run**, and the reason is recorded
   on every affected row rather than left as an implied absence.

A RULED METHOD IS NOT A POSITIVE RULING
---------------------------------------
`148_resolve_schedule_i_recipients.py` carries a live bug that promotes 42
tier-X NEGATIVE rulings to tier A, because it tested that a ruling EXISTED and
not what the ruling SAID. This script tests the VALUE:

    positive  native_controlled · tribally_controlled
    negative  place_name_coincidence · any tier-X ledger row
    neither   native_serving  ->  serves_native_entities, NOT ownership
    neither   UNRULED

A negative ruling BLOCKS the registrant and is never overridden by a weaker
positive from another route. `native_serving` is recorded in its own column and
never touches the ownership status - `serves_native_entities` is not
`parent_native_entity`, here as everywhere else in this project.

Tiering: `native_ownership_evidence_tier` is the tier of the SINGLE strongest
route, and a route's tier is the WEAKEST edge on its path. Corroboration is
counted in `n_ownership_routes` and NEVER promotes a tier - two-leg promotion
is a ledger method, not a consumer's.

Zero network calls. Writes its own outputs and patches only the eight
ownership columns 180 declared in `lobbying_registrants.csv`.
"""

import csv
import json
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

CEDAR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(CEDAR / "code"))
# See the note in 180: this script filtered on `org_type_barred` alone and
# would have read the 471 filings withdrawn by script 350 as live evidence.
from cedar_domain import lobbying_attribution_withdrawn   # noqa: E402

CLEAN = CEDAR / "data" / "clean"
REVIEW = CEDAR / "review"
SPINE = CEDAR / "data" / "spine" / "cedar_entity_spine.csv"

HUB = CLEAN / "lobbying_registrants.csv"
IDS = CLEAN / "lobbying_registrant_identifiers.csv"
DISC = CLEAN / "native_entity_lobbying_disclosures.csv"
LEDGER = CLEAN / "cedar_identifier_ledger_final.csv"
NPORGS = CLEAN / "np_orgs.csv"

OUT = CLEAN / "lobbying_registrant_native_ownership_evidence.csv"
QUEUE = REVIEW / "lobbying_registrant_native_ownership_queue_2026-08-26.csv"

TODAY = date.today().isoformat()
SCRIPT = "182_rule_lobbying_registrant_native_ownership.py"

csv.field_size_limit(min(sys.maxsize, 2147483647))

POSITIVE_NP_RULINGS = {"native_controlled", "tribally_controlled"}
NEGATIVE_NP_RULINGS = {"place_name_coincidence"}
SERVES_NOT_OWNS = {"native_serving"}

# Confidence vocabulary of the disclosure file, weakest first.
CONF_ORDER = ["withdrawn_org_type", "withdrawn_false_attribution",
              "low", "medium", "high"]
CONF_TO_TIER = {"high": "B", "medium": "C", "low": "C",
                "withdrawn_org_type": "X",
                # A withdrawn attribution carries no evidence at all. It never
                # reaches a tier here because `disc` excludes it above; the
                # entry exists so an unrecognised confidence can never fall
                # through to a default that publishes.
                "withdrawn_false_attribution": "X"}
TIER_ORDER = {"X": -1, "": 0, "C": 1, "B": 2, "A": 3}


def log(m=""):
    print(m, flush=True)


def read_csv(p):
    p = Path(p)
    if not p.exists():
        return []
    with open(p, newline="", encoding="utf-8-sig", errors="replace") as fh:
        return list(csv.DictReader(fh))


def write_csv(path, rows, fields):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    part = path.with_suffix(path.suffix + ".part")
    with open(part, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)
    if path.exists():
        bak = path.with_name(path.name + f".bak_{TODAY}_pre_{SCRIPT}")
        if not bak.exists():
            bak.write_bytes(path.read_bytes())
            log(f"  backed up -> {bak.name}")
    os.replace(part, path)


#: The columns this script MINTS. Anything else already on the output file was
#: put there by a later in-place enricher (`505` mints `cedar_uid`), and a full
#: rebuild here must carry it forward rather than silently erase it. That
#: erasure is this project's single most repeated defect - it took `cedar_uid`
#: off `admin_appeal_positions.csv` and two gaming tables on 2026-09-01, and it
#: took it off THIS table the first time the asserted_by_source fix ran.
#: Carried on (registrant_id, evidence_route, native_entity_id), which is
#: constant-valued for `cedar_uid` on every group in the pre-fix file; a group
#: that disagrees is left BLANK and reported rather than guessed at.
CARRY_FORWARD_JOIN = ["registrant_id", "evidence_route", "native_entity_id"]


def carry_forward_enriched_columns(path, rows, fields):
    """Copy columns a later enricher added back onto a freshly built table.

    Returns the (possibly extended) field list. Never invents a value: a join
    key the old file does not hold, or holds with two different values, leaves
    the cell blank and prints why.
    """
    old = read_csv(path)
    if not old:
        return fields
    extra = [c for c in old[0] if c not in fields]
    if not extra:
        return fields
    idx = defaultdict(lambda: defaultdict(set))
    for o in old:
        k = tuple(o.get(c, "") for c in CARRY_FORWARD_JOIN)
        for c in extra:
            if (o.get(c) or "").strip():
                idx[k][c].add(o[c])
    filled = Counter()
    ambiguous = Counter()
    for r in rows:
        k = tuple(r.get(c, "") for c in CARRY_FORWARD_JOIN)
        for c in extra:
            vals = idx.get(k, {}).get(c, set())
            if len(vals) == 1:
                r[c] = next(iter(vals))
                filled[c] += 1
            else:
                r.setdefault(c, "")
                if len(vals) > 1:
                    ambiguous[c] += 1
    log(f"  carried forward {len(extra)} enricher column(s) from the previous "
        f"{Path(path).name}: " + ", ".join(
            f"{c} on {filled[c]}/{len(rows)} rows"
            + (f" ({ambiguous[c]} left blank - two values on one join key)"
               if ambiguous[c] else "")
            for c in extra))
    return fields + extra


def norm_strict(s):
    """Normalization that PRESERVES the corporate form.

    Punctuation, case and `&` fold. `LLC`, `Inc`, `Corporation` do NOT. That
    single choice is what stops `ALUTIIQ, LLC` reaching the Native Village of
    Alutiiq.
    """
    if not isinstance(s, str):
        return ""
    s = s.lower().replace("&", " and ")
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def main():
    log("=== Cedar Press 182: registrant Native-entity evidence ===\n")

    hub = read_csv(HUB)
    if not hub:
        log(f"  !! {HUB} absent - run 180 first")
        return
    ids = read_csv(IDS)
    disc = [r for r in read_csv(DISC)
            if not lobbying_attribution_withdrawn(r)]
    spine = read_csv(SPINE)
    log(f"  registrants {len(hub)} · identifier rows {len(ids)} · "
        f"disclosures {len(disc):,} · spine {len(spine):,}")

    reg_name = {h["registrant_id"]: h.get("registrant_name") for h in hub}
    reg_variants = {h["registrant_id"]:
                    [v for v in (h.get("registrant_name_variants") or "").split(";") if v]
                    for h in hub}

    ev = []                       # one row per (registrant, route, evidence)
    blocks = defaultdict(list)    # registrant -> negative rulings

    def add(rid, route, status, rel, eid, ename, eclass, tier,
            basis, quote, url, src, extra=None):
        row = {
            "registrant_id": rid,
            "registrant_name": reg_name.get(rid, ""),
            "evidence_route": route,
            "claim": status,
            "relationship_to_native_entity": rel,
            "native_entity_id": eid or "",
            "native_entity_canonical_name": ename or "",
            "native_entity_class": eclass or "",
            "evidence_tier": tier,
            "tier_is_inherited": "1" if route in (
                "R1_SELF_FILED_ON_OWN_BEHALF",
                "R2_REGISTRANT_NAME_IS_A_KEYED_NATIVE_CLIENT",
                "R4_EIN_ON_A_RULED_NATIVE_NONPROFIT",
                "R5_IDENTIFIER_ATTRIBUTED_IN_THE_LEDGER") else "0",
            "match_basis": basis,
            "evidence_verbatim": quote,
            "evidence_url": url,
            "evidence_source": src,
            # THE COLUMN THAT MAKES THIS TABLE KEYABLE (workstream UPSTREAM,
            # 2026-09-01). The identifier routes R4 and R5 walk
            # `lobbying_registrant_identifiers.csv`, whose OWN declared grain
            # is "one row per identifier ASSERTION about a registrant, with
            # its asserter" - key (identifier, asserted_by_source). Four
            # sources asserting the same UEI produce FOUR evidence rows here,
            # and this script dropped the asserter, so they rendered
            # byte-identical: UEI CY16XXPHX213 (registrant 301072) reached
            # this table from a graph node, a prime, a funding row and a
            # subaward, as two B-paths and two C-paths, and looked like two
            # duplicated rows. THEY ARE FOUR INDEPENDENT CORROBORATIONS and
            # de-duplicating them deletes the corroboration. Carrying the
            # asserter costs one column and makes the row say what it is.
            # Blank on R1/R2/R3, which are not identifier routes - blank is a
            # value of this key, not a gap in it.
            "identifier_type": "",
            "identifier": "",
            "asserted_by_source": "",
            "built_by_script": SCRIPT,
            "built_date": TODAY,
        }
        row.update(extra or {})
        ev.append(row)

    # ---- R1 / R2 : the corpus's own keyed rows ---------------------------
    by_reg_self = defaultdict(list)
    client_keyed = defaultdict(list)
    for r in disc:
        if not (r.get("entity_id") or "").strip():
            continue
        if (r.get("self_filed") or "") == "1":
            by_reg_self[r["registrant_id"]].append(r)
        client_keyed[norm_strict(r.get("client_name"))].append(r)

    for rid, rows in by_reg_self.items():
        best = min(rows, key=lambda r: CONF_ORDER.index(
            r.get("match_confidence") or "low")
            if (r.get("match_confidence") in CONF_ORDER) else 0)
        conf = best.get("match_confidence") or ""
        add(rid, "R1_SELF_FILED_ON_OWN_BEHALF", "NATIVE_ENTITY",
            "IS_OR_IS_OWNED_BY_THE_NAMED_NATIVE_ENTITY",
            best.get("entity_id"), best.get("canonical_name"),
            best.get("entity_type"),
            CONF_TO_TIER.get(conf, "C"),
            f"self_filed=1 on {len(rows)} filings; entity link method "
            f"{best.get('attribution_method')}, confidence {conf}",
            f"The registrant filed on its own behalf: registrant "
            f"\"{best.get('registrant_name')}\" and client "
            f"\"{best.get('client_name')}\" are the same organisation on the "
            f"face of the filing.",
            best.get("filing_url") or "",
            "Senate LDA filing (lda.senate.gov) + "
            "native_entity_lobbying_disclosures.csv",
            {"n_supporting_filings": len(rows),
             "inherited_confidence": conf,
             "inherited_attribution_method": best.get("attribution_method")})

    for rid in reg_name:
        if rid in by_reg_self:
            continue
        for v in reg_variants.get(rid, []) + [reg_name.get(rid) or ""]:
            hits = client_keyed.get(norm_strict(v))
            if not hits:
                continue
            best = hits[0]
            conf = best.get("match_confidence") or ""
            add(rid, "R2_REGISTRANT_NAME_IS_A_KEYED_NATIVE_CLIENT",
                "NATIVE_ENTITY",
                "IS_OR_IS_OWNED_BY_THE_NAMED_NATIVE_ENTITY",
                best.get("entity_id"), best.get("canonical_name"),
                best.get("entity_type"), CONF_TO_TIER.get(conf, "C"),
                "registrant legal name equals a client name already keyed to "
                "a Native entity by another filer",
                f"\"{best.get('client_name')}\" appears as the CLIENT on "
                f"{len(hits)} filings in this corpus, keyed to "
                f"{best.get('canonical_name')}.",
                best.get("filing_url") or "",
                "native_entity_lobbying_disclosures.csv",
                {"n_supporting_filings": len(hits),
                 "inherited_confidence": conf,
                 "inherited_attribution_method": best.get("attribution_method")})
            break

    # ---- R3 : strict spine equality --------------------------------------
    spine_idx = defaultdict(list)
    for s in spine:
        for nm in (s.get("canonical_name"), s.get("fr_official_name")):
            if norm_strict(nm):
                spine_idx[norm_strict(nm)].append((s, "canonical_or_official"))
        for a in re.split(r"[;|]", s.get("aliases") or ""):
            if norm_strict(a):
                spine_idx[norm_strict(a)].append((s, "curated_alias"))
    refused_spine = []
    for rid in reg_name:
        for v in reg_variants.get(rid, []) + [reg_name.get(rid) or ""]:
            n = norm_strict(v)
            hits = spine_idx.get(n)
            if not hits:
                continue
            eids = {h[0]["tribe_id"] for h in hits}
            if len(eids) > 1:
                refused_spine.append((rid, v, sorted(eids)))
                break
            s, how = hits[0]
            add(rid, "R3_REGISTRANT_NAME_EQUALS_A_SPINE_ENTITY",
                "NATIVE_ENTITY", "IS_THE_NAMED_NATIVE_ENTITY",
                s["tribe_id"], s.get("canonical_name"), s.get("entity_class"),
                "B",
                f"corporate-form-preserving normalized equality against the "
                f"spine ({how})",
                f"Registrant name \"{v}\" equals spine entity "
                f"\"{s.get('canonical_name')}\" ({s['tribe_id']}, "
                f"{s.get('entity_class')}).",
                s.get("entity_source_url") or s.get("source_url") or "",
                "data/spine/cedar_entity_spine.csv",
                {"tier_declared_reason":
                 "declared B, not inherited: a name equality is a match, not "
                 "a ruling. No spine row asserts that this LDA registrant is "
                 "this entity."})
            break

    # ---- R4 : an EIN on a RULED Native nonprofit -------------------------
    np_by_ein = {}
    for r in read_csv(NPORGS):
        e = (r.get("EIN") or "").strip().replace("-", "")
        if e:
            np_by_ein.setdefault(e.zfill(9), r)
    serves_only = {}
    for i in ids:
        if i["identifier_type"] != "EIN":
            continue
        rec = np_by_ein.get(i["identifier"].strip().replace("-", "").zfill(9))
        if not rec:
            continue
        ruling = (rec.get("classification_ruling") or "").strip()
        # THE 148 BUG, REFUSED EXPLICITLY: a RULED method is not a POSITIVE
        # ruling. Test what the ruling SAYS, never that one exists.
        if ruling in NEGATIVE_NP_RULINGS:
            blocks[i["registrant_id"]].append(
                f"np_orgs EIN {i['identifier']} carries the NEGATIVE ruling "
                f"'{ruling}'")
            continue
        if ruling in SERVES_NOT_OWNS:
            serves_only[i["registrant_id"]] = (
                f"np_orgs rules EIN {i['identifier']} '{ruling}' - serving "
                f"Native entities is not being one")
            continue
        if ruling not in POSITIVE_NP_RULINGS:
            continue
        add(i["registrant_id"], "R4_EIN_ON_A_RULED_NATIVE_NONPROFIT",
            "NATIVE_ENTITY", "IS_THE_NAMED_NATIVE_ENTITY",
            rec.get("cedar_spine_entity_id") or rec.get("tribe_id"),
            rec.get("cedar_spine_canonical_name") or rec.get("tribe_canonical_name"),
            rec.get("cedar_native_entity_class"),
            rec.get("confidence_tier") or "C",
            f"EIN held by this registrant (via {i['asserted_by_source']}, "
            f"tier {i['confidence_tier']}) carries np_orgs ruling '{ruling}'",
            (rec.get("evidence") or "")[:600],
            rec.get("source_url") or "",
            "np_orgs.csv",
            {"inherited_confidence": rec.get("confidence_tier") or "",
             "identifier_type": i["identifier_type"],
             "identifier": i["identifier"],
             "asserted_by_source": i.get("asserted_by_source") or "",
             "path_weakest_edge":
                 f"identifier assertion tier {i['confidence_tier']} "
                 f"({i['asserted_by_source']})"})

    # ---- R5 : ledger attribution on a UEI or CAGE ------------------------
    led = defaultdict(list)
    for r in read_csv(LEDGER):
        t = (r.get("identifier_type") or "").strip().upper()
        if t in ("UEI", "CAGE"):
            led[(t, (r.get("identifier") or "").strip().upper())].append(r)
    for i in ids:
        if i["identifier_type"] not in ("UEI", "CAGE"):
            continue
        for r in led.get((i["identifier_type"],
                          i["identifier"].strip().upper()), []):
            tier = (r.get("confidence_tier") or "").strip().upper()
            tid = (r.get("tribe_id") or "").strip()
            if tier == "X":
                blocks[i["registrant_id"]].append(
                    f"ledger carries a tier-X NEGATIVE ruling on "
                    f"{i['identifier_type']} {i['identifier']}: "
                    f"{r.get('exclusion_evidence') or r.get('tier_rationale')}")
                continue
            if not tid:
                continue
            # weakest edge on the path
            path = [tier or "C", i["confidence_tier"]]
            weakest = min(path, key=lambda t: TIER_ORDER.get(t, 0))
            add(i["registrant_id"], "R5_IDENTIFIER_ATTRIBUTED_IN_THE_LEDGER",
                "NATIVE_OWNED", "OWNED_BY_THE_NAMED_NATIVE_ENTITY",
                tid, r.get("canonical_name"), r.get("entity_class"), weakest,
                f"{i['identifier_type']} {i['identifier']} is attributed in "
                f"the identifier ledger by method "
                f"'{r.get('attribution_method')}' at tier {tier}",
                (r.get("tier_rationale") or "")[:400],
                r.get("evidence_url") or "",
                "cedar_identifier_ledger_final.csv",
                {"inherited_confidence": tier,
                 "identifier_type": i["identifier_type"],
                 "identifier": i["identifier"],
                 "asserted_by_source": i.get("asserted_by_source") or "",
                 "path_weakest_edge":
                     f"min(ledger {tier}, identifier assertion "
                     f"{i['confidence_tier']}) = {weakest}"})

    # ---- roll up to one status per registrant ----------------------------
    by_reg = defaultdict(list)
    for e in ev:
        by_reg[e["registrant_id"]].append(e)

    n_status = Counter()
    queue = []
    for h in hub:
        rid = h["registrant_id"]
        rows = by_reg.get(rid, [])
        neg = blocks.get(rid, [])
        if neg and not rows:
            h["native_ownership_status"] = "NO_CLAIM_FOUND"
            h["native_ownership_basis"] = (
                "a NEGATIVE ruling blocks this registrant: " + "; ".join(neg))
            h["native_ownership_evidence_tier"] = "X"
            h["native_ownership_routes"] = "BLOCKED_BY_NEGATIVE_RULING"
            h["n_ownership_routes"] = "0"
            n_status["NO_CLAIM_FOUND_BLOCKED"] += 1
            continue
        if not rows:
            h["native_ownership_status"] = "NO_CLAIM_FOUND"
            h["native_ownership_basis"] = (
                "No retrieved evidence establishes that this registrant is a "
                "Native entity or is Native-owned. NO_CLAIM_FOUND means "
                "nobody has established a claim, NOT that the registrant is "
                "not Native. The firm-self-statement route (R6) is "
                "NOT_CHECKED in this run: the session's web-search budget was "
                "exhausted, so no firm's own published ownership statement "
                "was retrieved."
                + (" np_orgs rules an EIN this registrant holds "
                   "'native_serving', which is service to Native entities and "
                   "is not ownership." if rid in serves_only else ""))
            h["native_ownership_evidence_tier"] = ""
            h["native_ownership_routes"] = "R6_FIRM_SELF_STATEMENT:NOT_CHECKED"
            h["n_ownership_routes"] = "0"
            n_status["NO_CLAIM_FOUND"] += 1
            continue
        best = max(rows, key=lambda r: TIER_ORDER.get(r["evidence_tier"], 0))
        eids = {r["native_entity_id"] for r in rows if r["native_entity_id"]}
        top = TIER_ORDER.get(best["evidence_tier"], 0)
        tied = {r["native_entity_id"] for r in rows
                if TIER_ORDER.get(r["evidence_tier"], 0) == top
                and r["native_entity_id"]}
        h["native_ownership_status"] = best["claim"]
        h["native_ownership_basis"] = best["match_basis"] + (
            f" | ROUTES DISAGREE ON THE ENTITY at the same tier "
            f"{sorted(tied)} - HELD FOR A RULING, no id is carried. This is "
            f"the ALASKA_VILLAGE_GOVERNMENT_VS_VILLAGE_CORPORATION family "
            f"from docs/IDENTIFIER_GRAPH_BUILD_LOG.md arriving in the "
            f"lobbying data: one ruling settles the whole family."
            if len(tied) > 1 else
            (f" | routes name different entities {sorted(eids)}; the "
             f"strictly stronger route's id is carried"
             if len(eids) > 1 else ""))
        h["native_ownership_evidence_quote"] = best["evidence_verbatim"]
        h["native_ownership_evidence_url"] = best["evidence_url"]
        h["native_ownership_evidence_tier"] = best["evidence_tier"]
        # When two equally strong routes name different entities, DO NOT PICK.
        h["native_ownership_entity_id"] = (
            "" if len(tied) > 1 else best["native_entity_id"])
        h["native_ownership_routes"] = "|".join(
            sorted({r["evidence_route"] for r in rows}))
        h["n_ownership_routes"] = str(len({r["evidence_route"] for r in rows}))
        # The known family, flagged wherever it can bite: an Alaska VILLAGE
        # GOVERNMENT claimed for a registrant whose own name is a CORPORATION.
        # 334 identifiers and $24.52B sit on this exact question elsewhere in
        # the corpus. Flagged, never silently corrected - the claim is
        # inherited from the source and only a ruling may change it.
        if "Alaska Native Village" in (best["native_entity_class"] or "") \
                and re.search(r"\b(llc|inc|incorporated|corp|corporation|"
                              r"company|ltd|limited)\b",
                              (h.get("registrant_name") or "").lower()):
            h["native_ownership_basis"] += (
                " | FLAG ALASKA_VILLAGE_GOVERNMENT_VS_VILLAGE_CORPORATION: "
                "the claimed entity is a village GOVERNMENT and the "
                "registrant's own name carries a corporate form. The village "
                "corporation is a different legal person. Inherited from the "
                "source and held for the same ruling.")
        n_status[best["claim"]] += 1
        if len(eids) > 1:
            queue.append({
                "registrant_id": rid,
                "registrant_name": h.get("registrant_name"),
                "question": "Two evidence routes name DIFFERENT Native "
                            "entities for this registrant. Which is the "
                            "registrant?",
                "candidates": "; ".join(
                    f"{r['evidence_route']} -> {r['native_entity_id']} "
                    f"{r['native_entity_canonical_name']}" for r in rows),
                "evidence_needed": "a statement by the firm or by the entity",
                "built_by_script": SCRIPT, "built_date": TODAY,
            })

    # ---- the queue: the firms a web pass would settle in minutes ---------
    ranked = sorted(
        (h for h in hub if h["native_ownership_status"] == "NO_CLAIM_FOUND"),
        key=lambda h: -int(h.get("n_filings_native_clients") or 0))
    for h in ranked[:40]:
        queue.append({
            "registrant_id": h["registrant_id"],
            "registrant_name": h.get("registrant_name"),
            "question": "Is this firm Native-owned? NO_CLAIM_FOUND today "
                        "because route R6 (the firm's own published ownership "
                        "statement) was NOT_CHECKED - the session's "
                        "web-search budget was exhausted.",
            "candidates": f"LDA self-description: "
                          f"\"{h.get('registrant_description_lda_verbatim')}\" "
                          f"· city {h.get('registrant_city')}, "
                          f"{h.get('registrant_state')} · LDA contact "
                          f"{h.get('registrant_lda_contact_name')} · "
                          f"{h.get('n_filings_native_clients')} filings for "
                          f"{h.get('n_distinct_native_entities')} Native "
                          f"entities",
            "evidence_needed": "the firm's own published statement of "
                               "ownership, quoted verbatim with its URL - the "
                               "standard AGENTS.md sets for the individually "
                               "Native-owned class. An SBA certification "
                               "record or a state corporate filing naming the "
                               "owner also settles it.",
            "built_by_script": SCRIPT, "built_date": TODAY,
        })

    # ---- write -----------------------------------------------------------
    ev_fields = []
    for r in ev:
        for k in r:
            if k not in ev_fields:
                ev_fields.append(k)
    for r in ev:
        for k in ev_fields:
            r.setdefault(k, "")
    ev_fields = carry_forward_enriched_columns(OUT, ev, ev_fields)
    write_csv(OUT, ev, ev_fields)
    log(f"\n  wrote {OUT.name}: {len(ev)} evidence rows")
    if queue:
        write_csv(QUEUE, queue, list(queue[0].keys()))
        log(f"  wrote {QUEUE.name}: {len(queue)} questions")

    write_csv(HUB, hub, list(hub[0].keys()))
    log(f"  patched {HUB.name} ownership columns in place")

    # ---- verify by RE-READING -------------------------------------------
    back = read_csv(HUB)
    log("\n-- verification (re-read from disk) --")
    log(f"  {HUB.name}: {len(back)} rows, "
        f"{len(back[0])} cols (was {len(hub[0])})")
    c = Counter(r["native_ownership_status"] for r in back)
    for k, v in c.most_common():
        log(f"  {k:<40} {v}")
    log(f"  refused spine matches (one name, many entities): "
        f"{len(refused_spine)}")
    for rid, v, eids in refused_spine:
        log(f"    {v} -> {eids}")

    log("\n-- every registrant with a Native-entity claim --")
    log(f"  {'registrant':<44}{'entity':<24}{'tier':<6}{'routes'}")
    for r in sorted(back, key=lambda x: -int(x.get("n_filings_native_clients") or 0)):
        if r["native_ownership_status"] in ("", "NO_CLAIM_FOUND"):
            continue
        log(f"  {r['registrant_name'][:42]:<44}"
            f"{r['native_ownership_entity_id']:<24}"
            f"{r['native_ownership_evidence_tier']:<6}"
            f"{r['native_ownership_routes']}")
    log("\ndone.")


if __name__ == "__main__":
    main()
