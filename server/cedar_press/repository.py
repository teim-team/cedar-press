"""Where the service's data comes from.

Every route reads through here, so the move from the ported modules to
Postgres is one module's worth of change rather than a rewrite of the API.
The shapes returned are the shapes the client already reads — see
``src/features/grove/`` — because a repository that returns its own idea of a
collection just moves the translation somewhere less visible.

The catalog, the citation register and the CSV shaping live in
``collections.py`` and ``press_catalog.py``, carried over from Cedar Grove's
Python package. That is deliberate: those hold the inclusion rules and
release bookkeeping, and a second implementation of them is a second set of
numbers to keep in agreement.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from cedar_press import collections as launch
from cedar_press import press_catalog

#: Which shelf each plan reaches. Mirrors ``features/grove/pressAccess.js``;
#: the client decides what renders and this decides what is served, and the
#: two are written to answer identically.
SHELF_BY_TIER: dict[str, str] = {
    "press": "standard",
    "press_pro": "pro",
    "grove": "grove",
    "tree": "grove",
}


def _dataset_payload(dataset: Any) -> dict[str, Any]:
    """One collection, in the shape the shelf reads."""
    return {
        "id": dataset.id,
        "name": dataset.name,
        "shortName": dataset.short_name,
        "tracks": dataset.tracks,
        "rowsLabel": dataset.rows_label,
        "downloads": dataset.downloads,
        "vintage": dataset.vintage,
        "version": dataset.version,
        "updated": dataset.updated,
        "sources": dataset.sources,
        "method": dataset.method,
    }


def collections_for(tier: str) -> list[dict[str, Any]]:
    """The collections a plan may open.

    Today the launch collection is the whole catalog and every press tier
    reaches all of it; when the shelves diverge this filters on the tier's
    shelf rather than returning everything and letting the client hide the
    rest, because hiding is not withholding.
    """
    shelf = SHELF_BY_TIER.get(tier)
    if shelf is None:
        return []
    return [_dataset_payload(dataset) for dataset in launch.LAUNCH_COLLECTION]


def may_open(tier: str, collection_id: str) -> bool:
    """Whether this plan includes this collection."""
    if SHELF_BY_TIER.get(tier) is None:
        return False
    return any(dataset.id == collection_id for dataset in launch.LAUNCH_COLLECTION)


def collection_csv(collection_id: str) -> str | None:
    """The release file's rows, citation included."""
    return launch.collection_csv(collection_id)


def download_name(collection_id: str) -> str:
    dataset = next(
        (item for item in launch.LAUNCH_COLLECTION if item.id == collection_id), None
    )
    version = dataset.version if dataset else "v0"
    return f"{collection_id}-{version}.csv"


def releases() -> list[dict[str, Any]]:
    """Release history, newest first.

    The history lives in the JavaScript catalogue today
    (``features/grove/pressReleases.js``) and is not part of the ported
    Python. Returning an empty list is the honest answer until it moves:
    an invented history would be exactly the fabricated provenance the
    citation register exists to prevent.
    """
    return []


def _thaw(value: Any) -> Any:
    """Plain dicts and lists, all the way down.

    ``press_catalog`` deep-freezes its snapshot so no caller can edit the
    catalogue every later caller sees, which leaves nested values as
    ``mappingproxy`` — a type the JSON serializer refuses. Copying at the top
    level only was not enough: an article's body and figures are nested, and
    the failure surfaced as a 500 on a route whose data was fine.
    """
    if isinstance(value, Mapping):
        return {key: _thaw(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_thaw(item) for item in value]
    return value


def articles() -> list[dict[str, Any]]:
    """Published briefs, newest first."""
    return [_thaw(article) for article in press_catalog.ARTICLES]


def citations() -> list[dict[str, Any]]:
    """Every recorded public use of a collection. Empty until one lands."""
    return [_thaw(entry) for entry in press_catalog.CITATIONS]
