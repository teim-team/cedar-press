# Review tracker — Cedar Press, September 2026

Every change the owner asked for, in the order it was asked, with where it
landed and how it is held. Nothing is marked done from memory: each row names
the file that carries it and, where one exists, the test that fails if it is
undone.

**Status words are two only.** DONE, or OPEN with a reason. There is no
"mostly". A row that cannot say which file carries it is OPEN.

---

## Review 1 — 2026-09-14 (the structural pass)

| # | Asked for | Status | Where it lives | Held by |
|---|---|---|---|---|
| 1.1 | The login menu must not open by default on the door | DONE | `PressGate.jsx` — `panel` starts null | `the sign-in panel offers a working form` |
| 1.2 | Remove the search bar from the overview | DONE | `CedarPress.jsx` — `SearchStart` deleted | — |
| 1.3 | Remove the redundant collections strip | DONE | `PressCollectionStrip.jsx` deleted | — |
| 1.4 | Remove "Every record gets the right context" from Collections | DONE | `CedarPressData.jsx` | — |
| 1.5 | Methods: remove the stray logo | DONE | `CedarPressMethods.jsx`, `press.css` | — |
| 1.6 | Methods: display it better, hidden unless wanted | DONE | chapters + `Reasoning` disclosures | — |
| 1.7 | Methods: more icons and buttons | DONE | `pressMethodIcons.jsx`, `cp-ch__act` | — |
| 1.8 | Nav order: Collections, Research Briefs, Priorities | DONE | `PressChrome.jsx` `NAV`, `PressHub.jsx` | — |
| 1.9 | Replace Contact with Priorities in the tiles | DONE | `PressHub.jsx`; Contact moved to the footer | `sign in, read the overview, sign out` (6 tiles) |
| 1.10 | A record becomes a dedicated, linkable page | DONE | `CedarPressRecord.jsx`, `pressRecord.js` | `a row opens a linkable record…` |
| 1.11 | Transaction page, not an entity page | DONE | summary is the transaction; name links out | same |
| 1.12 | Entity name links to an entity profile | DONE | `CedarPressEntity.jsx` | `the entity name opens a profile…` |
| 1.13 | Remove the explanatory paragraph under every value | DONE | one "Field definitions" control | `record-definitions` assertions |
| 1.14 | Canonical name once, "Recorded as" underneath | DONE | `CedarPressRecord.jsx` | — |
| 1.15 | Cedar ID beside the name with a copy button | DONE | `CopyButton` in the identity line | — |
| 1.16 | Original amount primary, adjusted secondary with its year | DONE | `realDollars()` reads the file's own column | `pressRecord.test.js` |
| 1.17 | Repetitive and zero-valued fields out of the first view | DONE | declared view first, the rest folded | `record-more` assertions |
| 1.18 | Mostly white, more space, two columns | DONE | `press.css` `cp-rec__fields` | — |
| 1.19 | A row opens a linkable record page | DONE | `/record?k=&r=&from=` | `pressRecord.test.js` |
| 1.20 | Back to results restores filters, sort, page and scroll | DONE | `rememberReturn` / `takeReturn` | `pressRecord.test.js`, smoke |
| 1.21 | Previous and next record controls | DONE | `neighbours()` + `Walk` | `pressRecord.test.js`, smoke |

## Review 2 — 2026-09-15 (the editing pass)

| # | Asked for | Status | Where it lives | Held by |
|---|---|---|---|---|
| 2.1 | One row for the logo and the account control | DONE | `PressChrome.jsx` `AccountMenu` | `the header is one row…` |
| 2.2 | "Sign out" into the account menu | DONE | same | same test asserts no loose button |
| 2.3 | A compact mobile nav naming the current section | DONE | `SectionMenu` | same |
| 2.4 | Tighter spacing: nav to label to headline | DONE | `press.css` `cp-mh`, `cp-hero__access` | — |
| 2.5 | Drop the duplicate action buttons, keep Ask Cedar | DONE | `CedarPress.jsx` | — |
| 2.6 | One short introduction, not eight clauses | DONE | `CedarPress.jsx` | — |
| 2.7 | Remove "Point at a section for what it holds" | DONE | `PressHub.jsx`; the sentence is on the card | — |
| 2.8 | Collections: title is "Collections" | DONE | `CedarPressData.jsx` | — |
| 2.9 | Collections: remove the introductory paragraph | DONE | same | — |
| 2.10 | Move the entity-methodology link off the top | DONE | footer + each collection's panel | — |
| 2.11 | Shelf copy down to plan, coverage, tiles | DONE | `PressShelf.jsx` | — |
| 2.12 | The first mobile screen shows collections | DONE | the above, together | `Collections opens on collections` |
| 2.13 | Table: title, sample label, toolbar, results | DONE | `PressExplore.jsx` | — |
| 2.14 | Coverage and method behind "About this collection" | DONE | `AboutCollection` | `About this collection…` |
| 2.15 | Keep amount basis and year basis near the data | DONE | `cp-ex__reads` | `explore-scope` assertions |
| 2.16 | Short action labels; secondary actions in a menu | DONE | `PressExplore.jsx` | `no action label wraps past two lines` |
| 2.17 | Columns lead with entity, program, amount, date | DONE | `roleFirst` in `PressExplore.jsx` | `a single collection opens on the declared view` |
| 2.18 | Methods: shorter title, brief explanation, then topics | DONE | `CedarPressMethods.jsx` | — |
| 2.19 | Methods: explicit chapter names, consolidated | DONE | seven chapters, named | — |
| 2.20 | ID cards: what it names, when it persists; rest folded | DONE | `pressMethodSections.jsx` `IdentityPair` | Methods identity test |
| 2.21 | Disclosure labels say what is inside | DONE | every `Reasoning label=` | — |
| 2.22 | Defensible claims, not absolutes | DONE | hero and chapter 2 rewritten | — |
| 2.23 | Record: amount, program, date under the name | DONE | `CedarPressRecord.jsx` | `a record opens on its amount` |
| 2.24 | ID and recorded name below the summary | DONE | `cp-rec__ids` after `cp-rec__sum` | — |
| 2.25 | "View entity profile" | DONE | same | — |
| 2.26 | Remove the standalone row definition from the opening | DONE | moved to the evidence section | `a record opens on its amount` |
| 2.27 | No field shown twice | DONE | `shownInSummary` covers the subject | — |
| 2.28 | Evidence explains THIS match | DONE | `attribution_columns` per table | — |
| 2.29 | Raw implementation language out of the main view | DONE | attribution columns live in the evidence | — |
| 2.30 | Technical identifiers into additional details | DONE | `groupFields()` | — |
| 2.31 | Group the extra fields | DONE | geography, financial, identifiers, classifications | `record-more` assertions |
| 2.32 | One preview notice | DONE | one line in the evidence section | — |
| 2.33 | Profile: compact identity, notice, then records | DONE | `CedarPressEntity.jsx` | `an entity profile opens on its records` |
| 2.34 | Remove "Collections read" and the indirect count | DONE | one sentence | — |
| 2.35 | "View in table", and a way back to the record | DONE | `from` parameter | smoke asserts the back link |
| 2.36 | Fewer tiny uppercase labels | DONE | shelf facts, viewer caption, What's New note | — |
| 2.37 | Tests for the first screen and label wrapping | DONE | `tests/smoke.spec.js` "the first screen" | five tests |

## Review 3 — 2026-09-15 (width and spacing)

| # | Asked for | Status | Where it lives | Held by |
|---|---|---|---|---|
| 3.1 | Space above "Know what's shaping Indian Country" | DONE | `press.css` — the first-screen rule zeroed the hero's top padding | — |
| 3.2 | Methods uses the full page width | DONE | heading caps removed, body measures to 92ch | — |
| 3.3 | The two identifiers fill the width | DONE | same; the cards already did, the heading did not | — |
| 3.4 | The entity view and the record page, the same | DONE | `cp-rec__name` cap removed | — |
| 3.5 | Every page carries the adjustment | DONE | 32 rules widened; a scan reports no reader page with text capped under half its column | — |

---

## What is deliberately NOT done, and why

- **Award number and location in "Record details"** (review 2). The block is
  the collection's declared column view, topped up from the codebook, and it
  skips long source keys. The award number does appear on Federal Funding;
  the city and state sit in the Geography group, one click away. Pinning
  fields per collection is a product decision, not a display one.
- **The signed-out door keeps its narrow measures.** It is a landing page
  where a short line is the design, and the width review was about the
  subscriber pages.
- **Full-table search.** Every count on these pages is a count of the
  published ten-row samples, and every surface says so. That does not change
  until a serving layer ships.

## How to check this file is still true

```
npm run lint && npm run test && npm run test:smoke
```

The five tests under `the first screen` in `tests/smoke.spec.js` are the ones
that hold the review's visual asks: the header's height, a collection on the
first phone screen, the amount on the first phone screen, records on the
profile's first screen, and no action label wrapping past two lines.
