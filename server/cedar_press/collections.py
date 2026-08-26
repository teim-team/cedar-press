"""The launch collection: what the standalone Cedar Grove license reads.

Ported from ``src/features/grove/collection.js``.

The collection plan replaces the organizational insight layer on the Overview
with the curated Cedar Press datasets. This module holds the collection's
descriptors, the findings the collection currently supports (in the same claim
shapes the organizational findings use, so a renderer built for one renders the
other unchanged), the figure specs for the Overview's chart cards, and the CSV
rows behind each dataset's download button.

The two implementations must move together: this file mirrors the JS module
value for value, and ``tests/test_collection.py`` holds the same contracts the
JS suite holds, so a release that changes a series in one language and not the
other fails a build instead of shipping two different collections.

PROTOTYPE LIMITATIONS
    Every number in this file is demonstration data, exactly like
    ``prototype_data.py``: plausible values for the demo workspace, never real
    published figures. The real pilot datasets arrive as manifest + data files
    and replace the inline series here.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from cedar_press.claims import CLAIM_CLASS

__all__ = [
    "COLLECTION_FIGURES",
    "LAUNCH_COLLECTION",
    "CollectionDataset",
    "CollectionFigure",
    "CollectionFindings",
    "CollectionLead",
    "CollectionNeed",
    "CollectionSupported",
    "FigurePoint",
    "collection_citation",
    "collection_context_line",
    "collection_csv",
    "collection_findings",
    "figures_by_downloads",
]


@dataclass(frozen=True)
class CollectionDataset:
    """One curated dataset's descriptor, mirroring the manifest contract.

    ``rows_label`` is display copy, not a count the code trusts.

    ``origin`` and ``level`` use the evidence registry's vocabulary
    (``SOURCE_ORIGIN``, ``SOURCE_AVAILABILITY``). All three launch datasets
    are Lumecon-built curations over public records, and saying so is the
    point: the raw records exist elsewhere, the reconciled, entity-matched,
    versioned dataset exists because Lumecon assembled it. ``level`` says
    what the rows are: entity records, or entity records that also roll up
    to geography.
    """

    id: str
    name: str
    short_name: str
    origin: str
    level: str
    tracks: str
    rows_label: str
    downloads: int
    vintage: str
    version: str
    updated: str
    sources: str
    method: str


LAUNCH_COLLECTION: tuple[CollectionDataset, ...] = (
    CollectionDataset(
        id="deals",
        origin="lumecon",
        level="entity",
        name="Indian Country Deals",
        short_name="Deals",
        tracks=(
            "Documented public transactions under published inclusion rules: "
            "acquisitions, property purchases, project financings, bond issuances "
            "and major capital projects, 2010 to current."
        ),
        rows_label="1,248 rows",
        downloads=1610,
        vintage="2026 Q2",
        version="v9",
        updated="Jul 15",
        sources="Primary-source target · TBN archive",
        method=(
            "Announced and closed are labeled separately, and a transaction enters "
            "totals only when its status is confirmed against a primary source. "
            "Inclusion rules are published with every release, so a missing row is "
            "a known gap, not a silent one."
        ),
    ),
    CollectionDataset(
        id="contractors",
        origin="lumecon",
        level="entity",
        name="Native Federal Contractors",
        short_name="Contractors",
        tracks=(
            "Tribally owned firms, ANC and NHO subsidiaries and 8(a) participants, "
            "matched to parent entities, with award histories."
        ),
        rows_label="3,904 entities",
        downloads=2140,
        vintage="2026 Q2",
        version="v6",
        updated="Jul 12",
        sources="SAM · SBA · FPDS · USAspending",
        method=(
            "Collected weekly, reconciled and versioned quarterly. The "
            "parent-entity matching is the curation: awards roll up to the owning "
            "tribe, ANC or NHO, and provisional matches are labeled until "
            "registration confirms them."
        ),
    ),
    CollectionDataset(
        id="funding",
        origin="lumecon",
        level="both",
        name="Federal Funding to Indian Country",
        short_name="Funding",
        tracks=(
            "Grants and federal assistance to tribes and Native organizations: who "
            "received what, from which program, when."
        ),
        rows_label="28,517 awards",
        downloads=940,
        vintage="FY2025 + YTD",
        version="v4",
        updated="Jul 12",
        sources="USAspending assistance",
        method=(
            "USAspending assistance records in v1, sharing the contractor "
            "dataset's entity matching. Figures for the current fiscal year are "
            "partial until the quarterly release lands, and the page says so "
            "wherever they appear."
        ),
    ),
)


def collection_context_line() -> str:
    """One line for the context strip: versions and the latest refresh date."""
    versions = " · ".join(f"{d.short_name} {d.version}" for d in LAUNCH_COLLECTION)
    updated = sorted(d.updated for d in LAUNCH_COLLECTION)[-1]
    return f"{versions} · all current as of {updated}"


@dataclass(frozen=True)
class CollectionSupported:
    """A finding the collection supports, in the organizational claim shape."""

    id: str
    text: str
    basis: str
    claim_class: str
    confidence: str
    fidelity: str
    recipe_id: str | None = None


@dataclass(frozen=True)
class CollectionNeed:
    """An honesty item: a row awaiting confirmation or a release still partial."""

    id: str
    text: str


@dataclass(frozen=True)
class CollectionLead:
    """A story lead and the evidence it rests on, in the narrative shape."""

    id: str
    name: str
    have: int
    need: int
    missing: tuple[str, ...]
    requires: tuple[str, ...]


@dataclass(frozen=True)
class CollectionFindings:
    """The three feeds the collection Overview renders, together."""

    supported: tuple[CollectionSupported, ...]
    needs: tuple[CollectionNeed, ...]
    narratives: tuple[CollectionLead, ...]


def collection_findings() -> CollectionFindings:
    """What the collection supports today, in the findings shapes.

    Class and confidence are held as separate dimensions, the basis names the
    dataset and version, and fidelity is ``direct`` because the collection
    measures what it names rather than standing a wider geography in.
    """
    supported = (
        CollectionSupported(
            id="col-contracting-up",
            text="Federal contracting to Native entities rose for a fourth straight quarter.",
            basis="Contractors v6, FPDS and USAspending.",
            claim_class=CLAIM_CLASS.descriptive,
            confidence="high",
            fidelity="direct",
        ),
        CollectionSupported(
            id="col-deals-record",
            text="Announced deal volume in 2025 runs ahead of every prior year in the series.",
            basis="Deals v9, announced and closed labeled separately.",
            claim_class=CLAIM_CLASS.descriptive,
            confidence="high",
            fidelity="direct",
        ),
        CollectionSupported(
            id="col-sector-lead",
            text="Energy and project finance lead 2025 announced transactions, ahead of hospitality.",
            basis="Deals v9, sector taxonomy.",
            claim_class=CLAIM_CLASS.comparative,
            confidence="moderate",
            fidelity="direct",
        ),
    )

    needs = (
        CollectionNeed(
            id="col-need-closing",
            text=(
                "Three large announced deals await closing confirmation before they "
                "enter totals (Deals v9, primary source pending)."
            ),
        ),
        CollectionNeed(
            id="col-need-fy26",
            text=(
                "FY2026 assistance figures are partial until the Q1 release lands "
                "(Funding v4, USAspending publication lag)."
            ),
        ),
        CollectionNeed(
            id="col-need-matches",
            text=(
                "Two parent-entity matches are provisional pending SAM "
                "re-registration (Contractors v6, entity resolution queue)."
            ),
        ),
    )

    narratives = (
        CollectionLead(
            id="col-lead-energy",
            name="Energy project financing expansion",
            have=3,
            need=3,
            missing=(),
            requires=("Deal series", "Sector taxonomy", "Primary confirmations"),
        ),
        CollectionLead(
            id="col-lead-8a",
            name="8(a) participation and award growth",
            have=3,
            need=3,
            missing=(),
            requires=("Entity matches", "Award histories", "Certification lists"),
        ),
        CollectionLead(
            id="col-lead-assist",
            name="Assistance shifts under new appropriations",
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
    """

    id: str
    title: str
    basis: str
    kind: str
    points: tuple[FigurePoint, ...] = field(default_factory=tuple)


COLLECTION_FIGURES: tuple[CollectionFigure, ...] = (
    CollectionFigure(
        id="deals",
        title="Announced deals by quarter",
        basis="Deals v9",
        kind="bars",
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
        basis="Contractors v6",
        kind="leader",
        points=(
            FigurePoint(label="Parent entity A", value=100),
            FigurePoint(label="Parent entity B", value=78),
            FigurePoint(label="Parent entity C", value=65),
            FigurePoint(label="Parent entity D", value=48),
        ),
    ),
    CollectionFigure(
        id="funding",
        title="Federal assistance, trend",
        basis="Funding v4",
        kind="trend",
        points=(
            FigurePoint(label="FY21", value=52, compare=44),
            FigurePoint(label="FY22", value=58, compare=46),
            FigurePoint(label="FY23", value=55, compare=45),
            FigurePoint(label="FY24", value=71, compare=49),
            FigurePoint(label="FY25", value=84, compare=52),
        ),
    ),
)


def _dataset_for(dataset_id: str) -> CollectionDataset | None:
    """The descriptor behind a figure or download, or ``None`` for an unknown id.

    ``None`` rather than a raise because the ids arrive from the UI layer, and an
    unknown one should render as an absent card, not a crash.
    """
    return next((d for d in LAUNCH_COLLECTION if d.id == dataset_id), None)


def figures_by_downloads() -> tuple[CollectionFigure, ...]:
    """The collection's figures, most-downloaded dataset first.

    The public shelf orders by demonstrated use, the same signal the request
    rail counts. Download counts are demonstration data like every number
    here; the real counter is server work that lands with the first release.
    """

    def downloads(figure: CollectionFigure) -> int:
        dataset = _dataset_for(figure.id)
        return dataset.downloads if dataset else 0

    return tuple(sorted(COLLECTION_FIGURES, key=downloads, reverse=True))


def collection_citation(dataset_id: str, accessed_on: str | None = None) -> str | None:
    """The canonical citation for a collection dataset.

    The citation register records who cited a dataset; this is the other half
    of that loop, the sentence to cite it WITH. A dataset that is easy to cite
    correctly gets cited by name and version, corrections can find everyone
    who relied on a release, and Lumecon's name travels with every derivative
    table. Version and vintage are load-bearing, not garnish.

    ``accessed_on`` is a pre-formatted date string supplied by the caller, so
    this stays pure and byte-comparable with the JS implementation.
    """
    dataset = _dataset_for(dataset_id)
    if dataset is None:
        return None
    accessed = f" Accessed {accessed_on}." if accessed_on else ""
    return (
        f'Lumecon, "{dataset.name}" ({dataset.version}, vintage {dataset.vintage}), '
        f"Cedar Press collection, cedarpress.ai.{accessed}"
    )


def _csv_cell(value: object) -> str:
    """One CSV cell, quoted only when the value needs it.

    Ordinary cells stay byte-identical to what they were before quoting
    existed; only a cell carrying a comma, a quote or a newline is wrapped.
    """
    text = "" if value is None else str(value)
    if any(ch in text for ch in ('"', ",", "\n")):
        return '"' + text.replace('"', '""') + '"'
    return text


def collection_csv(dataset_id: str) -> str | None:
    """The rows behind a dataset card's Download button.

    The figure's own points, so what downloads is exactly what the card shows.
    Real datasets download their full release files; this is the prototype's
    honest stand-in, and the header row says which release it came from.

    The last row is the citation. A downloaded file outlives the page it came
    from, so the file itself must say what it is, whose work it is and how to
    credit it; provenance that lives only in the UI is provenance the reader
    loses on save.
    """
    figure = next((f for f in COLLECTION_FIGURES if f.id == dataset_id), None)
    dataset = _dataset_for(dataset_id)
    if figure is None or dataset is None:
        return None
    # A two-series figure downloads both series: the card draws value and
    # compare together, and a file that cannot reproduce the comparison line
    # is not the figure's own points.
    has_compare = any(point.compare is not None for point in figure.points)
    release = f"{dataset.name} {dataset.version}"
    header = ["period", "value", "compare", release] if has_compare else ["period", "value", release]

    def _row(point: FigurePoint) -> list[str]:
        if not has_compare:
            return [point.label, _format_value(point.value), ""]
        compare = _format_value(point.compare) if point.compare is not None else ""
        return [point.label, _format_value(point.value), compare, ""]

    rows = [_row(point) for point in figure.points]
    citation = (
        ["cite_as", collection_citation(dataset_id) or "", "", ""]
        if has_compare
        else ["cite_as", collection_citation(dataset_id) or "", ""]
    )
    return "\n".join(",".join(_csv_cell(cell) for cell in row) for row in [header, *rows, citation])


def _format_value(value: float) -> str:
    """Match the JS module's CSV cells: integers print without a decimal."""
    if float(value).is_integer():
        return str(int(value))
    return str(value)
