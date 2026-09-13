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
 * (`src/data/cedarIntents.ts`): a keyword-classified bank of prepared
 * answers. It never reaches the network, so it can answer a visitor's real
 * questions about what Cedar Press holds without opening anything a
 * subscriber pays for. It is not an LLM and does not pretend to be — the
 * panel says "prepared answers" on its face.
 *
 * WHERE THE DATASET ANSWERS COME FROM
 * The twelve collection answers are assembled from the catalog and the
 * release record at module load: name, shelf, blurb, coverage, row count,
 * update date, sources and linkage. Nothing about a collection is typed
 * here, so an answer cannot drift from the collection it describes, and the
 * day a release changes the row count the door's answer changes with it.
 *
 * The general answers ARE written here, because "what is Cedar Press" is a
 * position, not a measurement. Every number inside them is interpolated.
 */

import { LAUNCH_COLLECTION } from "./collection.js";
import { coverageLabel } from "./pressAccess.js";
import { PRESS_CATALOG_BY_ID, PRESS_TIERS, STOREFRONT_CATALOG } from "./pressCatalog.js";
import { formatUpdated, freshnessLine, recentlyUpdated } from "./pressReleases.js";
import { REGISTRY_PROGRAMS, SOURCE_COUNT } from "./pressSources.js";

const DESCRIPTOR = Object.fromEntries(LAUNCH_COLLECTION.map((entry) => [entry.id, entry]));
const TIER_BY_SHELF = Object.fromEntries(PRESS_TIERS.map((tier) => [tier.shelf, tier]));

/** Extra words that should reach a collection beyond its own name. */
const COLLECTION_WORDS = Object.freeze({
  funding: ["grant", "grants", "assistance", "award", "awards", "usaspending", "federal money", "block grant"],
  "federal-register": ["notice", "notices", "rule", "rulemaking", "comment period", "register"],
  legislation: ["bill", "bills", "congress", "vote", "votes", "roll call", "senate", "house", "law"],
  deals: ["deal", "acquisition", "merger", "bond", "financing", "transaction", "investment", "joint venture"],
  nagpra: ["repatriation", "remains", "graves", "inventory", "museum", "ancestors"],
  lobbying: ["lobby", "lobbying", "advocacy", "consultation", "docket", "ferc", "nrc", "testimony", "lda"],
  contractors: ["contract", "contracts", "contracting", "prime", "fpds", "8(a)", "set aside", "set-aside", "vendor"],
  subcontracting: ["subaward", "subawards", "subcontract", "subcontractor", "fsrs"],
  owned: ["tero", "small business", "individually owned", "business directory", "certified"],
  nonprofits: ["nonprofit", "nonprofits", "990", "irs", "charity", "foundation"],
  need: ["enterprise", "enterprises", "subsidiary", "subsidiaries", "ownership", "who owns", "holding company", "structure"],
  "natural-resources": ["royalty", "royalties", "oil", "gas", "coal", "mineral", "minerals", "timber", "severance", "onrr"],
});

/** One prepared answer per collection, assembled from what the catalog holds. */
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

function lowerFirst(text) {
  const value = String(text ?? "");
  return value ? value[0].toLowerCase() + value.slice(1) : value;
}

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
}));

const COUNT = STOREFRONT_CATALOG.length;
const NEWEST = recentlyUpdated(1)[0] ?? null;
const PRESS = PRESS_TIERS.find((tier) => tier.id === "press");
const PRESS_PRO = PRESS_TIERS.find((tier) => tier.id === "press_pro");

/**
 * The written intents. Positions, not measurements — but every figure in
 * them is interpolated from the catalog, so none of them can go stale.
 */
const GENERAL_INTENTS = [
  {
    id: "what",
    chip: "What is Cedar Press?",
    triggers: ["what is cedar press", "what is this", "what does cedar press do", "what is cedar", "about cedar press", "explain cedar press", "what do you do"],
    answer:
      `Cedar Press is a research and intelligence service about Indian Country's economy. ` +
      `It publishes ${COUNT} maintained collections, built from ${SOURCE_COUNT} kinds of source and ` +
      `resolved to the nations, corporations and organizations the records belong to.\n\n` +
      `A federal contract names a vendor. It does not say which nation owns that vendor. Cedar does ` +
      `the work between the record and the entity, publishes what it could not resolve, and keeps the ` +
      `collections current as new material arrives. Alongside the data there are research briefs, a ` +
      `release history and a methods reference.`,
  },
  {
    id: "collections",
    chip: "What collections are there?",
    triggers: ["what collections", "which collections", "list the collections", "what datasets", "which datasets", "what data do you have", "what is in it", "how many collections"],
    answer:
      `${COUNT} collections, on two shelves.\n\n` +
      `${PRESS?.name}: ${STOREFRONT_CATALOG.filter((e) => e.shelf === "standard").map((e) => e.short || e.name).join(", ")}.\n\n` +
      `${PRESS_PRO?.name}: ${STOREFRONT_CATALOG.filter((e) => e.shelf === "pro").map((e) => e.short || e.name).join(", ")}.\n\n` +
      `Ask me about any one of them by name and I will tell you what it holds, how far back it goes and what it is built from.`,
  },
  {
    id: "sources",
    chip: "Where does the data come from?",
    triggers: ["where does the data come from", "what are the sources", "what sources", "source systems", "is this public data", "where do you get", "how do you get the data", "provenance"],
    answer:
      `${SOURCE_COUNT} kinds of source across the ${COUNT} collections. Federal spending and award systems ` +
      `(USAspending, FPDS, FSRS, SAM, FAADS), Congress and the Federal Register (Congress.gov, Voteview, ` +
      `federalregister.gov), advocacy and docket records (Senate and House lobbying disclosure, FERC and NRC ` +
      `dockets, IBIA and IBLA appeals, regulations.gov), tax filings (IRS Business Master File, Form 990), ` +
      `resource revenue (ONRR, OSMRE, ANCSA 7(i) and 7(j) filings, the Osage Minerals Council), and what ` +
      `nations and corporations publish about themselves.\n\n` +
      `Some kinds are deep rather than single. Behind the tribal business directories sits a registry of ` +
      `${REGISTRY_PROGRAMS} source programs, each one a nation's own TERO list, a member-owned directory, a ` +
      `state certified-vendor list or a regional chamber.\n\n` +
      `Not all of it is public. The Native-Owned Businesses collection comes from tribal TERO and commerce ` +
      `offices under each nation's stated terms, and publishers whose terms forbid reuse are excluded by ` +
      `every route and named as excluded.`,
  },
  {
    id: "entities",
    chip: "How are records linked to nations?",
    triggers: ["how are records linked", "entity resolution", "how do you link", "how do you know which tribe", "resolved to", "matching", "how do you connect"],
    answer:
      `Every collection keys to the same entity layer. A vendor in a federal contract, a recipient in an ` +
      `assistance award, a party named in a notice and a subsidiary in an annual report are resolved to the ` +
      `nation, corporation or organization behind them, tracked through name changes, subsidiaries and ` +
      `reorganizations, so one enterprise's four names over a decade read as one enterprise.\n\n` +
      `Where a record cannot be placed, it keeps its printed party name and a blank key rather than a guess. ` +
      `Unresolved is published as unresolved. The methods page sets out the rules.`,
  },
  {
    id: "current",
    chip: "How current is it?",
    triggers: ["how current", "how often updated", "how fresh", "update", "updated", "cadence", "how often", "is it current", "snapshot"],
    answer:
      NEWEST
        ? `Records are added, ownership changes and corrections arrive every week, and the collections are ` +
          `kept current against them. The most recent release was ${formatUpdated(NEWEST.updated)}.\n\n` +
          `Every release is dated and versioned, and the release history records what changed, so a figure ` +
          `you cited last quarter still reproduces.`
        : `Records are added, ownership changes and corrections arrive every week, and every release is ` +
          `dated and versioned so a figure you cited last quarter still reproduces.`,
  },
  {
    id: "plans",
    chip: "How do I get access?",
    triggers: ["how do i get", "how much", "price", "pricing", "cost", "subscribe", "subscription", "plans", "buy", "sign up", "membership", "tiers", "difference between"],
    answer:
      `Cedar Press is available exclusively through a Tribal Business News membership, which handles ` +
      `payment, renewals and upgrades.\n\n` +
      `${PRESS?.name} opens ${STOREFRONT_CATALOG.filter((e) => e.shelf === "standard").length} collections — ` +
      `${lowerFirst(PRESS?.question ?? "")}\n` +
      `${PRESS_PRO?.name} adds the other ${STOREFRONT_CATALOG.filter((e) => e.shelf === "pro").length} — ` +
      `${lowerFirst(PRESS_PRO?.question ?? "")}\n\n` +
      `Two other routes need no subscription at all: a federally recognized tribal government can request ` +
      `and review the Cedar records about its own nation, and research access covers one or two collections ` +
      `for a defined project.`,
    links: ["plans", "request", "research"],
  },
  {
    id: "tribal",
    chip: "I work for a tribal government",
    triggers: ["tribal government", "my nation", "our records", "data request", "request our data", "sovereignty", "our nation's records", "free access"],
    answer:
      `Federally recognized tribal governments can request and review the Cedar records associated with ` +
      `their nation. No subscription is required.\n\n` +
      `The request page sets out what you get, what Cedar will and will not publish, and how to raise a ` +
      `correction.`,
    links: ["request"],
  },
  {
    id: "research",
    chip: "I'm a researcher or journalist",
    triggers: ["researcher", "journalist", "student", "academic", "citation", "cite", "research access", "for a project", "nonprofit access", "public interest"],
    answer:
      `Research access covers one or two collections for a defined project, for researchers, journalists, ` +
      `students, nonprofits and public-interest work. It needs no subscription.\n\n` +
      `If you are going to cite a figure, read the methods page first: it states inclusion rules, known ` +
      `gaps and how each collection is versioned, which is what a citation needs.`,
    links: ["research", "methods"],
  },
  {
    id: "who",
    chip: "Who builds it?",
    triggers: ["who builds", "who made", "who are you", "who is behind", "lumecon", "team", "tribal business news", "credentials", "who runs"],
    answer:
      `Cedar Press is built by Lumecon and distributed exclusively through Tribal Business News.\n\n` +
      `The collections are assembled by Indigenous researchers with Federal Reserve and university ` +
      `experience. Inclusion rules, known limitations and corrections ship with every collection rather ` +
      `than sitting in a document somewhere.`,
  },
  {
    id: "limits",
    chip: "What are the limits?",
    triggers: ["limitations", "limits", "what is missing", "gaps", "caveats", "accuracy", "how accurate", "problems", "what can't", "cannot"],
    answer:
      `Every collection publishes its own. The common ones: federal publication lags, so a current year is ` +
      `partial and labelled as partial; some records name a party the source cannot place, and those keep ` +
      `the printed name with a blank key rather than a guess; and roster collections state a capture date ` +
      `rather than a span, because their sources publish who is on the list now and archive nothing.\n\n` +
      `Cedar does not invent a date, an owner or a boundary to make a column tidy. Where a figure is not ` +
      `measured it is absent, not zero.`,
    links: ["methods"],
  },
];

/** Every intent, general first so a general question wins a shared word. */
export const DOOR_INTENTS = Object.freeze([...GENERAL_INTENTS, ...COLLECTION_INTENTS]);

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
 * What to offer after an answer, by the intent that was just answered.
 *
 * The door used to re-print the whole starter stack under every reply, which
 * read as a toolbar that had not noticed the conversation. lumecon.ai offers
 * at most three next questions under the answer instead (`followUpsFor` in
 * src/lib/cedarChat.ts), chosen by what was just discussed. This is that
 * table: deliberate pairs rather than a scored guess, because the door's bank
 * is ten general answers and twelve collections, small enough to write out.
 *
 * The twelve collections share one list — after "what is in Federal Prime
 * Contracting", the useful next questions are how it reaches a nation, what
 * it is built from, and how to get it.
 */
const FOLLOW_UPS = Object.freeze({
  what: ["collections", "entities", "plans"],
  collections: ["sources", "entities", "plans"],
  sources: ["current", "entities", "limits"],
  entities: ["limits", "sources", "plans"],
  current: ["sources", "collections", "plans"],
  plans: ["tribal", "research", "collections"],
  tribal: ["plans", "entities", "who"],
  research: ["plans", "limits", "sources"],
  who: ["entities", "limits", "plans"],
  limits: ["entities", "sources", "plans"],
});

const COLLECTION_FOLLOW_UPS = Object.freeze(["entities", "sources", "plans"]);
const FALLBACK_FOLLOW_UPS = Object.freeze(["what", "collections", "plans"]);

/**
 * Up to three next questions for an answer, minus anything already answered
 * in this conversation. Returns intents, so the caller routes a click
 * straight to the answer rather than re-classifying the label.
 *
 * `answered` is the set of intent ids the thread has already used. A
 * conversation that has exhausted a list gets no row rather than a repeat.
 */
export function followUpsFor(intent, answered = new Set()) {
  const wanted = intent?.collectionId
    ? COLLECTION_FOLLOW_UPS
    : (FOLLOW_UPS[intent?.id] ?? FALLBACK_FOLLOW_UPS);
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

const normalise = (text) =>
  ` ${String(text ?? "").toLowerCase().replace(/[^a-z0-9()' ]+/g, " ").replace(/\s+/g, " ").trim()} `;

/**
 * The classifier. A trigger scores when it appears in the normalised
 * question; the longest matching trigger wins, so "prime contracting" beats
 * a bare "contract", and ties fall to whichever intent is declared first —
 * which is why the general intents are listed before the twelve.
 */
export function classify(question) {
  const asked = normalise(question);
  if (asked.trim().length < 2) return null;
  let best = null;
  let bestScore = 0;
  for (const intent of DOOR_INTENTS) {
    for (const trigger of intent.triggers) {
      const needle = normalise(trigger).trim();
      if (!needle || !asked.includes(needle)) continue;
      // Longer triggers are more specific; a whole-phrase hit beats a word.
      const score = needle.length + (asked.includes(` ${needle} `) ? 1 : 0);
      if (score > bestScore) {
        best = intent;
        bestScore = score;
      }
    }
  }
  return best;
}

/** What Cedar says when it has nothing prepared. It does not guess. */
export const DOOR_FALLBACK = Object.freeze({
  id: "fallback",
  answer:
    `I answer from a prepared set here on the front page, and I do not have that one.\n\n` +
    `Try a collection by name, or ask what Cedar Press is, where the data comes from, how records are ` +
    `linked to nations, or how to get access. Inside the product, Cedar answers from the collections ` +
    `themselves rather than from a script.`,
});

/** The answer for a question, or the fallback. Never a guess. */
export function answer(question) {
  return classify(question) ?? DOOR_FALLBACK;
}
