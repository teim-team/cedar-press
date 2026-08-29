#!/usr/bin/env python3
"""
Cedar Press - 163: normalise a SAM Contract Awards extract into Cedar's schema.

WHAT THIS IS
------------
`141_pull_sam_contract_awards.py` SUBMITS and DOWNLOADS. This file is the other
half: it takes whatever extracts are on disk, normalises them, deduplicates them
against each other, reconciles them against `data/clean/prime_contracts.csv`,
and writes a licensing-marked clean table plus a codebook fragment.

It is deliberately **variant-aware and resumable**, because the six extracts do
not arrive together. One (TRIBAL, `zrlwsqiydG`) landed 2026-08-26; five were
still generating when the 10-call daily budget ran out. Running this file again
tomorrow with five more files in the directory must cost zero new engineering -
that is the whole design requirement.

    py -3 code/163_load_sam_contract_awards.py status
    py -3 code/163_load_sam_contract_awards.py load          # all new extracts
    py -3 code/163_load_sam_contract_awards.py load --force  # re-process all
    py -3 code/163_load_sam_contract_awards.py reconcile     # report only

MAKES NO NETWORK CALLS. Ever. It reads files.

THE FIVE THINGS THIS FILE REFUSES TO DO
---------------------------------------
1. **It never sums the two classes.** ENTITY_OWNED (INDIAN, ALASKAN NATIVE,
   NATIVE HAWAIIAN, TRIBAL) and INDIVIDUAL_NATIVE_OWNED (AMERICAN INDIAN,
   NATIVE AMERICAN) are held apart on every row and in every report line. An
   individually Native-owned firm is not a tribal enterprise; adding them
   overstates tribal economic activity, which is the single easiest way to
   discredit this dataset. `summary()` prints per class and emits no total.
2. **It never double-counts against `prime_contracts.csv`.** Every row carries
   `novelty` and `double_count_risk`. FY2000-2007 in prime_contracts comes from
   `master prime file.dta` at AWARD-YEAR-VENDOR grain; SAM is at TRANSACTION
   grain. The two are not the same grain and no key makes them so, so the
   reconciliation is reported at PIID and PIID x FY, never as a row delta.
3. **It never treats a variant hit as evidence of Native status.**
   `awardeeBusinessTypeName` is a PARTIAL string match and it lets in whole
   populations that are not Native. Two measured vectors, three orders of
   magnitude apart:

   **"Subcontinent Asian (Asian-INDIAN) American Owned Business" contains the
   string "INDIAN".** MEASURED 2026-08-26 on the INDIAN extract:
   **102,587 of 157,093 rows / 3,774 UEIs / $11,129,475,544 - 65.3% of that
   extract** are Asian-Indian-American-owned firms with no Native attribute of
   any kind. This is the largest single finding of the five-variant load, and
   the INDIAN extract is the biggest ENTITY_OWNED variant, so anyone counting
   "Native contracting" off a raw variant hit would overstate it by $11.1B.

   **"HOUSING AUTHORITIES PUBLIC/TRIBAL" contains the string "TRIBAL"**, which
   is how City of Wichita, City of Dodge, the Housing Authority of the City of
   Los Angeles and Scott Electric Company entered the TRIBAL extract - 87 rows /
   11 UEIs / $710,492.

   All of them are KEPT (the raw is the raw), each carries a
   `variant_match_basis` that NAMES why it is here, and all carry
   `include_in_native_universe = 0`. **Filter on that column before counting
   anything as Native.**
4. **It never publishes D&B Open Data.** Every row here is a base award dated
   before 2022-04-04, so the restriction attaches to 100% of it. Restricted
   columns are prefixed `dnb_`, marked `published = 0` in the codebook, listed
   in `_LICENSING_MANIFEST.json`, and physically absent from the
   `*_PUBLISHABLE.csv` view. Four independent marks, because one gets lost.
5. **It never reads a socio-economic flag as an adjudication.** Every row
   carries `socio_econ_basis = SELF_CERTIFICATION`. Goldbelt Raven LLC, an ANC
   subsidiary, certifies `alaskanNativeCorporationOwnedFirm = NO`. A flag is
   evidence toward tier B and never an automatic tier A.

THE DEDUPLICATION KEY, AND WHY IT HAS FIVE PARTS
------------------------------------------------
Measured on the 8,273-row TRIBAL extract:

    piid + mod                                  7,633 distinct  (640 collisions)
    piid + mod + txn                            7,638
    subtier + piid + mod + txn                  7,654
    subtier + piid + mod + txn + referencedIDV  8,273  <- unique

A delivery order's PIID is only unique WITHIN its parent IDV, so the referenced
IDV PIID is part of the identity, not decoration. `dateSigned` is deliberately
NOT in the key: a re-download must dedupe against what is already loaded, and a
date is a fact about the row, not a component of its name.

A transaction that matches more than one business-type variant is stored ONCE
with `matched_variants` carrying every variant that returned it, semicolon
separated, and `variant_class` set to ENTITY_OWNED if any entity variant
matched (a tribally owned firm that also self-certifies americanIndianOwned is
a tribal enterprise, not an individual). `class_conflict = 1` records that the
two classes both claimed the row so the case can be ruled rather than guessed.

INPUTS IT ACCEPTS
-----------------
Anything in data/raw/contracts/sam_contract_awards/ matching:
    sam_extract_<TOKEN>.zip          (what the browser/API download produces)
    sam_extract_<TOKEN>.csv
    sam_fy2000_2007_<class>_<variant>.csv   (what 141 download() writes)
Token -> variant/class is resolved from `_export_tokens.json`, which 141 wrote
when the submissions were accepted. If a file's token is not in that manifest
the file is REFUSED and named, never guessed at - a mislabelled variant would
put individual-owned rows into the tribal class silently.

TWO THINGS MEASURED WHEN THE OTHER FIVE EXTRACTS LANDED (2026-08-26 ~20:00)
---------------------------------------------------------------------------
Both were invisible in the one-variant rehearsal and both are recorded here so
the next reader does not rediscover them.

**1. THE EXTRACTS DO NOT SHARE A COLUMN SET.** Measured on the six files:

    INDIAN 379 . NATIVE AMERICAN 378 . AMERICAN INDIAN 374 . TRIBAL 372
    ALASKAN NATIVE 330 . NATIVE HAWAIIAN 322

SAM omits a column from an extract when it is empty for that whole result set,
so a column ABSENT from the header and a column PRESENT-BUT-BLANK are two
different facts that `row.get(col) or ""` renders identically. That is named
defect class 2b - *an absent column name reads as an empty source*. Concretely:
`awardeeUEIInformation.cageCode` is **absent from the NATIVE HAWAIIAN extract**,
so every NATIVE HAWAIIAN row would silently publish a blank `cage_code` and a
CAGE-coverage table would read it as "these firms have no CAGE".

So every file's header is now checked against the columns this loader reads:
  - a CRITICAL column absent (any part of the dedup key, fiscal year, date
    signed, obligation, UEI) **REFUSES the file, named**. A dedup key silently
    losing a part is the one failure this table cannot survive;
  - any other absent column is recorded per row in `source_columns_absent`, so
    the blank carries its own reason.

**2. IT WILL NOT FIT IN MEMORY AS A LIST.** The five outstanding extracts are
**380,374 rows** and the largest is 157,093 rows x 379 columns. `read_extract`
returned `list(csv.DictReader(...))`; materialising the INDIAN extract that way
costs roughly 3.5 GB against 4.6 GB free on this machine with six other agents
running. It is now `iter_extract()`, a GENERATOR, and normalised values are
pooled (`_intern`) - measured 6,857 -> 3,904 bytes per stored row on the
AMERICAN INDIAN extract, which is the difference between finishing and dying at
80%. Nothing about the merge semantics changed.
"""

import csv
import hashlib
import io
import json
import re
import sys
import zipfile
from collections import Counter, defaultdict
from datetime import date, datetime, timezone
from pathlib import Path

csv.field_size_limit(10 ** 9)

CEDAR = Path(r"C:\Users\esm247\Desktop\Cedar Press")
RAW = CEDAR / "data" / "raw" / "contracts" / "sam_contract_awards"
CLEAN = CEDAR / "data" / "clean"
REVIEW = CEDAR / "review"
CODEBOOK_DIR = CLEAN / "codebook"

TOKENS = RAW / "_export_tokens.json"
STATE = RAW / "_loader_state.json"
MANIFEST = CLEAN / "sam_prime_contracts_fy2000_2007._LICENSING_MANIFEST.json"

OUT = CLEAN / "sam_prime_contracts_fy2000_2007.csv"
OUT_PUB = CLEAN / "sam_prime_contracts_fy2000_2007_PUBLISHABLE.csv"
RECON = CLEAN / "sam_prime_contracts_fy2000_2007_reconciliation.csv"
FRAGMENT = CODEBOOK_DIR / "02e_sam_contract_awards.csv"
DATASET = "02e_sam_contract_awards"

PRIME = CLEAN / "prime_contracts.csv"

TODAY = date.today().isoformat()

# ---------------------------------------------------------------------------
# THE TWO CLASSES. Never summed. Recorded in LICENSING.md and in 141.
# ---------------------------------------------------------------------------
ENTITY_VARIANTS = ["INDIAN", "ALASKAN NATIVE", "NATIVE HAWAIIAN", "TRIBAL"]
INDIVIDUAL_VARIANTS = ["AMERICAN INDIAN", "NATIVE AMERICAN"]
VARIANT_CLASS = {**{v: "ENTITY_OWNED" for v in ENTITY_VARIANTS},
                 **{v: "INDIVIDUAL_NATIVE_OWNED" for v in INDIVIDUAL_VARIANTS}}
ALL_VARIANTS = ENTITY_VARIANTS + INDIVIDUAL_VARIANTS

# ---------------------------------------------------------------------------
# SOURCE COLUMNS. The extract has 372; these are the ones that carry meaning.
# ---------------------------------------------------------------------------
S = {
    "piid": "contractId.piid",
    "mod": "contractId.modificationNumber",
    "txn": "contractId.transactionNumber",
    "subtier": "contractId.subtier.code",
    "subtier_name": "contractId.subtier.name",
    "idv_piid": "contractId.referencedIDVPiid",
    "idv_mod": "contractId.referencedIDVModificationNumber",
    "date_signed": "awardDetails.dates.dateSigned",
    "fiscal_year": "awardDetails.dates.fiscalYear",
    "pop_start": "awardDetails.dates.periodOfPerformanceStartDate",
    "pop_end": "awardDetails.dates.ultimateCompletionDate",
    "action_obligation": "awardDetails.dollars.actionObligation",
    "base_all_options": "awardDetails.dollars.baseAndAllOptionsValue",
    "base_exercised": "awardDetails.dollars.baseAndExercisedOptionsValue",
    "total_action_obligation": "awardDetails.totalContractDollars.totalActionObligation",
    "awardee_name": "awardDetails.awardeeData.awardeeHeader.awardeeName",
    "legal_name": "awardDetails.awardeeData.awardeeHeader.legalBusinessName",
    "dba_name": "awardDetails.awardeeData.awardeeHeader.awardeeDoingBusinessAsName",
    "uei": "awardDetails.awardeeData.awardeeUEIInformation.uniqueEntityId",
    "cage": "awardDetails.awardeeData.awardeeUEIInformation.cageCode",
    "parent_uei": "awardDetails.awardeeData.awardeeUEIInformation.awardeeUltimateParentUniqueEntityId",
    "parent_name": "awardDetails.awardeeData.awardeeUEIInformation.awardeeUltimateParentName",
    "street1": "awardDetails.awardeeData.awardeeLocation.streetAddress1",
    "street2": "awardDetails.awardeeData.awardeeLocation.streetAddress2",
    "city": "awardDetails.awardeeData.awardeeLocation.city",
    "state": "awardDetails.awardeeData.awardeeLocation.state.code",
    "zip": "awardDetails.awardeeData.awardeeLocation.zip",
    "country": "awardDetails.awardeeData.awardeeLocation.country.code",
    "cong_district": "awardDetails.awardeeData.awardeeLocation.congressionalDistrict",
    "naics": "coreData.productOrServiceInformation.principalNaics[0].code",
    "naics_name": "coreData.productOrServiceInformation.principalNaics[0].name",
    "psc": "coreData.productOrServiceInformation.productOrService.code",
    "psc_name": "coreData.productOrServiceInformation.productOrService.name",
    "setaside": "coreData.competitionInformation.typeOfSetAside.name",
    "setaside_code": "coreData.competitionInformation.typeOfSetAside.code",
    "extent_competed": "coreData.competitionInformation.extentCompeted.name",
    "n_offers": "awardDetails.competitionInformation.numberOfOffersReceived",
    "contracting_dept": "coreData.federalOrganization.contractingInformation.contractingDepartment.name",
    "contracting_dept_code": "coreData.federalOrganization.contractingInformation.contractingDepartment.code",
    "contracting_subtier": "coreData.federalOrganization.contractingInformation.contractingSubtier.name",
    "contracting_office_code": "coreData.federalOrganization.contractingInformation.contractingOffice.code",
    "funding_dept": "coreData.federalOrganization.fundingInformation.fundingDepartment.name",
    "funding_dept_code": "coreData.federalOrganization.fundingInformation.fundingDepartment.code",
    "pop_state": "coreData.principalPlaceOfPerformance.state.code",
    "pop_city": "coreData.principalPlaceOfPerformance.city.name",
    "pop_county": "coreData.principalPlaceOfPerformance.county.name",
    "award_or_idv": "coreData.awardOrIDV",
    "award_type": "coreData.awardOrIDVType.name",
    "reason_for_mod": "contractId.reasonForModification.name",
    "org_type": "awardDetails.awardeeData.organizationFactors.organizationType",
    "state_of_incorporation": "awardDetails.awardeeData.organizationFactors.stateOfIncorporation.code",
    "description": "awardDetails.productOrServiceInformation.descriptionOfContractRequirement",
}

# Self-certified Native flags carried straight through, renamed but not judged.
FLAGS = {
    "flag_us_tribal_government": "awardDetails.awardeeData.awardeeBusinessTypes.usTribalGovernment",
    "flag_tribally_owned_firm": "awardDetails.awardeeData.socioEconomicData.triballyOwnedFirm",
    "flag_american_indian_owned": "awardDetails.awardeeData.socioEconomicData.americanIndianOwned",
    "flag_indian_tribe_federally_recognized": "awardDetails.awardeeData.socioEconomicData.indianTribeFederallyRecognized",
    "flag_alaskan_native_corporation_owned": "awardDetails.awardeeData.socioEconomicData.alaskanNativeCorporationOwnedFirm",
    "flag_native_hawaiian_org_owned": "awardDetails.awardeeData.socioEconomicData.nativeHawaiianOrganizationOwnedFirm",
    "flag_native_american_owned_minority": "awardDetails.awardeeData.socioEconomicData.isMinorityOwnedBusiness.nativeAmericanOwned",
    "flag_tribal_college": "awardDetails.awardeeData.educationalEntities.tribalCollege",
    "flag_alaskan_native_servicing_institution": "awardDetails.awardeeData.educationalEntities.alaskanNativeServicingInstitution",
    "flag_native_hawaiian_servicing_institution": "awardDetails.awardeeData.educationalEntities.nativeHawaiianServicingInstitution",
    # NOT a Native flag. It is the CONTAMINATION VECTOR - see the docstring.
    "flag_housing_authority_public_tribal": "awardDetails.awardeeData.otherGovernmentalEntities.housingAuthoritiesPublicTribal",
    # NOT A NATIVE FLAG EITHER, AND IT IS THE BIGGEST ONE. "Subcontinent Asian
    # (Asian-INDIAN) American Owned" contains the string "INDIAN", so
    # awardeeBusinessTypeName=INDIAN returns it. MEASURED on the INDIAN extract:
    # 102,587 of 157,093 rows / 3,774 UEIs / $11.13 BILLION. See the docstring.
    "flag_subcontinent_asian_indian_american_owned": "awardDetails.awardeeData.socioEconomicData.isMinorityOwnedBusiness.subcontinentAsianAsianIndianAmericanOwned",
    # Structural, for the individual-native class. NOT a Native flag either, and
    # NOT reliable as an individual-ownership marker - measured: CNI
    # Administration Services LLC (Chickasaw Nation Industries) carries
    # soleProprietorship = YES. See docs/INDIVIDUAL_NATIVE_CLASS_PROPOSAL.md.
    "flag_sole_proprietorship": "awardDetails.awardeeData.awardeeBusinessTypes.businessOrOrganization.soleProprietorship",
    "flag_for_profit": "awardDetails.awardeeData.organizationFactors.profitStructure.forProfitOrganization",
    "flag_non_profit": "awardDetails.awardeeData.organizationFactors.profitStructure.nonProfitOrganization",
    "flag_llc": "awardDetails.awardeeData.organizationFactors.limitedLiabilityCorporation",
    "flag_small_business": "awardDetails.awardeeData.socioEconomicData.smallBusiness",
    "flag_8a_participant": "awardDetails.awardeeData.certifications.sbaCertified8aProgramParticipant",
    "flag_self_certified_sdb": "awardDetails.awardeeData.certifications.selfCertifiedSmallDisadvantagedBusiness",
    "flag_veteran_owned": "awardDetails.awardeeData.socioEconomicData.veteranOwnedBusiness",
    "flag_women_owned": "awardDetails.awardeeData.socioEconomicData.womenOwnedBusiness",
}

# Flags that, if YES, mean the row belongs in a Native universe at all.
# `flag_housing_authority_public_tribal` is POINTEDLY not in this list.
NATIVE_FLAGS = [
    "flag_us_tribal_government", "flag_tribally_owned_firm",
    "flag_american_indian_owned", "flag_indian_tribe_federally_recognized",
    "flag_alaskan_native_corporation_owned", "flag_native_hawaiian_org_owned",
    "flag_native_american_owned_minority", "flag_tribal_college",
    "flag_alaskan_native_servicing_institution",
    "flag_native_hawaiian_servicing_institution",
]

# ---------------------------------------------------------------------------
# D&B OPEN DATA. Prefixed so a `SELECT *` cannot pretend not to know.
# ---------------------------------------------------------------------------
DNB_COLUMNS = [
    "dnb_awardee_legal_name",
    "dnb_awardee_name",
    "dnb_awardee_dba_name",
    "dnb_ultimate_parent_name",
    "dnb_awardee_street1",
    "dnb_awardee_street2",
    "dnb_awardee_city",
    "dnb_awardee_state",
    "dnb_awardee_zip",
    "dnb_awardee_country",
]

OUT_COLUMNS = [
    # --- identity ---
    "sam_transaction_key",
    "contract_number", "modification_number", "transaction_number",
    "referenced_idv_piid", "referenced_idv_modification_number",
    "contracting_subtier_code",
    # --- class, variant, provenance ---
    "variant_class", "matched_variants", "class_conflict",
    "source_system", "source_export_token", "source_file", "built_date",
    "source_columns_absent",
    # --- dates and money (contract facts - publish) ---
    "date_signed", "fiscal_year",
    "period_of_performance_start", "period_of_performance_end",
    "action_obligation", "base_and_all_options_value",
    "base_and_exercised_options_value", "total_action_obligation",
    # --- federal identifiers (publish - NOT D&B Open Data) ---
    "awardee_uei", "cage_code", "ultimate_parent_uei",
    # --- award facts (publish) ---
    "award_or_idv", "award_type", "reason_for_modification",
    "naics_code", "naics_name", "psc_code", "psc_name",
    "setaside_code", "setaside", "extent_competed", "number_of_offers",
    "contracting_department_code", "contracting_department",
    "contracting_subtier", "contracting_office_code",
    "funding_department_code", "funding_department",
    "place_of_performance_state", "place_of_performance_city",
    "place_of_performance_county",
    "organization_type", "state_of_incorporation",
    "contract_description",
    # --- Native typing: SELF-CERTIFIED, never adjudicated ---
    "socio_econ_basis",
    *FLAGS.keys(),
    "native_flag_any", "variant_match_basis", "include_in_native_universe",
    # --- reconciliation against prime_contracts.csv ---
    "recon_piid_held", "recon_piid_fy_held", "recon_uei_held",
    "novelty", "double_count_risk",
    # --- licensing ---
    "dnb_open_data_restricted",
    *DNB_COLUMNS,
]


# ---------------------------------------------------------------------------
def now():
    return datetime.now(timezone.utc).isoformat()


def load_state():
    if STATE.exists():
        try:
            return json.loads(STATE.read_text(encoding="utf-8-sig"))
        except Exception:
            pass
    return {"processed": {}, "history": []}


def save_state(st):
    tmp = STATE.with_suffix(".json.part")
    tmp.write_text(json.dumps(st, indent=1), encoding="utf-8")
    tmp.replace(STATE)


def token_manifest():
    """token -> (variant, class). Written by 141 when submissions were accepted.

    A file whose token is not here is REFUSED, not guessed. Guessing the variant
    would put INDIVIDUAL_NATIVE_OWNED rows into the ENTITY_OWNED class silently,
    which is the one error this dataset cannot survive.
    """
    if not TOKENS.exists():
        return {}
    body = json.loads(TOKENS.read_text(encoding="utf-8-sig"))
    return {t["exportToken"]: (t["variant"], t["class"])
            for t in body.get("tokens", [])}


def discover():
    """Every extract on disk, resolved to (path, variant, class, token)."""
    tm = token_manifest()
    found, refused = [], []
    for p in sorted(RAW.iterdir()):
        if p.suffix.lower() not in (".zip", ".csv"):
            continue
        if p.name.endswith(".part"):
            continue
        m = re.match(r"sam_extract_([A-Za-z0-9]+)\.(zip|csv)$", p.name)
        if m:
            tok = m.group(1)
            if tok in tm:
                found.append((p, tm[tok][0], tm[tok][1], tok))
            else:
                refused.append((p, f"token {tok!r} not in _export_tokens.json"))
            continue
        m = re.match(r"sam_fy2000_2007_([a-z_]+)_([a-z_]+)\.csv$", p.name)
        if m:
            # 141's download() naming: <class>_<variant>. Resolve by matching
            # the variant slug, so the class comes from VARIANT_CLASS and not
            # from the filename - a renamed file cannot reclassify a row.
            slug = p.stem[len("sam_fy2000_2007_"):]
            hit = [v for v in ALL_VARIANTS
                   if slug.endswith(v.replace(" ", "_").lower())]
            if hit:
                v = max(hit, key=len)
                tok = next((k for k, (vv, _) in tm.items() if vv == v), "")
                found.append((p, v, VARIANT_CLASS[v], tok))
            else:
                refused.append((p, "filename matches no known variant"))
            continue
    return found, refused


def member_name(path):
    """The single CSV member inside a zip, or the file's own name.

    A zip with more than one CSV member is REFUSED and named, never guessed at.
    """
    if path.suffix.lower() != ".zip":
        return path.name
    with zipfile.ZipFile(path) as z:
        members = [n for n in z.namelist() if n.lower().endswith(".csv")]
        if len(members) != 1:
            raise SystemExit(
                f"REFUSING {path.name}: expected exactly one CSV member, "
                f"found {len(members)}: {members}")
        return members[0]


def iter_extract(path):
    """STREAM rows out of a .zip (single CSV member) or a bare .csv.

    Deliberately a GENERATOR and not a list. MEASURED 2026-08-26: the INDIAN
    extract is 157,093 rows x 379 columns and the five outstanding extracts are
    380,374 rows in total; `list(csv.DictReader(...))` on the INDIAN file alone
    costs roughly 3.5 GB against 4.6 GB free with six other agents running.
    """
    if path.suffix.lower() == ".zip":
        with zipfile.ZipFile(path) as z:
            with z.open(member_name(path)) as fh:
                yield from csv.DictReader(io.TextIOWrapper(
                    fh, encoding="utf-8-sig", newline=""))
        return
    with open(path, encoding="utf-8-sig", newline="") as fh:
        yield from csv.DictReader(fh)


def extract_header(path):
    """The extract's own column list, read without materialising the file."""
    if path.suffix.lower() == ".zip":
        with zipfile.ZipFile(path) as z:
            with z.open(member_name(path)) as fh:
                return next(csv.reader(io.TextIOWrapper(
                    fh, encoding="utf-8-sig", newline="")))
    with open(path, encoding="utf-8-sig", newline="") as fh:
        return next(csv.reader(fh))


# The columns without which a row has no identity, no date, no money and no
# awardee. If one of these is ABSENT FROM THE HEADER the file is refused: a
# dedup key that silently loses a part collapses distinct transactions into one.
CRITICAL_SOURCE_COLS = [S["piid"], S["mod"], S["txn"], S["subtier"],
                        S["idv_piid"], S["date_signed"], S["fiscal_year"],
                        S["action_obligation"], S["uei"]]


def header_audit(path):
    """(absent_non_critical, absent_critical) for one extract.

    DEFECT CLASS 2b. SAM omits a column from an extract when it is empty for the
    whole result set, so `row.get(col) or ""` renders "column absent" and
    "column present and blank" identically. MEASURED: `cageCode` is absent from
    the NATIVE HAWAIIAN extract and `streetAddress2` from NATIVE HAWAIIAN and
    ALASKAN NATIVE. Without this audit those blanks would read as facts about
    the firms.
    """
    have = set(extract_header(path))
    needed = list(S.values()) + list(FLAGS.values())
    absent = [c for c in needed if c not in have]
    critical = [c for c in absent if c in CRITICAL_SOURCE_COLS]
    return sorted(c for c in absent if c not in critical), sorted(critical)


# Value pool. MEASURED on the 52,714-row AMERICAN INDIAN extract: pooling every
# stored value of 48 characters or less takes a normalised row from 6,857 bytes
# to 3,904. Agency names, PSC names, flag YES/NO and the empty string repeat
# across hundreds of thousands of rows; the description does not, and is skipped
# by the length test rather than by a guess about which column it is.
_POOL = {}


def _intern(v):
    if len(v) > 48:
        return v
    hit = _POOL.get(v)
    if hit is None:
        _POOL[v] = v
        return v
    return hit


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


def g(row, col):
    return (row.get(col) or "").strip()


def txn_key(row):
    """The five-part identity. See the docstring for the measurement."""
    parts = [g(row, S["subtier"]), g(row, S["piid"]), g(row, S["mod"]),
             g(row, S["txn"]), g(row, S["idv_piid"])]
    return "|".join(p.upper() for p in parts)


def iso_date(v):
    v = (v or "").strip()
    if not v:
        return ""
    return v[:10]


def num(v):
    v = (v or "").strip()
    if not v:
        return ""
    try:
        f = float(v)
    except ValueError:
        return ""
    return f"{f:.2f}"


# ---------------------------------------------------------------------------
def prime_index():
    """What prime_contracts.csv already holds, at three grains.

    NOT a row count comparison. FY2000-2007 in prime_contracts came from
    `master prime file.dta` at AWARD-YEAR-VENDOR grain (1.26 rows per
    contract-year); SAM is TRANSACTION grain (2.1+ per contract-year). Comparing
    row counts across that seam manufactures a number that means nothing.
    """
    piid, piid_fy, uei = set(), set(), set()
    n = 0
    with open(PRIME, encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            n += 1
            p = (row.get("contract_number") or "").strip().upper()
            if p:
                piid.add(p)
            f = (row.get("fiscal_year") or "").strip()
            try:
                fy = str(int(float(f)))
            except ValueError:
                fy = ""
            if p and fy:
                piid_fy.add((p, fy))
            u = (row.get("awardee_uei") or "").strip().upper()
            if u:
                uei.add(u)
    return {"rows": n, "piid": piid, "piid_fy": piid_fy, "uei": uei}


def normalise(row, variant, token, src_name, pidx, absent=""):
    piid = g(row, S["piid"]).upper()
    fy = g(row, S["fiscal_year"])
    uei = g(row, S["uei"]).upper()

    flags = {k: g(row, c).upper() for k, c in FLAGS.items()}
    native_any = any(flags.get(f) == "YES" for f in NATIVE_FLAGS)

    if native_any:
        basis = "NATIVE_FLAG"
    elif flags.get("flag_subcontinent_asian_indian_american_owned") == "YES":
        # THE LARGEST PARTIAL-MATCH TRAP IN THIS PULL. "Subcontinent Asian
        # (Asian-INDIAN) American Owned" contains "INDIAN", so the INDIAN
        # variant returns Asian-Indian-American-owned firms. Measured:
        # 102,587 rows / 3,774 UEIs / $11.13B, which is 65.3% of that extract.
        # Tested BEFORE the housing-authority branch because a firm can carry
        # both and this is the one that explains the INDIAN extract.
        basis = "SUBCONTINENT_ASIAN_INDIAN_AMERICAN_ONLY"
    elif flags.get("flag_housing_authority_public_tribal") == "YES":
        # The partial-match trap. "HOUSING AUTHORITIES PUBLIC/TRIBAL" contains
        # "TRIBAL". This is how City of Wichita entered a Native extract.
        basis = "HOUSING_AUTHORITY_PUBLIC_TRIBAL_ONLY"
    else:
        # A row in a Native extract carrying NO explanation at all. Named, not
        # counted silently - DEFECT 2c, a drop counter that does not name what
        # it dropped. Measured: 1 row per large extract.
        basis = "NO_NATIVE_FLAG_UNEXPLAINED"

    piid_held = piid in pidx["piid"]
    piid_fy_held = (piid, fy) in pidx["piid_fy"]
    if piid_fy_held:
        novelty = "PIID_FY_HELD"
    elif piid_held:
        novelty = "PIID_HELD_NEW_FY"
    else:
        novelty = "PIID_NEW"

    out = {c: "" for c in OUT_COLUMNS}
    out.update({
        "sam_transaction_key": txn_key(row),
        "contract_number": piid,
        "modification_number": g(row, S["mod"]),
        "transaction_number": g(row, S["txn"]),
        "referenced_idv_piid": g(row, S["idv_piid"]).upper(),
        "referenced_idv_modification_number": g(row, S["idv_mod"]),
        "contracting_subtier_code": g(row, S["subtier"]),

        "variant_class": VARIANT_CLASS[variant],
        "matched_variants": variant,
        "class_conflict": "0",
        "source_system": "SAM_CONTRACT_AWARDS",
        "source_export_token": token,
        "source_file": src_name,
        "built_date": TODAY,
        "source_columns_absent": absent,

        "date_signed": iso_date(g(row, S["date_signed"])),
        "fiscal_year": fy,
        "period_of_performance_start": iso_date(g(row, S["pop_start"])),
        "period_of_performance_end": iso_date(g(row, S["pop_end"])),
        "action_obligation": num(g(row, S["action_obligation"])),
        "base_and_all_options_value": num(g(row, S["base_all_options"])),
        "base_and_exercised_options_value": num(g(row, S["base_exercised"])),
        "total_action_obligation": num(g(row, S["total_action_obligation"])),

        "awardee_uei": uei,
        "cage_code": g(row, S["cage"]).upper(),
        "ultimate_parent_uei": g(row, S["parent_uei"]).upper(),

        "award_or_idv": g(row, S["award_or_idv"]),
        "award_type": g(row, S["award_type"]),
        "reason_for_modification": g(row, S["reason_for_mod"]),
        "naics_code": g(row, S["naics"]),
        "naics_name": g(row, S["naics_name"]),
        "psc_code": g(row, S["psc"]),
        "psc_name": g(row, S["psc_name"]),
        "setaside_code": g(row, S["setaside_code"]),
        "setaside": g(row, S["setaside"]),
        "extent_competed": g(row, S["extent_competed"]),
        "number_of_offers": g(row, S["n_offers"]),
        "contracting_department_code": g(row, S["contracting_dept_code"]),
        "contracting_department": g(row, S["contracting_dept"]),
        "contracting_subtier": g(row, S["contracting_subtier"]),
        "contracting_office_code": g(row, S["contracting_office_code"]),
        "funding_department_code": g(row, S["funding_dept_code"]),
        "funding_department": g(row, S["funding_dept"]),
        "place_of_performance_state": g(row, S["pop_state"]),
        "place_of_performance_city": g(row, S["pop_city"]),
        "place_of_performance_county": g(row, S["pop_county"]),
        "organization_type": g(row, S["org_type"]),
        "state_of_incorporation": g(row, S["state_of_incorporation"]),
        "contract_description": g(row, S["description"]),

        "socio_econ_basis": "SELF_CERTIFICATION",
        "native_flag_any": "1" if native_any else "0",
        "variant_match_basis": basis,
        "include_in_native_universe": "1" if native_any else "0",

        "recon_piid_held": "1" if piid_held else "0",
        "recon_piid_fy_held": "1" if piid_fy_held else "0",
        "recon_uei_held": "1" if uei and uei in pidx["uei"] else "0",
        "novelty": novelty,
        "double_count_risk": "1" if piid_fy_held else "0",

        "dnb_open_data_restricted": "1",
        "dnb_awardee_legal_name": g(row, S["legal_name"]),
        "dnb_awardee_name": g(row, S["awardee_name"]),
        "dnb_awardee_dba_name": g(row, S["dba_name"]),
        "dnb_ultimate_parent_name": g(row, S["parent_name"]),
        "dnb_awardee_street1": g(row, S["street1"]),
        "dnb_awardee_street2": g(row, S["street2"]),
        "dnb_awardee_city": g(row, S["city"]),
        "dnb_awardee_state": g(row, S["state"]),
        "dnb_awardee_zip": g(row, S["zip"]),
        "dnb_awardee_country": g(row, S["country"]),
    })
    out.update(flags)
    return {k: _intern(v) for k, v in out.items()}


# ---------------------------------------------------------------------------
def read_existing():
    if not OUT.exists():
        return {}
    with open(OUT, encoding="utf-8", newline="") as fh:
        return {r["sam_transaction_key"]: r for r in csv.DictReader(fh)}


def merge_variant(store, new_rows):
    """Union a variant's rows into the store. Returns (added, already_present).

    A transaction returned by two variants is stored ONCE. `matched_variants`
    accumulates; the class is ENTITY_OWNED if any entity variant claimed it,
    and `class_conflict` records that both classes did.
    """
    added = dup = 0
    for r in new_rows:
        k = r["sam_transaction_key"]
        prev = store.get(k)
        if prev is None:
            store[k] = r
            added += 1
            continue
        dup += 1
        variants = set(filter(None, (prev.get("matched_variants") or "").split(";")))
        variants |= set(filter(None, (r.get("matched_variants") or "").split(";")))
        classes = {VARIANT_CLASS[v] for v in variants if v in VARIANT_CLASS}
        prev["matched_variants"] = ";".join(sorted(variants))
        prev["variant_class"] = ("ENTITY_OWNED" if "ENTITY_OWNED" in classes
                                 else "INDIVIDUAL_NATIVE_OWNED")
        prev["class_conflict"] = "1" if len(classes) > 1 else "0"
        prev["source_export_token"] = ";".join(sorted(set(
            filter(None, (prev.get("source_export_token") or "").split(";")
                   + [r.get("source_export_token") or ""]))))
    return added, dup


TAG = "pre_163_load_sam_contract_awards"


def backup(path):
    """Tagged with the SCRIPT NAME, never the number.

    CONCURRENCY RULE 1, AGENTS.md: four agents each wrote a different
    `code/163_*.py` on 2026-08-26 and each backed up as `.bak_<date>_pre163`,
    after which one of them restored by glob and reverted seven files belonging
    to two other agents. The number is not an identity.
    """
    if not path.exists():
        return None
    b = path.with_suffix(path.suffix + f".bak_{TODAY}_{TAG}")
    n, cand = 1, b
    while cand.exists():
        n += 1
        cand = path.with_suffix(path.suffix + f".bak_{TODAY}_{TAG}_{n}")
    cand.write_bytes(path.read_bytes())
    return cand


def write_csv(path, columns, rows):
    tmp = path.with_suffix(path.suffix + ".part")
    with open(tmp, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=columns, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)
    tmp.replace(path)


# ---------------------------------------------------------------------------
def summary(rows):
    """Per class. NEVER a combined 'Native' total - that is the whole point."""
    out = []
    for cls in ("ENTITY_OWNED", "INDIVIDUAL_NATIVE_OWNED"):
        sub = [r for r in rows if r["variant_class"] == cls]
        if not sub:
            continue
        inc = [r for r in sub if r["include_in_native_universe"] == "1"]
        obl = sum(float(r["action_obligation"] or 0) for r in inc)
        out.append({
            "class": cls,
            "rows": len(sub),
            "rows_in_native_universe": len(inc),
            "distinct_piid": len({r["contract_number"] for r in sub}),
            "distinct_uei": len({r["awardee_uei"] for r in sub if r["awardee_uei"]}),
            "action_obligation_native_universe": round(obl, 2),
        })
    return out


def reconcile_report(rows, pidx):
    """Rows are per (class, variant-availability, novelty). No cross-class total."""
    recs = []
    for cls in ("ENTITY_OWNED", "INDIVIDUAL_NATIVE_OWNED"):
        sub = [r for r in rows if r["variant_class"] == cls]
        if not sub:
            continue
        for nov in ("PIID_FY_HELD", "PIID_HELD_NEW_FY", "PIID_NEW"):
            s = [r for r in sub if r["novelty"] == nov]
            if not s:
                continue
            recs.append({
                "generated": TODAY,
                "variant_class": cls,
                "grain_note": ("SAM is TRANSACTION grain; prime_contracts "
                               "FY2000-2007 is AWARD-YEAR-VENDOR grain. Row "
                               "counts are NOT comparable across the seam."),
                "novelty": nov,
                "sam_rows": len(s),
                "distinct_piid": len({r["contract_number"] for r in s}),
                "distinct_piid_fy": len({(r["contract_number"], r["fiscal_year"]) for r in s}),
                "distinct_uei": len({r["awardee_uei"] for r in s if r["awardee_uei"]}),
                "sam_action_obligation": round(
                    sum(float(r["action_obligation"] or 0) for r in s), 2),
                "rows_in_native_universe": sum(
                    1 for r in s if r["include_in_native_universe"] == "1"),
                "rows_excluded_partial_match_trap": sum(
                    1 for r in s
                    if r["variant_match_basis"] == "HOUSING_AUTHORITY_PUBLIC_TRIBAL_ONLY"),
                "double_count_risk_rows": sum(
                    1 for r in s if r["double_count_risk"] == "1"),
                "prime_contracts_rows_total": pidx["rows"],
            })
    return recs


def new_entities(rows, pidx):
    """UEIs this pull sees that prime_contracts.csv has never held.

    This is the entity-discovery prize and it goes to review/, never to the
    spine. A SAM flag is a self-certification; a spine row is a ruling.
    """
    agg = defaultdict(lambda: {"rows": 0, "obl": 0.0})
    for r in rows:
        u = r["awardee_uei"]
        if not u or u in pidx["uei"]:
            continue
        a = agg[u]
        a["rows"] += 1
        a["obl"] += float(r["action_obligation"] or 0)
        a["name"] = r["dnb_awardee_name"]
        a["parent_name"] = r["dnb_ultimate_parent_name"]
        a["parent_uei"] = r["ultimate_parent_uei"]
        a["cls"] = r["variant_class"]
        a["variants"] = r["matched_variants"]
        a["native_any"] = r["native_flag_any"]
        a["basis"] = r["variant_match_basis"]
        a["state"] = r["dnb_awardee_state"]
        a["sole_prop"] = r["flag_sole_proprietorship"]
    out = []
    for u, a in sorted(agg.items(), key=lambda kv: -kv[1]["obl"]):
        out.append({
            "awardee_uei": u,
            "variant_class": a["cls"],
            "matched_variants": a["variants"],
            "sam_rows": a["rows"],
            "action_obligation": round(a["obl"], 2),
            "native_flag_any": a["native_any"],
            "variant_match_basis": a["basis"],
            "flag_sole_proprietorship": a["sole_prop"],
            "ultimate_parent_uei": a["parent_uei"],
            "dnb_awardee_name": a["name"],
            "dnb_ultimate_parent_name": a["parent_name"],
            "dnb_awardee_state": a["state"],
            "spine_action": "UNRULED - candidate only. A SAM socio-economic "
                            "flag is self-certification, never a tier-A link.",
            "dnb_open_data_restricted": "1",
            "generated": TODAY,
        })
    return out


# ---------------------------------------------------------------------------
CODEBOOK_NOTES = {
    "sam_transaction_key": "Cedar-internal transaction identity: contracting subtier code | PIID | modification number | transaction number | referenced IDV PIID. Measured unique on 8,273/8,273 TRIBAL rows; PIID+modification alone collides 640 times because a delivery order PIID is unique only within its parent IDV.",
    "variant_class": "ENTITY_OWNED or INDIVIDUAL_NATIVE_OWNED. THESE TWO CLASSES MUST NEVER BE SUMMED INTO ONE 'Native' TOTAL. An individually Native-owned firm is not a tribal enterprise.",
    "matched_variants": "Every awardeeBusinessTypeName variant whose extract returned this transaction, semicolon separated. A transaction is stored once regardless of how many variants matched it.",
    "class_conflict": "1 when both classes claimed the same transaction. ENTITY_OWNED wins; the conflict is recorded rather than resolved silently.",
    "source_columns_absent": "Source columns this loader reads that were ABSENT FROM THIS EXTRACT'S HEADER, semicolon separated. SAM omits a column from an extract when it is empty for the whole result set, so an absent column and a present-but-blank column render identically through row.get(col) - named defect class 2b. MEASURED 2026-08-26: awardeeUEIInformation.cageCode is absent from the NATIVE HAWAIIAN extract, and awardeeLocation.streetAddress2 from NATIVE HAWAIIAN and ALASKAN NATIVE. Where this column names a field, that field's blank is a property of the EXTRACT and is not a fact about the firm. A file missing a CRITICAL column (any part of the dedup key, fiscal year, date signed, obligation, UEI) is refused outright and never reaches this table.",
    "socio_econ_basis": "Always SELF_CERTIFICATION. A SAM socio-economic flag is the firm's own assertion, not an adjudication. MEASURED: Goldbelt Raven LLC, an Alaska Native Corporation subsidiary, certifies alaskanNativeCorporationOwnedFirm = NO, triballyOwnedFirm = NO, americanIndianOwned = YES. Evidence toward tier B; never an automatic tier A.",
    "native_flag_any": "1 if any of the ten genuine Native self-certification flags is YES. flag_housing_authority_public_tribal is deliberately excluded from that test.",
    "variant_match_basis": "Why this row is in a Native extract at all. NATIVE_FLAG = one of the ten genuine Native self-certification flags is YES. SUBCONTINENT_ASIAN_INDIAN_AMERICAN_ONLY = the awardeeBusinessTypeName partial match hit 'Subcontinent Asian (Asian-Indian) American Owned Business', which contains the string 'INDIAN' and has nothing to do with American Indians; MEASURED 2026-08-26 on the INDIAN extract at 102,587 of 157,093 rows / 3,774 UEIs / $11,129,475,544 - 65.3% of that extract and by far the largest contamination vector in this pull. HOUSING_AUTHORITY_PUBLIC_TRIBAL_ONLY = the match hit the business type 'HOUSING AUTHORITIES PUBLIC/TRIBAL', which contains the string 'TRIBAL'; measured 87 rows / 11 UEIs / $710,492 on the TRIBAL extract, including City of Wichita, City of Dodge and the Housing Authority of the City of Los Angeles. NO_NATIVE_FLAG_UNEXPLAINED = a row in a Native extract carrying no Native flag and neither known trap; measured at 1 row per large extract, named rather than counted silently.",
    "flag_subcontinent_asian_indian_american_owned": "NOT A NATIVE FLAG, and the largest contamination vector in this pull. 'Subcontinent Asian (Asian-Indian) American Owned Business' contains the string 'INDIAN', so awardeeBusinessTypeName=INDIAN returns these firms. They are Asian-Indian-American owned and are not Native. MEASURED: 102,587 rows / 3,774 UEIs / $11.13B on the INDIAN extract. Kept because the raw is the raw; every one carries include_in_native_universe = 0. Never test Native status on it.",
    "include_in_native_universe": "0 for the partial-match trap rows. They are kept because the raw is the raw; they must be filtered out of any Native count.",
    "flag_housing_authority_public_tribal": "NOT A NATIVE FLAG. It is the contamination vector for the TRIBAL variant. Never test Native status on it.",
    "flag_sole_proprietorship": "Structural business type. NOT a reliable individual-ownership marker: MEASURED, CNI Administration Services LLC and CNI Manufacturing LLC (Chickasaw Nation Industries) both carry soleProprietorship = YES while carrying triballyOwnedFirm = YES. See docs/INDIVIDUAL_NATIVE_CLASS_PROPOSAL.md.",
    "novelty": "Reconciliation against data/clean/prime_contracts.csv. PIID_FY_HELD = this contract-year is already in prime_contracts. PIID_HELD_NEW_FY = the contract is held but not this fiscal year. PIID_NEW = the contract number appears nowhere in prime_contracts.",
    "double_count_risk": "1 when novelty = PIID_FY_HELD. Those dollars are already counted in prime_contracts at award-year-vendor grain. NEVER add this file's action_obligation to prime_contracts' total_obligations without excluding these rows.",
    "dnb_open_data_restricted": "Always 1. Every row is a base award dated before 2022-04-04, so D&B Open Data attaches to 100% of this table.",
    "action_obligation": "Transaction-level obligated dollars. SAM is TRANSACTION grain; prime_contracts FY2000-2007 is AWARD-YEAR-VENDOR grain from `master prime file.dta`. The two are not the same grain and row counts are not comparable.",
}

DNB_NOTE = ("D&B OPEN DATA - DO NOT DISSEMINATE IN BULK. SAM's disclaimer "
            "attaches this restriction to all base award notices dated before "
            "2022-04-04, which is 100% of this table. Internal matching, "
            "attribution and QA are unaffected; bulk publication is not "
            "permitted. Absent entirely from the *_PUBLISHABLE.csv view.")

DNB_PERSON_NOTE = (" ON INDIVIDUAL_NATIVE_OWNED ROWS THIS FIELD IS FREQUENTLY A "
                   "PRIVATE INDIVIDUAL'S NAME, because a sole proprietorship's "
                   "legal name usually is one. That is a privacy exposure a "
                   "tribal government's name is not, and it does not publish at "
                   "any tier, in bulk or singly.")


def infer_type(values):
    vals = [v for v in values if v not in ("", None)]
    if not vals:
        return "empty"
    if all(re.fullmatch(r"-?\d+", v) for v in vals):
        return "integer"
    if all(re.fullmatch(r"-?\d+(\.\d+)?", v) for v in vals):
        return "numeric"
    if all(re.fullmatch(r"\d{4}-\d{2}-\d{2}", v) for v in vals):
        return "date"
    return "text"


def write_fragment(rows):
    CODEBOOK_DIR.mkdir(parents=True, exist_ok=True)
    n = len(rows)
    out = []
    for col in OUT_COLUMNS:
        vals = [r.get(col, "") for r in rows]
        filled = sum(1 for v in vals if v not in ("", None))
        restricted = col.startswith("dnb_") and col != "dnb_open_data_restricted"
        desc = CODEBOOK_NOTES.get(col, "")
        if restricted:
            desc = DNB_NOTE
            if col in ("dnb_awardee_legal_name", "dnb_awardee_name",
                       "dnb_awardee_dba_name"):
                desc += DNB_PERSON_NOTE
        if not desc:
            desc = f"SAM Contract Awards field, normalised. See docs/SAM_EXTRACTION_PLAN.md."
        out.append({
            "dataset": DATASET,
            "variable": col,
            "type": infer_type(vals),
            "units": ("usd" if "obligation" in col or "value" in col
                      else "YYYY-MM-DD" if col.startswith("date") or "period_of" in col
                      else "flag" if col.startswith("flag_") or col in (
                          "native_flag_any", "class_conflict", "double_count_risk",
                          "include_in_native_universe", "dnb_open_data_restricted",
                          "recon_piid_held", "recon_piid_fy_held", "recon_uei_held")
                      else "code"),
            "pct_filled": round(100.0 * filled / n, 1) if n else 0.0,
            "n_rows": n,
            "published": 0 if restricted else 1,
            "access_tier": "internal" if restricted else "public",
            "description": desc,
            "generated": TODAY,
        })
    backup(FRAGMENT)
    write_csv(FRAGMENT, ["dataset", "variable", "type", "units", "pct_filled",
                         "n_rows", "published", "access_tier", "description",
                         "generated"], out)
    return len(out)


def write_manifest(rows):
    body = {
        "generated": now(),
        "dataset": DATASET,
        "file": OUT.name,
        "publishable_view": OUT_PUB.name,
        "source_system": "SAM_CONTRACT_AWARDS",
        "date_span_signed": "1999-10-01 .. 2007-09-30",
        "dnb_open_data_applies_to": "100% of rows - every row is a base award "
                                    "dated before 2022-04-04",
        "restricted_columns": DNB_COLUMNS,
        "restricted_rule": DNB_NOTE,
        "individual_native_privacy_rule": (
            "A sole proprietorship's legal business name is frequently a "
            "private individual's name. On INDIVIDUAL_NATIVE_OWNED rows the "
            "restricted name columns are a PRIVACY exposure independent of the "
            "D&B licence, and they do not publish at any tier - not in bulk, "
            "not per-entity lookup, not in a register. See "
            "docs/INDIVIDUAL_NATIVE_CLASS_PROPOSAL.md."),
        "publishable_columns": [c for c in OUT_COLUMNS if c not in DNB_COLUMNS],
        "class_rule": ("ENTITY_OWNED and INDIVIDUAL_NATIVE_OWNED are never "
                       "summed into one Native total."),
        "self_certification_rule": (
            "Every socio-economic flag here is the firm's own certification, "
            "not an adjudication. Goldbelt Raven LLC, an ANC subsidiary, "
            "certifies alaskanNativeCorporationOwnedFirm = NO."),
        "rows": len(rows),
        "rows_by_class": {c["class"]: c["rows"] for c in summary(rows)},
    }
    tmp = MANIFEST.with_suffix(".json.part")
    tmp.write_text(json.dumps(body, indent=1), encoding="utf-8")
    tmp.replace(MANIFEST)


# ---------------------------------------------------------------------------
def cmd_status():
    found, refused = discover()
    st = load_state()
    tm = token_manifest()
    print(f"  extracts on disk : {len(found)}")
    for p, v, c, tok in found:
        done = st["processed"].get(tok or p.name)
        print(f"    {v:16s} [{c:23s}] {p.name}"
              f"  {'LOADED ' + str(done['rows_in']) + ' rows' if done else 'PENDING'}")
    for p, why in refused:
        print(f"    REFUSED  {p.name}: {why}")
    have = {v for _, v, _, _ in found}
    missing = [v for v in ALL_VARIANTS if v not in have]
    print(f"  awaiting download : {missing if missing else 'none'}")
    print(f"  tokens on record  : {len(tm)}")
    # Counted with the csv reader, NOT by counting newlines. Two rows carry a
    # `contract_description` containing an embedded newline, so a line count
    # reads 8,324 where the table holds 8,273 - a discrepancy that looks like a
    # merge bug and is a quoting artefact.
    if OUT.exists():
        with open(OUT, encoding="utf-8", newline="") as fh:
            n = sum(1 for _ in csv.reader(fh)) - 1
        print(f"  output            : {OUT.name} ({n:,} rows)")
    else:
        print(f"  output            : {OUT.name} NOT BUILT")


def cmd_load(force=False):
    found, refused = discover()
    for p, why in refused:
        print(f"  REFUSED  {p.name}: {why}")
    if not found:
        print("  no extracts on disk - nothing to load")
        return
    st = load_state()

    # --- the header audit runs BEFORE anything is read, on every file --------
    # A critical column absent from a header refuses that file by name. Doing it
    # up front means a refusal costs no reading and cannot half-load a variant.
    audits, blocked = {}, []
    for p, variant, cls, tok in found:
        soft, hard = header_audit(p)
        audits[p.name] = (soft, hard)
        if hard:
            blocked.append((p, variant, hard))
        if soft:
            print(f"  {variant:16s} source columns ABSENT from the extract "
                  f"({len(soft)}), recorded per row in source_columns_absent:")
            for c in soft:
                print(f"      {c}")
    for p, variant, hard in blocked:
        print(f"  REFUSED  {p.name} [{variant}]: CRITICAL source column(s) "
              f"absent from the header - {hard}")
    found = [f for f in found if f[0] not in {b[0] for b in blocked}]
    if not found:
        print("  every extract was refused - nothing loaded")
        return

    # `--force` means re-process everything. Starting from the EXISTING output
    # would keep the old row on every key (merge_variant keeps `prev`), so a
    # forced rebuild would silently inherit whatever schema those rows were
    # written with. It rebuilds from the extracts instead - but only when every
    # token already in the state is still on disk, so a force can never drop
    # rows whose extract has gone.
    have_keys = {(tok or p.name) for p, _, _, tok in found}
    if force and set(st["processed"]) <= have_keys:
        store = {}
        print("  --force: rebuilding from the extracts "
              f"({len(st['processed'])} previously-processed token(s), all on disk)")
    else:
        store = read_existing()
        if force:
            missing = sorted(set(st["processed"]) - have_keys)
            print(f"  --force: keeping existing rows - processed token(s) not "
                  f"on disk: {missing}")
        print(f"  existing output rows: {len(store):,}")

    print("  indexing prime_contracts.csv ...")
    pidx = prime_index()
    print(f"    {pidx['rows']:,} rows  {len(pidx['piid']):,} PIID  "
          f"{len(pidx['piid_fy']):,} PIID x FY  {len(pidx['uei']):,} UEI")

    touched = False
    for p, variant, cls, tok in found:
        key = tok or p.name
        if key in st["processed"] and not force:
            print(f"  {variant:16s} already processed ({p.name}) - skip")
            continue
        digest = sha(p)
        member = member_name(p)
        absent = ";".join(audits[p.name][0])
        # STREAMED, one row at a time. See iter_extract's docstring.
        n_in = added = dup = 0
        for r in iter_extract(p):
            n_in += 1
            a, d = merge_variant(store, (normalise(r, variant, tok, member,
                                                   pidx, absent),))
            added += a
            dup += d
        st["processed"][key] = {
            "variant": variant, "class": cls, "file": p.name,
            "member": member, "sha256_16": digest, "rows_in": n_in,
            "rows_added": added, "rows_already_present": dup,
            "source_columns_absent": audits[p.name][0],
            "processed_utc": now(),
        }
        st["history"].append({"utc": now(), "variant": variant,
                              "file": p.name, "rows_in": n_in,
                              "added": added, "dup": dup})
        touched = True
        print(f"  {variant:16s} [{cls:23s}] {n_in:,} rows -> "
              f"+{added:,} new, {dup:,} already present from another variant")

    if not touched:
        print("  nothing new to load (use --force to re-process)")
        cmd_reconcile()
        return

    rows = sorted(store.values(),
                  key=lambda r: (r["fiscal_year"], r["contract_number"],
                                 r["modification_number"]))
    backup(OUT)
    write_csv(OUT, OUT_COLUMNS, rows)
    pub_cols = [c for c in OUT_COLUMNS if c not in DNB_COLUMNS]
    backup(OUT_PUB)
    write_csv(OUT_PUB, pub_cols, rows)
    write_manifest(rows)
    nvars = write_fragment(rows)
    save_state(st)

    recs = reconcile_report(rows, pidx)
    write_csv(RECON, list(recs[0].keys()), recs) if recs else None

    REVIEW.mkdir(parents=True, exist_ok=True)
    ne = new_entities(rows, pidx)
    if ne:
        write_csv(REVIEW / f"sam_fy2000_2007_new_entities_{TODAY}.csv",
                  list(ne[0].keys()), ne)

    print(f"\n  wrote {OUT.name}          {len(rows):,} rows x {len(OUT_COLUMNS)} cols")
    print(f"  wrote {OUT_PUB.name}  {len(rows):,} rows x {len(pub_cols)} cols "
          f"(no D&B columns)")
    print(f"  wrote {FRAGMENT.name}   {nvars} variables")
    print(f"  wrote {MANIFEST.name}")
    print(f"  wrote review/sam_fy2000_2007_new_entities_{TODAY}.csv  "
          f"{len(ne)} UEIs not in prime_contracts")
    print_summary(rows, recs)


def print_summary(rows, recs):
    print("\n  === PER CLASS (never summed) ===")
    for s in summary(rows):
        print(f"    {s['class']:24s} rows={s['rows']:,}  "
              f"in_native_universe={s['rows_in_native_universe']:,}  "
              f"PIID={s['distinct_piid']:,}  UEI={s['distinct_uei']:,}  "
              f"${s['action_obligation_native_universe']:,.0f}")
    print("\n  === RECONCILIATION vs prime_contracts.csv ===")
    for r in recs:
        print(f"    {r['variant_class']:24s} {r['novelty']:18s} "
              f"rows={r['sam_rows']:,}  PIID={r['distinct_piid']:,}  "
              f"PIIDxFY={r['distinct_piid_fy']:,}  "
              f"${r['sam_action_obligation']:,.0f}"
              f"{'  <- DOUBLE-COUNT RISK' if r['double_count_risk_rows'] else ''}")


def cmd_reconcile():
    if not OUT.exists():
        sys.exit(f"  {OUT.name} does not exist - run `load` first")
    with open(OUT, encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))
    pidx = prime_index()
    recs = reconcile_report(rows, pidx)
    if recs:
        write_csv(RECON, list(recs[0].keys()), recs)
    print_summary(rows, recs)


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "status"
    force = "--force" in sys.argv
    if mode == "status":
        cmd_status()
    elif mode == "load":
        cmd_load(force=force)
    elif mode == "reconcile":
        cmd_reconcile()
    else:
        sys.exit("usage: status | load [--force] | reconcile")


if __name__ == "__main__":
    main()
