# Dataset discovery — 2026-09-03 round: Native agriculture, tourism & arts registries

Frame: sector registries that enumerate Native-owned businesses in food/ag,
tourism, and arts. 3 rows in `dataset_discovery_2026-09-03.jsonl`
(WebSearch-only; URLs literal from results).

## The three pillars, ranked by identity strength

1. **IACB Source Directory** (federal, DOI) — the strongest cross-reference
   found in any discovery round: listing requires enrolled membership in a
   federally recognized tribe (or a tribal enterprise), and it backs the
   Indian Arts and Crafts Act enforcement regime. 500+ businesses.
2. **IAC American Indian Foods trademark directory** — certification-based
   with a real ownership rule (tribal member/entity or ≥51% controlling
   interest); 500+ licensed users since 1993.
3. **AIANTA / DestinationNativeAmerica.com** — tourism listings, curated by
   outreach with no stated ownership threshold; weakest basis, but fills the
   hospitality gap.

## Why this frame matters

The first two have **verified or certified** ownership bases, unlike the
chambers (membership) and the state DBE/USAspending flags (self-cert). They
sit high in the evidence hierarchy for a cross-reference — closer to the TERO
tribal-primary rosters in trustworthiness, though still directories, not the
nations' own certifications.

## Boundaries (do_not_infer)

- **Mixed ownership classes** in all three: tribal enterprises/cooperatives
  (tribally_owned) sit next to individually owned businesses — label per
  entry, never bulk-assign.
- **Person boundary** on the individual-artist (IACB) and individual-producer
  (IAC) rows — not ingestible pre-FIELD_CLASSIFICATION.
- **Do not construct URLs**: DestinationNativeAmerica.com appeared only as
  prose, not a linked result — confirm at first fetch.

All three are Cross-Reference candidates for the next registry wave; no rows
added this round.
