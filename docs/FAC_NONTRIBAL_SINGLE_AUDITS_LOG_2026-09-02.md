# FAC — the Single Audits `entity_type = tribal` cannot see

*Built 2026-09-02 by `code/1132_fac_nontribal_native_audits.py`
(`report | fetch | apply | codebook | verify | selftest`). Companion to
`docs/GAMING_FINANCIAL_EXHAUST_BUILD_LOG.md`, which covers
`code/147_build_fac_single_audits.py` and `fac_tribal_single_audits.csv`.
Every figure here is re-derivable with `apply`; `docs/fac_nontribal_native_audits.json`
is the machine-readable copy.*

---

## THE DEFECT: CEDAR WAS ASKING THE CLEARINGHOUSE THE WRONG QUESTION

`147` discovers Single Audits with

```
api.fac.gov/general?entity_type=eq.tribal
```

plus three `auditee_name ilike` nets for gaming. Measured on the live table:

| | |
|---|---:|
| `fac_tribal_single_audits.csv` rows | 6,780 |
| …arriving on the `entity_type_tribal` net | **6,774** |
| distinct spine entities it reaches | **638** of 1,555 |
| spine entities it does **not** reach | **917** |

The 917 are not a random remainder. By `entity_class`:

| class | missed |
|---|---:|
| Native Hawaiian Organization | 210 |
| Alaska Native Village Corporation | 152 |
| Federally recognized Alaska Native Village | 115 |
| BIE School | 114 |
| State-recognized tribe | 63 |
| Native Community Development Financial Institution | 55 |
| Individually Native-owned business | 45 |
| Intertribal Organization | 37 |
| Native Financial Institution | 29 |
| Urban Indian Organization | 28 |
| Federal-level self-governance consortium | 22 |
| Federally recognized tribe | 19 |
| *(4 smaller classes)* | 28 |

**An NHO does not file a Single Audit as a tribe.** `entity_type` is the
auditee's own self-typing on the SF-SAC, and its vocabulary is
tribal / non-profit / local / higher-ed / state / unknown. A Native Hawaiian
501(c)(3) files as `non-profit`; a BIE-funded school as `local` or
`higher-ed`; a Native CDFI as `non-profit`. **The filter is a statement about
the FILER'S FORM and Cedar was reading it as a statement about WHO THE FILER
IS.** Measured on the rows this pass recovered, their FAC `entity_type` is
`non-profit` 496, `local` 28, `higher-ed` 18, `unknown` 2, `tribal` 1.

---

## WHAT THE SECOND QUESTION RETURNED

545 further Single Audit filings, audit years **2016–2025**, on **99 entities
Cedar could not previously reach**, carrying **$9,779,055,684** of audited
federal expenditures, plus **7,252 SEFA lines across 506 distinct ALNs**.

Filings by the entity's Cedar class:

| class | filings | entities |
|---|---:|---:|
| Urban Indian Organization | 164 | 22 |
| Intertribal Organization | 91 | 14 |
| Native Hawaiian Organization | 83 | 15 |
| Federal-level self-governance consortium | 81 | 17 |
| Native Community Development Financial Institution | 60 | 13 |
| Federally recognized Alaska Native Village | 24 | 8 |
| Tribal College or University | 18 | 2 |
| Federally recognized tribe | 11 | 2 |
| State-recognized tribe | 9 | 3 |
| BIE School | 2 | 1 |
| Native Financial Institution | 1 | 1 |
| Federal-level constituency entity | 1 | 1 |

*Filings sum to 545; entities sum to 99. They are different units and the
first draft of this table quoted the filing count under both headings, which
is `AGENT_FIELD_GUIDE` §3 in miniature — re-derived from the live file.*

The largest programmes in the SEFA:

| ALN | programme | expended |
|---|---|---:|
| 93.210 | Tribal Self-Governance Program: IHS Compacts | $4,709,719,998 |
| 10.766 | Community Facilities Loans and Grants | $626,465,468 |
| 93.193 | Urban Indian Health Services | $341,830,355 |
| 93.224 | Consolidated Health Centers | $212,041,680 |
| 93.558 | Temporary Assistance for Needy Families | $174,465,548 |
| 21.023 | Emergency Rental Assistance Program | $161,190,241 |

**A conservation identity, not a coincidence.** The SEFA lines sum to
`$9,779,055,684.00` and the census `total_amount_expended` sums to
`$9,779,055,684.00` — to the cent, from two separately fetched tables. A SEFA
IS the decomposition of the audited total, so the two agree by construction,
and **that is exactly why they may never be summed together**. The fence is in
`512` as `GRAIN_FAC_NONTRIBAL`.

**A finding, not a defect: all 545 filings are PUBLIC.** `is_public = t` on
every one in the export. 147's tribal-typed set is 30.2% public, because the
2 CFR 200.512(b)(2) withholding election is a right of *an Indian tribe or
tribal organization* — and these auditees are NHOs, urban Indian
organizations, CDFIs and colleges, which do not have it. So for this half of
Indian Country the **reporting-package PDFs are all downloadable**, which the
tribal half largely is not.

---

## WHY THIS IS A SECOND TABLE AND NOT A WIDER 147

`147 --all` is a **full rebuild** of `fac_tribal_single_audits.csv`. An
in-place append into it is reverted by the next run while printing a larger
row count — the FERC rebuild/in-place collision in `START_HERE.md`, four times
over. And a file named `tribal` may not hold 83 Native Hawaiian filings;
loading them into it would be a correctness defect wearing the costume of
coverage.

**The two tables are DISJOINT ON `report_id`**, asserted by invariant **V4**,
which a fixture proves fires. A row is 147's or it is 1132's, never both, so a
consumer may UNION them without double-counting a dollar. A companion block at
the top of `147` says so from the other side, and says what to do if 147's
discovery is ever widened. Model decision: **ADR-033**.

---

## THE ROUTE, AND WHY IT IS NOT THE API

Measured **2026-09-02T17:52Z**, every path on `api.fac.gov` answered

```
HTTP 404  "Requested route ('fac-production-postgrest.app.cloud.gov')
           does not exist."          X-Ratelimit-Remaining: 997
```

The api.data.gov gateway accepted the key (the rate-limit header proves it) and
the FAC's own PostgREST backend was not routed. `www.fac.gov` carried a banner
naming the cause: *"FAC.gov will be undergoing maintenance on Wednesday,
September 2, 2026, between 9:00 AM and 4:00 PM EDT."* This is `START_HERE`
rule 3 in a second vocabulary — **a 404 is a state of the host, never evidence
that the path is wrong, and never evidence about the key.**

The route used instead is the FAC's **own published bulk export**, linked from
`https://www.fac.gov/data/download/current/`:

| object | bytes | used |
|---|---:|---|
| `general.csv` | 269,814,315 | stored, 413,762 records scanned |
| `additional_eins.csv` | 4,759,398 | stored, refusal only |
| `additional_ueis.csv` | 1,810,770 | stored, refusal only |
| `federal_awards.csv` | 1,336,897,672 | **streamed and filtered in flight**, never stored |

Four GETs, ≥3 s apart, one host lock (`logs/_HOSTLOCK_app.fac.gov.json`),
checksums and byte counts in `data/raw/fac/bulk/_manifest.json`. The
alternative was ~540 paginated API calls to reconstruct locally what one
request returns, so the bulk route is also the politer one. FAC documents these
files for exactly this use on that page ("Using the data files in code … import
pandas") and states they carry the same columns as the API tables.

**The robots observation, recorded rather than skipped.** `www.fac.gov` is
`User-agent: * / Disallow:` — nothing disallowed. The files themselves are
served from `app.fac.gov`, whose `robots.txt` is `Disallow: /`; that directive
covers the interactive Django application (audit search, submission,
Login.gov), none of which this build touches. It fetches only the four static
export objects `www.fac.gov` publishes, one request each, no crawling and no
search. **Nothing refused anything: every fetch returned 200 or 206.** If any
of them ever returns 403, stop — do not re-route to the search UI.

**PII.** `general.csv` carries `auditee_email`, `auditee_phone`,
`auditee_contact_name`, `auditee_certify_name`, the auditor equivalents and
street address lines. None is written to any output, and invariant **V8**
exits 1 if one appears in a header.

---

## THE DEFECT THIS BUILD FOUND IN ITSELF, AND WHY IT IS IN THIS LOG

The **first** `apply` matched **1,126 filings on 133 entities and
$243,319,063,298**. Every summary count looked like a triumph. The top of the
table by dollars did not:

```
$29.64B  COMMONWEALTH OF VIRGINIA    -> Pribilof Islands
$14.95B  STATE OF OKLAHOMA           -> Security State Bank of Oklahoma
$ 1.13B  SAN BERNARDINO COUNTY       -> Riverside-San Bernardino County
                                        Indian Health, Inc.
$ 0.33B  ALASKA NATIVE TRIBAL HEALTH -> Southeast Alaska Regional Health
         CONSORTIUM                     Consortium
$ 0.11B  The City of Oklahoma City   -> Oklahoma City Indian Clinic
```

Three separate causes, three structural fixes. **None of them is a threshold**,
because every one of these shares two or three tokens and a token-count guard
stopped none of them.

**1. `resolve_entity`'s CONTAINMENT leg may not key a dollar.** Containment
accepts a match when one distinctive-token core is a *subset* of the other, so
`{state, oklahoma}` ⊂ `{security, state, bank, oklahoma}`. 210 auditee names
reached the gap this way and **every one inspected is a false positive** — the
Riverside/San Bernardino case is already in `START_HERE.md` as a refusal an
owner made **by hand**, and it came straight back through a different door.
`START_HERE` §1 already says containment *"may name an owner; it may not key a
dollar"*; this table keys dollars on every row, so only `exact`, `core` and
`alias` are accepted. Invariant **V11**.

**2. No Cedar entity is a US state.** `entity_type = state` is refused
structurally on every route. Invariant **V12**.

**3. `additional_eins` / `additional_ueis` do not bind a filing.** They say a
reporting package *covers* a component unit with that identifier; the filing's
`total_amount_expended` is still the whole auditee's. Binding on one attached
the Commonwealth of Virginia's $29.64B to a component. Only the filing's own
`auditee_ein` / `auditee_uei` may bind it; the two files are still read, but
only to CONTRADICT. Invariant **V13**.

After the three fixes: 545 filings, 99 entities, $9.78B, and the largest rows
are Yukon-Kuskokwim Health Corporation and Southcentral Foundation matching
themselves `exact`.

**Two more, both the same shape as things already written down here.**

**4. `is_public` — the export writes `t`/`f`, not `true`/`false`.** The first
corrected build tested `in ("true","1","yes","y")` and recorded
`is_public = 0` on **all 545 rows** — every filing marked withheld under
2 CFR 200.512(b)(2) when none of them is. Identical in shape to
`AMERICANTRIBAL GOVERNMENT` in `START_HERE.md`, where one missing space drops
7,160 rows from an exact filter.

**5. And the invariant written to catch #4 fired on a CORRECT table.** Its
first draft said *"`is_public` must not be CONSTANT"*. The source really does
say `t` on all 545 — the finding above. A "must not be constant" test is
precisely this repo's signature defect: a plausible number about something
else. It was replaced with the check that actually matters — **the parsed
value must agree with the export, row by row, for the same `report_id`** — and
it emits UNMEASURED rather than clean when the export is not on disk.
Invariant **V14**.

**The general lesson, and it is not a new one.** `AGENT_FIELD_GUIDE` rule 3
says *print the denominator, the sample cap, and one worked example row*.
Nothing in the summary counts of the first run was wrong-looking. `apply` now
prints **the twelve largest matched filings** on every run, because that one
table is what made all of this visible, and no aggregate would have.

---

## TIER DISCIPLINE

`START_HERE` §1: a tier is **inherited from the source row, never assigned by
the consumer**. 821 of the ledger's 1,104 EIN rows are tier B via `need_v6`
(6.5% accurate), so an exact EIN hit says nothing about whether the *link* is
right.

| route | filings | tier |
|---|---:|---|
| `auditee_name` (exact / core / alias only) | 384 | A |
| `ein_exact` | 118 | inherited from the ledger / np-hub row |
| `uei_exact` | 43 | inherited |

Final distribution **A 436 · B 109 · X 0**, and every row names where its tier
came from in `entity_tier_inherited_from` (invariant **V7**). Tier X is a
NEGATIVE ruling and is refused outright as a key; 0 were present in the gap.

Refusals recorded in `review/fac_nontribal_refused_matches.csv`:

```
REFUSED_NAME_METHOD_MAY_NOT_KEY_A_DOLLAR   3,049 distinct (name, state) pairs
AMBIGUOUS_CEDAR_KEY_EIN                       15 keys reaching 2+ entities
KEYS_DISAGREE_ON_ENTITY                       15 filings
REFUSED_STATE_DISAGREEMENT                    12
REFUSED_SINGLE_TOKEN_CORE                      4
COVERED_COMPONENT_ONLY_NOT_THE_AUDITEE        (registered per filing)
```

**A NAME COLLISION FOUND IN PASSING — AND THE FIRST DRAFT OF THIS PARAGRAPH
WAS WRONG, WHICH IS WHY IT IS STILL HERE.** *Alaska Native Tribal Health
Consortium* containment-matched to *Southeast Alaska Regional Health
Consortium*, $333.6M in one audit, and was refused. This log first recorded
that as evidence ANTHC is missing from the spine and called it the cheapest
register addition of the pass. **It is not missing.** It is
`ITO-LSKHLT-00`, and `147` already holds **10 of its filings at tier A**,
FY2016–2025.

The reason it looked absent is structural and is an argument *for* the
containment refusal, not a fault in it. `1132`'s resolver is deliberately
handed **only the 917 entities 147 does not reach**, so a filing whose true
match is one of the 638 has no correct answer available — containment can then
only ever find a *wrong* entity inside the gap. Every name in the FAC corpus
that belongs to an already-covered entity is in exactly that position, which is
part of why 210 containment hits produced no true positive on inspection.

The general form, and it is worth carrying: **a matcher restricted to a
residual population will report a false match rather than no match, and the
absence it seems to prove is an artefact of the restriction.** Before reading a
refusal here as a spine gap, check the full spine — `147`'s table included.

---

## WHAT DID NOT HAPPEN

* Nothing was written to `fac_tribal_single_audits.csv`, to the spine, to
  `cedar_identifier_ledger.csv` or to any ledger. Zero Cedar ids minted.
* No PDF was fetched. This build reads structured data only.
* The historic (pre-2016, Census-era) FAC download at
  `www.fac.gov/data/download/historic/` was **not** touched. It is a real,
  measured next step and it is `NOT_ACQUIRED`, not absent.

## THE GATE

```
py -3 code/1132_fac_nontribal_native_audits.py verify     -> exit 0, 14 invariants
py -3 code/1132_fac_nontribal_native_audits.py selftest   -> 9/9 fixtures FIRE
```

`verify` FAILS when the work did not land, not merely when something broke:
floors on filings (500) and entities (90) that the *first, defective* run's
floors (700/150) correctly turned red against when the containment refusal cut
the table to its honest size. The floors below were then re-derived from a
measured green run rather than from an expectation.
