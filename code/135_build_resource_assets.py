"""Cedar Press 130 - the ASSET layer of the natural resource ledger.

`data/clean/resource_assets.csv` shipped with headers and ZERO rows. This
script fills it.

WHAT AN ASSET IS HERE
    A lease, tract, well, mine, deposit, allotment, unit or communitization
    agreement, timber/carbon project, water right or right-of-way that a Native
    entity owns, holds an interest in, or receives revenue from.

FOUR RULES THIS SCRIPT IS BUILT AROUND
------------------------------------------------------------------------
1.  AN ASSET IS NOT REVENUE, AND NEITHER IS DERIVED FROM THE OTHER.
    No asset row is created because a revenue row exists, and no revenue row
    is created here at all. Where an asset can be tied to a published revenue
    event the tie is written to review/ as a PROPOSAL with its own
    `link_basis` column - never merged into `resource_revenue.csv`.

2.  OWNERSHIP AND BENEFICIAL INTEREST ARE DIFFERENT FACTS, IN DIFFERENT
    COLUMNS. `legal_title_holder` is who holds title; `beneficial_interest_
    class` is who the property is held FOR. On the Osage Mineral Estate those
    are different parties and the Osage Nation's own auditor says so. An
    allotment held in trust for individual Indians is NOT tribally owned, and
    an ANCSA corporation's fee estate is NOT trust land. Collapsing any of
    these into one "owner" column is the false attribution this project
    refuses.

3.  NOTHING IS ESTIMATED. No acreage is summed, no rate is inverted, no
    production or value is modelled. Every number in an asset row is a digit
    string that appears verbatim in the cited document, and the gate below
    checks that on every run.

4.  COVERAGE IS FOUR-VALUED, NEVER BLANK. PUBLISHES / WITHHOLDS / NOT_FOUND /
    NOT_CHECKED. A source that is forbidden by law to publish and a source
    nobody looked at are opposite findings that look identical in a blank cell.

THE EVIDENCE GATE (the load-bearing part, borrowed from script 84)
------------------------------------------------------------------------
Every declared fact names a local document and an ANCHOR regex. The script:
    a. whitespace-normalises the document and splits it into sentences;
    b. requires the anchor to match EXACTLY ONE distinct sentence - zero is a
       missing fact, more than one is an ambiguous one, and both REFUSE;
    c. requires every declared number (`must_contain`) to appear literally in
       that sentence, so a figure can never drift away from its own quote;
    d. stores the matched sentence itself as `evidence_quote`, so the quote is
       verbatim BY CONSTRUCTION rather than by transcription.
A refused fact is reported and no row is written for it.

APPEND, NEVER REBUILD
    Reads the published file, deletes only rows whose id starts with a prefix
    this script owns (`RAS-`), carries everything else through untouched.
    Party links go through the same test on `object_id`.

ENTITY RESOLUTION
    `resolve_entity`, imported from `code/33_apply_party_rulings.py`. No second
    name matcher exists here. Every entity used resolves on `exact` or `core`;
    the defective containment tier is never reached, and a fact whose owner
    does not resolve is refused rather than guessed.

Usage:  py -3 code/130_build_resource_assets.py
"""

from __future__ import annotations

import csv
import glob
import importlib.util
import os
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CLEAN = ROOT / "data" / "clean"
RAW = ROOT / "data" / "raw" / "resources"
REVIEW = ROOT / "review"
ANCSA_TXT = ROOT / "code" / "ancsa_portal" / "txt"

TODAY = "2026-08-12"
ID_PREFIX = "RAS-"

# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------
# The first 29 fields are script 83's ASSET_FIELDS, unchanged and in order, so
# the file stays readable by anything already written against it. The rest are
# appended - safe, because the file had zero rows.
#
# niogems_* stay EMPTY BY CONSTRUCTION. BIA's NIOGEMS holds the lease, tract,
# agreement and well identifiers for Indian minerals; it is internal to BIA and
# Cedar Press has no access. The columns exist so that if access is ever
# granted the join is a merge and not a rebuild. NIOGEMS is a partnership
# target, never a cited source.

ASSET_FIELDS = [
    "resource_asset_id", "asset_type", "asset_name",
    "source_system", "source_asset_id",
    "niogems_lease_id", "niogems_tract_id", "niogems_agreement_id",
    "niogems_well_id",
    "resource_type", "commodity",
    "state", "county", "fips_code", "latitude", "longitude",
    "reservation_name", "land_status", "land_status_source_url",
    "operator_name", "operator_entity_id",
    "status", "first_production_date", "spud_date",
    "geometry_basis", "confidence",
    "source_url", "fetched_date", "built_date",
    # --- added by script 130 ---
    "legal_title_holder",
    "beneficial_interest_class",
    "ownership_basis",
    "area_acres", "area_unit", "area_basis", "as_of_date",
    "asset_count_in_source",
    "evidence_document", "evidence_document_type", "evidence_quote",
    "quote_verified",
    "revenue_coverage_state", "production_coverage_state",
    "coverage_note",
]

PARTY_FIELDS = [
    "party_link_id", "object_type", "object_id",
    "entity_id", "entity_name", "entity_is_native",
    "party_role", "relationship", "interest_share_pct",
    "basis", "confidence", "source_url", "fetched_date", "built_date",
]

LINK_FIELDS = [
    "proposal_id", "resource_asset_id", "asset_name",
    "resource_revenue_event_id", "revenue_source_system",
    "link_type", "link_basis",
    "proposed_payer_entity_name", "proposed_payer_entity_id", "payer_basis",
    "evidence_quote", "confidence", "source_url", "built_date", "status",
]

COVERAGE_FIELDS = [
    "source_system", "publisher", "attribute", "coverage_state",
    "what_was_swept", "evidence", "source_url", "checked_date",
]

COVERAGE_STATES = {"PUBLISHES", "WITHHOLDS", "NOT_FOUND", "NOT_CHECKED"}

# Controlled vocabularies. `not_stated` is always available and is never a
# synonym for "no".
LAND_STATUS = {
    "tribal_trust",            # US holds title in trust for a tribe
    "individual_indian_trust", # US holds title in trust for allottees
    "restricted_fee",
    "ancsa_fee",               # ANCSA corporation fee ownership - NOT trust
    "mixed_tribal_and_allottee",
    "not_stated",
}
BENEFICIAL = {
    "tribal_government",
    "individual_indian_allottee",
    "osage_headright_holder",
    "anc_shareholder",
    "mixed_tribal_and_allottee",
    "not_stated",
}

# ---------------------------------------------------------------------------
# IO helpers
# ---------------------------------------------------------------------------


def read_csv(p):
    p = Path(p)
    if not p.exists():
        return []
    with p.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def write_csv(p, rows, fields):
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fields})


def load_resolver():
    """THE one resolver. Imported, never re-implemented (standing rule 8)."""
    spec = importlib.util.spec_from_file_location(
        "m33", str(ROOT / "code" / "33_apply_party_rulings.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m.resolve_entity


_WS = re.compile(r"\s+")


def flatten(text):
    return _WS.sub(" ", text).strip()


def sentences(text):
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", flatten(text))]


_DOC_CACHE = {}


def doc_text(path):
    path = str(path)
    if path not in _DOC_CACHE:
        with open(path, encoding="utf-8", errors="replace") as fh:
            _DOC_CACHE[path] = fh.read()
    return _DOC_CACHE[path]


# ---------------------------------------------------------------------------
# ANCSA portal document lookup
# ---------------------------------------------------------------------------
# The portal URL is the citable source. It is read from the retrieval index
# another agent built, joined on the local filename, so a source_url is never
# constructed by hand.

def ancsa_index():
    idx = {}
    for r in read_csv(CLEAN / "ancsa_filings_index.csv"):
        lf = r.get("local_file") or ""
        if lf:
            idx[lf] = (r.get("portal_url", ""), r.get("retrieved_date", ""))
    return idx


def find_ancsa_doc(pattern):
    """Resolve a filename glob to the candidate documents, in order.

    A glob may legitimately match more than one file - a report split into two
    portal uploads, or a report filed alongside that year's meeting minutes.
    So the glob narrows and the ANCHOR decides: `resolve_fact` requires exactly
    one CANDIDATE DOCUMENT to contain exactly one matching sentence. Two
    documents both matching is still a refusal, because it means the anchor is
    not identifying a single published statement.
    """
    hits = sorted(glob.glob(str(ANCSA_TXT / pattern)))
    if not hits:
        return [], "doc_glob_matched_no_files"
    return hits, ""


# ---------------------------------------------------------------------------
# THE DECLARED FACTS
# ---------------------------------------------------------------------------
# Each entry names an asset, a document, an anchor, and the numbers the
# sentence must contain. Nothing here is transcribed prose - the quote that
# ends up in the CSV is lifted from the document by the gate.

A = "ANCSA_regional_corporation_annual_report"

# --- 1. ANCSA land and mineral estates -------------------------------------
# The estate itself is the asset: the tract of surface and/or subsurface that
# ANCSA conveyed and that everything else sits on. Ownership is FEE, held by a
# corporation, for shareholders. It is emphatically NOT trust land and NOT a
# tribal government holding, and `land_status = ancsa_fee` says so.
#
# One row per (corporation, estate type), carrying the figure from the most
# recent report that states it. The acreage is NOT a time series here and the
# yearly restatements are not stacked - that would turn one asset into eleven.

ANCSA_ESTATES = [
    # (owner, estate asset_type, asset_name, doc glob, anchor, acres, as_of, note)
    ("Ahtna, Inc.", "land_estate", "Ahtna ANCSA land estate",
     "2025__Ahtna_Inc.*.txt",
     r"the Company had received conveyance of approximately 1,598,246 acres",
     "1,598,246", "2025-12-31", ""),

    ("The Aleut Corporation", "surface_estate", "Aleut Corporation ANCSA surface estate",
     "2025__Aleut_Corporation*.txt",
     r"the Corporation also received the surface estate of approximately 66,000 acres",
     "66,000", "2025-03-31", ""),
    ("The Aleut Corporation", "subsurface_estate", "Aleut Corporation ANCSA subsurface estate",
     "2025__Aleut_Corporation*.txt",
     r"approximately 1,572,000 acres of subsurface estate",
     "1,572,000", "2025-03-31", ""),
    ("The Aleut Corporation", "land_conveyance", "Adak Island conveyance (Aleut Corporation)",
     "2025__Aleut_Corporation*.txt",
     r"received conveyance to approximately 46,000 acres on Adak Island",
     "46,000", "2004-03-17",
     "Conveyed in exchange for land selection rights, not as a direct ANCSA "
     "selection; the report says so in the quoted sentence."),

    ("Arctic Slope Regional Corporation", "combined_fee_estate",
     "ASRC ANCSA surface and subsurface estate",
     "2025__Arctic_Slope_Regional_Corporation*.txt",
     r"patent or interim conveyance of title to the surface and subsurface estate of approximately 5,000,000 acres",
     "5,000,000", "2025-12-31",
     "Surface and subsurface are reported as ONE figure by the source and are "
     "not split here; splitting them would invent a decomposition."),

    ("Bering Straits Native Corporation", "land_estate",
     "Bering Straits ANCSA land entitlement (regional selections)",
     "2026__Bering_Straits_Native_Corporation*.txt",
     r"had received interim conveyance or patent to 123,416 acres as of March 31, 2026",
     "123,416", "2026-03-31", ""),
    ("Bering Straits Native Corporation", "subsurface_estate",
     "Bering Straits ANCSA subsurface estate beneath village lands",
     "2026__Bering_Straits_Native_Corporation*.txt",
     r"interim conveyance or patent to 2,109,828 acres of subsurface estate",
     "2,109,828", "2026-03-31",
     "Subsurface beneath land conveyed to VILLAGE corporations. The surface of "
     "those same acres belongs to the village corporations, not to BSNC."),

    ("Bristol Bay Native Corporation", "subsurface_estate",
     "BBNC ANCSA estate (primarily subsurface)",
     "2025__Bristol_Bay_Native_Corporation*.txt",
     r"conveyed title to 3,069,391 acres of primarily subsurface estate lands",
     "3,069,391", "2025-12-31",
     "The source says 'primarily subsurface'; the surface/subsurface split is "
     "not stated and is not derived."),

    ("Calista Corporation", "subsurface_estate", "Calista ANCSA subsurface estate",
     "2025__Calista_Corporation*.txt",
     r"received interim conveyances and patents to 6,421,632 acres of subsurface rights",
     "6,421,632", "2025-12-31", ""),

    ("Chugach Alaska Corporation", "combined_fee_estate",
     "Chugach ANCSA full fee estate",
     "2025__Chugach_Alaska_Corporation*.txt",
     r"received conveyance of 377,421 acres of full fee estate",
     "377,421", "2025-12-31", ""),
    ("Chugach Alaska Corporation", "subsurface_estate",
     "Chugach ANCSA subsurface estate",
     "2025__Chugach_Alaska_Corporation*.txt",
     r"542,020 acres of subsurface estate",
     "542,020", "2025-12-31", ""),

    ("Doyon, Limited", "combined_fee_estate", "Doyon ANCSA fee land",
     "2025__Doyon_Limited*.txt",
     r"approximately 8\.2 million acres of fee land",
     "8.2 million", "2025-09-30", ""),
    ("Doyon, Limited", "subsurface_estate",
     "Doyon ANCSA subsurface beneath village lands",
     "2025__Doyon_Limited*.txt",
     r"3\.6 million acres of the subsurface beneath village lands",
     "3.6 million", "2025-09-30", ""),

    ("Koniag, Inc.", "surface_estate", "Koniag ANCSA surface estate",
     "2025__Koniag_Inc.__2025_Koniag_Inc._Annual_Report_8-27-2025*.txt",
     r"interim conveyance or patent to approximately 143,000 acres of surface estate",
     "143,000", "2025-03-31", ""),
    ("Koniag, Inc.", "subsurface_estate", "Koniag ANCSA subsurface estate",
     "2025__Koniag_Inc.__2025_Koniag_Inc._Annual_Report_8-27-2025*.txt",
     r"interim conveyance or patent to approximately 143,000 acres of surface estate and approximately 900,000 acres of subsurface estate",
     "900,000", "2025-03-31", ""),

    ("NANA Regional Corporation", "surface_estate", "NANA ANCSA surface estate",
     "2025__NANA_Regional_Corporation_Inc.*.txt",
     r"interim conveyance or patent to 1,984,944 acres of surface estate",
     "1,984,944", "2025-09-30", ""),
    ("NANA Regional Corporation", "subsurface_estate", "NANA ANCSA subsurface estate",
     "2025__NANA_Regional_Corporation_Inc.*.txt",
     r"2,190,547 acres of subsurface estate",
     "2,190,547", "2025-09-30", ""),

    ("Sealaska Corporation", "combined_fee_estate",
     "Sealaska ANCSA estate within the Tongass National Forest",
     "2025__Sealaska_Corporation*.txt",
     r"conveyance of approximately 362,000 acres of land within the exterior boundaries of the Tongass",
     "362,000", "2025-12-31", ""),

    ("Cook Inlet Region, Inc.", "surface_estate", "CIRI ANCSA surface estate",
     "2024__Cook_Inlet_Region_Inc.*.txt",
     r"529,500 ACRES of surface estate land",
     "529,500", "2024-12-31",
     "Read from a report INFOGRAPHIC, not an audited note. The 2025 report "
     "prints the same two figures with the labels interleaved in the text "
     "layer ('529,500 Acres 1.6M Acres ... of surface estate land of "
     "subsurface estate'), which is why the 2024 rendering is cited instead. "
     "Confidence B."),
    ("Cook Inlet Region, Inc.", "subsurface_estate", "CIRI ANCSA subsurface estate",
     "2024__Cook_Inlet_Region_Inc.*.txt",
     r"1\.6M ACRES of subsurface estate",
     "1.6M", "2024-12-31",
     "Same infographic caveat as the CIRI surface estate row. Confidence B."),
]

# --- 2. Named ANCSA projects: mines, deposits, oil fields, carbon ----------
# `operator` is a COUNTERPARTY, never an owner. Teck operates Red Dog; NANA
# owns the ground. The two facts live in different party rows on purpose.

ANCSA_PROJECTS = [
    dict(owner="NANA Regional Corporation", operator="Teck Alaska Incorporated",
         asset_type="mine", asset_name="Red Dog Mine",
         resource_type="hardrock", commodity="Zinc and lead",
         status="producing",
         doc="2018__NANA_Regional_Corporation_Inc.__2018_NANA_Annual_Report*.txt",
         anchor=r"a 36-year partnership between NANA and Teck Alaska, the operator",
         must=[], note=""),
    dict(owner="NANA Regional Corporation", operator="Teck Alaska Incorporated",
         asset_type="deposit", asset_name="Aqqaluk deposit (Red Dog Mine)",
         resource_type="hardrock", commodity="Zinc and lead",
         status="producing",
         doc="2025__NANA_Regional_Corporation_Inc.*.txt",
         anchor=r"continued production from the Aqqaluk ore body at Red Dog Mine",
         must=[], note="An ore body WITHIN Red Dog Mine, not a separate mine. "
                       "Never sum with the Red Dog Mine row."),
    dict(owner="NANA Regional Corporation", operator="Teck Alaska Incorporated",
         asset_type="deposit", asset_name="Qanaiyaq deposit (Red Dog Mine)",
         resource_type="hardrock", commodity="Zinc and lead",
         status="producing",
         doc="2025__NANA_Regional_Corporation_Inc.*.txt",
         anchor=r"continued production from the Qanaiyaq deposit at Red Dog Mine",
         must=[], note="An ore body WITHIN Red Dog Mine. The same deposit is "
                       "spelled 'Qaniayaq' in NANA reports through FY2022 and "
                       "'Qanaiyaq' from FY2023; one deposit, two spellings."),
    dict(owner="NANA Regional Corporation", operator="",
         asset_type="deposit", asset_name="Arctic deposit (Upper Kobuk Mineral Projects)",
         resource_type="hardrock", commodity="Copper, zinc, lead",
         status="exploration",
         doc="2021__NANA_Regional_Corporation_Inc.*.txt",
         anchor=r"the Arctic polymetallic deposit and the Bornite copper deposit",
         must=[], note="Operator not asserted: NANA reports name Trilogy Metals "
                       "and Ambler Metals as spending on exploration, which is "
                       "not the same fact as operatorship of the deposit."),
    dict(owner="NANA Regional Corporation", operator="",
         asset_type="deposit", asset_name="Bornite deposit (Upper Kobuk Mineral Projects)",
         resource_type="hardrock", commodity="Copper and cobalt",
         status="exploration",
         doc="2019__NANA_Regional_Corporation_Inc.*.txt",
         anchor=r"Bornite . a high-grade copper and cobalt deposit",
         must=[], note="Operator not asserted; see the Arctic deposit row."),
    dict(owner="NANA Regional Corporation", operator="",
         asset_type="prospect", asset_name="Fairhaven Gold Project",
         resource_type="hardrock", commodity="Gold",
         status="exploration",
         doc="2019__NANA_Regional_Corporation_Inc.*.txt",
         anchor=r"mineral exploration of the Fairhaven Gold Project, a prospect in the NANA region near Candle",
         must=[], note=""),
    dict(owner="Calista Corporation", operator="Donlin Gold LLC",
         asset_type="mine", asset_name="Donlin Gold Project",
         resource_type="hardrock", commodity="Gold",
         status="permitting_and_development",
         doc="2016__Calista_Corporation*.txt",
         anchor=r"Calista owns the subsurface estate at the Donlin Gold Project",
         must=[], note="Calista owns the SUBSURFACE. The surface at Donlin is "
                       "held by The Kuskokwim Corporation, which this row does "
                       "not assert because the cited sentence does not."),
    dict(owner="Arctic Slope Regional Corporation", operator="",
         asset_type="oil_field", asset_name="Alpine Oil Field (ASRC subsurface interest)",
         resource_type="oil_and_gas", commodity="Oil",
         status="producing",
         doc="2025__Arctic_Slope_Regional_Corporation*.txt",
         anchor=r"subsurface mineral rights granted through ANCSA, such as its interest in the Alpine Oil Field",
         must=[], note="ASRC states an INTEREST in the field, not ownership of "
                       "the field or of its operations. Operator not stated in "
                       "the cited sentence and not supplied from elsewhere."),
    dict(owner="Sealaska Corporation", operator="",
         asset_type="forest_carbon_project",
         asset_name="Sealaska forest carbon project (California cap-and-trade)",
         resource_type="timber", commodity="Forest carbon",
         status="active", acres="165,000",
         doc="2018__Sealaska_Corporation*.txt",
         anchor=r"we have preserved 165,000 acres of forest",
         must=["165,000"], note=""),
    dict(owner="Chugach Alaska Corporation", operator="",
         asset_type="forest_carbon_project",
         asset_name="Chugach forest carbon offset project",
         resource_type="timber", commodity="Forest carbon",
         status="active", acres="115,000",
         doc="2016__Chugach_Alaska_Corporation*.txt",
         anchor=r"Chugach agreed to begin a forest carbon offset project on 115,000 acres",
         must=["115,000"], note=""),
]

# --- 3. Lower-48: the two documents that are actually LEASES ---------------
# These are the only rows in this build backed by a lease instrument or by a
# lessee's own filing about one, and they are the only ones on tribal TRUST
# land. Everything above is ANCSA fee.

LEASE_DOCS = ROOT / "data" / "raw" / "resources" / "_leases"

# ---------------------------------------------------------------------------


def gate(doc_path, anchor, must):
    """Return (quote, error). Refuses on 0 or >1 anchor matches."""
    try:
        txt = doc_text(doc_path)
    except OSError as e:
        return None, f"document_unreadable:{e}"
    rx = re.compile(anchor)
    hits = []
    for s in sentences(txt):
        if rx.search(s) and s not in hits:
            hits.append(s)
    if not hits:
        return None, "anchor_matched_no_sentence"
    if len(hits) > 1:
        return None, f"anchor_ambiguous:{len(hits)}_sentences"
    q = hits[0]
    for m in must:
        if m and m not in q:
            return None, f"declared_number_absent_from_quote:{m}"
    return q, ""


def resolve_fact(glob_pattern, anchor, must):
    """(doc_path, quote, error) - exactly one document, exactly one sentence."""
    cands, err = find_ancsa_doc(glob_pattern)
    if err:
        return None, None, err
    wins, last = [], ""
    for p in cands:
        q, e = gate(p, anchor, must)
        if q:
            wins.append((p, q))
        else:
            last = e
    if not wins:
        return None, None, last or "anchor_matched_no_sentence"
    if len(wins) > 1:
        return None, None, f"anchor_matched_{len(wins)}_documents"
    return wins[0][0], wins[0][1], ""


def main():
    print("=== Cedar Press 130: resource ASSET layer ===\n")

    resolve_entity = load_resolver()
    spine = read_csv(ROOT / "data" / "spine" / "cedar_entity_spine.csv")
    print(f"  spine entities            : {len(spine):,}")
    idx = ancsa_index()

    assets, parties, refused = [], [], []
    ent_cache = {}

    def ent(name):
        if name not in ent_cache:
            ent_cache[name] = resolve_entity(name, spine)
        return ent_cache[name]

    def add_party(asset_id, name, role, relationship, basis, url, fetched,
                  is_native, conf="A"):
        eid, ename, how = ("", "", "")
        if is_native:
            eid, ename, how = ent(name)
            if not eid:
                refused.append((f"party:{asset_id}:{name}",
                                f"owner_unresolved:{how}"))
                return False
            if how not in ("exact", "core", "alias"):
                refused.append((f"party:{asset_id}:{name}",
                                f"resolver_tier_not_accepted:{how}"))
                return False
        parties.append({
            "party_link_id": f"PL-{asset_id}-{role.upper()}",
            "object_type": "asset", "object_id": asset_id,
            "entity_id": eid, "entity_name": ename or name,
            "entity_is_native": "1" if is_native else "0",
            "party_role": role, "relationship": relationship,
            "interest_share_pct": "",
            "basis": basis + (f"; resolve_entity/{how}" if is_native else ""),
            "confidence": conf, "source_url": url,
            "fetched_date": fetched, "built_date": TODAY,
        })
        return True

    n = [0]

    def new_id(kind):
        n[0] += 1
        return f"{ID_PREFIX}{kind}-{n[0]:05d}"

    # -- 1. ANCSA estates ---------------------------------------------------
    print("\n[1] ANCSA regional corporation land and mineral estates")
    for owner, atype, aname, dglob, anchor, acres, asof, note in ANCSA_ESTATES:
        path, quote, err = resolve_fact(dglob, anchor, [acres] if acres else [])
        if not quote:
            refused.append((aname, err)); continue
        base = os.path.basename(path)[:-4]          # drop .txt
        url, fetched = idx.get(base, ("", "2026-08-05"))
        aid = new_id("ANCSA")
        conf = "B" if "infographic" in note.lower() else "A"
        assets.append({
            "resource_asset_id": aid, "asset_type": atype, "asset_name": aname,
            "source_system": A, "source_asset_id": base,
            "resource_type": "land_and_minerals", "commodity": "",
            "state": "AK", "land_status": "ancsa_fee",
            "land_status_source_url": url,
            "status": "held", "geometry_basis": "none_published",
            "confidence": conf, "source_url": url, "fetched_date": fetched,
            "built_date": TODAY,
            "legal_title_holder": (
                f"{owner} (fee, by ANCSA patent or interim conveyance)"),
            "beneficial_interest_class": "anc_shareholder",
            "ownership_basis": (
                "ANCSA conveyance stated in the corporation's own annual "
                "report. This is FEE ownership by a corporation for its "
                "shareholders. It is NOT tribal trust land, NOT held by the "
                "United States, and NOT owned by a tribal government."),
            "area_acres": acres, "area_unit": "acres",
            "area_basis": "stated in the quoted sentence; never summed or derived",
            "as_of_date": asof,
            "evidence_document": base,
            "evidence_document_type": "ANCSA annual report",
            "evidence_quote": quote, "quote_verified": "yes",
            "revenue_coverage_state": "NOT_FOUND",
            "production_coverage_state": "NOT_FOUND",
            "coverage_note": (
                "No per-estate revenue or production figure is published. The "
                "corporation reports natural resource revenue at the "
                "consolidated level only. " + note).strip(),
        })
        add_party(aid, owner, "owner", "parent_native_entity",
                  "the corporation's own annual report states the conveyance to itself",
                  url, fetched, True, conf)
    print(f"    estate rows built       : "
          f"{sum(1 for a in assets if a['source_system'] == A)}")

    # -- 2. ANCSA named projects -------------------------------------------
    print("\n[2] ANCSA named projects (mines, deposits, fields, carbon)")
    before = len(assets)
    for f in ANCSA_PROJECTS:
        path, quote, err = resolve_fact(f["doc"], f["anchor"], f.get("must", []))
        if not quote:
            refused.append((f["asset_name"], err)); continue
        base = os.path.basename(path)[:-4]
        url, fetched = idx.get(base, ("", "2026-08-05"))
        aid = new_id("ANCSA")
        assets.append({
            "resource_asset_id": aid, "asset_type": f["asset_type"],
            "asset_name": f["asset_name"],
            "source_system": A, "source_asset_id": base,
            "resource_type": f["resource_type"], "commodity": f["commodity"],
            "state": "AK", "land_status": "ancsa_fee",
            "land_status_source_url": url,
            "operator_name": f.get("operator", ""), "operator_entity_id": "",
            "status": f.get("status", ""), "geometry_basis": "none_published",
            "confidence": "A", "source_url": url, "fetched_date": fetched,
            "built_date": TODAY,
            "legal_title_holder": f"{f['owner']} (ANCSA fee estate)",
            "beneficial_interest_class": "anc_shareholder",
            "ownership_basis": (
                "the owning corporation's own annual report. Ownership of the "
                "ground is a different fact from operatorship of the project; "
                "the operator is recorded as a counterparty and never as an "
                "owner."),
            "area_acres": f.get("acres", ""),
            "area_unit": "acres" if f.get("acres") else "",
            "area_basis": ("stated in the quoted sentence"
                           if f.get("acres") else ""),
            "as_of_date": base[:4],
            "evidence_document": base,
            "evidence_document_type": "ANCSA annual report",
            "evidence_quote": quote, "quote_verified": "yes",
            "revenue_coverage_state": (
                "PUBLISHES" if f["asset_name"] == "Red Dog Mine" else "NOT_FOUND"),
            "production_coverage_state": "NOT_FOUND",
            "coverage_note": f.get("note", ""),
        })
        add_party(aid, f["owner"], "owner", "parent_native_entity",
                  "the owning corporation's own annual report", url, fetched, True)
        if f.get("operator"):
            add_party(aid, f["operator"], "operator", "counterparty",
                      "named as operator in the quoted sentence; an operator is "
                      "never an owner", url, fetched, False)
    print(f"    project rows built      : {len(assets) - before}")

    # -- 3. Osage Mineral Estate -------------------------------------------
    # THE ownership-vs-beneficial-interest case in this dataset, and the reason
    # the two columns exist. Title is federal; the beneficiaries are headright
    # holders; the Osage Nation's own auditor states the Nation does not
    # receive the royalty distributions at all.
    print("\n[3] Osage Mineral Estate")
    reg_path = RAW / "_state_mechanisms" / "cedar_state_mechanism_register.csv"
    reg_rows = read_csv(reg_path)
    reg_text = flatten(open(reg_path, encoding="utf-8", errors="replace").read())

    # TWO DIFFERENT ESTATES, AND THEY MUST NOT INHERIT EACH OTHER'S FACTS.
    #
    # The MINERAL estate is undivided, reserved to the Osage Nation by the 1906
    # Act, and its income runs to headright holders. The 135,000 acres of
    # SURFACE trust and restricted land are a separate thing entirely: the 1906
    # Act severed surface from minerals and allotted the surface, so those
    # acres are held for the Nation AND for individual Osage allottees, and the
    # Minerals Council publishes nothing about them. Giving the surface tract
    # the mineral estate's beneficiary class or its PUBLISHES coverage would be
    # the same false attribution in miniature.
    OSAGE = [
        ("mineral_estate", "Osage Mineral Estate",
         "administering leasing and development of the 1.45 million-acre Osage Mineral Estate",
         "1.45 million", "oil_and_gas",
         "Oil, gas, sand and gravel, water use",
         "osage_headright_holder", "PUBLISHES",
         "Revenue is published BY THE OSAGE MINERALS COUNCIL, not by the "
         "federal administrator. ONRR publishes nothing that names the Osage: "
         "the string 'Osage' appears zero times in every ONRR bulk file Cedar "
         "Press holds. Lease- and tract-level records for the estate sit in "
         "BIA systems that are not public."),
        ("tract", "Osage County trust and restricted lands (BIA Osage Agency)",
         "overseeing more than 135,000 acres of trust and restricted lands in Osage County",
         "135,000", "land_and_minerals", "",
         "mixed_tribal_and_allottee", "NOT_FOUND",
         "SURFACE trust and restricted land, NOT the mineral estate. The 1906 "
         "Act severed the two, so these acres are held for the Nation and for "
         "individual Osage allottees together and the split is not published. "
         "No revenue series exists for them: the Osage Minerals Council "
         "reports on minerals only, and this row must never inherit the "
         "mineral estate's revenue."),
    ]
    osage_url = ""
    osage_checked = ""
    for r in reg_rows:
        if "Osage Agency proudly serves" in (r.get("quote") or ""):
            osage_url = r.get("citation_url", "")
            osage_checked = r.get("checked_date", "")
    before = len(assets)
    osage_ids = []
    for (atype, aname, anchor, acres, rtype, commodity,
         benef, rev_cov, cov_note) in OSAGE:
        if anchor not in reg_text:
            refused.append((aname, "anchor_absent_from_retained_evidence_register"))
            continue
        aid = new_id("OSAGE")
        osage_ids.append(aid)
        assets.append({
            "resource_asset_id": aid, "asset_type": atype, "asset_name": aname,
            "source_system": "BIA_Osage_Agency", "source_asset_id": "",
            "resource_type": rtype, "commodity": commodity,
            "state": "OK", "county": "Osage", "fips_code": "40113",
            "reservation_name": "Osage Reservation",
            "land_status": "tribal_trust",
            "land_status_source_url": osage_url,
            "operator_name": "", "status": "producing",
            "geometry_basis": "none_published",
            "confidence": "B", "source_url": osage_url,
            "fetched_date": osage_checked or "2026-08-06", "built_date": TODAY,
            "legal_title_holder": (
                "United States, in trust; leasing and development administered "
                "by the BIA Osage Agency"),
            "beneficial_interest_class": benef,
            "ownership_basis": (
                "The 1906 Osage Allotment Act reserved the mineral estate to "
                "the Osage Nation UNDIVIDED, and the beneficial interest is "
                "held as headrights by individual annuitants. These are "
                "DIFFERENT FACTS and are not collapsed: the Osage Nation's own "
                "audited statements say 'The distribution of mineral royalty "
                "income to entitled mineral royalty income owners is "
                "administered by the Bureau of Indian Affairs; these "
                "distributions are not received by the Nation and are not "
                "reflected in the accompanying financial statements.' So this "
                "asset must never be read as revenue to the Osage Nation's "
                "government."),
            "area_acres": acres, "area_unit": "acres",
            "area_basis": "stated by the BIA Osage Agency; never derived",
            "as_of_date": osage_checked or "2026-08-06",
            "evidence_document": "cedar_state_mechanism_register.csv",
            "evidence_document_type": (
                "BIA Osage Agency page, quoted in Cedar Press's retained "
                "evidence register"),
            "evidence_quote": next(
                (r["quote"] for r in reg_rows
                 if anchor in (r.get("quote") or "")), ""),
            "quote_verified": "yes",
            "revenue_coverage_state": rev_cov,
            "production_coverage_state": "NOT_FOUND",
            "coverage_note": cov_note,
        })
        if atype == "mineral_estate":
            add_party(aid, "The Osage Nation", "reserved_mineral_estate_holder",
                      "parent_native_entity",
                      "the 1906 Osage Allotment Act reserved the mineral estate "
                      "to the Osage Nation undivided; this is the RESERVED "
                      "INTEREST, not receipt of the royalty income",
                      osage_url, osage_checked or "2026-08-06", True, "B")
        else:
            # The surface tract is held for the Nation AND for individual
            # Osage allottees. Naming the Nation as its owner would assert an
            # exclusivity the source does not support, so no owner link is
            # written and the reason is recorded rather than left blank.
            add_party(aid, "The Osage Nation", "beneficiary_among_others",
                      "serves_native_entities",
                      "the BIA Osage Agency states it oversees these acres for "
                      "the Osage Nation; the surface was ALLOTTED in 1906, so "
                      "individual Osage allottees hold interests in the same "
                      "acres and no exclusive tribal ownership is asserted",
                      osage_url, osage_checked or "2026-08-06", True, "C")
    print(f"    Osage rows built        : {len(assets) - before}")

    # -- 4. Lower-48 leases on tribal TRUST land ---------------------------
    print("\n[4] Lower-48 tribal leases (retrieved lease and lessee filings)")
    before = len(assets)
    crow_txt = LEASE_DOCS / "westmoreland_crow_coal_lease_ex10-51.txt"
    crow_url = ("https://www.sec.gov/Archives/edgar/data/106455/"
                "000095013409005346/d66453exv10w51.htm")
    crow_id = None
    if crow_txt.exists():
        q, err = gate(str(crow_txt),
                      r"This CROW TRIBAL LANDS COAL LEASE .{0,40}made and entered into this 13",
                      ["13", "2004"])
        if q:
            crow_id = new_id("LEASE")
            assets.append({
                "resource_asset_id": crow_id, "asset_type": "lease",
                "asset_name": "Crow Tribal Lands Coal Lease",
                "source_system": "SEC_EDGAR_exhibit",
                "source_asset_id": "0000950134-09-005346 EX-10.51",
                "resource_type": "coal", "commodity": "Coal",
                "state": "MT", "county": "Big Horn", "fips_code": "30003",
                "reservation_name": "Crow Reservation",
                "land_status": "tribal_trust",
                "land_status_source_url": crow_url,
                "operator_name": "Westmoreland Resources, Inc.",
                "status": "executed", "geometry_basis": "none_published",
                "confidence": "A", "source_url": crow_url,
                "fetched_date": TODAY, "built_date": TODAY,
                "legal_title_holder": (
                    "United States, in trust for the Crow Tribe of Indians "
                    "(the lease is titled 'LEASE OF INDIAN LAND' and is "
                    "entered into under the Indian Mineral Development Act of "
                    "1982, which requires Secretarial approval)"),
                "beneficial_interest_class": "tribal_government",
                "ownership_basis": (
                    "The lease names the CROW TRIBE OF INDIANS as Lessor and "
                    "WESTMORELAND RESOURCES, INC. as Lessee. Lessor is the "
                    "beneficial owner; the lessee is a counterparty and owns "
                    "nothing."),
                "area_acres": "",
                "area_basis": (
                    "NOT STATED IN THE INSTRUMENT. The Leased Premises are "
                    "defined by reference to the Mining Area under Section 8 "
                    "of a separate Exploration Agreement, which this exhibit "
                    "does not reproduce. No acreage is inferred."),
                "as_of_date": "2004-02-13",
                "evidence_document": "westmoreland_crow_coal_lease_ex10-51.htm",
                "evidence_document_type": "executed lease, SEC EDGAR exhibit",
                "evidence_quote": q, "quote_verified": "yes",
                "revenue_coverage_state": "WITHHOLDS",
                "production_coverage_state": "NOT_FOUND",
                "coverage_note": (
                    "The lease publishes RATES and never dollars: royalty at "
                    "6.5% of the sales price per ton F.O.B. Mine at loadout, "
                    "capped so total royalty 'shall never exceed 12.5% of the "
                    "Sale Price', plus annual rental of $1.00 per acre. "
                    "MULTIPLYING A RATE BY TONNAGE WOULD BE A MODELLED NUMBER "
                    "AND IS REFUSED. Montana publishes no Crow coal series: "
                    "'Crow' appears zero times in all 430 pages of the MT DOR "
                    "2022-2024 Biennial Report, and the state's coal tax on "
                    "Crow Reservation production was invalidated in 1988."),
            })
            add_party(crow_id, "Crow Tribe of Indians", "lessor",
                      "parent_native_entity",
                      "named as Lessor in the executed lease", crow_url,
                      TODAY, True)
            add_party(crow_id, "Westmoreland Resources, Inc.", "lessee",
                      "counterparty",
                      "named as Lessee in the executed lease; a lessee is never "
                      "an owner", crow_url, TODAY, False)
        else:
            refused.append(("Crow Tribal Lands Coal Lease", err))
    else:
        refused.append(("Crow Tribal Lands Coal Lease", "document_not_on_disk"))

    peabody_txt = LEASE_DOCS / "peabody_10k_fy2010.txt"
    peabody_url = ("https://www.sec.gov/Archives/edgar/data/1064728/"
                   "000095012311019465/c61476e10vk.htm")
    if peabody_txt.exists():
        q, err = gate(str(peabody_txt),
                      r"These leases cover coal contained in 64,783 acres of land in northern Arizona",
                      ["64,783"])
        if q:
            aid = new_id("LEASE")
            assets.append({
                "resource_asset_id": aid, "asset_type": "lease_group",
                "asset_name": ("Three Peabody coal leases with the Navajo "
                               "Nation and the Hopi Tribe"),
                "source_system": "SEC_EDGAR_10K",
                "source_asset_id": "0000950123-11-019465 (Peabody Energy FY2010 10-K)",
                "resource_type": "coal", "commodity": "Coal",
                "state": "AZ",
                "reservation_name": "Navajo Nation; Hopi Reservation",
                "land_status": "tribal_trust",
                "land_status_source_url": peabody_url,
                "operator_name": "Peabody Western Coal Company",
                "status": "leased", "geometry_basis": "none_published",
                "confidence": "A", "source_url": peabody_url,
                "fetched_date": TODAY, "built_date": TODAY,
                "legal_title_holder": (
                    "United States, in trust; the lessee states the leases "
                    "'are administered by the U.S. Department of the Interior'"),
                "beneficial_interest_class": "tribal_government",
                "ownership_basis": (
                    "The lessee's own 10-K states it 'leases coal reserves in "
                    "Arizona from The Navajo Nation and the Hopi Tribe'. Two "
                    "different tribal lessors share one acreage figure and the "
                    "filing does not split it between them."),
                "area_acres": "64,783", "area_unit": "acres",
                "area_basis": (
                    "stated as a COMBINED figure for all three leases across "
                    "two reservations. It is not divisible between the Navajo "
                    "Nation and the Hopi Tribe and is not divided here."),
                "as_of_date": "2010-12-31",
                "asset_count_in_source": "3",
                "evidence_document": "peabody_10k_fy2010_c61476e10vk.htm",
                "evidence_document_type": "SEC Form 10-K",
                "evidence_quote": q, "quote_verified": "yes",
                "revenue_coverage_state": "WITHHOLDS",
                "production_coverage_state": "NOT_FOUND",
                "coverage_note": (
                    "ONE ROW, NOT THREE. The filing says 'three coal leases' "
                    "and identifies none of them individually - no lease "
                    "number, no lessor split, no per-lease acreage. Emitting "
                    "three rows would invent two assets. THE ROYALTY-RATE "
                    "TRAP: the 12.5% surface / 8.0% underground rates printed "
                    "nearby in the same filing govern FEDERAL leases; for the "
                    "tribal leases the filing says only that rates are "
                    "'generally based upon a percentage of the gross "
                    "realization' and states no number. No rate is recorded "
                    "for this asset and none may be inverted against it."),
            })
            add_party(aid, "Navajo Nation", "lessor", "parent_native_entity",
                      "named as a lessor in the lessee's 10-K; the filing does "
                      "not state which of the three leases is Navajo",
                      peabody_url, TODAY, True, "B")
            add_party(aid, "Hopi Tribe", "lessor", "parent_native_entity",
                      "named as a lessor in the lessee's 10-K; the filing does "
                      "not state which of the three leases is Hopi",
                      peabody_url, TODAY, True, "B")
            add_party(aid, "Peabody Western Coal Company", "lessee",
                      "counterparty",
                      "the filing entity's coal subsidiary named as lessee",
                      peabody_url, TODAY, False)
        else:
            refused.append(("Peabody Navajo/Hopi coal leases", err))

        q2, err2 = gate(str(peabody_txt),
                        r"hourly workers at our Kayenta Mine in Arizona", [])
        if q2:
            aid = new_id("LEASE")
            assets.append({
                "resource_asset_id": aid, "asset_type": "mine",
                "asset_name": "Kayenta Mine",
                "source_system": "SEC_EDGAR_10K",
                "source_asset_id": "0000950123-11-019465 (Peabody Energy FY2010 10-K)",
                "resource_type": "coal", "commodity": "Coal",
                "state": "AZ", "land_status": "not_stated",
                "land_status_source_url": peabody_url,
                "operator_name": "Peabody Western Coal Company",
                "status": "producing", "geometry_basis": "none_published",
                "confidence": "B", "source_url": peabody_url,
                "fetched_date": TODAY, "built_date": TODAY,
                "legal_title_holder": "not stated in the cited filing",
                "beneficial_interest_class": "not_stated",
                "ownership_basis": (
                    "NOT ASSERTED. The filing names Kayenta as a mine it "
                    "operates in Arizona and separately says it leases coal "
                    "from the Navajo Nation and the Hopi Tribe. It does NOT "
                    "say which mine works which lease. Joining the two would "
                    "be an inference, so no tribal owner is attached to this "
                    "row and no party link is written for it."),
                "as_of_date": "2010-12-31",
                "evidence_document": "peabody_10k_fy2010_c61476e10vk.htm",
                "evidence_document_type": "SEC Form 10-K",
                "evidence_quote": q2, "quote_verified": "yes",
                "revenue_coverage_state": "NOT_FOUND",
                "production_coverage_state": "PUBLISHES",
                "coverage_note": (
                    "Kept deliberately UNATTRIBUTED. It is recorded so that a "
                    "future pass with a BIA lease record can attach it on "
                    "evidence rather than on proximity."),
            })
    else:
        refused.append(("Peabody Navajo/Hopi coal leases", "document_not_on_disk"))
    print(f"    lease rows built        : {len(assets) - before}")

    # -- write, append-safe -------------------------------------------------
    print("\n[5] Writing (append; only RAS- rows are replaced)")
    apath = CLEAN / "resource_assets.csv"
    existing = read_csv(apath)
    kept = [r for r in existing
            if not r.get("resource_asset_id", "").startswith(ID_PREFIX)]
    print(f"    existing rows carried through : {len(kept):,}")

    all_assets = kept + assets
    dupes = [k for k, v in Counter(
        r["resource_asset_id"] for r in all_assets).items() if v > 1]
    if dupes:
        print(f"    !! DUPLICATE asset id(s), NOT WRITING: {dupes[:6]}")
        raise SystemExit("duplicate primary keys; assets not written")
    print(f"    primary key check             : {len(all_assets):,} ids, all unique")

    # vocabulary gate
    bad = [a for a in all_assets if a.get("land_status") not in LAND_STATUS]
    bad += [a for a in all_assets
            if a.get("beneficial_interest_class") not in BENEFICIAL]
    bad += [a for a in all_assets
            if a.get("revenue_coverage_state") not in COVERAGE_STATES
            or a.get("production_coverage_state") not in COVERAGE_STATES]
    if bad:
        print(f"    !! {len(bad)} rows outside a controlled vocabulary; NOT WRITING")
        for b in bad[:5]:
            print("       ", b["resource_asset_id"], b.get("land_status"),
                  b.get("beneficial_interest_class"))
        raise SystemExit("vocabulary violation; assets not written")

    write_csv(apath, all_assets, ASSET_FIELDS)

    # parties: re-read immediately before writing so a concurrent agent's rows
    # are not clobbered, and keep script 83's column set exactly.
    ppath = CLEAN / "resource_parties.csv"
    existing_par = read_csv(ppath)
    kept_par = [r for r in existing_par
                if not r.get("object_id", "").startswith(ID_PREFIX)]
    print(f"    existing party links carried  : {len(kept_par):,}")
    write_csv(ppath, kept_par + parties, PARTY_FIELDS)

    # -- 6. asset -> revenue linkage PROPOSALS (never merged) ---------------
    print("\n[6] Asset->revenue linkage proposals (review only)")
    rev = read_csv(CLEAN / "resource_revenue.csv")
    props = []
    rd_asset = next((a for a in assets if a["asset_name"] == "Red Dog Mine"), None)
    if rd_asset:
        teck_q = rd_asset["evidence_quote"]
        for r in rev:
            if "IN_MINE_ROYALTY" not in r["resource_revenue_event_id"]:
                continue
            # TIERED, NOT POOLED. Most of these rows carry evidence that names
            # Red Dog. One - FY2022, a table reading - does not, and the only
            # thing tying it to Red Dog is that Red Dog is NANA's producing
            # mine. That is context, not evidence, and it is graded C and said
            # out loud rather than folded in with the others.
            names_mine = "red dog" in (
                r["beneficiary_note"] + r["source_record_id"]).lower()
            props.append({
                "proposal_id": f"RASL-{len(props)+1:04d}",
                "resource_asset_id": rd_asset["resource_asset_id"],
                "asset_name": rd_asset["asset_name"],
                "resource_revenue_event_id": r["resource_revenue_event_id"],
                "revenue_source_system": r["source_system"],
                "link_type": "asset_generates_revenue_event",
                "link_basis": (
                    "the revenue row's own retained evidence names Red Dog "
                    "Mine, and the row is typed as royalty from a mine on the "
                    "corporation's own ANCSA lands. Proposed, not asserted, "
                    "and not derived from any arithmetic between the files."
                    if names_mine else
                    "WEAKER LEG: this row's own evidence does NOT name Red Dog "
                    "Mine. It is a table reading typed as royalty from a mine "
                    "on NANA's own ANCSA lands, and Red Dog is the only "
                    "producing mine NANA reports. That is context, not "
                    "evidence. Needs a ruling before it is treated like the "
                    "rows above."),
                "proposed_payer_entity_name": "Teck Alaska Incorporated",
                "proposed_payer_entity_id": "",
                "payer_basis": (
                    "NANA's audited statements name Teck Alaska as the "
                    "operator of Red Dog and separately report 'Amounts due "
                    "from Teck' on an accrual basis. Teck is a NON-NATIVE "
                    "counterparty and is deliberately not resolved to the "
                    "spine."),
                "evidence_quote": teck_q,
                "confidence": "B" if names_mine else "C",
                "source_url": rd_asset["source_url"],
                "built_date": TODAY, "status": "PROPOSED_AWAITING_RULING",
            })
    for oid in osage_ids:
        oa = next(a for a in assets if a["resource_asset_id"] == oid)
        if oa["asset_type"] != "mineral_estate":
            continue
        for r in rev:
            if not r["resource_revenue_event_id"].startswith("RRE-OK-"):
                continue
            props.append({
                "proposal_id": f"RASL-{len(props)+1:04d}",
                "resource_asset_id": oid, "asset_name": oa["asset_name"],
                "resource_revenue_event_id": r["resource_revenue_event_id"],
                "revenue_source_system": r["source_system"],
                "link_type": "asset_generates_revenue_event",
                "link_basis": (
                    "the revenue row is published by the Osage Minerals "
                    "Council, the body that administers this mineral estate, "
                    "and reports that estate's own receipts or the resulting "
                    "per-headright rate. NO PAYER IS PROPOSED: the estate's "
                    "lessees are not named in the source, and a per-headright "
                    "rate is a rate, not a payment."),
                "proposed_payer_entity_name": "", "proposed_payer_entity_id": "",
                "payer_basis": "",
                "evidence_quote": oa["evidence_quote"],
                "confidence": "B", "source_url": oa["source_url"],
                "built_date": TODAY, "status": "PROPOSED_AWAITING_RULING",
            })
    write_csv(REVIEW / f"resource_asset_revenue_linkage_proposals_{TODAY}.csv",
              props, LINK_FIELDS)
    print(f"    proposals written       : {len(props):,} "
          f"(payer proposed on "
          f"{sum(1 for p in props if p['proposed_payer_entity_name']):,})")

    # -- 7. coverage register ----------------------------------------------
    cov = build_coverage()
    bad = [c for c in cov if c["coverage_state"] not in COVERAGE_STATES]
    if bad:
        raise SystemExit(f"coverage_state outside vocabulary: {bad[:3]}")
    write_csv(CLEAN / "resource_asset_source_coverage.csv", cov, COVERAGE_FIELDS)
    print(f"\n[7] Coverage register     : {len(cov):,} source x attribute rows")
    for k, v in Counter(c["coverage_state"] for c in cov).most_common():
        print(f"      {v:3}  {k}")

    # -- summary ------------------------------------------------------------
    print("\n--- asset layer summary ---")
    print(f"  asset rows built          : {len(assets):,}")
    for k, v in Counter(a["asset_type"] for a in assets).most_common():
        print(f"      {v:3}  asset_type={k}")
    for k, v in Counter(a["land_status"] for a in assets).most_common():
        print(f"      {v:3}  land_status={k}")
    for k, v in Counter(a["beneficial_interest_class"]
                        for a in assets).most_common():
        print(f"      {v:3}  beneficial_interest_class={k}")
    linked = {p["entity_id"] for p in parties if p["entity_id"]}
    print(f"  party links written       : {len(parties):,}")
    print(f"  distinct Native entities  : {len(linked):,}")
    print(f"  quotes verified           : "
          f"{sum(1 for a in assets if a['quote_verified'] == 'yes'):,} of {len(assets):,}")
    print(f"  REFUSED                   : {len(refused):,}")
    for name, why in refused:
        print(f"      - {name}: {why}")


def build_coverage():
    """Four-valued coverage, per source x attribute.

    PUBLISHES  - retrieved it.
    WITHHOLDS  - the publisher has stated it will not release it.
    NOT_FOUND  - swept and did not find it, naming what was swept.
    NOT_CHECKED- nobody looked.
    A statutory withholding and an unchecked source look identical in a blank
    cell and are opposite findings.
    """
    D = "2026-08-12"
    C = []

    def add(src, pub, attr, state, swept, ev, url, when=D):
        C.append({"source_system": src, "publisher": pub, "attribute": attr,
                  "coverage_state": state, "what_was_swept": swept,
                  "evidence": ev, "source_url": url, "checked_date": when})

    onrr = "https://revenuedata.onrr.gov/how-revenue-works/native-american-revenue/"
    add("ONRR_NRRD", "Office of Natural Resources Revenue",
        "lease / agreement / well identifier on Native American records",
        "WITHHOLDS",
        "all five ONRR bulk files held locally: monthly_revenue, "
        "calendar_year_revenue, fiscal_year_revenue, "
        "fiscal_year_disbursements, monthly_production",
        "No ONRR bulk file carries a lease, agreement, tract or well column "
        "for ANY land class, and the publisher states: 'For all Native "
        "American land, the federal government only releases natural resource "
        "extraction and revenue information in aggregate. Specific data on "
        "Native American revenues are confidential and proprietary.'",
        onrr, "2026-08-06")
    add("ONRR_NRRD", "Office of Natural Resources Revenue",
        "state / county / FIPS on Native American records", "WITHHOLDS",
        "9,238 Native American monthly revenue rows",
        "0 of 9,238 Native rows carry any geography, against 99.8% of Federal "
        "rows in the same file. Re-measured on every run of script 83.",
        "https://revenuedata.onrr.gov/downloads/", "2026-08-06")
    add("ONRR_NRRD", "Office of Natural Resources Revenue",
        "tribe or entity name", "WITHHOLDS",
        "every ONRR bulk file held", "No ONRR file has a tribe-name field at "
        "all. 'Osage' appears zero times across all of them, despite the Osage "
        "mineral estate having exactly one owner.",
        onrr, "2026-08-06")
    add("ONRR_NRRD", "Office of Natural Resources Revenue",
        "production volume, Native American aggregate", "PUBLISHES",
        "monthly_production.csv", "837 Native American rows, land class x land "
        "category x commodity x volume. Held raw: with no lease, geography or "
        "entity there is nothing to attach a volume to, and volume x price is "
        "a model, not a measurement.",
        "https://revenuedata.onrr.gov/downloads/", "2026-08-06")

    add("BIA_NIOGEMS", "Bureau of Indian Affairs",
        "lease / tract / agreement / well identifiers for Indian minerals",
        "NOT_FOUND",
        "public BIA web properties",
        "NIOGEMS is an internal BIA system on the order of 50 tribal users "
        "across 8 reservations. No public interface or extract was located. "
        "The niogems_* columns are empty BY CONSTRUCTION so that access, if "
        "ever granted, is a merge and not a rebuild. Partnership target, never "
        "a cited source.",
        "https://www.bia.gov/", "2026-08-06")
    add("BIA_Osage_Agency", "Bureau of Indian Affairs",
        "per-lease and per-tract records of the Osage Mineral Estate",
        "NOT_FOUND", "BIA Osage Agency public pages",
        "The Agency states it administers leasing of the 1.45 million-acre "
        "estate; it publishes the estate's extent, not its leases.",
        "https://www.bia.gov/regional-offices/eastern-oklahoma/osage-agency")

    add("ND_DMR", "North Dakota Dept. of Mineral Resources",
        "mineral ownership (trust vs fee) on wells", "WITHHOLDS",
        "DMR free well search field list",
        "No DMR field states trust vs fee mineral ownership. Trust/fee is a "
        "Tax Commissioner construct and is FRACTIONAL, not binary - each "
        "spacing unit carries a Trust Ratio by mineral acreage. The strings "
        "TRUST and INDIAN in DMR data are lease, well and operator NAMES and "
        "must never be parsed as ownership. The complete Well Index is "
        "subscription-gated.",
        "https://www.dmr.nd.gov/oilgas/", "2026-08-06")
    add("MT_BOGC", "Montana Board of Oil and Gas Conservation",
        "mineral ownership on wells", "WITHHOLDS",
        "BOGC documented well attribute list",
        "Location and well identity only; no mineral-ownership field. Same "
        "conclusion as North Dakota.",
        "https://bogc.dnrc.mt.gov/", "2026-08-06")

    add("SEC_EDGAR", "U.S. Securities and Exchange Commission",
        "executed tribal mineral leases filed as exhibits", "PUBLISHES",
        "EDGAR full-text search for the Navajo/Hopi lease language, and the "
        "Westmoreland exhibit index",
        "Two instruments retrieved: the Crow Tribal Lands Coal Lease "
        "(EX-10.51) and Peabody's FY2010 10-K describing three Navajo/Hopi "
        "coal leases. This is the only route found to a tribal lease "
        "INSTRUMENT. www.sec.gov returns HTTP 403 without a declared "
        "User-Agent; that is an access rule, not an absence.",
        "https://www.sec.gov/cgi-bin/srqsb?text=form-type%3D10-K")
    add("SEC_EDGAR", "lessee filings",
        "royalty rate on tribal coal leases", "WITHHOLDS",
        "Peabody FY2010 10-K, Westmoreland Crow lease",
        "Peabody states tribal rates are 'generally based upon a percentage of "
        "the gross realization' and gives no number; the 12.5%/8.0% rates in "
        "the same filing are FEDERAL leases. Westmoreland's lease gives 6.5% "
        "capped at 12.5% but no tonnage. Rate x tonnage is a model and is "
        "refused in both cases.",
        "https://www.sec.gov/")

    add("ANCSA_portal", "Alaska Dept. of Commerce ANCSA filings portal",
        "corporation-level land and subsurface estate acreage", "PUBLISHES",
        "166 retrieved regional-corporation annual reports",
        "All twelve regional corporations state conveyed acreage in audited "
        "notes or, for CIRI, in a report infographic.",
        "https://portal.akdbsstar.us/StarWebPortal/", "2026-08-05")
    add("ANCSA_portal", "ANCSA regional corporations",
        "per-asset revenue or production", "NOT_FOUND",
        "the same 166 reports",
        "Natural resource revenue is reported consolidated. The one exception "
        "is NANA, which reports Red Dog Mine royalties as a line - which is "
        "why Red Dog is the only asset here with revenue_coverage_state = "
        "PUBLISHES.",
        "https://portal.akdbsstar.us/StarWebPortal/", "2026-08-05")
    add("ANCSA_portal", "ANCSA village corporations",
        "village corporation land and resource assets", "NOT_CHECKED",
        "nothing - not opened this pass",
        "173 village corporations are in the spine and the portal holds their "
        "filings. They hold the SURFACE estate where regionals hold the "
        "subsurface, so they are the missing half of the Alaska asset picture. "
        "Highest-value unworked lead.",
        "https://portal.akdbsstar.us/StarWebPortal/")

    add("BIA_forestry", "Bureau of Indian Affairs",
        "timber sales by reservation", "NOT_CHECKED",
        "nothing this pass",
        "bia.gov/bia/ots/forestry was recorded as 404 in an earlier wave. The "
        "only plausible route to named-tribe timber volume or value for "
        "AK/WA/MN/WI/CA. Not re-probed here.",
        "https://www.bia.gov/bia/ots/forestry")
    add("Indian_water_rights_settlements", "Congress / Dept. of the Interior",
        "quantified tribal water rights", "NOT_CHECKED",
        "nothing this pass",
        "Settlement acts quantify tribal water rights in acre-feet in enacted "
        "public law, which would make them the best-evidenced asset class "
        "available. Requires reading the Statutes at Large per settlement and "
        "was not attempted; recorded as unfinished work, not as absence.",
        "https://www.doi.gov/")
    add("BIA_rights_of_way", "Bureau of Indian Affairs",
        "rights-of-way across tribal and allotted land", "NOT_CHECKED",
        "nothing this pass",
        "No systematic public register was identified. Individual ROWs surface "
        "in FERC and NEPA records one at a time.",
        "https://www.bia.gov/")
    add("BIA_LTRO", "Bureau of Indian Affairs Land Titles and Records Offices",
        "allotments and individual Indian trust tracts", "WITHHOLDS",
        "public BIA land-records interfaces",
        "Individual Indian trust ownership is not public. THIS IS THE LARGEST "
        "STRUCTURAL HOLE IN THE ASSET LAYER: ONRR's own land class mixes "
        "tribal with individual allottee interests, and the allottee side has "
        "no public asset register at all. Zero allotment rows are built here, "
        "and none should be synthesised from reservation geography - a tract "
        "inside a reservation boundary is not evidence of tribal ownership.",
        "https://www.bia.gov/bia/ots/dlttr/ltro")

    add("OSMRE_AML", "Office of Surface Mining Reclamation and Enforcement",
        "abandoned mine land fee distributions naming Crow, Hopi, Navajo",
        "PUBLISHES", "11 retrieved PDFs, FY2016-FY2026",
        "Named entity, measured amount, continuous series - and HELD, because "
        "the text layer is offset by one row and the tables print no per-row "
        "check that would let a de-skew be proven. Revenue, not an asset; "
        "recorded here because it is the highest-value unbuilt lead touching "
        "these same tribes.",
        "https://www.osmre.gov/", "2026-08-06")
    return C


if __name__ == "__main__":
    main()
