# Section 106 project consultation - built, and the merge proposed

*Generated 2026-09-01 by `code/130_build_section_106_consultation.py`. Every number below is recomputed from the files it describes; none is hand-entered.*

## What was built

| | |
|---|---:|
| `data/clean/section_106_consultation_events.csv` | 1,367 rows |
| distinct tribes | 85 |
| distinct lead agencies | 32 |
| `data/clean/section_106_project_parties.csv` | 51 rows |
| distinct applicants / developers named | 41 |
| rows classed PROJECT_UNDERTAKING | 154 |
| years covered | 1994-2026 |

### By record type

| record_type | rows |
|---|---:|
| STATUTORY_REFERENCE_ONLY | 597 |
| AGREEMENT_DOCUMENT_REFERENCE | 355 |
| CONSULTATION_PROCESS_RECORD | 154 |
| PROJECT_UNDERTAKING | 154 |
| PROGRAM_ALTERNATIVE | 107 |

**Only `PROJECT_UNDERTAKING` is project-level consultation.** `STATUTORY_REFERENCE_ONLY` is a grant notice reciting that recipients must comply with Section 106. Both are real Section 106 mentions and publishing them at one confidence would rebuild, in a new place, the monoculture this dataset exists to break.

### By tier

- **A** - 103
- **B** - 134
- **C** - 1,130

### Top lead agencies

| agency | rows |
|---|---:|
| Interior Department | 301 |
| Energy Department | 196 |
| Transportation Department | 150 |
| Advisory Council on Historic Preservation | 147 |
| Housing and Urban Development Department | 105 |
| Environmental Protection Agency | 81 |
| Defense Department | 70 |
| Agriculture Department | 69 |
| Commerce Department | 43 |
| Health and Human Services Department | 32 |
| Nuclear Regulatory Commission | 31 |
| Tennessee Valley Authority | 25 |
| Federal Communications Commission | 24 |
| Homeland Security Department | 18 |
| State Department | 10 |

## Why this is not a duplicate of `consultation_events.csv`

The existing file's composition, recomputed:

| consultation_type | rows |
|---|---:|
| NAGPRA_consultation_reported | 10,888 |
| consultation_session | 212 |
| consultation_notice | 180 |
| NAGPRA | 38 |
| listening_session | 37 |
| NHPA_section_106 | 20 |
| negotiated_rulemaking | 14 |
| dear_tribal_leader_letter | 6 |
| advisory_committee | 5 |
| tribal_summit | 2 |

- 11,068 of 11,402 rows come from `Interior Department` alone.
- The existing file holds **20** Section 106 rows against **1,367** here.
- Source-URL overlap between the existing Section 106 rows and the new file: **14**.
- Tribes in the new file that appear nowhere in `consultation_events.csv`: **17**.

## The proposed merge - and why it is a proposal, not an action

`consultation_events.csv` was **not modified by this build** and must not be rebuilt to absorb this file. Script 96 owns it, rebuilds it from its own inputs, and would drop anything appended from outside - the same shape as the `09_import_rulings.py` regression in AGENTS.md.

Recommended, in order:

1. **Publish the two files side by side and join on nothing.** They answer different questions: `consultation_events.csv` is policy consultation, this is project consultation. A `channel` column already separates them (`CONSULTATION` vs `SECTION_106_CONSULTATION`) and both sit under `EventClass.GOVERNMENT_ENGAGEMENT`.
2. **If a single consultation view is wanted, build it as a THIRD file** - a harmonised view in the style of `code/110_build_harmonized_views.py` - reading both and writing neither. Never append into either source.
3. **Do not migrate the existing 20 `NHPA_section_106` rows out of `consultation_events.csv`.** They were built by a different parser against a different candidate set; moving them would lose script 96's provenance for no gain, and the overlap measured above is 14 rows.
4. **Carry the coverage file with any publication.** `section_106_source_coverage.csv` is what stops a reader concluding that a tribe with no row here was not consulted.

## What the private-sector side looks like

The applicant is the party nothing else in Cedar Press sees. Named parties, with the role the document itself assigns:

| party | role | project |
|---|---|---|
| AIDS Help, Inc | PROJECT_SPONSOR | - |
| Alabama Power Company | LICENSEE | Project No. 2146, 82 |
| Alaska Energy Authority | LICENSEE | Project No. 14241 |
| Badger State Solar | FILER | - |
| Basin Electric | FILER | - |
| Birch Power Company | APPLICANT | - |
| Black Rock City LLC | APPLICANT | - |
| Brightline West | APPLICANT | - |
| Brookfield White Pine Hydro LLC | LICENSEE | - |
| Central Electric | APPLICANT | - |
| Central Vermont Public Service Corporation | APPLICANT | - |
| City of Broken Bow, Oklahoma | LICENSEE | Project No. 12470 |
| City of Pasadena Water and Power | LICENSEE | - |
| Clark Canyon Hydro, LLC | APPLICANT | Project No. 12429 |
| Coeur Rochester Inc | APPLICANT | - |
| Cordova Electric Cooperative, Inc | APPLICANT | - |
| Crisp County Power Commission | LICENSEE | Project No. 659 |
| Crosland, Inc | DEVELOPER | - |
| Crown Hydro, LLC | LICENSEE | - |
| Crown Mill, LLC | LICENSEE | - |
| East Texas Electric Cooperative, Inc | LICENSEE | Project No. 12632-001 |
| FirstLight Hydro Generating Company | LICENSEE | Project No. 2662 |
| Georgia Power Company | LICENSEE | Project No. 485-063 |
| Grand River Dam Authority | LICENSEE | Project No. 2524-018 |
| Honuaula Partners, LLC | DEVELOPER | - |
| Hycroft Resources and Development, Inc | APPLICANT | - |
| Ketchikan Public Utilities | APPLICANT | - |
| Lockhart Power Company, Inc | APPLICANT | - |
| Loup River Public Power District | APPLICANT | - |
| Marigold Mining | APPLICANT | - |
| Marquette Board of Power and Light | LICENSEE | Project No. 2589-024 |
| Marseilles Land and Water Company | APPLICANT | - |
| NRP Group, LLC | DEVELOPER | - |
| Northern Indiana Public Service Company | LICENSEE | Project No. 12514 |
| PacifiCorp Energy | LICENSEE | Project No. 308 |
| Soule Hydro, LLC | APPLICANT | Project No. 13528-000 |
| South Carolina Public Service Authority | LICENSEE | Project No. 199 |
| Twin Lakes Canal Company | LICENSEE | - |
| Union Electric | APPLICANT | - |
| Upper Peninsula Power Company | LICENSEE | Project No. 10855-002 |
| Yuba County Water Agency | LICENSEE | Project No. 2246 |

**None of this is lobbying.** A licensee invited to develop a Programmatic Agreement with four tribes is discharging an obligation under 36 CFR 800, and `is_lobbying` is 0 on every row of both files.

## What was refused

- **FERC eLibrary.** Two different queries return the same 22,464-byte JavaScript shell; the record is not in the HTML. Harvesting it needs its private JSON endpoint and a per-docket crawl - a separate build with its own host budget.
- **BLM ePlanning.** The root answers HTTP 200 with 536,023 bytes; every register and API path tried returned 404. A live lead, not a closed source.
- **ACHP case records.** The site answers and publishes Section 106 *guidance*; no machine-readable index of case records or agreement documents was found from the front page or five direct paths. ACHP is still present here as a publisher through its own Federal Register documents.
- **Agency project files** - the correspondence, telephone logs, emails, meeting notes and site visits the ACHP directs agencies to keep. Not centrally published; reachable only per project, by FOIA or through an agency docket. This is the largest part of the Section 106 record and it is recorded as NOT_CHECKED rather than left implied.
