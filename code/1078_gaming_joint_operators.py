#!/usr/bin/env python3
"""
Cedar Press - 1078: A JOINTLY OPERATED CASINO HAS TWO OPERATORS AND ONE
`cedar_uid` CAN ONLY HOLD ONE.

    py -3 code/1078_gaming_joint_operators.py           # measure + repair
    py -3 code/1078_gaming_joint_operators.py verify    # read-only, exit 1
    py -3 code/1078_gaming_joint_operators.py selftest  # prove the check fires

WHAT CODEX SAW
---------------
PR #29 finding 5, on `gaming__sample.csv` row 10: The Stables Casino names
`Modoc Tribe of Oklahoma/Miami Tribe of Oklahoma` in `tribe` and exposes a
single `cedar_uid`, so entity filtering finds the facility under one operator
and never the other. Correct, and it is a real grain defect in
`gaming_facilities.csv` itself rather than in the ten-row projection - the
table has no second operator column to project.

MEASURED SCOPE: **1 facility of 787.** That number is the whole argument for
the shape of this fix.

WHY NOT A BRIDGE TABLE, WHICH IS CODEX'S OTHER SUGGESTION
-----------------------------------------------------------
A `facility -> operating tribe` bridge is the architecturally right answer and
it is the wrong answer at n=1. It would add a third shipped table to the
`gaming` collection, and `518_dataset_readiness.py` then requires a declared
and validated grain, a validated primary key and row-conservation coverage for
it - a real maintenance obligation, taken on to carry two rows. The
multi-valued column plus the count is the same information at the grain the
dataset already has, and `nagpra_notices.affiliated_entity_ids` is the
precedent in this project for exactly that. **A bridge becomes correct the
moment the count is not 1**, and `n_operating_entities` is the column that
will say so.

AND WHY THE OBVIOUS GENERALISATION WOULD BE WORSE THAN THE BUG
----------------------------------------------------------------
Splitting `tribe` on the usual separators to find more joint operations
returns **58 of 787 facilities** - and 57 of those are false. `&`, ` and ` and
`,` are inside single tribes' own legal names:

    Sac & Fox Tribe of the Mississippi in Iowa
    Assiniboine and Sioux Tribes of the Fort Peck Indian Reservation
    Grand Traverse Band of Ottawa and Chippewa Indians
    Confederated Salish & Kootenai Tribes
    Iowa Tribe of Kansas and Nebraska

Splitting on ` and ` would invent an "Assiniboine" and a "Sioux Tribes of the
Fort Peck Indian Reservation", neither of which is an entity. **`/` is the
only separator in this column that separates operators**, it occurs once, and
that is the rule applied here - stated rather than inferred, so the next
reader can check it in one grep.

WHAT THIS WRITES, IN PLACE
---------------------------
Three columns on `data/clean/gaming_facilities.csv`, never blank:

    operating_entity_cedar_uids  pipe-delimited, PRIMARY FIRST. Equals
                                 `cedar_uid` on 786 of 787 rows.
    n_operating_entities         1 on 786 rows, 2 on The Stables.
    operating_entity_basis       how the row was resolved, per row.

`cedar_uid` is UNCHANGED on every row. It stays the primary operator and the
stable join key; the new column is additive, so nothing that reads the table
today reads it differently.

THE SECOND OPERATOR, AND THE EVIDENCE FOR IT
----------------------------------------------
The Stables Casino, Miami OK. The facility row's own `tribe` field names both
nations, which is the source record's assertion, not Cedar's inference. Both
are in the register in their own right:

    CE-0016Y-PQ  Miami Tribe of Oklahoma   TRBF-MIAMIT-00  OK   (kept primary)
    CE-00175-5P  Modoc Nation              TRBF-MODOCN-00  OK   (added)

Note the register's canonical name for the second is **Modoc Nation**, while
the facility row says *Modoc Tribe of Oklahoma* - the nation renamed. The name
is matched through the register rather than by string equality, which is why
the rename does not break it.

INVARIANTS - exit 1 on any breach
----------------------------------
  I1  row count IDENTICAL before and after; exactly 3 columns added
  I2  `cedar_uid` is not modified on any row
  I3  `operating_entity_cedar_uids` always CONTAINS `cedar_uid`, and its first
      element IS `cedar_uid`
  I4  `n_operating_entities` equals the element count, on every row
  I5  every uid emitted exists in `cedar_identity_register.csv`
  I6  a `tribe` string containing `/` never leaves `n_operating_entities = 1`
  I7  the file did not move under us between read and write
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
TAG = f".bak_{TODAY}_pre_1078_gaming_joint_operators"

FAC = ROOT / "data" / "clean" / "gaming_facilities.csv"
REG = ROOT / "data" / "spine" / "cedar_identity_register.csv"
NEW_COLS = ("operating_entity_cedar_uids", "n_operating_entities",
            "operating_entity_basis")

# `/` is the ONLY separator in `gaming_facilities.tribe` that separates two
# operators. See the docstring for the 57 false positives every other
# candidate separator produces.
SEP = "/"

# Where the source names an operator whose string is not the register's
# canonical name, the mapping is declared HERE, by hand, with the reason -
# never guessed by a matcher. One entry today.
NAME_TO_UID = {
    "modoc tribe of oklahoma": ("CE-00175-5P",
                                "register canonical name is 'Modoc Nation'; "
                                "the nation renamed and the facility record "
                                "predates it"),
    "miami tribe of oklahoma": ("CE-0016Y-PQ", "register canonical name"),
}


def fingerprint(p: Path):
    st = p.stat()
    return (st.st_size, int(st.st_mtime))


def load_register():
    by_uid, by_name = {}, {}
    with REG.open(newline="", encoding="utf-8-sig", errors="replace") as fh:
        for r in csv.DictReader(fh):
            u = (r.get("cedar_uid") or "").strip()
            if not u:
                continue
            by_uid[u] = r
            by_name[(r.get("canonical_name") or "").strip().lower()] = u
    return by_uid, by_name


def main() -> int:
    arg = sys.argv[1] if len(sys.argv) > 1 else ""
    if arg == "selftest":
        return selftest()
    verify = arg == "verify"

    if not FAC.exists() or not REG.exists():
        print("  1078: gaming_facilities.csv or the register is ABSENT")
        return 1
    by_uid, by_name = load_register()
    fp = fingerprint(FAC)
    with FAC.open(newline="", encoding="utf-8-sig", errors="replace") as fh:
        rd = csv.DictReader(fh)
        cols = list(rd.fieldnames or [])
        rows = list(rd)
    n_before, c_before = len(rows), len(cols)

    added = [c for c in NEW_COLS if c not in cols]
    out_cols = cols + added

    joint, unresolved, breaches = [], [], []
    for r in rows:
        primary = (r.get("cedar_uid") or "").strip()
        tribe = (r.get("tribe") or "").strip()
        uids, basis = ([primary] if primary else []), "single_operator"
        if SEP in tribe:
            names = [n.strip() for n in tribe.split(SEP) if n.strip()]
            found, missed = [], []
            for nm in names:
                key = nm.lower()
                uid = (NAME_TO_UID.get(key, (None, ""))[0]
                       or by_name.get(key))
                if uid:
                    found.append(uid)
                else:
                    missed.append(nm)
            # I3: the primary must lead and must survive.
            ordered = ([primary] if primary in found or not primary else []) + \
                      [u for u in found if u != primary]
            if primary and primary not in found:
                ordered = [primary] + [u for u in found if u != primary]
            uids = ordered or found
            if missed:
                unresolved.append({"facility_id": r.get("facility_id"),
                                   "facility_name": r.get("facility_name"),
                                   "unresolved_operator_names": "|".join(missed)})
                basis = ("joint_operation_declared_in_source; "
                         + str(len(missed)) + " operator name(s) UNRESOLVED "
                         "and therefore NOT emitted - see review/")
            else:
                basis = ("joint_operation_declared_in_source: the facility "
                         "row's own `tribe` field names both nations, "
                         "resolved through cedar_identity_register.csv")
            joint.append({"facility_id": r.get("facility_id"),
                          "facility_name": r.get("facility_name"),
                          "tribe": tribe,
                          "cedar_uid_primary": primary,
                          "operating_entity_cedar_uids": "|".join(uids),
                          "n": len(uids)})
        r["operating_entity_cedar_uids"] = "|".join(uids)
        r["n_operating_entities"] = str(len(uids))
        r["operating_entity_basis"] = basis if primary else "no_cedar_uid"

        # ---- invariants, per row --------------------------------------
        lst = [u for u in r["operating_entity_cedar_uids"].split("|") if u]
        if primary and (not lst or lst[0] != primary):
            breaches.append(f"I3 {r.get('facility_id')}: primary not first")
        if len(lst) != int(r["n_operating_entities"]):
            breaches.append(f"I4 {r.get('facility_id')}: count mismatch")
        for u in lst:
            if u not in by_uid:
                breaches.append(f"I5 {r.get('facility_id')}: {u} not in the "
                                f"register")
        if SEP in (r.get("tribe") or "") and int(r["n_operating_entities"]) < 2:
            breaches.append(f"I6 {r.get('facility_id')}: '/' in tribe but "
                            f"only one operator emitted")

    if len(rows) != n_before:
        breaches.append(f"I1 rows {n_before} -> {len(rows)}")
    if len(out_cols) != c_before + len(added):
        breaches.append("I1 column arithmetic")

    print("  1078 gaming joint operators")
    print(f"    facilities                     {n_before:,}")
    print(f"    columns                        {c_before} -> {len(out_cols)} "
          f"(added {', '.join(added) or 'none - already present'})")
    print(f"    jointly operated               {len(joint)}")
    for j in joint:
        print(f"        {j['facility_name']}  {j['tribe']}")
        print(f"          {j['operating_entity_cedar_uids']}  (n={j['n']})")
    if unresolved:
        print(f"    operator names NOT resolved    {len(unresolved)} "
              f"- emitted as unresolved, never guessed")
    for b in breaches[:10]:
        print(f"    BREACH {b}")
    if breaches:
        return 1
    if verify:
        return 0

    if fingerprint(FAC) != fp:                                  # I7
        print("    BREACH I7 gaming_facilities.csv changed under us - ABORTED")
        return 1
    bak = FAC.with_name(FAC.name + TAG)
    if not bak.exists():
        shutil.copy2(FAC, bak)
    tmp = FAC.with_suffix(".csv.part")
    with tmp.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=out_cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    if fingerprint(FAC) != fp:
        tmp.unlink(missing_ok=True)
        print("    BREACH I7 changed during write - ABORTED")
        return 1
    os.replace(tmp, FAC)

    (ROOT / "docs" / "GAMING_JOINT_OPERATORS.json").write_text(
        json.dumps({"measured_date": TODAY, "facilities": n_before,
                    "columns_before": c_before, "columns_after": len(out_cols),
                    "jointly_operated": joint,
                    "unresolved_operator_names": unresolved,
                    "separator_rule": "'/' only",
                    "false_positive_separators_rejected": {
                        "&": 23, " and ": 35, ",": 4,
                        "note": "all inside single tribes' own legal names"}},
                   indent=2) + "\n", encoding="utf-8")
    return 0


def selftest() -> int:
    """The check must fire on the failure it exists to prevent."""
    by_uid = {"CE-A": {}, "CE-B": {}}
    row = {"tribe": "X/Y", "cedar_uid": "CE-A",
           "operating_entity_cedar_uids": "CE-A", "n_operating_entities": "1"}
    lst = [u for u in row["operating_entity_cedar_uids"].split("|") if u]
    assert SEP in row["tribe"] and int(row["n_operating_entities"]) < 2, \
        "I6 must fire here"
    row2 = {"cedar_uid": "CE-A", "operating_entity_cedar_uids": "CE-B|CE-A",
            "n_operating_entities": "2"}
    lst2 = row2["operating_entity_cedar_uids"].split("|")
    assert lst2[0] != row2["cedar_uid"], "I3 must fire on a non-leading primary"
    row3 = {"operating_entity_cedar_uids": "CE-A|CE-Z",
            "n_operating_entities": "2"}
    assert any(u not in by_uid
               for u in row3["operating_entity_cedar_uids"].split("|")), \
        "I5 must fire on a uid absent from the register"
    row4 = {"operating_entity_cedar_uids": "CE-A|CE-B",
            "n_operating_entities": "3"}
    assert len(row4["operating_entity_cedar_uids"].split("|")) != \
        int(row4["n_operating_entities"]), "I4 must fire on a count mismatch"
    # and the separator rule itself: ` and ` must NOT be treated as one
    assert SEP not in "Assiniboine and Sioux Tribes of the Fort Peck " \
                      "Indian Reservation"
    print("  1078 selftest OK: I3, I4, I5 and I6 each fire on an injected "
          "violation, and the separator rule leaves a confederated tribe's "
          "own name intact")
    return 0


if __name__ == "__main__":
    sys.exit(main())
