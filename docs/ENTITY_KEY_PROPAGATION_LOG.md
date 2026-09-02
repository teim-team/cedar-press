# Entity-key propagation log

*Written by `code/70_key_unjoined_datasets.py` on 2026-08-06.*
*Every number below is measured from the data at run time; regenerate rather than hand-edit.*

Six datasets carried a 0%-populated entity key and joined to nothing.
This run keys them against the 952-entity spine using the ONE resolver
(`33_apply_party_rulings.resolve_entity`).

## Result

| Dataset | Rows | Keyed | % | Tier A | Tier B | Note |
|---|---:|---:|---:|---:|---:|---|
| ownership_events | 98 | 93 | 94.9% | 77 | 16 |  |
| compacts | 707 | 702 | 99.3% | 628 | 74 |  |
| compact_events | 31 | 31 | 100.0% | 29 | 2 |  |
| compact_terms | 1,311 | 1,303 | 99.4% | 1,205 | 98 |  |
| gaming_land_decisions | 138 | 137 | 99.3% | 125 | 12 |  |
| gaming_facilities | 774 | 757 | 97.8% | 213 | 544 |  |
| np_orgs | 12,764 | 1,450 | 11.4% | 54 | 1,396 |  |
| native_bills (bridge) | 3,037 | 569 | 18.7% | 548 | 92 | 640 bill-entity links |
| bill_votes (bridge) | 423 | 25 | 5.9% | 20 | 6 | 26 vote-entity links, inherited via bill_id |
| member_positions | 136,119 | 0 | 0.0% | 0 | 0 | NOT KEYED BY DESIGN - joins through bill_id to the bill bridge. A member position is a person's vote, not an entity fact. |
| federal_actions (bridge) | 156,452 | 4,991 | 3.2% | 1,461 | 4,325 | 5,786 document-entity links; 1,836/2,794 of the named buckets keyed |

## How to read the new columns

| Column | Meaning |
|---|---|
| `tribe_id` | The spine entity. Present at EVERY tier - read `entity_tier` before using it. |
| `entity_id` | The **publishable** key. Written only at tier A, blank otherwise. |
| `entity_tier` | `A` publishable · `B` never publishes until ruled · `X` excluded by ruling |
| `entity_match_method` | exact / alias / core / containment / inherited / propagated ruling |
| `entity_match_basis` | Why, in words, including every guard that fired |

Roll-up joins `tribe_id` to the spine and aggregates on
`ultimate_parent_entity_id`.

## Tier rule applied

Tier A requires an **exact** name match, an **alias** match, a
**documented ruling**, or **structural inheritance** from a tier-A
parent row. Core-set equality and containment are tier B, however
obviously right they look. Every distinct tier-B name is queued in
`review/entity_key_tierB_promotion_queue_2026-08-06.csv` so one ruling
settles every row carrying that name.

## Many-to-many, modelled as bridges

A bill affects many tribes and a Federal Register notice can name
several. Those get bridge tables, never a single `tribe_id`:

- `data/clean/native_bills_entity_bridge.csv`
- `data/clean/bill_votes_entity_bridge.csv` (inherited via `bill_id`)
- `data/clean/federal_actions_entity_bridge.csv`

`member_positions.csv` is deliberately **not** keyed. It joins
through `bill_id` to the bill bridge; a member's vote is a fact
about a person, not about an entity.

## What refused, and why

A refusal is a good outcome. Full list:
`review/entity_key_refusals_2026-08-06.csv`.

| Reason | Rows |
|---|---:|
| `no_spine_match` | 5,932 |
| `org_type_barred` | 372 |
| `span_is_only_a_trap_token` | 217 |
| `trap_token_state_conflict` | 167 |
| `ambiguous_containment` | 115 |
| `ambiguous_span` | 10 |
| `ambiguous_core` | 3 |
| `elijah_ruling` | 2 |
| `ruled_not_a_native_entity` | 2 |
| `acronym_alias` | 0 |
| `all_generic_tokens` | 0 |

## The guards that fired

1. **Organisation type is a bar, not a score** - reused from
   `code/65`. A municipality, mining company, power district,
   cooperative or university cannot be a Native entity.
2. **Name traps** - a match resting entirely on `creek`, `cherokee`,
   `colorado`, `ojibwe`, `shawnee`, `oneida` or `apache` is refused.
3. **State disagreement** demotes; with a trap token it refuses.
4. **Village corporation != village government** - the resolver's
   ANCSA guard, re-checked here on the alias route.
5. **BIA index defect** - the 41 compact rows and 3 gaming-decision
   rows with `bia_tribes_column_conflict` cannot reach tier A off
   the defective column.
6. **Nonprofits** - `verified_strict` is a NAME match, not verified
   Native status, so an exact hit still needs to clear the
   place-name and civic-descriptor flags.
7. **Free text** additionally bars generic-token name strings
   (`Council`, `Little River`, `Tribal Self-Governance`) and acronym
   aliases. 117 spine name strings are excluded from
   prose matching for this reason.
