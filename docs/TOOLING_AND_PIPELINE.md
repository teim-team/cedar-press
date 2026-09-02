# Tooling and the Review Pipeline

*Written 2026-08-06 in answer to: "check if there are any python tools that can
help you... i suspect we are underutilizing a library here and the goal is to
have apis and sustainably update the datasets and a process to clean them and
then leave them for human review."*

You are right. The matcher in this project is hand-rolled, and while it now
encodes a lot of hard-won judgement, the *machinery* underneath it is doing by
hand what mature libraries do better.

---

## What is actually installed

```
INSTALLED : rapidfuzz, networkx, pyarrow
MISSING   : recordlinkage, splink, dedupe, jellyfish, duckdb, polars,
            pandera, great_expectations, tenacity, requests_cache,
            pydantic, fastapi, usaddress, probablepeople
```

Two of the three installed are being wasted:

- **`rapidfuzz`** is present and unused. Every fuzzy comparison in the project
  is a hand-written token-set intersection. `rapidfuzz` is C++-backed and does
  token-set ratio, partial ratio and a batched `cdist` that would replace the
  O(n×m) Python loops in `resolve_entity` outright.
- **`networkx`** is present and unused, and this is the bigger miss. The FPDS
  `ultimate_parent_uei` graph *is* a graph — parent, child, sibling, and
  multi-level chains like RiverTech → Akima → NANA. We walk it with dictionaries
  and `defaultdict(set)`. `networkx` gives connected components, ancestor
  resolution and cycle detection for free, and cycle detection matters: 528 of
  4,023 recipients (13.1%) report more than one parent, which is either an
  ownership change or a data error and is currently invisible.

## The one that matches what you actually asked for

**`dedupe`** is active-learning record linkage. You label candidate pairs; it
trains a model on your labels and applies it at scale, and it asks for the
labels that most reduce its uncertainty rather than a random sample.

That is precisely the loop you described — *"i can write a note on top of
selecting an option so you actually learn and your % confidence"*. Today the
review page shows a confidence measured from your past rulings, but the matcher
does not learn from them; a human (me) reads your notes and hand-writes a rule.
`dedupe` closes that loop mechanically.

**`splink`** (UK Ministry of Justice) is the heavier alternative: probabilistic
Fellegi-Sunter linkage on a DuckDB or Spark backend, with the m/u probabilities
estimated by expectation-maximisation and genuinely calibrated match weights.
It scales past `dedupe` and would give real probabilities rather than the
heuristic percentages currently on the cards.

**Honest caveat:** neither replaces the judgement already encoded here. No
trained model would have known that Bristol is Choggiung and not Bristol Bay,
that Alutiiq is Afognak's contracting brand, or that a village corporation is a
different legal person from its namesake government. Those came from you. The
libraries make the *mechanical* half faster and better calibrated; the
jurisprudence stays.

## The rest of the stack worth adding

| Need | Library | Why |
|---|---|---|
| Query the clean layer | `duckdb` | Reads CSV/Parquet directly, no server. The 6.6M-row subaward pull is already past comfortable CSV scale. |
| Columnar storage | `polars` + `pyarrow` | `prime_contracts.csv` is 221 MB; Parquet would cut it and load in a fraction of the time. |
| Schema validation | `pandera` | The 112-vs-105 column drift between the funding pull and the spine would have been caught at read time instead of by hand. |
| HTTP retries | `tenacity` | Exponential backoff as a decorator, which is rule 3 of `PULL_DISCIPLINE.md` written once instead of in every puller. |
| Response caching | `requests_cache` | Re-running a scrape would stop re-hitting hosts that have already rate-limited us. |
| API surface | `fastapi` + `pydantic` | The subscriber-facing API, with the codebook's `access_tier` enforced as a response model rather than by convention. |

---

## The review page belongs in the app, not in an artifact

The current page is a self-contained HTML file republished to a new URL each
build. That was right for iterating in a day, and it is wrong as a permanent
process, for reasons that have already bitten:

- **State lives in `localStorage`,** so a new URL starts empty. Rulings survive
  only because already-ruled items are suppressed at build time — which works,
  but means un-exported work can be lost.
- **Export is copy-paste** into a CSV, then a script reads it. Every hop is a
  chance to lose a batch.
- **Republishing interrupts you.** You asked for one stable page for a day
  precisely because of this.

What it should be, in the teim app under Lumecon branding:

1. **Postgres-backed queue.** A ruling is a row written on click — no export
   step, no localStorage, no lost work.
2. **Server-side suppression.** Ruled items leave the queue on the next request
   rather than at the next rebuild, so the page never asks twice.
3. **Notes as first-class.** A note that states a rule ("Alutiiq is Afognak's
   contracting brand") should create a *brand rule* record, not a text blob a
   human later reads. That is what makes the review compound.
4. **Weekly refresh cadence.** Federal Register is daily, USAspending lags ~4
   weeks, lobbying is quarterly, IRS 990s are annual. A weekly build is right
   for the queue; per-dataset refresh should follow the source, not the page.
5. **Brand-locked.** Inter, teal, no em dashes, no "engine"/"infrastructure" —
   the Lumecon rules already recorded.

**Not yet verified:** the `gh` CLI is not installed on this machine, so the
Cedar Press mockup in the teim organisation has not been read. The IA above is
inferred from how the review page is actually used, not from that mockup, and
should be reconciled against it before anything is built.
