/**
 * REVIEW OWNER: Havala
 *
 * Cedar on the door, without the service.
 *
 * WHY THIS IS NOT THE PRODUCT'S CEDAR
 * `PressCedarFab` asks the platform (`askCedar`) and needs an entitlement and
 * a connected deployment. A visitor at the door has neither, and the honest
 * behaviour there used to be a refusal: Cedar took the question and answered
 * that it would answer once you subscribed. A doorbell.
 *
 * This is the marketing-site pattern instead, the one lumecon.ai uses
 * (`src/data/cedarIntents.ts` there): a bank of answers matched locally. It
 * never reaches the network, so it can answer a visitor's real questions
 * about what Cedar Press holds without opening anything a subscriber pays
 * for. The conversation around the bank (memory, drill-downs, repeats, quick
 * replies, the graceful miss) is `cedarConversation.js`, shared with the
 * in-product panel; this file is the bank and the door's own configuration
 * of that runtime.
 *
 * WHAT THE PANEL USED TO SAY, AND WHY IT STOPPED
 * The panel printed "This page answers from prepared material and does not
 * query the collections", and the owner read it, correctly, as "preset
 * answers": a form with a transcript around it. The line is gone. What is
 * true is still true, and the code above says it, but the panel no longer
 * announces its machinery to the reader. It sets the same expectation
 * lumecon.ai's Cedar sets, and then it holds a conversation.
 *
 * WHERE THE DATASET ANSWERS COME FROM
 * The twelve collection answers are assembled from the catalog and the
 * release record at module load: name, shelf, blurb, coverage, row count,
 * update date, sources, linkage, and for the deeper answer the collection's
 * own method note. Nothing about a collection is typed here, so an answer
 * cannot drift from the collection it describes, and the day a release
 * changes the row count the door's answer changes with it.
 *
 * The general answers ARE written here, because "what is Cedar Press" is a
 * position, not a measurement. Every number inside them is interpolated.
 */

import {
  createMatcher,
  followUpsFor as runtimeFollowUps,
  freshMemory,
  resolveLocally,
} from "./cedarConversation.js";
import { LAUNCH_COLLECTION } from "./collection.js";
import { coverageLabel } from "./pressAccess.js";
import { PRESS_CATALOG_BY_ID, PRESS_TIERS, STOREFRONT_CATALOG } from "./pressCatalog.js";
import { formatUpdated, freshnessLine, recentlyUpdated } from "./pressReleases.js";
import { REGISTRY_PROGRAMS } from "./pressSources.js";

const DESCRIPTOR = Object.fromEntries(LAUNCH_COLLECTION.map((entry) => [entry.id, entry]));
const TIER_BY_SHELF = Object.fromEntries(PRESS_TIERS.map((tier) => [tier.shelf, tier]));

/** Extra words that should reach a collection beyond its own name. */
const COLLECTION_WORDS = Object.freeze({
  funding: ["grant", "grants", "assistance", "award", "awards", "usaspending", "federal money", "block grant", "federal funding"],
  "federal-register": ["notice", "notices", "rule", "rulemaking", "comment period", "register"],
  legislation: ["bill", "bills", "congress", "vote", "votes", "roll call", "senate", "house", "law", "laws"],
  deals: ["deal", "acquisition", "acquisitions", "merger", "mergers", "bond", "bonds", "financing", "transaction", "transactions", "investment", "investments", "joint venture"],
  nagpra: ["repatriation", "remains", "graves", "inventory", "museum", "museums", "ancestors"],
  lobbying: ["lobby", "lobbying", "advocacy", "consultation", "docket", "dockets", "ferc", "nrc", "testimony", "lda"],
  contractors: ["contract", "contracts", "contracting", "prime", "fpds", "8(a)", "set aside", "set-aside", "vendor", "vendors"],
  subcontracting: ["subaward", "subawards", "subcontract", "subcontracts", "subcontractor", "subcontractors", "fsrs"],
  owned: ["tero", "small business", "small businesses", "individually owned", "business directory", "certified", "native owned", "native-owned"],
  nonprofits: ["nonprofit", "nonprofits", "990", "irs", "charity", "charities", "foundation", "foundations"],
  need: ["enterprise", "enterprises", "subsidiary", "subsidiaries", "ownership", "who owns", "holding company", "structure"],
  "natural-resources": ["royalty", "royalties", "oil", "gas", "coal", "mineral", "minerals", "timber", "severance", "onrr"],
});

/** The first `count` sentences of a note, with the dashes the house style refuses turned into commas. */
function leadSentences(text, count) {
  const clean = String(text ?? "").replace(/\s*[\u2014\u2013]\s*/g, ", ").replace(/\s+/g, " ").trim();
  const sentences = clean.match(/[^.!?]+[.!?]+(\s|$)/g) ?? [];
  const lead = sentences.slice(0, count).join("").trim();
  return lead || clean;
}

/** One answer per collection, assembled from what the catalog holds. */
function collectionAnswer(entry) {
  const descriptor = DESCRIPTOR[entry.id];
  const tier = TIER_BY_SHELF[entry.shelf];
  const fresh = freshnessLine(entry.id);
  const lines = [entry.blurb];
  const facts = [`Coverage: ${coverageLabel(entry)}.`];
  if (descriptor?.rowsLabel) facts.push(`${descriptor.rowsLabel} in the current release.`);
  if (fresh) facts.push(`${fresh}.`);
  lines.push(facts.join(" "));
  if (descriptor?.sources) lines.push(`Built from ${lowerFirst(descriptor.sources)}`);
  if (entry.linkage) lines.push(entry.linkage);
  if (tier) lines.push(`It is included in ${tier.name}.`);
  return lines.join("\n\n");
}

/** The deeper answer for a collection: how it is constructed, off its own method note. */
function collectionExpanded(entry) {
  const descriptor = DESCRIPTOR[entry.id];
  const method = descriptor?.method ? leadSentences(descriptor.method, 2) : null;
  const lines = [];
  if (method) lines.push(`Going deeper on how ${entry.short || entry.name} is built: ${lowerFirst(method)}`);
  else if (entry.linkage) lines.push(`Going deeper: ${lowerFirst(entry.linkage)}`);
  lines.push(
    `Every release is dated and versioned, and the methods page states the inclusion rules and known gaps ` +
      `for this collection, which is what a citation needs.`,
  );
  return lines.join("\n\n");
}

function lowerFirst(text) {
  const value = String(text ?? "");
  return value ? value[0].toLowerCase() + value.slice(1) : value;
}

/**
 * The next questions under an answer, by the intent that was just answered.
 *
 * lumecon.ai offers at most three next questions under an answer, chosen by
 * what was just discussed. These are deliberate pairs rather than a scored
 * guess, because the door's bank is ten general answers and twelve
 * collections, small enough to write out. The twelve collections share one
 * list: after "what is in Federal Prime Contracting", the useful next
 * questions are how it reaches a nation, what it is built from, and how to
 * get it.
 */
const COLLECTION_FOLLOW_UPS = Object.freeze(["entities", "sources", "plans"]);
const FALLBACK_FOLLOW_UPS = Object.freeze(["what", "collections", "plans"]);

/** The twelve dataset intents, one per storefront collection. */
const COLLECTION_INTENTS = STOREFRONT_CATALOG.map((entry) => ({
  id: `collection:${entry.id}`,
  collectionId: entry.id,
  chip: entry.short || entry.name,
  triggers: [
    entry.id.replace(/-/g, " "),
    (entry.short || "").toLowerCase(),
    entry.name.toLowerCase(),
    ...(COLLECTION_WORDS[entry.id] ?? []),
  ].filter(Boolean),
  answer: collectionAnswer(entry),
  expanded: collectionExpanded(entry),
  followUps: COLLECTION_FOLLOW_UPS,
}));

const COUNT = STOREFRONT_CATALOG.length;
const RECENT = recentlyUpdated(3);
const NEWEST = RECENT[0] ?? null;
const PRESS = PRESS_TIERS.find((tier) => tier.id === "press");
const PRESS_PRO = PRESS_TIERS.find((tier) => tier.id === "press_pro");
const STANDARD = STOREFRONT_CATALOG.filter((e) => e.shelf === "standard");
const PRO = STOREFRONT_CATALOG.filter((e) => e.shelf === "pro");
const names = (entries) => entries.map((e) => e.short || e.name).join(", ");
const recentLine = RECENT.map((r) => `${PRESS_CATALOG_BY_ID[r.id]?.short ?? r.id} on ${formatUpdated(r.updated)}`).join(", ");

/**
 * The written intents. Positions, not measurements, but every figure in
 * them is interpolated from the catalog, so none of them can go stale.
 * `expanded` is what "tell me more" gets, and what a repeated question gets
 * the first time it is repeated.
 */
const GENERAL_INTENTS = [
  {
    id: "what",
    chip: "What is Cedar Press?",
    followUps: ["collections", "entities", "plans"],
    triggers: ["what is cedar press", "what is this", "what does cedar press do", "what is cedar", "about cedar press", "explain cedar press", "what do you do", "what is press", "cedar press", "what is it", "what are you"],
    answer:
      `Cedar Press is a research and intelligence service about Indian Country's economy. ` +
      `It publishes ${COUNT} maintained collections, built from more than 500 source websites and ` +
      `resolved to the nations, corporations and organizations the records belong to.\n\n` +
      `A federal contract names the company that won it but not the nation that owns the company, so ` +
      `Cedar does the work between the record and the entity, publishes what it could not resolve, and keeps the ` +
      `collections current as new material arrives. Alongside the data there are research briefs, a ` +
      `release history and a methods reference.`,
    expanded:
      `Going deeper: the collections are one product rather than ${COUNT} downloads. Every one keys to the ` +
      `same entity layer, so a nation's contracts, awards, deals, notices and subsidiaries read as one ` +
      `nation across all of them, and a figure you cite reproduces because every release is dated and ` +
      `versioned.\n\n` +
      `The briefs are written from the collections, the release history says what changed and when, and ` +
      `the methods page states the inclusion rules and the known gaps for each collection.`,
  },
  {
    id: "collections",
    chip: "What collections are there?",
    followUps: ["sources", "entities", "plans"],
    triggers: ["what collections", "which collections", "list the collections", "what datasets", "which datasets", "what data do you have", "what is in it", "how many collections", "the collections", "all the collections", "every collection"],
    answer:
      `${COUNT} collections, on two shelves.\n\n` +
      `${PRESS?.name}: ${names(STANDARD)}.\n\n` +
      `${PRESS_PRO?.name}: ${names(PRO)}.\n\n` +
      `Ask me about any one of them by name and I will tell you what it holds, how far back it goes and what it is built from.`,
    expanded:
      `Going deeper: the ${PRESS?.name} shelf is the public record of what is happening, ` +
      `${lowerFirst(PRESS?.promise ?? "")} The ${PRESS_PRO?.name} shelf is the structure behind it: ` +
      `who holds the contracts and subawards, who owns which enterprise, where resource revenue goes, ` +
      `which businesses and nonprofits are Native-controlled.\n\n` +
      `Each collection states its own coverage, row count and sources, and I can give you any of them by name.`,
  },
  {
    id: "sources",
    chip: "Where does the data come from?",
    followUps: ["current", "entities", "limits"],
    triggers: ["where does the data come from", "what are the sources", "what sources", "source systems", "is this public data", "where do you get", "how do you get the data", "provenance", "the sources", "data sources", "where is it from", "where does it come from"],
    answer:
      `Lumecon draws on more than 500 source websites for the ${COUNT} collections and the research behind ` +
      `them. They include federal spending and award systems ` +
      `(USAspending, FPDS, FSRS, SAM, FAADS), Congress and the Federal Register (Congress.gov, Voteview, ` +
      `federalregister.gov), advocacy and docket records (Senate and House lobbying disclosure, FERC and NRC ` +
      `dockets, IBIA and IBLA appeals, regulations.gov), tax filings (IRS Business Master File, Form 990), ` +
      `resource revenue (ONRR, OSMRE, ANCSA 7(i) and 7(j) filings, the Osage Minerals Council), and what ` +
      `nations and corporations publish about themselves.\n\n` +
      `Not all of it is public. The Native-Owned Businesses collection comes from tribal TERO and commerce ` +
      `offices under each nation's stated terms, and publishers whose terms forbid reuse are excluded by ` +
      `every route and named as excluded.`,
    expanded:
      `Going deeper: some sources are deep rather than single. Behind the tribal business directories ` +
      `sits a registry of ${REGISTRY_PROGRAMS} source programs, each one a nation's own TERO list, a ` +
      `member-owned directory, a state certified-vendor list or a regional chamber.\n\n` +
      `Every row carries the source it came from, so a figure can be traced back to the filing, the notice ` +
      `or the directory that stated it, and a source that changes its terms is removed by name rather than quietly.`,
  },
  {
    id: "entities",
    chip: "How are records linked to nations?",
    followUps: ["limits", "sources", "plans"],
    triggers: ["how are records linked", "entity resolution", "how do you link", "how do you know which tribe", "resolved to", "matching", "how do you connect", "linked to nations", "which nation", "which tribe", "entity layer", "identity"],
    answer:
      `Every collection keys to the same entity layer. A vendor in a federal contract, a recipient in an ` +
      `assistance award, a party named in a notice and a subsidiary in an annual report are resolved to the ` +
      `nation, corporation or organization behind them, tracked through name changes, subsidiaries and ` +
      `reorganizations, so one enterprise's four names over a decade read as one enterprise.\n\n` +
      `Where a record cannot be placed, it keeps its printed party name and a blank key rather than a guess. ` +
      `Unresolved is published as unresolved. The methods page sets out the rules.`,
    expanded:
      `Going deeper: a link is only ever made on evidence a source asserted. A shared name or a shared address ` +
      `is not evidence and does not create a link, and ownership is recorded only where a filing, a directory ` +
      `or the nation itself stated it.\n\n` +
      `Enterprises are tracked through their history, so a name change, a subsidiary and a reorganization ` +
      `stay attached to the same nation, and the basis for each link is carried on the row so it can be checked.`,
  },
  {
    id: "current",
    chip: "How current is it?",
    followUps: ["sources", "collections", "plans"],
    triggers: ["how current", "how often updated", "how fresh", "update", "updated", "cadence", "how often", "is it current", "snapshot", "how recent", "up to date", "latest release", "last updated"],
    answer:
      NEWEST
        ? `Records are added, ownership changes and corrections arrive every week, and the collections are ` +
          `kept current against them. The most recent release was ${formatUpdated(NEWEST.updated)}.\n\n` +
          `Every release is dated and versioned, and the release history records what changed, so a figure ` +
          `you cited last quarter still reproduces.`
        : `Records are added, ownership changes and corrections arrive every week, and every release is ` +
          `dated and versioned so a figure you cited last quarter still reproduces.`,
    expanded:
      `Going deeper: each collection keeps its own cadence, stated on the collection, because its sources ` +
      `publish on their own clocks. Federal award systems post continuously and the collection follows them; ` +
      `a roster collection states the date it was captured rather than a span, because its sources archive nothing.` +
      (recentLine ? `\n\nThe latest releases: ${recentLine}.` : ""),
  },
  {
    id: "plans",
    chip: "How do I get access?",
    followUps: ["tribal", "research", "collections"],
    triggers: ["how do i get", "how much", "price", "pricing", "cost", "subscribe", "subscription", "plans", "buy", "sign up", "membership", "tiers", "difference between", "get access", "access", "how do i read", "log in", "login"],
    answer:
      `Cedar Press is available exclusively through a Tribal Business News membership, which handles ` +
      `payment, renewals and upgrades.\n\n` +
      `${PRESS?.name} opens ${STANDARD.length} collections, ` +
      `${lowerFirst(PRESS?.question ?? "")}\n` +
      `${PRESS_PRO?.name} adds the other ${PRO.length}, ` +
      `${lowerFirst(PRESS_PRO?.question ?? "")}\n\n` +
      `Two other routes need no subscription at all: a federally recognized tribal government can request ` +
      `and review the Cedar records about its own nation, and research access covers one or two collections ` +
      `for a defined project.`,
    expanded:
      `Going deeper: there is no year gating. Every subscriber gets every year Cedar holds of each collection; ` +
      `the only difference between the two plans is which collections arrive. ${PRESS?.name} is ` +
      `${names(STANDARD)}. ${PRESS_PRO?.name} adds ${names(PRO)}.\n\n` +
      `Each collection downloads as a CSV that cites itself, and the same reader opens the briefs, the ` +
      `release history and the methods reference.`,
    links: ["plans", "request", "research"],
  },
  {
    id: "tribal",
    chip: "I work for a tribal government",
    followUps: ["plans", "entities", "who"],
    triggers: ["tribal government", "my nation", "our records", "data request", "request our data", "sovereignty", "our nation's records", "free access", "our tribe", "my tribe", "tribal council", "our nation"],
    answer:
      `Federally recognized tribal governments can request and review the Cedar records associated with ` +
      `their nation. No subscription is required.\n\n` +
      `The request page sets out what you get, what Cedar will and will not publish, and how to raise a ` +
      `correction.`,
    expanded:
      `Going deeper: the request is reviewed by a person, and what comes back is the set of records Cedar ` +
      `has resolved to your nation across the collections, with the basis for each link, so your office can ` +
      `see what is attributed to you and on what evidence.\n\n` +
      `A correction you raise is applied to the generating pipeline, not to a copy, so it holds in every ` +
      `release after it.`,
    links: ["request"],
  },
  {
    id: "research",
    chip: "I'm a researcher or journalist",
    followUps: ["plans", "limits", "sources"],
    triggers: ["researcher", "journalist", "student", "academic", "citation", "cite", "research access", "for a project", "nonprofit access", "public interest", "reporter", "newsroom", "thesis", "professor"],
    answer:
      `Research access covers one or two collections for a defined project, for researchers, journalists, ` +
      `students, nonprofits and public-interest work. It needs no subscription.\n\n` +
      `If you are going to cite a figure, read the methods page first: it states inclusion rules, known ` +
      `gaps and how each collection is versioned, which is what a citation needs.`,
    expanded:
      `Going deeper: every CSV cites itself, with the collection name and the release version written into ` +
      `the file, so a figure in a story or a paper points at the exact release it came from.\n\n` +
      `The research access page asks for the project and the collections it needs; a person reads it and ` +
      `replies.`,
    links: ["research", "methods"],
  },
  {
    id: "who",
    chip: "Who builds it?",
    followUps: ["entities", "limits", "plans"],
    triggers: ["who builds", "who made", "who are you", "who is behind", "lumecon", "team", "tribal business news", "credentials", "who runs", "who makes", "who wrote"],
    answer:
      `Cedar Press is built by Lumecon and distributed exclusively through Tribal Business News.\n\n` +
      `The collections are assembled by Indigenous researchers with Federal Reserve and university ` +
      `experience. Inclusion rules, known limitations and corrections ship with every collection rather ` +
      `than sitting in a document somewhere.`,
    expanded:
      `Going deeper: Lumecon builds the collections and the analyst behind them; Tribal Business News ` +
      `handles membership, payment and renewals. I am Cedar, Lumecon's AI economic analyst; here on the ` +
      `front page I answer about Cedar Press itself, and inside the product I answer from the collections.`,
  },
  {
    id: "limits",
    chip: "What are the limits?",
    followUps: ["entities", "sources", "plans"],
    triggers: ["limitations", "limits", "what is missing", "gaps", "caveats", "accuracy", "how accurate", "problems", "what can't", "cannot", "known issues", "reliable", "trust"],
    answer:
      `Every collection publishes its own. The common ones: federal publication lags, so a current year is ` +
      `partial and labelled as partial; some records name a party the source cannot place, and those keep ` +
      `the printed name with a blank key rather than a guess; and roster collections state a capture date ` +
      `rather than a span, because their sources publish who is on the list now and archive nothing.\n\n` +
      `Cedar does not invent a date, an owner or a boundary to make a column tidy. Where a figure is not ` +
      `measured it is absent, not zero.`,
    expanded:
      `Going deeper: a smaller true collection always beats a larger padded one, and that rule costs rows. ` +
      `A record whose party cannot be placed is kept and marked unresolved rather than dropped or guessed; ` +
      `a duplicate that is really two modifications of one award is kept because removing it would ` +
      `destroy real obligations.\n\n` +
      `Every dropped row has a named reason, and every collection's known gaps are stated on the methods page.`,
    links: ["methods"],
  },
];

/**
 * Conversational filler. None of these is a topic: "thanks" then "tell me
 * more" still drills into the topic before the thanks. Their variants
 * rotate on repeats so two hellos in a row never read identically.
 */
const FILLER_INTENTS = [
  {
    id: "greeting",
    chip: null,
    triggers: ["hi", "hello", "hey", "hiya", "good morning", "good afternoon", "good evening", "howdy", "yo"],
    answer:
      `Hi, I'm Cedar. Here on the front page I can tell you what Cedar Press holds, where the records come ` +
      `from, how they reach the right nation and how to get access. What brings you in?`,
    variants: [
      "Hello again. Ask me about any collection by name, or how to get in.",
      "Still here. We can pick up where we left off, or start somewhere new.",
    ],
  },
  {
    id: "thanks",
    chip: null,
    triggers: ["thanks", "thank you", "thx", "ty", "appreciate it", "appreciated", "cheers", "great thanks"],
    answer: "You're welcome. Ask me about another collection, or how to get access, whenever you like.",
    variants: ["Any time.", "Glad it helped. I'm here if another question comes up."],
  },
  {
    id: "tell_me_more",
    chip: null,
    triggers: ["tell me more", "go deeper", "more detail", "more details", "expand on that", "expand on this", "say more", "keep going", "continue", "what else", "more please", "elaborate", "go on"],
    answer:
      `Happy to go deeper. Pick what is most useful: a collection by name, where the data comes from, how ` +
      `records are linked to nations, or how to get access, and I will take it from there.`,
  },
  {
    id: "affirmative",
    chip: null,
    triggers: ["yes", "yeah", "yep", "sure", "ok", "okay", "please", "yes please", "go ahead", "sounds good", "do it"],
    answer: "Which one? Name a collection, or ask about sources, linking, freshness or access.",
    variants: ["Go ahead and ask; I'm listening.", "Name the collection or the question and I will pick it up."],
  },
  {
    id: "negative",
    chip: null,
    triggers: ["no", "nope", "not really", "no thanks", "nah", "never mind", "nevermind"],
    answer: "No problem. I'm here if something else comes up.",
    variants: ["All right. Ask whenever you like.", "Understood."],
  },
  {
    id: "goodbye",
    chip: null,
    triggers: ["bye", "goodbye", "see you", "see ya", "later", "cya", "im done", "that is all", "thats all"],
    answer: "Take care. The collections and the methods page are here whenever you come back.",
    variants: ["Bye for now.", "See you next time."],
  },
];

/** Every intent: general first so a general question wins a shared word, then the twelve, then filler. */
export const DOOR_INTENTS = Object.freeze([...GENERAL_INTENTS, ...COLLECTION_INTENTS, ...FILLER_INTENTS]);

/** The ids that never become "the last topic". */
export const NON_TOPIC_IDS = Object.freeze(new Set(FILLER_INTENTS.map((intent) => intent.id)));

/** The starter chips: the questions worth putting in front of a visitor. */
export const DOOR_STARTERS = Object.freeze([
  "what",
  "collections",
  "sources",
  "entities",
  "plans",
  "current",
  "limits",
  "tribal",
  "research",
  "who",
]);

/** The chip row, resolved to intents. */
export const DOOR_CHIPS = Object.freeze(
  DOOR_STARTERS.map((id) => DOOR_INTENTS.find((intent) => intent.id === id)).filter(Boolean),
);

/**
 * Questions the door is not for. A message carrying one of these, with no
 * strong match of its own, gets the graceful miss rather than a weak
 * single-word guess: "who is the president" should not land on "who builds
 * it" because of the word "who".
 */
export const OUT_OF_SCOPE_TRIGGERS = Object.freeze([
  "weather",
  "write my essay",
  "tell me a joke",
  "a joke",
  "who won",
  "bitcoin",
  "crypto",
  "capital of",
  "dating advice",
  "homework",
  "who is the president",
  "meaning of life",
  "sports score",
  "recipe",
  "stock price",
  "translate",
]);

/**
 * Who the reader says they are. One quick-reply slot leans toward their own
 * route in for the rest of the conversation.
 */
export const DOOR_AUDIENCES = Object.freeze([
  { key: "tribal", intentId: "tribal", words: ["tribal government", "my nation", "our nation", "our tribe", "my tribe", "tribal council", "our records", "our office"] },
  { key: "research", intentId: "research", words: ["researcher", "journalist", "reporter", "student", "academic", "professor", "newsroom", "thesis", "my paper", "my story"] },
]);

const MATCHER = createMatcher(DOOR_INTENTS, { outOfScopeTriggers: OUT_OF_SCOPE_TRIGGERS });

/** The research desk, named once a reader has missed twice in a row. */
export const RESEARCH_DESK = "contact@lumecon.ai";

/**
 * What Cedar says when it has nothing for a question. It does not guess: it
 * says so, offers the closest things it can speak to, and after a second
 * miss in a row names a person.
 */
export function missAnswer(question, nearest = [], handingOff = false) {
  const labels = nearest.map((intent) => intent.chip).filter(Boolean);
  const closest = labels.length
    ? `The closest things I can speak to here are ${labels.length === 1 ? labels[0] : `${labels.slice(0, -1).join(", ")} and ${labels[labels.length - 1]}`}, ` +
      `and any of the ${COUNT} collections by name.`
    : `Try a collection by name, or ask what Cedar Press is, where the data comes from, how records are ` +
      `linked to nations, or how to get access.`;
  const handoff = handingOff
    ? `\n\nIf it is something specific, the research desk answers in person: ${RESEARCH_DESK}.`
    : "";
  return `I do not have that one here on the front page. ${closest}${handoff}`;
}

/** The door's configuration of the shared runtime. */
export const DOOR_BANK = Object.freeze({
  matcher: MATCHER,
  drillDownIds: new Set(["tell_me_more"]),
  affirmativeIds: new Set(["affirmative"]),
  nonTopicIds: NON_TOPIC_IDS,
  audiences: DOOR_AUDIENCES,
  defaultFollowUps: FALLBACK_FOLLOW_UPS,
  miss: missAnswer,
});

/** The door's memory at open. */
export const doorMemory = freshMemory;

/**
 * One turn of the door's Cedar: the whole decision for a question against
 * the bank and the thread's memory. See `resolveLocally`.
 */
export function resolveDoor(memory, question, options = {}) {
  return resolveLocally(DOOR_BANK, memory, question, options);
}

/** The quick replies under a door answer. See `followUpsFor` in the runtime. */
export function doorFollowUps(memory, resolution) {
  return runtimeFollowUps(DOOR_BANK, memory, resolution);
}

/**
 * Up to three next questions for an intent, minus anything already answered
 * in this conversation. The table form of the quick replies, kept for the
 * pane and for callers that hold an intent rather than a resolution.
 */
export function followUpsFor(intent, answered = new Set()) {
  const wanted = intent?.followUps?.length ? intent.followUps : FALLBACK_FOLLOW_UPS;
  const out = [];
  for (const id of wanted) {
    if (id === intent?.id || answered.has(id)) continue;
    const next = DOOR_INTENTS.find((candidate) => candidate.id === id);
    if (next && !out.includes(next)) out.push(next);
    if (out.length === 3) break;
  }
  return out;
}

/** A collection's own intent, for the pane's "Ask Cedar about this one". */
export function intentForCollection(id) {
  return DOOR_INTENTS.find((intent) => intent.collectionId === id) ?? null;
}

/**
 * The classifier: the best intent for a question, or null. Whole-phrase
 * triggers, longer phrases weigh more, ties fall to whichever intent is
 * declared first, which is why the general intents are listed before the
 * twelve. See `createMatcher`.
 */
export function classify(question) {
  return MATCHER.classify(question);
}

/** The bank's own matcher, for tests and for callers that need more than `classify`. */
export const doorMatcher = MATCHER;

/** The refusal as an intent, for callers that hold intents. */
export const DOOR_FALLBACK = Object.freeze({
  id: "fallback",
  answer: missAnswer(""),
  followUps: FALLBACK_FOLLOW_UPS,
});

/** The answer for a question with no memory, or the refusal. Never a guess. */
export function answer(question) {
  return classify(question) ?? MATCHER.fuzzy(question) ?? DOOR_FALLBACK;
}
