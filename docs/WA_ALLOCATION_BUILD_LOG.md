# Washington machine allocation and inter-tribal transfer ledger — build log

*Built 2026-08-07 by `code/104_build_wa_allocations.py`. Every number below is
lifted from an instrument or a regulator page held under
`data/raw/external/wa_gaming/` with an md5 in `_SOURCE_MANIFEST.csv`.*

---

## What Washington actually does

Washington does not cap machines per casino. It gives **every** federally
recognised tribe in the state a per-tribe entitlement of Tribal Lottery System
Player Terminals — an **Allocation** — and lets that tribe operate the terminals
or transfer the right to operate them to another Washington tribe.

> "**12.1 Allocation.** The Tribe shall be entitled to an allocation of, and may
> operate or transfer the ability to operate, up to 975 Player Terminals
> ('Allocation')."
> — Appendix X2 §12.1, Shoalwater Bay first amendment, approved 2007-05-31

The Gambling Commission describes the same thing in its own words:

> "Each tribe could operate 1,500 player terminals per facility **by leasing
> machine rights from other tribes**."
> — WSGC, *Tribal Lottery System*, on Appendix X (1998)

So a Washington tribe with no casino still holds a tradeable asset, and a
Washington tribe with a large casino is operating machines it does not own. Both
sides of that are Native-to-Native commercial relationships that no federal
dataset can see.

---

## The allocation ledger — `data/clean/wa_machine_allocations.csv`

**75 rows · 29 tribes · 1999-01-28 to open.** Every row is
`measurement_type = AUTHORIZED_MAXIMUM`, and the build asserts
`may_promote(AUTHORIZED_MAXIMUM, ACTIVE_FLOOR_COUNT) is False` before writing.
A held allocation is an entitlement. It is not a machine on a floor and it never
becomes one by relabelling.

### The four regimes, all read from the instruments

| Regime | Own allocation | Instrument |
|---|---|---|
| Appendix X (1998) | **425** first year, **675** after a compliance review | §12.1 initial, §12.2 step-up |
| Appendix Spokane (2007) | **900** | §5 — Spokane only |
| Appendix X2 (2007) | **975** | §12.1 |
| Appendix X2 Addendum (2015–) | **1,075** | Addendum §2 amending §12.1 |
| Appendix Colville (2003) | **675 Electronic Gaming Devices** | §2 — Colville only, a different device class |

**All 29 tribes currently sit at 1,075 player terminals.**
Statewide authorised total: **29 × 1,075 = 31,175 player terminals.**

That figure is the hard ceiling on Class III player terminals in Washington.
Operating limits are far higher — 3,000 per facility since the 2021 Appendix E
amendments, and a Total Operating Ceiling of 3,000 per tribe, or 4,000 for
Muckleshoot, Tulalip and Puyallup — but **a ceiling can only be filled by
acquiring another tribe's allocation**, so no terminal can enter the state
except through the 31,175.

> "Subject to Section 12.4 below, the Tribe may operate no more than 2,500
> Player Terminals per facility ('Facility Limit'), and no more than a combined
> Player Terminal total ('Total Operating Ceiling') of 3,000 Player Terminals.
> It is also agreed that upon the effective date of this Appendix, the Total
> Operating Ceiling for the Muckleshoot Tribe, Tulalip Tribes, and Puyallup
> Tribe shall be 3,500 for each of those three tribes until the third
> anniversary of the effective date of this Appendix, at which time it shall
> increase to 4,000."
> — Appendix X2 §12.2.1

Subtracting gives the per-tribe *demand* for other tribes' allocations exactly:
**1,925** terminals for a tribe at the 3,000 ceiling, **2,925** for each of
Muckleshoot, Tulalip and Puyallup. That is arithmetic on two instrument
numbers, not an estimate, and it is not a claim that any tribe operates to its
ceiling.

### The escalator, recorded as a rule and not as a number

The 2015 Addendum lets each tribe add 50 terminals when the statewide lease
market runs dry, and extends any such increase to every other compacted tribe:

> "3.1 The Tribe's Allocation of Player Terminals as set forth in Appendix X2
> may increase by 50 Player Terminals upon meeting the procedures and conditions
> set forth in this Addendum. 3.2 The Tribe shall provide the State Gaming
> Agency with written notice, along with Certification from an Independent
> Accounting Firm, that there are **500 or fewer Player Terminals Available for
> Lease**…"

> "…the Tribe shall be automatically entitled to the same Allocation increase
> authorized to that other Washington tribe."

Present in 32 of 181 Washington version documents. **No +50 increment is written
into the data**, because nothing published says one was ever triggered. The
rule is recorded; the count is not invented. If WSGC ever publishes a triggered
increase, it lands as a new row with a new effective date — never as an edit to
an existing one.

### Coverage gap, stated rather than filled

Six tribes — Chehalis, Jamestown, Nisqually, Skokomish, Stillaguamish,
Suquamish — have **no 975-era row**. Their compact history in this file goes
675 → 1,075. The cause is documentary, not substantive: the 2007 Appendix X2
amendment we hold for each of them is the ~3,200-character Secretarial approval
letter, not the appendix text. WSGC's own compact page for each shows an
Appendix X2 signed 2007-03-30. **The regime applied to them; the instrument
stating it is not in our corpus, so no row was written.** 22 of 181 Washington
version documents are approval-letter-only in this way.

---

## The transfer ledger — `data/clean/wa_machine_transfers.csv`

**Schema written. Zero rows. That is the finding, and here is the evidence for
it.**

Modelled on `native_passthrough.csv`: a directed edge between two resolved
Native entities, `from_tribe_id` → `to_tribe_id`, never collapsed into the
receiving tribe's count. The build scans all 181 Washington instrument texts for
an executed transfer naming two parties. **Zero candidates.**

Three separate provisions explain why, and each is quoted from the instruments.

**1. Appendix D is a blank form.** Every Washington compact appends a *Class III
Gaming Station Transfer Agreement* with the party names, the count and the term
left as underscores. Present as a form in 9 version documents; executed
instances appear in none.

> "Transfer of Class III Gaming Station authorization from another Tribe shall
> be effectuated through the use of a 'Class III Gaming Station Transfer
> Agreement' **substantially in the form appended hereto as Appendix D** of this
> Compact."

**2. The terminal-transfer market is run by the tribes, and the State says so.**

> "The State shall have **no responsibility whatsoever** with respect to the
> plan, including but not limited to responsibility for providing notices to
> tribes, determining if the plan has been agreed to properly, monitoring its
> rules or implementation, or any other aspect of such plan, the entire
> responsibility for which shall be upon the Eligible Tribes."
> — Appendix X2 §12.2.2, in 53 version documents

**3. The price is placed, by design, in a document that is never filed.**

> "Transferor and Transferee **may enter into separate agreements** related to
> the utilization of Class III Gaming Stations transferred hereby, PROVIDED,
> that the terms of such separate agreements shall not affect the legal
> capabilities and authorizations for the transfer specified herein."
> — Appendix D §4, in 13 version documents

So the answer to *"is consideration ever disclosed?"* is structural, not
incidental: **the compact form separates the transfer from its price and files
only the transfer.** No amount can be disclosed because no amount is in the
instrument the State receives.

### And the State's own record got thinner over time

This is a datable narrowing that is worth its own line.

Under **Appendix X (1998)** the State received the transfer documents themselves:

> "The Tribe may not operate any Player Terminals acquired from any other
> Tribe's allocation until 30 days has elapsed following delivery to the State
> of **a complete set of the documents which govern the transfer**."
> — §12.4.3, in 26 version documents

Under **Appendix X2 (2007)** that became a count:

> "The Tribe may not utilize the ability to operate a Player Terminal that was
> allocated to, and subsequently acquired from, another tribe, until it
> completes delivery to the State of documentation confirming **the number of
> transfers** of the ability to operate such Terminals it has acquired."
> — §12.2.4, in 27 version documents

The records therefore exist — a tribe cannot switch on an acquired terminal
without filing — but since 2007 what is filed is a number, and it is filed with
the State Gaming Agency rather than published. **The route to the ledger is a
Washington Public Records Act request to WSGC, not a scrape.**

---

## What WSGC publishes, measured

Fetched 2026-08-07, one stream, lock held at `logs/_HOSTLOCK_www.wsgc.wa.gov.json`.

| Page | Present? | Carries per-tribe machine data? |
|---|---|---|
| Tribal partnerships (index) | yes | no |
| Tribal Lottery System | yes | **no** — describes allocations and leasing in prose, gives no counts |
| Tribal casino locations | yes | no — name, city, phone, sports-wagering flag |
| Tribal gaming compacts and amendments | yes | **yes, indirectly** — 29 per-tribe pages, 157 dated instruments with subjects |
| Tribal electronic table games | yes | no |
| `/about-us` | yes | no reports or statistics section at all |
| `/sitemap.xml`, `/about-us/reports`, `/about-us/publications` | **404** | — |
| `/search?keys=…` | **HTTP 500** | — |

**There is no allocation table, no transfer table, no per-tribe machine count
and no annual report anywhere on wsgc.wa.gov.** The tribal-partnerships section
carries seven pages and none of them is a data page. What the site does offer is
*Request public records*.

Two source self-disagreements, recorded rather than smoothed:

- The casino-locations page says **"23 tribes operate 29 casinos under
  compact"** and then returns **"Showing 1 - 28 of 28 results"**. Both are
  recorded; neither was adjusted to meet the other.
- WSGC's own tribe filter spells Quinault **"Quinalt"**. The build bridges it on
  a five-character prefix and logs the bridge in
  `logs/wa_allocations_summary_2026-08-07.json` so the typo is visible rather
  than silently repaired.

A CDX sweep of archived WSGC Tribal Lottery System fact sheets is queued behind
the live `web.archive.org` lock (`logs/_HOSTLOCK_web.archive.org.json`) rather
than run as a second poller.

---

## Tribes holding an allocation and operating no casino

**Six of twenty-nine**, and they are the point of the dataset rather than an
error in it:

**Hoh · Lower Elwha · Makah · Quileute · Samish · Sauk-Suiattle**

Each holds 1,075 player terminals of Class III entitlement and appears on no
WSGC compacted-casino listing. Samish is the cleanest case in the file: original
compact 2000-04-18, Appendix X2 2007-03-30, Appendix X2 Addendum 2015-04-08, and
no casino.

**Absence from that list is a property of the list.** WSGC's page covers
compacted Class III casinos only. Cedar's own property universe holds a WA
property for 26 of the 29 — Makah Tribal Bingo, the Elwha River Casino and a
Sauk-Suiattle record are Class II or historical and so are invisible to WSGC's
Class III filter. Only **Hoh, Quileute and Samish** have no gaming property in
Cedar's universe at all. The two counts measure different things and both are
true.

---

## Resolution

All 29 tribes resolved through `resolve_entity` (`code/33_apply_party_rulings.py`).
`review/wa_allocation_unresolved_2026-08-07.csv` is empty.

Three guards were applied on top of the shared resolver, sized to the 15
Washington rows in `review/spine_short_name_collisions_2026-08-07.csv`:

1. **Government class only.** A compact party is a federally recognised tribe by
   definition. This alone disposes of all five HIGH-risk Washington collisions —
   Chehalis Tribal Loan Fund, Jamestown S'Klallam Tribal Capital, Lummi Nation
   School, Muckleshoot Tribal School, Quileute Tribal School — none of which can
   sign a compact.
2. **Record at least as specific as the entity.** Containment is accepted only
   when the entity's core tokens are a subset of the record's. *Lower Elwha
   Klallam Tribe* → spine *Lower Elwha* passes; the reverse direction, which
   booked $2.8B onto a school on 2026-08-06, cannot.
3. **`NAME_TRAPS`.** A match whose entire token overlap is trap words never
   links.

---

## Two extraction defects found and fixed during the build

Recorded because both would have shipped plausible wrong numbers.

**A restated compact reprints its own history.** The 2022 Chehalis instrument
contains Appendix X's 425-terminal Initial Allocation *and* Appendix X2's 1,075,
side by side. Reading both as facts about 2022 put six tribes back on a 1998
number and understated the statewide total by 3,900 terminals. Appendix X2 §12.1
states the Allocation; Appendix X survives in the document only as the regime
under which pre-X2 terminals may keep operating (Appendix X2 §1). The build now
takes the highest-precedence clause present in a document and records the
superseded one in the citation.

**`Te[rn]{2}inals` cannot match "Terminals".** The character class was written
for the OCR variants *Tenninals* and *Te1minals* and excluded a plain `rm`,
which silently dropped the Appendix X compliance step-up from 20 of 21
documents — every Appendix X tribe read 425 instead of 425 + 250 = 675.

---

## Against NIGC

NIGC's Portland region (AK, ID, OR, WA) reports **58 operations and $4.94B gross
gaming revenue in FY2025** and **35 Washington gaming locations** on its facility
roster, against WSGC's 29 compacted Class III casinos — the gap is Class II,
which NIGC covers and a Class III compact list does not.

**NIGC publishes no device counts at any level.** There is no federal
counterpart to 31,175 authorised terminals, and no federal source from which the
number could be derived. That is the whole argument for this file.

---

## Files

```
code/104_build_wa_allocations.py
data/clean/wa_machine_allocations.csv          75 rows, 29 tribes
data/clean/wa_machine_transfers.csv            schema, 0 rows
data/raw/external/wa_gaming/                   45 files, md5 in _SOURCE_MANIFEST.csv
review/wa_allocation_unresolved_2026-08-07.csv 0 rows
logs/wa_allocations_summary_2026-08-07.json
logs/wa_rule_quotes_2026-08-07.json            one verbatim quote per transfer rule
docs/WA_ALLOCATION_BUILD_LOG.md
```

Codebook: 34 variable rows added to `data/clean/codebook_master.csv` under
`07e_wa_machine_allocations` and `07e_wa_machine_transfers`. Variables only.

**`codebook_master.csv` is being written by several agents at once.** During
this build it was rewritten twice by other scripts and this build's 34 rows were
dropped both times. The stage now backs the file up to
`codebook_master.csv.bak_2026-08-07_pre104`, re-reads immediately before
writing, and re-adds any of its rows that have gone missing, so a re-run of
`code/104_build_wa_allocations.py` restores them. Nothing written by another
agent was lost: the pre/post key diff is checked and was empty.

`code/62_no_regression_check.py` fails on `codebook_undocumented_public = 10`
both **before and after** this build. All ten rows belong to other datasets —
nine `06_nonprofit` Schedule C / 990-PF variables and `12_resources.source_system`
— and none was touched here. All 34 rows added by this build carry descriptions.
