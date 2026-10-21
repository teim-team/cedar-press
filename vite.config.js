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
// The build output is `dist-site/`, not vite's default `dist/`. `dist/` was
// the retired data workspace's gitignored output directory and may still
// exist in a checkout, and vite empties its
// output directory before every build, so the two cannot share one. Until
// 2026-10 this repository also tracked a sample bundle under `dist/`, and
// with the default every `npm run build` (and `npm run test:smoke`, which
// runs one) deleted it from the working tree.
//
// Whatever else moves, these two must move together: `outDir` here and
// `upload-pages-artifact`'s `path:` in .github/workflows/deploy.yml. Change
// one alone and the deployment publishes nothing.
const proxy = {
  "/api": {
    target: process.env.CEDAR_PRESS_API_TARGET || "http://localhost:8000",
    rewrite: (path) => path.replace(/^\/api/, ""),
  },
};

export default defineConfig({
  plugins: [react()],
  base: "/",
  build: { outDir: "dist-site" },
  // The CSP allows only same-origin API calls, so /api/* is proxied with the
  // prefix removed, as CloudFront serves it.
  server: { proxy },
  preview: { proxy },
  define: {
    __PRESS_BUILD_SHA__: JSON.stringify(process.env.PRESS_BUILD_SHA || gitSha()),
    __PRESS_BUILD_TIME__: JSON.stringify(new Date().toISOString()),
  },
});
