// The Cedar Press way in. A code is the only thing standing between a Tribal
// Business News subscriber and an account, so the shape check is pinned
// rather than eyeballed.

import assert from "node:assert/strict";
import test from "node:test";

import {
  PRESS_ACTIVATION_AVAILABLE,
  formatPressCode,
  isPlausiblePressCode,
  normalizePressCode,
  pressSignupError,
} from "./pressSignup.js";

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
// the routes that validate a code. A code screen with nothing behind it takes
// a subscriber's code and tells them their membership does not work.
//
// This suite runs with no VITE_API_URL, so it is the standalone case.
test("standalone, activation is not offered", () => {
  assert.equal(PRESS_ACTIVATION_AVAILABLE, false);
});

// Each failure needs a different next step, so they must not collapse.
test("every redemption failure says something different and actionable", () => {
  const codes = [
    "PRESS_CODE_INVALID",
    "PRESS_CODE_USED",
    "PRESS_CODE_EXPIRED",
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
  // The server answers a real code with the wrong address as INVALID, so
  // that copy must point at the address as well as the code.
  assert.match(pressSignupError("PRESS_CODE_INVALID"), /address/i);
  assert.match(pressSignupError("PRESS_CODE_INVALID"), /membership/i);
});

test("an unknown failure falls back to the server's own message", () => {
  assert.equal(pressSignupError("SOMETHING_NEW", "Server said no"), "Server said no");
  assert.match(pressSignupError(null), /Check the details/);
});
