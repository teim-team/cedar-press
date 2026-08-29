#!/usr/bin/env python3
"""
328 - MAKE A BYPASS OF THE ID SERVICE DETECTABLE, AND KEEP THE KEY CONTRACT
      HONEST.

    py -3 code/328_audit_id_service_bypass.py           # audit, exit 1 on new
    py -3 code/328_audit_id_service_bypass.py --json    # machine-readable

TWO CHECKS, BOTH OF THEM ABOUT THE SAME THING: an id must be reproducible by
somebody who is not this process.

CHECK A - THE ID SERVICE IS BYPASSED WITHOUT SAYING SO
------------------------------------------------------
`cedar_ids.allocate` takes an exclusive file lock and re-reads the counter
from disk, so two agents cannot mint the same id. An f-string does neither.
`284_audit_nondeterministic_keys.py` already reports `BYPASSED_ID_SERVICE`,
but its rule is "the file does not mention `cedar_ids`" - which means the
finding disappears the moment somebody imports the module for any reason at
all. That is a detector that can be silenced by an unrelated import, and this
project has already learned what a detector that stops detecting costs.

So this check is stricter and it is about DECLARATION, not mention. A script
that writes a literal `PREFIX-{...}` for a prefix the ID service MINTS must
either

  (a) call `cedar_ids.allocate(PREFIX, ...)`, or
  (b) call `cedar_ids.declare_static_block(PREFIX, lo, hi, owner, why)` -
      the legitimate case, where a build needs a CONTIGUOUS PRE-ASSIGNED
      range rather than one id at a time, and says so out loud, and

      `declare_static_block` refuses an overlap with a different owner's
      block and makes `allocate` step over it.

Anything else is an UNDECLARED BYPASS and is reported by file and line.

Found and fixed on 2026-08-26 by exactly this rule: `84_build_nigc_regions.py`
and `85_build_admin_region_crosswalk.py` between them minted SIX contiguous
`CEDAR-ADMREG` blocks by f-string, and `cedar_ids.RESERVED_BLOCKS` knew about
exactly ONE of the six. `allocate("CEDAR-ADMREG")` could have walked straight
into `BIA_REGION`. Both now declare their blocks.

CHECK B - THE PRODUCER AND THE MIGRATION MUST AGREE ON THE KEY
--------------------------------------------------------------
`327_migrate_class7_keys_to_digests.py` rewrote live tables using
`cedar_keys.surrogate_id(prefix, row, columns)`. Each producing script was
edited to mint the SAME id with the SAME prefix and column list. If those two
lists ever drift, the next rebuild silently re-keys the table and every id in
it changes - reintroducing, by a slower road, the exact defect the migration
removed.

So this check reads 327's specs and, for each one, reads the producing
script's own declared key-column constant and compares them. It is the same
principle as `293` importing 284's lint rather than re-deriving it: ONE
declaration, checked, never two copies trusted to stay equal.

NO NETWORK. Reads `code/*.py` with `ast` and never imports or executes a
linted script. Writes nothing outside `docs/`.

Claimed 2026-08-26 with script numbers 326-333.
"""

import ast
import json
import re
import sys
from pathlib import Path

CEDAR = Path(r"C:\Users\esm247\Desktop\Cedar Press")
CODE = CEDAR / "code"
OUT = CEDAR / "docs" / "schema" / "id_service_bypass.json"

sys.path.insert(0, str(CODE))
import cedar_ids as CI                              # noqa: E402

#: Prefixes the service MINTS. A grandfathered prefix (width 0) is never
#: minted, so an f-string carrying one is a REFERENCE to an existing id, not a
#: bypass - the same exemption 284 makes, and for the same reason.
MINTED = sorted((p for p, (_k, w) in CI.PREFIXES.items() if w > 0),
                key=len, reverse=True)

#: This file quotes the pattern in prose; 284 and 293 describe it. A detector
#: that flags its own documentation is a detector nobody runs.
SELF = {"328_audit_id_service_bypass.py",
        "284_audit_nondeterministic_keys.py",
        "293_lint_bug_classes.py",
        "cedar_ids.py"}

ALLOCATE_CALLS = {"allocate", "declare_static_block", "format_id",
                  "adopt_existing"}


def scan_file(p):
    """[(line, prefix, snippet)] - undeclared mints under a minted prefix."""
    try:
        src = p.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    lines = src.splitlines()
    try:
        tree = ast.parse(src)
    except SyntaxError:
        # A file the auditor cannot read has been checked for NOTHING, which
        # is not the same as clean. Reported, never silently skipped.
        return [(0, "UNPARSEABLE", "SyntaxError - NOT CHECKED")]

    # Which prefixes does this file route through the service?
    declared = set()
    for n in ast.walk(tree):
        if not isinstance(n, ast.Call):
            continue
        fn = getattr(n.func, "attr", None) or getattr(n.func, "id", None)
        if fn not in ALLOCATE_CALLS:
            continue
        for a in list(n.args) + [k.value for k in n.keywords]:
            if isinstance(a, ast.Constant) and isinstance(a.value, str):
                declared.add(a.value)

    out = []
    for pref in MINTED:
        if pref in declared:
            continue
        for m in re.finditer(r"f[\"'][^\"'\n]*" + re.escape(pref) + r"-?\{",
                             src):
            ln = src[:m.start()].count("\n") + 1
            out.append((ln, pref, lines[ln - 1].strip()[:150]))
    return out


def check_key_contract():
    """327's spec vs the producing script's own declared key columns."""
    spec_path = CODE / "327_migrate_class7_keys_to_digests.py"
    if not spec_path.exists():
        return [{"status": "UNMEASURED",
                 "detail": "327_migrate_class7_keys_to_digests.py is ABSENT - "
                           "the key contract is UNCHECKED, which is not the "
                           "same as agreed"}]
    tree = ast.parse(spec_path.read_text(encoding="utf-8"))
    specs = None
    for n in ast.walk(tree):
        if isinstance(n, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id == "SPECS" for t in n.targets):
            specs = ast.literal_eval(n.value)
    if specs is None:
        return [{"status": "UNMEASURED",
                 "detail": "SPECS not found in 327 - key contract UNCHECKED"}]

    out = []
    for s in specs:
        script = s["producer"].split(":")[0]
        p = CODE / script
        if not p.exists():
            out.append({"status": "MISSING_PRODUCER", "spec": s["name"],
                        "producer": script})
            continue
        src = p.read_text(encoding="utf-8", errors="replace")
        ptree = ast.parse(src)
        # every module-level list-of-strings constant whose name ends
        # _KEY_COLUMNS
        consts = {}
        for n in ptree.body:
            if isinstance(n, ast.Assign) and len(n.targets) == 1 and \
                    isinstance(n.targets[0], ast.Name) and \
                    n.targets[0].id.endswith("KEY_COLUMNS"):
                try:
                    consts[n.targets[0].id] = ast.literal_eval(n.value)
                except ValueError:
                    pass
        want = list(s["key_columns"])
        if not consts:
            out.append({"status": "NO_DECLARATION", "spec": s["name"],
                        "producer": script, "expected_columns": want,
                        "detail": "the producing script declares no "
                                  "*_KEY_COLUMNS constant, so a reader cannot "
                                  "see what the id is made of without reading "
                                  "327"})
            continue
        if any(v == want for v in consts.values()):
            out.append({"status": "AGREES", "spec": s["name"],
                        "producer": script, "columns": want})
        else:
            out.append({"status": "DRIFTED", "spec": s["name"],
                        "producer": script, "expected_columns": want,
                        "found_constants": consts,
                        "detail": "327 migrated the live table on one column "
                                  "list and the producer would rebuild it on "
                                  "another. A rebuild re-keys every row."})
        # the digest must be minted through cedar_keys, not by hand
        if "surrogate_id" not in src:
            out.append({"status": "NOT_ROUTED_THROUGH_CEDAR_KEYS",
                        "spec": s["name"], "producer": script,
                        "detail": "no call to cedar_keys.surrogate_id - the "
                                  "digest is being built somewhere else"})
    return out


def main():
    findings = []
    unparsed = []
    for p in sorted(CODE.glob("*.py")):
        if p.name in SELF:
            continue
        for ln, pref, snip in scan_file(p):
            if pref == "UNPARSEABLE":
                unparsed.append(p.name)
                continue
            findings.append({"script": p.name, "line": ln, "prefix": pref,
                             "snippet": snip})

    contract = check_key_contract()

    print("=" * 78)
    print("328  ID SERVICE BYPASS + KEY CONTRACT AUDIT")
    print("=" * 78)
    print(f"\nA. UNDECLARED MINTS under a prefix cedar_ids MINTS "
          f"({len(MINTED)} such prefixes)\n")
    if findings:
        for f in findings:
            print(f"   {f['script']}:{f['line']}  {f['prefix']}")
            print(f"      {f['snippet']}")
        print("\n   Each of these writes an id under a prefix the ID service "
              "owns without\n   calling `allocate` or declaring a static "
              "block. `allocate` takes an\n   exclusive file lock and re-reads "
              "the counter from disk; an f-string does\n   neither, and two "
              "agents minting at once get the same number.")
    else:
        print("   none - every mint under a minted prefix is either "
              "allocated or declared.")

    print("\n   DECLARED STATIC BLOCKS currently registered with the service:")
    if CI.STATIC_BLOCKS:
        for pref, blocks in sorted(CI.STATIC_BLOCKS.items()):
            for lo, hi, owner, why in blocks:
                print(f"     {pref}-{lo:06d}..{hi:06d}  {owner}")
                print(f"        {why[:96]}")
    else:
        print("     (none registered in THIS process - a block is declared by "
              "the owning\n      build at import time, so this list is only "
              "populated when that build\n      is imported. The source of "
              "truth is the `declare_static_block` call.)")
    print(f"     plus RESERVED_BLOCKS: {CI.RESERVED_BLOCKS}")

    print("\nB. KEY CONTRACT - 327's migration spec vs the producer's own "
          "declaration\n")
    bad = [c for c in contract if c["status"] not in ("AGREES",)]
    for c in sorted(contract, key=lambda x: (x["status"] != "AGREES",
                                             x.get("spec", ""))):
        mark = "  " if c["status"] == "AGREES" else "!!"
        print(f"   {mark} {c['status']:28s} {c.get('spec', ''):24s} "
              f"{c.get('producer', '')}")
        if c["status"] != "AGREES" and c.get("detail"):
            print(f"        {c['detail']}")

    if unparsed:
        print(f"\n   NOT PARSED - these were NOT checked, and that is not the "
              f"same as clean: {', '.join(unparsed)}")

    doc = {"produced_by": "328_audit_id_service_bypass.py",
           "minted_prefixes": MINTED,
           "undeclared_mints": findings,
           "key_contract": contract,
           "unparsed": unparsed}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    tmp = OUT.with_suffix(".json.part")
    tmp.write_text(json.dumps(doc, indent=1, sort_keys=True, default=str),
                   encoding="utf-8")
    tmp.replace(OUT)
    json.loads(OUT.read_text(encoding="utf-8"))          # verify by re-reading
    print(f"\nwrote {OUT.relative_to(CEDAR)} "
          f"({OUT.stat().st_size:,} bytes, re-read OK)")
    print(f"undeclared mints {len(findings)} · key-contract problems "
          f"{len(bad)} · unparsed {len(unparsed)}")
    return 1 if (findings or bad or unparsed) else 0


if __name__ == "__main__":
    sys.exit(main())
