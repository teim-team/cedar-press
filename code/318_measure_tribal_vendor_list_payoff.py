"""318 - measure what a tribal certification list is actually WORTH.

This is the point of the feasibility study.  Finding lists is easy to feel good
about; the question is how many unresolved federal contracting identifiers a
full 574-tribe sweep would plausibly resolve, and at what dollar value.  If the
answer is "few", that is a valid finding and cheaper to learn now.

THE TWO PRODUCTS, MEASURED SEPARATELY
-------------------------------------
B - the EVIDENCE layer.  A tribal government certifying a firm is a THIRD PARTY
    with authority over the ownership question, so it is a tier-A leg on the
    existing `contractors` collection.  Measured here as: how many ledger rows
    for the roster entities sit at tier B or C today, and what prime dollars
    ride on them.  Those are the rows a certification could upgrade.

A - the CERTIFICATION REGISTRY.  A dated, joinable index of "firm X is
    certified by Nation Y as of date Z, per URL".  Measured here as: how much
    of the unattributed universe is even reachable by such a registry, split by
    whether the list carries a JOINABLE IDENTIFIER or only a name.

THE RULE THAT BOUNDS EVERY NUMBER BELOW
---------------------------------------
A NAME IS NOT A KEY.  A list that carries no UEI/CAGE cannot LINK anything; it
can only produce CANDIDATES.  `cedar_match_guard.NAME_TRAPS` holds 51 tokens
("cherokee", "seminole", "apache", "creek", "river", ...) precisely because
name matching here has failed in ten distinct ways.  So the payoff is reported
in two columns that are never summed:

    resolvable_now      list carries UEI or CAGE -> a real join
    candidates_only     list carries names/addresses -> review queue input

Reading `candidates_only` as resolution is the single easiest way to overstate
this study by an order of magnitude.

NO NETWORK CALLS.  Local files only.
"""

from __future__ import annotations

import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PRIME = ROOT / "data" / "clean" / "prime_contracts.csv"
LEDGER = ROOT / "data" / "clean" / "cedar_identifier_ledger_final.csv"
REGISTRY = ROOT / "review" / "tribal_vendor_list_registry_2026-08-26.csv"
OUT = ROOT / "docs" / "TRIBAL_VENDOR_LIST_PAYOFF.json"

SCRIPT = "318_measure_tribal_vendor_list_payoff.py"
STUDY_DATE = "2026-08-26"

# 574 federally recognised tribes; the roster is 20 lower-48 + 5 ANC regional +
# 5 Alaska Native village entities.  Extrapolation is stated, never implied.
N_FEDERALLY_RECOGNISED = 574

TRUE = {"1", "Y", "YES", "TRUE", "T"}


def _require(row, cols, where):
    """Defect class 2b - RAISE on a missing column, never print a zero."""
    missing = [c for c in cols if c not in row]
    if missing:
        raise KeyError(f"{where} is missing column(s) {missing}. Refusing to "
                       f"compute a coverage figure against a column that is "
                       f"not there.")


def _t(v):
    return str(v).strip().upper() in TRUE


def scan_prime():
    """One streaming pass.  Returns the unattributed universe keyed by UEI,
    plus per-identifier dollars for the attributed side."""
    with PRIME.open(encoding="utf-8", errors="replace", newline="") as fh:
        rdr = csv.DictReader(fh)
        first = next(rdr, None)
        if first is None:
            raise SystemExit(f"{PRIME} is empty")
        _require(first, ["attributed_flag", "awardee_uei", "cage_code",
                         "awardee_name", "total_obligations", "tribe_id",
                         "confidence_tier", "recipient_state_code",
                         "reported_indian_business", "reported_buy_indian",
                         "reported_native_preference", "reported_8a",
                         "fiscal_year"], str(PRIME))

        unatt = defaultdict(lambda: {
            "usd": 0.0, "rows": 0, "name": "", "state": "",
            "ind": 0, "buy": 0, "nat": 0, "a8": 0,
            "fy_min": "9999", "fy_max": "0000"})
        att_by_uei = defaultdict(float)
        att_by_cage = defaultdict(float)
        totals = {"rows": 0, "unattributed_rows": 0,
                  "attributed_usd": 0.0, "unattributed_usd": 0.0}

        for row in ([first] + list(rdr)):
            totals["rows"] += 1
            try:
                usd = float(row["total_obligations"] or 0)
            except ValueError:
                usd = 0.0
            uei = (row["awardee_uei"] or "").strip().upper()
            cage = (row["cage_code"] or "").strip().upper()
            if row["attributed_flag"] == "0":
                totals["unattributed_rows"] += 1
                totals["unattributed_usd"] += usd
                d = unatt[uei]
                d["usd"] += usd
                d["rows"] += 1
                d["name"] = d["name"] or (row["awardee_name"] or "").strip()
                d["state"] = d["state"] or (
                    row["recipient_state_code"] or "").strip().upper()
                d["ind"] += _t(row["reported_indian_business"])
                d["buy"] += _t(row["reported_buy_indian"])
                d["nat"] += _t(row["reported_native_preference"])
                d["a8"] += _t(row["reported_8a"])
                fy = row["fiscal_year"] or ""
                if fy and fy < d["fy_min"]:
                    d["fy_min"] = fy
                if fy and fy > d["fy_max"]:
                    d["fy_max"] = fy
            else:
                totals["attributed_usd"] += usd
                if uei:
                    att_by_uei[uei] += usd
                if cage:
                    att_by_cage[cage] += usd
    return unatt, att_by_uei, att_by_cage, totals


def scan_ledger():
    with LEDGER.open(encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh))
    if rows:
        _require(rows[0], ["identifier_type", "identifier", "tribe_id",
                           "confidence_tier"], str(LEDGER))
    return rows


def load_roster():
    if not REGISTRY.exists():
        raise SystemExit(f"{REGISTRY} absent - run 316 first")
    with REGISTRY.open(encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh))
    if rows:
        _require(rows[0], ["tribe_id", "canonical_name", "verdict",
                           "list_type", "assertion_class",
                           "identifiers_present", "priority_group"],
                 str(REGISTRY))
    return rows


def main():
    roster = load_roster()
    ledger = scan_ledger()
    unatt, att_uei, att_cage, totals = scan_prime()

    roster_ids = {r["tribe_id"] for r in roster}

    # ---------------------------------------------------------------- B ----
    # Tier-upgrade headroom on rows we ALREADY hold, per roster entity.
    # A tier is INHERITED from the source row: this counts what EXISTS at B/C,
    # it never promotes anything.
    b_rows = []
    for r in roster:
        tid = r["tribe_id"]
        mine = [x for x in ledger if x["tribe_id"] == tid]
        by_tier = defaultdict(list)
        for x in mine:
            by_tier[x["confidence_tier"]].append(x)
        def dollars(recs):
            s = 0.0
            for x in recs:
                ident = (x["identifier"] or "").strip().upper()
                if x["identifier_type"] == "UEI":
                    s += att_uei.get(ident, 0.0)
                elif x["identifier_type"] == "CAGE":
                    s += att_cage.get(ident, 0.0)
            return s
        b_rows.append({
            "tribe_id": tid,
            "canonical_name": r["canonical_name"],
            "priority_group": r["priority_group"],
            "verdict": r["verdict"],
            "list_type": r["list_type"],
            "assertion_class": r["assertion_class"],
            "ledger_rows_total": len(mine),
            "tier_A": len(by_tier["A"]),
            "tier_B": len(by_tier["B"]),
            "tier_C": len(by_tier["C"]),
            "tier_X": len(by_tier["X"]),
            "upgradeable_rows_BC": len(by_tier["B"]) + len(by_tier["C"]),
            "prime_usd_on_BC_rows":
                round(dollars(by_tier["B"] + by_tier["C"]), 2),
        })

    # ---------------------------------------------------------------- A ----
    # The unattributed universe, and how much of it a certification registry
    # could even reach.
    uni = [{"uei": k, **v} for k, v in unatt.items()]
    uni.sort(key=lambda d: -d["usd"])
    uni_usd = sum(d["usd"] for d in uni)

    flagged = [d for d in uni if d["ind"] or d["buy"] or d["nat"]]
    unflagged = [d for d in uni if not (d["ind"] or d["buy"] or d["nat"]
                                        or d["a8"])]
    self_cert_ind = [d for d in uni if d["ind"]]
    buy_indian = [d for d in uni if d["buy"]]

    # States in which the 30 roster entities sit.  This is a CEILING on
    # geographic reachability for THESE 30, not a prediction.
    roster_states = {r["state"] for r in
                     csv.DictReader(REGISTRY.open(encoding="utf-8-sig",
                                                  newline=""))} \
        if False else set()
    with REGISTRY.open(encoding="utf-8-sig", newline="") as fh:
        roster_states = {(r.get("state") or "").strip().upper()
                         for r in csv.DictReader(fh)} - {""}
    in_roster_states = [d for d in uni if d["state"] in roster_states]

    top400 = uni[:400]

    def blk(rows):
        return {"identifiers": len(rows),
                "usd": round(sum(d["usd"] for d in rows), 2),
                "pct_of_identifiers": round(100 * len(rows) / len(uni), 2),
                "pct_of_usd": round(100 * sum(d["usd"] for d in rows)
                                    / uni_usd, 2)}

    # -------------------------------------------------------- extrapolate --
    found = [r for r in roster if r["verdict"].startswith("LIST_FOUND")]
    ownership = [r for r in found if r["assertion_class"] == "OWNERSHIP"]
    with_ident = [r for r in ownership
                  if any(k in (r["identifiers_present"] or "").upper()
                         for k in ("UEI", "CAGE", "EIN"))]
    # A WAF block is NOT a check. `SITE_UNREACHABLE` means the host exists
    # and answers and refuses this client on every path - it is not evidence
    # either way, so it must not sit in the denominator of a publication rate.
    # Counting it as a negative would publish our own access problem as a
    # fact about the source, which is defect class 2.
    unreachable = [r for r in roster if r["verdict"] == "SITE_UNREACHABLE"]
    checked = [r for r in roster
               if r["verdict"] not in ("NOT_CHECKED", "SITE_UNREACHABLE")]

    rate_found = (len(found) / len(checked)) if checked else 0.0
    rate_ownership = (len(ownership) / len(checked)) if checked else 0.0
    rate_joinable = (len(with_ident) / len(checked)) if checked else 0.0

    payoff = {
        "generated": STUDY_DATE,
        "script": f"code/{SCRIPT}",
        "network_requests": 0,
        "measured_from": {
            "prime_contracts": str(PRIME.relative_to(ROOT)),
            "identifier_ledger": str(LEDGER.relative_to(ROOT)),
            "registry": str(REGISTRY.relative_to(ROOT)),
        },
        "universe": {
            "prime_rows_total": totals["rows"],
            "unattributed_rows": totals["unattributed_rows"],
            "unattributed_identifiers": len(uni),
            "unattributed_usd": round(uni_usd, 2),
            "attributed_usd": round(totals["attributed_usd"], 2),
            "top400_identifiers_usd": round(
                sum(d["usd"] for d in top400), 2),
            "top400_share_of_unattributed_pct": round(
                100 * sum(d["usd"] for d in top400) / uni_usd, 2),
            "NOTE_top400": (
                "These are the top 400 raw IDENTIFIERS. The reconciliation "
                "tool's top 400 CLUSTERS ($35.81B, docs/RECONCILIATION_TOOL.md) "
                "is a different unit - 9,385 identifiers collapse to 8,876 "
                "clusters and 507 already-ruled clusters are suppressed before "
                "a human sees them. Do not reconcile the two figures by "
                "adjusting either."),
        },
        "reachability_of_the_unattributed_universe": {
            "carries_any_native_specific_flag": blk(flagged),
            "carries_american_indian_owned_self_cert": blk(self_cert_ind),
            "carries_buy_indian": blk(buy_indian),
            "carries_NO_flag_at_all": blk(unflagged),
            "in_a_roster_entity_state": blk(in_roster_states),
            "roster_states": sorted(roster_states),
            "WHY_THIS_MATTERS": (
                "The no-flag block is the one a certification list is for. "
                "Those identifiers are invisible to every flag-based discovery "
                "route Cedar Press has, so a third-party ownership assertion is "
                "the ONLY evidence that can reach them."),
        },
        "option_B_evidence_layer": {
            "definition": (
                "Tier-A upgrade headroom on identifiers ALREADY linked to the "
                "roster entities. A certification is a third-party leg, "
                "which is what tier A requires."),
            "roster_ledger_rows": sum(r["ledger_rows_total"] for r in b_rows),
            "upgradeable_rows_BC": sum(r["upgradeable_rows_BC"]
                                       for r in b_rows),
            "prime_usd_on_BC_rows": round(
                sum(r["prime_usd_on_BC_rows"] for r in b_rows), 2),
            "per_entity": b_rows,
        },
        "option_A_certification_registry": {
            "definition": (
                "A dated, joinable index of 'firm X certified by Nation Y as "
                "of date Z, per URL'. NOT a reproduction of the tribe's "
                "directory."),
            "resolvable_now_requires": "list carries UEI or CAGE",
            "candidates_only_requires": "list carries name/address only",
            "RULE": ("A name is not a key. `candidates_only` is review-queue "
                     "input and must never be reported as resolution."),
        },
        "extrapolation_to_574_tribes": {
            "roster_size": len(roster),
            "roster_checked_excluding_unreachable": len(checked),
            "roster_site_unreachable_excluded_from_rate": [
                r["tribe_id"] for r in unreachable],
            "lists_found": len(found),
            "ownership_assertions_found": len(ownership),
            "ownership_lists_carrying_a_joinable_identifier": len(with_ident),
            "rate_any_list": round(rate_found, 4),
            "rate_ownership_list": round(rate_ownership, 4),
            "rate_joinable_ownership_list": round(rate_joinable, 4),
            "projected_ownership_lists_at_574": round(
                rate_ownership * N_FEDERALLY_RECOGNISED),
            "projected_joinable_ownership_lists_at_574": round(
                rate_joinable * N_FEDERALLY_RECOGNISED),
            "THE_ASSUMPTION": (
                "The roster was stratified to OVER-sample the tribes most "
                "likely to publish - large contractors, known TERO offices, "
                "and the ANCSA corporations with the most operating companies. "
                "It deliberately also holds 5 entities Cedar Press holds "
                "nothing for. A straight rate applied to 574 is therefore an "
                "UPPER BOUND, not a central estimate. Halving it is the "
                "honest reading unless a random 30 is drawn to calibrate."),
        },
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    part = OUT.with_suffix(".json.part")
    part.write_text(json.dumps(payoff, indent=2), encoding="utf-8")
    part.replace(OUT)
    json.loads(OUT.read_text(encoding="utf-8"))       # verify by re-reading

    u = payoff["universe"]
    print(f"unattributed: {u['unattributed_identifiers']:,} identifiers  "
          f"${u['unattributed_usd'] / 1e9:.2f}B  "
          f"({u['unattributed_rows']:,} rows)")
    rr = payoff["reachability_of_the_unattributed_universe"]
    for k in ("carries_any_native_specific_flag",
              "carries_american_indian_owned_self_cert",
              "carries_NO_flag_at_all", "in_a_roster_entity_state"):
        b = rr[k]
        print(f"  {k:46s} {b['identifiers']:6,d} ids "
              f"({b['pct_of_identifiers']:5.1f}%)  "
              f"${b['usd'] / 1e9:6.2f}B ({b['pct_of_usd']:5.1f}%)")
    ob = payoff["option_B_evidence_layer"]
    print(f"\noption B headroom on the roster: {ob['upgradeable_rows_BC']:,} "
          f"tier-B/C ledger rows carrying "
          f"${ob['prime_usd_on_BC_rows'] / 1e9:.2f}B of attributed prime")
    ex = payoff["extrapolation_to_574_tribes"]
    print(f"\nchecked {ex['roster_checked_excluding_unreachable']}"
          f"/{ex['roster_size']} "
          f"({len(ex['roster_site_unreachable_excluded_from_rate'])}"
          f" unreachable, excluded from the rate); "
          f"lists found {ex['lists_found']}; ownership "
          f"{ex['ownership_assertions_found']}; joinable "
          f"{ex['ownership_lists_carrying_a_joinable_identifier']}")
    print(f"  -> projected ownership lists at 574: "
          f"{ex['projected_ownership_lists_at_574']} (UPPER BOUND)")
    print(f"\n{OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
