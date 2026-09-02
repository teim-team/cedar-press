#!/usr/bin/env python3
"""
Cedar Press - 961: PROMOTE THE FEDERAL REGISTER LEGAL NAME AND THE STATE ONTO
`data/spine/cedar_identity_register.csv`.

    py -3 code/961_promote_register_legal_names_and_state.py
    py -3 code/961_promote_register_legal_names_and_state.py verify
    py -3 code/961_promote_register_legal_names_and_state.py selftest

WHY
---
`docs/WHAT_IS_MISSING.md`, `_entity_layer` #1 and #2, both
`ON_DISK_NOT_PROMOTED`:

  *"The register's canonical_name is a colloquial stub, not the entity's legal
  name... A buyer searching for `Little River Band of Ottawa Indians` or
  `Table Mountain Rancheria` finds nothing. 536 register entities have their
  legally operative Federal Register name on disk in
  `federal_recognition_roster.csv`, keyed by cedar_uid - and 509 of the 536
  differ from what the register shows."*

Re-measured 2026-09-02 against the live files: **536 register uids appear in
the roster, 509 carry an FR entity name that differs from the register's
canonical_name, 27 match.** Both figures reproduce exactly.

  Absentee-Shawnee  ->  Absentee-Shawnee Tribe of Indians of Oklahoma
  Lovelock          ->  Lovelock Paiute Tribe of the Lovelock Indian Colony, Nevada
  Ak Chin           ->  Ak-Chin Indian Community

WHY THE STUB IS NOT OVERWRITTEN - a decision, stated
-----------------------------------------------------
The obvious move is to write the legal name into `canonical_name`. It is
refused, for one reason: **`canonical_name` is a join key in fact if not in
name.** Twenty scripts read this register and more read the spine's identical
column; the short form is what alias matching, review queues and several
hand-built crosswalks compare against. Replacing 509 of 1,555 values in one
pass, from an agent that cannot test every consumer, is how a token match
becomes a mis-attribution - and `AGENTS.md` opens on exactly that failure.

So the legal name arrives as **its own column, beside the stub**, and the
customer-facing sample is repointed at it (`code/770_sample_extracts.py`). A
buyer searching either string now finds the entity; nothing downstream moves.
`cedar_uid` is untouched on every row - no uid is minted, retired or
repointed, and no `handle` changes.

WHAT IS WRITTEN - FIVE COLUMNS
------------------------------
  federal_register_legal_name          the entity name as printed in the most
                                       recent BIA annual list that names it
  federal_register_legal_name_basis    the FR document number, its publication
                                       date and the roster entry kind
  federal_register_legal_name_url      the notice
  state                                from `cedar_entity_spine.csv` (1,492 of
                                       1,555 filled), which the register drops
  minted_basis                         says outright that `minted` records the
                                       REGISTER REBUILD, not when the entity
                                       was minted. The column name promises
                                       the opposite of what it holds and Cedar
                                       has no earlier mint record:
                                       `cedar_handle_history.csv` first
                                       recorded 1,536 of these bindings on
                                       2026-08-29 and 19 on 2026-09-01.

Only entities that the BIA list actually names get a legal name. A Native
Hawaiian Organisation, a BIE school and an ANCSA village corporation are not
on the federally recognised tribes list and correctly get a blank - that is
`OUT_OF_SCOPE_BY_CONSTRUCTION`, not a gap, and the basis column says so.

THE NAMED INVARIANTS - all exit 1
---------------------------------
  INV-ROWS   1,555 rows in, 1,555 out
  INV-UID    the exact set of cedar_uid values is unchanged, in order
  INV-STUB   `canonical_name`, `handle` and `cedar_entity_id` are byte-identical
  INV-NAME   every populated `federal_register_legal_name` equals an
             `entity_name` printed in `federal_recognition_roster.csv` for
             THAT uid - the join cannot invent a legal name
  INV-BASIS  a populated name has a populated basis and url

REBUILD ORDERING
----------------
`code/503_identity.py --apply` rewrites this register from a fixed ten-column
list and reverts all five. Re-run 961 after it.

**AND FLAG, WHILE HERE:** that same fixed list still contains
`same_as_legacy_cicd`, which `code/843_retire_cicd_scheme.py` deliberately
removed from the data on 2026-09-01. A rebuild of 503 would reintroduce a
retired scheme. Not fixed here - 503 is identity-critical and owned elsewhere -
but recorded in `docs/KNOWN_ISSUES.md` so it is not rediscovered.
"""
from __future__ import annotations

import csv
import hashlib
import json
import shutil
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
csv.field_size_limit(10_000_000)
TODAY = date.today().isoformat()

REGISTER = ROOT / "data" / "spine" / "cedar_identity_register.csv"
SPINE = ROOT / "data" / "spine" / "cedar_entity_spine.csv"
ROSTER = ROOT / "data" / "clean" / "federal_recognition_roster.csv"
MANIFEST = ROOT / "docs" / "REGISTER_NAME_PROMOTION.json"
BAK_TAG = f".bak_{TODAY}_pre961"

NEW = ["federal_register_legal_name", "federal_register_legal_name_basis",
       "federal_register_legal_name_url", "state", "minted_basis"]

FROZEN = ["cedar_uid", "handle", "cedar_entity_id", "canonical_name"]

MINTED_BASIS = ("`minted` records the date the REGISTER was rebuilt, not when "
                "this entity was first minted - it is 2026-09-01 on all 1,555 "
                "rows. Cedar holds no earlier mint record; the first recorded "
                "handle<->uid binding is in cedar_handle_history.csv "
                "(1,536 rows dated 2026-08-29, 19 dated 2026-09-01).")

OUT_OF_SCOPE = ("OUT_OF_SCOPE_BY_CONSTRUCTION - this entity class is not "
                "listed in the BIA annual list of federally recognized "
                "tribes, so no Federal Register legal name exists for it")

NOT_LISTED = ("NOT_IN_SOURCE - a federally recognised entity class, but no "
              "entry keyed to this cedar_uid was found in "
              "federal_recognition_roster.csv (1995-2026)")

# Classes the BIA annual list actually enumerates.
FR_LISTED_CLASSES = {"Federally recognized tribe",
                     "Federally recognized Alaska Native Village"}

US = "\x1f"


def read_csv(p: Path) -> list:
    with p.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
        return list(csv.DictReader(fh))


def roster_names() -> tuple[dict, dict]:
    """cedar_uid -> (name, basis, url); and uid -> {every name ever printed}."""
    by = defaultdict(list)
    seen = defaultdict(set)
    for r in read_csv(ROSTER):
        u = (r.get("cedar_uid") or "").strip()
        nm = (r.get("entity_name") or "").strip()
        if not u or not nm:
            continue
        by[u].append(r)
        seen[u].add(nm)
    out = {}
    for u, rs in by.items():
        # The list itself, not a rename note or a cross-reference.
        pool = [r for r in rs if (r.get("entry_kind") or "") == "entity"] or rs
        latest = max(pool, key=lambda r: ((r.get("publication_date") or ""),
                                          (r.get("list_order") or "")))
        basis = (f"federal_recognition_roster.csv, FR document "
                 f"{latest.get('fr_document_number')} "
                 f"({latest.get('fr_citation') or 'citation not stated'}) "
                 f"published {latest.get('publication_date')}; entry_kind "
                 f"{latest.get('entry_kind')}; the most recent BIA annual list "
                 f"naming this entity. The legally operative name.")
        out[u] = ((latest.get("entity_name") or "").strip(), basis,
                  (latest.get("source_url") or "").strip())
    return out, seen


def spine_state() -> dict:
    return {(r.get("cedar_uid") or "").strip(): (r.get("state") or "").strip()
            for r in read_csv(SPINE) if (r.get("cedar_uid") or "").strip()}


def _frozen_digest(rows: list) -> str:
    h = hashlib.md5()
    for r in rows:
        h.update(US.join((r.get(c) or "") for c in FROZEN)
                 .encode("utf-8", "replace"))
    return h.hexdigest()


def enrich() -> int:
    names, _ = roster_names()
    st = spine_state()
    rows = read_csv(REGISTER)
    with REGISTER.open(encoding="utf-8-sig", errors="replace",
                       newline="") as fh:
        hdr = next(csv.reader(fh))
    orig = [c for c in hdr if c not in NEW]

    stats = Counter()
    for r in rows:
        u = (r.get("cedar_uid") or "").strip()
        cls = (r.get("entity_class") or "").strip()
        hit = names.get(u)
        if hit and hit[0]:
            nm, basis, url = hit
            stats["legal_name"] += 1
            if nm != (r.get("canonical_name") or "").strip():
                stats["differs_from_stub"] += 1
            else:
                stats["matches_stub"] += 1
        else:
            nm, url = "", ""
            basis = NOT_LISTED if cls in FR_LISTED_CLASSES else OUT_OF_SCOPE
            stats["no_legal_name"] += 1
            stats["reason::" + basis.split(" -")[0]] += 1
        s = st.get(u, "")
        if s:
            stats["state"] += 1
        r.update({"federal_register_legal_name": nm,
                  "federal_register_legal_name_basis": basis,
                  "federal_register_legal_name_url": url,
                  "state": s,
                  "minted_basis": MINTED_BASIS})

    shutil.copy2(REGISTER, REGISTER.with_name(REGISTER.name + BAK_TAG))
    final = orig + NEW
    tmp = REGISTER.with_suffix(".csv.part")
    with tmp.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=final, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)
    tmp.replace(REGISTER)

    man = {"built_date": TODAY, "rows": len(rows),
           "columns_before": len(orig), "columns_after": len(final),
           "columns_gained": NEW, "columns_lost": [],
           "frozen_md5": _frozen_digest(rows),
           "uid_md5": hashlib.md5(
               US.join((r.get("cedar_uid") or "") for r in rows)
               .encode("utf-8")).hexdigest(),
           "stats": dict(stats), "backup": REGISTER.name + BAK_TAG,
           "script": "code/961_promote_register_legal_names_and_state.py"}
    MANIFEST.write_text(json.dumps(man, indent=2), encoding="utf-8")

    print(f"  961 cedar_identity_register.csv  rows {len(rows):,}  "
          f"cols {len(orig)} -> {len(final)} (+{len(NEW)}, -0)")
    print(f"    FR legal name        {stats['legal_name']:>5}  "
          f"(differs from the stub {stats['differs_from_stub']}, "
          f"identical {stats['matches_stub']})")
    print(f"    no FR legal name     {stats['no_legal_name']:>5}")
    for k in sorted(k for k in stats if k.startswith("reason::")):
        print(f"        {k[8:]:<36} {stats[k]:>5}")
    print(f"    state                {stats['state']:>5} of {len(rows):,} "
          f"({100*stats['state']/len(rows):.1f}%)")
    print("    cedar_uid / handle / canonical_name: UNTOUCHED")
    return 0


def verify(path: Path | None = None) -> int:
    p = path or REGISTER
    if not MANIFEST.exists():
        print("  [961] verify: no manifest - run the enricher first")
        return 1
    man = json.loads(MANIFEST.read_text(encoding="utf-8"))
    _, seen = roster_names()
    rows = read_csv(p)
    fails = []

    bad_name = bad_basis = 0
    ex = []
    for r in rows:
        u = (r.get("cedar_uid") or "").strip()
        nm = (r.get("federal_register_legal_name") or "").strip()
        if nm:
            if nm not in seen.get(u, set()):
                bad_name += 1
                if len(ex) < 5:
                    ex.append((u, nm))
            if not (r.get("federal_register_legal_name_basis") or "").strip() \
                    or not (r.get("federal_register_legal_name_url")
                            or "").strip():
                bad_basis += 1
        elif not (r.get("federal_register_legal_name_basis") or "").strip():
            bad_basis += 1

    if len(rows) != man["rows"]:
        fails.append(f"INV-ROWS {man['rows']:,} -> {len(rows):,}")
    uid_md5 = hashlib.md5(US.join((r.get("cedar_uid") or "") for r in rows)
                          .encode("utf-8")).hexdigest()
    if uid_md5 != man["uid_md5"]:
        fails.append("INV-UID the cedar_uid set or its order changed - a uid "
                     "must never move as a side effect of a name fix")
    if _frozen_digest(rows) != man["frozen_md5"]:
        fails.append("INV-STUB canonical_name / handle / cedar_entity_id "
                     "changed")
    if bad_name:
        fails.append(f"INV-NAME {bad_name} legal name(s) are not printed for "
                     f"that uid anywhere in the roster; e.g. {ex}")
    if bad_basis:
        fails.append(f"INV-BASIS {bad_basis} row(s) missing basis or url")

    print(f"  [961] verify  rows {len(rows):,}   fabricated names {bad_name}  "
          f" missing basis {bad_basis}")
    for f in fails:
        print(f"  [961] !! {f}")
    return 1 if fails else 0


def selftest() -> int:
    """Prove verify FIRES. Give one entity a legal name the roster never
    printed for it, on a copy. Expect exit 1."""
    if not MANIFEST.exists():
        print("  [961] selftest: run the enricher first")
        return 1
    fix = REGISTER.with_name("_961_selftest_fixture.csv")
    with REGISTER.open(encoding="utf-8-sig", errors="replace",
                       newline="") as fh:
        rd = csv.reader(fh)
        hdr = next(rd)
        rows = list(rd)
    i = hdr.index("federal_register_legal_name")
    ib = hdr.index("federal_register_legal_name_basis")
    iu = hdr.index("federal_register_legal_name_url")

    def write(rs):
        with fix.open("w", encoding="utf-8", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(hdr)
            w.writerows(rs)

    try:
        write(rows)
        clean = verify(fix)
        hit = next(r for r in rows if r[i].strip())
        keep = r0, r1, r2 = hit[i], hit[ib], hit[iu]
        hit[i] = "Cherokee Nation"        # a real tribe, the WRONG uid
        write(rows)
        dirty = verify(fix)
        hit[i], hit[ib], hit[iu] = keep
    finally:
        fix.unlink(missing_ok=True)
    ok = (clean == 0 and dirty == 1)
    print(f"  [961] selftest  clean exit {clean} (want 0)   "
          f"mis-keyed legal name exit {dirty} (want 1)   "
          f"{'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "enrich"
    sys.exit({"enrich": enrich, "verify": verify, "selftest": selftest}[cmd]())
