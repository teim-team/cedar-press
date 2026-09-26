// Regenerates server/cedar_press/_press_data.json from the JavaScript
// modules, so the Python service serves the same articles, citations and
// catalog the client renders. Run from the repo root after editing
// pressArticles.js, pressCitations.js, pressCatalog.js, pressReleases.js or
// readerWork.js:
//
//     node scripts/dump-press.mjs > server/cedar_press/_press_data.json
//
// `--check` compares instead of printing and exits 1 when the committed file
// is stale, so `make check-generated` catches a catalog edit that was never
// dumped (it used to surface only later, in `make test-python`).
import { readFileSync } from "node:fs";
import { PRESS_ARTICLES, TBN_URL, LUMECON_URL } from "../src/features/grove/pressArticles.js";
import { CITATIONS, REPORT_CITATION_HREF } from "../src/features/grove/pressCitations.js";
import { PRESS_CATALOG } from "../src/features/grove/pressCatalog.js";
import { PRESS_RELEASES } from "../src/features/grove/pressReleases.js";
import { WORK_KINDS } from "../src/features/grove/readerWork.js";

const TARGET = new URL("../server/cedar_press/_press_data.json", import.meta.url);
const text =
  JSON.stringify(
    {
      tbnUrl: TBN_URL,
      lumeconUrl: LUMECON_URL,
      articles: PRESS_ARTICLES,
      citations: CITATIONS,
      reportCitationHref: REPORT_CITATION_HREF,
      catalog: PRESS_CATALOG,
      releases: PRESS_RELEASES,
      // The vocabulary /press/profile accepts, so the service and the
      // Settings page cannot disagree about what a reader may say they do.
      workKinds: WORK_KINDS,
    },
    null,
    2,
  ) + "\n";

if (process.argv.includes("--check")) {
  let committed = "";
  try {
    committed = readFileSync(TARGET, "utf8");
  } catch {
    // A missing file is stale too.
  }
  if (committed !== text) {
    console.error(
      "server/cedar_press/_press_data.json is stale. Run `node scripts/dump-press.mjs > server/cedar_press/_press_data.json` and commit the result.",
    );
    process.exit(1);
  }
  console.log("  press data  server/cedar_press/_press_data.json current");
} else {
  process.stdout.write(text);
}
