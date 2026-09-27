import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

import { DUOTONES, applyDuotone, toneClass, toneOf } from "./duotone.js";

test("black maps to the shadow and white to the highlight", () => {
  for (const [name, { shadow, highlight }] of Object.entries(DUOTONES)) {
    const px = applyDuotone(new Uint8ClampedArray([0, 0, 0, 255, 255, 255, 255, 128]), name);
    assert.deepEqual([...px.slice(0, 3)], shadow, name);
    assert.deepEqual([...px.slice(4, 7)], highlight, name);
    assert.equal(px[7], 128, "alpha is untouched");
  }
});

test("an unknown wash falls back to teal", () => {
  assert.equal(toneOf("purple"), "teal");
  assert.equal(toneOf(undefined), "teal");
  assert.equal(toneClass("gold"), "cp-tone--gold");
});

test("every wash has its SVG filter in index.html, with the same ramp", () => {
  const html = readFileSync(new URL("../../../index.html", import.meta.url), "utf8");
  for (const [name, { shadow, highlight }] of Object.entries(DUOTONES)) {
    const at = html.indexOf(`id="cp-duo-${name}"`);
    assert.ok(at > 0, `no filter for ${name}`);
    const block = html.slice(at, html.indexOf("</filter>", at));
    const values = [...block.matchAll(/tableValues="([\d.]+) ([\d.]+)"/g)].map((m) => [Number(m[1]), Number(m[2])]);
    assert.equal(values.length, 3, name);
    values.forEach(([lo, hi], c) => {
      assert.ok(Math.abs(lo - shadow[c] / 255) < 0.001, `${name} shadow ${c}`);
      assert.ok(Math.abs(hi - highlight[c] / 255) < 0.001, `${name} highlight ${c}`);
    });
  }
});
