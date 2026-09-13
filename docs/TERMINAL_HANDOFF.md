# Terminal handoff — what the site needs from the workspace

*The one file to read after pulling `cedar-press`. Rewritten in place, never
appended to: it is a list of what is open, not a journal. Last rewritten
2026-09-13.*

**If you read nothing else, read §1.** It is every open item, what to do, and
how you will know it is done. Everything below §1 explains why.

---

## 1. Open items

| # | What | Where | Done when |
|---|---|---|---|
| 1 | **Mint the `CB-` business register.** Seed per ADR-043; the NEED register is its largest seed and the 45 `Individually Native-owned business` entities keep their uids and gain business ids with an equivalence row. | `docs/CEDAR_IDENTITY_SYSTEM_2026-09-13.md` §8 | A `CB-` register exists in `data/spine/`. Then flip `live: false` → `true` on `IDENTIFIERS[1]` in `src/features/grove/pressIdentity.js` and remove the "in progress" line the card renders. A test fails until you do. |
| 2 | **Settle check characters on `CB-`.** ADR-043 says `CB-0001842-XQ`; the owner's 2026-09-13 specification says `CB-0000001` with a check convention optional later. The site shows the plain serial. | `docs/CEDAR_IDENTITY_SYSTEM_2026-09-13.md` §7.1 | The two documents agree. If ADR-043 wins, change `IDENTIFIERS[1].shape` and the regex in `src/features/grove/pressIdentity.test.js`. |
| 3 | **Re-run linkage coverage whenever a flagship changes**, and consider adding it to the release path so it is not a thing to remember. `py -3 code/1139_linkage_coverage.py apply` | `docs/LINKAGE_COVERAGE.md` | `npm test` passes in `cedar-press`. It reads that file and fails if the headline total, either named extreme, **or the measurement date** has moved. The date check is what makes a regeneration visible: gate 62 measures live data but does not rewrite this document, so without it two stale things can agree with each other. |
| 4 | **Decide the Federal Reserve claim.** The site says the linkage methods come out of the team's years inside the Federal Reserve system. It does not say the Fed uses or endorses them, because nothing here evidences that. | `docs/CEDAR_PRESS_SITE_2026-09-13.md` §3.2 | Either evidence of institutional use is recorded in this repo, or the current sentence is confirmed as the strongest defensible one. |
| 5 | **Rename role-specific columns** in published datasets that do not already use them: `native_entity_uid`, `recipient_native_entity_uid`, `owner_cedar_uid`, `parent_cedar_uid`, `business_uid`. | `docs/CEDAR_IDENTITY_SYSTEM_2026-09-13.md` §1, §4 | The site's column chips match the shipped columns. |
| 6 | **Audit for the mixing rule** once both namespaces are populated: no `CE-…` in a business-id column, no `CB-…` in an entity-id column. | same, §3 | An audit script exists and passes. |
| 7 | **Name NEED "Cedar NEED" at source.** The site displays it that way now, from the storefront catalog's `short`. The workspace manifest still carries `short_name: "NEED"`, so an export, a codebook or anything else reading the descriptor still says the bare acronym. | `data/cedar/collections.manifest.json`, the `need` descriptor | `short_name` reads `Cedar NEED`. The site follows automatically; `collectionShort()` prefers the catalog and falls back to the descriptor, so the two agreeing is the end state. |
| 8 | **Cluster free-text `use_case`** if the request tally matters. The Priorities form is free text now, so `server/cedar_press/priorities.py`'s exact-string tally will fragment. | `server/cedar_press/priorities.py` | Either a clustering step exists, or the tally is accepted as fragmenting. Do not reintroduce a menu; the owner ruled that out. |

**Nothing else.** No dataset, schema, or publication rule changed in the site
work of 2026-09-13. The site was brought into line with rules this workspace
already held.

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
