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


THIS SCRIPT APPEND-MERGES. IT USED TO REPLACE. (2026-09-01, workstream C8)
==========================================================================
Until today this was the most destructive runnable command in the repo after
`41_build_codebooks.py`, and its docstring did not say so. It built the spine
from `canonical_tribe_table.csv` alone - 687 rows, 12 columns - and wrote that
over a live hub of 1,555 rows and 44 columns in `"w"` mode. Measured by
`741_hub_grain_and_rebuild.py census` WITHOUT running it: a direct invocation
dropped **868 of 1,555 entities** (210 NHOs, 185 BIE schools, 173 ANC village
corporations, 64 Native CDFIs and more) and **32 of 44 columns, `cedar_uid`
among them**. Fifteen enrichers put those there; one command took them out.

The 687 rows were never the problem. The `"w"` was. So the computation is
unchanged and the WRITE is now `cedar_pipeline.merge_table`:

  * every live row survives, in its original order;
  * every live column survives - the merge raises rather than drop one;
  * a canonical entity not yet in the spine is APPENDED;
  * on a row that already exists, only BLANK cells are filled. This script
    overwrites nothing, because it owns nothing exclusively: `n_uei_tierA`,
    `n_uei_tierB`, `n_cage`, `n_ein`, `aliases`, `cedar_entity_id` and `state`
    are all written by later scripts too (52, 61, 71, 73, 75, 163, 241, 416,
    524 - checked by grep on 2026-09-01, not assumed). Where the rebuild
    disagrees with the live value the LIVE VALUE STANDS and the pair is
    written to `review/spine_merge_drift_<date>.csv`, so the disagreement is
    visible instead of being either applied silently or discarded silently.

`--dry-run` performs the whole computation and the whole merge and writes
NOTHING, reporting what the merge would do. That is the mode
`812_c8_rebuild_proof.py` uses to prove the rebuild reproduces the census
against the live tables without touching them.

Removed from `cedar_pipeline.NEVER_RUN` on 2026-09-01, and the guard came off
only AFTER the merge existed and the proof passed. The gate this must clear is
`docs/schema/hub_rebuild_census.json`: >= 1,555 rows and all 44 columns.
"""

import csv
import shutil
import sys
from collections import Counter
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from cedar_pipeline import clean_state, merge_table, write_table  # noqa: E402

CEDAR = Path(__file__).resolve().parent.parent
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

#: THE SPINE KEY. `tribe_id` is unique on all 1,555 live rows and blank on
#: none of them (checked 2026-09-01). It is the handle `503_identity.py` keys
#: `cedar_uid` on, so merging on anything else would split an entity from its
#: own uid.
SPINE_KEY = ["tribe_id"]

#: THE LEDGER KEY. 19,229 of 19,232 rows are unique on this tuple; the three
#: that are not are disambiguated by occurrence ordinal inside
#: `cedar_pipeline.ordinal_key`, because collapsing them would be a row loss
#: called deduplication.
LEDGER_KEY = ["identifier_type", "identifier", "tribe_id", "source_file"]

#: Columns this script may OVERWRITE on a row that already exists. It is
#: deliberately empty. See the module docstring: every column 01 computes is
#: also written by a later enricher, so overwriting any of them would revert
#: one - the defect `cedar_pipeline` exists to prevent.
SPINE_REFRESH = ()
LEDGER_REFRESH = ()


def log(msg):
    print(msg, flush=True)


def read_csv(path):
    with open(path, "r", encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def stage_inputs(dry_run=False):
    """Copy every external input into Cedar Press so the folder is self-contained.

    `dry_run` leaves the staged copies exactly as they are. A dry run must not
    change the inputs either: a proof that mutates what it is proving against
    has proved nothing.
    """
    EXT.mkdir(parents=True, exist_ok=True)
    manifest = []
    for src, name, desc in INPUTS:
        dst = EXT / name
        if dry_run:
            log(f"  [dry-run] not restaged: {name}"
                f"{'' if dst.exists() else '  (LOCAL COPY MISSING)'}")
            continue
        if not src.exists():
            # A missing SOURCE is not a missing INPUT while the local copy
            # stands - Cedar Press builds from the local copies by design.
            # Reporting it as MISSING outright would have said the spine
            # could not be built on any machine without the dissertation
            # folder mounted, which is false.
            status = ("SOURCE_UNREACHABLE_LOCAL_COPY_USED" if dst.exists()
                      else "MISSING")
            log(f"  {status}: {src}")
            n = (sum(1 for _ in open(dst, encoding="utf-8-sig")) - 1
                 if dst.exists() else "")
            manifest.append({"local_file": name, "source_path": str(src),
                             "description": desc, "status": status,
                             "rows": n, "copied_date": TODAY})
            continue
        shutil.copy2(src, dst)
        n = sum(1 for _ in open(dst, encoding="utf-8-sig")) - 1
        log(f"  staged {name}  ({n:,} rows)")
        manifest.append({"local_file": name, "source_path": str(src),
                         "description": desc, "status": "OK",
                         "rows": n, "copied_date": TODAY})
    # THE MANIFEST MERGES TOO, AND IT HAD TO. Measured 2026-09-01: the live
    # `_SOURCE_MANIFEST.csv` carries 11 rows and `INPUTS` above declares 7, so
    # a replacing write would have deleted the provenance of four staged
    # inputs this script no longer lists. Small, invisible, and exactly the
    # defect the rest of this file was rewritten to stop.
    _, _, rep = merge_table(
        EXT / "_SOURCE_MANIFEST.csv", manifest,
        ["local_file", "source_path", "description", "status", "rows",
         "copied_date"], ["local_file"],
        refresh=("source_path", "description", "status", "rows",
                 "copied_date"),
        dry_run=dry_run, backup_tag="pre01")
    log(f"  {rep}")
    return {m["local_file"]: m["status"] for m in manifest}


def build(dry_run=False):
    tag = "[DRY RUN - nothing is written] " if dry_run else ""
    log(f"\n=== Cedar Press: entity spine build (APPEND-MERGE) ===")
    log(f"{tag}date: {TODAY}\n")

    log("[1] Staging external inputs into Cedar Press")
    stage_inputs(dry_run=dry_run)

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
    log(f"  spine entities built  : {len(spine):,}")
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
            # A STATE COLUMN MAY ONLY HOLD A STATE. The external registry's
            # `physical_state` holds the row's OWN uei in 12,127 of 13,191 rows
            # (92%) and a real state in 134. Read straight through, that put
            # 12,127 identifiers into the `state` column of a table that SHIPS,
            # and nothing noticed for as long as this file has existed - a
            # buyer filtering the ledger by state would have got silence for
            # 59% of it and never learned why. Fixed in the live tables by
            # 71_fix_known_defects.py defect 5; guarded here so a rerun of
            # this script cannot bring it back.
            "state": clean_state(r.get("physical_state"), uei)[0],
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

    # ---- MERGE, not replace ----------------------------------------------
    log("\n[5] Merging into the live tables (append-merge, nothing replaced)")
    reports = {}

    ledger_fields = ["identifier_type", "identifier", "tribe_id", "canonical_name",
                     "legal_business_name", "entity_class", "attribution_method",
                     "confidence_tier", "tier_rationale", "evidence_url",
                     "verified_date", "state", "prime_dollars_M", "source_file"]
    _, _, rep_led = merge_table(
        SPINE / "cedar_identifier_ledger.csv", ledger, ledger_fields,
        LEDGER_KEY, refresh=LEDGER_REFRESH, dry_run=dry_run,
        backup_tag="pre01",
        drift_report=REVIEW / f"ledger_merge_drift_{TODAY}.csv")
    reports["cedar_identifier_ledger.csv"] = rep_led
    log(f"  {rep_led}")

    spine_fields = ["tribe_id", "canonical_name", "entity_class", "state",
                    "bia_region", "self_governance", "cedar_entity_id",
                    "n_uei_tierA", "n_uei_tierB", "n_cage", "n_ein", "aliases"]
    spine_rows = sorted(spine.values(), key=lambda x: x["canonical_name"])
    # `n_*` are ints; the merge compares strings, and 0 must not read as blank.
    for r in spine_rows:
        for c in ("n_uei_tierA", "n_uei_tierB", "n_cage", "n_ein"):
            r[c] = str(r[c])
    _, spine_out_fields, rep_spine = merge_table(
        SPINE / "cedar_entity_spine.csv", spine_rows, spine_fields,
        SPINE_KEY, refresh=SPINE_REFRESH, dry_run=dry_run,
        backup_tag="pre01",
        drift_report=REVIEW / f"spine_merge_drift_{TODAY}.csv")
    reports["cedar_entity_spine.csv"] = rep_spine
    log(f"  {rep_spine}")
    if rep_spine.drift:
        log(f"  {len(rep_spine.drift):,} spine cells where the rebuild "
            f"disagrees with the live value - LIVE KEPT, pairs written to "
            f"review/spine_merge_drift_{TODAY}.csv")

    # ---- review queue -----------------------------------------------------
    # A dated file. Nothing enriches it, so it is written whole - but only the
    # tier B rows THIS build computed, which is what it has always been.
    log("\n[6] Building review queue (tier B only)")
    tierB = [r for r in ledger if r["confidence_tier"] == "B"]

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
    if not dry_run:
        write_table(REVIEW / f"review_queue_{TODAY}.csv", tierB,
                    ["review_id", "identifier_type", "identifier",
                     "legal_business_name", "canonical_name", "tribe_id",
                     "entity_class", "attribution_method", "state",
                     "prime_dollars_M", "evidence_url", "question",
                     "YOUR_RULING"], backup_tag="pre01")
    log(f"  review queue          : {len(tierB):,} items")

    # ---- summary ----------------------------------------------------------
    tiers = Counter(r["confidence_tier"] for r in ledger)
    bytype = Counter((r["identifier_type"], r["confidence_tier"]) for r in ledger)
    log("\n=== SUMMARY ===")
    log(f"spine entities computed here : {len(spine):,}")
    log(f"spine rows after merge       : {rep_spine.rows_after:,} "
        f"({len(spine_out_fields)} columns)")
    log(f"identifier links computed    : {len(ledger):,}")
    for t in ("A", "B", "C"):
        log(f"  tier {t}              : {tiers[t]:,}")
    log("")
    for idt in ("UEI", "CAGE", "EIN"):
        log(f"  {idt:4s}  A={bytype[(idt,'A')]:>6,}  B={bytype[(idt,'B')]:>6,}  C={bytype[(idt,'C')]:>6,}")
    dollars_at_stake = sum(dollars(r) for r in tierB)
    log(f"\ndollars at stake in B : ${dollars_at_stake:,.0f}M")
    log("\nOnly tier A is publishable. Tier B ships nothing until ruled.")
    if dry_run:
        log("\nDRY RUN: no file was written, no backup was taken.")
    return reports


if __name__ == "__main__":
    dry = "--dry-run" in sys.argv
    try:
        build(dry_run=dry)
    except Exception as exc:
        log(f"\nFAILED: {type(exc).__name__}: {exc}")
        raise
