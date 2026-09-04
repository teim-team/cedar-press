"""The shelf page's view model, composed in Python from Python.

WHY THIS PAGE
    ``docs/PYTHON_FIRST_SITE.md`` argues that the site should be rendered from
    Python because several modules are currently written twice, once per
    language, and have to be kept value-for-value in agreement. An argument
    like that is worth exactly as much as its demonstration, so this is the
    demonstration: the shelf, the page that reads more of the mirrored modules
    than any other, rendered end to end without JavaScript.

    ``src/pages/grove/PressShelf.jsx`` reads five modules that have Python
    counterparts -- ``collection.js``, ``pressAccess.js``, ``pressCatalog.js``,
    ``pressReleases.js`` and ``pressDownload.js``. This module reads the Python
    side of all five (``collections.py``, ``repository.py``,
    ``press_catalog.py``) and nothing else. Whatever the page shows, Python
    already knew.

WHAT IT DELIBERATELY DOES NOT SHOW
    The tier ladder's marketing copy -- each band's product name, price,
    question and promise -- exists only in ``pressCatalog.js``'s
    ``PRESS_TIERS``, which ``scripts/dump-press.mjs`` does not dump. It is not
    retyped here. Adding a seventh hand-maintained mirror to a page whose
    argument is that six is too many would refute the page. The template says
    so where the copy would sit, and moving that ladder into Python is a named
    step in the plan rather than a thing this slice quietly did.

THE TIER IS A DESCRIPTION, NOT A KEY
    ``view_for`` takes a tier so a reviewer can see what each plan is shown,
    including from a query string. That is safe here and would not be safe on a
    route that serves records: this page renders descriptions -- names, blurbs,
    coverage years, the same catalog copy the public gate already shows -- and
    every download link on it points at ``/press/collections/{id}/download``,
    which still requires a session and still checks ``repository.may_open``.
    The tier changes what is described. It cannot change what is served.

WHAT THE PAGE HAPPENS TO PROVE
    Rendered at ``?tier=tree`` it shows twelve open collections. The React
    shelf, given the same tier, shows none: ``repository.SHELF_BY_TIER`` maps
    ``tree`` to the ``grove`` shelf and ``pressAccess.js``'s ``PLAN_REACH``
    has no ``tree`` key at all. Two implementations of one access rule, and
    nothing in the suite compares them. ``test_shelf.py`` pins the Python
    answer so that whichever way the disagreement is settled, it is settled
    deliberately.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from cedar_press import collections as launch
from cedar_press import press_catalog, repository

__all__ = [
    "KNOWN_TIERS",
    "Band",
    "ShelfEntry",
    "ShelfView",
    "resolve_tier",
    "view_for",
]

#: The plans ``repository.SHELF_BY_TIER`` recognises, in reach order. Derived
#: rather than retyped, so a tier added to the access map appears here without
#: a second edit -- the exact failure this whole page is an argument about.
KNOWN_TIERS: tuple[str, ...] = tuple(
    sorted(
        repository.SHELF_BY_TIER,
        key=lambda tier: repository.SHELF_ORDER.index(repository.SHELF_BY_TIER[tier]),
    )
)

#: The fallback plan for a request that names none. The cheapest real plan, so
#: an unsigned reviewer sees the least rather than the most.
DEFAULT_TIER = "press"


def resolve_tier(requested: str | None) -> str:
    """A tier this page will describe, refusing anything not in the access map.

    An unknown string falls back rather than raising: the value arrives from a
    query string, and a reviewer who mistypes should get the standard shelf,
    not a 422. Falling back to the LOWEST plan matters -- the same defect in
    the other direction would describe a paid shelf to anyone who guessed a
    tier name.
    """
    return requested if requested in repository.SHELF_BY_TIER else DEFAULT_TIER


@dataclass(frozen=True)
class ShelfEntry:
    """One badge on a band, and everything the reader panel says about it."""

    id: str
    short: str
    name: str
    shelf: str
    blurb: str
    linkage: str
    #: ``"YYYY to present"``, or the two-part line when the full archive
    #: reaches back further than this shelf does.
    coverage: str
    #: What the release history says, or ``None`` where none is recorded.
    freshness: str | None
    #: Whether this plan may open it. The same answer ``/press/collections``
    #: gives, from the same function, so the badge and the route agree.
    open: bool
    #: The route the badge links to. Always the authenticated one.
    href: str
    #: ``None`` when a sample exists; otherwise Cedar's own reason it does not.
    unavailable_because: str | None


@dataclass(frozen=True)
class Band:
    """One shelf's band: its entries and whether this plan reaches it."""

    shelf: str
    entries: tuple[ShelfEntry, ...]
    reached: bool
    #: The earliest year any entry on this band reaches, or ``None`` when no
    #: entry states one. Rendered with an asterisk because it is the deepest
    #: single collection and not a promise about the shelf.
    earliest: int | None


@dataclass(frozen=True)
class ShelfView:
    """Everything the template renders, with nothing left for it to decide."""

    tier: str
    reach: str
    bands: tuple[Band, ...]
    #: Versions and the latest refresh date, from ``collections.py``.
    context_line: str
    #: Collections Cedar measures that the storefront does not sell. Carried
    #: onto the page rather than dropped, for the reason ``collections.py``
    #: gives: an absence nobody can see is an absence nobody can question.
    excluded: tuple[dict[str, str], ...]
    #: Ids in ``pressCatalog.js`` that the Python snapshot does not carry, and
    #: the reverse. Empty when the dump is current. Shown on the page because
    #: a staleness the page hides is one nobody fixes.
    catalog_gap: tuple[str, ...]


def _coverage_from(entry: dict[str, Any]) -> int | None:
    """The first year of a series, or ``None`` for a roster or an absence.

    Reads the catalog's one coverage field in its two shapes. This module read
    ``standardFrom`` and ``historyFrom`` until 2026-09-04, a pair the catalog
    retired on 2026-09-02, so every badge said "Coverage varies" and no band
    stated a year while the tests that would have noticed only checked that
    the retired names were absent. Mirrors ``coverageFrom`` in
    ``pressAccess.js``: a roster yields no year, never its capture date.
    """
    coverage = entry.get("coverage") or {}
    if coverage.get("kind") != "series":
        return None
    year = coverage.get("from")
    return year if isinstance(year, int) else None


def _coverage(entry: dict[str, Any]) -> str:
    """Coverage as one line, in the shape the collection actually has.

    Mirrors ``coverageLabel`` in ``pressAccess.js``: a series says the span,
    a roster says it is a roster and when it was taken. A collection the
    catalog snapshot has not caught up with states neither.
    """
    coverage = entry.get("coverage") or {}
    if coverage.get("kind") == "roster" and coverage.get("captured"):
        return f"Current roster, captured {coverage['captured']}"
    year = _coverage_from(entry)
    if year is None:
        return "Coverage varies"
    return f"{year} to present"


def _freshness(collection_id: str) -> str | None:
    """The release line for a collection, or ``None`` where none is recorded.

    Reads ``press_catalog.RELEASES``, the dumped snapshot of
    ``pressReleases.js``, so the page and the ``/press/releases`` route
    describe one history.
    """
    release = press_catalog.RELEASES.get(collection_id)
    if not release:
        return None
    version = release.get("version")
    updated = release.get("updated")
    cadence = release.get("cadence")
    parts = [part for part in (version, updated, cadence) if part]
    return " · ".join(parts) or None


def _catalog_gap() -> tuple[str, ...]:
    """Collections the storefront sells that the Python catalog has never heard of.

    ``press_catalog.CATALOG`` is a snapshot of ``pressCatalog.js`` that a human
    regenerates by hand, and a hand-run step is a step that gets skipped. This
    names what the snapshot is currently missing rather than rendering a
    shorter shelf and saying nothing.
    """
    known = {entry["id"] for entry in press_catalog.CATALOG}
    return tuple(dataset.id for dataset in launch.LAUNCH_COLLECTION if dataset.id not in known)


def _entry_for(dataset: Any, reached: bool) -> ShelfEntry:
    """One badge, from the descriptor plus whatever the catalog adds to it.

    The descriptor is authoritative for id, name and shelf -- both languages
    read it from ``collections.manifest.json``, so it cannot differ. The
    catalog supplies the blurb, the linkage and the coverage years, and a
    collection the snapshot has not caught up with renders with its descriptor
    alone rather than being dropped.
    """
    catalog = next(
        (dict(entry) for entry in press_catalog.CATALOG if entry["id"] == dataset.id), {}
    )
    return ShelfEntry(
        id=dataset.id,
        short=catalog.get("short") or dataset.short_name,
        name=catalog.get("name") or dataset.name,
        shelf=dataset.shelf,
        blurb=catalog.get("blurb") or dataset.tracks,
        linkage=catalog.get("linkage") or "",
        coverage=_coverage(catalog),
        freshness=_freshness(dataset.id),
        open=reached,
        href=f"/press/collections/{dataset.id}/download",
        unavailable_because=launch.sample_unavailable_reason(dataset.id),
    )


def view_for(tier: str) -> ShelfView:
    """The whole page for one plan.

    Bands come from ``repository.SHELF_ORDER`` and their membership from the
    descriptors' own ``shelf`` field, so the page cannot show a collection on a
    shelf the API would refuse it on: both read ``repository.may_open``.
    """
    # DO NOT `resolve_tier` HERE. The caller already sanitises the query-string
    # path (`session.tier if session else resolve_tier(tier)`); applying it a
    # second time corrupts the SESSION path, which is the one that matters.
    #
    # Codex, PR #38: a signed-in reader on a real but unsupported plan -
    # `free`, `sprout`, `sapling`, none of which is in `SHELF_BY_TIER` - was
    # coerced to `DEFAULT_TIER`, and `DEFAULT_TIER` is "press", the entry PAID
    # plan. The page then marked six collections "yours to download" while
    # `repository.may_open` refused every one of them.
    #
    # `resolve_tier`'s own docstring convicts this: *"Falling back to the
    # LOWEST plan matters -- the same defect in the other direction would
    # describe a paid shelf to anyone who guessed a tier name."* Coercing an
    # unsupported plan to `press` IS that defect, and it reached a signed-in
    # reader rather than a guessed query string.
    #
    # An unsupported plan now reaches NOTHING, which is what `_reaches` has
    # always returned for it and what the download route has always enforced.
    reach = repository.SHELF_BY_TIER.get(tier)
    bands = []
    for shelf in repository.SHELF_ORDER:
        reached = (reach is not None
                   and repository.SHELF_ORDER.index(shelf)
                   <= repository.SHELF_ORDER.index(reach))
        entries = tuple(
            _entry_for(dataset, reached)
            for dataset in launch.LAUNCH_COLLECTION
            if dataset.shelf == shelf
        )
        on_band = {item.id for item in entries}
        years = [
            year
            for entry in press_catalog.CATALOG
            if entry["id"] in on_band
            for year in [_coverage_from(entry)]
            if year is not None
        ]
        bands.append(
            Band(
                shelf=shelf,
                entries=entries,
                reached=reached,
                earliest=min(years) if years else None,
            )
        )
    return ShelfView(
        tier=tier,
        reach=reach,
        bands=tuple(bands),
        context_line=launch.collection_context_line(),
        excluded=tuple(dict(entry) for entry in launch.EXCLUDED_COLLECTIONS),
        catalog_gap=_catalog_gap(),
    )
