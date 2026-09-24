// The conversation runtime is what makes Cedar read as a conversation rather
// than a menu, so its behaviours are pinned here against a small bank whose
// answers are known: the matcher's rules, the memory's transitions and the
// quick replies under each kind of answer. The door's real bank is tested in
// doorCedar.test.js; the reader's quick replies in readerCedar.test.js.

import assert from "node:assert/strict";
import test from "node:test";

import {
  EXPECTATION_LINE,
  MAX_FOLLOW_UPS,
  REPEAT_BRIDGES,
  REPEAT_DEEPEN,
  beginTurn,
  createMatcher,
  detectAudience,
  followUpsFor,
  freshMemory,
  freshThread,
  normalise,
  remember,
  repeatAnswer,
  resolveLocally,
  retireFollowUps,
  settleTurn,
  shouldClarify,
  thinkingPause,
} from "./cedarConversation.js";

const INTENTS = Object.freeze([
  { id: "pricing", chip: "How much does it cost?", triggers: ["how much", "price", "pricing", "cost"], answer: "Pricing answer.", expanded: "Pricing, deeper.", followUps: ["deals", "access"] },
  { id: "access", chip: "How do I get access?", triggers: ["get access", "access", "sign up"], answer: "Access answer.", followUps: ["pricing"] },
  { id: "deals", chip: "Deals", triggers: ["deals", "deal", "acquisition"], answer: "Deals answer.", expanded: "Deals, deeper.", followUps: ["funding", "pricing"] },
  { id: "funding", chip: "Federal Funding", triggers: ["funding", "grants", "federal awards"], answer: "Funding answer.", expanded: "Funding, deeper.", followUps: ["deals"] },
  { id: "legislation", chip: "Legislation", triggers: ["legislation", "bills", "congress"], answer: "Legislation answer.", followUps: ["deals"] },
  { id: "tribal", chip: "I work for a tribal government", triggers: ["tribal government", "my nation"], answer: "Tribal answer.", followUps: ["access"] },
  { id: "tell_me_more", chip: null, triggers: ["tell me more", "go deeper"], answer: "Pick a topic and I will go deeper." },
  { id: "affirmative", chip: null, triggers: ["yes", "sure"], answer: "Which one?", variants: ["Go ahead.", "Name it."] },
  { id: "thanks", chip: null, triggers: ["thanks", "thank you"], answer: "You're welcome.", variants: ["Any time.", "Glad it helped."] },
]);
const NON_TOPIC = new Set(["tell_me_more", "affirmative", "thanks"]);
const matcher = createMatcher(INTENTS, { outOfScopeTriggers: ["weather", "who is the president"] });
const BANK = Object.freeze({
  matcher,
  drillDownIds: new Set(["tell_me_more"]),
  affirmativeIds: new Set(["affirmative"]),
  nonTopicIds: NON_TOPIC,
  audiences: [{ key: "tribal", intentId: "tribal", words: ["my nation", "our tribe"] }],
  defaultFollowUps: ["pricing", "access", "deals"],
  miss: (question, nearest, handingOff) =>
    `MISS ${nearest.map((i) => i.id).join(",")}${handingOff ? " HANDOFF" : ""}`,
});

/** Run a question through resolve + settle, the way the hook does. */
function converse() {
  let thread = freshThread();
  return {
    get memory() {
      return thread.memory;
    },
    say(question, options = {}) {
      const resolution = resolveLocally(BANK, thread.memory, question, options);
      thread = settleTurn(beginTurn(thread, question), resolution, {
        nonTopicIds: NON_TOPIC,
        audience: detectAudience(BANK.audiences, question),
        followUpsFor: (memory, reply) => followUpsFor(BANK, memory, reply),
      });
      return { ...resolution, chips: thread.followUps.map((c) => c.label) };
    },
  };
}

test("normalise pads, lowers, strips punctuation and apostrophes", () => {
  assert.equal(normalise("  What's  the DEAL?! "), " whats the deal ");
  assert.equal(normalise("8(a) set-aside"), " 8(a) set aside ");
});

test("a trigger matches whole phrases only, never inside another word", () => {
  assert.equal(matcher.classify("tell me about the deal")?.id, "deals");
  assert.equal(matcher.classify("the dealer said no"), null);
  assert.equal(matcher.classify(""), null);
});

test("a longer phrase outweighs a single word, and a tie falls to declaration order", () => {
  // "federal awards" (2) beats "deals" (1).
  assert.equal(matcher.classify("deals and federal awards")?.id, "funding");
  // A bare tie: pricing is declared before access.
  assert.equal(matcher.classify("access price")?.id, "pricing");
});

test("a second topic is offered when it is multi-word or tied with the first", () => {
  assert.equal(matcher.secondary("how much does it cost, and where do i sign up", "pricing")?.id, "access");
  assert.equal(matcher.secondary("deals or funding", "deals")?.id, "funding");
  // A stray single word that lost to a stronger match is not a topic.
  assert.equal(matcher.secondary("federal awards for a deal", "funding"), null);
});

test("a typo one edit from a trigger still routes, an unrelated word does not", () => {
  assert.equal(matcher.fuzzy("legislaton")?.id, "legislation");
  assert.equal(matcher.fuzzy("aquisition")?.id, "deals");
  assert.equal(matcher.fuzzy("banana bread"), null);
});

test("the nearest topics for a miss are chip-bearing and closest first", () => {
  const near = matcher.nearest("how much is pricing", 2);
  assert.equal(near[0].id, "pricing");
  assert.ok(near.every((i) => i.chip));
  assert.ok(near.length <= 2);
});

test("out-of-scope triggers are recognised on whole phrases", () => {
  assert.ok(matcher.isOutOfScope("what is the weather in Oslo"));
  assert.ok(!matcher.isOutOfScope("the weathervane collection"));
});

test("clarification is asked only on a real tie", () => {
  assert.ok(!shouldClarify(1, 2));
  assert.ok(shouldClarify(2, 2));
  assert.ok(shouldClarify(1, 3));
});

test("a first answer is the intent's own; tell me more drills into it", () => {
  const c = converse();
  const first = c.say("what are the deals");
  assert.equal(first.kind, "answer");
  assert.equal(first.text, "Deals answer.");
  assert.deepEqual(first.chips.slice(0, 1), ["Tell me more"]);
  const more = c.say("tell me more");
  assert.equal(more.kind, "drilldown");
  assert.equal(more.intent.id, "deals");
  assert.equal(more.text, "Deals, deeper.");
  assert.ok(!more.chips.includes("Tell me more"), "the deeper answer does not offer itself again");
});

test("a plain yes after a topic drills too; with no topic it is filler", () => {
  const cold = converse();
  assert.equal(cold.say("yes").kind, "answer");
  assert.equal(cold.say("tell me more").text, "Pick a topic and I will go deeper.");
  const warm = converse();
  warm.say("funding");
  assert.equal(warm.say("sure").text, "Funding, deeper.");
});

test("thanks does not displace the last topic", () => {
  const c = converse();
  c.say("deals");
  c.say("thanks");
  assert.equal(c.memory.priorTopicId, "deals");
  assert.equal(c.say("go deeper").text, "Deals, deeper.");
});

test("the same question twice gets the deeper answer, then an acknowledged restatement", () => {
  const c = converse();
  c.say("deals");
  const second = c.say("deals");
  assert.equal(second.kind, "repeat");
  assert.equal(second.text, REPEAT_DEEPEN + "Deals, deeper.");
  const third = c.say("deals");
  assert.equal(third.text, REPEAT_BRIDGES[1] + "Deals answer.");
  const fourth = c.say("deals");
  assert.equal(fourth.text, REPEAT_BRIDGES[2] + "Deals answer.");
  assert.notEqual(second.text, third.text);
});

test("filler rotates its variants on repeats, so two hellos never read the same", () => {
  const c = converse();
  assert.equal(c.say("thanks").text, "You're welcome.");
  assert.equal(c.say("thanks").text, "Any time.");
  assert.equal(c.say("thanks").text, "Glad it helped.");
  assert.equal(c.say("thanks").text, "Any time.");
  assert.equal(repeatAnswer(INTENTS[0], 1, true), REPEAT_BRIDGES[0] + "Pricing answer.");
});

test("a compound question answers the first topic and offers the second first", () => {
  const c = converse();
  const r = c.say("how much does it cost, and where do i sign up");
  assert.equal(r.intent.id, "pricing");
  assert.equal(r.secondary.id, "access");
  assert.equal(r.chips[0], "How do I get access?");
});

test("a strong tie asks which one rather than guessing", () => {
  const c = converse();
  const r = c.say("federal awards tribal government");
  assert.equal(r.kind, "clarify");
  assert.ok(r.clarified);
  assert.match(r.text, /Did you mean "Federal Funding" or "I work for a tribal government"\?/);
  assert.deepEqual(r.chips, ["Federal Funding", "I work for a tribal government"]);
  assert.equal(c.memory.priorTopicId, null, "a guess is not remembered as the topic");
});

test("an out-of-scope signal beats a weak single-word match, not a strong one", () => {
  const c = converse();
  assert.equal(c.say("who is the president, any deals?").kind, "miss");
  assert.equal(c.say("what is the weather like for federal awards").intent.id, "funding");
});

test("a miss offers the closest topics, and the second in a row hands off", () => {
  const c = converse();
  const first = c.say("banana bread");
  assert.equal(first.kind, "miss");
  assert.ok(first.missed);
  assert.match(first.text, /^MISS/);
  assert.doesNotMatch(first.text, /HANDOFF/);
  // The nearest topics, then the bank's defaults; never more than three,
  // never a chipless intent.
  assert.ok(first.chips.length >= 1 && first.chips.length <= MAX_FOLLOW_UPS);
  const labels = INTENTS.filter((i) => i.chip).map((i) => i.chip);
  assert.ok(first.chips.every((chip) => labels.includes(chip)));
  assert.equal(c.memory.misses, 1);
  const second = c.say("zzz qqq");
  assert.match(second.text, /HANDOFF$/);
  assert.equal(c.memory.misses, 2);
  c.say("deals");
  assert.equal(c.memory.misses, 0, "a hit resets the count");
});

test("a forced intent is answered as chosen, never re-classified", () => {
  const c = converse();
  const r = c.say("How much does it cost?", { forced: INTENTS[1] });
  assert.equal(r.intent.id, "access");
  assert.equal(r.text, "Access answer.");
  assert.equal(r.secondary, null);
});

test("the audience the reader names biases one quick-reply slot, from this answer on", () => {
  const c = converse();
  const r = c.say("I work for our tribe, what are the deals");
  assert.equal(r.intent.id, "deals");
  assert.equal(c.memory.audience, "tribal");
  assert.ok(r.chips.includes("I work for a tribal government"), "under this very answer, not the next");
  const later = c.say("funding");
  assert.ok(later.chips.includes("I work for a tribal government"));
  assert.equal(detectAudience(BANK.audiences, "just deals"), null);
});

test("quick replies never exceed three, never repeat the answer or what was already answered", () => {
  const c = converse();
  c.say("pricing");
  const r = c.say("deals");
  assert.ok(r.chips.length <= MAX_FOLLOW_UPS);
  assert.ok(!r.chips.includes("Deals"));
  assert.ok(!r.chips.includes("How much does it cost?"), "pricing was already answered");
  assert.deepEqual(r.chips, ["Tell me more", "Federal Funding"]);
});

test("remember counts answers, records shown depth and keeps the prior topic object", () => {
  let m = freshMemory();
  m = remember(m, { intent: INTENTS[2], kind: "answer", missed: false }, { nonTopicIds: NON_TOPIC });
  assert.equal(m.answered.deals, 1);
  assert.equal(m.priorTopic, INTENTS[2]);
  m = remember(m, { intent: INTENTS[2], kind: "drilldown", missed: false }, { nonTopicIds: NON_TOPIC });
  assert.deepEqual([...m.expandedShown], ["deals"]);
  assert.equal(m.answered.deals, 1, "a drill-down is not a second answer");
  assert.ok(Object.isFrozen(m));
});

test("a thread appends the reader's turn, retires the last chips, then settles Cedar's turn with its extras", () => {
  let t = freshThread();
  t = settleTurn(beginTurn(t, "hello"), { text: "hi", intent: INTENTS[0], kind: "answer" }, { followUpsFor: () => [{ label: "x" }] });
  assert.equal(t.turns.length, 2);
  assert.deepEqual(t.turns.map((x) => x.role), ["you", "cedar"]);
  assert.equal(t.followUps.length, 1);
  t = beginTurn(t, "again");
  assert.equal(t.followUps.length, 0);
  t = settleTurn(t, { text: "cited", basis: { kind: "release" }, source: "profile" });
  const last = t.turns[t.turns.length - 1];
  assert.equal(last.basis.kind, "release");
  assert.equal(last.source, "profile");
  assert.equal(last.kind, "answer");
  assert.notEqual(t.turns[0].key, t.turns[2].key);
});

test("the thinking pause scales with length, is clamped, and collapses under reduced motion", () => {
  const fixed = { random: () => 0.5 };
  assert.equal(thinkingPause("", fixed), 600);
  assert.equal(thinkingPause("x".repeat(2000), fixed), 1600);
  assert.equal(thinkingPause("x".repeat(100), { ...fixed, elapsed: 300 }), 720 - 300);
  assert.equal(thinkingPause("anything", { reducedMotion: true }), 150);
  assert.equal(thinkingPause("anything", { reducedMotion: true, elapsed: 900 }), 0);
});

test("the expectation line is the site's, in the house style", () => {
  assert.match(EXPECTATION_LINE, /^Cedar can make mistakes\. Verify important details/);
  assert.doesNotMatch(EXPECTATION_LINE, /prepared|preset|script/i);
  assert.doesNotMatch(EXPECTATION_LINE, /—|&/);
});

// ── Findings from the review of 235a8ce ──────────────────────────────────

test("a follow-up that names a topic is that topic, not a drill-down into the last one", () => {
  const c = converse();
  c.say("deals");
  const named = c.say("tell me more about funding");
  assert.equal(named.kind, "answer");
  assert.equal(named.intent.id, "funding");
  assert.equal(named.text, "Funding answer.");
  // On a fresh thread it is the topic too, not a request to pick one.
  const fresh = converse().say("tell me more about deals");
  assert.equal(fresh.intent.id, "deals");
  assert.equal(fresh.text, "Deals answer.");
  // A bare phrase still drills, with or without a please.
  const bare = converse();
  bare.say("deals");
  assert.equal(bare.say("Tell me more, please").kind, "drilldown");
});

test("a clarification offers every tied topic, including ones already discussed", () => {
  const c = converse();
  c.say("funding");
  c.say("tribal government");
  const r = c.say("federal awards tribal government");
  assert.equal(r.kind, "clarify");
  assert.deepEqual(r.chips, ["Federal Funding", "I work for a tribal government"]);
});

test("a repeat that already supplied the depth does not offer to go deeper again", () => {
  const c = converse();
  c.say("deals");
  const deeper = c.say("deals");
  assert.equal(deeper.text, REPEAT_DEEPEN + "Deals, deeper.");
  assert.ok(!deeper.chips.includes("Tell me more"), deeper.chips.join(" / "));
  assert.ok(c.memory.expandedShown.includes("deals"));
});

test("retiring the quick replies leaves the turns and the memory alone", () => {
  let t = freshThread();
  t = settleTurn(beginTurn(t, "deals"), { text: "Deals answer.", intent: INTENTS[2] }, { followUpsFor: () => [{ label: "x" }] });
  const retired = retireFollowUps(t);
  assert.deepEqual([...retired.followUps], []);
  assert.equal(retired.turns, t.turns);
  assert.equal(retired.memory, t.memory);
});
