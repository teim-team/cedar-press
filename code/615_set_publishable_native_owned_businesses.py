#!/usr/bin/env python3
"""
Cedar Press - 615: RESOLVE `publishable` ON native_owned_businesses.csv.

    py -3 code/615_set_publishable_native_owned_businesses.py            # report
    py -3 code/615_set_publishable_native_owned_businesses.py --apply
    py -3 code/615_set_publishable_native_owned_businesses.py verify

WHY
---
All 2,393 rows shipped with `publishable = N` and `consent_status = UNRESOLVED`
because nobody had decided the question. The owner decided it on 2026-09-01:

    "It's not like we just are taking a tribe dataset of their vendors and just
     putting it on our website. We're making it all cohesive and harmonized
     into one dataset per category... To the extent where we said we'll
     acknowledge you because you shared this data, we'll do that."

See `docs/PUBLICATION_POLICY.md`. The product is the harmonized dataset - 2,393
rows from 18 certifying authorities under one schema, with `identity_scope`
preserved so `enrolled_member_100pct` and `shareholder_descendant_or_spouse`
stay distinguishable. That is not a redistribution of anyone's page.

TWO INDEPENDENT GATES, AND A ROW MUST CLEAR BOTH
------------------------------------------------
Conflating them is how this would go wrong, so they are computed separately.

1. PERMISSION - a property of the SOURCE.
   `TERMS_STATED_RESTRICTIVE` (346 rows, Navajo NBOA) stays N. Harmonizing
   changes what we publish, not what we were allowed to take, and a harmonized
   derivative of refused data is still refused data. `SILENT` (1,998) and
   `TERMS_STATED_NO_REUSE_RESTRICTION` (49) clear this gate.

2. PRIVACY - a property of the ROW, and it does NOT track the source.
   `business_name_is_person_name = 1` (280 rows) means the firm's legal name IS
   a natural person's name. Publishing "Jane Doe Construction" publishes Jane
   Doe. Cedar's standing rule is that a natural person is never published and a
   firm whose legal name is a person's gets a privacy surrogate. Those stay N
   until a surrogate exists - the row is not lost, it is withheld.
   `= -1` (327) is UNDECIDABLE, and undecided means withheld. Silence is not
   consent and a maybe is not a yes.

The clean table was already sanitized before this ran and that was verified:
no `owner_name_raw`, email, phone, or street address column exists in it.
`owner_name_present` and `n_owners_named` are counts; `withheld_fields` names
per row what stayed in staging.

WHAT THIS DOES NOT DO
---------------------
It does not touch `consent_status`. Consent is a statement by the source about
Cedar's use, and no source has made one. `publishable` records OUR decision
under a stated policy; `consent_status` records THEIRS. A project that
overwrote the second with the first would be recording a permission nobody
gave, which is precisely the failure this dataset is most exposed to.
"""
from __future__ import annotations

import csv
import shutil
import sys
from collections import Counter
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
csv.field_size_limit(10_000_000)
TODAY = date.today().isoformat()
T = ROOT / "data" / "clean" / "native_owned_businesses.csv"

PERMISSION_OK = {"SILENT", "TERMS_STATED_NO_REUSE_RESTRICTION"}


def decide(r: dict) -> tuple:
    """(publishable, reason). Both gates, permission first."""
    terms = (r.get("source_terms_status") or "").strip()
    if terms not in PERMISSION_OK:
        return "N", f"PERMISSION:{terms or 'UNKNOWN'}"
    pn = (r.get("business_name_is_person_name") or "").strip()
    if pn == "1":
        return "N", "PRIVACY:legal_name_is_a_natural_person_needs_surrogate"
    if pn != "0":
        return "N", f"PRIVACY:person_name_undecidable({pn or 'blank'})"
    return "Y", "harmonized_publication_per_PUBLICATION_POLICY"


def main() -> int:
    apply = "--apply" in sys.argv
    verify = "verify" in sys.argv

    with T.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
        rd = csv.DictReader(fh)
        cols = list(rd.fieldnames or [])
        rows = list(rd)

    tally = Counter()
    for r in rows:
        p, why = decide(r)
        tally[(p, why.split(":")[0])] += 1
        r["_p"], r["_why"] = p, why

    y = sum(n for (p, _), n in tally.items() if p == "Y")
    print(f"  615 publishable  {len(rows):,} rows -> "
          f"{y:,} publishable, {len(rows) - y:,} withheld")
    for (p, cls), n in sorted(tally.items(), key=lambda kv: -kv[1]):
        print(f"    {p}  {cls:<12} {n:,}")

    # by source, so the acknowledgments section can be written from this
    bysrc = Counter()
    for r in rows:
        if r["_p"] == "Y":
            bysrc[r.get("certifying_authority_name") or r.get("source_id")] += 1
    print(f"    publishable authorities: {len(bysrc)}")

    if verify:
        bad = [r for r in rows
               if (r.get("publishable") or "") != r["_p"]]
        return 1 if bad else 0
    if not apply:
        print("    (report only - pass --apply)")
        return 0

    shutil.copy2(T, T.with_name(T.name + f".bak_{TODAY}_pre615"))
    if "publishable_basis" not in cols:
        cols.append("publishable_basis")
    for r in rows:
        r["publishable"] = r["_p"]
        r["publishable_basis"] = r["_why"]
        r.pop("_p", None)
        r.pop("_why", None)
    with T.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)
    print(f"    APPLIED. consent_status untouched - it records the SOURCE's "
          f"statement, not ours.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
