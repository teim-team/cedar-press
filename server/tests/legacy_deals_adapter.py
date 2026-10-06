"""Adapter from the legacy 40-column Deals preview to the 36-column producer header.

Documents, as code a test can hold, how a row of the historical
``deals_classified`` extract (the shape ``server/tests/fixtures/legacy-preview/
samples/deals/deals_classified__10.csv`` carries, with PR #149's ten reviewed
``CEV-*`` events) maps onto the header the producer's pinned Deals release
kept at ``data/cedar/samples/deals/spreadsheet__10.csv``. Every
decision is read from ``data/cedar/field_map.json`` (``deals/deals_classified``),
the owner's 2026-09-05 specification; nothing here is a new decision.

The arithmetic the task asked for, 40 legacy columns to 36 served:

- **6 dropped** (``internal`` or ``document``): ``Event_Quarter``,
  ``Event_Month`` (derivable), ``Confidence`` (verification_status carries
  the meaning), ``Date_Added`` (classification timestamp), ``Data_As_Of``
  (release metadata), ``native_party_attribution_tier`` (not in the approved
  list);
- **3 pairs fold to one column each** (net 3 fewer): ``Source_2`` +
  ``Source_2_Type`` -> ``additional_sources`` (a JSON list, mechanical);
  ``Deal_Category`` + ``transaction_type`` -> ``deal_type`` and ``Status`` +
  ``deal_status_std`` -> ``deal_status`` (each through a value-level
  crosswalk, never "whichever is nonblank");
- ``Event_Type`` -> ``transaction_structure`` (crosswalk) and ``Notes`` ->
  ``research_note`` (editorial pass, BLOCKING while Notes is populated and no
  note has been supplied) are one-to-one and change the count by nothing;
  the remaining 25 columns rename or keep one-to-one;
- **2 added from the register** by uid: ``entity_class``, ``cedar_entity_role``
  (blank: a party relationship is published only when evidence establishes
  it);
- **3 reserved record columns** the producer spreadsheet carries on every
  row: ``record_type``, ``record_key``, ``record_grain``.

40 - 6 - 3 + 2 + 3 = 36. So "the four extra" legacy columns are a net of
four, not four named columns: six are dropped, three disappear into pairs,
and five are added.

What the adapter does mechanically: renames and keeps, value for value;
builds ``additional_sources``; fills ``canonical_name`` and ``entity_class``
from the register by ``cedar_uid`` and reports where the legacy
``native_party_canonical_name`` disagreed; writes the three record columns;
orders the header exactly as served (reserved columns, then the approved
names sorted, which is the producer writer's order, not the field map's
reading order). What it does NOT do, and reports as
owed: the three crosswalk targets stay blank unless a crosswalk is supplied
(``crosswalks={"deal_type": {...}, ...}``) and both sources agree on a value
the crosswalk maps; ``research_note`` stays blank and every populated
``Notes`` is reported as blocking. ``cedar_uid`` is copied, never altered.
Nothing here changes what is served.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FIELD_MAP = ROOT / "data" / "cedar" / "field_map.json"
REGISTER_NAMES = ROOT / "data" / "spine" / "cedar_entity_names.csv"
SERVED_SAMPLE = ROOT / "data" / "cedar" / "samples" / "deals" / "spreadsheet__10.csv"
LEGACY_FIXTURE = (
    ROOT
    / "server"
    / "tests"
    / "fixtures"
    / "legacy-preview"
    / "samples"
    / "deals"
    / "deals_classified__10.csv"
)
TABLE_KEY = "deals/deals_classified"
RESERVED = ("record_type", "record_key", "record_grain")
RECORD_TYPE = "records"
#: The grain string the producer writes on every served Deals row.
RECORD_GRAIN = "one source-described deal or event, not additive project totals"
CROSSWALK_TARGETS = {
    "deal_type": ("Deal_Category", "transaction_type"),
    "deal_status": ("Status", "deal_status_std"),
    "transaction_structure": ("Event_Type",),
}
NOTE_SOURCES = ("Notes", "Caveat", "Candidate_Status")


def field_map_table() -> dict:
    return json.loads(FIELD_MAP.read_text(encoding="utf-8"))["tables"][TABLE_KEY]


def register_names() -> dict[str, tuple[str, str]]:
    """uid -> (published name, entity class), from the spine names file."""
    out = {}
    with REGISTER_NAMES.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            uid = (row.get("cedar_uid") or "").strip()
            if uid:
                out[uid] = (
                    (row.get("name") or "").strip(),
                    (row.get("entity_class") or "").strip(),
                )
    return out


def read_csv(path: Path) -> tuple[list[str], list[dict]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        return list(reader.fieldnames or []), rows


def producer_header(table: dict | None = None) -> list[str]:
    """The served header: the three reserved columns, then the approved
    columns in alphabetical order.

    The field map's ``order`` is the owner's reading order (the CE block first,
    ``research_note`` last); the producer's spreadsheet writer sorts the field
    names (the same rule ``server/cedar_press/need_preview.py`` reconstructs:
    ``["record_type", "record_key", "record_grain", *sorted(names)]``), so the
    served file carries ``additional_sources`` fourth and ``verification_status``
    last. The 33 names are the same set either way.
    """
    table = table or field_map_table()
    return [*RESERVED, *sorted(table["order"])]


def column_mapping(table: dict | None = None) -> list[dict]:
    """One row per legacy column: where it lands, by which decision, and why."""
    table = table or field_map_table()
    out = []
    for field in table["fields"]:
        decision = field["decision"]
        destination = (
            field.get("to")
            if decision in ("rename", "combine", "derive")
            else (field["column"] if decision == "keep" else None)
        )
        out.append(
            {
                "legacy_column": field["column"],
                "decision": decision,
                "destination": destination,
                "mechanical": decision in ("rename", "keep")
                or (decision == "derive" and field.get("to") == "additional_sources"),
                "why": field.get("why", ""),
                "blocking": bool(field.get("blocking")),
            }
        )
    for added in table["new"]:
        out.append(
            {
                "legacy_column": None,
                "decision": "new",
                "destination": added["column"],
                "mechanical": added["from"] == "register",
                "why": added["why"],
                "blocking": False,
            }
        )
    for column in RESERVED:
        out.append(
            {
                "legacy_column": None,
                "decision": "reserved",
                "destination": column,
                "mechanical": True,
                "why": "Producer spreadsheet record column, written on every row.",
                "blocking": False,
            }
        )
    return out


def decomposition(table: dict | None = None) -> dict:
    """The counts behind 40 -> 36, computed from the field map, not typed."""
    table = table or field_map_table()
    fields = table["fields"]
    legacy = [f["column"] for f in fields if f["column"] in LEGACY_COLUMNS(table)]
    dropped = [f["column"] for f in fields if f["decision"] in ("internal", "document")]
    targets: dict[str, list[str]] = {}
    for f in fields:
        if f["decision"] in ("combine", "derive"):
            targets.setdefault(f["to"], []).append(f["column"])
    pairs = {t: s for t, s in targets.items() if len(s) > 1}
    one_to_one = {t: s for t, s in targets.items() if len(s) == 1}
    added_from_register = [
        n["column"]
        for n in table["new"]
        if n["from"] == "register" or n["column"] == "cedar_entity_role"
    ]
    header = producer_header(table)
    return {
        "legacy_columns": len(legacy),
        "dropped": dropped,
        "pairs_folded": pairs,
        "one_to_one_derivations": one_to_one,
        "added_from_register": sorted(added_from_register),
        "reserved": list(RESERVED),
        "served_columns": len(header),
        "net_difference": len(legacy) - len(header),
        "arithmetic": (
            f"{len(legacy)} - {len(dropped)} dropped - "
            f"{sum(len(s) - 1 for s in pairs.values())} folded "
            f"+ {len(added_from_register)} from the register "
            f"+ {len(RESERVED)} reserved = {len(header)}"
        ),
    }


def LEGACY_COLUMNS(table: dict) -> set[str]:  # noqa: N802 - reads as a constant
    """The legacy sample's own header per the field map: every field that is
    not itself an approved target supplied by the build (research_note)."""
    return {
        f["column"]
        for f in table["fields"]
        if not (f["decision"] == "keep" and f["column"] == "research_note")
        and f["column"] not in ("Caveat", "Candidate_Status")
    }


def adapt(
    rows: list[dict],
    register: dict[str, tuple[str, str]],
    crosswalks: dict | None = None,
    table: dict | None = None,
) -> dict:
    """Return {"header", "rows", "report"} for the legacy rows. Pure."""
    table = table or field_map_table()
    crosswalks = crosswalks or {}
    header = producer_header(table)
    renames = {f["column"]: f["to"] for f in table["fields"] if f["decision"] == "rename"}
    keeps = {f["column"] for f in table["fields"] if f["decision"] == "keep"}
    report = {
        "rows_in": len(rows),
        "owed": {target: [] for target in CROSSWALK_TARGETS},
        "crosswalked": {target: 0 for target in CROSSWALK_TARGETS},
        "blocking_notes": [],
        "name_disagreements": [],
        "uids_not_in_register": [],
    }
    out = []
    for row in rows:
        new = {column: "" for column in header}
        for legacy, target in renames.items():
            if target in new:
                new[target] = row.get(legacy, "") or ""
        for column in keeps:
            if column in new:
                new[column] = row.get(column, "") or ""
        uid = (row.get("cedar_uid") or "").strip()
        new["cedar_uid"] = uid  # copied, never altered
        name, cls = register.get(uid, ("", ""))
        if uid and uid not in register:
            report["uids_not_in_register"].append(row.get("Deal_ID"))
        new["canonical_name"] = name
        new["entity_class"] = cls
        new["cedar_entity_role"] = ""
        legacy_name = (row.get("native_party_canonical_name") or "").strip()
        if uid in register and legacy_name and legacy_name != name:
            report["name_disagreements"].append((row.get("Deal_ID"), legacy_name, name))
        new["additional_sources"] = additional_sources(row)
        for target, sources in CROSSWALK_TARGETS.items():
            values = {(row.get(s) or "").strip() for s in sources}
            values.discard("")
            mapping = crosswalks.get(target, {})
            if len(values) == 1 and next(iter(values)) in mapping:
                new[target] = mapping[next(iter(values))]
                report["crosswalked"][target] += 1
            else:
                new[target] = ""
                report["owed"][target].append((row.get("Deal_ID"), sorted(values)))
        new["research_note"] = ""
        if any((row.get(s) or "").strip() for s in NOTE_SOURCES):
            report["blocking_notes"].append(row.get("Deal_ID"))
        new["record_type"] = RECORD_TYPE
        new["record_key"] = json.dumps([new["deal_id"]], ensure_ascii=False, separators=(",", ":"))
        new["record_grain"] = RECORD_GRAIN
        out.append(new)
    report["rows_out"] = len(out)
    report["blocking"] = bool(report["blocking_notes"])
    return {"header": header, "rows": out, "report": report}


def additional_sources(row: dict) -> str:
    """rule additional_sources: Source_2 and Source_2_Type as a JSON list."""
    url = (row.get("Source_2") or "").strip()
    if not url:
        return "[]"
    return json.dumps(
        [{"url": url, "source_type": (row.get("Source_2_Type") or "").strip()}],
        ensure_ascii=False,
        separators=(",", ":"),
    )
