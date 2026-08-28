#!/usr/bin/env python3
"""Regenerate the roster table in outreach/requests.md from partnership_leads.jsonl.

Only the generated table between the markers is rewritten; the hand-written
sections (priority conversions, protocol) are preserved.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BEGIN = "<!-- BEGIN GENERATED ROSTER -->"
END = "<!-- END GENERATED ROSTER -->"


def main() -> None:
    leads = [
        json.loads(line)
        for line in (ROOT / "partnership_leads.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    rows = [
        "| Source | Nation / org | Roster to request | Cited basis (evidence of existence) | Recommended ask |",
        "|---|---|---|---|---|",
    ]
    for lead in leads:
        rows.append(
            "| {source_id} | {nation_source} | {directory_register} | {evidence} | {ask} |".format(
                source_id=lead["source_id"],
                nation_source=lead["nation_source"].replace("|", "/"),
                directory_register=lead["directory_register"].replace("|", "/"),
                evidence=(lead.get("evidence_of_existence") or "—").replace("|", "/"),
                ask=(lead.get("recommended_next_step") or "—").replace("|", "/"),
            )
        )
    table = "\n".join(rows)

    path = ROOT / "outreach" / "requests.md"
    text = path.read_text(encoding="utf-8")
    pre, rest = text.split(BEGIN, 1)
    _, post = rest.split(END, 1)
    path.write_text(f"{pre}{BEGIN}\n{table}\n{END}{post}", encoding="utf-8")
    print(f"outreach/requests.md roster regenerated: {len(leads)} leads")


if __name__ == "__main__":
    main()
