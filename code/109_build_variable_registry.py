#!/usr/bin/env python3
"""
Cedar Press - 109: One vocabulary for columns, not sixteen.

ELIJAH, 2026-08-07
------------------
"a lot of these variables across our datasets are just taken as given and we
 might need to rename them, or add a question mark you can hover for clarity, or
 have a codebook. we can also make our own variables too, and clean up the data
 and harmonize it further."

MEASURED, AND HE IS RIGHT
-------------------------
    1,054 variables across 16 datasets
      910 distinct names
       63 appear in more than one dataset

So 93% of our column names are used exactly once. We inherited federal naming
wholesale and never reconciled it. The worst case is the JOIN KEY itself:

    entity_id            8 datasets
    tribe_id             7 datasets
    recipient_entity_id  1
    cedar_entity_id      1
    operator_entity_id   1

Five spellings for the column everything joins on. Money has nine spellings,
dates nine, names six.

WHY THIS DOES NOT RENAME ANYTHING
---------------------------------
Renaming 910 columns in place would break every script, every review file and
every ruling that references them - and would orphan work that took months.
Same reasoning as `cedar_domain.Tier.A.value == "A"`: the value in the data
wins.

So this builds a REGISTRY - a mapping layer over the existing names:

    concept          what the number MEANS, once
    canonical_name   the name we would use in a clean world
    source_names     every existing spelling, preserved
    display_label    what a human reads in the app
    definition       the hover text
    unit / grain     what it is counted in, and per what

The app reads the registry for labels and tooltips. Scripts keep using the
column names they already use. Nothing breaks and everything gets explained.

CEDAR'S OWN VARIABLES
---------------------
Some columns exist only because we made them - `tier`, `measurement_type`,
`bound_basis`, `parent_native_entity`. Those are the product, and they need the
CLEAREST definitions of all, because a subscriber has never seen them before and
cannot look them up anywhere else.

Writes data/clean/variable_registry.csv
       data/clean/variable_display.json      for the app
"""

import csv
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

CEDAR = Path(__file__).resolve().parent.parent
CLEAN = CEDAR / "data" / "clean"
TODAY = date.today().isoformat()

csv.field_size_limit(min(sys.maxsize, 2**31 - 1))

# concept -> (canonical, display label, definition, unit, grain, source names)
# Definitions are written for a subscriber who has never seen the dataset.
CONCEPTS = [
    ("entity_key", "cedar_entity_id", "Cedar entity",
     "The Native entity this record belongs to. A stable Cedar Press "
     "identifier that does not change between releases, so a panel joins "
     "across datasets and across vintages.",
     "id", "entity",
     ["tribe_id", "entity_id", "recipient_entity_id", "cedar_entity_id",
      "operator_entity_id", "subject_entity_id", "from_tribe_id",
      "to_tribe_id", "beneficiary_entity_id", "payer_entity_id"]),

    ("entity_name", "cedar_entity_name", "Entity",
     "The entity's canonical name as Cedar Press records it. Source documents "
     "often use a longer official name or a shorter common one; both are kept "
     "as aliases.",
     "text", "entity",
     ["canonical_name", "tribe_canonical_name", "entity", "tribe"]),

    ("source_name", "reported_name", "Name as reported",
     "The name exactly as the source document printed it, before resolution. "
     "Kept so any attribution can be checked against what the record actually "
     "said.",
     "text", "record",
     ["recipient_name", "awardee_name", "legal_business_name",
      "witness_organization", "requesting_organization", "prime_name",
      "sub_name", "Native_Party"]),

    ("money", "amount_usd", "Amount",
     "A dollar figure as reported by the source. Negative means money was "
     "taken back (a deobligation) and belongs in totals; zero means an action "
     "occurred that moved no money; blank means not reported, which is not "
     "the same as zero.",
     "USD", "record",
     ["total_obligations", "obligated_usd", "subaward_amount", "amount_usd",
      "spend_usd", "ggr_usd", "tax_remitted_usd", "Announced_Value_USD",
      "amount_requested", "amount_enacted", "value", "amount"]),

    ("money_real", "amount_usd_real2025", "Amount (2025 dollars)",
     "The same figure rebased to constant 2025 dollars using the BEA GDP "
     "deflator, so a long series can be read without inflation distorting it.",
     "USD 2025", "record",
     ["amount_usd_real2025", "total_obligations_real2025", "ggr_usd_real2025"]),

    ("fiscal_year", "fiscal_year", "Fiscal year",
     "The federal or state fiscal year the record falls in. Not a calendar "
     "year - the federal fiscal year runs October to September.",
     "year", "record",
     ["fiscal_year", "year", "tax_year", "filing_year", "congress_year"]),

    ("observed_date", "as_of_date", "As of",
     "The date the measurement was true, not the date we retrieved it. A "
     "capacity count with no as-of date cannot be interpreted.",
     "date", "observation",
     ["as_of_date", "observation_date", "action_date", "event_date",
      "notice_date", "meeting_date", "hearing_date", "subaward_date"]),

    ("source_url", "source_url", "Source",
     "The document this row came from. Every published row has one, so any "
     "figure can be traced to the record that states it.",
     "url", "record",
     ["source_url", "evidence_url", "Source_1", "source_document",
      "testimony_url", "materials_url"]),

    ("source_quote", "source_quote", "Quoted text",
     "The verbatim wording from the source that supports this row. A claim "
     "that cannot be quoted is not recorded.",
     "text", "record",
     ["source_quote", "supporting_text", "evidence_text", "claim_text",
      "source_evidence"]),

    ("fetched", "fetched_date", "Retrieved",
     "When Cedar Press retrieved the source. Distinct from the as-of date: a "
     "2026 retrieval can describe a 2003 fact.",
     "date", "record",
     ["fetched_date", "retrieved_at", "geocoded_date"]),

    ("state", "state", "State",
     "Two-letter state code. Where a record has both a recipient location and "
     "a place of performance, this is the recipient's.",
     "code", "record",
     ["state", "recipient_state_code", "member_state", "state_or_region"]),

    ("agency", "federal_agency", "Agency",
     "The federal agency that awarded, funded or published the record.",
     "text", "record",
     ["funding_agency", "awarding_agency", "agency", "federal_agency",
      "recipient_agency", "state_recipient_agency"]),
]

# Cedar's OWN variables. These are the product and a subscriber has never seen
# them anywhere else, so the definitions carry the most weight.
CEDAR_ORIGINAL = [
    ("tier", "Confidence tier",
     "What may be done with this row. A = verified or human-ruled, and "
     "publishable. B = visible for analysis but never published on its own. "
     "C = in the corpus but not linked to an entity. X = ruled out, "
     "permanently.", "A|B|C|X"),
    ("measurement_type", "Kind of measurement",
     "What kind of number this is. An authorised maximum is not a count of "
     "what operates; a projection is not an observation. Cedar never promotes "
     "one to another.", "enum"),
    ("measurement_status", "Evidence class",
     "How the figure was established: reported by the source, derived exactly "
     "by arithmetic from a published rate, bounded, or not reported at all.",
     "enum"),
    ("bound_basis", "Why this is a bound",
     "What stops this from being an exact figure - a minimum-payment clause, "
     "a bracketed rate schedule, or a total that covers more than one thing. "
     "A factual bound is not a statistical confidence interval.", "text"),
    ("parent_native_entity", "Native owner",
     "The Native entity that OWNS this firm. Distinct from an entity a firm "
     "merely serves - ownership and service are never collapsed.", "id"),
    ("serves_native_entities", "Serves",
     "Native entities this organisation serves without being owned by them. "
     "Never evidence of ownership.", "text"),
    ("ultimate_parent_entity_id", "Ultimate Native owner",
     "The top of the ownership chain - the Native government or corporation a "
     "roll-up should group by. Intermediate holding layers are recorded "
     "separately and are not published as a settled org chart.", "id"),
    ("attribution_method", "How it was linked",
     "The method that connected this record to an entity. A human ruling "
     "outranks every automated method, including an exact identifier match.",
     "enum"),
    ("duplicate_status", "Duplicate handling",
     "Whether this row is the primary record or a repeat of one already "
     "counted. Repeats are flagged rather than deleted so our totals can be "
     "reproduced.", "enum"),
    ("reported_8a", "8(a) reported",
     "Whether the FEDERAL RECORD reports 8(a) participation. This is a "
     "self-report, not Cedar's determination - 60.9% of the Native "
     "contracting dollars we identify carry no Native preference flag at all.",
     "0|1"),
]


def main():
    print("=== Cedar Press 109: variable registry ===\n")
    cb = list(csv.DictReader(
        open(CLEAN / "codebook_master.csv", encoding="utf-8-sig",
             errors="replace")))
    present = defaultdict(set)
    for r in cb:
        present[r["variable"]].add(r["dataset"])
    print(f"codebook: {len(cb):,} variables, {len(present):,} distinct names, "
          f"{len({r['dataset'] for r in cb})} datasets")

    rows, mapped = [], set()
    for concept, canon, label, definition, unit, grain, names in CONCEPTS:
        hits = [n for n in names if n in present]
        for n in hits:
            mapped.add(n)
        rows.append({
            "concept": concept, "canonical_name": canon,
            "display_label": label, "definition": definition,
            "unit": unit, "grain": grain,
            "source_names": " | ".join(sorted(hits)),
            "n_source_names": len(hits),
            "n_datasets": len({d for n in hits for d in present[n]}),
            "cedar_original": 0, "built_date": TODAY,
        })

    for var, label, definition, unit in CEDAR_ORIGINAL:
        rows.append({
            "concept": var, "canonical_name": var, "display_label": label,
            "definition": definition, "unit": unit, "grain": "record",
            "source_names": var if var in present else "",
            "n_source_names": 1 if var in present else 0,
            "n_datasets": len(present.get(var, [])),
            "cedar_original": 1, "built_date": TODAY,
        })
        mapped.add(var)

    p = CLEAN / "variable_registry.csv"
    with open(p, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"  wrote {p.relative_to(CEDAR)}  ({len(rows)} concepts)")

    # ---- the app's lookup: source column name -> label + tooltip ---------
    disp = {}
    for r in rows:
        for n in r["source_names"].split(" | "):
            if n:
                disp[n] = {"label": r["display_label"],
                           "tooltip": r["definition"],
                           "canonical": r["canonical_name"],
                           "unit": r["unit"],
                           "cedar_original": bool(r["cedar_original"])}
    # anything the codebook described but the registry has not reached
    for r in cb:
        n = r["variable"]
        if n not in disp and (r.get("description") or "").strip():
            disp[n] = {"label": n.replace("_", " ").strip().capitalize(),
                       "tooltip": r["description"],
                       "canonical": n, "unit": r.get("units", ""),
                       "cedar_original": False}
    p2 = CLEAN / "variable_display.json"
    p2.write_text(json.dumps(disp, indent=1, sort_keys=True), encoding="utf-8")
    print(f"  wrote {p2.relative_to(CEDAR)}  ({len(disp):,} columns carry a "
          f"label and tooltip)")

    fragmented = sorted((r for r in rows if r["n_source_names"] > 1),
                        key=lambda r: -r["n_source_names"])
    print("\n  worst fragmentation - one concept, many spellings:")
    for r in fragmented[:8]:
        print(f"     {r['n_source_names']:>2} names across {r['n_datasets']:>2} "
              f"datasets  {r['concept']:14s} -> {r['canonical_name']}")

    undoc = [n for n in present if n not in disp]
    print(f"\n  {len(disp):,} of {len(present):,} columns now carry a "
          f"human label and hover definition")
    print(f"  {len(undoc):,} still undocumented - the next target")
    if undoc:
        for n in sorted(undoc)[:10]:
            print(f"       {n}")


if __name__ == "__main__":
    main()
