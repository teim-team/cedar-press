"""Exact-proof admission for the small committed NEED preview only.

The producer release and public component are pinned independently. Copying a
metadata proof onto unrelated CSV bytes never authorizes a sample. This module
does not make other NEED components or full downloads publishable.
"""

from __future__ import annotations

import base64
import binascii
import csv
import hashlib
import io
import json
import re
from pathlib import Path

from cedar_press.need_publication import COMPONENT, reviewed_base_permitted

URL = "/data/cedar/samples/need/spreadsheet__10.csv"
ENVELOPE = "data/cedar/need-reviewed-preview.json"
LIMIT = 8 * 1024 * 1024


def _bytes(path, root):
    path = Path(path)
    if not path.resolve().is_relative_to(Path(root).resolve()) or path.stat().st_size > LIMIT:
        raise ValueError("Preview proof path or size refused")
    content = path.read_bytes()
    if len(content) > LIMIT:
        raise ValueError("Preview proof grew beyond its bound")
    return content


def need_preview_permitted(repo, collection, table, sample_path=None):
    """True only for the exact pinned facts-only CSV and the existing proof."""
    from cedar_press.repository import _canonical_bytes
    from cedar_press.spreadsheet import _cell

    try:
        if collection.get("id") != "need" or table.get("table") != "need.csv":
            return False
        sample = collection.get("sample", {})
        pin = collection.get("verified_preview", {})
        if sample.get("path") != URL or table.get("sample_path") != URL:
            return False
        declared = [
            candidate
            for candidate in collection.get("tables", [])
            if candidate.get("sample_path") == URL
        ]
        if len(declared) != 1 or declared[0] != table:
            return False
        if pin.get("component") != COMPONENT or pin.get("envelope") != ENVELOPE:
            return False
        if not all(
            isinstance(pin.get(key), str) and re.fullmatch(r"[0-9a-f]{64}", pin[key])
            for key in ("release_id", "manifest_sha256", "envelope_sha256", "sample_sha256")
        ):
            return False
        raw = _bytes(Path(repo) / ENVELOPE, repo)
        if hashlib.sha256(raw).hexdigest() != pin.get("envelope_sha256"):
            return False
        envelope = json.loads(raw)
        if envelope.get("schema_version") != 1:
            return False
        manifest = envelope["manifest"]
        if (
            manifest.get("collection_id") != "need"
            or manifest.get("synthetic") is not False
            or manifest.get("release_id") != pin.get("release_id")
            or sample.get("release_id") != pin.get("release_id")
            or hashlib.sha256(_canonical_bytes(manifest)).hexdigest() != pin.get("manifest_sha256")
            or sample.get("manifest_sha256") != pin.get("manifest_sha256")
        ):
            return False
        entry = manifest["components"][COMPONENT]
        if not reviewed_base_permitted(manifest, COMPONENT, entry):
            return False
        artifact = base64.b64decode(envelope["records_jsonl_base64"], validate=True)
        expected = entry["files"]["records.jsonl"]
        if len(artifact) > LIMIT or len(artifact) != expected["bytes"]:
            return False
        if hashlib.sha256(artifact).hexdigest() != expected["sha256"]:
            return False
        rows = [json.loads(line) for line in artifact.splitlines()]
        if len(rows) != entry["record_count"] or len(rows) != pin.get("public_records"):
            return False
        if table.get("rows_published") != len(rows) or sample.get("of") != len(rows):
            return False
        names = [field["name"] for field in entry["fields"]]
        if len(names) != len(set(names)):
            return False
        header = ["record_type", "record_key", "record_grain", *sorted(names)]
        expected_rows = set()
        keys = set()
        for row in rows:
            if not isinstance(row, dict) or set(row) != set(names):
                return False
            key_values = [row[column] for column in entry["primary_key"]]
            if any(value is None or value == "" for value in key_values):
                return False
            key = json.dumps(key_values, ensure_ascii=False, separators=(",", ":"))
            # Owner ruling 2026-10-04: a row's review status no longer refuses
            # the preview; only a duplicate key does.
            if key in keys:
                return False
            keys.add(key)
            expected_rows.add(
                tuple(
                    _cell(value)
                    for value in [
                        COMPONENT,
                        key,
                        entry["row_grain"],
                        *[row[name] for name in sorted(names)],
                    ]
                )
            )
        supplied = sample_path() if callable(sample_path) else sample_path
        path = Path(supplied) if supplied is not None else Path(repo) / "public" / URL.lstrip("/")
        csv_bytes = _bytes(path, repo)
        if hashlib.sha256(csv_bytes).hexdigest() != pin.get("sample_sha256"):
            return False
        reader = csv.reader(io.StringIO(csv_bytes.decode("utf-8"), newline=""), strict=True)
        if next(reader, []) != header:
            return False
        sampled = [tuple(row) for row in reader]
        if len(sampled) != min(10, len(rows)) or len(set(sampled)) != len(sampled):
            return False
        if sample.get("rows") != len(sampled) or sample.get("columns") != len(header):
            return False
        return all(row in expected_rows for row in sampled)
    except (
        OSError,
        ValueError,
        TypeError,
        KeyError,
        AttributeError,
        UnicodeError,
        binascii.Error,
        csv.Error,
    ):
        return False


def current_need_preview_permitted(repo):
    """Check the declared current sample, never an arbitrary NEED file."""
    try:
        manifest = json.loads(
            (Path(repo) / "data/cedar/collections.manifest.json").read_text(encoding="utf-8")
        )
        selected = [entry for entry in manifest["collections"] if entry.get("id") == "need"]
        if len(selected) != 1:
            return False
        collection = selected[0]
        tables = [
            table
            for table in collection["tables"]
            if table.get("sample_path") == collection.get("sample", {}).get("path")
        ]
        return len(tables) == 1 and need_preview_permitted(repo, collection, tables[0])
    except (OSError, ValueError, TypeError, KeyError, AttributeError):
        return False
