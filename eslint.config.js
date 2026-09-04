import js from "@eslint/js";
import globals from "globals";
import reactHooks from "eslint-plugin-react-hooks";
import reactRefresh from "eslint-plugin-react-refresh";
import { defineConfig, globalIgnores } from "eslint/config";

// Matches the platform's config, so a module that moves between the two
// repositories is held to one standard. no-undef is the rule that matters
// most here: a client that ships a reference to a name that does not exist
// fails at the reader, not at the build.
export default defineConfig([
  // `dist-site` is the web build's output (vite.config.js); `dist` is the
  // data workspace's tracked deliverables. Neither is source.
  //
  // `data` and `.claude` are ignored for the same reason and were added
  // 2026-09-03, after `npm run lint` was measured locally at 2,737 errors and
  // CI at zero. Every one of those errors came from a file git does not
  // track: 13 under `data/` are third-party JavaScript HARVESTED from source
  // websites (a tribal registry's jQuery probe, a state gaming commission's
  // map bundle), and 523 are stale agent worktrees under `.claude/`. CI
  // checks out tracked files only, so it never saw them.
  //
  // A gate that is green in CI and red on every developer's machine is a gate
  // people stop running, and the divergence hid the real question: no tracked
  // JavaScript outside `src/`, `tests/` and `scripts/` exists, so nothing that
  // ships is being un-linted by this line.
  globalIgnores(["dist", "dist-site", "data", ".claude"]),
  {
    files: ["**/*.{js,jsx}"],
    extends: [
      js.configs.recommended,
      reactHooks.configs.flat.recommended,
      reactRefresh.configs.vite,
    ],
    languageOptions: {
      ecmaVersion: 2020,
      globals: globals.browser,
      parserOptions: {
        ecmaVersion: "latest",
        ecmaFeatures: { jsx: true },
        sourceType: "module",
      },
    },
    rules: {
      "no-unused-vars": ["error", { varsIgnorePattern: "^[A-Z_]" }],
    },
  },
  {
    // The feature tests run on node, not in a browser.
    files: ["**/*.test.js"],
    languageOptions: { globals: globals.node },
  },
  {
    // Playwright's config and the smoke suite are node too. The spec's
    // page.evaluate callbacks run in the browser, so both sets of globals
    // are in scope in the same file and both have to be declared.
    files: ["playwright.config.js", "tests/**/*.spec.js"],
    languageOptions: { globals: { ...globals.node, ...globals.browser } },
  },
]);
