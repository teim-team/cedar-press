# Cedar data → Cedar Press

Real rows from the Cedar Press data project, in the shape this product already
declares. **Nothing here is wired in yet** — this is the data side of the
handshake, offered for review before anything replaces the demo series.

## Why this exists

`server/cedar_press/collections.py` says it plainly:

> **PROTOTYPE LIMITATIONS** — Every number in this file is demonstration data,
> exactly like `prototype_data.py`: plausible values for the demo workspace,
> never real published figures. **The real pilot datasets arrive as manifest +
> data files and replace the inline series here.**

These are those files.

## The two sides already agree

Checked, not assumed. The contract was written on both sides independently and
lines up:

| this product | the data project |
|---|---|
| launch ids `deals`, `contractors` | the same dataset ids |
| `shelf` — `standard` / `pro` / `grove` | the same, plus `infrastructure` for the entity hub |
| `level` — entity, or entity that rolls up to geography | `518.NATURAL_SCOPE` |
| `CollectionDataset` fields | emitted by `code/760_collection_descriptors.py` |

The one place they did **not** agree was the owned-business id, which Codex
caught: Cedar calls that collection `native-owned-businesses` and the catalog,
launch collection, article wiring, profile construction and API tests all call
it `owned`. It is mapped now, `owned` is what ships, **and the sample file is
named `owned__sample.csv`** — which it was not until today, because the
mapping reached the descriptor and not the filename. See finding 7 below.

## What is here

**`collection_descriptors.json`** — one object per dataset, carrying
**exactly** the fourteen `CollectionDataset` fields and nothing else, so
`CollectionDataset(**descriptor)` loads every one of the fourteen objects.

- The fields: `id`, `name`, `short_name`, `origin`, `level`, `tracks`,
  `rows_label`, `downloads`, `vintage`, `version`, `updated`, `sources`,
  `method`, `shelf`.
- **This file said "13 of 13 deserialize" and 0 of 13 did.** Every object also
  carried `cedar` and `needs_copy`, and an undeclared keyword is a `TypeError`
  whether it is one key or five. That is the same defect PR #26 finding 1
  closed on `n_rows`, reintroduced by the fix for it — namespacing Cedar's
  fields under one key made them tidy and left them just as unsupported.
  Codex caught it both times. The repair this time is the first of the two
  options it offered: publish only the dataclass fields.
- **Cedar's own facts move to `collection_descriptors.cedar.json`**, a sibling
  object keyed by the same product id, carrying `cedar_id`, `product_id`,
  `status`, `blockers`, `n_rows`, `n_tables`, `sample_file` and `needs_copy`.
  Nothing was dropped; it is one join on `id` away.
- **The claim is now a check rather than a sentence.**
  `code/760_collection_descriptors.py` compares each object's key set against
  the declared field tuple in **both directions** — a missing field and an
  unsupported extra are the same failure — and exits 1 rather than writing.
  Prose asserting a contract is how this broke twice.
- `downloads` is present and **`0`** — a platform metric Cedar has no business
  inventing, so it says "not counted here" rather than fabricating a count.
  `version` is `v0`; the platform owns bumping it.
- `blockers` (in the `.cedar.json` sibling) carries the **named** contract
  points rather than the bare word `BLOCKED`, so a consumer can tell a
  publication-rights block from an incomplete schema without opening an
  external project. **Three lists are non-empty today** — `owned` carries
  three named failures, `federal-register` three, and `deals` two. See
  *Status of the fourteen*. *(This line has now been wrong twice in the same
  way: it read "Today every dataset's list is empty" until Codex round 3, then
  "Two lists" until round 5 found it still saying two after
  `federal-register` was blocked. Both times the overview and the section it
  summarises went out of step. The count is the problem — it is now the names,
  which cannot drift without someone noticing which one is missing.)*
- `rows_label` is a count **only when a count is established**. Where two
  Cedar-side declarations of a collection's membership disagree it reads
  `row count unresolved`, and the component measurements ship separately in
  the `.cedar.json` sibling, each labelled with the table set it came from and
  **not added together**. Codex round 3 was right that publishing the sum
  fabricated a dataset that does not exist in that shape.

**`samples/*.csv`** — 10 real rows per dataset, 14 datasets. Not drafts of the
full tables; proof of concept, so the finished shape can be judged before the
datasets are finished. **The filename is the descriptor's `id`**, and
`sample_file` in the `.cedar.json` sibling states the path for each, so a
manifest consumer never has to guess it.

## How the samples were built, and what was deliberately left out

Every gate in the data project checks the data against a rule. **None of them
checks whether a person opening ten rows understands what they are holding.**
That is what these are for, so the construction matters:

- **Real rows only.** Straight from the clean tables, nothing synthesised.
- **The flagship table is curated, not the largest.** By row count,
  native-owned-businesses would have shipped an *exclusion* list — the rows
  judged NOT Native — and funding a BIE sub-table. Both real; neither is the
  product.
- **Columns are curated too.** `gaming_facilities` carries 105 columns, and
  every metric repeats four times as value / value_basis / observation_status
  / observed_date. That provenance is right to keep in the table and wrong to
  open a sample with. Nothing was removed from the datasets — only from these
  ten-row views.
- **The column set is fixed by that curation and does not move.** It used to.
  Until 2026-09-02 the builder deleted any requested column that happened to be
  blank across the ten rows drawn, so the sample *schema* was a function of the
  sample and a buyer diffing two rebuilds watched columns appear and vanish
  with no note. Requested columns now always ship; the ones that came back
  blank are named in `samples/README.md` under **Columns that are in the
  schema and empty in this sample**, because that is a coverage fact worth
  having rather than one to hide by dropping the column.
- **Spread, not `head()`.** First-ten returns one agency in one year and makes
  a dataset look narrow. Rows prefer completeness, then sample evenly.
- **Publishable rows only.** `publishable = N` and any
  `TERMS_STATED_RESTRICTIVE` source never appear — Navajo's 346 NBOA rows are
  absent here exactly as they are absent from a release.
- **Personal data held apart from a public role is refused** — home address,
  personal email or phone, date of birth, SSN or TIN. This is narrower than
  what this file used to claim, and the narrower claim is the correct one:
  `lobbying_registrants.csv` publishes STEPHEN GRAHAM of Boston MA and that row
  is *right*, because an individual may register as a lobbyist and the
  registration IS the public record the Lobbying Disclosure Act creates. A
  lobbying dataset that hid individual registrants would be broken. Codex
  flagged the old blanket wording and was correct to.

## Two columns that look like keys and are not, alone

Both were found by review of these samples, which is the argument for shipping
them.

- **`prime_contracts.contract_number`** is the awarding PIID, and on 290,519
  rows (23.9%) it is a modification stub — `0098`, `0006`, `SBA0001` —
  meaningless without the IDV it references. Four of ten sampled rows showed
  one. **`parent_contract_number` ships beside it, and the pair is the key.**
  Re-measured 2026-09-02: **507,884** rows carry a real parent and a full
  child PIID, **290,519** a real parent and a stub, **419,359** no parent and
  a complete standalone PIID, and **6** have neither.

  **Those numbers replace 664,470 / 290,525 / 262,773 / zero, and the
  correction is Codex's finding 4.** The old "zero rows have neither" was true
  only because **156,592 rows (12.86%) carried
  `parent_contract_number == contract_number`** — a self-parent, which the
  README's own definition of the column forbids. 156,587 of them come from the
  legacy `master prime file.dta`, where "standalone" is *encoded* as
  self-parent: measured in the raw source, 216,882 of 617,142 rows are
  self-parent and **not one is blank**, against a genuine blank on 31.2% of
  the FPDS archive rows. Same population, same rate, two encodings, and Cedar
  was shipping one of them as a vehicle reference. Cleared, and blanked rather
  than deleted — `contract_number` still holds the value on every affected
  row, so nothing is lost but a false edge.

  The generator was fixed too: `114_pull_prime_archive.py` wrote
  `s("parent_award_id_piid") or s("award_id_piid")`, which manufactures a
  self-parent whenever FPDS reports no referenced IDV. It had produced only 5
  live rows, which is exactly why it survived — and 262,773 archive rows in
  the merged table have no parent, so one refresh through that line would have
  turned all of them into fabricated self-parents.

  The remaining **6 rows with neither** are six-character PIIDs from the same
  legacy file with no vehicle. They are short pre-FPDS-NG identifiers rather
  than modification stubs, so they are named here rather than counted as
  broken.

  Adding that column exposed a second defect worth naming: it was documented as
  populated on all 1,217,768 rows and it was not. 262,773 rows (21.6%) held the
  literal three-character string `nan` — a pandas float written through
  `str()` on the way to CSV, which counts as present and means absent. Cleared
  at source.

- **`federal_funding_transactions.canonical_name`** is a legacy display label,
  not Cedar's name for the entity. **Group on `cedar_uid`.** On 344,360 of
  552,602 keyed rows the two disagree, and every one of those is a right
  identity wearing a stale label — re-measured below, with the method, because
  this file previously stated the same quantity as two different numbers.

## The Acoma finding, and the correction the data side owes this review

Codex read the funding sample and reported that `PUEBLO OF ACOMA (INC)`
resolves to Haaku Community Academy — a subordinate institution standing in for
the nation. **The reply it got from this side said that was a real
misattribution across 2,434 rows and $1.008B. That reply was wrong**, and
correcting it matters more than the original finding.

Traced to the row, the *keyed* attribution is correct. Every Acoma-family row
carries `cedar_uid = CE-0011W-HN`, which the identity register resolves to
**Pueblo of Acoma**, a federally recognized tribe. What is wrong is only the
free-text `canonical_name`, which `24_funding_merge` copies verbatim out of a
legacy do-file key that literally contains `{234, 'haaku community academy',
NM}`. It is not a Cedar name at all.

**Re-measured 2026-09-02, and this file had stated the same quantity twice with
two different values** — 345,180 where the section above now reads 344,360,
and 345,108 in this paragraph. **Both are dead**, and both are quoted here
only so the correction is traceable; neither figure appears anywhere as a live
claim. The method, so the next reader repeats it instead of trusting
it: compare `canonical_name` in `data/clean/federal_funding_transactions.csv`
against the `canonical_name` the identity register
(`data/spine/cedar_identity_register.csv`, 1,555 entries) holds for that row's
`cedar_uid`, case-insensitive, exact string.

| | rows |
|---|---:|
| carry a `cedar_uid` | 552,602 |
| …name disagrees with the register | **340,738** |
| …`canonical_name` blank, uid present | 3,622 |
| …`cedar_uid` absent from the register | **0** |
| total not matching the register's label | **344,360** |

**340,653 of the 340,738 — 100.0%, $94,256,591,555.42 of obligations — carry a
label that appears verbatim in the legacy do-file key
`lineageA_dta_corrtd_tribe_key.csv` (393 distinct name strings).** Right
identity, stale label, one known cause.

**The residue is 85 rows and neither needs a repoint, which is the part worth
saying.** 72 rows / $29,694,344.00 on `CE-001GC-WN` are labelled `Forest
County` while the register calls that entity *Sonoma County Indian Health
Project, Inc.* — and **all 72 are `recipient_state_code = CA`**, so the key is
right and only the label is wrong. That label is worse than merely stale: it
names a Wisconsin county, and Forest County Potawatomi is a real nation whose
published terms forbid reuse. The other 13 are `Warms Springs Tribe` for *Warm
Springs Tribe*, all Oregon — a typo. **Zero of the 344,360 turned out to be a
misattribution.**

The register holds the real sub-hubs separately and uses them correctly when
the recipient genuinely is the school (Blackfeet Community College,
`CE-0010N-2P`, 312 rows).

So entity-level grouping on `cedar_uid` — the key ADR-009 mandates — credits
the tribe. Only grouping on the legacy display name credits the school. **The
sample now shows `cedar_uid` beside `canonical_name`** so a reader can see
which of the two is the join.

**The genuinely wrong attribution was found by chasing this and is smaller in
rows and worse in kind.** Legacy id 347 mapped **820 rows and
$181,881,441.37** of *United Keetoowah Band* obligations onto *Cherokee
Nation* — two distinct federally recognized tribes merged into one uid on a
loose token match on the word "Cherokee", with United Keetoowah Band sitting in
the register in its own right. Fixed at source. The legacy id scheme that
produced it has since been retired outright.

## Before totalling any money column

`docs/MONEY_TOTALLING_RULES.md` in the data project is the authority. The three
that bite hardest:

- **`subaward_amount` summed unfiltered gives $45.62B against a correct
  $24.41B.** The filter removes **$21.21B** — **86.9% of the correct total**,
  and **46.5% of the unfiltered one**. *This file previously said 46.5% and the
  product descriptor said 86.9%, with neither stating its denominator, and a
  buyer holding both would reasonably conclude one of us cannot do arithmetic.*
  Both are the same $21.21B against different bases. An overstatement is
  measured against the truth, so **86.9%** is the number that ships and the
  denominator now travels with it. Filter to `duplicate_status = 'primary'` and
  `subaward_exceeds_prime_flag != 'yes'`.
- **`owner_obligations_usd` sums to $6,535.96B against a true $176.74B**, a
  36.98× inflation: owner-grain attributes repeat on every operating-company
  row. `firm_*` is the additive family.
- **A subaward is a slice of a prime award.** Never add subcontracting to
  contracting.

## One thing that reads as a bug and is not

In `gaming__sample.csv`, a facility shows `property_status = current` with a
past `close_date`. **Both are correct.** 113 of 787 rows carry a past
close date while currently operating — Casino Morongo closed in 2010 and
Chukchansi Gold in 2014, and both reopened and are open today.

The data is honest and the *schema* reads badly: one `close_date` column cannot
distinguish "closed permanently" from "closed once, since reopened." Flagged on
the data side.

## Status of the fourteen

**11 of 14 are READY as regenerated for this push**, against 12 in the last
one and 14 the one before. Both blocked datasets are named, with the contract point each one
misses, in `collection_descriptors.cedar.json`:

| | | |
|---|---|---|
| `owned` | BLOCKED | its published row count is contradicted by its own sample — a check added on this branch, section below. Its count is **withdrawn** |
| `federal-register` | BLOCKED | its sample is drawn from `consultation_events.csv`, which the contract marked **`UNDOCUMENTED`** rather than `shippable` at 09:23 today. Its 490,274-row count is **not** in dispute and still ships |
| `deals` | BLOCKED | `C1 grain UNSTATED` and `C2 no validated primary key` on `deals_press_edgar_ancsa_additions.csv`, a table another workstream added to the collection while this branch was open |

**The blocks are not all treated the same, and that distinction is enforced
in code.** An *arithmetic* violation — a published count smaller than
one of the dataset's own tables — is provably wrong, so the count is
withdrawn. A *membership* violation — the sample source is not a shippable
member — leaves the count untouched, because nothing contradicts it.
Collapsing them would have withheld `federal-register`'s 490,274 because a
different table's codebook status lapsed, which is a remedy out of all
proportion to the measurement. `deals` is a third case again — an ordinary
readiness block from the scoreboard, owned by another workstream.

**The `deals` block is not this workstream's and is named rather than
absorbed.** It is also the honest illustration of why this section says
"as regenerated" rather than a number: the count was 14, then 13, then 12
inside one hour, because ten jobs write the underlying tables concurrently and
`deals_classified.csv` itself moved 935 → 1,079 rows mid-branch. **Regenerate
the scoreboard — `py -3 code/518_dataset_readiness.py` — rather than quote
this line.** There are three statuses and no fourth.

Otherwise unchanged: up from 4 when this branch first opened and 11 two days
ago, with `nest` (tribally owned enterprises) the fourteenth collection,
landed mid-branch and shipping a sample like the rest.

**This section previously said 11 of 13, and named `subcontracting` at 42% of
entity-bearing rows keyed and `funding` at 40%. Both figures were wrong, and
Codex was right that they contradicted the descriptor — and wrong about which
half to change.** The contradiction it found is real and the descriptor is the
correct half.

The C4 coverage check read the **first 50,000 rows** of each table and
reported the result as a percentage. `head -n` is not a sample of a file with
an ordering, and the error was measured rather than feared:

| | first 50,000 | full file | error |
|---|---|---|---|
| `prime_contracts.csv` | 22,595 / 50,000 = 45.2% | 888,958 / 1,217,768 = 73.0% | **−27.8 pp** |

The cap read 4.1% of `prime_contracts` and 1.8% of
`faads_transactions_all_agencies`. It happened to cover 65% of `subawards.csv`,
which is precisely why the defect stayed invisible: it looked fine wherever
anyone checked. On the full scan:

| dataset | capped | full scan |
|---|---|---|
| `contractors` | 60% | **75%** |
| `subcontracting` | 42% | **100%** |
| `funding` | 40% | **80%** |

So `subcontracting` is fully keyed, its C4 blocker was removed because it was
measuring the wrong thing, and **the 42% in this file was the stale half of
the pair.** `funding`'s number moved twice — the full scan first put it at
16%, and the FAADS attribution work since has taken it to 80% — which is the
argument for regenerating this section rather than typing it: a figure quoted
by hand goes stale in place, and this one went stale twice in two days.

A BLOCKED dataset is not unusable; it means a specific contract point is
unmet, and which one is printed. Two are blocked today; the one this branch
found is below.

## The finding this side brought: `owned` shipped two row counts 1,259 apart

Nothing Codex asked for. It came out of the instruction to re-check every
claim in this directory against the live data before pushing, and the two
contradicting files were **already both in this repo**, side by side:

    data/cedar/samples/README.md          owned -> native_owned_businesses.csv, 2,916 rows
    data/cedar/collection_descriptors.json  owned -> "rows_label": "1,657 rows"

**A sum over a dataset's tables cannot be smaller than one of its tables.**
That is the whole bug, and it needed no judgement to see once the two numbers
were put next to each other — which nothing had ever done.

**Cause.** `770_sample_extracts.FLAGSHIP` draws the customer's ten rows from
`native_owned_businesses.csv` — the harmonised directory, **2,916 rows across
21 certifying authorities**, and the table the dataset is named after.
`760_collection_descriptors.rows_in()` sums only the tables the *collection
contract* claims, and for this collection that is six `individual_native_*`
tables totalling 1,657 — a different workstream, about firms owned by
individual people rather than by nations. The collection's membership rule in
the data project, `500.COLLECTIONS`, matches
`^(individual_native|tribal_certification)`; the namesake table matches
neither branch and is claimed by **no collection at all**. It has been a known
orphan since 2026-09-01, listed under `contract_orphan_shippable = 6` and
attributed to "the workstreams that registered them". Nobody had connected it
to what the product publishes.

**The row count is the smaller half of the cost.** `owned` was reported READY
on `c4_identity_path = 100% keyed` and `c1_grain = 6/6` — both measured across
the six tables that exclude the directory. Measured on the directory itself:

| | |
|---|---:|
| rows | 2,916 |
| `business_entity_id` filled | **4 (0.1%)** |
| `nation_id` filled | 2,725 (93.4%) |
| `certifying_authority_entity_id` filled | 2,767 (94.9%) |
| declared grain | **UNSTATED** |

So "100% keyed" is true of six tables the buyer is never shown and false of
the one they are. The dataset keys reliably to a *nation*; it barely keys the
*business*. That is a real and defensible product — `affiliated_with` a named
nation is exactly what `docs/PUBLICATION_POLICY.md` says Cedar should claim —
but it is not what READY was asserting.

**What was done, and what deliberately was not.** `760` now enforces the
arithmetic invariant, with three fixtures that prove the check fires
(`py -3 code/760_collection_descriptors.py selftest`) and a `verify` that
exits 1. On a violation it marks the dataset BLOCKED and publishes the
measurement in `cedar.blockers`. The status reverts on its own the moment the
collection is fixed.

**It publishes no row count at all, and the first version of this fix did —
Codex round 3 was right to refuse it.** That version shipped the *sum*,
1,657 + 2,916 = 4,573, which assumes the six contract tables and the flagship
are disjoint rows of one dataset. Nothing establishes that: this very section
argues they are **different relations** — firms a nation certified, and firms
owned by individual people — which is a reason to think they are disjoint, not
a measurement that they are. And the qualification sat in `n_rows_basis` in
the sibling `.cedar.json`, while `rows_label` is the field the product
renders, so a consumer would have seen `4,573 rows` as an exact count of a
dataset that does not exist in that shape. A fabricated number with a footnote
nobody renders is still a fabricated number. `rows_label` now reads
**`row count unresolved`**, and the two component measurements ship separately
in the sibling file — `n_rows_contract_tables` 1,657 and `n_rows_flagship`
2,916 — each labelled with the table set it came from and not added together.

**And pulling on the refusal found that 1,657 was never a row count either.**
Codex's objection was that nothing establishes the two table sets are disjoint
rows of one dataset. Measured, they very nearly are — 10 shared firm names
across all six contract tables against the directory's 2,738. But the same
measurement exposed something worse **inside** the contract set, which neither
side had looked at:

| table | rows | what a row is |
|---|---:|---|
| `individual_native_firm_register.csv` | 45 | a firm |
| `individual_native_firm_contracts.csv` | 324 | a **firm-year** — 38 distinct firms |
| `individual_native_ownership_verification.csv` | 335 | a firm's verification |
| `individual_native_verification_candidates.csv` | 335 | **the same 335 firms again** — all 335 `(name, uei)` keys shared, identical column set |
| `individual_native_firm_contracts_published.csv` | 613 | **not a firm at all** — `cell_type`, `dimension_1`, `dimension_2`, `n_firms`: a published cross-tabulation |
| `individual_native_exclusion_pairs.csv` | 5 | a pair |
| **sum** | **1,657** | **five different grains added together** |

So 1,657 counts 335 firms twice and adds 613 aggregate summary cells to a firm
count. **Neither number in the original contradiction was a count of a
dataset**, and adding them produced a third that was worse than both. Codex
asked for the count to be left unstated until the membership and
de-duplication semantics are resolved; the de-duplication problem turned out
to be inside the half nobody was questioning.

**The blockers carry the flagship's own contract failures, not just the count
mismatch** — also Codex round 3, and also right: the earlier version left the
harder failures in prose, where a consumer following the instruction to read
`cedar.blockers` would have concluded that reconciling the count alone makes
`owned` ready. All three now ship, measured on the table itself rather than
asserted: the flagship mismatch, `C4 identity path` (`business_entity_id`
filled on 4 of 2,916 rows, 0.1%), and `C1 grain UNSTATED` with no validated
primary key. The identity column is *found* among candidates rather than
assumed, and a table carrying none of them reports UNMEASURED rather than a
fill rate for a column that is not there.

## Codex round 3, finding 2: one `Nan` in one sampled row, 617,097 in the table

Codex saw `funding_agency = "Nan"` on row 4 of the contractors sample and
called it the same stringification failure the README says was cleared from
`parent_contract_number`. It was, and the reason it survived is more useful
than the row.

`772_strip_nan_sentinels.py` matched the sentinel **case-sensitively**, and
its own docstring gives the reason: *"never a substring — `Nanticoke`,
`Nanakuli` and `NANA` are real values in this project and a substring rule
would eat all three."* Every one of those is an argument against a **substring**
rule, and this was never a substring rule — it is a whole-cell equality test,
and a 3-character token cannot equal a 4- or 8-character value. **The
case-sensitivity guarded nothing that the whole-cell rule was not already
guarding, and it hid this:**

| column | cells | share of table | rendering |
|---|---:|---:|---|
| `cage_code` | 398,840 | 32.75% | `NAN` |
| `place_of_perform_city` | 88,269 | 7.25% | `NAN` |
| `place_of_perform_state` | 87,068 | 7.15% | `NAN` |
| `funding_agency` | 33,263 | 2.73% | `Nan` |
| `extent_competed` | 9,411 | 0.77% | `NAN` |
| `recipient_state_code` | 202 | | `NAN` |
| `parent_uei` | 22 | | `NAN` |
| `recipient_city_name` | 22 | | `NAN` |
| **total** | **617,097** | | |

`extent_competed` is the worst of the eight. Cedar's own guidance is that the
column holds two vocabularies and must be read through
`extent_competed_normalized`; a phantom `NAN` code is a third.

**The scope is one table, measured in both directions.** The same
case-insensitive sweep over the eleven other flagship tables — `subawards`,
`np_orgs`, `deals_classified`, `gaming_facilities`, `nagpra_notices`,
`native_owned_businesses`, `nest_enterprises`, `resource_revenue`,
`lobbying_registrants`, `bill_votes`, `consultation_events` — returns **0
cells**. This is `prime_contracts.csv` and nothing else.

**The token set was deliberately not widened.** `NA` (6 cells in
`award_base_description`) and `N/A` (7 in `recipient_city_name`) are left
exactly as they are. `NA` is an abbreviation a human may have typed to mean
*not applicable*, which is a statement; stripping it would be a judgement
rather than a repair. They are named here instead of swept.

### The source fix lost a race, so the guard is in two places

772 was corrected and run: 617,097 cells cleared, 1,217,768 rows in and out,
`$310,005,258,660.75` unchanged to the cent. Re-measured minutes later:
**all 617,097 were back.** A concurrent in-place enricher had read the table
before 772 started, and wrote back its own copy — with five new
`identifier_ruling_*` columns and every sentinel restored. 772's guard
compares size and mtime **across its own read** and correctly saw nothing
change; the other writer's read predated it.

That is this project's documented collision in a new place: **two in-place
enrichers on one table need a declared ordering, and these two had none.** It
is reported rather than fought — re-running 772 in a loop against another job
is a write war, and the ordering is an integrator decision.

So the second guard sits in the **product layer, where it cannot be raced**.
`770` now blanks any whole-cell null token (`nan`, `none`, `null`, `<na>`,
`nat`, case-insensitive) across the **whole source table** before the ten rows
are drawn — which also stops a row being judged "complete", and so
preferentially sampled, for holding the string `Nan`. Whatever the live table
holds this minute, no sample ships a fictitious agency. The counts are printed
per column and published in `samples/README.md` as a coverage fact, so the
guard surfaces the upstream defect rather than concealing it.

## Codex round 4: three findings, three right

| # | finding | verdict |
|---|---|---|
| 1 | the blocker still described a whole-dataset count conflict after the count was withdrawn | **Right — and it is the fourth instance on this branch** |
| 2 | topping up after a race publishes a mixed-version sample; restart instead | **Right, including the part I could not see** |
| 3 | `2Â€? CONDUIT` is corrupt and should not ship | **Right that it is corrupt; the suggested remedy reaches 9.6% of it** |

### Finding 1 — a stale number inside the very fix that made it stale

The blocker read *"the descriptor claims 1,657 rows for the whole dataset"* in
the same commit that set `n_rows` to null and relabelled 1,657 as the unsummed
size of six heterogeneous tables. A consumer relying on `cedar.blockers` was
told the open problem is an exact count conflict, when the point of the other
fix is that **no dataset-level count exists**. It now describes the membership
and grain conflict, which is what is actually unresolved.

**That is the fourth time on this branch a number was corrected in one place
and left standing in another** — `owned`'s two row counts, `345,180` /
`345,108`, the blockers overview, and now this. The first three were a
correction and an old copy elsewhere. This one was inside the fix itself.

### Finding 2 — right, and the hole was bigger than the one it named

The top-up restored the sample's *cardinality* and nothing else: the surviving
targets came from the old file's positions and completeness scores, the spares
from the rewritten file, so their union was a mixed-version sample that
preserved neither "most complete" nor "evenly spread". Codex also named the
case I had not seen — **a rewrite that leaves all ten target positions
publishable needs no replacements at all**, so the `RACED` warning never fires
and a silently mixed sample ships. One more check that did not measure its own
name, in the code written to catch exactly that.

There is no top-up now. The file is stamped `(size, mtime_ns)` before pass 1
and re-stamped after pass 2 — **on every attempt, not only when the sample
came up short**. If it moved, both passes are discarded and the sample is
re-drawn from a fresh snapshot; after three attempts it **raises rather than
publish**. Refusing is the honest outcome when a table will not hold still.

**And unifying the engines caught a live divergence.** `proveequal
subawards.csv` failed on row 1 after the mojibake work, because the streaming
engine discounted corrupt cells when scoring rows and the in-memory engine did
not, so the two chose different rows. `completeness()` now delegates to
`_score()` — one ranking function, both paths. That is the check earning its
keep on the exact thing it was written for.

### Finding 3 — right about the corruption; the remedy only reaches 9.6%

Real in the bytes this time: `b"1. 2\xc3\x82\xe2\x82\xac? CONDUIT"`. Worth
contrasting with the round-2 report of the same shape, which was a cp1252
*console* rendering a correct UTF-8 en dash and was measured before being
reported and found to be nothing.

Scale in `subawards.csv` (87,177 rows): **1,433 cells** — `description` 1,423
rows (1.63%), `subaward_number` 6, `sub_parent_name` 2, `sub_name` 2.

Codex asked to *"correct the source decoding/normalization and regenerate"*.
The repeated UTF-8-read-as-cp1252 chain is reversible and is now reversed —
`Ã‚Â½` → `½`, `Ã‚Â°C` → `°C`, `SELFÃ‚Â·` → `SELF·`. But **116 of 1,212
affected cells recover and 1,096 (90.4%) do not**, because they are not a pure
re-encoding chain: characters have been *substituted*. The dominant residue is
`Ã¢Â‚¬Â„¢` standing for a single `'`, where the `â` of a well-formed triple
mojibake has become `Â`. And Codex's own example is the clearest case: `2Â€?`
carries a literal `?` where a character was destroyed upstream. **You cannot
re-decode information that is gone.**

So the remedy is proportionate rather than complete. What repairs is repaired;
what does not now **scores as empty**, so the sampler prefers a clean row —
which also fixes the reason a corrupt row was *preferred* in the first place,
namely that a long mojibake description looked like a well-filled cell. 98.4%
of subaward rows are unaffected and a ten-row showcase should not spend one of
them on corruption. **No row is dropped from the dataset and no money column
is touched.** The counts ship in `samples/README.md`.

## Two findings this side brought in round 4

### `gaming_facilities.csv` contains seven rows that say there is no facility

Every "of 787" figure in this document — including two Codex used — divides by
a denominator that includes **seven rows whose `facility_name` is literally
`No casino`**:

    VP-0242  Havasupai        AZ        VP-0254  Zuni               NM
    VP-0243  Hopi             AZ        VP-0336  Pueblo of Zia      NM
    VP-0102  Quartz Valley    CA        VP-0337  Pueblo of Cochiti  NM
                                        VP-0338  Pueblo of Picuris  NM

These are not facilities and not duplicates. They are placeholders recording
that a nation does **not** operate a casino, shipped in the facility table as
though they were casinos. **787 rows, 780 facilities.**

They surfaced from the other half of this finding. A dedupe review,
`review/gaming_facility_duplicate_candidates_2026-09-02.csv`, proposes 56
duplicate groups, and **collapsing the 52 marked `LIKELY_SAME_PROPERTY` gives
exactly 734** — the figure now circulating as the true facility count. It
should not be adopted yet, for three measured reasons:

1. **No verdict has been applied.** All 56 rows carry `verdict_needed`, and
   the live table has `duplicate_of_facility_id` populated on **10 rows**, not
   59. 787 is what ships.
2. **Four groups are cross-tribe and must not be collapsed** — the file says
   so itself with `DIFFERENT_TRIBES_CHECK_BOTH`. `7 Clans First Council` pairs
   Otoe-Missouria with the Ponca Tribe; `Stables Casino` pairs the Miami Tribe
   with Modoc Nation, which is a **joint operation**, not a duplicate — the
   same fact pattern as Codex's round-2 finding 5.
3. **Two of the 56 groups are a normalisation artefact**: the grouper reduced
   `No casino` to the token `NO` and grouped Havasupai with Hopi, and four
   Pueblos with each other. That is how the seven placeholder rows were found.

So: **787 ships, 780 are facilities, 734 is a proposal with four exceptions
and two artefacts in it.** Stated rather than adopted.

**And the denominator was already wrong in customer-facing copy, which Codex
round 5 caught before it shipped further.** The `gaming` descriptor said
*"one row per facility, with the single non-facility row named"* — there are
seven — and advertised *"694 of 787 facilities carry a bounded revenue
estimate ... which of the 93 it cannot bound"*. Re-measured: **694 rows carry
a bounded estimate and 86 facility rows do not, not 93** — all seven
placeholders sat in the unbounded group and inflated it.

**But swapping 787 for 780 is not the fix, and the first version of this
correction did exactly that.** Two independent revisions are in flight on the
same denominator and they compound:

    787   rows in gaming_facilities.csv
    -7    placeholder rows that say there is no casino
    ---
    780   facility rows
    -53   the extra rows in 52 same-tribe duplicate groups, PROPOSED
    ---
    727   distinct properties, pending adjudication

**They are independent** — measured, not assumed: **zero** of the seven
placeholders appear in any of the 52 same-tribe groups (six appear in the
cross-tribe groups, which is how the placeholders were found). So the two
corrections do not overlap and both apply.

**Which makes 734 a partial correction, not the answer.** 734 is 787 − 53: it
removes the duplicates and leaves the placeholders in. The number it is
offered as a replacement for, 787, is wrong in two ways, and 734 fixes one of
them.

Nothing is merged. `duplicate_of_facility_id` is blank on all but ten rows, a
casino and its hotel can legitimately be two facilities, and four groups span
different nations. **So the descriptor now publishes no percentage for revenue
bounding at all** — a rate against a denominator under active revision in two
directions is a number that will be wrong twice. It states the ladder instead:
787 rows, 780 facility rows, ~727 distinct properties pending 56 groups.

### Claims re-measured against live data, and one that is already done

- **`nest`** — 1,610 enterprises, **977 (60.7%) with `in_federal_contracting =
  N`**, confirmed to the row. It already **has** a sample (`nest__sample.csv`,
  10 rows, 17 columns) and full editorial copy; the brief asking for both is
  describing a gap that was closed on the previous push.
- **`natural-resources` is aggregate by publisher, not by our failure** —
  `national_aggregate` 9,791 + `state_aggregate` 167 = **9,958 of 11,305
  (88.1%)**, against `entity_specific` 779 and `per_headright_rate` 508. The
  figure in circulation is 87%; measured today it is 88.1%.
- **`deals`** — 1,073 rows, up from 935 when this branch opened.

## Why the samples moved more than the fixes explain

Fixing finding 2 needed the generator to run, and it could not. `770` loaded
each source table whole; `prime_contracts.csv` is 1.46 GB across 75 columns,
which is roughly 10 GB of Python objects on a machine with **16.4 GB of RAM
and 1.6 GB free** with ten other jobs writing. A run that used to take seven
minutes for all fourteen datasets spent **over thirty on `contractors` alone**
and then died with an empty log — swapping, not computing.

Large tables are now sampled in **two streaming passes** and never held: pass
one keeps a one-byte completeness score per publishable row (1.2 MB for 1.2 M
rows, against ~10 GB for the dicts); pass two lifts only the ten wanted rows.
Small tables keep the original in-memory path unchanged, so nothing that
already worked changed shape.

**The claim that the two engines agree is asserted, not stated.**
`py -3 code/770_sample_extracts.py proveequal <table>` runs both on the same
file and exits 1 unless the sampled rows match cell for cell. It passes on
`nest_enterprises` (1.9 MB), `native_owned_businesses` (6.0 MB), `np_orgs`
(13.7 MB), `nagpra_notices` (10.8 MB) and `subawards` (82.7 MB).

**And the first version of it shipped a five-row sample.** `contractors` came
out with 5 rows of 10, because pass two indexed against pass one's positions
and a concurrent enricher rewrote `prime_contracts.csv` between the reads —
same row count, different publishable rows, so five wanted positions no longer
held a row that passed the gate. **A short sample is the quiet failure: it
looks like a small table, not a race.**

*The first repair for that was a strided spare buffer that topped the sample
back up to ten and printed a `RACED` line. **That is no longer what happens
and this paragraph described it as current until Codex round 5 caught it.***
Codex round 4 showed the top-up was wrong in two ways — it produced a
mixed-version sample, and it could not detect the case that matters — and it
was replaced by stamp-and-retry. The current behaviour is described under
*Codex round 4* above: both passes are discarded and re-drawn from a fresh
snapshot, and after three attempts the generator raises rather than publish.

**Widening the collection was not done here, on purpose.** It adds four tables
with no declared grain and no declared key (`native_owned_businesses.csv`
2,916, `native_business_contract_links.csv` 2,393,
`native_business_identifier_crosswalk.csv` 481,
`native_business_contracting_by_nation.csv` 18) and it moves a dataset's
readiness, which is an integrator and owner decision rather than this
workstream's. It is filed with this evidence in the data project's decision
queue, and declared in ADR-018.

Two things checked and found clean while chasing it. The same invariant across
all fourteen collections finds **1 violation, not a class**: 13 flagship
tables are claimed by their own collection and every other row count exceeds
its flagship. And `_entity_layer` is exempt from the membership half rather
than passed by luck — its flagship `cedar_identity_register.csv` lives in
`data/spine/`, outside the contract by construction, and clears the arithmetic
half at 1,555 rows against 326,899.

**One measurement retracted before it was reported.** Two consecutive runs of
`770` first appeared to produce different `legislation` samples, which would
have meant a non-deterministic sampler. Re-run with the input mtimes captured
either side: **byte-identical across all fourteen samples**, and the input
`bill_votes.csv` had been rewritten by a concurrent job between the first two
runs. The sampler is deterministic; the first check was measuring something
other than its own name.

## Codex round 2 (PR #29): eight findings, eight measured

All eight were right on the facts. Six were larger than the sampled row
showed, one needed the opposite repair to the one suggested, and one was right
in principle and disproportionate in remedy.

| # | finding | measured scope | what changed |
|---|---|---|---|
| 1 | `CollectionDataset(**d)` fails on `cedar` / `needs_copy` | **0 of 13** constructed | descriptor is now exactly the dataclass; Cedar's facts move to a sibling file; the claim is a check |
| 2 | one Old Harbor award credited to Three Affiliated | **4,947 rows, $449,376,831.04** | repointed at source and in five materialised tables, with row and money conservation proved to the cent |
| 3 | C4 blocker removed while the README says 42% | the README was the stale half | README corrected; blocker stays removed; measurement change explained above |
| 4 | self-referential `parent_contract_number` | **156,592 rows (12.86%)**, two distinct causes | cleared in place; the fabricating fallback removed from the generator |
| 5 | a jointly run casino exposes one operator | **1 of 787 rows** (see the denominator note below) | `operating_entity_cedar_uids` + `n_operating_entities` on the table and in the sample |
| 6 | notice-type text inside an institution name | **966 rows**; distinct institutions 2,184 → 1,798 | parser fixed at source; 6 residual colon names flagged, not stripped |
| 7 | `owned` has no `owned__sample.csv` | 1 of 14 ids | the sample filename is the product id, and the two maps now fail a check if they drift |
| 8 | one notice's institutions all get Yale's address | **392 notices** name >1 institution | `nagpra_notice_institutions.csv`, 7,234 rows, one per (notice, institution), each with its own city and state |

### Finding 2 in full, because it is the one that moves money

Old Harbor Native Corporation is an Alutiiq **village corporation on Kodiak
Island, Alaska**. The Three Affiliated Tribes — Mandan, Hidatsa and Arikara —
are in **North Dakota**. Codex sampled one row where the second was credited
with the first's award. Measured across the table it is 4,947 rows on two
awardee UEIs — `AMEE BAY, LLC` (3,592 rows, $295,915,554.72) and `OCEAN BAY
INFORMATION AND SYSTEMS MANAGEMENT` (1,355 rows, $153,461,276.32).

This is the United Keetoowah Band shape again ($181.9M, fixed the day before),
and as there the row disagrees with **itself**, so nothing was decided on a
name:

1. 2,341 of them carry `parent_uei = K3N7G5L6GRY6`, and **629 other rows with
   that same parent UEI are keyed to Old Harbor at tier A**. One parent UEI,
   two nations, one table.
2. A further 374 name the intermediate holding company, `THREE SAINTS BAY LLC`
   — the historic site beside Old Harbor on Kodiak Island.
3. **All 4,947 are `recipient_state_code = AK`.** Three Affiliated's other
   7,544 rows are IL 3,486 / ND 2,575 / TX 675 / GA 226 / MT 188.
4. The sibling firms Rolling Bay, Barling Bay and Shearwater Systems are keyed
   to Old Harbor at **tier A by an owner ruling**; the two disputed firms are
   keyed to Three Affiliated at **tier B by `cluster_v3`**, whose own rationale
   column reads *"Algorithmic name clustering, unreviewed."*

The cluster's token was `Three`, and it also swept up `Three Guys Garage,
Inc.`, `THREE BEES OF VIRGINIA L.L.C.`, `Three Fires Development Group` (an
Anishinaabe term) and `Three Sisters Federal`. **Those were flagged, not
moved** — none of them contradicts itself, and repointing an identifier on a
name pattern is the mistake being fixed, in the other direction.

Two neighbouring populations were checked and deliberately left alone, because
they do not share the cause: 137 rows of `OLD HARBOR SOLUTIONS LLC` keyed to
Alutiiq/Koniag, whose FPDS parent chain never touches Old Harbor Native
Corporation and whose current key is not implausible (Koniag is the regional
corporation for the archipelago that contains the village); and 292
`unattributed` rows, $66.4M, whose parent is Old Harbor Native Corporation but
whose only route to a key would be through the parent's *name* — a weaker
claim than the four above. Unresolved is a legitimate outcome.

After: rows 1,217,768 → 1,217,768, columns 70 → 70, table total
$310,005,258,661.21 → $310,005,258,661.21, and **exactly two** `cedar_uid`
totals changed, by equal and opposite amounts.

### Finding 5, and why it is a column rather than a bridge

The Stables Casino is jointly run by the Miami Tribe of Oklahoma and the Modoc
Nation, and Cedar exposed one of them. Correct — and it is **1 facility of
787**, which is the whole argument for the shape of the fix. A
facility-to-tribe bridge is the right architecture and the wrong instrument
for two rows: it would add a third shipped table to `gaming` and with it a
declared grain, a validated key and row-conservation coverage to maintain. The
multi-valued column carries the same information at the grain the dataset
already has, and `n_operating_entities` is the column that will say when a
bridge has become the right answer.

Worth naming because the obvious generalisation is worse than the bug:
splitting `tribe` on the usual separators finds **58 of 787** facilities, and
**57 are false** — `&`, ` and ` and `,` all occur inside single tribes' own
legal names (*Assiniboine and Sioux Tribes of the Fort Peck Indian
Reservation*, *Confederated Salish & Kootenai Tribes*, *Grand Traverse Band of
Ottawa and Chippewa Indians*). `/` is the only separator in that column that
separates operators, it occurs once, and that is the rule applied.

### Finding 8 was worse than reported, in two ways the sample could not show

The notice Codex pointed at names six institutions across SC, NC and CT.
`institution_count` said **4**. And `institution_names_all`, the column meant
to carry them all, split on `, and ` — which is a *within-name* separator in
ordinary American organisation names — and turned *South Carolina Department
of Parks, Recreation, and Tourism* into two entries, one of them `Tourism,
Columbia, SC`. **An institution that does not exist**, produced by the column
that was supposed to solve the reported problem. The Federal Register
separates co-holders with `; `, which the parser never split on at all.

`nagpra_notice_institutions.csv` now carries one row per (notice,
institution): 7,234 rows over 6,792 notices, 7,087 with a state, 392 notices
naming more than one holder. Every name, city and state in it is a substring
of that notice's own Federal Register title — the check that asserts so exits
1 rather than writing. `institution_city` and `institution_state` on the
notice row are now the **primary** institution's and are incomplete by
construction where the count is above 1, which the codebook says rather than
the row pretending otherwise.
