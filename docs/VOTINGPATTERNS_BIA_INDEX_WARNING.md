# Warning: the BIA compact index is misaligned at source

*Found 2026-08-05 during the Cedar Press compacts build. Flagged, not fixed upstream.*

## What is wrong

The BIA Office of Indian Gaming compact index page has its **`Tribes` column
misaligned with its `Title` column on 61 of 1,189 rows (5.1%)**. This was verified
against the archived raw HTML, so it is BIA's own error, not a scraping or parsing
artifact.

Examples:

| Compact (from Title) | BIA's `Tribes` column says |
|---|---|
| Mohegan | Mississippi Band of Choctaw Indians |
| Mashpee Wampanoag | Mashantucket Pequot |
| Miami Tribe | Kialegee Tribal Town |
| Yurok | Yocha Dehe |

## Why it matters here

Any dataset that took the tribe from that index inherited the misalignment. On the
Desktop that includes, at minimum:

- `votingpatterns/data/processed/compact_master_aiannh.csv` (1,242 compact-AIANNH rows)
- `votingpatterns/data/processed/tribe_compact_history.csv` (266 tribes)
- `votingpatterns/data/processed/tribe_year_compact_panel.csv` (272 AIANNHs, 1990-2030)
- `votingpatterns/data/processed/bia_compact_content_v2.csv`

`votingpatterns/README.md` designates the first three as **cross-project authoritative**
and instructs other projects to consume them rather than rebuild. So the error can
propagate into anything that joined compacts to tribes through them — including
dissertation Ch3 heterogeneity work using compact attributes.

**Scale:** roughly 5% of compact-to-tribe joins may point at the wrong tribe. Whether
that is material depends on whether the affected tribes are in the analysis sample; it
is not a reason to assume results are wrong, only a reason to check.

## How Cedar Press handled it

`data/clean/compacts.csv` takes the tribe from the **Title** where it conflicts with the
`Tribes` column and is corroborated by the PDF filename. BIA's original value is
preserved in `bia_tribes_column` with a conflict flag, so nothing is silently
overwritten and the disagreement stays auditable.

## What has NOT been done

**Nothing in `votingpatterns/` has been modified.** Per the standing rule to flag
conflicts rather than silently resolve them, and because those files feed dissertation
work, the correction has not been written back upstream. That is Elijah's call.

If a back-fix is wanted, the safe form is a new sidecar file listing the 61 affected
rows with both the BIA value and the corrected value, rather than an edit to the
existing CSVs.

---

# Second defect: `tier2A_agent_verified_real` mislabels derived revenue

*Found 2026-08-05 during the Cedar Press gaming build.*

In `votingpatterns/data/processed/published_tribal_gaming_revenue_v3_audited.csv`, the
tier label `tier2A_agent_verified_real` reads as "this revenue figure is real and
verified." It is not what the tier actually certifies. It certifies that a **payment**
was verified — not that revenue was **reported**.

**372 of the 435 rows carrying that label are compact-rate inversions**: a state
revenue-sharing payment divided by the compact's sharing rate to back out an implied
revenue figure. That is a derived estimate, not a disclosure.

The regression is documented in the files themselves: the **v2 vintage labeled these
honestly** as `tier2b_reverse_engineered`. The later audit pass overwrote that with the
`_verified_real` label. So the audit made the provenance *less* accurate, not more.

**Why it matters:** tribal gaming revenue is largely non-disclosed. A dataset that
appears to carry 435 verified revenue figures, when 372 are inversions of payment data,
would overstate what is knowable about the industry — and the error is invisible
downstream because the label says "verified real."

**How Cedar Press handled it:** `gaming_facilities.csv` derives `value_basis` from the
metric itself (reported | payments_derived | modelled | reverse_engineered), never from
the upstream tier label. Result: of 592 gaming-revenue observations, only **126 (21%)
are reported revenue** — essentially Connecticut slot win.

---

# Third defect: the BIA gaming-decisions index has the same column misalignment

The `Tribe(s)` column is misaligned with `Title` on **3 of 138 rows (2.2%)** on
`bia.gov/as-ia/oig/gaming-land-decisions`:

| Decision (from Title) | BIA's `Tribe(s)` column says |
|---|---|
| Graton | Ewiiaapaayp |
| Tunica-Biloxi | Tonawanda Band of Seneca |
| Saint Regis Mohawk | Rappahannock |

This is the **same failure mode as the compact index**, on a different BIA page. Two
independent indexes with identical structural breakage points at a CMS-level problem
rather than one bad page — so **any future BIA index scrape should be assumed to have
it until checked.**

Cedar Press preserves BIA's value verbatim, flags the conflict, and stores a
title-derived candidate alongside.

---

## To reproduce

The 61 conflicts are recoverable from `Cedar Press/data/clean/compacts.csv` by
filtering on the conflict flag; the archived raw BIA HTML is in
`Cedar Press/data/raw/external/compacts/`.
