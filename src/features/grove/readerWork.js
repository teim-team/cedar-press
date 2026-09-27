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

/**
 * The kinds of work the collections are built for.
 *
 * THE OFFERED LIST IS THE LANDING PAGE'S AUDIENCES, IN LANDING ORDER
 * (owner, 2026-09-26: "the personas should match what is on the landing
 * page"). `readerWork.test.js` holds the two lists together.
 *
 * AN ID IS A STORED ANSWER, SO IT OUTLIVES ITS LABEL. Where the meaning
 * survived a relabel the id is kept (`tribal_enterprise` now reads "Native
 * enterprise"; `advisor`, `media` and `academic` likewise), so an answer
 * given under the old wording still means what the reader meant.
 *
 * TWO ANSWERS ARE RETIRED, NOT REMAPPED. `federal` and `state_local` are not
 * landing audiences, and they are not "outside partner" either: a federal
 * agency and an economic development organization are different readers.
 * So neither is offered to a reader choosing today, and a reader who already
 * gave one keeps it verbatim, shown under its original label, until they
 * choose something else (`workOptions`). The service accepts every id in
 * this list, retired or not (`press_catalog.WORK_KINDS`, dumped from it by
 * `scripts/dump-press.mjs`), so a stored answer is never refused on re-save.
 */
export const WORK_KINDS = Object.freeze(
  [
    { id: "tribal_government", label: "Tribal Nation or tribal government" },
    { id: "anc_nho", label: "ANC or NHO" },
    { id: "tribal_enterprise", label: "Native enterprise" },
    { id: "lender_investor", label: "Bank, lender or investor (CDFIs included)" },
    { id: "native_nonprofit", label: "Native nonprofit" },
    { id: "foundation", label: "Foundation or philanthropy" },
    { id: "business", label: "Business working in Indian Country" },
    { id: "academic", label: "University or research institution" },
    { id: "media", label: "Newsroom or journalist" },
    { id: "advisor", label: "Advisor or professional services firm" },
    { id: "economic_development", label: "Economic development organization or outside partner" },
    // Retired 2026-09-26: never offered, kept so a stored answer keeps its meaning.
    { id: "federal", label: "Federal agency", retired: true },
    { id: "state_local", label: "State or local government", retired: true },
  ].map((kind) => Object.freeze(kind)),
);

/** What a reader choosing today is offered: the landing audiences, in order. */
export const OFFERED_WORK_KINDS = Object.freeze(WORK_KINDS.filter((kind) => !kind.retired));

const BY_ID = new Map(WORK_KINDS.map((kind) => [kind.id, kind]));

/** A stored value the taxonomy knows, retired or not, unchanged; otherwise null. */
export function normalizeWork(value) {
  return typeof value === "string" && BY_ID.has(value) ? value : null;
}

/** The label a stored answer is shown under, or null for one nobody declared. */
export function workLabel(value) {
  return BY_ID.get(value)?.label ?? null;
}

/**
 * The options the select shows a reader whose stored answer is `stored`: the
 * offered list, with a retired answer first when it is theirs, so opening
 * Settings and saving does not silently drop it. The same rule teim-app's
 * Settings follows for a stored role outside its preset list.
 */
export function workOptions(stored) {
  const kind = BY_ID.get(stored);
  return kind?.retired ? [kind, ...OFFERED_WORK_KINDS] : OFFERED_WORK_KINDS;
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
