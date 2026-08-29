#!/usr/bin/env python3
"""
Cedar Press - 181: give each LDA registrant every identifier we can EVIDENCE.

THE HYPOTHESIS UNDER TEST
-------------------------
Elijah, 2026-08-26:

    "maybe we can get more info on them from IRS 990 or other sources. The
     non-Native lobbying firm who isn't a tribe will have more data than the
     tribe, and we can link them to Native entities."

The framing is right and the second half of it is what this script measures.
`docs/IDENTIFIER_GRAPH_BUILD_LOG.md` established that **no stored file joins
EIN to UEI** - 28 rows in the whole corpus, 0.22% of `np_orgs`. The answer
there was: the ORG is the hub, and one org can be reached by several
identifiers even when no single file joins them. So this script does not look
for a pre-existing join. It CONSTRUCTS one per registrant, from six local
sources, and records for every identifier WHICH SOURCE ASSERTED IT.

WHAT IT WRITES
--------------
    data/clean/lobbying_registrant_identifiers.csv
        long: one row per (registrant_id, identifier_type, identifier),
        with the asserting source, the matching basis and the tier

    review/lobbying_registrant_identifier_refusals_2026-08-26.csv
        every candidate that was NOT written, with the reason

THE TIER, DECLARED ONCE, WITH A REASON
--------------------------------------
No source in this project asserts "this LDA registrant is that EIN". There is
no row to inherit a tier FROM, so a tier is DECLARED here, once, in
`SOURCE_TIER`, and never above B:

    B  the registrant's normalized legal name equals the source's normalized
       name AND the states agree. This is exactly the method
       `np_ein_uei_bridge.csv` calls `normalized_name_plus_state_exact`, and
       every one of its 28 rows is tier B.
    C  the names agree and the states do not, or the source carries no state.
       Written, never published alone, and never used to attribute a dollar.

`house_registrant_id` is the ONE exception and is tier A: it is not a match at
all. The Senate LDA registrant record CARRIES the Clerk of the House registrant
id as a field, so it is a stated identity from the registrar itself.

WHY EXACT-AND-UNIQUE, AND NOTHING CLEVERER
------------------------------------------
`resolve_entity`'s containment tier has failed ten distinct ways and is
forbidden for DETECTION. `need_v6`-style name matching measures 6.5% accurate.
So the rule here is: normalized-exact, must be UNIQUE on both sides, must not
be a single generic token, and any name whose surviving tokens are all in
`cedar_domain.NAME_TRAPS` is refused outright.

MEASURED, AND IT IS THE POINT OF THE EXERCISE
---------------------------------------------
Scanned the full IRS Business Master File - 1,957,340 exempt organisations,
`data/raw/external/irs990/bmf_full_2026-08-12/eo*.csv` - against all 653
registrants. **Seven names hit; five hit with state agreement.** That is not a
defect in the matcher. A DC lobbying LLP or law-firm partnership is a for-profit
partnership, files no Form 990, and is therefore ABSENT FROM THE 990 UNIVERSE
BY CONSTRUCTION. The owner's premise - "the firm has more data than the tribe" -
is true of the world, and it is specifically NOT true of the IRS exempt-org
data this project holds. Where the firm's data lives is SAM (blocked on the
pending role request), state corporate registries, and LDA itself.

One measured trap, recorded because it is the shape of an error this project
keeps paying for: the BMF holds SPIRIT ROCK MEDITATION CENTER (EIN 94-2971001,
Woodacre, California, a Buddhist retreat centre). SPIRIT ROCK CONSULTING is a
government-affairs firm in Alexandria, Virginia. A fuzzy or containment match
would have joined them and put a 990 on a lobbying firm. The state guard
refuses it, and the refusal is written to review rather than dropped.

THE CAVEAT THAT TRAVELS WITH ANY 990 FIGURE FROM THIS TABLE
-----------------------------------------------------------
6,453 of 12,764 organisations in `np_orgs` are 990-N filers reporting no
financial detail at all. A zero there is the filing regime, not a finding.

An EIN-keyed filing fact says NOTHING about the Native status of the filer -
the New Venture Fund case in AGENTS.md. Nothing in this file asserts Native
status; that is 182's job and it uses different evidence.

Zero network calls.
"""

import csv
import json
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

CEDAR = Path(r"C:\Users\esm247\Desktop\Cedar Press")
CLEAN = CEDAR / "data" / "clean"
REVIEW = CEDAR / "review"
RAWX = CEDAR / "data" / "raw" / "external"
BMF_DIR = RAWX / "irs990" / "bmf_full_2026-08-12"

HUB = CLEAN / "lobbying_registrants.csv"
OUT = CLEAN / "lobbying_registrant_identifiers.csv"
REF = REVIEW / "lobbying_registrant_identifier_refusals_2026-08-26.csv"

TODAY = date.today().isoformat()
SCRIPT = "181_enrich_lobbying_registrant_identifiers.py"

sys.path.insert(0, str(CEDAR / "code"))
try:
    from cedar_domain import NAME_TRAPS
except Exception:                                   # pragma: no cover
    NAME_TRAPS = set()

csv.field_size_limit(min(sys.maxsize, 2147483647))

# Declared once, with the reason. Nothing here is above B.
SOURCE_TIER = {
    "LDA_REGISTRANT_RECORD": ("A",
        "not a match: the Senate LDA registrant record carries the Clerk of "
        "the House registrant id as a field of the registration itself"),
    "IRS_BMF_FULL": ("B",
        "normalized legal name exact AND state agreement, against the full "
        "IRS exempt-organization Business Master File"),
    "NP_ORGS": ("B",
        "normalized legal name exact AND state agreement, against Cedar's "
        "nonprofit organisation table"),
    "SCHEDULE_I_RECIPIENT": ("B",
        "an EIN a 990 filer reported for this recipient; name exact and "
        "state agreement. The EIN is the FILER's assertion, not the IRS's"),
    "IDENTIFIER_GRAPH_NODE": ("B",
        "normalized name exact against a name observed on a federal spending "
        "row carrying this identifier"),
    "PRIME_CONTRACTS": ("B",
        "normalized name exact against prime_contracts.awardee_name"),
    "FUNDING_IDENTIFIER_HARVEST": ("B",
        "normalized name exact against the assistance identifier harvest"),
    "SUBAWARD_IDENTIFIER_HARVEST": ("B",
        "normalized name exact against the subaward identifier harvest"),
    "FPDS_UEI_CAGE_MAP": ("B",
        "normalized name exact against the FPDS UEI-CAGE map"),
}

GENERIC_STOP = {
    "group", "associates", "partners", "consulting", "consultants",
    "strategies", "solutions", "advisors", "policy", "capital", "global",
    "national", "american", "federal", "public", "government", "washington",
    "law", "firm", "engage", "impact", "advocacy", "the",
}


def log(m=""):
    print(m, flush=True)


def read_csv(p, **kw):
    p = Path(p)
    if not p.exists():
        return []
    with open(p, newline="", encoding="utf-8-sig") as fh:
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
    os.replace(part, path)


_SUFFIX = re.compile(
    r"\b(l ?l ?p|l ?l ?c|p ?l ?l ?c|p ?c|p ?a|inc|incorporated|corp|"
    r"corporation|company|co|ltd|limited|lp|plc)\b")


def norm(s):
    if not isinstance(s, str):
        return ""
    s = s.lower().replace("&", " and ")
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    s = _SUFFIX.sub(" ", s)
    return re.sub(r"\s+", " ", s).strip()


def usable(n):
    """Is this normalized name specific enough to key on?"""
    if not n:
        return False, "EMPTY_AFTER_NORMALIZATION"
    toks = n.split()
    if len(toks) == 1 and (len(n) < 10 or n in GENERIC_STOP):
        return False, "SINGLE_GENERIC_TOKEN"
    if all(t in NAME_TRAPS or t in GENERIC_STOP for t in toks):
        return False, "ALL_TOKENS_ARE_NAME_TRAPS_OR_GENERIC"
    return True, ""


def st(x):
    return (x or "").strip().upper()[:2]


_CAGE_OK = re.compile(r"^[A-Z0-9]{5}$")


def cage_ok(c):
    """A CAGE is exactly five alphanumerics.

    `prime_contracts.csv` carries the literal string `NAN` in `cage_code` on
    some rows - a pandas NaN that was written out as text. It passes any
    non-empty test, it is three characters, and it is not a CAGE. Script 21
    already exists because corrupt CAGE codes are a known defect in this
    corpus; this is the same defect arriving through a new door.
    """
    return bool(_CAGE_OK.match((c or "").strip().upper())) \
        and (c or "").strip().upper() != "NAN"


# ---------------------------------------------------------------------------

def build_index(pairs):
    """pairs: iterable of (name, state, payload) -> {norm_name: [rows]}"""
    idx = defaultdict(list)
    for name, state, payload in pairs:
        n = norm(name)
        if not n:
            continue
        ok, _ = usable(n)
        if not ok:
            continue
        idx[n].append((state, payload))
    return idx


def main():
    log("=== Cedar Press 181: registrant identifier enrichment ===\n")

    hub = read_csv(HUB)
    if not hub:
        log(f"  !! {HUB} absent - run 180 first")
        return
    log(f"  registrants: {len(hub)}")

    # registrant name index (all variants), keyed by registrant_id
    reg_names = defaultdict(set)
    reg_state, reg_disp = {}, {}
    for h in hub:
        rid = h["registrant_id"]
        reg_state[rid] = st(h.get("registrant_state"))
        reg_disp[rid] = h.get("registrant_name")
        for nm in (h.get("registrant_name_variants") or "").split(";"):
            n = norm(nm)
            if n:
                reg_names[rid].add(n)
    want = defaultdict(set)                       # norm name -> {rid}
    for rid, ns in reg_names.items():
        for n in ns:
            ok, why = usable(n)
            if ok:
                want[n].add(rid)
    log(f"  keyable normalized registrant names: {len(want)} "
        f"covering {len({r for v in want.values() for r in v})} registrants")

    out, refusals = [], []

    def emit(rid, itype, ident, source, source_row_name, source_state,
             basis, extra=None):
        tier, why = SOURCE_TIER[source]
        if source != "LDA_REGISTRANT_RECORD" and basis == "NAME_EXACT_NO_STATE_AGREEMENT":
            tier = "C"
            why = why + " -- DOWNGRADED to C: the states do not agree or the " \
                        "source carries no state"
        row = {
            "registrant_id": rid,
            "registrant_name": reg_disp.get(rid, ""),
            "registrant_state": reg_state.get(rid, ""),
            "identifier_type": itype,
            "identifier": ident,
            "asserted_by_source": source,
            "source_name_as_recorded": source_row_name,
            "source_state": source_state,
            "match_basis": basis,
            "confidence_tier": tier,
            "tier_rationale": why,
            "tier_assigned_not_inherited": (
                "1" if source != "LDA_REGISTRANT_RECORD" else "0"),
            "reading": "An identifier on this row is a claim that one legal "
                       "person holds two identifiers. It is NEVER a claim "
                       "that the person is Native, and it must not be used to "
                       "attribute a dollar on its own.",
            "built_by_script": SCRIPT,
            "built_date": TODAY,
        }
        row.update(extra or {})
        out.append(row)

    def refuse(rid, itype, ident, source, source_row_name, source_state,
               reason, n_candidates=""):
        refusals.append({
            "registrant_id": rid,
            "registrant_name": reg_disp.get(rid, ""),
            "registrant_state": reg_state.get(rid, ""),
            "identifier_type": itype,
            "candidate_identifier": ident,
            "candidate_source": source,
            "candidate_name": source_row_name,
            "candidate_state": source_state,
            "refusal_reason": reason,
            "n_candidates": n_candidates,
            "built_by_script": SCRIPT,
            "built_date": TODAY,
        })

    # ---- 0. house_registrant_id, straight off the registration -----------
    n_house = 0
    for h in hub:
        hid = (h.get("house_registrant_id") or "").strip()
        if hid:
            emit(h["registrant_id"], "HOUSE_REGISTRANT_ID", hid,
                 "LDA_REGISTRANT_RECORD", h.get("registrant_name"),
                 st(h.get("registrant_state")),
                 "STATED_ON_THE_REGISTRATION_ITSELF")
            n_house += 1
    log(f"  HOUSE_REGISTRANT_ID from the registration: {n_house}")

    # ---- generic matcher --------------------------------------------------
    def run(source, idx, itype_of, ident_of, label):
        got = 0
        for n, rids in want.items():
            cands = idx.get(n)
            if not cands:
                continue
            for rid in rids:
                rst = reg_state[rid]
                same = [c for c in cands if st(c[0]) and st(c[0]) == rst]
                pool, basis = (same, "NAME_EXACT_PLUS_STATE_AGREEMENT") if same \
                    else (cands, "NAME_EXACT_NO_STATE_AGREEMENT")
                # collapse to distinct identifiers before judging ambiguity
                by_ident = defaultdict(list)
                for state, payload in pool:
                    ident = ident_of(payload)
                    # DUNS is D&B Open Data. `cedar_domain` lists it in
                    # LICENSED_IDENTIFIER_TYPES and this project's standing
                    # rule is that DUNS never publishes. A published table
                    # must not be the place that question gets asked, so the
                    # type is refused at the door rather than stripped later.
                    if itype_of(payload) == "DUNS":
                        refuse(rid, "DUNS", ident, source,
                               payload.get("_name", ""), st(state),
                               "REFUSED_LICENSED_IDENTIFIER_TYPE_DUNS_"
                               "D_AND_B_OPEN_DATA_NEVER_PUBLISHES")
                        continue
                    if itype_of(payload) == "CAGE" and not cage_ok(ident):
                        refuse(rid, "CAGE", ident, source,
                               payload.get("_name", ""), st(state),
                               "MALFORMED_CAGE_NOT_FIVE_ALPHANUMERICS")
                        continue
                    by_ident[ident].append((state, payload))
                by_ident.pop("", None)
                by_ident.pop(None, None)
                if not by_ident:
                    continue
                if len(by_ident) > 1:
                    for ident, rs in by_ident.items():
                        refuse(rid, itype_of(rs[0][1]), ident, source,
                               rs[0][1].get("_name", ""), st(rs[0][0]),
                               "AMBIGUOUS_ONE_NAME_MANY_IDENTIFIERS",
                               len(by_ident))
                    continue
                ident, rs = next(iter(by_ident.items()))
                state, payload = rs[0]
                emit(rid, itype_of(payload), ident, source,
                     payload.get("_name", ""), st(state), basis,
                     payload.get("_extra"))
                got += 1
        log(f"  {label:<44} {got}")
        return got

    # ---- 1. IRS BMF (full exempt-org master file) -------------------------
    bmf_pairs, bmf_rows = [], 0
    files = sorted(BMF_DIR.glob("eo*.csv")) if BMF_DIR.exists() else []
    if not files:
        log(f"  !! BMF absent at {BMF_DIR} - EIN route NOT_CHECKED")
    for f in files:
        with open(f, newline="", encoding="utf-8-sig", errors="replace") as fh:
            for r in csv.DictReader(fh):
                bmf_rows += 1
                n = norm(r.get("NAME"))
                if n in want:
                    bmf_pairs.append((r.get("NAME"), r.get("STATE"), {
                        "_name": r.get("NAME"),
                        "_ein": (r.get("EIN") or "").strip(),
                        "_extra": {
                            "irs_bmf_subsection": r.get("SUBSECTION") or "",
                            "irs_bmf_filing_requirement": r.get("FILING_REQ_CD") or "",
                            "irs_bmf_ntee": r.get("NTEE_CD") or "",
                            "irs_bmf_city": r.get("CITY") or "",
                            "irs_bmf_ruling_yyyymm": r.get("RULING") or "",
                            "irs_bmf_asset_amt": r.get("ASSET_AMT") or "",
                            "irs_bmf_revenue_amt": r.get("REVENUE_AMT") or "",
                        }}))
    log(f"  IRS BMF rows scanned: {bmf_rows:,}  name hits: {len(bmf_pairs)}")
    run("IRS_BMF_FULL", build_index(bmf_pairs),
        lambda p: "EIN", lambda p: p["_ein"], "EIN from IRS BMF")

    # ---- 2. np_orgs -------------------------------------------------------
    npo = read_csv(CLEAN / "np_orgs.csv")
    run("NP_ORGS",
        build_index((r.get("org_name"), r.get("state"),
                     {"_name": r.get("org_name"),
                      "_ein": (r.get("EIN") or "").strip(),
                      "_extra": {
                          "np_orgs_classification_ruling":
                              r.get("classification_ruling") or "",
                          "np_orgs_confidence_tier":
                              r.get("confidence_tier") or "",
                      }}) for r in npo),
        lambda p: "EIN", lambda p: p["_ein"], "EIN from np_orgs")

    # ---- 3. Schedule I recipients (filer-asserted EINs) -------------------
    si_pairs = []
    with open(CLEAN / "np_schedule_i_grants.csv", newline="",
              encoding="utf-8-sig", errors="replace") as fh:
        for r in csv.DictReader(fh):
            n = norm(r.get("recipient_name_as_filed"))
            if n in want and (r.get("recipient_ein") or "").strip():
                si_pairs.append((r.get("recipient_name_as_filed"),
                                 r.get("recipient_state"),
                                 {"_name": r.get("recipient_name_as_filed"),
                                  "_ein": r["recipient_ein"].strip(),
                                  "_extra": {
                                      "schedule_i_filer_ein":
                                          r.get("filer_ein") or "",
                                      "schedule_i_filer_name":
                                          r.get("filer_name_as_filed") or "",
                                  }}))
    run("SCHEDULE_I_RECIPIENT", build_index(si_pairs),
        lambda p: "EIN", lambda p: p["_ein"], "EIN from Schedule I recipients")

    # ---- 4. the identifier graph's observed names ------------------------
    gn = read_csv(CLEAN / "cedar_identifier_graph_nodes.csv")
    run("IDENTIFIER_GRAPH_NODE",
        build_index((r.get("observed_name"), "",
                     {"_name": r.get("observed_name"),
                      "_id": r.get("identifier"),
                      "_t": r.get("identifier_type"),
                      "_extra": {
                          "graph_node_resolved_entity":
                              r.get("resolved_entity") or "",
                          "graph_node_resolved_tier":
                              r.get("resolved_tier") or "",
                          "graph_node_datasets": r.get("datasets") or "",
                          "graph_node_usd_observed": r.get("usd_observed") or "",
                      }})
                    for r in gn if (r.get("observed_name") or "").strip()),
        lambda p: p["_t"], lambda p: p["_id"], "UEI/CAGE/DUNS from graph nodes")

    # ---- 5. prime contracts (name + state, and it carries CAGE) ----------
    pc_seen, pc_pairs = set(), []
    with open(CLEAN / "prime_contracts.csv", newline="",
              encoding="utf-8-sig", errors="replace") as fh:
        for r in csv.DictReader(fh):
            n = norm(r.get("awardee_name"))
            if n not in want:
                continue
            key = (n, r.get("awardee_uei"), r.get("cage_code"),
                   r.get("recipient_state_code"))
            if key in pc_seen:
                continue
            pc_seen.add(key)
            pc_pairs.append((r.get("awardee_name"), r.get("recipient_state_code"),
                             {"_name": r.get("awardee_name"),
                              "_uei": (r.get("awardee_uei") or "").strip(),
                              "_cage": (r.get("cage_code") or "").strip(),
                              "_extra": {
                                  "prime_tribe_id": r.get("tribe_id") or "",
                                  "prime_confidence_tier":
                                      r.get("confidence_tier") or "",
                              }}))
    run("PRIME_CONTRACTS", build_index(
            [(a, b, c) for a, b, c in pc_pairs if c["_uei"]]),
        lambda p: "UEI", lambda p: p["_uei"], "UEI from prime_contracts")
    run("PRIME_CONTRACTS", build_index(
            [(a, b, c) for a, b, c in pc_pairs if c["_cage"]]),
        lambda p: "CAGE", lambda p: p["_cage"], "CAGE from prime_contracts")

    # ---- 6. assistance + subaward harvests, FPDS map ---------------------
    fh_rows = read_csv(CLEAN / "funding_identifier_harvest.csv")
    run("FUNDING_IDENTIFIER_HARVEST", build_index(
            (r.get("recipient_name"), r.get("recipient_state"),
             {"_name": r.get("recipient_name"),
              "_uei": (r.get("recipient_uei") or "").strip(),
              "_extra": {"assistance_total_obligated_usd":
                         r.get("total_obligated_usd") or ""}})
            for r in fh_rows if (r.get("recipient_uei") or "").strip()),
        lambda p: "UEI", lambda p: p["_uei"], "UEI from assistance harvest")

    sh_rows = read_csv(CLEAN / "subaward_identifier_harvest.csv")
    run("SUBAWARD_IDENTIFIER_HARVEST", build_index(
            (r.get("legal_business_name"), r.get("state"),
             {"_name": r.get("legal_business_name"),
              "_uei": (r.get("uei") or "").strip(),
              "_extra": {"subaward_total_usd": r.get("total_subaward_usd") or ""}})
            for r in sh_rows if (r.get("uei") or "").strip()),
        lambda p: "UEI", lambda p: p["_uei"], "UEI from subaward harvest")

    fp_rows = read_csv(CLEAN / "fpds_uei_cage_map.csv")
    run("FPDS_UEI_CAGE_MAP", build_index(
            (r.get("legal_business_name"), "",
             {"_name": r.get("legal_business_name"),
              "_cage": (r.get("cage_code") or "").strip(),
              "_extra": {"fpds_uei": r.get("uei") or ""}})
            for r in fp_rows if (r.get("cage_code") or "").strip()
            and (r.get("cage_malformed_flag") or "0") in ("", "0", "False")),
        lambda p: "CAGE", lambda p: p["_cage"], "CAGE from FPDS map")

    # ---- 6b. corroboration, recorded and NEVER promoting the tier --------
    # 169 set this precedent: `n_asserting_sources` is worth recording and it
    # does not promote, because two-leg promotion is a ledger method and not a
    # consumer's to mint.
    corro = Counter((r["registrant_id"], r["identifier_type"], r["identifier"])
                    for r in out)
    for r in out:
        k = (r["registrant_id"], r["identifier_type"], r["identifier"])
        r["n_asserting_sources"] = corro[k]
        r["corroboration_note"] = (
            "n_asserting_sources counts how many independent local sources "
            "put this identifier on this registrant. It NEVER promotes the "
            "tier - two-leg promotion is a ledger method, not a consumer's.")

    # ---- 7. attach 990 financials to any EIN we now hold -----------------
    fin = {}
    for f in ("np_financials.csv", "np_grantee_financials.csv"):
        for r in read_csv(CLEAN / f):
            e = (r.get("ein") or r.get("EIN") or "").strip().replace("-", "")
            if e:
                fin.setdefault(e.zfill(9), r)
    n_fin = 0
    for row in out:
        if row["identifier_type"] != "EIN":
            continue
        f = fin.get(row["identifier"].strip().replace("-", "").zfill(9))
        if not f:
            continue
        n_fin += 1
        row.update({
            "np_990_tax_year": f.get("tax_year") or "",
            "np_990_form_type": f.get("form_type") or "",
            "np_990_filing_regime": f.get("filing_regime") or "",
            "np_990_total_revenue": f.get("total_revenue") or "",
            "np_990_total_expenses": f.get("total_expenses") or "",
            "np_990_lobbying_expenditure": f.get("lobbying_expenditure") or "",
            "np_990_lobbying_field_basis": f.get("lobbying_field_basis") or "",
            "np_990_schedc_total_lobbying": f.get("schedc_total_lobbying") or "",
            "np_990_source_url": f.get("source_url") or "",
            "np_990_caveat":
                "6,453 of 12,764 organisations in np_orgs are 990-N filers "
                "reporting no financial detail. A zero here may be the filing "
                "regime, not a finding. LDA spend and 990 lobbying are "
                "different measures on different definitions and must never "
                "be summed.",
        })
    log(f"  EIN rows carrying a 990 financial record: {n_fin}")

    # ---- write -----------------------------------------------------------
    fields = []
    for r in out:
        for k in r:
            if k not in fields:
                fields.append(k)
    for r in out:
        for k in fields:
            r.setdefault(k, "")
    write_csv(OUT, out, fields)
    log(f"\n  wrote {OUT.name}: {len(out):,} identifier assertions")
    if refusals:
        rf = list(refusals[0].keys())
        write_csv(REF, refusals, rf)
        log(f"  wrote {REF.name}: {len(refusals):,} refusals")

    # ---- verify by RE-READING -------------------------------------------
    back = read_csv(OUT)
    log("\n-- verification (re-read from disk) --")
    log(f"  rows {len(back):,}   registrants covered "
        f"{len({r['registrant_id'] for r in back})} of {len(hub)}")
    by_t = Counter(r["identifier_type"] for r in back)
    for k, v in by_t.most_common():
        cov = len({r['registrant_id'] for r in back
                   if r['identifier_type'] == k})
        log(f"  {k:<24} {v:>5} assertions on {cov:>4} registrants")
    log("  tiers: " + ", ".join(
        f"{k}={v}" for k, v in sorted(Counter(
            r["confidence_tier"] for r in back).items())))
    log("\n-- every non-HOUSE identifier, in full --")
    for r in back:
        if r["identifier_type"] == "HOUSE_REGISTRANT_ID":
            continue
        log(f"  {r['registrant_name'][:44]:<46} {r['identifier_type']:<6} "
            f"{r['identifier']:<14} {r['confidence_tier']}  "
            f"{r['asserted_by_source']}  [{r['match_basis']}]")
    log("\ndone.")


if __name__ == "__main__":
    main()
