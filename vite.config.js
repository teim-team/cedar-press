import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

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
});
