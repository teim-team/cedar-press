// Regenerates server/cedar_press/_press_data.json from the JavaScript
// modules, so the Python service serves the same articles and citations the
// client renders. Run from the repo root after editing pressArticles.js or
// pressCitations.js:
//
//     node scripts/dump-press.mjs > server/cedar_press/_press_data.json
import { PRESS_ARTICLES, TBN_URL, LUMECON_URL } from "../src/features/grove/pressArticles.js";
import { CITATIONS, REPORT_CITATION_HREF } from "../src/features/grove/pressCitations.js";

process.stdout.write(
  JSON.stringify(
    {
      tbnUrl: TBN_URL,
      lumeconUrl: LUMECON_URL,
      articles: PRESS_ARTICLES,
      citations: CITATIONS,
      reportCitationHref: REPORT_CITATION_HREF,
    },
    null,
    2,
  ) + "\n",
);
