# Federal Recognition History — Build Log

> **COMPANION: `docs/RECOGNITION_HISTORY_LOG.md` holds the PARSING METHOD.**
> *Cross-link added 2026-08-28 during doc consolidation.* This file carries the
> verification and the defect list; the companion carries notice selection, GPO
> de-wrapping, the four meanings of a parenthesis, entity identity across
> notices, and the 118-rename bridging pass. **Neither supersedes the other.**

*Build: `code/76_build_recognition_history.py`. Data written 2026-08-06 19:04.
Verified and closed out 2026-08-07. Every number below was recomputed from the
files on disk.*

The build finished its data and died on an API spend limit before it wrote this
log or ran the regression gate. It also closed with one flagged risk — *"one
safety gap in the alias proposals — loose resolutions could attach a name to
the wrong tribe"* — which is worked first, in §3.

---

## Scope: this is infrastructure, not a product

`docs/plans/SPEC_v2_ENTITY_EVENT_INTELLIGENCE.md` §2 lists recognition events under
derived subsets with an explicit ruling:

> Recognition events (internal infrastructure feeding the entity/history layer;
> **ruled NOT to ship as a standalone collection**, since legal-status change
> moves too rarely to sell as a maintained cadence).

That ruling stands and this log documents the build accordingly. **This is the
authoritative internal feed for tribal-status temporal changes — renames,
recognitions, terminations, restorations.** It is what makes a 1996 contracting
row or a 2003 funding row resolve to the right modern entity. It is not a Press
shelf item, it has no publication cadence, and it is deliberately absent from
`data/clean/codebook_master.csv`, which carries only the fourteen shipping
datasets (`01_deals` … `13_admin_regions`). That absence is the ruling being
honoured, not an omission — and adding these columns as `published=1` without
descriptions would break `codebook_undocumented_public`, which is 0.

## Files on disk

| File | Rows | Grain |
|---|---:|---|
| `data/clean/federal_recognition_events.csv` | 366 | one row per status change |
| `data/clean/federal_recognition_roster.csv` | 17,058 | one row per (notice, listed entry) |
| `data/raw/external/fr_recognized/_notice_manifest.csv` | 129 | discovered FR notices, 32 selected |
| `review/recognition_alias_proposals.csv` | 298 | proposed spine aliases (input to §3) |
| `review/recognition_alias_dropped.csv` | 20 | proposals the build itself rejected |

Source: the annual "Indian Entities Recognized and Eligible To Receive Services
From the United States Bureau of Indian Affairs" notice, required since the
Federally Recognized Indian Tribe List Act of 1994 (Pub. L. 103-454).

---

## Internal consistency — verified

| Check | Result |
|---|---|
| Roster notices absent from the manifest | **0** |
| Events whose `fr_document_number` is not in the manifest | **0** |
| Events with no `fr_citation` / no `source_url` | **0 / 0** |
| Events with an empty `quote` / empty `quote_basis` | **0 / 0** |
| Events asserting a `mechanism` while `mechanism_basis` says `not_stated_in_record` | **0** |
| `REMOVED` events described as a termination | **0** of 11 |
| `tribe_id` values not present in the spine (events / roster) | **0 / 0** |
| Roster entries under 8 characters (the phantom-wrap signature) | **0** |
| Roster entries over 300 characters (the swallowed-list signature) | **0** |

The wrap-handling rules described in the build's docstring demonstrably work:
the 2014 unclosed-paren case and the `[[Page NNNN]]` cases produce no phantom
or swallowed entries anywhere in 17,058 rows.

**Zero fabrication, verified against the cached notices.** Every one of the 366
events carries a verbatim quote. Each quote was searched in the raw cached text
of the document it cites:

| `quote_basis` | Checked | Found verbatim |
|---|---:|---:|
| `roster_line` | 199 | 195 |
| `roster_lines_both_notices` | 130 | 130 |
| `notice_preamble` | 21 | 21 |
| `roster_line_of_prior_notice` | 10 | 10 |
| `correction_notice` | 3 | 3 |
| `related_fr_document` | 3 | 0 — *by design; the basis says the quote is from a different document* |
| **Total** | **366** | **359 (98.1%)** |

Excluding `related_fr_document`, which correctly points elsewhere, 359 of 363
quotes (98.9%) are byte-verifiable in the cited notice. The 4 `roster_line`
misses are whitespace/hyphenation variants of the cached GPO text, not invented
text.

Entity keying: events 341/366 (93.2%), roster 15,238/17,058 (89.3%). No key
points at an entity that does not exist.

---

## 3. The alias-proposal safety gap — worked first

The build's own closing flag was right, and it is worse than it looked.

**The risk.** An alias row is a permanent claim that spine entity *T* is also
known as string *S*. The spine's alias list is read by `resolve_entity`, which
every dataset in the project imports. A wrong alias is not a wrong row; it is a
wrong rule that silently misattributes every future record naming *S*.

**The 298 proposals as built:**

| `alias_source` | `exact` | `alias` | `core` | `containment` |
|---|---:|---:|---:|---:|
| `fr_previously_listed_as` — the FR itself declares the former name | 1 | 47 | 21 | 4 |
| `fr_also_known_as` | 1 | 1 | 1 | — |
| `fr_listed_name` — no rename declared; the link is the matcher's inference | — | — | 22 | **200** |

The dangerous cell is the bottom right: 200 proposals where the Federal
Register does *not* say the string is a former name **and** the entity link is
the containment tier — the tier `AGENTS.md` records as having cost real money
five times in a single day, and which may be used "only to resolve an owner
already named in evidence — never to detect a match."

### Five proposals are outright contradictory

The same alias string is proposed for **two different spine entities**.
Applying both would make the spine self-contradictory and poison the resolver
permanently:

| Alias string | Proposed for | And also for |
|---|---|---|
| `Paiute-Shoshone Indians of the Bishop Community of the Bishop Colony, California` | `TRBF-BISHOP-00` Bishop Paiute (CA) ✅ | `TRBF-FALLON-00` Paiute-Shoshone (NV) ❌ |
| `Paiute-Shoshone Indians of the Lone Pine Community of the Lone Pine Reservation, California` | `TRBF-LNPINE-00` Lone Pine (CA) ✅ | `TRBF-FALLON-00` Paiute-Shoshone (NV) ❌ |
| `Oneida Tribe of Indians of Wisconsin` | `TRBF-ONDAWI-00` Oneida Nation (WI) ✅ | `TRBF-ONDANY-00` Oneida (NY) ❌ |
| `Native Village of Old Harbor` | `AKNF-ALTIIQ-00-KONIAG` Alutiiq Tribe of Old Harbor ✅ | `ANVC-LDHRBR-00` Old Harbor Native **Corporation** ❌ |
| `Paiute Indian Tribe of Utah (Cedar City Band …)` | `TRBF-PTTRUT-00` Paiute of Utah | `CNSF-PTTRUT-CD` Cedar Band sub-unit |

Every one of these is a documented project trap firing again: the
Paiute-Shoshone / Shoshone-Paiute pair is literally in
`cedar_domain.STANDING_DISAMBIGUATIONS`; the Oneida NY/WI pair is the other
entry in that same tuple; and Old Harbor is the ANCSA
village-government-versus-village-corporation confusion from standing rule 2.

**Independent corroboration.** The Bishop→Fallon and Lone Pine→Fallon errors
were found *separately* in the NAGPRA bridge during the same close-out, where
they account for 97 misattributed rows across 30 notices
(`docs/NAGPRA_BUILD_LOG.md` §1b). Two unrelated builds, the same containment
tie-break, the same wrong tribe. That is a resolver defect, not a build defect.

### The split applied

Each proposal was tested for: contradiction; collision with an existing spine
name belonging to a different entity; state disagreement between the alias
string and the entity; an equally-scoring rival under the containment rule; and
an entity name composed only of trap / non-distinctive words.

| Bucket | Count | Written to |
|---|---:|---|
| **SAFE to apply** | **72** | `review/recognition_alias_proposals_safe.csv` |
| **STAGED — hard failure** | **47** | `review/recognition_alias_proposals_staged.csv` (`stage_priority=1_HARD`) |
| **STAGED — undeclared containment** | **179** | same file (`stage_priority=2_containment`) |
| Total | 298 | |

Hard-failure reasons (a proposal can fail more than one): equally-scoring rival
39 · contradictory 10 · state disagreement 6 · entity name is only
non-distinctive words 3.

The 72 safe proposals are: 31 `fr_previously_listed_as` + `alias`, 20
`fr_listed_name` + `core`, 18 `fr_previously_listed_as` + `core`, 1
`fr_previously_listed_as` + `exact`, 1 `fr_also_known_as` + `exact`, 1
`fr_also_known_as` + `core`. Every one has either the Federal Register stating
the former name in its own words (*"Ho-Chunk Nation of Wisconsin (formerly
known as the Wisconsin Winnebago Tribe)"*, *"Spirit Lake Tribe, North Dakota
(formerly known as the Devils Lake Sioux Tribe)"*, *"Tohono O'odham Nation of
Arizona (formerly known as the Papago Tribe …)"*) or an exact/core entity link,
and passes every hard test. Each carries a `safety_basis` column saying which.

**Nothing was applied to the spine.** `data/spine/` was not written by this
build or by this close-out. The 72 safe rows are staged as a reviewed
recommendation with a `YOUR_RULING` column; the 226 staged rows are ordered
hard-failures first so Elijah sees the five contradictions immediately.

---

## 4. What else this build got wrong

### One selected notice produced no roster rows and was not reported

The manifest selects 32 notices; the roster contains 30. The two missing:

- **`2021-06723`** (86 FR 18552, 2021-04-09) — titled *"… ; **Correction**"*.
  Correctly excluded: a correction notice is not a full list.
- **`2010-27138`** (75 FR 66124, 2010-10-27) — **unexplained.** Its title is
  identical to the primary 2010 notice `2010-24640` (2010-10-01), it carries no
  Correction marker, it is marked `selected=1`, its raw text is cached at
  `data/raw/external/fr_recognized/2010-27138_raw.txt`, and it produced zero
  roster rows with no entry in any refusal file.

This matters because second notices *are* kept in other years — 2016, 2018,
2023 and 2024 each contribute two full rosters. So the exclusion is
inconsistent with the build's own behaviour elsewhere and is either an
undocumented dedup or a silent parse failure. It should be resolved before the
1995–2010 half of the event stream is trusted.

### Six years have no notice, and the event dates absorb the gap

Roster coverage is 1995–2026 but only **26 distinct years**. Missing:
**1999, 2001, 2004, 2006, 2011, 2025.**

`effective_date_basis` is honest about what the date means —
`fr_publication_date_of_first_listing` (36), `…_of_first_absence` (11),
`…_of_the_new_name` (316), `…_of_correction` (3) — but a consumer must read it.
**Across a gap year, every change is dated to the later notice.** The five
additions dated 2012-08-10 (Narragansett, Onondaga, Shinnecock, Tejon,
Tuscarora) are a 2010→2012 diff, and Tejon's actual acknowledgment was
2012-01-03. **These are dates of first appearance on the published list, not
legal effective dates.**

### `event_type` alone overstates recognitions and removals

366 events: **RENAMED 319 · ADDED 35 · REMOVED 11 · RESTORED 1.**

But 8 of the 35 ADDED and 8 of the 11 REMOVED carry a
`possible_rename_counterpart` — they are the two halves of a rename the FR did
not mark as one, emitted separately because asserting an unmarked rename would
be an invented fact. A further 16 events carry
`review_flag = possible_unmarked_rename`.

**Net of counterparts: 27 real additions and 3 real removals.** Counting
`event_type == 'ADDED'` gives 35 and is wrong by 30%. This is the single most
likely misuse of the file and there is no column that computes it for you.

### The roster's per-notice entity count is not the BIA's own total

Entity-kind entries per notice fall from 545 (1995) to 463 (2022), then jump to
564 (2023). That is not 100 tribes being recognised — it is the BIA changing
how it prints Alaska villages and constituent bands. `data/clean/series_breaks.csv`
already carries one `recognition_history` row (`UNIVERSE_CHANGE`, `DOCUMENTED`,
source *91 FR 4102 and prior annual lists*), but it describes the moving
denominator generally, not this specific 2022→2023 printing change. **Never
publish a per-notice count as "the number of federally recognised tribes."**

### 1,336 roster rows dead-end on `ambiguous_core:2_spine_entities`

Script 77 solved this for NAGPRA by excluding the `CNSF-` federal-constituency
sub-units from its resolution view — leaving them in makes a parent tribe
permanently ambiguous against its own bands. Script 76 does not apply the same
exclusion, and 1,336 roster rows (7.8%) fail to resolve as a result. The two
scripts should agree.

---

## What this build got right

- **Terminations and restorations are captured with their statutory
  mechanism.** The Delaware Tribe of Indians is REMOVED 2005-11-25 (70 FR
  71194, `mechanism = court_order`) and RESTORED 2009-08-11 (74 FR 40218,
  `mechanism = act_of_congress`). That is the terminated-then-restored case the
  entity layer needs, with citations on both legs.
- **A removal is never called a termination.** 11 REMOVED events, 0 asserting
  termination; 10 carry the explicit basis *"not_stated_in_record; a removal is
  not evidence of termination."*
- **Act-of-Congress recognitions are correctly attributed**: the six Virginia
  tribes on 2018-07-23 (83 FR 34863), the Little Shell Tribe of Chippewa
  Indians of Montana 2020-01-30, and the **Lumbee Tribe of North Carolina
  2026-01-30 (91 FR 4102)** — the dataset's single most important event, and
  the one the build's docstring warns a naive `\(See` rule would have destroyed.
- **Pamunkey 2016-05-04** is correctly attributed to an administrative appeal
  order rather than to an act of Congress.
- `mechanism` is blank on 14 events with `mechanism_basis =
  not_stated_in_record` rather than guessed.

## How to use this feed

- **Join on `tribe_id`; read `previous_name` and the alias proposals to resolve
  historical strings.** This is the file that makes pre-2010 contracting and
  funding rows attach to the right modern entity.
- **Net ADDED/REMOVED against `possible_rename_counterpart`** before quoting
  any count of recognitions or removals.
- **Treat `effective_date` as date of first publication on the list**, and
  check `effective_date_basis`, especially across 1999, 2001, 2004, 2006, 2011
  and 2025.
- **Do not publish per-notice roster counts as tribe totals** (series break).
- **Do not apply `review/recognition_alias_proposals_staged.csv` to the spine
  without a ruling.** Five of them contradict each other outright.

## Open items, in priority order

1. Elijah to rule on `review/recognition_alias_proposals_staged.csv`, hard
   failures first (47 rows, of which the 5 contradictions are the urgent ones).
2. Fix the containment tie-break that produces Bishop→Fallon and
   Lone Pine→Fallon in `resolve_entity`. It affects this build *and* the NAGPRA
   bridge (212 rows there). A state-agreement condition on the tie-break is the
   minimal fix.
3. Resolve why `2010-27138` yielded no roster rows.
4. Apply script 77's `CNSF-` exclusion here to recover the 1,336 ambiguous
   roster rows.
5. Add a derived `net_change` column so `event_type` cannot be miscounted.
6. Record the 2022→2023 roster printing change in
   `data/clean/series_breaks.csv` as its own row.
7. Confirm whether 1999, 2001, 2004, 2006, 2011 and 2025 notices exist and were
   missed, or were never published. The List Act requires annual publication;
   BIA compliance has not been continuous.

## Provenance

- Discovery and full text: `federalregister.gov/api/v1` (GET, no key), cached
  as `data/raw/external/fr_recognized/<document_number>_raw.txt` with the
  manifest at `_notice_manifest.csv`. Every event row carries
  `fr_citation`, `source_url`, `quote` and `quote_basis`.
- Entity resolution: `resolve_entity` from `code/33_apply_party_rulings.py`.
  `data/spine/` read-only throughout; no spine row was written by this build or
  this close-out. Alias additions exist only as proposals.
