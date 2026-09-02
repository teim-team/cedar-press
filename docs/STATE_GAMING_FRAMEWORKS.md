# State gaming frameworks are not variations on one model

*Elijah, 2026-08-07. Domain context that changes what data exists in each state,
and therefore what we can pull. Confirmed against the parsed compacts where
noted.*

> "washington has a slot allowance per tribe and tribes can give them to other
> tribes, so not every tribe in WA has a casino but they can give their slot to
> another more successful tribe … shakopee has a unique compact where they don't
> have revenue sharing, and CA has revenue sharing among all tribes. every state
> has a different sort of framework."

This is the single most useful framing anyone has given this dataset. **The
framework determines what records exist.** A state that shares revenue must
track distributions; a state that allocates machines must track allocations; a
state that does neither generates neither.

---

## WASHINGTON — a transferable machine allocation, and therefore a market

**CONFIRMED in the compacts.** 98 of Washington's 410 parsed terms mention
allocation, transfer or lease. The clause language is explicit:

> "SECTION 12. TRIBAL LOTTERY SYSTEM PLAYER TERMINAL ACQUISITION AND OPERATION
> — 12.1 Allocation. The Tribe shall be entitled to an allocation of, and may
> operate…"

> "Appendix D, governing **gaming machine transfers between tribes**"

**Why this matters more than a slot count.** Every federally recognised tribe in
Washington gets an allocation whether or not it operates a casino. A tribe
without a casino can transfer its allocation to one that has demand. So:

1. **Machine counts are administratively necessary.** The state must know who
   holds how many, or the cap is unenforceable. That is a stronger guarantee of
   data existing than any voluntary reporting regime.
2. **Each transfer is a Native-to-Native commercial relationship** — recurring
   revenue for the transferring tribe, capacity for the receiving one. This is
   the same shape as ANCSA §7(i) revenue sharing: a flow **between** Native
   entities that federal data cannot see at all.
3. **It explains apparent anomalies.** A tribe with no casino and gaming-derived
   income is not a data error in Washington; it is the system working.

**What to pull:** the Washington State Gambling Commission's allocation and
transfer records, and Appendix D agreements. This should be modelled as an
`event` with two Native parties and a direction — reuse the
`native_passthrough` pattern, not a property attribute.

**A machine allocation is `AUTHORIZED_MAXIMUM`, never `ACTIVE_FLOOR_COUNT`** —
a tribe may hold an allocation it does not operate. That is the whole point of
the transfer market.

---

## CALIFORNIA — revenue sharing across all tribes

Gaming tribes fund the **Revenue Sharing Trust Fund**, which pays non-gaming and
limited-gaming tribes. Plus the **Special Distribution Fund** for local
government impact mitigation.

**So California publishes tribe-identified money for tribes that operate no
casino.** 81 tribes carry compact reporting obligations there — the most of any
state — and 1,221 obligations total.

Caution already measured: California's typical revenue base is *"the operation
of Gaming Devices"*, which is **tribe-level, not per-facility**. 44 rows were
demoted for exactly this. An RSTF or SDF payment is a compact-mandated transfer,
not property revenue.

---

## MINNESOTA — no revenue sharing, and the data reflects it

**CONFIRMED by absence.** Minnesota returned **zero** structured revenue terms
from the compact parse, against 43 reporting obligations.

Minnesota's compacts are perpetual and carry no revenue-sharing provision —
Shakopee Mdewakanton being the well-known case. Consequence: **there is no
payment series to pull, because there are no payments.** A blank Minnesota is
correct, not a gap, and any coverage report must say so rather than listing it
as unworked.

This is also why SMSC's giving is invisible from the funder side: no revenue
share to the state, and tribal governments are outside the 990 universe under
IRC §7871.

---

## ARIZONA — the heaviest reporting load in the country

746 obligations, **707 of them state-side** — the highest ratio anywhere — and
the highest recurrence weight. Arizona also runs a **device pool/draw system**,
so an authorised count there is a licence entitlement rather than an operating
count.

We hold 463 observations from Arizona against 746 obligations. **Under-mined
relative to what its compacts promise**, and a better target than several states
with zero coverage.

---

## The rule this yields

**Before pulling a state, read its framework.** The compact tells you what kind
of records must exist:

| Framework feature | Record it forces into existence |
|---|---|
| Revenue sharing to the state | distribution series, tribe-identified |
| Revenue sharing among tribes | transfers between Native entities |
| Transferable machine allocation | per-tribe counts **and** a transfer ledger |
| Device pool / draw | licence entitlements, not operating counts |
| No revenue sharing | **nothing — and that is the finding** |

Absence of a payment series in Minnesota and absence in a state we simply have
not checked look identical in a coverage table and are completely different
facts. `review/state_source_roadmap_2026-08-07.csv` ranks the states; this file
says what to expect when you get there.


---

## CORRECTION — 2026-08-08: digital gaming is NOT authorised through compacts

The digital build was queued behind the compact parse on the assumption that
**compacts define digital rights, so compacts must come first.** That assumption
is wrong, and the measurement is stark:

> **81 tribes hold a digital right in the compacts. 14 have an observed
> operation. The two sets intersect in ZERO tribes.**

**The states where tribal digital gaming actually happens do not authorise it
through the compact.** Michigan's 12 tribal operators run under the **Lawful
Internet Gaming Act (2019 PA 152)** — a separate state licensing regime.
Michigan's 18 compacts yield 35 revenue-share rows and **zero digital terms**.
Connecticut is the same shape.

Meanwhile Arizona's 21, Washington's 23 and New Mexico's 16 compact-authorised
tribes appear in **no tribe-identified digital revenue series anywhere**.

The single tribe in both sets is there by contradiction: **Pokagon** is a
licensed Michigan iGaming operator (launched 2021-02-15) whose only compact
digital term is its **Indiana** compact reading
`internet_wagering_authorized = prohibited`. Both are recorded; neither is
reconciled away.

**So the framework rule needs a fourth row:**

| Framework feature | Record it forces into existence |
|---|---|
| Revenue sharing to the state | distribution series, tribe-identified |
| Revenue sharing among tribes | transfers between Native entities |
| Transferable machine allocation | per-tribe counts **and** a transfer ledger |
| **Separate digital licensing statute** | **monthly per-operator revenue — and the compact says nothing** |

**Where to look for tribal digital gaming is the state's iGaming statute and
its regulator, not the compact.** Measured monthly series exist in:

- **Michigan** — per-operator iGaming + internet sports betting, Jan 2022–Jun
  2026. Tribal cumulative **$9.95bn handle, $5.85bn GGR, $1.04bn state
  payments**. 270 month×metric footings pass, 0 fail.
- **Connecticut** — online casino, online sports, retail sports, fantasy, Oct
  2021–Jun 2026. Tribal **$7.65bn sports handle, $3.92bn GGR, $448m to the
  State**.
- **Arizona** publishes by **brand**, not by tribe — 13 brands unattributable.

**A units trap worth carrying:** Connecticut labels two different measures
`wagers` — sports **handle** ($7.65bn) and online-casino **coin-in** ($72.1bn).
They are stored as `HANDLE` and `AMOUNT_WAGERED` precisely so nothing can sum
them.

**And a second-order finding:** grouping on the *provider* rather than the
operator surfaced **18 platform relationships that have already ended** —
Hannahville TwinSpires→Hard Rock, Sault Ste. Marie Wynn→Caesars, Lac Vieux
PointsBet→Fanatics and others. Those vendor changes appear in no property file,
and four are independently corroborated by NIGC declination letters. Every
`cessation_date` is blank because MGCB publishes an **absence**, not an end
date.
