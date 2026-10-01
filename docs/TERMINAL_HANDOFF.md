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
