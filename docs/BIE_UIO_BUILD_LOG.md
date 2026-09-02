# BIE Schools and Urban Indian Organizations - build log
*Built 2026-08-06 by `code/75_add_bie_schools_and_uios.py`. Every entity below carries a retrieved source URL and a verbatim quote; nothing here was typed from memory.*

## The distinction that is the whole task

A **BIE-operated** school is a federal school. The Bureau of Indian Education runs it, and the money spent on it is the federal government's own spending. Booking it to a tribe would be a false attribution of the most damaging kind, because the numbers would look entirely plausible. A **tribally controlled** school is a grant or contract school (P.L. 100-297 / P.L. 93-638) run by a tribe or a tribal school board, and those do belong to a tribe.

**56 of the 185 elementary and secondary schools added are federally operated and must NOT roll up to any tribe.** Their `parent_native_entity` is empty by rule, not for want of research, and `reconciliation_status` records that explicitly.

A **UIO** is owned by no tribe at all. Title V of the Indian Health Care Improvement Act funds nonprofits serving urban AI/AN people from many tribal affiliations; that is the design of the programme, not a gap in the data. `parent_native_entity` stays empty for all of them and `serves_native_entities` carries the relationship - the same ownership-vs-service ruling already made for Native American Health Center and the Alaska constellation organisations.

## Sources

| Source | URL | Verbatim quote |
|---|---|---|
| BIE school directory (landing page) | https://www.bie.edu/schools | "Here are 183 Bureau-funded elementary and secondary schools and residential facilities. Of these, 55 are BIE-Operated and 128 are Tribally Controlled. The BIE also directly operates two postsecondary institutions: Haskell Indian Nations University (HINU) and the Southwestern Indian Polytechnic Institute (SIPI)." |
| BIE school directory (live web experience item) | https://biamaps.geoplatform.gov/BIE-Schools-Directory | "There are 187 Bureau-funded elementary and secondary schools on 64 reservations in 23 states, serving approximately 40,000 Indian students. Of these, 58 are BIE-operated and 129 are tribally controlled under BIE contracts or grants." |
| BIE school directory (data behind the map) | https://services1.arcgis.com/UxqqIfhng71wUT9x/arcgis/rest/services/BIE_Schools_Directory/FeatureServer/0 | n/a - feature service; 187 features returned |
| IHS Office of Urban Indian Health Programs | https://www.ihs.gov/urban/urban-indian-organizations/ | "The Urban Indian Organizations (UIO) listed below have current Title V Indian Health Care Improvement Act contracts with the Indian Health Service. UIOs have been arranged in alphabetical order based on the IHS area and respective State they belong in." |
| NCUIH member directory (cross-check) | https://ncuih.org/uio-directory/ | "There are 41 Urban Indian Organizations in the United States who contract with the Indian Health Service. Urban Indian organization means a nonprofit situated in an urban center governed by a board of directors of whom at least 51 percent are American Indian and Alaska Natives, for establishing and administering an urban Indian health program and related activities as described in the Indian Health Care Improvement Act." |

### A source discrepancy worth recording

The BIE landing page says **183 schools, 55 BIE-operated, 128 tribally controlled**. The live web experience the same page redirects to says **187 schools, 58 BIE-operated, 129 tribally controlled**, and the feature service behind it returns exactly 187 features split 58/129. The landing-page text is stale. This build uses the feature service, because it is the data the directory actually renders and the only one of the two that can be counted rather than read.

Removing Haskell Indian Nations University and the Southwestern Indian Polytechnic Institute - BIE-operated **post-secondary**, and the concurrent TCU agent's to add - leaves **185 elementary and secondary schools: 56 BIE-operated and 129 tribally controlled**.

### The UIO count

IHS lists **41 entries across its eleven area pages** - the Title V direct-service roster, and the figure of roughly 41 UIOs in the brief - plus **4 more** on its Regional / National / Tribal page. Native American LifeLines accounts for two of the 41 because it runs sites in Baltimore and Boston; NCUIH lists those as two members, which is how it reaches 41 while naming 40 distinct bodies. They are one legal person with one EIN, so this build creates **one** entity with both locations recorded. Two rows would double-count every dollar it receives.

That gives 44 distinct organisations. NCUIH itself is one of them and is already in the spine as `ITO-RBNHLT-00`, so it is refused as a duplicate rather than added again - leaving **43** new entities.

## What was added

| Class | Entities | Notes |
|---|---|---|
| BIE School - `bie_operated` | 56 | Federal schools. No tribal parent, by rule. |
| BIE School - `tribally_controlled` | 129 | 31 have a parent tribe resolved at tier B (affiliation, not ownership); the rest keep `seek_parent`. |
| Urban Indian Organization | 43 | No tribal parent, by rule. |
| **Total** | **228** | spine 1082 -> 1310 |

## Parent attribution for tribally controlled schools

The BIE directory does not name the operating tribe, so the parent is an inference from the school's name resolved through `33_apply_party_rulings.resolve_entity` - the one resolver - and then put through two refusal guards. It is recorded at **tier B as affiliation, not ownership**, following the standing precedent for the four Navajo BIE grant schools and Kayenta Township. `parent_entity_id` is left empty on purpose so that no hierarchy rollup fires on the strength of a name.

The guards, and what each one actually caught here:

- **Alaska guard.** The spine holds Alaska Native Villages named `Circle` and `Eagle`. Containment resolved *Circle of Life Academy* (White Earth, Minnesota), *Circle of Nations* (North Dakota), *Little Eagle School* (Standing Rock, South Dakota) and *Two Eagle River School* (CSKT, Montana) onto them. All four refused.
- **Overlap guard.** The shared tokens must include one that identifies rather than describes. `{township}` alone resolved *Indian Township School* onto Passamaquoddy Indian Township - substantively right, but on evidence too thin to publish, so refused.
- **Trap words** (`creek, cherokee, colorado, ojibwe, shawnee, oneida, apache, central, eagle, river, mountain, santa`) cannot carry a match alone. This refuses the three *Cherokee Central* schools and *Oneida Nation School* - each of which is in fact tribally run, and each of which would be indistinguishable from a place-name coincidence to any rule this build could state.
- **Organisation type** bars city / county / university / cooperative / public, with `Cooperative Association` exempt as the IRA-era name for Alaska village governments.
- **Candidate class.** A tribally controlled school is controlled by a TRIBE, so only government-class spine rows (plus federal-level constituency entities, which is how the Fond du Lac Band is filed) may be a parent. This caught a live cross-agent error: *Sequoyah High School* (Tahlequah, Oklahoma - Cherokee Nation) resolved by containment on the single token `sequoyah` onto `Sequoyah Fund Inc., The` (`CDFI-SQYHFN-00`), a North Carolina CDFI the concurrent CDFI agent had just written into the spine. Wrong entity type, wrong state, wrong tribe - and it would have read as perfectly ordinary in a table.

Result: **31 of 129 tribally controlled schools** carry a parent. The remainder are a known unknown rather than a guess; a wrong tribe is a published error.

## Identifiers and dollars found

Elijah's finding held: **federal funding and FAADS beat contracting decisively** for these populations. Searching contracting alone would have made both classes look nearly dollarless.

| Dataset | Obligations matched |
|---|---|
| federal_funding | $3,537,539,150 |
| prime_contracts | $235,304,731 |
| faads_all_agencies | $120,183,074 |
| subawards | $12,582,879 |
| nonprofit_990 | $0 |
| **Total** | **$3,905,609,834** |

- Entities linked to at least one identifier or award: **114 of 228**
- Link rows written: **302** -> `data/clean/bie_uio_identifier_links.csv`
- Per-entity dollars -> `data/clean/bie_uio_dollars_by_entity.csv`

### How the dollars may and may not be used

| Bucket | Amount | Publishable as tribal revenue? |
|---|---|---|
| BIE-operated schools | $42,871,052 | **No.** Federal spending on federal schools. |
| Tribally controlled, parent resolved | $834,393,999 | **Not yet.** Tier B AFFILIATION; the school board is a distinct legal person from the tribe. |
| Tribally controlled, parent unresolved | $2,582,952,615 | **No - no tribe named.** The school owns these dollars; which tribe controls the school is an open question, not an assumed one. |
| Urban Indian Organizations | $445,392,167 | **No tribal owner exists.** Attribute to the UIO itself. |

### Two link-stage guards that changed the answer by billions

**Direction.** `resolve_entity`'s containment branch accepts a match in either direction, which is correct for the job it was written for. Pointed at award data it inverts: a tribe's own name is a SUBSET of its school's name, so `CHICKASAW NATION` resolved onto *Chickasaw Children's Village* and carried **$2.8B** of the Chickasaw Nation's federal funding onto a school. The same shape put the Yakama Nation's $917M on a school and the Blackfeet Nation's $568M on a dormitory, and matched `SANTA FE LTD` and `CHICAGO`. A first pass totalled **$13.4B**, most of it other people's money. Requiring the recipient to be at least as specific as the entity - and to add nothing beyond grantee form (`board`, `education`, `grant`, `bia`, `day`) - brings it to **$3,905,609,834**.

`district` is not on that allowed list, deliberately. *Menominee Indian School District* is the public district in Keshena; *Menominee Tribal School* is the BIE grant school in Neopit. One added word, two institutions, $112M between them.

**State.** The award recipient's state must equal the entity's state. School and clinic names repeat across the country, and without that check a place-name coincidence is indistinguishable from a match.

### A double-count avoided

`faads_transactions.csv` is **excluded** from the totals above. It is not an independent source: all 59,514 of its distinct (fain, action date, recipient, amount) keys also appear in `faads_transactions_all_agencies.csv`. Reading both counted $53M of the same awards twice - standing rule 7 wearing different clothes.

## Source defects found (reported, not corrected)

- **Website fields swapped.** The BIE directory gives *Hannahville Indian School* (Wilson, MI) the site `hanaadlicsd.com` and *Hanaadli Community School/Dormitory Inc.* (Bloomfield, NM) the site `hannahvilleschool.net`. Each school has been given the other's website. Recorded as retrieved; not silently corrected.
- **`Navajo_Operation` is an administrative grouping, not an ownership field.** *Blackwater Community School* (Coolidge, AZ - Gila River, and administered from the Albuquerque Education Resource Center) is tagged `Tribally-Controlled (Navajo)`. It is therefore recorded as metadata and **never** used to attribute a school to the Navajo Nation. Had it been trusted, 35 schools would have been booked to Navajo on the strength of a field that demonstrably does not mean that.

## Refused

Full list with reasons: `review/bie_uio_refusals.csv` (6176 rows).

| Reason | Count |
|---|---|
| guard | 5520 |
| state mismatch | 284 |
| recipient is BROADER than the entity - a parent body, not this entity | 216 |
| resolver | 86 |
| recipient adds identifying words beyond grantee form | 59 |
| no distinctive token after stripping school words | 8 |
| BIE-operated post-secondary | 2 |
| already in the spine | 1 |

Named refusals worth keeping in view:

- **Haskell Indian Nations University** and **Southwestern Indian Polytechnic Institute** - BIE-operated post-secondary, owned by the concurrent TCU agent. Present in the same feature service, which is why its 187 features become 185 schools here.
- **National Council of Urban Indian Health** - already in the spine as an Intertribal Organization (`ITO-RBNHLT-00`). Refused as a duplicate rather than added a second time.
- **Urban Indian Health Institute** - added, but flagged `review_possible_division`. IHS lists it under *Tribal* as a Tribal Epidemiology Center rather than a Title V direct-service grantee, and its own site publishes a press contact at `sihb.org`, which suggests it is a division of Seattle Indian Health Board. No retrieved statement says so outright, so the relationship is flagged, not asserted, and must be settled before any dollars roll up.

## Scope this build stayed out of

- `TCU-` and `CDFI-` prefixes: another agent's concurrent work.
- `api.usaspending.gov`: held by a puller with four jobs queued. Every host used here (`bie.edu`, `biamaps.geoplatform.gov`, `arcgis.com`, `services1.arcgis.com`, `ihs.gov`, `ncuih.org`) is unrelated to it.
- `data/clean/cedar_*` and `review/cedar_*.html`: not written. The identifiers found here land in new files for review rather than in the published ledger.
- `code/00_run_all.py`: not run.

## Reproduce

```
py -3 code/62_no_regression_check.py           # before
py -3 code/75_add_bie_schools_and_uios.py
py -3 code/62_no_regression_check.py           # after
```

Raw payloads and their retrieval manifest: `data/raw/external/bie_uio/` (`_SOURCE_MANIFEST.csv`).
