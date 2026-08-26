"""Cedar Grove: what may be said about a piece of evidence.

Ported from ``src/features/grove/claims.js``.

Grove's statements do not stay in Grove. They go into council packets, grant
applications, board presentations and advocacy materials, where a sentence that
quietly upgrades a correlation into a cause becomes a claim the organization has
to defend in public. Finding the pattern is the easy half. The half that matters
is telling someone what they can responsibly say about it.

**The load-bearing idea: confidence and causality are separate dimensions.** You
can be as certain as evidence ever gets that employment rose 25 percent, and have
no basis whatsoever for saying why. A finding can be maximally defensible and
purely descriptive. Grove must make that distinction almost impossible for a
reader to miss, which means it has to be impossible for Grove itself to blur.

The rules are deliberately conservative. A phrase that is sometimes fine and
often misleading is treated as forbidden, because the cost of a false positive is
a slightly flatter sentence and the cost of a false negative is a wrong claim in
a public document.

Class is declared by the evidence recipe, never inferred from the sentence. Grove
does not promote a claim to a stronger class on its own.

Known limit, carried over: the linter matches phrases, not grammar. "The data
show employment increased" and "The data show the expansion increased employment"
differ by their subject rather than by a keyword, and only the second is causal.
It catches the common cases and is not a parser.

ECONOMICS REVIEW
    The verb lists and the class distinctions are a starting framework, not a
    settled house style. In particular the terminology around input-output
    estimates and "supported" activity is Laurel's and Isabella's to settle.

HAVALA REVIEW
    The evidence classifications themselves, and the rule that a claim inherits
    its class from the recipe rather than from the strength of the pattern.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping
from types import MappingProxyType
from typing import Any, NamedTuple

__all__ = [
    "CLAIM_CLASS",
    "CLAIM_CLASS_LABEL",
    "CLAIM_CLASS_MEANING",
    "DESCRIPTIVE_VERBS",
    "HELP",
    "MODELED_VERBS",
    "Correction",
    "LintResult",
    "Violation",
    "correct_overstatement",
    "interrogate_claim",
    "lint_claim",
    "strongest_claim_class_for",
]


class _ClaimClass:
    """The claim taxonomy, as attributes so a typo raises instead of returning None.

    Seven classes, ordered from what was observed to what was identified. The
    order matters: Grove may always describe a claim in a weaker class than its
    evidence allows, and never in a stronger one.

    A ``dict`` would have been the direct translation of the frozen JavaScript
    object, and ``CLAIM_CLASS["desciptive"]`` would then be a ``KeyError`` at
    runtime in whichever branch nobody exercised. Attributes are checked by the
    type checker instead.
    """

    #: What was observed, in the data, as recorded.
    descriptive = "descriptive"
    #: A difference between groups, places or periods.
    comparative = "comparative"
    #: Two things move together or are statistically related.
    associational = "associational"
    #: Produced by a model rather than observed.
    modeled = "modeled"
    #: An identified effect, from a design that supports causal inference.
    causal = "causal"
    #: Establishes the setting rather than proving a finding.
    contextual = "contextual"
    #: A pattern worth investigating, not yet a finding.
    exploratory = "exploratory"

    def values(self) -> tuple[str, ...]:
        """Every class, in taxonomy order."""
        return (
            self.descriptive,
            self.comparative,
            self.associational,
            self.modeled,
            self.causal,
            self.contextual,
            self.exploratory,
        )

    def __contains__(self, value: object) -> bool:
        return value in self.values()


CLAIM_CLASS = _ClaimClass()

CLAIM_CLASS_LABEL: Mapping[str, str] = MappingProxyType(
    {
        "descriptive": "Descriptive",
        "comparative": "Comparative",
        "associational": "Associational",
        "modeled": "Modeled estimate",
        "causal": "Causal",
        "contextual": "Contextual",
        "exploratory": "Exploratory",
    }
)

# One-line statements of what each class can and cannot carry. These are what the
# interface shows when a reader asks what a class means.
CLAIM_CLASS_MEANING: Mapping[str, Mapping[str, str]] = MappingProxyType(
    {
        "descriptive": MappingProxyType(
            {
                "can": "State what was observed, for the stated geography, population and period.",
                "cannot": "Say why it happened, or that anything caused it.",
            }
        ),
        "comparative": MappingProxyType(
            {
                "can": "State that one group, place or period differs from another.",
                "cannot": "Say why the difference exists, or attribute it to either side.",
            }
        ),
        "associational": MappingProxyType(
            {
                "can": "State that two things move together, or that one occurred during the other.",
                "cannot": "Say that one produced the other.",
            }
        ),
        "modeled": MappingProxyType(
            {
                "can": "State what a model estimates, naming the model and its assumptions.",
                "cannot": "Present the estimate as an observed count, or as an identified effect.",
            }
        ),
        "causal": MappingProxyType(
            {
                "can": "State an estimated effect, naming the design and the comparison group.",
                "cannot": "Be used because a pattern looks convincing. The design has to support it.",
            }
        ),
        "contextual": MappingProxyType(
            {
                "can": "Describe the economic or demographic setting the analysis sits in.",
                "cannot": "Stand in for the impact finding itself.",
            }
        ),
        "exploratory": MappingProxyType(
            {
                "can": "Raise a question or pattern worth investigating.",
                "cannot": "Be presented as a conclusion.",
            }
        ),
    }
)


# ---------------------------------------------------------------------------
# Language rules
# ---------------------------------------------------------------------------

# Verbs and phrases that assert cause. Forbidden anywhere except a claim whose
# class is causal.
#
# "impact of" and "effect of" are on the list deliberately. They are ordinary
# words in this industry and they are causal claims: the effect of X on Y is
# precisely the thing an input-output model does not identify.
# Each verb is matched in every inflection: past, present, base and -ing.
# "The project will create 500 jobs" is the canonical wording of an impact
# pitch, and a linter that catches "created" while passing "will create" is a
# linter that misses the sentence most likely to be written.
_CAUSAL_PHRASES: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\bcaus(?:es|ed|e|ing)\b", re.I), "caused"),
    (re.compile(r"\b(?:leads?|led|leading) to\b", re.I), "led to"),
    (re.compile(r"\bresult(?:s|ed|ing)? in\b", re.I), "resulted in"),
    (re.compile(r"\bproduc(?:es|ed|e|ing)\b", re.I), "produced"),
    (re.compile(r"\bgenerat(?:es|ed|e|ing)\b", re.I), "generated"),
    (re.compile(r"\bcreat(?:es|ed|e|ing)\b", re.I), "created"),
    (re.compile(r"\b(?:drives?|drove|driven|driving)\b", re.I), "drove"),
    (re.compile(r"\bbecause of\b", re.I), "because of"),
    (re.compile(r"\bdue to\b", re.I), "due to"),
    (re.compile(r"\bthanks to\b", re.I), "thanks to"),
    (re.compile(r"\beffect of\b", re.I), "effect of"),
    (re.compile(r"\bimpact of\b", re.I), "impact of"),
    (re.compile(r"\battributable to\b", re.I), "attributable to"),
    (re.compile(r"\bresponsible for\b", re.I), "responsible for"),
    (re.compile(r"\bboost(?:s|ed|ing)?\b", re.I), "boosted"),
    (re.compile(r"\bspur(?:s|red|ring)?\b", re.I), "spurred"),
)

# Claims of proof. Forbidden in every class, including causal.
#
# Statistical and economic evidence supports, estimates, indicates, documents or
# is consistent with a proposition. It does not prove one.
_PROOF_PHRASES: tuple[tuple[re.Pattern[str], str], ...] = (
    # "prov(es?|ed|ing)" and not "prov": "provide" and "province" are
    # innocent, and "proved" is the past-tense form that slipped through.
    (re.compile(r"\bprov(?:es?|ed|ing)\b", re.I), "proves"),
    (re.compile(r"\bproof\b", re.I), "proof"),
    (re.compile(r"\bproven\b", re.I), "proven"),
    (re.compile(r"\bconclusively\b", re.I), "conclusively"),
    (re.compile(r"\bdefinitively\b", re.I), "definitively"),
    (re.compile(r"\bconfirm(?:s|ed|ing)? that\b", re.I), "confirms that"),
    (re.compile(r"\bundeniabl", re.I), "undeniably"),
    (re.compile(r"\bguarantee(?:s|d|ing)?\b", re.I), "guarantees"),
)

# Phrases presenting a modeled estimate as an observed count. Forbidden on a
# modeled claim, which is where they are most tempting and most wrong: an
# input-output model estimates activity supported by a level of spending. It does
# not count jobs anyone created.
#
# "Value added" is exempted at scan time: see the mask in ``lint_claim``.
# "counted" stays past-tense-only on purpose: "count" and "counts" are
# ordinary nouns in this domain ("establishment counts") and forbidding them
# would flag honest sentences constantly.
_OBSERVATION_PHRASES: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\bcreat(?:es|ed|e|ing)\b", re.I), "created"),
    (re.compile(r"\badd(?:s|ed|ing)?\b", re.I), "added"),
    (re.compile(r"\b(?:brings?|brought|bringing)\b", re.I), "brought"),
    (re.compile(r"\bactual\b", re.I), "actual"),
    (re.compile(r"\bcounted\b", re.I), "counted"),
)

#: Verbs that are safe for a purely descriptive statement.
DESCRIPTIVE_VERBS: tuple[str, ...] = (
    "increased",
    "decreased",
    "rose",
    "fell",
    "was",
    "were",
    "accounted for",
    "represented",
    "reported",
    "employed",
    "earned",
    "lived",
    "occurred",
    "recorded",
    "documented",
)

#: Verbs that keep a modeled result honest about being modeled.
MODELED_VERBS: tuple[str, ...] = (
    "estimates",
    "supported",
    "associated with",
    "modeled",
    "is estimated at",
)

# Which phrase families each class forbids.
_FORBIDDEN_BY_CLASS: Mapping[str, tuple[tuple[tuple[re.Pattern[str], str], ...], ...]] = MappingProxyType(
    {
        "descriptive": (_CAUSAL_PHRASES, _PROOF_PHRASES),
        "comparative": (_CAUSAL_PHRASES, _PROOF_PHRASES),
        "associational": (_CAUSAL_PHRASES, _PROOF_PHRASES),
        "modeled": (_CAUSAL_PHRASES, _PROOF_PHRASES, _OBSERVATION_PHRASES),
        "contextual": (_CAUSAL_PHRASES, _PROOF_PHRASES),
        "exploratory": (_CAUSAL_PHRASES, _PROOF_PHRASES),
        # A causal claim may say caused. It still may not say proved.
        "causal": (_PROOF_PHRASES,),
    }
)


def strongest_claim_class_for(evidence_class: object) -> str:
    """The strongest claim a kind of evidence could support.

    Bridges the two class vocabularies Grove carries rather than merging them.
    They describe different things and both are correct: an *evidence* class is a
    property of a recipe, meaning what kind of evidence this source and method
    produce. A *claim* class is a property of a statement, meaning what a
    particular sentence asserts. One recipe supports several statements, and a
    comparative recipe may be used to make a merely descriptive claim.

    The mapping is therefore a ceiling, not an equivalence. Grove may always
    state something weaker. Without it, an evidence object with no claim class
    attached would default to descriptive and a modeled impact would lose the
    label that keeps it honest.

    ``modeled_impact`` maps to modeled and not to causal deliberately. An
    input-output result is an estimate produced under assumptions, and no part of
    the method identifies an effect.

    ECONOMICS REVIEW
        Confirm the ceiling for causal. A recipe is currently allowed to declare
        itself causal, which trusts the recipe author. The alternative is to
        require an identification strategy in the recipe metadata before the
        causal class is reachable at all, so causal is earned by design rather
        than by declaration.
    """
    mapping = {
        "comparative": CLAIM_CLASS.comparative,
        "modeled_impact": CLAIM_CLASS.modeled,
        "causal": CLAIM_CLASS.causal,
        "descriptive": CLAIM_CLASS.descriptive,
    }
    # An unrecognized class must not silently become a strong one. Grove reports
    # the weakest class it has, which is the safe failure.
    return (
        mapping.get(evidence_class, CLAIM_CLASS.descriptive)
        if isinstance(evidence_class, str)
        else CLAIM_CLASS.descriptive
    )


class Violation(NamedTuple):
    """One phrase that broke a rule, and why it is a rule."""

    phrase: str
    kind: str
    why: str

    def as_dict(self) -> dict[str, str]:
        """The JS-shaped mapping, for comparing against the reference build."""
        return {"phrase": self.phrase, "kind": self.kind, "why": self.why}


class LintResult(NamedTuple):
    """Whether a statement's language matches its class."""

    ok: bool
    violations: tuple[Violation, ...]

    def as_dict(self) -> dict[str, Any]:
        """The JS-shaped mapping, for comparing against the reference build."""
        return {"ok": self.ok, "violations": [v.as_dict() for v in self.violations]}


def lint_claim(text: object, claim_class: object) -> LintResult:
    """Check a statement against the class of evidence behind it.

    Used two ways: as a guard on anything Grove generates, and as a test the
    suite runs over every finding, so an overstatement cannot ship.
    """
    statement = "" if text is None else str(text)
    key = claim_class if isinstance(claim_class, str) else ""
    families = _FORBIDDEN_BY_CLASS.get(key, (_CAUSAL_PHRASES, _PROOF_PHRASES))
    violations: list[Violation] = []

    # The accounting term "value added" is a fixed noun phrase, not a claim
    # that jobs were added; scan a copy with it masked so GDP-contribution
    # findings pass while "added 400 jobs" still gets caught.
    scanned = _VALUE_ADDED.sub("value contribution", statement)
    for family in families:
        for pattern, phrase in family:
            if not pattern.search(scanned):
                continue
            if family is _PROOF_PHRASES:
                violations.append(
                    Violation(
                        phrase,
                        "proof",
                        "Evidence supports, estimates, indicates or documents a proposition. "
                        "It does not prove one.",
                    )
                )
            elif family is _OBSERVATION_PHRASES:
                violations.append(
                    Violation(
                        phrase,
                        "modeled-as-observed",
                        f'A modeled estimate is not an observed count, so "{phrase}" overstates '
                        f"what the model measured.",
                    )
                )
            else:
                label = CLAIM_CLASS_LABEL.get(key, "").lower() or "this"
                violations.append(
                    Violation(
                        phrase,
                        "causal",
                        f'"{phrase}" asserts cause, and {label} evidence does not identify one.',
                    )
                )
    return LintResult(not violations, tuple(violations))


# ---------------------------------------------------------------------------
# Correcting overstatement
# ---------------------------------------------------------------------------


class _Rewrite(NamedTuple):
    """A valency-safe substitution: same grammatical shape in, same shape out."""

    when: re.Pattern[str]
    substitutions: tuple[tuple[re.Pattern[str], str | Callable[[re.Match[str]], str]], ...]
    note: str
    for_class: str | None = None

    def apply(self, text: str) -> str:
        """Run every substitution in order."""
        for pattern, replacement in self.substitutions:
            text = pattern.sub(replacement, text)
        return text


# Rewrites that keep the observation and drop the unsupported attribution.
#
# Every entry is valency-safe: the replacement takes the same grammatical shape
# as the phrase it replaces, so the sentence stays grammatical. That constraint
# is why the list is short.
#
# Deliberately absent: "caused". "The casino caused employment to rise" cannot be
# repaired by swapping a verb, because the causative construction ("A caused B to
# C") has no same-shape non-causal equivalent. Substituting one produces "The
# casino coincided with employment to rise", which is worse than saying nothing.
# Those cases get guidance instead of a rewrite.
# The substitutions keep the sentence's tense. "Created" must become
# "supported" and "will create" must become "will support"; a rewrite that
# flattens every inflection to the past tense mangles the prospective
# sentence it most needs to repair.
_VALUE_ADDED = re.compile(r"\bvalue[- ]added\b", re.I)


def _guarded_supported(replacement: str) -> Callable[[re.Match[str]], str]:
    """A replacer that leaves fixed terms and passive uses alone.

    "Value added" is an accounting noun phrase the finite estimated phrase
    would mangle, and a passive or participial use ("Jobs created by the
    expansion") cannot take a finite phrase either; left as found, the linter
    still flags the passive and no automatic rewrite is offered.
    """

    def _replace(match: re.Match[str]) -> str:
        before = match.string[: match.start()]
        after = match.string[match.end() :]
        if re.search(r"\bvalue[- ]$", before, re.I):
            return match.group(0)
        if re.match(r"\s+by\b", after, re.I):
            return match.group(0)
        return replacement

    return _replace


_REWRITES: tuple[_Rewrite, ...] = (
    # Modeled employment presented as job creation. The single most common
    # overstatement in this industry, and a clean verb-for-verb swap.
    # The rewrite keeps the estimate explicit: "supported 400 jobs" alone
    # still states the modeled result as fact, trading one prohibited claim
    # for another. Each form maps to an explicitly estimated phrasing in its
    # own tense.
    _Rewrite(
        when=re.compile(r"\b(creates?|created|creating|adds?|added|adding)\b", re.I),
        substitutions=(
            (re.compile(r"\b(created|added)\b", re.I), _guarded_supported("is estimated to have supported")),
            (re.compile(r"\b(creates|adds)\b", re.I), _guarded_supported("is estimated to support")),
            (re.compile(r"\b(creating|adding)\b", re.I), _guarded_supported("supporting an estimated")),
            (re.compile(r"\b(create|add)\b", re.I), _guarded_supported("support an estimated")),
        ),
        note='"Estimated to support" keeps both truths: the model estimates, and what it '
        "measures is activity sustained by a level of spending, not jobs anyone created.",
        for_class=CLAIM_CLASS.modeled,
    ),
    # Preposition for preposition.
    _Rewrite(
        when=re.compile(r"\b(because of|due to|thanks to|attributable to)\b", re.I),
        substitutions=(
            (
                re.compile(r"\b(because of|due to|thanks to|attributable to)\b", re.I),
                "during the same period as",
            ),
        ),
        note="The timing is documented. The attribution is not.",
    ),
    # Verb for verb, both taking a noun-phrase object. The -ing forms are
    # deliberately absent: "leading to X" has no substitution that stays
    # grammatical, so those sentences take the no-suggestion path instead.
    _Rewrite(
        when=re.compile(
            r"\b(leads? to|led to|results? in|resulted in|produces?|produced|generates?|generated)\b",
            re.I,
        ),
        substitutions=(
            (re.compile(r"\b(led to|resulted in|produced|generated)\b", re.I), "was accompanied by"),
            (re.compile(r"\b(leads to|results in|produces|generates)\b", re.I), "is accompanied by"),
            (re.compile(r"\b(lead to|result in|produce|generate)\b", re.I), "be accompanied by"),
        ),
        note="The evidence shows the two together. Attributing one to the other needs a design "
        "that identifies the effect.",
    ),
    _Rewrite(
        when=re.compile(r"\b(prov(?:es?|ed|ing)|proven|conclusively|definitively)\b", re.I),
        substitutions=(
            (re.compile(r"\bproves\b", re.I), "indicates"),
            (re.compile(r"\bproved\b", re.I), "indicated"),
            (re.compile(r"\bprove\b", re.I), "indicate"),
            (re.compile(r"\bproving\b", re.I), "indicating"),
            (re.compile(r"\bproven\b", re.I), "documented"),
            (re.compile(r"\s*\b(conclusively|definitively)\b", re.I), ""),
        ),
        note="Evidence indicates, documents or is consistent with. Proof is a bar statistical "
        "evidence does not clear.",
    ),
)

# The causative construction, which cannot be repaired by substitution.
_CAUSATIVE = re.compile(r"\b(caus(?:es|ed|e|ing)|drives?|drove|driven|driving)\b", re.I)

_GUIDANCE = (
    "State the observation and the timing separately, and leave the attribution out: say what "
    "changed, over what period, and that the two occurred together."
)


class Correction(NamedTuple):
    """The result of checking a sentence for overstatement.

    ``suggestion`` is ``None`` where a substitution would not keep the sentence
    grammatical. In that case ``guidance`` says what the sentence would have to
    become, which is more use than a mangled rewrite the author then repairs.
    """

    overstated: bool
    original: str
    suggestion: str | None
    why: str | None = None
    note: str | None = None
    guidance: str | None = None
    violations: tuple[Violation, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        """The JS-shaped mapping, for comparing against the reference build."""
        if not self.overstated:
            return {"overstated": False, "original": self.original, "suggestion": self.suggestion}
        return {
            "overstated": True,
            "original": self.original,
            "suggestion": self.suggestion,
            "why": self.why,
            "note": self.note,
            "guidance": self.guidance,
            "violations": [v.as_dict() for v in self.violations],
        }


def correct_overstatement(text: object, claim_class: object) -> Correction:
    """Turn an overstated sentence into one the evidence supports.

    This is the behaviour Cedar needs. A user writes "The new casino caused
    county employment to increase 14 percent" and Grove holds only a descriptive
    employment trend. Cedar should not reinforce the sentence; it should say what
    the evidence does show and offer the defensible version.
    """
    statement = "" if text is None else str(text)
    result = lint_claim(statement, claim_class)
    if result.ok:
        return Correction(overstated=False, original=statement, suggestion=statement)

    # Every matching family is applied, not just the first: a sentence carrying
    # both a proof claim and a causal verb needs both repaired, and a suggestion
    # that fixes one while shipping the other is worse than none.
    applied: list[_Rewrite] = []
    candidate = statement
    for entry in _REWRITES:
        if not entry.when.search(candidate):
            continue
        if entry.for_class is not None and entry.for_class != claim_class:
            continue
        candidate = entry.apply(candidate)
        applied.append(entry)

    # A suggestion is offered only when the substitution keeps the sentence
    # grammatical AND the result passes the linter for its own class. Where it
    # would not, Grove says what the evidence does show and what the sentence
    # would have to become.
    can_rewrite = bool(applied) and not _CAUSATIVE.search(statement) and lint_claim(candidate, claim_class).ok

    return Correction(
        overstated=True,
        original=statement,
        suggestion=candidate if can_rewrite else None,
        # What the evidence does support, stated before the correction so the
        # reader is not simply told no.
        why=result.violations[0].why,
        note=applied[0].note if can_rewrite else None,
        guidance=None if can_rewrite else _GUIDANCE,
        violations=result.violations,
    )


# ---------------------------------------------------------------------------
# The methods layer behind every "?"
# ---------------------------------------------------------------------------

# Contextual help copy. Not glossary entries: each one exists to stop a specific
# misreading, and the most important is `high_confidence`, because confidence
# describes how well the evidence fits the statement and says nothing at all
# about cause.
HELP: Mapping[str, Mapping[str, str]] = MappingProxyType(
    {
        "supportedFinding": MappingProxyType(
            {
                "title": ("Supported finding"),
                "short": (
                    "The available evidence is sufficient to make this statement as written. That does "
                    "not mean the statement is causal."
                ),
                "long": (
                    "A finding can be highly defensible and still be purely descriptive. “The Nation is "
                    "the largest named employer in the county” can be a very strong finding without "
                    "saying anything about why."
                ),
            }
        ),
        "exploratoryLead": MappingProxyType(
            {
                "title": "Worth investigating",
                "short": (
                    "A pattern Grove noticed in the evidence it already holds: a reversal, a gap"
                    " moving against a benchmark or a step outside the series' own history. It is"
                    " a question, not a finding."
                ),
                "long": (
                    "Leads are computed by deterministic scans over the same observation rows the"
                    " figures draw, and they carry the exploratory claim class: a pattern worth"
                    " investigating, not yet a finding. The numbers that triggered the scan are"
                    " shown with the lead, and the suggested next step names the analysis that"
                    " would confirm or refute the pattern. Nothing about a lead says why the"
                    " pattern exists, and a lead that has not been investigated must not appear in"
                    " a packet or grant application."
                ),
            }
        ),
        "highConfidence": MappingProxyType(
            {
                "title": ("High confidence"),
                "short": (
                    "The evidence is well matched to this statement's geography, population, period and "
                    "measure, with no material coverage issue identified."
                ),
                "long": (
                    "Confidence describes the strength and fit of the evidence for the statement as "
                    "written. It does not mean the estimate is certain, causal or free from sampling and "
                    "measurement error. Confidence and causality are separate: you can be confident "
                    "employment rose and have no basis for saying why."
                ),
            }
        ),
        "needsCoverage": MappingProxyType(
            {
                "title": ("Needs coverage"),
                "short": (
                    "More evidence is needed before Grove treats this statement as adequately supported."
                ),
                "long": (
                    "Grove names what is missing rather than lowering the bar: an absent period, a "
                    "population the sources do not identify or a public source that only covers a wider "
                    "geography."
                ),
            }
        ),
        "studyNarrative": MappingProxyType(
            {
                "title": ("Potential study narrative"),
                "short": (
                    "A pattern or question that may be worth investigating in a study. Grove has not "
                    "treated it as an established finding."
                ),
                "long": (
                    "Narratives help identify useful directions for analysis. They may rest on "
                    "descriptive patterns, comparisons or contextual evidence, and should not be "
                    "presented as conclusions until the underlying evidence is evaluated."
                ),
            }
        ),
        "causalClaim": MappingProxyType(
            {
                "title": ("Causal claim"),
                "short": (
                    "A causal claim states that an event, policy, program or activity changed an outcome."
                ),
                "long": (
                    "Grove uses causal language only where the research design supports that "
                    "interpretation: a difference-in-differences, event study, instrumental variable, "
                    "regression discontinuity, synthetic control or randomized design, correctly "
                    "specified with a defensible comparison group. A method's name is not enough."
                ),
            }
        ),
        "modeledEstimate": MappingProxyType(
            {
                "title": ("Modeled estimate"),
                "short": (
                    "This value comes from an economic or statistical model rather than being observed in "
                    "the source data."
                ),
                "long": (
                    "This is an input-output model estimate. It describes economic activity supported by "
                    "the modeled expenditure or activity, and should not be read as a causal effect or as "
                    "a count of jobs created."
                ),
            }
        ),
        "contextualEvidence": MappingProxyType(
            {
                "title": ("Contextual evidence"),
                "short": ("This evidence describes the economic or demographic setting of the analysis."),
                "long": (
                    "It can help explain or interpret a finding, and does not by itself establish an "
                    "economic impact or a causal relationship. An impact report usually combines model "
                    "results, descriptive statistics, organization records and benchmarks; those play "
                    "different evidentiary roles and Grove keeps them distinct."
                ),
            }
        ),
        "countyProxy": MappingProxyType(
            {
                "title": ("County proxy"),
                "short": ("The source does not publish the selected geography, so a wider one stands in."),
                "long": (
                    "The county includes activity outside the study geography and excludes activity "
                    "inside it that falls outside the county. The figure is usable with the assumption "
                    "stated."
                ),
            }
        ),
    }
)


def interrogate_claim(claim: Mapping[str, Any] | None) -> dict[str, Any]:
    """The internal test Grove applies before presenting a finding.

    Returned as a structure rather than prose so it can be shown, tested and
    attached to an export. The questions are the ones an economist asks when
    reading someone else's number.
    """
    record = claim if isinstance(claim, Mapping) else {}
    key = record.get("claimClass")
    meaning = CLAIM_CLASS_MEANING.get(key if isinstance(key, str) else "", CLAIM_CLASS_MEANING["descriptive"])
    return {
        "observe": record.get("observed"),
        "comparing": record.get("comparison"),
        "modeled": record.get("text") if key == CLAIM_CLASS.modeled else None,
        "canSay": meaning["can"],
        "cannotSay": meaning["cannot"],
        "wouldStrengthen": record.get("wouldStrengthen"),
    }
