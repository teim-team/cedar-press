# Cedar Press: public dataset cleanup and harmonization

*The owner's specification, received 2026-09-05 and recorded here verbatim below
the rule. It governs the customer files, the samples the site serves, the
viewer and the researcher documentation. Where it and
`docs/COLUMN_ORDER_NOTE_FOR_THE_TERMINAL_2026-09-05.md` differ, this document
wins; the note's preface says where. The first step it asks for, the explicit
old-to-new field map, is `data/cedar/field_map.json`, rendered as
`docs/FIELD_MAP_2026-09-05.md`; the customer-file writer reads it through
`cedar_publication.apply_field_map` and refuses a flagship column that has no
decision. Everything the specification asks of the full tables (grain changes,
source reconciliation, the acceptance counts) runs in the data workspace and is
not certified by anything in this repository.*

---

## Objective

Turn the 12 Cedar Press collections into cohesive, research-ready datasets. Customers should receive one understandable dataset per topic, not a collection of internal processing tables. The downloadable data and the viewer must use the same approved public schema.

This is an implementation specification, not a certification that the full production datasets have already been cleaned. The reviewed materials include earlier sample bundles, the Explore implementation, and the current storefront manifest. Validate every instruction against the full current source tables before applying it. Earlier samples do not establish current error rates, coverage, missingness, or distributions.

Do not add new collections during this cleanup. Gaming and the identity register are not additional Cedar Press datasets in this scope. Preserve the existing distinction between Cedar Press record browsing and Cedar Grove's deeper analysis.

## 1. A consistent public structure

### Put Cedar's entity fields first

Use the same opening fields wherever applicable:

`cedar_uid`, `cedar_entity_name`, `cedar_entity_type`, `cedar_entity_role`.

Follow these with the dataset's own identifiers, then substantive fields, dates and geography, financial or other measures, meaningful research qualifications, and sources.

The Cedar UID remains the immutable identifier for the canonical Native entity. Do not redefine it as a contract, enterprise, filing, project, notice, or transaction ID. Those objects keep their own identifiers.

`cedar_entity_role` explains why the Native entity appears: recipient, owning entity, client, participant, certifying authority, or another documented relationship. A row about a subsidiary can properly carry its Native owner's UID while retaining the subsidiary's own name and business identifiers.

Resolve canonical names and classes from the approved register without overwriting the actual recipient, enterprise, institution, or organization name. Keep classification of the associated Native entity separate from classification of the record's subject.

Remove duplicate aliases of the same Cedar identifier from the public export. Remove retired CICD/NEID identifiers from public columns, explanatory text, and serialized values. Preserve useful official identifiers such as EIN, UEI, FAIN, document numbers, and bill IDs. A legacy official identifier is not automatically an unnecessary developer identifier.

### Preserve multiple entities without fabricating a primary entity

Retain explicit role-specific links when roles are stable, such as prime and subcontractor, payer and recipient, or owner and enterprise. These are not redundant identifiers when they represent different entities.

Where several Native entities legitimately participate, preserve all supported associations. Never select the first UID merely to fill the opening columns. Use a documented multi-entity representation or an explicitly declared record-entity relationship grain. Do not introduce a second customer-facing dataset to solve an internal join.

Keep the underlying event or object ID stable. When an event has multiple entity-association rows, document that distinction and count events by distinct event ID. Repeated event-level amounts must not become additional spending. Unallocated joint amounts must never be represented as each participant's attributable share.

The viewer must find the entity through every supported role, not only the first displayed UID. Blank attribution means unknown, unresolved, not applicable, or genuinely multiple according to a documented status, not automatically non-Native.

## 2. Remove clutter, not research meaning

Exclude developer-only material from public exports: script names, local paths, run identifiers, parser templates, token-match explanations, agent agreement counts, proposed redirects, internal queues, scratch fields, and notes about what someone should fix next.

Keep that material internally for reproducibility and review. Removing a warning column does not make a questionable record publishable. Resolve the problem or apply the appropriate publication restriction before exporting.

Retain concise, structured qualifications that change interpretation: estimated versus reported amounts, announced versus completed activity, historical ownership uncertainty, amendment status, missing date precision, geographic aggregation, and material coverage restrictions.

Replace mixed-purpose `Notes` columns with substantive fields and, only when necessary, a short `research_note`. Do not copy internal discussion into the note. A useful note explains the data, for example: "Amount covers the entire joint venture; the Native participant's share is not stated."

Do not remove columns simply because they are blank in a 10-row or 100-row sample. Review their full-data population and research value. Do not impose an arbitrary universal column limit. The goal is an intentional schema, not the smallest possible file.

Use stable snake_case field names in downloads and readable labels in the viewer. Define codes and units in the data dictionary. Keep identifiers as text, preserving leading zeros. Do not convert missing amounts to zero or incomplete dates to invented days.

## 3. Harmonize sources inside each dataset

For each collection, first classify every input as substantive records, supporting reference information, a derived aggregate, or an internal diagnostic. Only appropriate substantive records and verified enrichments belong in the public table.

Define what one row represents before combining sources. Map equivalent fields into common columns only when their definitions, units, timing, and record grain agree. Preserve meaningful differences using fields such as `record_type`, `amount_basis`, or `source_system` where necessary.

Different sources describing the same event should enrich one record, not automatically create multiple observations. Match using stable identifiers and documented evidence, not similar names alone. Revisions, duplicate source copies, separate transactions, and historical observations require different treatment.

Do not mix detail records and their totals as interchangeable rows. Do not manufacture one universal `amount` or `year` when the source concepts differ. Keep fiscal year, calendar date, reporting period, announcement date, and observation date distinguishable.

Use role-specific geography: recipient location, enterprise headquarters, project location, place of performance, or removal location. A recipient's county is not necessarily the county where the funded work occurs. Do not turn state or regional evidence into a precise county or tribal-area match without support.

Each dataset should have one public table, a researcher-facing guide, and a data dictionary. Supporting internal tables remain available to the pipeline, not as competing customer downloads. Large files may be partitioned for delivery without changing the logical dataset or schema.

## 4. Federal Funding

### Public purpose and row unit

Help users identify which recipients receive federal financial assistance, under which programs, in which periods, and in what amounts. For the requested simplified annual product, use an award-recipient-fiscal-year grain where stable award identity and compatible transaction measures support it. Keep the underlying transaction history internally.

### Keep and organize

Lead with Cedar attribution, followed by `award_id`, FAIN or other official award identifiers, recipient name and UEI, assistance type, agency and subagency, program code and title, fiscal year, first and last action dates, annual obligations, relevant loan measures, recipient geography, and source references. Retain a clearly labeled constant-dollar measure when its construction is validated and documented.

### Harmonization and cleanup

Reconcile historical FAADS and USAspending coverage before combining them. Source overlap is not additional spending. Sum only verified transaction-level changes within the intended award and year. Keep negative adjustments. Do not sum cumulative award values, loan face values, and subsidy costs together.

Where a historical source cannot support award-level identification, preserve an explicitly labeled source-record unit rather than inventing an award ID or allocating an aggregate to tribes. Source families that cannot support the main unit need an explicit record type and separate counting rules in the same public dataset.

Move proposed entity matches, attribution-rule transcripts, exclusion logs, deflator plumbing, and geographic matching diagnostics out of the public columns. Retain meaningful attribution status and actual recipient names. Do not attribute a consortium's full award to every member tribe.

### Researcher notes

Explain the row unit, obligation measure, fiscal-year basis, partial periods, historical coverage changes, loan treatment, and recipient-versus-beneficiary distinction. State that an unobserved award or blank amount is not evidence of no funding.

## 5. Federal Register and Agency Actions

### Public purpose and row unit

Make federal notices, agency actions, and associated consultation opportunities discoverable. Use a stable document or action ID and define whether linked sessions are separate records. Do not present a notice, a meeting announced in it, and an attendee as equivalent observations.

### Keep and organize

Keep document number, title, agency, subagency or program where useful, action or notice type, topic, publication date, effective date when applicable, event dates, comment deadline, format, location, Native participant roles, official citation, and source URL. Retain meaningful availability indicators for comments, summaries, or transcripts when verified.

### Harmonization and cleanup

Merge duplicate representations of the same document or action. Distinguish publication, meeting, deadline, and effective dates. Keep agency-wide or Indian-Country-wide documents even when no individual tribe is named, with their scope stated honestly.

Replace vague `channel` values with documented source or activity categories. Move build dates, matching methods, confidence shorthand, and extraction diagnostics internally. Keep short source quotations only when they materially clarify classification or participation.

Cross-reference overlap with Advocacy or NAGPRA instead of treating the appearances as unrelated events. A record's appearance in two thematic datasets does not establish two underlying actions.

### Researcher notes

Explain the difference between announced opportunities and documented participation, corrections and withdrawals, entity-specific versus broad scope, and what each date means. A notice inviting consultation does not prove consultation occurred.

## 6. Legislation

### Public purpose and row unit

Help users follow legislation relevant to Native entities, its subject matter, sponsorship, progress, and recorded votes. Make bills the primary browseable records, keyed by Congress, bill type, and number. Do not treat the same bill from two sources as two bills.

### Keep and organize

Keep bill ID, title, Congress, chamber, bill type and number, sponsor name and identifier, policy area, relevance scope, affected Native entities where supported, introduction date, latest action and date, status, companion bill ID, official URL, and useful sponsorship or voting information.

### Harmonization and cleanup

Use action histories to derive current status consistently rather than exposing contradictory status fields. Keep current status and its as-of date together. A new introduction in a later Congress is a different bill, even with the same title.

Do not imply that broad Indigenous-policy legislation names every tribe. Distinguish specific entity references from class-wide or topic-wide relevance.

Preserve substantive vote-level coverage the collection actually promises. When member votes or action records belong in the public dataset, use explicit record types and their own IDs in the same table. Do not replace those records with counts while claiming the same research coverage. Bill totals must use distinct bill IDs.

Remove classification agreement statistics, internal evidence paths, build flags, and matching notes. Retain readable relevance categories and limitations that affect interpretation.

### Researcher notes

Explain bill identity, status definitions, companion bills, relevance coding, the treatment of vote records, and the difference between passage by one chamber and enactment.

## 7. Indian Country Deals

### Public purpose and row unit

Provide one coherent record per distinct transaction or project-financing event, updated as its status changes. Multiple articles about an event should not create multiple deals.

### Keep and organize

Keep `deal_id`, readable title, Native participant and role, counterparties, target or project, deal category, industry, location, announcement date, closing date where confirmed, date precision, status, announced value, value basis, Native-attributable value only where supported, description, and primary sources.

### Harmonization and cleanup

Consolidate overlapping classifications such as `Deal_Category`, `transaction_type`, `Event_Type`, and `record_class` into a deliberate public taxonomy. Do not retain several almost-identical category fields simply because different scripts produced them. Preserve distinctions between financing, acquisition, partnership, asset sale, and project announcement when substantively meaningful.

Separate whole-project value from the Native participant's share. Do not allocate joint amounts by guesswork. Keep announcements, completed transactions, cancellations, and unconfirmed outcomes distinct. Preserve partial date precision instead of inserting the first day of a month.

A press release naming several genuinely distinct transactions may produce several records. A new source confirming an existing transaction normally enriches that record.

Remove parser lineage, source-file paths, classification timestamps, duplicate raw labels, and generic confidence letters. Keep concise factual limitations and source-specific evidence needed to interpret the deal.

### Researcher notes

Explain inclusion thresholds, event boundaries, announcement versus closing, undisclosed values, joint ventures, value bases, geography, and why missing transactions or values prevent unsupported market-total claims.

## 8. NAGPRA

### Public purpose and row unit

Make public notices and documented process information searchable while preserving their legal and evidentiary distinctions. Use a notice or document record as the primary unit, with correction relationships retained.

### Keep and organize

Keep document ID, notice type, publication date, institution name and location, documented process stage, named Native entities and their roles, stated counts by category, relevant deadlines, correction status, related notice ID, and official source links.

### Harmonization and cleanup

Keep consulted entities, affiliated entities, disposition-priority parties, and named recipients distinct. These relationships cannot be collapsed into an undifferentiated list of tribes.

Preserve the source's stated measurement units. Minimum-number-of-individuals measures, object counts, and other cultural-item counts are not interchangeable. Do not add them into a single total. Corrected notices must not inflate totals by repeating the same underlying holdings.

Resolve retired entity references through approved identity links; do not recover tribal identity from names alone. Move parser templates, span counts, extraction statements, artifact timestamps, and matching diagnostics internally. Retain short measurement qualifications when the published counts are ambiguous.

Do not expand the public export to precise sensitive locations or personal information simply because an upstream source contains them. Apply the established publication rules to each field.

### Researcher notes

State explicitly what each notice stage establishes. A notice, eligibility date, or named recipient does not by itself prove that a physical transfer has been completed. Explain corrections, missing counts, incomplete coverage, and the difference between institution geography and removal geography.

## 9. Advocacy and Government Engagement

### Public purpose and row unit

Combine lobbying and other documented advocacy or government-engagement activity into one collection. Do not reduce the scope to LDA filings merely because they are the easiest records to load.

### Keep and organize

Use an `activity_id` and explicit `activity_type`. Include Native entity and role, actual client or participating organization, representative or registrant, target agency or congressional body, topic, activity date or reporting period, source-specific filing ID, reported amount where applicable, amount basis, filing status, source system, and source URL.

### Harmonization and cleanup

Evaluate LDA filings, documented consultations, testimony, agency calendars, ex parte records, written comments, and relevant nonprofit reporting against a common activity schema. Include only source families actually obtained and supported. A research lead is not coverage.

Merge duplicate evidence of the same activity while preserving separate reports when they describe different reporting units. A registrant's reported income and a client's reported expenses may describe overlapping activity; do not add them automatically. Non-monetary activity has a missing amount, not zero lobbying expenditure.

Apply amendments and supersession consistently. Historical filings may remain when clearly labeled, but the default current-filing view must not count the original and amendment as separate spending.

Remove search keywords, matched aliases, attribution-script notes, internal exclusion explanations, and raw debugging fields. Preserve entity-link uncertainty, participation role, period, monetary basis, and amendment status where analytically relevant.

### Researcher notes

Explain the source families actually covered, non-covered activity, reporting lags, money double-counting risks, and the difference between an invitation, scheduled meeting, documented attendance, and filed advocacy.

## 10. Federal Prime Contracting

### Public purpose and row unit

Make contracting accessible without requiring customers to reconstruct every modification. Use an award-recipient-fiscal-year public record where transaction history supports that calculation, retaining the detailed history internally.

### Keep and organize

Keep `award_id`, contract number, parent award where meaningful, contractor name, UEI and useful CAGE identifier, Native association and role, fiscal year, first and last action dates, annual obligations, agency, industry and product/service classifications, contract description, set-aside or competition categories, recipient geography, place-of-performance geography, and source references.

### Harmonization and cleanup

Build annual obligations from verified incremental transaction measures. Do not sum repeated cumulative award values or eliminate genuine modifications because visible values happen to match. Preserve deobligations. Any award-ceiling or lifetime-value field retained must be explicitly labeled and documented as non-additive across years.

Match historical ownership to the relevant period. Current ownership must not automatically reassign earlier awards. Where ownership changes within the year, define a valid attribution-period grain or retain a clear qualification rather than assigning the full year by current owner.

Collapse duplicate set-aside and industry labels only after confirming equivalence. Native ownership, preference eligibility, and actual use of a preference in an award are different concepts.

Move attribution debugging, proposed identity decisions, build fields, and geographic matching machinery internally. Do not replace the contractor's name with the tribal government's name.

### Researcher notes

Explain annual versus lifetime amounts, modifications, recipient versus owner, ownership timing, partial periods, preferences, and geography. Award obligations are not automatically contractor revenue or economic impact.

## 11. Federal Subcontracting

### Public purpose and row unit

Provide one record per identifiable reported subaward, with its appropriate version or reporting-period treatment. A refreshed copy of the same report should not automatically be another subaward.

### Keep and organize

Keep subaward ID or number, source record ID where needed for uniqueness, prime award ID, subcontractor name and UEI, prime contractor name and UEI, relevant Native entity links for each side, recipient role, subaward date, reporting period, amount, description, industry, agency context, subcontractor geography, source, and a meaningful revision status.

### Harmonization and cleanup

Reconcile overlapping source systems and distinguish report snapshots from incremental transactions before combining amounts. Do not sum successive cumulative versions. Separate contract subawards from assistance subawards if both source populations are included, using an explicit award type.

Keep prime and subrecipient identities distinct. A Native prime does not make every subcontractor Native. Preserve which side creates the Native connection.

Do not fill subcontractor geography using the prime contractor's address. A subaward-to-prime ratio is suitable only when the numerator and denominator cover compatible award definitions, periods, and versions; otherwise leave it out of the default export.

Remove duplicate-report diagnostics, identity candidates, promotion timestamps, and matching traces. Retain the information needed to establish version, scope, and Native association.

### Researcher notes

Explain source coverage, reporting limitations, revisable values, Native role, and why prime and subaward amounts must not be added as independent federal spending.

## 12. Natural Resources

### Public purpose and row unit

Bring resource-related payments, revenues, distributions, and relevant financial events into one dataset with an explicit record type and measurement level.

### Keep and organize

Keep event or source record ID, recipient, beneficiary and payer where different, related operator or asset where supported, Native association, resource and commodity, revenue type, period start and end, payment or announcement date with its meaning, amount, measurement status, aggregation level, geography, land status where supported, and source.

### Harmonization and cleanup

Do not assign aggregate Indian Country revenue to a particular tribe. Distinguish entity-specific records, regional aggregates, and countrywide aggregates. Keep tribal and individual beneficiary populations separate when the source supports that distinction.

Keep royalties, distributions, reclamation grants, budgets, announced allocations, and actual payments distinguishable. A report announcing an allocation is not automatically evidence that cash was received that day.

Avoid double-counting the same financial event across source systems or against its appearance in Federal Funding. Preserve a cross-reference when a reliable common identifier exists.

Move build notes and allocation-code details internally. Keep aggregation level, sign meaning, beneficiary distinctions, and measurement status. Document validated allocation rules and their effective periods; do not fill unsupported tribal shares.

### Researcher notes

Explain which amounts can be compared or summed, payment versus announcement dates, aggregate coverage, beneficiary populations, and geographic limitations. Absence of a named tribal recipient is not zero tribal revenue.

## 13. NEST

### Public purpose and row unit

Describe Native enterprise ownership and organizational relationships. Use a clearly defined enterprise-owner relationship, with an effective period where known. Count businesses by distinct enterprise ID, not by the number of ownership relationships.

### Keep and organize

Keep enterprise ID, legal or published enterprise name, trade name where useful, Native owner UID/name/type, immediate parent enterprise ID and name, relationship type, documented ownership percentage, industry, operating status, business location, official business identifiers, ownership dates or observation dates, source, and material relationship qualifications.

### Harmonization and cleanup

Distinguish legal ownership, joint venture participation, affiliation, management, and service relationships. A firm serving a tribe is not thereby owned by it. Subsidiaries remain distinct legal businesses even when they share a Native owner.

Merge duplicate observations only after confirming the same enterprise and relationship. Similar names, common addresses, or a shared owner are not sufficient. Multiple owners must remain visible, not be replaced by an arbitrary primary owner.

Separate an ownership effective date from the date Cedar first observed a website listing. Do not infer historical existence or continuous ownership from a current page.

Remove raw normalization strings, proposed identifiers, constellation debugging, duplicate-group diagnostics, machine paths, and script notes. Preserve useful public relationship evidence and uncertainty rather than disguising a contested affiliation as verified ownership.

### Researcher notes

Explain enterprise versus owner, immediate versus ultimate parent, ownership versus affiliation, joint ventures, dates, and known coverage gaps. Do not claim the file is a complete census of Native enterprises without evidence.

## 14. Native Nonprofits

### Public purpose and row unit

Identify relevant nonprofit organizations and make their reported characteristics and finances usable. Use organization-EIN-reporting-period records for financial analysis; directory-only records must be explicitly distinguishable and must not receive a fabricated financial year.

### Keep and organize

Keep EIN as text, organization name, associated Native entity and relationship, Native-controlled or Native-serving classification where supported, city/state, nonprofit activity classification, relevant tax status, filing or reporting period, financial measures with exact definitions, filing source, and source URL.

### Harmonization and cleanup

Combine BMF, returns, audited material, and other verified sources only when they refer to the same legal organization and compatible reporting period. A retrieval date is not a tax year.

Keep revenue, expenses, assets, income or receipts measures, federal award expenditures, and lobbying expenditures distinct. Confirm the source definition before renaming `bmf_income_amt`; do not casually label it net income. A newer organizational snapshot is not automatically a new annual financial observation.

Native control, Native service populations, tribal-government identity, and a textual name match are different concepts. A nonprofit serving several tribes must not be assigned to one by a shared word in its name.

Remove agent research narratives, matching-token fields, coding agreement counts, proposed redirects, review queues, and build dates. Resolve contested links before presenting them as settled; keep material public classifications and limitations concise.

### Researcher notes

Explain population inclusion, EIN identity, tax/reporting periods, financial definitions, amendments, source lags, and the distinction between Native control and Native-serving activity.

## 15. Individually Owned Native Businesses

### Public purpose and row unit

Describe individually Native-owned businesses using publishable, supported listings and certifications. Do not confuse individual Native ownership with tribal-government ownership.

### Keep and organize

Keep business ID, business name and trade name where publishable, business category, services, publishable business location and contact channels, listing or certifying authority, program, certification status and dates where stated, source, and observation date.

### Harmonization and cleanup

Normalize business categories across issuing directories while preserving the issuing authority's actual certification and preference terminology. Different programs are not necessarily equivalent certifications.

Separate the business from the nation or office that lists or certifies it. A certifying nation's Cedar UID may be an associated entity link, but its role must be labeled `certifying_authority`, not owner. Use an existing business Cedar UID only when the approved identity system already assigns one appropriately.

Multiple directory listings should enrich one supported business record where identity is verified. Certification by two authorities does not automatically mean two businesses, but same-name businesses must not be merged without evidence.

Apply publication permissions before producing any preview, download, search index, or Cedar response. A business website does not override a restriction in the publication policy. Do not reintroduce withheld names through aliases, source text, or fallback fields.

### Researcher notes

Explain source-by-source coverage, certification meaning, observation dates, publication restrictions, and why absence from the roster does not establish that a business is not Native-owned. Do not present current listings as historical coverage.

## 16. Researcher-facing documentation

Write one substantive guide per dataset, not a developer changelog. Each guide must explain its purpose, population, row unit, key identifiers, actual source coverage, time and geography, field meanings, missing-value conventions, entity relationships, revisions, limitations, suitable analyses, and unsafe aggregations.

Include a field dictionary with readable label, definition, data type, units, allowed values where relevant, and when a blank is meaningful. Explain source-dependent fields without exposing internal implementation notes.

Use measured coverage and counts from the finished public table. Do not advertise the sum of rows across internal staging, linkage, and summary tables as the dataset's size. Distinguish record counts, distinct events, distinct entities, and reporting periods.

Put dataset-level version, release date, citation, and methodology in the documentation or manifest. Do not append `cite_as`, `cut`, or other metadata as fake CSV observations. Preserve concise row-level source references and record-specific qualifications.

## 17. Implementation and acceptance

Before editing, inventory the current full inputs and create an explicit old-to-new field map. Every field must have a decision: keep, rename, combine, derive, move to documentation, keep internally, or withhold. For combined fields, test whether values genuinely agree; do not simply keep the first nonblank value.

Generate public exports from approved field lists. Do not delete raw evidence or mutate adjudicated Cedar identity decisions. New upstream fields must require a publication decision rather than appearing automatically in customer data.

For each dataset, report the original and final row counts, distinct record counts, final column count, excluded records with reasons, duplicate keys, unsupported entity links, missing sources, and any unresolved blockers. Reconcile every removed or combined row. Financial totals must reconcile at the relevant unit and source scope, not just globally.

Check several entities across the collections. Their Cedar identities should agree while their roles, actual record subjects, historical ownership, and geography remain distinct. Joining detailed datasets on UID alone can multiply observations; give users a safe entity-level or entity-period aggregation example before joining measures.

Test the exact CSVs and viewer against the same release: entity filters, reporting-period filters, source links, meaningful statuses, all matching export rows, and multiple-entity records. Verify that withholding holds across every display and export path.

Complete the work dataset by dataset, prioritizing validated 2025-2026 coverage where that is the current launch plan, without discarding older records or pretending those years are complete. Finish with 12 cohesive public datasets, 12 researcher guides, field dictionaries, and a clear account of anything still awaiting evidence. Do not label a schema-only change or a cleaned sample as a fully validated production release.
