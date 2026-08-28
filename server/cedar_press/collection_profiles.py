"""Machine-readable profiles: the living data dictionary Cedar answers from.

Cedar does not "know" the collections because copy was stuffed into a prompt.
Each profile is assembled here from the material that actually governs the
dataset: the descriptor in ``collections.py`` (what it tracks, its method,
version, vintage), the Overview figures (the only statistics the product
shows), and the construction facts the methods page documents. A number
Cedar quotes is a number the collection itself carries, so it goes stale
with the release, never with a prompt.

Four levels, mirroring how a reader trusts a dataset:

1. what is in it        — tracks, unit of observation, coverage, sources
2. how it was built     — entity resolution, inclusion rules, limitations
3. what the data says   — the headline figures, from the figure specs
4. what changed         — the release notes, from the What's New history

``demonstration`` is carried per profile and every statistics answer for a
demonstration collection says so: the three launch collections' numbers are
placeholders until the first real releases, and Cedar repeating them as
findings would be exactly the fabricated confidence this module exists to
prevent. The Owned collection's aggregates are real (nation-supplied) and
are marked accordingly.
"""

from __future__ import annotations

from typing import Any

from cedar_press import press_catalog
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
        "coverage_standard_from": "2010",
        "coverage_full_from": "2010",
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
        "coverage_standard_from": "2010",
        "coverage_full_from": "2000",
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
        "coverage_standard_from": "2010",
        "coverage_full_from": "2001",
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
        "coverage_standard_from": "2026",
        "coverage_full_from": "2026",
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


def _catalog_profile(dataset_id: str) -> dict[str, Any] | None:
    """A profile for a collection the catalog carries but the pilot does not.

    The wider ladder (``pressCatalog.js``, dumped into ``_press_data.json``)
    describes collections whose first release is still in preparation. Cedar
    can honestly answer what such a collection is designed to hold and how its
    records connect to Native entities — that is the catalog's own copy — but
    it has no release, so every release-shaped field is ``None`` and the
    limitations say so. No number is invented for a collection with no data.
    """
    entry = next((c for c in press_catalog.CATALOG if c["id"] == dataset_id), None)
    if entry is None:
        return None
    return {
        "collection_name": entry["name"],
        "collection_id": entry["id"],
        "shelf": entry["shelf"],
        "description": entry["blurb"],
        "coverage_standard_from": str(entry["standardFrom"]),
        "coverage_full_from": str(entry["historyFrom"]),
        "coverage_end": None,
        "update_frequency": None,
        "record_count_label": None,
        "primary_sources": None,
        "unit_of_observation": None,
        "entity_resolution_method": entry.get("linkage"),
        "inclusion_rules": None,
        "known_limitations": (
            "This collection's first release is in preparation: the catalog "
            "entry describes its design, and no records or figures are "
            "published through Cedar yet."
        ),
        "method": None,
        "version": None,
        "vintage": None,
        "last_updated": None,
        "demonstration": False,
        "headline_statistics": None,
    }


def profile_for(dataset_id: str) -> dict[str, Any] | None:
    """The standardized profile, or ``None`` for an unknown collection."""
    dataset = next((d for d in LAUNCH_COLLECTION if d.id == dataset_id), None)
    if dataset is None:
        # The pilot's four datasets carry releases; the rest of the ladder
        # answers from its catalog entry.
        return _catalog_profile(dataset_id)
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
        # Two depths, deliberately: the standard shelf opens the collection
        # from coverage_standard_from; Cedar Press+ opens the full archive
        # back to coverage_full_from. One number here flattened the tier
        # ladder and told a standard reader they had years they do not.
        "coverage_standard_from": construction.get("coverage_standard_from"),
        "coverage_full_from": construction.get("coverage_full_from"),
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


def _fmt(value: Any) -> str:
    return str(int(value)) if float(value).is_integer() else str(value)


def _stats_sentence(profile: dict[str, Any]) -> str | None:
    headline = profile.get("headline_statistics")
    if not headline:
        return None
    # A two-series figure answers with both series: the card draws value and
    # comparison together, and an answer that silently drops the gray line is
    # not the figure's own numbers.
    points = ", ".join(
        f"{p['label']}: {_fmt(p['value'])}"
        + (f" (comparison {_fmt(p['compare'])})" if p.get("compare") is not None else "")
        for p in headline["points"]
    )
    # Every statistics answer carries its standing: demonstration figures say
    # so, and real figures say where they came from.
    caveat = (
        " These figures are demonstration data, standing in until the first real release."
        if profile["demonstration"]
        else f" Source: {profile['primary_sources']}."
    )
    return (
        f"{profile['collection_name']} currently holds {profile['record_count_label']}. "
        f"{headline['title']} ({headline['basis']}): {points}.{caveat}"
    )


# Change words are checked first: "what changed in v4.2" is a question about
# a release, and the What's New page hands Cedar exactly that phrasing.
_CHANGE_WORDS = (
    "changed", "change", "release", "updated", "update", "latest", "what's new", "whats new",
)
# Statistics words are checked before construction words: "how many records"
# is a quantity question, and a bare "how " here once swallowed it into the
# entity-resolution answer.
_CONSTRUCT_WORDS = (
    "construct", "built", "build", "method", "resolve", "resolution",
    "how was", "how is", "how are", "how does",
)
_CONTENT_WORDS = ("cover", "contain", "what is", "what does", "include", "track", "field", "source")
_STATS_WORDS = (
    "headline", "figure", "statistic", "largest", "how many", "count", "record", "number",
)


def _changes_sentence(profile: dict[str, Any], asked: str) -> str:
    """What a release changed, from the release log itself.

    If the question names a version that the log carries, that release
    answers; otherwise the latest one does. Every answer says which release
    it describes, and — like the launch figures — says the notes are
    demonstration content until the first real releases, because a change
    note is a claim about records nobody has shipped yet.
    """
    name = profile["collection_name"]
    release = press_catalog.RELEASES.get(profile["collection_id"])
    if not release or not release.get("history"):
        return (
            f"{name} has no release notes published yet; its release history "
            "starts with the first shipped release."
        )
    history = release["history"]
    entry = next(
        (item for item in history if item["version"].lower() in asked),
        history[0],
    )
    kind = "methodology release" if entry.get("kind") == "methodology" else "data release"
    note = f" Note: {entry['note']}" if entry.get("note") else ""
    changes = " ".join(entry["changed"])
    return (
        f"{name} {entry['version']} ({entry['date']}, {kind}): {changes}{note} "
        "These release notes are demonstration content, standing in until the "
        "first real releases."
    )


def _coverage_sentence(profile: dict[str, Any], full_archive: bool = False) -> str | None:
    """Coverage stated per tier, because the tiers buy different depths.

    ``full_archive`` is whether the asking subscription already opens the
    reconstructed archive: telling a Cedar Press+ reader that "Cedar Press+
    opens the full archive" sells them the plan they are asking from.
    """
    std = profile.get("coverage_standard_from")
    full = profile.get("coverage_full_from")
    if not std:
        return None
    # A catalog-only profile has no release, so no vintage to date it by.
    dated = profile.get("vintage") and profile.get("last_updated")
    tail = (
        f" Current vintage {profile['vintage']}, last updated {profile['last_updated']}."
        if dated
        else ""
    )
    if full and full != std:
        if full_archive:
            return (
                f"Coverage from {full}, the full reconstructed archive, "
                f"which your plan opens.{tail}"
            )
        return (
            f"Coverage from {std} on Cedar Press; Cedar Press+ opens the full "
            f"archive back to {full}.{tail}"
        )
    return f"Coverage from {std} to present.{tail}"


def answer_from_profile(
    question: str, dataset_id: str, full_archive: bool = False
) -> dict[str, str] | None:
    """A profile-grounded answer, or ``None`` when the question needs more.

    Deliberately narrow: this answers from the profile's own fields and never
    composes beyond them. A question about the records themselves is not
    answerable here and returns ``None`` so the route can refuse honestly.
    ``full_archive`` says whether the asking subscription already opens the
    reconstructed archive; the coverage sentence is phrased for the reader
    it is answering.
    """
    profile = profile_for(dataset_id)
    if profile is None:
        return None
    asked = question.lower()
    # A released collection is cited by version and vintage; a catalog-only
    # one has neither, and its basis says what it actually is.
    basis = (
        f"{profile['collection_name']} {profile['version']}, vintage {profile['vintage']}"
        if profile.get("version")
        else f"{profile['collection_name']}, Cedar Press catalog entry"
    )

    if any(word in asked for word in _CHANGE_WORDS):
        return {"answer": _changes_sentence(profile, asked), "basis": basis}
    if any(word in asked for word in _STATS_WORDS):
        sentence = _stats_sentence(profile)
        if sentence:
            return {"answer": sentence, "basis": basis}
        # No figures is an answer, not a routing miss: a reader who asked a
        # quantity question about an unreleased collection should hear that
        # the numbers do not exist yet, not a generic refusal.
        return {
            "answer": (
                f"{profile['collection_name']} has no published figures yet: its "
                "first release is in preparation. Ask what it covers or how it "
                "is being constructed."
            ),
            "basis": basis,
        }
    if any(word in asked for word in _CONSTRUCT_WORDS):
        parts = [
            profile.get("entity_resolution_method"),
            profile.get("inclusion_rules"),
            f"Known limitations: {profile['known_limitations']}"
            if profile.get("known_limitations")
            else None,
        ]
        answer = " ".join(p for p in parts if p)
        if answer:
            return {"answer": answer, "basis": basis}
    if any(word in asked for word in _CONTENT_WORDS):
        parts = [
            profile["description"],
            f"Unit of observation: {profile['unit_of_observation']}"
            if profile.get("unit_of_observation")
            else None,
            _coverage_sentence(profile, full_archive),
            f"Sources: {profile['primary_sources']}." if profile.get("primary_sources") else None,
        ]
        return {"answer": " ".join(p for p in parts if p), "basis": basis}
    return None
