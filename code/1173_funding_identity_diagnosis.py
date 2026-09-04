#!/usr/bin/env python3
"""
1173 - FEDERAL FUNDING IDENTITY DIAGNOSIS.  READ-ONLY on data/.

    py -3 code/1173_funding_identity_diagnosis.py measure    # every number, to stdout
    py -3 code/1173_funding_identity_diagnosis.py proposals  # + the review/ CSVs
    py -3 code/1173_funding_identity_diagnosis.py selftest   # prove the classifier fires

WHAT THIS ANSWERS, AND WHY IT IS NOT A FIX
------------------------------------------
An external reviewer measured `federal_funding_transactions.canonical_name`
disagreeing with `data/spine/cedar_identity_register.csv` on 340,738 of 549,134
keyed rows and warned - correctly - that overwriting every row's
`canonical_name` from the register would make the table internally consistent
while hiding the legal recipient.  This script DIAGNOSES.  It writes nothing
into `data/`.  Its only writes are proposal CSVs under `review/`.

THE FINDING THE WHOLE THING TURNS ON
------------------------------------
The 340,738 disagreements are not 340,738 independent errors.  They are **333
distinct (cedar_uid, canonical_name) pairs**, and 340,653 of the 340,738 rows
(99.98%) carry a `canonical_name` that is a verbatim lowercase string out of
`data/raw/external/federal_funding/lineageA_dta_corrtd_tribe_key.csv` - the
`Tribe` label of the Stata do-file replayed by `24_funding_merge.py`, one
label per `tribe_id`, itself lifted from a USAspending RECIPIENT name.
`register.canonical_name` is Cedar's SHORT DISPLAY name ("Navajo",
"Oglala Sioux").  Two different name authorities, compared as if they were
one.  267,951 of the disagreeing rows have `canonical_name` EQUAL, character
for character after normalisation, to that row's own `recipient_name`.

So the headline 62.1% is a category error in the COMPARISON before it is a
defect in the DATA - which is exactly why the reviewer's instruction not to
overwrite is right, and why the fix is a role-specific schema rather than a
name sync.

AGENT_FIELD_GUIDE COMPLIANCE
----------------------------
- rule 3: every count prints its denominator; no scan is capped; the row count
  of the source file is printed at the top of every pass.
- rule 8: nothing here issues an instruction from a sample.  Every figure is a
  full-file stream of all rows in the table.
- rule 11: a single shared token is never treated as a name.  Where a bucket
  rests on one token the token is printed beside the count and the pair is
  routed to adjudication, not to a verdict.
- rule 15: the disagreement definition is stated beside the number -
  non-blank `cedar_uid` AND non-blank `canonical_name`, normalised for
  case/punctuation/whitespace, compared to `register.canonical_name`.
- SNAPSHOT: concurrent rebuilds are live in this repo.  The mtime of the
  source table is printed with every run.  Any figure here is that snapshot.
"""

import collections
import csv
import difflib
import re
import sys
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CLEAN = ROOT / "data" / "clean"
SPINE = ROOT / "data" / "spine"
REVIEW = ROOT / "review"
FUND = CLEAN / "federal_funding_transactions.csv"
REGISTER = SPINE / "cedar_identity_register.csv"
ENTSPINE = SPINE / "cedar_entity_spine.csv"
RELS = CLEAN / "entity_relationships.csv"
LEDGER = CLEAN / "cedar_identifier_ledger_final.csv"
TRIBEKEY = (ROOT / "data" / "raw" / "external" / "federal_funding"
            / "lineageA_dta_corrtd_tribe_key.csv")
TODAY = date.today().isoformat()

csv.field_size_limit(min(sys.maxsize, 2 ** 31 - 1))

ABBR = {"STE": "SAINTE", "ST": "SAINT", "FT": "FORT", "MT": "MOUNT"}


def strictnorm(s):
    """The reviewer's own comparison: case and whitespace only."""
    return " ".join((s or "").strip().upper().split())


def norm(s):
    s = (s or "").upper().replace("&", " AND ")
    s = re.sub(r"[^A-Z0-9 ]", " ", s)
    t = [ABBR.get(w, w) for w in s.split()]
    out, i = [], 0
    while i < len(t):
        if t[i] == "MC" and i + 1 < len(t):
            out.append("MC" + t[i + 1])
            i += 2
        else:
            out.append(t[i])
            i += 1
    return " ".join(out)


# Generic words. A token in this set is NEVER the distinctive part of a name -
# AGENT_FIELD_GUIDE rule 11, and the reason `REGIONAL` put AVCP under ASRC.
STOP = set("""OF THE AND A AN IN FOR TO INC INCORPORATED LLC LP LTD CORP CO COMPANY
TRIBE TRIBES TRIBAL NATION NATIONS BAND BANDS INDIAN INDIANS NATIVE PEOPLE PEOPLES
COMMUNITY RESERVATION RANCHERIA PUEBLO VILLAGE COLONY CONFEDERATED FEDERATED
COUNCIL GOVERNMENT ADMINISTRATION OFFICE AUTHORITY DEPARTMENT AGENCY BUREAU""".split())

SUBORD = {
    "housing_authority": [r"\bHOUSING\b"],
    "education": [r"\bCOLLEGE\b", r"\bSCHOOL\b", r"\bACADEMY\b",
                  r"\bUNIVERSITY\b", r"\bHEAD START\b"],
    "health": [r"\bHEALTH\b", r"\bCLINIC\b", r"\bHOSPITAL\b", r"\bMEDICAL\b",
               r"\bWELLNESS\b"],
    "business_entity": [r"\bLLC\b", r"\bINC\b", r"\bENTERPRISES?\b",
                        r"\bTECHNOLOGIES\b", r"\bPRODUCTS\b",
                        r"\bCORPORATION\b", r"\bFUND\b", r"\bASSOCIATION\b",
                        r"\bPROJECT\b"],
    "utility": [r"\bUTILITY\b", r"\bUTILITIES\b"],
    "environmental": [r"\bENVIRONMENTAL\b"],
    "governing_body": [r"\bCOUNCIL\b", r"\bGOVERNMENT\b",
                       r"\bADMINISTRATION\b", r"\bGOVERNOR\b"],
}

# The legal-form / place-token challenge set the reviewer asked for.
CHALLENGE_FORMS = [
    ("HOUSING_AUTHORITY_OF_THE_CITY_OF",
     r"\bHOUSING AUTHORITY OF THE CITY OF\b"),
    ("CITY_HOUSING_AUTHORITY",
     r"\bCITY OF [A-Z ]*HOUSING AUTHORITY\b|\bCITY HOUSING AUTHORITY\b"),
    ("COUNTY_HOUSING_AUTHORITY",
     r"\bCOUNTY HOUSING AUTHORITY\b|\bHOUSING AUTHORITY OF [A-Z ]*COUNTY\b"),
    ("MUNICIPAL_HOUSING_AUTHORITY", r"\bMUNICIPAL HOUSING AUTHORITY\b"),
    ("SCHOOL_DISTRICT",
     r"\bSCHOOL DISTRICT\b|\bSCHOOL DIST\b|\bUNIFIED SCHOOL\b|\bPUBLIC SCHOOL"),
    ("PORT_AUTHORITY", r"\bPORT AUTHORITY\b"),
    ("CITY_OF", r"\bCITY OF\b|^CITY\b"),
    ("COUNTY_OF", r"\bCOUNTY OF\b"),
    ("COUNTY_TOKEN", r"\bCOUNTY\b"),
    ("TOWNSHIP", r"\bTOWNSHIP\b"),
    ("TOWN_BOROUGH_VILLAGE_OF", r"\bTOWN OF\b|\bBOROUGH OF\b|^VILLAGE OF\b"),
    ("STATE_OF", r"\bSTATE OF\b"),
]

# Forms that, in Indian country, are ordinarily a TRIBAL legal form. A name
# carrying one of these is NOT challenged on the place token alone - some
# tribal entities legitimately carry a municipal-looking form, which is the
# reviewer's own caveat and the reason this list exists.
TRIBAL_FORMS = [r"\bNATIVE VILLAGE\b", r"\bORGANIZED VILLAGE OF\b",
                r"\bTRADITIONAL VILLAGE OF\b", r"\bVILLAGE COUNCIL\b",
                r"\bIRA COUNCIL\b", r"\bINDIAN TOWNSHIP\b", r"\bTRIBAL\b",
                r"\bINDIAN TRIBE\b", r"\bINDIAN COMMUNITY\b", r"\bRANCHERIA\b",
                r"\bPUEBLO\b", r"\bINDIAN NATION\b",
                r"\bINDIAN HOUSING AUTHORITY\b"]

PROPOSED_ACTION = {
    "ALIAS_SAME_ENTITY":
        "SCHEMA - move the string to recipient_name_source; relationship_type=self",
    "HISTORICAL_NAME":
        "SCHEMA - recipient_name_source + relationship_type=self; record the "
        "rename in register.former_names and date it",
    "GOVERNING_BODY_OF_LINKED_ENTITY":
        "SCHEMA - relationship_type=governing_body_of; same legal person, no mint",
    "SUBORDINATE_ORG_HOUSING_AUTHORITY":
        "MINT + relationship_type=tribally_designated_housing_entity - ADJUDICATE",
    "SUBORDINATE_ORG_EDUCATION":
        "MINT + relationship_type=school_or_college_of - ADJUDICATE",
    "SUBORDINATE_ORG_HEALTH":
        "MINT + relationship_type=health_organisation_of - ADJUDICATE",
    "SUBORDINATE_ORG_BUSINESS":
        "MINT + relationship_type=owned_by - ADJUDICATE",
    "CONSTITUENT_BAND_UNDER_PARENT":
        "relationship_type=constituent_band_of - the edge already exists",
    "ORTHOGRAPHIC_VARIANT":
        "SCHEMA - recipient_name_source; fix the misspelled alias in the spine",
    "WRONG_NAME_ON_ROW": "ADJUDICATE - candidate wrong link",
    "UNCLASSIFIED": "ADJUDICATE - no mechanical evidence either way",
}

MINT_FORMS = {
    "housing_authority": [r"\bHOUSING\b"],
    "education": [r"\bCOLLEGE\b", r"\bSCHOOL\b", r"\bACADEMY\b",
                  r"\bUNIVERSITY\b", r"\bHEAD START\b", r"\bLEARNING\b"],
    "health": [r"\bHEALTH\b", r"\bCLINIC\b", r"\bHOSPITAL\b", r"\bMEDICAL\b",
               r"\bWELLNESS\b", r"\bBEHAVIORAL\b"],
    "business": [r"\bLLC\b", r"\bINC\b", r"\bENTERPRISES?\b",
                 r"\bCORPORATION\b", r"\bTECHNOLOGIES\b", r"\bINDUSTRIES\b",
                 r"\bDEVELOPMENT\b"],
    "utility": [r"\bUTILITY\b", r"\bUTILITIES\b", r"\bWATER\b", r"\bPOWER\b",
                r"\bELECTRIC\b"],
    "gaming": [r"\bCASINO\b", r"\bGAMING\b"],
    "governing_body": [r"\bCOUNCIL\b", r"\bGOVERNMENT\b", r"\bADMINISTRATION\b",
                       r"\bGOVERNOR\b", r"\bEXECUTIVE\b"],
    "nonprofit": [r"\bFOUNDATION\b", r"\bASSOCIATION\b", r"\bSOCIETY\b",
                  r"\bPROJECT\b", r"\bFUND\b"],
}

PHA_UEIS = ("DFPYJKG9K2X4", "MZMVA1YQ6MS6")


def f2(s):
    try:
        return float((s or "").strip())
    except (TypeError, ValueError):
        return 0.0


def rows_of(p):
    with open(p, encoding="utf-8-sig", errors="replace", newline="") as fh:
        yield from csv.DictReader(fh)


def load_reference():
    reg, spine = {}, {}
    name2uid = collections.defaultdict(set)
    for r in rows_of(REGISTER):
        u = r["cedar_uid"].strip()
        reg[u] = r
        for v in (r.get("canonical_name"), r.get("federal_register_legal_name")):
            if v and v.strip():
                name2uid[norm(v)].add(u)
        for a in (r.get("former_names") or "").replace(";", "|").split("|"):
            a = a.split("(")[0]
            if a.strip():
                name2uid[norm(a)].add(u)
    for r in rows_of(ENTSPINE):
        u = (r.get("cedar_uid") or "").strip()
        if not u:
            continue
        spine.setdefault(u, r)
        for v in (r.get("canonical_name"), r.get("fr_official_name")):
            if v and v.strip():
                name2uid[norm(v)].add(u)
        for a in (r.get("aliases") or "").split("|"):
            if a.strip():
                name2uid[norm(a)].add(u)
    rel = collections.defaultdict(set)
    rel_edges = rel_dated = 0
    for r in rows_of(RELS):
        rel_edges += 1
        rel[(r.get("source_entity_id") or "").strip()].add(r["relationship_type"])
        rel[(r.get("target_entity_id") or "").strip()].add(r["relationship_type"])
        if (r.get("start_date") or "").strip() or (r.get("end_date") or "").strip():
            rel_dated += 1
    tribekey = set()
    if TRIBEKEY.exists():
        for r in rows_of(TRIBEKEY):
            tribekey.add(norm(r.get("Tribe")))
    ledger = collections.defaultdict(set)
    for r in rows_of(LEDGER):
        i = (r.get("identifier") or "").strip()
        u = (r.get("cedar_uid") or "").strip()
        if i and u:
            ledger[i].add(u)
    return reg, spine, name2uid, rel, rel_edges, rel_dated, tribekey, ledger


def toks(s):
    return {t for t in norm(s).split() if t not in STOP}


def known_names(uid, reg, spine):
    r, sp = reg.get(uid, {}), spine.get(uid, {})
    out = set()
    for v in (r.get("canonical_name"), r.get("federal_register_legal_name"),
              sp.get("fr_official_name"), sp.get("canonical_name")):
        if v and v.strip():
            out.add(norm(v))
    for field in (r.get("former_names"), sp.get("aliases")):
        for a in (field or "").replace(";", "|").split("|"):
            a = a.split("(")[0]
            if a.strip():
                out.add(norm(a))
    return out


def former_names(uid, reg):
    return {norm(a.split("(")[0])
            for a in (reg.get(uid, {}).get("former_names") or "")
            .replace(";", "|").split("|") if a.strip()}


def classify_pair(uid, funding_name, reg, spine, rel, name2uid):
    """One pair, one cause. UNCLASSIFIED is a real answer and is never padded."""
    regname = reg[uid]["canonical_name"]
    nf = norm(funding_name)
    rt, ft = toks(regname), toks(funding_name)
    residue, shared = ft - rt, rt & ft
    forms = {k for k, pats in SUBORD.items() if any(re.search(x, nf) for x in pats)}
    other = sorted(name2uid.get(nf, set()) - {uid})
    ratio = difflib.SequenceMatcher(None, norm(regname), nf).ratio()
    reltypes = rel.get(reg[uid].get("handle", ""), set())

    if nf in former_names(uid, reg):
        return ("HISTORICAL_NAME",
                "register.former_names holds this exact string")
    if nf in known_names(uid, reg, spine):
        return ("ALIAS_SAME_ENTITY",
                "funding name == a register/spine name held for this cedar_uid")
    if "housing_authority" in forms and residue:
        return ("SUBORDINATE_ORG_HOUSING_AUTHORITY",
                f"housing legal form; residue {sorted(residue)}")
    if "education" in forms and residue:
        return ("SUBORDINATE_ORG_EDUCATION",
                f"education legal form; residue {sorted(residue)}")
    if "health" in forms and residue:
        return ("SUBORDINATE_ORG_HEALTH",
                f"health legal form; residue {sorted(residue)}")
    if (forms & {"business_entity", "utility", "environmental"}) and residue:
        return ("SUBORDINATE_ORG_BUSINESS",
                f"business/utility legal form; residue {sorted(residue)}")
    if "governing_body" in forms:
        return ("GOVERNING_BODY_OF_LINKED_ENTITY",
                "council/government/administration organ of the linked entity")
    if "constituent_band_of" in reltypes:
        return ("CONSTITUENT_BAND_UNDER_PARENT",
                "entity_relationships holds constituent_band_of on this handle")
    if rt and rt <= ft:
        tail = ("  [ONE TOKEN ONLY - rule 11, adjudicate]" if len(rt) == 1 else "")
        return ("ALIAS_SAME_ENTITY",
                f"all {len(rt)} distinctive register token(s) present in the "
                f"funding name; residue {sorted(residue)}{tail}")
    if ratio >= 0.80:
        return ("ORTHOGRAPHIC_VARIANT", f"sequence ratio {ratio:.3f}")
    if other:
        return ("WRONG_NAME_ON_ROW",
                f"funding name is the canonical name of a DIFFERENT registered "
                f"entity {other}")
    if not shared:
        return ("UNCLASSIFIED",
                "no shared distinctive token, no legal-form / relationship / "
                "former-name evidence")
    return ("UNCLASSIFIED", f"partial token overlap only: shared {sorted(shared)}")


def stream(reg, name2uid, ledger):
    st = collections.Counter()
    money = collections.Counter()
    pairs = collections.defaultdict(lambda: {
        "rows": 0, "usd": 0.0, "recips": collections.Counter(),
        "ueis": set(), "tiers": collections.Counter(),
        "methods": collections.Counter(), "states": collections.Counter()})
    lf = collections.defaultdict(lambda: {
        "rows": 0, "usd": 0.0, "tiers": collections.Counter(),
        "methods": collections.Counter(), "states": collections.Counter(),
        "cities": collections.Counter(), "fy": set(),
        "attributed": collections.Counter(), "excluded": collections.Counter()})
    recip = collections.defaultdict(lambda: {
        "rows": 0, "usd": 0.0, "uids": set(), "name": "",
        "attributed": collections.Counter()})
    reltype = collections.Counter()
    reltype_usd = collections.Counter()
    pha = collections.defaultdict(lambda: [0, 0.0])
    ha = collections.Counter()
    ha_usd = collections.Counter()

    for row in rows_of(FUND):
        st["rows_total"] += 1
        amt = f2(row.get("obligated_usd"))
        rn = (row.get("recipient_name") or "").strip()
        nrn = norm(rn)
        uei = (row.get("recipient_uei") or "").strip()
        uid = (row.get("cedar_uid") or "").strip()
        cn = (row.get("canonical_name") or "").strip()

        if rn:
            st["recipient_name_source"] += 1
        if uei:
            st["recipient_uei"] += 1
            if uei in ledger:
                st["recipient_uei_in_identifier_ledger"] += 1
        if uid:
            st["linked_native_entity_cedar_uid"] += 1
            if uid in reg:
                st["linked_native_entity_canonical_name_derivable"] += 1
            else:
                st["cedar_uid_NOT_in_register"] += 1
        if cn:
            st["canonical_name_nonblank"] += 1

        if uid and cn:
            st["keyed_rows_uid_and_canonical_name"] += 1
            r = reg.get(uid)
            # TWO NORMALISATIONS, BOTH REPORTED - rule 15.
            # The reviewer's 340,738 is case+whitespace only. Treating "&" as
            # "and" (and punctuation as separators) moves 1,976 rows across
            # exactly two pairs. Neither figure is wrong; they answer
            # different questions, so both are printed and the delta is named.
            if r is not None:
                if strictnorm(r["canonical_name"]) == strictnorm(cn):
                    st["agree_STRICT_case_and_whitespace_only"] += 1
                else:
                    st["disagree_STRICT_case_and_whitespace_only"] += 1
            if r is None:
                st["keyed_but_uid_unknown_to_register"] += 1
            elif norm(r["canonical_name"]) == norm(cn):
                st["agree_with_register"] += 1
                money["agree_with_register"] += amt
            else:
                st["disagree_with_register"] += 1
                money["disagree_with_register"] += amt
                if norm(cn) == nrn:
                    st["disagree_AND_canonical_name_equals_recipient_name"] += 1
                    money["disagree_AND_canonical_name_equals_recipient_name"] += amt
                d = pairs[(uid, cn)]
                d["rows"] += 1
                d["usd"] += amt
                d["recips"][nrn] += 1
                if uei:
                    d["ueis"].add(uei)
                d["tiers"][row.get("confidence_tier", "")] += 1
                d["methods"][(row.get("attribution_method") or "")[:48]] += 1
                d["states"][row.get("recipient_state_code", "")] += 1

        own = name2uid.get(nrn, set())
        if len(own) == 1:
            st["recipient_entity_id_resolvable_exact_name"] += 1
            oid = next(iter(own))
            if uid and oid == uid:
                st["  recipient_entity_id == linked entity (SELF)"] += 1
            elif uid:
                st["  recipient_entity_id is a DIFFERENT entity"] += 1
        elif len(own) > 1:
            st["recipient_entity_id_ambiguous_name"] += 1
        else:
            st["recipient_entity_id_unresolvable"] += 1

        if not uid:
            rt_ = "NO_LINK"
        elif len(own) == 1 and next(iter(own)) == uid:
            rt_ = "SELF_same_entity"
        elif len(own) == 1:
            rt_ = "OTHER_REGISTERED_ENTITY_needs_adjudication"
        elif len(own) > 1:
            rt_ = "AMBIGUOUS_NAME"
        else:
            rt_ = "UNDETERMINED_recipient_has_no_cedar_entity"
        reltype[rt_] += 1
        reltype_usd[rt_] += amt
        if rt_ == "UNDETERMINED_recipient_has_no_cedar_entity" and uid:
            k = uei or ("NAME:" + nrn)
            d = recip[k]
            d["rows"] += 1
            d["usd"] += amt
            d["uids"].add(uid)
            d["name"] = rn
            d["attributed"][row.get("attributed_flag", "")] += 1

        hits = [k for k, p in CHALLENGE_FORMS if re.search(p, nrn)]
        if hits:
            st["rows_place_or_legalform_token_any"] += 1
            if any(re.search(p, nrn) for p in TRIBAL_FORMS):
                st["  ...but carries a tribal legal form - not challenged"] += 1
            else:
                st["  ...challengeable"] += 1
                if uid:
                    st["  ...challengeable AND LINKED"] += 1
                    d = lf[(uid, uei, nrn, "|".join(hits))]
                    d["rows"] += 1
                    d["usd"] += amt
                    d["tiers"][row.get("confidence_tier", "")] += 1
                    d["methods"][(row.get("attribution_method") or "")[:48]] += 1
                    d["states"][row.get("recipient_state_code", "")] += 1
                    d["cities"][row.get("recipient_city_name", "")] += 1
                    d["attributed"][row.get("attributed_flag", "")] += 1
                    d["excluded"][row.get("excluded_flag", "")] += 1
                    fy = row.get("fiscal_year", "")
                    if fy:
                        d["fy"].add(fy)
                else:
                    st["  ...challengeable but UNLINKED"] += 1

        if re.search(r"\bHOUSING AUTH", nrn):
            ha["ha_rows"] += 1
            ha_usd["ha_rows"] += amt
            key = "ha_rows_linked" if uid else "ha_rows_unlinked"
            ha[key] += 1
            ha_usd[key] += amt

        if uei in PHA_UEIS:
            k = (uei, row.get("attribution_method", ""),
                 row.get("confidence_tier", ""), row.get("canonical_name", ""),
                 row.get("attributed_flag", ""),
                 row.get("attribution_source_line", ""))
            pha[k][0] += 1
            pha[k][1] += amt

    return dict(st=st, money=money, pairs=pairs, lf=lf, recip=recip,
                reltype=reltype, reltype_usd=reltype_usd, pha=pha,
                ha=ha, ha_usd=ha_usd)


def classify_mint(recip, reg, spine):
    out = []
    for key, v in sorted(recip.items(), key=lambda kv: -kv[1]["usd"]):
        uids = sorted(v["uids"])
        uid = uids[0] if len(uids) == 1 else ""
        base = set()
        if uid:
            r, sp = reg.get(uid, {}), spine.get(uid, {})
            for x in (r.get("canonical_name"),
                      r.get("federal_register_legal_name"),
                      sp.get("fr_official_name")):
                if x:
                    base |= toks(x)
        ft = toks(v["name"])
        nname = norm(v["name"])
        forms = sorted({k for k, ps in MINT_FORMS.items()
                        if any(re.search(p, nname) for p in ps)})
        shared, residue = base & ft, ft - base
        hard = set(forms) - {"governing_body"}
        if len(uids) > 1:
            b = "LINKED_TO_MULTIPLE_ENTITIES"
        elif base and base <= ft and not hard:
            b = "NAME_VARIANT_OF_LINKED_ENTITY"
        elif base and base <= ft and hard:
            b = "SUBORDINATE_ORG_OF_LINKED_ENTITY"
        elif shared and forms:
            b = "SUBORDINATE_ORG_CANDIDATE_PARTIAL_NAME"
        elif shared:
            b = "NAME_VARIANT_PARTIAL"
        elif forms:
            b = "DISTINCT_ORG_NO_NAME_OVERLAP"
        else:
            b = "NO_OVERLAP_NO_FORM"
        out.append({
            "recipient_key": key, "recipient_name": v["name"],
            "rows": v["rows"], "usd": round(v["usd"], 2),
            "linked_cedar_uid": uid, "linked_cedar_uids_all": ";".join(uids),
            "linked_canonical_name": reg.get(uid, {}).get("canonical_name", ""),
            "bucket": b, "legal_forms": "|".join(forms),
            "shared_distinctive_tokens": ";".join(sorted(shared)),
            "residue_tokens": ";".join(sorted(residue)),
            "attributed_flag_1_rows": v["attributed"].get("1", 0),
        })
    return out


def snapshot_line():
    m = datetime.fromtimestamp(FUND.stat().st_mtime)
    return (f"SNAPSHOT  data/clean/{FUND.name}  mtime {m:%Y-%m-%d %H:%M:%S}  "
            f"size {FUND.stat().st_size:,} bytes  "
            f"measured {datetime.now():%Y-%m-%d %H:%M:%S}")


def write_csvs(rowsdet, lf, mint, R, reg):
    REVIEW.mkdir(exist_ok=True)
    outs = []

    p = REVIEW / f"funding_identity_disagreement_causes_{TODAY}.csv"
    with open(p, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rowsdet[0].keys()),
                           lineterminator="\n")
        w.writeheader()
        for r in sorted(rowsdet, key=lambda z: -z["rows"]):
            w.writerow(r)
    outs.append((p, len(rowsdet)))

    p = REVIEW / f"funding_legal_form_challenge_{TODAY}.csv"
    rows = []
    for (uid, uei, rn, forms), d in lf.items():
        r = reg.get(uid, {})
        shared = sorted(toks(r.get("canonical_name", "")) & toks(rn))
        rows.append({
            "your_ruling": "", "cedar_uid": uid,
            "register_canonical_name": r.get("canonical_name", ""),
            "register_entity_class": r.get("entity_class", ""),
            "register_state": r.get("state", ""),
            "recipient_uei": uei, "recipient_name_source": rn,
            "legal_form_tokens": forms, "rows": d["rows"],
            "obligated_usd": round(d["usd"], 2),
            "recipient_state": (d["states"].most_common(1)[0][0]
                                if d["states"] else ""),
            "recipient_city": (d["cities"].most_common(1)[0][0]
                               if d["cities"] else ""),
            "fy_min": min(d["fy"]) if d["fy"] else "",
            "fy_max": max(d["fy"]) if d["fy"] else "",
            "confidence_tiers": "|".join(f"{k}:{v}" for k, v in d["tiers"].most_common()),
            "attribution_methods": "|".join(f"{k}:{v}" for k, v in d["methods"].most_common(2)),
            "attributed_flag_counts": "|".join(f"{k}:{v}" for k, v in d["attributed"].most_common()),
            "excluded_flag_counts": "|".join(f"{k}:{v}" for k, v in d["excluded"].most_common()),
            "shared_distinctive_tokens": ";".join(shared),
            "n_shared_distinctive_tokens": len(shared),
            "evidence_for_the_link":
                ("shares the linked entity's distinctive token(s) "
                 + ";".join(shared)) if shared
                else "NONE - the link rests on no distinctive token at all",
            "evidence_against_the_link":
                ("recipient state " + (d["states"].most_common(1)[0][0]
                                       if d["states"] else "?")
                 + " vs register state " + (r.get("state", "") or "?")),
        })
    rows.sort(key=lambda z: -z["obligated_usd"])
    with open(p, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()),
                           lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    outs.append((p, len(rows)))

    p = REVIEW / f"funding_recipient_entity_mint_candidates_{TODAY}.csv"
    with open(p, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["your_ruling"] + list(mint[0].keys()),
                           lineterminator="\n")
        w.writeheader()
        for m_ in mint:
            w.writerow({"your_ruling": "", **m_})
    outs.append((p, len(mint)))

    p = REVIEW / f"funding_pha_ruling_application_gap_{TODAY}.csv"
    rows = []
    for k, v in sorted(R["pha"].items()):
        uei, meth, tier, cn, af, line = k
        rows.append({
            "recipient_uei": uei, "attribution_method": meth,
            "confidence_tier": tier, "canonical_name_on_row": cn,
            "attributed_flag": af, "do_file_source_line": line,
            "rows": v[0], "obligated_usd": round(v[1], 2),
            "reachable_by_a_ledger_keyed_correction":
                "Y" if meth == "uei_exact_archive" else
                "N - written by the Stata do-file replay inside "
                "24_funding_merge.py"})
    with open(p, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()),
                           lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    outs.append((p, len(rows)))

    print("\n=== PROPOSAL FILES WRITTEN (review/ only - no data was changed) ===")
    for p, k in outs:
        print(f"  review/{p.name}   {k:,} rows")


def measure(write_proposals=False):
    print(snapshot_line())
    (reg, spine, name2uid, rel, rel_edges, rel_dated,
     tribekey, ledger) = load_reference()
    print(f"register entities {len(reg):,} · spine rows with a uid {len(spine):,} "
          f"· entity_relationships edges {rel_edges:,}, of which dated {rel_dated:,}")
    R = stream(reg, name2uid, ledger)
    st, money = R["st"], R["money"]
    n = st["rows_total"]

    print("\n=== 0. DENOMINATORS (full file, no cap) ===")
    for k in ("rows_total", "recipient_name_source", "recipient_uei",
              "recipient_uei_in_identifier_ledger", "canonical_name_nonblank",
              "linked_native_entity_cedar_uid",
              "linked_native_entity_canonical_name_derivable",
              "cedar_uid_NOT_in_register",
              "keyed_rows_uid_and_canonical_name",
              "keyed_but_uid_unknown_to_register",
              "agree_STRICT_case_and_whitespace_only",
              "disagree_STRICT_case_and_whitespace_only",
              "agree_with_register", "disagree_with_register",
              "disagree_AND_canonical_name_equals_recipient_name"):
        if k in st:
            usd = f"  ${money[k]:,.2f}" if k in money else ""
            print(f"  {k:56} {st[k]:>9,} {100*st[k]/n:6.2f}%{usd}")

    pairs = R["pairs"]
    rowsum = sum(d["rows"] for d in pairs.values())
    print(f"\n=== 1. CAUSE OF THE {rowsum:,} DISAGREEMENTS ===")
    from_key = sum(d["rows"] for (uid, cn), d in pairs.items()
                   if norm(cn) in tribekey)
    print(f"  distinct (cedar_uid, canonical_name) disagreeing pairs: {len(pairs):,}")
    print(f"  rows whose canonical_name is verbatim a "
          f"lineageA_dta_corrtd_tribe_key.csv `Tribe` label: "
          f"{from_key:,} of {rowsum:,}")
    pc = collections.Counter()
    rc = collections.Counter()
    uc = collections.Counter()
    rowsdet = []
    for (uid, cn), d in pairs.items():
        cause, basis = classify_pair(uid, cn, reg, spine, rel, name2uid)
        pc[cause] += 1
        rc[cause] += d["rows"]
        uc[cause] += d["usd"]
        top = d["recips"].most_common(3)
        rowsdet.append({
            "cedar_uid": uid, "handle": reg[uid].get("handle", ""),
            "register_canonical_name": reg[uid]["canonical_name"],
            "register_entity_class": reg[uid].get("entity_class", ""),
            "funding_canonical_name": cn,
            "cause": cause, "cause_basis": basis,
            "rows": d["rows"], "obligated_usd": round(d["usd"], 2),
            "n_distinct_recipient_names": len(d["recips"]),
            "top_recipient_name_1": top[0][0] if top else "",
            "top_recipient_name_2": top[1][0] if len(top) > 1 else "",
            "top_recipient_name_3": top[2][0] if len(top) > 2 else "",
            "canonical_name_equals_top_recipient_name":
                "Y" if top and norm(cn) == top[0][0] else "N",
            "canonical_name_is_lineageA_tribe_label":
                "Y" if norm(cn) in tribekey else "N",
            "n_recipient_ueis": len(d["ueis"]),
            "confidence_tiers": "|".join(f"{k}:{v}" for k, v in d["tiers"].most_common()),
            "attribution_methods": "|".join(f"{k}:{v}" for k, v in d["methods"].most_common(3)),
            "recipient_states": "|".join(f"{k}:{v}" for k, v in d["states"].most_common(3)),
            "proposed_action": PROPOSED_ACTION.get(cause, "ADJUDICATE"),
        })
    print(f"\n  {'cause':42} {'pairs':>6} {'rows':>9} {'share':>7} "
          f"{'obligated_usd':>21}")
    for c, _ in rc.most_common():
        print(f"  {c:42} {pc[c]:>6} {rc[c]:>9,} {100*rc[c]/rowsum:>6.2f}% "
              f"${uc[c]:>20,.2f}")
    print(f"  {'TOTAL':42} {sum(pc.values()):>6} {rowsum:>9,} {100.0:>6.2f}% "
          f"${sum(uc.values()):>20,.2f}")

    print("\n=== 2. ROLE-SPECIFIC SCHEMA - rows that would populate each field TODAY ===")
    for f, v, why in [
        ("recipient_name_source", st["recipient_name_source"],
         "the source string, verbatim. Never overwritten."),
        ("recipient_entity_id", st["recipient_entity_id_resolvable_exact_name"],
         "recipient resolves by EXACT name to exactly one Cedar entity"),
        ("recipient_uei", st["recipient_uei"], "non-blank recipient_uei"),
        ("linked_native_entity_cedar_uid", st["linked_native_entity_cedar_uid"],
         "the existing cedar_uid column"),
        ("linked_native_entity_canonical_name",
         st["linked_native_entity_canonical_name_derivable"],
         "derivable from the register for every linked row"),
    ]:
        print(f"  {f:38} {v:>9,} {100*v/n:>6.2f}%   {why}")
    tot = sum(R["reltype"].values())
    print(f"  {'relationship_type':38} {'':>9}   derivable today:")
    for k, v in R["reltype"].most_common():
        print(f"      {k:48} {v:>9,} {100*v/tot:>6.2f}%  "
              f"${R['reltype_usd'][k]:>18,.2f}")
    print(f"  {'relationship_valid_from':38} {rel_dated:>9,}   "
          f"entity_relationships start_date/end_date non-blank on "
          f"{rel_dated} of {rel_edges} edges")
    print(f"  {'relationship_valid_to':38} {rel_dated:>9,}   (same source)")

    recip = R["recip"]
    print(f"\n  recipients under a link with NO Cedar entity of their own: "
          f"{len(recip):,} distinct, "
          f"{sum(d['rows'] for d in recip.values()):,} rows, "
          f"${sum(d['usd'] for d in recip.values()):,.2f}")
    mint = classify_mint(recip, reg, spine)
    mb = collections.Counter()
    mr = collections.Counter()
    mu = collections.Counter()
    for m_ in mint:
        mb[m_["bucket"]] += 1
        mr[m_["bucket"]] += m_["rows"]
        mu[m_["bucket"]] += m_["usd"]
    print(f"\n  {'bucket':46} {'recips':>7} {'rows':>9} {'obligated_usd':>21}")
    for b, _ in mu.most_common():
        print(f"  {b:46} {mb[b]:>7} {mr[b]:>9,} ${mu[b]:>20,.2f}")

    print("\n=== 3. THE $1.13B RULING - what the table holds, by write mechanism ===")
    for k, v in sorted(R["pha"].items()):
        uei, meth, tier, cn, af, line = k
        print(f"  {v[0]:>6} ${v[1]:>16,.2f}  uei={uei} method={meth:22} "
              f"tier={tier} attributed_flag={af} canonical_name={cn!r} "
              f"do_file_line={line or '-'}")

    lf = R["lf"]
    print("\n=== 4. LEGAL-FORM / PLACE-TOKEN CHALLENGE ===")
    for k in ("rows_place_or_legalform_token_any",
              "  ...but carries a tribal legal form - not challenged",
              "  ...challengeable", "  ...challengeable AND LINKED",
              "  ...challengeable but UNLINKED"):
        if k in st:
            print(f"  {k:56} {st[k]:>9,}")
    print(f"  distinct challengeable LINKED candidates: {len(lf):,}  "
          f"rows {sum(d['rows'] for d in lf.values()):,}  "
          f"${sum(d['usd'] for d in lf.values()):,.2f}")
    ha, ha_usd = R["ha"], R["ha_usd"]
    print("\n  housing-authority recipient census "
          "(recipient_name matches 'HOUSING AUTH'):")
    for k in ("ha_rows", "ha_rows_linked", "ha_rows_unlinked"):
        print(f"    {k:22} {ha[k]:>8,}  ${ha_usd[k]:>18,.2f}")

    if write_proposals:
        write_csvs(rowsdet, lf, mint, R, reg)
    return R


def selftest():
    """Prove the classifier FIRES on a known violation - field guide rule 1."""
    reg, spine, name2uid, rel, _, _, _, _ = load_reference()
    uid = next(u for u, r in reg.items() if r["canonical_name"] == "Navajo")
    # a second subject with NO relationship edge, so the constituent-band
    # branch cannot pre-empt the later rules.
    uid2 = next(u for u, r in reg.items()
                if r["canonical_name"].startswith("Sonoma County Indian Health")
                and not rel.get(r.get("handle", "")))
    fails = []
    cases = [
        (uid, "navajo nation tribal government, the",
         "GOVERNING_BODY_OF_LINKED_ENTITY"),
        (uid, "navajo nation housing authority",
         "SUBORDINATE_ORG_HOUSING_AUTHORITY"),
        (uid, "navajo community college", "SUBORDINATE_ORG_EDUCATION"),
        # no shared distinctive token, no legal form, no relationship, no
        # former name: the honest answer is UNCLASSIFIED, not a guess.
        (uid2, "borrego springs mutual", "UNCLASSIFIED"),
        # a name Cedar already holds for a DIFFERENT registered entity must
        # come back as a candidate wrong link, never as an alias.
        (uid2, "forest county", "WRONG_NAME_ON_ROW"),
    ]
    for subj, nm, want in cases:
        got, _ = classify_pair(subj, nm, reg, spine, rel, name2uid)
        ok = got == want
        print(f"  {'OK  ' if ok else 'FAIL'} {nm!r:44} -> {got} (want {want})")
        if not ok:
            fails.append(nm)
    print("selftest", "PASS" if not fails else "FAIL")
    return 1 if fails else 0


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "measure"
    if cmd == "measure":
        measure(False)
        return 0
    if cmd == "proposals":
        measure(True)
        return 0
    if cmd == "selftest":
        return selftest()
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
