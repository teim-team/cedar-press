# The twelve in git: one dataset per category, as the sanity check

*Owner, 2026-09-02: "the point of the dataset — one dataset per category in git —
is that it's a good sanity check, my North Star."*

`dist/preview/` holds **one file per Cedar Press category**, 100 real rows each,
and those twelve files are tracked in git. 228 KB total. That is deliberate: a
dataset you can open in a diff is a faster signal than a failing test, and it is
a signal about the thing customers actually receive rather than about the
machinery.

## Why these twelve and not the real ones

The full datasets are on disk in `dist/customer/` and are **not** tracked.
`contractors.csv` alone is 1.6 GB and GitHub refuses any file over 100 MB. So
git carries the previews and the disk carries the product.

That split is fine for a sanity check and dangerous if forgotten, because the
preview is a **curated 7-11 columns** while the delivered file is 43-309. A
preview can look perfect while the delivered file ships a lineage column or a
superseded row. Both were true this week.

## What the sanity check catches, and what it cannot

**Catches** — a category whose rows are all one entity, a column of blanks, an
identifier where a name should be, a money column that is obviously wrong, a
dataset that silently lost its rows. All of those show up in a diff of 100 rows.

**Cannot catch** — anything the curation removed. Publication state, provenance,
adjudication flags, duplicate status. `dist/preview` is chosen for readability,
so a defect in a column it does not carry is invisible here by construction.
That is what `1152`'s reconciliation and `1153`'s eligibility policy are for.

Both were live examples on 2026-09-02: the previews looked clean while the
delivered files carried 1,064 superseded lobbying filings, 9,223 contradicted
contractor attributions and `built_by_script` on 4,000 rows.

## How to read a change

```
git diff dist/preview/
```

A row count that moved, a column that appeared or vanished, a nation that took
over a file. If a preview changes and you cannot say why, that is the signal —
`review/QA_RECONCILIATION_*.csv` and `docs/PUBLICATION_ELIGIBILITY.md` say what
the last pass changed and why.

## The rule that keeps this honest

The previews are **generated, never edited** — `code/1151_customer_preview_ten.py`,
from the delivered files, on every build. Rows are chosen to maximise distinct
subjects rather than taken from the top, because `head(100)` returns one agency,
one year, one nation and makes a broad dataset look narrow. No value is
reformatted: every cell is exactly what the delivered file holds. A preview that
tidies its rows is a lie about the product, and the first thing a buyer does
with the real file is discover it.
