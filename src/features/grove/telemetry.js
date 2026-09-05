/**
 * PURPOSE
 * What the service reports about itself: errors and performance to Datadog
 * RUM, and the handful of interactions that say whether the product works.
 *
 * WHAT IS TRACKED, AND WHY THESE
 * A subscriber intelligence service has a small number of moments that
 * matter: whether people get in, whether they find a collection, whether
 * they take the data, whether they read a brief, and whether they hit the
 * upgrade boundary. Those are the events here. There is deliberately no
 * page-wide click or scroll capture — behavioural exhaust nobody reads is a
 * privacy cost with no product return.
 *
 * PRIVACY
 * Telemetry initializes only when an application id and client token are
 * both configured, so preview and local builds report nothing. The
 * subscriber's identity is sent as an opaque tier plus a hashed id when the
 * platform supplies one; email addresses are never sent, and Datadog's
 * default input masking stays on.
 */
import { DATADOG, datadogConfigured } from "../../config.js";
import { profileSegments } from "./subscriberProfile.js";

let rum = null;
let started = false;

/**
 * Start Datadog RUM. The SDK is imported dynamically so a deployment
 * without telemetry configured never downloads it.
 */
export async function startTelemetry() {
  if (started || !datadogConfigured()) return;
  started = true;
  try {
    const mod = await import("@datadog/browser-rum");
    rum = mod.datadogRum;
    rum.init({
      applicationId: DATADOG.applicationId,
      clientToken: DATADOG.clientToken,
      site: DATADOG.site,
      service: DATADOG.service,
      env: DATADOG.env,
      version: DATADOG.version || undefined,
      sessionSampleRate: DATADOG.sampleRate,
      sessionReplaySampleRate: DATADOG.sessionReplaySampleRate,
      trackResources: true,
      trackLongTasks: true,
      trackUserInteractions: false,
      defaultPrivacyLevel: "mask-user-input",
    });
  } catch {
    // Telemetry must never be the reason a reader cannot use the service.
    rum = null;
  }
}

/**
 * Attach the subscription to the session as segments a dashboard can group
 * by — the tier, and the class of organization the address implies — and
 * never the person. The reader is asked for none of it. No address and no
 * domain: a single tribe's domain in an analytics tool identifies the
 * reader on its own.
 */
export function identify(user) {
  if (!rum) return;
  if (!user) {
    rum.clearUser();
    return;
  }
  rum.setUser({ id: user.subscriber_id ?? undefined, ...profileSegments(user) });
}

/**
 * The events worth having. `name` is one of the constants below so the
 * dashboard is not built from strings typed at each call site.
 */
export function track(name, properties = {}) {
  if (!rum) return;
  rum.addAction(name, properties);
}

/** Something failed in a way the reader saw. */
export function trackError(error, context = {}) {
  if (!rum) return;
  rum.addError(error, context);
}

export const EVENT = Object.freeze({
  signedIn: "press.signed_in",
  signInFailed: "press.sign_in_failed",
  signedOut: "press.signed_out",
  sectionOpened: "press.section_opened",
  collectionViewed: "press.collection_viewed",
  collectionDownloaded: "press.collection_downloaded",
  shelfDownloadedAll: "press.shelf_downloaded_all",
  lockedCollectionTapped: "press.locked_collection_tapped",
  upgradeOpened: "press.upgrade_opened",
  articleOpened: "press.article_opened",
  cedarAsked: "press.cedar_asked",
  // The Explore card: a cut narrowed (which filters, never which entity),
  // downloaded as a file, or kept on the reader's device.
  exploreCut: "press.explore_cut",
  exploreDownloaded: "press.explore_downloaded",
  exploreSaved: "press.explore_saved",
});
