"""Cedar Press: the tiers, the articles and the citation register.

Ported from ``src/features/grove/pressAccess.js``, ``pressArticles.js`` and
``pressCitations.js``. Those three are one subject and are one module here,
because none of them is large enough to earn its own file and a reader
answering "what is Press?" should not have to open three.

**Cedar Press is a standalone product. Cedar Grove is a superset of it.**
This module said the opposite three times, and one of those times was the file
layout, so the correction is stated rather than quietly applied.

The retired model was a pipeline: the Cedar data workspace fed Cedar Grove, and
Cedar Grove published a slice of itself as Cedar Press. Press was therefore *a
surface of* Grove -- "the same shelves, the same figures, the reader price" --
and that is why this module sits in a package named for Grove and why the page
and stylesheet sit under ``src/pages/grove``.

The owner retired it on 2026-09-02: Cedar Press is a standalone product, and
the only relationship left is one of content. Cedar Grove includes all the
datasets Cedar Press sells, and adds a data library and other public data work
that this repository neither builds nor describes. So Grove is a superset of
Press by *content*, and nothing more: Press has no runtime dependency on Grove.
Both products read the same upstream -- the Cedar data workspace, through
``data/cedar/collections.manifest.json`` -- rather than one reading the other.

The ``grove/`` directory names on the JavaScript side outlived the model that
justified them. They are vestigial names, not a dependency; the rename and its
measured cost are set out in ``docs/ARCHITECTURE.md`` under "Where the
``grove/`` paths came from".

**The article and citation data is transcribed, not retyped.**
``_press_data.json`` is written by ``scripts/dump-press.mjs`` from the
JavaScript modules. Headlines and deks are editorial copy, so a retyped
character is a misquotation rather than a crash, which is the failure that
would survive review::

    node scripts/dump-press.mjs > server/cedar_press/_press_data.json

The script and the destination are both named here because the docstring
named neither correctly: it pointed at ``python/tools/dump_press.mjs``
writing ``python/grove/_press_data.json``, and no such paths exist in this
repository. ``TestPressCatalogSnapshot`` in ``server/tests/test_collection.py``
re-runs the real script and fails if this file is behind it.

ACCESS IS AN AFFORDANCE, NOT A CONTROL
``can_read_cedar_press`` decides what renders, in the same sense as
``prototype_state`` and the JavaScript ``canReadCedarPress``. The control is
``canUseCedarPress`` in ``server/lib/tierCapabilities.js``, and it only becomes
a real boundary once press data moves behind an endpoint. Today the collection
ships in the page bundle, so the gate governs display and not access. That is
harmless while every number is demonstration data and stops being harmless the
day real datasets land. Recorded here rather than left to be discovered.

HAVALA REVIEW
The three tiers below are a commercial decision, not a derived fact. ``press``
exists only through the Tribal Business News subscription; ``grove`` is the
standalone licence; ``tree`` is the full platform, which includes Grove. If the
partnership changes what a reader tier buys, this set changes with it.

That ruling answers two different questions and they must not be run together.
Whether a plan is sold the Cedar Press *page* is ``can_read_cedar_press``, and
only the two Press tiers are: a Grove or Tree licensee reaches the collections
through Grove, not through this storefront. Which *collections* a plan opens is
``repository.SHELF_BY_TIER``, and there Grove reaches every shelf because Grove
carries every dataset, and Tree reaches every shelf because Tree includes
Grove. The JavaScript went one way and the Python the other for exactly one
tier -- ``tree`` was in ``SHELF_BY_TIER`` and missing from ``PLAN_REACH``, so a
Tree subscriber was served twelve collections by the API and shown none of them
in the browser -- because nothing compared the two maps.
``server/tests/test_access.py`` compares them now, key for key.

PROTOTYPE LIMITATIONS
The three articles are demonstration placeholders, one per launch dataset,
written to be replaced by the real first Data Briefs. The citation register
launches EMPTY on purpose: inventing entries would be fabricated proof, which
is the thing the datasets exist to replace.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from types import MappingProxyType
from typing import Any

__all__ = [
    "ARTICLES",
    "CATALOG",
    "CITATIONS",
    "RELEASES",
    "LUMECON_URL",
    "PRESS_TIERS",
    "REPORT_CITATION_HREF",
    "TBN_URL",
    "can_read_cedar_press",
    "citation_count_for",
]

_DATA_PATH = Path(__file__).with_name("_press_data.json")
_DATA: dict[str, Any] = json.loads(_DATA_PATH.read_text(encoding="utf-8"))


def _deep_freeze(value: Any) -> Any:
    """Freeze mappings and sequences all the way down.

    Freezing only the top level left an article's ``body``, ``draws``, figure
    ``points`` and paired images mutable, so a caller could edit the
    module-global catalogue every later caller sees.
    """
    if isinstance(value, dict):
        return MappingProxyType({key: _deep_freeze(item) for key, item in value.items()})
    if isinstance(value, list | tuple):
        return tuple(_deep_freeze(item) for item in value)
    return value


def _frozen(rows: list[dict[str, Any]]) -> tuple[Mapping[str, Any], ...]:
    """Deep-freeze the snapshot rows so nothing downstream can edit the catalogue.

    The data comes from ``_press_data.json``, dumped from the JavaScript
    catalogue, and it is the reference for what each Press tier receives. A
    mutable dict here would let one caller's "adjustment" silently change what
    every later caller sees.
    """
    return tuple(_deep_freeze(row) for row in rows)


#: Where the Data Briefs publish, and where the collection lives.
TBN_URL: str = _DATA["tbnUrl"]
LUMECON_URL: str = _DATA["lumeconUrl"]

#: Article cards, newest first. Each names the dataset it draws from, so an
#: article can never advertise data the page does not show.
ARTICLES = _frozen(_DATA["articles"])

#: Every known public use of a Cedar Press dataset, newest first. Empty until
#: the first real citation lands; see the module docstring.
CITATIONS = _frozen(_DATA["citations"])

#: The full collection ladder (``pressCatalog.js``): every collection the
#: product is designed around, including ones whose first release is still in
#: preparation. Cedar's profile layer reads this for the collections that do
#: not yet ship figures, so a catalog entry can describe itself without a
#: second hand-typed copy of its blurb.
CATALOG = _frozen(_DATA["catalog"])

#: Release history per collection (``pressReleases.js``): version, cadence and
#: the change notes behind the What's New feed. Dumped rather than retyped for
#: the same reason as the articles — a paraphrased change note misdescribes a
#: release. Keyed by collection id.
RELEASES = _deep_freeze(_DATA["releases"])

#: Where a reader reports a citation the register missed.
REPORT_CITATION_HREF: str = _DATA["reportCitationHref"]

#: The plans that include the Press page. A frozenset rather than a chain of
#: comparisons so adding a tier is one edit in one place, and so the JavaScript
#: and this can be compared as sets by the parity test. That parity test did
#: not exist when this comment first claimed it; ``server/tests/test_access.py``
#: is it, and it compares this set against ``canReadCedarPress`` in
#: ``src/features/grove/pressAccess.js`` tier by tier.
PRESS_TIERS = frozenset({"press", "press_pro"})


def can_read_cedar_press(tier: str | None) -> bool:
    """Whether a plan includes the Cedar Press page.

    Takes the resolved tier rather than a user record: tier resolution lives in
    ``src/workspaceTier.js`` on the JavaScript side and has no Python caller,
    so duplicating it here would be a second definition of a fact this module
    does not own.

    An unknown or missing tier is refused. Failing closed matters more than the
    convenience of a default, because the alternative is a typo in a tier name
    silently opening the page.
    """
    return tier in PRESS_TIERS


def citation_count_for(dataset_id: str) -> int:
    """How many registered citations name this dataset.

    Counts by ``datasetId`` alone, not by version: a citation of any release of
    a dataset is a citation of that dataset. Version is recorded on the entry
    so a correction to a release can find the pieces that used it, which is a
    different question from this one.
    """
    return sum(1 for c in CITATIONS if c.get("datasetId") == dataset_id)
