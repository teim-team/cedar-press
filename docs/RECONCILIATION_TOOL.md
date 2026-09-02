# The entity reconciliation tool — how it works, and how to keep it running

*Written 2026-08-26. The tool is the published Artifact at
`https://claude.ai/code/artifact/dafb2a1a-7854-40d8-88cc-ce66916ab08d`.
Rebuild it with `build_recon2.py` + `recon_template.html`.*

---

## What it is for

Adjudicating unmatched identifiers in federal prime contracting. Cedar Press
holds **328,906 unattributed rows on 9,385 identifiers carrying $65.24B**. No
algorithm resolves those — the measured discovery work says contracting has an
**adjudication problem, not a discovery problem**: 94.2% of the gap is already
on file at tier C, harvested and never ruled.

So this tool exists to turn a human's knowledge into tier-A attributions, at the
highest dollar-per-decision available.

---

## THE WORKFLOW — three steps, and completion is separate from classification

This was wrong in the first build and is the most important thing to preserve.

1. **Classify** — Tribe / ANC / NHO / Individual Native / Not Native.
   Keyboard `1`–`5` on the card in view.
   **This does NOT clear the card.** The card turns amber and stays in the queue.
2. **Name the entity** — the free-text field. For Tribe, ANC and NHO this is the
   whole point: a class without an owner is not an attribution, it is a
   category. `Not Native` and `Individual Native` legitimately have no entity.
3. **Complete & clear** — the explicit button. Only this removes the card.

**Why the split matters.** In the first build, classification cleared the card
immediately. A ruling of "ANC" with no entity named is not applicable — nothing
downstream can act on it — so the queue was consuming decisions and producing
nothing usable. Classification is a judgement; completion is a commitment. Keep
them apart.

Filters: **Open** (not completed) · **In progress** (classified, not completed) ·
**Completed** · **8(a) families** · **Self-certified** · **Already ruled**.

---

## THE EXPORT MUST CARRY IDENTIFIERS

The first export emitted `name` and no identifier. Applying it back would have
meant **name matching** — the exact defect this project has failed at ten
distinct ways. Fixed: every exported ruling now carries `cluster_key`, the full
`uei` and `cage` lists (semicolon-joined, one cluster can hold many), and
`n_identifiers`.

**Never accept a ruling export without an identifier.** A name is not a key.

---

## CLUSTERING — one ruling clears a family

Cards are **clusters**, not rows. 9,385 identifiers collapse to 8,876 clusters,
**353 of them multi-identifier**. Joined on normalised name, and on shared
name-stem plus city.

This is the 8(a) successor pattern: the programme's term is nine years, so
tribes and ANCs stand up successor entities sharing a name and address with new
identifiers. Many-identifiers-to-one-entity is **expected**;
one-identifier-to-many-entities is a defect and goes to review.

Each card lists every member with its own obligations and row count, all
copyable, plus an "All ids" button. **Check the member list before ruling** — a
name-stem-plus-city join can merge unrelated firms in a big city, and the table
is there so a bad merge is visible rather than hidden.

Known limit: `prime_contracts.csv` carries city and state but **no street
address**, so "same address" is approximated. The SAM extracts do carry street
and will tighten it.

---

## CONFIDENCE — priced on measured flag semantics, deliberately low

The scores look pessimistic. They are honest. Measured 2026-08-26:

- **`reported_native_preference` is NOT a Native identifier.** It is the union
  INCLUDING 8(a). Genuinely Native-specific set-asides are $1.2005B, 0.49% of
  attributed dollars.
- **8(a) carries no Native signal** — it is open to any disadvantaged owner.
- **Buy Indian is Native-specific** and is the one flag that discriminates.
- **Absence of a flag is not evidence against**: $140.00B of $244.77B attributed
  (57.2%, 565,364 rows) sits on awards with no Native set-aside at all, and
  42.4% of attributed firms are invisible to flag-based discovery.
- **A SAM self-certification is not a determination.** `americanIndianOwned =
  YES` appears on 2,846 of 8,273 rows of the *TRIBAL* extract, so the flags do
  not separate individual from entity ownership. Goldbelt Raven, an ANC
  subsidiary, certifies `alaskanNativeCorporationOwnedFirm = NO`.

Result: 301 of 400 cards sit under 20%. That is the true state of the evidence,
and a card that says so is more useful than one that flatters.

---

## SUPPRESSION — what never reaches the queue

**507 clusters are suppressed as already-ruled.** Sources, in order:

1. `data/clean/cedar_ruling_ledger_consolidated.csv` — 15,587 rulings from 157
   files. Filter on **`outcome`**, never `status`: status says a ruling was
   processed, outcome says what it decided.
2. `prime_contracts.ruling_status` — applied rulings drop out automatically.
3. `review/ancsa_ruling_resolutions_*` and `ancsa_attribution_changes_*`.
4. `review/elijah_rulings_*_recon.csv` — this tool's own output, fed back.

**A ruling queue must subtract already-ruled subjects before a human sees it.**
The 2026-08-12 Schedule I queue asked about 30 EINs already ruled tier X,
including `UNITED WAY OF THE GREATER CHIPPEWA VALLEY` — the case the whole tier
rule was built on. That is the failure this suppression prevents.

---

## EVIDENCE ON THE CARD

- **Your prior ruling**, where one exists, with its date and Cedar's own findings
  against it.
- **The firm's own verbatim ownership sentence** with URL and fetch date — 123
  cards. 22 name a specific nation. 10 are independently corroborated. **1 is
  contradicted by an independent source and is flagged red.**
- **Where the linkage signal comes from**, in plain language, with each flag's
  real meaning stated rather than assumed.
- **The 8(a) family table** where the cluster holds more than one identifier.

Evidence tiers: **A** requires a leg that is not the firm. A SAM flag plus a
company website is *one voice in two venues*, not two sources — govcb, govcon,
opengovus, Buzzfile, LinkedIn and PRNewswire are SAM mirrors or paid placements.
Typing them correctly moved tier A from 39 to 18.

---

## REBUILDING IT

```
py -3 <scratchpad>/build_recon2.py      # writes recon_data2.json
# inject into recon_template.html at the /*__DATA__*/ marker, publish
```

Progress lives in the reader's browser (`localStorage`, key `cedar_recon_v1`),
keyed by the cluster's lead identifier. **Keep the key scheme stable across
rebuilds or progress is lost.**

**Do not republish while the owner is mid-session** unless asked. The owner
asked for this explicitly on 2026-08-26 — republishing rebuilds the page and his
in-browser progress is keyed to the cluster's lead identifier, so a rebuild that
changes the key scheme destroys work he has already done.

**The live watch on the artifact ended 2026-08-27** (connection lost, not
republished). **Absence of a republish notification is not evidence the owner
has not been working in it** — his progress is local to his browser and this
session cannot see it either way. Ask, or read his next export; do not infer.

---

## APPLYING RULINGS BACK — the step that is always skipped

**A ruling that is not applied back to its source table is not a ruling, it is a
note.** Measured: 492 clusters carrying $17.5B had a ruling recorded somewhere
and never written back, so they resurfaced as unresolved. The owner recognised
entities he had already adjudicated — that is what it looks like from the
outside.

Apply with the `124_apply_rulings_in_place.py` pattern. **Never**
`09_import_rulings.py` or `01_build_entity_spine.py` — both rebuild from a stale
upstream and silently drop later work.

Inherit the tier from the ruling. Do not compute it from the method: a RULED
method is not automatically a POSITIVE ruling, and `148_resolve_schedule_i_
recipients.py` published **317** tier-X exclusions as tier-A attributions on
exactly that mistake.

`62_no_regression_check.py` tracks `rulings_unapplied`. It must not rise.

---

## KNOWN LIMITS

- **The queue is structurally FY2000–2022.** All 209,495 FY2023–26 prime rows
  are 100% attributed *by construction* — the archive backfill was
  identifier-seeded, so recent years have no unknowns because nobody looked.
- **Prime contracting only.** Assistance and subawards are separate universes
  with different dollar bases; do not mix them into one queue.
- The top 400 clusters carry $35.81B of the $65.24B. The tail is long and small.
