#!/usr/bin/env python3
"""Stage exact-release previews or explicitly admit selected verified preview assets.

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
import importlib.util
import json
import os
import re
import subprocess
import sys
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


def proposed_entry(prior, metadata, counts, sample, updated, layout=None):
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
            **({"record_type_fields": layout["mappings"]} if layout is not None else {}),
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
            "This release is the reviewed public base: 43 enterprises, each pinned to its "
            "evidence. NEED has no "
            "publication hold (owner ruling 2026-10-04): its records come from publicly "
            "available websites and Lumecon has permission to publish them, and source rights "
            "are recorded as provenance. Existing enterprise IDs and source evidence are preserved."
        )
        if "verified_claims" in metadata["columns"]:
            entry["descriptor"]["method"] += (
                " Each row lists its verified claims; identity, identifiers and relationships "
                "are separate assertions. Blank unclaimed fields are not negative findings. "
                "This reviewed cohort is not the full enterprise register or a deduplicated entity count."
            )
    return entry


def _reviewed_preview_fields(
    collection, header, metadata_fields, codebook, field_map, repo, producer, layout=None
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
    if collection in {"foundation-corporate-giving", "plot"}:
        if layout is None or layout["columns"] != header:
            raise ValueError("Mixed preview definitions require the verified plan")
        return preview_fields(collection, layout, producer, module)
    return module.require_fields(
        collection,
        header,
        metadata_fields,
        codebook,
        field_map,
        overrides=module.load_overrides(repo, producer),
    )


def _next_preview_version(value):
    if not isinstance(value, str) or re.fullmatch(r"v(?:0|[1-9][0-9]*)", value) is None:
        raise ValueError("Selected refresh requires an existing numeric preview version such as v4")
    return "v" + str(int(value[1:]) + 1)


def _existing_release_pins(values):
    result = {}
    for value in values or ():
        cid, separator, release = value.partition("=")
        if not separator or cid in result or cid not in EXPECTED or not SHA256.fullmatch(release):
            raise ValueError("Expected existing releases must be distinct COLLECTION=SHA256 pins")
        result[cid] = release
    return result


def _refresh_context(repo, manifest, queue, collections, expected_releases, input_pins):
    """Bind a selected refresh to installed metadata and unchanged public bytes."""
    selected = tuple(collections or ())
    entries = {entry["id"]: entry for entry in manifest["collections"]}
    if (not selected or len(set(selected)) != len(selected)
            or len(entries) != len(manifest["collections"])
            or not set(selected) <= set(entries) or "gaming" in selected):
        raise ValueError("Refresh requires distinct existing storefront collections")
    if set(expected_releases or {}) != set(selected):
        raise ValueError("Every refreshed collection requires its expected existing release")
    if not any(entry["id"] == "gaming" for entry in manifest.get("excluded", [])):
        raise ValueError("The explicit Gaming exclusion must be preserved")
    ledger_path = "data/cedar/verified-preview-releases.json"
    ledger_bytes = (repo / ledger_path).read_bytes()
    input_pins[ledger_path] = hashlib.sha256(ledger_bytes).hexdigest()
    ledger = json.loads(ledger_bytes)
    if set(ledger.get("collections", {})) != EXPECTED:
        raise ValueError("Selected refresh requires the complete 15-collection ledger")
    previous = {}
    versions = {}
    for cid, item in queue.items():
        pin = ledger["collections"][cid]
        pair = (pin["release_id"], pin["manifest_sha256"])
        if not all(isinstance(value, str) and SHA256.fullmatch(value) for value in pair):
            raise ValueError(f"{cid}: invalid existing ledger pin")
        if cid in selected:
            if expected_releases[cid] != pair[0]:
                raise ValueError(f"{cid}: expected existing release differs from installed ledger")
            if item["release"] == pair[0]:
                raise ValueError(f"{cid}: refresh must select a different immutable release")
            previous[cid] = dict(zip(("release_id", "manifest_sha256"), pair))
            old_version = entries[cid]["descriptor"].get("version")
            versions[cid] = {
                "previous": old_version,
                "next": _next_preview_version(old_version),
            }
        elif (item["release"], item["manifest_sha256"]) != pair:
            raise ValueError(f"{cid}: unselected queue pin changed")

    def bind(relative, expected):
        if not isinstance(relative, str) or not isinstance(expected, str) or not SHA256.fullmatch(expected):
            raise ValueError("Invalid installed preview artifact binding")
        root = repo.resolve()
        path = (repo / relative).resolve()
        if not path.is_relative_to(root) or not path.is_file():
            raise ValueError("Installed preview artifact is absent or escapes the repository")
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != expected:
            raise ValueError(f"Installed preview artifact hash mismatch: {relative}")
        input_pins[path.relative_to(root).as_posix()] = actual

    for cid, entry in entries.items():
        pin = ledger["collections"][cid]
        pair = (pin["release_id"], pin["manifest_sha256"])
        for section in ("cedar", "sample"):
            if (entry[section].get("release_id"), entry[section].get("manifest_sha256")) != pair:
                raise ValueError(f"{cid}: installed manifest and ledger pins disagree")
        expected_url = f"/data/cedar/samples/{cid}/spreadsheet__10.csv"
        if entry["sample"].get("path") != expected_url:
            raise ValueError(f"{cid}: unexpected installed spreadsheet preview path")
        bind(expected_url.lstrip("/"), pin["sample_sha256"])
        if "verified_preview" in entry:
            proof = entry["verified_preview"]
            if (proof.get("release_id"), proof.get("manifest_sha256")) != pair:
                raise ValueError(f"{cid}: installed proof pins disagree")
            bind(proof["envelope"], proof["envelope_sha256"])
    return {
        "selected": selected, "previous": previous, "versions": versions, "ledger": ledger,
        "manifest": copy.deepcopy(manifest),
        "codebook": read_json(repo / "data/cedar/codebook.json"),
    }


def _merge_refresh(context, proposed, codebook, receipts, producer_commit, updated, queue_sha256):
    """Keep prior provenance for unselected releases; annotate only new artifacts."""
    selected = set(context["selected"])
    original_manifest = context["manifest"]
    originals = {entry["id"]: entry for entry in original_manifest["collections"]}
    if [entry["id"] for entry in proposed["collections"]] != list(originals):
        raise ValueError("Selected refresh changed storefront membership or order")
    for entry in proposed["collections"]:
        if entry["id"] not in selected and entry != originals[entry["id"]]:
            raise ValueError("Selected refresh altered an unselected collection")
        if entry["id"] in selected:
            version = context["versions"][entry["id"]]
            if entry["descriptor"].get("version") != version["previous"]:
                raise ValueError("Selected preview version changed outside its guarded increment")
            entry["descriptor"]["version"] = version["next"]
    original_book = context["codebook"]
    keys = {f"{cid}/{cid}" for cid in selected}
    if ({key: value for key, value in codebook["tables"].items() if key not in keys}
            != {key: value for key, value in original_book["tables"].items() if key not in keys}
            or {key: value for key, value in codebook.items() if key != "tables"}
            != {key: value for key, value in original_book.items() if key != "tables"}):
        raise ValueError("Selected refresh altered unrelated codebook definitions")
    if set(receipts) != selected:
        raise ValueError("Selected refresh generated an unexpected receipt set")
    ledger = copy.deepcopy(context["ledger"])
    provenance = copy.deepcopy(original_manifest.get("provenance", {}))
    if not isinstance(provenance, dict):
        raise ValueError("Existing manifest provenance must be an object")
    refreshes = copy.deepcopy(provenance.get("selected_refreshes", {}))
    if not isinstance(refreshes, dict):
        raise ValueError("Existing selected refresh provenance must be an object")
    for cid, receipt in receipts.items():
        receipt.update(
            producer_commit=producer_commit, updated=updated,
            source_queue_sha256=queue_sha256,
            preview_version=context["versions"][cid]["next"],
            replaces_preview_version=context["versions"][cid]["previous"],
            replaces=context["previous"][cid],
        )
        ledger["collections"][cid] = receipt
        refreshes[cid] = {
            "generator": "scripts/stage_verified_previews.py --refresh-existing",
            "producer_commit": producer_commit, "updated": updated,
            "release_id": receipt["release_id"],
            "manifest_sha256": receipt["manifest_sha256"],
            "preview_version": context["versions"][cid]["next"],
            "replaces_preview_version": context["versions"][cid]["previous"],
            "replaces": context["previous"][cid],
        }
    # Existing top-level provenance continues to describe the earlier batch.
    # The per-collection entry records the new producer, date and release.
    provenance["selected_refreshes"] = refreshes
    proposed["provenance"] = provenance
    return ledger


def stage(repo, producer, queue_path, output, producer_commit, updated, *,
          refresh_existing=False, collections=None, expected_existing_releases=None):
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
    if not refresh_existing and (collections or expected_existing_releases):
        raise ValueError("Selected refresh arguments require refresh_existing")
    queue_sha256 = hashlib.sha256(Path(queue_path).read_bytes()).hexdigest()
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
    refresh = (
        _refresh_context(repo, manifest, queue, collections,
                         expected_existing_releases, input_pins)
        if refresh_existing else None
    )
    selected_queue = refresh["selected"] if refresh is not None else queue
    output.mkdir(parents=True)
    receipts = {}
    replacements = {}
    codebook = read_json(repo / "data/cedar/codebook.json")
    for cid in sorted(selected_queue):
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
            replacements[cid] = proposed_entry(prior, metadata, counts, rows, updated, layout)
            asset = (
                output
                / "assets/data/cedar/samples"
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
                    layout,
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
        replacements.get(entry["id"], entry) for entry in manifest["collections"]
    ]
    proposed["provenance"] = {
        "generator": "scripts/stage_verified_previews.py",
        "producer_commit": producer_commit,
        "updated": updated,
        "note": "Counts and samples derive from verified permitted spreadsheets, not legacy source previews. No production pin changes.",
        "preview_receipts": "data/cedar/verified-preview-releases.json",
    }
    ledger = {
        "schema_version": 1,
        "producer_commit": producer_commit,
        "updated": updated,
        "collections": receipts,
    }
    if refresh is not None:
        ledger = _merge_refresh(
            refresh, proposed, codebook, receipts, producer_commit, updated, queue_sha256
        )
    write_json(output / "assets/data/cedar/collections.manifest.json", proposed)
    write_json(output / "assets/data/cedar/codebook.json", codebook)
    write_json(output / "assets/data/cedar/verified-preview-releases.json", ledger)
    if hashlib.sha256(Path(queue_path).read_bytes()).hexdigest() != queue_sha256:
        raise ValueError("Release queue changed during staging")
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
            "queue_sha256": queue_sha256,
            "producer_commit": producer_commit,
            "collection_count": len(receipts),
            "ledger_collection_count": len(ledger["collections"]),
            "refresh_existing": refresh is not None,
            "selected_collections": sorted(receipts),
            "staged_asset_sha256": {
                path.relative_to(output / "assets").as_posix():
                    hashlib.sha256(path.read_bytes()).hexdigest()
                for path in sorted((output / "assets").rglob("*")) if path.is_file()
            },
            "storefront_ids_unchanged": [
                entry["id"] for entry in manifest["collections"]
            ],
            "followup": [
                ("Install only the listed selected sample/proof files and complete staged metadata; preserve every unselected sample."
                 if refresh is not None else
                 "Inspect complete staged asset diff; replace stale data/cedar/samples subtree only within its checked absolute path, then re-render the customer tables (scripts/render_sample_downloads.py)."),
                "Preserve Gaming exclusion and production pin files.",
                "Refresh measure-samples, derive-explore and dump.mjs --kind press after explicitly staging reviewed assets; regenerate docs with docs-markdown.mjs --kind all.",
                "Run collection/publication/preview tests and browser review before committing.",
            ],
        },
    )
    return ledger



ADDITIONS = {
    "foundation-corporate-giving": {
        "name": "Foundation & Corporate Giving", "short_name": "Giving",
        "shelf": "standard",
        "tracks": "Publicly disclosed giving facts, with each source disclosure and financial status preserved.",
        "sources": "Cited first-party donation reports and public foundation, corporate and bank disclosures admitted by the producer rights contract.",
        "method": (
            "One permitted source disclosure, not one distinct award or payment. "
            "Reported recipient names may identify a program or intermediary. "
            "Commitments, payments, unpaid balances, exact amounts, ranges and aggregate program totals remain distinct and nonadditive. "
            "Only reviewed recipient bindings are carried; no ownership or Native identity is inferred from names. "
            "Restricted source prose and other withheld material remain excluded under field-level publication rights."
        ),
        "types": {"policy_eligible_disclosures", "reviewed_disclosures"},
    },
    "plot": {
        "name": "PLOT", "short_name": "PLOT", "shelf": "pro",
        "tracks": "Public tract, assessor parcel, permit and environmental observations at their declared source grain.",
        "sources": "Cited BIA mapped tract, Wisconsin V12 assessor parcel, local permit and EPA regulatory sources admitted by the producer rights contract.",
        "method": (
            "One permitted source observation at its declared record type. A BIA tract can contain several parcels; "
            "an assessor owner label is not title certification, beneficial ownership or verified Native ownership. "
            "A permit is not necessarily a unique project, and regulatory lifecycle events remain separate observations. "
            "Source snapshots, issued dates and event dates retain their own meanings. "
            "No ownership, financial transaction or canonical entity binding is inferred across components."
        ),
        "types": {"tract_observations", "ownership_observations", "permits", "permit_events", "environmental_permits", "environmental_events"},
    },
}
STRUCTURAL = {
    "record_type": "The permitted logical record type from the pinned release.",
    "record_key": "The original source primary-key values serialized as JSON.",
    "record_grain": "What one observation of this record type represents; never sum across overlapping grains.",
}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def module_at(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ValueError("Cannot load reviewed preview definitions")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def preview_fields(cid, plan, producer, definitions):
    if cid == "foundation-corporate-giving":
        from lumecon_data.collections import foundation_metadata

    possibilities = {name: [] for name in plan["columns"]}
    for kind, meaning in STRUCTURAL.items():
        possibilities[kind].append((meaning, {"kind": "spreadsheet_structure", "path": "src/lumecon_data/spreadsheet.py"}))
    for group in plan["groups"]:
        name = group["name"]
        fields = group["contract"]["fields"]
        annotations = foundation_metadata.annotation(name, fields).get("fields", {}) if cid == "foundation-corporate-giving" else {}
        for field in fields:
            if field["name"] not in plan["mappings"][name]:
                continue
            column = plan["mappings"][name][field["name"]]
            annotation = annotations.get(field["name"], {})
            meaning = annotation.get("definition") or field.get("description")
            if not definitions.is_substantive(meaning, column):
                raise ValueError(f"{cid}/{name}/{field['name']}: no substantive maintained definition")
            authority = {"kind": "verified_producer_contract", "component": name, "field": field["name"]}
            if annotation.get("definition"):
                authority.update(
                    kind="maintained_producer_annotation",
                    path="src/lumecon_data/collections/foundation_metadata.py",
                    sha256=digest((producer / "src/lumecon_data/collections/foundation_metadata.py").read_bytes()),
                )
            possibilities[column].append((meaning, authority))
    result = []
    for column in plan["columns"]:
        meanings = {value for value, _ in possibilities[column]}
        if len(meanings) != 1:
            raise ValueError(f"{cid}/{column}: absent or conflicting definitions: {sorted(meanings)}")
        result.append({
            "column": column, "label": column.replace("_", " "),
            "meaning": next(iter(meanings)),
            "definition_source": [source for _, source in possibilities[column]],
        })
    return result


def admit(repo, producer, queue_path, staging, producer_commit, receipt, apply=False, collections=None):
    selected_ids = tuple(ADDITIONS) if collections is None else tuple(collections)
    if not selected_ids or len(set(selected_ids)) != len(selected_ids) or not set(selected_ids) <= set(ADDITIONS):
        raise ValueError("Select distinct reviewed Giving/PLOT collections explicitly")
    if not COMMIT.fullmatch(producer_commit):
        raise ValueError("Expected producer commit must be exact")
    if os.environ.get("LUMECON_ENVIRONMENT") != "review":
        raise ValueError("LUMECON_ENVIRONMENT=review is required")
    head = subprocess.check_output(["git", "-C", str(producer), "rev-parse", "HEAD"], text=True).strip()
    if head != producer_commit:
        raise ValueError("Producer checkout differs from expected exact commit")
    dirty = subprocess.check_output(["git", "-C", str(producer), "status", "--porcelain", "--untracked-files=no"], text=True)
    if dirty.strip():
        raise ValueError("Producer tracked code must be committed before admission")
    sys.path.insert(0, str(producer / "src"))
    from lumecon_data import dbload, spreadsheet
    for module in (dbload, spreadsheet):
        if not Path(module.__file__).resolve().is_relative_to((producer / "src").resolve()):
            raise ValueError("Wrong producer import")
    manifest_path = repo / "data/cedar/collections.manifest.json"
    book_path = repo / "data/cedar/codebook.json"
    ledger_path = repo / "data/cedar/verified-preview-releases.json"
    paths = [manifest_path, book_path, ledger_path]
    originals = {path: path.read_bytes() for path in paths}
    manifest, book, ledger = (json.loads(originals[path]) for path in paths)
    existing = {entry["id"]: entry for entry in manifest["collections"]}
    baseline = EXPECTED - set(ADDITIONS) - {"gaming"}
    if len(existing) != len(manifest["collections"]) or not baseline <= set(existing) or not set(existing) <= baseline | set(ADDITIONS):
        raise ValueError("Unexpected storefront population or Gaming admission")
    if set(selected_ids) & set(existing):
        raise ValueError("Selected preview already exists; use ordinary staging to refresh it")
    if not any(entry["id"] == "gaming" for entry in manifest["excluded"]):
        raise ValueError("Gaming exclusion must remain explicit")
    queue = queue_items(read_json(queue_path))
    definitions = module_at("cedar_preview_definitions_admission", repo / "scripts/preview_definitions.py")
    new_files = {}
    accepted = {}
    for cid in selected_ids:
        descriptor = ADDITIONS[cid]
        pin = ledger["collections"][cid]
        selected = queue[cid]
        if (selected["release"], selected["manifest_sha256"]) != (pin["release_id"], pin["manifest_sha256"]):
            raise ValueError(f"{cid}: queue differs from the tracked verified preview ledger")
        source = (staging / pin["sample_path"]).resolve()
        if not source.is_relative_to(staging.resolve()):
            raise ValueError("Preview path escapes staging")
        raw = source.read_bytes()
        if digest(raw) != pin["sample_sha256"]:
            raise ValueError(f"{cid}: preserved preview bytes differ from verified ledger")
        release, manifest_sha = dbload.load_manifest(Path(selected["store"]), cid, selected["release"])
        if manifest_sha != pin["manifest_sha256"] or release.get("synthetic") is not False:
            raise ValueError(f"{cid}: exact nonsynthetic manifest verification failed")
        plan = spreadsheet.plan({**release, "collection_id": cid})
        if {g["name"] for g in plan["groups"]} != descriptor["types"]:
            raise ValueError(f"{cid}: reviewed public record-type set changed")
        reader = csv.reader(io.StringIO(raw.decode("utf-8"), newline=""), strict=True)
        header, rows = next(reader), list(reader)
        if header != plan["columns"] or len(rows) != pin["sample_rows"] or any(len(r) != len(header) for r in rows):
            raise ValueError(f"{cid}: verified sample shape changed")
        if set(pin["record_types"]) != descriptor["types"] or sum(pin["record_types"].values()) != pin["public_records"]:
            raise ValueError(f"{cid}: record-type counts disagree")
        for row in rows:
            kind = row[header.index("record_type")]
            if kind not in descriptor["types"] or not row[header.index("record_key")] or not row[header.index("record_grain")]:
                raise ValueError(f"{cid}: invalid source observation identity")
        url = f"/data/cedar/samples/{cid}/spreadsheet__10.csv"
        destination = repo / url.lstrip("/")
        if destination.exists():
            raise ValueError(f"{cid}: new preview destination already exists")
        new_files[destination] = raw
        fields = preview_fields(cid, plan, producer, definitions)
        entry = {
            "id": cid,
            "descriptor": {
                "id": cid, "shelf": descriptor["shelf"], "level": "record", "origin": "lumecon",
                "rows_label": f"{pin['public_records']:,} observations", "vintage": None,
                "version": "v3", "updated": ledger["updated"], "downloads": None,
                **{key: descriptor[key] for key in ("name", "short_name", "tracks", "sources", "method")},
            },
            "cedar": {
                "cedar_id": cid, "status": "READY", "blockers": [], "n_rows": pin["public_records"],
                "n_tables": 1, "n_record_types": len(pin["record_types"]),
                "count_basis": "Permitted rows in the exact producer spreadsheet; mixed grains are not totals.",
                "release_id": pin["release_id"], "manifest_sha256": pin["manifest_sha256"],
                "readiness_scope": "Verified local preview; production approval and endpoint pins are separate.",
            },
            "sample": {"table": f"{cid}.csv", "path": url, "rows": len(rows), "of": pin["public_records"], "columns": len(header), "release_id": pin["release_id"], "manifest_sha256": pin["manifest_sha256"]},
            "tables": [{
                "table": f"{cid}.csv", "sample_path": url,
                "rows_in": pin["public_records"] + pin["held_records_in_selected_groups"],
                "rows_published": pin["public_records"], "rows_withheld": pin["held_records_in_selected_groups"],
                "withheld_why": "Held observations excluded by the verified producer publication contract." if pin["held_records_in_selected_groups"] else None,
                "columns_published": len(header), "sample_rows": len(rows),
                "record_types": pin["record_types"], "record_type_fields": plan["mappings"],
                "full_file": {"shippable": True, "split": "", "files": 1, "largest_file_mb": pin["spreadsheet_bytes"] / 1_000_000},
            }],
            "full_files": {"served": False, "note": "The local spreadsheet was verified. These staged previews do not approve or configure a production download."},
        }
        manifest["collections"].append(entry)
        book["tables"][f"{cid}/{cid}"] = {
            "collection": cid, "dataset": descriptor["name"],
            "row": "One permitted observation at its declared record_type and record_grain.",
            "where": f"Exact release {pin['release_id']}; one researcher spreadsheet.",
            "fields": fields,
        }
        ledger["collections"][cid]["storefront_asset"] = True
        accepted[cid] = {"release_id": pin["release_id"], "manifest_sha256": pin["manifest_sha256"], "rows": pin["public_records"], "sample_sha256": digest(raw), "columns": len(header), "record_types": pin["record_types"], "definition_count": len(fields)}
    if len(manifest["collections"]) != len(existing) + len(selected_ids):
        raise ValueError("Selective preview admission changed the wrong population")
    for cid, original in existing.items():
        if next(entry for entry in manifest["collections"] if entry["id"] == cid) != original:
            raise ValueError("Existing collection was altered")
    for path, value in zip(paths, (manifest, book, ledger), strict=True):
        new_files[path] = (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    result = {
        "status": "ADMITTED_NOT_TESTED" if apply else "PREFLIGHT_PASSED_NO_WRITES",
        "producer_commit": producer_commit, "collections": accepted,
        "input_sha256": {str(path.relative_to(repo)): digest(raw) for path, raw in originals.items()},
        "output_sha256": {str(path.relative_to(repo)): digest(raw) for path, raw in new_files.items()},
        "limitations": ["Preview admission is not production deployment.", "No source rows, identities or publication rights were changed.", "Observation counts are not distinct entities, parcels, awards or payments."],
    }
    if receipt.exists():
        raise ValueError("Preserve existing admission receipt")
    if apply:
        for path, original in originals.items():
            if path.read_bytes() != original:
                raise ValueError("Concurrent metadata edit; refusing")
        for path, raw in new_files.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
    receipt.parent.mkdir(parents=True, exist_ok=True)
    receipt.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--producer", type=Path, required=True)
    parser.add_argument("--producer-commit", required=True)
    parser.add_argument("--queue", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--updated")
    parser.add_argument("--admit-existing", action="store_true", help="Admit selected already verified preview samples; do not respool source data.")
    parser.add_argument("--refresh-existing", action="store_true",
                        help="Stage selected existing previews from new exact releases; do not install.")
    parser.add_argument("--expected-existing-release", action="append", metavar="COLLECTION=SHA256",
                        help="Required installed release guard for every selected refresh.")
    parser.add_argument("--collection", action="append", choices=sorted(EXPECTED - {"gaming"}))
    parser.add_argument("--staging", type=Path)
    parser.add_argument("--receipt", type=Path)
    parser.add_argument("--apply", action="store_true", help="Install explicitly admitted previews after all checks; otherwise receipt-only preflight.")
    args = parser.parse_args()
    if args.admit_existing and args.refresh_existing:
        parser.error("--admit-existing and --refresh-existing are separate operations")
    if args.expected_existing_release and not args.refresh_existing:
        parser.error("--expected-existing-release requires --refresh-existing")
    if args.admit_existing:
        if not args.collection or args.staging is None or args.receipt is None:
            parser.error("--admit-existing requires --collection, --staging and --receipt")
        if args.output is not None or args.updated is not None:
            parser.error("Admission retains the verified ledger date; --output/--updated are staging options")
        result = admit(
            args.repo.resolve(), args.producer.resolve(), args.queue.resolve(),
            args.staging.resolve(), args.producer_commit, args.receipt.resolve(),
            args.apply, args.collection,
        )
        print(json.dumps(result, ensure_ascii=False))
    elif args.refresh_existing:
        if args.output is None or args.updated is None or not args.collection:
            parser.error("Selected refresh requires --output, --updated and --collection")
        if args.staging is not None or args.receipt is not None or args.apply:
            parser.error("Selected refresh is stage-only; admission/install options are invalid")
        try:
            expected_releases = _existing_release_pins(args.expected_existing_release)
            if set(expected_releases) != set(args.collection):
                raise ValueError("Every selected collection requires --expected-existing-release")
        except ValueError as error:
            parser.error(str(error))
        stage(
            args.repo.resolve(), args.producer.resolve(), args.queue.resolve(),
            args.output.resolve(), args.producer_commit, args.updated,
            refresh_existing=True, collections=args.collection,
            expected_existing_releases=expected_releases,
        )
    else:
        if args.output is None or args.updated is None:
            parser.error("Staging requires --output and --updated")
        if args.collection or args.staging is not None or args.receipt is not None or args.apply:
            parser.error("Selective admission options require --admit-existing")
        stage(args.repo.resolve(), args.producer.resolve(), args.queue.resolve(),
              args.output.resolve(), args.producer_commit, args.updated)


if __name__ == "__main__":
    main()
