"""Local process boundary for authenticated Grove application requests.

teim-app resolves its live account and Grove sponsorship before invoking this
module. This is not an HTTP authentication endpoint. It delegates release pins,
rights, byte verification and profile attribution to Cedar's existing consumer.
The caller owns a private output directory and streams completed files to its
authenticated response. No credentials or data bodies travel on command lines.
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import re
import sys
import tempfile
from pathlib import Path

from cedar_press import need_profiles, release_research, repository, spreadsheet

PROTOCOL_VERSION = 1
MAX_REQUEST_BYTES = 16 * 1024
MAX_METADATA_BYTES = 4 * 1024 * 1024


class ExchangeRefusal(ValueError):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status


def _validate(request: dict) -> str:
    if not isinstance(request, dict) or request.get("protocol_version") != PROTOCOL_VERSION:
        raise ExchangeRefusal(400, "Unsupported Grove consumer protocol")
    if request.get("tier") not in ("grove", "tree"):
        raise ExchangeRefusal(403, "Cedar Grove entitlement required")
    operation = request.get("operation")
    if not isinstance(operation, str):
        raise ExchangeRefusal(400, "Invalid Grove consumer operation")
    extra = {
        "discover": set(),
        "profile": {"cedar_uid"},
        "download": {"collection", "release_id", "component"},
        "spreadsheet": {"collection", "release_id"},
        "research": {"collection", "release_id", "component"},
    }.get(operation)
    if extra is None or set(request) - ({"protocol_version", "tier", "operation"} | extra):
        raise ExchangeRefusal(400, "Invalid Grove consumer request")
    return operation


def exchange(request: dict, output_directory: Path | None = None) -> dict:
    """Run only after teim-app has authenticated and resolved the current tier."""
    operation = _validate(request)
    if operation == "discover":
        return repository.release_targets_for(request["tier"])
    if operation == "profile":
        uid = request.get("cedar_uid")
        if not isinstance(uid, str):
            raise ExchangeRefusal(400, "A registered Cedar entity ID is required")
        return need_profiles.entity_evidence(uid)
    collection = request.get("collection")
    rid = request.get("release_id")
    component = request.get("component")
    if (
        not isinstance(collection, str)
        or not re.fullmatch(r"[a-z][a-z0-9-]{0,63}", collection)
        or not isinstance(rid, str)
        or not re.fullmatch(r"[0-9a-f]{64}", rid)
        or (
            component is not None
            and (
                not isinstance(component, str)
                or not re.fullmatch(r"[a-z0-9][a-z0-9_]{0,59}", component)
            )
        )
    ):
        raise ExchangeRefusal(400, "Invalid collection, component or release identity")
    if not repository.may_download_full(request["tier"], collection):
        raise ExchangeRefusal(403, "Collection is unavailable to this plan")
    if collection != "need" or (
        operation != "spreadsheet" and component != repository.need_publication.COMPONENT
    ):
        repository.assert_collection_publishable(collection)
    if operation == "research":
        return release_research.packet(request["tier"], collection, rid, component)
    if output_directory is None or not output_directory.is_dir() or output_directory.is_symlink():
        raise ExchangeRefusal(503, "Private download storage is unavailable")
    if operation == "spreadsheet":
        release = spreadsheet.download(collection, rid)
    elif repository.is_component_release(collection):
        release = repository.grove_full_release(collection, rid, component=component)
    else:
        if component is not None:
            raise ExchangeRefusal(400, "This collection has no selectable component")
        release = repository.full_release(collection, rid)
    stream = release.get("content_file") or release.get("spool")
    if stream is None and isinstance(release.get("content"), bytes):
        stream = io.BytesIO(release["content"])
    if stream is None:
        raise ExchangeRefusal(503, "Verified release bytes are unavailable")
    destination = None
    try:
        if release.get("release_id") != rid:
            raise ExchangeRefusal(503, "Release pin changed")
        digest = hashlib.sha256()
        size = 0
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=output_directory,
            prefix="cedar-",
            suffix=".csv" if operation == "spreadsheet" else ".jsonl",
            delete=False,
        ) as saved:
            destination = Path(saved.name)
            while chunk := stream.read(64 * 1024):
                size += len(chunk)
                digest.update(chunk)
                saved.write(chunk)
            saved.flush()
            os.fsync(saved.fileno())
        if digest.hexdigest() != release.get("sha256"):
            raise ExchangeRefusal(
                503, "Completed download digest differs from the verified release"
            )
        return {
            "kind": "verified_download",
            "release_id": rid,
            "collection": collection,
            "component": component,
            "file": destination.name,
            "filename": release["filename"],
            "media_type": release["media_type"],
            "sha256": digest.hexdigest(),
            "bytes": size,
            "record_count": release["record_count"],
            "citation": release["citation"],
            **{
                key: release[key]
                for key in ("publication_scope", "reviewed_public_base")
                if key in release
            },
        }
    except BaseException:
        if destination is not None:
            destination.unlink(missing_ok=True)
        raise
    finally:
        stream.close()


def response(request: dict, output_directory: Path | None = None) -> dict:
    try:
        payload = exchange(request, output_directory)
        result = {"protocol_version": PROTOCOL_VERSION, "status": 200, "payload": payload}
        if len(json.dumps(result).encode()) > MAX_METADATA_BYTES:
            raise ExchangeRefusal(503, "Consumer metadata exceeds its response limit")
        return result
    except ExchangeRefusal as error:
        return {"protocol_version": PROTOCOL_VERSION, "status": error.status, "error": str(error)}
    except need_profiles.UnregisteredEntity:
        return {
            "protocol_version": PROTOCOL_VERSION,
            "status": 404,
            "error": "No registered entity profile",
        }
    except (repository.FullReleaseUnavailable, OSError, ValueError, TypeError, KeyError):
        # Source configuration may contain a private URL. Never emit exception text.
        return {
            "protocol_version": PROTOCOL_VERSION,
            "status": 503,
            "error": "Pinned release unavailable or held",
        }


def main() -> None:
    try:
        content = sys.stdin.buffer.read(MAX_REQUEST_BYTES + 1)
        if len(content) > MAX_REQUEST_BYTES:
            raise ValueError("Oversized request")
        request = json.loads(content)
    except (ValueError, UnicodeDecodeError):
        result = {"protocol_version": PROTOCOL_VERSION, "status": 400, "error": "Invalid request"}
    else:
        directory = os.environ.get("CEDAR_GROVE_EXCHANGE_DIRECTORY")
        result = response(request, Path(directory) if directory else None)
    sys.stdout.write(json.dumps(result, ensure_ascii=True) + "\n")


if __name__ == "__main__":
    main()
