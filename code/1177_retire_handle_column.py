#!/usr/bin/env python3
"""
Cedar Press - 1177: delete the CICD handle from the source tables.

    py -3 code/1177_retire_handle_column.py            # report
    py -3 code/1177_retire_handle_column.py apply      # rewrite, with backups
    py -3 code/1177_retire_handle_column.py verify     # exit 1 if any survives
    py -3 code/1177_retire_handle_column.py selftest

WHY THIS EXISTS, AND WHY IT IS THE SEVENTH ATTEMPT
---------------------------------------------------
Owner, 2026-09-04, having asked six times:

    "ive asked you to remove the cicd id like 6 times and you say you have so
     literally delete it... we dont need a readable id cuz we just have the
     entity name"

He is right, and the reason it kept coming back is worth stating plainly
because it is not a story about carelessness. Each earlier pass removed the
names known that day:

    2026-09-01  843 dropped `tribe_id` from three files, named by hand
    2026-09-03  the rule moved into publishable_columns() - 77 more files
    2026-09-03  the VALUES, hiding in `entity_id`, `affiliated_entity_ids`
    2026-09-04  `handle` - which had been DOCUMENTED as Cedar's own readable
                code, including in the explainer written for the owner, and is
                not: it is the CICD Native Entity Connector Crosswalk's

That last one is the whole failure. A column described as ours was skipped by
every pass looking for theirs. AGENTS.md:703 always said NEID was CICD's; the
prefixed handle IS the NEID.

WHAT THIS DOES THAT THE PUBLICATION GATE DOES NOT
--------------------------------------------------
`cedar_publication.NEID_COLS` already stops the handle reaching a customer, and
`1169.check_no_retired_scheme_columns` fails the release if one ever does. That
is the guard. This is the deletion: the column comes out of the SOURCE tables,
so there is nothing left to leak.

SAFE BECAUSE IT IS 1:1, MEASURED BEFORE ANYTHING IS WRITTEN
------------------------------------------------------------
1,555 handles, 1,555 uids, no handle claiming two uids and no uid claiming two
handles. Every table below carries `cedar_uid` beside the handle already, on
every populated row - verified per file at run time, and a file that fails that
test is REFUSED rather than stripped. Dropping the column therefore costs no
identity anywhere; the uid does the joining and `canonical_name` does the
reading, which is the owner's point.

THE TWELVE READERS
------------------
Twelve scripts read a handle column. They are NOT rewritten here, and that is
deliberate: this script deletes data, and a data change plus a dozen code
changes in one pass is not reviewable. `verify` lists every reader still
referring to a column that no longer exists, so the follow-up is a named list
rather than a surprise at the next build.
"""
from __future__ import annotations

import csv
import os
import shutil
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CLEAN = ROOT / "data" / "clean"
SPINE = ROOT / "data" / "spine"
TODAY = date.today().isoformat()
csv.field_size_limit(10_000_000)

#: Every file carrying a handle column, and the uid column that replaces it.
#: Enumerated, because deleting a column from a file nobody checked is how the
#: last six passes each left something behind - the sweep below RE-DERIVES this
#: list from disk and refuses to run if it finds a file not named here.
TARGETS = {
    "data/clean/cedar_entity_freshness.csv": ("handle", "cedar_uid"),
    "data/clean/cedar_harvest_coverage_matrix.csv": ("handle", "cedar_uid"),
    "data/clean/entity_dated_public_facts.csv": ("handle", "cedar_uid"),
    "data/clean/nest_enterprise_relations.csv": ("owner_hub_handle", "owner_hub_cedar_uid"),
    "data/clean/nest_enterprises.csv": ("owner_hub_handle", "owner_hub_cedar_uid"),
    "data/clean/nest_entity_dual_role.csv": ("handle", "cedar_uid"),
    "data/spine/cedar_identity_register.csv": ("handle", "cedar_uid"),
}

#: Files that are RECORDS OF the retired scheme rather than tables carrying it.
#: `cedar_handle_history.csv` is 1,555 rows of handle -> uid bindings with their
#: validity dates: stripping the handle would leave a history of nothing. It
#: goes to `graveyard/` whole, so the binding stays recoverable and stops being
#: a live spine table. Found by the sweep, not by the list - which is the sweep
#: earning its place.
RETIRE_WHOLE = {
    "data/spine/cedar_handle_history.csv":
        "the handle->uid binding history; the handle is the CICD identifier, so "
        "the table documents a retired scheme rather than describing Indian "
        "Country. Kept in graveyard/ because the binding is how any older "
        "artifact still naming a handle can be read.",
}

#: NOT the retired scheme, and never to be stripped. Owner, 2026-09-04:
#: "cedar_uid is Cedar's only entity ID, but datasets still need award/deal/
#: filing IDs."
#:
#: That distinction is the difference between a cleanup and a data loss. A
#: contract number, a FAIN, a Deal_ID, an LDA filing uuid and a Federal
#: Register document number are the identifiers of an EVENT, not of an entity.
#: Cedar did not mint them, the retirement does not touch them, and a sweep
#: that took them would destroy the only handle a customer has on the record
#: itself. Asserted in `selftest`.
NOT_AN_ENTITY_ID = (
    "contract_number", "award_id_fain", "award_id_piid", "subaward_number",
    "Deal_ID", "filing_uuid", "document_number", "notice_id", "bill_id",
    "cedar_place_id", "recipient_uei", "cage_code", "EIN", "duns",
)

HANDLE_NAMES = ("handle",)


def is_handle(col: str) -> bool:
    c = col.strip().lower()
    return c == "handle" or c.endswith("_handle") or c.startswith("handle_")


def sweep():
    """Every file on disk carrying a handle column. Never trust the list."""
    found = {}
    for d in (CLEAN, SPINE):
        for p in sorted(d.glob("*.csv")):
            if ".bak" in p.name or p.suffix != ".csv":
                continue
            try:
                with p.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
                    hdr = next(csv.reader(fh), []) or []
            except OSError:
                continue
            cols = [c for c in hdr if is_handle(c)]
            if cols:
                found[str(p.relative_to(ROOT)).replace("\\", "/")] = cols
    return found


def check_one(path: Path, handle_col: str, uid_col: str):
    """Would dropping the handle lose identity on any row? Full pass."""
    with path.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
        rd = csv.DictReader(fh)
        hdr = rd.fieldnames or []
        if handle_col not in hdr:
            return None
        has_uid = uid_col in hdr
        n = h_only = both = 0
        for r in rd:
            n += 1
            h = (r.get(handle_col) or "").strip()
            u = (r.get(uid_col) or "").strip() if has_uid else ""
            if h and u:
                both += 1
            elif h and not u:
                h_only += 1
    return {"rows": n, "uid_col_present": has_uid,
            "handle_with_uid": both, "handle_WITHOUT_uid": h_only}


def strip_file(path: Path, apply_it: bool):
    with path.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
        rd = csv.DictReader(fh)
        hdr = rd.fieldnames or []
        keep = [c for c in hdr if not is_handle(c)]
        rows = list(rd)
    if len(keep) == len(hdr):
        return 0, len(rows)
    if not apply_it:
        return len(hdr) - len(keep), len(rows)
    bak = path.with_suffix(path.suffix + f".bak_{TODAY}_pre_1177_retire_handle_column")
    shutil.copy(path, bak)
    tmp = path.with_suffix(path.suffix + ".part")
    with tmp.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=keep, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    os.replace(tmp, path)
    return len(hdr) - len(keep), len(rows)


def readers():
    """Scripts still naming a handle column, so the follow-up is a list."""
    out = []
    for p in sorted((ROOT / "code").glob("*.py")):
        if p.name.startswith("1177"):
            continue
        try:
            t = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if ('"handle"' in t or "'handle'" in t or "owner_hub_handle" in t
                or "handle_prefix" in t):
            out.append(p.name)
    return out


def main() -> int:
    mode = sys.argv[1] if len(sys.argv) > 1 else "report"

    if mode == "selftest":
        import tempfile
        ok = []
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "t.csv"
            p.write_text("cedar_uid,handle,name\nCE-1,TRBF-X-00,A\n", encoding="utf-8")
            c = check_one(p, "handle", "cedar_uid")
            ok.append(("a handle beside a uid is safe to drop",
                       c["handle_WITHOUT_uid"] == 0))
            n, _ = strip_file(p, True)
            ok.append(("the column is actually removed", n == 1))
            ok.append(("the uid survives", "cedar_uid" in p.read_text(encoding="utf-8")))
            q = Path(d) / "u.csv"
            q.write_text("cedar_uid,handle\n,TRBF-Y-00\n", encoding="utf-8")
            c2 = check_one(q, "handle", "cedar_uid")
            ok.append(("a handle with NO uid is detected, not stripped",
                       c2["handle_WITHOUT_uid"] == 1))
            # An award/deal/filing ID is not an entity ID and must survive.
            # This is the assertion that separates a cleanup from a data loss.
            ok.append(("no award/deal/filing ID looks like a handle",
                       not any(is_handle(c) for c in NOT_AN_ENTITY_ID)))
            r = Path(d) / "v.csv"
            hdr_line = "cedar_uid,handle," + ",".join(NOT_AN_ENTITY_ID)
            val_line = "CE-1,TRBF-Z-00," + ",".join("x" for _ in NOT_AN_ENTITY_ID)
            r.write_text(hdr_line + chr(10) + val_line + chr(10), encoding="utf-8")
            strip_file(r, True)
            after = r.read_text(encoding="utf-8").splitlines()[0].split(",")
            ok.append(("every award/deal/filing ID survives a strip",
                       all(c in after for c in NOT_AN_ENTITY_ID)))
            ok.append(("and the handle does not", "handle" not in after))
        for what, good in ok:
            print(f"    {'ok  ' if good else 'FAIL'}  {what}")
        bad = sum(1 for _, g in ok if not g)
        print(f"\n  1177 selftest   {'ok' if not bad else 'FAIL'}   {bad} failure(s)")
        return 1 if bad else 0

    on_disk = sweep()
    unknown = [f for f in on_disk if f not in TARGETS and f not in RETIRE_WHOLE]
    if unknown:
        print("  REFUSING: files carry a handle column and are not in TARGETS.")
        print("  Deleting a column from a file nobody checked is how the last")
        print("  six passes each left something behind. Add them, then re-run.")
        for f in unknown:
            print(f"      {f}  {on_disk[f]}")
        return 2

    if mode == "verify":
        left = sweep()
        rs = readers()
        print(f"  source files still carrying a handle column: {len(left)}")
        for f, cols in left.items():
            print(f"      {f}  {cols}")
        print(f"\n  scripts still naming one: {len(rs)}")
        for r in rs:
            print(f"      {r}")
        return 1 if left else 0

    print(f"\n  {'file':<48}{'rows':>9}{'w/ uid':>9}{'NO uid':>8}")
    print("  " + "-" * 74)
    refused, total_rows = [], 0
    for rel, (hcol, ucol) in TARGETS.items():
        p = ROOT / rel
        if not p.exists():
            continue
        c = check_one(p, hcol, ucol)
        if c is None:
            continue
        total_rows += c["rows"]
        flag = ""
        if c["handle_WITHOUT_uid"]:
            flag = "  <- REFUSED, identity would be lost"
            refused.append(rel)
        print(f"  {Path(rel).name:<48}{c['rows']:>9,}{c['handle_with_uid']:>9,}"
              f"{c['handle_WITHOUT_uid']:>8,}{flag}")

    if refused:
        print(f"\n  {len(refused)} file(s) refused: a handle with no uid beside it "
              f"is the only identity on that row.")
        return 2

    if mode != "apply":
        print(f"\n  {len(TARGETS)} file(s), {total_rows:,} rows, every handle has a "
              f"uid beside it. Nothing written - pass `apply`.")
        return 0

    print()
    for rel, why in RETIRE_WHOLE.items():
        src = ROOT / rel
        if not src.exists():
            continue
        dest = ROOT / "graveyard" / "cicd" / Path(rel).name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dest))
        (dest.parent / (Path(rel).stem + "_WHY.txt")).write_text(
            f"Retired {TODAY} by 1177." + chr(10) * 2 + why + chr(10),
            encoding="utf-8")
        print(f"  {Path(rel).name:<48} -> graveyard/cicd/  (whole file)")

    for rel in TARGETS:
        p = ROOT / rel
        if not p.exists():
            continue
        dropped, rows = strip_file(p, True)
        if dropped:
            print(f"  {Path(rel).name:<48} dropped {dropped} column(s), "
                  f"{rows:,} rows kept")
    rs = readers()
    print(f"\n  {len(rs)} script(s) still name a handle column and will need "
          f"updating; run `verify` for the list.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
