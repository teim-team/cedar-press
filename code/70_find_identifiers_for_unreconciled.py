#!/usr/bin/env python3
"""
Cedar Press - 70: Find identifiers for the entities that link to nothing.

ELIJAH, 2026-08-06
------------------
"most orgs or entities likely have a grant or direct spending or like would
 show up in lobbying or native deals its unlikely that they dont show up
 somewhere but they may not have a contract or grant"

That reframes the search. Every prior sweep looked at CONTRACTING, which is the
one place a small tribe or an intertribal council is least likely to appear.
This looks everywhere, and it looks under the FULL OFFICIAL NAME rather than
the spine's short one - because "Sleetmute" is filed federally as "Village of
Sleetmute" and was never going to match.

He also asked, reasonably: "i assume when you mean federal activity you mean
contracts, direct spending, loans or grants? in which case virtually all native
entities should have some." Yes - and that is the premise. An entity with
nothing anywhere is the exception worth investigating, not the rule.

WHERE IT LOOKS, cheapest and most reliable first
------------------------------------------------
    federal funding   recipient_name + recipient_uei   grants, direct payments
    FAADS             recipient_name                    older assistance
    subawards         subawardee + prime names          pass-through money
    lobbying          client_name                        no award needed at all
    deals             Native_Party                       press and filings
    nonprofits        org_name + EIN                     990 filers
    contracting       awardee_name + UEI/CAGE            least likely for these

WHAT IT PRODUCES - CANDIDATES, NEVER ATTRIBUTIONS
-------------------------------------------------
A name appearing in a dataset is evidence that an identifier EXISTS, not proof
it belongs to this entity. Everything here lands in a review file with the
matched string, the dataset, and the identifier found, for ruling.

The traps that have already cost real money on this project all apply and are
enforced: village corporation is not village government; an organisation type
(city, county, mining company, power district, cooperative, university) bars a
match outright; and the name-trap tokens must never carry a match alone.

Writes review/identifier_candidates_for_unreconciled.csv
"""

import csv
import glob
import importlib.util
import re
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

CEDAR = Path(__file__).resolve().parent.parent
CLEAN = CEDAR / "data" / "clean"
SPINE_P = CEDAR / "data" / "spine" / "cedar_entity_spine.csv"
REVIEW = CEDAR / "review"
TODAY = date.today().isoformat()

# An organisation of these forms cannot be a Native entity. Same guard that
# withdrew $39.43M of lobbying attribution.
BARRED = re.compile(
    r"^\s*(city|town|county|state) of\b|\bmines?\b|\b(power|irrigation|water|"
    r"utility|electric)\s+district\b|\bcooperative\b|\bschool district\b|"
    r"\bchamber of commerce\b|\buniversity\b", re.I)

# Tokens that must never carry a match on their own.
TRAPS = {"creek", "cherokee", "colorado", "ojibwe", "shawnee", "oneida",
         "apache", "santa", "san", "river", "salt", "round", "united",
         "enterprise", "mountain", "valley", "lake"}

SOURCES = [
    ("federal_funding", "federal_funding_transactions.csv",
     "recipient_name", ["recipient_uei"]),
    ("faads", "faads_transactions_all_agencies.csv",
     "recipient_name", []),
    ("subawards", "subawards.csv", "subawardee_name", ["sub_uei", "sub_cage"]),
    ("subawards_prime", "subawards.csv", "prime_awardee_name",
     ["prime_uei", "prime_cage"]),
    ("lobbying", "native_entity_lobbying_disclosures.csv", "client_name", []),
    ("nonprofits", "np_orgs.csv", "org_name", ["EIN"]),
    ("contracting", "prime_contracts.csv", "awardee_name",
     ["awardee_uei", "cage_code"]),
]


def load_m33():
    spec = importlib.util.spec_from_file_location(
        "m33", CEDAR / "code" / "33_apply_party_rulings.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def read_csv(p):
    if not Path(p).exists():
        return []
    with open(p, encoding="utf-8-sig", errors="replace", newline="") as fh:
        return list(csv.DictReader(fh))


def main():
    print("=== Cedar Press 70: identifier discovery ===\n")
    m = load_m33()
    spine = read_csv(SPINE_P)
    targets = read_csv(REVIEW / "unreconciled_entities.csv")
    by_id = {r["tribe_id"]: r for r in spine}
    print(f"entities to find: {len(targets):,}")

    # Search keys: the short name, the FULL FR official name, and every alias.
    # The official name is the one federal systems actually carry.
    keys = {}
    for t in targets:
        row = by_id.get(t["tribe_id"], {})
        names = [t["canonical_name"], row.get("fr_official_name", "")]
        names += [a.strip() for a in (row.get("aliases") or "").split("|")]
        cores = {}
        for nm in names:
            if not nm:
                continue
            c = m.core(nm)
            # A single-token core made only of trap words is not searchable.
            if not c or (len(c) == 1 and next(iter(c)) in TRAPS):
                continue
            cores[frozenset(c)] = nm
        if cores:
            keys[t["tribe_id"]] = (t["canonical_name"], cores)
    print(f"  searchable (after dropping trap-only names): {len(keys):,}\n")

    hits = defaultdict(list)
    for label, fname, namecol, idcols in SOURCES:
        paths = sorted(glob.glob(str(CLEAN / fname)))
        if not paths:
            print(f"  {label:18s} no file")
            continue
        seen_names = {}
        n = 0
        for p in paths:
            for r in read_csv(p):
                nm = (r.get(namecol) or "").strip()
                if not nm or BARRED.search(nm):
                    continue
                n += 1
                if nm in seen_names:
                    continue
                seen_names[nm] = {c: (r.get(c) or "").strip() for c in idcols}
        print(f"  {label:18s} {len(seen_names):>8,} distinct names "
              f"of {n:,} rows")

        # Match on core-set containment: the entity's core must sit inside the
        # dataset name's core. Exact-equal cores are the strongest signal.
        name_cores = {nm: m.core(nm) for nm in seen_names}
        for tid, (canon, cores) in keys.items():
            for ecore, ename in cores.items():
                for nm, ncore in name_cores.items():
                    if not ncore:
                        continue
                    if ecore == ncore:
                        strength = "core_exact"
                    elif ecore <= ncore and len(ecore) >= 2:
                        strength = "core_contained"
                    else:
                        continue
                    ids = seen_names[nm]
                    if not any(ids.values()) and label not in ("lobbying", "faads"):
                        continue
                    hits[tid].append({
                        "tribe_id": tid, "entity": canon,
                        "matched_via": ename, "dataset": label,
                        "matched_name": nm, "strength": strength,
                        **{k: v for k, v in ids.items()},
                    })
                    break

    rows = []
    for tid, hs in hits.items():
        best = sorted(hs, key=lambda h: (h["strength"] != "core_exact",
                                         h["dataset"]))
        for h in best[:6]:
            rows.append({**h, "YOUR_RULING": "", "found": TODAY,
                         "note": "CANDIDATE - a name match is evidence an "
                                 "identifier exists, not proof it is this "
                                 "entity's."})

    p = REVIEW / "identifier_candidates_for_unreconciled.csv"
    cols = ["tribe_id", "entity", "matched_via", "dataset", "matched_name",
            "strength", "recipient_uei", "sub_uei", "sub_cage", "prime_uei",
            "prime_cage", "awardee_uei", "cage_code", "EIN",
            "YOUR_RULING", "note", "found"]
    with open(p, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)

    print(f"\n  entities with at least one candidate: {len(hits):,} "
          f"of {len(targets):,}")
    print(f"  candidate rows: {len(rows):,}")
    print(f"  wrote {p.relative_to(CEDAR)}")

    ds = Counter(h["dataset"] for hs in hits.values() for h in hs)
    print("\n  where they were found:")
    for k, v in ds.most_common():
        print(f"     {v:6,}  {k}")

    still = [t for t in targets if t["tribe_id"] not in hits]
    print(f"\n  still nothing anywhere: {len(still):,}")
    for t in still[:10]:
        print(f"     {t['canonical_name'][:48]:48s} {t['entity_class'][:30]}")


if __name__ == "__main__":
    main()
