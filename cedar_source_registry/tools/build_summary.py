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


def ordered(counter, order):
    """
    Project a Counter onto a display order WITHOUT dropping unknown keys.

    The previous form -- {k: c[k] for k in ORDER if c[k]} -- silently discarded
    any value not already in the hardcoded list, so a new status_group vanished
    from summary.json while check_integrity (which recomputes from the full
    Counter) failed forever with no indication of the cause. Vocabulary drift
    must surface as a new key, never as a missing count.
    """
    known = [k for k in order if counter.get(k)]
    extra = sorted(k for k in counter if k not in order and counter[k])
    return {k: counter[k] for k in known + extra}


def main() -> int:
    sources = [
        json.loads(line)
        for line in (ROOT / "sources.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    existing = json.loads((ROOT / "summary.json").read_text(encoding="utf-8"))

    by_priority = Counter(s["source_priority_class"] for s in sources)
    by_status = Counter(s["status_group"] for s in sources)

    summary = {
        "registry": existing["registry"],
        "wave": existing["wave"],
        "generated": date.today().isoformat(),
        "scope": existing["scope"],
        "total_source_programs": len(sources),
        "by_priority_class": ordered(by_priority, PRIORITY_ORDER),
        "by_status_group": ordered(by_status, STATUS_ORDER),
    }

    # Optional blocks that exist only once the corresponding registry columns do.
    by_scope = Counter(
        s["nation_scope"] for s in sources if s.get("nation_scope")
    )
    if by_scope:
        summary["by_nation_scope"] = ordered(by_scope, NATION_SCOPE_ORDER)
        summary["sources_with_nation_ids"] = sum(
            1 for s in sources if s.get("nation_ids")
        )
    by_checked = Counter(s["last_checked"] for s in sources)
    summary["by_last_checked"] = {k: by_checked[k] for k in sorted(by_checked)}

    nations_path = ROOT / "nations.jsonl"
    if nations_path.exists():
        nations = [
            json.loads(line)
            for line in nations_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        summary["nations_in_crosswalk"] = len(nations)

        # Coverage ledger: knowing which tribes were checked and found NOTHING
        # is as load-bearing as the sources themselves — it is what keeps the
        # dataset maintainable (negatives carry recheck dates so the same
        # tribes are not re-researched forever).
        sourced = set()
        for s in sources:
            sourced.update(s.get("nation_ids") or [])
        neg_path = ROOT / "negative_findings.jsonl"
        neg_rows = []
        if neg_path.exists():
            neg_rows = [
                json.loads(line)
                for line in neg_path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
        negative_ids = {r["nation_id"] for r in neg_rows}
        bia_entities = sum(1 for n in nations if n.get("on_bia_list"))
        checked = sourced | negative_ids
        bia_checked = sum(
            1 for n in nations
            if n.get("on_bia_list") and (n["nation_id"] in checked)
        )
        by_result = Counter(r["result"] for r in neg_rows)
        by_recheck = Counter(r["recheck_after"] for r in neg_rows)
        summary["coverage"] = {
            "bia_list_total_reported": 575,
            "bia_list_total_note": "verified 2026-08-28 against the FR 2026-01-30 "
                                   "notice itself (91 FR 4102, owner-supplied PDF; "
                                   "research/bia_list_2026-01-30/). Crosswalk rows "
                                   "can exceed 575 because the combined Capitan "
                                   "Grande and Pribilof Islands entries are "
                                   "represented by their member rows",
            "bia_entities_in_crosswalk": bia_entities,
            "nations_with_source_rows": len(sourced),
            "nations_negative_findings_only": len(negative_ids - sourced),
            "nations_checked": len(checked),
            "bia_entities_unchecked_estimate": max(0, 575 - bia_checked),
            "negative_findings_by_result": {
                k: by_result[k] for k in sorted(by_result)
            },
            "rechecks_due_by": {k: by_recheck[k] for k in sorted(by_recheck)},
        }

    summary["matching_rules"] = existing["matching_rules"]

    out = json.dumps(summary, indent=1, ensure_ascii=False) + "\n"
    (ROOT / "summary.json").write_text(out, encoding="utf-8")
    print(f"summary.json regenerated: {len(sources)} sources", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
