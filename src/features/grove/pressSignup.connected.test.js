import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const source = readFileSync(new URL("./pressSignup.js", import.meta.url), "utf8");
const anchor = 'import { isConnected } from "../../config.js";';
assert.equal(source.split(anchor).length, 2);
const { initialPressStep, PRESS_STEP } = await import("data:text/javascript;base64," +
  Buffer.from(source.replace(anchor, "const isConnected = () => true;")).toString("base64"));

test("an explicit login on a fresh workspace host uses the existing password flow", () => {
  const storage = { getItem: () => null };
  assert.equal(initialPressStep(storage, { signInRequested: true }), PRESS_STEP.SIGN_IN);
  assert.equal(initialPressStep(storage), PRESS_STEP.ACTIVATE);
});

test("blocked browser storage does not turn an explicit login into activation", () => {
  const storage = { getItem: () => { throw new Error("Storage blocked"); } };
  assert.equal(initialPressStep(storage, { signInRequested: true }), PRESS_STEP.SIGN_IN);
  assert.equal(initialPressStep(storage), PRESS_STEP.ACTIVATE);
});

test("the existing account hint remains compatible without a login query", () => {
  assert.equal(initialPressStep({ getItem: () => "1" }), PRESS_STEP.SIGN_IN);
});
