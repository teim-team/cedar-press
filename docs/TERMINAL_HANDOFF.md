# Consumer continuation

*Rewritten in place, never appended to.*

Business register state: `live: false` is the current consumer state. Change
`live: false` → `true` only after an approved register is imported and its product integration is verified.
An external issued-ID package does not establish consumer liveness; see the
[consumer identity state](../src/features/grove/pressIdentity.js).

## Current workflow

Database follow-ups from the 2026-10-06 landing-page work (a larger NEED
release, an accurate Native Nonprofits count, the other populations once held)
are under "Open follow-ups" below, and the open items of the 2026-10-02
fact-check under "Open items from the 2026-10-02 fact-check".

The dated [producer convergence checkpoint](https://github.com/teim-team/Lumecon-data/blob/bdb630841bc344872d79a444eadebcde61b21bb7/docs/cedar-convergence.md)
retains the September 30 history, and the dated
[review status of 2026-10-02](https://github.com/teim-team/cedar-press/blob/data-workspace-final/docs/REVIEW_STATUS.md),
at the tag `data-workspace-final`, the October 1 and 2 checkpoints. Recheck the
current PR and checkout before using a dated code SHA. Documentation branch links
are navigation, never runtime data pins.

Lumecon-data builds and verifies immutable releases and the cohesive researcher
spreadsheet. Cedar Press owns the shared Press/Grove consumer, publication filters,
entitlement checks and presentation. The installed producer spreadsheet command
takes explicit store, collection and release pins; the authenticated Press API
uses the same pinned download verifier. [README.md](../README.md#living-datasets-and-the-researcher-spreadsheet)
describes the consumer boundary.

Static public previews remain approved samples. Their tracked bytes and measured
sample counts are maintained by the existing preview/import and measurement
scripts. Connected counts come from the API's permitted exact-release spreadsheet
descriptor. Source record counts, review counts and public sample counts are
different measures. The [presentation data-flow guide](PRESENTATION_DATA_FLOW.md)
identifies each existing script's role.

`Makefile` remains the local and hosted check authority. Use its generated-file,
frontend, backend and dependency gates, plus the maintained smoke checks, after
changes. See [AGENTS.md](../AGENTS.md) section 3 and [server/README.md](../server/README.md).
Current workflow configuration determines the tested producer revision; historical
handoff pins below do not override it.

## Open follow-ups from the 2026-10-06 landing-page work

Carried from docs/handoffs/CODEX_LANDING_FOLLOWUPS_2026-10-06.md when that file was
removed on 2026-10-12; the file, with the evidence for each item, is at the tag
`data-workspace-final`.

For the producer (Lumecon-data):

- **NEED, a larger reviewed set.** Re-measure NEED's servable rows under the
  2026-10-04 ruling, build the release from that population, and carry each row's
  top-level Native entity (Cedar ID, name and class) from the enterprise register's
  owner-hub binding, never from the name. Ask the owner what "agencies" means before
  choosing example rows for it.
- **Native Nonprofits, an accurate count.** Re-measure under the no-holds ruling,
  decide with the owner which population is published, and make the descriptor's
  method text agree with it.
- **The populations once held.** Confirm under the 2026-10-04 ruling whether the rows
  once held in Giving, PLOT, Prime Contracting, Federal Funding, Subcontracting,
  Individual Native-Owned Businesses, Natural Resources, Deals and Legislation now
  publish, and re-pin.
- **PLOT's expansion.** The owner set it as "Parcel-Level Ownership and Transfers"
  (2026-10-06); the producer's description and glossary still say otherwise.
- **Three example bindings an audit of 2026-10-06 found wrong** (no primary source
  could be read then): legislation `100-hr-2642` is bound to the Ute Indian Tribe of
  the Uintah and Ouray Reservation where the Southern Ute and Ute Mountain Ute tribes
  are likely meant; NAGPRA `00-11378` is bound to a BIE school and the Fallon tribe
  where the Duckwater Shoshone and Lone Pine Paiute-Shoshone tribes are likely meant;
  Giving `FF-03B9C4E5A6CA00E15034` is rightly left unlinked until its source page is
  read.

In this repository, once those fixes land:

- Delete the display workarounds: `EXCLUDED_EXAMPLES`, `SHOWCASE_RULES`,
  `DISPLAY_DEFAULTS` and `COLUMN_FALLBACKS` in `src/features/grove/showcase.js`;
  `with_native_owner` in `server/cedar_press/collections.py`; `repairMojibake` in
  `src/features/grove/readerPresentation.js`; `ACRONYM_LEADS` in
  `src/features/grove/collection.js` and `server/cedar_press/collections.py`.
- `src/features/grove/showcase.test.js` fails on purpose when a re-pinned release
  fixes a binding: delete its entry there and the exclusion in
  `src/features/grove/showcase.js` together.

## Open items from the 2026-10-02 fact-check

Carried from docs/REVIEW_STATUS.md when that file was removed; its last version is
in git history, and the fact-check (docs/FACT_CHECK_2026-10-02.md) is at the tag
`data-workspace-final`.

For the producer (Lumecon-data):

- **Deals `ANCSA-2014-001`.** Its `research_note` still describes a mid-month
  placeholder day while `event_date` is `2014-05` at month precision (low).
- **Giving `FG-*` rows.** `currency` is blank on the five `reviewed_disclosures`
  rows that carry `amount_exact_usd`, and `publication_status` is blank where `FF-*`
  rows read `observed`; the component's contract settles it.
- **The Siletz recipient repair.** Siletz Tribal Arts and Heritage Society is a
  separate nonprofit, but two Federal Funding transactions (recipient UEI
  `GJV4PJ8M5PC7`, award `ASST_NON_1896753-42-22_417`) project to the tribal
  government. Applying it needs the uid they carry now, read off the projection; a
  ruling that states the fact (a distinct recipient, not `not_native`); and the
  evidence re-read (the society's [board page](https://siletzartsheritagesociety.org/board-of-directors/)
  and the [USAspending award](https://www.usaspending.gov/award/ASST_NON_1896753-42-22_417)). No new
  Cedar ID unless the owner admits the society to the register.
- **The full spreadsheets were not re-measured** in that pass; only the 140 preview
  rows and the manifest were.

For the owner:

- **One name, two entities.** `CE-000RA-MT` and `CE-001R2-8V` share the canonical
  name National Center for American Indian Enterprise Development; the evidence and
  the next sources are in `data/spine/cedar_duplicate_name_review.json`.
- **The Deals served preview.** Whether the ten events reviewed on 2026-10-01 become
  the served sample (Havala).
- **Individually owned businesses, after the 2026-10-02 ruling.** Whether the TERO
  rosters' `owner_name_raw`, `dba_name` and business street address follow the
  ruling, and whether `owner_name`, `owner_tribal_affiliation_named` and
  `self_description_sentence` publish under it, were left for the owner to confirm.

Not defects, recorded so they are not re-investigated: negative `obligations_usd`
are de-obligations kept as recorded; the `$0.00` funding transaction
(`...12X1105_10.664_0003`) is a zero-dollar modification; `fiscal_year 2026` on a
2025-12-24 subaward is the federal fiscal year; `registrant_id 400635921` is a
post-2017 LDA registrant id; `reporting_year 1999` filed 2000-02-14 is a year-end
report; the contractor `award_id` duplicates are several transactions of one award
(the key is `transaction_id`); `owned.cedar_uid` equals the certifying tribe by
definition (`cedar_entity_role = certifying_authority`).

## Preserved evidence and older instructions

The [archived terminal checkpoints](handoffs/2026-10-01-terminal-history.md)
preserve the complete former handoff, including prior dates, measurements,
permissions and review-batch notes. They are historical observations, not live
writer assignments or a substitute for the current user instruction.
START_HERE.md, the former journal in AGENTS.md and the numbered builders
preserve workspace history at the tag `data-workspace-final`, for their
documented reproduction or adjudication role; do not use a historical build
chain as the current release/export entrypoint.

Retain existing owner decisions, stable IDs and source receipts. Engineering
fixes, schema repair, infrastructure and missing research stay with the coding
workflow; only fully researched, genuinely ambiguous subject linkages belong in
the owner's adjudication queue.

## 2026-10-04 Gaming columns follow the rights ruling

Lumecon-data #17 (`019ded3`, the Gaming consumer job's `LUMECON_DATA_SHA` when this was written)
applies the owner ruling of 2026-10-04 to Gaming releases: a field-rights class
is provenance, so a release ships every column of any class (projection rule
`gaming-presented-fields-v2`) except personal data and a few columns whose
content the identity contract or a fact check refuses. The consumer still
matches columns exactly: each changed Gaming declaration in
`data/cedar/gaming_component_contracts.json`, and the `gaming_government_payments`
field-map entry, now also lists the new column set in `compatible_orders`, so
the saved release (`order`) and a newer one both serve. The added columns are
in `fields` with their rights class, not in `display_order`.
`server/tests/test_gaming_release.py` checks both column sets against the
pinned producer.

## 2026-10-04 NEED integration

NEED has no publication hold (owner ruling 2026-10-04, Elijah Moreno), and the
consumer applies none: it presents NEED's `reviewed_public_base` (43 reviewed
rows, release `428d1104...`) like any other component. The Gaming consumer job
installed producer `363c13e` (Lumecon-data #17) when this was written; it carries the rights
ruling and the producer-side NEED fixes. Merge order, the pins each repository
expects, the commands that prove the chain and the open owner decisions (which
NEED table customers get, re-cutting the pre-ruling release) are in the
producer's [NEED integration checklist](https://github.com/teim-team/Lumecon-data/blob/363c13e21288421649829c5914f9826775f1e568/docs/need-integration-checklist.md).
Rows that look like they lost their linkage context are flagged there for the
identity audit, not changed.

## 2026-10-03 Infrastructure research acceptance

The real-release research rehearsal now derives Grove-only handling from
`repository.is_grove_release` for both Gaming and Infrastructure. It no longer
selects a Press product, tier or pin for Infrastructure.

The corrected real Infrastructure release aeaf2aa17b50ff1edd45222fe4c8469f2cdb0f5f5fad9824ec6b118cb410c09b
passed the isolated producer-metadata and shared-consumer rehearsal. Records has
28,484 permitted rows, 30 examples and 41 fields. The other 13 components were
refused under the holds in force on 2026-10-03, before the owner rulings of
2026-10-04, and the research packet was refused in production mode. Packet receipt SHA256:
b2743050ae728dd63e4b7a000fa7c35ee6f533f0347f0b9b83726a5c6cab1f2a.
This is review evidence, not deployment or new human approval. The packet currently
contains zero map features; map serving and consumer re-pins remain unfinished.

Producer 39a1ca7 adds the tested persistent review core. Its authenticated webpage,
runtime provisioning and actual human-review-to-publication acceptance remain
handoff work. Havala and Kaylyn are now explicit assignees on Press #132. Articles
remain paused. No customer login, account or production pointer changed here.
