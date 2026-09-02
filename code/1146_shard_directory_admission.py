#!/usr/bin/env python3
# lint-ok: class6 - this script is an APPEND-ONLY enricher on
# data/clean/native_owned_businesses.csv. It writes through
# cedar_pipeline.merge_table, which cannot drop a row and raises rather than
# drop a column, so it cannot revert 615/953/1070/1100's in-place work the way
# a `330 promote` rebuild would.
"""1146 - ADMIT THE SHARD-C / SHARD-L / SHARD-M BUSINESS DIRECTORIES.

    py -3 code/1146_shard_directory_admission.py report     # offline, no writes
    py -3 code/1146_shard_directory_admission.py apply      # offline, appends
    py -3 code/1146_shard_directory_admission.py verify     # exits 1 when it did not land
    py -3 code/1146_shard_directory_admission.py selftest   # proves verify FIRES

WHAT THIS IS, AND WHY IT IS FREE
--------------------------------
`docs/AGENT_FIELD_GUIDE.md` §5: "missing" has four causes and only one is a
download. This is the `ON_DISK_NOT_PROMOTED` case, measured.

`data/staging/business_registry/` holds 36 harvested directory files. Fifteen of
them have never reached `data/clean/native_owned_businesses.csv`, and NOT
because anything is wrong with them:

    330_build_native_owned_businesses.py `promote` refuses any staging file
    whose source id is absent from its SOURCES / PRIOR / SIBLING dicts, with
    the message "unknown source id ... NOT PROMOTED". That refusal is CORRECT
    and deliberate - promoting a file whose certifying authority, assertion
    class and terms status the script cannot state is how a restricted source
    reaches data/clean by accident. But 330's SIBLING dict was written on
    2026-09-01, and `570_shard_l_vendor_list_hunt.py` (TBD-L01..L11), shard_m
    (TBD-M01..M03) and shard_c (TBD-C03) wrote into that directory afterwards.

So fifteen directories from fifteen certifying nations, harvested, parsed,
provenanced and sitting on disk, are invisible to the dataset. This script
states the missing adjudication for each one and admits them. ZERO NETWORK.

WHY IT APPENDS INSTEAD OF ASKING 330 TO REBUILD
-----------------------------------------------
`330 promote` is a FULL REBUILD of the table, and five in-place enrichers have
touched it since the last one - the `.bak_*` files beside it name them:
`_pre615`, `_pre_1070merge`, `_pre_953_nob_federal_identifier_candidates`,
`_pre_doyon`, `_pre_1100_nob_crosswalk_promotion`. `330 promote` writes with
`restval=""`, so a rebuild today would carry the enrichment COLUMNS and blank
their VALUES: the rebuild/in-place collision that START_HERE.md records four
times over.

This pass therefore does BOTH halves, which is the only correct answer:

  1. APPENDS the fifteen sources now, through `cedar_pipeline.merge_table`,
     which preserves every live row and every live cell.
  2. WRITES the adjudication to `data/staging/business_registry/`
     `_shard_admission_dispositions.json`, and `330 promote` now reads that
     file into its SIBLING dict. A future rebuild REPRODUCES these rows
     instead of dropping them.

Without (2) this work is reverted by the next rebuild and the revert looks like
nothing happened. Without (1) it does not exist until somebody dares run a
rebuild that blanks five enrichers.

WHAT IS ADJUDICATED HERE, AND WHAT IS NOT
-----------------------------------------
Per source: the certifying authority's spine id and name, the programme name,
and the `assertion_class` where the staged rows do not carry one. Everything
else - `identity_scope`, `directory_type`, `identity_claim_text`,
`verification_basis`, the per-row certification fields - is READ FROM THE
STAGED ROW and never re-derived. `identity_scope` is deliberately left MIXED
within a source where the source is mixed (Puyallup 81 any_native / 7 citizen);
flattening it would erase the distinction the dataset exists to preserve.

TWO VOCABULARY DECISIONS, BOTH STATED RATHER THAN SLIPPED IN
------------------------------------------------------------
`AGENT_FIELD_GUIDE` rule 7: a controlled vocabulary is an interface.

1. `assertion_class` in the live table holds exactly OWNERSHIP (2,387),
   RELATIONSHIP (527), JOINT_VENTURE_PARTICIPATION (2). Two staged sources
   assert a TRIBAL BUSINESS LICENCE, and `570_shard_l` typed one of them
   `LICENCE`. This pass does NOT widen the vocabulary. It maps a licence to
   **RELATIONSHIP** - "the authority asserts the firm DOES BUSINESS WITH the
   tribe", 330's own definition - and records the source's own word in
   `validation_flags`. Reading a licence as OWNERSHIP would be the exact error
   this dataset exists to avoid: the Hoopa register says in its own words that
   it carries "NO ownership threshold, NO tribal membership requirement".
   Note the live table already types Lummi's `business_licence` rows OWNERSHIP,
   correctly, because the Lummi list is titled "Lummi-owned businesses". The
   directory TYPE does not decide the assertion CLASS; the source's own claim
   sentence does.

2. `source_terms_status` gains two values it has not held before -
   `TERMS_STATED_COPYRIGHT_ONLY` (17 rows) and `NOT_CHECKED` (19). Both fall
   OUTSIDE `615_set_publishable_native_owned_businesses.PERMISSION_OK`, which
   is an ALLOW-list, so both land `publishable = N`. That is the safe
   direction and it is almost certainly too conservative for the copyright-only
   three - a copyright notice is not a reuse restriction. **Widening that
   allow-list is 615's decision, not this script's**, so the rows are admitted
   held and the question is written to the owner decision queue rather than
   answered here.

PRIVACY - INHERITED FROM 330, NOT REINVENTED
--------------------------------------------
The staged rows carry `owner_name_raw`, `email`, `phone`, `address_raw`,
`postal_code`. NONE of those five columns exists in
`native_owned_businesses.csv` and none is created here. They stay in staging,
exactly as `330`'s WITHHELD list requires and as the 2026-09-02 terms ruling
leaves untouched: a firm's name is not PII, a person's home phone is. What
ships is the count (`owner_name_present`, `n_owners_named`) and the
`withheld_fields` list naming what was held.

READS   data/staging/business_registry/TBD-{C03,L01..L11,M01..M03}_*.jsonl
        data/clean/native_owned_businesses.csv          (live, preserved)
        data/spine/cedar_entity_spine.csv
        review/tribal_vendor_list_registry_2026-08-26.csv   (terms status)
WRITES  data/clean/native_owned_businesses.csv          (APPEND via merge_table)
        data/staging/business_registry/_shard_admission_dispositions.json
        review/native_owned_businesses_shard_admission_1146.csv   (the exhibit)
"""
from __future__ import annotations

import argparse
import collections
import csv
import hashlib
import importlib
import json
import re
import shutil
import sys
import urllib.parse as up
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "code"))

CLEAN = ROOT / "data" / "clean" / "native_owned_businesses.csv"
STAGE = ROOT / "data" / "staging" / "business_registry"
SPINE = ROOT / "data" / "spine" / "cedar_entity_spine.csv"
REGISTRY = ROOT / "review" / "tribal_vendor_list_registry_2026-08-26.csv"
DISPOSITIONS = STAGE / "_shard_admission_dispositions.json"
EXHIBIT = ROOT / "review" / "native_owned_businesses_shard_admission_1146.csv"

SCRIPT = "1146_shard_directory_admission.py"
BACKUP_TAG = "2026-09-02_pre_1146_shard_directory_admission"
HARVEST_DATE = "2026-09-01"          # the date the shards fetched them
ADMISSION_DATE = "2026-09-02"

csv.field_size_limit(min(sys.maxsize, 2**31 - 1))


# ---------------------------------------------------------------------------
# THE ADJUDICATION. One entry per staging file 330 refuses as UNKNOWN_SOURCE_ID.
#
# `tribe_id` was resolved by matching the staged row's source_url HOST against
# `review/tribal_vendor_list_registry_2026-08-26.csv`, then confirming the id
# resolves in `data/spine/cedar_entity_spine.csv`. All fifteen confirmed.
# `assertion_class` is None where the staged rows carry their own.
# ---------------------------------------------------------------------------
ADMIT = {
    "TBD-C03": dict(
        tribe_id="TRBF-PUYLLP-00", authority="Puyallup Tribe of Indians",
        programme="TERO Indian Preference Directory",
        assertion_class="OWNERSHIP",
        why=("Puyallup Tribal Code 3.24.050 requires preference for 'qualified "
             "Indian-owned businesses' and the directory is the TERO's list of "
             "them, so the tribe is asserting OWNERSHIP, not a vendor "
             "relationship. identity_scope stays MIXED per row - 81 any_native "
             "and 7 citizen - because the directory prints a TRIBE OF "
             "AFFILIATION per entry and most name a tribe OTHER than Puyallup. "
             "Flattening that to `citizen` would be a false claim about 81 "
             "firms."),
        built_by="shard_c",
    ),
    "TBD-L01": dict(
        tribe_id="TRBF-HOOPAV-00", authority="Hoopa Valley Tribe",
        programme="Hoopa Active Business Names (tribal business licence register)",
        assertion_class="RELATIONSHIP", assertion_class_source_word="LICENCE",
        why=("The register states, in the staged rows' own claim text, 'NO "
             "ownership threshold, NO tribal membership requirement'. It is a "
             "licence to do business under Hoopa jurisdiction, which is a "
             "RELATIONSHIP the tribe asserts, not an ownership certification. "
             "570_shard_l typed it `LICENCE`; that value is not in this "
             "table's vocabulary and the source's word is kept in "
             "validation_flags instead of widening the interface."),
        built_by="570_shard_l_vendor_list_hunt.py",
    ),
    "TBD-L02": dict(
        tribe_id="TRBF-BADRVR-00", authority="Bad River Band",
        programme="Business Directory - Tribal Member Owned Businesses",
        assertion_class=None,
        why=("Staged rows carry assertion_class=OWNERSHIP. identity_scope is "
             "MIXED and stays so: 31 `citizen` and 8 `vendor_relationship`. "
             "The 8 are on the same page and are NOT ownership claims; the "
             "per-row scope is the only thing that keeps them apart."),
        built_by="570_shard_l_vendor_list_hunt.py",
    ),
    "TBD-L03": dict(
        tribe_id="TRBF-LTRVRS-00",
        authority="Little Traverse Bay Bands of Odawa Indians",
        programme="LTBB Tribal Citizen-owned Business Directory",
        assertion_class=None,
        why="Staged rows carry assertion_class=OWNERSHIP, identity_scope=citizen.",
        built_by="570_shard_l_vendor_list_hunt.py",
    ),
    "TBD-L04": dict(
        tribe_id="TRBF-AQNNAH-00",
        authority="Wampanoag Tribe of Gay Head (Aquinnah)",
        programme="Business Directory (Planning Department listing)",
        assertion_class=None,
        why=("Staged rows carry OWNERSHIP. The scope is the WEAK one - the "
             "tribe's own sentence is 'businesses owned by Aquinnah Wampanoag "
             "individuals or their families', which 570_shard_l mapped to the "
             "existing `shareholder_descendant_or_spouse` token and flagged as "
             "a borrowed vocabulary. That flag is carried through verbatim; a "
             "family-owned claim is not a 51% certification."),
        built_by="570_shard_l_vendor_list_hunt.py",
    ),
    "TBD-L05": dict(
        tribe_id="TRBF-DELAWT-00", authority="Delaware Tribe of Indians",
        programme="Tribal Business register (WordPress `tribalbusiness` type)",
        assertion_class=None,
        why=("Staged rows carry OWNERSHIP / tribally_owned_entity. The "
             "publisher IS the asserted owner, which is the strongest form of "
             "this claim and the reason no ownership percentage is stated."),
        built_by="570_shard_l_vendor_list_hunt.py",
    ),
    "TBD-L06": dict(
        tribe_id="TRBF-CAVLLY-00", authority="California Valley Miwok Tribe",
        programme="Tribally owned SBA 8(a) operating companies",
        assertion_class=None,
        why="Staged rows carry OWNERSHIP / tribally_owned_entity; publisher is the tribe.",
        built_by="570_shard_l_vendor_list_hunt.py",
    ),
    "TBD-L07": dict(
        tribe_id="TRBF-CHEHLS-00",
        authority="Confederated Tribes of the Chehalis Reservation",
        programme="Chehalis Tribal Enterprises (CTE) family of businesses",
        assertion_class=None,
        why="Staged rows carry OWNERSHIP / tribally_owned_entity; publisher is the tribe.",
        built_by="570_shard_l_vendor_list_hunt.py",
    ),
    "TBD-L08": dict(
        tribe_id="TRBF-CITIZN-00", authority="Citizen Potawatomi Nation",
        programme="Tribal enterprise register (WordPress `enterprise` type)",
        assertion_class=None,
        why=("Staged rows carry OWNERSHIP / tribally_owned_entity. Flagged in "
             "the source as a CLOSED register, not an open vendor directory - "
             "it enumerates the Nation's own enterprises and nobody else's."),
        built_by="570_shard_l_vendor_list_hunt.py",
    ),
    "TBD-L09": dict(
        tribe_id="TRBF-FTHALL-00", authority="Shoshone-Bannock Tribes",
        programme="TERO Certified Indian Preference Business Directory",
        assertion_class=None,
        why=("Staged rows carry OWNERSHIP. The directory's own cover says 'All "
             "previous directories are void', issue date September 2022, so "
             "`source_last_updated` is four years old and a consumer should "
             "read these as of 2022 - the row carries the edition."),
        built_by="570_shard_l_vendor_list_hunt.py",
    ),
    "TBD-L10": dict(
        tribe_id="TRBF-CHTMCH-00", authority="Chitimacha Tribe of Louisiana",
        programme="Tribal Enterprises",
        assertion_class=None,
        why="Staged rows carry OWNERSHIP / tribally_owned_entity; publisher is the tribe.",
        built_by="570_shard_l_vendor_list_hunt.py",
    ),
    "TBD-L11": dict(
        tribe_id="TRBF-KALSPL-00", authority="Kalispel Tribe of Indians",
        programme="Kalispel tribal enterprises (/our-enterprises)",
        assertion_class=None,
        why="Staged rows carry OWNERSHIP / tribally_owned_entity; publisher is the tribe.",
        built_by="570_shard_l_vendor_list_hunt.py",
    ),
    "TBD-M01": dict(
        tribe_id="TRBF-SPKANE-00", authority="Spokane Tribe of Indians",
        programme="TERO Updated Indian Preference Companies List",
        assertion_class="OWNERSHIP",
        why=("The document title is 'UPDATED INDIAN PREFERENCE COMPANIES LIST' "
             "and the TERO reviews entries, so the tribe is asserting Indian "
             "ownership. identity_scope is MIXED per row (16 any_native, 6 "
             "mixed, 1 tribally_owned_entity) and stays so. The staged rows "
             "record that NO ownership percentage, threshold, certification "
             "number or expiry appears anywhere in the source."),
        built_by="shard_m",
    ),
    "TBD-M02": dict(
        tribe_id="TRBF-SWOYTE-00", authority="Sisseton-Wahpeton Oyate",
        programme="TERO Approved Indian Preference Businesses",
        assertion_class="OWNERSHIP",
        why=("Document heading, verbatim: 'APPROVED INDIAN PREFERENCE'. TERO "
             "review, identity_scope any_native on every row. Ingested by OCR "
             "- `ocr_mean_confidence` rides on the row."),
        built_by="shard_m",
    ),
    "TBD-M03": dict(
        tribe_id="TRBF-PYRMDL-00", authority="Pyramid Lake Paiute Tribe",
        programme="2025 Approved Business Licenses",
        assertion_class="RELATIONSHIP",
        why=("A licence to operate on the reservation is NOT an ownership "
             "claim, and the staged rows say so in their own validation flag: "
             "'identity_scope=vendor_relationship AND NOT an ownership claim'. "
             "The column headings are 'Name of License Holder' / 'Expiration "
             "Date' / 'License #'. Typing this OWNERSHIP would put 73 firms "
             "into the dataset as Native-owned on the strength of a business "
             "licence."),
        built_by="shard_m",
    ),
}

# Staging files that are NOT admitted, each with the reason. An unlisted
# foreign file is refused by default - see `enumerate_staging`.
HELD = {
    "TBD-C01": ("EXCLUDE_DUPLICATE",
                "Same 337 rows as TBD-079 (MCN CESO vendor list). 330's own "
                "SIBLING dict already refuses it; repeating the refusal here "
                "keeps the two scripts from disagreeing."),
    "TBD-L00": ("NOT_A_BUSINESS_DIRECTORY",
                "TBD-L00_business_identifiers.jsonl (576) and "
                "TBD-L00_business_identifier_fpds_match.jsonl (1) are the "
                "identifier crosswalk built by 1000/1001, not a certifying "
                "authority's directory. They belong to "
                "native_business_identifier_crosswalk.csv."),
}


# ---------------------------------------------------------------------------
def _load_330():
    """Reuse 330's own helpers so a rule cannot drift between two scripts."""
    return importlib.import_module("330_build_native_owned_businesses")


def _load_615_permission():
    m = importlib.import_module("615_set_publishable_native_owned_businesses")
    ok = getattr(m, "PERMISSION_OK", None)
    if not ok:
        raise RuntimeError(
            "615_set_publishable_native_owned_businesses.PERMISSION_OK is "
            "absent. This script must not invent a permission gate; 615 owns "
            "`publishable`.")
    return set(ok)


def staging_files():
    out = {}
    for f in sorted(STAGE.glob("TBD-*.jsonl")):
        out.setdefault(f.name.split("_")[0], []).append(f)
    return out


def _registry_terms():
    terms, urls = {}, {}
    with REGISTRY.open(encoding="utf-8", newline="") as fh:
        for r in csv.DictReader(fh):
            tid = (r.get("tribe_id") or "").strip()
            if tid:
                terms[tid] = (r.get("source_terms_status") or "").strip()
            u = (r.get("list_url") or "").strip()
            if u:
                urls.setdefault(up.urlparse(u).netloc.lower()
                                .replace("www.", ""), r)
    return terms, urls


def _spine():
    out = {}
    with SPINE.open(encoding="utf-8", errors="replace", newline="") as fh:
        for r in csv.DictReader(fh):
            out[(r.get("tribe_id") or "").strip()] = r
    return out


def read_rows(sid):
    rows = []
    for f in staging_files().get(sid, []):
        with f.open(encoding="utf-8") as fh:
            for line in fh:
                if line.strip():
                    rows.append(json.loads(line))
    return rows


# ---------------------------------------------------------------------------
def build_rows(verbose=True):
    """Render the fifteen staged sources into the LIVE table's schema.

    Returns (rows, per_source_counts, notes). No writes.
    """
    m330 = _load_330()
    perm_ok = _load_615_permission()
    ident = importlib.import_module("503_identity")
    exact, gov, state_of = ident.build_index()
    spine = _spine()
    reg_terms, _ = _registry_terms()

    live_fields = _live_fields()

    out, counts, notes = [], {}, []
    for sid, adj in ADMIT.items():
        rows = read_rows(sid)
        if not rows:
            notes.append(f"{sid}: NO STAGING ROWS FOUND - nothing admitted")
            counts[sid] = 0
            continue
        auth_tid = adj["tribe_id"]
        if auth_tid not in spine:
            raise RuntimeError(
                f"{sid}: certifying authority {auth_tid} is not in the spine. "
                f"A directory cannot be admitted under an authority Cedar "
                f"cannot name.")
        auth_name = adj["authority"]
        terms = reg_terms.get(auth_tid, "") or ""
        n = 0
        for r in rows:
            name = r.get("business_name_raw") or ""
            owner = r.get("owner_name_raw")
            # RESOLUTION: exact normalized name/alias only, 330's rule. The
            # loose gov-class token path is REFUSED - on a business roster it
            # resolves "Navajo Transitional Energy" to the Navajo Nation,
            # which is a false ownership claim, not a match.
            tid, why = ident.resolve(name, exact, gov, state_of,
                                     r.get("state_province") or "")
            if tid and not why.startswith(("exact normalized",
                                           "declared equivalence")):
                tid, why = None, "REFUSED_LOOSE_TOKEN_PATH: " + why
            ent = spine.get(tid or "", {})

            aclass = (r.get("assertion_class") or "").strip()
            flags = list(r.get("validation_flags") or [])
            if adj.get("assertion_class"):
                if aclass and aclass != adj["assertion_class"]:
                    flags.append(
                        f"assertion_class_source_word={aclass}; mapped to "
                        f"{adj['assertion_class']} by {SCRIPT} - see ADMIT[{sid}]")
                aclass = adj["assertion_class"]
            if aclass not in ("OWNERSHIP", "RELATIONSHIP",
                              "JOINT_VENTURE_PARTICIPATION"):
                raise RuntimeError(
                    f"{sid}: assertion_class {aclass!r} is outside this "
                    f"table's vocabulary. Widen it explicitly or adjudicate "
                    f"the source; do not let a new value in silently.")

            nown = 0
            if owner:
                nown = len([x for x in re.split(r";|&|\band\b", owner)
                            if x.strip()])
            withheld = ";".join(k for k in m330.WITHHELD if r.get(k))

            pub = "Y" if terms in perm_ok else "N"
            pub_basis = ("harmonized_publication_per_PUBLICATION_POLICY"
                         if pub == "Y"
                         else f"PERMISSION:{terms or 'UNKNOWN'}")

            out.append({
                "business_source_id": r["business_source_id"],
                "source_id": sid,
                "source_business_key": r.get("source_business_key") or "",
                "certifying_authority_entity_id": auth_tid,
                "certifying_authority_name": auth_name,
                "nation_id": r.get("nation_id") or "",
                "programme_name": adj["programme"],
                "business_name_raw": name,
                "business_name_normalized": r.get("business_name_normalized") or "",
                "business_name_is_person_name": m330.looks_like_person(name, owner),
                "business_entity_id": tid or "",
                "business_entity_name": ent.get("canonical_name", ""),
                "business_entity_class": ent.get("entity_class", ""),
                "resolution_method": why,
                "record_scope": "entity" if tid else "unresolved",
                "assertion_class": aclass,
                "directory_type": r.get("directory_type") or "",
                "identity_scope": r.get("identity_scope") or "",
                "identity_claim_text": r.get("identity_claim_text") or "",
                "inclusion_basis": "program_authority",
                "ownership_percent": r.get("ownership_percent") or "",
                "ownership_threshold_min": r.get("ownership_threshold_min") or "",
                "verification_basis": r.get("verification_basis") or "",
                "certification_number": r.get("certification_number") or "",
                "certification_tier": r.get("certification_tier") or "",
                "certification_start": m330.iso_date(r.get("certification_start")),
                "certification_expiration": m330.iso_date(
                    r.get("certification_expiration")),
                "business_license_number": r.get("business_license_number") or "",
                "federal_contract_number": r.get("federal_contract_number") or "",
                "service_category_raw": r.get("service_category_raw") or "",
                "naics": r.get("naics") or "",
                "city": r.get("city") or "",
                "state_province": r.get("state_province") or "",
                "owner_name_present": 1 if owner else 0,
                "n_owners_named": nown,
                "withheld_fields": withheld,
                "source_url": r.get("source_url") or "",
                "source_edition": r.get("source_edition") or "",
                "source_last_updated": r.get("source_last_updated") or "",
                "harvest_date": HARVEST_DATE,
                "first_seen": r.get("first_seen") or "",
                "last_seen": r.get("last_seen") or "",
                "is_current": r.get("is_current", True),
                "ingestion_method": r.get("ingestion_method") or "",
                "ocr_mean_confidence": r.get("ocr_mean_confidence") or "",
                "raw_snapshot_uri": r.get("raw_snapshot_uri") or "",
                "source_terms_status": terms or "SILENT",
                "consent_status": "UNRESOLVED",
                "suppression_key": f"SUPPRESS::{auth_tid}",
                "publishable": pub,
                "publishable_basis": pub_basis,
                "validation_flags": ";".join(m330.redact_flags(flags)),
                "record_hash": r.get("record_hash") or "",
                "built_by_script": SCRIPT,
            })
            n += 1
        counts[sid] = n

    # ------------------------------------------------------------------
    # DEFECT CLASS 7 - A NON-UNIQUE PRIMARY KEY, INHERITED FROM STAGING.
    #
    # shard_m keys a Pyramid Lake row on a hash of the FIRM NAME, and the
    # 2025 Approved Business Licenses list issues a firm one licence per
    # activity: `I80 Smoke Shop` holds five (General, Convenience Store,
    # Liquor Retail x2, Food Services). Six firms therefore share one
    # `business_source_id` across twelve rows.
    #
    # These are NOT duplicate rows - AGENT_FIELD_GUIDE 4, four of five
    # duplicate allegations in this repo were phantom. Every one differs in
    # `business_license_number` and `service_category_raw`, and collapsing
    # them would delete real licences. The ROWS are right; the KEY is wrong.
    #
    # So the key is widened with the discriminator the source itself
    # publishes - the licence number - and only where it collides, so no
    # existing key changes. Where the source printed no licence number the
    # row takes an ordinal and SAYS SO in validation_flags, because an
    # invented ordinal that looks like a licence number would be worse than
    # the collision.
    # ------------------------------------------------------------------
    by_key = collections.Counter(r["business_source_id"] for r in out)
    collided = {k for k, v in by_key.items() if v > 1}
    if collided:
        for r in out:
            k = r["business_source_id"]
            if k not in collided:
                continue
            disc, basis = _discriminator(r)
            # lint-ok: class7 - `disc` is a function of the ROW, never of its
            # position: `_discriminator` returns the source's own
            # business_license_number, or a digest of the row's own content
            # columns. The ordinal version this replaced WAS a class 7
            # instance and is retired; V7 asserts the result is unique.
            r["business_source_id"] = f"{k}#{disc}"
            r["validation_flags"] = ";".join(
                x for x in [r.get("validation_flags"),
                            f"business_source_id_disambiguated_by={basis}"] if x)
        print(f"  disambiguated {len(collided)} colliding "
              f"business_source_id(s) covering "
              f"{sum(by_key[k] for k in collided)} rows")

    # A column this script emits that the live table does not hold would be a
    # silent schema change. Refuse it.
    emitted = set()
    for r in out:
        emitted |= set(r)
    stray = sorted(emitted - set(live_fields))
    if stray:
        raise RuntimeError(
            f"{SCRIPT} would add columns to native_owned_businesses.csv: "
            f"{stray}. This is an APPEND, not a schema change.")

    # And a PII column must never appear, whatever the staged row carries.
    pii = sorted(set(m330.WITHHELD) & emitted)
    if pii:
        raise RuntimeError(f"PII columns would ship: {pii}")

    if verbose:
        for note in notes:
            print("  !! " + note)
    return out, counts, notes


def _live_fields():
    with CLEAN.open(encoding="utf-8", newline="") as fh:
        return next(csv.reader(fh))


def _live_source_counts():
    counts = {}
    with CLEAN.open(encoding="utf-8", newline="") as fh:
        for r in csv.DictReader(fh):
            counts[r["source_id"]] = counts.get(r["source_id"], 0) + 1
    return counts


# ---------------------------------------------------------------------------
def cmd_report(_args):
    live = _live_source_counts()
    staged = staging_files()
    print(f"\n  live table: {CLEAN.relative_to(ROOT)}")
    print(f"    rows {sum(live.values()):,}   source_ids {len(live)}")
    print("\n  STAGING FILES, and where each one stands")
    print(f"    {'source':<10} {'rows':>6}  disposition")
    admit_rows = 0
    for sid in sorted(staged):
        n = sum(sum(1 for line in f.open(encoding='utf-8') if line.strip())
                for f in staged[sid])
        if sid in live:
            disp = f"ALREADY IN CLEAN ({live[sid]:,} rows)"
        elif sid in ADMIT:
            disp = "ADMIT (this script)"
            admit_rows += n
        elif sid in HELD:
            disp = "HELD: " + HELD[sid][0]
        else:
            disp = "UNADJUDICATED - refused by default"
        print(f"    {sid:<10} {n:>6}  {disp}")
    print(f"\n    rows this script would append: {admit_rows:,}")

    rows, counts, _ = build_rows()
    print(f"    rows it actually renders:      {len(rows):,}")
    _summarise(rows, counts)
    return 0


def _summarise(rows, counts):
    import collections
    print("\n  WHAT THE APPENDED ROWS SAY")
    for k in ("assertion_class", "directory_type", "identity_scope",
              "source_terms_status", "publishable", "record_scope"):
        c = collections.Counter(str(r[k]) for r in rows)
        print(f"    {k:<22} " + "  ".join(f"{a}={b}" for a, b in c.most_common(6)))
    auth = collections.Counter(r["certifying_authority_name"] for r in rows)
    print(f"    certifying authorities  {len(auth)} new")
    withheld = sum(1 for r in rows if r["withheld_fields"])
    print(f"    rows with a withheld contact channel  {withheld:,} "
          f"(the columns do not exist in the table)")
    res = sum(1 for r in rows if r["business_entity_id"])
    print(f"    resolved to a spine entity            {res:,}")


def _discriminator(r):
    """The suffix that separates two rows sharing a staged key.

    Defect class 7 is an id minted from OUTSIDE the row - a process hash, a
    RANK or a POSITION. The first draft of this used an ordinal (`#n1`, `#n2`)
    where the source printed no licence number, which is exactly that: it is
    stable only while the file's row ORDER is, and a re-parse that reordered
    the staging file would silently re-key those rows. Every input below comes
    off the row itself, so the id is a function of the record and nothing
    else.

    First choice is the discriminator the SOURCE published - Pyramid Lake
    prints `PL 2025-026` / `PL S2025-001` for the same firm's general and
    towing licences. Where there is none, the fallback is a short digest of
    the columns that actually differ between the colliding rows, and it SAYS
    it is Cedar's rather than dressing up as a licence number.
    """
    lic = re.sub(r"[^A-Za-z0-9]+", "-",
                 (r.get("business_license_number") or "")).strip("-")
    if lic:
        return lic, "business_license_number"
    fields = ("service_category_raw", "certification_expiration",
              "certification_start", "certification_tier", "city",
              "state_province", "source_url")
    payload = "||".join(str(r.get(f) or "") for f in fields)
    return ("x" + hashlib.md5(payload.encode("utf-8")).hexdigest()[:8],
            "CEDAR_CONTENT_DIGEST of "
            + ",".join(fields)
            + " - the source printed no licence number for this row, so this "
              "suffix is Cedar's and is a function of the row, never of its "
              "position in the file")


def _repair_live_keys(dry_run=False):
    """One-shot, idempotent: apply the same disambiguation to rows ALREADY in
    the live table.

    The collision was applied on 2026-09-02 before it was noticed, so twelve
    Pyramid Lake rows are in `data/clean` under six keys. `merge_table` did
    not lose them - it keys ordinally - but `business_source_id` is the
    declared primary key of this table and a consumer joining on it gets one
    of five licences at random. This rewrites those keys with the same rule
    `build_rows` now uses, so the two agree and a re-`apply` matches instead
    of appending a second copy.
    """
    with CLEAN.open(encoding="utf-8", newline="") as fh:
        rd = csv.DictReader(fh)
        fields, rows = rd.fieldnames, list(rd)
    mine = {r["business_source_id"] for r in rows if r["source_id"] in ADMIT}
    cnt = collections.Counter(r["business_source_id"] for r in rows
                              if r["source_id"] in ADMIT)
    collided = {k for k, v in cnt.items() if v > 1}
    if not collided:
        return 0
    n = 0
    for r in rows:
        if r["source_id"] not in ADMIT:
            continue
        k = r["business_source_id"]
        if k not in collided:
            continue
        disc, basis = _discriminator(r)
        # lint-ok: class7 - same rule as build_rows: `_discriminator` reads
        # the row, not its position. See its docstring.
        r["business_source_id"] = f"{k}#{disc}"
        r["validation_flags"] = ";".join(
            x for x in [r.get("validation_flags"),
                        f"business_source_id_disambiguated_by={basis}"] if x)
        n += 1
    print(f"  repairing {len(collided)} colliding primary key(s) already in "
          f"the live table, covering {n} rows"
          + ("  (DRY RUN)" if dry_run else ""))
    if dry_run:
        return n
    shutil.copy2(CLEAN, CLEAN.with_name(
        CLEAN.name + ".bak_2026-09-02_pre_1146_key_repair"))
    part = CLEAN.with_suffix(".csv.part_1146keys")
    with part.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    part.replace(CLEAN)
    return n


def cmd_apply(args):
    import cedar_pipeline as cp

    _repair_live_keys(dry_run=args.dry_run)
    before = _live_source_counts()
    rows, counts, _ = build_rows()
    if not rows:
        print("  nothing to append")
        return 2

    fields = _live_fields()
    merged, out_fields, rep = cp.merge_table(
        CLEAN, rows, fields, key_cols=["business_source_id"],
        dry_run=args.dry_run, backup_tag=None if args.dry_run else BACKUP_TAG,
        drift_report=str(ROOT / "review" /
                         "native_owned_businesses_1146_drift.csv"))

    print(f"\n  merge_table -> {CLEAN.relative_to(ROOT)}"
          f"{'  (DRY RUN)' if args.dry_run else ''}")
    print(f"    rows before   {rep.rows_before:,}")
    print(f"    appended      {rep.rows_appended:,}")
    print(f"    matched       {rep.rows_matched:,}   cells filled {rep.cells_filled:,}")
    print(f"    rows after    {rep.rows_after:,}")
    print(f"    columns       {len(rep.cols_before)} -> {len(out_fields)} "
          f"(added {rep.cols_added}, lost {rep.cols_lost})")
    if rep.drift:
        print(f"    drift declined on {len(rep.drift)} cells - see review/")

    if rep.rows_appended != len(rows):
        print(f"    !! {len(rows) - rep.rows_appended} row(s) collided with an "
              f"existing business_source_id and were merged, not appended.")

    if not args.dry_run:
        _write_dispositions(counts)
        _write_exhibit(rows)
        print(f"\n    dispositions -> {DISPOSITIONS.relative_to(ROOT)}")
        print(f"    exhibit      -> {EXHIBIT.relative_to(ROOT)}")

    after = _live_source_counts() if not args.dry_run else {}
    if after:
        new = sorted(set(after) - set(before))
        print(f"\n    NEW source_ids in the table: {len(new)}  {new}")
    _summarise(rows, counts)
    return 0


def _write_dispositions(counts):
    """The file `330 promote` reads, so a REBUILD reproduces these rows.

    Without this the next `330 promote` drops all fifteen sources again and
    prints nothing but its own progress.
    """
    payload = {
        "_written_by": SCRIPT,
        "_written_date": ADMISSION_DATE,
        "_what_this_is": (
            "Admission decisions for staging files written into "
            "data/staging/business_registry/ by shard_c, "
            "570_shard_l_vendor_list_hunt.py and shard_m AFTER 330's SIBLING "
            "dict was authored. 330_build_native_owned_businesses.py "
            "`promote` merges this into SIBLING so a rebuild reproduces them. "
            "Editing this file changes what reaches data/clean."),
        "sources": {},
    }
    for sid, adj in ADMIT.items():
        # 330 needs a CONCRETE fallback class, not "PER_ROW": its promote does
        # `r.get("assertion_class") or aclass`. Where this script deferred to
        # the row, read the row's own value back and refuse if the source
        # disagrees with itself - a source with two classes needs adjudicating,
        # not a majority vote.
        aclass = adj.get("assertion_class")
        if not aclass:
            vals = {(r.get("assertion_class") or "").strip()
                    for r in read_rows(sid)}
            vals.discard("")
            if len(vals) != 1:
                raise RuntimeError(
                    f"{sid}: staged rows carry {sorted(vals)} for "
                    f"assertion_class. ADMIT[{sid}] must state one.")
            aclass = vals.pop()
        payload["sources"][sid] = {
            "disposition": "INCLUDE",
            "tribe_id": adj["tribe_id"],
            "authority": adj["authority"],
            "programme": adj["programme"],
            "assertion_class": aclass,
            "rows_admitted_2026_09_02": counts.get(sid, 0),
            "built_by": adj["built_by"],
            "why": adj["why"],
        }
    for sid, (disp, why) in HELD.items():
        payload["sources"][sid] = {"disposition": disp, "why": why}
    DISPOSITIONS.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _write_exhibit(rows):
    cols = ["source_id", "certifying_authority_name",
            "certifying_authority_entity_id", "programme_name",
            "business_name_raw", "assertion_class", "identity_scope",
            "directory_type", "source_terms_status", "publishable",
            "publishable_basis", "withheld_fields", "source_url",
            "identity_claim_text"]
    EXHIBIT.parent.mkdir(parents=True, exist_ok=True)
    with EXHIBIT.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)


# ---------------------------------------------------------------------------
# VERIFY. AGENT_FIELD_GUIDE rule 5: a proof that nothing broke is not a proof
# that something happened. Every invariant below can ONLY be met by the write
# having landed, and `selftest` raises each floor above the live value and
# asserts exit 1.
# ---------------------------------------------------------------------------
def _floors():
    """Per-source row floors, derived from the STAGING FILES, not remembered."""
    return {sid: len(read_rows(sid)) for sid in ADMIT}


def cmd_verify(args, table=None, floors=None):
    table = Path(table or CLEAN)
    floors = floors or _floors()
    live = {}
    fields = None
    with table.open(encoding="utf-8", newline="") as fh:
        rd = csv.DictReader(fh)
        fields = rd.fieldnames
        for r in rd:
            live[r["source_id"]] = live.get(r["source_id"], 0) + 1

    bad = []
    # V1 - every admitted source is present, at or above its staging count.
    for sid, floor in sorted(floors.items()):
        got = live.get(sid, 0)
        if got < floor:
            bad.append(f"V1 {sid}: {got} rows in the table, staging holds {floor}")

    # V2 - no PII column reached the table.
    m330 = _load_330()
    pii = sorted(set(m330.WITHHELD) & set(fields or []))
    if pii:
        bad.append(f"V2 PII columns present in the table: {pii}")

    # V3 - the assertion_class vocabulary was not widened.
    seen = set()
    with table.open(encoding="utf-8", newline="") as fh:
        for r in csv.DictReader(fh):
            if r["source_id"] in floors:
                seen.add(r["assertion_class"])
    stray = sorted(seen - {"OWNERSHIP", "RELATIONSHIP",
                           "JOINT_VENTURE_PARTICIPATION"})
    if stray:
        bad.append(f"V3 assertion_class widened by these rows: {stray}")

    # V4 - every admitted row names a certifying authority that is in the spine.
    spine = _spine()
    missing = set()
    with table.open(encoding="utf-8", newline="") as fh:
        for r in csv.DictReader(fh):
            if r["source_id"] in floors:
                a = r["certifying_authority_entity_id"]
                if a not in spine:
                    missing.add(a)
    if missing:
        bad.append(f"V4 certifying authority not in the spine: {sorted(missing)}")

    # V5 - the disposition file 330 reads exists and covers every source.
    if table == CLEAN:
        if not DISPOSITIONS.exists():
            bad.append("V5 the disposition file is absent - a `330 promote` "
                       "rebuild would drop all of this and look like progress")
        else:
            d = json.loads(DISPOSITIONS.read_text(encoding="utf-8"))
            miss = sorted(set(ADMIT) - set(d.get("sources", {})))
            if miss:
                bad.append(f"V5 disposition file does not cover {miss}")

    # V7 - `business_source_id` is this table's declared primary key and it
    # must be unique. Six shard_m keys collided across eighteen Pyramid Lake
    # rows on first apply, because shard_m hashes the FIRM NAME and the source
    # issues one licence per activity. Widened, not collapsed - the rows are
    # real. This invariant is what stops it coming back.
    keys = collections.Counter()
    with table.open(encoding="utf-8", newline="") as fh:
        for r in csv.DictReader(fh):
            keys[r["business_source_id"]] += 1
    dupes = [k for k, v in keys.items() if v > 1]
    if dupes:
        bad.append(f"V7 business_source_id is not unique: {len(dupes)} key(s) "
                   f"over {sum(keys[k] for k in dupes)} rows, e.g. {dupes[:3]}")

    # V6 - 330 actually reads that file. A disposition nobody loads is inert.
    src = (ROOT / "code" / "330_build_native_owned_businesses.py").read_text(
        encoding="utf-8", errors="replace")
    if "_shard_admission_dispositions.json" not in src:
        bad.append("V6 330_build_native_owned_businesses.py does not read the "
                   "disposition file; a rebuild still drops these sources")

    for b in bad:
        print("  FAIL  " + b)
    if bad:
        print(f"\n  {len(bad)} invariant(s) BREACHED")
        return 1
    total = sum(live.get(s, 0) for s in floors)
    print(f"  OK  {len(floors)} admitted sources, {total:,} rows, "
          f"6 invariants clean")
    return 0


def cmd_selftest(_args):
    """Prove verify FIRES. A check that has never failed on purpose is not
    known to work."""
    import tempfile
    ok = True

    # 1. clean copy must pass
    if cmd_verify(None) != 0:
        print("  SELFTEST FAIL: verify is red on the live table")
        ok = False
    else:
        print("  selftest 1/3: verify is green on the live table")

    tmp = Path(tempfile.mkdtemp()) / "poisoned.csv"
    shutil.copy2(CLEAN, tmp)

    # 2. floors raised above the live value must fire V1
    floors = {sid: n + 1 for sid, n in
              _live_source_counts().items() if sid in ADMIT}
    if not floors:
        print("  SELFTEST FAIL: no admitted source is in the table, so V1 "
              "cannot be exercised. Run `apply` first.")
        ok = False
    elif cmd_verify(None, table=tmp, floors=floors) != 1:
        print("  SELFTEST FAIL: V1 did not fire on a raised floor")
        ok = False
    else:
        print(f"  selftest 2/3: V1 fires when every floor is live+1 "
              f"({len(floors)} sources)")

    # 3. a source removed from the table must fire V1
    victim = sorted(ADMIT)[0]
    with tmp.open(encoding="utf-8", newline="") as fh:
        rd = csv.DictReader(fh)
        flds, keep = rd.fieldnames, [r for r in rd if r["source_id"] != victim]
    with tmp.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=flds)
        w.writeheader()
        w.writerows(keep)
    if cmd_verify(None, table=tmp, floors=_floors()) != 1:
        print(f"  SELFTEST FAIL: V1 did not fire with {victim} deleted")
        ok = False
    else:
        print(f"  selftest 3/3: V1 fires when {victim} is deleted from the table")

    shutil.rmtree(tmp.parent, ignore_errors=True)
    print("  SELFTEST PASS" if ok else "  SELFTEST FAILED")
    return 0 if ok else 1


MASTER = ROOT / "data" / "clean" / "codebook_master.csv"
CODEBOOK_DATASET = "02m_native_owned_businesses"


def cmd_codebook(_args):
    """Re-measure the 02m codebook block against the LIVE table, in place.

    WHY NOT `330 codebook` ALONE, AND A DEFECT IT EXPOSED
    -----------------------------------------------------
    `330 codebook` writes the FRAGMENT at data/clean/codebook/02m_*.csv, and
    the master is rebuilt from fragments by `cedar_codebook.py build`. That
    fragment describes 330's own 53 `CLEAN_COLUMNS`. The live table has 74
    columns: 953, 1070 and 1100 added 21 more and wrote their descriptions
    STRAIGHT INTO THE MASTER, never into a fragment.

    So `py -3 code/cedar_codebook.py check` reports, today:

        in master but NOT in fragments (would be LOST): 20
           ('02m_native_owned_businesses', 'federal_cage_candidate')  ...

    A `cedar_codebook build` right now silently drops twenty codebook rows
    describing this table's federal-crosswalk columns, and the global
    shrink guard cannot see it because other fragments grew. That defect
    PRE-DATES this pass and is not fixed here - fixing it means 953/1100
    emitting fragments, which is their file, not this one. It is recorded in
    docs/SHARD_DIRECTORY_ADMISSION_LOG_2026-09-02.md and in the work queue.

    What this command does instead is narrow and safe: for the 02m block ONLY,
    re-measure `pct_filled` and `n_rows` against the live table, in place, for
    every one of the 74 columns, KEEPING each row's existing description text.
    No other dataset's rows are read or written.
    """
    live_rows = []
    with CLEAN.open(encoding="utf-8-sig", newline="") as fh:
        rd = csv.DictReader(fh)
        cols = rd.fieldnames or []
        live_rows = list(rd)
    n = len(live_rows)
    filled = {c: sum(1 for r in live_rows if str(r.get(c, "")).strip())
              for c in cols}

    with MASTER.open(encoding="utf-8-sig", newline="") as fh:
        rd = csv.DictReader(fh)
        mfields = rd.fieldnames
        mrows = list(rd)

    # ------------------------------------------------------------------
    # RECOVER 02m rows a `cedar_codebook build` has already dropped.
    #
    # This is not hypothetical. The docstring above predicted it at 17:2x on
    # 2026-09-02 and it HAPPENED at 17:38, between two runs of this command:
    # the 02m block went 74 variable rows -> 53, losing every column 953,
    # 1070 and 1100 had written straight into the master. `cedar_codebook
    # build` is fragment-driven and the global shrink guard cannot see a
    # 21-row loss inside a 6,000-row file.
    #
    # The rows are recovered from the newest master backup that still holds
    # them, DESCRIPTION VERBATIM - nothing is re-worded here - and the
    # measured columns are recomputed below like every other row.
    # ------------------------------------------------------------------
    have = {r["variable"] for r in mrows if r.get("dataset") == CODEBOOK_DATASET}
    recovered = []
    for c in cols:
        if c in have:
            continue
        for bak in sorted(MASTER.parent.glob(MASTER.name + ".bak_*"),
                          key=lambda p: p.stat().st_mtime, reverse=True):
            try:
                with bak.open(encoding="utf-8-sig", newline="") as fh:
                    for r in csv.DictReader(fh):
                        if (r.get("dataset") == CODEBOOK_DATASET
                                and r.get("variable") == c
                                and (r.get("description") or "").strip()):
                            mrows.append({k: r.get(k, "") for k in mfields})
                            have.add(c)
                            recovered.append((c, bak.name))
                            break
            except OSError:
                continue
            if c in have:
                break
    if recovered:
        print(f"  RECOVERED {len(recovered)} codebook row(s) a fragment "
              f"rebuild had dropped: {[c for c, _ in recovered]}")
        print(f"           source: {recovered[0][1]}")

    touched, unknown = 0, []
    for r in mrows:
        if r.get("dataset") != CODEBOOK_DATASET:
            continue
        v = r.get("variable")
        if v not in filled:
            unknown.append(v)
            continue
        r["pct_filled"] = round(100.0 * filled[v] / n, 1) if n else 0.0
        r["n_rows"] = n
        touched += 1

    described = {r["variable"] for r in mrows
                 if r.get("dataset") == CODEBOOK_DATASET}
    undescribed = [c for c in cols if c not in described]

    # A shipped column with no codebook row is a gap a buyer meets first.
    # Only a column this pass can describe from the code that writes it gets
    # one; anything else is REPORTED, never invented.
    ADDABLE = {
        "publishable_basis": (
            "text",
            "Why `publishable` holds the value it does. Written by "
            "code/615_set_publishable_native_owned_businesses.py and by "
            "code/1146_shard_directory_admission.py using 615's own "
            "PERMISSION_OK allow-list. Two shapes: "
            "'harmonized_publication_per_PUBLICATION_POLICY' where the row "
            "cleared the permission gate, and 'PERMISSION:<status>' naming "
            "the source_terms_status that held it back. An unrecognised "
            "terms status renders as PERMISSION:UNKNOWN and is held, because "
            "the gate is an allow-list, not a deny-list."),
    }
    tmpl = next((r for r in mrows if r.get("dataset") == CODEBOOK_DATASET),
                None)
    added = []
    for c in list(undescribed):
        if c not in ADDABLE or tmpl is None:
            continue
        typ, desc = ADDABLE[c]
        row = {k: "" for k in mfields}
        row.update({"dataset": CODEBOOK_DATASET, "variable": c, "type": typ,
                    "units": "",
                    "pct_filled": round(100.0 * filled[c] / n, 1) if n else 0.0,
                    "n_rows": n, "published": tmpl.get("published", "0"),
                    "access_tier": tmpl.get("access_tier", "internal"),
                    "description": desc, "generated": ADMISSION_DATE})
        mrows.append(row)
        undescribed.remove(c)
        added.append(c)
    if added:
        print(f"  codebook rows ADDED for previously undescribed column(s): "
              f"{added}")

    shutil.copy2(MASTER, MASTER.with_name(
        MASTER.name + f".bak_{ADMISSION_DATE}_pre_1146_shard_directory_admission"))
    part = MASTER.with_suffix(".csv.part_1146")
    with part.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=mfields, extrasaction="ignore")
        w.writeheader()
        w.writerows(mrows)
    part.replace(MASTER)

    # And write the FRAGMENT with the full block, so the next
    # `cedar_codebook build` reproduces all of it instead of dropping back to
    # 330's 53 CLEAN_COLUMNS. Reporting the divergence was not enough - it
    # recurred within fifteen minutes of being written down.
    frag = MASTER.parent / "codebook" / f"{CODEBOOK_DATASET}.csv"
    block = [r for r in mrows if r.get("dataset") == CODEBOOK_DATASET]
    if frag.exists() and block:
        with frag.open(encoding="utf-8-sig", newline="") as fh:
            ffields = next(csv.reader(fh))
        with frag.open("w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=ffields, extrasaction="ignore")
            w.writeheader()
            for r in block:
                w.writerow({k: r.get(k, "") for k in ffields})
        print(f"  fragment {frag.relative_to(ROOT)}: {len(block)} variables "
              f"(was 53 - a rebuild no longer drops the enrichment columns)")

    print(f"  {CODEBOOK_DATASET}: {touched} variable rows re-measured "
          f"against {n:,} live rows")
    if unknown:
        print(f"  !! {len(unknown)} codebook variable(s) describe a column the "
              f"table no longer has: {unknown}")
    if undescribed:
        print(f"  !! {len(undescribed)} live column(s) have NO codebook row: "
              f"{undescribed}")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("report")
    a = sub.add_parser("apply")
    a.add_argument("--dry-run", action="store_true")
    sub.add_parser("codebook")
    sub.add_parser("verify")
    sub.add_parser("selftest")
    args = ap.parse_args()
    return {"report": cmd_report, "apply": cmd_apply,
            "codebook": cmd_codebook,
            "verify": cmd_verify, "selftest": cmd_selftest}[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
