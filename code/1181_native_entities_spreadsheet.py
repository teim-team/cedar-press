#!/usr/bin/env python3
"""
Cedar Press - 1181: the native entities spreadsheet, and the definitions that
make it readable on its own.

    py -3 code/1181_native_entities_spreadsheet.py            # report
    py -3 code/1181_native_entities_spreadsheet.py build
    py -3 code/1181_native_entities_spreadsheet.py verify
    py -3 code/1181_native_entities_spreadsheet.py selftest

WHY THIS EXISTS
---------------
Owner, 2026-09-04:

    "in the artifact list you describe the cedar system and list all our
     entities i want definitions for those entities as well and them markdowns
     or other documents carry them so the spreadsheet of native entities makes
     sense and we have our cedar uid and entity type as well"

    "change the datasets so cedar uid is first, then name then entity type
     then any other ids we make like event, then the key ids from those
     datasets"

Two problems, one file each.

THE DEFINITIONS ALREADY EXISTED. `docs/CEDAR_TAXONOMY.json` holds a definition,
a `what_it_is_not`, and a `how_membership_is_evidenced` for all 17 entity
classes, and it is good work. It simply never shipped: it is a build artefact
under docs/, so a buyer opening the spreadsheet saw seventeen bare class
strings and no way to learn what any of them meant. This was a DISTRIBUTION
gap, not an authoring one, which is why the fix is a copy rather than a
rewrite - `docs/ENTITY_TYPES.md` travels with the CSV.

COLUMN ORDER IS A READING ORDER. Identity first, then what the row IS, then
the keys that let a reader join it to something else, then everything else.
The old register led with `cedar_uid, cedar_entity_id, canonical_name, ...` -
two identifiers before the human ever learns what the row is about.

`name` IS THE OFFICIAL NAME (see 1180). Not the short handle. The owner's
diagnosis was exact:

    "i honestly think using short names is what made it harder to match too"

Measured, on the BIA list: matching on `canonical_name` resolved 29 of 577
rows (5.0%). Matching on the official name resolved 576 of 577 (99.8%). A
short handle is lossy by construction - `Benton` carries nothing that connects
it to the Utu Utu Gwaitu Paiute Tribe of the Benton Paiute Reservation - so no
matcher could reach those rows, and that is exactly why 21 corrupted handles
sat undetected. The handle is kept as `short_handle` for display, clearly
marked, and it is never the join key.
"""
from __future__ import annotations

import csv
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REGISTER = ROOT / "data" / "spine" / "cedar_identity_register.csv"
NAMES = ROOT / "data" / "spine" / "cedar_entity_names.csv"
TYPES = ROOT / "data" / "spine" / "cedar_entity_types.csv"
CROSSWALK = ROOT / "data" / "spine" / "cedar_retired_neid_crosswalk.csv"
DEFS_SRC = ROOT / "docs" / "ENTITY_TYPES.md"

OUT_DIR = ROOT / "dist" / "customer"
OUT_CSV = OUT_DIR / "native_entities.csv"
OUT_DEFS = OUT_DIR / "native_entities__DEFINITIONS.md"

csv.field_size_limit(10 ** 9)

#: THE READING ORDER. Identity, then what it is, then the keys, then the rest.
#:
#: NEITHER `retired_neid` NOR `short_handle` SHIPS, and both were in my first
#: draft. Owner, 2026-09-04, on seeing the retired id in the output:
#:
#:     "no remove that ... we should have everything linked and crosswalked
#:      already"
#:
#: He is right and the first draft contradicted the purge it was built beside.
#: I had justified `retired_neid` as a convenience for a buyer holding an old
#: extract, which is the same reasoning that kept the CICD scheme alive
#: through six previous removals: every one of them left the identifier
#: somewhere for someone's convenience. The crosswalk is INTERNAL - it lives
#: at data/spine/cedar_retired_neid_crosswalk.csv so `translate_neid_values`
#: can resolve an old value to a `cedar_uid` - and the resolved uid is the
#: only thing a customer ever sees. Linking is Cedar's job, not the buyer's.
#:
#: `short_handle` went for the owner's other reason: it IS `canonical_name`,
#: he said plainly that it is not needed, and it is the lossy string that made
#: matching fail at 5.0% where the official name reaches 99.8%.
COLUMN_ORDER = (
    "cedar_uid",            # 1. identity, always first
    "name",                 # 2. the official name, from its source
    "entity_type",          # 3. what this row IS
    "cedar_entity_id",      # 4. other Cedar-minted ids
    "state",
    "register_status",
    "former_names",         # real prior NAMES, not a retired id scheme
    "name_source",
    "name_source_url",
    "name_captured",
    "name_match_route",
)


def _read(path: Path) -> list:
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
        return list(csv.DictReader(fh))


def rows() -> list:
    reg = _read(REGISTER)
    names = {r["cedar_uid"]: r for r in _read(NAMES)}
    out = []
    for r in reg:
        uid = (r.get("cedar_uid") or "").strip()
        n = names.get(uid, {})
        out.append({
            "cedar_uid": uid,
            "name": n.get("name") or (r.get("canonical_name") or "").strip(),
            "entity_type": (r.get("entity_class") or "").strip(),
            "cedar_entity_id": (r.get("cedar_entity_id") or "").strip(),
            "state": (r.get("state") or "").strip(),
            "register_status": (r.get("register_status") or "").strip(),
            "former_names": (r.get("former_names") or "").strip(),
            "name_source": n.get("name_source", "cedar_internal"),
            "name_source_url": n.get("name_source_url", ""),
            "name_captured": n.get("name_captured", ""),
            "name_match_route": n.get("name_match_route", ""),
        })
    return out


def build(apply: bool = False) -> int:
    data = rows()
    if not data:
        print("  no register rows found")
        return 1
    sourced = sum(1 for r in data if r["name_source"] != "cedar_internal")
    types = {}
    for r in data:
        types[r["entity_type"]] = types.get(r["entity_type"], 0) + 1

    print("  1181 native entities   %s"
          % ("BUILD" if apply else "REPORT (writes nothing)"))
    print("    rows            : %d" % len(data))
    print("    entity types    : %d" % len(types))
    print("    sourced names   : %d (%.1f%%)"
          % (sourced, 100.0 * sourced / len(data)))
    print("    unsourced (kept): %d"
          % sum(1 for r in data if r["name_source"] == "cedar_internal"))
    print("    column order    : %s ..." % ", ".join(COLUMN_ORDER[:5]))

    if apply:
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        with OUT_CSV.open("w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(COLUMN_ORDER))
            w.writeheader()
            for r in data:
                w.writerow({k: r.get(k, "") for k in COLUMN_ORDER})
        if DEFS_SRC.exists():
            shutil.copyfile(DEFS_SRC, OUT_DEFS)
        print()
        print("    wrote %s" % OUT_CSV.relative_to(ROOT))
        print("    wrote %s" % OUT_DEFS.relative_to(ROOT))
    return 0


def verify() -> int:
    data = _read(OUT_CSV)
    if not data:
        print("  NOT BUILT: %s" % OUT_CSV)
        return 1
    ok = True
    got = list(data[0].keys())
    if got[:3] != ["cedar_uid", "name", "entity_type"]:
        print("  FAIL first three columns are %s" % got[:3]); ok = False
    blank_uid = sum(1 for r in data if not r["cedar_uid"].strip())
    blank_name = sum(1 for r in data if not r["name"].strip())
    blank_type = sum(1 for r in data if not r["entity_type"].strip())
    print("  rows            : %d" % len(data))
    print("  blank cedar_uid : %d" % blank_uid)
    print("  blank name      : %d" % blank_name)
    print("  blank type      : %d" % blank_type)
    print("  definitions ship: %s" % OUT_DEFS.exists())
    if blank_uid or blank_name or blank_type or not OUT_DEFS.exists():
        ok = False
    print("  OK" if ok else "  FAIL")
    return 0 if ok else 1


def selftest() -> int:
    """Every entity_type in the data must have a published definition, and the
    spreadsheet must lead with identity."""
    ok = True
    if list(COLUMN_ORDER[:3]) != ["cedar_uid", "name", "entity_type"]:
        print("  FAIL COLUMN_ORDER does not lead with uid/name/type"); ok = False

    # THE BANNED COLUMNS. Owner, 2026-09-04: "there should be no short handle
    # we cant use it reliable", and on the retired id, "no remove that ... we
    # should have everything linked and crosswalked already". Both were in my
    # first draft. This asserts they cannot return by anyone's convenience
    # argument - which is how the CICD scheme survived six prior removals.
    banned = {"retired_neid", "short_handle", "canonical_name", "handle",
              "handle_prefix", "tribe_id", "name_differs_from_short_handle"}
    leaked = sorted(banned & set(COLUMN_ORDER))
    if leaked:
        print("  FAIL banned column(s) in COLUMN_ORDER: %s" % ", ".join(leaked))
        ok = False
    else:
        print("  no short handle and no retired id in the shipped columns")

    data = rows()
    # and prove it against the DATA, not just the declared order
    if data:
        stray = sorted(banned & set(data[0].keys()))
        if stray:
            print("  FAIL builder still emits: %s" % ", ".join(stray))
            ok = False
    # `type_code` is the value that appears in the data; `label` is the human
    # rendering of it. Keying on `label` here failed 16 of 17 and was my bug.
    defined = {r["type_code"].strip() for r in _read(TYPES)}
    present = {r["entity_type"] for r in data if r["entity_type"]}
    missing = sorted(present - defined)
    if missing:
        print("  FAIL %d entity_type(s) ship with no definition:" % len(missing))
        for m in missing[:6]:
            print("       %s" % m)
        ok = False
    else:
        print("  all %d entity types carry a definition" % len(present))
    print("  selftest %s" % ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "report"
    if cmd == "build":
        raise SystemExit(build(apply=True))
    if cmd == "verify":
        raise SystemExit(verify())
    if cmd == "selftest":
        raise SystemExit(selftest())
    raise SystemExit(build(apply=False))
