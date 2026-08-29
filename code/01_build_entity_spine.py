#!/usr/bin/env python3
"""
Cedar Press - 01: Build the entity spine and identifier ledger.

Cedar Press is self-contained: this script COPIES every external input into
data/raw/external/ and then builds only from those local copies. Re-running it
refreshes the copies. Nothing downstream ever reads outside Cedar Press.

Outputs
-------
data/spine/cedar_entity_spine.csv       one row per canonical Native entity
data/spine/cedar_identifier_ledger.csv  one row per (identifier, entity, evidence)
review/review_queue_<date>.csv          links needing an Elijah ruling

Prime directive: never falsely attribute. Every identifier->entity link carries
its attribution method, evidence, and a confidence tier. Only tier A ships.
"""

import csv
import shutil
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

CEDAR = Path(r"C:\Users\esm247\Desktop\Cedar Press")
EXT = CEDAR / "data" / "raw" / "external"
SPINE = CEDAR / "data" / "spine"
REVIEW = CEDAR / "review"
TODAY = date.today().isoformat()

FEDSPEND = Path(r"C:\Users\esm247\Desktop\dissertation\data\tribal_federal_spending")

# (source path, local filename, what it is)
INPUTS = [
    (FEDSPEND / "sam_extracts" / "canonical_tribe_table.csv",
     "canonical_tribe_table.csv", "CICD NEID spine, 687 entities"),
    (FEDSPEND / "sam_extracts" / "master_tribal_entity_registry_2026-05-06.csv",
     "master_tribal_entity_registry.csv", "UEI-level attribution ledger"),
    (FEDSPEND / "clean" / "native_entity_enterprise_dataset_v6_geocoded.csv",
     "need_v6_geocoded.csv", "NEED v6, 18,110 enterprises"),
    (FEDSPEND / "sam_extracts" / "anc_tribal_subsidiary_lookup.csv",
     "anc_tribal_subsidiary_lookup.csv", "ANC/tribal subsidiary parentage"),
    (FEDSPEND / "sam_extracts" / "sba_dsbs_native_entities_2026_04_30.csv",
     "sba_dsbs_native_entities.csv", "SBA DSBS Native 8(a) certified"),
    (FEDSPEND / "sam_extracts" / "hawaii_nho_candidates_2026_05_01.csv",
     "hawaii_nho_candidates.csv", "444 Hawaii NHO candidates"),
    (FEDSPEND / "sam_extracts" / "tribal_irs990_verified_strict_2026_04_30.csv",
     "tribal_irs990_verified_strict.csv", "1,090 verified tribal EINs"),
]

# Confidence tiers. Tier A ships. Tier B goes to Elijah. Tier C is discovery.
TIER = {
    "hand":                     ("A", "Manual attribution with citation"),
    "web_verified":             ("A", "Verified against a retrieved source"),
    "subsidiary_lookup":        ("A", "Structural parent->child, documented"),
    "sam_namematch_2026_05_06": ("B", "SAM legal-name match, unreviewed"),
    "cluster_v3":               ("B", "Algorithmic name clustering, unreviewed"),
    "unmatched":                ("C", "No attribution - discovery candidate"),
}


def log(msg):
    print(msg, flush=True)


def read_csv(path):
    with open(path, "r", encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def write_csv(path, rows, fields):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    log(f"  wrote {path.relative_to(CEDAR)}  ({len(rows):,} rows)")


def stage_inputs():
    """Copy every external input into Cedar Press so the folder is self-contained."""
    EXT.mkdir(parents=True, exist_ok=True)
    manifest = []
    for src, name, desc in INPUTS:
        dst = EXT / name
        if not src.exists():
            log(f"  MISSING: {src}")
            manifest.append({"local_file": name, "source_path": str(src),
                             "description": desc, "status": "MISSING",
                             "rows": "", "copied_date": TODAY})
            continue
        shutil.copy2(src, dst)
        n = sum(1 for _ in open(dst, encoding="utf-8-sig")) - 1
        log(f"  staged {name}  ({n:,} rows)")
        manifest.append({"local_file": name, "source_path": str(src),
                         "description": desc, "status": "OK",
                         "rows": n, "copied_date": TODAY})
    write_csv(EXT / "_SOURCE_MANIFEST.csv", manifest,
              ["local_file", "source_path", "description", "status", "rows", "copied_date"])
    return {m["local_file"]: m["status"] for m in manifest}


def build():
    log("\n=== Cedar Press: entity spine build ===")
    log(f"date: {TODAY}\n")

    log("[1] Staging external inputs into Cedar Press")
    status = stage_inputs()

    log("\n[2] Loading spine sources")
    cedar_em = read_csv(CEDAR / "entity_master.csv")
    canon = read_csv(EXT / "canonical_tribe_table.csv")
    registry = read_csv(EXT / "master_tribal_entity_registry.csv")
    need = read_csv(EXT / "need_v6_geocoded.csv")
    bgov = read_csv(CEDAR / "entity_crosswalk_bgov.csv")
    log(f"  cedar entity_master : {len(cedar_em):,}")
    log(f"  canonical (NEID)    : {len(canon):,}")
    log(f"  UEI registry        : {len(registry):,}")
    log(f"  NEED v6 enterprises : {len(need):,}")
    log(f"  BGOV crosswalk      : {len(bgov):,}")

    # ---- entity spine -----------------------------------------------------
    # NEID is the backbone. Cedar Entity_IDs attach to it, never replace it.
    log("\n[3] Building entity spine (NEID backbone)")
    spine = {}
    for r in canon:
        tid = r["tribe_id"].strip()
        if not tid:
            continue
        aliases = [r.get("entity_namefull", ""), r.get("fedreg_nameaka", ""),
                   r.get("fedreg_nameprev", ""), r.get("biatld_nameshort", "")]
        spine[tid] = {
            "tribe_id": tid,
            "canonical_name": r.get("canonical_name", "").strip(),
            "entity_class": r.get("entity_type", "").strip(),
            "state": r.get("entity_state", "").strip(),
            "bia_region": r.get("biatld_region", "").strip(),
            "self_governance": r.get("biaosg_selfgov", "").strip(),
            "aliases": " | ".join(sorted({a.strip() for a in aliases if a.strip()})),
            "cedar_entity_id": "",
            "n_uei_tierA": 0, "n_uei_tierB": 0,
            "n_cage": 0, "n_ein": 0,
        }

    # Link Cedar Entity_IDs onto the NEID spine via the existing NEID column.
    neid_col = "NEID (CICD connector)"
    linked = 0
    for r in cedar_em:
        neid = (r.get(neid_col) or "").strip()
        if neid and neid in spine:
            spine[neid]["cedar_entity_id"] = r.get("Entity_ID", "").strip()
            linked += 1
    log(f"  spine entities        : {len(spine):,}")
    log(f"  Cedar IDs linked      : {linked:,} / {len(cedar_em):,}")

    # ---- identifier ledger ------------------------------------------------
    log("\n[4] Building identifier ledger")
    ledger = []

    # UEI links from the registry, tiered by attribution method.
    for r in registry:
        uei = (r.get("uei") or "").strip()
        tid = (r.get("tribe_id") or "").strip()
        method = (r.get("attribution_method") or "unmatched").strip()
        tier, rationale = TIER.get(method, ("B", "Unrecognized method - review"))
        if not tid or tid not in spine:
            tier = "C"
        ledger.append({
            "identifier_type": "UEI",
            "identifier": uei,
            "tribe_id": tid,
            "canonical_name": (r.get("canonical_name") or "").strip(),
            "legal_business_name": (r.get("legal_business_name") or "").strip(),
            "entity_class": (r.get("parent_entity_type") or "").strip(),
            "attribution_method": method,
            "confidence_tier": tier,
            "tier_rationale": rationale,
            "evidence_url": (r.get("attribution_source_url") or "").strip(),
            "verified_date": (r.get("verified_date") or "").strip(),
            "state": (r.get("physical_state") or "").strip(),
            "prime_dollars_M": (r.get("total_master_prime_dol_M") or "").strip(),
            "source_file": "master_tribal_entity_registry.csv",
        })
        if tid in spine:
            if tier == "A":
                spine[tid]["n_uei_tierA"] += 1
            elif tier == "B":
                spine[tid]["n_uei_tierB"] += 1

    # CAGE + EIN from NEED v6.
    for r in need:
        tid = (r.get("tribe_id") or "").strip()
        name = (r.get("enterprise_name") or "").strip()
        method = (r.get("attribution_method") or "").strip() or "need_v6"
        tier, rationale = TIER.get(method, ("B", "NEED v6 attribution - review"))
        if not tid or tid not in spine:
            tier = "C"
        for idtype, col in (("CAGE", "enterprise_cage_code"), ("EIN", "enterprise_ein")):
            val = (r.get(col) or "").strip()
            if not val:
                continue
            ledger.append({
                "identifier_type": idtype,
                "identifier": val,
                "tribe_id": tid,
                "canonical_name": (r.get("canonical_name") or "").strip(),
                "legal_business_name": name,
                "entity_class": (r.get("entity_type_normalized") or "").strip(),
                "attribution_method": method,
                "confidence_tier": tier,
                "tier_rationale": rationale,
                "evidence_url": (r.get("verification_source") or "").strip(),
                "verified_date": (r.get("verified_date") or "").strip(),
                "state": (r.get("hq_state") or "").strip(),
                "prime_dollars_M": (r.get("total_master_prime_dol_M") or "").strip(),
                "source_file": "need_v6_geocoded.csv",
            })
            if tid in spine and tier == "A":
                spine[tid]["n_cage" if idtype == "CAGE" else "n_ein"] += 1

    # Historical CAGE/DUNS from the BGOV crosswalk (pre-2022 identifiers).
    for r in bgov:
        cages = (r.get("CAGE_Codes") or "").strip()
        tribe = (r.get("Tribe (as in BGOV file)") or "").strip()
        if not cages:
            continue
        for cage in [c.strip() for c in cages.replace(";", ",").split(",") if c.strip()]:
            ledger.append({
                "identifier_type": "CAGE",
                "identifier": cage,
                "tribe_id": "",
                "canonical_name": tribe,
                "legal_business_name": (r.get("Performing_Vendor") or "").strip(),
                "entity_class": "BGOV tribal vendor",
                "attribution_method": "bgov_manual",
                "confidence_tier": "A",
                "tier_rationale": "Elijah's manual BGOV tribe->vendor crosswalk",
                "evidence_url": "",
                "verified_date": "",
                "state": (r.get("Vendor_States") or "").strip(),
                "prime_dollars_M": "",
                "source_file": "entity_crosswalk_bgov.csv",
            })

    fields = ["identifier_type", "identifier", "tribe_id", "canonical_name",
              "legal_business_name", "entity_class", "attribution_method",
              "confidence_tier", "tier_rationale", "evidence_url",
              "verified_date", "state", "prime_dollars_M", "source_file"]
    write_csv(SPINE / "cedar_identifier_ledger.csv", ledger, fields)

    spine_fields = ["tribe_id", "canonical_name", "entity_class", "state",
                    "bia_region", "self_governance", "cedar_entity_id",
                    "n_uei_tierA", "n_uei_tierB", "n_cage", "n_ein", "aliases"]
    write_csv(SPINE / "cedar_entity_spine.csv",
              sorted(spine.values(), key=lambda x: x["canonical_name"]), spine_fields)

    # ---- review queue -----------------------------------------------------
    log("\n[5] Building review queue (tier B only)")
    tierB = [r for r in ledger if r["confidence_tier"] == "B"]
    # Rank by dollars at stake so the highest-consequence rulings come first.
    def dollars(r):
        try:
            return float(r["prime_dollars_M"] or 0)
        except ValueError:
            return 0.0
    tierB.sort(key=dollars, reverse=True)
    for i, r in enumerate(tierB, 1):
        r["review_id"] = f"RV-{i:05d}"
        r["question"] = (f"Is '{r['legal_business_name'] or r['identifier']}' "
                         f"({r['identifier_type']} {r['identifier']}) genuinely owned by "
                         f"{r['canonical_name'] or 'this entity'}?")
        r["YOUR_RULING"] = ""
    write_csv(REVIEW / f"review_queue_{TODAY}.csv", tierB,
              ["review_id", "identifier_type", "identifier", "legal_business_name",
               "canonical_name", "tribe_id", "entity_class", "attribution_method",
               "state", "prime_dollars_M", "evidence_url", "question", "YOUR_RULING"])

    # ---- summary ----------------------------------------------------------
    tiers = Counter(r["confidence_tier"] for r in ledger)
    bytype = Counter((r["identifier_type"], r["confidence_tier"]) for r in ledger)
    log("\n=== SUMMARY ===")
    log(f"spine entities        : {len(spine):,}")
    log(f"identifier links      : {len(ledger):,}")
    for t in ("A", "B", "C"):
        log(f"  tier {t}              : {tiers[t]:,}")
    log("")
    for idt in ("UEI", "CAGE", "EIN"):
        log(f"  {idt:4s}  A={bytype[(idt,'A')]:>6,}  B={bytype[(idt,'B')]:>6,}  C={bytype[(idt,'C')]:>6,}")
    log(f"\nreview queue          : {len(tierB):,} items awaiting your ruling")
    dollars_at_stake = sum(dollars(r) for r in tierB)
    log(f"dollars at stake in B : ${dollars_at_stake:,.0f}M")
    log("\nOnly tier A is publishable. Tier B ships nothing until ruled.")


if __name__ == "__main__":
    try:
        build()
    except Exception as exc:
        log(f"\nFAILED: {type(exc).__name__}: {exc}")
        raise
