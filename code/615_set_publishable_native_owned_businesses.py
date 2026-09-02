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

2. PRIVACY - and the owner CORRECTED an over-withholding here on 2026-09-01.

   The first version of this script withheld 521 rows because
   `business_name_is_person_name` was 1 or undecidable - "Jane Doe
   Construction" was treated as publishing Jane Doe. That was wrong, and the
   owner said so:

       "If a site is publicly accessible, it is part of the public domain and
        therefore we can incorporate it. So if they have their names or
        whatever, that's fine. It's not PII, it's not Social Security numbers.
        But the firm is named after the owner - it's the name of the firm, and
        of course we're going to include that."

   He is right. **A firm's legal name is the firm's name.** A business listed
   on a tribe's public vendor directory has been published by that tribe as a
   business, and the certifying authority chose to list it. Suppressing the
   business name would make the row useless while protecting nobody - the name
   is already public, on the tribe's own site, precisely so people can hire
   them.

   The distinction that survives is NOT name-shaped-ness. It is: does the
   column describe the FIRM, or a PERSON separate from the firm?

     FIRM      legal name, DBA, city, state, NAICS, certification number,
               licence number, identity_scope  ->  publish
     PERSON    a home address, a personal email or phone, an owner's date of
               birth, an SSN or TIN, anything a person holds apart from the
               business  ->  never, and none of it is in this table anyway

   The clean table was verified before this ran: it carries no
   `owner_name_raw`, email, phone or street-address column at all.
   `owner_name_present` and `n_owners_named` are counts. So there is nothing
   left in it that the privacy gate needs to catch, and the gate is retired.

   `business_name_is_person_name` is KEPT as a column. It is no longer a
   suppression trigger, but it is a real property of the row and a downstream
   consumer may want it.

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
    """(publishable, reason).

    ONE gate: permission. The privacy gate was retired 2026-09-01 - see the
    module docstring. A firm's legal name is the firm's name, and no
    person-scoped column exists in this table to withhold.
    """
    terms = (r.get("source_terms_status") or "").strip()
    if terms not in PERMISSION_OK:
        return "N", f"PERMISSION:{terms or 'UNKNOWN'}"
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
