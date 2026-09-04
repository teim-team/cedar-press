# Entity Name Harvest — build log

*Stage 35. Run 2026-08-05. Script `code/35_entity_harvest.py`, log `logs/35_entity_harvest.log`.*

One-time universe-completion job: every distinct Native-entity-shaped name appearing anywhere in the Cedar Press corpus, normalized, deduplicated, and matched against the spine.

## The rule this job obeyed

**No parallel ID system was minted.** The spine is NEID (CICD connector, 687 entities) plus the `Entity_Master` series — `T-` 588 federally recognized tribes, `A-` 191 ANCs and village corporations, `E-` 29 enterprises and subsidiaries, `N-` 7 Native Hawaiian Organizations. Every proposal in this build **extends** one of those series or the `I-` series that docs/plans/INFLUENCE_DATASET_PLAN.md reserves for intertribal and inter-Native organizations. Nothing here is assigned; `entity_candidates_new.csv` and `entity_candidates_ambiguous.csv` both carry a blank `YOUR_RULING` column and a later script does the minting.

**On `NP-`.** It is proposed, sparingly, for Native nonprofits that are *not* Hawaiian. `N-` is already in use for Native Hawaiian Organizations — all 7 current `N-` rows are NHOs, and the DOI NHO roster is the population behind them. Putting a Minnesota Native CDFI or a national Native philanthropy under `N-` would make the prefix mean two different things and would silently corrupt every NHO count taken off a prefix filter, including the 190-row DOI roster ceiling in docs/handoffs/STATE_OF_BUILD.md. That is a genuine collision, so `NP-` is proposed rather than forced into `N-`. If Elijah prefers, the alternative is to keep one `N-` series with a mandatory subclass column; the register is written so either ruling is a one-line change.

## Alias corpus

| Source | Alias strings contributed |
|---|---:|
| `cedar_entity_spine.aliases` | 1,300 |
| `entity_master.Canonical_Name` | 815 |
| `canonical_tribe_table.canonical_name` | 687 |
| `canonical_tribe_table.entity_namefull` | 687 |
| `cedar_entity_spine.canonical_name` | 687 |
| `canonical_tribe_table.biatld_nameshort` | 588 |
| `entity_master.Aliases` | 254 |
| `entity_master.Canonical_Name[paren_stripped]` | 54 |
| `entity_master.Canonical_Name[paren_inner]` | 44 |
| `canonical_tribe_table.fedreg_nameaka` | 35 |
| `canonical_tribe_table.fedreg_nameprev` | 16 |
| `entity_master.Aliases[paren_stripped]` | 12 |
| `cedar_entity_spine.aliases[paren_stripped]` | 11 |
| `cedar_entity_spine.aliases[paren_inner]` | 7 |
| `canonical_tribe_table.entity_namefull[paren_stripped]` | 6 |
| `entity_master.Aliases[paren_inner]` | 5 |
| `canonical_tribe_table.entity_namefull[paren_inner]` | 3 |
| `canonical_tribe_table.canonical_name[paren_stripped]` | 3 |
| `cedar_entity_spine.canonical_name[paren_stripped]` | 3 |
| `canonical_tribe_table.fedreg_nameaka[paren_stripped]` | 2 |
| `canonical_tribe_table.fedreg_nameaka[paren_inner]` | 2 |
| `canonical_tribe_table.biatld_nameshort[paren_stripped]` | 2 |
| `canonical_tribe_table.fedreg_nameprev[paren_stripped]` | 2 |
| `canonical_tribe_table.fedreg_nameprev[paren_inner]` | 2 |
| **total** | **5,227** |

Collapsed to 1,783 distinct normalized alias keys. Both sides of every comparison are normalized identically: casefold, diacritics and Hawaiian glottal marks stripped, punctuation removed, leading *The* dropped, trailing corporate forms (Inc/LLC/Corp/Corporation/Foundation/Association) peeled, and `of <State>` treated as optional via a second state-dropped key.

## Names harvested per source

| Source dataset | Distinct names | Matched to spine | Match rate |
|---|---:|---:|---:|
| `identifier_ledger` | 16,572 | 893 | 5% |
| `np_orgs` | 12,108 | 95 | 1% |
| `federal_actions` | 2,656 | 1,239 | 47% |
| `gaming_facilities` | 1,516 | 324 | 21% |
| `compacts` | 568 | 555 | 98% |
| `deals[deals_federal_awards_additions]` | 482 | 315 | 65% |
| `lobbying_unmatched` | 250 | 122 | 49% |
| `subawards` | 208 | 31 | 15% |
| `lobbying_disclosures` | 204 | 181 | 89% |
| `native_bills` | 202 | 128 | 63% |
| `anc_ceiling_roster` | 196 | 160 | 82% |
| `nho_doi_roster` | 190 | 3 | 2% |
| `deals[deals_2026_ytd]` | 154 | 72 | 47% |
| `deals[deals_historical_2020_2025]` | 122 | 36 | 30% |
| `gaming_land_decisions` | 98 | 95 | 97% |
| `deals[deals_2000_2019_additions]` | 80 | 16 | 20% |
| `deals[deals_historical_additions]` | 70 | 11 | 16% |
| `deals[deals_anc_reports_additions]` | 44 | 7 | 16% |
| `deals[deals_sec_2010_2017_additions]` | 41 | 10 | 24% |
| `nho_parents` | 21 | 5 | 24% |
| `deals[deals_2026_ytd_additions]` | 2 | 1 | 50% |

`federal_actions.csv` was **streamed** — 156,452 rows / 240 MB read one row at a time, never loaded. Two bounded extractors ran on `title` + `abstract`: the alias-corpus phrase matcher (3,087 observations) and a suffix-anchored capture that only takes capitalised phrases *ending* in a tribal form word — Tribe, Nation, Band, Rancheria, Pueblo, Native Village, Indian Community (6,341 observations). No open-ended NER was attempted.

An alias phrase matched in running prose must also carry a tribal marker — *tribe*, *band*, *Indian*, *pueblo*, *village*, *native*, *reservation* — either inside the phrase or within three tokens of it. **3,029 phrase hits were rejected by that rule.** Without it, *Las Vegas* in a Federal Register notice about the city matched the Las Vegas Tribe of Paiute Indians on 295 documents, and *Bristol Bay* matched the ANC every time the fishery was mentioned.

`native_bills.affected_entities` is empty on all 3,037 rows in the current build, so bill titles were run through the same suffix-anchored extractor. Fixing `affected_entities` upstream would materially improve this source.

## Match rate against the spine

| Confidence | Names | Share |
|---|---:|---:|
| exact | 1,008 | 3.2% |
| alias | 917 | 2.9% |
| containment | 272 | 0.9% |
| none | 29,531 | 93.1% |
| **total** | **31,728** | |

**2,197 of 31,728 distinct names (6.9%) matched a single spine entity.**

That headline rate is close to meaningless on its own, because the denominator is dominated by two sources that are *supposed* to be mostly non-Native: the IRS BMF candidate pool in `np_orgs` and every UEI legal name in the contracting ledger. The rate that actually measures spine coverage is the one restricted to fields that are **Native by construction**:

| Scope | Distinct names | Matched | Rate |
|---|---:|---:|---:|
| All sources | 31,728 | 2,197 | 6.9% |
| Native-by-construction fields only | 1,720 | 1,188 | 69.1% |

Native-by-construction fields are: `anc_ceiling_roster.corporation_name`, `nho_doi_notification_roster.organization_name`, `nho_parents.parent_name`, `deals.Native_Party`, `compacts.tribe` and `bia_tribes_column`, `gaming_land_decisions.tribe`, `gaming_facilities.tribe`, `native_entity_lobbying_disclosures.client_name`, and the federal-actions alias-phrase hits. A name in one of those that reaches no spine entity is a real coverage question, not noise — which is why it is the HIGH-priority bucket in the candidate register.

Method breakdown:

| Method | Names |
|---|---:|
| `no_alias_hit` | 25,888 |
| `blocked_place_or_civic` | 2,673 |
| `exact_normalized_string` | 1,071 |
| `alias_token_set_with_state` | 700 |
| `blocked_indian_placename` | 331 |
| `alias_token_set_state_optional` | 260 |
| `containment_alias_phrase` | 255 |
| `multiple_plausible_parents` | 214 |
| `blocked_south_asian_indian` | 123 |
| `blocked_federal_agency` | 105 |
| `blocked_single_generic_token` | 43 |
| `blocked_spanish_pueblo` | 43 |
| `prefix_of_longer_spine_alias` | 22 |

## New candidates by proposed class

| Prefix | Meaning | Candidates |
|---|---|---:|
| `E-` | enterprise or subsidiary | 1,534 |
| `T-` | tribal government (recognition status unruled) | 1,376 |
| `I-` | intertribal / inter-Native organization | 367 |
| `NP-` | Native nonprofit (non-Hawaiian) | 344 |
| `N-` | Native Hawaiian Organization | 287 |
| `A-` | ANC / village corporation | 11 |
| **total** | | **3,919** |

Proposed class detail:

| Proposed class | Candidates |
|---|---:|
| Tribal government (recognition status unruled) | 1,376 |
| Enterprise or subsidiary | 978 |
| Unclassified Native-signalled organization | 556 |
| Intertribal / inter-Native organization | 367 |
| Native nonprofit (non-Hawaiian) | 344 |
| Native Hawaiian Organization | 287 |
| Alaska Native corporation / village corporation | 8 |
| ANCSA corporation (ceiling roster) | 3 |

### Triage

`entity_candidates_new.csv` carries a `priority` column so the ruling session has an order:

| Priority | Candidates | Rule |
|---|---:|---|
| HIGH | 401 | the name came out of a field that is Native **by construction** — ANC ceiling roster, DOI NHO roster, NHO parents, deal `Native_Party`, compact `tribe`, gaming `tribe`, attributed lobbying `client_name`. If it is real and unmatched, the spine has a hole. |
| MEDIUM | 817 | a Native signal in the name, from a mixed source such as the identifier ledger or the unmatched lobbying clients. |
| LOW | 2,701 | single sightings in a discovery pool built to over-capture (`np_orgs`), or suffix-anchored captures out of Federal Register prose. Occurrence count does **not** promote a capture: a frequently repeated fragment is still a fragment. |

Highest-occurrence HIGH-priority candidates (full list in `data/clean/entity_candidates_new.csv`):

| Candidate | Prefix | Occurrences | Evidence |
|---|---|---:|---|
| THE THREE AFFILIATED TRIBES OF ND/MHA NATION | `I-` | 62 | collective-vehicle token 'affiliated tribes' alongside a Native signal |
| JOINT TRIBAL COUNCIL OF THE PASSAMAQUODDY TRIBE | `T-` | 22 | tribal-government form 'tribal' |
| Mohegan Tribal Gaming Authority | `E-` | 18 | corporate form 'gaming' with a Native signal |
| Lower Elwha Klallam Tribe | `T-` | 15 | tribal-government form 'tribe' |
| PAUCATUCK EASTERN PEQUOT TRIBAL NATION | `T-` | 14 | tribal-government form 'tribal' |
| SCHAGHTICOKE TRIBAL NATION OF CT | `T-` | 13 | tribal-government form 'tribal' |
| SISSETON-WAHPETON SIOUX INDIAN TRIBE | `T-` | 12 | tribal-government form 'tribe' |
| Chickasaw Management Services | `E-` | 11 | corporate form 'services' with a Native signal |
| NAVAJO TRIBAL UTILITY AUTHORITY | `E-` | 11 | tribal form 'tribal' plus business vocabulary (authority, utility) — reads as an arm of a government, not the  |
| TIMBISHA SHOSHONE TRIBE OF DEATH VALLEY | `T-` | 9 | tribal-government form 'tribe' |
| UNITED SOUTH & EASTERN TRIBES INC | `I-` | 7 | named in docs/plans/INFLUENCE_DATASET_PLAN.md's I- layer ('united south and eastern tribes') |
| IOWA TRIBE OF KANSAS AND NEBRASKA - NUWEH | `T-` | 6 | tribal-government form 'tribe' |
| MHA Nation | `T-` | 6 | tribal-government form 'nation' |
| SHIVWITZ BAND OF THE PAIUTE INDIAN TRIBE OF UTAH | `T-` | 6 | tribal-government form 'band' |
| Cheyenne River Sioux Tribe Telephone Authority | `E-` | 5 | tribal form 'tribe' plus business vocabulary (authority) — reads as an arm of a government, not the government |
| Rosebud Economic Development Corporation | `E-` | 5 | corporate form 'development corporation' with a Native signal |
| Salish & Kootenai Housing Authority | `E-` | 5 | appears in a field that is Native by construction |
| Seneca Gaming Corporation | `E-` | 5 | corporate form 'gaming' with a Native signal |
| MANDAN, HIDATSA & ARIKARA NATION THREE AFFILIATED TRIBES | `I-` | 5 | collective-vehicle token 'affiliated tribes' alongside a Native signal |
| Viejas Band of Kumeyaay Indians | `T-` | 5 | tribal-government form 'band' |
| Chickasaw Health Consulting, LLC | `E-` | 4 | corporate form 'llc' with a Native signal |
| Colville Indian Housing Authority | `E-` | 4 | Native signal 'indian' |
| Cook Inlet Housing Authority | `E-` | 4 | appears in a field that is Native by construction |
| Fort Peck Housing Authority | `E-` | 4 | appears in a field that is Native by construction |
| OGLALA LAKOTA HOUSING AUTHORITY | `E-` | 4 | appears in a field that is Native by construction |

## Ambiguities

**325 names** reach two or more spine records. None was picked. `review/entity_candidates_ambiguous.csv` carries the competing IDs, the competing canonical names, the question and a blank ruling column. They are two different problems, so the file has an `ambiguity_type` column:

| Type | Names | What it means |
|---|---:|---|
| `competing_entities` | 320 | genuinely two or more distinct entities are plausible — the Oneida NY / Oneida WI class of problem. Needs a substantive ruling. |
| `possible_unlinked_spine_pair` | 5 | one `Entity_Master` row and one NEID that look like the same entity, because `entity_master`'s NEID cell is blank on 250 of 815 rows. Not an entity ambiguity — it is the open crosswalk gap AGENTS.md lists as queue item 4 ("finish NEID fuzzy pass, ~215"). Restricted to pairs whose canonical names are *identical* once true corporate-form synonyms (Inc/Corp/Ltd) are collapsed. Association, Foundation and Consortium are NOT treated as synonyms of Corporation, so Bristol Bay Native Corporation and Bristol Bay Native Association stay apart. |

**Byproduct worth taking:** the `possible_unlinked_spine_pair` rows are a ready-made worklist for that queue item. Ruling them closes the crosswalk gap and raises the true match rate without any new data pull.

Substantive ambiguities, highest occurrence first:

| Candidate | Competing | Occurrences |
|---|---|---:|
| Seminole Tribe | Seminole Tribe of Florida / The Seminole Nation of Oklahoma | 83 |
| Bristol Bay Native Corporation | Bristol Bay Native Corporation / Bristol Bay Native Association | 56 |
| nana regional | NANA Regional Corporation / NANA Regional Corporation, Incorporated | 43 |
| Mille Lacs Band | Minnesota Chippewa Tribe, Minnesota / Minnesota Chippewa Tribe, Minnesota (Mille Lacs Band) | 30 |
| Ponca Tribe | Ponca Tribe of Indians of Oklahoma / Ponca Tribe of Nebraska | 22 |
| leech lake band | Minnesota Chippewa Tribe, Minnesota / Minnesota Chippewa Tribe, Minnesota (Leech Lake Band) | 20 |
| Shoshone-Paiute Tribes | Paiute-Shoshone Tribe of the Fallon Reservation and Colony, Nevada / Shoshone-Paiute Tribes of the Duck Valley | 18 |
| WASHOE TRIBE OF NEVADA & CALIFORNIA | Washoe Tribe of Nevada & California (Carson Colony, Dresslerville Colony, Woodfords Community, Stewart Communi | 17 |
| fond du lac band | Minnesota Chippewa Tribe, Minnesota / Minnesota Chippewa Tribe, Minnesota (Fond du Lac Band) | 14 |
| GRAND PORTAGE RESERVATION TRIBAL COUNCIL | Minnesota Chippewa Tribe, Minnesota / Minnesota Chippewa Tribe, Minnesota (Grand Portage Band) | 13 |
| Kickapoo Tribe | Kickapoo Traditional Tribe of Texas / Kickapoo Tribe of Indians of the Kickapoo Reservation in Kansas / Kickap | 11 |
| grand portage band | Minnesota Chippewa Tribe, Minnesota / Minnesota Chippewa Tribe, Minnesota (Grand Portage Band) | 9 |
| Leech Lake Band of Ojibwe | Minnesota Chippewa Tribe, Minnesota / Minnesota Chippewa Tribe, Minnesota (Leech Lake Band) | 9 |
| Minnesota Chippewa Tribe | Minnesota Chippewa Tribe, Minnesota / Minnesota Chippewa Tribe, Minnesota (Fond du Lac Band) / Minnesota Chipp | 9 |
| Capitan Grande Band of Diegueno Mission Indians of California | Capitan Grande Band of Diegueno Mission Indians of California (Barona Group of Capitan Grande Band of Mission  | 8 |
| Chenega Corporation | Chenega Corporation / Native Village of Chenega | 7 |
| white earth band | Minnesota Chippewa Tribe, Minnesota / Minnesota Chippewa Tribe, Minnesota (White Earth Band) | 7 |
| Paiute Indian Tribe | Paiute Indian Tribe of Utah (Cedar Band of Paiutes, Kanosh Band of Paiutes, Koosharem Band of Paiutes, Indian  | 6 |
| port graham | The Port Graham Corporation / Native Village of Port Graham | 6 |
| White Mountain Apache Housing Authority | White Mountain Native Corporation / White Mountain Apache Tribe of the Fort Apache Reservation, Arizona | 6 |
| Liquor Ordinance of the Wichita and Affiliated Tribes | Wichita and Affiliated Tribes (Wichita, Keechi, Waco, & Tawakonie), Oklahoma / Wichita and Affiliated Tribes | 5 |
| Mille Lacs Band of Ojibwe | Minnesota Chippewa Tribe, Minnesota / Minnesota Chippewa Tribe, Minnesota (Mille Lacs Band) | 5 |
| paiute indian tribe of utah | Paiute Indian Tribe of Utah (Cedar Band of Paiutes, Kanosh Band of Paiutes, Koosharem Band of Paiutes, Indian  | 5 |
| Paiute-Shoshone Indian Tribe | Paiute-Shoshone Tribe of the Fallon Reservation and Colony, Nevada / Shoshone-Paiute Tribes of the Duck Valley | 5 |
| SAC FOX NATION MESKWAKI TRIBE | Sac & Fox Nation of Missouri in Kansas and Nebraska / Sac & Fox Nation, Oklahoma / Sac & Fox Tribe of the Miss | 4 |

## Traps enforced

Each of these has already cost the project once, so each is a hard rule in the matcher, not a heuristic:

1. **Never match on a single generic token.** A name whose entire distinctive content is one token from the tribe-word/place-word collision list (`cherokee`, `creek`, `oneida`, `seminole`, …) and which carries no tribal form word never reaches a spine entity. Bare *Cherokee* cannot reach Cherokee Nation; bare *Creek* cannot reach Berry Creek — the error SBA DSBS made three times.
2. **Never collapse qualified names.** Containment matching requires the spine alias to appear as a *contiguous phrase* and every uncovered token to sit in an explicit allow-list of corporate/programme words. *Absentee* is not in that list, so **Absentee Shawnee Tribe of Oklahoma** cannot collapse into **Shawnee Tribe**. Three distinct governments stay three.
3. **Oneida NY and Oneida WI.** The full token key retains the state qualifier and is tried *before* the state-dropped key. Where a name is genuinely state-ambiguous, both entities compete and the row goes to the ambiguous register unpicked. The $716M mis-split cannot recur through this matcher.
4. **`Pueblo` is Spanish for village.** Names using *pueblo* in its Spanish sense — *el/la/los pueblo*, *pueblo de*, *Pueblo Viejo* — are blocked before matching. El Pueblo de Abiquiu Library and PUEBLO VIEJO DOMINICANA CORPORATION are both caught.
5. **`Indian` also means South Asian.** Hindu Temple & Indian Cultural Center, North American Indian Muslim Association and the campus Indian Student Association are blocked. The word-order tell is encoded: *American Indian* is Native, *Indian American* is South Asian.
6. **`Indian <landform>` is a US place name.** Indian Creek, Indian Harbor, Indian Paintbrush, Indian Head, Indian River — blocked before matching.
7. **Federal agencies and programmes are not entities.** Bureau of Indian Affairs, Indian Health Service, HUD Office of Native American Programs, the Tribal Broadband Connectivity Program and the statutes named after people are all rejected.
8. **County and town names.** A place/civic regex (county, city of, school district, chamber of commerce, electric cooperative, volunteer fire, booster, little league, Falls, Heights, Junction …) blocks the name outright, and a following-token guard kills *Chippewa Falls*, *Cherokee County*, *Mohawk Valley*. A softer regex (library, museum, community college) only *flags*, because tribal colleges and tribal libraries are real.

## How much of this is noise — honest statement

Of 31,728 distinct names, **29,531 did not match the spine** (93.1%). That number is *not* 29,531 missing entities. Decomposing it:

The buckets below are mutually exclusive and sum to the unmatched total:

| Bucket | Names | Share of unmatched |
|---|---:|---:|
| Hard-blocked by a trap rule (place/civic, `Indian <landform>`, South Asian, federal agency, Spanish *pueblo*, bare generic token) | 3,318 | 11% |
| Competing spine entities — ambiguous, not missing | 325 | 1% |
| Proposed as genuine new entities | 3,919 | 13% |
| Rejected at the candidate gate | 21,969 | 74% |

Gate rejection reasons:

| Reason | Names |
|---|---:|
| no Native signal in the name and no Native-by-construction source | 18,300 |
| already ruled out by an existing nonprofit exclusion ruling | 3,063 |
| not name-shaped (sentence fragment, programme, statute, reservation geography, scrape artefact) | 606 |

**Estimate: roughly 86% of the unmatched harvest — about 25,287 names — is place-name noise, non-Native counterparties, or ordinary corporate names, not real Native entities.** The dominant sources of that noise are `np_orgs` (an IRS BMF candidate pool built to over-capture), `identifier_ledger.legal_business_name` (every UEI legal name in the contracting corpus, most of them non-Native primes and vendors), `subawards.prime_name`, and `deals.Counterparty_or_Funder` — which is *supposed* to be mostly non-Native, since it records banks, buyers and federal agencies on the other side of the deal.

The 3,919 proposed candidates are the residue after all of that: names carrying an explicit Native signal, or drawn from a field that is Native by construction (ANC ceiling roster, DOI NHO roster, deal `Native_Party`, compact `tribe`, gaming `tribe`, attributed lobbying `client_name`), which nonetheless reach no spine entity. Even there, expect a meaningful minority to be DBAs, subsidiaries of entities already on the spine, or historical name variants rather than new governments — which is exactly why they are proposals with a blank ruling column and not minted IDs. Minting an ID for something that turns out to be a county fair committee is worse than leaving it unassigned.

## Files written

| File | Rows | What it is |
|---|---:|---|
| `data/clean/entity_name_harvest.csv` | 31,728 | every distinct normalized name observed, with occurrence counts, sources, year range and match verdict |
| `data/clean/entity_candidates_new.csv` | 3,919 | matched nothing, looks genuinely Native, proposed prefix and class, blank `YOUR_RULING` |
| `review/entity_candidates_ambiguous.csv` | 325 | two or more spine entities plausible; never picked |
| `logs/35_entity_harvest.log` | — | full run trace |

This stage writes only those four files. Nothing in `data/spine/`, no `data/clean/cedar_*`, not `entity_master.csv`, not `review/cedar_review*.html` was opened for writing. The existing nonprofit exclusion rulings are read and **honoured** — a name already ruled out can never resurface as a new candidate.
