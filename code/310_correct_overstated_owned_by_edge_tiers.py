#!/usr/bin/env python3
"""
Cedar Press - 310: correct the OVER-STATED tier on `owned_by` edges in
`data/clean/entity_relationships.csv`, IN PLACE.

    py -3 code/310_correct_overstated_owned_by_edge_tiers.py            # dry run
    py -3 code/310_correct_overstated_owned_by_edge_tiers.py --apply    # write

NO NETWORK. Reads two files, writes one, and only ever moves a tier DOWN.

WHY
---
`97_build_aliases_and_relationships.py` minted every ledger-sourced `owned_by`
edge at **tier A with confidence 0.90**, whatever the source row said:

    if tier != Tier.A and not ruled:      # METHOD MEMBERSHIP admits the row
        continue
    add("", "owned_by", eid, tier=D.Tier.A.value, confidence=0.90, ...)

`attribution_method` says WHO decided; `confidence_tier` says WHAT was decided.
A human deciding "B" is still a B. `owned_by` is in
`cedar_domain.OWNERSHIP_BEARING`, so the edge can carry money, and a tier-A
ownership edge is the strongest claim this project makes about a firm.

**It is not the negative-ruling bug.** 97 drops `confidence_tier == X` before
that loop, so no exclusion reaches it. The ENTITY is right on every affected
row; only the TIER is over-stated.

97 was fixed the same day to inherit the tier verbatim. **97 is a FULL
REBUILD** of `entity_relationships.csv` (and of `entity_aliases.csv`, and it
refreshes its own codebook block), and `entity_relationships.csv` has in-place
consumers, so re-running it to pick up the fix is the rebuild/in-place
collision this project has now paid for four times. Hence this script: the same
correction, applied to the live rows only, touching nothing else.

WHAT IT CHANGES, PER ROW
------------------------
    tier                 A  ->  the tier the ledger row actually carries
    confidence         0.90 ->  {A: 0.90, B: 0.60, C: 0.40}[tier]
    verification_status RULED/TIER_A -> RULED_TIER_<t> / TIER_<t>
    notes                appended with the correction, its date and its reason

`source_entity_id`, `target_entity_id`, `relationship_type`,
`relationship_id`, `evidence_text` and every other column are untouched. **No
row is added, removed, promoted or re-typed.**

HOW A LIVE EDGE IS MATCHED BACK TO ITS SOURCE ROW
-------------------------------------------------
97 writes the firm's legal name and its identifier into `notes`:

    firm 'Tigua-Jtek Llc' (CAGE 8EGN7) is owned by this Native entity ...

so the join key is (`target_entity_id`, normalised legal name) - 97's own
dedupe key - with the identifier used as a cross-check. `norm` is imported from
`33_apply_party_rulings`, the ONE resolver (regression rule 8), never
re-implemented: a normaliser that turns a diacritic into a space cost eight
Hawaiian organisations their EINs once.

Where several ledger rows share that key, the STRONGEST non-X tier wins. That
is still inheriting - it never writes a tier no source row states - and it is
what stops the answer depending on ledger row ORDER.

REFUSALS, STATED UP FRONT
-------------------------
  * A row whose correct tier is A or higher than its current tier is LEFT
    ALONE. This script demotes only. Promotion needs a rebuild.
  * A row whose source cannot be found in today's ledger is LEFT ALONE and
    NAMED. "I could not find it" is not "it is fine", and a count with no
    names is not actionable.
  * Tier X never appears: a ledger row at X is an exclusion, and an exclusion
    that reached an ownership edge would be a different and much worse bug -
    so it is asserted, and the script refuses outright if one is found.
"""

import csv
import importlib.util
import re
import shutil
import sys
from collections import Counter
from datetime import date
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
csv.field_size_limit(min(sys.maxsize, 2 ** 31 - 1))

CEDAR = Path(__file__).resolve().parent.parent
CODE = CEDAR / "code"
CLEAN = CEDAR / "data" / "clean"
REVIEW = CEDAR / "review"
TODAY = date.today().isoformat()
SCRIPT = "310_correct_overstated_owned_by_edge_tiers.py"

REL = CLEAN / "entity_relationships.csv"
LEDGER = CLEAN / "cedar_identifier_ledger_final.csv"

sys.path.insert(0, str(CODE))
import cedar_domain as D                                    # noqa: E402


def _load_numbered(stem):
    spec = importlib.util.spec_from_file_location(
        "m_" + stem.split("_")[0], CODE / f"{stem}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


norm = _load_numbered("33_apply_party_rulings").norm

# Same map 97 writes. Declared here too because this script must be readable on
# its own, and asserted against 97's copy below so the two cannot drift.
TIER_CONFIDENCE = {"A": 0.90, "B": 0.60, "C": 0.40}
TIER_RANK = {"A": 0, "B": 1, "C": 2}

FIRM_RE = re.compile(r"firm '(?P<lbn>.*?)' \((?P<idt>UEI|CAGE|EIN|DUNS) "
                     r"(?P<ident>[^)]+)\)")


def read_csv(p):
    with open(p, encoding="utf-8-sig", errors="replace", newline="") as fh:
        return list(csv.DictReader(fh))


def header_of(p):
    with open(p, encoding="utf-8-sig", errors="replace", newline="") as fh:
        return next(csv.reader(fh), [])


def assert_no_drift():
    """97's map and this one must be the same object of thought."""
    src = (CODE / "97_build_aliases_and_relationships.py").read_text(
        encoding="utf-8", errors="replace")
    m = re.search(r"LEDGER_TIER_CONFIDENCE\s*=\s*\{([^}]*)\}", src)
    if not m:
        print("  !! 97 no longer declares LEDGER_TIER_CONFIDENCE. This script "
              "and the build would now write different confidences for the "
              "same tier. Reconcile them before running.")
        return False
    theirs = dict(re.findall(r'"([ABC])":\s*([0-9.]+)', m.group(1)))
    theirs = {k: float(v) for k, v in theirs.items()}
    if theirs != TIER_CONFIDENCE:
        print(f"  !! 97 declares {theirs} and this script declares "
              f"{TIER_CONFIDENCE}. Reconcile them before running.")
        return False
    print(f"  97's LEDGER_TIER_CONFIDENCE matches this script: "
          f"{TIER_CONFIDENCE}")
    return True


def ledger_index(ledger):
    """(entity, normalised legal name) -> best non-X tier, with its row."""
    idx = {}
    n_x = 0
    for r in ledger:
        tier = (r.get("confidence_tier") or "").strip().upper()
        eid = (r.get("tribe_id") or "").strip()
        lbn = " ".join((r.get("legal_business_name") or "").split())
        if not eid or not lbn:
            continue
        if tier == "X":
            n_x += 1
            continue                       # an exclusion is not an ownership
        if tier not in TIER_RANK:
            continue
        key = (eid, norm(lbn))
        cur = idx.get(key)
        if cur is None or TIER_RANK[tier] < TIER_RANK[cur[0]]:
            idx[key] = (tier, r)
    return idx, n_x


def ledger_by_identifier(ledger):
    """(entity, identifier) -> best non-X tier. The cross-check leg."""
    idx = {}
    for r in ledger:
        tier = (r.get("confidence_tier") or "").strip().upper()
        eid = (r.get("tribe_id") or "").strip()
        ident = (r.get("identifier") or "").strip()
        if not eid or not ident or tier not in TIER_RANK:
            continue
        key = (eid, ident)
        cur = idx.get(key)
        if cur is None or TIER_RANK[tier] < TIER_RANK[cur]:
            idx[key] = tier
    return idx


def main():
    apply = "--apply" in sys.argv
    print("=" * 78)
    print(f"310  OVER-STATED `owned_by` TIERS  -  "
          f"{'APPLY' if apply else 'DRY RUN'}")
    print("=" * 78)

    for p in (REL, LEDGER):
        if not p.exists():
            print(f"\nSTOP: {p} is absent. Nothing measured, nothing written.")
            return 1

    print(f"\n  owned_by is ownership-bearing: "
          f"{'owned_by' in D.OWNERSHIP_BEARING}")
    if "owned_by" not in D.OWNERSHIP_BEARING:
        print("  !! `owned_by` is no longer in cedar_domain.OWNERSHIP_BEARING. "
              "The premise of this correction has changed; read the domain "
              "module before continuing.")
        return 1
    if not assert_no_drift():
        return 1

    ledger = read_csv(LEDGER)
    rows = read_csv(REL)
    hdr = header_of(REL)
    print(f"\n  ledger rows                {len(ledger):,}")
    print(f"  entity_relationships rows  {len(rows):,}  "
          f"({len(hdr)} columns)")

    by_name, n_x = ledger_index(ledger)
    by_ident = ledger_by_identifier(ledger)
    print(f"  ledger tier-X rows skipped as exclusions   {n_x:,}")

    # What the NEXT run of 97 would have minted at A, re-derived here rather
    # than quoted from a document.
    exposure = Counter()
    for r in ledger:
        t = (r.get("confidence_tier") or "").strip().upper()
        if t in ("A", "X", ""):
            continue
        if not D.is_ruling((r.get("attribution_method") or "").strip()):
            continue
        if not (r.get("tribe_id") or "").strip():
            continue
        if not (r.get("legal_business_name") or "").strip():
            continue
        exposure[(t, (r.get("attribution_method") or "").strip())] += 1
    print(f"\n  LEDGER EXPOSURE - rows a `ruled method -> tier A` consumer "
          f"would\n  over-state today: {sum(exposure.values()):,}")
    for (t, m), n in exposure.most_common():
        print(f"     tier {t}  {m:<28} {n:>5,}")

    changed, unmatched, already_ok, refused = [], [], 0, []
    for r in rows:
        if r.get("relationship_type") != "owned_by":
            continue
        if r.get("source_id") != "cedar_identifier_ledger_final.csv":
            continue
        m = FIRM_RE.search(r.get("notes") or "")
        if not m:
            unmatched.append((r.get("relationship_id"), "no firm/identifier "
                                                        "in notes"))
            continue
        eid = (r.get("target_entity_id") or "").strip()
        key = (eid, norm(m.group("lbn")))
        hit = by_name.get(key)
        via = "legal_business_name"
        if hit is None:
            t2 = by_ident.get((eid, m.group("ident").strip()))
            if t2 is not None:
                hit, via = (t2, None), "identifier"
        if hit is None:
            unmatched.append((r.get("relationship_id"),
                              f"{m.group('idt')} {m.group('ident')} / "
                              f"'{m.group('lbn')}' -> {eid} has no non-X "
                              f"ledger row today"))
            continue
        correct = hit[0]
        cur = (r.get("tier") or "").strip().upper()
        if correct == cur:
            already_ok += 1
            continue
        if TIER_RANK.get(correct, 99) < TIER_RANK.get(cur, 99):
            # the ledger is STRONGER than the edge. Promotion is a rebuild's
            # job, never this script's.
            refused.append((r.get("relationship_id"), cur, correct))
            continue
        changed.append({
            "relationship_id": r.get("relationship_id"),
            "target_entity_id": eid,
            "identifier": f"{m.group('idt')} {m.group('ident')}",
            "legal_business_name": m.group("lbn"),
            "tier_was": cur, "tier_now": correct,
            "confidence_was": r.get("confidence"),
            "confidence_now": f"{TIER_CONFIDENCE[correct]:.2f}",
            "verification_status_was": r.get("verification_status"),
            "matched_via": via,
            "row": r,
        })

    print(f"\n  ledger-sourced owned_by edges examined      "
          f"{already_ok + len(changed) + len(refused) + len(unmatched):,}")
    print(f"  already correct                            {already_ok:,}")
    print(f"  OVER-STATED, to demote                     {len(changed):,}")
    print(f"  ledger is stronger - refused (no promotion){len(refused):>5,}")
    print(f"  source row not found today - LEFT ALONE    {len(unmatched):,}")

    if changed:
        print("\n  the rows this corrects:")
        for c in changed:
            print(f"     {c['relationship_id']}  {c['identifier']:<18} "
                  f"{c['target_entity_id']:<26} tier {c['tier_was']} -> "
                  f"{c['tier_now']}   ({c['legal_business_name'][:38]})")
    if refused:
        print("\n  REFUSED - the live edge is WEAKER than the ledger. A "
              "promotion is\n  a rebuild's job; re-run 97 in a quiet window "
              "if these matter:")
        for rid, cur, correct in refused[:20]:
            print(f"     {rid}  tier {cur} on the edge, {correct} in the "
                  f"ledger")
    if unmatched:
        print(f"\n  NOT MATCHED ({len(unmatched)}) - named, not counted away. "
              f"Each is an edge\n  whose ledger row has moved or gone; the "
              f"edge is UNCHANGED:")
        for rid, why in unmatched[:20]:
            print(f"     {rid}  {why}")
        if len(unmatched) > 20:
            print(f"     ... and {len(unmatched) - 20} more")

    audit = REVIEW / f"overstated_owned_by_tier_corrections_{TODAY}.csv"
    audit_rows = [{k: v for k, v in c.items() if k != "row"} for c in changed]

    if not apply:
        print("\n  DRY RUN - nothing written. Re-run with --apply.")
        return 0
    if not changed:
        print("\n  nothing to correct; the live file is already consistent "
              "with the ledger. NOTHING WRITTEN.")
        return 0

    bak = REL.with_name(REL.name + f".bak_{TODAY}_pre_{SCRIPT[:-3]}")
    shutil.copy2(REL, bak)
    print(f"\n  backup -> {bak.name}")

    for c in changed:
        r = c["row"]
        t = c["tier_now"]
        was_status = (r.get("verification_status") or "").strip()
        r["tier"] = t
        r["confidence"] = f"{TIER_CONFIDENCE[t]:.2f}"
        r["verification_status"] = ("RULED_TIER_" + t
                                    if was_status.startswith("RULED")
                                    else "TIER_" + t)
        r["notes"] = ((r.get("notes") or "").rstrip() +
                      f" | TIER CORRECTED {TODAY} by {SCRIPT}: the edge was "
                      f"minted at tier {c['tier_was']} on METHOD membership "
                      f"alone; the ledger row for this firm carries tier {t}, "
                      f"and a tier is INHERITED from the source row, never "
                      f"assigned by the consumer. Entity unchanged; matched "
                      f"on {c['matched_via']}.")

    part = REL.with_suffix(".csv.part")
    with open(part, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=hdr, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    part.replace(REL)

    apart = audit.with_suffix(".csv.part")
    with open(apart, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(audit_rows[0].keys()))
        w.writeheader()
        w.writerows(audit_rows)
    apart.replace(audit)

    # VERIFY BY RE-READING. Never by trusting the write (concurrency rule 4).
    back = read_csv(REL)
    hdr_back = header_of(REL)
    want = {c["relationship_id"]: c["tier_now"] for c in changed}
    got = {r["relationship_id"]: (r.get("tier") or "").strip()
           for r in back if r.get("relationship_id") in want}
    bad = {k: (v, got.get(k)) for k, v in want.items() if got.get(k) != v}
    print(f"\n  re-read: {len(back):,} rows (was {len(rows):,}), "
          f"{len(hdr_back)} columns (was {len(hdr)})")
    print(f"  re-read: {len(want) - len(bad)} of {len(want)} corrections "
          f"present on disk")
    if bad or len(back) != len(rows) or hdr_back != hdr:
        print(f"  !! VERIFICATION FAILED. bad={bad}. The backup is {bak.name}.")
        return 1
    n_a = sum(1 for r in back if r.get("relationship_type") == "owned_by"
              and (r.get("tier") or "").strip() == "A")
    n_ob = sum(1 for r in back if r.get("relationship_type") == "owned_by")
    print(f"  owned_by edges now: {n_ob:,} total, {n_a:,} at tier A "
          f"({n_ob - n_a:,} below A)")
    print(f"  audit -> {audit.relative_to(CEDAR)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
