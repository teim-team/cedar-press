"""Replay saved real release queues through both ASGI apps with disk-bounded transport.

No listener, subprocess, rebuilding, or response-body accumulation. Source HTTP
responses are spooled to the configured temporary directory; Cedar responses are
hashed and counted in the ASGI send callback. Existing producer and consumer
verification remains active. Receipts are per collection so failures can resume.
"""

import argparse
import asyncio
import hashlib
import json
import os
import tempfile
import time
from contextlib import ExitStack
from email.message import Message
from pathlib import Path
from unittest.mock import patch
from urllib.parse import urlsplit


def emit(**entry):
    print(json.dumps(entry, sort_keys=True), flush=True)


async def stream_asgi(app, target, *, headers=(), sink=None, timeout=1800, progress=None):
    """Consume HTTP events without retaining the logical response body."""
    parsed = urlsplit(target)
    done = asyncio.Event()
    received = False
    state = {"status": None, "headers": {}, "bytes": 0, "rows": 0, "max_chunk_bytes": 0}
    digest = hashlib.sha256()
    last = b""
    next_progress = 64 * 1024 * 1024

    async def receive():
        nonlocal received
        if not received:
            received = True
            return {"type": "http.request", "body": b"", "more_body": False}
        await done.wait()
        return {"type": "http.disconnect"}

    async def send(message):
        nonlocal last, next_progress
        if message["type"] == "http.response.start":
            state["status"] = message["status"]
            state["headers"] = {
                key.decode("latin1").lower(): value.decode("latin1")
                for key, value in message.get("headers", [])
            }
        elif message["type"] == "http.response.body":
            body = message.get("body", b"")
            digest.update(body)
            state["bytes"] += len(body)
            state["rows"] += body.count(b"\n")
            state["max_chunk_bytes"] = max(state["max_chunk_bytes"], len(body))
            if body:
                last = body[-1:]
            if sink is not None:
                sink.write(body)
            if progress and state["bytes"] >= next_progress:
                progress(state["bytes"], state["rows"])
                next_progress = state["bytes"] + 64 * 1024 * 1024
            if not message.get("more_body", False):
                done.set()

    scope = {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.4"},
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": parsed.path,
        "raw_path": parsed.path.encode("ascii"),
        "query_string": parsed.query.encode("ascii"),
        "root_path": "",
        "headers": list(headers),
        "client": ("127.0.0.1", 1),
        "server": ("review", 80),
    }
    await asyncio.wait_for(app(scope, receive, send), timeout=timeout)
    if state["status"] is None or not done.is_set():
        raise RuntimeError("ASGI response did not complete")
    state.update(sha256=digest.hexdigest(), ends_in_newline=last == b"\n")
    return state


class DiskResponse:
    """The urllib response interface used by the existing Cedar transport."""

    def __init__(self, stream, headers):
        self.stream = stream
        self.headers = Message()
        for key, value in headers.items():
            self.headers[key] = value

    def read(self, size):
        if size < 0:
            raise ValueError("Unbounded response reads are forbidden in this rehearsal")
        return self.stream.read(size)

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.stream.close()


def expected_artifact(directory, entries):
    """Independently reconcile exact manifest-ordered local JSONL bytes."""
    combined = hashlib.sha256()
    total = rows = 0
    for name, entry in entries:
        path = (
            directory / "components" / name / "records.jsonl"
            if name
            else directory / "records.jsonl"
        )
        digest = hashlib.sha256()
        observed = counted = 0
        with path.open("rb") as stream:
            while chunk := stream.read(1024 * 1024):
                combined.update(chunk)
                digest.update(chunk)
                observed += len(chunk)
                counted += chunk.count(b"\n")
        expected = entry["files"]["records.jsonl"]
        if (observed, counted, digest.hexdigest()) != (
            expected["bytes"],
            entry["record_count"],
            expected["sha256"],
        ):
            raise ValueError("Saved artifact differs from its manifest")
        total += observed
        rows += counted
    return {"bytes": total, "rows": rows, "sha256": combined.hexdigest()}


def run_one(item, output, temporary, timeout):
    from lumecon_data.api import create_app
    from lumecon_data.catalog import build_catalog
    from lumecon_data.collection import collection_dir

    from cedar_press import repository, subscribers
    from cedar_press.app import app
    from cedar_press.session import Session, current_session

    key, rid, store = item["collection"], item["release"], Path(item["store"])
    collection_path = collection_dir(store, key, rid)
    dataset_path = store / "releases" / key / rid
    if collection_path.exists() == dataset_path.exists():
        raise ValueError("Require exactly one existing dataset or collection release")
    collection = collection_path.exists()
    directory = collection_path if collection else dataset_path
    raw_manifest = (directory / "manifest.json").read_bytes()
    manifest = json.loads(raw_manifest)
    if manifest.get("synthetic") is not False:
        raise ValueError("Only real saved candidates are accepted")
    product = "cedar_grove" if key == "gaming" else "cedar_press"
    catalog = build_catalog(
        store,
        [(key, rid)],
        product=product,
        release_kind="collection" if collection else "dataset",
        allow_rehearsal=True,
    )
    catalog_bytes = repository._canonical_bytes(catalog)
    output.mkdir(parents=True, exist_ok=True)
    catalog_path, pin_path = output / "catalog.json", output / "pin.json"
    catalog_path.write_bytes(catalog_bytes)
    components = repository.is_component_release(key)
    if components:
        pin_path.write_bytes(
            repository._canonical_bytes(
                {
                    "schema_version": 1,
                    "product": product,
                    "pins": {
                        key: {
                            "collection_id": key,
                            "release_id": rid,
                            "catalog_id": catalog["catalog_id"],
                            "catalog_sha256": hashlib.sha256(catalog_bytes).hexdigest(),
                            "manifest_sha256": catalog["collection_releases"][0]["manifest_sha256"],
                        }
                    },
                }
            )
        )
    environment = {
        "CEDAR_PRESS_RELEASE_CATALOG": str(catalog_path),
        "CEDAR_GROVE_RELEASE_CATALOG": str(catalog_path),
        "CEDAR_PRESS_COMPONENT_RELEASE_CATALOG": str(catalog_path),
        "CEDAR_PRESS_COMPONENT_RELEASE_PIN": str(pin_path),
    }
    source_app = create_app(store, {"isolated-review": {key}})
    source_calls = 0
    consumer_errors = []
    consumer_function = repository.grove_full_release if components else repository.full_release

    def traced_consumer(*args, **kwargs):
        try:
            return consumer_function(*args, **kwargs)
        except repository.FullReleaseUnavailable as error:
            consumer_errors.append(str(error))
            if error.__cause__ is not None:
                consumer_errors.append(str(error.__cause__))
            raise

    def source_response(path):
        nonlocal source_calls
        source_calls += 1
        # Ownership passes to DiskResponse; failure closes it here.
        stream = tempfile.TemporaryFile(mode="w+b", dir=temporary)  # noqa: SIM115
        try:
            result = asyncio.run(
                stream_asgi(
                    source_app,
                    path,
                    sink=stream,
                    timeout=timeout,
                    headers=[(b"authorization", b"Bearer isolated-review")],
                    progress=lambda size, rows: emit(
                        collection=key, phase="source", bytes=size, rows=rows
                    ),
                )
            )
            if result["status"] != 200:
                raise repository.FullReleaseUnavailable(f"Producer status {result['status']}")
            stream.seek(0)
            return DiskResponse(stream, result["headers"])
        except BaseException:
            stream.close()
            raise

    logical = {entry["name"]: entry for entry in manifest.get("partitioned_components", [])}
    offered = repository.grove_components(key) if components else [None]
    results = []
    with ExitStack() as stack:
        stack.enter_context(patch.dict(os.environ, environment))
        if key == "gaming":
            stack.enter_context(patch.object(repository, "GROVE_RELEASE_PIN", pin_path))
        stack.enter_context(
            patch.object(repository, "_release_response", side_effect=source_response)
        )
        stack.enter_context(
            patch.object(
                repository,
                "grove_full_release" if components else "full_release",
                side_effect=traced_consumer,
            )
        )
        stack.enter_context(
            patch.object(
                subscribers,
                "find",
                return_value=subscribers.Subscriber("review@example.invalid", "grove", "review"),
            )
        )
        try:
            for component in offered:
                emit(
                    collection=key,
                    component=component,
                    phase="consumer-start",
                    source_calls=source_calls,
                )
                if component in logical:
                    entries = [
                        (p["component"], manifest["components"][p["component"]])
                        for p in logical[component]["parts"]
                    ]
                elif components:
                    if component not in manifest["components"]:
                        results.append({"component": component, "status": "absent"})
                        continue
                    entries = [(component, manifest["components"][component])]
                elif collection:
                    entries = sorted(
                        manifest["components"].items(), key=lambda p: p[1]["metadata"]["ordinal"]
                    )
                else:
                    entries = [(None, manifest)]
                expected = expected_artifact(directory, entries)
                route = f"/press/collections/{key}/full-download?release_id={rid}"
                if component:
                    route += f"&component={component}"
                app.dependency_overrides[current_session] = lambda: None
                before = source_calls
                denied = asyncio.run(stream_asgi(app, route, timeout=timeout))
                if denied["status"] != 401 or source_calls != before:
                    raise AssertionError("Anonymous download was not refused")
                wrong_tier = "press_pro" if key == "gaming" else "guest"
                app.dependency_overrides[current_session] = lambda tier=wrong_tier: Session(
                    "review@example.invalid", tier
                )
                before = source_calls
                denied = asyncio.run(stream_asgi(app, route, timeout=timeout))
                if denied["status"] != 403 or source_calls != before:
                    raise AssertionError("Entitlement refusal touched protected data")
                app.dependency_overrides[current_session] = lambda: Session(
                    "review@example.invalid", "grove"
                )
                served = asyncio.run(
                    stream_asgi(
                        app,
                        route,
                        timeout=timeout,
                        progress=lambda size, rows: emit(
                            collection=key, phase="consumer", bytes=size, rows=rows
                        ),
                    )
                )
                permitted = all(
                    entry.get("download_permitted", True)
                    and entry["rights"].get("redistribution") is True
                    for _, entry in entries
                )
                if not permitted:
                    if served["status"] != 503:
                        raise AssertionError("Held component was not withheld")
                    with patch.dict(os.environ, {"CEDAR_PRESS_ENVIRONMENT": "production"}):
                        refused = asyncio.run(stream_asgi(app, route, timeout=timeout))
                        if refused["status"] != 503:
                            raise AssertionError("Production accepted a held review component")
                    results.append(
                        {
                            "component": component,
                            "status": "rights-held",
                            "expected": expected,
                            "anonymous": 401,
                            "wrong_tier": 403,
                            "production_refused": True,
                            "download_permitted": False,
                            "tiers": {"grove": 503},
                        }
                    )
                    continue
                if served["status"] != 200 or any(
                    served[name] != expected[name] for name in expected
                ):
                    raise AssertionError(
                        f"Consumer reconciliation failed: status={served['status']}; "
                        + "; ".join(consumer_errors[-3:])
                    )
                if served["headers"].get("x-cedar-release") != rid or not served["ends_in_newline"]:
                    raise AssertionError("Consumer did not preserve the exact release")
                results.append(
                    {
                        "component": component,
                        "status": "passed",
                        "expected": expected,
                        "served": served,
                        "anonymous": 401,
                        "wrong_tier": 403,
                    }
                )
                with patch.dict(os.environ, {"CEDAR_PRESS_ENVIRONMENT": "production"}):
                    refused = asyncio.run(stream_asgi(app, route, timeout=timeout))
                    if refused["status"] != 503:
                        raise AssertionError("Production accepted a review release")
                results[-1]["production_refused"] = True
                emit(collection=key, component=component, phase="consumer-passed", **expected)
        finally:
            app.dependency_overrides.clear()
    return {
        "status": (
            "passed_with_absent_components"
            if any(r["status"] == "absent" for r in results)
            else "passed"
        ),
        "collection": key,
        "release": rid,
        "manifest_file_sha256": hashlib.sha256(raw_manifest).hexdigest(),
        "catalog_id": catalog["catalog_id"],
        "source_calls": source_calls,
        "synthetic": False,
        "components": results,
    }


def reusable_receipt(item, receipt, code_revision):
    """Resume only after the producer re-verifies all saved release parts."""
    if (
        receipt.get("status") != "passed"
        or receipt.get("release") != item["release"]
        or receipt.get("code_revision") != code_revision
    ):
        return False
    from cedar_press import repository

    if repository.is_component_release(item["collection"]):
        checked = {entry["component"] for entry in receipt.get("components", [])}
        if checked != set(repository.grove_components(item["collection"])):
            return False
    from lumecon_data.collection import collection_dir, verify_collection_release
    from lumecon_data.pipeline import verify_release

    store, key, rid = Path(item["store"]), item["collection"], item["release"]
    directory = collection_dir(store, key, rid)
    if directory.exists():
        verify_collection_release(store, key, rid)
    else:
        directory = store / "releases" / key / rid
        verify_release(store, key, rid)
    raw = (directory / "manifest.json").read_bytes()
    return hashlib.sha256(raw).hexdigest() == receipt.get("manifest_file_sha256")


def main():
    if any(os.environ.get(name, "").strip() for name in ("DATABASE_URL", "CEDAR_PRESS_DB")):
        raise SystemExit("REFUSED: use an isolated environment without database configuration")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--queue", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--temporary-directory", type=Path, required=True)
    parser.add_argument("--collection", action="append")
    parser.add_argument("--timeout-seconds", type=int, default=1800)
    parser.add_argument("--code-revision", required=True)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    if not 30 <= args.timeout_seconds <= 7200:
        parser.error("timeout must be between 30 and 7200 seconds")
    queue = json.loads(args.queue.read_text(encoding="utf-8"))
    args.output.mkdir(parents=True, exist_ok=True)
    args.temporary_directory.mkdir(parents=True, exist_ok=True)
    failures = 0
    with (
        patch.object(tempfile, "tempdir", str(args.temporary_directory)),
        patch.dict(
            os.environ,
            {
                "LUMECON_ENVIRONMENT": "review",
                "CEDAR_PRESS_ENVIRONMENT": "development",
                "CEDAR_GROVE_ENVIRONMENT": "review",
                "CEDAR_PRESS_PARTITIONED_REHEARSAL": "1",
                "SQLITE_TMPDIR": str(args.temporary_directory),
                "TMP": str(args.temporary_directory),
                "TEMP": str(args.temporary_directory),
            },
        ),
    ):
        for item in queue:
            if args.collection and item["collection"] not in args.collection:
                continue
            output = args.output / item["collection"]
            output.mkdir(parents=True, exist_ok=True)
            receipt_path = output / "receipt.json"
            if args.resume and receipt_path.exists():
                old = json.loads(receipt_path.read_text())
                try:
                    reusable = reusable_receipt(item, old, args.code_revision)
                except (OSError, ValueError, RuntimeError):
                    reusable = False
                if reusable:
                    emit(
                        collection=item["collection"],
                        phase="already-verified",
                        release=item["release"],
                    )
                    continue
            start = time.monotonic()
            emit(collection=item["collection"], phase="verify-start", release=item["release"])
            try:
                receipt = run_one(item, output, args.temporary_directory, args.timeout_seconds)
            except Exception as error:
                failures += 1
                receipt = {
                    "status": "failed",
                    "collection": item["collection"],
                    "release": item["release"],
                    "error_type": type(error).__name__,
                    "error": str(error),
                }
            receipt.update(
                code_revision=args.code_revision, elapsed_seconds=round(time.monotonic() - start, 3)
            )
            temporary_receipt = receipt_path.with_suffix(".tmp")
            temporary_receipt.write_text(
                json.dumps(receipt, sort_keys=True, indent=2) + "\n", encoding="utf-8"
            )
            temporary_receipt.replace(receipt_path)
            emit(
                collection=item["collection"],
                phase=receipt["status"],
                elapsed_seconds=receipt["elapsed_seconds"],
            )
    raise SystemExit(1 if failures else 0)


if __name__ == "__main__":
    main()
