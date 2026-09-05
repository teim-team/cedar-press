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
 */
import { API_URL, isConnected } from "./config.js";

const JSON_HEADERS = { "Content-Type": "application/json" };

class ApiError extends Error {
  constructor(message, code, status) {
    super(message);
    this.name = "ApiError";
    this.code = code;
    this.status = status;
  }
}

/** Whether a call can be made at all; callers use this to choose a source. */
export function apiAvailable() {
  return isConnected();
}

async function request(path, { method = "GET", body, signal, headers } = {}) {
  if (!isConnected()) {
    throw new ApiError(
      "This deployment is not connected to the Cedar platform API.",
      "NOT_CONNECTED",
      0,
    );
  }
  let response;
  try {
    response = await fetch(`${API_URL}${path}`, {
      method,
      credentials: "include",
      signal,
      headers: body instanceof FormData ? headers : { ...JSON_HEADERS, ...headers },
      body: body instanceof FormData ? body : body ? JSON.stringify(body) : undefined,
    });
  } catch (cause) {
    // A dropped connection is not a 500 and must not read as one: the caller
    // decides whether to retry or to tell the reader the service is
    // unreachable.
    throw new ApiError("The service could not be reached.", "NETWORK", 0, { cause });
  }
  if (response.status === 204) return null;
  const payload = await response.json().catch(() => null);
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

/** The signed-in subscriber, or null when the session is not valid. */
export async function fetchSession({ signal } = {}) {
  try {
    return await request("/me", { signal });
  } catch (error) {
    if (error.status === 401) return null;
    throw error;
  }
}

export async function login({ email, password }) {
  return request("/auth/login", { method: "POST", body: { email, password } });
}

export async function logout() {
  return request("/auth/logout", { method: "POST" });
}

/* ── Activation ──────────────────────────────────────────────────────── */

export async function validatePressCode({ code, email }) {
  return request("/press/activation/validate", { method: "POST", body: { code, email } });
}

export async function activatePressAccount({ code, email, password }) {
  return request("/press/activation", { method: "POST", body: { code, email, password } });
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

/** Release history: what changed in each collection, newest first. */
export async function fetchReleases({ signal } = {}) {
  return request("/press/releases", { signal });
}

/** Published briefs. */
export async function fetchArticles({ signal } = {}) {
  return request("/press/articles", { signal });
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
    throw new ApiError(`Download failed (${response.status}).`, "DOWNLOAD_FAILED", response.status);
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
 * Ask Cedar a question about the collections. `surface` tells the platform
 * which product the question came from, so an answer can cite what this
 * reader can actually open rather than the whole warehouse.
 */
export async function askCedar({ question, collectionId, signal } = {}) {
  return request("/cedar/ask", {
    method: "POST",
    body: { question, surface: "cedar-press", collectionId },
    signal,
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
export async function movePoints({ priorityId, points }) {
  return request(`/press/priorities/${encodeURIComponent(priorityId)}/points`, {
    method: "POST",
    body: { points },
  });
}

/** The priorities a request reads as being about, as the service reads it. */
export async function fetchRelatedPriorities({ text, signal } = {}) {
  return request(`/press/priorities/related?q=${encodeURIComponent(text ?? "")}`, { signal });
}

/** A subscriber's own words, beside the priority they are about, with a point on it if asked. */
export async function submitResearchRequest({ text, useCase, priorityId, supportPoints = 0 }) {
  return request("/press/requests", {
    method: "POST",
    body: { text, use_case: useCase || null, priority_id: priorityId || null, support_points: supportPoints },
  });
}

export { ApiError };
