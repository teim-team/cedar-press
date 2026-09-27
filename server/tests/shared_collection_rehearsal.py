"""Replay a real Giving/PLOT release through Lumecon and Cedar in one process.

No network listener, subprocess, fixture generation or source mutation. Install
both repositories in the same Python environment (or set their import paths).
The output includes an isolated review catalog/pin and machine-readable receipt.
"""

import argparse
import hashlib
import json
import os
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from lumecon_data.api import create_app
from lumecon_data.collection import build_collection_catalog, verify_collection_release

from cedar_press import repository, subscribers
from cedar_press.app import app
from cedar_press.session import Session, current_session


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--store", required=True, type=Path)
    parser.add_argument(
        "--collection", required=True, choices=repository.governed_collections.SHARED_COLLECTIONS
    )
    parser.add_argument("--release", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    receipt = {"collection_id": args.collection, "release_id": args.release, "components": []}
    review_env = {
        "LUMECON_ENVIRONMENT": "review",
        "CEDAR_PRESS_ENVIRONMENT": "development",
        "CEDAR_GROVE_ENVIRONMENT": "review",
        "CEDAR_PRESS_COMPONENT_RELEASE_PIN": str(args.output / "pin.json"),
        "CEDAR_PRESS_COMPONENT_RELEASE_CATALOG": str(args.output / "catalog.json"),
    }
    with patch.dict(os.environ, review_env):
        manifest = verify_collection_release(args.store, args.collection, args.release)
        if manifest["synthetic"]:
            raise ValueError("This receipt requires real candidate content")
        catalog = build_collection_catalog(
            args.store,
            [(args.collection, args.release)],
            product="cedar_press",
            allow_rehearsal=True,
        )
        catalog_bytes = repository._canonical_bytes(catalog)
        (args.output / "catalog.json").write_bytes(catalog_bytes)
        pin = {
            "collection_id": args.collection,
            "release_id": args.release,
            "catalog_id": catalog["catalog_id"],
            "catalog_sha256": hashlib.sha256(catalog_bytes).hexdigest(),
            "manifest_sha256": catalog["collection_releases"][0]["manifest_sha256"],
        }
        (args.output / "pin.json").write_bytes(
            repository._canonical_bytes(
                {"schema_version": 1, "product": "cedar_press", "pins": {args.collection: pin}}
            )
        )
        receipt.update(
            {
                "synthetic": False,
                "release_class": manifest["release_class"],
                "manifest_metadata_sha256": pin["manifest_sha256"],
                "transport": "in-process HTTP clients; exact saved real release",
            }
        )
        with TestClient(create_app(args.store, {"local-review": {args.collection}})) as producer:

            def fetch(path, limit=None):
                response = producer.get(path, headers={"Authorization": "Bearer local-review"})
                if response.status_code != 200:
                    raise repository.FullReleaseUnavailable(
                        f"Producer status {response.status_code}"
                    )
                if limit is not None and len(response.content) > limit:
                    raise repository.FullReleaseUnavailable("Producer response exceeds byte limit")
                return response.content

            with (
                TestClient(app) as consumer,
                patch.object(repository, "_release_bytes", side_effect=fetch),
                patch.object(
                    subscribers,
                    "find",
                    return_value=subscribers.Subscriber(
                        "local-review@example.invalid", "grove", "local-review"
                    ),
                ),
            ):
                try:
                    for component in repository.grove_components(args.collection):
                        contract = manifest["components"][component]
                        permitted = contract["download_permitted"]
                        route = f"/press/collections/{args.collection}/full-download"
                        params = {"release_id": args.release, "component": component}
                        entry = {
                            "component": component,
                            "real_rows": contract["record_count"],
                            "download_permitted": permitted,
                            "tiers": {},
                        }
                        for tier in ("press", "press_pro", "grove"):
                            app.dependency_overrides[current_session] = lambda t=tier: Session(
                                "local-review@example.invalid", t
                            )
                            response = consumer.get(route, params=params)
                            entitled = repository.may_download_full(tier, args.collection)
                            expected_status = 403 if not entitled else (200 if permitted else 503)
                            if response.status_code != expected_status:
                                raise AssertionError((component, tier, response.status_code))
                            entry["tiers"][tier] = response.status_code
                            if response.status_code == 200:
                                rows = len(response.content.splitlines())
                                digest = hashlib.sha256(response.content).hexdigest()
                                if (
                                    rows != contract["record_count"]
                                    or digest != contract["files"]["records.jsonl"]["sha256"]
                                ):
                                    raise AssertionError("Consumer bytes differ from real manifest")
                                entry.update({"served_rows": rows, "served_sha256": digest})
                        receipt["components"].append(entry)
                        print(json.dumps(entry, sort_keys=True), flush=True)
                    with patch.dict(os.environ, {"CEDAR_PRESS_ENVIRONMENT": "production"}):
                        response = consumer.get(route, params=params)
                        if response.status_code != 503:
                            raise AssertionError("Production accepted a review pin")
                    receipt["production_refused"] = True
                finally:
                    app.dependency_overrides.clear()
    receipt["status"] = "passed"
    (args.output / "receipt.json").write_bytes(repository._canonical_bytes(receipt))
    print(json.dumps({"status": "passed", "receipt": str(args.output / "receipt.json")}))


if __name__ == "__main__":
    main()
