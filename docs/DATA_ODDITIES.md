# Data Oddities

*What a zero, a negative, or a blank actually means in each dataset.*

Elijah, 2026-08-06: *"there should be some question mark on certain fields —
what a negative value means or 0 etc, since all these datasets have oddities in
them."*

Right, and they are not rare. Nearly 10% of contract rows are negative. A
subscriber who filters them out loses real information; one who sums them
without understanding gets a number that is correct and misleading at the same
time. Every figure below is measured, not estimated.

---

## The three values that are not missing data

| Value | Means | Never |
|---|---|---|
| **Negative** | Money was **taken back**. A deobligation, a cancelled option year, a corrected overstatement. | Not an error. Not a data-quality problem. |
| **Zero** | An action occurred that **moved no money** — a period-of-performance change, an address correction, an administrative modification. | Not a missing value. |
| **Blank** | **Not reported.** The field was left empty at source. | Not zero. |

The distinction between zero and blank is the one that gets lost. Zero is an
assertion; blank is a silence.

---

## Prime contracting

| Field | Zero | Negative | Blank |
|---|---:|---:|---:|
| `total_obligations` | 61,028 (9.9%) | **59,794 (9.7%)** | 0 |
| `total_award_value` | 17,165 (2.8%) | 656 (0.1%) | 0 |

**The negatives are deobligations and they belong in the total.** A contract
obligated $10M in FY2019 and deobligated $2M in FY2021 has moved $8M. Dropping
the negative row reports $10M, which is wrong. One −$167.2M Bureau of
Reclamation row once made an entire agency-year net negative — that is the
system working, not breaking.

**A negative `total_award_value` (656 rows) is different and is probably an
error at source.** An award ceiling cannot be below zero. Flagged, not
corrected, because we cannot know the intended value.

**Two money columns behave in opposite ways.** `total_obligations` is
transactional and must be SUMMED. `total_award_value` is restated on every
transaction of the same contract — N6871197C3726 carries 745,240 on both its
FY2000 and FY2001 rows — and must be MAXed. Summing it double-counts. This is
why `prime_contracts_awards.csv` exists.

**5,759 contracts carry a cumulative-snapshot signature** — 390 repeat an
identical non-zero obligation on every row, 5,369 rise monotonically. Both are
the pattern that inflates USAspending award data ~2.2× when summed. Flagged in
`cumulative_snapshot_flag`, retained rather than dropped.

---

## Federal funding

| Field | Zero | Negative | Blank |
|---|---:|---:|---:|
| `obligated_usd` | 55,698 (11.7%) | 25,099 (5.3%) | 0 |

Same reading: negatives are deobligations, zeros are non-monetary actions.

**Credit programmes report `obligated_usd` as exactly 0.00 by design.**
Assistance types 07 (direct loan), 08 (guaranteed loan) and 09 (insurance)
carry their value in `total_face_value_of_loan` and
`original_loan_subsidy_cost`. A zero there is not an absence of money — it is
money in a different column. **And a loan guarantee is not federal outlay**: the
face value is the borrower's principal, the subsidy cost is what it costs the
government. Adding face value to grant obligations overstates federal spending
by the entire principal.

`total_face_value_of_loan` is also **award-cumulative and signed**. Six rows
sum to $271.4M against a true $171.4M.

---

## Subcontracting — the messiest, and Elijah is right about it

| Field | Zero | Negative | Blank |
|---|---:|---:|---:|
| `subaward_amount` | 1,352 (2.5%) | 296 (0.5%) | 0 |
| `prime_award_amount` | 238 (0.4%) | 49 (0.1%) | **3,424** |

His read — *"we can at least say who did subcontracting work, the values might
be wonky"* — is the correct use of this dataset, and here is why:

**5,941 rows report a subaward LARGER than its own prime award.** The worst is a
prime award of **$64,910.88** reporting a subaward of **$794,526,041** — 12,240×,
for "asphalt and stripe parking spaces." Among Native-linked rows, **17 rows
carry 54.6% of the dollars.**

FSRS is **self-reported by the prime contractor** with no validation at
submission. So:

> **The subcontracting dataset is reliable about RELATIONSHIPS and unreliable
> about AMOUNTS.** Who subcontracted to whom, on which prime award, in which
> year — that is solid. The dollar figure needs two filters before it can be
> summed: `duplicate_status == 'primary'` AND
> `subaward_exceeds_prime_flag != 'yes'`. Applying them removes 492 rows and
> $5.96B — a quarter of the unfiltered total.

**3,424 blank `prime_award_amount` values** are why the ratio test cannot run on
every row; those rows are neither confirmed nor flagged.

---

## Lobbying

`spend_usd` of 0 is common and usually **truthful**: a registrant files a
quarterly report with no reportable activity. It is not missing data.

Reported spend is a **good-faith estimate rounded to the nearest $10,000** under
the LDA. A total printed to the dollar implies precision the source does not
have.

Income and expenses are **either/or, not both**: outside registrants report
income, self-filers report expenses. Only one is populated on any given filing,
so `expenses_usd` being 0.9% filled is correct.

---

## Nonprofits

A 990-N filer (the e-postcard, under the filing threshold) reports **no
financial detail at all**. `lobbying_expenditure` and `n_employees` at 0% filled
is the filing regime, not a gap — 6,453 of 12,764 organisations are 990-N.

---

## The general rule

**Never filter an oddity out silently.** Flag it, count it, explain it, and let
the consumer decide. Every exclusion above is available as a column, so a
subscriber can reproduce our totals or disagree with them — which is what makes
a number auditable rather than merely published.
