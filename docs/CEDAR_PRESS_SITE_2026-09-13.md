# Cedar Press: the site's identity argument, and what the terminal owns

*Written 2026-09-13, for the terminal. Records what changed in
`cedar-press` on branch `claude/landing-page-collections-redesign-07dx8v`,
which claims the site now makes, which file proves each one, and the three
places where the site and the workspace do not yet agree.*

Read with `docs/IDENTIFIER_STANDARD.md` (the uid contract),
`docs/CEDAR_BUSINESS_ID_DECISION_2026-09-06.md` (the CB- decision, still
unimplemented) and `code/cedar_domain.py` (the individual-Native publication
rule).

---

## 0. The one thing to act on

**`CB-` is specified and unminted, and the site now says so on its face.**
The owner's identity specification of the same day is recorded in
`docs/CEDAR_IDENTITY_SYSTEM_2026-09-13.md`; that file is the authority on the
model and lists four disagreements with earlier documents that the terminal
owns reconciling.

The Methods page shows both display forms, `CE-00001-6S` and `CB-0000001`, and
marks the business register as being minted rather than implying a populated
register. `src/features/grove/pressIdentity.js` carries `live: false` on that
card; `pressIdentity.test.js` asserts it, so when the terminal mints `CB-` the
assertion fails on purpose. Flip `live` and the liveness line goes away.

---

## 1. What the site now claims

The Methods page (`/methods`) was a description of a careful process. It now
carries the argument the product is actually sold on, in three sections.

### Identity

Two identifiers, side by side, written against the specification.

| | Cedar entity id | Cedar business id |
|---|---|---|
| Identifies | one canonical Native entity | one distinct business or enterprise |
| Form shown | `CE-00001-6S` (live, and a real uid in the register) | `CB-0000001` (specified, not minted) |
| Columns | `native_entity_uid`, `recipient_native_entity_uid`, `owner_cedar_uid`, `parent_cedar_uid` | `business_uid` |
| Survives | recognition change, an attribute correction, a dataset that would be tidier without it | name, DBA, address, NAICS, certification, owner, dissolution, acquisition |

Two further sections carry the rest of the model:

- **Two subjects** — the worked example. Cherokee Nation as `CE-…`, Cherokee
  Nation Businesses as `CB-…`, the dated ownership edge between them, and the
  two questions that stop being the same question: *what activity is associated
  with this nation* and *what contracts has this enterprise received*.
- **Kept outside** — ownership and structure live in relationship rows with
  dates and a source; UEI, CAGE, EIN, SAM, NAICS and state registrations live
  in an attribute ledger; awards, deals, filings, notices and bills keep their
  own record ids and link out.

The load-bearing case, in the owner's framing: an individually owned firm
affiliated with a nation but not owned by one gets a **business id and no
entity id**, from first sighting, so the series is continuous if a nation later
buys it.

### Linkage

Six moves the identifiers make possible: joining records with no shared key,
holding an organisation still while it changes, reading an old record with
today's knowledge, following one answer into the next question, asking a
question instead of running a search, and handing a cut to someone who can
rebuild it.

### The loop

Methods with a provenance, machines propose, a researcher decides, the
decision goes back in. Closing on: *"None of that is a feature that can be
added later. It is an accumulation of decisions about records that contradict
each other, and the decisions are the asset."*

---

## 2. Every claim, and the file that proves it

`src/features/grove/pressIdentity.test.js` runs in `npm test` and fails the
build if any of these drift.

| Claim on the page | Proof |
|---|---|
| Eleven named register classes carry an entity id | `public/data/cedar/register.json` `classes[].code` |
| `Individually Native-owned business` is a register class | same file |
| Every row in that class ships with a uid and a **null** name | same file, and the count equals its own `withheld_names` |
| `cedar_uid` is the documented permanent identity | `docs/IDENTIFIER_STANDARD.md` |
| The columns shown are the specification's, and no external identifier is presented as a Cedar id | `IDENTIFIERS[].fields`, checked against a deny-list of `business_source_id`, `entity_id`, `uei`, `cage`, `ein` |
| `CE-00001-6S` is a uid the published register really holds | `public/data/cedar/register.json` |
| The worked example keeps the two namespaces apart | `WHY_BOTH`, prefixes asserted |
| UEI, CAGE, EIN and NAICS are named as things kept outside the id | `KEPT_OUTSIDE` |
| The sample uid uses Crockford base32 with I, L, O, U removed | regex on `IDENTIFIERS[0].shape` |
| The business register is not claimed as live | `IDENTIFIERS[1].live === false`, see §0 |
| The loop does not claim Federal Reserve **use** or **endorsement** | regex over `LOOP_STAGES` |
| No em dash, no antithesis, no comma-splice fragment | regex over all displayed prose |

The forty-two source kinds behind the door are proved the same way by
`pressSources.test.js`, against collection descriptors and
`cedar_source_registry/sources.jsonl`.

---

## 3. Where the site and the workspace do not agree

Three, all recorded here rather than papered over.

**3.1 `CB-` is specified and unminted.** §0. Three further disagreements
between the specification and earlier documents (check characters on `CB-`,
the absent tribal-enterprise class, and whether the harmonized registry's own
keys are Cedar ids) are listed in `docs/CEDAR_IDENTITY_SYSTEM_2026-09-13.md` §7. The
terminal owns all of them.

**3.2 The Federal Reserve claim is bounded to affiliation.** The owner's
framing was "our team has developed methods that even the Federal Reserve
uses." The workspace evidences team **affiliation** with the Federal Reserve
Board and the Banks of Minneapolis and Philadelphia
(`CREDIBILITY_STRIP` in `src/features/grove/pressMethod.js`), carried with a
disclaimer that affiliation is not endorsement. It does not evidence
institutional use of Cedar's methods.

The page therefore says the record-linkage work *comes out of the team's
years inside the Federal Reserve system* and that Cedar rebuilt it since. A
test refuses the stronger sentence. **If the terminal holds evidence of
institutional use** — a published Fed methodology citing the work, a
contract, a named engagement — record it in this repo and the sentence can be
strengthened the same day.

**3.3 "Cedar does not publish what it resolves" was wrong, and is fixed.**
The owner challenged an earlier sentence saying the register carries
individually owned firms with names withheld. He was right that it read as a
product that resolves firms and then hides them. What is actually withheld is
narrower, and the site now says so:

- The storefront's **Individually Owned Native Businesses** collection
  publishes these firms **by name**, because a nation's own TERO or commerce
  office published them and shared them under stated terms.
- Where the only evidence is a **federal award file**, the activity publishes
  and the owner's name, address and UEI do not
  (`INDIVIDUAL_NATIVE_WITHHELD_FIELDS`, `code/cedar_domain.py`). Per field,
  defaulting to withholding; any published cell resolving to fewer than three
  firms is suppressed; a firm's own website saying it is Native is evidence,
  never permission.
- **`register.json`**, the entity lookup the whole site can read, withholds
  the name for the class outright, because it is a lookup and not a release.

The identifier is on the firm in all three cases. That is the point, and it is
now what the page says.

---

## 4. Copy rulings applied 2026-09-13

- **"Records are only the beginning" is cut**, on both the door and Methods.
  It names a starting point and stops, which describes a gap rather than a
  product and could sit on any data company's page. Replaced with the door's
  *"The hard part is knowing who a record is about."* and Methods'
  *"The records exist. Nothing in them agrees on who is who."*
- **Stop leaning on federal contracting.** Every example that opened on a
  federal contract now opens on a different record type: a 990, a royalty
  statement, a docket, a NAGPRA notice, an ANCSA audited filing, a nation's
  own enterprise register. Contracting is one of twelve.
- **Unlinked rows are mostly intentional, and the page says which.** Two of
  the three non-resolved states are by design and the workspace says so in its
  own words (`link_statuses` in `data/cedar/scopes.json`, which contains the
  phrases "Never a failed match" and "not by failure"): a record that addresses
  a population names no organization, and an individually owned firm's identity
  is withheld by policy. The third, `unresolved`, is work still to do and is
  labelled that way. The site renders those definitions rather than a
  paraphrase.
- **Subscribers can write anything.** The Priorities page led with eleven
  preset cards and filed a request under a `<select>` of seven use cases. The
  free-text box leads the page now and the use case is a free field. The
  service already stored `use_case` as TEXT and never validated it, so no
  server change was needed — but note that
  `priorities.py` aggregates requests by exact `use_case` string, so that
  tally will fragment. If the terminal wants a tally, it should cluster the
  text rather than reintroduce a menu.
- **No sentence ending in a comma and a fragment**, and no antithesis. Both
  are enforced by regex over displayed prose in the test files.

---

## 5. Site changes with no workspace consequence

Recorded so the terminal is not surprised by the diff.

- Methods: "Accuracy has a time dimension" and its illustrative timeline are
  removed; `MAINTENANCE_TIMELINE` is deleted from `pressMethod.js`.
- Methods: the twelve accordions are a tab index of the twelve collection
  marks with one profile open beneath, assembled from the catalog, launch
  descriptors and release log.
- Methods hero: the Lumecon mark fills the empty top right, riding the pull
  quote's row.
- Collections: the Cedar Grove block is one band instead of a page-width
  second storefront.
- Collections: an open record now carries the source document, the resolution
  basis, the release and a copyable citation from `collectionCitation`.
- Overview: a search box that navigates to Explore with the same `q=`.
- `.cp-fade` had **no CSS rule** for five commits, deleted by accident in
  `d11cbde`; the reveal was inert site-wide. Restored, with a test.
- Two overflow bugs fixed: the Entity type filter panel ran ~180px off-screen
  at 1280 and 1440, and `minmax(19rem, 1fr)` put settings and article cards
  past their own grid at 320px.

---

## 5b. Codex's four findings on PR #77, and what each one changed

All four were correct. Recorded because two of them were claims about the
workspace that the site had got wrong, not style notes.

**P1, the unminted business identifier.** Already half-fixed by the
specification work above: the card marks the register as being minted. Codex
also caught a second thing the specification work missed. The copy said flatly
that an individually owned firm carries a business id and no entity id, while
the published register shows all 45 firms in that class carrying `CE-` uids
today. ADR-043 closes the class to new mints and gives those 45 an equivalence
row rather than taking their uids away, so the rule is true going forward and
false about the firms that already exist. The card now states the dated
exception, and a test pins the count at 45 against the register.

**P1, "the identifier was already on every row".** `docs/LINKAGE_COVERAGE.md`
measures 1,485,083 of 2,093,620 flagship rows (70.93%) carrying a resolved
Cedar entity, with contracting at 65.02%, legislation at 19.26%, nonprofits at
11.15% and natural resources at 6.24%. The page promised a "whole footprint",
which would have a subscriber read a 6% answer as a complete one. The measured
figure is now on the page, naming both extremes, and `pressIdentity.test.js`
reads the generated file and fails if any digit drifts. **The terminal owns
re-running `code/1139_linkage_coverage.py apply` when the flagships change; the
site will fail its own build rather than quote a stale figure.**

**P2, the homepage search.** It searches the ten-row release previews Explore
reads, not the full tables, so an entity present in a million-row collection can
return nothing. It now says what it covers under the box.

**P2, the citation copy button.** No fallback when the Clipboard API is absent
or refused. It now mirrors `copyLink`'s prompt, as that handler in the same file
already did.

---

## 5c. The declared column view was never read

Not a Codex finding, and the oldest outstanding item from the owner's relayed
design review: "the signed-in table should default to entity, date, agency,
description, amount and status, with the raw ids in the expanded record."

It turned out that view already exists in the workspace and the site was
ignoring it. Eleven flagship contracts declare `default_columns`, 6 to 8
columns each, chosen by the owner and recorded in
`docs/PUBLIC_DATASET_SPEC_2026-09-05.md`. Prime Contracting declares exactly the
reviewer's shape:

```
canonical_name, action_date, awardee_name, funding_agency,
award_base_description, total_obligations, owner_attribution_status
```

`PressExplore.jsx` preferred the **codebook** and fell back to
`default_columns`. The codebook is a dictionary of every column in the table, so
the fallback was unreachable and the declared view was never used once. Prime
Contracting opened on 44 columns beginning with five raw ids; the other ten
flagships opened on 27 to 54.

The declared view now wins, the codebook is the fallback for a table that has
not declared one, and "Show all 72 columns" still reaches everything. A smoke
test pins it.

**Nothing in the workspace changed for this.** If a flagship should show
different columns, edit its `default_columns` in the contract and the site
follows.

---

## 5d. The deploy had been failing since #76

**The live site did not move for two merges.** Both built, linted and passed
every JavaScript check, then failed the Python step, and `npm run build:site`
and the Pages upload are downstream of it, so they were skipped. Two gates,
both doing their job:

- `server/cedar_press/_press_data.json` is written by
  `scripts/dump-press.mjs` and read by the API. The NEED rename changed the
  catalog name and the dump was never re-run, so the API would have served the
  old one. **If you change the catalog, re-run the dump in the same commit.**
- `docs/ARCHITECTURE.md` carries a measured table of what the pending
  `src/grove` rename would touch, and `test_rename_plan` re-measures it every
  run. The documentation added this session cites source paths, which moved
  four of its numbers. **Any document that names a `src/…/grove` path moves
  this table.**

The gate's own positive control was also pinned to a literal (`` `docs/` 6 ``)
that the world is allowed to move, so it reported "has just injected nothing"
while the gate underneath it worked. It derives its labels now, the way
`_refs_row` in the same file already did for the headline count.

---

## 5e. Tooltips, and the twelve collections on the overview

**`src/pages/grove/Explain.jsx`** is the question mark. One control, two
behaviours decided by the pointer rather than the screen width: a mouse hovers,
a thumb taps and it latches until dismissed. Keyboard focus opens it and Escape
closes it; a mouse click is deliberately inert because hover already governs.
The panel flips its own edge when it would leave the viewport and becomes a
bottom sheet under 560px.

It may only carry prose the product already declares. Three placements so far:

| Where | What it holds | From |
|---|---|---|
| A single collection's scope line | how it is built, what it reads, how a record reaches its entity, coverage | the launch descriptor's `method` and `sources`, the catalog's `linkage` and `coverage` |
| The Explore caption | what a sample record is, and that counts here are counts of samples | the preview's own contract |
| The Methods coverage figure | the denominator, and that the total is a scale figure never a quality one | `docs/LINKAGE_COVERAGE.md` |

**`src/pages/grove/PressCollectionStrip.jsx`** puts all twelve collections on
the overview between the section tiles and the priorities block, each a link
into Explore already narrowed to it. Same point-to-read language as the section
tiles and the shelves, so it is not a thirteenth interaction to learn.

---

## 5f. Cedar on the door, on a phone

Reported from an iPhone: the panel hung in the middle of the screen with page
showing under it, the launcher stayed on top of it, and the suggested questions
came back in full under every answer. All three were real, and all three were
places the door had drifted from `lumecon-website`'s FAB, which is the
reference implementation for this surface.

| Was | Is | The rule it now follows |
|---|---|---|
| The panel was a 36rem card, a flex item stacked above the launcher — on an 844px screen it floated mid-viewport | `position: fixed`, pinned to the bottom edge, top corners only; full width and `min(78dvh, 35rem)` tall under 720px, rising from the bottom | `.cedar-fab-panel` in `src/components/CedarFAB.astro` |
| The launcher stayed visible over the panel's own corner | Hidden while the panel is open (`.cp-dc.is-open .cp-dc__fab`); the panel's close is the way out, and closing hands focus back to the launcher | `body.cedar-popped .cedar-fab { display: none }` |
| Every answer re-printed the remaining starter chips beneath itself | The starter stack belongs to the empty panel and collapses for good on the first question; each answer carries at most three next questions in a quieter row | `collapseChips()` and `renderFollowUps()` in `src/lib/cedarChat.ts` |

`dvh`, not `vh`: mobile Safari's `vh` is the tall viewport, so a sheet sized in
`vh` puts its composer under the address bar. The launcher and the sheet both
carry `env(safe-area-inset-*)` so a notched phone does not park either under
the home indicator.

The next questions come from a table in `src/features/grove/doorCedar.js`
(`FOLLOW_UPS`, and one shared list for the twelve collections) rather than a
score, because the door's bank is ten written answers and twelve collections —
small enough to choose the pairs deliberately. `followUpsFor()` drops anything
the conversation has already answered, so an exhausted thread shows no row
rather than a repeat. `src/features/grove/doorCedar.test.js` holds the bank to
it: every starter classifies back to its own intent, every follow-up is a real
intent with a chip, and none offers the answer it is sitting under.

A click outside the sheet closes it, as it does on the marketing site.

The signed-in Cedar (`.cedar-widget__panel`) was already a bottom sheet and is
unchanged. It keeps its launcher visible on purpose and pads its own bottom to
clear it; that is a different surface with a different reason, written down
where the rule lives.

---

## 5g. Codex's three on #80, and the one that mattered

**The unlinked split had a denominator nobody stated.** `docs/LINKAGE_COVERAGE.md`
carries a third denominator — how many rows can name an entity at all — for
**four** of the thirteen flagships. The other nine read `—`, and `—` means not
measured, not zero. The #79 correction derived `unresolved` by subtracting the
four flagships' structural count from *all* unlinked rows, which published nine
flagships' unmeasured rows as work still to do. Same class of error as the one
it was fixing, in a smaller place.

Stated over the population it was measured on:

| | rows |
|---|---:|
| unlinked, all thirteen | 608,537 |
| measured, four flagships | 600,689 |
| — cannot name an entity | 82,055 |
| — could and does not | 518,634 |
| not measured, nine flagships | 7,848 |

**86.3% of the measured population is work still to do**, against the 86.5%
the cross-product claimed. The conclusion survives being scoped honestly, which
is the only reason it is worth printing at all. `pressIdentity.test.js` now
asserts `structural + unresolved === measuredUnlinked` — the assertion that
fails if anyone reintroduces the cross-product — and that the note prints every
one of the five figures.

The other two were interaction bugs, both real:

- **A dismissal is not a close.** Clicking outside the door's Cedar sheet
  handed focus back to the launcher one frame after the browser focused
  whatever was clicked, so dismissing the sheet ate the click that dismissed
  it. `close(restoreFocus)` — true for the close button and Escape, false for
  an outside pointerdown.
- **A latched tooltip kept a stale nudge.** `Explain.jsx` measured its
  placement only when `open` changed, so a rotation or a crossing of the 560px
  breakpoint left the desktop offset applied to a bottom sheet that pins itself
  to the gutters. It re-measures on resize and rotation, and the sheet carries
  `translate: none !important` so it cannot be nudged even for the frame in
  between.

Both are held by smoke tests verified against the bug: reverting either fix
turns the test red on both projects.

---

## 6. What the terminal owns after this

1. Mint `CB-` per `docs/CEDAR_IDENTITY_SYSTEM_2026-09-13.md` §8, then flip
   `IDENTIFIERS[1].live` and its test in `cedar-press`.
2. Decide whether evidence exists for institutional Federal Reserve use
   (§3.2). If it does, record it here; if it does not, the current sentence
   is the strongest defensible one and should stay.
3. If the request tally matters, cluster free-text `use_case` (§4).
4. Re-run `code/1139_linkage_coverage.py apply` whenever a flagship changes.
   The site quotes its headline total and both extremes and tests them against
   the generated file, so a stale measurement fails the build rather than
   shipping.
5. Nothing else. No dataset, no schema and no publication rule changed in
   this work; the site was brought into line with rules the workspace already
   held.
