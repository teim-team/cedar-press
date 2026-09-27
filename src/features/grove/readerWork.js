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
import { AUDIENCE_JOBS, visibleAudiences } from "./pressJobs.js";

const LOCAL_KEY = "cedar-press-work";

/**
 * Landing audience id (`AUDIENCE_JOBS` in `pressJobs.js`) to the id a reader
 * in that audience stores.
 *
 * THE OFFERED LIST IS THE LANDING PAGE'S AUDIENCES: same set, same order,
 * same labels (owner, 2026-09-26: "the personas should match what is on the
 * landing page"; restated 2026-09-27). The labels and the order are READ
 * from the landing's own module rather than restated here, so the two cannot
 * drift; only this id map is local, because a stored id is a promise to the
 * reader who saved it and a landing id is not. `readerWork.test.js` fails
 * when a landing audience has no entry here.
 *
 * AN ID IS A STORED ANSWER, SO IT OUTLIVES ITS LABEL. Where the meaning
 * survived a relabel the id is kept (`advisor` now reads "Consultants and
 * advisors", `tribal_enterprise` "Native enterprises", and so on), so an
 * answer given under the old wording still means what the reader meant.
 */
const WORK_ID_BY_AUDIENCE = Object.freeze({
  "tribal-nations": "tribal_government",
  "ancs-nhos": "anc_nho",
  "native-enterprises": "tribal_enterprise",
  "banks-lenders": "lender_investor",
  "native-nonprofits": "native_nonprofit",
  "foundations-philanthropy": "foundation",
  businesses: "business",
  "universities-researchers": "academic",
  "government-officials": "government",
  journalists: "media",
  advisors: "advisor",
  "economic-development": "economic_development",
});

const landingKind = (audience) => {
  const id = WORK_ID_BY_AUDIENCE[audience.id];
  return id ? Object.freeze({ id, label: audience.audience }) : null;
};

const GOVERNMENT = landingKind(AUDIENCE_JOBS.find((audience) => audience.id === "government-officials"));

/**
 * TWO ANSWERS ARE PRESERVED, NOT REMAPPED (owner, 2026-09-27). `federal`
 * ("Federal agency") and `state_local` ("State or local government") were
 * answers before the government audience existed. They now belong to it, and
 * keep their level: the stored value stays exactly as saved (never rewritten
 * in the database or in localStorage), it is shown under the government
 * audience's label with its level in brackets, and it is offered only to the
 * reader who holds it (`workOptions`). They are never folded into economic
 * development or "outside partner": a federal agency is not one. The service
 * accepts every id in this list (`press_catalog.WORK_KINDS`, dumped from it
 * by `scripts/dump-press.mjs`), so a stored answer is never refused on
 * re-save; `workAudience` groups them with `government` for reporting.
 */
const PRESERVED = Object.freeze(
  [
    { id: "federal", level: "federal" },
    { id: "state_local", level: "state or local" },
  ].map(({ id, level }) =>
    Object.freeze({ id, label: `${GOVERNMENT.label} (${level})`, retired: true, audience: GOVERNMENT.id }),
  ),
);

/** Every answer the service accepts: each landing audience, then the preserved ones. */
export const WORK_KINDS = Object.freeze([
  ...AUDIENCE_JOBS.map(landingKind).filter(Boolean),
  ...PRESERVED,
]);

/** What a reader choosing today is offered: the landing's shown audiences, in its order, under its labels. */
export const OFFERED_WORK_KINDS = Object.freeze(visibleAudiences().map(landingKind).filter(Boolean));

const BY_ID = new Map(WORK_KINDS.map((kind) => [kind.id, kind]));

/** A stored value the taxonomy knows, preserved or not, unchanged; otherwise null. */
export function normalizeWork(value) {
  return typeof value === "string" && BY_ID.has(value) ? value : null;
}

/** The label a stored answer is shown under, or null for one nobody declared. */
export function workLabel(value) {
  return BY_ID.get(value)?.label ?? null;
}

/**
 * The audience an answer counts under, for reporting: `government` for
 * `federal`, `state_local` and `government` alike, the answer itself for
 * every other known id, and null for anything else. Pure; the stored value
 * is never changed by it.
 */
export function workAudience(value) {
  const kind = BY_ID.get(value);
  if (!kind) return null;
  return kind.audience ?? kind.id;
}

/**
 * The options the select shows a reader whose stored answer is `stored`: the
 * offered list, with the reader's own answer added when it is not on it, so
 * opening Settings and saving does not silently drop it. A preserved answer
 * sits directly after the audience it belongs to; anything else goes first.
 * The same rule teim-app's Settings follows for a stored role outside its
 * preset list.
 */
export function workOptions(stored) {
  const kind = BY_ID.get(stored);
  if (!kind || OFFERED_WORK_KINDS.some((offered) => offered.id === kind.id)) return OFFERED_WORK_KINDS;
  const at = OFFERED_WORK_KINDS.findIndex((offered) => offered.id === kind.audience);
  if (at < 0) return [kind, ...OFFERED_WORK_KINDS];
  return [...OFFERED_WORK_KINDS.slice(0, at + 1), kind, ...OFFERED_WORK_KINDS.slice(at + 1)];
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
