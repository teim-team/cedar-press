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

**3.1 `CB-` is specified and unminted.** §0. Four further disagreements
between the specification and earlier documents (check characters on `CB-`,
Cherokee Nation Businesses as an entity or a business, the absent
tribal-enterprise class, and whether the harmonized registry's own keys are
Cedar ids) are listed in `docs/CEDAR_IDENTITY_SYSTEM_2026-09-13.md` §7. The
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

## 6. What the terminal owns after this

1. Mint `CB-` per `docs/CEDAR_IDENTITY_SYSTEM_2026-09-13.md` §8, then flip
   `IDENTIFIERS[1].live` and its test in `cedar-press`.
2. Decide whether evidence exists for institutional Federal Reserve use
   (§3.2). If it does, record it here; if it does not, the current sentence
   is the strongest defensible one and should stay.
3. If the request tally matters, cluster free-text `use_case` (§4).
4. Nothing else. No dataset, no schema and no publication rule changed in
   this work; the site was brought into line with rules the workspace already
   held.
