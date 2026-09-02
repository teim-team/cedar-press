# Florida / Seminole gaming — build log

*`code/105_build_florida_gaming.py`, run 2026-08-07. One compact tribe, one
payment obligation, sixteen years of the State's own arithmetic about it.*

Elijah, 2026-08-07:

> "seminole data must be available either through public ratings or its
> exclusivity deal with sports betting in florida — I'd be surprised if there
> wasn't rich data on Florida Seminole too."

There is. It is not where the brief expected it, and the richest thing in it is
a **tribe-level Net Win series** the Florida Legislature's own economists
publish, not a bond disclosure.

---

## WHAT WAS BUILT

```
data/clean/fl_gaming_payments.csv          9,756 rows   758 latest-statement
data/clean/seminole_bond_disclosures.csv      29 rows
data/raw/external/fl_gaming/                 106 documents + _SOURCE_MANIFEST.csv
review/fl_gaming_unresolved_2026-08-07.csv    12 items
data/interim/105_zone_log.csv              per-table extraction + footing record
data/interim/105_litigation_figures.csv       48 figures found in the court record
docs/codebooks/07e_fl_gaming.md            variables only
```

Nothing in the do-not-edit list was written. `gaming_facilities.csv` is read to
attach the twelve Florida property IDs and never modified.

---

## THE THREE SOURCES, IN ORDER OF WHAT THEY ACTUALLY DELIVERED

### 1. The compact payment series — Florida EDR (39 documents, Nov 2010 – Jan 2026)

The Florida Legislature's Office of Economic and Demographic Research runs an
**Indian Gaming Revenue Estimating Conference**. Its archive is complete from
November 2010 and every document is a free PDF. Four table shapes were parsed,
each refused unless it reconciles to something the document itself prints:

| Table | Foots against | Result |
|---|---|---|
| Historical Indian Gaming Receipts | its own `Total` and `Running Sub-Total` rows, per block | annual actual receipts **FY2007/08 – FY2024/25** |
| Year-to-date performance grid | the printed `Year` column | monthly actuals, modern vintage |
| Monthly receipts / local distribution blocks | the block's printed fiscal-year total | monthly actuals back to **Jul-2010** |
| Net Win / Net Revenues by fiscal year | the 2010 Compact's own printed schedule, applied to the base | **tribe-level Net Win, FY2012-13 – FY2019-20** |
| Net Win / revenue share by game category | `rev_share / net_win == printed effective rate` | forecast only, FY2025-26 onward |

898 zones foot; 6 fail and are refused; 5 of 39 documents yield nothing
recognised. 959 rows are logged `schedule_unmatched` — mostly the two
minimum-bound years where no (base, obligation) pair satisfies the schedule.

**Annual receipts, latest statement of each period** (USD):

```
FY2007/08     60,416,666.70   |  FY2016/17    288,840,354.15
FY2008/09     77,083,333.30   |  FY2017/18    341,803,426.06
FY2009/10    150,000,000.00   |  FY2018/19    257,994,274.00
FY2010/11    140,416,666.67   |  FY2019/20              0.00
FY2011/12    150,000,000.00   |  FY2020/21              0.00
FY2012/13    226,083,337.00   |  FY2021/22    187,500,000.04
FY2013/14    237,312,301.00   |  FY2022/23              0.00
FY2014/15    255,610,619.20   |  FY2023/24    357,030,045.00
FY2015/16    272,840,413.00   |  FY2024/25    817,306,784.00
                                 -------------------------------
                                 TOTAL      3,820,238,220.12
```

The four zero years are not gaps. Payments ceased after the April 2019 payment
when the banked card game authorisation lapsed, resumed briefly under the 2021
Compact (Oct 2021 – Feb 2022 activity), and stopped again while *West Flagler*
was on appeal. EDR states this in its own notes and the notes are carried as
`source_quote`.

**EDR restates every period at every conference.** 8,998 of 9,756 rows are not
the latest statement of their period — 3,866 flagged `restated_by_later_
conference` and the remainder already flagged as forecasts. They are kept and
readable; for a single-value series filter
`document_status = latest_statement_for_period` (758 rows).

### 2. Bond and audited disclosure

Three routes were worked. Two are closed and one produced new instruments.

**MSRB EMMA is closed to an automated client.** `emma.msrb.org/robots.txt` is
two lines in its entirety:

```
User-agent: *
Disallow: /*.pdf$
```

The official statements and continuing disclosures are PDFs. No document
request was made. This is recorded as a row in
`seminole_bond_disclosures.csv` (`availability_status =
not_retrievable_by_automated_client`) and queued for a user-mediated pull, with
the search terms the SEC route produced.

**Rating agency pages are JavaScript shells.** `fitchratings.com/entity/
seminole-tribe-of-florida-90000000` returns 1.3 MB containing the word
"Seminole" zero times; `moodys.com` returns a 2.7 KB stub. The eleven Seminole
rows already in `tribal_bond_issuances.csv` are carried forward with their own
provenance and re-checked for tribe and state agreement only.

**SEC EDGAR full-text search worked, and found instruments Cedar did not hold.**
Registered municipal and loan funds must disclose their schedules of
investments, and those schedules name the security:

- **Capital Trust Agency, FL, Revenue Bonds (Series 2001), 10.00%, "Seminole
  Tribe of Florida Convention and Resort Hotel Facilities", 10/1/2033**
- **Capital Trust Agency, FL, Revenue Bonds (Series 2003A), 8.95%**, same
  obligor and maturity
- **Term B-1 and Term B-2 Delayed Draw Loans**, 6.97 / 6.972 / 6.8 / 7.12 /
  7.125%, held 2007–2008

The two Capital Trust Agency issues are **conduit municipal bonds predating
every Seminole row Cedar held** — `tribal_bond_issuances.csv` starts at Series
2005A. They also name the EMMA issuer to search under, which is what makes the
user-mediated pull actionable rather than a wish. The term loans corroborate
the $794m 2007-vintage senior term loan already on file and name its tranches.

None of these carry a gaming revenue figure. They are a **third party's**
disclosure about the security, not the Tribe's disclosure about itself.

**The Tribe's audited statements exist, are filed annually, and are withheld by
regulation.** Seminole Tribe of Florida (EIN 59-1415030) files a Single Audit
every year, audited by Deloitte & Touche. Every one is `is_public: false` at
the Federal Audit Clearinghouse — FY2019 through FY2025, ten filings — while
every non-tribal Florida auditee returned by the same query is public.
2 CFR 200.512(b)(2) exempts Indian tribes from publication of the reporting
package unless the tribe opts in. Ten rows, one per audit year, each queued for
a ruling on whether to request the package from the Tribe directly.

### 3. The litigation record

Nine documents scanned: four USCOURTS opinion packages (D.D.C. and D.C. Cir.,
*West Flagler* and the *Monterra* companion) and five Supreme Court filings from
docket 23A315.

**Forty-eight dollar figures were found and all forty-eight are in one place:**
the Emergency Application Appendix, which reproduces the 2021 Compact and the
district-court record. The D.D.C. opinion, both D.C. Circuit opinions, West
Flagler's stay application and the Solicitor General's opposition contain **no
dollar figure at all** — not one, across roughly 184,000 characters.

The compact litigation is about whether IGRA authorises a compact to reach
wagers placed off Indian lands. It put the compact's own numbers back on the
public record and added nothing about what the Tribe earns. The one figure that
is a party's own fact rather than a quoted clause is West Flagler's: *"To date,
West Flagler has spent over $55,000,000 on capital improvements."*

---

## THE DERIVATION THAT WAS BUILT, PUBLISHED IN A DRAFT, AND THEN KILLED

The first pass emitted 44 `BOUNDED_DERIVED_REVENUE` rows on this reasoning:
every dollar of Net Win is charged at no less than the lowest marginal rate in
the governing compact, therefore `Net Win <= payment / rate_min` exactly.

The inequality is true of the **obligation**. EDR publishes **receipts**.

```
FY 2013/14 receipts             $237,312,301
implied ceiling on Net Win      $1.978bn
EDR's own Net Win, same year    $2.098bn     <- BOUND VIOLATED
```

The gap is the true-up, and EDR names the mechanism in the document:

> "Revenues collected are lagged by one month"
> "True-up payments generated from activity in any Fiscal Year are received in
> the following Fiscal Year."

A state fiscal year's cash is one cycle's instalments plus the previous cycle's
true-up. The period does not match on both sides, so the rule is to refuse
rather than caveat. **All 44 rows were withdrawn.** `bound_basis` on every
payment row now carries the arithmetic above so the refusal is auditable and
nobody re-derives it.

Two further blockers survive even with a matched period:

1. The payment is `max(percentage amount, guaranteed minimum)`. A binding
   minimum carries no information about Net Win, and Florida's minimum bound in
   FY2010/11 through FY2012/13.
2. Under the 2021 Compact one total is the sum of four category schedules —
   Slot Machines 12→25%, Table Games 15→25%, Sports Betting 13.75%, Sports
   Betting through a Qualified Pari-mutuel Permitholder brand 10% — so one
   number does not determine four bases.

### The related defect in an existing dataset

`compact_structured_terms.csv` records a Florida `revenue_sharing_rate = 10`
with `formula_invertibility = INVERTIBLE_FLAT_RATE`. Read in place, that 10% is
Part XI.C.1(k) — the bottom tier of a graduated schedule for one game category,
under a compact carrying a $2.5bn guaranteed minimum. This build does not use
it. The file is owned by `95_parse_compact_terms.py` and was **not edited**; the
conflict is item `FL-COMPACT-RATE-10PCT-INVERTIBILITY` in the review queue.
This is the same error the California parse made 44 times.

---

## WHAT IS GENUINELY TRIBE-LEVEL REVENUE

138 rows carry `TRIBE_LEVEL_REVENUE`, and none of them is a derivation. EDR's
December 2015 conference names its own source in the document:

> "the actual Net Win for Fiscal Year 2014-15, and other information from the
> most recent quarterly financial reports available from the Tribe"

So for a fiscal year that closed before the conference met, the Net Win column
is the State's statement of a figure the Tribe reported to it. Two guards
separate that from a forecast sitting in the past:

1. **The schedule test.** The 2010 Compact's schedule is strictly monotone and
   piecewise-linear, so a (base, obligation) pair either satisfies it to the
   cent or it does not. Exactly one qualifying pair per row is required.
   FY2013-14: `2000 x 12% + 98 x 15% = 254.7`, which is the printed obligation.
2. **The stability test.** A forecast moves; a settled actual does not.
   `foot_detail` records how many conferences restated each period *after* it
   closed and how many distinct values they gave. FY2012-13 through FY2015-16:
   eleven post-close statements, one distinct value each.

```
                       net_win_total    net_win_subject_to_revenue_share
FY2012-13             1,977,600,000                       1,977,600,000
FY2013-14             2,098,000,000                       2,098,000,000
FY2014-15             2,218,900,000                       2,218,900,000
FY2015-16             2,325,600,000                       1,418,400,000
FY2016-17             2,334,300,000                         987,300,000
FY2017-18             2,538,000,000                       2,538,000,000
FY2018-19             2,574,000,000                       2,574,000,000
FY2019-20             2,187,000,000                       2,187,000,000
```

The two columns diverge in FY2015-16 and FY2016-17 only, and the divergence is
the story of those years: the State excluded table-game revenue from the share
base while the banked card game authorisation had lapsed. Total Net Win and the
share base are different facts and neither is recorded as the other.

**The series stops at FY2019-20.** February 2021 is the last conference to
publish this table. Nothing in the 2021-Compact era republishes a tribal Net
Win actual — the modern documents forecast cycles and nothing more.

---

## WHAT FLORIDA STRUCTURALLY DOES NOT PUBLISH

**No per-property figure of any kind, and none is coming.** The Florida Gaming
Control Commission publishes per-facility slot revenue (FY2006-07 forward),
cardroom gross receipts (FY2008-09 forward) and pari-mutuel handle (FY2005-06
forward) — by individual racing association or fronton. Those are **permitholder**
series. A tribal casino operates under the compact and holds no pari-mutuel
permit, so it is outside the population of every per-facility table the State
publishes. The DBPR/FGCC annual report mentions the Seminole Tribe only in the
context of the State Compliance Agency's oversight function.

`fl_gaming_payments.csv` carries **twelve explicit `NO_REVENUE_OBSERVATION`
rows**, one per Florida property (10 Seminole, 2 Miccosukee), so that absence
reads as a fact about the source rather than as an unworked gap.

**No tribe-reported Net Win after 2020.** The compact requires the Tribe to give
the State audited Net Win (Part XI.C.3) and, in the same instrument, lets the
Tribe mark what it gives the State *"Trade Secret, Confidential and
Proprietary"*, whereupon a Chapter 119 public-records request triggers notice to
the Tribe rather than release. The State holds the number and does not publish
it.

**No audited financial statement.** Filed every year with the Federal Audit
Clearinghouse; withheld by 2 CFR 200.512(b)(2) because the auditee is a tribe.

**No official statement through an automated client.** EMMA's robots.txt.

---

## THE MISATTRIBUTION THAT WAS GUARDED AGAINST

**Seminole Tribe of Florida (`TRBF-SMNLFL-00`, FL) is not Seminole Nation of
Oklahoma (`TRBF-SMNLOK-00`, OK).** The spine's canonical name for the Florida
tribe is the bare word *Seminole*, and the compact corpus holds
`508 Compliant 2001.06.07 Seminole Nation Tribal State Gaming Compact.pdf`
alongside `508_compliant_2010.07.06_seminole_tribe_...pdf` — one word apart.
Every resolution in this build runs through `resolve_entity` and is then
refused unless the spine says the entity's state is FL. An assertion at the end
of the build fails the run if any row lands on a tribe other than the two
Florida ones. Two distinct names resolved; nothing was refused, because nothing
outside Florida was ever offered.

---

## PULL DISCIPLINE

Seven hosts, each claimed in `logs/_HOSTLOCK_<host>.json`, worked sequentially
at a 1.6 s gap, and released on completion: `edr.state.fl.us`, `flgaming.gov`,
`api.govinfo.gov`, `www.supremecourt.gov`, `api.fac.gov`, `emma.msrb.org`
(two requests, no documents), `efts.sec.gov` / `www.sec.gov`. No retry loop was
started and no host refused. 106 documents, all HTTP 200, md5 in
`_SOURCE_MANIFEST.csv`.

`api.usaspending.gov` was not touched.

Only three of the 60 FGCC per-facility statistics files were fetched, and only
as negative evidence — one slot, one cardroom, one handle. Pulling the other 57
would have been a pull for its own sake.

---

## KNOWN UNEXTRACTED

Recorded rather than quietly dropped, because a gap that is not written down
looks identical to a gap nobody found:

- **5 of 39 EDR documents yield nothing** (Aug 2021 – Feb 2024). They are the
  transition-era conferences and use table shapes not implemented here.
- **The `Revenues Collected` / `Minimum Payment` / `True-up Payment` columns**
  of the 2010-era table are read only insofar as the schedule test needs them.
  The true-up series would make the receipts-versus-obligation reconciliation
  explicit rather than narrative.
- **Local distribution at monthly grain** in the pre-2024 blocks. Annual local
  distribution is captured from the historical receipts table.
- **Sports wagering separately from physical casino GGR.** Florida publishes
  the split only as a forecast, and it is recorded only as a forecast. No
  sports-betting figure is merged into any casino figure anywhere in this file.
