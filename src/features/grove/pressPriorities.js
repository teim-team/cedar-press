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

/**
 * WHAT TO ASK FOR: EXAMPLES, NOT A ROADMAP (owner, 2026-09-26).
 *
 * Collections answer what the current evidence can answer; Priorities is
 * where a subscriber asks what intelligence should exist next. These show
 * the scale of ask the page is for. None is planned, scheduled or promised,
 * and the page labels them as examples where they are shown.
 *
 *   datasets   ambitious collections that do not exist yet, one per theme
 *   research   ambitious questions, split into descriptive patterns (what
 *              happened, where, how much) and causal ones (why, and what
 *              changed because of it), which need a research design beyond
 *              the records and say so
 *   expansions narrower asks that grow a collection Cedar already publishes;
 *              shown smaller, beneath the other two
 *
 * None names a collection that is announced but not released.
 */
export const PRIORITY_EXAMPLES = Object.freeze({
  datasets: Object.freeze([
    Object.freeze({ theme: "Infrastructure", text: "Every broadband, water, road and transit project on tribal lands, with its funding sources, sponsors, cost and completion status." }),
    Object.freeze({ theme: "Capital access", text: "Loans, guarantees and equity reaching Native enterprises and households, by lender type, terms and outcome." }),
    Object.freeze({ theme: "Housing", text: "Housing units built, rehabilitated and financed by tribal housing authorities, with the programs and partners behind each one." }),
    Object.freeze({ theme: "Healthcare", text: "Tribal and Indian Health Service facilities, the services each offers, its staffing and its funding over time." }),
    Object.freeze({ theme: "Energy", text: "Energy projects on tribal lands from proposal to operation, with capacity, ownership, offtake and revenue to the Nation." }),
    Object.freeze({ theme: "Workforce", text: "Employment in tribal governments and enterprises by sector and occupation, including TERO hiring and training outcomes." }),
  ]),
  research: Object.freeze({
    descriptive: Object.freeze([
      "Which tribal enterprises have grown fastest in federal contracting over the last decade, and in which industries?",
      "How is federal assistance to Native nations distributed across agencies and programs, and how has that mix shifted?",
      "Where are Native-owned businesses concentrated by industry and region, and how does that compare with tribal enterprises?",
    ]),
    causal: Object.freeze([
      "Did changes to 8(a) rules alter how tribally owned firms grow?",
      "Does federal infrastructure funding change how many enterprises a Nation starts in the years that follow?",
      "How much of a Nation's economic diversification follows from its gaming revenue?",
    ]),
  }),
  expansions: Object.freeze([
    "Add annual filing history to Native Nonprofits.",
    "Add more tribal TERO and commerce offices to Individual Native-Owned Businesses.",
    "Carry Natural Resource Revenues to more Nations and commodities.",
  ]),
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
