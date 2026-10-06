/**
 * PURPOSE
 * The client for the Cedar platform API: the one place that knows the
 * service's endpoints, how a request is authenticated and what an error
 * looks like coming back.
 *
 * Every call here is a no-op in a standalone deployment (see config.js):
 * callers ask `isConnected()` first and take the bundled catalog instead, so
 * this module never has to invent data to cover for a missing backend.
 *
 * CONTRACT
 * Cookies carry the session (`credentials: "include"`), because a token in
 * browser storage is a token any script on the page can read. Errors arrive
 * as `{ code, message }` and are rethrown as an Error with `code` attached,
 * which is the shape pressSignup.pressSignupError already reads.
 *
 * Every request has a deadline (`REQUEST_TIMEOUT_MS`, longer for the two
 * calls whose server side waits on another service). A request that misses
 * it rejects with code `TIMEOUT`, and a dropped connection with `NETWORK`;
 * `isUnreachable(error)` is how a page tells either from a refusal, so it
 * can offer a Retry instead of a verdict. Before the deadline, a stalled
 * connection left the session check, an article and the spreadsheet list
 * waiting indefinitely (2026-10-04 audit, Slow 3G).
 */
import { API_URL, isConnected } from "./config.js";

const JSON_HEADERS = { "Content-Type": "application/json" };

class ApiError extends Error {
  constructor(message, code, status, options) {
    super(message, options);
    this.name = "ApiError";
    this.code = code;
    this.status = status;
  }
}

/** How long a request may take, headers and body, before it is abandoned. */
export const REQUEST_TIMEOUT_MS = 15_000;

/**
 * Cedar's own deadline is 45 s (`CEDAR_TIMEOUT_MS` in cedar_service.py) and
 * the data service's 30 s (`CEDAR_PRESS_DATA_TIMEOUT_SECONDS`), so the calls
 * that wait on them wait longer here; a client deadline shorter than the
 * server's would abandon answers that were on their way.
 */
export const CEDAR_TIMEOUT_MS = 60_000;
export const RESEARCH_TIMEOUT_MS = 45_000;

/** Whether an error means the service was not reached in time, not that it refused. */
export function isUnreachable(error) {
  return error?.code === "NETWORK" || error?.code === "TIMEOUT";
}

/** Whether a call can be made at all; callers use this to choose a source. */
export function apiAvailable() {
  return isConnected();
}

async function request(path, { method = "GET", body, signal, headers, timeoutMs = REQUEST_TIMEOUT_MS } = {}) {
  if (!isConnected()) {
    throw new ApiError(
      "This deployment is not connected to the Cedar platform API.",
      "NOT_CONNECTED",
      0,
    );
  }
  // One controller for both reasons to stop: the caller's signal (a page
  // that unmounted) and the deadline. AbortSignal.any would say this in one
  // line, but it is Safari 17.4 and Firefox 124, newer than the build's
  // target (Vite's default, Safari 16.4 and Firefox 114).
  const controller = new AbortController();
  let timedOut = false;
  const timer = setTimeout(() => {
    timedOut = true;
    controller.abort();
  }, timeoutMs);
  const forward = () => controller.abort();
  if (signal?.aborted) controller.abort();
  else signal?.addEventListener("abort", forward, { once: true });
  const stopped = (cause) => (timedOut
    ? new ApiError("The service did not answer in time.", "TIMEOUT", 0, { cause })
    : null);
  let response;
  let payload;
  try {
    try {
      response = await fetch(`${API_URL}${path}`, {
        method,
        credentials: "include",
        signal: controller.signal,
        headers: body instanceof FormData ? headers : { ...JSON_HEADERS, ...headers },
        body: body instanceof FormData ? body : body ? JSON.stringify(body) : undefined,
      });
    } catch (cause) {
      // A dropped connection is not a 500 and must not read as one: the caller
      // decides whether to retry or to tell the reader the service is
      // unreachable.
      throw stopped(cause) ?? new ApiError("The service could not be reached.", "NETWORK", 0, { cause });
    }
    if (response.status === 204) return null;
    // The deadline covers the body too: a response whose headers arrive and
    // whose body stalls is as unanswered as one that never started.
    try {
      payload = await response.json();
    } catch (cause) {
      const late = stopped(cause);
      if (late) throw late;
      payload = null;
    }
  } finally {
    clearTimeout(timer);
    signal?.removeEventListener("abort", forward);
  }
  if (!response.ok) {
    throw new ApiError(
      payload?.message || `Request failed (${response.status}).`,
      payload?.code || "REQUEST_FAILED",
      response.status,
    );
  }
  return payload;
}

/* ── Session ─────────────────────────────────────────────────────────── */

function requireSessionPayload(payload) {
  if (!payload || typeof payload !== "object" || Array.isArray(payload)
      || typeof payload.email !== "string" || !payload.email.trim()
      || typeof payload.workspace_tier !== "string" || !payload.workspace_tier.trim()) {
    throw new ApiError(
      "The sign-in service returned an unexpected response. Please try again or contact Cedar Press.",
      "AUTH_RESPONSE_INVALID",
      502,
    );
  }
  return payload;
}

/** The signed-in subscriber, or null when the session is not valid. */
export async function fetchSession({ signal } = {}) {
  try {
    return requireSessionPayload(await request("/me", { signal }));
  } catch (error) {
    if (error.status === 401) return null;
    throw error;
  }
}

export async function login({ email, password }) {
  return requireSessionPayload(await request("/auth/login", { method: "POST", body: { email, password } }));
}

export async function logout() {
  return request("/auth/logout", { method: "POST" });
}

/* ── Activation ──────────────────────────────────────────────────────── */

export async function validatePressCode({ code, email }) {
  return request("/press/activation/validate", { method: "POST", body: { code, email } });
}

export async function activatePressAccount({ code, email, password }) {
  return requireSessionPayload(await request("/press/activation", { method: "POST", body: { code, email, password } }));
}

/* ── The subscriber ──────────────────────────────────────────────────── */

/** The subscriber's declared organization and role. */
export async function fetchProfile({ signal } = {}) {
  return request("/press/profile", { signal });
}

/** Save what the subscriber declared. Partial: only what they answered. */
export async function saveProfile(profile) {
  return request("/press/profile", { method: "PATCH", body: profile });
}

/* ── The catalog ─────────────────────────────────────────────────────── */

/** Collections the signed-in subscription can see, with their shelf and reach. */
export async function fetchCollections({ signal } = {}) {
  return request("/press/collections", { signal });
}

export function fetchReleaseCollections({ signal } = {}) {
  return request("/press/release-collections", { signal });
}

export function releaseDownloadUrl(collection, releaseId, component = null) {
  if (!/^[a-z][a-z0-9-]{0,63}$/.test(collection || "") || collection === "gaming"
      || !/^[a-f0-9]{64}$/.test(releaseId || "")
      || (component !== null && !/^[a-z0-9][a-z0-9_]{0,59}$/.test(component))) return null;
  const query = new URLSearchParams({ release_id: releaseId });
  if (component) query.set("component", component);
  return `${API_URL}/press/collections/${collection}/full-download?${query}`;
}

export function spreadsheetDownloadUrl(collection, metadata, parts) {
  if (metadata?.kind !== "spreadsheet" || metadata.format !== "csv"
      || !parts.some((part) => part.available && part.releaseId === metadata.release_id)
      || !releaseDownloadUrl(collection, metadata.release_id)) return null;
  return `${API_URL}/press/collections/${collection}/spreadsheet-download?${new URLSearchParams({ release_id: metadata.release_id })}`;
}

export function fetchReleaseResearch(collection, releaseId, component = null, { signal } = {}) {
  if (!releaseDownloadUrl(collection, releaseId, component)) return Promise.reject(new Error("Invalid release"));
  const query = new URLSearchParams({ release_id: releaseId });
  if (component) query.set("component", component);
  return request(`/press/collections/${collection}/research?${query}`, { signal, timeoutMs: RESEARCH_TIMEOUT_MS });
}

/** Release history: what changed in each collection, newest first. */
export async function fetchReleases({ signal } = {}) {
  return request("/press/releases", { signal });
}

/** Published briefs. */
export async function fetchArticles({ signal } = {}) {
  return request("/press/articles", { signal });
}

export async function fetchArticle(slug, { signal } = {}) {
  return request("/press/articles/" + encodeURIComponent(slug), { signal });
}

/**
 * A collection's release file. Returns a Blob rather than parsed rows: the
 * file is what the subscriber is taking, and re-serializing it here would
 * make the download something this client composed rather than what the
 * platform published.
 */
export async function downloadCollection(id) {
  if (!isConnected()) {
    throw new ApiError("Not connected.", "NOT_CONNECTED", 0);
  }
  const response = await fetch(`${API_URL}/press/collections/${encodeURIComponent(id)}/download`, {
    credentials: "include",
  });
  if (!response.ok) {
    // The service says why (`NOT_INCLUDED`, `NO_SAMPLE`), and the reader is
    // told that rather than a status code.
    const payload = await response.json().catch(() => null);
    throw new ApiError(
      payload?.message || `Download failed (${response.status}).`,
      payload?.code || "DOWNLOAD_FAILED",
      response.status,
    );
  }
  return {
    blob: await response.blob(),
    filename:
      response.headers
        .get("content-disposition")
        ?.match(/filename="?([^";]+)"?/i)?.[1] || `${id}.csv`,
  };
}

/* ── Cedar ───────────────────────────────────────────────────────────── */

/**
 * One turn of a conversation with Cedar.
 *
 * `surface` tells the platform which product the question came from, so an
 * answer can cite what this reader can actually open rather than the whole
 * warehouse.
 *
 * `threadId` is Cedar's own conversation id, and it is what separates a
 * conversation from a row of unrelated questions: absent on the first turn,
 * returned by the service, and sent back on every turn after. The panel owns
 * it for as long as it is open. `pathname` says where in the product the
 * question was asked.
 *
 * Returns `{ answer, basis, source, threadId }`. `source` is "profile" when
 * the collection's own release answered — then `basis` names that release —
 * or "cedar" when the service did.
 */
export async function askCedar({ question, collectionId, threadId, pathname, signal } = {}) {
  return request("/cedar/ask", {
    method: "POST",
    body: { question, surface: "cedar-press", collectionId, threadId, pathname },
    signal,
    timeoutMs: CEDAR_TIMEOUT_MS,
  });
}

// ── Shape the Research ──────────────────────────────────────────────────

/** Every priority with its points and subscriber count, most supported first. */
export async function fetchPriorities({ signal } = {}) {
  return request("/press/priorities", { signal });
}

/** What this subscription has and has done; the service credits the month first, once. */
export async function fetchInfluence({ signal } = {}) {
  return request("/press/influence", { signal });
}

/** Put points on a priority (positive) or take them back (negative). */
export async function movePoints({ priorityId, points, signal }) {
  return request(`/press/priorities/${encodeURIComponent(priorityId)}/points`, {
    method: "POST",
    body: { points },
    signal,
  });
}

/** The priorities a request reads as being about, as the service reads it. */
export async function fetchRelatedPriorities({ text, signal } = {}) {
  return request(`/press/priorities/related?q=${encodeURIComponent(text ?? "")}`, { signal });
}

/** A subscriber's own words, beside the priority they are about, with a point on it if asked. */
export async function submitResearchRequest({ text, useCase, priorityId, supportPoints = 0, signal }) {
  return request("/press/requests", {
    method: "POST",
    body: { text, use_case: useCase || null, priority_id: priorityId || null, support_points: supportPoints },
    signal,
  });
}

export { ApiError };

export function getNeedEntityEvidence(cedarUid, { signal } = {}) {
  return request(`/press/entities/${encodeURIComponent(cedarUid)}/need-evidence`, { signal });
}
