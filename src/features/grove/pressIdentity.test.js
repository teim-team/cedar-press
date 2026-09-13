// The identity section is the strongest claim the Methods page makes, so every
// class code and every field name in it is checked against the published
// register and the registry schemas. A claim about an identifier is worth
// nothing if the identifier stopped being there.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

import {
  IDENTIFIERS,
  LINKAGE_MOVES,
  LOOP_CLOSE,
  LOOP_STAGES,
  WITHHELD_CLASS,
} from "./pressIdentity.js";

const read = (relative) => JSON.parse(readFileSync(new URL(relative, import.meta.url), "utf8"));
const register = read("../../../public/data/cedar/register.json");
const entitySchema = read("../../../cedar_source_registry/schema/harmonized_entity.schema.json");
const recordSchema = read("../../../cedar_source_registry/schema/source_record.schema.json");

test("every class an identifier claims is a class the published register holds", () => {
  const codes = new Set(register.classes.map((entry) => entry.code));
  for (const identifier of IDENTIFIERS) {
    assert.ok(identifier.classes.length > 0, `${identifier.id} names no class`);
    for (const code of identifier.classes) {
      assert.ok(codes.has(code), `${identifier.label} claims register class "${code}", which the register does not hold`);
    }
  }
});

test("every field an identifier names is a real field", () => {
  // cedar_uid is the spine's, documented in docs/IDENTIFIER_STANDARD.md; the
  // other two are the registry schemas'.
  const known = new Set([
    "cedar_uid",
    ...Object.keys(entitySchema.properties ?? {}),
    ...Object.keys(recordSchema.properties ?? {}),
  ]);
  for (const identifier of IDENTIFIERS) {
    for (const field of identifier.fields) {
      assert.ok(known.has(field), `${identifier.label} names field "${field}", which no schema declares`);
    }
  }
  const doc = readFileSync(new URL("../../../docs/IDENTIFIER_STANDARD.md", import.meta.url), "utf8");
  assert.match(doc, /cedar_uid/, "the identifier standard no longer documents cedar_uid");
});

test("the withheld class is really withheld in the published register", () => {
  const index = register.classes.findIndex((entry) => entry.code === WITHHELD_CLASS);
  assert.ok(index >= 0, `the register no longer holds the class "${WITHHELD_CLASS}"`);
  const rows = register.entities.filter((entity) => entity[2] === index);
  assert.ok(rows.length > 0, `the register holds no ${WITHHELD_CLASS} rows`);
  for (const [uid, name] of rows) {
    assert.equal(name, null, `${uid} publishes a name the withholding rule says it should not`);
    assert.match(uid, /^CE-[0-9A-Z]{5}-[0-9A-Z]{2}$/, `${uid} is not a well-formed cedar_uid`);
  }
  assert.equal(
    rows.length,
    register.withheld_names,
    "the register's withheld_names count disagrees with its own withheld rows",
  );
});

test("the shapes shown on the page are shapes the standard permits", () => {
  const entity = IDENTIFIERS.find((item) => item.id === "entity");
  // Crockford base32 with I, L, O and U removed: a sample uid that contained
  // one of those would be teaching a reader an impossible id.
  assert.match(entity.shape, /^CE-[0-9ABCDEFGHJKMNPQRSTVWXYZ]{5}-[0-9ABCDEFGHJKMNPQRSTVWXYZ]{2}$/);
  // The business id shows no sample. Its customer-facing CB- form is decided
  // (docs/CEDAR_BUSINESS_ID_DECISION_2026-09-06.md) and nothing mints it yet,
  // and the form that IS minted is a source-record key with a source code in
  // it, which the decision's first rule forbids as an identity. A sample here
  // again means CB- shipped; check that it did.
  const business = IDENTIFIERS.find((item) => item.id === "business");
  assert.equal(business.shape, null, "the business card shows a sample; is CB- minted?");
});

test("the prose keeps the brand lock", () => {
  const prose = [
    ...IDENTIFIERS.flatMap((item) => [item.names, item.note, ...item.survives]),
    ...LINKAGE_MOVES.flatMap((item) => [item.label, item.body]),
    ...LOOP_STAGES.flatMap((item) => [item.label, item.body]),
    LOOP_CLOSE,
  ];
  for (const line of prose) {
    assert.ok(!line.includes("—"), `em dash in "${line}"`);
    assert.ok(!/\bnot just\b/i.test(line), `antithesis in "${line}"`);
    // The tell the owner named: a sentence that ends on a comma and then a
    // fragment ("this is only the beginning, new data every day"). Bare
    // possessive "its" after a comma is an ordinary list item and was a false
    // positive on "its resource revenue, its advocacy and its structure", and
    // a subordinate ", which is why ..." is ordinary English, not the tell.
    assert.ok(!/,\s*(and\s+)?(it's|that's|this is)\b/i.test(line), `comma splice in "${line}"`);
  }
});

test("the loop does not claim an institution uses or endorses Cedar", () => {
  // The team's Federal Reserve experience is evidenced as affiliation. A
  // sentence saying the Federal Reserve uses Cedar's methods is not, and it is
  // the one claim on this page a reader could disprove.
  const all = LOOP_STAGES.map((stage) => stage.body).join(" ");
  assert.match(all, /Federal Reserve/, "the loop no longer says where the methods come from");
  assert.ok(
    !/(Federal Reserve[^.]*\b(uses|relies on|endorses)\b)|(\buses\b[^.]*Cedar's methods)/i.test(all),
    "the loop asserts institutional use or endorsement, which nothing in the workspace evidences",
  );
});
