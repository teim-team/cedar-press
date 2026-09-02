# Dataset discovery — 2026-09-02 (2nd round): tribal enterprise holding companies

Frame: the corporate vehicles nations create to hold and operate their
non-gaming businesses. 4 rows in `dataset_discovery_2026-09-02b.jsonl`
(WebSearch-only; every subsidiary name and URL literal from results).

## Why this is its own source class

Every registry source so far that lists *businesses* lists **individually
owned** ones (TERO rosters, chambers, licence registers). Holding companies
are the other half of Indian Country's business economy: enterprises the
**nation itself owns**, rolled up to the government that owns them. Their
public "companies / investments / portfolio" pages enumerate the
tribally-owned enterprise layer directly — and the federal-contracting
subsidiaries (Ho-Chunk's Flatwater Group, all of CNI) cross-walk straight to
USAspending's "Tribally Owned Firm" recipient flag, giving a second,
independent check on that layer.

## The four

- **Ho-Chunk, Inc.** (Winnebago Tribe of NE) — subsidiary pages across
  hochunktrading.com / flatwater-group.com.
- **Chickasaw Nation Industries** — a full companies list at
  chickasawfederal.com/companies; large federal portfolio.
- **Mno-Bmadsen** (Pokagon Band) — six named portfolio sectors at
  mno-bmadsen.com/investments.
- **Waséyabek** (Nottawaseppi Huron Band) — ~32 companies, but no single
  list page; must be assembled from dated acquisition posts (honest partial).

## The binding caveat (do_not_infer)

These are **tribally_owned**, never individually owned — the opposite
ownership class from the TERO rosters, and the two must not be merged. Two
finer traps recur: **joint ventures / minority stakes** (CNI's JV LLCs,
Waséyabek's co-investments with another nation's vehicle) are not 100%
single-nation ownership; and a **subsidiary's legal name routinely shares no
token with its owner**, so resolution is by declared parent, never by name
match. All four are Cross-Reference candidates for the next registry wave;
no rows added this round.
