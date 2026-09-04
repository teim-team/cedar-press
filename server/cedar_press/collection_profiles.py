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
demonstration collection says so: the figure series are placeholders until the
first real releases, and Cedar repeating them as findings would be exactly the
fabricated confidence this module exists to prevent. It is read off the
figure's own ``demonstration`` flag rather than a hand-kept list of ids, so the
two cannot disagree. The Owned collection's aggregates are real
(nation-supplied) and are marked accordingly.

WHAT THE TWELVE HAVE AND WHAT THEY DO NOT
Eight collections joined the shelf when Cedar's measured descriptors replaced
the four hand-written ones. They carry real names, row counts, sources and
methods, and they carry no figures -- Cedar publishes no figure series -- so a
statistics question about them is answered with "no published figures yet"
rather than a number. ``_CONSTRUCTION`` below is hand-written methods copy and
still covers only the original four; the rest read coverage and linkage from
the catalog, which states both for every collection on the ladder, and leave
unit of observation and inclusion rules absent. An empty field a human fills
is honest; a generated sentence that reads like a claim about method is not.
"""

from __future__ import annotations

from collections.abc import Mapping
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

def _figure_for(dataset_id: str):
    return next((f for f in COLLECTION_FIGURES if f.id == dataset_id), None)


def _catalog_entry(dataset_id: str) -> dict[str, Any] | None:
    """The wider ladder's entry for a collection (``pressCatalog.js``)."""
    return next((c for c in press_catalog.CATALOG if c["id"] == dataset_id), None)


def _catalog_profile(dataset_id: str) -> dict[str, Any] | None:
    """A profile for a collection the catalog carries but the pilot does not.

    The wider ladder (``pressCatalog.js``, dumped into ``_press_data.json``)
    describes collections whose first release is still in preparation. Cedar
    can honestly answer what such a collection is designed to hold and how its
    records connect to Native entities — that is the catalog's own copy — but
    it has no release, so every release-shaped field is ``None`` and the
    limitations say so. No number is invented for a collection with no data.
    """
    entry = _catalog_entry(dataset_id)
    if entry is None:
        return None
    return {
        "collection_name": entry["name"],
        "collection_id": entry["id"],
        "shelf": entry["shelf"],
        "description": entry["blurb"],
        **_coverage_fields(entry),
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
    # The eight collections that joined the shelf with Cedar's real descriptors
    # have no construction entry: `_CONSTRUCTION` is hand-written methods copy
    # and nothing measured it. Coverage and linkage are the exception, because
    # the catalog already states both for every collection on the ladder, so
    # they are read from there rather than left blank or guessed. Everything
    # else stays absent: a unit of observation nobody wrote is not a field this
    # module is entitled to fill.
    catalog = _catalog_entry(dataset_id) or {}
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
        # One depth, because there is one axis. This used to be a pair --
        # a 2010 window for Cedar Press and the archive behind it for
        # Cedar Press+ -- and the pair is retired (see `pressCatalog.js`).
        # The value comes from the catalog and nowhere else: it is a claim
        # to a paying subscriber and it is measured against the delivered
        # file, so a second hand-written copy could only drift from it.
        **_coverage_fields(catalog),
        "coverage_end": dataset.vintage,
        # Honest until a cadence is a commitment, not a plan.
        "update_frequency": None,
        "record_count_label": dataset.rows_label,
        "primary_sources": dataset.sources,
        "unit_of_observation": construction.get("unit_of_observation"),
        "entity_resolution_method": construction.get("entity_resolution_method")
        or catalog.get("linkage"),
        "inclusion_rules": construction.get("inclusion_rules"),
        "known_limitations": construction.get("known_limitations"),
        "method": dataset.method,
        "version": dataset.version,
        "vintage": dataset.vintage,
        "last_updated": dataset.updated,
        # Read off the figure rather than a hand-kept id list. The list said
        # which three collections were demonstration data and had to be edited
        # by hand every time a figure's standing changed; the figure now
        # carries its own answer, so the two cannot disagree. A collection with
        # no figure has nothing to flag.
        "demonstration": bool(figure and figure.demonstration),
        "headline_statistics": headline,
    }


def _str_or_none(value: Any) -> str | None:
    return None if value is None else str(value)


def _coverage_fields(catalog: Mapping[str, Any]) -> dict[str, Any]:
    """The catalog's coverage declaration, flattened onto a profile.

    Two shapes, because two of these collections are rosters rather than
    series: their sources publish who is certified or exempt now and archive
    nothing behind it, so they have a capture date and no first year. A
    profile field that were always a year would force one of them to invent
    one, which is the defect this shape exists to prevent. ``coverage_from``
    is therefore ``None`` on a roster, and every reader of it has to cope.
    """
    coverage = catalog.get("coverage") or {}
    kind = coverage.get("kind")
    return {
        "coverage_kind": kind,
        "coverage_from": _str_or_none(coverage.get("from")),
        "coverage_captured": coverage.get("captured"),
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
    it describes. The log is derived from the manifest (``pressReleases.js``,
    dumped into ``_press_data.json``), so a note here is a measured fact about
    the shipped release rather than the demonstration copy it used to be.
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
    return f"{name} {entry['version']} ({entry['date']}, {kind}): {changes}{note}"


def _coverage_sentence(profile: dict[str, Any]) -> str | None:
    """Coverage, which is one sentence for every tier and two for every shape.

    It used to be three sentences chosen by a ``full_archive`` flag: Cedar
    Press opened a collection from 2010 and Cedar Press+ opened the archive
    behind it, so Cedar had to know who was asking before it could say what a
    collection covered. The window was retired on 2026-09-02, so the reader
    does not enter into it.

    What does enter into it is whether the collection is a series or a
    roster. Answering "coverage from 1992 to present" for a list of live TERO
    certifications would be Cedar stating a 34-year span that no certifying
    office keeps, which is the failure this module exists to prevent.
    """
    # A catalog-only profile has no release, so no vintage to date it by.
    dated = profile.get("vintage") and profile.get("last_updated")
    tail = (
        f" Current vintage {profile['vintage']}, last updated {profile['last_updated']}."
        if dated
        else ""
    )
    if profile.get("coverage_kind") == "roster":
        captured = profile.get("coverage_captured")
        if not captured:
            return None
        return (
            "This is a current roster rather than a series: it states who is "
            f"on the list as of {captured}, and the sources behind it do not "
            f"publish the superseded lists.{tail}"
        )
    coverage_from = profile.get("coverage_from")
    if not coverage_from:
        return None
    return f"Coverage from {coverage_from} to present.{tail}"


def answer_from_profile(question: str, dataset_id: str) -> dict[str, str] | None:
    """A profile-grounded answer, or ``None`` when the question needs more.

    Deliberately narrow: this answers from the profile's own fields and never
    composes beyond them. A question about the records themselves is not
    answerable here and returns ``None`` so the route can refuse honestly.

    It took a ``full_archive`` flag until 2026-09-02, when the year cap that
    made coverage tier-dependent was retired. Nothing here varies by plan any
    more, so nothing here needs to know the plan.
    """
    profile = profile_for(dataset_id)
    if profile is None:
        return None
    asked = question.lower()
    # A released collection is cited by version, and by vintage when it has
    # one; a catalog-only collection has neither, and its basis says what it
    # actually is. Vintage is appended only when present: no collection states
    # one today, and "vintage None" was what unconditional interpolation
    # printed -- a basis line naming a measurement that does not exist.
    if profile.get("version"):
        vintage = f", vintage {profile['vintage']}" if profile.get("vintage") else ""
        basis = f"{profile['collection_name']} {profile['version']}{vintage}"
    else:
        basis = f"{profile['collection_name']}, Cedar Press catalog entry"

    if any(word in asked for word in _CHANGE_WORDS):
        return {"answer": _changes_sentence(profile, asked), "basis": basis}
    if any(word in asked for word in _STATS_WORDS):
        sentence = _stats_sentence(profile)
        if sentence:
            return {"answer": sentence, "basis": basis}
        # No figures is an answer, not a routing miss: a reader who asked a
        # quantity question should hear that the figure series does not exist,
        # not a generic refusal. Codex, PR #51: "no published figures" and "no
        # release" are two facts, and this sentence ran them together, so a
        # shipped collection with a version, a date and a row count was
        # described as still in preparation while /press/releases served its
        # release. A shipped collection says what it holds; only a collection
        # with no release says it is in preparation.
        if profile.get("version"):
            held = (
                f" Its current release is {profile['version']}"
                f" ({profile['last_updated']}), holding {profile['record_count_label']}."
                if profile.get("record_count_label")
                else f" Its current release is {profile['version']} ({profile['last_updated']})."
            )
            return {
                "answer": (
                    f"{profile['collection_name']} has no published figures yet: Cedar "
                    f"publishes no figure series for it.{held} Ask what it covers, "
                    "what changed in the release or how it is constructed."
                ),
                "basis": basis,
            }
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
            _coverage_sentence(profile),
            f"Sources: {profile['primary_sources']}." if profile.get("primary_sources") else None,
        ]
        return {"answer": " ".join(p for p in parts if p), "basis": basis}
    return None
