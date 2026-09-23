// REVIEW OWNER: Havala
//
// The reader's Cedar, the parts that are not a component: what the panel
// offers to ask, how a bare "tell me more" is understood, and which quick
// replies follow an answer. `PressCedarFab.jsx` renders them; this file is
// where `node --test` can reach them, and where the fast-refresh rule that a
// component file exports only components is kept.
import { normalise } from "./cedarConversation.js";
import { LAUNCH_COLLECTION } from "./collection.js";

// The collection-scoped prompt set, from the implementation brief §3, minus
// one.
//
// Every starter here was run against `answer_from_profile` before it was
// offered, because a starter that falls through to Cedar is a starter that
// comes back uncited, and the point of offering them is that they come back
// read off the release.
//
// THE ONE THAT IS NOT HERE. The brief also lists "Why is this record
// connected to this entity?", and that question does not fall through: it
// returns the collection's ROW COUNT. `_STATS_WORDS` in
// `collection_profiles.py` contains `"record"`, so any question carrying that
// word routes to headline figures: an identity question answered with
// "3,345,971 rows", confidently and in the release's name. That is the exact
// failure the answer-basis work exists to prevent, so the prompt is withheld
// until the router is fixed rather than shipped as a demonstration of it.
export const SCOPED_EXAMPLES = [
  "What does this collection cover?",
  "How are entities resolved?",
  "What sources are included?",
  "What changed in the latest release?",
];

/**
 * WHAT AN UNSCOPED PANEL OFFERS.
 *
 * Every page but the overview mounted this with no `examples`, so nine of
 * the eleven places a reader can open Cedar opened on a greeting and an
 * empty box. "Ask Cedar" is the product's own invitation and answering it
 * with a blank prompt is the worst moment to ask somebody to think of a
 * question.
 *
 * Each of these carries the collection it is about, so the tap scopes the
 * panel and the question is answerable as shown, the same rule the
 * overview's own set follows. They are collections rather than topics
 * because an unscoped question has no release to be answered from, and an
 * answer with no release behind it is the thing the basis line exists to
 * mark.
 */
export const OPEN_EXAMPLES = [
  { q: "What does this collection cover?", at: 0 },
  { q: "How was this collection built?", at: 1 },
  { q: "What sources are included?", at: 2 },
  { q: "What changed in the latest release?", at: 3 },
]
  .map(({ q, at }) => {
    const entry = LAUNCH_COLLECTION[at];
    return entry ? { q, scope: { id: entry.id, name: entry.name } } : null;
  })
  .filter(Boolean);

/** The phrases that mean "more on what you just said" rather than a new question. */
const DRILL_DOWN = ["tell me more", "go deeper", "more detail", "more details", "say more", "keep going", "continue", "what else", "elaborate", "go on", "more please"];
export const isDrillDown = (question) => {
  const asked = normalise(question).trim();
  return DRILL_DOWN.some((phrase) => asked === phrase || asked === `${phrase} please`);
};

/** A question as a topic the thread can remember. */
export const topicOf = (question, scope = null) => ({
  id: `${scope?.id ?? "*"}:${normalise(question).trim()}`,
  chip: String(question ?? "").trim(),
});

/**
 * The quick replies under an answer: the questions worth asking next about
 * this collection (or these collections), minus any this thread has already
 * asked, and "Tell me more" first when Cedar itself composed the answer and
 * so can go deeper on it. A gate, a routing note or an error offers nothing:
 * there is no answer to follow up.
 *
 * `examples` is the unscoped set the page mounted; each entry may carry the
 * scope its question is about.
 */
export function fabFollowUps(memory, reply, { scope, examples }) {
  if (!reply || ["gate", "routing", "error"].includes(reply.kind)) return [];
  const out = [];
  if (reply.source === "cedar" && reply.intent) {
    out.push({ label: "Tell me more", text: "tell me more", intent: null });
  }
  const candidates = scope
    ? SCOPED_EXAMPLES.map((q) => ({ q, scope }))
    : examples.map((example) => (typeof example === "string" ? { q: example, scope: null } : { q: example.q, scope: example.scope ?? null }));
  for (const candidate of candidates) {
    if (out.length >= 3) break;
    const topic = topicOf(candidate.q, candidate.scope);
    if (memory.answered[topic.id] || topic.id === reply.intent?.id) continue;
    if (out.some((o) => o.label === candidate.q)) continue;
    out.push({
      label: candidate.scope && !scope ? `${candidate.q} (${candidate.scope.name})` : candidate.q,
      text: candidate.q,
      intent: null,
      scope: candidate.scope,
    });
  }
  return out.slice(0, 3);
}

