# ASSUMPTIONS AND LIMITATIONS — the register that tells a reporting rule from a finding

*Built 2026-08-26. Measurements from `code/234_measure_reporting_regime_signatures.py`
(READ-ONLY; writes `review/reporting_regime_signatures_2026-08-26.json` and nothing else).
Statutory and regulatory citations retrieved live from govinfo, eCFR, the Federal Register,
Treasury, IRS, NPS and the joint House/Senate LDA guidance. **No paywalled source appears
here.** No dataset was modified to build this file.*

---

## WHY THIS FILE EXISTS

**A reporting rule can look exactly like a finding.** When a threshold moves, a filing
frequency changes, or a relief programme starts, the data STEPS — and the step is a fact
about the REGIME, not about Indian Country. Published as a discovery, it is a factual
error about the world wearing a correct number.

Every entry is **typed**:

| type | means |
|---|---|
| **STRUCTURAL** | the data cannot exist — no law required it, no system collected it, or the form does not ask |
| **THRESHOLD** | the data exists only above a reporting floor; below the floor, absence is the rule speaking |
| **REGIME_CHANGE** | a definition, frequency or scope changed on a date; the series is not comparable across it |
| **SUPPRESSION** | collected but withheld — the value exists and is not published, often rendered as a zero |

And every entry carries a **CITATION** — a statute, a regulation, agency guidance, or a
measured observation in our own files. Where the citation is a measurement, the script and
artefact are named so the next reader can repeat it rather than trust it.

### Read alongside

- **`docs/ANOMALY_REPORT.md`** — the concurrent year-over-year anomaly sweep
  (`code/227_anomaly_sweep.py`). **That document finds the steps; this one holds the
  rulebook that explains them.** Its `THE REGIME REGISTER` table defines the keys and
  **this file uses the same keys**, so the two line up. An anomaly landing on a date in
  this file is *explained*; one that does not is a candidate finding. Keys introduced here
  and not yet in 227 are marked **`NEW`**.
- **`docs/DOC_CONTRADICTIONS_2026-08-26.md`** — before quoting any number from a build log.
- **`docs/LABOR_SOURCES_FOR_GAMING_2026-08-26.md`** §3 and §15 — the fullest existing
  treatment of Census/BLS and OSHA disclosure limits. Summarised here, not duplicated.
- **`docs/CICD_BENCHMARK.md`** — `INTERNAL-05` (the `extent_competed` seam) and
  `UNDERCOUNT-01` (the $140.00B no-set-aside measurement).
- **`docs/FAADS_FEASIBILITY_2026-08-05.md`** §3 — the FAADS record layout.

### Six corrections this research forces, before anything else

1. **The Single Audit threshold is NOT $750,000. It is $1,000,000**, for auditee fiscal
   years beginning on or after **2024-10-01** (89 FR 30046; 2 CFR 200.501(a) as it now
   reads). Anything in our docs saying "currently $750,000" is a year out of date. §B5.
2. **The tribal Single Audit opt-out is 2 CFR 200.512(b)(3), not (b)(2).** `START_HERE.md`
   cites `2 CFR 200.512(b)(2)`; that paragraph is the certification, and **(b)(3)** is the
   opt-out. Correct the cite before it is published. §B5b.
3. **`docs/PUBLISHED_LANDSCAPE_2026-08-26.md` §7's replacement framing is arithmetically
   false.** It says *"across 2,769,748 FAADS rows for FY2001–07, the recipient identifier
   is populated on 0.0% of rows."* Measured: **0.003% for FY2001–06 (65 of 1,994,993)** and
   **87.4% for FY2007 (676,970 of 774,755)**. Over the full FY2001–07 span it is **24.4%**.
   The finding is real and is stronger stated correctly; stated as written it is wrong and
   a reviewer will catch it. §A1.
4. **"Per-entity federal assistance begins FY2007" is FALSE for the Department of the
   Interior** — the largest tribal assistance agency. Interior's recipient identifier is
   0.0% through FY2009 and does not reach 100% until **FY2011**. A reader who filters
   Interior at FY2007 gets nothing and concludes our data is bad. §A2.
5. **`Buy Indian` and `Indian Business` are ONE instrument under TWO codes, and must always
   be summed.** `Indian Business` is zero in every year FY2000–2013 and overtakes `Buy Indian`
   in FY2016 — the DOI Buy Indian rule of 2013-07-08 created a second set-aside tier. Read
   alone, `Buy Indian` says Native set-asides collapsed 62% after 2015; summed, they rose 44%.
   **This is unrecorded anywhere else in the repo and it would have produced a false
   headline.** §E1b.
6. **FY2026 prime contract COUNTS are not comparable to any other year.** 71.9% of FY2026
   positive obligations are ≤ $2,500 and the median is $443, against 8–20% in prior years. FAR
   4.606(a)(1) requires modifications to be reported `regardless of dollar value`; FY2026 as
   held is a partial year of small modifications. §E1.

### The rule that generalises

**Absence under a filter is a property of the filter.** Every entry below is an instance.

---
---

# PART I — THE CROSS-CUTTING TIMELINE

*The date given is the **operative** one — the date the rule BOUND, not the date it was
published. A rule published in April and applicable to fiscal years beginning the following
October moves the data in October.*

| date | key | type | what changed | collections hit |
|---|---|---|---|---|
| **1984-10-19** (FYs beginning after 1984-12-31) | `SINGLE_AUDIT_THRESHOLD` | THRESHOLD | Single Audit Act of 1984: $100,000 audit / $25,000 floor, **State and local governments only** — non-profits and tribal organisations outside the population entirely | FAC |
| **1988-10-17** | `IGRA_ERA` | REGIME_CHANGE | IGRA (Pub. L. 100-497) creates Class I/II/III and the compact requirement — the *reporting universe itself* | Gaming |
| **1990-11-16** | `NAGPRA_STATUTE` **NEW** | STRUCTURAL | NAGPRA enacted; summaries due 1993, inventories due 1995. **No notice can predate 1990.** Our earliest is 1994 | NAGPRA |
| **1995-12-19** (eff. 1996-01-01) | `LDA_1995` **NEW** | STRUCTURAL | LDA creates LD-1/LD-2. **SEMIANNUAL** reports; income/expense censored below $10,000 and rounded to the nearest $20,000 | Lobbying |
| **1996-07-05** (FYs beginning after 1996-06-30) | `SINGLE_AUDIT_THRESHOLD` | THRESHOLD + REGIME_CHANGE | $300,000; test changes from *receives* to **expends**; non-profits brought in | FAC |
| **1997-01-01, then every 4th Jan 1** | `LDA_CPI` **NEW** | THRESHOLD | LDA registration thresholds CPI-adjusted (2 U.S.C. 1603(a)(3)(B)). The floor rises in real terms on a fixed cycle unrelated to lobbying | Lobbying |
| **2003-06-27** (FYs **ENDING** after 2003-12-31) | `SINGLE_AUDIT_THRESHOLD` | THRESHOLD | $300,000 → **$500,000**. OMB's own estimate: **~6,000 entities leave the population at once** | FAC |
| **1996-01-03** | `NAGPRA_1995_RULE` **NEW** | REGIME_CHANGE | Original 43 CFR Part 10 effective (60 FR 62134, pub. 1995-12-04). **Our 1994–95 notices predate the regulation entirely** | NAGPRA |
| **2002-07-17** | `CLASS_II_III_LINE` **NEW** | REGIME_CHANGE | 25 CFR 502.7/502.8 redraw the "technologic aid" vs "facsimile" line (67 FR 41166). **The same machine can change class without changing** | Gaming |
| **2006-09-26** | `FFATA_FY2007_FLOOR` **NEW** | STRUCTURAL + THRESHOLD | FFATA §2(b)(2): *"The website shall include data for fiscal year 2007, and each fiscal year thereafter."* **And §2(a)(2)(B): "does not include individual transactions below $25,000"** | Assistance, Prime |
| **2006-09-28** | `ACQUISITION_THRESHOLDS` | THRESHOLD | Micro-purchase $2,500 → **$3,000**, and the FPDS reporting floor moves with it (FAC 2005-13, 71 FR 57363). **A mid-FY2007 break** | Prime |
| **2007-01-01** | `FORM_990N` | THRESHOLD | Form 990-N (e-Postcard) created by PPA 2006 §1223, applicable to `annual periods beginning after 2006` | Nonprofit |
| **2008-01-01** | `HLOGA_QUARTERLY` | REGIME_CHANGE | **FOUR simultaneous breaks** — semiannual→quarterly; rounding grain $20,000→$10,000; censoring point $10,000→$5,000; registration thresholds halved | Lobbying |
| **2008 mid-year** | `LD203` **NEW** | REGIME_CHANGE | LD-203 created by HLOGA §203, filed **per lobbyist** not per registrant-client. A new form type appearing mid-2008 | Lobbying |
| **2008-04-22** | `FPDS_FLOOR_IS_MPT` **NEW** | REGIME_CHANGE | FAR Case 2004-038 pegs FPDS coverage to the micro-purchase threshold instead of a fixed figure. **From here the FPDS floor is a moving target** | Prime |
| **2008-10-01** | `FFATA_CARD_CARVEOUT` **NEW** | STRUCTURAL | FFATA §2(a)(2)(C): before this date the Act `does not include credit card transactions` | Assistance, Prime |
| **2008-11-10** | `CLASS_II_III_LINE` **NEW** | REGIME_CHANGE | 25 CFR Part 547 Class II technical standards (73 FR 60508) | Gaming |
| **2009-02-17** | `ARRA` | REGIME_CHANGE | ARRA; obligations bounded at **2010-09-30** (§1603), NAHASDA line to 2011-09-30. **ARRA-funded subawards are excluded from 2 CFR 170 outright** | Assistance, Prime |
| **2010-05-14** | `NAGPRA_CUI_2010` **NEW** | REGIME_CHANGE | 43 CFR 10.11 culturally-unidentifiable disposition rule **effective** (75 FR 12378, pub. 2010-03-15). **Break on the effective date, not publication** | NAGPRA |
| **2010-07-08 → 2011-03-01** | `FFATA_SUBAWARD` | THRESHOLD + STRUCTURAL | FSRS begins. Contracts phase in **three times** (≥$20M, then ≥$550,000, then ≥$25,000 from 2011-03-01); grants cut over cleanly at 2010-10-01. **No subaward can exist before 2010-07-08** | Subawards |
| **2010-10-01** | `ACQUISITION_THRESHOLDS` | THRESHOLD | SAT $100,000 → **$150,000** (FAC 2005-45, 75 FR 53129) | Prime |
| **2011-06-08** | `IRC_6033J` **NEW** | REGIME_CHANGE | First automatic-revocation list — **~275,000 organisations leave the BMF in one act**, updated monthly since | Nonprofit |
| **2014-12-26** (FYs beginning on/after) | `SINGLE_AUDIT_THRESHOLD` | THRESHOLD | Uniform Guidance, $500,000 → **$750,000** | FAC |
| **2015-10-01** | `FFATA_SUBAWARD` / `ACQUISITION_THRESHOLDS` | THRESHOLD | **Contract** subaward floor $25,000 → **$30,000**; micro-purchase $3,000 → **$3,500** (FAC 2005-83, 80 FR 38293). **Grant subawards stay at $25,000 — the two families are out of sync until 2020** | Subawards, Prime |
| **2016-10-31** | `DUNS_TO_UEI` | *not a break* | FAR relabels the field "unique entity identifier" (FAC 2005-91, 81 FR 67736). **A schema change with no value change — do not read it as an identifier break** | Prime |
| **2020-08-31** | `ACQUISITION_THRESHOLDS` | THRESHOLD | Micro-purchase $3,500 → **$10,000**; SAT $150,000 → **$250,000** (FAR Case 2018-004, 85 FR 40064). **The FPDS reporting floor TRIPLES overnight** | Prime |
| **2020-11-12** | `FFATA_SUBAWARD` | THRESHOLD | **Grant** subaward floor $25,000 → **$30,000** (85 FR 49506) — five years after contracts | Subawards |
| **2019** (Taxpayer First Act) | `TFA_EFILE` **NEW** | REGIME_CHANGE | Mandatory 990 e-filing. **Paper filers 2011–2018 are absent from the XML entirely** | Nonprofit, Schedule I |
| **2020-03-27** | `COVID_RELIEF` | REGIME_CHANGE | CARES Act §5001: **$8,000,000,000** Coronavirus Relief Fund tribal set-aside, payable within 30 days | Assistance |
| **2020-12-27** | `COVID_RELIEF` | REGIME_CHANGE | CRRSAA: CRF deadline extended; IHS transfers; **Tribal Broadband Connectivity Program $1B** (obligates FY2022) | Assistance |
| **2021-03-11** | `COVID_RELIEF` | REGIME_CHANGE | ARPA §9901: **$20,000,000,000** SLFRF tribal set-aside; ARPA Title XI adds **$8.8B** more | Assistance |
| **2021-06-25** | `ANC_ELIGIBILITY` **NEW** | REGIME_CHANGE | *Yellen v. Chehalis* — **ANCs are eligible for the CRF but NOT for SLFRF.** Two incompatible definitions of "tribe" in adjacent programme years | Assistance |
| **2022-04-04** | `DUNS_TO_UEI` | REGIME_CHANGE | DUNS retired, UEI adopted. Measured: assistance DUNS coverage 93.3% (FY2020) → 78.2% (FY2021) → **16.8% (FY2022) → 0.0% (FY2023)** | Prime, Assistance, Subawards |
| **2024-01-12** | `NAGPRA_2024_RULE` | REGIME_CHANGE | Revised 43 CFR 10 effective. Measured: the `culturally_unidentifiable` category **goes to zero** and a new `intended_disposition` notice type appears | NAGPRA |
| **2024-10-01** (FYs beginning on/after) | `SINGLE_AUDIT_THRESHOLD` | THRESHOLD | **$750,000 → $1,000,000.** Lands in FAC submissions received during **2026**, not 2025 | FAC |
| **2025-10-01** | `ACQUISITION_THRESHOLDS` / `FFATA_SUBAWARD` | THRESHOLD | Micro-purchase $10,000 → **$15,000**; SAT $250,000 → **$350,000**; **contract** subaward floor $30,000 → **$40,000** (FAC 2025-06, 90 FR 41872). Grant subawards stay at $30,000 | Prime, Subawards |
| **2026-07-31** | `HOUSE_LDA_SUNSET` **NEW** | ACCESS | `disclosurespreview.house.gov` goes ZIP-only; API users directed to LDA.gov. **Our pipeline is on borrowed time** | Lobbying |
| **2029-01-10** | `NAGPRA_2024_RULE` | *forward-looking* | Statutory-style deadline in 43 CFR 10.10(d)(3) for updating every un-noticed inventory. **Expect elevated NAGPRA counts THROUGH 2029 and a fall after** | NAGPRA |

---
---

# PART II — PER-COLLECTION REGISTER

## A. FEDERAL ASSISTANCE — `federal_funding_transactions.csv` (701,955 rows, FY2007–2026) and `faads_transactions_all_agencies.csv` (2,769,748 rows, FY2001–2007)

*Row count note: `START_HERE.md` says 684,923. The file now holds **701,955**, after the
credit pass logged in `docs/ASSISTANCE_ARCHIVE_PULL_LOG.md`. Measured 2026-08-26.*

### A1 · `FFATA_FY2007_FLOOR` · **STRUCTURAL** — per-entity assistance cannot begin before FY2007

**CITATION — statute.** Federal Funding Accountability and Transparency Act of 2006,
Pub. L. 109-282, **§2(b)(2)**, 120 Stat. 1186, approved 2006-09-26.
https://www.govinfo.gov/content/pkg/PLAW-109publ282/html/PLAW-109publ282.htm

> `(2) Scope of data.--The website shall include data for fiscal year 2007, and each fiscal year thereafter.`

Verified character-for-character. **The cite is §2(b)(2), captioned "Scope of data"** — our
docs have carried it without the subsection. §2(b)(1) is the separate 2008-01-01 deadline
for the website to *exist*, which is why FY2007 is thin even where present: the first
covered fiscal year was over before the site was due.

**CITATION — record layout.** FAADS is a **624-byte fixed-width record with 34 fields** and
**has no DUNS field and no EIN field at all**. Census's own user guide, recovered from the
Internet Archive (the live `census.gov/govs/faads/usrguide.txt` is a 404) and staged at
`data/raw/external/faads/census_faads_usrguide.txt`, says FAADS *"does not currently collect
DUNS information for recipients of Federal assistance."* Recipient Name (45 chars) is the
only recipient identifier the form carries. See `docs/FAADS_FEASIBILITY_2026-08-05.md` §3.

**CITATION — measured, 2026-08-26.** `recipient_duns` populated in
`faads_transactions_all_agencies.csv`:

| FY | rows | DUNS populated | % |
|---|---:|---:|---:|
| 2001 | 316,006 | 1 | 0.0003% |
| 2002 | 321,290 | 3 | 0.0009% |
| 2003 | 334,206 | 6 | 0.0018% |
| 2004 | 318,543 | 9 | 0.0028% |
| 2005 | 327,210 | 7 | 0.0021% |
| 2006 | 377,738 | 39 | 0.0103% |
| **2007** | **774,755** | **676,970** | **87.4%** |

**FY2001–06 combined: 65 of 1,994,993 rows — 0.003%.** That is the original Cedar Press
measurement and it is stronger than the version currently in circulation.

**THE FY2007 STEP IS FAADS → FAADS PLUS, AND IT IS NOT UNIFORM ACROSS AGENCIES.** DUNS
arrives with FAADS PLUS in 2007, and not every agency filed FAADS PLUS that year. Measured
within FY2007, by source file:

| FY2007 source file | rows | DUNS % |
|---|---:|---:|
| `ed_fy2007_archive.zip` | 344,401 | 100.0% |
| `hud_fy2007_archive.zip` | 171,554 | 100.0% |
| `hhs_fy2007_archive.zip` | 74,163 | 99.7% |
| `usda_fy2007_archive.zip` | 67,615 | 98.0% |
| `dot_fy2007_archive.zip` | 86,921 | **0.7%** |
| `doi_fy2007.zip` | 9,662 | **0.0%** |

**HOW TO STATE IT.** *"FFATA required USAspending to carry a unique recipient identifier and
provided that the website 'shall include data for fiscal year 2007, and each fiscal year
thereafter' (Pub. L. 109-282 §2(b)(2)). The predecessor system, FAADS, had no field for one:
its 624-byte record layout contains neither DUNS nor EIN, and Census documented that it 'does
not currently collect DUNS information.' We measured the consequence — across 1,994,993 FAADS
rows for FY2001–06, a recipient identifier appears on 65 of them, 0.003%. FY2007 is the
transition year and is not uniform: agencies that filed FAADS PLUS carry the identifier on
98–100% of rows, while Interior and DOT carry it on 0.0% and 0.7%."*

**DO NOT** write "FY2001–07 is 0.0%." It is 24.4% over that span.

---

### A2 · `INTERIOR_IDENTIFIER_FLOOR` **NEW** · **STRUCTURAL** — the FY2007 floor is FY2011 at Interior

**CITATION — measured, 2026-08-26**, `federal_funding_transactions.csv`, `recipient_duns`
populated, by awarding agency × fiscal year:

| agency | FY07 | FY08 | FY09 | FY10 | FY11 | FY12 | FY13 |
|---|---:|---:|---:|---:|---:|---:|---:|
| Health and Human Services | 100.0 | 99.3 | 99.6 | 99.6 | 100.0 | 99.9 | 99.9 |
| Education | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 |
| Agriculture | 98.3 | 98.8 | 98.2 | 97.5 | 98.6 | 96.6 | 94.3 |
| Housing and Urban Development | 100.0 | 98.3 | 95.9 | 96.6 | 100.0 | 99.9 | 99.9 |
| **the Interior** | **0.0** | **0.0** | **0.0** | **11.9** | **100.0** | 100.0 | 100.0 |
| Justice | 98.4 | 96.1 | **32.6** | 98.5 | 100.0 | 100.0 | 100.0 |
| Transportation | **0.0** | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 |
| Homeland Security | — | **0.0** | **27.8** | 100.0 | 100.0 | 100.0 | 100.0 |

**Interior is the largest tribal assistance agency and its identifier floor is FY2011, four
fiscal years later than the published claim.** $1.19B of Interior tribal assistance across
FY2008–FY2010 carries no DUNS at all. DOT's zero is a one-year, 59-row artefact and should
not be given equal billing. DOJ's FY2009 dip to 32.6% ($330M without an identifier) sits in
the ARRA year — a rushed-money hypothesis worth testing, not asserting.

**AND A SEPARATE, PURELY OURS, HOLE IN THE SAME PLACE.** Interior row counts by FY: 841
(2007) · 1,629 (2008) · 5,339 (2009) · **143 (2010) · 79 (2011) · 176 (2012)** · 9,742 (2013).
The FY2010–2012 collapse is a **Cedar coverage gap, not a regime change**, and it sits
immediately beside the identifier crossover, so the two are easy to confuse. Flag both.

---

### A3 · `COVID_RELIEF` · **REGIME_CHANGE** — the single biggest confounder in the panel, now sized

**CITATION — statute, CARES Act.** Pub. L. 116-136 div. A tit. V §5001(a), enacted
**2020-03-27**, adding SSA §601 = **42 U.S.C. §801**.
https://www.govinfo.gov/content/pkg/USCODE-2024-title42/html/USCODE-2024-title42-chap7-subchapVI-sec801.htm

> `(2) Reservation of funds` … `(B) $8,000,000,000 of such amount for making payments to Tribal governments.`

> `(b)(1)` … `not later than 30 days after March 27, 2020, the Secretary shall pay each State and Tribal government…`

Treasury's allocation method (https://home.treasury.gov/system/files/136/Coronavirus-Relief-Fund-Tribal-Allocation-Methodology.pdf):
> `Treasury has determined to distribute 60 percent of the $8 billion reserved for Tribal governments immediately based on population.`
…with a `minimum payment of $100,000` and a pro-rata reduction capping the first tranche at
`$4.8 billion`. The remaining 40% went out from 2020-06-12 on employment and expenditure data.

**CITATION — statute, ARPA.** Pub. L. 117-2 tit. IX §9901(a), enacted **2021-03-11**, adding
SSA §602 = **42 U.S.C. §802**.
https://www.govinfo.gov/content/pkg/USCODE-2024-title42/html/USCODE-2024-title42-chap7-subchapVI-sec802.htm

> `(2) Payments to Tribal governments` — `(A) In general` — `The Secretary shall reserve $20,000,000,000 of the amount appropriated under subsection (a)(1) to make payments to Tribal governments.` — `(B) Allocation` — `(i) $1,000,000,000 shall be allocated by the Secretary equally among each of the Tribal governments; and (ii) $19,000,000,000 shall be allocated by the Secretary to the Tribal governments in a manner determined by the Secretary.`

> `(b)(6)(B)` — `the Secretary shall make the payment required for the Tribal government not later than 60 days after March 11, 2021.`

Assistance Listing numbers, both verified from the Federal Register rather than assumed:
**21.019** Coronavirus Relief Fund (86 FR 4182, 2021-01-15: *"The CFDA number assigned to the
Fund is 21.019."*) and **21.027** Coronavirus State and Local Fiscal Recovery Funds
(87 FR 3385, 2022-01-21). Also verified: **21.026** HAF, **21.029** CPF, **14.867** IHBG.

**CITATION — measured, 2026-08-26.** Total assistance obligations by fiscal year:

| FY | $B | vs FY2015–19 mean ($8.71B) |
|---|---:|---:|
| 2019 | 10.96 | — |
| **2020** | **20.59** | **+$11.87B** |
| **2021** | **40.80** | **+$32.08B** |
| 2022 | 14.67 | +$5.95B |
| 2023 | 15.03 | +$6.32B |

The four named COVID Assistance Listings account for **$7.466B of FY2020** (62.9% of the
excess) and **$22.073B of FY2021** (68.8% of the excess, and **54.1% of every assistance
dollar in that fiscal year**):

| listing | FY2020 | FY2021 |
|---|---:|---:|
| 21.019 Coronavirus Relief Fund | $7.466B | $0.516B |
| 21.027 State and Local Fiscal Recovery Funds | — | **$20.227B** |
| 21.023 Emergency Rental Assistance | — | $0.833B |
| 21.026 Homeowner Assistance Fund | — | $0.497B |

**$20.227B against a $20.000B statutory set-aside.** The programme lands essentially whole
in one fiscal year. **Never read FY2021 growth as organic. It is one statute.**

**AND THE REST OF THE EXCESS IS ALSO COVID, FLOWING THROUGH ORDINARY LISTINGS.** IHS Tribal
Self-Governance (93.210) runs $2.417B (FY2019) → $3.277B (FY2020) → **$5.667B (FY2021)** →
$3.053B (FY2022) — a 2.34× peak on an ordinary listing, driven by CARES ($1.032B IHS),
CRRSAA ($790M + $210M IHS transfers) and ARPA §11001 ($6.094B IHS). **A COVID filter built
on Assistance Listing numbers misses this entirely.**

**THE INSTRUMENT WE LACK.** Our schema carries **no `disaster_emergency_fund_code` (DEFC)**
column. DEFC is the federal marker that separates supplemental from base appropriations, and
without it COVID and ARRA money in ordinary listings is **not separable at all**. Adding DEFC
to the assistance pull is the single highest-value schema change available. *(USAspending is
owned by another agent's poller; this is a recommendation, not an action.)*

**THE LATE TAIL.** FY2022 carries **$1.159B Tribal Broadband Connectivity Program (11.029)**,
appropriated by CRRSAA in December 2020, and **$0.510B Local Assistance and Tribal Consistency
Fund (21.032)** from ARPA §605. **The relief window is FY2020–FY2023, not FY2020–21.**

---

### A4 · `ANC_ELIGIBILITY` **NEW** · **REGIME_CHANGE** — two incompatible definitions of "tribe" in adjacent years

This is the finding in the COVID family that nothing in our docs currently holds, and it
changes the recipient universe between FY2020 and FY2021.

**CITATION — statute.** CRF eligibility runs on **ISDEAA**, 42 U.S.C. §801(g)(1):
> `The term "Indian Tribe" has the meaning given that term in section 5304(e) of title 25.`

25 U.S.C. §5304(e) expressly **includes** ANCs:
> `…including any Alaska Native village or regional or village corporation as defined in or established pursuant to the Alaska Native Claims Settlement Act…`

SLFRF eligibility runs on the **FRITLA list**, 42 U.S.C. §802(g)(7):
> `…individually identified (including parenthetically) in the list published most recently as of March 11, 2021, pursuant to section 5131 of title 25.`

**ANCs are eligible for 21.019 and NOT for 21.027.** Same Treasury, adjacent fiscal years,
different universes.

**CITATION — litigation.** Treasury, *Disbursements to Alaska Native Corporations*, 2021-08-04
(https://home.treasury.gov/system/files/136/Disbursements-Alaska-Native-Corporations.pdf):
> `On June 25, 2021, the Supreme Court held in Yellen v. Confederated Tribes of the Chehalis Reservation that ANCs are eligible for payments from the CRF.`
> `The total amount of funds available for disbursement to ANCs at this time … is $443,863,750.27.`

**CITATION — measured, 2026-08-26, and it independently confirms the holding.** Listing
21.019 in **FY2021** carries **$515.8M across 238 recipients**, and the top of the list is
almost entirely ANCs: Cook Inlet Region $111.8M · Arctic Slope Regional $63.3M · NANA $32.9M
· Doyon $30.9M · Chugach Alaska $24.7M · Afognak $19.3M · Bristol Bay $17.0M · Bering Straits
$15.0M · UIC $13.5M · Calista $12.2M · Ahtna $11.7M · Goldbelt $11.1M · Koniag $6.8M ·
Sitnasuak $6.0M · Tyonek $5.1M · Tatitlek $4.9M. The FY2021 CRF tail **is** the Chehalis
disbursement, visible in our own file, against Treasury's stated $443.9M.

**CONSEQUENCE FOR ANY SERIES.** A recipient count across FY2020–FY2021 that pools 21.019 and
21.027 mixes two eligibility rules. **A drop in "tribal recipients" from CRF to SLFRF is the
statute, not attrition.** State which definition each figure uses.

---

### A5 · `ARRA` · **REGIME_CHANGE** — real, smaller, and only partly separable

**CITATION — statute.** American Recovery and Reinvestment Act of 2009, Pub. L. 111-5,
enacted **2009-02-17**, 123 Stat. 115.
https://www.govinfo.gov/content/pkg/PLAW-111publ5/html/PLAW-111publ5.htm

> `Sec. 1603. All funds appropriated in this Act shall remain available for obligation until September 30, 2010, unless expressly provided otherwise in this Act.`

Named tribal lines, verbatim from the enacted text: **BIA $500,000,000** ($40M Operation of
Indian Programs + $450M Construction + $10M Guaranteed Loan); **IHS $500,000,000** ($85M
health IT + $415M facilities); **HUD NAHASDA $510,000,000** (`to remain available until
September 30, 2011`; $255M formula obligated `within 30 days of enactment`, $255M competitive
obligated `by September 30, 2009`); **FHWA Indian Reservation Roads $310,000,000** of a $550M
tribal/federal-lands transportation proviso; **DOJ tribal law enforcement $225,000,000**; plus
EPA STAG tribal set-asides. Separately, §1402 created a **$2,000,000,000** national Tribal
Economic Development Bond limitation (26 U.S.C. 7871(f)) — a **tax expenditure that produces
no award row at all**.

> **The ~$2.05B tribal total often quoted is arithmetic on those line items, not an
> agency-published aggregate.** GAO (`gao.gov` returns HTTP 403) and CRS
> (`crsreports.congress.gov` returns 520/403) could not be reached to corroborate it.
> **UNVERIFIED as an aggregate.** Cite the line items, not the sum.

**CITATION — measured, 2026-08-26.** Assistance Listings whose *title* contains `RECOVERY`
or `ARRA`:

| FY | rows | $ |
|---|---:|---:|
| 2008 | 9 | $6.9M |
| **2009** | **1,367** | **$918.2M** |
| 2010 | 404 | $140.0M |
| 2011 | 48 | $25.7M |

FY2009's top ARRA-named lines: **14.882** NAHBG (Formula) Recovery $241M · **14.887** NAHBG
(Competitive) Recovery $226M · **16.811** Recovery Act – Correctional Facilities on Tribal
Lands $220M. Against a FY2008→FY2009 rise of **$3.70B**, ARRA-named listings explain
**$918.2M — under a quarter of it.** The rest flowed through ordinary listings with no ARRA
marker in our schema.

**TWO TRAPS.** (1) A `RECOVERY` substring filter **also catches 21.027 "Fiscal Recovery
Funds"** and returns $20.24B for FY2021. It is not an ARRA filter. (2) ARRA awards carry
§1512 recipient-reporting flags at source; **we do not hold that field.**

---

### A6 · `CFDA_TO_ASSISTANCE_LISTINGS` · **REGIME_CHANGE** — join on the number, never the title

CFDA was renamed *Assistance Listings* and moved to SAM.gov in 2018. **Numbers largely
persisted; titles and groupings did not.** Our own file shows the drift: `93.575 CHILD CARE
AND DEVELOPMENT BLOCK GRANT` and `93.596 CHILD CARE MANDATORY AND MATCHING FUNDS…` are
separately populated in different years for related money. **Never build a programme series
on `cfda_title`.** *(Carried from `docs/ANOMALY_REPORT.md`; the SAM.gov migration date itself
is **UNVERIFIED** here because `api.sam.gov` is owned by another agent.)*

---

### A7 · `ISDEAA_INSTRUMENT` **NEW** · **STRUCTURAL / UNVERIFIED**

BIA and IHS money moves through both ISDEAA Title I self-determination **contracts** and
Title IV self-governance **compacts/AFAs**. **No free official source was found stating how
each is reported — FPDS contract row or assistance row.** This matters because ARPA §11001's
$6.094B IHS and §11002's $900M BIA may appear on either side of our prime/assistance split,
or be split across both. **Do not assume BIA/IHS relief money is assistance.** Verify against
award records before building a series. Flagged **UNVERIFIED** deliberately.

---

## B. TRIBAL SINGLE AUDITS — `fac_tribal_single_audits.csv` (6,780 rows, audit years 2016–2026)

### B1 · Coverage floor, stated first

**Our holdings begin at audit year 2016.** The 1984/1996/2003 threshold history below is
therefore *context*, not a break inside our data — but it is the reason a reader cannot
extend this collection backwards, and the 2014 and 2024 moves DO bind on it.

| audit year | reports | public | non-public |
|---|---:|---:|---:|
| 2016 | 670 | 264 | 406 |
| 2017 | 677 | 250 | 427 |
| 2018 | 677 | 221 | 456 |
| 2019 | 696 | 233 | 463 |
| 2020 | 749 | 224 | 525 |
| 2021 | 789 | 237 | 552 |
| 2022 | 778 | 210 | 568 |
| 2023 | 715 | 183 | 532 |
| 2024 | 655 | 147 | 508 |
| 2025 | 372 | 82 | 290 |
| 2026 | 2 | 1 | 1 |

**2025 and 2026 are incomplete filings, not a collapse.**

### B2 · `SINGLE_AUDIT_THRESHOLD` · **THRESHOLD** — and it is measurable in our own file

**CITATIONS — statute and regulation, each with its own applicability rule, which differ in kind:**

| threshold | authority | applicability |
|---|---|---|
| $100,000 / $25,000 | Single Audit Act of 1984, Pub. L. 98-502 §2 (31 U.S.C. 7502, 7507). https://www.govinfo.gov/content/pkg/STATUTE-98/pdf/STATUTE-98-Pg2327.pdf | `This chapter shall apply to any State or local government with respect to any of its fiscal years which begin after December 31, 1984.` **State and local governments only — non-profits and tribal organisations are outside the population entirely.** |
| **$300,000** | Single Audit Act Amendments of 1996, Pub. L. 104-156 §2. https://www.govinfo.gov/content/pkg/PLAW-104publ156/html/PLAW-104publ156.htm | `…any of its fiscal years which begin after June 30, 1996.` Test changes from *receives* to **`expends`**; non-profits brought in |
| **$500,000** | OMB, **68 FR 38401** (2003-06-27). https://www.federalregister.gov/documents/2003/06/27/03-16355/audits-of-states-local-governments-and-non-profit-organizations | `effective for fiscal years ending after December 31, 2003` — a **fiscal years ENDING** rule, so the cohort boundary smears through calendar 2004 |
| **$750,000** | Uniform Guidance, **78 FR 78590** (2013-12-26), 2 CFR 200.501(a) | `applies to audits of fiscal years beginning on or after December 26, 2014` — a Dec-26 hinge, so a Sept-30 auditee's first covered year is FY2016 |
| **$1,000,000** | OMB, **89 FR 30046** (2024-04-22), doc. 2024-07496; Part 200 at 89 FR 30136 | effective **2024-10-01**; applicable to **auditee fiscal years beginning on or after 2024-10-01** |

Current 2 CFR 200.501(a), retrieved verbatim from eCFR
(https://www.ecfr.gov/current/title-2/subtitle-A/chapter-II/part-200/subpart-F/section-200.501):

> `(a) Audit required. A non-Federal entity that expends $1,000,000 or more during the non-Federal entity's fiscal year in Federal awards must have a single or program-specific audit conducted for that year in accordance with the provisions of this part.`

OMB's own estimate of what the 2003 move did, verbatim from 68 FR 38401:
> `The revision increases the audit threshold from $300,000 to $500,000. This increase relieves almost 6,000 entities from the audit requirements of Circular A-133…`

**A DOCUMENTARY ODDITY WORTH RECORDING.** The 2024 revision **deleted** the old 2 CFR
200.110(b) audit-applicability sentence, and the phrase *"fiscal years beginning on or after
October 1, 2024"* **appears nowhere in 89 FR 30046 and nowhere in the CFR.** The applicability
rule survives only in OMB's **2025 Compliance Supplement**, Part 1 p. 1-1
(https://www.fac.gov/assets/compliance/2025-Compliance-Supplement.pdf):
> `On April 22, 2024, OMB issued revisions to 2 CFR Part 200, Subpart F, which, among other things, increased the audit threshold to $1,000,000 for auditee fiscal years beginning on or after October 1, 2024.`
Corroborated by the FAC glossary: `Prior to October 1, 2024, this was $750,000. After October 1, 2024, this is $1 million.`
**Cite the Compliance Supplement for the applicability rule, not the CFR or the FR notice.**

**CITATION — measured, 2026-08-26, and the threshold is visible working.** Count of tribal
audits reporting `total_amount_expended` below each threshold:

| audit year | reports | below $750k | below $1M |
|---|---:|---:|---:|
| 2016 | 670 | **0** | 42 |
| 2019 | 696 | **0** | 52 |
| 2022 | 778 | **4** | 22 |
| 2024 | 655 | **0** | 15 |
| **2025** | 372 | **0** | **0** |
| **2026** | 2 | **0** | **0** |

**Not one tribal audit in ten years reports expenditures below $750,000, except four in 2022.**
That is not a property of Indian Country; it is the threshold. And the 14–52 audits per year
in the **$750k–$1M band go to zero in 2025** — the first fiscal years under the $1,000,000
rule. **If our panel ends in 2026, the bottom of the entity distribution drops out in the
final two years and will read as a collapse in small-entity federal spending. It is not.**

### B3 · `FAC_TRIBAL_OPT_OUT` **NEW** · **SUPPRESSION** — 4,728 of 6,780 records

**CITATION — regulation. The cite in `START_HERE.md` is wrong and must be corrected: the
opt-out is 2 CFR 200.512(b)(3), not (b)(2).** (b)(2)(iv) is the authorisation that (b)(3)
lets a tribe exclude. Retrieved verbatim from
https://www.ecfr.gov/current/title-2/subtitle-A/chapter-II/part-200/subpart-F/section-200.512:

> `(3) An auditee that is an Indian Tribe or a tribal organization (as defined in the Indian Self-Determination, Education and Assistance Act (ISDEAA), 25 U.S.C. 450b(l)) may opt not to authorize the FAC to make the reporting package publicly available on a website. To opt-out, an Indian Tribe or tribal organization must exclude the authorization described in paragraph (b)(2)(iv) of this section.`

And the FAC's reciprocal duty at (g):
> `The FAC must make available the reporting packages … to the public, except for Indian Tribes exercising the option in paragraph (b)(3) of this section…`

**There is no separate Indian-tribe provision in 2 CFR 200.501.** The complete current text
of §200.501(a)–(i) mentions neither Indian Tribes nor ISDEAA. **The tribal carve-out affects
PUBLICATION, never COVERAGE.** A tribe over $1,000,000 must be audited exactly like anyone
else; it may simply decline to have the package posted.

**FOUR THINGS THAT FOLLOW, AND ALL FOUR ARE PUBLISHABLE:**

1. **The non-public 4,728 are not missing data.** The audits exist and were submitted. Only
   the *reporting package* is withheld. `START_HERE.md` already records what survives the
   withholding, measured on matched samples of 25: `federal_awards` (SEFA) serves **25/25 for
   both** public and non-public auditees; `notes_to_sefa`, findings and corrective actions
   serve **25/25 public, 0/25 non-public**; the reporting-package PDF **403s**.
2. **The opt-out is exercised per submission, by excluding a checkbox, with no notice
   requirement and no register of who opted out.** So **public/non-public is not a fixed
   attribute of a tribe** and must never be treated as one.
3. **The opt-out rate is itself a variable.** Measured: public share falls **39.4% (2016) →
   22.4% (2024)**. That trend is a disclosure-behaviour trend, and it is a genuine finding —
   but it is a finding about *disclosure*, not about auditing or about money.
4. **Selection is not random.** Publishing is the default; withholding is an affirmative act.
   **Any comparison of public tribal audits against public non-tribal audits compares a
   self-selected subset to a census.**

---

## C. LOBBYING — `native_entity_lobbying_disclosures.csv` (27,796 filings, 1999–2026) and `code/lobbying_pull/raw_filings.jsonl` (39,448)

### C1 · `HLOGA_QUARTERLY` · **REGIME_CHANGE** — FOUR simultaneous breaks on 2008-01-01

**This is the most dangerous single date in the whole product**, because our lobbying series
runs 1999–2026 and every filing-count trend in it crosses this break.

**CITATION — statute, the original semiannual rule.** Lobbying Disclosure Act of 1995,
Pub. L. 104-65 §5(a), approved 1995-12-19, effective 1996-01-01 (§24(a)).
https://www.govinfo.gov/content/pkg/PLAW-104publ65/html/PLAW-104publ65.htm
> `(a) Semiannual Report.--No later than 45 days after the end of the semiannual period beginning on the first day of each January and the first day of July of each year in which a registrant is registered under section 4, each registrant shall file a report…`

And the original dollar convention, §5(c) — **the item most likely to corrupt a dollar series**:
> `(1) Estimates of amounts in excess of $10,000 shall be rounded to the nearest $20,000.`
> `(2) In the event income or expenses do not exceed $10,000, the registrant shall include a statement that income or expenses totaled less than $10,000 for the reporting period.`

**CITATION — statute, the change.** Honest Leadership and Open Government Act of 2007,
Pub. L. 110-81, approved **2007-09-14**.
https://www.govinfo.gov/content/pkg/PLAW-110publ81/html/PLAW-110publ81.htm

Applicability, §215, verbatim:
> `Except as otherwise provided in sections 203, 204, 206, 211, 212, and 213, the amendments made by this title shall apply with respect to registrations under the Lobbying Disclosure Act of 1995 having an effective date of January 1, 2008, or later and with respect to quarterly reports under that Act covering calendar quarters beginning on or after January 1, 2008.`

§201(a)(1), verbatim: `by striking "Semiannual" and inserting "Quarterly"` … `by striking "45 days" … and inserting "20 days after the end of the quarterly period…"`

§201(b)(5)–(6), verbatim: registration thresholds `$5,000`→`$2,500` and `$20,000`→`$10,000`;
§5(c) rounding `$10,000`/`$20,000`→`$5,000`/`$10,000`, and the censoring statement `$10,000`→`$5,000`.

**THE FOUR BREAKS, ALL ON 2008-01-01:**
1. Reporting frequency semiannual → quarterly — **filing counts roughly double**
2. Dollar rounding grain **$20,000 → $10,000**
3. Dollar censoring point **$10,000 → $5,000**
4. Registration thresholds halved and re-denominated per quarter

**CITATION — measured, 2026-08-26, and it is exactly as sharp as the statute predicts.**
Filings by year and filing-type class in `native_entity_lobbying_disclosures.csv`:

| year | quarterly types | semiannual/other | total filings |
|---|---:|---:|---:|
| 2005 | **0** | 614 | 650 |
| 2006 | **0** | 584 | 635 |
| 2007 | **0** | 669 | **712** |
| **2008** | **1,120** | 76 | **1,344** |
| 2009 | 1,034 | 44 | 1,210 |
| 2010 | 1,010 | 59 | 1,187 |

**Zero quarterly-type filings in every year 1999–2007; 1,120 in 2008. There is no transition.**
Filings rise **712 → 1,344, +88.8%**, and the mean goes from **562 (1999–2007)** to **1,222
(2009–2025)**, a ratio of **2.17**. The independent raw corpus reproduces it: 1,087 → 1,940.

**The registrant-concentration series in `docs/ANOMALY_REPORT.md` crosses this break.** A
top-5 share computed on filings is a share of a denominator that doubled mid-series.
**Recompute on dollars, or on unique registrant-client pairs per year, or restrict to 2008+.**

### C2 · `LD203` **NEW** · **REGIME_CHANGE** — a new form type appearing mid-2008

**CITATION — statute.** HLOGA §203, adding LDA §5(d), and §203(b) applicability:
> `The amendment made by subsection (a) shall apply with respect to the first semiannual period described in section 5(d)(1) … that begins after the date of the enactment of this Act`
— i.e. **January–June 2008, filed by 2008-07-30.** §203 is expressly carved out of §215, so
LD-203 runs on its own semiannual clock and **remains semiannual to this day**.

**CITATION — measured.** The House Clerk's LC (LD-203) bulk archive begins exactly at
`2008_MidYear_XML.zip` — 38 files, earliest 2008 MidYear, latest 2026 YearEnd
(https://disclosurespreview.house.gov/data/LC/LcSearchPastFilings.json).

**LD-203 is filed PER LOBBYIST, not per registrant-client.** Pooling LD-203 with LD-1/LD-2
adds a second, independent mid-2008 jump on top of the quarterly doubling, scaled by lobbyist
headcount. **Segregate form types before counting anything.**

### C3 · `LDA_NO_DOLLAR` **NEW** · **REPORTED_EMPTY + THRESHOLD** — the 41.3% decomposes cleanly

**CITATION — guidance.** Joint *Lobbying Disclosure Act Guidance*, revised 2025-02-28
(https://lobbyingdisclosure.house.gov/ldaguidance.pdf), §6:
> `The quarterly activity report (LD-2) provides boxes for a lobbying firm to report income of less than $5,000, or of $5,000 or more. If lobbying income is $5,000 or more, a lobbying firm must provide a good faith estimate of the actual dollar amount rounded to the nearest $10,000.`

And the **second, independent** source of dollar-free filings — the mandatory no-activity report:
> `So long as a registration is on file and has not been terminated, a registrant must report its lobbying activities even if those activities during a particular quarterly period would not trigger a registration requirement in the first instance… A registrant with no lobbying activity during a quarterly period checks the "no activity" box on the quarterly activity report (LD-2).`

**CITATION — measured, 2026-08-26.** The no-dollar population, decomposed (Senate report-type
`Y` suffix marks a no-activity report):

| class | filings | share |
|---|---:|---:|
| **HAS A DOLLAR** | 16,492 | **59.3%** |
| `NO_ACTIVITY_REPORT` (`Y`-suffix types) | 5,308 | **19.1%** |
| `BELOW_FLOOR_OR_UNSTATED` (the "less than $5,000" box) | 4,061 | **14.6%** |
| `REGISTRATION/AMENDMENT` (`RR`, `RA`) — no dollar field by construction | 1,428 | 5.1% |
| `AMENDMENT/TERMINATION` | 507 | 1.8% |

**So the alarming "41.3% report no dollar" is really: 19.1% affirmatively reported ZERO
ACTIVITY, 6.9% are forms with no dollar field at all, and only 14.6% is genuine below-floor
spending.** And the below-floor share is stable at **10–13% before 2008 and 11–20% after** —
it is not a trend.

**A REPORTED ZERO IS A FACT ABOUT THE REGISTRATION, NOT ABOUT THE TRIBE.** A tribe with a live
registration and no lobbying that quarter is legally required to file saying so. Reading those
5,308 filings as "lobbied for $0" is right; reading them as evidence of the tribe's absence
from Washington is wrong.

**AND THE DOLLARS ARE A LATTICE, NOT A CONTINUUM.** Post-2008 values are quantised to $10,000;
pre-2008 to $20,000. **Do not compute means, medians or Gini coefficients on this column
across 2008 without saying so.**

### C4 · `LDA_CPI` **NEW** · **THRESHOLD** — the registration floor rises every four years

**CITATION — statute.** 2 U.S.C. 1603(a)(3)(B) (originally Pub. L. 104-65 §4(a)(3)(B)):
> `The dollar amounts in subparagraph (A) shall be adjusted-- (i) on January 1, 1997 … and (ii) on January 1 of each fourth year occurring after January 1, 1997, to reflect changes in the Consumer Price Index … rounded to the nearest $500.`

The adjustment fires **1997, 2001, 2005, 2009, 2013, 2017, 2021, 2025** — eight step-changes
in who must appear at all.

**CITATION — current values, guidance, verbatim:**
> `After January 1, 2025, an organization employing in-house lobbyists is exempt from registration if its total expenses for lobbying activities do not exceed and are not expected to exceed $16,000 during a quarterly period. The new income threshold for lobbying firms is $3,500.`

**Current: $3,500 / $16,000, effective 2025-01-01.** *(The "$3,000 / $14,000" figures in
circulation are stale.)*

**UNVERIFIED: the intermediate adjusted values for 1997, 2001, 2005, 2009, 2013, 2017 and
2021.** The current guidance supersedes all prior revisions and carries no history table;
`lobbyingdisclosure.house.gov/amended_lda_guide.html` 404s and CRS returned 404/520. **Do not
assert an intermediate threshold value without retrieving an archived guidance revision or
the relevant-year GAO LDA compliance report.**

### C5 · `LDA_BULK_FLOOR` **NEW** · **STRUCTURAL** — the House archive does not reach 1999

**CITATION — measured from the manifest**
(https://disclosurespreview.house.gov/data/LD/LdSearchPastFilings.json): **113 LD files,
earliest `2002_MidYear_XML.zip`.** The arithmetic reconciles exactly — 6 years × 3 files
(2002–2007) + 19 years × 5 files (2008–2026) = 113. **There are no 1999, 2000 or 2001 files.**
The Senate-side search UI does offer 1999–2026.

**Our series claims 1999–2026 and carries 397/451/500 filings for those three years.** They
did not come from House bulk XML. **Establish and state their provenance before plotting
them** — a count that begins where the ZIPs begin reads as a spurious level shift at the left
edge of a chart.

### C6 · `HOUSE_LDA_SUNSET` **NEW** · **ACCESS** — a live risk, not a limitation

`disclosurespreview.house.gov` carries the notice: `Beginning July 31, 2026, this site will be
unavailable, except for the ability to download ZIP files.` API users are directed to LDA.gov;
`lda.senate.gov` already 301s to `lda.gov`. **If our pipeline calls the House REST API it is
on borrowed time.** Page footer `Last Updated: 2026-06-17`.

### C7 · Two standing traps carried forward from `AGENTS.md`

- **`native_entity_lobbying_disclosures.csv` contains no nonprofits.** Zero of the spine's 55
  intertribal organisations appear; NCAI, NIGA, USET, NIHB, NARF, NAIHC and NCUIH sit in
  `lobbying_unmatched_clients.csv`. **Any question about *organisational* Native advocacy must
  read the raw corpus, not the keyed file.**
- **LDA client state is the FILING address, not the client's.** 941 disagreements are `DC`.

---

## D. NAGPRA NOTICES — `nagpra_notices.csv` (6,729 notices, 1994–2026)

### D1 · `NAGPRA_2024_RULE` · **REGIME_CHANGE** — the surge is largely regulatory, and the mechanism is visible

**CITATION — measured, 2026-08-26.** Notices per publication year, with the two diagnostic
categories:

| year | notices | `culturally_unidentifiable` | `intended_disposition` |
|---|---:|---:|---:|
| 2018 | 211 | 60 | — |
| 2019 | 202 | 53 | — |
| 2020 | 163 | 51 | — |
| 2021 | 169 | 33 | — |
| 2022 | 244 | 44 | — |
| **2023** | **496** | **3** | — |
| **2024** | **707** | **0** | **37** |
| **2025** | **900** | **0** | **70** |
| 2026 (partial) | 570 | 0 | 18 |

Median 1994–2022 is ~160 notices/year. **2025 is 5.6× that.**

**THE MECHANISM IS IN THE CATEGORIES, AND IT IS DECISIVE.** The
`culturally_unidentifiable` class runs 33–70 per year from 2006 through 2022, collapses to
**3 in 2023**, and is **0 in every year from 2024**. A brand-new notice type,
`intended_disposition`, appears in **2024** and nowhere before. **Both are exactly what a
revision that removed the "culturally unidentifiable" category and elevated the Notice of
Intended Disposition would do.** That is a regulatory fingerprint, not a behavioural one.

**BUT THE SURGE STARTS IN 2023, A YEAR BEFORE THE RULE BOUND — AND THAT PART IS NOT
EXPLAINED.** 2022 → 2023 is 244 → 496, a doubling entirely inside the old regime. Candidate
causes: the proposed rule and its comment period; institutional anticipation; external
pressure on museums during 2023. **None of these is verified here. Do not close this by
picking one.** State the 2024 step as regulatory and the 2023 step as open.

### D2 · The mechanism, in the regulation's own words — the trigger went from CONDITIONAL to UNIVERSAL

**CITATION — the rule before.** 43 CFR 10.9(e)(1), text in force through 2024-01-11
(eCFR historical snapshot 2023-12-01):
> `(e) Notification. (1) If the inventory results in the identification or likely identification of the cultural affiliation of any particular human remains or associated funerary objects with one or more Indian tribes or Native Hawaiian organizations, the museum or Federal agency, not later than six (6) months after completion of the inventory, must send … a notice of inventory completion…`

**CITATION — the rule now.** 43 CFR 10.10(e), current
(https://www.ecfr.gov/current/title-43/section-10.10):
> `(e) Step 5—Submit a notice of inventory completion. No later than six months after completing or updating an inventory under paragraph (d) of this section, a museum or Federal agency must submit a notice of inventory completion for all human remains or associated funerary objects in the inventory.`

**The trigger changed from "*if* cultural affiliation is identified" to "**for all** human
remains … in the inventory."** Remains that previously produced **no** notice — because no
affiliation could be found — now produce one, carrying a §10.10(d)(1)(iii)(D) determination
that `No lineal descendant or any Indian Tribe or Native Hawaiian organization with cultural
affiliation can be clearly or reasonably identified.` **That is a mechanical expansion of the
notice-generating population, not a change in institutional willingness to repatriate.**

**CITATION — the category was deleted, not renamed.** Preamble to 88 FR 86452:
> `DOI Response: These regulations do not use the term "culturally unidentifiable" …`

Structurally: in the 2023-12-01 CFR, §10.11 was *Disposition of culturally unidentifiable
human remains*. In the current CFR, **§10.11 is *Civil penalties*.** The section was removed
outright and its number reassigned. **This is why our `culturally_unidentifiable` column goes
to zero from 2024 — the category no longer exists in law.**

**CITATION — the deadline that bounds the surge.** 43 CFR 10.10(d)(3):
> `(3) No later than January 10, 2029, for any human remains or associated funerary objects listed in an inventory but not published in a notice of inventory completion prior to January 12, 2024, a museum or Federal agency must: (i) Initiate consultation … (iii) Update its inventory … (iv) Submit an updated inventory…`

Preamble, on why five years and not two:
> `4. Extended the timeline to allow five years (rather than two as proposed) for museums and Federal agencies to consult and update inventories…`

**A decades-old backlog is being compressed into a five-year window closing 2029-01-10.
Expect elevated counts through 2029 and a fall afterwards. Say so.** *(Note the deadline is
**January 10**, 2029, not January 12. Quote it exactly.)*

**CITATION — the rulemakings, all verified:**

| rule | FR citation | published | **effective** |
|---|---|---|---|
| Original 43 CFR Part 10 | **60 FR 62134** | 1995-12-04 | **1996-01-03** |
| Culturally unidentifiable remains | **75 FR 12378** | 2010-03-15 | **2010-05-14** |
| Revised Part 10 (RIN 1024-AE19) | **88 FR 86452** | **2023-12-13** | **2024-01-12** |

**Two date corrections our docs need:** the 2010 rule's break is at its **effective date
2010-05-14**, not its publication date; and **our 1994–1995 notices predate 43 CFR Part 10
entirely** — they were made under the bare statute. **Treat 1994–95 as a distinct regime, not
as the low end of a trend.**

### D3 · `NAGPRA_STATUTE` **NEW** · **STRUCTURAL** — and an asymmetry that defines what this collection IS

**CITATION — statute.** Pub. L. 101-601, enacted **1990-11-16**, 104 Stat. 3048.
https://www.govinfo.gov/content/pkg/STATUTE-104/pdf/STATUTE-104-Pg3048.pdf

§5(b)(1)(B) — inventories `completed by not later than the date that is 5 years after the date
of enactment of this Act` (**1995-11-16**). §6(b)(1)(C) — summaries `completed by not later
than the date that is 3 years after the date of enactment` (**1993-11-16**).

§5(d)(3) — the publication duty:
> `A copy of each notice provided under paragraph (1) shall be sent to the Secretary who shall publish each notice in the Federal Register.`

**THE ASYMMETRY THAT DEFINES THIS COLLECTION: the Federal Register publication duty attaches
only to §5 notices (inventories / human remains). §6 summaries — unassociated funerary
objects, sacred objects, objects of cultural patrimony — carry NO publication requirement.**
Our collection is a census of the §5 line, **not** a census of NAGPRA compliance. Anyone
reading it as institutional-compliance coverage is reading half the statute.

### D4 · `NAGPRA_NOTICE_GRAIN` **NEW** · **STRUCTURAL** — count remains, not notices

**CITATION — regulation.** 43 CFR 10.10(e):
> `The museum or Federal agency may include in a single notice any human remains or associated funerary objects having the same determination under paragraph (d)(1)(iii) of this section.`

**Notices may be combined. So notice counts and remains counts diverge, and
notices-per-remains is not constant across the 2024 break.** For any volume claim, **count
remains, not notices.**

### D5 · The magnitude is NOT quantified, and one table must not be misused

**No NPS or preamble statement projects the number of notices under the new rule versus the
old.** The full 666 KB rule text yields three hits on "number of notices," none of them a
projection. **The claim "the 2024 rule was expected to increase notice volume by N" cannot be
sourced and must not be made.** The mechanism is documented; the magnitude is not.

The closest defensible proxy, verbatim from 88 FR 86452:
> `we estimate 407 museums and 122 Federal agencies will be required to update inventories within five years after promulgation of a final rule.`
**Label it as a count of institutions required to update inventories, not of notices.**

**⚠ AND A TRAP.** The rule's **Table 7** shows `+14` responses and `+36,725.25` annual hours.
**That compares the 2022 proposed-rule baseline against the 2023 final-rule baseline — two
estimates of the EXISTING burden, revised after comments. It is not a before/after estimate
of the rule's effect.** Citing "+14" as "NPS expected only 14 more filings" would be a serious
misread and is recorded here so nobody makes it.

---

## E. PRIME CONTRACTS — `prime_contracts.csv` (1,217,768 rows, $310.01B, FY2000–2026)

### E1 · `ACQUISITION_THRESHOLDS` · **THRESHOLD** — a small-contract count is a threshold series

Contracts below the micro-purchase threshold are not reported to FPDS. The threshold moved
repeatedly across our window, so **a change in "number of small contracts" may be a threshold
change rather than a change in contracting behaviour.**

**CITATION — measured, 2026-08-26.** Positive-obligation rows at or below each historic
micro-purchase level:

| FY | positive rows | ≤$2,500 | ≤$3,000 | ≤$3,500 | ≤$10,000 |
|---|---:|---:|---:|---:|---:|
| 2005 | 16,094 | 2,023 | 2,413 | 2,798 | 5,696 |
| 2006 | 23,721 | 8,463 | 8,840 | 9,199 | 12,035 |
| 2010 | 44,610 | 3,758 | 4,324 | 5,054 | 12,635 |
| 2015 | 36,386 | 4,602 | 5,222 | 5,912 | 11,584 |
| 2020 | 38,782 | 4,084 | 4,514 | 4,929 | 9,283 |
| 2024 | 32,551 | 5,275 | 5,623 | 6,006 | 8,863 |
| **2026** | **48,784** | **35,088** | **35,672** | **36,172** | **38,558** |

**CITATION — the thresholds, every move dated, and three figures in circulation are wrong:**

| date | micro-purchase | SAT | authority |
|---|---|---|---|
| 1994-10-13 | **$2,500** | **$100,000** | FASA, Pub. L. 103-355 §§4301(a), 4001 |
| **2006-09-28** | **$3,000** | $100,000 | FAC 2005-**13**, FAR Case 2004-033, 71 FR 57363 |
| **2010-10-01** | $3,000 | **$150,000** | FAC 2005-**45**, 75 FR 53129 |
| **2015-10-01** | **$3,500** | $150,000 (`unchanged`) | FAC 2005-**83**, 80 FR 38293 |
| **2020-08-31** | **$10,000** | **$250,000** | FAR Case 2018-004, 85 FR 40064 (statutes: Pub. L. 115-91 §§805, 806, 2017-12-12) |
| **2025-10-01** | **$15,000** | **$350,000** | FAC 2025-06, 90 FR 41872 |

**Corrections: the SAT moved to $150,000 in 2010, not 2015** (the 2015 rule says `The
simplified acquisition threshold (FAR 2.101) of $150,000 is unchanged`); **the circulars were
FAC 2005-13 and 2005-83, not 2005-11 and 2005-82**; and **there is no $13,000 micro-purchase
step — the sequence is $2,500 → $3,000 → $3,500 → $10,000 → $15,000.**

**CITATION — the FPDS floor IS the micro-purchase threshold, and has been since 2008-04-22.**
FAR Case 2004-038 (73 FR 21773) redefined a reportable contract action as one `using
appropriated dollars over the micro-purchase threshold`; before that, FAR 4.602(c) carried a
hard-coded figure that the 2006 rule moved in lockstep with the MPT.

FAR 4.606 as it now stands (https://www.acquisition.gov/far/4.606):
> `(a)(1) As a minimum, agencies must report the following contract actions over the micro-purchase threshold … and agencies must report any modification to these contract actions that change previously reported contract action data, regardless of dollar value:`
> `(b) Reporting other actions. Agencies may submit actions other than those listed … only if they are able to be segregated from FAR-based actions and this is approved in writing by the FPDS Program Office … (1) Transactions at or below the micro-purchase threshold…`
> `(c)(1) Imprest fund transactions below the micro-purchase threshold, including those made via the Government purchase card` — **not to be reported.**

**AND 41 U.S.C. 1908(d) MAKES EACH MOVE A SAME-DAY DISCONTINUITY ACROSS THE WHOLE LIVE STOCK:**
> `The thresholds take effect on the date of publication and shall apply, in the case of the procurement of property or services by contract, to a contract, and any subcontract at any tier under the contract, in effect on that date without regard to the date of award of the contract or subcontract.`

**So: a fall in "number of small contract actions" across 2020-08-31 is at minimum definitional
— the reporting floor TRIPLED, $3,500 → $10,000, overnight.** You can only interpret a
small-action count after conditioning on a band lying entirely above the highest MPT in the
window (≥ $15,000 for any series reaching FY2026).

**PURCHASE CARDS ARE PRESENT IN DOLLARS AND ABSENT FROM COUNTS.** Individual card
transactions below the MPT are expressly not reported (4.606(c)(1)), but FAR 4.606(a)(2)
provides that `The GSA Office of Charge Card Management will provide the Government purchase
card data, at a minimum annually, and GSA will incorporate that data into FPDS for reports.`
**Card spend enters FPDS as a periodic aggregate feed, not as transaction-level rows** — so it
is in dollar totals, structurally invisible in action counts, and annual-lumpy in timing.

**AND THE FY2026 OUTLIER IS NOW CLOSED — the answer is in FAR 4.606(a)(1).** 71.9% of FY2026
positive obligations are ≤ $2,500 and the median is **$443**, against 8–20% in every other
year. No threshold moved downward — the MPT went *up* to $15,000 on 2025-10-01, the first day
of FY2026. The rule explains it: **modifications are reported `regardless of dollar value`.**
FY2026 as we hold it is a partial year dominated by small modifications to existing awards
rather than new awards. **Do not publish an FY2026 contract *count*, and do not compare
FY2026 action counts to any earlier year.** *(Recorded for `code/227_anomaly_sweep.py`: this
anomaly is explained, and the explanation is a reporting rule.)*

### E1b · `NATIVE_SETASIDE_CODE_SPLIT` **NEW** · **REGIME_CHANGE** — the seam that would have produced a false headline

**This is the single most dangerous unrecorded artefact found today.** Measured,
2026-08-26, `setaside` row counts:

| FY | `Buy Indian` | `Indian Business` | **combined** |
|---|---:|---:|---:|
| 2012 | 492 | **0** | 492 |
| 2013 | 489 | **0** | 489 |
| 2014 | 830 | **7** | 837 |
| **2015** | **1,109** | 29 | 1,138 |
| **2016** | **417** | **935** | 1,352 |
| 2017 | 303 | 1,047 | 1,350 |
| 2020 | 268 | 1,178 | 1,446 |
| 2022 | 485 | 1,528 | 2,013 |

**`Indian Business` is ZERO in every fiscal year 2000–2013.** It first appears in FY2014 (7
rows), and across FY2015→FY2016 the two series are near mirror images: Buy Indian −692,
Indian Business +906.

**Read alone, `Buy Indian` says Native set-asides collapsed by 62% after 2015. Combined, they
say Native set-asides rose 44%.** The first reading is false and would have been publishable.

**CITATION — the regulatory mechanism.** DOI's Buy Indian Act acquisition regulation, 48 CFR
Part 1480, created a **two-tier** structure — `Indian Economic Enterprise` (IEE) and
`Indian Small Business Economic Enterprise` (ISBEE) — with separate solicitation notices at
48 CFR 1452.280-1 `Notice of Indian Small Business Economic Enterprise Set-aside (JUL 2013)`
and 1452.280-2. Final rule **78 FR 34266**, published 2013-06-07: `This rule is effective on
July 8, 2013.` **The second code appears in our data the fiscal year after the regulation that
created the second instrument.**

**AND THE TWO BUY INDIAN AGENCIES ARE ON DIFFERENT CLOCKS — a second, later break.** IHS/HHS
did not adopt the IEE/ISBEE architecture until **87 FR 2067**, published 2022-01-13:
`This rule is effective March 14, 2022.` The predecessor HHSAR subpart (80 FR 72151, effective
2015-12-18) used the term `Indian firm` and had **no** IEE/ISBEE tiering, no offeror
representation, and no challenge procedure. *(The "IHS Buy Indian final rule of 2013" in
circulation does not exist: a full Federal Register term search on "Buy Indian Act" returns
exactly one 2013 rule and it is Interior's.)*

**THE RULE THIS EARNS: `reported_buy_indian` and `reported_indian_business` must always be
summed. Neither is a time series on its own.** And a pooled DOI+IHS "Buy Indian over time"
series manufactures a 2022 discontinuity that is purely regulatory.

### E1c · `CONTRACT_COUNT_REGIMES` **NEW** · **REGIME_CHANGE** — three more dates under any "number of contracts" series

Consolidation and bundling rules change **how many contract actions a fixed volume of
procurement generates, without changing the dollars.**

| date | what | authority |
|---|---|---|
| **2013-12-31** | Task/delivery order contracts, bundling, consolidation | 78 FR 61114 |
| **2016-10-31** | FAR 7.107 consolidation/bundling implementing Small Business Jobs Act §1313 (Pub. L. 111-240, 2010-09-27), written determination required above **$2,000,000** | **81 FR 67763** |
| **2020-03-30** | Set-Asides Under Multiple-Award Contracts — changes whether a set-aside flag attaches to an **order** or a **base contract** | 85 FR 11746 |

*(There is no 2020 FAR consolidation rule; the 2020 rule is the order-level set-aside rule.
FAR 7.107's own source note is `[81 FR 67770, Sept. 30, 2016]`.)*

**Any series of the form "number of Native-flagged contract actions per year" crosses at least
six regime boundaries: 2011-03-16, 2013-07-08, 2013-12-31, 2016-10-31, 2020-03-30 and
2022-03-14. Report dollars and counts separately, and never read a count trend across these
dates as behaviour.**

### E1d · `EIGHT_A_JA_2011` **NEW** · **REGIME_CHANGE** — a behaviour break, not just paperwork

**CITATION — statute.** NDAA for FY2010, **Pub. L. 111-84 §811**, enacted **2009-10-28**
(not 2010): `the head of an agency may not award a sole-source contract in a covered
procurement for an amount exceeding $20,000,000 unless-- (1) the contracting officer … justifies
the use of a sole-source contract in writing; (2) the justification is approved …; and (3) the
justification and related information are made public…`

**CITATION — FAR implementation.** Interim rule **76 FR 14559**, `Effective Date: March 16,
2011`; final rule 77 FR 23369, effective 2012-04-18. The preamble is explicit that it is not a
cap: `The requirement for a J&A is not a ceiling or a "cap" on sole-source awards over $20
million for 8(a) contractors.`

**From 2011-03-16 every 8(a) sole-source award above $20M — exactly the band where large
tribal and ANC awards live — required a written, approved, publicly posted justification.**
Expect a deterrent effect on award size, bunching just under the threshold, and post-2011
awards being far more visible in public data than pre-2011 ones. **Treat FY2011 as a regime
boundary in any tribal/ANC sole-source series**, and note the bunching point has since moved
(13 CFR 124.506(b)(5) now says $25M, $100M for DoD; FAR 19.808-1 says $30M — **the two
authorities disagree as retrieved, so name the source and vintage with any figure**).

**And the affiliation exemption is why the dollars concentrate**, 13 CFR 124.109(c)(2)(iii):
> `In determining the size of a small business concern owned by a socially and economically disadvantaged Indian tribe … the firm's size shall be determined independently without regard to its affiliation with the tribe, any entity of the tribal government, or any other business enterprise owned by the tribe…`

**NHOs are NOT symmetric with tribes and ANCs.** 13 CFR 124.506(b)(2) gives an NHO-owned
concern the above-threshold sole-source exemption only for **Department of Defense** contracts.
**A "Native-owned sole source" series pooling NHO with tribal/ANC carries a built-in
agency-mix effect.**

### E1e · `INDIAN_INCENTIVE_PROGRAM` **NEW** · **STRUCTURAL** — 5% that never appears as a Native prime row

**CITATION — statute.** 25 U.S.C. 1544, **Pub. L. 93-262 title V §504, as added by Pub. L.
100-442 §7, 1988-09-22** *(not Pub. L. 100-581, which amended 25 U.S.C. 47)*:
> `a contractor of a Federal agency … may be allowed an additional amount of compensation equal to 5 percent of the amount paid, or to be paid, to a subcontractor or supplier … if such subcontractor or supplier is an Indian organization or Indian-owned economic enterprise…`

DFARS 252.226-7001 (JAN 2023) carries it, at `5 percent of the estimated cost, target cost, or
fixed price included in the subcontract at the time of award`, flowed down `in all subcontracts
exceeding $500,000`.

**The Indian Incentive Program is a subcontract-level rebate paid to the PRIME. It never
appears as a Native-flagged prime contract row.** A "Native contracting dollars" series built
from prime rows omits it structurally. Presence or absence in any year also partly reflects
DoD's Indian Incentive Program appropriation, not tribal subcontracting.

### E2 · `PRIME_GRAIN_SEAM` **NEW** · **REGIME_CHANGE (ours, not the government's)**

**A BGOV row is an award-year-vendor aggregate. An archive row is a transaction.** `master
prime file.dta` carries **no `modification_number` and no `transaction_number`**: 507,564 BGOV
rows over 402,005 distinct (PIID, FY) — 1.26 rows per contract-year — against the archive's
2.14. **Row counts are NOT comparable across the seam**, and the seam is visible in
`source_file`, which is deliberately not rewritten on any row.

**CITATION — measured.** FY2007 → FY2008 rows go **28,844 → 60,446**. That doubling is the
grain change and the FY2008 archive floor, **not** a doubling of contracting.

### E3 · `EXTENT_COMPETED_VOCABULARY` · **REGIME_CHANGE (ours)** — and it is FIXED, but the raw column is not

`docs/CICD_BENCHMARK.md` `INTERNAL-05` recorded this as a BGOV-vs-archive era seam. **The
measurement says it is neither: it is a DOWNLOAD-VINTAGE artefact confined to FY2008–FY2016.**

| FY range | source stamp | token shape |
|---|---|---|
| FY2000–2007 | `master prime file.dta` | rendered labels (+9,420 blanks) |
| **FY2008–2016** | `*_20260806.zip` | **355,644 single-letter FPDS codes** + short alpha codes |
| FY2017–2026 | `*_20260706.zip` | rendered labels |

The single-letter codes appear **only** in files downloaded on 2026-08-06. **A filter on
rendered labels silently selects FY2000–2007 plus FY2017–2026 and drops nine fiscal years in
the middle** — a filter that manufactures a U-shaped trend out of nothing.

**IT IS ALREADY FIXED, AND THE FIX IS NOT DOCUMENTED ANYWHERE ELSE.**
`extent_competed_normalized` is populated on **1,217,768 of 1,217,768 rows (100%)**.
**Use `extent_competed_normalized`. Never filter on `extent_competed`.** Update `INTERNAL-05`
and `docs/ANOMALY_REPORT.md`, both of which still describe this as unfixed.

### E4 · `SETASIDE_GRAIN` · **REGIME_CHANGE (ours)** — "None reported" is a mixture, and two correct numbers are in circulation

**A SET-ASIDE IS A PROPERTY OF THE AWARD, NOT OF EACH MODIFICATION.** The USAspending archive
reports set-aside per transaction and leaves it **blank on ~56% of rows**; `master prime
file.dta` carries the award's value on every row. Read transaction-level the two disagree on
**59.6% of shared contracts**, and 4,580 contracts the `.dta` calls 8(a) land in "None
reported."

**AND OUR FILE RENDERS THOSE BLANKS AS `"None reported"`.** Measured: `setaside` has **zero
blank rows in either era**. So `"None reported"` **conflates "the award carried no set-aside"
with "this modification did not restate it."**

**TWO NUMBERS, BOTH CORRECT, ABOUT DIFFERENT THINGS:**

| figure | what it is | where |
|---|---|---|
| **$110.27B on 470,815 rows (45.1% of attributed)** | raw `setaside == "None reported"`, transaction-level, **contaminated by the blank-rendering** | measured here |
| **$140.00B on 565,364 rows (57.2% of attributed)** | set-aside **forward-filled to award level** on (contract_number, awardee_uei); no Native set-aside of any kind | `docs/CICD_BENCHMARK.md` `UNDERCOUNT-01` |

**The $140.00B figure is the publishable one. Say that it is forward-filled, in the same
sentence.** Quoting $110.27B as "no set-aside" understates by $30B and is measuring our
rendering.

Native-specific set-asides, measured on attributed dollars: **Buy Indian $0.49B + Indian
Business $0.71B = $1.20B, 0.49% of $244.77B.** 8(a) is $97.33B (39.8%).

### E5 · `CAGE_COVERAGE_SEAM` **NEW** · **REGIME_CHANGE (ours)**

**CITATION — measured.** `cage_code` populated: **0.2–0.5% FY2000–2007** (BGOV era) ·
**66–73% FY2008–2016** · **91.1% FY2017** · **100% FY2018–2026**. `awardee_uei` is 100% on
every row of every year — because it was **backfilled**, not because it was reported.
**A CAGE-based method applied across FY2017 measures our download vintages.**

### E6 · `FY2023_ATTRIBUTION_BOUNDARY` · **REGIME_CHANGE (ours)** — the 79.0% headline is a blend

**CITATION — measured.** `attributed_flag` share of obligations by fiscal year: 42.6–79.0%
in every year FY2000–FY2022, and **exactly 100.0% in FY2023, FY2024, FY2025 and FY2026.**
Those four years were built by identifier-seeded backfill, so **every row is attributed by
construction**. There is no unattributed comparison group in them.

**Consequences that must travel with the number:** an "attribution rate over time" chart is
meaningless past FY2022; a "share of Native contracting" denominator changes definition at
FY2023; and any model trained across the boundary learns our pipeline.

### E7 · `NAICS_REVISIONS` · **REGIME_CHANGE** — five-yearly definitional breaks

NAICS is revised in 2002 / 2007 / 2012 / 2017 / 2022: codes added, retired, split, merged.
An industry series crossing a revision year compares different definitions. Related, measured
elsewhere in this repo: **`713200`, the 4-digit group padded out, is filed 1,607 times against
439 filings of `713210`** — an exact-set filter on `713210` loses the majority of the gaming
rows. **Match NAICS by prefix, never by set membership.**

**For gambling specifically the news is good and is measured against the full Census
concordances: 713210 and 713290 are stable 1:1 across every revision 1997 → 2022.** The only
break is a *definitional* widening of 713210 in 2022 that the crosswalk does not record — see
§I2b, which carries the detail and the control code to use.

---

## F. SUBAWARDS — `subawards.csv` (~~63,548~~ **72,837** rows)

> *Row count re-measured 2026-09-01 (workstream H): the file grew to 72,837
> after the FY2021 API pull. **The per-year and per-threshold measurements
> below are 2026-08-26 and were NOT re-derived** — they describe the reporting
> regime, which has not changed, not the file size. Two things that HAVE
> changed and bear on this section: the file carries **10,770 literal duplicate
> rows** (14.8%), and `(subaward_number, subaward_date)` collides 27,470
> times — so the `duplicate_status = 'primary'` filter this section relies on
> is necessary but is **not sufficient** to make the file uniquely keyed. See
> `docs/KNOWN_ISSUES.md` §C2.*

### F1 · `FFATA_SUBAWARD` · **STRUCTURAL + THRESHOLD** — subcontracting cannot reach 2000

**CITATION — measured, 2026-08-26.** Rows by fiscal year:

| FY | rows | $M |
|---|---:|---:|
| 2001–2008 | 18 total | $1.8M |
| 2009 | 33 | $16.5M |
| **2010** | **141** | $345.8M |
| **2011** | **1,953** | $2,406.0M |
| 2012 | 3,106 | $1,247.0M |
| 2013 | 3,669 | $2,430.8M |

**The 51 rows dated before FY2010 are exactly the 51 rows carrying
`action_date_precedes_ffata_flag = yes`.** The flag and the count agree perfectly — our own
guard already identifies every impossible-under-FFATA row. **FY2012 forward is the first
comparable stretch.** The 2009→2011 rise of 59× is the reporting system switching on.

**CITATION — measured, the dollar floor.** Amounts against the reporting threshold:

| band | rows | share |
|---|---:|---:|
| below $25,000 | 9,557 | 15.0% |
| $25,000–$29,999 | 2,542 | 4.0% |
| $30,000 and above | 51,449 | 81.0% |

**19.0% of our subaward rows sit below the $30,000 threshold in force for most of the panel.**
That is a floor working loosely, not tightly — the *absent* population below the floor is
larger than a clean threshold would imply.

### F1b · The rules, retrieved — and FIVE assumptions in circulation did not survive

**CITATION — the statutory authority for subawards is 2006, not 2008.** Subaward reporting
comes from **FFATA §2(d)(2)** (Pub. L. 109-282, 2006):
> `(2) Reporting of subawards.--(A) In general.--Based on the pilot program conducted under paragraph (1) … not later than January 1, 2009, the Director of the Office of Management and Budget-- (i) shall ensure that data regarding subawards are disclosed in the same manner as data regarding other Federal awards…`

**Pub. L. 110-252 §6202 (2008) added EXECUTIVE COMPENSATION ONLY, not subawards.** Verbatim,
it inserts `(F) the names and total compensation of the five most highly compensated officers`
into FFATA §2(b)(1). **Cite §2(d)(2) for subawards; citing §6202 is wrong.**

**CITATION — grants.** OMB interim final guidance, **75 FR 55663 (2010-09-14)**, RIN 0348-AB61:
> `DATES: The effective date for this interim final guidance is September 14, 2010.`
> `…an award term that each agency must include in grant and cooperative agreement awards it makes on or after October 1, 2010…`
> 2 CFR 170.220(a): `…each award to a non-Federal entity under which the total funding will include $25,000 or more in Federal funding at any time during the project or program period.`

And the no-back-fill rule, verbatim from OMB's comment response:
> `They do not include obligating actions on or after October 1, 2010, that provide additional funding under continuing grants and cooperative agreements awarded in prior fiscal years.`

**CITATION — contracts, and the phase-in is NOT what our notes assumed.** FAC 2005-44,
FAR Case 2008-039, **75 FR 39414 (2010-07-08)**, FAR 52.204-10(e) as promulgated:
> `(1) Until September 30, 2010, any newly awarded subcontract must be reported if the prime contract award amount was $20,000,000 or more.`
> `(2) From October 1, 2010, until February 28, 2011, any newly awarded subcontract must be reported if the prime contract award amount was $550,000 or more.`
> `(3) Starting March 1, 2011, any newly awarded subcontract must be reported if the prime contract award amount was $25,000 or more.`

**THIS EXPLAINS OUR OWN NUMBERS EXACTLY.** FY2010 holds 141 rows (the ≥$20M and ≥$550,000
stages only); **FY2011 holds 1,953 — a 13.9× jump — because the ≥$25,000 stage opened on
2011-03-01, five months into FY2011.** The jump is the third phase-in stage, to the day.

**CITATION — the threshold moved, twice, and the two families are OUT OF SYNC:**

| date | contracts (FAR 4.1401 / 52.204-10) | grants (2 CFR 170.220) |
|---|---|---|
| 2010 | $25,000 | $25,000 |
| **2015-10-01** (FAC 2005-83, 80 FR 38293) | **$30,000** | $25,000 |
| **2020-11-12** (85 FR 49506) | $30,000 | **$30,000** |
| **2025-10-01** (FAC 2025-06, 90 FR 41872) | **$40,000** | $30,000 |

> `• The threshold for reporting first-tier subcontract information including executive compensation increases from $30,000 to $40,000 (FAR 4.1401).` — 90 FR 41872

**Pooling grant and contract subawards across 2015-10-01 → 2020-11-12, or after 2025-10-01,
mixes two different censoring rules.** And since 2020-06-05 the clause floats: reporting is
required for a subcontract `valued at or above the threshold specified in FAR 4.1403(a) on the
date of subcontract award` — **so one prime contract can straddle two thresholds.**

**THREE FURTHER RULE-BASED ABSENCES, each verbatim:**
1. **ARRA-funded subawards are excluded outright.** 2 CFR 170 App. A, I.a.1: `you must report each action that obligates $25,000 or more in Federal funds that does not include Recovery funds (as defined in section 1512(a)(2) of the American Recovery and Reinvestment Act of 2009, Pub. L. 111-5)`.
2. **Small recipients are exempt entirely.** Current 2 CFR 170 App. A(d)(1): `A recipient with gross income under $300,000 in the previous tax year is exempt from the requirements to report: (i) Subawards…`
3. **A SECOND-TIER SUBAWARD NEVER EXISTS.** 75 FR 55663: `The Transparency Act does not authorize a limitation on the reporting requirement to the first-tier of subawards. At this time, however, we are deferring to a later date the implementation of the reporting requirement below the first-tier.` **No later implementation was found.** FAR 4.1401(b): `Reporting of subcontract information will be limited to the first-tier subcontractor.` 2 CFR 25.105(b): `This part does not apply to subrecipients of subrecipients (second-tier subrecipients) or contractors under Federal awards.`

**AND A FOURTH ABSENCE THAT IS NOT ABOUT SUBAWARDS AT ALL.** FFATA §2(a)(2) puts a *statutory*
floor under the whole USAspending universe, separate from FPDS:
> `(B) does not include individual transactions below $25,000; and (C) before October 1, 2008, does not include credit card transactions.`
**FPDS and USAspending have different bottom censoring.** Do not assume a transaction present
in one is present in the other.

### F2 · `SUBAWARD_DUPLICATE_STATUS` **NEW** · **A FORBIDDEN SUM**

**CITATION — measured.** `subaward_amount` by `duplicate_status`:

| status | rows | $B |
|---|---:|---:|
| `primary` | 48,065 | **$25.77B** |
| `exact_repeat_within_source` | 14,637 | $13.14B |
| `superseded_by_primary_source` | 846 | $0.53B |
| **naive total** | 63,548 | **$39.43B** |

**Summing past this column inflates subaward dollars by 53%.** The true figure is **$25.77B**.

### F3 · `SUBAWARD_FY2021_24_OUTAGE` · **OURS, AND UPSTREAM**

FY2021–24 hold **173 / 89 / 120 / 166** rows against 8,589 in FY2018 and 9,373 in FY2019.
`data/raw/subcontracts/usaspending_2026-08-12/_state.json` records fy2021/22/23/24 each
`status: failed`, `total_rows: 0` — a service-wide bulk_download outage, proven by a
prime-award control and an FY2015 replay. **This is not a Cedar gap and it is not a finding
about subcontracting.** Any 2021–24 subaward figure is a floor of a floor.

### F4 · Linkage, stated correctly

`prime_native_tribe_id` is populated on 26,430 rows (41.6%) and `sub_native_tribe_id` on
38,336, but **either is populated on 63,504 of 63,548 — 99.9%.** Quoting 41.6% alone
understates the dataset badly.

---

## G. NONPROFITS AND 990 SCHEDULE I — `np_orgs.csv` (12,764), `np_schedule_i_grants.csv` (58,685)

### G1 · `SECTION_7871` · **STRUCTURAL** — 6,217 recipient EINs absent from the BMF, carrying $4.96B

**CITATION — measured, 2026-08-26**, `np_schedule_i_grants.csv` against the full IRS EO BMF
(1,957,340 organisations, fetched 2026-08-12):

| recipient BMF status | rows | distinct EINs | $ |
|---|---:|---:|---:|
| `in_full_irs_bmf` | 39,178 | 12,491 | $11.636B |
| **`absent_from_full_irs_bmf`** | **16,344** | **6,217** | **$4.958B** |
| `no_ein_reported_on_schedule` | 3,163 | — | $0.724B |

*(The $4.92B in circulation is the cash-grant-only figure; $4.958B is cash + non-cash. Say
which.)*

**These EINs are printed on a filed Form 990 Schedule I — a return under penalty of perjury,
naming a real recipient and a real dollar amount — and they are absent from the entire
Exempt Organizations Business Master File. That is not a gap in our data and it is not queued
as one.** It reproduces independently in `docs/PHILANTHROPY_DISCOVERY_LOG.md` and
`docs/GRANTEE_990_LOG.md`, which reached the same conclusion from 153 of 601 grantee EINs.
Three builds, one finding. A further **1,069 rows have the filer writing `TRIBE` in the IRC
section**, naming the case in its own words.

**AND THE TEST WAS WRONG BEFORE THE FULL BMF WAS FETCHED.** The first cut tested recipient
EINs against the **12,764-row Native-connected slice** and labelled **17,848 ordinary
charities** with the 7871 signature. Testing against a subset answers *"is this recipient in
our Native subset"* and cannot answer *"does this EIN file a Form 990 at all."* **Any
re-derivation of this finding must use the full BMF.**

### G1b · The legal mechanism, retrieved — and THREE ways to state it wrong

**This is load-bearing for the planned editorial piece. Every sentence below is the retrieved
text, and three natural-sounding paraphrases are legally wrong.**

**STEP 1 — §7871 makes a tribe a State for charitable-deduction purposes.** 26 U.S.C. 7871(a),
added by Pub. L. 97-473 §202(a), 1983-01-14:
> `(a) General rule — An Indian tribal government shall be treated as a State— (1) for purposes of determining whether and in what amount any contribution or transfer to or for the use of such government (or a political subdivision thereof) is deductible under— (A) section 170 (relating to income tax deduction for charitable, etc., contributions and gifts) …`

**⚠ WRONG WAY #1: "§7871 treats a tribe as a State for purposes of §170(c)(1)."** §7871
contains **no cross-reference to §170(c)(1)**. It points at **§170 as a whole**. The
§170(c)(1) result is produced by *operation* — §7871 says "treated as a State," and §170(c)(1)
independently makes a gift to "a State … or any political subdivision" a charitable
contribution:
> `(c) Charitable contribution defined … (1) A State, a possession of the United States, or any political subdivision of any of the foregoing, or the United States or the District of Columbia, but only if the contribution or gift is made for exclusively public purposes.`
**Write it as the two steps.** §7871(d) separately provides that a subdivision is treated as a
political subdivision `if (and only if) the Secretary determines (after consultation with the
Secretary of the Interior) that such subdivision has been delegated the right to exercise one
or more of the substantial governmental functions of the Indian tribal government.`

**STEP 2 — a tribe is not a taxable entity at all.** Rev. Rul. 67-284, 1967-2 C.B. 55
(https://www.irs.gov/pub/irs-tege/rr67_284.pdf):
> `Income tax statutes do not tax Indian tribes. The tribe is not a taxable entity.`
IRS Publication 3908 (Rev. 9-2019): `Even though Indian tribes are not subject to federal
income tax…`

**STEP 3 — and this is why there is no Form 990.** The filing duty is textually keyed to
§501(a). Treas. Reg. 26 CFR 1.6033-2(a)(1):
> `every organization exempt from taxation under section 501(a) shall file an annual information return…`

**⚠ WRONG WAY #2: "tribal governments are exempt from filing Form 990."** **No IRS document
says that, and the statement is legally wrong.** A tribe is not an *exception* to the Form 990
regime — it is **outside** it. The duty runs to organisations exempt under §501(a); a tribal
government is not such an organisation, because it is not taxable in the first place. **The
correct sentence is stronger than an exception would be:** *the Form 990 filing duty attaches
only to organisations exempt under §501(a); a tribal government is not one.*

**STEP 4 — and a private foundation may still lawfully grant to it.** This is the piece most
likely to be got wrong, and the answer is one regulation: 26 CFR 53.4945-5(a)(4):
> `(4) Certain "public" organizations. For purposes of this section, an organization will be treated as a section 509(a)(1) organization if: … (ii) It is an organization described in section 170(c)(1) or 511(a)(2)(B), even if it is not described in section 501(c)(3) … However, any grant to an organization referred to in this subparagraph must be made exclusively for charitable purposes as described in section 170(c)(2)(B).`

**A §170(c)(1) governmental unit is DEEMED a §509(a)(1) public charity "even if it is not
described in section 501(c)(3)" — so no expenditure responsibility is required** under 26
U.S.C. 4945(d)(4). §7871(a)(7)(B) separately treats a tribe as a State for purposes of
`subchapter A of chapter 42 (relating to private foundations)`.

**⚠ WRONG WAY #3: "§4942 counts the grant because the tribe is a §170(c)(1) donee."**
26 U.S.C. 4942(g)(1)(A) defines a qualifying distribution as `any amount … paid to accomplish
one or more purposes described in section 170(c)(2)(B)`. **That is a PURPOSE test, not a
donee-status test.** The donee-status work is done by 53.4945-5(a)(4)(ii), above.

**THE PUBLISHABLE SENTENCE:** *A foundation grants to a tribe on the same Schedule I footing as
a grant to a public charity, and its own return shows nothing unusual. The absence is entirely
on the recipient side. Our $4.96B is not evidence of irregular grantmaking; it is evidence that
Schedule I records payments to a class of donee the Business Master File was never built to
contain.*

**AND ONE MORE CORRECTION.** **Rev. Proc. 2008-55 is not a list.** It is the rule that
*replaced* the IRS's own roster: after 2008-09-29 the IRS designates as tribal governments
`the Indian tribal entities that appear on the current or future lists of federally recognized
Indian tribes published annually by the Department of the Interior, Bureau of Indian Affairs
… for purposes of section 7701(a)(40).` **There is no IRS-maintained enumeration to join
against — the joinable roster is the BIA Federal Register list.** It is also about §7701(a)(40)
*tribal-government* status, **not** about political subdivisions; for those, use §7871(d).
*(Rev. Proc. 84-36 could not be retrieved — pre-1996 Bulletins are not posted. **Do not assert
a Rev. Proc. 84-36 political-subdivision list.**)*

### G1c · ⚠ THE 6,217 MUST NOT BE ATTRIBUTED WHOLLY TO TRIBAL STATUS

There is a **second, independent** reason a Schedule I recipient EIN can be absent from the
BMF: **automatic revocation** (§G6). On **2011-06-08** roughly **275,000 organisations** left
the exempt-organization population in one administrative act, and are `removed from the
cumulative list of tax-exempt organizations`. **The 6,217 figure is an upper bound on the
§7871 population until auto-revoked EINs are separated out.** That separation has not been
done. Say "absent from the BMF," which is measured, rather than "tribal governments," which is
inferred, until it is.

### G2 · `FORM_990N` · **REPORTED_EMPTY** — half our nonprofit universe reports no financial detail

**CITATION — measured, 2026-08-26.** BMF filing-requirement code across all 12,764 orgs
(every one of which is in the BMF snapshot):

| `bmf_filing_req_cd` | orgs | share |
|---|---:|---:|
| `02` — not required to file (income below threshold) | **6,453** | **50.6%** |
| `01` — Form 990 required | 4,247 | 33.3% |
| `06` — not required (church) | 1,491 | 11.7% |
| `00` — no filing requirement | 468 | 3.7% |
| `13`/`14`/`07`/`03` | 105 | 0.8% |

**8,505 of 12,764 organisations (66.6%) file no Form 990 financial detail at all.** A zero in
a revenue column for any of them **is the filing regime, not a finding about the
organisation.**

**CITATION — statute.** Pension Protection Act of 2006, Pub. L. 109-280 §1223, approved
**2006-08-17**, adding IRC §6033(i). §1223(f): `The amendments made by this section shall apply
to notices and returns with respect to annual periods beginning after 2006.`

**CITATION — the threshold move.** Rev. Proc. 2011-15, 2011-3 I.R.B. 322, published
2011-01-17, `applicable to annual returns filed for tax years beginning on or after January 1,
2010`:
> `…whose annual gross receipts are normally not more than $50,000. This is an increase from the previous filing threshold of annual gross receipts that are normally not more than $25,000.`
The prior $25,000 figure came from Rev. Proc. 83-23. Now codified at 26 CFR
1.6033-2(g)(1)(iii).

**CITATION — what the e-Postcard actually collects, verbatim from irs.gov.** `You'll need only
eight items of basic information about your organization`: EIN · tax year · legal name and
mailing address · other names used · name and address of a principal officer · website ·
**`Confirmation that the organization's annual gross receipts are $50,000 or less`** · a
termination statement if applicable.

**STATE IT PLAINLY, AND IT IS AIRTIGHT: a Form 990-N filing contains no revenue figure, no
expense figure, no asset figure, no compensation, no grants made, no grants received and no
programme description. Its only financial content is a yes/no attestation that gross receipts
are ≤ $50,000.** There is nothing to extract because nothing is collected.

For our **6,453** 990-N filers we therefore have an upper bound of $50,000 on gross receipts
and literally nothing else. **Any financial aggregate we compute is computed over the other
6,311 organisations only. A 990-N filer is not a missing or non-compliant record — it is a
fully compliant record of a form that carries no financial detail. Do not impute; do not treat
990-N as zero.**

### G3 · `TFA_EFILE` **NEW** · **REGIME_CHANGE** — paper filers 2011–2018 are absent entirely

**CITATION — measured.** Schedule I rows by tax year: 5 (2015) · 4,214 (2016) · 4,825 (2017)
· 5,284 (2018) · **4,257 (2019)** · 6,098 (2020) · 6,528 (2021) · 6,375 (2022) · 6,706 (2023)
· 9,779 (2024) · 4,614 (2025).

**Mandatory e-filing arrived with the Taxpayer First Act; paper filers 2011–2018 are absent
from the XML entirely.** An organisation with no return here **may simply have filed on
paper.** The **2019 dip to 4,257 is a coverage artefact of the cache, not a drop in
grantmaking.** And the **IRS e-file index begins at submission year 2017**, so tax years
before roughly 2015 have no machine-readable return at any URL. **Never read absence as "the
org did not file."**

### G4 · `SCHEDULE_I_5000_FLOOR` **NEW** · **THRESHOLD**

**Schedule I Part II has a $5,000 floor.** Grants below it are absent by design. Any
"smallest grant" or "number of grants" figure from this collection is bounded at $5,000.

### G5 · `SCHEDULE_I_PART_III` **NEW** · **STRUCTURAL** — $7.32B the form does not ask about

**Part III grants to individuals carry no recipient names — the form does not ask.** 1,372
returns report **$7,318,402,903** this way. It is unattributable **by construction**, and it
is counted here only to give the invisible channel a size. Also: **fiscally sponsored projects
file under the sponsor's EIN**, so the organisation named is not always the legal person paid.

### G6 · `IRC_6033J` **NEW** · **REGIME_CHANGE** — the BMF population itself changes on a date

**CITATION — statute.** IRC §6033(j)(B), added by PPA §1223(b):
> `If an organization described in subsection (a)(1) or (i) fails to file an annual return or notice required under either subsection for 3 consecutive years, such organization's status as an organization exempt from tax under section 501(a) shall be considered revoked … The Secretary shall publish and maintain a list of any organization the status of which is so revoked.`

**CITATION — the first list, dated exactly.** IRS **IR-2011-63, 2011-06-08**:
> `WASHINGTON — The Internal Revenue Service today announced that approximately 275,000 organizations under the law have automatically lost their tax-exempt status because they did not file legally required annual reports for three consecutive years.`
> `…it is because IRS records indicate the organization had a filing requirement and did not file the required returns or notices for 2007, 2008 and 2009.`
> `The IRS will update the list monthly…`
And: an automatically revoked organisation `will be removed from the cumulative list of
tax-exempt organizations, Publication 78.`

**THE BMF IS NOT A STABLE FRAME.** On one day in 2011 roughly 275,000 rows left the population,
and the list has been revised **monthly** ever since. **Any BMF-based denominator, join, or
present-vs-absent test is a snapshot with a date attached.** Our 1,957,340-row extract is dated
**2026-08-12** and that date must travel with every figure derived from it. Pre-2011 and
post-2011 BMF populations are not comparable.

---

## H. GAMING — `gaming_facilities.csv` (784 rows), `gaming_facility_metrics.csv`

### H1 · `GAMING_UNIVERSE_RECONCILIATION` · **OURS** — we undercount operating and overcount historical

**CITATION — measured, 2026-08-26.** `property_status`: **`current` 449** · `approved` 1 ·
**blank 334**. Distinct `tribe_id` among current facilities: **189**.

**CITATION — published federal figures**, from `docs/PUBLISHED_LANDSCAPE_2026-08-26.md`:

| source | facilities | tribes | as of |
|---|---:|---:|---|
| **CRS IF12527** (sourced to NIGC) | 532 | 243 | Sept 2024 |
| **NIGC via TBN/CDC Gaming** | 545 | 246 | FY2025 |
| **Cedar Press, `current`** | **449** | **189** | 2026-08-26 |
| Cedar Press, all rows | 784 | — | historical universe |

**Both directions are wrong and both must be stated in the same sentence.** 449 operating
against 532–545 licensed is an **undercount of operating facilities**; 784 against 545 is a
**historical universe including closed sites**, not broader current coverage. **An
unreconciled 784 reads as an error, not as coverage.** Name IF12527 as the baseline.

### H2 · `IGRA_ERA` · **REGIME_CHANGE** — pre-1988 gaming is a different legal object

**CITATION — measured.** 53 facilities carry an `open_date` before 1988. Opens by 5-year
bucket: 18 (1980–84) · 42 (1985–89) · **120 (1990–94)** · 102 (1995–99) · **131 (2000–04)** ·
105 (2005–09) · 66 (2010–14) · 42 (2015–19) · 3 (2020–24).

**The early-1990s peak is an institution being built, not a market expanding within a stable
one.** A facility "operating" in 1985 was doing something legally different from a facility
operating in 1995.

**CITATION — statute.** Indian Gaming Regulatory Act, Pub. L. 100-497, enacted
**1988-10-17**, 102 Stat. 2467. 25 U.S.C. 2703 defines the classes; **Class III is a residual
category defined by exclusion**:
> `(8) The term "class III gaming" means all forms of gaming that are not class I gaming or class II gaming.`
And Class II expressly excludes `(ii) electronic or electromechanical facsimiles of any game of
chance or slot machines of any kind.`

25 U.S.C. 2710(d)(1) — Class III is lawful **only if** it is `(A) authorized by an ordinance or
resolution` of the tribe and approved by the Chairman, `(B) located in a State that permits
such gaming for any purpose by any person, organization, or entity, and (C) conducted in
conformance with a Tribal-State compact … that is in effect.`

**Conditions (B) and (C) are STATE-level facts, not tribal attributes.** Class III presence is a
function of state law and of a bilaterally negotiated compact. **Any tribe-level model of
Class III presence carries an unavoidable state fixed effect.**

### H2b · `CLASS_II_III_LINE` **NEW** · **REGIME_CHANGE** — the same machine can change class without moving

Because Class III is residual, the entire boundary rests on the "technologic aid" vs
"facsimile" line — and **that line was redrawn twice inside our window.**

**CITATION — regulation.** 25 CFR Part 502 (source: `57 FR 12392, Apr. 9, 1992`). The
definitions at **§502.7** (electronic, computer or other technologic aid) and **§502.8**
(electronic or electromechanical facsimile) both carry the source note **`[67 FR 41172, June
17, 2002]`**. *(Correction: the facsimile definition is at §502.8. §502.13 is "Indian tribe.")*

> `§502.8 … a game played in an electronic or electromechanical format that replicates a game of chance by incorporating all of the characteristics of the game, except when, for bingo, lotto, and other games similar to bingo, the electronic or electromechanical format broadens participation by allowing multiple players to play with or against each other rather than with or against a machine.`

| rule | FR citation | published | effective |
|---|---|---|---|
| Definitions: technologic aid / facsimile / game similar to bingo | **67 FR 41166** | 2002-06-17 | **2002-07-17** |
| Class II technical standards (25 CFR Part 547) | **73 FR 60508** | 2008-10-10 | **2008-11-10** |

**Class II / Class III splits are NOT comparable across 2002-07-17 or 2008-11-10.** Treat a
pre-2002 classification as a different variable.

**CITATION — *California v. Cabazon Band*.** The citation **480 U.S. 202 (1987)** is confirmed
from federalregister.gov full text (26 documents cite it; 134 name the Band). **The decision
DAY could not be verified from any permitted host** — govinfo's SCOTUS resolver returns 500 and
supremecourt.gov was out of scope. **Write "decided in 1987"; do not print a day.**

### H3 · `CT_UNIT_CHANGE` · **REGIME_CHANGE (ours)** — a column that changes units without changing its name

**The Connecticut gaming source changes UNITS mid-series without changing the column name**
— `payout` reads 91.45 in 1993-01 and 0.912 in 2025-12. `gaming_facility_metrics.csv` does
not carry `payout`; **confirm before any raw CT read.** The concurrent anomaly sweep cannot
see this seam because it does not fall on a year boundary — **absence from that report is not
evidence the seam is gone.**

### H4 · `NIGC_CONFIDENTIALITY` **NEW** · **SUPPRESSION** — the number exists, is federally held, and Congress made it confidential in 1988

**This is the most important reclassification in the gaming section: per-facility revenue is
not a data-collection gap. It is a statutory disclosure bar.**

**CITATION — the audit requirement.** 25 U.S.C. 2710(b)(2)(C): the Chairman shall approve a
tribal gaming ordinance if it provides that
> `annual outside audits of the gaming, which may be encompassed within existing independent tribal audit systems, will be provided by the Indian tribe to the Commission;`
and (b)(2)(D) subjects every contract over $25,000 annually (except legal and accounting) to
those audits. **This reaches Class III by incorporation** — §2710(d)(1)(A)(ii) requires the
Class III ordinance to meet `the requirements of subsection (b)`. *(Correction: §2710(d)(9) is
about **management contracts**, not audits. Cite (b)(2)(C) with (d)(1)(A)(ii).)*

**CITATION — the confidentiality bar.** 25 U.S.C. **2716(a)**, "Investigative powers,"
Pub. L. 100-497 §17:
> `Except as provided in subsection (b), the Commission shall preserve any and all information received pursuant to this chapter as confidential pursuant to the provisions of paragraphs (4) and (7) of section 552(b) of title 5.`

Note the construction precisely: §2716(a) does not create a freestanding secrecy rule; it
directs the Commission to withhold **under FOIA Exemptions 4 and 7**. The bar is FOIA's,
invoked by statute.

**SO: every Class II and Class III operation files an annual independently audited financial
statement with the Commission. Per-facility revenue EXISTS and is federally held — and is
withheld.** Two consequences travel with the number: only aggregates are publishable
(NIGC FY2025 **$46.2B**, `docs/PUBLISHED_LANDSCAPE_2026-08-26.md` treats aggregate revenue as
occupied and unclaimable), and **because the audits are annual, no sub-annual per-facility
series can exist from this source at all.**

*(For the accounting concept the audits report on, 25 CFR 502.16 defines `net revenues` as
gross gaming revenues less prizes and total gaming-related operating expenses excluding
management fees — `[74 FR 36932, July 27, 2009]`.)*

### H5 · Licensing, which is a limitation on what we may publish

**Casino City may be read for QA and never published.** The vendor share of the property
universe is **610 of 774**. **D&B Open Data** (legal name, street, city, state, ZIP) may not
be disseminated in bulk and attaches to every base award dated before **2022-04-04** — 100%
of the SAM FY2000–2007 backfill.

---

## I. EMPLOYMENT AND LABOUR — forward-looking; the layer is Form 5500 + OSHA ITA today

*Cedar currently holds `gaming_employment_observations.csv` (3,300 rows) built from **Form
5500** and **OSHA ITA**, not from Census or BLS. The suppression entries below gate a planned
layer and are recorded now so nobody builds on a zero. Full treatment:
`docs/LABOR_SOURCES_FOR_GAMING_2026-08-26.md` §3 and §15.*

### I0 · `TRIBAL_UI_COVERAGE_2000` **NEW** · **REGIME_CHANGE** — a structural break under EVERY UI-derived series

**QCEW, QWI and LODES all inherit their frame from state unemployment-insurance records.
Before 2000-12-21, tribal employers were outside the FUTA definition of "employment."**

**CITATION — statute.** Community Renewal Tax Relief Act of 2000 **§166**, enacted as part of
Pub. L. 106-554, **2000-12-21**, 114 Stat. 2763A-627.
https://www.govinfo.gov/content/pkg/PLAW-106publ554/html/PLAW-106publ554.htm
> `(a) In General.—Section 3306(c)(7) (defining employment) is amended— (1) by inserting "or in the employ of an Indian tribe," after "service performed in the employ of a State, or any political subdivision thereof,"…`
> `(u) Indian Tribe.—For purposes of this chapter, the term "Indian tribe" has the meaning given to such term by section 4(e) of the Indian Self-Determination and Education Assistance Act (25 U.S.C. 450b(e)), and includes any subdivision, subsidiary, or business enterprise wholly owned by such an Indian tribe.`
> `(e) Effective Date … (1) … The amendments made by this section shall apply to service performed on or after the date of the enactment of this Act.`

**Wholly-owned tribal business enterprises — expressly including gaming enterprises — enter
the UI frame on 2000-12-21.** Tribes elect contributory or reimbursable status per §3309(d),
separately for each subsidiary.

**TRIBAL CASINO JOBS APPEARING "NEW" IN 2001 QCEW ARE A COVERAGE CHANGE, NOT EMPLOYMENT
GROWTH.** LODES and QWI begin in 2002, entirely after the break — but **the QCEW back-series
does not**, and QCEW reaches 1990.

### I1 · `QCEW_SUPPRESSION` · **SUPPRESSION** — the worst failure mode in the product

**A SUPPRESSED QCEW CELL IS ZERO-FILLED, WITH A REAL ESTABLISHMENT COUNT BESIDE IT.** It looks
exactly like a real zero and nothing about the output is broken.

**CITATION — BLS, verbatim** (https://www.bls.gov/cew/questions-and-answers.htm):
> `Suppressed data fields are published with an "N" in the disclosure code field. Only establishment counts are disclosed for these cells, based on approval from this Federal Register Notice, while all other data items for the cell are suppressed (zero-filled).`
> `Most of the suppressed data are provided by or are substantially attributable to a single large employer.`
> `Even the county by industry data cited above is at the margin of being disclosable - approximately 60 percent of the most detailed level data are suppressed for confidentiality reasons.`

BLS Handbook of Methods, QCEW: Calculation (last modified 2026-01-13):
> `BLS withholds the publication of UI-covered employment and wage data for any industry level when necessary to protect the identity of employers. Totals at the industry level for the states and the nation include the undisclosed data suppressed within the detailed tables without revealing those data.`

**Vintage matters:** 2001–2003 files zero-fill **all** items including establishment counts;
1990–2000 NAICS files mostly **omit** suppressed cells entirely (they were reconstructed from
SIC-era data). And a dash `-` means the cell does not exist that quarter, which is a **third**
state distinct from both suppression and zero.

**GAMBLING IS EXACTLY THE "ONE LARGE EMPLOYER" CASE, so 7132 suppression is near-universal by
construction — and the establishment count is the one usable signal.** If the pipeline reads
the numeric employment column without reading the disclosure column, **every suppressed casino
county silently becomes a true zero.**

**UNVERIFIED: BLS publishes no numeric primary-suppression criterion** — no n-rule, no
p-percent parameter — anywhere reachable. The only cited methodological authority is FCSM
Statistical Policy Working Paper 22. **Do not state a specific QCEW cell threshold.**
*(Retrieval note: bls.gov returns HTTP 403 to plain requests, including to `/robots.txt`.)*

### I1b · `QCEW_NO_TRIBAL_OWNERSHIP_CODE` **NEW** · **STRUCTURAL**

**QCEW's ownership codes are 0 Total Covered · 1 Federal · 2 State · 3 Local · 4 International
· 5 Private · 8 Total Government · 9 Total UI Covered. There is no tribal category.**
(https://www.bls.gov/cew/classifications/ownerships/ownership-titles.htm)

**Tribal casino employment is not separately identifiable in QCEW under any ownership code**,
and a search of the QCEW ownership page, Q&A and Handbook chapters for "tribal", "tribe" and
"Indian" returns **zero substantive matches**. **UNVERIFIED: whether tribal establishments are
coded 5 (Private) or 3 (Local Government), and whether that treatment ever changed. Any claim
that a QCEW ownership split isolates tribal gaming is unsupported.**

### I2 · `LODES_QWI_SUPPRESSION` · **SUPPRESSION** — and LODES cannot answer the question at all

**⚠ FIRST, A CORRECTION THAT CHANGES WHAT IS EVEN POSSIBLE: LODES has no NAICS 7132. Ever. At
any geography.** LODES RAC/WAC files carry industry only as the 20 two-digit sectors
`CNS01`–`CNS20` — gambling sits inside `CNS17 | Num | Number of jobs in NAICS sector 71 (Arts,
Entertainment, and Recreation)`. **Any 7132 county-year series must come from QWI (4-digit) or
QCEW (6-digit), and those two use different suppression regimes.** (LODES Technical
Documentation Format Version **8.4**, Rev. 20251203.)

**LODES IS MODEL OUTPUT, NOT A COUNT.** Census, *OnTheMap: Data Overview (LODES Version 8)*,
OTM20251202:
> `As with previous versions of data released in OnTheMap, LODES Version 8 is a partially synthetic dataset…`
**A LODES zero is a draw from a synthetic model.** *(And note for fact-checking: the LODES
Technical Documentation itself contains **no** description of the disclosure method — only the
CBDRB-FY21-249 clearance footnote. Cite the OnTheMap Data Overview and LEHD TP-2006-01 instead;
"the LODES tech doc says" will not survive a check.)*

**LODES STATE COVERAGE IS RAGGED AND THE RAGGEDNESS MOVES BETWEEN VERSIONS.** States without
OD/WAC data: Alaska 2017–2023 · Arizona 2002–03 · Arkansas 2002 · DC 2002–09 · Massachusetts
2002–10 · Michigan 2022–23 · Mississippi 2002–03 · New Hampshire 2002 · Puerto Rico and USVI
all years. **And Mississippi's 2019–2021 status CHANGED between LODES 8.3 and 8.4** — 8.3
(Rev. 20241105) listed Mississippi as missing 2019–2022; 8.4 restores it. **A panel built
before December 2025 and one built after are not the same panel. Pin the tech-doc version in
the methods note.**

**QWI HAS FOUR KINDS OF ABSENCE AND ONE OF THEM IS A PUBLISHED WRONG NUMBER.** Status flags
(LEHD Public Use Data Schema V4.14.0 §6.1; QWI 101):
> `-2,no data available in this category for this quarter` · `-1,data not available to compute this estimate` · `1,OK` · `5,Value suppressed because it does not meet US Census Bureau publication standards.` · `9,Data significantly distorted - fuzzed value released` · `11,Aggregate of cells not released because component cells do not meet U.S. Census Bureau publication standards`

**Flag 9 is a published number you must not treat as measured.** Reading any of −2, −1, 5 or 9
as "zero gambling employment" is a category error.

**AND THE QWI NOISE DOES NOT CANCEL IN A ONE-CASINO COUNTY.** LEHD TP-2006-01 (2005-12-05):
> `for a given workplace, the data are always distorted in the same direction (increased or decreased) by the same percentage amount in every period, and in every revision of the QWI series … when the estimates are aggregated, the effects of the distortion cancel out for the vast majority of the estimates`
> `some of the aggregate estimates turn out to be based on fewer than three persons or establishments. These estimates are suppressed…`
> `a fuzz factor is attached to each SEIN and SEINUNIT only once and retained for all time periods after the initial assignment.`

**Cancellation is an aggregation property.** In a county with one or two casinos the cell is
either suppressed (n<3) or **released with a single establishment's permanent fuzz factor
passing straight through to the county total** — biased the same direction in every quarter.
**It is a fixed effect, not white noise.** *(The distortion parameters are defined only
symbolically in TP-2006-01. **UNVERIFIED — never quote a percentage.**)*

**AND SUPPRESSION IS CORRELATED WITH THE POPULATION OF INTEREST.** AIAN cells in small counties
are the ones that suppress, which is exactly where reservations are. **A complete-looking AIAN
series is a selected one.**

### I2b · `NAICS_7132_STABLE_BUT_WIDENED` **NEW** · **REGIME_CHANGE (small, and easy to miss)**

**Good news, measured against the full Census concordances: the 6-digit gambling codes are
stable 1997 → 2022.** 713210 and 713290 each map 1:1 to themselves across 1997→2002,
2002→2007, 2007→2012, 2012→2017 and 2017→2022. **There is no code-level revision break.**

**But NAICS 2022 widened the 713210 DEFINITION and left no footprint in the crosswalk.** The
2022 description adds `and casinos with racetracks` to 713210 (2017 read only `floating casinos
(i.e., gambling cruises, riverboat casinos)`) and adds `or card-` to 713290 — while the
concordance records **no** split from 711212 Racetracks. **Racino establishments may reclassify
from 711212 into 713210 at the 2022 vintage change with nothing in the crosswalk telling you.**
Treat 2022-vintage 713210 as not strictly comparable to earlier vintages, **and carry 711212
alongside 7132 as a control.**

Also, the subsector's own coverage warning, verbatim: `The Gambling Industries industry group
does not provide for full coverage of gambling activities. For example, casino hotels are
classified in Subsector 721, Accommodation; and horse and dog racing tracks without casinos are
classified in Industry Group 7112, Spectator Sports.` **A 7132-only filter omits casino hotels
by definition.**

### I3 · `OSHA_ITA_ABSENCE` · **THRESHOLD + REPORTED_EMPTY**

**Electronic submission is required only of establishments above size thresholds in covered
industries, and compliance is uneven.** Therefore:
- **AN ESTABLISHMENT ABSENT FROM ITA IS NOT AN ESTABLISHMENT WITH ZERO INJURIES, AND NOT ONE
  WITH ZERO EMPLOYEES.** It is an establishment that did not file.
- **The set of establishments filing under one tribe changes year to year.** A tribe-year SUM
  is **not a consistent panel** and must never be differenced as one. Every row carries
  `DO_NOT_SUM_ACROSS_YEARS_WITHOUT_A_BALANCED_PANEL`.
- It is **self-reported** — the employer files its own 300A.
- Screen `hours_per_employee` before use: 6 of 327 rows sit outside 200–5,000 (a "Choctaw
  Casino Amenity Refresh" reports 19 employees and 117,335 hours).

### I4 · `FORM_5500_SCOPE` · **STRUCTURAL**

**A Form 5500 row keys to an EIN, never to a facility**, and **plan participants are not
employees.** `TOT_ACTIVE_PARTCP_CNT` *brackets* employment and the bracket is conditional in
two directions at once. **A tribe with no qualifying plan has no filing, and that is not a
data gap.** 147 of Cedar's 275 facility tribes have no gaming-NAICS 5500 filing; 13 tribes
file one and have no Cedar gaming facility (a review queue, not a merge).

Also: **any consumer that sums `OSHA_ESTABLISHMENT_REPORTED` and `OSHA_TRIBE_LEVEL_REPORTED`
without filtering on `already_facility_attached` double-counts 317 filings.**

*(The Census/BLS disclosure texts, the QCEW `N` code and the 2000 FUTA/UI change are cited in
full at §I0–§I2b above. What remains unverified — the QCEW numeric suppression criterion and
the ownership code tribal employers land in — is in PART V.)*

---
---

# PART III — OUR OWN LIMITATIONS, PLAINLY

*Everything above is somebody else's rule. This is ours.*

## J1 · THE ABSENCE VOCABULARY — every collection must use it

**A blank must never read as our failure when it is the source's silence.** Cedar Press
already carries a **SOURCE-level** four-state vocabulary
(`docs/EDITORIAL_PIPELINE.md`): `PUBLISHES` / `WITHHOLDS` / `NOT_FOUND` / `NOT_CHECKED`, which
answers *"does this source publish this thing?"*

**This section adds the ENTITY-level vocabulary, which answers a different question: "why is
THIS entity absent from THIS source?"** The two are complementary and both travel.

| value | means | worked example |
|---|---|---|
| **`NOT_IN_SOURCE`** | we queried the source and the entity is genuinely absent from it | An establishment we searched for in OSHA ITA CY2016–CY2025 and did not find. **This is the value that protects us** and it must be distinguishable at a glance from every other blank |
| **`BELOW_REPORTING_THRESHOLD`** | the source only covers above a floor and this entity is below it — absent **BY RULE**, not by failure | A tribal entity expending under $1,000,000 in federal awards has **no Single Audit**, so it has no FAC record (2 CFR 200.501(a)). A subaward under $30,000. A Schedule I grant under $5,000. A contract under the micro-purchase threshold |
| **`OUT_OF_SCOPE_BY_CONSTRUCTION`** | the source structurally cannot contain this entity — it was never eligible | **A tribal government is not a 501(c)(3) and files no Form 990, so it is not missing from the BMF; it was never eligible for it.** **FAADS has no DUNS field and no EIN field in its 624-byte layout, so a pre-FY2007 assistance row cannot carry an identifier.** A DC lobbying LLP likewise files no 990 |
| **`SUPPRESSED`** | the source holds it and withholds it | A tribal Single Audit reporting package where the tribe excluded the 2 CFR 200.512(b)(2)(iv) authorisation — **4,728 of our 6,780 records.** A QCEW NAICS 7132 county-year. A LODES or QWI small cell. Per-facility NIGC gross gaming revenue |
| **`REPORTED_EMPTY`** | the source affirmatively reports nothing — the filing exists and says zero | **6,453 of 12,764 organisations are 990-N filers reporting no financial detail.** **5,308 LDA filings (19.1%) are mandatory no-activity reports** — a live registration affirming zero lobbying that quarter |
| **`NOT_CHECKED`** | we did not look. Honest, and required — **a guess is not** | Any source in the queue we have not swept. Word deliberately identical to the existing source-level term |

**THE TWO ERRORS THIS PREVENTS, EACH PAID FOR ONCE:**
- **`NOT_FOUND` read as `OUT_OF_SCOPE_BY_CONSTRUCTION`** — a first pass tested Schedule I
  recipient EINs against a 12,764-row Native slice instead of the full 1,957,340-row BMF and
  labelled **17,848 ordinary charities** with the IRC 7871 signature.
- **`SUPPRESSED` read as zero** — a suppressed QCEW cell is published as `0`. That is a
  number, and it is not a measurement.

**Corroborating measurements from a concurrent agent** (recorded here, not re-derived):
**6 of 653 lobbying registrants appear in the full BMF (0.8%)**, and **28 of 12,764 np_orgs
EINs reach a spending UEI (0.22%)**. Both are `OUT_OF_SCOPE_BY_CONSTRUCTION`, not coverage
failures.

### J1b · Two worked examples, in full — OSHA ITA and Form 5500

*These are the two the owner named, and they are the two most likely to be read as our failure.*

**OSHA ITA — "this casino isn't in your injury data."**

| the blank | the right value | why |
|---|---|---|
| Establishment not in ITA for a covered year, and we swept | `NOT_IN_SOURCE` | We hold CY2016–CY2025, 3,189,050 establishment-years, 5,062 in a gambling NAICS. If it isn't there, it isn't there |
| Establishment below OSHA's size threshold, or in a non-covered industry | `BELOW_REPORTING_THRESHOLD` | Electronic submission is required only of establishments **above size thresholds in covered industries** |
| Year before CY2016 | `NOT_CHECKED` / out of window | ITA electronic submission does not reach back |

**AND THE SENTENCE THAT MUST TRAVEL: an establishment absent from ITA is not an establishment
with zero injuries, and not one with zero employees. It is an establishment that did not file.**
ITA is self-reported — the employer files its own 300A — and compliance is uneven. **The set of
establishments filing under one tribe changes year to year, so a tribe-year SUM is not a
consistent panel and must never be differenced as one.** Every row carries
`DO_NOT_SUM_ACROSS_YEARS_WITHOUT_A_BALANCED_PANEL`.

**Form 5500 — "this tribe isn't in your employment data."**

| the blank | the right value | why |
|---|---|---|
| Tribe sponsors no qualifying retirement or welfare plan | **`OUT_OF_SCOPE_BY_CONSTRUCTION`** | **Form 5500 is filed by PLAN SPONSORS. A tribe with no qualifying plan has no filing, and that is not a data gap.** 147 of our 275 facility tribes have no gaming-NAICS 5500 filing — most are small operations that sponsor no plan |
| Tribe files, but we want a per-facility figure | `OUT_OF_SCOPE_BY_CONSTRUCTION` | **A 5500 row keys to an EIN, never to a facility.** Every staged row carries `facility_id = ""` |
| We have a participant count and want employment | *not a blank — a different variable* | **Plan participants are not employees.** `TOT_ACTIVE_PARTCP_CNT` *brackets* employment, and the bracket is conditional in two directions at once |

**FAADS — the cleanest `OUT_OF_SCOPE_BY_CONSTRUCTION` in the product.** A pre-FY2007 assistance
row has no DUNS and no EIN because **the 624-byte FAADS record layout has no such field**, and
Census documented that FAADS `does not currently collect DUNS information for recipients of
Federal assistance.` **The recipient is not missing an identifier we failed to collect. The
form never asked.** That is documentary, and it is the difference between "our pipeline is
thin" and "the record does not exist."

## J2 · Attribution is 79.0% blended, and FY2023–26 is 100% by construction

Already at §E6. Repeated here because it is the number most likely to be quoted alone.
**$244.77B of $310.01B (79.0%) is attributed, across 498 entities and 888,862 rows — but that
79.0% is a blend of 42.6–79.0% in FY2000–2022 and exactly 100.0% in FY2023–2026.**

## J3 · Flag-based coverage is a floor, and we can size the floor

**$140.00B of $244.77B attributed (57.2%), on 565,364 rows, carries no Native set-aside of
any kind** once set-aside is forward-filled to award level. A flag-based method recovers the
complement, $104.76B. **This is a floor twice over**: 8(a) is open to non-Native individually
owned firms, so the instrument used is *more* generous than the business-type
self-certification flag a competitor actually uses.

Independently, on the assistance side: of attributed federal assistance, **only 51.9% flows
through a programme whose CFDA title contains a tribal word.** Filter the federal money to
programmes with "Indian" in the name and you lose half of it.

## J3b · IDENTIFIER-based coverage is a floor too — and it is the SAME SIZE

*Added 2026-08-26 by `code/276_measure_discovery_gap.py` (READ-ONLY, zero network requests).
Artefact: `docs/DISCOVERY_GAP.json`. Doctrine and full working:
`docs/PULL_DISCIPLINE.md` § TARGETED PULLS: THE SELECTION DOCTRINE.
Type: **STRUCTURAL (ours)** — the data cannot exist, because the selection never asked for it.*

J3 sizes the **flag-side** floor. This is the **identifier-side** floor, and it had never been
measured. **An identifier-seeded pull can never discover an entity we do not already know** —
that is the defining property of the selection, not a defect in any script. It is the reason
J2's "100% attributed in FY2023–26" is true: **100% attributed means 0% discovered.**

**CITATION — measured, 2026-08-26, on two independent instruments that were not tuned to each
other:**

| | universe | reachable by identifier selection alone | **invisible** |
|---|---:|---:|---:|
| **Assistance** — 115's per-FY archive extracts, FY2007–2026, 701,458 rows, `population_basis` stamped at pull time | 6,390 entities | 1,524 (23.85%) | **4,866 — 76.15%**, on rows carrying **$33.53B of $219.10B (15.30%)** |
| **Prime** — HigherGov flag-at-award extract, 1,101,796 rows, FY1979–2023, carrying the true USAspending business-type self-certification columns | 12,643 flagged entities | 2,886 (+38 via declared parent) | **9,719 — 76.87%**, carrying **$70.96B** |

**76.15% and 76.87%, from two unrelated sources and two different programmes.** The honest
one-line form: **roughly three quarters of the entity universe is unreachable by identifier
selection alone.** The SAM current-registration route agrees in direction (4,251 of 6,582,
64.59%, $59.37B).

**THE DECOMPOSITION, WHICH A READER MUST BE GIVEN WITH THE HEADLINE — the two sides are
opposite.** Being outside the selection set is not the same as never having been seen. Tier C
holds **9,335 UEI rows, 9,320 of them `attribution_method = unmatched`** — identifiers
harvested and never adjudicated:

| | prime | assistance |
|---|---:|---:|
| outside the selection set | 9,719 | 4,866 |
| …**on file at tier C, unadjudicated** — a REVIEW backlog | **9,154 (94.2%)** | 156 (3.2%) |
| …**absent from the ledger entirely** — true non-discovery | 565 (5.8%) | **4,696 (96.5%)** |

**On contracting the gap is an adjudication backlog; on assistance it is genuine
non-discovery.** Quoting 9,719 as "entities we have never seen" would be wrong by 94%.

**AND IT IS NOT A COUNT OF MISSING NATIVE ENTITIES.** Every entity above is
self-certified and self-certification is not determination — Goldbelt Raven, an ANC
subsidiary, certifies `alaskanNativeCorporationOwnedFirm = NO`. The figure measures the
**search surface** an identifier-only pull cannot see. It is a bound on what we could
find, never a claim about what we are missing.

Related, and fixed the same day: `44_pull_contracts_transactions.py` selected on UEI alone
while `114_pull_prime_archive.py` matched uei OR cage OR parent_uei. Measured against 114's
own kept rows, that lost **75,303 of 904,282 rows (8.33%) across FY2007–2026** — rising from
0.23% in FY2014 to **68.3% in FY2026**. 44 now resolves CAGE and declared-parent to recipient
UEIs offline and recovers **70,290 of the 75,303 (93.3%)**. The residual 5,013 rows are CAGEs
absent from `fpds_uei_cage_map.csv` and remain unreachable.

## J4 · The four known seams, in one place

| seam | column | what breaks | fixed? |
|---|---|---|---|
| Vocabulary | `prime_contracts.extent_competed` | Two vocabularies; a label filter drops FY2008–2016 | **YES** — use `extent_competed_normalized`, 100% populated |
| Grain | `prime_contracts.setaside` | Per-transaction vs per-award; blanks rendered as "None reported" | **NO** — forward-fill before any share |
| Construction | `prime_contracts.attributed_flag` | 100% on FY2023–26 by construction | **NO** — structural |
| Units | CT gaming `payout` | Units change mid-series, name does not | **NO** — not in the clean table; confirm before raw read |

Add three more measured today: **`prime_contracts` grain (BGOV aggregate vs archive
transaction)**, **`cage_code` coverage (0.4% → 100% across FY2017)**, and
**`subawards.duplicate_status` (a 53% inflation if summed past)**.

### J4a · Three more in `federal_funding_transactions.csv`, all now DECLARED IN COLUMNS

*Measured and harmonised 2026-08-26 by `code/334`–`337`. Full write-up in
START_HERE and `docs/ASSISTANCE_SEAM_HARMONIZATION.json`.*

| seam | column | what breaks | fixed? |
|---|---|---|---|
| **Identifier scheme** | `tribe_id` | INTEGER (365,535 rows, **$107.50B**) and Cedar NEID (183,995) in one column. Per-entity totals SPLIT; distinct-entity counts DOUBLE-COUNT. Nothing blank, nothing malformed. | **DECLARED, NOT MERGED** — read `tribe_id_scheme_resolved` (never blank) and **filter to one scheme before any per-entity aggregate** |
| **Source vintage** | `source_archive_stamp` | Three vintages, year-aligned; 67.9% of rows carried no stamp at all | **YES** — `source_vintage` populated on all 701,955 rows |
| **Flag rendering** | `business_types_description` | `AMERICANTRIBAL` / `FEDERALLY RECOGNIZED` vs `AMERICAN TRIBAL` / `FEDERALLY-RECOGNIZED`; an exact filter drops **7,160** Native recipients | **YES** — use `business_types_description_normalized` |

**The identifier seam is the one that will bite, and it is deliberately NOT
auto-merged.** `assistance_tribe_id_crosswalk.csv` proposes a NEID for 344 of
the 361 integers, but **all 344 are confidence tier B** and **122 rest on the
containment matcher**, which AGENTS.md forbids from keying a dollar. The
proposal travels as `tribe_id_neid_proposed` / `_tier` / `_basis` — adopt it
explicitly, inherit the tier, and refuse the containment rows for any dollar
figure. **17 integers have no candidate at all** and are spine gaps, not junk.

**Until a ruling lands, the honest published statement is per-scheme, not
pooled.** "N tribes received federal assistance" computed across the whole
table is wrong in both directions at once — and note that the entity universe
already steps **968 (FY2023) → 620 (FY2024)** for this reason, with row counts
holding flat, so the step is internal to Cedar and not a fact about Indian
Country.

### J4b · Five tables were invisible to the coverage tools — a NAME, not a gap

Three tools ask "what period is this row in?" and each had its own answer, so a
period column absent under the name a tool looked for read exactly like a table
with no dates. **Five fully-dated tables were being missed on the name alone:**

| table | period column | rows dated | span |
|---|---|---|---|
| `gaming_revenue_bounds` | `fiscal_year` (a YEAR) | 13,803 / 13,803 | 1994–2025 |
| `ca_gaming_payments` | `period_end` | 40,164 / 40,164 | 2001–2026 |
| `resource_revenue` | `period_end` ∥ `payment_date` | 10,482 / 10,482 | 1993–2026 |
| `consultation_events` | `notice_date` | 11,402 / 11,402 | 1994–2026 |
| `ferc_docket_filings` | `filed_date` | 102,615 / 102,615 | 1990–2026 |

`35_coverage_audit.py` held `filing_date` but not `filed_date`, and
`publication_date` but not `notice_date`. All five are now declared once in
**`code/cedar_period_columns.py`**, which 35, 102 and 301 all read; 301 fails at
import if its own registry disagrees. This is the **third** instance of the
same defect in one day — `102` printed 0.0% for 19 days on two tables keyed
`tribe_entity_id`, and `35` reported gaming as undated while both gaming files
were fully dated.

⚠ **`ferc_docket_filings.issued_date` is populated on ZERO of 102,615 rows**, so
301's declared `filed → issued` lag pair measures nothing. An empty
distribution renders as "no lag detected" rather than "not measurable" — the
flattering reading. Do not quote a filed-to-issued lag.

**A year stays a year.** `gaming_revenue_bounds` is declared `kind="year"` and
no month or day is synthesised for it. Fabricating one is the defect that
already put 415 gaming dates on day-15 and day-31.

## J5 · Identifier discontinuity — DUNS to UEI, measured

**CITATION — measured, 2026-08-26.** `recipient_duns` populated in
`federal_funding_transactions.csv`: 93.9% (FY2019) · 93.3% (FY2020) · **78.2% (FY2021)** ·
**16.8% (FY2022)** · **0.0% (FY2023–2026)**. `recipient_uei` runs the other way: 97.4%
(FY2019) → 100.0% (FY2025). The crossover sits inside FY2022, exactly where the transition date
predicts. **An entity has DUNS-keyed history and UEI-keyed history that do not join without a
crosswalk.**

**CITATION — the date, verified in a Federal Register final rule.** USDA Rural Development,
*Rural Development Regulations With the Unique Entity Identifier (UEI) for Federal Awards*,
**89 FR 34955** (2024-05-01):
> `On April 4, 2022, the universal identifier used across the Federal Government transitioned from using the DUNS number to the UEI, which is now the official identifier for doing business with the Federal Government.`
Corroborated by a pre-transition notice, U.S. Dept. of Education, 86 FR 73264 (2021-12-27):
`On and after April 4, 2022, [entities] will not need to use a DUNS for entity registration or
reporting. If registering before April 4, 2022, you can obtain a DUNS number from Dun and
Bradstreet…`

**⚠ AND A TRAP: THERE IS AN EARLIER DATE THAT IS NOT A BREAK.** FAC 2005-91, **FAR Case
2015-022**, 81 FR 67736, effective **2016-10-31**, removed "DUNS" from the FAR and substituted
a generic `unique entity identifier`. **That is a schema change with no value change — the
field was relabelled, the values were still DUNS. Do not read the 2016 relabel as an identifier
break.** *(The "FAR Case 2019-014" in circulation is not the right case number.)* The grants-side
relabel is 2 CFR Part 25 at 85 FR 49506, effective 2020-11-12.

**UNVERIFIED — whether historical records were retrofitted with UEIs.** 2 CFR 25 and the FAR
both define the identifier by reference to whatever SAM issues and are silent on retrofitting.
GSA has **retired** its UEI transition page (`gsa.gov/entityid` → 404), and `api.sam.gov` is
owned by another agent. **Safe wording until someone verifies: *"Records before 2022-04-04 were
created with DUNS-valued identifiers. Whether the historical store was retrofitted with UEIs is
unverified; treat the entity key as potentially discontinuous at 2022-04-04 and join on a
crosswalk rather than on the raw identifier."***

**AND ONE MORE, WHICH SILENTLY COLLAPSES ENTITIES.** 2 CFR 25.110(a)(1)(i): where an agency
grants an exception, it `must use a generic entity identifier in the data it reports to
USASpending.gov`. **Some prime assistance awards carry a deliberately NON-UNIQUE identifier by
rule. Those rows collapse together under any entity-level `group by`.**

## J6 · The FY2007 double-count question, answered before anyone asks

We describe our holdings as *"701,955 assistance rows FY2007–2026 **plus** 2,769,748 FAADS
rows FY2001–2007."* **Both tiers include FY2007** — 11,443 rows in the modern file and
774,755 in FAADS. **State the de-duplication rule in the codebook.** Related and already
recorded: `faads_transactions.csv` is a **strict subset** of
`faads_transactions_all_agencies.csv` (all 59,514 keys checked); reading both double-counts
$53M.

## J7 · The settled FY2007-vs-FY2008 discrepancy

The brief flagged a conflict between `START_HERE.md` (FAADS tops out at 2007) and
`docs/USASPENDING_PROBLEM_BRIEF.md` (said to say 2008). **There is no conflict. There are
three different FY2008 statements about three different objects:**

1. **FAADS as we hold it: max fiscal year 2007.** Measured — 2,769,748 rows, FY2001–2007, no
   2008 row exists. Both documents agree (`USASPENDING_PROBLEM_BRIEF.md` line 61 says
   "FY2001–2007").
2. **The FAADS *system* ended after FY2007** and USAspending replaced it in FY2008 — a
   statement about the system, at line 105.
3. **"The static archive only goes back to FY2008"** at line 81 is about **prime contracts**,
   and it is **already struck** by the correction at lines 19–25 of the same file: *"The
   static archive DOES reach FY2007."*

**Nothing needs changing except that line 81 should carry a pointer to its own correction.**

## J8 · Documents that are stale and must not be quoted

- **`data/clean/coverage_audit.csv`** — dated 2026-08-06, reports prime = 0 rows for
  FY2023–26 (actual 45,747 / 53,056 / 48,879 / 61,813).
- **`dist/`** — `notes_index.json` still records prime at 617,142 rows / FY2000–2022 / 470
  entities. **Nothing in `dist/` should ship until it is rebuilt.**
- **`START_HERE.md`'s assistance row count (684,923)** — the file holds **701,955**.
- **`docs/COMPETITIVE_POSITION.md`** — mixed vintage; §0's ground-truth table is two
  generations stale.
- **`docs/CICD_BENCHMARK.md` `INTERNAL-05`** — describes `extent_competed` as unfixed. It is
  fixed. Update it.

## J9 · Where we are standing on prior work

**Cedar Press's entity spine is a derivative of a CICD public data product**, and CAGE-first
linkage, parent-vendor observation and per-record verification provenance are **published
CICD method** (Chavis, Gregg & Moreno, 2022). **Cedar Press must not describe per-record
attribution provenance as an invention.** This is a limitation on our *claims*, and it belongs
in the same register as the limitations on our data.

---
---

# PART IV — WHAT A READER MUST BE TOLD

*One page. Written to travel in a Collection's `method` field and in the `.notes.json`
comparability-breaks block — because these limits have to move with the data, not sit in a
document nobody reads.*

## The four sentences that go on every page

1. **Coverage is a floor, not a census.** Every collection here counts what a federal
   reporting rule required somebody to file. Where the rule did not reach, the data does not
   exist — and we say so with a named reason rather than a blank.
2. **A blank is typed.** `NOT_IN_SOURCE` · `BELOW_REPORTING_THRESHOLD` ·
   `OUT_OF_SCOPE_BY_CONSTRUCTION` · `SUPPRESSED` · `REPORTED_EMPTY` · `NOT_CHECKED`. If an
   entity is missing, we tell you which.
3. **Several series contain dates on which the rules changed, not the world.** They are listed
   below. A step at one of these dates is a regime change until proven otherwise.
4. **Attribution is ours, and it is uneven.** 79.0% of prime contract dollars are attributed
   to a Native entity; FY2023 onward is 100% by construction, so the rate is not a trend.

## The dates a reader must be handed

| if your series crosses… | then… |
|---|---|
| **FY2007** (assistance) | Per-entity assistance is not required before FY2007 (FFATA §2(b)(2)). FAADS has no identifier field at all. **And Interior's identifier does not arrive until FY2011.** |
| **2008-01-01** (lobbying) | Filing counts roughly DOUBLE. Semiannual became quarterly, the dollar rounding grain halved, the censoring point halved, and a new form type appeared. **Nothing about 2008 in a filing count is behaviour.** |
| **FY2010–FY2011** (subawards) | Subaward reporting switches on. There are no subawards before it, by rule. FY2012 forward is the first comparable stretch. |
| **FY2020–FY2023** (assistance) | COVID relief. CARES sent **$8B** and ARPA **$20B** directly to tribal governments; ARPA Title XI added **$8.8B** more. **$22.07B of FY2021 — 54% of the year — is four relief programmes.** Do not read growth. |
| **2021-06-25** (assistance) | *Yellen v. Chehalis*. ANCs are eligible for the Coronavirus Relief Fund and **not** for Fiscal Recovery Funds. The recipient universe changes between the two. |
| **2022-04-04** (all award data) | DUNS retired, UEI adopted. Measured: assistance DUNS coverage 93% → 0% across FY2021–FY2023. Entity history does not join across it without a crosswalk. |
| **2024-01-12** (NAGPRA) | Revised 43 CFR 10. The "culturally unidentifiable" category disappears and a new notice type appears. The 2024–26 surge is regulatory first. The 2023 doubling is **not yet explained.** |
| **2024-10-01** (Single Audits) | The audit threshold rose from $750,000 to $1,000,000. The bottom of the entity distribution leaves the population, landing in submissions received during **2026**. |
| **FY2016** (Native set-asides) | **`Buy Indian` and `Indian Business` are one instrument recorded under two codes.** `Indian Business` is zero before FY2014 and takes over in FY2016 after DOI's 2013 Buy Indian rule created a second set-aside tier. Read alone, `Buy Indian` says Native set-asides collapsed 62%. **Summed, they rose 44%. Always sum them.** |
| **2000-12-21** (any UI-based employment) | Tribal employers entered the FUTA definition of "employment" (Pub. L. 106-554 §166). QCEW, QWI and LODES all inherit the UI frame. **Tribal casino jobs appearing in 2001 QCEW are a coverage change, not growth.** |
| **2020-08-31** (contract counts) | The FPDS reporting floor tripled, $3,500 → $10,000, and rose again to $15,000 on 2025-10-01. **A "small contract count" cannot be interpreted across these dates.** FY2026 is 71.9% sub-$2,500 modifications; do not publish an FY2026 contract count. |

## The four numbers a reader will otherwise misread

- **449, not 784, is our count of operating gaming facilities.** NIGC reports 545 (FY2025) and
  CRS 532 (Sept 2024). **We undercount operating and overcount historical.** Both directions,
  same sentence.
- **4,728 of 6,780 tribal Single Audit records are not public — by the auditee's own election
  under 2 CFR 200.512(b)(3).** The audits exist. The SEFA survives; the reporting package does
  not. Public share fell 39.4% (2016) → 22.4% (2024), and that trend is about disclosure, not
  about money.
- **6,453 of 12,764 organisations file Form 990-N and report no financial detail.** A zero
  there is the filing regime.
- **6,217 recipient EINs carrying $4.96B appear on filed Schedule I returns and in no row of
  the 1,957,340-organisation IRS Business Master File.** They are not missing. Tribal
  governments are not 501(c)(3) organisations and file no Form 990.

## The one sentence for the `method` field

> Cedar Press reports what federal reporting rules required somebody to file. Coverage is a
> floor: subawards begin at the FFATA reporting threshold in FY2010, per-entity assistance at
> the FFATA floor in FY2007 (FY2011 at Interior), and Single Audits above $1,000,000 in
> federal expenditures (previously $750,000, $500,000, $300,000). Lobbying filing counts
> roughly double at 2008-01-01 when the LDA moved from semiannual to quarterly reporting.
> FY2020–FY2023 assistance carries $28B of statutory COVID relief and must not be read as
> growth. Every absence is typed — `NOT_IN_SOURCE`, `BELOW_REPORTING_THRESHOLD`,
> `OUT_OF_SCOPE_BY_CONSTRUCTION`, `SUPPRESSED`, `REPORTED_EMPTY` or `NOT_CHECKED` — so a blank
> is never mistaken for a gap in our work. Full register:
> `docs/ASSUMPTIONS_AND_LIMITATIONS.md`.

---
---

# PART V — WHAT COULD NOT BE VERIFIED

*Named, with what was tried, so the next agent does not repeat the search. **An unverified
citation is worse than no citation**, so nothing below is asserted in the body above without
this flag.*

## Could not be retrieved

| item | status | what was tried |
|---|---|---|
| **GAO / CRS quantification of ARRA tribal totals** | **UNVERIFIED** | `gao.gov` returns **403** (Akamai) to everything including `/robots.txt`; `crsreports.congress.gov` returns **520**/**403**. govinfo's GAOREPORTS collection stops around 2008. **The ~$2.05B ARRA tribal figure and the $8.8B ARPA Title XI figure are ARITHMETIC on verbatim statutory line items, not agency-published aggregates. Cite the line items, never the sum.** |
| **Assistance Listing numbers for BIA, IHS, ICDBG, BIE, NTIA TBCP, SSBCI, PPP, EIDL** | **UNVERIFIED** | These live in SAM.gov Assistance Listings; `api.sam.gov` is owned by another agent. **Verified from the Federal Register instead: 21.019, 21.027, 21.026, 21.029, 14.867 only.** |
| **How ISDEAA Title I contracts vs Title IV compacts are REPORTED** — FPDS row or assistance row | **UNVERIFIED, and load-bearing** | No free official source found. **Do not assume BIA/IHS relief money is assistance.** This decides whether ARPA §11001's $6.094B IHS and §11002's $900M BIA land in our prime file, our assistance file, or both. |
| **LDA CPI-adjusted registration thresholds for 1997, 2001, 2005, 2009, 2013, 2017, 2021** | **UNVERIFIED** | Current guidance supersedes all prior revisions and carries no history table; `lobbyingdisclosure.house.gov/amended_lda_guide.html` **404**; CRS **404/520**. **Retrieve an archived guidance revision or the relevant-year GAO LDA compliance report before asserting any intermediate value.** Only the current $3,500 / $16,000 (eff. 2025-01-01) is verified. |
| **Whether LDA bulk data reaches 1999** | **UNVERIFIED** | The House LD archive demonstrably starts at `2002_MidYear_XML.zip` (113 files, arithmetic reconciles). The Senate search UI offers 1999–2026. `lda.gov` was outside scope. **Our 1999–2001 filings need a stated provenance.** |
| **FPDS-NG Data Dictionary — when `IndianTribe`, `TriballyOwnedFirm`, ISBEE/IEE `typeOfSetAside` codes were introduced** | **UNVERIFIED** | Every `fpds.gov` path 301-redirects to `sam.gov/contracting`, which another agent owns. **Nothing about those field names or their history should be asserted.** The regulatory floor is the usable bound: an ISBEE/IEE code cannot correspond to a real solicitation before **2013-07-08** (Interior) or **2022-03-14** (IHS). Earlier rows carrying such a code are a retroactive recode. |
| **QCEW numeric primary-suppression criterion** | **UNVERIFIED** | BLS publishes no n-rule and no p-percent parameter anywhere reachable; the only cited authority is FCSM Statistical Policy Working Paper 22. **Do not state a QCEW cell threshold.** |
| **QCEW ownership treatment of tribal employers** | **UNVERIFIED** | No tribal ownership code exists (codes 0,1,2,3,4,5,8,9). Searches of the ownership page, Q&A and Handbook chapters for "tribal"/"tribe"/"Indian" return zero substantive matches. **Whether tribal establishments are coded Private or Local Government, and whether it ever changed, is unknown.** The governing FR notice is linked to `doleta.gov`, out of scope. |
| **LODES/QWI noise-infusion parameters** | **UNVERIFIED by design** | TP-2006-01 defines the distortion bounds symbolically only. **Never quote a percentage.** |
| **NPS projection of NAGPRA notice volume under the 2024 rule** | **UNVERIFIED — and the claim must not be made** | The full 666 KB rule text yields three hits on "number of notices," none a projection. **The rule's Table 7 (`+14` responses) compares two baselines, not before/after. Citing it as "NPS expected 14 more filings" would be a serious misread.** Closest defensible proxy: `407 museums and 122 Federal agencies will be required to update inventories within five years`. |
| **The 2023 NAGPRA doubling (244 → 496), a year before the rule bound** | **UNEXPLAINED** | Candidates: the 2022 proposed rule and comment period; institutional anticipation; external pressure on museums during 2023. **None verified. Do not close this by picking one.** |
| **`California v. Cabazon` decision DAY** | **UNVERIFIED** | govinfo's SCOTUS resolver returns 500; supremecourt.gov out of scope. Citation **480 U.S. 202 (1987)** confirmed via federalregister.gov. **Write "decided in 1987"; do not print a day.** |
| **Original DFARS entry date of 252.226-7001, and when "Native Hawaiian small business concerns" was added** | **UNVERIFIED** | Verified present by **April 1994** (the earliest year of FR full-text indexing). The NHO addition falls between 2002 and 2019; the 2019 rule's own abstract says it only added contact information. |
| **Rev. Proc. 84-36** | **UNVERIFIED** | Pre-1996 Internal Revenue Bulletins are not posted at `irs.gov/pub/irs-irbs/`; the ITG revenue-procedures subpage **404s**. **Do not assert a Rev. Proc. 84-36 political-subdivision list. Use §7871(d), which is retrievable and dispositive.** |
| **Whether pre-2022 records were retrofitted with UEIs** | **UNVERIFIED** | GSA retired its UEI transition page (404). Safe wording supplied at §J5. |
| **The CFDA → Assistance Listings / SAM.gov migration date** | **UNVERIFIED** | `api.sam.gov` owned by another agent. The *behaviour* (join on the number, never the title) is measured in our own file and stands regardless. |

## Two things that are NOT in this register, deliberately

- **Nothing about `api.sam.gov`, `api.usaspending.gov`, NIGC or state gaming regulators was
  retrieved.** Other agents own those hosts. Where an answer required one of them it is flagged
  UNVERIFIED above rather than guessed.
- **`code/227_anomaly_sweep.py`'s findings are not restated here.** That document owns the
  steps; this one owns the rulebook. Duplication would let the two drift.

## How to extend this file

1. Run `py -3 code/234_measure_reporting_regime_signatures.py` — READ-ONLY, no network, writes
   one JSON to `review/`.
2. A new entry needs **a type**, **a citation** (statute / regulation / agency guidance / a
   measured observation naming its script and artefact), and **a date the rule BOUND** — not
   the date it was published.
3. **If you cannot retrieve it, put it in the table above rather than in the body.** An
   unverified citation is worse than no citation: it survives review that a blank would not.
4. Use the `docs/ANOMALY_REPORT.md` key if one exists; mark a genuinely new one **`NEW`** so
   227 can adopt it.
