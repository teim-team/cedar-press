// The Cedar Press way in. A code is the only thing standing between a Tribal
// Business News subscriber and an account, so the shape check and the mode
// memory are pinned rather than eyeballed.

import assert from "node:assert/strict";
import test from "node:test";

import {
  PRESS_ACTIVATION_AVAILABLE,
  PRESS_STEP,
  formatPressCode,
  initialPressStep,
  isPlausiblePressCode,
  normalizePressCode,
  pressSignupError,
  rememberPressAccount,
} from "./pressSignup.js";

function fakeStorage(initial = {}) {
  const store = { ...initial };
  return {
    getItem: (k) => (k in store ? store[k] : null),
    setItem: (k, v) => {
      store[k] = String(v);
    },
  };
}

const throwingStorage = {
  getItem() {
    throw new Error("blocked");
  },
  setItem() {
    throw new Error("blocked");
  },
};

test("a code normalizes past case, spaces and hyphens", () => {
  assert.equal(normalizePressCode("tbn4-9k2m-x7qd"), "TBN49K2MX7QD");
  assert.equal(normalizePressCode("  tbn4 9k2m x7qd "), "TBN49K2MX7QD");
  assert.equal(normalizePressCode(null), "");
});

test("a plausible code is alphanumeric and 8 to 32 characters", () => {
  assert.equal(isPlausiblePressCode("tbn4-9k2m-x7qd"), true);
  assert.equal(isPlausiblePressCode("ABCD1234"), true);
  assert.equal(isPlausiblePressCode("ABC123"), false, "too short");
  assert.equal(isPlausiblePressCode("A".repeat(33)), false, "too long");
  assert.equal(isPlausiblePressCode("TBN4-9K2M-X7Q!"), false, "punctuation");
  assert.equal(isPlausiblePressCode(""), false);
});

test("display grouping never changes what the code is", () => {
  const typed = "tbn49k2mx7qd";
  assert.equal(formatPressCode(typed), "TBN4-9K2M-X7QD");
  assert.equal(normalizePressCode(formatPressCode(typed)), normalizePressCode(typed));
});

// Activation follows connectivity, because only a connected build can reach
// the routes that validate a code. A standalone build — which is what
// cedarpress.ai serves, a static site with no backend — must open on
// sign-in for every browser: a code screen with nothing behind it takes a
// subscriber's code and tells them their membership does not work.
//
// This suite runs with no VITE_API_URL, so it is the standalone case.
test("standalone, every browser opens on sign-in", () => {
  assert.equal(PRESS_ACTIVATION_AVAILABLE, false, "standalone must not offer activation");
  assert.equal(initialPressStep(fakeStorage()), PRESS_STEP.SIGN_IN);
});

test("a browser that has activated opens on sign-in", () => {
  const storage = fakeStorage();
  rememberPressAccount(storage);
  assert.equal(initialPressStep(storage), PRESS_STEP.SIGN_IN);
});

// Private browsing throws on both calls; the gate still has to render.
test("blocked storage still renders a screen rather than throwing", () => {
  assert.equal(initialPressStep(throwingStorage), PRESS_STEP.SIGN_IN);
  assert.doesNotThrow(() => rememberPressAccount(throwingStorage));
  assert.equal(initialPressStep(undefined), PRESS_STEP.SIGN_IN);
});

// Each failure needs a different next step, so they must not collapse.
test("every redemption failure says something different and actionable", () => {
  const codes = [
    "PRESS_CODE_INVALID",
    "PRESS_CODE_USED",
    "PRESS_CODE_EXPIRED",
    "PRESS_CODE_EMAIL_MISMATCH",
    "EMAIL_IN_USE",
  ];
  const messages = codes.map((code) => pressSignupError(code));
  assert.equal(new Set(messages).size, codes.length);
  assert.match(pressSignupError("PRESS_CODE_USED"), /sign in/i);
  assert.match(pressSignupError("PRESS_CODE_EXPIRED"), /Tribal Business News/);
  assert.match(pressSignupError("EMAIL_IN_USE"), /sign in/i);
  // A code is one authorized user, so a reused one must say so rather than
  // reading as a generic failure.
  assert.match(pressSignupError("PRESS_CODE_USED"), /one authorized user/i);
  assert.match(pressSignupError("PRESS_CODE_EMAIL_MISMATCH"), /different address/i);
});

test("an unknown failure falls back to the server's own message", () => {
  assert.equal(pressSignupError("SOMETHING_NEW", "Server said no"), "Server said no");
  assert.match(pressSignupError(null), /Check the details/);
});
