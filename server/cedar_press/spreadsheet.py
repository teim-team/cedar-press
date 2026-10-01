"""One researcher CSV assembled only from the existing verified download path."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import re
import tempfile
from contextlib import closing

from cedar_press import repository as r

RESERVED = ("record_type", "record_key", "record_grain")


def _layout(collection, pin, manifest):
    groups = []
    signatures = {}
    logical = {entry["name"]: entry for entry in manifest.get("partitioned_components", [])}
    for name in r.grove_components(collection):
        parts = (
            [part["component"] for part in logical[name]["parts"]] if name in logical else [name]
        )
        if any(part not in manifest["components"] for part in parts):
            continue
        try:
            descriptor = r._grove_component_release(pin, manifest, name, metadata_only=True)
        except r.ComponentPublicationHeld:
            continue
        contract = manifest["components"][parts[0]]
        for part in parts:
            candidate = manifest["components"][part]
            if any(
                candidate.get(key) != contract.get(key)
                for key in (
                    "row_grain",
                    "fields",
                    "primary_key",
                    "rights",
                    "publication_status_field",
                )
            ) or candidate.get("status_value_fields", []) != contract.get(
                "status_value_fields", []
            ):
                raise r.FullReleaseUnavailable("Spreadsheet partition meanings disagree")
        for field in contract["fields"]:
            signature = json.dumps(
                {k: field.get(k) for k in ("type", "unit", "description")}, sort_keys=True
            )
            signatures.setdefault(field["name"], set()).add(signature)
        groups.append((name, contract, descriptor))
    if not groups:
        raise r.FullReleaseUnavailable("No permitted spreadsheet records")
    columns = {}
    mappings = {}
    origins = {}
    for name, contract, _ in groups:
        mapping = {}
        for field in contract["fields"]:
            source = field["name"]
            target = (
                f"{name}__{source}" if len(signatures[source]) > 1 or source in RESERVED else source
            )
            definition = {k: field.get(k) for k in ("type", "unit", "description")}
            if target in RESERVED or (
                target in columns and (columns[target] != definition or origins[target] != source)
            ):
                raise r.FullReleaseUnavailable("Spreadsheet column collision")
            origins[target] = source
            columns[target] = definition
            mapping[source] = target
        mappings[name] = mapping
    return groups, [*RESERVED, *sorted(columns)], mappings


def metadata(collection):
    """Advertise a single file only when the pinned collection can be verified."""
    try:
        return download(collection, metadata_only=True)
    except (r.FullReleaseUnavailable, OSError, ValueError, KeyError, TypeError):
        return None


def _cell(value):
    if value is None:
        return ""
    if isinstance(value, (list, dict)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    text = str(value)
    if (
        isinstance(value, str)
        and text.lstrip().startswith(("=", "+", "-", "@"))
        and not re.fullmatch(r"-?[0-9]+(?:\.[0-9]+)?", text)
    ):
        return "'" + text
    return text


def download(collection, release_id=None, *, metadata_only=False):
    """Pins and every component's byte, schema, key and rights checks stay binding."""
    r.assert_collection_publishable(collection)
    if not r.is_component_release(collection):
        return _single_dataset(collection, release_id, metadata_only=metadata_only)
    pin = r.grove_release_pin(collection)
    if not metadata_only and pin["release_id"] != release_id:
        raise r.FullReleaseUnavailable("Requested release is not the approved catalog pin")
    r._grove_catalog(pin)
    manifest = r._grove_manifest(pin)
    groups, columns, mappings = _layout(collection, pin, manifest)
    descriptor = {
        "kind": "spreadsheet",
        "format": "csv",
        "release_id": pin["release_id"],
        "fields": columns,
        "filename": f"{collection}.csv",
        "scope": "One observation per row, with record type, grain and original source fields.",
        "download_path": (
            f"/press/collections/{collection}/spreadsheet-download?release_id={pin['release_id']}"
        ),
    }
    if metadata_only:
        return descriptor
    output = tempfile.TemporaryFile(mode="w+b")  # noqa: SIM115 - response owns this spool
    digest = hashlib.sha256()
    total = 0

    def write(values):
        line = io.StringIO(newline="")
        csv.writer(line, lineterminator="\n").writerow([_cell(value) for value in values])
        content = line.getvalue().encode("utf-8")
        output.write(content)
        digest.update(content)

    try:
        write(columns)
        for name, contract, _ in groups:
            part = r._grove_component_release(pin, manifest, name)
            with closing(part["content_file"]) as content:
                for line in content:
                    row = json.loads(line)
                    if row.get(contract.get("publication_status_field")) in {
                        "held",
                        "contested",
                        "withheld",
                    }:
                        continue
                    record = {target: row[source] for source, target in mappings[name].items()}
                    record.update(
                        record_type=name,
                        record_key=json.dumps(
                            [row[key] for key in contract["primary_key"]],
                            ensure_ascii=False,
                            separators=(",", ":"),
                        ),
                        record_grain=contract.get("row_grain", "See source definitions"),
                    )
                    write(record.get(column) for column in columns)
                    total += 1
        output.seek(0)
        return {
            **descriptor,
            "content_file": output,
            "record_count": total,
            "sha256": digest.hexdigest(),
            "media_type": "text/csv; charset=utf-8",
            "citation": r.launch.collection_citation(collection)
            or f"Lumecon, {collection}, Cedar collection.",
        }
    except BaseException:
        output.close()
        raise


def _single_dataset(collection, release_id, *, metadata_only):
    """The existing flagship is already one grain; give it the same CSV interface."""
    source = r.full_release(collection, release_id, metadata_only=metadata_only)
    rid = source["release_id"]
    descriptor = {
        "kind": "spreadsheet",
        "format": "csv",
        "release_id": rid,
        "fields": source["fields"],
        "filename": f"{collection}.csv",
        "scope": source.get("scope", "One source observation per row."),
        "download_path": f"/press/collections/{collection}/spreadsheet-download?release_id={rid}",
    }
    if metadata_only:
        return descriptor
    content = source.get("content_file") or source.get("spool") or io.BytesIO(source["content"])
    output = tempfile.TemporaryFile(mode="w+b")  # noqa: SIM115 - response owns this spool
    digest = hashlib.sha256()
    count = 0
    try:
        with closing(content):

            def write(values):
                line = io.StringIO(newline="")
                csv.writer(line, lineterminator="\n").writerow([_cell(value) for value in values])
                value = line.getvalue().encode("utf-8")
                output.write(value)
                digest.update(value)

            write(source["fields"])
            for line in content:
                row = json.loads(line)
                write(row[name] for name in source["fields"])
                count += 1
        if count != source["record_count"]:
            raise r.FullReleaseUnavailable("Spreadsheet count differs from verified records")
        output.seek(0)
        return {
            **descriptor,
            "content_file": output,
            "record_count": count,
            "sha256": digest.hexdigest(),
            "media_type": "text/csv; charset=utf-8",
            "citation": source["citation"],
        }
    except BaseException:
        output.close()
        raise
