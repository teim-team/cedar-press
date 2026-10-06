# Consumer continuation

*Rewritten in place, never appended to.*

Business register state: `live: false` is the current consumer state. Change
`live: false` → `true` only after an approved register is imported and its product integration is verified.
An external issued-ID package does not establish consumer liveness; see the
[consumer identity state](../src/features/grove/pressIdentity.js).

## Current workflow

The [current review status](REVIEW_STATUS.md) records the current cross-repository
checkpoints, measured review results and remaining integration work. The dated
[producer convergence checkpoint](https://github.com/teim-team/Lumecon-data/blob/bdb630841bc344872d79a444eadebcde61b21bb7/docs/cedar-convergence.md)
retains the September 30 history; later October 1 results in the current status supersede it. Recheck the current PR and checkout before using a
dated code SHA. Documentation branch links are navigation, never runtime data pins.

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

## Preserved evidence and older instructions

The [archived terminal checkpoints](handoffs/2026-10-01-terminal-history.md)
preserve the complete former handoff, including prior dates, measurements,
permissions and review-batch notes. They are historical observations, not live
writer assignments or a substitute for the current user instruction.
[START_HERE.md](../START_HERE.md) and the append-only part of AGENTS.md preserve
workspace history. The numbered builders remain available for their documented
reproduction or adjudication role; do not use a historical build chain as the
current release/export entrypoint.

Retain existing owner decisions, stable IDs and source receipts. Engineering
fixes, schema repair, infrastructure and missing research stay with the coding
workflow; only fully researched, genuinely ambiguous subject linkages belong in
the owner's adjudication queue.

## 2026-10-04 Gaming columns follow the rights ruling

Lumecon-data #17 (`019ded3`, now the Gaming consumer job's `LUMECON_DATA_SHA`)
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
refused according to existing holds, and the research packet was refused in
production mode. Packet receipt SHA256:
b2743050ae728dd63e4b7a000fa7c35ee6f533f0347f0b9b83726a5c6cab1f2a.
This is review evidence, not deployment or new human approval. The packet currently
contains zero map features; map serving and consumer re-pins remain unfinished.

Producer 39a1ca7 adds the tested persistent review core. Its authenticated webpage,
runtime provisioning and actual human-review-to-publication acceptance remain
handoff work. Havala and Kaylyn are now explicit assignees on Press #132. Articles
remain paused. No customer login, account or production pointer changed here.
