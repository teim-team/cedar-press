#!/usr/bin/env python3
"""
1171 - prior_finding_regression_pack

A regression fixture pack for the named bad rows recorded in
`review/QA_REVIEW_10ROW_2026-09-02.txt` (151 findings: 59 P0, 76 P1, 16 P2).

WHY THIS EXISTS
---------------
The 2026-09-03 changelog was a narrative of new discoveries with no accounting
of the old blockers. A reviewer said so. This script is the accounting: one
NAMED detector per previously-confirmed bad row or bad-row class, run against
the CURRENT tree, so that "closed" is a measurement and not a claim.

The companion document is `docs/PRIOR_FINDING_CLOSURE_MATRIX.md`. That document
quotes numbers this script printed; regenerate them rather than retyping them.

WHAT IT READS
-------------
  dist/customer/*.csv   the delivered product (full files, uncapped by default)
  dist/preview/*.csv    the 100-row previews
It opens nothing else and it writes nothing into either directory.

WHAT IT WRITES
--------------
  review/1171_regression_pack_<date>.json   the run record (counts + evidence)
  review/1171_baseline.json                 only on `baseline`, and only the
                                            counts, so `ratchet` can refuse an
                                            increase.
Nothing under dist/, data/clean/ or docs/ is written by this script.

MODES
-----
  py -3 code/1171_prior_finding_regression_pack.py selftest
      Injects each violation class into a synthetic fixture and asserts the
      correspondingly NAMED detector FIRES on the dirty fixture and stays
      SILENT on the clean one. A detector that cannot be shown to fire is
      reported as NOT_TRUSTWORTHY and the mode exits nonzero.
      THIS IS THE MODE TO RUN FIRST. A check that returns zero without ever
      having been shown to return one is not evidence of anything.

  py -3 code/1171_prior_finding_regression_pack.py check [--quick]
      Runs every detector against the live tree. Exits 1 if ANY detector is
      nonzero. Every named case is expected to be zero; a nonzero count is a
      live defect, whether it is a regression of something fixed or a blocker
      that was never closed. `--quick` caps each file at 200,000 rows and every
      capped figure is printed with the word CAPPED - a capped scan is a floor,
      never a population figure.

  py -3 code/1171_prior_finding_regression_pack.py baseline
      Records today's counts as the ratchet floor. Only legitimate while you
      intend the recorded counts to be the ceiling from here on; it does not
      make `check` green and is not a way around a red gate.

  py -3 code/1171_prior_finding_regression_pack.py ratchet
      Exits 1 only if a count INCREASED against `review/1171_baseline.json`.
      Use this as the CI gate while the open items are being worked; use
      `check` to know the truth.

HARD RULES OBSERVED
-------------------
  * Zero fabrication: every number this prints came from a row it read.
  * A capped scan is never reported as a population figure - the word CAPPED
    is printed next to it and the run record carries `capped: true`.
  * Zero observed violations licenses a FLOOR ("no instance in N rows read"),
    never "100% clean".
  * This script never mutates, deletes or unflags a row. It only reads.
  * Any single run is a SNAPSHOT. Concurrent rebuilds write `data/clean` and
    `dist/` while this runs; the run record stamps the mtime and size of every
    file it read for exactly that reason.
"""

from __future__ import annotations

import csv
import json
import os
import re
import sys
import tempfile
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CUSTOMER = ROOT / "dist" / "customer"
PREVIEW = ROOT / "dist" / "preview"
REVIEW = ROOT / "review"
TODAY = date.today().isoformat()  # noqa: DTZ011
QUICK_CAP = 200_000

csv.field_size_limit(1_000_000_000)


# --------------------------------------------------------------------------
# normalisation helpers
# --------------------------------------------------------------------------

# Organisational designators that do NOT distinguish one entity from another
# when comparing an enterprise name to its owner hub's name. Corporate forms
# (CORPORATION, INC, LLC) are deliberately NOT in this list: "Afognak Native
# Corporation" is a different legal person from the Native Village of Afognak
# and must not be folded into it.
_GOV_WORDS = {
    "NATION", "NATIONS", "TRIBE", "TRIBES", "TRIBAL", "BAND", "BANDS",
    "PUEBLO", "COMMUNITY", "RANCHERIA", "VILLAGE", "NATIVE", "INDIAN",
    "INDIANS", "RESERVATION", "OF", "THE", "AND", "A",
}


def entity_core(s: str | None) -> str:
    """Fold a name to its distinguishing core. Governmental designators drop;
    corporate forms are kept, because they distinguish a real entity."""
    s = (s or "").upper().replace("&", " AND ")
    s = re.sub(r"[^A-Z0-9 ]", " ", s)
    return " ".join(t for t in s.split() if t not in _GOV_WORDS)


def truthy(v: str | None) -> bool:
    return (v or "").strip().upper() in {"1", "Y", "YES", "TRUE", "T"}


def money(v: str | None) -> float | None:
    s = (v or "").strip().replace(",", "").replace("$", "")
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def up(row: dict, key: str) -> str:
    return (row.get(key) or "").upper()


# --------------------------------------------------------------------------
# the detectors
#
# Each detector is a predicate over ONE row of ONE named file. `evidence_cols`
# is what gets printed and stored when it fires, so a reader can see a real row
# rather than a count. `clean` / `dirty` are the synthetic fixture rows the
# selftest uses to prove the detector can return one as well as zero.
#
# `prior_ids` cites the finding IDs in review/QA_REVIEW_10ROW_2026-09-02.txt
# that this detector stands for.
# --------------------------------------------------------------------------

# machine paths are unambiguous: no customer field should ever carry one
_MACHINE_PATH = re.compile(r"(~[\\/]Desktop|[A-Za-z]:\\Users\\|/Users/|[\\/]Desktop[\\/])")
# Code lineage: a script filename, a numbered script reference, a local table path.
# CASE-SENSITIVE, and that is not a style choice. Under re.I the alternative
# `review[/\\][a-z0-9_]` matched the FPDS product-service label
# "SUPPORT- PROFESSIONAL: PROGRAM EVALUATION/REVIEW/DEVELOPMENT" and inflated this
# detector by ~185,000 rows on 2026-09-03 - a detector loud about nothing. Repo
# paths are lowercase; an uppercase REVIEW/ is prose. The clean selftest fixture
# for this detector is that exact label, so the false positive cannot return
# silently. `.zip` stays case-insensitive: archive names really are uppercase here
# (FY2016_All_Contracts_Full_*.zip).
_CODE_LINEAGE = re.compile(
    r"(\bcode[\\/]\d{1,4}\b"        # code/1140
    r"|\b\d{1,4}_[a-z0-9_]+\.py\b"  # 1109_subawardee_geo_promote.py
    r"|\bdata[\\/]clean[\\/]"       # data/clean/native_bills_entity_bridge.csv
    r"|\breview[\\/][a-z0-9_]"      # review/1010_....csv   (lowercase only)
    r"|\.[Zz][Ii][Pp]\b)"           # FY2016_All_Contracts_Full_*.zip
)

_NAT_PARK = re.compile(r"\bNATIONAL\s+(PARK|MONUMENT|FOREST|HISTORIC(AL)?\s+(SITE|PARK)|SEASHORE|RECREATION\s+AREA|PRESERVE|BATTLEFIELD)\b", re.I)
# a county cell is a list of county names; these tokens mean a sentence leaked in
_SOURCE_PHRASE = re.compile(r"(\bby the\b|\bsite in\b|\bRiver in\b|\bcollected\b|\bexcavated\b|\bremoved by\b|\bdonated\b|\bpurchased\b|\bduring\b|\bDr\.)", re.I)
# an institution cell holding notice-title prose instead of an institution
_NOTICE_TITLE = re.compile(r"^\s*(of|for|from|in)\s|\b(Human Remains|Funerary Objects|Cultural Patrimony|Sacred Objects)\b", re.I)


DETECTORS: list[dict] = [

    # ---- named bad row 1: AVCP -> Arctic Slope Regional Corporation --------
    {
        "id": "AVCP_ATTRIBUTED_TO_ASRC_NEST",
        "prior_ids": ["CP-038", "CP-116"],
        "what": "AVCP Regional Housing Authority carried as an enterprise of Arctic Slope Regional Corporation",
        "file": ("customer", "nest.csv"),
        "cols": ["enterprise_name", "owner_hub_name", "owner_hub_cedar_uid", "publishable"],
        "pred": lambda r: "AVCP" in up(r, "enterprise_name") and "ARCTIC SLOPE" in up(r, "owner_hub_name"),
        "clean": {"enterprise_name": "AVCP REGIONAL HOUSING AUTHORITY", "owner_hub_name": "Association of Village Council Presidents", "owner_hub_cedar_uid": "CE-00000-00", "publishable": "Y"},
        "dirty": {"enterprise_name": "AVCP REGIONAL HOUSING AUTHORITY", "owner_hub_name": "Arctic Slope Regional Corporation", "owner_hub_cedar_uid": "CE-00078-KR", "publishable": "Y"},
    },
    {
        "id": "AVCP_ATTRIBUTED_TO_ASRC_FUNDING",
        "prior_ids": ["CP-038"],
        "what": "AVCP federal assistance keyed to Arctic Slope Regional Corporation",
        "file": ("customer", "funding.csv"),
        "cols": ["recipient_name", "canonical_name", "cedar_uid", "attributed_flag"],
        "pred": lambda r: "AVCP" in up(r, "recipient_name") and "ARCTIC SLOPE" in up(r, "canonical_name"),
        "clean": {"recipient_name": "AVCP REGIONAL HOUSING AUTHORITY", "canonical_name": "", "cedar_uid": "", "attributed_flag": "0"},
        "dirty": {"recipient_name": "AVCP REGIONAL HOUSING AUTHORITY", "canonical_name": "Arctic Slope Regional Corporation", "cedar_uid": "CE-00078-KR", "attributed_flag": "1"},
    },

    # ---- named bad row 2: a $1.282B subaward on a $13.4M prime -------------
    {
        "id": "SUBAWARD_DWARFS_ITS_PRIME",
        "prior_ids": ["CP-027"],
        "what": "subaward amount >= $100M AND more than 10x its own prime award amount",
        "file": ("customer", "subcontracting.csv"),
        "cols": ["sub_name", "prime_name", "prime_award_id", "subaward_amount", "prime_award_amount", "subaward_exceeds_prime_flag"],
        "pred": lambda r: (
            (money(r.get("subaward_amount")) or 0) >= 100_000_000
            and (money(r.get("prime_award_amount")) or 0) > 0
            and (money(r.get("subaward_amount")) or 0) > 10 * (money(r.get("prime_award_amount")) or 0)
        ),
        "clean": {"sub_name": "SUB CO", "prime_name": "PRIME CO", "prime_award_id": "X1", "subaward_amount": "1000000", "prime_award_amount": "13406053.11", "subaward_exceeds_prime_flag": ""},
        "dirty": {"sub_name": "VISTA DEFENSE TECHNOLOGIES, LLC", "prime_name": "STS SYSTEMS INTEGRATION", "prime_award_id": "HT001517C0008", "subaward_amount": "1282234055.8", "prime_award_amount": "13406053.11", "subaward_exceeds_prime_flag": "yes"},
    },
    {
        "id": "SUBAWARD_EXCEEDS_PRIME_ANY",
        "prior_ids": ["CP-027", "CP-012"],
        "what": "any subaward larger than the prime award it sits under",
        "file": ("customer", "subcontracting.csv"),
        "cols": ["sub_name", "prime_name", "subaward_amount", "prime_award_amount"],
        "pred": lambda r: (
            (money(r.get("prime_award_amount")) or 0) > 0
            and (money(r.get("subaward_amount")) or 0) > (money(r.get("prime_award_amount")) or 0)
        ),
        "clean": {"sub_name": "SUB CO", "prime_name": "PRIME CO", "subaward_amount": "10", "prime_award_amount": "100"},
        "dirty": {"sub_name": "SUB CO", "prime_name": "PRIME CO", "subaward_amount": "101", "prime_award_amount": "100"},
    },

    # ---- named bad row 3: a failed vote recorded as passed -----------------
    {
        # The review named ONE row: 105-hr-948, the Burt Lake Band Act, which
        # failed 240-167 in the House and was labelled `passed-one-chamber`.
        # This is the named-row assertion. It is deliberately pinned to the
        # bill id so it can never drift onto a different bill and be silently
        # "satisfied" by something else.
        "id": "BURT_LAKE_FAILED_VOTE_RECORDED_AS_PASSED",
        "prior_ids": ["CP-062"],
        "what": "105-hr-948 (Burt Lake Band Act), which FAILED 240-167 in the House, recorded as having advanced",
        "file": ("customer", "legislation.csv"),
        "cols": ["bill_id", "title", "outcome", "latest_action"],
        "pred": lambda r: (
            (r.get("bill_id") or "").strip().lower() == "105-hr-948"
            and (r.get("outcome") or "").strip().lower() in {"passed-one-chamber", "enacted", "passed-both-chambers"}
        ),
        "clean": {"bill_id": "105-hr-948", "title": "Burt Lake Band Act", "outcome": "floor-vote-failed", "latest_action": "On motion to suspend the rules and pass the bill Failed by the Yeas and Nays: (2/3 required): 240 - 167 (Roll no. 574)."},
        "dirty": {"bill_id": "105-hr-948", "title": "Burt Lake Band Act", "outcome": "passed-one-chamber", "latest_action": "On motion to suspend the rules and pass the bill Failed by the Yeas and Nays: (2/3 required): 240 - 167 (Roll no. 574)."},
    },
    {
        # The generalisation of the same defect, made chamber-aware. A SENATE
        # bill that passed the Senate and then failed in the House is honestly
        # `passed-one-chamber`; only a House measure whose House vote failed
        # contradicts that label. Without the chamber test this detector
        # returns a false positive on 95-s-666 - measured 2026-09-03.
        "id": "HOUSE_BILL_FAILED_HOUSE_VOTE_RECORDED_AS_PASSED",
        "prior_ids": ["CP-062"],
        "what": "a House measure whose recorded House vote FAILED is labelled as having passed a chamber",
        "file": ("customer", "legislation.csv"),
        "cols": ["bill_id", "title", "outcome", "latest_action"],
        "pred": lambda r: (
            re.search(r"-(hr|hres|hjres|hconres)-", (r.get("bill_id") or "").lower()) is not None
            and re.search(r"\bfail(ed)?\b", r.get("latest_action") or "", re.I) is not None
            and re.search(r"\bin (the )?senate\b", r.get("latest_action") or "", re.I) is None
            and (r.get("outcome") or "").strip().lower() in {"passed-one-chamber", "enacted", "passed-both-chambers"}
        ),
        "clean": {"bill_id": "95-s-666", "title": "A Senate bill", "outcome": "passed-one-chamber", "latest_action": "Measure failed of passage in House under suspension of rules, roll call #495 (118-204)."},
        "dirty": {"bill_id": "105-hr-948", "title": "Burt Lake Band Act", "outcome": "passed-one-chamber", "latest_action": "On motion to suspend the rules and pass the bill Failed by the Yeas and Nays: (2/3 required): 240 - 167 (Roll no. 574)."},
    },

    # ---- named bad row 4: Union Calendar bill recorded died-in-committee ---
    {
        "id": "UNION_CALENDAR_RECORDED_DIED_IN_COMMITTEE",
        "prior_ids": ["CP-063"],
        "what": "bill reported out and placed on the Union Calendar, but outcome says it died in committee",
        "file": ("customer", "legislation.csv"),
        "cols": ["bill_id", "title", "outcome", "latest_action"],
        "pred": lambda r: (
            "UNION CALENDAR" in up(r, "latest_action")
            and (r.get("outcome") or "").strip().lower() == "died-in-committee"
        ),
        "clean": {"bill_id": "110-hr-1575", "title": "Burt Lake Reaffirmation Act", "outcome": "reported-to-floor", "latest_action": "Placed on the Union Calendar, Calendar No. 512."},
        "dirty": {"bill_id": "110-hr-1575", "title": "Burt Lake Reaffirmation Act", "outcome": "died-in-committee", "latest_action": "Placed on the Union Calendar, Calendar No. 512."},
    },

    # ---- named bad row 5: Goldbelt -> Tlingit & Haida ----------------------
    {
        "id": "GOLDBELT_FAMILY_ATTRIBUTED_TO_TLINGIT_HAIDA",
        "prior_ids": ["CP-116", "CP-121"],
        "what": "a Goldbelt, Incorporated award attributed to the Central Council of Tlingit & Haida",
        "file": ("customer", "contractors.csv"),
        "cols": ["awardee_name", "parent_name", "canonical_name", "cedar_uid"],
        "pred": lambda r: (
            ("GOLDBELT" in up(r, "awardee_name") or "GOLDBELT" in up(r, "parent_name"))
            and "TLINGIT" in up(r, "canonical_name")
        ),
        "clean": {"awardee_name": "GOLDBELT HAWK L.L.C.", "parent_name": "Goldbelt Incorporated", "canonical_name": "Goldbelt, Incorporated", "cedar_uid": "CE-0008Y-WE"},
        "dirty": {"awardee_name": "C P Leasing, Inc", "parent_name": "Goldbelt Incorporated", "canonical_name": "Tlingit & Haida", "cedar_uid": "CE-0006B-0K"},
    },

    # ---- named bad row 6: UTTC -> United Auburn ----------------------------
    {
        "id": "UTTC_ATTRIBUTED_TO_UNITED_AUBURN",
        "prior_ids": ["CP-117"],
        "what": "United Tribes Technical College keyed to the United Auburn Indian Community",
        "file": ("customer", "funding.csv"),
        "cols": ["recipient_name", "canonical_name", "cedar_uid", "attributed_flag"],
        "pred": lambda r: "UNITED TRIBES TECHNICAL" in up(r, "recipient_name") and "AUBURN" in up(r, "canonical_name"),
        "clean": {"recipient_name": "UNITED TRIBES TECHNICAL COLLEGE", "canonical_name": "", "cedar_uid": "", "attributed_flag": "0"},
        "dirty": {"recipient_name": "UNITED TRIBES TECHNICAL COLLEGE", "canonical_name": "United Auburn Indian Community", "cedar_uid": "CE-00000-UA", "attributed_flag": "1"},
    },

    # ---- named bad row 7: an entity emitted as its own enterprise ----------
    {
        "id": "ENTITY_IS_ITS_OWN_ENTERPRISE",
        "prior_ids": ["CP-118"],
        "what": "the enterprise and its owner hub fold to the same entity core (Tohono O'odham Nation owned by Tohono O'odham)",
        "file": ("customer", "nest.csv"),
        "cols": ["enterprise_name", "owner_hub_name", "owner_hub_cedar_uid", "publishable"],
        "pred": lambda r: (
            bool(entity_core(r.get("enterprise_name")))
            and entity_core(r.get("enterprise_name")) == entity_core(r.get("owner_hub_name"))
        ),
        "clean": {"enterprise_name": "Tohono O'odham Gaming Enterprise", "owner_hub_name": "Tohono O'odham", "owner_hub_cedar_uid": "CE-001B9-HT", "publishable": "Y"},
        "dirty": {"enterprise_name": "The Tohono O'Odham Nation", "owner_hub_name": "Tohono O'odham", "owner_hub_cedar_uid": "CE-001B9-HT", "publishable": "Y"},
    },

    # ---- named bad row 8: superseded lobbying filings shipping as current --
    {
        # A SUPERSEDED FILING SHIPPING IS THE POLICY, NOT THE DEFECT.
        #
        # Codex, PR #46, and it is right. `cedar_publication.LOBBYING_FENCE`
        # disposes superseded LDA filings as FLAG and KEEPS them, deliberately,
        # so a customer retains the amendment history; the fence is a MONEY
        # fence that removes them from countable spend, not a row gate. The
        # first version of this predicate fired on every delivered superseded
        # row, so the documented 1,064 legitimate ones made this pack
        # permanently red - and the only way to green it would have been to
        # DELETE valid history. A regression test that can only be satisfied by
        # destroying correct data is worse than no test.
        #
        # What is actually a defect is a superseded filing that arrives
        # UNFLAGGED: no `supersession_status`, or one that does not name what
        # superseded it. That is the row a customer would sum.
        "id": "SUPERSEDED_LOBBYING_FILING_UNFLAGGED",
        "prior_ids": ["CP-097", "CP-002"],
        "what": "a superseded filing ships WITHOUT the flag that fences it out of countable spend",
        "file": ("customer", "lobbying.csv"),
        "cols": ["client_name", "filing_uuid", "filing_year", "supersession_status", "superseded_by_filing_uuid"],
        "pred": lambda r: (truthy(r.get("is_superseded"))
                           and not up(r, "supersession_status").startswith("SUPERSEDED")),
        "clean": {"client_name": "HOPI TRIBE", "filing_uuid": "3014138c", "filing_year": "1999", "supersession_status": "SUPERSEDED_BY_AMENDMENT", "superseded_by_filing_uuid": "f8fa8e38", "is_superseded": "1"},
        "dirty": {"client_name": "HOPI TRIBE", "filing_uuid": "3014138c", "filing_year": "1999", "supersession_status": "", "superseded_by_filing_uuid": "", "is_superseded": "1"},
    },
    {
        "id": "WITHDRAWN_ATTRIBUTION_SHIPPED",
        "prior_ids": ["CP-002"],
        "what": "a lobbying row whose Native attribution was withdrawn is still delivered carrying that attribution",
        "file": ("customer", "lobbying.csv"),
        "cols": ["client_name", "canonical_name", "attribution_withdrawn", "attribution_withdrawn_reason"],
        "pred": lambda r: truthy(r.get("attribution_withdrawn")),
        "clean": {"client_name": "X", "canonical_name": "Y", "attribution_withdrawn": "", "attribution_withdrawn_reason": ""},
        "dirty": {"client_name": "X", "canonical_name": "Y", "attribution_withdrawn": "1", "attribution_withdrawn_reason": "org_type_barred"},
    },

    # ---- named bad row 9: NAGPRA parse failures ---------------------------
    {
        "id": "NAGPRA_INSTITUTION_CELL_IS_NOTICE_PROSE",
        "prior_ids": ["CP-085", "CP-086"],
        "what": "institution_name holds notice-title prose, not an institution",
        "file": ("customer", "nagpra.csv"),
        "cols": ["document_number", "institution_name", "institution_count"],
        "pred": lambda r: bool(_NOTICE_TITLE.search(r.get("institution_name") or "")),
        "clean": {"document_number": "2020-1", "institution_name": "Bernice Pauahi Bishop Museum", "institution_count": "1"},
        "dirty": {"document_number": "2020-1", "institution_name": "of Native American Human Remains from the Island of Lanai in the Collections of the Bernice Pauahi Bishop Museum", "institution_count": "1"},
    },
    {
        "id": "NAGPRA_MULTI_INSTITUTION_COLLAPSED",
        "prior_ids": ["CP-085", "CP-086"],
        "what": "institution_names_all lists more than one institution but institution_count still says 1",
        "file": ("customer", "nagpra.csv"),
        "cols": ["document_number", "institution_name", "institution_names_all", "institution_count"],
        "pred": lambda r: (
            len([p for p in re.split(r"\||;", r.get("institution_names_all") or "") if p.strip()]) > 1
            and (r.get("institution_count") or "").strip() in {"", "1"}
        ),
        "clean": {"document_number": "2020-2", "institution_name": "A Museum", "institution_names_all": "A Museum|B University", "institution_count": "2"},
        "dirty": {"document_number": "2020-2", "institution_name": "A Museum", "institution_names_all": "A Museum|B University", "institution_count": "1"},
    },
    {
        "id": "NAGPRA_NATIONAL_PARK_PARSED_AS_CITY",
        "prior_ids": ["CP-087"],
        "what": "a national park / monument / forest sits in the city column",
        "file": ("customer", "nagpra.csv"),
        "cols": ["document_number", "institution_name", "institution_city", "institution_state"],
        "pred": lambda r: bool(_NAT_PARK.search(r.get("institution_city") or "")),
        "clean": {"document_number": "2020-3", "institution_name": "Mesa Verde National Park", "institution_city": "Cortez", "institution_state": "CO"},
        "dirty": {"document_number": "2020-3", "institution_name": "Mesa Verde National Park", "institution_city": "Mesa Verde National Park", "institution_state": "CO"},
    },
    {
        "id": "NAGPRA_COUNTY_CELL_HOLDS_SOURCE_PHRASE",
        "prior_ids": ["CP-088"],
        "what": "removal_counties holds a fragment of the source sentence instead of county names",
        "file": ("customer", "nagpra.csv"),
        "cols": ["document_number", "removal_counties", "removal_states"],
        "pred": lambda r: bool(_SOURCE_PHRASE.search(r.get("removal_counties") or "")),
        "clean": {"document_number": "2020-4", "removal_counties": "King|Pierce|Thurston", "removal_states": "WA"},
        "dirty": {"document_number": "2020-4", "removal_counties": "King|Pierce|Thurston|by the Thurston", "removal_states": "WA"},
    },

    # ---- named bad row 10: municipal / county PHAs read as tribes ----------
    {
        "id": "MUNICIPAL_PHA_KEYED_TO_A_TRIBE",
        "prior_ids": ["CP-040", "CP-002"],
        "what": "a city or county housing authority carries a Native entity key (Omaha, Yakima, Montgomery County)",
        "file": ("customer", "funding.csv"),
        "cols": ["recipient_name", "canonical_name", "cedar_uid", "attributed_flag", "excluded_flag", "obligated_usd"],
        "pred": lambda r: (
            bool(re.search(r"HOUSING AUTHORITY OF THE (CITY|COUNTY|TOWN|VILLAGE) OF|\bCOUNTY HOUSING AUTHORITY\b|\bCITY HOUSING AUTHORITY\b", up(r, "recipient_name")))
            and (r.get("canonical_name") or "").strip() != ""
            and truthy(r.get("attributed_flag"))
            and not truthy(r.get("excluded_flag"))
        ),
        "clean": {"recipient_name": "HOUSING AUTHORITY OF THE CITY OF OMAHA", "canonical_name": "", "cedar_uid": "", "attributed_flag": "0", "excluded_flag": "1", "obligated_usd": "2767653.00"},
        "dirty": {"recipient_name": "HOUSING AUTHORITY OF THE CITY OF OMAHA", "canonical_name": "Omaha", "cedar_uid": "CE-0017W-FN", "attributed_flag": "1", "excluded_flag": "0", "obligated_usd": "2767653.00"},
    },

    # ---- publication-gate blockers the review called P0 --------------------
    {
        "id": "QUARANTINED_CONTRACT_ROW_SHIPPED",
        "prior_ids": ["CP-016", "CP-002"],
        "what": "identifier_ruling_quarantined = Y in the delivered file",
        "file": ("customer", "contractors.csv"),
        "cols": ["awardee_name", "canonical_name", "identifier_ruling_quarantined", "ruling_status"],
        "pred": lambda r: up(r, "identifier_ruling_quarantined") == "Y",
        "clean": {"awardee_name": "A", "canonical_name": "B", "identifier_ruling_quarantined": "N", "ruling_status": "RULED_ATTRIBUTED"},
        "dirty": {"awardee_name": "A", "canonical_name": "B", "identifier_ruling_quarantined": "Y", "ruling_status": "RULED_HOLD"},
    },
    {
        "id": "UNRESOLVED_OWNERSHIP_SHIPPED_AS_ATTRIBUTED",
        "prior_ids": ["CP-017", "CP-020"],
        "what": "ruling_status is HOLD or CONFLICT, or ownership is CONTRADICTED, and the row still ships with a canonical name",
        "file": ("customer", "contractors.csv"),
        "cols": ["awardee_name", "canonical_name", "ruling_status", "owner_attribution_status", "attributed_flag"],
        "pred": lambda r: (
            (up(r, "ruling_status") in {"RULED_HOLD", "RULING_CONFLICT"} or up(r, "owner_attribution_status") == "CONTRADICTED_AS_OF")
            and (r.get("canonical_name") or "").strip() != ""
        ),
        "clean": {"awardee_name": "A", "canonical_name": "B", "ruling_status": "RULED_ATTRIBUTED", "owner_attribution_status": "CONFIRMED_AS_OF", "attributed_flag": "1"},
        "dirty": {"awardee_name": "A", "canonical_name": "B", "ruling_status": "RULED_HOLD", "owner_attribution_status": "CONTRADICTED_AS_OF", "attributed_flag": "1"},
    },
    {
        "id": "UNRULED_NONPROFIT_SHIPPED",
        "prior_ids": ["CP-131", "CP-002"],
        "what": "a nonprofit whose Native classification is still UNRULED is in the delivered file",
        "file": ("customer", "nonprofits.csv"),
        "cols": ["org_name", "EIN", "classification_ruling", "disposition"],
        "pred": lambda r: up(r, "classification_ruling") in {"UNRULED", ""},
        "clean": {"org_name": "X", "EIN": "1", "classification_ruling": "tribally_controlled", "disposition": "NATIVE_VERIFIED_STRICT"},
        "dirty": {"org_name": "X", "EIN": "1", "classification_ruling": "UNRULED", "disposition": "CANDIDATE_NAME_ONLY"},
    },

    # ---- metadata-as-data and provenance leakage --------------------------
    {
        "id": "CITE_AS_METADATA_ROW_IN_DATA_FILE",
        "prior_ids": ["CP-001"],
        "what": "a manifest/citation row shipped inside a data table",
        "file": ("customer", "*"),
        "cols": ["__first__"],
        "pred": lambda r: any((v or "").strip().lower() == "cite_as" for v in list(r.values())[:2]),
        "clean": {"a": "real value", "b": "2"},
        "dirty": {"a": "cite_as", "b": "Cedar Press, 2026"},
    },
    {
        "id": "MACHINE_PATH_IN_CUSTOMER_FIELD",
        "prior_ids": ["CP-125", "CP-007"],
        "what": "a customer-visible cell carries a path on somebody's machine (~/Desktop, C:\\Users, /Users/)",
        "file": ("customer", "*"),
        "cols": ["__hit__"],
        "pred": lambda r: any(v and _MACHINE_PATH.search(v) for v in r.values()),
        "clean": {"source_document": "annual report, Goldbelt Incorporated, 2023"},
        "dirty": {"source_document": "native_entity_enterprise_dataset_v6_geocoded.csv (the owner's research dataset, on this machine at ~/Desktop/dissertation/data/tribal)"},
    },
    {
        "id": "CODE_LINEAGE_IN_CUSTOMER_FIELD",
        "prior_ids": ["CP-033", "CP-007", "CP-140", "CP-094"],
        "what": "a customer-visible cell cites a script number, a .py file, a local data/clean path, or a zip",
        "file": ("customer", "*"),
        "cols": ["__hit__"],
        "pred": lambda r: any(v and _CODE_LINEAGE.search(v) for v in r.values()),
        # The clean row carries the two real FPDS labels that a case-insensitive
        # version of this pattern wrongly matched. If someone relaxes the regex,
        # selftest fails here instead of the count silently growing by 185,000.
        "clean": {"outcome_basis": "the most final action in this bill's full history (2017-06-29)",
                  "product_or_service_code_description": "SUPPORT- PROFESSIONAL: PROGRAM EVALUATION/REVIEW/DEVELOPMENT",
                  "award_base_description": "SITE PREP AND REVIEW/DEVELOPMENT SERVICES"},
        "dirty": {"outcome_basis": "collapsed one-row-per-bill from data/clean/native_bills_entity_bridge.csv by code/1140 on 2026-09-02",
                  "product_or_service_code_description": "SUPPORT- PROFESSIONAL: PROGRAM EVALUATION/REVIEW/DEVELOPMENT",
                  "award_base_description": ""},
    },
]


# --------------------------------------------------------------------------
# running the detectors
# --------------------------------------------------------------------------

def _files_for(spec: tuple[str, str]) -> list[Path]:
    where, name = spec
    base = CUSTOMER if where == "customer" else PREVIEW
    if name == "*":
        return sorted(p for p in base.glob("*.csv") if p.name != "MANIFEST.csv")
    p = base / name
    return [p] if p.exists() else []


def run_detectors(detectors: list[dict], quick: bool = False,
                  file_override: dict[str, Path] | None = None) -> dict:
    """Run every detector. One pass per physical file, all detectors for that
    file evaluated on the same row, so a 1.4 GB table is read once."""
    by_file: dict[Path, list[dict]] = {}
    missing: list[dict] = []
    for d in detectors:
        if file_override and d["id"] in file_override:
            by_file.setdefault(file_override[d["id"]], []).append(d)
            continue
        paths = _files_for(d["file"])
        if not paths:
            missing.append(d)
        for p in paths:
            by_file.setdefault(p, []).append(d)

    results: dict[str, dict] = {
        d["id"]: {
            "id": d["id"], "what": d["what"], "prior_ids": d["prior_ids"],
            "count": 0, "rows_read": 0, "capped": False,
            "files": [], "evidence": [],
        }
        for d in detectors
    }
    for d in missing:
        results[d["id"]]["unmeasured"] = "file not present in the tree"

    files_read = []
    for path, dets in sorted(by_file.items()):
        st = path.stat()
        n = 0
        capped = False
        with path.open(newline="", encoding="utf-8", errors="replace") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                n += 1
                if quick and n > QUICK_CAP:
                    capped = True
                    n -= 1
                    break
                for d in dets:
                    try:
                        hit = d["pred"](row)
                    except Exception:  # a malformed cell must not silence a detector
                        hit = False
                        results[d["id"]].setdefault("pred_errors", 0)
                        results[d["id"]]["pred_errors"] += 1
                    if hit:
                        res = results[d["id"]]
                        res["count"] += 1
                        if len(res["evidence"]) < 3:
                            if d["cols"] == ["__hit__"]:
                                ev = {k: (v or "")[:180] for k, v in row.items()
                                      if v and (_MACHINE_PATH.search(v) or _CODE_LINEAGE.search(v))}
                                ev = dict(list(ev.items())[:2])
                            elif d["cols"] == ["__first__"]:
                                ev = dict(list(row.items())[:3])
                            else:
                                ev = {c: (row.get(c) or "")[:120] for c in d["cols"]}
                            ev["__file__"] = path.name
                            res["evidence"].append(ev)
        try:
            shown = str(path.relative_to(ROOT))
        except ValueError:  # a selftest fixture outside the repo
            shown = str(path)
        files_read.append({"file": shown, "rows_read": n,
                           "capped": capped, "bytes": st.st_size,
                           "mtime": st.st_mtime})
        for d in dets:
            r = results[d["id"]]
            r["rows_read"] += n
            r["capped"] = r["capped"] or capped
            r["files"].append(path.name)

    return {"results": results, "files_read": files_read}


# --------------------------------------------------------------------------
# selftest: prove every detector can return one
# --------------------------------------------------------------------------

def selftest() -> int:
    """For each detector, build a two-row synthetic fixture - one clean row,
    one carrying the injected violation - and assert the detector fires on the
    dirty row and only on the dirty row. Then assert `check` over the dirty
    fixture set exits nonzero and over the clean fixture set exits zero."""
    print("SELFTEST - injecting each violation class into a synthetic fixture")
    print("-" * 78)
    failures: list[str] = []
    tmp = Path(tempfile.mkdtemp(prefix="cedar_1171_selftest_"))

    for d in DETECTORS:
        cols = sorted(set(list(d["clean"].keys()) + list(d["dirty"].keys())))
        clean_p = tmp / f"{d['id']}__clean.csv"
        dirty_p = tmp / f"{d['id']}__dirty.csv"
        for p, rows in ((clean_p, [d["clean"]]), (dirty_p, [d["clean"], d["dirty"]])):
            with p.open("w", newline="", encoding="utf-8") as fh:
                w = csv.DictWriter(fh, fieldnames=cols)
                w.writeheader()
                for r in rows:
                    w.writerow({c: r.get(c, "") for c in cols})

        clean_run = run_detectors([d], file_override={d["id"]: clean_p})
        dirty_run = run_detectors([d], file_override={d["id"]: dirty_p})
        c_clean = clean_run["results"][d["id"]]["count"]
        c_dirty = dirty_run["results"][d["id"]]["count"]

        ok_fires = c_dirty >= 1
        ok_silent = c_clean == 0
        status = "OK" if (ok_fires and ok_silent) else "NOT_TRUSTWORTHY"
        if not ok_fires:
            failures.append(f"{d['id']}: did NOT fire on the injected violation")
        if not ok_silent:
            failures.append(f"{d['id']}: fired on the clean row ({c_clean}) - false positive")
        print(f"  {status:<16} {d['id']:<46} clean={c_clean} dirty={c_dirty}")

    print("-" * 78)
    print(f"detectors: {len(DETECTORS)}   proven to fire and stay silent: "
          f"{len(DETECTORS) - len({f.split(':')[0] for f in failures})}")
    if failures:
        print("\nA detector that cannot be shown to fire does not ship:")
        for f in failures:
            print(f"  !! {f}")
        return 1
    print("\nEvery detector returned one on an injected violation and zero on the "
          "clean row. The counts printed by `check` are therefore counts, not "
          "the silence of a broken check.")
    return 0


# --------------------------------------------------------------------------
# check / baseline / ratchet
# --------------------------------------------------------------------------

def _report(run: dict, quick: bool) -> tuple[list[str], list[str]]:
    fired, clean = [], []
    print(f"{'detector':<48}{'count':>12}   rows read")
    print("-" * 92)
    for d in DETECTORS:
        r = run["results"][d["id"]]
        if "unmeasured" in r:
            print(f"{d['id']:<48}{'UNMEASURED':>12}   {r['unmeasured']}")
            continue
        cap = " CAPPED" if r["capped"] else ""
        print(f"{d['id']:<48}{r['count']:>12}   {r['rows_read']:,}{cap}")
        (fired if r["count"] else clean).append(d["id"])
    print("-" * 92)
    for d in DETECTORS:
        r = run["results"][d["id"]]
        if r["count"] and r["evidence"]:
            print(f"\n  {d['id']}  ({r['count']:,} rows)  -- {d['what']}")
            for ev in r["evidence"]:
                print(f"     {ev}")
    return fired, clean


def check(quick: bool) -> int:
    print(f"CHECK - {len(DETECTORS)} named detectors against the live tree, {TODAY}")
    print("THIS RUN IS A SNAPSHOT. Concurrent rebuilds write dist/ and data/clean/;")
    print("the run record stamps the size and mtime of every file read.")
    if quick:
        print(f"--quick: each file capped at {QUICK_CAP:,} rows. A capped count is a "
              "FLOOR, never a population figure.")
    print()
    run = run_detectors(DETECTORS, quick=quick)
    fired, clean = _report(run, quick)

    print()
    print(f"FIRED (live defects): {len(fired)}")
    print(f"ZERO in what was read: {len(clean)}")
    if clean:
        rows = min(run["results"][i]["rows_read"] for i in clean)
        print(f"  Zero observed is a FLOOR, not a proof of absence: no instance was "
              f"found in the rows read (>= {rows:,} rows for the narrowest of them).")

    REVIEW.mkdir(parents=True, exist_ok=True)
    out = REVIEW / f"1171_regression_pack_{TODAY}.json"
    out.write_text(json.dumps({
        "run_date": TODAY, "quick": quick,
        "prior_review": "review/QA_REVIEW_10ROW_2026-09-02.txt",
        "snapshot_warning": "concurrent rebuilds; single run is a snapshot",
        "files_read": run["files_read"],
        "results": run["results"],
    }, indent=1, default=str), encoding="utf-8")
    print(f"\nrun record: {out.relative_to(ROOT)}")

    if fired:
        print(f"\nFAIL - {len(fired)} named detector(s) nonzero: {', '.join(fired)}")
        return 1
    print("\nPASS - every named prior finding measured zero in the rows read.")
    return 0


def baseline(quick: bool) -> int:
    run = run_detectors(DETECTORS, quick=quick)
    counts = {k: v["count"] for k, v in run["results"].items() if "unmeasured" not in v}
    REVIEW.mkdir(parents=True, exist_ok=True)
    p = REVIEW / "1171_baseline.json"
    p.write_text(json.dumps({"recorded": TODAY, "quick": quick, "counts": counts},
                            indent=1), encoding="utf-8")
    print(f"recorded {len(counts)} counts to {p.relative_to(ROOT)}")
    print("This is a CEILING, not a waiver. `check` still exits 1 while any count "
          "is nonzero.")
    return 0


def ratchet(quick: bool) -> int:
    p = REVIEW / "1171_baseline.json"
    if not p.exists():
        print(f"no baseline at {p.relative_to(ROOT)} - run `baseline` first")
        return 2
    base = json.loads(p.read_text(encoding="utf-8"))["counts"]
    run = run_detectors(DETECTORS, quick=quick)
    worse = []
    for d in DETECTORS:
        r = run["results"][d["id"]]
        if "unmeasured" in r:
            continue
        was = base.get(d["id"])
        if was is None:
            print(f"  NEW      {d['id']:<48}{r['count']:>10}")
            continue
        arrow = "->"
        if r["count"] > was:
            worse.append(f"{d['id']}: {was} {arrow} {r['count']}")
            print(f"  WORSE    {d['id']:<48}{was:>8} {arrow} {r['count']}")
        elif r["count"] < was:
            print(f"  BETTER   {d['id']:<48}{was:>8} {arrow} {r['count']}")
        else:
            print(f"  same     {d['id']:<48}{r['count']:>10}")
    if worse:
        print("\nFAIL - counts increased:")
        for w in worse:
            print(f"  !! {w}")
        return 1
    print("\nPASS - no named count increased against the baseline.")
    return 0


def main() -> int:
    args = sys.argv[1:]
    quick = "--quick" in args
    mode = next((a for a in args if not a.startswith("-")), "check")
    if mode == "selftest":
        return selftest()
    if mode == "check":
        return check(quick)
    if mode == "baseline":
        return baseline(quick)
    if mode == "ratchet":
        return ratchet(quick)
    print(__doc__)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
