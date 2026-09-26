"""Read-only inventory of local gaming-related CSVs; prints JSON lines to stdout.

Usage: python scripts/audit_gaming_inventory.py "<data workspace>/data/clean"
"""

import csv
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path

PATTERN = re.compile(r"gaming|nigc|compact|casino|sports|olms|nlrb|osha|5500|permit|amenit|declin|nepa|region|loyalty|wa_machine", re.I)
DATE = re.compile(r"(?:19|20)\d{2}")
KEY_SUFFIX = ("_id", "_uid")


def inspect(path):
    digest = hashlib.sha256()
    with path.open("rb") as binary:
        for chunk in iter(lambda: binary.read(1024 * 1024), b""):
            digest.update(chunk)
    with path.open(encoding="utf-8-sig", newline="", errors="replace") as source:
        reader = csv.DictReader(source)
        columns = reader.fieldnames or []
        keys = [c for c in columns if c.endswith(KEY_SUFFIX) or c in ("cedar_uid", "fiscal_year")]
        dates = [c for c in columns if "date" in c or "year" in c or "period" in c]
        values = {c: set() for c in keys}
        blank = Counter()
        years = {c: set() for c in dates}
        year_counts = {c: Counter() for c in dates}
        iso_dates = {c: set() for c in dates if c.endswith("_date")}
        rows = 0
        for row in reader:
            rows += 1
            for c in keys:
                v = row.get(c, "").strip()
                if v:
                    values[c].add(v)
                else:
                    blank[c] += 1
            for c in dates:
                match = DATE.search(row.get(c, ""))
                if match:
                    years[c].add(int(match.group()))
                    year_counts[c][match.group()] += 1
                if c in iso_dates and re.fullmatch(r"\d{4}-\d{2}-\d{2}", row.get(c, "")):
                    iso_dates[c].add(row[c])
    return {"path": str(path), "rows": rows, "bytes": path.stat().st_size,
            "sha256": digest.hexdigest(), "columns": columns,
            "keys": {c: {"distinct": len(values[c]), "blank": blank[c]} for c in keys},
            "years": {c: [min(y), max(y)] for c, y in years.items() if y},
            "recent": {c: {y: n for y, n in counts.items() if y in ("2025", "2026")}
                       for c, counts in year_counts.items() if counts.get("2025") or counts.get("2026")},
            "source_dates": {c: [min(v), max(v)] for c, v in iso_dates.items() if v}}


def main():
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    root = Path(sys.argv[1])
    if not root.is_dir():
        raise SystemExit(f"No such directory: {root}")
    for path in sorted(root.glob("*.csv")):
        if PATTERN.search(path.name):
            print(json.dumps(inspect(path), ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
