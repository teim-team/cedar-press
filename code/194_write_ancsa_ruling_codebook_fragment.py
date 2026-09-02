#!/usr/bin/env python3
"""
194 - Register the ANCSA ruling outputs in the codebook, as a FRAGMENT.

Writes `data/clean/codebook/05c_ancsa_ownership_ruling.csv`, covering the three
tables scripts 191-193 produced:

    review/ancsa_ruling_resolutions_2026-08-26.csv
    review/ancsa_ruling_refusals_2026-08-26.csv
    review/ancsa_adjacent_family_scan_2026-08-26.csv

WHY A FRAGMENT AND NOT A REBUILD
---------------------------------
`41_build_codebooks.py` is a GLOBAL rebuild and is on the do-not-run list; it
would delete blocks other agents registered. `156`, `172` and `176` established
the convention - touch ONE file, measure only what is a measurement, never
rebuild across another agent's timing. This follows it, and like them the new
fragment is **not** yet in `codebook_master.csv`; that is 41's job and 41 is
unsafe to run. Recorded rather than worked around.

`description`, `published` and `access_tier` are HAND-WRITTEN and are the point
of the file. `pct_filled` and `n_rows` are measured at run time.

**All three tables are `access_tier = internal`, `published = 0`.** They are
review artefacts: they record a refusal, an evidence rung and a human's
outstanding queue. A refusal file that shipped would read as an assertion about
an entity, which is the opposite of what it says.

SAFE TO RE-RUN. Backs up if the fragment exists, writes `.part`, renames,
appends only variables not already present.
"""

import csv
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUN_DATE = "2026-08-26"
CB = os.path.join(ROOT, "data", "clean", "codebook",
                  "05c_ancsa_ownership_ruling.csv")
BAK = f".bak_{RUN_DATE}_pre_194_write_ancsa_ruling_codebook_fragment"

HEADER = ["dataset", "variable", "type", "units", "pct_filled", "n_rows",
          "published", "access_tier", "description", "generated"]

SOURCES = {
    "05c_ancsa_ruling_resolutions": os.path.join(
        ROOT, "review", f"ancsa_ruling_resolutions_{RUN_DATE}.csv"),
    "05c_ancsa_ruling_refusals": os.path.join(
        ROOT, "review", f"ancsa_ruling_refusals_{RUN_DATE}.csv"),
    "05c_ancsa_adjacent_family_scan": os.path.join(
        ROOT, "review", f"ancsa_adjacent_family_scan_{RUN_DATE}.csv"),
}

DESC = {
    ("05c_ancsa_ruling_resolutions", "disposition"):
        "RESOLVED_TO_VILLAGE_CORPORATION_RULE_1 | "
        "RESOLVED_TO_VILLAGE_GOVERNMENT_RULE_3 | "
        "REDIRECTED_TO_A_THIRD_ENTITY_RULE_3 | RULE_3_CANDIDATE_HUMAN_NEEDED | "
        "HELD_BY_AN_EXISTING_RULING_HUMAN_NEEDED | "
        "HUMAN_NEEDED_SURVIVING_CORPORATION_UNVERIFIED. Rule 1 is the "
        "presumption; rule 3 is an exception that must be evidenced.",
    ("05c_ancsa_ruling_resolutions", "inherited_tier"):
        "The tier of the leg or evidence row this resolution points at, copied "
        "VERBATIM. The ruling assigns no tier and promotes nothing: it says "
        "which entity is correct, not that the link is strong. 206 of 322 "
        "resolutions are tier B and do not publish.",
    ("05c_ancsa_ruling_resolutions", "evidence"):
        "The named rung(s) that carried the decision. C1 a tier-A "
        "village_corporation_for edge; C2 a SETTLED outcome=ENTITY ruling on "
        "this identifier; C3 a ledger row with a RULED method; C4 a tier-A "
        "RULED brand_of edge; C5 one-sided name evidence pointing at the "
        "corporation and not at the village. A HOLD outcome is never a rung.",
    ("05c_ancsa_ruling_resolutions", "corporation_is_this_villages_own"):
        "Y where a tier-A village_corporation_for edge ties this corporation "
        "to this village government - the case the ruling squarely settles. N "
        "where the corporation belongs to a different village, which the "
        "ruling does not settle on its own.",
    ("05c_ancsa_ruling_resolutions", "redirected_to_third_entity"):
        "Populated where the correct owner is NEITHER leg of the defect.",
    ("05c_ancsa_ruling_refusals", "refusal_rule"):
        "RULE_2_A_VILLAGE_GOVERNMENT_NEVER_OWNS_AN_ANC. Every row here is an "
        "attribution that asserted a village government owns an ANC and is "
        "therefore wrong.",
    ("05c_ancsa_ruling_refusals", "refusal_text"):
        "The refusal in words, including the owner's rule-4 correction: the "
        "village-corporation/village-government link is ASSOCIATION and the "
        "association is ANCESTRAL, not membership - a shareholder is not "
        "necessarily enrolled in the tribe but necessarily has ancestry, "
        "because shares descend by inheritance and gift while village "
        "enrollment closed long ago. Two overlapping populations, not one "
        "list.",
    ("05c_ancsa_adjacent_family_scan", "ancsa_ruling_verdict"):
        "SETTLED_BY_THIS_RULING | CONSTRAINED_NOT_SETTLED | NOT_TOUCHED. "
        "CONSTRAINED_NOT_SETTLED means the ruling forbids one resolution path "
        "(rule 5: a regional corporation does not own a village corporation) "
        "without supplying the answer. It exists so that middle state is not "
        "collapsed into either neighbour.",
    ("05c_ancsa_adjacent_family_scan", "why"):
        "Why this row is or is not this question. The test is not 'is an ANC "
        "involved' but 'are these the two legal persons of ONE Alaska "
        "village'.",
}

GENERIC = {
    "node": "identifier_type:identifier, the graph node the defect sits on.",
    "identifier_type": "UEI, CAGE, DUNS or EIN.",
    "identifier": "The identifier value.",
    "firm_name": "Operating company name as recorded, for the reader. Never "
                 "evidence of ownership on its own.",
    "usd_observed": "Dollars observed on this identifier in the defect scan. "
                    "Context for triage, not an attributed total.",
    "ruling_cited": "docs/ANCSA_OWNERSHIP_RULING.md, Elijah 2026-08-26.",
    "built_date": "Run date.",
}


def measure(path):
    with open(path, newline="", encoding="utf-8-sig") as fh:
        rdr = csv.DictReader(fh)
        cols = list(rdr.fieldnames)
        rows = list(rdr)
    n = len(rows)
    filled = {c: sum(1 for r in rows if (r.get(c) or "").strip())
              for c in cols}
    return cols, n, filled


def main():
    existing, header = [], HEADER
    if os.path.exists(CB):
        with open(CB, newline="", encoding="utf-8-sig") as fh:
            rdr = csv.DictReader(fh)
            header = list(rdr.fieldnames)
            existing = list(rdr)
        with open(CB, "rb") as s, open(CB + BAK, "wb") as d:
            d.write(s.read())
        print(f"backed up -> {os.path.basename(CB + BAK)}")
    have = {(r["dataset"], r["variable"]) for r in existing}

    out = list(existing)
    added = 0
    for ds, path in SOURCES.items():
        cols, n, filled = measure(path)
        for c in cols:
            if (ds, c) in have:
                continue
            out.append({
                "dataset": ds, "variable": c, "type": "text", "units": "code",
                "pct_filled": round(100.0 * filled[c] / n, 1) if n else 0.0,
                "n_rows": n, "published": 0, "access_tier": "internal",
                "description": DESC.get((ds, c)) or GENERIC.get(
                    c, f"See code/191-193 and {os.path.basename(path)}."),
                "generated": RUN_DATE,
            })
            added += 1

    part = CB + ".part"
    with open(part, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=header)
        w.writeheader()
        w.writerows(out)
    os.replace(part, CB)

    with open(CB, newline="", encoding="utf-8-sig") as fh:
        back = list(csv.DictReader(fh))
    print(f"wrote {CB}: {added} variables added, {len(back)} rows on disk "
          f"(re-read, not trusted from the run log)")
    print("NOT registered in codebook_master.csv - that is 41's job and 41 is "
          "unsafe to run. Recorded, not worked around.")


if __name__ == "__main__":
    main()
