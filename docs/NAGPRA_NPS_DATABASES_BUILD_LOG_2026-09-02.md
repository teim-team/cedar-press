# The National NAGPRA Program's own six databases — build log

*Built 2026-09-02 by `code/1148_nagpra_nps_databases.py`. Every number below was
re-derived from the files on disk after the last `apply`; none is carried over
from the run report. Re-derive before quoting:
`py -3 code/1148_nagpra_nps_databases.py report`.*

**Collection:** `nagpra`. Seven new tables, **28,499 rows**, all reached by the
existing `^(nagpra_|fr_nagpra)` pattern in `code/500_build_architecture_map.py`
— no `COLLECTIONS` edit was needed and `docs/ARCHITECTURE.md` picks all seven up
on a plain re-run.

---

## What this closes

`docs/NAGPRA_BUILD_LOG.md` line 20, written 2026-08-06:

> *"`docs/SUBSET_DATASETS.md` records that no structured public database of this
> exists; that is still true. The National NAGPRA Program publishes a notice
> *search*, not the notices as data."*

**That is no longer true, and it was the reason nobody looked.** The "search" at
`apps.cr.nps.gov/nagprapublic` is a server-side DataTables grid. Its JSON
endpoints return the Program's register **as data**, with the Program's own
counts on it. Cedar had never issued one request to that host.

## The seven tables

| table | rows | grain | source endpoint |
|---|---:|---|---|
| `nagpra_nps_grant_awards.csv` | **1,221** | one NAGPRA grant award | `getgrants` |
| `nagpra_nps_inventories.csv` | **11,811** | one published inventory grid line | `getinventories` ×2 |
| `nagpra_nps_summaries.csv` | **1,540** | one museum/agency summary | `getsummaries` |
| `nagpra_nps_intended_dispositions.csv` | **253** | one newspaper-published NID | `getnids` |
| `nagpra_nps_notice_index.csv` | **6,818** | one notice | `getnotices` ×4 |
| `nagpra_nps_unclaimed_remains.csv` | **15** | one unclaimed-remains listing | `getunclaimedlists` |
| `nagpra_notice_source_corroboration.csv` | **6,841** | one FR document number | *derived* |

Route: POST, the same DataTables protocol the public grid's own "CSV" and
"Excel" export buttons use. No login, no token, no admin path.
`apps.cr.nps.gov/robots.txt` is **404** — per `docs/PULL_DISCIPLINE.md` that is
*not* a disallow — and `www.nps.gov/robots.txt` answers 200 disallowing only
`/ns/`, `/search/` and `/loader.cfm`, none of which is on this path. One poller,
`logs/_HOSTLOCK_apps.cr.nps.gov.json`, 1.5 s pacing, 45-minute hard stop.

---

## THE POINT OF THE PASS: the first genuinely independent corroboration in Cedar

`START_HERE.md` item 0 says this is the highest-value work in the project:

> *"Across 8,975 single-valued facts — **0** have a second source… The
> arbitration machinery works and has nothing to arbitrate."*

It has something to arbitrate now. `nagpra_notices.csv` derives `mni_total_stated`
by **reading the Federal Register notice's prose**
(`code/77_build_nagpra_dataset.py`). NPS's `TotalMNI` is the **Program's own
record of the same repatriation**. Two observers, not one source republished —
which is the distinction that made the earlier FR-roster attempt add zero
corroborations.

Joined on `fr_document_number`, 6,841 documents:

| status | n |
|---|---:|
| `AGREE` | **3,954** |
| `DISAGREE` | **315** |
| `NOT_TESTABLE_NO_MNI_ONE_SIDE` | 2,492 |
| `IN_NPS_ONLY` | **49** |
| `IN_CEDAR_ONLY` | 31 |

**Neither value is overwritten and no disagreement is resolved.** A `DISAGREE`
row carries both numbers and both sources. Examples, all single-NPS-row so the
gap is not an aggregation artefact: `00-19292` Cedar 4 / NPS 99; `00-12852`
Cedar 19 / NPS 11; `00-25126` Cedar 491 / NPS 490; `00-29811` Cedar 141 / NPS
142. The ±1 cases look like an off-by-one in one reader or the other; the 4-vs-99
case does not, and is the kind of row this table exists to surface.

**The 49 `IN_NPS_ONLY` documents are the actionable half** — FR document numbers
the Program lists that Cedar's Federal Register sweep does not hold at all. They
are a named worklist, not a defect claim: none has been checked against the FR
itself in this pass.

> **A key repair, declared because it changes two counts.** Two NPS rows write
> the FR document number with a literal `?` where the hyphen belongs
> (`2016?26975`, `2016?29537`). Both `-` forms exist in Cedar and neither `?`
> form does, so without the repair the same notice appears once as
> `IN_NPS_ONLY` and once as `IN_CEDAR_ONLY` — wrong twice. The repair fires only
> when substituting `-` for `?` yields a key Cedar actually holds. Measured
> across all 6,818 NPS rows: **608 are non-canonical and 606 of those are
> legitimate FR prefixes** (`E8-`, `E9-`, `X94-`, `R7-`), which are not touched.

---

## TWO HIDDEN DEFAULT FILTERS, AND BOTH WOULD HAVE SHIPPED A SHORT TABLE

This is the field guide's signature defect in a new place: **a check that
measures something other than its own name.** In both cases the loop's own
`got >= recordsTotal` test never fired, every request was HTTP 200, and the
result looked complete.

**1. `getnotices` defaults to `NoticeType=NIC`.** A pull that never sends the
parameter returns **4,810 of 6,818 rows — 70.6%** — and stops. The only signal
is that `recordsFiltered` (4,810) is not `recordsTotal` (6,818). Asked per type:

    NIC  notice of inventory completion       4,810
    NIR  notice of intended repatriation      1,869
    NID  notice of intended disposition         131
    NOT  notice of transfer or reinterment        8
                                             ------
                                              6,818   exactly

**2. `getinventories` defaults to both inventory types collapsed.** Asked
without `InventoryType` the endpoint returns 11,812 rows of which **4,139 are
literal duplicates of another row (35%)**, because culturally affiliated and
culturally **unidentifiable** holdings render as the same six columns. Split:
`CulturallyAssociated` 454 + `NotCulturallyAssociated` 11,358 = 11,812. That
distinction is not cosmetic — "culturally unidentifiable" is a status under
43 CFR 10.11 with consequences for who may claim an ancestor — so the pull was
re-run per type and `cultural_affiliation_status` is now a column.

**The rule this earns: read the denominator the SERVER gives you.** `recordsTotal`
is the whole table; `recordsFiltered` is what your request selects. A paging loop
that compares its cumulative count against `recordsTotal` terminates early and
silently the moment any default filter is in force. `code/1148`'s loop now reads
`recordsFiltered`, prints both, and warns when they differ.

Both stale cache directories were **retired by MOVE, never deleted** (field
guide rule 9): `data/raw/external/nagpra_nps_1148/_retired_getnotices_default_NIC_filter_2026-09-02/`
and `_retired_getinventories_no_InventoryType_2026-09-02/`.

---

## THE GRANTS TABLE — $66,095,102.79, and it is NOT a duplicate of the assistance stream

1,221 awards, **FY1994–2025**, 0 unparseable amounts.

| cut | awards | dollars |
|---|---:|---:|
| all | 1,221 | **$66,095,102.79** |
| recipient_type `Tribe` | 705 | $36,497,399.28 |
| recipient_type `Museum` | 516 | $29,597,703.51 |
| FY1994–2006 | 524 | $27,691,873.00 |
| FY2013–2025 | 485 | $27,846,965.79 |
| grant_type `Consultation` | 905 | — |
| grant_type `Repatriation` | 316 | — |

**A first draft of this pass claimed these awards "appear in no other Cedar
table". That was false and the check is the finding.**
`federal_funding_transactions.csv` holds **696 rows on CFDA 15.922, FY2007–2026,
$11,215,956.86**. What it does not hold is the years:

| window | Cedar assistance (CFDA 15.922) | NPS grants database |
|---|---|---|
| FY1994–2006 | **nothing** | 524 awards · $27,691,873 |
| FY2007 | 1 row · $4,000 | 35 awards · $1,892,641 |
| FY2008–2012 | **zero rows** | 177 awards · $8,663,623 |
| FY2013–2025 | 669 rows · $11,241,421.22 | 485 awards · $27,846,965.79 |
| FY2026 | 26 rows · **−$29,464** (deobligations) | *(database ends FY2025)* |

**736 of the 1,221 awards — $38,248,137 — fall in FY2012 or earlier, a window in
which Cedar's assistance stream holds one $4,000 transaction.** From FY2013 the
two overlap but describe different things: Cedar counts *transactions*
(modifications included, and FY2026 nets negative) while NPS publishes the
*award*.

> **DO NOT SUM THE TWO.** They are two grains of one programme. A total that
> adds `nagpra_nps_grant_awards.amount_awarded_usd` to
> `federal_funding_transactions` CFDA 15.922 double-counts every FY2013–2025
> award.

---

## What was refused, and it is reachable

`/nagprapublic/home/getcontacts` answers HTTP 200 and returns
`FirstName, LastName, Company, Title, Phone, Email`. **It was not fetched.** No
directory for it exists under `data/raw/external/nagpra_nps_1148/`, and
`verify` invariant **NPS-4** fails if one ever appears or if any output table
grows a column named `firstname`, `lastname`, `email` or `phone`. A natural
person's contact details are outside what Cedar publishes even when the
publisher is a federal agency and the page is open —
`docs/PUBLICATION_POLICY.md`, `AGENT_FIELD_GUIDE` §5.

## The terms value nearly withheld all 21,658 rows

`code/cedar_publication.py` gates on
`GATES["source_terms_status"] = {"SILENT", "TERMS_STATED_NO_REUSE_RESTRICTION", ""}`.
The first draft wrote `source_terms_status = PUBLIC_DOMAIN_US_GOVERNMENT_WORK` —
**true, accurate, and not in the allow-set**, so every row would have been
withheld at publication with nothing saying so. The vocabulary has no
public-domain member. The published value is now
`TERMS_STATED_NO_REUSE_RESTRICTION`, which the NPS disclaimer supports verbatim
(*"material created by the National Park Service and presented on this website,
unless otherwise indicated, is generally considered in the public domain"*,
`https://www.nps.gov/aboutus/disclaimer.htm`, quoted 2026-09-02), and the
public-domain fact rides in `source_terms_url` + `source_terms_basis`.

**For the integrator:** the gate vocabulary would be more honest with an explicit
public-domain member, but `code/cedar_publication.py` is not an agent-editable
file. Recorded, not changed.

---

## What is NOT clean, stated rather than hidden

**1. The source publishes no row identifier, and four of the six tables have no
unique natural key.** Measured on the published columns only (provenance
excluded):

| table | rows | distinct published tuples | literal-duplicate surplus |
|---|---:|---:|---:|
| `nagpra_nps_grant_awards.csv` | 1,221 | 1,212 | 9 |
| `nagpra_nps_inventories.csv` | 11,811 | 7,693 | **4,118** |
| `nagpra_nps_intended_dispositions.csv` | 253 | 245 | 8 |
| `nagpra_nps_notice_index.csv` | 6,818 | 6,817 | 1 |
| `nagpra_nps_summaries.csv` | 1,540 | 1,540 | 0 |
| `nagpra_nps_unclaimed_remains.csv` | 15 | 15 | 0 |

**Nothing was collapsed** (field guide §4: four of five duplicate allegations in
this repo were phantom). Two grants of $15,000 to Cape Fox Corporation in FY2001
are most likely two grants. The inventories surplus survived the
`InventoryType` split, so the remaining discriminator — probably the claiming
tribe or the submission — is simply **not in the published projection**. These
tables are declared `GRAIN_OPEN` in `code/512_build_dataset_contracts.py`, with
the grain stated and the primary key stated as unstatable, rather than given a
positional key (`code/293_lint_bug_classes.py` class 7).

**2. The source's own two counters disagree by one, and the row is unreachable.**
On `getinventories?InventoryType=NotCulturallyAssociated` the server reports
`recordsTotal` **11,358** and `recordsFiltered` **11,357**. A request at
`start=11357` returns zero rows. Cedar holds 11,357 + 454 = **11,811** and the
11,812th does not exist as far as the API is concerned. **Not fabricated, not
rounded up.**

**3. `nagpra_nps_summaries.tribes_listed_semicolon` is a list-valued column**, up
to hundreds of tribe names in one cell, and it is published as recorded with
`n_tribes_listed` beside it. It is **not** resolved to `cedar_uid` in this pass.
That is the obvious next piece of work and it is a name-resolution job on a
list-valued field — the shape `docs/ARCHITECTURE_DECISIONS.md` ADR-037 §2
describes for the NAGPRA bridge — not an acquisition.

**4. No table here carries a `cedar_uid`.** Institution names are museums and
federal agencies, which are not spine entities; the tribe side lives in the
summaries list column above. Linking is out of scope for an acquisition pass and
is named here so the absence is a task, not a silence.

---

## Verify, and the proof it fires

```
py -3 code/1148_nagpra_nps_databases.py verify     # exits 1 when it did not land
py -3 code/1148_nagpra_nps_databases.py selftest   # PASSES, 5/5 fired
```

`verify` is a **landing** check, not a conservation check
(`AGENT_FIELD_GUIDE` rule 5 — a proof that nothing broke is not a proof that
something happened):

| invariant | fails when |
|---|---|
| **NPS-1** | any of the six tables is absent, or below its row floor |
| **NPS-2** | the corroboration table is absent, or fewer than 1,000 notices could be compared on MNI — i.e. the second source is not landing |
| **NPS-3** | any row carries no `source_terms_status` |
| **NPS-4** | the refused contacts endpoint reached disk or a table grew a person-column |
| **NPS-5** | grant dollars sum to zero |

`selftest` injects each breach in turn, asserts exit 1 **and** that the named
invariant is what fired, restores from a literal path (never a glob) and asserts
exit 0. Result 2026-09-02: **5 of 5 FIRED, restored, verify exit 0.**

## Re-running

Fetch is checkpointed per page under
`data/raw/external/nagpra_nps_1148/<endpoint>[__<variant>]/startNNNNNNN.json`;
a re-run downloads nothing it already holds. `apply` is a full rebuild of the
seven tables from that cache and takes no network. There is **no in-place
enricher on any of these tables**, so there is no rebuild/enrich ordering to
declare — `apply` may be re-run at any time.
