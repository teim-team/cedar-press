"""The launch collection: the twelve datasets Cedar Press sells.

Mirrors ``src/features/grove/collection.js``.

This docstring used to open "what the standalone Cedar Grove license reads",
from the model in which Cedar Grove published a slice of itself as Cedar Press.
That model was retired on 2026-09-02. Cedar Press is a standalone product, and
this module is the Cedar Press launch collection; Cedar Grove reads the same
twelve because Grove carries all the datasets, not because Press is a view of
Grove. Where the two diverge is recorded in ``EXCLUDED_COLLECTIONS`` and
compared against the Cedar data workspace by ``server/tests/test_access.py``.

This module holds the collection's descriptors, the findings the collection
currently supports (in the same claim shapes the organizational findings use,
so a renderer built for one renders the other unchanged), the figure specs for
the Overview's chart cards, and the rows behind each dataset's download button.

ONE SOURCE, TWO LANGUAGES
    Both implementations read ``data/cedar/collections.manifest.json``. They
    used to hold two hand-written copies of the same literals, and this
    module's docstring claimed ``tests/test_collection.py`` compared them so a
    release that changed one and not the other would fail a build. No such
    file existed, nothing compared them, and they had already drifted: the
    Python descriptor carried ``shelf`` and the JavaScript one did not, and
    the JavaScript citation resolved its version through ``pressReleases.js``
    while this one read the descriptor, so the same dataset cited as v9.0 in
    the browser and v9 on the server. Reading one file makes a value
    difference impossible, and ``server/tests/test_collection.py`` -- which
    now exists, and runs in CI -- executes both implementations and compares
    them field by field anyway.

WHERE THE NUMBERS COME FROM
    ``scripts/import_cedar_manifest.py`` writes the manifest from the Cedar
    data workspace: ``code/760_collection_descriptors.py`` for the descriptors
    and ``code/1135_full_dataset_review_bundle.py`` for the per-table row
    counts and the ten-row samples. Nothing here is typed by hand.

WHAT IS STILL NOT MEASURED, AND SAYS SO
    ``vintage`` and ``downloads`` are ``None`` on every dataset, and
    ``UNMEASURED_FIELDS`` carries the reason for each: Cedar's cadence
    measurement produced no vintage, and no download counter exists. They are
    absent rather than zero or blank, because a zero download count and an
    empty vintage both read as measurements.

    ``COLLECTION_FIGURES`` is the one place demonstration data remains. Cedar
    publishes no figure series, so the four pilot charts are the placeholders
    they always were -- now carrying ``demonstration=True`` in the data rather
    than only in prose, so a renderer or an answer can see it without reading
    a comment. The Owned figure is the exception and is marked
    ``demonstration=False``: its aggregates come from the roster White Earth
    Nation's TERO supplied on 2026-08-28. No figure was invented for the eight
    collections that arrived with this change; they have none, and none is
    drawn.
"""

from __future__ import annotations

import csv
import io
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# The storefront's own naming. `press_catalog` reads a committed snapshot and
# imports nothing from this package, so it is a leaf and cannot close a cycle.
from cedar_press import csv_safety, press_catalog
from cedar_press.claims import CLAIM_CLASS

__all__ = [
    "COLLECTION_FIGURES",
    "EXCLUDED_COLLECTIONS",
    "GROVE_RELEASE_COLLECTIONS",
    "GROVE_RELEASE_IDS",
    "LAUNCH_COLLECTION",
    "UNMEASURED_FIELDS",
    "CollectionDataset",
    "CollectionFigure",
    "CollectionFindings",
    "CollectionLead",
    "CollectionNeed",
    "CollectionSupported",
    "FigurePoint",
    "collection_cedar_facts",
    "collection_citation",
    "collection_context_line",
    "collection_csv",
    "collection_findings",
    "collection_sample",
    "collection_tables",
    "figures_in_shelf_order",
    "sample_unavailable_reason",
]

#: The repository root, from ``server/cedar_press/collections.py``. The
#: manifest and the sample rows are repository data rather than package data:
#: the browser bundle reads the same manifest, and a second copy inside the
#: package would be a second set of numbers to keep in agreement.
_REPO = Path(__file__).resolve().parents[2]
_MANIFEST_PATH = _REPO / "data" / "cedar" / "collections.manifest.json"
#: Where a manifest ``sample_path`` resolves: the repository root, so
#: ``/data/cedar/samples/<c>/spreadsheet__10.csv`` is
#: ``data/cedar/samples/<c>/spreadsheet__10.csv``. Until 2026-10-04 this was
#: ``public/`` and the built site served those raw producer previews, retired
#: ``CEDAR-NEST-`` IDs and all. They are now inputs only: the site serves the
#: customer table rendered from them (``scripts/render_sample_downloads.py``).
_SAMPLE_ROOT = _REPO


def raw_preview_file(url: str) -> Path:
    """The raw producer preview a manifest ``sample_path`` names, on disk.

    Not served: the browser reads ``/data/cedar/downloads/<c>.csv`` instead.
    """
    return _SAMPLE_ROOT / str(url).lstrip("/")

_MANIFEST: dict[str, Any] = json.loads(_MANIFEST_PATH.read_text(encoding="utf-8"))

#: Which fields carry no measurement, and why. Read by anything that would
#: otherwise render an absent value as a real one.
UNMEASURED_FIELDS: dict[str, str] = dict(_MANIFEST["unmeasured_fields"])

#: Collections Cedar measures that the storefront does not sell, each with the
#: reason. Held rather than dropped: an absence nobody can see is an absence
#: nobody can question.
EXCLUDED_COLLECTIONS: tuple[dict[str, str], ...] = tuple(
    dict(entry) for entry in _MANIFEST["excluded"]
)

#: THE reviewed Cedar Grove release declaration: the one place that says which
#: collections the full-download route may serve from a pinned ``cedar_grove``
#: catalog. A declared id is served only while the manifest still places it on
#: the ``grove`` shelf in ``excluded`` (the storefront neither sells nor
#: previews it), so a collection that moves shelf stops being Grove-served
#: rather than being served twice. WHICH release is served is not listed here:
#: it is the one Lumecon-data collection release pinned in
#: ``data/cedar/grove_release_pin.json`` (``repository.grove_release_pin``).
#: Which COMPONENTS are offered is the collection's field-map presentation
#: entries (``data/cedar/field_map.json`` keys ``<collection>/<component>``),
#: each validated against that release's embedded component contract. Access
#: reuses the existing tier model: a tier whose shelf reaches ``grove``
#: (``grove``, ``tree``). No tier or route is added.
GROVE_RELEASE_IDS: tuple[str, ...] = ("gaming", "infrastructure")
GROVE_RELEASE_COLLECTIONS: tuple[dict[str, str], ...] = tuple(
    entry
    for entry in EXCLUDED_COLLECTIONS
    if entry["id"] in GROVE_RELEASE_IDS and entry.get("shelf") == "grove"
)


@dataclass(frozen=True)
class CollectionDataset:
    """One curated dataset's descriptor, mirroring the manifest contract.

    ``rows_label`` is display copy, not a count the code trusts. It reads
    ``row count unresolved`` where two Cedar-side declarations of a
    collection's membership disagree, which is a real state one dataset is in
    today rather than a placeholder.

    ``origin`` and ``level`` use the evidence registry's vocabulary
    (``SOURCE_ORIGIN``, ``SOURCE_AVAILABILITY``). ``level`` says what the rows
    are: entity records, entity records that also roll up to geography, or
    geography.

    ``vintage`` and ``downloads`` are ``None`` on every dataset today. They are
    optional because Cedar measures neither, not because they are unimportant
    -- see ``UNMEASURED_FIELDS`` for each reason. A ``str`` defaulting to ``""``
    and an ``int`` defaulting to ``0`` were how the prototype made an absence
    look like a measurement.
    """

    id: str
    name: str
    short_name: str
    origin: str
    level: str
    tracks: str
    rows_label: str
    downloads: int | None
    vintage: str | None
    version: str
    #: The data date in ``LAUNCH_COLLECTION`` (see ``refreshed``). A
    #: descriptor loaded directly with ``CollectionDataset(**descriptor)``
    #: carries the release date here, as the descriptor states it.
    updated: str | None
    sources: str
    method: str
    #: Which shelf carries this dataset ("standard", "pro", "grove"). The
    #: client's catalog declares the same placement; this one is the control
    #: the routes enforce.
    shelf: str = "standard"
    #: When the DATA was last refreshed from the producer. In
    #: ``LAUNCH_COLLECTION`` this is also ``updated``: the one date a reader
    #: sees for a collection, labelled "Updated", and the date its citation
    #: carries. On 2026-10-06 every collection was re-released at the owner's
    #: request without a producer refresh, so the release date said the data
    #: changed when it had not. Read from the manifest provenance
    #: (``_data_refreshed``), never replaced by the release date; the client
    #: reads the same fields (collection.js ``dataRefreshed``).
    refreshed: str | None = None
    #: The release date the ledger records (data/cedar/releases.json), kept
    #: for checks against the ledger and never shown.
    released: str | None = None


#: Collections whose observation count is not shown to readers (owner,
#: 2026-10-06: NEED's published reviewed set (43) is a small part of the
#: enterprise register, so no count is stated rather than a misleading one;
#: Native Nonprofits' 89 ruled-in organizations is shown). The label
#: reads empty, which every surface already treats as "no count". The client
#: applies the same set (collection.js COUNT_NOT_SHOWN).
COUNT_NOT_SHOWN: frozenset[str] = frozenset({"need"})


#: What an abbreviated collection name stands for (owner, 2026-10-06: a
#: paragraph describing NEED or PLOT says what the letters mean). NEED's
#: descriptor name already spells it out; PLOT's description does not, so it
#: is prefixed where it is read. The client applies the same text
#: (pressCatalog.js blurbs).
ACRONYM_LEADS: dict[str, str] = {
    "plot": "PLOT (Parcel-Level Ownership and Transfers)",
}


def _descriptor_for_readers(descriptor: dict[str, Any]) -> dict[str, Any]:
    out = dict(descriptor)
    if out.get("id") in COUNT_NOT_SHOWN:
        out["rows_label"] = ""
    lead = ACRONYM_LEADS.get(out.get("id"))
    if lead and lead not in (out.get("tracks") or ""):
        out["tracks"] = f"{lead}: {out['tracks']}"
    return out


def _data_refreshed(collection_id: str) -> str | None:
    """The producer refresh a collection was staged from, or ``None``.

    ``provenance.selected_refreshes[id].updated`` where the collection was
    refreshed on its own, else ``provenance.updated``, the producer pin every
    other collection was staged from. Never the release date.
    """
    provenance = _MANIFEST.get("provenance") or {}
    selected = (provenance.get("selected_refreshes") or {}).get(collection_id) or {}
    return selected.get("updated") or provenance.get("updated") or None


def _launch_dataset(entry: dict[str, Any]) -> CollectionDataset:
    """A storefront dataset, dated by its data refresh, not its release."""
    descriptor = _descriptor_for_readers(entry["descriptor"])
    released = descriptor.pop("updated", None)
    refreshed = _data_refreshed(descriptor["id"])
    return CollectionDataset(
        **descriptor, updated=refreshed, refreshed=refreshed, released=released
    )


LAUNCH_COLLECTION: tuple[CollectionDataset, ...] = tuple(
    _launch_dataset(entry) for entry in _MANIFEST["collections"]
)

#: Cedar's own facts per dataset, keyed by product id: readiness status, the
#: named blockers behind a BLOCKED one, and the measured row and table counts.
#: Beside the descriptor rather than inside it, because ``CollectionDataset``
#: declares fourteen fields and an undeclared keyword is a ``TypeError``.
_CEDAR: dict[str, dict[str, Any]] = {
    entry["id"]: entry["cedar"] for entry in _MANIFEST["collections"]
}
# Sample files the manifest declares and the repository does not hold, as
# measured by scripts/measure-samples.mjs. The client applies the same record
# (collection.js), so a declared-but-uncommitted sample reads as unpublished,
# with the reason, on both sides instead of as a file that will 404.
_PUBLISHED: dict[str, Any] = json.loads(
    (_MANIFEST_PATH.parent / "samples.published.json").read_text(encoding="utf-8")
)
_UNPUBLISHED: frozenset[str] = frozenset(entry["path"] for entry in _PUBLISHED["unpublished"])


def _with_publication(sample: dict[str, Any] | None) -> dict[str, Any] | None:
    if not sample or not sample.get("path") or sample["path"] not in _UNPUBLISHED:
        return sample
    marked = {k: v for k, v in sample.items() if k != "path"}
    marked["path"] = None
    marked["unpublished_path"] = sample["path"]
    marked["unavailable_because"] = _PUBLISHED["reason"].replace("{table}", sample["table"])
    return marked


def _table_with_publication(table: dict[str, Any]) -> dict[str, Any]:
    if not table.get("sample_path") or table["sample_path"] not in _UNPUBLISHED:
        return table
    return {**table, "sample_path": None, "sample_unpublished": table["sample_path"]}


_SAMPLE: dict[str, dict[str, Any]] = {
    entry["id"]: _with_publication(entry["sample"]) for entry in _MANIFEST["collections"]
}
_TABLES: dict[str, tuple[dict[str, Any], ...]] = {
    entry["id"]: tuple(_table_with_publication(t) for t in entry["tables"])
    for entry in _MANIFEST["collections"]
}


def _dataset_for(dataset_id: str) -> CollectionDataset | None:
    """The descriptor behind a figure or download, or ``None`` for an unknown id.

    ``None`` rather than a raise because the ids arrive from the UI layer, and an
    unknown one should render as an absent card, not a crash.
    """
    return next((d for d in LAUNCH_COLLECTION if d.id == dataset_id), None)


def collection_cedar_facts(dataset_id: str) -> dict[str, Any] | None:
    """Readiness, blockers and measured counts for a dataset, or ``None``."""
    facts = _CEDAR.get(dataset_id)
    return dict(facts) if facts else None


def collection_tables(dataset_id: str) -> tuple[dict[str, Any], ...]:
    """Every table in a collection, with its sample and its full-file facts.

    The full spreadsheets are not in this repository -- the set measures 6.2 GB
    and single tables exceed GitHub's file limit -- so each entry carries the
    row count, the split and the file count a serving layer needs to locate
    the real file. ``full_file.shippable`` is the publication rule's own
    answer, not a guess.
    """
    return _TABLES.get(dataset_id, ())


def collection_sample(dataset_id: str) -> dict[str, Any] | None:
    """The flagship table's ten-row sample: which table, where, how many of."""
    sample = _SAMPLE.get(dataset_id)
    return dict(sample) if sample else None


def sample_unavailable_reason(dataset_id: str) -> str | None:
    """Why a collection has no preview file, when it has none.

    ``None`` when a sample exists. A collection whose flagship table Cedar
    could not settle carries the reason as data so a route can say what is
    actually wrong instead of reporting the collection missing.
    """
    sample = _SAMPLE.get(dataset_id)
    if sample is None:
        return None
    return sample.get("unavailable_because")


def collection_short(dataset: Any) -> str | None:
    """The label a citation or a version line shows for a collection.

    The storefront catalog's ``short`` wins over the descriptor's
    ``short_name`` where the two differ: the catalog is where the storefront
    decides how a collection is NAMED to a reader, the descriptor is the
    workspace's record of what it IS. ``shelf.py`` already resolved it in that
    order; ``collections.py`` did not, and the JavaScript did not either, so
    both sides agreed on the wrong answer and the parity test was satisfied.

    It matters for one collection today. NEED's descriptor short name is a
    bare "NEED", and ``docs/NEED_RENAME_2026-09-10.md`` renamed the formal
    name to lead with Cedar precisely because a bare one reads as the
    Minneapolis Fed's dataset. A basis line under a figure is where that
    ambiguity does the most damage.
    """
    if dataset is None:
        return None
    for entry in press_catalog.CATALOG:
        if entry["id"] == dataset.id and entry.get("short"):
            return str(entry["short"])
    return dataset.short_name


def collection_context_line() -> str:
    """One line for the context strip: the latest data refresh date."""
    dates = sorted(d.updated for d in LAUNCH_COLLECTION if d.updated)
    return f"Updated {dates[-1]}" if dates else ""


@dataclass(frozen=True)
class CollectionSupported:
    """A finding the collection supports, in the organizational claim shape."""

    id: str
    text: str
    basis: str
    claim_class: str
    confidence: str
    fidelity: str
    #: Whether the series behind this finding is demonstration data. True on
    #: every finding here: Cedar publishes no figure series, so none of these
    #: rests on a measurement. Carried in the data rather than in a comment,
    #: because a renderer cannot read a comment.
    demonstration: bool = True
    recipe_id: str | None = None


@dataclass(frozen=True)
class CollectionNeed:
    """An honesty item: a row awaiting confirmation or a release still partial."""

    id: str
    text: str
    demonstration: bool = False


@dataclass(frozen=True)
class CollectionLead:
    """A story lead and the evidence it rests on, in the narrative shape."""

    id: str
    name: str
    have: int
    need: int
    missing: tuple[str, ...]
    requires: tuple[str, ...]
    demonstration: bool = True


@dataclass(frozen=True)
class CollectionFindings:
    """The three feeds the collection Overview renders, together."""

    supported: tuple[CollectionSupported, ...]
    needs: tuple[CollectionNeed, ...]
    narratives: tuple[CollectionLead, ...]


def collection_findings() -> CollectionFindings:
    """What the collection supports today, in the findings shapes.

    Class and confidence are held as separate dimensions, the basis names the
    dataset, and fidelity is ``direct`` because the collection measures what it
    names rather than standing a wider geography in.

    Every supported finding here is ``demonstration=True``. These read on the
    same series ``COLLECTION_FIGURES`` draws, and Cedar publishes no figure
    series, so none of them is a measured claim. They kept version numbers in
    their basis strings -- "Contractors v6", "Deals v9" -- that no release ever
    carried; the basis is derived from the descriptor now, so it cannot name a
    version that does not exist.
    """

    def basis(dataset_id: str, detail: str) -> str:
        dataset = _dataset_for(dataset_id)
        name = collection_short(dataset) if dataset else dataset_id
        return f"{name}, {detail}"

    supported = (
        CollectionSupported(
            id="col-contracting-up",
            text="Federal contracting to Native entities rose for a fourth straight quarter.",
            basis=basis("contractors", "FPDS and USAspending."),
            claim_class=CLAIM_CLASS.descriptive,
            confidence="high",
            fidelity="direct",
        ),
        CollectionSupported(
            id="col-deals-record",
            text="Announced deal volume in 2025 runs ahead of every prior year in the series.",
            basis=basis("deals", "announced and closed labeled separately."),
            claim_class=CLAIM_CLASS.descriptive,
            confidence="high",
            fidelity="direct",
        ),
        CollectionSupported(
            id="col-sector-lead",
            text="Energy and project finance lead 2025 announced transactions, ahead of hospitality.",
            basis=basis("deals", "sector taxonomy."),
            claim_class=CLAIM_CLASS.comparative,
            confidence="moderate",
            fidelity="direct",
        ),
    )

    availability_needs = []
    for dataset in LAUNCH_COLLECTION:
        facts = collection_cedar_facts(dataset.id) or {}
        sample = collection_sample(dataset.id) or {}
        missing = []
        rows = facts.get("n_rows")
        if type(rows) is not int or not 0 <= rows <= 2**53 - 1:
            missing.append("The current release does not state a row count.")
        if not sample.get("path"):
            missing.append(
                sample_unavailable_reason(dataset.id)
                or "No preview file is published for the current release."
            )
        if missing:
            availability_needs.append(
                CollectionNeed(
                    id=f"col-need-{dataset.id}-availability",
                    text=f"{dataset.name}: {' '.join(missing)}",
                )
            )
    without_vintage = [
        dataset
        for dataset in LAUNCH_COLLECTION
        if not isinstance(dataset.vintage, str) or not dataset.vintage.strip()
    ]
    vintage_needs = []
    if without_vintage:
        vintage_text = (
            "No collection states a vintage."
            if len(without_vintage) == len(LAUNCH_COLLECTION)
            else "A collection vintage is not stated for: "
            + "; ".join(dataset.name for dataset in without_vintage)
            + "."
        )
        vintage_needs.append(
            CollectionNeed(
                id="col-need-vintage",
                text=vintage_text
                + " An update date does not establish the periods covered by every source.",
            )
        )

    needs = (
        CollectionNeed(
            id="col-need-closing",
            text=(
                "Demonstration: Three large announced deals await closing confirmation "
                "before they enter totals (Deals, primary source pending)."
            ),
            demonstration=True,
        ),
        CollectionNeed(
            id="col-need-fy26",
            text=(
                "Demonstration: FY2026 assistance figures are partial until the Q1 "
                "release lands (Funding, USAspending publication lag)."
            ),
            demonstration=True,
        ),
        CollectionNeed(
            id="col-need-matches",
            text=(
                "Demonstration: Two parent-entity matches are provisional pending SAM "
                "re-registration (Contractors, entity resolution queue)."
            ),
            demonstration=True,
        ),
        *availability_needs,
        *vintage_needs,
    )

    narratives = (
        CollectionLead(
            id="col-lead-energy",
            name="Demonstration: Energy project financing expansion",
            have=3,
            need=3,
            missing=(),
            requires=("Deal series", "Sector taxonomy", "Primary confirmations"),
        ),
        CollectionLead(
            id="col-lead-8a",
            name="Demonstration: 8(a) participation and award growth",
            have=3,
            need=3,
            missing=(),
            requires=("Entity matches", "Award histories", "Certification lists"),
        ),
        CollectionLead(
            id="col-lead-assist",
            name="Demonstration: Assistance shifts under new appropriations",
            have=2,
            need=3,
            missing=("Q1 release",),
            requires=("Assistance records", "Entity matches", "Q1 release"),
        ),
    )

    return CollectionFindings(supported=supported, needs=needs, narratives=narratives)


@dataclass(frozen=True)
class FigurePoint:
    """One mark on a figure; ``compare`` is the gray dashed comparison series."""

    label: str
    value: float
    compare: float | None = None


@dataclass(frozen=True)
class CollectionFigure:
    """One Overview chart card, kept as data so a renderer stays dumb.

    ``kind`` picks the mark: quarterly bars, a leader-vs-others comparison, or
    a two-series trend (``compare`` is the gray dashed comparison line).

    ``demonstration`` says whether the points are a measurement. Cedar
    publishes no figure series, so three of the four are placeholders and say
    so here rather than only in a docstring.
    """

    id: str
    title: str
    basis: str
    kind: str
    demonstration: bool
    points: tuple[FigurePoint, ...] = field(default_factory=tuple)


def _basis_for(dataset_id: str, fallback: str) -> str:
    """A figure's basis line, derived so it cannot name a stale version."""
    dataset = _dataset_for(dataset_id)
    if dataset is None:
        return fallback
    if not dataset.updated:
        return collection_short(dataset)
    return f"{collection_short(dataset)}, updated {dataset.updated}"


COLLECTION_FIGURES: tuple[CollectionFigure, ...] = (
    CollectionFigure(
        id="deals",
        title="Announced deals by quarter",
        basis=_basis_for("deals", "Deals"),
        kind="bars",
        demonstration=True,
        points=(
            FigurePoint(label="Q2'25", value=9),
            FigurePoint(label="Q3'25", value=12),
            FigurePoint(label="Q4'25", value=10),
            FigurePoint(label="Q1'26", value=16),
            FigurePoint(label="Q2'26", value=19),
        ),
    ),
    CollectionFigure(
        id="contractors",
        title="Top parents by obligations",
        basis=_basis_for("contractors", "Contractors"),
        kind="leader",
        demonstration=True,
        points=(
            FigurePoint(label="Parent entity A", value=100),
            FigurePoint(label="Parent entity B", value=78),
            FigurePoint(label="Parent entity C", value=65),
            FigurePoint(label="Parent entity D", value=48),
        ),
    ),
    # The one measured figure on the page: White Earth Nation's TERO supplied
    # the roster on 2026-08-28 and these are its certification tiers. It is
    # not in the descriptor manifest because Cedar's descriptor emitter
    # publishes no figure series for any collection.
    CollectionFigure(
        id="owned",
        title="White Earth certified businesses by preference tier",
        basis="White Earth Nation TERO roster, supplied 2026-08-28",
        kind="leader",
        demonstration=False,
        points=(
            FigurePoint(label="1st preference", value=17),
            FigurePoint(label="2nd preference", value=4),
            FigurePoint(label="4th preference", value=1),
        ),
    ),
    CollectionFigure(
        id="funding",
        title="Federal assistance, trend",
        basis=_basis_for("funding", "Funding"),
        kind="trend",
        demonstration=True,
        points=(
            FigurePoint(label="FY21", value=52, compare=44),
            FigurePoint(label="FY22", value=58, compare=46),
            FigurePoint(label="FY23", value=55, compare=45),
            FigurePoint(label="FY24", value=71, compare=49),
            FigurePoint(label="FY25", value=84, compare=52),
        ),
    ),
)


def figures_in_shelf_order() -> tuple[CollectionFigure, ...]:
    """The collection's figures, in the order the shelf carries the datasets.

    This used to be ``figures_by_downloads`` and sorted on a download count.
    No download counter exists -- the count was demonstration data and is now
    ``None`` -- so ordering by "demonstrated use" ranked the figures on a
    number nobody had measured. Shelf order is a fact the manifest states.
    """
    order = {dataset.id: index for index, dataset in enumerate(LAUNCH_COLLECTION)}
    return tuple(sorted(COLLECTION_FIGURES, key=lambda f: order.get(f.id, len(order))))


def collection_citation(dataset_id: str, accessed_on: str | None = None) -> str | None:
    """The canonical citation for a collection dataset.

    The citation register records who cited a dataset; this is the other half
    of that loop, the sentence to cite it WITH. A dataset that is easy to cite
    correctly gets cited by name and version, corrections can find everyone
    who relied on a release, and Lumecon's name travels with every derivative
    table.

    Version is load-bearing. Vintage was too, and is omitted rather than
    printed empty: Cedar states no vintage for any collection, and
    "vintage " with nothing after it is a citation that cannot be checked.

    ``accessed_on`` is a pre-formatted date string supplied by the caller, so
    this stays pure and byte-comparable with the JS implementation.
    """
    dataset = _dataset_for(dataset_id)
    if dataset is None:
        return None
    updated = f" Updated {dataset.updated}." if dataset.updated else ""
    accessed = f" Accessed {accessed_on}." if accessed_on else ""
    return f'Lumecon, "{dataset.name}", Cedar Press collection, cedarpress.ai.{updated}{accessed}'


def _csv_cell(value: object) -> str:
    """One CSV cell, quoted only when the value needs it."""
    text = csv_safety.spreadsheet_safe("" if value is None else str(value))
    if any(ch in text for ch in ('"', ",", "\n", "\r")):
        return '"' + text.replace('"', '""') + '"'
    return text


#: NEED ownership chains, each with its evidence (``data/cedar/need_ownership_evidence.json``).
_NEED_OWNERSHIP_PATH = _REPO / "data" / "cedar" / "need_ownership_evidence.json"
#: The columns the NEED download adds after ``enterprise_name``. The reviewed
#: NEED table records only the relationship each evidence page states
#: directly (often the holding company one level up, or nothing); a reader
#: needs the Native nation or corporation at the top of the chain. Every
#: value comes from a recorded ownership ruling or register binding cited in
#: ``native_owner_evidence``, never from a name.
NATIVE_OWNER_COLUMNS = ("native_owner", "native_owner_cedar_uid", "native_owner_basis", "native_owner_source")

#: Plain words for each kind of ownership evidence the file records.
_EVIDENCE_WORDS = {
    "owner_ruling": "ownership ruling recorded by Cedar",
    "enterprise_register": "Cedar enterprise register binding",
    "first_party_cage_list": "listed by the owner's federal contracting arm with its CAGE code",
    "identifier_ledger": "federal identifier ledger ultimate-parent chain",
    "derived_ranking": "Cedar contractor ranking attribution",
    "producer_evidence_pin": "the owner's own published page",
    "government_record": "federal procurement record",
}


def _need_ownership() -> list[dict[str, Any]]:
    if not _NEED_OWNERSHIP_PATH.exists():
        return []
    return json.loads(_NEED_OWNERSHIP_PATH.read_text(encoding="utf-8")).get("records", [])


def _public_url(urls: list[str]) -> str:
    """The first page a reader can open: an owner's or agency's own page, never Cedar's private repository."""
    return next((url for url in urls if url and "github.com/teim-team/" not in url), "")


def with_native_owner(rows: list[list[str]]) -> list[list[str]]:
    """NEED rows with their evidenced ultimate Native owner, matched by UEI, else exact name.

    ``native_owner_source`` is a page the reader can open: the evidence's own
    public page, else the row's first published source (the owner's page that
    lists the enterprise). Rows with no recorded ruling stay blank.
    """
    header = rows[0]
    if "enterprise_name" not in header or set(NATIVE_OWNER_COLUMNS) & set(header):
        return rows
    by_uei: dict[str, dict[str, Any]] = {}
    by_name: dict[str, dict[str, Any]] = {}
    for record in _need_ownership():
        if not record.get("in_pinned_need_sample"):
            continue
        if record.get("uei"):
            by_uei[record["uei"]] = record
        if record.get("enterprise_name_as_recorded"):
            by_name[record["enterprise_name_as_recorded"]] = record
    col = {name: index for index, name in enumerate(header)}
    at = col["enterprise_name"] + 1
    out = [[*header[:at], *NATIVE_OWNER_COLUMNS, *header[at:]]]
    for row in rows[1:]:
        uei = row[col["uei"]] if "uei" in col else ""
        record = (by_uei.get(uei) if uei else None) or by_name.get(row[col["enterprise_name"]])
        if record is None:
            added = ["", "", "", ""]
        else:
            evidence = record.get("evidence", [])
            kinds = list(dict.fromkeys(_EVIDENCE_WORDS.get(e.get("kind"), "") for e in evidence))
            basis = "; ".join(kind for kind in kinds if kind)
            own_sources = row[col["source_urls"]].split(";") if "source_urls" in col else []
            source = _public_url([e.get("url") or "" for e in evidence]) or _public_url([u.strip() for u in own_sources])
            added = [record.get("ultimate_native_owner") or "", record.get("ultimate_native_owner_cedar_uid") or "", basis, source]
        out.append([*row[:at], *added, *row[at:]])
    return out


def collection_csv(dataset_id: str) -> str | None:
    """The rows behind a dataset card's Download button.

    The collection's flagship table, ten real rows of it, straight from
    ``code/1135_full_dataset_review_bundle.py``. This used to be the figure's
    own points -- five demonstration bars dressed as a release file. What
    downloads now is data.

    ``None`` when the collection has no sample. One is in that state today and
    ``sample_unavailable_reason`` says why; handing over a metadata file in
    place of the rows a tile promises is the failure this avoids.

    The citation is a column, never an extra observation. A downloaded file outlives the page it came
    from, so the file itself must say what it is, whose work it is and how to
    credit it; provenance that lives only in the UI is provenance the reader
    loses on save.
    """
    # The NEED reviewed-base proof no longer gates the preview (owner ruling
    # 2026-10-04: no NEED publication hold).
    sample = _SAMPLE.get(dataset_id)
    if sample is None or not sample.get("path"):
        return None
    path = raw_preview_file(sample["path"])
    if not path.exists():
        return None
    text = path.read_text(encoding="utf-8").replace("\r\n", "\n").rstrip("\n")
    rows = list(csv.reader(io.StringIO(text)))
    citation = collection_citation(dataset_id) or ""
    result = [[*rows[0], "cite_as"], *[[*row, citation] for row in rows[1:]]]
    return "\n".join(",".join(_csv_cell(value) for value in row) for row in result)
