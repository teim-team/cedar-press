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
it `owned`. It is mapped now, and `owned` is what ships.

## What is here

**`collection_descriptors.json`** — one object per dataset, contract-exact
against the `CollectionDataset` dataclass on `main`. Verified, not assumed:
13 of 13 deserialize with `CollectionDataset(**descriptor)`, no missing
required field and no unsupported extra.

- The dataclass fields are at the top level: `id`, `name`, `short_name`,
  `origin`, `level`, `tracks`, `rows_label`, `downloads`, `vintage`,
  `version`, `updated`, `sources`, `method`, `shelf`.
- Cedar's own facts live under a namespaced **`cedar`** key the dataclass never
  sees: `cedar_id`, `status`, `blockers`, `n_rows`, `n_tables`.
- `downloads` is present and **`0`** — a platform metric Cedar has no business
  inventing, so it says "not counted here" rather than fabricating a count.
  `version` is `v0`; the platform owns bumping it.
- `blockers` carries the **named** contract points rather than the bare word
  `BLOCKED`, so a consumer can tell a publication-rights block from an
  incomplete schema without opening an external project.

**`samples/*.csv`** — 10 real rows per dataset, 13 datasets. Not drafts of the
full tables; proof of concept, so the finished shape can be judged before the
datasets are finished.

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

- **`prime_contracts.contract_number`** is the awarding PIID, and on 290,525
  rows (23.9%) it is a modification stub — `0098`, `0006`, `SBA0001` —
  meaningless without the IDV it references. Four of ten sampled rows showed
  one. **`parent_contract_number` now ships beside it, and the pair is the
  key.** They are complementary and the cross-tab has an empty cell exactly
  where it matters: 664,470 rows carry a real parent and a full child PIID,
  290,525 a real parent and a stub, 262,773 no parent and a complete
  standalone PIID, and **zero rows have neither**.

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

## Status of the thirteen

**11 of 13 are READY** against the data project's production contract, up from
4 when this branch first opened: `_entity_layer`, `contractors`, `deals`,
`federal-register`, `gaming`, `legislation`, `lobbying`, `nagpra`, `owned`,
`natural-resources`, `nonprofits`.

Two are BLOCKED, and the blocker is named on each descriptor rather than
smoothed over. Both fail on the same shape — an unstated grain, no validated
primary key, literal duplicates, a money column a buyer cannot safely total,
and under half of entity-bearing rows carrying a Cedar id:

- **`subcontracting`** — `subawards.csv`: grain UNSTATED, 10,770 literal
  duplicates, 42% of entity-bearing rows keyed.
- **`funding`** — `faads_transactions_all_agencies.csv` and
  `native_passthrough.csv`: grain UNSTATED on both, 3,441 and 116 literal
  duplicates, 40% of entity-bearing rows keyed.

A BLOCKED dataset is not unusable. It means a specific contract point is not
yet met, and which one is printed.
