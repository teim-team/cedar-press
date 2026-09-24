# Cedar Press design system — the shared shell

The sitewide consistency contract: every page renders through these shared
pieces, and a page-local variant of any of them is a bug. Mapping of the
system's named components to where each lives today.

| Component | Implementation | Notes |
|---|---|---|
| SiteHeader + PrimaryNav | `PressMast` (`src/pages/grove/PressChrome.jsx`) | One masthead: logo, "Built by Lumecon… through Tribal Business News", nav (`NAV` array is the single source of section order/labels), account control. |
| PageContainer | `.cp` (`src/styles/grove/press.css`) | `--cp-measure: 1560px`, `padding-inline: 2.4rem` (1.15rem mobile). Articles keep a narrower *inner* prose measure; their hero, sponsorship and footer align to the outer grid. |
| SectionEyebrow | `.cp-sec__band` / `.cp-hero__access` | Small uppercase mono labels: `SECTIONS`, `ORIGINAL RESEARCH`, `SPONSORSHIP`. Three levels: eyebrow → major heading → mono metadata line. |
| ActionPill | `.cp-start__act` | The overview's start-here verbs. Reuse for any future inline CTA row; do not restyle per page. |
| SponsorshipUnit | `PressAd` + `AD_SLOT` (`pressAds.js`) | One component, shape variants per slot (banner on the overview, sidebar in articles). Same `SPONSORSHIP` cap, border, tint and CTA everywhere. Enquiries go to TBN's media kit (`AD_ENQUIRY_HREF`). |
| AskCedarFAB | `PressCedarFab` | Identical launcher, offset and dimensions on every page; context arrives via props (`examples`, `gated`) and events (`cedar:open`, `cedar:ask-collection`), never via per-page styling. The PANEL is `.cp-dc__*`, shared with the door and with lumecon.ai's `CedarFAB.astro` — see "Cedar" below. |
| CollectionRail | `PressCollectionRail` (`src/pages/grove/PressCollectionRail.jsx`) | The twelve collections, once. Two modes: `preview` on the door, `app` behind the paywall, where a collection the plan cannot open stays in the rail and is visibly locked. Never a second list of the same twelve. |
| CollectionAtlas | `CollectionAtlas` (in `PressExplore`) | The catalogue, in the table: one row a collection, its coverage, size, release and what opens it, locked ones included. What "show me everything" means when nothing has been asked yet; the pooled records come back the moment a search or filter turns the question back into one about records. |
| LockedCollection | `LockedCollection` (in `PressExplore`) | The same toolbar, the collection's own declared column headers, the same row density, the same status bar — with the values withheld by never being fetched. One line says what opens it. A blank page with an upsell box asks somebody to buy a thing they have not been shown. |
| Briefing | `PressBriefing` | The overview: one lead, three signals, one collection, one question. Every line read from the release record and the article list, so it cannot go stale. It replaced six cards that restated the nav bar. |
| CollectionExplorer | `PressExplore` | Rail, one toolbar row, the table, one status bar. Nothing between the toolbar and the first record: description lives under the records, controls live in the bar, and the collection's name is the h1 at toolbar size. The signed-in Collections page IS this component; the door mounts the same rail and the same table. |
| RecordTable | `PressRecordTable` (`Rows`, `Cards`) + `recordColumns.js` (`columnPlan`) | The record table, once. The signed-in viewer and the signed-out door both mount it; the door mounts it `readOnly` (no sort control, no record link, since neither leads anywhere without a subscription). A second table that draws records is a bug. |
| CollectionProfile | `PressCollectionAbout` | The deep-linkable profile at `?c=<id>&about=1`: a side sheet on a wide screen, the whole screen on a phone. Every field is read from the release (descriptor, codebook, ledger); nothing on it is written. |
| CollectionReads | `articlesDrawingOn` (`pressArticles.js`) | The loop between the records and the journalism, from the `draws` an article already declares. The collection's foot names the newest piece; its profile lists them all; the article's rail and its data cards link back into the table; an entity profile's collection headings open the table carrying both the collection and the entity. One relationship, read both ways, never a second list. |
| ReleaseSpecimen | `PressReleaseSpecimen` | The hero's release bookkeeping card. Facts from `collections.manifest.json` only, and never a delta — the manifest records the current release, not the one before it. |
| SiteFooter | `PressFoot` (`PressChrome.jsx`) | One footer, navy, full-bleed, thin teal top edge, nav left / publisher domains right — on every page including articles. `flush` only where the preceding band is already navy (the overview's close). |
| Breakpoints | `press.css` media queries | Stack points in use: 600 / 640 / 720 / 760 / 880 / 900 / 980 / 1000 / 1050 / 1100 / 1250. New responsive work picks from these rather than inventing new ones. Inspected at 1440 / 1280 / 1024 / 768 / 430 / 390 / 320. |
| Tokens | `redesign.css` `:root` vars | `--teal`, `--dteal`, `--ink`, `--line`, `--radius-card`, `--mono`, `--sans`; `--cp-measure` for the grid. Never hex-code a brand color in a page rule. |

Reference pages: the article template and the overview are the system's
anchors. When another page drifts, pull it toward those two, not the other
way around.

## Cedar, on three surfaces

One conversation, rendered by one set of classes. `PressDoorCedar` (the
signed-out door), `PressCedarFab` (behind the paywall) and lumecon.ai's
`src/components/CedarFAB.astro` all draw `.cp-dc__*`: teal identity band with
a status dot, a transcript of bubbles with the mark beside Cedar's, quick
replies inside the transcript, a one-line composer, one line of
expectation-setting under it. Full screen on a phone.

**The size is the site's, measured.** The owner put the two side by side and
the Press panel was wider. `.cp-dc__panel` is now `min(380px, 100vw - 1.8rem)`
wide with the site's right offset (`clamp(0.9rem, 2.2vw, 1.5rem)`) and
ceiling (`100dvh - 5rem`), and its transcript is the site's transcript cap,
`min(400px, 52vh)`, as a height. Measured off lumecon.ai's built page at 1280,
1440 and 1920 by 900: 380 x 577.88, 24px from the right edge. The smoke suite
holds both Press panels to those numbers within 2px, and
`cedarPanelParity.test.js` holds the rules to what the suite assumes.

**It is one conversation, not one look.** Both surfaces run
`cedarConversation.js` through `useCedarThread`: "tell me more" goes deeper
on the last topic, the same question twice is answered deeper or acknowledged
rather than replayed, a question naming two topics gets the second as the
first quick reply, and a miss offers the closest topics. The door's bank is
`doorCedar.js`; the reader's answers are the service's. The line under the
composer is the site's expectation line (`EXPECTATION_LINE`), not a
description of the machinery: the old "answers from prepared material" read
as a menu of preset answers, and it is gone.

The **panel's own tokens** are declared on `.cp-dc` and `.cedar-widget`
rather than only on `.cp-door`. That is not tidying: every `--door-*` the
panel reads is declared on the signed-out page, and mounted inside the
reader they resolve to nothing, so `background: var(--door-surface)` is
dropped and the panel paints as a transparent hole.

**The panel opens with something to ask.** `examples` defaults to four
questions, each already scoped to a collection so the tap that asks also
picks the release the answer comes from. Nine of the eleven mounts passed no
examples and opened on a greeting and an empty box, which is the worst moment
to ask a reader to think of a question.

**What an answer rests on is a sentence, not a badge.** Under the answer:
"Based on *Native Federal Contractors v1*, updated September 4, 2026. View
supporting records", or four words when Cedar composed it. No chip, no
"Evidence used" disclosure, no taxonomy prefix. A cited-record count is
printed only when the service supplies one — absent, never `0`.

## Motion

One curve, three kinds of movement, and two audiences that get less.

**The curve.** `--cp-ease: cubic-bezier(0.22, 1, 0.36, 1)`, declared once on
`.teim-rd` at the top of `press.css`. It is the family's `--ease`
(lumecon-website `global.css`), the page entrance (`cp-page-in`) and the
door's `--door-ease`, which is now an alias of it. Every rule written since
2026-09-24 says `var(--cp-ease)`; `pressMotion.test.js` fails a rule in the
touched set that names a curve instead. **Drift, recorded rather than
fixed:** `cubic-bezier(0.2, 0, 0, 1)` survives on `.cp-fade` and on a dozen
older card hovers, and plain `ease` on more; each is pulled onto the token
when its rule is next touched, not in a sweep that would put sixty
unrelated lines in one diff. The Cedar panel (`.cp-dc`, `.cedar-widget`)
declares the same value for itself and is left exactly as PR #119 left it.

**Arrival** — once, on scroll, never on the first screen. `.cp-fade` blocks
are revealed by `useFadeIn` (see the hook for why anything on the first
screen is marked `cp-fade--now` and does not transition). Inside a revealed
block, a set reads in order rather than landing as a slab: the door's four
claims and three ways in stagger by `transition-delay` on the items
themselves (0/70/140/210ms); the twelve collection tiles and Methods' seven
process stages stagger by a keyframe (`cp-tile-in`, `cp-stage-in`) on each
item's own `--i`, 45ms and 55ms a beat, with a `backwards` fill and no
forward fill, so an arrived element is free to answer the pointer. Both are
inert under `.cp-fade--now` — which, measured on the built door, is what the
twelve are on every common desktop window (their top sits at 0.77 to 1.01 of
the window height from 1280x720 to 1920x1080, inside the hook's 1.1 slack), so
on a desktop they arrive with the page and the stagger is what a phone, or a
window under about 1100 wide, sees.

**Response** — a fine pointer, or keyboard focus. A lift of at most 3px with
a soft shadow (the twelve: `translateY(-2px)` + `--door-shadow-surface`; the
hero frame 3px). Every `:hover` on the door and on Methods' process rail is
inside `@media (hover: hover) and (pointer: fine)`, and `:focus-visible`
lifts a tile the same way. The pattern is lumecon-website PR #353 (the Why
Lumecon cards). Nothing loops, nothing moves after it has arrived, and
nothing around the lifted element moves.

**State** — colour only. The shelf whose collection is in hand
(`.cp-dcol__shelf.is-active`) takes the accent on its rule and its plan
name; a tapped tile is `.is-on`. A state is never a movement.

**Reduced motion** removes travel, not response: no transition, no
animation, every arrival already in place, and a pointed tile raised on the
next frame rather than over 180ms. The old rule of also cancelling the lift
made the pointer response vanish for that reader, which is not what the
setting asks for.

**Touch** gets no hover state anywhere. A touch browser pins `:hover` to the
last thing tapped, so an unguarded lift leaves the tile a reader chose raised
beside the one they chose next. The tap's own state (`.is-on`,
`aria-pressed`) is what a finger gets. The phone smoke project runs with
`hasTouch`, and "a finger gets no hover state" asserts it.

**What stays still, and why.**

- Figures. No count-ups on record or collection counts: a frame mid-count is
  a number that appears in no release, on a product whose first invariant is
  that every figure traces to one; and every headline figure (the door's
  facts, What's new's pulse) sits on a first screen, where the site's own
  rule is that nothing moves after paint.
- The record table, the column control and a record's field groups. A
  working surface; every screen of motion there costs rows, and its card
  mode renders only at touch widths, where there is no hover to answer.
- The masthead and the footer. Structural, identical on every page.
- The Cedar launcher and panel. Reworked in PR #119, and shared with the
  site; sized and measured there.
- Expand/collapse. Already native `<details>` wherever a note is long:
  Methods' reasoning, What's new's change lists, a record's field groups, the
  collection profile, the request page's requester rules. Nothing else on
  the site shows a long note all at once, so nothing new was folded.

Radius stays at 10px or under (the tiles are 4px), nothing added is a
gradient, and no copy changed.

Measured by: `the door's twelve arrive and respond` (3), `a finger gets no
hover state`, `Methods' seven stages arrive as a sequence` in
`tests/smoke.spec.js`, and `src/features/grove/pressMotion.test.js` (7).

## Where this is deliberately not the Lumecon website

`lumecon-website` is the family's visual source of truth and the material,
type and teal rules above come from it. Two differences are intentional:

- **The strongest object on a Cedar Press page is a record table**, not a
  photograph. Where the marketing site leads with an image, this one leads
  with a release, a ledger or a field list.
- **Navy is structural, and one region per page is enough.** The rail, the
  locked-collection inset and the entity profile's names block each own the
  navy on their page; nothing else does.

## Rules that exist because something broke

- `position: relative` on `.cp-rail__item`. Without it the rail's background
  painted over its own unpositioned children and every row was visible and
  unclickable.
- `overflow: clip`, not `hidden`, on `.cp-ex__frame`. `hidden` makes it a
  scroll container and the sticky rail then sticks to a box that never
  scrolls.
- A closed `<details>` hides its children through the UA's own mechanism, so
  no media query can open one. `MethodsIndex` reads the breakpoint in
  JavaScript and writes the `open` attribute.
- Colour is stated on `.cp-rail__name`, not inherited: something upstream
  sets `--ink` on spans, and the rail rendered twelve row counts with no
  collection names attached.
- Every box between `.cp-ex__frame` and the scroller carries `min-height: 0`.
  A flex item's floor is its content, so without it the table refuses to be
  shorter than its rows, the chain grows past the frame, and the height set
  on the frame is silently ignored.
- The collections page's frame height is measured in JavaScript
  (`--cp-frame-h`, `CedarPressData`) rather than written as a `calc`. The
  chrome above it is a masthead plus a title, two heights at two widths, and
  the hardcoded `calc(100dvh - 12rem)` was wrong by 14px at 1440 and by more
  on a phone.
- A full-page screenshot of a page with revealed sections is a page of white
  gaps: `.cp-fade` starts at opacity 0 and arrives on scroll. Anything
  capturing the site has to walk the page first.
- The phone's `Explain` sheet docks to whichever edge its question mark is
  not on. Pinned to the bottom it covered a trigger low on the page, so the
  tap that should have closed it landed on the sheet and the control looked
  stuck open.
- `/data` has no page title. The collection's own name is the `h1`, inside
  the pane. A band above a screen-filling table of one collection said a
  second time what the rail and that line already said.
- Nothing goes above the records on `/data` that is not a control. The
  legend, the state caption and the Cedar Press+ line each cost every screen
  in the product some of its rows; they are in the status bar and the rail
  now. A short label there carries the full sentence as its `aria-label`, so
  "8/63 columns" still announces itself as "Show all 63 columns".
- A link to a collection carries `?c=<id>`. `/data` flat opens on Federal
  Funding, so "View collection" from a NAGPRA release used to land a reader
  on the wrong one.
- Two class names were doing two jobs each, and the app inherited the door's
  navy in both cases: `.cp-why` was the door's passage band AND Methods'
  reasoning disclosure; `.cp-rail` was the collection rail AND Methods'
  seven-stage diagram. Renamed `.cp-reason` and `.cp-proc`. Methods halved.
  Before adding a class, grep it.
- Navy in the app is the rail, one high-stakes disclosure, the Cedar answer
  state and the footer. Nothing else.
