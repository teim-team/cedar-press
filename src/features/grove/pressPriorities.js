// REVIEW OWNER: Havala
//
// Shape the Research, on the client: the priorities as the owner seeds them,
// the words for their types and statuses, the points rule as the service
// states it, and the one function that reads a request against the list.
//
// The rule lives in server/cedar_press/priorities.py and the ledger with
// it; nothing here counts a point. This module reads the same seed file so
// the page can list the priorities before the service answers (or in a
// build with no service at all, where it says so), and mirrors the
// related-priority search word for word so the form can suggest before the
// request is sent and the service agrees when it arrives.

import seed from "../../../data/cedar/priorities.json" with { type: "json" };
import { MONTHS } from "./pressReleases.js";

export const POINTS_PER_ACTIVE_MONTH = Object.freeze({ ...seed.rules.points_per_active_month });
export const EXPIRY_MONTHS = seed.rules.expiry_months;
export const POINTS_RULE = seed.rules.note;

export const PRIORITY_TYPES = Object.freeze({
  research_question: Object.freeze({
    label: "Research question",
    plural: "Research questions",
    lede: "Things Cedar Press should investigate, answer or publish research around.",
  }),
  dataset: Object.freeze({
    label: "Data priority",
    plural: "Data priorities",
    lede: "Things subscribers want Cedar to build, expand, improve or collect.",
  }),
});

/** The statuses in the order a priority moves through them. */
export const PRIORITY_STATUSES = Object.freeze([
  Object.freeze({ id: "interest", label: "Gathering interest" }),
  Object.freeze({ id: "under_review", label: "Under review" }),
  Object.freeze({ id: "research_underway", label: "Research underway" }),
  Object.freeze({ id: "data_construction_underway", label: "Data construction underway" }),
  Object.freeze({ id: "published", label: "Published" }),
]);

export function statusLabel(id) {
  return PRIORITY_STATUSES.find((s) => s.id === id)?.label ?? id;
}

/** The seeded priorities with no points: what a build without the service shows. */
export const SEED_PRIORITIES = Object.freeze(
  seed.priorities.map((p) => Object.freeze({ ...p, status: p.status ?? "interest", points: 0, subscribers: 0 })),
);

export const SEED_PRIORITIES_BY_ID = Object.freeze(Object.fromEntries(SEED_PRIORITIES.map((p) => [p.id, p])));

/** Most supported first, then most subscribers, then by title. */
export function sortPriorities(list) {
  return [...list].sort((a, b) => b.points - a.points || b.subscribers - a.subscribers || a.title.localeCompare(b.title));
}

export function byType(list, type) {
  return sortPriorities(list.filter((p) => p.type === type));
}

// ── Related priorities: the same function as priorities.py, word for word ──

const STOP = new Set(
  "a an and are as at be by for from has have how in into is it its of on or that the their there these this to was we what which who will with you your i wish had dataset data showing show more about would like want need".split(" "),
);

export function tokens(text) {
  return new Set((String(text ?? "").toLowerCase().match(/[a-z0-9]+/g) ?? []).filter((w) => w.length >= 3 && !STOP.has(w)));
}

export function relatedness(query, priority) {
  const q = tokens(query);
  const p = tokens(`${priority.title ?? ""} ${priority.description ?? ""}`);
  if (!q.size || !p.size) return 0;
  let shared = 0;
  for (const w of q) if (p.has(w)) shared += 1;
  return shared / Math.sqrt(q.size * p.size);
}

export const RELATED_THRESHOLD = 0.2;

/** The priorities a request reads as being about, best first, none below the threshold. */
export function related(query, priorities = SEED_PRIORITIES, limit = 3) {
  return priorities
    .map((p) => ({ p, s: relatedness(query, p) }))
    .filter(({ s }) => s >= RELATED_THRESHOLD)
    .sort((a, b) => b.s - a.s || a.p.id.localeCompare(b.p.id))
    .slice(0, limit)
    .map(({ p, s }) => ({ ...p, relatedness: Math.round(s * 1000) / 1000 }));
}

// ── Words ──


/** "2026-09" -> "Sept. 2026", the way the What's New feed spells a month. */
export function formatMonth(month) {
  const m = /^(\d{4})-(\d{2})$/.exec(month ?? "");
  if (!m) return month ?? "";
  return `${MONTHS[Number(m[2]) - 1]} ${m[1]}`;
}

export function pointsWord(n) {
  return `${n} point${n === 1 ? "" : "s"}`;
}

/** One line for a ledger entry: "+2 · Active month", "−1 · Tribal enterprise ownership". */
export function describeActivity(entry) {
  const sign = entry.amount > 0 ? "+" : "−";
  const what = {
    monthly_activity: "Active month",
    allocation: entry.title ?? entry.priority_id ?? "Allocated",
    refund: `Returned from ${entry.title ?? entry.priority_id ?? "a priority"}`,
    expiration: "Expired after twelve months",
  }[entry.reason] ?? entry.reason;
  return `${sign}${Math.abs(entry.amount)} · ${what}`;
}

/** What the profile says about earning: the rate for this tier, in words. */
export function earningLine(tier) {
  const rate = POINTS_PER_ACTIVE_MONTH[tier] ?? 0;
  if (!rate) return "This plan does not earn Cedar Points.";
  return `Earn ${pointsWord(rate)} in each month you use Cedar Press. Allocate them to the research questions and datasets you want Cedar to prioritize.`;
}

/** "You asked. Cedar researched it." material: the published ones, most supported first. */
export function published(list) {
  return sortPriorities(list.filter((p) => p.status === "published"));
}
