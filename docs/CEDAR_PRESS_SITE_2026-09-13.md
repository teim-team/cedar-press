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

**`CB-` is decided and unminted, and the site is now written around that
gap.** The Methods page names a Cedar business id, describes it correctly
per the 2026-09-06 decision, and deliberately shows **no sample**, because
the only form that exists is `business_source_id` (for example
`TBD-030:4033`), which carries a source code and therefore breaks the
decision's first rule that the number means nothing.

`src/features/grove/pressIdentity.js` carries `shape: null` on that card with
the reason beside it, and `pressIdentity.test.js` asserts it stays null. When
the terminal mints `CB-`, that assertion fails on purpose: change it, set
`shape: "CB-0000001"`, and the card shows the sample.

---

## 1. What the site now claims

The Methods page (`/methods`) was a description of a careful process. It now
carries the argument the product is actually sold on, in three sections.

### Identity

Two identifiers, side by side.

| | Cedar entity id | Cedar business id |
|---|---|---|
| Names | government, agency, NHO, consortium, college, CDFI, nonprofit, nation-owned enterprise | a firm as one source named it, then the resolved firm those sightings add up to |
| Form shown | `CE-1A7K3-MQ` | none yet, see §0 |
| Fields | `cedar_uid` | `business_source_id`, `entity_id` |
| Survives | recognition change, rename, reorganisation | four spellings in four directories, a source conflict, acquisition by a nation |

The load-bearing case, in the owner's framing: an individually owned firm
affiliated with a nation but not owned by one gets a **business id and no
entity id**, from first sighting, so the series is continuous if a nation
later buys it.

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
| `business_source_id`, `entity_id` are real fields | `cedar_source_registry/schema/{source_record,harmonized_entity}.schema.json` |
| The sample uid uses Crockford base32 with I, L, O, U removed | regex on `IDENTIFIERS[0].shape` |
| The business card shows no sample | `shape === null`, see §0 |
| The loop does not claim Federal Reserve **use** or **endorsement** | regex over `LOOP_STAGES` |
| No em dash, no antithesis, no comma-splice fragment | regex over all displayed prose |

The forty-two source kinds behind the door are proved the same way by
`pressSources.test.js`, against collection descriptors and
`cedar_source_registry/sources.jsonl`.

---

## 3. Where the site and the workspace do not agree

Three, all recorded here rather than papered over.

**3.1 `CB-` is decided and unminted.** §0. The terminal owns minting it.

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

1. Mint `CB-` per `docs/CEDAR_BUSINESS_ID_DECISION_2026-09-06.md`, then flip
   `IDENTIFIERS[1].shape` and its test in `cedar-press`.
2. Decide whether evidence exists for institutional Federal Reserve use
   (§3.2). If it does, record it here; if it does not, the current sentence
   is the strongest defensible one and should stay.
3. If the request tally matters, cluster free-text `use_case` (§4).
4. Nothing else. No dataset, no schema and no publication rule changed in
   this work; the site was brought into line with rules the workspace already
   held.
