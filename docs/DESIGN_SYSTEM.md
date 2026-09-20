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
| CollectionExplorer | `PressExplore` | Rail + selected-collection header + table/cards + release footer, as one object. The signed-in Collections page IS this component; the door mounts the same rail inside its hero frame. |
| RecordTable | `PressRecordTable` (`Rows`, `Cards`) + `recordColumns.js` (`columnPlan`) | The record table, once. The signed-in viewer and the signed-out door both mount it; the door mounts it `readOnly` (no sort control, no record link, since neither leads anywhere without a subscription). A second table that draws records is a bug. |
| CollectionProfile | `PressCollectionAbout` | The deep-linkable profile at `?c=<id>&about=1`: a side sheet on a wide screen, the whole screen on a phone. Every field is read from the release (descriptor, codebook, ledger); nothing on it is written. |
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
