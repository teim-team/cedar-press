// Cedar on the door answers without the network, which means the bank itself
// is the product: a trigger that stops matching, or a follow-up pointing at an
// intent that no longer exists, degrades silently into a refusal. These are
// the failures a reader would see.

import assert from "node:assert/strict";
import test from "node:test";

import {
  DOOR_CHIPS,
  DOOR_FALLBACK,
  DOOR_INTENTS,
  DOOR_STARTERS,
  answer,
  classify,
  followUpsFor,
  intentForCollection,
} from "./doorCedar.js";
import { STOREFRONT_CATALOG } from "./pressCatalog.js";

test("every starter resolves to an intent with a chip", () => {
  assert.equal(DOOR_CHIPS.length, DOOR_STARTERS.length);
  for (const intent of DOOR_CHIPS) assert.ok(intent.chip, `${intent.id} has no chip`);
});

test("each of the twelve collections has its own answer", () => {
  for (const entry of STOREFRONT_CATALOG) {
    const intent = intentForCollection(entry.id);
    assert.ok(intent, `no intent for ${entry.id}`);
    assert.ok(intent.answer.length > 80, `${entry.id} answers in a line`);
  }
});

test("a chip's own label classifies back to the chip's intent", () => {
  for (const intent of DOOR_CHIPS) {
    assert.equal(classify(intent.chip)?.id, intent.id, `${intent.id} does not match its own chip`);
  }
});

test("a question it has nothing for refuses instead of guessing", () => {
  assert.equal(answer("what is the weather in Oslo").id, DOOR_FALLBACK.id);
  assert.match(DOOR_FALLBACK.answer, /do not have that one/);
});

// The follow-up row under an answer is the door's version of the behaviour
// lumecon.ai's FAB has: at most three next questions, never the whole starter
// stack again. An id that no longer exists would render a short row or none,
// which reads as the conversation running out rather than as a bug.
test("every follow-up an answer offers is a real intent with a chip", () => {
  for (const intent of DOOR_INTENTS) {
    const next = followUpsFor(intent);
    assert.ok(next.length >= 1, `${intent.id} offers nothing next`);
    assert.ok(next.length <= 3, `${intent.id} offers ${next.length} next questions`);
    for (const candidate of next) {
      assert.ok(DOOR_INTENTS.includes(candidate), `${intent.id} points at a stranger`);
      assert.ok(candidate.chip, `${intent.id} offers a chipless ${candidate.id}`);
    }
  }
});

test("a follow-up never offers the answer it is sitting under", () => {
  for (const intent of DOOR_INTENTS) {
    assert.ok(
      !followUpsFor(intent).some((c) => c.id === intent.id),
      `${intent.id} offers itself`,
    );
  }
});

test("a follow-up never re-asks what the thread already answered", () => {
  const first = followUpsFor(DOOR_INTENTS[0]);
  const answered = new Set([DOOR_INTENTS[0].id, first[0].id]);
  const second = followUpsFor(DOOR_INTENTS[0], answered);
  for (const candidate of second) assert.ok(!answered.has(candidate.id), `${candidate.id} repeats`);
});

test("the twelve collections all offer the same three next questions", () => {
  const shape = followUpsFor(intentForCollection(STOREFRONT_CATALOG[0].id)).map((c) => c.id);
  assert.deepEqual(shape, ["entities", "sources", "plans"]);
  for (const entry of STOREFRONT_CATALOG) {
    assert.deepEqual(followUpsFor(intentForCollection(entry.id)).map((c) => c.id), shape);
  }
});

test("the refusal still offers a way back into the bank", () => {
  const next = followUpsFor(DOOR_FALLBACK).map((c) => c.id);
  assert.deepEqual(next, ["what", "collections", "plans"]);
});

test("an exhausted conversation gets no row rather than a repeat", () => {
  const answered = new Set(DOOR_INTENTS.map((intent) => intent.id));
  assert.deepEqual(followUpsFor(DOOR_INTENTS[0], answered), []);
});

// ── The conversation around the bank ──────────────────────────────────────
// The door used to answer without memory: "tell me more" was refused, the
// same question twice printed the same paragraph, and every miss was one
// fixed sentence. These pin the behaviours the shared runtime gives it.

import { beginTurn, detectAudience, freshThread, settleTurn } from "./cedarConversation.js";
import {
  DOOR_AUDIENCES,
  NON_TOPIC_IDS,
  OUT_OF_SCOPE_TRIGGERS,
  doorFollowUps,
  doorMatcher,
  missAnswer,
  resolveDoor,
} from "./doorCedar.js";

function door() {
  let thread = freshThread();
  return {
    get memory() {
      return thread.memory;
    },
    say(question, options = {}) {
      const resolution = resolveDoor(thread.memory, question, options);
      thread = settleTurn(beginTurn(thread, question), resolution, {
        nonTopicIds: NON_TOPIC_IDS,
        audience: detectAudience(DOOR_AUDIENCES, question),
        followUpsFor: doorFollowUps,
      });
      return { ...resolution, chips: thread.followUps.map((c) => c.label) };
    },
  };
}

test("every topic has a deeper answer for tell me more, and none of it breaks the house style", () => {
  for (const intent of DOOR_INTENTS) {
    if (intent.chip) assert.ok(intent.expanded?.length > 80, `${intent.id} has no deeper answer`);
    for (const text of [intent.answer, intent.expanded ?? "", intent.chip ?? "", ...(intent.variants ?? [])]) {
      assert.ok(!text.includes("—"), `em dash in ${intent.id}`);
      assert.ok(!/&amp;|[A-Za-z0-9] & [A-Za-z0-9]/.test(text), `ampersand in ${intent.id}`);
      assert.ok(!/prepared (set|material|answers)/i.test(text), `${intent.id} announces its machinery`);
    }
  }
});

test("tell me more after a collection goes deeper on that collection", () => {
  const c = door();
  const first = c.say("what is in the deals collection");
  assert.equal(first.intent.id, "collection:deals");
  assert.equal(first.chips[0], "Tell me more");
  const more = c.say("tell me more");
  assert.equal(more.kind, "drilldown");
  assert.equal(more.intent.id, "collection:deals");
  assert.match(more.text, /^Going deeper on how Deals is built/);
  assert.ok(!more.chips.includes("Tell me more"));
});

test("the same question twice is answered deeper, then acknowledged, never verbatim", () => {
  const c = door();
  const first = c.say("How current is it?");
  const second = c.say("How current is it?");
  const third = c.say("How current is it?");
  assert.equal(second.kind, "repeat");
  assert.match(second.text, /^We touched on this earlier/);
  assert.notEqual(second.text, first.text);
  assert.notEqual(third.text, second.text);
  assert.ok(third.text.endsWith(first.text), "the restatement still carries the answer");
});

test("a question naming two topics answers one and offers the other first", () => {
  const c = door();
  const r = c.say("how much does it cost and how current is it");
  assert.equal(r.intent.id, "plans");
  assert.equal(r.secondary?.id, "current");
  assert.equal(r.chips[0], "How current is it?");
  const two = door().say("deals or funding");
  assert.equal(two.intent.id, "collection:funding");
  assert.equal(two.chips[0], "Deals");
});

test("a typo still reaches the collection", () => {
  assert.equal(door().say("legislaton").intent.id, "collection:legislation");
  assert.equal(answer("repatriaton").id, "collection:nagpra");
});

test("a miss says so, offers the closest topics, and after a second miss names the research desk", () => {
  const c = door();
  const first = c.say("what is the weather in Oslo");
  assert.equal(first.kind, "miss");
  assert.match(first.text, /I do not have that one here on the front page/);
  assert.match(first.text, /closest things I can speak to/);
  assert.doesNotMatch(first.text, /contact@lumecon\.ai/);
  assert.ok(first.chips.length >= 1 && first.chips.length <= 3);
  const second = c.say("banana bread");
  assert.match(second.text, /research desk answers in person: contact@lumecon\.ai/);
  assert.equal(c.memory.misses, 2);
  assert.equal(missAnswer("x", [], false), missAnswer("x"));
});

test("who is the president is a miss, not a match on the word who", () => {
  assert.equal(door().say("who is the president of mexico").kind, "miss");
  assert.ok(OUT_OF_SCOPE_TRIGGERS.includes("who is the president"));
});

test("a reader who says who they are gets their own route in as a quick reply", () => {
  const c = door();
  const r = c.say("for my story, what is in the legislation collection");
  assert.equal(r.intent.id, "collection:legislation");
  assert.equal(c.memory.audience, "research");
  assert.ok(c.say("federal funding").chips.includes("I'm a researcher or journalist"));
});

test("filler is never the last topic, and greetings do not repeat verbatim", () => {
  const c = door();
  c.say("what is nagpra");
  const hello = c.say("hi");
  const again = c.say("hi");
  assert.notEqual(hello.text, again.text);
  assert.equal(c.memory.priorTopicId, "collection:nagpra");
  assert.equal(c.say("yes").kind, "drilldown");
});

test("every collection is reachable by its chip, its id and its extra words", () => {
  for (const entry of STOREFRONT_CATALOG) {
    const intent = intentForCollection(entry.id);
    assert.equal(doorMatcher.classify(entry.id.replace(/-/g, " "))?.id, intent.id, entry.id);
    assert.equal(doorMatcher.classify(`what is in ${entry.short || entry.name}`)?.id, intent.id, entry.id);
  }
  assert.equal(doorMatcher.classify("do you track royalties")?.id, "collection:natural-resources");
  assert.equal(doorMatcher.classify("form 990 filings")?.id, "collection:nonprofits");
});
