"""Where the service's data comes from.

Every route reads through here, so the move from the ported modules to
Postgres is one module's worth of change rather than a rewrite of the API.
The shapes returned are the shapes the client already reads — see
``src/features/grove/`` — because a repository that returns its own idea of a
collection just moves the translation somewhere less visible.

The catalog, the citation register and the CSV shaping live in
``collections.py`` and ``press_catalog.py``, ported from Cedar Grove's Python
package rather than rewritten. That is deliberate: those hold the inclusion
rules and release bookkeeping, and a second implementation of them is a second
set of numbers to keep in agreement.

It is also provenance and not a dependency. Cedar Press is a standalone
product: nothing here imports a Cedar Grove module or calls a Grove service,
and every value comes from ``data/cedar/collections.manifest.json``, generated
from the Cedar data workspace in ``code/``.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from cedar_press import collection_profiles, press_catalog
from cedar_press import collections as launch

#: Which shelf each plan reaches. Mirrors ``PLAN_REACH`` in
#: ``features/grove/pressAccess.js``; the client decides what renders and this
#: decides what is served, and the two are written to answer identically.
#:
#: They were not compared until ``tests/test_access.py``, and by then they had
#: drifted: ``tree`` was here and missing there, so a Tree subscriber was
#: served twelve collections by this module and shown none of them on the
#: shelf. That test now compares the two maps key for key.
#:
#: ``grove`` reaches every shelf because Cedar Grove carries every dataset, and
#: ``tree`` reaches every shelf because Tree includes Grove. Reaching a shelf
#: is not the same as being sold the Cedar Press page -- neither tier is; that
#: question is ``press_catalog.can_read_cedar_press``.
SHELF_BY_TIER: dict[str, str] = {
    "press": "standard",
    "press_pro": "pro",
    "grove": "grove",
    "tree": "grove",
}

#: Shelves nest upward: a plan that reaches "pro" also reaches "standard",
#: mirroring SHELF_ORDER in ``features/grove/pressAccess.js``.
SHELF_ORDER: tuple[str, ...] = ("standard", "pro", "grove")


def _reaches(tier: str, dataset_shelf: str) -> bool:
    """Whether this plan's shelf includes a dataset placed on ``dataset_shelf``."""
    shelf = SHELF_BY_TIER.get(tier)
    if shelf is None or dataset_shelf not in SHELF_ORDER:
        return False
    return SHELF_ORDER.index(dataset_shelf) <= SHELF_ORDER.index(shelf)


def _dataset_payload(dataset: Any) -> dict[str, Any]:
    """One collection, in the shape the shelf reads.

    ``vintage`` and ``downloads`` are ``null`` on every collection today and
    are still sent: a client that receives the key and no value can render an
    absence, while a client that receives no key at all cannot tell an absent
    measurement from an older server. ``unmeasured`` names them and says why,
    so nothing downstream has to decide on its own whether a null is a gap or
    a zero.

    ``sample`` and ``tables`` are what the download is actually backed by --
    ten rows of the flagship table, and every table's row count and
    full-file split -- so a client can say what it is handing over instead of
    calling ten rows a collection.
    """
    return {
        "id": dataset.id,
        "shelf": dataset.shelf,
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
        "cedar": launch.collection_cedar_facts(dataset.id),
        "sample": launch.collection_sample(dataset.id),
        "tables": list(launch.collection_tables(dataset.id)),
        "unmeasured": {
            field: reason
            for field, reason in launch.UNMEASURED_FIELDS.items()
            if getattr(dataset, field, None) in (None, "")
        },
    }


def collections_for(tier: str) -> list[dict[str, Any]]:
    """The collections a plan may open.

    The shelves diverged with the Owned dataset (pro and above), so this
    filters on the tier's reach rather than returning everything and letting
    the client hide the rest, because hiding is not withholding.
    """
    return [
        _dataset_payload(dataset)
        for dataset in launch.LAUNCH_COLLECTION
        if _reaches(tier, dataset.shelf)
    ]


def may_open(tier: str, collection_id: str) -> bool:
    """Whether this plan includes this collection.

    ``LAUNCH_COLLECTION`` is the storefront -- the twelve on
    ``cedar_publication.STOREFRONT_SHELVES`` -- so a collection the Cedar data
    workspace placed on the ``grove`` shelf is refused to every tier here,
    including ``grove`` and ``tree``. That is the ruling and not an oversight:
    ``gaming`` "ships through Cedar Grove, not the Press storefront", and it
    reaches this repository in the manifest's ``excluded`` rather than its
    ``collections``.

    The browser used to disagree. Codex, PR #41: its catalog is thirteen, it
    reads the shelf ordering rather than the storefront, and a Grove or Tree
    session was shown ``gaming`` as open while this function refused it.
    ``canOpenDataset`` in ``features/grove/pressAccess.js`` now refuses a
    grove-shelf collection for every plan, and
    ``tests/test_access.py::TestNothingTheClientOpensIsRefused`` compares the
    two answers per tier and per collection in both directions.
    """
    return any(
        dataset.id == collection_id and _reaches(tier, dataset.shelf)
        for dataset in launch.LAUNCH_COLLECTION
    )


def collection_csv(collection_id: str) -> str | None:
    """The preview file's rows, citation included.

    Ten rows of the collection's flagship table, not the collection. The full
    tables are not served from this repository; ``collection_tables`` carries
    what a serving layer needs to find them.
    """
    return launch.collection_csv(collection_id)


def sample_unavailable_reason(collection_id: str) -> str | None:
    """Why a collection has no preview file, so a route can say which it is.

    A collection the shelf shows and the file layer cannot serve is a
    different failure from a collection that does not exist, and answering
    both with "No such collection" hides a real, named data problem behind a
    routing message.
    """
    return launch.sample_unavailable_reason(collection_id)


def download_name(collection_id: str) -> str:
    dataset = next(
        (item for item in launch.LAUNCH_COLLECTION if item.id == collection_id), None
    )
    version = dataset.version if dataset else "v0"
    # The filename says it is a sample. A file called `deals-v0.csv` sitting in
    # somebody's downloads folder a month later cannot be told apart from the
    # release, and ten rows of a 2,662-row collection is not the release.
    return f"{collection_id}-{version}-sample.csv"


def releases() -> list[dict[str, Any]]:
    """Release history per collection, most recently updated first.

    Served from the dumped snapshot of ``pressReleases.js`` — the same
    change notes the What's New feed renders — so the service and the page
    describe one history rather than two.
    """
    rows = [
        {"id": collection_id, **_thaw(release)}
        for collection_id, release in press_catalog.RELEASES.items()
    ]
    return sorted(rows, key=lambda row: row.get("updated", ""), reverse=True)


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


def collection_profile(collection_id: str) -> dict[str, Any] | None:
    """The machine-readable profile Cedar answers from, or ``None``."""
    return collection_profiles.profile_for(collection_id)


def cedar_answer(question: str, collection_id: str) -> dict[str, str] | None:
    """A profile-grounded answer, or ``None`` when the question needs more.

    The tier used to travel with the question, because coverage was phrased
    for the reader: a Cedar Press reader was told what Cedar Press+ would
    open. Retiring the year cap (2026-09-02) removed the only thing the tier
    decided here, and a parameter nothing reads is a parameter the next
    caller will pass wrongly.
    """
    return collection_profiles.answer_from_profile(question, collection_id)


def articles() -> list[dict[str, Any]]:
    """Published briefs, newest first."""
    return [_thaw(article) for article in press_catalog.ARTICLES]


def citations() -> list[dict[str, Any]]:
    """Every recorded public use of a collection. Empty until one lands."""
    return [_thaw(entry) for entry in press_catalog.CITATIONS]
