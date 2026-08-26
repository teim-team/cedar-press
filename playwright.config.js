// Smoke tests run against the built site, not the dev server.
//
// The bugs these are here to catch are build-time and cascade-level: a
// renamed export that the bundler happily ships, a stylesheet whose rules
// stop applying, a route that 404s once it is a static file rather than a
// dev-server rewrite. `vite dev` hides all three, so the web server below
// builds first and serves `dist`.
import { defineConfig, devices } from "@playwright/test";

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
  },
});
