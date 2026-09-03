// Smoke tests run against the built site, not the dev server.
//
// The bugs these are here to catch are build-time and cascade-level: a
// renamed export that the bundler happily ships, a stylesheet whose rules
// stop applying, a route that 404s once it is a static file rather than a
// dev-server rewrite. `vite dev` hides all three, so the web server below
// builds first and serves the build (`dist-site`, per vite.config.js).
import { defineConfig, devices } from "@playwright/test";

import { ACCOUNTS_JSON } from "./tests/demoAccount.js";

// The port the suite builds onto and serves from.
//
// It used to be the constant 4180 with `reuseExistingServer` on, and that
// combination silently tests the WRONG BUILD. `reuseExistingServer` means
// "if something already answers on this URL, do not start a server" — it
// does not, and cannot, check that the thing answering is this checkout's
// build. Anyone with a `vite preview` up on 4180 — a second worktree, a dev
// window left open, another agent — gets attached to instead, so `npm run
// test:smoke` reports on their `dist-site/` while yours is never built. It
// has already happened: a run failed against a build the tree had never
// produced, and the same suite passed 56/56 once it was given a port of its
// own.
//
// PORT overrides it, so parallel checkouts can each take one. The default
// is derived from the checkout's own path rather than shared, which makes
// the collision impossible by default instead of merely documented. Range
// 41000-41999, above the ephemeral-port floor on the platforms this runs on.
import { createHash } from "node:crypto";

const PORT = Number(process.env.PORT)
  || 41000 + (parseInt(createHash("sha1").update(process.cwd()).digest("hex").slice(0, 8), 16) % 1000);

export default defineConfig({
  testDir: "./tests",
  // Smoke tests assert on a shared, read-only site: parallelism is safe and
  // the suite is meant to be quick enough that nobody skips it.
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  // One retry in CI, none locally. A smoke test that needs more than one
  // retry is not flaky, it is failing.
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? "github" : "list",
  use: {
    baseURL: `http://localhost:${PORT}`,
    trace: "on-first-retry",
  },
  projects: [
    { name: "desktop", use: { ...devices["Desktop Chrome"] } },
    // A real phone profile, not a narrow desktop window: touch and the
    // absence of hover change what this page renders. Chromium rather than
    // the profile's default WebKit, so the suite needs one engine installed
    // rather than two — these are smoke tests, not a compatibility matrix.
    { name: "phone", use: { ...devices["iPhone 13"], browserName: "chromium" } },
  ],
  webServer: {
    command: `npm run build && npm run preview -- --port ${PORT} --strictPort`,
    url: `http://localhost:${PORT}/`,
    // Never reuse. The suite's contract is "test the build this checkout
    // produces", and reuse is the one setting that can quietly break it:
    // adopting whatever is already listening means the `npm run build` in
    // `command` above never runs, so the tests describe someone else's
    // dist-site. A rebuild costs about a second and a half; a green run
    // against the wrong bundle costs however long it takes to notice.
    reuseExistingServer: false,
    timeout: 120_000,
    // The suite builds the deployment it means to test, rather than
    // inheriting whatever the machine happens to have configured.
    //
    // Empty VITE_API_URL pins this to STANDALONE: with a developer's local
    // API in the environment the same build would be CONNECTED, the gate
    // would authenticate against a server these tests never started, and the
    // failure would read as a broken page.
    //
    // The demo account is the suite's own throwaway (tests/demoAccount.js).
    // Without one the standalone gate signs nobody in — correctly — and
    // every test past the door would fail.
    env: { VITE_API_URL: "", VITE_PRESS_DEMO_ACCOUNTS: ACCOUNTS_JSON },
  },
});
