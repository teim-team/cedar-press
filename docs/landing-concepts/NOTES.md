# Landing page redo — concepts and wiring notes

Owner brief (2026-09-02, voice): redo the landing entirely. Not "numbers in
text" — something beautiful where the figures update off the real datasets
and **flutter when updates land**. One full page; a button to Tribal Business
News for non-subscribers, sign-in for subscribers (hamburger is fine). The
feeling to hit: *"there's an immense amount of live value behind this door."*

Three working concepts live next to this file — each is a self-contained
HTML page (open in a browser; they animate). All three share the same
figures, chrome, and honesty rules; they differ in what the hero *is*.

## The three concepts

### A — The Ledger (`concept-a-ledger.html`)
The record stream is the page. Four columns of **real rows from the sample
files** (Bowhead FY2023, the Yurok forestry award, ONRR royalties, NAGPRA
notices…) drift slowly behind one enormous cycling figure. Every ~5s the
figure rolls to the next stat with an odometer flutter, a chip names what
just arrived ("+118 contract actions · just landed"), and one row in the
wall lights up as "the record arriving." Feels like standing in front of
the ledger itself. Risk: the wall must stay quiet enough not to fight the
figure (opacity is the whole game).

### B — The Constellation (`concept-b-constellation.html`)
The product's core claim is entity resolution, so the hero is the graph:
a living canvas constellation (hub nodes = nations/corporations, small
nodes = businesses/records) where a pulse traveling down an edge is a
record being connected. Each pulse pushes a plain-language connection into
a side ticker ("BOWHEAD PROGRAM MGMT → Ukpeaġvik Iñupiat Corporation ·
FY2023 contract") and flutters one of the four stats stacked beside the
headline "Every record, connected to the nation it touches." The most
distinctive of the three — nobody else's landing page can honestly show
this, because the connections are Cedar's work.

### C — The Rising Curve (`concept-c-curve.html`)
The light, editorial one. A full-viewport area chart sweeps FY2000 → today
on load and the $176.7B figure rides the end of the curve, rolling up as
the sweep completes. Supporting stats run as a band along the bottom;
"LATEST RELEASE · +$41.2M" pulses at the curve tip. The wow is **time
depth**: twenty-five years, maintained. Cheapest to make fully real —
the curve is one fiscal-year series the contractors dataset can emit.

**Hybrid worth considering:** C's rising curve as the hero with A's record
wall ghosted faintly behind it — depth of time and depth of volume at once.

## Honesty rules (all concepts)

- Figures are the data project's published totals only (see
  `src/features/grove/pressStats.js` for provenance and the totalling
  traps). No improvised sums, no entity counts on the door.
- Flutter fires on **real release events**, not a fake ticker. The mockups
  simulate a release every few seconds to show the motion; production
  flutters when the stats payload actually changes, plus one staged
  roll-up on first paint (which is honest: the page is catching you up).
- The cadence line stays: "figures update weekly · as of {date}."

## Wiring architecture (when the datasets are ready)

1. **The data side emits a stats manifest** alongside each release —
   `stats.json`: `{as_of, figures: {contracting_usd, subaward_usd,
   assistance_transactions, deal_transactions, total_rows}, deltas:
   {since_last_release: …}, series: {contracting_by_fy: […]}}`.
   Totals computed under `MONEY_TOTALLING_RULES.md` *at build time* — the
   website never sums anything.
2. **The platform serves it** at something like `/api/press/stats`
   (server/cedar_press already owns the collection descriptors; this is
   the same handshake as `data/cedar/collection_descriptors.json`, one
   file further).
3. **The landing fetches on load**; the flutter component compares the
   payload's `as_of` to what it rendered and rolls any figure that
   changed. Optional later: poll hourly, or SSE, but weekly data makes
   polling on page-load sufficient — no live socket needed to be honest.
4. Until 1–3 exist, `pressStats.js` stays the hand-synced source (as
   noted in that file, refreshing it *is* the weekly update).

**What to ask the data project for, per concept:**
- A (Ledger): a curated "recent rows" feed (the sample-file discipline:
  publishable, no natural persons, spread not head()) + per-release deltas.
- B (Constellation): nothing new — the graph can be decorative-but-truthful
  with only the connection examples; a real "recently resolved" feed makes
  it fully honest.
- C (Curve): `contracting_by_fy` (additive firm-grain family per fiscal
  year). The mockup's curve shape is illustrative and must be replaced
  before shipping.
- A map hero (discussed, not built): needs state-level aggregates with the
  suppression rules already used in natural-resources; park until the data
  side emits them.

## Product/navigation decisions to make with Havala

- The new landing becomes the **public front door** (replaces the split
  PressGate hero); sign-in moves behind the hamburger + a quiet button,
  and the access panel becomes its own screen/route rather than sharing
  the first viewport. PressGate's activation flow, tribal-request and
  research-access links survive in the hamburger and page footer.
- Signed-in readers should never see the door: route them straight to the
  hub as today (`canReadCedarPress` already decides this).
- The four-pillars grid, catalog names, and credibility strip move below
  the fold (page two of the scroll) or onto Methods — the door leads with
  the data, the trust case follows it.
- Reduced-motion: every concept needs a `prefers-reduced-motion` variant
  (static figures, no drift/pulses) before any of this ships.
- Mobile: A and C degrade naturally (fewer wall columns; chart under the
  headline). B needs the graph pushed behind the panel at phone widths.
