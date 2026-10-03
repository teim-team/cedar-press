#!/usr/bin/env python3
"""Read-only, uncapped CSV inventory of retired ID values by path and column.

Usage: python code/audit_retired_ids.py ROOT [ROOT ...]
Roots may be individual CSV files or directories. JSON lines go to stdout.
Historical inputs are intentionally reported, not modified or deleted.
"""

import csv
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

from cedar_ids import RETIRED_ISSUANCE_PREFIXES

csv.field_size_limit(10_000_000)

PREFIXES = sorted(RETIRED_ISSUANCE_PREFIXES | {"CEDAR-FAC"}, key=len, reverse=True)
PATTERN = re.compile(r"(?<![A-Za-z0-9])(?:" + "|".join(map(re.escape, PREFIXES)) + r")-[A-Za-z0-9-]+")


def inventory(path):
    counts = defaultdict(Counter)
    examples = {}
    rows = 0
    with path.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
        reader = csv.DictReader(fh)
        columns = reader.fieldnames or []
        for row in reader:
            rows += 1
            for column, value in row.items():
                if not column or not value or "-" not in value:
                    continue
                for match in PATTERN.finditer(value):
                    token = match.group(0).rstrip("-.,;:)]}\"'")
                    prefix = next((p for p in PREFIXES if token.startswith(p + "-")), "")
                    counts[column][prefix] += 1
                    examples.setdefault((column, prefix), token[:120])
    return {"path": str(path), "rows": rows, "columns": columns,
            "retired": [{"column": c, "prefix": p, "count": n,
                         "example": examples[(c, p)]}
                        for c in sorted(counts) for p, n in sorted(counts[c].items())]}


def paths(roots):
    seen = set()
    for root in roots:
        for path in ([root] if root.is_file() else root.rglob("*.csv")):
            resolved = path.resolve()
            if resolved not in seen:
                seen.add(resolved)
                yield path


def main(argv):
    if not argv:
        raise SystemExit("usage: audit_retired_ids.py ROOT [ROOT ...]")
    for path in paths(map(Path, argv)):
        try:
            print(json.dumps(inventory(path), ensure_ascii=False), flush=True)
        except (OSError, UnicodeError, csv.Error) as exc:
            print(json.dumps({"path": str(path), "error": str(exc)}), flush=True)
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
