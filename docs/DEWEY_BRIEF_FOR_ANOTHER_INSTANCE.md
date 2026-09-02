# Dewey Data — brief for another Claude instance

*Written 2026-08-12 from the Cedar Press build terminal. Hand this whole file to
the new instance. It assumes no prior context.*

---

## THE ACTUAL PURPOSE — read before the licensing section

**Elijah's intended use is RESEARCH, not resale.** In his words:

> "i ultimately want to use the data to produce a methodology paper for Harvard
> so it is for research, for Lumecon … if we create multipliers and leakage
> calculations for reservations that is also what i want to test out … build off
> of tribal economic zones from CICD which just has inflow, but this can also
> model inflow and for more sectors and communities."

**This changes the licensing question fundamentally, and you must not conflate
the two uses.** There are three distinct things, and most academic data licences
treat them very differently:

| use | typical academic licence treatment |
|---|---|
| **Publishing research findings and derived aggregates** (a methodology paper, multipliers, leakage coefficients) | **normally PERMITTED** — this is what an academic subscription is for |
| **Redistributing the underlying records** (shipping Dewey rows in a Cedar Press product) | **normally PROHIBITED** |
| **Commercial use** (Lumecon consulting deliverables) | **usually a SEPARATE licence tier** — academic ≠ commercial |

So the honest reading is: the methodology paper is very likely fine; a Cedar
Press data product containing Dewey-derived rows is very likely not; and
**Lumecon is the genuinely ambiguous middle** — an academic subscription used to
produce commercial consulting output is the clause to read most carefully.

**YOUR PRIMARY DELIVERABLE IS THE LICENCE READING ITSELF.** Go to the terms for
each subscribed product and quote them verbatim on exactly these four points:

1. May derived statistics and aggregates be published?
2. Is there a minimum aggregation threshold (e.g. no cell with fewer than N
   establishments) before a figure may be shown?
3. Is commercial use permitted, or is the subscription academic-only?
4. What attribution is required, and in what form?

Do not paraphrase. Elijah needs the actual sentences, because a methodology
paper for Harvard has to state its data provenance and access terms accurately.

### The substantive research goal, so you know what to look for

He wants to build **regional multipliers and leakage estimates for reservation
economies** — how much of a dollar spent on a reservation stays there versus
leaks to off-reservation businesses. The existing CICD tribal-economic-zones
work measures **inflow only**. He wants **inflow and outflow, across more sectors
and more communities.**

That makes **origin-destination visit data the single most valuable thing in the
Dewey catalogue** — where visitors to a reservation POI come from, and where
residents of a reservation travel to shop. Leakage is literally an
origin-destination question. Prioritise any product with home-census-block-group
or origin-tract fields over one with visit counts alone.

Cedar Press already holds two things that pair with this directly: LODES
block-level worker flows, and a NaNDA-vs-host-county reservation industry mix
built for exactly this purpose. Check `MASTER_DATA_INVENTORY` before pulling
anything, per house rule.

---

## THE LICENSING GATE — for the Cedar Press product, not the paper

**Dewey is a licensed data marketplace, not an open source. Nothing pulled from
it may ship in a Cedar Press product until Elijah confirms a redistribution
entitlement in writing.** This constrains the *product*; it does not constrain
the research paper, which is governed by the reading you are about to do.

Cedar Press already has a precedent for exactly this, and it is binding:

> **Casino City may be read for QA and may never be published or resold.**
> — `docs/GAMING_SPEC_RECONCILIATION.md`

That rule exists because Cedar Press discovered, late, that its own 774-property
gaming universe was vendor-derived (595 properties carry a `casino_city_id`;
all 64,181 capacity observations cite the vendor panel). The fix was to keep the
IDs and **replace the evidence under them** with free official sources. Repeating
that mistake with Dewey would be worse, because Dewey products carry explicit
licence terms and an academic subscription almost never includes redistribution.

**Default posture: Dewey is an INTERNAL QA LAYER.** It validates Cedar Press
figures; it never publishes. The mechanism that enforces this already exists —
`code/87_build_dataset_notes.py` holds a `LICENSED_SOURCE_FILES` gate, and a file
listed there gets no notes contract and therefore **structurally cannot ship**.
Any Dewey-derived file you create must be added to that list on creation, not
later.

If Elijah says he has a redistribution entitlement, get the specific product
name and the specific licence clause. "I have a subscription" is not an
entitlement to resell.

---

## What Elijah wants

Access via **API key**, not browser clicking. He is logged into
`https://app.deweydata.io/discover` in Chrome. The discover page advertises a
**Dewey MCP connector**, which is the preferred route — headless, reproducible,
and it enumerates exactly which datasets his subscription entitles him to.

**He has not generated an API key yet.** Generating one changes his account
settings, so **ask before doing it, or let him click it himself.** Same for
accepting any terms, starting any trial, or subscribing to any dataset —
all of those are his call, not yours. Do not click them.

---

## Step 1 — establish what the subscription actually covers

This is the single most valuable thing you can do, and it must come before any
pull. Cedar Press has a standing distinction that applies directly:

| state | meaning |
|---|---|
| `PUBLISHES` | source makes it available and we have it |
| `WITHHOLDS` | source has it and refuses to release it |
| `NOT_FOUND` | we looked and it does not exist |
| `NOT_CHECKED` | we have not looked |

**A dataset visible in Dewey's catalogue but not covered by his subscription is
`WITHHOLDS`, not `NOT_FOUND`.** Record the difference. An empty result that does
not say which of the four states it is in is worse than no result.

Write the inventory to `review/dewey_catalogue_2026-08-12.csv` with at minimum:
product name, provider, whether subscribed, temporal coverage, geographic grain,
unit of observation, and licence/redistribution terms **quoted verbatim**.

---

## Step 2 — what is actually worth having

Ranked by what it adds to Cedar Press, which is a dataset venture on the **Native
economy** (tribal governments, Alaska Native corporations, Native Hawaiian
organisations, and their enterprises).

1. **Origin-destination foot traffic (Advan, SafeGraph lineage) — THE TARGET.**
   Monthly visits per POI, and critically the **home census block group of the
   visitors**. Two payoffs at once: Cedar Press holds **774 gaming properties**
   with no demand-side measure of any of them, and the origin field is what makes
   the leakage/multiplier research possible at all. A product with visit counts
   but no origin field is worth far less for the paper. Most licence-encumbered
   item in the catalogue; treat product use as QA-only until the licence is read.
2. **POI / places reference data (Placekey).** A crosswalk between Cedar Press
   property IDs and a widely used POI key would be genuinely useful even if the
   visit data itself can never ship, because a crosswalk is our own work.
3. **Employment / business establishment panels.** Cedar Press deliberately keeps
   *multiple independent* employment figures per property rather than forcing one
   number. A Dewey establishment panel is another independent figure — valuable
   precisely because it disagrees.
4. **Consumer spending / transaction panels.** Interesting, but tribal enterprise
   revenue is the thing Cedar Press has explicitly refused to estimate. See the
   hard rules below before touching it.

---

## Step 3 — the rules you must not break

These are Cedar Press house rules, learned the expensive way. They are in
`AGENTS.md`; the ones that bear on Dewey work:

- **Never estimate revenue IN A CEDAR PRESS DATASET.** Elijah's exact words:
  *"i'd rather someone else estimate revenue than us."* Foot traffic times an
  assumed spend-per-visit is an estimate wearing a costume. Anything written into
  `data/clean/` must be exact arithmetic from a published figure and a published
  rate, typed as such.

  **The research paper is the opposite case and must not be strangled by this
  rule.** Multipliers and leakage coefficients ARE estimates — that is what a
  methodology paper produces, and estimating them is the entire point. The line
  is the artifact, not the arithmetic:

  | artifact | estimates allowed? |
  |---|---|
  | `data/clean/*.csv` shipped to subscribers | **no** — measured or exactly derived only |
  | the Harvard methodology paper and its outputs | **yes** — with stated assumptions and sensitivity |

  Keep them in separate files. A modelled multiplier must never be written into a
  published Cedar Press table as though it were an observation.
- **A modelled number is never stored beside a measured one without a type
  column.** Dewey panels are frequently modelled/extrapolated from a sample. If
  the product documentation says "modelled", that word goes in the data.
- **Absence in a source is a property of that source.** A casino with no Dewey
  POI record is not a closed casino.
- **Ownership is never collapsed with service.** Cedar Press keeps
  `parent_native_entity` and `serves_native_entities` strictly separate. A POI
  located on tribal land is not a tribally owned business.
- **Do not create a second property universe.** Attach to existing Cedar IDs
  (`CCP-`, `VP-`, `TPL-`). A vendor using a different name for a property is an
  **alias**, not a second property.
- **Provenance columns are mandatory** on anything written: source URL, fetched
  date, and a verbatim quote or product identifier. Cite the primary source,
  never a hand-built filename.
- **Never overwrite a historical observation.** Observations are dated rows.

---

## Step 4 — practical notes

- **Python, not R.** Cedar Press pipelines are Python for maintainability.
  Invoke as `py -3`. There is a `deweydatapy` package on PyPI (Dewey's own
  client); it is **not currently installed** — installing it is fine, it is a
  normal dependency, but say so in your report.
- **Cedar Press is self-contained by rule.** Copy raw data into
  `C:\Users\esm247\Desktop\Cedar Press\data\raw\external\dewey\`. Never leave a
  pipeline reading from a path outside the project at runtime.
- **One poller per host.** Do not run parallel pullers against Dewey.
- **The machine is busy.** As of writing, 8 OCR shards and a USAspending archive
  puller are running. Do not add heavy parallel work without checking.
- **A backoff bounds the RATE, not the RUN.** Any long pull needs a wall-clock
  `RUN_DEADLINE` and must stop on the first refusal rather than retry into a ban.
- **USAspending's `bulk_download` service was returning `failed` on every job on
  2026-08-12** — unrelated to Dewey, but if you see Cedar Press subaward gaps,
  that is why. Don't try to fix it.

---

## What to report back

1. The catalogue inventory, with subscribed vs not clearly separated.
2. **The licence terms, quoted.** This is the deliverable that unblocks
   everything else.
3. A recommendation on whether any Dewey product can ship, or whether the whole
   connection is QA-only.
4. What you did **not** do and why — Cedar Press treats a documented refusal as
   equal in value to a build. Recent examples: California produced zero derived
   revenue rows because every rate was marginal; Florida built a revenue bound
   and then killed all 44 rows when the state's own figures falsified it.

**Do not purchase, subscribe, accept terms, or start a trial. Those are Elijah's
decisions.**
