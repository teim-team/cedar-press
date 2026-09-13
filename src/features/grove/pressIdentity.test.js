// The identity section is the strongest claim the Methods page makes, so every
// class code and every field name in it is checked against the published
// register and the registry schemas. A claim about an identifier is worth
// nothing if the identifier stopped being there.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

import { CONTRACTS } from "./explore.js";
import {
  IDENTIFIERS,
  KEPT_OUTSIDE,
  LINKAGE_COVERAGE,
  UNLINKED_REASONS,
  requireStatus as requireStatusForTest,
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

test("the live columns are columns the exports really carry", () => {
  // Codex, PR #78: the card advertised the specification's role-specific
  // names and not one of them appears in a published table, while `cedar_uid`
  // (on 66 of them) was omitted. The previous version of this test asserted a
  // hand-written list against itself, which is not evidence of anything.
  const shipped = new Set();
  for (const contract of Object.values(CONTRACTS)) {
    if (contract.entity_uid) shipped.add(contract.entity_uid);
    for (const role of contract.entity_roles ?? []) shipped.add(role.column);
  }
  for (const identifier of IDENTIFIERS) {
    for (const field of identifier.fields) {
      assert.ok(shipped.has(field), `${identifier.label} advertises "${field}", which no published contract carries`);
    }
  }
  // The entity id must name the column that is actually on 66 tables.
  assert.ok(IDENTIFIERS[0].fields.includes("cedar_uid"));
  // And the business id has no live column, because nothing mints one.
  assert.deepEqual(IDENTIFIERS[1].fields, []);
});

test("the renaming targets are the ones the specification names", () => {
  const spec = readFileSync(new URL("../../../docs/CEDAR_IDENTITY_SYSTEM_2026-09-13.md", import.meta.url), "utf8");
  const becoming = IDENTIFIERS.flatMap((item) => item.becoming ?? []);
  assert.deepEqual(becoming, [
    "native_entity_uid",
    "recipient_native_entity_uid",
    "owner_cedar_uid",
    "parent_cedar_uid",
    "business_uid",
  ]);
  for (const field of becoming) {
    assert.ok(spec.includes(field), `the specification does not name "${field}"`);
  }
  // A target that has shipped belongs in `fields`, not in `becoming`.
  const shipped = new Set(Object.values(CONTRACTS).flatMap((c) => [c.entity_uid, ...(c.entity_roles ?? []).map((r) => r.column)]));
  for (const field of becoming) {
    assert.ok(!shipped.has(field), `"${field}" has shipped; move it from becoming to fields`);
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
  // Codex, PR #78: the previous version checked only that the uid EXISTS, and
  // the page paired CE-00001-6S with Cherokee Nation while the register binds
  // it to Asa'carsarmiut Tribe. A page arguing that an identifier resolves to
  // one entity, printing one that resolves to another. Check the NAME.
  const byUid = new Map(register.entities.map((row) => [row[0], row[1]]));
  assert.ok(byUid.has(entity.shape), `${entity.shape} is not in the published register`);
  assert.equal(
    byUid.get(entity.shape),
    WHY_BOTH.entity.name,
    `${entity.shape} is not ${WHY_BOTH.entity.name} in the register`,
  );

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
  // The worked example names a real nation by its real uid, checked both ways.
  const byUid = new Map(register.entities.map((row) => [row[0], row[1]]));
  assert.equal(byUid.get(WHY_BOTH.entity.id), WHY_BOTH.entity.name);
  const byName = register.entities.filter((row) => row[1] === WHY_BOTH.entity.name);
  assert.equal(byName.length, 1, `${WHY_BOTH.entity.name} is not unique in the register`);
  assert.equal(byName[0][0], WHY_BOTH.entity.id);
  assert.ok(WHY_BOTH.entity.id.startsWith("CE-"));
  assert.ok(WHY_BOTH.business.id.startsWith("CB-"));
  assert.equal(WHY_BOTH.questions.length, 2);
  // The entity side is a real, checked identifier. The business side is the
  // FORM, because no CB- register exists, and must be marked as such or a
  // reader transcribes it as this enterprise's id. Same error Codex caught on
  // the entity side; the flag has to track the card's liveness.
  const business = IDENTIFIERS.find((item) => item.id === "business");
  assert.equal(WHY_BOTH.business.pending, !business.live);
  assert.ok(!WHY_BOTH.entity.pending, "the entity example is real and checked; it must not be marked provisional");
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

test("the coverage figures are the generated file's, to the digit", () => {
  // Codex, PR #77: the page promised an organization's whole footprint while
  // four collections sit far below the average. The measured figure is on the
  // page now, and it is copied from a generated file, so it is exactly the
  // kind of number that goes stale silently. It does not get to.
  const doc = readFileSync(new URL("../../../docs/LINKAGE_COVERAGE.md", import.meta.url), "utf8");
  const total = doc.match(/([\d,]+) of ([\d,]+) rows \(([\d.]+)%\) carry a resolved Cedar entity/);
  assert.ok(total, "LINKAGE_COVERAGE.md no longer states its headline total in the expected shape");
  const num = (text) => Number(text.replace(/,/g, ""));
  assert.equal(LINKAGE_COVERAGE.linked, num(total[1]));
  assert.equal(LINKAGE_COVERAGE.rows, num(total[2]));
  // Codex, PR #78: comparing two static things stays green while both go
  // stale. The generated file states the date it was measured, so a
  // regeneration moves that date, this fails, and the figures get re-read.
  const measured = doc.match(/Measured (\d{4}-\d{2}-\d{2})/);
  assert.ok(measured, "LINKAGE_COVERAGE.md no longer states when it was measured");
  assert.equal(LINKAGE_COVERAGE.measuredOn, measured[1], "the file was re-measured; re-read its figures");
  // Both named extremes have to still be the extremes, or the page is holding
  // up a spread that has moved.
  const pcts = [...doc.matchAll(/^\| `[^`]+` \| `[^`]+` \|[^|]+\|[^|]+\| ([\d.]+)% \|/gm)].map((m) => Number(m[1]));
  assert.ok(pcts.length >= 10, `expected the per-dataset table, found ${pcts.length} rows`);
  assert.equal(Math.max(...pcts).toFixed(2) + "%", LINKAGE_COVERAGE.best.pct);
  assert.equal(Math.min(...pcts).toFixed(2) + "%", LINKAGE_COVERAGE.worst.pct);
  // And the note the page renders has to carry both, not just the flattering
  // one. Prose writes 100% where the table writes 100.00%, so compare values.
  const inNote = new Set(
    [...LINKAGE_COVERAGE.note.matchAll(/([\d.]+)%/g)].map((m) => Number(m[1])),
  );
  assert.ok(inNote.has(Number(LINKAGE_COVERAGE.best.pct.replace("%", ""))), "the note hides the best figure");
  assert.ok(inNote.has(Number(LINKAGE_COVERAGE.worst.pct.replace("%", ""))), "the note hides the worst figure");
});

test("the business card states the exception rather than overclaiming", () => {
  // Codex, PR #77: the copy said an individually owned firm carries a business
  // id and no entity id, while the register shows that class carrying CE- uids
  // today. The rule is true going forward; the exception is dated and on the
  // page.
  const business = IDENTIFIERS.find((item) => item.id === "business");
  assert.ok(business.exception, "the dated exception is gone; did the 45 lose their uids?");
  const index = register.classes.findIndex((entry) => entry.code === WITHHELD_CLASS);
  const count = register.entities.filter((entity) => entity[2] === index).length;
  assert.equal(count, 45, `the register holds ${count} of that class; the exception says forty-five`);
  assert.match(business.exception, /forty-five/i);
  assert.match(business.exception, /closed to new mints/i);
  // Codex, PR #78: it said those firms HAVE equivalence rows and that every
  // firm resolved from here CARRIES a business id only. Neither register
  // exists. While `live` is false, nothing about a business id may be present
  // tense.
  if (!business.live) {
    assert.match(business.exception, /when the business register is written/i);
    assert.ok(!/\bgain an equivalence row to their business id\b/.test(business.exception));
    assert.ok(!/\bcarries a business id only\b/.test(business.exception), "present tense about an unminted register");
  }
});

test("every rendered link status is the workspace's own definition", () => {
  // Codex, PR #79: the smoke test checked the card COUNT and two phrases that
  // only the intentional statuses contribute, and the module read each body
  // with `?? ""`. Renaming or dropping `unresolved` in scopes.json would have
  // rendered an empty card with every assertion green.
  const scopes = read("../../../data/cedar/scopes.json");
  const defined = scopes.link_statuses ?? {};
  for (const reason of UNLINKED_REASONS) {
    assert.equal(
      reason.body,
      defined[reason.id],
      `${reason.id} is not rendering the definition scopes.json holds for it`,
    );
    assert.ok(reason.body.trim().length > 20, `${reason.id} renders an empty or stub definition`);
    assert.ok(reason.label.trim(), `${reason.id} has no label`);
  }
  // Every state except `resolved` is shown. A new one must be triaged as
  // intentional or not, rather than quietly left off the page.
  assert.deepEqual(
    UNLINKED_REASONS.map((reason) => reason.id).sort(),
    Object.keys(defined).filter((id) => id !== "resolved").sort(),
  );
  assert.deepEqual(
    UNLINKED_REASONS.filter((reason) => reason.intentional).map((reason) => reason.id),
    ["no_individual_named", "withheld"],
  );
});

test("a missing definition is visible rather than blank", () => {
  // The fixture Codex asked for: prove the fallback is a message, not "".
  const missing = requireStatusForTest("this_status_does_not_exist");
  assert.match(missing, /Definition missing/);
  assert.match(missing, /this_status_does_not_exist/);
  assert.ok(missing.length > 20);
});

test("the unlinked split is derived from the generated table, not asserted", () => {
  // Codex, PR #79: the page said the spread was "mostly deliberate", which
  // counted two of three STATUS LABELS and let that stand for the rows. By row
  // it is the other way round, and this recomputes it from the file.
  const doc = readFileSync(new URL("../../../docs/LINKAGE_COVERAGE.md", import.meta.url), "utf8");
  const rows = [...doc.matchAll(/^\| `([a-z-]+)` \| `[^`]+` \| ([\d,]+) \| ([\d,]+) \| [\d.]+% \| ([\d,]+) \| (.+?) \|$/gm)];
  assert.ok(rows.length >= 10, `expected the per-dataset table, found ${rows.length} rows`);
  const num = (text) => Number(text.replace(/,/g, ""));
  let unlinked = 0;
  let measuredUnlinked = 0;
  let structural = 0;
  let measuredFlagships = 0;
  for (const [, , total, , unl, canCol] of rows) {
    unlinked += num(unl);
    // The last column names how many rows can carry an entity at all; the
    // rest of that denominator structurally cannot. Codex, PR #80: it is
    // present for four flagships and `-` for nine, and `-` is NOT MEASURED,
    // not zero. A row without it contributes to `unlinked` and to nothing
    // else — folding it into either side invents a measurement.
    const can = canCol.match(/of ([\d,]+)/);
    if (!can) continue;
    measuredFlagships += 1;
    measuredUnlinked += num(unl);
    structural += num(total) - num(can[1]);
  }
  assert.ok(measuredFlagships > 0 && measuredFlagships < rows.length,
    "the third denominator is now on every flagship or none; the copy assumes a subset");
  assert.equal(LINKAGE_COVERAGE.unlinked, unlinked);
  assert.equal(LINKAGE_COVERAGE.measuredUnlinked, measuredUnlinked);
  assert.equal(LINKAGE_COVERAGE.structural, structural);
  assert.equal(LINKAGE_COVERAGE.unresolved, measuredUnlinked - structural);
  assert.equal(LINKAGE_COVERAGE.unmeasured, unlinked - measuredUnlinked);
  // The two sides account for the measured population and nothing more. This
  // is the assertion that fails if anyone reintroduces the cross-product.
  assert.equal(
    LINKAGE_COVERAGE.structural + LINKAGE_COVERAGE.unresolved,
    LINKAGE_COVERAGE.measuredUnlinked,
    "the split covers rows whose disposition was never measured",
  );
  assert.ok(
    LINKAGE_COVERAGE.unmeasured > 0,
    "every flagship is measured now; say so plainly instead of naming a remainder",
  );
  // The claim the page must not make again: most unlinked rows are NOT
  // intentional. If that ever reverses, this fails and the copy gets rewritten.
  assert.ok(
    LINKAGE_COVERAGE.unresolved > LINKAGE_COVERAGE.structural,
    "most unlinked rows are now structural; the note says the opposite",
  );
  // Every figure the note prints is one of these, and the remainder is named
  // rather than absorbed — the whole point of the correction.
  const comma = (n) => n.toLocaleString("en-US");
  for (const key of ["unlinked", "measuredUnlinked", "structural", "unresolved", "unmeasured"]) {
    assert.ok(
      LINKAGE_COVERAGE.note.includes(comma(LINKAGE_COVERAGE[key])),
      `the note does not print ${key}`,
    );
  }
  assert.ok(
    !LINKAGE_COVERAGE.note.includes(comma(unlinked - structural)),
    "the note still prints the cross-product figure",
  );
  assert.ok(!/mostly deliberate|mostly intentional/i.test(LINKAGE_COVERAGE.note));
  assert.ok(LINKAGE_COVERAGE.note.includes(LINKAGE_COVERAGE.mostlyStructural.share));
  assert.ok(LINKAGE_COVERAGE.note.includes(LINKAGE_COVERAGE.mostlyUnresolved.share));
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
