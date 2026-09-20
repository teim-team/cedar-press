# Mockups and review artifacts

Working material for a design decision, not shipped code. Nothing here is
imported by the app.

## `cedar-press-table.html`

**Superseded, 2026-09-20 — kept as the record of the decision, not as a
proposal.** It redrew the in-product Explore table in the language of the
door's collection pane (`.cp-pane__table`), which was the table the owner
picked out.

It went the other way in the end. The door's pane was drawing four columns of
its own naming while the product opened on the collection's own fields behind
a pinned Cedar identity block, so a visitor was shown a picture of something
they would not recognise on their first day. Rather than restyle the product
as the marketing table, `Rows` and `Cards` moved into `PressRecordTable.jsx`
and the door mounts them read-only. `.cp-pane__table` and its nine cell
classes are deleted, so the left-hand column of the comparison below no longer
describes anything that exists.

The rows are real: the first twelve of "All 12 open collections", read out of
the running app, from the ten-row samples in `public/data/cedar/samples`. The
marks are the app's own, from `src/pages/grove/pressCollectionIcons.jsx`.

Open it through `npm run dev` (`/mockups/...` is not served; copy it into
`public/` temporarily, or open it from disk and accept the system font stack —
the `@font-face` rules point at `/fonts/*.woff2`).

What it proposes, in short:

| | now | proposed |
|---|---|---|
| columns | 7 + a control column | 5 |
| truncated per row | 4 (name, alias, observation, amount basis) | 0 |
| collection | a teal link, repeated | the collection's own mark + name |
| Cedar id | grey, under the name, same weight as the alias | teal, always the second line |
| amount basis | clipped, every row | wrapped, once per run |
| state ("102 of 110") | a paragraph above the table | the mono caption band the door uses |

## Measurements taken while reviewing (2026-09-19)

Live, against this checkout, desktop 1440x900 and phone 390x844:

- Page length, phone: `/methods` 15.6 screens, `/data` 8.5, `/priorities` 6.6,
  `/settings` 4.4 (for 326 words), `/research-access` 1.7 (for 108 words).
- The resting Cedar launcher covers page content on every surface tested.
  `document.elementsFromPoint` under it returns: `/settings` (phone) the
  `Manage TBN membership / Sign out` row, `/articles` a brief's card, `/data`
  the collection blurb, `/methods` the first claim line of section 01.
  `press.css` already names this ("A PILL THAT IS ALWAYS THERE IS ALWAYS ON TOP
  OF SOMETHING"); shrinking it to a circle reduced the area, not the problem.
  lumecon.ai's FAB steps aside as the page scrolls — not ported.
- `/data` logs a React nesting warning on every load: `Explain.jsx` renders its
  panel as a `<span>` containing `<p>` elements, and the shelf puts it inside a
  `<p>`. The browser silently closes the outer paragraph.

## Open, and deliberately not decided here

1. The panel behind the login floats clear of the bottom edge and keeps its
   launcher visible while open; lumecon.ai docks its panel to the edge and
   hides its FAB at every width. `press.css` records the float as a considered
   choice, so it was left alone. One line either way.
2. The full-screen phone panel covers the page, so a click outside it is no
   longer a dismissal (`smoke.spec.js` checks both contracts). It is still
   `role="dialog"` without `aria-modal`, which is right for the corner card at
   desktop widths and arguably wrong for the full-screen one. A
   viewport-conditional ARIA property is a bigger change than this pass.

## The screens PDF

Every screen, desktop and phone, in one file:
`cedar-press-screens.pdf`. It is captured against the running stack — the
built site talking to the Cedar Press API, which talks to a contract-faithful
stand-in for the Cedar service — at 1440x900 and 390x844, with any page taller
than one screen cut into screen-sized slices in reading order rather than
squashed onto one plate.

Two things a capture script has to know, both learned the hard way:

- `npx playwright test` rebuilds `dist-site` in standalone mode
  (`VITE_API_URL: ""`), which un-wires the local API. Rebuild with the API URL
  and patch the CSP's `connect-src` before capturing.
- `.cp-fade` sections start at opacity 0 and arrive on scroll, so a full-page
  screenshot of an unscrolled document is a page of white gaps. Walk the page
  first.

`.gitignore` excludes `*.pdf`, so the file is generated and handed over rather
than committed.
