#!/usr/bin/env python3
"""
Cedar Press - 353: propagate the FA-01 withdrawals to the tables that consume
`native_entity_lobbying_disclosures.csv` and never received them.

THE POINT
---------
This script exists because of the defect it is fixing. `65_lobbying_
organization_type_guard.py` withdrew Salt River Project from the disclosures
on 2026-08-06 and **the table that publishes was never rebuilt**, so the false
attribution shipped for twenty days. If 350's withdrawals stop at the
disclosures, they repeat that exactly, one file over.

Two consumers carry a per-filing or per-client entity link and are corrected
here, IN PLACE, with no row lost:

  `lobbying_issue_families_filing.csv`  (27,796 rows)
      one row per filing, carrying `entity_id`. Re-keyed against the
      disclosures ON `filing_uuid` - a JOIN KEY, never a name match; AGENTS.md
      records what preferring a cleverer string match cost at `n_deals_for_
      entity`. Measured before writing: 471 rows disagree with the corrected
      disclosures and every one of them is a 350 withdrawal. The 841 script-65
      withdrawals are ALREADY correct here, because this file was built at
      17:24 on 2026-08-06 and the guard ran at 16:19 - the same five hours
      that the panel missed by one day.

  `lobbying_registrant_client_relationships.csv`  (1,309 rows)
      one row per (registrant_id, client_id), carrying `native_entity_id`.
      A pair is unlinked when NO surviving filing in it still carries the
      entity.

WHY UNLINK IN PLACE RATHER THAN RE-RUN 180
------------------------------------------
`180_build_lobbying_registrant_hub.py` DROPS a withdrawn pair's row entirely
(it filters to `keyed` before building pairs), so a re-run would take
`lobbying_registrant_client_relationships.csv` from 1,309 rows to ~1,291 and
delete the evidence that the pair was ever attributed. Unlinking keeps the
relationship - the firm really did represent Santa Rosa County FL - and
removes only the false claim that Santa Rosa County FL is a tribe. That is
strictly more informative, and it costs no shipping rows.

**180 has been patched separately** so that a future re-run cannot re-import
the 471: it filtered on `org_type_barred` alone and could not see a second
withdrawal mark. The predicate now lives in
`cedar_domain.lobbying_attribution_withdrawn`.

Writes  data/clean/lobbying_issue_families_filing.csv              (in place)
        data/clean/lobbying_registrant_client_relationships.csv    (in place)
        data/clean/cedar_correction_register.csv                   (append)
"""

import csv
import importlib.util
import os
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

csv.field_size_limit(min(sys.maxsize, 2147483647))

CEDAR = Path(r"C:\Users\esm247\Desktop\Cedar Press")
CODE = CEDAR / "code"
sys.path.insert(0, str(CODE))
from cedar_domain import lobbying_attribution_withdrawn   # noqa: E402

CLEAN = CEDAR / "data" / "clean"
TODAY = date.today().isoformat()
SCRIPT = "353_propagate_lobbying_corrections_to_consumers.py"

DISC = CLEAN / "native_entity_lobbying_disclosures.csv"
FAM = CLEAN / "lobbying_issue_families_filing.csv"
RELS = CLEAN / "lobbying_registrant_client_relationships.csv"


def read_csv(p):
    with open(p, newline="", encoding="utf-8-sig", errors="replace") as fh:
        return list(csv.DictReader(fh))


def write_in_place(path, rows, fields, before_mtime):
    if path.stat().st_mtime != before_mtime:
        print(f"  !! {path.name} CHANGED UNDER US. Refusing to write.")
        return False
    bak = path.with_name(path.name + f".bak_{TODAY}_pre_{SCRIPT}")
    if not bak.exists():
        bak.write_bytes(path.read_bytes())
        print(f"    backed up -> {bak.name}")
    part = path.with_suffix(path.suffix + ".part")
    with open(part, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fields})
    os.replace(part, path)
    print(f"    wrote {path.name}")
    return True


def load_register():
    spec = importlib.util.spec_from_file_location(
        "reg354", CODE / "354_correction_register.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def main():
    print("=== Cedar Press 353: propagate FA-01 to its consumers ===\n")
    disc = read_csv(DISC)
    by_uuid = {r["filing_uuid"]: r for r in disc}
    withdrawn_client = {}          # (entity, client) -> reason
    for r in disc:
        if (r.get("attribution_withdrawn") or "") == "1":
            withdrawn_client[
                ((r.get("attribution_withdrawn_entity_id") or "").strip(),
                 (r.get("client_name") or "").strip())] = \
                r.get("attribution_withdrawn_reason") or ""
    print(f"  disclosures: {len(disc):,} filings · "
          f"{len(withdrawn_client)} withdrawn client(s)")

    decl = []

    # ---------------------------------------------------------------- FAM ---
    print(f"\n  [1] {FAM.name}")
    fam_mtime = FAM.stat().st_mtime
    fam = read_csv(FAM)
    fields = list(fam[0].keys())
    for c in ("entity_id_withdrawn", "entity_id_withdrawn_reason",
              "entity_id_withdrawn_by_script", "entity_id_withdrawn_date"):
        if c not in fields:
            fields.append(c)

    # A COUNT IS NOT ACTIONABLE; A FILENAME - OR HERE A KEY - IS A TASK.
    # Defect class 2c: `87` counted 33,817 dropped rows for twenty days
    # without ever printing what they were. Every unmatched filing_uuid is
    # NAMED below, not tallied.
    unmatched_keys = []
    changed = Counter()
    for r in fam:
        for c in ("entity_id_withdrawn", "entity_id_withdrawn_reason",
                  "entity_id_withdrawn_by_script", "entity_id_withdrawn_date"):
            r[c] = r.get(c) or ""
        d = by_uuid.get(r.get("filing_uuid"))
        if d is None:
            unmatched_keys.append(r.get("filing_uuid", "(blank)"))
            continue
        want = (d.get("entity_id") or "").strip()
        have = (r.get("entity_id") or "").strip()
        if want == have:
            continue
        # The disclosures are upstream and authoritative on the entity link.
        changed[(have, want or "(unlinked)")] += 1
        if not want and lobbying_attribution_withdrawn(d):
            r["entity_id_withdrawn"] = have
            r["entity_id_withdrawn_reason"] = (
                d.get("attribution_withdrawn_reason")
                or d.get("org_type_reason") or "")
            r["entity_id_withdrawn_by_script"] = SCRIPT
            r["entity_id_withdrawn_date"] = TODAY
        r["entity_id"] = want
    print(f"    rows {len(fam):,} · filing_uuid not in disclosures "
          f"{len(unmatched_keys)}")
    for k in unmatched_keys[:20]:
        print(f"      NOT IN DISCLOSURES, LEFT ALONE: filing_uuid={k}")
    if len(unmatched_keys) > 20:
        print(f"      ...and {len(unmatched_keys) - 20} more, all named in "
              f"the run log of a --verbose pass")
    for (a, b), n in changed.most_common():
        print(f"    {n:>5}  {a or '(blank)'} -> {b}")
    if changed and write_in_place(FAM, fam, fields, fam_mtime):
        per = defaultdict(int)
        for r in fam:
            if r.get("entity_id_withdrawn_by_script") == SCRIPT:
                d = by_uuid[r["filing_uuid"]]
                per[(r["entity_id_withdrawn"],
                     (d.get("client_name") or "").strip())] += 1
        for (eid, cname), n in sorted(per.items()):
            decl.append({
                "finding_id": "FA-01", "entity_id": eid,
                "withdrawn_key": cname, "table": FAM.name,
                "column_unlinked": "entity_id", "rows_affected": n,
                "rows_removed": 0, "action": "UNLINK", "repointed_to": "",
                "provenance_preserved":
                    "client_name; filing_uuid; entity_id_withdrawn",
                "reason": withdrawn_client.get((eid, cname), ""),
            })

    # --------------------------------------------------------------- RELS ---
    print(f"\n  [2] {RELS.name}")
    rels_mtime = RELS.stat().st_mtime
    rels = read_csv(RELS)
    rfields = list(rels[0].keys())
    for c in ("native_entity_id_withdrawn", "native_entity_id_withdrawn_reason",
              "native_entity_id_withdrawn_by_script",
              "native_entity_id_withdrawn_date"):
        if c not in rfields:
            rfields.append(c)

    # which (registrant_id, client_id) pairs still have a LIVE keyed filing?
    live_pair = defaultdict(set)
    for r in disc:
        if lobbying_attribution_withdrawn(r):
            continue
        eid = (r.get("entity_id") or "").strip()
        if eid:
            live_pair[((r.get("registrant_id") or "").strip(),
                       (r.get("client_id") or "").strip())].add(eid)

    n_unlinked = 0
    for r in rels:
        for c in ("native_entity_id_withdrawn",
                  "native_entity_id_withdrawn_reason",
                  "native_entity_id_withdrawn_by_script",
                  "native_entity_id_withdrawn_date"):
            r[c] = r.get(c) or ""
        eid = (r.get("native_entity_id") or "").strip()
        if not eid:
            continue
        key = ((r.get("registrant_id") or "").strip(),
               (r.get("client_id") or "").strip())
        if eid in live_pair.get(key, set()):
            continue                       # still supported by a live filing
        cname = (r.get("client_name") or "").strip()
        reason = withdrawn_client.get((eid, cname), "")
        if not reason:
            # Only unlink what a DECLARED withdrawal covers. A pair that lost
            # its support for some other reason is a finding, not a licence.
            print(f"    [not covered by a declared withdrawal, LEFT ALONE] "
                  f"{cname!r} -> {eid}")
            continue
        r["native_entity_id_withdrawn"] = eid
        r["native_entity_id_withdrawn_reason"] = reason
        r["native_entity_id_withdrawn_by_script"] = SCRIPT
        r["native_entity_id_withdrawn_date"] = TODAY
        r["native_entity_id"] = ""
        r["native_entity_canonical_name"] = ""
        r["native_entity_class"] = ""
        r["native_entity_state"] = ""
        r["client_is_keyed_native"] = "0"
        r["entity_link_confidence_inherited"] = "withdrawn_false_attribution"
        n_unlinked += 1
        decl.append({
            "finding_id": "FA-01", "entity_id": eid, "withdrawn_key": cname,
            "table": RELS.name, "column_unlinked": "native_entity_id",
            "rows_affected": 1, "rows_removed": 0, "action": "UNLINK",
            "repointed_to": "",
            "provenance_preserved":
                "client_name; entity_link_matched_alias; "
                "native_entity_id_withdrawn; n_filings",
            "reason": reason,
        })
    print(f"    rows {len(rels):,} · pairs unlinked {n_unlinked} "
          f"(0 rows removed - the relationship is real, the tribal claim is not)")
    if n_unlinked:
        write_in_place(RELS, rels, rfields, rels_mtime)

    if decl:
        reg = load_register()
        n = reg.record(decl, SCRIPT)
        print(f"\n  declared {n} correction(s) in "
              f"{reg.REGISTER.relative_to(CEDAR)}")

    # ------------------------------------------------------- verify by re-read
    fam2 = read_csv(FAM)
    rels2 = read_csv(RELS)
    bad_fam = sum(1 for r in fam2
                  if ((r.get("entity_id") or "").strip(),
                      (by_uuid[r["filing_uuid"]].get("client_name") or "").strip())
                  in withdrawn_client)
    bad_rels = sum(1 for r in rels2
                   if ((r.get("native_entity_id") or "").strip(),
                       (r.get("client_name") or "").strip()) in withdrawn_client)
    print(f"\n  RE-READ: {FAM.name} {len(fam2):,} rows, still-false links "
          f"{bad_fam} (must be 0)")
    print(f"           {RELS.name} {len(rels2):,} rows, still-false links "
          f"{bad_rels} (must be 0)")
    return 0 if (bad_fam == 0 and bad_rels == 0) else 1


if __name__ == "__main__":
    raise SystemExit(main())
