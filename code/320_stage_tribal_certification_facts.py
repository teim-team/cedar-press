"""320 - STAGE (never merge) the certification layer from the feasibility study.

Two files, and the difference between them is the whole design.

1. `tribal_certification_sources_2026-08-26.csv`
   One row per CERTIFYING AUTHORITY. Who asserts, about what class of thing,
   where, under what stated terms, captured when, and whether that source may
   be published. This is the citation spine of the whole layer.

2. `tribal_certification_facts_sample_2026-08-26.csv`
   Firm-level certification FACTS - "firm X is asserted by authority Y as of
   date Z, per this URL." This is what option B needs: the certification fact,
   not the tribe's directory.

   IT IS A SAMPLE AND IT SAYS SO IN ITS OWN FILENAME. Only rows whose
   identifier was READ FROM THE SOURCE and then TESTED against
   `prime_contracts.csv` are here. A feasibility study measures; harvesting is
   the next pass and needs the consent question answered first.

WHY EVERY ROW CARRIES A CAPTURE DATE
------------------------------------
Wayback is a FEATURE here, not a fallback: a longitudinal record of tribal
business certification - who was certified when, who entered, who lapsed - does
not exist anywhere. The schema is built for it from the first row:
`capture_date`, `first_seen`, `last_seen`, and a `certification_status` that
can say certified-in-2018-and-not-in-2026 WITHOUT ever presenting a historical
snapshot as current. Two rules are enforced by the columns rather than by
memory:

  * Never present a historical snapshot as current.
  * Never rule a current page against a historical record, or the reverse.

CONSENT IS A COLUMN, NOT A PARAGRAPH
------------------------------------
`source_terms_status`, `consent_status`, `suppression_key` and `publishable`
travel with every row. Silence is UNRESOLVED, never permission. Flipping one
`consent_status` field removes - or, if a TERO office says yes, admits - an
entire tribe's rows. `321_gate_tribal_source_restriction.py` fails a build that
tries to publish an unresolved row, in the same machinery as the Casino City
`LICENSED_SOURCE_FILES` gate and the D&B pre-2022 restriction, rather than as
documentation somebody has to remember.

STAGED, NEVER MERGED. Nothing here is written to `data/clean/`.
"""

from __future__ import annotations

import csv
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "review" / "tribal_vendor_list_registry_2026-08-26.csv"
PRIME = ROOT / "data" / "clean" / "prime_contracts.csv"
STAGE = ROOT / "data" / "staging" / "tribal_vendor_lists"

SCRIPT = "320_stage_tribal_certification_facts.py"
CAPTURE_DATE = "2026-08-26"

SOURCES_OUT = STAGE / f"tribal_certification_sources_{CAPTURE_DATE}.csv"
FACTS_OUT = STAGE / f"tribal_certification_facts_sample_{CAPTURE_DATE}.csv"

SOURCE_COLUMNS = [
    "certification_source_id",
    "certifying_authority_entity_id",     # spine tribe_id - the AUTHORITY
    "certifying_authority_name",
    "authority_class",                    # TRIBAL_GOVERNMENT | ANCSA_CORPORATION
    "programme_name",                     # what the authority calls it
    "assertion_class",                    # OWNERSHIP | RELATIONSHIP | OPERATING_ON_LAND | NONE
    "list_type",
    "list_url",
    "list_format",
    "entry_count_approx",
    "entry_count_is_verified",            # Y | N  - a claimed count is not a counted one
    "identifiers_present",
    "carries_joinable_identifier",        # Y | N  - UEI/CAGE/EIN present
    "update_frequency",
    "verdict",
    "capture_date",
    "source_terms_status",
    "source_terms_quote",
    "consent_status",
    "suppression_key",
    "publishable",
    "robots_note",
    "notes",
    "staged_by",
]

FACT_COLUMNS = [
    "certification_fact_id",
    "certification_source_id",
    "certifying_authority_entity_id",
    "certifying_authority_name",
    "asserted_firm_name",
    "identifier_type",                    # UEI | CAGE | NONE
    "identifier",
    "secondary_identifier_type",
    "secondary_identifier",
    "assertion_class",
    "assertion_verbatim",                 # the source's OWN words
    "assertion_source_url",
    "capture_date",
    "first_seen",
    "last_seen",
    "certification_status",               # ASSERTED_AS_OF_CAPTURE | LAPSED_BY_CAPTURE | UNKNOWN
    "evidence_leg",                       # THIRD_PARTY_PARENT | THIRD_PARTY_TRIBAL_GOVT | SELF
    # measured at build time against prime_contracts.csv, never hand-typed
    "join_outcome",                       # RESOLVES_EXISTING | RESOLVES_UNATTRIBUTED |
                                          # NO_MATCH_IN_PRIME | CANDIDATE_ONLY_NO_IDENTIFIER
    "prime_rows_matched",
    "prime_obligations_usd_matched",
    "prime_current_tier",
    "prime_current_attributed_entity",
    "value_added",                        # NEW_ATTRIBUTION | INDEPENDENT_CORROBORATION | NONE
    "consent_status",
    "suppression_key",
    "publishable",
    "staged_by",
]

# --------------------------------------------------------------------------
# The firm-level facts VERIFIED in the 2026-08-26 discovery pass. Each was read
# off the certifying party's own page, with the identifier printed there.
# Nothing is inferred and nothing is name-matched.
# --------------------------------------------------------------------------
FACTS = [
    dict(certifying_authority_entity_id="ANRC-DOYONL-00",
         asserted_firm_name="Doyon Project Services, LLC",
         identifier_type="UEI", identifier="F9M5KXFBC8N3",
         secondary_identifier_type="CAGE", secondary_identifier="3Q5W1",
         assertion_verbatim=(
             "Doyon Project Services, LLC (DPS) is a Minority-Owned, Small "
             "Disadvantaged Business and a subsidiary of Doyon, Limited, an "
             "Alaska Native Corporation (ANC)."),
         assertion_source_url=(
             "https://www.doyongovgrp.com/wp-content/uploads/2026/05/"
             "Doyon-Project-Services-Capability-Statement.pdf"),
         evidence_leg="THIRD_PARTY_PARENT"),
    dict(certifying_authority_entity_id="ANRC-ARCSLO-00",
         asserted_firm_name="ASRC Federal NetCentric Technology, LLC",
         identifier_type="UEI", identifier="T65LCYKJCW58",
         secondary_identifier_type="CAGE", secondary_identifier="1R5E0",
         assertion_verbatim=(
             "Subsidiary page publishes the firm's CAGE 1R5E0, UEI "
             "T65LCYKJCW58 and DUNS 113807676 alongside its PARENT's CAGE "
             "3JA23, UEI VYN3SB8H8BL7 and DUNS 135908783 - the corporation "
             "asserting both sides of the ownership link with identifiers."),
         assertion_source_url=(
             "https://www.asrcfederal.com/contract-vehicles/"),
         evidence_leg="THIRD_PARTY_PARENT"),
    dict(certifying_authority_entity_id="ANRC-ARCSLO-00",
         asserted_firm_name="ASRC Federal Holding Company, LLC",
         identifier_type="UEI", identifier="VYN3SB8H8BL7",
         secondary_identifier_type="CAGE", secondary_identifier="3JA23",
         assertion_verbatim=(
             "Named as the PARENT on the subsidiary's own page, with UEI and "
             "CAGE printed."),
         assertion_source_url=(
             "https://www.asrcfederal.com/contract-vehicles/"),
         evidence_leg="THIRD_PARTY_PARENT"),
    dict(certifying_authority_entity_id="ANRC-NANARC-00",
         asserted_firm_name="Nakuuruq Solutions, LLC",
         identifier_type="UEI", identifier="FZYKN78D9LJ2",
         secondary_identifier_type="CAGE", secondary_identifier="3NCA0",
         assertion_verbatim=(
             "Akima operating-company page publishes CAGE 3NCA0, UEI "
             "FZYKN78D9LJ2, DUNS 141090170, primary NAICS 517112, 8(a) "
             "Direct Award status and a street address, under Akima LLC, "
             "the federal arm of NANA Regional Corporation."),
         assertion_source_url="https://www.akima.com/opcos/nakuuruq/",
         evidence_leg="THIRD_PARTY_PARENT"),
]


def _require(row, cols, where):
    missing = [c for c in cols if c not in row]
    if missing:
        raise KeyError(f"{where} is missing column(s) {missing}.")


def load_registry():
    if not REGISTRY.exists():
        raise SystemExit(f"{REGISTRY} absent - run 316 then 319 first")
    with REGISTRY.open(encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh))
    if rows:
        _require(rows[0], ["tribe_id", "canonical_name", "entity_class",
                           "verdict", "list_type", "assertion_class",
                           "list_url", "list_format", "entry_count_approx",
                           "identifiers_present", "update_frequency",
                           "source_terms_status", "consent_status",
                           "suppression_key", "publishable", "robots_note",
                           "notes"], str(REGISTRY))
    return rows


def scan_prime(wanted_uei, wanted_cage):
    """Measure the join, never assume it."""
    by_uei = defaultdict(lambda: {"rows": 0, "usd": 0.0,
                                  "tiers": defaultdict(int),
                                  "att": defaultdict(int),
                                  "entity": defaultdict(int)})
    by_cage = defaultdict(lambda: {"rows": 0, "usd": 0.0,
                                   "att": defaultdict(int)})
    with PRIME.open(encoding="utf-8", errors="replace", newline="") as fh:
        rdr = csv.DictReader(fh)
        first = next(rdr, None)
        if first is None:
            raise SystemExit(f"{PRIME} is empty")
        _require(first, ["awardee_uei", "cage_code", "total_obligations",
                         "confidence_tier", "attributed_flag",
                         "canonical_name"], str(PRIME))
        for row in [first] + list(rdr):
            u = (row["awardee_uei"] or "").strip().upper()
            c = (row["cage_code"] or "").strip().upper()
            try:
                usd = float(row["total_obligations"] or 0)
            except ValueError:
                usd = 0.0
            if u in wanted_uei:
                d = by_uei[u]
                d["rows"] += 1
                d["usd"] += usd
                d["tiers"][row["confidence_tier"] or "(blank)"] += 1
                d["att"][row["attributed_flag"]] += 1
                d["entity"][row["canonical_name"] or "(none)"] += 1
            if c in wanted_cage:
                d = by_cage[c]
                d["rows"] += 1
                d["usd"] += usd
                d["att"][row["attributed_flag"]] += 1
    return by_uei, by_cage


def main():
    reg = load_registry()
    by_id = {r["tribe_id"]: r for r in reg}
    STAGE.mkdir(parents=True, exist_ok=True)

    # ---------------------------------------------------------- sources ----
    src_rows, src_id_for = [], {}
    for r in sorted(reg, key=lambda x: x["tribe_id"]):
        # Keyed on the AUTHORITY, never on row position. A positional id
        # changes when a row is inserted, which silently repoints every
        # fact that cited it (defect class 7).
        sid = f"TCS-{r['tribe_id']}"
        src_id_for[r["tribe_id"]] = sid
        ident = (r["identifiers_present"] or "").upper()
        src_rows.append({
            "certification_source_id": sid,
            "certifying_authority_entity_id": r["tribe_id"],
            "certifying_authority_name": r["canonical_name"],
            "authority_class": ("ANCSA_CORPORATION"
                                if r["entity_class"].startswith("Alaska "
                                                                "Native "
                                                                "Regional")
                                else "TRIBAL_GOVERNMENT"),
            "programme_name": r["list_type"],
            "assertion_class": r["assertion_class"],
            "list_type": r["list_type"],
            "list_url": r["list_url"],
            "list_format": r["list_format"],
            "entry_count_approx": r["entry_count_approx"],
            # A claimed count is not a counted one, and the registry says which
            # is which in its own notes. Anything carrying a caveat word is N.
            "entry_count_is_verified": (
                "N" if (not r["entry_count_approx"]
                        or any(w in r["entry_count_approx"].lower()
                               for w in ("unknown", "claim", "not verified",
                                         "not enumerated", "-", "against")))
                else "Y"),
            "identifiers_present": r["identifiers_present"],
            "carries_joinable_identifier": (
                "Y" if any(k in ident for k in ("UEI", "CAGE", "EIN"))
                else "N"),
            "update_frequency": r["update_frequency"],
            "verdict": r["verdict"],
            "capture_date": CAPTURE_DATE,
            "source_terms_status": r["source_terms_status"],
            "source_terms_quote": r["source_terms_quote"],
            "consent_status": r["consent_status"],
            "suppression_key": r["suppression_key"],
            "publishable": r["publishable"],
            "robots_note": r["robots_note"],
            "notes": r["notes"],
            "staged_by": f"code/{SCRIPT}",
        })

    # ------------------------------------------------------------ facts ----
    want_u = {f["identifier"] for f in FACTS if f["identifier_type"] == "UEI"}
    want_c = {f["secondary_identifier"] for f in FACTS
              if f["secondary_identifier_type"] == "CAGE"}
    by_uei, by_cage = scan_prime(want_u, want_c)

    fact_rows = []
    for f in FACTS:
        tid = f["certifying_authority_entity_id"]
        reg_row = by_id.get(tid)
        if reg_row is None:
            raise SystemExit(f"fact names an entity absent from the "
                             f"registry: {tid}")
        m = by_uei.get(f["identifier"])
        if not m or m["rows"] == 0:
            outcome, tier, ent, rows_, usd = ("NO_MATCH_IN_PRIME", "", "",
                                              0, 0.0)
            value = "NONE"
        else:
            rows_ = m["rows"]
            usd = round(m["usd"], 2)
            tier = max(m["tiers"], key=lambda k: m["tiers"][k])
            ent = max(m["entity"], key=lambda k: m["entity"][k])
            unattributed = m["att"].get("0", 0)
            if unattributed == rows_:
                outcome, value = ("RESOLVES_UNATTRIBUTED", "NEW_ATTRIBUTION")
            elif unattributed:
                outcome, value = ("RESOLVES_UNATTRIBUTED",
                                  "NEW_ATTRIBUTION_PARTIAL")
            else:
                outcome, value = ("RESOLVES_EXISTING",
                                  "INDEPENDENT_CORROBORATION")
        fact_rows.append({
            # Keyed on (authority, identifier) - stable across rebuilds and
            # across insertions, unlike an enumerate() counter.
            "certification_fact_id":
                f"TCF-{tid}-{f['identifier_type']}-{f['identifier']}",
            "certification_source_id": src_id_for[tid],
            "certifying_authority_entity_id": tid,
            "certifying_authority_name": reg_row["canonical_name"],
            "asserted_firm_name": f["asserted_firm_name"],
            "identifier_type": f["identifier_type"],
            "identifier": f["identifier"],
            "secondary_identifier_type": f["secondary_identifier_type"],
            "secondary_identifier": f["secondary_identifier"],
            "assertion_class": "OWNERSHIP",
            "assertion_verbatim": f["assertion_verbatim"],
            "assertion_source_url": f["assertion_source_url"],
            "capture_date": CAPTURE_DATE,
            "first_seen": CAPTURE_DATE,
            "last_seen": CAPTURE_DATE,
            # One capture cannot establish a range. It says only what was
            # true at the capture, which is exactly what the value names.
            "certification_status": "ASSERTED_AS_OF_CAPTURE",
            "evidence_leg": f["evidence_leg"],
            "join_outcome": outcome,
            "prime_rows_matched": rows_,
            "prime_obligations_usd_matched": usd,
            "prime_current_tier": tier,
            "prime_current_attributed_entity": ent,
            "value_added": value,
            "consent_status": reg_row["consent_status"],
            "suppression_key": reg_row["suppression_key"],
            "publishable": reg_row["publishable"],
            "staged_by": f"code/{SCRIPT}",
        })

    for path, cols, rows in ((SOURCES_OUT, SOURCE_COLUMNS, src_rows),
                             (FACTS_OUT, FACT_COLUMNS, fact_rows)):
        part = path.with_suffix(path.suffix + ".part")
        with part.open("w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=cols)
            w.writeheader()
            w.writerows(rows)
        part.replace(path)
        with path.open(encoding="utf-8-sig", newline="") as fh:
            back = list(csv.DictReader(fh))
        if len(back) != len(rows):
            raise SystemExit(f"{path.name}: re-read {len(back)}, "
                             f"wrote {len(rows)}")
        print(f"  {path.relative_to(ROOT)}  ({len(back)} rows, re-read OK)")

    print(f"\n  sources with a joinable identifier: "
          f"{sum(1 for r in src_rows if r['carries_joinable_identifier'] == 'Y')}"
          f" of {len(src_rows)}")
    print("  fact join outcomes:")
    agg = defaultdict(lambda: [0, 0.0])
    for r in fact_rows:
        agg[r["join_outcome"]][0] += 1
        agg[r["join_outcome"]][1] += float(r["prime_obligations_usd_matched"])
    for k, (n, usd) in sorted(agg.items()):
        print(f"    {k:26s} {n:3d} facts  ${usd / 1e6:,.1f}M")
    print("  value added:")
    va = defaultdict(int)
    for r in fact_rows:
        va[r["value_added"]] += 1
    for k, n in sorted(va.items()):
        print(f"    {k:28s} {n}")
    print("\n  STAGED ONLY. Nothing written to data/clean/. "
          "publishable = N on every row until consent is resolved.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
