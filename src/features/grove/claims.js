/**
 * PURPOSE
 * Govern what Cedar Grove is allowed to say about a piece of evidence.
 *
 * Grove's statements do not stay in Grove. They go into council packets, grant
 * applications, board presentations and advocacy materials, where a sentence
 * that quietly upgrades a correlation into a cause becomes a claim the
 * organization has to defend in public. Finding the pattern is the easy half.
 * The half that matters is telling someone what they can responsibly say about
 * it.
 *
 * The load-bearing idea in this module: **confidence and causality are separate
 * dimensions.** You can be as certain as evidence ever gets that employment
 * rose 25 percent, and have no basis whatsoever for saying why it rose. A
 * finding can be maximally defensible and purely descriptive. Grove must make
 * that distinction almost impossible for a reader to miss, which means it has
 * to be impossible for Grove itself to blur.
 *
 * INPUTS
 * A claim: a statement plus the class of evidence behind it.
 *
 * OUTPUTS
 * - `CLAIM_CLASS`: the taxonomy.
 * - `lintClaim()`: whether a statement's language matches its class, and which
 *   phrase broke the rule.
 * - `correctOverstatement()`: a defensible rewrite of an overstated sentence.
 * - `HELP`: the contextual copy behind every `?` in Grove.
 *
 * SOURCE
 * Nothing is fetched. This is a language rulebook, and it is deliberately
 * conservative: a phrase that is sometimes fine and often misleading is
 * treated as forbidden, because the cost of a false positive is a slightly
 * flatter sentence and the cost of a false negative is a wrong claim in a
 * public document.
 *
 * ASSUMPTIONS
 * Class is declared by the evidence recipe, not inferred from the sentence.
 * Grove never promotes a claim to a stronger class on its own.
 *
 * PROTOTYPE LIMITATIONS
 * The linter matches phrases, not grammar. "The data show employment
 * increased" and "The data show the expansion increased employment" differ by
 * their subject, not by a keyword, and only the second is causal. The linter
 * catches the common cases and is not a parser.
 *
 * ECONOMICS REVIEW
 * Review the language rules distinguishing descriptive, comparative,
 * associational, modeled and causal claims, and in particular the terminology
 * around input-output estimates and "supported" economic activity. The verb
 * lists below are a starting framework, not a settled house style.
 *
 * HAVALA REVIEW
 * Review the evidence classifications themselves, and the rule that a claim
 * inherits its class from the recipe rather than from the strength of the
 * pattern.
 */

/**
 * What kind of statement a piece of evidence can support.
 *
 * Seven classes, ordered from what was observed to what was identified. The
 * order matters: Grove may always describe a claim in a weaker class than its
 * evidence allows, and never in a stronger one.
 */
export const CLAIM_CLASS = Object.freeze({
  /** What was observed, in the data, as recorded. */
  descriptive: "descriptive",
  /** A difference between groups, places or periods. */
  comparative: "comparative",
  /** Two things move together or are statistically related. */
  associational: "associational",
  /** Produced by a model rather than observed. */
  modeled: "modeled",
  /** An identified effect, from a design that supports causal inference. */
  causal: "causal",
  /** Establishes the setting rather than proving a finding. */
  contextual: "contextual",
  /** A pattern worth investigating, not yet a finding. */
  exploratory: "exploratory",
});

export const CLAIM_CLASS_LABEL = Object.freeze({
  descriptive: "Descriptive",
  comparative: "Comparative",
  associational: "Associational",
  modeled: "Modeled estimate",
  causal: "Causal",
  contextual: "Contextual",
  exploratory: "Exploratory",
});

/**
 * One-line statements of what each class can and cannot carry. These are what
 * the interface shows when a reader asks what a class means.
 */
export const CLAIM_CLASS_MEANING = Object.freeze({
  descriptive: {
    can: "State what was observed, for the stated geography, population and period.",
    cannot: "Say why it happened, or that anything caused it.",
  },
  comparative: {
    can: "State that one group, place or period differs from another.",
    cannot: "Say why the difference exists, or attribute it to either side.",
  },
  associational: {
    can: "State that two things move together, or that one occurred during the other.",
    cannot: "Say that one produced the other.",
  },
  modeled: {
    can: "State what a model estimates, naming the model and its assumptions.",
    cannot: "Present the estimate as an observed count, or as an identified effect.",
  },
  causal: {
    can: "State an estimated effect, naming the design and the comparison group.",
    cannot: "Be used because a pattern looks convincing. The design has to support it.",
  },
  contextual: {
    can: "Describe the economic or demographic setting the analysis sits in.",
    cannot: "Stand in for the impact finding itself.",
  },
  exploratory: {
    can: "Raise a question or pattern worth investigating.",
    cannot: "Be presented as a conclusion.",
  },
});

// ---------------------------------------------------------------------------
// Language rules
// ---------------------------------------------------------------------------

/**
 * Verbs and phrases that assert cause. Forbidden anywhere except a claim whose
 * class is `causal`.
 *
 * "impact of" and "effect of" are on the list deliberately. They are ordinary
 * words in this industry and they are causal claims: the effect of X on Y is
 * precisely the thing an input-output model does not identify.
 */
// Each verb is matched in every inflection: past, present, base and -ing.
// "The project will create 500 jobs" is the canonical wording of an impact
// pitch, and a linter that catches "created" while passing "will create" is a
// linter that misses the sentence most likely to be written.
const CAUSAL_PHRASES = Object.freeze([
  { pattern: /\bcaus(?:es|ed|e|ing)\b/i, phrase: "caused" },
  { pattern: /\b(?:leads?|led|leading) to\b/i, phrase: "led to" },
  { pattern: /\bresult(?:s|ed|ing)? in\b/i, phrase: "resulted in" },
  { pattern: /\bproduc(?:es|ed|e|ing)\b/i, phrase: "produced" },
  { pattern: /\bgenerat(?:es|ed|e|ing)\b/i, phrase: "generated" },
  { pattern: /\bcreat(?:es|ed|e|ing)\b/i, phrase: "created" },
  { pattern: /\b(?:drives?|drove|driven|driving)\b/i, phrase: "drove" },
  { pattern: /\bbecause of\b/i, phrase: "because of" },
  { pattern: /\bdue to\b/i, phrase: "due to" },
  { pattern: /\bthanks to\b/i, phrase: "thanks to" },
  { pattern: /\beffect of\b/i, phrase: "effect of" },
  { pattern: /\bimpact of\b/i, phrase: "impact of" },
  { pattern: /\battributable to\b/i, phrase: "attributable to" },
  { pattern: /\bresponsible for\b/i, phrase: "responsible for" },
  { pattern: /\bboost(?:s|ed|ing)?\b/i, phrase: "boosted" },
  { pattern: /\bspur(?:s|red|ring)?\b/i, phrase: "spurred" },
]);

/**
 * Claims of proof. Forbidden in every class, including causal.
 *
 * Statistical and economic evidence supports, estimates, indicates, documents
 * or is consistent with a proposition. It does not prove one.
 */
const PROOF_PHRASES = Object.freeze([
  // "prov(es?|ed|ing)" and not "prov": "provide" and "province" are
  // innocent, and "proved" is the past-tense form that slipped through.
  { pattern: /\bprov(?:es?|ed|ing)\b/i, phrase: "proves" },
  { pattern: /\bproof\b/i, phrase: "proof" },
  { pattern: /\bproven\b/i, phrase: "proven" },
  { pattern: /\bconclusively\b/i, phrase: "conclusively" },
  { pattern: /\bdefinitively\b/i, phrase: "definitively" },
  { pattern: /\bconfirm(?:s|ed|ing)? that\b/i, phrase: "confirms that" },
  { pattern: /\bundeniabl/i, phrase: "undeniably" },
  { pattern: /\bguarantee(?:s|d|ing)?\b/i, phrase: "guarantees" },
]);

/**
 * Phrases that present a modeled estimate as an observed count. Forbidden on a
 * `modeled` claim, which is where they are most tempting and most wrong: an
 * input-output model estimates activity supported by a level of spending. It
 * does not count jobs anyone created.
 */
// "counted" stays past-tense-only on purpose: "count" and "counts" are
// ordinary nouns in this domain ("establishment counts") and forbidding them
// would flag honest sentences constantly.
const OBSERVATION_PHRASES = Object.freeze([
  { pattern: /\badd(?:s|ed|ing)?\b/i, phrase: "added" },
  { pattern: /\b(?:brings?|brought|bringing)\b/i, phrase: "brought" },
  { pattern: /\bactual\b/i, phrase: "actual" },
  { pattern: /\bcounted\b/i, phrase: "counted" },
]);

/** Verbs that are safe for a purely descriptive statement. */
export const DESCRIPTIVE_VERBS = Object.freeze([
  "increased", "decreased", "rose", "fell", "was", "were", "accounted for",
  "represented", "reported", "employed", "earned", "lived", "occurred",
  "recorded", "documented",
]);

/** Verbs that keep a modeled result honest about being modeled. */
export const MODELED_VERBS = Object.freeze([
  "estimates", "supported", "associated with", "modeled", "is estimated at",
]);

/**
 * PURPOSE
 * Bridge the two class vocabularies Grove carries, rather than merging them.
 *
 * They describe different things and both are correct. `EVIDENCE_CLASS` in
 * evidence.js is a property of a RECIPE: what kind of evidence this source and
 * method produce. `CLAIM_CLASS` here is a property of a STATEMENT: what a
 * particular sentence asserts. One recipe supports several statements, and a
 * comparative recipe may be used to make a merely descriptive claim.
 *
 * The mapping is therefore a ceiling, not an equivalence. It answers "what is
 * the strongest claim this evidence could support", and Grove may always state
 * something weaker. The direction matters: without it, an evidence object with
 * no claim class attached would default to descriptive, and a modeled impact
 * would lose the label that keeps it honest.
 *
 * `modeled_impact` maps to modeled and not to causal deliberately. An
 * input-output result is an estimate produced under assumptions, and no part of
 * the method identifies an effect.
 *
 * ECONOMICS REVIEW
 * Confirm the ceiling for `causal`. A recipe is currently allowed to declare
 * itself causal, which trusts the recipe author. The alternative is to require
 * an identification strategy in the recipe metadata before the causal class is
 * reachable at all, so causal is earned by design rather than by declaration.
 */
export function strongestClaimClassFor(evidenceClass) {
  switch (evidenceClass) {
    case "comparative":
      return CLAIM_CLASS.comparative;
    case "modeled_impact":
      return CLAIM_CLASS.modeled;
    case "causal":
      return CLAIM_CLASS.causal;
    case "descriptive":
      return CLAIM_CLASS.descriptive;
    default:
      // An unrecognized class must not silently become a strong one. Grove
      // reports the weakest class it has, which is the safe failure.
      return CLAIM_CLASS.descriptive;
  }
}

/** Which phrase families each class forbids. */
const FORBIDDEN_BY_CLASS = Object.freeze({
  descriptive: [CAUSAL_PHRASES, PROOF_PHRASES],
  comparative: [CAUSAL_PHRASES, PROOF_PHRASES],
  associational: [CAUSAL_PHRASES, PROOF_PHRASES],
  modeled: [CAUSAL_PHRASES, PROOF_PHRASES, OBSERVATION_PHRASES],
  contextual: [CAUSAL_PHRASES, PROOF_PHRASES],
  exploratory: [CAUSAL_PHRASES, PROOF_PHRASES],
  // A causal claim may say caused. It still may not say proved.
  causal: [PROOF_PHRASES],
});

/**
 * PURPOSE
 * Check a statement against the class of evidence behind it.
 *
 * Used two ways: as a guard on anything Grove generates, and as a test the
 * suite runs over every finding so an overstatement cannot ship.
 *
 * @param {string} text the statement as it would be shown
 * @param {string} claimClass a CLAIM_CLASS value
 * @returns {{ok: boolean, violations: Array<{phrase: string, kind: string, why: string}>}}
 */
export function lintClaim(text, claimClass) {
  const statement = String(text ?? "");
  const families = FORBIDDEN_BY_CLASS[claimClass] || [CAUSAL_PHRASES, PROOF_PHRASES];
  const violations = [];

  // The accounting term "value added" is a fixed noun phrase, not a claim
  // that jobs were added; scan a copy with it masked so GDP-contribution
  // findings pass while "added 400 jobs" still gets caught.
  const scanned = statement.replace(/\bvalue[- ]added\b/gi, "value contribution");
  for (const family of families) {
    for (const { pattern, phrase } of family) {
      if (!pattern.test(scanned)) continue;
      if (family === PROOF_PHRASES) {
        violations.push({
          phrase,
          kind: "proof",
          why: "Evidence supports, estimates, indicates or documents a proposition. It does not prove one.",
        });
      } else if (family === OBSERVATION_PHRASES) {
        violations.push({
          phrase,
          kind: "modeled-as-observed",
          why: `A modeled estimate is not an observed count, so "${phrase}" overstates what the model measured.`,
        });
      } else {
        violations.push({
          phrase,
          kind: "causal",
          why: `"${phrase}" asserts cause, and ${CLAIM_CLASS_LABEL[claimClass]?.toLowerCase() || "this"} evidence does not identify one.`,
        });
      }
    }
  }
  return { ok: violations.length === 0, violations };
}

// ---------------------------------------------------------------------------
// Correcting overstatement
// ---------------------------------------------------------------------------

/**
 * Rewrites that keep the observation and drop the unsupported attribution.
 *
 * Every entry here is a **valency-safe** substitution: the replacement takes
 * the same grammatical shape as the phrase it replaces, so the sentence stays
 * grammatical. That constraint is why the list is short.
 *
 * Deliberately absent: "caused". "The casino caused employment to rise" cannot
 * be repaired by swapping a verb, because the causative construction
 * ("A caused B to C") has no same-shape non-causal equivalent. Substituting one
 * produces "The casino coincided with employment to rise", which is worse than
 * saying nothing. Those cases get guidance instead of a rewrite, in
 * `correctOverstatement` below.
 */
/**
 * Substitutions that keep the sentence's tense and keep the estimate
 * explicit. "Created 400 jobs" rewritten to "supported 400 jobs" still
 * states the modeled result as fact, which trades one prohibited claim for
 * another; the required construction says the jobs are estimated. Each form
 * maps to an explicitly estimated phrasing in its own tense, so "will
 * create" keeps its future sense and a participial "creating" stays
 * participial.
 */
const SUPPORTED_BY_FORM = Object.freeze({
  created: "is estimated to have supported", added: "is estimated to have supported",
  creates: "is estimated to support", adds: "is estimated to support",
  create: "support an estimated", add: "support an estimated",
  creating: "supporting an estimated", adding: "supporting an estimated",
});

const ACCOMPANIED_BY_FORM = Object.freeze({
  // Past forms.
  "led to": "was accompanied by", "resulted in": "was accompanied by",
  produced: "was accompanied by", generated: "was accompanied by",
  // Present forms.
  "leads to": "is accompanied by", "results in": "is accompanied by",
  produces: "is accompanied by", generates: "is accompanied by",
  // Base forms, as in "will result in".
  "lead to": "be accompanied by", "result in": "be accompanied by",
  produce: "be accompanied by", generate: "be accompanied by",
});

const REWRITES = Object.freeze([
  // Modeled employment presented as job creation. The single most common
  // overstatement in this industry, and a clean verb-for-verb swap.
  {
    when: /\b(creates?|created|creating|adds?|added|adding)\b/i,
    forClass: CLAIM_CLASS.modeled,
    replace: (text) =>
      text.replace(
        /\b(creates?|created|creating|adds?|added|adding)\b/gi,
        (match, _verb, offset, whole) => {
          // The accounting term "value added" is a fixed noun phrase; the
          // finite estimated phrase would mangle it.
          if (/\bvalue[- ]$/i.test(whole.slice(0, offset))) return match;
          // A passive or participial use ("Jobs created by the expansion")
          // cannot take the finite phrase either; left as found, the linter
          // still flags it and no automatic rewrite is offered.
          if (/^\s+by\b/i.test(whole.slice(offset + match.length))) return match;
          return SUPPORTED_BY_FORM[match.toLowerCase()] ?? "supported";
        },
      ),
    note:
      '"Estimated to support" keeps both truths: the model estimates, and what it measures is activity sustained by a level of spending, not jobs anyone created.',
  },
  // Preposition for preposition.
  {
    when: /\b(because of|due to|thanks to|attributable to)\b/i,
    replace: (text) =>
      text.replace(/\b(because of|due to|thanks to|attributable to)\b/gi, "during the same period as"),
    note: "The timing is documented. The attribution is not.",
  },
  // Verb for verb, both taking a noun-phrase object. The -ing forms are
  // deliberately absent: "leading to X" has no substitution that stays
  // grammatical, so those sentences take the no-suggestion path instead.
  {
    when: /\b(leads? to|led to|results? in|resulted in|produces?|produced|generates?|generated)\b/i,
    replace: (text) =>
      text.replace(
        /\b(leads? to|led to|results? in|resulted in|produces?|produced|generates?|generated)\b/gi,
        (match) => ACCOMPANIED_BY_FORM[match.toLowerCase()] ?? "was accompanied by",
      ),
    note:
      "The evidence shows the two together. Attributing one to the other needs a design that identifies the effect.",
  },
  {
    when: /\b(prov(?:es?|ed|ing)|proven|conclusively|definitively)\b/i,
    replace: (text) =>
      text
        .replace(/\bproves\b/gi, "indicates")
        .replace(/\bproved\b/gi, "indicated")
        .replace(/\bprove\b/gi, "indicate")
        .replace(/\bproving\b/gi, "indicating")
        .replace(/\bproven\b/gi, "documented")
        .replace(/\s*\b(conclusively|definitively)\b/gi, ""),
    note: "Evidence indicates, documents or is consistent with. Proof is a bar statistical evidence does not clear.",
  },
]);

/** The causative construction, which cannot be repaired by substitution. */
const CAUSATIVE = /\b(caus(?:es|ed|e|ing)|drives?|drove|driven|driving)\b/i;

/**
 * PURPOSE
 * Turn an overstated sentence into one the evidence supports.
 *
 * This is the behaviour Cedar needs. A user writes "The new casino caused
 * county employment to increase 14 percent" and Grove holds only a descriptive
 * employment trend. Cedar should not reinforce the sentence; it should say what
 * the evidence does show and offer the defensible version.
 *
 * @param {string} text the user's sentence
 * @param {string} claimClass the class of evidence actually available
 * @returns {{overstated: boolean, original, suggestion, why, note} | {overstated: false}}
 */
export function correctOverstatement(text, claimClass) {
  const statement = String(text ?? "");
  const { ok, violations } = lintClaim(statement, claimClass);
  if (ok) return { overstated: false, original: statement, suggestion: statement };

  // Every matching family is applied, not just the first: a sentence carrying
  // both a proof claim and a causal verb needs both repaired, and a suggestion
  // that fixes one while shipping the other is worse than none.
  const applied = [];
  let candidate = statement;
  for (const entry of REWRITES) {
    if (!entry.when.test(candidate)) continue;
    if (entry.forClass && entry.forClass !== claimClass) continue;
    candidate = entry.replace(candidate);
    applied.push(entry);
  }

  // A suggestion is offered only when the substitution keeps the sentence
  // grammatical AND the result passes the linter for its own class. Where it
  // would not, Grove says what the evidence does show and what the sentence
  // would have to become, rather than emitting a mangled or still-overstated
  // rewrite that the user then has to repair.
  const canRewrite =
    applied.length > 0 && !CAUSATIVE.test(statement) && lintClaim(candidate, claimClass).ok;

  return {
    overstated: true,
    original: statement,
    suggestion: canRewrite ? candidate : null,
    // What the evidence does support, stated before the correction so the
    // reader is not simply told no.
    why: violations[0].why,
    note: canRewrite ? applied[0].note : null,
    guidance: canRewrite
      ? null
      : "State the observation and the timing separately, and leave the attribution out: say what changed, over what period, and that the two occurred together.",
    violations,
  };
}

// ---------------------------------------------------------------------------
// The methods layer behind every "?"
// ---------------------------------------------------------------------------

/**
 * Contextual help copy.
 *
 * These are not glossary entries. Each one exists to stop a specific
 * misreading, and the most important is `highConfidence`: confidence describes
 * how well the evidence fits the statement, and says nothing at all about
 * cause.
 */
export const HELP = Object.freeze({
  supportedFinding: {
    title: "Supported finding",
    short:
      "The available evidence is sufficient to make this statement as written. That does not mean the statement is causal.",
    long:
      "A finding can be highly defensible and still be purely descriptive. “The Nation is the largest named employer in the county” can be a very strong finding without saying anything about why.",
  },
  exploratoryLead: {
    title: "Worth investigating",
    short:
      "A pattern Grove noticed in the evidence it already holds: a reversal, a gap moving against a benchmark or a step outside the series' own history. It is a question, not a finding.",
    long:
      "Leads are computed by deterministic scans over the same observation rows the figures draw, and they carry the exploratory claim class: a pattern worth investigating, not yet a finding. The numbers that triggered the scan are shown with the lead, and the suggested next step names the analysis that would confirm or refute the pattern. Nothing about a lead says why the pattern exists, and a lead that has not been investigated must not appear in a packet or grant application.",
  },
  highConfidence: {
    title: "High confidence",
    short:
      "The evidence is well matched to this statement's geography, population, period and measure, with no material coverage issue identified.",
    long:
      "Confidence describes the strength and fit of the evidence for the statement as written. It does not mean the estimate is certain, causal or free from sampling and measurement error. Confidence and causality are separate: you can be confident employment rose and have no basis for saying why.",
  },
  needsCoverage: {
    title: "Needs coverage",
    short: "More evidence is needed before Grove treats this statement as adequately supported.",
    long:
      "Grove names what is missing rather than lowering the bar: an absent period, a population the sources do not identify or a public source that only covers a wider geography.",
  },
  studyNarrative: {
    title: "Potential study narrative",
    short:
      "A pattern or question that may be worth investigating in a study. Grove has not treated it as an established finding.",
    long:
      "Narratives help identify useful directions for analysis. They may rest on descriptive patterns, comparisons or contextual evidence, and should not be presented as conclusions until the underlying evidence is evaluated.",
  },
  causalClaim: {
    title: "Causal claim",
    short:
      "A causal claim states that an event, policy, program or activity changed an outcome.",
    long:
      "Grove uses causal language only where the research design supports that interpretation: a difference-in-differences, event study, instrumental variable, regression discontinuity, synthetic control or randomized design, correctly specified with a defensible comparison group. A method's name is not enough.",
  },
  modeledEstimate: {
    title: "Modeled estimate",
    short:
      "This value comes from an economic or statistical model rather than being observed in the source data.",
    long:
      "This is an input-output model estimate. It describes economic activity supported by the modeled expenditure or activity, and should not be read as a causal effect or as a count of jobs created.",
  },
  contextualEvidence: {
    title: "Contextual evidence",
    short:
      "This evidence describes the economic or demographic setting of the analysis.",
    long:
      "It can help explain or interpret a finding, and does not by itself establish an economic impact or a causal relationship. An impact report usually combines model results, descriptive statistics, organization records and benchmarks; those play different evidentiary roles and Grove keeps them distinct.",
  },
  countyProxy: {
    title: "County proxy",
    short:
      "The source does not publish the selected geography, so a wider one stands in.",
    long:
      "The county includes activity outside the study geography and excludes activity inside it that falls outside the county. The figure is usable with the assumption stated.",
  },
});

/**
 * PURPOSE
 * The internal test Grove applies before presenting a finding.
 *
 * Written as a returned structure rather than prose so it can be shown, tested
 * and attached to an export. The six questions are the ones an economist asks
 * when reading someone else's number.
 */
export function interrogateClaim(claim) {
  const meaning = CLAIM_CLASS_MEANING[claim?.claimClass] || CLAIM_CLASS_MEANING.descriptive;
  return {
    observe: claim?.observed ?? null,
    comparing: claim?.comparison ?? null,
    modeled: claim?.claimClass === CLAIM_CLASS.modeled ? claim.text : null,
    canSay: meaning.can,
    cannotSay: meaning.cannot,
    wouldStrengthen: claim?.wouldStrengthen ?? null,
  };
}
