# Subset Datasets

*Elijah, 2026-08-06: "these 10 datasets are parent datasets — see if there are
viable subset datasets that are easy for us to add that can help our work and
provide more value. we want to be an authoritative source of data for all to
use."*

Everything below is **already inside data we hold**. No new source, no new
pull. The counts are measured, not estimated.

---

## Why a subset is worth cutting at all

A parent dataset answers "how much money moved." A subset answers a question
somebody actually has. 156,452 Federal Register documents is a corpus; **6,179
NAGPRA notices is a dataset a museum registrar, a THPO and a journalist each
need and none of them can get.**

Two tests before cutting one:
1. **Does it have its own users?** NAGPRA has tribal historic preservation
   officers and museums. "FR documents mentioning tribes" has nobody.
2. **Does the parent make it hard to find?** If a subscriber can filter to it in
   one click, it is a saved search, not a dataset.

Cut where the answer to both is yes.

---

## Inside Dataset 9 (Federal Register, 156,452 docs, 1994–2026)

| Docs | Subset | Why it stands alone |
|---:|---|---|
| **6,179** | **NAGPRA / repatriation** | The strongest candidate in the whole corpus. Every notice of inventory completion and intent to repatriate, 1994–2026, naming the institution, the tribes consulted, and what is being returned. **No structured public database of this exists.** Its users — THPOs, museums, NAGPRA Review Committee, journalists — are underserved and easy to identify. |
| **3,179** | Gaming / IGRA notices | Compact approvals and disapprovals, Secretarial procedures, land determinations. Feeds Dataset 7 and stands alone for gaming counsel. |
| **560** | Energy and mineral leasing | Leasing regulations and approvals. Pairs with the contracting and funding series for an energy-development view. |
| **543** | Indian Health Service | Contract health, service-area and funding notices. |
| **490** | Probate, allotment, fractionation | Land-tenure administration. Feeds any land-consolidation analysis. |
| **407** | **Recognition history** | Already being built. Annual rosters 1995–2026 diffed into recognitions, terminations, restorations and renames. |
| **385** | Tribal consultation notices | Who is consulted, by which agency, on what — a direct measure of federal engagement. |
| **287** | Liquor ordinances | A genuine FR category; tribal liquor ordinances must be published to take effect. Small, complete, and nobody has it. |
| **209** | Self-governance and 638 contracting | The administrative record behind $27B of IHS self-governance money. |
| **189** | Land into trust | Fee-to-trust acquisitions and reservation proclamations. Bounds gaming facility dates from below. |
| **164** | Housing / NAHASDA | The regulatory layer under IHBG. |
| **82 / 79 / 75 / 18** | Roads · ICWA · Water rights settlements · EPA Treatment-as-State | Small but each is complete and unavailable elsewhere. Water settlements especially carry large dollar figures. |

---

## Inside Dataset 2 (Prime contracting, 617,142 rows)

| Rows | Subset | Why |
|---:|---:|---|
| 176,859 · $74.41B | **8(a) participation** | The single largest set-aside channel for Native firms, and the one that carries the ANC/NHO/tribal 8(a) story. A time series of entry, growth and graduation is a product on its own. |
| 7,245 · $0.65B<br>6,927 · $0.73B | **Indian Business · Buy Indian** | Together **0.5%** of Native prime dollars. That number is itself the finding: the Native-specific set-asides are not how Native firms win federal work. Small, exact, and quotable. |
| 223,603 · $52.60B | No set-aside reported | A quarter of the dollars arrive with no preference recorded — worth publishing as a data-quality fact about FPDS. |

---

## Inside Dataset 3 (Federal funding)

Each major programme is a defensible series in its own right:

| Rows | $ | Programme |
|---:|---:|---|
| 23,513 | $27.25B | 93.210 IHS Tribal Self-Governance |
| 30,896 | $5.71B | 15.022 Tribal Self-Governance (Interior) |
| 22,410 | $7.98B | 93.441 Indian Self-Determination |
| 12,643 | $3.32B | 20.205 Highway Planning and Construction |
| 9,508 | $0.62B | 10.567 Food Distribution on Indian Reservations |

**Self-governance across the three programmes is ~$41B and is the largest single
story in Native federal finance.** It deserves its own cut rather than sitting
inside a 2.7M-row transaction file.

---

## Inside Dataset 4 (Lobbying)

**The registrant market — 429 firms representing Native clients.** Sonosky
Chambers (1,858 filings), Hobbs Straus (1,603), Holland & Knight (1,298), Ietan
(800), PACE (766). Who represents whom, at what price, and how that has shifted
over 27 years. Law firms and tribes both want this and neither can get it.

---

## Inside Dataset 5 (Entities)

**The ownership graph as a product.** 952 entities with `parent_entity_id`,
`ultimate_parent_entity_id` and `ancsa_region_entity_id`, plus 2,148 tier-A
identifier links and 106 learned brand families. Nobody else can state that
Alutiiq Pacific is Afognak's, because nobody else has built the crosswalk.

This is the moat. It is worth publishing as an entity reference in its own
right, separate from any transaction data.

---

## Recommended order

1. **NAGPRA** — largest, most underserved, clearest users, zero new sourcing.
2. **Self-governance series** — biggest dollars, cleanest programme boundary.
3. **8(a) participation** — the Native federal contracting story.
4. **Recognition history** — in progress; retroactively fixes identification.
5. **Registrant market** — small effort, distinct buyer.

The first three need no new data at all — only a cut, a codebook and a
narrative.

---

## The rule that keeps this from becoming clutter

**A subset must inherit the parent's entity keys and its caveats.** A NAGPRA
dataset that loses `tribe_id` is a PDF index. One that loses the parent's
warnings — that FR classification is keyword-derived, that only the named
buckets are precise — is worse, because it presents an unqualified extract of a
qualified source.

Every subset ships with the parent's `tribe_id`, the parent's confidence tier,
and a pointer back to the parent's codebook.
