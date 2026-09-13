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
