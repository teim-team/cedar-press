#!/usr/bin/env python3
"""
cedar_extent_competed.py — the ONE FPDS extent-competed crosswalk.

Standing rule 8 (AGENTS.md): never write a second matcher. This module is the
only place in the repo that maps an `extent_competed` token to a meaning.
`code/207_normalize_extent_competed.py` imports it; so must any future build of
`prime_contracts.csv` (`40_build_prime_contracts.py`,
`114_pull_prime_archive.py`).

WHY THIS EXISTS
---------------
`docs/CICD_BENCHMARK.md` finding INTERNAL-05 (HIGH): `extent_competed` on
`prime_contracts.csv` carries TWO VOCABULARIES — raw FPDS codes on some rows
and rendered description tags on others — with no crosswalk anywhere. A filter
on either vocabulary therefore selects a SOURCE VINTAGE, not a competition
status.

THE CROSSWALK IS NOT OURS AND WAS NOT INFERRED FROM OUR DATA.
It is quoted verbatim from the authoritative federal dictionary. It was NOT
reconstructed by matching letters to labels by frequency: a guessed crosswalk
that looks right is worse than none, because it never gets questioned again.

SOURCE, QUOTED VERBATIM
-----------------------
    DATA Act Information Model Schema (DAIMS) — Data Element Crosswalk (DEC)
    DAIMS-DEC v2.2, Revision Date: 2022-06-03
    sheet "Public", element `ExtentCompeted`
    ("FPDS Data Dictionary Element" = "Extent Competed"), column "Domain Values"

    https://files.usaspending.gov/docs/Data_Dictionary_Crosswalk.xlsx
    (the file served behind https://www.usaspending.gov/data-dictionary;
     retrieved 2026-08-26, HTTP 200, 110,540 bytes,
     md5 0353550157c0c66278f67147ff916d9e)

Definition, verbatim from the same row:

    "A code that represents the competitive nature of the contract."

Domain Values cell, verbatim (newline-separated in the source cell):

    A = FULL AND OPEN COMPETITION
    B = NOT AVAILABLE FOR COMPETITION
    C = NOT COMPETED
    D = FULL AND OPEN COMPETITION AFTER EXCLUSION OF SOURCES
    E = FOLLOW ON TO COMPETED ACTION
    F = COMPETED UNDER SAP
    G = NOT COMPETED UNDER SAP
    CDO = COMPETITIVE DELIVERY ORDER
    NDO = NON-COMPETITIVE DELIVERY ORDER

The same DEC row also settles WHY one Cedar column holds both vocabularies.
They are TWO DIFFERENT USAspending download fields:

  | DEC element                      | USAspending download column | holds |
  |----------------------------------|-----------------------------|-------|
  | `ExtentCompeted`                 | `extent_competed_code`      | code  |
  | `Extent Competed Description Tag`| `extent_competed`           | label |

  "Extent Competed Description Tag — Description tag (by way of the FPDS Atom
   Feed) that explains the meaning of the code provided in the Extent Competed
   Field."

`114_pull_prime_archive.py` reads the archive column named `extent_competed`,
which the dictionary says is the DESCRIPTION TAG. It is the label from FY2017
onward and the CODE for FY2007-FY2016 — measured in the raw extracts at
`data/raw/contracts/usaspending_archive_2026-08-07/filtered/`, so the seam is
UPSTREAM, in the award archive's own monthly files, not in Cedar's extraction.

WHAT THE DICTIONARY DOES NOT DEFINE
-----------------------------------
The literal token `nan` (uppercased to `NAN` by 114's `.upper()`). It is not a
domain value. It is a stringified null and is normalised to `NOT_REPORTED`,
never to a competition status. Blank is likewise `NOT_REPORTED`.

SUBSTANTIVE MEANING (for anyone reading the categories, not just filtering)
--------------------------------------------------------------------------
FAR Part 6 implements 41 U.S.C. ch. 33 (the Competition in Contracting Act).
A = FAR 6.102 full and open; D = full and open after exclusion of sources
(FAR 6.2); B/C = the FAR 6.3 exceptions; F/G = Simplified Acquisition
Procedures (FAR Part 13), which are NOT a FAR Part 6 competition at all;
CDO/NDO describe fair-opportunity on delivery/task orders (FAR 16.505(b)(1)).
**"Competed" is therefore not one line through this vocabulary** — grouping is
a research decision and must be stated, not assumed.
"""
from __future__ import annotations

# ---------------------------------------------------------------------------
# THE CROSSWALK. Transcribed character-for-character from the Domain Values
# cell quoted in the docstring. Do not edit without re-reading that cell.
# ---------------------------------------------------------------------------
FPDS_EXTENT_COMPETED = {
    "A": "FULL AND OPEN COMPETITION",
    "B": "NOT AVAILABLE FOR COMPETITION",
    "C": "NOT COMPETED",
    "D": "FULL AND OPEN COMPETITION AFTER EXCLUSION OF SOURCES",
    "E": "FOLLOW ON TO COMPETED ACTION",
    "F": "COMPETED UNDER SAP",
    "G": "NOT COMPETED UNDER SAP",
    "CDO": "COMPETITIVE DELIVERY ORDER",
    "NDO": "NON-COMPETITIVE DELIVERY ORDER",
}

VALID_LABELS = frozenset(FPDS_EXTENT_COMPETED.values())

CROSSWALK_ID = "DAIMS-DEC v2.2 ExtentCompeted"
CROSSWALK_URL = "https://files.usaspending.gov/docs/Data_Dictionary_Crosswalk.xlsx"

# Tokens that are an ABSENCE, not a value. `nan` is a stringified null; it is
# not in the dictionary and must never be read as a competition status.
NULL_TOKENS = {"", "NAN", "NA", "N/A", "NONE", "NULL"}

NOT_REPORTED = "NOT_REPORTED"
UNDEFINED = "UNDEFINED_BY_DICTIONARY"

_B = f"{CROSSWALK_ID} | {CROSSWALK_URL} | "
BASIS_CODE_MAPPED = _B + "FPDS_CODE_MAPPED"
BASIS_LABEL_AS_RECORDED = _B + "LABEL_AS_RECORDED"
BASIS_NOT_REPORTED_BLANK = _B + "NOT_REPORTED_BLANK"
BASIS_NOT_REPORTED_NULL_TOKEN = _B + "NOT_REPORTED_NULL_TOKEN"
BASIS_UNDEFINED = _B + "UNDEFINED_BY_DICTIONARY"


def normalize(raw: str) -> tuple[str, str]:
    """Return (normalized_label, basis) for one raw `extent_competed` token.

    NEVER guesses. A token that is neither a dictionary code nor a dictionary
    label comes back as UNDEFINED_BY_DICTIONARY with the raw value left intact
    in `extent_competed`, which is the column of record.
    """
    s = (raw or "").strip().upper()
    if s == "":
        return NOT_REPORTED, BASIS_NOT_REPORTED_BLANK
    if s in NULL_TOKENS:
        return NOT_REPORTED, BASIS_NOT_REPORTED_NULL_TOKEN
    if s in FPDS_EXTENT_COMPETED:
        return FPDS_EXTENT_COMPETED[s], BASIS_CODE_MAPPED
    if s in VALID_LABELS:
        return s, BASIS_LABEL_AS_RECORDED
    return UNDEFINED, BASIS_UNDEFINED
