// The identity section is the strongest claim the Methods page makes, so every
// class code and every field name in it is checked against the published
// register and the registry schemas. A claim about an identifier is worth
// nothing if the identifier stopped being there.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

import {
  IDENTIFIERS,
  KEPT_OUTSIDE,
  LINKAGE_MOVES,
  LOOP_CLOSE,
  LOOP_STAGES,
  WHY_BOTH,
  WITHHELD_CLASS,
} from "./pressIdentity.js";

const read = (relative) => JSON.parse(readFileSync(new URL(relative, import.meta.url), "utf8"));
const register = read("../../../public/data/cedar/register.json");

test("every class an identifier claims is a class the published register holds", () => {
  const codes = new Set(register.classes.map((entry) => entry.code));
  for (const identifier of IDENTIFIERS) {
    assert.ok(identifier.classes.length > 0, `${identifier.id} names no class`);
    for (const code of identifier.classes) {
      assert.ok(codes.has(code), `${identifier.label} claims register class "${code}", which the register does not hold`);
    }
  }
});

test("the role-specific columns are the ones the standard names", () => {
  // The specification of 2026-09-13 names these columns and says the role
  // matters: a recipient column, an owner column and a parent column are not
  // interchangeable, and neither identifier may sit in the other's column.
  const entity = IDENTIFIERS.find((item) => item.id === "entity");
  assert.deepEqual(entity.fields, [
    "native_entity_uid",
    "recipient_native_entity_uid",
    "owner_cedar_uid",
    "parent_cedar_uid",
  ]);
  const business = IDENTIFIERS.find((item) => item.id === "business");
  assert.deepEqual(business.fields, ["business_uid"]);
  // The registry's own keys are external identifiers under the standard, not
  // Cedar identities, so they must not be presented as either id's field.
  const all = IDENTIFIERS.flatMap((item) => item.fields);
  for (const foreign of ["business_source_id", "entity_id", "uei", "cage", "ein"]) {
    assert.ok(!all.includes(foreign), `${foreign} is an external identifier, not a Cedar id`);
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

test("the shapes are the standard's, and the entity sample is a real uid", () => {
  const entity = IDENTIFIERS.find((item) => item.id === "entity");
  // Crockford base32 with I, L, O and U removed: a sample carrying one of
  // those would be teaching a reader an impossible id.
  assert.match(entity.shape, /^CE-[0-9ABCDEFGHJKMNPQRSTVWXYZ]{5}-[0-9ABCDEFGHJKMNPQRSTVWXYZ]{2}$/);
  assert.equal(entity.live, true);
  // And it is a uid the published register actually holds, so the page is
  // never teaching a form by inventing an entity.
  const uids = new Set(register.entities.map((row) => row[0]));
  assert.ok(uids.has(entity.shape), `${entity.shape} is not in the published register`);

  const business = IDENTIFIERS.find((item) => item.id === "business");
  assert.match(business.shape, /^CB-\d{7}$/);
  // SPECIFIED, NOT MINTED. No CB- exists in data/spine, so the section says
  // so in one line. When the terminal mints the register, flip `live` and
  // this assertion with it.
  assert.equal(business.live, false, "business ids are live; update the page's liveness line too");
});

test("the worked example uses the two shapes and keeps them apart", () => {
  assert.equal(WHY_BOTH.entity.id, IDENTIFIERS[0].shape);
  assert.equal(WHY_BOTH.business.id, IDENTIFIERS[1].shape);
  assert.ok(WHY_BOTH.entity.id.startsWith("CE-"));
  assert.ok(WHY_BOTH.business.id.startsWith("CB-"));
  assert.equal(WHY_BOTH.questions.length, 2);
  // The rule the example exists to teach.
  assert.match(WHY_BOTH.close, /never goes in a business column/i);
});

test("what is kept outside the identifiers is named", () => {
  const text = KEPT_OUTSIDE.map((item) => `${item.label} ${item.body}`).join(" ");
  for (const external of ["UEI", "CAGE", "EIN", "NAICS"]) {
    assert.ok(text.includes(external), `${external} is not named as an external identifier`);
  }
  assert.match(text, /effective dates/i, "relationships must carry dates");
  assert.match(text, /source/i, "relationships must carry a source");
});

test("the prose keeps the brand lock", () => {
  const prose = [
    ...IDENTIFIERS.flatMap((item) => [item.names, item.note, ...item.survives]),
    ...KEPT_OUTSIDE.flatMap((item) => [item.label, item.body]),
    ...LINKAGE_MOVES.flatMap((item) => [item.label, item.body]),
    WHY_BOTH.close,
    ...WHY_BOTH.questions,
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
