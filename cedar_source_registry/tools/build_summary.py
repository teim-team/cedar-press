#!/usr/bin/env python3
"""Regenerate summary.json from sources.jsonl.

Counts are computed, never transcribed (definition of done for every
registry-facing PR). The matching rules block is carried over verbatim from the
existing summary.json — rules are policy, not counts, and change only by an
explicit registry edit.
"""
import json
import sys
from collections import Counter
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

PRIORITY_ORDER = [
    "Tribal Primary",
    "Tribal Secondary",
    "Tribal Partnership",
    "Cross-Reference",
    "Discovery Only",
    "Coverage Frame",
]
STATUS_ORDER = ["Live", "Stale", "Historical", "Lead", "Complementary"]
NATION_SCOPE_ORDER = [
    "single_nation",
    "multi_nation",
    "regional",
    "national",
    "unknown",
]


def main() -> int:
    sources = [
        json.loads(line)
        for line in (ROOT / "sources.jsonl").read_text().splitlines()
        if line.strip()
    ]
    existing = json.loads((ROOT / "summary.json").read_text())

    by_priority = Counter(s["source_priority_class"] for s in sources)
    by_status = Counter(s["status_group"] for s in sources)

    summary = {
        "registry": existing["registry"],
        "wave": existing["wave"],
        "generated": date.today().isoformat(),
        "scope": existing["scope"],
        "total_source_programs": len(sources),
        "by_priority_class": {
            k: by_priority[k] for k in PRIORITY_ORDER if by_priority[k]
        },
        "by_status_group": {k: by_status[k] for k in STATUS_ORDER if by_status[k]},
    }

    # Optional blocks that exist only once the corresponding registry columns do.
    by_scope = Counter(
        s["nation_scope"] for s in sources if s.get("nation_scope")
    )
    if by_scope:
        summary["by_nation_scope"] = {
            k: by_scope[k] for k in NATION_SCOPE_ORDER if by_scope[k]
        }
        summary["sources_with_nation_ids"] = sum(
            1 for s in sources if s.get("nation_ids")
        )
    by_checked = Counter(s["last_checked"] for s in sources)
    summary["by_last_checked"] = {k: by_checked[k] for k in sorted(by_checked)}

    nations_path = ROOT / "nations.jsonl"
    if nations_path.exists():
        nations = [
            json.loads(line)
            for line in nations_path.read_text().splitlines()
            if line.strip()
        ]
        summary["nations_in_crosswalk"] = len(nations)

    summary["matching_rules"] = existing["matching_rules"]

    out = json.dumps(summary, indent=1, ensure_ascii=False) + "\n"
    (ROOT / "summary.json").write_text(out)
    print(f"summary.json regenerated: {len(sources)} sources", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
