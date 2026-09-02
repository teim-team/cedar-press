#!/usr/bin/env python3
"""
Cedar Press - 525: EVENT IDs. The 'thing', alongside the 'who'.

    py -3 code/525_event_ids.py            # registry + gap report
    py -3 code/525_event_ids.py verify     # read-only, exit 1 on breach

WHY
---
Owner, 2026-09-01:

    "The initial datasets I mentioned are pretty good because they have the
     native entity IDs - who's involved - and then they have the transaction
     ID. So it can keep track of the thing you're talking about and the entity
     you're talking about doing the thing... it has to be cognizant of the
     other datasets, so we can't use the same transaction ID in natural
     resources that we do for Indian country deals, because then we wouldn't
     want them to seem like they're the same transaction."

Cedar answers WHO with `cedar_uid` (dataset 13, the hub - ADR-009). It answers
WHAT HAPPENED inconsistently: 27 distinct id prefixes are in the wild, minted
ad hoc by whichever script needed one, with **no registry and no collision
check**. Two datasets can mint the same-looking id today and nothing notices.

This file is the registry. It is deliberately small.

WHAT NEEDS AN EVENT ID, AND WHAT DOES NOT
-----------------------------------------
Not every table. Three shapes, and only one of them needs a surrogate:

  EVENT    a thing that happened, at a time, involving parties - a deal, an
           award, a lease, a filing, a payment. NEEDS a stable event id,
           because the same event recurs across tables and must be joinable.
  PANEL    a measure per (entity x period) - obligations by tribe-year.
           NEEDS NO surrogate: the dimensions ARE the key, and adding one
           invites a buyer to think two rows differ when they do not.
  REGISTRY one row per durable thing - an entity, a facility, a property.
           Already has an id, from the hub or from its own minting.

Getting this wrong in the PANEL direction is not harmless. It is how a table
acquires a key that is unique but meaningless, which is exactly the trap the
grain sweep found in `contractor_ranking.csv`, whose only unique keys required
a MEASURE.

THE SCHEME
----------
    <PREFIX>-<12 hex>        e.g. DEAL-3f9a1c7b20e4

`PREFIX` is registered here, unique across the whole project, and names the
DATASET and the EVENT TYPE together. The digest is `cedar_keys.surrogate_id`
over declared natural columns - content-addressed, so the same event yields
the same id in any process on any machine, forever.

The rule `cedar_keys` already states and this file enforces:

    A KEY MAY NEVER DEPEND ON ANYTHING OUTSIDE THE ROW ITSELF.

Not `hash()`, not `uuid4()`, not row position, not rank. Lint class 7 exists
because both of those shipped here once: `ferc_filing_id` kept 4 of 2,534 ids
across a rebuild, and `INV-0307` silently acquired another firm's ownership
sentence when a rank shifted.

**A natural key beats a surrogate every time.** Where the SOURCE already
assigns a stable identifier - an FPDS `contract_transaction_unique_key`, an FR
`document_number`, an LDA `filing_uuid` - that IS the event id and this
registry records it as `natural` rather than minting a second one. A surrogate
next to a perfectly good natural key is two ids for one thing.
"""
from __future__ import annotations

import csv
import json
import sys
from collections import Counter
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
csv.field_size_limit(10_000_000)
TODAY = date.today().isoformat()

OUT = ROOT / "data" / "spine" / "cedar_event_id_registry.csv"
OUT_MD = ROOT / "docs" / "EVENT_IDS.md"
CONTRACTS = ROOT / "docs" / "schema" / "dataset_contracts.json"

# =====================================================================
# THE REGISTRY. One row per event type. PREFIX IS UNIQUE PROJECT-WIDE.
# =====================================================================
# kind: natural   - the source already assigns a stable id; use it, mint nothing
#       surrogate - no natural key; mint from the declared columns
#       panel     - dimensions are the key; NO event id, recorded so the
#                   absence is a decision rather than an oversight
REGISTRY = [
    # ---- deals -------------------------------------------------------
    dict(dataset="deals", event="a transaction in Indian Country",
         table="deals_classified.csv", prefix="DEAL", kind="existing",
         columns=["Deal_ID"],
         note="ALREADY EXISTS. The deals ledger has carried Deal_ID all "
              "along; the gap was that nothing registered it, so nothing "
              "stopped another dataset minting something that looked like it."),

    # ---- natural resources -------------------------------------------
    dict(dataset="natural-resources", event="a resource revenue payment",
         table="resource_revenue.csv", prefix="RRE", kind="existing",
         columns=["resource_revenue_event_id"],
         note="ALREADY EXISTS - the owner's own example, and it was already "
              "built. resource_revenue_event_id is distinct from DEAL by "
              "construction, which is exactly the separation he asked for: a "
              "resource payment and a deal can never look like the same "
              "transaction."),
    dict(dataset="natural-resources", event="a lease / asset record",
         table="resource_assets.csv", prefix="RAS", kind="existing",
         columns=["resource_asset_id"],
         note="ALREADY EXISTS. An asset is durable rather than an event, but "
              "the revenue rows point at it, so it needs a stable handle."),

    # ---- gaming --------------------------------------------------------
    dict(dataset="gaming", event="a gaming land / ordinance decision",
         table="gaming_land_decisions.csv", prefix="GLD", kind="existing",
         columns=["decision_id"],
         note="ALREADY EXISTS."),

    # ---- contractors ----------------------------------------------------
    dict(dataset="contractors", event="a prime contract transaction",
         table="prime_contracts.csv", prefix="FPDSTX", kind="natural",
         columns=["contract_transaction_unique_key"],
         note="FPDS assigns it and it is now part of the validated PK. The "
              "80,778 apparent duplicates were distinct transactions whose "
              "identity the mapper had destroyed - the natural key was always "
              "there and was being thrown away. 376,766 rows still carry no "
              "value (the BGOV aggregate half); those events cannot be "
              "referenced individually and that is recorded, not hidden."),

    # ---- funding ---------------------------------------------------------
    dict(dataset="funding", event="an assistance transaction",
         table="federal_funding_transactions.csv", prefix="ASSTTX",
         kind="natural", columns=["assistance_transaction_unique_key"],
         note="Measured unique across all 701,955 rows of the "
              "assistance+archive union."),
    dict(dataset="funding", event="obligations per entity-year",
         table="federal_funding_tribe_year_panel.csv", prefix="",
         kind="panel", columns=["tribe_id", "fiscal_year"],
         note="PANEL - the dimensions ARE the key. Minting a surrogate here "
              "would invite a buyer to believe two rows are different events "
              "when they are one measure."),

    # ---- lobbying ---------------------------------------------------------
    dict(dataset="lobbying", event="an LDA filing",
         table="native_entity_lobbying_disclosures.csv", prefix="LDAFIL",
         kind="natural", columns=["filing_uuid"],
         note="The LDA API assigns filing_uuid; 353 already re-keys consumers "
              "on it."),

    # ---- federal register / nagpra ----------------------------------------
    dict(dataset="federal-register", event="a Federal Register document",
         table="federal_actions.csv", prefix="FRDOC", kind="natural",
         columns=["document_number"],
         note="SHARES the FRDOC namespace with nagpra DELIBERATELY - see the "
              "nagpra entry."),
    dict(dataset="nagpra", event="a NAGPRA notice",
         table="nagpra_notices.csv", prefix="FRDOC", kind="natural",
         columns=["document_number"],
         note="SHARES the FRDOC namespace with federal-register deliberately: "
              "a NAGPRA notice IS a Federal Register document, and the same "
              "document surfacing in two collections must carry the SAME id. "
              "The one case where a shared prefix is correct, declared here so "
              "the collision check treats it as intent rather than error."),

    # ---- subcontracting - THE REAL GAP -------------------------------------
    dict(dataset="subcontracting", event="a subaward",
         table="subawards.csv", prefix="SUBAW", kind="MISSING",
         columns=[],
         note="THE ONE DATASET THAT GENUINELY LACKS AN EVENT ID. Measured on "
              "72,837 rows: subaward_number gives 36,098 distinct values; "
              "(prime_award_id + subaward_number) still collides 32,394 "
              "times; adding sub_uei only gets to 31,078 collisions. FSRS "
              "does not assign a usable unique id and no combination of the "
              "columns we carry is unique - the same destroyed-identity shape "
              "prime_contracts had, where the mapper dropped the column that "
              "separated the rows. Do NOT mint a surrogate over a key that is "
              "not unique: it would manufacture 31,078 false distinctions. "
              "Diagnose the source extract first."),
]



def read_csv(p: Path) -> list:
    if not p.exists():
        return []
    with p.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
        return list(csv.DictReader(fh))


def header_of(name: str):
    for d in ("data/clean", "data/spine"):
        p = ROOT / d / name
        if p.exists():
            try:
                with p.open(encoding="utf-8-sig", errors="replace",
                            newline="") as fh:
                    return next(csv.reader(fh), []), p
            except OSError:
                return [], p
    return [], None


def check():
    fails, warns = [], []

    # C1 - prefix collisions across DIFFERENT datasets, except declared shares
    by_prefix = {}
    for r in REGISTRY:
        if r["kind"] == "panel" or not r["prefix"]:
            continue
        by_prefix.setdefault(r["prefix"], []).append(r)
    for pre, rows in sorted(by_prefix.items()):
        ds = {r["dataset"] for r in rows}
        if len(ds) > 1:
            shared = any("SHARES" in (r["note"] or "") for r in rows)
            if not shared:
                fails.append(
                    f"E1 prefix {pre!r} is claimed by {sorted(ds)} without a "
                    f"declared share - two datasets would mint ids that look "
                    f"like the same kind of thing")

    # C2 - the declared columns must exist in the table
    for r in REGISTRY:
        hdr, path = header_of(r["table"])
        if path is None:
            warns.append(f"E2 {r['table']} not on disk - registry entry is "
                         f"ahead of the data")
            continue
        missing = [c for c in r["columns"] if c not in hdr]
        if missing:
            fails.append(f"E2 {r['table']}: declared id columns absent from "
                         f"the file: {missing}")

    # C3 - a `natural` entry must actually be unique on the full file
    for r in REGISTRY:
        if r["kind"] not in ("natural", "existing") or not r["columns"]:
            continue
        hdr, path = header_of(r["table"])
        if path is None:
            continue
        seen, dupes, blank = set(), 0, 0
        try:
            with path.open(encoding="utf-8-sig", errors="replace",
                           newline="") as fh:
                for row in csv.DictReader(fh):
                    k = tuple((row.get(c) or "").strip() for c in r["columns"])
                    if not any(k):
                        blank += 1
                        continue
                    if k in seen:
                        dupes += 1
                    seen.add(k)
        except OSError:
            continue
        if dupes:
            fails.append(f"E3 {r['table']}: declared NATURAL id "
                         f"{'+'.join(r['columns'])} is not unique - {dupes:,} "
                         f"duplicate values. It is not a natural key.")
        if blank:
            warns.append(f"E3 {r['table']}: {blank:,} rows have no value for "
                         f"the natural id - those events cannot be referenced")

    return fails, warns


def gap_report():
    """Event tables with neither a natural nor a registered surrogate id."""
    if not CONTRACTS.exists():
        return []
    doc = json.loads(CONTRACTS.read_text(encoding="utf-8"))
    registered = {r["table"] for r in REGISTRY}
    gaps = []
    for coll in doc.get("contracts", []):
        for t in coll.get("tables", []):
            if t.get("status") != "shippable" or t["table"] in registered:
                continue
            grain = (t.get("grain") or "").lower()
            # a PANEL says so in its grain; anything "one X per event/filing/
            # award/payment/transaction" is an event table
            if any(w in grain for w in ("per year", "per entity-year",
                                        "one row per year", "panel")):
                continue
            if any(w in grain for w in ("transaction", "award", "filing",
                                        "notice", "decision", "payment",
                                        "deal", "event", "claim", "grant")):
                gaps.append((coll["collection"], t["table"],
                             "+".join(t.get("primary_key") or []) or "NO PK"))
    return gaps


def main() -> int:
    verify = len(sys.argv) > 1 and sys.argv[1] == "verify"
    fails, warns = check()
    gaps = gap_report()

    if not verify:
        OUT.parent.mkdir(parents=True, exist_ok=True)
        cols = ["dataset", "event", "table", "prefix", "kind", "columns",
                "note", "registered_date"]
        with OUT.open("w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
            w.writeheader()
            for r in REGISTRY:
                w.writerow({**r, "columns": "+".join(r["columns"]),
                            "registered_date": TODAY})

        L = ["# Event IDs — the *thing*, alongside the *who*", "",
             f"*Generated {TODAY} by `code/525_event_ids.py`. `cedar_uid` says "
             f"WHO (dataset 13, the hub). This says WHAT HAPPENED, and keeps "
             f"the two namespaces from colliding.*", "",
             "**A natural key beats a surrogate every time.** Where the source "
             "already assigns a stable id, that IS the event id and we mint "
             "nothing — a surrogate beside a good natural key is two ids for "
             "one thing.", "",
             "| dataset | event | prefix | kind | key |",
             "|---|---|---|---|---|"]
        for r in REGISTRY:
            L.append(f"| {r['dataset']} | {r['event']} | "
                     f"`{r['prefix'] or '—'}` | **{r['kind']}** | "
                     f"`{'+'.join(r['columns'])}` |")
        L += ["", "## Why some tables get no event id", "",
              "A **panel** (a measure per entity × period) has the dimensions "
              "as its key. Minting a surrogate would let a buyer believe two "
              "rows are different events when they are one measure — the trap "
              "the grain sweep found in `contractor_ranking.csv`, whose only "
              "unique keys required a *measure*.", ""]
        if gaps:
            L += ["## Event tables with no registered id yet", "",
                  "| collection | table | current PK |", "|---|---|---|"]
            for c, tb, pk in gaps:
                L.append(f"| {c} | `{tb}` | `{pk}` |")
        OUT_MD.write_text("\n".join(L), encoding="utf-8")

    kinds = Counter(r["kind"] for r in REGISTRY)
    print(f"  event id registry   {len(REGISTRY)} event types across "
          f"{len({r['dataset'] for r in REGISTRY})} datasets")
    print(f"                      natural {kinds['natural']}   surrogate "
          f"{kinds['surrogate']}   panel (no id, by decision) {kinds['panel']}")
    print(f"                      {len(gaps)} event table(s) with no "
          f"registered id yet")
    for f in fails:
        print(f"  FAIL  {f}")
    for w in warns[:6]:
        print(f"  warn  {w}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
