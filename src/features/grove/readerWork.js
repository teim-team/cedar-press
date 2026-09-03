/**
 * PURPOSE
 * What a reader works on, if they care to say.
 *
 * The collections are curated for whoever is actually reading them, and a
 * subscription only says an address. This is the one place the service asks
 * for more, it is optional, and it is asked as the trade it is: more detail,
 * better-curated collections.
 *
 * One field, not a form. A reader who answers should be done in a second,
 * and everything else the roadmap needs — which collections get opened, which
 * locked ones get reached for — the service already sees without asking.
 */
import * as api from "../../api.js";
import { isConnected } from "../../config.js";

const LOCAL_KEY = "cedar-press-work";

/** The kinds of work the collections are built for. */
export const WORK_KINDS = Object.freeze([
  { id: "tribal_government", label: "Tribal government" },
  { id: "tribal_enterprise", label: "Tribal enterprise or corporation" },
  { id: "anc_nho", label: "ANC or NHO" },
  { id: "native_nonprofit", label: "Native nonprofit or association" },
  { id: "federal", label: "Federal agency" },
  { id: "state_local", label: "State or local government" },
  { id: "lender_investor", label: "Lender, investor or fund" },
  { id: "advisor", label: "Law, accounting or consulting firm" },
  { id: "media", label: "Newsroom or media" },
  { id: "academic", label: "University or research institute" },
]);

const IDS = new Set(WORK_KINDS.map((kind) => kind.id));

/** A stored value the taxonomy still knows, or null. */
export function normalizeWork(value) {
  return typeof value === "string" && IDS.has(value) ? value : null;
}

export async function loadWork({ signal } = {}) {
  if (isConnected()) {
    const payload = await api.fetchProfile({ signal });
    return normalizeWork(payload?.work ?? payload?.profile?.work);
  }
  try {
    return normalizeWork(localStorage.getItem(LOCAL_KEY));
  } catch {
    return null;
  }
}

export async function saveWork(value) {
  const work = normalizeWork(value);
  if (isConnected()) {
    const saved = await api.saveProfile({ work });
    return normalizeWork(saved?.work ?? saved?.profile?.work ?? work);
  }
  try {
    if (work) localStorage.setItem(LOCAL_KEY, work);
    else localStorage.removeItem(LOCAL_KEY);
  } catch {
    // The answer applies for this session even if it cannot persist.
  }
  return work;
}
