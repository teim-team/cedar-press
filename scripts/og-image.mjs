// The link-preview card, generated rather than hand-exported.
//
// This is what a subscriber sends a colleague, so it is the first thing many
// people ever see of Cedar Press. It matches lumecon.ai's card deliberately —
// same gradient, same contour motif, same weight of wordmark — because the two
// are one company and a link preview is where that reads fastest.
//
// The card carries the wordmark and nothing else. The line underneath it in a
// message thread is `og:title`, not part of the image: baking a tagline into
// a PNG means re-exporting a binary to change a sentence.
//
//   node scripts/og-image.mjs
//
// Writes public/cedar-press-og-1200x630.png at 1200x630.
import { chromium } from "@playwright/test";
import { fileURLToPath } from "node:url";
import { readFileSync, writeFileSync } from "node:fs";

const root = new URL("..", import.meta.url);
const out = fileURLToPath(new URL("public/cedar-press-og-1200x630.png", root));
const font = readFileSync(fileURLToPath(new URL("public/fonts/inter-800.woff2", root)));

// Sampled from lumecon.ai's own card rather than guessed, so the two sit
// beside each other in a thread without one looking like a copy of the other.
const FROM = "#17b6a7";
const TO = "#0c8a7d";

const html = `<!doctype html><meta charset="utf-8"><style>
  @font-face {
    font-family: Inter; font-weight: 800; font-display: block;
    src: url(data:font/woff2;base64,${font.toString("base64")}) format("woff2");
  }
  html, body { margin: 0; padding: 0; }
  .card {
    position: relative; width: 1200px; height: 630px; overflow: hidden;
    background: linear-gradient(135deg, ${FROM} 0%, ${TO} 100%);
  }
  /* Topographic rings off the top-right corner, the same motif the site draws
     behind its teal bands. Stroke only and barely there: it is depth behind a
     flat field of colour, not a picture of anything. */
  .rings { position: absolute; inset: 0; }
  .rings path { fill: none; stroke: #fff; stroke-opacity: 0.17; stroke-width: 7; }
  .word {
    position: absolute; left: 158px; top: 50%; transform: translateY(-50%);
    font-family: Inter, sans-serif; font-weight: 800; font-size: 116px;
    letter-spacing: 0.055em; color: #fff; white-space: nowrap;
    text-shadow: 0 6px 28px rgba(4, 60, 54, 0.22);
  }
</style>
<div class="card">
  <svg class="rings" viewBox="0 0 1200 630" preserveAspectRatio="none">
    <path d="M1247 -40 C 1120 20, 1006 96, 964 210 C 922 324, 986 404, 1104 430 C 1198 451, 1268 430, 1310 384"/>
    <path d="M1305 -96 C 1130 -30, 960 78, 902 226 C 844 374, 936 484, 1096 512 C 1216 533, 1312 502, 1366 448"/>
    <path d="M1360 -150 C 1140 -78, 918 60, 842 244 C 766 428, 884 566, 1088 596 C 1236 618, 1358 578, 1424 512"/>
    <path d="M1196 12 C 1104 62, 1030 128, 1004 214 C 978 300, 1030 358, 1122 374"/>
  </svg>
  <div class="word">CEDAR PRESS</div>
</div>`;

const file = fileURLToPath(new URL("scratch-og.html", root));
writeFileSync(file, html);
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1200, height: 630 }, deviceScaleFactor: 1 });
await page.goto(`file://${file}`);
await page.evaluate(() => document.fonts.ready);
await page.locator(".card").screenshot({ path: out });
await browser.close();
console.log(`wrote ${out}`);
