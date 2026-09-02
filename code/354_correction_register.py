#!/usr/bin/env python3
"""
Cedar Press - 354: the CORRECTION REGISTER, and the propagation check.

THE DEFECT THIS EXISTS FOR
--------------------------
`AGENTS.md` already carries the sentence:

    A RULING THAT IS NOT APPLIED BACK TO ITS SOURCE TABLE IS NOT A RULING,
    IT IS A NOTE.

`62_no_regression_check.py` measures that as `rulings_unapplied` (1,215) by
reading `cedar_ruling_ledger_consolidated.csv` for rows whose `status` is
`CONFLICT_NOT_APPLIED`. That catches a ruling that reached NO table.

**It cannot catch a correction that reached ONE table and not its siblings**,
and that is the same disease with a different name. Three live instances,
2026-08-26, every one of them found by a human reading a shipping table:

  FA-01  `65_lobbying_organization_type_guard.py` withdrew the Salt River
         Project attribution from `native_entity_lobbying_disclosures.csv` on
         2026-08-06. `tribe_year_lobbying_panel.csv` was built 2026-08-05 and
         was never rebuilt, so the panel still published
         **$40,279,500 / 557 filings** on `TRBF-SRPMCP-00` against a corrected
         $10,414,000 / 141. The correction was applied. It was applied to one
         file. `rulings_unapplied` reported nothing, correctly, because from
         its point of view the ruling WAS applied.

  FA-01b The same guard is a NAME-FORM bar, so it caught `CITY OF` and `MINES`
         and missed `SANTA ROSA COUNTY FL`, `SANTA ROSA JUNIOR COLLEGE` and
         `COEUR D'ALENE MINING`. A correction that covers one spelling of a
         defect and not its variants is the same failure inside one file.

  FA-02  94 `foia_request_index.csv` rows keyed to the Native Village of
         Georgetown because `georgetown.edu` appeared in a list of email
         domains a requester asked to be searched. A prior pass DEMOTED and
         FLAGGED them. A demoted wrong link is still a wrong link in a
         shipping column.

WHAT A REGISTER ROW IS
----------------------
One applied correction, stated so a machine can re-test it:

  - `entity_id` + `withdrawn_key` - the PAIR that must no longer co-occur in
    any row of any table. Not a column name: a VALUE PAIR. Column names differ
    across this project's tables (`entity_id`, `tribe_id`, `tribe_entity_id`,
    `native_entity_id`) and a check coupled to a column name goes blind the
    moment a consumer renames one. Standing rule 8 in a new place.
  - `table` - where the correction was APPLIED.
  - `rows_affected` / `rows_removed` - the exact accounting. `rows_removed` is
    what lets the shipping guard tell a withdrawal from a loss (see below).
  - `reason` - verbatim, in the register, not in a document somewhere.

THE SHIPPING ALLOWANCE, AND WHY IT IS NOT AN ACKNOWLEDGEMENT BUTTON
-------------------------------------------------------------------
`62` fails when a shipping table's row count falls, on the stated grounds that
*"there is no benign cause"*. Withdrawing 54 false panel rows IS a benign
cause, and it was not anticipated. Per the gate's own rule 2 - show it is not
a defect, change the check, say why - the allowance is:

    a fall is permitted ONLY when the register declares, for that table,
    a `rows_removed` total EXACTLY EQUAL to the fall.

Exact, never `<=`. If the table later loses one more row the arithmetic stops
matching and the gate fails again. A declared correction cannot be used to
wave away an unrelated loss, which is the failure mode of every "known issues"
list this project has ever kept.

USE
---
    py -3 code/354_correction_register.py --check     # propagation, verbose
    py -3 code/354_correction_register.py --apply     # finish every stale one
    py -3 code/354_correction_register.py --list

`62_no_regression_check.py` IMPORTS this module rather than re-implementing
it, exactly as it imports 160's registries: a detector holding its own copy of
a registry rebuilds the defect it is detecting.

Writes  data/clean/cedar_correction_register.csv   (APPEND-ONLY, by id)
        data/clean/_correction_scan_cache.json     (speed only, safe to delete)
"""

import csv
import json
import os
import sys
from pathlib import Path

def _derive(canonical, path):
    """Canonical order first, then any column the live file already carries.

    A FIXED literal header is the regenerate defect (ADR-017): a wholesale
    writer silently deleting an in-place enricher's column. Added 2026-09-02
    after `845` rule 17 flagged this writer as new since its baseline.
    """
    import csv as _csv, os as _os
    if not _os.path.exists(path):
        return list(canonical)
    try:
        with open(path, encoding="utf-8-sig", errors="replace") as _fh:
            live = next(_csv.reader(_fh), [])
    except OSError:
        return list(canonical)
    return list(canonical) + [c for c in live if c and c not in canonical]


csv.field_size_limit(min(sys.maxsize, 2147483647))

CEDAR = Path(__file__).resolve().parent.parent
CLEAN = CEDAR / "data" / "clean"
REGISTER = CLEAN / "cedar_correction_register.csv"
SCAN_CACHE = CLEAN / "_correction_scan_cache.json"

FIELDS = [
    "correction_id",        # stable, content-addressed on finding+entity+key
    "recorded_date",
    "recorded_by_script",
    "finding_id",           # FA-01 / FA-02 / ... as named in ANOMALY_REPORT.md
    "entity_id",            # the id that was WRONGLY attached
    "withdrawn_key",        # the SUBJECT it was wrongly attached to - see below
    "table",                # where the correction was APPLIED
    "column_unlinked",      # the column whose value was removed
    "rows_affected",
    "rows_removed",         # rows that CEASED TO EXIST in `table` (usually 0)
    "action",               # UNLINK | REPOINT | REBUILD
    "repointed_to",         # non-blank only for REPOINT
    "provenance_preserved", # columns deliberately KEPT so the fix is visible
    "reason",
]

# `withdrawn_key` MUST BE THE SUBJECT KEY THAT CROSSES TABLES.
#
# Two shapes were tried and only one works:
#
#   the MATCH PHRASE  -  wrong. `TRBF-ENTPRS-00` was withdrawn from 15 FOIA
#       rows whose `tribe_match_phrase` is the bare word 'Enterprise'. Two
#       OTHER rows carry the same phrase and are CORRECT (Enterprise Rancheria
#       land-into-trust). A pair-level invariant on the phrase cannot express
#       a row-level ruling, and it also flagged 306 `prime_contracts` rows
#       whose recipient name merely contains the English word.
#
#   the SUBJECT       -  right. The subject of a lobbying attribution is the
#       CLIENT NAME (`SANTA ROSA COUNTY FL`); the subject of a FOIA link is
#       the REQUEST (`DOI-2025-006304`). Both are the key a sibling table
#       would carry if it re-derived the same wrong link.
#
# One register row per (entity_id, subject). Verbose on purpose: the register
# is a data table, and a correction stated in aggregate cannot be re-tested.

# Cells in these columns are the PRESERVED PROVENANCE OF THE CORRECTION, not a
# live link, and must not count as the pair recurring. A correction that is
# recorded honestly - `attribution_withdrawn_entity_id`,
# `tribe_entity_id_withdrawn` - would otherwise report itself as its own
# unfixed consumer, and the only way to get a clean check would be to erase
# the evidence. That is precisely backwards.
PROVENANCE_MARKER = "withdrawn"

# Tables that are allowed to keep the pair because keeping it IS their job:
# review queues, refusal registers, the register itself, and the anomaly
# artefacts that exist to record the bad link. Named, never globbed - an
# exemption that matches by pattern eventually exempts a shipping table.
EXEMPT_TABLES = {
    "cedar_correction_register.csv",
    "cedar_ruling_ledger_consolidated.csv",
}


def read_csv(p):
    p = Path(p)
    if not p.exists():
        return []
    with open(p, newline="", encoding="utf-8-sig", errors="replace") as fh:
        return list(csv.DictReader(fh))


def load():
    """Every declared correction, as dicts. [] when the register is absent."""
    return read_csv(REGISTER)


def correction_id(finding_id, entity_id, withdrawn_key, table):
    import hashlib
    # Content-addressed and deliberately NOT positional: START_HERE.md records
    # three ids in this repo minted from Python's per-process-randomised
    # hash(), and a re-run changed 482 of 492 of them.
    h = hashlib.md5("|".join(
        (finding_id, entity_id, withdrawn_key, table)).encode("utf-8"))
    return f"CORR-{h.hexdigest()[:12]}"


def record(rows, script):
    """APPEND rows to the register, skipping ids already present.

    Append-only by construction: an existing correction is never rewritten,
    because a register that can be edited in place is a register that can be
    quietly emptied.
    """
    from datetime import date
    existing = load()
    have = {r.get("correction_id") for r in existing}
    fresh = []
    for r in rows:
        r = dict(r)
        r.setdefault("recorded_date", date.today().isoformat())
        r.setdefault("recorded_by_script", script)
        r["correction_id"] = r.get("correction_id") or correction_id(
            r.get("finding_id", ""), r.get("entity_id", ""),
            r.get("withdrawn_key", ""), r.get("table", ""))
        if r["correction_id"] in have:
            continue
        have.add(r["correction_id"])
        fresh.append({k: r.get(k, "") for k in FIELDS})
    if not fresh:
        return 0
    out = existing + fresh
    part = REGISTER.with_suffix(REGISTER.suffix + ".part")
    with open(part, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=_derive(FIELDS, REGISTER), extrasaction="ignore")
        w.writeheader()
        for r in out:
            w.writerow({k: r.get(k, "") for k in FIELDS})
    os.replace(part, REGISTER)
    return len(fresh)


def declared_row_removals():
    """{table: total rows the register says were REMOVED from it}."""
    out = {}
    for r in load():
        t = (r.get("table") or "").strip()
        try:
            n = int(float(r.get("rows_removed") or 0))
        except ValueError:
            n = 0
        if t and n:
            out[t] = out.get(t, 0) + n
    return out


# ---------------------------------------------------------------------------
# THE PROPAGATION CHECK
#
# A correction is propagated when NO table in data/clean still carries a row
# in which the withdrawn entity_id and the withdrawn key CO-OCCUR.
#
# Co-occurrence is tested on the ROW, across all cells, not on named columns.
# That is the whole point: the sibling tables use four different names for the
# same id column, and the check must survive a fifth.
# ---------------------------------------------------------------------------

def _load_cache():
    if SCAN_CACHE.exists():
        try:
            d = json.loads(SCAN_CACHE.read_text(encoding="utf-8"))
            if isinstance(d, dict):
                return d
        except Exception:
            pass
    return {}


def _save_cache(cache):
    try:
        part = SCAN_CACHE.with_suffix(SCAN_CACHE.suffix + ".part")
        part.write_text(json.dumps(cache), encoding="utf-8")
        os.replace(part, SCAN_CACHE)
    except Exception:
        pass                       # a cold cache costs time, never correctness


def _candidate_files(needles, cache):
    """Files whose BYTES contain every needle. Cheap prefilter, cached on
    (name, size, mtime) so an unchanged file is never re-read."""
    hits = {}
    for p in sorted(CLEAN.glob("*.csv")):
        if ".bak" in p.name or p.name.endswith(".part"):
            continue
        if p.name in EXEMPT_TABLES:
            continue
        st = p.stat()
        key = f"{p.name}|{st.st_size}|{int(st.st_mtime)}"
        entry = cache.get(key)
        if not isinstance(entry, dict):
            entry = {}
        missing = [n for n in needles if n not in entry]
        if missing:
            found = {n: False for n in missing}
            try:
                with open(p, "rb") as fh:
                    tail = b""
                    while True:
                        chunk = fh.read(1 << 22)
                        if not chunk:
                            break
                        buf = tail + chunk
                        for n in missing:
                            if not found[n] and n.encode("utf-8") in buf:
                                found[n] = True
                        if all(found.values()):
                            break
                        tail = buf[-128:]
            except Exception:
                found = {n: True for n in missing}   # unreadable -> inspect it
            entry.update(found)
            cache[key] = entry
        hits[p.name] = entry
    return hits


def check_propagation(verbose=False):
    """-> (n_stale, [ {correction_id, entity_id, withdrawn_key, table, rows} ])

    `table` here is the SIBLING still carrying the pair, never the table the
    correction was applied to.
    """
    regs = load()
    if not regs:
        return 0, []
    needles = sorted({r["entity_id"] for r in regs if r.get("entity_id")} |
                     {r["withdrawn_key"] for r in regs if r.get("withdrawn_key")})
    cache = _load_cache()
    byte_hits = _candidate_files(needles, cache)
    _save_cache(cache)

    # group by (entity_id, withdrawn_key) - one pair can be declared against
    # several tables, and it only has to be checked once.
    pairs = {}
    for r in regs:
        eid, key = r.get("entity_id", ""), r.get("withdrawn_key", "")
        if not eid or not key:
            continue
        pairs.setdefault((eid, key), []).append(r)

    stale = []
    for (eid, key), rs in sorted(pairs.items()):
        applied_to = {r.get("table", "") for r in rs}
        cands = [fn for fn, e in byte_hits.items()
                 if e.get(eid) and e.get(key)]
        for fn in sorted(cands):
            n = 0
            example = ""
            try:
                with open(CLEAN / fn, newline="", encoding="utf-8-sig",
                          errors="replace") as fh:
                    rd = csv.reader(fh)
                    hdr = next(rd, None) or []
                    # Drop the correction's own preserved provenance columns.
                    live = [i for i, h in enumerate(hdr)
                            if PROVENANCE_MARKER not in h.strip().lower()]
                    # A row that REFUTES the link is not a stale link. The
                    # identifier ledgers record a withdrawn attribution as
                    # confidence_tier = X - the house convention for a
                    # negative ruling, and what 510_assertions.py harvests as
                    # polarity=deny. The pair MUST co-occur in such a row: a
                    # refutation that does not name what it refutes is a
                    # blank, and blanks cannot say "this UEI is NOT BBNC".
                    tier_i = next((i for i, h in enumerate(hdr)
                                   if h.strip().lower() == "confidence_tier"),
                                  None)
                    for row in rd:
                        cells = set(row[i].strip() for i in live
                                    if i < len(row))
                        if eid in cells and key in cells:
                            if tier_i is not None and tier_i < len(row) \
                                    and row[tier_i].strip().upper() == "X":
                                continue
                            n += 1
                            if not example and hdr:
                                example = "; ".join(
                                    f"{hdr[i]}={row[i]}" for i in live
                                    if i < len(row)
                                    and row[i].strip() in (eid, key))
            except Exception:
                continue
            if n:
                stale.append({
                    "correction_id": rs[0]["correction_id"],
                    "finding_id": rs[0].get("finding_id", ""),
                    "entity_id": eid, "withdrawn_key": key,
                    "table": fn, "rows": n,
                    "was_applied_to": ", ".join(sorted(applied_to)),
                    "example": example,
                })
    if verbose:
        for s in stale:
            print(f"  !! {s['table']}: {s['rows']} row(s) still carry "
                  f"{s['entity_id']} <-> {s['withdrawn_key']!r} "
                  f"({s['finding_id']}, applied to {s['was_applied_to']})")
    return len(stale), stale


def apply_propagation():
    """Finish every correction the checker calls stale, using the checker's
    own findings - the finder and the fixer are one function apart, so they
    cannot disagree about what needs doing.

    Two actions, chosen by what the table is:

      identifier ledgers  -> confidence_tier = X, pair KEPT. The house
                             convention for a negative ruling (71 does this
                             for barred firms; 510 harvests it as a deny
                             assertion). The refutation must name what it
                             refutes, so eid and key stay in the row.
      every other table   -> UNLINK, exactly the action the original FA-01
                             correction applied: blank each cell equal to the
                             withdrawn entity_id (or its cedar_uid - the uid
                             would otherwise keep the link alive under a
                             different name), keep the observed name and every
                             provenance column.

    NOT done here, deliberately: repointing the rows to SGVF-BRSTLB-00, the
    spine's own Bristol Bay Area Health Corporation. That would key 695
    funding rows' dollars to an entity by name evidence, and the standing rule
    is that keying a dollar is a RULING, not a computation. The proposal goes
    to the rulings inbox instead.
    """
    import shutil
    from datetime import date
    n, stale = check_propagation(verbose=False)
    if not n:
        print("  nothing stale - the register is fully propagated")
        return 0
    regs = load()
    by_pair = {}
    for r in regs:
        by_pair.setdefault((r.get("entity_id", ""), r.get("withdrawn_key", "")), r)
    today = date.today().isoformat()

    by_table = {}
    for s in stale:
        by_table.setdefault(s["table"], []).append(s)

    new_regs = []
    for fn, items in sorted(by_table.items()):
        path = CLEAN / fn
        rows = read_csv(path)
        if not rows:
            continue
        hdr = list(rows[0].keys())
        is_ledger = fn.startswith("cedar_identifier_ledger")
        shutil.copy2(path, str(path) + f".bak_{today}_pre354")
        touched = {s["entity_id"]: 0 for s in items}
        for s in items:
            eid, key = s["entity_id"], s["withdrawn_key"]
            orig = by_pair.get((eid, key), {})
            uid = (orig.get("cedar_uid") or "").strip()
            reason = (orig.get("reason") or "").strip()
            hit = 0
            for r in rows:
                cells = {v.strip() for v in r.values() if v}
                if eid not in cells or key not in cells:
                    continue
                if is_ledger:
                    if (r.get("confidence_tier") or "").upper() == "X":
                        continue
                    r["confidence_tier"] = "X"
                    r["tier_rationale"] = (
                        f"Withdrawn {today} by 354 propagation of "
                        f"{orig.get('correction_id', 'FA-01')}: {reason}"
                    )[:500]
                else:
                    for col in hdr:
                        v = (r.get(col) or "").strip()
                        if v == eid or (uid and v == uid):
                            r[col] = ""
                hit += 1
            if hit:
                new_regs.append({
                    "finding_id": s.get("finding_id") or "FA-01",
                    "entity_id": eid,
                    "withdrawn_key": key,
                    "table": fn,
                    "column_unlinked": ("confidence_tier=X" if is_ledger
                                        else "every cell equal to the id"),
                    "rows_affected": hit,
                    "rows_removed": 0,
                    "action": "REFUTE" if is_ledger else "UNLINK",
                    "repointed_to": "",
                    "provenance_preserved": "all name and evidence columns",
                    "reason": reason or "propagated from the applied "
                                        "correction; see the original row",
                    "cedar_uid": uid,
                })
                touched[s["entity_id"]] = touched.get(s["entity_id"], 0) + hit
                print(f"  {fn}: {hit} row(s) "
                      f"{'REFUTED (tier X)' if is_ledger else 'unlinked'} "
                      f"for {eid} <-> {key[:40]!r}")
        with open(path, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=hdr, extrasaction="ignore")
            w.writeheader()
            w.writerows(rows)
    added = record(new_regs, "354_correction_register.py --apply")
    print(f"\n  {added} correction row(s) appended to the register")
    n2, _ = check_propagation(verbose=False)
    print(f"  re-check: {n2} stale consumer(s) remain")
    return 1 if n2 else 0


def main():
    regs = load()
    print("=== Cedar Press 354: correction register ===\n")
    print(f"  register: {REGISTER.relative_to(CEDAR)}")
    print(f"  declared corrections: {len(regs):,}")
    if "--apply" in sys.argv:
        print("  applying every stale propagation:\n")
        return apply_propagation()
    if "--list" in sys.argv:
        for r in regs:
            print(f"   {r['correction_id']}  {r['finding_id']:6s} "
                  f"{r['entity_id']:16s} {r['action']:8s} "
                  f"{r['withdrawn_key'][:44]:44s} -> {r['table']} "
                  f"(rows_affected={r['rows_affected']}, "
                  f"rows_removed={r['rows_removed']})")
    rm = declared_row_removals()
    if rm:
        print("\n  declared row REMOVALS (the shipping allowance):")
        for t, n in sorted(rm.items()):
            print(f"    {t}: {n}")
    print("\n  propagation check - every sibling table that still carries a "
          "withdrawn pair:")
    n, stale = check_propagation(verbose=True)
    if n == 0:
        print("     none. Every declared correction reached every table that "
              "carries the pair.")
    else:
        print(f"\n  {n} stale consumer(s). A correction that lands in one "
              f"table and not its siblings\n  is the same disease as a ruling "
              f"that lands in no table at all.")
    return 1 if n else 0


if __name__ == "__main__":
    raise SystemExit(main())
