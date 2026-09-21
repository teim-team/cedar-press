import { execSync } from "node:child_process";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// THE ONE QUESTION NOBODY COULD ANSWER FROM A PHONE: is what I am looking at
// the build that was just pushed, or the one from a week ago?
//
// cedarpress.ai is served from S3 behind CloudFront, so a stale page can be a
// browser cache, a CloudFront cache, or a publish that never ran -- and for a
// month it was the third one, silently. Nothing in the page said which build
// it was, so "it hasn't updated" and "it updated and looks the same" were
// indistinguishable to the person looking at it.
//
// The commit is stamped into the bundle here and shown on /settings. Reading
// it takes five seconds on a phone and settles the question outright.
//
// `git` is absent in some build sandboxes and the tree can be dirty locally,
// so this never throws: it degrades to "unknown", which the test below treats
// as a local build rather than a failure.
function gitSha() {
  try {
    return execSync("git rev-parse --short HEAD", { stdio: ["ignore", "pipe", "ignore"] })
      .toString()
      .trim();
  } catch {
    return "unknown";
  }
}

// Served at the domain root (cedarpress.ai), so base stays "/".
//
// The build output is `dist-site/`, not vite's default `dist/`, and that is
// not cosmetic. The 2026-09-02 consolidation brought the data workspace into
// this repository, and it TRACKS 295 files under `dist/` — `dist/review/`,
// the sample bundle `scripts/import_cedar_manifest.py` reads. Vite empties
// its output directory before every build, so with the default every
// `npm run build` (and `npm run test:smoke`, which runs one) deleted all 295
// of them, silently, from the working tree. It happened twice before anyone
// noticed the missing files.
//
// Whatever else moves, these two must move together: `outDir` here and
// `upload-pages-artifact`'s `path:` in .github/workflows/deploy.yml. Change
// one alone and the deployment publishes the data bundle, or nothing.
export default defineConfig({
  plugins: [react()],
  base: "/",
  build: { outDir: "dist-site" },
  define: {
    __PRESS_BUILD_SHA__: JSON.stringify(process.env.PRESS_BUILD_SHA || gitSha()),
    __PRESS_BUILD_TIME__: JSON.stringify(new Date().toISOString()),
  },
});
