# Dataset discovery — 2026-09-04 round: validation infrastructure

Frame: registries that VERIFY a business claim (existence, standing,
ownership) rather than enumerate Native businesses. 2 rows in
`dataset_discovery_2026-09-04.jsonl` (WebSearch-only; URLs literal).

## One live path, one closed one

- **OpenCorporates** — the aggregation layer over all 50 states' SOS company
  registers (~100M companies, ~190M officers), with bulk/API for some states.
  This is the entity-resolution spine's **corroboration layer**: match a
  candidate Native business to its state registration to confirm it exists
  and pin the canonical name/address. Hard limit: US state records do not
  carry beneficial ownership, so it validates the *entity*, never Native
  *ownership*.

- **FinCEN BOI (Corporate Transparency Act)** — would have been the one
  federal registry of who actually owns a company. **Path closed:** the
  2025-03-26 interim final rule exempts all US-created entities from
  reporting; "reporting company" now means only foreign-formed entities.
  Domestic tribally-owned and individually-Native-owned firms do not file,
  and filed BOI was never public. Recorded so it is not chased.

## Side lead worth a future frame

The CTA's "reporting company" definition explicitly names filing with "a
secretary of state or similar office" of a **Tribal jurisdiction** —
confirming some tribes run their own business registries that function like a
state SOS. Those tribal registries are an ENUMERATION lead (not validation),
and a candidate for a later discovery round.

## Discipline

Both are validation tools, not Native-business rosters. The binding
do_not_infer: **registration is not ownership** — an entity existing, or an
officer name matching, corroborates identity resolution but never asserts
tribal citizenship or an ownership share. No registry rows added.
