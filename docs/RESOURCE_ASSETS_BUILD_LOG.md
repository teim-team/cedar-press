# The natural resource ASSET layer — build log

*Built 2026-08-12 by `code/130_build_resource_assets.py`. Pairs with
`docs/RESOURCE_LEDGER_BUILD_LOG.md` (ONRR/ND/UT/MT), `docs/RESOURCE_LEDGER_STATES_LOG.md`
(the state expansion) and `docs/RESOURCE_RECIPIENT_SIDE_LOG.md` (ANCSA §7(i)).*

`data/clean/resource_assets.csv` had **0 rows**. It now has **35**, carrying
**41 party links** across **16 distinct Native entities**, every row with a
verbatim quote from a retrieved document and a machine-checked provenance.

**Built:** 35 assets · 30 tier A, 5 tier B · 0 refused at the gate ·
4 source systems · 18 source × attribute coverage findings.

---

## First, the defect that made this file empty

`resource_assets.csv` was not empty because nobody built it. It was empty
because it was being **erased**.

Script 83 ended with

```python
assets = build_assets() if do_all else []
write_csv(CLEAN / "resource_assets.csv", assets, ASSET_FIELDS)
```

The write sat **outside** the `do_all` branch. On any run that was not a full
rebuild — `--onrr`, `--states`, `--more-states` — `assets` is `[]`, so the file
was truncated to its header. The second-wave state expansion ran
`--more-states`, and that is almost certainly what zeroed it.

This is the failure shape AGENTS.md already names twice: *the file still looks
healthy afterwards, just smaller.* Nothing errors, nothing warns, and a
0-row file reads as unfinished work rather than as deleted work.

**Fixed.** Script 83 now writes that file only on a full rebuild that actually
produced rows, and **refuses outright** if the published file carries any row it
did not write — the same guard `--all` already applies to the revenue ledger:

```
REFUSING to write resource_assets.csv: it carries 35 row(s) this script did not
write, and rewriting from raw would delete them
```

---

## The gate, and why the quotes are trustworthy

Every declared fact names a local document and an **anchor** regex. The script
then:

1. whitespace-normalises the document and splits it into sentences;
2. requires the anchor to match **exactly one** sentence in **exactly one**
   candidate document — zero is a missing fact, more than one is an ambiguous
   one, and **both refuse**;
3. requires every declared number to appear **literally** in that sentence;
4. stores **the matched sentence itself** as `evidence_quote`.

Point 4 is the important one. The quote is verbatim **by construction** rather
than by transcription, so the class of error script 84 caught — a figure read
correctly, attached to a quote that does not literally exist — cannot occur
here at all.

**The gate refused 16 facts on the first run and every refusal was real:**

| Refusal | Cause |
|---|---|
| 13 × `declared_number_absent_from_quote` | I declared `1598246`; Ahtna prints `1,598,246`. A number that does not appear in its own quote is not a quoted number. |
| 2 × `anchor_matched_2_documents` | `2025__Calista*` matches two portal uploads of one report; `2021__NANA*` matches the annual report **and** the annual meeting minutes. |
| 2 × `anchor_ambiguous` | Koniag prints its acreage in both an audited note and a summary line; Chugach describes its carbon project twice. Both were re-anchored on the audited/definite sentence. |

Final state: **35 declared, 35 verified, 0 refused.** Two consecutive runs
produce a **byte-identical** file.

---

## Ownership and beneficial interest are two columns, because they are two facts

This is the requirement that shaped the schema. Four columns carry it:

| Column | Answers |
|---|---|
| `legal_title_holder` | who holds **title** |
| `beneficial_interest_class` | who the property is held **for** |
| `ownership_basis` | the sentence-level reason, in the row |
| `land_status` | controlled vocabulary, `not_stated` always available |

The distribution is itself a finding:

```
land_status                 ancsa_fee 30 · tribal_trust 4 · not_stated 1
beneficial_interest_class   anc_shareholder 30 · tribal_government 2 ·
                            osage_headright_holder 1 ·
                            mixed_tribal_and_allottee 1 · not_stated 1
```

**30 of 35 assets are ANCSA fee, not trust.** An ANCSA corporation owns its
estate in **fee**, for **shareholders**. It is not held by the United States, it
is not trust land, and it is not owned by a tribal government. Writing
"tribally owned" across these rows would be wrong 30 times.

### The Osage estate is the case the columns exist for

`legal_title_holder` = *United States, in trust; leasing administered by the BIA
Osage Agency.* `beneficial_interest_class` = **`osage_headright_holder`**, not
the tribal government — because the Osage Nation's own auditor says so:

> "The distribution of mineral royalty income to entitled mineral royalty
> income owners is administered by the Bureau of Indian Affairs; **these
> distributions are not received by the Nation and are not reflected in the
> accompanying financial statements.**"

So the Nation is attached to that asset as `reserved_mineral_estate_holder` —
the 1906 Act reserved the estate to it undivided — and **not** as the recipient
of its income. Those are different facts and the row keeps them apart.

### The same trap in miniature, caught inside the Osage rows

The first pass gave the Osage Agency's **135,000 acres of surface trust and
restricted land** the same `beneficial_interest_class` and the same
`PUBLISHES` coverage as the mineral estate, because both came from one
sentence.

**That is wrong, and the 1906 Act is why.** It severed surface from minerals:
the minerals stayed undivided with the Nation, the **surface was allotted**. So
those acres are held for the Nation *and* for individual Osage allottees
together — `mixed_tribal_and_allottee` — and the Osage Minerals Council
publishes nothing whatever about them. The surface tract now carries
`NOT_FOUND`, and **no owner party link is written for it**, because naming the
Nation as its owner would assert an exclusivity the source does not support.

---

## An asset is not revenue, and neither was derived from the other

No asset row here exists because a revenue row exists, and **no revenue row was
written, edited, or recomputed.** `resource_revenue.csv` is byte-untouched at
10,482 rows; `resource_parties.csv` was **appended** to, its 1,395 pre-existing
links carried through unchanged.

Where an asset can be tied to a published revenue event, the tie is a
**proposal in `review/`** with its own basis column, never a merge:

`review/resource_asset_revenue_linkage_proposals_2026-08-12.csv` — **181
proposals**, all `PROPOSED_AWAITING_RULING`.

- **174** link the Osage Mineral Estate to the `RRE-OK-*` rows. Basis: the
  Osage Minerals Council publishes both, and the revenue *is* that estate's.
  **No payer is proposed** — the estate's lessees are not named in the source,
  and 106 of those rows are a **per-headright rate**, which is a rate and not a
  payment.
- **7** link Red Dog Mine to NANA's `IN_MINE_ROYALTY` rows, with a proposed
  payer of **Teck Alaska Incorporated** — a non-Native counterparty, deliberately
  not resolved to the spine.

### The seventh proposal is graded differently, on purpose

Six of the seven NANA rows carry retained evidence that **names Red Dog**. The
FY2022 row does not: it is a table reading, and the only thing tying it to Red
Dog is that Red Dog is the only producing mine NANA reports.

**That is context, not evidence.** It is graded **C** against the others' B, and
its `link_basis` begins `WEAKER LEG:` and says exactly why. Pooling all seven at
one confidence would have been the easy thing and would have hidden the one row
that needs a ruling.

*(This addresses the coordinator's note that 89% of revenue rows name no payer.
Seven of those 9,371 can be closed from an asset record. The other 9,364 are
overwhelmingly ONRR rows, where the payer is **withheld by law** — see below.
That hole is not fillable; it is a property of the source.)*

---

## Coverage: four values, never a blank

`data/clean/resource_asset_source_coverage.csv` — **18 source × attribute rows.
7 WITHHOLDS · 4 PUBLISHES · 4 NOT_CHECKED · 3 NOT_FOUND.**

A source forbidden by law to publish and a source nobody looked at are opposite
findings that look identical in an empty cell.

### What WITHHOLDS

| Source | Attribute | Evidence |
|---|---|---|
| **ONRR** | lease / agreement / well identifier on Native records | No ONRR bulk file carries a lease, agreement, tract or well column for **any** land class. Publisher: *"the federal government only releases natural resource extraction and revenue information in aggregate. Specific data on Native American revenues are confidential and proprietary."* |
| **ONRR** | state / county / FIPS on Native records | 0 of 9,238 Native rows carry geography, against 99.8% of Federal rows in the same file |
| **ONRR** | tribe or entity name | No ONRR file has a tribe-name field at all. `Osage` appears **zero** times — even though that estate has exactly one owner |
| **ND DMR** | mineral ownership on wells | No trust/fee field exists. Trust/fee is a Tax Commissioner construct and is **fractional, not binary**. `TRUST` and `INDIAN` in DMR data are lease, well and operator **names** |
| **MT BOGC** | mineral ownership on wells | Location and well identity only |
| **BIA LTRO** | allotments / individual Indian trust tracts | Not public. **The largest structural hole in this layer** |
| **Lessee SEC filings** | royalty rate on tribal coal leases | Peabody: rates *"generally based upon a percentage of the gross realization"*, no number. Westmoreland: 6.5% capped at 12.5%, no tonnage |

### What does not publish it (NOT_FOUND — swept, named)

- **BIA NIOGEMS** — the system that *does* hold Indian lease, tract, agreement
  and well ids. Internal to BIA, ~50 tribal users across 8 reservations. The
  `niogems_*` columns are **empty by construction**, so that access, if granted,
  is a merge and not a rebuild. Partnership target, never a cited source.
- **BIA Osage Agency** — publishes the estate's extent, not its leases.
- **ANCSA reports** — per-asset revenue. Consolidated only, with **one**
  exception: NANA reports Red Dog royalties as a line, which is why Red Dog is
  the only asset here with `revenue_coverage_state = PUBLISHES`.

### What nobody checked (NOT_CHECKED — unfinished work, said so)

ANCSA **village** corporation filings · BIA forestry timber sales · Indian
water rights settlements · BIA rights-of-way. See the ranked leads below.

---

## What got built

| Source system | Rows | What |
|---|---:|---|
| `ANCSA_regional_corporation_annual_report` | 30 | 20 land/mineral estates (all 12 regionals) + 10 named projects |
| `BIA_Osage_Agency` | 2 | Osage Mineral Estate; Osage County surface trust and restricted lands |
| `SEC_EDGAR_10K` | 2 | Three Peabody Navajo/Hopi coal leases; Kayenta Mine |
| `SEC_EDGAR_exhibit` | 1 | **Crow Tribal Lands Coal Lease** — the only executed lease instrument in the file |

Assets by type: subsurface_estate 9 · surface_estate 4 · combined_fee_estate 4 ·
deposit 4 · mine 3 · land_estate 2 · forest_carbon_project 2 ·
land_conveyance 1 · prospect 1 · oil_field 1 · mineral_estate 1 · tract 1 ·
lease 1 · lease_group 1.

### The Alaska layer needed no fetch at all

All 30 ANCSA rows came from **166 annual reports another agent had already
retrieved for a different purpose** — the same lesson the recipient-side log
recorded. The portal URL on every row is read from that agent's retrieval index
by filename join, so no `source_url` is constructed by hand.

Named projects: Red Dog Mine (NANA / Teck Alaska), the Aqqaluk and Qanaiyaq ore
bodies within it, the Arctic and Bornite deposits, the Fairhaven Gold Project,
Donlin Gold (Calista subsurface / Donlin Gold LLC), ASRC's interest in the
Alpine Oil Field, and the Sealaska and Chugach forest carbon projects.

**An operator is never an owner.** Teck operates Red Dog; NANA owns the ground.
The two are separate party rows with different `relationship` values, and
Teck is not resolved to the spine because it is not a Native entity.

---

## What was refused, and why

| Refused | Why |
|---|---|
| **Splitting Peabody's three leases into three rows** | The 10-K says *"three coal leases"* and identifies **none** individually — no lease number, no lessor split, no per-lease acreage. Three rows would invent two assets. Written as ONE `lease_group` with `asset_count_in_source = 3`. |
| **Splitting the 64,783 acres between Navajo and Hopi** | It is a combined figure across two reservations. The filing does not divide it, so neither do we. |
| **Applying the 12.5% / 8.0% royalty rates to the tribal leases** | Those rates govern **federal** leases in the same filing. Applying them to the tribal leases is the rate-inversion trap in a new place. No rate is recorded for that asset. |
| **Rate × tonnage for the Crow lease** | 6.5% capped at 12.5%, and $1.00/acre rental, are rates. Multiplying by production would be a modelled number. |
| **Acreage for the Crow lease** | The Leased Premises are defined by reference to Section 8 of a separate Exploration Agreement the exhibit does not reproduce. `area_acres` is blank and `area_basis` says so. **Not inferred.** |
| **Attaching Kayenta Mine to the Navajo/Hopi leases** | The 10-K names Kayenta as a mine it operates in Arizona, and separately says it leases coal from the Navajo Nation and the Hopi Tribe. It never says which mine works which lease. Kayenta is kept **deliberately unattributed**, with **no party link at all**, so a future pass can attach it on evidence rather than on proximity. |
| **Any allotment row** | There is no public register. And a tract inside a reservation boundary is **not** evidence of tribal mineral ownership — trust versus fee is the whole question. |
| **Stacking the yearly ANCSA acreage restatements** | One row per (corporation, estate), carrying the most recent stated figure. Stacking eleven vintages would turn one asset into eleven. |
| **Splitting ASRC's 5,000,000 acres into surface and subsurface** | ASRC reports one combined figure. A decomposition would be invented. |
| **Summing any acreage** | No total is computed anywhere in this build. Regional subsurface overlaps village surface by design — BSNC's 2,109,828 subsurface acres sit **beneath land owned by village corporations**. |

---

## Two evidence-quality notes carried in the data

**CIRI is the only regional whose acreage comes from an infographic**, not an
audited note — and the 2025 report's text layer **interleaves the labels**:

```
529,500 Acres 1.6M Acres ... of surface estate land of subsurface estate
```

Read naively that assigns the wrong figure to each estate. The **2024**
rendering prints each label adjacent to its number and is cited instead. Both
CIRI rows are **tier B** and the hazard is written into `coverage_note`. This is
the same class as the OSMRE one-row offset already held elsewhere.

**The Crow lease quote carries its EDGAR exhibit header** (`EX-10.51 10
d66453exv10w51.htm …`) because the filing's text layer has no sentence break
before the lease title. It is left exactly as retrieved. Trimming it would break
the verbatim-by-construction guarantee that makes every other quote checkable.

---

## Access facts worth recording

- **`www.sec.gov` returns HTTP 403 to an unidentified client and 200 with a
  declared User-Agent.** That is an access rule, not an absence — and it is the
  only route found to an executed tribal mineral lease instrument.
- **EDGAR full-text search reached the Navajo/Hopi lease language in one call**
  (45 hits). It is the practical index for tribal lease language in lessee
  filings.
- The session's **WebSearch budget was exhausted (200/200) by other agents**
  before this build. All retrieval therefore used URLs already surfaced in the
  project's own retained evidence. Recorded as a constraint, not a limitation of
  the sources.

---

## Downstream, now stale

`docs/codebooks/12_resources.md`, `codebook_master.csv` (70 variables under
`12_resources`) and `dist/12_resources/*.notes.json` do not yet describe the 16
columns script 130 added, nor `resource_asset_source_coverage.csv`.

**Regenerate them; do not hand-edit.** They were deliberately *not* regenerated
in this run because `codebook_master.csv` changed underneath this session
(641 → 1,452 variables between two runs of the guard), meaning another agent is
actively rebuilding it. Running the generator concurrently is the collision
AGENTS.md warns about.

---

## Open leads, in order of value

1. **ANCSA village corporation filings.** 173 village corporations, the same
   portal, already-proven retrieval path. They hold the **surface** where the
   regionals hold the **subsurface** — the missing half of the Alaska asset
   picture, and the §7(j) receiving side the regionals' reports structurally
   omit. No new access needed.
2. **Indian water rights settlements.** Enacted public laws that **quantify**
   tribal water rights in acre-feet. This would be the best-evidenced asset
   class available anywhere in the ledger — a named tribe, an exact quantity, in
   the Statutes at Large. Recorded `NOT_CHECKED`, not `NOT_FOUND`.
3. **EDGAR full-text search for tribal lease language generally.** One query
   found the Peabody leases. `"Indian Mineral Development Act"`, `"tribal
   lands"`, `"lease of Indian land"` across all exhibit types is an unworked
   seam with a proven retrieval path.
4. **BIA forestry timber sales.** `bia.gov/bia/ots/forestry` 404'd in an earlier
   wave; the only plausible route to named-tribe timber for AK/WA/MN/WI/CA.
5. **BIA NIOGEMS partnership.** The one system that would turn this layer from
   35 rows into thousands. The join columns are already in place and empty.
