# Cedar Press — state after 2026-09-04

*Every line below carries the command that PROVES it. A checklist whose items
cannot be re-verified is a memory, and memory is what kept letting the CICD
identifier come back.*

## How to check everything at once

    py -3 code/1169_release_verify.py            # the release gate, 11 checks
    py -3 code/1169_release_verify.py selftest   # proves each check FIRES (14 fixtures)
    py -3 code/1116_ruling_propagation_2026_09_02.py verify   # no stale figure in docs/

The gate is the answer to "where is this NEID coming from". It now covers the
surface that actually leaked.

## Identity — the CICD purge, finally closed

| what | state | proof |
|---|---|---|
| delivered CSVs | **0** retired identifiers | gate: `delivered CSV identity migration` |
| sample trees | **0** | gate: `sample trees carry no retired identity` |
| ambiguous NEIDs | **0** | `cedar_publication.neid_map()` |
| customer database | rebuilding | gate: `customer database identity migration` |

It began at 13,400 rows across six datasets. The reason six earlier passes did
not hold: each removed the names known that day, and nothing checked the
SAMPLES — 77 files under `public/data/cedar/samples/` shipped a retired NEID
while every delivered CSV was clean and two identity gates passed. That hole is
now a gate with a fixture.

`TRBF-FSCWSA-00` was the last ambiguous NEID, blocking 27 rows. FSCWSA decodes
to Fort Sill Chiricahua Warm Springs Apache; the rival claimant shared only the
words "Warm Springs". Adjudicated in `cedar_publication.ADJUDICATED_COLLISIONS`
with its reasoning, not as a bare mapping.

## Names — sourced, not maintained

`name` is the OFFICIAL name from the register that publishes it, with the URL
and capture date beside it. 1,331 of 1,916 entities are sourced that way; the
rest read `cedar_internal`, which means no external register publishes a name
for that class.

Matching the BIA list on the old short handle resolved **29 of 577 (5.0%)**.
On the official name: **576 of 577 (99.8%)**. The handle is retired, and
`1181 verify` FAILS the build if two entities ever ship the same name.

## Datasets rebuilt this session

| dataset | grain | note |
|---|---|---|
| `federal_awards_2025_2026` | one row per AWARD | 61,579 transactions -> 29,622 awards; 2025/2026 split; deny-by-default attribution |
| `native_federal_advocacy_2025_2026` | one row per activity per entity | 3,261 rows, 5 sources, `activity_type` |
| `deals` (2025-26 review slice) | one row per deal | 76 corrections, 43 columns |
| `native_entities` | one row per entity | 1,916 across 18 classes |

Contracting ships at the CONTRACT grain (110,692 rows are 68,616 contracts —
one absorbed 98 modifications). Subcontracting is the open structural
question: two entities per row where every other Cedar dataset uses one.

## Open, and honest about it

- **customer database** — rebuilding from the clean CSVs.
- **`no-regression chain (62)`** and **`dataset semantic correctness`** —
  NOT_ESTABLISHED. No test asserts them. Named rather than omitted: an absent
  check must never read as a pass.
- **`congressional_testimony`** — 349 witness rows acquired 2026-09-04, not yet
  merged into the advocacy dataset.
- **`formal_letter`** — declared, no source.
- **F14** — 142 deals rows labelled `Federal` need per-row evidence.
- **12,134 nonprofit rows** still unkeyed; the class now exists to key them to.

## The rule this session kept re-learning

A check that reads a key, column or file which does not exist **passes**. It
does not fail. Three times today:

- a state-conflict check read `recipient_state`; the column is `state`. It
  reported 0 conflicts where there were 63, worth $2.60B.
- a verification-queue guard kept reading a file after the queue became a
  column. It reported "0 outstanding, OK" with 108 rows queued.
- a legal-suffix regex had its `\b` turned into a literal backspace by a shell
  heredoc. It matched nothing, silently.

Every one was found by measuring the output, never by reading the code.
