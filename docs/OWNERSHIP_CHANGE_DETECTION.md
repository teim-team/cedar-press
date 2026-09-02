# Ownership Change Detection

*A note, not yet a build. Written 2026-08-06.*

Elijah:

> "if we are good at tracking deals we should be able to reliably link owners to
> firms, or how they change over time — and we may also be able to use the
> contracting data to get deals not listed but we can see."

Both halves are right, and the second half is the new one. This note records the
method and, more importantly, the four things that will make it lie if they are
not handled.

---

## The two directions

**Direction A — deals fix the contracting data.**
FPDS **does not update retroactively when ownership changes**. A firm acquired
in 2024 keeps its 2019 parent on every historical row. The deals ledger records
dated ownership events (Chenega buys SecuriGence 6/2024; sells CFS 4/2025;
BSNC buys Alakaʻina 2026). Joining deal dates to the crosswalk makes attribution
**time-aware** — the thing this project already knew it had, and the reason the
deals ledger is the missing time-varying ownership source.

**Direction B — contracting finds deals nobody reported.**
A firm's `parent_uei` changing between fiscal years is an ownership-change
*signal*, visible whether or not anyone published a press release. Small tribal
acquisitions rarely get written up. The contracting file sees them anyway.

The two are complementary, not redundant: **contracting DETECTS the event,
deals DATES it.**

---

## Measured, 2026-08-06, on `prime_contracts.csv`

| | |
|---|---:|
| Distinct awardee UEIs carrying parent data | 12,121 |
| UEIs whose `parent_uei` changes over time | **488 (4.0%)** |
| …with clean, non-overlapping year ranges | **173** |

Recognisable names in the clean set: Cherokee General Corporation, **Flintco**
(Muscogee Creek Nation), Portage Environmental, Paragon Systems, Arrowhead Space
and Telecommunications.

Transitions by the year the new parent first appears:

```
2011  6   2015  9   2019 13
2012  4   2016 18   2020 20
2013 16   2017 15   2021 16
2014  9   2018 16   2022 37   <-- contaminated
```

**Spread across twelve years, which is the important result.** Had they piled
into one year it would be a re-identification artefact rather than real
ownership change.

---

## The four things that will make this lie

**1. The observed date is not the transaction date.** Because FPDS does not
update retroactively, the new parent appears only on transactions issued after
the SAM registration was updated. That lag can be years. So a detected
transition gives a **lower bound on when it was recorded**, never a deal date.
The deals ledger supplies the date; the detection supplies the lead.

**2. FY2022 is contaminated and must be discounted.** 37 transitions against a
~15/year baseline. **DUNS was retired and replaced by the UEI on 2022-04-04** —
a mass re-identification event that manufactures parent changes where no
ownership changed at all. Treat 2022 transitions as suspect by default and
require a second leg. This is already recorded in `series_breaks.csv`.

**3. A parent change is not a sale.** It can equally be a re-registration, an
internal restructuring, a data correction, or the *parent's own* identifier
changing while ownership stayed put. The signal says "something happened to this
firm's declared parentage," which is a narrower claim than it looks.

**4. It detects; it does not establish.** Per the standing rule in `AGENTS.md`
(*"we own the TOP, the tribe owns the INSIDE"*), a federal parent field is
**evidence, not authority**. A detected transition is a candidate for a ruling,
never a published ownership event on its own.

---

## What a build would look like

1. Extract every clean `parent_uei` transition per awardee UEI, with the year
   ranges on both sides, dollars either side, and a `duns_uei_migration_risk`
   flag for anything crossing 2022.
2. Join to `data/clean/ownership_events.csv` (98 rows) and the `deals_*`
   ledger.
3. Three outcomes, all of them useful:
   - **CORROBORATED** — a deal we already hold. Validates both sources and
     dates the transition properly.
   - **UNDOCUMENTED CANDIDATE** — a transition with no deal on file. **This is
     the product**: a possible acquisition nobody reported. Research it.
   - **DEAL WITHOUT A SIGNAL** — a deal we hold that produced no parentage
     change. Also informative: an asset purchase, a minority stake, or FPDS
     simply never updated.
4. Everything goes to `review/` for a ruling. Nothing publishes as an ownership
   event on detection alone.

## Why it is worth building

It runs entirely on data already on disk, it targets exactly the firms whose
ownership the federal record gets wrong, and its failure mode is a research
queue rather than a false attribution. The same test should then run against
`federal_funding_transactions.csv` and `subawards.csv`, which carry the same
identifier fields.
