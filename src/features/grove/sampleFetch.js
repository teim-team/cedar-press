/**
 * PURPOSE
 * Reading a published sample file, with a deadline, and noticing when the
 * connection comes back.
 *
 * WHY THIS EXISTS
 * The sample hooks (useSamples.js, the door's preview) fetched with no
 * deadline and kept a failure for the life of the page. On a connection that
 * stalls, a fetch can stay pending for minutes, so the preview said "Reading
 * the sample…" indefinitely; one that failed once stayed failed until a
 * reload, and the viewer reported the empty result as "No matching records
 * in this preview. Widen a filter", which is a different and wrong claim.
 * Found by the 2026-10-04 throttled audit (Chromium, Slow 3G, 4x CPU).
 *
 * CONTRACT
 * `fetchSampleText` resolves to the file's text or throws; it never resolves
 * to a failure value, so a caller cannot store a failure by accident. The
 * deadline covers the body as well as the headers. The hooks keep only what
 * succeeded; a failure is shown with a Retry and is cleared when the browser
 * reports it is back online (`onBackOnline`).
 */

import { textMatchesDigest } from "./customerTables.js";

/** A sample is ten rows: fifteen seconds is a stalled connection, not a slow file. */
export const SAMPLE_TIMEOUT_MS = 15_000;

/**
 * The sample's text, or a thrown error naming why it could not be read.
 *
 * `sha256` is required: every sample a reader sees is a rendered customer
 * table with its digest in `data/cedar/sample_downloads.json`
 * (customerTables.js), and bytes that do not match it are refused. A stale
 * cached copy, or any other file served at that path, never reaches a table.
 */
export async function fetchSampleText(path, { sha256, timeoutMs = SAMPLE_TIMEOUT_MS, fetchImpl = globalThis.fetch } = {}) {
  if (!/^[a-f0-9]{64}$/.test(sha256 ?? "")) {
    throw new Error(`No published digest for ${path}; only a rendered customer table is read.`);
  }
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetchImpl(path, { signal: controller.signal });
    if (!response.ok) throw new Error(`The sample answered ${response.status}.`);
    const text = await response.text();
    if (!(await textMatchesDigest(text, sha256))) {
      throw new Error("The sample is not the published customer table (digest mismatch).");
    }
    return text;
  } catch (error) {
    if (controller.signal.aborted) {
      throw new Error(`The sample did not arrive within ${timeoutMs / 1000} seconds.`, { cause: error });
    }
    throw error;
  } finally {
    clearTimeout(timer);
  }
}

/**
 * Call `callback` each time the browser reports the connection is back.
 * Returns the unsubscribe. A no-op where there is no `window` (Node).
 */
export function onBackOnline(callback, target = globalThis.window) {
  if (!target?.addEventListener) return () => {};
  target.addEventListener("online", callback);
  return () => target.removeEventListener("online", callback);
}
