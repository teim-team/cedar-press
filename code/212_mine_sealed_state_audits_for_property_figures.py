#!/usr/bin/env python3
"""
212_mine_sealed_state_audits_for_property_figures.py -- Cedar Press.

TARGET 2 of the blocked-source bypass: per-property gaming money in the three
states recorded as "collected but sealed" --

    Nevada    NGC-31 form confidentiality
    N. Dakota NDCC 54-58-02
    Kansas    KLRD

THE ARGUMENT
------------
**The seal is on the REGULATOR'S copy of the figure, not on the figure.** Cedar
already proved this shape once: 2 CFR 200.512(b)(2) withholds a tribal
auditee's REPORTING PACKAGE and the SEFA survives it (START_HERE.md, the
2026-08-12 correction). The same test is run here one level up -- does a figure
a STATE regulator seals appear in a document a FEDERAL audit regime publishes?

This script makes ZERO network calls. The 340 accepted Single Audit reporting
packages are already on disk as text at `data/raw/fac/txt/`. The 2026-08-12
sweep that produced `fac_audit_gaming_disclosures.csv` was aimed at machine
PARTICIPATION arrangements and typed only 25 of its 1,521 rows; it was never
looking for per-property money. This one is.

WHAT IT WILL AND WILL NOT CLAIM
-------------------------------
A tribal government's Single Audit does NOT contain the casino's gross gaming
revenue. What it contains is the money that CROSSED from a named casino to the
tribal government -- distributions, loan payments, administration fees, and
year-end balances due. Those are typed as what they are:

    CASINO_DISTRIBUTION_TO_TRIBE   an enterprise-fund transfer, per casino
    CASINO_PAYABLE_TO_TRIBE        a balance owed at the fiscal year end

Neither is `gaming_revenue` and neither is a floor for it -- a casino can
distribute more than it earned in a year out of reserves, and routinely
distributes far less. **A transfer is not a revenue bound and is not published
as one.** The point of the row is that a per-PROPERTY figure exists at all in a
state whose regulator publishes none.

WRITES (staged, never merged here -- other agents are live)
  review/sealed_state_property_figures_2026-08-26.csv
  review/sealed_state_audit_sweep_2026-08-26.json
"""
import csv, glob, json, os, re, sys
from pathlib import Path

CEDAR = Path(__file__).resolve().parent.parent
TXT = CEDAR / "data" / "raw" / "fac" / "txt"
SPINE = CEDAR / "data" / "clean" / "fac_tribal_single_audits.csv"
REVIEW = CEDAR / "review"
TODAY = "2026-08-26"

SEALED = {"NV", "ND", "KS"}

# Property-name anchors. Deliberately NOT a bare "casino" match: an auditee that
# merely mentions the word tells us nothing. A named property does.
CASINO_NAME = re.compile(
    r"\b([A-Z][A-Za-z'\u2019\-]+(?:\s+[A-Z][A-Za-z'\u2019\-]+){0,3}\s+"
    r"(?:Casino(?:\s+(?:and|&)\s+(?:Resort|Hotel))?|Casino\s+Resort))\b")

MONEY = re.compile(r"\$?\s?([0-9]{1,3}(?:,[0-9]{3})+(?:\.[0-9]{2})?)")

# A money figure with a casino/gaming word inside 240 characters either side.
# MEASURED: a line-anchored pattern misses almost everything here, because the
# figures that matter live in TABLES whose cells `pdftotext` emits one per line
# -- Turtle Mountain's whole related-party transfer table is 40 short lines.
# The document is whitespace-normalised to one string before matching.
NEAR_MONEY = re.compile(
    r".{0,240}(?:Casino|Gaming|gaming|casino)\s.{0,240}?"
    r"\$\s?[0-9]{1,3}(?:,[0-9]{3})+(?:\.[0-9]{2})?.{0,140}")


def load_spine():
    idx = {}
    with open(SPINE, encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            idx.setdefault(r["report_id"], r)
    return idx


def main():
    spine = load_spine()
    REVIEW.mkdir(exist_ok=True)
    sweep = {"built_date": TODAY, "network_calls": 0, "files_scanned": 0,
             "sealed_state_files": 0, "reports_with_named_property": [],
             "notes": []}
    out_rows = []

    for f in sorted(glob.glob(str(TXT / "*.txt"))):
        sweep["files_scanned"] += 1
        rid = os.path.basename(f)[:-4]
        meta = spine.get(rid)
        if not meta or meta.get("auditee_state") not in SEALED:
            continue
        sweep["sealed_state_files"] += 1
        text = open(f, encoding="utf-8", errors="replace").read()
        names = sorted({m.group(1).strip() for m in CASINO_NAME.finditer(text)})
        # Drop obvious non-properties picked up by the capitalisation rule.
        names = [n for n in names
                 if not re.match(r"^(The|A|And|Due|From|To|Indian|Tribal|Class)\b", n)]
        if not names:
            continue
        sweep["reports_with_named_property"].append(
            {"report_id": rid, "auditee": meta["auditee_name"],
             "state": meta["auditee_state"], "audit_year": meta["audit_year"],
             "named_properties": names})

        flat = re.sub(r"\s+", " ", text)
        for m in NEAR_MONEY.finditer(flat):
            quote = m.group(0).strip()
            figs = MONEY.findall(quote)
            out_rows.append({
                "state": meta["auditee_state"],
                "auditee_name": meta["auditee_name"],
                "entity_id": meta.get("entity_id", ""),
                "entity_name": meta.get("entity_name", ""),
                "entity_tier": meta.get("entity_tier", ""),
                "audit_year": meta["audit_year"],
                "fy_end_date": meta.get("fy_end_date", ""),
                "properties_named_in_report": " | ".join(names[:8]),
                "report_id": rid,
                "source_authority": "Federal Audit Clearinghouse (2 CFR 200 Subpart F single audit)",
                "source_document_type": "audited financial statements, notes to financial statements",
                "source_url": meta.get("source_url", ""),
                "verbatim_quote": quote[:1200],
                "figures_in_quote": " | ".join(figs[:12]),
                "measurement_type": "PENDING_HAND_TYPING",
                "built_date": TODAY,
            })

    # De-duplicate on (report_id, property)
    seen, ded = set(), []
    for r in out_rows:
        k = (r["report_id"], r["verbatim_quote"][:200])
        if k in seen:
            continue
        seen.add(k)
        ded.append(r)

    outp = REVIEW / f"sealed_state_property_figures_{TODAY}.csv"
    if ded:
        with open(outp, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(ded[0].keys()))
            w.writeheader()
            w.writerows(ded)
    sweep["staged_rows"] = len(ded)
    (REVIEW / f"sealed_state_audit_sweep_{TODAY}.json").write_text(
        json.dumps(sweep, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in sweep.items()
                      if k != "reports_with_named_property"}, indent=2))
    for r in sweep["reports_with_named_property"]:
        print(" ", r["state"], r["audit_year"], r["auditee"], "->", r["named_properties"])


if __name__ == "__main__":
    main()
