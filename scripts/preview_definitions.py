"""Resolve preview definitions without guessing source-role or rename semantics.

The producer definition wins when substantive. A legacy fallback is allowed
only for a unique kept, withheld or explicitly renamed source field in the
reviewed field map. Derived fields and combines require their own definition.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

METADATA_MEANINGS = {
    "record_type": "The permitted logical record type from the pinned release.",
    "record_key": "The original source primary-key values serialized as JSON.",
    "record_grain": "What one observation of this record type represents; never sum across overlapping grains.",
}


def is_substantive(value: Any, column: str) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    text = value.strip().casefold()
    source_column = column.rsplit("__", 1)[-1]
    if text.startswith("reviewed cedar field contract:"):
        return False
    return text not in {
        "see the exact release contract.",
        "see the exact release contract",
        column.casefold(),
        column.replace("_", " ").casefold(),
        source_column.casefold(),
        source_column.replace("_", " ").casefold(),
    }


def load_overrides(
    repo: Path, producer: Path | None = None
) -> dict[str, dict[str, dict[str, Any]]]:
    """Read maintained definitions and verify their evidence bytes before use."""
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "cedar_preview_definition_overrides",
        Path(__file__).resolve().with_name("preview_definition_overrides.py"),
    )
    if spec is None or spec.loader is None:
        raise ValueError("Preview override loader could not be loaded")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.load(repo, producer, is_substantive=is_substantive)


def _legacy_candidates(
    collection: str, codebook: Mapping[str, Any], field_map: Mapping[str, Any]
) -> tuple[dict[str, list[dict[str, Any]]], dict[str, list[str]]]:
    candidates: dict[str, list[dict[str, Any]]] = {}
    rejected: dict[str, list[str]] = {}
    for key, contract in field_map.get("tables", {}).items():
        if contract.get("collection") != collection:
            continue
        book = codebook.get("tables", {}).get(key)
        if not isinstance(book, Mapping) or book.get("collection") != collection:
            continue
        decisions: dict[str, list[Mapping[str, Any]]] = {}
        for field in contract.get("fields", []):
            decisions.setdefault(field.get("column", ""), []).append(field)
        order = set(contract.get("order", []))
        for field in book.get("fields", []):
            column = field.get("column", "")
            if field.get("add"):
                rejected.setdefault(column, []).append(
                    f"{key}.{column}: derived opening or added field requires its current definition"
                )
                continue
            matches = decisions.get(column, [])
            if len(matches) != 1:
                rejected.setdefault(column, []).append(
                    f"{key}.{column}: no unique source-field decision"
                )
                continue
            decision = matches[0]
            kind = decision.get("decision")
            target = decision.get("to") if kind == "rename" else column
            if kind not in {"keep", "withhold", "rename"} or not isinstance(
                target, str
            ):
                rejected.setdefault(str(decision.get("to") or column), []).append(
                    f"{key}.{column}: {kind} is not a direct source-field definition"
                )
                continue
            if target not in order:
                rejected.setdefault(target, []).append(
                    f"{key}.{column}: target is not in the reviewed output order"
                )
                continue
            if (
                kind == "rename"
                and field.get("rename_to") != target
                or kind != "rename"
                and field.get("rename_to")
                or field.get("combine_into")
            ):
                rejected.setdefault(target, []).append(
                    f"{key}.{column}: codebook and field map disagree on the transformation"
                )
                continue
            if not is_substantive(field.get("meaning"), column):
                rejected.setdefault(target, []).append(
                    f"{key}.{column}: legacy meaning is blank or a placeholder"
                )
                continue
            candidates.setdefault(target, []).append(
                {
                    "column": target,
                    "label": field.get("label") or target.replace("_", " "),
                    "meaning": field["meaning"],
                    "definition_source": {
                        "kind": "reviewed_field_map_source",
                        "table_key": key,
                        "source_column": column,
                        "decision": kind,
                        "target_column": target,
                    },
                }
            )
    return candidates, rejected


def resolve_fields(
    collection: str,
    header: Sequence[str],
    producer_fields: Mapping[str, Any],
    legacy_codebook: Mapping[str, Any],
    field_map: Mapping[str, Any],
    *,
    description_origin: str = "producer_description",
    overrides: Mapping[str, Mapping[str, Mapping[str, Any]]] | None = None,
) -> dict[str, Any]:
    if (
        not header
        or len(set(header)) != len(header)
        or any(not name for name in header)
    ):
        raise ValueError("Missing or duplicate spreadsheet header")
    candidates, rejected = _legacy_candidates(collection, legacy_codebook, field_map)
    current_overrides = dict((overrides or {}).get(collection, {}))
    if set(current_overrides) - set(header):
        raise ValueError(
            "Override columns absent from current spreadsheet: "
            + ", ".join(sorted(set(current_overrides) - set(header)))
        )
    fields = []
    unresolved = []
    for column in header:
        metadata = producer_fields.get(column, {})
        description = (
            metadata.get("description") if isinstance(metadata, Mapping) else None
        )
        if column in METADATA_MEANINGS:
            fields.append(
                {
                    "column": column,
                    "label": column.replace("_", " "),
                    "meaning": METADATA_MEANINGS[column],
                    "definition_source": {"kind": "spreadsheet_metadata_contract"},
                }
            )
        elif column in current_overrides and (
            not is_substantive(description, column)
            or (
                isinstance(metadata.get("definition_source"), Mapping)
                and metadata["definition_source"].get("kind")
                == "reviewed_transform_contract"
                and metadata["definition_source"].get("override_key")
                == f"{collection}.{column}"
            )
        ):
            fields.append(dict(current_overrides[column]))
        elif is_substantive(description, column):
            fields.append(
                {
                    "column": column,
                    "label": metadata.get("label") or column.replace("_", " "),
                    "meaning": description,
                    "definition_source": dict(metadata["definition_source"])
                    if isinstance(metadata.get("definition_source"), Mapping)
                    else {"kind": description_origin},
                }
            )
        else:
            options = candidates.get(column, [])
            if len(options) == 1:
                fields.append(options[0])
            else:
                unresolved.append(
                    {
                        "collection": collection,
                        "column": column,
                        "reason": "ambiguous_target"
                        if options
                        else "no_substantive_direct_definition",
                        "candidates": options,
                        "rejected_candidates": rejected.get(column, []),
                    }
                )
    return {
        "collection": collection,
        "header": list(header),
        "fields": fields,
        "unresolved": unresolved,
    }


def require_fields(*args: Any, **kwargs: Any) -> list[dict[str, Any]]:
    result = resolve_fields(*args, **kwargs)
    if result["unresolved"]:
        raise ValueError(
            "Substantive preview definitions unresolved: "
            + json.dumps(result["unresolved"], sort_keys=True, ensure_ascii=False)
        )
    return result["fields"]


def _read(path: Path) -> tuple[dict[str, Any], str]:
    data = path.read_bytes()
    return json.loads(data), hashlib.sha256(data).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument(
        "--producer", help="Producer checkout used to verify pinned definition evidence"
    )
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    root = Path(args.root).resolve(strict=True)
    paths = {
        "codebook": root / "data/cedar/codebook.json",
        "field_map": root / "data/cedar/field_map.json",
        "manifest": root / "data/cedar/collections.manifest.json",
    }
    overrides_path = root / "data/cedar/preview_definition_overrides.json"
    if overrides_path.exists():
        paths["definition_overrides"] = overrides_path
    loaded = {kind: _read(path) for kind, path in paths.items()}
    codebook = loaded["codebook"][0]
    field_map = loaded["field_map"][0]
    manifest = loaded["manifest"][0]
    overrides = load_overrides(root, Path(args.producer) if args.producer else None)
    reports = []
    replacements = {}
    for entry in manifest["collections"]:
        sample = entry.get("sample") or {}
        if not str(sample.get("path", "")).endswith("/spreadsheet__10.csv"):
            continue
        collection = entry["id"]
        table = sample.get("table", "")
        if (
            not isinstance(table, str)
            or not table.endswith(".csv")
            or Path(table).name != table
        ):
            raise ValueError(f"Unambiguous manifest table name required: {collection}")
        key = f"{collection}/{table[:-4]}"
        book = codebook["tables"].get(key)
        if not book or book.get("collection") != collection:
            raise ValueError(f"Missing current dictionary: {key}")
        sample_path = (root / "public" / sample["path"].lstrip("/")).resolve(
            strict=True
        )
        if not sample_path.is_relative_to((root / "public").resolve()):
            raise ValueError("Sample escapes public directory")
        with sample_path.open(encoding="utf-8-sig", newline="") as stream:
            header = next(csv.reader(stream))
        if header != [field["column"] for field in book["fields"]]:
            raise ValueError(f"Current dictionary does not match served header: {key}")
        current = {
            field["column"]: {
                "description": field.get("meaning"),
                "label": field.get("label"),
                "definition_source": field.get("definition_source"),
            }
            for field in book["fields"]
        }
        result = resolve_fields(
            collection,
            header,
            current,
            codebook,
            field_map,
            description_origin="existing_installed_definition",
            overrides=overrides,
        )
        reports.append(result)
        if not result["unresolved"]:
            replacements[key] = result["fields"]
    unresolved = sum(len(result["unresolved"]) for result in reports)
    receipt = {
        "schema_version": 1,
        "kind": "preview_definition_resolution",
        "inputs": {
            kind: {"path": str(paths[kind]), "sha256": digest}
            for kind, (_, digest) in loaded.items()
        },
        "collections": reports,
        "unresolved_count": unresolved,
        "applied": bool(args.apply and unresolved == 0),
        "canonical_rows_changed": False,
    }
    report_path = Path(args.report).resolve()
    if report_path.exists():
        raise ValueError("Definition report must be a new file")
    if args.apply and not unresolved:
        # Refuse an intervening edit; only dictionary metadata is touched.
        for kind, path in paths.items():
            if hashlib.sha256(path.read_bytes()).hexdigest() != loaded[kind][1]:
                raise ValueError(
                    "Dictionary input changed during definition resolution: " + kind
                )
        for key, fields in replacements.items():
            codebook["tables"][key]["fields"] = fields
        encoded = (json.dumps(codebook, ensure_ascii=False, indent=1) + "\n").encode(
            "utf-8"
        )
        paths["codebook"].write_bytes(encoded)
        receipt["output_codebook_sha256"] = hashlib.sha256(encoded).hexdigest()
    with report_path.open("xb") as stream:
        stream.write(
            (json.dumps(receipt, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
        )
    print(
        json.dumps(
            {
                "report": str(report_path),
                "collections": len(reports),
                "unresolved_count": unresolved,
                "applied": receipt["applied"],
            },
            indent=2,
        )
    )
    if args.apply and unresolved:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
