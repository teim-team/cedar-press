# Methodology — Lobbying (Dataset 4)

*Adapted 2026-08-06 from the LDA methodology Elijah supplied, with the changes
argued rather than asserted. The source methodology is good; most of what
follows sharpens it rather than replacing it.*

---

## What we keep, unchanged

**The base number.** Each filing's disclosed value: reported income plus in-house
expenses on the quarterly Senate and House LDA disclosure.

**The cleaning sequence.** Amendments applied over the originals they replace,
duplicates removed, non-standard records (registrations, terminations) set
aside before any total is struck.

> **CORRECTED 2026-09-02.** That paragraph described an intention, not the
> shipped file. Until 2026-09-02 `native_entity_lobbying_disclosures.csv`
> applied **no** amendment supersession: 1,416 amendment rows, 1,432
> registrations and 1,233 terminations all shipped as rows and a naive
> `SUM(spend_usd)` double-counted **$37,349,254.01 — 5.15%** of the
> $725,743,974.52 total. It is now done **as flags, not deletions** —
> `is_superseded`, `superseded_by_filing_uuid`, `supersession_status`,
> `supersession_group_id`, written by
> `code/1091_lobby_amendment_supersession.py`. The additive filing-grain total
> is `SUM(spend_usd) WHERE is_superseded = 0` = **$688,394,720.51**.
> Registrations and terminations are **not** set aside: registrations carry
> $0 by construction and terminations carry $17,280,761.63 of real reported
> spend for the period they close, so setting them aside would delete money
> rather than deduplicate it. Full account, including the 129 rows where
> supersession is refused as unknowable: the `LOBBY-SUPERSESSION` block in
> `docs/MONEY_TOTALLING_RULES.md`.

**Whole dollars for the payer.** A filing's full value counts once toward the
organisation that paid it. Rankings of organisations and industries are
therefore whole-dollar and sum to the real money.

**Even division where the disclosure is silent.** A filing naming four agencies
contributes a quarter of its value to each. The disclosure never says how a fee
was split, and crediting the full amount to each would count the same dollars
four times.

**Deviation against an entity's own norm** — the quarter against the mean of the
prior six — rather than against the field.

---

## Seven changes

### 1. Publish the even split AND the unallocated count. Never mix them.

Even division is a *stated assumption*, not a measurement, and it has a
direction: it understates how concentrated influence is on any single agency,
because a filing that names one agency and a filing that names eight are treated
as equally informative about each.

So report both, labelled, and never in the same column:

- `spend_allocated_usd` — the even split. Sums to the true total. Use for shares.
- `spend_touching_usd` — full value to each named item. Sums to more than the
  true total **by construction**. Use for "how much lobbying touched the BIA",
  which is a different and legitimate question.

A reader who is not told which they are looking at will read the second as the
first.

### 2. Income and expenses are an either/or, not a sum.

Under the LDA an outside registrant reports **income**; a self-filing
organisation reports **expenses**. On any single filing only one is populated.
`income + expenses` is correct as a portfolio rule and wrong as a row rule — it
silently doubles anything mis-keyed.

Cedar Press carries `self_filed`, `income_usd`, `expenses_usd`, `spend_usd` and
`spend_basis`, so the basis travels with every dollar and can be audited.

### 3. State the rounding. The precision is false.

LDA requires good-faith estimates **rounded to the nearest $10,000**. A total
printed to the dollar implies precision the source does not have. Report to the
nearest $10,000, and say so — a $28.71M figure is really $28.7M ± the rounding
of hundreds of filings.

### 4. Six quarters is too short, and quarters are seasonal.

Q1 and Q4 differ systematically — appropriations cycles, session calendars — so
a six-quarter mean compares a Q4 against a window containing two Q4s and puts
the seasonal swing into the "deviation."

Use **same-quarter prior-year** as the primary comparison, with the
six-quarter mean as a secondary. And require a minimum of four non-zero
quarters before reporting a deviation at all: tribal lobbying is lumpy, and an
entity that files once a year produces a meaningless percentage.

### 5. A quarter with no filing is $0, not missing.

An entity that stops lobbying must appear as zero in the series. If absent rows
are dropped, every trend line is fitted only to the quarters an entity was
active, and disengagement reads as flat rather than as a decline.

### 6. **Attribution confidence must travel with the dollar.** This is the big one.

The source methodology maps a filing to an organisation and an industry code and
stops. It has no way to express *how sure it is* that the filing belongs to that
organisation — and for Native entities that is the hard part, because the
client name is often nothing like the entity name.

Today this cost $39.43M. `SALT RIVER PROJECT` — an Arizona public power and
irrigation district — had 324 filings and $28.71M attributed to the **Salt River
Pima-Maricopa Indian Community** on the alias `river salt`. Also withdrawn:
Coeur d'Alene **Mines** ($2.96M), **City of** Santa Rosa ($2.31M), and eleven
more (`code/65_lobbying_organization_type_guard.py`).

Three rules follow:

- **Every attributed dollar carries a tier.** Only tier A publishes. A
  medium-confidence name match is a candidate, never a figure.
- **Organisation type is a bar, not a similarity score.** A municipality, a
  mining company, a public power district and a member cooperative are legal
  forms a tribe, an ANC or an NHO cannot be. That is a fact about the name and
  it outranks any string distance.
- **Withdrawals are recorded, not deleted** —
  `review/lobbying_withdrawn_by_org_type.csv` keeps every withdrawn client with
  its reason, so the correction is auditable and reversible.

### 7. Roll subsidiaries to the entity — and say which layer a number is.

This is where Cedar Press can do something the source methodology structurally
cannot. It maps to an organisation. We map to a **Native entity**, and can roll
a subsidiary's lobbying up to the entity that owns it: NANA Development's
filings belong to NANA Regional Corporation; Alutiiq's to Afognak.

Two guards on that:

- **Ownership and service are separate fields.** An organisation that *serves* a
  tribe is not owned by it, and its lobbying must never roll up as though it
  were.
- **Publish both layers.** `spend_direct_usd` (the entity's own filings) and
  `spend_rolled_usd` (entity plus owned subsidiaries). Presenting only the
  rolled figure would overstate direct political activity; only the direct
  figure would miss most of it.

---

## Source and coverage

US Senate and House LDA disclosures, `lda.gov` API, 1999–2026. Filings before
1999 do not exist in electronic form. Reported spend is the filer's good-faith
estimate rounded to $10,000, not an audited figure.
