# NHO layer — diagnosis, 2026-08-28

*Read-only pass. Nothing was minted, promoted or edited. Every count is measured
from the files named.*

The Native Hawaiian Organization layer reads thin and has done for a while.
This says what is actually wrong with it, because the answer is four different
problems and only one of them is "missing data".

## 1. Coverage: 86 of 210

`docs/ENTITY_INVENTORY.md`, measured 2026-08-28: **86 of 210 NHO entities have
rows in any collection; 124 have none.** That is the thinnest of the large
classes — federally recognized tribes are 349 of 349.

**Most of the earlier alarm was measurement, not data.** The same inventory read
**4 of 210** on its first run and **32** on its second. Both were reader bugs:

- the `nho_*` table family was never claimed by any collection, so it was never
  read at all;
- `nho_doi_notification_roster.csv` keys on `nho_id`, and `nho_register.csv` on
  `proposed_id` — neither was in the recognised id list.

So the real figure is 86, and it moved 4 → 32 → 86 by fixing the reader three
times. **Do not quote a coverage number for this layer without saying which
tables were read.**

## 2. Only one NHO table joins the spine

| table | rows | spine-joinable id |
|---|---:|---|
| `nho_ito_spine_crosswalk.csv` | — | ✅ `tribe_id` |
| `nho_ownership_changes.csv` | — | partial — `acquirer_tribe_id` only |
| `nho_register.csv` | 218 | ⚠ `proposed_id` — a PROPOSAL, not a spine id |
| `nho_doi_notification_roster.csv` | 190 | ⚠ `nho_id` |
| `nho_verified_entities.csv` | 36 | ❌ none |
| `nho_parents.csv` | 21 | ❌ none (`parent_name` only) |

Three of six carry no spine id at all. That is the structural reason the layer
looks thin: the rows exist and cannot be attributed.

## 3. The 8 unpromoted register ids are NOT 8 organizations

`nho_register.csv` holds 218 `proposed_id` values; **210 are in the spine, 8 are
not.** An earlier note in this repo said the register "was never promoted" —
that was wrong, it is 96% promoted. But the residual 8 must not be minted as a
batch, because they are four different things:

| id | name | what it actually is |
|---|---|---|
| `N-0032` | Ho'opale Foundation | **organization** — `contracting_nho`, route `elijah_ruling`. Mint. |
| `N-0033` | Kalaimoku Foundation | **organization** — same. Mint. |
| `N-0051` | Council for Native Hawaiian Advancement | **organization** — a well-known NHO. Mint. |
| `N-0076` | Hui Huliau Inc | **DUPLICATE** of `NHO-HUIHUL-00` "Hui Huliau", already in the spine. Do not mint; add "Inc" as an alias. |
| `N-0170` | Office of Hawaiian Affairs - **continued** | **PARSING ARTEFACT.** "- continued" is a page-break fragment; OHA is already `NHO-FFCHWN-00`. Do not mint. |
| `N-0048` | Brian Kaniela Naeʻole Naauao | **A NATURAL PERSON.** |
| `N-0112` | Keoni Kealoha Alvarez | **A NATURAL PERSON.** |
| `N-0145` | Maʻa ʻOhana c/o Lani Maʻa Lapilio | an organization **addressed care-of a named individual**. |

> **Promoting all 8 would put two named individuals into the entity spine as
> organizations, and add two duplicates.** The three DOI-notification rows are
> individuals who filed a notification with the Department of the Interior —
> that is a person appearing on a public list, not an NHO. `N-0145` is a real
> ʻohana entity whose registry line carries a person's name in the `c/o`; mint
> the entity, not the person, and do not carry the individual's name into
> `canonical_name`.

**Safe to mint: 3.** Duplicates: 2. Artefact: 1. Natural persons: 2 (plus one
care-of line needing the person stripped).

## 4. Three NHOs in the owner rulings exist in neither register nor spine

From `review/owner_rulings_cedar_recon_v1_2026-08-28.json`:

| ruled entity | obligations | in register? | in spine? |
|---|---:|---|---|
| The Hana Group | $162M | no | no |
| HONUʻAPO | $156M | no | no |
| The Hawaii Pacific Foundation, Inc. | $111M | no | no |
| Native Hawaiian Community Development Corporation | $158M | ~`N-0003` | no |

**$587M against organizations the roster has never heard of.** These are the
strongest evidence yet that 210 understates the NHO universe — they were found
by ruling on contract dollars, not by roster work.

## 5. The ʻokina is U+2018, not U+02BB

Hawaiian names in the register use **U+2018 LEFT SINGLE QUOTATION MARK** where
the ʻokina (**U+02BB MODIFIER LETTER TURNED COMMA**) belongs — verified on
`N-0048` and `N-0145` by codepoint.

**This is not mojibake.** A first look at these names in a Windows console
rendered them as `Nae?ole` and I nearly reported an encoding bug; a codepoint
check showed the file is clean UTF-8. The characters are intact, they are just
the wrong character.

It still matters: a search or join using a correctly-typed ʻokina will not match
these rows, and neither will one using a plain apostrophe. Normalise all three
to one form before matching, and prefer U+02BB when writing a canonical name —
it is a consonant in Hawaiian, not punctuation.

## 6. One competing writer, now resolved

`nho_verified_entities.csv` had two wholesale writers, `06_verify_nho_via_8a.py`
and `19_rebuild_nho_layer.py`, with no declared ordering — whichever ran last
won. **06 is archived** (`graveyard/2026-08-28_nho_disproven_8a_inference/`):
its central inference, that an active SBA 8(a) certification proves NHO
ownership, is recorded as disproven in 19's own docstring, with a named
counterexample (HALOA CONSTRUCTION LLC — 8(a) certified, family-owned, no NHO
parent).

## What to do, in order

1. **Mint 3 entities** — Hoʻopale Foundation, Kalaimoku Foundation, Council for
   Native Hawaiian Advancement. Owner-ruled or well-established.
2. **Alias, do not mint,** `Hui Huliau Inc` → `NHO-HUIHUL-00`.
3. **Drop `N-0170`** as a parsing artefact and fix the page-break split that
   produced it, or it returns on the next parse.
4. **Rule on the three natural persons.** They are on a DOI notification list.
   The question is whether a person who notified DOI belongs in an entity
   registry at all — and the answer is probably a separate person layer with its
   own publication rules, not a row in the NHO spine.
5. **Mint the 4 ruling-sourced organizations** ($587M) once someone confirms
   they are NHOs rather than NHO-owned firms — the rulings say `nho`, but the
   distinction between an NHO and a business it owns is exactly the one this
   layer keeps losing.
6. **Give `nho_verified_entities`, `nho_parents` and `nho_register` a
   spine-joinable id.** Until then the layer cannot be measured honestly.

## What this does not answer

Whether 210 is the right universe at all. The register is a compilation of a DOI
notification list and owner rulings; there is no authoritative NHO roster
equivalent to the BIA list for tribes. Item 4 above found four organizations
worth $587M outside it in a single afternoon's rulings, which suggests the
universe is materially larger and the boundary is not currently defined
anywhere.
