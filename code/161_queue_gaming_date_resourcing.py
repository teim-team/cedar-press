#!/usr/bin/env python3
r"""Cedar Press 161 - queue the opening dates that still need an independent source.

`code/158` withdrew fabricated day precision. It did NOT make those dates
publishable, and the distinction matters:

  * 415 values were re-typed to the precision their own `*_precision` column
    asserts. They are now HONEST.
  * 298 of the 304 placeholder-shaped ones came from the **Casino City** vendor
    roster, which by standing rule may be read for QA and never published. An
    honest year is still a vendor year.

So this file separates two queues that look the same in a coverage table:

  NEEDS_INDEPENDENT_SOURCE  the date is correct as far as we know and rests on
                            a licensed vendor. It cannot ship until a free
                            source states it.
  SUSPECT_PLACEHOLDER_DAY   the value is typed `day` precision and lands on
                            1 January - the one placeholder shape the 2026-08-06
                            precision derivation did not catch, because it
                            looked for -12-31 and -MM-15. Eight rows. Not
                            downgraded here: 1 January is a real date and there
                            is no evidence either way. It needs a human ruling,
                            not a rule.

Writes review/gaming_open_date_resourcing_2026-08-26.csv
"""

import csv
import importlib.util
import sys
from collections import Counter
from datetime import date
from pathlib import Path

CEDAR = Path(__file__).resolve().parent.parent
TODAY = date.today().isoformat()
csv.field_size_limit(min(sys.maxsize, 2**31 - 1))

spec = importlib.util.spec_from_file_location(
    "m157", str(CEDAR / "code" / "157_reconcile_nigc_roster.py"))
M = importlib.util.module_from_spec(spec)
spec.loader.exec_module(M)

VENDOR = "Casino City Tribal Property List"


def main():
    fac = M.read_csv(CEDAR / "data" / "clean" / "gaming_facilities.csv")
    rows, counts = [], Counter()
    for f in fac:
        v, basis = f.get("open_date", ""), f.get("open_date_basis", "")
        if not v:
            continue
        vendor_only = VENDOR in basis and not f.get("open_date_source_url")
        if len(v) == 10 and f.get("open_date_precision") == "day" \
                and v.endswith("-01-01") and VENDOR in basis:
            kind = "SUSPECT_PLACEHOLDER_DAY"
            q = ("This value is typed day precision and lands on 1 January, "
                 "which is also how a year placeholder looks. The 2026-08-06 "
                 "precision derivation looked for YYYY-12-31 and YYYY-MM-15 "
                 "only. Is 1 January the stated opening, or the vendor's other "
                 "year placeholder? NOT downgraded on inference.")
        elif f.get("open_date_source_value_verbatim") and vendor_only:
            kind = "NEEDS_INDEPENDENT_SOURCE"
            q = ("Day precision withdrawn 2026-08-26. The remaining year/month "
                 "value rests only on the Casino City vendor roster, which may "
                 "be read for QA and never published. Needs a free source "
                 "stating the opening before this date can ship.")
        elif vendor_only:
            kind = "NEEDS_INDEPENDENT_SOURCE"
            q = ("Date rests only on the Casino City vendor roster and cannot "
                 "be published. Needs a free source.")
        else:
            continue
        counts[kind] += 1
        rows.append({
            "queue": kind, "facility_id": f["facility_id"],
            "facility_name": f["facility_name"],
            "tribe_canonical_name": f.get("tribe_canonical_name", ""),
            "city": f.get("city", ""), "state": f.get("state", ""),
            "open_date_now": v,
            "open_date_source_value_verbatim":
                f.get("open_date_source_value_verbatim", ""),
            "open_date_precision": f.get("open_date_precision", ""),
            "open_date_not_before": f.get("open_date_not_before", ""),
            "open_date_not_after": f.get("open_date_not_after", ""),
            "open_date_basis": f.get("open_date_basis", "")[:400],
            "question": q,
            "YOUR_RULING": "", "your_source_url": "", "built_date": TODAY,
        })
    M.write_csv(CEDAR / "review" / f"gaming_open_date_resourcing_{TODAY}.csv", rows)
    print(f"queued {len(rows)} rows: {dict(counts)}")


if __name__ == "__main__":
    main()
