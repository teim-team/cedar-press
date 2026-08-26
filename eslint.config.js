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
  globalIgnores(["dist"]),
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
