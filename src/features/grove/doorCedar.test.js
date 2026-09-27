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

// ── The conversation around the bank ──────────────────────────────────────
// The door used to answer without memory: "tell me more" was refused, the
// same question twice printed the same paragraph, and every miss was one
// fixed sentence. These pin the behaviours the shared runtime gives it.

import { beginTurn, detectAudience, freshThread, settleTurn } from "./cedarConversation.js";
import {
  DOOR_AUDIENCES,
  NON_TOPIC_IDS,
  OUT_OF_SCOPE_TRIGGERS,
  doorFollowUps,
  doorMatcher,
  missAnswer,
  resolveDoor,
} from "./doorCedar.js";

function door() {
  let thread = freshThread();
  return {
    get memory() {
      return thread.memory;
    },
    say(question, options = {}) {
      const resolution = resolveDoor(thread.memory, question, options);
      thread = settleTurn(beginTurn(thread, question), resolution, {
        nonTopicIds: NON_TOPIC_IDS,
        audience: detectAudience(DOOR_AUDIENCES, question),
        followUpsFor: doorFollowUps,
      });
      return { ...resolution, chips: thread.followUps.map((c) => c.label) };
    },
  };
}

test("every topic has a deeper answer for tell me more, and none of it breaks the house style", () => {
  for (const intent of DOOR_INTENTS) {
    if (intent.chip) assert.ok(intent.expanded?.length > 80, `${intent.id} has no deeper answer`);
    for (const raw of [intent.answer, intent.expanded ?? "", intent.chip ?? "", ...(intent.variants ?? [])]) {
      // The one named exemption: the collection's own name, which the owner
      // keeps with its ampersand. Nothing else may carry one.
      const text = raw.replaceAll("Foundation & Corporate Giving", "");
      assert.ok(!text.includes("—"), `em dash in ${intent.id}`);
      assert.ok(!/&amp;|[A-Za-z0-9] & [A-Za-z0-9]/.test(text), `ampersand in ${intent.id}`);
      assert.ok(!/prepared (set|material|answers)/i.test(text), `${intent.id} announces its machinery`);
    }
  }
});

test("tell me more after a collection goes deeper on that collection", () => {
  const c = door();
  const first = c.say("what is in the deals collection");
  assert.equal(first.intent.id, "collection:deals");
  assert.equal(first.chips[0], "Tell me more");
  const more = c.say("tell me more");
  assert.equal(more.kind, "drilldown");
  assert.equal(more.intent.id, "collection:deals");
  assert.match(more.text, /^Going deeper on how Deals is built/);
  assert.ok(!more.chips.includes("Tell me more"));
});

test("the same question twice is answered deeper, then acknowledged, never verbatim", () => {
  const c = door();
  const first = c.say("How current is it?");
  const second = c.say("How current is it?");
  const third = c.say("How current is it?");
  assert.equal(second.kind, "repeat");
  assert.match(second.text, /^We touched on this earlier/);
  assert.notEqual(second.text, first.text);
  assert.notEqual(third.text, second.text);
  assert.ok(third.text.endsWith(first.text), "the restatement still carries the answer");
});

test("a question naming two topics answers one and offers the other first", () => {
  const c = door();
  const r = c.say("how much does it cost and how current is it");
  assert.equal(r.intent.id, "plans");
  assert.equal(r.secondary?.id, "current");
  assert.equal(r.chips[0], "How current is it?");
  const two = door().say("deals or funding");
  assert.equal(two.intent.id, "collection:funding");
  assert.equal(two.chips[0], "Deals");
});

test("a typo still reaches the collection", () => {
  assert.equal(door().say("legislaton").intent.id, "collection:legislation");
  assert.equal(answer("repatriaton").id, "collection:nagpra");
});

test("a miss says so, offers the closest topics, and after a second miss names the research desk", () => {
  const c = door();
  const first = c.say("what is the weather in Oslo");
  assert.equal(first.kind, "miss");
  assert.match(first.text, /I do not have that one here on the front page/);
  assert.match(first.text, /closest things I can speak to/);
  assert.doesNotMatch(first.text, /contact@lumecon\.ai/);
  assert.ok(first.chips.length >= 1 && first.chips.length <= 3);
  const second = c.say("banana bread");
  assert.match(second.text, /research desk answers in person: contact@lumecon\.ai/);
  assert.equal(c.memory.misses, 2);
  assert.equal(missAnswer("x", [], false), missAnswer("x"));
});

test("who is the president is a miss, not a match on the word who", () => {
  assert.equal(door().say("who is the president of mexico").kind, "miss");
  assert.ok(OUT_OF_SCOPE_TRIGGERS.includes("who is the president"));
});

test("a reader who says who they are gets their own route in as a quick reply", () => {
  const c = door();
  const r = c.say("for my story, what is in the legislation collection");
  assert.equal(r.intent.id, "collection:legislation");
  assert.equal(c.memory.audience, "research");
  assert.ok(c.say("federal funding").chips.includes("I'm a researcher or journalist"));
});

test("filler is never the last topic, and greetings do not repeat verbatim", () => {
  const c = door();
  c.say("what is nagpra");
  const hello = c.say("hi");
  const again = c.say("hi");
  assert.notEqual(hello.text, again.text);
  assert.equal(c.memory.priorTopicId, "collection:nagpra");
  assert.equal(c.say("yes").kind, "drilldown");
});

test("every collection is reachable by its chip, its id and its extra words", () => {
  for (const entry of STOREFRONT_CATALOG) {
    const intent = intentForCollection(entry.id);
    assert.equal(doorMatcher.classify(entry.id.replace(/-/g, " "))?.id, intent.id, entry.id);
    assert.equal(doorMatcher.classify(`what is in ${entry.short || entry.name}`)?.id, intent.id, entry.id);
  }
  assert.equal(doorMatcher.classify("do you track royalties")?.id, "collection:natural-resources");
  assert.equal(doorMatcher.classify("form 990 filings")?.id, "collection:nonprofits");
});

// ── The door as the product now ships (owner, 2026-09-27) ─────────────────
// Fourteen collections, seven on each plan, Foundation & Corporate Giving
// and PLOT live like the rest; no gaming anywhere; the twelve landing
// audiences with their outcomes; and nothing claimed that the collections
// cannot back.

import { AUDIENCE_JOBS, visibleAudiences } from "./pressJobs.js";
import { PRESS_TIERS, spellCount } from "./pressCatalog.js";
import { recordStructure } from "./pressRecordStructure.js";

/** Every string a door answer can show a visitor. */
const everything = () =>
  DOOR_INTENTS.flatMap((intent) => [intent.answer, intent.expanded ?? "", intent.chip ?? "", ...(intent.variants ?? [])]);

test("routing: foundations and philanthropy reach the audience, and giving questions the collection", () => {
  assert.equal(classify("Foundations and philanthropy")?.id, "audience:foundations-philanthropy");
  assert.equal(classify("I work at a foundation")?.id, "audience:foundations-philanthropy");
  assert.equal(classify("which foundations fund tribes")?.id, "collection:foundation-corporate-giving");
  assert.equal(classify("corporate giving to tribes")?.id, "collection:foundation-corporate-giving");
  assert.equal(classify("philanthropy")?.id, "collection:foundation-corporate-giving");
});

test("routing: land, parcels and permits reach PLOT", () => {
  for (const question of ["land ownership records", "who owns these parcels", "do you track building permits", "parcel data", "property records"]) {
    assert.equal(classify(question)?.id, "collection:plot", question);
  }
});

test("routing: the renamed audience answers to consultants and advisors", () => {
  for (const question of ["Consultants and advisors", "I am a consultant", "we are an advisory firm", "research for my clients", "professional services"]) {
    assert.equal(classify(question)?.id, "audience:advisors", question);
  }
});

test("routing: the new audience answers to government and public agency officials", () => {
  for (const question of ["Government and public agency officials", "I work for a federal agency", "state government", "we are a county government", "preparing a tribal consultation", "government-to-government relationships"]) {
    assert.equal(classify(question)?.id, "audience:government-officials", question);
  }
});

test("routing: a tribal government still reaches its own free-access answer, and Tribal Nations its audience", () => {
  assert.equal(classify("I work for a tribal government")?.id, "tribal");
  assert.equal(classify("can our nation review our records")?.id, "tribal");
  assert.equal(classify("Tribal Nations")?.id, "audience:tribal-nations");
  const tribal = DOOR_INTENTS.find((intent) => intent.id === "tribal");
  assert.match(tribal.answer, /^Federally recognized tribal governments can request and review the Cedar records associated with their nation\. No subscription is required\./);
});

test("the audience answers are the landing's twelve, with their outcomes, counted from the layer", () => {
  const shown = visibleAudiences();
  assert.equal(shown.length, AUDIENCE_JOBS.length);
  const list = DOOR_INTENTS.find((intent) => intent.id === "audiences");
  assert.ok(list.answer.startsWith(`Cedar Press is built for ${spellCount(shown.length)} audiences`), list.answer.slice(0, 60));
  for (const audience of shown) {
    assert.ok(list.answer.includes(`${audience.audience}: ${audience.outcome}`), `${audience.id} is missing from "Who is it for?"`);
    const own = DOOR_INTENTS.find((intent) => intent.id === `audience:${audience.id}`);
    assert.ok(own, `${audience.id} has no answer of its own`);
    assert.ok(own.answer.includes(audience.outcome), `${audience.id}: the outcome is not the owner's`);
    assert.ok(own.answer.includes(audience.explanation), `${audience.id}: the explanation is not the owner's`);
    for (const entry of audience.collections) assert.ok(own.answer.includes(entry.short || entry.name), `${audience.id} omits ${entry.id}`);
  }
  assert.doesNotMatch(list.answer, /Advisors and professional services/);
});

test("consultants are told it is research, not a contact database", () => {
  const advisors = DOOR_INTENTS.find((intent) => intent.id === "audience:advisors");
  assert.match(advisors.answer, /not a contact database/);
  // No line anywhere offers contacts, leads or outreach lists.
  for (const text of everything()) {
    const offered = text.replace(/no contact lists, leads lists or outreach lists|no contact or outreach lists|supply contact lists|not a contact database/g, "");
    assert.doesNotMatch(offered, /contact (list|database)|leads? lists?|outreach lists?/i, text.slice(0, 80));
  }
});

test("government officials are told Cedar supports consultation and never replaces engaging Native nations", () => {
  const government = DOOR_INTENTS.find((intent) => intent.id === "audience:government-officials");
  assert.match(government.answer, /supports consultation and government-to-government relationships/);
  assert.match(government.answer, /does not replace direct engagement with Native nations/);
  for (const text of everything()) {
    const claimed = text.replace(/does not replace direct engagement|stand in for engaging/g, "");
    assert.doesNotMatch(claimed, /(replaces?|instead of|substitute for|stands? in for) (direct )?(engagement|consultation|engaging)/i, text.slice(0, 80));
  }
});

test("no answer claims a need score or a cause", () => {
  for (const text of everything()) {
    const claimed = text.replace(/not a need score|no need scores|score need/g, "");
    assert.doesNotMatch(claimed, /need score|need index|most in need/i, text.slice(0, 80));
    const causal = text.replace(/no claim that one thing caused another/g, "");
    assert.doesNotMatch(causal, /\b(caused|causes|led to|resulted in|because of)\b/i, text.slice(0, 80));
  }
});

test("no gaming collection or gaming source remains in any door answer", () => {
  for (const text of everything()) assert.doesNotMatch(text, /gaming|casino|NIGC/i, text.slice(0, 80));
  for (const intent of DOOR_INTENTS) {
    for (const trigger of intent.triggers ?? []) assert.doesNotMatch(trigger, /gaming|casino/i, intent.id);
  }
  assert.equal(answer("tell me about the gaming collection").id, DOOR_FALLBACK.id);
});

test("both new collections are described like the rest, with no figure and no 'not yet published'", () => {
  for (const id of ["plot", "foundation-corporate-giving"]) {
    const intent = intentForCollection(id);
    const entry = STOREFRONT_CATALOG.find((item) => item.id === id);
    for (const text of [intent.answer, intent.expanded]) {
      assert.doesNotMatch(text, /not yet published|first release|pending|preparation/i, id);
      assert.doesNotMatch(text, /\d/, `${id} states a figure`);
    }
    assert.ok(intent.answer.includes(entry.blurb), `${id}: what it contains`);
    assert.ok(intent.answer.includes(recordStructure(id).summary), `${id}: what each record holds`);
    // How it connects to the other collections, in the owner's Methods words.
    assert.match(intent.answer, id === "plot" ? /Indian Country Deals links to the parcels PLOT follows/ : /beside federal funding and the Native Nonprofits roster/);
  }
  for (const text of everything()) assert.doesNotMatch(text, /not yet published|with (its|their) first release/i, text.slice(0, 80));
});

test("collections and plans are counted from the catalog: fourteen, seven on each plan", () => {
  const collections = DOOR_INTENTS.find((intent) => intent.id === "collections");
  assert.ok(collections.answer.startsWith(`${STOREFRONT_CATALOG.length} collections, on two shelves.`));
  const plans = DOOR_INTENTS.find((intent) => intent.id === "plans");
  for (const tier of PRESS_TIERS.filter((t) => t.storefront)) {
    const count = STOREFRONT_CATALOG.filter((entry) => entry.shelf === tier.shelf).length;
    assert.ok(plans.answer.includes(`${count}`), `${tier.name}: ${count}`);
  }
  for (const id of ["plot", "foundation-corporate-giving"]) {
    assert.ok(collections.answer.includes(STOREFRONT_CATALOG.find((entry) => entry.id === id).short), id);
  }
});

test("who made it reads the same way everywhere the door says it", () => {
  const who = DOOR_INTENTS.find((intent) => intent.id === "who");
  assert.match(who.answer, /^Cedar Press is built by Lumecon in partnership with Tribal Business News/);
  for (const text of everything()) {
    assert.doesNotMatch(text, /distributed exclusively through|built by Lumecon and/i, text.slice(0, 80));
    if (/built by Lumecon/i.test(text)) assert.match(text, /built by Lumecon in partnership with Tribal Business News/i);
  }
});

test("maintenance and Cedar NEED's enrichments: door Cedar says weekly, and keeps each record with its entity", () => {
  const current = DOOR_INTENTS.find((intent) => intent.id === "current");
  assert.match(current.answer, /maintains its datasets weekly with human review/);
  assert.match(current.expanded, /exceptionally useful, well-documented data and tools/);
  assert.equal(classify("do you have patents")?.id, "collection:need");
  assert.equal(classify("credit ratings for tribal enterprises")?.id, "collection:need");
  const need = intentForCollection("need").answer;
  assert.match(need, /later acquired/);
  assert.match(need, /never presented as its parent's/);
  const sources = DOOR_INTENTS.find((intent) => intent.id === "sources").answer;
  assert.match(sources, /patent records, supported by company, tribal, SEC and court evidence/);
  assert.match(sources, /rating-agency announcements, supported by issuer and tribal releases, filings, regulator records and labeled secondary sources/);
  for (const text of everything()) assert.doesNotMatch(text, /updated (monthly|quarterly|annually)|every quarter/i, text.slice(0, 60));
});

test("institutional accounts: team and organization questions reach their own answer, never plans", () => {
  const phrasings = [
    "can my team share an account",
    "is there an institutional plan",
    "we have multiple users",
    "do you offer an organization account",
    "how do I invite colleagues",
    "who is the admin for our account",
    "how much is the institutional plan",
  ];
  for (const question of phrasings) {
    const id = classify(question)?.id;
    assert.equal(id, "institutional", question);
    assert.notEqual(id, "plans", question);
  }
  const intent = DOOR_INTENTS.find((item) => item.id === "institutional");
  assert.match(intent.answer, /Cedar Press and Cedar Press\+ are individual plans, one person each/);
  assert.match(intent.answer, /admin invites colleagues by email/);
  assert.match(intent.answer, /share the organization's details and its Cedar context/);
  assert.match(intent.answer, /own sign-in/);
  assert.match(intent.answer, /teammates do not see each other's conversations/);
  assert.match(intent.answer, /loses that access at once and keeps anything they hold individually/);
  assert.match(intent.answer, /elijah\.moreno@lumecon\.ai/);
  for (const text of [intent.answer, intent.expanded]) {
    assert.doesNotMatch(text, /\bseats?\b|\$|\bprice|\bcost|per user|up to \d/i, text.slice(0, 60));
  }
  assert.equal(classify("can we do collaborative analysis")?.id, "collaboration");
  assert.match(DOOR_INTENTS.find((item) => item.id === "collaboration").answer, /Cedar Grove, not Cedar Press/);
});
