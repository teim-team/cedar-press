#!/usr/bin/env python3
"""
32b_build_gaming_nepa_pilot.py -- Cedar Press Gaming dataset, Phase 2 Step B.

Builds the three NEPA extraction tables from the two PILOT document sets
retrieved by 32a:

  data/clean/gaming_project_facilities.csv    (Table 1: facility-project record)
  data/clean/gaming_projections.csv           (Table 2: projection/impact record)
  data/clean/gaming_mitigation_agreements.csv (Table 3: mitigation & IGAs)

EVERY value below was read out of the retrieved PDF and carries its source
document, PDF page, printed page label and table reference. Nothing is inferred
from outside the documents. Calculated values are flagged `calculated` and carry
their arithmetic in `derivation`; nothing derived is ever presented as reported.

`entity_id` is blank throughout -- spine linking is out of scope here and is
never guessed.
"""
import os, csv, io, datetime
from pathlib import Path

BASE = str(Path(__file__).resolve().parent.parent)
CLEAN = os.path.join(BASE, "data", "clean")
LOG = os.path.join(BASE, "logs", "32_gaming_nepa_pilot.log")

buf = io.StringIO()
def log(*a):
    s = " ".join(str(x) for x in a); print(s); buf.write(s + "\n")

BIA = "https://www.bia.gov/sites/default/files/media_document/"

# short document keys -> (filename, url, document_date, description)
DOCS = {
    "OSAGE_EA": ("ea-report.pdf", BIA + "ea-report.pdf", "2025-07",
                 "Osage Nation Lake Ozark Casino Resort Project Environmental Assessment, July 2025"),
    "OSAGE_NOA": ("noa-dea.pdf", BIA + "noa-dea.pdf", "2025-07",
                  "BIA Eastern Oklahoma Region Notice of Availability of a Draft EA, Osage Lake Ozark"),
    "MEN_EA": ("menominee-kenosha_casino_published_ea.pdf",
               BIA + "menominee-kenosha_casino_published_ea.pdf", "2026-03",
               "Menominee Indian Tribe of Wisconsin Kenosha Casino Project Environmental Assessment, March 2026 (NEPA-ID-58312)"),
    "MEN_PROJDESC": ("menominee_kenosha_casino_ea_appendix-proj-desc.pdf",
                     BIA + "menominee_kenosha_casino_ea_appendix-proj-desc.pdf", "2026-03",
                     "Menominee Kenosha EA Appendix PROJ DESC -- Alternatives Tables"),
    "MEN_SOCIO": ("menominee_kenosha_casino_ea_appendix-socio.pdf",
                  BIA + "menominee_kenosha_casino_ea_appendix-socio.pdf", "2023-11-01",
                  "Menominee Kenosha EA Appendix SOCIO -- KlasRobinson Q.E.D., Economic Impact Study, November 2023"),
    "MEN_ENVANA": ("menominee_kenosha_casino_ea_appendix-env-ana.pdf",
                   BIA + "menominee_kenosha_casino_ea_appendix-env-ana.pdf", "2026-03",
                   "Menominee Kenosha EA Appendix ENV ANA -- Resources Not of Environmental Concern"),
    "MEN_IGA": ("menominee_kenosha_casino_ea_appendix-iga.pdf",
                BIA + "menominee_kenosha_casino_ea_appendix-iga.pdf", "2026-03",
                "Menominee Kenosha EA Appendix IGA -- Intergovernmental Agreements (City, County, Tourism)"),
    "MEN_NOA1": ("2026.03.09-final-noa-menominee-kenosha-ea-signed-2.pdf",
                 BIA + "2026.03.09-final-noa-menominee-kenosha-ea-signed-2.pdf", "2026-03-09",
                 "BIA Midwest Regional Office Notice of Availability, Menominee Kenosha EA"),
}

def doc(k): return DOCS[k][3]
def url(k): return DOCS[k][1]

# =============================================================== TABLE 1 =====
T1_COLS = [
    # --- schema as specified in GAMING_DATASET_PLAN.md ---
    "project_id", "tribe", "entity_id", "facility_name", "status",
    "source_document", "document_date", "alternative", "acres", "gaming_sqft",
    "total_sqft", "machines", "tables", "hotel_rooms", "meeting_sqft",
    "restaurant_seats", "parking", "hours", "construction_cost",
    "construction_start", "construction_duration", "projected_opening",
    "observation_status", "source_page",
    # --- columns the pilot proved are needed (see GAMING_NEPA_PILOT_LOG.md) ---
    "project_name", "state", "decision_id", "alternative_role", "record_type",
    "table_game_seats", "entertainment_sqft", "entertainment_seats",
    "gaming_class", "observation_date", "source_page_label", "table_ref",
    "source_url", "value_completeness", "notes",
]

def t1(**kw):
    r = {c: "" for c in T1_COLS}
    r.update(kw)
    bad = [k for k in kw if k not in T1_COLS]
    assert not bad, f"unknown T1 column(s): {bad}"
    r["source_document"] = doc(kw["_doc"]) if "_doc" in kw else r["source_document"]
    return r

OSAGE = dict(project_id="OSAGE-LAKEOZARK", tribe="The Osage Nation", state="MO",
             decision_id="GLD-MO-the-osage-nation-20250731",
             project_name="Osage Nation Lake Ozark Casino Resort Project",
             status="Pending", observation_status="proposed",
             observation_date="2025-07")
MEN = dict(project_id="MENOM-KENOSHA", tribe="Menominee Indian Tribe of Wisconsin",
           state="WI", decision_id="GLD-WI-menominee-indian-tribe-of-wisconsin-20260309",
           project_name="Menominee Indian Tribe of Wisconsin Kenosha Casino Project",
           status="Pending", observation_status="proposed",
           observation_date="2026-03")
DGP = dict(project_id="MENOM-KENOSHA-DGP-2013",
           tribe="Menominee Indian Tribe of Wisconsin", state="WI",
           decision_id="GLD-WI-menominee-indian-tribe-of-wisconsin-20260309",
           project_name="Menominee Kenosha Casino Project -- Dairyland Greyhound Park site (2013 ROD)",
           status="", observation_status="proposed", observation_date="2013")

T1 = []

# ---------------------------------------------------- Osage Lake Ozark ------
T1.append(t1(**OSAGE, source_document=doc("OSAGE_EA"), document_date="2025-07",
    alternative="Alternative A - Casino and Hotel", alternative_role="analyzed",
    record_type="ea_body_and_table",
    acres="29", gaming_sqft="40000", total_sqft="237160", machines="750",
    hotel_rooms="150", meeting_sqft="6000", parking="435",
    hours="24 hours a day, seven days a week",
    construction_start="2025 (assumed)", construction_duration="12 to 18 months",
    gaming_class="Class II",
    source_page="11; 15", source_page_label="7; (unnumbered table page)",
    table_ref="Table 2: Alternative A Components", source_url=url("OSAGE_EA"),
    value_completeness="construction_cost NOT disclosed; projected_opening NOT stated; tables (table games) not applicable -- Class II machines only",
    notes="Gaming floor 40,000 sf with 'up to 750 Class II gaming devices'; casino subtotal incl. BOH/FOH = 75,000 sf; hotel subtotal 120,330 sf; total of all components 237,160 sf. Meeting space 6,000 sf rooms plus 2,000 sf pre-function (recorded separately in Table 2). Parking 435 = 385 guest + 50 employee. Restaurant seats reported per venue only, no total (see calculated row in Table 2). Acreage conflict: the BIA Notice of Availability for this same EA states approximately 27.6 acres -- see Table 2 row."))

T1.append(t1(**OSAGE, source_document=doc("OSAGE_EA"), document_date="2025-07",
    alternative="Alternative B - Hotel with No Casino", alternative_role="analyzed",
    record_type="ea_body",
    acres="29", hotel_rooms="100", parking="150",
    source_page="20; 22", source_page_label="16; 18", source_url=url("OSAGE_EA"),
    value_completeness="no gaming component; total_sqft, meeting_sqft, construction cost/duration not quantified",
    notes="Non-gaming alternative: 100-room hotel with pool, fitness center and limited meeting space; approximately 150 parking stalls; approximately 6.1 acres impacted (vs 14.3 under Alternative A). Construction 'would commence in 2025' but a duration is not given."))

T1.append(t1(**OSAGE, source_document=doc("OSAGE_EA"), document_date="2025-07",
    alternative="Alternative C - No Action", alternative_role="analyzed",
    record_type="ea_body", source_page="20", source_page_label="16",
    source_url=url("OSAGE_EA"), value_completeness="no development; no quantities by design",
    notes="Project Site would not be taken into trust and would remain in its current state."))

for alt, note in [
    ("Reduced Intensity Alternative",
     "Rejected: a less intensive development 'would not be economically feasible'; a casino of a certain size is necessary to offset fixed costs; Alternative B already serves as a reduced-intensity case. No quantities given."),
    ("Increased Intensity Alternative",
     "Rejected: the Economic and Fiscal Impact Study (Appendix C, NOT posted) 'determined that Alternative A was of sufficient size to meet the Nation's economic development needs'. No quantities given."),
    ("Class III Gaming Facility",
     "Rejected: would require a tribal-state compact with Missouri; Class II requires only an NIGC-approved tribal ordinance. No quantities given."),
    ("Off-Site Development",
     "Rejected: the Nation owns no other land in the vicinity; acquiring more land would place an undue financial burden. No quantities given."),
]:
    T1.append(t1(**OSAGE, source_document=doc("OSAGE_EA"), document_date="2025-07",
        alternative=alt, alternative_role="eliminated_from_consideration",
        record_type="ea_body", source_page="22", source_page_label="18",
        source_url=url("OSAGE_EA"), value_completeness="named but unquantified in the EA",
        notes=note))

# ------------------------------------------------- Menominee Kenosha --------
T1.append(t1(**MEN, source_document=doc("MEN_EA"), document_date="2026-03",
    alternative="Alternative A - Casino and Hotel", alternative_role="analyzed",
    record_type="ea_body",
    acres="59", gaming_sqft="70000", total_sqft="346000", machines="1500",
    tables="55", table_game_seats="330", hotel_rooms="150", parking="2400",
    entertainment_sqft="33000", entertainment_seats="2000",
    hours="24 hours a day, seven days a week",
    construction_duration="approximately 18 months",
    construction_start="after the land has been taken into trust",
    gaming_class="Class III",
    source_page="15", source_page_label="10", source_url=url("MEN_EA"),
    value_completeness="construction_cost not in EA body (it is in Appendix SOCIO); projected_opening not stated",
    notes="EA body states 'a casino of up to 95,000 square feet' and 'gross footprint of up to approximately 346,000 square feet'. Appendix PROJ DESC Table 1 gives casino subtotal 106,000 sf and total 358,350 sf for the same alternative -- CONFLICT, both preserved as separate rows. Hard Rock Live 'up to approximately 33,000 sf', 2,000 seats, ballroom seating up to approximately 600. Hotel tower up to 75 ft (Kenosha Regional Airport height restriction)."))

T1.append(t1(**MEN, source_document=doc("MEN_PROJDESC"), document_date="2026-03",
    alternative="Alternative A - Casino and Hotel", alternative_role="analyzed",
    record_type="ea_appendix_program",
    gaming_sqft="70000", total_sqft="358350", machines="1500", tables="55",
    table_game_seats="330", hotel_rooms="150", restaurant_seats="750",
    parking="2400", entertainment_sqft="33000", entertainment_seats="2000",
    gaming_class="Class III",
    source_page="2", source_page_label="1",
    table_ref="Table 1: Alternative A Components (Source: Hard Rock, 2024)",
    source_url=url("MEN_PROJDESC"),
    value_completeness="acres/hours/construction not in this appendix",
    notes="Casino subtotal 106,000 sf (gaming floor 70,000 + BOH 26,000 + FOH 10,000); hotel subtotal 189,300 sf (tower 164,300 + BOH 25,000); Hard Rock Live subtotal 33,000 sf (house 23,000 + pre-function 7,000 + restrooms 3,000); F&B subtotal 28,800 sf / 750 seats (7 restaurant venues 650 seats + 3 bar/cafe venues 100 seats); retail 1,250 sf; parking 788,000 sf / 2,400 spaces. Ballroom/convention is stated as included in Hard Rock Live seating, so meeting_sqft is left blank rather than double-counted."))

T1.append(t1(**dict(MEN, observation_status="approved", observation_date="2024-01-03"),
    source_document=doc("MEN_IGA"), document_date="2024-01-03",
    alternative="Alternative A - Casino and Hotel", alternative_role="analyzed",
    record_type="iga_exhibit_program",
    acres="60", gaming_sqft="70000", machines="1500", tables="55",
    hotel_rooms="150", meeting_sqft="18375", parking="2375",
    entertainment_sqft="22000", entertainment_seats="2000",
    restaurant_seats="752", gaming_class="Class III",
    source_page="91-93", source_page_label="Exhibit E",
    table_ref="City of Kenosha Intergovernmental Agreement, Exhibit E, Table 1 -- 'current approved concept program'",
    source_url=url("MEN_IGA"),
    value_completeness="total_sqft not given as a single figure in this exhibit",
    notes="This is the concept program the City of Kenosha actually contracted to on 2024-01-03 and is therefore recorded as observation_status=approved (approved by the counterparty government, NOT by BIA). 'approximately 60 acres' here vs 59 acres in the EA. 70,000 sf covers 'Gaming Areas AND Support Areas' -- narrower than the EA's 70,000 sf gaming floor alone. Hotel = 31 suites + 119 standard rooms. Ballroom and support space 18,375 sf, 567 seats. Hard Rock Live 22,000 sf enclosed, 2,000 seats. restaurant_seats 752 is the SUM of the five named F&B venues (Hard Rock Cafe 150, Marketplace/Buffet 250, Steakhouse 87, Asian 95, Other F&B 170) -- the exhibit gives no total; see the calculated row in Table 2."))

T1.append(t1(**dict(MEN, observation_date="2023-11-01"),
    source_document=doc("MEN_SOCIO"), document_date="2023-11-01",
    alternative="Alternative A - Casino and Hotel", alternative_role="analyzed",
    record_type="impact_study_assumption",
    machines="1500", tables="55", hotel_rooms="150", meeting_sqft="8509",
    restaurant_seats="782", parking="2375", entertainment_sqft="22000",
    entertainment_seats="2000", construction_cost="360000000",
    construction_duration="18 months", gaming_class="Class III",
    source_page="8-9", source_page_label="3-4",
    table_ref="ASSUMPTIONS section", source_url=url("MEN_SOCIO"),
    value_completeness="acres/gaming_sqft/total_sqft not stated in the assumption set",
    notes="These are the FACILITY ASSUMPTIONS of the KlasRobinson Q.E.D. economic impact study (Nov 2023), not the EA's proposed program -- they differ and are kept separate. 150 keys incl. 31 suites = 232 room modules, average module 402.3 sf; outdoor pool; 1,280 sf fitness center; 8,509 sf ballroom + 5,207 sf pre-function; 22,000 sf Hard Rock Live for 2,000 concert seats; 7 restaurants 675 seats; 3 bars 107 seats (restaurant_seats 782 = 675 + 107, a Cedar Press sum -- see calculated row in Table 2); 1,000 sf gift retail; surface parking 2,375. No poker tables assumed. construction_cost 360,000,000 is 'total new development cost' (hard construction cost 232,200,000 -- see Table 2)."))

T1.append(t1(**MEN, source_document=doc("MEN_PROJDESC"), document_date="2026-03",
    alternative="Alternative B - Reduced Intensity Alternative", alternative_role="analyzed",
    record_type="ea_appendix_program",
    acres="59", gaming_sqft="30000", total_sqft="256000", machines="750",
    tables="30", table_game_seats="95", hotel_rooms="150",
    restaurant_seats="500", parking="1900",
    hours="24 hours a day, seven days a week",
    construction_duration="approximately 18 months", gaming_class="Class III",
    source_page="3", source_page_label="2",
    table_ref="Table 2: Alternative B - Reduced Intensity Alternative",
    source_url=url("MEN_PROJDESC"),
    value_completeness="construction_cost and projected_opening not stated",
    notes="Casino subtotal 48,000 sf (gaming floor 30,000 + BOH 13,000 + FOH 5,000). The EA body (p.22, printed 17) describes this as 'a casino of up to 48,000 square feet' -- i.e. the body quotes the casino SUBTOTAL where the appendix quotes a 30,000 sf gaming floor. gaming_sqft here is the appendix's gaming-floor figure. No Hard Rock Live and no ballroom under this alternative. Hotel identical to Alternative A (189,300 sf, 150 rooms)."))

T1.append(t1(**MEN, source_document=doc("MEN_PROJDESC"), document_date="2026-03",
    alternative="Alternative C - Non-Gaming Alternative", alternative_role="analyzed",
    record_type="ea_appendix_program",
    acres="59", total_sqft="326250", hotel_rooms="150", meeting_sqft="126000",
    restaurant_seats="250", parking="1400",
    source_page="3-4", source_page_label="2-3",
    table_ref="Table 3: Alternative C - Non-Gaming Alternative",
    source_url=url("MEN_PROJDESC"),
    value_completeness="no gaming component",
    notes="Hotel subtotal 304,000 sf (tower 164,000 + pool/fitness 1,500 + BOH/amenities/support 138,500); F&B 22,150 sf, one restaurant venue 250 seats plus bar and coffee shop with no seat counts; total 326,250 sf; parking 458,000 sf / 1,400 spaces. meeting_sqft 126,000 comes from the EA BODY (p.23, printed 18: 'a conference ballroom/meeting space of up to approximately 126,000 square feet') -- the appendix table has no meeting-space line and instead carries 138,500 sf of 'BOH, Amenities and Support'. Appendix TIA models this alternative as a 126,000 sf convention center, which corroborates the body."))

T1.append(t1(**MEN, source_document=doc("MEN_EA"), document_date="2026-03",
    alternative="Alternative D - No Action", alternative_role="analyzed",
    record_type="ea_body", source_page="23", source_page_label="18",
    source_url=url("MEN_EA"), value_completeness="no development; no quantities by design",
    notes="Project Site would not be placed into trust and would remain in its current undeveloped state."))

for alt, pg, note in [
    ("Big-Box Retail", "25",
     "Rejected: less likely to be economically feasible given the abundance of existing big-box retail in the greater Kenosha area, and redundant with the non-gaming Alternative C. No quantities given."),
    ("Off-Site Development", "25",
     "Rejected: other suitable parcels in the vicinity were generally unavailable for acquisition. No quantities given."),
]:
    T1.append(t1(**MEN, source_document=doc("MEN_EA"), document_date="2026-03",
        alternative=alt, alternative_role="eliminated_from_consideration",
        record_type="ea_body", source_page=pg, source_page_label="20",
        source_url=url("MEN_EA"), value_completeness="named but unquantified in the EA",
        notes=note))

# ------------------- the 2013 ROD project, as summarized in the 2026 EA ------
T1.append(t1(**DGP, source_document=doc("MEN_EA"), document_date="2026-03",
    alternative="A - Casino & Hotel (2013 ROD)", alternative_role="analyzed",
    record_type="prior_decision_summary_in_ea",
    acres="223", gaming_sqft="107300", hotel_rooms="400",
    entertainment_seats="5000",
    source_page="24-25", source_page_label="19-20",
    table_ref="Table 3: Comparison of Alternatives Between the Current EA and 2013 ROD",
    source_url=url("MEN_EA"),
    value_completeness="summary line only -- machines, tables, parking, cost not given",
    notes="SECOND-HAND: this is the 2026 EA's one-line summary of the 2013 Record of Decision for the Dairyland Greyhound Park site. The 2013 ROD/FEIS itself was NOT retrieved in this pilot and must be extracted directly before these figures are treated as primary. Site is a different 223-acre parcel about half a mile east of I-94. Future expansion (water park, RV park) noted without quantities."))

T1.append(t1(**DGP, source_document=doc("MEN_EA"), document_date="2026-03",
    alternative="B - Reduced Intensity (2013 ROD)", alternative_role="analyzed",
    record_type="prior_decision_summary_in_ea",
    gaming_sqft="37600",
    source_page="25", source_page_label="20",
    table_ref="Table 3: Comparison of Alternatives Between the Current EA and 2013 ROD",
    source_url=url("MEN_EA"), value_completeness="summary line only",
    notes="SECOND-HAND (see Alternative A row). Interim casino using the existing Dairyland Greyhound Park clubhouse, limited gaming, no new hotel or entertainment venue."))

T1.append(t1(**DGP, source_document=doc("MEN_EA"), document_date="2026-03",
    alternative="C - Non-Gaming / Keshena expansion (2013 ROD)", alternative_role="analyzed",
    record_type="prior_decision_summary_in_ea",
    gaming_sqft="39996", hotel_rooms="200",
    source_page="25", source_page_label="20",
    table_ref="Table 3: Comparison of Alternatives Between the Current EA and 2013 ROD",
    source_url=url("MEN_EA"), value_completeness="summary line only",
    notes="SECOND-HAND (see Alternative A row). DIFFERENT SITE: expansion of the Tribe's existing Menominee Casino Resort on reservation land in Keshena, WI (approx. 180 miles north of Kenosha), with a parking garage. Recorded here because the 2026 EA presents it as the 2013 ROD's Alternative C."))

# =============================================================== TABLE 2 =====
T2_COLS = [
    # --- schema as specified in GAMING_DATASET_PLAN.md ---
    "project_id", "metric", "value", "unit", "impact_type", "geography",
    "time_period", "reported_or_calculated", "source_document", "page",
    "table_ref", "confidence",
    # --- columns the pilot proved are needed ---
    "tribe", "alternative", "derivation", "observation_status",
    "modeling_basis", "page_label", "source_url", "notes",
]

def t2(**kw):
    bad = [k for k in kw if k not in T2_COLS and k != "_doc"]
    assert not bad, f"unknown T2 column(s): {bad}"
    r = {c: "" for c in T2_COLS}
    d = kw.pop("_doc")
    r.update(kw)
    r["source_document"] = doc(d); r["source_url"] = url(d)
    r.setdefault
    if not r["confidence"]: r["confidence"] = "high"
    if not r["observation_status"]: r["observation_status"] = "proposed"
    if not r["reported_or_calculated"]: r["reported_or_calculated"] = "reported"
    return r

T2 = []
O = dict(project_id="OSAGE-LAKEOZARK", tribe="The Osage Nation")
M = dict(project_id="MENOM-KENOSHA", tribe="Menominee Indian Tribe of Wisconsin")
ALT_A_O = "Alternative A - Casino and Hotel"
ALT_B_O = "Alternative B - Hotel with No Casino"
ALT_A_M = "Alternative A - Casino and Hotel"
ALT_B_M = "Alternative B - Reduced Intensity Alternative"
ALT_C_M = "Alternative C - Non-Gaming Alternative"

# ---- Osage: land ----
T2.append(t2(**O, _doc="OSAGE_NOA", metric="trust_acquisition_acres", value="27.6",
    unit="acres", impact_type="project_input", geography="Project Site",
    time_period="at acquisition", page="1", page_label="1", confidence="medium",
    notes="CONFLICT: the BIA Notice of Availability for this EA states 'approximately 27.6 acres'; the EA itself states 'approximately 29-acre Project Site' (EA p.8 and p.11) and 'approximately 29 acres' in the comparison of alternatives (p.20). Both are preserved; neither is corrected."))
T2.append(t2(**O, _doc="OSAGE_EA", metric="trust_acquisition_acres", value="29",
    unit="acres", impact_type="project_input", geography="Project Site",
    time_period="at acquisition", page="8; 11; 20", page_label="4; 7; 16",
    notes="See the conflicting 27.6-acre figure in the BIA Notice of Availability."))
T2.append(t2(**O, _doc="OSAGE_EA", metric="graded_area", value="14.3", unit="acres",
    impact_type="construction", geography="Project Site", alternative=ALT_A_O,
    time_period="construction", page="16", page_label="12", table_ref="Appendix B (not posted)"))
T2.append(t2(**O, _doc="OSAGE_EA", metric="new_impervious_surface", value="4.9",
    unit="acres", impact_type="construction", geography="Project Site",
    alternative=ALT_A_O, time_period="construction", page="16", page_label="12",
    notes="Total impervious surface after construction 7.9 acres."))
T2.append(t2(**O, _doc="OSAGE_EA", metric="impacted_area", value="6.1", unit="acres",
    impact_type="construction", geography="Project Site", alternative=ALT_B_O,
    time_period="construction", page="20", page_label="16"))

# ---- Osage: employment & output ----
T2.append(t2(**O, _doc="OSAGE_EA", metric="construction_jobs", value="1968",
    unit="full-time equivalent and temporary jobs", impact_type="construction",
    geography="Miller County and Camden County, MO", alternative=ALT_A_O,
    time_period="construction period", page="15", page_label="11",
    modeling_basis="Appendix C Economic and Fiscal Impact Study (NOT posted)"))
T2.append(t2(**O, _doc="OSAGE_EA", metric="construction_jobs", value="2176",
    unit="full-time and temporary jobs", impact_type="construction",
    geography="State of Missouri", alternative=ALT_A_O,
    time_period="construction period", page="15; 49", page_label="11; 45",
    modeling_basis="Appendix C Economic and Fiscal Impact Study (NOT posted)",
    notes="p.49 (printed 45) restates this as '2,176 new one-time construction jobs'."))
T2.append(t2(**O, _doc="OSAGE_EA", metric="operational_jobs", value="455",
    unit="full and part-time direct permanent jobs", impact_type="operational",
    geography="Miller County and Camden County, MO", alternative=ALT_A_O,
    time_period="stabilized operations", page="11", page_label="7",
    confidence="medium",
    modeling_basis="Appendix C Economic and Fiscal Impact Study (NOT posted)",
    notes="INTERNAL CONFLICT in the EA: p.11 (printed 7) calls 455 'full and part-time direct and permanent employment opportunities'; p.48 (printed 44) calls the same 455 'direct, indirect and induced jobs'; p.49 (printed 45) says 'approximately 455 of these jobs would occur in Miller and Camden counties' out of 510 permanent positions. Direct-vs-total is therefore ambiguous in the source and is not resolved here."))
T2.append(t2(**O, _doc="OSAGE_EA", metric="operational_jobs", value="510",
    unit="full and part-time direct permanent jobs", impact_type="operational",
    geography="State of Missouri", alternative=ALT_A_O,
    time_period="stabilized operations", page="11; 49", page_label="7; 45",
    modeling_basis="Appendix C Economic and Fiscal Impact Study (NOT posted)"))
T2.append(t2(**O, _doc="OSAGE_EA", metric="operational_jobs", value="41",
    unit="full-time jobs", impact_type="operational",
    geography="Miller County and Camden County, MO", alternative=ALT_B_O,
    time_period="operations", page="20; 70", page_label="16; 66",
    modeling_basis="Appendix C Economic and Fiscal Impact Study (NOT posted)"))
T2.append(t2(**O, _doc="OSAGE_EA", metric="operational_jobs", value="47",
    unit="full-time jobs", impact_type="operational", geography="State of Missouri",
    alternative=ALT_B_O, time_period="operations", page="20; 70", page_label="16; 66",
    modeling_basis="Appendix C Economic and Fiscal Impact Study (NOT posted)"))
T2.append(t2(**O, _doc="OSAGE_EA", metric="economic_output", value="100600000",
    unit="USD", impact_type="operational_modelled",
    geography="Miller County and Camden County, MO", alternative=ALT_A_O,
    time_period="first year of stabilized operations", page="46", page_label="42",
    modeling_basis="Appendix C Economic and Fiscal Impact Study (NOT posted); model not identified in the EA",
    notes="MODELLED OUTPUT, NOT GAMING REVENUE. The EA glosses output as '(i.e., revenues)', which is the consultant's phrasing for total economic output, not gaming win."))
T2.append(t2(**O, _doc="OSAGE_EA", metric="economic_output", value="117100000",
    unit="USD", impact_type="operational_modelled", geography="State of Missouri",
    alternative=ALT_A_O, time_period="first full year of stabilized operations",
    page="46", page_label="42",
    modeling_basis="Appendix C Economic and Fiscal Impact Study (NOT posted); model not identified in the EA",
    notes="MODELLED OUTPUT, NOT GAMING REVENUE."))
T2.append(t2(**O, _doc="OSAGE_EA", metric="economic_output", value="11300000",
    unit="USD", impact_type="operational_modelled",
    geography="Miller County and Camden County, MO", alternative=ALT_B_O,
    time_period="annual", page="70", page_label="66",
    modeling_basis="Appendix C Economic and Fiscal Impact Study (NOT posted)",
    notes="MODELLED OUTPUT, NOT GAMING REVENUE."))

# ---- Osage: fiscal & substitution ----
T2.append(t2(**O, _doc="OSAGE_EA", metric="property_tax_forgone", value="56840",
    unit="USD per year", impact_type="fiscal", geography="Miller County, MO",
    alternative=ALT_A_O, time_period="annual after trust acquisition",
    page="46", page_label="42",
    notes="EA states this equals approximately 0.5 percent of the Miller County budget; total FY2017 Miller County expenditures approximately $10.4 million (Missouri State Auditor, 2018). Applies identically to Alternative B (p.70)."))
T2.append(t2(**O, _doc="OSAGE_EA", metric="gaming_revenue_substitution", value="1800000",
    unit="USD", impact_type="substitution", geography="Isle of Capri Casino Hotel, Boonville, MO (approx. 72 miles north)",
    alternative=ALT_A_O, time_period="first full year of operations", page="48",
    page_label="44", modeling_basis="Appendix C (NOT posted)",
    notes="EA states effects decline to zero in subsequent years. The Isle of Capri Boonville is one of at least 52 Caesars Entertainment properties; Caesars net revenue approximately $9.6 billion for the year ended 2021-12-31."))
T2.append(t2(**O, _doc="OSAGE_EA", metric="hotel_room_night_displacement", value="9900",
    unit="room nights", impact_type="substitution",
    geography="competitive lodging properties, Lake Ozark market", alternative=ALT_A_O,
    time_period="first year of stabilized operations", page="48", page_label="44",
    modeling_basis="Appendix C (NOT posted)"))
T2.append(t2(**O, _doc="OSAGE_EA", metric="hotel_occupancy_reduction", value="1.5",
    unit="percentage points (market-wide)", impact_type="substitution",
    geography="competitive lodging properties, Lake Ozark market", alternative=ALT_A_O,
    time_period="first year of stabilized operations", page="48", page_label="44"))
T2.append(t2(**O, _doc="OSAGE_EA", metric="hotel_revenue_reduction", value="1100000",
    unit="USD per year", impact_type="substitution",
    geography="competitive lodging properties, Lake Ozark market", alternative=ALT_A_O,
    time_period="first year of stabilized operations", page="48", page_label="44",
    notes="EA also expresses this as a decrease of approximately 3 percent in annual revenue."))
T2.append(t2(**O, _doc="OSAGE_EA", metric="in_migrating_school_age_children", value="182",
    unit="children", impact_type="operational", geography="Miller County and Camden County, MO",
    alternative=ALT_A_O, time_period="stabilized operations", page="49", page_label="45",
    derivation="stated in source: 455 jobs x 40 percent in-migration assumption x 1 K-12 child per in-migrating household",
    notes="Reported in the EA but explicitly derived there from an assumption; equals 1.7 percent of the counties' approximately 11,000 school-age children."))

# ---- Osage: infrastructure & visitation ----
T2.append(t2(**O, _doc="OSAGE_EA", metric="water_demand", value="38153",
    unit="gallons per day", impact_type="infrastructure", geography="City of Lake Ozark municipal supply",
    alternative=ALT_A_O, time_period="average day, stabilized operations",
    page="58", page_label="54", table_ref="Table 26: Estimated Water and Wastewater Usage",
    modeling_basis="Montrose Environmental",
    notes="Table 26 cells as printed: casino 15,840 GPD, hotel 22,313 GPD, total 38,153 GPD; drivers 1,760 average daily patrons at 9 GPD/patron and 128 average daily occupied rooms at 175 GPD/room. The casino cell reproduces exactly (1,760 x 9 = 15,840); the HOTEL CELL DOES NOT (128 x 175 = 22,400, not 22,313). The table's own figures are recorded verbatim and the discrepancy is not corrected. The EA body rounds the total to 'approximately 38,000 gallons' (p.16, p.57) and states it is approximately 3.2 percent of the 1.2 MGD municipal capacity."))
T2.append(t2(**O, _doc="OSAGE_EA", metric="wastewater_generation", value="31445",
    unit="gallons per day", impact_type="infrastructure",
    geography="Lake Ozark/Osage Beach joint WWTP", alternative=ALT_A_O,
    time_period="average day, stabilized operations", page="58", page_label="54",
    table_ref="Table 26", modeling_basis="Montrose Environmental",
    notes="Table 26 cells as printed: casino 12,320 GPD, hotel 19,125 GPD, total 31,445 GPD; drivers 1,760 patrons at 7 GPD and 128 occupied rooms at 150 GPD. Casino reproduces (1,760 x 7 = 12,320); the HOTEL CELL DOES NOT (128 x 150 = 19,200, not 19,125). Recorded verbatim, not corrected. Body rounds the total to 'approximately 31,000 GPD' and states it is 1.0 percent of WWTP capacity (capacity approximately 3.0 MGD, 2020-21 average flows under 1.5 MGD)."))
T2.append(t2(**O, _doc="OSAGE_EA", metric="water_demand", value="14875",
    unit="gallons per day", impact_type="infrastructure", geography="City of Lake Ozark municipal supply",
    alternative=ALT_B_O, time_period="average day", page="58", page_label="54",
    table_ref="Table 26", notes="85 average daily occupied rooms x 175 GPD/room."))
T2.append(t2(**O, _doc="OSAGE_EA", metric="wastewater_generation", value="12750",
    unit="gallons per day", impact_type="infrastructure", geography="Lake Ozark/Osage Beach joint WWTP",
    alternative=ALT_B_O, time_period="average day", page="58", page_label="54",
    table_ref="Table 26", notes="85 average daily occupied rooms x 150 GPD/room."))
T2.append(t2(**O, _doc="OSAGE_EA", metric="average_daily_patrons", value="1760",
    unit="patrons per day", impact_type="operational", geography="Project Site",
    alternative=ALT_A_O, time_period="average day, stabilized operations",
    page="58", page_label="54", table_ref="Table 26",
    notes="Used in the EA only as a water/wastewater demand driver, but it is the single best public visitation figure for this project."))
T2.append(t2(**O, _doc="OSAGE_EA", metric="average_daily_occupied_rooms", value="128",
    unit="occupied rooms per day", impact_type="operational", geography="Project Site",
    alternative=ALT_A_O, time_period="average day, stabilized operations",
    page="58", page_label="54", table_ref="Table 26"))
T2.append(t2(**O, _doc="OSAGE_EA", metric="average_daily_occupied_rooms", value="85",
    unit="occupied rooms per day", impact_type="operational", geography="Project Site",
    alternative=ALT_B_O, time_period="average day", page="58", page_label="54",
    table_ref="Table 26"))
T2.append(t2(**O, _doc="OSAGE_EA", metric="daily_vehicle_trips", value="7448",
    unit="24-hour weekday trips", impact_type="traffic", geography="area roadways",
    alternative=ALT_A_O, time_period="opening year 2025", page="51; 62",
    page_label="47; 58", table_ref="Table 22: Trip Generation",
    modeling_basis="CJW Transportation Consultants, LLC, Transportation Impact Assessment (Appendix E, NOT posted)",
    notes="Trip rate applied to 750 slot machines. Peak hour: Friday 235 in / 208 out; Sunday 254 in / 226 out. Existing Osage Beach Parkway volume approximately 10,000 daily trips."))
T2.append(t2(**O, _doc="OSAGE_EA", metric="construction_worker_vehicle_trips", value="23",
    unit="trips per day (maximum)", impact_type="construction", geography="area roadways",
    alternative=ALT_A_O, time_period="construction", page="60", page_label="56",
    table_ref="Appendix G (not posted)",
    notes="Plus an estimated 10 material trips per day, converted in the EA to 100 passenger-car-equivalent hauling trips per day; total construction traffic given as 150 trips, a 1.5 percent increase on Osage Beach Parkway."))

# ---- Osage: Cedar Press calculated ----
T2.append(t2(**O, _doc="OSAGE_EA", metric="annual_visits", value="642400",
    unit="visits per year", impact_type="operational", geography="Project Site",
    alternative=ALT_A_O, time_period="stabilized operations year",
    reported_or_calculated="calculated", confidence="medium",
    derivation="1,760 average daily patrons (EA Table 26, p.58) x 365 days",
    page="58", page_label="54", table_ref="Table 26 (input)",
    notes="CEDAR PRESS CALCULATION -- this figure does not appear in the EA. It assumes 365 operating days at the stated average; the EA notes seasonal fluctuation in the Lake Ozark market, so the annual total is an order-of-magnitude figure, not a forecast."))
T2.append(t2(**O, _doc="OSAGE_EA", metric="implied_hotel_occupancy", value="85.3",
    unit="percent", impact_type="operational", geography="Project Site",
    alternative=ALT_A_O, time_period="stabilized operations",
    reported_or_calculated="calculated", confidence="medium",
    derivation="128 average daily occupied rooms (EA Table 26, p.58) / 150 hotel rooms (EA Table 2, p.15)",
    page="58; 15", page_label="54; (table page)", table_ref="Table 26 and Table 2 (inputs)",
    notes="CEDAR PRESS CALCULATION -- an implied occupancy rate is never stated in the EA."))
T2.append(t2(**O, _doc="OSAGE_EA", metric="implied_hotel_occupancy", value="85.0",
    unit="percent", impact_type="operational", geography="Project Site",
    alternative=ALT_B_O, time_period="operations",
    reported_or_calculated="calculated", confidence="medium",
    derivation="85 average daily occupied rooms (EA Table 26, p.58) / 100 hotel rooms (EA p.20)",
    page="58; 20", page_label="54; 16", table_ref="Table 26 (input)",
    notes="CEDAR PRESS CALCULATION."))
T2.append(t2(**O, _doc="OSAGE_EA", metric="food_and_beverage_seats_total", value="264",
    unit="seats", impact_type="project_input", geography="Project Site",
    alternative=ALT_A_O, time_period="at opening",
    reported_or_calculated="calculated", confidence="high",
    derivation="60 sports bar + 150 casual restaurant dining + 24 casual restaurant bar + 30 bistro/snack bar (EA Table 2, p.15)",
    page="15", page_label="(table page)", table_ref="Table 2: Alternative A Components (inputs)",
    notes="CEDAR PRESS SUM -- the EA reports seats per venue only and gives no total. Center bar/casino lounge and hotel pool bar seats are listed as 'TBD' and are therefore excluded, so 264 is a lower bound."))

# ---- Menominee: land / infrastructure (EA) ----
T2.append(t2(**M, _doc="MEN_EA", metric="trust_acquisition_acres", value="59",
    unit="acres", impact_type="project_input", geography="Project Site (4 parcels)",
    time_period="at acquisition", page="7; 15", page_label="2; 10",
    notes="The City of Kenosha Intergovernmental Agreement Exhibit E (2024-01-03) says 'approximately 60 acres' for the same transfer -- see Table 1."))
T2.append(t2(**M, _doc="MEN_EA", metric="graded_area", value="53.5", unit="acres",
    impact_type="construction", geography="Project Site",
    alternative="Alternatives A, B and C", time_period="construction",
    page="17; 23", page_label="12; 18", table_ref="Appendix GRADE",
    notes="Up to 70 percent of the graded area would be impervious surface. Detention capacity up to approximately 4.63 acre-feet across three above-ground basins and one underground system."))
T2.append(t2(**M, _doc="MEN_EA", metric="water_demand", value="115000",
    unit="gallons per day", impact_type="infrastructure", geography="Kenosha Water Utility",
    alternative=ALT_A_M, time_period="stabilized operations", page="16; 50",
    page_label="11; 45", table_ref="Appendix GRADE",
    modeling_basis="Eriksson Engineering Associates, LTD. (Water and Wastewater Study)",
    notes="EA also expresses this as approximately 42 million gallons per year and approximately 0.27 percent of KWU's 42 MGD capacity (peak flows approximately 27 MGD)."))
T2.append(t2(**M, _doc="MEN_EA", metric="wastewater_generation", value="113000",
    unit="gallons per day", impact_type="infrastructure", geography="Kenosha WWTP",
    alternative=ALT_A_M, time_period="stabilized operations", page="16; 50",
    page_label="11; 45", table_ref="Appendix GRADE",
    modeling_basis="Eriksson Engineering Associates, LTD.",
    notes="Stated as 0.4 percent of Kenosha WWTP capacity; WWTP average flows approximately 19.6 MGD against 28.6 MGD capacity."))
T2.append(t2(**M, _doc="MEN_EA", metric="wastewater_generation", value="74000",
    unit="gallons per day", impact_type="infrastructure", geography="Kenosha WWTP",
    alternative=ALT_B_M, time_period="operations", page="22; 51", page_label="17; 46",
    table_ref="Appendix GRADE"))

# ---- Menominee: traffic (EA Tables 12/14/15) ----
for alt, tab, pg, raw, linked, new, casino, cas_pos in [
    (ALT_A_M, "Table 12: Trip Generation - Alternative A", "44", "19960", "2400", "17560", "14660", "1830"),
    (ALT_B_M, "Table 14: Trip Generation - Alternative B", "45", "9625", "1815", "7810", "6770", "845"),
    (ALT_C_M, "Table 15: Trip Generation - Alternative C", "46", "2580", "600", "1980", "", ""),
]:
    T2.append(t2(**M, _doc="MEN_EA", metric="daily_vehicle_trips_new", value=new,
        unit="weekday two-way trips", impact_type="traffic", geography="area roadways",
        alternative=alt, time_period="base year 2028", page=pg,
        page_label=str(int(pg) - 5), table_ref=tab,
        modeling_basis="MSA Professional Services, Inc., Traffic Impact Analysis (Appendix TIA)",
        notes=f"Raw trips {raw}; linked (internal-capture) trips ({linked}); total new trips {new}." +
              (f" Casino component {casino} weekday trips on {cas_pos} gaming positions." if casino else "")))
T2.append(t2(**M, _doc="MEN_EA", metric="gaming_positions", value="1830", unit="positions",
    impact_type="project_input", geography="Project Site", alternative=ALT_A_M,
    time_period="at opening", page="44", page_label="39", table_ref="Table 12",
    notes="Used as the traffic model's casino size variable. Equals 1,500 slot machines + 330 table game seats. Appendix SOCIO independently states 1,885 gaming positions (1,500 machines + 55 tables counted differently) -- see that row."))
T2.append(t2(**M, _doc="MEN_EA", metric="gaming_positions", value="845", unit="positions",
    impact_type="project_input", geography="Project Site", alternative=ALT_B_M,
    time_period="at opening", page="45", page_label="40", table_ref="Table 14",
    notes="750 slot machines + 95 table game seats."))

# ---- Menominee: employment (EA body) ----
T2.append(t2(**M, _doc="MEN_EA", metric="construction_jobs", value="975",
    unit="temporary jobs", impact_type="construction", geography="not specified in EA body",
    alternative=ALT_A_M, time_period="18-month construction period", page="16",
    page_label="11", modeling_basis="Appendix SOCIO (KlasRobinson Q.E.D., Nov 2023)"))
T2.append(t2(**M, _doc="MEN_EA", metric="operational_jobs_direct", value="1075",
    unit="direct permanent jobs", impact_type="operational", geography="Project Site",
    alternative=ALT_A_M, time_period="stabilized operations", page="16", page_label="11",
    modeling_basis="Appendix SOCIO (KlasRobinson Q.E.D., Nov 2023)"))
T2.append(t2(**M, _doc="MEN_EA", metric="operational_jobs_indirect_induced", value="640",
    unit="jobs", impact_type="operational_modelled", geography="Kenosha County, WI",
    alternative=ALT_A_M, time_period="stabilized operations", page="16", page_label="11",
    modeling_basis="IMPLAN via KlasRobinson Q.E.D. (Appendix SOCIO)"))
T2.append(t2(**M, _doc="MEN_EA", metric="operational_jobs_total", value="1715",
    unit="full and part-time permanent jobs", impact_type="operational_modelled",
    geography="Kenosha County, WI", alternative=ALT_A_M,
    time_period="stabilized operations", page="16", page_label="11",
    modeling_basis="IMPLAN via KlasRobinson Q.E.D. (Appendix SOCIO)"))
T2.append(t2(**M, _doc="MEN_ENVANA", metric="annual_hotel_guests", value="27000",
    unit="guests per year", impact_type="operational", geography="Project Site",
    alternative=ALT_C_M, time_period="annual", page="30", page_label="29",
    derivation="stated in source: 150 hotel rooms at an assumed approximately 50 percent occupancy",
    notes="Reported in the appendix but explicitly derived there from an assumed occupancy rate."))

# ---- Menominee: KlasRobinson economic impact study ----
S = dict(**M, _doc="MEN_SOCIO", alternative=ALT_A_M,
         modeling_basis="KlasRobinson Q.E.D., IMPLAN model; inputs from KlasRobinson's own November 2023 Feasibility Study (NOT posted)")
T2.append(t2(**S, metric="total_development_cost", value="360000000", unit="USD",
    impact_type="construction", geography="Project Site", time_period="one-time",
    page="13", page_label="8"))
T2.append(t2(**S, metric="hard_construction_cost", value="232200000", unit="USD",
    impact_type="construction", geography="Project Site", time_period="one-time",
    page="13", page_label="8"))
T2.append(t2(**S, metric="construction_payroll", value="104500000", unit="USD",
    impact_type="construction", geography="Project Site", time_period="one-time",
    page="13", page_label="8"))
T2.append(t2(**S, metric="construction_jobs", value="975", unit="full-time equivalent jobs",
    impact_type="construction", geography="Project Site", time_period="18-month construction period",
    page="11; 13", page_label="6; 8"))
T2.append(t2(**S, metric="operational_jobs_direct", value="1075", unit="jobs",
    impact_type="operational", geography="Project Site", time_period="stabilized operations",
    page="13", page_label="8",
    notes="965 full-time (89.8 percent) and 110 part-time (10.2 percent), yielding 1,077 full-time equivalents. 399 jobs (37.1 percent) projected to be filled by minority employees; 788 (73.3 percent) by Kenosha County residents; 929 (86.4 percent) by Wisconsin residents."))
T2.append(t2(**S, metric="gaming_positions", value="1885", unit="positions",
    impact_type="project_input", geography="Project Site", time_period="at opening",
    page="13", page_label="8", confidence="medium",
    notes="Stated as '1,500 gaming machines and 55 table games'. Appendix TIA/EA Table 12 uses 1,830 positions (1,500 machines + 330 table game seats). The two appendices count table capacity differently; neither is corrected. Employee-to-position ratio 0.57 vs a regional range of 0.19-1.71, mean 0.62, median 0.68 for properties with 1,000+ positions."))
T2.append(t2(**S, metric="direct_employee_earnings", value="55050000", unit="USD per year",
    impact_type="operational", geography="Project Site", time_period="stabilized annual",
    page="11; 39", page_label="6; 34",
    notes="Executive summary states 'nearly $55.1 million' and average earnings of $54,000 per FTE; the impact table gives $55,050,000."))
T2.append(t2(**S, metric="payroll_related_taxes", value="20860000", unit="USD per year",
    impact_type="fiscal", geography="federal and State of Wisconsin",
    time_period="stabilized annual", page="18", page_label="13",
    table_ref="Annual Payroll Related Taxes",
    notes="Components: federal withholding $8,089,000; state withholding $2,753,000; Social Security employee-paid $4,211,000 and employer-paid $4,211,000; Medicare employee-paid $798,000 and employer-paid $798,000."))
T2.append(t2(**S, metric="employee_benefits", value="9900000", unit="USD per year",
    impact_type="operational", geography="Project Site", time_period="stabilized annual",
    page="18", page_label="13"))
T2.append(t2(**S, metric="purchases_of_goods_and_services", value="50700000",
    unit="USD per year", impact_type="operational", geography="all vendors",
    time_period="stabilized annual", page="20", page_label="15",
    notes="Of which more than $28.5 million from in-state vendors. Largest disclosed categories: advertising and promotion $10,720,000; food and beverage $6,998,000; gaming supplies $5,507,000 (entirely out-of-state)."))
T2.append(t2(**S, metric="annual_visits", value="2443400", unit="visits per year",
    impact_type="operational", geography="Project Site", time_period="stabilized annual",
    page="11; 23", page_label="6; 18",
    notes="The study also states 'an average of almost 6,995 visits per day' (p.23). 2,443,400 / 365 = 6,694, so the stated daily figure is not the annual figure divided by 365 -- see the Cedar Press calculated row."))
T2.append(t2(**S, metric="annual_visits_by_origin", value="213800", unit="visits per year",
    impact_type="operational", geography="Kenosha County, WI", time_period="stabilized annual",
    page="23", page_label="18", table_ref="Estimated Visitor Origins",
    notes="8.8 percent of total visits."))
T2.append(t2(**S, metric="annual_visits_by_origin", value="739100", unit="visits per year",
    impact_type="operational", geography="Wisconsin excluding Kenosha County",
    time_period="stabilized annual", page="23", page_label="18",
    table_ref="Estimated Visitor Origins", notes="30.2 percent of total visits."))
T2.append(t2(**S, metric="annual_visits_by_origin", value="1490500", unit="visits per year",
    impact_type="operational", geography="outside Wisconsin", time_period="stabilized annual",
    page="23", page_label="18", table_ref="Estimated Visitor Origins", confidence="medium",
    notes="61.0 percent of total visits. INTERNAL CONFLICT: the study's executive summary (p.11, printed 6) states 'almost 1,623,000 annual visits from outside of Wisconsin', and a chart label on p.24 reads 1,622,900. The three table components sum exactly to the 2,443,400 total, so the table is internally consistent and the executive-summary figure is the outlier; neither is corrected."))
T2.append(t2(**S, metric="direct_spending", value="276250000", unit="USD per year",
    impact_type="operational_modelled", geography="Project Site", time_period="stabilized annual",
    page="34; 39", page_label="29; 34", table_ref="Total Spending by Source",
    notes="By origin: Kenosha County $18,129,400 (6.6 percent); other Wisconsin $86,070,450 (31.2 percent); outside Wisconsin $172,049,800 (62.3 percent). This equals the study's Year 3 'Total Kenosha Revenue' line."))
for yr, tot, pot, hoch, new in [
    ("Year 1", "258890000", "21635575", "649067", "236605358"),
    ("Year 2", "267260000", "17868048", "357361", "249034591"),
    ("Year 3", "276250000", "13851816", "69259", "262328925"),
    ("Year 4", "284540000", "9511664", "0", "275028336"),
    ("Year 5", "293080000", "7347855", "0", "285732145"),
]:
    T2.append(t2(**S, metric="projected_property_revenue", value=tot, unit="USD",
        impact_type="operational_modelled", geography="Project Site", time_period=yr,
        page="38", page_label="33", table_ref="Projected Competitive Gaming Impact",
        notes="CONSULTANT PROJECTION, not observed revenue, and not a disclosure of gaming win by any operating facility. Reproduced in the EA as Appendix ENV ANA Table ENV ANA-20."))
    T2.append(t2(**S, metric="gaming_revenue_substitution", value=pot, unit="USD",
        impact_type="substitution", geography="Potawatomi Hotel & Casino, Milwaukee, WI",
        time_period=yr, page="38", page_label="33",
        table_ref="Projected Competitive Gaming Impact",
        notes="Revenue projected to be captured FROM the named competitor."))
    T2.append(t2(**S, metric="gaming_revenue_substitution", value=hoch, unit="USD",
        impact_type="substitution", geography="Ho-Chunk Gaming Madison, WI (Class II)",
        time_period=yr, page="38", page_label="33",
        table_ref="Projected Competitive Gaming Impact"))
    T2.append(t2(**S, metric="net_new_revenue", value=new, unit="USD",
        impact_type="operational_modelled", geography="Project Site", time_period=yr,
        page="38", page_label="33", table_ref="Projected Competitive Gaming Impact",
        notes="Total projected revenue less capture from Wisconsin competitors; includes capture from Illinois."))
T2.append(t2(**S, metric="non_gaming_substitution", value="2100000", unit="USD per year",
    impact_type="substitution", geography="Kenosha County and Wisconsin non-gaming businesses",
    time_period="stabilized annual", page="37", page_label="32",
    notes="Stated as an assumed additional 0.8 percent of new spending substituted from restaurants, bars, hotels, retail and entertainment. This is an ASSUMPTION of the study, not an estimate derived from data."))
for geo, out_d, out_i, out_ind, out_t, emp_d, emp_i, emp_ind, emp_t, ea_d, ea_i, ea_ind, ea_t, kind, pg, lbl in [
    ("Kenosha County, WI", "276250000", "57130000", "18800000", "352180000", "1075", "509", "131", "1715",
     "55050000", "20140000", "6140000", "81330000", "full", "39", "34"),
    ("State of Wisconsin", "276250000", "122930000", "93130000", "492310000", "1075", "725", "545", "2345",
     "55050000", "43880000", "30210000", "129140000", "full", "39", "34"),
    ("Kenosha County, WI", "260247900", "53820700", "17711000", "331779600", "1013", "480", "123", "1616",
     "51861200", "18973400", "5784300", "76618900", "net", "40", "35"),
    ("State of Wisconsin", "260247900", "115809100", "87735300", "463792300", "1013", "683", "513", "2209",
     "51861200", "41338200", "28460100", "", "net", "40", "35"),
]:
    tab = ("Projected Full Economic Impact" if kind == "full" else "Projected Net Economic Impact")
    T2.append(t2(**S, metric=f"economic_output_{kind}", value=out_t, unit="USD per year",
        impact_type="operational_modelled", geography=geo, time_period="stabilized annual",
        page=pg, page_label=lbl, table_ref=tab,
        notes=f"MODELLED OUTPUT, NOT GAMING REVENUE. Direct {out_d} + indirect {out_i} + induced {out_ind}."
              + (" Net figures deduct spending sourced from within the geography, competitive capture and substitution." if kind == "net" else "")))
    T2.append(t2(**S, metric=f"employment_{kind}", value=emp_t, unit="jobs",
        impact_type="operational_modelled", geography=geo, time_period="stabilized annual",
        page=pg, page_label=lbl, table_ref=tab,
        notes=f"Direct {emp_d} + indirect {emp_i} + induced {emp_ind}."))
    if ea_t:
        T2.append(t2(**S, metric=f"earnings_{kind}", value=ea_t, unit="USD per year",
            impact_type="operational_modelled", geography=geo, time_period="stabilized annual",
            page=pg, page_label=lbl, table_ref=tab,
            notes=f"Direct {ea_d} + indirect {ea_i} + induced {ea_ind}."))
    else:
        T2.append(t2(**S, metric=f"earnings_{kind}", value="", unit="USD per year",
            impact_type="operational_modelled", geography=geo, time_period="stabilized annual",
            page=pg, page_label=lbl, table_ref=tab, confidence="low",
            notes=f"TOTAL NOT LEGIBLE in the retrieved PDF's text layer -- the Wisconsin net-earnings total row is cut off. Components read: direct {ea_d}, indirect {ea_i}, induced {ea_ind}. The executive summary (p.11) states net annual employee earnings of $76.6 million for Kenosha County and 'another $45.0 million for Wisconsin', which is a different (incremental) presentation. Left blank rather than summed."))
T2.append(t2(**S, metric="indirect_induced_sales_tax_revenue", value="10500000",
    unit="USD per year", impact_type="fiscal", geography="Wisconsin state and local governments",
    time_period="stabilized annual", page="42", page_label="37",
    notes="Approximately 35 percent projected to be collected in Kenosha County. Sales at the facility itself are not subject to state or local point-of-sale tax."))
for svc, amt in [("police", "1045700"), ("fire", "780600"), ("other_services", "481500"), ("total", "2307800")]:
    T2.append(t2(**S, metric=f"government_service_cost_{svc}", value=amt, unit="USD per year",
        impact_type="fiscal_cost", geography="City of Kenosha / local government",
        time_period="stabilized annual", page="43", page_label="38",
        table_ref="Estimated Impact on Government",
        notes="Reproduced in the EA as Appendix ENV ANA Table ENV ANA-19. This is the projected COST side of the fiscal analysis."))
T2.append(t2(**S, metric="human_services_expenditure_reduction", value="75000",
    unit="USD per year (low end of range)", impact_type="fiscal",
    geography="Kenosha County, WI", time_period="stabilized annual", page="43",
    page_label="38", confidence="low",
    notes="Study states a range of $75,000 to $125,000 per year and concedes the effect 'will not likely be large enough to separate out from year-to-year general economic and policy impacts'. Range recorded at both ends."))
T2.append(t2(**S, metric="human_services_expenditure_reduction", value="125000",
    unit="USD per year (high end of range)", impact_type="fiscal",
    geography="Kenosha County, WI", time_period="stabilized annual", page="43",
    page_label="38", confidence="low", notes="See low-end row."))
T2.append(t2(**S, metric="payments_to_government", value="26300000", unit="USD per year",
    impact_type="fiscal", geography="State of Wisconsin and local governments",
    time_period="stabilized annual", page="43", page_label="38",
    notes="Stated as 'payments totaling 11 percent of annual gaming revenue each year to state and local government, averaging over $26.3 million annually'. The 11 percent is the combined compact and IGA rate; the 4 percent IGA component is itemised in Table 3."))
T2.append(t2(**S, metric="new_housing_demand", value="190", unit="housing units",
    impact_type="operational", geography="Kenosha County, WI", time_period="over time",
    page="44", page_label="39", notes="Stated as less than 0.1 percent of total housing units."))
T2.append(t2(**S, metric="in_migrating_school_age_children", value="86", unit="children",
    impact_type="operational", geography="Kenosha County, WI", time_period="over time",
    page="44", page_label="39",
    notes="Against a county K-12 enrollment of 18,870, i.e. 0.5 percent."))

# ---- Menominee: ENV ANA fiscal ----
T2.append(t2(**M, _doc="MEN_ENVANA", metric="projected_net_win", value="259000000",
    unit="USD", impact_type="operational_modelled", geography="Project Site",
    alternative=ALT_A_M, time_period="first full year of operations", page="27",
    page_label="26", modeling_basis="Appendix SOCIO (KlasRobinson Q.E.D.)",
    notes="CONSULTANT PROJECTION. Rounded restatement of the Appendix SOCIO Year 1 figure of $258,890,000."))
T2.append(t2(**M, _doc="MEN_ENVANA", metric="iga_net_win_payments", value="10400000",
    unit="USD", impact_type="fiscal", geography="City of Kenosha and Kenosha County",
    alternative=ALT_A_M, time_period="first full year of operations", page="27",
    page_label="26",
    derivation="stated in source: 4 percent of Net Win (3 percent City + 1 percent County) x approximately $259 million projected Net Win",
    notes="Reported in the appendix but explicitly derived there. Excludes the fixed-dollar IGA payments itemised in Table 3."))
T2.append(t2(**M, _doc="MEN_ENVANA", metric="hotel_substitution", value="1000000",
    unit="USD", impact_type="substitution", geography="Kenosha County hotels",
    alternative=ALT_A_M, time_period="first full year of operations", page="28",
    page_label="27", confidence="low",
    derivation="stated in source: approximately half of the $2.1 million total local-business substitution estimate",
    notes="The appendix then estimates this as approximately 5 percent of county-wide hotel revenue, itself estimated at $22 million/year from approximately 1,200 Kenosha County rooms (2019) at an assumed $100 average daily rate and 50 percent occupancy. Every step after the $2.1 million is an assumption."))
T2.append(t2(**M, _doc="MEN_ENVANA", metric="hotel_substitution_share", value="12.5",
    unit="percent of county hotel rooms", impact_type="substitution",
    geography="Kenosha County hotels", alternative=ALT_C_M,
    time_period="first full year of operations", page="31", page_label="30",
    derivation="stated in source: 150 rooms / approximately 1,200 Kenosha County hotel rooms",
    notes="Under the non-gaming alternative the appendix expects LARGER hotel substitution than under the casino alternatives, because there would be no captive casino patronage."))
T2.append(t2(**M, _doc="MEN_ENVANA", metric="property_tax_forgone", value="0",
    unit="USD per year", impact_type="fiscal", geography="Kenosha County, WI",
    alternative="Alternatives A, B and C", time_period="annual after trust acquisition",
    page="26; 29; 31", page_label="25; 28; 30",
    notes="'Property taxes are not currently being assessed on the Project Site' -- the parcels are already tax-exempt, so trust acquisition removes nothing from the roll. Contrast Osage, where $56,840/yr comes off the Miller County roll. Do NOT generalise either case."))
T2.append(t2(**M, _doc="MEN_ENVANA", metric="host_public_safety_budget", value="49054545",
    unit="USD per year", impact_type="context", geography="City of Kenosha, WI",
    time_period="2022 budget", page="26", page_label="25",
    table_ref="Table ENV ANA-18: City of Kenosha 2022 Budget - Select Budget Items",
    observation_status="current",
    notes="Public safety total. Components: police $29,929,042; fire $13,580,807; joint services $4,173,836; city inspections $1,370,860. Plus EMS special revenue fund $9,360,092 and capital project funds (fire $4,983,300, police $333,000). Baseline for judging the $2,307,800 projected service cost."))

# ---- Menominee: Cedar Press calculated ----
T2.append(t2(**M, _doc="MEN_SOCIO", metric="implied_mean_daily_visits", value="6694",
    unit="visits per day", impact_type="operational", geography="Project Site",
    alternative=ALT_A_M, time_period="stabilized operations",
    reported_or_calculated="calculated", confidence="medium",
    derivation="2,443,400 annual visits (Appendix SOCIO p.23) / 365 days",
    page="23", page_label="18",
    notes="CEDAR PRESS CALCULATION. The study itself states 'an average of almost 6,995 visits per day' on the same page; that figure implies roughly 349 operating days rather than 365. The discrepancy is recorded, not resolved."))
T2.append(t2(**M, _doc="MEN_SOCIO", metric="implied_win_per_position_per_day", value="401.5",
    unit="USD per gaming position per day", impact_type="operational_modelled",
    geography="Project Site", alternative=ALT_A_M, time_period="Year 3 (stabilized)",
    reported_or_calculated="calculated", confidence="low",
    derivation="$276,250,000 Year 3 projected property revenue (Appendix SOCIO p.38) / 1,885 gaming positions (p.13) / 365 days",
    page="38; 13", page_label="33; 8",
    notes="CEDAR PRESS CALCULATION, offered only as a scale check. The numerator is TOTAL projected property revenue (gaming plus non-gaming), so this is NOT a win-per-unit-per-day statistic in the industry sense and must not be quoted as one."))
T2.append(t2(**M, _doc="MEN_SOCIO", metric="food_and_beverage_seats_total", value="782",
    unit="seats", impact_type="project_input", geography="Project Site",
    alternative=ALT_A_M, time_period="at opening",
    reported_or_calculated="calculated", confidence="high",
    derivation="675 restaurant seats across 7 venues + 107 bar seats across 3 bars (Appendix SOCIO p.9)",
    page="9", page_label="4",
    notes="CEDAR PRESS SUM of the impact study's assumption set. The EA's own Appendix PROJ DESC gives a reported total of 750 seats (650 restaurant + 100 bar) for the same alternative -- a 32-seat difference between the two documents."))
T2.append(t2(**M, _doc="MEN_IGA", metric="food_and_beverage_seats_total", value="752",
    unit="seats", impact_type="project_input", geography="Project Site",
    alternative=ALT_A_M, time_period="at opening",
    reported_or_calculated="calculated", confidence="high",
    observation_status="approved",
    derivation="Hard Rock Cafe 150 + Marketplace/Buffet 250 + Steakhouse 87 + Asian Restaurant 95 + Other F&B 170 (City IGA Exhibit E, p.92)",
    page="92", page_label="Exhibit E",
    notes="CEDAR PRESS SUM of the January 2024 City IGA's approved concept program. Three documents, three F&B seat counts for the same alternative: 750 (EA appendix), 752 (IGA exhibit), 782 (impact study)."))

# =============================================================== TABLE 3 =====
T3_COLS = [
    # --- schema as specified in GAMING_DATASET_PLAN.md ---
    "project_id", "counterparty_government", "service", "amount", "term",
    "effective_date", "source_document", "page",
    # --- columns the pilot proved are needed ---
    "tribe", "counterparty_type", "agreement_name", "section_ref",
    "amount_basis", "amount_value", "amount_unit", "agreement_status",
    "date_basis", "page_label", "source_url", "notes",
]

def t3(**kw):
    bad = [k for k in kw if k not in T3_COLS and k != "_doc"]
    assert not bad, f"unknown T3 column(s): {bad}"
    r = {c: "" for c in T3_COLS}
    d = kw.pop("_doc"); r.update(kw)
    r["source_document"] = doc(d); r["source_url"] = url(d)
    return r

T3 = []
OA = dict(project_id="OSAGE-LAKEOZARK", tribe="The Osage Nation")
MA = dict(project_id="MENOM-KENOSHA", tribe="Menominee Indian Tribe of Wisconsin")

# ---- Osage ----
T3.append(t3(**OA, _doc="OSAGE_EA",
    counterparty_government="Miller County Sheriff's Department, Missouri",
    counterparty_type="county law enforcement",
    agreement_name="Mutual Aid and Assistance Agreement",
    service="Emergency response services, incident control and other law enforcement services on request from the 911 system or from the Nation",
    amount="$50,000 per year", amount_basis="fixed_annual", amount_value="50000",
    amount_unit="USD per year",
    term="three years, commencing with the opening of a casino",
    effective_date="2023-09", date_basis="EA states the agreement was entered 'in September of 2023'; no day given",
    agreement_status="executed", page="46", page_label="42",
    section_ref="EA Section 3.2.6; Appendix D (NOT posted)",
    notes="The agreement text itself (Appendix D) is referenced in the EA but is not among the three documents BIA posted for this project, so the terms here are the EA's summary of it. The EA also notes this agreement 'only becomes effective upon the opening of a casino' and therefore does not apply to Alternative B (p.70)."))
T3.append(t3(**OA, _doc="OSAGE_EA",
    counterparty_government="City of Lake Ozark, Missouri",
    counterparty_type="municipality", agreement_name="(law enforcement services agreement)",
    service="Law enforcement services from the Lake Ozark Police Department",
    amount="", amount_basis="not_yet_agreed", term="", effective_date="",
    date_basis="none -- EA states the Nation and the City 'are in the process of negotiating'",
    agreement_status="under_negotiation", page="46", page_label="42",
    section_ref="EA Section 3.2.6",
    notes="No amount, rate or term disclosed. Section 4 mitigation requires the Nation to enter into 'one or more service agreements'."))
T3.append(t3(**OA, _doc="OSAGE_EA",
    counterparty_government="Lake Ozark Fire Protection District, Missouri",
    counterparty_type="special district", agreement_name="(fire and EMS agreement)",
    service="Fire protection and emergency medical services",
    amount="", amount_basis="not_yet_agreed", term="", effective_date="",
    date_basis="none -- 'in the process of negotiating'",
    agreement_status="under_negotiation", page="46", page_label="42",
    section_ref="EA Section 3.2.6",
    notes="District responded to over 1,700 calls for service in calendar year 2021. No amount disclosed."))
T3.append(t3(**OA, _doc="OSAGE_EA",
    counterparty_government="City of Lake Ozark, Missouri", counterparty_type="municipality",
    agreement_name="(water and wastewater service agreement)",
    service="Municipal water supply and wastewater treatment",
    amount="rate premium, unquantified", amount_basis="service_rate_premium",
    term="", effective_date="",
    date_basis="none -- tentative agreement reported, not executed",
    agreement_status="tentative_agreement", page="47", page_label="43",
    section_ref="EA Section 3.2.6",
    notes="EA: 'The parties have reached a tentative agreement whereby the Nation will be charged higher rates than what most commercial users pay for water and wastewater (Osage Nation, 2023).' No rate or differential is disclosed. Section 4 mitigation requires a service agreement compensating the City for the proportional cost of service."))
T3.append(t3(**OA, _doc="OSAGE_EA",
    counterparty_government="City of Lake Ozark, Missouri", counterparty_type="municipality",
    agreement_name="(mitigation measure, Section 4)",
    service="Install or fund a designated westbound right turn lane at Access P1 and Bagnell Dam Boulevard",
    amount="", amount_basis="in_kind_capital_works", term="", effective_date="",
    date_basis="none -- mitigation commitment, not a dated agreement",
    agreement_status="mitigation_measure", page="75", page_label="71",
    section_ref="EA Table 32: Mitigation Measures",
    notes="Cost not disclosed. Recommended for Alternative A only."))
T3.append(t3(**OA, _doc="OSAGE_EA", counterparty_government="(unnamed solid waste provider)",
    counterparty_type="private service provider", agreement_name="(solid waste service agreement)",
    service="Solid waste collection", amount="", amount_basis="not_yet_agreed",
    term="", effective_date="", date_basis="none",
    agreement_status="commitment_to_enter", page="58", page_label="54",
    section_ref="EA Section 3.2.9",
    notes="'The Nation would enter into a service agreement for solid waste services prior to operation of Alternative A.' Counterparty is a private hauler (GFL is named as the area collector), not a government."))

# ---- Menominee: City of Kenosha IGA ----
CITY = dict(**MA, _doc="MEN_IGA",
            counterparty_government="City of Kenosha, Wisconsin",
            counterparty_type="municipality",
            agreement_name="Intergovernmental Agreement -- City of Kenosha (Appendix IGA-1)",
            effective_date="2024-01-03",
            date_basis="agreement text: 'entered into this 3rd day of January 2024'; corroborated by the EA (p.10) and by Common Council proceedings of 2024-01-03 reproduced at Appendix IGA pp.99-103",
            agreement_status="executed")
T3.append(t3(**CITY, service="Payments to support local government operations (general)",
    amount="3 percent of Net Win", amount_basis="percent_of_net_win", amount_value="3",
    amount_unit="percent of Net Win",
    term="from establishment of the Federal Trust Land; parties must meet in Calendar Year 20 and every 10 years thereafter to discuss increases",
    page="8", page_label="3", section_ref="Section 2(A)(1)",
    notes="Net Win = total amount wagered less amounts paid out as prizes. Paid quarterly, within 30 days of quarter end. Late payments accrue 1.5 percent per month. Annual CPA audit of Net Win required, delivered to the City."))
T3.append(t3(**CITY, service="Minimum annual payment floor under the Net Win share",
    amount="$100,000 (CY1-CY2); $1,000,000 (CY3-CY8); $2,500,000 CPI-adjusted (CY9 onward)",
    amount_basis="minimum_annual", amount_value="2500000",
    amount_unit="USD per year from Calendar Year 9, CPI-U adjusted",
    term="Calendar Year 1 onward; CY1 prorated if trust acquisition occurs after 1 January",
    page="9-11", page_label="4-6", section_ref="Section 2(A)(2)-(3)",
    notes="Payable only to the extent the 3 percent Net Win payments fall short; due within 45 days of year end. amount_value carries the CY9+ figure; the earlier steps are in the amount text. Exhibit D (pp.87-89) gives worked illustrations."))
T3.append(t3(**CITY, service="Advanced life support vehicles",
    amount="$500,000 by close of Calendar Year 3 and $500,000 by close of Calendar Year 4",
    amount_basis="one_time", amount_value="1000000", amount_unit="USD total",
    term="Calendar Years 3 and 4", page="13", page_label="8", section_ref="Section 2(A)(6)"))
T3.append(t3(**CITY, service="Construction of a fire/police/public works outpost serving the facility area",
    amount="$500,000 annually", amount_basis="fixed_annual", amount_value="500000",
    amount_unit="USD per year",
    term="Calendar Year 3 through Calendar Year 8 (six payments)", page="13-14",
    page_label="8-9", section_ref="Section 2(A)(7)",
    notes="City must hold the contributions in a segregated account until used for the stated purpose."))
T3.append(t3(**CITY, service="Public museums trust fund and City homeownership program (charitable contribution)",
    amount="$500,000 annually", amount_basis="fixed_annual", amount_value="500000",
    amount_unit="USD per year",
    term="Calendar Year 3 through Calendar Year 12 (ten payments)", page="14-15",
    page_label="9-10", section_ref="Section 2(B)(1)",
    notes="Museum trust principal preserved, interest used to remove museum costs from the property tax levy."))
T3.append(t3(**CITY, service="Distribution to public schools located in the City",
    amount="$750,000, contingent", amount_basis="conditional_annual", amount_value="750000",
    amount_unit="USD per year when triggered",
    term="any Calendar Year in which Section 2(A)(1) Net Win payments exceed $2,000,000; paid within 90 days of year end",
    page="15", page_label="10", section_ref="Section 2(B)(2)",
    notes="One third to the school districts that had taxing jurisdiction over the land before it went into trust; two thirds to City school districts at the City's discretion."))
T3.append(t3(**dict(CITY, _doc="MEN_EA"),
    service="Sewer, water and stormwater service charges and infrastructure upgrade costs",
    amount="customary commercial charges plus project-related upgrade costs",
    amount_basis="service_charges_and_capital_costs", term="ongoing",
    page="10", page_label="5", section_ref="City IGA Section 2(K), as summarized in EA Section 1.6.2",
    notes="Amount not quantified anywhere in the retrieved documents. Recorded from the EA's summary of the IGA rather than from the agreement text, because the summary is where the commitment is stated in quantifiable terms."))
T3.append(t3(**CITY, service="Local and minority contractor bid preference",
    amount="3 percent bid preference", amount_basis="non_monetary_commitment",
    amount_value="3", amount_unit="percent price preference", term="ongoing",
    page="17", page_label="12", section_ref="Section 2(E)",
    notes="Preference of 3 percent over the lowest quoted price for bidders whose principal place of business is local. Paired with a 25 percent minority employment goal and Indian preference (Section 2(D), p.16)."))
T3.append(t3(**CITY, service="Exclusivity: City will not endorse or license any other Class III or casino-style gaming",
    amount="", amount_basis="non_monetary_commitment",
    term="for so long as the Tribe and the Authority conduct Class III gaming at the facility",
    page="7", page_label="2", section_ref="Section 1(D)",
    notes="A commitment BY the City TO the Tribe -- the reciprocal direction of this table's usual flow. Exclusivity is consideration for the payment stream above."))

# ---- Menominee: Kenosha County IGA ----
CTY = dict(**MA, _doc="MEN_IGA", counterparty_government="Kenosha County, Wisconsin",
           counterparty_type="county",
           agreement_name="Intergovernmental Agreement -- Kenosha County (Appendix IGA-2)",
           effective_date="2024-02",
           date_basis="EA (p.10) states 'In February of 2024'; the copy reproduced at Appendix IGA p.105 is an UNEXECUTED template reading 'this [DATE] day of [MONTH], 2023'. County Board Resolution No. 73 at p.201 is marked postponed to 2024-01-16.",
           agreement_status="executed_per_EA_appendix_copy_undated")
T3.append(t3(**CTY, service="Payments to support county government operations (general)",
    amount="1 percent of Net Win, rising to 1.33 percent from Calendar Year 9",
    amount_basis="percent_of_net_win", amount_value="1",
    amount_unit="percent of Net Win (1.33 percent from Calendar Year 9)",
    term="from establishment of the Federal Trust Land; renegotiation review in Calendar Year 20 and every 10 years thereafter",
    page="110", page_label="6", section_ref="Section 2.A.1",
    notes="Quarterly, 30 days after quarter end; 1.5 percent per month interest on late payments; annual CPA audit delivered to the County."))
T3.append(t3(**CTY, service="Minimum annual payment floor under the Net Win share",
    amount="$50,000 (CY1-CY2); $500,000 (CY3-CY8); $1,000,000 CPI-adjusted (CY9 onward)",
    amount_basis="minimum_annual", amount_value="1000000",
    amount_unit="USD per year from Calendar Year 9, CPI-U adjusted",
    term="Calendar Year 1 onward; CY1 prorated", page="110-112", page_label="6-8",
    section_ref="Section 2.A.2-3"))
T3.append(t3(**CTY, service="Debt service on a new county human services building",
    amount="$650,000 annually", amount_basis="fixed_annual", amount_value="650000",
    amount_unit="USD per year", term="Calendar Years 9 through 12 (four payments)",
    page="113", page_label="9", section_ref="Section 2.A.6"))
T3.append(t3(**CTY, service="Problem gambling assessment and treatment (match to county appropriation)",
    amount="$75,000 total (see note)", amount_basis="matching_capped",
    amount_value="75000", amount_unit="USD, total cap per the agreement text",
    term="any Calendar Year in which the County appropriates funds for problem gambling; paid within 90 days of appropriation or of commencement of gaming",
    page="113-114", page_label="9-10", section_ref="Section 2.A.7",
    notes="CONFLICT: the agreement text reads 'the Authority's commitment under this subsection (7) is limited to a total payment to the County of Seventy-Five Thousand Dollars ($75,000)'; the EA's summary (p.10) reads 'match Kenosha County expenditures up to $75,000 per year'. The agreement text is recorded here; the EA's per-year reading is preserved in this note. Misuse of the funds triggers treble repayment to the Authority."))
T3.append(t3(**CTY, service="Charitable organizations addressing cultural and charitable needs in the County",
    amount="minimum $850,000", amount_basis="minimum_cumulative", amount_value="850000",
    amount_unit="USD, cumulative minimum", term="within the first 12 Calendar Years",
    page="115", page_label="11", section_ref="Section 2.B",
    notes="Payments made by a contracted facility manager count toward this minimum."))
T3.append(t3(**CTY, service="Remittance of tribal sales tax collected in lieu of Wisconsin sales tax",
    amount="75 percent of tax collected (CY1-CY8), then 25 percent (CY9 onward)",
    amount_basis="share_of_tax", amount_value="75",
    amount_unit="percent of tribal sales tax collected (falls to 25 percent from Calendar Year 9)",
    term="for so long as the Tribe or Authority makes sales on the trust land subject to the tribal sales tax ordinance",
    page="188-189", page_label="32-33",
    section_ref="Exhibit F, Agreement Regarding Sales Tax, Section B",
    notes="County must ring-fence the funds for general infrastructure (roads, equipment, capital, highway debt service, broadband) and publish an annual use report. Comps and sales to Menominee tribal members are exempt from the tribal sales tax."))
T3.append(t3(**CTY, service="Exclusivity: County will not endorse any other Class III gaming facility",
    amount="", amount_basis="non_monetary_commitment", term="not stated in the retrieved text",
    page="109", page_label="5", section_ref="Section 1.D",
    notes="A commitment BY the County TO the Tribe."))

# ---- Menominee: tourism / room tax ----
T3.append(t3(**MA, _doc="MEN_IGA",
    counterparty_government="Kenosha Area Tourism Corporation (Kenosha Area Convention & Visitors Bureau)",
    counterparty_type="quasi-governmental tourism corporation (Wisconsin Chapter 181 non-stock non-profit)",
    agreement_name="Agreement Regarding Tourism Promotion and Room Tax (Appendix IGA-3)",
    service="Convention and leisure tourism promotion, marketing, visitor services and public relations for the facility",
    amount="90 percent of room tax collected", amount_basis="share_of_tax",
    amount_value="90", amount_unit="percent of room tax collected",
    term="in perpetuity for so long as the Tribe or Authority operates or permits a hotel or motel at the facility",
    effective_date="2024-01-10",
    date_basis="EA p.11: 'On January 10, 2024, the Tribe and the Kenosha Area Tourism Corporation entered into an agreement'",
    agreement_status="executed", page="206-209", page_label="1-4",
    section_ref="Sections V(A), VI and VII",
    notes="Paid monthly. The Tribe must enact and maintain a room tax equal to the City of Kenosha's room tax (Section VI). Unpaid amounts bear 12 percent per annum. The Authority designates a director to the Bureau's board. Absolute dollar value is not projected anywhere in the retrieved documents."))
T3.append(t3(**MA, _doc="MEN_EA", counterparty_government="State of Wisconsin",
    counterparty_type="state",
    agreement_name="Menominee Indian Tribe of Wisconsin and State of Wisconsin Gaming Compact of 1992, as amended (most recently August 2022)",
    service="Class III gaming authorization; revenue distribution to the State",
    amount="formula based on gaming Net Win; rate not stated in the EA",
    amount_basis="percent_of_net_win_unspecified",
    term="per the compact as amended", effective_date="1992-06",
    date_basis="EA p.9: 'In June 1992, the Tribe and the state of Wisconsin entered into a Tribal-State Gaming Compact'; most recent amendment August 2022",
    agreement_status="executed", page="9", page_label="4", section_ref="EA Section 1.6.1",
    notes="The compact itself is not in the appendix set. Appendix SOCIO states that total payments to state and local government are expected to be 11 percent of annual gaming revenue, of which 4 percent is the City+County IGA share, implying a 7 percent compact component -- but that residual is NOT stated in any document and is not recorded as a value here."))

# ================================================================= WRITE =====
# --- REGENERATE GUARD (ADR-017, 2026-09-02) --------------------------------
def _carry_live_columns(path, canonical):
    """Derive this writer's header instead of declaring it.

    A wholesale writer holding a FIXED `fieldnames` list deletes every column
    an in-place enricher added since - no error, no exception, a diff nobody
    reads. Canonical order first so column order stays stable, then whatever
    the live file already carries. A retired column stays retired because it
    is not on disk; a promoted column survives because it is.

    THIS BUILD CANNOT REPOPULATE AN ENRICHER'S COLUMN. Carried columns are
    written BLANK and NAMED on stdout, which is strictly better than deleted:
    the schema survives and the enricher can refill them. Re-run the enricher
    after this build - `cedar_pipeline.enrichers_to_rerun(<table>)` names it.
    """
    import csv as _csv
    import os as _os
    canonical = list(canonical)
    _p = str(path)
    if not _os.path.exists(_p):
        return canonical
    with open(_p, encoding="utf-8-sig", newline="", errors="replace") as _fh:
        _live = next(_csv.reader(_fh), [])
    _extra = [c for c in _live if c and c not in canonical]
    if _extra:
        print("  [regenerate guard] %s: carrying %d enricher column(s) through "
              "this rebuild, BLANK - re-run the enricher: %s"
              % (_os.path.basename(_p), len(_extra), ", ".join(_extra)))
    return canonical + _extra


def write(path, cols, rows):
    # REGENERATE GUARD (ADR-017, 2026-09-02): derive the header, do not declare it.
    cols = _carry_live_columns(path, cols)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in cols})
    log(f"wrote {os.path.basename(path):42s} {len(rows):4d} rows x {len(cols)} cols")

# strip helper keys
T1 = [{k: v for k, v in r.items() if k in T1_COLS} for r in T1]

write(os.path.join(CLEAN, "gaming_project_facilities.csv"), T1_COLS, T1)
write(os.path.join(CLEAN, "gaming_projections.csv"), T2_COLS, T2)
write(os.path.join(CLEAN, "gaming_mitigation_agreements.csv"), T3_COLS, T3)

# -------------------------------------------------------------- summary -----
from collections import Counter
log("\n-- Table 1 by project x alternative_role --")
for k, v in sorted(Counter((r["project_id"], r["alternative_role"]) for r in T1).items()):
    log(f"   {k[0]:26s} {k[1]:32s} {v}")
log("\n-- Table 2 reported vs calculated --")
for k, v in sorted(Counter(r["reported_or_calculated"] for r in T2).items()):
    log(f"   {k:12s} {v}")
log("\n-- Table 2 by project --")
for k, v in sorted(Counter(r["project_id"] for r in T2).items()):
    log(f"   {k:26s} {v}")
log("\n-- Table 2 by impact_type --")
for k, v in sorted(Counter(r["impact_type"] for r in T2).items()):
    log(f"   {k:28s} {v}")
log("\n-- Table 2 confidence --")
for k, v in sorted(Counter(r["confidence"] for r in T2).items()):
    log(f"   {k:12s} {v}")
log("\n-- Table 3 by counterparty --")
for k, v in sorted(Counter(r["counterparty_government"] for r in T3).items()):
    log(f"   {k[:60]:62s} {v}")
log("\n-- Table 3 amount_basis --")
for k, v in sorted(Counter(r["amount_basis"] for r in T3).items()):
    log(f"   {k:34s} {v}")

with open(LOG, "a", encoding="utf-8") as f:
    f.write(f"\n===== 32b_build_gaming_nepa_pilot.py  {datetime.datetime.now()} =====\n")
    f.write(buf.getvalue())
