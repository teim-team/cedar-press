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
// The mark itself, byte-identical to the all-teal one lumecon.ai ships.
// Drawing an approximation of it was the earlier mistake: the rings are
// asymmetric and an even set of circles does not read as this logo.
const mark = readFileSync(
  fileURLToPath(new URL("public/brand/lumecon-logo-mark-teal.png", root)),
);

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
  /* The real mark, off the top-right corner. Rendered white rather than in
     its own teal, which would vanish against a teal field — the same choice
     lumecon.ai's card makes, and the reason its rings are white there too.
     brightness(0) invert(1) repaints every opaque pixel white and leaves the
     alpha channel alone, so the geometry is the logo's own. */
  .mark {
    position: absolute; top: -392px; right: -404px;
    width: 880px; height: 880px;
    filter: brightness(0) invert(1);
    opacity: 0.17;
  }
  .word {
    position: absolute; left: 158px; top: 50%; transform: translateY(-50%);
    font-family: Inter, sans-serif; font-weight: 800; font-size: 116px;
    letter-spacing: 0.055em; color: #fff; white-space: nowrap;
    text-shadow: 0 6px 28px rgba(4, 60, 54, 0.22);
  }
</style>
<div class="card">
  <img class="mark" src="data:image/png;base64,${mark.toString("base64")}" alt="">
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
