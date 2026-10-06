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
  the Collections table footer gap closed; the Native Nonprofits count hidden;
  a hover card on the app's collection list; "How to read these records" keys
  for NEED and PLOT; NEED and PLOT spelled out wherever a paragraph describes
  them.

Every local gate passes: `npm run lint`, `make check-generated`,
`npm run test` (coverage gate), `ruff check server`, `make test-python` and
`npm run test:smoke`. **Not run:** `make audit-node` and `make audit-python`
(network), the `subscriber-storage` workflow (Postgres), the cross-repository
Lumecon-data job in `.github/workflows/ci.yml`, and the deploy.

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

The count is hidden from readers (owner, 2026-10-06), by `COUNT_NOT_SHOWN` in
`src/features/grove/collection.js` and `server/cedar_press/collections.py`.
Published today: 89 rows. Producer README: 89 review rows, **12,675 held**
(the same README note on measurement dates applies). The descriptor's method
text says 4,651 of 12,764 candidates were ruled out and 1,831 are unruled
candidates.

To do: re-measure under the no-holds ruling, decide with the owner which
population is "Native nonprofits" (ruled-in only, or ruled-in plus
candidates), publish it, then remove `nonprofits` from both
`COUNT_NOT_SHOWN` sets in the same commit.

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
- `src/features/grove/exampleEnrichment.js`: NEED's `native_owner` columns
  and the three prepended tribe-owned examples (CNI Advantage, Chickasaw
  Nation Industries, Choctaw Defense Manufacturing Group), each sourced to an
  owner ruling in `code/55_stage_anc_subsidiary_rulings.py`; owned's
  `stated_tribe`, parsed from `identity_claim_text`.
- `readerPresentation.js` `repairMojibake`: garbled UTF-8 in several samples
  (for example "CNSPÃ¢Â‚Â¬Â„Â¢S").

**Data notes, by collection**

- **NEED**: no top-level Native owner column; all ten examples are ANC
  subsidiaries, none tribe-owned. Publish `native_owner` (name and
  `cedar_uid`) from the ruling chain and re-draw the sample to include tribal
  enterprises. Check whether Salish Networks is a tribal enterprise (CSKT).
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
  Crow link), giving `FF-03B9C4E5A6CA00E15034` (recipient "Notah Begay",
  almost certainly NB3 Foundation), nonprofits (a Seneca organization left
  unlinked).
- **Deals**: `sector` and `capital_source` blank or uninformative in most rows.
- **Subcontracting**: one subaward re-filed monthly appears as several rows;
  a Bowhead row carries prime amount 0.
- **Prime Contracting**: three of ten rows have no attributed Native entity;
  `affiliation_attribution_status = NOT_EVALUATED` sorts as the strongest
  basis in the reader view. Rank it below every evaluated status.
- **Lobbying**: carries LDA filings only; the collection description now says
  so. If agency meetings, consultations, comments and testimony are meant to
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
