# Tribal tax bases — build log

*Built 2026-08-07 by `code/108_build_tribal_tax_bases.py`. Spec:
`docs/TRIBAL_TAX_DECOMPOSITION.md`. Output: `data/clean/tribal_tax_bases.csv`
(72 rows), `review/tribal_tax_unresolved_2026-08-07.csv` (3 rows), raw under
`data/raw/external/tribal_tax/` with `_SOURCE_MANIFEST.csv` and md5s (16 files,
all HTTP 200).*

---

## The headline finding, and it is about the record, not about us

**Almost every state that taxes tribal fuel and tobacco publishes the
AGREEMENT per tribe and the MONEY only in total.** Fifty-six of 72 rows are
per-tribe agreement rows carrying no amount; fourteen are amounts that the
publishing state does not disaggregate. That is not thin coverage of a rich
record — it is complete coverage of a record that stops where it stops.

Washington states the reason in the report itself, and the sentence is quoted
onto all 25 of its fuel rows:

> "Information from the tribe or tribal retailers received by the state or open
> to state review under the terms of an agreement are deemed to be personal
> information and exempt from public inspection and copying."

So Washington **holds** per-tribe gallons and refunds and **may not publish
them**. A coverage table that shows Washington as a gap and a state nobody
checked as a gap is describing two completely different facts.

---

## What each state publishes

| State | Document retrieved | Per-tribe detail? | Amounts? | Rows | What it gives |
|---|---|---|---|---|---|
| **WA** | DOL *2024 Tribal Fuel Tax Agreement Report*; DOR *Tribal Retail Sales Tax Compact Revenue Sharing*; RCW 82.38.030 | **Yes, roster** (25 tribes, 23 × 75/25 + 2 per-capita) | **Aggregate only** — per-tribe withheld by statute | 29 | the fullest fuel-agreement roster in the country, the 75/25 rate, CY2023 refund $68.4M and state-retained $22.8M, and the one derived volume in the dataset |
| **NM** | TRD *Cigarette Tax Credit Stamp Listing* | **Yes, roster** (21 tribes, pueblos and nations) | No | 21 | which tribes levy a **qualifying tribal cigarette tax** under Section 7-12-2 NMSA 1978 — i.e. which tribes tax tobacco themselves |
| **MI** | Treasury per-tribe *Tax Agreement* pages | **Yes, roster** (10 tribes) with every amendment and its effective date | No | 10 | the citable instrument per tribe; Michigan publishes the agreements, not the money under them |
| **MT** | DOR *Biennial Report 2022–2024*, Other Taxes chapter | No | **Yes, aggregate**, FY2020–FY2024 for two taxes | 10 | cigarette tax revenue shared with tribes fell $3.58M → $2.66M; tobacco products tax share fell $677K → $569K. Both columns checked against the printed total |
| **OK** | OTC *FY2025 Revenue & Apportionment Report* | No | **Yes, aggregate**, FY2024–FY2025 | 2 | "To Participating Tribes" — $26,120,361.46 (FY2025), $25,723,595.89 (FY2024) |

### States probed in this pass that yielded no publishable row

Recorded so that a later pass does not re-walk them, and so that "no rows" is
never mistaken for "not looked at".

| State | What was swept | Result |
|---|---|---|
| **MN** | `revenue.state.mn.us` sitemap, 2,698 URLs | `/tribal-government-agreements`, `/tribal-nation-aid`, `/american-indian-exemption` exist as **policy pages with no distribution file**. Consistent with `docs/STATE_GAMING_FRAMEWORKS.md`: Minnesota's blank is structural, not unworked. Worth one more pass on the agreements page |
| **WI** | `revenue.wi.gov` sitemap, 2,071 URLs; Tribes section | Refund **mechanism** confirmed — forms CT-001 (cigarette tax refund claim for Native American tribes) and TT-001 (tobacco products), plus Publication 405. **No refund amounts published on these pages.** The likeliest home for amounts is the DOR annual report / Legislative Fiscal Bureau excise paper — not yet retrieved |
| **AZ** | `azdor.gov` sitemap, 478 URLs | **Zero** tribal/Indian/Native URLs. Notable given Arizona's reporting load in the gaming work |
| **ID** | `tax.idaho.gov` WP sitemaps | One page: consumer fuels, *"buying from an Idaho Indian tribe member"*. Rule page, no distributions |
| **NV** | `tax.nv.gov` WP sitemaps | No tribal pages in the page sitemap |
| **NY** | `www.tax.ny.gov/sitemap.xml` | Top-level index only (48 URLs); the Native American cigarette stamp / coupon material is not reachable from it. Needs a different entry point |
| **KS** | `www.ksrevenue.gov/sitemap.xml` | Returns 200 with **zero `<loc>` entries** — the sitemap is empty, not the site |
| **OR** | `www.oregon.gov/sitemap.xml` | 404. Oregon fuel tax agreements sit with ODOT, not the revenue department |
| **ND** *(not on the list; found while sweeping)* | `tax.nd.gov` sitemap | `/native-american` plus a news item, *"North Dakota Legislature passes state-tribal revenue share agreement"*. **This is the highest-value unworked target in the country**: oil and gas gross production tax sharing on Fort Berthold is the largest per-tribe severance flow anywhere, and North Dakota reports it monthly |

---

## Refusals, and why each one is a refusal rather than a row

**Oklahoma — three tribal lines identified and not published.** Script 94
recorded that `pdftotext -layout` shifts a label column against its numbers.
This report is a live case. Read from the text layer it says $70,341,313.12 of
diesel excise went "To Participating Tribes"; read by word position the
apportionment total across all funds is $26,120,361.46. The text-layer figure
is an artefact. So:

- *SOURCE OF REVENUE* (alphabetical, two label columns and two value columns) —
  **refused.** A baseline groups a label from the left column with values
  belonging to the right column's row; it reads "State / Tribal Compact Stamps
  $63,889,121.46" and "Use Tax $63,889,121.46" off the same numbers.
- *"Where it came from / Where it went"* fund pages — **refused.** Two
  independent two-column tables share a baseline, so a tribal figure cannot be
  tied to the tax named at the top of the page.
- *1695T Tribal Trust Account* and *Tribal License Plate* — **refused.** Values
  are not adjacent to the label, and the license-plate line does not state the
  direction of the flow. Rule 4 forbids publishing a bare tribal number whose
  direction is unstated.

Only the *Apportionment of Statutory Revenues* table survives, because there the
label sits alone on its baseline and the two fiscal-year values sit alone on the
next one — checkable, and checked.

**Montana — footing check.** Both tables are published only because
`total − tribal = remainder` holds on all five fiscal years in each. A column
that does not foot would have been reported here and left out of the CSV.

**Michigan disagrees with itself, and the disagreement is recorded rather than
smoothed over.** Four of the ten agreement pages spell the tribe more than one
way across the state's own instruments. The Sixth Amendment for Little Traverse
Bay Bands of Odawa Indians drops "Little" from a name the five earlier
instruments spell in full; Nottawaseppi appears as both "Potawatomi" and
"Pottawatomi"; Sault Ste. Marie appears with and without the full stop. Taking
the newest or the first title would have carried the state's typo into entity
resolution. The spelling every instrument agrees on wins, and the disagreement
is logged.

---

## The one derived base, and why there is only one

```
$22,800,000 retained / 0.25          = $91,200,000 of state fuel tax
$91,200,000 / $0.494 per gallon      = 184,615,385 GALLONS
```

Gallons of fuel delivered to tribally licensed retail stations under
Washington's 75/25 agreements, calendar 2023. Both inputs are quoted: the
retained amount from the DOL report, the rate from RCW 82.38.030 — which
publishes increments rather than a total, so the row carries the subsections in
force during 2023 and states that they sum to 49.4 cents.

**It is a volume. It is not a dollar figure and must never be read as one.**

The $68.4M refund figure sitting beside it is **not** divisible the same way,
and the reason is the whole of rule 1. That figure pools the two per-capita
agreements, whose amount comes from a population formula — the report calls its
own output "an estimate of the amount of fuel tax most likely paid by tribal
members" — and not from a quantity of fuel sold. Dividing it would manufacture
gallons nobody sold. `derive_base()` refuses `per_capita_formula` and
`share_of_state_tax_collected` in code, so this is enforced rather than
remembered.

Every other amount in the dataset is a revenue **share** of somebody else's tax,
not a rate levied on a quantity, so no volume comes out of it.

---

## Netting readiness: zero tribes, and that is the honest number

Only a **per-tribe amount** can be netted out of a whole-tribe revenue figure.
An agreement roster row proves the agreement exists and subtracts nothing.

**No tribe in this dataset yet carries a per-tribe non-gaming tax amount**, so
no whole-tribe revenue figure can be netted down toward gaming today, and no
`BOUNDED_DERIVED_REVENUE` row exists. The bound machinery is built, tested and
idle; the missing input is per-tribe money, and the states that hold it either
withhold it by statute (WA) or have not been reached yet (ND, WI, MN).

A bound produced this way would be `bound_basis =
NON_GAMING_CATEGORIES_NETTED`, `measurement_status = BOUNDED_DERIVED_REVENUE`,
and an **upper bound, never a value** — untaxed government receipts, grants and
other enterprise income stay in the residual. **A factual bound is not a
confidence interval**; `assert_no_forecast_language()` refuses the words
"estimate", "predicted", "forecast" and "confidence interval" in any cell this
build authors, and lets them through only inside a verbatim source quote.

---

## Entity resolution

53 spine entities reached; 3 records refused and staged for a ruling in
`review/tribal_tax_unresolved_2026-08-07.csv`. All three refusals are the
guards working, not resolver defects:

| Record | State | Refused because |
|---|---|---|
| Fort Sill Apache Tribe | NM | **state disagreement** — the spine places it in OK. Fort Sill Apache is Oklahoma-recognised and holds land in New Mexico; the resolver may not decide that, so a human does |
| Indian Pueblo Cultural Center (19 New Mexico Pueblos) | NM | no spine match. It is an intertribal organisation standing in for 19 pueblos, **not a tribe**, and inventing a tribal owner for it is exactly the containment defect |
| Little River Band of Ottawa Indians | MI | **name-trap-only** — the spine's short name reduces to `{little, river}`, both `NAME_TRAPS` tokens. The match is very likely right; precision over recall says a human confirms it |

Guards applied, and only the ones AGENTS.md records as having survived
measurement: the record must be at least as specific as the entity, the spine
row's state must agree with the source's, a match resting only on trap tokens is
refused, and anything name-only goes to `review/` at Tier B.

---

## Next targets, in value order

1. **North Dakota** — oil and gas gross production tax sharing, Fort Berthold.
   Monthly, per-tribe, and the largest severance flow to any tribe in the
   country. `SEVERANCE` is presently an empty tax type in this dataset.
2. **Wisconsin** — the refund forms prove the mechanism; find the amounts in the
   DOR annual report or the Legislative Fiscal Bureau excise paper.
3. **Transient occupancy** — presently **zero rows**. Elijah's second example is
   the least-served category here and nothing retrieved in this pass carried a
   lodging figure.
4. **Minnesota** — one more pass on `/tribal-government-agreements` before
   recording the state as structurally blank.
5. **New York** — the Native American cigarette stamp material is not reachable
   from the site's top-level sitemap and needs a different entry point.
