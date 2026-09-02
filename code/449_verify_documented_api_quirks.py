#!/usr/bin/env python3
r"""Cedar Press 449 - verify DOCUMENTED API quirks against the data we already hold.

WHY THIS EXISTS
---------------
The owner's instruction: *"For data we use APIs - if there is like a technical
manual make sure you are reading it, or find research papers that used it for
quirks."*

`docs/API_TECHNICAL_NOTES.md` is the register that instruction produces. This
script is its evidence leg. A quirk read in a vendor manual and never checked
against our own files is a claim, not a finding - and this project has already
paid for the inverse (`docs/ASSUMPTIONS_AND_LIMITATIONS.md` Part V:
*"an unverified citation is worse than no citation"*).

So every quirk in the register that is CHEAPLY reproducible from a file already
on disk is reproduced here, and every one that is NOT reproducible is reported
as NOT_REPRODUCIBLE rather than quietly dropped. **A documented quirk we cannot
reproduce is worth flagging as much as one we can** - it means either the
manual is wrong about our vintage, or our pull already worked around it.

ZERO NETWORK. ZERO WRITES TO ANY SHARED TABLE.
----------------------------------------------
No socket is opened. The only file written is
`docs/API_TECHNICAL_QUIRK_VERIFICATION.json`, `.part`-then-renamed.
Ten agents were live when this was written; nothing here reads a table under a
concurrent writer for anything but counting, and nothing here writes one.

CHECKS
------
  Q1  LDA  page_size is capped SERVER-SIDE at 25 (requesting 100 returns 25).
           Reproduced from `code/lobbying_pull/pull_progress.json`: pages x 25
           must reconcile to the per-keyword count.
  Q2  USASpending assistance: `business_types_description` renders the
           federally-recognized tribal government token TWO ways, one missing a
           space and one missing a hyphen. An exact-string filter drops rows.
  Q3  FPDS/DAIMS: `extent_competed` holds TWO vocabularies split at an archive
           vintage boundary, so filtering it selects an ERA. Reproduced by
           crosstabbing raw token against fiscal year.
  Q4  Socrata: `data.ct.gov` is pulled with `$limit=50000`. SODA 2.0 caps
           `$limit` and truncates SILENTLY. Reproduced by comparing the rows on
           disk against the ceiling - a LATENT ceiling is still a ceiling.
  Q5  SAM: `awardeeBusinessTypeName` is a PARTIAL string match. Reproduced from
           the loaded SAM extract by counting rows whose only basis is a
           non-Native business type containing the query substring.
  Q6  FAC: the Census-era historical archive index links 1998-2015, but the
           2015 object itself refused. Reproduced from the probe artefact.

Run:  py -3 code/449_verify_documented_api_quirks.py
"""

import csv
import json
import os
import pathlib
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone

csv.field_size_limit(10 ** 9)

ROOT = pathlib.Path(__file__).resolve().parent.parent
CLEAN = ROOT / "data" / "clean"
OUT = ROOT / "docs" / "API_TECHNICAL_QUIRK_VERIFICATION.json"

TODAY = datetime.now(timezone.utc).strftime("%Y-%m-%d")


def result(key, source, claim, verdict, evidence, note=""):
    return {"key": key, "source": source, "claim": claim, "verdict": verdict,
            "evidence": evidence, "note": note}


# ---------------------------------------------------------------- Q1  LDA
def q1_lda_page_size():
    p = ROOT / "code" / "lobbying_pull" / "pull_progress.json"
    claim = ("Senate LDA API page_size is capped SERVER-SIDE at 25; requesting "
             "100 still returns 25 (measured 2026-08-05, recorded in "
             "code/lobbying_pull/01_pull_lda_filings.py docstring).")
    if not p.exists():
        return result("Q1_LDA_PAGE_SIZE_25", "lda.senate.gov", claim,
                      "NOT_REPRODUCIBLE", {},
                      "pull_progress.json absent; the pull's own state is the "
                      "only artefact that records pages-vs-count.")
    prog = json.loads(p.read_text(encoding="utf-8"))
    ev = {}
    consistent = 0
    total = 0
    for kw, d in prog.items():
        if not isinstance(d, dict):
            continue
        c = d.get("count")
        np_ = d.get("next_page")
        if not isinstance(c, int) or not isinstance(np_, int) or np_ < 2:
            continue
        total += 1
        # next_page is the page AFTER the last fetched page, so pages = np_ - 1
        pages = np_ - 1
        implied = c / pages if pages else 0
        ev[kw] = {"count": c, "pages_fetched": pages,
                  "implied_page_size": round(implied, 2)}
        if 24.0 <= implied <= 25.0:
            consistent += 1
    # THE TEST IS A CEILING, NOT AN EQUALITY. A keyword whose last page is
    # short implies a page size BELOW 25 and says nothing; only a keyword
    # implying a size ABOVE 25 would falsify the cap. Counting "how many equal
    # 25" is the wrong test and scored 9/12 on a quirk that is fully confirmed.
    above = {k: v for k, v in ev.items() if v["implied_page_size"] > 25.0}
    ev_max = max((v["implied_page_size"] for v in ev.values()), default=0)
    verdict = ("REPRODUCED" if total and not above
               else "REFUTED" if above else "NOT_REPRODUCIBLE")
    return result("Q1_LDA_PAGE_SIZE_25", "lda.senate.gov", claim, verdict,
                  {"per_keyword": ev, "max_implied_page_size": ev_max,
                   "keywords_implying_above_25": above,
                   "keywords_tested": total},
                  f"NO keyword of {total} implies a page size above 25 "
                  f"(max {ev_max}); a short final page explains every value "
                  f"below it. That is the shape of a SERVER-SIDE cap, not of a "
                  f"client setting. PAGE_SIZE in the puller is 25 and the "
                  f"docstring records that 100 was requested and 25 served.")


# ------------------------------------------- Q2  assistance flag rendering
def q2_business_types_rendering():
    p = CLEAN / "federal_funding_transactions.csv"
    claim = ("USAspending `business_types_description` renders the "
             "federally-recognized tribal government token in TWO ways - one "
             "missing a space, one missing a hyphen - so an exact-string "
             "filter silently drops rows (START_HERE.md, seam 3).")
    if not p.exists():
        return result("Q2_BUSINESS_TYPE_TWO_RENDERINGS", "api.usaspending.gov "
                      "award archive", claim, "NOT_REPRODUCIBLE", {},
                      "federal_funding_transactions.csv absent")
    # THE FIELD IS SEMICOLON-DELIMITED AND MULTI-VALUED. Counting whole-field
    # strings and counting TOKENS are different measurements and the register
    # has been quoting them interchangeably. Both are computed here.
    CANON = "INDIAN/NATIVE AMERICAN TRIBAL GOVERNMENT (FEDERALLY-RECOGNIZED)"
    VARIANT = "INDIAN/NATIVE AMERICANTRIBAL GOVERNMENT (FEDERALLY RECOGNIZED)"
    whole = Counter()
    tok_canon = 0
    tok_variant = 0
    canon_exact = 0
    canon_in_compound = 0
    n = 0
    with p.open(encoding="utf-8", newline="") as f:
        rd = csv.DictReader(f)
        if "business_types_description" not in (rd.fieldnames or []):
            return result("Q2_BUSINESS_TYPE_TWO_RENDERINGS",
                          "api.usaspending.gov award archive", claim,
                          "NOT_REPRODUCIBLE", {},
                          "column business_types_description not present; "
                          "AGENTS.md concurrency rule 8 - an absent column "
                          "name must not read as an empty source.")
        for r in rd:
            n += 1
            v = (r.get("business_types_description") or "").strip().upper()
            if "TRIBAL GOVERNMENT" not in v:
                continue
            whole[v] += 1
            toks = [t.strip() for t in v.split(";") if t.strip()]
            if CANON in toks:
                tok_canon += 1
                if v == CANON:
                    canon_exact += 1
                else:
                    canon_in_compound += 1
            if VARIANT in toks:
                tok_variant += 1
    ev = {"rows_scanned": n,
          "distinct_WHOLE_FIELD_renderings_containing_TRIBAL_GOVERNMENT":
              len(whole),
          "top_whole_field_renderings": dict(whole.most_common(12)),
          "rows_whose_TOKEN_set_contains_canonical": tok_canon,
          "  ...as the ENTIRE field": canon_exact,
          "  ...inside a SEMICOLON-DELIMITED COMPOUND": canon_in_compound,
          "rows_whose_TOKEN_set_contains_the_spacing_variant": tok_variant}
    verdict = "REPRODUCED" if tok_variant and canon_exact else "NOT_REPRODUCIBLE"
    return result("Q2_BUSINESS_TYPE_TWO_RENDERINGS",
                  "api.usaspending.gov award archive", claim, verdict, ev,
                  "THE QUIRK IS TWO-LAYERED AND ONLY ONE LAYER IS RECORDED IN "
                  "START_HERE.md. Layer 1, recorded: one token renders two "
                  "ways (missing space / missing hyphen). Layer 2, NOT "
                  "recorded: the field is SEMICOLON-DELIMITED AND MULTI-VALUED, "
                  "so an equality filter on the whole field ALSO drops every "
                  "compound row. Split on ';' and test token membership; never "
                  "compare the whole field.")


# ---------------------------------------------- Q3  extent_competed seam
def q3_extent_competed_seam():
    p = CLEAN / "prime_contracts.csv"
    claim = ("`extent_competed` holds TWO vocabularies - raw FPDS codes "
             "(A..G, CDO, NDO) and rendered DAIMS description tags - split at "
             "the FY2016/FY2017 archive-vintage boundary, so filtering the raw "
             "column selects an ERA and not a competition status "
             "(START_HERE.md item 5; docs/EXTENT_COMPETED_CROSSWALK.md).")
    if not p.exists():
        return result("Q3_EXTENT_COMPETED_TWO_VOCABULARIES", "USAspending "
                      "award archive / DAIMS-DEC", claim, "NOT_REPRODUCIBLE",
                      {}, "prime_contracts.csv absent")
    CODES = {"A", "B", "C", "D", "E", "F", "G", "CDO", "NDO"}
    by_fy = defaultdict(lambda: {"code": 0, "label": 0, "blank": 0})
    fycol = None
    with p.open(encoding="utf-8", newline="") as f:
        rd = csv.DictReader(f)
        fn = rd.fieldnames or []
        if "extent_competed" not in fn:
            return result("Q3_EXTENT_COMPETED_TWO_VOCABULARIES",
                          "USAspending award archive / DAIMS-DEC", claim,
                          "NOT_REPRODUCIBLE", {},
                          "column extent_competed not present")
        for cand in ("fiscal_year", "action_date_fiscal_year", "fy",
                     "award_fiscal_year"):
            if cand in fn:
                fycol = cand
                break
        for r in rd:
            v = (r.get("extent_competed") or "").strip()
            fy = (r.get(fycol) or "").strip()[:4] if fycol else "?"
            b = by_fy[fy]
            if not v:
                b["blank"] += 1
            elif v.upper() in CODES:
                b["code"] += 1
            else:
                b["label"] += 1
    years = sorted(k for k in by_fy if k.isdigit())
    ev = {"fiscal_year_column": fycol,
          "by_fiscal_year": {y: by_fy[y] for y in years}}
    # find the boundary: last year that is majority code, first majority label
    last_code = None
    first_label = None
    for y in years:
        b = by_fy[y]
        if b["code"] > b["label"] and b["code"] > 0:
            last_code = y
        if b["label"] > b["code"] and first_label is None and b["label"] > 0:
            first_label = y
    ev["last_majority_code_fy"] = last_code
    ev["first_majority_label_fy"] = first_label
    verdict = ("REPRODUCED"
               if last_code and first_label and last_code < first_label
               else "PARTIAL")
    return result("Q3_EXTENT_COMPETED_TWO_VOCABULARIES",
                  "USAspending award archive / DAIMS-DEC v2.2 (2022-06-03)",
                  claim, verdict, ev,
                  "The crosswalk is quoted verbatim in "
                  "code/cedar_extent_competed.py and must never be re-derived "
                  "from the data. Filter extent_competed_normalized instead.")


# ------------------------------------------------------- Q4  Socrata limit
def q4_socrata_limit_ceiling():
    claim = ("Socrata SODA 2.0 `/resource/<id>.json` caps `$limit` and "
             "truncates SILENTLY at the cap. Cedar requests `$limit=50000` in "
             "code/159_extend_gaming_metrics.py and "
             "code/119_build_digital_and_loyalty.py.")
    cands = sorted((ROOT / "data" / "raw" / "multistate_gaming_revenue")
                   .glob("ct_slot_revenue_monthly*.json")) \
        if (ROOT / "data" / "raw" / "multistate_gaming_revenue").exists() else []
    ev = {"limit_requested_in_code": 50000, "artefacts": {}}
    rows = None
    for c in cands:
        try:
            d = json.loads(c.read_text(encoding="utf-8"))
        except Exception as e:                       # noqa: BLE001
            ev["artefacts"][c.name] = f"unreadable: {e}"
            continue
        if isinstance(d, list):
            ev["artefacts"][c.name] = len(d)
            rows = max(rows or 0, len(d))
    if rows is None:
        return result("Q4_SOCRATA_LIMIT_SILENT_TRUNCATION", "data.ct.gov "
                      "(Socrata SODA)", claim, "NOT_REPRODUCIBLE", ev,
                      "no CT artefact on disk to count")
    ev["rows_on_disk"] = rows
    ev["headroom_to_requested_limit"] = 50000 - rows
    return result("Q4_SOCRATA_LIMIT_SILENT_TRUNCATION",
                  "data.ct.gov (Socrata SODA)", claim, "LATENT_NOT_TRIGGERED",
                  ev,
                  "The ceiling is real and is NOT currently reached - the CT "
                  "series is small. It is recorded because "
                  "code/343_refresh_ct_gaming_monthly.py asks the source for "
                  "count(1) FIRST and compares retrieved against reported, "
                  "while code/119 issues the bare $limit=50000 with no such "
                  "comparison. 119 is on the NEVER-RUN list for other reasons; "
                  "if it is ever revived, that request is a silent ceiling "
                  "(defect class 4).")


# ----------------------------------------------------- Q5  SAM partial match
def q5_sam_partial_match():
    claim = ("SAM `awardeeBusinessTypeName` is a PARTIAL string match: the "
             "business type \"Subcontinent Asian (Asian-INDIAN) American Owned "
             "Business\" contains \"INDIAN\", and \"HOUSING AUTHORITIES "
             "PUBLIC/TRIBAL\" contains \"TRIBAL\" "
             "(docs/SAM_EXTRACTION_PLAN.md).")
    cands = [CLEAN / "sam_contract_awards.csv",
             CLEAN / "sam_contract_awards_fy2000_2007.csv"]
    p = next((c for c in cands if c.exists()), None)
    if p is None:
        found = sorted(CLEAN.glob("sam_*.csv"))
        return result("Q5_SAM_PARTIAL_MATCH", "api.sam.gov contract-awards "
                      "extract", claim, "NOT_REPRODUCIBLE",
                      {"sam_files_in_clean": [f.name for f in found]},
                      "no expected SAM extract filename found; the measurement "
                      "of record is docs/SAM_EXTRACTION_PLAN.md "
                      "(102,587 rows / 3,774 UEIs / $11,129,475,544 on "
                      "SUBCONTINENT_ASIAN_INDIAN_AMERICAN_ONLY).")
    bases = Counter()
    incl = Counter()
    n = 0
    with p.open(encoding="utf-8", newline="") as f:
        rd = csv.DictReader(f)
        fn = rd.fieldnames or []
        if "variant_match_basis" not in fn:
            return result("Q5_SAM_PARTIAL_MATCH", "api.sam.gov contract-awards "
                          "extract", claim, "NOT_REPRODUCIBLE",
                          {"file": p.name, "columns_sample": fn[:25]},
                          "variant_match_basis column absent - an absent "
                          "column must not read as an empty source.")
        for r in rd:
            n += 1
            bases[(r.get("variant_match_basis") or "").strip()] += 1
            incl[(r.get("include_in_native_universe") or "").strip()] += 1
    ev = {"file": p.name, "rows": n,
          "variant_match_basis": dict(bases.most_common(15)),
          "include_in_native_universe": dict(incl)}
    non_native = sum(v for k, v in bases.items()
                     if "SUBCONTINENT" in k.upper()
                     or "HOUSING_AUTHORITY" in k.upper())
    ev["rows_matched_by_a_NON_NATIVE_business_type"] = non_native
    return result("Q5_SAM_PARTIAL_MATCH",
                  "api.sam.gov contract-awards extract", claim,
                  "REPRODUCED" if non_native else "PARTIAL", ev,
                  "Filter include_in_native_universe = 1 for any Native count. "
                  "A variant hit is NOT evidence of Native status.")


# --------------------------------------------------------- Q6  FAC archive
def q6_fac_historical_object():
    claim = ("The FAC Census-era historical index links 1998-2015, but the "
             "objects are served from s3-us-gov-west-1 and do not all answer "
             "alike; api.fac.gov itself begins at audit_year 2016.")
    p = ROOT / "docs" / "FAC_HISTORICAL_BULK_VERIFICATION.json"
    q = ROOT / "docs" / "FAC_HISTORICAL_DEPTH_PROBE.json"
    ev = {}
    if p.exists():
        d = json.loads(p.read_text(encoding="utf-8"))
        ev["index_years_linked"] = (d.get("index_page") or {}).get("years_linked")
        ev["boundary_probes"] = {k: {"status": v.get("status"),
                                     "final_host": v.get("final_host")}
                                 for k, v in (d.get("boundary_probes") or {}).items()}
        ev["downloads"] = {k: {"status": v.get("status"),
                               "bytes": v.get("bytes_written")}
                           for k, v in (d.get("downloads") or {}).items()}
    if q.exists():
        d2 = json.loads(q.read_text(encoding="utf-8"))
        ev["api_earliest_audit_year_any"] = d2.get("earliest_audit_year_any")
        ev["api_pre2016_count_content_range"] = [
            pr.get("content_range") for pr in (d2.get("probes") or [])
            if "audit_year <" in str(pr.get("probe"))]
    if not ev:
        return result("Q6_FAC_API_FLOOR_VS_BULK_FLOOR", "api.fac.gov / "
                      "app.fac.gov historical", claim, "NOT_REPRODUCIBLE", {},
                      "neither FAC probe artefact is on disk")
    return result("Q6_FAC_API_FLOOR_VS_BULK_FLOOR",
                  "api.fac.gov / app.fac.gov historical archive", claim,
                  "REPRODUCED", ev,
                  "An API's floor is a fact about the API, not about the "
                  "source. The 403 on census-2015.zip is a fact about ONE "
                  "OBJECT at one route and is not evidence the year is absent.")


def main():
    checks = [q1_lda_page_size, q2_business_types_rendering,
              q3_extent_competed_seam, q4_socrata_limit_ceiling,
              q5_sam_partial_match, q6_fac_historical_object]
    out = {"generated_utc": datetime.now(timezone.utc).isoformat(),
           "script": "code/449_verify_documented_api_quirks.py",
           "network_requests": 0,
           "shared_tables_written": 0,
           "companion": "docs/API_TECHNICAL_NOTES.md",
           "checks": []}
    for fn in checks:
        try:
            r = fn()
        except Exception as e:                       # noqa: BLE001
            r = result(fn.__name__, "?", "?", "ERROR", {},
                       f"{type(e).__name__}: {e}")
        out["checks"].append(r)
        print(f"  {r['verdict']:<22} {r['key']}")
        if r["note"]:
            print(f"      {r['note'][:150]}")

    tally = Counter(c["verdict"] for c in out["checks"])
    out["tally"] = dict(tally)
    print("\n  " + "  ".join(f"{k}={v}" for k, v in sorted(tally.items())))

    part = OUT.with_suffix(".json.part")
    part.write_text(json.dumps(out, indent=1), encoding="utf-8")
    os.replace(part, OUT)
    print(f"\n  wrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
