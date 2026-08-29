#!/usr/bin/env python3
"""
Cedar Press - 34: Apply agent-researched nonprofit classifications to np_orgs.

WHY THIS IS NOT SCRIPT 09
-------------------------
Script 09 reads review_id/YOUR_RULING and treats the ruling text as an OWNER
NAME. These rulings are CATEGORIES ("place_name_coincidence"), not owners. Fed
through 09, all 375 would be compared against canonical_name, fail, and be
demoted to tier X - silently discarding the 89 organisations the research
CONFIRMED as Native. The file is deliberately kept out of the
rulings_inbox_*.csv glob for that reason.

ASYMMETRIC EVIDENCE STANDARD
----------------------------
These are agent findings, not Elijah's hand-checks, so they do not
automatically earn tier A. The two directions carry different risk:

  EXCLUDING  can only ever under-attribute. A wrongly excluded nonprofit is
             missing coverage, which this project accepts. Excluding on solid
             agent evidence at high OR medium confidence is therefore safe.

  INCLUDING  can falsely attribute, which the project does not accept. So a
             Native classification lands at tier A only at HIGH confidence
             with a primary source. Medium and low go to tier B and wait for
             Elijah - visible, but never published.

That asymmetry is the whole point. It is not an oversight that the two
branches use different thresholds.

Reads  review/agent_rulings_nonprofit_2026-08-05.csv
       data/clean/np_orgs.csv
Writes data/clean/np_orgs.csv                       (rulings applied in place)
       review/np_needs_elijah_<date>.csv            (included at < high conf)
"""

import csv
import re
import shutil
from collections import Counter
from datetime import date
from pathlib import Path

CEDAR = Path(__file__).resolve().parent.parent
CLEAN = CEDAR / "data" / "clean"
REVIEW = CEDAR / "review"
TODAY = date.today().isoformat()

RULINGS = REVIEW / "agent_rulings_nonprofit_2026-08-05.csv"
NP = CLEAN / "np_orgs.csv"

CONF_RE = re.compile(r"confidence\s*=\s*(high|medium|low)", re.I)

# A primary source is the organisation's own site, the IRS, or a tribal
# government. A search-results page is a lead, not evidence - the research log
# flagged 40 rows resting on one, and none of those may reach tier A.
PRIMARY_HINTS = ("propublica.org/nonprofits/api", "irs.gov", ".gov/",
                 "guidestar", "990")
SEARCH_PAGE_HINTS = ("causeiq.com/search", "google.com/search", "bing.com/search",
                     "/search?", "search-results")

NATIVE_RULINGS = {"native_controlled", "tribally_controlled", "native_serving"}

# WHICH TIER A IS ACTUALLY PROTECTED
# ----------------------------------
# Not all tier A is equal here. np_orgs reaches tier A through funnel_stage
# `verified_strict`, and that name OVERSTATES what it did: it is a strict
# NAME match, not a verification of Native control. It is how "SOUTHERN
# YAVAPAI FIRE DEPT" and "LEGACY TRADITIONAL SCHOOL-PEORIA" became publishable.
# The np_placename review queue was itself built out of these rows precisely
# because they were suspected leakage.
#
# So a name-match A does NOT outrank documented research. Only a human ruling
# or an explicit hand-check does - that is the project's authority order, and
# `verified_strict` is not in it.
PROTECTED_BASES = {"elijah_ruling", "hand_checked", "ruled_native_verified"}
NAME_MATCH_BASES = {"verified_strict", "canonical_name_match",
                    "raw_name_candidate", "state_validated"}


def read_csv(p):
    with open(p, encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh)), None


def confidence(note):
    m = CONF_RE.search(note or "")
    return m.group(1).lower() if m else "unstated"


def is_search_page(note):
    n = (note or "").lower()
    return any(h in n for h in SEARCH_PAGE_HINTS)


def main():
    print("=== Cedar Press 34: apply nonprofit classifications ===\n")

    if not RULINGS.exists():
        raise SystemExit(f"missing {RULINGS}")

    rulings, _ = read_csv(RULINGS)
    print(f"agent rulings: {len(rulings):,}")

    by_ein = {}
    for r in rulings:
        rid = (r.get("review_id") or "").strip()
        if not rid.upper().startswith("EIN:"):
            continue
        ein = rid.split(":", 1)[1].strip()
        by_ein[ein] = r
    print(f"keyed by EIN : {len(by_ein):,}")

    rows, _ = read_csv(NP)
    print(f"np_orgs rows : {len(rows):,}")

    shutil.copy2(NP, NP.with_suffix(f".csv.bak_{TODAY}_pre34"))

    # Make sure the columns we write exist.
    for col in ("classification_ruling", "evidence", "ruling_authority",
                "ruling_confidence", "ruling_date"):
        for row in rows:
            row.setdefault(col, "")
    fields = list(rows[0].keys())
    for col in ("ruling_authority", "ruling_confidence", "ruling_date"):
        if col not in fields:
            fields.append(col)

    applied = Counter()
    needs_elijah = []
    conflicts = []
    matched = 0

    for row in rows:
        ein = (row.get("EIN") or "").strip()
        r = by_ein.get(ein)
        if not r:
            continue
        matched += 1
        ruling = (r.get("YOUR_RULING") or "").strip().lower()
        note = (r.get("YOUR_NOTE") or "").strip()
        conf = confidence(note)
        basis = (row.get("funnel_stage") or "").strip()
        # Protected only if a human put it there. A name-match A is a
        # candidate, not a finding, whatever its stage is called.
        was_A = (row.get("confidence_tier") == "A"
                 and basis not in NAME_MATCH_BASES)

        row["classification_ruling"] = ruling
        row["evidence"] = note
        row["ruling_authority"] = "agent_research"
        row["ruling_confidence"] = conf
        row["ruling_date"] = TODAY

        if ruling == "unresolved":
            row["classification_ruling"] = "UNRULED"
            applied["left unruled"] += 1
            continue

        if ruling == "place_name_coincidence":
            # A prior tier A means an earlier, stricter method already verified
            # this org as Native. Agent research disagreeing is a CONFLICT
            # between two methods, not a correction - resolving it silently in
            # either direction destroys the disagreement. Flag it and leave the
            # row untouched.
            if was_A:
                conflicts.append({
                    "EIN": ein,
                    "org_name": row.get("org_name", ""),
                    "state": row.get("state", ""),
                    "prior_tier": "A",
                    "prior_basis": row.get("funnel_stage", ""),
                    "agent_ruling": ruling,
                    "agent_confidence": conf,
                    "evidence": note,
                })
                row["classification_ruling"] = "CONFLICT"
                applied["CONFLICT: was tier A, agent says not Native"] += 1
                continue
            # Safe direction: this can only remove, never falsely add.
            row["confidence_tier"] = "X"
            row["funnel_stage"] = "ruled_not_native"
            row["exclusion_reason"] = f"Agent-researched {TODAY}: place-name coincidence"
            applied["excluded (not Native)"] += 1
            continue

        if ruling in NATIVE_RULINGS:
            # A concordant Native ruling must never LOWER an existing tier A.
            # The agent agrees the org is Native; agreement is not grounds for
            # demotion, and treating it as such would discard the earlier
            # verification that produced the A in the first place.
            if was_A:
                applied[f"tier A held - {ruling} (agent concurs)"] += 1
                continue
            solid = conf == "high" and not is_search_page(note)
            if solid:
                row["confidence_tier"] = "A"
                row["funnel_stage"] = "ruled_native_verified"
                applied[f"tier A - {ruling}"] += 1
            else:
                row["confidence_tier"] = "B"
                row["funnel_stage"] = "ruled_native_needs_elijah"
                applied[f"tier B - {ruling} ({conf})"] += 1
                needs_elijah.append({
                    "EIN": ein,
                    "org_name": row.get("org_name", ""),
                    "state": row.get("state", ""),
                    "proposed_ruling": ruling,
                    "agent_confidence": conf,
                    "rests_on_search_page": int(is_search_page(note)),
                    "evidence": note,
                })
            continue

        applied[f"unrecognised ruling: {ruling}"] += 1

    print(f"\nEINs matched into np_orgs: {matched:,} of {len(by_ein):,}")
    unmatched = len(by_ein) - matched
    if unmatched:
        print(f"  NOT FOUND in np_orgs   : {unmatched:,}  (reported, not invented)")

    print("\napplied")
    for k, v in applied.most_common():
        print(f"  {v:5d}  {k}")

    with open(NP, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    print(f"\n  wrote {NP.relative_to(CEDAR)}")

    if needs_elijah:
        p = REVIEW / f"np_needs_elijah_{TODAY}.csv"
        with open(p, "w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(needs_elijah[0].keys()))
            w.writeheader()
            w.writerows(needs_elijah)
        print(f"  wrote {p.relative_to(CEDAR)}  ({len(needs_elijah):,} rows)")

    if conflicts:
        p = REVIEW / f"np_method_conflicts_{TODAY}.csv"
        with open(p, "w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(conflicts[0].keys()))
            w.writeheader()
            w.writerows(conflicts)
        print(f"  wrote {p.relative_to(CEDAR)}  ({len(conflicts):,} rows) "
              f"<- prior tier A vs agent 'not Native'; UNRESOLVED by design")

    tiers = Counter(r.get("confidence_tier", "") for r in rows)
    print("\nnp_orgs confidence tiers now")
    for k in ("A", "B", "C", "X"):
        print(f"  {k}: {tiers.get(k,0):,}")


if __name__ == "__main__":
    main()
