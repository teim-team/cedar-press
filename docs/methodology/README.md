# Cedar Press methodology papers

*Written 2026-09-02.*

One paper per dataset, thirteen in all. Each is the **methodology record** for
its dataset: what was pulled and from where, how the rows were made, how
entities were attributed, what was decided and why, what the known limits are,
and how often it has to be re-pulled.

| paper | dataset | shelf |
|---|---|---|
| [`contractors.md`](contractors.md) | Federal prime contracting | pro |
| [`subcontracting.md`](subcontracting.md) | Federal subcontracting | pro |
| [`funding.md`](funding.md) | Federal financial assistance | standard |
| [`gaming.md`](gaming.md) | Tribal gaming | grove |
| [`natural-resources.md`](natural-resources.md) | Natural resource revenue | pro |
| [`native-owned-businesses.md`](native-owned-businesses.md) | Native-owned businesses | pro |
| [`nonprofits.md`](nonprofits.md) | Native nonprofits | pro |
| [`deals.md`](deals.md) | Indian Country deals | standard |
| [`lobbying.md`](lobbying.md) | Tribal advocacy and lobbying | standard |
| [`legislation.md`](legislation.md) | Native legislation and votes | standard |
| [`federal-register.md`](federal-register.md) | Federal Register — Indian Affairs | standard |
| [`nagpra.md`](nagpra.md) | NAGPRA notices | standard |
| [`_entity_layer.md`](_entity_layer.md) | The entity spine (dataset 13) | infrastructure |

**These are not the product copy and not the codebooks.** Customer-facing
description lives in `docs/datasets/_descriptors.json`; field definitions live
in `docs/codebooks/`.

**Each paper stands alone.** A reader who picks up `gaming.md` cold should not
have to read `contractors.md` to follow it, so shared context is repeated
inside each paper rather than cross-referenced. The duplication is deliberate.
This README holds only the background that is genuinely common and genuinely
not dataset-specific.

---

## How to read a figure in these papers

- **`[measured]`** — this document re-counted the figure from the live file in
  `data/clean/` on **2026-09-02**, with `csv.reader`, streaming the whole file
  rather than sampling. Where a build log and the data disagreed, the
  measurement won and the disagreement is recorded in each paper's *Stale
  claims found while writing this*.
- **`[from the record]`** — taken from a build log, a docstring or an ADR
  without independent measurement, usually because it describes a historical
  state, a source's behaviour, or a decision rather than a current count.

Numbers in this project move. Nine of the thirteen datasets were rebuilt or
enriched between 2026-09-01 and 2026-09-02 while these papers were being
written, and several figures in the standing documents went stale in that
window. **The figures are stamped; the reasoning is what is meant to last.**

---

## The twelve-point contract every dataset is held to

Since 2026-08-30 a dataset is not "done" when it looks complete. It is done
when it crosses a contract measured by `code/518_dataset_readiness.py` and
reported in `docs/DATASET_READINESS.md`. There are three statuses —
**READY / BLOCKED / NOT_TESTED** — and deliberately no fourth, because a vague
status is how nine datasets sit at 80% forever.

```
C1  grain declared AND validated on the full file
C2  primary key + join keys validate; cardinality is a promise, not a guess
C3  literal duplicates removed, or the distinguishing dimension declared
C4  entity attachment WHERE THE SUBJECT IS AN ENTITY
C5  every harvested row lands in a NAMED disposition bucket
C6  unresolved identity conflicts never ship as definite facts
C7  no double-counting path; join cardinality honest
C8  ONE documented rebuild that does not destroy later enrichment
C9  an update runbook another session can execute from the document alone
C10 regression + semantic-diff gates cover the outputs
C11 column hygiene — no always-empty columns, every column in a codebook
C12 inclusion basis — every row can answer WHY IT IS IN CEDAR
```

**Scoreboard, 2026-09-02: READY 9 / 13.** `_entity_layer`, `contractors`,
`deals`, `federal-register`, `gaming`, `lobbying`, `nagpra`,
`native-owned-businesses` and `nonprofits` are READY; `legislation`,
`natural-resources`, `subcontracting` and `funding` are BLOCKED. Each paper
reproduces its own dataset's blockers. [measured — scoreboard regenerated
2026-09-02]

---

## Identity: `cedar_uid`, the handle, and hub-and-sub-hub

Every dataset keys to one identity layer, dataset 13. Three things about it are
assumed by all thirteen papers.

**`cedar_uid` is permanent; the handle is not.** Each entity holds one
permanent identifier that is never reused and never changes
(`CE-0011W-HN`), and separately a human-readable handle
(`AKNF-ACSRMT-00-CALSTA-ASVCPR`) that **retires when an entity is
reclassified**. Join on `cedar_uid`. A handle is for reading, not for keying.

**A compound handle is not a broken one.** `AKNF-MTLKTL-00-TLNGHD` and
`CNSF-MINNCH-LL` are canonical; the apparent "base" `AKNF-MTLKTL-00` is not in
the spine at all. Stripping the suffix to make a join work turns 21,693
joinable rows into unjoinable ones while looking like a normalisation.

**Relationships are hub and sub-hub, never peer.** A holding company and a
casino are sub-hubs of the nation that owns them. Twelve local implementations
of many-to-many is how `nagpra` ended up with a correct party bridge and
`deals` ended up able to name only one Native party.

**Identity claims are append-only with their evidence attached**, so a later
correction is recorded as a correction rather than overwriting what was
believed before.

---

## The evidence tiers

| tier | what it means |
|---|---|
| **A** | an identifier (UEI, CAGE, EIN, declared parent UEI), or a human ruling. The only grade a dollar may be keyed on without corroboration |
| **B** | a strong name method with an independent corroborator, or inheritance from a tier-A parent |
| **C** | a weak method — containment, token subset — held as a candidate, not published as a fact |
| **X** | **refused.** A negative ruling. Never read as a confirmation |

Ledger totals, `data/clean/cedar_identifier_ledger_final.csv`: **20,577 rows ·
A 2,286 · B 5,443 · C 12,380 · X 468.** [measured]

**A ruled *method* is not a positive ruling.** `attribution_method` says WHO
decided; `confidence_tier` says WHAT was decided. All 317 `elijah_ruling` EIN
rows are tier X — *negative* — and a script that read "the method is in the
RULED set" as "the answer was yes" published 317 owner *exclusions* as
confident attributions. Standing detector: `py -3 code/293_lint_bug_classes.py`.

---

## Record scope: an unkeyed row is often the right answer

ADR-010 draws a distinction the earlier work collapsed:

    "we could not identify the entity"        <- a defect, work to do
    "there is no single entity to identify"   <- the correct representation

`record_scope` is one of `entity`, `multi_entity`, `indian_country`,
`geographic`, `native_serving`, or `unresolved` — and **`unresolved` is the
only one that is a defect**. A bill amending federal Indian law affects all 574
federally recognised tribes; NCAI lobbying on behalf of Indian Country is not
an unresolved link to one tribe. Coverage is measured against the *resolvable*
denominator, not the row count.

ADR-013 completes it. Where no entity can be named, the row still has to say
**why it is in Cedar at all**: `named_entity`, `term_match` (with the matched
terms recorded, not just the fact of matching), `program_authority`,
`geographic`, `subject_classification`, or `human_ruling`.

---

## What was excluded on purpose

**Terms of use.** Sources marked `TERMS_STATED_RESTRICTIVE` are excluded by
**every** route — the publisher's own page, its WordPress media API, the
Wayback Machine, and any harmonised derivative. Harmonising changes what Cedar
publishes; it does not change what Cedar was allowed to take.

Named exclusions: **Confederated Colville**, **CTUIR / Umatilla**, **Yakama**,
**Chickasaw** (its terms name company directories specifically, ~622 firms),
**NANA / Akima** (forbids automated use, scraping and aggregation — ~55
operating companies carrying UEI, CAGE, DUNS, NAICS and 8(a) status, the single
highest-value refusal in the project; a sitemap enumeration was **stopped
mid-run** when the terms were read), **Southern Ute** (27 firms), **Forest
County Potawatomi** (18 firms), and Navajo's NBOA directory.

It is enforced in code, not by convention:
`code/615_set_publishable_native_owned_businesses.py` runs a permission gate on
`source_terms_status` before anything else. Each exclusion is recorded with the
quote that justifies it, so the boundary is auditable and a future opt-in
request has something to point at. **Asking is the route back in; a cleverer
scrape is not.**

**Licence, distinct from terms.** Casino City may be read for QA and never
published. D&B Open Data (legal name, street, city, state, ZIP) may not be
disseminated in bulk and attaches to every base award dated before 2022-04-04.

**Consent, distinct from both.** `publishable` records *Cedar's* decision under
a stated policy; `consent_status` records *the source's*. Overwriting the
second with the first would record a permission nobody gave.

---

## Four of five duplicate allegations were phantom

This finding shaped how every money table in Cedar is built, so it is repeated
in the papers it bears on. Stated once here in full.

An automated scan flagged large blocks of "duplicate" rows across the money
tables. Measured against the **source objects** rather than inferred from the
output, four of the five dissolved:

| allegation | flagged | after measurement | what they really were |
|---|---:|---:|---|
| `prime_contracts.csv` | 80,778 | **0** [measured] | distinct FPDS transactions; the mapper had dropped `contract_transaction_unique_key` |
| `prime_contracts_archive_backfill.csv` | 60,919 | **0** [from the record] | same cause, same fix |
| `faads_*` (both tables) | 180,260 | **3,441** [measured] | distinct assistance transactions; a de-dupe would have destroyed **$8,291,124,113** of real obligations |
| `np_schedule_i_grants.csv` | 101 | **0** [measured] | one return listing a grant line twice — both real |
| the identity hub | 11,981 | **11,981 — real** | but distinct events rendered identical by a lossy projection |

**Not one row was deleted to reach any of those zeros.** Each fix restored or
added an identifying column: `code/430_restore_prime_transaction_key.py`,
`code/791_faads_transaction_key_and_repoint.py`,
`code/781_upstream_grain_columns.py`.

The evidence is the part worth keeping. `ed_fy2007_archive.zip` holds 344,401
rows and **344,401 distinct transaction keys**; the worst apparent duplicate
group in it — 445 identical UC Irvine rows — is 740 real transactions carrying
modification numbers 0001–0740, 592 of them $0. The rows looked identical
because the *published* fields were identical, not because the events were.

**The rule this earned: a duplicate is proved against the source, never
inferred from the output.** An identical-looking row is evidence that the
projection is lossy. The fix is an ordinal or a restored key — never a delete.

---

## Two operational hazards that explain odd-looking history

**A full rebuild and an in-place enricher on one file need an ordering, and the
enricher must run LAST.** This has bitten repeatedly: `code/133` rebuilding
`ferc_docket_filings.csv` reverted `code/168`'s in-place entity links four
times in a single day. Before running any rebuild, check for a
`.bak_*_pre<script>` file beside the target — that is the signal an enricher
has touched it. `py -3 code/build.py plan <collection>` prints the ordered
rebuilds-then-enrichers, and `code/cedar_pipeline.NEVER_RUN` names what may not
be run at all.

**A warning with no expiry outlives the condition it describes.** A "nothing
should ship until `dist/` is rebuilt" hold was read as live on 2026-08-28 and
used to defer a ship chain — for a rebuild that had already happened two days
earlier. When writing a warning, say what would make it false.
