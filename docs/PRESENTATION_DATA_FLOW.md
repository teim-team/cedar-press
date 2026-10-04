# Press and Grove presentation data flow

Cedar Press and Cedar Grove consume the same verified releases from Lumecon-data.
The producer owns acquisition, identities, transforms, full-population validation,
publication policy and the source codebook. Press owns the shared release consumer;
Grove calls that consumer through its pinned process protocol.

## Two preview populations

Public Press previews read the committed, publication-eligible sample files.
Their captions count those sample records. The snapshot's update date describes
the preview. A sample is not a current full-dataset count, and counts across
supporting tables or collections are not an unduplicated entity or event total.
No collection carries a publication hold (owner ruling 2026-10-04), so no preview is removed for one.

Signed-in examples use the release research API. The record count shown beside a
spreadsheet comes from its verified release metadata and must match the permitted
record types for the same release. Unavailable or held groups do not become
available because an older manifest records a count. Mixed record types retain
their grains and money meanings; a row count is never permission to add amounts.

The public samples stay public only under their existing publication eligibility.
Review-only material does not become a public sample when a local count changes.

## Maintained entry points

| Responsibility | Authority or entry point |
| --- | --- |
| Public descriptor and sample import | scripts/import_cedar_manifest.py |
| Sample publication availability | scripts/measure-samples.mjs; measures committed bytes against the Git index |
| Public sample display contracts | scripts/derive-explore.mjs; reads sample headers plus reviewed explore.overrides.json |
| Connected catalog and release checks | server/cedar_press/repository.py |
| Connected preview rows and source definitions | server/cedar_press/release_research.py |
| One verified spreadsheet per collection | server/cedar_press/spreadsheet.py |
| Shared reader-facing field and record labels | src/features/grove/readerPresentation.js |
| Public table column layout | src/features/grove/recordColumns.js |
| Connected display order and count checks | src/features/grove/releaseResearch.js |
| Generated codebook documentation | scripts/docs-markdown.mjs --kind codebook |
| Cross-language duplication measurement | scripts/measure_duplication.py |
| Generated-file validation | make check-generated |
| Structural audit of served previews, descriptors and spine (read-only; also a firing test) | server/tests/test_public_preview_audit.py --report; findings recorded in docs/FACT_CHECK_2026-10-02.md |
| Consumer-side release-gap register (what exists but is not served, per gate) | server/tests/release_gap_register.py --write; held current by test_release_gap_register.py; docs/RELEASE_GAP_2026-10-02.md |
| Reference graph for the numbered workspace scripts and the archive rule | server/tests/code_reference_graph.py --write; docs/CODE_REFERENCE_GRAPH_2026-10-02.json; code/archive/INDEX.md |
| Per-UEI recipient holds and rebinds (policy input, not a denial; nothing applies it yet) | code/cedar_publication.recipient_holds(); data/cedar/recipient_holds.json; docs/RECIPIENT_HOLDS_2026-10-02.md |
| Legacy 40-column Deals preview to the 36-column producer header | server/tests/legacy_deals_adapter.py (tested mapping; changes nothing served) |
| Collection display names (owned is Individual Native-Owned Businesses) | server/tests/test_collection_display_names.py |

The sample publication check and display-contract generator serve different
contracts; neither is a substitute for the other. JS/Python parity checks remain
necessary where both runtimes implement the same product rule. Use the existing
duplication measurement before proposing a shared-module extraction.

Retired CICD, NEID and readable-handle identifiers are excluded from selectable
preview columns. Cedar entity IDs, names, original source record IDs and source
citations remain. Canonical data cleanup and export schemas remain the producer's
responsibility. This display rule does not rewrite historical evidence or infer
identity bindings.

## Validation and review

Run the focused reader presentation, connected preview, collection and spreadsheet
tests, then the repository's normal lint, generated-file, unit and browser checks.
Render the public door and the collection profile on desktop and mobile after a
presentation change. Existing automated deployment checks remain enabled.

Havala reviews the source, grain, count and publication boundary. Laurel's export
review should inspect the actual spreadsheet and its public codebook: names and
units, key columns, missing values, original source attribution, distinct record
types and the exact population represented. Reuse the producer's generated
codebook rather than writing a second set of definitions in Press.

Historical logs and handoffs are evidence of their dated state. This page owns
the current presentation boundary; link here instead of copying a second current
count or rerun recipe into another handoff.
