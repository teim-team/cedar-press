# The Indian Incentive Program: a measured gap

*Written 2026-08-06. Task: establish whether IIP data is obtainable and
recommend a route. **No data was pulled** — `api.usaspending.gov` is held by
another process and this is a feasibility determination, not a build.*

---

## What the programme is

**25 U.S.C. 1544**, implemented at **DFARS subpart 226.1** and clause **DFARS
252.226-7001**, lets a DoD prime contractor claim a **5% rebate on amounts it
subcontracts to an Indian organization or Indian-owned economic enterprise**.
The incentive is paid to the *prime*, as an adjustment to its contract, for work
performed by a Native *sub*. It is administered by the DoD Office of Small
Business Programs.

This is a genuine Native preference channel and one Cedar Press does not cover.
It matters because it is structurally different from every channel we do cover:
**it is a subsidy on the buyer's side of a subcontract, not an award to a Native
entity.** Nothing in a prime-award file can show it, by construction.

---

## Confirmed: it is absent from our data

| Where I looked | Result |
|---|---|
| `data/clean/prime_contracts.csv` (617,142 rows, 34 columns) | **No IIP field.** Native-preference columns are `reported_8a`, `reported_buy_indian`, `reported_indian_business`, `reported_native_preference`, `setaside`, `setaside_reported` |
| `setaside` value set | Exactly 7 values, none an incentive flag: `None reported` (223,603), `8(a)` (176,859), `Small Business` (97,093), `Other` (95,188), `HUBZone` (10,227), `Indian Business` (7,245), `Buy Indian` (6,927) |
| `data/clean/subawards.csv` (55,035 rows, 48 columns) | **No IIP field and no rebate field.** |
| Source `.dta` files | No IIP field |
| Literal sweep for `indian incentive` / `252.226-7001` across `data/`, `code/`, `docs/` | Zero hits in any transaction file |

**Confirmed as stated in the task: the IIP is not in our data at all.**

---

## But it is in our data twice — as regulation and as advocacy

The literal sweep did return hits, in two corpora that are not transaction data.
Both are useful and neither was previously noticed.

**Seven Federal Register documents** are about the programme
(`data/clean/federal_actions.csv`):

| Date | Type | Title |
|---|---|---|
| 1995-11-30 | Rule | DFARS; Miscellaneous Amendments |
| 1996-07-26 | Rule | Federal Acquisition Regulation; **Indian-Owned Economic Enterprises** |
| 1999-11-18 | Proposed Rule | DFARS; Utilization of Indian Organizations and Indian-Owned Economic Enterprises |
| 2000-04-13 | Rule | DFARS; Utilization of Indian Organizations and Indian-Owned Economic Enterprises |
| 2002-11-22 | Proposed Rule | DFARS; **Indian Incentive Clause — Contract Types** |
| 2003-10-01 | Rule | DFARS; **Indian Incentive Program** |
| 2004-09-17 | Rule | DFARS; **Indian Incentive Program** |

That is the programme's regulatory history, already in hand, and it dates the
clause revisions precisely.

**Eleven lobbying filings** mention it, all from **Arctic Slope Regional
Corporation**, 2019–2021, all to the same end:

> "Legislation to restore direct appropriations for the Department of Defense
> Indian Incentive Program" — and, in the 2019 filings, naming **H.R. 2968** and
> **S. 2474** (116th Congress).

This tells us something the transaction data could not: **the programme's direct
appropriation lapsed or was threatened, and an ANC lobbied to restore it.** It
also means IIP funding levels are a live congressional issue with named
vehicles. Neither H.R. 2968 nor S. 2474 is currently in
`data/clean/native_bills.csv` — a small, concrete coverage gap in Dataset 10.

---

## The eligible population we *can* already size

We cannot observe a single rebate. We can observe the population the rebate
applies to, because `subawards.csv` carries SAM business-type codes on the sub.

- **22,484** subaward rows have a **DoD prime**.
- **5,773** of those go to subs flagged Native in `sub_business_types`
  (`AMERICAN INDIAN OWNED`, `NATIVE AMERICAN OWNED`, `TRIBALLY OWNED FIRM`,
  `INDIAN TRIBE (FEDERALLY RECOGNIZED)`, `ALASKAN NATIVE CORPORATION OWNED
  FIRM`), totalling **$12.10B** in subaward dollars.

**This is a ceiling on the eligible base, not a measure of the programme.** Read
it as: *"$12.1B of DoD subcontract dollars went to Native-flagged firms in the
FSRS-reported population; a 5% rebate on the qualifying subset of that is the
outer bound of IIP activity."* It must never be presented as IIP spending —
eligibility requires the prime to claim the incentive and the sub to meet the
statutory definition, and neither is observable here. Standing rule 7 also
applies: FSRS subaward dollars must not be summed unfiltered, and FSRS
under-reports below its thresholds.

---

## The definitional problem that would bite any build

**25 U.S.C. 1452(e)** defines an *"economic enterprise"* as any commercial,
industrial or business activity **owned at least 51% by Indians**. The operative
word is **Indians — individuals**, not tribes.

This does not line up with our spine, and the mismatch is the same one the
`hci_analysis.do` per-UEI rulings spent enormous manual effort on: **individual
Native ownership is not tribal ownership.** The do-file's many "owned by
individual Cherokees" drops are exactly the population the IIP *includes* and
our entity spine *excludes*.

So an IIP dataset would be substantially a dataset of **individually
Indian-owned firms** — a universe Cedar Press has never built, that has no
membership roster, and that cannot be resolved to `tribe_id` because there is no
tribe on the other end. Tribally-owned firms and ANCs qualify too, but they are
not the whole eligible set and may not be most of it.

**This is the single strongest argument against treating IIP as a Cedar Press
dataset**, and it is a finding in its own right: the preference channel and our
entity model are keyed on different definitions of Native ownership.

---

## Route determination

*This section records what external sourcing routes exist.*

> **Evidentiary status — read before relying on this section.** Findings marked
> **[agent-retrieved]** come from a documentation sweep run by a subordinate
> agent on 2026-08-06. **I did not open those documents myself.** They are
> recorded with their source identifiers so they can be checked, and per
> standing rule 4 they are agent research — not a ruling, and not Cedar Press
> data. **No figure below has been written into `data/clean/`, and none should
> be until someone opens the named PDF.** Findings about *our own files* (the
> sections above) were verified directly by me and carry no such caveat.

### Route A — FPDS-NG prime-award flag

**Assessment: almost certainly unavailable, and the reason is structural.** FPDS
records *awards*, not *clauses*. The socio-economic data elements it carries
describe the **awardee's** status (8(a), HUBZone, SDB, women-owned, tribally
owned, ANC-owned). The IIP is a rebate to a **non-Native prime** for the status
of its **sub** — there is no awardee attribute that could encode it, and no
FPDS element corresponds to DFARS 252.226-7001. Our own `setaside` field having
exactly 7 values with no incentive flag is consistent with this.

**[agent-retrieved] The mechanism that closes it.** The rebate is paid by
**modifying the prime's existing contract**, funded by an OSBP MIPR. It never
becomes its own award record, so there is no transaction for FPDS to capture —
the incentive is a line of money moving inside a contract that already exists.
This is the crisp reason Route A cannot work, and it is stronger than the
inference from our field inventory.

Treat Route A as closed.

### Route B — subcontract reporting (FSRS / USAspending subawards)

**Assessment: partially available, and it is the best of the data-driven
routes.** FSRS captures the sub's identity and dollars, and — as demonstrated
above — SAM business types let us flag Native subs under DoD primes. What FSRS
does **not** carry is any indication that an incentive was claimed or paid. So
Route B gives the **eligible base**, never the **programme**.

Its known limits apply in full: reporting thresholds exclude small subawards,
compliance is imperfect, and the population is not the universe.

### Route C — DoD's own IIP reporting

**Assessment: CONFIRMED and cheap. This is the route.** It was the weakest-
evidenced section of this memo and is now the strongest.

**[agent-retrieved] Where the line lives.** Procurement, Defense-Wide (0300D),
BA 01 Major Equipment, **P-1 Line 30**. The OSD/OSW O&M justification books were
text-searched directly (FY2027 `OSW_OP-5`, 976,608 chars; FY2026 `OSD_OP-5`,
861,268 chars) and contain **zero occurrences of "Indian" or "Incentive"** —
so there is no O&M line and the Procurement line is the whole programme.

**[agent-retrieved] A naming trap for anyone building the series.** The cost
element was **relabelled** from *"Indian Incentive Program"* (FY2024–FY2025
books) to **"Indian Financing Act"** (FY2026–FY2027 books). String-matching on
one label alone will silently truncate the series at FY2025.

**[agent-retrieved] The published series** ($ millions):

| FY | Request | Shown as executed | Source |
|---|---:|---:|---|
| 2022 | 25.000 | 25.000 | FY2024 PB P-5 |
| 2023 | — | 44.556 | FY2024, FY2025 PB |
| 2024 | 25.169 | 25.169 | FY2024/25/26 PB |
| 2025 | 10.950 | 25.169 | FY2025 PB vs FY2026/27 PB |
| 2026 | 7.613 | 24.613 | FY2026 PB vs FY2027 PB |
| 2027 | 6.821 | House adds +35.000 | FY2027 PB; H. Rept. 119-715 |

Cumulative prior-years through FY2024: **119.728**. Senate JES adds +17.000 for
FY2026; the House adds +35.000 for FY2027 (H. Rept. **119-715**, an FY2027
report — not FY2026).

**The structural pattern is the finding**: DoD requests well below what Congress
appropriates, every year. The *executed* column is the one to use, and it
directly corroborates the ASRC lobbying campaign documented above — the
appropriation really was contested.

**[agent-retrieved] Aggregate programme statistics**, repeated verbatim across
the FY2025–FY2027 books: roughly **140 rebates a year**, **100+ participating
primes**, **100+ Native-owned firms**, and 46% of participants crediting the
programme. The FY2027 book adds one statistic the earlier books lack: *"60
percent of FY 2026 rebate payments supported military weapon systems and
mission priorities."* Note these are explicitly rounded ("over 140", "over
100") — DoD never names a participant or publishes a per-rebate record.

**[agent-retrieved] Why the series starts at FY2022.** The IIP entered the
President's Budget request for the first time in **FY2024**; before that it
existed purely as a congressional add, which is why no earlier justification-book
series exists (DoD OSBP director, Senate Small Business Committee, 2023-03-22,
`CHRG-118shrg60057`).

**[agent-retrieved] Historical scale, from advocacy testimony — not DoD.**
National Center for American Indian Enterprise Development, Senate Indian
Affairs, 2014 (`CHRG-113shrg90934`): *"Between fiscal years 1999-2010, the IIP
leveraged cumulative program funding of $122 million into more than $2.5 billion
in subcontractor revenue for Native businesses"*, with annual appropriation then
*"$15 million"* and backlogs that *"have always exceeded the annual
appropriation."* **Treat as interested testimony, not as a measurement.** The
$2.5B leverage claim in particular is unaudited and should never be repeated
without that attribution.

### Route D — FOIA / DoD IG

**[agent-retrieved] There is already an audit, and nobody has read it.**
**DoD IG Report D-2011-091, *"DoD Indian Incentive Program Payments to Related
Parties and Rebates to Excluded Parties"*, 22 July 2011** — listed on dodig.mil's
Audits/Evaluations index and in the DoD IG Semiannual Report (1 Apr – 30 Sep
2011). PDF at
`https://media.defense.gov/2011/Jul/22/2001712155/-1/-1/1/D-2011-091.pdf`.

Two independent attempts to fetch it hit Akamai 403. **This is the
highest-value unread document in the whole enquiry** — its title alone says the
IG found payments to *related parties* and rebates to *excluded parties*, which
is a data-quality and integrity story about the programme, and it may name
participants. Open it in a browser.

Everything else is negative and the negatives are now solid:

- **GAO holds no IIP data.** Only `GAO-07-714` (2007, three purely descriptive
  mentions, no dollar figures), the `B-310737.3` bid protest, and a footnote in
  `GAO-22-104621`.
- **CRS: not found.** Search endpoints are JavaScript-only and returned nothing
  verifiable — absence not established.
- **The entire congressional-document footprint is 22 items**, from a govinfo
  full-text search for `"Indian Incentive"` across CRPT/BILLS/CREC/CHRG/
  GAOREPORTS.
- **oversight.gov cannot be used to establish absence**: it returned "No
  results" for IIP *and* for a Mentor-Protégé control query, so the index
  itself is unreliable.

### Access note worth keeping

`comptroller.defense.gov`, `business.defense.gov`, `media.defense.gov`,
`gao.gov` and `dodig.mil` all return Akamai 403 to automated fetch. Three
workarounds, recorded because they generalise well beyond this enquiry:

1. **`comptroller.war.gov` serves byte-identical justification PDFs with HTTP
   200** where `comptroller.defense.gov` 403s. Simplest fix.
2. `https://web.archive.org/web/<yyyy>id_/<url>` returns raw PDF bytes for older
   books.
3. `https://www.govinfo.gov/content/pkg/<PKG>/html/<PKG>.htm` needs no key and
   has no rate limit.

These belong in `docs/ACCESS_TECHNIQUES.md` on a future pass.

---

## Recommendation

**Do not build a transaction-level IIP dataset — it does not exist and cannot be
made. Do publish a small, sourced IIP reference note, because the programme
series turned out to be obtainable.**

This is a change from the first draft of this memo, which recommended treating
the whole thing as a gap. The route sweep confirmed a real, citable
FY2022–FY2027 DoD-published series, so the recommendation splits in two.

**Still ruled out — a dataset:**

1. **The unit of observation does not exist in any structured source.** The
   rebate is paid as a modification to the prime's existing contract, funded by
   an OSBP MIPR, so it never becomes an award record anywhere. Not an FPDS gap;
   a structural impossibility.
2. **The eligible universe is keyed on individual Indian ownership**, which our
   entity spine deliberately does not model and which the project's own per-UEI
   rulings exist to *exclude*. An IIP dataset would need a new entity universe
   with no roster behind it, and **DoD never names a participant** in any case.
3. **We can already state the ceiling** — $12.10B of DoD subaward dollars to
   Native-flagged firms — which is the number a subscriber actually wants.

**Now worth doing — a reference note (one session, network-light):**

4. **Verify and publish the FY2022–FY2027 programme series.** Open the
   justification books via `comptroller.war.gov`, confirm the figures in the
   Route C table against the P-1 Line 30 / "Indian Financing Act" element, and
   publish as a sourced reference table. Six years of request-versus-executed on
   a Native preference programme, with a clear pattern of Congress
   appropriating several times what DoD requests, is a genuine finding and
   nobody has assembled it.
5. **Open DoD IG D-2011-091 in a browser.** Highest-value unread document in
   this enquiry.

**Do these now (no network, no new sourcing):**

- **Publish the eligible-base measure** as a documented cut of the subaward
  dataset: DoD-prime subawards to Native-flagged subs, per year, clearly
  captioned as a ceiling on IIP-eligible activity and never as IIP spending.
- **Add the 7 FR documents as a named subset.** The IIP's complete regulatory
  history, 1995–2004, is a small exact artefact of the kind
  `SUBSET_DATASETS.md` argues for — nobody else has it assembled.
- **Add H.R. 2968 and S. 2474 (116th) to Dataset 10.** They are missing, and
  they are the legislative half of a story the lobbying data already tells.
- **Record the definitional finding** — that federal Native preference channels
  are keyed on *individual* Indian ownership while our spine is keyed on
  *entity* ownership — in the coverage documentation. It explains a class of
  undercount that will recur, and it is worth saying out loud.

**Revisit the dataset question only if** DoD OSBP begins publishing per-award
rebate records. Nothing in the current evidence suggests it will.

---

## What is NOT established

- **Every figure in Route C is agent-retrieved and unverified by me.** I did not
  open a single justification book. The FY table, the P-1 line, the "Indian
  Financing Act" relabel, the 140-rebates statistic and the hearing quotes all
  need confirming against the named documents before publication. **None has
  been written to `data/clean/`.**
- **DoD IG D-2011-091 has not been read** by anyone in this enquiry — two fetch
  attempts returned Akamai 403. Its findings are unknown; only its title is.
- **No FPDS data element was inspected by name** in a published data dictionary.
  Route A is closed on the MIPR-modification mechanism, which is a strong
  structural reason but not a quoted field-list absence.
- **No IIP dollar figure is asserted as Cedar Press data.** The $12.10B is FSRS
  subaward dollars to Native-flagged subs under DoD primes — a different
  quantity that bounds the programme from above, subject to standing rule 7.
- **The NCAIED "$122M leveraged into $2.5B" claim is advocacy testimony**, not a
  measurement, and is unaudited.
- **CRS coverage is unknown**, not absent: its search is JavaScript-only and
  returned nothing verifiable. Likewise oversight.gov, whose index failed a
  control query and therefore cannot establish absence of anything.
- **The share of IIP-eligible firms that are individually Indian-owned versus
  tribally owned is unknown** and was not estimated.
- **Whether the direct appropriation was restored** after the 2019–21 ASRC
  campaign is not directly established. The FY2022–2027 executed column is
  consistent with restoration but was not traced to that campaign.
