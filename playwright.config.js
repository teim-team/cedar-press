// Smoke tests run against the built site, not the dev server.
//
// The bugs these are here to catch are build-time and cascade-level: a
// renamed export that the bundler happily ships, a stylesheet whose rules
// stop applying, a route that 404s once it is a static file rather than a
// dev-server rewrite. `vite dev` hides all three, so the web server below
// builds first and serves the build (`dist-site`, per vite.config.js).
import { defineConfig, devices } from "@playwright/test";

import { ACCOUNTS_JSON } from "./tests/demoAccount.js";

const PORT = 4180;

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
    reuseExistingServer: !process.env.CI,
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
