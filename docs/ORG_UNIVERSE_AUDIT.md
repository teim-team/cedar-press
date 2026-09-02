# The organisational universe — what Cedar holds, what exists, what was added, what is still missing

*Workstream K, pass 3. Measured and acted on 2026-09-01 by `code/524_universe_gap.py`. Every number is recomputed from live data. Companion to `docs/CEDAR_TAXONOMY.md` (what the classes mean) and `docs/NATIVE_ENTITY_NUANCES.md` (why a name is not evidence).*

## The owner's question

> "It seems like we have the right Native entities and organizations. The one thing I didn't see is Native nonprofits… but urban Indian organizations are nonprofits. The listing's pretty good — I think the only thing we're missing is nonprofits. But make sure we have all the organizations."

Both halves are answered, and they do not have the same answer. **Nonprofit legal form is already well represented** — the UIO, TCU, CDFI, intertribal and NHO classes are overwhelmingly 501(c)(3)s, so a `Native nonprofit` class would re-cut entities we already hold. **But the scatter did leave organisations out**, and they are not random: they cluster in three functional types the class list has no home for — tribal health organisations, tribal housing entities and tribal school-board corporations. The first of those had an authoritative federal roster, so it was **fixed in this pass, not filed as a finding**.

## What this pass CHANGED

**19 tribal health organisations were appended to the spine** from the IHS Tribal Self-Governance Program participant list — every one of them a federal roster entry, not an inference.

- Roster: [IHS Office of Tribal Self-Governance, *Self-Governance Tribes*](https://www.ihs.gov/selfgovernance/tribes/), retrieved 2026-09-01. Its own words: *"The following Tribes and authorized Tribal Organizations currently participate in the IHS Tribal Self-Governance Program."*
- Class: `Federal-level self-governance consortium`. The class assignment is not a judgement — **seven entities already in the spine under this class come off this same roster** (Bristol Bay Area Health Corporation, Aleutian Pribilof Islands Association, Chugachmiut, Copper River Native Association, Maniilaq, Tanana Chiefs Conference, Council of Athabascan Tribal Governments), and `SGVF-BRSTLB-00` was minted from the IHS Alaska page in exactly this shape in August.
- Every appended row carries `verification_route = ihs_tribal_self_governance_roster_<date>` plus the corroborating federal source (a FAC single-audit EIN or a USAspending UEI), and a `reconciliation_note` naming the **nearest spine neighbour it must not be merged with**.
- The append re-reads the spine immediately before writing, backs it up, and aborts on an id collision. `cedar_uid` is left blank: this script never runs `503 mint` or `510 --apply`; the integrator does.

| appended | state | corroborating federal source |
|---|---|---|
| Kodiak Area Native Association | AK | FAC single audit 2025, EIN 92-0038225 |
| Norton Sound Health Corporation | AK | FAC single audit 2022, EIN 92-0041488 |
| Southcentral Foundation | AK | USAspending assistance, UEI SMQ9D8WCGWY9, $957M obligations |
| Southeast Alaska Regional Health Consortium | AK | USAspending assistance, UEI F3NBRWQM8M69 |
| Yukon-Kuskokwim Health Corporation | AK | FAC single audit 2020, EIN 92-0041414; USAspending $767M |
| Eastern Aleutian Tribes | AK | FAC single audit 2025, EIN 92-0139107 |
| Mount Sanford Tribal Consortium | AK | FAC single audit 2025, EIN 92-0143492 |
| Northern Valley Indian Health, Inc. | CA | FAC single audit 2022, EIN 94-1747220 |
| Riverside-San Bernardino County Indian Health, Inc. | CA | FAC single audit 2024, EIN 95-2846605; USAspending $149M |
| Consolidated Tribal Health Project, Inc. | CA | FAC single audit 2023, EIN 94-2891496 |
| Indian Health Council, Inc. | CA | FAC single audit, EIN 95-2506788; USAspending $71M |
| Feather River Tribal Health, Inc. | CA | FAC single audit 2025, EIN 68-0440292 |
| Chapa-De Indian Health Program, Inc. | CA | FAC single audit 2019, EIN 94-2583156; USAspending $51M |
| Southern Indian Health Council, Inc. | CA | FAC single audit 2024, EIN 95-3782164; USAspending $43M |
| Lake County Tribal Health Consortium, Inc. | CA | FAC single audit 2022, EIN 94-2847137; USAspending $53M |
| Sonoma County Indian Health Project, Inc. | CA | FAC single audit 2025, EIN 94-1741896 |
| Utah Navaho Health System, Inc. | UT | FAC single audit 2019, EIN 87-0560763 |
| Winslow Indian Health Care Center, Inc. | AZ | FAC single audit 2025, EIN 81-0549382; USAspending $248M |
| Northeastern Tribal Health System | OK | FAC single audit 2025, EIN 73-1588323 (FAC records the auditee address in TX; IHS files it in the Oklahoma City Area and its facility is in Miami, Oklahoma) |

### Named on the roster and deliberately NOT added

| organisation | why not |
|---|---|
| Arctic Slope Native Association | COLLISION. `503_identity.resolve()` returns AKNF-ARCTIC-00 (Arctic Village) on a distinctive-token match, and the distinctive-token scan additionally hits ANRC-ARCSLO-00 (Arctic Slope Regional Corporation) on {ARCTIC, SLOPE}. Both hits are WRONG - ASNA is the North Slope regional health organisation, and it is neither the Interior village nor the ANCSA corporation - but standing rule 3 of this pass is that any resolver hit is a refusal. Promoting past a resolver hit is how one entity becomes two. Queued with the resolver defect reported. |
| Tuba City Regional Health Care Corporation | COLLISION. The distinctive-token scan finds TWO rare tokens - {CITY, TUBA} - shared with BIE-TBCTYB-00 Tuba City Boarding School. They are different organisations that share a place name, and this script believes so, but two shared rare tokens is the threshold at which a name is plausibly one organisation and the refusal stands. Queued for an owner ruling; corroborated by FAC single audit 2025, EIN 04-3651340, and it is the Navajo Area Title V compactor. |
| Alaska Native Tribal Health Consortium | ALREADY IN THE SPINE as ITO-LSKHLT-00, filed under `Intertribal Organization` rather than this class. Not promoted, not re-classed - a re-class is a ruling. Reported as a class-placement inconsistency. |
| Great Plains Tribal Leaders Health Board | ALREADY IN THE SPINE as ITO-GRTPL1-00, same inconsistency as ANTHC. |
| Aleutian Pribilof Islands Association | already in spine SGVF-PRBLFA-00 |
| Bristol Bay Area Health Corporation | already in spine SGVF-BRSTLB-00 |
| Chugachmiut | already in spine SGVF-CHGCMT-00 - but its canonical_name is 'Chugachmiut self-governance consortium', a DESCRIPTION rather than the organisation's legal name, so `resolve('Chugachmiut')` returns None. Reported as an alias gap, not fixed here. |
| Copper River Native Association | already in spine SGVF-CPPRRV-00 |
| Maniilaq Association | already in spine SGVF-MANLLQ-00 |
| Tanana Chiefs Conference | already in spine SGVF-TNNACH-00 |
| Council of Athabascan Tribal Governments | already in spine SGVF-CATHTG-00 |

**The Arctic Slope refusal is the most useful row in this document.** `503_identity.resolve('Arctic Slope Native Association')` returns `AKNF-ARCTIC-00`, *Arctic Village* — a Gwich'in village government in the Interior, roughly 600 miles from the North Slope. The distinctive token set for *Arctic Village* reduces to `{ARCTIC}`, and `{ARCTIC}` is a subset of the filed name, so the gov-class token path claims it "uniquely". The scan also hits `ANRC-ARCSLO-00` *Arctic Slope Regional Corporation* on `{ARCTIC, SLOPE}` — the ANCSA corporation, not the health organisation. Both are wrong and the promotion was refused anyway, because a resolver hit is a refusal. **The defect is the single-token gov match, and it is reported to workstream I rather than patched here** (`503` is not this workstream's file).

---

## Part 1 — the three-way split

**"We have 349 tribes" means nothing without "and the roster has N."** Each class is placed by the state of its ROSTER, not by our diligence. Counts are post-append.

| class | held | authoritative universe | state | roster |
|---|---:|---:|---|---|
| Federally recognized tribe | 349 | — | **see below** | (see FEDERAL RECOGNITION below) |
| Federally recognized Alaska Native Village | 228 | — | **see below** | (see FEDERAL RECOGNITION below) |
| Native Hawaiian Organization | 210 | **no roster** | **OPEN** | [no authoritative roster exists](https://www.doi.gov/hawaiian) |
| BIE School | 185 | 187 | **COMPLETE** | [BIE Schools Directory feature service](https://services1.arcgis.com/UxqqIfhng71wUT9x/arcgis/rest/services/BIE_Schools_Directory/FeatureServer/0) |
| Alaska Native Village Corporation | 173 | **no roster** | **OPEN** | [no current roster is published](https://www.commerce.alaska.gov/cbp/main) |
| Native Community Development Financial Institution | 64 | 65 | **INCOMPLETE** | [Treasury CDFI Fund, Currently Certified CDFIs](https://www.cdfifund.gov/media/8018641/download?inline) |
| State-recognized tribe | 64 | **no roster** | **OPEN** | no authoritative roster exists |
| Intertribal Organization | 56 | **no roster** | **OPEN** | no authoritative roster exists |
| Individually Native-owned business | 45 | **no roster** | **OPEN** | no roster can exist |
| Urban Indian Organization | 43 | 44 | **COMPLETE** | [IHS Office of Urban Indian Health Programs, Title V contractors](https://www.ihs.gov/urban/urban-indian-organizations/) |
| Tribal College or University | 37 | 37 | **COMPLETE** | [AIHEC TCU Roster and Profiles](https://www.aihec.org/tcu-roster-and-profiles/) |
| Native Financial Institution | 29 | 91 | **COUNTED WITH THE CDFI ROW** | [CICD / Minneapolis Fed Native financial institutions map data](https://github.com/frb-mpls-cde/nafi-map/raw/refs/heads/main/data/nafi-map-data_current.xlsx) |
| Federal-level constituency entity | 22 | **no roster** | **OPEN** | derived, not published |
| Alaska Native Regional Corporation | 12 | 13 | **INCOMPLETE** | [ANCSA s.7, 43 U.S.C. 1606](https://www.govinfo.gov/content/pkg/USCODE-2024-title43/html/USCODE-2024-title43-chap33-sec1606.htm) |
| Federal-level self-governance consortium | 29 | 27 | **INCOMPLETE** | [IHS Tribal Self-Governance Program participants, non-tribe organisations](https://www.ihs.gov/selfgovernance/tribes/) |
| ANCSA Group Corporation | 6 | **no roster** | **OPEN** | [no roster is published](https://www.govinfo.gov/content/pkg/USCODE-2024-title43/html/USCODE-2024-title43-chap33-sec1607.htm) |
| State-level constituency entity | 3 | **no roster** | **OPEN** | derived, not published |

Four of those states are NOT what a raw count comparison would give, and each override is a named reason rather than a rounding:

- **BIE School → COMPLETE.** 187 features minus Haskell and SIPI, which are post-secondary and sit in the TCU class. 185 of 185 elementary/secondary held.
- **Urban Indian Organization → COMPLETE.** 44 distinct bodies on the IHS Title V roster; 43 are in this class and the 44th, NCUIH, is in the spine as ITO-RBNHLT-00. All 44 held. **This is complete against the TITLE V roster only** - urban Indian CENTRES without a Title V health contract are a separate and OPEN population.
- **Native Financial Institution → COUNTED WITH THE CDFI ROW.** The CICD roster of 91 OVERLAPS the CDFI Fund roster of 65 and Cedar splits them into two classes (64 + 29 = 93). The overlap is not measured here, so the two counts are not subtractable and this class cannot be given a state of its own.
- **Federal-level self-governance consortium → INCOMPLETE.** 29 held exceeds the 27-organisation IHS roster only because this class ALSO holds Alaska regional social-service consortia (Kawerak, AVCP, Bristol Bay Native Association) that are not IHS compactors. Against the roster itself **2 are still missing** - Arctic Slope Native Association and Tuba City Regional Health Care Corporation, both refused on a name collision and queued - and the BIA Office of Self-Governance compact list has not been pulled at all, so 27 is a floor rather than the universe.

Why each OPEN class is open, in one line each:

- **Native Hawaiian Organization** — DOI ONHR maintains an NHPA CONSULTATION notification list, not a register of NHOs. There is no federal recognition process for an NHO and no closed universe. 179 of the 210 held come from that list.
- **Alaska Native Village Corporation** — ANCSA s.8 authorised a corporation for each listed village; the surviving set changes by merger, dissolution and reinstatement, and AS 10.06.960(k) permits reinstatement AT ANY TIME. Alaska's corporations database publishes no 'ANCSA corporation' flag.
- **State-recognized tribe** — Recognition is granted state by state, by statute, executive order or commission, with no federal register and no interstate list.
- **Intertribal Organization** — No register of intertribal organisations exists at any level.
- **Individually Native-owned business** — Membership turns on an individual's ownership of a firm. Open by construction, discovery-driven and privacy-restricted.
- **Federal-level constituency entity** — Bands and sub-governments named in Federal Register parentheticals. The FR list is authoritative for its own parentheticals but publishes no count of them.
- **ANCSA Group Corporation** — ANCSA s.14(h)(2) group corporations were formed case by case on BLM determinations; no consolidated list is published.
- **State-level constituency entity** — Same shape as the federal constituency class, from state instruments.

### FEDERAL RECOGNITION — the one roster Cedar holds as data

`data/clean/federal_recognition_roster.csv`, notice year **2026**:

| | |
|---|---:|
| entities listed (`entity` + `rename`) | **573** |
| cross-reference pointers to entries already listed | 4 |
| listed entities resolving to a spine government entity | **570** |
| listed names this audit could not resolve | 0 |
| spine rows in the two federally-recognised government classes | **577** |

**Verdict: COMPLETE, and the 4-row difference reconciles exactly.** The universe is 573 listed entities; the spine holds 577 government rows, which is 573 + the 4 cross-reference entries. Those four — Arctic Village, Village of Venetie, St. Paul Island and St. George Island — are named on the list only as pointers into two COMBINED listings (Native Village of Venetie Tribal Government; Pribilof Islands Aleut Communities of St. Paul & St. George Islands), and Cedar holds each as its own row because money arrives addressed to it. That is the constituency-entity pattern `NATIVE_ENTITY_NUANCES.md` documents, not four extra tribes.

The split of 349 `Federally recognized tribe` + 228 `Federally recognized Alaska Native Village` is **geographic, not legal** — quoting 349 as "the federally recognised tribes" understates the universe by 40%.

**But the roster TABLE's own `tribe_id` column is not coverage.** 527 of 573 listed rows carry a `tribe_id`, and some that do are keyed to the wrong CLASS:

| listed entity (a GOVERNMENT) | keyed to | defect |
|---|---|---|
| Algaaciq Native Village (St. Mary's) | `ANVC-STMRYS-00` | keyed to an ANCSA **corporation** — the Elim defect, live in the roster of record |
| Native Village of Chuathbaluk (Russian Mission, Kuskokwim) | `ANVC-RSSNMS-00` | keyed to an ANCSA **corporation** — the Elim defect, live in the roster of record |
| Native Village of Elim | `ANVC-ELIMXX-00` | keyed to an ANCSA **corporation** — the Elim defect, live in the roster of record |
| Native Village of Shishmaref | `ANVC-SHSHMR-00` | keyed to an ANCSA **corporation** — the Elim defect, live in the roster of record |

A second live instance of a documented trap: the 2026 listing of **Oneida Nation** (Wisconsin) is keyed to `TRBF-ONDANY-00`, the **Oneida Indian Nation of New York**. Both are keying bugs in one table, not universe gaps, and both belong to that table's owner — recorded here because a reader counting keyed rows would otherwise read them as coverage.

### Reading the split

- **COMPLETE — 3 classes**, plus federal recognition.
- **OPEN — 8 classes.** No authoritative roster exists, so the universe **cannot be sized** and this audit refuses to invent a denominator. NHOs are the known example and are not the only one.
- **INCOMPLETE — 3 classes.**

**OPEN is not a softer word for INCOMPLETE.** For an open class, "complete" is not a state the data can reach, and any coverage percentage quoted against it is invented. For an incomplete class the shortfall is a work item with a known end.

---

## Part 2 — organisations with federal evidence and no spine entity

### The evidence standard, stated before any claim

`docs/NATIVE_ENTITY_NUANCES.md` records the governing counter-example: **TUSCARAWAS METROPOLITAN HOUSING** is an Ohio county authority named for a Delaware-origin place. A Native-sounding name is not evidence. Nothing below was admitted on a name.

| family | the declaration | who made it |
|---|---|---|
| `SAM_BUSINESS_TYPE` | certified in SAM as an Indian/Native American Tribal Designated Organization, tribal government other than federally recognised, or a Tribally Controlled College or University | the registrant, under FAR — the LR_SAM family: self-certified, but a legal declaration, not a name |

**Two adjacent SAM codes were tried and rejected**, which is the Tuscarawas rule applied to a checkbox rather than a name. `PUBLIC/INDIAN HOUSING AUTHORITY` gives a HUD public housing authority and a tribally designated housing entity the *same value* — including it put Cumberland Valley Regional Housing Authority and Boone County Assisted Housing Department at the top of the TDHE probe, and a code that cannot tell the two apart is evidence of neither. `ALASKA NATIVE AND NATIVE HAWAIIAN SERVING INSTITUTIONS` is a Department of Education MSI designation earned by *enrolment share*, which University of Alaska campuses hold; it says who a college serves, never who controls it. TDHEs still surface, through CFDA 14.867, whose statute restricts eligibility to tribes and TDHEs — eligibility is the evidence, the checkbox was not.
| `FAC_TRIBAL_AUDITEE` | `entity_type = tribal` on a Single Audit submission | the auditee, to the Federal Audit Clearinghouse — **self-declared, and it does carry filing errors: see below** |
| `TRIBAL_ONLY_PROGRAM` | obligations under a programme whose **statute** limits eligibility to tribes, tribal organisations, TDHEs, Native Hawaiian/Alaska Native organisations or UIOs | the awarding agency, by making the award |
| `CEDAR_NP_RULING` | `native_controlled` / `tribally_controlled` / `native_serving` in `np_orgs` | a Cedar human ruling |

The programme whitelist is 25 CFDA codes, each with its restricting statute, hard-coded in the script. **A title regex is deliberately not used**: *Impact Aid* (84.041) and *Indian Education — Grants to Local Educational Agencies* (84.060) both say "Indian" and both pay public school districts.

**`FAC_TRIBAL_AUDITEE` alone is not enough, and here is the specimen that proves it.** *Cumberland Valley Regional Housing Authority* (Barbourville, **Kentucky**, EIN 61-1001084) and *Boone County Assisted Housing Department* (Burlington, **Kentucky**, EIN 61-6000718) both filed Single Audits with `entity_type = tribal`. They are county housing authorities and the tick is a filing error — in a federal system of record. The `n_evidence_families` column exists for exactly this: **a reader should require two families before treating a row as an organisation, and single-family rows are ranked below multi-family ones throughout this document.**

### And a candidate is only a gap if the spine does not already hold it

*"A spine gap is usually an alias gap."* Four suppressions run before anything is reported:

| # | suppression | fired |
|---:|---|---:|
| 1 | **institutional form** — the name's own form says city, county, state agency, federal agency, university system or school district | 564 |
| 2 | **identifier** — UEI/EIN bound to a spine entity in the ledger or the nonprofit EIN hub (tier X is a refutation and does not suppress) | 1,917 |
| 3 | **exact name** — folded name equals a spine canonical name, alias, FR official name or former name | 188 |
| 4 | **name variant** — same name once governmental filler is stripped from both ends, or contains a spine alias whose residue is all governmental. *SAN CARLOS APACHE TRIBE* is the San Carlos Apache Tribe; *CHEYENNE RIVER HOUSING AUTHORITY* is not the Cheyenne River Sioux Tribe. | 141 |
| — | **survives as a candidate** | **2,412** |

Suppression 4 is where the interesting case lives. A name that contains a spine alias but whose residue is **substantive** — `housing authority`, `health corporation`, `school board` — is *not* suppressed; it is kept with the related spine entity recorded, because an **affiliate** of a known entity is precisely the organisation the master list does not hold.

**2,412 organisations survive.** 314 carry two or more independent evidence families. Sorted by family count, then size. `size` is the largest of federal assistance obligations, single-audit federal awards expended, or IRS BMF revenue — `basis` says which, and **the three are different quantities and must never be summed across rows.**

| # | organisation | st | families | size (USD) | basis | evidence |
|---:|---|---|---|---:|---|---|
| 1 | THE CHEROKEE BOYS CLUB INC | NC | FAC_TRIBAL_AUDITEE + SAM_BUSINESS_TYPE + TRIBAL_ONLY_PROGRAM | 243,946,257 | federal assistance obligations | SAM certified federally-recognised tribal government on 50 rows; $119,954,800 under CFDA 15.042 (Indian School Equalization); $90,737,532 under CFDA 15.047 (Indian Education Facilities O&M); declared  |
| 2 | CENTRAL VALLEY INDIAN HEALTH INC | CA | FAC_TRIBAL_AUDITEE + SAM_BUSINESS_TYPE + TRIBAL_ONLY_PROGRAM | 174,321,640 | federal assistance obligations | SAM business type certified Native on 27 of 135 assistance rows; $167,013,501 under CFDA 93.441 (Indian Self-Determination); $7,308,139 under CFDA 93.237 (Special Diabetes Program for Indians); declar |
| 3 | TOIYABE INDIAN HEALTH PROJECT, INC. | CA | FAC_TRIBAL_AUDITEE + SAM_BUSINESS_TYPE + TRIBAL_ONLY_PROGRAM | 113,166,055 | federal awards expended (single audit) | SAM business type certified Native on 98 of 148 assistance rows; $41,175,141 under CFDA 93.441 (Indian Self-Determination); $5,608,840 under CFDA 93.237 (Special Diabetes Program for Indians); declare |
| 4 | EIGHT NORTHERN INDIAN PUEBLOS COUNCIL INC | NM | FAC_TRIBAL_AUDITEE + SAM_BUSINESS_TYPE + TRIBAL_ONLY_PROGRAM | 58,763,602 | federal awards expended (single audit) | SAM business type certified Native on 149 of 522 assistance rows; $13,052,062 under CFDA 93.441 (Indian Self-Determination); $11,724,018 under CFDA 10.567 (FDPIR); declared entity_type=tribal on 9 Fed |
| 5 | ORUTSARARMIUT NATIVE COUNCIL | AK | FAC_TRIBAL_AUDITEE + SAM_BUSINESS_TYPE + TRIBAL_ONLY_PROGRAM | 53,967,916 | federal awards expended (single audit) | SAM certified federally-recognised tribal government on 1 rows; $758,508 under CFDA 15.022 (Tribal Self-Governance); declared entity_type=tribal on 4 Federal Audit Clearinghouse submission(s) |
| 6 | FAIRBANKS NATIVE ASSOCIATION, | AK | FAC_TRIBAL_AUDITEE + SAM_BUSINESS_TYPE + TRIBAL_ONLY_PROGRAM | 48,439,058 | federal assistance obligations | SAM business type certified Native on 200 of 290 assistance rows; $4,175,225 under CFDA 93.441 (Indian Self-Determination); $948,263 under CFDA 93.612 (Native American Programs (ANA)); declared entity |
| 7 | TUBA CITY HIGH SCHOOL BOARD, INC | AZ | FAC_TRIBAL_AUDITEE + SAM_BUSINESS_TYPE + TRIBAL_ONLY_PROGRAM | 46,443,589 | federal awards expended (single audit) | SAM certified federally-recognised tribal government on 3 rows; $3,314,764 under CFDA 15.042 (Indian School Equalization); $2,274,733 under CFDA 15.047 (Indian Education Facilities O&M); declared enti |
| 8 | FIVE SANDOVAL INDIAN PUEBLOS INC | NM | FAC_TRIBAL_AUDITEE + SAM_BUSINESS_TYPE + TRIBAL_ONLY_PROGRAM | 36,078,671 | federal awards expended (single audit) | SAM business type certified Native on 32 of 478 assistance rows; $9,783,482 under CFDA 10.567 (FDPIR); $8,588,243 under CFDA 93.441 (Indian Self-Determination); declared entity_type=tribal on 9 Federa |
| 9 | 1854 TREATY AUTHORITY | MN | FAC_TRIBAL_AUDITEE + SAM_BUSINESS_TYPE + TRIBAL_ONLY_PROGRAM | 27,533,949 | federal assistance obligations | SAM business type certified Native on 31 of 99 assistance rows; $22,466,916 under CFDA 15.036 (Indian Rights Protection); $1,612,427 under CFDA 15.035 (Forestry on Indian Lands); declared entity_type= |
| 10 | HEALING LODGE OF THE SEVEN NATIONS,THE | WA | FAC_TRIBAL_AUDITEE + SAM_BUSINESS_TYPE + TRIBAL_ONLY_PROGRAM | 25,988,477 | federal awards expended (single audit) | SAM business type certified Native on 27 of 28 assistance rows; $8,723,589 under CFDA 93.441 (Indian Self-Determination); declared entity_type=tribal on 7 Federal Audit Clearinghouse submission(s) |
| 11 | INTERTRIBAL BUFFALO COUNCIL | SD | FAC_TRIBAL_AUDITEE + SAM_BUSINESS_TYPE + TRIBAL_ONLY_PROGRAM | 23,776,158 | federal assistance obligations | SAM business type certified Native on 17 of 39 assistance rows; $2,349,444 under CFDA 15.024 (ISD Contract Support); $601,240 under CFDA 93.612 (Native American Programs (ANA)); declared entity_type=t |
| 12 | TAGIUGMIULLU NUNAMIULLU HOUSING AUTHORITY | AK | FAC_TRIBAL_AUDITEE + SAM_BUSINESS_TYPE + TRIBAL_ONLY_PROGRAM | 23,515,486 | federal assistance obligations | SAM certified federally-recognised tribal government on 7 rows; $27,495,473 under CFDA 14.867 (IHBG); declared entity_type=tribal on 1 Federal Audit Clearinghouse submission(s) |
| 13 | UPPER COLUMBIA UNITED TRIBES | WA | FAC_TRIBAL_AUDITEE + SAM_BUSINESS_TYPE + TRIBAL_ONLY_PROGRAM | 23,417,274 | federal assistance obligations | SAM business type certified Native on 7 of 72 assistance rows; $9,731,312 under CFDA 15.036 (Indian Rights Protection); $2,728,095 under CFDA 15.024 (ISD Contract Support); declared entity_type=tribal |
| 14 | BARANOF ISLAND HOUSING AUTHORITY | AK | FAC_TRIBAL_AUDITEE + SAM_BUSINESS_TYPE + TRIBAL_ONLY_PROGRAM | 20,165,811 | federal awards expended (single audit) | SAM certified federally-recognised tribal government on 5 rows; $7,959,146 under CFDA 14.867 (IHBG); declared entity_type=tribal on 9 Federal Audit Clearinghouse submission(s) |
| 15 | UNITED AMERICAN INDIAN INVOLVEMENT INC | CA | FAC_TRIBAL_AUDITEE + SAM_BUSINESS_TYPE + TRIBAL_ONLY_PROGRAM | 18,952,386 | federal assistance obligations | SAM business type certified Native on 1 of 83 assistance rows; $6,387,487 under CFDA 93.193 (Urban Indian Health); $5,122,257 under CFDA 17.265 (Native American Employment and Training); declared enti |
| 16 | INTER TRIBAL COUNCIL INC | OK | FAC_TRIBAL_AUDITEE + SAM_BUSINESS_TYPE + TRIBAL_ONLY_PROGRAM | 18,619,584 | federal assistance obligations | SAM business type certified Native on 17 of 262 assistance rows; $10,137,645 under CFDA 10.567 (FDPIR); $2,500,000 under CFDA 11.029 (Tribal Broadband Connectivity); declared entity_type=tribal on 2 F |
| 17 | KODIAK ISLAND HOUSING AUTHORITY | AK | FAC_TRIBAL_AUDITEE + SAM_BUSINESS_TYPE + TRIBAL_ONLY_PROGRAM | 18,582,663 | federal assistance obligations | SAM certified federally-recognised tribal government on 4 rows; $18,393,009 under CFDA 14.867 (IHBG); declared entity_type=tribal on 1 Federal Audit Clearinghouse submission(s) |
| 18 | POINT NO POINT TREATY COUNCIL | WA | FAC_TRIBAL_AUDITEE + SAM_BUSINESS_TYPE + TRIBAL_ONLY_PROGRAM | 17,403,509 | federal awards expended (single audit) | SAM business type certified Native on 10 of 52 assistance rows; $3,533,500 under CFDA 15.036 (Indian Rights Protection); $719,190 under CFDA 15.024 (ISD Contract Support); declared entity_type=tribal  |
| 19 | STRONG FAMILY HEALTH CENTER | CA | FAC_TRIBAL_AUDITEE + SAM_BUSINESS_TYPE + TRIBAL_ONLY_PROGRAM | 15,543,444 | federal assistance obligations | SAM business type certified Native on 29 of 122 assistance rows; $15,340,766 under CFDA 93.441 (Indian Self-Determination); $202,678 under CFDA 93.237 (Special Diabetes Program for Indians); declared  |
| 20 | ALASKA NATIVE JUSTICE CENTER, INC. | AK | FAC_TRIBAL_AUDITEE + SAM_BUSINESS_TYPE + TRIBAL_ONLY_PROGRAM | 13,894,751 | federal awards expended (single audit) | SAM business type certified Native on 29 of 58 assistance rows; $3,444,638 under CFDA 16.587 (VAWA grants to Indian tribal governments); $1,314,704 under CFDA 93.612 (Native American Programs (ANA));  |
| 21 | ALEUTIAN HOUSING AUTHORITY | AK | FAC_TRIBAL_AUDITEE + SAM_BUSINESS_TYPE + TRIBAL_ONLY_PROGRAM | 13,349,893 | federal assistance obligations | SAM certified federally-recognised tribal government on 5 rows; $13,483,836 under CFDA 14.867 (IHBG); declared entity_type=tribal on 2 Federal Audit Clearinghouse submission(s) |
| 22 | NORTHWEST INTERTRIBAL COURT SYSTEM | WA | FAC_TRIBAL_AUDITEE + SAM_BUSINESS_TYPE + TRIBAL_ONLY_PROGRAM | 9,671,800 | federal awards expended (single audit) | SAM business type certified Native on 15 of 37 assistance rows; $3,243,297 under CFDA 15.024 (ISD Contract Support); $1,116,018 under CFDA 93.612 (Native American Programs (ANA)); declared entity_type |
| 23 | NATIVE AMERICAN PROFESSIONAL PARENT RESOURCES INC | NM | FAC_TRIBAL_AUDITEE + SAM_BUSINESS_TYPE + TRIBAL_ONLY_PROGRAM | 7,611,162 | federal awards expended (single audit) | SAM certified federally-recognised tribal government on 8 rows; $255,627 under CFDA 93.612 (Native American Programs (ANA)); declared entity_type=tribal on 3 Federal Audit Clearinghouse submission(s) |
| 24 | RED CLOUD INDIAN SCHOOL, INC. | SD | FAC_TRIBAL_AUDITEE + SAM_BUSINESS_TYPE + TRIBAL_ONLY_PROGRAM | 4,852,546 | federal awards expended (single audit) | SAM certified federally-recognised tribal government on 3 rows; $106,769 under CFDA 93.612 (Native American Programs (ANA)); declared entity_type=tribal on 4 Federal Audit Clearinghouse submission(s) |
| 25 | CLARE SWAN EARLY LEARNING CENTER | AK | FAC_TRIBAL_AUDITEE + SAM_BUSINESS_TYPE + TRIBAL_ONLY_PROGRAM | 3,273,814 | federal awards expended (single audit) | SAM business type certified Native on 3 of 15 assistance rows; $1,084,382 under CFDA 93.612 (Native American Programs (ANA)); declared entity_type=tribal on 1 Federal Audit Clearinghouse submission(s) |
| 26 | DENVER INDIAN CENTER, INC. | CO | FAC_TRIBAL_AUDITEE + SAM_BUSINESS_TYPE + TRIBAL_ONLY_PROGRAM | 2,553,450 | federal assistance obligations | SAM certified federally-recognised tribal government on 5 rows; $2,151,529 under CFDA 17.265 (Native American Employment and Training); declared entity_type=tribal on 1 Federal Audit Clearinghouse sub |
| 27 | TAMAYA HOUSING INC | NM | FAC_TRIBAL_AUDITEE + SAM_BUSINESS_TYPE + TRIBAL_ONLY_PROGRAM | 2,225,383 | federal assistance obligations | SAM certified federally-recognised tribal government on 4 rows; $1,620,383 under CFDA 14.867 (IHBG); $605,000 under CFDA 14.862 (ICDBG); declared entity_type=tribal on 1 Federal Audit Clearinghouse su |
| 28 | FLORIDA GOVERNOR'S COUNCIL ON INDIAN AFFAIRS, INC. | FL | FAC_TRIBAL_AUDITEE + SAM_BUSINESS_TYPE + TRIBAL_ONLY_PROGRAM | 1,304,581 | federal assistance obligations | SAM certified federally-recognised tribal government on 1 rows; $1,304,581 under CFDA 17.265 (Native American Employment and Training); declared entity_type=tribal on 1 Federal Audit Clearinghouse sub |
| 29 | SOUTHERN CALIFORNIA AMERICAN INDIAN RESOURCE CENTER, INC | CA | FAC_TRIBAL_AUDITEE + SAM_BUSINESS_TYPE + TRIBAL_ONLY_PROGRAM | 855,168 | federal awards expended (single audit) | SAM certified federally-recognised tribal government on 1 rows; $748,665 under CFDA 17.265 (Native American Employment and Training); declared entity_type=tribal on 1 Federal Audit Clearinghouse submi |
| 30 | DENA NENA HENASH | AK | SAM_BUSINESS_TYPE + TRIBAL_ONLY_PROGRAM | 1,562,751,462 | federal assistance obligations | SAM business type certified Native on 315 of 1,523 assistance rows; $1,098,359,952 under CFDA 93.210 (Tribal Self-Governance IHS compacts); $279,525,323 under CFDA 15.022 (Tribal Self-Governance) |
| 31 | FORT DEFIANCE INDIAN HOSPITAL BOARD, INC. | AZ | SAM_BUSINESS_TYPE + TRIBAL_ONLY_PROGRAM | 820,809,418 | federal assistance obligations | SAM business type certified Native on 75 of 222 assistance rows; $814,937,306 under CFDA 93.441 (Indian Self-Determination); $4,953,267 under CFDA 93.237 (Special Diabetes Program for Indians) |
| 32 | ROCK POINT SCHOOL, INCORPORATED | AZ | SAM_BUSINESS_TYPE + TRIBAL_ONLY_PROGRAM | 105,207,406 | federal assistance obligations | SAM business type certified Native on 10 of 173 assistance rows; $105,070,563 under CFDA 15.042 (Indian School Equalization); $4,663 under CFDA 15.047 (Indian Education Facilities O&M) |
| 33 | ROUGH ROCK SCHOOL BOARD, INC. | AZ | SAM_BUSINESS_TYPE + TRIBAL_ONLY_PROGRAM | 85,634,360 | federal assistance obligations | SAM certified federally-recognised tribal government on 55 rows; $49,639,811 under CFDA 15.042 (Indian School Equalization); $29,866,920 under CFDA 15.047 (Indian Education Facilities O&M) |
| 34 | K'IMA:W MEDICAL CENTER | CA | FAC_TRIBAL_AUDITEE + SAM_BUSINESS_TYPE | 72,796,833 | federal awards expended (single audit) | SAM business type certified Native on 8 of 77 assistance rows; declared entity_type=tribal on 8 Federal Audit Clearinghouse submission(s) |
| 35 | INTERIOR REGIONAL HOUSING AUTHORITY | AK | SAM_BUSINESS_TYPE + TRIBAL_ONLY_PROGRAM | 50,298,226 | federal assistance obligations | SAM business type certified Native on 1 of 11 assistance rows; $50,116,912 under CFDA 14.867 (IHBG) |
| 36 | SOUTH PUGET INTERTRIBAL PLANNING AGENCY | WA | SAM_BUSINESS_TYPE + TRIBAL_ONLY_PROGRAM | 46,219,298 | federal assistance obligations | SAM business type certified Native on 143 of 296 assistance rows; $5,363,863 under CFDA 10.567 (FDPIR) |
| 37 | WABANAKI PUBLIC HEALTH & WELLNESS NPC | ME | SAM_BUSINESS_TYPE + TRIBAL_ONLY_PROGRAM | 27,315,983 | federal assistance obligations | SAM business type certified Native on 149 of 215 assistance rows; $0 under CFDA 93.612 (Native American Programs (ANA)) |
| 38 | M.A.C.T. HEALTH BOARD, INCORPORATED | CA | SAM_BUSINESS_TYPE + TRIBAL_ONLY_PROGRAM | 24,797,391 | federal assistance obligations | SAM business type certified Native on 28 of 28 assistance rows; $24,797,391 under CFDA 93.441 (Indian Self-Determination); $0 under CFDA 93.237 (Special Diabetes Program for Indians) |
| 39 | EQUITABLE HEALTH CORPORATION | NY | SAM_BUSINESS_TYPE + TRIBAL_ONLY_PROGRAM | 23,957,422 | federal assistance obligations | SAM business type certified Native on 4 of 4 assistance rows; $23,957,422 under CFDA 93.441 (Indian Self-Determination) |
| 40 | INDIAN BOARD OF EDUCATION FOR PIERRE | SD | SAM_BUSINESS_TYPE + TRIBAL_ONLY_PROGRAM | 19,798,280 | federal assistance obligations | SAM business type certified Native on 26 of 91 assistance rows; $11,467,744 under CFDA 15.042 (Indian School Equalization); $2,796,263 under CFDA 15.047 (Indian Education Facilities O&M) |
| 41 | PHOENIX INDIAN CENTER | AZ | SAM_BUSINESS_TYPE + TRIBAL_ONLY_PROGRAM | 18,977,925 | federal assistance obligations | SAM certified federally-recognised tribal government on 3 rows; $18,977,925 under CFDA 17.265 (Native American Employment and Training) |
| 42 | SMALL TRIBES ORGANIZATION OF WESTERN WAS | WA | SAM_BUSINESS_TYPE + TRIBAL_ONLY_PROGRAM | 17,590,011 | federal assistance obligations | SAM business type certified Native on 22 of 149 assistance rows; $17,173,848 under CFDA 10.567 (FDPIR) |
| 43 | CENTRAL OKLAHOMA AMERICAN INDIAN HEALTH COUNCIL, INC. *(affiliate of `SGVF-NDNHLT-00` — Indian Health Council, Inc.)* | OK | SAM_BUSINESS_TYPE + TRIBAL_ONLY_PROGRAM | 16,601,688 | federal assistance obligations | SAM business type certified Native on 25 of 105 assistance rows; $10,676,399 under CFDA 93.237 (Special Diabetes Program for Indians) |
| 44 | MANDAREE PUBLIC SCHOOL | ND | SAM_BUSINESS_TYPE + TRIBAL_ONLY_PROGRAM | 16,439,436 | federal assistance obligations | SAM certified federally-recognised tribal government on 45 rows; $7,304,315 under CFDA 15.042 (Indian School Equalization); $3,516,146 under CFDA 15.047 (Indian Education Facilities O&M) |
| 45 | ALU LIKE INC | HI | SAM_BUSINESS_TYPE + TRIBAL_ONLY_PROGRAM | 16,415,623 | federal assistance obligations | SAM certified federally-recognised tribal government on 7 rows; $15,895,923 under CFDA 17.265 (Native American Employment and Training) |
| 46 | NORTH PACIFIC RIM HOUSING AUTHORITY | AK | SAM_BUSINESS_TYPE + TRIBAL_ONLY_PROGRAM | 15,946,526 | federal assistance obligations | SAM certified federally-recognised tribal government on 8 rows; $18,508,670 under CFDA 14.867 (IHBG) |
| 47 | TWO FEATHERS NATIVE AMERICAN FAMILY SERVICES | CA | FAC_TRIBAL_AUDITEE + SAM_BUSINESS_TYPE | 14,854,926 | federal awards expended (single audit) | SAM business type certified Native on 43 of 49 assistance rows; declared entity_type=tribal on 6 Federal Audit Clearinghouse submission(s) |
| 48 | MNI WASTE' WATER COMPANY | SD | FAC_TRIBAL_AUDITEE + SAM_BUSINESS_TYPE | 13,396,279 | federal awards expended (single audit) | SAM certified federally-recognised tribal government on 2 rows; declared entity_type=tribal on 1 Federal Audit Clearinghouse submission(s) |
| 49 | FIRST NATIONS COMMUNITY HEALTH SOURCE INC | NM | SAM_BUSINESS_TYPE + TRIBAL_ONLY_PROGRAM | 12,345,486 | federal assistance obligations | SAM business type certified Native on 21 of 58 assistance rows; $2,570,774 under CFDA 93.193 (Urban Indian Health); $1,964,885 under CFDA 93.237 (Special Diabetes Program for Indians) |
| 50 | RED LAKE BAND OF CHIPPEWA | MN | SAM_BUSINESS_TYPE + TRIBAL_ONLY_PROGRAM | 12,095,110 | federal assistance obligations | SAM certified federally-recognised tribal government on 1 rows; $12,095,110 under CFDA 15.022 (Tribal Self-Governance) |
| 51 | HAUDENOSAUNEE ENVIRONMENTAL TASK FORCE | NY | SAM_BUSINESS_TYPE + TRIBAL_ONLY_PROGRAM | 11,401,075 | federal assistance obligations | SAM business type certified Native on 10 of 59 assistance rows; $8,386,528 under CFDA 66.926 (Indian Environmental GAP); $1,500,000 under CFDA 11.029 (Tribal Broadband Connectivity) |
| 52 | AMERICAN INDIAN ASSOCIATION OF TUCSON, INC. | AZ | SAM_BUSINESS_TYPE + TRIBAL_ONLY_PROGRAM | 10,153,540 | federal assistance obligations | SAM certified federally-recognised tribal government on 15 rows; $5,463,223 under CFDA 17.265 (Native American Employment and Training); $2,193,829 under CFDA 93.193 (Urban Indian Health) |
| 53 | ALASKA NATIVE HERITAGE CENTER, INCORPORATED | WI | FAC_TRIBAL_AUDITEE + SAM_BUSINESS_TYPE | 9,699,932 | federal awards expended (single audit) | SAM certified federally-recognised tribal government on 15 rows; declared entity_type=tribal on 3 Federal Audit Clearinghouse submission(s) |
| 54 | COUNCIL OF 3 RIVERS AMERICAN INDIAN CENTER | PA | SAM_BUSINESS_TYPE + TRIBAL_ONLY_PROGRAM | 9,318,044 | federal assistance obligations | SAM certified federally-recognised tribal government on 3 rows; $9,318,044 under CFDA 17.265 (Native American Employment and Training) |
| 55 | COPPER RIVER HOUSING AUTHORITY | AK | SAM_BUSINESS_TYPE + TRIBAL_ONLY_PROGRAM | 9,205,394 | federal assistance obligations | SAM certified federally-recognised tribal government on 7 rows; $9,111,651 under CFDA 14.867 (IHBG) |
| 56 | CENTRAL COUNCIL - TLINGIT & | AK | SAM_BUSINESS_TYPE + TRIBAL_ONLY_PROGRAM | 8,595,839 | federal assistance obligations | SAM certified federally-recognised tribal government on 1 rows; $8,595,839 under CFDA 15.022 (Tribal Self-Governance) |
| 57 | COPPER RIVER BASIN REGIONAL HOUSING AUTHORITY | AK | FAC_TRIBAL_AUDITEE + TRIBAL_ONLY_PROGRAM | 8,449,119 | federal awards expended (single audit) | $1,529,839 under CFDA 14.867 (IHBG); declared entity_type=tribal on 2 Federal Audit Clearinghouse submission(s) |
| 58 | ASSOCIATION OF VILLAGE COUNCIL | AK | SAM_BUSINESS_TYPE + TRIBAL_ONLY_PROGRAM | 8,430,231 | federal assistance obligations | SAM certified federally-recognised tribal government on 1 rows; $8,430,231 under CFDA 15.022 (Tribal Self-Governance) |
| 59 | VALDEZ NATIVE TRIBE | AK | SAM_BUSINESS_TYPE + TRIBAL_ONLY_PROGRAM | 8,277,268 | federal assistance obligations | SAM business type certified Native on 36 of 154 assistance rows; $5,166,385 under CFDA 93.441 (Indian Self-Determination); $1,420,438 under CFDA 15.021 (Consolidated Tribal Government) |
| 60 | MISS BAND OF CHOCTAW INDIANS | MS | SAM_BUSINESS_TYPE + TRIBAL_ONLY_PROGRAM | 7,814,378 | federal assistance obligations | SAM certified federally-recognised tribal government on 1 rows; $3,158,326 under CFDA 15.024 (ISD Contract Support); $2,915,000 under CFDA 15.042 (Indian School Equalization) |

### What the top of that list is made of

Three functional types, each a real legal person that receives money in its own name:

1. **Tribal health organisations** — the ISDEAA Title I contractor or Title V compactor that operates a tribe's or region's health system. **The IHS self-governance subset of these was promoted in this pass; the Title I contractors and the non-self-governance health boards were not, because no single roster names them.**
2. **Tribally Designated Housing Entities** — NAHASDA 25 U.S.C. 4103(22). Often regional and multi-tribal, especially in Alaska where one housing authority serves many villages.
3. **Tribal school-board corporations** — the P.L. 100-297 grant school operator, a 501(c)(3) legally distinct from the school building Cedar already holds in the `BIE School` class.

---

## Part 3 — does any real organisation type fit no class?

Each type was tested **against the spine first**. "Missing" is a measurement, not an assumption.

| organisation type | in spine | filed under | candidates with no entity | candidate $ | verdict |
|---|---:|---|---:|---:|---|
| Tribally Designated Housing Entity / tribal housing authority | 2 | `Intertribal Organization`, `Native Hawaiian Organization` | 470 | 606,785,399 | **held partially; more outside than in** |
| Tribal health organisation (Title I contractor / Title V compactor) | 34 | `Federal-level self-governance consortium`, `Intertribal Organization`, `Native Hawaiian Organization`, `Urban Indian Organization` | 22 | 1,274,363,696 | represented |
| Tribal school board corporation (grant/contract school operator) | 0 | — | 15 | 233,773,923 | **NO CLASS AND NO MEMBERS** |
| Alaska regional non-profit (the non-ANCSA service arm) | 9 | `ANCSA Group Corporation`, `Alaska Native Village Corporation`, `Federal-level self-governance consortium` | 5 | 102,757,507 | represented |
| Tribal utility / infrastructure authority | 0 | — | 7 | 12,578,624 | **NO CLASS AND NO MEMBERS** |
| Tribal court / judicial body | 0 | — | 0 | 0 | absent from both — **not a gap** |
| Cultural institution, museum, language organisation | 0 | — | 15 | 14,238,864 | **NO CLASS AND NO MEMBERS** |
| Urban Indian centre without an IHS Title V contract | 4 | `Urban Indian Organization` | 13 | 47,043,389 | **held partially; more outside than in** |
| Native Hawaiian civic club / homestead association | 14 | `Native Hawaiian Organization` | 0 | 0 | represented |
| Tribal or Native philanthropic foundation | 0 | — | 4 | 331,243 | **NO CLASS AND NO MEMBERS** |

**Tribally Designated Housing Entity / tribal housing authority** — NAHASDA 25 U.S.C. 4103(22): the entity a tribe designates to receive IHBG. A legal person distinct from the tribe, and often multi-tribal.

- in spine: Nanakuli Housing Corporation (`Native Hawaiian Organization`); Bristol Bay Housing Authority (`Intertribal Organization`)
- best-evidenced with no entity: TAGIUGMIULLU NUNAMIULLU HOUSING AUTHORITY (3 families, $23,515,486); BARANOF ISLAND HOUSING AUTHORITY (3 families, $20,165,811); KODIAK ISLAND HOUSING AUTHORITY (3 families, $18,582,663); ALEUTIAN HOUSING AUTHORITY (3 families, $13,349,893)

**Tribal health organisation (Title I contractor / Title V compactor)** — The organisation that operates a tribe's or a region's health system under ISDEAA. Not the tribe, and not a UIO.

- in spine: National Indian Health Board (`Intertribal Organization`); Northwest Portland Area Indian Health Board (`Intertribal Organization`); California Rural Indian Health Board, Inc. (`Intertribal Organization`); Southern Plains Tribal Health Board (`Intertribal Organization`)
- best-evidenced with no entity: TOIYABE INDIAN HEALTH PROJECT, INC. (3 families, $113,166,055); STRONG FAMILY HEALTH CENTER (3 families, $15,543,444); FORT DEFIANCE INDIAN HOSPITAL BOARD, INC. (2 families, $820,809,418); K'IMA:W MEDICAL CENTER (2 families, $72,796,833)

**Tribal school board corporation (grant/contract school operator)** — P.L. 100-297 grant school operator - a 501(c)(3) separate from the BIE school Cedar already holds.

- in spine: none
- best-evidenced with no entity: TUBA CITY HIGH SCHOOL BOARD, INC (3 families, $46,443,589); ROUGH ROCK SCHOOL BOARD, INC. (2 families, $85,634,360); INDIAN BOARD OF EDUCATION FOR PIERRE (2 families, $19,798,280); CHUSKA SCHOOL BOARD OF (2 families, $4,219,611)

**Alaska regional non-profit (the non-ANCSA service arm)** — The ANCSA regional corporation's non-profit sibling: Kawerak, Tanana Chiefs, Maniilaq, KANA. Same region, different legal person.

- in spine: Bristol Bay Native Association (`Federal-level self-governance consortium`); Copper River Native Association (`Federal-level self-governance consortium`); Chickaloon Moose Creek Native Association, Inc. (`Alaska Native Village Corporation`); Gold Creek-Susitna Native Association, Inc. (`Alaska Native Village Corporation`)
- best-evidenced with no entity: ORUTSARARMIUT NATIVE COUNCIL (3 families, $53,967,916); FAIRBANKS NATIVE ASSOCIATION, (3 families, $48,439,058); TANANA NATIVE COUNCIL (2 families, $299,795); KUSHKOKWIM NATIVE ASSOCIATION (1 families, $46,938)

**Tribal utility / infrastructure authority** — e.g. Navajo Tribal Utility Authority - an enterprise of government, chartered separately.

- in spine: none
- best-evidenced with no entity: FRIANT WATER AUTHORITY (2 families, $15,000); TRUCKEE MEADOWS WATER AUTHORITY (1 families, $10,000,000); NUVISTA LIGHT & ELECTRIC COOPERATIVE INC (1 families, $1,551,968); ALASKA VILLAGE ELECTRIC COOPERATIVE INC. (1 families, $759,656)

**Tribal court / judicial body** — An organ of a government Cedar already holds, not a separate legal person. Expected ABSENT, and the probe records that it is.

- in spine: none

**Cultural institution, museum, language organisation** — Native-run museums, THPO-adjacent institutions and language revival non-profits.

- in spine: none
- best-evidenced with no entity: ALASKA NATIVE HERITAGE CENTER, INCORPORATED (2 families, $9,699,932); INDIAN PUEBLO CULTURAL CENTER (2 families, $2,238,392); NORTH AMERICAN INDIAN CULTURAL CENTER (2 families, $1,041,113); NATIVE AMERICAN CULTURAL CENTER (2 families, $396,643)

**Urban Indian centre without an IHS Title V contract** — The 43 UIOs held ARE the Title V roster. Urban Indian centres without a Title V health contract are a different, larger population.

- in spine: Friendship House Association of American Indians (`Urban Indian Organization`); Kansas City Indian Center (`Urban Indian Organization`); Urban Indian Center of Salt Lake (`Urban Indian Organization`); Tucson Indian Center (`Urban Indian Organization`)
- best-evidenced with no entity: DENVER INDIAN CENTER, INC. (3 families, $2,553,450); PHOENIX INDIAN CENTER (2 families, $18,977,925); COUNCIL OF 3 RIVERS AMERICAN INDIAN CENTER (2 families, $9,318,044); AMERICAN INDIAN CENTER OF ARKANSAS , INC. (2 families, $4,061,297)

**Native Hawaiian civic club / homestead association** — Present in the NHO class; probed to confirm.

- in spine: Ahonui Homestead Association (`Native Hawaiian Organization`); Hau‘ouiwi Homestead Association on Lāna‘i (`Native Hawaiian Organization`); Hawaiian Civic Club of Wahiawa (`Native Hawaiian Organization`); Kaha I Ka Panoa Kaleponi Hawaiian Civic Club (`Native Hawaiian Organization`)

**Tribal or Native philanthropic foundation** — The grantmaking arm, distinct from the tribe and from a CDFI.

- in spine: none
- best-evidenced with no entity: ARCTIC SLOPE COMMUNITY FOUNDATION, INC. (2 families, $0); PUERTO RICO COMMUNITY FOUNDATION INC (1 families, $299,860); COWLITZ COMMUNITY FOUNDATION (1 families, $21,383); MOUNTAIN VALLEY CHARITABLE FOUNDATION, INC. (1 families, $10,000)

---

## Should `Native nonprofit` become a class?

**No — and the owner's own sentence is the reason.** *"Urban Indian organizations are nonprofits."* So are the 37 TCUs, the 64 Native CDFIs, most of the intertribal organisations and most of the 210 NHOs. A `Native nonprofit` class would either duplicate those entities or become a residual bucket meaning "Native, nonprofit, and none of the above" — a class defined by what it is not.

Three reasons, each measurable rather than aesthetic:

1. **501(c)(3) status is an attribute, not a kind of organisation** — and Cedar already carries it. `np_orgs` holds the IRS BMF subsection and filing requirement per EIN and `np_ein_entity_hub` binds EINs to spine entities, so "which of our entities are nonprofits?" is a join, and the join exists.
2. **The existing classes are FUNCTIONAL and the taxonomy is load-bearing.** `docs/CEDAR_TAXONOMY.md` documents guards that branch on class — the ANCSA rule-2/rule-4 ownership refusals, the government-class restriction that kills the Elim defect, the BIE federally-operated blank-parent ruling. A legal-form class can carry none of them, because tax status implies nothing about who controls the organisation.
3. **A residual class hides exactly the gap this pass found.** Filing an Alaska regional housing authority, a Title V health corporation and a grant-school board under one `Native nonprofit` label would make them countable and still unanalysable. Each needs its own functional class with its own ownership rule — which is what was done for the health organisations here.

### What to add instead — two more functional classes

| proposed class | why it cannot go in an existing class | the ownership rule it needs | roster to promote from |
|---|---|---|---|
| **Tribally Designated Housing Entity** | designated by a tribe under 25 U.S.C. 4103(22) and is not the tribe; a regional TDHE is designated by *several* tribes and cannot roll up to one | `designated_by`, many-to-many — **never** `owned_by`. A regional TDHE's IHBG must not book to one member tribe. | HUD ONAP IHBG formula allocation list — not yet pulled; the 78 unkeyed IHBG recipients in `federal_funding` are the interim queue |
| **Tribal school-board corporation** | it is the legal person that operates a `BIE School`, and the two are already separate rows in the world | `operates`, pointing at the BIE School entity Cedar holds | BIE grant/contract school list (129 tribally controlled schools already held) joined to the FAC auditee EINs |

The tribal health organisation class was the third, and it is now populated inside `Federal-level self-governance consortium` rather than as a new class — because the IHS roster's own criterion IS self-governance participation, and seven precedents already sat there. **The Title I contractors and the area health boards still need a ruling**: see the class-placement inconsistency below.

## The single largest finding: $1.78B on one missing alias

**`DENA NENA HENASH`, UEI `D37SXRJ5HMJ1`, carries $1,783,253,649 of federal assistance across 2,496 transactions and is unattributed.** `cedar_identifier_ledger_final.csv` holds that UEI with `legal_business_name = "Dena' Nena' Henash"`, `attribution_method = unmatched`, tier C, *"No attribution — discovery candidate"*.

It is **Tanana Chiefs Conference**, already in the spine as `SGVF-TNNACH-00`. Its own website, retrieved 2026-09-01, says so verbatim:

> "Tanana Chiefs Conference (TCC) is an Alaska Native non-profit corporation, also organized as Dena' Nena' Henash or 'Our Land Speaks'." — <https://www.tananachiefs.org/>

The two spellings Cedar *does* match — `TANANA CHIEFS CONFERENCE` and `TANANA CHIEFS CONFERENCE, INC.` — carry $11.0M between them across 23 transactions. **So 99.4% of this organisation's federal assistance is filed under a name the spine cannot see.** It is not a missing entity; it is a missing alias, and it is the largest single identity gap this pass found by two orders of magnitude.

**It was not fixed here, and that is a judgement call worth stating.** An alias is an identity claim — the same shape as a merge — and this pass's rules route merges to a ruling and reserve `entity_aliases.csv` to the alias layer's owner. The fix is one row:

```
entity_id = SGVF-TNNACH-00
alias_name = Dena' Nena' Henash        (also: Dena Nena Henash)
alias_type = common / former_legal     verification_status = RECORDED
tier = A   source = https://www.tananachiefs.org/ (self-stated, verbatim)
```

Note the orthography rule while landing it: the apostrophes are Athabascan glottal marks and every form — `ʼ`, `'`, none — must fold to one key, exactly as `NATIVE_ENTITY_NUANCES.md` requires for Suhʼdutsing.

## Defects found, reported and NOT fixed here

Each is somebody else's file this pass. Named with evidence so the owner is not rediscovered by a future session.

1. **`503_identity.resolve()` matches on a single distinctive token for gov-class entities.** *Arctic Slope Native Association* → `AKNF-ARCTIC-00` (Arctic Village), "unique". *Arctic Village*'s distinctive token set is `{ARCTIC}` alone. Any filed name containing the word Arctic can be claimed by it. Owner: workstream I / whoever owns `503`.
2. **`federal_recognition_roster.csv` keys four Alaska GOVERNMENT listings to ANCSA CORPORATIONS** — Algaaciq→`ANVC-STMRYS-00`, Chuathbaluk→`ANVC-RSSNMS-00`, Elim→`ANVC-ELIMXX-00`, Shishmaref→`ANVC-SHSHMR-00`. This is the Elim defect in the roster of record. The FR list cannot name a corporation.
3. **The same table keys "Oneida Nation" (WI) to `TRBF-ONDANY-00`** (Oneida Indian Nation, NY) — two different sovereigns, and `503`'s own `RESOLUTIONS` dict already rules the opposite way for that exact string.
4. **Class-placement inconsistency inside the IHS self-governance roster.** Alaska Native Tribal Health Consortium (`ITO-LSKHLT-00`) and Great Plains Tribal Leaders Health Board (`ITO-GRTPL1-00`) are `Intertribal Organization`; seven of their fellow compactors are `Federal-level self-governance consortium`. One roster, two classes. **A re-class is a ruling and was not made here.**
5. **`SGVF-CHGCMT-00`'s canonical name is `Chugachmiut self-governance consortium`** — a description, not the organisation's legal name, which is simply *Chugachmiut*. `503.resolve('Chugachmiut')` therefore returns None. An alias would fix it; the alias layer is not this workstream's file.
6. **`Bristol Bay Housing Authority` (`ITO-BRSTL1-00`) is classed `Intertribal Organization`.** It is a TDHE. It is the only housing entity in the spine, and it is in the wrong class — which is itself the argument for the TDHE class proposed above.
7. **Three tier-B `containment` links in `np_ein_entity_hub.csv` bind an organisation's own legal name to a different organisation.** Found while building this pass's index, and they matter because a bad link there makes a missing organisation look present:

| EIN | organisation as filed | keyed to | what that entity actually is |
|---|---|---|---|
| 95-2506788 | INDIAN HEALTH COUNCIL INC (Valley Center, CA) | `ITO-RBNHLT-00` | National Council of Urban Indian Health — a national membership body, not a California clinic consortium |
| 81-0549382 | WINSLOW INDIAN HEALTH CARE CENTER INC | `UIO-HEALTH-00` | *Native Health*, a Phoenix UIO |
| 73-0955756 | CENTRAL OKLAHOMA AMERICAN INDIAN HEALTH COUNCIL INC | `ANVC-COUNCI-00` | **Council Native Corporation, an ANCSA village corporation in Alaska** — matched on the word "Council" |

Both of the first two organisations are Title V compactors that this pass has now given their own spine entities, so the hub links are not merely wrong, they are wrong in a way that would have blocked the correction. This audit therefore **stopped indexing `np_ein_entity_hub.org_name` as a spine name** and uses only its EIN→entity link. The table itself was not edited.

## What this pass did NOT do

- No entity was added on a name, a nonprofit filing, or this script's judgement. Every appended row is a federal roster entry with a second federal source attached.
- No existing spine row was edited, re-classed, merged or deleted. Duplicates and wrong classes are reported above for a ruling.
- `503 mint`, `510 --apply` and `build.py ship` were not run. `cedar_uid` on the new rows is blank by design.
- Where no roster exists the universe is recorded **OPEN**, and no class was given an estimated denominator.

## Reproduce

```
py -3 code/524_universe_gap.py selftest
py -3 code/524_universe_gap.py refetch     # roster drift vs the embedded copy
py -3 code/524_universe_gap.py promote     # dry run
py -3 code/524_universe_gap.py measure
py -3 code/62_no_regression_check.py
```

