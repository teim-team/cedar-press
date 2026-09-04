# NHO Register + Intertribal (`I-`) Layer — Build Log

*Built 2026-08-05 by `code/36_build_nho_intertribal.py`. Console log at `logs/36_nho_intertribal.log`.*

Two entity classes the spine covered worst: Native Hawaiian Organizations, and the
collective vehicles that do much of Indian Country's lobbying. This build closes both
from source.

## Outputs

| File | Rows |
|---|---:|
| `data/clean/nho_register.csv` | 218 |
| `data/clean/intertribal_orgs.csv` | 57 |
| `data/clean/intertribal_memberships.csv` | 989 |
| `review/entity_candidates_nho_intertribal.csv` | 16 |

Nothing in `data/spine/`, `data/clean/cedar_*`, `entity_master.csv`, `nho_parents.csv`
or `review/cedar_review*.html` was touched.

---

## PART A — NHO register

### The correction that governs this build

An SBA **8(a) certification does not prove NHO ownership**. 8(a) admits both
entity-owned firms and firms owned by socially disadvantaged **individuals**; Native
Hawaiians qualify as individuals, so a family firm can hold 8(a) with no NHO parent —
HALOA Construction LLC, ruled 2026-08-05. Nothing in this register rests on a firm's
8(a) status.

Nothing rests on a Hawaii address either. The 444-row Hawaii geographic net included
"Backflow Testing Hawaii LLC"; 408 of 444 were correctly rejected.

### What made the enumeration possible

NHOA — the Native Hawaiian Organizations Association — publishes the only public
enumeration of SBA-certified NHOs, and **its membership is gated**:

> "NHOA membership is open to any non-profit NHO certified by the SBA pursuant to
> 13 C.F.R. 124.3."
> — <http://www.nhoassociation.org/membership.html>, fetched 2026-08-05

That gate is what makes directory membership evidence rather than association. It is a
different claim from "this firm holds 8(a)": it says the **parent** is SBA-certified as
an NHO.

The live member page is now **behind a login (HTTP 401)**. The roster was therefore
harvested from the Wayback Machine as a **series of 10 captures, 2021-05-06 to
2024-04-14** (`scratchpad/nhoa_series.py`, results in `nhoa_series.json`). A series beats
a snapshot because membership churns, and the churn is itself evidence:

- **Hui O Hana Pono** appears 2022-05-28 → 2023-06-06, then drops off. An exit.
- **Krilla Kaleiwahea Foundation** appears only in the final 2024-04-14 capture. A joiner.

`nho_register.csv` carries `nhoa_member_first_seen` / `nhoa_member_last_seen` per row.

### Result against the 30–40 estimate

**33 contracting NHOs registered** — inside Elijah's 30–40 band, up from 21 ruled parents.

| Evidence basis | Orgs |
|---|---:|
| `self_stated` — the organization (or its own subsidiary's site) states NHO status | 12 |
| `sba_8a_entity_owned` — NHOA member directory, membership gated on SBA NHO certification | 18 |
| `elijah_ruling` — Elijah's ruling is the only evidence | 3 |

| Confidence tier | Orgs |
|---|---:|
| A | 15 |
| B | 16 |
| C | 2 |

An added column, `verification_route`, records *how* each claim was established
(`org_self_statement`, `subsidiary_statement`, `NHOA_member_directory`,
`NHOA_board_seat`, `elijah_ruling`, `doi_onhr_notification_list`) so the
"8(a) proves nothing" lesson cannot be re-lost by reading `nho_status_basis` alone.

### 12 NHOs entirely new to Cedar Press

Alaka\`i Foundation Inc. · Hui O Hana Pono · Kalino Foundation · Kina\`ole Foundation ·
Kinai \`Eha · Ku Kanaka Foundation · Kulia Foundation · Makaha Cultural Learning Center ·
Malama Moloka\`i Foundation · Native Hawaiian Institute for Technology and Business ·
Pelatron Center for Economic Development · The Ali\`i Group · Krilla Kaleiwahea Foundation

### Self-statements verified firsthand

Five NHO self-statements were re-fetched directly rather than taken on a subagent's
word — Ho'omaka, Hui Huliau, Mana'o Nui, Ke Kumu 'Ulu, The Makua Group — as was the
entire NHOA members / membership / board triple. All matched.

### Aliases and renames recorded

Renames silently break name matching, so every one found is in `aliases`:

- **Ho'omaka Foundation** ← Native Hawaiian Legal Defense and Education Fund. Domain is
  still `nhldef.org`. NHOA renders it "…Education **Foundation**", a third variant.
- **Alaka'ina Foundation** → now under Bering-Alaka'ina Holdings / BSNC.
- **Hui O Hana Pono** ↔ The Hana Group (dba reported, not verified firsthand → review).
- **Kina\`ole Foundation** ↔ Kina'ole Family of Companies (unresolved → review).

**Native Hawaiian Legal *Corporation*** (EIN 99-0161861) and **Native Hawaiian Legal
*Defense* & Education Fund** are different organizations and are **not merged**. Two more
near-collisions are flagged in-row: Menehune Foundation vs Menehune Sports Foundation;
Kapono Foundation vs Henry Kapono Foundation. And **Alaka\`i Foundation Inc.** must never
be merged with **Alaka'ina Foundation** — both are NHOA members, different organizations.

### DOI ONHR Notification List — 185 rows at tier C

All 190 DOI-list organizations are carried, minus the 5 already present as contracting
NHOs, at `nho_status_basis = doi_roster_only`, `confidence_tier = C`,
`nho_class = doi_notification_list`. **Roster presence alone is not verification** — the
list is an NHPA Section 106 *consultation* list of community organizations, homestead
associations and civic clubs, and the register says so in every row's `evidence_quote`.
They are carried for completeness and for the EIN identifier, which is the one identifier
the spine lacks. The two classes are separable by `nho_class` and must not be summed.

How far the list ranges from the contracting universe is best shown by example: it
includes **"Captain Kimo's Hawaiian Adventures"** (EIN 88-4330264). That is the DOI list's
own Backflow-Testing-Hawaii moment — a reminder that presence on it says nothing about
SBA NHO certification.

**55 of the 190 DOI organizations resolved to a verified EIN**, matched against ProPublica
Nonprofit Explorer on exact normalized-name equality **and** state = HI, nothing looser.
The pass ran to completion over all 190 names despite heavy HTTP 429 throttling.

**A normalization bug was caught and fixed mid-build, and it is worth keeping.** The first
pass stripped `ʻokina` but **not kahakō (macrons)**, so `Hui o Kuapā` failed against the
IRS record `Hui O Kuapa`. Re-matching with a diacritic-aware normalizer
(`unicodedata` NFD, drop combining marks) recovered **8 more EINs, 47 → 55** — Hui o Kuapā,
Kauhakō Ohana Association, Ke Kula Nui O Waimānalo, Papakōlea Community Development
Corporation, Waimānalo Canoe Club, Waimānalo Hawaiian Homes Association, Waimānalo Health
Center, and ʻAhahui Siwila Hawaiʻi O Kapōlei. **Hawaiian orthography is a name-matching
trap on the same footing as the `creek` and `cherokee` tokens** in
`docs/CROSS_DATASET_LEARNING.md`, and any future Hawaii-side matching must fold both
ʻokina and kahakō before comparing.

Of the 135 still unmatched, **123 returned nothing at all** from ProPublica — consistent
with the DOI list being full of unincorporated groups (`ʻohana`, homestead associations,
canoe clubs, `ʻaha moku` councils) that hold no EIN. The other 12 have near-misses that the
strict rule deliberately blocked, including two **IRS-side typos** ("Ahonui Homestead
*Assoication*", "Pacific Justice & *Reconcollation* Center") and three **mainland chapters**
of Hawaiian civic clubs in CA and NV. Those are judgement calls, queued as `NHOIT-015`
rather than auto-accepted — the same strictness is what stopped "Nakupuna Foundation" from
absorbing "Nakuwauna Foundation".

**The two populations barely overlap, and that is the finding.** Only **5 of the 33**
contracting NHOs appear anywhere on the 190-name DOI list — Alaka\`i Foundation Inc.,
Menehune Foundation, Nakupuna Foundation, Native Hawaiian Community Development
Corporation, and The Makua Group. So 28 of 33 SBA-certified contracting NHOs are absent
from DOI's consultation list, and ~185 of DOI's 190 are not contracting NHOs. Anyone
treating the DOI list as an NHO contracting registry would get the universe wrong in
both directions at once. That is precisely why `doi_roster_only` is tier C.

### Ownership event that changes classification

> "Certified in 2004 as a Native Hawaiian Organization (NHO), the Alaka'ina Foundation
> entered federal contracting in 2005 and established nine (9) for profit firms that were
> **wholly acquired in June 2026 by BSNC**." — <http://beringalakaina.com/>

Nine firms Cedar Press currently classes NHO-owned became **ANC-owned** in June 2026. The
foundation remains an NHO; its subsidiaries do not. This is exactly the time-aware
ownership attribution the deal ledger exists to support — an ownership-change record
should be emitted. Queued as `NHOIT-009`.

### What could not be verified (Part A)

- **Founding years** for most NHOs. Only Mana'o Nui (2005) and The Makua Group (2008)
  state one on a fetched page. Everything else is blank, not guessed.
- **EINs for 25 of 33** contracting NHOs. ProPublica fuzzy-matches, which is a trap:
  searching "Nakupuna Foundation" returns "**Nakuwauna** Foundation" (84-2031455, Kailua
  Kona HI) — a different organization. EINs were accepted only on exact normalized-name
  equality **and** state = HI. Two rejections on state alone: "Kekoa Foundation"
  (Torrance CA) and "Makua Group" (Elkwood VA).
- **Ho'opale Foundation** and **Kalaimoku Foundation** are tier C — the weakest rows.
  Ho'opale's site says "a Native Hawaiian **organization**" in lower case, a generic
  descriptor and not the 13 C.F.R. 124.110 term of art. Kalaimoku's only evidence is a
  **consulting vendor's case study**, not a statement by either party.
- **Ho'opale → Nexus Consulting Group → Pacific Ridge** is uncorroborated. Nexus is
  described independently only as a "Native Hawaiian Organization Owned Firm" — an
  ownership *flag* with no parent named. `subsidiaries` left blank.
- **Lawelawe's "8 NHO subsidiaries"**: two subsidiary sites claim eight, no page names
  them. Only the 3 that are named are recorded. "Lawelawe Legacy Inc" (in
  `nho_verified_entities.csv`) appears on no retrieved page. `lawelawe.com` is a **parked
  domain for sale**, not the organization's site.

### Two likely misclassifications in `nho_parents.csv` (not edited — out of scope)

1. **Alaka\`i Services Group Inc.** is carried there as a parent. NHOA lists it as the
   **subsidiary** of Alaka\`i Foundation, Inc. in all 9 relevant captures. → `NHOIT-001`
2. **Hoilina Ranch LLC** is carried as a parent. 13 C.F.R. 124.110 requires an NHO to be
   a **non-profit**; an LLC cannot be one, and third-party text calls it "Native Hawaiian
   organization-**owned**", i.e. a subsidiary. → `NHOIT-002`

Plus a labelling bug: **Hawaiian Native Corporation** is `parent_class=ANC` in
`nho_parents.csv`, but it is an NHOA member and `entity_master.csv` already carries it as
**N-0002, "Native Hawaiian Organization (NHO)"**. The ANC label is an artifact of the
`ANC_HINT` regex in `code/19_rebuild_nho_layer.py` matching the token "corporation" — not
a ruling. → `NHOIT-008`. (Bristol Bay, Ahtna and St. Mary's in that file *are* genuinely
ANCs and are correctly excluded from this register.)

---

## PART B — intertribal / inter-Native organizations (`I-`)

**57 organizations registered**: 18 national, 19 regional, 20 sector. Every organization
named in `docs/plans/INFLUENCE_DATASET_PLAN.md` is present.

| Plan's named list | Registered |
|---|---|
| National — NCAI, NIGA, NAFOA, NCAIED, NIHB, NIEA, NAIHC, AFN, NHOA, ANCSA Regional Association, NACA | 11 / 11 |
| Regional — USET, ATNI, ITCA, Great Plains Tribal Chairmen's Association, MAST, CRITFC, NWIFC | 7 / 7 |
| Sector — tribal health boards, self-governance consortia, state gaming associations, tribal energy consortia | all four classes populated |

Beyond the plan: 7 more IHS-area health boards, 4 more state gaming associations, GLIFWC,
GLITC, ITCMI, ITCN, ITCC, APCG, COLT, SCTCA, UTOM, AVCP, TCC, ANVCA, NCUIH, AIHEC, NARF,
NAP, IAC, ITC, NATHPO, NTTA, NTEC, MTERA, NITEC and CERT.

`SGCETC` links the layer to the existing **SGVF** prefix in the NEID spine.

### `files_lda` is evidence, not judgement

Queried against the LDA.gov filings API as a lobbying **client**, 2026-08-05:

| | Orgs |
|---|---:|
| `yes` — filings exist, count and year range recorded | 38 |
| `no` — API returned 0 for that exact client-name query | 12 |
| `unknown` — query errored | 7 |

`no` means no filings appeared **under that name**, not that the organization never
lobbied. Three alias traps proved the point and were corrected in-build:

- **All Pueblo Council of Governors** — 0 under its own name, **8 filings 2007-2008**
  under the predecessor "ALL INDIAN PUEBLO COUNCIL".
- **CNIGA** — 0 under the full name, **11 filings 1999-2004** under the abbreviated
  "CALIFORNIA NATIONS INDIAN GAMING ASSN".
- **Inter Tribal Council of Arizona** — 0 under "Council", **38 filings 2016-2023** under
  "INTER TRIBAL **ASSOCIATION** OF ARIZONA". Whether that is the same legal entity or a
  c3/advocacy pair is unresolved → `NHOIT-010`.

Also methodological: the LDA API **substring-matches**. A bare "Indian Gaming Association"
query returns 535 filings because it sweeps in the state associations. IGA's own count is
the 393 recorded under "National Indian Gaming Association" — and both names must stay in
the alias list, because the organization **renamed** in April 2022.

### `member_count` vs `roster_count` — kept apart on purpose

"Represents X tribes" is a representation claim, not a membership count. Both columns are
carried and discrepancies are recorded, never reconciled:

- **NIHB** represents "574+" tribes; its **members are ~12 IHS-area health boards**, of
  which 11 are named.
- **NCUIH**'s 41 are IHS-contracting Urban Indian Organizations — its constituency.
- **ITCC** claims 47 members; its roster enumerates **35** — the largest gap in the layer.
- **AAIHB** claims to represent 27 tribes; its member page lists **6**.
- **OIGA** 31 vs 25 · **ATNI** 57 vs 59 · **MAST** 35 vs 36 · **SCTCA** 25 vs 26 ·
  **GPTLHB** 18 vs 19 · **TCC** 42 members ≠ 39 villages ≠ 37 federally recognized tribes.
- **AFN** is the cleanest: membership stated **by class** (192 tribes + 152 village
  corporations + 11 regional corporations + 11 regional nonprofits) — though its own
  regional page lists 12 of each, not 11.

### Membership rosters — the exposure channel

**35 organizations published a roster; 989 membership rows captured.** This is the
analytic point of the layer: a tribe that never files an LDA report still lobbies through
NCAI or NIGA dues, so membership is an exposure channel alongside direct filings.

`member_entity_id` is **deliberately blank throughout** — spine linking is a separate job
and was not guessed here.

Largest rosters: Indian Gaming Association 123 · ATNI 59 · AVCP 56 · CNIGA 54 · NPAIHB 43 ·
TCC 42 · NCUIH 41 · AIHEC 38 (tiered: 34 regular + 1 associate + 2 developing) ·
MTERA 33 · USET 33.

`membership_status` distinguishes COLT's **current** (12) from its **founding** (11)
roster — both are published on one page, and they differ: Northern Arapaho and Crow are
founding-only; Eastern Shoshone, Fort Belknap and San Carlos Apache are current-only.

**Three rosters are decoys and were deliberately excluded.** NCAI's Tribal Directory
explicitly disclaims being a member list ("this directory is not a listing of NCAI's
Tribal Nation Membership"); CNHA's 219-entry directory is a **paid business directory**
including T-Mobile, Bank of Hawaii and Marriott; NCUIH's is a federal-contracting
constituency list (loaded, but labelled as such).

**Rosters do not partition, and three are not tribe-level.** CRIHB lists Tribal Health
Programs (clinics), ANTHC lists regional health corporations, AVCP and TCC list
villages/communities. GLIFWC and GLITC share seven tribes; Lac Vieux Desert appears in
five organizations; Shoshone-Bannock in three. Any tribe-level rollup that sums across
organizations will double-count.

### Structural findings worth keeping

- **CRITFC and NWIFC have no EIN, and that is structural, not a gap.** They are
  intertribal **governmental** fishery agencies created by their member tribes, not
  chartered charities — the tribal-instrumentality blind spot of
  `docs/plans/NONPROFIT_DATASET_PLAN.md` caveat 1, showing up in the influence layer. NWIFC files
  **103 LDA reports** while having no 990 presence at all, which is precisely why this
  layer cannot be built off IRS data.
- **GPTCA ≠ GPTLHB.** A near-name collision with GPTLHB's own former name ("Great Plains
  Tribal Chairmen's **Health** Board"). Different mission, legal form, count (16 vs 18)
  and states. Both are registered separately.
- **GPTLHB's full rename chain**: AATCHB (1986) → Great Plains Tribal Chairmen's Health
  Board → Great Plains Tribal Leaders' Health Board (2020-10-01) → "Great Plains Tribal
  Health" brand (2025). IRS legal name is still the third.
- **Three IHS "area health boards" are not independent entities**: Phoenix is an ITCA
  department, Nashville a USET department, Navajo a tribal-government department. There is
  no "Bemidji Area Indian Health Board" — the Bemidji board is **GLATHB**.
- **ANTHC ≠ Alaska Native Health Board.** NIHB names ANHB as the Alaska-area board; ANTHC
  is the health-services consortium.
- **CERT is defunct or dormant** — ProPublica heads the record "Unknown Organization", the
  last Form 990 was FY2010, the website refuses connections with zero Wayback snapshots.
  No dissolution filing was found, so the evidence is cessation, not a recorded wind-up.
  Carried for historical LDA/990 matching. → `NHOIT-011`
- **Michigan and Wisconsin have no state Indian gaming association.** Wisconsin has only
  an informal, explicitly non-incorporated *regulators'* body (WGRA) — no EIN, no roster.
- Three domains in the plan are wrong or stale: `mastribes.org` → **midwesttribes.org**;
  `unitedtribesofmichigan.org` → **.com**; `gptchb.org` (HTTP 526) →
  **greatplainstribalhealth.org**.

### What could not be verified (Part B)

- **8 organizations have no EIN.** CRITFC, NWIFC, APCG, COLT, GPTCA, RMTLC, NTTA, NTEC.
  For CRITFC, NWIFC and APCG the absence is structural or historically explained; for
  **RMTLC it is a fetch failure** (ProPublica HTTP 429), not an established absence, and
  should be retried first. → `NHOIT-014`
- **No roster published** by NCAI, NAFOA, NACA, NHOA, SPTHB, SGCETC, NITEC, CERT or GPTCA.
- **MIGA's roster is recoverable later** — `/members/` returns HTTP 500 (WordPress fatal
  error) though it is in the site's own sitemap. → `NHOIT-015`
- **Founding years missing** for NCAIED, NIEA, NAIHC, NCUIH, AIHEC, NARF, NAP, IAC, ITC,
  NATHPO, NTTA, UTOM, RMTLC, GLATHB, WIGA and CNHA. AIHEC's homepage reads "50th
  Anniversary" (implying ~1974-75) but states no year — not recorded. AFN's 1966 rests on
  a **federal third-party** source (NLM Native Voices); AFN's own site states none.
- **NCAI has two EINs** under one name — 53-0210846 (c4, registered) and 53-6017907 (c3,
  the NCAI Fund). Whether to carry one entity or two is a ruling. → `NHOIT-012`

---

## One organization appears in both registers, by design

**Council for Native Hawaiian Advancement** is `I-012` in `intertribal_orgs.csv` (a
national inter-Native membership body) *and* `N-0051` in `nho_register.csv` (it sits on the
DOI notification list, tier C). Both are correct — they record different roles, and both
carry the same verified EIN 91-0313383. Anyone joining the two registers on EIN or name
must expect this row twice and must not double-count it.

## Review queue — 16 items, all `YOUR_RULING` blank

`review/entity_candidates_nho_intertribal.csv`. Every row carries **evidence_for** and
**evidence_against**, not just a question.

| ID | Entity | Issue |
|---|---|---|
| NHOIT-001 | Alaka\`i Services Group Inc. | parent or subsidiary of Alaka\`i Foundation? |
| NHOIT-002 | Hoilina Ranch LLC | an LLC cannot be an NHO (13 C.F.R. 124.110) |
| NHOIT-003 | Ho'opale → Nexus → Pacific Ridge | ownership chain uncorroborated |
| NHOIT-004 | Kalaimoku Foundation | only evidence is a vendor case study |
| NHOIT-005 | Native Hawaiian Organization Charity | never states its own NHO status |
| NHOIT-006 | Hui O Hana Pono / The Hana Group | dba unconfirmed; membership lapsed 2023 |
| NHOIT-007 | Kina\`ole Foundation vs KFOC | which is the legal NHO? |
| NHOIT-008 | Hawaiian Native Corporation | ANC label is a regex artifact |
| NHOIT-009 | Alaka'ina subsidiaries | NHO → ANC after the June 2026 BSNC acquisition |
| NHOIT-010 | ITCA vs Inter Tribal Association of Arizona | same entity or c3/advocacy pair? |
| NHOIT-011 | CERT | defunct, dormant, or active-unknown? |
| NHOIT-012 | NCAI | two EINs, one name |
| NHOIT-013 | GPTCA | no website, EIN, LDA record or roster |
| NHOIT-014 | CRITFC/NWIFC/APCG/COLT/RMTLC/NTTA/NTEC | structural absence vs fetch failure |
| NHOIT-015 | DOI-list EIN near-misses | IRS typos + mainland civic-club chapters |
| NHOIT-016 | MIGA roster | page returns HTTP 500 |

---

## Reproducibility

| Source | Access |
|---|---|
| NHOA member directory | Wayback CDX + `web.archive.org/web/<ts>id_/` — **curl works, WebFetch is blocked** |
| NHOA about / membership / board | `http://` only — https fails TLS handshake |
| LDA.gov filings API | free GET, ~15 req/min anonymous; **substring-matches client names** |
| ProPublica Nonprofit Explorer | JSON API `/nonprofits/api/v2/search.json?q=` works when the HTML pages CAPTCHA; supports `&state[id]=HI`; **fuzzy-matches — verify name and state** |
| IRS EO BMF | local slice `data/raw/external/irs990/irs_bmf_slice_universe_2026-08-05.csv` |

Harvest scripts live in the session scratchpad: `nhoa_series.py` (roster series),
`lda_probe.py`, `pp_probe.py`, `pass2.py`, `doi_ein_probe.py`.

## House rules observed

- **Zero fabrication.** Every row carries an evidence URL; unverifiable fields are blank.
- **IDs proposed, not minted.** 26 new `N-` proposed from N-0008; the 7 existing ids in
  `entity_master.csv` were carried, not re-minted. `I-` starts at I-001.
- **Flag, never delete.** Weak rows are tiered C and queued, not dropped.
- **Cite primary sources**, never hand-built dataset filenames.
