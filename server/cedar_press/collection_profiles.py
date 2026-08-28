"""Machine-readable profiles: the living data dictionary Cedar answers from.

Cedar does not "know" the collections because copy was stuffed into a prompt.
Each profile is assembled here from the material that actually governs the
dataset: the descriptor in ``collections.py`` (what it tracks, its method,
version, vintage), the Overview figures (the only statistics the product
shows), and the construction facts the methods page documents. A number
Cedar quotes is a number the collection itself carries, so it goes stale
with the release, never with a prompt.

Three levels, mirroring how a reader trusts a dataset:

1. what is in it        — tracks, unit of observation, coverage, sources
2. how it was built     — entity resolution, inclusion rules, limitations
3. what the data says   — the headline figures, from the figure specs

``demonstration`` is carried per profile and every statistics answer for a
demonstration collection says so: the three launch collections' numbers are
placeholders until the first real releases, and Cedar repeating them as
findings would be exactly the fabricated confidence this module exists to
prevent. The Owned collection's aggregates are real (nation-supplied) and
are marked accordingly.
"""

from __future__ import annotations

from typing import Any

from cedar_press.collections import (
    COLLECTION_FIGURES,
    LAUNCH_COLLECTION,
)

#: Construction facts per collection, from the methods documentation. These
#: describe process, not numbers: how rows come to exist and what keeps them
#: honest. Sourced from the methods page and the source registry protocol;
#: a change there is a change here.
_CONSTRUCTION: dict[str, dict[str, Any]] = {
    "deals": {
        "unit_of_observation": (
            "One documented transaction (acquisition, property purchase, "
            "project financing, bond issuance or major capital project)."
        ),
        "coverage_start": "2010",
        "entity_resolution_method": (
            "Buyers, sellers, borrowers and issuers are resolved to tribal "
            "governments, tribally owned enterprises, ANCs and NHOs, with "
            "name changes and reorganizations tracked over time so one "
            "enterprise's four names over a decade read as one enterprise."
        ),
        "inclusion_rules": (
            "Announced and closed are labeled separately; a transaction "
            "enters totals only when its status is confirmed against a "
            "primary source. Undisclosed values are counted as transactions "
            "and excluded from dollar totals."
        ),
        "known_limitations": (
            "The most recent quarter is always understated on the confirmed "
            "series, since confirmation trails announcement by one to three "
            "quarters. Inclusion rules are published with every release, so "
            "a missing row is a known gap, not a silent one."
        ),
    },
    "contractors": {
        "unit_of_observation": (
            "One Native-owned contracting entity, with its federal award history."
        ),
        "coverage_start": "2000",
        "entity_resolution_method": (
            "Vendors are matched to parent entities so awards roll up to the "
            "owning tribe, ANC or NHO; provisional matches are labeled until "
            "registration confirms them."
        ),
        "inclusion_rules": (
            "Tribally owned firms, ANC and NHO subsidiaries and 8(a) "
            "participants, collected weekly from SAM, SBA, FPDS and "
            "USAspending, reconciled and versioned quarterly."
        ),
        "known_limitations": (
            "Parent-entity matches can be provisional pending SAM "
            "re-registration; provisional rows are labeled as such rather "
            "than silently included."
        ),
    },
    "funding": {
        "unit_of_observation": (
            "One federal assistance award (grant, loan, direct payment or "
            "insurance) to a tribe or Native organization."
        ),
        "coverage_start": "2001",
        "entity_resolution_method": (
            "Recipients are resolved to the Native entity behind them, so an "
            "award to a subsidiary, a housing authority or a consortium is "
            "attributed to the nation or organization it belongs to, using "
            "the same entity matching as the contractor collection."
        ),
        "inclusion_rules": (
            "USAspending assistance records; the current fiscal year is partial "
            "until the quarterly release lands and is labeled so wherever it appears."
        ),
        "known_limitations": (
            "USAspending publication lag makes current-year figures partial; "
            "the pages say so where the figures appear."
        ),
    },
    "owned": {
        "unit_of_observation": (
            "One individually owned Native business, certified by its nation's "
            "TERO or commerce office."
        ),
        "coverage_start": "2026",
        "entity_resolution_method": (
            "No inference: each business is exactly what its nation's office "
            "certifies it to be. Listings carry the certifying nation, and "
            "nothing overrides what a nation says about its own certified "
            "businesses."
        ),
        "inclusion_rules": (
            "Consent-first: each nation's office shares its certified list "
            "directly and rows appear only under that nation's stated terms. "
            "Until an office confirms publication terms, its businesses "
            "appear in aggregates only, credited to the issuing office."
        ),
        "known_limitations": (
            "Coverage is one nation so far (White Earth Nation, 22 "
            "businesses) with a national outreach wave in progress; the "
            "collection is a census being assembled office by office, not a "
            "finished register."
        ),
    },
}

#: The three launch collections' figures are demonstration data; the Owned
#: aggregates come from a nation-supplied roster.
_DEMONSTRATION: set[str] = {"deals", "contractors", "funding"}


def _figure_for(dataset_id: str):
    return next((f for f in COLLECTION_FIGURES if f.id == dataset_id), None)


def profile_for(dataset_id: str) -> dict[str, Any] | None:
    """The standardized profile, or ``None`` for an unknown collection."""
    dataset = next((d for d in LAUNCH_COLLECTION if d.id == dataset_id), None)
    if dataset is None:
        return None
    construction = _CONSTRUCTION.get(dataset_id, {})
    figure = _figure_for(dataset_id)
    headline = (
        {
            "title": figure.title,
            "basis": figure.basis,
            "points": [
                {"label": p.label, "value": p.value, "compare": p.compare}
                for p in figure.points
            ],
        }
        if figure
        else None
    )
    return {
        "collection_name": dataset.name,
        "collection_id": dataset.id,
        "shelf": dataset.shelf,
        "description": dataset.tracks,
        "coverage_start": construction.get("coverage_start"),
        "coverage_end": dataset.vintage,
        # Honest until a cadence is a commitment, not a plan.
        "update_frequency": None,
        "record_count_label": dataset.rows_label,
        "primary_sources": dataset.sources,
        "unit_of_observation": construction.get("unit_of_observation"),
        "entity_resolution_method": construction.get("entity_resolution_method"),
        "inclusion_rules": construction.get("inclusion_rules"),
        "known_limitations": construction.get("known_limitations"),
        "method": dataset.method,
        "version": dataset.version,
        "vintage": dataset.vintage,
        "last_updated": dataset.updated,
        "demonstration": dataset_id in _DEMONSTRATION,
        "headline_statistics": headline,
    }


def _stats_sentence(profile: dict[str, Any]) -> str | None:
    headline = profile.get("headline_statistics")
    if not headline:
        return None
    points = ", ".join(
        f"{p['label']}: "
        f"{int(p['value']) if float(p['value']).is_integer() else p['value']}"
        for p in headline["points"]
    )
    caveat = (
        " These figures are demonstration data, standing in until the first real release."
        if profile["demonstration"]
        else ""
    )
    return (
        f"{profile['collection_name']} currently holds {profile['record_count_label']}. "
        f"{headline['title']} ({headline['basis']}): {points}.{caveat}"
    )


_CONSTRUCT_WORDS = ("construct", "built", "build", "method", "resolve", "resolution", "how ")
_CONTENT_WORDS = ("cover", "contain", "what is", "what does", "include", "track", "field", "source")
_STATS_WORDS = (
    "headline", "figure", "statistic", "largest", "how many", "count", "record", "number",
)


def answer_from_profile(question: str, dataset_id: str) -> dict[str, str] | None:
    """A profile-grounded answer, or ``None`` when the question needs more.

    Deliberately narrow: this answers from the profile's own fields and never
    composes beyond them. A question about the records themselves is not
    answerable here and returns ``None`` so the route can refuse honestly.
    """
    profile = profile_for(dataset_id)
    if profile is None:
        return None
    asked = question.lower()
    basis = f"{profile['collection_name']} {profile['version']}, vintage {profile['vintage']}"

    if any(word in asked for word in _CONSTRUCT_WORDS):
        parts = [
            profile.get("entity_resolution_method"),
            profile.get("inclusion_rules"),
            f"Known limitations: {profile['known_limitations']}"
            if profile.get("known_limitations")
            else None,
        ]
        return {"answer": " ".join(p for p in parts if p), "basis": basis}
    if any(word in asked for word in _STATS_WORDS):
        sentence = _stats_sentence(profile)
        if sentence:
            return {"answer": sentence, "basis": basis}
    if any(word in asked for word in _CONTENT_WORDS):
        parts = [
            profile["description"],
            f"Unit of observation: {profile['unit_of_observation']}"
            if profile.get("unit_of_observation")
            else None,
            f"Coverage from {profile['coverage_start']}, current vintage "
            f"{profile['vintage']}, last updated {profile['last_updated']}."
            if profile.get("coverage_start")
            else None,
            f"Sources: {profile['primary_sources']}.",
        ]
        return {"answer": " ".join(p for p in parts if p), "basis": basis}
    return None
