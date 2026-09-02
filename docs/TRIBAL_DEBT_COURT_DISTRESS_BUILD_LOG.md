# Tribal debt distress, from the court record

*Built 2026-09-02 by `code/1110_tribal_debt_court_distress.py`. Third document in
the tribal-debt set, and the one that opens the DISTRESS channel:*

* `docs/TRIBAL_DEBT_BUILD_LOG.md` (2026-08-05) — the ISSUER UNIVERSE (Moody's, EMMA)
* `docs/TRIBAL_DEBT_HOLDINGS_BUILD_LOG.md` (2026-09-02) — WHO HOLDS THE PAPER (Form N-PORT)
* **this log** — WHAT REACHED A COURT

*None supersedes another.*

**Do not commit.** Everything is staged in `data/staging/` and `review/`. Nothing
in `data/clean/` was touched.

---

## The question this had to answer, and why the last channel could not

`1082` measured **zero distress flags across 1,585 fund-holding observations**
and diagnosed the reason exactly right: **the channel is younger than the
distress.** Form N-PORT begins in 2019; Lake of the Torches was decided in 2011,
Chukchansi's noteholder litigation ran 2013–2014, Mashantucket's restructuring
closed in 2013.

So the record is in the courts, and `COURTLISTENER_API_TOKEN` is the route.

### CORRECTION — the token had been used, five days earlier

The mandate for this pass said the token "has never been used." **It has.**
`code/366_courtlistener_ownership_adjudication.py` spent **112 requests on
2026-08-27** (92 × HTTP 200, 18 × 500, 2 × 429), logged in
`data/raw/external/courtlistener_2026-08-26/_request_ledger.json`, and left 76
cached response objects on disk.

This matters operationally, not just for the record: **the rate limit is per
TOKEN, not per script.** 5/min, 50/hr, 125/day. Two scripts each keeping a
private ledger would each believe it had 125 and the second would collect
429s. **`1110` therefore appends to `366`'s ledger** rather than opening its
own, and `spend` reports the shared total with the 1110 slice named.

---

## What was built

| output | rows | grain |
|---|---:|---|
| `data/staging/tribal_debt_court_events.csv` | **32** | ONE EVENT TYPE in ONE COURT DOCUMENT |
| `data/staging/tribal_debt_court_dockets.csv` | **9** | ONE DOCKET in ONE COURT |
| `data/staging/tribal_debt_court_documents.csv` | **20** | one retrieved judicial opinion |
| `review/1110_targets.csv` | **62** | one query, one named question |
| `review/1110_search_hits.csv` | **703** | every result the API returned |
| `review/1110_rejected_hits.csv` | **288** | every opinion refused, with the reason |
| `review/1110_rejected_dockets.csv` | **348** | every docket refused, with the reason |
| `review/1110_rejected_events.csv` | 6 | events refused for naming no instrument |
| `review/1110_person_screen_held.csv` | **3** | held by the natural-person screen |
| `review/1110_unreached_cases.csv` | **15** | questions the corpus could not answer |
| `review/1110_fetch_manifest.csv` | **86** | every request made |
| `data/raw/external/tribal_debt_court_1110/*.json.gz` | **83** | the cache; every figure re-readable |

Stages: `targets` → `probe` → `search` → `opinions` → `remine` → `build` →
`verify` → `selftest` → `spend`.

**87 requests, all HTTP 200, zero refusals**, inside a shared 125/day budget.
`remine` re-derives every hit row from the cache with **zero** requests.

---

## THE CONSTRAINT THAT SHAPED EVERY COLUMN

**A tribal default is not a corporate default**, and the leading case is the
proof rather than the exception.

> *"The district court held that the indenture was void because it was a gaming
> facility management contract unapproved by the National Indian Gaming
> Commission."*
>
> — Wells Fargo Bank, National Ass'n v. Lake of the Torches Economic Development
> Corp., **658 F.3d 684** (7th Cir. 2011), No. 10-2069

A naive reader records that as *the tribe did not pay its bondholders*. The
court found the **contract void**. And four years later, on the same paper:

> *"Because we conclude that the Tribal and Bond Resolutions were not void as
> unapproved management contracts, we need not address Saybrook's alternative
> contention that the voiding regulation, 25 C.F.R. …"*
>
> — Stifel, Nicholaus & Co. v. Lac Du Flambeau Band, **807 F.3d 184**
> (7th Cir. 2015), Nos. 14-2150, 14-2287

**Two findings, opposite directions, same instrument, four years apart.** Any
schema that flattens these into `is_default = Y` is not simplifying, it is
lying. Hence:

| column | what it stops |
|---|---|
| `event_type` + `event_type_basis` | typing by vibe. The basis records **the exact phrase that fired**; no phrase → `UNTYPED_NEEDS_HUMAN`, and no row is written |
| `assertion_or_finding` (+ basis) | reading a complaint as a judgment. `ALLEGATION_BY_A_PARTY` / `COURT_FINDING` / `PROCEDURAL_RECORD`, decided by cue words in the quoted sentence itself |
| `as_of_date` + `currency_caution` | an event read as a running condition. Every row is dated and every row says so in words |
| `sovereign_immunity_caution` | characterising a nation's finances. On every row, in full |
| `instrument_as_described` + `verbatim_quote` | a characterisation with no instrument behind it. **Every word in `instrument_as_described` must appear in the row's own quote** — invariant I9 |
| `tribal_party_role` (dockets) | reading `Picayune Rancheria v. Goldenwise Capital Management` as distress. It is the nation **suing** |
| `court_disagreement` | silently picking a court when the source gives two |

### The instrument guard, and the six rows it refused

An event stages **only** if the passage that fired names an instrument. Where
the matching sentence did not, the window widens to three sentences once; if it
still names none, the event is written to `review/1110_rejected_events.csv`
with the reason and never staged. **Six were refused this way.**

The rule is the mandate's own: *quote the instrument and the court*. An event we
cannot quote an instrument for is a characterisation, not a record.

---

## What was found

### 32 events, by type

| event type | rows |
|---|---:|
| `LITIGATION_OUTCOME_INSTRUMENT_HELD_VOID_OR_UNENFORCEABLE` | 10 |
| `LITIGATION_OUTCOME_SOVEREIGN_IMMUNITY_BARS_THE_CLAIM` | 7 |
| `RECEIVERSHIP` | 5 |
| `RESTRUCTURING_OR_EXCHANGE` | 5 |
| `DEFAULT_ASSERTED_OR_FOUND` | 3 |
| `LITIGATION_OUTCOME_WAIVER_OF_IMMUNITY_ENFORCED` | 1 |
| `FORBEARANCE` | 1 |

**The largest single category is an instrument held UNENFORCEABLE, not a
default.** That is the substantive finding of this build and it is the opposite
of what a "tribal debt distress" table would be assumed to contain.

### by year — and there is no row after 2017

| year | rows |
|---|---:|
| 2010 | 4 |
| 2011 | 9 |
| 2013 | 11 |
| 2015 | 4 |
| 2017 | 4 |

**This is the exact complement of `1082`.** N-PORT starts 2019 and found
nothing; the opinion record ends 2017 and found everything. The two channels
do not overlap by a single year, and neither one alone would have shown that.

### by speaker

| | rows |
|---|---:|
| `PROCEDURAL_RECORD` | 27 |
| `ALLEGATION_BY_A_PARTY` | 3 |
| `COURT_FINDING` | 2 |

**Only two rows in the whole table are a court holding something.** That is the
honest reading and it is why the column exists. The other 30 are the record
reciting what happened or a party asserting it, and a consumer must not quote
them as findings.

### Obligors resolved — 9 distinct Cedar entities

**Events (5 entities, 32 rows)**

| entity | rows | joins 1082 |
|---|---:|---|
| Lac du Flambeau | 15 | no |
| Nooksack | 6 | no |
| Sokaogon Chippewa Community | 6 | no |
| Shingle Springs | 4 | no |
| Rosebud | 1 | no |

**Dockets (7 entities, 9 rows)** — the docket table is where the mandate's
"court and docket number" actually lives.

| entity | court | docket | filed | tribal role | joins 1082 |
|---|---|---|---|---|---|
| Dry Creek | N.D. Cal. | 3:01-cv-04125 | 2001-11-05 | **defendant** | **yes** (22 obs) |
| Lac du Flambeau | W.D. Wis. | 3:09-cv-00768 | 2009-12-21 | both/unclear | no |
| Sokaogon Chippewa Community | E.D. Wis. | 1:10-cv-01039 | 2010-11-19 | **defendant** | no |
| Lac du Flambeau | W.D. Wis. | 3:12-cv-00255 | 2012-04-09 | both/unclear | no |
| Cabazon | C.D. Cal. | 5:12-cv-01278 | 2012-08-01 | **defendant** | **yes** (5 obs) |
| Lac du Flambeau | W.D. Wis. | 3:13-cv-00372 | 2013-05-24 | **defendant** | no |
| Picayune Rancheria | E.D. Cal. | 1:14-cv-01044 | 2014-07-02 | **defendant** | no |
| Picayune Rancheria | E.D. Cal. | 1:20-cv-00183 | 2020-02-04 | plaintiff | no |
| Mashantucket Pequot | D.R.I. | 1:21-cv-00177 | 2021-04-20 | **defendant** | **yes** (8 obs) |

### The join to `1082` — 3 of 14 obligors

**Three of `1082`'s fourteen obligors are reached by a court record**: Cabazon
Band of Mission Indians, Mashantucket (Western) Pequot Tribe, and River Rock
Entertainment Authority (as Dry Creek Rancheria). The join runs on
`obligor_cedar_uid` against `data/staging/tribal_debt_obligors.csv`, **not** on
the obligor label — a label is what a fund's schedule of investments happened to
print and a court caption will never match it. `joins_1082_basis` says so on
every row.

**Zero EVENT rows join `1082`.** Every entity with a staged event —
Lac du Flambeau, Nooksack, Shingle Springs, Rosebud — is absent from the
holdings register, and every entity in the holdings register with a court record
has a DOCKET rather than an opinion. **The two datasets touch at three
entities and at no single row.** That is the finding, not a gap: the nations
whose paper a registered fund still holds are largely not the nations whose
paper produced a published opinion.

### Five entities NEW to the tribal-debt workstream

Lac du Flambeau, Nooksack, Sokaogon Chippewa Community, Shingle Springs and
Rosebud appear in no
tribal-debt table before this build. Three arrived through **doctrine queries**
rather than name queries — see below.

---

## The cases we could not reach, named

`review/1110_unreached_cases.csv` holds 15 questions with an explicit state.
The important ones:

| case sought | result | state |
|---|---|---|
| **Mashantucket / Foxwoods ~$2.3B restructuring** | no opinion; ONE docket (`U.S. Bank v. Mashantucket Pequot Gaming Enterprise`, D.R.I. 1:21-cv-00177, 2021) | `SOURCE_DOES_NOT_PUBLISH` — the 2009–2013 restructuring was an out-of-court workout. There is no opinion because there was no litigated outcome |
| **Mohegan Tribal Gaming Authority** | 184 opinions, **zero debt** | every hit is a tort or employment matter from the Mohegan Gaming Disputes Court. `Mohegan Tribal Finance Authority`: **NO_RESULT** |
| **Chukchansi noteholder litigation** | the NY **appellate** order only (118 A.D.3d 550) | the trial-level Wells Fargo action is in NY Supreme Court, **outside CourtListener's opinion corpus**. The appellate order decides a preliminary-injunction appeal inside an internal tribal leadership dispute and recites no instrument, so it stages **no event** |
| **Chukchansi receivership** | not reached | the receivership was in **Madera County Superior Court**, a state trial court CourtListener does not index |
| **Santa Ysabel** | 44 opinions, **zero debt** | `Santa Ysabel Resort and Casino`: **NO_RESULT**. Everything returned is the online-bingo/UIGEA line of cases (`California v. Iipay Nation`), which is regulatory, not debt |
| **Inn of the Mountain Gods** | 19 opinions, **zero debt** | the 2009–10 senior-note default produced no published opinion. Hits are torts and a 1981 Court of Claims land matter |
| **River Rock Entertainment Authority** | **NO_RESULT** on opinions; one docket via `Sonoma Falls Developers, LLC v. Dry Creek Rancheria` | the 2011 note exchange was consensual |
| **Catawba Nation Gaming Authority**, **PCI Gaming Authority**, **Downstream Development Authority**, **East Valley Tourist Development Authority** | no debt matter | three are `NO_RESULT` outright |

**The pattern is worth stating plainly: most tribal debt distress never reaches
a published federal opinion.** It is worked out consensually, or litigated in
state trial courts and tribal courts that no free corpus indexes. A table built
from published opinions will therefore always understate it, and this one does.

---

## Eight defects committed and caught, all of one shape

`docs/AGENT_FIELD_GUIDE.md` §3 names this repo's signature defect: *a check that
does not measure its own name.* Four of the six are instances of it, and **not one of those four was found by
a check** — all four were found by reading the output table end to end, which
is field-guide habit 3. The remaining two were found by the standing gates, and
those two are the worst of the set.

### 1. The obligor was read off the QUERY, not off the DOCUMENT

The first `build` produced this row:

```
Outsource Services Management, LLC v. Nooksack Business Corp.
    obligor = Lac du Flambeau Band of Lake Superior Chippewa Indians
```

and the same for `Colombe v. Rosebud Sioux Tribe`. **CourtListener searches full
text**, so the query `"Lac du Flambeau Band of Lake Superior Chippewa Indians"`
returns every opinion that *cites* the Lake of the Torches decisions. The build
then inherited the obligor from the target row that had found the document.

**Nooksack's loan and Rosebud's were attributed to Lac du Flambeau.** The
shortlist already enforced *a search hit is not a party* (code/219,
`Seminole v. Berkebile`); the build did not. Fixed: the obligor is resolved from
the **caption** and, for dockets, from the **clerk's party array**, and the
target's obligor is used only when it is itself named in the caption.

### 2. The debt filter measured where an opinion STARTS

The first shortlist required debt vocabulary in the caption or the snippet, and
rejected

```
Wells Fargo Bank, N.A. v. Chukchansi Economic Development Authority
    reason: no debt vocabulary in caption or snippet
```

— the single most important Chukchansi document in the corpus. A snippet is the
first ~600 characters of a document, not a summary of it, and that one opens on
a procedural sentence. Fixed with two more routes: **a financial institution
named in the caption**, and for doctrine queries the fact that **the engine
matched the debt terms in the full document text**, which is a stronger
statement than any snippet can make.

The same filter had rejected `Sharp Image Gaming v. Shingle Springs Band`,
`Outsource Services Management v. Nooksack Business Corp` and
`Stifel, Nicolaus & Co. v. Lac du Flambeau` — **three of the five most
substantive cases in the final table.**

### 3. First-wins de-duplication dropped a real case

One opinion is returned by several queries, and `setdefault` kept whichever
arrived first. `Saybrook Tax Exempt Investors, LLC v. Lake of Torches Economic
Development Corporation` was therefore attached to the Lac du Flambeau
full-text query, failed the caption test, and vanished. Fixed by preferring the
hit **whose query is actually in the caption**.

### 4. `suitNature` (and `cause`) measure a civil cover sheet, not a loan

Tried as a third debt signal for dockets and **refused after measurement**. It
admitted six dockets coded `Contract: Other`:

`State of Wisconsin v. Ho-Chunk Nation` · `State of California v. Paskenta Band
of Nomlaki Indians` · `California Valley Miwok Tribe v. California Gambling
Control Commission` · three `… v. Iipay Nation of Santa Ysabel` dockets

— every one a compact or regulatory dispute with **no lender, no instrument and
no debt**. The `cause` field was tested separately and produces the same class
(`28:1332 Diversity-Contract Dispute` on an **insurance** case). Both routes are
refused, with the reason recorded inline in the code so they are not re-added.

### 5. A POSITIONAL PRIMARY KEY, and it silently unasked two questions

**Found by `py -3 code/293_lint_bug_classes.py` class 7**, after the table had
already been written twice and read twice by a human who did not see it.

`target_id` was `f"T{i:02d}_{stype}"` — the index of the case in a Python list.
Adding the round-two targets shifted every index after the doctrine block, so
`T16_o`, which in round one was the **CONTROL** query
(`Kwithluk Sentinel Indenture Trustee Holdings`, built to return nothing), became
`Lake of the Torches Economic Development Corporation` in round two. The resume
check saw `T16_o` already present in the hits file, **never asked the new
question**, and `remine` then attributed the control's zero-result response to
it. The same happened to `Mashantucket Pequot Gaming Enterprise`.

**Two real questions were published in `review/1110_unreached_cases.csv` as
`NO_RESULT` having never been asked.** That is field-guide habit 4 exactly — an
absence of evidence printing as evidence of absence — and the absence in
question was about *Foxwoods*, the largest case in the mandate.

Confirmed against the request ledger, which records the URL of every request
and therefore what each id actually asked:

```
MISMATCH  T16_o | target: Lake of the Torches Economic Development Corporation
                | ledger: Kwithluk Sentinel Indenture Trustee Holdings
MISMATCH  T30_o | target: Mashantucket Pequot Gaming Enterprise
                | ledger: Kwithluk Sentinel Indenture Trustee Holdings
```

Fixed: `target_id()` is now a slug of the **question**, so it cannot move. The
58 cached responses were renamed from the ledger's own mapping — the ledger is
the only authority for which id asked what, because the cached file does not
carry its query. The four superseded duplicates are in
`data/raw/external/tribal_debt_court_1110/_superseded_positional_ids/` with a
README; nothing was deleted. The four unasked questions were then asked, and
both recovered ones returned results.

**`Lake of the Torches Economic Development Corporation` alone returned 7
opinions and 9 dockets**, including `Godfrey & Kahn v. Lac Du Flambeau Band`
(7th Cir. 14-2287) which no other query reached.

### 6. A filename sanitiser that disagreed with the key it was sanitising

Immediately downstream of the fix above. `cache_path()` collapsed
`[^A-Za-z0-9]+` to a single `_`, so the new id `..._{}_o` was written to disk as
`..._o`, and `remine` — which parses the id back out of the filename — could not
find four responses **that were sitting on disk**. Fixed by keeping `_` in the
character class. The lesson generalises: a sanitiser and the key it sanitises
have to agree on the alphabet, or a round trip through a filename is lossy in a
way nothing reports.

---

## The natural-person discipline

**No party-person table is emitted anywhere in this build.** Beyond that, four
screens, applied before a request is spent where possible:

1. **Caption shape** — `per capita`, `disenroll`, `wrongful death`, `estate of`,
   `habeas`, and the rest. Rejected at shortlist so it does not cost a request.
2. **The debtor side.** `Mashantucket Pequot Gaming Enterprise v. Renzulli` is a
   tribal enterprise collecting from a **patron**. The debt is a private
   individual's, the obligor is not a nation, and the row belongs in neither
   direction of this table. A person on the **claimant** side (a contractor
   suing a nation, `Becker v. Ute Indian Tribe`) is a counterparty in a public
   commercial case and stays, flagged in `caption_names_a_natural_person`.
   **4 documents held**, in `review/1110_person_screen_held.csv`.
3. **Any natural person in a docket's party array drops the docket.** The Lake
   of the Torches query alone returned four consumer payday-lending dockets —
   `Morgan v. West Side Lending`, `KNOTTS v. CRANE LENDING`,
   `RANSOM v. GREATPLAINS FINANCE`, `Mee v. Clarity Services` — in which a
   tribal lender is the **creditor** and the borrower is a private individual.
4. **`Lac du Flambeau Band v. Coughlin`, 599 U.S. 382 (2023)** was retrieved and
   **held by screen 2**. It is a payday-loan case in which the Band is the
   lender and Coughlin an individual debtor; the holding is about the
   Bankruptcy Code abrogating tribal immunity, not about tribal debt distress.
   Correctly out, and worth naming because it is the case a keyword sweep would
   most likely have published by mistake.

### 7. The natural-person screen called a TRIBE a person, and lost a real case

`side_is_a_natural_person` treats a caption side with no organisational marker
and at most three tokens as a person. Its marker list had no `community` in it,
so

```
Wells Fargo Bank, N.A. v. Sokaogon Chippewa Community
```

— a Wells Fargo tribal **bond** action, the Mole Lake sibling of Lake of the
Torches — read as a bank suing a three-word individual and was **held out of
the table entirely**. Erring safe is still erring: the screen exists to protect
private individuals and it removed a nation.

Fixed twice over: `community`, `council`, `committee`, `agency`, `district` and
`office of` added to the organisational markers, and — the durable half — **the
tribal test now runs inside the person test**, because a tribal entity is never
a natural person. That is the same word-boundary tribal test used everywhere
else here, rather than a second list to drift.

**Recovered: 6 events, 1 docket, and a ninth Cedar entity.**

### 8. An amicus is not a counterparty

The docket debt test asked whether a financial institution was **anywhere** in
the party array. That admitted

```
Blue Lake Rancheria, et al. v. Kalshi, Inc., et al.   62 parties
Mescalero Apache Tribe v. Kalshi, Inc.                43 parties
```

— the sports prediction-market coalition cases, nothing whatever to do with
debt — on the strength of the **Native American Finance Officers Association**
appearing among the amici. A 10-party construction payment dispute came in the
same way, on `Credit Provider Group LLC`.

Fixed with a threshold that was **measured rather than asserted**: the nine
genuine debt dockets in this corpus carry **2–6 parties**; the three false
positives carry **10, 43 and 62**. A financial name now counts only if it is
**in the caption**, where an adverse party is, or if the docket is a two-sided
commercial case. All nine real dockets survive; all three false positives are
refused with the reason written on the row.

---

## Terms

**A court docket is the COURT's record, not the tribe's.**
`docs/PUBLICATION_POLICY.md` `TERMS-SCOPE`: *"The distinction is authorship, not
subject matter."* No tribal source's terms of use reach a filed case, and the
eight hard-listed sources are unaffected by this build — none of them is a
publisher of anything used here.

**EMMA was not touched, and no route around it was attempted.** Its terms bar
the output *"either commercially or free of charge"*, name *"or any manual
process"*, and CUSIP Global Services is a second licensor requiring its own fee.
Queued as **TD-1** in `review/OWNER_DECISION_QUEUE.md`, recommending we ask.

**CourtListener.** `docs/BLOCKED_SOURCE_BYPASS_2026-08-26.md` records the site as
`ROBOTS_FORBIDDEN` for SCRAPING — `Disallow: /`, naming `ClaudeBot`. That still
stands and **this script never touches the HTML site.** The REST API is the
sanctioned route, the owner supplied the token, and every request carries a
declared User-Agent with a contact address. The token is read from the
environment / `.env.local` / HKCU, is never written to a file or a log, and
`redact()` is applied to every string that leaves the process.

---

## The gates

```
py -3 code/1110_tribal_debt_court_distress.py verify     # exit 1 on breach
py -3 code/1110_tribal_debt_court_distress.py selftest   # proves every one fires
```

**Sixteen invariants — ten on events, six on dockets — and `selftest` proves
every one of them fires on its own synthetic violation**, then restores both
tables byte-for-byte and re-asserts green.

```
I1_every_event_names_a_court_and_a_source_url                             FIRES
I2_every_event_is_dated                                                   FIRES
I3_event_type_is_never_guessed_the_phrase_that_fired_is_recorded          FIRES
I4_every_event_declares_assertion_or_finding                              FIRES
I5_every_event_carries_the_sovereign_immunity_and_currency_cautions       FIRES
I6_no_event_asserts_a_summable_total                                      FIRES
I7_every_event_carries_a_verbatim_quote_present_in_the_cached_document    FIRES
I8_no_event_row_survives_the_natural_person_screen                        FIRES
I9_every_event_quotes_an_instrument_that_appears_in_its_own_quote         FIRES
I10_entity_tier_is_blank_when_there_is_no_entity_link                     FIRES
D1_every_docket_names_a_court_a_docket_number_and_a_source_url            FIRES
D2_every_docket_is_dated                                                  FIRES
D3_no_docket_names_a_natural_person_among_its_parties                     FIRES
D4_every_docket_carries_the_sovereign_and_currency_cautions               FIRES
D5_every_docket_declares_which_side_of_the_caption_the_nation_is_on       FIRES
D6_every_docket_records_how_the_entity_was_matched                        FIRES
```

`selftest` refuses to run against an already-red baseline, and restores each
table before mutating the next so a docket mutation is never evaluated against
a still-broken events file.

**`I7` is the one worth understanding.** It re-opens the cached opinion and
asserts the quote is *in it*. A verbatim quote nobody can re-read is a
characterisation with quotation marks around it, and on this material that is
the failure that would matter.

Two smaller disciplines carried over from `1082` and `366`:

* **`_named_invariant_fired` reconstructs the exact line `verify` prints**
  rather than doing string arithmetic on an offset. That bug (a 12-character
  window missing the verdict of a 50-character invariant) reported a *working*
  check as broken in `1082`, and it is not available here.
* **`404` and `403` do not trip the circuit breaker.** They are facts about an
  object, not the host turning us away (`START_HERE.md` standing rule).
* **`293` class 4 is WAIVED with a reason, not silenced.** The `RUN_DEADLINE`
  stops the loop over targets, never one target's own retrieval: a target is
  exactly one request and carries its own retrieved-vs-reported `completeness`.
  A target the deadline never reached has no row at all, and `search` resumes
  on exactly those. `293` counts and names the waiver in its output.

### Two source properties recorded rather than repaired

1. **`court_disagreement`.** CourtListener files the district Lake of the
   Torches opinion under `wied` (E.D. Wis.) while its own RECAP docket for the
   same caption is `wiwd 3:09-cv-00768` (W.D. Wis.). **Both values are kept and
   neither is overwritten** — two sources disagreeing is a finding, and the
   column says to check before citing the court.
2. **`verbatim_quote_lost_characters`.** CourtListener's PDF extraction loses
   curly quotes to `U+FFFD` in some opinions. We do not repair it — editing a
   verbatim quote to make it read better is editing evidence. The count is
   published per row so nobody publishes a mangled quote unknowingly. **0 of 26
   rows are affected today.**

---

## Honest coverage

| denominator | reached |
|---|---:|
| ~574 nations | **9** distinct Cedar entities |
| `1082`'s 14 obligors | **3** |
| the 8 canonical cases in the mandate | **2 fully** (Lake of the Torches, Cabazon), **2 by docket only** (Mashantucket, River Rock/Dry Creek), **1 partially** (Chukchansi — appellate order and two dockets, no event), **3 not at all** (Mohegan, Santa Ysabel, Inn of the Mountain Gods) |
| distress events after 2017 | **0** |

**This is a small table and it should be reported as a small table.** Its value
is not volume. It is that the largest category in it is an instrument held
*unenforceable*, that only two rows are a court holding anything, that nothing
in it is later than 2017, and that every one of those statements is checkable
against a cached document.

---

## What to do next, ranked

1. **Decide TD-1 (EMMA).** Unchanged and still first.
2. **TD-2 — PACER.** The three most substantive matters here exist in RECAP as
   dockets with no free documents. The complaints and the indenture exhibits
   are behind PACER at $0.10/page. This is a small, priceable purchase against
   named docket numbers, and it is queued as TD-2.
3. **State trial courts.** Chukchansi's receivership (Madera County Superior)
   and the Wells Fargo trial-level action (NY Supreme, New York County) are
   both outside every free corpus. Neither is a research problem; both are
   procurement or FOIA-shaped.
4. **Re-run when the corpus grows.** `remine` re-derives everything from cache
   at zero cost, so a periodic re-`search` is cheap. The 2019+ gap in this table
   and the pre-2019 gap in `1082` are the same gap seen from two sides.
5. **The doctrine queries earned their keep and should be extended.** Three of
   the four new entities arrived through them, not through a name. The two
   round-three doctrine queries returned `NO_RESULT` because they carried too
   many terms — keep them to five or six.
