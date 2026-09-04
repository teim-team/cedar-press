# Editorial Pipeline

**LIVING DOCUMENT. Last reviewed: 2026-08-26** *(re-ranked the same day against
`docs/PUBLISHED_LANDSCAPE_2026-08-26.md` and two owner directions — see PRIOR ART).*

*What each of the eleven shipping Collections can carry as published writing today, how
strong the evidence is for each candidate, and what would make each one stronger.*

> **Three things changed after the first draft and they change the ranking, not just the
> copy.** (1) The FAADS framing is **withdrawn** — the 0.0% measurement ships, the claim
> that the federal government does not document the boundary does not; FFATA §2 does.
> (2) **CICD is not a foil** and the entity-spine derivation question is **closed**.
> (3) **Native-versus-non-Native comparison is deprioritised**, which demoted two pieces.
> A **Tier 0** was added for the one artefact that is unclaimed, unblocked, and writable
> from data already on disk.

This is not a content calendar and it is not a wish list. Every figure below was measured
against a file in `data/clean/` on the date stated beside it. Several agents are live and
row counts move under this document — **a figure with no date beside it is not usable.**
When you update a section, restate the measurement date; do not silently refresh a number.

**Read first:** `README.md` → `START_HERE.md` → `docs/DOC_CONTRADICTIONS_2026-08-26.md`.
That last one matters here more than anywhere else in the repo: there is no version
control, so superseded figures sit in build logs looking exactly as authoritative as
current ones, and an editorial document is precisely where a stale number gets laundered
into print.

---

## THE RULE THIS DOCUMENT ENFORCES

**Do not write a story the data cannot carry.**

Cedar Press's prime directive is zero fabrication. In an editorial context that has a
sharper edge than it does in a build log, because a published sentence is read by people
who cannot check it. Three specific traps, all of which this project has already walked
into and recorded:

1. **Right arithmetic, right citation, wrong answer.** California's `$19M / 15% = $126.7M`
   was correct arithmetic against a correctly-cited compact rate and was wrong by an order
   of magnitude, because the rate is marginal. A footnote does not save a sentence like
   that.
2. **A stale number reads as an adjudicated one.** `docs/COMPETITIVE_POSITION.md` corrects
   an earlier "687 entities" up to 866 in an authoritative voice; 866 is now two
   generations stale and 1,310 is current. The correction is what makes the stale figure
   dangerous.
3. **A denominator that quietly excludes.** "790 deals" omitted the 131 rows in the two
   root ledgers for three weeks after the defect was identified, because nothing connected
   the fact-check to the documents repeating it.

**Every piece below names the file it is written against, and the date that file was
measured.** A piece that cannot name one is not ready.

---

## THE PUBLICATION CALENDAR, AND THE FINAL-VERSUS-YTD RULE

**Launch: before the end of calendar 2026. Refresh wave: once the year turns.**

This governs how each piece is built, not only when it runs.

### Two clocks, and they are not the same clock

| | status on 2026-08-26 | consequence for a launch piece |
|---|---|---|
| **Federal fiscal year 2026** | **CLOSED 2026-09-30** | An FY-keyed figure covering FY2026 or earlier is final **for its period** — *if we hold the whole period*. See the trap below. |
| **Calendar year 2026** | **open until 2026-12-31** | Any CY-keyed figure is **year-to-date**. It must say so, in the sentence, not in a footnote. |

A reader who cites a number in December and finds it different in February has been
failed — *unless we told them it was YTD*. That is the whole rule.

### ⚠ THE TRAP: A CLOSED FISCAL YEAR IS NOT A HELD FISCAL YEAR

**FY2026 closed on 2026-09-30. Cedar Press's assistance data stops on 2026-06-30.**

Measured 2026-08-26 on `data/clean/federal_funding_transactions.csv`: max `action_date`
is **2026-06-30**, and all **24,895** FY2026 rows carry `fy_partial_flag = 1`. The fiscal
year being closed at Treasury says nothing about whether our pull covers it. Roughly one
quarter of FY2026 is simply absent.

So the operative rule is stricter than "FY2026 is final":

> **The last publishable complete fiscal year is the last one whose max `action_date`
> equals `<year>-09-30`.** For federal funding that is **FY2025**. Check it per dataset;
> do not assume it.

Practically, for a launch piece: **lead on FY2025 as the last closed year, and state
FY2026 as partial-through-June if you state it at all.** Naming FY2026 as final on data
that stops in June is exactly the failure this document exists to prevent — and it would
be a *self-inflicted* one, because we know the endpoint.

A second, subtler version of the same trap sits in `data/clean/coverage_audit.csv`
(rebuilt 2026-08-26, otherwise correct): its `date_column` is **`action_date`** for
`federal_funding` and `faads` but **`fiscal_year`** for `prime_contracts`. Reading one
row of each off that file as "the same year" compares a calendar year to a fiscal year —
a 6,570-row and $5.03B difference in 2026 alone. **Never build a cross-collection year
chart off that file without normalising the basis first.**

### What every piece must record, explicitly

Two lists, written into the piece's own working notes before drafting:

- **FINAL** — figures complete for their period and stable across the year turn.
- **WILL MOVE** — figures that are year-to-date, or sit on a dataset whose next pull
  extends it. Name the expected direction (these only ever grow) and the refresh trigger.

### Structure for update, not rewrite

The product already supports this. A Collection descriptor carries `vintage`, `version`
and `updated`, and `pressReleases.js` is the release ledger a download is cited against.
**Every piece names the release it was written against.** Then the year-turn refresh is a
version bump and a paragraph, not a new article.

Practically: put the moving figures in a small number of named places — a lead stat block,
one chart, one closing table — and keep the argument in prose that does not restate them.
An article whose thesis is "the composition is X" survives a refresh. An article whose
thesis is "the number is N" does not.

### Which collections gain most at the year turn

Measured 2026-08-26 from `docs/SHIP_GAP_REPORT.json` and the underlying files.

All endpoints below were measured from the real content date column on 2026-08-26 — not from
a build date, and not from the ship-gap detector's heuristic date pick.

| Collection | real endpoint | year-turn gain | why |
|---|---|---|---|
| **lobbying** | `dt_posted` **2026-08-04**; CY2026 = **643 filings** (Q1 331 · Q2 311 · **Q3 1**) | **LARGE** | Q3 has barely posted and Q4 posts in January. **2026 will roughly double.** |
| **legislation** | bills freeze **2026-04-16**; roll calls end **2025-05-06**; 119th holds **1 roll call** | **LARGE** | The stalest endpoint in the slate, four months behind everything else. The 119th does not close until January 2027. |
| **subcontracting** | `subaward_date` **2026-08-03**; 2026 = **3,457 rows** | **LARGE** | And larger still if the upstream FY2021–24 outage resolves. |
| **deals** | `Event_Date` **2026-08-20**; 2026 = **91 rows** | **LARGE** | Four months of 2026 uncaptured. |
| **contractors** | prime FY2026 cut at `action_date` **2026-07-03** — a **nine-month partial** | **MODERATE** | Plus FPDS restates retroactively up to five years, so even closed years drift slightly. |
| **funding** | `action_date` **2026-06-30**; FY2026 = 24,895 rows, **all `fy_partial_flag = 1`** | **MODERATE** | **A full quarter of the closed FY2026 is missing.** See the trap above. |
| **federal-register** | `publication_date` **2026-08-05** (ex parte to **2026-08-24**); 2026 = 3,454 docs | **MODERATE** | A January re-pull completes CY2026. |
| **nagpra** | **2026-08-03**; 2026 YTD = **570 notices** | **MODERATE — and newsworthy** | 2026 is the first full post-deadline year under 43 CFR part 10. It deserves its own follow-up piece, not a silent refresh. |
| **gaming** | CA `period_end` **2026-06-30** · digital **2026-06-30** · compacts **2026-04-14** · ordinances **2026-02-12** | **MIXED** | The payment and digital series move quarterly and monthly. The facility universe does not — it has a different problem, below. |
| **natural-resources** | ONRR monthly **2026-06-30** · ND **2026-07-22** · MT **2026-03-31** · Osage headright **2026Q2** | **SMALL** | State royalty and severance reporting is annual and lags. |
| **nonprofits** | Schedule I `tax_period_end` **2025-12-31**; grantmaker **2025-11-30** | **NONE — and say so** | **990 filings lag ~18 months structurally.** Worse: TY2025 is *present but 1–43% populated* — `grantmaker_funding_flows` TY2025 is **128 rows from ONE return (1.3%)**. **Quote TY2023/TY2024. Do not promise a February refresh.** |

### Collections that will look STALE at launch unless refreshed first

| table | latest content date | reads as |
|---|---|---|
| `gaming_facilities` / `gaming_properties` | `open_date` max **2025-07-23** | ends 2025 |
| `gaming_property_capacity_history` (vendor) | **2023-01-01** | ends 2023 — *cannot be published anyway* |
| `gaming_mitigation_agreements` | `effective_date` max **2024-01-10** | **ends 2024** — two years stale at launch |
| `bill_votes` | roll calls end **2025-05-06** | ends 2025 |
| `native_bills` | freezes **2026-04-16** | four months stale |
| Osage newsletter series | **2022Q1** — two newsletters 404 | **STALLED, not YTD.** Different fact; say which. |

Two honest options per row, and only two: **refresh it before launch**, or **state the
endpoint in the piece**. There is no third option where the piece is silent about it.

### One more distinction the launch copy must not blur

**A channel endpoint is not a data endpoint.** The deals channel was swept through
**2026-08-22**; the latest deal in the file is dated **2026-08-20**. Both are true, they are
different facts, and **the publishable one is the data endpoint.** The same shape appears in
`funding` (archive cut vs fiscal-year close) and in `contractors` (archive object cut at
2026-07-03 vs FY2026 closing 2026-09-30).

---

## PRIOR ART — SCAN LANDED. READ `docs/PUBLISHED_LANDSCAPE_2026-08-26.md` BEFORE DRAFTING.

**The landscape scan is complete** and lives at `docs/PUBLISHED_LANDSCAPE_2026-08-26.md`
(1,484 lines, swept 2026-08-26). It covers published research and public data products —
CICD, NNI, NBER, Harvard Project, NAFOA, NCAI, NCAIED, First Nations, Oweesta, USET, GAO,
CRS, OMB, SBA, BIA, Census, and the trade press. **It supersedes the empty slot this
section used to hold.**

### ⚠ HOW TO USE IT — the owner's direction, 2026-08-26

> **The scan is for avoiding redundancy and citing prior work properly. It is not a
> foil.**
>
> **Do not organise any piece as a response, comparison, or corrective to CICD.** The owner
> built CICD's datasets himself and reads their 2026-08-24 federal contracting article as
> largely a synthesis of his own prior work with a couple of new insights. He is a named
> co-author on three CICD publications and a fourth Harvard co-authorship. **Positioning
> against CICD would be positioning against his own record.** They are a sanity check on
> arithmetic. Nothing in this document should read as a rebuttal.
>
> **And the entity-spine derivation question is CLOSED.** See `OWNER RULING 2026-08-26` at
> the end of the scan. The spine's relationship to CICD's Native Entity Connector Crosswalk
> is an **input, not a blocker**: the entities are public facts (Federal Register list,
> ANCSA statute), Cedar Press has its own identification system and has more than doubled
> the universe **687 → 1,489** including classes CICD's file does not carry at all, and NEED
> is not accessible at entity level by written policy. **The only action is one line on the
> methods page crediting the crosswalk as an input — a courtesy and a positioning move, not
> a legal or ethical requirement. Do not surface this question in any piece, and do not
> re-open it.**

### ⚠ SECOND OWNER DIRECTION — comparison to non-Native entities is DEPRIORITISED

**A story whose spine is "Native versus non-Native share" is not a launch piece.** It can be
added later; it is not important right now. **Rank those below anything that stands on
Cedar Press's own measurements.** Two pieces in this document were re-ranked on this
instruction — see `legislation` (the 2.24× enactment ratio, demoted to queue) and
`contractors` (the set-aside share, demoted in favour of the undercount).

### The rule, which is not negotiable

**Honor prior work. Never re-claim it.**

This project's prime directive is that it never falsely attributes. That directive is
usually read as being about *entities* — do not attribute Salt River Project's lobbying to
the Salt River Pima-Maricopa Indian Community. **It extends identically to intellectual
credit.** Publishing a finding that CICD, NNI, NBER, USET, GAO or a congressional witness
established first, without saying so, is the same failure with a different object.

Operationally, four cases:

| case | what the piece does |
|---|---|
| **They found it first** | Cite them by name in the text, not a footnote. Our contribution is whatever we *add*. Lead with the addition, not the finding. |
| **They found it and we can extend it** | "X reported N; measured against Cedar Press's series the figure through FY2026 is M." Their number stays theirs. |
| **We found it independently and can show it** | Say so plainly, with our measurement date, and cite theirs anyway. Independent arrival at the same finding is a corroboration. |
| **We contradict them** | Publish both figures, both methods, both sources. `docs/CROSS_SOURCE_VERIFICATION.md`: two sources that disagree is a finding, not a defeat. |

### ⛔ NINE STORIES THAT ARE ALREADY TAKEN — do not lead with any of them

From the scan, §6. Each is published, most with the owner's own name on it:

1. **"Native federal contracting is huge and growing."** CICD, twice, most recently
   2026-08-24. **And $310.01B must never appear beside CICD's $26.6B without the
   definitional reconciliation** — see the `contractors` slate.
2. **"Native primes hire local non-Native small businesses."** CICD 2024-07-16 and
   2026-08-24, with better subaward coverage than our FY2021–24 hole allows.
3. **"Tribal casinos lift surrounding businesses."** CICD WP 2024-02.
4. **"Contracting tribes also tend to be gaming tribes."** CICD 2022, 64.6%. *This is the
   closest published relative of our 3+-dataset corroboration claim — state ours as being
   about **evidentiary independence**, not co-occurrence, or a reader hears an echo.*
5. **"The 8(a) programme drives Native contracting."** CICD 2023 and 2026.
6. **"Federal data on tribes is unreliable."** Akee, Henson, Jorgensen & Kalt 2020 —
   *"None of the publicly available data series are reliable."* **We own the remedy and the
   measurement, not the diagnosis.**
7. **"Tribes own far more businesses than people realise."** CICD NEED 2025-04-15 —
   5,559 establishments, 344 tribes, 425 industries. *Published with the owner's name on
   it.*
8. **Any aggregate tribal gaming revenue figure.** NIGC, republished same-day by two
   outlets. Claim facility-level only.
9. **"Native entities are acquiring companies to grow their federal contracting."** Moreno,
   Dippel & Siken, *Tribal Business News*, 2024-05-05. **Taken by the owner, in the partner
   outlet.** The deals piece pitches as *"an update and expansion of our 2024 analysis"*
   with the full citation.

### ✅ WHAT IS GENUINELY OPEN — and this is what should lead

The scan's three strongest gaps, plus two originals measured during it. **Every launch
ranking below is built on this list.**

| | the gap | why nobody else has it |
|---|---|---|
| **G1** | **The commercial-identity layer — UEI/CAGE/EIN → owning Native entity, published** | CICD's crosswalk stops at government entities; its CAGE list went to HigherGov **unpublished**; NEED links by *name*, not identifier; NBER's entity-level work is locked in a Census RDC. **SBA's own 8(a) page concedes entity-owned firms "may have multiple 8(a) firms" and publishes no parent mapping.** *The void is documented by the agency that created it.* **This is the moat and it is intact.** |
| **G2** | **The SIZE of the self-certification undercount** | CICD called its own hand-built dataset a *"lower-bound estimate"* and never sized the shortfall. Cedar Press holds **both** a flag-based count and a hand-adjudicated ownership count **on the same universe**. *"The only contracting story that is both unclaimed and consequential."* |
| **G3** | **Tribal lobbying, FERC, and the formal federal record** | **ZERO tribal lobbying analysis exists anywhere** — checked across CICD, NNI, NBER, NAFOA, NCAI, NCAIED, First Nations, Oweesta and USET. *"The cleanest gap in this sweep."* Nothing adjacent to 102,615 FERC filings. Nothing structured on NAGPRA at scale. |
| **G4** | **Tribal bond issuance and municipal finance** | **NAFOA — the tribal-finance body itself — has no research function at all**, confirmed four ways. Its only finance publication is an accounting manual. |
| **O1** | **ORIGINAL: tribal governments have no classification in the Census of Governments** | Measured 2026-08-26 across all 463 pages of the Census Bureau's *Government Finance and Employment Classification Manual*: **`tribal` 0 · `tribe`/`tribes` 0 · `Native` 0 · `reservation` 0.** Three incidental `Indian` hits, all federal-agency references. **Reproducible in one command, needs no statutory caveat, and says something structural rather than technical.** |
| **O2** | **ORIGINAL: the FAADS FY2001–06 0.0% rate** | Unclaimed. **But the boundary is statute — see the reframing in the `funding` slate. Measurement keeps, framing goes.** |

**And the first product the scan points to:** *a ranking of top tribal, ANC and NHO federal
contractors, with the ownership chain shown.* Demonstrably unpublished anywhere (checked
across seven outlets), directly producible from the 498-entity attributed set, impossible
for the incumbents by construction — **and already demanded by a public dispute: a U.S.
senator and the Poarch Band fought over whose 8(a) contracts count as whose, and nobody had
a dataset to settle it.** See the `contractors` slate.

### Fourteen claims that must now be CITED rather than originated

Full table at scan §5. The ones that touch pieces in this document:
- **"Per-entity federal assistance cannot begin before FY2007"** → **FFATA §2. Withdraw.**
- **A human-readable Native entity ID scheme (`TRBF-…-00`)** → CICD Native Entity Connector
  Crosswalk, Feb 2026. Credit as an input.
- **CAGE-first linkage of vendors to tribal owners** → CICD 2022 appendix
  (Chavis/Gregg/**Moreno**).
- **"First to link tribal governments to their differently-named enterprises"** → **withdraw
  "first."** USET's *2022 Tribal Enterprise Directory* is the regional precedent. Say
  instead: *first **national, machine-readable, identifier-bearing** tribal enterprise
  crosswalk, corroborated across independent federal datasets.*
- **The count of tribal gaming establishments** → **CRS IF12527**: 243 tribes, **532
  establishments**, $43.9B, Sept 2024. **Reconcile on the same page.**
- **A per-reservation economic compendium** → Akee, **Moreno** & Besaw-Medford, *Databook*
  3rd ed., HPIGD, Sept 2025. Cedar Press is the **entity/enterprise layer** that the
  Databook's **place layer** cannot reach.
- **Aggregate Native M&A in federal contracting** → **Moreno**, Dippel & Siken, TBN,
  2024-05-05.

### The best available opening line, and it is not a dollar total

**CRS IF12612** records that BIA's *American Indian Population and Labor Force Report* ran
**1982–2013 and stopped**, and that tribal service population data *"are not publicly
available below the national level."* Paired with **O1** — the United States runs a census
of its governments and does not count tribal governments in it — that is the launch essay's
opening. **The federal government abandoned this field.** Cite IF12612 as the authoritative
acknowledgment; do not re-derive the claim.

---

## THE ARCHITECTURE CLAIM — MEASURED, AND CORRECTED

The claim carried into this task was *"458 entities corroborated by 3+ independent
datasets."* **That figure does not reproduce.** Measured 2026-08-26 against
`data/clean/entity_evidence_profile.csv`:

| independent sources naming the entity | entities |
|---|---:|
| ≥ 2 | **685** |
| **≥ 3** | **516** |
| ≥ 4 | **432** |
| = 12 (the maximum observed) | **13** |

All 516 are in the spine. `458` appears elsewhere in the repo attached to two different
objects — "458 lobbying clients settled" (`docs/handoffs/STATE_OF_BUILD.md` line 133) and "600 party
rows / 458 distinct pairs" (`docs/LOBBYING_EXPANSION_RECONCILIATION.md` line 282) — and
neither is the corroboration count. **Use 516, and re-measure before publishing.**

**And the file itself is stale in the conservative direction.** It carries
`built_date = 2026-08-12`. Since then `deals_classified.csv` entity links went 752 → 886
and `ferc_docket_filings.csv` links went 581 → 1,107. The true figure today is ≥ 516.
`code/151_rebuild_entity_evidence_profile.py` regenerates it, reads only, and should be
run before this number is printed anywhere. *(This agent did not run it — the constraint
was to modify no dataset.)*

### Why no federal source can compute this

The nineteen sources counted are independent record systems with no shared key: FPDS keys
on UEI, USAspending assistance on a recipient identifier that does not exist before FY2007,
the LDA on a filer-declared client string, the FR on nothing at all, IRS 990 Schedule I on
EIN, the FAC on an auditee identifier, NIGC and the state gaming regulators on tribe name
as typed. **The join is the product.** No agency has the mandate to build it, and the
identifier ledger that makes it possible is 20,559 rows of which only **1,538 are
`tier_A_ruled`** — hand-checked, not inferred.

### ⚠ THE SPINE MOVED UNDER THIS DOCUMENT WHILE IT WAS BEING WRITTEN

`docs/DOC_CONTRADICTIONS_2026-08-26.md` records **1,310 entities / 16 classes** as ground
truth and lists four live values for the spine count (687 · 866 · 952 · 1,310), naming
1,310 as the only current one.

**Measured directly from `data/spine/cedar_entity_spine.csv` at 2026-08-26: 1,489
entities, 16 classes.** The difference is almost entirely **Native Hawaiian Organizations,
now 210 against the 31 recorded in the contradictions register** — the NHO promotion
listed as RUNNING in `docs/WORK_QUEUE.md` has been landing during this session.

| entity_class | n |
|---|---:|
| Federally recognized tribe | 349 |
| Federally recognized Alaska Native Village | 228 |
| **Native Hawaiian Organization** | **210** |
| BIE School | 185 |
| Alaska Native Village Corporation | 173 |
| State-recognized tribe | 64 |
| Native CDFI | 64 |
| Intertribal Organization | 55 |
| Urban Indian Organization | 43 |
| Tribal College or University | 37 |
| Native Financial Institution | 29 |
| Federal-level constituency entity | 22 |
| Alaska Native Regional Corporation | 12 |
| Federal-level self-governance consortium | 9 |
| ANCSA Group Corporation | 6 |
| State-level constituency entity | 3 |

**There are now five live values for the spine count, and this document's own is the
fifth.** That is the strongest possible illustration of why every figure here carries a
date — and it is a hard instruction to whoever writes the entity-architecture piece:
**re-measure the spine on the morning you draft, and again on the morning you publish.**
Do not inherit 1,489 from this line.

The thirteen entities visible in all twelve sources, 2026-08-26: Coeur d'Alene,
Confederated Colville, Confederated Yakama, Eastern Cherokee, Menominee, Mississippi
Choctaw, Navajo, Seneca, Muscogee (Creek), Umatilla, Ute Mountain, Warm Springs,
Winnebago.

### The rule that must travel with this number

`code/151_rebuild_entity_evidence_profile.py` refuses to sum dollars across sources, and
the article must refuse too. A prime-contract obligation, a 990 grant received, a resource
royalty and a compact payment are **different concepts pointing in different directions**.
The output column is literally named `amounts_per_source_NEVER_SUM`. A piece that
aggregates them invents a number no source reports — and it would look extremely
well-sourced.

Second rule: **a source is evidence that a record exists, not that an entity is Native and
not that an attribution is correct.** Appearing in IBIA as an appellant proves an appeal.
Tier stays with the ledger.

---

## THE REFUSALS — INDEX

*The full section is at the end of this document. Indexed here because these are the
strongest publishable material in the project and they belong to no single shelf — the
slates cross-reference them by number.*

| # | the refusal | shelf |
|---|---|---|
| **R1** | California: zero derived revenue rows, because every rate is marginal — the $126.7M that would have shipped with a correct citation | gaming |
| **R2** | Florida: a bound built, published in a draft, then killed by the publisher's own Net Win | gaming |
| **R3** | The Single Audit reversal — a dead end recorded from one auditee's election | gaming / cross |
| **R4** | 415 gaming dates wearing a day of the month they never had | gaming |
| **R5** | A fiscal sponsor is not the project it sponsors — $43.5M that would have looked well-sourced | nonprofits |
| **R6** | $56B of real records a plausible cleaning step would have deleted | funding |
| **R7** | A guard that discloses it refuses true attributions — $5.95B withheld | funding |
| **R8** | Three states that look identical in a coverage table and are opposite findings | cross |
| **R9** | The substring that would have mistyped 616 Surface Transportation Board documents | federal-register |
| **R10** | A classifier that invented a NAGPRA collapse that never happened | nagpra / FR |
| **R11** | A finding reported because it was the prior, and it is not supported | lobbying |
| **R12** | Casino City: a source we read and will never publish | gaming |
| **R13** | A characterisation we would be authoring — why `position_on_native_issue` does not exist | lobbying |
| **R14** | The empty review file that was deliberately not written | subcontracting |
| **R15** | A $10 discrepancy killed a fiscal year | natural-resources |
| **R16** | A dedupe that would have destroyed $10.8 billion | natural-resources |

---

## HOW TO UPDATE THIS DOCUMENT

It is structured to be edited by section, not rewritten. Four rules:

1. **Update the header date whenever you touch anything.** `Last reviewed:` at the top.
2. **A slate section is self-contained.** Each has the same four blocks — *What the data
   can support today* (a measured table), *★ LAUNCH PIECE*, *QUEUE*, *refusals*. Rewrite a
   block; do not restructure the section.
3. **When a figure moves, restate it with the new date and strike the old one in place** —
   the same convention `START_HERE.md` and `docs/COMPETITIVE_POSITION.md` use. Do not
   silently overwrite. In an editorial document, *why* a figure moved is often the story.
4. **A piece is promoted out of QUEUE into ★ LAUNCH only by a measured upgrade**, and the
   section must say what changed: a new pull landed, a review queue cleared, a ruling
   applied, an error rate re-audited. "It feels stronger now" is not an upgrade.

**One structural warning.** Nothing in `dist/` is currently a data artefact — every
`dist/<group>/` directory holds only `.notes.json` and `.NOTES.md`, and `dist/` has not
been rebuilt since 2026-08-12. The project ship ratio measured 2026-08-26 is **66.7%**
against the notes contract, with **201 of 255 tables at 0%** and **2,609,646 unshipped
rows** (`docs/SHIP_GAP_REPORT.json`, `healthy: false`). **An article can be written
against `data/clean/`; a download the article points a reader at cannot.** Every launch
piece therefore has a shipping dependency as well as an editorial one, and the ranking at
the end of this document scores both.

---

# THE ELEVEN SLATES

*One designated **LAUNCH** piece per Collection, then a **QUEUE** of additional candidates
ranked by strength. Where a Collection cannot honestly carry a piece today, it says so and
names exactly what it needs.*

Format vocabulary used below:
- **web** — ≈800-word web article. One claim, one chart, one table, a named source.
- **paper** — research-paper-oriented longer piece. Method section, audited error rate,
  refusals published alongside the finding.
- **brief** — under 400 words plus one exhibit. Used for monthly cadence, not launch.

Confidence vocabulary:
- **HIGH** — figure reproduces from the file today; method survives its own audit; no
  known contradiction in `docs/DOC_CONTRADICTIONS_2026-08-26.md`.
- **MEDIUM** — figure reproduces but rests on one source, or on a classifier with a
  published error rate that materially bounds the claim.
- **LOW** — the shape of the finding is real; the level is not publishable without more
  work. Listed so it is not lost, not so it ships.

---

<!-- SLATE:funding -->
## 1. `funding` — Federal Funding to Indian Country · shelf `standard`

### What the data can support today

*All figures measured 2026-08-26.*

| | |
|---|---|
| `data/clean/federal_funding_transactions.csv` | **684,923 rows**, FY2007–FY2026, `action_date` **2006-10-01 → 2026-06-30**, **$211,999,072,509** obligated |
| entity-linked | **536,023 rows (78.26%)** · **$163,271,990,428 (77.02%)** |
| `data/clean/faads_transactions_all_agencies.csv` | **2,769,748 rows**, FY2001–FY2007, **$1,830,639,317,708**, `tribe_id` non-blank on **0 rows** |
| `data/clean/faads_entity_attribution.csv` | **29,594 transactions**, **686 entities**, $4,951,906,323 gross / **$4,721,685,550 net**, **tier B on every row** |
| last complete fiscal year held | **FY2025** — 44,471 rows / $16,674,151,861 |
| FY2026 | **24,895 rows / $12,120,704,679, partial through 2026-06-30 only** |

**One caution that governs every entity claim in this collection.** The "1,011 distinct
entity ids" in the transactions file is **not 1,011 entities**. `tribe_id_scheme` splits
the file into two disjoint namespaces — `lineageA_dofile_integer` (365,535 rows, 361 ids,
a bare 1–381 integer local to a do-file) and blank-scheme (319,388 rows, 650 spine/ledger
ids). The two sets do not overlap at all; 361 + 650 = 1,011 exactly. `tribe_id_neid` is
non-blank on **0 of 684,923 rows**, deliberately — the NEID crosswalk is a ruling, not a
computation. **A per-entity ranking across the whole file is not supported today.**

---

### ★ LAUNCH PIECE — *Congress said the record starts in FY2007. Nobody measured what the years before it actually contain. We did: 0.0%.*

**Format:** paper (with an 800-word web companion). **Confidence: HIGH on the measurement.
The framing was rebuilt 2026-08-26 — read the withdrawal notice first.**

### ⛔ FRAMING WITHDRAWN 2026-08-26 — the measurement keeps, the framing goes

This piece was previously titled *"Per-entity federal assistance cannot begin before FY2007,
and no federal source says so,"* and that sentence **must not be published.** It is the
plain text of the enabling statute:

> **Federal Funding Accountability and Transparency Act of 2006**, P.L. 109-282 §2 —
> *"The website shall include data for **fiscal year 2007, and each fiscal year
> thereafter**"*, and must carry *"a **unique identifier of the entity receiving the award**
> and of the parent entity."*

**FY2001–06 FAADS has no recipient identifier because no law required one.** Publishing the
boundary as a discovery would be *"the single most damaging credibility error available at
launch — a reviewer who knows FFATA will discount everything else on the page"*
(`docs/PUBLISHED_LANDSCAPE_2026-08-26.md` §7).

**What survives, intact and unclaimed: the RATE.** No GAO, CRS, OMB, Treasury or Census
document reached in the sweep states that FAADS carries a recipient identifier on 0.0% of
FY2001–06 rows. **That measurement is Cedar Press's.**

**Use this wording, from the scan, not the old sentence:**

> FFATA required USAspending to carry *"a unique identifier of the entity receiving the
> award and of the parent entity"* and provided that *"the website shall include data for
> fiscal year 2007, and each fiscal year thereafter"* (P.L. 109-282 §2). CRS accordingly
> reports that USAspending search *"enables searching of federal awards from FY2008 to the
> present"* while *"custom award data are available going back to FY2001"* (CRS R44027) —
> **and does not explain what that earlier tier contains.** We measured it: across 2,769,748
> FAADS rows for FY2001–07, the recipient identifier is populated on **0.0% of rows**. The
> pre-FFATA tier is not a thinner version of the modern record; it is a structurally
> different record supporting programme-level totals only. OMB conceded in 2008 that *"much
> of the data submitted in the past has been incomplete, untimely, and inaccurate"*
> (GAO-06-294). **We quantify what "incomplete" meant for entity attribution.**

**Four citations are now unavoidable and belong in the text:**

| source | what it does for the piece |
|---|---|
| **P.L. 109-282 §2** (2006) | **The boundary. Concede it in the first paragraph.** |
| **CRS R44027**, *Tracking Federal Awards*, upd. 2026-05-21 | **The opening.** States the FY2008-search / FY2001-custom-download seam and **never mentions FAADS, DUNS or the UEI, and never explains the asymmetry.** |
| **CRS RL34718**, *FFATA: Implementation*, 2009-02-03 | **NEAREST MISS — cite and distinguish explicitly.** *"Similar problems have been reported with FAADS…"*; GAO reviewed 86 grant programs and found *"no data, incomplete data, or inaccurate data"* in the majority. **Qualitative, unquantified, and about subrecipients and congressional district — not the recipient identifier.** |
| **GAO-06-294** + OMB's March 2008 response | Supporting authority, not a competitor. **OMB conceding the defect without quantifying it.** |

Also worth one sentence: **Census's FAADS program page now 301-redirects to
usaspending.gov**, so no contemporaneous record layout survives at the canonical path.
*That absence is why nobody has checked.*

**⚠ AND ANSWER THE FY2007 OVERLAP BEFORE ANYONE ASKS.** Cedar Press describes its holdings
as *"684,923 assistance rows FY2007–2026 **plus** 2,769,748 FAADS rows FY2001–07."* Both
tiers include FY2007. **The first reviewer question will be whether they double-count in the
overlap year. Put the de-duplication statement in the codebook, not in a reply.**

**The claim, restated.** Anyone building a per-recipient history of federal assistance to
Indian Country hits a statutory floor at FY2007. What nobody had measured is how absolute
the floor is: the pre-2007 data is *there*, in volume — 2.77 million transactions and $1.83
trillion — and it carries a recipient identifier on 0.0% of rows.

**The evidence.**
- FAADS FY2001–FY2007 holds **2,769,748 transactions and $1.83 trillion** of federal
  assistance. `data/clean/faads_transactions_all_agencies.csv`.
- `data/clean/faads_identifier_coverage_by_agency_year.csv` reports `pct_with_duns` and
  `pct_with_uei` at **0.0 on all 66 FY2001–FY2006 agency-year cells** — eleven agencies
  (HHS, Education, HUD, USDA, DOJ, DOL, EPA, DOT, Energy, Commerce, Interior), no
  exception.
- The floor lifts abruptly in **FY2007**: **87.38% DUNS, 78.04% UEI** file-wide across
  774,755 rows. Two agencies do not participate in the lift — **DOT at 0.7% and Interior
  at 0.0%** — which matters more for Indian Country than for anyone else.
- Two genuinely independent confirmations, documentary and empirical
  (`docs/FAADS_FEASIBILITY_2026-08-05.md` §3): the Census FAADS record layout **has no
  DUNS/EIN field at all** — *"FAADS 'does not currently collect DUNS information for
  recipients of Federal assistance'"* — and *"across 60,661 Department of the Interior
  assistance transactions FY2001–2007, `recipient_duns` and `recipient_uei` are populated
  on 0 rows — 0.0%."*
- A sweep of USAspending's About-the-Data corpus, Treasury guidance and four GAO reports
  (**GAO-18-138, GAO-20-75, GAO-22-104702, GAO-10-365**), extended 2026-08-26 across GAO,
  CRS, OMB, Treasury, Census, SBA and the FFATA/DATA Act implementation record, **found no
  authoritative statement of the RATE.** *(It did find the boundary — see the withdrawal
  notice above. The two halves of the old claim have opposite verdicts.)*

**Two corrections that must be made before this ships — both are ours.**

1. **"No row carries a recipient identifier before 2007" is literally false.** Measured
   against the raw file, **65 of 1,994,993 FY2001–06 rows (0.00326%) carry a non-blank
   `recipient_duns` or `recipient_uei`** — DOT 29, HHS 27, DOJ 6, USDA 2, HUD 1. **Two of
   them are tribal**: SOBOBA BAND OF LUISENO INDIANS, DOJ, FY2003 and FY2004, DUNS
   `172695025`, UEI `VKLKM9Y78228`. The coverage file's own
   `pct_with_duns_tribal_rows_only` already leaks this — DOJ 2003 and 2004 read **0.2**,
   not 0.0. `docs/COVERAGE_AUDIT.md` currently says *"No row carries a recipient
   identifier before 2007"* and that sentence is the first thing a fact-checker will test
   with a `notnull()` filter. **Publish "0.0% at one-decimal precision; 65 rows in two
   million, two of them tribal" — which is a better sentence anyway, because the exception
   proves the field existed and was almost never populated.**
2. **"Measured two independent ways" overstates what was done.** The source documents say
   *"two independent **routes**"*, and that control (`FUNDING_PRE2008_BUILD_LOG.md` §4)
   compared a generated `bulk_download` job against the static Award Data Archive for
   **Interior FY2007** — identical results, 9,662 rows / 0.0% DUNS / 841 tribal-flagged /
   $1,466,244,955 — which is a *retrieval-route* equivalence check on FY2007, not two
   measurements of FY2001–06. The genuinely independent pair is the documentary +
   empirical pair in item 4 above. Say that one.

**Why the rate is still a Cedar Press original.** CRS states the FY2008/FY2001 seam and does
not explain it. OMB conceded the data was "incomplete" and never quantified it. **We
quantify what "incomplete" meant for entity attribution** — and that is a narrower, harder,
and more defensible claim than the one it replaces.

**What would make it stronger.**
- ~~Log the GAO/Treasury sweep.~~ **DONE 2026-08-26** — `docs/PUBLISHED_LANDSCAPE_2026-08-26.md`
  §7 carries the four citations with roles assigned. The unlogged-negative-search weakness
  is closed, and closing it is what produced the withdrawal.
- **Write the FY2007 de-duplication statement into the codebook.** It is the one open
  vulnerability left in this piece.
- Extend the agency-year coverage table through FY2010 to show *when each agency*
  crossed, not just that the corpus did. DOT and Interior are the interesting laggards.

**FINAL vs WILL MOVE.** Everything in this piece is **FINAL**. FAADS FY2001–2007 is a
terminal historical series and nothing in it moves at the year turn. That is unusual in
this slate and it is a reason to lead with it.

---

### QUEUE — additional `funding` candidates, ranked

**F2. The $41B nobody counts as one thing: tribal self-governance.** *(web · MEDIUM,
upgradeable to HIGH)*
`docs/SUBSET_DATASETS.md` records three programmes that are one story — 93.210 IHS Tribal
Self-Governance ($27.25B), 15.022 Tribal Self-Governance/Interior ($5.71B), 93.441 Indian
Self-Determination ($7.98B) — **≈$41B**, the largest single story in Native federal
finance, currently buried inside a 684,923-row transaction file. **Blocker: those figures
were measured on the pre-backfill file and must be re-measured against the current
684,923 rows before publication.** Once re-measured this is arguably a stronger launch
piece than F1 for a *subscriber* audience, because it is money rather than metadata.

**F3. What a name can and cannot buy you.** *(paper · HIGH)*
`faads_entity_attribution.csv` recovers **29,594 transactions / $4.72B net / 686
entities** from the pre-2007 void **by name**, and it is **tier B on every row and may
never be promoted**, because *"a name is not an identifier."* The audit is the story: 60
distinct (name, state) → entity pairs, `random.seed(60806)`, **3 wrong in 60 — a 5.0%
false-positive rate, published as-found**, with the explicit refusal to re-score the same
sample after fixing what it found. **3,669 refusal records** sit in
`review/faads_attribution_refusals_2026-08-06.csv`. This is a methods paper about the
price of name matching, and the 5% is the point, not the embarrassment.

**F4. The guard that refuses true attributions on purpose.** *(web · HIGH)*
The state-agreement guard withholds **12,987 rows / $5,946,365,640 across 190 recipient
names** (measured 2026-08-26) from Native totals. The lead example: SANTA CLARA COUNTY
HOUSING AUTHORITY (CA) was proposed for Pueblo of Santa Clara (NM) at **$1,782,219,598
across 389 rows**. And the guard discloses that it over-refuses — Navajo Technical
University (NM) under Navajo Nation (spine state AZ), **$73.9M**, almost certainly correct
and withheld anyway. *"A conservative refusal that lands in a queue is recoverable; a
false attribution that ships is not."*
**⚠ The published bound is stale**: `docs/ASSISTANCE_ARCHIVE_PULL_LOG.md` FINDING 3 says
*"99 recipients, 3,293 rows, $2,503,254,778"*. The backfills grew it and the doc was never
updated. **Quote $5.95B / 12,987 / 190, dated.**

**F5. Half of a $67B "overcount" was a guess.** *(paper · HIGH, internal-facing but
publishable)*
A dedup pass removed $67B. Re-examined: only **9.8% ($6,583,322,777 / 6,295 rows)** is a
demonstrable duplicate. **83.7% ($56,267,946,786 / 15,642 rows)** is *"the same award seen
through two different observation windows at two different cumulative amounts; deleting
the smaller one is a guess, not a dedup."* Two upstream claims failed to reproduce — the
asserted cross-source median ratio of 1.00 is actually **0.8687**, and only **28.3%** are
exact. The max-keeping reducer is now prohibited by rule. This is a story about how a
plausible cleaning step destroys $56B of real records.

**F6. A finding that was killed for being an artifact.** *(brief · HIGH)*
"Coverage thins after 2022" — a 592 → 409 → 539 → 465 tribe-row collapse — **is an
artifact of `first_seen_year`**. On a true fiscal-year basis the same data gives 598 / 535
/ 554 / 550 for 2022–2025: a mild decline consistent with a partial year, not a 31% cliff
and rebound. Short, and it pairs naturally with F5 as a two-part "things we nearly
published" piece.

**F7. LOW — the two panels are stale and must not be published.**
`federal_funding_tribe_year_panel.csv` (5,496 rows, FY2008–FY2023, 359 tribes, $107.05B)
and `entity_year_panel.csv` (12,534 rows, 1999–2026, 659 entities) **both pre-date the
2026-08-12 archive backfill** and no longer agree with the transactions file they derive
from. Any per-tribe time-series piece needs them rebuilt first. Listed so the idea is not
lost; not shippable.

### The `funding` refusals worth publishing

- The $67B that was not an overcount (F5).
- The $5.95B the guard withholds, **including the true attributions it refuses** (F4).
- **Lineage B killed as a dollar source.** *"The two lineages are not two datasets. They
  are two treatments of one file."* — byte-identical md5 `5414c27e9620fc90c8c3b0f1c9204e64`
  in both trees. There is no independent second source of assistance dollars to reconcile
  against, and the reconciliation exercise's own premise died.
- **Automated name matching killed at the merge layer.** *"`cluster_v3` is never
  auto-accepted — Elijah's rulings have run 9-for-0 against automated name matching."*
  975 UEIs sit unruled in `review/funding_tribe_candidates_2026-08-05.csv`; 55,443 Alaska
  rows are retained but unattributed by construction.
- **A source do-file that does not reproduce its own output**, with $1.06B of Oneida money
  turning on it. Internal, but it is the best available argument for why the identifier
  ledger has to be hand-ruled.

### Documentation defects to fix before any `funding` piece ships

1. `docs/COVERAGE_AUDIT.md` — *"No row carries a recipient identifier before 2007"*. False;
   65 rows do.
2. `docs/ASSISTANCE_ARCHIVE_PULL_LOG.md` FINDING 3 — the $2.5B bound is now $5.95B; all
   four `population_basis` counts are stale.
3. `docs/FEDERAL_FUNDING_MERGE_LOG_2026-08-05.md` — *"every FY2023 row carries
   `fy_partial_flag=1`"*. Only 15,141 of 49,652 do; **FY2023 is now a complete fiscal
   year** and the partial-year caveat should be repointed at FY2026.
4. `START_HERE.md` line 151 — *"`coverage_audit.csv` is stale and must not be quoted"*.
   **No longer true**; it was rebuilt 2026-08-26 and reproduces. START_HERE is now the
   stale document on this point.

---

<!-- SLATE:federal-register -->
## 2. `federal-register` · shelf `standard`

### What the data can support today

*Tier counts re-verified against `data/clean/fr_content_classification.csv` on 2026-08-26.
Audited accuracy figures are from `docs/CONTENT_ANALYSIS.md`, built 2026-08-06 by
`code/78_content_analysis.py` and regenerable by it.*

| | |
|---|---|
| `data/clean/federal_actions.csv` / `fr_content_classification.csv` | **156,452 documents** (156,452 unique `document_number`, no duplicates) |
| real date column | **`publication_date`**, span **1994-01-03 → 2026-08-05** |
| `title_subject` (Native term in the title) | **9,523 · 6.087%** ✅ |
| `abstract_subject` (Native term in the abstract only) | **12,855 · 8.217%** ✅ |
| `weak_term_only` (*reservation*, *Pueblo*) | 1,110 · 0.709% ✅ |
| **`body_only_unverifiable`** | **132,964 · 84.987%** ✅ |
| **names a tribal term in its own title or abstract** | **22,378 = 14.3%** — see the correction below |
| corpus-weighted classifier accuracy | **91.8%**, precision 0.68, recall 0.73 (n=120, `AUDIT_SEED = 20260806`) |
| **genuinely about Indian Country, estimated** | **20,842 documents — 13.3%** |
| agencies | 333 distinct agency strings (6,756 rows carry none). Interior 26,838 · EPA 25,724 · HHS 11,765 · DHS 11,445 · Energy 11,103 |
| document types | Notice 89,273 · Rule 39,710 · Proposed Rule 23,690 · Uncategorized 2,866 · Presidential 834 |
| 2026 to date | **3,454 documents**, max `publication_date` **2026-08-05** |

**⚠ CORRECTION: the number is 14.3%, not 14.2%.** (9,523 + 12,855) / 156,452 =
**14.3034%**, and the rounded components sum to 14.3 as well. The tier counts reproduce
exactly and match `data/clean/_content_analysis_stats.json`, so this is an arithmetic slip
in `docs/CONTENT_ANALYSIS.md` propagated into `docs/COMPETITIVE_POSITION.md`, not a data
change. **Fix it in the launch copy and in both source documents.**

**⚠ A YEAR CURVE DEFECT NOBODY HAS EXPLAINED YET.** 2023 = 6,295 · **2024 = 7,068** ·
**2025 = 5,283**. A 25% drop into a *complete* calendar year is either a real regulatory
volume drop or a pull artefact, and nothing on disk says which. **Do not publish a "federal
attention to Indian Country is rising" trend until 2025 is resolved.** Years 1994–2024 are
final; 2025 is complete-but-anomalous; 2026 is YTD through 2026-08-05.

**The single most important sentence in this slate:**

> **Never publish "156,452 federal actions affecting tribal nations."**

The corpus is a full-text keyword net. A document enters if the word "tribal" appears
anywhere in it, and Cedar Press holds `title`, `abstract`, `action` and `dates` — **not
body text**. Randomly drawn `body_only` documents from the audit sample include
*Establishment of the Waco Mammoth National Monument*, *Safety Zone; Hilo Harbor*,
*US Savings Bonds Series I*, and *Chromium Electroplating Emission Standards*.

---

### ★ LAUNCH PIECE — *We counted 156,452 federal documents about Indian Country. About 20,800 of them actually are.*

**Format:** paper, with an 800-word web companion. **Confidence: HIGH.**

**The claim.** The standard way to build a "federal actions affecting tribes" corpus —
full-text keyword search — produces a number roughly seven times too large, and the error
is invisible from inside the corpus. Cedar Press measured its own, published the error
rate, and refused to headline the big number.

**The evidence.**
- The tier table above, with **85.0% of the corpus carrying no Native term in any field we
  hold**.
- A hand-coded stratified sample of 120 documents, frozen classifier, frozen seed,
  reweighted to the corpus: **91.8% accuracy, precision 0.68**. Errors were **reported,
  not patched** — *"tuning a classifier against its own audit sample converts a
  measurement into a claim."*
- The false positives are the fun half and they are all place names: *Indian Point Nuclear
  Generating Unit No. 3* (New York), *Radio Broadcasting Services; Indian Wells, CA*,
  *Indian River Lagoon South Project* (Florida), *Oak Ridge Reservation* (a DOE site).
- **The false negatives matter more**, and this is the part that lifts the piece above
  methodological throat-clearing: *Proclaiming Certain Lands … as an addition to the
  Pueblo of Laguna Reservation* (a fee-to-trust action), *Transfer of Excess Property —
  Cherokee Nation*, the *Osage Negotiated Rulemaking Committee*, and the Four Corners /
  Navajo Generating Station air rules. **All squarely Indian Country. All missed.**
- Honest self-report: the `abstract_subject` tier is the weak one — barely half its
  sampled documents are genuinely tribal-subject, because *"State, Tribal, and Federal
  agencies are invited to comment"* is boilerplate in thousands of notices.

**Why this is the right launch piece for this shelf.** Every competitor and every
advocacy shop that has ever built one of these corpora has the same problem and none of
them publishes the error rate. Leading with our own denominator problem is the single
most credible thing this collection can do, and it makes every later number from this
shelf easier to believe.

**What would make it stronger.**
- **Pull FR body text.** It is the difference between classifying 14% and 100% of the
  corpus. Feasible, not free, and blocked today by pull discipline — *"Route it through
  pull discipline; do not start a second poller."* This is the single highest-value
  unblocked improvement in the collection.
- Add a `land_administration` theme. There is currently **no theme for land
  administration, leasing and rights-of-way**, so *Rights-of-Way on Indian Land* — a major
  BIA final rule — has no home in the vocabulary. That is a vocabulary gap, not a
  classifier error, and it should be disclosed in the piece.
- Have a human spot-check a slice of the audit. The hand-coding was done by an agent, is
  labelled as such in a `hand_coder` column, and **is not a ruling**. Error rates are
  provisional until a human overturns or confirms a slice.

**FINAL vs WILL MOVE.** The tier composition and the audited error rates are **FINAL** for
the 2026-08-06 build. The corpus **WILL MOVE** — it runs to the pull date, so CY2026 is
incomplete and a January re-pull extends it. State the corpus vintage in the piece.

---

### QUEUE — additional `federal-register` candidates, ranked

**FR2. Where the government acts is not where Indian Country lobbies.** *(web · MEDIUM —
directional only)*
`agency_attention_vs_advocacy.csv`. Where the government acts by regulation — EPA
(−5.1pp), Education (−2.2pp), HUD (−2.1pp), Interior (−11.2pp) — advocacy is aimed
proportionally *less*. Where advocacy concentrates — **White House/EOP +6.9pp**, Justice
+2.9pp, Treasury +2.9pp, Defense +2.4pp — comparatively little tribal-subject regulation
is published. Consistent with lobbying targeting **discretionary and appropriations
channels** rather than notice-and-comment rulemaking.
**Three caveats that must be in the piece, not under it:** the denominators are different
objects (shares comparable, raw counts not); FR agency attribution is exact while lobbying
targets are filer-reported and unaudited; the FR side inherits precision 0.68. **Congress
is excluded** — 42.3% of lobbying targets and 0.0% of FR documents, because Congress does
not publish in the Federal Register. That gap measures the two sources' definitions, not
anybody's behaviour. **This supports a directional claim and not an elasticity.**

**FR3. The consultation record did not grow with the policy record.** *(web · MEDIUM)*
Classifiable tribal-subject FR documents roughly **doubled from ~650/yr to ~1,300/yr
between 2020 and 2024**, while consultation notices stayed flat in the teens and twenties.
On the available evidence the two series are unrelated.
And the measurement correction is half the story: a naive rule counted **2,795**
"consultation notices", nearly all of which were NAGPRA inventory notices containing the
sentence *"in consultation with the appropriate Indian Tribes or Native Hawaiian
organizations"* — evidence that consultation **happened**, not a notice announcing one.
Publishing the two together would have **inflated the consultation record roughly
six-fold**. Two measures, published separately and never summed: **484** notices whose
purpose is to convene consultation, **1,829** documents reporting consultation already
undertaken.
Also useful shape: **Interior is under a third of consultation notices** (151), with HHS
(99) and EPA (43) together nearly matching it — consultation is meaningfully
government-wide even though tribal-subject *rulemaking* is 56% Interior.
**Verified 2026-08-26:** `fr_consultation_notices.csv` = **484** ✅ (span 1994-01-13 →
**2026-05-20**), `fr_consultation_referenced.csv` = **1,829** ✅, agency shares Interior
151 (31.2%) · HHS 99 (20.5%) · EPA 43 (8.9%) ✅.
**Hard constraint:** do not read the 2025–26 decline (7 and 6 notices) as policy. The
corpus is incomplete for 2026 and single-digit moves are noise. And the `referenced`
series **must not be read as a trend at all** — it is 0 before 2011 purely because
pre-2011 abstracts are missing, and it collapses to ~1 in 2024–25 because the NAGPRA notice
template changed wording. It measures template language.
**⚠ A second break in the same column, measured 2026-08-26:**
`n_documents_reporting_consultation_undertaken` falls **172 (2022) → 12 (2023) → 1 (2024)
→ 1 (2025) → 0 (2026)**. That is a detector or source-field break, not a collapse in
consultation practice. **Do not publish that series as a trend in any form.**

**FR4. The docket number that is not a phrase.** *(brief · HIGH)* — see refusal **R9**.
All verified 2026-08-26: **`fr_ex_parte_notices.csv` = 7,820 rows** (the *index* is 7,818;
the +2 are the two new FERC notices `01-1578` and `2026-16634` — **quote 7,820 for the
file, 7,818 for the index**). **69** documents carry `series =
AGENCY_EX_PARTE_DISCLOSURE`, i.e. name a party outside FERC ✅. **FCC = 4,430** ✅.
**STB = 616** ✅ — but note the build log's sentence reads *"616 indexed documents are STB
**or its ICC predecessor**"*, and that union is **727** (STB 616 + ICC 111). **616 is STB
alone. Fix the wording in the log before quoting it.**
The two quotable lines, verbatim:
> **"EX PARTE" IS A DOCKET NUMBER AT THE SURFACE TRANSPORTATION BOARD.** STB numbers its
> rulemakings of general applicability *Ex Parte No. 290*, *Ex Parte No. 733* … The string
> is present and no communication is disclosed. Typing those as ex parte communications
> because the substring matched is the same error shape as reading the Wichita Tribe out of
> "Boys & Girls Clubs of Wichita Falls".

> **An agency with the strongest ex parte disclosure regime in government contributes
> almost nothing to an FR-based dataset**, and its 4,430 documents make it look like the
> opposite.

Short, checkable, and the kind of thing that makes a data buyer trust a vendor. **This is
also the freshest file in the whole slate — max publication date 2026-08-24.**

**FR5. The subset shelf.** *(product, not an article — but it generates several)*
`docs/SUBSET_DATASETS.md` names the cuts already inside this corpus, each with its own
users and none of them available anywhere as structured data: **NAGPRA 6,179** ·
**gaming/IGRA 3,179** · energy and mineral leasing 560 · IHS 543 · probate/allotment/
fractionation 490 · recognition history 407 · consultation 385 · **liquor ordinances 287**
· self-governance and 638 contracting 209 · land into trust 189 · NAHASDA 164 · roads 82 ·
ICWA 79 · water rights settlements 75 · EPA Treatment-as-State 18.
The liquor-ordinance cut is the sleeper: tribal liquor ordinances **must** be published in
the FR to take effect, so it is small, complete, and nobody has it.
**The rule that keeps this from becoming clutter:** a subset must inherit the parent's
entity keys *and its caveats*. A NAGPRA dataset that loses `tribe_id` is a PDF index; one
that loses the parent's warnings is worse, because it presents an unqualified extract of a
qualified source.

**FR6. ⭐ FERC — 102,615 filings over 307 dockets, 1990–2026, and nothing adjacent exists.**
*(paper · MEDIUM on entity attribution, HIGH on the corpus)*
Gap **G3** in the landscape scan: *"Nothing adjacent found."* Where tribes appear in the
formal federal adjudicatory record — hydropower relicensing, pipeline certificates, LNG
terminals — across 36 years. **307 of 307 dockets on disk, 0 refused, 0 truncated**;
`ADVOCACY` 22,540 + `GOVERNMENT_ENGAGEMENT` 278 = **22,818**;
`ferc_docket_parties.csv` 11,563 rows; the ex parte layer 4,248 communications.
**Two hard constraints, both already documented:** `is_lobbying` is **0 on every row** — do
not filter on it expecting advocacy, and **advocacy is not lobbying** (an administrative
comment or an amicus brief is advocacy and is not lobbying; *"conflating them would be wrong
in a way that matters legally"*). And **entity linkage is 1,107 of 102,615 rows — 1.08%,
100 distinct entities.** So the publishable piece today is about **dockets and
participation**, not about per-entity influence.
**⚠ Do not join on `ferc_filing_id`.** Its last segment is `abs(hash(filer_organization)) %
10000` and Python randomises string hashing per process — **4 of 2,534 shared documents kept
their id across two builds.** Join on `docket_number` + `accession_number` +
`filer_organization_as_recorded`.
**On the owner's speed criterion this is a strong second piece for the shelf: the corpus is
complete on disk and needs no pull.** The entity layer is the thing that would take work,
and the piece does not require it.

**FR7. LOW — anything about the 132,964 body-only documents.** We do not hold body text.
This is a missing-data problem, not a modelling problem. Listed so nobody tries.

### The `federal-register` refusals worth publishing

- **R9** — the STB docket number, 616 documents.
- **R10** — the NAGPRA collapse that never happened, and the abstract-availability
  boundary at 2011 that bounds every other theme series in the corpus.
- The six-fold consultation inflation described at FR3.
- **Every pre-2011 FR theme level or trend is unpublishable.** Abstract coverage changes
  under the series (70–82% before 2011, 88–92% after). NAGPRA has a corrected series
  because its FR notice titles are prescribed by 43 CFR part 10; **no other theme does.**

> **✅ VERIFIED 2026-08-26.** Corpus size, all four tier counts, the ex parte figures and
> both consultation counts reproduce exactly. **Two copy corrections stand: 14.3% not
> 14.2%, and 616 is STB alone not STB+ICC.** Two series are unpublishable as trends: the
> 2025 document-count anomaly and the `consultation_undertaken` break.

---

<!-- SLATE:legislation -->
## 3. `legislation` — Congressional Votes and Proposed Legislation · shelf `standard`

### What the data can support today

*All measured 2026-08-26.*

| file | rows | span |
|---|---:|---|
| `native_bills.csv` | **3,069** | Congress **93–119**; introduced **1973-01-03 → 2026-04-16** |
| `native_bill_outcomes.csv` | **3,069** | 12-value `disposition` ladder, `disposition_basis = congress_gov_action_text` |
| `bill_votes.csv` | **423** | 1973-04-16 → **2025-05-06**; House 282 / Senate 141; 398 linked to a bill |
| `bill_votes_official_verification.csv` | **305** | 1989-09-20 → 2025-05-06, `fetch_status = ok` on all |
| `member_positions.csv` | **136,119** | 423 vote_ids, 283 bill_ids; Yea 82,410 · Nay 45,366 · NV 8,312 · Present 31 |
| `hearing_appearances.csv` | **2,667** | 1997-04-24 → **2026-07-21**; `entity_id` on 1,775 (66.6%) |
| `hearing_bill_links.csv` | **465** | 2013-03-20 → **2026-08-05**; 325 bills |
| `native_bills_entity_bridge.csv` | **676** | 591 bills, **154 entities**; tier A 560 / B 116 |
| `native_bills_entity_class.csv` | **2,694** | 2,456 bills; Fed. Rec. Tribe 2,306 · NHO 122 · ANC village 120 · ANC regional 88 |
| `native_bills_subject_sweep.csv` | **2,414** | 2,382 already in `native_bills`, **32 net-new** |

**The 3,037-versus-3,069 conflict is resolved and both are right at different times.**
3,037 rows carry `build_date = 2026-08-05`; **32 carry 2026-08-06**, added by
`73_bills_votes_completion.py --sweep` (ANCSA 14, general 10, Native Hawaiian 8).
`docs/CONTENT_ANALYSIS.md` is stale by one build. **Current file is 3,069.**

**⚠ A live casing bug, found in the same 32 rows.** They are the only rows with lowercase
`chamber` values — `senate` 21, `house` 11. **Any filter written as `chamber == 'Senate'`
silently drops them.** Fix before any chamber split is published.

**⚠ A coverage cliff that invalidates any rate before the 103rd.** Congresses **93–102 hold
only 98 bills in total**, and all of them arrive from `HSall_rollcalls.csv` via tribal
roll-call classification — not from a bill universe. **The real bill corpus starts at the
103rd Congress. Never compute a rate on 93–102.**

---

### ★ LAUNCH PIECE — *Every roll-call vote on Indian Country legislation, checked against the official record — including the two that do not match*

**Format:** paper, with an 800-word web companion. **Confidence: HIGH.**

**Why this and not the enactment-ratio piece.** The 2.24× ratio (below) is a
Native-versus-general comparison, and **the owner has deprioritised those.** This piece
stands entirely on Cedar Press's own measurements and needs no external denominator — and
it is the cheapest credibility asset in the whole slate.

**The claim.** **305 of 423 roll calls (72.1%) were checked line-by-line against an official
source** — clerk.house.gov 213, senate.gov 92 — and **303 of 305 agree on both the yea and
the nay count. 99.3%.** Exactly two disagree, and **both are named in the file**:
`H101-0788` (1990-10-10, *"official 248-172 vs cedar 247-172"*) and `S109-0538` (2006-06-15,
*"official 46-53 vs cedar 45-54"*).

**The other 118 are the better half of the story.** None is a blank. Each carries a reason:
*"no_official_electronic_record: House EVS begins 1990, Senate LIS begins the 101st
Congress."* **The federal record of how Congress voted on Indian Country simply does not
exist in machine-readable form before 1990**, and the only way to know that is to try all
423 and publish what happened to each. Separately, `tally_matches_voteview = 1` on **415 of
423**, which is a second, independent check.

**Why it matters beyond method.** Every claim anyone makes about congressional treatment of
tribes rests on a vote record nobody has audited. This publishes the audit, the failures by
name, and the boundary of what the federal record can support — 136,119 individual member
positions across 423 votes and 283 bills, with the pre-1990 wall stated rather than papered
over.

**What would make it stronger.** Extend past **2025-05-06**. The 119th Congress holds
**exactly one roll call** in the file. Congress.gov's API is free-key and this is the
highest return-on-effort refresh in the slate.

**FINAL vs WILL MOVE.** The 305 verifications are FINAL. The roll-call series ends
2025-05-06 and the bill record freezes 2026-04-16 — **the stalest endpoints in the slate.**

---

### QUEUE ITEM, DEMOTED FROM LAUNCH — *Native bills are enacted at roughly twice the rate of federal bills generally*

**⬇ Demoted 2026-08-26 on the owner's direction that comparison to non-Native entities is
deprioritised.** The measurement is HIGH-confidence and the denominator genuinely exists —
this is a strong piece and it should run, just not first. *"It can be added later."*

**The claim.** Applying the *identical* enactment rule to both sides
(`latest_action_text` matching "became public law" / "public law no"), measured 2026-08-26
against `data/raw/external/votingpatterns/all_bill_intros.csv` (**183,233 bill
introductions, 103rd–119th Congress**):

| window | Native bills | all bills | ratio |
|---|---:|---:|---:|
| **103rd–118th (complete congresses)** | **231 / 2,817 = 8.20%** | **5,228 / 142,962 = 3.66%** | **2.24×** |
| 118th alone | 9 / 229 = 3.93% | 271 / 16,565 = 1.64% | 2.40× |
| 103rd alone | 25 / 147 = 17.01% | 453 / 8,540 = 5.30% | 3.21× |

**The ratio is the story; the level is not.** Native-focused bills clear at roughly twice
the general rate in *every* congress from the 103rd to the 118th — and **both series have
fallen by about two-thirds** across that span. Indian Country's legislative advantage is
real, stable, and shrinking in absolute terms along with everything else Congress does.

**Why this piece is unusually strong for this project.** Most Cedar Press findings are
constrained by the absence of a denominator. Here there is one, it is on disk, and the
same rule can be applied to both numerators — which is exactly the comparison every "tribes
and Congress" claim in circulation lacks.

**⚠ One internal contradiction that must be resolved before any enactment count is
printed.** `native_bills.outcome` says **229 enacted**. `native_bill_outcomes.disposition`
says **283**. `outcome` is null on 325 rows, 50 of which `disposition` resolves to enacted,
and the two disagree outright on 4 non-null rows (3 `died-in-committee` → enacted, 1
`vetoed` → enacted). **`native_bill_outcomes` is the later and better-sourced derivation —
use 283 / 3,069 = 9.22%, and say in the piece which column you used and why.**

**Caveat to publish with it, in the text:** `native_bills` is a **curated slice**, so
selection into it may correlate with salience. **The comparison supports a rate difference,
not a causal claim about why.**

**What would make it stronger.**
- **Reconcile `outcome` against `disposition`** and retire one of them. Two enactment
  counts in one collection is the shape of defect this project catches in other people's
  data.
- **Fix the chamber casing bug.**
- Extend the roll-call series past 2025-05-06 — see the endpoint warning below.

**FINAL vs WILL MOVE.** **FINAL through the 118th Congress.** The **119th is a stub** — 154
bills and **exactly one roll call**. Do not chart it. **The bill record freezes at
2026-04-16** (`introduced_date` and `latest_action_date` both), which makes this the
**stalest endpoint in the whole slate — four months behind every other shelf.**

---

### ⛔ THE ENDPOINT PROBLEM, STATED PLAINLY

| series | max date | reads as |
|---|---|---|
| `bill_votes.csv` | **2025-05-06** | ends 2025; the 119th has 1 roll call |
| `native_bills.csv` / outcomes | **2026-04-16** | four months stale |
| `hearing_appearances.csv` | 2026-07-21 | current |
| `hearing_bill_links.csv` | 2026-08-05 | current |

**Two honest options and only two: refresh before launch, or state the endpoint.** For this
shelf the refresh is cheap — Congress.gov's API is free-key — and it is the single highest
return-on-effort refresh in the slate, because the launch piece's headline metric is
congress-keyed and the 119th is what a reader will ask about first.

---

### QUEUE — additional `legislation` candidates, ranked

**LG2. ⬆ PROMOTED TO THE LAUNCH PIECE — the roll-call verification.** See above.

**LG3. Who carries Indian Country's legislation.** *(web · MEDIUM)*
Sponsor concentration, measured 2026-08-26: **Rep. Don Young [R-AK] 139** · Sen. John McCain
[R-AZ] 106 · Sen. Ben Nighthorse Campbell [R-CO] 81 · Sen. Lisa Murkowski [R-AK] 75 · Sen.
Daniel Inouye [D-HI] 59 · Sen. Jon Tester [D-MT] 47 · Sen. Tom Udall [D-NM] 41 · Sen. Martin
Heinrich [D-NM] 36. By **enactments**: McCain 13 and Campbell 13, then Young 8. `sponsor` is
null on 117 rows — say so.
**⚠ HARD CONSTRAINT: tribal affiliation of members is NOT in the dataset.** No column in
`native_bills.csv` or `member_positions.csv` carries affiliation, ancestry or anything
equivalent. It can only be hand-coded against an external roster, and a hand-coding by an
agent **is not a ruling**. If the piece wants the Native-members angle — Campbell (Northern
Cheyenne) 84 bills / 13 enacted, Cole (Chickasaw) 31 / 0, Mullin (Cherokee) 24 / 3, Haaland
(Laguna Pueblo) 13 / 0, Peltola (Yup'ik) 10 / 0, Davids (Ho-Chunk) 9 / 0, Kahele (Native
Hawaiian) 2 / 0 — then **build the roster as a ruled artefact first and label it as
Cedar Press's own coding.** Do not slip it in as a data fact.

**LG4. The hearing record.** *(web · MEDIUM)*
2,667 witness appearances 1997–2026, `entity_id` on 66.6%, tier B 1,598 / C 892 / **A 177**.
465 hearing-to-bill links across 325 bills. Who testifies, how often, and whether testifying
predicts anything. **Runs later than any other series on this shelf (2026-08-05), so it is
the natural monthly-cadence brief while the bill record waits for a refresh.**

**LG5. The bills that aren't there.** *(brief · HIGH — a cross-shelf finding)*
**H.R. 2968 and S. 2474 (116th Congress)** — the bills Arctic Slope Regional Corporation
filed eleven lobbying disclosures about, seeking to restore direct appropriations for the
DoD Indian Incentive Program — **are not in `native_bills.csv`.** A bill that Indian
Country demonstrably lobbied on, absent from the Native bills corpus, is a measured recall
failure and a legitimate thing to publish about our own selection rule. It also links this
shelf directly to **C2** on the contractors shelf.

**LG6. LOW — content classification of the bills corpus.** Not attempted, deliberately.
`native_bills` already carries a `policy_area` assigned by the Library of Congress — a
maintained, external, authoritative taxonomy — and *"replacing it with our regex would be
strictly worse."* Distribution: Native Americans 2,101 · Public Lands & Natural Resources
161 · Taxation 157 · **NaN 124** · Health 58 · Armed Forces 40 · Education 39. The useful
work is joining bill numbers parsed from lobbying `specific_issues_text` to `bill_id` — a
**linkage** task, not content analysis.

### The `legislation` refusals worth publishing

- The 118 unverifiable roll calls, each carrying **the reason** rather than a blank.
- The two named disagreements with the official record.
- The refusal to classify the bills corpus against an existing authoritative taxonomy.
- **The pre-103rd cliff, published as a cliff.** 98 bills across ten congresses, all
  arriving from a roll-call file rather than a bill universe. Most datasets would let that
  become a "historical trend."

> **✅ VERIFIED 2026-08-26.** All row counts, spans, the 305/423 verification rate, the
> 303/305 agreement, the sponsor ranking and the 183,233-row denominator reproduce.
> **Two corrections stand: `native_bills` is 3,069 not 3,037, and the enactment count is
> 283 not 229.**

---

<!-- SLATE:deals -->
## 4. `deals` — Indian Country Deals · shelf `standard`

### What the data can support today

*All measured 2026-08-26 from `data/clean/deals_classified.csv`.*

| | |
|---|---|
| rows | **935** ✅ |
| entity-linked | **886 = 94.76%** ✅ (tier A 716 · B 170 · unlinked 49) |
| span | **2000-01-01 → 2026-08-20**, no interior gaps |
| `Announced_Value_USD` | $45,195,917,316 over 835 rows — **not safely summable** |
| 2026 to date | **91 rows**, **$11,656,742,000 over 65 valued rows** |

Provenance reconciles arithmetically: eight additions files = 790, plus `deals_2026_ytd.csv`
90 and `deals_historical_2020_2025.csv` 55 = **935**. The documented "790 → 935, 131 merged
+ 14 collected" reproduces exactly. **`docs/COVERAGE_AUDIT.md` still says 790 in two
places** and **`data/clean/deals_taxonomy.csv` is stale** (`built_date` 2026-08-06, counts
still summing to 790). **Do not draw the chart from the taxonomy file** — it is wrong by
145 rows.

---

### ★ LAUNCH PIECE — *The Indian Country "deal" curve is a chart of when three federal agencies announced their grant rounds*

**Format:** ≈800-word web article with a longer method note. **Confidence: HIGH — and the
dataset says this about itself, which is the whole reason it is publishable.**

**The claim.** Re-measured against the current 935-row file: **623 of 935 rows are grant or
public financing against 151 acquisitions** (`Deal_Category`), or **653 against 170** on
the `transaction_type` axis. The ratio softened from 4.95:1 to 4.13:1 when the base-ledger
merge brought in 145 transaction-heavy rows — **the correction runs against the headline,
which makes it safer to publish, not weaker.**

**And the year curve is not a deal-activity curve.**

- **Acquisitions are flat across the whole 27 years**: min 1, max 25, mean 6.3 (2000–2018
  mean 3.1; 2019–2025 mean 13.7). **They do not produce the curve.**
- **Three federal programmes produce 546 of 653 public awards (83.6%) and 58.4% of the
  entire ledger**: **NTIA TBCP 273 · HUD ONAP 222** (IHBG-Competitive 148 + ICDBG 72) **·
  EDA ARPA Indigenous Communities 51.** Add DOE Office of Indian Energy (49) and it is 91%
  of awards.
- **Peak years are almost entirely those programmes**: 2022 = 169/186 (**90.9%**) · 2024 =
  154/177 (**87.0%**) · 2023 = 93/113 (82.3%) · 2019 = 51/75 (68.0%).
- **HUD ONAP arrives on exactly eight dates**, delivering 222 rows: 2019-12-16 (51),
  2021-04-12 (24), 2024-05-22 (36), 2024-07-29 (41), 2024-12-27 (32), 2025-04-09 (36), plus
  two singletons. **It is a step function of announcement days.**

**The decisive evidence, and it is the sentence that makes this a Cedar Press piece rather
than an observation:** the ledger's own `Date_Basis` column says so. **456 of 935 rows
(48.8%) are dated by a publication or announcement date rather than a transaction or
award-action date**, and **147 rows carry the literal phrase "NOT an award action date"** —

> `PDF creation date of the corrected HUD award list (2019-12-16). NOT an award action
> date.` — 51 rows
> `Announcement date (NTIA recommended-for-award release); award action date not published`
> — 48 rows

**The single largest one-day cluster in the entire file — 51 rows on 2019-12-16 — is a PDF
creation date.**

**Why this is the right story.** Everyone who builds a Native deal tracker produces this
curve and reads it as deal activity. It is a chart of federal announcement cadence. **That
is a genuinely important fact about how capital actually arrives in Indian Country** — not
through an M&A market but through competitive grant rounds whose timing is set in
Washington — and it reframes the collection from "a deal database" to "a record of how
Indian Country is financed."

**⛔ PRIOR ART — cite it in the lede, not the footnotes.** *"Native entities are acquiring
companies to grow their federal contracting"* is **already published, by the owner, in the
partner outlet**: **Moreno, Dippel & Siken, *Tribal Business News*, 2024-05-05** — 100
acquisitions, 47 entities, 2000–2023, ~$10B, built on HigherGov. **Pitch this piece as "an
update and expansion of our 2024 analysis," with the full citation.** The acquisition series
here (151 rows on `Deal_Category`, 170 on `transaction_type`) is a direct extension of that
work, and the composition finding — that acquisitions are the *small* half — is the new
contribution.

**⚠ Do NOT chart `Announced_Value_USD` by year.** Six rows are aggregates covering ~600
recipients or more (two IHBG formula rounds at $1.1B each); three SEC instrument pairs must
never be summed; **160 rows are sub-threshold** (`Threshold_Exception = Yes`); and
`native_party_value_caution` is set on 50 rows.

**⚠ And 2026's $11.66B is not a record year.** It is the largest figure in the file, on
eight months, driven by capital projects, **one $2.3B contract *ceiling*** (ASRC Federal DLA
ChemPOL III) and **one $1.1B ~600-recipient aggregate**. **Not comparable to prior years.
Do not chart it as a trend.**

**What would make it stronger.**
- **Rebuild `deals_taxonomy.csv`** so the chart has a current source. *(Note: `88_build_deals_taxonomy.py` is on the NEVER RUN list — it is a full rebuild that drops the attribution columns. The taxonomy needs a new non-destructive builder.)*
- Fix `docs/COVERAGE_AUDIT.md`'s two 790s.

**FINAL vs WILL MOVE.** **2000–2025 is FINAL.** **2026 is YTD: 91 rows, max `Event_Date`
2026-08-20.** *(Note the distinction: the coordinator's "through 2026-08-22" is the
**channel** endpoint — article ids swept to Aug 22 — while **2026-08-20 is the data
endpoint**. Both are true and they are different facts. **Publish 2026-08-20.**)* This
collection gains substantially at the year turn.

---

### QUEUE — additional `deals` candidates, ranked

**D2. A $700M row whose federal approval was reversed, and a vocabulary with no word for
it.** *(web · HIGH — and it is the best small story in the collection)*
`ND-2026-040`, Scotts Valley, `Event_Date` 2026-04-19, `Announced_Value_USD = 700,000,000`.
**`Status` still reads `"Approved; litigated"` and `deal_status_std = UNCLASSIFIED`.** The
correction sits unapplied in `review/deals_status_corrections_2026-08-26.csv`:
> "INTERIOR WITHDREW THE GAMING DETERMINATION. Assistant Secretary … concluded on
> reconsideration that 'the Band has not established a significant historical connection to
> the Parcel' … **NOT applied automatically - the `Status` vocabulary has no agreed term for
> a withdrawn federal determination and inventing one silently drops the row from the fixed-
> label rollups.**"

The 21-value `Status` vocabulary (Awarded 583, Completed 96, Closed 94, Recommended for
award 48 …) genuinely contains no withdrawn or reversed term. **Editorial consequence:
$700M of the 2026 total sits on a row whose underlying federal approval was reversed on
2026-07-31, and the ledger cannot say so.** A piece about what happens when reality needs a
word your schema does not have. **Awaiting an owner ruling — do not resolve it by
inference.**

**D3. The deals we did not write.** *(web · HIGH)*
`review/deals_skipped_leads_2026-08-26.csv` (8) + `deals_skipped_leads_2000_2019.csv` (28:
no_date 11, no_amount 9, out_of_window 4, aggregator_only 4). Named kills, each of which
would have been a plausible row:
- **Cherokee Nation / Rogers State MOU** — *"No money will change hands under the new
  agreement."*
- **Naskila Casino Resort groundbreaking** — firmly dated 2026-06-18 and **no cost published
  anywhere retrieved**, so it cannot clear the $1M threshold on evidence.
- **Dartmouth's $5M Tribal Sovereignty Institute** — no Native party.
- **Paskenta / Mad River Brewery** — a search summary presented it as August 2026; retrieved
  coverage dates it **March 2024**. *"Had the summary been trusted it would have been the
  window's only acquisition — and wrong by two and a half years."*
- **Lone Star Park's "$47.8 million"** — refused, because the retrieved article says terms
  were **not disclosed**.
- **Mohegan Niagara** — left blank because every figure is **Canadian dollars** and no rate
  was invented.
- Seven value traps excluded from every value field, each a figure that belongs to a
  different year or a different transaction.
- **`MA2020-008` withdrawn whole as a duplicate**, with the newsroom URL carried onto the
  survivor's blank `Source_2` *"so nothing retrieved was lost."*
**And an absence recorded as a finding:** *"No acquisition closed or was announced in Indian
Country between 2026-07-28 and 2026-08-26 that any swept channel reports."* August 2026
contains zero acquisitions, and the file says so rather than leaving a gap.

**D4. ⭐ Tribal capital markets — an empty field, and the story is what is closed.**
*(paper · MEDIUM on the data, HIGH on the gap)*
**Gap G4 in the landscape scan, and it is nearly a fourth headline gap.** **NAFOA — the
tribal-finance body itself — has no research function at all**, confirmed four ways: no
`/research`, and no research, publications, data or library node anywhere in its own
sitemap. Its only finance publication is an accounting manual. Nothing found anywhere else.
`AGENTS.md` already lists "tribal municipal/bond finance (EMMA)" among the next-three
dataset candidates — **the sweep says that space is empty.**
The data, however, is thin, and the piece must be built on the refusal map rather than the
series:
Four files, and every one of them is a wall:
- `tribal_bond_issuances.csv` — **29 rows, and it is not a series: only 1 of 29 carries an
  `issue_date`.** Par $6.71B over 28 rows, 10 issuers, Seminole $2.82B (42%). **All 29
  sourced to Moody's rating actions — single-authority.** Every one is gaming-backed.
- `gaming_financing_events.csv` — 293 events, 131 tribes, and **`principal_amount_usd` is
  null on all 293**, with `execution_status = UNEXECUTED_DRAFTS_REVIEWED` on all 293. These
  are NIGC opinions on *draft* agreements.
- `seminole_bond_disclosures.csv` — **29 rows, of which 10 are Single Audit packages
  `withheld_by_rule`** under 2 CFR 200.512(b)(2), 1 `not_retrievable_by_automated_client`,
  and the MSRB EMMA route closed by robots.txt.
- `tribal_resolution_financings.csv` — **1 row.** A stub.
**The strongest thing here is the refusal map**, and it has a genuinely good ending: **7
rows are Seminole term loans and bonds named, with coupons, in the quarterly holdings
schedules of registered mutual funds filed on EDGAR.** *A tribe's private debt is visible
because somebody else's public fund owns it.* And even where the audit is withheld, **the
FAC still publishes the threshold measure** — federal awards expended, $121.7M (FY2025),
$182.7M (FY2024), down to $25.5M (FY2018).

**D5. LOW — ownership-change detection.** `docs/OWNERSHIP_CHANGE_DETECTION.md` is a note,
not a build. 12,121 awardee UEIs carry parent data; **488 (4.0%) change parent over time;
173 have clean non-overlapping year ranges.** **FY2022 is contaminated** (37 against a
~15/yr baseline) because the DUNS→UEI migration on 2022-04-04 manufactures parent changes —
already in `series_breaks.csv`. Four stated failure modes, the last of which is the reason
this is LOW: *"It detects; it does not establish."*

### The `deals` refusals worth publishing

- **An aggregate party must never resolve to one entity.** Four autoresolver proposals
  refused by hand, **all still unruled**: *Riverside San Bernardino County Indian Health
  Inc* → `UIO-HEALTH-00` (that is "Native Health", **Arizona**, and the party is
  Californian); *Department of Hawaiian Home Lands* → an NHO (DHHL is a **department of the
  State of Hawaii**); a **nine-applicant** aggregate keyed to one tribe; and an
  **eight-project** aggregate matched on the generic phrase "health organisations."
- **A resolver re-run that would have looked like progress.** Re-running script 57 against
  the grown spine **lost 4 parties outright and silently repointed 4**, two of them from a
  tribal government onto that tribe's *college* (`TRBF-KWNWBY-00` → `TCU-KWNWB1-00`;
  `TRBF-CSKTFR-00` → `TCU-SLSHKT-00`). Rejected and kept as
  `.rerun57_2026-08-26_REJECTED`; merged **additively** instead, going 443 → 502, **added
  59, lost 0.**
- The named kills at D3, especially the two-and-a-half-year date error a search summary
  would have introduced.
- The Scotts Valley vocabulary gap at D2.

> **✅ VERIFIED 2026-08-26.** 935 / 886 / 94.8% ✅ · the 790 → 935 arithmetic ✅ · all eight
> HUD round dates ✅ · the 2026 monthly table ✅ · 18-of-26 April rows are one USDOT RTA
> round ✅ · the rejected re-run's 4 lost / 4 repointed ✅ · 443 → 502, +59, lost 0 ✅.
> **The composition headline must be restated as 623 / 151 (or 653 / 170), not 594 / 120.**

---

<!-- SLATE:nagpra -->
## 5. `nagpra` · shelf `standard`

### What the data can support today

*All measured 2026-08-26.*

| | |
|---|---|
| `data/clean/nagpra_notices.csv` | **6,729 notices** ✅, 6,729 unique `document_number`, **1994-02-25 → 2026-08-03** |
| notice type | `inventory_completion` **4,770** · `intent_to_repatriate` **1,834** · `intended_disposition` **125** (mapping 1:1 to 25 U.S.C. 3003 / 3004 / 43 CFR 10.7). `is_correction = 1` on **286** |
| `data/clean/fr_nagpra_title_index.csv` | **6,606** ✅ — the **index**, carrying no parsed content at all |
| `nagpra_notice_entity_bridge.csv` | **51,338 rows**; **6,028 of 6,729 notices (89.6%) resolve to ≥1 spine entity**; 47,688 of 51,338 rows resolve, reaching **542 entities** |
| bridge tiers | B 29,821 · C 17,867 · X 863 · blank 2,787. **ZERO tier A. Nothing here is hand-ruled.** |
| institution names | `institution_primary` populated on **all 6,729**; type: university 2,923 · museum 1,515 · federal agency 1,246 · other 539 · state agency 271 · historical society 218 · tribal 17 |
| ship ratio | **3,089 of 6,729 in `dist/` — 45.9%** |

**Three counts are in circulation and they are three different objects.** 6,729 is the
product file. 6,606 is the FR title index. 6,179 is the subset estimate in
`docs/SUBSET_DATASETS.md`. **Name which one you are quoting.**

**⚠ AND THE SURGE FIGURES IN CIRCULATION ARE THE WRONG FILE'S.** `docs/CONTENT_ANALYSIS.md`
gives 2023 = 496, 2024 = 670, 2025 = 830. Those are **index** counts. The product carries
123 more notices:

| year | index (`fr_nagpra_title_index`) | **product (`nagpra_notices`)** |
|---|---:|---:|
| 2023 | 496 | **496** ✅ |
| 2024 | 670 | **707** |
| 2025 | 830 | **900** |
| 2026 YTD (to 08-03) | 552 | **570** |

**The publishable surge is 496 → 707 → 900, an 81% rise across 2023–2025**, and the piece
must name which file it came from.

---

### ★ LAUNCH PIECE — *The last three years produced more NAGPRA notices than the first seventeen*

**Format:** paper. **Confidence: HIGH** — the classifier here is near-exact by
construction, which is unusual in this slate.

**The claim.** Notices roughly quadrupled from **244 in 2022** to **900 in 2025** — 496,
707, 900 across 2023–2025 against 1,925 for the entire period 1994–2010. This is a real
surge, and it is consistent with the revised NAGPRA regulations at **43 CFR part 10,
effective January 2024**, which required institutions to complete and update inventories.
**And the record names the institutions.** `institution_primary` is populated on all 6,729
notices; the Peabody Museum of Archaeology and Ethnology at Harvard accounts for **316**,
more than three times the next holder (American Museum of Natural History, 93), then
Interior/BIA 68, the Tennessee Valley Authority 65, the Burke Museum at the University of
Washington 60.
*(One deduplication trap: "Field Museum" (53) and "Field Museum of Natural History" (42)
are the same institution split across two strings — 95 combined, which would move it to
second place. **Institution names are not deduplicated.** Any ranking must merge them by
hand or say it has not.)*

**Why the classifier can be trusted here when it cannot elsewhere in the FR corpus.** This
is the piece's methodological spine and it is a genuinely interesting one. The FR-wide
relevance tier **missed 1,249 of these notices — 18.9%** — because pre-2011 NAGPRA notices
usually carry no abstract and their titles (*"Notice of Inventory Completion: Beloit
College, Logan Museum of Anthropology, Beloit, WI"*) contain no Native term. The fix does
**not** re-tune the tier rule, because that would invalidate the audit sample. It
classifies on a signal present throughout the whole period: **the FR's own standardised
notice titles, prescribed by 43 CFR part 10.** *"Notice of Inventory Completion"* **is** a
NAGPRA notice. Precision is near-total and it does not depend on an abstract existing.

**And the artefact it replaced is the story's opening.** See refusal **R10**: the theme
series showed NAGPRA collapsing from ~80/yr in 2002 to ~17/yr across 2003–2010, then
exploding after 2011. **That did not happen.** It was an artefact of abstract availability
interacting with our own relevance tier, and it was caught only because one such notice
turned up in a 120-document hand-audit sample.

**⚠ FRAMING — this subject is not like the others on the shelf, and four rules govern the
piece. They are not stylistic preferences.**

**1. NEVER publish a summed count of ancestral remains as an inventory statistic.**
`mni_total_stated` is populated on 4,252 notices and sums to **158,162 individuals**. That
number is *technically* sourced, and publishing it would be wrong twice over. It is a
headline about human beings rendered as inventory. **And it is not defensible arithmetic**:
2,477 of 6,729 notices are deliberately blank (`no_mni_stated` 2,315 +
`multiple_statements_not_summed` 162), so the sum is a floor of unknown depth over an
incomplete denominator. `docs/NAGPRA_BUILD_LOG.md` says it outright: **"Never sum
`mni_total_stated` as a population figure."** Honor it. The same applies to the 2,360,830
associated funerary objects. **If magnitude must be conveyed, convey it as notices and
institutions.** Where remains must be counted at all, count them **per notice, quoting the
notice**, never as a project total.

**2. `culturally_unidentifiable = 1` (615 notices) must never be rendered as "unidentified"
or "unclaimed."** It is a **contested statutory determination made by the holding
institution**, and the 2023 rule was written to curtail it. Framing it as a neutral fact
adopts the institution's position in a live dispute.

**3. Do not collapse `relationship`.** `consulted` (18,946) ≠ `culturally_affiliated`
(19,874) ≠ `aboriginal_land` (4,332) ≠ `repatriation_recipient` (5,322). These are distinct
legal findings under 25 U.S.C. 3003–3005 and 43 CFR 10.11, and `disposition_priority`
applies *precisely where no affiliation was found*. A single "tribes linked to this
collection" number is a category error with real consequences for whose ancestors these
are.

**4. Consult before publishing.** The named users — THPOs, the NAGPRA Review Committee,
museum registrars — are the people best placed to say whether a framing is acceptable, and
they are reachable. This is the one piece in the slate where the right pre-publication step
is a conversation, not another measurement.

---

### ⛔ HARD BLOCKER — the bridge carries live misattributions, all verified still present 2026-08-26

`docs/NAGPRA_BUILD_LOG.md` states the standard this shelf is held to, and it is the
sharpest sentence in the project: **"A wrong tribe on a row is not a mismatch; it is a
false claim about whose ancestors those are."** And: **"`party_name_verbatim` is
authoritative for what was published; `tribe_id` is not."**

Every documented defect was re-checked against the file today. **All of them are still
live.**

| defect | log says | measured 2026-08-26 |
|---|---|---|
| `Pueblo of San Juan` → San Juan Southern Paiute (AZ) instead of Ohkay Owingeh (NM) | 105 rows | **105 rows on `TRBF-SNJUAN-00`** (against 100 correctly on `TRBF-OKYOWG-00` in the same file) |
| Bishop / Lone Pine (CA) → Fallon Paiute-Shoshone (NV) | 97 rows | **97 rows on `TRBF-FALLON-00`** |
| Kootenai of the Flathead → Kootenai Tribe of Idaho | 7 rows | **9 rows** |
| Sac and Fox KS/NE → Sac and Fox OK | 3 rows | **2 rows** |
| **Forest County Potawatomi erased by the `county` guard** | 328 mentions lost | **`TRBF-FSTCTY-00` appears 0 times. 0 rows contain "Forest County."** |
| section headings parsed as party names | 87 rows | **87 rows** exactly |
| Minnesota Chippewa band coarsening | 594 rows, 541 name a band | **594 rows on `TRBF-MINNCH-00`** |

> **No article on this shelf may name a tribe from `tribe_id` without either excluding
> those eight nations or hand-verifying every named row.** Use `party_name_verbatim`.

**And an irony worth carrying into the writing, because it says something true about the
whole project:** the **Forest County Potawatomi Community is invisible in NAGPRA** — erased
by a guard built to stop county names becoming tribes — **and is simultaneously the #2
medium-confidence lobbying client at $4.61M**, i.e. a false *presence* on one shelf and a
false *absence* on another, from the same spine, in the same build. Guards that stop one
error shape create the opposite one.

**Why the dataset is worth publishing at all, framed correctly.** *"No structured public
database of this exists."* Its users — THPOs, museums, the NAGPRA Review Committee,
journalists — are underserved and easy to identify, and the compliance record is a public
accountability record by statutory design. `docs/SUBSET_DATASETS.md` ranks it **first** of
all available cuts, and `docs/CONTENT_ANALYSIS.md` independently calls it *"the strongest
single subset story in the corpus."* Two internal analyses arriving at the same
recommendation from different directions is the closest thing to a vote this project has.

**What would make it stronger.**
- **Clear the misattributions above** before publishing anything tribe-attributed. A
  misattributed repatriation notice is a categorically worse error than a misattributed
  contract.
- **Get a tier-A row into the bridge.** There are currently **zero**, and the build log
  says so on purpose: *"Nothing in this bridge is hand-ruled, and the build correctly
  refuses to claim publishable tier for an algorithmic match."* That refusal is right, and
  it also means the entity layer of this collection is not publishable at entity grain
  today. The launch piece is written at **institution** grain for exactly this reason.
- Rule the **1,106 alias proposals** left unresolved rather than forced — Office of
  Hawaiian Affairs (99), Arapaho of Wind River (138), Hui Mālama I Nā Kūpuna ʻO Hawaiʻi Nei
  (64), Wanapum Band (63, *"a non-Federally recognized Indian group"* in the FR's own
  words).
- Raise the ship ratio from 45.9%. A piece pointing at a download that holds half the file
  is a bad experience.

### ⛔ TIME-TO-REPATRIATION IS NOT COMPUTABLE. Do not attempt it.

This is the question every user of this dataset actually has, and the answer is that the
data does not contain it. Measured 2026-08-26:

There is a notice date (`publication_date`, 100% populated) and a
**`repatriation_eligible_date`** (2,719 of 6,729 = 40.4%). **The second is the statutory
earliest-eligible date, not an event date.** No column anywhere records whether, or when, a
repatriation actually occurred.

The measured interval is therefore just the statutory waiting period, and it is a
near-constant: **median 30 days**, mean 31.0, min 28, max 365 — 1,525 notices at exactly
30, 643 at 32, 385 at 31, 152 at 33, and **only 2 notices exceed 33 days**. **That
distribution contains no information about repatriation. It is a restatement of the
regulation.** Publishing it as "time to repatriation" would be a fabrication with a real
column name on it.

*(Also: `window_days_derived` carries **6 negative values and one zero**, including
document `03-20757` at **−31,816 days** — a `response_deadline_date` of 1916-07-05 on a
2003 notice. Small, but it poisons any unfiltered mean.)*

**FINAL vs WILL MOVE.** **1994–2025 is FINAL** and is the window the piece should use.
**2026 is YTD and incomplete** — and the 43 CFR part 10 deadline surge is *still running*,
so 2026 will grow substantially. That makes the year-turn refresh genuinely newsworthy for
this collection rather than housekeeping: **the 2026 count is the first full post-deadline
year and it should be its own follow-up piece.**

---

### QUEUE — additional `nagpra` candidates, ranked

**N2. Which institutions filed, and when.** *(web · MEDIUM pending measurement)*
A compliance-shaped ranking — notices filed per institution, and the gap between the 1990
statute, the 2024 regulation and the filing date. Requires the institution-name parse to be
verified and the framing rules above applied. **Do not draft until the institution column's
precision is measured.**

**N3. The regulation moved the record.** *(brief · HIGH)*
A single chart: notices per year 1994–2025 with the January 2024 regulation marked. It is
the launch piece's exhibit and can run on its own as the monthly-cadence brief. Cheap, and
it is the single most legible thing this collection produces.

**N4. ❌ KILLED — time to repatriation.** See the block above. It is not in the data, and
the near-constant 30-day interval that *is* in the data would be mistaken for it. **Record
it as a refusal rather than a backlog item**, because a future agent will otherwise
rediscover the column and publish the regulation.

**N5. The abstract that did not exist.** *(brief · MEDIUM)*
`fr_nagpra_title_index.csv`'s one genuinely publishable series is **abstract availability:
0% before 2011, 67% in 2011, 100% from 2014 on.** It is the diagnostic under **R10** and it
is a small, precise, checkable story about how a metadata practice change can manufacture
a policy trend.

### The `nagpra` refusals worth publishing

- **R10**, in full. It is the best available demonstration that this project audits its own
  classifiers rather than its sources.
- **The refusal to infer MNI.** Empty on all 2,477 notices that state none or state several
  — verified today. A blank that is deliberate and documented is a different object from a
  missing value, and this dataset marks the difference in `mni_basis`.
- **The refusal to claim tier A.** Zero hand-ruled rows in a 51,338-row bridge, stated
  rather than hidden.
- **Ambiguous containment declines to choose.** `resolve_method =
  ambiguous_containment:2:Delaware Nation, Delaware Tribe of Indians` — the resolver leaves
  `tribe_id` empty and keeps the verbatim name. **2,787 unresolved rows** carried openly.
- **1,089 refused fragments** in `review/nagpra_refused_fragments.csv`, of which **733 are
  `prose_not_a_name`** — the most common being the sentence *"has determined that the
  cultural items listed in this notice meet the definition of unassociated funerary
  objects"*, refused 142 times. A parser that will not treat a statutory recitation as a
  party name.
- **The refusal to re-run `code/41_build_codebooks.py`** mid-build, *"because re-running it
  here would fold their in-flight work into a documentation artefact and risk the guard."*
  The cost is disclosed: the codebook's row count is stale at 47,460 against a true 58,067.
  **A known-stale number that is documented as stale is a different thing from a wrong
  one.**
- The filename incident, which is a real refusal of convenience: these outputs were first
  written to `nagpra_notices.csv` and **silently clobbered a concurrent agent's much richer
  NAGPRA build**. It was caught only because a row count read back **1,180 against the
  6,606 written**. The index was renamed rather than the richer file being rebuilt. *An
  interruption must not look like a completion*, and neither must a collision.

> **✅ VERIFIED 2026-08-26.** 6,729 notices ✅ · 6,606 index ✅ · 51,338 bridge rows ✅ ·
> notice-type split, institution ranking, MNI basis invariant (2,315 + 162 = 2,477) all
> reproduce. **Two corrections stand: the surge is 496 / 707 / 900 from the product, not
> 496 / 670 / 830 from the index; and time-to-repatriation is not computable.** All eight
> documented misattributions are still live.

---

<!-- SLATE:lobbying -->
## 6. `lobbying` · shelf `standard`

### What the data can support today

| | |
|---|---|
| `data/clean/native_entity_lobbying_disclosures.csv` | **27,796 filings**, `filing_year` **1999–2026** *(measured 2026-08-26)* |
| CY2026 to date | **643 filings** — Q1 331 · Q2 311 · Q3 1. Max `dt_posted` **2026-08-04** *(measured 2026-08-26)* |
| last complete calendar year | **2025 — 1,377 filings** |
| attributed spend | **$725.2M** *(documented 2026-08-06; re-verify)* |
| the issue-family series | `lobbying_issue_family_year.csv` — **quote `share_of_family_mentions`, never a raw count** |

**Three denominator warnings, all of which have already caused a wrong number in this
repo.**

1. **27,796 is right; 43,963 is wrong and matches no lobbying file at any stage.** The raw
   pull is **39,448**. (`docs/DOC_CONTRADICTIONS_2026-08-26.md` B4.)
2. **"97.0% keyed — the highest keyed rate of any Cedar dataset" is off by 29 points in a
   sales context.** The denominator is the *post-match* file. 39,448 filings were scored,
   **27,796 matched (70.5%)**, 11,652 did not. True coverage of the pulled universe is
   **26,955 / 39,448 = 68.3%**. (`docs/DOC_CONTRADICTIONS_2026-08-26.md` A6.) **Do not put
   97% in a public sentence.**
3. **Spend cannot be apportioned to an issue.** `spend_usd` is a filing-level total
   covering every issue in the filing. **Any "tribes spent $X lobbying on gaming" figure
   would be fabricated.** It was not computed and must not be.

---

### ✅ THE THREE HARD BLOCKERS WERE CLEARED 2026-08-26 (evening). Read this before the original text below.

*The original blocker text is kept verbatim underneath, because it is the diagnosis and
deleting it would delete the reasoning. What follows is what changed.*

| blocker | state | evidence |
|---|---|---|
| **1 — Salt River Project live in the panel** | **CLEARED** | `code/351_rebuild_lobbying_panel_from_corrected_disclosures.py` rebuilt `tribe_year_lobbying_panel.csv` in place from the corrected disclosures. `TRBF-SRPMCP-00` now reads **141 filings / $10,414,000**, exactly the corrected reading `docs/ANOMALY_REPORT.md` FA-01 states. Panel 5,051 → 4,997 rows; filings 27,796 → 26,484; spend $725,223,724.52 → **$680,041,390.52**. The rebuild's aggregation is `05_match_filings_v2.py`'s own, PROVEN equivalent against the pre-65 vintage the old panel was built from (0 keys added, 0 lost, 0 field mismatches) before it was allowed to write. |
| **2 — the second, undocumented false attribution** | **CLEARED** | `code/350_withdraw_false_lobbying_attributions.py` withdrew **471 filings / $5,756,834** across 18 clients. `TRBF-SROSAR-00` now reads **13 filings / $210,000** — the tribe's own, and nothing else. Also withdrawn: `COEUR D'ALENE MINING` (8), BBEDC (135), BBAHC (99), two Bristol Bay fishermen's associations (9). All UNLINKED — no spine entity exists for any of them — never repointed, never tier X. |
| **3 — the confidence figures are pre-fix** | **RESTATED, see the table below** | the `high` slice did not move. |

**The publishing rule and its number are UNCHANGED, and that is the point.** All 471
withdrawals were `medium`. Measured after the fix:

| `match_confidence` | filings | spend |
|---|---:|---:|
| **high** | **23,741** | **$627,601,108** |
| medium | 2,743 | $52,440,282 |
| withdrawn_org_type (script 65) | 841 | $39,425,500 |
| withdrawn_false_attribution (script 350) | 471 | $5,756,834 |

> **Publish `high` only: 23,741 filings / $627,601,108.** Unchanged. **Attributed spend
> across all live tiers is now $680,041,390.52**, not $685,798,224.52 and not $725.2M.
> Anyone summing `spend_usd` must exclude BOTH withdrawal sentinels — use
> `cedar_domain.lobbying_attribution_withdrawn(row)`, which reads every mark, rather than
> testing one column. Testing `org_type_barred` alone is exactly how scripts 180 and 182
> would have re-imported all 471 on their next run.

**STILL STALE, named not fixed:** `lobbying_registrants.csv` and
`lobbying_registrant_concentration.csv` carry per-registrant and concentration AGGREGATES
computed over the 471 withdrawn filings. They carry no (entity, client) pair, so the
propagation check in `354_correction_register.py` cannot see them — **an aggregate consumer
carries the defect without carrying the evidence of it, and that is a real limit of a
pair-based check.** Fix: run `180_build_lobbying_registrant_hub.py` then
`182_rule_lobbying_registrant_native_ownership.py`, in that order (180 rebuilds the hub,
182 enriches it — the enricher runs LAST), on a quiet machine. Expect
`lobbying_registrant_client_relationships.csv` to drop ~18 rows on that run: 180 deletes a
withdrawn pair outright, where `353_propagate_lobbying_corrections_to_consumers.py`
unlinked it in place and kept the row. **Declare the drop in the correction register first
or `62` will fail on it.**

---

### ⛔ THE ORIGINAL BLOCKER TEXT, kept as the diagnosis. Verified 2026-08-26 (morning).

**Blocker 1 — Salt River Project is FIXED in the source file and STILL LIVE in the panel a
launch article would most likely quote.**

`docs/COMPETITIVE_POSITION.md` Finding 4 recorded **SALT RIVER PROJECT** — an Arizona
public power and irrigation district — attributed to the **Salt River Pima-Maricopa Indian
Community** (`TRBF-SRPMCP-00`) at medium confidence on the alias `river salt`, carrying 340
filings and $28.71M.

**In `native_entity_lobbying_disclosures.csv` it is fixed.** All three name variants now
carry a blank `entity_id` and `match_confidence = withdrawn_org_type`, with the reason
carried verbatim on every row: *"the Salt River Project, an Arizona public power and
irrigation district - NOT the Salt River Pima-Maricopa Indian Community"*, `org_type_barred
= 1`. 340 filings / $28,818,000. `review/lobbying_withdrawn_by_org_type.csv` holds all 14
withdrawn clients — **841 filings / $39,425,500** — auditable and reversible. Coeur d'Alene
Mines (123 filings / $5.33M) and City of Santa Rosa (84 / $2.31M) are withdrawn too.

**But `tribe_year_lobbying_panel.csv` was built 2026-08-05 17:28 and the disclosures were
rebuilt 2026-08-06 16:19.** The panel predates the guard. Its `n_filings` sums to exactly
27,796 and its spend to exactly $725,223,724.52 — proving it was built from the
pre-withdrawal file.

| entity | panel says | corrected disclosures say | inflation |
|---|---:|---:|---|
| **`TRBF-SRPMCP-00` Salt River Pima-Maricopa** | **$40,279,500 / 557 filings** | **$10,414,000 / 141 filings** | **+$29.9M, +416 filings** |
| `TRBF-CRDALN-00` Coeur d'Alene | $6,645,000 / 228 | $1,315,000 / 105 | +$5.3M |
| `TRBF-SROSAR-00` Santa Rosa | $5,620,334 / 317 | $3,310,334 / 233 | +$2.3M |
| `ANRC-BRBYCO-00` Bristol Bay Native Corp | $5,148,500 / 387 | $4,908,500 / 358 | +$0.24M |

> **In the panel, Salt River Pima-Maricopa is the #2 Native lobbying entity in America —
> entirely on the strength of an Arizona public power district's money.** Any "top tribal
> lobbying spenders" ranking, chart or table built from `tribe_year_lobbying_panel.csv`
> publishes the exact false attribution the project already caught and fixed.
> **Rebuild the panel from the corrected disclosures. This is blocker 1.**

**Blocker 2 — a SECOND false attribution of equal severity is live and undocumented.**

The org-type guard is a **name-form** bar. It caught "CITY OF", "MINES", "PROJECT" — and it
missed everything shaped differently. Still attributed at `medium` today:

| client as filed | attributed to | alias | filings | spend | what it actually is |
|---|---|---|---:|---:|---|
| SANTA ROSA COUNTY FL | `TRBF-SROSAR-00` | `rosa santa` | 106 | $1,495,000 | a **Florida county** |
| SANTA ROSA COUNTY, FL | same | `rosa santa` | 38 | $555,000 | the same Florida county |
| SANTA ROSA MEMORIAL HOSPITAL | same | `rosa santa` | 5 | $480,000 | a California hospital |
| TEAM SANTA ROSA ECON. DEV. COUNCIL | same | `rosa santa` | 14 | $260,000 | a Florida EDC |
| SANTA ROSA MEMORIAL | same | `rosa santa` | 13 | $142,334 | hospital |
| CHRISTUS SANTA ROSA HOSPITAL (+ CHILDRENS) | same | `rosa santa` | 6 | $78,000 | a Texas hospital system |
| SANTA ROSA JUNIOR COLLEGE | same | `rosa santa` | 25 | $0 | a California college |
| TEAM SANTA ROSA / COUNTY BD OF SUPERVISORS | same | `rosa santa` | 13 | $90,000 | |
| **subtotal wrongly on the Santa Rosa Rancheria Tachi Tribe** | | | **~220** | **~$3.10M** | |
| *the actual tribe* — SANTA ROSA RANCHERIA TACHI TRIBE | same | | **13** | **$210,000** | and it is only coded `medium` |
| COEUR D'ALENE MINING | `TRBF-CRDALN-00` | `coeur dalene` | 8 | $90,000 | the mining company, variant the guard missed |
| BRISTOL BAY ECONOMIC DEVELOPMENT CORP | `ANRC-BRBYCO-00` | `bay bristol corp` | 135 | $2,048,500 | **BBEDC is a separate CDQ nonprofit** |
| BRISTOL BAY AREA HEALTH CORP | `ANRC-BRBYCO-00` | `bay bristol corp` | 99 | $500,000 | **BBAHC is a separate health org** |
| BRISTOL BAY DRIFTNETTERS / REG. SEAFOOD DEV. ASSN | `SGVF-BRBYAS-00` | `association bay bristol` | 9 | $18,000 | fishermen's groups |

**`TRBF-SROSAR-00` holds $3.31M in the corrected file and only $210,000 of it is the
tribe's.** In row count that is a *larger* error than Salt River Project was, and unlike
Salt River it is documented nowhere.

**Blocker 3 — the published confidence figures are pre-fix and must be restated.**

Current distribution, measured 2026-08-26:

| `match_confidence` | filings | spend | share of $725.2M |
|---|---:|---:|---:|
| **high** | **23,741** | **$627,601,108** | 86.54% |
| medium | 3,214 | $58,197,116 | 8.02% |
| withdrawn_org_type | 841 | $39,425,500 | 5.44% |

- **"$97.6M of $725.2M (13%)" no longer describes anything.** $58.20M + $39.43M = $97.62M
  exactly — the $97.6M *was* the medium bucket before 841 filings were pulled out of it.
  **Medium today is $58.2M / 8.0%.**
- **"$725.2M attributed" is now wrong by construction.** It includes $39.4M explicitly
  marked as not-a-Native-entity. **Attributed spend is $685,798,224.52.** Anyone summing
  `spend_usd` without filtering `match_confidence != 'withdrawn_org_type'` re-imports the
  entire error.

> ### THE PUBLISHING RULE FOR THIS SHELF
> `docs/METHODOLOGY_LOBBYING.md` §6 already states it: **"Every attributed dollar carries a
> tier. Only tier A publishes. A medium-confidence name match is a candidate, never a
> figure."**
>
> **Publish `high` only: 23,741 filings / $627,601,108.** That is the number a launch
> article carries. Everything else is a candidate list.

**A competitor who finds any of this first can dismiss the entire "never falsely attribute"
premise with one screenshot.**

---

### ★ LAUNCH PIECE — *Gaming has more than halved as a share of what Indian Country lobbies about*

**Format:** paper, with an 800-word web companion. **Confidence: MEDIUM-HIGH** — the
finding survives every control applied and carries a published error rate that bounds it.

**The claim.** Between 1999–2007 and 2018–2026, gaming fell from **14.4% to 5.7%** of
tribal lobbying's issue composition — from second-largest family to seventh — while
**public safety tripled, 2.0% → 6.2%**. Culture/repatriation and agriculture each roughly
tripled off very small bases.

**⭐ THE FIELD IS EMPTY, AND THAT IS THE STRONGEST FACT ABOUT THIS SHELF.**
`docs/PUBLISHED_LANDSCAPE_2026-08-26.md` §4 item 5: **zero tribal lobbying analysis was
found anywhere** — not at CICD, NNI, NBER, NAFOA, NCAI, NCAIED, First Nations, Oweesta or
USET. *"This is the cleanest gap in this sweep."* 27,796 LDA filings across 27 years is an
unclaimed field with no incumbent, no prior art to cite, and no superlative to withdraw.
**Which is exactly why the three blockers below have to be cleared rather than worked
around** — there is nobody else's error to hide behind, and the first published analysis of
tribal lobbying will be the one everyone checks.

**Why this is a real finding and not an artefact — this is the piece's spine.**

- **The federal disclosure system cannot answer this question**, which is why the analysis
  exists. The LDA gives filers a 73-code issue taxonomy, and for this population it
  collapses: **18,403 of 22,699 coded filings carry `IND`**. A tribe lobbying on broadband,
  a tribe lobbying on water rights and a tribe lobbying on casino regulation all file under
  the same code. The free-text `specific_issues_text` is the only place the subject appears.
- **Classification runs on issue segments, not filings.** Filers write one issue per line
  and repeat the block across activity records separated by `|||`; classifying the
  concatenated blob would count the same line up to nine times and would mark a filing
  "energy" because one of nine lines mentioned a pipeline.
- **The first version of this series was wrong and the correction is published.** Measuring
  each family's share of *classified filings* showed almost every family rising — because
  the mean number of families disclosed per filing rose from **~2.0 in 2002–03 to ~3.1 in
  the 2020s**. Filings got wordier. The verbosity confound is published as its own file,
  `lobbying_disclosure_verbosity_year.csv`. The verbosity-neutral measure is
  **composition**.
- **A prior that failed is reported.** See refusal **R11** — the gaming share did *not*
  move to health. Health is flat (8.1% → 8.3%) and broadband, though it tripled, remains
  one of the two smallest families.
- **The error rate is published and it bounds one row of the table.** Exact-set match
  60.0%, label precision 0.84, recall 0.84 (n=120). The dominant error is `land_water`
  under-detection — **23 of 44 total misses** — because the pattern covers "land into
  trust" and "water rights" but not *land conveyance*, *land exchange*, *land status*,
  *Reservation Reaffirmation Act*. **The `land_water` series is a floor and its −2.7pp
  change is the least trustworthy row. Say so in the table.**

**Non-disclosure is itself a measurement, and it belongs in the piece.** Of 27,796 filings,
**8,324 disclose no issue text at all**, and a further 2,102 segments are pure boilerplate
("General tribal issues", "Monitor Indian related legislation", "Federal Representation").
**About 30% of filings tell you nothing about what was lobbied on.** That is a fact about
the LDA regime, published in a `text_status` column rather than silently dropped.

**What would make it stronger.**
- **Fix `land_water` recall, then draw a FRESH audit sample.** Do not re-score the existing
  one. This is the difference between a table with one weak row and a table with none.
- **Run the precision pass on the client universe** (the hard blocker above). The audit
  itself surfaced Coeur d'Alene *Mines*, Salt River Project, the Metropolitan Water
  District and the City of Santa Rosa sitting in a Native-entity net.
- Have a human spot-check the audit slice. Agent adjudication published for human review is
  not a human gold standard, and the files say so.

**FINAL vs WILL MOVE.** The **1999–2025 composition series is FINAL.** The **2026 window is
YTD — 643 filings through `dt_posted` 2026-08-04, Q3 essentially empty (1 filing) and Q4
not filed yet.** Q4 LDA filings post in January, so this collection gains materially at the
year turn. **Do not include 2026 in any window comparison** — `docs/CONTENT_ANALYSIS.md`
excludes it from all of them, and the piece should say why.

---

### QUEUE — additional `lobbying` candidates, ranked

**L2. Filings measure the relationship. Dollars measure the mandate.** *(web · HIGH on
filing counts, MEDIUM on dollars)*
**429 distinct registrants** ✅ (426 distinct `registrant_id`). Every
`docs/SUBSET_DATASETS.md` figure reproduces exactly, measured 2026-08-26: Sonosky Chambers
**1,858**, Hobbs Straus **1,603**, Holland & Knight **1,298**, Ietan **800**, PACE **766**.

**But the filing-count ranking is not the story — this is.** The two firms with the most
filings, **Sonosky and Hobbs Straus — the historic Indian-law bar — rank 10th and 15th by
dollars** ($13.37M and $7.76M). **Akin Gump captures $95.77M on 689 filings — more than
Sonosky, Hobbs Straus, Holland & Knight, Ietan and PACE combined ($106M on 6,325 filings)
— at one-ninth the filing volume.**

| # | registrant | filings | spend | clients |
|---:|---|---:|---:|---:|
| 1 | Sonosky, Chambers, Sachse, Endreson & Perry | 1,858 | $13.37M | 55 |
| 2 | Hobbs, Straus, Dean & Walker | 1,603 | $7.76M | 36 |
| 3 | Holland & Knight | 1,298 | $24.57M | 51 |
| 4 | Ietan Consulting | 800 | $29.34M | 30 |
| 5 | PACE (fka PACE-Capstone) | 766 | $31.13M | 21 |
| 6 | Spirit Rock Consulting | 741 | $24.68M | 24 |
| **7** | **Akin Gump Strauss Hauer & Feld** | **689** | **$95.77M** | 26 |
| 8 | Peebles Bergin (fka Peebles Kidder) | 614 | $3.01M | 18 |
| 9 | Mapetsi Policy Group | 577 | $16.20M | 11 |
| 10 | Sense Incorporated | 538 | $0.02M | 13 |

**Law firms and tribes both want this and neither can get it.** Distinct buyer, small
effort, and a genuinely counter-intuitive lead.
**Caveat that must be in the piece:** filing counts are robust; **per-registrant dollars
inherit the medium-confidence contamination in Blocker 2. Re-run the dollar column on
`high`-only before publishing it.**

**L2b. $243.8M of tribal lobbying that we cannot name a client for.** *(brief · HIGH)*
`lobbying_unmatched_clients.csv` holds **515 clients and $243,836,564 of unmatched spend**,
each with a stated reason: `no_alias_hit` 311 · `single_token_core_needs_ruling` 166 ·
`nickname_alias_underspecified` 10 · `ambiguous_sibling_family` 9 · `ambiguous_multiple` 6
· `generic_single_token` 4. Publishing the size and the *reasons* for the gap is a
stronger credibility move than any coverage percentage, and it doubles as a public call for
corrections.

**L3. About 30% of tribal lobbying filings say nothing about what was lobbied on.**
*(brief · HIGH)*
8,324 filings with no issue text, plus 2,102 boilerplate segments, against a 73-code
taxonomy where **81% of coded filings pick the same code**. A short, exact piece about what
the LDA regime actually discloses. It stands alone and it is the natural methods sidebar to
the launch piece.

**L4. The false-attribution piece — publish it about ourselves.** *(paper · HIGH, and it is
the highest-integrity move available on this shelf)*
Once blockers 1 and 2 are cleared, the story is: a token match on `river salt` put an
Arizona public power district's $28.7M into a tribal ledger; we caught it in our own audit;
we withdrew 14 clients / **841 filings / $39,425,500** into a reversible, auditable review
file rather than deleting them; **and then the same class of error came back through a door
the guard did not cover** — `rosa santa` matching a Florida county, two hospitals and a
junior college onto a California rancheria whose own filings are worth $210,000.
**The rule earned, twice over:** *blocking one bad-match path pushes it to the next.* A
containment guard fixed "Denver Indian Health → Native Health" and the same wrong match
arrived via the token path; an org-type guard fixed "CITY OF" and "MINES" and the same
error arrived shaped as a county name. `NAME_TRAPS` now covers 39 terms and it was still
not enough.
**Do not publish this before the fix. Publishing a live defect is not transparency — it is
a live defect with a nice paragraph attached.**

**L5. LOW — any per-filing issue label.** Exact-set match is 60%. The series are sound in
aggregate; **an individual filing's family list is not a fact to publish about that
client.** Listed so nobody builds a client-profile feature on it.

**L6. LOW — passthrough advocacy.** `advocacy_passthrough.csv` and `native_passthrough*`
exist but were not assessed here. Needs a scope and a tier before it is an article.

**L7. Who Indian Country actually lobbies.** *(brief · HIGH)*
`lobbying_target_entities.csv`, 116 targets, measured 2026-08-26: House **19,568** · Senate
**19,542** · Interior **9,757** · BIA **5,099** · USDA 1,154 · White House Office 1,154 ·
IHS 1,115 · NIGC 1,056. Pairs directly with **FR2** on the other shelf — the two together
make one good piece about the difference between where rules are written and where money
is decided.

### The `lobbying` refusals worth publishing

- **R11** — the prior that failed. Gaming did not move to health.
- The verbosity confound that would have produced a page of spurious growth findings.
- **No dollar amount may be attached to an issue family.** Not computed, and it should not
  be. This is the most tempting available fabrication on the whole shelf and the reason it
  is tempting — every reader wants that number — is exactly why refusing it is worth
  writing about.
- The 97%-versus-68.3% denominator, published against ourselves. And note that **the
  project caught this one itself, unprompted**, in `docs/LOBBYING_EXPANSION_RECONCILIATION.md`:
  *"Quoted in a sales context it is off by 29 points, against a buyer who can pull the LDA
  API and check."*
- **`position_on_native_issue` was refused as specced.** Verbatim: *"This is the
  highest-risk item in the spec, and it is not a data problem… `position_on_native_issue =
  Oppose` is a **characterisation we would be authoring**, published under our name, about
  a named organisation."* And: *"A wrong `Oppose` on a named party is defamatory in a way a
  wrong CAGE code is not."* Replaced with a derived, falsifiable `alignment ∈ {SAME |
  OPPOSED | NO_TRIBAL_POSITION_FOUND}` computed per bill from two sourced positions. **This
  is the single best refusal in the project for explaining what "evidentiary standard"
  means to a non-technical reader.**
- **A visitor log is not a meeting.** `may_promote_event_class(ACCESS → ADVOCACY)` returns
  False, enforced in code, not in a doc. WAVES visitor records are `EventClass.ACCESS`
  permanently: *"A visitor log says a person entered a building. It does not say a meeting
  happened."* And `resolve_entity` is deliberately **not** run against the WAVES
  `Description` field — `native_entity_link_basis = NOT_ATTEMPTED_BY_RULE` — because *"its
  containment tier is the one that put $2.8B on a school."*
- **No dataset about private individuals.** 0 visitor names published · 0 position rows ·
  274 NRC individuals withheld · **10,077 IBIA/IBLA natural persons blanked, each with a
  stated reason.**
- **Advocacy is not lobbying.** `is_lobbying` is narrower than `EventClass.ADVOCACY` — an
  administrative comment or an amicus brief is advocacy and is not lobbying. *"Conflating
  them would be wrong in a way that matters legally."*
- **Containment barred from keying links in admin appeals and NRC**, at a measured cost of
  60% of matches (997 → 397 linked decisions), and accepted.

> **✅ VERIFIED 2026-08-26.** 27,796 filings ✅ · 1999–2026 ✅ · `spend_usd` sums to
> $725,223,724.52 ✅ · 300 distinct `entity_id` ✅ · 643 CY2026 filings ✅ · max
> `dt_posted` 2026-08-04 ✅ · 429 registrants ✅ and all five headline registrant counts ✅.
> **"458 clients settled" is a RULINGS count, not an attribution count** —
> `lobbying_client_attribution.csv` holds 458 ruled clients of which **261 are tier A and
> 197 are tier X (excluded)**. 458 ruled, 261 accepted, 300 entities attributed. All three
> are true of different things. **Say which one you mean.**

---

<!-- SLATE:contractors -->
## 7. `contractors` — Federal Prime Contracting · shelf `pro`

### What the data can support today

*All measured 2026-08-26 from `data/clean/prime_contracts.csv` (1,217,768 rows, 38 columns).*

| | |
|---|---|
| rows | **1,217,768**, FY2000–FY2026, no gaps |
| total obligated | **$310,005,258,660.75** |
| attributed | **888,803 rows (72.99%)** · **$244,765,156,392.10 (78.96%)** · **498 entities** |
| tier split | A 586,185 rows / $176.74B / 283 entities · B 302,618 / $68.02B / 382 · **C 328,965 / $65.24B / 0** |
| last complete fiscal year | **FY2025** — 48,879 rows, action dates 2024-10-01 → 2025-09-30 |
| **FY2026** | **61,813 rows, but the archive cut it at `action_date` 2026-07-03 — a NINE-MONTH PARTIAL** |

`attributed_flag` is exactly equivalent to tier: **1 ⟺ A or B; 0 ⟺ C**. Note that the
standing rule is **tier B never publishes alone**, so `attributed_flag = 1` is *not* a
publishability test.

**⚠ FY2026 is neither closed nor calendar-to-date.** It stops 2026-07-03 because that is
where the July archive object cuts. `prime_contracts.csv` **carries no transaction-date
column at all** — only `fiscal_year` — so the endpoint is invisible from inside the file
and must be read from the retained filtered extract. Anyone reading FY2026 as "through
today" over-reads by nearly two months. Standing caveat from
`docs/PRIME_ARCHIVE_PULL_LOG.md`: *"FY2026 is a partial year and has no BEA annual
deflator, so it carries factor 1.0 — undeflated, not adjusted. **Never compare it to a
full year.**"*

---

### ★ LAUNCH PIECE — *How much does the federal flag miss? We are the only people who can answer, because we counted the same firms twice.*

**Format:** paper, with an 800-word web companion. **Confidence: HIGH on the mechanism and
the worked cases. The corpus-wide magnitude is being sized right now — see the reserved
slot.**

**Why this is the launch piece and the set-aside story is not.** `docs/PUBLISHED_LANDSCAPE_2026-08-26.md`
§6 is blunt: *"The one contracting story still open is the **undercount**. Nobody has
published how much the flag/self-certification method misses, because nobody else holds both
a flag-based count and a hand-adjudicated ownership count on the same universe. CICD called
its own dataset a 'lower-bound estimate' and never sized the shortfall. **That is Cedar
Press's contracting story, and it is the only one that is both unclaimed and
consequential.**"*

**The claim.** Every published count of Native federal contracting rests on a
self-certification flag. The flag is a box a firm ticks about itself. Cedar Press holds a
second, independent count of the same firms — hand-adjudicated ownership — and the two do
not agree. **This piece measures the disagreement.**

**The evidence — the worked cases, measured 2026-08-26.**

> **22 of the 40 hand-ruled individually-Native-owned firms carry zero Native
> self-certification on any contract row — $212.5 million of obligations.**

The largest is **Frontier Electronic Systems Corp: 998 contract rows, $204,225,019
obligated, and not one Native flag on any of them.** Therefore — and this is the sentence
the piece turns on — **no candidate set defined by the federal flag can ever reach those
firms.** They are not undercounted at the margin. They are structurally invisible to the
method everyone uses.

**And the flag fails in the other direction too, which is what makes this a measurement
rather than a complaint.** `americanIndianOwned = YES` appears on **2,846 of 8,273 rows of
the *TRIBAL* SAM extract** — Chugach, ASRC, Chickasaw Nation Industries. *"Reading
`americanIndianOwned = YES` as 'individually owned' would reclassify Alaska Native
corporations as sole proprietors."* The canonical counter-example is cleaner still:
**Goldbelt Raven LLC, an ANC subsidiary, certifies `alaskanNativeCorporationOwnedFirm = NO`,
`triballyOwnedFirm = NO`, `americanIndianOwned = YES`.**

> ### 🔲 RESERVED SLOT — corpus-wide magnitude
> A benchmark agent is sizing the undercount across the full universe now. **Drop the
> number here when it lands**, with its measurement date and the exact denominator it uses.
> Prior partial measurements in circulation, from the landscape scan: *66.7% of tier-A
> dollars by the token test*, and *241 flagged tribes against 588 recognized entities*.
> **Re-derive both against the current file before publishing either** — they pre-date the
> archive backfill.

**Supporting context that is free to cite and strengthens the piece.** SBA's own 8(a)
programme page concedes the many-to-one problem without solving it: *"Alaska Native
corporations, Tribal-owned Native Hawaiian organizations, and Community Development
Corporations **may have multiple 8(a) firms**"* — **and SBA publishes no roster mapping
those firms to their parent entities.** Quote that sentence in the methodology section. The
void is documented by the agency that created it.

**What would make it stronger.**
- **The corpus-wide number** (reserved slot above). Without it this is a strong mechanism
  piece; with it, it is the definitive statement of the field's measurement error.
- **An owner ruling on the individual-Native class.** `docs/INDIVIDUAL_NATIVE_CLASS_PROPOSAL.md`
  is marked *"AWAITING OWNER RULING"* with three open `[RULE NEEDED]` items, the class is
  **83% unresolved** (278 of 334 `UNDETERMINED`), and **the spine has no class that can hold
  these firms — 0 of 1,489.** Publishability is already computed per column:
  `publishable_contract_facts = Y` on all 334, **`publishable_entity_name = N` on 15**
  (possible personal names), and any aggregate cell resolving to **fewer than 3 firms is
  suppressed**. Individual-Native **never** appears in tribal totals.

**FINAL vs WILL MOVE.** The 40 hand-ruled firms are a fixed adjudicated set. The contract
rows under them move with FPDS restatement.

---

### ⛔ BEFORE ANY DOLLAR TOTAL FROM THIS SHELF IS PUBLISHED

**$310.01B must never appear beside CICD's $26.6B without the reconciliation table.** Two
Native-contracting totals that disagree is the worst possible first impression, and they do
not actually disagree — they are different quantities. Measured 2026-08-26:

| | CICD (USAspending) | Cedar Press (`total_obligations`, nominal) |
|---|---:|---:|
| 2025 | **$26.6B** prime **+ sub** | **$18.63B** prime only, FY2025 |
| 2016–2025 | **~$200B** prime + sub | **$173.5B** total / **$145.8B** attributed, FY2016–25 |
| 1981–2021 | **$202B** prime + sub, **2021 dollars** | $164.9B attributed FY2000–2021, **nominal**, no pre-2000 |

Four definitional differences explain the whole gap and **all four go in any published
comparison**: (a) CICD includes subcontracts, our prime file does not; (b) CICD reports
calendar/action year, we report fiscal year; (c) CICD's 1981–2021 figure is inflation-adjusted
to 2021 dollars, ours is nominal; (d) CICD's recent series uses self-certification flags,
ours uses the identifier ledger. Applied, they are the same order of magnitude.

**And "79.0% attributed" is a blended figure over two differently-constructed populations,
not a quality measure.** **FY2023–FY2026 rows are 100% `attributed_flag = 1` — 209,495 of
209,495** — because those years landed pre-filtered to Cedar's identifier population.
FY2000–2022 came from the BGOV-filtered `.dta` at a mixed rate (FY2000 48%, FY2021 78%).
**The upside: FY2025's $18.63B *is* "obligations to identified Native entities," which is
exactly the right quantity to set beside CICD's $26.6B. State the construction and the
comparison becomes an asset.**

---

### QUEUE ITEM PROMOTED TO SECOND — *The Native-specific set-asides are not how Native firms win federal work*

**Format:** paper. **Confidence: HIGH on the arithmetic. Demoted from launch on the owner's
direction that Native-versus-general comparisons are deprioritised, and because
"the 8(a) programme drives Native contracting" is already taken (CICD 2023 and 2026).**
The 0.49% figure is still ours and still striking — it is the *within-Native composition*
that CICD has not published, not a Native-versus-non-Native share — so it runs second, not
never.

**The claim.** Of **$244.77 billion** in federal prime obligations Cedar Press can attribute
to Native entities FY2000–FY2026, the two set-asides *designed* for Native firms — **Indian
Business** and **Buy Indian** — account for **$1,200,514,511. That is 0.49%.**

**The evidence**, measured 2026-08-26 on the current 1,217,768-row file:

| set-aside | rows | obligated | attributed rows | attributed $ |
|---|---:|---:|---:|---:|
| None reported | 598,321 | $127,468,151,786.55 | 470,756 | $110,273,024,772.91 |
| **8(a)** | 364,150 | $117,056,105,547.54 | 294,608 | **$97,327,112,765.01** |
| Small Business | 163,064 | $43,008,061,725.27 | 98,943 | $31,931,209,403.53 |
| Other | 55,439 | $16,564,932,495.90 | 5,706 | $2,310,705,228.11 |
| HUBZone | 17,362 | $3,987,251,629.46 | 10,235 | $1,722,589,711.66 |
| **Indian Business** | 9,934 | $1,056,694,372.99 | 4,313 | **$706,933,970.73** |
| **Buy Indian** | 9,498 | $864,061,103.04 | 4,242 | **$493,580,540.14** |

**8(a) is the channel.** $97.33B of attributed dollars — **39.8% of everything** — against
0.49% for the two Native-specific programmes combined. The story is not that the Native
set-asides are small; it is that **a general small-business programme, not an Indian
programme, is the mechanism by which Indian Country reaches the federal market.**

**And the share carrying no Native preference at all is 59.75%** — $146,237,529,116.21 of
$244,765,156,392.10. That figure is **rising**: attributed dollars that *do* carry a
preference flag fall from **51.3% in FY2008 to 30.3% in FY2026**
(`docs/PRIME_ARCHIVE_PULL_LOG.md` line 188). A pooled number averages over a trend and
must be dated.

**Three method points that have to be in the piece, because they are what make the number
defensible.**

1. **A set-aside is a property of the AWARD, not of each modification.** The USAspending
   archive reports set-aside per *transaction* and leaves it blank on **56% of rows**. Read
   transaction-level, the archive and the hand-checked `.dta` **disagree on 59.6% of shared
   contracts**, and **4,580 contracts the `.dta` calls 8(a) land in "None reported."**
   Published naively that would have inflated the no-preference share purely on a
   definition change between sources. **Fill set-aside forward from
   `contract_award_unique_key` across all years before computing any share.** That fill is
   already applied on disk — `setaside` has zero blanks across 1.2M rows — so the 0.49% is
   computed the way the rule requires.
2. **Use the ATTRIBUTED denominator, not all rows.** All-rows gives 0.62% and silently adds
   tier-C rows never established as Native. Base-award grain gives 11,621 of 455,080 =
   2.55%. **Say which grain you used.** Three defensible numbers exist and they are not the
   same number.
3. **8(a) is a lower bound.** 4,317 contracts the `.dta` calls 8(a) have no archive
   set-aside in any year — a real source disagreement, and *"the archive's silence is a
   non-report, not an assertion of 'no set-aside used'."*

**⚠ Correction to make in our own documents first.** `docs/CROSS_SOURCE_VERIFICATION.md`
and `AGENTS.md` say **60.9%** with a paired **$86.19B**. Measured today it is **59.75%**
and **$146.24B**. Close, and it moved in the direction the trend predicts — but it does not
reproduce, and the dollar figure is off by $60B. Every set-aside figure in
`docs/SUBSET_DATASETS.md` lines 49–56 and `docs/INDIAN_INCENTIVE_PROGRAM_GAP.md` line 30 is
stale for the same reason (all measured at 617,142 rows). **Only the 0.5% headline
survives, as 0.49%.**

**Prior art, handled not fought.** CICD has published on 8(a) as the dominant channel (2023,
2026). **Cite it, then add what is ours**: the FY2026 endpoint, the award-grain set-aside
fill, the 59.75%-and-rising no-preference trend, and the 0.49% Indian Business + Buy Indian
figure, which is not in anyone's published work. **Lead with the addition.**

**What would make it stronger.**
- **The Indian Incentive Program is the missing half of this story and it is structurally
  invisible.** See C2.
- Fix `prime_contracts_published.csv` (see the defect list) so the piece can point readers
  at a download.

**FINAL vs WILL MOVE.** **FY2000–FY2025 is FINAL.** **FY2026 is a nine-month partial cut at
2026-07-03** and will grow by roughly a quarter when the archive next replaces. Additionally
**FPDS restates retroactively up to five years**, so even closed years move slightly — say
so once, in the method note.

---

### QUEUE — additional `contractors` candidates, ranked

**C0. ⭐ THE FIRST PRODUCT THE LANDSCAPE SCAN POINTS TO — a ranking of top tribal, ANC and
NHO federal contractors, with the ownership chain shown.** *(product + web article · HIGH ·
**write this immediately after the launch piece, or instead of it if speed wins**)*
The scan checked seven outlets — Tribal Business News, Indigi Today, ICT, Native News
Online, GGB, CDC Gaming, Casino City Press — and **it does not exist anywhere.** It is
(a) demonstrably unpublished, (b) **directly producible today from the 498-entity attributed
set with no new pull**, (c) impossible for the incumbents by construction — TBN has no
USAspending capability, CICD's method is flag-based and its policy is anonymisation, **and
BGOV ranks Afognak at #174 and cannot name Alutiiq Pacific** — and (d) **already demanded by
a public dispute: a U.S. senator and the Poarch Band fought over whose 8(a) contracts count
as whose, and nobody had a dataset to settle it.**
**It carries the entity-identification question in its sharpest form. That is a feature —
answer it once, at launch, on the artefact that most needs it.** Two constraints: the D&B
mark bars bulk legal name and address on pre-2022-04-04 base awards (contract facts
publish), and the tier-B-never-publishes-alone rule governs which entities can be named.
**On the owner's speed criterion this is the single best piece in the document: zero new
data, zero blockers, and a named public dispute waiting for it.**

**C1b. ⭐ THE MOAT, PUBLISHED — the commercial-identity layer.** *(paper · HIGH)*
Gap **G1**. UEI / CAGE / EIN → owning Native entity. **Nothing found in the entire landscape
sweep publishes it.** CICD's crosswalk deliberately stops at government entities; **CICD's
own CAGE-linked list was handed to HigherGov and never published**; NEED links to contracts
by *cross-referencing business names against USAspending*, not by carrying vendor
identifiers; NBER's entity-level work sits behind a Census RDC. *"This is the moat and it is
intact — the one asset in the whole build that nobody else has published, and no incumbent
has announced an intention to."*
The publishable spine of the piece: **20,559 identifier links, of which only 1,538 are
`tier_A_ruled`** — hand-checked, not inferred — plus the dated subsidiary ownership graph
(Afognak → Alutiiq Pacific; Ho-Chunk → Wincomp dba All Native) that makes attribution
correct *as of a date* rather than as of today.
**Two withdrawals the scan requires.** Do not say **"first"** to link tribal governments to
differently-named enterprises — **USET's *2022 Tribal Enterprise Directory*** (600+
enterprises, 33 tribes, with an SBA 8(a) index) is the regional precedent. Say: ***first
national, machine-readable, identifier-bearing tribal enterprise crosswalk, corroborated
across independent federal datasets.*** And credit the **CICD Native Entity Connector
Crosswalk as an input** on the methods page, once.

**C1c. The ANC share of the 8(a) programme.** *(web · MEDIUM)*
**Never published** (scan §8C.5). And it sits on the coverage advantage that is *"largest
and least contested"* — NEED is federally recognized tribes, lower 48, only: **no ANCs, no
NHOs, no state-recognized tribes, no Alaska.** Our spine carries 173 ANC village corps, 12
ANRCs, 210 NHOs, 228 Alaska Native villages, 64 state-recognized tribes.
**⚠ Verify before selling it.** `AGENTS.md` line 541 records that the inherited
`hci_analysis.do` identifies **lower-48 tribes only**, with ANCs appearing solely as
exclusions and **no NHO identification anywhere in it.** *"The ANC/NHO advantage is real in
the spine; verify it is real in the attribution before selling it."*

**C2. The 5% rebate nothing can see.** *(paper · HIGH on the structural finding, and it is
the most intellectually interesting piece on this shelf)*
**25 U.S.C. 1544** / DFARS 252.226-7001 gives a DoD prime a **5% rebate** on amounts it
subcontracts to an Indian organization or Indian-owned economic enterprise. It is *"a
subsidy on the buyer's side of a subcontract, not an award to a Native entity.* **Nothing
in a prime-award file can show it, by construction."** The rebate is paid by **modifying
the prime's existing contract**, funded by an OSBP MIPR — *"It never becomes its own award
record, so there is no transaction for FPDS to capture."*
Three findings that make this a piece rather than a caveat:
- **DoD requests well below what Congress appropriates, every year.** FY2026: **7.613
  requested against 24.613 executed.** Corroborated independently by **eleven Arctic Slope
  Regional Corporation lobbying filings, 2019–2021**, seeking *"Legislation to restore
  direct appropriations for the Department of Defense Indian Incentive Program"* (H.R. 2968
  / S. 2474, 116th — **neither bill is in `native_bills.csv`**, which is its own finding
  about the bills collection).
- **The line was renamed.** "Indian Incentive Program" in the FY2024–25 books became
  **"Indian Financing Act"** in FY2026–27. *"String-matching on one label alone will
  silently truncate the series at FY2025."*
- **The deepest point, and it reframes the whole shelf: 25 U.S.C. 1452(e) defines an
  "economic enterprise" as 51% owned by *Indians* — individuals, not tribes.** *"The
  preference channel and our entity model are keyed on different definitions of Native
  ownership."*
**Status: feasibility only. NO DATA PULLED.** Route A (FPDS) is closed; Route B (FSRS)
gives the eligible base but never the programme; **Route C — DoD's own P-1 Line 30 budget
justification — is CONFIRMED and cheap.** The ceiling on the eligible base is measured:
22,484 subaward rows have a DoD prime, **5,773 go to Native-flagged subs, $12.10B** — and
*"it must never be presented as IIP spending."* **Do the P-1 pull, then write this.**

**C3. One entity, many UEIs: the nine-year clock.** *(web · MEDIUM — the count reproduces,
the published dollars do not)*
SBA's 8(a) term is **nine years and non-renewable per firm**, so a tribe or ANC wanting
continued access must stand up a *new* legal entity with a *new* UEI — same name, same
address, fresh clock. Measured 2026-08-26 against `prime_contracts.csv`: **267 name-clusters
covering 623 cluster memberships**, exactly as documented.
**⚠ But 623 and $14.98B both double-count.** A UEI registered under two legal names joins
two clusters. **Distinct UEIs = 585. Deduplicated dollars = $13,192,922,268.65** — the
documented $14.98B **over-states by $1.77B (13.4%)**. Live example: `NATIVE AMERICAN
SERVICES` and `NASCENT GROUP JV` are two clusters sharing the same two UEIs and their $423M
is counted twice. **Publish 267 clusters / 585 distinct UEIs / $13.19B**, or say explicitly
that 623 counts memberships.
**⚠⚠ And there is no artefact behind the claim.** The numbers live in **one place** — the
docstring of `code/169_build_identifier_graph.py`, lines 45–49 — and **the script has never
been run.** None of its five declared outputs exist. **Run 169 and log it before this
publishes.**
Supporting evidence that the mechanism is real: **415 of the 623 cluster UEIs carry at
least one `reported_8a = 1` row**; median cluster FY span is **11 years**, consistent with
sequential nine-year terms rather than simultaneous registrations; cluster sizes are 214
pairs, 30 triples, 14 quads, 6 fives, 2 sixes, 1 seven.
**Publishability:** cluster names DO publish — these rows come from BGOV and the
USAspending archive, not a SAM extract, so the D&B mark does not attach (stated explicitly
in `docs/codebooks/02f_individual_native_verification.md` line 86). **Two constraints that
do bite:** a cluster whose name is a person's name does not publish (sole-proprietor
privacy stacks independently of D&B), and **these are tier-C unattributed rows — the names
publish, no attribution to any tribe publishes with them. The cluster is a question, not a
finding.**

**C4. ⬆ PROMOTED TO THE LAUNCH PIECE — the self-certification undercount.** See above.
*(Note the count correction: this queue item previously read "14 of the 40." The current
figure carried by the owner and the benchmark work is **22 of 40, $212.5M**. Re-measure and
date it before drafting; do not inherit either number from this document.)*

**C5. The SAM FY2000–2007 backfill exists and it is one-sixth done.** *(brief · HIGH,
internal-facing)*
**8,273 rows landed 2026-08-26 17:29** — `sam_prime_contracts_fy2000_2007.csv`, FY2000:34
through FY2007:2,022, `date_signed` 1999-10-04 → 2007-09-30, `action_obligation` sum
**$1,240,291,955.76**. **But only the TRIBAL variant is on disk** (`matched_variants` =
TRIBAL on all 8,273; token `zrlwsqiydG`). The INDIAN, ALASKAN NATIVE and NATIVE HAWAIIAN
entity-owned extracts and **both** INDIVIDUAL_NATIVE_OWNED extracts are still undownloaded —
**five of six tokens unspent.** Anyone reading START_HERE's *"all six accepted"* as "all six
on disk" under-counts by five variants.
The genuinely new material against the existing 109,578 FY2000–2007 rows is **480 PIID_NEW
rows** (393 in the Native universe, 203 distinct PIIDs, 95 UEIs, **$17,139,716.37**) plus
171 PIID_HELD_NEW_FY ($7,923,600.55). **SAM is TRANSACTION grain; `prime_contracts` FY2000–
2007 is AWARD-YEAR-VENDOR grain. Row counts are NOT comparable across the seam** — and the
reconciliation file says so on all three of its rows.
The `_PUBLISHABLE` variant strips **10 D&B columns** — legal name, DBA, ultimate parent
name, street 1 and 2, city, state, ZIP, country — with `dnb_open_data_restricted = 1` on
**100%** of rows. `dnb_awardee_legal_name` is populated on 8,269 of 8,273, so the strip does
real work. **UEI, CAGE and `ultimate_parent_uei` survive: they are federal identifiers, not
D&B Open Data.**

**C6. LOW — a finding built and then quarantined.** The "147 UEIs the `.dta` never saw /
$549,070,387" headline is **not publishable as stated**, because **82.7% of those dollars
($454.2M of $549.1M, 63 of 147 UEIs) rest on a tier-B ledger link whose own rationale reads
"Algorithmic name clustering, unreviewed."** Listed because the *quarantine* is
publishable even though the finding is not.

### The `contractors` refusals worth publishing

- **The set-aside definitional trap** — 59.6% transaction-level disagreement, 4,580
  contracts reclassified by a definition change between sources. Publishing naively would
  have moved the headline number.
- **The IIP structural invisibility.** A federal preference programme that *by construction*
  produces no award record.
- **The self-certification counter-examples**, in both directions — Goldbelt Raven
  certifying NO, and 2,846 ANC/tribal rows certifying `americanIndianOwned = YES`.
- **The guards, at scale.** ~2.2M guard refusals across the prime and sub legs, of which
  **435,382 come from one rule**: *"An entity whose whole distinguishing core is one
  non-trap word — Hamilton, Elem, Enterprise, Craig, Spokane, 'Native Health' — cannot be
  told from a company that shares it."* 4,000 `REFUSED_BY_GUARD` rows are published *"so
  the refusal is auditable rather than silent."* And: *"the guards can only reject an
  answer, never invent one."*
- **The federal roll-up trap.** UEI `NW2RJN8TQQW1` `GOVERNMENT OF THE UNITED STATES` carries
  **29 children** — BIA, IHS, Army, tribally-controlled grant schools — and *"a single one
  of these would contaminate every child beneath it."* Also: `immediate_parent_uei` and
  `domestic_parent_uei` are populated on **0 rows** in all three FPDS extracts; all
  hierarchy is `ultimate_parent_uei`, and **190 children appear under more than one
  ownership parent.**

### Defects to fix before any `contractors` piece ships

1. **`prime_contracts_published.csv` cannot ship as-is.** It is column-filtered, not
   row-filtered — byte-identical in row set to `prime_contracts_awards.csv` (455,080 rows)
   — and the 6 columns it drops include **`confidence_tier` and `attributed_flag`**. So it
   retains **185,554 unattributed award rows** while removing the two columns that encode
   "may this publish?". Against the tier-B-never-publishes-alone rule, this is the wrong
   file to point a reader at.
2. **`prime_contracts_entity_year.csv`'s `n_contracts` counts transactions (888,803), not
   contracts.** Award grain is 455,080 total / 269,526 attributed. Any "N contracts" claim
   off this column is wrong by roughly 2×.
3. **The archive stamp is a global constant, contrary to its own guarantee.** Every archive
   row's `source_authority` reads `stamp 20260806`, but `source_file` on FY2017–FY2026 rows
   reads `..._20260706.zip` and `_SOURCE_MANIFEST.csv` agrees. `docs/PRIME_ARCHIVE_PULL_LOG.md`
   line 19 promises the opposite. Row counts show no double-append so the damage is
   provenance-only — but **no vintage claim may be sourced from `source_authority`.**
4. **`FY2026-DEFLATOR-CONVENTION` is unresolved and owner-blocking.** Three datasets —
   `prime_contracts.csv`, `federal_funding_transactions.csv`, `subawards.csv` — deflate
   FY2026 two different ways. It *"needs an owner's decision, applied across all three
   together, not one at a time."* **Any cross-collection real-dollar chart is blocked on
   this.**
5. `data/clean/coverage_audit.csv` is now current, but **all of `dist/`** still records
   prime at 617,142 rows / FY2000–2022 / 470 entities.

---

<!-- SLATE:subcontracting -->
## 8. `subcontracting` · shelf `pro`

### What the data can support today

*All measured 2026-08-26 from `data/clean/subawards.csv` (63,548 rows, 52 columns).*

| | |
|---|---|
| rows | **63,548** ✅ |
| `subaward_amount` total | **$39,433,964,351.81** (0 nulls) |
| span | FY2001–FY2026; `subaward_date` **2001-08-18 → 2026-08-03** (0 nulls) |
| **Native entity on either side** | **63,504 of 63,548 = 99.93%** ✅ — only **44** rows have neither |
| `prime_native_tribe_id` alone | **26,430 = 41.59%** ✅ (149 distinct tribes) |
| `sub_native_tribe_id` alone | 38,336 = 60.33% (575 distinct tribes) |
| 2026 to date | **3,457 rows**, max `subaward_date` **2026-08-03** |

**Quoting the 41.59% alone understates this dataset badly.** It is the *prime-side*
linkage. The dataset's actual coverage claim is 99.93%.

**The FY2021–2024 hole is upstream and it is proven three ways.** Rows per FY: 2011:1,953 ·
2012:3,106 · 2013:3,669 · 2014:4,963 · 2015:5,248 · 2016:5,637 · 2017:5,569 · 2018:8,589 ·
2019:9,373 · 2020:3,884 · **2021:173 · 2022:89 · 2023:120 · 2024:166** · 2025:7,360 ·
2026:3,457. The raw corpus (22 zips, 6,613,471 rows) holds **literally zero** FY2021–2024
rows; `_state.json` holds 22 finished jobs, **none of them fy2021–fy2024** — *"The four
years in the middle were never submitted"*; and every row's fiscal year equals its own
job's year — *"zero bleed — so the missing years cannot be hiding inside a neighbouring
chunk."* The 548 surviving rows come from elsewhere entirely, and **FY2024 has no FSRS rows
at all** (all 166 are `funding_forward_fill`).

**Hard floor:** subcontracting **cannot reach 2000.** FSRS began under FFATA in 2010.

---

### ★ LAUNCH PIECE — *$2.27 billion of federal subcontracting is one tribe's firm hiring another tribe's firm*

**Format:** ≈800-word web article with a longer method appendix. **Confidence: HIGH on the
figures, MEDIUM on interpretation** — see the caveat.

**The claim.** Measured on the full 63,548-row file, the four directions of Native
subcontracting are:

| direction | rows | dollars |
|---|---:|---:|
| Non-Native prime → **Native sub** | 37,074 | **$22,552,607,137.36** |
| **Native prime** → non-Native sub | 25,168 | **$14,052,426,637.88** |
| **Both sides Native** | 1,262 | **$2,789,908,063.57** |
| …of which **cross-tribal** — a Native prime hiring a *different* tribe's firm | **707** | **$2,270,892,876.82** |
| …of which within one entity | 555 | $519,015,186.75 |

**The cross-tribal figure is the genuinely novel one and it is the lead.** Prime-award data
cannot see it at all — it is a Native-to-Native commercial relationship that exists only
in the subaward layer. It is also, in `AGENTS.md`'s own framing, *"empirical input-output
linkage data — observed tribal supply chains,"* which is why this piece has a second
audience beyond subscribers.

**The other two rows carry the counter-story and the piece must run both.** **$14.05
billion enters a Native prime and leaves to a non-Native subcontractor**, against $22.55
billion arriving the other way. Neither number is a leakage estimate — they are gross flows
in a threshold-gated reporting regime — but the *shape* is the thing a tribal economic
development office cannot get anywhere else.

**Largest both-sides players**, measured: **The Chickasaw Nation** (`TRBF-CHKNAT-00`, tier
A) — 681 rows / $612.5M as prime, 416 rows as sub, and **all 416 of its sub rows are
both-sides**. **Arctic Slope** (`ANRC-ARCSLO-00`, tier B) is largest by prime dollars
($1.74B) and near-symmetric ($1.68B as sub). `subaward_entity_rollup.csv` holds 450
entities, of which **148 appear on both sides**.

**Three caveats that go in the text, not the footnotes.**
1. **The FY2021–2024 hole.** Four fiscal years are effectively absent for reasons upstream
   of Cedar Press. **Never chart the year series without marking them.** State the
   three-way proof; it is what makes the gap a finding rather than an omission.
2. **Every dollar total here is a lower bound of unknown tightness.** FSRS reporting is
   threshold-gated. The build log says it in those words.
3. **`FY2023 is a partial year. Never chart it as a decline."** — the log's own instruction,
   about a different partial year, and the same rule now applies to FY2026.

**What would make it stronger.**
- **The SAM org role request (10/day → 1,000/day)** unblocks the FY2021–24 retry. Subawards
  need ~2,733 paginated calls and are **not attemptable** without it. This is the single
  highest-value unblocking action for this shelf.
- Run `py -3 code/121_pull_subawards_api.py canary` to test whether the upstream fleet
  produces files again. **Never raise `MAX_INFLIGHT` above 1.**

**FINAL vs WILL MOVE.** **FY2001–FY2025 is FINAL as held** (with the FY2021–24 hole marked).
**FY2026 is YTD through 2026-08-03 — 3,457 rows.** This shelf gains substantially at the
year turn, and would gain far more if the upstream outage resolves.

---

### QUEUE — additional `subcontracting` candidates, ranked

**S2. A firm reported as its own subcontractor.** *(brief · HIGH)*
`prime_sub_network.csv` carries **3 self-edges** (`self_edge_flag = yes`): Cherokee Nation
Assurance → itself ($401,817, FY2017), Cherokee Nation Aerospace and Defense → itself ($0,
FY2020), Cherokee Services Group → itself ($99,000, FY2019). And the cleanest single
instance of intra-family subcontracting in the file: **Cherokee Nation Mission Solutions →
Cherokee Nation Healthcare Services, 7 subawards, $15,260,707** — a tribal prime
subcontracting to a sibling under the same tribe.
**⛔ But read the blocker below before writing a word of this from `prime_sub_network.csv`.**

**S3. LOW — anything shaped like a market share.** See the blocker.

### ⛔ THE BLOCKER ON `prime_sub_network.csv`

**220 rows, 12 columns, 153 primes / 92 subs, $669,825,812, FY2011–2023 — and all 220 come
from a single file whose query definition was not preserved.** The build log's own words:

> "The sampling frame is unknown, so no denominator statement, no share-of-market claim,
> and no 'Native entities received X% of subawards' is supportable from this file."

**Treat it as anecdote, never as a network.** The self-edges above are real observations
and publishable *as observations*; the graph they sit in is not a graph of anything.
Additional trap: **`naics_modal` is the PRIME award's NAICS, not the sub's** — FSRS carries
no sub-level NAICS — so it must never be read as the supplying industry.

### The `subcontracting` refusals worth publishing

- **An empty review file was deliberately not written.** `review/subaward_api_unresolved_<date>.csv`
  *"was not written. It is the discovery pool of subawardees the ledger has never seen…
  With zero rows retrieved it would be an empty file, and an empty review file reads as
  'we looked and found nothing to rule' — the `NOT_FOUND` / `NOT_CHECKED` conflation this
  project treats as a distinct kind of error. **NOT_CHECKED, because the source served
  nothing.**"* This is a very small decision that encodes the entire epistemology.
- **A failed job and an absent object are different facts.** *"It did not read the five dead
  tokens as 'not published.'"*
- **What could not be extracted, listed rather than approximated:** DUNS (not in the
  source); **true CAGE for 9 entities**, Excel-corrupted at source — **7 leading-zero-
  stripped values are mechanically inferable and were NOT repaired**, per the no-repair
  rule, and 2 scientific-notation values are unrecoverable; `direction` left `unknown` on
  all 998 rows of that file by design; sub-level NAICS/PSC (does not exist in FSRS); and
  **the HigherGov query definition — "the single biggest limitation on the file's
  interpretability."**
- **Sioux Manufacturing Corporation appears under two distinct sub UEIs and was
  deliberately left unmerged.**
- **`prime_to_sub` is a contracting relationship, not ownership.** *"Do not propagate
  Native-entity ownership along `prime_to_sub` edges."*

> **✅ VERIFIED 2026-08-26.** Row count, dollar total, the FY2021–24 series (173/89/120/166),
> the 99.93% and the 41.59% all reproduce exactly. The `FY2026-DEFLATOR-CONVENTION` conflict
> named in the `contractors` slate also blocks any real-dollar chart on this shelf.

---

<!-- SLATE:natural-resources -->
## 9. `natural-resources` — Natural Resource Revenues · shelf `pro`

### What the data can support today

*All measured 2026-08-26.*

| | |
|---|---|
| `resource_revenue.csv` | **10,482 rows** ✅ · **734 recipient-linked (7.00%)** ✅ · **ceiling 966** ✅ |
| span | `period_end` **1994-09-30 → 2026-06-30**; `payment_date` 2008-09-22 → **2026-07-22** |
| `amount_usd` | $47,684,143,749 — **must never be summed as printed** |
| by `aggregation_level` | national_aggregate 9,467 / **$39.66B** · entity_specific 682 / $7.90B · state_aggregate 167 / $35.2M · entity_specific_component 60 / $96.9M · **per_headright_rate 106 / $557,660 (a RATE, not money)** |
| distinct entities resolved | **17**, out of a 1,489-entity spine |
| `resource_assets.csv` · `resource_parties.csv` | **35** · **1,436** |
| `tribal_tax_bases.csv` | **1,712** rows, 1990-01-01 → 2027-06-30; `tax_remitted_usd` $8.65B — **1,640 of 1,712 (95.8%) are North Dakota** |

**The 966 ceiling decomposes exactly.** 966 = every row carrying a named recipient string.
734 resolve to a spine entity; **232 are refused or held** — Osage headright holders 106 ·
Uintah Basin Revitalization Fund 60 · village corps and at-large shareholders 35 · other
ANCSA regionals 24 · combined class 7 — four of the five carrying *"AGGREGATE_OR_INDIVIDUALS
- refused by rule: an aggregate party never resolves to one entity."* **The remaining 9,516
rows are national aggregates that can never carry a recipient.**

**⚠ `nd_severance_allocation.csv` (7 rows) is currently mis-shelved under `gaming`.** It is
MHA Nation **oil and gas severance tax** allocation and belongs here. Note also that
**ND-ALLOC-003 and ND-ALLOC-004 are BOTH in force today.**

---

### ★ LAUNCH PIECE — *There is no published, named-tribe resource revenue series in the United States — with one exception, and the exception publishes for itself*

**Format:** paper, with an 800-word web companion. **Confidence: HIGH.** This is the best
piece in the `pro` shelves and possibly the best piece in the project.

**The claim.** Three independent legs, each measured rather than asserted.

**Leg 1 — the federal collector suppresses it by law, and the build re-measures the
suppression every run.**

```
Native rows carrying any geography :       0 of 9,238
Federal rows carrying any geography: 400,597 of 401,348 (99.8%)
```

ONRR's own words: *"For all Native American land, the federal government only releases
natural resource extraction and revenue information in aggregate. Specific data on Native
American revenues are confidential and proprietary. Treaties, laws, and regulations dictate
what data the government can release."* **No ONRR file has a tribe-name field at all, and
the string `Osage` appears zero times in every ONRR bulk file held** — for an estate with
exactly one owner.

**Leg 2 — most states never built a mechanism, and the sharpest case is Nevada.** 15 states
plus the federal layer were worked: **47 findings — 7 BUILT · 14 MECHANISM EXISTS, NO
PUBLIC SERIES · 26 NO MECHANISM.** Nevada's Net Proceeds of Minerals Bulletin publishes
named royalty recipient × operator × mine × commodity × county **with dollars**, across
eleven years — *"we found the right source, it names recipients individually, and the tribes
are not in it"* — and NRS ch. 362 contains zero occurrences of Indian, Native American,
tribal, reservation or colony.

**Leg 3 — tribal governments do not self-disclose, and the reason is corporate form, not
culture.** Probed 2026-08-06: `southernute-nsn.gov/finance/` returns 200 and publishes no
dollar figure; **`mhanation.com` returns 200 and publishes nothing — for the tribe that
appears in this very ledger receiving $3.13 billion of North Dakota oil tax
distributions.** The build log states the conclusion in the only defensible form:

> "ANCSA corporations disclose because a statute makes them… Tribal governments are under
> no equivalent duty. **The disclosure is a property of the corporate form, not of Native
> entities.** Any claim that Cedar Press covers 'Native resource revenue' would be false; it
> covers *ANCSA corporate* resource revenue plus two state tax series."

**And the exception, which is the piece's ending: the Osage.** A per-headright quarterly
series, **2000Q1 → 2026Q2**, ranging **$1,360 to $11,600 per full headright per quarter**
(mean $5,261), gated by a reconciliation that all 28 years 1998–2025 pass to **$0.00**, and
independently corroborated (2020 Q4 = **$2,385** in both the Minerals Council's spreadsheet
and Osage News). **It exists because the Osage Minerals Council publishes it themselves.**

**What would make it stronger.**
- **OSMRE AML is the highest-value unbuilt lead and it is one careful read away.** It names
  Crow, Hopi and Navajo with dollars, FY2016–FY2026 without a gap. All eleven PDFs are
  retrieved. **It is held because the text layer is offset by one row with no per-row
  subtotal to prove a de-skew:** *"Read naively, the Hopi Tribe received $799,809. Read
  correctly, $799,809 is the Navajo Nation's distribution printed on Hopi's line."* A
  visual read unblocks it.
- The Navajo Tax Commission carries the identical hazard and the identical answer.

**FINAL vs WILL MOVE.** **FINAL:** ONRR fiscal-year disbursements through FY2025 · ANCSA
§7(i) through FY2025 · Utah COBI through FY2025 · the MMS recovery (FY2001 / CY2000, a
closed series). **YTD:** ONRR monthly (period_end 2026-06-30) · ND Treasurer (2026-07-22) ·
MT DOR (2026-03-31) · Osage headright (2026Q2). **STALLED, and it is not the same as YTD:**
the Osage newsletter series **stops at 2022Q1** because two newsletters 404. Say which.

---

### QUEUE — additional `natural-resources` candidates, ranked

**NR2. Six things ONRR does not have.** *(paper · HIGH — this is the subscriber-facing
companion to the launch piece)*
ONRR's public data gives you **one national monthly aggregate for "Native American" land,
January 2003 forward** — no state, no county, no FIPS, no tribe, no lease, no well — **and
a land class that mixes tribal mineral interests with individual allottee interests.**
Against that:
1. **966 rows with a named recipient, 734 keyed to an entity — ONRR contributes 0 of them.**
   Every one comes from a non-federal publisher: North Dakota's Treasurer (489), the ANCSA
   regionals' own annual reports (185), the Osage Minerals Council (174), Utah's COBI API
   (118), Montana DOR (49).
2. **Nine years ONRR does not serve.** MMS-era archives recover **FY1994–FY2001 (FY1997
   held) and CY1996–CY2000 — 72 rows / $2,428,350,436** — against a portal floor of January
   2003. Recovered from PDFs whose text layer is offset by one line, and published only
   because the calendar-year table cross-foots in both directions across twelve independent
   checks.
3. **A statutory money flow between named Native entities that appears in no federal file.**
   ANCSA §7(i)/§7(j): **185 rows, all twelve regional corporations, FY2014–FY2025**,
   receipts **$998.6M** and obligations **$1.93B**. And it shows what no federal source
   states: **§7(i) is overwhelmingly funded by two regions — NANA paid $1.385B out while
   receiving $7.5M back; ASRC $366.2M out against $40.1M in.** With a recipient naming its
   payers, verbatim from Bering Straits' 2016 report: *"the 7(i) distribution from NANA and
   Arctic Slope Regional Corporation decreased, resulting in 7(i) revenue of $6.7 million."*
4. **The only named-tribe severance series in the country, plus its denominator.** ND: **489
   payments, $3,125,453,109.56**, 2008-09 → 2026-07, **parsed twice and agreeing to $0.00.**
   And because the Legislative Council publishes *both legs*, the effective blended share is
   **measured, not modelled**: 50.00% (2015-17, 2017-19) → 51.20% → 53.17% → 54.14% →
   **55.48%** (2025-27 to date). The exact 50.00% under the uniform 2013 regime is what
   validates the two legs as the same basis.
5. The Osage per-headright series (above).
6. **A measurement of the suppression itself, which is the most publishable thing here.**
   0 of 9,238 against 99.8%. And this: **a dedupe on the visible key of
   `fiscal_year_disbursements.csv` would discard 134 rows and $10,789,042,639.73.** From
   FY2015 that file carries 11–15 rows per year **identical in every published column**,
   differing only in amount — *because the dimension separating them was suppressed along
   with the geography.* **A dedupe that destroys $10.8 billion is the single most concrete
   demonstration of what redaction does to a dataset.**

**Honest limits that must be in this piece:** 90.3% of rows are still national aggregates a
reader could get from ONRR themselves; 17 entities are resolved out of 1,489; the tribal-tax
layer is 95.8% North Dakota; and `derived_taxable_base` is **empty on every severance row**,
populated only on 779 motor-fuel rows where it is **gallons, never dollars**.

**NR3. Three states, three different ways of not publishing.** *(web · HIGH)*
- **Oklahoma — a tribal column exists in the state's severance accounting, and severance is
  provably not in it.** 68 O.S. § 1004 contains zero occurrences of tribe, tribal, Indian or
  Osage. But the corroboration beats the statute: the **Oklahoma Tax Commission's FY2025
  apportionment chart has a column headed "Returned To Participating Tribes"** carrying
  **$26.1M** of motor-fuel and storage-leakage money — **and it is blank on both gross
  production tax rows, against $1.04B of gross production tax collected.** *"That is a far
  stronger negative than 'the statute does not mention tribes.'"*
- **New Mexico — closed by design, not by omission.** The royalty deduction sits in **three**
  articles (NMSA 1978 §§ 7-29-4.1, 7-31-5, 7-32-5), each carrying *"royalties paid or due
  any Indian tribe, Indian pueblo or Indian that is a ward of the United States."*
  Confidentiality is at **§ 7-1-8**, and the sharpest evidence is **§ 7-1-8.2**, which
  enumerates what *may* be revealed and includes taxpayer-level **fuel** detail **with no
  oil-and-gas equivalent.** Two clean negatives: the monthly Ad Valorem Distribution by Fund
  names every recipient with an exact amount and contains **zero tribal hits**; the State
  Land Office beneficiary list contains no tribe, nation or pueblo.
- **Colorado — the data exists and cannot legally be obtained.** C.R.S. 39-7-101(1)(c)
  **requires** operators to separately report volumes *"delivered to … any Indian tribe as
  royalty"* — and **39-7-101(4) makes those statements private documents, with disclosure a
  petty offense under C.R.S. 39-1-116.** Colorado's actual mechanism runs the other way: the
  Southern Ute is **exempt** from state severance tax and pays a PILT to La Plata County,
  capped at $1,000,000/yr and **not published.**

**NR4. A finding that is a zero, published because a zero is an assertion.** *(brief · HIGH)*
**Every single Montana quarter reads `Tribal Distribution: $0.00` across all 49 letters,
2014Q1 → 2026Q1** — verified, all 49 rows exactly zero. Published rather than dropped.
Pairs naturally with **R8** (the four-state coverage vocabulary).

**NR5. A definition change found by arithmetic, invisible in the numbers.** *(brief · HIGH)*
Osage "Total Revenue" is **net** of the Oklahoma gross production tax through 2017 and
**gross** of it from 2021. *"A subscriber charting the two together would read a definition
change as ~5% growth."* Recorded in `review/resource_series_breaks_2026-08-06.csv`.
Companion: **the "Major Details" block is not a partition and it is provable** — in 2016Q3
the oil line ($7,332,608.57) **exceeds** the quarter's stated total revenue ($7,209,421.48).

**NR6. LOW — the ND trust/fee mix.** Unreachable *in principle*, not merely unbuilt.
Schedule T-84 makes each operator report a trust/non-trust allocation per well and the
filings are confidential taxpayer data; the state books the answer under pool codes and
**never publishes collections by pool code** — *"that single file would decompose the blend
completely."* Worth one paragraph inside NR2, not its own piece.

### The `natural-resources` refusals worth publishing — the densest set in the project

- **The Osage divisor refused as a multiplier.** The Council prints a divisor of
  2,228.97393 right beside the per-headright rate. *"Refused. The divisor is used only as a
  check, never as a multiplier."* A new `aggregation_level` value, `per_headright_rate`, was
  added **so the non-additivity is machine-visible.**
- **BTFA cannot be a series** — its own page says trust funds include *"payments from
  judgment awards, settlements of claims, land-use agreements, royalties…, other proceeds…,
  and financial investment income."* Royalties are one of six ingredients. All four figures
  verify and are held **as scale context only.**
- **MMS FY1997 held by a reconciliation gate over a $10 internal inconsistency in the source
  document.** Confirmed absent from the file. **A $10 discrepancy killing a fiscal year is
  the most quotable sentence available about this project's standard.**
- **30 of 35 assets are ANCSA fee, not trust.** *"Writing 'tribally owned' across these rows
  would be wrong 30 times."* And the Osage estate carries `beneficial_interest_class =
  osage_headright_holder`, not the tribal government, because the Nation's own auditor says
  *"these distributions are not received by the Nation and are not reflected in the
  accompanying financial statements."*
- **Refused outright:** `estimated_gross_production_value` · `estimated_royalty` · any
  `modeled_amount` · per-tribe splits of the federal aggregate · land status inferred from a
  map · applying ND's 80/20 to the post-2019 series · **describing Utah's fund deposits as
  tribal royalty income** (Utah Code 63N-24-703(4): the fund *"consists of state severance
  tax money to be spent at the discretion of the state"* and *"does not constitute a trust
  fund"*) · applying the statutory ANCSA 70%/50% to any row · **splitting Peabody's three
  leases** (the 10-K identifies none individually) · **summing any acreage at all.**
- **The asset gate refused 16 facts on its first run, 13 because a declared number did not
  appear literally in its own quote.**
- **8 cross-source conflicts recorded and NOT resolved**, including **a $46.7 million
  restatement of one audited NANA line** (FY2023: $96,882K as originally reported vs
  $143,609K in two later reports) and a $64M cash-vs-accrual disagreement **inside the same
  document.** Vintage rule applied uniformly: as-originally-reported wins.
- **Six refuted citations**, each worth a line: ONRR Native coverage is not 2022–2025 (it is
  2003-01 → 2026-06, with MMS to 1994) · Montana's 50% is not in MCA Title 15 ch. 36 (which
  never mentions tribes) · Utah is not governed by Title 35A ch. 8 (renumbered into 63N ch.
  24) · Wind River's 85% cannot be cited to 25 U.S.C. § 612 (**§ 612 is omitted from the
  Code**, and the rate was **two-thirds** before ~1959) · Westmoreland's *"$3.1M yearly
  average"* is **company** income, not a tribal payment · NMFA's *"Jicarilla Apache Nation
  3,085,750"* is a **debt-service loan payment.**
- **181 asset↔revenue links are PROPOSALS, never merges** (174 Osage + 7 Red Dog, all
  `PROPOSED_AWAITING_RULING`), and **359 recipient-entity proposals** of which **106 and 66
  are refused** — headright payments run to individuals, and a class of recipients is not
  one entity.
- **Five things NOT VERIFIED and asserted nowhere**, listed so nobody assumes they were
  checked: the "800+ Navajo Revitalization Fund grants since 1998" claim · the Hopi ~80–85%
  coal-royalty dependence claim · whether the Fort Peck agreement was renewed after
  2017-06-30 · the Blackfeet agreement text · CY2001, CY2002 and FY2002, absent from every
  route probed.

> **✅ VERIFIED 2026-08-26.** 10,482 / 734 / 966 ✅ · 0-of-9,238 geography ✅ · 19.0%
> negatives and −$1,075,020,365.16 ✅ · the 134-row / $10,789,042,639.73 dedupe loss ✅ ·
> 489 ND payments / $3,125,453,109.56 ✅ · 49 Montana quarters all $0.00 ✅ · 174 Osage rows
> ✅ · MMS FY1997 absent ✅ · §7(i) receipts $998.6M ✅ · all 8 conflicts present ✅ · 35
> assets / 30 ANCSA-fee ✅.
> **Two doc figures do not reproduce and are benign: §7(i) obligations are $1,927,201,000
> not "$1.95 billion" (the doc's own table sums to $1.927B), and
> `RESOURCE_LEDGER_BUILD_LOG.md`'s headline "10,123 events / 1,096 party links" is
> superseded by 10,482 / 1,436 without a banner.**

---

<!-- SLATE:nonprofits -->
## 10. `nonprofits` — Native Nonprofits · shelf `pro`

### What the data can support today

*All measured 2026-08-26.*

| file | rows | span | dollars |
|---|---:|---|---|
| `np_schedule_i_grants.csv` | **58,685** ✅ | `tax_year` **2015–2025** | cash **$16,439,532,633** · noncash $878,481,598 · **627 distinct `filer_ein`** ✅ · 18,708 recipient EINs |
| `np_schedule_i_filers.csv` | 10,314 | 2014–2026 | Part II cash reconciles exactly; **Part III individuals $7,318,402,903 — and no names** |
| `np_orgs.csv` | **12,764** | a BMF **snapshot**, not a time series | revenue $19.91B · assets $46.83B |
| `np_financials.csv` | 8,507 | `tax_year` 1996–2025 | $20.33B (n=5,108); **662 EINs** |
| `np_grantee_financials.csv` | 4,058 | 2014–2025 | grantee revenue $202.31B; lobbying $364.43M; 927 EINs |
| `grantmaker_funding_flows.csv` | **18,656** ✅ | 2016–2025 | cash **$4,358,173,488** · **14 funders** ✅ |
| `np_ein_entity_hub.csv` · `np_ein_uei_bridge.csv` | 2,303 · 28 | — | 2,303 EINs → 792 entity_ids |

---

### ★ LAUNCH PIECE — *Nearly a third of the grant money named on Form 990 goes to organizations the IRS has no record of. That is what tribal government looks like in the tax data.*

**Format:** paper, with an 800-word web companion. **Confidence: HIGH.** This is a fact
about the *source*, not about anyone's Native status, so it survives every ruling caveat the
project imposes — which is rare on this shelf.

**The claim, in one measured sentence.**

> **Of the $16,439,532,633 in cash grants named on filed Form 990 Schedule I in this shelf,
> $4,915,941,725 — 29.90%, across 6,217 distinct recipient EINs — goes to organizations that
> do not exist anywhere in the IRS exempt-organization Business Master File.**

Numerator, denominator and columns are `cash_grant_usd` × `recipient_bmf_status` in
`data/clean/np_schedule_i_grants.csv`. The three-value split:
`in_full_irs_bmf` 39,178 rows / $11,300,432,106 (68.74%) · **`absent_from_full_irs_bmf`
16,344 / $4,915,941,725 (29.90%)** · `no_ein_reported_on_schedule` 3,163 / $223,158,802
(1.36%).

**Why it happens: IRC §7871.** Tribal governments are outside the Form 990 universe. They
have EINs, they receive and give hundreds of millions of dollars, and **none of it is
reportable on a 990 anyone can read.** The build log states it exactly:

> "6,217 distinct recipient EINs are printed on a filed Schedule I and absent from the
> entire BMF. That is the 7871 signature… It files no return. **This is not a gap and is not
> queued as one.**"

**Four corroborations, in increasing order of strength.**

1. **1,069 rows carry `TRIBE` in `irc_section_as_filed`** — the filer naming the case in its
   own words.
2. **Seven named tribal givers have no record of any kind in the full IRS master file.**
   Re-tested against **1,957,340 BMF rows**: `YUHAAVIATAM`, `MUCKLESHOOT` and `PECHANGA`
   return **zero rows in the entire BMF**; every `SHAKOPEE` / `SAN MANUEL` / `MORONGO` /
   `TULALIP` / `SEMINOLE TRIBE` hit is a place-name organization — the City of Shakopee
   volleyball association, the town of San Manuel AZ fire department, the Morongo Basin
   humane society, `ABSENTEE SEMINOLE TRIBE OF TEXAS`.
3. **The exception proves it.** **Tulalip Foundation** (EIN 26-0807036), the tribe's
   separately-incorporated 501(c)(3), *does* file and *is* in the data: 8 parsed returns,
   **5 grant rows totalling $99,791.** Against SMSC's own statement — *"Since the 1980s, the
   tribe has donated more than $400 million… and provided $500 million in low-interest
   loans"* — with **no grantee list on any path checked.** The observable-to-actual ratio for
   tribal philanthropy on this shelf is on the order of **$99,791 against $400,000,000.**
4. **The universe upper bound: 349 federally recognized tribes + 228 federally recognized
   Alaska Native Villages = 577 tribal governments**, every one outside the 990 universe by
   construction. **No file anywhere in the repo enumerates §7871 tribal givers.** The docs
   name nine. There is no roster.

**⚠ AN EVIDENTIARY CAVEAT YOU MUST NOT PUBLISH AROUND.** The conclusion is right. **The
stated evidence — "HTTP 404" per funder on ProPublica — is not reproducible from anything on
disk.** The only artefact records `n_results = FETCH_FAILED`, not `404`, and the producing
code collapses every HTTP error code *and* every transport exception into that one literal.
Decisively: **`Running Strong for American Indian Youth` — an ordinary 501(c)(3) that
unambiguously files a 990 — returns the same `FETCH_FAILED` on the same run.**
**Publish the BMF sentence, not the ProPublica sentence.** "Zero organizations across
1,957,340 IRS master-file rows" is stronger, is reproducible, and is the IRS's own record
rather than a third party's rendering. *(The other 404 claim is airtight: `logs/75_resolve.log`
contains exactly 153 lines of `HTTP 404 …/organizations/<EIN>.json`, reproducing the
documented "153 of 601 grantee EINs" precisely.)*

### ⭐ THE COMPANION FINDING — and it may be the better opening

**Tribal governments have no classification in the Census of Governments.** Measured
2026-08-26 across all 463 pages (997,181 characters) of the U.S. Census Bureau's
***Government Finance and Employment Classification Manual*** — the document that defines
what counts as a government for the Census of Governments:

| term | occurrences |
|---|---:|
| **`tribal`** | **0** |
| **`tribe` / `tribes`** | **0** |
| **`Native`** | **0** |
| **`Alaska Native`** | **0** |
| **`reservation`** | **0** |
| `Indian` | **3** — all incidental (Indian education aid; "parts of the Bureau of Indian Affairs" as a *federal* education agency, twice) |
| `school district` | 53 |

**The United States conducts a census of its governments and does not count tribal
governments in it.** `docs/PUBLISHED_LANDSCAPE_2026-08-26.md` §8.6 rates this a Cedar Press
original and **better than the FAADS finding in three ways: it needs no statutory caveat, it
is reproducible in one command by anyone who doubts it, and it says something structural
rather than technical.**

**It belongs here because it explains the §7871 finding rather than sitting beside it.**
There is no official denominator for tribal government finance — which is precisely why the
Single Audit, 990 and compact layers have no public counterpart, and why 29.90% of Schedule
I money lands on organizations the IRS has no record of. **Two independent measurements of
the same absence, from two different agencies.**

**Pair it with CRS IF12612**, which records that BIA's *American Indian Population and Labor
Force Report* ran **1982–2013 and stopped**, and that tribal service population data *"are
not publicly available below the national level."* Cite IF12612 as the authoritative
acknowledgment; do not re-derive it.

**⚠ One boundary.** Publish it as a measurement of a named document, with the counts,
exactly as above. **Do NOT extrapolate it into "Census excludes tribal governments from all
products"** — the AIAN population and geography products are a different matter, and the ABS
AIAN business tabulations remain unchecked.

**What would make it stronger.**
- **Build the §7871 roster.** 577 tribal governments, none of which can file, and no file
  that names them as a class. It is a small, high-value artefact and it converts this piece
  from a measurement into a reference.
- Resolve some of the 6,217 EINs to spine entities. Even a few hundred turns a structural
  finding into a per-entity one.

**FINAL vs WILL MOVE — and this is the one collection that will NOT benefit from the year
turn.** 990 filings lag roughly 18 months structurally. Terminal-year state, measured:

| file | TY2025 | TY2024 | safe terminal year |
|---|---|---|---|
| `np_financials.csv` | 26 rows, **0 with revenue** | 251 rows, 51 with revenue | **TY2023** |
| `np_schedule_i_grants.csv` | 4,614 rows / $1.146B (**~43%**) | 9,779 / $2.661B | **TY2024** |
| `np_grantee_financials.csv` | 202 rows (**~38%**) | 530 | **TY2024** |
| `grantmaker_funding_flows.csv` | **128 rows / $10.26M from ONE return (~1.3%)** | 2,720 / $783.5M | **TY2024** |

**The pull genuinely reaches the frontier** — TY2026 filings appear as submission-year
prefixes and `tax_period_end` reaches 2026-04-30 — **but no TY2025 total in this shelf is
publishable.** Quote TY2023 and TY2024. **Do not promise a nonprofit refresh in February; it
buys almost nothing.**

---

### QUEUE — additional `nonprofits` candidates, ranked

**NP2. There is no publishable "Native grantmaking" total, and here is the number that
proves it.** *(web · HIGH)*
**Only $5,894,012 — 0.0359% — of Schedule I cash comes from a filer carrying an affirmative
Native ruling. Sixty rows. Three filers.** `docs/SCHEDULE_I_BUILD_LOG.md` retracted its own
first cut in exactly these terms: ***"Not one line is a publishable 'Native grantmaking'
total."*** A short piece about a headline number that dissolved on inspection, and it is the
natural sidebar to the launch piece.

**NP3. ⚠ CORRECTION TO THE BRIEF — `grantmaker_funding_flows.csv` is not a Native
philanthropy file, and it cannot answer the question that was asked of it.** *(paper ·
HIGH, but it is a different story than expected)*
The brief asked what share of foundation dollars labelled "Native" reaches Native-controlled
organizations. **This file cannot answer that.** It is a **14-funder conservative-foundation
panel** — Templeton, DonorsTrust, Charles Koch Foundation, Bradley, Kirby, Coors, Scaife,
Diana Davis Spencer, Searle, Koch Institute, Ed Uihlein, Donors Capital, JM Foundation, Koch
Foundation II — built to trace the litigation infrastructure on the **anti-ICWA** side.
Measured: `cedar_recipient_native_entity_class`, `cedar_recipient_spine_entity_id` and
`cedar_funder_native_entity_class` are **0 non-null of 18,656**, and the build log says why
in a heading: ***"`grantmaker_funding_flows.csv` LINKS TO NOTHING, AND THAT IS THE RIGHT
ANSWER."*** A keyword scan confirms it: `"NATIVE AMERICAN"` → **0 rows, $0**; `"TRIBE"` →
**0 rows**; `"NATIVE"` → 33 rows / $8.69M (0.200%); `"INDIAN"` → 58 / $13.36M (0.307%).
**What it DOES measure, and it is publishable:** **236 grants totalling $70,047,495** carry
`recipient_icwa_position = C_INSTITUTIONAL_ACTION:OPPOSED_TO_TRIBAL_PARTIES`, 2016–2025. By
funder: DonorsTrust $23.5M · Koch Institute $11.7M · Searle $10.6M · Koch Foundation $10.5M
· Bradley $4.7M · Scaife $4.2M. By recipient: Cato $23.8M · Pacific Legal Foundation $15.3M
· New Civil Liberties Alliance $13.1M · Texas Public Policy Foundation $10.7M · Goldwater
$5.7M · Project on Fair Representation $1.5M. **8 of the 14 funders gave to both sides at
unit-identified granularity.**
**The restraint that makes it publishable:** `carries_institutional_position = 0` on **all
18,656 rows** — the file deliberately refuses to read a shared funder as a shared position.
**This is a live-litigation subject and it must be written with the same care as the NAGPRA
piece: fund a party's counsel and you have funded counsel, not a position.**

**NP4. Seven things this shelf can never see.** *(brief · HIGH)*
Listed in the build logs and worth publishing as a bounded statement of scope: tribal
government grantmaking (§7871) · membership dues · grants under $5,000 · **grants to
individuals — Part III carries $7,318,402,903 and no names** · fiscally sponsored projects ·
whether a grant was restricted · sub-threshold lobbying. A dataset that publishes its own
blind spots in a list is doing something almost nobody in this field does.

**NP5. LOW — anything built on the tier-A revenue aggregate.** **Forbidden to quote.**
*"Tier A is a screened candidate set, not a Native organization list… Do not quote it,"* and
*"Its revenue aggregate is 69.3% place-name-risk organizations. Do not quote it, before or
after subtracting them."* Listed so the $2.51B figure is never picked up.

### The `nonprofits` refusals worth publishing — 65 documented; the load-bearing ones

- **R5, the fiscal sponsor**, in full. It is the clearest single illustration on this shelf.
- **All 12,764 `np_orgs` rows left `UNRULED` deliberately.** *"The IRS BMF has no
  control-status field… Minting `tribally_controlled` from a name match would be exactly the
  fabrication the prime directive forbids."*
- **The identifier ledger's entire EIN leg refused as a link source — all 1,104 rows** —
  *"a 6.5%-accurate disagreement is not evidence about the row it disagrees with."*
- **Every name path other than exact / alias / core refused**, because *"containment has
  failed ten documented ways in this repo."* **143,735 row-instances left deliberately
  unlinked**; 325 near-misses individually refused; 15 of 33 conflicts refused
  auto-resolution.
- **78 grantees ruled `UNRESOLVED` as a positive act.** *"`UNRESOLVED` is a real ruling here,
  not a dodge… Calling them `NOT_NATIVE` would be a false attribution in the negative
  direction."* **A false negative is a false attribution — that framing is worth a paragraph
  on its own.**
- **310 EINs excluded rather than zeroed.** *"A 990-N filer reports gross receipts under
  $50,000 and nothing else. Zero lobbying there is the **filing regime, not a finding**."*
- **NCAI, NIGA, USET, NAIHC and AFN refused a pass-through reading.** *"Presenting their
  advocacy as a concealed pass-through would simply be wrong."* A refusal that protects the
  subjects rather than the dataset.
- **DonorsTrust / Donors Capital donor identity refused outright.** *"This is a hard wall;
  the file never infers past it."*
- **$123.9M of Koch money at George Mason refused a Mercatus reading.** *"The Mercatus figure
  the returns support for that funder is $0."*
- **A failed hypothesis kept failed.** *"That hypothesis failed and stays failed."*
- **A live bug reported rather than quietly patched:** `code/148_resolve_schedule_i_recipients.py`
  promotes 42 negative `elijah_ruling` rows to tier A — *"a RULED method is not automatically
  a POSITIVE ruling."*
- **The scope bounded in writing:** *"Any claim that this dataset covers 'Native
  philanthropy' would be false; it covers *Native foundation* philanthropy."*
- **Grantmakers dropped rather than half-built**, including the **Native American Agriculture
  Fund's $266M Keepseagle corpus** — *"the single most valuable unworked funder in the
  channel."*

### Documentation defects to fix before any `nonprofits` piece ships

1. `docs/SCHEDULE_I_BUILD_LOG.md` says **628 filers / 1,432 returns**; the file holds **627
   / 1,431**, and the pre-linkage backup agrees, so it is not a linkage artefact. Its year
   table shows TY2024 at 355 where the file holds 354.
2. Same log says **44 columns**; measured **63** now and 47 in the pre-167 backup.
3. `docs/NONPROFIT_BUILD_LOG_2026-08-05.md` §4 tier tables are stale and unmarked (doc A
   1,090 / B 7,018 / X 4,656; measured **A 739 / B 7,092 / X 4,933**), and its line 136 —
   *"`classification_ruling` is `UNRULED` on all 12,764 rows"* — **is now false**; 371 rows
   carry a ruling.
4. `docs/PHILANTHROPY_DISCOVERY_LOG.md` says 78 `UNRESOLVED` at two places and 81 at a
   third — **internally inconsistent inside one document.**
5. `docs/GRANTMAKER_FUNDING_FLOWS_BUILD_LOG.md` documents a column value that **occurs zero
   times** (`MERCATUS_NAMED_IN_TEXT`) and claims the column is *"on every row"* when it is
   **null on 18,040 of 18,656 (97%)**. The Hoover row count is **18 / 22 / 40** across three
   places.
6. `grantmaker_funding_flows.noncash_assistance_usd` has 3,859 non-null values **summing to
   exactly $0.00.** The column carries no information and will render as a real-looking zero
   in any table. Suppress it.

> **✅ VERIFIED 2026-08-26.** 58,685 ✅ · 627 filers ✅ · $16,439,532,633 ✅ · the 6,217 /
> $4,915,941,725 / 29.90% headline ✅ · 1,069 `TRIBE` rows ✅ · 18,656 / 14 funders ✅ ·
> 8-of-14 both sides ✅ · 153 logged 404s ✅ · 1,957,340 BMF rows ✅.

---

<!-- SLATE:gaming -->
## 11. `gaming` — Gaming Intelligence · shelf `grove` (Cedar Grove licensees only)

### ★★ THE FLAGSHIP ★★

**The owner's brief: a gaming article that leads readers to purchase Cedar Grove.** Gaming
is grove-only, so the piece must demonstrate value **without giving the collection away** —
and it must do it under a licensing constraint that removes the easiest material.

---

### What the data can support today

*All measured 2026-08-26. This is the largest collection in the project — 40+ tables. Only
the load-bearing ones are listed.*

**Publishable (free / official sources):**

| file | rows | span |
|---|---:|---|
| `gaming_capacity_official.csv` | **6,461** | 1990-08-02 → 2026-08-06 — state regulators + compacts + SEC. **The publishable capacity/revenue layer.** |
| `ca_gaming_payments.csv` | **40,164** | 2000-07-01 → 2026-06-30. CGCC RSTF/TNGF ledger. **0 derived revenue rows.** |
| `digital_gaming_revenue.csv` | **10,661** | 2021-10-01 → 2026-06-30. MI 5,670 / CT 4,899 / AZ 91 / FL 1 |
| `fl_gaming_payments.csv` | **9,756** | 2007-07-01 → 2031-06-30 (5,371 are forecasts). **0 derived bound rows.** |
| `gaming_revenue_bounds.csv` | 13,803 | FY1994–FY2025; 694 properties / 260 tribes; 13,494 are `REGIONAL_GGR_CEILING`; **all tier B** |
| `compact_required_reports.csv` | 4,121 | typed reporting obligations across 707 compacts |
| `compact_structured_terms.csv` | 2,887 | typed terms incl. rate invertibility |
| `gaming_property_locations.csv` | **2,212** | 1,471 `publishable = Y`; **1,068 with coordinates → 539 distinct properties** ✅ |
| `fac_audit_gaming_disclosures.csv` | **1,521** | audit years 2016–2026 |
| `gaming_ordinances.csv` | **1,155** | 1985-12-02 → 2026-02-12; **298 distinct `tribe_id`** |
| `compacts.csv` | **707** | 1990-04-02 → **2026-04-14** |
| `gaming_nigc_roster_link.csv` | **453** | links into the NIGC roster |
| `nigc_declination_letters.csv` | **327** | 2013-07-30 → 2026-04-14; **307 resolved to 140 tribes** |
| `gaming_ordinance_ocr.csv` | **263** | 263 image-only scans recovered, 136 tribes |
| `nigc_regional_ggr.csv` | **198** | **FY2001 → FY2025** |
| `gaming_land_decisions.csv` | **138** | 1990-03-05 → 2026-03-09; 95 tribes, 22 states |
| `wa_machine_allocations.csv` | **75** | 1999-01-28 → open; 29 tribes; **all tier A** |
| `nigc_revenue_bands.csv` | **20** | FY2022–FY2025 |

**The property hub:** `gaming_facilities.csv` **784 rows** (was 774 before the 2026-08-26
rebuild), `gaming_properties.csv` **784** — the de-vendored published view. `open_date` max
**2025-07-23**; `close_date` max **2023**.

### ⛔ RECONCILE 784 AGAINST THE CONGRESSIONALLY-CITED COUNT, ON THE SAME PAGE

> **CRS IF12527**, *Indian Gaming Regulatory Act: Gaming on "Indian Lands"*, updated
> **17 Dec 2025** — *"As of September 2024, **243 Tribes owned, operated, or licensed 532
> gaming establishments in 29 states, grossing a total of $43.9 billion** in gaming
> revenue."* — sourced to NIGC

**784 is 47% higher than the count Congress uses, and it will be challenged on day one.**
The honest reconciliation is available and it is *favourable*. Measured 2026-08-26 from
`gaming_facilities.csv`: **449 rows carry `property_status = current`**, 1 is `approved`,
and **334 are blank.**

> **Lead with 449 current, or 574 independently evidenced. Name IF12527 as the baseline.
> Say what the other 335 rows are.** 449 current against NIGC's 532 licensed is an
> *undercount of operating facilities*; 784 is a **historical universe**. Publishing "784
> facilities — more than the federal regulator counts" would be exactly the false precision
> this project exists to prevent. **An unreconciled 784 reads as an error, not as broader
> coverage.**

---

### ⛔ THE LICENSING BOUNDARY — read before writing one sentence

**Casino City may be read for QA and may never be published or resold.** And the trap that
has already caught one reader:

> **`tribal_property_list` IS ALSO CASINO CITY.** It is the *Casino City Tribal Property
> List*. So the vendor-derived share is not the 440 rows naming `casino_city_press`. It is
> **610 of 774.**

Verified 2026-08-26: id prefixes are `CCP-` 595 · `VP-` 164 · `TPL-` 15 · `CEDAR-FAC-` 10,
so **vendor-minted = 610**, identical in the 774-row backup and the current 784-row file.
Against the current file it is **610 of 784 (77.8%)**. The union of `tribal_property_list`
(610) and `casino_city_press` (440) is exactly 610 — the second is a strict subset of the
first. **174 rows touch neither.**

**The one-line editorial rule, from the build log: "Casino City establishes nothing
publishable."**

**NEVER PUBLISH — whole files:** `gaming_property_capacity_history.csv` (64,181 rows, 100%
vendor) · the 64,181 vendor rows inside `gaming_facility_metrics.csv` (of 68,211).

**NEVER PUBLISH — specific columns**, measured: `casino_city_id` (595) · `source_datasets`
where it names either vendor token (610) · `coords_basis` (430) · `open_date_basis` /
`close_date_basis` (447) · `open_date_absent_reason` (16) · `gaming_equipment_source` (429)
· `property_likelihood_basis` (182) · `n_vendor_capacity` (432) · `n_vendor_metrics` (435)
· `entity_tier_basis` wherever it appears (599 / 968 / 623 / 65,436).

**THE SUBTLE ONE — `facility_id` itself.** `CCP-` / `TPL-` prefixes carry the vendor's key
into **every downstream table**: `gaming_facility_metrics` 67,172 · `gaming_capacity_official`
**3,589** · `gaming_device_observations` 968 · `gaming_employment_observations` 641 ·
`gaming_property_coverage` 610 · `gaming_properties` 610 · `gaming_property_federal_traces`
610 · `gaming_nigc_roster_link` 400. The docs call the prefix *"history, not provenance"*
and the underlying **facts** in `gaming_capacity_official` are state regulators, which
publish. **But never print a bare `facility_id` in an article. Use the facility name.**

**A DERIVED-COUNT LEAK found during this audit and not previously flagged.**
`gaming_property_coverage.csv`'s `n_publishable_sources` and `evidence_strength` are
computed over 22 source families, **one of which is `vendor_metrics`**. Publishing a
per-property "number of sources" or a "STRONG — 4+ independent sources" badge without first
stripping `n_vendor_capacity` and `n_vendor_metrics` **republishes a vendor-derived count**.
435 of 784 properties carry ≥1 licensed source.

**THE ONE EXPLICIT EXCEPTION**, and it is a useful one:
> "`match_status` was deliberately **kept**. Its values name the vendor (`casino_city_only`)
> but it is Cedar's own provenance taxonomy, not the vendor's key… Naming what KIND of
> fact a row is does not disclose how the row was made."

**You may write "this property is attested only by a licensed vendor source." You may not
print the vendor's id, capacity numbers, dates, or addresses.**

**AND A LIVE LICENSING EXPOSURE THAT MUST BE CONFIRMED CLOSED BEFORE PUBLICATION.** The
gate `LICENSED_SOURCE_FILES` in `code/87_build_dataset_notes.py` was **a dead constant for
20 days** — *"The gate is a dead constant. This is a licensing exposure, not just a data
problem, and it is the highest-severity finding in this audit."* Both Casino City files had
live shipping contracts (**129,404 rows**); `dist/cedar_press.db`, `cedar_press_master.xlsx`
and `schema.sql` were quarantined to `graveyard/2026-08-26_licensed_dist_purge/`. Licensed
files with a shipping contract went **2 → 0**. **Verify `dist/` is clean before the article
ships, and verify the gate is referenced in `main()` and not merely declared.**

---

### THE FLAGSHIP DESIGN

**Working title:** *Eight percent of tribal gaming operations hold more than half the
revenue. The federal government publishes that — and cannot tell you which eight percent.*

**Format:** ≈1,400-word web article (longer than a standard web piece, shorter than a
paper), one chart, one table, one sidebar. **Confidence: HIGH on everything shown.**

#### The hook, and why it is honest

**NIGC publishes the concentration and structurally cannot resolve it.** From
`nigc_revenue_bands.csv` — NIGC's own chart, federal, free, citable, and stable across four
years:

> **FY2025: 8.6% of tribal gaming operations hold 55.8% of the revenue. 54.3% of operations
> hold 4.8%.**

That is the finding. It is a *federal* finding — we did not compute it, NIGC did — and
saying so is the point. **What NIGC does not publish is which operations are in which
band.** It publishes bands, not properties. Its regional GGR series
(`nigc_regional_ggr.csv`, 198 region-years, FY2001–FY2025) tops out at
**$46,162,783,570 national GGR in FY2025 across 545 operations** — again, a region, not a
property.

So the article's argument writes itself and does not overclaim: **the public record proves
the concentration exists and is structurally incapable of naming it. Everything a reader
would want to do next requires resolving a regulatory band to a physical property, and that
resolution is the product.**

This is the honest hook because it is *true of the sources*, not a marketing claim about
us. NIGC's statutory job is to regulate, not to publish a market map.

#### What the article SHOWS — five things, all free-source, all checkable

1. **The concentration, from NIGC's own bands.** Stable FY2022–FY2025. Chart it.
2. **Tribal regulatory capacity, counted for the first time.** **973 ordinance rows name a
   Tribal Gaming Agency across 307 tribes, with 469 distinct agency names** — and the
   reason this matters is a gap in the compacts: the compact parse found **674 reporting
   obligations running to a "Tribal Gaming Agency" and could name none of them.** *No
   federal source publishes a directory of tribal gaming commissions.* Show the count and
   two or three named examples. **Do not publish the register.**
   *Honest caveat that must appear:* the register is *"a lead list, not a normalised
   roster"* — of the 13 named examples in the build log, 11 verify as genuinely new, one
   was already in the born-digital corpus, and one survives only as a glued OCR string.
   **Do not print 469 as a clean count of institutions.**
3. **The Class II-only universe, named.** **40 tribes hold an ordinance and no compact** —
   structurally invisible to anyone working from compacts. 34 of the 40 have Class II
   authorisation confirmed in an instrument's own text, and **29 of the 40 have no
   NIGC-mapped location: authorised, not observed operating.** Name them; the list is a
   public-record fact and it is the single most useful free thing this article can give
   away. The methodological note beside it is what sells the product: **16 unresolved NIGC
   names were EXCLUDED from that count rather than folded in**, because joining on a missing
   key scores every unresolved name as "no compact" — Viejas, Santa Ysabel, Mille Lacs,
   Cherokee Nation and St. Regis demonstrably hold compacts, and including them would have
   inflated the headline by 40% using tribes that contradict it.
4. **What a tribe actually pays a slot manufacturer — two figures that exist nowhere else.**
   **25 `MACHINE_PARTICIPATION_ARRANGEMENT` disclosures across 8 tribal entities**, verified
   exactly: Quapaw Nation 6 · Robinson Rancheria 6 · Grand Traverse Band 4 · Sault Ste.
   Marie 3 · Little Traverse Bay Bands 3 · Muscogee (Creek) 1 · Ottawa Tribe of Oklahoma 1 ·
   Sac and Fox of Missouri 1. Two carry an exact wide-area-progressive figure, both Robinson
   Rancheria, both verbatim from the audit:
   > "Of these total amounts, **$319,889** were paid to fund wide-area progressive jackpot
   > amounts and have been included as a contra to gaming machine revenues during the year
   > ended December 31, **2019**."
   > "…**$210,827**… year ended December 31, **2020**."

   And the quotable one, Sault Ste. Marie, identical text FY2022 / FY2023 / FY2024:
   > "The Gaming Authority leases some of its slot machines from gaming equipment
   > manufacturers under participation arrangements, whereby the gaming manufacturer
   > receives a percentage of the handle or net win associated with the leased machine."

   **⚠ Precision fix: say "two exact participation figures," not "two rows with figures."**
   Four MPA rows carry numbers; the other two are Robinson's total gaming revenue tables
   with a **blank `measurement_type`**.
   **⚠ And the standing rule travels with it:** manufacturer revenue per participation unit
   measures **the manufacturer's** economics, not the casino's GGR.
5. **The two refusals, in full.** California (**R1**) and Florida (**R2**). Verified in the
   data today: `ca_gaming_payments.derived_tribe_revenue_value` is **empty on all 40,164
   rows** and `payment_invertible` is never `yes`; `fl_gaming_payments.derived_revenue_bound_value`
   is **empty on all 9,756**. And the Florida refusal **ships on every payment row** — 4,166
   rows carry the full arithmetic in `bound_basis` beginning *"Refused, not caveated…"*.
   **A refusal that is auditable inside the shipped file is the single most credible thing
   this collection contains,** and it is free to publish because it gives away nothing.

#### What the article WITHHOLDS — and how to withhold it visibly

The rule: **show that a join exists; never perform it in public.** Name each withheld layer
by what question it answers, so a reader knows exactly what they would be buying.

| withheld | what it answers | why a reader wants it |
|---|---|---|
| the property hub — 784 properties with their compacts, ordinances, decisions and traces | *which* operations | the entire article's open question |
| `gaming_capacity_official` — **6,461** official capacity/revenue observations | how big, when, from whose regulator | the only free-source capacity series that exists |
| `ca_gaming_payments` **40,164** rows / `fl_gaming_payments` **9,756** | who pays what to which state, quarterly | tribal finance and state-relations work |
| `digital_gaming_revenue` **10,661** rows, MI/CT/AZ | the fastest-growing segment, per operator | nobody else holds it tribe-attributed |
| `compact_structured_terms` **2,887** typed terms | device caps, rates, **rate invertibility** | compact renegotiation, and this is the feature a tribe would pay for unprompted |
| `gaming_nigc_roster_link` — **453** links | which property is a regulated IGRA operation | the resolution the article says NIGC cannot give |
| `nigc_declination_letters` **327**, `gaming_financing_events` **293** | who is lending to tribal gaming, and on what terms | banker and investor buyers |
| the tribal gaming agency register, 973 rows / 469 names | who regulates, per tribe | vendors, counsel, and the compacts' own unanswered question |

**State the withholding plainly in the piece** — a sentence like *"Cedar Grove resolves
each of these to a named property; this article does not"* is more persuasive than a
paywall, and it is honest.

#### The three things that make the hook credible rather than promotional

1. **Publish defects in NIGC's own record.** Verified: **the NIGC gaming location map holds
   496 real locations plus 10 Chinese railway stations, a blank marker and 14 exact
   duplicates.** Kialegee Tribal Town's amendment link **serves Kalispel's PDF** — different
   URLs, byte-identical file, caught only by md5, and that row is refused with no extracted
   content. One ordinance link is printed under two dates; Santa Ysabel is listed twice; one
   approval date is **three years before IGRA**. **18 tribes hold compacts with no ordinance
   on the index, 15 of them unexplained** — and since IGRA requires an ordinance for Class
   III too, that is a gap in NIGC's published index, not in our extraction.
2. **Publish a defect we created ourselves.** *"A misspelling in the source became a claim
   about our coverage."* Script 92's partition test was exact string equality on a parsed
   city, and NIGC's own address text misspells cities — `Mohnomen` for Mahnomen, `Muscogee`
   for Muskogee, `Seneca Fall` for Seneca Falls. Each misspelling scored *"Cedar has nothing
   in this city."* The 140 staged additions were mostly wrong: **103 ruled
   `ALREADY_IN_CEDAR_DO_NOT_ADD`, 10 appended, 43 queued as possible duplicates, 5 queued as
   NIGC-current-vs-Cedar-closed conflicts.**
3. **State the coverage honestly.** **574 of 784 facilities (73.2%) are independently
   evidenced** — 174 independently-minted ids (`VP-` + `CEDAR-FAC-`) plus 453 NIGC roster
   links. **210 are vendor-only and their existence cannot be asserted from a free source.**
   Saying that out loud is the difference between a data product and a directory.

#### What must NOT go in the flagship

- **Any Casino City-derived figure**, per the boundary above. This removes the easiest
  material — capacity, open dates, addresses — and the article is designed around its
  absence rather than against it.
- **Any bare `facility_id`.**
- **Any per-property "N sources" or `evidence_strength` badge** (the derived-count leak).
- **"150 on day 31, 148 on day 15."** ❌ **Does not reproduce.** Measured: **148 on 31
  December, 153 on day 15**, plus 3 on a non-December day 31 → 304 placeholder-shaped
  values. Already flagged in `docs/FACT_CHECK_2026-08-06.md` row B-28. **And do not attach
  those to the 415** — they are two different measurements. **415 is correct** and is the
  count of dates whose value contradicted its own stated precision (339 open + 76 close),
  all downgraded, with `open_date_source_value_verbatim` preserving the original on **339 of
  339 — nothing lost.**
- **A naive sum of `nigc_regional_ggr`.** ❌ **New defect found in this audit:** FY2002,
  FY2007 and FY2016 each appear under **two `region_system_version`s**. Summing all rows
  gives FY2002 $29.2B instead of ~$14.5B, FY2007 $52.2B instead of ~$26.0B, FY2016 $62.6B
  instead of $31.3B. **Always filter on one `region_system_version`.**
- **A count of "321 tribes" with a gaming ordinance.** 321 is `ORIGINAL_ORDINANCE` rows;
  distinct `tribe_id` is **298**.
- **Seminole gaming revenue.** `seminole_bond_disclosures.csv` **contains none** —
  `carries_gaming_revenue = no` on 18 rows, `unknown` on 11, 10 `withheld_by_rule`, and its
  21 dollar figures are Single Audit federal-awards-expended, **explicitly labelled "NOT
  revenue, NOT gaming."**
- **Anything read as tier A out of `digital_gaming_revenue`.** `confidence_tier` is **blank
  on all 10,661 rows** — entity-linked but un-tiered.

**FINAL vs WILL MOVE.** **FINAL:** NIGC revenue bands FY2022–FY2025 · NIGC regional GGR
through FY2025 · the ordinance corpus to 2026-02-12 · the 40-tribe Class II list · the two
refusals · the machine-participation disclosures. **WILL MOVE:** CA payments (quarterly,
through 2026-06-30) · FL payments · digital revenue (monthly, through 2026-06-30) ·
compacts (through 2026-04-14). **WILL LOOK STALE AND MUST BE STATED:** `gaming_facilities`
/ `gaming_properties` `open_date` stops **2025-07-23**, and the vendor capacity panel — which
cannot be published anyway — stops **2023-01-01**.

---

### QUEUE — additional `gaming` candidates, ranked

**G2. An inter-tribal market in machine rights that no regulator publishes.** *(paper ·
HIGH, and it is the strongest second piece in the collection)*
`wa_machine_allocations.csv`: **75 rows, 29 Washington tribes, 1999-01-28 → open, every row
`AUTHORIZED_MAXIMUM`, every row tier A.** Four regimes: Appendix X (1998) 425 → 675 ·
Appendix Colville (2003) 675 · Appendix X2 (2007) 975 · **Appendix X2 Addendum (2015–)
1,075.**
The finding is `wa_machine_transfers.csv` — **0 rows, and that is the finding, not a gap.**
Verbatim:
> "**12.1 Allocation.** The Tribe shall be entitled to an allocation of, and may operate or
> transfer the ability to operate, up to 975 Player Terminals." — Appendix X2 §12.1

> "Each tribe could operate 1,500 player terminals per facility **by leasing machine rights
> from other tribes**." — WSGC, *Tribal Lottery System*

> "So a Washington tribe with no casino still holds a tradeable asset, and a Washington
> tribe with a large casino is operating machines it does not own. **Both sides of that are
> Native-to-Native commercial relationships that no federal dataset can see.**"

> "since Appendix X2 (2007) WSGC receives only *the number of transfers*, not the transfer
> documents, and **the price sits by design in a separate agreement that is never filed**."

**Arizona runs the identical market and also publishes no ledger** — ADG FY2025 Annual
Report, verbatim: *"Another six Tribes do not have casinos but have slot machine rights that
they may lease to other Tribes with casinos (transfer agreements)."* Named on that page:
**Havasupai · Hopi · Hualapai · Kaibab Band of Paiute · San Juan Southern Paiute · Zuni.**
Washington's equivalent six non-operators: **Hoh · Lower Elwha · Makah · Quileute · Samish ·
Sauk-Suiattle.** 36 PDFs on `gaming.az.gov/resources/reports` were enumerated and **not one
is an allocation or transfer table.**
**The article's call to action is a public-records request**, which is a genuinely good
ending — it invites the reader to help extend the record.
**⚠ Arithmetic gotcha:** the documented statewide ceiling is 29 × 1,075 = **31,175**, but
summing every row with a blank `effective_end` gives **31,850 across 30 rows** — Confederated
Colville's 2003 Appendix-Colville 675-EGD row was never closed out. **Subtract it. Do not
sum the open rows.**
**And the reason this is a gaming-collection exclusive:** *"NIGC publishes no device counts
at any level. There is no federal counterpart to 31,175 authorised terminals, and no federal
source from which the number could be derived."*

**G3. The one violation in 327 letters.** *(web · HIGH)*
`nigc_declination_letters.csv`: **327 letters, 2013-07-30 → 2026-04-14, 307 resolved to 140
distinct tribes**, 178 counterparty companies. `is_management_contract = NO` on 284,
`chair_approval_required = NO` on 286, `sole_proprietary_interest_analysis =
NO_VIOLATION_FOUND` on 284 — **and `VIOLATION_FOUND` on exactly one.** That single row is
the most story-rich object in the collection.
Most-lettered tribes: Catawba 7 · Mohegan 7 · Poarch 7 · Eastern Cherokee 6. Per year, with
a visible COVID-era spike: 2019:37 · **2020:44 · 2021:42** · 2022:14 · 2023:10.
**Two hard rules travel with it.** What a declination *is*, from the file's own
`evidence_meaning` on every row:
> "NIGC OGC reviewed the SUBMITTED, UNEXECUTED documents named in this letter… This is NOT
> evidence that the transaction closed, that any agreement was executed, that a property
> opened or operates, or that land is in trust or gaming-eligible."

And the absence rule, also on every row:
> "NIGC review is voluntary and posting is subject to a FOIA release review, so this archive
> is not a census of tribal gaming agreements. **A property or tribe with no letter is not a
> property or tribe with no financing.**"

**A story must not count silence.**

**G4. Read the mood of the clause, not the presence of the phrase.** *(web · HIGH)*
**196 tribes' ordinances reference a Revenue Allocation Plan**, and the obvious reading —
that per-capita distribution exists — is wrong. **160 carry only the conditional statutory
recitation of 25 U.S.C. 2710(b)(3)**: *"**If** the Tribe elects to make per capita
payments…"* That proves the ordinance contemplates per capita, not that a plan or a
distribution exists. **22 assert a plan or election in the indicative — the real leads. 22
prohibit per capita outright — also a finding.** A short, precise piece about the difference
between a statute being quoted and a fact being stated, on a subject about which almost
everything written is wrong.

**G5. Where a tribe pleads determines whether it wins.** *(web · MEDIUM)*
`gaming_land_decisions.csv`: 138 BIA IGRA §20 decisions, 95 tribes, 22 states, 1990-03-05 →
2026-03-09. **Approved 104 · Disapproved 29 · Pending 5.** Legal theory: Two-Part Secretarial
Determination 47 · Restored Lands 31 · Within/Contiguous 25 · OK Former Reservation 17 ·
Initial Reservation 8 · Land Claim Settlement 6 · Last Recognized Reservation 3. Peaks in
2008 (21) and 2020 (11).
With `gaming_decision_events.csv` (265 events, 17 types) the *procedural path* becomes
visible: 71 FR land-acquisition notices, **2 FR reversals, 8 remands, 6 governor
concurrences against 4 governor NON-concurrences**, 4 reconsiderations, 1 rescission.
**Governor non-concurrence is a documented veto point** and almost nobody outside gaming
counsel knows the number is that small.
**Mandatory caveat, and it is in the manifest already:** *"Decision STATUS alone is
insufficient: approvals have been rescinded and reversed after the index recorded them.
Read the event stream."* Plus the structural selection bias — **only projects requiring a
federal action appear**, and BIA states its list is not exhaustive.

**G6. The Single Audit reversal.** *(paper · HIGH)* — refusal **R3**, in full. It is the
methodological companion to the flagship and it explains where the machine-participation
figures came from.

**G7. LOW — device manufacturers.** Publish as a **negative finding** or not at all: **0 of
1,326 device observation rows name a manufacturer**; of 158 declination letters swept, 4
mention a gaming machine and **0 name a manufacturer**; 38 tribal-issuer 10-K/S-4s swept and
**0 name a slot supplier in a supply context**; and of 740 SEC supplier-disclosure rows
across 51 entities, only **2** are `VENDOR_AUTHORIZED_BY_TRIBAL_REGULATOR` — *because a
mention is not an authorisation, a prospective approval is not a licence held, and a tribal
gaming authority naming itself in its own 10-K is not a vendor relationship.*

### Mis-shelved and near-empty files — fix before the collection ships

- **`nd_severance_allocation.csv` (7 rows) is not gaming.** It is MHA Nation **oil and gas
  severance tax** allocation. It belongs on `natural-resources`.
- **`fac_audit_sefa_gaming_programs.csv` holds 1 row.** Effectively empty; do not cite it as
  a dataset.
- **`gaming_mitigation_agreements.csv` (24 rows) ends 2024-02.** Two years stale at launch —
  refresh or state it.

> **✅ VERIFIED 2026-08-26.** Machine participation (25 / 8 entities / both Robinson figures
> / the Sault verbatim) ✅ · property locations 2,212 / 1,068 / 539 ✅ · vendor share 610 ✅ ·
> California 0 derived rows and the 9,222 / 938 split ✅ · Florida 44 rows killed and 0
> derived bounds ✅ · 415 precision downgrades ✅ · OCR 32 → 10 ✅ and the "66" reconciled as
> 72 raw minus 6 OCR garbles.
> **Corrections that must be made: "150/148" → 148 on day 31 and 153 on day 15; "2 rows with
> figures" → "two exact participation figures"; "490 NIGC locations" → 496; "321 tribes" →
> 298; and `nigc_regional_ggr` must be filtered on one `region_system_version`.**

---

<!-- SECTION:refusals -->
# THE REFUSALS — THE STRONGEST MATERIAL IN THE SLATE

*This project kills findings that do not survive scrutiny, and that discipline is itself a
story. It is also the only category of writing here that no competitor can copy, because
copying it would require having done the work and then thrown it away.*

The editorial argument for publishing refusals is not modesty. It is that **a refusal is a
fact about the source that the source does not disclose**, and it is usually the single
most useful thing a subscriber can learn about a dataset before they build on it.

Two rules for writing them:

1. **Publish the arithmetic that failed, not just the conclusion.** "We could not derive
   California revenue" is a shrug. "$19M ÷ 15% = $126.7M, correct arithmetic against a
   correctly-cited rate, wrong by an order of magnitude" is a lesson.
2. **Name what would have shipped.** The reader must be able to see the sentence we did
   not print. That is what makes it a story rather than a disclaimer.

---

### R1 — California: zero derived revenue rows, because every rate is marginal

**Shelf: gaming (grove). Also publishable as a standalone methods piece.**

51 California compact rates were marked `INVERTIBLE_FLAT_RATE`. Joining them to RSTF
receipts produced **795 publishable-looking tribe revenue figures**. Reading the compact
quotes one at a time showed **every single one is a marginal base**:

> "of its Net Win from the operation of Gaming Devices **in excess of** three hundred
> fifty (350)"

> a fixed annual sum plus 15% on "the **additional** Gaming Devices"

**San Manuel: `$19M receipt ÷ 15% = $126.7M` would have shipped as that nation's annual
Net Win. The true figure is far larger** — the rate applies only to revenue above a
threshold, so dividing recovers the *excess*, not the total. The citation would have been
correct. The arithmetic would have been correct. The number would have been wrong by an
order of magnitude, in the direction that flatters nobody.

**Final California state after the guard: 0 derived revenue rows.** 9,222
`TRIBE_LEVEL_REVENUE` and 938 `BOUNDED_DERIVED_REVENUE`, each naming its own blocker.

The rule earned: **before inverting any rate, read the base clause for `in excess of`,
`above`, `additional`, `over`, `beyond`, or a bracket schedule.** A flat rate divides; a
marginal rate does not.

Two adjacent California refusals that belong in the same piece:
- **CGCC suppresses some tribes' amounts** from 2016, printing `--` and reporting them
  only in an "Aggregate Total for Tribes" line. **318 rows** carry
  `value_suppressed_by_regulator` with a blank value; the aggregate is typed
  `aggregate_of_suppressed_tribes` and **never attributed to a tribe**.
- **SDF does not name the tribe** — it runs county → local agency → project. Not
  facility-attributable, and never summed with RSTF.

---

### R2 — Florida: a bound built, published in a draft, then killed by the publisher's own numbers

**Shelf: gaming (grove). The cleanest single refusal in the project.**

The Florida build constructed `Net Win ≤ payment ÷ rate_min`, **published it in a draft,
and then killed all 44 rows** — because the source falsified it.

The bound is true of the **obligation**. Florida EDR publishes **receipts**. FY2013/14
receipts of **$237,312,301** imply a ceiling of **$1.978bn**, while **EDR's own Net Win
for that year is $2.098bn**. The bound is violated by the publisher's own figures. EDR
states the mechanism itself: *"True-up payments generated from activity in any Fiscal Year
are received in the following Fiscal Year."*

The rule earned: **before inverting any payment, establish whether the figure is what was
OWED or what ARRIVED.** A cash-basis receipt series lags the accrual it derives from, and
a bound built across that gap is arithmetically sound and factually wrong. The arithmetic
now lives in a `bound_basis` column on every payment row **instead of producing a bound**.

Three distinct ways a rate inversion failed, all in one build day — this is the spine of
the article:

| # | failure | where |
|---|---|---|
| 1 | **marginal base** — "in excess of 350 devices" | California, 795 rows killed |
| 2 | **graduated schedule read as a flat rate** | New Mexico's spelled-out brackets; Florida's 10%, which is the bottom tier of a graduated schedule for one game category under a $2.5bn guaranteed minimum |
| 3 | **receipts vs obligation timing** | Florida, 44 rows killed |

Honest disclosure the piece must carry: `compact_structured_terms.csv` **still marks
Florida `revenue_sharing_rate = 10` as `INVERTIBLE_FLAT_RATE`.** It is not. Open review
item `FL-COMPACT-RATE-10PCT-INVERTIBILITY`.

---

### R3 — The Single Audit reversal: a dead end recorded from one entity's behaviour

**Shelf: gaming (grove) for the disclosures; the reversal itself is cross-collection.**

Tribal Single Audits were written into `START_HERE.md` under **"documented dead ends — do
not retry"**, on the strength of 2 CFR 200.512(b)(2) and Seminole Tribe of Florida
returning `is_public: false` on 10 of 10 filings.

**2 CFR 200.512(b)(2) is an auditee OPT-OUT, not a bar.** Measured on `api.fac.gov`:
**6,780 `entity_type = tribal` records, 2,052 (30.3%) `is_public = true`**, and their
reporting-package PDFs download — Sault Ste. Marie, Mississippi Choctaw, Muscogee (Creek),
Gila River, Turtle Mountain, Quapaw, Robinson Rancheria.

**And the withholding is per endpoint**, which is the finding inside the finding.
Matched samples of 25:

| endpoint | public auditee | non-public auditee |
|---|---|---|
| `notes_to_sefa` | 25/25 | **0/25** |
| findings / corrective actions | 25/25 | **0/25** |
| reporting-package PDF | serves | **403** |
| **`federal_awards` (SEFA)** | **25/25** | **25/25** |

**The SEFA survives the withholding; the reporting package does not.** 127 SEFA rows exist
for Seminole FY2022 against a 403 on its PDF.

The rule earned, and the reason this is a story rather than a correction: **one auditee's
election was generalised into a rule about the source.** Same error shape as "a broken
search is not evidence of absence" — a property of one record read as a property of the
whole system. **A dead end recorded from a single entity's behaviour needs a second entity
before it is written down.**

---

### R4 — Fabricated precision: 415 gaming dates that were wearing a day they never had

**Shelf: gaming (grove).**

**415 gaming dates were carrying a day of the month their own precision field said they did
not have**, and were downgraded to their true precision. Verified 2026-08-26 by diffing
against `gaming_facilities.csv.bak_2026-08-26_pre158`: **339 open dates + 76 close dates =
415.** Of the 339 open dates, **177 truncated to `YYYY`** and 162 to `YYYY-MM`; close dates
went 17 to year and 59 to month. **`open_date_source_value_verbatim` preserves the original
full ISO string on 339 of 339 — nothing was lost, only demoted.**

A placeholder wearing an ISO date is indistinguishable from an observation until someone
counts the day-of-month distribution; real opening dates do not cluster on the 15th and the
31st. In the pre-fix file: **148 dates on 31 December, 153 on day 15**, and 3 more on a
non-December day 31 — **304 placeholder-shaped values.** After the fix only 4 day-31 and 6
day-15 dates survive with day precision.

**⚠ Two corrections to the figures in circulation.** `docs/COMPETITIVE_POSITION.md` line 322
says *"150 on day 31, 148 on day 15."* **It does not reproduce** — it is 148 and 153, and
`docs/FACT_CHECK_2026-08-06.md` row B-28 already flagged it (that check measured 151/155).
**And 304 and 415 are two different measurements** — placeholder-*shaped* values versus
precision-contradicting values. Do not attach one to the other.

This is the smallest refusal in the slate and possibly the most useful to a data buyer,
because it is the one they can check in their own vendor file in about four minutes.

---

### R5 — A fiscal sponsor is not the project it sponsors

**Shelf: nonprofits (pro).**

The largest lobbying figure recovered from the grantee 990 pull is **$43,568,567 on the
TY2024 return of New Venture Fund** (EIN 20-5806345) — a Washington DC fiscal sponsor with
roughly $900M of expenses. The philanthropy queue proposed `NATIVE_ORG` for it, on the
strength of a profile for *Alaska Native Birthworkers Community* — which is a fiscally
**sponsored project**, not the filer.

**The project is Native. The legal person that filed the return is not.** Attributing a
sponsor's $43.5M to Indian Country because it hosts a Native project would be a
catastrophic false attribution, and **it would look well-sourced**.

Rule: **an EIN-keyed filing fact says nothing about the Native status of the filer.**
17 recipients whose Native typing rests on a proposed ruling *and* now carry a 990
lobbying figure sit in the review queue with the dollar amount attached.

Companion trap from the same build: **The Nature Conservancy's TY2019 return reports the
identical $8,086,325 on Schedule C Part II-B and on Part IX line 11d.** Both parse
correctly. Summing them invents $16.2M. The two columns stay separate and are never added.

---

### R6 — $56B of real records that a plausible cleaning step would have deleted

**Shelf: funding (standard).** Full detail in the `funding` slate, item F5. In one line:
a dedup pass removed $67B; only **9.8% ($6.58B)** is a demonstrable duplicate, and
**83.7% ($56.27B)** is the same award seen through two observation windows. *"Deleting the
smaller one is a guess, not a dedup."*

---

### R7 — A guard that discloses it refuses true attributions

**Shelf: funding (standard).** Full detail at F4. The publishable sentence:
**$5,946,365,640 across 12,987 rows and 190 recipient names is withheld from Native
totals**, and the log names the ones it is probably wrong to withhold. *"A conservative
refusal that lands in a queue is recoverable; a false attribution that ships is not."*

---

### R8 — Three states that look identical in a coverage table and are opposite findings

**Cross-collection; strongest fit is `natural-resources` and `gaming`.**

South Dakota's `dor.sd.gov/search/` returns **zero results for `casino`** — a term
demonstrably present across that same site. Kansas's sitemap returns HTTP 200 with **zero
entries**. Oregon's 404s. Arizona's 478-URL sitemap contains **zero** tribal pages.

**A site's own navigation failing is a fact about the navigation.** Three captures of the
South Dakota search are retained as evidence of the *search behaviour* and must never be
cited as evidence that South Dakota publishes nothing.

Hence the four-state vocabulary every Cedar Press coverage table carries:

| | meaning |
|---|---|
| `PUBLISHES` | retrieved it |
| `WITHHOLDS` | published a statement that it will not release — e.g. Washington deems per-tribe fuel data *"personal information and exempt from public inspection"* |
| `NOT_FOUND` | swept and did not find it, **naming what was swept** |
| `NOT_CHECKED` | nobody looked |

**A state that withholds by statute and a state nobody checked are opposite findings.** The
first is permanent; the second is unfinished work. Most published "coverage" tables in this
field collapse all four into a blank cell.

---

### R9 — The substring that would have mistyped 616 documents

**Shelf: federal-register (standard).**

**"Ex Parte No. 733" is a Surface Transportation Board *docket number*.** Verified
2026-08-26: substring matching on an ex parte phrase types **616 STB documents** as ex parte
*communications*. They are not communications; they are filings in a numbered proceeding
whose name happens to contain the words. Verbatim:

> **"EX PARTE" IS A DOCKET NUMBER AT THE SURFACE TRANSPORTATION BOARD.** STB numbers its
> rulemakings of general applicability *Ex Parte No. 290*, *Ex Parte No. 733* … The string
> is present and no communication is disclosed. **Typing those as ex parte communications
> because the substring matched is the same error shape as reading the Wichita Tribe out of
> "Boys & Girls Clubs of Wichita Falls".**

Adjacent and equally instructive: **the FCC is 4,430 of the 7,818 documents and contributes
almost nothing** — its actual ex parte filings live in ECFS, and the FR text is
permit-but-disclose boilerplate. *"An agency with the strongest ex parte disclosure regime
in government contributes almost nothing to an FR-based dataset, and its 4,430 documents
make it look like the opposite."* **The largest contributor to a keyword count can be the
least informative part of it.**

*(Two precision notes: the file holds **7,820** rows against an index of 7,818 — the +2 are
two new FERC notices. And **616 is STB alone**; the log's phrasing "STB or its ICC
predecessor" describes a union of **727**.)*

---

### R10 — A classifier that invented a NAGPRA collapse that never happened

**Shelf: nagpra (standard) / federal-register (standard).**

The FR theme series showed NAGPRA notices collapsing from ~80/yr in 2002 to ~17/yr across
2003–2010, then exploding after 2011. **That did not happen.**

Before 2011, almost no NAGPRA notice in the corpus carries an abstract at all (0–5 per
year against 90–214 notices per year), and their titles — *"Notice of Inventory
Completion: Beloit College, Logan Museum of Anthropology, Beloit, WI"* — contain no Native
term. So they fall into `body_only_unverifiable`, never reach the theme classifier, and
vanish from the series. **The trough is an artefact of abstract availability interacting
with our own relevance tier.** It was caught only because one such notice turned up in a
120-document hand-audit sample.

The correction is the part worth publishing: **it does not re-tune the tier rule, because
that would invalidate the audit.** It classifies NAGPRA on the signal present throughout —
the FR's own standardised notice titles, prescribed by 43 CFR part 10.

And the generalisation, which bounds every other series in the corpus: **abstract coverage
runs 70–82% before 2011 and 88–92% after. Every pre-2011 theme count is a floor, not a
level, and no theme's trend may be read across the 2011 boundary without checking whether
it depends on abstracts.**

---

### R11 — A finding reported because it was the prior, and it is not supported

**Shelf: lobbying (standard).**

The hypothesis was that tribal lobbying shifted **from gaming toward broadband and
health**. Gaming did fall (14.4% → 5.7% of family mentions). **Broadband rose but remains
one of the two smallest families (0.5% → 1.6%), and health is flat (8.1% → 8.3%).** The
gaming share did not move to health.

Reported because it was the prior. Most published analysis in this space would have
reported the gaming decline and the broadband rise and let the reader draw the
implication.

Same piece carries the verbosity trap: the first version of this series measured each
family's **share of classified filings** and showed almost every family rising, because
the mean number of issue families per filing rose from ~2.0 in 2002–03 to ~3.1 in the
2020s. **Filings got wordier, so against that denominator everything grows.** It would
have produced a page of spurious growth findings. The verbosity-neutral measure is
composition — `share_of_family_mentions`.

---

### R12 — Casino City: a source we read and will never publish

**Shelf: gaming (grove). This is a licensing refusal, not an evidentiary one, and it
belongs in the set because it constrains the flagship.**

**Casino City may be read for QA and never published.** `tribal_property_list` **is**
Casino City, and the vendor share of the property universe is **610 of 774** — not 440, as
was once written. **No vendor-derived figure goes in a public article**, and the flagship
gaming piece is designed around that constraint rather than against it.

Two related licensing marks that shape what can be printed:

- **D&B Open Data** (legal name, street, city, state, ZIP) may not be disseminated in
  bulk, and attaches to **every base award dated before 2022-04-04** — 100% of the SAM
  FY2000–2007 backfill. **Contract facts publish; entity name and address do not.**
- **A SAM socio-economic flag is self-certification.** Goldbelt Raven, an ANC subsidiary,
  certifies `alaskanNativeCorporationOwnedFirm = NO`. Any piece built on set-aside flags
  must say what the flag is.

---

### R13 — A characterisation we would be authoring

**Shelf: lobbying (standard). The best refusal in the project for explaining "evidentiary
standard" to a non-technical reader.**

The spec asked for a column called `position_on_native_issue`. It was refused, in these
words:

> "This is the highest-risk item in the spec, and it is **not a data problem**…
> `position_on_native_issue = Oppose` is a **characterisation we would be authoring**,
> published under our name, about a named organisation."

> "**A wrong `Oppose` on a named party is defamatory in a way a wrong CAGE code is not.**"

It was replaced with a derived, falsifiable `alignment ∈ {SAME | OPPOSED |
NO_TRIBAL_POSITION_FOUND}`, computed per bill from **two sourced positions** rather than
authored from one.

The same discipline runs through the whole shelf: **a visitor log is not a meeting**
(`may_promote_event_class(ACCESS → ADVOCACY)` returns False, enforced in code); **advocacy
is not lobbying** (*"conflating them would be wrong in a way that matters legally"*); and
**no dataset about private individuals** — 0 visitor names, 274 NRC individuals withheld,
**10,077 IBIA/IBLA natural persons blanked, each with a stated reason.**

---

### R14 — The empty file that was deliberately not written

**Shelf: subcontracting (pro). The smallest decision in this document and possibly the
purest.**

A review file was due. The source served nothing. So:

> "`review/subaward_api_unresolved_<date>.csv` **was not written.** … With zero rows
> retrieved it would be an empty file, and **an empty review file reads as *'we looked and
> found nothing to rule'*** — the `NOT_FOUND` / `NOT_CHECKED` conflation this project treats
> as a distinct kind of error. **NOT_CHECKED, because the source served nothing.**"

Writing the empty file would have been more diligent-looking and less true. Companion from
the same log: *"It did not read the five dead tokens as 'not published.' **A failed job and
an absent object are different facts.**"*

---

### R15 — A $10 discrepancy killed a fiscal year

**Shelf: natural-resources (pro).**

MMS FY1997 is absent from `resource_revenue.csv` — confirmed by measurement — because a
reconciliation gate caught **a $10 internal inconsistency in the source document.** Nine
recovered fiscal years shipped; that one did not.

The same gate refused **16 asset facts on its first run, 13 of them because a declared
number did not appear literally in its own quote.**

And the most instructive refusal on that shelf is arithmetic rather than editorial: **the
Osage Minerals Council prints a divisor of 2,228.97393 directly beside its per-headright
rate**, and multiplying would produce a total-revenue figure. *"Refused. The divisor is used
only as a check, never as a multiplier."* A new `aggregation_level` value,
`per_headright_rate`, was created **so the non-additivity is machine-visible to the next
reader** rather than living in a footnote.

---

### R16 — A dedupe that would have destroyed $10.8 billion

**Shelf: natural-resources (pro). The most concrete demonstration available of what
redaction does to a dataset.**

From FY2015 onward, ONRR's `fiscal_year_disbursements.csv` carries **11–15 rows per year
that are identical in every published column** and differ only in amount. The obvious
cleaning step — dedupe on the visible key — **discards 134 rows and $10,789,042,639.73**
(reproduced to the cent).

They are not duplicates. **The dimension that separates them was suppressed along with the
geography.** A reader who has never seen the suppressed column has no way to know that the
rows are distinct, and every standard data-hygiene instinct says to collapse them.

That is the whole argument for publishing suppression as a measurement:
**0 of 9,238 Native rows carry any geography, against 400,597 of 401,348 (99.8%) federal
rows** — and the $10.8B is what that gap costs somebody who does not know it is there.

---

<!-- SECTION:ranking -->
# THE SLATE, RANKED BY LAUNCH-READINESS

**⚠ RE-RANKED 2026-08-26 after the landscape scan and two owner directions.** The previous
ranking scored evidence, blockers and shipping. It now scores five things, in this order:

1. **Unclaimed** — is it in the scan's genuinely-open list, or is it one of the nine already
   taken?
2. **Stands on our own measurements** — not on a Native-versus-non-Native comparison, which
   the owner has deprioritised.
3. **Speed** — *"he wants to produce content quickly."* **A piece writable from data already
   on disk outranks a better piece that needs another pull.**
4. **Blockers** — how big, and are they ours to clear.
5. **Shipping** — can a reader get the data the piece points at.

## TIER 0 — write this first. No new data, no blockers, a named public dispute waiting.

| # | collection | piece | why it jumps the queue |
|---|---|---|---|
| **0** | **`contractors`** | **A ranking of top tribal, ANC and NHO federal contractors, with the ownership chain shown** | **It does not exist anywhere** — checked across seven outlets. Falls straight out of the 498-entity attributed set with **zero new pulls**. Impossible for the incumbents by construction (TBN has no USAspending capability; CICD's policy is anonymisation; **BGOV ranks Afognak at #174 and cannot name Alutiiq Pacific**). And **a U.S. senator and the Poarch Band publicly fought over whose 8(a) contracts count as whose with no dataset to settle it.** On every one of the five criteria this is the best piece in the document. |

## TIER 1 — ready to draft now

| # | collection | launch piece | why it is here |
|---|---|---|---|
| **1** | **`contractors`** | *How much does the federal flag miss? We counted the same firms twice.* | **The only contracting story that is both unclaimed and consequential** (scan §6). 22 of 40 hand-ruled firms carry zero Native self-certification, $212.5M, Frontier Electronic Systems at $204M with no flag at all. **Nobody else holds both counts on the same universe.** Corpus-wide magnitude is being sized — slot reserved. |
| **2** | **`gaming`** ★flagship | *8.6% of operations hold 55.8% of the revenue — and the federal government cannot tell you which 8.6%* | **Grove-shelf, and CICD does not touch gaming at all.** Fully specified, every shown figure verified, and it is the piece with a direct commercial purpose. Two things to clear first: confirm the licence gate is live, and **reconcile 784 → 449 current against CRS IF12527's 532**. |
| **3** | **`natural-resources`** | *No published, named-tribe resource revenue series exists in the US — except the Osage, who publish for themselves* | Three independent legs, all measured, all ours. **The core finding is about ABSENCE, so it carries no attribution risk** — the one class of story that cannot false-attribute. Data FINAL or terminal. |
| **4** | **`nonprofits`** | *29.90% of Schedule I grant money goes to organizations the IRS has no record of* — **plus the Census of Governments original** | A fact about the **source**, so it survives every ruling caveat. And the companion is a **new Cedar Press original measured during the scan**: `tribal` / `tribe` / `Native` / `reservation` appear **0 times in 463 pages** of the manual that defines the Census of Governments. **Two independent measurements of the same absence, from two different agencies.** |
| **5** | **`funding`** | *Congress said the record starts in FY2007. Nobody measured what the years before it contain. We did: 0.0%.* | **Reframed 2026-08-26.** The rate is original and unclaimed; the boundary is FFATA §2 and is conceded in paragraph one. Entirely FINAL. **One open vulnerability: write the FY2007 overlap de-duplication statement into the codebook before anyone asks.** |

## TIER 2 — one named fix away

| # | collection | launch piece | the fix |
|---|---|---|---|
| **6** | **`federal-register`** | *We counted 156,452 documents. About 20,800 actually are about Indian Country.* | Two copy fixes (14.3% not 14.2%; STB 616 is STB alone). **And the shelf's second piece — FERC, 102,615 filings, "nothing adjacent found" — is complete on disk and needs no pull.** |
| **7** | **`subcontracting`** | *$2.27B of federal subcontracting is one tribe's firm hiring another tribe's* | **Mark the FY2021–24 hole on every chart.** Note the adjacent story is taken — *"Native primes hire local non-Native small businesses"* is CICD 2024 and 2026 — so lead on the **cross-tribal** flow, which is not. |
| **8** | **`deals`** | *The Indian Country deal curve is a chart of when three agencies announced grant rounds* | **`deals_taxonomy.csv` is stale at 790** and cannot source the chart. **And cite Moreno/Dippel/Siken TBN 2024-05-05 in the lede** — pitch as an update and expansion of the owner's own prior analysis. |
| **9** | **`legislation`** | *Every roll call on Indian Country legislation, checked against the official record — including the two that do not match* | **Promoted over the enactment-ratio piece**, which was a Native-versus-general comparison and is now demoted. Fix the lowercase-`chamber` bug; reconcile `outcome` 229 against `disposition` 283 before any enactment count is printed. |

## TIER 3 — blocked, and the blockers are ours

| # | collection | launch piece | the blocker |
|---|---|---|---|
| **10** | **`lobbying`** | *Gaming has more than halved as a share of what Indian Country lobbies about* | **The cleanest gap in the entire landscape sweep — ZERO tribal lobbying analysis exists anywhere across nine organisations.** **All three blockers were CLEARED 2026-08-26 (evening)** — (a) the panel was rebuilt and `TRBF-SRPMCP-00` now reads 141 filings / $10,414,000; (b) the `rosa santa` instance and 15 more clients were withdrawn, 471 filings / $5,756,834, leaving `TRBF-SROSAR-00` at its own 13 filings / $210,000; (c) the confidence table is restated in §6. **Publish `high` only: 23,741 filings / $627,601,108 — unchanged, because every withdrawal was `medium`.** One residual, named: `lobbying_registrants.csv` and `lobbying_registrant_concentration.csv` still carry aggregates over the 471; re-run 180 then 182 before quoting a registrant concentration figure. With no incumbent to hide behind, the first published analysis of tribal lobbying is the one everyone checks. |
| **11** | **`nagpra`** | *The last three years produced more NAGPRA notices than the first seventeen* | **⛔ Eight documented misattributions are all still live in the bridge**, including the completely erased Forest County Potawatomi Community. And this is the one piece whose right pre-publication step is **a conversation with THPOs and the Review Committee**, not another measurement. The finding is HIGH; the responsibility bar is higher. |

## What every row is blocked on jointly

**Prior art is RESOLVED.** `docs/PUBLISHED_LANDSCAPE_2026-08-26.md` has landed. Nine stories
are off the table, fourteen claims must be cited rather than originated, one framing was
withdrawn (FAADS), the word "first" comes off the enterprise-crosswalk claim, and two
headline counts — **784 gaming facilities** and **$310.01B contracting** — must be reconciled
against published federal figures before they appear anywhere. **No Cedar Press claim was
found flatly redundant.**

**Shipping is unresolved for all eleven.** Measured 2026-08-26 (`docs/SHIP_GAP_REPORT.json`,
`healthy: false`): project ship ratio **66.7%**, **201 of 255 tables at 0%**, **2,609,646
unshipped rows**, 11 stale `dist/` artefacts. And a structural point that matters more than
the ratio: **all 114 files under `dist/` are `.notes.json`, `.NOTES.md`, manifests or an
index — there is not one data file**, and `dist/01_deals` still records **790**. **An
article can be written against `data/clean/`; a download the article points a reader at
cannot.** Run the chain in `docs/SHIPPING_RUNBOOK.md`, in order, **only when no writer is
live.**

**Three of the eleven Collections have no manifest at all.** `dist/manifests/` holds nine —
`bills-votes`, `compacts`, `contractors`, `deals`, `federal-actions`, `funding`, `gaming`,
`lobbying`, `nonprofit` — and **`nagpra`, `subcontracting` and `natural-resources` are
missing**, while `compacts` is a manifest for something that is not one of the eleven
shelves. A manifest is an **authored** claim about what a dataset measures and is never
generated, so this is a writing backlog, not a build failure — but it is three pieces
without a descriptor to cite.

## The fastest paths to published content — ordered for speed, per the owner

1. **Write the top-contractor ranking (Tier 0).** No pull, no blocker, no prior art, a named
   public dispute waiting for it. **This is the shortest path from today to a published
   artefact.**
2. **Run `code/151_rebuild_entity_evidence_profile.py`.** Zero network, read-only inputs,
   minutes. Refreshes the corroboration claim (≥516 entities at 3+ sources) that every piece
   can cite.
3. **Rebuild `tribe_year_lobbying_panel.csv` from the corrected disclosures.** Clears the
   largest single blocker in the slate and moves the *cleanest gap in the whole landscape*
   from Tier 3 to Tier 2.
4. **Reconcile the two headline counts** — 784 → 449 current against CRS IF12527's 532, and
   $310.01B against CICD's $26.6B via the four definitional differences. Both tables are
   already drafted in this document. **Neither needs data; both unblock a Tier 1 piece.**
5. **Pull DoD's P-1 Line 30 budget justification.** The only entry on this list that needs a
   pull. Confirmed and cheap, and it converts C2 — the Indian Incentive Program piece — from
   feasibility into the most intellectually interesting article on the `contractors` shelf.

## Two framings that are now closed and must not be re-opened

- **The entity-spine derivation question.** Ruled 2026-08-26: the CICD crosswalk is an
  **input, not a blocker**. One line on the methods page crediting it, and nothing else.
  **It should not surface in any piece.**
- **CICD as a foil.** They are a sanity check on arithmetic. The owner built their datasets
  and is a co-author on three of their publications. **No piece is organised as a response,
  comparison or corrective to them.**

## Two things this document found that nobody asked for

**The spine moved while this was being written** — 1,310 in the contradictions register,
**1,489 measured**, and the difference is 179 Native Hawaiian Organizations landing during
the session. Five live values for the spine count now exist and this document's is the
fifth. **Re-measure on the morning you draft.**

**`docs/COVERAGE_AUDIT.md`'s successor is now correct and `START_HERE.md` is the stale
document.** `data/clean/coverage_audit.csv` was rebuilt 2026-08-26 and reproduces exactly;
START_HERE line 151 still says it must not be quoted. That reversal is worth recording
because it is the *good* case — the fix landed and the warning outlived it.

---

*End of the ranked slate. Last reviewed 2026-08-26. Update the header date whenever you
touch anything above.*
