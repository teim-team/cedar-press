#!/usr/bin/env python3
"""Stage exact-release preview assets; never install them or change production pins.

The queue is an array of exactly 15 objects:
  collection, release, store, manifest_sha256
Optional expected_public_rows binds an independently measured public-row count.
Run with both producer src/ and Press server/ on PYTHONPATH. TEMP/TMP must point
to the bounded review volume. Output must be a new directory.
"""

from __future__ import annotations

import argparse
import base64
import copy
import csv
import hashlib
import io
import json
import os
import re
import subprocess
from collections import Counter
from contextlib import closing
from datetime import date
from pathlib import Path

EXPECTED = {
    "contractors",
    "deals",
    "federal-register",
    "foundation-corporate-giving",
    "funding",
    "gaming",
    "legislation",
    "lobbying",
    "nagpra",
    "natural-resources",
    "need",
    "nonprofits",
    "owned",
    "plot",
    "subcontracting",
}
SHA256 = re.compile(r"[0-9a-f]{64}")
COMMIT = re.compile(r"[0-9a-f]{40}")
RESERVED = ("record_type", "record_key", "record_grain")


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def queue_items(value):
    if not isinstance(value, list):
        raise ValueError("Queue must be an explicit array")
    by_id = {}
    for item in value:
        if (
            not isinstance(item, dict)
            or not {"collection", "release", "store", "manifest_sha256"} <= item.keys()
        ):
            raise ValueError("Incomplete queue entry")
        cid = item["collection"]
        if cid not in EXPECTED or cid in by_id:
            raise ValueError("Duplicate or unexpected collection")
        if not all(
            isinstance(item[key], str) and SHA256.fullmatch(item[key])
            for key in ("release", "manifest_sha256")
        ):
            raise ValueError("Queue pins must be exact lowercase SHA-256 values")
        if not isinstance(item["store"], str) or not Path(item["store"]).is_absolute():
            raise ValueError("Queue store must be an absolute path")
        count = item.get("expected_public_rows")
        if count is not None and (type(count) is not int or count < 0):
            raise ValueError("Invalid independent public-row count")
        by_id[cid] = dict(item)
    if set(by_id) != EXPECTED:
        raise ValueError("Queue must pin all 15 collections exactly once")
    return by_id


def read_preview(content, metadata, layout):
    """Read the complete verified CSV; retain a deterministic ten-row preview."""
    content.seek(0)
    digest = hashlib.sha256()
    observed_bytes = 0
    while chunk := content.read(1024 * 1024):
        digest.update(chunk)
        observed_bytes += len(chunk)
    if digest.hexdigest() != metadata["sha256"] or observed_bytes != metadata["bytes"]:
        raise ValueError("Spreadsheet bytes differ from producer receipt")
    content.seek(0)
    text = io.TextIOWrapper(content, encoding="utf-8", newline="")
    groups = [group["name"] for group in layout["groups"]]
    counts = Counter({name: 0 for name in groups})
    samples = {name: [] for name in groups}
    previous_limit = csv.field_size_limit(64 * 1024 * 1024)
    try:
        reader = csv.reader(text, strict=True)
        header = next(reader, [])
        if header != metadata["columns"] or header != layout["columns"]:
            raise ValueError("Spreadsheet header differs from verified plan")
        indexes = [header.index(name) for name in RESERVED]
        for row in reader:
            if len(row) != len(header):
                raise ValueError("Malformed spreadsheet row")
            kind, key, grain = (row[index] for index in indexes)
            if kind not in counts or not key or not grain:
                raise ValueError("Unknown record type or missing observation identity")
            counts[kind] += 1
            if len(samples[kind]) < 10:
                samples[kind].append(row)
    finally:
        text.detach()
        csv.field_size_limit(previous_limit)
    if sum(counts.values()) != metadata["records"]:
        raise ValueError("Spreadsheet count differs from producer receipt")
    chosen = []
    for offset in range(10):
        for kind in groups:
            if offset < len(samples[kind]):
                chosen.append(samples[kind][offset])
                if len(chosen) == 10:
                    return header, chosen, dict(counts)
    return header, chosen, dict(counts)


def sample_bytes(header, rows):
    output = io.StringIO(newline="")
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(header)
    writer.writerows(rows)
    return output.getvalue().encode("utf-8")


def proposed_entry(prior, metadata, counts, sample, updated):
    """An existing storefront entry, measured against one public spreadsheet."""
    entry = copy.deepcopy(prior)
    cid = entry["id"]
    table = f"{cid}.csv"
    url = f"/data/cedar/samples/{cid}/spreadsheet__10.csv"
    path_count = sum(counts.values())
    if path_count != metadata["records"]:
        raise ValueError("Preview/receipt count disagreement")
    entry["descriptor"]["rows_label"] = f"{path_count:,} observations"
    entry["descriptor"]["updated"] = updated
    entry["descriptor"]["vintage"] = None
    entry["descriptor"]["downloads"] = None
    entry["cedar"].update(
        n_rows=path_count,
        n_tables=1,
        n_record_types=len(counts),
        count_basis="Permitted rows in the exact producer spreadsheet; mixed grains are not totals.",
        release_id=metadata["release_id"],
        manifest_sha256=metadata["source_manifest_sha256"],
        readiness_scope="Verified local preview; production approval and endpoint pins are separate.",
    )
    entry["sample"] = {
        "table": table,
        "path": url,
        "rows": len(sample),
        "of": path_count,
        "columns": len(metadata["columns"]),
        "release_id": metadata["release_id"],
        "manifest_sha256": metadata["source_manifest_sha256"],
    }
    entry["tables"] = [
        {
            "table": table,
            "sample_path": url,
            "rows_in": path_count + metadata["held_records_in_selected_groups"],
            "rows_published": path_count,
            "rows_withheld": metadata["held_records_in_selected_groups"],
            "withheld_why": (
                "Held observations excluded by the verified producer publication contract."
                if metadata["held_records_in_selected_groups"]
                else None
            ),
            "columns_published": len(metadata["columns"]),
            "sample_rows": len(sample),
            "record_types": counts,
            "full_file": {
                "shippable": True,
                "split": "",
                "files": 1,
                "largest_file_mb": metadata["bytes"] / 1_000_000,
            },
        }
    ]
    entry["full_files"] = {
        "served": False,
        "note": "The local spreadsheet was verified. These staged previews do not approve or configure a production download.",
    }
    if cid == "need":
        # The caller has already required the maintained exact-proof plan and
        # exactly the reviewed public component. Do not carry the old blanket
        # gate into this facts-only preview, or clear any underlying held part.
        entry.pop("publication_hold", None)
        entry["cedar"]["status"] = "REVIEWED_PUBLIC_BASE"
        entry["cedar"]["blockers"] = []
        entry["descriptor"]["method"] = (
            "This preview contains only the evidence-pinned reviewed public base. "
            "Original source components, unresolved identities, ratings and patent material "
            "retain their existing holds. Existing enterprise IDs and source evidence are preserved."
        )
    return entry


def _reviewed_preview_fields(
    collection, header, metadata_fields, codebook, field_map, repo, producer
):
    # Loading by sibling path works for direct CLI and importlib-based tests.
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "cedar_preview_definitions",
        Path(__file__).resolve().with_name("preview_definitions.py"),
    )
    if spec is None or spec.loader is None:
        raise ValueError("Preview definition resolver could not be loaded")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.require_fields(
        collection,
        header,
        metadata_fields,
        codebook,
        field_map,
        overrides=module.load_overrides(repo, producer),
    )


def stage(repo, producer, queue_path, output, producer_commit, updated):
    from lumecon_data import dbload, spreadsheet

    if os.environ.get("LUMECON_ENVIRONMENT") != "review":
        raise ValueError("Explicit LUMECON_ENVIRONMENT=review is required")
    for module in (dbload, spreadsheet):
        if (
            not Path(module.__file__)
            .resolve()
            .is_relative_to((producer / "src").resolve())
        ):
            raise ValueError("Imported producer code is not the expected checkout")
    if not COMMIT.fullmatch(producer_commit):
        raise ValueError("Expected producer commit must be exact")
    head = subprocess.check_output(
        ["git", "-C", str(producer), "rev-parse", "HEAD"], text=True
    ).strip()
    if head != producer_commit:
        raise ValueError("Producer checkout differs from expected commit")
    dirty = subprocess.check_output(
        ["git", "-C", str(producer), "status", "--porcelain", "--untracked-files=no"],
        text=True,
    )
    if dirty.strip():
        raise ValueError(
            "Producer tracked source must be committed before staging previews"
        )
    if date.fromisoformat(updated).isoformat() != updated:
        raise ValueError("Updated must be an ISO date")
    if output.exists():
        raise ValueError("Output must be new; preserve prior review bundles")
    queue = queue_items(read_json(queue_path))
    input_pins = {
        relative: hashlib.sha256((repo / relative).read_bytes()).hexdigest()
        for relative in (
            "data/cedar/collections.manifest.json",
            "data/cedar/codebook.json",
        )
    }
    manifest = read_json(repo / "data/cedar/collections.manifest.json")
    storefront = {entry["id"] for entry in manifest["collections"]}
    if "gaming" in storefront or not storefront <= EXPECTED:
        raise ValueError(
            "Preserve explicit Gaming exclusion and existing storefront membership"
        )
    output.mkdir(parents=True)
    receipts = {}
    replacements = {}
    codebook = read_json(repo / "data/cedar/codebook.json")
    for cid in sorted(queue):
        item = queue[cid]
        store = Path(item["store"])
        release, manifest_sha = dbload.load_manifest(store, cid, item["release"])
        if (
            manifest_sha != item["manifest_sha256"]
            or release.get("synthetic") is not False
        ):
            raise ValueError(f"{cid}: non-synthetic release/manifest pin mismatch")
        layout = spreadsheet.plan({**release, "collection_id": cid})
        if cid == "need" and [g["name"] for g in layout["groups"]] != [
            "reviewed_public_base"
        ]:
            raise ValueError(
                "NEED preview must contain only its exact-proof reviewed public base"
            )
        content, metadata = spreadsheet.spool(store, cid, item["release"])
        with closing(content):
            if (metadata["release_id"], metadata["source_manifest_sha256"]) != (
                item["release"],
                item["manifest_sha256"],
            ):
                raise ValueError(f"{cid}: export pin changed")
            header, rows, counts = read_preview(content, metadata, layout)
        if (
            item.get("expected_public_rows") is not None
            and metadata["records"] != item["expected_public_rows"]
        ):
            raise ValueError(f"{cid}: independent public-row count disagrees")
        blob = sample_bytes(header, rows)
        review_path = output / "review-samples" / f"{cid}.csv"
        review_path.parent.mkdir(parents=True, exist_ok=True)
        review_path.write_bytes(blob)
        receipts[cid] = {
            "release_id": item["release"],
            "manifest_sha256": manifest_sha,
            "spreadsheet_sha256": metadata["sha256"],
            "spreadsheet_bytes": metadata["bytes"],
            "public_records": metadata["records"],
            "held_records_in_selected_groups": metadata[
                "held_records_in_selected_groups"
            ],
            "record_types": counts,
            "sample_rows": len(rows),
            "sample_sha256": hashlib.sha256(blob).hexdigest(),
            "sample_path": str(review_path.relative_to(output)).replace("\\", "/"),
            "release_class": metadata["release_class"],
            "storefront_asset": cid in storefront,
            "unharmonized_fields": metadata["unharmonized_fields"],
        }
        if cid in storefront:
            prior = next(
                entry for entry in manifest["collections"] if entry["id"] == cid
            )
            replacements[cid] = proposed_entry(prior, metadata, counts, rows, updated)
            asset = (
                output
                / "assets/public/data/cedar/samples"
                / cid
                / "spreadsheet__10.csv"
            )
            asset.parent.mkdir(parents=True, exist_ok=True)
            asset.write_bytes(blob)
            if cid == "need":
                from lumecon_data.collection import collection_manifest_metadata
                from lumecon_data.storage import canonical_json
                from cedar_press.need_preview import ENVELOPE, need_preview_permitted
                from cedar_press.need_publication import (
                    COMPONENT,
                    reviewed_base_permitted,
                )

                api_manifest = collection_manifest_metadata(release)
                if (
                    hashlib.sha256(canonical_json(api_manifest)).hexdigest()
                    != manifest_sha
                ):
                    raise ValueError(
                        "NEED API manifest projection disagrees with its pinned digest"
                    )
                public_entry = api_manifest["components"][COMPONENT]
                if not reviewed_base_permitted(api_manifest, COMPONENT, public_entry):
                    raise ValueError(
                        "Consumer proof refuses the producer NEED reviewed base"
                    )
                public_bytes = dbload._component_bytes(
                    dbload.release_directory(store, cid, item["release"]),
                    COMPONENT,
                    release["components"][COMPONENT]["files"]["records.jsonl"],
                )
                proof_path = output / "assets" / ENVELOPE
                write_json(
                    proof_path,
                    {
                        "schema_version": 1,
                        "manifest": api_manifest,
                        "records_jsonl_base64": base64.b64encode(public_bytes).decode(
                            "ascii"
                        ),
                    },
                )
                replacements[cid]["verified_preview"] = {
                    "component": COMPONENT,
                    "envelope": ENVELOPE,
                    "envelope_sha256": hashlib.sha256(
                        proof_path.read_bytes()
                    ).hexdigest(),
                    "release_id": item["release"],
                    "manifest_sha256": manifest_sha,
                    "sample_sha256": hashlib.sha256(blob).hexdigest(),
                    "public_records": metadata["records"],
                }
                if not need_preview_permitted(
                    output / "assets",
                    replacements[cid],
                    replacements[cid]["tables"][0],
                    asset,
                ):
                    raise ValueError(
                        "Generated NEED static preview failed its exact-proof gate"
                    )
            # Metadata meanings are resolved with the exact field dictionary below.
            codebook["tables"][f"{cid}/{cid}"] = {
                "collection": cid,
                "dataset": prior["descriptor"]["name"],
                "row": "One permitted observation at its declared record_type and record_grain.",
                "where": f"Exact release {item['release']}; one researcher spreadsheet.",
                "fields": _reviewed_preview_fields(
                    cid,
                    header,
                    metadata["fields"],
                    codebook,
                    read_json(repo / "data/cedar/field_map.json"),
                    repo,
                    producer,
                ),
            }
        print(
            json.dumps(
                {
                    "collection": cid,
                    "records": metadata["records"],
                    "sample_rows": len(rows),
                }
            ),
            flush=True,
        )
    proposed = copy.deepcopy(manifest)
    proposed["collections"] = [
        replacements[entry["id"]] for entry in manifest["collections"]
    ]
    proposed["provenance"] = {
        "generator": "scripts/stage_verified_previews.py",
        "producer_commit": producer_commit,
        "updated": updated,
        "note": "Counts and samples derive from verified permitted spreadsheets, not legacy source previews. No production pin changes.",
        "preview_receipts": "data/cedar/verified-preview-releases.json",
    }
    write_json(output / "assets/data/cedar/collections.manifest.json", proposed)
    write_json(output / "assets/data/cedar/codebook.json", codebook)
    ledger = {
        "schema_version": 1,
        "producer_commit": producer_commit,
        "updated": updated,
        "collections": receipts,
    }
    write_json(output / "assets/data/cedar/verified-preview-releases.json", ledger)
    if any(
        hashlib.sha256((repo / relative).read_bytes()).hexdigest() != digest
        for relative, digest in input_pins.items()
    ):
        raise ValueError("Press input metadata changed during staging")
    # A ready marker is written last. An incomplete directory must never install.
    write_json(
        output / "READY.json",
        {
            "status": "STAGED_ONLY_NOT_INSTALLED",
            "press_input_sha256": input_pins,
            "verification_scope": (
                "Cryptographic, schema, key and publication validation of exact releases; "
                "not independent primary-source fact-checking of every observation."
            ),
            "queue_sha256": hashlib.sha256(Path(queue_path).read_bytes()).hexdigest(),
            "producer_commit": producer_commit,
            "collection_count": len(receipts),
            "storefront_ids_unchanged": [
                entry["id"] for entry in manifest["collections"]
            ],
            "followup": [
                "Inspect complete staged asset diff; replace stale public sample subtree only within its checked absolute path.",
                "Preserve Gaming exclusion and production pin files.",
                "Refresh measure-samples, derive-explore and dump-press after explicitly staging reviewed assets.",
                "Run collection/publication/preview tests and browser review before committing.",
            ],
        },
    )
    return ledger


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--producer", type=Path, required=True)
    parser.add_argument("--producer-commit", required=True)
    parser.add_argument("--queue", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--updated", required=True)
    args = parser.parse_args()
    stage(
        args.repo.resolve(),
        args.producer.resolve(),
        args.queue.resolve(),
        args.output.resolve(),
        args.producer_commit,
        args.updated,
    )


if __name__ == "__main__":
    main()
