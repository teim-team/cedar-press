/**
 * Which build is this, in a form a person can read off a phone.
 *
 * The question this answers is not academic. cedarpress.ai is served from S3
 * behind CloudFront, so a page that looks unchanged has three possible causes
 * — the browser cached it, CloudFront cached it, or the publish never ran —
 * and for a month it was the third, with nothing on the page to say so. The
 * owner could not distinguish "my change did not deploy" from "my change
 * deployed and looks the same", and neither could anyone helping.
 *
 * `vite.config.js` defines both constants at build time. They are compile-time
 * replacements, not globals, so they are referenced through `typeof` guards:
 * the test runner and any tool that imports this module without vite's
 * `define` would otherwise throw a ReferenceError rather than fall back.
 */

/** The commit the bundle was built from, or "unknown" outside a vite build. */
export function buildSha() {
  return typeof __PRESS_BUILD_SHA__ === "string" ? __PRESS_BUILD_SHA__ : "unknown";
}

/** ISO instant of the build, or "" outside a vite build. */
export function buildTime() {
  return typeof __PRESS_BUILD_TIME__ === "string" ? __PRESS_BUILD_TIME__ : "";
}

/**
 * One line, e.g. `bea4961 · 21 Sept 2026, 04:12 UTC`.
 *
 * UTC deliberately: the reader is comparing this against a GitHub Actions run
 * or a commit timestamp, both of which are quoted in UTC. Rendering it in the
 * phone's zone would force a conversion at exactly the moment someone is
 * trying to answer a yes/no question.
 */
export function buildLine() {
  const sha = buildSha();
  const iso = buildTime();
  if (!iso) return sha;
  const at = new Date(iso);
  if (Number.isNaN(at.getTime())) return sha;
  const stamp = at.toLocaleString("en-GB", {
    day: "numeric",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    timeZone: "UTC",
    hour12: false,
  });
  return `${sha} · ${stamp} UTC`;
}
