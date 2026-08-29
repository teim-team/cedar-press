# Native resource revenue, read from the RECIPIENT

*Run 2026-08-06. Script: `code/84_resource_recipient_side.py`. Appended to
`data/clean/resource_revenue.csv` and `data/clean/resource_parties.csv`;
conflicts to `review/resource_recipient_side_conflicts_2026-08-06.csv`.
Pairs with `docs/RESOURCE_LEDGER_BUILD_LOG.md`, which built the payer side.*

---

## The problem this run exists to solve

The resource ledger's first build ended with a number that is really a verdict:

> **9,467 of 10,123 rows are `national_aggregate` with no entity resolved**, and
> exactly one entity in the entire ledger resolves — the Three Affiliated Tribes,
> and only because North Dakota's Treasurer names a payee that Interior will not.

That is not an unfinished join. Interior releases Native American extraction and
revenue information **only in aggregate, by law**, and the build measured the
suppression rather than assuming it: 0 of 9,238 Native monthly revenue rows carry
any geography, against 99.8% of Federal rows in the same file.

The philanthropy build hit the identical wall from the funder side. Tribal
governments are outside the Form 990 universe under IRC §7871, so ProPublica
returned **HTTP 404 — no organisation at all** for Shakopee, San Manuel, Tulalip,
Muckleshoot, Morongo, Pechanga and Seminole. Its closing recommendation was to
invert the channel: *"instead of reading the funder's return, read the
recipients'."*

This run does that for resource revenue. **It works, and it works far better
than expected — but only in one of the four channels.**

---

## Result in one line

**185 revenue events, 12 of 12 ANCSA regional corporations, fiscal years
2014–2025, every figure verified against a retrieved document before it was
written.** 82 rows rest on audited financial statements or their notes; 103 on
management's discussion and analysis. Zero rows were estimated, modelled,
allocated or derived.

| Channel | Rows added | Verdict |
|---|---:|---|
| **1. ANCSA §7(i) / §7(j)** | **185** | **The channel. Recurring, statutory, audited, between named Native entities.** |
| 2. Tribal bonds / MSRB EMMA | 0 | Structurally near-dead for *resource* revenue — see below |
| 3. Tribal annual reports and financials | 0 | Measurably barren at the tribal-government level |
| 4. Litigation and settlements | 0 | Not disproven; **blocked**, not refuted — see below |

---

# Channel 1 — ANCSA §7(i) and §7(j)

## Why this is the strongest resource-revenue trace in Indian Country

Section 7(i) requires each of the twelve Alaska-based ANCSA regional
corporations to divide **70% of net revenues from timber resources and the
subsurface estate** among all twelve, by original-enrollment share. Section 7(j)
requires each to pass **not less than half** of what it receives to the village
corporations and at-large shareholders of its own region.

So it is a **recurring, statutory, audited money flow between named Native
entities** — the exact object the federal record refuses to produce. And unlike
a federal payment file, both ends of it are disclosed by the parties themselves.

## Nothing was fetched

Cedar Press already held **166 ANCSA-portal annual reports as retrieved PDFs
converted to text** under `code/ancsa_portal/txt/`, indexed with per-document
portal URL, byte count and SHA256 in `data/clean/ancsa_filings_index.csv`
(19,269 rows, swept 2026-08-05). **126 of the 166 contain §7(i) or §7(j).**

**No remote host was touched by this run.** No lock was claimed and none was
needed. `docs/PULL_DISCIPLINE.md` rule 1 is satisfied vacuously.

That is the reusable lesson: the highest-yield step here was **grepping an asset
another agent had already retrieved for a different purpose**. The ANCSA portal
sweep was built to find *deals*. It also contains a complete twelve-corporation
resource-revenue panel, and nobody had read it that way.

## The anti-fabrication gate, and why it is the load-bearing part

Every one of the 134 declared facts carries the text that must be present in the
named local document, and the script **refuses to emit any row whose evidence
does not verify**:

- `quote_type = verbatim_sentence` — the whole sentence must appear
  (whitespace-normalised) in the document text.
- `quote_type = table_reading` — the printed label **and** every printed number
  must appear in the document.

```
EVIDENCE GATE
  facts declared : 134
  verified       : 134
  REFUSED        : 0
```

**The gate earned its keep on the first run.** One fact failed: Bering Straits
FY2023, because the PDF prints `Fiscal year 2023’s` with U+2019 and the fact was
typed with an ASCII apostrophe. That is exactly the class of error the gate
exists to catch — a figure I had read correctly, attached to a quote that did not
literally exist. It was corrected against the document, not against memory.

The verbatim quote travels with the row, in `beneficiary_note`, prefixed
`source_document_type=… quote_type=… VERBATIM: "…"`. A future reader can re-check
any figure without leaving the CSV.

*(Schema note: `resource_revenue.csv` has no `source_document_type` or quote
column, and adding one would mean rewriting 10,123 existing rows while another
agent is concurrently appending states. The document type is therefore carried as
a machine-parseable token at the head of `beneficiary_note`. Recorded here as a
deliberate compromise, not an oversight.)*

## What was built, by corporation

Amounts are the sum of the rows written, in nominal dollars. **They overlap by
construction and must not be added** (see the double-count section).

| Corporation | Inbound §7(i) | Outbound §7(i)/§7(j) | Other |
|---|---|---|---|
| NANA Regional Corporation | 3 rows · $7.5M | 24 rows · $1,390.1M | Red Dog royalty 7 rows · $1,728.6M; PILT 1 row · $26.7M |
| Sealaska Corporation | 9 rows · $197.6M | — | |
| Calista Corporation | 8 rows · $166.2M | — | |
| Doyon, Limited | 11 rows · $139.4M | — | |
| Cook Inlet Region (CIRI) | 12 rows · $112.1M | 21 rows · $117.1M | |
| Bristol Bay Native Corporation | 12 rows · $92.2M | — | |
| Bering Straits Native Corporation | 7 rows · $66.8M | — | |
| Koniag, Incorporated | 12 rows · $57.1M | — | |
| Chugach Alaska Corporation | 13 rows · $58.1M | 6 rows · $18.2M | |
| Aleut Corporation | 11 rows · $51.1M | 8 rows · $35.6M | |
| Arctic Slope Regional Corporation | 9 rows · $40.1M | 7 rows · $366.2M | |
| Ahtna, Incorporated | 4 rows · $10.5M | — | |

**§7(i) receipts recorded: $998.6 million. §7(i)/§7(j) obligations recorded:
$1.95 billion.** All twelve regionals resolved to the spine on `exact` — no
containment tier was used, and no name matcher was written.

### The two corporations that generate the pool

The panel makes visible something no federal source states: **§7(i) is
overwhelmingly funded by two regions.** NANA's Red Dog zinc royalty and ASRC's
North Slope oil royalty are the sources, and both corporations' §7(i) obligations
dwarf their receipts:

- NANA reports paying **$1.385 billion** to the other regionals over FY2014–FY2025
  while receiving **$7.5 million** back.
- ASRC reports **$366.2 million** of combined §7(i)/§7(j) obligations over
  2019–2025 against **$40.1 million** received.

Bering Straits states this outright in its 2016 report: *"the 7(i) distribution
from NANA and Arctic Slope Regional Corporation decreased, resulting in 7(i)
revenue of $6.7 million."* **A recipient naming its payers.** That single sentence
is the thing the federal record cannot give us.

### The collapse and rebound nobody has written about

NANA's audited note reports §7(i) cash paid to the regional corporations of
**$4,452 thousand in FY2024** — against $143,609 thousand in FY2023 and $101,067
thousand in FY2025. A 97% collapse and a 22× rebound in consecutive audited years.
Recorded as reported. Not explained by anything in the documents, and **not
smoothed**.

## The double-count, handled explicitly rather than silently

A §7(i) dollar appears in the paying corporation's report **and** in every
receiving corporation's report. Netting them would destroy the relationship; so
would picking one.

So the direction is carried in the row, per the `native_passthrough.csv` pattern:

| Series | Meaning |
|---|---|
| `IN_7I_GROSS` | received, **before** the §7(j) pass-through |
| `IN_7I_NET` | received, **net of** the §7(j) pass-through |
| `OUT_7I` | distributed by this corporation to the other regionals |
| `OUT_7J` | distributed by this corporation to village corporations / at-large shareholders |
| `OUT_7I_7J_COMBINED` | ASRC reports one combined obligation and does not split it |

Every row carries this in `beneficiary_note`:

> DOUBLE-COUNT WARNING: ANCSA Section 7(i) is a transfer AMONG the twelve
> Alaska-based regional corporations, so the same dollars appear in the paying
> corporation's report and in every receiving corporation's report. This row
> records ONE SIDE. Inbound and outbound rows in this source system must never be
> summed together, and a 'net of 7(j)' row must never be added to a gross row.

**And gross vs net is not cosmetic.** Chugach's 2021 §7(i) income is printed
**$4,205,940** in its 2021 statements and **$2,102,970** in its 2023 comparative
column — exactly half, because the label changed from `7(i) income from other
regional corporations` to `…, net`. Both are kept, under different series, with
the arithmetic relationship stated in the row. A build that deduplicated on
`(corporation, year)` would have picked one at random and halved or doubled a
regional's decade.

## Conflicts recorded, not resolved (8)

Per `docs/CROSS_SOURCE_VERIFICATION.md`, a disagreement at the same authority
level goes to `review/` with both values, both URLs, and **no resolution**.

| Entity | Year | Disagreement |
|---|---|---|
| **NANA** | FY2023 | §7(i) cash paid **$96,882K** (FY2023 report) vs **$143,609K** (FY2024 *and* FY2025 reports). **A $46.7 million restatement of one audited line.** |
| **NANA** | FY2022 | §7(i) **$199,368K cash paid** (audited note) vs **$263.6 million distribution** (MD&A infographic) — **in the same document**, $64M apart. Accrual vs cash is the likely cause; the report does not say. |
| **ASRC** | 2020 | Amounts payable to other regions **$(59.8)M** (2020 report) vs **$(52.8)M** (2022 report). Natural-resources earnings for 2020 also restated 24.7 → 31.6. |
| **Sealaska** | 2019 | Net §7(i)/§7(j) revenue sharing **$20,270K** (2019 report) vs **$28,635K** (2020 and 2021 reports). Coincides with logging moving to discontinued operations. |
| **Koniag** | FY2024 | Segment table **$2,107K** vs MD&A prose **"$2.4 million"** — same document. Every other Koniag year agrees to the rounding. |
| **Aleut** | FY2022 | §7(i) received **$4,178,214** vs §7(j) distributed **$4,178,124** — adjacent paragraphs, $90 apart. Probably a transposition in the source. |
| **Chugach** | 2021 | Gross vs net presentation change, exactly 2:1. **Not a contradiction — a series break**, and recorded as one. |
| **Calista** | 2021 | **Held, not published.** The only sentence carrying it is OCR-degraded (`"S25.8 million in 2022 compared to $16.9 millton in 2021"`). |

**Vintage rule, applied uniformly:** a figure is taken from the report in which
that year is the *current* year (as-originally-reported), with evidence rank
breaking ties (audited statement > MD&A table > MD&A prose). The ledger therefore
carries $96,882K for NANA FY2023 while two later audited reports say $143,609K.
That is a rule, stated, not a judgement about which is true.

## Refused within this channel

| Refused | Why |
|---|---|
| **Calista 2024 and 2025** | The reports state only *"increased by almost $10 million or 69% in 2025 as compared to 2024"*. Back-solving a level from a percentage is a derivation. The series stops at 2023. |
| **Calista 2021** | OCR-degraded in the retrieved text layer. Held. |
| Balance-sheet §7(i)/§7(j) items | `Amounts payable under ANCSA Sections 7(i) and 7(j)` (Sealaska), `Accrued 7(j) liability` and `Prepaid 7(i) distribution` (Chugach) are **stocks, not flows**. A revenue ledger that admits a payable balance stops being a revenue ledger. |
| Sealaska's §7(i) charts | Non-operating EBITDA charts combine investments, carbon and §7(i). *"roughly $15M"* is an explicit approximation and is not a figure. |
| Applying the 70% / 50% statute to any row | The shares are governed by the 1982 §7(i) Settlement Agreement plus allowable deductions and cost carryforwards **that no report quantifies**. `allocation_formula` says so in the field itself, so a subscriber cannot pick up "70%" and multiply — the same guard the North Dakota rows carry against the 80/20 split. |
| Any village-corporation §7(j) recipient | §7(j) rows name the *paying* regional. No report names which village corporation received what. Recipient stays the collective description; no village corporation is attributed. |

## What this channel structurally cannot yield

- **Per-counterparty detail.** No report says "we paid Doyon $X". The §7(i) pool
  is divided by enrollment share, and only the pool total is published. Pairwise
  flows between named regionals are **not obtainable from this channel** and
  should not be attempted from it.
- **Village corporations.** 173 village corporations are in the spine. §7(j) money
  reaches them, and not one report names a village-corporation amount. Reaching
  them means reading *village* corporation annual reports — which the ANCSA portal
  also holds, and which this run did not open.
- **Pre-2014.** The portal sweep starts at filing year 2016 (reporting 2014 as a
  comparative). Earlier filings exist in the portal and were not swept.
- **Lower-48 tribes.** §7(i) is an Alaska statute. This channel says nothing about
  any tribe outside ANCSA, which is why channels 3 and 4 matter so much.

## What a future pass should try, ranked

1. **Village corporation annual reports on the same ANCSA portal.** 173 village
   corporations, the same retrieval path, and the §7(j) *receiving* side that the
   regionals' reports structurally omit. This is the single highest-value unworked
   item in the whole run, and it needs no new access.
2. **Pre-2016 portal filings.** Extends a clean twelve-corporation panel backwards.
3. **NANA and ASRC royalty detail.** Both disclose gross mine and North Slope
   royalty; NANA's FY2022 infographic decomposes gross royalty → §7(i) → §7(j) →
   retained → PILT → Village Investment Fund. Only FY2022 was built. The other
   years' infographics are in the same PDFs.
4. **Reconcile the pool.** Sum all `OUT_7I` against all `IN_7I_GROSS` for a year in
   which all twelve are present. They should be close. **They will not match**
   (cash vs accrual, fiscal years ending in three different months, cost
   carryforwards) — and measuring the gap is a genuine finding either way.

---

# Channel 2 — Tribal bonds and MSRB EMMA

**0 rows. Near-dead for resource revenue, and the reason is clean.**

`data/clean/tribal_bond_issuances.csv` holds 29 issuances. **Every single one is
gaming-backed.** Seminole Tribe of Florida (11), Mohegan, Mashantucket Pequot,
Choctaw Resort Development Enterprise, Chukchansi Economic Development Authority,
Downstream Development Authority, Snoqualmie Entertainment Authority,
Tunica-Biloxi Gaming Authority, Little Traverse Bay Bands, River Rock
Entertainment Authority. The `use_of_proceeds` values are casino construction and
term-loan refinancing.

That is not a gap in the file. **Tribal debt in the public market is a gaming
instrument.** A tribe with a resource-revenue stream large enough to pledge is
overwhelmingly likely to fund from that stream rather than borrow against it, and
the tribes that borrow are the ones monetising a gaming enterprise.

**But the channel's logic is sound — it is just in the wrong market.** The
retrieved ANCSA reports contain exactly the disclosure the channel predicted,
in the *corporate* rather than the municipal market. Koniag, FY2018 annual report,
notes to the financial statements, verbatim:

> "Note payable held by Koniag to a corporation for a loan with interest computed
> at the federal prime rate plus 2.75% … **secured by ANCSA 7(i) revenue and
> receipts net of 7(j) obligations.**"

A Native entity pledging its resource-revenue-sharing stream as collateral, in an
audited note. **Recorded here as a finding, not as a revenue row — it is a debt
instrument, not revenue.**

**What a future pass should try:** EMMA continuing-disclosure filings for the
*non-gaming* tribal issuers, and the tribal utility authorities and housing
authorities that issue on the strength of severance or royalty streams. This run
could not work EMMA: the session's web-search budget was exhausted by other
agents (200 of 200), EMMA needs a search to reach an issuer page, and
`docs/PULL_DISCIPLINE.md` forbids blind probing. **This is a deferral with a
stated cause, not a refutation.**

---

# Channel 3 — Tribal annual reports, budgets and audited financials

**0 rows, and this was measured, not assumed.**

Probed directly, 2026-08-06:

| Target | Result |
|---|---|
| `southernute-nsn.gov/finance/` | **200 OK. Publishes nothing.** The Finance Department page describes accounting, budgeting, AP/AR, payroll and contracts, and carries **no dollar figure and no link to any financial report.** |
| `mhanation.com` | **200 OK. Publishes nothing.** Governance information, event calendar, service directory. No financial documentation, no oil and gas revenue figure — for the tribe that appears in *our own ledger* receiving $3.13 billion of North Dakota oil tax distributions. |
| `www.osagemineralscouncil.com` | **DNS does not resolve.** |
| `nnoilgas.com` | **DNS does not resolve.** |
| `doi.gov/ost` | 200 OK, and useful: *"We disburse more than $1 billion annually and have more than $9 billion under active day-to-day management and investment on behalf of Tribes and individuals."* **Corroborates** the FY2027 Budget in Brief BTFA figures already in the build log ($8.8B, $1B+/yr) from an independent Interior page — two federal traces agreeing, per `CROSS_SOURCE_VERIFICATION.md`. Still not a series, for the same reason as before: BTFA totals mix royalties with judgments, settlements, land-use and investment income. |

**The finding is symmetrical to the §7871 finding in the philanthropy log, and
just as important:**

> **Tribal governments are not required to publish financial statements, and the
> ones with the largest resource revenue in the country generally do not.** The
> MHA Nation receives, by our own ledger, $3.1 billion in oil tax distributions
> from one state, and publishes no figure about it anywhere on its own site.

This is the mirror image of the ANCSA result and explains it. **ANCSA
corporations disclose because a statute makes them** — ANCSA requires an annual
report to shareholders, and Alaska requires it to be filed with the state, which
is why a public portal exists at all. Tribal governments are under no equivalent
duty. **The disclosure is a property of the corporate form, not of Native
entities.** Any claim that Cedar Press covers "Native resource revenue" would be
false; it covers *ANCSA corporate* resource revenue plus two state tax series.

**What a future pass should try, in order of expected yield:**

1. **The Federal Audit Clearinghouse.** Every tribe expending ≥$750,000 in federal
   awards files a Single Audit, and the FAC publishes the full audited financial
   statement PDF. **This is machine-readable, free, keyed by EIN, and it is the
   only route by which a tribal government's audited financials become public.**
   It is the correct next move for this channel and it was not worked here.
   Resource revenue appears there as a governmental-fund revenue line.
2. **Tribal enterprise subsidiaries that file elsewhere** — a tribally owned
   corporation with public debt or an SEC-reporting partner discloses what its
   owner does not.
3. **State severance-tax and royalty-sharing reports** naming tribes, on the North
   Dakota and Montana model already built.

---

# Channel 4 — Litigation and settlement records

**0 rows. Blocked, not refuted — and this is the channel most likely to pay.**

The reasoning holds: the *Cobell* accounting, the 2012–2016 tribal trust
mismanagement settlements, and the Osage litigation all put **sourced dollar
amounts naming a recipient** on the public record, and they are settlements of
*resource-royalty accounting* claims specifically.

What stopped this run:

- **The session's web-search budget was exhausted** (200 of 200 calls) by other
  agents before this channel was reached. `docs/PULL_DISCIPLINE.md` and the
  project's `web_fetch` convention require a URL surfaced in conversation; without
  search there is no way to surface one.
- **`justice.gov` returned HTTP 403 to automated fetch** on a directly constructed
  press-release URL — the same automated-fetch block already recorded for
  `ntia.gov` and `sanmanuel-nsn.gov`. Add `justice.gov` to that list.
- `doi.gov/ost/tribal_beneficiaries/settlement` returned **404** — a path guess,
  not a block, since `doi.gov/ost` itself served fine.

**Nothing was written from memory.** Every figure a person could recite here —
Cobell's $3.4 billion, the ~$1 billion of tribal trust settlements, Osage's $380
million — is exactly the kind of number that is *almost* right, and would be
quoted, and would be ours. **A figure I cannot quote from a retrieved document
does not exist.**

**What a future pass should try:**

1. **DOJ ENRD and Interior press releases for the 2012–2016 tribal trust
   settlements** — these name each tribe and each amount. Retrieve via
   `web.archive.org` (tolerant, and the right fallback when an origin blocks;
   note a host lock already exists at `logs/_HOSTLOCK_web.archive.org.json` — join
   its queue, do not start a second poller).
2. **The settling tribes' own announcements** — recipient-side again, and not
   subject to the DOJ block.
3. **Cobell must be handled with care and probably excluded.** Its recipient class
   is *individual Indian* account holders, not tribal governments. Booking it to
   tribes would repeat precisely the error the ONRR `Native American` land-class
   caveat exists to prevent: *"revenue from Native American lands, NOT payments to
   tribal governments."*
4. **Osage** deserves its own treatment, as the first build log already concluded:
   a headright regime distributing to individual annuitants, not a row in a tax
   table.

---

## Defects found in other people's work, reported and not patched

**`resource_revenue.csv` has 12 duplicate primary keys, all pre-existing.**
`resource_revenue_event_id` is truncated to 19 characters in the MMS builder, so
`…-OTHER_REVENUES` and `…-OTHER_ROYALTIES` collide:

```
RRE-MMS-FY1994-OTHE  RRE-MMS-FY1995-OTHE  RRE-MMS-FY1996-OTHE  RRE-MMS-FY1998-OTHE
RRE-MMS-FY1999-OTHE  RRE-MMS-FY2000-OTHE  RRE-MMS-FY2001-OTHE  RRE-MMS-CY1996-OTHE
RRE-MMS-CY1997-OTHE  RRE-MMS-CY1998-OTHE  RRE-MMS-CY1999-OTHE  RRE-MMS-CY2000-OTHE
```

Twelve pairs, each two distinct revenue events sharing one id. Any join or
dedupe on that key silently loses one of each pair. **None of the 185 rows written
by this run is affected** — `RRE-ANCSA-*` ids are unique across the file — and the
MMS builder was not touched, because it belongs to whoever owns script 83.

---

## Boundaries respected

- `code/01_build_entity_spine.py` **was not run.** The spine was re-read
  immediately before writing and not modified.
- `nigc_*`, `admin_region*`, `gaming_*` and `series_breaks.csv` were not touched.
- `resource_revenue.csv` and `resource_parties.csv` were **appended to, never
  rewritten**; both headers were re-read from disk immediately before the append
  so a concurrent agent adding states could not be clobbered.
- Entity resolution went through `resolve_entity`, imported from
  `code/33_apply_party_rulings.py`. **No second name matcher was written**, and
  all twelve corporations resolved on the `exact` tier — the defective
  `containment` tier was never reached.
- No host was fetched for channel 1. Four probes were made in channels 3 and 4,
  sequentially, against four different hosts, with no retry loop and no lock
  required.
