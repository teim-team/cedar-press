// Smoke tests run against the built site, not the dev server.
//
// The bugs these are here to catch are build-time and cascade-level: a
// renamed export that the bundler happily ships, a stylesheet whose rules
// stop applying, a route that 404s once it is a static file rather than a
// dev-server rewrite. `vite dev` hides all three, so the web server below
// builds first and serves the build (`dist-site`, per vite.config.js).
import { defineConfig, devices } from "@playwright/test";

import { ACCOUNTS_JSON } from "./tests/demoAccount.js";

// Overridable, because the port is shared state between checkouts. See the
// `reuseExistingServer` note below for what that cost once.
const PORT = Number(process.env.CEDAR_PRESS_SMOKE_PORT ?? 4180);

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
    // NEVER measure a build this run did not make.
    //
    // This was `!process.env.CI`, which reads as a local convenience and is
    // not one: the port is hardcoded, so a run in one checkout attached to
    // whatever preview server another checkout had left listening on 4180 and
    // reported on THAT bundle. It does not announce itself — every assertion
    // about the page passes, against the wrong page — and it surfaced only
    // because the two tests at the bottom of the suite read `dist-site/` off
    // this checkout's disk, where the build had never been written. The
    // failure read as "the build is broken"; the truth was "54 of these
    // results belong to someone else's tree".
    //
    // Two checkouts at once is what CEDAR_PRESS_SMOKE_PORT is for. Without
    // it, a busy port is now a loud `--strictPort` refusal to start, which is
    // the failure a reader can act on.
    reuseExistingServer: false,
    timeout: 180_000,
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
