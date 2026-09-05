// Regenerates server/cedar_press/_press_data.json from the JavaScript
// modules, so the Python service serves the same articles, citations and
// catalog the client renders. Run from the repo root after editing
// pressArticles.js, pressCitations.js, pressCatalog.js, pressReleases.js or
// readerWork.js:
//
//     node scripts/dump-press.mjs > server/cedar_press/_press_data.json
import { PRESS_ARTICLES, TBN_URL, LUMECON_URL } from "../src/features/grove/pressArticles.js";
import { CITATIONS, REPORT_CITATION_HREF } from "../src/features/grove/pressCitations.js";
import { PRESS_CATALOG } from "../src/features/grove/pressCatalog.js";
import { PRESS_RELEASES } from "../src/features/grove/pressReleases.js";
import { WORK_KINDS } from "../src/features/grove/readerWork.js";

process.stdout.write(
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
  ) + "\n",
);
