"""Local real-release rehearsal, separate from redistributable fixture CI.

Run with --store and --catalog pointing to an unpublished local Lumecon release.
Creates only a second immutable metadata-version release and a local audit log.
Never promotes a pointer or modifies canonical input. Requires both packages.
"""

import argparse
import hashlib
import json
import logging
import os
import secrets
import socket
import sqlite3
import threading
import time
from pathlib import Path

import uvicorn
from fastapi.testclient import TestClient


def main():
    # Development labels do not override database selection. Refuse inherited
    # stores before importing either service or creating any candidate artifact.
    if any(os.environ.get(name, "").strip() for name in ("DATABASE_URL", "CEDAR_PRESS_DB")):
        raise SystemExit(
            "REFUSED: rehearsal requires an isolated environment without database configuration"
        )
    from lumecon_data.api import create_app
    from lumecon_data.catalog import (
        build_catalog,
        import_catalog_release,
        select_catalog_release,
    )
    from lumecon_data.contracts import DatasetContract
    from lumecon_data.pipeline import build_release, verify_release
    from lumecon_data.storage import canonical_json, checked_path, immutable_bytes

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--store", type=Path, required=True)
    parser.add_argument("--catalog", type=Path, required=True)
    args = parser.parse_args()
    first_catalog = json.loads(args.catalog.read_text())
    pin = first_catalog["collections"][0]
    dataset = pin["dataset_id"]
    manifest = verify_release(args.store, dataset, pin["release_id"])
    original_files = {
        p: hashlib.sha256(p.read_bytes()).hexdigest()
        for p in (args.store / "releases" / dataset / pin["release_id"]).iterdir()
    }
    data = dict(manifest["contract"])
    data["title"] += " (local rollback rehearsal metadata version)"
    second = build_release(
        DatasetContract.model_validate(data), manifest["source"]["snapshot_id"], args.store
    )
    second_catalog = build_catalog(
        args.store, [(dataset, second["release_id"])], product="cedar_press"
    )
    second_path = args.store / "catalogs" / (second_catalog["catalog_id"] + ".json")
    immutable_bytes(second_path, canonical_json(second_catalog))
    database_path = checked_path(args.store, "operational", "release-catalog.sqlite")
    database_path.parent.mkdir(parents=True, exist_ok=True)
    database = sqlite3.connect(database_path)
    for _ in range(2):
        assert import_catalog_release(database, args.store, dataset, pin["release_id"],
                                      product="cedar_press") == first_catalog
    assert database.execute(
        "SELECT count(*) FROM lumecon_releases WHERE dataset_id=? AND release_id=?",
        (dataset, pin["release_id"]),
    ).fetchone()[0] == 1
    assert select_catalog_release(database, args.store, dataset, pin["release_id"],
                                  product="cedar_press") == first_catalog
    import_catalog_release(
        database, args.store, dataset, second["release_id"], product="cedar_press"
    )
    token = secrets.token_hex(32)
    password = secrets.token_hex(32)
    os.environ["CEDAR_PRESS_ENVIRONMENT"] = "development"
    os.environ["CEDAR_PRESS_SECRET"] = secrets.token_hex(32)
    os.environ["CEDAR_PRESS_INSECURE_COOKIE"] = "1"
    os.environ["CEDAR_PRESS_ACCOUNTS"] = json.dumps(
        {
            "pilot@example.invalid": {"password": password, "tier": "press_pro"},
            "denied@example.invalid": {"password": password, "tier": "unknown"},
        }
    )
    os.environ["CEDAR_PRESS_DATA_TOKEN"] = token
    os.environ["CEDAR_PRESS_RELEASE_CATALOG"] = str(args.catalog)
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    os.environ["CEDAR_PRESS_DATA_API"] = "http://127.0.0.1:" + str(sock.getsockname()[1])
    service = uvicorn.Server(
        uvicorn.Config(
            create_app(args.store, {token: {dataset}}), log_level="error", access_log=False
        )
    )
    worker = threading.Thread(target=lambda: service.run(sockets=[sock]), daemon=True)
    worker.start()
    for _ in range(100):
        if service.started:
            break
        time.sleep(0.05)
    assert service.started, "Local data API did not start"
    from cedar_press.app import app

    audit_path = args.store / "download-rehearsal.audit.jsonl"
    audit_start = audit_path.stat().st_size if audit_path.exists() else 0
    audit = logging.FileHandler(audit_path, encoding="utf-8")
    logger = logging.getLogger("cedar_press.download")
    logger.setLevel(logging.INFO)
    logger.addHandler(audit)
    try:
        with TestClient(app) as client:
            route = f"/press/collections/{dataset}/full-download?release_id={pin['release_id']}"
            assert client.get(route).status_code == 401
            assert (
                client.post(
                    "/auth/login", json={"email": "denied@example.invalid", "password": password}
                ).status_code
                == 200
            )
            assert client.get(route).status_code == 403
            client.cookies.clear()
            assert (
                client.post(
                    "/auth/login", json={"email": "pilot@example.invalid", "password": password}
                ).status_code
                == 200
            )
            catalog_response = client.get("/press/collections")
            assert catalog_response.status_code == 200
            metadata = next(
                item for item in catalog_response.json()["collections"] if item["id"] == dataset
            )["fullRelease"]
            assert metadata["release_id"] == pin["release_id"]
            assert metadata["record_count"] == manifest["record_count"]
            assert metadata["download_path"] == route
            before = client.get(route)
            assert before.status_code == 200, before.text
            rows = [json.loads(line) for line in before.content.splitlines()]
            assert len(rows) == manifest["record_count"] == manifest["record_count"]
            assert (
                len({tuple(row[key] for key in manifest["primary_key"]) for row in rows})
                == manifest["record_count"]
            )
            assert before.headers["x-cedar-release"] == pin["release_id"]
            assert (
                before.content
                == (
                    args.store / "releases" / dataset / pin["release_id"] / "records.jsonl"
                ).read_bytes()
            )
            assert hashlib.sha256(before.content).hexdigest() == before.headers["x-cedar-sha256"]
            endpoint = f"/press/collections/{dataset}/full-download"
            assert client.get(endpoint, params={"release_id": "../outside"}).status_code == 400
            assert client.get(endpoint, params={"release_id": "0" * 64}).status_code == 503
            assert select_catalog_release(database, args.store, dataset, second["release_id"],
                                          product="cedar_press") == second_catalog
            os.environ["CEDAR_PRESS_RELEASE_CATALOG"] = str(second_path)
            assert client.get(route).status_code == 503  # Stale pins cannot silently follow latest.
            newer = client.get(
                f"/press/collections/{dataset}/full-download?release_id={second['release_id']}"
            )
            assert (
                newer.status_code == 200
                and newer.headers["x-cedar-release"] == second["release_id"]
            )
            assert select_catalog_release(database, args.store, dataset, pin["release_id"],
                                          product="cedar_press", rollback=True) == first_catalog
            os.environ["CEDAR_PRESS_RELEASE_CATALOG"] = str(args.catalog)
            restored = client.get(route)
            assert restored.content == before.content
            assert restored.headers["x-cedar-release"] == pin["release_id"]
            assert all(
                hashlib.sha256(p.read_bytes()).hexdigest() == digest
                for p, digest in original_files.items()
            )
            assert not (args.store / "current").exists(), "No promotion is authorized"
            audit.flush()
            audit_text = audit_path.read_bytes()[audit_start:].decode("utf-8")
            events = [json.loads(line) for line in audit_text.splitlines()]
            assert len(events) == 8, "Every attempt in this run must have its own audit event"
            assert len({event["request_id"] for event in events}) == len(events)
            allowed = {
                "collection_id",
                "event",
                "outcome",
                "release_id",
                "request_id",
                "requested_release_id",
                "sha256",
                "timestamp",
            }
            assert all(set(event) == allowed for event in events)
            assert all(
                secret not in audit_text
                for secret in (
                    token,
                    password,
                    "pilot@example.invalid",
                    "denied@example.invalid",
                    "../outside",
                )
            )
            outcomes = [event["outcome"] for event in events]
            assert outcomes == [
                "denied_anonymous",
                "denied_entitlement",
                "authorized_prepared",
                "invalid_release_request",
                "unavailable",
                "unavailable",
                "authorized_prepared",
                "authorized_prepared",
            ]
            assert all(event["collection_id"] == dataset for event in events)
            approvals = [event for event in events if event["outcome"] == "authorized_prepared"]
            assert [event["release_id"] for event in approvals] == [
                pin["release_id"],
                second["release_id"],
                pin["release_id"],
            ]
            assert all(event["sha256"] == before.headers["x-cedar-sha256"] for event in approvals)
            result = {
                "status": "PASSED_LOCAL_NOT_PRODUCTION",
                "rows": len(rows),
                "release_id": pin["release_id"],
                "rollback_from": second["release_id"],
                "artifact_sha256": before.headers["x-cedar-sha256"],
                "canonical_release_unchanged": True,
                "catalog_database": "SQLite development metadata only; PostgreSQL not tested",
                "idempotent_import": True,
                "checks": [
                    "real data API",
                    "real Cedar login",
                    "401",
                    "403",
                    "200",
                    "audit",
                    "current-run audit completeness and redaction",
                    "malformed and nonexistent release refusal",
                    "rollback",
                    "versioned catalog database import, retry and rollback",
                ],
            }
            (args.store / "rehearsal-result.json").write_text(json.dumps(result, indent=2) + "\n")
            print(json.dumps(result))
    finally:
        logger.removeHandler(audit)
        audit.close()
        service.should_exit = True
        worker.join(timeout=10)
        sock.close()
        database.close()


if __name__ == "__main__":
    main()
