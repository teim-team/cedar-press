/**
 * REVIEW OWNER: Havala
 *
 * The Cedar conversation runtime, shared by the door and the in-product panel.
 *
 * WHY ONE MODULE
 * Cedar Press had two panels that looked alike and behaved differently. The
 * door answered from a bank but kept no memory: "tell me more" after an
 * answer was refused as a question it had nothing for, the same question
 * asked twice printed the same paragraph twice, and every miss printed the
 * same refusal. lumecon.ai's Cedar (`src/lib/cedarChat.ts` there) is the
 * reference, and it reads as a conversation because it remembers: the last
 * topic, what it has already said, and whether it has missed twice in a row.
 *
 * This module is that runtime with the answer source left open. A bank of
 * intents matched locally (the door, which never reaches the network) and a
 * service answering over HTTP (the reader, which does) both feed the same
 * thread, the same memory, the same quick replies. `useCedarThread.js` is the
 * React seam; nothing in here touches the DOM, so all of it runs under
 * `node --test`.
 *
 * WHAT IS HERE
 *   - a matcher over an intent bank: whole-phrase triggers, longer phrases
 *     weigh more, ties fall to declaration order, a Fuse index rescues a
 *     typo, and a looser Fuse search names the nearest topics for a miss;
 *   - the local resolver: drill-downs ("tell me more" after a topic), repeat
 *     awareness (a deeper answer, then an acknowledged restatement, never the
 *     same paragraph verbatim), clarification on a real tie, compound
 *     questions (the second topic becomes the first quick reply), a graceful
 *     miss that offers the closest topics, and a hand-off after two misses;
 *   - the thread and its memory as plain values with pure transitions;
 *   - the quick replies under an answer.
 *
 * Nothing in here invents a fact: every sentence Cedar says on the door is a
 * string an intent carries, and the runtime only chooses which one.
 */

import Fuse from "fuse.js";

/**
 * The one line of expectation-setting under the composer, the same on every
 * Cedar surface. lumecon.ai's reads "Cedar can make mistakes. Verify important
 * details against linked pages or with our team. This site chat does not run
 * analyses." This is that line with the two things a Press reader can check
 * against and without the sentence about analyses, which Press does not run.
 * At the shared 380px it wraps to the same three lines the site's does
 * (measured in the panel's own Inter), which is what keeps the two panels
 * the same height; a longer line wrapped to four and the layout test named it.
 */
export const EXPECTATION_LINE =
  "Cedar can make mistakes. Verify important details against the methods page or with our team.";

/**
 * Lower-cased, punctuation stripped, padded with one space each side so a
 * padded trigger matches only on word boundaries: " deal " does not match
 * "dealer", and "i'm" and "im" normalise to the same thing.
 */
export const normalise = (text) =>
  ` ${String(text ?? "")
    .toLowerCase()
    .replace(/['’`]/g, "")
    .replace(/[^a-z0-9()+ ]+/g, " ")
    .replace(/\s+/g, " ")
    .trim()} `;

const words = (needle) => needle.trim().split(" ").filter(Boolean).length;

/* Fuse's score is 0 for a perfect match and 1 for none. 0.25 is tight enough
   that a random five-letter word does not find a neighbour, loose enough
   that a transposition or a dropped letter still routes. */
const TYPO_THRESHOLD = 0.25;
/* The nearest-topic search is deliberately looser: it is not deciding an
   answer, only which three chips to offer under a miss. */
const NEAREST_THRESHOLD = 0.55;

/**
 * A matcher over a bank of intents. Each intent: `{ id, chip, triggers,
 * answer, expanded?, variants?, followUps?, links? }`, in priority order.
 */
export function createMatcher(intents, { outOfScopeTriggers = [] } = {}) {
  const bank = intents.map((intent) => ({
    intent,
    needles: [...new Set(intent.triggers.map((t) => normalise(t)).filter((n) => n.trim()))],
  }));

  // Single-word triggers of five letters or more, for the typo rescue. A
  // multi-word trigger tokenised would index "what", "data" and "how", and
  // let a typo in an unrelated sentence hijack a topic.
  const typoIndex = new Fuse(
    bank.flatMap(({ intent }, idx) =>
      [...new Set(intent.triggers.map((t) => t.toLowerCase().trim()))]
        .filter((t) => t.length >= 5 && !/[\s-]/.test(t))
        .map((w) => ({ w, idx })),
    ),
    { keys: ["w"], includeScore: true, threshold: TYPO_THRESHOLD, ignoreLocation: true, minMatchCharLength: 4 },
  );

  // Chip labels and triggers together, for "the closest things I can speak
  // to" under a miss. Only chip-bearing intents: a filler cannot be a topic.
  const nearestIndex = new Fuse(
    bank
      .filter(({ intent }) => intent.chip)
      .map(({ intent }) => ({ id: intent.id, text: [intent.chip, ...intent.triggers].join(" ") })),
    { keys: ["text"], includeScore: true, threshold: NEAREST_THRESHOLD, ignoreLocation: true, minMatchCharLength: 3 },
  );

  const oos = outOfScopeTriggers.map((t) => normalise(t)).filter((n) => n.trim());
  const byId = new Map(intents.map((intent) => [intent.id, intent]));

  /** Every intent that scores, with its score. Longer phrases weigh more. */
  function scoreAll(question) {
    const asked = normalise(question);
    if (asked.trim().length < 2) return [];
    const scored = [];
    for (const { intent, needles } of bank) {
      let score = 0;
      for (const needle of needles) if (asked.includes(needle)) score += Math.max(1, words(needle));
      if (score > 0) scored.push({ intent, score });
    }
    return scored;
  }

  /** The top score and every intent tied at it, in declaration order. */
  function topMatches(question) {
    const scored = scoreAll(question);
    let best = 0;
    for (const s of scored) if (s.score > best) best = s.score;
    return { score: best, intents: scored.filter((s) => s.score === best).map((s) => s.intent) };
  }

  /** The best intent, or null when nothing matched a whole phrase. */
  function classify(question) {
    const { score, intents: tied } = topMatches(question);
    return score >= 1 ? tied[0] : null;
  }

  /**
   * A strong second topic in the same message, distinct from the primary:
   * "how much does it cost and how current is it" scores plans first and
   * current second. Needs a multi-word hit, or a tie with the primary, so a
   * stray single word cannot claim a quick-reply slot.
   */
  function secondary(question, primaryId) {
    const scored = scoreAll(question);
    const primary = scored.find((s) => s.intent.id === primaryId)?.score ?? 0;
    const rest = scored
      .filter((s) => s.intent.id !== primaryId && s.intent.chip)
      .sort((a, b) => b.score - a.score);
    if (!rest.length) return null;
    // A runner-up tied with the primary named a second topic as plainly as
    // the first ("deals or funding"): the primary won on declaration order
    // alone, so the other is offered rather than dropped.
    return rest[0].score >= 2 || rest[0].score === primary ? rest[0].intent : null;
  }

  /** A typo rescue: one word of the question is one edit from a trigger. */
  function fuzzy(question) {
    const tokens = normalise(question).trim().split(" ").filter((t) => t.length >= 5);
    let best = null;
    for (const token of tokens) {
      const hit = typoIndex.search(token, { limit: 1 })[0];
      if (!hit || typeof hit.score !== "number" || hit.score > TYPO_THRESHOLD) continue;
      if (Math.abs(hit.item.w.length - token.length) > 2) continue;
      if (!best || hit.score < best.score) best = { idx: hit.item.idx, score: hit.score };
    }
    return best ? bank[best.idx].intent : null;
  }

  /** The chip-bearing intents nearest a question, closest first. */
  function nearest(question, limit = 3) {
    const seen = new Set();
    const out = [];
    for (const hit of nearestIndex.search(String(question ?? ""), { limit: limit * 2 })) {
      if (seen.has(hit.item.id)) continue;
      seen.add(hit.item.id);
      out.push(byId.get(hit.item.id));
      if (out.length === limit) break;
    }
    return out;
  }

  function isOutOfScope(question) {
    const asked = normalise(question);
    return oos.some((needle) => asked.includes(needle));
  }

  return { intents, byId, scoreAll, topMatches, classify, secondary, fuzzy, nearest, isOutOfScope };
}

/* ── Memory ──────────────────────────────────────────────────────────────── */

/** A fresh memory: nothing discussed, nothing missed. */
export const freshMemory = () =>
  Object.freeze({
    /** The last substantive topic, for "tell me more": the intent itself
     *  (or, on a surface with no bank, a `{ id, chip }` record). */
    priorTopic: null,
    /** Its id, for lookups. */
    priorTopicId: null,
    /** How many times each intent has been answered in this thread. */
    answered: Object.freeze({}),
    /** Intents whose deeper answer has already been shown. */
    expandedShown: Object.freeze([]),
    /** Consecutive misses; two in a row hands the reader to a person. */
    misses: 0,
    /** Who the reader said they are, biasing one quick-reply slot. */
    audience: null,
  });

/**
 * Only clarify when the ambiguity is real: two distinct multi-word topics
 * tied, or three or more topics sharing the top score. A two-way tie on a
 * single bare word is usually a compound question the declaration-order
 * winner can just answer.
 */
export const shouldClarify = (score, candidates) => candidates >= 3 || (score >= 2 && candidates >= 2);

const list = (labels) =>
  labels.length <= 1 ? labels[0] : `${labels.slice(0, -1).join(", ")} or ${labels[labels.length - 1]}`;

/** The bridge into a deeper answer on a repeat, and the restatement openers. */
export const REPEAT_DEEPEN = "We touched on this earlier, so here is a level deeper. ";
export const REPEAT_BRIDGES = Object.freeze([
  "Coming back around to this one. ",
  "Happy to run this one back. ",
  "Same ground as before, in case a second pass helps. ",
]);

/**
 * What to say when an intent has been answered before. A deeper answer the
 * first time there is one; a rotating acknowledgement and the answer after
 * that; filler intents rotate their own variants instead.
 */
export function repeatAnswer(intent, timesAnswered, expandedSeen) {
  if (intent.variants?.length) return intent.variants[(timesAnswered - 1) % intent.variants.length];
  if (typeof intent.expanded === "string" && !expandedSeen) return REPEAT_DEEPEN + intent.expanded;
  return REPEAT_BRIDGES[(timesAnswered - 1) % REPEAT_BRIDGES.length] + intent.answer;
}

/**
 * The local resolver: the whole decision for one question against a bank.
 *
 * `bank` is `{ matcher, drillDownIds, affirmativeIds, nonTopicIds,
 * audiences, miss(question, nearest, handingOff), clarify?(labels) }`.
 * Returns `{ text, intent, kind, secondary, missed, clarified }` where
 * `kind` is one of answer, drilldown, repeat, clarify, miss.
 */
export function resolveLocally(bank, memory, question, { forced = null } = {}) {
  const { matcher } = bank;
  const nonTopic = bank.nonTopicIds ?? new Set();
  const drill = bank.drillDownIds ?? new Set();
  const affirm = bank.affirmativeIds ?? new Set();
  const prior = memory.priorTopic ?? (memory.priorTopicId ? matcher.byId.get(memory.priorTopicId) : null);

  // A chip is an explicit choice of intent: route straight to it rather than
  // re-classifying its label, which may not contain its own triggers.
  const matched = forced ?? matcher.classify(question);
  const isDrillDown =
    !forced && matched != null && (drill.has(matched.id) || affirm.has(matched.id)) && typeof prior?.expanded === "string";

  if (isDrillDown) {
    return { text: prior.expanded, intent: prior, kind: "drilldown", secondary: null, missed: false, clarified: false };
  }

  const { score, intents: tied } = matcher.topMatches(question);
  const candidates = tied.filter((i) => i.chip);
  const oos = !forced && matcher.isOutOfScope(question);

  if (!forced && !oos && shouldClarify(score, candidates.length)) {
    const labels = candidates.slice(0, 3).map((c) => `"${c.chip}"`);
    const text =
      bank.clarify?.(labels) ??
      `I can read that a couple of ways, and I would rather get it right than guess. Did you mean ${list(labels)}? Tell me which one, or add a few words, and I will go from there.`;
    return { text, intent: null, kind: "clarify", secondary: null, missed: false, clarified: true, candidates };
  }

  // An out-of-scope signal beats a weak single-word match; a strong,
  // multi-word match still wins.
  let intent = matched;
  if (!forced && (!intent || (oos && score <= 1))) intent = oos ? null : matcher.fuzzy(question);
  if (!intent) {
    const near = matcher.nearest(question);
    const handingOff = memory.misses + 1 >= 2;
    return {
      text: bank.miss(question, near, handingOff),
      intent: null,
      kind: "miss",
      secondary: null,
      missed: true,
      clarified: false,
      nearest: near,
    };
  }

  const seen = memory.answered[intent.id] ?? 0;
  const kind = seen > 0 ? "repeat" : "answer";
  const text = seen > 0 ? repeatAnswer(intent, seen, memory.expandedShown.includes(intent.id)) : intent.answer;
  const second = forced || nonTopic.has(intent.id) ? null : matcher.secondary(question, intent.id);
  return { text, intent, kind, secondary: second, missed: false, clarified: false };
}

/** Which audience a question names, if any: `{ key, intentId }` or null. */
export function detectAudience(audiences = [], question) {
  const asked = normalise(question);
  for (const audience of audiences) {
    if (audience.words.some((w) => asked.includes(normalise(w)))) return audience;
  }
  return null;
}

/**
 * The memory after an answer has been given. Pure: the old memory is not
 * touched. `resolution` is what `resolveLocally` (or a service resolver
 * shaped like it) returned; `nonTopicIds` are the fillers that never become
 * "the last topic".
 */
export function remember(memory, resolution, { nonTopicIds = new Set(), audience = null } = {}) {
  const { intent, kind, missed } = resolution;
  const answered = { ...memory.answered };
  const expandedShown = [...memory.expandedShown];
  let priorTopic = memory.priorTopic ?? null;

  if (intent && kind !== "drilldown") answered[intent.id] = (answered[intent.id] ?? 0) + 1;
  if (intent && (kind === "drilldown" || (kind === "repeat" && resolution.text.startsWith(REPEAT_DEEPEN)))) {
    if (!expandedShown.includes(intent.id)) expandedShown.push(intent.id);
  }
  if (intent && !resolution.clarified && !nonTopicIds.has(intent.id)) priorTopic = intent;

  return Object.freeze({
    priorTopic,
    priorTopicId: priorTopic?.id ?? null,
    answered: Object.freeze(answered),
    expandedShown: Object.freeze(expandedShown.slice(-60)),
    misses: missed ? memory.misses + 1 : 0,
    audience: audience?.key ?? memory.audience,
  });
}

/* ── Quick replies ───────────────────────────────────────────────────────── */

export const MAX_FOLLOW_UPS = 3;

/**
 * Up to three next questions under an answer, as `{ label, text, intent }`.
 *
 * In order: the other half of a compound question (the reader literally just
 * asked it); "Tell me more" when the topic has a deeper answer not yet shown;
 * one slot for the reader's stated audience; then the topic's own related
 * questions, or the bank's defaults. Never the answer it sits under, never
 * anything this thread has already answered, never a chipless intent.
 */
export function followUpsFor(bank, memory, resolution) {
  const { matcher } = bank;
  const audiences = bank.audiences ?? [];
  const intent = resolution.intent;
  const out = [];
  const push = (id) => {
    if (out.length >= MAX_FOLLOW_UPS) return;
    if (!id || id === intent?.id || memory.answered[id]) return;
    const next = matcher.byId.get(id);
    if (!next?.chip || out.some((o) => o.intent?.id === id)) return;
    out.push({ label: next.chip, text: next.chip, intent: next });
  };

  if (resolution.kind === "miss") {
    for (const near of resolution.nearest ?? []) push(near.id);
    for (const id of bank.defaultFollowUps ?? []) push(id);
    return out.slice(0, MAX_FOLLOW_UPS);
  }
  if (resolution.kind === "clarify") {
    for (const candidate of resolution.candidates ?? []) push(candidate.id);
    return out.slice(0, MAX_FOLLOW_UPS);
  }

  if (resolution.secondary) push(resolution.secondary.id);
  if (
    intent &&
    resolution.kind !== "drilldown" &&
    typeof intent.expanded === "string" &&
    !memory.expandedShown.includes(intent.id)
  ) {
    out.push({ label: "Tell me more", text: "tell me more", intent: null });
  }
  const audience = audiences.find((a) => a.key === memory.audience);
  if (audience) push(audience.intentId);
  const related = intent?.followUps?.length ? intent.followUps : (bank.defaultFollowUps ?? []);
  for (const id of related) push(id);
  return out.slice(0, MAX_FOLLOW_UPS);
}

/* ── The thread ──────────────────────────────────────────────────────────── */

let nextKey = 0;
const turn = (role, text, extra = {}) => ({ key: `t${(nextKey += 1)}`, role, text, ...extra });

/** An empty thread with a fresh memory. */
export const freshThread = () => Object.freeze({ turns: Object.freeze([]), memory: freshMemory(), followUps: Object.freeze([]) });

/** The thread with the reader's turn appended and the last quick replies retired. */
export function beginTurn(thread, echo) {
  return Object.freeze({ ...thread, turns: Object.freeze([...thread.turns, turn("you", echo)]), followUps: Object.freeze([]) });
}

/**
 * The thread with Cedar's turn appended and the memory advanced.
 *
 * `reply` is `{ text, intent, kind, ...extra }`; anything beyond the runtime's
 * own fields (a basis line, a gate, an error) rides on the turn untouched, so
 * a surface can render what only it knows about. `followUpsFor(memory,
 * reply)` names the quick replies to show under it; it sees the memory as it
 * was before this answer, with the audience this question named already in
 * it, so a reader who has just said who they are sees their own route in
 * under this very answer rather than the next one.
 */
export function settleTurn(thread, reply, { nonTopicIds, audience, followUpsFor } = {}) {
  const { text, intent = null, kind = "answer", ...extra } = reply;
  const resolution = { ...reply, intent, kind };
  const biased = audience ? { ...thread.memory, audience: audience.key } : thread.memory;
  const followUps = followUpsFor ? followUpsFor(biased, resolution) : [];
  const memory = remember(thread.memory, resolution, { nonTopicIds, audience });
  return Object.freeze({
    turns: Object.freeze([...thread.turns, turn("cedar", text ?? "", { intent, kind, ...extra })]),
    memory,
    followUps: Object.freeze([...followUps]),
  });
}

/**
 * How long the typing indicator stays up before an answer lands, so a reply
 * reads as composed rather than precomputed. Scales with length, clamped so
 * a short answer does not feel instant and a long one does not stall, with a
 * little jitter so the rhythm is not a metronome. Near-instant under reduced
 * motion, and never added on top of time a real request already spent.
 */
export function thinkingPause(text, { reducedMotion = false, elapsed = 0, random = Math.random } = {}) {
  if (reducedMotion) return Math.max(0, 150 - elapsed);
  const base = Math.min(1600, Math.max(600, 420 + String(text ?? "").length * 3));
  return Math.max(0, Math.round(base * (0.85 + random() * 0.3)) - elapsed);
}
