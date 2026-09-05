// Render the public pages to static HTML after the build, so a crawler (or a
// reader on a connection that has not finished fetching the bundle) meets the
// page's text in the document rather than an empty root.
//
//     npm run build && node scripts/prerender.mjs
//
// Only the three pages a visitor reaches without a subscription: the door,
// the tribal data request policy and research access. Everything behind the
// gate is left as the app shell, which is what a crawler should get there.
// React mounts over the rendered markup and replaces it with the same tree.
//
// Needs the Chromium Playwright installs; run after `npx playwright install
// chromium`. Skips, saying so, when no browser is available, so a build on a
// machine without one still succeeds — the deployment runs it in CI, where
// the smoke tests have already installed the browser.
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { spawn } from "node:child_process";
import { fileURLToPath } from "node:url";

const ROOT = fileURLToPath(new URL("..", import.meta.url));
const OUT = `${ROOT}dist-site`;
const PORT = Number(process.env.CEDAR_PRESS_PRERENDER_PORT) || 41999;
const PAGES = ["/", "/tribal-data-request", "/research-access"];

async function waitFor(url, tries = 60) {
  for (let i = 0; i < tries; i += 1) {
    try {
      const r = await fetch(url);
      if (r.ok) return;
    } catch { /* not up yet */ }
    await new Promise((resolve) => setTimeout(resolve, 250));
  }
  throw new Error(`prerender: ${url} never answered`);
}

async function main() {
  let chromium;
  try {
    ({ chromium } = await import("@playwright/test"));
  } catch {
    console.log("prerender: @playwright/test not installed; leaving the app shell as built");
    return;
  }
  const server = spawn("npx", ["vite", "preview", "--port", String(PORT), "--strictPort"], { cwd: ROOT, stdio: "ignore" });
  try {
    await waitFor(`http://localhost:${PORT}/`);
    let browser;
    try {
      browser = await chromium.launch();
    } catch (error) {
      console.log(`prerender: no browser available (${String(error).split("\n")[0]}); leaving the app shell as built`);
      return;
    }
    const context = await browser.newContext({ reducedMotion: "reduce", viewport: { width: 1280, height: 900 } });
    const page = await context.newPage();
    const shell = readFileSync(`${OUT}/index.html`, "utf8");
    for (const path of PAGES) {
      await page.goto(`http://localhost:${PORT}${path}`, { waitUntil: "networkidle" });
      await page.locator("#root h1").first().waitFor({ timeout: 15_000 });
      const { rendered, title, description, canonical } = await page.evaluate(() => ({
        rendered: document.getElementById("root").innerHTML,
        title: document.title,
        description: document.querySelector('meta[name="description"]')?.getAttribute("content") ?? "",
        canonical: document.querySelector('link[rel="canonical"]')?.getAttribute("href") ?? "",
      }));
      if (!rendered || !title) throw new Error(`prerender: ${path} rendered nothing`);
      // The head is the shell's (its asset links, policy and structured data
      // are what the build wrote); the root's markup and the page's title,
      // description, canonical address and index permission come from the
      // render. A prerendered page is by definition one a crawler may index.
      const attr = (text) => text.replace(/&/g, "&amp;").replace(/"/g, "&quot;").replace(/</g, "&lt;");
      let out = shell.replace('<div id="root"></div>', `<div id="root">${rendered}</div>`);
      out = out.replace(/<title>[^<]*<\/title>/, `<title>${attr(title)}</title>`);
      if (description) out = out.replace(/(<meta\s+name="description"\s+content=")[^"]*(")/, `$1${attr(description)}$2`);
      if (canonical) out = out.replace(/(<link rel="canonical" href=")[^"]*(")/, `$1${attr(canonical)}$2`);
      out = out.replace("</head>", '  <meta name="robots" content="index, follow">\n  </head>');
      // Written twice for a satellite page: `path.html`, which GitHub Pages
      // and the preview server both serve at the extensionless address the
      // sitemap and the canonical name, and `path/index.html` for the
      // trailing-slash form.
      const files = path === "/" ? [`${OUT}/index.html`] : [`${OUT}${path}.html`, `${OUT}${path}/index.html`];
      if (path !== "/") mkdirSync(`${OUT}${path}`, { recursive: true });
      for (const file of files) writeFileSync(file, out);
      console.log(`prerender: ${path} -> ${files.map((f) => f.replace(ROOT, "")).join(", ")} (${rendered.length} bytes of markup)`);
    }
    await browser.close();
  } finally {
    server.kill();
  }
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
