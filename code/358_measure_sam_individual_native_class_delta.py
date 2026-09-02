#!/usr/bin/env python3
"""
Cedar Press - 358: what the SAM FY2000-2007 backfill adds to the individually
Native-owned business class, and what of it may be published.

WHAT THIS IS
------------
`163_load_sam_contract_awards.py` loads and reconciles the six SAM extracts.
This file asks the one question the load cannot answer on its own:

    the "Individually Native-owned business" class was created on 2026-08-26
    with 45 firms seeded from hand rulings. The AMERICAN INDIAN and NATIVE
    AMERICAN extracts are the FEDERAL population for that class. How much of it
    is new, how much money is on it, and what of that is publishable?

MAKES NO NETWORK CALLS. Writes NOTHING to `data/clean` and nothing to the spine
or the ledger - every output goes to `review/`. That is deliberate on two
counts: a new `data/clean` table would move six shipping counters that are
already failing for another agent (named in AGENTS.md, 2026-08-26 ~20:15), and
a SAM socio-economic flag is a SELF-CERTIFICATION, so nothing here is entitled
to become a spine row.

THE FOUR THINGS IT REFUSES TO DO
--------------------------------
1. **It never calls a candidate a class member.** Every UEI counted here landed
   through `awardeeBusinessTypeName`, which is a partial string match over a
   self-certified business type. Per `docs/INDIVIDUAL_NATIVE_CLASS_PROPOSAL.md`
   section 4 the ceiling on that evidence is **tier C**, and tier C never
   publishes alone. The output column is `spine_action = UNRULED_CANDIDATE`.
2. **It never sums the two classes.** ENTITY_OWNED and INDIVIDUAL_NATIVE_OWNED
   are separate populations and every figure here is emitted per class with no
   total line to quote by accident.
3. **It never writes NOT_NATIVE.** A firm with no Native flag is
   `NO_CLAIM_FOUND` - absence of a self-certification is not evidence against.
   MEASURED on this class already: 76.7% of its dollars carry no Native
   set-aside at all, against 57.2% project-wide.
4. **It never publishes a private individual.** The per-firm file is INTERNAL.
   The publishable artefact is AGGREGATE ONLY, with any cell resolving to fewer
   than 3 firms suppressed and the suppression reported. There is deliberately
   no per-firm publishable view and no surrogate-keyed one either: a digest of a
   UEI is reversible by enumerating SAM's own entity space, so a "de-identified"
   per-firm file would be a disclosure with an extra step.

THE PRIVACY CLASSIFIER IS IMPORTED, NOT REWRITTEN
-------------------------------------------------
`privacy_class()` comes from `171_build_individual_native_verification.py`.
Standing rule 8: one matcher, imported, never re-implemented - a second copy
drifts, and a drifted privacy classifier fails OPEN, which is the direction that
costs a person. It is deliberately conservative: a name of three tokens or fewer
carrying no corporate form is POSSIBLE_PERSONAL_NAME even when it is a firm,
because an unnecessary withholding costs a column and a wrong disclosure does
not.

    py -3 code/358_measure_sam_individual_native_class_delta.py
"""

import csv
import importlib.util
import json
import sys
from collections import Counter, defaultdict
from datetime import date, datetime, timezone
from pathlib import Path

csv.field_size_limit(10 ** 9)

CEDAR = Path(__file__).resolve().parent.parent
CLEAN = CEDAR / "data" / "clean"
SPINE = CEDAR / "data" / "spine" / "cedar_entity_spine.csv"
REVIEW = CEDAR / "review"
RAW = CEDAR / "data" / "raw" / "contracts" / "sam_contract_awards"

SAM = CLEAN / "sam_prime_contracts_fy2000_2007.csv"
REGISTER = CLEAN / "individual_native_firm_register.csv"
LEDGER = CLEAN / "cedar_identifier_ledger_final.csv"
LOADER_STATE = RAW / "_loader_state.json"

TODAY = date.today().isoformat()
TAG = "358_measure_sam_individual_native_class_delta"

CLASSES = ("ENTITY_OWNED", "INDIVIDUAL_NATIVE_OWNED")
SMALL_CELL = 3

# Entity classes whose presence in the ledger means the identifier is ALREADY
# accounted for as an entity-owned firm, and is therefore NOT a candidate for
# the individual class. Read from the spine, never guessed from a name.
ENTITY_OWNED_SPINE_CLASSES = {
    "Federally recognized tribe",
    "Federally recognized Alaska Native Village",
    "Alaska Native Village Corporation",
    "Alaska Native Regional Corporation",
    "ANCSA Group Corporation",
    "Native Hawaiian Organization",
    "State-recognized tribe",
    "Tribal College or University",
    "BIE School",
    "Urban Indian Organization",
    "Intertribal Organization",
    "Native Community Development Financial Institution",
    "Native Financial Institution",
    "Federal-level constituency entity",
    "State-level constituency entity",
    "Federal-level self-governance consortium",
}
INDIVIDUAL_SPINE_CLASS = "Individually Native-owned business"

# The flags that assert an ENTITY owns the firm - a tribe, an ANC, an NHO, a
# tribal college. `americanIndianOwned` and the minority-owned
# `nativeAmericanOwned` are POINTEDLY not here: both are assertions about a
# PERSON, and either can be true of a tribal enterprise or of a sole proprietor.
TRIBAL_FLAGS = [
    "flag_us_tribal_government", "flag_tribally_owned_firm",
    "flag_indian_tribe_federally_recognized",
    "flag_alaskan_native_corporation_owned", "flag_native_hawaiian_org_owned",
    "flag_tribal_college", "flag_alaskan_native_servicing_institution",
    "flag_native_hawaiian_servicing_institution",
]


def now():
    return datetime.now(timezone.utc).isoformat()


def import_privacy_class():
    """The ONE privacy classifier, imported from 171. Never re-implemented."""
    p = CEDAR / "code" / "171_build_individual_native_verification.py"
    spec = importlib.util.spec_from_file_location("m171", p)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["m171"] = mod
    spec.loader.exec_module(mod)
    return mod.privacy_class


def read_rows(path, required):
    """Rows of a CSV, RAISING when a column this pass reads is absent.

    DEFECT CLASS 2b: an absent column name reads as an empty source. `102`
    counted two datasets on a `tribe_id` column neither file has and printed
    0.0% coverage for nineteen days. A missing column is a stop, never a zero.
    """
    with open(path, encoding="utf-8-sig", newline="") as fh:
        rd = csv.DictReader(fh)
        missing = [c for c in required if c not in (rd.fieldnames or [])]
        if missing:
            raise SystemExit(
                f"REFUSING {path.name}: column(s) absent from the header: "
                f"{missing}. Present: {rd.fieldnames}")
        for row in rd:
            yield row


def write_csv(path, columns, rows):
    tmp = path.with_suffix(path.suffix + ".part")
    with open(tmp, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=columns, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)
    tmp.replace(path)


# ---------------------------------------------------------------------------
def load_class_members():
    """The 45 firms already IN the class, by identifier. Uppercased."""
    by_uei, by_cage, sids = {}, {}, set()
    for r in read_rows(REGISTER, ["surrogate_entity_id", "identifier_type",
                                  "identifier"]):
        sid = (r["surrogate_entity_id"] or "").strip()
        sids.add(sid)
        ident = (r["identifier"] or "").strip().upper()
        if not ident:
            continue
        if r["identifier_type"].strip().upper() == "UEI":
            by_uei[ident] = sid
        elif r["identifier_type"].strip().upper() == "CAGE":
            by_cage[ident] = sid
    return by_uei, by_cage, sids


def load_ledger_index():
    """UEI/CAGE -> the spine classes it is bound to, with the best tier.

    A tier is INHERITED from the ledger row, never assigned here. The tier is
    carried so a caller can see WHICH rows are strong; nothing in this file
    promotes on it.
    """
    spine_class = {}
    for r in read_rows(SPINE, ["tribe_id", "entity_class"]):
        spine_class[(r["tribe_id"] or "").strip()] = (r["entity_class"] or "").strip()

    uei, cage = defaultdict(set), defaultdict(set)
    tiers_u, tiers_c = defaultdict(set), defaultdict(set)
    for r in read_rows(LEDGER, ["identifier_type", "identifier", "tribe_id",
                                "confidence_tier"]):
        ident = (r["identifier"] or "").strip().upper()
        tid = (r["tribe_id"] or "").strip()
        tier = (r["confidence_tier"] or "").strip()
        if not ident or not tid:
            continue
        # A tier-X row is a NEGATIVE ruling. It says the link was REFUSED, so it
        # must never be read as "this identifier is accounted for". DEFECT 3.
        if tier == "X":
            continue
        cls = spine_class.get(tid, "")
        t = (r["identifier_type"] or "").strip().upper()
        if t == "UEI":
            uei[ident].add(cls)
            tiers_u[ident].add(tier)
        elif t == "CAGE":
            cage[ident].add(cls)
            tiers_c[ident].add(tier)
    return uei, cage, tiers_u, tiers_c, spine_class


# ---------------------------------------------------------------------------
def scan_sam(pc):
    """STREAM the SAM table once, aggregating to the UEI. Never materialised.

    The table is ~380k rows x 90 columns. Reading it into a list costs upwards
    of 2 GB; the aggregation below is a few tens of thousands of firms.
    """
    need = ["variant_class", "matched_variants", "class_conflict",
            "awardee_uei", "cage_code", "ultimate_parent_uei",
            "action_obligation", "fiscal_year", "native_flag_any",
            "variant_match_basis", "include_in_native_universe",
            "novelty", "double_count_risk", "flag_sole_proprietorship",
            "funding_department", "naics_code", "setaside", "contract_number",
            "dnb_awardee_name", "dnb_awardee_legal_name", "dnb_awardee_state",
            "dnb_ultimate_parent_name", "source_columns_absent"] + TRIBAL_FLAGS

    firms = {}
    per_class = {c: {"rows": 0, "native_rows": 0, "obl": 0.0,
                     "native_obl": 0.0, "piid": set(), "uei": set(),
                     "trap_rows": 0, "trap_obl": 0.0,
                     "no_claim_rows": 0, "conflict_rows": 0,
                     "setaside_rows": 0, "setaside_obl": 0.0}
                 for c in CLASSES}
    fy_cells = defaultdict(lambda: {"rows": 0, "obl": 0.0, "firms": set()})
    agency_cells = defaultdict(lambda: {"rows": 0, "obl": 0.0, "firms": set()})
    naics_cells = defaultdict(lambda: {"rows": 0, "obl": 0.0, "firms": set()})
    setaside_cells = defaultdict(lambda: {"rows": 0, "obl": 0.0, "firms": set()})
    conflicts = []
    variants_seen = Counter()
    absent_cols = Counter()
    conflict_basis = Counter()
    conflict_uei = defaultdict(set)
    # The variant co-occurrence matrix, rebuilt from `matched_variants` on the
    # merged table rather than from the extracts, so it can never disagree with
    # the table it describes.
    pair = Counter()
    solo = Counter()
    n = 0

    for r in read_rows(SAM, need):
        n += 1
        cls = r["variant_class"]
        if cls not in per_class:
            raise SystemExit(f"REFUSING: unknown variant_class {cls!r} on row {n}")
        obl = float(r["action_obligation"] or 0)
        uei = (r["awardee_uei"] or "").strip().upper()
        native = r["include_in_native_universe"] == "1"
        pcls = per_class[cls]
        pcls["rows"] += 1
        pcls["obl"] += obl
        if r["contract_number"]:
            pcls["piid"].add(r["contract_number"])
        if uei:
            pcls["uei"].add(uei)
        if native:
            pcls["native_rows"] += 1
            pcls["native_obl"] += obl
        if r["variant_match_basis"] == "HOUSING_AUTHORITY_PUBLIC_TRIBAL_ONLY":
            pcls["trap_rows"] += 1
            pcls["trap_obl"] += obl
        if r["native_flag_any"] != "1":
            pcls["no_claim_rows"] += 1
        if r["class_conflict"] == "1":
            pcls["conflict_rows"] += 1
        sa = (r["setaside"] or "").strip()
        if sa and sa.upper() not in ("NONE", "NO SET ASIDE USED", "NO SET ASIDE USED."):
            pcls["setaside_rows"] += 1
            pcls["setaside_obl"] += obl
        vs = sorted(filter(None, (r["matched_variants"] or "").split(";")))
        for v in vs:
            variants_seen[(cls, v)] += 1
            for w in vs:
                pair[(v, w)] += 1
        if len(vs) == 1:
            solo[vs[0]] += 1
        for c in filter(None, (r["source_columns_absent"] or "").split(";")):
            absent_cols[c] += 1

        if r["class_conflict"] == "1":
            # WHAT IS THE ENTITY_OWNED ASSIGNMENT ACTUALLY RESTING ON?
            # The merge rule gives a contested transaction to ENTITY_OWNED. That
            # is right when an entity-ownership flag is present. It is NOT
            # evidence when the only reason an entity variant claimed the row is
            # that `awardeeBusinessTypeName=INDIAN` partial-matches the business
            # type "American Indian Owned" - which is an assertion about a
            # PERSON. Those rows are assigned by a SUBSTRING, and they are named
            # here so they can be ruled instead of inherited.
            tribal = any(r.get(f, "").upper() == "YES" for f in TRIBAL_FLAGS)
            basis = ("TRIBAL_ENTITY_FLAG_PRESENT" if tribal
                     else "SUBSTRING_ONLY_NO_ENTITY_OWNERSHIP_FLAG")
            conflict_basis[(cls, basis)] += 1
            conflict_basis[(cls, basis, "obl")] += obl
            if uei:
                conflict_uei[(cls, basis)].add(uei)
            conflicts.append({
                "contract_number": r["contract_number"],
                "fiscal_year": r["fiscal_year"],
                "matched_variants": r["matched_variants"],
                "variant_class_assigned": cls,
                "entity_claim_basis": basis,
                "entity_claim_basis_meaning": (
                    "An entity-ownership flag (tribal government, tribally "
                    "owned, federally recognized tribe, ANC, NHO, tribal "
                    "college) is YES on this row, so ENTITY_OWNED is supported "
                    "by evidence."
                    if tribal else
                    "NO entity-ownership flag is YES. The only Native flags are "
                    "americanIndianOwned / nativeAmericanOwned, which assert "
                    "something about a PERSON. This row was assigned to "
                    "ENTITY_OWNED because awardeeBusinessTypeName=INDIAN "
                    "partial-matches the business type 'American Indian Owned' "
                    "- a SUBSTRING, not evidence of tribal ownership. NEEDS A "
                    "RULING."),
                "awardee_uei": uei,
                "action_obligation": f"{obl:.2f}",
                "native_flag_any": r["native_flag_any"],
                "rule": "ENTITY_OWNED wins a contested transaction: a tribally "
                        "owned firm whose owner also self-certifies as an "
                        "individual American Indian is a tribal enterprise, not "
                        "an individual. The conflict is RECORDED so it can be "
                        "ruled, never resolved silently.",
                "spine_action": "UNRULED - no class is asserted by this file.",
                "generated": TODAY,
            })

        # --- publishable aggregate cells, native universe only -------------
        if native:
            fy_cells[(cls, r["fiscal_year"])]["rows"] += 1
            fy_cells[(cls, r["fiscal_year"])]["obl"] += obl
            agency_cells[(cls, r["funding_department"] or "NOT_RECORDED")]["rows"] += 1
            agency_cells[(cls, r["funding_department"] or "NOT_RECORDED")]["obl"] += obl
            n2 = (r["naics_code"] or "")[:2] or "NOT_RECORDED"
            naics_cells[(cls, n2)]["rows"] += 1
            naics_cells[(cls, n2)]["obl"] += obl
            # The set-aside NAME, published verbatim per class. Cedar does not
            # define "a Native set-aside" here - the vocabulary is published so
            # any definition can be applied to it, rather than one being
            # invented in this file and quoted as if it were the source's.
            sa_key = sa or "NOT_RECORDED"
            setaside_cells[(cls, sa_key)]["rows"] += 1
            setaside_cells[(cls, sa_key)]["obl"] += obl
            if uei:
                fy_cells[(cls, r["fiscal_year"])]["firms"].add(uei)
                agency_cells[(cls, r["funding_department"] or "NOT_RECORDED")]["firms"].add(uei)
                naics_cells[(cls, n2)]["firms"].add(uei)
                setaside_cells[(cls, sa_key)]["firms"].add(uei)

        if not uei:
            continue
        f = firms.get(uei)
        if f is None:
            f = firms[uei] = {
                # Rows and dollars are held PER CLASS. A UEI can carry rows in
                # both classes - measured, 883 of 8,375 do - and summing them
                # into one per-firm total books ENTITY_OWNED dollars onto the
                # individual class, which is the exact error this whole table
                # exists to prevent.
                "uei": uei, "cls": set(), "variants": set(), "rows": 0,
                "obl": 0.0, "native_rows": 0, "native_obl": 0.0,
                "rows_by_class": Counter(), "obl_by_class": Counter(),
                "native_rows_by_class": Counter(),
                "native_obl_by_class": Counter(),
                "fy": set(), "fy_by_class": defaultdict(set),
                "name": "", "legal_name": "", "state": "",
                "parent_uei": "", "parent_name": "", "cage": set(),
                "sole_prop": "", "conflict": "0", "novelty": Counter(),
                "double_count_rows": 0, "setaside_rows": 0,
            }
        f["cls"].add(cls)
        f["variants"].update(filter(None, (r["matched_variants"] or "").split(";")))
        f["rows"] += 1
        f["obl"] += obl
        f["rows_by_class"][cls] += 1
        f["obl_by_class"][cls] += obl
        if native:
            f["native_rows"] += 1
            f["native_obl"] += obl
            f["native_rows_by_class"][cls] += 1
            f["native_obl_by_class"][cls] += obl
        if r["fiscal_year"]:
            f["fy"].add(r["fiscal_year"])
            f["fy_by_class"][cls].add(r["fiscal_year"])
        f["name"] = f["name"] or (r["dnb_awardee_name"] or "").strip()
        f["legal_name"] = f["legal_name"] or (r["dnb_awardee_legal_name"] or "").strip()
        f["state"] = f["state"] or (r["dnb_awardee_state"] or "").strip()
        f["parent_uei"] = f["parent_uei"] or (r["ultimate_parent_uei"] or "").strip()
        f["parent_name"] = f["parent_name"] or (r["dnb_ultimate_parent_name"] or "").strip()
        if r["cage_code"]:
            f["cage"].add(r["cage_code"].strip().upper())
        f["sole_prop"] = f["sole_prop"] or r["flag_sole_proprietorship"]
        if r["class_conflict"] == "1":
            f["conflict"] = "1"
        f["novelty"][r["novelty"]] += 1
        if r["double_count_risk"] == "1":
            f["double_count_rows"] += 1
        if sa and sa.upper() not in ("NONE", "NO SET ASIDE USED"):
            f["setaside_rows"] += 1

    for f in firms.values():
        f["privacy_class"] = pc(f["legal_name"] or f["name"])
    return (n, firms, per_class, fy_cells, agency_cells, naics_cells,
            setaside_cells, conflicts, variants_seen, absent_cols,
            conflict_basis, conflict_uei, pair, solo)


# ---------------------------------------------------------------------------
def classify_firm(f, reg_uei, reg_cage, led_uei, led_cage, tiers_u, tiers_c):
    """Where does this UEI already sit? Returns (status, detail).

    Four states, and they are NOT the same fact:
      ALREADY_IN_INDIVIDUAL_CLASS - the class register already holds it
      HELD_AS_ENTITY_OWNED        - the ledger binds it to a tribe/ANC/NHO/etc,
                                    so it is somebody's enterprise and is NOT a
                                    candidate for the individual class
      HELD_UNCLASSED              - the ledger binds it to a spine row whose
                                    class this pass does not recognise
      NEW_TO_BOTH                 - unknown to the register and to the ledger
    """
    cages = f["cage"]
    if f["uei"] in reg_uei:
        return "ALREADY_IN_INDIVIDUAL_CLASS", reg_uei[f["uei"]]
    for c in cages:
        if c in reg_cage:
            return "ALREADY_IN_INDIVIDUAL_CLASS", reg_cage[c]

    bound = set(led_uei.get(f["uei"], set()))
    tiers = set(tiers_u.get(f["uei"], set()))
    for c in cages:
        bound |= set(led_cage.get(c, set()))
        tiers |= set(tiers_c.get(c, set()))
    if not bound:
        return "NEW_TO_BOTH", ""
    if INDIVIDUAL_SPINE_CLASS in bound:
        return "ALREADY_IN_INDIVIDUAL_CLASS", "ledger"
    named = sorted(x for x in bound if x)
    if any(x in ENTITY_OWNED_SPINE_CLASSES for x in named):
        return "HELD_AS_ENTITY_OWNED", ";".join(named) + "|tier:" + ",".join(sorted(tiers))
    return "HELD_UNCLASSED", ";".join(named) + "|tier:" + ",".join(sorted(tiers))


def cell_rows(cells, dimension):
    """Publishable aggregate rows, with cells under 3 firms SUPPRESSED.

    The suppression is REPORTED, never a silent drop - the CGCC precedent in
    AGENTS.md. A suppressed row keeps its label and loses its value.
    """
    out = []
    for (cls, key), v in sorted(cells.items()):
        nf = len(v["firms"])
        supp = nf < SMALL_CELL
        out.append({
            "variant_class": cls,
            "dimension": dimension,
            "value": key,
            "n_firms": "" if supp else nf,
            "n_rows": "" if supp else v["rows"],
            "action_obligation_usd": "" if supp else f"{v['obl']:.2f}",
            "value_suppressed_small_cell": "1" if supp else "0",
            "suppression_rule": (f"fewer than {SMALL_CELL} firms in the cell"
                                 if supp else ""),
            "universe": "include_in_native_universe = 1 only",
            "class_rule": "ENTITY_OWNED and INDIVIDUAL_NATIVE_OWNED are never "
                          "summed into one Native total.",
            "generated": TODAY,
        })
    return out


# ---------------------------------------------------------------------------
def main():
    if not SAM.exists():
        sys.exit(f"{SAM.name} does not exist - run 163 load first")
    pc = import_privacy_class()
    reg_uei, reg_cage, sids = load_class_members()
    print(f"  individual-Native class register : {len(sids)} firms, "
          f"{len(reg_uei)} UEI + {len(reg_cage)} CAGE identifiers")
    led_uei, led_cage, tiers_u, tiers_c, spine_class = load_ledger_index()
    print(f"  ledger index (tier X excluded)    : {len(led_uei):,} UEI, "
          f"{len(led_cage):,} CAGE")
    print(f"  streaming {SAM.name} ...")
    (n, firms, per_class, fy_cells, agency_cells, naics_cells,
     setaside_cells, conflicts, variants_seen, absent_cols, conflict_basis,
     conflict_uei, pair, solo) = scan_sam(pc)
    print(f"    {n:,} rows, {len(firms):,} distinct awardee UEI")

    # ---- per-variant load facts, read from the loader's own checkpoint -----
    state = json.loads(LOADER_STATE.read_text(encoding="utf-8-sig"))
    per_variant = []
    for tok, s in sorted(state["processed"].items(),
                         key=lambda kv: -kv[1]["rows_in"]):
        per_variant.append({
            "variant": s["variant"], "class": s["class"],
            "export_token": tok, "file": s["file"],
            "rows_in": s["rows_in"], "rows_added": s["rows_added"],
            "rows_already_present_from_another_variant":
                s["rows_already_present"],
            "source_columns_absent": ";".join(s.get("source_columns_absent", [])),
        })

    # ---- the individual-Native class delta --------------------------------
    IC = "INDIVIDUAL_NATIVE_OWNED"
    ind = [f for f in firms.values() if f["native_rows_by_class"][IC] > 0]
    delta = Counter()
    rows_out = []
    for f in sorted(ind, key=lambda x: -x["native_obl_by_class"][IC]):
        status, detail = classify_firm(f, reg_uei, reg_cage, led_uei, led_cage,
                                       tiers_u, tiers_c)
        # SCOPED TO THE CLASS. f["native_obl"] would include this firm's
        # ENTITY_OWNED rows and book them onto the individual class.
        f_obl = f["native_obl_by_class"][IC]
        f_rows = f["native_rows_by_class"][IC]
        delta[status] += 1
        delta[status + "__obl"] += f_obl
        delta[status + "__rows"] += f_rows
        person = f["privacy_class"] == "POSSIBLE_PERSONAL_NAME"
        rows_out.append({
            "awardee_uei": f["uei"],
            "cage_code": ";".join(sorted(f["cage"])),
            "variant_class": "INDIVIDUAL_NATIVE_OWNED",
            "matched_variants": ";".join(sorted(f["variants"])),
            "class_conflict": f["conflict"],
            "class_membership_status": status,
            "class_membership_detail": detail,
            "sam_rows_this_class": f["rows_by_class"][IC],
            "sam_rows_in_native_universe_this_class": f_rows,
            "action_obligation_native_universe_this_class_usd": f"{f_obl:.2f}",
            "sam_rows_other_class_entity_owned": f["rows_by_class"]["ENTITY_OWNED"],
            "action_obligation_other_class_entity_owned_usd":
                f"{f['native_obl_by_class']['ENTITY_OWNED']:.2f}",
            "class_scoping_note": "The two class figures are held apart on this "
                                  "row and are NEVER added. A UEI can carry "
                                  "transactions in both.",
            "fiscal_years_this_class": ";".join(sorted(f["fy_by_class"][IC])),
            "rows_with_a_setaside": f["setaside_rows"],
            "native_claim_status": ("SELF_CERTIFIED_NATIVE_FLAG"
                                    if f_rows else "NO_CLAIM_FOUND"),
            "novelty_vs_prime_contracts": ";".join(
                f"{k}={v}" for k, v in sorted(f["novelty"].items())),
            "double_count_risk_rows": f["double_count_rows"],
            "flag_sole_proprietorship": f["sole_prop"],
            "privacy_class": f["privacy_class"],
            "firm_legal_name_is_person": "UNKNOWN" if f["privacy_class"] in (
                "POSSIBLE_PERSONAL_NAME", "NO_CORPORATE_FORM", "UNKNOWN") else "0",
            "publish_name": "0",
            "publish_uei": "0" if person else "1",
            "publish_uei_reason": (
                "WITHHELD - SAM's public entity search resolves a UEI to a "
                "legal name and address, and this legal name reads as a private "
                "individual's. Publishing the UEI publishes the name by one hop."
                if person else
                "Federal identifier on a name carrying a corporate form. Not "
                "D&B Open Data. Publishes."),
            "consent_status": "NOT_ASKED",
            "publication_policy_inherited_from":
                "nrc_meeting_participants; ferc_ex_parte_parties",
            "evidence_ceiling": "C",
            "evidence_ceiling_reason":
                "awardeeBusinessTypeName is a PARTIAL string match over a "
                "SELF-CERTIFIED business type. Tier C never publishes alone. "
                "MEASURED: americanIndianOwned = YES on 2,846 of 8,273 rows of "
                "the TRIBAL extract, all tribal enterprises; and CNI "
                "Administration Services LLC, a Chickasaw Nation company, "
                "carries soleProprietorship = YES.",
            "spine_action": "UNRULED_CANDIDATE - a SAM socio-economic flag is a "
                            "self-certification, never a tier-A link and never "
                            "a spine row on its own.",
            "dnb_open_data_restricted": "1",
            "dnb_awardee_name": f["name"],
            "dnb_awardee_legal_name": f["legal_name"],
            "dnb_awardee_state": f["state"],
            "dnb_ultimate_parent_name": f["parent_name"],
            "ultimate_parent_uei": f["parent_uei"],
            "generated": TODAY,
            "generated_by": TAG,
        })

    REVIEW.mkdir(parents=True, exist_ok=True)
    cand = REVIEW / f"sam_individual_native_candidates_{TODAY}.csv"
    if rows_out:
        write_csv(cand, list(rows_out[0].keys()), rows_out)

    dist = (cell_rows(fy_cells, "fiscal_year")
            + cell_rows(agency_cells, "funding_department")
            + cell_rows(naics_cells, "naics_2_digit")
            + cell_rows(setaside_cells, "setaside_name"))
    distf = REVIEW / f"sam_class_distributions_PUBLISHABLE_{TODAY}.csv"
    write_csv(distf, list(dist[0].keys()), dist)

    conf = REVIEW / f"sam_class_conflicts_{TODAY}.csv"
    if conflicts:
        write_csv(conf, list(conflicts[0].keys()), conflicts)

    # ---- the report -------------------------------------------------------
    priv = Counter()
    for f in firms.values():
        for c in f["cls"]:
            priv[(c, f["privacy_class"])] += 1

    report = {
        "generated": now(),
        "generated_by": TAG,
        "makes_network_calls": False,
        "writes_to_data_clean": False,
        "sam_table": SAM.name,
        "sam_rows": n,
        "distinct_awardee_uei": len(firms),
        "per_variant": per_variant,
        "per_class": {
            c: {
                "rows": v["rows"],
                "rows_in_native_universe": v["native_rows"],
                "rows_partial_match_trap": v["trap_rows"],
                "obligation_partial_match_trap_usd": round(v["trap_obl"], 2),
                "rows_with_no_native_claim": v["no_claim_rows"],
                "rows_class_conflict": v["conflict_rows"],
                "distinct_piid": len(v["piid"]),
                "distinct_uei": len(v["uei"]),
                "action_obligation_native_universe_usd": round(v["native_obl"], 2),
                "rows_with_a_setaside_of_any_kind": v["setaside_rows"],
                "obligation_with_a_setaside_of_any_kind_usd":
                    round(v["setaside_obl"], 2),
                "share_of_dollars_with_no_setaside_OF_ANY_KIND_pct": (
                    round(100.0 * (1 - v["setaside_obl"] / v["obl"]), 1)
                    if v["obl"] else None),
                "setaside_metric_warning": (
                    "This counts ANY set-aside, not a NATIVE set-aside. Do NOT "
                    "compare it with the class's published 76.7% or the "
                    "project-wide 57.2%, which are NATIVE-set-aside shares. The "
                    "full set-aside name distribution is published per class in "
                    "the aggregate file so any definition can be applied to it "
                    "without re-deriving one here."),
            } for c, v in per_class.items()},
        "no_total_row": ("ENTITY_OWNED and INDIVIDUAL_NATIVE_OWNED are "
                         "different populations and are never summed."),
        "individual_native_class_delta": {
            "class_register_firms_before": len(sids),
            "candidate_firms_measured": len(ind),
            "already_in_individual_class": delta["ALREADY_IN_INDIVIDUAL_CLASS"],
            "already_in_individual_class_obligation_usd":
                round(delta["ALREADY_IN_INDIVIDUAL_CLASS__obl"], 2),
            "held_as_entity_owned_not_candidates":
                delta["HELD_AS_ENTITY_OWNED"],
            "held_as_entity_owned_obligation_usd":
                round(delta["HELD_AS_ENTITY_OWNED__obl"], 2),
            "held_unclassed": delta["HELD_UNCLASSED"],
            "held_unclassed_obligation_usd": round(delta["HELD_UNCLASSED__obl"], 2),
            "new_to_both_register_and_ledger": delta["NEW_TO_BOTH"],
            "new_to_both_obligation_usd": round(delta["NEW_TO_BOTH__obl"], 2),
            "new_to_both_rows": delta["NEW_TO_BOTH__rows"],
            "all_dollar_figures_here_are_scoped_to": (
                "INDIVIDUAL_NATIVE_OWNED rows only. 883 of 8,375 UEIs carry "
                "transactions in BOTH classes; a per-firm total that pooled "
                "them would book tribal-enterprise dollars onto the individual "
                "class."),
            "status_meaning": {
                "ALREADY_IN_INDIVIDUAL_CLASS": "the 45-firm register or a "
                    "non-X ledger row already binds this identifier to the class",
                "HELD_AS_ENTITY_OWNED": "the ledger binds this identifier to a "
                    "tribe, ANC, NHO or other entity - it is somebody's "
                    "enterprise and is NOT a candidate for the individual class",
                "HELD_UNCLASSED": "bound in the ledger to a spine row whose "
                    "class this pass does not recognise - needs a human",
                "NEW_TO_BOTH": "unknown to the register and to the ledger. This "
                    "is the discovery, and every one of them is tier C.",
            },
        },
        "privacy": {
            f"{c}|{k}": v for (c, k), v in sorted(priv.items())},
        "privacy_rule": (
            "May publish: contract facts, class totals, distributions, "
            "small-cell-suppressed aggregates. May NOT publish, in bulk or "
            "singly: legal/DBA/owner name, address, any person-to-ancestry "
            "pairing, and the UEI where the legal name is a person's - SAM's "
            "public entity search resolves a UEI to that name. consent_status "
            "is NOT_ASKED on every row. Absence is NO_CLAIM_FOUND, never "
            "NOT_NATIVE."),
        "small_cell_threshold_firms": SMALL_CELL,
        "cells_suppressed": sum(1 for r in dist
                                if r["value_suppressed_small_cell"] == "1"),
        "cells_published": sum(1 for r in dist
                               if r["value_suppressed_small_cell"] == "0"),
        "source_columns_absent_row_counts": dict(absent_cols),
        "variant_row_counts_after_dedup": {
            f"{c}|{v}": k for (c, v), k in sorted(variants_seen.items())},
        "variant_overlap_rows": {
            f"{a}|{b}": k for (a, b), k in sorted(pair.items()) if a <= b},
        "variant_rows_matched_by_that_variant_alone": dict(sorted(solo.items())),
        "class_conflict_basis": {
            f"{k[0]}|{k[1]}": v for k, v in sorted(conflict_basis.items())
            if len(k) == 2},
        "class_conflict_basis_obligation_usd": {
            f"{k[0]}|{k[1]}": round(v, 2)
            for k, v in sorted(conflict_basis.items()) if len(k) == 3},
        "class_conflict_basis_distinct_uei": {
            f"{k[0]}|{k[1]}": len(v) for k, v in sorted(conflict_uei.items())},
        "class_conflict_basis_meaning": (
            "SUBSTRING_ONLY_NO_ENTITY_OWNERSHIP_FLAG counts transactions given "
            "to ENTITY_OWNED with NO tribal/ANC/NHO ownership flag on the row. "
            "The entity variant that claimed them is INDIAN, and it claimed "
            "them because 'American Indian Owned' contains the string 'INDIAN'. "
            "Neither the variant nor the flags separate the two classes; these "
            "rows need a ruling, and until they get one their class column is "
            "provisional."),
        "outputs": {
            "internal_per_firm": cand.name if rows_out else None,
            "publishable_aggregate": distf.name,
            "class_conflicts": conf.name if conflicts else None,
        },
    }
    rp = REVIEW / f"sam_individual_native_class_delta_{TODAY}.json"
    tmp = rp.with_suffix(".json.part")
    tmp.write_text(json.dumps(report, indent=1), encoding="utf-8")
    tmp.replace(rp)

    # ---- print ------------------------------------------------------------
    print("\n  === PER VARIANT (as loaded) ===")
    for v in per_variant:
        print(f"    {v['variant']:16s} [{v['class']:23s}] "
              f"in={v['rows_in']:>7,}  new={v['rows_added']:>7,}  "
              f"already_held={v['rows_already_present_from_another_variant']:>7,}"
              + (f"  ABSENT_COLS={v['source_columns_absent']}"
                 if v["source_columns_absent"] else ""))
    print("\n  === PER CLASS (never summed) ===")
    for c in CLASSES:
        v = report["per_class"][c]
        print(f"    {c:24s} rows={v['rows']:>7,}  native={v['rows_in_native_universe']:>7,}  "
              f"UEI={v['distinct_uei']:>6,}  PIID={v['distinct_piid']:>6,}  "
              f"${v['action_obligation_native_universe_usd']:,.0f}")
        print(f"      {'':22s} trap_rows={v['rows_partial_match_trap']:,} "
              f"(${v['obligation_partial_match_trap_usd']:,.0f})  "
              f"no_native_claim_rows={v['rows_with_no_native_claim']:,}  "
              f"conflict_rows={v['rows_class_conflict']:,}  "
              f"no_setaside_of_ANY_kind_share="
              f"{v['share_of_dollars_with_no_setaside_OF_ANY_KIND_pct']}%")
    d = report["individual_native_class_delta"]
    print("\n  === INDIVIDUALLY NATIVE-OWNED CLASS DELTA ===")
    print(f"    class register before                 {d['class_register_firms_before']:,} firms")
    print(f"    candidate firms in the two extracts   {d['candidate_firms_measured']:,}")
    print(f"      already in the class                {d['already_in_individual_class']:,}  "
          f"${d['already_in_individual_class_obligation_usd']:,.0f}")
    print(f"      held as ENTITY-owned (not cands)    {d['held_as_entity_owned_not_candidates']:,}  "
          f"${d['held_as_entity_owned_obligation_usd']:,.0f}")
    print(f"      held, class unrecognised            {d['held_unclassed']:,}  "
          f"${d['held_unclassed_obligation_usd']:,.0f}")
    print(f"      NEW to register AND ledger          {d['new_to_both_register_and_ledger']:,}  "
          f"${d['new_to_both_obligation_usd']:,.0f}  "
          f"({d['new_to_both_rows']:,} rows)")
    print("\n  === CLASS CONFLICT - what the ENTITY_OWNED assignment rests on ===")
    for k, v in report["class_conflict_basis"].items():
        print(f"    {k:56s} rows={v:>7,}  "
              f"UEI={report['class_conflict_basis_distinct_uei'].get(k, 0):>6,}  "
              f"${report['class_conflict_basis_obligation_usd'].get(k, 0):,.0f}")
    print("\n  === VARIANT ROWS MATCHED BY THAT VARIANT ALONE ===")
    for k, v in report["variant_rows_matched_by_that_variant_alone"].items():
        print(f"    {k:18s} {v:>8,}")
    print("\n  === PRIVACY (distinct UEI by name class) ===")
    for k, v in report["privacy"].items():
        print(f"    {k:52s} {v:,}")
    print(f"\n  publishable aggregate cells: {report['cells_published']:,} "
          f"published, {report['cells_suppressed']:,} suppressed "
          f"(<{SMALL_CELL} firms)")
    print(f"  wrote review/{distf.name}")
    if rows_out:
        print(f"  wrote review/{cand.name}   ({len(rows_out):,} firms, INTERNAL)")
    if conflicts:
        print(f"  wrote review/{conf.name}  ({len(conflicts):,} rows)")
    print(f"  wrote review/{rp.name}")


if __name__ == "__main__":
    main()
