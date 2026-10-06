"""Verify real saved research packets through the producer API and consumer gates.

This is an explicit local review command, not a CI fixture or a customer publish step.
The queue names immutable stores/releases and packet directories. No source rows print.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from cedar_press import grove_exchange, release_research, repository, subscribers
from cedar_press.app import app
from cedar_press.session import Session, current_session


def run_one(item, output):
    from lumecon_data.api import create_app
    from lumecon_data.catalog import build_catalog
    from lumecon_data.collection import collection_dir

    key, rid = item["collection"], item["release"]
    store, packet_dir = Path(item["store"]), Path(item["packet"])
    packet_receipt = json.loads((packet_dir / "receipt.json").read_text(encoding="utf-8"))
    assert packet_receipt["release_id"] == rid and packet_receipt["synthetic"] is False
    packet_pin = hashlib.sha256((packet_dir / "receipt.json").read_bytes()).hexdigest()
    output.mkdir(parents=True, exist_ok=True)
    research_catalog = packet_dir.parent / (key + "-catalog.json")
    research_catalog.write_bytes(
        repository._canonical_bytes(
            {
                "review_only": True,
                "packets": {
                    key: {
                        "release_id": rid,
                        "directory": packet_dir.name,
                        "receipt_sha256": packet_pin,
                    }
                },
            }
        )
    )
    grove_only = repository.is_grove_release(key)
    product = "cedar_grove" if grove_only else "cedar_press"
    catalog = build_catalog(
        store,
        [(key, rid)],
        product=product,
        allow_rehearsal=True,
        release_kind="collection" if collection_dir(store, key, rid).exists() else "dataset",
    )
    catalog_bytes = repository._canonical_bytes(catalog)
    catalog_path, pin_path = output / "catalog.json", output / "pin.json"
    catalog_path.write_bytes(catalog_bytes)
    component_release = repository.is_component_release(key)
    if component_release:
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
        "CEDAR_PRESS_RESEARCH_CATALOG": str(research_catalog),
    }
    source = create_app(store, {"isolated-review": {key}})
    source_calls = []
    response_cache = {}

    def fetch_json(path, *, limit=8 * 1024 * 1024):
        # Only metadata is needed; real full-byte downloads have separate receipts.
        assert path.endswith("/manifest"), "Research should not download whole collections"
        if path in response_cache:
            return json.loads(response_cache[path])
        source_calls.append(path)
        result = source_client.get(path, headers={"Authorization": "Bearer isolated-review"})
        if result.status_code != 200:
            raise repository.FullReleaseUnavailable("Producer refused manifest")
        assert len(result.content) <= limit
        response_cache[path] = result.content
        return result.json()

    tier = "grove" if grove_only else "press_pro"
    results = []
    with ExitStack() as stack:
        stack.enter_context(patch.dict(os.environ, environment))
        source_client = stack.enter_context(TestClient(source))
        stack.enter_context(patch.object(repository, "_release_json", side_effect=fetch_json))
        if grove_only:
            stack.enter_context(patch.object(repository, "GROVE_RELEASE_PIN", pin_path))
        stack.enter_context(
            patch.object(
                subscribers,
                "find",
                return_value=subscribers.Subscriber("review@example.invalid", tier, "local-review"),
            )
        )
        app.dependency_overrides[current_session] = lambda: Session("review@example.invalid", tier)
        stack.callback(app.dependency_overrides.pop, current_session, None)
        client = stack.enter_context(TestClient(app))
        components = repository.grove_components(key) if component_release else [None]
        for component in components:
            print(
                json.dumps({"collection": key, "component": component, "phase": "research-gates"}),
                flush=True,
            )
            logical = component or next(iter(packet_receipt["tables"]))
            expected = (
                packet_receipt["tables"].get(logical, {}).get("permitted_review_rows", 0) > 0
                and key != "need"
            )
            try:
                payload = grove_exchange.exchange(
                    {
                        "protocol_version": 1,
                        "tier": "grove",
                        "operation": "research",
                        "collection": key,
                        "release_id": rid,
                        **({"component": component} if component else {}),
                    }
                )
            except repository.FullReleaseUnavailable as error:
                assert not expected, f"{key}/{component}: {error}"
                results.append({"component": component, "status": "held_refused"})
                continue
            assert expected and payload["release_id"] == rid
            assert 0 < payload["sample_rows"] <= 30
            assert (
                payload["source_rows"] == packet_receipt["tables"][logical]["permitted_review_rows"]
            )
            if not grove_only:
                params = {"release_id": rid, **({"component": component} if component else {})}
                response = client.get("/press/collections/" + key + "/research", params=params)
                assert response.status_code == 200, response.text[:300]
                assert response.json() == payload
                assert response.headers["cache-control"] == "private, no-store"
            results.append(
                {
                    "component": component,
                    "status": "permitted_review_preview",
                    "source_rows": payload["source_rows"],
                    "sample_rows": payload["sample_rows"],
                    "fields": len(payload["codebook"]["fields"]),
                    "map_features": len(payload.get("map_preview", {}).get("features", [])),
                    "map_omitted": len(payload.get("map_preview", {}).get("omitted", [])),
                    "map_artifact_sha256": payload["provenance"].get("map_artifact_sha256"),
                    "response_sha256": hashlib.sha256(
                        repository._canonical_bytes(payload)
                    ).hexdigest(),
                }
            )
        with patch.dict(
            os.environ,
            {"CEDAR_PRESS_ENVIRONMENT": "production", "CEDAR_GROVE_ENVIRONMENT": "production"},
        ):
            for component in components:
                try:
                    release_research.packet(tier, key, rid, component)
                except repository.FullReleaseUnavailable:
                    pass
                else:
                    raise AssertionError("Review release exposed in production")
    result = {
        "collection": key,
        "release_id": rid,
        "packet_receipt_sha256": packet_pin,
        "manifest_sha256": packet_receipt["consumer_manifest_sha256"],
        "synthetic": False,
        "metadata_requests": len(source_calls),
        "components": results,
        "production_refused": True,
        "scope": "Real packet and producer metadata API; separate receipts prove full downloads.",
    }
    (output / "receipt.json").write_bytes(repository._canonical_bytes(result))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--queue", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if any(os.environ.get(k) for k in ("DATABASE_URL", "CEDAR_PRESS_DB")):
        raise SystemExit(
            "Use isolated review environment without subscriber database configuration"
        )
    with patch.dict(
        os.environ,
        {
            "LUMECON_ENVIRONMENT": "review",
            "CEDAR_PRESS_ENVIRONMENT": "development",
            "CEDAR_GROVE_ENVIRONMENT": "review",
            "CEDAR_PRESS_PARTITIONED_REHEARSAL": "1",
        },
    ):
        for item in json.loads(args.queue.read_text(encoding="utf-8")):
            started = time.monotonic()
            result = run_one(item, args.output / item["collection"])
            print(
                json.dumps(
                    {
                        "collection": item["collection"],
                        "components": len(result["components"]),
                        "seconds": round(time.monotonic() - started, 2),
                        "status": "PASS",
                    }
                ),
                flush=True,
            )


if __name__ == "__main__":
    main()
