#!/usr/bin/env python3
"""
Cedar Press - 03: Apply the exclusion jurisprudence and finalise confidence tiers.

Two jobs:

1. SAFETY. Any identifier Elijah has ruled non-tribal is stamped tier X and
   can never be published, no matter what any automated source claims. If an
   automated pull re-attributed a UEI he already excluded, that is a caught
   false attribution and it gets reported loudly.

2. AUTHORITY. Hand-checked sources outrank automated ones. Per Elijah
   (2026-08-05): the Federal Spending folder, the BGOV crosswalk, and the
   ESM/HCI Winnebago work are hand-checked and are the reference standard.
   An automated attribution that CONFLICTS with a hand-checked one loses.

Outputs
-------
data/clean/cedar_identifier_ledger_tiered.csv   ledger + tier X + authority flags
data/clean/cedar_publishable_identifiers.csv    tier A only, exclusion-clean
review/conflicts_<date>.csv                     disagreements needing a ruling
"""

import csv
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

CEDAR = Path(__file__).resolve().parent.parent
SPINE = CEDAR / "data" / "spine"
CLEAN = CEDAR / "data" / "clean"
REVIEW = CEDAR / "review"
TODAY = date.today().isoformat()

# Sources Elijah hand-checked. These are the reference standard.
AUTHORITY_METHODS = {"hand", "web_verified", "bgov_manual", "subsidiary_lookup"}
AUTHORITY_FILES = {"entity_crosswalk_bgov.csv"}


# --- REGENERATE GUARD (ADR-017, 2026-09-02) --------------------------------
def _carry_live_columns(path, canonical):
    """Derive this writer's header instead of declaring it.

    A wholesale writer holding a FIXED `fieldnames` list deletes every column
    an in-place enricher added since - no error, no exception, a diff nobody
    reads. Canonical order first so column order stays stable, then whatever
    the live file already carries. A retired column stays retired because it
    is not on disk; a promoted column survives because it is.

    THIS BUILD CANNOT REPOPULATE AN ENRICHER'S COLUMN. Carried columns are
    written BLANK and NAMED on stdout, which is strictly better than deleted:
    the schema survives and the enricher can refill them. Re-run the enricher
    after this build - `cedar_pipeline.enrichers_to_rerun(<table>)` names it.
    """
    import csv as _csv
    import os as _os
    canonical = list(canonical)
    _p = str(path)
    if not _os.path.exists(_p):
        return canonical
    with open(_p, encoding="utf-8-sig", newline="", errors="replace") as _fh:
        _live = next(_csv.reader(_fh), [])
    _extra = [c for c in _live if c and c not in canonical]
    if _extra:
        print("  [regenerate guard] %s: carrying %d enricher column(s) through "
              "this rebuild, BLANK - re-run the enricher: %s"
              % (_os.path.basename(_p), len(_extra), ", ".join(_extra)))
    return canonical + _extra


def read_csv(p):
    with open(p, encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def write_csv(p, rows, fields):
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    print(f"  wrote {p.relative_to(CEDAR)}  ({len(rows):,} rows)")


def main():
    print("=== Cedar Press: apply exclusions + finalise tiers ===\n")

    ledger = read_csv(SPINE / "cedar_identifier_ledger.csv")
    excl = read_csv(SPINE / "cedar_exclusion_rulings.csv")
    print(f"ledger links      : {len(ledger):,}")
    print(f"exclusion rulings : {len(excl):,}\n")

    excl_idx = {(r["identifier_type"], r["identifier"].upper()): r for r in excl}

    # ---- 1. apply exclusions ---------------------------------------------
    print("[1] Applying exclusion jurisprudence")
    caught = []
    for row in ledger:
        key = (row["identifier_type"], row["identifier"].upper())
        hit = excl_idx.get(key)
        row["is_authority"] = ("YES" if row["attribution_method"] in AUTHORITY_METHODS
                               or row["source_file"] in AUTHORITY_FILES else "")
        if hit:
            prior = row["confidence_tier"]
            row["confidence_tier"] = "X"
            row["tier_rationale"] = (f"EXCLUDED by ruling {hit['exclusion_id']}: "
                                     f"{hit['exclusion_reason']}")
            row["exclusion_id"] = hit["exclusion_id"]
            row["exclusion_evidence"] = hit["evidence_url"] or hit["ruling_note"]
            # A previously-attributed link that is actually excluded = a caught
            # false attribution. This is the whole point of the exercise.
            if prior in ("A", "B"):
                caught.append({
                    "identifier_type": row["identifier_type"],
                    "identifier": row["identifier"],
                    "legal_business_name": row["legal_business_name"],
                    "wrongly_attributed_to": row["canonical_name"],
                    "prior_tier": prior,
                    "attribution_method": row["attribution_method"],
                    "exclusion_id": hit["exclusion_id"],
                    "exclusion_reason": hit["exclusion_reason"],
                    "evidence_url": hit["evidence_url"],
                    "prime_dollars_M": row["prime_dollars_M"],
                })
        else:
            row.setdefault("exclusion_id", "")
            row.setdefault("exclusion_evidence", "")

    print(f"  links stamped tier X (excluded) : "
          f"{sum(1 for r in ledger if r['confidence_tier']=='X'):,}")
    print(f"  FALSE ATTRIBUTIONS CAUGHT       : {len(caught):,}")

    # ---- 2. authority conflicts ------------------------------------------
    print("\n[2] Checking automated attributions against hand-checked authority")
    by_id = defaultdict(list)
    for r in ledger:
        if r["confidence_tier"] == "X":
            continue
        by_id[(r["identifier_type"], r["identifier"].upper())].append(r)

    conflicts = []
    for key, rows in by_id.items():
        if len(rows) < 2:
            continue
        auth = [r for r in rows if r["is_authority"] == "YES"]
        auto = [r for r in rows if r["is_authority"] != "YES"]
        if not auth or not auto:
            continue
        auth_names = {r["canonical_name"].strip().lower() for r in auth if r["canonical_name"].strip()}
        for r in auto:
            nm = r["canonical_name"].strip().lower()
            if nm and auth_names and nm not in auth_names:
                # Hand-checked wins. Demote the automated claim.
                r["confidence_tier"] = "B"
                r["tier_rationale"] = ("Conflicts with hand-checked attribution - "
                                       "demoted pending ruling")
                conflicts.append({
                    "identifier_type": key[0],
                    "identifier": key[1],
                    "legal_business_name": r["legal_business_name"],
                    "authority_says": " | ".join(sorted({a["canonical_name"] for a in auth})),
                    "authority_method": " | ".join(sorted({a["attribution_method"] for a in auth})),
                    "automated_says": r["canonical_name"],
                    "automated_method": r["attribution_method"],
                    "prime_dollars_M": r["prime_dollars_M"],
                    "question": (f"Hand-checked work says {list(auth_names)[0]}; "
                                 f"{r['attribution_method']} says {r['canonical_name']}. Which is right?"),
                    "YOUR_RULING": "",
                })
    print(f"  authority-vs-automated conflicts : {len(conflicts):,}")

    # ---- 3. write outputs -------------------------------------------------
    print("\n[3] Writing outputs")
    LEDGER_CANONICAL = ["identifier_type", "identifier", "tribe_id",
                        "canonical_name", "legal_business_name",
                        "entity_class", "attribution_method",
                        "confidence_tier", "tier_rationale", "is_authority",
                        "exclusion_id", "exclusion_evidence", "evidence_url",
                        "verified_date", "state", "prime_dollars_M",
                        "source_file"]
    tiered_p = CLEAN / "cedar_identifier_ledger_tiered.csv"
    write_csv(tiered_p, ledger, _carry_live_columns(tiered_p, LEDGER_CANONICAL))

    publishable = [r for r in ledger if r["confidence_tier"] == "A"]
    pub_p = CLEAN / "cedar_publishable_identifiers.csv"
    write_csv(pub_p, publishable, _carry_live_columns(pub_p, LEDGER_CANONICAL))

    if caught:
        write_csv(REVIEW / f"false_attributions_caught_{TODAY}.csv", caught,
                  ["identifier_type", "identifier", "legal_business_name",
                   "wrongly_attributed_to", "prior_tier", "attribution_method",
                   "exclusion_id", "exclusion_reason", "evidence_url", "prime_dollars_M"])
    if conflicts:
        write_csv(REVIEW / f"conflicts_{TODAY}.csv", conflicts,
                  ["identifier_type", "identifier", "legal_business_name",
                   "authority_says", "authority_method", "automated_says",
                   "automated_method", "prime_dollars_M", "question", "YOUR_RULING"])

    # ---- summary ----------------------------------------------------------
    tiers = Counter(r["confidence_tier"] for r in ledger)
    print("\n=== FINAL TIERS ===")
    labels = {"A": "publishable now", "B": "needs your ruling",
              "C": "unattributed / discovery", "X": "EXCLUDED - never publish"}
    for t in ("A", "B", "C", "X"):
        print(f"  tier {t}  {tiers[t]:>6,}   {labels[t]}")
    auth_n = sum(1 for r in ledger if r["is_authority"] == "YES")
    print(f"\n  hand-checked (authority) links : {auth_n:,}")
    print(f"  publishable identifiers        : {len(publishable):,}")


if __name__ == "__main__":
    main()
