# Codebook fragment - Tribal certification layer

*Generated 2026-08-26 by `code/322_build_tribal_certification_codebook.py`. Fill rates and value vocabularies are computed from the staged files, not typed.*

**STATUS: STAGED, NOT REGISTERED.** These tables live in `data/staging/tribal_vendor_lists/` and are deliberately absent from the codebook master, `25_TABLES` and `27_SPEC`. They do not ship, and `code/321_gate_tribal_source_restriction.py` fails any build that tries - a tribal or ANCSA source publishes only on `consent_status = OPT_IN`, and **silence is UNRESOLVED, never permission.**

**THE ONE DISTINCTION TO CARRY OUT OF THIS FRAGMENT.** `assertion_class` separates three different facts that look alike: who OWNS a firm, who DOES BUSINESS WITH a tribe, and where a firm OPERATES. Only `OWNERSHIP` is evidence for attribution. A general vendor list is a good relationship dataset and a bad ownership claim, and many of its entries will be Home Depot.

## `tribal_certification_sources`

*62 rows, 24 columns. Source: `data\staging\tribal_vendor_lists\tribal_certification_sources_2026-08-26.csv`.*

One row per CERTIFYING AUTHORITY. Who asserts, about what class of thing, where, under what stated terms, and whether that source may be published.

| Variable | Type | Filled | Values / description |
|---|---|---:|---|
| `certification_source_id` | text | 100% | Identifier for the certifying source. Keyed on the AUTHORITY's spine id, never on row position, so it survives an insertion. |
| `certifying_authority_entity_id` | text | 100% | `tribe_id` in `data/spine/cedar_entity_spine.csv` of the entity MAKING the assertion - the tribe or ANCSA corporation, not the firm. |
| `certifying_authority_name` | text | 100% | Canonical name of the certifying authority. |
| `authority_class` | text | 100% | `TRIBAL_GOVERNMENT`, `ANCSA_CORPORATION`<br>Whether the authority is a tribal government or an ANCSA corporation. They certify different things under different powers. |
| `programme_name` | text | 100% | `NONE`, `TERO`, `SUBSIDIARY_DIRECTORY`, `SHAREHOLDER_VENDOR`, `VENDOR`<br>What the authority itself calls the programme. |
| `assertion_class` | text | 100% | `NONE`, `OWNERSHIP`, `RELATIONSHIP`<br>WHAT THE LIST ASSERTS, and the most load-bearing column in the layer. `OWNERSHIP` (TERO / Indian-preference certification, a parent naming its subsidiary, a shareholder-owned directory) is evidence about who owns a firm. `RELATIONSHIP` (a general vendor or supplier list) says only that a firm does business with the tribe. `OPERATING_ON_LAND` (a business licence registry) says only where a firm operates. Reading a RELATIONSHIP row as OWNERSHIP is the single failure mode that would discredit this layer. |
| `list_type` | text | 100% | `NONE`, `TERO`, `SUBSIDIARY_DIRECTORY`, `SHAREHOLDER_VENDOR`, `VENDOR`<br>The source's own form. TERO / SUBSIDIARY_DIRECTORY / SHAREHOLDER_VENDOR map to OWNERSHIP; VENDOR and TERO_EMPLOYER map to RELATIONSHIP; LICENSE maps to OPERATING_ON_LAND. |
| `list_url` | text | 35% | Landing page for the list as published by the authority. |
| `list_format` | text | 100% | `NONE`, `PDF`, `HTML`, `MACHINE_READABLE`, `PORTAL_SEARCH_ONLY`<br>MACHINE_READABLE (CSV/XLSX/DOCX/XML), PDF, HTML, PORTAL_SEARCH_ONLY or NONE. PORTAL_SEARCH_ONLY means the rows exist but are not retrievable as a set. |
| `entry_count_approx` | text | 35% | Approximate entries. READ `entry_count_is_verified` BEFORE USING THIS - several counts are the authority's own claim. |
| `entry_count_is_verified` | text | 100% | `N`, `Y`<br>`Y` only where the count was obtained by enumerating the source. A claimed count is not a counted one. |
| `identifiers_present` | text | 35% | Fields each entry carries. Note whether a JOINABLE identifier (UEI/CAGE/EIN) is among them - most lists carry none. |
| `carries_joinable_identifier` | text | 100% | `N`, `Y`<br>`Y` when the list publishes UEI, CAGE or EIN. When `N`, the list can produce CANDIDATES only and never a link: a name is not a key. |
| `update_frequency` | text | 35% | Cadence as STATED by the source, or NOT_STATED. |
| `verdict` | text | 100% | Typed discovery outcome for the CERTIFICATION product. LIST_FOUND_MACHINE_READABLE / LIST_FOUND_PDF / LIST_FOUND_HTML / LIST_BEHIND_LOGIN / LIST_REFERENCED_NOT_PUBLISHED / NO_LIST_FOUND / NOT_CHECKED / SITE_UNREACHABLE. `NO_LIST_FOUND` means not published on the authority's own site as at the capture date - a weaker claim than 'does not exist'. |
| `capture_date` | text | 100% | `2026-08-26`<br>Date the source was read. EVERY ROW HAS ONE. A snapshot testifies only about its own date: never present a historical capture as current, and never rule a current page against a historical record. |
| `source_terms_status` | text | 100% | `SILENT`, `NOT_CHECKED`, `TERMS_STATED_RESTRICTIVE`, `ROBOTS_DISALLOW`<br>SILENT / TERMS_STATED_PERMISSIVE / TERMS_STATED_RESTRICTIVE / ROBOTS_DISALLOW / NOT_CHECKED. SILENT means the source states nothing about reuse. NOT_CHECKED means the terms could not be read, which is not the same as absent. |
| `source_terms_quote` | text | 26% | The stated term, verbatim, where one exists. |
| `consent_status` | text | 100% | `UNRESOLVED`<br>UNRESOLVED / OPT_IN / OPT_OUT. **SILENCE IS UNRESOLVED, NEVER PERMISSION.** A federal record is public by statute; a sovereign government's own publication is not, and publicly reachable is not licensed for redistribution. |
| `suppression_key` | text | 100% | Flip this row's `consent_status` to remove an authority's rows - or to admit them if a TERO office opts in. Removal must be one field, not a search. |
| `publishable` | text | 100% | `N`<br>`Y` only when `consent_status = OPT_IN`. Enforced by `code/321_gate_tribal_source_restriction.py`, which fails the build rather than leaving the rule as prose. |
| `robots_note` | text | 61% | robots.txt behaviour: crawl-delay, named user-agents, or a WAF. A 403 on every path including robots.txt is a filter, not a refusal we can read, and not evidence of absence. |
| `notes` | text | 100% | Analyst notes, including every caveat that bounds the row. |
| `staged_by` | text | 100% | Script that produced the row. |

## `tribal_certification_rules`

*14 rows, 32 columns. Source: `data\staging\tribal_vendor_lists\tribal_certification_rules_2026-08-26.csv`.*

One row per (authority, programme): the ELIGIBILITY RULE behind the certification, quoted verbatim with a source URL and capture date. This is what lets a subscriber filter for themselves instead of trusting a threshold Cedar Press picked.

| Variable | Type | Filled | Values / description |
|---|---|---:|---|
| `certification_rule_id` | text | 100% | Identifier for one (authority, programme) rule. Keyed on the authority's spine id plus a programme slug, never on row position. |
| `certifying_authority_entity_id` | text | 100% | `tribe_id` in `data/spine/cedar_entity_spine.csv` of the entity MAKING the assertion - the tribe or ANCSA corporation, not the firm. |
| `certifying_authority_name` | text | 100% | Canonical name of the certifying authority. |
| `programme_name_as_they_call_it` | text | 100% | The programme's name in the authority's own words. Load-bearing: searching 'TERO' alone finds a minority of these - CSKT says Indian Preference Office, Muscogee says Contracting and Employment Support Office, Laguna files it under Tax Administration. |
| `programme_slug` | text | 100% | Short stable token for the programme, used in the key. A (tribe, programme) pair must be unique. |
| `rule_verdict` | text | 100% | `RULE_FOUND`, `RULE_PARTIAL`<br>RULE_FOUND / RULE_PARTIAL / RULE_NOT_PUBLISHED / BEHIND_LOGIN / NOT_CHECKED / SITE_REFUSED. FOUND and PARTIAL both REQUIRE a verbatim quote and a source URL - the build refuses to write them otherwise. A rule is QUOTED, never inferred from the list's contents. |
| `assertion_class` | text | 100% | `OWNERSHIP`<br>WHAT THE LIST ASSERTS, and the most load-bearing column in the layer. `OWNERSHIP` (TERO / Indian-preference certification, a parent naming its subsidiary, a shareholder-owned directory) is evidence about who owns a firm. `RELATIONSHIP` (a general vendor or supplier list) says only that a firm does business with the tribe. `OPERATING_ON_LAND` (a business licence registry) says only where a firm operates. Reading a RELATIONSHIP row as OWNERSHIP is the single failure mode that would discredit this layer. |
| `authority_citation` | text | 100% | The ordinance, code title or corporate statement the rule comes from, named precisely enough to re-find. |
| `authority_url` | text | 100% | Where the rule text was read. |
| `capture_date` | text | 100% | `2026-08-26`<br>Date the source was read. EVERY ROW HAS ONE. A snapshot testifies only about its own date: never present a historical capture as current, and never rule a current page against a historical record. |
| `ownership_pct_required` | text | 100% | `YES`, `NOT_STATED`, `NO`<br>YES / NO / NOT_STATED / NOT_CHECKED. Whether the programme requires an ownership percentage AT ALL. Measured 2026-08-26: 10 of 14 programmes YES, 1 NO, 3 NOT_STATED. |
| `ownership_pct_floor_numeric` | text | 71% | `51`, `60`, `100`<br>THE MOST USEFUL FILTER COLUMN IN THE TABLE. The lowest certifiable ownership floor as a number. Measured floors range 51 / 60 / 100 - **a blanket 51% filter silently mis-states Colville and CTUIR (both 60) and MHA (100)**. |
| `ownership_pct_threshold` | text | 100% | The threshold in the source's own terms, including grading. Prose; use the numeric column to filter. |
| `is_graded` | text | 100% | `Y`, `N`<br>Y where the programme ranks firms by ownership level rather than issuing a single binary certification. |
| `whose_ownership` | text | 100% | WHOSE ownership qualifies, and these are DIFFERENT POPULATIONS that do not nest: THIS_TRIBE_MEMBER / ANY_FEDERALLY_RECOGNIZED_TRIBE_MEMBER / ANY_NATIVE_PERSON / TRIBAL_GOVERNMENT_ENTITY / SHAREHOLDER_OR_DESCENDANT_OR_SPOUSE / PARENT_CORPORATION / MIXED_SEE_TIERS. A study of individual Native business ownership wants the first three and specifically NOT the sixth. |
| `tiers` | text | 100% | Each tier and its definition, in the source's words. |
| `control_requirement` | text | 100% | What the programme demands beyond ownership - management, voting control, anti-front tests. |
| `enrollment_requirement` | text | 100% | Whose enrolment counts. CRITICAL: most programmes admit members of ANY federally recognised tribe, so a certification is NOT evidence of citizenship in the certifying nation. |
| `residency_or_onreservation_requirement` | text | 100% | Residency or on-reservation criteria, or NOT_STATED. Often the geography bounds where the ordinance BITES rather than who qualifies - the codebook says which. |
| `verification_method` | text | 100% | What the authority demands and does: documents, site visits, interviews, or nothing at all. |
| `renewal_cadence` | text | 100% | How often certification must be renewed. Ranges from weekly republication to biennial recertification to none stated. |
| `expiry_terms` | text | 100% | Lapse, decertification and re-application bars. |
| `verbatim_quote` | text | 100% | The single most load-bearing sentence, exactly as written. A paraphrase is our claim; a quotation is theirs. |
| `verbatim_quote_2` | text | 100% | A second quote where the tiers need it. |
| `quote_source_url` | text | 100% | Where the quote was read. Required whenever a quote is present. |
| `rule_list_mismatch` | text | 100% | WHERE THE PUBLISHED LIST AND THE GOVERNING RULE DISAGREE, stated plainly. Colville's list flags firms certified at 0% ownership against a code floor of 60%; EBCI's list says 'TRIBAL MEMBER owned' when its own rule admits any federally recognised tribe at 51%. Cedar Press does not adjudicate these - it publishes both and names the conflict. |
| `searched` | text | 7% | What was looked for, required whenever the verdict is RULE_NOT_PUBLISHED, so the next pass extends the search instead of inheriting the conclusion. |
| `notes` | text | 100% | Analyst notes, including every caveat that bounds the row. |
| `consent_status` | text | 100% | `UNRESOLVED`<br>UNRESOLVED / OPT_IN / OPT_OUT. **SILENCE IS UNRESOLVED, NEVER PERMISSION.** A federal record is public by statute; a sovereign government's own publication is not, and publicly reachable is not licensed for redistribution. |
| `suppression_key` | text | 100% | Flip this row's `consent_status` to remove an authority's rows - or to admit them if a TERO office opts in. Removal must be one field, not a search. |
| `publishable` | text | 100% | `N`<br>`Y` only when `consent_status = OPT_IN`. Enforced by `code/321_gate_tribal_source_restriction.py`, which fails the build rather than leaving the rule as prose. |
| `staged_by` | text | 100% | Script that produced the row. |

## `tribal_certification_facts_sample`

*4 rows, 27 columns. Source: `data\staging\tribal_vendor_lists\tribal_certification_facts_sample_2026-08-26.csv`.*

Firm-level certification FACTS - firm X is asserted by authority Y as of date Z, per this URL. A SAMPLE: only rows whose identifier was read from the source and then tested against prime_contracts.csv.

| Variable | Type | Filled | Values / description |
|---|---|---:|---|
| `certification_fact_id` | text | 100% | Identifier for one certification fact. Keyed on (authority, identifier type, identifier) so it is stable across rebuilds. |
| `certification_source_id` | text | 100% | `TCS-ANRC-ARCSLO-00`, `TCS-ANRC-DOYONL-00`, `TCS-ANRC-NANARC-00`<br>Identifier for the certifying source. Keyed on the AUTHORITY's spine id, never on row position, so it survives an insertion. |
| `certifying_authority_entity_id` | text | 100% | `ANRC-ARCSLO-00`, `ANRC-DOYONL-00`, `ANRC-NANARC-00`<br>`tribe_id` in `data/spine/cedar_entity_spine.csv` of the entity MAKING the assertion - the tribe or ANCSA corporation, not the firm. |
| `certifying_authority_name` | text | 100% | Canonical name of the certifying authority. |
| `asserted_firm_name` | text | 100% | Firm name as the certifying authority prints it. |
| `identifier_type` | text | 100% | `UEI`<br>UEI, CAGE or NONE. |
| `identifier` | text | 100% | `F9M5KXFBC8N3`, `T65LCYKJCW58`, `VYN3SB8H8BL7`, `FZYKN78D9LJ2`<br>The identifier AS PUBLISHED BY THE AUTHORITY. Not looked up, not inferred, not name-matched. |
| `secondary_identifier_type` | text | 100% | `CAGE`<br>Second identifier type where published. |
| `secondary_identifier` | text | 100% | `3Q5W1`, `1R5E0`, `3JA23`, `3NCA0`<br>Second identifier where published. |
| `assertion_class` | text | 100% | `OWNERSHIP`<br>WHAT THE LIST ASSERTS, and the most load-bearing column in the layer. `OWNERSHIP` (TERO / Indian-preference certification, a parent naming its subsidiary, a shareholder-owned directory) is evidence about who owns a firm. `RELATIONSHIP` (a general vendor or supplier list) says only that a firm does business with the tribe. `OPERATING_ON_LAND` (a business licence registry) says only where a firm operates. Reading a RELATIONSHIP row as OWNERSHIP is the single failure mode that would discredit this layer. |
| `assertion_verbatim` | text | 100% | The authority's OWN WORDS. A paraphrase is our claim; a quotation is theirs. |
| `assertion_source_url` | text | 100% | Where the assertion was read. |
| `capture_date` | text | 100% | `2026-08-26`<br>Date the source was read. EVERY ROW HAS ONE. A snapshot testifies only about its own date: never present a historical capture as current, and never rule a current page against a historical record. |
| `first_seen` | text | 100% | `2026-08-26`<br>Earliest capture in which this firm-authority pair was observed. Equals `capture_date` until a Wayback pass extends the series. |
| `last_seen` | text | 100% | `2026-08-26`<br>Most recent capture in which the pair was observed. |
| `certification_status` | text | 100% | `ASSERTED_AS_OF_CAPTURE`<br>ASSERTED_AS_OF_CAPTURE / LAPSED_BY_CAPTURE / UNKNOWN. A single capture can only support ASSERTED_AS_OF_CAPTURE; LAPSED_BY_CAPTURE requires two captures and says the pair was present in the earlier and absent in the later. |
| `evidence_leg` | text | 100% | `THIRD_PARTY_PARENT`<br>THIRD_PARTY_PARENT (a corporation naming its own subsidiary), THIRD_PARTY_TRIBAL_GOVT (a tribe certifying a firm) or SELF. Tier A requires a leg that is NOT the firm, which is the whole point of this layer - a SAM socio-economic flag is self-certification. |
| `join_outcome` | text | 100% | `RESOLVES_EXISTING`<br>MEASURED against `prime_contracts.csv` at build time, never typed. RESOLVES_UNATTRIBUTED (the identifier is in the unattributed universe), RESOLVES_EXISTING (already attributed - the assertion corroborates rather than discovers), NO_MATCH_IN_PRIME, or CANDIDATE_ONLY_NO_IDENTIFIER. |
| `prime_rows_matched` | number | 100% | `799`, `1039`, `2`, `1327`<br>Prime contract rows carrying the identifier. |
| `prime_obligations_usd_matched` | number | 100% | `363488039.47`, `661274750.48`, `30526.75`, `259287449.11`<br>Obligations on those rows, USD nominal. This is the dollar value the assertion SPEAKS TO, not dollars newly discovered - read `value_added` for that. |
| `prime_current_tier` | text | 100% | `A`<br>Modal confidence tier on the matched rows today. |
| `prime_current_attributed_entity` | text | 100% | Entity the matched rows are attributed to today, if any. |
| `value_added` | text | 100% | `INDEPENDENT_CORROBORATION`<br>NEW_ATTRIBUTION (resolves something unresolved), NEW_ATTRIBUTION_PARTIAL, INDEPENDENT_CORROBORATION (confirms an existing link with a leg that is not the firm) or NONE. Corroboration is not nothing: tier A requires a non-firm leg and the reconciliation queue has almost none. |
| `consent_status` | text | 100% | `UNRESOLVED`<br>UNRESOLVED / OPT_IN / OPT_OUT. **SILENCE IS UNRESOLVED, NEVER PERMISSION.** A federal record is public by statute; a sovereign government's own publication is not, and publicly reachable is not licensed for redistribution. |
| `suppression_key` | text | 100% | `SUPPRESS::ANRC-ARCSLO-00`, `SUPPRESS::ANRC-DOYONL-00`, `SUPPRESS::ANRC-NANARC-00`<br>Flip this row's `consent_status` to remove an authority's rows - or to admit them if a TERO office opts in. Removal must be one field, not a search. |
| `publishable` | text | 100% | `N`<br>`Y` only when `consent_status = OPT_IN`. Enforced by `code/321_gate_tribal_source_restriction.py`, which fails the build rather than leaving the rule as prose. |
| `staged_by` | text | 100% | Script that produced the row. |

