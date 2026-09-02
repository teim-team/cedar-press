# The biggest Native federal contractors, and the ownership chains that hide them

*Draft. Written against **Cedar Press, "Top Native Federal Contractors, with Ownership
Chain," vintage 2026 Q3**, dataset `contractor_ranking.csv` — 1,429 rows, period
FY2000–FY2026 — built 2026-08-26 from `prime_contracts.csv` (mtime **2026-08-26
18:45:37**), with the entity spine and identifier ledger at 2026-08-26 18:59. Every figure
below is reproducible by running `code/269_build_contractor_ranking.py`, which stamps each
measurement with the vintage of the file it came from. **FY2025 is the last complete fiscal
year in this release; the prime record stops at action date 2026-07-03, so every
calendar-2026 and FY2026 figure here is year-to-date.** Cite the release, not the article —
a year-turn refresh is a version bump and a paragraph, not a rewrite.*

---

The second-largest Native-owned firm in the federal contracting record is a fuel refiner
called Petro Star. Since fiscal 2000 it has taken **$3.60 billion** in federal prime
obligations. It is owned by Arctic Slope Regional Corporation, the ANCSA corporation for
the Iñupiat of Alaska's North Slope.

Across twenty-seven fiscal years and every one of those dollars, Petro Star has never
appeared on a federal contract carrying a Native set-aside. Not 8(a), not Buy Indian, not
the Indian Business set-aside. If you build a picture of Native federal contracting from
the preference flags — which is how nearly everyone builds it, because it is the only field
the data hands you — Petro Star is not in the picture at all.

It is not an outlier. It is the pattern.

## The ranking

Cedar Press maintains an identifier ledger that ties Unique Entity IDs and CAGE codes to
the Native entity that owns the firm behind them. Restricting to links that are
hand-checked or independently corroborated — the ledger calls this tier A, and nothing
weaker is published — the ledger resolves **1,429 operating companies to 283 Native
entities**, carrying **$176.74 billion** in federal prime obligations across FY2000–FY2026.

| # | Owner | Class | Obligations | Operating cos. | UEIs | No set-aside | Largest subsidiary |
|---:|---|---|---:|---:|---:|---:|---|
| 1 | Arctic Slope Regional Corporation | ANC regional | $25.17B | 57 | 56 | 69.1% | Petro Star, Inc. — $3.60B |
| 2 | NANA Regional Corporation | ANC regional | $19.89B | 70 | 67 | 59.5% | TKC Integration Services — $4.12B |
| 3 | Chugach Alaska Corporation | ANC regional | $11.01B | 23 | 22 | 37.3% | Wolf Creek Federal Services — $1.43B |
| 4 | Chenega Corporation | ANC village | $10.64B | 53 | 52 | 48.2% | NJVC — $1.12B |
| 5 | Afognak Native Corporation | ANC village | $10.30B | 61 | 59 | 46.1% | FSS Alutiiq Joint Venture — $0.86B |
| 6 | Cherokee Nation | Tribe | $9.92B | 48 | 45 | 54.1% | Cherokee Nation Management & Consulting — $1.56B |
| 7 | Calista Corporation | ANC regional | $8.83B | 34 | 34 | 85.0% | Defense Systems and Solutions — $3.27B |
| 8 | Ukpeaġvik Iñupiat Corporation | ANC village | $5.76B | 47 | 47 | 52.7% | Bowhead Science and Technology — $0.58B |
| 9 | Bering Straits Native Corporation | ANC regional | $4.85B | 26 | 26 | 59.2% | Paragon Professional Services — $0.77B |
| 10 | Bristol Bay Native Corporation | ANC regional | $4.32B | 25 | 25 | 41.3% | CCI Utility and Construction — $0.94B |
| 11 | Koniag, Incorporated | ANC regional | $4.29B | 24 | 23 | 50.2% | Tuknik Government Services — $0.58B |
| 12 | Cook Inlet Region, Incorporated | ANC regional | $4.19B | 36 | 34 | 78.2% | *name withheld* — $1.18B |
| 13 | Goldbelt, Incorporated | ANC village | $3.54B | 19 | 17 | 43.8% | Goldbelt C6 — $0.43B |
| 14 | The Chickasaw Nation | Tribe | $3.18B | 26 | 21 | 42.4% | Chickasaw Nation Industries — $0.36B |
| 15 | Winnebago Tribe of Nebraska | Tribe | $3.13B | 35 | 33 | 54.1% | HCI Management Services — $0.88B |

*Source: `data/clean/contractor_ranking.csv`, built 2026-08-26 from `prime_contracts.csv`
(mtime 2026-08-26 18:45:37). Nominal dollars, `total_obligations`. FY2026 is a nine-month
partial, cut at action date 2026-07-03; it is 3.1% of the total.*

Two things jump out of the right-hand columns before you get to any of the money.

**The names do not match.** Cherokee Nation's largest contracting subsidiary is called
Cherokee Nation Management & Consulting, and that is the exception. NANA's is TKC. Arctic
Slope's is Petro Star. Bristol Bay's is CCI. The Winnebago Tribe of Nebraska's is HCI
Management Services. Fifty of Afognak Native Corporation's sixty-one operating companies
are named Alutiiq, after the people, not after the owner. Nothing in a contract record
connects any of these firms to the entity whose shareholders or citizens they belong to.

**One owner holds many identifiers.** NANA Regional Corporation appears in this data under
**67 distinct Unique Entity IDs across 70 operating companies**. Thirty-one entities in the
ranking hold ten or more operating companies each; 133 of the 283 hold two or more UEIs.
That is not corporate exotica — it is the SBA 8(a) programme working as designed. A firm's
8(a) term is nine years and non-renewable, so an owner wanting continued access stands up a
new legal entity with a new identifier and a fresh clock. SBA says so plainly on its own
programme page: tribal, ANC and Native Hawaiian owners "may have multiple 8(a) firms." What
SBA does not publish is any roster mapping those firms back to their parents. GAO flagged
the oversight consequences of exactly this structure in **GAO-06-399**, twenty years ago.
The map still does not exist.

## What the flags miss

Which brings us back to Petro Star.

Take the ranking and ask a narrow question of it: how much of this money sits on awards
that carry a Native set-aside — 8(a), Buy Indian, or the Indian Business set-aside — on any
transaction at all?

**$98.39 billion of the $176.74 billion does not. That is 55.7%, on 121,698 of 179,488
awards.** A method that finds Native contractors by looking for the preference flag recovers
the other $78.35 billion and misses this.

Worse, at the level of the firm: **499 of the 1,429 operating companies — 34.9%, holding
$21.97 billion — never carry a Native set-aside on a single transaction in twenty-seven
years.** A flag-based build would not have found them at all, and so would never have known
to attribute them. **114 of the 283 owning entities never appear on a Native-preference
award.** Two owners in five are invisible to the instrument.

And the set-asides written specifically for Indian Country are almost invisible in the
other direction. Buy Indian and the Indian Business set-aside together account for **$797
million — 0.45% of the total.** The rest of the preference dollars are 8(a), which is a
general disadvantaged-business programme open to firms with no Native ownership at all.

Which is why the number is a floor and not an estimate. Counting 8(a) as a Native flag when
it is not one makes the instrument *generous* to the flag-based method. The true share that
no preference field can see is higher than 55.7% — and no preference field can tell you how
much higher.

## The argument this settles

In December 2025, Senator Joni Ernst's office put the figure for 8(a) awards to
Native-owned firms at $16.1 billion. The Poarch Band of Creek Indians publicly disputed the
characterisation, saying the federal data had been misapplied. Tribal Business News reported
the argument (Brian Edwards, 2025-12-11) and could do nothing else with it, because no
public dataset resolves an operating company to the entity that owns it.

This one does. **The Poarch Band of Creek Indians ranks 34th**, with **$812.4 million** in
federal prime obligations across **seven operating companies** — PCI Government Services,
PCI Aviation, PCI Productions, PCI Support Services, Media Fusion, Creek Defense Solutions
and one joint venture. Every one of those links is hand-adjudicated against a named source.
**47.8% of that money sits on awards with no Native set-aside of any kind.** Whatever one
thinks of the policy argument, the underlying question — whose contracts are whose — now
has a checkable answer.

## Where this is Alaska

The most consequential structural fact in the table is geographic. **Entities domiciled in
Alaska hold 76.5% of the publishable total.** Twelve ANC regional corporations alone hold
**48.6%**; twenty-four ANC village corporations hold another **27.2%**; 226 federally
recognized tribes elsewhere hold **22.6%** between them. The top ten owners hold 62.6% of
everything; the top fifteen hold 73.0%. Most published work on Native contracting cannot
see this concentration, because the entity datasets it rests on stop at federally recognized
tribes in the contiguous United States and exclude ANCs entirely.

## What this is not

**It is a floor, twice over.** Cedar Press attributes $244.77 billion of the $310.01 billion
in this file to a Native entity; the ranking uses only the $176.74 billion whose identifier
link is tier A. The remaining $68 billion is real money whose owner we have not finished
proving — and the discipline is not decorative. Attributed at face value, the eighth-largest
"Native contractor" in the file would be an Alaska Native village government credited with
$8.75 billion, of which $3.53 billion belongs to General Dynamics Information Technology and
$2.03 billion to Peraton. That is a name-clustering artefact, it is tier B, and tier B does
not publish.

**The attribution rate is a blend, not a quality score.** All 209,495 FY2023–FY2026 rows are
100% attributed *by construction*, because those years entered the dataset already filtered
to our identifier population. Earlier years came from a differently built source and run
lower. 79% is not a coverage measure for any single year.

**FY2025 is the last complete year.** Tier-A obligations were **$11.92 billion** in FY2025.
The FY2026 figure of **$5.45 billion** is year-to-date through 2026-07-03 and will grow.
FPDS also restates retroactively for up to five years, so even closed years drift slightly.

**Native Hawaiian organizations are under-represented here**, at five entities and $488
million. That is a statement about how far our verification has reached, not about how much
NHO-owned firms contract.

**134 of the 1,429 operating-company names are withheld**, holding $6.08 billion. A sole
proprietor's legal name is a private person's name, and SAM's public search resolves a UEI
straight to it, so any name without a corporate form is suppressed by default — including
some that are plainly corporate. Contract facts publish on those rows; the name and the UEI
do not.

---

### Method, sources and credit

Entity identifiers follow the **NEID** scheme published by the **Center for Indian Country
Development, Federal Reserve Bank of Minneapolis** (*Native Entity Connector Crosswalk*,
February 2026), which seeded the Cedar Press entity spine. The `ANVC-` and `ANRC-` prefixes
are Cedar extensions to that scheme.

The general diagnosis that federal data does not reliably identify Native entities is not
ours: see **Akee, Henson, Jorgensen & Kalt (2020)**. What is offered here is a measurement
of the gap and a resolved chain, not the observation that a gap exists. **USET's *2022
Tribal Enterprise Directory*** is the regional precedent for linking tribal governments to
differently-named enterprises, covering 600-plus enterprises across 33 tribes with an 8(a)
index; this is a national, machine-readable, identifier-bearing version of the same idea.

Ownership of Alaska Native corporations follows the rule that a village *government* never
owns an ANC and an ANC never owns the village government — the two are associated because
the people are, and the association is ancestral rather than one of membership
(`docs/ANCSA_OWNERSHIP_RULING.md`). Applying it moved 322 identifiers and $24.38 billion to
the correct village corporations. Because a village corporation and a village government
share a name and a place *by statute*, matching on either is not weak evidence of ownership;
it is no evidence at all.

Dollars are `total_obligations`, the only summable money column in this file. Companion
registers: `docs/ANOMALY_REPORT.md` (the seam that requires set-aside to be filled to award
level before any share is computed) and `docs/ASSUMPTIONS_AND_LIMITATIONS.md`.
`docs/CICD_BENCHMARK.md` `UNDERCOUNT-01` uses the same award key on the wider attributed
universe and this build reproduces it to the third decimal — $140.004 billion.

**Two cuts a reader might expect and will not find here.** There is no competition
breakdown and no funding-agency breakdown. `funding_agency` in this file holds two
different vocabularies either side of the FY2016/FY2017 archive boundary, across 176,973
rows, with no authoritative code column to normalise against — any agency cut spanning that
seam would select an *era* and report it as an agency. `extent_competed` has the same
defect; a normalised column now exists (`extent_competed_normalized`, built against the
DAIMS-DEC v2.2 crosswalk) and a competition piece can be written off it, but not off the
raw column and not off the award-level tables, which copy the raw value forward.

**No figure here comes from `coverage_audit.csv`**, which was reporting zero prime rows for
FY2023–FY2026 until it was rebuilt on 2026-08-26.

*Refresh trigger: the next prime pull. The ranking's composition is stable; the FY2026 row
and the tier-A total both only ever grow.*
