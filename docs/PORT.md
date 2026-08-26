# What differs from the app

The source of truth is `teim-team/teim-app`, branch `cedar-grove/09-press`
(read at the `claude/cedar-grove-hardening-kxdpft` tip, which contains it plus
the hardening pass). Everything under `src/pages/grove`, `src/features/grove`,
`src/components/grove` and `src/styles` is verbatim from there except the
seams below — when the app's press surface moves, re-port and re-apply these.

## Replaced modules (the server seams)

| File | Here | In the app |
| --- | --- | --- |
| `src/context/authContext.jsx` + `src/context/useAuth.js` | Mock provider: two preview accounts, localStorage session, same `{ user, loading, login, logout, refreshSession }` contract | Real session against the backend |
| `src/api.js` | Stubs for `validatePressCode` / `activatePressAccount` (unreachable while `PRESS_ACTIVATION_AVAILABLE` is false); reject with the server's error-code shape | Real API module |
| `src/main.jsx` | The route table (the reader at `/`, satellites on their paths) and the AuthProvider mount | `App.jsx` owns routes |

## Edited in place

- `src/features/grove/pressRoutes.js` — paths lose the `/press` prefix; the
  reader is this site's root.
- `src/features/grove/appLink.js` (new) — `/app`, `/app/grove` and the plan
  page become absolute links into `VITE_APP_URL` (default lumecon.ai), used
  by `CedarPress.jsx`, `PressCedarFab.jsx` and `PressShelf.jsx` in place of
  their in-app `<Link>`s.
- `src/pages/grove/PressGate.jsx` — "Forgot password?" mails
  contact@lumecon.ai instead of the app's `/?forgot=1`; the log-in panel
  prints the preview account (leaves with real auth).
- `src/pages/grove/CedarPress.jsx` — the masthead adds Sign out beside the
  signed-in address (the preview account is shared; the app's rail owns this
  there).

## Mobile-specific behavior (standalone additions)

Phones are a first-class surface here, not a shrunk desktop; these diverge
from the app's press branch on purpose and live in `press.css` +
`PressShelf.jsx`:

- The gate flows and scrolls under 880px (the app's viewport-fixed split
  clipped the press hero), opens on the sign-in panel with its own wordmark,
  and renders the proof pillars as compact rows instead of stacked squares.
- The shelf is tap-native on coarse pointers: the first tap on a tile opens
  the read panel (scrolled into view) instead of downloading, the panel
  carries its own Download button, selection is sticky, and the hint copy
  says "Tap" instead of "Point".
- Justified body copy reads ragged-right under 640px (justification tears
  into rivers at phone measures) and the Ask Cedar launcher travels light
  there (no context line, tighter pad).

## Not ported

The rest of the app: the grove workbench, python package, server, and every
non-press page. The article images (`public/pitch/lanes/`), the mark
(`public/lumecon-mark.png`) and the brand fonts (`public/fonts/`) came across
as-is.
