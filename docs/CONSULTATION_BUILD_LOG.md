# Tribal consultation — build log

*Built 2026-08-07 by `code/96_build_consultation_events.py`. Phase 1 of the
Government Relations & Advocacy expansion (`docs/LOBBYING_EXPANSION_RECONCILIATION.md`,
SPEC v2 §9.5).*

---

## What this is, and the one line that governs it

**Tribal consultation is a statutory government-to-government obligation. It is
not lobbying.** E.O. 13175, NHPA §106, NAGPRA 25 U.S.C. 3003 and each agency's
own consultation policy create a duty owed to sovereigns. Filing that duty
under "lobbying" would characterise a sovereign relationship as
influence-buying, which is both wrong and offensive to the subject.

The build asserts this in code rather than in prose. `cedar_domain.AdvocacyChannel.CONSULTATION.is_lobbying`
returns `False`, and script 96 refuses to run if it ever returns `True`:

```python
assert AdvocacyChannel.CONSULTATION.is_lobbying is False, \
    "cedar_domain says consultation is lobbying - refusing to build."
```

Every row carries `channel = CONSULTATION`. The dataset is *government
relations and advocacy*, of which LDA filing is one channel among seven.

---

## What was extended, not rebuilt

The Federal Register pass already on disk was the input, and none of it was
modified:

| Input (unchanged) | Rows |
|---|---|
| `data/clean/fr_consultation_notices.csv` | 484 |
| `data/clean/fr_consultation_referenced.csv` | 1,829 |
| `data/clean/fr_consultation_by_agency.csv` | 21 agencies |
| `data/clean/fr_consultation_year.csv` | 33 years |

Those files hold *notice-level* metadata. This build retrieved the **full
published text of all 2,313 documents** and went to *participant level*.

---

## Output

| File | Rows |
|---|---|
| `data/clean/consultation_events.csv` | 11,402 |
| `data/clean/consultation_agency_coverage.csv` | 66 |
| `review/consultation_unresolved_2026-08-07.csv` | 477 |
| `data/clean/codebook_master.csv` | +50 variables, dataset `15_consultation` |

**2,313 consultations · 10,396 participant rows · 396 distinct Native entities ·
1994–2026 (33 years).**

One row per (consultation, participating entity). A consultation with 40 named
Tribes is 40 rows sharing one `consultation_event_id`.

`source_url` and a verbatim `source_quote` are present on **11,402 of 11,402
rows (100%)**. No row exists without the sentence that produced it.

Every row is **tier B**. A parsed federal record is one leg of evidence; tier A
requires a human ruling or two independent legs.

---

## The fact this dataset adds that nothing else in Cedar holds

NAGPRA consultation notices carry a fixed grammar that separates two different
facts into adjacent sentences:

> "A detailed assessment of the human remains was made by Dinosaur National
> Monument professional staff **in consultation with representatives of** the
> Arapahoe Tribe of the Wind River Reservation, Wyoming; Comanche Nation,
> Oklahoma; … and the Ute Mountain Tribe of the Ute Mountain Reservation,
> Colorado, New Mexico & Utah. The Hopi Tribe of Arizona; Navajo Nation,
> Arizona, New Mexico & Utah; … and the Zuni Tribe of the Zuni Reservation, New
> Mexico, **were contacted for consultation purposes but did not attend the
> consultation meetings**."
> — 76 FR 7232, document 2011-2793

Sometimes the Federal Register names the two groups itself:

> "…hereafter referred to as **'The Consulted Tribes.'** The Burns Paiute
> Tribe; … and the Klamath Tribes **were notified, but did not participate in
> consultation.** Hereafter, these tribes are referred to as **'The Invited
> Tribes.'**"
> — 84 FR 2918, document 2019-01624

**A Tribe invited is not a Tribe present.** Role is assigned only from a verb
phrase in the *same sentence* as the name list; a name list in a sentence with
no role marker yields no participants at all. Roles are never upgraded.

| `participant_role` | Rows | Meaning |
|---|---|---|
| `consulted` | 9,110 | the record states consultation was held with this entity |
| `invited_did_not_participate` | 1,211 | the record states it was contacted or invited and **did not attend** |
| `not_enumerated` | 1,006 | the consultation is real; the record names no participants |
| `invited` | 75 | invited, outcome not stated |

---

## Cross-source verification against `nagpra_notice_entity_bridge.csv`

`docs/CROSS_SOURCE_VERIFICATION.md` is standing policy: one federal source is a
claim, two that agree is a verification, two that disagree is a finding.
Dataset `11_nagpra` (another agent) independently parsed 6,316 NAGPRA notices
into 51,338 party rows. 1,828 of its documents overlap this build.

**Agreement — a verification.** Of this build's `consulted` rows on shared
documents, **8,509 agree** with the bridge's `consulted` label. 511 are absent
from the bridge; 89 carry a different NAGPRA relationship there
(`aboriginal_land`, `culturally_affiliated`, `disposition_priority`) — those are
different relationships, not contradictions.

**Difference — new coverage.** Of this build's 1,211
`invited_did_not_participate` rows, **1,063 (87.8%) do not appear in the bridge
at all.** The invited-but-absent fact class is genuinely new to Cedar.

**Disagreement — a finding, recorded, neither side adjusted.** In 5 cases the
bridge labels a party `consulted` where the notice says it did not attend. All
5 are document 2019-01624, whose own text calls them "The Invited Tribes" and
says they "were notified, but did not participate in consultation." On the
published evidence this build is right and the bridge's `consulted` count
over-includes non-attenders. **Nothing in `11_nagpra` was edited** — that
dataset is another agent's, and the disagreement is recorded here rather than
smoothed over.

---

## Resolution, and the six ways containment has failed

`resolve_entity` is imported from `code/33_apply_party_rulings.py` — the one
resolver, never re-implemented. Its containment tier is unsafe in the
entity-contains-record direction, so this build wraps it in guards and, in
practice, supersedes it: **0 of 10,396 participant rows** were resolved by bare
containment.

| Method | Rows | |
|---|---|---|
| `fr_official_name` | 8,251 | record's name IS the official Federal Register name |
| `fr_official_prefix` | 759 | official name leads the record |
| `name_head` | 650 | spine name leads the record |
| `government_class_core` | 477 | identical identifying tokens, government class only |
| `resolve_entity_alias` | 136 | spine alias |
| `government_class_core_via_former_name` | 57 | matched on "(previously listed as …)" |
| `constituent_band_in_parenthetical` | 55 | expanded band list |
| `exact_canonical` | 10 | |
| `name_head_via_former_name` | 1 | |

**79% are exact official-name matches.** The guards:

1. **Specificity.** Containment is accepted only when `core(record) ⊇ core(entity)` — the record must be at least as specific. The direction that put $2.8B on a school is refused outright.
2. **The head rule.** An official Native government name *leads* and then qualifies: "Leech Lake Band **of the** Minnesota Chippewa Tribe, Minnesota". If the entity's name does not begin the record's name, the record is not about that entity. 119 candidate matches were refused on this alone.
3. **Class.** A consultation participant is a government, never a school, CDFI or college.
4. **State agreement**, where both sides carry one. 14 refusals.
5. **Trap tokens** (`cedar_domain.NAME_TRAPS`) — refused unless the state independently corroborates.

### Three defects this build found and fixed in itself

**Oneida.** "Oneida Nation (previously listed as Oneida Tribe of Indians of
**Wisconsin**)" resolved to the **New York** nation, because the parenthetical —
the Federal Register's own disambiguator, and the only thing carrying the state —
was being stripped before resolution. `cedar_domain.STANDING_DISAMBIGUATIONS`
names this exact pair. The parenthetical is now retained, states are read from
both halves, and where the two halves resolve to *different* entities the record
is treated as self-contradictory and neither is used.

**The umbrella swallowed by its own band.** The record "Minnesota Chippewa
Tribe, Minnesota" matched a spine row whose `fr_official_name` *begins* with it
— i.e. one of its six bands. Prefix matching now runs in one direction only.

**The band list that contradicted itself.** Document 2022-22514 lists, in the
same notice, "Minnesota Chippewa Tribe, Minnesota (Mille Lacs Band)" as
consulted and "Minnesota Chippewa Tribe, Minnesota (Bois Forte Band (Nett
Lake); Fond du Lac Band; Grand Portage Band; Leech Lake Band; White Earth
Band)" as invited-but-absent. Collapsing both to the umbrella made one Tribe
simultaneously present and absent. The parenthetical is not decoration — it
names *which bands did what*. It is now expanded to one row per band, matched
within the umbrella's own spine family (`CNSF-MINNCH-*`), **all-or-nothing** so
a partial expansion can never silently drop a band. Contradiction detection now
keys on the resolved entity rather than the published string, which is why the
string-keyed check had missed this.

Also fixed: the Federal Register uses semicolons *inside* parentheses to
separate constituent bands, so semicolon splitting is done with parentheses
masked (the same class of bug as the term-67 separator defect).

### Unresolved — 477 rows, 234 distinct names, never guessed

| Reason | Rows |
|---|---|
| `no_spine_match` | 265 |
| `entity_name_does_not_lead_record` | 119 |
| `ambiguous_containment` | 48 |
| `state_disagreement` | 14 |
| `non_government_class` | 9 |
| `current_vs_former_name_disagree` | 9 |
| `only_trap_tokens_shared` | 9 |
| `record_less_specific_than_entity` | 2 |
| `contradictory_roles_for_same_entity_in_one_record` | 2 |

Many are correct refusals rather than misses. Historical Federal Register names
("Arapahoe Tribe of the Wind River Reservation, Wyoming" = today's Northern
Arapaho; "Shoshone Tribe of the Wind River Reservation, Wyoming" = Eastern
Shoshone) need a **ruling**, not a fuzzy match. Others are parties genuinely
outside the spine, and the notices say so in as many words — "Wanapum Band, a
non-Federally recognized Indian group", the Brothertown Indian Nation, the
Cowasuck Band of the Pennacook-Abenaki People.

---

## Coverage — and what a zero means

`consultation_agency_coverage.csv` is keyed on the **publishing agency**, taking
the sub-agency where the record has one. Keying on the parent department books
all 1,829 NAGPRA notices to "Interior Department" and reports the National Park
Service — which published every one of them — as publishing nothing. That false
absence is the exact failure this file exists to prevent.

| Agency | Events | Participant rows | Tribes |
|---|---|---|---|
| National Park Service | 1,841 | 10,361 | 395 |
| Indian Affairs Bureau | 85 | 1 | 1 |
| HHS (ACF, CDC, CMS, dept.) | 77 | 0 | 0 |
| Environmental Protection Agency | 43 | 0 | 0 |
| Interior Department (direct) | 29 | 34 | 34 |
| Housing and Urban Development | 14 | 0 | 0 |
| Indian Health Service | 8 | 0 | 0 |
| USDA (incl. Forest Service) | 8 | 0 | 0 |
| Transportation (incl. FHWA) | 7 | 0 | 0 |
| Fish and Wildlife Service | 5 | 0 | 0 |
| Federal Communications Commission | 4 | 0 | 0 |
| Energy | 3 | 0 | 0 |
| Army Corps / Defense | 2 | 0 | 0 |
| Bureau of Land Management | 2 | 0 | 0 |

**The finding: 12 of the 13 agencies worked publish consultation records that
name no participating Tribes at all.** NAGPRA is the only federal consultation
regime that routinely publishes attendance. Everywhere else the consultation is
announced and the participants are not disclosed. That is a property of federal
publishing practice, not of tribal engagement.

**Absence of consultation records is not absence of consultation.** Every zero
in the coverage file carries the probe evidence behind it, and the file
distinguishes four different things that all look like "nothing":

- **Edge-blocked (HTTP 403)** — HHS, USDA, DOT, USACE, FCC. A WAF refused an
  automated client. Their consultation material is real and unretrieved. Same
  class as the known ntia.gov block in `AGENTS.md`.
- **Unlocated page (HTTP 404)** — read as *our* error until proven otherwise.
  AGENTS.md already records that BIA's Southwest Region page 404s at the obvious
  slug. Correcting guessed URLs took the 200-rate from 5/19 to 9/24; DOI, EPA
  and IHS were all recovered this way.
- **JavaScript-rendered (HTTP 200, <500 chars)** — NPS, HUD. The page is live
  and its content is not in the bytes.
- **Records name no participants** — the 12 agencies above.

Only the last is even arguably a statement about an agency, and none of them is
a statement about whether consultation happened.

### Published obligations captured

A published obligation is a map to records nobody has pulled. Two agencies
publish one in machine-readable form:

- **BLM** — "Under Section 106 of the National Historic Preservation Act
  (NHPA), federal agencies are **required to consult** with Tribal Nations when
  projects (or undertakings) may affect historic properties…"
  (`blm.gov/programs/cultural-heritage-and-paleontology/tribal-consultation`)
- **FWS** — 510 FW 1: "We **will consult** with inter-Tribal organizations to
  the degree that Tribes have authorized such an organization to consult on the
  Tribe's behalf." (`fws.gov/policy-library/510fw1`)

The obligation regexes were rewritten after measuring: agencies write "we will
consult … when X", not "consultation is required annually". A pattern built for
the latter matched nothing on any of the nine retrievable pages and would have
recorded "no obligation published" — a false negative on the most consequential
field here.

---

## Fields that are mostly blank, and why that is correct

| Field | Filled | Why |
|---|---|---|
| `comment_deadline` | 9,026 | from the Federal Register's structured `comments_close_on`, never inferred |
| `event_start_date` | 93 | parsed **only** from a DATES sentence that describes a meeting and is not the comment deadline |
| `location` | 60 | parsed only from the record's ADDRESSES section |

Most records in this corpus report a *completed* consultation and never state
when or where it happened. **Blank is silence, not zero.** Guessing a meeting
date out of a comment deadline would have filled these columns and made them
worthless.

---

## Advocacy coverage — the blind spot this closes

- Entities in the LDA lobbying dataset: **300**
- Entities reached by consultation: **396**
- **New to the advocacy dataset — no LDA filing at any time: 128**

128 Native governments have a documented government-to-government relationship
with a federal agency and no lobbying filing at all. A filter on LDA answers
"did this entity self-report as a lobbying client," never "does this entity
engage the federal government." This is the single largest blind spot the
advocacy dataset had.

Reach by class: 337 federally recognized tribes, 44 Alaska Native villages, 8
constituent bands, 6 state-recognized tribes, 1 intertribal organization.

Constituent bands are treated as participants in their own right. That is a
**participation** judgment and not a money judgment — nothing here rolls up, and
AGENTS.md's rule that a constituent band's contracts are not the umbrella's is
untouched.

---

## Pull discipline

`docs/PULL_DISCIPLINE.md`, observed throughout.

- `logs/_HOSTLOCK_www.federalregister.gov.json` was checked (released
  2026-08-06 by script 76), claimed, and released on completion.
- `api.usaspending.gov` and `web.archive.org` were **held by other agents and
  never touched** — not even a probe.
- 2,313 documents + 39 metadata calls, sequential, ≥0.8 s spacing, exponential
  backoff 60 s→1800 s, instant-disconnect treated as an edge block rather than
  retried. **Zero throttling, zero 429s, zero retries.**
- Metadata was initially requested 200 document numbers at a time and returned
  **HTTP 414 (URI too long)**; chunking at 60 fixed it.
- Every agency host was claimed and released individually; each took ≤3
  requests.
- Every request's status is in
  `data/raw/external/consultation/_SOURCE_MANIFEST.csv` (2,211 rows) and
  `agency_probe_log.csv` (31 rows). Status travels with the bytes — a 404 body
  still contains markup.

---

## What was not touched

`fr_*` source files, `nagpra_*`, `gaming_*`, `compact_*`, `nigc_*`,
`subawards.csv`, `resource_*`, the identifier ledger, and
`code/01_build_entity_spine.py` (never run — a rebuild drops every appended
entity). `codebook_master.csv` was appended to with a re-read immediately before
write, so scripts 97 and 99 cannot be clobbered.

---

## Next

1. **The 234 unresolved names are the highest-value ruling queue here** — many are historical Federal Register names that only a ruling can settle, and each one settled unlocks every consultation that names it.
2. **The five edge-blocked agencies** (HHS, USDA, DOT, USACE, FCC) need a manual download → upload path. Uploaded files bypass robots restrictions (AGENTS.md).
3. **EPA's TCOTS** (Tribal Consultation Opportunities Tracking System) is a live consultation tracker and redirected (302) rather than resolving; it is the single richest un-pulled consultation source found.
4. **IHS Dear Tribal Leader Letters** are published as a series and are the cleanest non-NAGPRA participant source available.
5. Extend to the remaining channels in §9.5: `OIRA_MEETING`, `HEARING_TESTIMONY`, `FACA`.
