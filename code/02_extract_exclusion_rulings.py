#!/usr/bin/env python3
"""
Cedar Press - 02: Extract the per-UEI exclusion jurisprudence from hci_analysis.do.

These are Elijah's hand rulings: UEIs that LOOK Native by name but are not
tribally owned (individually-Native-owned firms, non-profits, false name
matches). Each carries a citation - cage.dla.mil, GAO decisions,
OpenCorporates, archived company sites.

This is negative evidence, and it is the single most valuable asset against
false attribution: it is the only source that says "do NOT attribute this."
No automated pull regenerates it. Every future pull must consult it.

Output
------
data/spine/cedar_exclusion_rulings.csv
"""

import csv
import re
from datetime import date
from pathlib import Path

CEDAR = Path(r"C:\Users\esm247\Desktop\Cedar Press")
DOFILE = CEDAR / "data" / "raw" / "esm_hci" / "ESM" / "code" / "hci_analysis.do"
OUT = CEDAR / "data" / "spine" / "cedar_exclusion_rulings.csv"
TODAY = date.today().isoformat()

# drop if <idfield> == "VALUE"   [// trailing evidence comment]
DROP_RE = re.compile(
    r'^\s*drop\s+if\s+(?P<field>parent_uei|uei_id|awardee_uei|cage_code)\s*==\s*'
    r'"(?P<value>[^"]+)"\s*(?://+\s*(?P<comment>.*))?$',
    re.IGNORECASE,
)
URL_RE = re.compile(r'https?://\S+')


def classify(comment: str) -> str:
    """Bucket the ruling by the reason Elijah gave."""
    c = (comment or "").lower()
    if "individual" in c and "cherokee" in c:
        return "individually_native_owned"
    if "individual" in c:
        return "individually_native_owned"
    if "non-profit" in c or "nonprofit" in c or "not tribally owned" in c:
        return "nonprofit_not_tribally_owned"
    if "joint venture" in c or " jv" in c or "ahtna" in c:
        return "joint_venture_or_anc_exclusion"
    if not c.strip():
        return "unstated_reason_cited_lookup"
    return "other_documented_exclusion"


def evidence_kind(comment: str) -> str:
    c = (comment or "").lower()
    if "cage.dla.mil" in c:
        return "CAGE registry lookup"
    if "gao.gov" in c:
        return "GAO decision"
    if "opencorporates" in c:
        return "OpenCorporates filing"
    if "web.archive.org" in c:
        return "Archived company website"
    if "http" in c:
        return "Company website"
    return "Narrative note"


def main():
    if not DOFILE.exists():
        raise SystemExit(f"do-file not found: {DOFILE}")

    rows, seen = [], set()
    with open(DOFILE, "r", encoding="utf-8", errors="replace") as fh:
        for lineno, line in enumerate(fh, 1):
            m = DROP_RE.match(line.rstrip("\n"))
            if not m:
                continue
            value = m.group("value").strip()
            field = m.group("field").lower()
            comment = (m.group("comment") or "").strip()

            # Identifier-shaped only: UEIs are 12 alphanumerics, CAGE is 5.
            if field == "cage_code":
                idtype = "CAGE"
                if not re.fullmatch(r"[A-Z0-9]{5}", value, re.IGNORECASE):
                    continue
            else:
                idtype = "UEI"
                if not re.fullmatch(r"[A-Z0-9]{12}", value, re.IGNORECASE):
                    continue

            key = (idtype, value.upper())
            if key in seen:
                continue
            seen.add(key)

            urls = URL_RE.findall(comment)
            rows.append({
                "exclusion_id": "",
                "identifier_type": idtype,
                "identifier": value.upper(),
                "source_field": field,
                "exclusion_reason": classify(comment),
                "evidence_type": evidence_kind(comment),
                "evidence_url": urls[0] if urls else "",
                "ruling_note": URL_RE.sub("", comment).strip(" -/"),
                "ruled_by": "Elijah Moreno",
                "source_file": "hci_analysis.do",
                "source_line": lineno,
                "extracted_date": TODAY,
            })

    rows.sort(key=lambda r: (r["identifier_type"], r["identifier"]))
    for i, r in enumerate(rows, 1):
        r["exclusion_id"] = f"EXCL-{i:04d}"

    OUT.parent.mkdir(parents=True, exist_ok=True)
    fields = ["exclusion_id", "identifier_type", "identifier", "source_field",
              "exclusion_reason", "evidence_type", "evidence_url", "ruling_note",
              "ruled_by", "source_file", "source_line", "extracted_date"]
    with open(OUT, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)

    from collections import Counter
    print(f"extracted {len(rows):,} exclusion rulings -> {OUT.relative_to(CEDAR)}\n")
    print("--- by reason ---")
    for k, v in Counter(r["exclusion_reason"] for r in rows).most_common():
        print(f"  {v:>4}  {k}")
    print("\n--- by evidence type ---")
    for k, v in Counter(r["evidence_type"] for r in rows).most_common():
        print(f"  {v:>4}  {k}")
    cited = sum(1 for r in rows if r["evidence_url"])
    print(f"\nrulings carrying a citation URL: {cited:,} / {len(rows):,}")


if __name__ == "__main__":
    main()
