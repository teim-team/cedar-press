#!/usr/bin/env python3
"""
1149_codebook_money_fed.py - codebook registry blocks for the nine tables
`code/1145_cosponsor_harvest.py` and `code/1148_nagpra_nps_databases.py` built.

    py -3 code/1149_codebook_money_fed.py            # write fragments, rebuild
    py -3 code/1149_codebook_money_fed.py verify     # exits 1 on breach
    py -3 code/1149_codebook_money_fed.py selftest   # proves verify FIRES

WHY THIS IS A SEPARATE SCRIPT, AND WHY IT IS NOT OPTIONAL
---------------------------------------------------------
`docs/codebooks/*.md` is prose. `data/clean/codebook/<dataset>.csv` is the
REGISTRY the shipping gate reads: `25_build_publication_layer` resolves the
registry, and a table with no block cannot ship however good its markdown is.
`62_no_regression_check`'s `tables_undocumented_in_codebook` is the metric.
Same reasoning, and the same shape, as `code/1124_register_acquire_codebooks.py`
for the 1119/1120/1121 acquisition.

EVERY `pct_filled` AND `n_rows` IS MEASURED off the live table at run time.
None is typed. `verify` re-counts and fails if a recorded figure has drifted
from the file by more than 0.1pp - a codebook stating a fill rate it did not
measure is this repo's signature defect.

WHAT IT DOES NOT DO
-------------------
It does not run the ship chain. `build.py ship --execute`, `25`, `27` and `87`
belong to the integrator.

INVARIANTS
----------
  CBM-1  every column of all nine tables has a registry row
  CBM-2  no registry row has an empty description
  CBM-3  every recorded pct_filled matches the live table to 0.1pp
  CBM-4  the master never loses a row
"""
from __future__ import annotations

import csv
import importlib.util
import shutil
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
csv.field_size_limit(10_000_000)
TODAY = date.today().isoformat()
CLEAN = ROOT / "data" / "clean"
FRAG = CLEAN / "codebook"
MASTER = CLEAN / "codebook_master.csv"

_spec = importlib.util.spec_from_file_location(
    "cedar_codebook", ROOT / "code" / "cedar_codebook.py")
cb = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cb)                                       # type: ignore

FIELDS = ["dataset", "variable", "type", "units", "pct_filled", "n_rows",
          "published", "access_tier", "description", "generated"]

PROV = {
    "source_dataset": "Which publisher database this row came out of, as "
                      "`national_nagpra_online_database:<endpoint>`.",
    "source_endpoint": "The DataTables endpoint name on "
                       "apps.cr.nps.gov/nagprapublic.",
    "source_url": "The exact URL this row was read from.",
    "source_terms_status": "Terms disposition. "
                           "`TERMS_STATED_NO_REUSE_RESTRICTION` on every row "
                           "here: the NPS disclaimer states the material is "
                           "generally in the public domain. This column is a "
                           "PUBLICATION GATE read by cedar_publication.GATES - "
                           "a value outside its allow-set withholds the row.",
    "source_terms_url": "Where that terms statement is published.",
    "source_terms_basis": "The terms statement quoted verbatim, plus the "
                          "robots.txt measurement behind the route.",
    "retrieved_at": "UTC timestamp of the pull that produced this row.",
}

# dataset id -> (table, {column: description})
BLOCKS: dict[str, tuple[str, dict[str, str]]] = {
    # ---------------- legislation ----------------------------------------
    "10e_native_bill_cosponsors": ("native_bill_cosponsors.csv", {
        "bill_id": "Cedar's bill key, joining `native_bills.csv`. Format "
                   "`<congress>-<type>-<number>`.",
        "congress": "The Congress the bill was introduced in, 93-119.",
        "chamber": "House or Senate, from the bill type.",
        "bill_type": "congress.gov bill type slug (hr, s, hres, hjres, "
                     "sjres, sconres).",
        "bill_number": "The measure number within its Congress and type.",
        "cosponsor_bioguide_id": "The cosponsoring member's Biographical "
                                 "Directory of Congress id - the stable "
                                 "cross-Congress member key. Never blank; "
                                 "1145's CS-5 fails the build otherwise.",
        "cosponsor_full_name": "The member's name as congress.gov renders it, "
                               "including party and state, e.g. "
                               "`Rep. Meeds, Lloyd [D-WA-2]`. A member of "
                               "Congress in their public role.",
        "cosponsor_party": "Party letter as recorded at the time of "
                           "sponsorship.",
        "cosponsor_state": "The member's state.",
        "cosponsor_district": "House district. BLANK FOR SENATORS AND FOR "
                              "PRE-MODERN HOUSE RECORDS the API does not "
                              "carry - blank is not 'at large'.",
        "sponsorship_date": "The date the member signed on. Part of the "
                            "primary key, because a member can appear twice "
                            "on one bill if they withdrew and re-joined.",
        "is_original_cosponsor": "Y if the member signed at introduction, N "
                                 "if they joined later, blank if the source "
                                 "does not say. THE DISTINCTION MATTERS: an "
                                 "original cosponsor is a co-author, a later "
                                 "one is an endorsement.",
        "sponsorship_withdrawn_date": "Non-blank on a member who LEFT the "
                                      "bill. A withdrawn cosponsor is still a "
                                      "row; filtering it is the consumer's "
                                      "decision, not Cedar's.",
        "record_basis": "Which pass produced the row: "
                        "`congress_gov_api_v3_cosponsors_1145` (this "
                        "acquisition) or `legacy__cosponsors_csv` (an earlier "
                        "unnumbered pass, promoted out of an orphan file). A "
                        "legacy row appears only where no fetched roster "
                        "exists for that bill, so the two never double-count.",
        "source_url": "The congress.gov v3 endpoint this roster came from.",
        "fetched_date": "Date of the fetch. Blank on legacy rows, whose "
                        "original fetch date was not recorded.",
    }),
    "10f_native_bill_cosponsor_coverage": (
        "native_bill_cosponsor_coverage.csv", {
            "bill_id": "Cedar's bill key. ONE ROW FOR EVERY BILL IN "
                       "`native_bills.csv` - this is the denominator table.",
            "congress": "The Congress the bill was introduced in.",
            "chamber": "House or Senate.",
            "bill_type": "congress.gov bill type slug as held in "
                         "`native_bills.csv`.",
            "bill_number": "The measure number.",
            "cosponsor_lookup_status": "What happened when Cedar looked. "
                                       "`ok` a roster was returned; "
                                       "`zero_cosponsors_reported` the source "
                                       "says the bill had none; "
                                       "`no_api_record` congress.gov has no "
                                       "such bill; `ok_legacy_only` only the "
                                       "earlier pass's roster exists; "
                                       "`SOURCE_DOES_NOT_PUBLISH_ON_BILL_ENDPOINT` "
                                       "the bill_type is not a canonical "
                                       "congress.gov slug (treaty documents "
                                       "are not on /bill at all); "
                                       "`NEVER_CHECKED` no artefact records an "
                                       "attempt. A ZERO IS NOT AN ABSENCE OF "
                                       "EVIDENCE HERE - that is what this "
                                       "column exists to say.",
            "n_cosponsors_retrieved": "How many cosponsor rows Cedar holds "
                                      "for this bill.",
            "n_cosponsors_reported_by_source": "The count the source itself "
                                               "reported in its pagination "
                                               "block, independent of how "
                                               "many rows were parsed.",
            "cosponsor_count_in_native_bills": "The `cosponsor_count` "
                                               "`native_bills.csv` has "
                                               "carried since 2026-08-05.",
            "count_agrees_with_native_bills": "Y / N / NOT_TESTABLE. A "
                                              "CROSS-CHECK between two "
                                              "independently obtained counts. "
                                              "NOT_TESTABLE means one side is "
                                              "blank - NEVER that they "
                                              "agreed.",
            "cosponsor_lookup_basis": "The sentence behind the status: the "
                                      "endpoint and HTTP result, or the "
                                      "artefact the earlier pass left.",
            "source_url": "The endpoint that was, or would have been, called.",
            "fetched_date": "Date this coverage row was derived.",
        }),

    # ---------------- nagpra ----------------------------------------------
    "11e_nagpra_nps_grant_awards": ("nagpra_nps_grant_awards.csv", {
        "fiscal_year": "Federal fiscal year of the award, 1994-2025.",
        "grant_type": "`Consultation` (consultation/documentation) or "
                      "`Repatriation`. Note the source writes "
                      "`Repatriation ` with a trailing space on some rows; "
                      "kept as recorded.",
        "recipient_name_as_recorded": "The grantee exactly as NPS publishes "
                                      "it. NOT resolved to a Cedar entity in "
                                      "this pass.",
        "recipient_state": "Grantee state, in the source's upper case.",
        "recipient_type": "`Tribe` (705 awards) or `Museum` (516). NPS's own "
                          "classification, not Cedar's.",
        "amount_awarded_usd": "Award amount in nominal dollars. 0 "
                              "unparseable across 1,221 rows; total "
                              "$66,095,102.79. **DO NOT SUM AGAINST "
                              "`federal_funding_transactions` CFDA 15.922** - "
                              "that is 696 transaction rows FY2007-2026 and "
                              "the two overlap from FY2013. Different grains "
                              "of one programme.",
        **PROV}),
    "11f_nagpra_nps_inventories": ("nagpra_nps_inventories.csv", {
        "cultural_affiliation_status": "`CULTURALLY_AFFILIATED` (454 rows) or "
                                       "`CULTURALLY_UNIDENTIFIABLE` (11,357). "
                                       "A status under 43 CFR 10.11 with "
                                       "consequences for who may claim an "
                                       "ancestor, not a label. The source's "
                                       "grid COLLAPSES the two by default; "
                                       "this column exists because the pull "
                                       "asks per type.",
        "institution_state": "State of the museum or federal agency holding "
                             "the remains.",
        "institution_name": "The holding museum or federal agency as NPS "
                            "publishes it.",
        "mni": "Minimum number of individuals, as the institution reported "
               "it. Never inferred.",
        "associated_funerary_objects": "Count of associated funerary objects "
                                       "as reported.",
        "geographic_origin_state": "State the remains were removed from. "
                                   "`ZUnknown` is the source's own literal "
                                   "for unknown and sorts last by design.",
        "geographic_origin_county": "County of removal. `-` and `ZUnknown` "
                                    "are the source's own literals for "
                                    "not-stated.",
        **PROV}),
    "11g_nagpra_nps_summaries": ("nagpra_nps_summaries.csv", {
        "institution_state": "State of the museum or federal agency.",
        "institution_name": "The museum or federal agency that filed the "
                            "NAGPRA summary. ONE ROW PER INSTITUTION - "
                            "counting rows counts institutions, not tribes.",
        "tribes_listed_semicolon": "LIST-VALUED. Every tribe the institution "
                                   "named in its summary, semicolon "
                                   "separated, as published. Explode before "
                                   "any per-tribe analysis. NOT resolved to "
                                   "`cedar_uid` in this pass.",
        "n_tribes_listed": "How many names are in the list column. Derived by "
                           "splitting on `;`, so it counts NAMES AS "
                           "PUBLISHED, not distinct resolved tribes.",
        **PROV}),
    "11h_nagpra_nps_intended_dispositions": (
        "nagpra_nps_intended_dispositions.csv", {
            "institution_state": "State of the federal agency or museum.",
            "institution_name": "The agency or museum publishing the notice.",
            "publication_as_recorded": "Free text: the NEWSPAPER names and "
                                       "dates the disposition was published "
                                       "in, semicolon separated. A Notice of "
                                       "Intended Disposition runs in a local "
                                       "paper, not the Federal Register, "
                                       "which is why this is not a date "
                                       "column.",
            **PROV}),
    "11i_nagpra_nps_notice_index": ("nagpra_nps_notice_index.csv", {
        "notice_type": "NIC / NIR / NID / NOT. PART OF THE PRIMARY KEY and "
                       "not cosmetic: the source's grid defaults to NIC and a "
                       "pull that does not ask per type returns 4,810 of "
                       "6,818 rows while looking complete.",
        "notice_type_label": "The expanded form of `notice_type`.",
        "institution_state": "State of the museum or federal agency.",
        "institution_name": "The museum or federal agency named on the "
                            "notice.",
        "publication_date": "Federal Register publication date as the source "
                            "renders it, M/D/YYYY.",
        "repatriation_date": "The source's 'Statement Date'. Literal `-` "
                             "where the source prints a dash.",
        "fr_document_number": "The Federal Register document number - the "
                              "join key to `nagpra_notices.csv` and to "
                              "`nagpra_notice_source_corroboration.csv`. 608 "
                              "of 6,818 are non-canonical and 606 of those "
                              "are legitimate FR prefixes (E8-, E9-, X94-, "
                              "R7-).",
        "total_mni": "The Program's OWN minimum-number-of-individuals count. "
                     "INDEPENDENT of `nagpra_notices.mni_total_stated`, which "
                     "is parsed from the notice prose. Populated on NIC and "
                     "NID; a blank on an NIR is the wrong column for that "
                     "notice type, not a missing value.",
        "total_associated_funerary_objects": "The Program's count of "
                                             "associated funerary objects. "
                                             "NIC/NID.",
        "unassociated_funerary_objects": "Count of unassociated funerary "
                                         "objects. An NIR column.",
        "sacred_objects": "Count of sacred objects. An NIR column.",
        "objects_of_cultural_patrimony": "Count of objects of cultural "
                                         "patrimony. An NIR column.",
        "sacred_objects_and_cultural_patrimony": "Count of items that are "
                                                 "both sacred objects and "
                                                 "objects of cultural "
                                                 "patrimony. An NIR column.",
        "publication_date_iso": "`publication_date` as ISO. Blank where the "
                                "source printed no parseable date.",
        "repatriation_date_iso": "`repatriation_date` as ISO. Blank where the "
                                 "source printed `-`.",
        **PROV}),
    "11j_nagpra_nps_unclaimed_remains": ("nagpra_nps_unclaimed_remains.csv", {
        "institution_name": "The federal agency holding unclaimed human "
                            "remains.",
        "institution_state": "State of the holding agency.",
        "county": "County the remains were removed from.",
        "mni": "Minimum number of individuals, as reported.",
        "associated_funerary_objects": "Associated funerary objects.",
        "unassociated_funerary_objects": "Unassociated funerary objects.",
        "sacred_objects": "Sacred objects.",
        "objects_of_cultural_patrimony": "Objects of cultural patrimony.",
        "sacred_objects_and_cultural_patrimony": "Items that are both.",
        **PROV}),
    "11k_nagpra_notice_source_corroboration": (
        "nagpra_notice_source_corroboration.csv", {
            "fr_document_number": "The Federal Register document number. One "
                                  "row per document seen by EITHER source - "
                                  "the union, not the intersection.",
            "in_cedar_nagpra_notices": "Y/N: whether `nagpra_notices.csv` "
                                       "holds this document.",
            "in_nps_notice_index": "Y/N: whether the National NAGPRA "
                                   "Program's own register holds it.",
            "n_nps_rows_for_this_document": "How many NPS rows carry this "
                                            "document number. Greater than 1 "
                                            "on three genuine second-NIR "
                                            "rows.",
            "cedar_mni_total_stated": "Cedar's MNI, parsed from the Federal "
                                      "Register notice prose by "
                                      "code/77_build_nagpra_dataset.py.",
            "nps_total_mni": "The Program's MNI for the same repatriation.",
            "corroboration_status": "AGREE 3,954 / DISAGREE 315 / "
                                    "NOT_TESTABLE_NO_MNI_ONE_SIDE 2,492 / "
                                    "IN_NPS_ONLY 49 / IN_CEDAR_ONLY 31. **A "
                                    "DISAGREE ROW IS A FINDING, NOT AN ERROR "
                                    "TO RESOLVE** - both values are carried "
                                    "and neither is overwritten. "
                                    "NOT_TESTABLE means one side published no "
                                    "MNI; it never means the two agreed.",
            "cedar_source": "Which Cedar table and column the left-hand value "
                            "came from, and which script derived it.",
            "nps_source": "The NPS endpoint the right-hand value came from.",
            "evidence_families": "Why this is corroboration and not a "
                                 "republication: two observers of one "
                                 "repatriation - the Federal Register text "
                                 "and the Program's own record.",
            "corroboration_basis": "The sentence stating what the comparison "
                                   "does and does not decide.",
            "retrieved_at": "Date the comparison was derived.",
        }),
}


def _measure(table: str):
    p = CLEAN / table
    with p.open("r", encoding="utf-8-sig", newline="") as fh:
        rdr = csv.DictReader(fh)
        cols = list(rdr.fieldnames or [])
        fill = {c: 0 for c in cols}
        n = 0
        for r in rdr:
            n += 1
            for c in cols:
                if (r.get(c) or "").strip():
                    fill[c] += 1
    return n, fill, cols


def build_rows() -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {}
    for ds, (table, descs) in BLOCKS.items():
        if not (CLEAN / table).exists():
            print(f"  SKIP {ds}: {table} not built")
            continue
        n, fill, cols = _measure(table)
        rows = []
        for c in cols:
            rows.append({
                "dataset": ds, "variable": c, "type": "text", "units": "",
                "pct_filled": round(100.0 * fill[c] / n, 1) if n else 0.0,
                "n_rows": n, "published": 1, "access_tier": "public",
                "description": descs.get(c, ""), "generated": TODAY})
        out[ds] = rows
    return out


def register() -> int:
    before = len(cb.read(MASTER))
    total = 0
    for ds, rows in build_rows().items():
        frag = FRAG / f"{ds}.csv"
        existing = cb.read(frag) if frag.exists() else []
        mine = {r["variable"] for r in rows}
        keep = [r for r in existing if r["variable"] not in mine]
        cb.write_fragment(ds, keep + [{k: r[k] for k in FIELDS} for r in rows],
                          FIELDS)
        total += len(rows)
        blank = sum(1 for r in rows if not r["description"])
        print(f"  {ds:<46} {len(rows):>3} variables"
              + (f"  !! {blank} WITH NO DESCRIPTION" if blank else ""))
    cb.build()
    after = len(cb.read(MASTER))
    print(f"\n{total} variable rows across {len(BLOCKS)} datasets; "
          f"master {before:,} -> {after:,}")
    if after < before:
        print("  FAIL CBM-4: the master SHRANK.")
        return 1
    return 0


def verify(quiet: bool = False) -> int:
    fails = []
    master = cb.read(MASTER)
    by_ds: dict[str, dict[str, dict]] = {}
    for r in master:
        by_ds.setdefault(r["dataset"], {})[r["variable"]] = r

    for ds, (table, _descs) in BLOCKS.items():
        p = CLEAN / table
        if not p.exists():
            fails.append(f"CBM-1: {table} does not exist")
            continue
        n, fill, cols = _measure(table)
        got = by_ds.get(ds, {})
        missing = [c for c in cols if c not in got]
        if missing:
            fails.append(f"CBM-1: {ds} missing {len(missing)} variable(s): "
                         f"{missing[:6]}")
        for c in cols:
            r = got.get(c)
            if not r:
                continue
            if not (r.get("description") or "").strip():
                fails.append(f"CBM-2: {ds}.{c} has an empty description")
            want = round(100.0 * fill[c] / n, 1) if n else 0.0
            try:
                have = float(r.get("pct_filled") or 0)
            except ValueError:
                have = -1.0
            if abs(have - want) > 0.1:
                fails.append(f"CBM-3: {ds}.{c} pct_filled {have} recorded "
                             f"against {want} measured")
    if not quiet:
        for f in fails[:25]:
            print(f"  FAIL {f}")
        print(f"  {len(BLOCKS)} datasets checked; "
              + ("VERIFY OK" if not fails else f"VERIFY FAILED ({len(fails)})"))
    return 1 if fails else 0


def selftest() -> int:
    if verify(quiet=True) != 0:
        print("  UNMEASURED: the registry already fails verify.")
        return 1
    ds = "11e_nagpra_nps_grant_awards"
    frag = FRAG / f"{ds}.csv"
    bak = frag.with_suffix(".csv.selftest_bak")
    mbak = MASTER.with_suffix(".csv.selftest_bak")
    shutil.copy2(frag, bak)
    shutil.copy2(MASTER, mbak)
    ok = True
    try:
        rows = cb.read(frag)
        cases = [
            ("CBM-1", [r for r in rows if r["variable"] != "fiscal_year"]),
            ("CBM-2", [dict(r, description="") if r["variable"] == "fiscal_year"
                       else r for r in rows]),
            ("CBM-3", [dict(r, pct_filled="3.3") if r["variable"] == "fiscal_year"
                       else r for r in rows]),
        ]
        for inv, injected in cases:
            cb.write_fragment(ds, [{k: r[k] for k in FIELDS} for r in injected],
                              FIELDS)
            cb.build(force=True)
            import io
            buf = io.StringIO()
            real, sys.stdout = sys.stdout, buf
            try:
                rc = verify(quiet=False)
            finally:
                sys.stdout = real
            fired = rc == 1 and inv in buf.getvalue()
            print(f"  {inv}: exit {rc}, {'FIRED' if fired else 'DID NOT FIRE'}")
            ok = ok and fired
    finally:
        shutil.copy2(bak, frag)
        shutil.copy2(mbak, MASTER)
        bak.unlink(missing_ok=True)
        mbak.unlink(missing_ok=True)
    rc = verify(quiet=True)
    print(f"  restored, verify exit {rc}")
    ok = ok and rc == 0
    print("  SELFTEST " + ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "register"
    raise SystemExit({"register": register, "verify": verify,
                      "selftest": selftest}.get(cmd, register)())
