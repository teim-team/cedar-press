/**
 * PURPOSE
 * Where a subscriber's profile lives, on both sides of the seam.
 *
 * Connected, it is a column on the subscriber record: the platform holds it,
 * every session sees it, and the roadmap can query it — which is the whole
 * point, since a shelf curated for whoever is actually reading needs to know
 * who that is across the subscription, not in one browser.
 *
 * Standalone, there is nowhere to put it, so it stays in this browser and
 * the interface says the answers are not saved to an account. Same shape
 * either way, so the card above it does not branch.
 */
import * as api from "../../api.js";
import { isConnected } from "../../config.js";
import { normalizeProfile } from "./subscriberProfile.js";

const LOCAL_KEY = "cedar-press-profile";

function readLocal() {
  try {
    const raw = localStorage.getItem(LOCAL_KEY);
    return raw ? normalizeProfile(JSON.parse(raw)) : null;
  } catch {
    return null;
  }
}

function writeLocal(profile) {
  try {
    localStorage.setItem(LOCAL_KEY, JSON.stringify(profile));
  } catch {
    // A profile that cannot persist still applies for this session.
  }
}

export async function loadProfile({ signal } = {}) {
  if (isConnected()) {
    const payload = await api.fetchProfile({ signal });
    return normalizeProfile(payload?.profile ?? payload);
  }
  return readLocal();
}

export async function saveProfile(profile) {
  const next = normalizeProfile({ ...profile, updatedAt: new Date().toISOString() });
  if (isConnected()) {
    const saved = await api.saveProfile(next);
    return normalizeProfile(saved?.profile ?? saved) ?? next;
  }
  writeLocal(next);
  return next;
}

/**
 * Remember that the reader put the questions aside. Kept wherever the
 * profile is kept, so declining on a phone does not re-ask on a laptop when
 * the deployment is connected.
 */
export async function dismissProfile(profile) {
  return saveProfile({ ...(profile ?? {}), dismissed: true });
}
