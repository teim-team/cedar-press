# Terminal handoff — what the site needs from the workspace

*The one file to read after pulling `cedar-press`. Rewritten in place, never
appended to: it is a list of what is open, not a journal. Last rewritten
2026-09-16.*

**Verified 2026-09-16:** `main` is three commits ahead of `origin/main` and nothing has been pushed: `b12cd23` the review-wording fix, `9be18d1` the R7 frozen-source audit workflow, and this documentation commit at HEAD. Committed: `code/1174_qc_review_bundle.py` and `code/1176_build_review_artifact.py`; `code/1188_import_chatgpt_r7_business_register.py` and `code/1188_import_chatgpt_r7_business_register_test.py` (209 assertions, 70 positive controls, 139 negative fixtures, 0 failed, including independent-subprocess lock tests, report lock and read-only tests, and a git line-ending round trip); `.gitattributes`; `docs/imports/r7_audit/CURRENT.json` with all four bundles; `docs/CB_ID_FORMAT_PROPOSAL_2026-09-14.md`; `docs/SHIP_BARS_DRAFT_2026-09-14.md`; this file. R7 refrozen once under the reviewed tool and still not imported: current bundle e6708a8f8e608cd16df9c09c, integrity PASS, NOT_APPROVED, report exit 10, store CLEAN, all 83 proposed pairs UNRESOLVED, and no business register under data/spine/. Four files remain untracked and were never staged: the lock files docs/imports/r7_audit/.lock and .lock.owner.json, and two pre-bundle artifacts read by no code, docs/imports/R7_2026-09-14_FREEZE_MANIFEST.json and docs/imports/R7_2026-09-14_equivalence_adjudication_queue.csv (the owner decides whether to delete them). Server tests 191 pass (1161 subtests); JS 215 of 216, the one failure the local-only sitemap check (CI green).

**If you read nothing else, read §1.** It is every open item, what to do, and
how you will know it is done. Everything below §1 explains why.

---

## 1. Open items

| # | What | Where | Done when |
|---|---|---|---|
| 1 | **Mint the `CB-` business register.** BLOCKED ON THE OWNER. R7 frozen and audited, not imported. `code/1188_import_chatgpt_r7_business_register.py` reads the R7 ZIP directly and imports nothing; its tests are `py -3 -B code/1188_import_chatgpt_r7_business_register_test.py`. Current audit bundle e6708a8f8e608cd16df9c09c via `docs/imports/r7_audit/CURRENT.json` (refrozen 2026-09-16; schema v3; integrity PASS; reproduces from current inputs; import approval NOT_APPROVED, G03-G06 blocked); history 5bfe75935203e605fed449cb (v2), b1dbf9c7681d781dd7955c5d, 5c21f711f2d6e81d03e1a095, e6708a8f8e608cd16df9c09c, all four kept. **Bundles are immutable: never edit anything under docs/imports/r7_audit/bundles/**; their bytes are content-addressed, so any formatting, quoting or newline change is corruption, and `.gitattributes` stops git converting them. The owner edits only docs/imports/R7_OWNER_DECISIONS.json (typed decisions; may open gates) and docs/imports/R7_OWNER_NOTES.json (commentary; never a gate); neither exists yet, and their schemas are in the tool's docstring. `freeze` and `recover` hold one OS-managed lock for the whole operation and recheck every consequential input immediately before activation; a held lock is refused (exit 5), never waited on. The operating system releases the lock when its holder exits or dies, so there is no stale lock and no unlock step: after a crash, run `recover`. Report exits 10 while not approved, 5 when a freeze or recover holds the lock, 6 when the audit store has not been initialized (the report creates nothing, not even the lock file: run `freeze` first), and 11 when an input changes while the report runs, so a stale snapshot is never returned as 0 or 10. The report holds the same lock for its whole snapshot. `freeze` exit 0 means audit artifacts were written, not approval. Retention: every activated bundle is kept, nothing is pruned, and failed-transaction leftovers are renamed aside and listed by the report inventory. When an approved import lands, flip `live: false` → `true` on `IDENTIFIERS[1]` in `src/features/grove/pressIdentity.js`. | `docs/imports/r7_audit/CURRENT.json` | Every gate OPEN on CURRENT recorded decisions, and the import made as a separate reviewed change. |
| 2 | **Settle the `CB-` format.** Three specifications compete (ADR-043, the 2026-09-13 specification, R7 as issued). Measured: reusing the existing entity-id check function (`check_chars` in `code/503_identity.py`) on a 7-digit serial covers only 5 of the 7 digits and misses 28.57% of single-digit substitutions; that is a naive implementation, not ADR-043 itself. Proposed, not adopted: the R7 serial plus ISO 7064 MOD 97-10 check digits, which would amend ADR-043. Owner to decide. | `docs/CB_ID_FORMAT_PROPOSAL_2026-09-14.md` | The owner's decision is recorded and ADR-043 and the identity specification agree with it. |
| 3 | **Re-run linkage coverage whenever a flagship changes**, and consider adding it to the release path so it is not a thing to remember. `py -3 code/1139_linkage_coverage.py apply` | `docs/LINKAGE_COVERAGE.md` | `npm test` passes in `cedar-press`. It reads that file and fails if the headline total, either named extreme, **or the measurement date** has moved. The date check is what makes a regeneration visible: gate 62 measures live data but does not rewrite this document, so without it two stale things can agree with each other. |
| 4 | **Decide the Federal Reserve claim.** The site says the linkage methods come out of the team's years inside the Federal Reserve system. It does not say the Fed uses or endorses them, because nothing here evidences that. | `docs/CEDAR_PRESS_SITE_2026-09-13.md` §3.2 | Either evidence of institutional use is recorded in this repo, or the current sentence is confirmed as the strongest defensible one. |
| 5 | **Rename role-specific columns** in published datasets: `native_entity_uid`, `recipient_native_entity_uid`, `owner_cedar_uid`, `parent_cedar_uid`, `business_uid`. PARTLY DONE, and the old bar tested the wrong thing. Measured 2026-09-16: not one of the five names appears anywhere in tracked `data/` (0 occurrences; `cedar_uid` appears 301 times). The samples ship `cedar_uid` (contractors, deals, funding, nonprofits, the entity layer), `owner_hub_cedar_uid` (need), a name rather than an id (`recipient_entity_name`, natural-resources), a class rather than an id (`native_entity_classes`, lobbying), and no entity id at all (federal-register). The site already stopped advertising names that do not ship: `src/features/grove/pressIdentity.js` holds `fields` (what ships: `cedar_uid`, and nothing for business) apart from `becoming` (the specification's names), so the chip-versus-column mismatch is closed and the old done-when was satisfied without a single column being renamed. The `attribution_columns` metadata added upstream on 2026-09-16 to `data/cedar/explore.overrides.json` (8 of the 12 tables) names existing attribution columns for the record page; it renames nothing. What is left is the rename itself, which waits on the identifier decisions in items 2 and 9. | `docs/CEDAR_IDENTITY_SYSTEM_2026-09-13.md` §1, §4 | A published table ships a role-specific column name and `fields` in `src/features/grove/pressIdentity.js` names it. |
| 6 | **Audit for the mixing rule.** Enforced over R7's frozen registries by `code/1188` check I10 (negative fixtures cover both directions). Still open over published datasets, once they carry business ids. | `docs/CEDAR_IDENTITY_SYSTEM_2026-09-13.md` §3 | An audit over the published previews exists and passes. |
| 7 | **Name NEED "Cedar NEED" at source.** CONTRADICTED BY A TEST: `src/features/grove/pressCatalog.test.js` asserts the workspace descriptor stays `NEED` and only the storefront catalog renames it. A rename was tried 2026-09-14 and reverted. Owner or site maintainer to decide which is right. | `data/cedar/collections.manifest.json` | The handoff and the test agree. |
| 8 | **Cluster free-text `use_case`** if the request tally matters. The Priorities form is free text now, so `server/cedar_press/priorities.py`'s exact-string tally will fragment. | `server/cedar_press/priorities.py` | Either a clustering step exists, or the tally is accepted as fragmenting. Do not reintroduce a menu; the owner ruled that out. |
| 9 | **Rule on the R7 import gates.** Proposed equivalence pairs (proposals, not equivalences): all 83 UNRESOLVED in the current bundle's queue (generated evidence only: 60 weak or insufficient, 17 identifier not in ledger, 3 no identifier, 2 conflict, 1 refuted, 0 candidate). The ledger records attribution, never legal identity. Decisions go only in the decisions file (docs/imports/R7_OWNER_DECISIONS.json, schema v2 in `code/1188`, not yet created); each pair decision names the evidence fingerprint reviewed and goes STALE if that evidence changes. Ship bars, including whether tribal TERO certifications rank with state certifications: `docs/SHIP_BARS_DRAFT_2026-09-14.md`. G05 needs owner approval AND the live policy function in `code/cedar_domain.py` to publish names. | `code/1188_import_chatgpt_r7_business_register.py` | G03, G05, G06 open on CURRENT decisions. |
| 10 | **Approve the documentation consolidation.** Existing files stay canonical; nothing new competes. Handoff: this file. Navigation: `START_HERE.md`. Generated data map: `docs/DATA_ARCHITECTURE.md`. Runbook: `docs/SHIPPING_RUNBOOK.md`, whose historical "chain is staged, not run" warning must be refreshed before it is presented as the current procedure; approved ship bars fold into it and `docs/schema/dataset_contracts.json`. Inventory: extend `code/521_inventory.py`. `code/465_consolidation_inventory.py` stays, because `code/502_archive_candidates.py` consumes its output. An approved CB format folds into `docs/CEDAR_IDENTITY_SYSTEM_2026-09-13.md` with its decision history kept. Nothing moved, deleted or marked obsolete until approved. | this file | The owner approves the plan. |

**Nothing else.** No dataset, schema, or publication rule changed on 2026-09-14;
every open decision is items 1, 2, 7, 9 and 10.

---

## 1b. Two gates that stopped the deploy, and will again

The live site did not move for two merges because both failed the Python step
in `.github/workflows/deploy.yml`, which sits **before** the build and the
Pages upload. Neither is a flake; both are gates working.

1. **Change the catalog, re-run the dump.**
   `node scripts/dump-press.mjs > server/cedar_press/_press_data.json`.
   The API reads that snapshot and `test_collection` fails rather than skips
   when it disagrees with the JavaScript.
2. **Name a `src/…/grove` path in a document, re-measure the rename table.**
   `docs/ARCHITECTURE.md` carries counts that `test_rename_plan` re-measures on
   every run, and the failure prints the current values for you to paste.

Run the whole thing before merging, because **CI runs nothing on a pull
request**:

```
npm run lint && npm run test && npm run test:smoke
ruff check server && (cd server && python -m unittest discover -s tests -t .)
```

---

## 2. How the site tells you it is out of date

The site does not describe the workspace in prose that can go stale. It reads
the workspace's own files and **fails its own build** when they move. Run
`npm test` in `cedar-press` and these are the assertions that speak:

| Test | Reads | Fails when |
|---|---|---|
| `src/features/grove/pressIdentity.test.js` | `public/data/cedar/register.json` | a register class the Methods page names disappears; the uid the page shows, `CE-00134-BX`, stops being Cherokee Nation; the withheld class stops being withheld; the count of individually owned firms moves off 45 |
| `src/features/grove/pressIdentity.test.js` | `docs/LINKAGE_COVERAGE.md` | the headline total, the best figure or the worst figure moves by a digit |
| `src/features/grove/pressIdentity.test.js` | `docs/IDENTIFIER_STANDARD.md` | it stops documenting `cedar_uid` |
| `src/features/grove/pressSources.test.js` | `cedar_source_registry/sources.jsonl`, the collection descriptors | the door names a source kind the workspace no longer reads, or a declared program count moves |
| `src/features/grove/pressCatalog.test.js` | the manifest | a collection is sold without a descriptor, or measured without a shelf |

So the workflow after a data change is: run the generator, run `npm test` in
`cedar-press`, and fix what it names. A red test here is the site telling you a
published claim no longer matches the data.

---

## 3. What the site now claims, in one place

Two documents, both dated 2026-09-13:

- **`docs/CEDAR_IDENTITY_SYSTEM_2026-09-13.md`** — the owner's identity
  specification. `CE-…` and `CB-…`, what each identifies, what stays outside
  them, the role-specific columns, and four disagreements with earlier
  documents that this handoff's items 1, 2, 5 and 6 exist to close.
- **`docs/CEDAR_PRESS_SITE_2026-09-13.md`** — every claim the site makes with
  the file that proves it, the copy rulings applied, and Codex's four findings
  on PR #77 with what each one changed.

Read the identity file first. It is the authority on the model; the site file
is the record of how the site was made to match it.

---

## 4. What changed in the site, for orientation

Not action items. Here so a diff of ~1,500 lines is not a surprise.

**Methods** now carries the identity argument in four sections: the two
identifiers; the worked example of a nation and the company it owns; what is
kept outside an identifier; and why the collection improves with use. The
twelve collection marks index the per-collection specifics. "Accuracy has a
time dimension" and its illustrative timeline are gone.

**Priorities** leads with a free-text box. The `<select>` of seven use cases is
a free field, per the owner's ruling that subscribers can write anything. See
item 7.

**Collections** shows each flagship's declared 6-8 column view instead of the
codebook's 27-54, which is the owner's own selection from
`docs/PUBLIC_DATASET_SPEC_2026-09-05.md` and had never been read by the viewer.
An open record carries the source document, the resolution basis, the release
and a copyable citation.

**Overview** leads with a search, labelled as reaching the ten-record previews,
because that is what the serving layer offers today.

**Copy rulings applied:** "Records are only the beginning" is cut from the door
and Methods; no argument opens on a federal contract any more; and the site no
longer implies Cedar withholds what it resolves (see the identity file, and
`INDIVIDUAL_NATIVE_WITHHELD_FIELDS` in `code/cedar_domain.py`).

---

## 5. Running the site

`README.md` covers it. In short:

```
npm ci
npm run lint          # eslint
npm run test          # node --test, the unit suite that reads this workspace
npm run test:smoke    # playwright, builds the site and drives it
npm run build
```

CI runs exactly those on a push to `main` (`.github/workflows/deploy.yml`) and
runs **nothing on a pull request**, so run them locally before merging.

---

**Checkpoint 2026-09-14: BLOCKED** — R7 frozen and audited; import waits on the owner's rulings in items 2, 9 and 10.
