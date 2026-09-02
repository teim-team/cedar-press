#!/usr/bin/env python3
"""
329 — merge the White Earth Nation TERO register into the tribal certification
tables (the 316-324 track).

WHY THIS MATTERS. `tribal_certification_rules` holds 14 rules and
`tribal_certification_facts` holds a FOUR-ROW SAMPLE, all four of them ANC
subsidiaries. The rules and the source survey are built; the facts are not.
White Earth adds:

  - the 15th rule, and the ONLY one carrying a quantified bid-price preference
    schedule (10% under $100k sliding to 1.5% over $7M);
  - the first 22 facts about INDIVIDUALLY-OWNED Native businesses rather than
    corporate subsidiaries, which is the dataset this track exists to build.

The evidence leg is THIRD_PARTY_TRIBAL_GOVT — a tribal government certifying a
business is a third party with authority over the question. That is the tier-A
leg the whole track was created to get, and we have almost none of it.

INPUT (restricted, deliberately outside the public repo):
  data/restricted/white_earth_2026-08-28/TBD-113_white_earth.jsonl
  data/restricted/white_earth_2026-08-28/certification_rules.json

OUTPUT (staging, dated; the 2026-08-26 sample file is left untouched):
  data/staging/tribal_vendor_lists/tribal_certification_facts_2026-08-28.csv
  data/staging/tribal_vendor_lists/tribal_certification_rules_2026-08-28.csv

NETWORK: none.

JOIN DISCIPLINE. These 22 rows carry NO UEI and NO CAGE — the register does not
publish them. So the only available join to prime_contracts is by name, and
AGENTS.md forbids a containment matcher from keying a dollar. This script
therefore does an EXACT normalized-name-plus-state match ONLY, and records the
result as `NAME_ONLY_CANDIDATE` — never an attribution, never a tier. A match
here is a lead for a human, not evidence.

Usage:  py -3 code/329_merge_white_earth_into_certification_facts.py [--write]
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESTRICTED = os.path.join(ROOT, "data", "restricted", "white_earth_2026-08-28")
STAGING = os.path.join(ROOT, "data", "staging", "tribal_vendor_lists")

AUTHORITY_ENTITY_ID = "CNSF-MINNCH-WE"      # constituent band of TRBF-MINNCH-00
AUTHORITY_NAME = "White Earth Nation"
PARENT_ENTITY_ID = "TRBF-MINNCH-00"         # Minnesota Chippewa Tribe
SOURCE_ID = "TCS-CNSF-MINNCH-WE"
CAPTURE = "2026-08-28"

FACT_COLS = [
    "certification_fact_id", "certification_source_id",
    "certifying_authority_entity_id", "certifying_authority_name",
    "asserted_firm_name", "identifier_type", "identifier",
    "secondary_identifier_type", "secondary_identifier", "assertion_class",
    "assertion_verbatim", "assertion_source_url", "capture_date",
    "first_seen", "last_seen", "certification_status", "evidence_leg",
    "join_outcome", "prime_rows_matched", "prime_obligations_usd_matched",
    "prime_current_tier", "prime_current_attributed_entity", "value_added",
    "consent_status", "suppression_key", "publishable", "staged_by",
    # --- directory columns, added 2026-08-28 -------------------------------
    # The product is a usable directory of Native-owned businesses: a
    # subscriber must be able to identify the owner, see the tribal
    # affiliation, put the firm on a map, and CONTACT it. Those are the
    # deliverable, not incidental metadata. The existing four sample rows are
    # ANC subsidiaries and carry none of this, so the columns are simply empty
    # for them -- an absent value, never a fabricated one.
    "owner_name", "tribal_affiliation_raw",
    "address_raw", "city", "state_province", "postal_code",
    "phone", "email", "website",
    "geocode_status", "latitude", "longitude",
]

csv.field_size_limit(10_000_000)


def norm(s: str) -> str:
    """Normalize a firm name for EXACT comparison only. Never for containment."""
    s = (s or "").lower()
    s = re.sub(r"[.,]", " ", s)
    s = re.sub(r"\b(llc|l l c|inc|incorporated|corp|corporation|co|company|"
               r"ltd|limited|lp|llp|pllc)\b", " ", s)
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def load_white_earth():
    p = os.path.join(RESTRICTED, "TBD-113_white_earth.jsonl")
    with open(p, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def load_rules():
    p = os.path.join(RESTRICTED, "certification_rules.json")
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def index_prime():
    """
    Exact normalized-name -> aggregated prime facts, restricted to MN so a
    common name in another state cannot collide. Returns {} if unavailable.
    """
    p = os.path.join(ROOT, "data", "clean", "prime_contracts.csv")
    if not os.path.exists(p):
        print("  prime_contracts.csv not found - join skipped", file=sys.stderr)
        return {}
    idx = {}
    with open(p, encoding="utf-8", errors="replace", newline="") as f:
        r = csv.reader(f)
        hdr = next(r)
        I = {c: i for i, c in enumerate(hdr)}
        need = ["awardee_name", "total_obligations"]
        missing = [c for c in need if c not in I]
        if missing:
            # Loud, and it does NOT silently become "0 matches" downstream --
            # a join that never ran must never be reported as a null result.
            print(f"  prime_contracts missing {missing} - join skipped",
                  file=sys.stderr)
            return None
        st_col = I.get("recipient_state_code")
        tier_col = I.get("confidence_tier")
        ent_col = I.get("canonical_name")
        for row in r:
            try:
                st = (row[st_col].strip().upper() if st_col is not None else "")
                if st and st != "MN":
                    continue
                k = norm(row[I["awardee_name"]])
                if not k:
                    continue
                d = idx.setdefault(k, {"rows": 0, "usd": 0.0, "tier": "", "ent": ""})
                d["rows"] += 1
                try:
                    d["usd"] += float(row[I["total_obligations"]] or 0)
                except ValueError:
                    pass
                if tier_col is not None and not d["tier"]:
                    d["tier"] = row[tier_col].strip()
                if ent_col is not None and not d["ent"]:
                    d["ent"] = row[ent_col].strip()
            except IndexError:
                continue
    return idx


def build_rule_row(rules):
    ladder = rules["contracting_preference_ladder"]
    sched = rules["percentage_preference_schedule"]
    tiers = " | ".join(
        f"L{v['level']} (ordinance category {v['ordinance_category']}): "
        f"{'certified' if v['certified'] else 'NON-certified'}, principal place "
        f"{'ON' if v['principal_place_on_reservation'] else 'OFF'} reservation"
        for v in sorted(ladder.values(), key=lambda x: x["level"])
    )
    sched_txt = "; ".join(
        f"<${s['contract_max_usd']:,}: {s['bid_preference_pct']}%" if s["contract_max_usd"]
        else f">=${s['contract_min_usd']:,}: {s['bid_preference_pct']}%"
        for s in sched
    )
    return {
        "certification_rule_id": f"TCR-{AUTHORITY_ENTITY_ID}",
        "certifying_authority_entity_id": AUTHORITY_ENTITY_ID,
        "certifying_authority_name": AUTHORITY_NAME,
        "programme_name_as_they_call_it":
            "Certified Indian Owned Businesses / White Earth TERO",
        "programme_slug": "white-earth-tero",
        "rule_verdict": "RULE_FOUND",
        "assertion_class": "OWNERSHIP",
        "authority_citation":
            "White Earth TERO Ordinance (2026), Chapter 6 Scope of Indian "
            "Preference; Chapter 20 Indian Preference Guidelines",
        "authority_url": "https://www.whiteearth.com/divisions/human-services/workforce-center",
        "capture_date": CAPTURE,
        "ownership_pct_required": "YES",
        "ownership_pct_floor_numeric": "0.51",
        "ownership_pct_threshold": "51% actual management and control",
        "is_graded": "YES",
        "whose_ownership":
            "enrolled Indian owners, WITHOUT REGARD TO TRIBAL AFFILIATION "
            "(the ordinance defines Indian Preference that way) - this is NOT a "
            "White Earth citizen list",
        "tiers": tiers,
        "control_requirement":
            "At least 51% actual management AND control by enrolled Indian "
            "owners; certification by the White Earth TERO Commission",
        "enrollment_requirement":
            "Enrolled Indian; tribal affiliation not restricted to White Earth",
        "residency_or_onreservation_requirement":
            "Not required for certification, but principal place of business ON "
            "the Reservation or Tribal Trust Land raises the preference level "
            "(category C over D)",
        "verification_method":
            "TERO Commission reviews applications and supporting documentation "
            "and may investigate; may suspend or revoke on changed circumstances",
        "renewal_cadence":
            "Rolling per-firm expiration dates (observed 2027-01 through 2029-12)",
        "expiry_terms": "Per-firm expiration stated on the register",
        "verbatim_quote": ladder["1st"]["text"],
        "verbatim_quote_2": (
            "SCHEDULE OF PERCENTAGE PREFERENCE (granted ABOVE the lowest "
            "responsible bid, in preference-level order): " + sched_txt +
            ". A Category C bidder must submit a timely responsible sealed bid "
            "and CANNOT match the low bid after the low bid is known."
        ),
        "quote_source_url": "https://www.whiteearth.com/divisions/human-services/workforce-center",
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args()

    recs = load_white_earth()
    rules = load_rules()
    print(f"White Earth: {len(recs)} layer-1 records, "
          f"{len(rules['contracting_preference_ladder'])} preference levels")

    print("indexing prime_contracts (MN only, exact name)...")
    prime = index_prime()
    if prime is None:
        # Distinguish "the join found nothing" from "the join could not run".
        print("  JOIN UNAVAILABLE -- outcomes recorded as JOIN_NOT_RUN",
              file=sys.stderr)
    else:
        print(f"  {len(prime):,} distinct MN normalized names")

    facts = []
    joined = 0
    for rec in recs:
        nm = rec["business_name_raw"]
        key = norm(nm)
        hit = prime.get(key) if prime is not None else None
        if prime is None:
            outcome = "JOIN_NOT_RUN"
            rows_m, usd_m, tier, ent = "", "", "", ""
            value = "UNKNOWN_JOIN_NOT_RUN"
        elif hit:
            joined += 1
            outcome = "NAME_ONLY_CANDIDATE"
            rows_m, usd_m = str(hit["rows"]), f"{hit['usd']:.2f}"
            tier, ent = hit["tier"], hit["ent"]
            value = "REVIEW_REQUIRED_NAME_ONLY"
        else:
            outcome = "NO_PRIME_MATCH"
            rows_m, usd_m, tier, ent = "0", "0.00", "", ""
            value = "NEW_FIRM_NOT_IN_PRIME"

        facts.append({
            "certification_fact_id":
                f"TCF-{AUTHORITY_ENTITY_ID}-NAME-{re.sub(r'[^A-Z0-9]+','', nm.upper())[:18]}",
            "certification_source_id": SOURCE_ID,
            "certifying_authority_entity_id": AUTHORITY_ENTITY_ID,
            "certifying_authority_name": AUTHORITY_NAME,
            "asserted_firm_name": nm,
            # The register publishes no UEI or CAGE. Say so; do not invent a key.
            "identifier_type": "NAME",
            "identifier": nm,
            "secondary_identifier_type": "",
            "secondary_identifier": "",
            "assertion_class": "OWNERSHIP",
            "assertion_verbatim": rec["identity_claim_text"],
            "assertion_source_url": rec["source_url"],
            "capture_date": CAPTURE,
            "first_seen": CAPTURE,
            "last_seen": CAPTURE,
            "certification_status": (
                f"CERTIFIED_EXPIRES_{rec['certification_expiration']}"
                if rec.get("certification_expiration") else "CERTIFIED_EXPIRY_UNKNOWN"
            ),
            # A tribal government certifying a business is a third party with
            # authority over the question. This is the tier-A leg.
            "evidence_leg": "THIRD_PARTY_TRIBAL_GOVT",
            "join_outcome": outcome,
            "prime_rows_matched": rows_m,
            "prime_obligations_usd_matched": usd_m,
            "prime_current_tier": tier,
            "prime_current_attributed_entity": ent,
            "value_added": value,
            # Publication rights are UNCONFIRMED and the roster names private
            # individuals. Suppressed until the Nation says otherwise.
            "consent_status": "UNRESOLVED_OWNER_SUPPLIED_COPY",
            "suppression_key": f"SUPPRESS::{AUTHORITY_ENTITY_ID}",
            "publishable": "N",
            "staged_by": "code/329_merge_white_earth_into_certification_facts.py",
            "owner_name": rec.get("owner_name_raw") or "",
            "tribal_affiliation_raw": rec.get("tribal_affiliation_raw") or "",
            "address_raw": rec.get("address_raw") or "",
            "city": rec.get("city") or "",
            "state_province": rec.get("state_province") or "",
            "postal_code": rec.get("postal_code") or "",
            "phone": rec.get("phone") or "",
            "email": rec.get("email") or "",
            "website": rec.get("website") or "",
            "geocode_status": "PENDING" if rec.get("address_raw") else "NO_ADDRESS",
            "latitude": "",
            "longitude": "",
        })

    print(f"\nfacts built: {len(facts)}")
    if prime is None:
        print("  prime join: NOT RUN (column mismatch) - not reported as zero")
    else:
        print(f"  exact name+MN match in prime_contracts: {joined}")
        print(f"  no prime match:                         {len(facts)-joined}")
    for lab, fld in [("owner name", "owner_name"), ("phone", "phone"),
                     ("email", "email"), ("address", "address_raw")]:
        n = sum(1 for r in facts if r[fld])
        print(f"  with {lab:11s}: {n}/{len(facts)}")
    print(f"  ALL rows publishable=N, consent UNRESOLVED (rights unconfirmed)")

    tiers = {}
    for rec in recs:
        t = rec.get("certification_tier") or "?"
        tiers[t] = tiers.get(t, 0) + 1
    print("  tier labels as printed:", json.dumps(tiers))

    if not a.write:
        print("\nDRY RUN -- pass --write")
        return 0

    # Facts: carry the existing sample forward into one current dated file.
    sample = os.path.join(STAGING, "tribal_certification_facts_sample_2026-08-26.csv")
    out_rows = []
    if os.path.exists(sample):
        out_rows.extend(csv.DictReader(open(sample, encoding="utf-8")))
    out_rows.extend(facts)
    fp = os.path.join(STAGING, "tribal_certification_facts_2026-08-28.csv")
    tmp = fp + ".part"
    with open(tmp, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FACT_COLS, extrasaction="ignore")
        w.writeheader()
        w.writerows(out_rows)
    os.replace(tmp, fp)
    print(f"\nwrote {len(out_rows)} facts -> {fp}")

    # Rules: same pattern.
    rsrc = os.path.join(STAGING, "tribal_certification_rules_2026-08-26.csv")
    rrows = list(csv.DictReader(open(rsrc, encoding="utf-8"))) if os.path.exists(rsrc) else []
    rcols = list(rrows[0].keys()) if rrows else list(build_rule_row(rules).keys())
    rrows.append(build_rule_row(rules))
    rp = os.path.join(STAGING, "tribal_certification_rules_2026-08-28.csv")
    tmp = rp + ".part"
    with open(tmp, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=rcols, extrasaction="ignore")
        w.writeheader()
        w.writerows(rrows)
    os.replace(tmp, rp)
    print(f"wrote {len(rrows)} rules -> {rp}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
