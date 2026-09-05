# Cedar Press: public dataset cleanup and harmonization

*The owner's specification, received 2026-09-05 and recorded verbatim in two
parts: the cleanup and harmonization brief (first), then, later the same day,
the exact public column specification and the identifier retirement rule (the
addendum at the foot of this file). Where the two differ, the addendum wins:
the opening block is `cedar_uid`, `canonical_name`, `entity_class`,
`cedar_entity_role`; Legislation and NAGPRA carry the plural aligned-array
block; every dataset ends with `research_note`; this pass changes columns and
never rows, identities or publication eligibility, so the annual grain the
brief mentioned for Funding and Contracting is withdrawn. One conflict inside
the addendum is resolved by its own later rule: the Funding list keeps
`recipient_duns` and the retirement rule says not to publish DUNS, so DUNS
stays internal and Funding ships 39 columns. The map that implements this is
`data/cedar/field_map.json` (rendered as `docs/FIELD_MAP_2026-09-05.md`); the
customer-file writer reads it through `cedar_publication.apply_field_map` and
refuses a column with no decision, a competing identifier awaiting
adjudication, or a retired scheme's name in a shipped value; the retirement
report is `docs/IDENTIFIER_RETIREMENT_2026-09-05.md`. Everything the
specification asks of the full tables (value-for-value validation of renames,
the combine crosswalks, the row-count and totals proof, the rows-affected
counts) runs in the data workspace and is not certified by anything here.*

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


---

# Addendum, later on 2026-09-05: the exact public column specification

*Recorded verbatim. It supersedes the brief above where they differ.*

I've now specified the exact public column order for all 12 datasets, along with a field-by-field map showing what stays, gets renamed or combined, or moves out of the customer-facing files.

The largest reductions are Native Nonprofits from 67 to 24 columns, NEST from 65 to 30, and Prime Contracting from 72 to 49. Those starting counts come from the current published sample headers, not the older review bundle.

This is the exact specification for the next export, not a claim that the production files have already been rewritten. I also removed the earlier suggestion to aggregate funding and contracting into annual rows from this task. This pass changes columns, not row structure or Cedar identities.

## Scope

Produce one cohesive public dataset per collection, using the exact ordered column lists below.

This pass covers column selection, naming, order, source-field harmonization, and presentation. It does not authorize row aggregation, deduplication, changes to publication eligibility, or reassignment of Cedar UIDs.

Apply these schemas to the actual customer exports, not merely the columns visible in the website table. Generate the downloadable files, samples, viewer labels, and Explore mappings from the same approved schema.

The field-by-field companion accounts for the inspected source columns. Full combined customer files may contain additional source-prefixed fields. A substantive field that has not been mapped must be reviewed before enforcing the schema, not silently dropped.

## Shared identity and presentation rules

For records with one canonical Native entity association, start with:

    cedar_uid
    canonical_name
    entity_class
    cedar_entity_role

Use canonical_name and entity_class rather than introducing another pair of aliases. Resolve them from the same approved Cedar register across datasets.

The Cedar UID identifies the canonical Native entity. It does not replace the actual enterprise, recipient, nonprofit, filing, award, or event identifier.

cedar_entity_role explains the association: recipient, owner, affiliate, client, participant, or another supported relationship. A subsidiary can retain its own business name and identifiers while carrying its Native owner's Cedar UID.

Keep role-specific Cedar IDs when they represent different entities, such as prime_cedar_uid and sub_cedar_uid.

### Records involving multiple Native entities

Legislation and NAGPRA use the plural equivalent:

    cedar_uids
    canonical_names
    entity_classes
    entity_roles
    entity_names_as_published

These are aligned lists, serialized as JSON arrays in CSV. Each position represents the same entity-role association across all five columns. A named but unresolved party retains its name-as-published and a null UID.

Do not independently sort these lists, choose the first tribe arbitrarily, or place several IDs inside singular cedar_uid.

The viewer should display readable names and roles and search every resolved Cedar UID. Users unpacking these associations for analysis must retain distinct bill/document IDs so the expansion does not inflate event counts or duplicate amounts.

Populate source names from the actual relationship evidence. A registry name is not proof of what the source called an entity. Preserve unresolved counts where reconstruction is incomplete.

### Public notes and technical material

Every dataset ends with research_note, but it is not a dumping ground for removed columns.

Use it only for a concise factual qualification that changes interpretation, such as an uncertain closing date, an amount covering an entire joint venture, or a geography that cannot be assigned precisely. Leave it blank when unnecessary.

Script names, local paths, parser diagnostics, agent commentary, matching-token explanations, proposed redirects, build logs, and internal review instructions stay internal.

Apply publication and identity restrictions before removing their implementation fields. Removing a warning column does not make a questionable value safe to publish.

Preserve identifiers as text, including leading zeros. Missing amounts stay missing. Dates retain their actual precision. Do not drop a field merely because it is empty in a sample.

## Column counts

These compare the inspected source headers with the recommended public headers. They include newly standardized identity fields and substantive controls.

| Dataset | Inspected columns | Public columns |
|---|---:|---:|
| Federal Funding | 63 | 40 |
| Federal Register and Agency Actions | 39 | 31 |
| Legislation | 37 | 29 |
| Indian Country Deals | 40 | 33 |
| NAGPRA | 69 | 52 |
| Advocacy and Government Engagement | 43 | 38 |
| Federal Prime Contracting | 72 | 49 |
| Federal Subcontracting | 78 | 54 |
| Natural Resources | 45 | 38 |
| Individually Owned Native Businesses | 53* | 32 |
| NEST | 65 | 30 |
| Native Nonprofits | 67 | 24 |

*The 53-column Native-Owned Businesses baseline is the builder's column declaration, not a verified public export. Its publication restrictions still apply.

NAGPRA and Subcontracting remain wider because their relationship, measurement, and analytical-control fields are substantively important. Do not force every dataset to have the same number of columns.

## 1. Federal Funding: 40 columns

Preserve assistance-transaction rows. Do not aggregate to award-year in this column-only change.

Exact order, left to right:

    cedar_uid, canonical_name, entity_class, cedar_entity_role, transaction_id, award_id
    fain, action_date, fiscal_year, fy_partial_flag, recipient_name, recipient_uei
    recipient_duns, recipient_type, assistance_type_code, assistance_type, program_code, program_name
    awarding_agency, awarding_subagency, obligations_usd, obligations_usd_real2025, loan_face_value_usd, loan_subsidy_cost_usd
    total_loan_face_value_usd, total_loan_subsidy_cost_usd, recipient_city, recipient_state, recipient_county, recipient_county_fips
    performance_county, performance_county_fips, recipient_geography_status, performance_geography_status, attributed_flag, attribution_status
    source_system, source_vintage, source_url, research_note

Default viewer:
canonical_name, action_date, fiscal_year, recipient_name, program_name,
obligations_usd, attribution_status, source_url.

Consolidate the overlapping recipient-type descriptions into one readable
recipient_type using the source-code dictionary and conflict checks.

Keep attributed_flag, attribution_status, and fy_partial_flag. They affect
which amounts can be interpreted or counted, so they are not developer clutter.

Keep DUNS for historical joins and all four distinct loan measures. Do not
combine incremental and cumulative loan fields.

Retain recipient and performance county identifiers separately. Translate
geographic ambiguity into the two geography-status fields before removing
the detailed matching diagnostics.

Move attribution-rule transcripts, source-line references, repeated deflator
parameters, archive plumbing, and build timestamps out of the public table.

## 2. Federal Register and Agency Actions: 31 columns

Preserve the current event-participant/document row structure and its counting controls.

Exact order, left to right:

    cedar_uid, canonical_name, entity_class, cedar_entity_role, consultation_event_id, fr_document_number
    agency, subagency, program, activity_type, topic, document_role
    notice_date, event_start_date, event_end_date, event_date_precision, participant_name, participant_role
    location, event_format, comment_deadline, has_written_comments, has_summary, has_transcript
    is_event_primary_row, participant_rows_per_event, federal_register_citation, source_system, source_url, source_quote
    research_note

Default viewer:
canonical_name, notice_date, topic, agency, document_role, event_start_date,
participant_name, source_url.

Keep document_role, is_event_primary_row, and participant_rows_per_event.
The consultation ID is not necessarily a unique row key.

Do not merge publication dates, meeting dates, and comment deadlines.
A scheduled opportunity is not evidence of attendance.

Preserve useful source quotations and public evidence about participation.
Translate date/location qualifications into the appropriate public fields
and research_note before removing their internal explanations.

Remove build timestamps, extraction notes, internal overlap checks, and
matching machinery from the customer columns.

## 3. Legislation: 29 columns

Preserve the current bill-based public view. Do not create additional rows
for every action, cosponsor, vote, or entity association during this pass.

Exact order, left to right:

    cedar_uids, canonical_names, entity_classes, entity_roles, entity_names_as_published, bill_id
    congress, chamber, bill_type, bill_number, title, policy_area
    bill_scope, affected_entity_classes, affected_entities_as_published, introduced_date, sponsor_name, sponsor_bioguide_id
    cosponsor_count, latest_action, latest_action_date, outcome, companion_bill_id, rollcall_count
    resolved_entity_count, entity_link_statuses, source_system, source_url, research_note

Default viewer:
canonical_names, bill_id, title, congress, introduced_date, sponsor_name,
outcome, source_url.

Use the plural identity fields because a bill may concern multiple entities.
Keep class-wide legislative scope separate from the actual registry classes
of named entities.

Keep sponsorship, latest action, outcome, companion bill, and roll-call
information. Remove has_rollcall only after proving its information is
preserved by rollcall_count and the documented coverage rules.
A zero observed roll-call count must not imply complete vote coverage when
coverage is incomplete.

Remove classification agreement statistics, build flags, duplicate entity
counts, and internal classification narratives. Retain unresolved names and
meaningful limitations.

Write the official bill URL into the export rather than relying on the
website to construct it.

## 4. Indian Country Deals: 33 columns

Preserve the existing deal/event population. This is not a deduplication pass.

Exact order, left to right:

    cedar_uid, canonical_name, entity_class, cedar_entity_role, deal_id, event_date
    event_date_precision, event_date_not_before, event_date_not_after, event_year, title, native_party_name
    native_party_type, native_party_role, counterparty_or_funder, deal_type, transaction_structure, industry
    sector, capital_source, deal_status, announced_value_usd, value_basis, project_total_value_usd
    state, location, description, native_connection, verification_status, source_url
    source_type, additional_sources, research_note

Default viewer:
canonical_name, event_date, title, deal_type, deal_status,
announced_value_usd, value_basis, source_url.

Normalize mixed-case headers. Consolidate overlapping category fields into
deal_type and transaction_structure through a documented value-level
crosswalk, not by keeping whichever value is nonblank.

Keep industry and broader sector when they convey different information.

Retain native_party_role separately from cedar_entity_role. A subsidiary's
role as buyer is different from the canonical Native entity's role as owner.

Keep both date bounds. A precision label alone does not preserve an uncertain
date interval. Month and quarter do not need separate public columns when
they can be derived accurately.

Keep whole-project value separate from announced transaction value.

additional_sources is a list of additional public source objects containing
URL and source type. It replaces the fixed Source_2/Source_2_Type pattern
without limiting a deal to two sources.

Convert substantive Notes into concise research_note text. Do not discard
closing-date disclaimers, uncertain status, or ownership-share limitations.

## 5. NAGPRA: 52 columns

Preserve the current notice/document population and correction handling.
Do not aggregate counts during column cleanup.

Exact order, left to right:

    cedar_uids, canonical_names, entity_classes, entity_roles, entity_names_as_published, document_number
    publication_date, publication_year, notice_type, process_stage, is_correction, title
    institution_name, additional_institution_names, institution_city, institution_state, institution_type, institution_split_flag
    responsible_party_statement, agency_names, object_categories, individuals_stated, individuals_statement, associated_funerary_objects_stated
    unassociated_funerary_objects_stated, sacred_objects_stated, cultural_patrimony_objects_stated, cultural_items_total_stated, removal_counties, removal_states
    removal_location, repatriation_eligible_date, response_deadline_date, lineal_descendant_determination, culturally_unidentifiable, n_consulted_named
    n_consulted_resolved, n_affiliated_named, n_affiliated_resolved, n_disposition_priority_named, n_disposition_priority_resolved, n_repatriation_recipient_named
    n_repatriation_recipient_resolved, n_letter_of_support_named, n_letter_of_support_resolved, n_aboriginal_land_named, n_aboriginal_land_resolved, n_parties_named
    n_entities_resolved, source_url, pdf_url, research_note

Default viewer:
canonical_names, publication_date, notice_type, institution_name,
process_stage, individuals_stated, source_url.

Retain all six named/resolved count pairs and both overall counts.
They distinguish unresolved entity links from absence of a named relationship.

Consolidate the six role-specific ID lists into the aligned identity arrays
only after verifying that every association and role survives.
Consulted, affiliated, recipient, disposition-priority, letter-of-support,
and aboriginal-land relationships remain distinct. Do not flatten them into
an undifferentiated list of tribes.

Keep counts of individuals, funerary objects, sacred objects, cultural
patrimony, and stated cultural-item totals separate. Do not add them into
one generic count.

Retain measurement statements when they explain how to interpret a number.
An eligibility date is not a confirmed transfer date.

Institution geography applies to the designated institution, not
automatically to every additional institution.

Remove parser templates, span counts, artifact timestamps, duplicate URL
representations, and extraction bookkeeping. Apply existing restrictions
to sensitive location or identifying information before export.

## 6. Advocacy and Government Engagement: 38 columns

Preserve existing filing/activity records. Accommodate non-LDA sources in
the same schema without claiming those sources have already been collected.

Exact order, left to right:

    cedar_uid, canonical_name, entity_class, cedar_entity_role, activity_id, activity_type
    source_record_id, reporting_year, reporting_period, activity_date, activity_title, client_name
    client_id, client_state, registrant_name, registrant_id, registrant_state, self_filed
    participant_name, participant_role, government_bodies, issue_codes, issues_text, affiliated_organizations
    income_usd, expenses_usd, reported_amount_usd, amount_basis, termination_date, supersession_status
    is_superseded, superseded_by_record_id, supersession_group_id, attribution_withdrawn, attribution_withdrawn_reason, source_system
    source_url, research_note

Default viewer:
canonical_name, activity_type, reporting_year, client_name, registrant_name,
activity_title, reported_amount_usd, source_url.

This schema accommodates filings, documented consultations, testimony,
comments, calendars, ex parte activity, and relevant nonprofit reporting.
Only actual sourced records may populate those activity types.

Use stable source-based activity IDs. A filing UUID remains available in
source_record_id.

Keep income, expenses, and the selected reported amount with its basis.
They are not three additive measures. Non-monetary activity has a null amount.

Retain supersession and attribution-withdrawal controls. A valid underlying
filing can remain in the dataset even when its Native association is withdrawn.

Document the meaning of activity_date by source type. A filing's posting date
is not the day lobbying occurred.

Remove duplicate Cedar IDs, matched aliases, pull keywords, redundant URLs,
and internal exclusion diagnostics after their effects have been applied.

## 7. Federal Prime Contracting: 49 columns

Preserve transaction/modification rows. Do not aggregate to award-year or
collapse genuine modifications.

Exact order, left to right:

    cedar_uid, canonical_name, entity_class, cedar_entity_role, transaction_id, award_id
    contract_number, parent_contract_number, action_date, fiscal_year, awardee_name, awardee_uei
    cage_code, parent_name, parent_uei, funding_agency, award_type, description
    naics_code, naics_description, psc_code, psc_description, sector, obligations_usd
    obligations_usd_real2025, cumulative_award_value_usd, set_aside_reported, set_aside_classification, reported_8a, reported_buy_indian
    reported_indian_business, reported_native_preference, competition_type, recipient_city, recipient_state, recipient_county
    recipient_county_fips, performance_city, performance_state, performance_county, performance_county_fips, recipient_geography_status
    performance_geography_status, attributed_flag, owner_attribution_status, owner_as_of_transaction_cedar_uid, source_system, source_url
    research_note

Default viewer:
canonical_name, action_date, awardee_name, funding_agency, description,
obligations_usd, owner_attribution_status, source_url.

Keep transaction and award identifiers, CAGE/UEI, parent identifiers, actual
awardee name, and transaction-date ownership attribution.

Keep all four reported preference flags. Reported set-aside and Cedar's
classification remain separate unless full-data validation establishes
that a single field preserves both meanings.

Verify that the producer's total_obligations is an incremental transaction
measure before renaming it obligations_usd. A column name is not proof.

Clearly label cumulative award value. It must not be summed across
transaction rows.

Consolidate raw/normalized competition labels using a validated dictionary.

Move repeated cumulative-value deflation, ruling diagnostics, build fields,
and geographic matching calculations internally.

Preserve public geography-status information before removing uncertainty
diagnostics.

## 8. Federal Subcontracting: 54 columns

Preserve reported subaward/version rows and their existing controls.
Do not collapse revisions during this column pass.

Exact order, left to right:

    cedar_uid, canonical_name, entity_class, cedar_entity_role, subaward_record_id, subaward_number
    report_id, subaward_date, fiscal_year, report_year, award_kind, subaward_type
    description, subcontractor_name, subcontractor_uei, subcontractor_cage, subcontractor_parent_name, subcontractor_parent_uei
    subcontractor_parent_cage, sub_cedar_uid, prime_name, prime_uei, prime_cage, prime_parent_name
    prime_parent_uei, prime_parent_cage, prime_cedar_uid, native_direction, prime_award_id, prime_award_unique_key
    subaward_amount_usd, subaward_amount_usd_real2025, prime_award_amount_usd, subaward_to_prime_ratio, awarding_agency, awarding_subagency
    prime_set_aside, naics_code, naics_description, psc_code, psc_description, subcontractor_business_types
    subcontractor_city, subcontractor_state, subcontractor_county, subcontractor_county_fips, subcontractor_country, subcontractor_geography_status
    duplicate_status, subaward_exceeds_prime_flag, action_date_precedes_ffata_flag, source_system, source_url, research_note

Default viewer:
canonical_name, subaward_date, subcontractor_name, prime_name,
native_direction, subaward_amount_usd, duplicate_status, source_url.

Keep prime and subcontractor Native links and all four CAGE fields.
A Native prime does not make its subcontractor Native.

Keep duplicate_status, subaward_exceeds_prime_flag, and
action_date_precedes_ffata_flag. These are analytical controls.

Keep the subaward-to-prime ratio only with its validated amount, period,
and version definitions. Do not recompute it from incompatible snapshots.

Use the subcontractor's own geography. Do not fill a missing subcontractor
county with the prime recipient's or prime performance county.

Remove internal identifier-basis fields, promotion timestamps, repeated
deflator parameters, and unrelated prime-geography enrichments.

## 9. Natural Resources: 38 columns

Preserve each existing event/period and its stated measurement level.

Exact order, left to right:

    cedar_uid, canonical_name, entity_class, cedar_entity_role, resource_revenue_event_id, source_record_id
    recipient_name, beneficiary_entity_id, beneficiary_name, payer_entity_id, payer_name, operator_entity_id
    operator_name, related_asset_ids, revenue_type, resource_type, commodity, product
    mineral_lease_type, period_type, period_start, period_end, payment_date, amount_usd
    amount_usd_real2025, measurement_status, aggregation_level, amount_sign_meaning, land_status, allocation_formula
    allocation_formula_effective_start, allocation_formula_effective_end, allocation_formula_source_url, geography_note, attribution_status, source_system
    source_url, research_note

Default viewer:
canonical_name, payment_date, resource_type, revenue_type, recipient_name,
amount_usd, aggregation_level, source_url.

Keep payer, recipient, beneficiary, and operator distinct. Their identifiers
retain their declared namespace; only verified Cedar identifiers are used
as Native entity join keys.

Keep measurement_status, aggregation_level, amount_sign_meaning, and
attribution_status. An aggregate Indian Country amount must not appear to
belong to one tribe.

Keep commodity versus product, allocation formulas and effective dates,
and related_asset_ids even where sparse.

Preserve the actual meaning of payment_date. An announcement must not be
presented as confirmed cash receipt.

Remove repeated deflator parameters, build timestamps, and attribution
implementation notes. Retain factual beneficiary and geography qualifications.

## 10. Individually Owned Native Businesses: 32 columns

Preserve the existing business-directory/certification listing unit.
Do not merge distinct certifications into a new business snapshot.

Exact order, left to right:

    cedar_uid, canonical_name, entity_class, cedar_entity_role, business_source_id, business_name
    business_entity_id, certifying_authority_entity_id, certifying_authority_name, program_name, directory_type, assertion_class
    identity_scope, identity_claim_text, ownership_percent, ownership_threshold_min, certification_number, certification_tier
    certification_start, certification_expiration, business_license_number, service_category, naics_code, city
    state, source_edition, source_last_updated, first_seen, last_seen, is_current
    source_url, research_note

Default viewer:
canonical_name, business_name, certifying_authority_name, assertion_class,
service_category, city, state, source_url.

Keep the authority's substantive ownership or relationship claim,
assertion_class, identity_scope, ownership threshold, and certification terms.
A vendor listing is not automatically evidence of Native ownership.
Different authorities' certifications are not automatically equivalent.

Keep the business distinct from its certifying authority. Do not fill a
missing business identity with the certifying nation's UID. Authority links
remain separately searchable.

The inspected baseline is the builder declaration, not publication approval.
Apply existing permissions and field-level restrictions before producing
any preview, download, search index, or Cedar answer.

Do not add private owner names, contact information, restricted website/DBA
fields, raw snapshots, OCR diagnostics, or suppression machinery to the
public schema.

## 11. NEST: 30 columns

Preserve the enterprise/relationship unit declared by the current producer.

Exact order, left to right:

    cedar_uid, canonical_name, entity_class, cedar_entity_role, enterprise_id, enterprise_name
    alternative_names, parent_enterprise_id, parent_name, relationship_type, relationship_as_recorded, ownership_percent
    sector, operating_status, city, state, uei, cage_code
    in_federal_contracting, first_observed_year, last_observed_year, source_count, relationship_evidence_status, reported_federal_parent_name
    federal_parent_corroboration, source_document, source_edition_date, source_url, additional_source_urls, research_note

Default viewer:
canonical_name, enterprise_name, parent_name, relationship_type,
ownership_percent, sector, operating_status, source_url.

The Cedar block identifies the associated Native owner or affiliate.
enterprise_id and enterprise_name identify the actual business.

Keep the immediate parent, stated ownership percentage, original relationship
description, evidence status, and federal-parent corroboration or disagreement.

Observation years are not incorporation dates or ownership effective dates.

Remove duplicate owner-hub identity aliases after equality checks.
Remove normalized-name plumbing, proposed UEIs, constellation diagnostics,
and matcher notes. Do not replace verified identifiers with candidates.

A non-equivalent enterprise_existing_cedar_uid or other distinct approved
identifier must be accounted for before retirement. Stop rather than delete
an identity merely to meet the target column count.

## 12. Native Nonprofits: 24 columns

Preserve the current organization snapshot unit. Do not silently convert
the dataset into an organization-year panel.

Exact order, left to right:

    cedar_uid, canonical_name, entity_class, cedar_entity_role, ein, organization_name
    organization_entity_class, inclusion_category, city, state, ntee_code, irs_status
    irs_subsection, irs_foundation_code, irs_ruling_month, tax_period, bmf_revenue_usd, bmf_assets_usd
    bmf_income_usd, bmf_as_of_date, entity_link_status, source_system, source_url, research_note

Default viewer:
canonical_name, organization_name, ein, inclusion_category, state,
tax_period, bmf_revenue_usd, source_url.

Keep EIN, the actual organization name and class, and the relationship to
the canonical Native entity.

Native-serving, Native-controlled, and tribal-government organizations are
not interchangeable categories.

Keep BMF revenue, assets, and income under their actual source definitions.
Do not relabel bmf_income_amt as profit or net income without verification.

Keep tax_period separate from the BMF snapshot date. Do not combine a newer
return's finances with an older BMF record as though they describe the same
reporting period.

Consolidate substantive classification and linkage outcomes into
inclusion_category, entity_link_status, and a factual research_note.

Remove token comparisons, coder agreement counts, redirect proposals,
funnel stages, internal review narratives, and duplicate Cedar identifiers.

## Required validation before release

For every dataset:

1. Prove that column cleanup has not changed row count, record multiplicity,
   event identity, existing financial totals, or the applicable publication
   and attribution rules.
2. Verify simple renames value-for-value. Validate combined fields across
   the complete dataset, not only the preview rows. Conflicting categories,
   statuses, identities, or source definitions must not be silently coalesced.
3. Account for substantive fields introduced by supporting sources.
   A source-specific analytical field cannot be discarded merely because
   it was absent from the flagship sample inspected here.
4. Keep restricted information out of names, notes, source lists, expanded
   records, search indexes, and downloads. Retiring permission columns does
   not retire the permission checks.
5. Generate the customer export, sample, data dictionary, and viewer from
   the same approved public schema. Keep the smaller default viewer
   selection without creating a second competing customer dataset.
6. Document the row unit, identifiers, dates, source coverage, null meanings,
   classifications, and non-additive measures. Put citation and release
   metadata outside the analytical rows.

Deliver 12 public datasets with intentional headers, not 12 narrow-looking
views sitting on top of unchanged, cluttered downloads.

## NON-NEGOTIABLE: RETIRE ALL LEGACY, VENDOR, AND COMPETING ENTITY IDs

cedar_uid is Cedar's canonical cross-dataset identity system. The final Cedar Press datasets must not carry parallel entity-identification systems simply because they exist in source files, older exports, historical code, or upstream databases.

Actively search the entire dataset pipeline for competing IDs, including column names, values, crosswalks, supporting tables, schemas, samples, documentation, code, and historical outputs. This includes CICD/NEID, Casino City IDs, DUNS, vendor IDs, old Cedar identifiers, resolver IDs, candidate IDs, source-registry entity IDs, and other fields being used to identify the same entity that Cedar UID is intended to identify.

For every such identifier found:

1. Determine what object it identifies. Do not delete blindly. Establish whether it identifies the canonical Native entity, a business/enterprise, an award, filing, notice, bill, casino, source record, or some other object.
2. If it identifies the canonical Native entity, resolve it to the correct cedar_uid. Validate the crosswalk rather than assuming equivalence. Once the Cedar UID is populated and validated, remove the competing ID from the public dataset.
3. If it identifies a different legitimate research object, do not replace it with Cedar UID. Give that object an appropriate stable identifier or retain an approved public identifier. For example, an enterprise needs an enterprise_id; a deal needs a deal_id; a filing can retain its filing UUID; an award can retain its official award ID.
4. If it exists only for matching, reconciliation, provenance, or historical pipeline purposes, move it to the internal identity/crosswalk layer and delete it from the customer dataset.
5. If its purpose cannot be determined, stop and flag it for adjudication. Do not retain an unexplained ID "just in case," and do not delete it until its role has been accounted for.

Older files are not authoritative schemas. The appearance of CICD, NEID, Casino City, DUNS, or another retired identifier in an older dataset is evidence that migration may still be required, not evidence that the field should be restored.

Do not allow a later import, rebuild, schema inference, source refresh, or agent to reintroduce a retired identifier. Add regression tests that fail if prohibited IDs return to public schemas.

After migration, produce an identifier retirement report containing:

dataset | old_identifier | what_it_identified | cedar_uid_or_replacement | disposition | rows_affected | unresolved_count

Every retired identifier must therefore be accounted for before deletion.

The desired end state is not merely that these columns are hidden. It is that Cedar's identity architecture has absorbed everything useful they contributed, and the redundant identifier has been removed from the customer-facing dataset and prevented from returning.

DUNS: use it internally to reconcile historical federal records to the correct entity/UEI/Cedar UID where necessary. Once that information has been absorbed into the current identity mapping, do not publish DUNS merely because historical source files contain it.

Casino City IDs: first make sure every useful casino/entity relationship that depends on the Casino City identifier has been migrated into Cedar's own entity/object relationships. Then retire the Casino City ID from the public dataset. Do not lose the relationship just to eliminate the identifier.

CICD/NEID: these are retired identity systems. Find every remaining dependency, translate validated entity references to Cedar UID, resolve or flag anything that cannot be translated, then remove the old identifier and prevent its reintroduction.

The rule: migrate → reconcile → verify → retire → regression-test, not simply "drop these columns."
