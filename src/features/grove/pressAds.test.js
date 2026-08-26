import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import test from "node:test";

import { AD_SLOT, AD_SLOTS, adsPreview, creativeFor, slotSpec } from "./pressAds.js";

const page = (name) =>
  readFileSync(fileURLToPath(new URL(`../../pages/grove/${name}`, import.meta.url)), "utf8");

test("every slot id has a spec, and every spec has an id", () => {
  for (const id of Object.values(AD_SLOT)) {
    assert.ok(slotSpec(id), `${id} has no spec`);
  }
  assert.equal(AD_SLOTS.length, Object.values(AD_SLOT).length);
});

// The state that ships. A slot with nothing booked has to resolve to nothing
// at all, because the component renders no element when this returns null.
test("nothing is sold, so every slot resolves to nothing", () => {
  for (const id of Object.values(AD_SLOT)) {
    assert.equal(creativeFor(id), null, id);
  }
});

test("the preview is off unless a URL asks for it by name", () => {
  assert.equal(adsPreview(""), false);
  assert.equal(adsPreview("?ads=1"), false);
  assert.equal(adsPreview("?ads=true"), false);
  assert.equal(adsPreview("?demo=ads"), false);
  assert.equal(adsPreview(undefined), false);
  assert.equal(adsPreview(null), false);
  assert.equal(adsPreview("?ads=demo"), true);
  assert.equal(adsPreview("?view=data&ads=demo"), true);
});

// Rule 2 in pressAds.js, pinned rather than trusted. These three pages exist
// to be believed, and a sponsor on any of them is worth less than what it
// costs. Rule 3 covers the gate, which is a sign-in.
test("no sponsorship reaches a trust surface or the way in", () => {
  for (const name of [
    "CedarPressMethods.jsx",
    "CedarPressTribalRequest.jsx",
    "CedarPressResearchAccess.jsx",
    "PressGate.jsx",
  ]) {
    assert.ok(!page(name).includes("PressAd"), `${name} carries a slot`);
  }
});

// Rule 1. The shelves are the data, and a unit beside a collection tile reads
// as a sponsor of the collection.
test("no sponsorship reaches the shelves", () => {
  assert.ok(!page("PressShelf.jsx").includes("PressAd"));
});

// Rule 1 again, at the seam that is easiest to get wrong. The article page
// sells three slots, and the temptation is to put one inside the block that
// offers the data. Nothing may sit between a reader and a download.
test("the article page sells the rail and the end, never the data block", () => {
  const src = page("CedarPressArticle.jsx");
  const dataBlock = src.slice(src.indexOf("cp-ar__data"));
  assert.ok(!dataBlock.includes("PressAd"), "a slot sits inside the underlying-data block");
  assert.ok(src.includes("AD_SLOT.ARTICLE_RAIL"), "the rail carries no slot");
});

test("every slot says where it is and what fits, for the media kit", () => {
  for (const slot of AD_SLOTS) {
    assert.match(slot.size, /^\d+ × \d+$/, slot.id);
    assert.ok(slot.where.length > 10, slot.id);
    assert.ok(slot.note.length > 10, slot.id);
    assert.ok(["strip", "box"].includes(slot.shape), slot.id);
    if (slot.shape === "box") assert.ok(slot.ratio, slot.id);
    if (slot.shape === "strip") assert.ok(slot.height, slot.id);
  }
});
