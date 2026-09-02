# Individually Native-owned business verification — build log

*Built 2026-08-26. Scripts `code/170` (candidates), `code/171` (verification table),
`code/172` (codebook fragment), `code/173` (regenerates section 9 from the table).*

> Elijah, 2026-08-26: *"I still want to verify individual Native American
> ownership though — like seeing if their website says it. You can't lie to
> federal contractors, but anyway, the ones I have identified previously as
> individually Native owned, I looked."*

Two instructions, and the second one is the harder of the two.

---

## WHAT WAS BUILT

| file | what it is |
|---|---|
| `data/clean/individual_native_ownership_verification.csv` | the product — one row per candidate, four independent evidence fields, verbatim sentence, URL, fetch date, computed tier |
| `data/clean/individual_native_verification_candidates.csv` | the work list (script 170) |
| `data/clean/individual_native_prior_rulings.csv` | every individual-Native ruling the owner has already made, gathered from five files in three vocabularies |
| `data/clean/codebook/02f_individual_native_verification.csv` | codebook fragment, 63 variables, every one described |
| `docs/codebooks/02f_individual_native_verification.md` | its markdown counterpart |
| `review/individual_native_ownership_ambiguous_2026-08-26.csv` | what needs a ruling, each row carrying its evidence |
| `data/raw/web/individual_native_verification_2026-08-26/` | the raw web pass: 12 input batches, 12 output batches |

---

## 1. HIS PRIOR RULINGS — FOUND, AND THEY WERE IN THREE DIFFERENT VOCABULARIES

**45 rulings, 45 distinct identifiers, all carried forward unchanged.** They do
not live in one place and they do not use one word, which is why a sweep that
assumes a single shape finds a third of them and reports success.

| source | n | the words used |
|---|---:|---|
| `data/spine/cedar_exclusion_rulings.csv` ← `hci_analysis.do` | **31** | `exclusion_reason = individually_native_owned`, note *"owned by individual Cherokees"* |
| `review/rulings_inbox_2026-08-08_elijah_batch2.csv` | **5** | `YOUR_RULING = INDIVIDUAL_NATIVE` |
| `review/rulings_inbox_2026-08-07_elijah.csv` | **4** | `YOUR_RULING = OWNER_NAMED` with a note beginning *"individual native"* |
| `review/rulings_inbox_2026-08-05{i,j,m}.csv` | **5** | `"Not a Native entity - individually Native-owned firm"` |

Three traps in that table, all of them live:

- **`OWNER_NAMED` is ambiguous by itself.** AGENTS.md settles it: `OWNER_NAMED`
  with a note beginning *"individual native"* is this class; a note naming a
  tribe or corporation (CALISTA, Bering Straits, Native Village of Eyak) is
  **tribal/ANC ownership and a completely different ruling**. The note, not the
  ruling word, carries the meaning. Script 170 matches on the note.
- **The 2026-08-05 rulings look like refusals and are not.** *"Not a Native
  entity — individually Native-owned firm"* refuses the **tribal link**, not
  Native ownership. Read as "not Native" it inverts his meaning and deletes
  five firms from the register. They are carried as
  `INDIVIDUAL_NATIVE_NOT_TRIBAL` so the direction of the refusal stays visible.
- **`cross_dataset_ruling_map.csv` shows 166 rows of
  `BLOCKED: individually_native_owned`, which is 31 rulings propagated across
  three identifier files.** Counting the rows counts his work 5.4× over.

**Nothing here was re-decided.** Where the web pass found a sentence vaguer than
his ruling — a site saying "Native American owned" where he ruled
`INDIVIDUAL_NATIVE` — the sentence is recorded and **the ruling stands**. The
review queue explicitly does not ask him to re-classify a firm he has already
classified; that guard is in `171` and is the reason the queue is shorter than
it would otherwise be.

---

## 2. THE FINDING THAT CHANGED THE BUILD: HIS RULINGS REACH FIRMS THE FEDERAL FLAG CANNOT

The candidate set was specified as unattributed awardees carrying a native
self-certification flag. Built that way it is **305 firms, $36.0B**, and it
**drops 29 of his 45 rulings on the floor** — only 11 of the 40 UEI-keyed
rulings land in the top 400 by obligations.

So a second stream was added: `candidate_basis = PRIOR_OWNER_RULING`. That is
not tidiness. It is where the finding is.

> **22 of the 40 prior-ruled firms carry ZERO native self-certification flags
> across every one of their contract rows.**

The largest is **Frontier Electronic Systems Corp — 998 contract rows,
$204,225,019 obligated, not one native flag on any of them**, ruled
`INDIVIDUAL_NATIVE` by the owner from the company's own site. Also in that
group: Cherokee Energy Management & Construction, Cherokee Holdings, Cherokee
Veterans Construction, Cherokee Controls, Bank of Cherokee County.

**No candidate set defined by the federal flag can ever reach those firms.**
The do-file already warned about this direction in general — *"discovery of
residual candidates restricted to Buy Indian / 8(a) / Indian Business
set-asides → tribally-owned firms with non-obvious names winning only
full-and-open contracts can be missed"* — and this is that undercount measured
on the individual class specifically.

**Consequence for the product:** `sam_self_certification` is a **discovery
channel with a documented blind spot**, never a definition of the population.
Any headline of the form "N individually Native-owned firms" built from the
flag alone is a floor, and the size of the gap is unknown because the only
instrument that has ever found a flagless one is a person looking.

Candidate set at this build: **335 firms** — 306 flagged + 29 prior-ruled — of
which **22 carry no native self-certification at all, holding $212.5M**. That
first number moves: `prime_contracts.csv` is written by other agents, and a
firm crossing the top-400 line changes it. **§9 is regenerated from the table
and is the count to quote**; the web pass covers 334 of the 335, the exception
being Iyabak Construction, which entered the top 400 after the batches were
dispatched.

One caution against over-reading it: this is a **Cherokee-heavy sample**. 31 of
the 45 rulings come from one do-file pass over Cherokee-named firms, so the
*direction* of the undercount is established and its *magnitude* across Indian
Country is not. What can be said is that the flag missed 22 firms that a person
found, and nothing in this project has ever looked for the flagless ones
systematically.

---

## 3. THE EVIDENCE MODEL, AND THE INDEPENDENCE RULE

Four fields, recorded separately, never collapsed into a boolean:

| field | what it is | is it independent of the firm? |
|---|---|---|
| `sam_self_certification` | the federal filing — `reported_8a`, `reported_buy_indian`, `reported_indian_business`, `reported_native_preference`, `setaside` | **no** |
| `self_description` | what the company's own website says, as a verbatim sentence | **no** |
| `third_party` | SBA 8(a)/DSBS, a certifying body, trade press, a court or GAO decision | **yes** |
| `tribal_affiliation_named` | does any source name the specific tribe | depends on the source |

### The rule that shapes the whole table

**A SAM flag and the company's website are the same party speaking in two
venues.** They are not two sources. When they agree, what has been established
is that the firm is *consistent* — worth recording, and not corroboration.

Counting them as two legs would have manufactured a tier-A population out of
one voice repeated twice. That is the same error shape as START_HERE finding
#1, where the exactness of an EIN was read as the correctness of a link: **the
weight of an assertion says nothing about its independence.**

A false certification to a contracting officer carries False Claims Act
exposure, so the federal flag is *weighty* self-certification — and START_HERE
already holds the counter-example that stops it being proof: **Goldbelt Raven,
an ANC subsidiary, certifies `alaskanNativeCorporationOwnedFirm = NO`.**

So `evidence_tier = A` requires at least one leg that is **not the firm**, and
`evidence_independence` records which of the three states every row is in.

### Tier is computed, not chosen

`compute_tier()` in `code/171` is a pure function of the legs present, and
`tier_basis` names them on every row so any reader can recompute it by hand.

| tier | rule |
|---|---|
| **A** | an independent leg (third party, or an owner ruling backed by a **retrieved third-party document**) plus a second agreeing leg |
| **B** | exactly one non-SAM leg — the website sentence alone, a third-party listing alone, or an owner ruling resting on a narrative note |
| **C** | federal self-certification only |
| **X** | a source names a **non-Native** owner against the federal flag — a finding, sent to review with its evidence, never a deletion |

This makes the owner's own evidence types do real work. A **CAGE registry
lookup, a GAO decision or an OpenCorporates filing** is a third-party document
and lifts his ruling to an independent leg. A **company website or an archived
company website** is the firm speaking about itself and does not — it is the
same voice as the SAM flag, retrieved by hand.

### NOT EVERY "THIRD PARTY" IS A THIRD PARTY — and this cost 21 tier-A rows

The researchers flagged it themselves, unprompted, in three separate batches:

> *"Every directory hit (govtribe, highergov, govconinabox, opengovus) is
> SAM-derived, i.e. the same self-certification the project already has."*

A federal-data aggregator republishing a SAM socio-economic flag is **the
firm's own voice arriving by a longer road**. Counting it as corroboration
double-counts `sam_self_certification` and manufactures tier A out of a single
assertion — precisely the failure the independence rule exists to prevent. A
company-issued press release is the same problem in a different costume:
PRNewswire and PRLog print what the company pays them to print.

So `third_party_independence` types every third-party URL by host:

| type | examples found | is it a leg? |
|---|---|---|
| `INDEPENDENT` | `gao.gov`, `sba.gov`, `irs.gov`, `doa.nc.gov`, `tethys.pnnl.gov`, Spokane Journal of Business, Construction Equipment magazine | **yes — the only kind that can reach tier A** |
| `RELATED_PARTY` | a parent, JV partner or corporate-family site — Calista, Old Harbor Native Corp, Mill Creek, The Clement Group | a leg, but it is the owner speaking |
| `SELF_SOURCED_AGGREGATOR` | `govcb.com`, `govcon.com`, `fedbizconnect.com`, `sba8a.com`, Buzzfile, BisProfiles, TheOrg, Salary.com, LinkedIn, PRNewswire, PRLog | **no — not counted at all** |

**Anything unrecognised is `UNCLASSIFIED` and confers no independence.**
Unknown provenance is not independence.

Applying it moved **tier A from 39 to 18**. Twenty-one rows had been tier A on
the strength of a SAM mirror or a press release. Every one of those demotions
is surfaced in the review queue naming the URL, so the demotion is visible
rather than silent.

---

## 4. THE BY-PRODUCT THAT MAY BE WORTH MORE THAN THE PRODUCT

Every candidate is `attributed_flag = 0`: **Cedar attributes it to nobody.**

The web pass therefore keeps turning up firms whose own site declares a
**tribe, an ANC or an NHO** as owner. Those are not individually Native-owned
firms. They are **missing tier-A entity attributions, at the dollar figure
already in the row.**

They are queued as `MISSING ENTITY ATTRIBUTION` with the declaring sentence and
the obligation attached. The queue deliberately does **not** propose an entity:
resolving one from the name is the containment defect, and half these names are
`NAME_TRAPS` terms.

This is the opposite of the finding the build set out to make, which is exactly
why it is written down rather than swallowed.

---

## 5. THREE GUARDS THAT ARE ON EVERY ROW

**A name is never evidence.** `name_trap_warning` fires on the 39 `NAME_TRAPS`
terms and on tribe-name-plus-place-suffix. 41 of 334 candidates carry one —
`cherokee`, `creek`, `indian`, `united`, `river`, `alliance`, `pacific`. Where
a trap name has **no** supporting claim, the row is queued saying so in as many
words, because a native-sounding name with nothing behind it is the single most
likely thing to be mistaken for a finding.

**Absence of a claim is never disproof.** The vocabulary is `NO_CLAIM_FOUND`,
never `NOT_NATIVE`. Plenty of small contractors never mention ownership on
their site. `SITE_UNREACHABLE` is kept separate again: only 404 and 403 are
facts about an object, and a 500 or a TLS failure is a fact about the moment.

**A current page cannot testify about a historical record.** `temporal_caveat`
is populated on **100% of rows**, and that is structural, not incidental:

> All **209,478** FY2023–FY2026 rows in `prime_contracts.csv` carry
> `attributed_flag = 1`. The archive backfill was seeded from known Native
> identifiers — `uei_exact` 152,516 / `parent_uei` 39,673 / `cage_exact` 17,306
> — rather than pulled full-universe. **`attributed_flag = 0` therefore selects
> the BGOV `master prime file.dta` era exclusively, and every candidate's
> contract activity ends FY2022 or earlier.**

So a 2026 page is always testifying about a record at least four years older
than itself, and on some rows twenty. Three gaming rulings were withdrawn
2026-08-06 for exactly this error. The caveat must travel with any quotation of
`self_description_sentence`.

It also means **nobody should go looking for new individually-Native firms in
FY2023+**: the absence there is a property of the pull, not of Indian Country.

---

## 5b. OWNERSHIP CHANGED INSIDE THE AWARD WINDOW — REPEATEDLY, AND WITH DATES

The temporal caveat is not a formality. The web pass turned up **at least nine
firms whose ownership provably changed during the years they were winning the
contracts in this file**, and in most cases the change is *dated*:

| firm | change | date | contract rows |
|---|---|---|---|
| Aeromet Inc. | L-3 Communications bought all stock, ~$20M | May 2003 | FY2000–2022 |
| ICRC | acquired by VSE Corporation | 2007-06-04 | FY2000–2017 |
| Akimeka | acquired by VSE Corporation | 2010 | FY2002–2020 |
| TeraThink | absorbed by CGI | 2020-03-31 | — |
| Meyer Contracting | sold to an ESOP, now 100% employee-owned | 2024 | FY2002–2021 |
| Lakota Solutions | acquired by Shee Atiká Inc. (ANC), founded 2006 as a GA 8(a) | undated on the page | FY2010–2022 |
| Arrowhead Contracting | majority-owned by Kava Equity Partners, the Southern Ute Growth Fund's investment entity | undated on the page | FY2000–2022 |
| Sayres and Associates | acquired by a private holding company, Broadtree Partners as PE sponsor | undated | FY2002–2022 |
| DAWSON portfolio (≥6 rows) | rebranded to **LAUKOA**, UEI/CAGE unchanged | 2026-06-29 | various, all ≤FY2022 |
| Indian Eyes | *"continues under new ownership"*, owner unnamed | undated | →FY2022 |

**No single ownership answer is correct for the whole span of any of those
rows.** That is why `evidence_tier = X` on Sayres is queued as a *finding with
its caveat attached* rather than a disproof: an ownership change inside the
award window produces exactly this pattern and leaves the federal flag correct
for the years it was filed.

It also lands directly on the insight already recorded in AGENTS.md — *"the
deals dataset IS the missing time-varying ownership ledger"*. These are ten
dated ownership-change events, discovered as a by-product of a verification
pass, most of them with a source URL already in the table. They belong in the
deals ledger, and once there they make attribution in this file
**year-aware** instead of forcing one answer across twenty years.

Note the DAWSON → LAUKOA case specifically: **the UEI and CAGE did not
change.** A rebrand that keeps the identifiers is invisible to every
identifier-keyed join in the project, and it happened eight weeks ago.

---

## 5c. A POSITIONAL ID FABRICATED AN ATTRIBUTION, AND IT WAS CAUGHT BY A RE-RUN

**This one nearly shipped, and it is worth more to the next agent than anything
else in this log.**

`verification_id` is `INV-nnnn`, assigned in descending obligation order. The
web pass was dispatched keyed on it. Between two runs of the pipeline — at
**17:57 on 2026-08-26** — a concurrent agent rewrote `prime_contracts.csv`.
One new firm (**Iyabak Construction**) crossed into the top 400, the candidate
set went 334 → 335, and **every id below the insertion point shifted by one.**

The visible result:

```
INV-0307   Cherokee Construction, Inc.
           self_description_url = https://www.fescorp.com/company-overview
           "FES is a Native American, woman-owned small business..."
```

That is **Frontier Electronic Systems' sentence, on Cherokee Construction's
row**, complete with URL and fetch date. Nothing errored. Nothing looked wrong.
It is a fabricated ownership attribution manufactured by nothing worse than a
rebuild against a moving upstream — the same shape as the Kootenai regression
and the re-run-57 regression already in AGENTS.md, arriving through a new door.

**The fix is not to freeze the upstream, and it is not to snapshot.** It is to
stop joining on a position:

- the input batches record `verification_id → awardee_uei`, so the web results
  are re-keyed to **UEI, then CAGE, then normalised name**, and joined to the
  candidate set on identity;
- `web_pass_matched_on` records which key carried each row (currently **UEI on
  334 of 334**);
- `web_pass_verification_id` keeps the id the firm held *at pass time*, so the
  divergence is visible and auditable rather than erased;
- a web row that matches no candidate, and a candidate that matches no web row,
  are both **reported loudly** instead of silently dropped. Iyabak Construction
  is the one candidate with no web coverage, and the run says so.

**Standing rule earned: never join two artefacts on a rank, an index, or a
row number when both derive from a file another agent can write.** A positional
key is only as stable as the least stable input, and on this machine that is
never stable. This one was caught because the pipeline was re-run and the
counts moved; had it been run once, it would have published.

---

## 6. PRIVACY — ANSWERED PER FIELD, NOT PER DATASET

A sole proprietorship's legal name is frequently a private person's name, and
Cedar does not publish a page that names a private individual.

- `privacy_class` — `CORPORATE_FORM_PRESENT`, `NO_CORPORATE_FORM`,
  `POSSIBLE_PERSONAL_NAME`, `UNKNOWN`. Deliberately over-inclusive: a
  two-or-three token name with no corporate form is treated as possibly
  personal even when it is not, because the two errors do not cost the same.
- `publishable_entity_name` = `N` on those rows.
- `publishable_sentence` = `N` where the quoted sentence carries a personal
  name on a row already flagged possibly-personal.
- `publishable_contract_facts` = `Y` throughout.
- `researcher_note` is `published = 0` in the codebook — it is where an owner's
  name lands when a company publishes one itself.

**The D&B question is answered and the answer is no.** These rows come from
BGOV `master prime file.dta` and the USAspending award archive, **not** from a
SAM entity extract, so the bulk-dissemination restriction on D&B Open Data
recorded in START_HERE does not attach. `dnb_open_data_attaches` says so on
every row, so the question can be re-answered per field the day anyone asks —
and any future SAM-sourced row must carry its own answer rather than inheriting
this one.

---

## 7. THE FINER-GRAINED FEDERAL FIELD, AND THE JOIN THAT IS STILL WAITING

`prime_contracts.csv` carries four coarse flags. The SAM extract carries the
field that actually separates a **person** from an **entity**:

```
flag_american_indian_owned        a PERSON
flag_sole_proprietorship
flag_tribally_owned_firm          an ENTITY
flag_alaskan_native_corporation_owned
flag_indian_tribe_federally_recognized
```

Measured on `data/clean/sam_prime_contracts_fy2000_2007.csv` as it stands
today: **McKinzie Construction carries `flag_american_indian_owned = YES` on
122 rows with `flag_tribally_owned_firm` never set** — the individual class
asserted by the filer in the filer's own federal record. That is exactly the
distinction this build needs, and `sam_individual_vs_entity` records it.

**It reaches only 4 of 334 candidates today, and that is a timing fact, not a
coverage fact.** Only the `TRIBAL` variant of the FY2000–2007 extract is loaded
(8,273 rows, `matched_variants = TRIBAL` on all of them). The two
`INDIVIDUAL_NATIVE_OWNED` variants — `AMERICAN INDIAN` (`xAjEAaGtTI`) and
`NATIVE AMERICAN` (`PTdhhaQztU`) — are accepted server-side and still
generating. **When they land, re-run `code/171`; the join needs no change.**

Note what it will and will not buy: it is a *sharper reading of one voice*,
never a second leg. It cannot move a row to tier A.

A concurrent agent is writing `docs/INDIVIDUAL_NATIVE_CLASS_PROPOSAL.md` from
those two variants. **It did not exist while this build ran** and none of its
files were written to. Coordinate through it.

---

## 8. THE WEB PASS — HOW IT WAS RUN

334 firms in 12 batches, one researcher per batch, each fetching a different
set of hosts. Per `docs/PULL_DISCIPLINE.md` this is not a shared-host problem:
these are ~300 distinct company websites, one request at a time each, and no
`_HOSTLOCK_` in `logs/` covers any of them. `api.sam.gov`, NIGC and the state
gaming regulators were off limits and were not contacted.

### Three tooling facts that shaped the result, and one of them is fixable

1. **A research session exhausts its WebSearch budget at ~200 calls.** *Every
   one of the twelve batches hit it*, most of them partway through, one before
   its first query. **`NO_SITE_FOUND` from a budget-exhausted session is not
   the same fact as `NO_SITE_FOUND` from a completed search.** The 106
   `NO_SITE_FOUND` rows are therefore a ceiling on absence, not a measurement
   of it, and this is the single largest known bias in the file.
2. **`web.archive.org` is blocked for `WebFetch` in this environment** — the
   availability API answers, the snapshots do not. For a candidate set whose
   contract activity ends FY2022 and reaches back to FY2000, **the archive is
   the only route to award-period ownership language**, and it was shut. Four
   batches independently named specific firms with confirmed live snapshots
   they could not read. `docs/PULL_DISCIPLINE.md` lists `web.archive.org` as
   "tolerant — the right fallback when an origin blocks"; that is true of the
   host and **not** true of this tool against it. Worth resolving before any
   re-run, because it is where the remaining yield is.
3. **The workaround that carried the build was `opengovus.com/sam-entity/<UEI>`**
   — a third-party SAM mirror that publishes each entity's own *registered
   website URL*. It recovered domains for roughly half the firms in several
   batches and is a better domain source than search. **It was used for domain
   discovery and identity only, never as ownership evidence**, because its
   business-type flags are re-published SAM self-certification and are already
   counted in `sam_flags_asserted`. `api.sam.gov` itself was never contacted.

Search engines behaved badly across the board through `WebFetch`: DuckDuckGo
and searx served CAPTCHAs, Brave/Mojeek/Ecosia/Startpage 403'd, Bing ignored
the query, Yahoo worked for a few calls then 500'd. Buzzfile, Blue Book,
ZoomInfo and Manta 403 on direct fetch — several firms have an *indexed*
third-party ownership sentence that could be seen in a snippet and not
retrieved. Those were recorded as `NOT_FOUND` with the lead in
`researcher_note`, **never cited from a snippet**.

`web_pass_batch` is on every row so one batch can be re-run without disturbing
the others.

### What the researchers caught that a name match would have shipped

Worth recording because each is a false attribution that did not happen:

- **`tmgva.com` is Training Modernization Group, not The Matthews Group** —
  different CAGE, same initials, same state.
- **`seselectrical.com` is a husband-and-wife electrical firm in Essex,
  England**, not SES Electrical LLC of Tennessee.
- **`glacier-tech.com` is Glacier Technologies LLC** (CAGE 36HM0), a BBNC
  subsidiary with a clean ownership sentence — and **not** Glacier Technical
  Solutions (CAGE 54GG5), the firm in the row. The sentence was not borrowed.
- **Bering Straits uses "wholly-owned subsidiary of …" on a *sibling*
  subsidiary's page but not on Global Technical Services'.** Recorded
  `NO_CLAIM_FOUND` with an explicit warning against transferring the sibling's
  sentence.
- **`coalcreekconstruction.com` is a Tennessee firm**, not the North Dakota
  awardee. **`arrowheadcontracting.com` is a Michigan residential builder**,
  not the Lenexa federal contractor. **`paragonsystemsinc.com` is the
  California company of that name**, not the Alabama one.
- **Nisga'a Data Systems is owned by Goldbelt, Inc.**, the ANCSA urban
  corporation for Juneau — not by the Nisga'a Nation of British Columbia, whose
  name it evokes.
- **Au' Authum Ki**: a search summary attributed "a member of the Salt River
  Pima-Maricopa Indian community" to the company. The researcher re-fetched the
  About page specifically to check, found the phrase absent, and recorded
  `tribal_affiliation_named = NO`.

And two firms whose *own sites* contradict their federal flag: **Native
American Services Corp** — *"NASCO is privately owned with headquarters in the
beautiful Silver Valley of Idaho"*, no Native claim anywhere — and **Native
Energy & Technology**, no ownership statement at all. Both self-certify
`reported_native_preference`. Both are recorded `NO_CLAIM_FOUND`, **not**
`NOT_NATIVE`, and both carry a `name_trap_warning`.

### Wording distinctions that were preserved rather than tidied

The point of quoting a sentence is that its exact words matter:

- **"founded" is not "owned."** Arrow Indian Contractors publishes *"a superior
  Native American-founded and Woman Owned construction company"* — the
  `-owned` suffix attaches to "Woman". Not upgraded.
- **A badge is not a sentence.** Gearhart's "Native American Owned and
  Operated" is a certification logo with no prose around it. SiloSmashers'
  only Native language sits inside an awards timeline. Both flagged.
- **Heritage is not ownership.** Firelake's About page explains that *"the
  inspiration for our company name was driven by our Native American
  Heritage"* — an etymology, not an ownership claim. Recorded
  `NO_CLAIM_FOUND` deliberately.
- **Descent is not enrollment.** One row names "Cherokee descent" with no
  nation and no enrollment; `tribal_affiliation_name` says so in as many words
  rather than resolving it to the Cherokee Nation.
- **An NHO is not a tribe.** Firms owned by Native Hawaiian Organizations are
  `tribal_affiliation_named = NO`, flagged in their notes.
- **One Mohawk affiliation is Canadian** (Six Nations of the Grand River / Bay
  of Quinte, Ontario) — recorded as found, and it is not a US federally
  recognised tribe.

---

## 9. MEASURED RESULTS

*Regenerated 2026-08-26 by `code/173_refresh_individual_native_results_section.py` from `data/clean/individual_native_ownership_verification.csv`. Do not hand-edit this section — re-run the script.*

**335 candidates, $36,313,241,504 in nominal obligations.** 306 reached via the federal flag, 29 reached only because the owner had already ruled them.

### Prior rulings

| | |
|---|---:|
| individual-Native rulings found across five files | **45** |
| distinct identifiers | **45** |
| landing on a candidate row and carried forward unchanged | **40** |
| obligations under a standing ruling | **$2,340,066,582** |
| prior-ruled firms carrying NO native self-certification | **22** |

### The web pass

| | n | share of checked |
|---|---:|---:|
| `CLAIM_FOUND` | 141 | 42.2% |
| `NO_CLAIM_FOUND` | 50 | 15.0% |
| `SITE_UNREACHABLE` | 37 | 11.1% |
| `NO_SITE_FOUND` | 106 | 31.7% |
| `NOT_CHECKED` | 1 | — |

**150 of 335 candidates carry a verbatim website sentence** (44.8%), covering $19,749,769,004.

**34 carry a third-party source** — the only leg that is not the firm speaking about itself, and the only one that can carry a row to tier A.

**31 name a specific tribe or nation.** An unnamed "Native American owned" is recorded as `NO`: it cannot be checked against a tribal roll and cannot be joined to the entity spine.

### Tier — computed from the legs present, never assigned

| tier | n | obligations |
|---|---:|---:|
| **A** | 18 | $1,793,549,293 |
| **B** | 160 | $16,287,981,103 |
| **C** | 156 | $17,951,054,628 |
| **X** | 1 | $280,656,480 |

### Independence — the column that decides whether anything was verified

| state | n |
|---|---:|
| `FEDERAL_SELF_CERT_ONLY` | 156 |
| `SELF_ASSERTION_ONLY` | 147 |
| `INDEPENDENT_CORROBORATION` | 31 |
| `INDEPENDENT_CONTRADICTION` | 1 |

### Ownership class, from the strongest EVIDENCED source

| class | n | obligations |
|---|---:|---:|
| `UNDETERMINED` | 146 | $16,620,430,990 |
| `INDIVIDUAL_NATIVE` | 74 | $5,073,650,826 |
| `NATIVE_UNSPECIFIED` | 47 | $5,430,607,938 |
| `ALASKA_NATIVE_CORPORATION` | 31 | $3,577,315,795 |
| `NATIVE_HAWAIIAN_ORGANIZATION` | 30 | $4,042,383,756 |
| `TRIBAL_ENTITY` | 6 | $1,288,195,720 |
| `NON_NATIVE_OWNER_NAMED` | 1 | $280,656,480 |

**`UNDETERMINED` means nobody said, not that the firm is not Native-owned.** No row in this table says `NOT_NATIVE` and none ever will.

### Guards

* `name_trap_warning` fires on **41** rows.
* `temporal_caveat` is populated on **100%** of rows — structural, see §5.
* `privacy_class`: `CORPORATE_FORM_PRESENT` 307, `POSSIBLE_PERSONAL_NAME` 15, `NO_CORPORATE_FORM` 13. **15** rows are `publishable_entity_name = N`.

### Sent to review

**164 rows** in `review/individual_native_ownership_ambiguous_2026-08-26.csv`, each carrying its evidence, its URL and its tier basis.

| reason | n |
|---|---:|
| MISSING ENTITY ATTRIBUTION | 67 |
| site unreachable - retry, not a finding | 37 |
| native-sounding name (trap_token | 24 |
| claims Native ownership without saying individual or tribal, | 22 |
| the only 'third party' found is a SAM mirror or a company pr | 14 |
| a source names a NON-Native owner against a federal native f | 1 |

---

## 10. WHAT IS NOT DONE

1. **The codebook fragment is not registered in
   `data/clean/codebook_master.csv`.** Registration belongs to
   `41_build_codebooks.py`, which is a global rebuild and is **unsafe to run
   today — it would delete 21 of the 43 blocks the master now holds**, because
   several fragments postdate its dataset map. Recorded rather than worked
   around, per the precedent set by `156_refresh_deals_codebook_fragment.py`.
2. **`62_no_regression_check.py` is clean.** It reported
   `codebook_undocumented_public = 45` mid-build — all 45 in
   `07o_nigc_declinations`, another agent's fragment, not touched here — and
   that agent had fixed it by the final run. **Final state: no regressions.**
   Nothing in this build writes to the ledger, the spine or
   `codebook_master.csv`, so it cannot regress them.
3. **The two `INDIVIDUAL_NATIVE_OWNED` SAM variants** — see §7. Re-run `171`.
4. **`SITE_UNREACHABLE` rows are retryable and should be retried**, ideally
   through a real browser. Several are TLS or connection failures rather than
   HTTP statuses, which `WebFetch` handles poorly and a browser handles fine.
5. **The 2,550-firm tail.** The candidate set is the flagged subset of the
   **top 400** unattributed awardees. Across the whole file 2,550 unattributed
   awardees carry a native flag, holding $19.52B. The top-400 cut is a priority
   order, not the universe.
6. **The ten dated ownership-change events in §5b are not yet deal rows.**
   Each has a date and most have a source URL sitting in the table already.
   They are the exact input the ownership-change ledger wants.
7. **No entity class was created and no ledger row was written.** This build
   asserts nothing into the spine or the identifier ledger. Promoting a
   verified firm into a `individually Native-owned business` entity class is a
   separate decision, and AGENTS.md already fixes its rules:
   `parent_native_entity` stays NULL, it never rolls up to a tribe, ANC or NHO,
   and no tribal total changes.
