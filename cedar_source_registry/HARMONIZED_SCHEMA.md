# Cedar Harmonized Dataset — Two-Layer Model

The harmonized dataset has exactly two layers. Nothing else sits between the raw
scrape and the entity a user sees.

```
raw snapshots  →  LAYER 1: source_records   →  LAYER 2: harmonized_entities
(immutable)       one row per business          one row per resolved business,
                  appearance in one source      built ONLY from layer-1 rows
```

Files in this package:

| File | What it is |
|---|---|
| `schema/source_record.schema.json` | JSON Schema for layer 1 — formalizes the workbook's "Recommended Schema" sheet |
| `schema/harmonized_entity.schema.json` | JSON Schema for layer 2 — the entity template |
| `templates/source_record.example.jsonl` | Worked layer-1 examples (real Tulalip record + illustrative cross-reference) |
| `templates/harmonized_entity.example.json` | Worked layer-2 example merging those records |
| `templates/source_record.header.csv` | Empty CSV header for layer-1 exports |

## Layer 1 — source_records (the assertion layer)

One row = one business's appearance in one source. This layer is append-mostly
and never "corrected" by other sources: a Tulalip record says what Tulalip says,
a chamber record says what the chamber says, forever. Fields are the workbook's
Recommended Schema, with three enum values added on the strength of Wave 5 page
inspection: `relationship_basis` gains `spouse` (BBNC admits spouse-owned
businesses) and `operated_by` (Koniag admits operated-not-owned businesses), and
`identity_scope` gains `shareholder_spouse_descendant`. These are recorded, never
collapsed into ownership.

Layer-1 invariants:
- `business_source_id` is stable and never reused.
- `*_raw` fields are exact source text; normalized/derived fields never replace them.
- `record_hash` changes iff the source's content for this record changes.
- `cross_reference_only = true` rows can propose matches; they can never
  originate a tribal-ownership assertion (matching rule 4).

## Layer 2 — harmonized_entities (the entity layer)

One row = one resolved business. An entity is a *view over layer-1 rows*, plus
resolution metadata. It contains no facts of its own — every canonical value
carries provenance back to a `business_source_id`, and every identity claim is
an assertion object, not a flag.

The load-bearing design decisions, each derived from the registry's matching rules:

1. **Identity is an array, never a boolean.** `identity_assertions[]` holds one
   object per contributing source claim (scope, relationship basis, affiliation,
   verification basis, priority class, as-of date). The single derived field
   `native_ownership_status` is an enum computed strictly from the controlling
   assertion's priority class:
   - `tribal_primary_asserted` — a Tribal Primary source asserts it (rule 1)
   - `tribal_secondary_asserted` — best evidence is Tribal Secondary; caveat travels (rule 2)
   - `cross_reference_only` — only cross-reference evidence exists; NOT an ownership claim (rule 4)
   - `relationship_not_ownership` — best evidence is a spouse/operated-by/family relationship
   - `conflicting` — open conflict between assertions at the same precedence
   - `unknown`
   There is deliberately no `true`.

2. **Conflicts persist (rule 5).** When assertions disagree, the losing value is
   not deleted — it stays in layer 1 and is indexed in the entity's
   `conflicts[]` with the competing values, their precedence ranks, and an
   open/resolved status. `assertion_precedence_rank` orders review; it never
   authorizes deletion.

3. **Field-level provenance.** Canonical contact/descriptive fields
   (name, address, phone, email, website, description) are selected by
   precedence-then-recency, and `field_provenance` maps each populated field to
   the `business_source_id` that supplied it. If you can't say where a value
   came from, it doesn't go in the entity.

4. **Nations are edges, not labels.** `nations[]` links the entity to canonical
   `nation_id`s with a per-edge `relationship`
   (`citizen | descendant | shareholder | spouse | operated_by | asserted_unspecified`)
   and the evidence records behind it. A Tulalip TERO record for a Klamath-affiliated
   firm yields a Klamath edge — the certifying tribe and the affiliation tribe
   are different facts (Tulalip's `tulalip_owned_%` measures Tulalip-member
   ownership only).

5. **Certifications roll up without merging.** `certifications[]` keeps one
   object per certifying source (number, tier, dates, event status,
   `is_current`). Two tribes certifying the same firm = two objects.

### Merge procedure (deterministic, re-runnable)

1. Candidate generation: certification_number ≫ exact website/email/phone ≫
   normalized name + locality ≫ fuzzy name (review queue). Record every accepted
   link in `match_edges[]` with method, confidence, run id, and reviewer.
2. Canonical field selection: for each field, take the value from the highest
   `assertion_precedence_rank`; break ties by most recent `last_seen`. Log
   displaced values to `conflicts[]` only when they *disagree* (not when merely absent).
3. Identity derivation: compute `controlling_assertion_id` and
   `native_ownership_status` per the enum above. Cross-reference rows never
   participate in this step except to attach as corroboration
   (`matched_primary_source_ids` on the layer-1 row).
4. Currency: entity `is_current` = any contributing assertion `is_current`.
   A record vanishing from a source flips that assertion, not the entity's history.

### Do not

- Do not store an ownership boolean anywhere in layer 2.
- Do not let a chamber, state-certification, or ANC record set or upgrade
  `native_ownership_status`.
- Do not map `spouse` or `operated_by` relationships to any ownership status.
- Do not resolve a conflict by deleting a layer-1 row.
- Do not emit an entity with an empty `source_record_ids` or missing `field_provenance`.
