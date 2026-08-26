# Cedar Press

The standalone site for Cedar Press — the joint data brand of
[Tribal Business News](https://tribalbusinessnews.com) and
[Lumecon](https://lumecon.ai) — served at [cedarpress.ai](https://cedarpress.ai).

The page was ported out of the app (`teim-app`, branch `claude/cedar-press`,
`src/pages/CedarPress.jsx`) to live on its own domain. It keeps the app's
design tokens, marks and copy so the standalone page cannot drift from what
subscribers see inside Cedar Grove.

## What it is right now

A **functioning mockup**. The home page is the sign-in; everything behind it
works, but nothing touches a server yet:

- **Sign-in** — one preview account, printed on the gate:
  `press@cedarpress.ai` / `cedar-demo-2026`. The session lives in
  localStorage. Real accounts arrive with the app's auth
  (swap `src/auth.js` for the API call; the session shape already matches).
- **The collection** — the three launch datasets with the same figure cards
  as Cedar Grove, rows viewable and downloadable as CSV. All numbers are
  demonstration data.
- **Upload datasets** — sign in and drop a CSV on *Add your data*: it parses
  in the browser, lands on the shelf (with a figure when the first two
  columns are label + number), and can be downloaded back or removed.
  Uploads stay in that browser; publishing to a shared shelf is server work.
- **Dark mode** — follows the system preference, with a toggle in the
  masthead; uses the app's approved dark token block.
- **Responsive** — desktop and mobile layouts.

## Develop

```sh
npm install
npm run dev     # local dev server
npm run build   # production build into dist/
```

## Deploy

Pushes to `main` build and deploy to GitHub Pages via
`.github/workflows/deploy.yml`. The custom domain comes from `public/CNAME`
(`cedarpress.ai`), which Vite copies into the build. The repository's Pages
setting must be set to **GitHub Actions** as the source.
