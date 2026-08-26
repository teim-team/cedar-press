# Cedar Press

The standalone site for Cedar Press — built by [Lumecon](https://lumecon.ai),
available exclusively through
[Tribal Business News](https://tribalbusinessnews.com) — served at
[cedarpress.ai](https://cedarpress.ai).

The surface is ported from the app (`teim-app`, branch `cedar-grove/09-press`,
"Cedar Press, whole, on the Grove it stands on", taken at the
`claude/cedar-grove-hardening-kxdpft` tip that contains it). Pages, features,
styles and tests are carried verbatim — the same gate, reader, shelf, article,
methods, tribal-data-request, research-access and what's-new surfaces, on the
app's own tokens — so the standalone site cannot drift from what the app
renders. `docs/PORT.md` lists the seams that differ.

## What it is right now

A **functioning mockup**: the front door is the real gate (the teal split
sign-in), everything behind it works, and nothing touches a server yet.

- **Sign-in** — the gate's own form against two preview accounts
  (localStorage sessions, printed on the gate's log-in panel):
  - `press@cedarpress.ai` / `cedar-demo-2026` — the Cedar Press tier
  - `press-plus@cedarpress.ai` / `cedar-demo-2026` — Cedar Press+, the pro
    shelf

  Real auth replaces `src/context/authContext.jsx` and `src/api.js`; the
  session shape (`workspace_tier`) already matches what `workspaceTier.js`
  reads. Access-code activation stays gated off by
  `pressSignup.PRESS_ACTIVATION_AVAILABLE`, exactly as in the app.
- **The reader** — briefs, the collections shelf with per-tier reach and
  downloads, the citation register, the Grove teaser, the close.
- **Satellite pages** — `/methods`, `/tribal-data-request`,
  `/research-access`, `/whats-new`, and hosted articles at `/articles/:id`.
- **Theme** — the press pages pin the paper look in dark mode by design
  (`press.css`: `.teim-rd--paper` re-pins the light tokens over the dark
  remap), so the standalone document declares `color-scheme: light`.
- **Responsive** — the app's own breakpoints, verified on desktop and phone.

## Develop

```sh
npm install
npm run dev     # local dev server
npm run test    # the ported press feature tests (node --test)
npm run build   # production build into dist/ (copies index.html to 404.html
                # so GitHub Pages serves the SPA's client routes)
```

`VITE_APP_URL` (optional, build time) names the app's origin for the
"open the app" links (Ask Cedar, Get Cedar Grove, the plan page); without it
they land on lumecon.ai.

## Deploy

Pushes to `main` build and deploy to GitHub Pages via
`.github/workflows/deploy.yml`. The custom domain comes from `public/CNAME`
(`cedarpress.ai`), which Vite copies into the build. The repository's Pages
setting must be set to **GitHub Actions** as the source.
