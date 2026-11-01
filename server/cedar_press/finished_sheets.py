"""Finished customer spreadsheets on disk, one per release.

Press sends nothing until a spreadsheet is verified, and the largest take longer
to build than CloudFront waits for a first byte. So each is built once, through
the ordinary verified path, and kept. A file is served only for the release the
current pin names, under the current presentation rules, with its hash rechecked;
anything else falls back to building it in the request.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import shutil
import sys
import tempfile
import time
from contextlib import closing
from functools import lru_cache
from pathlib import Path

from cedar_press import csv_safety, customer_sheet
from cedar_press import repository as r

FOLDER_ENV = "CEDAR_PRESS_FINISHED_SHEETS"
log = logging.getLogger("cedar_press.download")


@lru_cache(maxsize=1)
def _rules() -> bytes:
    """Everything beyond the release that decides a spreadsheet's bytes."""
    from cedar_press import spreadsheet

    digest = hashlib.sha256()
    for path in (
        customer_sheet.__file__,
        csv_safety.__file__,
        spreadsheet.__file__,
        *spreadsheet.CEDAR_ID_REGISTERS,
    ):
        if Path(path).is_file():
            digest.update(Path(path).read_bytes())
    return digest.digest()


def _paths(collection, release_id):
    folder = os.environ.get(FOLDER_ENV)
    if not folder:
        return None
    citation = r.launch.collection_citation(collection) or ""
    key = hashlib.sha256(_rules() + citation.encode("utf-8")).hexdigest()[:16]
    name = f"{collection}--{release_id}--{key}"
    return Path(folder) / f"{name}.csv", Path(folder) / f"{name}.json"


def open_verified(collection, descriptor):
    """This release's finished file, its hash rechecked, or None to build it instead."""
    paths = _paths(collection, descriptor["release_id"])
    if paths is None:
        return None
    content = None
    try:
        record = json.loads(paths[1].read_text(encoding="utf-8"))
        content = paths[0].open("rb")
        digest = hashlib.sha256()
        while chunk := content.read(1024 * 1024):
            digest.update(chunk)
        if (
            digest.hexdigest() != record["sha256"]
            or record["record_count"] != descriptor["record_count"]
            or record["fields"] != descriptor["fields"]
        ):
            raise ValueError("Finished spreadsheet differs from its record")
        content.seek(0)
    except FileNotFoundError:
        if content is not None:
            content.close()
        return None
    except (OSError, ValueError, KeyError, TypeError) as error:
        if content is not None:
            content.close()
        log.warning("finished spreadsheet refused: %s %s", collection, type(error).__name__)
        return None
    return {
        **descriptor,
        "content_file": content,
        "sha256": record["sha256"],
        "media_type": "text/csv; charset=utf-8",
        "citation": record["citation"],
    }


def _publish(target, write):
    """A reader sees the whole file or none of it."""
    handle, name = tempfile.mkstemp(dir=target.parent, prefix=".build-")
    try:
        with os.fdopen(handle, "wb") as output:
            write(output)
            output.flush()
            os.fsync(output.fileno())
        os.replace(name, target)
    except BaseException:
        Path(name).unlink(missing_ok=True)
        raise


def build(collection):
    """Keep one collection's finished file; returns its paths and whether it was new."""
    from cedar_press import spreadsheet

    descriptor = spreadsheet.assemble(collection, metadata_only=True)
    target, sidecar = _paths(collection, descriptor["release_id"])
    existing = open_verified(collection, descriptor)
    if existing is not None:
        existing["content_file"].close()
        return (target, sidecar), False
    release = spreadsheet.assemble(collection, descriptor["release_id"])
    with closing(release["content_file"]) as content:
        _publish(target, lambda output: shutil.copyfileobj(content, output, 1024 * 1024))
    record = {key: release[key] for key in ("sha256", "record_count", "fields", "citation")}
    # Written last, so a sidecar means its file is complete.
    _publish(sidecar, lambda output: output.write(json.dumps(record).encode("utf-8")))
    return (target, sidecar), True


def _prune(folder, current):
    for path in Path(folder).iterdir():
        if path not in current:
            path.unlink()


def main():
    folder = os.environ.get(FOLDER_ENV)
    if not folder:
        print(f"{FOLDER_ENV} is not set; nothing to build", flush=True)
        return 1
    current = set()
    failed = []
    for item in r.launch.LAUNCH_COLLECTION:
        start = time.monotonic()
        try:
            paths, built = build(item.id)
            current.update(paths)
        except (r.FullReleaseUnavailable, OSError, ValueError, KeyError, TypeError) as error:
            failed.append(item.id)
            print(f"finished sheet {item.id}: failed, {type(error).__name__}", flush=True)
            continue
        state = "built" if built else "already current"
        print(f"finished sheet {item.id}: {state}, {time.monotonic() - start:.1f} s", flush=True)
    # A failed collection may still need its older file, so nothing is removed.
    if not failed:
        _prune(folder, current)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
