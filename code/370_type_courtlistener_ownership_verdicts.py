"""370 - TYPE what each retrieved caption actually SUPPORTS.  By hand.

WHY BY HAND, AND WHY THAT IS NOT LAZINESS
-----------------------------------------
`code/218_type_sealed_state_rows.py` typed ten Single-Audit figures by hand for
a reason it wrote down: *"the measure differs sentence by sentence and a regex
that guessed it would produce exactly the defect this project keeps catching -
a figure that is well-sourced and mislabelled."*

The same is true here, and worse.  Two captions with identical shapes mean
opposite things:

    Ray v. Tanaq Government Services            (N.D. Ga. 1:24-cv-00056)
        Tanaq Government Services AND St. George Tanaq Corporation are
        co-DEFENDANTS.  Operating company beside village corporation.

    Novotny v. Delaware Nation Economic Development Authority LLC
        (W.D. Okla. 5:18-cv-00200)
        KNWEBS Inc and the Delaware Nation entity are in ONE party array and
        on OPPOSITE sides of the `v.`  Same shape, opposite meaning.

No rule over the party array separates those.  A human reading the caption
does, in one second, and then writes down which it was.

THE VOCABULARY, AND WHAT MAY INHERIT FROM WHAT
----------------------------------------------
    COURT_FOUND            a court made the finding          -> ownership evidence
    STIPULATED             the parties agreed it on record   -> ownership evidence
    NAMED_AS_PARENT        a Rule 7.1 / corporate-disclosure
                           statement names the parent        -> ownership evidence
    ALLEGED_IN_COMPLAINT   a party asserted it               -> NOT a finding
    CO_PARTY_ALIGNED       same side of the v.               -> relationship only
    CO_DEFENDANT_ONLY      both defendants, tie unstated     -> relationship only
    CO_PARTY_ADVERSE       opposite sides                    -> evidence AGAINST a
                                                                simple parent
                                                                reading at that date
    NOT_FOUND_IN_RECAP     swept, naming what was swept      -> a RESULT

**Nothing typed below ownership may become an attribution**, and this script
assigns NO tier and writes NO shared table.  A tier is inherited from the
source row; `docs/UNTAPPED_FREE_SOURCES_2026-08-26.md` section A build-plan
item 3 says it in this exact context: *"Only VERIFIED_PARTY may become a link,
and its tier is inherited from the docket row, never assigned because a caption
is exact."*

DATE EVERYTHING.  A 2015 caption is evidence about 2015.
--------------------------------------------------------
`Novotny` is 2018.  `Huliau v. KWN Assets` is 2021.  `Modoc Nation v. Shah` is
2024.  `St. George Tanaq Corp v. Tanadgusix Corp` is 1984.  An ownership
structure that held in 1984 says nothing about the 2022 roster, and a
historical record ruled against a current roster is the error this file
refuses to make.  Every row carries `evidence_date` and
`applies_to_period`.

py -3 code/370_type_courtlistener_ownership_verdicts.py     # 0 requests
"""
import csv
import json
import pathlib
import sys

csv.field_size_limit(10 ** 8)

ROOT = pathlib.Path(__file__).resolve().parent.parent
REVIEW = ROOT / "review"
TODAY = "2026-08-26"
OUT = REVIEW / f"courtlistener_ownership_verdicts_{TODAY}.csv"

CL = "https://www.courtlistener.com/docket/"

# ---------------------------------------------------------------------------
# Each row is ONE Cedar question and the ONE thing the retrieved record says
# about it.  `party_verbatim` is copied from the API response with no editing;
# that quote plus its citation IS the product.
# ---------------------------------------------------------------------------
V = [
 # ---------------- THE SEVEN RULED `NATIVE` WITH NO OWNER NAMED -------------
 dict(bucket="1_THE_SEVEN", subject="Redstone Defense Systems",
      subject_key="UEI:SQVHYKHN43H5", usd_at_stake="1362233885",
      verdict="NOT_FOUND_IN_RECAP", relationship_type="NOT_FOUND_IN_RECAP",
      case_name="", court="", docket_number="", evidence_date="",
      docket_url="", party_verbatim="",
      what_was_swept=("two routes, two requests: full-text `q=\"Redstone Defense "
                      "Systems\"` -> count=1, a C.D. Cal. APA case naming Blue "
                      "Aerospace and United Aeronautical, our name present only in "
                      "document text; and `party_name=Redstone Defense Systems` -> "
                      "count=1, 0 verified parties."),
      what_it_does_not_prove=("Absence under a filter is a property of the filter. "
                              "RECAP is a PARTIAL mirror of PACER and "
                              "code/139 already records that the absence of an "
                              "organisation is not evidence it did not file."),
      cedar_action="STILL NEEDS AN OWNER. Highest single unattributed figure in the queue.",
      applied="NO"),
 dict(bucket="1_THE_SEVEN", subject="Manu Kai, LLC",
      subject_key="UEI:HD9LT6J78NB3", usd_at_stake="760581490",
      verdict="RELATIONSHIP_ONLY_NO_OWNER_NAMED",
      relationship_type="CO_DEFENDANT_ONLY",
      case_name="Michaud v. Manu Kai, LLC", court="District Court, D. Hawaii",
      docket_number="1:15-cv-00438", evidence_date="2015-10-20",
      docket_url=CL + "13318768/michaud-v-manu-kai-llc/",
      party_verbatim=("ITT Systems Corporation | Doe Government Entities 1-20 | "
                      "Exelis Inc. | Ke'aki Technologies, LLC | Doe Subsidiaries 1-20 | "
                      "ITT Industries Systems Division | Vectrus Systems Corporation | "
                      "ITT Exelis Information Systems | Darlington, Inc. | "
                      "Doe Partnerships 1-20 | David L. Michaud | ITT Exelis Corporation | "
                      "United States of America | Manu Kai, LLC | ITT Corporation | "
                      "Harris Corporation | Akimeka, LLC | ITT Industries, Inc. | "
                      "Doe Holding Companies 1020 | John Does 1-20 | "
                      "Doe Limited Liability Companies | Doe Business Entities 1-20 | "
                      "Doe Vessels 1-20 | Doe Vessel Owners/Charterers/Operators 1-20 | "
                      "Akimeka Technologies, LLC | Mary Does 1-20 | "
                      "Exelis Systems Corporation | Doe Joint Ventures 1-20 | "
                      "Vectrus, Inc. | Doe Associations 1-20 | Does Corporations 1-20"),
      what_was_swept=("VERIFIED_PARTY on two D. Haw. dockets, 1:15-cv-00438 and "
                      "1:15-cv-00321. Manu Kai, Ke'aki Technologies LLC and "
                      "Akimeka LLC / Akimeka Technologies LLC are in one party array."),
      what_it_does_not_prove=("NOT ownership, and the caption says why itself: 31 "
                              "parties including `Doe Holding Companies 1020`, "
                              "`Doe Subsidiaries 1-20` and `Doe Joint Ventures 1-20`. "
                              "A plaintiff naming every conceivable entity is not a "
                              "corporate-family disclosure. The ITT / Exelis / Vectrus / "
                              "Harris chain on the same caption shows the common thread "
                              "is a NAVY CONTRACT, not a parent."),
      cedar_action=("STILL NEEDS AN OWNER. What is new is a dated SIBLING SET - "
                    "Manu Kai + Ke'aki Technologies + Akimeka - to test against the "
                    "spine as one family."),
      applied="NO"),
 dict(bucket="1_THE_SEVEN", subject="KNWEBS Inc.",
      subject_key="UEI:FQPCMNZP6JB3", usd_at_stake="167179488",
      verdict="NAMED_RELATIONSHIP_BUT_SIDES_UNKNOWN",
      relationship_type="CO_PARTY_SIDE_NOT_YET_ESTABLISHED",
      case_name="Novotny v. Delaware Nation Economic Development Authority LLC",
      court="District Court, W.D. Oklahoma", docket_number="5:18-cv-00200",
      evidence_date="2018-03-05",
      docket_url=CL + "6501295/novotny-v-delaware-nation-economic-development-authority-llc/",
      party_verbatim=("Kenneth W Novotny | Indigenous Technologies LLC | "
                      "Delaware Nation Economic Development Authority LLC | KNWEBS Inc"),
      what_was_swept=("VERIFIED_PARTY. Cause 28:1332 Diversity-Other Contract. "
                      "Cedar independently attributes the co-party INDIGENOUS "
                      "TECHNOLOGIES, LLC (Chickasha OK, $371.5M, attributed_flag=1) "
                      "to Delaware Nation, so two of the four parties are already a "
                      "Delaware Nation pair. A second docket, Huliau v. KWN Assets LLC, "
                      "W.D. Okla. 5:21-cv-01119 filed 2021-11-24, party array "
                      "`Hui Huliau | Kenneth W Novotny | Pono Aina Management LLC | "
                      "KWN Assets LLC`, puts the NHO Hui Huliau against KNWEBS' "
                      "principal three years later."),
      what_it_does_not_prove=("The caption is Novotny **v.** the Delaware Nation entity. "
                              "Until party ROLES are read, KNWEBS may be a plaintiff "
                              "ADVERSE to Delaware Nation rather than a co-defendant "
                              "beside it - and those two readings point at opposite "
                              "answers. `code/368` asks exactly that question."),
      cedar_action=("The strongest of the seven. Two dated, named counterparties "
                    "(Delaware Nation EDA 2018; Hui Huliau 2021) where there were none."),
      applied="NO"),
 dict(bucket="1_THE_SEVEN", subject="Tc&S/F-W, L.L.C.",
      subject_key="UEI:X4FLQ8BSTTK5", usd_at_stake="160251283",
      verdict="NOT_FOUND_IN_RECAP", relationship_type="NOT_FOUND_IN_RECAP",
      case_name="", court="", docket_number="", evidence_date="", docket_url="",
      party_verbatim="",
      what_was_swept=("`q=\"Tc&S/F-W\"` -> count=1, a N.D. Ill. habeas petition, "
                      "text-only. `party_name=TC&S/F-W` -> **HTTP 500** from the API, "
                      "which is not a fact about the object and was re-queued as "
                      "`TCS F-W`."),
      what_it_does_not_prove=("A 500 means try later - AGENTS.md, `only 404 and 403 "
                              "are facts about an object`."),
      cedar_action=("LOCAL LEAD, ZERO REQUESTS: all 2,339 prime rows on this UEI are "
                    "registered at **SAN JUAN PUEBLO, NM**, which is Ohkay Owingeh. "
                    "BEWARE the San Juan collision recorded in AGENTS.md - the spine's "
                    "`San Juan` is the San Juan Southern Paiute Tribe of ARIZONA. "
                    "`party_name=Ohkay Owingeh` returned 2 dockets and neither names "
                    "this firm, so the pueblo leg is unconfirmed."),
      applied="NO"),
 dict(bucket="1_THE_SEVEN", subject="Atlantic Nicc Jv Llc",
      subject_key="UEI:ZF6TS5PKA4F4", usd_at_stake="123212698",
      verdict="NOT_FOUND_IN_RECAP", relationship_type="NOT_FOUND_IN_RECAP",
      case_name="", court="", docket_number="", evidence_date="", docket_url="",
      party_verbatim="",
      what_was_swept="`q=` -> 0 dockets. `party_name=Atlantic NICC` -> 0 dockets. `party_name=NICC JV` -> 0 dockets.",
      what_it_does_not_prove="RECAP holds nothing on this name; it does not follow that no case exists.",
      cedar_action=("LOCAL FINDING, ZERO REQUESTS: this is one of **six** NICC JVs in "
                    "`prime_contracts.csv` - Atlantic, Central, National, Pacific, "
                    "`NICC JV LLC` and NORTHEAST - all at Falls Church / Vienna VA. "
                    "Five are unattributed; **NORTHEAST NICC JV, LLC is attributed to "
                    "`TRBS-CHKNAL-00 Cherokee Tribe of Northeast Alabama`, a "
                    "STATE-recognised tribe**, on 2 rows. That single attribution is "
                    "the only thread the family has and it deserves its own look."),
      applied="NO"),
 dict(bucket="1_THE_SEVEN", subject="Southwind Construction Company",
      subject_key="UEI:JDAKGNWJL3A1", usd_at_stake="110923113",
      verdict="RELATIONSHIP_ONLY_NO_OWNER_NAMED",
      relationship_type="CO_PARTY_ADVERSE",
      case_name="Southwind Construction Services LLC v. Ross Group Construction Corporation The",
      court="District Court, W.D. Oklahoma", docket_number="5:15-cv-00102",
      evidence_date="2015-01-29",
      docket_url=CL + "13566135/southwind-construction-services-llc-v-ross-group-construction-corporation/",
      party_verbatim=("C3 LLC | Ross Group Construction Corporation The | "
                      "Ross Group LLC The | John Does | Southwind Construction Services LLC | "
                      "Pentacon LLC | Red Cedar Enterprises Inc"),
      what_was_swept=("5 VERIFIED_PARTY dockets. Cause 31:3729 False Claims Act. "
                      "No tribal or corporate parent is named on any of them."),
      what_it_does_not_prove=("**AND IT CARRIES A NAME TRAP.** Three different legal "
                              "persons answer to `Southwind Construction`: "
                              "`Southwind Construction Corporation` (W.D. Tenn. "
                              "2:04-cv-02931 and E.D.N.C. 4:24-cv-00005, a MARINE "
                              "contractor), `Southwind Construction Services LLC` "
                              "(W.D. Okla.), and Cedar's own target `Southwind "
                              "Construction Co Inc` of Edmond OK. None of the five "
                              "dockets names the Edmond entity. A name match across "
                              "states is a hypothesis."),
      cedar_action=("STILL NEEDS AN OWNER. The caption's real yield is elsewhere: it "
                    "put `Pentacon LLC` (Catoosa OK, $121.6M, UNATTRIBUTED) and "
                    "`Red Cedar Enterprises Inc` on the record together."),
      applied="NO"),
 dict(bucket="1_THE_SEVEN", subject="Central Nicc Jv, Llc",
      subject_key="UEI:XH6JJCZ1F7R4", usd_at_stake="66017732",
      verdict="NOT_FOUND_IN_RECAP", relationship_type="NOT_FOUND_IN_RECAP",
      case_name="", court="", docket_number="", evidence_date="", docket_url="",
      party_verbatim="",
      what_was_swept=("`q=\"Central Nicc\"` -> count=1, `Lexon Insurance Company v. "
                      "FutureNet Group, Inc.` (E.D. Mich.), text-only, unrelated. "
                      "`party_name=Central NICC` -> 0."),
      what_it_does_not_prove="see Atlantic NICC.",
      cedar_action="STILL NEEDS AN OWNER. Same six-JV family as Atlantic NICC.",
      applied="NO"),

 # ------------- WHAT THE SAME BUDGET SETTLED OUTSIDE THE SEVEN --------------
 dict(bucket="2_CONFLICT_BROKEN", subject="Red Cedar Enterprises, Inc.",
      subject_key="UEI:JZQYD48BJMX3 / CAGE:3V7E1 / CAGE:6F0N0",
      usd_at_stake="183470000",
      verdict="COURT_RECORD_CONTRADICTS_A_LIVE_CEDAR_ATTRIBUTION",
      relationship_type="CO_PARTY_ALIGNED",
      case_name="Modoc Nation v. Shah",
      court="Court of Appeals for the Tenth Circuit", docket_number="24-5135",
      evidence_date="2024-11-18",
      docket_url=CL + "71537478/modoc-nation-v-shah/",
      party_verbatim=("WALGA MTE, LLC | SHARAD DADBHAWALA | LEGAL ADVOCATES FOR "
                      "INDIAN COUNTRY LLP | MODOC MTE, LLC | TROY LITTLEAXE | "
                      "BUFFALO MTE, LLC | MODOC NATION, AKA Modoc Tribe of Oklahoma | "
                      "RAJESH SHAH | SOFTEK SOLUTIONS, INC. | BLAKE FOLLIS | "
                      "RED CEDAR ENTERPRISES, INC. | SOFTEK MANAGEMENT SERVICES, LLC | "
                      "EAGLE T..."),
      what_was_swept=("Cedar's ledger holds BOTH answers on this one company and "
                      "neither was applied: `CAGE:3V7E1 -> TRBF-MODOCN-00 Modoc Nation`, "
                      "`agent_research_one_leg`, tier B, `is_authority: YES`, "
                      "rationale *'Agent-researched 2026-08-06: single evidence leg'*; "
                      "and `UEI:JZQYD48BJMX3 -> TRBF-PTTRUT-00 Paiute of Utah`, "
                      "`cluster_v3`, tier B, rationale *'Algorithmic name clustering, "
                      "unreviewed'*. `prime_contracts.csv` follows the cluster_v3 leg "
                      "via `uei_exact` on 611 rows / $183.5M. The firm's own registered "
                      "city on all 611 rows is **MIAMI, OK** - the Modoc Nation's seat - "
                      "not Cedar City, Utah."),
      what_it_does_not_prove=("A caption is alignment, not ownership. Modoc Nation and "
                              "Red Cedar Enterprises are co-parties, and the record "
                              "retrieved does not state that one owns the other."),
      cedar_action=("**THE SECOND EVIDENCE LEG the Modoc attribution was missing.** "
                    "AGENTS.md: two independent legs = tier A, one leg = tier B. "
                    "Tier is not assigned here. Send to the owner with the quote."),
      applied="NO"),
 dict(bucket="2_CONFLICT_BROKEN",
      subject="cluster_v3 hung every company named `Cedar` on Paiute Indian Tribe of Utah",
      subject_key="TRBF-PTTRUT-00", usd_at_stake="313756454",
      verdict="NAMED_DEFECT_IN_A_LIVE_ATTRIBUTION_METHOD",
      relationship_type="NOT_A_COURT_FINDING_LOCAL_MEASUREMENT",
      case_name="", court="", docket_number="", evidence_date=TODAY, docket_url="",
      party_verbatim="",
      what_was_swept=("Found by following the Modoc caption back into the ledger, then "
                      "measured locally at zero network cost by "
                      "`code/371_stage_cedar_token_cluster_review.py`. Of 37 "
                      "Paiute-of-Utah ledger rows, 16 are `cluster_v3` / tier B / "
                      "*'Algorithmic name clustering, unreviewed'*, and **12 of those "
                      "carry the token `cedar` or `tikigaq`**: Red Cedar Enterprises "
                      "(MIAMI OK), Red Cedar Harmonia (Leesburg VA), Red Cedar "
                      "Solutions x2 and Red Cedar Management Solutions (Moorestown NJ), "
                      "Cedar International Services (Poquoson VA / Tampa FL), Cedar "
                      "Spring (Irvine CA), Cedar Butte Forestry (Hillsboro OR), CEDAR "
                      "RIO JV, **Cedar Key Native Environmental (CEDAR KEY, FLORIDA)** "
                      "and **Goldbelt-Cedar, L.L.C. (Irving TX - Goldbelt is the JUNEAU "
                      "ANCSA urban corporation)**. Prime exposure booked to Paiute of "
                      "Utah on those twelve identifiers: **$313,756,454 over 1,235 "
                      "rows.** Not one of those cities is in Utah."),
      what_it_does_not_prove=("cluster_v3 got the CONSTITUENT BANDS right - Shivwits "
                              "Band Corporation, Kanosh Band, Indian Peaks Band and the "
                              "tribe itself, seven rows, all correct. The defect is "
                              "specific to a PLACE TOKEN, not to the method everywhere, "
                              "and each of the twelve needs its own ruling: this is a "
                              "review queue, not a mass retraction. **And one of the "
                              "twelve is a different defect entirely** - "
                              "`UEI:R3GMNTDL7356` is `Tikigaq Technology Services` in "
                              "the ledger and `S & T SERVICES, LLC` on 311 of its 312 "
                              "prime rows, **30 of them in CEDAR CITY, UT**, which is "
                              "the tribe's own seat. That attribution may be perfectly "
                              "correct; what is wrong is that two files disagree about "
                              "WHICH COMPANY the identifier is. It is typed "
                              "`LEDGER_AND_PRIME_DISAGREE_ON_THE_COMPANY_NAME` rather "
                              "than swept in, because a well-sourced mislabelled row is "
                              "the failure this project keeps paying for."),
      cedar_action=("The tribe is seated in **Cedar City, Utah** and its Cedar Band owns "
                    "Cedar Band Corporation, so `cedar` is the anchor token. Same shape "
                    "as AGENTS.md's `core() FOLDS AWAY THE WORD THAT DISTINGUISHES` and "
                    "`a place suffix makes a tribe name a place`. Staged, not applied."),
      applied="NO"),
 dict(bucket="2_CONFLICT_BROKEN",
      subject="the 116 conflicting rulings - what a court record can and cannot break",
      subject_key="review/ruling_conflicts_2026-08-26.csv", usd_at_stake="",
      verdict="TRIAGED_BEFORE_SPENDING_A_REQUEST",
      relationship_type="LOCAL_MEASUREMENT",
      case_name="", court="", docket_number="", evidence_date=TODAY, docket_url="",
      party_verbatim="",
      what_was_swept=("1,215 rows collapse to **116 distinct subjects**: 83 "
                      "`OWNER_VS_DIFFERENT_UNRESOLVED_OWNER`, 28 "
                      "`POSITIVE_VS_NOT_NATIVE`, 5 `TWO_DIFFERENT_UNRESOLVED_OWNERS`. "
                      "**The great majority are not questions a docket can answer, and "
                      "that is MEASURED, not asserted:** stripping generic words "
                      "(tribe/nation/band/pueblo/housing/authority/...) and comparing "
                      "core tokens, **77 of the 83 owner conflicts have every candidate "
                      "ruling sharing a core token with the subject itself** - "
                      "`Standing Rock Sioux Tribe` against the placeholder "
                      "`RESOLVED_UNAMBIGUOUS`, `Quapaw Tribe` against `Quapaw Nation`, "
                      "`Tolowa Dee-ni Nation` against `Tolowa Dee-ni' Nation`. Those are "
                      "**two spellings of one tribal government** and a caption naming "
                      "the tribe adjudicates nothing. Only **6** name something with no "
                      "shared token, and two of those six are the same Alakaʻi subject "
                      "under two identifiers, two are Capitan Grande "
                      "band-versus-group id conflicts (Barona, Viejas), one is a housing "
                      "authority against its own tribe (Akwesasne / Saint Regis Mohawk) "
                      "and one is a constituent band against its umbrella (South Fork "
                      "Band Council / Te-Moak), which `cedar_domain` already holds in "
                      "`NEVER_OWNERSHIP`. The 28 `POSITIVE_VS_NOT_NATIVE` rows are "
                      "nonprofit EINs (`NORTH EASTERN BAND OF CHEROKEE`, `FLORIDA "
                      "TRIBE OF CHEROKEE INDIANS`) where the question is federal "
                      "recognition, which is a Federal Register question and not a "
                      "docket question."),
      what_it_does_not_prove=("This is a triage, not a ruling on any of the 116. None "
                              "was closed and none was touched."),
      cedar_action=("**Only a handful name two DIFFERENT LEGAL PERSONS, which is the "
                    "only shape a caption resolves**, and those are the ones that got "
                    "the requests: `CAGE:8QYZ6 / UEI:EMNDBXF7JSK9 Alakaʻi Services "
                    "Group` (standalone vs NHO-ALAKA1-00 Alakaʻi Foundation) - "
                    "**0 dockets on both routes, unsettled**; and `UEI:DD76ANKVJKY8` "
                    "(REFUSE vs St. George Tanaq Corporation) - **settled far enough "
                    "to matter, see the row below.** The right instrument for the other "
                    "~110 is a name-normalisation pass and the Federal Register list of "
                    "recognised tribes, not RECAP - and spending 110 of 125 daily "
                    "requests to learn that would have been the expensive way."),
      applied="NO"),
 dict(bucket="2_CONFLICT_BROKEN", subject="St. George Tanaq Corporation",
      subject_key="UEI:DD76ANKVJKY8 / CAGE:7LQS6", usd_at_stake="91800000",
      verdict="CORROBORATES_THE_CORPORATION_LEG",
      relationship_type="CO_DEFENDANT_ONLY",
      case_name="Ray v. Tanaq Government Services",
      court="District Court, N.D. Georgia", docket_number="1:24-cv-00056",
      evidence_date="2024-01-04",
      docket_url=CL + "68142331/ray-v-tanaq-government-services/",
      party_verbatim=("Amanda Jean Ray | Tanaq Government Services | "
                      "St. George Tanaq Corporation | "
                      "Center for Disease Control and Prevention (CDC)"),
      what_was_swept=("The conflict row is `UEI:DD76ANKVJKY8 | Pribilof Islands | "
                      "REFUSE // St. George Tanaq Corporation`, and the ANCSA "
                      "resolution file carries `CAGE:7LQS6` and `UEI:LCMDVD5845M4` "
                      "(HELIOTECH, $11.03M) as "
                      "`HUMAN_NEEDED_SURVIVING_CORPORATION_UNVERIFIED` on the same "
                      "pair. Cedar already attributes `TANAQ GOVERNMENT SERVICES, LLC` "
                      "(Anchorage AK, $91.8M) to St. George Tanaq Corporation, and "
                      "this 2024 caption is an INDEPENDENT third party naming the "
                      "operating company and the village corporation together."),
      what_it_does_not_prove=("Co-defendants, not a stated parent. And it does not "
                              "identify WHICH Pribilof village - `St. George Tanaq "
                              "Corp v. Tanadgusix Corp`, D. Alaska 3:84-cv-00034 filed "
                              "1984-01-25, shows the St. George and St. Paul "
                              "corporations litigating AGAINST each other, which is "
                              "itself rule-5 evidence and a caution against treating "
                              "`Pribilof Islands` as one legal person."),
      cedar_action=("Second independent corroboration of ANCSA rule 1 after "
                    "`Pease v. Sitnasuak`: operating company + VILLAGE CORPORATION on "
                    "one caption, village GOVERNMENT absent."),
      applied="NO"),
 dict(bucket="3_HIGH_DOLLAR_CLUSTER",
      subject="the Dawson family and Hawaiian Native Corp.",
      subject_key="Dawson Enterprises / Technical / Federal / Solutions / Global / D7",
      usd_at_stake="1060500000",
      verdict="CAPTION_NAMES_A_LEAD_DEFENDANT_OVER_THE_WHOLE_FAMILY",
      relationship_type="CO_DEFENDANT_ONLY",
      case_name="United States of America v. Hawaiian Native Corp.",
      court="District Court, S.D. California", docket_number="3:18-cv-02849",
      evidence_date="2018-12-19",
      docket_url=CL + "16069152/united-states-of-america-v-hawaiian-native-corp/",
      party_verbatim=("Total Reliant Solutions, LLC | Dawson Technical, LLC | D7, LLC | "
                      "Dawson Enterprises, LLC | Wagon Wheel, LLC | Dawson Solutions, LLC | "
                      "Dawson Federal Inc. | United States of America | "
                      "Sandlot Ventures, LLC | Eugene Sellers | Dawson Global, LLC | "
                      "BD Solutions, LLC | Program Construction and Management"),
      what_was_swept=("Not one of the seven, and the largest unattributed family this "
                      "pass touched. Measured from `prime_contracts.csv` "
                      "attributed_flag=0: Dawson Enterprises LLC (HI) $363.8M, "
                      "Dawson Federal Inc (TX) $191.9M, D7 LLC (CO) $211.0M, "
                      "Dawson Technical LLC (TX+HI) $227.7M, Dawson Solutions LLC (AL) "
                      "$133.8M, plus the Dawson JVs - **~$1.06B, all unattributed** - "
                      "and the United States is the plaintiff against all of them under "
                      "a caption headed by **Hawaiian Native Corp.**"),
      what_it_does_not_prove=("Co-defendants. The complaint was not retrieved, so "
                              "whether the United States alleged an ownership or "
                              "affiliation relationship is `NOT_CHECKED`, and an "
                              "allegation would not be a finding in any case."),
      cedar_action=("Highest-value single lead produced by this pass. The free RECAP "
                    "documents on docket 16069152 are the next request to spend."),
      applied="NO"),

 # ----------------------- ANCSA: A MEASURED NEGATIVE -----------------------
 dict(bucket="4_ANCSA", subject="Copper River / Native Village of Eyak (RULE_3_CANDIDATE)",
      subject_key="UEI:VJ4MGKFTMVJ8 / CAGE:7B3W1", usd_at_stake="410842",
      verdict="NOT_SETTLED_BY_RECAP_MEASURED",
      relationship_type="NOT_FOUND_IN_RECAP",
      case_name="Taylor v. Alaska Native General Services LLC",
      court="District Court, D. Alaska", docket_number="3:17-cv-00080",
      evidence_date="2017-04-11",
      docket_url=CL + "14519600/taylor-v-alaska-native-general-services-llc/",
      party_verbatim=("GSI, LLC | H.  Benjamin Brucker | Edmund I. Mangini, III | "
                      "Donald Taylor | Alaska Native General Services LLC | "
                      "Copper River Information Technology, LLC"),
      what_was_swept=("Five requests. `party_name=Native Village of Eyak` -> 8 dockets, "
                      "7 verified, and **every one is the TRIBE litigating as a "
                      "government** - Native Village of Eyak v. Exxon Corp (D. Alaska "
                      "3:91-cv-00568 and 3:94-cv-00331), v. Gary Locke (3:98-cv-00365 "
                      "and 9th Cir. 09-35881), v. Brown (3:95-cv-00063), Tribal Council "
                      "v. Cesar (3:93-cv-00369), and Pallas v. Cordova Community "
                      "Medical Center. It NEVER appears beside an operating company. "
                      "`party_name=Eyak Corporation` -> 6 dockets, **0 verified "
                      "parties**. `q=EyakTek` -> 8 dockets, all the D.D.C. Army Corps "
                      "bribery prosecutions (Khan, Cho, McKinney, Corbett, Nova "
                      "Datacom), text-only, no Eyak entity in any party array. "
                      "`party_name=Copper River` -> 77 dockets, 16 verified, and the "
                      "only true operating-company docket is `Brucker v. Copper River "
                      "Shared Services LLC` (E.D. Va. 1:20-cv-00738, 2020-07-02), two "
                      "parties, no parent."),
      what_it_does_not_prove=("**AND IT CARRIES THE NAME TRAP THIS FAMILY IS BUILT "
                              "FOR.** `Copper River Native Association` - a tribal "
                              "health consortium appearing in the opioid and JUUL MDLs "
                              "beside Kenaitze Indian Tribe, Chugachmiut and Tanana "
                              "Chiefs Conference - is a DIFFERENT legal person from the "
                              "Copper River family of companies. So is `Copper River "
                              "Salon, LLC` (D.N.J.), `Copper River Campus, LLC` and "
                              "`Copper River Guides, LLC`. A `Copper River` name match "
                              "merges four unrelated entities."),
      cedar_action=("The RULE_3_CANDIDATE stays OPEN. `docs/ANCSA_OWNERSHIP_RULING.md` "
                    "requires rule 3 be EVIDENCED per identifier; RECAP does not supply "
                    "that evidence, and **a sweep that finds nothing is a result** "
                    "(PULL_DISCIPLINE). Recorded with the date and the surface probed."),
      applied="NO"),

 dict(bucket="1_THE_SEVEN",
      subject="ALL SEVEN - the self-certification legs are empty, measured",
      subject_key="the seven NEEDS_AN_OWNER UEIs", usd_at_stake="2750399689",
      verdict="EVERY_SELF_CERTIFICATION_LEG_IS_EMPTY",
      relationship_type="LOCAL_MEASUREMENT",
      case_name="", court="", docket_number="", evidence_date=TODAY, docket_url="",
      party_verbatim="",
      what_was_swept=("Zero network cost, over all 8,447 prime rows on the seven UEIs. "
                      "`reported_indian_business` is **0 on every one of the 8,447**. "
                      "`reported_buy_indian` - the one flag `docs/RECONCILIATION_TOOL.md` "
                      "says actually discriminates - is 1 on **exactly ONE row**, and it "
                      "is KNWEBS'. `reported_native_preference` tracks `reported_8a` "
                      "**digit for digit** on all seven firms (Redstone 81/81, KNWEBS "
                      "503 vs 504, TC&S/F-W 506/506, Southwind 272/272, and 0/0 on Manu "
                      "Kai and both NICC JVs). And the SAM/FSRS DECLARED-PARENT leg is "
                      "empty too: Redstone Defense Systems names **itself** as its "
                      "ultimate parent on all 2,039 prime rows and all 9 of its subaward "
                      "rows, and the other six appear in `subawards.csv` not at all."),
      what_it_does_not_prove=("Absence of a flag is not evidence against Native "
                              "ownership - $140.00B of $244.77B attributed sits on "
                              "awards with no Native set-aside at all."),
      cedar_action=("This is WHY these seven are the hardest rows in the project and "
                    "why a court record was the right instrument to reach for. It also "
                    "confirms, on this exact cohort, the reconciliation doc's claim "
                    "that `reported_native_preference` is the 8(a) flag relabelled and "
                    "carries no Native signal. KNWEBS' single Buy Indian row and its "
                    "**Indian Health Service majority funder (386 of 742 rows)** are the "
                    "only Native-specific signals any of the seven emit."),
      applied="NO"),

 dict(bucket="4_ANCSA",
      subject="HELIOTECH - the only one of the 8 still booked to a VILLAGE GOVERNMENT",
      subject_key="UEI:LCMDVD5845M4 / CAGE:7LQS6", usd_at_stake="11033998",
      verdict="RULE_2_REFUSAL_IS_STILL_LIVE_IN_THE_PRIME_TABLE",
      relationship_type="CO_DEFENDANT_ONLY",
      case_name="Ray v. Tanaq Government Services",
      court="District Court, N.D. Georgia", docket_number="1:24-cv-00056",
      evidence_date="2024-01-04",
      docket_url=CL + "68142331/ray-v-tanaq-government-services/",
      party_verbatim=("Amanda Jean Ray | Tanaq Government Services | "
                      "St. George Tanaq Corporation | "
                      "Center for Disease Control and Prevention (CDC)"),
      what_was_swept=("Zero network cost, found while preparing the ANCSA queries. "
                      "`review/ancsa_ruling_resolutions_2026-08-26.csv` files 8 rows as "
                      "`HUMAN_NEEDED_SURVIVING_CORPORATION_UNVERIFIED`. **Seven of the "
                      "eight are already booked to the CORPORATION leg in "
                      "`prime_contracts.csv`, most at tier A** - O.E.S., Inc. (Wainwright "
                      "AK) -> Olgoonik Corporation, tier A, $120.97M over 458 rows; "
                      "UIC Bowhead Transport and Umiaq Design -> Ukpeaġvik Iñupiat "
                      "Corporation, tier A; Sand Point Generating LLC -> Tanadgusix "
                      "Corporation (TDX), tier B. **HELIOTECH is the exception**: 196 "
                      "rows, $11,033,998, registered CHICAGO IL, still keyed to "
                      "`AKNF-PRBLFC-00 Pribilof Islands` - a village GOVERNMENT - at "
                      "tier B."),
      what_it_does_not_prove=("The caption is co-defendants and does not name a parent, "
                              "and it is about Tanaq Government Services, not about "
                              "HELIOTECH. It corroborates that St. George Tanaq "
                              "Corporation is the corporate person that stands behind "
                              "an operating company; it does not prove HELIOTECH is one "
                              "of them. And the 1984 case `St. George Tanaq Corp v. "
                              "Tanadgusix Corp` (D. Alaska 3:84-cv-00034) is a warning "
                              "that `Pribilof Islands` is TWO villages and two "
                              "corporations, not one."),
      cedar_action=("`docs/ANCSA_OWNERSHIP_RULING.md` rule 2 says a village government "
                    "never owns an ANC and an attribution asserting it is wrong. This "
                    "one is still live in the promoted prime table. It is the cheapest "
                    "dollar-bearing ANCSA item left and it now has an independent "
                    "record on the corporation side. **Not applied here** - repointing "
                    "a promoted table is `code/192`'s job, not this pass's."),
      applied="NO"),

 # ------------------------------- CONTROLS ---------------------------------
 dict(bucket="0_CONTROL", subject="CONTROL_ABSENT on the full-text route",
      subject_key="", usd_at_stake="", verdict="CONTROL_RETURNED_ZERO",
      relationship_type="CONTROL",
      case_name="", court="", docket_number="", evidence_date=TODAY, docket_url="",
      party_verbatim="",
      what_was_swept=("`type=r&q=\"Kwithluk Sentinel Holdings Incorporated\"` -> "
                      "**count=0, 0 results.**"),
      what_it_does_not_prove="",
      cedar_action=("This is the row that makes every positive above mean something. "
                    "ProPublica's organizations endpoint is the counter-example: HTTP "
                    "200 and `\"name\": \"Unknown Organization\"` for EIN 999999999."),
      applied="NO"),
 dict(bucket="0_CONTROL", subject="CONTROL_ABSENT on the party_name route",
      subject_key="", usd_at_stake="", verdict="CONTROL_RETURNED_ZERO",
      relationship_type="CONTROL",
      case_name="", court="", docket_number="", evidence_date=TODAY, docket_url="",
      party_verbatim="",
      what_was_swept=("`type=r&party_name=Kwithluk Sentinel Holdings` -> **count=0.** "
                      "Run separately because a FILTER is a different code path from a "
                      "full-text query and inherits none of its evidence."),
      what_it_does_not_prove="",
      cedar_action=("Needed because the same probe exposed that `party_name` is "
                      "TOKENISED, not phrase-matched: `party_name=Manu Kai` returned "
                      "**26** dockets including `Lazetta Kay Manus`, `Milton Britt "
                      "Manues and Marilyn Kay Manues` and `Kirk Edward Mc Manus and "
                      "Leslie Kay Mc Manus`. The Torres Martinez surname trap, in a new "
                      "field. Every row is re-verified locally against the party array."),
      applied="NO"),
]

COLS = ["bucket", "subject", "subject_key", "usd_at_stake", "verdict",
        "relationship_type", "case_name", "court", "docket_number",
        "evidence_date", "applies_to_period", "docket_url", "party_verbatim",
        "what_was_swept", "what_it_does_not_prove", "cedar_action", "applied",
        "typed_by", "typed_date", "source_files"]

SRC = ("review/courtlistener_docket_evidence_2026-08-26.csv | "
       "review/courtlistener_party_evidence_2026-08-26.csv | "
       "review/courtlistener_party_roles_2026-08-26.csv")


def main():
    order = {"0_CONTROL": 0, "1_THE_SEVEN": 1, "2_CONFLICT_BROKEN": 2,
             "3_HIGH_DOLLAR_CLUSTER": 3, "4_ANCSA": 4}
    rows = sorted(V, key=lambda r: (order[r["bucket"]],
                                    -float(r["usd_at_stake"] or 0)))
    for r in rows:
        # A record is evidence about ITS OWN DATE.  Never rule a historical
        # record against a current roster.
        r["applies_to_period"] = (f"as of {r['evidence_date']}"
                                  if r["evidence_date"] else "n/a")
        r["typed_by"] = "code/370, by hand, from the verbatim party array"
        r["typed_date"] = TODAY
        r["source_files"] = SRC
    tmp = OUT.with_suffix(".csv.part")
    with tmp.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLS)
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in COLS})
    tmp.replace(OUT)

    back = [r for r in csv.DictReader(OUT.open(encoding="utf-8-sig"))]
    print(f"{len(back)} typed verdict(s) -> {OUT.name}  (re-read from disk)")
    seven = [r for r in back if r["bucket"] == "1_THE_SEVEN"]
    settled = [r for r in seven if r["relationship_type"] in
               ("COURT_FOUND", "STIPULATED", "NAMED_AS_PARENT")]
    print(f"  of the seven: {len(seven)} typed, "
          f"**{len(settled)} settled with a verbatim ownership citation**")
    for r in back:
        print(f"  [{r['bucket']:22s}] {r['verdict']:46s} {r['subject'][:44]}")
    print("\nNOTHING HERE IS APPLIED. No shared table was written. No tier assigned.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
