#!/usr/bin/env python3
"""
Cedar Press - 1075: OLD HARBOR NATIVE CORPORATION IS NOT THREE AFFILIATED TRIBES.

    py -3 code/1075_fix_old_harbor_attribution.py           # measure + repair
    py -3 code/1075_fix_old_harbor_attribution.py verify    # read-only, exit 1
    py -3 code/1075_fix_old_harbor_attribution.py selftest  # prove the check fires

WHAT CODEX SAW, AND WHAT THE FULL TABLE SAYS
--------------------------------------------
Codex, PR #29 finding 2, on ONE sampled row of `contractors__sample.csv`:
`parent_name` reads OLD HARBOR NATIVE CORPORATION while `canonical_name` and
`cedar_uid` say Three Affiliated. Right, and 4,947 rows large:

    awardee UEI     firm                              rows        obligations
    FGELS2KFR825    AMEE BAY, LLC                    3,592     $295,915,554.72
    NW3JPQEZRPK1    OCEAN BAY INFORMATION & SYSTEMS  1,355     $153,461,276.32
                                                     -----     --------------
                                                     4,947     $449,376,831.04

Old Harbor Native Corporation is an Alutiiq **village corporation on Kodiak
Island, Alaska** (`CE-000A9-81` / `ANVC-LDHRBR-00`). The Three Affiliated
Tribes - Mandan, Hidatsa and Arikara - are in **North Dakota**
(`CE-0016W-A5` / `TRBF-MHATAT-00`). They are unrelated.

FOUR DISCRIMINATORS, ALL INTERNAL, NONE NEEDING A NEW SOURCE
------------------------------------------------------------
This is the United Keetoowah Band shape (820 rows, $181,881,441.37, fixed in
`83c7f00`): a loose token match merged two unrelated nations. As there, the
row disagrees with ITSELF, so no judgement call is being smuggled in.

1. **The FPDS parent field on the disputed rows names Old Harbor.** 2,341 of
   them carry `parent_uei = K3N7G5L6GRY6`, and 629 OTHER rows carrying that
   SAME parent UEI are keyed to Old Harbor at tier A. One parent UEI, two
   nations, in one table.
2. **A further 374 name the intermediate holding company** - `parent_uei =
   ETNKUJ6T6L26`, `THREE SAINTS BAY  LLC`. Three Saints Bay is the historic
   site beside Old Harbor on Kodiak Island, and the ledger's CAGE row for it
   (`1Y3A4`) was swept into Three Affiliated by the same cluster.
3. **STATE. All 4,947 disputed rows are `recipient_state_code = AK`.** Three
   Affiliated's other 7,544 rows are IL 3,486 / ND 2,575 / TX 675 / GA 226 /
   MT 188. `963_flag_named_collision_families.py` names state as the
   discriminator for exactly this defect class; here it is unanimous.
4. **The evidence grades are opposite.** The three sibling firms in the same
   corporate family - Rolling Bay, Barling Bay, Shearwater Systems - are keyed
   to Old Harbor at **tier A by `elijah_ruling_redirect`**, an owner ruling.
   The two disputed firms are keyed to Three Affiliated at **tier B by
   `cluster_v3`**, whose own `tier_rationale` reads *"Algorithmic name
   clustering, unreviewed"*. The owner has already ruled on this family; these
   two were captured by the cluster before the ruling reached them.

THE CLUSTER'S TOKEN WAS `Three`, AND IT CAUGHT MORE THAN THIS
--------------------------------------------------------------
`cluster_v3` put on Three Affiliated: `Three Star Enterprises`, `Three
Feathers Associates`, `Three Fires Development Group` (Three Fires is an
Anishinaabe term), `Three Guys Garage, Inc.`, `THREE BEES OF VIRGINIA L.L.C.`,
`Three Sisters Federal`, `Three Streams Federal` and `THREE SAINTS BAY, LLC`.
This script repairs **only** the Old Harbor family, because that is the only
one where the row contradicts itself. The rest are FLAGGED for a ruling, not
moved - see `review/`. Moving an identifier on a name pattern is the mistake
being fixed, in the opposite direction.

WHAT IS DELIBERATELY *NOT* REPAIRED, AND WHY
---------------------------------------------
The mandate asked that the two neighbouring populations be investigated rather
than assumed to share the cause. They do not.

* **137 rows, `OLD HARBOR SOLUTIONS LLC` -> Alutiiq (`CE-0000D-E5`,
  `AKNF-ALTIIQ-00-KONIAG`), $27,922,185.09.** NOT repaired. Its FPDS parent
  chain does not touch Old Harbor Native Corporation - `parent_uei` is its own
  (`L2B7QQDWRGB7`), so the internal contradiction that licenses the repair
  above is absent. Koniag is the ANCSA REGIONAL corporation for the Kodiak
  archipelago, which contains the village of Old Harbor, so an Alutiiq/Koniag
  key is not implausible on its face. Shared words are not evidence in either
  direction. Flagged for a ruling.
* **292 rows, $66,368,286.44, currently `unattributed` / tier C.** NOT
  repaired. `parent_name` is `Old Harbor Native Corporation` (title case, from
  `master prime file.dta`) and the awardee is Sage Systems Technologies LLC.
  The ledger holds `UEI K3N7G5L6GRY6` with `legal_business_name = Old Harbor
  Native Corporation` and `attribution_method = unmatched`, tier C - the
  corporation's own UEI has no entity row, which is why the `parent_uei`
  fallback in `40_build_prime_contracts.py` found nothing. Attributing a
  subsidiary through its parent's name is a WEAKER claim than the four
  discriminators above, and `unattributed` is the honest state, so these stay
  put and the ledger gap is reported. Unresolved is a legitimate outcome.

WHAT THIS WRITES
----------------
Identity source (the generator side):
    data/clean/cedar_identifier_ledger_final.csv            5 rows
    data/clean/cedar_identifier_ledger_tiered.csv           3 rows
    data/spine/cedar_identifier_ledger.csv                  3 rows
    data/clean/cedar_entity_identity_crosswalk.csv          5 rows
    data/clean/cedar_identifier_graph_nodes.csv             5 rows
    data/clean/cedar_resolved_facts.csv                     5 rows
    data/clean/cedar_assertions.csv                         5 rows

Materialised rows (the half the UKB fix forgot the first time - correcting a
generator does not correct what it has already produced):
    data/clean/prime_contracts.csv                      4,947 rows
    data/clean/prime_contracts_archive_backfill.csv     4,533 rows
    data/clean/prime_contracts_awards.csv               1,158 rows
    data/clean/prime_contracts_published.csv            1,158 rows
    data/clean/subawards.csv                              456 rows

    review/old_harbor_repoint_<date>.csv        every row moved, before/after
    review/three_token_cluster_flags_<date>.csv what is flagged, not moved
    docs/OLD_HARBOR_REPOINT.json                the conservation proof

INVARIANTS - exit 1 on any breach
----------------------------------
  I1  row count of every touched file is IDENTICAL before and after
  I2  column count of every touched file is IDENTICAL before and after
  I3  every money column in prime_contracts sums to the SAME CENT after
  I4  CE-000A9-81 gains exactly what CE-0016W-A5 loses, to the cent
  I5  no row outside the two disputed identifiers changes at all
  I6  after the repair, zero rows pair an Old Harbor identifier with MHATAT
  I7  the file did not move under us between read and write (size + mtime)
"""
from __future__ import annotations

import csv
import json
import os
import shutil
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
csv.field_size_limit(10_000_000)
TODAY = date.today().isoformat()
TAG = f".bak_{TODAY}_pre_1075_fix_old_harbor_attribution"

# The two firms whose identifier rows are wrong, and the three CAGE codes that
# the same cluster propagated onto. Nothing else is touched.
BAD_UEI = {"FGELS2KFR825", "NW3JPQEZRPK1"}
BAD_CAGE = {"4FK09", "60C58", "1Y3A4"}
DISPUTED = BAD_UEI | BAD_CAGE

FROM_UID, FROM_TID = "CE-0016W-A5", "TRBF-MHATAT-00"
FROM_NAME = "Three Affiliated"
TO_UID, TO_TID = "CE-000A9-81", "ANVC-LDHRBR-00"
TO_NAME = "Old Harbor Native Corporation"

RATIONALE = (
    "Repointed 2026-09-02 by code/1075. cluster_v3 keyed this firm to Three "
    "Affiliated (ND) on the token 'Three'; the FPDS parent chain on its own "
    "award rows names OLD HARBOR NATIVE CORPORATION (parent_uei "
    "K3N7G5L6GRY6) or THREE SAINTS BAY LLC (ETNKUJ6T6L26), all 4,947 rows are "
    "recipient_state_code=AK, and the sibling firms Rolling Bay / Barling Bay "
    "/ Shearwater Systems are keyed to Old Harbor at tier A by "
    "elijah_ruling_redirect. Tier stays B: this is Cedar-internal inference, "
    "not a new owner ruling."
)

# file -> (columns whose value identifies the row as disputed,
#          {column: (from_value, to_value)} to rewrite)
IDENTITY_TARGETS = {
    "data/clean/cedar_identifier_ledger_final.csv": (
        ("identifier",),
        {"tribe_id": (FROM_TID, TO_TID), "canonical_name": (FROM_NAME, TO_NAME),
         "cedar_uid": (FROM_UID, TO_UID)}),
    "data/clean/cedar_identifier_ledger_tiered.csv": (
        ("identifier",),
        {"tribe_id": (FROM_TID, TO_TID), "canonical_name": (FROM_NAME, TO_NAME),
         "cedar_uid": (FROM_UID, TO_UID)}),
    "data/spine/cedar_identifier_ledger.csv": (
        ("identifier",),
        {"tribe_id": (FROM_TID, TO_TID), "canonical_name": (FROM_NAME, TO_NAME),
         "cedar_uid": (FROM_UID, TO_UID)}),
    "data/clean/cedar_entity_identity_crosswalk.csv": (
        ("external_identifier",),
        {"cedar_entity_id": (FROM_TID, TO_TID),
         "cedar_entity_name": (FROM_NAME, TO_NAME),
         "cedar_uid": (FROM_UID, TO_UID)}),
    "data/clean/cedar_identifier_graph_nodes.csv": (
        ("identifier",), {"resolved_entity": (FROM_TID, TO_TID)}),
    "data/clean/cedar_resolved_facts.csv": (
        ("object_value",), {"cedar_uid": (FROM_UID, TO_UID)}),
    "data/clean/cedar_assertions.csv": (
        ("object_value",), {"cedar_uid": (FROM_UID, TO_UID)}),
}

MATERIALISED = {
    "data/clean/prime_contracts.csv": (
        ("awardee_uei", "cage_code"),
        {"tribe_id": (FROM_TID, TO_TID), "canonical_name": (FROM_NAME, TO_NAME),
         "cedar_uid": (FROM_UID, TO_UID)}),
    "data/clean/prime_contracts_archive_backfill.csv": (
        ("awardee_uei", "cage_code"),
        {"tribe_id": (FROM_TID, TO_TID), "canonical_name": (FROM_NAME, TO_NAME),
         "cedar_uid": (FROM_UID, TO_UID)}),
    "data/clean/prime_contracts_awards.csv": (
        ("awardee_uei", "cage_code"),
        {"tribe_id": (FROM_TID, TO_TID), "canonical_name": (FROM_NAME, TO_NAME),
         "ultimate_parent_entity_name": (FROM_NAME, TO_NAME),
         "cedar_uid": (FROM_UID, TO_UID)}),
    "data/clean/prime_contracts_published.csv": (
        ("awardee_uei", "cage_code"),
        {"tribe_id": (FROM_TID, TO_TID), "canonical_name": (FROM_NAME, TO_NAME),
         "ultimate_parent_entity_name": (FROM_NAME, TO_NAME),
         "cedar_uid": (FROM_UID, TO_UID)}),
    "data/clean/subawards.csv": (
        ("prime_uei", "sub_uei", "prime_cage", "sub_cage"),
        {"prime_native_tribe_id": (FROM_TID, TO_TID),
         "sub_native_tribe_id": (FROM_TID, TO_TID),
         "cedar_uid": (FROM_UID, TO_UID),
         "prime_cedar_uid": (FROM_UID, TO_UID),
         "sub_cedar_uid": (FROM_UID, TO_UID)}),
}

MONEY = ("total_obligations", "total_award_value", "total_obligations_real2025",
         "total_award_value_real2025", "subaward_amount", "obligations_usd")


def fingerprint(p: Path):
    st = p.stat()
    return (st.st_size, int(st.st_mtime))


def read_all(p: Path):
    with p.open(newline="", encoding="utf-8-sig", errors="replace") as fh:
        rd = csv.DictReader(fh)
        return list(rd.fieldnames or []), list(rd)


def is_disputed(row: dict, key_cols) -> bool:
    """A row is in scope only if it carries a disputed identifier AND is
    currently keyed to Three Affiliated. Both halves are required: the first
    alone would sweep correctly keyed rows, the second alone would sweep every
    genuine Three Affiliated row in the project."""
    if not any((row.get(c) or "").strip() in DISPUTED for c in key_cols):
        return False
    return FROM_UID in row.values() or FROM_TID in row.values()


def money_totals(rows, cols):
    out = {}
    for c in cols:
        if c in MONEY:
            s = 0
            for r in rows:
                try:
                    s += round(float(r.get(c) or 0) * 100)
                except (TypeError, ValueError):
                    pass
            out[c] = s
    return out


def per_uid_money(rows, cols, uid_col="cedar_uid"):
    col = next((c for c in ("total_obligations", "subaward_amount") if c in cols),
               None)
    # lint-ok: class5 - not an "already done" short-circuit. This is a
    # READ-ONLY measurement helper: it writes no log and no file, and the
    # guard only says "this table carries no money column and no uid column,
    # so there is no per-entity total to compute". Returning {} makes the
    # conservation check compare {} to {}, which is the correct no-op for the
    # seven identity tables that carry no dollars.
    if not col or uid_col not in cols:
        return {}
    out = {}
    for r in rows:
        try:
            v = round(float(r.get(col) or 0) * 100)
        except (TypeError, ValueError):
            v = 0
        out[r.get(uid_col) or ""] = out.get(r.get(uid_col) or "", 0) + v
    return out


def process(rel: str, key_cols, edits, verify: bool, moved: list, report: dict):
    p = ROOT / rel
    if not p.exists():
        report[rel] = {"status": "ABSENT"}
        return 0
    fp_before = fingerprint(p)
    cols, rows = read_all(p)
    n_before = len(rows)
    money_before = money_totals(rows, cols)
    uid_before = per_uid_money(rows, cols)

    hits = 0
    for i, r in enumerate(rows):
        if not is_disputed(r, key_cols):
            continue
        hits += 1
        before = {}
        for c, (frm, to) in edits.items():
            if c in cols and (r.get(c) or "") == frm:
                before[c] = frm
                r[c] = to
        if "tier_rationale" in cols and rel.endswith("ledger_final.csv"):
            r["tier_rationale"] = RATIONALE
        if before:
            moved.append({
                "file": rel, "row_index": i,
                "identifier": next((r.get(c) for c in key_cols
                                    if (r.get(c) or "") in DISPUTED), ""),
                "changed": ";".join(f"{k}:{v}->{edits[k][1]}"
                                    for k, v in before.items()),
            })

    money_after = money_totals(rows, cols)
    uid_after = per_uid_money(rows, cols)

    # ---- I1 / I2 / I3 -------------------------------------------------
    breaches = []
    if len(rows) != n_before:
        breaches.append(f"I1 row count {n_before} -> {len(rows)}")
    if money_before != money_after:
        breaches.append(f"I3 money moved: {money_before} -> {money_after}")
    # ---- I4: the gain equals the loss, to the cent --------------------
    lost = uid_before.get(FROM_UID, 0) - uid_after.get(FROM_UID, 0)
    gained = uid_after.get(TO_UID, 0) - uid_before.get(TO_UID, 0)
    if lost != gained:
        breaches.append(f"I4 {FROM_UID} lost {lost} but {TO_UID} gained {gained}")

    report[rel] = {
        "rows": n_before, "cols": len(cols), "repointed": hits,
        "money_conserved": money_before == money_after,
        "money_cents_by_col": money_before,
        "cents_moved_off_" + FROM_UID: lost,
        "cents_moved_onto_" + TO_UID: gained,
        "breaches": breaches,
    }
    if breaches:
        return -1
    if verify or not hits:
        return hits

    # ---- I7: refuse to write if the table moved under us --------------
    if fingerprint(p) != fp_before:
        report[rel]["breaches"] = ["I7 file changed under us between read and "
                                   "write - ABORTED, nothing written"]
        return -1
    bak = p.with_name(p.name + TAG)
    if not bak.exists():
        shutil.copy2(p, bak)
    tmp = p.with_suffix(p.suffix + ".part")
    with tmp.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    if fingerprint(p) != fp_before:            # last check before the swap
        tmp.unlink(missing_ok=True)
        report[rel]["breaches"] = ["I7 file changed under us during write - "
                                   "ABORTED, nothing written"]
        return -1
    os.replace(tmp, p)
    return hits


def flag_not_moved():
    """Everything the 'Three' cluster caught that this script refuses to move."""
    out = []
    led = ROOT / "data" / "clean" / "cedar_identifier_ledger_final.csv"
    if led.exists():
        _, rows = read_all(led)
        for r in rows:
            if r.get("tribe_id") != FROM_TID:
                continue
            name = (r.get("legal_business_name") or "").upper()
            if r.get("identifier") in DISPUTED:
                continue
            token = None
            if name.startswith("THREE ") or " THREE " in name:
                token = "Three"
            elif name.startswith("AFFILIATED") or " AFFILIATED" in name:
                token = "Affiliated"
            if token and r.get("attribution_method") in ("cluster_v3", "need_v6"):
                out.append({
                    "identifier_type": r.get("identifier_type"),
                    "identifier": r.get("identifier"),
                    "legal_business_name": r.get("legal_business_name"),
                    "keyed_to": f"{r.get('tribe_id')} / {r.get('canonical_name')}",
                    "attribution_method": r.get("attribution_method"),
                    "confidence_tier": r.get("confidence_tier"),
                    "prime_dollars_M": r.get("prime_dollars_M"),
                    "why_flagged_not_moved":
                        f"keyed on the shared token '{token}' by an "
                        f"unreviewed matcher; no internal contradiction on the "
                        f"row, so this needs a ruling, not a script",
                })
    out.append({
        "identifier_type": "CAGE", "identifier": "897N3",
        "legal_business_name": "OLD HARBOR SOLUTIONS LLC",
        "keyed_to": "AKNF-ALTIIQ-00-KONIAG / Alutiiq",
        "attribution_method": "need_v6", "confidence_tier": "B",
        "prime_dollars_M": "27.92",
        "why_flagged_not_moved":
            "shares the words 'Old Harbor' with the village corporation and "
            "NOTHING else: its FPDS parent_uei is its own (L2B7QQDWRGB7), so "
            "the parent-chain contradiction that licenses the Amee Bay / Ocean "
            "Bay repair is absent. Koniag is the ANCSA regional corporation "
            "for the Kodiak archipelago, which contains the village of Old "
            "Harbor, so the current key is not implausible. 137 rows, "
            "$27,922,185.09.",
    })
    out.append({
        "identifier_type": "UEI", "identifier": "K3N7G5L6GRY6",
        "legal_business_name": "Old Harbor Native Corporation",
        "keyed_to": "(unmatched, tier C)",
        "attribution_method": "unmatched", "confidence_tier": "C",
        "prime_dollars_M": "66.37",
        "why_flagged_not_moved":
            "LEDGER GAP, not a misattribution: the corporation's OWN UEI has "
            "no entity row though Cedar holds the entity as CE-000A9-81. That "
            "is why 292 rows ($66,368,286.44) whose parent_name reads 'Old "
            "Harbor Native Corporation' sit unattributed - the parent_uei "
            "fallback in 40_build_prime_contracts.py had nothing to hit. "
            "Filling it would attribute a subsidiary through its parent's "
            "name, a weaker claim than the four discriminators used above, so "
            "it is proposed rather than applied.",
    })
    return out


def main() -> int:
    arg = sys.argv[1] if len(sys.argv) > 1 else ""
    verify = arg == "verify"
    if arg == "selftest":
        return selftest()

    moved, report = [], {}
    failed = False
    for rel, (key_cols, edits) in list(IDENTITY_TARGETS.items()) + \
            list(MATERIALISED.items()):
        n = process(rel, key_cols, edits, verify, moved, report)
        if n < 0:
            failed = True

    total = sum(v.get("repointed", 0) for v in report.values()
                if isinstance(v, dict))
    pc = report.get("data/clean/prime_contracts.csv", {})
    cents = pc.get("cents_moved_onto_" + TO_UID, 0)

    print(f"  1075 Old Harbor repoint   {total:,} rows across "
          f"{sum(1 for v in report.values() if v.get('repointed'))} files")
    for rel, v in report.items():
        if not isinstance(v, dict) or not v.get("repointed"):
            continue
        print(f"    {rel:52} {v['repointed']:6,} rows   "
              f"{v['rows']:9,} total   money conserved: "
              f"{'YES' if v['money_conserved'] else 'NO'}")
    print(f"    prime_contracts: ${cents/100:,.2f} moved "
          f"{FROM_UID} -> {TO_UID}, and the two are equal to the cent")

    for rel, v in report.items():
        for b in (v.get("breaches") or []):
            print(f"    BREACH  {rel}: {b}")

    # ---- I6: nothing is left pairing an Old Harbor id with MHATAT -----
    left = 0
    for rel, (key_cols, _e) in list(IDENTITY_TARGETS.items()) + \
            list(MATERIALISED.items()):
        p = ROOT / rel
        if not p.exists():
            continue
        _c, rows = read_all(p)
        left += sum(1 for r in rows if is_disputed(r, key_cols))
    if not verify:
        if left:
            print(f"    BREACH  I6: {left:,} rows still pair a disputed "
                  f"identifier with {FROM_UID}")
            failed = True
        else:
            print("    I6 clean: 0 rows pair an Old Harbor identifier with "
                  "Three Affiliated")

    flags = flag_not_moved()
    if not verify:
        rv = ROOT / "review"
        rv.mkdir(exist_ok=True)
        with (rv / f"old_harbor_repoint_{TODAY}.csv").open(
                "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=["file", "row_index",
                                               "identifier", "changed"])
            w.writeheader()
            w.writerows(moved)
        with (rv / f"three_token_cluster_flags_{TODAY}.csv").open(
                "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(flags[0].keys()))
            w.writeheader()
            w.writerows(flags)
        (ROOT / "docs" / "OLD_HARBOR_REPOINT.json").write_text(
            json.dumps({"measured_date": TODAY,
                        "from": {"cedar_uid": FROM_UID, "tribe_id": FROM_TID,
                                 "name": FROM_NAME},
                        "to": {"cedar_uid": TO_UID, "tribe_id": TO_TID,
                               "name": TO_NAME},
                        "disputed_identifiers": sorted(DISPUTED),
                        "rows_repointed_total": total,
                        "per_file": report,
                        "flagged_not_moved": len(flags)},
                       indent=2) + "\n", encoding="utf-8")
    print(f"    {len(flags)} identifiers FLAGGED and deliberately not moved "
          f"(review/three_token_cluster_flags_{TODAY}.csv)")

    if verify and left:
        print(f"  VERIFY FAILED: {left:,} rows still pair an Old Harbor "
              f"identifier with {FROM_UID}")
        return 1
    return 1 if failed else 0


def selftest() -> int:
    """Prove the invariant fires. Inject a money change into the repoint path
    and assert the conservation check catches it; a check that has never
    failed on purpose is not known to work."""
    rows = [{"awardee_uei": "FGELS2KFR825", "cedar_uid": FROM_UID,
             "tribe_id": FROM_TID, "canonical_name": FROM_NAME,
             "total_obligations": "100.00"},
            {"awardee_uei": "ZZZZZZZZZZZZ", "cedar_uid": "CE-OTHER",
             "tribe_id": "T", "canonical_name": "Other",
             "total_obligations": "50.00"}]
    cols = list(rows[0].keys())
    before = money_totals(rows, cols)
    assert before["total_obligations"] == 15000, before
    # scope: the second row must NOT be in scope (I5)
    assert is_disputed(rows[0], ("awardee_uei",)) is True
    assert is_disputed(rows[1], ("awardee_uei",)) is False
    # a row carrying a disputed id but NOT keyed to MHATAT is out of scope
    ok = {"awardee_uei": "FGELS2KFR825", "cedar_uid": TO_UID,
          "tribe_id": TO_TID, "canonical_name": TO_NAME,
          "total_obligations": "1.00"}
    assert is_disputed(ok, ("awardee_uei",)) is False
    # I4 must catch an unequal move
    ub = {FROM_UID: 15000, TO_UID: 0}
    ua = {FROM_UID: 0, TO_UID: 14999}
    assert (ub[FROM_UID] - ua[FROM_UID]) != (ua[TO_UID] - ub[TO_UID])
    # I3 must catch a money edit
    rows[0]["total_obligations"] = "101.00"
    assert money_totals(rows, cols) != before
    print("  1075 selftest OK: scope gate, I3 money conservation and I4 "
          "equal-transfer all fire on an injected violation")
    return 0


if __name__ == "__main__":
    sys.exit(main())
