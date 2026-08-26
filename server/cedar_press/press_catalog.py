"""Cedar Grove: Cedar Press, the published surface.

Ported from ``src/features/grove/pressAccess.js``, ``pressArticles.js`` and
``pressCitations.js``. Those three are one subject and are one module here,
because none of them is large enough to earn its own file and a reader
answering "what is Press?" should not have to open three.

**Press is a Grove surface, not a sibling product.** It is how the launch
collection gets published with a partner: the same shelves, the same figures,
the reader price. That is why it lives in this package rather than beside it,
and why the page and stylesheet sit under ``src/pages/grove``.

**The article and citation data is transcribed, not retyped.**
``_press_data.json`` is written by ``python/tools/dump_press.mjs`` from the
JavaScript modules. Headlines and deks are editorial copy, so a retyped
character is a misquotation rather than a crash, which is the failure that
would survive review::

    node python/tools/dump_press.mjs > python/grove/_press_data.json

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
    "CITATIONS",
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

#: Where a reader reports a citation the register missed.
REPORT_CITATION_HREF: str = _DATA["reportCitationHref"]

#: The plans that include the Press page. A frozenset rather than a chain of
#: comparisons so adding a tier is one edit in one place, and so the JavaScript
#: and this can be compared as sets by the parity test.
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
