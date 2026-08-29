# Coverage Expansion Options

*Where each dataset could reach beyond the published window, what it would cost, and
what would break. Maintained so subscriber demand can be answered with a real estimate
instead of a guess.*

*Created 2026-08-05. Standing policy: temporal floor is 2000; see STATE_OF_BUILD.md.*

---

## Why this file exists

Elijah set the 2000 floor for consistency and source quality. But several datasets
*could* go deeper, and some can't reach 2000 at all. When a subscriber asks "does this
go back further?", the answer should be a scoped estimate, not an improvisation.

Two distinct questions per dataset:
- **Deeper** — can we go earlier than 2000, and is it worth it?
- **Shallower** — does it fail to reach 2000, and can that be fixed?

---

## Datasets that could go DEEPER than 2000

| Dataset | Already have | Could reach | Cost | Verdict |
|---|---|---|---|---|
| **Bills & Votes** | Congress 93 (1973), flagged | Congress 1 (1789) | Low — Voteview publishes the full series | **Cheap.** Roll-call quality does not degrade with age; these are archival records, not web sourcing. Strongest candidate. |
| **Federal Actions (FR)** | 1994, flagged | 1936 | High — pre-1994 is scanned volumes on GovInfo, not the API | Acknowledgment and ANCSA histories are the valuable part. Priced as its own effort. |
| **Compacts** | 1990, flagged | 1988 (IGRA enacted) | Low — only 2 years, and IGRA is the hard floor | Already effectively complete; nothing exists before IGRA. |
| **Federal contracting (prime)** | 1991 via BGOV, flagged | ~1978 (FPDS origin) | High — pre-2000 FPDS is an archived system with a different schema | Low value against high schema cost. |

**Note the asymmetry:** for these, pre-2000 data already sits in Cedar Press with
`pre_2000_flag = 1`. Publishing deeper is a *filter change*, not a new build. That makes
"expand coverage" a genuinely cheap yes for Bills & Votes.

---

## Datasets that CANNOT currently reach 2000

| Dataset | Reaches back to | Gap | Candidate fix | Status |
|---|---|---|---|---|
| **Federal funding** | FY2008 | **FY2000–2007** | FAADS (Census Bureau, predecessor system) | **Under investigation** — see `FAADS_FEASIBILITY_2026-08-05.md`. The binding risk is not availability but *identifier* availability: pre-2004 there was no DUNS mandate and no UEI, so the join may be name-only, which is the method ruled against 9-for-0. |
| **Nonprofit / 990** | e-file era | pre-e-file | IRS paper-era filings | Not digitised at scale. Structural limit; publish it as such. |
| **Deals** | 2020 (backfill to 2000 running) | 2000–2019 | Newsroom archives, ANC annual reports, SEC filings, FR land actions | **In progress.** Expect thinning by era — the 2000s will be materially sparser than the 2010s. |
| **Subcontracting** | 2011 | 2000–2010 | FSRS predates 2011 only patchily; reporting mandate is post-2008 | Likely a hard floor near 2010. FSRS is threshold-gated and self-reported throughout. |
| **Lobbying** | 1999 | — | LDA itself begins 1999 | **Statutory floor.** The Lobbying Disclosure Act of 1995 produced filings from 1999; nothing earlier exists to get. |
| **Gaming** | 1990 (decisions) | varies by layer | — | Decision index reaches 1990; the directory core's capacity panel starts 2001. |

---

## The seam problem — read before splicing anything

Extending a series backwards across a system change risks a **false discontinuity**: an
artifact of source change that gets read as a real-world event.

Known seam risks:
- **FY2008 in federal funding** — FAADS→USAspending. Different collection systems,
  possibly different assistance-type definitions and program coding. A visible jump at
  2008 would be indistinguishable from a policy change to a reader.
- **1994 in Federal Register** — the API floor. Also a metadata artifact:
  1994 has 2,838 of 2,926 rows typed `Uncategorized Document`, so 1994 shows 39
  rulemakings against 1,287 in 1995. **That is not a policy shift.** Rulemaking series
  should start at 1995.
- **2011 in subcontracting** — FSRS reporting mandate phase-in, not a change in
  subcontracting behavior.

Rule: any spliced series ships with a `source_system` column and the seam documented in
the method note. Never present a spliced series as continuous without it.

---

## Recommended posture for subscribers

1. **Ship 2000–present as the standard window** across all datasets.
2. **Bills & Votes deeper history is a cheap yes** — the data is already in hand and
   flagged; publishing it back to 1973 (or earlier) is a filter change.
3. **Federal funding FY2000–2007 is the real open question**, gated on the FAADS
   identifier and comparability findings.
4. **Lobbying's 1999 floor is statutory** — say so plainly rather than treating it as a
   gap we might close.
5. Where a floor is structural (990 e-file era, LDA 1999, IGRA 1988), publish the limit
   as a documented feature of the dataset rather than an omission.
