# Landing-page follow-ups that need the database (2026-10-06)

Written by the Claude session that built branch
`claude/lansing-cedar-press-updates-ed9643` (cedar-press). That session had the
repositories but **no access to the Lumecon-data review database, no network
to the source sites, and no Postgres**. Everything below is what it could not
do, measure or verify. Re-measure every count before acting on it: the numbers
here are copied from files as of this date, not from the database.

## What the branch already contains

- PR #132 (one flat customer table per collection), which already held #149
  (Deals) and the Giving, PLOT and Legislation consumer branches.
- PR #150 (owner ruling: no publication holds; SECURITY.md links), merged and
  reconciled against #132. See the merge commit message for the file-by-file
  resolution.
- Owner requests of 2026-10-06: early-access banner with `contact@lumecon.ai`;
  "observations" language and a hero total; every collection dated
  2026-10-06; no preview, sample, draft or demonstration wording for readers;
  the Collections table footer gap closed; the NEED count hidden (the
  Native Nonprofits count was hidden first, then shown again as 89 in
  `8bc330b`; see section 2); a hover card on the app's collection list; "How to read these records" keys
  for NEED and PLOT; NEED and PLOT spelled out wherever a paragraph describes
  them.

Every local gate passes: `npm run lint`, `make check-generated`,
`npm run test` (coverage gate), `ruff check server`, `make test-python` and
`npm run test:smoke`. **Not run:** `make audit-node` and `make audit-python`
(network), the `subscriber-storage` workflow (Postgres), the cross-repository
Lumecon-data job in `.github/workflows/ci.yml`, and the deploy.

## 0. External review of PR #155 (reviewed head 2f08aa3): what changed, what is open

Status: **not ready to call released.** The layout defects and the display
versus download mismatches are fixed on this branch; the three wrong
attribution bindings are still in the pinned data and need the producer.

Fixed on this branch:

- **Layout.** The rail and the frame now switch to one column together at
  900px. The frame is no longer shrunk with `transform: scale()`: labels are
  13px actual size and controls at least 40px at 1100 and 1440px. Phones show
  three examples and a "Show more examples" button. Deep-linked collections
  scroll into view in the phone rail. The source band has Pause and Play,
  pauses on hover, and is static under reduced motion. The rail hover card
  stays inside the viewport and closes on Escape. NEED cards read: enterprise,
  ultimate parent, relationship.
- **What a reader sees is what they download.** The showcase
  (`showcase.js`) now applies only to the landing frame. The collection
  viewer, record and entity pages show every downloaded record, deobligations,
  $0 actions and monthly subaward reports included (`viewerItems` in
  `useSamples.js`, tested record for record against all 14 downloads).
  Monthly subaward reports each carry their own `report_id`, so they are
  distinct observations; the first-row "dedup" was removed and only the
  landing order varies them. A showcase rule is never dropped to reach a
  minimum count.
- **NEED owners in the file.** The ultimate Native owner now travels in the
  NEED download itself (`native_owner`, `native_owner_cedar_uid`,
  `native_owner_basis`, `native_owner_source`), written by
  `server/cedar_press/collections.py` from `data/cedar/need_ownership_evidence.json`
  for the 10 released rows, each with a public first-party source. The five
  enterprises the browser used to add (CNI Advantage, Chickasaw Nation
  Industries, Choctaw Defense Manufacturing, Akima Global Services, Koniag
  Services) are **removed**: none is in the NEED release, and two had
  unsourced immediate parents. The current NEED release has **no tribe-owned
  example**; a released tribe-owned record exists in Prime Contracting
  (CNI Advantage, LLC, FPDS parent Chickasaw Nation, attribution confirmed).
  Publishing tribe-owned and NHO enterprises in NEED is producer work
  (section 1). Leads to check before any of those five is published: Akima
  Global Services may be jointly owned with The Aleut Corporation, and
  Koniag Services' immediate parent is probably Koniag Government Services.
- **Copy.** The Advocacy description now matches the release (LDA filings
  only) in all four copies, with the inventory baseline refreshed by
  `code/521_inventory.py` (only the `cedar_publication.py` entries kept).
  Mixed-grain observation total explained on the page. Each collection shows
  "Data as of" (its producer refresh, 2026-10-01 for all 14) separately from
  the page revision (2026-10-06). "Weekly" is worded as a schedule. Primary
  actions request early access by email instead of pointing at the general
  TBN membership page.
- **Sources figure.** "700+" was an owner-supplied total that no registry
  supports with a countable unit. The page now shows the measured
  `RELEASED_SOURCE_KINDS` = 47 (kinds of source named by the released
  collections; method in `sourceRotation.js`). Other measured figures: 174
  tribal business registry programs (75 live), 114 Lumecon-data intake
  entries, 154 discovery leads (not sources). **Owner decision:** restore a
  larger figure only with a registry and unit behind it.

**Owner, later on 2026-10-06: the landing page may show examples beyond the
current release, as long as they are clean.** The landing frame now reads
curated sets, one per collection, in `data/cedar/landing_examples/<id>.json`
(`src/features/grove/landingExamples.js`). Every row is copied from real
records already in this repository (the pinned downloads, the 100-row previews
in `dist/preview/`, test fixtures under `server/tests/fixtures/`, and Cedar's
ownership rulings in `code/55_stage_anc_subsidiary_rulings.py`), and each row
names its `_origin`. NEED's set leads with tribe-owned enterprises
(CNI Advantage, Choctaw Manufacturing Defense Contractors) and spans ASRC,
NANA, Koniag, Chugach, Calista, Ahtna, Tyonek and Ukpeaġvik Iñupiat, each
with its ultimate parent, UEI and CAGE. Only the landing frame reads these
sets: the viewer, record pages and downloads still read the release.
`landingExamples.test.js` checks every row against the download's columns,
for an origin, garbled text, positive amounts and the known wrong records.
Thin spots: PLOT has only three real records in the repository (two with a
blank cell); five Natural Resources rows come from the 100-row preview with
no source page; Individual Native-Owned Businesses has only the Tulalip TERO
registry rows with both a stated tribe and a source; Prime Contracting and
Subcontracting have six clean rows each. Re-drawn producer samples would
replace all of this.

Open, needs the producer or the owner:

- The three wrong bindings (section 8), with corrections recorded in
  `review/attribution_pending_items_2026-10-06.json`. They stay off the
  landing (`EXCLUDED_EXAMPLES`), and `showcase.test.js` fails on purpose once
  a re-pinned release fixes them. The primary sources (govinfo.gov,
  federalregister.gov, shakopeedakota.org) were blocked by this session's
  network policy and must be read before applying.
- Cross-repository pins, after #155 merges: Lumecon-data `ci.yml:131,161`
  (cedar-press `7ad068c` to the merge commit), teim-app
  `server/contracts/cedarReleaseConsumer.json:4,6`, then regenerate Grove's
  descriptors with `node scripts/sync-collection-descriptors.mjs` and
  `node scripts/sync-press-releases.mjs`. A dry run against this branch
  passed: Lumecon-data `cedar-check` (96) and `grove-check` (69), Grove's
  consumer tests and frontend suite (same two environmental `exceljs`
  failures as the baseline). Those pins sit on the `codex/*` branches of
  Lumecon-data #17 and teim-app #181.
- Not tested: Safari/WebKit (only Chromium is installed here), connected
  partner purchase and production entitlement, Docker build of the Grove
  backend.
- `RailTip` cannot be hovered itself (WCAG 1.4.13 hoverable condition).
  `server/cedar_press/articles.json` still quotes "more than 700 sources" in
  a brief, attributed as the team's working count. "Foundation & Corporate
  Giving" keeps its ampersand because the name is in citations.

## 1. NEED: publish the larger reviewed set (owner priority)

**Owner, 2026-10-06:** "We should have a larger sample of NEED … not just the
43", with examples that include tribes and agencies.

What the consumer serves today: 43 rows in
`data/cedar/need-reviewed-preview.json` (owners: Koniag Government Services
19, Nakupuna Foundation 8, Ahtna Diversified Holdings 1, no owner confirmed
15). **None is owned by a tribe.** The ten example rows are all Ahtna and ASRC
subsidiaries.

What the producer holds: Lumecon-data `README.md` on
`codex/convergence-packet-guard-20260928` (PR #17) reports **0 review rows and
143,326 held rows for `need`, measured 2026-09-30, before the hold was lifted**
by the owner ruling of 2026-10-04. Under that ruling those rows are no longer
held.

To do, in Lumecon-data with the database:

1. Re-measure NEED's servable rows under the 2026-10-04 ruling (the only
   remaining hold is a specific record ruled to name the wrong entity; apply
   `need_attribution_rulings.csv`).
2. Build the release and the customer table from that population, and choose
   the ten example rows to show the range: enterprises owned by **federally
   recognized tribes**, by **Alaska Native corporations** and by **Native
   Hawaiian organizations**, with parent chains and UEI/CAGE where present.
3. **Ask the owner what "agencies" means** before choosing rows for it. Two
   readings were offered and neither was confirmed: (a) tribal government
   agencies and authorities (housing authorities, utilities, gaming
   commissions) as owners or subjects; (b) the federal agencies an enterprise
   contracts with, which NEED does not carry today (it carries UEI and CAGE
   only; agency would come from a join to Prime Contracting).
4. Pin the new release into cedar-press with `scripts/stage_verified_previews.py`
   (its docstring gives the queue format), then regenerate as in section 7.

**Every NEED row must also name its top-level Native entity (owner,
2026-10-06: "why don't the ANC examples have the ultimate ANC, like Arctic
Slope or NANA or Koniag").** The reviewed customer table
(`public/data/cedar/downloads/need.csv`, 21 columns) carries only the
relationship each evidence page states directly: `related_entity_name` is the
immediate parent (Ahtna Diversified Holdings, LLC; ASRC Federal Holding
Company, LLC) and is blank on five of the ten example rows. There is no column
for the Native entity at the top of the chain. The older enterprise register
had it: `owner_hub_cedar_uid`, `owner_hub_name` and `owner_hub_entity_class`
(see the `need/need_enterprises` table in `data/cedar/codebook.json`, where
`owner_hub_name` is labelled "Native entity"). To do:

- Carry the owner hub (Cedar ID, canonical name, entity class) onto every
  reviewed NEED row, from the enterprise register's existing owner-hub binding
  for that `enterprise_id`, with its evidence. Do **not** derive it from the
  name ("ASRC Federal ..." is not by itself evidence for Arctic Slope Regional
  Corporation); the register binding or a source that states the chain is.
- Show it as the first column ("Native entity"), so a row reads ASRC Federal
  InuTeq → ASRC Federal Holding Company → Arctic Slope Regional Corporation.
- Where only the immediate parent is evidenced, keep the hub blank rather than
  guessing; say so in `review_reason`.

The NEED reading key (`src/features/grove/readingKeys.js`) names the values
that appear today (Subsidiary of, Owned by, Affiliated with; Immediate,
Ultimate). If the larger set introduces new relationship or extent values, add
them there.

## 2. Native Nonprofits: an accurate count

**Corrected 2026-10-06 (later the same day): the count is shown, not hidden.**
`COUNT_NOT_SHOWN` in `src/features/grove/collection.js` and
`server/cedar_press/collections.py` holds only `need`; commit `8bc330b`
("show Nonprofits' 89, hide NEED's 43") reversed the earlier hide, so readers
see "89 observations". Published today: 89 rows. Producer README: 89 review rows, **12,675 held**
(the same README note on measurement dates applies). The descriptor's method
text says 4,651 of 12,764 candidates were ruled out and 1,831 are unruled
candidates.

To do: re-measure under the no-holds ruling, decide with the owner which
population is "Native nonprofits" (ruled-in only, or ruled-in plus
candidates), publish it, and make the descriptor's method text agree with
the published count. If the owner wants the count hidden until then, add
`nonprofits` to both `COUNT_NOT_SHOWN` sets in one commit; today it is not
there.

## 3. The other held populations

Same README, same caveat. Confirm under the 2026-10-04 ruling whether these
should now publish, and re-pin if so:

| Collection | Review rows | Held rows |
| --- | ---: | ---: |
| Foundation & Corporate Giving | 193 | 7,608 |
| PLOT | 151,715 | 83,670 |
| Prime Contracting | 841,002 | 376,766 |
| Federal Funding | 640,942 | 61,013 |
| Subcontracting | 70,054 | 19,755 |
| Individual Native-Owned Businesses | 3,725 | 548 |
| Natural Resources | 11,120 | 185 |
| Deals | 978 | 95 |
| Legislation | 3,064 | 11 |

## 4. Producer-side copy the consumer is patching

These are applied in cedar-press when the descriptor is read, and should move
into the producer so the patches can be deleted:

- **PLOT's description** does not say what PLOT stands for. Both sides prefix
  "PLOT (Parcel-Level Ownership and Transfers)" (`ACRONYM_LEADS` in
  `collection.js` and `collections.py`). **Owner, 2026-10-06: PLOT stands for
  "Parcel-Level Ownership and Transfers"** (owner's exact wording). The Lumecon-data
  glossary and `docs/plot-convergence.md` still say "Parcels, Ownership, Land
  Activity & Permits" and must be updated to match. House style writes "and",
  never an ampersand, in reader prose.
- **The owned collection's name**: the producer descriptor still carries the
  pre-2026-10-02 title; Lumecon-data #17 changes it (see GAP-22 in
  `docs/RELEASE_GAP_2026-10-02.md`).

## 5. Dates and pins

- Every collection was recorded as released on 2026-10-06 (the owner asked for
  today's date). No producer data changed with it: the rendered downloads
  differ only in their citation date. The next real producer pin should carry
  its own date.
- Lumecon-data CI pins cedar-press at `7ad068c` (#132's head). That commit stays
  in history, so nothing breaks when this branch merges; move the pin to the
  new cedar-press `main` when convenient.

## 6. Example-record audit: data notes for the producer (2026-10-06)

All fourteen pinned example files were audited on 2026-10-06. The site now
works around what it can, **for display only**: the downloads are still the
pinned bytes. Each item below needs a producer fix, after which the matching
consumer workaround should be deleted.

**Consumer workarounds to delete once fixed upstream**

- `src/features/grove/showcase.js`: `EXCLUDED_EXAMPLES` (three records hidden),
  `SHOWCASE_RULES` (unattributed contract rows, monthly subaward repeats, $0
  and negative obligations pushed out or down), `DISPLAY_DEFAULTS` and
  `COLUMN_FALLBACKS` (opening columns chosen because the declared ones are
  blank in the sample).
- `server/cedar_press/collections.py` `with_native_owner`: NEED's owner
  columns in the download, until the producer publishes them. (The browser
  no longer adds any NEED record or owner; see section 0.) Owned's
  `stated_tribe` is still parsed in the browser from the row's own
  `identity_claim_text`.
- `readerPresentation.js` `repairMojibake`: garbled UTF-8 in several samples
  (for example "CNSPÃ¢Â‚Â¬Â„Â¢S").

**Data notes, by collection**

- **NEED**: no top-level Native owner column; all ten examples are ANC
  subsidiaries of two owners (ASRC, Ahtna), none tribe-owned, and four leave
  the immediate parent blank. **Owner, 2026-10-06: every NEED record must
  name its ultimate parent** (the regional corporation or the tribe, not the
  holding company one level up). Publish `native_owner` (name and
  `cedar_uid`) from the ruling chain as a column of the customer table, fill
  the immediate parent, and re-draw the sample to include tribal enterprises
  and other regional corporations (NANA, Koniag and more). The viewer
  currently adds two NANA and Koniag examples (Akima Global Services, Koniag
  Services) and fills the four blank ASRC parents ("ASRC Federal Holding
  Company, LLC" where the ruling names it, else "Part of ASRC Federal family
  of companies"); all from `code/55_stage_anc_subsidiary_rulings.py`. Check whether Salish Networks is a tribal enterprise (CSKT).
  Cherokee Nation Research Labs has a UEI conflict between sources.
- **Natural Resources**: the examples are 1925 to 1931 national aggregates;
  re-draw from recent, tribe-level ONRR records.
- **Federal Register**: only five rows, several off topic; the count mixes
  grains (9,856 documents plus 11,402 participants). Publish one grain.
- **PLOT**: only three example rows; the count includes permits. State what
  the count measures, and pin at least ten parcels.
- **Wrong links**: Leech Lake (entity class and name), Shoshone-Bannock (name),
  legislation `100-hr-2642` (Colorado Ute settlement linked to Uintah and
  Ouray, should be Southern Ute and Ute Mountain Ute), NAGPRA `00-11378`
  (Duckwater Shoshone Elementary School resolved as a tribe; also check the
  Crow link), giving `FF-03B9C4E5A6CA00E15034` (recipient reported as "Notah
  Begay"; **not** established as the NB3 Foundation, see section 8),
  nonprofits (a Seneca organization left unlinked). Section 8 has the
  evidence status and the producer-format corrections for the first three.
- **Deals**: `sector` and `capital_source` blank or uninformative in most rows.
- **Subcontracting**: one subaward re-filed monthly appears as several rows;
  a Bowhead row carries prime amount 0.
- **Prime Contracting**: three of ten rows have no attributed Native entity;
  `affiliation_attribution_status = NOT_EVALUATED` sorts as the strongest
  basis in the reader view. Rank it below every evaluated status.
- **Lobbying**: carries LDA filings only. **Corrected 2026-10-06:** this
  file said the description "now says so"; at commit `2f08aa3` it did not
  (the descriptor in `data/cedar/collections.manifest.json` was unchanged
  since 2026-09-05 and still promised agency meetings, consultations,
  comments, testimony and Schedule C). An uncommitted working-tree edit to
  that manifest, made concurrently by another worker, rewrites `tracks`,
  `sources` and `method` to LDA-only; confirm it is in the landed commit
  before treating this as done, and move it to the producer descriptor
  (section 4). If agency meetings, consultations, comments and testimony are meant to
  be in scope, they are not in this release.
- **Native Nonprofits**: the method note does not match the published 89;
  align it (see section 2).
- **Re-draw all samples** as a showcase (entity-linked, recent, with money
  where the collection has money) rather than the first rows of a sort.

## 7. Regenerating after a re-pin

From the cedar-press root, after staging:

```sh
python3 scripts/render_sample_downloads.py
node scripts/record-release.mjs
node scripts/dump.mjs --kind press --target server/cedar_press/_press_data.json
node scripts/seo-head.mjs
node scripts/docs-markdown.mjs --kind all
python3 server/tests/release_gap_register.py --write
make check-generated
```

If new files under `src/**/grove/` were added, re-measure the rename table in
`docs/ARCHITECTURE.md`; `server/tests/test_rename_plan.py` prints the current
values when it fails. Then run the full gate list at the top of this file,
including `npm run test:smoke`, which also covers the NEED and PLOT keys and
the hover card.

## 8. Example-record attribution corrections (added 2026-10-06)

Written by a later worker on the same branch. **No primary source could be
read here:** govinfo.gov, federalregister.gov, congress.gov, shakopeedakota.org,
usaspending.gov, sam.gov and every company site were denied by the session's
egress proxy (only GitHub answered). So nothing below quotes a primary
source, and no correction auto-applies. The Cedar IDs are exact names in
`public/data/cedar/register.json`.

**Where the corrections are recorded.** `review/attribution_pending_items_2026-10-06.json`,
in the Lumecon-data `lumecon_data.adjudication_triage` input format (schema
version 1, the format behind `decisions/identity/need/attribution-2026-10-04/`).
16 items; run through the triage module locally they give 7 `AUTO_OWNER_RULING`
(NEED owners, from the owner rulings in `code/55`) and 9 human review
(6 `MISATTRIBUTION_FLAGGED`, 3 `NO_DIRECT_SOURCE`). `review/*` is gitignored:
either add `!review/attribution_pending_items_2026-10-06.json` to `.gitignore`
or, better, move it to Lumecon-data as
`decisions/identity/attribution-2026-10-06/pending-items.json`. cedar-press's
own ruling inboxes (`review/rulings_inbox_*.csv`, read by `code/33`, `code/173`)
and the tables they apply to (`data/clean/`) are not in this checkout at all.

| Record | Published binding | Correct binding (to confirm from the source) | Evidence status |
| --- | --- | --- | --- |
| legislation `100-hr-2642` | `CE-001BW-3N` Ute Indian Tribe of the Uintah & Ouray Reservation, Utah | `CE-001AX-4Y` Southern Ute Indian Tribe of the Southern Ute Reservation, Colorado; `CE-001BZ-N0` Ute Mountain Ute Tribe | Pub. L. 100-585, 102 Stat. 2973 not read. Scope is also wrong: `bill_scope = general` with collective scope `federally-recognized-tribes / general_subject`; a settlement for two named tribes is tribe-specific. |
| NAGPRA `00-11378` | `CE-000E9-W1` Duckwater Shoshone Elementary School (BIE School); `CE-0014D-6E` Paiute-Shoshone Tribe of the Fallon Reservation and Colony, Nevada | `CE-00145-P6` Duckwater Shoshone Tribe; `CE-00168-JH` Lone Pine Paiute-Shoshone Tribe | 65 FR notice not read, so the other nine parties and every role (all 11 published as `affiliated`, 0 repatriation recipients) are **unaudited**. Check whether the notice also names Fallon before removing it. |
| giving `FF-03B9C4E5A6CA00E15034` | none: `recipient_name` blank, `recipient_name_reported` "Notah Begay", `overlap_status = unlinked` | unchanged | The 2023 donation report (PDF page 29) was not read. The row already preserves the reported name and leaves identity unresolved, which is correct until the page is read. Do **not** bind `CE-001MT-4K` (The Notah Begay Iii Foundation Inc) unless the page names the foundation. No item filed. |

**How the defects arise (for the producer fix).**

- Legislation: the bill-entity bridge matched the spine short name `Ute`
  (`data/spine/cedar_entity_names.csv`, `CE-001BW-3N`) inside "Colorado Ute"
  (inferred: the full name is not in the title). The same token links
  Uintah and Ouray as a third entity on `105-hr-745` and `105-s-440`, whose
  titles name only "the Ute Mountain Ute Indian Tribe and the Southern Ute
  Indian Tribe" (`dist/preview/legislation.csv` lines 64 and 72), and by
  inheritance on vote `S106-0656` / `106-s-2508` (title not in Git). `103-s-2252`
  and `104-hr-2239` rest on the same token but may be right (Ute tax status
  concerns Uintah and Ouray mixed-bloods), so they are review items, unmasked.
  Fix in the bridge builder: a short name that is a substring of another
  spine entity's name in the same span must not match on its own. The
  title-only scope ruler (`build_scope_ruler`, `code/14`) drops names under
  eight characters and cannot see statute text, which is why the row reads
  `general`.
- NAGPRA: `Duckwater` and `Paiute-Shoshone` are the spine short names of the
  school and of Fallon. The current `party_candidate_view` in `code/77`
  already refuses a BIE School for any fragment containing "tribe", so a
  rebuild with today's code should not repeat the school binding; the Fallon
  containment match has no such guard. The published row's
  `entity_names_as_published` is null, so the verbatim fragments cannot be
  checked from Git.
- Other occurrences found in the populations in Git (10-row samples, legacy
  fixtures, `dist/preview`): none else of school-as-tribe; NAGPRA `00-10463`
  binds "Native Village of Eagle" twice (affiliated, repatriation recipient)
  for a BLM Alaska notice and `eagle` is on `code/77`'s trap list, so check it
  against the notice; the legacy NAGPRA bridge fixture shows "Oneida Indian
  Nation of New York" with canonical name "Oneida Nation" but the correct uid
  `CE-0017X-NE` (stale display name only). Giving: no other person-name
  recipient among the ten published rows. The full populations are not in
  Git, so this sweep is not exhaustive: rerun it in Lumecon-data.

**Steps, with the release store and network (Codex).**

1. Read the three sources and record page-anchored quotes: Pub. L. 100-585
   (`https://www.govinfo.gov/content/pkg/STATUTE-102/pdf/STATUTE-102-Pg2973.pdf`,
   section 2 and every section naming a tribe); FR 2000-05-08 doc 00-11378
   (`https://www.govinfo.gov/content/pkg/FR-2000-05-08/pdf/00-11378.pdf`, the
   full party list with each party's role); the SMSC 2023 donation report,
   PDF page 29. Add each quote as `evidence` (`source_kind` `government_record`
   or `first_party`, `capture` `page`) to the matching item, and add NAGPRA
   items for any other party or role the notice contradicts.
2. Land the file in Lumecon-data, run
   `uv run python -m lumecon_data.adjudication_triage --input <file> --output-dir <dir> --ruled-date <date>`,
   and put the `MISATTRIBUTION_FLAGGED` items in front of a person (the owner
   rule reserves them).
3. Apply the ruled corrections in the producer builds of legislation and
   NAGPRA (the appliers do not yet read `BILL_ENTITY_LINK` or
   `NAGPRA_NOTICE_PARTY`; add that, keyed on the bill or notice and the uid),
   including the 100-hr-2642 scope change, and cut new releases.
4. Re-pin in cedar-press: write a 15-entry queue (collection, release, store,
   manifest_sha256), then with `LUMECON_ENVIRONMENT=review` and both
   Lumecon-data `src/` and cedar-press `server/` on `PYTHONPATH`:
   `python3 scripts/stage_verified_previews.py --repo . --producer <Lumecon-data checkout at the release commit> --producer-commit <sha> --queue <queue.json> --output <new dir> --refresh-existing --collection legislation --collection nagpra --expected-existing-release legislation=8b4569e17831f4a0dfc7a6df8f03e39191f79637f714fe76bd9ba0991e56f2f3 --expected-existing-release nagpra=b45822cd045724582cee3e2be0e87008fc61569d82cf2fa53fe2e2c309eb3c0d`,
   (`--refresh-existing` stages and does not install; install with the
   script's `--admit-existing --staging <dir> --receipt <file>` preflight,
   then the same with `--apply`, per its `--help`), then regenerate as in
   section 7 (`render_sample_downloads.py` rewrites
   `public/data/cedar/downloads/*.csv` from the new samples).

**Why this could not be done here.** The pinned samples
(`data/cedar/samples/*/spreadsheet__10.csv`) are cut by
`stage_verified_previews.py` from a verified release spreadsheet that it
re-hashes against the producer receipt (legislation release `8b4569e1…`,
2,094,957 bytes; NAGPRA `b45822cd…`, 12,684,163 bytes). That needs the
release store (an absolute `store` path per collection) and a Lumecon-data
checkout whose `src/lumecon_data/dbload.py` and `spreadsheet.py` exist at the
pinned producer commit. The commits are in the local Lumecon-data object store
(`cf29ec31`, `9f615693`), but no release store, `data/clean/`, `data/raw/`,
database or parquet/sqlite/duckdb file exists anywhere in the container, and
no environment variable points to one. Hand-editing the sample bytes would
break the sha256 pins in `data/cedar/verified-preview-releases.json` and
`collections.manifest.json`, so it was not done.

**NEED ownership evidence.** `data/cedar/need_ownership_evidence.json` holds
the chain (immediate parent, ultimate Native owner, Cedar ID, UEI, CAGE,
evidence URL and quote, open issues) for the ten pinned rows and the five
records the viewer adds. Its ultimate-owner half is also filed as pending
items. It is a new file under the gitignored `data/cedar/`; add
`!/data/cedar/need_ownership_evidence.json` to `.gitignore` if the viewer reads
it. Findings the viewer should honour: the CNI Advantage immediate parent
(Chickasaw Nation Industries) and the Akima Global Services parent (Akima,
LLC) have no source in Git; the trade name "Choctaw Defense Manufacturing
Group" and "wholly owned" for Chickasaw Nation Industries have none either;
Koniag Services' immediate parent is probably Koniag Government Services, LLC,
and Akima Global Services may be jointly owned with The Aleut Corporation
(both are uncaptured web-search leads, to be confirmed before anything is
published); ASRC Federal Advanced Research and the three Ahtna rows have no
ownership statement in Git beyond the domain of their evidence pages.
