/**
 * PURPOSE
 * What this deployment is connected to.
 *
 * Cedar Press runs in two modes and must be honest about which one it is in:
 *
 * - CONNECTED. `VITE_API_URL` names the Cedar platform API. Sessions, the
 *   catalog, releases, downloads, uploaded datasets and Cedar's answers all
 *   come from it, and the database behind it is the source of truth.
 * - STANDALONE. No API is configured. The client serves the bundled catalog
 *   so the service can be demonstrated, reviewed and deployed on its own,
 *   and anything that would write to the database stays in the browser and
 *   says so.
 *
 * Every module that reaches for data asks `isConnected()` rather than
 *guessing from a failed request, so a network error never silently reads as
 * "this deployment is standalone" and quietly shows fixtures in production.
 *
 * TWO SENSES OF "STANDALONE", AND THEY ARE NOT THE SAME
 * The word above means "no API configured". The product sense — Cedar Press
 * is a standalone product, not a surface of Cedar Grove — is a different
 * claim, and it holds in both modes: nothing in this client imports a Grove
 * module or calls a Grove endpoint, and `VITE_API_URL` can name Cedar Press's
 * own FastAPI service in `server/`, which implements the contract in
 * `api.js`. Keep the two apart when reading this file.
 *
 * ONE ROUTE THAT IS NOT YET BOTH
 * `server/` serves every endpoint `api.js` calls except `/press/profile`
 * (GET and PATCH, the reader's declared work — see `readerWork.js`). That
 * route exists only on the Lumecon platform backend, so a CONNECTED
 * deployment pointed at Cedar Press's own API 404s on it: the read is
 * swallowed by `CedarPressSettings.jsx` and reads as "not answered", and the
 * write rejects with nothing shown. It is the one place the client still
 * assumes the platform, and it is named here rather than left to be found.
 */

const raw = import.meta.env?.VITE_API_URL ?? "";

/** The platform API's origin, without a trailing slash. Empty when standalone. */
export const API_URL = String(raw).trim().replace(/\/+$/, "");

/** Whether this deployment talks to the platform API. */
export function isConnected() {
  return API_URL !== "";
}

/** The Lumecon platform's origin, for links out of the service. */
export const APP_URL = String(
  import.meta.env?.VITE_APP_URL ?? "https://lumecon.ai",
).replace(/\/+$/, "");

/**
 * Datadog RUM, configured per environment. Telemetry stays off entirely
 * unless an application id and client token are both present, so a preview
 * build reports nothing.
 */
export const DATADOG = Object.freeze({
  applicationId: import.meta.env?.VITE_DATADOG_APPLICATION_ID ?? "",
  clientToken: import.meta.env?.VITE_DATADOG_CLIENT_TOKEN ?? "",
  site: import.meta.env?.VITE_DATADOG_SITE ?? "datadoghq.com",
  service: import.meta.env?.VITE_DATADOG_SERVICE ?? "cedar-press",
  env: import.meta.env?.VITE_DATADOG_ENV ?? (import.meta.env?.DEV ? "development" : "production"),
  version: import.meta.env?.VITE_APP_VERSION ?? "",
  sampleRate: Number(import.meta.env?.VITE_DATADOG_SAMPLE_RATE ?? 100),
  sessionReplaySampleRate: Number(
    import.meta.env?.VITE_DATADOG_REPLAY_SAMPLE_RATE ?? 0,
  ),
});

export function datadogConfigured() {
  return Boolean(DATADOG.applicationId && DATADOG.clientToken);
}
