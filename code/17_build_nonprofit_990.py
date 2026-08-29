#!/usr/bin/env python3
r"""
Cedar Press - 17: Native Nonprofit layer (Dataset 6) + EIN identifier harvest.

Builds, from the IRS Exempt Organizations Business Master File and the prior
tribal-990 identification work in the dissertation repo:

  data/spine/nonprofit_exclusion_rulings.csv   prior EXCLUSION rulings (block list)
  data/clean/np_orgs.csv                       candidate nonprofit universe + tiers
  data/clean/np_ein_uei_bridge.csv             EIN <-> UEI bridge rows
  data/raw/external/irs990/                    local copies + BMF slice + manifest

Rules honored
-------------
* No new ID system. entity_id is written BLANK - spine linking is the owner's job.
* Zero fabrication. classification_ruling is UNRULED unless an upstream file
  carries an actual ruling; the IRS BMF has no control-status field, so no
  Native-control claim is minted here. Evidence strings name the exact signals.
* Exclusions first. Anything Elijah already ruled OUT is tier X and carries
  excluded_by_prior_ruling=1, same jurisprudence model as the per-UEI drops.
* Self-contained. Sources are copied into data/raw/external/irs990/ with a
  manifest; the 323 MB BMF is streamed once (chunked, dtype=str) and a slice of
  the candidate EIN universe is written locally. All later steps read the slice.

Usage
-----
  py -3 code/17_build_nonprofit_990.py               # all steps
  py -3 code/17_build_nonprofit_990.py --steps 1,2   # selected steps
"""

from __future__ import annotations

import argparse
import csv
import re
import shutil
from collections import Counter
from datetime import date, datetime
from pathlib import Path

import pandas as pd

CEDAR = Path(r"C:\Users\esm247\Desktop\Cedar Press")
DISS = Path(r"C:\Users\esm247\Desktop\dissertation\data\tribal_federal_spending")
SAM = DISS / "sam_extracts"
BMF_DIR = DISS / "irs_bmf"

RAW = CEDAR / "data" / "raw" / "external" / "irs990"
SPINE = CEDAR / "data" / "spine"
CLEAN = CEDAR / "data" / "clean"

TODAY = date.today().isoformat()
BMF_SOURCE_URL = "https://www.irs.gov/pub/irs-soi/eo{n}.csv"
BMF_SOURCE_PAGE = ("https://www.irs.gov/charities-non-profits/"
                   "exempt-organizations-business-master-file-extract-eo-bmf")

# Source files: local name -> (source path, description)
SOURCES = {
    "tribal_irs990_candidates_2026_04_29.csv": (
        SAM / "tribal_irs990_candidates_2026_04_29.csv",
        "Net-1 raw candidate pool: BMF orgs whose name carries a tribal token"),
    "tribal_irs990_strict_2026_04_29.csv": (
        SAM / "tribal_irs990_strict_2026_04_29.csv",
        "Candidates name-matched to the canonical tribe table (ICR input)"),
    "tribal_irs990_state_validated_2026_04_29.csv": (
        SAM / "tribal_irs990_state_validated_2026_04_29.csv",
        "Strict rows whose IRS state is the tribe state or adjacent"),
    "tribal_irs990_unmatched_2026_04_29.csv": (
        SAM / "tribal_irs990_unmatched_2026_04_29.csv",
        "Distinctive-token orgs with no canonical tribe match"),
    "tribal_irs990_icr_high_confidence_2026_04_29.csv": (
        SAM / "tribal_irs990_icr_high_confidence_2026_04_29.csv",
        "Intercoder-reliability pass: 3+ of 5 coders agree"),
    "tribal_irs990_icr_review_queue_2026_04_29.csv": (
        SAM / "tribal_irs990_icr_review_queue_2026_04_29.csv",
        "Intercoder-reliability disagreements: exactly 2 of 5 coders"),
    "tribal_irs990_verified_2026_04_30.csv": (
        SAM / "tribal_irs990_verified_2026_04_30.csv",
        "ICR pool minus place-name false positives"),
    "tribal_irs990_verified_strict_2026_04_30.csv": (
        SAM / "tribal_irs990_verified_strict_2026_04_30.csv",
        "Strict-verified tribal nonprofit EINs (highest confidence)"),
    "tribal_irs990_dropped_falsepositive_2026_04_30.csv": (
        SAM / "tribal_irs990_dropped_falsepositive_2026_04_30.csv",
        "EXCLUSION RULINGS: place-name false positives ruled out"),
    "tribal_irs990_dropped_strict_2026_04_30.csv": (
        SAM / "tribal_irs990_dropped_strict_2026_04_30.csv",
        "EXCLUSION RULINGS: ambiguous-token orgs with no tribal-purpose signal"),
    "irs_990_to_federal_funding_match_2026_05_01.csv": (
        SAM / "irs_990_to_federal_funding_match_2026_05_01.csv",
        "EIN to federal-assistance recipient match (EIN<->UEI bridge source)"),
}

# ---------------------------------------------------------------------------
# Rule sets reproduced from the upstream verification scripts, so that each
# exclusion ruling can name the SPECIFIC rule that fired. Copied verbatim from
# verify_irs_990_with_real_filters.py and verify_irs_990_v2_strict.py.
# ---------------------------------------------------------------------------
PLACE_NAME_EXCLUSIONS = [
    r"\bWICHITA FALLS\b", r"\bWICHITA COUNTY\b", r"\bWICHITA STATE\b",
    r"\bWICHITA EAGLE\b", r"\bSEDGWICK COUNTY\b", r"\bDAKOTA STATE\b",
    r"\bDAKOTA WOOD\b", r"\bDAKOTA STAR\b", r"\bDAKOTA SONSHINE\b",
    r"\bDAKOTA SHRINE\b", r"\bDAKOTA TERRITORY\b", r"\bDAKOTA COUNTY\b",
    r"\bSOUTH DAKOTA\b", r"\bNORTH DAKOTA\b", r"\bDAKOTA BUSINESS\b",
    r"\bDAKOTA REAL ESTATE\b", r"\bACOMA STREET\b", r"\bAPACHE COUNTY\b",
    r"\bAPACHE JUNCTION\b", r"\bCOMANCHE COUNTY\b", r"\bSEMINOLE COUNTY\b",
    r"\bSEMINOLE HEIGHTS\b", r"\bMIAMI INDIAN\b", r"\bKLAMATH COUNTY\b",
    r"\bKLAMATH FALLS\b", r"\bMENOMINEE FALLS\b", r"\bONEIDA COUNTY\b",
    r"\bSENECA COUNTY\b", r"\bONONDAGA COUNTY\b", r"\bPENOBSCOT BAY\b",
    r"\bPENOBSCOT VALLEY\b", r"\bPENOBSCOT COUNTY\b", r"\bPENOBSCOT THEATRE\b",
    r"\bPENOBSCOT CHRISTIAN\b", r"\bPENOBSCOT KENNEL\b", r"\bMOHAWK VALLEY\b",
    r"\bMOHAWK COLLEGE\b", r"\bMOHEGAN LAKE\b", r"\bSHOSHONE COUNTY\b",
    r"\bSHOSHONE FALLS\b", r"\bCHEROKEE COUNTY\b", r"\bCHEROKEE TRAIL\b",
    r"\bCHEROKEE PARK\b", r"\bCHEROKEE STREET\b", r"\bCHEROKEE LAKE\b",
    r"\bCHEROKEE GARDEN\b", r"\bNAVAJO COUNTY\b", r"\bAPACHE TRAIL\b",
    r"\bPAWNEE COUNTY\b", r"\bOSAGE COUNTY\b", r"\bMICMAC COLLEGE\b",
    r"\bMICMAC FAMILY\b", r"\bGUTHRIE COMMUNITY\b", r"\bMOUNT MIWOK\b",
    r"\bPAIUTE WILDERNESS\b", r"\bCHIPPEWA FALLS\b", r"\bCHIPPEWA COUNTY\b",
    r"\bMUSKOGEE COUNTY\b", r"\bMUSKOGEE PHOENIX\b", r"\bCREEK COUNTY\b",
    r"\bSALISH SCHOOL\b", r"\bSALISH SEA\b", r"\bMOJAVE COUNTY\b",
    r"\bMOJAVE DESERT\b", r"\bYAVAPAI COUNTY\b", r"\bMARICOPA COUNTY\b",
    r"\bMARICOPA WELLS\b", r"\bPIMA COUNTY\b", r"\bPIMA COMMUNITY COLLEGE\b",
    r"\bGREEK\b", r"\bPI BETA PHI\b", r"\bDELTA SIGMA\b", r"\bSIGMA ALPHA\b",
    r"\bALPHA OMEGA\b", r"\bKAPPA SIGMA\b", r"\bIRISH CULTURAL\b",
    r"\bVIETNAMESE COMMUNITY\b", r"\bSCOTTISH HIGHLAND\b", r"\bSKI CLUB\b",
    r"\bJUNIOR GOLF\b", r"\bUMPIRES ASSOCIATION\b",
]

AMBIGUOUS_TRIBE_IDS = {
    "TRBF-WKWTOK-00", "TRBF-CHYNRV-00", "TRBF-KLAMTH-00", "TRBF-ACOMAP-00",
    "TRBF-LAGUNA-00", "TRBF-TAOSPB-00", "TRBF-SANDIA-00", "TRBF-CMNCHE-00",
    "TRBF-CHCKTW-00", "TRBF-OSAGEN-00", "TRBF-PEORIA-00", "TRBF-CADDON-00",
    "TRBF-ABSXFP-00", "TRBF-CHYARP-00", "TRBF-PNCANE-00", "TRBF-PUYLLP-00",
    "TRBF-MNMNEE-00", "TRBF-SMNLFL-00", "TRBF-CTWNAT-00", "TRBF-NAVAJO-00",
    "TRBF-CHKNAT-00", "TRBF-WASHOE-00", "TRBS-WCCMWS-00", "TRBF-CAYUGA-00",
    "TRBF-SNCCYG-00", "TRBF-WYNDTT-00", "TRBF-SRMHWK-00", "TRBF-ONDANY-00",
    "TRBF-WNNBGO-00", "TRBS-UHOUMA-00", "TRBF-BADRVR-00", "TRBF-SRPMCP-00",
}

TRIBAL_PURPOSE_RE = re.compile(
    r"\b(TRIBE|TRIBAL|NATION|RESERVATION|PUEBLO OF|RANCHERIA|"
    r"INDIAN COMMUNITY|INDIAN HEALTH|INDIAN HOUSING|INDIAN EDUCATION|"
    r"BAND OF|CONFEDERATED TRIBES|SELF[- ]GOVERNANCE|TRIBAL COUNCIL|"
    r"NATIVE AMERICAN|AFFILIATED TRIBES|TRIBAL HEAD ?START|"
    r"INDIAN TRIBE|FIRST NATION|INDIGENOUS|BIE TRIBAL|CULTURAL CENTER OF THE|"
    r"AND HAIDA|CHEROKEE NATION|CHOCTAW NATION|CHICKASAW NATION|"
    r"NAVAJO NATION|SEMINOLE NATION|HOPI TRIBE|YAKAMA NATION|"
    r"INDIAN HEALTH SERVICE|NATIVE COMMUNITY|TRIBAL HEALTH|TRIBAL SCHOOL|"
    r"TRIBAL ENTERPRISE|TRIBAL ENTERPRISES|TRIBE OF|NATION OF)\b")

# IRS BMF FILING_REQ_CD values that mean "not in the 990 universe".
# 00 not required, 06 church, 07 government 501(c)(1), 13 religious, 14 state
# institution. Source: IRS EO BMF data dictionary.
FILING_REQ_NOT_REQUIRED = {"00", "06", "07", "13", "14"}
FILING_REQ_990N = {"02"}          # 990-N e-Postcard filers
FILING_REQ_990_GROUP = {"03"}     # group return

# QC: names that read as county/civic/booster organizations sharing a tribal
# word. These are review flags, never rulings.
CIVIC_PLACE_RE = re.compile(
    r"\b(COUNTY|CITY OF|TOWN OF|STATE UNIVERSITY|UNIVERSITY OF|PUBLIC SCHOOL|"
    r"SCHOOL DISTRICT|CHAMBER OF COMMERCE|ROTARY|LIONS CLUB|KIWANIS|"
    r"ELECTRIC COOPERATIVE|ELECTRIC MEMBERSHIP|BOOSTER|PTA|PTO|"
    r"HISTORICAL SOCIETY|ARTS COUNCIL|FARM BUREAU|LIBRARY|"
    r"VOLUNTEER FIRE|CEMETERY ASSOCIATION)\b")

# QC: excluded orgs whose names read like real tribal institutions even though
# they lack the literal tribal-purpose terms the v2 filter required. Flag for
# re-check by the ruling authority; this asserts nothing about Native status.
RECHECK_INSTITUTION_RE = re.compile(
    r"\b(TECHNICAL COLLEGE|COMMUNITY COLLEGE|TRIBAL COLLEGE|HOUSING AUTHORITY|"
    r"HEALTH CENTER|HEALTH BOARD|HEAD ?START|CULTURAL CENTER|LANGUAGE|"
    r"CHILD DEVELOPMENT|ELDERS|GAMING (COMMISSION|AUTHORITY)|"
    r"UTILITY AUTHORITY|DEVELOPMENT (AUTHORITY|CORPORATION))\b")


def log(msg: str, fh) -> None:
    print(msg)
    fh.write(msg + "\n")
    fh.flush()


def norm_ein(x) -> str:
    if x is None or (isinstance(x, float)):
        return ""
    s = str(x).strip().replace("-", "")
    if not s or s.lower() == "nan":
        return ""
    return s.zfill(9)


# ---------------------------------------------------------------------------
# Step 1 - copy sources, inventory
# ---------------------------------------------------------------------------
def step1_copy_and_inventory(fh) -> dict:
    RAW.mkdir(parents=True, exist_ok=True)
    manifest_rows, counts = [], {}
    log("\n=== STEP 1: copy sources + inventory ===", fh)
    for name, (src, desc) in SOURCES.items():
        if not src.exists():
            log(f"  [MISSING] {src}", fh)
            continue
        dst = RAW / name
        shutil.copy2(src, dst)
        df = pd.read_csv(dst, dtype=str, low_memory=False)
        counts[name] = len(df)
        manifest_rows.append({
            "local_file": name,
            "source_path": str(src),
            "source_url": "IRS EO BMF derivative (built in dissertation repo)",
            "description": desc,
            "rows": len(df),
            "unique_eins": df["EIN"].nunique() if "EIN" in df.columns else "",
            "source_mtime": datetime.fromtimestamp(src.stat().st_mtime).date().isoformat(),
            "copied_date": TODAY,
        })
        log(f"  {len(df):>7,} rows  {name}", fh)

    for n in (1, 2, 3, 4):
        f = BMF_DIR / f"eo{n}.csv"
        if f.exists():
            manifest_rows.append({
                "local_file": f"eo{n}.csv (NOT copied - streamed; see slice below)",
                "source_path": str(f),
                "source_url": BMF_SOURCE_URL.format(n=n),
                "description": (f"IRS Exempt Organizations Business Master File region {n}; "
                                f"landing page {BMF_SOURCE_PAGE}"),
                "rows": "",
                "unique_eins": "",
                "source_mtime": datetime.fromtimestamp(f.stat().st_mtime).date().isoformat(),
                "copied_date": TODAY,
            })

    mpath = RAW / "_SOURCE_MANIFEST.csv"
    pd.DataFrame(manifest_rows).to_csv(mpath, index=False)
    log(f"  manifest -> {mpath.relative_to(CEDAR)}", fh)
    return counts


# ---------------------------------------------------------------------------
# Step 2 - stream the BMF, write a slice for the candidate EIN universe
# ---------------------------------------------------------------------------
BMF_KEEP = ["EIN", "NAME", "CITY", "STATE", "ZIP", "SUBSECTION", "RULING",
            "FOUNDATION", "STATUS", "TAX_PERIOD", "FILING_REQ_CD",
            "PF_FILING_REQ_CD", "ASSET_AMT", "INCOME_AMT", "REVENUE_AMT",
            "NTEE_CD"]


def universe_eins() -> set:
    eins = set()
    for name in SOURCES:
        p = RAW / name
        if not p.exists():
            continue
        d = pd.read_csv(p, dtype=str, usecols=["EIN"], low_memory=False)
        eins |= {norm_ein(x) for x in d["EIN"]}
    eins.discard("")
    return eins


def step2_bmf_slice(fh) -> None:
    log("\n=== STEP 2: stream IRS BMF (chunked) -> local slice ===", fh)
    eins = universe_eins()
    log(f"  candidate EIN universe: {len(eins):,}", fh)

    frames, total_rows = [], 0
    for n in (1, 2, 3, 4):
        f = BMF_DIR / f"eo{n}.csv"
        if not f.exists():
            log(f"  [MISSING] {f}", fh)
            continue
        region_rows, region_hits = 0, 0
        for chunk in pd.read_csv(f, dtype=str, chunksize=200_000, low_memory=False,
                                 encoding="utf-8", encoding_errors="replace"):
            region_rows += len(chunk)
            chunk["EIN_N"] = chunk["EIN"].map(norm_ein)
            hit = chunk[chunk["EIN_N"].isin(eins)]
            if len(hit):
                keep = [c for c in BMF_KEEP if c in hit.columns]
                sub = hit[keep + ["EIN_N"]].copy()
                sub["bmf_region"] = str(n)
                frames.append(sub)
                region_hits += len(hit)
        total_rows += region_rows
        log(f"  eo{n}.csv: {region_rows:,} rows streamed, {region_hits:,} universe hits", fh)

    bmf = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    bmf = bmf.drop_duplicates(subset=["EIN_N"], keep="first")
    out = RAW / "irs_bmf_slice_universe_2026-08-05.csv"
    bmf.to_csv(out, index=False)
    log(f"  BMF total rows streamed: {total_rows:,}", fh)
    log(f"  slice rows (unique EIN): {len(bmf):,} -> {out.relative_to(CEDAR)}", fh)
    log(f"  universe EINs NOT in current BMF: {len(eins) - len(bmf):,} "
        f"(revoked, merged, or EIN drift)", fh)


# ---------------------------------------------------------------------------
# Step 3 - exclusion jurisprudence
# ---------------------------------------------------------------------------
def which_place_rule(name: str) -> str:
    up = (name or "").upper()
    hits = [p for p in PLACE_NAME_EXCLUSIONS if re.search(p, up)]
    return "; ".join(h.replace(r"\b", "") for h in hits)


def step3_exclusions(fh) -> pd.DataFrame:
    log("\n=== STEP 3: exclusion jurisprudence ===", fh)
    rows = []

    fp = pd.read_csv(RAW / "tribal_irs990_dropped_falsepositive_2026_04_30.csv",
                     dtype=str, low_memory=False)
    for _, r in fp.iterrows():
        name = r.get("NAME") or ""
        rule = which_place_rule(name)
        ev = (f"Name matches place-name exclusion pattern [{rule}] from "
              f"verify_irs_990_with_real_filters.py PLACE_NAME_EXCLUSIONS; "
              f"no strong tribal-purpose pattern override. "
              f"ICR was {r.get('n_coders_agree')}/5 coders, entered from "
              f"{'high-confidence' if r.get('orig') == 'hc' else 'review-queue'} pool; "
              f"token-matched tribe {r.get('tribe_id') or 'none'} "
              f"({r.get('canonical_name') or 'unmatched'}); IRS state {r.get('STATE')}."
              ) if rule else (
              f"Ruled out in verify_irs_990_with_real_filters.py place-name pass "
              f"(specific pattern not reproducible from name text); ICR "
              f"{r.get('n_coders_agree')}/5 coders; token-matched tribe "
              f"{r.get('tribe_id') or 'none'}.")
        rows.append({
            "ein": norm_ein(r.get("EIN")),
            "org_name": name,
            "exclusion_reason": "place_name_false_positive",
            "evidence": ev,
            "source_file": "tribal_irs990_dropped_falsepositive_2026_04_30.csv",
            "ruled_date": "2026-04-30",
            "ruled_by": "Elijah Moreno (rule set authored in verify_irs_990_with_real_filters.py)",
            "ruling_type": "rule_based_script_filter",
            "recheck_candidate": int(bool(RECHECK_INSTITUTION_RE.search((name or "").upper()))),
            "state": r.get("STATE") or "",
            "tribe_id_token_match": r.get("tribe_id") or "",
            "n_coders_agree": r.get("n_coders_agree") or "",
        })

    ds = pd.read_csv(RAW / "tribal_irs990_dropped_strict_2026_04_30.csv",
                     dtype=str, low_memory=False)
    for _, r in ds.iterrows():
        name = r.get("NAME") or ""
        tid = r.get("tribe_id") or ""
        amb = tid in AMBIGUOUS_TRIBE_IDS
        purpose = bool(TRIBAL_PURPOSE_RE.search((name or "").upper()))
        ev = (f"Token-matched tribe {tid} ({r.get('canonical_name') or ''}) is on the "
              f"ambiguous-token list in verify_irs_990_v2_strict.py (tribe name overlaps a "
              f"major non-tribal place name), and the org name carries no explicit "
              f"tribal-purpose term (Tribe/Nation/Reservation/Pueblo of/Band of/"
              f"Rancheria/Indian Community/Tribal Council). ICR "
              f"{r.get('n_coders_agree')}/5 coders; IRS state {r.get('STATE')}."
              ) if amb and not purpose else (
              f"Dropped by the v2 strict pass; token-matched tribe {tid}; ambiguous_token="
              f"{amb}; tribal_purpose_term_present={purpose}; ICR "
              f"{r.get('n_coders_agree')}/5 coders.")
        rows.append({
            "ein": norm_ein(r.get("EIN")),
            "org_name": name,
            "exclusion_reason": ("ambiguous_place_token_no_tribal_purpose"
                                 if amb and not purpose else "v2_strict_drop_other"),
            "evidence": ev,
            "source_file": "tribal_irs990_dropped_strict_2026_04_30.csv",
            "ruled_date": "2026-04-30",
            "ruled_by": "Elijah Moreno (rule set authored in verify_irs_990_v2_strict.py)",
            "ruling_type": "rule_based_script_filter",
            "recheck_candidate": int(bool(RECHECK_INSTITUTION_RE.search((name or "").upper()))),
            "state": r.get("STATE") or "",
            "tribe_id_token_match": tid,
            "n_coders_agree": r.get("n_coders_agree") or "",
        })

    ex = pd.DataFrame(rows)
    # An EIN can be ruled out by both passes; keep both rulings but flag.
    ex["n_rulings_for_ein"] = ex.groupby("ein")["ein"].transform("size")
    ex = ex.sort_values(["ein", "source_file"]).reset_index(drop=True)
    ex.insert(0, "exclusion_id", [f"NPEXCL-{i:05d}" for i in range(1, len(ex) + 1)])
    ex["extracted_date"] = TODAY

    SPINE.mkdir(parents=True, exist_ok=True)
    out = SPINE / "nonprofit_exclusion_rulings.csv"
    ex.to_csv(out, index=False)
    log(f"  rulings written: {len(ex):,} rows, {ex['ein'].nunique():,} unique EINs "
        f"-> {out.relative_to(CEDAR)}", fh)
    for k, v in Counter(ex["exclusion_reason"]).most_common():
        log(f"    {v:>6,}  {k}", fh)
    dual = (ex["n_rulings_for_ein"].astype(int) > 1).sum()
    log(f"  EINs ruled out by BOTH passes: {dual // 2:,}", fh)
    rc = int(ex["recheck_candidate"].sum())
    log(f"  recheck_candidate=1 (name reads like a tribal institution despite the drop): "
        f"{rc:,} -- these need a human ruling before the block list is treated as final", fh)
    for _, r in ex[ex.recheck_candidate == 1].head(15).iterrows():
        log(f"    RECHECK {r['ein']}  {r['org_name']}  ({r['state']})", fh)
    return ex


# ---------------------------------------------------------------------------
# Step 4 - np_orgs
# ---------------------------------------------------------------------------
def load(name: str) -> pd.DataFrame:
    d = pd.read_csv(RAW / name, dtype=str, low_memory=False)
    d["EIN_N"] = d["EIN"].map(norm_ein)
    return d


def tier_from_bmf(row) -> tuple:
    """990 tier + the basis for it, from BMF filing-requirement + dollar fields."""
    req = (row.get("FILING_REQ_CD") or "").strip()
    if not req or pd.isna(row.get("FILING_REQ_CD")):
        return "UNKNOWN", "no BMF row for this EIN (not in current BMF snapshot)"
    if req in FILING_REQ_990N:
        return "990_N", "BMF FILING_REQ_CD=02 (990-N e-Postcard, under filing threshold)"
    if req in FILING_REQ_NOT_REQUIRED:
        return "not_required_to_file", f"BMF FILING_REQ_CD={req} (church/government/state/religious - exempt from filing)"
    rev = pd.to_numeric(row.get("REVENUE_AMT"), errors="coerce")
    ast = pd.to_numeric(row.get("ASSET_AMT"), errors="coerce")
    if pd.isna(rev) and pd.isna(ast):
        return "UNKNOWN", f"BMF FILING_REQ_CD={req} but no revenue/asset amounts reported"
    rev = 0 if pd.isna(rev) else rev
    ast = 0 if pd.isna(ast) else ast
    if rev < 200_000 and ast < 500_000:
        return "990_EZ", (f"BMF FILING_REQ_CD={req}; REVENUE_AMT={rev:,.0f} < 200k and "
                          f"ASSET_AMT={ast:,.0f} < 500k (990-EZ eligibility thresholds)")
    return "full_990", (f"BMF FILING_REQ_CD={req}; REVENUE_AMT={rev:,.0f}, "
                        f"ASSET_AMT={ast:,.0f} above 990-EZ thresholds")


def step4_np_orgs(ex: pd.DataFrame, fh) -> pd.DataFrame:
    log("\n=== STEP 4: np_orgs ===", fh)

    cand = load("tribal_irs990_candidates_2026_04_29.csv")
    strict = load("tribal_irs990_strict_2026_04_29.csv")
    stval = load("tribal_irs990_state_validated_2026_04_29.csv")
    unm = load("tribal_irs990_unmatched_2026_04_29.csv")
    hc = load("tribal_irs990_icr_high_confidence_2026_04_29.csv")
    rq = load("tribal_irs990_icr_review_queue_2026_04_29.csv")
    ver = load("tribal_irs990_verified_2026_04_30.csv")
    vstr = load("tribal_irs990_verified_strict_2026_04_30.csv")

    s_cand, s_strict, s_stval = set(cand.EIN_N), set(strict.EIN_N), set(stval.EIN_N)
    s_unm, s_hc, s_rq = set(unm.EIN_N), set(hc.EIN_N), set(rq.EIN_N)
    s_ver, s_vstr = set(ver.EIN_N), set(vstr.EIN_N)
    s_excl = set(ex["ein"])
    log(f"  set sizes: candidates {len(s_cand):,}, strict {len(s_strict):,}, "
        f"state_validated {len(s_stval):,}, ICR-HC {len(s_hc):,}, ICR-RQ {len(s_rq):,}, "
        f"verified {len(s_ver):,}, verified_strict {len(s_vstr):,}, excluded {len(s_excl):,}", fh)
    log(f"  strict subset of candidates: {len(s_strict - s_cand) == 0} "
        f"({len(s_strict - s_cand):,} strict EINs absent from candidates)", fh)

    # widest record per EIN: prefer the richest upstream row
    base = {}
    for df, tag in ((cand, "candidates"), (unm, "unmatched"), (strict, "strict"),
                    (stval, "state_validated"), (rq, "icr_review_queue"),
                    (hc, "icr_high_confidence"), (ver, "verified"), (vstr, "verified_strict")):
        for _, r in df.iterrows():
            e = r["EIN_N"]
            rec = base.setdefault(e, {"source_files": []})
            rec["source_files"].append(tag)
            for c in ("NAME", "STATE", "CITY", "NTEE_CD", "tribe_id", "canonical_name",
                      "n_coders_agree", "coder_A_distinctive", "coder_B_state",
                      "coder_C_ntee", "coder_D_strong", "coder_E_usaspending",
                      "attribution_method"):
                v = r.get(c)
                if isinstance(v, str) and v.strip():
                    rec[c] = v.strip()

    bmf = pd.read_csv(RAW / "irs_bmf_slice_universe_2026-08-05.csv", dtype=str,
                      low_memory=False).set_index("EIN_N")
    excl_map = (ex.groupby("ein")
                  .agg(reason=("exclusion_reason", lambda s: "|".join(sorted(set(s)))),
                       srcs=("source_file", lambda s: "|".join(sorted(set(s))))).to_dict("index"))

    rows = []
    for e, rec in base.items():
        b = bmf.loc[e].to_dict() if e in bmf.index else {}
        tier, tier_basis = tier_from_bmf(b) if b else ("UNKNOWN", "no BMF row for this EIN")

        if e in s_excl:
            ctier, stage = "X", "excluded_by_prior_ruling"
        elif e in s_vstr:
            ctier, stage = "A", "verified_strict"
        elif e in s_ver:
            ctier, stage = "B", "verified_not_strict"
        elif e in s_hc:
            ctier, stage = "B", "icr_high_confidence"
        elif e in s_rq:
            ctier, stage = "B", "icr_review_queue"
        elif e in s_stval:
            ctier, stage = "B", "state_validated"
        elif e in s_strict:
            ctier, stage = "B", "canonical_name_match"
        else:
            ctier, stage = "B", "raw_name_candidate"

        coders = [rec.get(c, "0") for c in ("coder_A_distinctive", "coder_B_state",
                                            "coder_C_ntee", "coder_D_strong",
                                            "coder_E_usaspending")]
        ev = []
        if rec.get("tribe_id"):
            ev.append(f"BMF name matched canonical tribe {rec['tribe_id']} "
                      f"({rec.get('canonical_name', '')}) via "
                      f"{rec.get('attribution_method', 'name match')}")
        else:
            ev.append(f"BMF name carries a tribal token; no canonical tribe match "
                      f"({rec.get('attribution_method', 'unmatched')})")
        if rec.get("n_coders_agree"):
            ev.append(f"ICR {rec['n_coders_agree']}/5 coders agree "
                      f"(A_distinctive={coders[0]}, B_state={coders[1]}, C_ntee={coders[2]}, "
                      f"D_strong={coders[3]}, E_usaspending={coders[4]})")
        if stage == "verified_strict":
            ev.append("survived place-name filter and v2 ambiguous-token strict filter")
        elif stage == "verified_not_strict":
            ev.append("survived place-name filter; dropped by v2 strict filter")
        if e in excl_map:
            ev.append(f"PRIOR EXCLUSION RULING: {excl_map[e]['reason']} "
                      f"({excl_map[e]['srcs']})")
        if b:
            ev.append(f"present in IRS EO BMF snapshot (STATUS={b.get('STATUS')}, "
                      f"SUBSECTION={b.get('SUBSECTION')}, TAX_PERIOD={b.get('TAX_PERIOD')})")
        else:
            ev.append("not present in the IRS EO BMF snapshot streamed 2026-08-05")

        org_name = rec.get("NAME", b.get("NAME", ""))
        civic = CIVIC_PLACE_RE.search((org_name or "").upper())
        if civic:
            ev.append(f"REVIEW FLAG: org name contains civic/place descriptor "
                      f"'{civic.group(0)}' - classic place-name trap, do not treat the "
                      f"tier label as a Native-status ruling")

        rows.append({
            "EIN": e,
            "entity_id": "",                       # spine linking is not done here
            "org_name": org_name,
            "classification_ruling": "UNRULED",
            "evidence": "; ".join(ev),
            "tier": tier,
            "tier_basis": tier_basis,
            "state": rec.get("STATE", b.get("STATE", "")),
            "city": rec.get("CITY", b.get("CITY", "")),
            "ntee_code": rec.get("NTEE_CD", b.get("NTEE_CD", "")),
            "confidence_tier": ctier,
            "funnel_stage": stage,
            "review_flag": ("civic_or_place_descriptor_in_name" if civic else ""),
            "review_flag_token": (civic.group(0) if civic else ""),
            "excluded_by_prior_ruling": 1 if e in s_excl else 0,
            "exclusion_reason": excl_map.get(e, {}).get("reason", ""),
            "tribe_id_token_match": rec.get("tribe_id", ""),
            "canonical_name_token_match": rec.get("canonical_name", ""),
            "n_coders_agree": rec.get("n_coders_agree", ""),
            "bmf_in_snapshot": 1 if b else 0,
            "bmf_status": b.get("STATUS", ""),
            "bmf_subsection": b.get("SUBSECTION", ""),
            "bmf_filing_req_cd": b.get("FILING_REQ_CD", ""),
            "bmf_foundation_cd": b.get("FOUNDATION", ""),
            "bmf_irs_ruling_yyyymm": b.get("RULING", ""),
            "bmf_tax_period": b.get("TAX_PERIOD", ""),
            "bmf_revenue_amt": b.get("REVENUE_AMT", ""),
            "bmf_asset_amt": b.get("ASSET_AMT", ""),
            "bmf_income_amt": b.get("INCOME_AMT", ""),
            "source_files": "|".join(sorted(set(rec["source_files"]))),
            "source_dataset": "IRS Exempt Organizations Business Master File (eo1-eo4)",
            "source_url": BMF_SOURCE_PAGE,
            "bmf_vintage_fetched": "2026-04-29",
            "built_date": TODAY,
        })

    np_orgs = pd.DataFrame(rows).sort_values(
        ["confidence_tier", "state", "org_name"]).reset_index(drop=True)
    CLEAN.mkdir(parents=True, exist_ok=True)
    out = CLEAN / "np_orgs.csv"
    np_orgs.to_csv(out, index=False, quoting=csv.QUOTE_MINIMAL)
    log(f"  np_orgs: {len(np_orgs):,} rows -> {out.relative_to(CEDAR)}", fh)
    log("  --- confidence_tier ---", fh)
    for k, v in np_orgs["confidence_tier"].value_counts().items():
        log(f"    {v:>7,}  {k}", fh)
    log("  --- funnel_stage ---", fh)
    for k, v in np_orgs["funnel_stage"].value_counts().items():
        log(f"    {v:>7,}  {k}", fh)
    log("  --- 990 tier ---", fh)
    for k, v in np_orgs["tier"].value_counts().items():
        log(f"    {v:>7,}  {k}", fh)
    log("  --- 990 tier within confidence tier A ---", fh)
    for k, v in np_orgs.loc[np_orgs.confidence_tier == "A", "tier"].value_counts().items():
        log(f"    {v:>7,}  {k}", fh)
    log("  --- classification_ruling ---", fh)
    for k, v in np_orgs["classification_ruling"].value_counts().items():
        log(f"    {v:>7,}  {k}", fh)
    rev = pd.to_numeric(np_orgs.loc[np_orgs.confidence_tier == "A", "bmf_revenue_amt"],
                        errors="coerce")
    log(f"  tier-A reported BMF revenue: n={rev.notna().sum():,}, "
        f"sum=${rev.sum() / 1e6:,.1f}M, max=${rev.max() / 1e6:,.1f}M", fh)
    log("  --- REVIEW FLAGS (civic/place descriptor in org name) ---", fh)
    for t in ("A", "B", "X"):
        sub = np_orgs[np_orgs.confidence_tier == t]
        n = (sub["review_flag"] != "").sum()
        log(f"    tier {t}: {n:,} of {len(sub):,} flagged ({100 * n / max(len(sub), 1):.1f}%)", fh)
    log("  tier-A flagged examples (place-name leak through the strict filter):", fh)
    for _, r in np_orgs[(np_orgs.confidence_tier == "A") &
                        (np_orgs.review_flag != "")].head(12).iterrows():
        log(f"    {r['EIN']}  {r['org_name']}  ({r['state']})", fh)
    return np_orgs


# ---------------------------------------------------------------------------
# Step 5 - EIN <-> UEI bridge + net-new identifier count
# ---------------------------------------------------------------------------
def step5_bridge(np_orgs: pd.DataFrame, fh) -> pd.DataFrame:
    log("\n=== STEP 5: EIN <-> UEI bridge ===", fh)
    br = load("irs_990_to_federal_funding_match_2026_05_01.csv")
    log(f"  bridge source rows: {len(br):,}; with recipient_uei: "
        f"{br['recipient_uei'].notna().sum():,}; with assistance dollars: "
        f"{br['total_fed_assist_M'].notna().sum():,}", fh)

    tier_map = dict(zip(np_orgs["EIN"], np_orgs["confidence_tier"]))
    stage_map = dict(zip(np_orgs["EIN"], np_orgs["funnel_stage"]))

    rows = []
    for _, r in br[br["recipient_uei"].notna()].iterrows():
        e = norm_ein(r["EIN"])
        rows.append({
            "ein": e,
            "uei": (r["recipient_uei"] or "").strip().upper(),
            "org_name": r.get("NAME", ""),
            "match_method": "normalized_name_plus_state_exact",
            "match_evidence": (
                f"IRS BMF org name normalized (uppercase, non-alphanumeric stripped, "
                f"whitespace collapsed) and joined to USAspending assistance recipients "
                f"aggregated by (normalized recipient_name, recipient_state_code); "
                f"IRS state {r.get('STATE')}; matched assistance obligations "
                f"${float(r['total_fed_assist_M']):,.3f}M; EIN token-matched to tribe "
                f"{r.get('tribe_id')} ({r.get('canonical_name')}); "
                f"built by enrich_need_v2.py step [4]"),
            "total_fed_assist_M": r.get("total_fed_assist_M", ""),
            "tribe_id_token_match": r.get("tribe_id", ""),
            "canonical_name_token_match": r.get("canonical_name", ""),
            "ein_confidence_tier": tier_map.get(e, ""),
            "ein_funnel_stage": stage_map.get(e, ""),
            "confidence_tier": "B",   # name+state join, algorithmic and unreviewed
            "confidence_tier_rationale": (
                "Name-plus-state exact join on normalized strings, no UEI-level "
                "verification; algorithmic and unreviewed"),
            "review_flag": ("civic_or_place_descriptor_in_name"
                            if CIVIC_PLACE_RE.search((r.get("NAME") or "").upper()) else ""),
            "source_file": "irs_990_to_federal_funding_match_2026_05_01.csv",
            "source_dataset": "IRS EO BMF x USAspending assistance prime awards",
            "built_date": TODAY,
        })

    bridge = pd.DataFrame(rows).drop_duplicates(subset=["ein", "uei"])
    out = CLEAN / "np_ein_uei_bridge.csv"
    bridge.to_csv(out, index=False)
    log(f"  bridge rows written: {len(bridge):,} "
        f"({bridge['ein'].nunique():,} EINs, {bridge['uei'].nunique():,} UEIs) "
        f"-> {out.relative_to(CEDAR)}", fh)
    if len(bridge):
        for k, v in bridge["ein_confidence_tier"].value_counts().items():
            log(f"    EIN-side tier {k}: {v}", fh)

    # read-only comparison against the identifier ledger
    led = pd.read_csv(CLEAN / "cedar_identifier_ledger_final.csv", dtype=str, low_memory=False)
    led_uei = {str(x).strip().upper() for x, t in zip(led["identifier"], led["identifier_type"])
               if str(t).strip().upper() == "UEI"}
    log(f"  cedar_identifier_ledger_final.csv: {len(led):,} rows, "
        f"{len(led_uei):,} unique UEIs (read-only)", fh)
    ueis = set(bridge["uei"]) if len(bridge) else set()
    netnew = sorted(ueis - led_uei)
    log(f"  bridge UEIs: {len(ueis):,}; already in ledger: {len(ueis & led_uei):,}; "
        f"NET-NEW: {len(netnew):,}", fh)
    for u in netnew:
        row = bridge.loc[bridge.uei == u].iloc[0]
        flag = f"  [{row['review_flag']}]" if row["review_flag"] else ""
        log(f"    NET-NEW {u}  {row['org_name']}{flag}", fh)

    if len(bridge):
        bridge["uei_already_in_cedar_ledger"] = bridge["uei"].isin(led_uei).astype(int)
        bridge.to_csv(out, index=False)

    # EIN-side comparison against the ledger (read-only)
    led_types = Counter(str(t).strip().upper() for t in led["identifier_type"])
    log(f"\n  ledger identifier_type counts: {dict(led_types)}", fh)
    led_ein = {norm_ein(i) for i, t in zip(led["identifier"], led["identifier_type"])
               if str(t).strip().upper() == "EIN"}
    led_ein.discard("")
    log(f"  CONFLICT WITH BRIEF: the ledger already carries {led_types.get('EIN', 0):,} EIN rows "
        f"({len(led_ein):,} unique), all sourced from need_v6_geocoded.csv, which itself "
        f"ingested the 1,090 strict-verified 990 EINs. EIN is thinly present, not absent.", fh)
    all_ein = set(np_orgs["EIN"])
    for t in ("A", "B", "X"):
        s = set(np_orgs.loc[np_orgs.confidence_tier == t, "EIN"])
        log(f"  tier {t}: {len(s):,} EINs, {len(s & led_ein):,} already in ledger, "
            f"{len(s - led_ein):,} NET-NEW to the ledger", fh)
    log(f"  ALL np_orgs EINs net-new to the ledger: {len(all_ein - led_ein):,}", fh)

    # exclusion rulings vs the ledger: does the ledger carry an EIN we ruled out?
    ex = pd.read_csv(SPINE / "nonprofit_exclusion_rulings.csv", dtype=str)
    viol = sorted(set(ex["ein"]) & led_ein)
    log(f"  RULING VIOLATIONS: {len(viol):,} excluded EIN(s) present in the ledger", fh)
    for v in viol:
        nm = ex.loc[ex.ein == v, "org_name"].iloc[0]
        rsn = ex.loc[ex.ein == v, "exclusion_reason"].iloc[0]
        lnm = led.loc[led["identifier"].map(norm_ein) == v, "canonical_name"].iloc[0]
        log(f"    {v}  {nm}  [excluded: {rsn}]  ledger canonical_name={lnm}", fh)
    return bridge


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--steps", default="1,2,3,4,5")
    args = ap.parse_args()
    steps = {s.strip() for s in args.steps.split(",")}

    (CEDAR / "logs").mkdir(exist_ok=True)
    logpath = CEDAR / "logs" / "17_nonprofit_990_2026-08-05.log"
    with open(logpath, "w", encoding="utf-8") as fh:
        log(f"Cedar Press 17 - Native Nonprofit layer + EIN harvest   run {TODAY}", fh)
        if "1" in steps:
            step1_copy_and_inventory(fh)
        if "2" in steps:
            step2_bmf_slice(fh)
        ex = step3_exclusions(fh) if "3" in steps else pd.read_csv(
            SPINE / "nonprofit_exclusion_rulings.csv", dtype=str)
        if "4" in steps:
            np_orgs = step4_np_orgs(ex, fh)
        else:
            np_orgs = pd.read_csv(CLEAN / "np_orgs.csv", dtype=str)
        if "5" in steps:
            step5_bridge(np_orgs, fh)
        log("\nDONE", fh)
    print(f"\nlog -> {logpath}")


if __name__ == "__main__":
    main()
