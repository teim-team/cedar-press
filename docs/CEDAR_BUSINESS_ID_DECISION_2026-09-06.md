# The Cedar Business ID: the owner's decision, 2026-09-06

The owner adopted a reviewer's proposal on 2026-09-06 for a second permanent identifier, kept deliberately separate from the Cedar UID. This file records the decision, reconciles it with what the identity layer already holds, and lists what the terminal owns. It is written for the terminal; nothing in this repository mints, stores or validates a business id yet.

Read with `docs/IDENTIFIER_STANDARD.md` (the uid contract, the hub model, the identifier ledger), `docs/ARCHITECTURE_DECISIONS.md` ADR-008 (registrations as legal persons, proposed and not implemented) and ADR-020 (the NEST register is a sub-hub, not a second entity space), and `docs/IDENTIFIER_RETIREMENT_2026-09-05.md`.

## The decision, in the reviewer's words

> **CEDAR UID** = canonical Native institution or entity: tribe, ANC, NHO, tribal enterprise, Native nonprofit, tribal authority, and so on.
>
> **CEDAR BUSINESS ID** = commercial business or operating company: LLC, corporation, sole proprietorship, DBA, contractor, vendor, small Native-owned business, acquisition target, supplier, and so on.
>
> I'd call the second identifier the Cedar Business ID, or CBID. Something simple like `CB-0000001`. The number should mean absolutely nothing. No state code, tribe code, ownership type, year, NAICS, or anything else embedded in it. Those characteristics can change. The ID cannot.
>
> The CBID itself only means: Cedar has determined that this is a distinct business identity.
>
> Native ownership should be a relationship, not baked into the ID. Do not create `NB-`, `NONNATIVE-`, `TRIBAL-` prefixes, because ownership changes. The business ID doesn't change when ownership changes. For individual Native-owned firms, the owner doesn't necessarily need a public Cedar person ID at all: store `native_ownership_status = VERIFIED`, `native_ownership_basis = NAVAJO_PRIORITY_1_CERTIFICATION`, with the source. That avoids unnecessarily building a database of individual people.
>
> Distinguish three different things. **Business**: the legal or commercial identity, `CB-0001234`. **Establishment**: a physical operating location; a company can have 20 establishments but only one CBID. **Registration or certification**: an identifier assigned by somebody else (UEI, CAGE, state corporation number, TERO certificate, Native vendor number, SBA registration). Those should never become your canonical business identity.
>
> Name changes should not create new IDs. If it is the same continuing legal business, the CBID stays the same; store `business_alias`, `valid_from`, `valid_to`, `source`, `alias_type`. But genuine legal successors should get different IDs, connected by `SUCCESSOR_OF`. If Business A is acquired but continues operating legally: same CBID, new ownership relationship. If Business A disappears into Business B: `CB-A` is inactive or merged and `CB-B` continues. If the acquisition creates a new entity: new CBID.
>
> Keep Cedar UID and CBID impermeable. A company doesn't "graduate" from CBID to Cedar UID because it gets big. An enterprise doesn't get both unless there is a legitimate reason to represent two different concepts. Cherokee Nation Businesses may legitimately belong in the entity register because it is a canonical Native enterprise that anchors many datasets; one ordinary subsidiary is simply a `CB-` linked to the Cedar entity.
>
> A Cedar UID should represent an institution that Cedar treats as a canonical Native entity in its own right: tribal government, ANC, NHO, major Native institutional enterprise, tribal authority, Native nonprofit, other approved canonical entity class. A CBID should represent: commercial legal entity, operating subsidiary, privately owned Native business, sole proprietorship, vendor, contractor, acquisition target, portfolio company, supplier. **When uncertain, give it a CBID first.** Promotion to the institutional register requires an explicit adjudication. Never delete the CBID if historical records used it; establish an equivalence or supersession relationship if the classification is later found wrong.
>
> Naming: `CE-` for the entity register, `CB-` for businesses, and perhaps later `CS-` for establishments or sites. Event ids stay descriptive (`CEDAR-DEAL-`, `CEDAR-AWARD-`, `CEDAR-JOB-`). Not every object uses the same id style, and that is a strength.

The register the reviewer proposed, in outline:

```
CEDAR ENTITY REGISTER        CE-XXXXX      canonical Native institutions
        │  owns / controls / affiliates
        ▼
CEDAR BUSINESS REGISTER      CB-XXXXXXX    commercial businesses
        ├── external identifiers   EIN, UEI, CAGE, DUNS, SAM, state corporation id,
        │                          TERO vendor id, tribal source-list id, SBA id, PPP record
        ├── certifications         CERTIFIED_AS  (Navajo Priority 1, ...)
        ├── establishments         CS-XXXXXXX, one per operating location
        ├── ownership history      owner_id, owner_type, percent, effective dates, source, confidence
        ├── aliases                dated names, never new ids
        ├── succession             SUCCESSOR_OF, MERGED_INTO
        └── observations           employment, contracts, deals, procurement, jobs
```

Core table: `business_id`, `canonical_business_name`, `legal_name`, `business_type`, `formation_state`, `formation_date`, `dissolution_date`, `status`, `primary_naics`, `website`, `ultimate_native_entity_id`, `native_ownership_status`, `native_ownership_basis`, `first_observed`, `last_verified`. Most of these may be null; the id asserts only that the business is a distinct identity.

## Why the owner adopted it

The Cedar UID answers "which Native entity is this record attributed to?" and it answers it for 1,916 entities across every collection. It cannot answer "which business is this?", and the pipeline now generates that question faster than it can be answered by hand. The examples the reviewer gave are the ones the terminal already meets: a Navajo-owned contractor acquiring a regional construction company where neither party belongs in the entity register; a small firm that appears as five spellings of one name across a TERO list, a state corporation record, SAM, a PPP borrower file and a tribal procurement list; a deal target that surfaces three years later in USAspending, on an OSHA log, in a Form 5500, or in another acquisition. Without a permanent business identifier each of those is resolved again every time it appears. DUNS, UEI and CAGE solve that problem externally and none of them is Cedar's to rely on: DUNS is proprietary (`docs/IDENTIFIER_STANDARD.md` §4), the tribal certification directories publish no federal identifier at all (`docs/NATIVE_BUSINESS_IDENTIFIER_CROSSWALK_LOG.md`, measured on 249 objects: zero), and a UEI identifies a registration, which is not the same thing as a legal person (ADR-008).

## How this sits with what the identity layer already holds

The decision does not start from nothing. Four things in the spine are already the business register in embryo, and the reviewer's rules say what each becomes.

| what exists today | where | what the decision makes of it |
|---|---|---|
| `Individually Native-owned business`, an entity class in `cedar_identity_register.csv` (45 rows, handle prefix `CEDAR-ENT-`, self-parented, never rolls up, publication withheld absent consent) | `code/cedar_domain.py` `INDIVIDUAL_NATIVE_CLASS`; `docs/INDIVIDUAL_NATIVE_CLASS_PROPOSAL.md` | These are businesses by the reviewer's definition and belong in the business register. Their uids are **not deleted and not reused** (the standard's rule and the reviewer's rule agree). Each gets a `CB-` id, and the register records the equivalence. The class closes to new mints (decided the same day, below): from here a privately owned Native business is a `CB-` only. |
| `CEDAR-NEST-nnnnnn-CC`, the enterprise sub-hub register (4,798 enterprises since the owner's dataset became a builder input, ADR-034; 1,512 rows carry a stated ownership tie and 3,286 an affiliation that is not an ownership claim, `docs/methodology/nest.md`; keyed to `owner_hub_cedar_uid`) | `data/spine/cedar_nest_id_register.csv`; ADR-020; ADR-034 | An enterprise tied to a nation, ANC or NHO is a commercial operating company linked to a Cedar entity, and NEST is the business register's largest seed. The seed keeps each row's evidenced relationship class: an ownership relationship is written only where a source stated ownership, and an affiliation stays an affiliation, so the 3,286 affiliation rows do not become ownership by being seeded. The NEST id is retained as a source-scoped key beside the `CB-` id, as ADR-030 kept `facility_id` beside `cedar_place_id`; nothing is re-keyed by deletion. ADR-020's rule that a NEST id may never appear where a `cedar_uid` is expected carries over to `CB-` unchanged. |
| `CEDAR-PLACE-nnnnnn-CC`, the physical-place register (ADR-030) | `data/spine/cedar_place_id_register.csv` | This is the reviewer's establishment layer, already built: `place_class` is a column and the operator can change without the place changing. The `CS-` prefix is the reviewer's suggestion for a later establishment id; the place register already serves that role, and whether it is renamed or simply keeps its prefix is a naming choice, not a modelling one. A place keyed to a business rather than to an entity needs an `operator_cedar_business_id` beside `operator_cedar_uid`. |
| The identifier ledger (one row per `identifier_type`, `identifier`, entity; UEI, CAGE, EIN today; state ids and licence numbers welcome) | `cedar_identifier_ledger_final.csv`; standard §3 | The ledger's shape is the right one and it gains a second subject column and a validity interval: an external identifier binds to a `CB-` id or to a `CE-` uid, never to both on one row, with `valid_from`, `valid_to` and the evidence for the binding. The interval is not optional: `code/1071_identifier_driven_deal_sweep.py` finds CAGE codes re-paired from one UEI to another, a constant registration whose legal person changed, and an undated binding would attach one CAGE to two businesses at once or fuse two successors. An overlapping or undated binding stays unresolved. A UEI bound to a business rolls up to the entity through the ownership relationship, which is what ADR-008 asked for and could not have without a legal-person key. |
| ADR-008, the registration as a legal person (3,511 candidate legal persons keyed only as attributes of an entity, $173.9B of prime dollars through them) | `docs/ARCHITECTURE_DECISIONS.md` | Superseded by this decision. The key ADR-008 proposed per `(identifier_type, identifier)` is a registration key; the reviewer's rule is that a registration is never the canonical business identity. The business register is the legal-person layer; registrations hang off it. |
| The constellation's name-only from-side (2,365 TERO-certified directory rows keyed by `business_source_id`, 278 of them named after a person) and the certified-firm directory itself, 4,273 rows today (`docs/DATASET_CODEBOOK.md`; 2,393 when the crosswalk was built on 2026-09-02, with `business_entity_id` populated on 4 of them) | ADR-020; `docs/NATIVE_BUSINESS_IDENTIFIER_CROSSWALK_LOG.md`; `docs/DATASET_CODEBOOK.md` | These are the firms the reviewer says gain most from a `CB-` id, and the decision's "when uncertain, CBID first" is the answer ADR-020 declined to give with a uid. The 278 person-named rows are the exception that stays: a business named after its owner may hold a `CB-` id only under the publication policy's rule for a natural person's data, and the register must not become a register of people. |
| Deals (935 classified rows; buyer, seller, target as names and attribution to a Native entity) | `deals/deals_classified`; `docs/DEALS_IDENTIFIER_SWEEP_2026-09-02.md` | A buyer, seller or target gets a `CB-` id only after a party-type adjudication says it is a commercial business: a party that is a Cedar entity keeps its uid (the `ownership_events` sample holds a direct tribe-to-tribe land transfer), a real-property target is an asset and gets no business id, and an individual counterparty is a person and gets none. The ultimate Native owner stays a `CE-` uid, and the succession rules (same id through an acquisition that keeps the legal entity; merged or inactive when it disappears; new id when the deal creates a new entity) are the deals dataset's own rules from here. |

## Rules the terminal implements

These are the reviewer's rules restated as the contract the standard already uses for `cedar_uid`, so that `503_identity.py verify` and `62_no_regression_check.py` can hold them.

1. **The id encodes nothing and never changes.** Not on a name change, an ownership change, a move, a new NAICS, a certification, or a reclassification. One business, one `CB-` id, for as long as the records exist.
2. **Never reused, never dropped.** A merged, dissolved or reclassified business keeps its row, with a status. A `CB-` id pointed at a different business raises, as `HandleReuse` does.
3. **Impermeable to `cedar_uid`.** A `CB-` id may not appear in a `cedar_uid`, `cedar_uids` or any column the field map declares as entity identity, and a `CE-` uid may not appear in a business-identity column. An entity that is legitimately both (Cherokee Nation Businesses) holds two ids for two concepts, linked by an equivalence row that says why. No promotion without an adjudication record; no demotion by deletion.
4. **Ownership is a dated relationship with a source and a confidence,** never part of the id and never inferred from a name. `native_ownership_status` and `native_ownership_basis` on the register row summarise the current state; the history table holds every interval.
5. **Registrations are attributes, and each binding is dated.** UEI, CAGE, EIN, DUNS (internal only), state corporation numbers, TERO and tribal vendor numbers, SBA and PPP identifiers bind to the business in the identifier ledger with `valid_from`, `valid_to` and the evidence. None of them is the business's identity, a business with no external identifier is still a business, and a binding that overlaps another or carries no date stays unresolved rather than resolving to either business.
6. **Aliases, not new ids, for name changes.** `business_alias` with `valid_from`, `valid_to`, `source` and `alias_type` (legal, trade, filing variant, source spelling). A genuine legal successor gets a new id and a `SUCCESSOR_OF` edge. In a merger the surviving business keeps its id and the absorbed one is marked merged with a `MERGED_INTO` edge; only a deal that creates a new legal entity mints one.
7. **Establishments are children.** A location keys to its business and the business can change hands without the location changing.
8. **When uncertain, a `CB-` id.** The register asserts distinctness, nothing more. Fields may be null. Minting requires a distinct-identity determination with its basis recorded; it does not require Native ownership, a certification, or an external identifier.

## What the terminal owns

- The register files, in the spine, append-only, with a mint command, a verify command and regression keys on the pattern of `503_identity.py` and `1129_place_ids.py`: `cedar_business_register.csv`, `cedar_business_aliases.csv`, `cedar_business_ownership.csv`, `cedar_business_succession.csv`, and the identifier ledger's second subject column.
- The seed: NEST enterprises with their evidenced relationship class, the 45 individually owned entities, the certified-firm directories, the contracting awardees and subawardees with a UEI or CAGE, deal parties after party-type adjudication, and lobbying registrants (ADR-008's population). Each seed keeps its source key beside the new id, and the seed's acceptance is measured against the current inventories at build time, never against the counts quoted in this file.
- The stamp: `cedar_business_id` on every table where a business is the row's subject or a named party, in the same pass that stamps `cedar_uid`, with the raw name and the source identifier retained as evidence.
- The adjudication queue for the boundary: which enterprises are canonical institutions (`CE-`) rather than businesses (`CB-`), one reviewed row at a time, recorded with its basis. The default for anything not adjudicated is `CB-`.
- The equivalence rows for the 45 individually owned entities and for any NEST enterprise that is also a register entity (`nest.enterprise_existing_cedar_uid`, held at `adjudicate` in the retirement report, is this case).

## What this repository does with it

Nothing yet, and the following once the register exists:

- The field map declares `cedar_business_id` on the datasets where a business is a party: Contractors (the awardee), Subcontracting (prime and sub), Deals (buyer, seller, target), NEST (the enterprise; `enterprise_id` stays as the source key), Owned (the business; `business_entity_id` stays, as the field map already classes it, an object id kept beside `cedar_business_id`, because its populated values identify businesses that hold a Cedar uid and keep it), Lobbying (the registrant), and Federal Funding where the recipient is a business rather than an entity. The plural block gains no business column: a record's Native entities stay in `cedar_uids`, and a party list of businesses is its own aligned column.
- The writer refuses a `CB-` id in any identity column and a `CE-` uid in a business column, as it refuses a scope code in an identity field today, and never fills `cedar_uid` from a business id or a business id from an owner's uid.
- The codebook and the researcher guides say what the two identifiers mean and that they never substitute for each other; the viewer's entity search does not search businesses until a business register reaches the site as its own contract.
- The publication rule for individually Native-owned businesses (`may_publish_individual_native_field`) applies to the business id as it applies to the name: a `CB-` id on a withheld row would let a reader link the withheld business across datasets, which is what withholding exists to prevent. Decided with the two decisions below: the id is withheld with the name until consent is recorded. The writer today finds the row's `cedar_uid` in `cedar_entity_names.csv` and masks only where that register reports the individually owned class, so a firm minted as `CB-` only has nothing for that check to find. That is a precondition, not a footnote: no `CB-` only firm is published through the writer until the writer reads the business register's ownership, privacy and consent fields and applies the same rule through them. The same precondition gates decision 2 below.

## Two further decisions, made by the owner the same day

1. **The id carries two check characters.** The format is the reviewer's semantics with the standard's mechanics: a meaningless sequence, nothing encoded, and two trailing check characters over the same Crockford alphabet the uid uses (no `O`, `I`, `L`, `U`), so a business id is transcribed as safely as an entity id. The standard's section 0 gives the measurements that justify it. The terminal picks the digit width; seven digits, as the reviewer wrote, leaves room for ten million businesses and is the default.

       CB-0001842-XQ
       │  │       └─ two check characters, from two independent weightings
       │  └─ a sequence that means nothing
       └─ namespace

2. **The individually owned entity class closes to new mints.** The 45 `Individually Native-owned business` entities keep their uids and gain business ids with an equivalence row. From here a privately owned Native firm is a `CB-` only, its Native ownership a dated relationship with a certification as its basis, and the publication rule for the class applies to it through the ownership relationship rather than through the entity class. Until the writer reads that relationship from the business register, no `CB-` only firm ships (see the precondition above). A firm that is genuinely a canonical Native institution is admitted to the entity register by adjudication, under an existing class, never under this one.
