# Collective scope: the owner's decision, 2026-09-05

The proposal of 2026-09-05 (a reviewer's draft, not the owner's) suggested minting "All federally recognized tribes" and similar populations as entities in the identity register. The owner rejected that architectural centre and approved the feature on different terms. The decision is recorded here verbatim; `data/cedar/scopes.json` is its vocabulary, and the implementation notes follow it.

## Decision: implement collective scope without changing Cedar entity identity

> Approve collective-scope classification and filtering.
>
> Do not mint ordinary CE-XXXXX-CC Cedar UIDs for "all tribes," state subsets, all ANCs, all NHOs, or general Indian Country relevance. Do not add "Collective scope" as a Native entity class.
>
> Keep cedar_uid and cedar_uids exclusively for entities admitted under the existing canonical Native entity rules. An actual intertribal organization is different from an abstract population.
>
> Add collective_scopes to affected public schemas. Use an explicit scope definition, relationship to the record, source evidence, and temporal and geographic interpretation. Keep this information separate from named-party identity and resolution status.
>
> A record can contain both named entities and collective scopes. It can also have a valid collective scope and unresolved named parties. A scope must never be a fallback for a failed entity match.
>
> Distinguish addressed audience, applicability, eligible class, aggregate measurement, and general subject matter. Do not infer universal relevance from generic tribal language.
>
> Implement scope-aware filtering in the shared query model, not only the viewer. Individual-entity inclusion of collective records is optional and off by default. Explain the match and preserve the existing record grain.
>
> Resolve membership using the source's definition and relevant date. Missing historical or geographic evidence produces unknown membership, not a guessed inclusion or exclusion. Version the definitions and evidence; versioned membership caches are permitted.
>
> Never allocate collective amounts to individual members through a filter or join. Collective context may coexist with a genuinely identified recipient, but cannot replace that recipient.
>
> Reconcile the proposed federally recognized population against the official BIA list before displaying a national membership count. Do not force a match by deleting or reclassifying entities without evidence.
>
> Keep one public dataset per collection. This change does not authorize row expansion, new customer datasets, revival of retired identifiers, or reassignment of existing Cedar UIDs.

## The reasoning the owner gave, in brief

- `cedar_uid` identifies the canonical Native entity; a scope describes a population. Putting a population in the register with a valid-looking uid would make every consumer remember an exception: a distinct-uid count would count it, a join could treat it as a recipient, and a record with a scope would look entity-resolved when no individual entity was identified.
- A blank entity field is not inherently an error. The associated status explains it: no individual entity named, unresolved, or withheld. "Blank means unresolved, and only that" is rejected.
- "Addresses a class" needs a relationship: addressed, applies to, eligible class, aggregate measured population, general subject matter. A consultation notice does not address every tribe merely because it concerns consultation; an invitation is not participation; an eligible class is not receipt. The statutory population is not interchangeable with the recognized-tribe list (*Yellen v. Confederated Tribes of the Chehalis Reservation*: ANCs qualified as Indian tribes under the incorporated ISDA definition for CARES Act Title V), and a generic NHO label is not a program's definition.
- Membership cannot come from a generic state field or one universal date rule. Headquarters, trust land and service area are different predicates; an invitation, an ongoing program and a statute fix their populations at different dates. Missing evidence gives "unknown", never present membership as historical membership. "Computed, never stored" becomes: derived from a versioned definition and evidence, with versioned caches permitted.
- The viewer keeps named records distinct from broader relevance: inclusion of collective records for an entity is off by default, every added result says why it appeared, a record matching through a name and a scope appears once, and the scope, the toggle and the version enter the shared query state so the viewer, the saved view, the download and the Cedar request agree.
- Collective records can carry money: an appropriation for a class is a legitimate record whose amount belongs to the program, not to a synthetic recipient. A scope cannot occupy a recipient or owner identity field, and scope-based relevance cannot create entity-attributable dollars. A real recipient administering services for a broader population keeps its uid and carries the population as a scope.
- The national count in the proposal (577) was the register's class totals; the official list of 2026-01-30 states 575. That is reconciled at uid level on the terminal before any count is shown, never forced by reclassifying entities.

## What this repository does with it

- `data/cedar/scopes.json` holds the vocabulary: the scope codes and definitions, the five relationships, the as-of rules, the membership kinds, the element schema, and null versus `[]`.
- The field map declares `collective_scopes` on the affected datasets: Legislation, built at write time from the terminal's class-level scope columns (`bill_scope`, `entity_class_scope`) with the conservative relationship `general_subject`; the Federal Register, owed by the terminal together with an `entity_link_status` that distinguishes a record naming no individual entity from one whose named party is unresolved and from one withheld.
- The writer validates every supplied element against the vocabulary, refuses a scope code in an identity field, and never fills `cedar_uid` from a scope.
- The viewer's shared query model carries `scopes` and `broad`; the picker offers the scopes the loaded rows carry, individual-entity inclusion is a toggle that is off by default and works only for scopes whose membership is evaluable per entity from the register, every included row says why, and the reduced export carries `collective_scopes`.
- Owed on the terminal: the Federal Register's scope and link-status columns from the source text; the uid-level reconciliation against the BIA list; per-state and regional scopes when a source requires them.
