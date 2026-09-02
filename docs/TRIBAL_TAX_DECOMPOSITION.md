# Isolating gaming revenue by subtracting what is separately taxed

*Elijah, 2026-08-07:*

> "i know for a fact that tribes have to pay gas excise tax and all those sin
> taxes and prob occupancy taxes too (the former had the Colville cig case, the
> latter was a Navajo case) which are findable, so we can isolate the gaming
> revenue further i imagine."

This solves a problem the other derivation methods hit and could not get past.

---

## The problem it solves

Three methods now recover a revenue base by division:

```
compact payment / stated rate            = revenue base
charitable giving / stated % commitment  = revenue base
tribe-level figure, 1 property           = property revenue
```

**All three break when the base is WHOLE-TRIBE revenue** rather than gaming
revenue, because a tribe's total includes fuel stations, smoke shops, hotels,
retail and government receipts. `may_attribute_to_single_property()` refuses
exactly this case — `base_is_gaming_revenue=False` returns False — and that
refusal currently ends the analysis.

**Subtraction reopens it.** Where the non-gaming categories are *separately
taxed and separately reported*, they can be netted out:

```
gaming revenue  ≈  whole-tribe revenue
                   − fuel/motor-fuel excise base
                   − tobacco excise base
                   − transient occupancy / lodging base
                   − other separately-taxed categories
```

Each subtracted term is itself recoverable by the same division:
`tax remitted / statutory rate = taxable base`.

---

## Why the records exist

State–tribal **tax agreements and compacts** (distinct from gaming compacts)
govern fuel and tobacco, and they exist precisely because the tax incidence was
litigated. Elijah names the two lines of cases: the **Colville** line on
cigarette taxation, and a **Navajo** matter on the occupancy side. The doctrinal
outcome matters less here than the administrative consequence:

> **Where a tax is collected, a rate is published and a remittance is recorded.**

That means a state revenue department holds per-tribe fuel and tobacco figures
even where it holds nothing about gaming. These are typically **motor fuel tax
refunds or credits to tribes**, **cigarette stamp allocations or tax-agreement
distributions**, and **lodging/transient occupancy collections**.

*(The case names above are Elijah's recollection and are recorded as
orientation, not as citations. Any published claim must cite the retrieved
agreement or statute, not the case.)*

---

## What to build

`data/clean/tribal_tax_bases.csv` — one row per (tribe, tax type, period):

```
tax_observation_id, tribe_id, tax_type, period_start, period_end,
tax_remitted_usd, statutory_rate, derived_taxable_base_usd,
rate_source_quote, amount_source_quote, agreement_or_statute_cite,
measurement_status, bound_basis, source_url, fetched_date, tier, confidence
```

`tax_type`: `MOTOR_FUEL | TOBACCO | TRANSIENT_OCCUPANCY | ALCOHOL | RETAIL_SALES
| SEVERANCE | OTHER`.

**Sources:** state departments of revenue (tax-agreement distribution reports),
state–tribal tax compacts, legislative fiscal analyses, and tribal annual
reports where they break out enterprise lines.

---

## The four rules that keep this honest

**1. A taxable base is not revenue.** Fuel excise is levied per gallon, so the
derived base is a **volume**, not a dollar figure, unless the tax is ad valorem.
Tobacco stamps are per pack. Record what the rate is levied on and never call a
gallon count a dollar.

**2. Subtraction produces a BOUND, not a value.** The categories we can subtract
are the ones that happen to be taxed. Anything untaxed — government receipts,
grants, unrelated enterprise income — stays in the residual. So:

```
gaming revenue  ≤  whole-tribe revenue − (subtractable categories)
```

That is an **upper bound**, `bound_basis = NON_GAMING_CATEGORIES_NETTED`. It
becomes a value only if a source states that the remaining categories are
exhaustive.

**3. Periods and entities must match on both sides.** A calendar-year tax
remittance against a fiscal-year revenue figure is not a subtraction. A tribal
enterprise that remits tax under its own name is not automatically inside the
tribe's reported revenue.

**4. Never publish a tribe's tax remittance as a stand-alone "tax burden"
figure without the agreement context.** Tribal taxation is legally contested
ground, and a bare number invites a wrong reading in either direction. The
agreement or statute travels with the row.

---

## Why it is worth building on its own merits

Even where it never touches gaming, this produces something nobody has:
**a per-tribe series of fuel, tobacco and lodging economic activity**, sourced
from state revenue records. That is a measure of the non-gaming tribal economy —
the part of Indian Country's commerce that gaming coverage systematically
ignores.

And it composes with everything else: `whole_tribe_revenue − tax_derived_bases`
narrows the gaming figure, while the tax bases themselves stand as their own
dataset.


---

## CORRECTION AND EXTENSION — 2026-08-07, after the North Dakota build

**Two statements in the tribal-tax build log are now false and are corrected
here.**

**1. "Netting readiness: zero tribes" — superseded.** North Dakota publishes
per-tribe non-gaming tax money for **four** tribes: Tribal Highway (motor fuel)
back to 2005 (902 payments, $53.4M), Tribal Cigarette (Standing Rock, 258
payments), Tribal Sales Tax and Tribal Alcohol. Retained raw and queued; the
earlier "no tribe carries a per-tribe non-gaming amount" no longer holds.

**2. A blended formula CAN be decomposed — if the publisher prints both legs.**
The post-2019 North Dakota split cannot be resolved by well vintage (per-well
tax data is confidential, so vintage weights are unreachable *in principle*).
But the Legislative Council publishes monthly **collections on the Fort
Berthold Reservation** AND **the amount allocated to the Three Affiliated
Tribes** — so the effective share is **measured, not derived**:

| Biennium | Measured tribal share |
|---|---:|
| 2015-17, 2017-19 | **50.00%** |
| 2019-21 | 51.20% |
| 2021-23 | 53.17% |
| 2023-25 | 54.14% |
| 2025-27 to date | **55.48%** |

**The exact 50.00% under the uniform 2013 regime is what validates the two legs
as the same basis.** Neither figure was adjusted to make it land.

It also yields a floor on the vintage mix without needing the vintages:
`post_2019_share >= (observed - 0.50) / 0.30`.

**The rule this generalises to: before trying to invert a blended rate, check
whether the publisher prints the denominator.** A measured ratio beats a
derived one, and it sidesteps every inversion failure mode below.

---

## A FOURTH WAY RATE INVERSION FAILS

Recorded in `AGENTS.md` alongside the other three:

1. **Marginal base** — "in excess of 350 devices" (California, 795 rows killed)
2. **Graduated schedule read as flat** — New Mexico's spelled-out brackets;
   Florida's 10% bottom tier
3. **Receipts lag obligations** — Florida true-ups arrive the following fiscal
   year, falsifying the bound with the publisher's own figures
4. **MIXED UNITS IN ONE FIGURE** — North Dakota's gross production tax pools an
   **ad valorem oil tax with a per-mcf gas tax**. One reported number, two
   units, **not invertible at all**. No amount of rate research fixes it; the
   figure simply is not a single base times a single rate.

North Dakota adds a fifth complication short of failure: the oil extraction
rate on the reservation is **state-contingent** (5% or 6% by trigger price),
and the 2023 session kept that trigger *only* for reservation and straddle
wells. Every month therefore carries a range `[collections/0.06,
collections/0.05]` rather than a value.

And the deepest blocker is not arithmetic: **the tribal-state agreement is not
published**, and NDCC 57-51.2-02(3)/(4) permit it to set the trust-land rate
below cap and re-enable exemptions. The rate on paper may not be the rate in
force.
