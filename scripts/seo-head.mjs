// The structured data and the sitemap, generated from the catalog so a search
// engine reads the twelve collections as what they are: datasets, each with
// its name, its description, what it covers and who built it.
//
//     node scripts/seo-head.mjs            rewrite index.html's JSON-LD block and public/sitemap.xml
//     node scripts/seo-head.mjs --check    exit 1 if either is stale (the tests run this)
//
// Only the public surface is described. The collections are named and
// described because their names are what someone searching for data on a
// tribe, a Native enterprise or Indian Country's economy types; the records
// themselves stay behind the subscription, and `isAccessibleForFree: false`
// says so rather than inviting a crawler to look for a file.
import { readFileSync, writeFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

import { PRESS_CATALOG, STOREFRONT_SHELVES } from "../src/features/grove/pressCatalog.js";
import { PRESS_RELEASES } from "../src/features/grove/pressReleases.js";
import { coverageLabel } from "../src/features/grove/pressAccess.js";

const ROOT = fileURLToPath(new URL("..", import.meta.url));
const INDEX = `${ROOT}index.html`;
const SITEMAP = `${ROOT}public/sitemap.xml`;
const SITE = "https://cedarpress.ai";
const ORG = "https://lumecon.ai/#organization";

// The words a search for this material actually uses, beside each
// collection's own name. Plain vocabulary, not a keyword list: every term
// here names something the collection genuinely holds.
const KEYWORDS = [
  "Indian Country data", "tribal data", "tribal government", "tribal economy",
  "Native American economic data", "Alaska Native Corporations", "Native Hawaiian Organizations",
  "tribal enterprises", "Native-owned businesses", "federal funding to tribes",
  "federal contracting tribal", "NAGPRA notices", "tribal consultation", "Federal Register tribes",
  "tribal legislation", "tribal lobbying", "Indian Country deals", "tribal natural resources revenue",
  "Native nonprofits", "Cedar Press", "Lumecon", "Tribal Business News",
];

function latestReleaseDate() {
  const dates = Object.values(PRESS_RELEASES).map((r) => r.updated).filter(Boolean).sort();
  return dates.at(-1)?.slice(0, 10) ?? null;
}

export function datasets() {
  return PRESS_CATALOG.filter((entry) => STOREFRONT_SHELVES.includes(entry.shelf)).map((entry) => ({
    "@type": "Dataset",
    "@id": `${SITE}/#dataset-${entry.id}`,
    name: entry.name,
    alternateName: entry.short !== entry.name ? entry.short : undefined,
    description: `${entry.blurb} ${entry.linkage ?? ""}`.trim(),
    url: `${SITE}/`,
    creator: { "@id": ORG },
    publisher: { "@id": ORG },
    includedInDataCatalog: { "@id": `${SITE}/#catalog` },
    temporalCoverage: coverageLabel(entry),
    spatialCoverage: "United States",
    keywords: [entry.name, entry.short, ...KEYWORDS.slice(0, 6)].filter((k, i, a) => k && a.indexOf(k) === i),
    isAccessibleForFree: false,
    license: "https://cedarpress.ai/methods",
    inLanguage: "en",
  }));
}

export function graph() {
  return {
    "@context": "https://schema.org",
    "@graph": [
      {
        "@type": "WebSite",
        "@id": `${SITE}/#website`,
        url: `${SITE}/`,
        name: "Cedar Press",
        description:
          "Trusted intelligence for Indian Country: original economic collections, data-driven research and transparent method.",
        inLanguage: "en",
        keywords: KEYWORDS,
        publisher: { "@id": ORG },
      },
      {
        "@type": "Organization",
        "@id": ORG,
        name: "Lumecon",
        url: "https://lumecon.ai",
        email: "contact@lumecon.ai",
      },
      {
        "@type": "Product",
        name: "Cedar Press",
        url: `${SITE}/`,
        brand: { "@id": ORG },
        description:
          "A subscriber intelligence service covering the money, policy, transactions, institutions and public actions that shape Indian Country's economy. Every collection begins with public records and carries its own citation.",
        category: "Economic data and research",
      },
      {
        "@type": "DataCatalog",
        "@id": `${SITE}/#catalog`,
        name: "The Cedar Press collections",
        url: `${SITE}/`,
        description:
          "Twelve collections on Indian Country's economy: federal funding, the Federal Register, legislation, deals, NAGPRA, advocacy, prime contracting, subcontracting, natural resources, Native-owned businesses, Native nonprofits and the enterprise register, each resolved to the tribal governments and Native entities behind the records.",
        provider: { "@id": ORG },
        dataset: datasets().map((d) => ({ "@id": d["@id"] })),
      },
      ...datasets(),
    ],
  };
}

export function sitemap() {
  const lastmod = latestReleaseDate();
  const url = (path, changefreq, priority) =>
    `  <url>\n    <loc>${SITE}${path}</loc>\n${lastmod ? `    <lastmod>${lastmod}</lastmod>\n` : ""}    <changefreq>${changefreq}</changefreq>\n    <priority>${priority}</priority>\n  </url>`;
  return `<?xml version="1.0" encoding="UTF-8"?>
<!--
  Only the pages a reader can reach without a subscription. The subscriber
  sections are deliberately absent: listing a URL that answers with a sign-in
  asks a search engine to rank a login wall. Generated by scripts/seo-head.mjs;
  lastmod is the newest release in the ledger.
-->
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
${url("/", "weekly", "1.0")}
${url("/tribal-data-request", "monthly", "0.6")}
${url("/research-access", "monthly", "0.6")}
</urlset>
`;
}

const BLOCK = /(<script type="application\/ld\+json">\n)([\s\S]*?)(\n\s*<\/script>)/;

export function renderIndex(html) {
  const json = JSON.stringify(graph(), null, 2).replace(/^/gm, "      ");
  if (!BLOCK.test(html)) throw new Error("index.html has no JSON-LD block to fill");
  return html.replace(BLOCK, (_, open, __, close) => `${open}${json}${close}`);
}

function main(argv) {
  const check = argv.includes("--check");
  const html = readFileSync(INDEX, "utf8");
  const nextHtml = renderIndex(html);
  const nextMap = sitemap();
  let stale = 0;
  if (nextHtml !== html) {
    stale += 1;
    if (!check) writeFileSync(INDEX, nextHtml);
  }
  let currentMap = "";
  try { currentMap = readFileSync(SITEMAP, "utf8"); } catch { /* absent */ }
  if (nextMap !== currentMap) {
    stale += 1;
    if (!check) writeFileSync(SITEMAP, nextMap);
  }
  if (check && stale) {
    console.error(`seo-head: ${stale} file(s) stale; run node scripts/seo-head.mjs`);
    process.exit(1);
  }
  console.log(check ? "seo-head: current" : `seo-head: wrote ${stale} file(s), ${datasets().length} datasets`);
}

if (process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1]) main(process.argv.slice(2));
