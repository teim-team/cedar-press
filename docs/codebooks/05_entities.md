# Codebook — Entities

*10,772 rows across 6 file(s). Generated 2026-08-07.*

Variables marked **internal** are retained for auditing and are not included in published extracts.

| Variable | Type | Units / format | Filled | Description |
|---|---|---|---:|---|
| `tribe_id` | text | code | 100% | Cedar Press permanent identifier for the Native entity. Stable across releases; use this to join datasets. |
| `canonical_name` | text | text | 100% | Cedar Press standard name for the Native entity. |
| `entity_class` | text | category | 100% | Kind of Native entity: federally recognised tribe, state-recognised tribe, Alaska Native Village, Alaska Native Regional Corporation, or consortium. |
| `state` | text | 2-letter code | 96% | US state or territory. |
| `bia_region` | text | category | 45% | Bureau of Indian Affairs region. |
| `self_governance` | integer | 0/1 | 45% | 1 when the tribe operates under a self-governance compact. |
| `cedar_entity_id` | text | code | 63% | Short public entity code. T- tribes, A- Alaska Native corporations, N- Native Hawaiian Organisations, E- enterprises, I- intertribal, NP- nonprofits. |
| `n_uei_tierA` | integer | integer | 100% | Count. |
| `n_uei_tierB` | integer | integer | 100% | Count. |
| `n_cage` | integer | code | 100% | Commercial and Government Entity code (5 characters). |
| `n_ein` | integer | integer | 100% | Count. |
| `aliases` | text | text | 88% | Other names the entity is known by, separated by `|`. |
| `parent_entity_id` | text | code | 3% | The IMMEDIATE parent, one step up. Kept separate from the ultimate parent because the middle of a chain is a real fact: RiverTech is Akima's and Akima is NANA's, which is three facts and not one. Mille Lacs' immediate parent is the Minnesota Chippewa Tribe. |
| `parent_entity_name` | text | text | 3% | Name of the immediate parent. |
| `ultimate_parent_entity_id` | text | code | 84% | The top of this entity's ownership chain, and the ONLY safe column to group on for a roll-up. Three Chenega operating companies share one ultimate parent; summing on `tribe_id` would report them as three unrelated entities. An entity that is its own top carries its own id here rather than a blank, so a roll-up can group unconditionally. |
| `ultimate_parent_entity_name` | text | text | 84% | Name of the ultimate parent entity. |
| `ancsa_region_entity_id` | text | code | 35% | The ANCSA regional corporation whose region this entity sits in. THIS IS GEOGRAPHY AND STATUTE, NOT OWNERSHIP - regional and village corporations are separate corporations with separate shareholders. It is deliberately NOT the ultimate parent and must never be summed as though the region owned the village corporation. |
| `hierarchy_basis` *(internal)* | text | text | 48% | How the parent relationship was established. |
| `cicd_verified` | integer | 0 to 1 | 70% | One of: `1`, `0` |
| `reconciliation_status` | text |  | 33% | One of: `added_2026-08-06_script73`, `seek_identifiers`, `seek_parent`, `federally_operated_no_tribal_parent`, `parent_affiliation_tierB`, `reclassified_intertribal`, `review_possible_division` |
| `reconciliation_note` | text | text | 33% | Free-text note explaining why an entity is still open in the reconciliation queue and what would close it. |
| `fr_official_name` | text | text | 40% | Name. |
| `parent_native_entity` | text | text | 5% | The Native entity that OWNS this organisation. Empty when no single entity owns it. |
| `serves_native_entities` | text | text | 4% | Native entities this organisation serves. Distinct from ownership and never implies it. |
| `ownership_basis` *(internal)* | text |  | 10% |  |
| `entity_source_url` | text | URL | 10% | Link. |
| `entity_source_quote` | text | text | 10% | The sentence in the cited source that establishes this entity's existence or status, quoted so the claim can be checked without re-retrieving the source. |
| `bie_operation_type` | text |  | 14% | One of: `tribally_controlled`, `bie_operated` |
| `source_url` | text | URL | 17% | Link to the record's published source. |
| `source_quote` | text | text | 17% | The document's own words supporting the recorded term. |
| `entity_website` | text | URL | 17% | The entity's own website, where one has been recorded. Blank means none has been recorded, not that none exists. |
| `city` | text | text | 16% | City. |
| `built_by_script` | text |  | 17% | One of: `code/75_add_bie_schools_and_uios.py` |
| `proposed_id` | text | code | 100% | Identifier. |
| `organization_name` | text | text | 100% | Name. |
| `org_scope` | text |  | 100% | One of: `sector`, `regional`, `national` |
| `ein` *(subscriber)* | text | code | 40% | Employer Identification Number, the IRS taxpayer identifier. |
| `member_count` | text | integer | 56% | Count. |
| `roster_count` | text | integer | 63% | Count. |
| `files_lda` | text |  | 100% | One of: `yes`, `no`, `unknown` |
| `lda_filing_count` | integer | integer | 88% | Count. |
| `lda_years_observed` | text | YYYY list | 67% | Years in which the organisation appears in lobbying disclosures. |
| `website` | text | URL | 91% | Official website. |
| `founded_year` | integer | YYYY | 15% | Year. |
| `evidence_url` | text | URL | 100% | Source supporting the classification. |
| `retrieved_date` | text | YYYY-MM-DD | 100% | Date. |
| `notes` | text | text | 100% | Analyst notes on the record. |
| `nho_class` | text |  | 100% | One of: `doi_notification_list`, `contracting_nho` |
| `nho_status_basis` *(internal)* | text |  | 100% | One of: `doi_roster_only`, `sba_8a_entity_owned`, `self_stated`, `elijah_ruling` |
| `verification_route` *(internal)* | text |  | 100% |  |
| `evidence_quote` | text | text | 100% | Quoted sentence from the source supporting the classification. |
| `subsidiaries` | text | text | 14% | Known subsidiary organisations. |
| `nhoa_member_first_seen` | text |  | 11% | One of: `2022-05-28`, `2021-05-06`, `2024-04-14` |
| `nhoa_member_last_seen` | text |  | 11% | One of: `2024-04-14`, `2023-06-06` |
| `source` | text | text | 100% | Publisher of the record. |
| `confidence_tier` | text | category | 100% | Publication tier. A = verified, publishable. B = provisional, withheld from published extracts. C = unattributed. X = ruled out. |
| `built_date` | text | YYYY-MM-DD | 100% | Date. |
| `alias_id` | text | code | 100% | Cedar-internal identifier for one recorded name variant. Minted by cedar_ids; never an official identifier. |
| `entity_id` | text | code | 100% | Identifier. |
| `alias_name` | text | text | 100% | The name variant as the source spells it, including diacritics and punctuation. |
| `normalized_alias` | text | text | 100% | alias_name after the shared fold in 33_apply_party_rulings.norm: lowercased, diacritics folded to their base letter, punctuation removed. Match on this, never on alias_name. |
| `alias_type` | text | code | 100% | Which kind of name variant this is, from cedar_domain.ALIAS_TYPES. full_form_federal_filing is the long form federal systems file for a short spine name; diacritic_folded is the ASCII rendering. |
| `source_system` | text | code | 100% | The system the name or the relationship came from - the Federal Register, the Cedar spine, the identifier ledger, or Cedar itself where the variant was generated. |
| `start_date` | empty | YYYY-MM-DD | 0% | Date. |
| `end_date` | empty | YYYY-MM-DD | 0% | Date. |
| `first_observed_date` | empty | YYYY-MM-DD | 0% | Earliest date this variant was seen in a source, where a source states one. |
| `last_observed_date` | empty | YYYY-MM-DD | 0% | Latest date this variant was seen in a source, where a source states one. |
| `verification_status` | text | code | 100% | How the row was established: OFFICIAL and RULED are the strong cases; GENERATED_UNCONFIRMED and OFFICIAL_UNLINKED say plainly that nobody has confirmed it. |
| `confidence` | numeric | 0-1 | 100% | 0-1. Below 0.50 the row may never auto-link - which is what a generated variant colliding with a municipality is set to. |
| `tier` | text | A/B/C/X | 100% | Publishability, from cedar_domain.Tier. A publishes; B is visible internally only; C is unattributed; X is ruled out and never resurfaces. |
| `source_id` | text | code | 100% | Identifier. |
| `created_at` | text | YYYY-MM-DD | 100% | Date the row was written by the build. |
| `relationship_id` | text | code | 100% | Cedar-internal identifier for one typed edge. Minted by cedar_ids. |
| `source_entity_id` | text | code | 31% | The entity the relationship is stated FROM. Blank where the party is real but has no Cedar entity - a brand family, a tribally owned firm - which is recorded by name rather than resolved onto a tribe. |
| `relationship_type` | text | code | 100% | The typed edge, from cedar_domain.ALL_RELATIONSHIPS. The type alone decides whether a dollar may roll along the edge: see cedar_domain.bears_ownership. There is no generic related_to. |
| `target_entity_id` | text | code | 91% | The entity the relationship points TO. Blank where the counterparty has no Cedar entity, including the federal government and every tribally designated housing entity. |
| `is_current` | integer | 0/1 | 100% | 1 where the relationship is in force as recorded; 0 where it has ended. |
| `legal_or_informal` | text | legal/informal | 100% | Whether the relationship is a legal fact (charter, statute, ownership) or an informal one (a brand). |
| `direct_or_inferred` | text | direct/inferred | 100% | direct where a source states the relationship; inferred where it was derived, including anything resolved by name containment. |
| `evidence_text` | text | text | 98% | The source's own words, or the ruling, supporting the relationship. |

## Value sets

- **`entity_class`** — `Federally recognized tribe`, `Federally recognized Alaska Native Village`, `Alaska Native Village Corporation`, `BIE School`, `State-recognized tribe`, `Intertribal Organization`, `Native Community Development Financial Institution`, `Native Hawaiian Organization`, `Federal-level constituency entity`, `Urban Indian Organization`, `Tribal College or University`, `Native Financial Institution`, `Alaska Native Regional Corporation`, `Federal-level self-governance consortium`, `ANCSA Group Corporation`, `State-level constituency entity`
- **`bia_region`** — `Alaska`, `Pacific`, `Northwest`, `Western`, `Eastern`, `Midwest`, `Southwest`, `Southern Plains`, `Eastern Oklahoma`, `Great Plains`, `Rocky Mountain`, `Navajo`
- **`ancsa_region_entity_id`** — `ANRC-CKINLT-00`, `ANRC-CALSTA-00`, `ANRC-DOYONL-00`, `ANRC-BRBYCO-00`, `ANRC-BERSTR-00`, `ANRC-SEALSK-00`, `ANRC-ALEUTC-00`, `ANRC-ARCSLO-00`, `ANRC-NANARC-00`, `ANRC-KONIAG-00`, `ANRC-CHGCCO-00`, `ANRC-AHTNAI-00`
- **`reconciliation_status`** — `added_2026-08-06_script73`, `seek_identifiers`, `seek_parent`, `federally_operated_no_tribal_parent`, `parent_affiliation_tierB`, `reclassified_intertribal`, `review_possible_division`
- **`serves_native_entities`** — `multi-tribal urban American Indian and Alaska Native service population; no single tribal owner (IHCIA Title V)`, `CMN has a main campus located on the southern border of the Menominee Indian Reservation and also operates a campus in Green Bay, WI that serves many students from the Oneida Nation. | CMN has a main campus located on the southern border of the Menominee Indian Reservation and also operates a campus in Green Bay, WI that serves many students from the Oneida Nation.`, `Located in Okmulgee, Oklahoma, the capital of the Muscogee (Creek) Nation, the college was organized to serve Muscogee Nation Tribal members and residents.`, `Chartered by the Fort Peck Assiniboine and Sioux Tribes in 1978, FPCC’s mission is to serve the people of the reservation by providing educational opportunities and community service.`, `Haskell serves members of federally recognized American Indian and Alaska Native Nations as authorized by Congress and in partial fulfillment of treaty and trust obligations.`, `Founded in 1990 to serve the Anishinaabe (Ojibwe) people of the Leech Lake Indian Reservation, LLTC offers postsecondary education grounded in the language, history, and culture of the Anishinaabe.`, `Located on the Lummi Indian Reservation in Washington state, 20 miles from the Canadian border, NWIC is the only accredited Tribal College or University serving reservation communities of Washington, Oregon, and Idaho. | In 1983, the Lummi Indian Business Council recognized the need for a more comprehensive institution to serve the postsecondary educational needs of Indian people living in the Pacific Northwest and chartered the Lummi Community College.`, `It serves the Pine Ridge Reservation, which has a population of about 26,000 and covers 3,468 square miles in southwestern South Dakota.`, `The College provides opportunities for individual self-improvement, promotes and helps maintain the cultures of the Confederated Tribes of the Flathead Indian Nation while primarily serving the needs of Native American people.`, `The College serves communities on and surrounding the 105,000 acre Lake Traverse Reservation in northeastern South Dakota, home to the Sisseton and Wahpeton bands of the Dakota people.`, `SBC serves the Standing Rock Indian Reservation consisting of a land base of 2.8 million acres in North Dakota and South Dakota with campuses in Fort Yates, ND and McLaughlin, SD.`, `The College was established to serve the residents of the Tohono O’odham Nation and nearby communities, with the critical goals of preparing students to contribute to the social, political, and economic needs of the Tohono O’odham Nation and the world and preserving the O’odham Himdag (cultural way`, `The main campus is located just north of the unincorporated city of Belcourt, which serves the reservation community as the center of government, commerce, and education for the more than 31,000 enrolled members of the tribe.`, `UTTC is owned and operated by and serves the five tribal nations located entirely or in-part of North Dakota: Sisseton-Wahpeton Oyate, Spirit Lake Nation, Standing Rock Sioux Tribe, Three Affiliated Tribes (Mandan, Hidatsa, and Arikara Nation) of the Fort Berthold Reservation, and Turtle Mountain Ba`, `WETCCe has a fully equipped computer science center serving the college, White Earth Reservation, and surrounding communities.`
- **`entity_source_url`** — `https://www.cdfifund.gov/media/8018641/download?inline`, `https://www.aihec.org/tcu-roster-and-profiles/`, `https://github.com/frb-mpls-cde/nafi-map/raw/refs/heads/main/data/nafi-map-data_current.xlsx`, `http://www.bfcc.edu/about`, `http://www.lltc.edu/about`, `http://www.ctlf-empowers.org`, `http://www.sniedc.org`, `https://www.islandmtn.com/about`, `https://www.legacybankca.com/about`
- **`bie_operation_type`** — `tribally_controlled`, `bie_operated`
- **`source_url`** — `https://www.bie.edu/schools -> https://services1.arcgis.com/UxqqIfhng71wUT9x/arcgis/rest/services/BIE_Schools_Directory/FeatureServer/0`, `https://www.ihs.gov/urban/urban-indian-organizations/california/`, `https://www.ihs.gov/urban/urban-indian-organizations/bemidji/`, `https://www.ihs.gov/urban/urban-indian-organizations/billings/`, `https://www.ihs.gov/urban/urban-indian-organizations/oklahoma-city/`, `https://www.ihs.gov/urban/urban-indian-organizations/phoenix/`, `https://www.ihs.gov/urban/urban-indian-organizations/portland/`, `https://www.ihs.gov/urban/urban-indian-organizations/regional-national-tribal/`, `https://www.ihs.gov/urban/urban-indian-organizations/albuquerque/`, `https://www.ihs.gov/urban/urban-indian-organizations/great-plains/`, `https://www.ihs.gov/urban/urban-indian-organizations/nashville/`, `https://www.ihs.gov/urban/urban-indian-organizations/navajo/`, `https://www.ihs.gov/urban/urban-indian-organizations/tucson/`
- **`source_quote`** — `There are 187 Bureau-funded elementary and secondary schools on 64 reservations in 23 states, serving approximately 40,000 Indian students. Of these, 58 are BIE-operated and 129 are tribally controlled under BIE contracts or grants.`, `The Urban Indian Organizations (UIO) listed below have current Title V Indian Health Care Improvement Act contracts with the Indian Health Service. UIOs have been arranged in alphabetical order based on the IHS area and respective State they belong in.`
- **`org_scope`** — `sector`, `regional`, `national`
- **`member_count`** — `12`, `33`, `20`, `11`, `43`, `over 180`, `574+ (representation claim)`, `192 tribes + 152 village corporations + 11 regional corporations + 11 regional nonprofits`, `41 (IHS-contracting UIOs)`, `57`, `16`, `35`, `4`, `28`, `47`, `25`, `56`, `42 members / 39 villages / 37 federally recognized tribes`, `31 sanctioning tribes / 20 member Tribal Health Programs`, `18`, `27 (representation claim)`, `34`, `31`, `8`, `54 US tribes + 4 Canadian First Nations (as of 2012)`
- **`files_lda`** — `yes`, `no`, `unknown`
- **`nho_class`** — `doi_notification_list`, `contracting_nho`
- **`evidence_quote`** — `Listed on the DOI Office of Native Hawaiian Relations Native Hawaiian Organization Notification List (updated 2025-04-02). This is an NHPA Section 106 CONSULTATION list, not a contracting registry and not evidence of SBA NHO certification.`, `NHOA membership is open to any non-profit NHO certified by the SBA pursuant to 13 C.F.R. 124.3.`, `Native Hawaiian Organizations (NHO) are non-profit organizations like the Ho‘omaka Foundation (formerly the Native Hawaiian Legal Defense and Education Fund) that serve the Native Hawaiian community.`, `Hui Huliau is a nonprofit 501(c)(3) Native Hawaiian Organization (NHO) and community service organization whose business activities principally benefit Native Hawaiians.`, `Manaʻo Nui Inc. is a non-profit Native Hawaiian Organization (NHO) founded in Honolulu, Hawaiʻi in 2005.`, `Ke Kumu ‘Ulu is recognized by the Small Business Administration (SBA) as a non-profit Native Hawaiian Organization (NHO).`, `The Makua Group, a Native Hawaiian Organization (NHO) was founded for the purpose of developing an organization consisting primarily of small businesses that will generate a revenue stream that will provide financial aid to disadvantaged Native Hawaiian people.`, `The Menehune Foundation is a Non-Profit Native Hawaiian Organization (NHO) that seeks to educate and advance Native Hawaiians and their communities`, `Galapagos is part of the Small Disadvantaged Business (SBD) registered with the Small Business Administration (SBA) under Nā ʻŌiwi Kāne, a Native Hawaiian Organization (NHO).`, `A subsidiary of Ka Lama Kuhikuhi Foundation, a nonprofit Native Hawaiian Organization (NHO).`, `Manawa Kūpono is a Native Hawaiian Organization (NHO) established in Honolulu, Hawaii`, `Island Empire Community Development, a Native Hawaiian Organization (NHO) who works closely with Federal Government Clientele`, `The Nakupuna Companies are majority owned by the Nakupuna Foundation, a Native Hawaiian Organization working to promote and advance the Native Hawaiian community through partnerships, programs, and targeted investments.`, `The Hawaii Pacific Foundation (HPF) is a Native Hawaiian Organization (NHO) incorporated in the State of Hawaii.`, `Certified in 2004 as a Native Hawaiian Organization (NHO), the Alaka'ina Foundation entered federal contracting in 2005 and established nine (9) for profit firms that were wholly acquired in June 2026 by BSNC.`, `Native Hawaiian Organization (NHO) Subsidiaries`, `Ho'opale Foundation is a Native Hawaiian organization dedicated to uplifting and empowering the Hawaiian community.`, `incorporating it under a nonprofit umbrella organization to achieve NHO status... the Kalaimoku Foundation can create perpetual 8(a) companies to benefit all native Hawaiians`
- **`nhoa_member_first_seen`** — `2022-05-28`, `2021-05-06`, `2024-04-14`
- **`nhoa_member_last_seen`** — `2024-04-14`, `2023-06-06`
- **`source`** — `DOI Office of Native Hawaiian Relations, NHO Notification List (updated 2025-04-02)`, `Native Hawaiian Organizations Association member directory, Wayback series (10 captures 2021-05-06..2024-04-14); membership gated on SBA NHO certification per 13 C.F.R. 124.3`, `organization website / Elijah ruling`
- **`confidence_tier`** — `C`, `B`, `A`
- **`alias_type`** — `common`, `full_form_federal_filing`, `legal`, `shortened`, `acronym`, `brand`, `diacritic_folded`, `source_specific`
- **`source_system`** — `cedar_spine`, `cedar_generated`, `federal_register`, `UEI`, `cedar_brand_registry`, `CAGE`, `EIN`
- **`verification_status`** — `RECORDED`, `GENERATED_UNCONFIRMED`, `SPINE_CANONICAL`, `RULED`, `TIER_A`, `OFFICIAL`, `STATUTORY`, `GENERATED_MUNICIPAL_LOOKALIKE`, `REGISTERED`, `OFFICIAL_UNLINKED`, `FOLDED`, `MIGRATED`
- **`tier`** — `A`, `B`
- **`source_id`** — `cedar_entity_spine.csv:aliases`, `97_build_aliases_and_relationships.py:generated`, `cedar_identifier_ledger_final.csv`, `cedar_entity_spine.csv`, `cedar_entity_spine.csv:fr_official_name`, `entity_hierarchy.csv`, `brand_family_registry.csv`, `admin_region_assignments.csv`, `97_build_aliases_and_relationships.py:ascii_fold`, `village_corp_namesake_pairs.csv`, `cedar_entity_spine.csv:bie_operation_type`
- **`relationship_type`** — `owned_by`, `associated_with_region`, `affiliated_with`, `brand_of`, `village_corporation_for`, `operated_by`, `chartered_by`, `constituent_band_of`
- **`legal_or_informal`** — `legal`, `informal`
- **`direct_or_inferred`** — `direct`, `inferred`
