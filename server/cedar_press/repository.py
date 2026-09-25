"""Where the service's data comes from.

Every route reads through here, so the move from the ported modules to
Postgres is one module's worth of change rather than a rewrite of the API.
The shapes returned are the shapes the client already reads â€” see
``src/features/grove/`` â€” because a repository that returns its own idea of a
collection just moves the translation somewhere less visible.

The catalog, the citation register and the CSV shaping live in
``collections.py`` and ``press_catalog.py``, ported from Cedar Grove's Python
package rather than rewritten. That is deliberate: those hold the inclusion
rules and release bookkeeping, and a second implementation of them is a second
set of numbers to keep in agreement.

It is also provenance and not a dependency. Cedar Press is a standalone
product: nothing here imports a Cedar Grove module or calls a Grove service,
and every value comes from ``data/cedar/collections.manifest.json``, generated
from the Cedar data workspace in ``code/``.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import re
from collections.abc import Mapping
from functools import lru_cache
from http.client import HTTPException
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener

from cedar_press import collection_profiles, press_catalog
from cedar_press import collections as launch

#: Which shelf each plan reaches. Mirrors ``PLAN_REACH`` in
#: ``features/grove/pressAccess.js``; the client decides what renders and this
#: decides what is served, and the two are written to answer identically.
#:
#: They were not compared until ``tests/test_access.py``, and by then they had
#: drifted: ``tree`` was here and missing there, so a Tree subscriber was
#: served twelve collections by this module and shown none of them on the
#: shelf. That test now compares the two maps key for key.
#:
#: ``grove`` reaches every shelf because Cedar Grove carries every dataset, and
#: ``tree`` reaches every shelf because Tree includes Grove. Reaching a shelf
#: is not the same as being sold the Cedar Press page -- neither tier is; that
#: question is ``press_catalog.can_read_cedar_press``.
SHELF_BY_TIER: dict[str, str] = {
    "press": "standard",
    "press_pro": "pro",
    "grove": "grove",
    "tree": "grove",
}

#: Shelves need upward: a plan that reaches "pro" also reaches "standard",
#: mirroring SHELF_ORDER in ``features/grove/pressAccess.js``.
SHELF_ORDER: tuple[str, ...] = ("standard", "pro", "grove")


def _reaches(tier: str, dataset_shelf: str) -> bool:
    """Whether this plan's shelf includes a dataset placed on ``dataset_shelf``."""
    shelf = SHELF_BY_TIER.get(tier)
    if shelf is None or dataset_shelf not in SHELF_ORDER:
        return False
    return SHELF_ORDER.index(dataset_shelf) <= SHELF_ORDER.index(shelf)


def _dataset_payload(dataset: Any) -> dict[str, Any]:
    """One collection, in the shape the shelf reads.

    ``vintage`` and ``downloads`` are ``null`` on every collection today and
    are still sent: a client that receives the key and no value can render an
    absence, while a client that receives no key at all cannot tell an absent
    measurement from an older server. ``unmeasured`` names them and says why,
    so nothing downstream has to decide on its own whether a null is a gap or
    a zero.

    ``sample`` and ``tables`` are what the download is actually backed by --
    ten rows of the flagship table, and every table's row count and
    full-file split -- so a client can say what it is handing over instead of
    calling ten rows a collection.
    """
    return {
        "id": dataset.id,
        "shelf": dataset.shelf,
        "name": dataset.name,
        "shortName": dataset.short_name,
        "tracks": dataset.tracks,
        "rowsLabel": dataset.rows_label,
        "downloads": dataset.downloads,
        "vintage": dataset.vintage,
        "version": dataset.version,
        "updated": dataset.updated,
        "sources": dataset.sources,
        "method": dataset.method,
        "cedar": launch.collection_cedar_facts(dataset.id),
        "sample": launch.collection_sample(dataset.id),
        "fullRelease": full_release_metadata(dataset.id),
        "tables": list(launch.collection_tables(dataset.id)),
        "unmeasured": {
            field: reason
            for field, reason in launch.UNMEASURED_FIELDS.items()
            if getattr(dataset, field, None) in (None, "")
        },
    }


def collections_for(tier: str) -> list[dict[str, Any]]:
    """The collections a plan may open.

    The shelves diverged with the Owned dataset (pro and above), so this
    filters on the tier's reach rather than returning everything and letting
    the client hide the rest, because hiding is not withholding.
    """
    return [
        _dataset_payload(dataset)
        for dataset in launch.LAUNCH_COLLECTION
        if _reaches(tier, dataset.shelf)
    ]


def may_open(tier: str, collection_id: str) -> bool:
    """Whether this plan includes this collection.

    ``LAUNCH_COLLECTION`` is the storefront -- the twelve on
    ``cedar_publication.STOREFRONT_SHELVES`` -- so a collection the Cedar data
    workspace placed on the ``grove`` shelf is refused to every tier here,
    including ``grove`` and ``tree``. That is the ruling and not an oversight:
    ``gaming`` "ships through Cedar Grove, not the Press storefront", and it
    reaches this repository in the manifest's ``excluded`` rather than its
    ``collections``.

    The browser used to disagree. Codex, PR #41: its catalog is thirteen, it
    reads the shelf ordering rather than the storefront, and a Grove or Tree
    session was shown ``gaming`` as open while this function refused it.
    ``canOpenDataset`` in ``features/grove/pressAccess.js`` now refuses a
    grove-shelf collection for every plan, and
    ``tests/test_access.py::TestNothingTheClientOpensIsRefused`` compares the
    two answers per tier and per collection in both directions.
    """
    return any(
        dataset.id == collection_id and _reaches(tier, dataset.shelf)
        for dataset in launch.LAUNCH_COLLECTION
    )


def is_sold(collection_id: str) -> bool:
    """Whether the storefront sells this collection to anybody at all.

    ``may_open`` answers False for two situations that are not the same thing,
    and a caller that treats them alike says something false about one of
    them. A ``pro``-shelf collection is refused to a Press plan *and named*:
    it is sold, and Cedar Press+ opens it. A collection that is not in
    ``LAUNCH_COLLECTION`` -- one catalogued ahead of its descriptor, or
    ``gaming``, which ships through Cedar Grove and reaches this repository in
    the manifest's ``excluded`` -- is refused to *every* plan, including Grove
    and Tree. Telling a reader that one of those "comes with Cedar Press+"
    would be an upgrade prompt for something the upgrade does not include.

    So the plan gate asks this first, and only a collection the storefront
    actually sells can be withheld on the grounds of a plan.
    """
    return any(dataset.id == collection_id for dataset in launch.LAUNCH_COLLECTION)


def collection_csv(collection_id: str) -> str | None:
    """The preview file's rows, citation included.

    Ten rows of the collection's flagship table, not the collection. The full
    tables are not served from this repository; ``collection_tables`` carries
    what a serving layer needs to find them.
    """
    return launch.collection_csv(collection_id)


def sample_unavailable_reason(collection_id: str) -> str | None:
    """Why a collection has no preview file, so a route can say which it is.

    A collection the shelf shows and the file layer cannot serve is a
    different failure from a collection that does not exist, and answering
    both with "No such collection" hides a real, named data problem behind a
    routing message.
    """
    return launch.sample_unavailable_reason(collection_id)


def download_name(collection_id: str) -> str:
    dataset = next((item for item in launch.LAUNCH_COLLECTION if item.id == collection_id), None)
    version = dataset.version if dataset else "v0"
    # The filename says it is a sample. A file called `deals-v0.csv` sitting in
    # somebody's downloads folder a month later cannot be told apart from the
    # release, and ten rows of a 2,662-row collection is not the release.
    return f"{collection_id}-{version}-sample.csv"


def releases() -> list[dict[str, Any]]:
    """Release history per collection, most recently updated first.

    Served from the dumped snapshot of ``pressReleases.js`` â€” the same
    change notes the What's New feed renders â€” so the service and the page
    describe one history rather than two.
    """
    rows = [
        {"id": collection_id, **_thaw(release)}
        for collection_id, release in press_catalog.RELEASES.items()
    ]
    return sorted(rows, key=lambda row: row.get("updated", ""), reverse=True)


def _thaw(value: Any) -> Any:
    """Plain dicts and lists, all the way down.

    ``press_catalog`` deep-freezes its snapshot so no caller can edit the
    catalogue every later caller sees, which leaves nested values as
    ``mappingproxy`` â€” a type the JSON serializer refuses. Copying at the top
    level only was not enough: an article's body and figures are nested, and
    the failure surfaced as a 500 on a route whose data was fine.
    """
    if isinstance(value, Mapping):
        return {key: _thaw(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_thaw(item) for item in value]
    return value


def collection_profile(collection_id: str) -> dict[str, Any] | None:
    """The machine-readable profile Cedar answers from, or ``None``."""
    return collection_profiles.profile_for(collection_id)


def cedar_answer(question: str, collection_id: str) -> dict[str, str] | None:
    """A profile-grounded answer, or ``None`` when the question needs more.

    The tier used to travel with the question, because coverage was phrased
    for the reader: a Cedar Press reader was told what Cedar Press+ would
    open. Retiring the year cap (2026-09-02) removed the only thing the tier
    decided here, and a parameter nothing reads is a parameter the next
    caller will pass wrongly.
    """
    return collection_profiles.answer_from_profile(question, collection_id)


def articles() -> list[dict[str, Any]]:
    """Published briefs, newest first."""
    return [_thaw(article) for article in press_catalog.ARTICLES]


def citations() -> list[dict[str, Any]]:
    """Every recorded public use of a collection. Empty until one lands."""
    return [_thaw(entry) for entry in press_catalog.CITATIONS]


class FullReleaseUnavailable(ValueError):
    """The pinned full file cannot be verified; never substitute a sample."""


def _canonical_bytes(value):
    return (
        json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
        )
        + "\n"
    ).encode("utf-8")


MAX_RELEASE_BYTES = 256 * 1024 * 1024


def _release_bytes(path, *, limit=MAX_RELEASE_BYTES):
    base = os.environ.get("CEDAR_PRESS_DATA_API", "").rstrip("/")
    token = os.environ.get("CEDAR_PRESS_DATA_TOKEN", "")
    environment = os.environ.get("CEDAR_PRESS_ENVIRONMENT", "development")
    parsed = urlparse(base)
    if environment not in {"development", "staging", "production"}:
        raise FullReleaseUnavailable("Unknown service environment")
    if (
        not token
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or parsed.path not in {"", "/"}
        or any(character.isspace() for character in token)
    ):
        raise FullReleaseUnavailable("Missing or invalid data service configuration")
    local = parsed.hostname in {"127.0.0.1", "localhost", "::1"}
    if parsed.scheme != "https" and not (
        environment == "development" and parsed.scheme == "http" and local
    ):
        raise FullReleaseUnavailable("Data service requires HTTPS outside local development")
    if environment != "development" and (
        local or os.environ.get("CEDAR_PRESS_INSECURE_COOKIE") == "1"
    ):
        raise FullReleaseUnavailable(
            "Production/staging cannot use local or insecure configuration"
        )

    if environment != "development":
        secret = os.environ.get("CEDAR_PRESS_SECRET", "")
        database = os.environ.get("DATABASE_URL", "")
        if (
            len(secret) < 32
            or len(token) < 32
            or not database.startswith(("postgresql://", "postgres://"))
            or os.environ.get("CEDAR_PRESS_ACCOUNTS", "").strip()
        ):
            raise FullReleaseUnavailable("Persistent protected service configuration required")

    class NoRedirect(HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            raise FullReleaseUnavailable("Data service redirects are refused")

    request = Request(base + path, headers={"Authorization": "Bearer " + token})
    with build_opener(NoRedirect()).open(request, timeout=30) as response:
        content = response.read(limit + 1)
    if len(content) > limit:
        raise FullReleaseUnavailable("Data response exceeds configured safety limit")
    return content


def _release_json(path):
    return json.loads(_release_bytes(path, limit=4 * 1024 * 1024))


@lru_cache(maxsize=1)
def _publication_policy():
    # The existing governed producer owns the hold. Do not recreate it in the API.
    path = Path(__file__).resolve().parents[2] / "code/cedar_publication.py"
    spec = importlib.util.spec_from_file_location("cedar_release_publication", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def full_release(collection_id, requested_release_id=None, *, metadata_only=False):
    """Exact pinned Lumecon artifact, checked against the existing product field map.

    A trusted, reviewed catalog enables a collection; user parameters cannot select
    a different release. Holds remain enforced by the canonical publication owner.
    """
    if not any(item.id == collection_id for item in launch.LAUNCH_COLLECTION):
        raise FullReleaseUnavailable("Unknown collection")
    try:
        policy = _publication_policy()
    except (OSError, ImportError, AttributeError) as error:
        raise FullReleaseUnavailable("Publication policy unavailable") from error
    try:
        policy.assert_collection_publishable(collection_id)
    except policy.FieldMapRefusal as error:
        raise FullReleaseUnavailable("Collection publication is held") from error
    location = os.environ.get("CEDAR_PRESS_RELEASE_CATALOG")
    if not location:
        raise FullReleaseUnavailable("No pinned release catalog configured")
    try:
        catalog = json.loads(Path(location).read_text(encoding="utf-8"))
        if not isinstance(catalog, dict) or not isinstance(catalog.get("collections"), list):
            raise FullReleaseUnavailable("Malformed catalog")
        if any(not isinstance(item, dict) for item in catalog["collections"]):
            raise FullReleaseUnavailable("Malformed catalog entries")
        catalog_id = catalog.pop("catalog_id")
        if hashlib.sha256(_canonical_bytes(catalog)).hexdigest() != catalog_id:
            raise FullReleaseUnavailable("Catalog checksum mismatch")
        if (
            type(catalog.get("schema_version")) is not int
            or catalog["schema_version"] != 1
            or catalog.get("product") != "cedar_press"
            or catalog.get("entitlement_required") is not True
        ):
            raise FullReleaseUnavailable("Wrong product catalog")
        pins = [item for item in catalog["collections"] if item["dataset_id"] == collection_id]
        if len(pins) != 1:
            raise FullReleaseUnavailable("Exactly one pinned collection release required")
        pin = pins[0]
        release_id = pin["release_id"]
        if not isinstance(release_id, str) or not re.fullmatch(r"[0-9a-f]{64}", release_id):
            raise FullReleaseUnavailable("Malformed release ID")
        if not metadata_only and requested_release_id != release_id:
            raise FullReleaseUnavailable("Requested release is not the approved catalog pin")
        manifest_digest = pin.get("manifest_sha256")
        if not isinstance(manifest_digest, str) or not re.fullmatch(
            r"[0-9a-f]{64}", manifest_digest
        ):
            raise FullReleaseUnavailable("Catalog lacks an approved manifest digest")
        prefix = f"/v1/datasets/{collection_id}/releases/{release_id}"
        manifest = _release_json(prefix + "/manifest")
        if not isinstance(manifest, dict) or not isinstance(manifest.get("rights"), dict):
            raise FullReleaseUnavailable("Malformed manifest")
        if hashlib.sha256(_canonical_bytes(manifest)).hexdigest() != manifest_digest:
            raise FullReleaseUnavailable("Manifest differs from the approved catalog pin")
        for name in ("dataset_id", "release_id", "record_count", "fields", "rights", "synthetic"):
            if manifest[name] != pin[name]:
                raise FullReleaseUnavailable("Release metadata differs from pinned catalog")
        if (
            type(manifest.get("schema_version")) is not int
            or manifest["schema_version"] != 1
            or manifest["synthetic"] is not False
            or manifest["rights"]["publication_class"] not in {"public", "publishable"}
            or manifest["rights"].get("redistribution") is not True
        ):
            raise FullReleaseUnavailable("Release is not eligible for customer delivery")
        header = [field["name"] for field in manifest["fields"]]
        field_map = json.loads(
            (Path(__file__).resolve().parents[2] / "data/cedar/field_map.json").read_text(
                encoding="utf-8"
            )
        )
        entries = [
            (name, entry)
            for name, entry in field_map["tables"].items()
            if name.startswith(collection_id + "/")
        ]
        if len(entries) != 1 or header != entries[0][1]["order"]:
            raise FullReleaseUnavailable("Full release does not match product field map")
        table_id = entries[0][0].split("/", 1)[1]
        count = manifest["record_count"]
        expected = manifest["files"]["records.jsonl"]
        if (
            type(count) is not int
            or count < 1
            or type(expected["bytes"]) is not int
            or not 0 < expected["bytes"] <= MAX_RELEASE_BYTES
            or not re.fullmatch(r"[0-9a-f]{64}", expected["sha256"])
        ):
            raise FullReleaseUnavailable("Invalid or oversized release artifact")
        route = f"/press/collections/{collection_id}/full-download?release_id={release_id}"
        if metadata_only:
            return {
                "kind": "full",
                "release_id": release_id,
                "schema_version": 1,
                "record_count": count,
                "fields": header,
                "table_id": table_id,
                "scope": "Pinned flagship table only; ancillary tables excluded",
                "format": "jsonl",
                "records_sha256": expected["sha256"],
                "download_path": route,
            }
        content = _release_bytes(prefix + "/download", limit=expected["bytes"])
        if (
            len(content) != expected["bytes"]
            or hashlib.sha256(content).hexdigest() != expected["sha256"]
        ):
            raise FullReleaseUnavailable("Served bytes differ from verified release artifact")
        rows = [json.loads(line) for line in content.splitlines()]
        if len(rows) != count or any(
            not isinstance(row, dict) or set(row) != set(header) for row in rows
        ):
            raise FullReleaseUnavailable("Record count or schema mismatch")
        primary_key = manifest["primary_key"]
        if (
            not isinstance(primary_key, list)
            or not primary_key
            or not set(primary_key) <= set(header)
        ):
            raise FullReleaseUnavailable("Missing declared row identity")
        keys = [tuple(row[key] for key in primary_key) for row in rows]
        if (
            any(any(value is None or value == "" for value in key) for key in keys)
            or len(set(keys)) != count
        ):
            raise FullReleaseUnavailable("Invalid primary keys")
        return {
            "content": content,
            "release_id": release_id,
            "record_count": count,
            "sha256": expected["sha256"],
            "fields": header,
            "citation": f"Cedar Press {collection_id}/{table_id}, release {release_id}",
            "filename": f"{collection_id}-{release_id}.jsonl",
            "media_type": "application/x-ndjson",
        }
    except (OSError, HTTPException, ValueError, KeyError, TypeError) as error:
        raise FullReleaseUnavailable(
            "Pinned full release unavailable or failed verification"
        ) from error


def full_release_metadata(collection_id):
    """Preview counts are never substituted for a verified full-release descriptor."""
    if not os.environ.get("CEDAR_PRESS_RELEASE_CATALOG"):
        return None
    try:
        return full_release(collection_id, metadata_only=True)
    except FullReleaseUnavailable:
        return {"kind": "full", "status": "unavailable"}
