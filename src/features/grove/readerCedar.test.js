// The reader's Cedar answers from the service; what this side owes the
// conversation is the quick replies under each answer, the memory that keeps
// them from repeating, and the reading of a bare "tell me more".

import assert from "node:assert/strict";
import test from "node:test";

import { freshMemory, remember } from "./cedarConversation.js";
import { OPEN_EXAMPLES, SCOPED_EXAMPLES, fabFollowUps, isDrillDown, topicOf } from "./readerCedar.js";

const SCOPE = { id: "deals", name: "Deals in Indian Country" };

test("a bare drill-down phrase is recognised, a real question is not", () => {
  assert.ok(isDrillDown("Tell me more"));
  assert.ok(isDrillDown("go deeper, please"));
  assert.ok(!isDrillDown("tell me more about the sources"));
  assert.ok(!isDrillDown("What changed in the latest release?"));
});

test("a topic id is the question at its scope, so the same words at two scopes are two topics", () => {
  assert.equal(topicOf("What does this collection cover?", SCOPE).id, "deals:what does this collection cover");
  assert.notEqual(topicOf("What does this collection cover?", SCOPE).id, topicOf("What does this collection cover?").id);
  assert.equal(topicOf("  x  ").chip, "x");
});

test("scoped quick replies are the profile's own questions, minus the one just asked", () => {
  let memory = freshMemory();
  const topic = topicOf(SCOPED_EXAMPLES[0], SCOPE);
  memory = remember(memory, { intent: topic, kind: "answer", missed: false });
  const chips = fabFollowUps(memory, { intent: topic, kind: "answer", source: "profile" }, { scope: SCOPE, examples: OPEN_EXAMPLES });
  assert.deepEqual(chips.map((c) => c.label), SCOPED_EXAMPLES.slice(1, 4));
  assert.ok(chips.every((c) => c.scope === SCOPE));
});

test("a question already asked in this thread is not offered again", () => {
  let memory = freshMemory();
  for (const q of SCOPED_EXAMPLES.slice(0, 3)) {
    memory = remember(memory, { intent: topicOf(q, SCOPE), kind: "answer", missed: false });
  }
  const chips = fabFollowUps(memory, { intent: topicOf("anything", SCOPE), kind: "answer", source: "profile" }, { scope: SCOPE, examples: [] });
  assert.deepEqual(chips.map((c) => c.label), [SCOPED_EXAMPLES[3]]);
});

test("tell me more is offered only when Cedar itself composed the answer", () => {
  const memory = freshMemory();
  const topic = topicOf("why does this matter", SCOPE);
  const composed = fabFollowUps(memory, { intent: topic, kind: "answer", source: "cedar" }, { scope: SCOPE, examples: [] });
  assert.equal(composed[0].label, "Tell me more");
  assert.equal(composed[0].text, "tell me more");
  const cited = fabFollowUps(memory, { intent: topic, kind: "answer", source: "profile" }, { scope: SCOPE, examples: [] });
  assert.ok(!cited.some((c) => c.label === "Tell me more"));
});

test("unscoped quick replies carry the collection each question is about, named in the label", () => {
  const chips = fabFollowUps(freshMemory(), { intent: topicOf("x"), kind: "answer", source: "profile" }, { scope: null, examples: OPEN_EXAMPLES });
  assert.ok(chips.length <= 3);
  for (const chip of chips) {
    assert.ok(chip.scope?.id, "an unscoped suggestion names its collection");
    assert.match(chip.label, new RegExp(`\\(${chip.scope.name.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}\\)$`));
    assert.equal(chip.text, chip.label.replace(` (${chip.scope.name})`, ""));
  }
});

test("a gate, a routing note or an error has nothing to follow up", () => {
  for (const kind of ["gate", "routing", "error"]) {
    assert.deepEqual(fabFollowUps(freshMemory(), { kind, text: "" }, { scope: SCOPE, examples: OPEN_EXAMPLES }), []);
  }
  assert.deepEqual(fabFollowUps(freshMemory(), null, { scope: SCOPE, examples: OPEN_EXAMPLES }), []);
});

test("every starter offered unscoped is a real collection", () => {
  assert.ok(OPEN_EXAMPLES.length >= 3);
  for (const example of OPEN_EXAMPLES) assert.ok(example.scope.id && example.scope.name);
});
