#!/usr/bin/env python3
"""
Cedar Press - 174: write the missing definitions for the `07o_nigc_declinations`
codebook block, from each column's OWN evidence.

    py -3 code/174_document_nigc_declination_codebook.py --dry-run
    py -3 code/174_document_nigc_declination_codebook.py

WHY THIS EXISTS
---------------
`code/62_no_regression_check.py` has failed on

    codebook_undocumented_public = 45, must be 0

for long enough that six separate agent sessions recorded it as "pre-existing,
not mine" and moved on. A gate everyone has learned to step around is worse
than no gate, because it launders every OTHER failure it reports.

The 45 are all one block. `07o_nigc_declinations` has 60 variables. Thirteen of
them were documented by `code/100_finish_declinations_and_employment.py`, which
also wrote `docs/codebooks/07d_nigc_declination_variables.md` - and that
markdown covers ONLY the 13 columns script 100 added. The other 47 come from
`code/91_build_nigc_declinations.py` and were never described anywhere
machine-readable. 45 are `published = 1`, so the gate counts them; 2 are
already `internal`, so it does not - and those two were undocumented too, and
are documented here as well.

WHERE EACH DEFINITION COMES FROM
--------------------------------
Every string below is traceable to one of four places, and the source is named
in `evidence` beside it so the next reader can check rather than trust:

    91   the assignment in code/91_build_nigc_declinations.py that writes it
    100  the assignment in code/100_finish_declinations_and_employment.py
    LOG  docs/NIGC_DECLINATION_BUILD_LOG.md, which explains what the column is
         FOR and, for several of them, the specific defect it exists to stop
    DATA the value distribution measured in data/clean/nigc_declination_
         letters.csv (327 rows) on 2026-08-26

NOTHING HERE IS INVENTED. Where a column's meaning could not be established
from those four, the rule was to tier it `internal` and say why, never to write
a plausible sentence to clear a counter. One column is tiered that way and it
is named in TIER_INTERNAL below.

WHAT IT TOUCHES
---------------
`data/clean/codebook/07o_nigc_declinations.csv` (the fragment this block owns)
and the `07o_nigc_declinations` rows of `data/clean/codebook_master.csv`.

Rows for every other block are copied through byte-for-byte. It fills a
`description` only where the existing one is BLANK, so a hand-written
description already on a row is never overwritten.

`py -3 code/cedar_codebook.py build` is NOT used, deliberately: `check`
reports it would LOSE 28 rows (the four `cedar_filer_entity_*` columns on two
`04e_schedule_i_*` blocks), which is the shrinking-codebook bug that module was
written to prevent. Both files are patched in place instead, `.part` then
rename, with a `.bak_<date>_pre174` beside each.
"""

import csv
import shutil
import sys
from datetime import date
from pathlib import Path

CEDAR = Path(r"C:\Users\esm247\Desktop\Cedar Press")
CLEAN = CEDAR / "data" / "clean"
FRAG = CLEAN / "codebook" / "07o_nigc_declinations.csv"
MASTER = CLEAN / "codebook_master.csv"
BLOCK = "07o_nigc_declinations"
TODAY = date.today().isoformat()

csv.field_size_limit(min(sys.maxsize, 2**31 - 1))

# ---------------------------------------------------------------------------
# THE DEFINITIONS.  (description, evidence)
#
# `evidence` is not decoration. It is the answer to "how do you know?", carried
# next to the claim, which is the same discipline the letters layer itself
# applies to the agency's quotes.
# ---------------------------------------------------------------------------
DEFS = {
    # -- identity and provenance of the letter -----------------------------
    "cedar_opinion_id": (
        "Cedar-assigned stable id for one NIGC OGC declination letter, formed "
        "as NIGC-DL-<YYYYMMDD>-<nn> from the letter's date in NIGC's own "
        "published index plus a within-day sequence. Unique across the 327 "
        "index rows. It is OUR id: NIGC publishes no letter number.",
        "91 line 821 / 90 line 209; LOG s13 '327 letters, ids unique - PASS'"),
    "opinion_date": (
        "Date of the letter as printed in NIGC's own index table. Range "
        "2013-07-30 to 2026-04-14. It is the date of the OPINION, not of the "
        "agreement reviewed, not of any execution or closing.",
        "91 line 825 (row['index_date']); LOG s1"),
    "opinion_date_basis": (
        "Always `nigc_published_index_table` on all 327 rows: the date is "
        "taken from the agency's index, never parsed out of the PDF or "
        "inferred from a filename. A one-valued basis column is still a basis "
        "column - it states which source the date came from.",
        "91 line 826; DATA 327/327 one value"),
    "index_tribe_string": (
        "The tribe exactly as NIGC's index table spells it, unaltered. This "
        "is the ONLY tribe attribution used in this layer. NIGC's spellings "
        "include `San Manual`, `Cahuillla`, `Lac Court Oreilles`, `Kickapoo "
        "Tribe of OK` and `Shoshone - Bannock` with an en dash; they are kept "
        "verbatim, and where a letter's body names a different or more precise "
        "entity that appears as a CLAIM in gaming_source_claims.csv, never as "
        "a correction to this column.",
        "91 line 827; LOG s5, s12.6, s18.6"),
    "index_company_string": (
        "The counterparty exactly as NIGC's index table spells it - lender, "
        "bank, developer, consultant or enterprise. NIGC writes the same "
        "lender several ways (`PNC` and `PNC Bank N.A.`, `Wells Fargo N.A.` "
        "and `Wells Fargo, N.A.`), so 91 distinct strings on financing events "
        "normalise to 70 counterparties. Never key on this column raw. Blank "
        "or `N/A` where the index names none.",
        "91 line 828; LOG s7.1, s7.2; DATA 99.1% filled"),
    "source_url": (
        "The WPDM download link for this letter as published INSIDE NIGC's "
        "`<table id=\"tablepress-2\">`, carrying its `wpdmdl=` and `ind=` "
        "ids. Links from elsewhere on the page are not letters: `wpdmdl=3974` "
        "is the sidebar and `wpdmdl=7374` is 'Helpful Hints for Submitting a "
        "Request for an Opinion Letter'. A distinct URL here is NOT evidence "
        "of a distinct document - see pdf_shared_with_opinion_ids.",
        "91 line 829; LOG s1.1"),
    "index_url": (
        "The NIGC declination-letters index page this row was scraped from, "
        "constant across the file. It is the citable public landing page; "
        "source_url is the object.",
        "91 line 830 (INDEX_URL constant)"),
    "pdf_path": (
        "Repository-relative path to the retrieved PDF under "
        "data/raw/external/nigc_declinations/pdf/. A local working path, not "
        "a citation - cite resolved_pdf_url or index_url instead. Blank on "
        "the letter NIGC's own link 404s.",
        "91 line 831 (manifest local_path)"),
    "pdf_md5": (
        "md5 of the retrieved PDF object. It is the identity test in this "
        "layer, because two index rows can carry different `wpdmdl` values, "
        "different URLs, and resolve to one identical object. All 325 objects "
        "were re-hashed on disk on 2026-08-07 and matched.",
        "91 line 832; LOG s1.1.2, s13"),
    "resolved_pdf_url": (
        "The URL the download link actually resolved to after its 302, "
        "carrying the real `filename=`. Resolved BEFORE anything is written, "
        "so the object's own name is known rather than assumed.",
        "91 line 833; LOG s13"),
    "fetched_date": (
        "Date the PDF was retrieved from nigc.gov. Retrieval date, not "
        "publication date and not opinion date.",
        "91 line 834"),
    "pdf_shared_with_opinion_ids": (
        "Pipe-separated ids of OTHER letters whose published link resolves to "
        "this exact same object (identical md5). Populated on the two rows of "
        "the one disclosed collision - NIGC-DL-20210412-01 (Yavapai-Apache / "
        "BOKF N.A.) and NIGC-DL-20210413-01 (Tunica Biloxi / First Guaranty "
        "Bank), which carry `wpdmdl` 3173 and 3175, the SAME `ind=3176`, and "
        "both serve the Yavapai-Apache document. A defect in the published "
        "archive, recorded rather than repaired.",
        "91 line 837; LOG s1.1.2; DATA 2 rows populated"),
    "retrieval_status": (
        "Whether this row's PDF was obtained and whether it may be read. "
        "`retrieved` (325); `not_retrieved_http_404` (1 - Kalispel / Wells "
        "Fargo 2014-05-19, listed in the agency's own index and not served by "
        "it); `pdf_link_serves_another_letters_document` (1 - the losing side "
        "of the md5 collision). NOTHING is extracted from either non-retrieved "
        "row: reading the shared PDF for both would attribute a "
        "Yavapai-Apache opinion to the Tunica-Biloxi Tribe.",
        "91 lines 839-861; DATA 325/1/1"),
    "retrieval_note": (
        "Prose stating, in full, why a row's retrieval_status is not plain "
        "`retrieved`, or - on a winning collision row - why this row is the "
        "one the shared PDF was attributed to (the resolved filename carries "
        "this row's date). Blank on an ordinary retrieval.",
        "91 lines 842-861; DATA 0.9% filled"),

    # -- tribe resolution ---------------------------------------------------
    "tribe_entity_id": (
        "Cedar entity-spine id for the tribe in index_tribe_string, or blank "
        "where the name was HELD. 307 of 327 letters resolve, to 140 distinct "
        "tribes. Resolution is `33_apply_party_rulings.resolve_entity` - the "
        "project's one resolver - called under this build's tribe guard.",
        "91 line 865; LOG s5"),
    "tribe_canonical_name": (
        "Canonical spine name of tribe_entity_id. It is OUR short canonical "
        "form (`Ione`, `Scotts Valley`), not NIGC's long official one, which "
        "stays verbatim in index_tribe_string.",
        "91 line 866; LOG s5"),
    "tribe_resolve_how": (
        "Which route resolved the tribe, or the named reason a candidate was "
        "REFUSED. Routes: `containment` 127, `core` 110, `alias` 48, `exact` "
        "22. Refusals: `no_spine_match` 8, "
        "`containment_refused_record_not_more_specific` 5, "
        "`containment_refused_non_government_class:<class>` 2, "
        "`ambiguous_containment:<n>:<names>` 2. The refusals are the tribe "
        "guard doing its job - unguarded containment resolved `Keweenaw Bay "
        "Indian Community` to Keweenaw Bay Ojibwa COLLEGE, `Cherokee Nation of "
        "Oklahoma` to the United Keetoowah Band (a different federally "
        "recognised tribe), and the placeholder `N/A` to Native American Bank "
        "N.A., because core('N/A') = {n, a}.",
        "91 lines 794-813, 867; LOG s5; DATA value counts"),
    "tribe_resolve_status": (
        "`RESOLVED` (307) or `HELD` (20). HELD means no spine entity was "
        "accepted and the name is staged for a hand ruling in "
        "review/nigc_declination_entities_held_2026-08-06.csv - most of the 20 "
        "are NIGC's own spellings. HELD is unfinished work, never a finding "
        "that the tribe is absent from the spine.",
        "91 line 868; LOG s5; DATA 307/20"),

    # -- what was readable --------------------------------------------------
    "n_pages": (
        "Pages from which text was extracted, after running headers and "
        "footers are stripped. Modal value 2. Zero on a row whose PDF was not "
        "retrieved.",
        "91 lines 877-880; DATA mode 2"),
    "text_chars": (
        "Characters of text recovered from the letter after running matter is "
        "stripped. The threshold that drives text_layer_quality: under 400 "
        "characters is treated as no text layer at all, because both PyMuPDF "
        "and `pdftotext -layout` return zero characters on NIGC's image-only "
        "scans. A near-empty extraction is a SCAN, not an empty document.",
        "91 lines 881, 887, 932; LOG s2"),
    "common_word_ratio": (
        "Share of alphabetic tokens in the recovered text that fall in a "
        "62-word list of ordinary English and NIGC boilerplate (the, of, and, "
        "opinion, management, contract, ...). A plausibility check on the "
        "text, not a quality score: it separates ordinary prose from scanner "
        "noise. Median 0.45 across the OCR-recovered letters; observed range "
        "0.0 to 0.535.",
        "91 lines 205-216, 882; LOG s14"),
    "n_conclusion_sentences": (
        "How many sentences in the letter carry an explicit opinion marker "
        "('it is my opinion that', 'I conclude', 'in my opinion') and do NOT "
        "carry a question marker ('whether', 'you have asked') or a "
        "legal-standard marker ('within the meaning of IGRA', 'C.F.R.', "
        "'is defined as'). Only these sentences may produce a finding. A first "
        "pass that matched 'management contract' anywhere in the letter "
        "produced 11 affirmative findings and ALL ELEVEN were false - the "
        "match was on the letter's question or on the footnoted legal "
        "standard, not on its answer.",
        "91 lines 261-329, 886; LOG s3.1"),
    "text_layer_quality": (
        "How this letter's text was obtained and whether the agency's standard "
        "conclusion language was recoverable from it. "
        "`standard_language_recovered` 158 (publisher text layer, finding "
        "quote found); `ocr_recovered_rapidocr` 158 (image-only scan read by "
        "OCR in the 2026-08-07 completion pass); "
        "`text_present_standard_language_not_recovered` 9; `no_text_layer` 2 "
        "- the agency's own 404 and its own mis-served link. Before the OCR "
        "pass 160 of 327 letters were image-only, concentrated in FY2015-2019 "
        "(140 letters, 5 readable), so any year series charted off the "
        "pre-OCR file was charting NIGC's scanner.",
        "91 lines 931-937; 100 (OCR pass); LOG s2, s14; DATA 158/158/9/2"),

    # -- the findings -------------------------------------------------------
    "is_management_contract": (
        "NIGC OGC's own answer to whether the submitted documents constitute a "
        "management contract under IGRA, read ONLY from a conclusion sentence. "
        "`NO_NOT_A_MANAGEMENT_CONTRACT` 284; `NOT_STATED_IN_OCR_TEXT` 28; "
        "`NOT_STATED_IN_TEXT_LAYER` 13; `NOT_EXTRACTABLE` 2. Zero affirmative "
        "findings survive across the whole archive, which is the expected "
        "shape - a document that IS a management contract goes to the NIGC "
        "CHAIR for approval under 25 U.S.C. 2711, not to OGC for a "
        "declination. `NOT_STATED_*` means the detector could not recover a "
        "conclusion sentence; it is not a finding of any kind.",
        "91 lines 889-896; LOG s3.3, s14.1, s17.3; DATA value counts"),
    "finding_quote": (
        "The agency's own conclusion sentence supporting is_management_"
        "contract, verbatim but for whitespace collapsing. Empty where no "
        "conclusion sentence was recovered. Running headers are stripped "
        "before any sentence is read: a conclusion straddling a page break "
        "extracted as 'do not <Letter to ... Page 2 of 2> constitute a "
        "management contract', which published Seminole and Choctaw Nation as "
        "finding the opposite of what they say.",
        "91 lines 877, 896; LOG s3.2"),
    "chair_approval_required": (
        "NIGC OGC's own answer to whether the arrangement requires the NIGC "
        "Chair's approval. `NO` 286; `NOT_STATED_IN_OCR_TEXT` 29; "
        "`NOT_STATED_IN_TEXT_LAYER` 10; `NOT_EXTRACTABLE` 2. Read only from a "
        "conclusion sentence, with an OCR-tolerant negation test - the 2013 "
        "scans read 'do not requit\"c the approval' and 'dues no! rcquir~ the "
        "approval', and a negation eaten by OCR inverts the finding.",
        "91 lines 898-905; LOG s2.1, s14.1; DATA value counts"),
    "chair_approval_quote": (
        "The agency's own conclusion sentence supporting "
        "chair_approval_required, verbatim but for whitespace collapsing.",
        "91 line 905"),
    "sole_proprietary_interest_analysis": (
        "NIGC OGC's own answer to whether the arrangement violates IGRA's "
        "requirement that the tribe retain the sole proprietary interest in "
        "its gaming operation. `NO_VIOLATION_FOUND` 284; "
        "`NOT_ADDRESSED_IN_OCR_TEXT` 22; "
        "`ADDRESSED_BUT_NOT_IN_A_CONCLUSION_SENTENCE` 14 (the letter discusses "
        "it, no conclusion sentence was recovered); `NOT_ADDRESSED_IN_TEXT_"
        "LAYER` 4; `NOT_EXTRACTABLE` 2; `VIOLATION_FOUND` 1. The single "
        "violation is NIGC-DL-20201020-01, Mashantucket Pequot / DraftKings, "
        "and it is CONDITIONAL - see finding_is_conditional.",
        "91 lines 907-916; LOG s3.3, s14.1; DATA value counts"),
    "sole_proprietary_interest_quote": (
        "The agency's own conclusion sentence supporting "
        "sole_proprietary_interest_analysis, verbatim but for whitespace "
        "collapsing. 'Nor, in my opinion, do they violate IGRA's sole "
        "proprietary interest mandate' is how the agency writes a NEGATIVE "
        "finding, and a naive test for 'violates' read six of these as "
        "violations.",
        "91 lines 308-316, 916; LOG s3.3"),
    "finding_is_conditional": (
        "1 where any of the three finding quotes carries a conditional marker "
        "(if, unless, to the extent, provided that, should); else 0. Set on "
        "exactly one row: NIGC-DL-20201020-01 concludes that '**if** gaming "
        "activity occurs on the Nation's Indian lands under the Agreement, "
        "then the Agreement violates IGRA's requirement...'. A conditional "
        "conclusion is a different asset from an unconditional one and must "
        "not be quoted as though the condition were established.",
        "91 lines 314, 918-923; LOG s3.3; DATA 1 row"),
    "material_change_warning": (
        "1 where the letter states that the opinion lapses if the reviewed "
        "documents change materially before closing; else 0. Set on 247 rows. "
        "This is a further reason a letter is not evidence of what was "
        "executed: the opinion is about the draft in front of the agency.",
        "91 lines 925-926; LOG s3.4, s14.1; DATA 247/80"),
    "material_change_quote": (
        "The letter's own material-change sentence, verbatim but for "
        "whitespace collapsing. Blank where the letter carries none.",
        "91 lines 328-329, 927"),
    "scope_limitation_quote": (
        "The letter's own scope-limiting sentence, verbatim - typically 'this "
        "opinion is limited to ... and does not include or extend to any other "
        "agreements not submitted for review'. Blank where the letter carries "
        "none.",
        "91 lines 348-350, 928; LOG s3.4, s14.1"),
    "documents_unexecuted_quote": (
        "The letter's own sentence establishing that the documents reviewed "
        "were UNEXECUTED - 'unexecuted', 'not been executed', 'substantially "
        "final form', 'prior to their execution'. This is the sentence that "
        "supports evidentiary_stage on the row, in the agency's own words "
        "rather than ours. Blank where the letter carries none.",
        "91 lines 351-354, 929; LOG s0, s14.1"),

    # -- letter surface -----------------------------------------------------
    "re_line": (
        "The letter's `Re:` subject line, taken as the text between 'Re:' and "
        "'Dear'. It names the agreement and usually the tribe, which is why "
        "counterparty overlap against the deals ledger is computed on the "
        "counterparty strings ONLY and never against this column - doing "
        "otherwise matched 'Shingle Springs' to 'Shingle Springs' and "
        "manufactured a counterparty match out of the tribe's own name.",
        "91 lines 940-941; LOG s17.2.1"),
    "addressee": (
        "The person the letter is addressed to, taken from the text after "
        "'Dear'. Typically counsel for the tribe or the lender. Populated on "
        "48.9% of rows; blank where the salutation was not recovered.",
        "91 lines 942-943; DATA 48.9% filled"),
    "signer": (
        "The NIGC Office of General Counsel attorney who signed the letter, "
        "taken from the block after 'Sincerely'. Michael Hoenig and Rea "
        "Cisneros sign most of the readable archive. Populated on 42.2% of "
        "rows; blank where the signature block was not recovered, which is "
        "not evidence the letter is unsigned.",
        "91 lines 944-946; LOG s3.4; DATA 42.2% filled"),
    "signer_title": (
        "The signer's title as printed: `General Counsel` 122, `Acting General "
        "Counsel` 14, `Associate General Counsel` 2, blank 189. Only these "
        "three titles are accepted, because the signature-block pattern "
        "requires them - it is what distinguishes the signature from any other "
        "name in the letter.",
        "91 lines 944-947; DATA value counts"),

    # -- agreement typology and lineage -------------------------------------
    "agreement_type": (
        "Pipe-separated types of the documents NIGC reviewed, detected in the "
        "Re: line and the first 6,000 characters against nine labels: "
        "loan_or_credit_agreement, note_indenture_or_bond, "
        "security_or_collateral_agreement, lease, "
        "equipment_or_gaming_machine_agreement, technology_or_systems_"
        "agreement, development_or_construction_agreement, "
        "consulting_or_services_agreement, amendment_or_restatement. A letter "
        "commonly carries several. This types the DOCUMENTS SUBMITTED, not a "
        "transaction that occurred.",
        "91 lines 361-386, 949-957; LOG s7"),
    "agreement_type_basis": (
        "For each label in agreement_type, the literal substring that matched, "
        "as `label<-'matched text'`. It is what makes the typology auditable "
        "one row at a time rather than a black box, and it is how the "
        "`collateral` homonym was caught: 25 C.F.R. 502.5 defines a "
        "'collateral agreement' as a contract related to a gaming operation, "
        "nothing to do with security for a loan.",
        "91 line 958; LOG s4.3"),
    "amendment_number": (
        "Which amendment the reviewed instrument is, as an integer, read from "
        "'<ordinal> amendment' or 'Amendment No. N' in the letter. Populated "
        "on 52 rows, 1 through 9. Blank where the letter names no ordinal - "
        "including on letters that ARE amendments but do not number "
        "themselves, so a blank is not evidence of a first agreement.",
        "91 lines 388-397, 960-967; DATA 52 rows populated"),
    "amendment_quote": (
        "The letter's own phrase that supplied amendment_number, verbatim. "
        "Blank wherever amendment_number is blank.",
        "91 line 964"),
    "prior_financing_reference": (
        "A verbatim sentence in which the letter refers to an EARLIER OGC "
        "review or letter for the same parties - e.g. 'was the subject of a "
        "declination letter issued on January 12, 2026'. It is the evidence "
        "that this letter belongs to a running relationship rather than a new "
        "one, which is what stops one long financing relationship being "
        "counted as several unrelated deals.",
        "91 lines 397-400, 969; LOG s7.1; DATA 67.9% filled"),
    "lineage_relations_in_text": (
        "Pipe-separated relations the letter states in its own words between "
        "the reviewed documents and earlier ones: AMENDS, RESTATES, "
        "REFINANCES, EXTENDS, SUPERSEDES. Blank on 222 rows. Used with the "
        "tribe and the significant tokens of the counterparty string to group "
        "letters into financing chains; where a chain names no relation the "
        "fallback label is FINANCING_FOR. Grouping on the whole counterparty "
        "string under-detects badly, because NIGC writes one lender several "
        "ways.",
        "91 lines 970-981; LOG s7.1; DATA value counts"),

    # -- the two constants that must travel with the row --------------------
    "evidence_meaning": (
        "The agency's own evidentiary limit, written on EVERY row so it "
        "survives a join: NIGC OGC reviewed the SUBMITTED, UNEXECUTED "
        "documents named in the letter and reached the legal conclusion "
        "recorded here, and this is NOT evidence that the transaction closed, "
        "that any agreement was executed, that a property opened or operates, "
        "or that land is in trust or gaming-eligible. NIGC's own index says "
        "documents 'should be submitted prior to their execution (unsigned) as "
        "the General Counsel will not provide a declination letter for "
        "executed documents.' A sentence in a build log does not survive a "
        "join; a column does.",
        "91 lines 983-990; LOG s0, s16"),
    "absence_meaning": (
        "The companion limit, also on every row: NIGC review is voluntary, is "
        "offered as a courtesy, and posting is subject to a FOIA release "
        "review, so this archive is NOT a census of tribal gaming agreements. "
        "A property or tribe with no letter is not a property or tribe with no "
        "financing. No count from this file is a count of tribal gaming "
        "agreements and no tribe's absence from it means anything.",
        "91 lines 991-995; LOG s0, s12.1, s18.1"),
    "built_date": (
        "Date this row was written by the build. Provenance of the ROW, not of "
        "the letter - opinion_date is the letter's date and fetched_date is "
        "the retrieval's.",
        "91 line 996"),
}

# ---------------------------------------------------------------------------
# TIERED INTERNAL RATHER THAN PUBLISHED.
#
# The rule for this pass was: define it from its own evidence, or tier it
# internal and say why. Never write a plausible sentence to clear a counter.
# One column is tiered, and it is not tiered because its meaning is unknown -
# it is tiered because the VALUE is a path on this machine and means nothing
# to a subscriber. It still carries its definition above.
# ---------------------------------------------------------------------------
TIER_INTERNAL = {
    "pdf_path": "a working path under data/raw/ on the build machine, not a "
                "citation; resolved_pdf_url and index_url are the public "
                "references to the same object",
}

FIELDS = ["dataset", "variable", "type", "units", "pct_filled", "n_rows",
          "published", "access_tier", "description", "generated"]


def read_rows(p):
    with open(p, encoding="utf-8-sig", errors="replace", newline="") as fh:
        rd = csv.DictReader(fh)
        return list(rd), list(rd.fieldnames or [])


def write_rows(p, rows, fields):
    tmp = p.with_suffix(p.suffix + ".part")
    with open(tmp, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)
    tmp.replace(p)


def patch(rows, report):
    """Fill blank descriptions on the 07o block. Returns (filled, tiered)."""
    filled = tiered = 0
    for r in rows:
        if r.get("dataset") != BLOCK:
            continue
        var = (r.get("variable") or "").strip()
        d = DEFS.get(var)
        if d and not (r.get("description") or "").strip():
            r["description"] = d[0]
            filled += 1
            if report:
                print(f"    + {var:38s} [{d[1]}]")
        elif d is None and not (r.get("description") or "").strip():
            print(f"    !! {var} has no definition and no description - "
                  f"the gate will still fail on it")
        if var in TIER_INTERNAL and r.get("access_tier") != "internal":
            r["access_tier"] = "internal"
            r["published"] = "0"
            tiered += 1
            if report:
                print(f"    ~ {var:38s} -> internal: {TIER_INTERNAL[var]}")
    return filled, tiered


def main():
    dry = "--dry-run" in sys.argv
    print("=" * 74)
    print("174 - documenting the 07o_nigc_declinations codebook block")
    print(f"    {'DRY RUN - nothing will be written' if dry else 'writing'}")
    print("=" * 74)

    for p in (FRAG, MASTER):
        if not p.exists():
            print(f"  ABSENT: {p} - nothing done")
            return 1

    total_filled = 0
    for p in (FRAG, MASTER):
        rows, fields = read_rows(p)
        fields = fields or FIELDS
        block = [r for r in rows if r.get("dataset") == BLOCK]
        blank_before = sum(1 for r in block
                           if not (r.get("description") or "").strip())
        print(f"\n  {p.relative_to(CEDAR)}")
        print(f"    {len(rows):,} rows | {len(block)} in {BLOCK} | "
              f"{blank_before} with no description")
        filled, tiered = patch(rows, report=True)
        total_filled += filled
        blank_after = sum(1 for r in rows if r.get("dataset") == BLOCK
                          and not (r.get("description") or "").strip())
        still_public = sum(1 for r in rows if r.get("published") == "1"
                           and not (r.get("description") or "").strip())
        print(f"    filled {filled} | tiered internal {tiered} | "
              f"{blank_after} still blank in the block | "
              f"{still_public} undocumented public rows FILE-WIDE")
        if dry:
            continue
        bak = p.with_name(p.name + f".bak_{TODAY}_pre174")
        if not bak.exists():
            shutil.copy2(p, bak)
            print(f"    backed up -> {bak.name}")
        write_rows(p, rows, fields)
        print(f"    wrote {p.name} (.part then rename)")

    print(f"\n  {total_filled} descriptions written across both files.")
    print("  Now run: py -3 code/62_no_regression_check.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
