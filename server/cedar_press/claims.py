"""The claim classes a finding carries.

Ported from ``src/features/grove/claims.js``.

Confidence and causality are separate dimensions: a finding can be as certain
as evidence gets and still be purely descriptive. Each finding names its class,
declared by the evidence behind it and never inferred from the sentence.
"""

from __future__ import annotations

__all__ = ["CLAIM_CLASS"]


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
