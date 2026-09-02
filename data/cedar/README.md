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
  external project. Today every dataset's list is empty — see *Status of the
  fourteen*.

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
  not Cedar's name for the entity. **Group on `cedar_uid`.** On 345,180 of
  552,602 keyed rows the two disagree, and the overwhelming majority of those
  are a right identity wearing a stale label. See the correction below.

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
NM}`. It is not a Cedar name at all. Of 552,602 rows carrying a `cedar_uid`,
345,108 disagree with the register's name, and **339,129 of those — 98.3%,
$94.0B — are explained entirely by that legacy reconciliation: right identity,
stale label.** The register even records the reconciliation, and it holds the
real sub-hubs separately and uses them correctly when the recipient genuinely
is the school (Blackfeet Community College, `CE-0010N-2P`, 312 rows).

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
past `close_date`. **Both are correct.** 113 of 787 facilities carry a past
close date while currently operating — Casino Morongo closed in 2010 and
Chukchansi Gold in 2014, and both reopened and are open today.

The data is honest and the *schema* reads badly: one `close_date` column cannot
distinguish "closed permanently" from "closed once, since reopened." Flagged on
the data side.

## Status of the fourteen

**14 of 14 are READY** against the data project's production contract, up from
4 when this branch first opened and 11 a day ago. The fourteenth, `nest`
(tribally owned enterprises), landed while this branch was open and ships with
a sample like the rest. Regenerate the scoreboard with
`py -3 code/518_dataset_readiness.py`; there are three statuses and no fourth.

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

A BLOCKED dataset would not be unusable; it would mean a specific contract
point is unmet, and which one is printed. None is blocked today.

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
| 5 | a jointly run casino exposes one operator | **1 of 787** facilities | `operating_entity_cedar_uids` + `n_operating_entities` on the table and in the sample |
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
