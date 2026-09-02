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

## What is here

**`collection_descriptors.json`** — one object per dataset in the
`CollectionDataset` shape. `id`, `shelf`, `level`, `rows_label`, `n_rows`,
`n_tables`, `vintage`, `updated`, `cedar_status`, plus the editorial fields
`name`, `short_name`, `tracks`, `sources`, `method`.

`downloads` is deliberately **absent**: it is a product metric that belongs in
the platform database, and the data side has no business inventing it.

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
- **Columns are curated too.** `gaming_facilities` carries 105 columns, nine of
  them blank throughout, and every metric repeats four times as value /
  value_basis / observation_status / observed_date. That provenance is right to
  keep in the table and wrong to open a sample with. Nothing was removed from
  the datasets — only from these ten-row views.
- **Spread, not `head()`.** First-ten returns one agency in one year and makes
  a dataset look narrow. Rows prefer completeness, then sample evenly.
- **Publishable rows only.** `publishable = N` and any
  `TERMS_STATED_RESTRICTIVE` source never appear — Navajo's 346 NBOA rows are
  absent here exactly as they are absent from a release. Verified on the
  native-owned-businesses sample: 10 of 10 `publishable = Y`, no restricted
  source present.
- **No natural persons.** A table carrying an owner name, email, phone or
  address is refused outright rather than filtered.

## One thing that reads as a bug and is not

In `gaming__sample.csv`, Keex Kwan Gaming shows `property_status = current`
with `close_date = 2006-04`. **Both are correct.** 113 of 787 facilities carry
a past close date while currently operating — Casino Morongo closed in 2010 and
Chukchansi Gold in 2014, and both reopened and are open today.

The data is honest and the *schema* reads badly: one `close_date` column cannot
distinguish "closed permanently" from "closed once, since reopened." Flagged on
the data side. It is exactly the kind of thing only a person looking at rows
finds, which is the argument for these files existing.

## Before totalling any money column

`docs/MONEY_TOTALLING_RULES.md` in the data project is the authority. The three
that bite hardest:

- **`subaward_amount` summed unfiltered gives $45.62B against a correct
  $24.41B — a 46.5% overstatement.** Filter to `duplicate_status = 'primary'`
  and `subaward_exceeds_prime_flag != 'yes'`.
- **`owner_obligations_usd` sums to $6,535.96B against a true $176.74B**, a
  36.98× inflation: owner-grain attributes repeat on every operating-company
  row. `firm_*` is the additive family.
- **A subaward is a slice of a prime award.** Never add subcontracting to
  contracting.

## Status of the thirteen

4 of 13 are READY against the data project's production contract
(`contractors`, `federal-register`, `nagpra`, `native-owned-businesses`); the
rest carry named blockers. `cedar_status` on each descriptor says which. A
BLOCKED dataset is not unusable — it means a specific contract point is not yet
met, and the blocker is named rather than smoothed over.
